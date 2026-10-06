//============================================================================
//  Williams ADPCM sound board (T-Unit: Mortal Kombat, NBA Jam / TE, Judge
//  Dredd)
//
//  A 6809E at 2 MHz with a YM2151, an 8-bit DAC and an OKI M6295, talking
//  to the main board through a command latch (MAME
//  williams_adpcm_sound_device):
//    0000-1FFF  RAM, 8 KB
//    2000-23FF  W: ROM bank (0-7)
//    2400-27FF  YM2151 (IRQ: FIRQ)
//    2800-2BFF  W: DAC
//    2C00-2FFF  OKI M6295
//    3000-33FF  R: command (clears IRQ)
//    3400-37FF  W: OKI bank
//    3C00-3FFF  W: talkback
//    4000-BFFF  banked ROM, C000-FFFF fixed ROM
//
//  ROM comes from SDRAM; the region starts at what MAME calls offset 0x10000
//  of the sound CPU region. Each game protects its sound program with a
//  small window of hidden RAM (MAME init_*: install_ram over the ROM), an
//  overlay RAM here.
//
//  The Y Unit core's williams_sound.sv with the CVSD board taken out: the
//  T-Unit only has this board. The mixer is pipelined (one multiply or one
//  sum per clock), the fix the Y Unit made for its worst timing path.
//
//  Copyright (C) 2026 Gm0rk - GPL-3.0-or-later
//============================================================================

module williams_adpcm
(
	input             clk,             // 96 MHz
	input             reset,
	input             pause,

	input      [15:0] prot_start,      // hidden RAM window (MAME init_*)
	input      [15:0] prot_end,

	// command from the main board
	input             cmd_wr,
	input      [15:0] cmd_data,
	output            irq_state,       // command pending

	// SDRAM: sound CPU ROM and OKI samples
	output reg [24:3] rom_addr,
	output reg        rom_req,
	input             rom_ack,
	input      [63:0] rom_data,

	output reg [24:3] oki_addr,
	output reg        oki_req,
	input             oki_ack,
	input      [63:0] oki_data,

	output reg signed [15:0] audio
);

localparam [24:0] SND_BASE = 25'h0D0_0000;
localparam [24:0] OKI_BASE = 25'h0D4_0000;

//----------------------------------------------------------------------------
// Clock enables: E/Q for the 6809 (2 MHz), YM2151 (3.579545 MHz), OKI (1 MHz)
//----------------------------------------------------------------------------

reg   [5:0] ecnt;
reg         fallE, fallQ;
reg         mem_ready;

// A CPU cycle is 48 clk. The E edge is held back while a ROM read is still
// in flight; the time lost is made up by shortening the following cycles
// (to no less than 32 clk) so the average rate stays at 2 MHz.
//
// Settling times: the 6809 core works out its next address and register
// values combinationally (many logic levels), so nothing samples them until
// A_SETTLE clk after an E edge, and the read data is latched into din_r at
// least D_SETTLE clk before the E edge that takes it. The SDC declares the
// matching multicycle paths for the sound CPU.
localparam [5:0] A_SETTLE = 6'd8;
localparam [3:0] D_SETTLE = 4'd8;

reg   [7:0] lag;
reg         din_ok;              // read data latched for this cycle
reg   [3:0] din_age;             // clk since then
wire  [5:0] shorten = (lag > 8'd15) ? 6'd15 : lag[5:0];
reg   [5:0] cyc_end;             // last clk of this cycle (lag only changes at the E edge)
always @(posedge clk) cyc_end <= 6'd47 - shorten;
wire        e_fire  = !pause && (ecnt >= cyc_end) && din_ok && (din_age >= D_SETTLE - 4'd1);   // last clk of the cycle

always @(posedge clk) begin
	fallE <= 1'b0;
	fallQ <= 1'b0;
	if (reset) begin
		ecnt <= 6'd0;
		lag  <= 8'd0;
	end
	else if (!pause) begin
		if (ecnt == cyc_end - 6'd12)
			fallQ <= 1'b1;
		if (e_fire) begin
			fallE <= 1'b1;
			ecnt  <= 6'd0;
			lag   <= lag - {2'd0, shorten} + {2'd0, ecnt - cyc_end};
		end
		else if (ecnt != 6'd63)
			ecnt <= ecnt + 6'd1;
	end
end

reg  [26:0] fm_acc;
reg         fm_cen, fm_cen_p1, fm_half;
always @(posedge clk) begin
	fm_cen    <= 1'b0;
	fm_cen_p1 <= 1'b0;
	if (reset) begin
		fm_acc  <= 27'd0;
		fm_half <= 1'b0;
	end
	else if (fm_acc + 27'd3579545 >= 27'd96000000) begin
		fm_acc    <= fm_acc + 27'd3579545 - 27'd96000000;
		fm_cen    <= ~pause;
		fm_half   <= ~fm_half;
		fm_cen_p1 <= ~pause & fm_half;
	end
	else
		fm_acc <= fm_acc + 27'd3579545;
end

reg   [6:0] oki_div;
reg         oki_cen;
always @(posedge clk) begin
	oki_cen <= 1'b0;
	if (reset)
		oki_div <= 7'd0;
	else if (oki_div == 7'd95) begin
		oki_div <= 7'd0;
		oki_cen <= ~pause;
	end
	else
		oki_div <= oki_div + 7'd1;
end

//----------------------------------------------------------------------------
// Command interface and board reset (MAME williams_adpcm_sound_device
// reset_write / write)
//
// Bit 8 low holds the sound CPU in reset (and selects bank 0); bits 0-7 are
// latched, and bit 9 low raises the CPU IRQ. The T-Unit always writes bit 9
// as 0 (MAME passes data & 0xff), so every command interrupts.
//----------------------------------------------------------------------------

reg         cpu_hold;            // reset requested by the main board
reg   [7:0] cmd_latch;
reg         snd_irq;             // command IRQ
reg         int_state;           // visible to the main CPU
reg  [10:0] int_clr_timer;       // 10 us after a command read

assign irq_state = int_state;

wire        cpu_rnw;
wire [15:0] cpu_addr;
wire  [7:0] cpu_dout;
reg   [7:0] cpu_din;             // read data mux (settles during the cycle)
reg   [7:0] din_r;               // what the CPU sees, latched before the E edge
reg   [2:0] bank;
reg   [2:0] oki_bank;

reg         cmd_read;            // command register read this cycle

always @(posedge clk) begin
	if (reset) begin
		cpu_hold      <= 1'b0;
		cmd_latch     <= 8'h00;
		snd_irq       <= 1'b0;
		int_state     <= 1'b0;
		int_clr_timer <= 11'd0;
	end
	else begin
		if (int_clr_timer != 11'd0) begin
			int_clr_timer <= int_clr_timer - 11'd1;
			if (int_clr_timer == 11'd1) int_state <= 1'b0;
		end
		if (cmd_read) begin
			snd_irq       <= 1'b0;
			int_clr_timer <= 11'd960;
		end
		if (cmd_wr) begin
			cpu_hold  <= ~cmd_data[8];
			cmd_latch <= cmd_data[7:0];
			if (!cmd_data[8]) begin
				// device_reset: interrupt lines and the IRQ state drop
				snd_irq       <= 1'b0;
				int_state     <= 1'b0;
				int_clr_timer <= 11'd0;
			end
			if (!cmd_data[9]) begin
				snd_irq   <= 1'b1;
				int_state <= 1'b1;
			end
		end
	end
end

//----------------------------------------------------------------------------
// 6809E
//----------------------------------------------------------------------------

wire        ym_irq_n;
reg         cpu_reset_n;

always @(posedge clk)
	cpu_reset_n <= ~(reset | cpu_hold);

mc6809is cpu
(
	.CLK      (clk),
	.fallE_en (fallE),
	.fallQ_en (fallQ),
	.OP       (8'h00),
	.D        (din_r),
	.DOut     (cpu_dout),
	.ADDR     (cpu_addr),
	.RnW      (cpu_rnw),
	.BS       (),
	.BA       (),
	.nIRQ     (~snd_irq),
	.nFIRQ    (ym_irq_n),
	.nNMI     (1'b1),
	.AVMA     (),
	.BUSY     (),
	.LIC      (),
	.nHALT    (1'b1),
	.nRESET   (cpu_reset_n),
	.nDMABREQ (1'b1),
	.RegData  ()
);

//----------------------------------------------------------------------------
// Address decode
//----------------------------------------------------------------------------

wire a_ram   = (cpu_addr[15:13] == 3'b000);                      // 0000-1FFF
wire a_bank  = (cpu_addr[15:10] == 6'b001000);                   // 2000
wire a_ym    = (cpu_addr[15:10] == 6'b001001);                   // 2400
wire a_dac   = (cpu_addr[15:10] == 6'b001010);                   // 2800
wire a_oki   = (cpu_addr[15:10] == 6'b001011);                   // 2C00
wire a_cmd   = (cpu_addr[15:10] == 6'b001100);                   // 3000
wire a_okibk = (cpu_addr[15:10] == 6'b001101);                   // 3400
wire a_rom   = (cpu_addr[15:14] != 2'b00);                       // 4000-FFFF

// ROM byte offset from the start of the sound region in SDRAM (MAME region
// offset 0x10000): banks of 0x8000 at 4000-BFFF, the last 16 KB fixed above
wire [19:0] rom_off = (cpu_addr[15:14] == 2'b11) ? (20'h3C000 + {6'd0, cpu_addr[13:0]})
                                                 : ({2'd0, bank, 15'd0} + {4'd0, cpu_addr} - 20'h04000);

// hidden RAM window (MAME install_ram over the ROM)
reg  [7:0] pram [0:63];
reg  [7:0] pram_q;
wire [5:0] pram_a = 6'(cpu_addr - prot_start);
reg        pram_we;
wire       a_prot = (cpu_addr >= prot_start) && (cpu_addr <= prot_end);

//----------------------------------------------------------------------------
// RAMs
//----------------------------------------------------------------------------

reg  [7:0] ram [0:8191];
reg  [7:0] ram_q;
reg        ram_we;

always @(posedge clk) begin
	if (ram_we) ram[cpu_addr[12:0]] <= cpu_dout;
	ram_q <= ram[cpu_addr[12:0]];
end

always @(posedge clk) begin
	if (pram_we) pram[pram_a] <= cpu_dout;
	pram_q <= pram[pram_a];
end

//----------------------------------------------------------------------------
// Peripherals
//----------------------------------------------------------------------------

reg        ym_wr;
wire [7:0] ym_dout;
wire signed [15:0] ym_l, ym_r;

jt51 ym
(
	.rst     (reset),
	.clk     (clk),
	.cen     (fm_cen),
	.cen_p1  (fm_cen_p1),
	.cs_n    (~ym_wr),
	.wr_n    (~ym_wr),
	.a0      (cpu_addr[0]),
	.din     (cpu_dout),
	.dout    (ym_dout),
	.ct1     (),
	.ct2     (),
	.irq_n   (ym_irq_n),
	.sample  (),
	.left    (ym_l),
	.right   (ym_r),
	.xleft   (),
	.xright  ()
);

reg  [7:0] dac;                  // DAC latch

reg        oki_wr;
wire [7:0] oki_dout;
wire [17:0] oki_rom_a;
reg  [7:0] oki_rom_d;
reg        oki_rom_ok;
wire signed [13:0] oki_snd;

jt6295 #(.INTERPOL(0)) oki
(
	.rst      (reset),
	.clk      (clk),
	.cen      (oki_cen),
	.ss       (1'b1),
	.wrn      (~oki_wr),
	.din      (cpu_dout),
	.dout     (oki_dout),
	.rom_addr (oki_rom_a),
	.rom_data (oki_rom_d),
	.rom_ok   (oki_rom_ok),
	.sound    (oki_snd),
	.sample   ()
);

//----------------------------------------------------------------------------
// CPU bus cycle
//
// The address is stable from one E falling edge to the next. ROM reads are
// started once it has settled; everything else is answered from block RAM
// or registers. Side effects (writes, read-clear registers) happen once, on
// the clk before the E edge that ends the cycle.
//----------------------------------------------------------------------------

reg        rom_pending;
reg  [7:0] rom_byte;
reg  [2:0] rom_sel;

wire       addr_ok  = (ecnt == A_SETTLE);    // the new address has settled
wire       din_take = !din_ok && mem_ready && (ecnt > A_SETTLE) &&
                      ({1'b0, ecnt} + {3'd0, D_SETTLE} >= {1'b0, cyc_end});

always @(posedge clk) begin
	ym_wr      <= 1'b0;
	ram_we     <= 1'b0;
	pram_we    <= 1'b0;
	oki_wr     <= 1'b0;
	cmd_read   <= 1'b0;

	if (reset) begin
		rom_pending <= 1'b0;
		mem_ready   <= 1'b1;
		din_ok      <= 1'b0;
		rom_req     <= rom_ack;
		bank        <= 3'd0;
		oki_bank    <= 3'd0;
		dac         <= 8'h80;
	end
	else begin
		if (cmd_wr && !cmd_data[8])
			bank <= 3'd0;

		// read data for the E edge
		if (fallE)
			din_ok <= 1'b0;
		else if (din_take) begin
			din_r   <= cpu_din;
			din_ok  <= 1'b1;
			din_age <= 4'd0;
		end
		else if (din_ok && din_age != 4'd15)
			din_age <= din_age + 4'd1;

		// address settled: fetch ROM bytes from SDRAM
		if (addr_ok) begin
			if (cpu_rnw && a_rom && !a_prot) begin
				rom_addr    <= SND_BASE[24:3] + {5'd0, rom_off[19:3]};
				rom_sel     <= rom_off[2:0];
				rom_req     <= ~rom_req;
				rom_pending <= 1'b1;
				mem_ready   <= 1'b0;
			end
		end

		if (rom_pending && rom_req == rom_ack) begin
			rom_pending <= 1'b0;
			rom_byte    <= rom_data[{rom_sel, 3'b000} +: 8];
			mem_ready   <= 1'b1;
		end

		// last clk of the cycle: perform the access
		if (e_fire) begin
			if (!cpu_rnw && cpu_reset_n) begin
				if (a_prot)
					pram_we <= 1'b1;
				else if (a_ram)
					ram_we <= 1'b1;
				if (a_ym)    ym_wr    <= 1'b1;
				if (a_oki)   oki_wr   <= 1'b1;
				if (a_dac)   dac      <= cpu_dout;
				if (a_bank)  bank     <= cpu_dout[2:0];
				if (a_okibk) oki_bank <= cpu_dout[2:0];
			end
			else if (cpu_rnw && cpu_reset_n) begin
				if (a_cmd) cmd_read <= 1'b1;
			end
		end
	end
end

// read data (stable before the E edge)
always @(*) begin
	cpu_din = 8'hFF;
	if (a_prot)
		cpu_din = pram_q;
	else if (a_rom)
		cpu_din = rom_byte;
	else if (a_ram)
		cpu_din = ram_q;
	else if (a_ym)
		cpu_din = ym_dout;
	else if (a_oki)
		cpu_din = oki_dout;
	else if (a_cmd)
		cpu_din = cmd_latch;
end

//----------------------------------------------------------------------------
// OKI sample ROM: one cached SDRAM line
//
// Bank map (MAME): 0x00000-0x1FFFF banked, 0x20000-0x3FFFF fixed at 0x60000.
//----------------------------------------------------------------------------

// Every bank base is a multiple of 0x20000, so the offset is the bank's top
// three bits in front of the 17-bit sample address
reg   [2:0] oki_hi;
always @(*) begin
	case (oki_bank)
		3'd0, 3'd1: oki_hi = 3'b010;    // 0x40000
		3'd2:       oki_hi = 3'b001;    // 0x20000
		3'd3:       oki_hi = 3'b000;    // 0x00000
		3'd4:       oki_hi = 3'b111;    // 0xE0000
		3'd5:       oki_hi = 3'b110;    // 0xC0000
		3'd6:       oki_hi = 3'b101;    // 0xA0000
		default:    oki_hi = 3'b100;    // 0x80000
	endcase
end
wire [19:0] oki_off = {oki_rom_a[17] ? 3'b011 : oki_hi, oki_rom_a[16:0]};   // fixed half at 0x60000

reg  [16:0] oki_tag;
reg         oki_tag_ok;
reg  [63:0] oki_line;
reg         oki_busy;

always @(posedge clk) begin
	if (reset) begin
		oki_tag_ok <= 1'b0;
		oki_busy   <= 1'b0;
		oki_req    <= oki_ack;
	end
	else begin
		if (oki_busy) begin
			if (oki_req == oki_ack) begin
				oki_busy   <= 1'b0;
				oki_line   <= oki_data;
				oki_tag_ok <= 1'b1;
			end
		end
		else if (!(oki_tag_ok && oki_tag == oki_off[19:3])) begin
			oki_tag    <= oki_off[19:3];
			oki_tag_ok <= 1'b0;
			oki_addr   <= OKI_BASE[24:3] + {5'd0, oki_off[19:3]};
			oki_req    <= ~oki_req;
			oki_busy   <= 1'b1;
		end
	end
	oki_rom_d  <= oki_line[{oki_off[2:0], 3'b000} +: 8];
	oki_rom_ok <= oki_tag_ok && (oki_tag == oki_off[19:3]) && !oki_busy;
end

//----------------------------------------------------------------------------
// Mixer (MAME route gains): YM2151 0.10 per channel, DAC 0.10, OKI 0.15,
// doubled for level (x 512 / 256: 52, 52, 52, 77)
//
// One multiply or one sum per clock: the Y Unit core's four products and
// their sum in one clock were its worst timing path.
//----------------------------------------------------------------------------

wire signed [15:0] dac_s = {~dac[7], dac[6:0], 8'h00};
// OKI: jt6295 sums its four voices, 12 bits each, into 14 bits. MAME counts
// one voice at full volume as full scale (ADPCM value x volume / 2048), so
// one voice must reach +-32768 here: 4 bits up, 18 bits for four voices.
wire signed [17:0] oki_s = {oki_snd, 4'b0000};

reg signed [15:0] m_yl, m_yr, m_dac;
reg signed [17:0] m_oki;
reg signed [25:0] p_yl, p_yr, p_dac, p_oki;   // products
reg signed [25:0] s_ym, s_dk;                 // pair sums
reg signed [25:0] mix;
always @(posedge clk) begin
	// sources registered first: the YM2151 outputs come through its
	// log-to-linear conversion combinationally
	m_yl  <= ym_l;
	m_yr  <= ym_r;
	m_dac <= dac_s;
	m_oki <= oki_s;

	p_yl  <= 26'(m_yl)  * 26'sd52;
	p_yr  <= 26'(m_yr)  * 26'sd52;
	p_dac <= 26'(m_dac) * 26'sd52;
	p_oki <= 26'(m_oki) * 26'sd77;

	s_ym  <= p_yl + p_yr;
	s_dk  <= p_dac + p_oki;

	mix   <= s_ym + s_dk;

	if (mix > 26'sd8388352)
		audio <= 16'sd32767;
	else if (mix < -26'sd8388608)
		audio <= 16'sh8000;        // -32768 (written in hex: 32768 does not fit a 16-bit signed literal)
	else
		audio <= mix[23:8];
end

endmodule

//============================================================================
//  DCS Audio 2K board for the T-Unit (Mortal Kombat II)
//
//  The board as MAME models it (src/mame/shared/dcs.cpp, dcs_audio_2k_device,
//  REV_DCS1), around the ADSP-2105 core in rtl/dcs/adsp2105.sv (a port of
//  MAME's ADSP-21xx core):
//
//    Program memory   0000-03FF internal RAM (loaded by the boot), 0800-1FFF
//                     the 2K x 24 external RAM (mirrored three times), the
//                     rest reads 0.
//    Data memory      0000-1FFF the external RAM's upper 16 bits (mirrored),
//                     2000-2FFF the sound ROM bank (bank % 1536, 4K words, the
//                     ROM byte in bits 7-0, 0xFF above as MAME's ERASEFF
//                     region), 3000-33FF bank select (data & 0x7FF), 3400-37FF
//                     the host latches (read: input, acknowledged by the read;
//                     write: output), 3800-39FF internal RAM, 3FE0-3FFF the
//                     control registers, the rest reads 0.
//    Host             a write of the sound word: reset_w(bit 8) then
//                     data_w(bits 7-0): bit 8 low runs dcs_reset() and holds
//                     the CPU in reset, high releases it (device_reset); the
//                     data sets IRQ2 and the input latch. Status read: the
//                     latch control word (bit 11 input empty, bit 10 output
//                     empty), the 34010 sees it >> 4. Data read: the output
//                     latch, emptying it.
//    dcs_reset        bank 0, the control registers 0, IRQ0-2 cleared, both
//                     latches empty, the boot from bank 0, the timer off. As in
//                     MAME it leaves a running SPORT1 timer alone (with the
//                     autobuffer size and step at 0 it then only resets I0 and
//                     pulses IRQ1).
//    Boot             (byte 3 + 1) x 8 words from the 4K page of the bank, 4
//                     ROM bytes a word, into internal program RAM; at
//                     dcs_reset and when the program sets SYSCONTROL bit 9
//                     (then from the current bank, and the CPU is reset).
//    SPORT1           a TX1 write with SYSCONTROL bit 11 and S1_AUTOBUF bit 1
//                     set takes the autobuffer's I, M and L registers, aligns
//                     I to 16 words and starts a timer at half the buffer
//                     (L / (2 M) samples); each time it fires, that many words
//                     are read from data memory at I into the DAC queue, I
//                     advances, and when it passes the end of the buffer it
//                     goes back to the start and IRQ1 is pulsed (dcs_irq). The
//                     sample rate is 31.25 kHz, or 10 MHz / (2 (SCLKDIV + 1) x
//                     16) with S1_CONTROL bit 14. Clearing SYSCONTROL bit 11 or
//                     S1_AUTOBUF bit 1 stops it and empties the queue.
//    DAC              one queued sample per sample period, 0 when the queue is
//                     empty (MAME's dmadac).
//    Timer            MAME's model: scale, count and period registers, MSTAT's
//                     timer bit starts and stops it, the count register reads
//                     MAME's computed count, the first interrupt after
//                     scale x (count + 1) cycles and then every scale x
//                     (period + 1) while period > 10 or scale > 1, none when
//                     the timer vector holds the DRAM refresh stub.
//
//  Timing. The board steps on every second clock (ce, 48 MHz). A 10 MHz
//  cycle is 4.8 steps (5 / 24); the CPU is charged one cycle per instruction
//  against a debt the cycles pay off, may start the next instruction when
//  the debt is paid, and catches up (to -4096 cycles) time lost to SDRAM
//  waits and to the board's copies (boot pages, the DAC transfers, which
//  MAME does in no time); waiting in IDLE gives no credit. All the board's
//  timers count those 10 MHz cycles. Pause stops them and the CPU.
//
//  The sound ROMs are read 8 bytes at a time through a 64-line cache.
//  ROM packing (tools/tunit_layout.py): region word w is ROM byte
//  {w[22:20], w[18:0]} at 0xD00000 (six 512 KB windows; MAME's ROM_RELOAD
//  mirrors make bank bit 7 a mirror).
//
//  Every register of the board and the CPU changes only on ce edges (the SDC
//  declares two-cycle paths inside dcs_board); the inputs from the 96 MHz
//  side are captured on ce edges first.
//
//  Based on MAME's dcs.cpp, copyright Aaron Giles (BSD-3-Clause).
//  Copyright (C) 2026 Gm0rk - GPL-3.0-or-later
//============================================================================

module tunit_dcs
(
	input             clk,           // 96 MHz
	input             reset,         // board reset (and "not a DCS game")
	input             pause,         // hold the DSP, its timers and the DAC

	// host (34010) side
	input             cmd_wr,        // one pulse per write of the sound word
	input      [15:0] cmd_data,
	input             data_rd,       // one pulse per read of the data word
	output reg [15:0] status,        // control_r() >> 4
	output reg [15:0] rdata,         // data_r() & 0xff

	// SDRAM: packed sound ROMs
	output     [24:3] rom_addr,
	output            rom_req,       // toggle
	input             rom_ack,
	input      [63:0] rom_data,

	output signed [15:0] audio
);

reg ph = 1'b0;
always @(posedge clk) ph <= ~ph;

// host strobes, held as toggles for the board
reg [15:0] cmd_lat = 16'd0;
reg        cmd_tog = 1'b0, rd_tog = 1'b0;
always @(posedge clk) begin
	if (cmd_wr) begin cmd_lat <= cmd_data; cmd_tog <= ~cmd_tog; end
	if (data_rd) rd_tog <= ~rd_tog;
end

wire [15:0] b_latch, b_out;

dcs_board board
(
	.clk       (clk),
	.ce        (ph),
	.rst_in    (reset),
	.pause_in  (pause),
	.cmd_tog_in(cmd_tog),
	.cmd_in    (cmd_lat),
	.rd_tog_in (rd_tog),
	.latch_ctl (b_latch),
	.out_data  (b_out),
	.rom_addr  (rom_addr),
	.rom_req   (rom_req),
	.ack_in    (rom_ack),
	.data_in   (rom_data),
	.audio     (audio)
);

always @(posedge clk) begin
	status <= {4'h0, b_latch[15:4]};
	rdata  <= {8'h00, b_out[7:0]};
end

endmodule


//============================================================================
//  The board (ce domain)
//============================================================================

module dcs_board
(
	input             clk,
	input             ce,
	input             rst_in,
	input             pause_in,
	input             cmd_tog_in,
	input      [15:0] cmd_in,
	input             rd_tog_in,
	output reg [15:0] latch_ctl,
	output reg [15:0] out_data,
	output reg [24:3] rom_addr,
	output reg        rom_req,
	input             ack_in,
	input      [63:0] data_in,
	output reg signed [15:0] audio
);

localparam [21:0] DCS_LINE0 = 22'h1A0000;     // 0xD00000 / 8

// control register indexes (0x3FE0 + n)
localparam C_PFDATA = 5, C_PFCTL = 6, C_S1AUTO = 15, C_S1SCLK = 17, C_S1CTL = 18,
           C_TSCALE = 27, C_TCOUNT = 28, C_TPERIOD = 29, C_SYSCTL = 31;

//----------------------------------------------------------------------------
// Inputs, captured on ce edges
//----------------------------------------------------------------------------

reg        rst_i = 1'b1, pause_i = 1'b0, cmd_tog_i = 1'b0, rd_tog_i = 1'b0, ack_i = 1'b0;
reg [15:0] cmd_i = 16'd0;
reg [63:0] rom_i = 64'd0;
always @(posedge clk) if (ce) begin
	rst_i <= rst_in; pause_i <= pause_in;
	cmd_tog_i <= cmd_tog_in; cmd_i <= cmd_in; rd_tog_i <= rd_tog_in;
	ack_i <= ack_in; rom_i <= data_in;
end

//----------------------------------------------------------------------------
// 10 MHz cycles and the CPU's cycle debt
//----------------------------------------------------------------------------

reg  [4:0] t_acc = 5'd0;
reg        tick = 1'b0;
reg [31:0] cyc = 32'd0;          // 10 MHz cycles (MAME total_cycles)
always @(posedge clk) if (ce) begin
	tick <= 1'b0;
	if (rst_i) t_acc <= 5'd0;
	else if (!pause_i) begin
		if (t_acc >= 5'd19) begin t_acc <= t_acc - 5'd19; tick <= 1'b1; end
		else t_acc <= t_acc + 5'd5;
	end
	if (tick) cyc <= cyc + 32'd1;
end

localparam signed [15:0] DEBT_FLOOR = -16'sd4096;
reg  signed [15:0] debt = 16'sd0;
reg  signed [15:0] d_next;
wire        cpu_start, cpu_idle;
reg         host_rst = 1'b0;      // reset line from the host's last write
always @(posedge clk) if (ce) begin
	d_next = debt + (cpu_start ? 16'sd1 : 16'sd0) - (tick ? 16'sd1 : 16'sd0);
	if (d_next < DEBT_FLOOR) d_next = DEBT_FLOOR;
	if (cpu_idle && d_next < 16'sd0) d_next = 16'sd0;
	if (rst_i || host_rst) d_next = 16'sd0;     // the CPU is held: no time owed
	debt <= d_next;
end
wire go = (debt <= 16'sd0) && !pause_i;

//----------------------------------------------------------------------------
// State
//----------------------------------------------------------------------------

reg  [10:0] bank = 11'd0;              // m_sounddata_bank
reg         in_empty = 1'b1, out_empty = 1'b1;
reg  [15:0] in_data = 16'd0;
// m_control_regs: the ones the board uses live in registers, every one is
// kept in a small RAM for reading back (written since dcs_reset, else 0)
reg  [15:0] r_pfdata = 16'd0, r_pfctl = 16'd0, r_s1auto = 16'd0, r_s1sclk = 16'd0,
            r_s1ctl = 16'd0, r_tcount = 16'd0, r_sysctl = 16'd0;
reg  [15:0] ctlm [0:31];
reg  [15:0] ctlm_q;
reg  [31:0] ctl_v = 32'd0;
reg         ctl_vq = 1'b0;
reg  [15:0] progflags = 16'd0;
reg         cmd_seen = 1'b0, rd_seen = 1'b0;
reg         data_pend = 1'b0;          // data_w after reset_w
reg   [7:0] data_val = 8'd0;

always @(posedge clk) if (ce) latch_ctl <= {4'd0, in_empty, out_empty, 10'd0};

// boot
reg         boot_go = 1'b0;            // start a boot (restarts one in progress)
reg  [10:0] boot_bank = 11'd0;
reg   [2:0] bst = 3'd0;
wire        boot_busy = boot_go || (bst != 3'd0);
reg  [10:0] boot_words = 11'd0;        // words to load (pagelen, at most 1024)
reg   [8:0] boot_line = 9'd0;
reg  [63:0] boot_q = 64'd0;
reg         boot_we = 1'b0;
reg   [9:0] boot_wa = 10'd0;
reg  [23:0] boot_wd = 24'd0;

// CPU reset: the host's line, a board reset, a boot in progress
reg         sys_rst_pulse = 1'b0;      // SYSCONTROL bit 9 (pulse_input_line)
wire        cpu_reset = rst_i || host_rst || boot_busy || sys_rst_pulse;

// interrupt events to the CPU
reg   [2:0] e_irq_set = 3'd0, e_irq_clr = 3'd0;
reg         e_irq1_pulse = 1'b0, e_timer_pulse = 1'b0;

// I register side port and hold (DAC copies, timer arithmetic)
reg         sp_we = 1'b0;
reg   [2:0] sp_idx = 3'd0;
reg  [13:0] sp_val = 14'd0;
wire        hold_ack;
reg         dma_hold = 1'b0;
wire        t_busy;
reg         timer_en_d = 1'b0;
wire        timer_en;
wire        hold_req = dma_hold || t_busy || (timer_en != timer_en_d);

//----------------------------------------------------------------------------
// CPU
//----------------------------------------------------------------------------

wire [13:0] pm_a, dm_a;
wire        pm_we, dm_we, dm_rd, dm_rd_done;
wire [23:0] pm_wd;
wire [15:0] dm_wd;
reg  [23:0] pm_q;
reg  [15:0] dm_q;
reg         dm_rdy;
wire        tx1_wr;
wire [8*14-1:0] i_regs, l_regs, base_regs;
wire [8*16-1:0] m_regs;
wire        cpu_retire, cpu_irq;
wire [13:0] cpu_ppc;

wire        tx1_arm  = r_sysctl[11] && r_s1auto[1];

adsp2105 dsp
(
	.clk         (clk),
	.ce          (ce),
	.reset       (cpu_reset),
	.go          (go),
	.hold_req    (hold_req),
	.hold_ack    (hold_ack),
	.sp_we       (sp_we),
	.sp_idx      (sp_idx),
	.sp_val      (sp_val),
	.tx1_arm     (tx1_arm),
	.tx1_ireg    (r_s1auto[11:9]),
	.tx1_wr      (tx1_wr),
	.irq_set     (e_irq_set),
	.irq_clr     (e_irq_clr),
	.irq1_pulse  (e_irq1_pulse),
	.timer_pulse (e_timer_pulse),
	.pm_a        (pm_a),
	.pm_we       (pm_we),
	.pm_wd       (pm_wd),
	.pm_q        (pm_q),
	.dm_a        (dm_a),
	.dm_we       (dm_we),
	.dm_wd       (dm_wd),
	.dm_rd       (dm_rd),
	.dm_rd_done  (dm_rd_done),
	.dm_q        (dm_q),
	.dm_rdy      (dm_rdy),
	.start       (cpu_start),
	.idle        (cpu_idle),
	.timer_en    (timer_en),
	.i_regs      (i_regs),
	.m_regs      (m_regs),
	.l_regs      (l_regs),
	.base_regs   (base_regs),
	.retire      (cpu_retire),
	.ppc_o       (cpu_ppc),
	.irq_taken   (cpu_irq)
);

//----------------------------------------------------------------------------
// Memories
//----------------------------------------------------------------------------

// internal program RAM (1K x 24): the CPU, or the boot while it is in reset
reg  [23:0] ipm [0:1023];
reg  [23:0] ipm_q;
wire        ipm_we = boot_busy ? boot_we : (pm_we && pm_a[13:10] == 4'd0 && !cpu_reset);
wire  [9:0] ipm_a  = boot_busy ? boot_wa : pm_a[9:0];
wire [23:0] ipm_d  = boot_busy ? boot_wd : pm_wd;
always @(posedge clk) if (ce) begin
	if (ipm_we) ipm[ipm_a] <= ipm_d;
	ipm_q <= ipm[ipm_a];
end

// the timer vector's words (dcs.cpp reset_timer's DRAM refresh stub check)
reg   [4:0] stub = 5'd0;
always @(posedge clk) if (ce && ipm_we && ipm_a >= 10'h018 && ipm_a <= 10'h01C)
	case (ipm_a[2:0])
		3'd0: stub[0] <= (ipm_d == 24'h0C0030);   // 0x18 ENA SEC_REG
		3'd1: stub[1] <= (ipm_d == 24'h804828);   // 0x19 SI = DM($0482)
		3'd2: stub[2] <= (ipm_d == 24'h904828);   // 0x1A DM($0482) = SI
		3'd3: stub[3] <= (ipm_d == 24'h0C0020);   // 0x1B DIS SEC_REG
		default: stub[4] <= (ipm_d == 24'h0A001F);// 0x1C RTI
	endcase

// external RAM (2K x 24): bits 23-8 on two ports (program side, data side),
// bits 7-0 on the program side only
wire        pm_ext = (pm_a >= 14'h0800 && pm_a < 14'h2000);
wire [15:0] eph_qa, eph_qb;
reg   [7:0] epl [0:2047];
reg   [7:0] epl_q;
wire        ep_we_a = pm_we && pm_ext && !cpu_reset;
always @(posedge clk) if (ce) begin
	if (ep_we_a) epl[pm_a[10:0]] <= pm_wd[7:0];
	epl_q <= epl[pm_a[10:0]];
end

// data side address: the CPU, or the DAC copy while the CPU is held
reg         dma_act = 1'b0;
reg  [16:0] d_reg = 17'd0;             // reg (an int in MAME)
wire [13:0] dsa = dma_act ? d_reg[13:0] : dm_a;
wire        ds_ram = (dsa[13] == 1'b0);                        // 0000-1FFF
wire        ds_idm = (dsa[13:9] == 5'b11100);                  // 3800-39FF
wire        eph_we_b = !dma_act && dm_we && ds_ram;

dcs_tdp16 eph
(
	.clk   (clk),
	.ce    (ce),
	.a_a   (pm_a[10:0]),
	.a_we  (ep_we_a),
	.a_d   (pm_wd[23:8]),
	.a_q   (eph_qa),
	.b_a   (dsa[10:0]),
	.b_we  (eph_we_b),
	.b_d   (dm_wd),
	.b_q   (eph_qb)
);

// internal data RAM (512 x 16)
reg  [15:0] idm [0:511];
reg  [15:0] idm_q;
wire        idm_we = !dma_act && dm_we && ds_idm;
always @(posedge clk) if (ce) begin
	if (idm_we) idm[dsa[8:0]] <= dm_wd;
	idm_q <= idm[dsa[8:0]];
end

// program memory read data (by the region of the last address)
reg   [1:0] pm_rg = 2'd0;
always @(posedge clk) if (ce) pm_rg <= (pm_a[13:10] == 4'd0) ? 2'd1 : pm_ext ? 2'd2 : 2'd0;
always @* case (pm_rg)
	2'd1:    pm_q = ipm_q;
	2'd2:    pm_q = {eph_qa, epl_q};
	default: pm_q = 24'd0;
endcase

//----------------------------------------------------------------------------
// Sound ROM: line fetches and the cache
//----------------------------------------------------------------------------

// the bank's ROM line for a window offset: {window, bank[6:0], offset[11:3]}
reg  [10:0] bk_mod;
always @* bk_mod = (bank >= 11'd1536) ? bank - 11'd1536 : bank;
wire [18:0] win_line = {bk_mod[10:8], bk_mod[6:0], dm_a[11:3]};
wire [10:0] boot_mod = (boot_bank >= 11'd1536) ? boot_bank - 11'd1536 : boot_bank;

// line fetch engine (one SDRAM read at a time): the cache or the boot
reg         lf_busy = 1'b0;
reg         lf_done = 1'b0;
reg  [63:0] lf_data = 64'd0;
reg         lf_boot = 1'b0;            // the fetch is the boot's

// cache: 64 lines, index offset[8:3], tag {window, bank[6:0], offset[11:9]}
reg  [63:0] cdat [0:63];
reg  [12:0] ctag [0:63];
reg  [63:0] cval = 64'd0;
reg  [63:0] cdat_q;
reg  [12:0] ctag_q;
reg         c_we = 1'b0;
reg   [5:0] c_wa = 6'd0;
reg  [63:0] c_wd = 64'd0;
reg  [12:0] c_wt = 13'd0;
wire  [5:0] c_a = c_we ? c_wa : dm_a[8:3];
always @(posedge clk) if (ce) begin
	if (c_we) begin cdat[c_wa] <= c_wd; ctag[c_wa] <= c_wt; end
	cdat_q <= cdat[c_a];
	ctag_q <= ctag[c_a];
end
reg         fill_v = 1'b0;             // the last fill, for the read that waits on it
reg  [18:0] fill_line = 19'd0;
reg  [63:0] fill_q = 64'd0;

wire        win_rd   = dm_rd && (dm_a[13:12] == 2'b10);       // 2000-2FFF
wire        c_hit    = cval[dm_a[8:3]] && (ctag_q == win_line[18:6]) && !c_we;
wire        f_hit    = fill_v && (fill_line == win_line);
wire [63:0] win_q64  = f_hit ? fill_q : cdat_q;
wire  [7:0] win_byte = win_q64[dm_a[2:0]*8 +: 8];

//----------------------------------------------------------------------------
// Timer (dcs.cpp internal timer)
//----------------------------------------------------------------------------

reg         t_en = 1'b0, t_ign = 1'b0, t_run = 1'b0;
reg   [8:0] t_scale = 9'd1;
reg  [31:0] t_scnt = 32'd0;            // m_timer_start_count
reg  [15:0] t_per = 16'd0;
reg  [31:0] t_start = 32'd0;

// timer operations: update_timer_count (division), reset_timer
localparam T_IDLE = 3'd0, T_DIV1 = 3'd1, T_DIV2 = 3'd2, T_UPD = 3'd3, T_RESET = 3'd4, T_DONE = 3'd5;
reg   [2:0] tst = T_IDLE;
reg   [3:0] t_ops = 4'd0;              // pending: [0] update, [1] then apply, [2] reset, [3] read reply
reg   [1:0] t_apply = 2'd0;            // after the update: 0 none, 1 disable, 2 scale, 3 period
reg  [15:0] t_apply_v = 16'd0;
reg  [31:0] t_now = 32'd0;
reg  [31:0] dv_n = 32'd0, dv_q = 32'd0;
reg  [16:0] dv_d = 17'd0;
reg  [32:0] dv_r = 33'd0;
reg   [5:0] dv_i = 6'd0;
reg  [31:0] t_ec = 32'd0;
assign      t_busy = (tst != T_IDLE) || (t_ops != 4'd0);
reg  [31:0] t_accf = 32'd0;            // fired x scale x (period + 1)
wire [31:0] t_due  = t_start + ({23'd0, t_scale} * (t_scnt + 32'd1)) + t_accf;
reg         t_rd_done = 1'b0;          // a count read has its value

//----------------------------------------------------------------------------
// SPORT1 autobuffer and the DAC
//----------------------------------------------------------------------------

reg   [2:0] ab_ireg = 3'd0;            // m_ireg
reg  [15:0] ab_size = 16'd0, ab_incs = 16'd0, ab_base = 16'd0;
reg         ab_run = 1'b0;             // m_reg_timer
reg  [36:0] ab_acc = 37'd0, ab_t = 37'd0;
reg  [16:0] ab_step = 17'd0;
reg  [21:0] smp_cyc = 22'd0;           // sample period, 10 MHz cycles
reg  [21:0] slot_cnt = 22'd0;
reg         dac_en = 1'b0;             // dmadac enable
reg         dma_fire = 1'b0;

// DAC queue
reg  [15:0] fifo [0:2047];
reg  [10:0] f_wp = 11'd0, f_rp = 11'd0;
reg  [11:0] f_used = 12'd0, f_used_d = 12'd0, f_used_d2 = 12'd0;  // the RAM write lands a step later
reg  [15:0] f_q = 16'd0;
reg         f_push = 1'b0;
reg  [15:0] f_pd = 16'd0;
reg  [10:0] f_wa = 11'd0;
always @(posedge clk) if (ce) begin
	if (f_push) fifo[f_wa] <= f_pd;
	f_q <= fifo[f_rp];
end

// DAC copy (dcs_irq)
localparam D_IDLE = 3'd0, D_HOLD = 3'd1, D_READ = 3'd2, D_WRAP = 3'd4, D_REL = 3'd5;
reg   [2:0] dst = D_IDLE;
reg  [16:0] d_lim = 17'd0;             // 2 x incs x (i + 1)
reg  [16:0] d_inc2 = 17'd0;
reg         d_pend = 1'b0;             // a read in flight
reg         d_rram = 1'b0, d_ridm = 1'b0;

//----------------------------------------------------------------------------
// Data memory read data
//----------------------------------------------------------------------------

reg   [3:0] ds_rg = 4'd0;
localparam G_NONE = 4'd0, G_RAM = 4'd1, G_ROM = 4'd2, G_LATCH = 4'd3, G_IDM = 4'd4, G_CTL = 4'd5;
always @(posedge clk) if (ce)
	ds_rg <= (dsa[13] == 1'b0)               ? G_RAM :
	         (dsa[13:12] == 2'b10)           ? G_ROM :
	         (dsa[13:10] == 4'b1101)         ? G_LATCH :
	         (dsa[13:9]  == 5'b11100)        ? G_IDM :
	         (dsa[13:5]  == 9'b111111111)    ? G_CTL : G_NONE;

// the control register RAM (read at the decode step, as the others)
wire        ctl_we = dm_we && !dma_act && !cpu_reset && (dm_a[13:5] == 9'b111111111);
always @(posedge clk) if (ce) begin
	if (ctl_we) ctlm[dm_a[4:0]] <= dm_wd;
	ctlm_q <= ctlm[dm_a[4:0]];
	ctl_vq <= ctl_v[dm_a[4:0]];
end

reg  [15:0] ctl_rd;
always @* begin
	case (dm_a[4:0])
		5'(C_PFDATA):  ctl_rd = (r_pfctl & r_pfdata) | (progflags & ~r_pfctl);
		5'(C_PFCTL):   ctl_rd = r_pfctl;
		5'(C_S1AUTO):  ctl_rd = r_s1auto;
		5'(C_S1SCLK):  ctl_rd = r_s1sclk;
		5'(C_S1CTL):   ctl_rd = r_s1ctl;
		5'(C_TCOUNT):  ctl_rd = r_tcount;
		5'(C_SYSCTL):  ctl_rd = r_sysctl;
		default:       ctl_rd = ctl_vq ? ctlm_q : 16'd0;
	endcase
end

always @* begin
	dm_q = 16'd0; dm_rdy = 1'b1;
	case (ds_rg)
		G_RAM:   dm_q = eph_qb;
		G_ROM:   begin dm_q = {8'hFF, win_byte}; dm_rdy = c_hit || f_hit; end
		G_LATCH: dm_q = in_data;
		G_IDM:   dm_q = idm_q;
		G_CTL:   begin
			dm_q = ctl_rd;
			if (dm_a[4:0] == C_TCOUNT && t_en) dm_rdy = t_rd_done;
		end
		default: ;
	endcase
end

//----------------------------------------------------------------------------
// The board
//----------------------------------------------------------------------------

reg         dcs_reset;                 // dcs_reset() this step
reg         f_clr, f_do_push, f_do_pop;
reg  [15:0] f_val;
reg         b_req;                     // a boot request this step
reg  [10:0] b_req_bank;
reg   [4:0] c_off;
reg  [16:0] tmp17;
reg  [36:0] tmp37;

always @(posedge clk) if (ce) begin
	e_irq_set <= 3'd0; e_irq_clr <= 3'd0; e_irq1_pulse <= 1'b0; e_timer_pulse <= 1'b0;
	sp_we <= 1'b0; boot_we <= 1'b0; c_we <= 1'b0;
	sys_rst_pulse <= 1'b0;
	f_used_d <= f_used; f_used_d2 <= f_used_d;
	dcs_reset = 1'b0;
	f_clr = 1'b0; f_do_push = 1'b0; f_do_pop = 1'b0; f_val = 16'd0;
	b_req = 1'b0; b_req_bank = 11'd0;

	//------------------------------------------------------------------
	// Host
	//------------------------------------------------------------------
	if (data_pend) begin                       // data_w, after reset_w
		data_pend <= 1'b0;
		e_irq_set[2] <= 1'b1;
		in_empty  <= 1'b0;
		in_data   <= {8'd0, data_val};
	end
	if (cmd_tog_i != cmd_seen) begin
		cmd_seen <= cmd_tog_i;
		if (!cmd_i[8]) begin                   // reset_w(0): dcs_reset, hold the CPU
			host_rst  <= 1'b1;
			dcs_reset = 1'b1;
		end
		else host_rst <= 1'b0;                 // reset_w(1): release (device_reset)
		data_pend <= 1'b1;
		data_val  <= cmd_i[7:0];
	end
	if (rd_tog_i != rd_seen) begin             // data_r: auto-ack
		rd_seen   <= rd_tog_i;
		out_empty <= 1'b1;
	end

	//------------------------------------------------------------------
	// CPU data writes and read side effects
	//------------------------------------------------------------------
	if (dm_we && !dma_act && !cpu_reset) begin
		casez (dm_a)
			14'b11_00??_????_????: bank <= dm_wd[10:0];             // 3000-33FF
			14'b11_01??_????_????: begin                            // 3400-37FF
				out_data  <= dm_wd;
				out_empty <= 1'b0;
			end
			14'b11_1111_111?_????: begin                            // 3FE0-3FFF
				c_off = dm_a[4:0];
				for (int k = 0; k < 32; k = k + 1) if (5'(k) == c_off) ctl_v[k] <= 1'b1;
				case (c_off)
					5'(C_PFDATA): r_pfdata <= dm_wd;
					5'(C_PFCTL):  r_pfctl  <= dm_wd;
					5'(C_S1SCLK): r_s1sclk <= dm_wd;
					5'(C_S1CTL):  r_s1ctl  <= dm_wd;
					default: ;
				endcase
				case (c_off)
					C_SYSCTL: begin
						r_sysctl <= dm_wd;
						if (dm_wd[9]) begin                         // reboot from the current bank
							sys_rst_pulse <= 1'b1;
							b_req = 1'b1; b_req_bank = bank;
							r_sysctl <= 16'd0;
						end
						if (!dm_wd[11]) begin                       // SPORT1 off
							dac_en <= 1'b0; ab_run <= 1'b0; f_clr = 1'b1;
						end
					end
					C_S1AUTO: begin
						r_s1auto <= dm_wd;
						if (!dm_wd[1]) begin                        // autobuffer off
							dac_en <= 1'b0; ab_run <= 1'b0; f_clr = 1'b1;
						end
					end
					C_TSCALE: if ({1'b0, dm_wd[7:0]} + 9'd1 != t_scale) begin
						t_apply <= 2'd2; t_apply_v <= {7'd0, dm_wd[7:0] + 9'd1};
						t_ops <= 4'b0111; t_now <= cyc;
					end
					C_TCOUNT: begin
						r_tcount <= dm_wd;
						t_scnt <= {16'd0, dm_wd};
						t_ops <= 4'b0100; t_now <= cyc;
					end
					C_TPERIOD: if (dm_wd != t_per) begin
						t_apply <= 2'd3; t_apply_v <= dm_wd;
						t_ops <= 4'b0111; t_now <= cyc;
					end
					default: ;
				endcase
			end
			default: ;
		endcase
	end
	if (dm_rd_done && !cpu_reset) begin
		if (dm_a[13:10] == 4'b1101) begin                           // input latch: auto-ack
			in_empty <= 1'b1;
			e_irq_clr[2] <= 1'b1;
		end
		if (dm_a == 14'h3FE5) progflags <= progflags ^ 16'h0006;
		if (dm_a == 14'h3FFC) t_rd_done <= 1'b0;
	end
	// a count read while the timer runs: update_timer_count first
	if (dm_rd && dm_a == 14'h3FFC && t_en && !t_rd_done && t_ops == 4'd0 && tst == T_IDLE) begin
		t_ops <= 4'b1001; t_apply <= 2'd0; t_now <= cyc;
	end

	//------------------------------------------------------------------
	// SPORT1 transmit (sound_tx_callback), with the I register aligned
	//------------------------------------------------------------------
	if (tx1_wr) begin
		if (r_sysctl[11] && r_s1auto[1]) begin
			ab_ireg <= r_s1auto[11:9];
			ab_base <= {2'd0, i_regs[r_s1auto[11:9]*14 +: 14]};
			ab_size <= {2'd0, l_regs[r_s1auto[11:9]*14 +: 14]};
			tmp17   = {1'b0, m_regs[{r_s1auto[11], r_s1auto[8:7]}*16 +: 16]};
			ab_incs <= tmp17[15:0];
			// recompute_sample_rate
			smp_cyc <= r_s1ctl[14] ? 22'(({6'd0, r_s1sclk} + 22'd1) << 5) : 22'd320;
			dac_en  <= 1'b1;
			if (tmp17[15:0] != 16'd0) begin
				ab_run  <= 1'b1;
				ab_acc  <= 37'd0;
				ab_step <= {tmp17[15:0], 1'b0};
				tmp37   = (r_s1ctl[14] ? 37'(({6'd0, r_s1sclk} + 22'd1) << 5) : 37'd320)
				          * {23'd0, l_regs[r_s1auto[11:9]*14 +: 14]};
				ab_t    <= tmp37;
			end
			slot_cnt <= r_s1ctl[14] ? 22'(({6'd0, r_s1sclk} + 22'd1) << 4) : 22'd160;
		end
		else begin
			dac_en <= 1'b0; ab_run <= 1'b0; f_clr = 1'b1;
		end
	end

	// the half-buffer timer
	if (tick && ab_run) begin
		if (ab_acc + {20'd0, ab_step} >= ab_t) begin
			ab_acc   <= ab_acc + {20'd0, ab_step} - ab_t;
			dma_fire <= 1'b1;
		end
		else ab_acc <= ab_acc + {20'd0, ab_step};
	end

	// DAC: one sample per period, 0 when the queue is empty
	if (tick && smp_cyc != 22'd0) begin
		if (slot_cnt == 22'd0) begin
			slot_cnt <= smp_cyc - 22'd1;
			if (f_used_d2 != 12'd0 && f_used != 12'd0) begin
				audio <= f_q;
				f_do_pop = 1'b1;
			end
			else audio <= 16'sd0;
		end
		else slot_cnt <= slot_cnt - 22'd1;
	end

	//------------------------------------------------------------------
	// DAC copy (dcs_irq), with the CPU held at a boundary
	//------------------------------------------------------------------
	case (dst)
		D_IDLE: if (dma_fire) begin
			dma_fire <= 1'b0;
			dma_hold <= 1'b1;
			dst <= D_HOLD;
		end
		D_HOLD: if (hold_ack) begin
			dma_act <= 1'b1;
			d_reg   <= {3'd0, i_regs[ab_ireg*14 +: 14]};
			d_inc2  <= (ab_incs == 16'd0) ? 17'd2 : {ab_incs, 1'b0};
			d_lim   <= (ab_incs == 16'd0) ? 17'd2 : {ab_incs, 1'b0};
			d_pend  <= 1'b0;
			dst <= D_READ;
		end
		D_READ: begin
			// the previous read's data (MAME: buffer[i] = read_word(reg));
			// the board's RAMs, 0 elsewhere
			if (d_pend && dac_en) begin
				f_do_push = 1'b1;
				f_val = d_rram ? eph_qb : d_ridm ? idm_q : 16'd0;
			end
			if (d_lim <= {1'b0, ab_size}) begin                     // i < count: read at reg
				d_rram <= (d_reg[13] == 1'b0);
				d_ridm <= (d_reg[13:9] == 5'b11100);
				d_pend <= 1'b1;
				d_reg  <= d_reg + {1'b0, ab_incs};
				d_lim  <= d_lim + d_inc2;
			end
			else begin
				d_pend <= 1'b0;
				dma_act <= 1'b0;
				dst <= D_WRAP;
			end
		end
		D_WRAP: begin
			ab_base <= {2'd0, base_regs[ab_ireg*14 +: 14]};
			sp_we  <= 1'b1;
			sp_idx <= ab_ireg;
			if (d_reg >= {3'd0, base_regs[ab_ireg*14 +: 14]} + {1'b0, ab_size}) begin
				sp_val <= base_regs[ab_ireg*14 +: 14];
				e_irq1_pulse <= 1'b1;
			end
			else sp_val <= d_reg[13:0];
			dst <= D_REL;
		end
		default: begin                                              // D_REL
			dma_hold <= 1'b0;
			dst <= D_IDLE;
		end
	endcase

	//------------------------------------------------------------------
	// Timer
	//------------------------------------------------------------------
	timer_en_d <= timer_en;
	if (timer_en != timer_en_d) begin              // timer_enable_callback
		if (timer_en) begin t_en <= 1'b1; t_ops <= 4'b0100; t_now <= cyc; end
		else begin t_apply <= 2'd1; t_ops <= 4'b0011; t_now <= cyc; end
	end

	// interrupts when the target cycle is reached
	if (tick && t_run && cyc == t_due) begin
		e_timer_pulse <= 1'b1;
		t_accf <= t_accf + ({23'd0, t_scale} * ({16'd0, t_per} + 32'd1));
		if (t_ign || !(t_per > 16'd10 || t_scale > 9'd1)) t_run <= 1'b0;
	end

	case (tst)
		T_IDLE: begin
			if (t_ops[0]) begin                              // update_timer_count
				t_ops[0] <= 1'b0;
				if (t_en) begin
					dv_n <= t_now - t_start; dv_d <= {8'd0, t_scale}; dv_q <= 32'd0;
					dv_r <= 33'd0; dv_i <= 6'd32;
					tst <= T_DIV1;
				end
			end
			else if (t_ops[1]) begin                         // then: disable / scale / period
				t_ops[1] <= 1'b0;
				case (t_apply)
					2'd1: begin t_en <= 1'b0; t_run <= 1'b0; end
					2'd2: t_scale <= t_apply_v[8:0];
					2'd3: t_per <= t_apply_v;
					default: ;
				endcase
			end
			else if (t_ops[2]) begin                         // reset_timer
				t_ops[2] <= 1'b0;
				if (t_en) begin
					t_start <= t_now;
					t_accf  <= 32'd0;
					if (!t_ign && stub == 5'b11111) t_ign <= 1'b1;
					else if (!t_ign) t_run <= 1'b1;
				end
			end
			else if (t_ops[3]) begin                         // a count read gets its value
				t_ops[3] <= 1'b0;
				t_rd_done <= 1'b1;
			end
		end
		T_DIV1, T_DIV2: begin                                // restoring division
			if (dv_i != 6'd0) begin
				tmp37 = {dv_r[31:0], dv_n[31]};
				dv_n  <= {dv_n[30:0], 1'b0};
				if (tmp37[32:0] >= {16'd0, dv_d}) begin
					dv_r <= tmp37[32:0] - {16'd0, dv_d};
					dv_q <= {dv_q[30:0], 1'b1};
				end
				else begin
					dv_r <= tmp37[32:0];
					dv_q <= {dv_q[30:0], 1'b0};
				end
				dv_i <= dv_i - 6'd1;
			end
			else if (tst == T_DIV1) begin
				// elapsed_clocks = elapsed / scale
				if (dv_q < t_scnt + 32'd1) begin
					t_scnt <= t_scnt - dv_q;
					r_tcount <= 16'(t_scnt - dv_q);
					tst <= T_IDLE;
				end
				else begin
					dv_n <= dv_q - (t_scnt + 32'd1); dv_d <= {1'b0, t_per} + 17'd1;
					dv_q <= 32'd0; dv_r <= 33'd0; dv_i <= 6'd32;
					tst <= T_DIV2;
				end
			end
			else begin
				// the remainder of the periods
				t_scnt <= {16'd0, t_per} - dv_r[31:0];
				r_tcount <= 16'(t_per - dv_r[15:0]);
				tst <= T_IDLE;
			end
		end
		default: tst <= T_IDLE;
	endcase

	//------------------------------------------------------------------
	// dcs_reset (host write with bit 8 low, board reset)
	//------------------------------------------------------------------
	if (dcs_reset || rst_i) begin
		bank <= 11'd0;
		ab_size <= 16'd0; ab_incs <= 16'd0; ab_ireg <= 3'd0;
		ctl_v <= 32'd0;
		r_pfdata <= 16'd0; r_pfctl <= 16'd0; r_s1auto <= 16'd0; r_s1sclk <= 16'd0;
		r_s1ctl <= 16'd0; r_tcount <= 16'd0; r_sysctl <= 16'd0;
		e_irq_clr <= 3'b111;
		in_empty <= 1'b1; out_empty <= 1'b1;
		b_req = 1'b1; b_req_bank = 11'd0;
		t_ign <= 1'b0; t_en <= 1'b0; t_scale <= 9'd1; t_run <= 1'b0;
		t_ops <= 4'd0; tst <= T_IDLE; t_rd_done <= 1'b0;
	end

	//------------------------------------------------------------------
	// Boot loader (load_boot_data): lines of the bank's page
	//------------------------------------------------------------------
	case (bst)
		3'd0: if (boot_go && !rst_i && !lf_busy) begin
			boot_go   <= 1'b0;
			boot_line <= 9'd0;
			bst <= 3'd1;
		end
		3'd1: if (!lf_busy) bst <= 3'd2;                         // fetch a line (below)
		3'd2: if (lf_done && lf_boot) begin
			boot_q <= lf_data;
			if (boot_line == 9'd0)
				boot_words <= (({3'd0, lf_data[31:24]} + 11'd1) << 3) > 11'd1024 ? 11'd1024
				              : (({3'd0, lf_data[31:24]} + 11'd1) << 3);
			bst <= 3'd3;
		end
		3'd3: begin                                              // word 2L: bytes 0-2
			boot_we <= 1'b1; boot_wa <= {boot_line, 1'b0};
			boot_wd <= {boot_q[7:0], boot_q[15:8], boot_q[23:16]};
			bst <= 3'd4;
		end
		3'd4: begin                                              // word 2L+1: bytes 4-6
			boot_we <= 1'b1; boot_wa <= {boot_line, 1'b1};
			boot_wd <= {boot_q[39:32], boot_q[47:40], boot_q[55:48]};
			if ({1'b0, boot_line, 1'b0} + 11'd2 >= boot_words) bst <= 3'd0;
			else begin boot_line <= boot_line + 9'd1; bst <= 3'd1; end
		end
		default: bst <= 3'd0;
	endcase
	if (b_req) begin                                              // (re)start a boot
		boot_go <= 1'b1;
		boot_bank <= b_req_bank;
		if (bst != 3'd2) bst <= 3'd0;
	end
	else if (boot_go && bst != 3'd0 && bst != 3'd2) bst <= 3'd0;

	//------------------------------------------------------------------
	// Line fetches: the boot's, or a cache fill for the waiting CPU read
	//------------------------------------------------------------------
	lf_done <= 1'b0;
	if (!lf_busy) begin
		if (bst == 3'd2 && !lf_done) begin
			rom_addr <= DCS_LINE0 + {3'd0, boot_mod[10:8], boot_mod[6:0], boot_line};
			rom_req  <= ~rom_req;
			lf_busy  <= 1'b1; lf_boot <= 1'b1;
		end
		else if (win_rd && !c_hit && !f_hit && !cpu_reset && !lf_done) begin
			rom_addr <= DCS_LINE0 + {3'd0, win_line};
			rom_req  <= ~rom_req;
			lf_busy  <= 1'b1; lf_boot <= 1'b0;
			fill_line <= win_line;
			fill_v    <= 1'b0;
		end
	end
	else if (ack_i == rom_req) begin
		lf_busy <= 1'b0;
		lf_done <= 1'b1;
		lf_data <= rom_i;
		if (!lf_boot) begin
			c_we <= 1'b1; c_wa <= fill_line[5:0]; c_wd <= rom_i; c_wt <= fill_line[18:6];
			for (int k = 0; k < 64; k = k + 1) if (6'(k) == fill_line[5:0]) cval[k] <= 1'b1;
			fill_q <= rom_i;
			fill_v <= 1'b1;
		end
	end

	//------------------------------------------------------------------
	// DAC queue (MAME keeps BUFFER_SIZE - 1 samples; this one 2047)
	//------------------------------------------------------------------
	f_push <= f_do_push && !f_clr && (f_used != 12'd2047 || f_do_pop);
	f_pd   <= f_val;
	f_wa   <= f_wp;
	if (f_clr) begin
		f_wp <= 11'd0; f_rp <= 11'd0; f_used <= 12'd0;
	end
	else begin
		if (f_do_push && (f_used != 12'd2047 || f_do_pop)) f_wp <= f_wp + 11'd1;
		if (f_do_pop) f_rp <= f_rp + 11'd1;
		f_used <= f_used + ((f_do_push && (f_used != 12'd2047 || f_do_pop)) ? 12'd1 : 12'd0)
		                 - (f_do_pop ? 12'd1 : 12'd0);
	end

	//------------------------------------------------------------------
	// Board reset: power-up state
	//------------------------------------------------------------------
	if (rst_i) begin
		host_rst <= 1'b0;
		data_pend <= 1'b0;
		cmd_seen <= cmd_tog_i; rd_seen <= rd_tog_i;
		cval <= 64'd0; fill_v <= 1'b0;
		dac_en <= 1'b0; ab_run <= 1'b0; dma_fire <= 1'b0;
		f_wp <= 11'd0; f_rp <= 11'd0; f_used <= 12'd0;
		smp_cyc <= 22'd0; slot_cnt <= 22'd0;
		audio <= 16'sd0;
		dst <= D_IDLE; dma_hold <= 1'b0; dma_act <= 1'b0;
		progflags <= 16'd0;
	end
end

endmodule


//============================================================================
//  2K x 16 true dual-port RAM (one clock, clock enable)
//============================================================================

module dcs_tdp16
(
	input             clk,
	input             ce,
	input      [10:0] a_a,
	input             a_we,
	input      [15:0] a_d,
	output reg [15:0] a_q,
	input      [10:0] b_a,
	input             b_we,
	input      [15:0] b_d,
	output reg [15:0] b_q
);

reg [15:0] mem [0:2047] /*verilator public_flat_rd*/;

always @(posedge clk) if (ce) begin
	if (a_we) begin mem[a_a] <= a_d; a_q <= a_d; end
	else a_q <= mem[a_a];
end

always @(posedge clk) if (ce) begin
	if (b_we) begin mem[b_a] <= b_d; b_q <= b_d; end
	else b_q <= mem[b_a];
end

endmodule

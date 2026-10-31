//============================================================================
//  Williams/Midway T-Unit CPU board
//
//  TMS34010 plus everything on its local bus (MAME midtunit.cpp main_map;
//  34010 bit addresses, unmapped reads return 0xFFFF as in MAME):
//    0x00000000-0x003FFFFF  frame store (VRAM, in DDR3), entries 0-0x7FFFF
//    0x01000000-0x013FFFFF  main RAM, 512 KB (SDRAM, through a cache)
//    0x01400000-0x0141FFFF  CMOS, 16 KB
//    0x01480000-0x014FFFFF  W: CMOS write enable (MAME ignores it)
//    0x01600000-0x0160003F  IN0, IN1, IN2, DSW
//    0x01800000-0x0187FFFF  palette RAM, 32768 x xRGB 5-5-5
//    0x01A80000-0x01A800FF  DMA blitter registers
//    0x01B00000-0x01B0001F  W: control register (unless a protection uses it)
//    0x01D00000-0x01D0001F  R: sound status
//    0x01D01020-0x01D0103F  sound data (writes at 0x01D01030)
//    0x01D81060-0x01D8107F  W: watchdog (MAME's never fires)
//    0x01F00000-0x01F0001F  W: control register
//    0x02000000-0x07FFFFFF  graphics ROM read-back, two 4 MB windows
//    0x1F800000-0x1FFFFFFF  program ROM mirror (MK)
//    0xFF800000-0xFFFFFFFF  program ROM, 1 MB (SDRAM, through a cache)
//  plus each game's protection (MAME midtunit_m.cpp init_*), which takes
//  priority over the map above where they overlap, and the OSD's read
//  patches (secrets), which take priority over everything for CPU reads.
//
//  Control register: bit 5 selects whether CPU VRAM accesses reach the pixel
//  bytes (1) or the palette bytes (0); bit 7 banks the top 4 MB of the
//  graphics ROM on MK2's large-ROM board.
//
//  Memories:
//    SDRAM  program ROM 0x000000, graphics 0x100000, sound 0xD00000,
//           main RAM 0x1000000 (byte addresses)
//    DDR3   frame store
//    BRAM   CMOS, palette, the ROM and RAM caches, line and row buffers
//
//  Main RAM is 512 KB, too much for block RAM beside everything else. It is
//  kept in SDRAM behind a 32 KB direct-mapped cache of 8-byte lines: reads
//  that hit take two clocks, a miss fetches one line. Writes go through the
//  cache (updating a line that is present) into a small queue of SDRAM word
//  writes; a miss waits for the queue to empty first, so a line is never
//  fetched with a write to it still pending. The program ROM has its own
//  16 KB cache as on the Y Unit. The 34010 core charges MAME's cycle counts
//  and pays them off against the real time taken, so memory latency only
//  matters when it runs longer than the instruction's own time.
//
//  Derived from the Y Unit core's midway_yunit.sv.
//
//  Copyright (C) 2026 Gm0rk - GPL-3.0-or-later
//============================================================================

module midway_tunit
(
	input             clk,           // 96 MHz
	input             reset,
	input             pause,
	input             vtiming,       // MiSTer option: 0 native frame (54.7 Hz), 1 277 lines
	                                 // (57.1 Hz); see "Video timing"

	// game configuration
	input       [2:0] prot_id,       // protection (P_* below)
	input             mk_turbo,      // MK Turbo Ninja: counter GAL at 0xFFFFF400
	input             big_rom,       // MK2: large graphics ROM (control bit 7 banks it)
	input             dcs,           // DCS sound board (MK2), else the ADPCM board
	input       [3:0] gfx_mb,        // graphics ROM loaded, MB (reads above return 0)

	// main RAM clear after a ROM load (toggle); the CPU waits until done
	input             ram_clr_req,

	// inputs (active low as the CPU reads them): IN0, IN1, IN2, DSW
	input      [63:0] in_ports,

	// read patches: entries 0-7 from tunit_secrets.sv (OSD secrets), 8-15 from
	// tunit_cheats.sv (OSD cheats): word addresses and values, enables
	input     [447:0] pt_addr,       // 16 x 28-bit word addresses: 8 OSD secrets, 8 cheats
	input     [255:0] pt_data,
	input      [15:0] pt_en,
	input      [15:0] pt_fetch,      // entry applies to instruction fetches only (program code)
	input      [15:0] pt_store,      // entry also replaces the value the CPU writes to the word (main RAM)

	// Fixed AI Difficulty (MK, MK2): while lvl_on, the CPU's reads of the
	// game's AI level word return lvl_val (see "Read patches")
	input             lvl_on,
	input      [27:0] lvl_addr,      // the level word's word address (bit address >> 4)
	input       [3:0] lvl_val,       // 0 (easiest) to 9

	// sound board
	output reg        snd_wr,        // one pulse per write of the sound data word
	output reg [15:0] snd_data,
	output reg        snd_rd,        // one pulse per read of the sound data (DCS)
	input      [15:0] snd_status,    // DCS: status word the CPU reads
	input      [15:0] snd_rdata,     // DCS: data word the CPU reads

	// SDRAM: CPU lines (program ROM, graphics read-back, main RAM)
	output reg [24:3] cpu_sd_addr,
	output reg        cpu_sd_req,
	input             cpu_sd_ack,
	input      [63:0] cpu_sd_data,

	// SDRAM: blitter source lines
	output reg [24:3] dma_sd_addr,
	output reg        dma_sd_req,
	input             dma_sd_ack,
	input      [63:0] dma_sd_data,

	// SDRAM: main RAM word writes
	output reg [24:1] ram_wr_addr,
	output reg [15:0] ram_wr_data,
	output reg        ram_wr_req,
	input             ram_wr_ack,

	// DDR3 (VRAM)
	input             ddr_busy,
	output      [7:0] ddr_burstcnt,
	output     [28:0] ddr_addr,
	input      [63:0] ddr_dout,
	input             ddr_dout_ready,
	output            ddr_rd,
	output     [63:0] ddr_din,
	output      [7:0] ddr_be,
	output            ddr_we,

	// CMOS access for NVRAM load/save (word address, 8 K words)
	input      [12:0] nv_addr,
	input             nv_we,
	input      [15:0] nv_din,
	output     [15:0] nv_dout,
	output            cmos_write,    // the game wrote its CMOS (NVRAM needs saving)

	// video
	output            ce_pix,
	output      [7:0] vid_r,
	output      [7:0] vid_g,
	output      [7:0] vid_b,
	output            vid_hs,
	output            vid_vs,
	output            vid_hb,
	output            vid_vb,

	// debug: simulation logs; in the core dbg_rd and dbg_wa also tell the
	// secrets module when the CPU reaches a hidden menu (the rest unconnected)
	output     [31:0] dbg_pc,
	output            dbg_retire,
	output            dbg_blit_busy,
	output            dbg_wr,        // one pulse per CPU write as it completes
	output            dbg_rd,        // one pulse per CPU read as it completes
	output     [27:0] dbg_wa,        // its word address (bit address >> 4)
	output     [15:0] dbg_wdata,
	output     [15:0] dbg_rdata,
	output            dbg_ie         // the CPU's interrupt enable with them (simulation: --rdhist)
);

// SDRAM byte addresses of the regions
localparam [24:0] ROM_BASE = 25'h000_0000;
localparam [24:0] GFX_BASE = 25'h010_0000;
localparam [24:0] RAM_BASE = 25'h100_0000;

//----------------------------------------------------------------------------
// Clock enables
//
// Everything runs from one 24-step phase counter at 96 MHz:
//  - cpu_ce enables the 34010's logic on every other clock (48 MHz). Its
//    paths are constrained as two-cycle paths in the SDC.
//  - ce_cyc is the 34010 machine cycle, 50 MHz / 8 = 6.25 MHz, from a
//    fractional divider stepped at 48 MHz, so it always falls in a cpu_ce
//    cycle (faster with the shorter video frames, see "Video timing").
//  - VCLK is 4 MHz (96 / 24) and the pixel clock 8 MHz, both aligned to
//    cpu_ce cycles.
// Each enable is registered from the phase it will be high in.
//----------------------------------------------------------------------------

reg   [4:0] ph;
reg         cpu_ce, ce_vclk, ce_pix_r;
always @(posedge clk) begin
	ph       <= (ph == 5'd23) ? 5'd0 : ph + 5'd1;
	cpu_ce   <= ph[0];                               // next phase is even
	ce_vclk  <= (ph == 5'd23);                       // next phase 0
	ce_pix_r <= (ph == 5'd23) || (ph == 5'd11);      // next phase 0 or 12
end
assign ce_pix = ce_pix_r;

//----------------------------------------------------------------------------
// Video timing (MiSTer option for 15 kHz TVs)
//
// Every game runs a 289-line frame at 15.81 kHz: 54.7 Hz, which some TVs do
// not hold well. The shorter frame drops blank lines in the 34010's CRT
// controller (see tms34010.sv): 277 lines for 57.1 Hz. The games count time
// in frames, so they run 289/277 (+4.3 %) faster; the CPU's machine cycle
// and the blitter's completion time are sped up by the same ratio, so a
// frame still gets the real board's cycles. The sound boards keep their own
// clocks.
//----------------------------------------------------------------------------

reg   [9:0] frame_lines;
always @(posedge clk)
	frame_lines <= vtiming ? 10'd277 : 10'd0;

// step (6.25 MHz in kHz, times 289/277 for the shorter frame) and the level
// at which a step wraps, so the accumulator update is one add or subtract
// and one compare
reg  [16:0] cyc_step, cyc_thr;
always @(posedge clk) begin
	cyc_step <= vtiming ? 17'd6521 : 17'd6250;   // 57 Hz : native
	cyc_thr  <= 17'd48000 - cyc_step;
end

// blitter completion time: one extra count off its timer at 289/277 - 1 of
// the clocks (16-bit fraction)
reg  [15:0] dma_frac, dma_fstep;
reg         dma_fast;
always @(posedge clk) begin
	dma_fstep <= vtiming ? 16'd2839 : 16'd0;
	{dma_fast, dma_frac} <= {1'b0, dma_frac} + {1'b0, dma_fstep};
end

// steps of 6.25 MHz out of 48 MHz: acc + step >= 48000 is acc >= 48000 - step,
// and acc + step - 48000 is acc - (48000 - step)
reg  [16:0] cyc_acc;
reg         ce_cyc;
always @(posedge clk) begin
	ce_cyc <= 1'b0;
	if (reset)
		cyc_acc <= 17'd0;
	else if (ph[0]) begin
		if (cyc_acc >= cyc_thr) begin
			cyc_acc <= cyc_acc - cyc_thr;
			ce_cyc  <= ~pause;
		end
		else
			cyc_acc <= cyc_acc + cyc_step;
	end
end

//----------------------------------------------------------------------------
// CPU reset
//
// The 34010 (and with it the raster, which its CRT controller generates) is
// held in reset while the board gets its memories ready:
//  - after every reset both caches are cleared by walking their 4096 lines
//    (c_clr, in the bus state machine below). Holding the CPU until then
//    makes it start together with its raster, as in MAME; starting it at
//    once left it waiting ~270 machine cycles for its reset vector while the
//    raster ran, a phase difference that shows up as input and interrupt
//    timing in timing-sensitive games (Judge Dredd).
//  - after a ROM load the main RAM is zeroed through the write queue
//    (clr_busy).
//----------------------------------------------------------------------------

reg         clr_busy = 1'b0;
reg         clr_seen = 1'b0;
reg  [17:0] clr_addr;
reg         c_clr = 1'b1;                // walking the caches
reg  [11:0] c_clr_a = 12'd0;
wire        cpu_reset = reset | clr_busy | c_clr;

//----------------------------------------------------------------------------
// TMS34010
//----------------------------------------------------------------------------

wire [27:0] mem_addr;
wire [31:0] mem_baddr;
wire        mem_rd, mem_wr, mem_srt;
wire [15:0] mem_wdata;
reg  [15:0] mem_rdata;
reg         mem_ack;
wire [15:0] cpu_rdata;           // mem_rdata, or a read patch's value

wire        cpu_hs, cpu_vs, cpu_hb, cpu_vb, disp_en;
wire  [9:0] hcount, vcount, heblnk, hsblnk, cpu_vsblnk;
wire        line_start, line_vis;
wire [11:0] line_row;
wire [13:0] line_col;
wire        dma_irq;
wire [31:0] cpu_pc;
wire [31:0] cpu_st;
wire        cpu_retire;

tms34010 cpu
(
	.clk        (clk),
	.ce         (cpu_ce),
	.reset      (cpu_reset),
	.ce_cyc     (ce_cyc),
	.ce_vclk    (ce_vclk),
	.pause      (pause),
	.frame_lines(frame_lines),

	.mem_addr   (mem_addr),
	.mem_baddr  (mem_baddr),
	.mem_rd     (mem_rd),
	.mem_wr     (mem_wr),
	.mem_srt    (mem_srt),
	.mem_wdata  (mem_wdata),
	.mem_rdata  (cpu_rdata),
	.mem_ack    (mem_ack),

	.int1       (dma_irq),
	.int2       (1'b0),

	.hsync      (cpu_hs),
	.vsync      (cpu_vs),
	.hblank     (cpu_hb),
	.vblank     (cpu_vb),
	.hcount     (hcount),
	.vcount     (vcount),
	.heblnk     (heblnk),
	.hsblnk     (hsblnk),
	.vsblnk     (cpu_vsblnk),
	.disp_en    (disp_en),
	.line_start (line_start),
	.line_vis   (line_vis),
	.line_row   (line_row),
	.line_col   (line_col),

	.dbg_pc     (cpu_pc),
	.dbg_st     (cpu_st),
	.dbg_retire (cpu_retire),
	.dbg_cycles ()
);

assign dbg_pc = cpu_pc;

// CPU pulses last two clocks (one cpu_ce period); count them once
assign dbg_retire = cpu_retire & cpu_ce;

// an access completes on the cpu_ce edge that takes its acknowledge; the
// CPU's own address and data (and the read data it takes) are on the bus then
assign dbg_wr    = cpu_ce & mem_ack & mem_wr;
assign dbg_rd    = cpu_ce & mem_ack & mem_rd;
assign dbg_wa    = mem_addr;
assign dbg_wdata = mem_wdata;
assign dbg_rdata = cpu_rdata;
assign dbg_ie    = b_ie;

//----------------------------------------------------------------------------
// CPU bus, registered on the board side
//
// Decoding the CPU's request on the clock it appears made the longest
// single-clock paths of the Y Unit core (CPU register -> address decode ->
// bus state machine), so the board decodes a copy registered one clock
// later. That costs nothing on fast accesses: the CPU only looks at mem_ack
// on cpu_ce edges, every other clock.
//
// When the CPU takes an acknowledge (mem_ack high on a cpu_ce edge) it moves
// on at once, but the copy still holds the finished request for one more
// clock; b_stale keeps the state machine from serving it twice.
//----------------------------------------------------------------------------

reg         b_rd, b_wr, b_srt, b_stale;
reg  [27:0] b_addr;
reg  [21:3] b_baddr;
reg  [15:0] b_wdata;
reg  [31:4] b_pc;                // the CPU's PC (word address) with b_addr
reg         b_ie;                // and its interrupt enable (ST bit 21)
always @(posedge clk) begin
	b_rd    <= mem_rd;
	b_wr    <= mem_wr;
	b_srt   <= mem_srt;
	b_addr  <= mem_addr;
	b_pc    <= cpu_pc[31:4];
	b_ie    <= cpu_st[21];
	b_baddr <= mem_baddr[21:3];
	b_wdata <= mem_wdata;
	b_stale <= cpu_ce & mem_ack;
end

//----------------------------------------------------------------------------
// Address decode (word addresses = bit address >> 4, from the registered copy)
//----------------------------------------------------------------------------

wire [27:0] wa = b_addr;

//----------------------------------------------------------------------------
// Read patches (OSD secrets, tunit_secrets.sv; OSD cheats, tunit_cheats.sv)
//
// A CPU read of a word in the patch table returns the table's value instead
// of memory: program ROM words (instruction fetches included) and RAM
// variables alike; writes are untouched. The compare runs on the registered
// address every clock, so its result is ready on the same edge as the bus
// state machine's acknowledge for that address (which is decoded from the
// same copy), and stays valid for as long as the CPU holds the request.
//
// An entry marked pt_fetch (a program ROM patch: an instruction or one of
// its parameter words) applies only when the CPU fetches the word as code:
// the CPU's PC is the address of the word it fetches, opcode and immediate
// words alike (b_pc is registered with b_addr), so data reads of the
// program ROM (the games' power-up and diagnostics ROM tests) still see the
// original. A main RAM entry (a game variable) applies only while the CPU
// has interrupts enabled: the games read these variables from their
// processes (all reads seen in MAME: ST.IE 1), while the RAM tests (NBA Jam
// 2.00's at every power-up, the diagnostics') run with interrupts off and
// so read back what they wrote.
//
// The OSD cheats are 8 more entries of the same kind (pt_*[15:8]), switched
// by the Cheats menu instead of the secrets' options: Infinite Health P1 and
// P2 (the energy words, read as full: main RAM entries, the games read them
// from their processes with interrupts enabled), Stop Finishing Move Timer
// (the FINISH HIM routine's wait) and Infinite Round Time (the instruction
// that counts the round clock down), both program ROM entries.
//
// An entry marked pt_store also replaces the value the CPU writes to the
// word (the same compare, on the CPU's own address and interrupt enable, so
// it is ready with the registered copy). Infinite Health uses it: the game
// works out the new energy from the full value it reads and writes the
// result, and without this the game's own copy is left at full less the last
// hit, which is what the bar showed when the cheat was switched off. With
// it every write stores full, so the bar stays full when the cheat goes off.
//
// Fixed AI Difficulty is one more entry of the same kind, with its value
// from the OSD (lvl_val, 0 to 9) instead of the table: MK and MK2 keep their
// CPU opponent's level in one main RAM word (the AI picks entries of its
// 10-entry tables with it; the game raises it after matches won and lowers
// it after matches lost, from a few places), and while the option is on
// every read of that word with interrupts enabled returns the chosen level.
// The game's writes are untouched (it goes on adjusting its own copy, which
// the option does not show it), so Off hands the game's own value back at
// once, and in the diagnostics' RAM test (interrupts off, MAME) the word
// reads what the test wrote.
//----------------------------------------------------------------------------

reg         pt_hit;
reg  [15:0] pt_q;
integer     pt_i;
always @(posedge clk) begin
	pt_hit <= 1'b0;
	for (pt_i = 0; pt_i < 16; pt_i = pt_i + 1)
		if (pt_en[pt_i] && wa == pt_addr[28 * pt_i +: 28] &&
		    (pt_fetch[pt_i] ? (b_pc == wa) : ((wa[27:18] != 10'h004) || b_ie))) begin   // 0x004: main RAM
			pt_hit <= 1'b1;
			pt_q   <= pt_data[16 * pt_i +: 16];
		end
	if (lvl_on && wa == lvl_addr && b_ie) begin
		pt_hit <= 1'b1;
		pt_q   <= {12'd0, lvl_val};
	end
end

assign cpu_rdata = pt_hit ? pt_q : mem_rdata;

// write patches: the value stored for a CPU write to a pt_store entry's word,
// decoded from the CPU's own address on the clock b_addr takes it, so it is
// valid whenever the registered copy is
reg         wp_hit;
reg  [15:0] wp_q;
integer     wp_i;
always @(posedge clk) begin
	wp_hit <= 1'b0;
	for (wp_i = 0; wp_i < 16; wp_i = wp_i + 1)
		if (pt_store[wp_i] && pt_en[wp_i] && mem_addr == pt_addr[28 * wp_i +: 28] &&
		    ((mem_addr[27:18] != 10'h004) || cpu_st[21])) begin
			wp_hit <= 1'b1;
			wp_q   <= pt_data[16 * wp_i +: 16];
		end
end

wire [15:0] ram_wdata = wp_hit ? wp_q : b_wdata;   // the data of a main RAM write

localparam P_NONE = 3'd0, P_MK = 3'd1, P_NBAJAM = 3'd2, P_NBAJAMTE = 3'd3,
           P_JDREDD = 3'd4, P_MK2 = 3'd5;

// protection windows (MAME init_mktunit, init_nbajam_common, init_jdreddp, init_mk2)
wire pw_mk     = (prot_id == P_MK) && (wa[27:16] == 12'h01B) && (wa[15:12] <= 4'h6);  // 0x01B00000-0x01B6FFFF
wire pw_nba    = (prot_id == P_NBAJAM) && (wa >= 28'h01B1402) && (wa <= 28'h01B2503);
wire pw_te1    = (prot_id == P_NBAJAMTE) && (wa >= 28'h01B15F4) && (wa <= 28'h01B37F5);
wire pw_te2    = (prot_id == P_NBAJAMTE) && (wa >= 28'h01B95F4) && (wa <= 28'h01BB7F5);
wire pw_jd     = (prot_id == P_JDREDD) && (wa[27:16] == 12'h01B);                      // 0x01B00000-0x01BFFFFF
wire pw_mk2w   = (prot_id == P_MK2) && ((wa[27:1] == 27'h0079063) || (wa[27:1] == 27'h007A141));
wire pw_mk2d   = (prot_id == P_MK2) && ((wa[27:1] == 27'h00D0C87) || (wa[27:2] == 26'h0068F43));
wire pw_mk2s   = (prot_id == P_MK2) && (wa[27:1] == 27'h00D0C8E);
wire pw_mk2c   = (prot_id == P_MK2) && ((wa[27:1] == 27'h00ECE8F) || (wa[27:1] == 27'h00EF7C9));
wire pw_turbo  = mk_turbo && (wa == 28'hFFFFF40);
wire sel_prot  = pw_mk | pw_nba | pw_te1 | pw_te2 | pw_jd | pw_mk2w | pw_mk2d | pw_mk2s | pw_mk2c | pw_turbo;

wire sel_vram  = (wa[27:18] == 10'h000);
wire sel_ram   = (wa[27:18] == 10'h004);
wire sel_cmos  = (wa[27:13] == 15'h00A0);
wire sel_in    = (wa[27:2]  == 26'h0058000);
wire sel_pal   = (wa[27:15] == 13'h0030);
wire sel_dma   = (wa[27:4]  == 24'h01A800);
wire sel_ctrl  = (wa[27:1]  == 27'h00D8000) || (wa[27:1] == 27'h00F8000);   // 0x01B00000, 0x01F00000
wire sel_sstat = (wa[27:1]  == 27'h00E8000);                                 // 0x01D00000
wire sel_sdata = (wa[27:1]  == 27'h00E8081);                                 // 0x01D01020
wire sel_gfx   = (wa[27:23] == 5'd0) && (wa[22:21] != 2'b00);                // 0x02000000-0x07FFFFFF
wire sel_rom   = ((wa[27:25] == 3'b111) || (wa[27:25] == 3'b000)) && (wa[24:19] == 6'h3F);

//----------------------------------------------------------------------------
// CMOS (8 K x 16). Port B serves NVRAM load/save.
//
// An explicit altsyncram (true dual-port M10K): Quartus 17 would not infer a
// true dual-port RAM from either Intel template in the Y Unit core and fell
// back to registers. Addresses and write data are registered inside the
// block, the outputs are not, so q_a/q_b hold the word addressed on the
// previous clock. A behavioural model for simulation lives in sim/.
//----------------------------------------------------------------------------

wire [15:0] cmos_q;
reg         cmos_we;

altsyncram #(
	.operation_mode                     ("BIDIR_DUAL_PORT"),
	.intended_device_family             ("Cyclone V"),
	.lpm_type                           ("altsyncram"),
	.ram_block_type                     ("M10K"),
	.width_a                            (16),
	.widthad_a                          (13),
	.numwords_a                         (8192),
	.width_b                            (16),
	.widthad_b                          (13),
	.numwords_b                         (8192),
	.width_byteena_a                    (1),
	.width_byteena_b                    (1),
	.address_reg_b                      ("CLOCK0"),
	.indata_reg_b                       ("CLOCK0"),
	.wrcontrol_wraddress_reg_b          ("CLOCK0"),
	.outdata_reg_a                      ("UNREGISTERED"),
	.outdata_reg_b                      ("UNREGISTERED"),
	.outdata_aclr_a                     ("NONE"),
	.outdata_aclr_b                     ("NONE"),
	.clock_enable_input_a               ("BYPASS"),
	.clock_enable_input_b               ("BYPASS"),
	.clock_enable_output_a              ("BYPASS"),
	.clock_enable_output_b              ("BYPASS"),
	.read_during_write_mode_port_a      ("NEW_DATA_NO_NBE_READ"),
	.read_during_write_mode_port_b      ("NEW_DATA_NO_NBE_READ"),
	.read_during_write_mode_mixed_ports ("DONT_CARE"),
	.power_up_uninitialized             ("FALSE")
) cmos_mem
(
	// port A: TMS34010
	.clock0         (clk),
	.address_a      (wa[12:0]),
	.data_a         (b_wdata),
	.wren_a         (cmos_we),
	.q_a            (cmos_q),

	// port B: NVRAM load/save and CMOS clear from the top level
	.clock1         (1'b1),
	.address_b      (nv_addr),
	.data_b         (nv_din),
	.wren_b         (nv_we),
	.q_b            (nv_dout),

	// unused controls
	.aclr0          (1'b0),
	.aclr1          (1'b0),
	.addressstall_a (1'b0),
	.addressstall_b (1'b0),
	.byteena_a      (1'b1),
	.byteena_b      (1'b1),
	.clocken0       (1'b1),
	.clocken1       (1'b1),
	.clocken2       (1'b1),
	.clocken3       (1'b1),
	.rden_a         (1'b1),
	.rden_b         (1'b1),
	.eccstatus      ()
);

assign cmos_write = cmos_we;

//----------------------------------------------------------------------------
// Program ROM cache: 2048 lines of 8 bytes, direct mapped
//----------------------------------------------------------------------------

reg  [63:0] rc_data [0:2047];
reg   [6:0] rc_tag  [0:2047];           // {valid, tag}
reg  [63:0] rc_dq;
reg   [6:0] rc_tq;
reg         rc_we;
reg  [10:0] rc_wa;
reg  [63:0] rc_wd;
reg   [6:0] rc_wt;

wire [16:0] rom_line = wa[18:2];        // 8-byte line within the 1 MB ROM

always @(posedge clk) begin
	if (rc_we) begin
		rc_data[rc_wa] <= rc_wd;
		rc_tag[rc_wa]  <= rc_wt;
	end
	rc_dq <= rc_data[rom_line[10:0]];
	rc_tq <= rc_tag[rom_line[10:0]];
end

//----------------------------------------------------------------------------
// Main RAM cache: 4096 lines of 8 bytes, direct mapped, write-through
//----------------------------------------------------------------------------

reg  [63:0] mc_data [0:4095];
reg   [4:0] mc_tag  [0:4095];           // {valid, tag}
reg  [63:0] mc_dq;
reg   [4:0] mc_tq;
reg         mc_we;
reg  [11:0] mc_wa;
reg  [63:0] mc_wd;
reg   [4:0] mc_wt;

wire [15:0] ram_line = wa[17:2];        // 8-byte line within the 512 KB RAM

always @(posedge clk) begin
	if (mc_we) begin
		mc_data[mc_wa] <= mc_wd;
		mc_tag[mc_wa]  <= mc_wt;
	end
	mc_dq <= mc_data[ram_line[11:0]];
	mc_tq <= mc_tag[ram_line[11:0]];
end

// both caches are cleared by walking them after reset (c_clr, c_clr_a are
// declared with the CPU reset above)

//----------------------------------------------------------------------------
// Main RAM write queue (4 words) to the SDRAM write port
//----------------------------------------------------------------------------

reg  [33:0] wq [0:3];                   // {word address, data}
reg   [1:0] wq_rd = 2'd0, wq_wr = 2'd0;
reg   [2:0] wq_n = 3'd0;
reg         wq_push;
reg  [33:0] wq_in;
wire        wq_full  = (wq_n == 3'd4);
wire        wq_idle  = (wq_n == 3'd0) && (ram_wr_req == ram_wr_ack);

// The queue is not reset: the CPU cannot push while in reset, so it only
// drains. (Resetting it threw away the RAM clear's last writes, which end
// while the board is still held in reset after a ROM load.)
always @(posedge clk) begin
	begin
		// pop into the SDRAM write port when it is free
		if (wq_n != 3'd0 && ram_wr_req == ram_wr_ack) begin
			ram_wr_addr <= RAM_BASE[24:1] + {6'd0, wq[wq_rd][33:16]};
			ram_wr_data <= wq[wq_rd][15:0];
			ram_wr_req  <= ~ram_wr_req;
			wq_rd       <= wq_rd + 2'd1;
		end
		if (wq_push) begin
			wq[wq_wr] <= wq_in;
			wq_wr     <= wq_wr + 2'd1;
		end
		wq_n <= wq_n + (wq_push ? 3'd1 : 3'd0)
		             - ((wq_n != 3'd0 && ram_wr_req == ram_wr_ack) ? 3'd1 : 3'd0);
	end
end

//----------------------------------------------------------------------------
// Main RAM clear sequencer
//----------------------------------------------------------------------------

reg clr_push;
always @(posedge clk) begin
	clr_push <= 1'b0;
	if (ram_clr_req != clr_seen) begin
		clr_seen <= ram_clr_req;
		clr_busy <= 1'b1;
		clr_addr <= 18'd0;
	end
	else if (clr_busy && !wq_full && !clr_push) begin
		clr_push <= 1'b1;
		clr_addr <= clr_addr + 18'd1;
		if (clr_addr == 18'h3FFFF) clr_busy <= 1'b0;
	end
end

//----------------------------------------------------------------------------
// Graphics ROM read-back (MAME midtunit_gfxrom_r): two 4 MB windows, the
// second always at 0x400000, the first at 0 or (MK2, control bit 7) 0x800000
//----------------------------------------------------------------------------

reg   [7:0] ctrl;                       // control register bits 7-0
wire        videobank = ctrl[5];

wire [22:0] gfx_woff  = wa[22:0] - 23'h200000;                    // word offset in the window
wire [23:0] gfx_bbase = gfx_woff[21] ? 24'h400000 : ((big_rom && ctrl[7]) ? 24'h800000 : 24'h000000);
wire [23:0] gfx_byte  = gfx_bbase + {2'b00, gfx_woff[20:0], 1'b0};
wire        gfx_out   = (gfx_byte[23:20] >= gfx_mb);              // above the loaded ROM: 0

//----------------------------------------------------------------------------
// Protection state (MAME midtunit_m.cpp)
//----------------------------------------------------------------------------

`include "tunit_prot_tables.svh"

reg   [5:0] mk_idx;                     // MK: index into mk_prot_values
reg  [15:0] nba_q [0:4];                // NBA Jam: value queue
reg   [2:0] nba_i;
reg   [7:0] jd_i, jd_end;               // Judge Dredd: next entry and end of the table
reg         jd_on;
reg  [15:0] mk2_data;                   // MK2: data latch
reg   [7:0] fake_snd;                   // ADPCM boards: MAME's fake sound status count

// NBA Jam: table index from the address within the window (offset >> 6)
// (registered: a protection write waits one clock in S_NBAW for it)
wire [27:0] nba_rel = pw_te2 ? (wa - 28'h01B95F4) : pw_te1 ? (wa - 28'h01B15F4) : (wa - 28'h01B1402);
reg  [31:0] nba_tv;
always @(posedge clk) nba_tv <= nba_val({prot_id == P_NBAJAMTE, nba_rel[12:6]});

// Judge Dredd: table selected by the write offset
wire [27:0] jd_rel  = wa - 28'h01B0000;

// MK Turbo counter GAL (MAME returns random numbers; any changing value does)
reg  [15:0] lfsr;
always @(posedge clk)
	lfsr <= reset ? 16'hACE1 : {lfsr[14:0], lfsr[15] ^ lfsr[13] ^ lfsr[12] ^ lfsr[10]};

//----------------------------------------------------------------------------
// DMA blitter
//----------------------------------------------------------------------------

reg         dma_reg_wr;
wire [15:0] dma_rdata;
wire        dma_wr_wait;
wire [15:0] dma_palette;

wire  [8:0] blt_row;
wire  [7:0] blt_lo, blt_hi, blt_raddr;
wire [63:0] blt_q;
wire  [7:0] blt_be;
wire        blt_req, blt_ack;
wire [25:0] dma_line;
wire        dma_req;
reg         dma_ack;
reg  [63:0] dma_data;

tunit_dma dma
(
	.clk         (clk),
	.reset       (cpu_reset),
	.big_rom     (big_rom),
	.fast        (dma_fast),

	.reg_wr      (dma_reg_wr),
	.reg_idx     (wa[3:0]),
	.reg_wdata   (b_wdata),
	.reg_rdata   (dma_rdata),
	.reg_wr_wait (dma_wr_wait),
	.palette_reg (dma_palette),

	.irq         (dma_irq),

	.gfx_line    (dma_line),
	.gfx_req     (dma_req),
	.gfx_ack     (dma_ack),
	.gfx_data    (dma_data),

	.blt_req     (blt_req),
	.blt_ack     (blt_ack),
	.blt_row     (blt_row),
	.blt_lo      (blt_lo),
	.blt_hi      (blt_hi),
	.blt_raddr   (blt_raddr),
	.blt_q       (blt_q),
	.blt_be      (blt_be),

	.busy        (dbg_blit_busy)
);

// blitter source lines: from SDRAM below the loaded ROM size, 0 above it
reg dma_pend;
always @(posedge clk) begin
	if (cpu_reset) begin
		dma_ack    <= dma_req;
		dma_sd_req <= dma_sd_ack;
		dma_pend   <= 1'b0;
	end
	else if (dma_pend) begin
		if (dma_sd_req == dma_sd_ack) begin
			dma_pend <= 1'b0;
			dma_data <= dma_sd_data;
			dma_ack  <= dma_req;
		end
	end
	else if (dma_req != dma_ack) begin
		if (dma_line[25:17] >= {5'd0, gfx_mb}) begin
			dma_data <= 64'd0;
			dma_ack  <= dma_req;
		end
		else begin
			dma_sd_addr <= GFX_BASE[24:3] + {1'b0, dma_line[20:0]};   // up to 16 MB of lines
			dma_sd_req  <= ~dma_sd_req;
			dma_pend    <= 1'b1;
		end
	end
end

//----------------------------------------------------------------------------
// VRAM controller
//----------------------------------------------------------------------------

wire        disp_req, disp_ack;
wire  [8:0] disp_row;
wire        lb_we;
wire  [6:0] lb_addr;
wire [63:0] lb_data;

reg         srt_req;
wire        srt_ack;
reg         srt_wr;
reg  [18:0] srt_entry;
wire [15:0] srt_first;

reg         vcpu_req;
wire        vcpu_ack;
reg         vcpu_wr;
reg  [16:0] vcpu_qaddr;
reg         vcpu_half;
reg   [3:0] vcpu_be;
reg  [31:0] vcpu_wdata;
wire [31:0] vcpu_rdata;

tunit_vram vram
(
	.clk            (clk),
	.reset          (cpu_reset),

	.ddr_busy       (ddr_busy),
	.ddr_burstcnt   (ddr_burstcnt),
	.ddr_addr       (ddr_addr),
	.ddr_dout       (ddr_dout),
	.ddr_dout_ready (ddr_dout_ready),
	.ddr_rd         (ddr_rd),
	.ddr_din        (ddr_din),
	.ddr_be         (ddr_be),
	.ddr_we         (ddr_we),

	.disp_req       (disp_req),
	.disp_ack       (disp_ack),
	.disp_row       (disp_row),
	.lb_we          (lb_we),
	.lb_addr        (lb_addr),
	.lb_data        (lb_data),

	.srt_req        (srt_req),
	.srt_ack        (srt_ack),
	.srt_wr         (srt_wr),
	.srt_entry      (srt_entry),
	.srt_first      (srt_first),

	.blt_req        (blt_req),
	.blt_ack        (blt_ack),
	.blt_row        (blt_row),
	.blt_lo         (blt_lo),
	.blt_hi         (blt_hi),
	.blt_raddr      (blt_raddr),
	.blt_q          (blt_q),
	.blt_be         (blt_be),

	.cpu_req        (vcpu_req),
	.cpu_ack        (vcpu_ack),
	.cpu_wr         (vcpu_wr),
	.cpu_qaddr      (vcpu_qaddr),
	.cpu_half       (vcpu_half),
	.cpu_be         (vcpu_be),
	.cpu_wdata      (vcpu_wdata),
	.cpu_rdata      (vcpu_rdata)
);

wire vram_idle = (vcpu_req == vcpu_ack) && (srt_req == srt_ack);

//----------------------------------------------------------------------------
// Video (with the palette RAM)
//----------------------------------------------------------------------------

reg         pal_we;
wire [15:0] pal_q;

tunit_video video
(
	.clk          (clk),
	.reset        (reset),
	.ce_pix       (ce_pix_r),
	.ce_vclk      (ce_vclk),

	.hcount       (hcount),
	.heblnk       (heblnk),
	.hsblnk       (hsblnk),
	.hsync_in     (cpu_hs),
	.vsync_in     (cpu_vs),
	.hblank_in    (cpu_hb),
	.vblank_in    (cpu_vb),
	.disp_en      (disp_en),
	.line_start   (line_start & cpu_ce),     // one clock per CPU pulse
	.line_vis     (line_vis),
	.line_row     (line_row),
	.line_col     (line_col),

	.pal_we       (pal_we),
	.pal_addr     (wa[14:0]),
	.pal_wdata    (b_wdata),
	.pal_q        (pal_q),

	.disp_req     (disp_req),
	.disp_ack     (disp_ack),
	.disp_row     (disp_row),
	.lb_we        (lb_we),
	.lb_addr      (lb_addr),
	.lb_data      (lb_data),

	.r            (vid_r),
	.g            (vid_g),
	.b            (vid_b),
	.hsync        (vid_hs),
	.vsync        (vid_vs),
	.hblank       (vid_hb),
	.vblank       (vid_vb)
);

//----------------------------------------------------------------------------
// Bus cycle state machine
//----------------------------------------------------------------------------

localparam S_IDLE    = 4'd0;
localparam S_BRAM    = 4'd1;     // CMOS / palette read data arrives
localparam S_ROM     = 4'd2;     // ROM cache tag check
localparam S_ROMFILL = 4'd3;     // waiting for the SDRAM line
localparam S_GFX     = 4'd4;     // graphics read-back from SDRAM
localparam S_VRAMRD  = 4'd5;     // VRAM read: wait for the bridge, then the data
localparam S_VRAMWR  = 4'd6;     // VRAM write: wait for a free slot
localparam S_SRT     = 4'd7;     // shift-register transfer
localparam S_DMAWAIT = 4'd8;     // blitter start held while it is busy
localparam S_RAMRD   = 4'd9;     // RAM cache tag check (read)
localparam S_RAMWR   = 4'd10;    // RAM cache update (write)
localparam S_RAMMISS = 4'd11;    // wait for the write queue, then fetch the line
localparam S_RAMFILL = 4'd12;
localparam S_NBAW    = 4'd13;    // NBA Jam protection write: the table value is ready

reg   [3:0] bstate;
reg         bram_pal;            // S_BRAM: palette (else CMOS)
reg         vram_sent;

// The CPU holds a request until it sees mem_ack in a cpu_ce cycle, so the ack
// is held until then; while it is up, and for the one clock after it is
// taken (b_stale), the same request is not served again.
wire        req = (b_rd | b_wr) & ~mem_ack & ~b_stale;

// write queue entries from the CPU and from the RAM clear
always @(*) begin
	wq_push = clr_push;
	wq_in   = {clr_addr - 18'd1, 16'h0000};   // clr_addr has already moved on
	if (bstate == S_IDLE && req && !c_clr && !b_srt && b_wr && sel_ram && !sel_prot && !wq_full && !clr_busy && !clr_push) begin
		wq_push = 1'b1;
		wq_in   = {wa[17:0], ram_wdata};
	end
end

// read value of a protection location
wire  [5:0] mk_cur = (mk_idx >= 6'd57) ? 6'd0 : mk_idx;   // MAME wraps an index past the end
wire  [7:0] mk_v   = mk_val(mk_cur);
reg  [15:0] prot_rd;
always @(*) begin
	prot_rd = 16'hFFFF;
	if (pw_turbo)
		prot_rd = lfsr;
	else if (pw_mk)
		prot_rd = {mk_v[6:0], 9'd0};
	else if (pw_nba | pw_te1 | pw_te2)
		prot_rd = nba_q[nba_i];
	else if (pw_jd)
		prot_rd = (jd_on && jd_i < jd_end) ? {1'b0, jd_val(jd_i), 9'd0} : 16'hFFFF;
	else if (pw_mk2d)
		prot_rd = mk2_data;
	else if (pw_mk2s)
		prot_rd = {1'b0, mk2_data[15:1]};
	else if (pw_mk2c)
		prot_rd = 16'h0002;
end

always @(posedge clk) begin
	if (cpu_ce)
		mem_ack <= 1'b0;
	cmos_we    <= 1'b0;
	pal_we     <= 1'b0;
	rc_we      <= 1'b0;
	mc_we      <= 1'b0;
	snd_wr     <= 1'b0;
	snd_rd     <= 1'b0;
	dma_reg_wr <= 1'b0;

	// clear both caches after a reset; the CPU stays in reset until done
	if (reset) begin
		c_clr   <= 1'b1;
		c_clr_a <= 12'd0;
	end
	else if (c_clr) begin
		rc_we   <= 1'b1;
		rc_wa   <= c_clr_a[10:0];
		rc_wt   <= 7'd0;
		mc_we   <= 1'b1;
		mc_wa   <= c_clr_a;
		mc_wt   <= 5'd0;
		c_clr_a <= c_clr_a + 12'd1;
		if (c_clr_a == 12'hFFF) c_clr <= 1'b0;
	end

	if (cpu_reset) begin
		mem_ack     <= 1'b0;
		bstate      <= S_IDLE;
		cpu_sd_req  <= cpu_sd_ack;
		vcpu_req    <= vcpu_ack;
		srt_req     <= srt_ack;
		ctrl        <= 8'd0;
		mk_idx      <= 6'd0;
		nba_i       <= 3'd0;
		jd_on       <= 1'b0;
		mk2_data    <= 16'd0;
		fake_snd    <= 8'd0;
		vram_sent   <= 1'b0;
	end
	else begin
		case (bstate)
			S_IDLE: if (req && !c_clr) begin
				if (b_srt) begin
					// VRAM shift-register transfer of two rows
					if (vram_idle) begin
						srt_wr    <= b_wr;
						srt_entry <= b_baddr[21:3];
						srt_req   <= ~srt_req;
						bstate    <= S_SRT;
					end
				end
				else if (b_wr) begin
					// ---- writes ----
					if (pw_nba | pw_te1 | pw_te2)
						bstate <= S_NBAW;
					else if (sel_prot) begin
						mem_ack <= 1'b1;
						if (pw_mk) begin
							// find the written value in the table (MAME mk_prot_w)
							mk_idx <= mk_first(b_wdata[14:9]);
						end
						if (pw_jd) begin
							case (jd_rel[15:0])
								16'h1074: begin jd_on <= 1'b1; jd_i <= 8'd0;   jd_end <= 8'd46;  end
								16'h1324: begin jd_on <= 1'b1; jd_i <= 8'd46;  jd_end <= 8'd47;  end
								16'h7654: begin jd_on <= 1'b1; jd_i <= 8'd47;  jd_end <= 8'd49;  end
								16'h7776: begin jd_on <= 1'b1; jd_i <= 8'd49;  jd_end <= 8'd140; end
								16'h8002: begin jd_on <= 1'b1; jd_i <= 8'd140; jd_end <= 8'd156; end
								default: ;
							endcase
						end
						if (pw_mk2w)
							mk2_data <= b_wdata;
					end
					else if (sel_vram)
						bstate <= S_VRAMWR;
					else if (sel_dma) begin
						dma_reg_wr <= 1'b1;
						bstate     <= S_DMAWAIT;
					end
					else if (sel_ram) begin
						// queued for SDRAM above; the cache line is updated next
						if (!wq_full && !clr_busy)
							bstate <= S_RAMWR;
					end
					else begin
						mem_ack <= 1'b1;
						if (sel_cmos)
							cmos_we <= 1'b1;
						if (sel_pal)
							pal_we <= 1'b1;
						if (sel_ctrl)
							ctrl <= b_wdata[7:0];
						if (sel_sdata && wa[0]) begin
							// 0x01D01030: sound command (0x01D01020 is ignored)
							snd_wr   <= 1'b1;
							snd_data <= b_wdata;
							fake_snd <= 8'd128;
						end
					end
				end
				else begin
					// ---- reads ----
					if (sel_prot) begin
						mem_ack   <= 1'b1;
						mem_rdata <= prot_rd;
						if (pw_mk)
							mk_idx <= mk_cur + 6'd1;
						if ((pw_nba | pw_te1 | pw_te2) && nba_i < 3'd4)
							nba_i <= nba_i + 3'd1;
						if (pw_jd && jd_on && jd_i < jd_end)
							jd_i <= jd_i + 8'd1;
					end
					else if (sel_cmos || sel_pal) begin
						bram_pal <= sel_pal;
						bstate   <= S_BRAM;
					end
					else if (sel_ram)
						bstate <= S_RAMRD;
					else if (sel_rom)
						bstate <= S_ROM;
					else if (sel_gfx) begin
						if (gfx_out) begin
							mem_ack   <= 1'b1;
							mem_rdata <= 16'h0000;
						end
						else begin
							cpu_sd_addr <= GFX_BASE[24:3] + {1'b0, gfx_byte[23:3]};
							cpu_sd_req  <= ~cpu_sd_req;
							bstate      <= S_GFX;
						end
					end
					else if (sel_vram)
						bstate <= S_VRAMRD;
					else begin
						mem_ack <= 1'b1;
						if (sel_dma)
							mem_rdata <= dma_rdata;
						else if (sel_in)
							mem_rdata <= in_ports[{wa[1:0], 4'b0000} +: 16];
						else if (sel_sstat) begin
							if (dcs)
								mem_rdata <= snd_status;
							else if (fake_snd != 8'd0) begin
								// MAME's fake status: busy (0) for 128 reads after a command
								fake_snd  <= fake_snd - 8'd1;
								mem_rdata <= 16'h0000;
							end
							else
								mem_rdata <= 16'hFFFF;
						end
						else if (sel_sdata) begin
							mem_rdata <= dcs ? {8'h00, snd_rdata[7:0]} : 16'hFFFF;
							snd_rd    <= dcs;
						end
						else
							mem_rdata <= 16'hFFFF;
					end
				end
			end

			S_NBAW: begin
				// MAME nbajam_prot_w: the written word, then the four bytes
				// of the table entry for this address, each << 9
				nba_q[0] <= b_wdata;
				nba_q[1] <= {nba_tv[30:24], 9'd0};
				nba_q[2] <= {nba_tv[22:16], 9'd0};
				nba_q[3] <= {nba_tv[14:8], 9'd0};
				nba_q[4] <= {nba_tv[6:0], 9'd0};
				nba_i    <= 3'd0;
				mem_ack  <= 1'b1;
				bstate   <= S_IDLE;
			end

			S_BRAM: begin
				// the read address went to the RAMs with the request
				mem_ack   <= 1'b1;
				mem_rdata <= bram_pal ? pal_q : cmos_q;
				bstate    <= S_IDLE;
			end

			S_RAMWR: begin
				// write-through: update the cached line if it is present
				if (mc_tq == {1'b1, ram_line[15:12]}) begin
					mc_we <= 1'b1;
					mc_wa <= ram_line[11:0];
					mc_wt <= mc_tq;
					mc_wd <= mc_dq;
					mc_wd[{wa[1:0], 4'b0000} +: 16] <= ram_wdata;
				end
				mem_ack <= 1'b1;
				bstate  <= S_IDLE;
			end

			S_RAMRD: begin
				if (mc_tq == {1'b1, ram_line[15:12]}) begin
					mem_ack   <= 1'b1;
					mem_rdata <= mc_dq[{wa[1:0], 4'b0000} +: 16];
					bstate    <= S_IDLE;
				end
				else
					bstate <= S_RAMMISS;
			end

			S_RAMMISS: if (wq_idle) begin
				// no write to this line can still be on its way
				cpu_sd_addr <= RAM_BASE[24:3] + {6'd0, ram_line};
				cpu_sd_req  <= ~cpu_sd_req;
				bstate      <= S_RAMFILL;
			end

			S_RAMFILL: if (cpu_sd_req == cpu_sd_ack) begin
				mc_we     <= 1'b1;
				mc_wa     <= ram_line[11:0];
				mc_wd     <= cpu_sd_data;
				mc_wt     <= {1'b1, ram_line[15:12]};
				mem_ack   <= 1'b1;
				mem_rdata <= cpu_sd_data[{wa[1:0], 4'b0000} +: 16];
				bstate    <= S_IDLE;
			end

			S_ROM: begin
				if (rc_tq == {1'b1, rom_line[16:11]}) begin
					mem_ack   <= 1'b1;
					mem_rdata <= rc_dq[{wa[1:0], 4'b0000} +: 16];
					bstate    <= S_IDLE;
				end
				else begin
					cpu_sd_addr <= ROM_BASE[24:3] + {5'd0, rom_line};
					cpu_sd_req  <= ~cpu_sd_req;
					bstate      <= S_ROMFILL;
				end
			end

			S_ROMFILL: if (cpu_sd_req == cpu_sd_ack) begin
				rc_we     <= 1'b1;
				rc_wa     <= rom_line[10:0];
				rc_wd     <= cpu_sd_data;
				rc_wt     <= {1'b1, rom_line[16:11]};
				mem_ack   <= 1'b1;
				mem_rdata <= cpu_sd_data[{wa[1:0], 4'b0000} +: 16];
				bstate    <= S_IDLE;
			end

			S_GFX: if (cpu_sd_req == cpu_sd_ack) begin
				mem_ack   <= 1'b1;
				mem_rdata <= cpu_sd_data[{gfx_byte[2:1], 4'b0000} +: 16];
				bstate    <= S_IDLE;
			end

			S_VRAMWR: if (vram_idle) begin
				// two entries per CPU word: pixel bytes carry the DMA palette
				// register along (MAME midtunit_vram_w), palette bytes leave
				// the pixels alone
				vcpu_wr    <= 1'b1;
				vcpu_qaddr <= wa[17:1];
				vcpu_half  <= wa[0];
				if (videobank) begin
					vcpu_be    <= 4'b1111;
					vcpu_wdata <= {dma_palette[15:8], b_wdata[15:8], dma_palette[7:0], b_wdata[7:0]};
				end
				else begin
					vcpu_be    <= 4'b1010;
					vcpu_wdata <= {b_wdata[15:8], 8'h00, b_wdata[7:0], 8'h00};
				end
				vcpu_req <= ~vcpu_req;
				mem_ack  <= 1'b1;                // posted
				bstate   <= S_IDLE;
			end

			S_VRAMRD: begin
				if (!vram_sent) begin
					if (vram_idle) begin
						vcpu_wr    <= 1'b0;
						vcpu_qaddr <= wa[17:1];
						vcpu_half  <= wa[0];
						vcpu_req   <= ~vcpu_req;
						vram_sent  <= 1'b1;
					end
				end
				else if (vcpu_req == vcpu_ack) begin
					vram_sent <= 1'b0;
					mem_ack   <= 1'b1;
					mem_rdata <= videobank ? {vcpu_rdata[23:16], vcpu_rdata[7:0]} : {vcpu_rdata[31:24], vcpu_rdata[15:8]};
					bstate    <= S_IDLE;
				end
			end

			S_SRT: if (srt_req == srt_ack) begin
				mem_ack   <= 1'b1;
				mem_rdata <= srt_first;
				bstate    <= S_IDLE;
			end

			S_DMAWAIT: begin
				// keep offering the write until the blitter takes it
				if (dma_wr_wait)
					dma_reg_wr <= 1'b1;
				else begin
					mem_ack <= 1'b1;
					bstate  <= S_IDLE;
				end
			end

			default: bstate <= S_IDLE;
		endcase
	end
end

endmodule

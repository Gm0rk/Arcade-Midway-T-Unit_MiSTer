//============================================================================
//  DCS Audio 2K board for the T-Unit (Mortal Kombat II)
//
//  An ADSP-2105 at 10 MHz that boots from and plays out of banked sound
//  ROMs, with one-word mailboxes to and from the 34010 and a 16-bit DAC at
//  31.25 kHz (MAME dcs_audio_2k_device, shared/dcs.cpp). The DSP itself is
//  the Killer Instinct core's (rtl/dcs, same board); this wrapper is adapted
//  from KI's ki_dcs_audio.sv for the T-Unit:
//
//    Host side (MAME midtunit mk2_state)
//      a write of the sound word (0x01D01030) sets the reset line from
//      bit 8 (low holds the DSP in reset) and puts bits 0-7 in the input
//      mailbox (dcs_w); the status read (0x01D00000) is the latch control
//      word >> 4 (bit 7 input empty, bit 6 output empty), the data read
//      (0x01D01020) the output mailbox's low byte, which empties it.
//
//    Sound ROMs
//      six 512 KB ROMs, one per 1 MB window of the ADSP's 16 MB bank space,
//      each mirrored in the window's upper half (MAME ROM_RELOAD); windows 6
//      and 7 wrap to 0 and 1 (MAME: bank % 1536). They sit packed in SDRAM
//      at 0xD00000 (see tools/tunit_layout.py), read 8 bytes at a time
//      through the DSP's ROM cache.
//
//  Clocking. Everything runs on the 96 MHz clk. The DSP's logic advances
//  only on core_ce (35.75 MHz on average, KI's rate for 10 MIPS), and only
//  on every second clock. The strobes it takes on core_ce edges (DAC slots,
//  host command writes and response reads) are held until a cycle with
//  core_ce; the inputs it samples on every clock (the ROM ready, the resets)
//  are lined up with the same cycles. Every register inside adsp2105
//  therefore changes at most once every two clocks, and the SDC declares its
//  internal paths as two-cycle paths (KI runs the same logic at 50 MHz).
//
//  Copyright (C) 2026 Gm0rk - GPL-3.0-or-later
//  (contains code adapted from ki_dcs_audio.sv, GPL-3.0-only)
//============================================================================

module tunit_dcs
(
	input             clk,           // 96 MHz
	input             reset,         // board reset (and "not a DCS game")

	// host (34010) side
	input             cmd_wr,        // one pulse per write of the sound word
	input      [15:0] cmd_data,
	input             data_rd,       // one pulse per read of the data word
	output reg [15:0] status,        // control_r() >> 4
	output reg [15:0] rdata,         // data_r() & 0xff

	// SDRAM: packed sound ROMs
	output reg [24:3] rom_addr,
	output reg        rom_req,       // toggle
	input             rom_ack,
	input      [63:0] rom_data,

	output reg signed [15:0] audio
);

localparam [24:0] DCS_BASE = 25'h0D0_0000;

//----------------------------------------------------------------------------
// Phase: the DSP's clocks are the edges at the end of ph = 1 cycles
//----------------------------------------------------------------------------

reg ph = 1'b0;
always @(posedge clk) ph <= ~ph;

// board reset, changing only at the edges that start a ph = 1 cycle
reg rst_d = 1'b1;
always @(posedge clk) if (!ph) rst_d <= reset;

// core_ce: 35.75 MHz out of the 48 MHz of ph = 1 cycles (3575 / 4800)
reg  [12:0] ce_acc = 13'd0;
reg         dcs_ce = 1'b0;
always @(posedge clk) begin
	dcs_ce <= 1'b0;
	if (!ph) begin
		if (ce_acc + 13'd3575 >= 13'd4800) begin
			ce_acc <= ce_acc + 13'd3575 - 13'd4800;
			dcs_ce <= 1'b1;
		end
		else
			ce_acc <= ce_acc + 13'd3575;
	end
end

// DAC slots: 31.25 kHz = 1536 ph = 1 cycles
reg  [10:0] dac_div = 11'd0;
reg         dac_slot = 1'b0;
always @(posedge clk) begin
	dac_slot <= 1'b0;
	if (!ph) begin
		if (dac_div == 11'd1535) begin
			dac_div  <= 11'd0;
			dac_slot <= 1'b1;
		end
		else
			dac_div <= dac_div + 11'd1;
	end
end

// The DSP counts DAC slots (its autobuffer half-period) and takes host
// response reads only on core_ce edges: adsp2105 samples dac_ce_in and
// host_resp_rd inside its core_ce block, whatever its header says. A strobe
// that falls in a ph = 1 cycle without core_ce would be lost, and about a
// third of the DAC slots were: the DSP drained a buffer half every 390 slots
// instead of 240, the output FIFO ran dry and Mortal Kombat II's sound played
// slow and broken up. Both strobes are therefore held until the next cycle
// with core_ce. The output FIFO below still pops on every real slot.
reg  slot_pend = 1'b0;
wire dsp_slot  = slot_pend & dcs_ce;
always @(posedge clk) begin
	if (dac_slot)      slot_pend <= 1'b1;
	else if (dsp_slot) slot_pend <= 1'b0;
end

//----------------------------------------------------------------------------
// Host mailboxes
//
// MAME's mk2_state::dcs_w calls reset_w(data & 0x100) and then
// data_w(data & 0xff): the command lands even while bit 8 holds the DSP in
// reset. After a board reset the line is released (machine_reset pulses it).
//----------------------------------------------------------------------------

reg         host_rst_n = 1'b1;       // reset line from the last write
reg         host_rst   = 1'b0;       // to the DSP, changes before ph = 1 cycles
reg         cmd_pend   = 1'b0;
reg  [15:0] cmd_lat;
reg         rd_pend    = 1'b0;       // a host data read the DSP has not taken yet
wire        resp_rd    = rd_pend & dcs_ce;

always @(posedge clk) begin
	if (reset) begin
		host_rst_n <= 1'b1;
		cmd_pend   <= 1'b0;
		rd_pend    <= 1'b0;
	end
	else begin
		if (cmd_wr) begin
			host_rst_n <= cmd_data[8];
			cmd_lat    <= {8'h00, cmd_data[7:0]};
			cmd_pend   <= 1'b1;
		end
		else if (cmd_pend && dcs_ce)
			cmd_pend <= 1'b0;                 // taken by the DSP on this edge

		if (data_rd)
			rd_pend <= 1'b1;
		else if (resp_rd)
			rd_pend <= 1'b0;                  // taken by the DSP on this edge
	end
	if (!ph) host_rst <= ~host_rst_n | reset;
end

//----------------------------------------------------------------------------
// ADSP-2105 (KI core)
//----------------------------------------------------------------------------

wire [15:0] dcs_status, dcs_resp;
wire        ext_req;
wire [18:0] ext_addr;
reg         ext_rdy = 1'b0;
reg  [63:0] ext_q;
wire [15:0] dac_sample;
wire        dac_we;

adsp2105 #(.ROM_GAP_FF(0)) dsp
(
	.clk                 (clk),
	.rst                 (rst_d),
	.core_ce             (dcs_ce),
	.host_rst            (host_rst),
	.host_cmd_w          (cmd_pend && dcs_ce),
	.host_cmd_data       (cmd_lat),
	.host_status_r       (dcs_status),
	.host_response_r     (dcs_resp),
	.host_resp_rd        (resp_rd),
	.rom_ddr_req         (ext_req),
	.rom_ddr_addr        (ext_addr),
	.rom_ddr_rdy         (ext_rdy),
	.rom_ddr_q           (ext_q),
	.dac_ce_in           (dsp_slot),
	.o_ppc               (),
	.o_valid             (),
	.o_unimpl            (),
	.dac_sample          (dac_sample),
	.dac_ce              (dac_we),
	.dbg_wrap_pc         (),
	.dbg_wrap_cnt        (),
	.dbg_src_pc          (),
	.dbg_src_addr        (),
	.dbg_src_cnt         (),
	.dbg_src_op          (),
	.dbg_rom_unstable_o  (),
	.dbg_rom_bankdelta_o (),
	.dbg_cmd_lost        (),
	.dbg_cmd_read        ()
);

// what the 34010 reads (registered: these are DSP outputs read at any clock)
always @(posedge clk) begin
	status <= {4'h0, dcs_status[15:4]};
	rdata  <= {8'h00, dcs_resp[7:0]};
end

//----------------------------------------------------------------------------
// Sound ROM reads: one 8-byte line per DSP cache miss
//
// The DSP's ROM cache holds ext_req with a stable address until it sees
// ext_rdy; ext_rdy is raised for exactly one ph = 1 cycle with the line in
// ext_q, after which the cache drops the request.
//----------------------------------------------------------------------------

localparam R_IDLE = 2'd0, R_FETCH = 2'd1, R_READY = 2'd2, R_DONE = 2'd3;
reg  [1:0] rstate = R_IDLE;

// window (ext_addr[18:16]) 6 and 7 wrap to 0 and 1 (MAME bank % 1536)
wire [2:0] win = (ext_addr[18:17] == 2'b11) ? {2'b00, ext_addr[16]} : ext_addr[18:16];

always @(posedge clk) begin
	if (rst_d) begin
		rstate  <= R_IDLE;
		ext_rdy <= 1'b0;
		rom_req <= rom_ack;
	end
	else case (rstate)
		R_IDLE: if (ext_req) begin
			rom_addr <= DCS_BASE[24:3] + {3'd0, win, ext_addr[15:0]};
			rom_req  <= ~rom_req;
			rstate   <= R_FETCH;
		end
		R_FETCH: if (rom_req == rom_ack) begin
			ext_q  <= rom_data;
			rstate <= R_READY;
		end
		R_READY: if (!ph) begin
			ext_rdy <= 1'b1;                  // through the next ph = 1 cycle
			rstate  <= R_DONE;
		end
		R_DONE: begin
			ext_rdy <= 1'b0;
			if (!ext_req) rstate <= R_IDLE;
		end
	endcase
end

//----------------------------------------------------------------------------
// Sample FIFO (from KI's wrapper): the DSP writes a whole autobuffer half at
// once; one sample goes out per DAC slot. Playback starts at 256 queued
// samples; an underrun holds the last sample until the FIFO refills.
//----------------------------------------------------------------------------

reg  [15:0] pcm_fifo [0:2047];
reg  [10:0] pcm_wp, pcm_rp;
reg  [11:0] pcm_used;
reg         pcm_running;
reg  [15:0] pcm_head;

wire pcm_pop   = dac_slot && pcm_running && (pcm_used != 12'd0);
wire pcm_push  = dac_we && ((pcm_used != 12'd2048) || pcm_pop);
wire pcm_start = !pcm_running && pcm_push && (pcm_used >= 12'd255);
wire pcm_under = dac_slot && pcm_running && (pcm_used == 12'd0);

always @(posedge clk) begin
	if (pcm_push) pcm_fifo[pcm_wp] <= dac_sample;
	pcm_head <= pcm_fifo[pcm_rp];
end

always @(posedge clk) begin
	if (rst_d || host_rst) begin
		pcm_wp      <= 11'd0;
		pcm_rp      <= 11'd0;
		pcm_used    <= 12'd0;
		pcm_running <= 1'b0;
		audio       <= 16'sd0;
	end
	else begin
		if (pcm_push) pcm_wp <= pcm_wp + 11'd1;
		if (pcm_pop) begin
			audio  <= pcm_head;
			pcm_rp <= pcm_rp + 11'd1;
		end
		if (pcm_start)
			pcm_running <= 1'b1;
		else if (pcm_under)
			pcm_running <= 1'b0;
		case ({pcm_push, pcm_pop})
			2'b10: pcm_used <= pcm_used + 12'd1;
			2'b01: pcm_used <= pcm_used - 12'd1;
			default: ;
		endcase
	end
end

endmodule

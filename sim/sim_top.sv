//============================================================================
//  Full-board simulation top (Verilator)
//
//  The T-Unit board, the ADPCM sound board, the secrets module (code player
//  and read patches) and the real SDRAM controller with a chip model, as
//  Arcade-Midway-T-Unit.sv wires them; the DDR3 port,
//  ROM loading (straight into the SDRAM model), inputs, frames and audio
//  are handled by the C++ harness (sim/sim_main.cpp). The SDRAM write
//  channel arbiter is the top level's.
//
//  Copyright (C) 2026 Gm0rk - GPL-3.0-or-later
//============================================================================

module sim_top
(
	input             clk,
	input             reset,
	input             pause,

	// game configuration (the top level's game table)
	input       [2:0] prot_id,
	input             mk_turbo,
	input             big_rom,
	input             dcs,
	input       [3:0] gfx_mb,
	input      [15:0] sprot_start,
	input      [15:0] sprot_end,
	input             ram_clr_req,
	input             snd_off,       // hold the sound board in reset (faster video-only runs)

	input      [63:0] in_ports,

	// secrets: the ROM index 1 table (written by the harness during reset)
	// and the OSD items (R[15:14] triggers, option slots 1-11)
	input             info_start,
	input             info_wr,
	input       [8:0] info_addr,
	input      [15:0] info_data,
	input       [1:0] osd_trig,
	input      [10:0] osd_opt,

	// DDR3 (C++ model)
	input             ddr_busy,
	output      [7:0] ddr_burstcnt,
	output     [28:0] ddr_addr,
	input      [63:0] ddr_dout,
	input             ddr_dout_ready,
	output            ddr_rd,
	output     [63:0] ddr_din,
	output      [7:0] ddr_be,
	output            ddr_we,

	// NVRAM port (unused in simulation: CMOS starts empty)
	output     [15:0] nv_dout,

	// video
	output            ce_pix,
	output      [7:0] vid_r,
	output      [7:0] vid_g,
	output      [7:0] vid_b,
	output            vid_hs,
	output            vid_vs,
	output            vid_hb,
	output            vid_vb,

	// audio
	output signed [15:0] audio,

	// debug
	output     [31:0] dbg_pc,
	output            dbg_retire,
	output            dbg_blit_busy,
	output            dbg_snd_wr,
	output     [15:0] dbg_snd_data,
	output            dbg_dcs_we,      // DCS: a sample drained into the output FIFO
	output     [15:0] dbg_dcs_smp,
	output            dbg_dcs_slot,    // DCS: DAC slot pulse into the DSP
	output            dbg_dcs_ce,      // DCS: DSP clock enable
	output            dbg_dcs_valid,   // DCS: DSP retired an instruction
	output     [13:0] dbg_dcs_pc,
	output     [15:0] dbg_dcs_slotctr,
	output            dbg_wr,
	output            dbg_rd,
	output     [27:0] dbg_wa,
	output     [15:0] dbg_wdata,
	output     [15:0] dbg_rdata
);

wire [24:3] cpu_sd_addr, dma_sd_addr, snd_sd_addr, oki_sd_addr;
wire        cpu_sd_req, dma_sd_req, snd_sd_req, oki_sd_req;
wire        cpu_sd_ack, dma_sd_ack, snd_sd_ack, oki_sd_ack;
wire [63:0] cpu_sd_data, dma_sd_data, snd_sd_data, oki_sd_data;

wire [24:1] ram_wr_addr;
wire [15:0] ram_wr_data;
wire        ram_wr_req;
reg         ram_wr_ack = 1'b0;
wire        sd_wr_ack;

wire        snd_wr, snd_rd;
wire [15:0] snd_data;
wire [15:0] snd_status, snd_rdata;
wire [24:3] dcs_sd_addr;
wire        dcs_sd_req;
wire signed [15:0] adpcm_audio, dcs_audio;
assign audio = dcs ? dcs_audio : adpcm_audio;

assign dbg_snd_wr   = snd_wr;
assign dbg_snd_data = snd_data;
assign dbg_dcs_we   = dcs_board.dac_we;
assign dbg_dcs_smp  = dcs_board.dac_sample;
assign dbg_dcs_slot = dcs_board.dac_slot;
assign dbg_dcs_ce   = dcs_board.dcs_ce;
assign dbg_dcs_valid = dcs_board.dsp.o_valid;
assign dbg_dcs_pc   = dcs_board.dsp.o_ppc;
assign dbg_dcs_slotctr = dcs_board.dsp.dac_slot_ctr;

// secrets, as the top level: frames counted at the start of each running
// vertical blank; a playing code replaces IN0 and holds its start buttons
wire        code_on;
wire [15:0] code_in0;
wire  [1:0] code_start;
wire [223:0] pt_addr;
wire [127:0] pt_data;
wire   [7:0] pt_en;
reg         vb_d;
always @(posedge clk) vb_d <= vid_vb;

tunit_secrets secrets
(
	.clk        (clk),
	.reset      (reset),
	.dl_start   (info_start),
	.dl_wr      (info_wr),
	.dl_addr    (info_addr),
	.dl_data    (info_data),
	.trig       (osd_trig),
	.opt        (osd_opt),
	.frame      (vid_vb & ~vb_d & ~pause),
	.cpu_rd     (dbg_rd),
	.cpu_wa     (dbg_wa),
	.code_on    (code_on),
	.code_in0   (code_in0),
	.code_start (code_start),
	.pt_addr    (pt_addr),
	.pt_data    (pt_data),
	.pt_en      (pt_en)
);

wire [63:0] ports = {in_ports[63:22],
                     in_ports[21] & ~(code_on & code_start[1]),
                     in_ports[20:19],
                     in_ports[18] & ~(code_on & code_start[0]),
                     in_ports[17:16],
                     code_on ? ~code_in0 : in_ports[15:0]};

midway_tunit board
(
	.clk            (clk),
	.reset          (reset),
	.pause          (pause),

	.prot_id        (prot_id),
	.mk_turbo       (mk_turbo),
	.big_rom        (big_rom),
	.dcs            (dcs),
	.gfx_mb         (gfx_mb),

	.ram_clr_req    (ram_clr_req),

	.in_ports       (ports),

	.pt_addr        (pt_addr),
	.pt_data        (pt_data),
	.pt_en          (pt_en),

	.snd_wr         (snd_wr),
	.snd_data       (snd_data),
	.snd_rd         (snd_rd),
	.snd_status     (snd_status),
	.snd_rdata      (snd_rdata),

	.cpu_sd_addr    (cpu_sd_addr),
	.cpu_sd_req     (cpu_sd_req),
	.cpu_sd_ack     (cpu_sd_ack),
	.cpu_sd_data    (cpu_sd_data),

	.dma_sd_addr    (dma_sd_addr),
	.dma_sd_req     (dma_sd_req),
	.dma_sd_ack     (dma_sd_ack),
	.dma_sd_data    (dma_sd_data),

	.ram_wr_addr    (ram_wr_addr),
	.ram_wr_data    (ram_wr_data),
	.ram_wr_req     (ram_wr_req),
	.ram_wr_ack     (ram_wr_ack),

	.ddr_busy       (ddr_busy),
	.ddr_burstcnt   (ddr_burstcnt),
	.ddr_addr       (ddr_addr),
	.ddr_dout       (ddr_dout),
	.ddr_dout_ready (ddr_dout_ready),
	.ddr_rd         (ddr_rd),
	.ddr_din        (ddr_din),
	.ddr_be         (ddr_be),
	.ddr_we         (ddr_we),

	.nv_addr        (13'd0),
	.nv_we          (1'b0),
	.nv_din         (16'd0),
	.nv_dout        (nv_dout),
	.cmos_write     (),

	.ce_pix         (ce_pix),
	.vid_r          (vid_r),
	.vid_g          (vid_g),
	.vid_b          (vid_b),
	.vid_hs         (vid_hs),
	.vid_vs         (vid_vs),
	.vid_hb         (vid_hb),
	.vid_vb         (vid_vb),

	.dbg_pc         (dbg_pc),
	.dbg_retire     (dbg_retire),
	.dbg_blit_busy  (dbg_blit_busy),
	.dbg_wr         (dbg_wr),
	.dbg_rd         (dbg_rd),
	.dbg_wa         (dbg_wa),
	.dbg_wdata      (dbg_wdata),
	.dbg_rdata      (dbg_rdata)
);

williams_adpcm sound
(
	.clk        (clk),
	.reset      (reset | dcs | snd_off),
	.pause      (pause),

	.prot_start (sprot_start),
	.prot_end   (sprot_end),

	.cmd_wr     (snd_wr & ~dcs),
	.cmd_data   ({snd_data[15:10], 1'b0, snd_data[8:0]}),
	.irq_state  (),

	.rom_addr   (snd_sd_addr),
	.rom_req    (snd_sd_req),
	.rom_ack    (snd_sd_ack),
	.rom_data   (snd_sd_data),

	.oki_addr   (oki_sd_addr),
	.oki_req    (oki_sd_req),
	.oki_ack    (oki_sd_ack),
	.oki_data   (oki_sd_data),

	.audio      (adpcm_audio)
);

tunit_dcs dcs_board
(
	.clk        (clk),
	.reset      (reset | ~dcs | snd_off),

	.cmd_wr     (snd_wr & dcs),
	.cmd_data   (snd_data),
	.data_rd    (snd_rd & dcs),
	.status     (snd_status),
	.rdata      (snd_rdata),

	.rom_addr   (dcs_sd_addr),
	.rom_req    (dcs_sd_req),
	.rom_ack    (snd_sd_ack),
	.rom_data   (snd_sd_data),

	.audio      (dcs_audio)
);

// SDRAM write channel arbiter (as in the top level; downloads are done by
// the harness writing the model directly, so only the board uses it here)
reg  [24:1] sd_wr_addr;
reg  [15:0] sd_wr_data;
reg         sd_wr_req = 1'b0;
reg         sd_wr_busy = 1'b0;

always @(posedge clk) begin
	if (sd_wr_busy) begin
		if (sd_wr_ack == sd_wr_req) begin
			sd_wr_busy <= 1'b0;
			ram_wr_ack <= ram_wr_req;
		end
	end
	else if (ram_wr_req != ram_wr_ack) begin
		sd_wr_addr <= ram_wr_addr;
		sd_wr_data <= ram_wr_data;
		sd_wr_req  <= ~sd_wr_req;
		sd_wr_busy <= 1'b1;
	end
end

wire [15:0] dq_i, dq_o;
wire        dq_oe;
wire [12:0] sd_a;
wire  [1:0] sd_ba;
wire        sd_ncas, sd_nras, sd_nwe, sd_dqml, sd_dqmh;

sdram sdram
(
	.init        (1'b0),
	.clk         (clk),

	.SDRAM_DQ_I  (dq_i),
	.SDRAM_DQ_O  (dq_o),
	.SDRAM_DQ_OE (dq_oe),
	.SDRAM_A     (sd_a),
	.SDRAM_DQML  (sd_dqml),
	.SDRAM_DQMH  (sd_dqmh),
	.SDRAM_BA    (sd_ba),
	.SDRAM_nCS   (),
	.SDRAM_nWE   (sd_nwe),
	.SDRAM_nRAS  (sd_nras),
	.SDRAM_nCAS  (sd_ncas),
	.SDRAM_CKE   (),
	.SDRAM_CLK   (),

	.ch0_addr    (dcs ? dcs_sd_addr : snd_sd_addr),
	.ch0_req     (dcs ? dcs_sd_req  : snd_sd_req),
	.ch0_ack     (snd_sd_ack),
	.ch0_dout    (snd_sd_data),

	.ch1_addr    (cpu_sd_addr),
	.ch1_req     (cpu_sd_req),
	.ch1_ack     (cpu_sd_ack),
	.ch1_dout    (cpu_sd_data),

	.ch2_addr    (dma_sd_addr),
	.ch2_req     (dma_sd_req),
	.ch2_ack     (dma_sd_ack),
	.ch2_dout    (dma_sd_data),

	.ch3_addr    (oki_sd_addr),
	.ch3_req     (oki_sd_req),
	.ch3_ack     (oki_sd_ack),
	.ch3_dout    (oki_sd_data),

	.wr_addr     (sd_wr_addr),
	.wr_data     (sd_wr_data),
	.wr_be       (2'b11),
	.wr_req      (sd_wr_req),
	.wr_ack      (sd_wr_ack)
);

sdram_model sdram_chip
(
	.clk  (clk),
	.a    (sd_a),
	.ba   (sd_ba),
	.ncas (sd_ncas),
	.nras (sd_nras),
	.nwe  (sd_nwe),
	.dqml (sd_dqml),
	.dqmh (sd_dqmh),
	.dq_o (dq_o),
	.dq_i (dq_i)
);

endmodule

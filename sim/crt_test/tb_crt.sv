//============================================================================
//  tb_crt.sv — testbench top for the analog CRT stage (rtl/video/tunit_crt.sv)
//
//  Copyright (C) 2026 Gm0rk. Distributed under GNU GPL v3 or later.
//
//  Drives tunit_crt with the T-Unit raster as the board makes it after
//  power-up: 96 MHz clock, 8 MHz dot enable (every 12 clocks), 506 dots x
//  289 lines, HSync dots 0-35, picture dots 90-489 (400) on lines 20-273
//  (254), VSync lines 0-2. Each picture dot carries where it came from:
//  R = picture line (0-253), G = dot within the line (low 8 bits),
//  B = 0x80 | dot bit 8. The OSD settings are inputs set by crt_tb.cpp.
//  vtiming drops blank lines as the 34010 does for the 57/60 Hz Video
//  Timing on this raster: 277 lines (275-286 dropped) or 263 (275-288 and
//  3-14 dropped).
//============================================================================

module tb_crt
(
	input             clk,
	input             crt_en,
	input             autow,
	input       [4:0] hsize_osd,
	input       [6:0] hpos_osd,
	input       [4:0] vshift_osd,
	input       [3:0] vsize_osd,
	input             vsmode_osd,
	input       [1:0] vtiming,      // 0 289 lines, 1 277, 2 263

	output            ce_out,       // CE_PIXEL while CRT Adjust is on
	output      [7:0] r,
	output      [7:0] g,
	output      [7:0] b,
	output            hs,
	output            vs,
	output            de,
	output            crt_on
);

reg [3:0] ph = 4'd0;
reg       ce_pix = 1'b0;
always @(posedge clk) begin
	ph     <= (ph == 4'd11) ? 4'd0 : ph + 4'd1;
	ce_pix <= (ph == 4'd10);
end

reg [9:0] hcnt = 10'd0, vcnt = 10'd274;     // the raster starts at VBlank, as the board's
reg [7:0] vr = 8'd0, vg = 8'd0, vb = 8'd0;
reg       vhs = 1'b0, vvs = 1'b0, vhb = 1'b1, vvb = 1'b1;
wire [9:0] px = hcnt - 10'd90;
always @(posedge clk) if (ce_pix) begin
	hcnt <= (hcnt == 10'd505) ? 10'd0 : hcnt + 10'd1;
	if (hcnt == 10'd505)
		vcnt <= (vtiming == 2'd1 && vcnt == 10'd274) ? 10'd287 :
		        (vtiming == 2'd2 && vcnt == 10'd274) ? 10'd0 :
		        (vtiming == 2'd2 && vcnt == 10'd2)   ? 10'd15 :
		        (vcnt == 10'd288) ? 10'd0 : vcnt + 10'd1;
	vhs <= hcnt < 10'd36;
	vvs <= vcnt < 10'd3;
	vhb <= (hcnt < 10'd90) || (hcnt >= 10'd490);
	vvb <= (vcnt < 10'd20) || (vcnt >= 10'd274);
	vr  <= 8'(vcnt - 10'd20);
	vg  <= px[7:0];
	vb  <= {7'b1000000, px[8]};
end

wire rd_ce, de_osd;

tunit_crt dut
(
	.clk         (clk),
	.ce_pix      (ce_pix),
	.crt_en      (crt_en),
	.autow       (autow),
	.scandoubler (1'b0),
	.hsize_osd   (hsize_osd),
	.hpos_osd    (hpos_osd),
	.vshift_osd  (vshift_osd),
	.vsize_osd   (vsize_osd),
	.vsmode_osd  (vsmode_osd),
	.r_in        (vr),
	.g_in        (vg),
	.b_in        (vb),
	.hs_in       (vhs),
	.vs_in       (vvs),
	.hb_in       (vhb),
	.vb_in       (vvb),
	.c_hs        (),
	.c_vs        (),
	.crt_on      (crt_on),
	.rd_ce       (rd_ce),
	.r_out       (r),
	.g_out       (g),
	.b_out       (b),
	.hs_out      (hs),
	.vs_out      (vs),
	.de_osd      (de_osd),
	.centred     (),
	.pic_dots    (),
	.h_eff       (),
	.str_act     ()
);

assign ce_out = rd_ce;
assign de     = de_osd;

endmodule

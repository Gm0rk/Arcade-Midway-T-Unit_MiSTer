//============================================================================
//  T-Unit video output
//
//  Turns the frame store into pixels the way MAME's midtunit scanline_update
//  does:
//    - at the start of every displayed line the row the 34010 points at
//      (DPYADR) is fetched from VRAM into a line buffer
//    - pixels from HEBLNK to HSBLNK read consecutive entries of that row,
//      starting at the column address and wrapping at 512
//    - each 16-bit entry, masked to 15 bits, is a pen of the 32768-colour
//      palette (xRGB 5-5-5)
//
//  The palette RAM lives here: one 32 K x 16 block RAM with two ports. Port A
//  is the CPU's (0x01800000-0x0187FFFF, read and write, all 16 bits kept);
//  port B is the display's read port. Unlike the Y Unit there is no pen map
//  and no autoerase.
//
//  All video signals are delayed by one pixel so the line buffer and palette
//  RAM reads complete between pixel clocks.
//
//  Copyright (C) 2026 Gm0rk - GPL-3.0-or-later
//============================================================================

module tunit_video
(
	input             clk,
	input             reset,

	input             ce_pix,        // 8 MHz pixel enable
	input             ce_vclk,       // 4 MHz VCLK (coincides with every other ce_pix)

	// timing and display address from the 34010
	input       [9:0] hcount,
	input       [9:0] heblnk,
	input       [9:0] hsblnk,
	input             hsync_in,
	input             vsync_in,
	input             hblank_in,
	input             vblank_in,
	input             disp_en,
	input             line_start,
	input             line_vis,
	input      [11:0] line_row,
	input      [13:0] line_col,

	// palette RAM, CPU port (read data the clock after the address)
	input             pal_we,
	input      [14:0] pal_addr,
	input      [15:0] pal_wdata,
	output     [15:0] pal_q,

	// VRAM row fetch (see tunit_vram)
	output reg        disp_req,
	input             disp_ack,
	output reg  [8:0] disp_row,
	input             lb_we,
	input       [6:0] lb_addr,
	input      [63:0] lb_data,

	// video out
	output reg  [7:0] r,
	output reg  [7:0] g,
	output reg  [7:0] b,
	output reg        hsync,
	output reg        vsync,
	output reg        hblank,
	output reg        vblank
);

//----------------------------------------------------------------------------
// Line buffer: two banks of one 512-entry row (128 beats of 4 entries)
//----------------------------------------------------------------------------

reg  [63:0] linebuf [0:255];
reg         fill_bank;           // bank the current fetch writes
reg         show_bank;           // bank being displayed
reg   [7:0] lb_raddr;
reg  [63:0] lb_q;

always @(posedge clk) begin
	if (lb_we) linebuf[{fill_bank, lb_addr}] <= lb_data;
	lb_q <= linebuf[lb_raddr];
end

//----------------------------------------------------------------------------
// Palette RAM (32 K x 16), true dual port
//
// An explicit altsyncram: Quartus 17 does not reliably infer a true
// dual-port RAM from a behavioural array (the Y Unit core's CMOS fell back to
// registers). Addresses and write data are registered inside the block, the
// outputs are not, so each q holds the word addressed on the previous clock.
// A behavioural model for simulation lives in sim/, outside the core.
//----------------------------------------------------------------------------

reg  [14:0] pal_raddr;           // display port address
wire [15:0] pal_disp;

altsyncram #(
	.operation_mode                     ("BIDIR_DUAL_PORT"),
	.intended_device_family             ("Cyclone V"),
	.lpm_type                           ("altsyncram"),
	.ram_block_type                     ("M10K"),
	.width_a                            (16),
	.widthad_a                          (15),
	.numwords_a                         (32768),
	.width_b                            (16),
	.widthad_b                          (15),
	.numwords_b                         (32768),
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
) palram
(
	// port A: TMS34010
	.clock0         (clk),
	.address_a      (pal_addr),
	.data_a         (pal_wdata),
	.wren_a         (pal_we),
	.q_a            (pal_q),

	// port B: display (read only)
	.clock1         (1'b1),
	.address_b      (pal_raddr),
	.data_b         (16'h0000),
	.wren_b         (1'b0),
	.q_b            (pal_disp),

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

//----------------------------------------------------------------------------
// Row fetch
//----------------------------------------------------------------------------

reg   [8:0] col_start;           // first entry of the line
reg         line_on;             // this line shows pixels

always @(posedge clk) begin
	if (reset) begin
		disp_req  <= disp_ack;
		fill_bank <= 1'b0;
		show_bank <= 1'b0;
		line_on   <= 1'b0;
	end
	else if (line_start) begin
		line_on <= line_vis & disp_en;
		if (line_vis & disp_en) begin
			// fetch this line's row; it is shown from this line's HEBLNK on
			disp_row  <= line_row[8:0];
			disp_req  <= ~disp_req;
			fill_bank <= ~fill_bank;
			show_bank <= ~fill_bank;
			col_start <= {line_col[7:0], 1'b0};
		end
	end
end

//----------------------------------------------------------------------------
// Pixel pipeline
//
// The cycle after each ce_pix the beam position is captured (HCOUNT has moved
// on by then if a VCLK came with it) and the line buffer is addressed. The
// entry and palette lookups finish well before the next ce_pix, which
// outputs the colour together with the timing signals captured with it.
//----------------------------------------------------------------------------

reg         ce_pix_d, vclk_d;
reg   [3:0] stage;
reg   [1:0] lane;
reg         a_hs, a_vs, a_hb, a_vb, a_on;
reg  [14:0] a_rgb;

wire [10:0] pix_pos  = {hcount, ~vclk_d};                 // pixel within the line
wire [10:0] act_x    = pix_pos - {heblnk, 1'b0};          // pixel within the active area
wire  [8:0] entry    = col_start + act_x[8:0];

wire [15:0] ent      = lb_q[{lane, 4'b0000} +: 16];

// MAME's pal5bit: 5-bit colour to 8 bits
function automatic [7:0] pal5(input [4:0] c);
	pal5 = {c, c[4:2]};
endfunction

always @(posedge clk) begin
	ce_pix_d <= ce_pix;
	if (ce_pix) vclk_d <= ce_vclk;

	stage <= {stage[2:0], 1'b0};

	if (ce_pix_d) begin
		a_hs     <= hsync_in;
		a_vs     <= vsync_in;
		a_hb     <= hblank_in;
		a_vb     <= vblank_in;
		a_on     <= line_on & ~hblank_in & ~vblank_in;
		lb_raddr <= {show_bank, entry[8:2]};
		lane     <= entry[1:0];
		stage[0] <= 1'b1;
	end
	if (stage[1])                       // line buffer data valid: the pen
		pal_raddr <= ent[14:0];
	if (stage[3])                       // palette data valid
		a_rgb <= a_on ? pal_disp[14:0] : 15'd0;

	if (ce_pix) begin
		r      <= pal5(a_rgb[14:10]);
		g      <= pal5(a_rgb[9:5]);
		b      <= pal5(a_rgb[4:0]);
		hsync  <= a_hs;
		vsync  <= a_vs;
		hblank <= a_hb;
		vblank <= a_vb;
	end
end

endmodule

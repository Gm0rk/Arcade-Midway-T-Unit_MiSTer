//============================================================================
//  T-Unit DMA blitter
//
//  Draws a rectangle of graphics ROM pixels into the 512 x 512 frame store,
//  one 16-bit entry {palette page, pixel} per drawn pixel. It follows MAME's
//  midtunit_video_device::dma_w and dma_draw (midtunit_v.cpp) step for step:
//
//    - sources are a bit stream: 1-8 bits per pixel (command bits 12-14,
//      0 = 8), read at any bit address
//    - "skip" compression (command bit 7): every row starts with a byte
//      whose low and high nibbles are the pixels left out at the start and
//      the end of the row, scaled by 1 << pre/postskip (bits 8-9, 10-11)
//    - start/end skip from register 0: with command bit 6 the low byte is
//      the start skip and the high byte the end skip (MK, MK2); without it
//      the whole word is the end skip (NBA Jam)
//    - X and Y scaling in 8.8 fixed point (registers 10/11, 0 = 1.0): each
//      destination pixel/row advances the source by the integer steps of the
//      accumulated scale
//    - X and Y flip (command bits 4, 5): the destination runs backwards
//    - four clip edges checked per pixel (top/bottom per row); registers 12
//      and 13 write the top/bottom or, with register 15 bit 5 clear, the
//      left/right clip (MAME's two register banks)
//    - X is 10 bits and wraps at 1024, Y 9 bits; pixels at X 512-1023 land
//      in the next row, as MAME's frame store pointer arithmetic puts them
//    - completion: command bit 15 reads back set, and INT1 rises, 41 ns per
//      pixel of the unclipped (scaled) area after the start; any write to
//      the command register drops INT1
//
//  Structure
//  ---------
//  A row state machine does what MAME does once per row (skip byte, the
//  divisions of the scaled skips, clipping, end skip, the source advance to
//  the next row). The pixels of a row then run through a two-stage pipeline
//  at up to one pixel per clock:
//    stage 1  extracts the pixel at bit address o from a two-line window of
//             source data and steps o, the X accumulator and the
//             destination column
//    stage 2  decides what to write (MAME's PIXEL_SKIP/COLOR/COPY per mode)
//             and assembles 4-entry beats for the row buffer
//  Finished rows go to the VRAM controller as one burst (double buffered).
//
//  Source data comes from SDRAM as 8-byte lines (byte addresses of MAME's
//  "video" region, little endian); a line and its successor are kept so a
//  pixel or skip byte that straddles two lines can be read.
//
//  Copyright (C) 2026 Gm0rk - GPL-3.0-or-later
//============================================================================

module tunit_dma
(
	input             clk,
	input             reset,

	input             big_rom,       // MK2: graphics offsets are not reduced by 0x2000000
	input             fast,          // count the completion timer down by 2 this clock
	                                 // (shorter video frames, see midway_tunit.sv)

	// register file, CPU side (16-bit words 0-15)
	input             reg_wr,
	input       [3:0] reg_idx,
	input      [15:0] reg_wdata,
	output     [15:0] reg_rdata,
	output            reg_wr_wait,   // hold a new start until the current blit has drawn
	output     [15:0] palette_reg,   // DMA_PALETTE, also used by CPU VRAM writes

	output reg        irq,           // INT1

	// graphics ROM, 8-byte lines from SDRAM (line index in the region)
	output reg [25:0] gfx_line,
	output reg        gfx_req,       // toggle
	input             gfx_ack,
	input      [63:0] gfx_data,

	// VRAM row write-back (see tunit_vram)
	output reg        blt_req,       // toggle
	input             blt_ack,
	output reg  [8:0] blt_row,
	output reg  [7:0] blt_lo,
	output reg  [7:0] blt_hi,
	input       [7:0] blt_raddr,
	output     [63:0] blt_q,
	output      [7:0] blt_be,

	// status for simulation
	output            busy
);

//----------------------------------------------------------------------------
// Registers (MAME's m_dma_register, 18 words; 16 and 17 are the left/right
// clips reached through offsets 12/13 in register bank 0)
//----------------------------------------------------------------------------

localparam R_LRSKIP = 0, R_COMMAND = 1, R_OFFSETLO = 2, R_OFFSETHI = 3,
           R_XSTART = 4, R_YSTART = 5, R_WIDTH = 6, R_HEIGHT = 7,
           R_PALETTE = 8, R_COLOR = 9, R_SCALE_X = 10, R_SCALE_Y = 11,
           R_TOPCLIP = 12, R_BOTCLIP = 13, R_TEST = 14, R_CONFIG = 15,
           R_LEFTCLIP = 16, R_RIGHTCLIP = 17;

reg  [15:0] r [0:17];

// write mapping: offsets 12/13 go to the left/right clips in bank 0
wire        regbank  = r[R_CONFIG][5];
wire  [4:0] wr_reg   = (reg_idx == 4'd12 && !regbank) ? 5'd16 :
                       (reg_idx == 4'd13 && !regbank) ? 5'd17 : {1'b0, reg_idx};

// reads: register 0 reads as register 1 (MAME, for Rampage/Open Ice)
assign reg_rdata   = r[(reg_idx == 4'd0) ? 5'd1 : {1'b0, reg_idx}];
assign palette_reg = r[R_PALETTE];

//----------------------------------------------------------------------------
// Row buffers: 2 banks x 256 beats of {generation, byte enables, data}
//
// A row's window is 256 beats (X 0-1023). Only the beats between the first
// and the last one written go out, and every beat the pixels pass is stored
// with its byte enables, so stale beats only lie inside that range when X
// wrapped from 1023 to 0 within a row. The generation tag catches those: a
// beat stored for an earlier row of the bank has another generation and its
// byte enables are dropped on the way out. When a bank's generation wraps,
// the bank is cleared first.
//----------------------------------------------------------------------------

reg  [79:0] rowbuf [0:511];
reg         rb_we;
reg   [8:0] rb_waddr;
reg  [79:0] rb_wdata;
reg         flush_bank;                 // bank the VRAM controller is reading
reg  [79:0] rb_q;

always @(posedge clk) begin
	if (rb_we) rowbuf[rb_waddr] <= rb_wdata;
	rb_q <= rowbuf[{flush_bank, blt_raddr}];
end

reg   [7:0] gen [0:1];                  // current generation of each bank
reg   [8:0] rst_clr = 9'd0;             // row buffer entry being cleared during reset
assign blt_q  = rb_q[63:0];
assign blt_be = (rb_q[79:72] == gen[flush_bank]) ? rb_q[71:64] : 8'h00;

//----------------------------------------------------------------------------
// Shared arithmetic: a restoring divider (18-bit dividend, 16-bit divisor,
// one quotient bit per clock) and one registered 18 x 18 multiplier
//----------------------------------------------------------------------------

reg         div_go;                     // start (operands in dv_n / dv_d)
reg  [17:0] dv_n;                       // dividend
reg  [15:0] dv_d;                       // divisor (never 0)
reg  [17:0] div_n;                      // dividend bits still to shift in
reg  [15:0] div_d;
reg  [17:0] div_q;
reg  [16:0] div_r;
reg   [4:0] div_cnt;
wire        div_busy = (div_cnt != 5'd0);

wire [17:0] div_try = {div_r, div_n[17]};           // remainder with the next dividend bit
always @(posedge clk) begin
	if (reset)
		div_cnt <= 5'd0;
	else if (div_go) begin
		div_n   <= dv_n;
		div_d   <= dv_d;
		div_r   <= 17'd0;
		div_q   <= 18'd0;
		div_cnt <= 5'd18;
	end
	else if (div_busy) begin
		div_n <= {div_n[16:0], 1'b0};
		if (div_try >= {2'b00, div_d}) begin
			div_r <= 17'(div_try - {2'b00, div_d});
			div_q <= {div_q[16:0], 1'b1};
		end
		else begin
			div_r <= div_try[16:0];
			div_q <= {div_q[16:0], 1'b0};
		end
		div_cnt <= div_cnt - 5'd1;
	end
end
wire        div_done = !div_go && !div_busy;    // result in div_q (after a start)

// The multiplier's product is ready two clocks after its inputs are set:
// states that use it count mwait 0, 1, 2 and read mul_p at 2.
reg  [17:0] mul_a, mul_b;
reg  [17:0] mul_ra, mul_rb;
reg   [1:0] mwait;
reg  [35:0] mul_p;
always @(posedge clk) begin
	mul_ra <= mul_a;
	mul_rb <= mul_b;
	mul_p  <= mul_ra * mul_rb;          // product of the inputs set two clocks ago
end

//----------------------------------------------------------------------------
// Blit parameters (latched at the start, as MAME's m_dma_state)
//----------------------------------------------------------------------------

reg  [15:0] cmd;
reg   [3:0] bpp;                        // 1-8
reg   [7:0] pmask;                      // (1 << bpp) - 1
reg   [9:0] xpos;
reg   [8:0] ypos;
reg   [9:0] width, height;
reg  [15:0] pal, color;
reg  [15:0] xstep, ystep;
reg   [8:0] topclip, botclip;
reg   [9:0] leftclip, rightclip;
reg  [15:0] startskip, endskip;
reg  [31:0] offset;                     // bit address of the current row
reg  [12:0] rowbits;                    // width x bpp
reg  [10:0] adv_a, adv_b;               // source bits per pixel step without/with the carry

wire  [3:0] mode   = cmd[3:0];
wire        xflip  = cmd[4];
wire        yflip  = cmd[5];
wire        skipc  = cmd[7];            // skip-compressed rows
wire  [1:0] preskip  = cmd[9:8];
wire  [1:0] postskip = cmd[11:10];
wire        unity_x = (xstep == 16'h0100);

//----------------------------------------------------------------------------
// Source window: l0 holds the line of bit address o, l1 the next line
//----------------------------------------------------------------------------

reg  [31:0] o;                          // source bit address (MAME's o)
reg  [25:0] l0_tag, l1_tag;
reg  [63:0] l0_data, l1_data;
reg         l0_ok, l1_ok;
reg         fetching, fetch_l1;
reg  [25:0] fetch_tag;
reg   [3:0] rd_bits;                    // bits the current read needs (bpp, or 8 for a skip byte)

wire [25:0] o_tag   = o[31:6];
wire        need_l1 = ({1'b0, o[5:0]} + {3'b000, rd_bits}) > 7'd64;
wire        l0_hit  = l0_ok && (l0_tag == o_tag);
wire        have    = l0_hit && (!need_l1 || l1_ok);
wire [127:0] win    = {l1_data, l0_data};
wire  [7:0] rd_byte = 8'(win >> o[5:0]);           // 8 bits from bit address o
wire  [7:0] rd_pix  = rd_byte & pmask;

//----------------------------------------------------------------------------
// State
//----------------------------------------------------------------------------

localparam B_IDLE   = 6'd0;
localparam B_START  = 6'd1;   // offset relocation, completion time
localparam B_TIME1  = 6'd2;
localparam B_TIME2  = 6'd3;
localparam B_TIME3  = 6'd4;
localparam B_ROW    = 6'd5;   // next row
localparam B_SKIPB  = 6'd6;   // read the row's skip byte
localparam B_SKIPB2 = 6'd7;   // use it
localparam B_PRE1   = 6'd8;   // scaled preskip: tx = pre / xstep
localparam B_PRE2   = 6'd9;
localparam B_YCLIP  = 6'd10;
localparam B_SS1    = 6'd11;  // start skip
localparam B_SSU1   = 6'd12;  // start skip, unscaled: pixels, bits, address
localparam B_SSU2   = 6'd13;
localparam B_SS2    = 6'd14;
localparam B_SS3    = 6'd15;
localparam B_ESKIP  = 6'd16;  // end skip, pixel loop set-up
localparam B_PIX    = 6'd17;  // pixel pipeline
localparam B_PIXEND = 6'd18;
localparam B_ROWEND = 6'd19;
localparam B_FLUSH  = 6'd20;
localparam B_ADV    = 6'd21;  // advance to the next row
localparam B_ADV2   = 6'd22;
localparam B_ADV3   = 6'd23;  // compressed rows: bits of the row just done
localparam B_ADV4   = 6'd24;
localparam B_YSKIP  = 6'd25;  // walk skipped compressed rows (Y scaling)
localparam B_YSK2   = 6'd26;  // one skipped row: pixels, bits, address
localparam B_YSK3   = 6'd27;
localparam B_YSK4   = 6'd28;
localparam B_NEXT   = 6'd29;
localparam B_CLR    = 6'd30;  // clear a row buffer bank (generation wrap)
localparam B_DRAIN  = 6'd31;
localparam B_WAIT   = 6'd32;  // drawn; wait for the completion time

reg   [5:0] bstate;
reg         start_pending;
reg  [39:0] timer;                      // clk cycles until completion may be signalled

// row state
reg  [19:0] iy;                         // Y accumulator, 8.8
reg   [8:0] sy;                         // destination row
reg   [9:0] sx;                         // destination column
reg  [11:0] ixi;                        // X accumulator, integer part
reg   [7:0] ixf;                        //                fraction
reg   [6:0] pre_px, post_px;            // this row's skip nibbles, in pixels
reg  signed [17:0] w_eff;               // pixels of the row to draw (MAME's width >> 8)
reg   [8:0] ty;                         // source rows to advance
reg   [7:0] skb;                        // a skip byte, registered from the source window
reg  signed [11:0] t_w;                 // pipelined row-advance arithmetic:
reg  [13:0] t_tb;                       //   pixels, then bits
reg  [31:0] o2;                         // source walk for Y-scaled skip rows

// pipeline stage 2
reg         s2_v;
reg   [7:0] s2_pix;
reg         s2_zero;
reg   [9:0] s2_sx;
reg         s2_in;

// row assembly
reg         fill_bank;
reg         flush_busy;
reg  [63:0] acc;
reg   [7:0] acc_be;
reg   [7:0] acc_q;                      // beat index of acc
reg         acc_valid;
reg         row_any;
reg   [7:0] row_lo, row_hi;
reg   [8:0] clr_a;

assign busy = (bstate != B_IDLE) && (bstate != B_WAIT);

// MAME: a start arriving while the previous blit is still drawing waits
wire        start_wr    = reg_wr && (wr_reg == 5'd1) && reg_wdata[15];
assign reg_wr_wait      = start_wr && busy;

// stage 1 continue condition: MAME's "while (ix < width)" in integer pixels
wire        px_more = $signed({6'd0, ixi}) < w_eff;

// X step: ix += xstep, o += bpp * (pixels the integer part moved)
wire  [8:0] fsum   = {1'b0, ixf} + {1'b0, xstep[7:0]};
wire [11:0] ixi_n  = ixi + {4'd0, xstep[15:8]} + {11'd0, fsum[8]};
// both sums in parallel, picked by the fraction's carry, so the 32-bit add
// does not wait for the 8-bit one
wire [31:0] o_na   = o + {21'd0, adv_a};
wire [31:0] o_nb   = o + {21'd0, adv_b};
wire [31:0] o_n    = fsum[8] ? o_nb : o_na;
wire  [9:0] sx_n   = xflip ? (sx - 10'd1) : (sx + 10'd1);
wire        in_clip = (sx >= leftclip) && (sx <= rightclip);

// stage 2: what to write (MAME's PIXEL_SKIP / PIXEL_COLOR / PIXEL_COPY)
reg         px_wr;
reg  [15:0] px_val;
always @(*) begin
	px_wr  = 1'b0;
	px_val = pal | {8'h00, s2_pix};
	case (mode)
		4'd1:         begin px_wr = s2_zero; px_val = pal; end
		4'd2:         px_wr = ~s2_zero;
		4'd3:         px_wr = 1'b1;
		4'd4, 4'd5:   begin px_wr = s2_zero; px_val = color; end
		4'd6, 4'd7:   begin px_wr = 1'b1; if (s2_zero) px_val = color; end
		4'd8, 4'd10:  begin px_wr = ~s2_zero; px_val = color; end
		4'd9, 4'd11:  begin px_wr = 1'b1; px_val = s2_zero ? pal : color; end
		4'd12, 4'd13,
		4'd14, 4'd15: begin px_wr = 1'b1; px_val = color; end
		default:      px_wr = 1'b0;
	endcase
	px_wr = px_wr & s2_in;
end

// bits of w source pixels (w x bpp), for the row advance
function automatic [13:0] times_bpp(input [10:0] w, input [3:0] b);
	times_bpp = (b[0] ? {3'd0, w} : 14'd0) + (b[1] ? {2'd0, w, 1'b0} : 14'd0) +
	            (b[2] ? {1'd0, w, 2'b0} : 14'd0) + (b[3] ? {w, 3'b0} : 14'd0);
endfunction

// skip nibbles of the registered skip byte, in pixels
wire  [6:0] nib_pre  = {3'd0, skb[3:0]} << preskip;
wire  [6:0] nib_post = {3'd0, skb[7:4]} << postskip;

// next Y accumulator and the source rows it moves (ty)
wire [19:0] iy_n    = iy + {4'd0, ystep};
wire  [8:0] ty_n    = 9'(iy_n[19:8] - iy[19:8]);

// MAME row advance: source pixels of a compressed row (width - pre - post),
// for the row just drawn (w_left) and for a skipped row's skip byte (w_skip)
wire signed [11:0] w_left = $signed({2'd0, width}) - $signed({5'd0, pre_px})  - $signed({5'd0, post_px});
wire signed [11:0] w_skip = $signed({2'd0, width}) - $signed({5'd0, nib_pre}) - $signed({5'd0, nib_post});

// graphics offset relocation (MAME dma_w): small-ROM boards see the ROM at
// 0x2000000 in the offset space; offsets from 0xF8000000 wrap to 0
wire [31:0] off_t1  = (!big_rom && offset >= 32'h0200_0000) ? offset - 32'h0200_0000 : offset;
wire [31:0] off_rel = (off_t1 >= 32'hF800_0000) ? off_t1 - 32'hF800_0000 : off_t1;
wire        src_ok  = (offset < 32'h1000_0000);   // after relocation (from B_TIME1 on)

integer i;
always @(posedge clk) begin
	rb_we  <= 1'b0;
	div_go <= 1'b0;

	if (reset) begin
		// the row buffer is cleared (generation 0, no bytes) while in reset
		// (it lasts at least 4096 clocks), so no entry left from before can
		// match the generations, which restart at 1
		rb_we    <= 1'b1;
		rb_waddr <= rst_clr;
		rb_wdata <= 80'd0;
		rst_clr  <= rst_clr + 9'd1;
		for (i = 0; i < 18; i = i + 1)
			r[i] <= 16'd0;
		bstate        <= B_IDLE;
		irq           <= 1'b0;
		flush_busy    <= 1'b0;
		fill_bank     <= 1'b0;
		flush_bank    <= 1'b0;
		gen[0]        <= 8'd1;
		gen[1]        <= 8'd1;
		l0_ok         <= 1'b0;
		l1_ok         <= 1'b0;
		fetching      <= 1'b0;
		timer         <= 40'd0;
		blt_req       <= blt_ack;
		gfx_req       <= gfx_ack;
		start_pending <= 1'b0;
		s2_v          <= 1'b0;
	end
	else begin
		if (fast && (timer > 40'd1))
			timer <= timer - 40'd2;
		else if (timer != 40'd0)
			timer <= timer - 40'd1;

		// ---- flush handshake ----
		if (flush_busy && (blt_req == blt_ack))
			flush_busy <= 1'b0;

		// ---- source window: l0 = line of o, l1 = the line after it ----
		if (fetching && (gfx_req == gfx_ack)) begin
			fetching <= 1'b0;
			if (!fetch_l1) begin
				if (fetch_tag == o_tag) begin
					l0_data <= gfx_data; l0_tag <= fetch_tag; l0_ok <= 1'b1; l1_ok <= 1'b0;
				end
			end
			else if (l0_ok && fetch_tag == l0_tag + 26'd1) begin
				l1_data <= gfx_data; l1_tag <= fetch_tag; l1_ok <= 1'b1;
			end
		end
		else if (!fetching && (bstate == B_SKIPB || bstate == B_PIX || bstate == B_YSKIP)) begin
			if (!l0_hit) begin
				if (l1_ok && l1_tag == o_tag) begin
					// o moved on to the next line: promote it
					l0_data <= l1_data; l0_tag <= l1_tag; l0_ok <= 1'b1; l1_ok <= 1'b0;
				end
				else begin
					fetching  <= 1'b1;
					fetch_l1  <= 1'b0;
					fetch_tag <= o_tag;
					gfx_line  <= o_tag;
					gfx_req   <= ~gfx_req;
				end
			end
			else if (!l1_ok) begin
				fetching  <= 1'b1;
				fetch_l1  <= 1'b1;
				fetch_tag <= l0_tag + 26'd1;
				gfx_line  <= l0_tag + 26'd1;
				gfx_req   <= ~gfx_req;
			end
		end

		// ---- stage 2: assemble destination beats ----
		if (s2_v) begin
			// a new destination beat: store the finished one first
			if (acc_valid && (s2_sx[9:2] != acc_q)) begin
				rb_we    <= 1'b1;
				rb_waddr <= {fill_bank, acc_q};
				rb_wdata <= {gen[fill_bank], acc_be, acc};
			end
			if (!acc_valid || (s2_sx[9:2] != acc_q)) begin
				acc_q     <= s2_sx[9:2];
				acc_valid <= 1'b1;
			end
			if (px_wr) begin
				acc[{s2_sx[1:0], 4'b0000} +: 16] <= px_val;
				if (!row_any || s2_sx[9:2] < row_lo) row_lo <= s2_sx[9:2];
				if (!row_any || s2_sx[9:2] > row_hi) row_hi <= s2_sx[9:2];
				row_any <= 1'b1;
				if (acc_valid && (s2_sx[9:2] == acc_q))
					acc_be[{s2_sx[1:0], 1'b0} +: 2] <= 2'b11;
				else
					acc_be <= 8'd3 << {s2_sx[1:0], 1'b0};
			end
			else if (!(acc_valid && (s2_sx[9:2] == acc_q)))
				acc_be <= 8'd0;
		end
		s2_v <= 1'b0;

		case (bstate)
			B_IDLE: if (start_pending) begin
				// MAME dma_w: fill in m_dma_state from the registers
				start_pending <= 1'b0;
				cmd       <= r[R_COMMAND];
				bpp       <= (r[R_COMMAND][14:12] == 3'd0) ? 4'd8 : {1'b0, r[R_COMMAND][14:12]};
				pmask     <= (r[R_COMMAND][14:12] == 3'd0) ? 8'hFF : 8'((9'd1 << r[R_COMMAND][14:12]) - 9'd1);
				xpos      <= r[R_XSTART][9:0];
				ypos      <= r[R_YSTART][8:0];
				width     <= r[R_WIDTH][9:0];
				height    <= r[R_HEIGHT][9:0];
				pal       <= r[R_PALETTE] & 16'h7F00;
				color     <= (r[R_PALETTE] & 16'h7F00) | {8'h00, r[R_COLOR][7:0]};
				xstep     <= (r[R_SCALE_X] != 16'd0) ? r[R_SCALE_X] : 16'h0100;
				ystep     <= (r[R_SCALE_Y] != 16'd0) ? r[R_SCALE_Y] : 16'h0100;
				topclip   <= r[R_TOPCLIP][8:0];
				botclip   <= r[R_BOTCLIP][8:0];
				leftclip  <= r[R_LEFTCLIP][9:0];
				rightclip <= r[R_RIGHTCLIP][9:0];
				// drawing mode C needs no pixel data: its offset is 0
				offset    <= (r[R_COMMAND][3:0] == 4'hC) ? 32'd0 : {r[R_OFFSETHI], r[R_OFFSETLO]};
				// MK/MK2 (bit 6): low byte start skip, high byte end skip;
				// otherwise the whole word is the end skip
				startskip <= r[R_COMMAND][6] ? {8'd0, r[R_LRSKIP][7:0]} : 16'd0;
				endskip   <= r[R_COMMAND][6] ? {8'd0, r[R_LRSKIP][15:8]} : r[R_LRSKIP];
				bstate    <= B_START;
			end

			B_START: begin
				// graphics offset relocation, in MAME's order
				offset  <= off_rel;
				rowbits <= 13'(times_bpp({1'b0, width}, bpp));
				adv_a   <= 11'(times_bpp({3'd0, xstep[15:8]}, bpp));
				adv_b   <= 11'(times_bpp({3'd0, xstep[15:8]}, bpp) + {10'd0, bpp});
				// completion time: pixels = w x h, or the scaled counts
				// ((w << 8) / xstep) x ((h << 8) / ystep)
				if (xstep == 16'h0100 && ystep == 16'h0100) begin
					mul_a  <= {8'd0, width};
					mul_b  <= {8'd0, height};
					mwait  <= 2'd0;
					bstate <= B_TIME3;
				end
				else begin
					dv_n   <= {width, 8'd0};
					dv_d   <= xstep;
					div_go <= 1'b1;
					bstate <= B_TIME1;
				end
			end

			B_TIME1: if (div_done) begin
				mul_a  <= div_q;
				dv_n   <= {height, 8'd0};
				dv_d   <= ystep;
				div_go <= 1'b1;
				bstate <= B_TIME2;
			end

			B_TIME2: if (div_done) begin
				mul_b  <= div_q;
				mwait  <= 2'd0;
				bstate <= B_TIME3;
			end

			B_TIME3: begin
				mwait <= mwait + 2'd1;
				if (mwait == 2'd2) begin
					// 41 ns per pixel = 3.9375 clk at 96 MHz; nothing if the
					// source was out of range (MAME skips the draw: 0 pixels)
					timer  <= src_ok ? ((40'(mul_p) << 6) - 40'(mul_p)) >> 4 : 40'd0;
					iy     <= 20'd0;
					sy     <= ypos;
					l0_ok  <= 1'b0;
					l1_ok  <= 1'b0;
					bstate <= (!src_ok || mode == 4'd0) ? B_DRAIN : B_ROW;
				end
			end

			B_ROW: begin
				if (iy >= {2'b00, height, 8'd0})
					bstate <= B_DRAIN;
				else begin
					o       <= offset;
					sx      <= xpos;
					ixi     <= 12'd0;
					ixf     <= 8'd0;
					pre_px  <= 7'd0;
					post_px <= 7'd0;
					rd_bits <= 4'd8;
					bstate  <= skipc ? B_SKIPB : B_YCLIP;
				end
			end

			B_SKIPB: if (have) begin
				// the row's skip byte: pixels left out at the start and end
				skb    <= rd_byte;
				o      <= o + 32'd8;
				bstate <= B_SKIPB2;
			end

			B_SKIPB2: begin
				pre_px  <= nib_pre;
				post_px <= nib_post;
				if (unity_x) begin
					// tx = pre / 0x100 is the nibble itself, ix = tx x 0x100
					ixi    <= {5'd0, nib_pre};
					sx     <= xflip ? (sx - {3'd0, nib_pre}) : (sx + {3'd0, nib_pre});
					bstate <= B_YCLIP;
				end
				else begin
					dv_n   <= {3'd0, nib_pre, 8'd0};
					dv_d   <= xstep;
					div_go <= 1'b1;
					bstate <= B_PRE1;
				end
			end

			B_PRE1: if (div_done) begin
				// tx = pre / xstep: sx moves tx, ix = tx x xstep
				sx     <= xflip ? (sx - div_q[9:0]) : (sx + div_q[9:0]);
				mul_a  <= div_q;
				mul_b  <= {2'd0, xstep};
				mwait  <= 2'd0;
				bstate <= B_PRE2;
			end

			B_PRE2: begin
				mwait <= mwait + 2'd1;
				if (mwait == 2'd2) begin
					ixi    <= mul_p[19:8];
					ixf    <= mul_p[7:0];
					bstate <= B_YCLIP;
				end
			end

			B_YCLIP: begin
				rd_bits <= bpp;
				if (sy < topclip || sy > botclip)
					bstate <= B_ADV;              // clipped row: only the source moves on
				else
					bstate <= B_SS1;
			end

			B_SS1: begin
				// start skip: if ix < startskip, skip whole X steps of source
				if ({ixi, ixf} < {startskip[11:0], 8'd0}) begin
					if (unity_x) begin
						// ix is a whole number of pixels: jump straight there
						t_w    <= 12'(startskip[10:0] - ixi[10:0]);
						bstate <= B_SSU1;
					end
					else begin
						dv_n   <= 18'({2'b00, startskip[9:0], 8'd0} - {ixi, ixf});
						dv_d   <= xstep;
						div_go <= 1'b1;
						bstate <= B_SS2;
					end
				end
				else
					bstate <= B_ESKIP;
			end

			B_SSU1: begin
				t_tb   <= times_bpp(t_w[10:0], bpp);
				bstate <= B_SSU2;
			end

			B_SSU2: begin
				o      <= o + {18'd0, t_tb};
				ixi    <= startskip[11:0];
				bstate <= B_ESKIP;
			end

			B_SS2: if (div_done) begin
				mul_a  <= div_q;
				mul_b  <= {2'd0, xstep};
				mwait  <= 2'd0;
				bstate <= B_SS3;
			end

			B_SS3: begin
				mwait <= mwait + 2'd1;
				if (mwait == 2'd2) begin
					// tx = whole steps x xstep: ix += tx, o += (tx >> 8) x bpp
					{ixi, ixf} <= {ixi, ixf} + mul_p[19:0];
					o          <= o + {18'd0, times_bpp(mul_p[18:8], bpp)};
					bstate     <= B_ESKIP;
				end
			end

			B_ESKIP: begin
				// width -= post; then the end skip limit (MAME compares whole
				// pixels: (width >> 8) > m_dma_state.width - endskip)
				if ($signed({8'd0, width}) - $signed({11'd0, post_px}) >
				    $signed({8'd0, width}) - $signed({2'd0, endskip}))
					w_eff <= $signed({8'd0, width}) - $signed({2'd0, endskip});
				else
					w_eff <= $signed({8'd0, width}) - $signed({11'd0, post_px});
				acc_valid <= 1'b0;
				acc_be    <= 8'd0;
				row_any   <= 1'b0;
				bstate    <= B_PIX;
			end

			B_PIX: begin
				// stage 1: one pixel per clock while the source is at hand
				if (!px_more)
					bstate <= B_PIXEND;
				else if (have) begin
					s2_v    <= 1'b1;
					s2_pix  <= rd_pix;
					s2_zero <= (rd_pix == 8'd0);
					s2_sx   <= sx;
					s2_in   <= in_clip;
					sx      <= sx_n;
					ixi     <= ixi_n;
					ixf     <= fsum[7:0];
					o       <= o_n;
				end
			end

			B_PIXEND: bstate <= B_ROWEND;        // stage 2 takes the last pixel

			B_ROWEND: begin
				// store the last beat, then hand the row to the VRAM controller
				if (acc_valid) begin
					rb_we    <= 1'b1;
					rb_waddr <= {fill_bank, acc_q};
					rb_wdata <= {gen[fill_bank], acc_be, acc};
				end
				bstate <= B_FLUSH;
			end

			B_FLUSH: if (!row_any || !flush_busy) begin
				// rows where nothing was drawn need no VRAM write at all
				if (row_any) begin
					flush_busy <= 1'b1;
					flush_bank <= fill_bank;
					fill_bank  <= ~fill_bank;
					blt_row    <= sy;
					blt_lo     <= row_lo;
					blt_hi     <= row_hi;
					blt_req    <= ~blt_req;
					gen[~fill_bank] <= gen[~fill_bank] + 8'd1;
				end
				bstate <= B_ADV;
			end

			B_ADV: begin
				// MAME: next destination row; ty = source rows to move on
				sy     <= yflip ? (sy - 9'd1) : (sy + 9'd1);
				iy     <= iy_n;
				ty     <= ty_n;
				mul_a  <= {9'd0, ty_n};
				mul_b  <= {5'd0, rowbits};
				mwait  <= 2'd0;
				bstate <= B_ADV2;
			end

			B_ADV2: begin
				if (!skipc) begin
					// offset += ty x width x bpp
					mwait <= mwait + 2'd1;
					if (mwait == 2'd2) begin
						offset <= offset + mul_p[31:0];
						bstate <= B_NEXT;
					end
				end
				else if (ty == 9'd0)
					bstate <= B_NEXT;             // the same source row again
				else begin
					// the row just done: offset + 8 + (width - pre - post) x bpp
					t_w    <= w_left;
					ty     <= ty - 9'd1;
					bstate <= B_ADV3;
				end
			end

			B_ADV3: begin
				t_tb   <= (t_w > 0) ? times_bpp(t_w[10:0], bpp) : 14'd0;
				bstate <= B_ADV4;
			end

			B_ADV4: begin
				o2      <= offset + 32'd8 + {18'd0, t_tb};
				rd_bits <= 4'd8;
				bstate  <= B_YSKIP;
			end

			B_YSKIP: begin
				// skipped compressed rows (Y scaled down): each has its own
				// skip byte, used here as whole pixels (MAME leaves out the
				// << 8 in this loop)
				if (ty == 9'd0) begin
					offset <= o2;
					bstate <= B_NEXT;
				end
				else if (o != o2)
					o <= o2;                      // point the window at the next skip byte
				else if (have) begin
					skb    <= rd_byte;
					bstate <= B_YSK2;
				end
			end

			B_YSK2: begin
				t_w    <= w_skip;
				bstate <= B_YSK3;
			end

			B_YSK3: begin
				t_tb   <= (t_w > 0) ? times_bpp(t_w[10:0], bpp) : 14'd0;
				bstate <= B_YSK4;
			end

			B_YSK4: begin
				o2     <= o2 + 32'd8 + {18'd0, t_tb};
				ty     <= ty - 9'd1;
				bstate <= B_YSKIP;
			end

			B_NEXT: begin
				// a fill bank whose generation wrapped to 0 is cleared first,
				// once: the clear sets it to 1
				clr_a  <= 9'd0;
				bstate <= (gen[fill_bank] == 8'd0) ? B_CLR : B_ROW;
			end

			B_CLR: begin
				rb_we    <= 1'b1;
				rb_waddr <= {fill_bank, clr_a[7:0]};
				rb_wdata <= 80'd0;
				clr_a    <= clr_a + 9'd1;
				if (clr_a[7:0] == 8'hFF) begin
					gen[fill_bank] <= 8'd1;   // cleared entries (generation 0) stay invalid
					bstate <= B_ROW;
				end
			end

			B_DRAIN: if (!flush_busy && !fetching)
				bstate <= B_WAIT;

			B_WAIT: begin
				if (start_pending)
					bstate <= B_IDLE;            // restarted: the old completion is cancelled
				else if ((timer == 40'd0 || timer == 40'd1) && !start_wr) begin
					r[R_COMMAND][15] <= 1'b0;
					irq              <= 1'b1;
					bstate           <= B_IDLE;
				end
			end

			default: bstate <= B_IDLE;
		endcase

		// ---- CPU register writes (last, so they win over the completion) ----
		if (reg_wr && !reg_wr_wait) begin
			r[wr_reg] <= reg_wdata;
			if (wr_reg == 5'd1) begin
				irq <= 1'b0;                     // any command write drops INT1
				if (reg_wdata[15]) start_pending <= 1'b1;
			end
		end
	end
end

endmodule

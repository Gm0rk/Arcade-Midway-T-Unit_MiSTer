//============================================================================
//  T-Unit video RAM controller (DDR3)
//
//  The T-Unit frame store is MAME's m_local_videoram: 1 MB of 16-bit entries
//  (low byte: the pixel the blitter or CPU wrote, high byte: the palette page
//  it carried). The display and the blitter use the first 512 x 512 entries;
//  the CPU (bit addresses 0x00000000-0x003FFFFF) and the shift-register
//  transfers reach all 512 K entries. It lives in DDR3 behind the MiSTer
//  DDRAM port: 64-bit Avalon, 4 entries per beat, one 512-entry row = 128
//  beats, beat address = entry / 4.
//
//  Clients, in priority order (a burst in progress is never interrupted):
//    1. display  - read one row into the scanline buffer at each line start
//    2. srt      - VRAM shift-register load/store for the CPU (two rows)
//    3. blitter  - write back one finished blitter row
//    4. cpu      - 32-bit read or byte-masked write (two entries)
//
//  A blitter row is a window of 256 beats (1024 entries) starting at its row,
//  because the blitter's X position has 10 bits: like MAME, pixels at X 512 to
//  1023 land in the following row. The window's beats lo..hi go out in at
//  most two bursts of up to 128 beats.
//
//  Write bursts take their data straight from the output register of the
//  source block RAM. Its address runs one beat ahead whenever the bridge
//  accepts a beat, so the next beat's data is on DDRAM_DIN the following cycle
//  and a burst streams at one beat per cycle.
//
//  Derived from the Y Unit core's yunit_vram (autoerase removed, 1 MB, the
//  blitter's 256-beat window).
//
//  Copyright (C) 2026 Gm0rk - GPL-3.0-or-later
//============================================================================

module tunit_vram
(
	input             clk,
	input             reset,

	// DDR3 (MiSTer DDRAM port)
	input             ddr_busy,
	output reg  [7:0] ddr_burstcnt,
	output reg [28:0] ddr_addr,
	input      [63:0] ddr_dout,
	input             ddr_dout_ready,
	output reg        ddr_rd,
	output     [63:0] ddr_din,
	output      [7:0] ddr_be,
	output reg        ddr_we,

	// display: fetch one row into the scanline buffer
	input             disp_req,      // toggle
	output reg        disp_ack,
	input       [8:0] disp_row,
	output reg        lb_we,
	output reg  [6:0] lb_addr,
	output reg [63:0] lb_data,

	// shift-register transfer (1024 entries starting at an entry index)
	input             srt_req,       // toggle
	output reg        srt_ack,
	input             srt_wr,        // 0: VRAM -> shift register, 1: shift register -> VRAM
	input      [18:0] srt_entry,
	output     [15:0] srt_first,     // shift register entry 0 (value a load returns)

	// blitter row write-back: beats lo..hi of a row's 256-beat window
	input             blt_req,       // toggle
	output reg        blt_ack,
	input       [8:0] blt_row,
	input       [7:0] blt_lo,
	input       [7:0] blt_hi,
	output      [7:0] blt_raddr,     // read address into the blitter's row buffer
	input      [63:0] blt_q,         // its data, one cycle later
	input       [7:0] blt_be,

	// CPU: one 32-bit half of a beat
	input             cpu_req,       // toggle
	output reg        cpu_ack,
	input             cpu_wr,
	input      [16:0] cpu_qaddr,     // beat (qword) address
	input             cpu_half,      // 0: entries 0-1, 1: entries 2-3
	input       [3:0] cpu_be,
	input      [31:0] cpu_wdata,
	output reg [31:0] cpu_rdata
);

// VRAM sits at 0x30000000 in the HPS address space (DDRAM_ADDR counts beats)
localparam [28:0] BASE = 29'h0600_0000;

//----------------------------------------------------------------------------
// Shift register (1024 entries = 256 beats)
//----------------------------------------------------------------------------

reg  [63:0] srt_buf [0:255];
reg   [7:0] sb_waddr;
reg  [63:0] sb_wdata;
reg         sb_we;
reg   [7:0] sb_raddr;
reg  [63:0] sb_q;
reg  [15:0] sr0;                 // copy of entry 0 for the CPU
always @(posedge clk) begin
	if (sb_we) srt_buf[sb_waddr] <= sb_wdata;
	sb_q <= srt_buf[sb_raddr];
end
assign srt_first = sr0;

//----------------------------------------------------------------------------
// Sequencer
//----------------------------------------------------------------------------

localparam V_IDLE   = 3'd0;
localparam V_RD     = 3'd1;      // read burst command
localparam V_RDDATA = 3'd2;      // receiving read beats
localparam V_WRPRE  = 3'd3;      // prime the source RAM for a write burst
localparam V_WR     = 3'd4;      // write beats
localparam V_DONE   = 3'd5;

localparam D_LINE = 2'd0;        // clients
localparam D_SRT  = 2'd1;
localparam D_BLT  = 2'd2;
localparam D_CPU  = 2'd3;

reg   [2:0] vstate;
reg   [1:0] op;                  // which client is being served
reg   [7:0] beats;               // beats in this burst
reg   [7:0] bi;                  // beat counter
reg   [7:0] src_idx;             // source RAM beat index for writes
reg         second;              // second burst of a two-burst operation
reg         more;                // a second burst follows this one
reg  [28:0] next_addr;
reg   [7:0] next_beats;
reg   [7:0] blt_base;            // first window beat of the current blitter burst

wire        wr_accept = ddr_we & ~ddr_busy;

// source RAM address runs one beat ahead when a beat is accepted
wire  [7:0] src_next = src_idx + (wr_accept ? 8'd1 : 8'd0);
always @(*) sb_raddr = src_next;
assign blt_raddr = blt_base + src_next;

reg  [63:0] cpu_din;
reg   [7:0] cpu_bemask;
assign ddr_din = (op == D_CPU) ? cpu_din    : (op == D_SRT) ? sb_q : blt_q;
assign ddr_be  = (op == D_CPU) ? cpu_bemask : (op == D_SRT) ? 8'hFF : blt_be;

// blitter burst split: up to 128 beats each
wire  [8:0] blt_span = {1'b0, blt_hi} - {1'b0, blt_lo} + 9'd1;     // 1..256
wire [16:0] blt_beat = {1'b0, blt_row, 7'd0} + {9'd0, blt_lo};    // window start (row x 128) + lo

always @(posedge clk) begin
	lb_we <= 1'b0;
	sb_we <= 1'b0;

	if (reset) begin
		vstate    <= V_IDLE;
		ddr_rd    <= 1'b0;
		ddr_we    <= 1'b0;
		disp_ack  <= disp_req;
		srt_ack   <= srt_req;
		blt_ack   <= blt_req;
		cpu_ack   <= cpu_req;
	end
	else begin
		case (vstate)
			V_IDLE: begin
				second  <= 1'b0;
				more    <= 1'b0;
				src_idx <= 8'd0;
				bi      <= 8'd0;
				if (disp_req != disp_ack) begin
					op           <= D_LINE;
					ddr_addr     <= BASE | {13'd0, disp_row, 7'd0};   // row x 128 beats
					ddr_burstcnt <= 8'd128;
					beats        <= 8'd128;
					vstate       <= V_RD;
				end
				else if (srt_req != srt_ack) begin
					op           <= D_SRT;
					ddr_addr     <= BASE | {12'd0, srt_entry[18:2]};
					next_addr    <= BASE | {12'd0, srt_entry[18:2] + 17'd128};
					ddr_burstcnt <= 8'd128;
					beats        <= 8'd128;
					more         <= 1'b1;
					vstate       <= srt_wr ? V_WRPRE : V_RD;
				end
				else if (blt_req != blt_ack) begin
					op           <= D_BLT;
					blt_base     <= blt_lo;
					// the row's window starts at beat row x 128
					ddr_addr     <= BASE | {12'd0, blt_beat};
					if (blt_span > 9'd128) begin
						ddr_burstcnt <= 8'd128;
						beats        <= 8'd128;
						more         <= 1'b1;
						next_addr    <= BASE | {12'd0, blt_beat + 17'd128};
						next_beats   <= 8'(blt_span - 9'd128);
					end
					else begin
						ddr_burstcnt <= blt_span[7:0];
						beats        <= blt_span[7:0];
					end
					vstate       <= V_WRPRE;
				end
				else if (cpu_req != cpu_ack) begin
					op           <= D_CPU;
					ddr_addr     <= BASE | {12'd0, cpu_qaddr};
					ddr_burstcnt <= 8'd1;
					beats        <= 8'd1;
					if (cpu_wr) begin
						ddr_we     <= 1'b1;
						cpu_din    <= {cpu_wdata, cpu_wdata};
						cpu_bemask <= cpu_half ? {cpu_be, 4'b0000} : {4'b0000, cpu_be};
						vstate     <= V_WR;
					end
					else
						vstate <= V_RD;
				end
			end

			V_RD: begin
				ddr_rd <= 1'b1;
				if (ddr_rd & ~ddr_busy) begin
					ddr_rd <= 1'b0;
					vstate <= V_RDDATA;
				end
			end

			V_RDDATA: if (ddr_dout_ready) begin
				case (op)
					D_LINE: begin
						lb_we   <= 1'b1;
						lb_addr <= bi[6:0];
						lb_data <= ddr_dout;
					end
					D_SRT: begin
						sb_we    <= 1'b1;
						sb_waddr <= {second, bi[6:0]};
						sb_wdata <= ddr_dout;
						if (!second && bi == 8'd0) sr0 <= ddr_dout[15:0];
					end
					default: cpu_rdata <= cpu_half ? ddr_dout[63:32] : ddr_dout[31:0];
				endcase
				bi <= bi + 8'd1;
				if (bi + 8'd1 == beats) begin
					bi <= 8'd0;
					if (more) begin
						more     <= 1'b0;
						second   <= 1'b1;
						ddr_addr <= next_addr;
						vstate   <= V_RD;
					end
					else
						vstate <= V_DONE;
				end
			end

			V_WRPRE: begin
				// the source RAM sees src_idx this cycle; its data is on DIN next cycle
				ddr_we <= 1'b1;
				vstate <= V_WR;
			end

			V_WR: begin
				if (wr_accept) begin
					if (bi + 8'd1 == beats) begin
						ddr_we <= 1'b0;
						bi     <= 8'd0;
						if (more) begin
							// second burst: the source continues where the first ended
							more     <= 1'b0;
							second   <= 1'b1;
							ddr_addr <= next_addr;
							src_idx  <= 8'd128;
							if (op == D_BLT) begin
								ddr_burstcnt <= next_beats;
								beats        <= next_beats;
							end
							vstate   <= V_WRPRE;
						end
						else
							vstate <= V_DONE;
					end
					else begin
						bi      <= bi + 8'd1;
						src_idx <= src_idx + 8'd1;
					end
				end
			end

			V_DONE: begin
				case (op)
					D_LINE:  disp_ack <= disp_req;
					D_SRT:   srt_ack  <= srt_req;
					D_BLT:   blt_ack  <= blt_req;
					default: cpu_ack  <= cpu_req;
				endcase
				vstate <= V_IDLE;
			end

			default: vstate <= V_IDLE;
		endcase
	end
end

endmodule

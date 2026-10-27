//============================================================================
//  tunit_idle - the core's own frames while a ROM set loads
//
//  The board holds the 34010 in reset while a ROM set loads, and the 34010's
//  raster counters stop with it: the board sends no frames at all, and the
//  scaler goes on showing the last frame it had (the MiSTer menu's coloured
//  or patterned background behind the "Sending ROM" box). So while a ROM set
//  loads the top level sends these frames instead (the picture is black):
//  the timing the 34010 starts from, 253 VCLKs of 2 dots x 289 lines, the
//  same blanking and sync, 15.81 kHz and 54.7 Hz.
//
//  With the 57 Hz Video Timing (vt57) the frame is the one the board makes
//  then: the 34010 drops 12 blank lines after VSBLNK (tms34010.sv, "Shorter
//  frames"), so the line after VSBLNK (274) is 287 and the frame is 277
//  lines, 57.1 Hz. The picture lines (20-273), VSync (0-2) and VSBLNK are
//  the same; only the blank time at the end of the frame is shorter. The
//  loading screen then runs at the refresh rate the game will run at, and
//  the output stays locked when the game starts.
//
//  Copyright (C) 2026 Gm0rk - GPL-3.0-or-later
//============================================================================

module tunit_idle
(
	input  clk,
	input  ce_pix,       // one dot (the board's ce_pix)
	input  vt57,         // Video Timing 57Hz: the 277-line frame

	output hs,           // sync and blanking of the frame, active high
	output vs,
	output hb,
	output vb
);

reg [8:0] x = 9'd0;      // dot in the line, 0-505
reg [8:0] y = 9'd0;      // line in the frame, 0-288 (274 is followed by 287 when vt57)

always @(posedge clk) if (ce_pix) begin
	if (x == 9'd505) begin
		x <= 9'd0;
		y <= (vt57  && y == 9'd274) ? 9'd287 :
		     (y == 9'd288)          ? 9'd0   : y + 9'd1;
	end
	else
		x <= x + 9'd1;
end

assign hs = (x < 9'd36);                          // HESYNC 18 VCLKs
assign hb = (x < 9'd90) | (x >= 9'd500);          // HEBLNK 45, HSBLNK 250
assign vs = (y < 9'd3);                           // VESYNC 3
assign vb = (y < 9'd20) | (y >= 9'd274);          // VEBLNK 20, VSBLNK 274

endmodule

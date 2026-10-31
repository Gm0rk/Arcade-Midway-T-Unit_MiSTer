//============================================================================
//  Arcade-Midway-T-Unit - OSD cheats
//
//  Copyright (C) 2026 Gm0rk - GPL-3.0-or-later
//
//  This program is free software; you can redistribute it and/or modify it
//  under the terms of the GNU General Public License as published by the Free
//  Software Foundation; either version 3 of the License, or (at your option)
//  any later version.
//============================================================================
//
// The MRA's <cheats size="8" max="8"> block gives the OSD a Cheats menu
// (CONF_STR "C,Cheats;"). Main_MiSTer sends the switched-on cheats, units
// back to back, as one download with index 255 each time one is toggled: a
// lone 2-byte word when none is on. This module takes up to 8 units of 8
// bytes (four 16-bit words, little-endian) and presents them as read patches
// of the board (rtl/midway_tunit.sv, the same compare as the OSD secrets').
//
//   word 0   word address bits 15-0 (bit address >> 4)
//   word 1   word address bits 27-16
//   word 2   the value the CPU reads
//   word 3   bit 0: a program ROM word (patched for instruction fetches
//            only); 0: a main RAM variable
//            bit 1: the CPU's writes to the word store the value too (a
//            main RAM variable only: Infinite Health, so the game's own copy
//            stays full and switching the cheat off leaves the bar full)
//
// The entries are cleared when a download of cheats begins (so each toggle
// sends the whole list again) and when a ROM set loads (Main forgets which
// cheats were on). tools/tunit_cheats.py makes the units.
//
// ck_en[n] is set once all four words of unit n have arrived, so a download
// cut short never leaves half an entry in use.

module tunit_cheats
(
	input             clk,
	input             clear,         // a ROM set is loading: all cheats off
	input             dl_start,      // pulse: a cheat download begins
	input             dl_wr,
	input       [4:0] dl_addr,       // word index: unit [4:2], word in unit [1:0]
	input      [15:0] dl_data,

	output    [223:0] ck_addr,       // 8 x 28-bit word addresses
	output    [127:0] ck_data,       // 8 x 16-bit values
	output reg  [7:0] ck_en = 8'd0,  // entry valid
	output reg  [7:0] ck_fetch = 8'd0, // entry is program code: instruction fetches only
	output reg  [7:0] ck_store = 8'd0  // entry also replaces the value the CPU writes
);

reg  [27:0] c_addr [0:7];
reg  [15:0] c_val  [0:7];
reg  [15:0] s_lo, s_hi, s_val;       // the unit being received

genvar g;
generate
	for (g = 0; g < 8; g = g + 1) begin : e
		assign ck_addr[28 * g +: 28] = c_addr[g];
		assign ck_data[16 * g +: 16] = c_val[g];
	end
endgenerate

always @(posedge clk) begin
	if (clear | dl_start) begin
		ck_en    <= 8'd0;
		ck_fetch <= 8'd0;
		ck_store <= 8'd0;
	end
	else if (dl_wr) begin
		case (dl_addr[1:0])
			2'd0: s_lo  <= dl_data;
			2'd1: s_hi  <= dl_data;
			2'd2: s_val <= dl_data;
			2'd3: begin
				c_addr[dl_addr[4:2]]  <= {s_hi[11:0], s_lo};
				c_val[dl_addr[4:2]]   <= s_val;
				ck_fetch[dl_addr[4:2]] <= dl_data[0];
				ck_store[dl_addr[4:2]] <= dl_data[1];
				ck_en[dl_addr[4:2]]   <= 1'b1;
			end
		endcase
	end
end

endmodule

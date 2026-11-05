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
//   word 1   bits 11-0: word address bits 27-16
//            bit 12: a program ROM word (patched for instruction fetches
//                    only); 0: a main RAM variable, or a program ROM word
//                    the game reads as data (Mortal Kombat II's Infinite
//                    Health: a table word of the damage routine), which is
//                    patched for every read of it
//            bit 13: the CPU's writes to the word store the value too, and
//                    the board writes the value to the word once when the
//                    entry goes on (a main RAM variable only: Mortal
//                    Kombat's Infinite Energy, so the game's own copy stays
//                    full and switching the cheat off leaves the bar full)
//            bit 14: a one-shot write: no read patch; the board writes the
//                    value to the word (a whole 16-bit word of main RAM)
//                    once, when the entry first appears in the list, not
//                    again when another cheat is toggled and the list is
//                    sent again (the list is compared with the previous one)
//   word 2   the value the CPU reads (or writes, for a one-shot)
//   word 3   the bits of the word the value covers: the CPU reads the game's
//            own value in the bits that are 0 (FFFF: the whole word; a byte
//            of a RAM word; one bit of the flag word of a player). Entries
//            on the same word combine: their covered bits are ORed. Not
//            used by a one-shot or by an entry with the store flag, which
//            take the whole word.
//
// The entries are cleared when a download of cheats begins (so each toggle
// sends the whole list again) and when a ROM set loads (Main forgets which
// cheats were on). tools/tunit_cheats.py makes the units.
//
// ck_en[n] is set once all four words of unit n have arrived, so a download
// cut short never leaves half an entry in use. ck_pk[n] says the same for a
// one-shot (which has no read patch, so no ck_en), and ck_fire[n] is one
// clock when that one-shot is new.
//
// The previous list: at the start of a download the addresses and values of
// the one-shots in the list that is about to be replaced are kept (o_*), and
// a one-shot that arrives with the same address and value as one of them is
// the same cheat sent again, wherever it sits in the list now. When no
// one-shot is in the list (the cheat was switched off, or all cheats were) the
// copy is empty, so switching it on again fires it again.

module tunit_cheats
(
	input             clk,
	input             clear,         // a ROM set is loading: all cheats off
	input             dl_start,      // pulse: a cheat download begins
	input             dl_wr,
	input       [4:0] dl_addr,       // word index: unit [4:2], word in unit [1:0]
	input      [15:0] dl_data,

	output    [223:0] ck_addr,       // 8 x 28-bit word addresses
	output    [127:0] ck_data,       // 8 x 16-bit values (zero outside the mask)
	output    [127:0] ck_mask,       // 8 x 16-bit masks
	output reg  [7:0] ck_en = 8'd0,  // read patch valid
	output reg  [7:0] ck_fetch = 8'd0, // entry is program code: instruction fetches only
	output reg  [7:0] ck_store = 8'd0, // entry also replaces the value the CPU writes
	output reg  [7:0] ck_pk = 8'd0,  // a one-shot write is in the entry
	output reg  [7:0] ck_fire = 8'd0 // one clock: a one-shot that was not in the previous list
);

reg  [27:0] c_addr [0:7];
reg  [15:0] c_val  [0:7];
reg  [15:0] c_mask [0:7];
reg  [27:0] o_addr [0:7];            // the previous list's one-shots
reg  [15:0] o_val  [0:7];
reg   [7:0] o_pk = 8'd0;
reg  [15:0] s_lo, s_hi, s_val;       // the unit being received

genvar g;
generate
	for (g = 0; g < 8; g = g + 1) begin : e
		assign ck_addr[28 * g +: 28] = c_addr[g];
		assign ck_data[16 * g +: 16] = c_val[g];
		assign ck_mask[16 * g +: 16] = c_mask[g];
	end
endgenerate

wire [27:0] n_addr = {s_hi[11:0], s_lo};
wire        n_pk   = s_hi[14];

// the new unit's address and value against the previous list's one-shots
reg   [7:0] dup;
integer     k;
always @(*) begin
	for (k = 0; k < 8; k = k + 1)
		dup[k] = o_pk[k] && (o_addr[k] == n_addr) && (o_val[k] == s_val);
end

integer m;
always @(posedge clk) begin
	ck_fire <= 8'd0;
	if (clear | dl_start) begin
		ck_en    <= 8'd0;
		ck_fetch <= 8'd0;
		ck_store <= 8'd0;
		ck_pk    <= 8'd0;
		o_pk     <= clear ? 8'd0 : ck_pk;
		for (m = 0; m < 8; m = m + 1) begin
			o_addr[m] <= c_addr[m];
			o_val[m]  <= c_val[m];
		end
	end
	else if (dl_wr) begin
		case (dl_addr[1:0])
			2'd0: s_lo  <= dl_data;
			2'd1: s_hi  <= dl_data;
			2'd2: s_val <= dl_data;
			2'd3: begin
				c_addr[dl_addr[4:2]]   <= n_addr;
				c_val[dl_addr[4:2]]    <= n_pk ? s_val : (s_val & dl_data);
				c_mask[dl_addr[4:2]]   <= n_pk ? 16'hFFFF : dl_data;
				ck_fetch[dl_addr[4:2]] <= s_hi[12] & ~n_pk;
				ck_store[dl_addr[4:2]] <= s_hi[13] & ~n_pk;
				ck_en[dl_addr[4:2]]    <= ~n_pk;
				ck_pk[dl_addr[4:2]]    <= n_pk;
				ck_fire[dl_addr[4:2]]  <= n_pk & ~|dup;
			end
		endcase
	end
end

endmodule

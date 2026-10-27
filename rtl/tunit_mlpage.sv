//============================================================================
//  tunit_mlpage - the page of the information window
//
//  The OSD's Move List (Mortal Kombat games), View Secret Players (NBA Jam
//  games) and View Secrets (Mortal Kombat II Plus) options are Off or On. While
//  one is On the window shows one page (the first when it was switched on)
//  and, with the OSD closed, Right turns to the next page and Left to the
//  previous one, from the last page round to the first and back. One press
//  turns one page; a button held down does not repeat. Both pressed together
//  turn nothing. While the OSD is open the controls are the menu's: nothing
//  turns, and the page is kept. A page past the list (a game loaded with
//  another list while the option stayed On) goes back to the first.
//
//  A game has one or two lists: list A (the Move List, or the Secret Player
//  List) and list B (Mortal Kombat II Plus's View Secrets). With both On the
//  one switched On last is shown (show_b says which; both switched On in the
//  same clock: list B); switching from one to the other starts at the first
//  page. With only one On, that one is shown.
//
//  Copyright (C) 2026 Gm0rk - GPL-3.0-or-later
//============================================================================

module tunit_mlpage
(
	input            clk,
	input            on_a,      // list A's option is On (and the game has it)
	input            on_b,      // list B's option is On (and the game has it)
	input      [4:0] pages_a,   // pages in list A, 1 to 31
	input      [4:0] pages_b,   // pages in list B, 1 to 31
	input            osd_open,  // the OSD is open
	input            left,      // the controller's Left (any player)
	input            right,     // the controller's Right (any player)

	output           show_b,    // the page is list B's (else list A's)
	output reg [4:0] page = 5'd0   // the page to show, from 0
);

reg  on_a_d  = 1'b0;
reg  on_b_d  = 1'b0;
reg  last_b  = 1'b0;               // list B was switched on after list A
reg  show_b_d = 1'b0;
reg  left_d  = 1'b0;
reg  right_d = 1'b0;
wire go_l    = left  & ~left_d;
wire go_r    = right & ~right_d;

assign show_b = on_b & (~on_a | last_b);

wire       any   = on_a | on_b;
wire [4:0] last  = (show_b ? pages_b : pages_a) - 5'd1;

always @(posedge clk) begin
	left_d   <= left;
	right_d  <= right;
	on_a_d   <= on_a;
	on_b_d   <= on_b;
	show_b_d <= show_b;

	if (on_b & ~on_b_d)
		last_b <= 1'b1;
	else if (on_a & ~on_a_d)
		last_b <= 1'b0;

	if (!any || page > last || show_b != show_b_d)
		page <= 5'd0;
	else if (!osd_open) begin
		if (go_r && !go_l)
			page <= (page == last) ? 5'd0 : page + 5'd1;
		else if (go_l && !go_r)
			page <= (page == 5'd0) ? last : page - 5'd1;
	end
end

endmodule

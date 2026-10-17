//============================================================================
//  Finishing moves (Mortal Kombat, Mortal Kombat II), from the OSD
//
//  The OSD's "Finishing Moves" page lists each fighter's fatalities,
//  friendships, babalities and stage moves. A pick sets the move; this
//  module plays it on the winner's controls at the next FINISH HIM where
//  the winner is that fighter, and says in an OSD message when it cannot
//  (another stage, too far or too close, FINISH HIM over, not taken).
//
//  Following the fight. The module keeps copies of the game's fight
//  variables by watching the CPU's writes (the board's dbg_wr): the round
//  state (3 = FINISH HIM), both fighters' character, energy, object and
//  process pointers, the stage and the finish flag the game sets when a
//  finishing move starts. Their addresses differ between revisions; the MRA
//  sends them (ROM index 1, words 0x200-0x227, tools/tunit_fmoves.py finds
//  them in each set's program ROM). Through the pointers it follows each
//  fighter's x (object word 9) and where its process resumes (process words
//  14-15): the finisher's stance loop and the loser's dizzy loop tell when a
//  move can start; until then the games drop it.
//
//  The winner is the fighter whose energy is not 0 at FINISH HIM. A move
//  starts when its fighter is the winner, the stage fits (stage moves), the
//  distance between the two fighters' x is in the move's window and both
//  are ready; the module then takes that player's controls (the player's
//  own are ignored) for a few frames so the finisher comes to rest, and
//  plays the move's program. Out of the window it says so once and waits,
//  leaving the controls to the player, who can step in or out: the move
//  starts when the distance fits. A move that holds a button first (charge
//  moves) starts holding it at once when the distance fits, and lets go of
//  the controls again if the player has to move.
//
//  Programs (rtl/tunit_fmoves_tab.svh, from tools/tunit_fmoves.py): steps
//  {op[2:0], arg[12:0]}, one starting per frame at most:
//    0 END
//    1 TAP      keys arg[8:0] for arg[12:9] + 1 frames, then 3 frames up
//    2 PRESS    hold keys arg[8:0] (next step on the next frame)
//    3 RELEASE  let go of keys arg[8:0], then 3 frames
//    4 WAIT     arg frames
//    5 READY    wait for the loser dizzy, the finisher in its stance (unless
//               a button is held) and the distance in the window
//    6 WALK     walk forward until the distance is arg or less
//  Keys {BL, LK, HK, LP, HP, B, F, D, U}; F and B are toward and away from
//  the loser, turned into Right / Left each frame from the two x.
//
//  After the program the finish flag says whether the game took the move
//  (MK's The Pit: the round state leaving FINISH HIM). Taken, the move is
//  done; not taken in 192 frames, a message says so. Either way the set
//  move is cleared. A move set outside FINISH HIM (or for another fighter)
//  waits for the right one; a FINISH HIM that ends first leaves it set. A
//  move the loaded revision does not have (a list in the same MRA words) is
//  refused with a message.
//
//  Frames are running frames (the top level's osd_frame), so with "Pause
//  when OSD is open" a pick made at FINISH HIM starts when the OSD closes.
//
//  Copyright (C) 2026 Gm0rk - GPL-3.0-or-later
//============================================================================

module tunit_fmoves
(
	input             clk,
	input             reset,
	input             game_mk,       // MK or MK Turbo is loaded
	input             game_mk2,      // MK2 is loaded

	// ROM index 1 words 0x200-0x227: the set's fight variables
	input             dl_start,      // pulse: ROM index 1 is about to arrive
	input             dl_wr,
	input       [5:0] dl_addr,
	input      [15:0] dl_data,

	// OSD
	input             sel,           // one clock: a pick
	input       [3:0] sel_line,      // the page's fighter (its line in the Fighter list)
	input       [3:0] sel_slot,      // the move's line, 15 = clear the set move
	input             frame,         // one clock at the start of each running frame

	// CPU writes (the board's dbg_wr, dbg_wa, dbg_wdata)
	input             cpu_wr,
	input      [27:0] cpu_wa,
	input      [15:0] cpu_wd,

	// controls: while drive[n], player n+1's controls are keys (active high)
	output      [1:0] drive,
	output reg  [8:0] keys,          // {BL, LK, HK, LP, HP, Right, Left, Down, Up}
	output reg        msg_req,       // one clock: show OSD message msg
	output reg  [4:0] msg
);

`include "tunit_fmoves_tab.svh"

localparam K_FATAL = 3'd0, K_FRIEND = 3'd1, K_BABY = 3'd2, K_STAGE = 3'd3, K_PIT2 = 3'd4,
           K_DEAD = 3'd5, K_MKPIT = 3'd6;
localparam OP_END = 3'd0, OP_TAP = 3'd1, OP_PRESS = 3'd2, OP_RELEASE = 3'd3, OP_WAIT = 3'd4,
           OP_READY = 3'd5, OP_WALK = 3'd6;
localparam [12:0] GAP = 13'd3;            // frames up after a tap or a release
localparam [7:0] CHECK_FRAMES = 8'd192;
// MK's Pit sets no flag; it ends FINISH HIM at once (round state leaves 3
// within 2 frames of the uppercut, MAME). The state also leaves 3 when
// FINISH HIM runs out, so the Pit counts as taken only that soon.
localparam [7:0] PIT_FRAMES = 8'd12;
localparam [2:0] SETTLE = 3'd4;

//----------------------------------------------------------------------------
// The set's addresses
//----------------------------------------------------------------------------

// word addresses: 0 round state, 1-2 P1 / P2 character, 3-4 energy,
// 5-6 object pointer, 7-8 process pointer, 9 stage, 10 finish flag
reg  [27:0] c_a  [0:10];
reg  [27:0] c_a1 [0:10];         // each + 1 (high word of a pointer)
reg  [31:0] c_diz1, c_diz2, c_stance;
reg   [7:0] c_xoff, c_soff;
reg [127:0] c_gone;              // the OSD's moves this revision lacks (bit line * 8 + slot)
reg         c_ok;

integer i;
always @(posedge clk) begin
	for (i = 0; i < 11; i = i + 1) c_a1[i] <= c_a[i] + 28'd1;

	if (dl_start) begin
		c_ok   <= 1'b0;
		c_gone <= 128'd0;
	end
	else if (dl_wr) begin
		if (dl_addr == 6'd0) c_ok <= (dl_data == 16'd1);
		for (i = 0; i < 11; i = i + 1) begin
			if ({26'd0, dl_addr} == 2 + 2 * i) c_a[i][15:0]  <= dl_data;
			if ({26'd0, dl_addr} == 3 + 2 * i) c_a[i][27:16] <= dl_data[11:0];
		end
		if (dl_addr == 6'd24) c_diz1[15:0]    <= dl_data;
		if (dl_addr == 6'd25) c_diz1[31:16]   <= dl_data;
		if (dl_addr == 6'd26) c_diz2[15:0]    <= dl_data;
		if (dl_addr == 6'd27) c_diz2[31:16]   <= dl_data;
		if (dl_addr == 6'd28) c_stance[15:0]  <= dl_data;
		if (dl_addr == 6'd29) c_stance[31:16] <= dl_data;
		if (dl_addr == 6'd30) {c_soff, c_xoff} <= dl_data;
		for (i = 0; i < 8; i = i + 1)
			if ({26'd0, dl_addr} == 32 + i) c_gone[16 * i +: 16] <= dl_data;
	end
end

//----------------------------------------------------------------------------
// The fight, from the CPU's writes
//----------------------------------------------------------------------------

reg         w_v;
reg  [27:0] w_a;
reg  [15:0] w_d;
always @(posedge clk) begin
	w_v <= cpu_wr & c_ok;
	w_a <= cpu_wa;
	w_d <= cpu_wd;
end

reg  [15:0] v_state, v_c1, v_c2, v_e1, v_e2, v_stage, v_flag;
reg  [31:0] v_o1, v_o2, v_p1, v_p2;          // object, process pointers (bit addresses)
reg  [15:0] v_x1, v_x2;                      // x
reg  [31:0] v_r1, v_r2;                      // where the processes resume
reg         v_xv1, v_xv2, v_rv1, v_rv2;      // written since the pointer last changed
reg  [27:0] a_x1, a_x2, a_r1, a_r2, a_r1h, a_r2h;

always @(posedge clk) begin
	a_x1  <= v_o1[31:4] + {20'd0, c_xoff};
	a_x2  <= v_o2[31:4] + {20'd0, c_xoff};
	a_r1  <= v_p1[31:4] + {20'd0, c_soff};
	a_r2  <= v_p2[31:4] + {20'd0, c_soff};
	a_r1h <= v_p1[31:4] + {20'd0, c_soff} + 28'd1;
	a_r2h <= v_p2[31:4] + {20'd0, c_soff} + 28'd1;

	if (reset || !c_ok) begin
		v_state <= 16'd0;
		v_flag  <= 16'd0;
		{v_xv1, v_xv2, v_rv1, v_rv2} <= 4'd0;
	end
	else if (w_v) begin
		if (w_a == c_a[0])  v_state <= w_d;
		if (w_a == c_a[1])  v_c1    <= w_d;
		if (w_a == c_a[2])  v_c2    <= w_d;
		if (w_a == c_a[3])  v_e1    <= w_d;
		if (w_a == c_a[4])  v_e2    <= w_d;
		if (w_a == c_a[9])  v_stage <= w_d;
		if (w_a == c_a[10]) v_flag  <= w_d;
		if (w_a == c_a[5])  begin v_o1[15:0]  <= w_d; v_xv1 <= 1'b0; end
		if (w_a == c_a1[5]) begin v_o1[31:16] <= w_d; v_xv1 <= 1'b0; end
		if (w_a == c_a[6])  begin v_o2[15:0]  <= w_d; v_xv2 <= 1'b0; end
		if (w_a == c_a1[6]) begin v_o2[31:16] <= w_d; v_xv2 <= 1'b0; end
		if (w_a == c_a[7])  begin v_p1[15:0]  <= w_d; v_rv1 <= 1'b0; end
		if (w_a == c_a1[7]) begin v_p1[31:16] <= w_d; v_rv1 <= 1'b0; end
		if (w_a == c_a[8])  begin v_p2[15:0]  <= w_d; v_rv2 <= 1'b0; end
		if (w_a == c_a1[8]) begin v_p2[31:16] <= w_d; v_rv2 <= 1'b0; end
		if (w_a == a_x1)  begin v_x1 <= w_d; v_xv1 <= 1'b1; end
		if (w_a == a_x2)  begin v_x2 <= w_d; v_xv2 <= 1'b1; end
		if (w_a == a_r1)  begin v_r1[15:0]  <= w_d; v_rv1 <= 1'b1; end
		if (w_a == a_r1h) begin v_r1[31:16] <= w_d; v_rv1 <= 1'b1; end
		if (w_a == a_r2)  begin v_r2[15:0]  <= w_d; v_rv2 <= 1'b1; end
		if (w_a == a_r2h) begin v_r2[31:16] <= w_d; v_rv2 <= 1'b1; end
	end
end

//----------------------------------------------------------------------------
// The finisher and the loser (registered each clock)
//----------------------------------------------------------------------------

reg         fin;                 // FINISH HIM with a known winner
reg         who;                 // the winner: 0 P1, 1 P2
reg  [15:0] fin_char;
reg  [15:0] sep;
reg         sep_ok;             // both x known
reg         fwd_right;           // the loser is to the winner's right
reg         opp_dizzy, fin_stance;

always @(posedge clk) begin
	fin        <= (v_state == 16'd3) && ((v_e1 == 16'd0) != (v_e2 == 16'd0));
	who        <= (v_e1 == 16'd0);
	fin_char   <= (v_e1 == 16'd0) ? v_c2 : v_c1;
	sep       <= (v_x1 > v_x2) ? v_x1 - v_x2 : v_x2 - v_x1;
	sep_ok    <= v_xv1 & v_xv2;
	fwd_right  <= (v_e1 == 16'd0) ? (v_x2 < v_x1) : (v_x1 < v_x2);
	opp_dizzy  <= (v_e1 == 16'd0) ? v_rv1 && (v_r1 == c_diz1 || v_r1 == c_diz2)
	                              : v_rv2 && (v_r2 == c_diz1 || v_r2 == c_diz2);
	fin_stance <= (v_e1 == 16'd0) ? v_rv2 && v_r2 == c_stance
	                              : v_rv1 && v_r1 == c_stance;
end

//----------------------------------------------------------------------------
// The set move
//----------------------------------------------------------------------------

reg         sel_d;
reg   [7:0] sel_id;
reg         sel_clr;
wire [36:0] rec = fm_rec(sel_id);

reg         m_pre;
reg   [2:0] m_kind;
reg   [3:0] m_char;
reg   [8:0] m_dmin, m_dmax;
reg   [9:0] m_start;

wire        stage_ok = (m_kind == K_STAGE) ? (v_stage == 16'd6 || v_stage == 16'd1) :
                       (m_kind == K_PIT2)  ? (v_stage == 16'd6) :
                       (m_kind == K_DEAD)  ? (v_stage == 16'd0) :
                       (m_kind == K_MKPIT) ? (v_stage == 16'd3) : 1'b1;
wire  [4:0] stage_msg = (m_kind == K_STAGE) ? MSG_STAGE :
                        (m_kind == K_PIT2)  ? MSG_PIT2 :
                        (m_kind == K_DEAD)  ? MSG_DEAD : MSG_MKPIT;
wire        too_close = sep < {7'd0, m_dmin};
wire        too_far   = sep > {7'd0, m_dmax};
wire        in_window = sep_ok & ~too_close & ~too_far;
wire        mine      = fin && fin_char == {12'd0, m_char};
wire        taken     = (v_flag != 16'd0) || (m_kind == K_MKPIT && v_state != 16'd3);

//----------------------------------------------------------------------------
// Player
//----------------------------------------------------------------------------

localparam S_IDLE = 3'd0, S_ARMED = 3'd1, S_RUN = 3'd2, S_CHECK = 3'd3;

reg   [2:0] st;
reg         skip;                // this FINISH HIM does not fit the move
reg   [1:0] warned;              // distance messages given this FINISH HIM: [0] too far, [1] too close
reg         own;                 // the controls are the player's
reg   [2:0] settle;
reg   [9:0] ptr;
reg  [15:0] stp;
reg  [12:0] wait_n;
reg   [3:0] tap_n;
reg   [7:0] walk_n = 8'd0;
reg   [7:0] chk_n;
reg   [8:0] held, tap;           // relative keys {BL, LK, HK, LP, HP, B, F, D, U}
reg         pwho;                // whose controls
reg         begun;               // past the ready point: the move is being entered

assign drive = own ? (pwho ? 2'b10 : 2'b01) : 2'b00;

always @(posedge clk) stp <= fm_step(ptr);

wire  [2:0] op  = stp[15:13];
wire  [8:0] arg_keys = stp[8:0];

// relative keys to the port's
wire  [8:0] rk = held | tap;
always @(posedge clk)
	keys <= {rk[8:4],
	         fwd_right ? rk[2] : rk[3],        // Right
	         fwd_right ? rk[3] : rk[2],        // Left
	         rk[1], rk[0]};

// out of the window: a message once per change
wire        warn_far   = too_far   && !warned[0];
wire        warn_close = too_close && !warned[1];
wire        both_ready = opp_dizzy && (fin_stance || held != 9'd0);

always @(posedge clk) begin
	msg_req <= 1'b0;
	sel_d   <= sel;
	sel_id  <= {game_mk2, sel_line, sel_slot[2:0]};
	sel_clr <= (sel_slot == 4'd15);

	if (reset || !(game_mk || game_mk2)) begin
		st   <= S_IDLE;
		own  <= 1'b0;
		held <= 9'd0;
		tap  <= 9'd0;
	end
	else if (sel_d && c_ok) begin
		own  <= 1'b0;
		held <= 9'd0;
		tap  <= 9'd0;
		skip <= 1'b0;
		if (sel_clr) begin
			if (st != S_IDLE) begin msg_req <= 1'b1; msg <= MSG_CLEARED; end
			st <= S_IDLE;
		end
		else if (rec[36] && c_gone[sel_id[6:0]]) begin
			// a move this revision does not have
			msg_req <= 1'b1;
			msg     <= MSG_NOT_HERE;
		end
		else if (rec[36]) begin
			{m_pre, m_kind, m_char, m_dmin, m_dmax, m_start} <= rec[35:0];
			st <= S_ARMED;
			if (!fin) begin
				msg_req <= 1'b1;
				msg     <= MSG_SET;
			end
			else if (fin_char != {12'd0, rec[31:28]}) begin
				msg_req <= 1'b1;
				msg     <= MSG_NOT_THIS;
			end
		end
	end
	else if (frame) begin
		if (!fin) skip <= 1'b0;

		case (st)
			S_ARMED: begin
				// the move's fighter wins: go when the stage fits
				if (mine && !skip) begin
					if (!stage_ok) begin
						msg_req <= 1'b1;
						msg     <= stage_msg;
						skip    <= 1'b1;
					end
					else begin
						st     <= S_RUN;
						ptr    <= m_start;
						pwho   <= who;
						walk_n <= 8'd0;          // a walk cut short last time starts over
						wait_n <= 13'd0;
						tap_n  <= 4'd0;
						held   <= 9'd0;
						tap    <= 9'd0;
						settle <= 3'd0;
						warned <= 2'd0;
						begun  <= 1'b0;
					end
				end
			end

			S_RUN: begin
				if (!fin && !begun) begin
					// FINISH HIM over before the move started: it stays set
					msg_req <= 1'b1;
					msg     <= MSG_OVER;
					st      <= S_ARMED;
					own     <= 1'b0;
					held    <= 9'd0;
					tap     <= 9'd0;
				end
				else if (!fin) begin
					// over while it played (a stage move or a hit): see what came of it
					st    <= S_CHECK;
					chk_n <= CHECK_FRAMES;
					own   <= 1'b0;
					held  <= 9'd0;
					tap   <= 9'd0;
				end
				else begin
					// a tap's keys go up after its frames
					if (tap_n != 4'd0) tap_n <= tap_n - 4'd1;
					else if (op != OP_WALK) tap <= 9'd0;

					if (wait_n != 13'd0)
						wait_n <= wait_n - 13'd1;
					else case (op)
						OP_TAP: begin
							tap    <= arg_keys;
							tap_n  <= stp[12:9];
							wait_n <= {9'd0, stp[12:9]} + GAP;
							ptr    <= ptr + 10'd1;
						end
						OP_PRESS: begin
							// a move that holds a button first starts when the distance fits
							if (ptr == m_start && !in_window) begin
								// (said once the loser stands dizzy: the distance still
								// changes while it reels from the last hit)
								if (opp_dizzy && (warn_far | warn_close)) begin
									msg_req <= 1'b1;
									msg     <= warn_far ? MSG_FAR : MSG_CLOSE;
									warned  <= warned | {warn_close, warn_far};
								end
							end
							else begin
								own  <= 1'b1;
								held <= held | arg_keys;
								ptr  <= ptr + 10'd1;
							end
						end
						OP_RELEASE: begin
							held   <= held & ~arg_keys;
							wait_n <= GAP - 13'd1;
							ptr    <= ptr + 10'd1;
						end
						OP_WAIT: begin
							wait_n <= stp[12:0] - 13'd1;
							ptr    <= ptr + 10'd1;
						end
						OP_READY: begin
							if (!both_ready) begin
								// the loser still reels or gets up, the finisher recovers
							end
							else if (!in_window) begin
								// hand the controls back so the player can move, and
								// start again (a held button too) when it fits
								if (warn_far | warn_close) begin
									msg_req <= 1'b1;
									msg     <= warn_far ? MSG_FAR : MSG_CLOSE;
									warned  <= warned | {warn_close, warn_far};
								end
								own    <= 1'b0;
								held   <= 9'd0;
								settle <= 3'd0;
								ptr    <= m_start;
							end
							else begin
								if (!own) begin
									own    <= 1'b1;            // take over, let the finisher stand
									settle <= SETTLE;
								end
								else if (settle != 3'd0)
									settle <= settle - 3'd1;
								else begin
									wait_n <= 13'd1;
									ptr    <= ptr + 10'd1;
									begun  <= 1'b1;
								end
							end
						end
						OP_WALK: begin
							if (sep <= {3'd0, stp[12:0]} || walk_n == 8'd150) begin
								tap    <= 9'd0;
								walk_n <= 8'd0;
								wait_n <= GAP - 13'd1;
								ptr    <= ptr + 10'd1;
							end
							else begin
								tap    <= 9'd4;                // F
								walk_n <= walk_n + 8'd1;
							end
						end
						default: begin                     // END
							st    <= S_CHECK;
							chk_n <= CHECK_FRAMES;
							own   <= 1'b0;
							held  <= 9'd0;
							tap   <= 9'd0;
						end
					endcase
				end
			end

			S_CHECK: begin
				if (taken)
					st <= S_IDLE;
				else if (chk_n == 8'd0 || (m_kind == K_MKPIT && chk_n == CHECK_FRAMES - PIT_FRAMES)) begin
					msg_req <= 1'b1;
					msg     <= (m_kind == K_FRIEND || m_kind == K_BABY) ? MSG_NOT_TAKEN_FB : MSG_NOT_TAKEN;
					st <= S_IDLE;
				end
				else
					chk_n <= chk_n - 8'd1;
			end

			default: ;
		endcase
	end
end

endmodule

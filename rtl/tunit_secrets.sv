//============================================================================
//  Secrets: hidden menus and screens of the T-Unit games, from the OSD
//
//  Two mechanisms, both driven by a per-set table the MRA sends as ROM
//  index 1 (tools/tunit_secrets.py finds the addresses in each revision's
//  program ROM and builds it):
//
//  - Code player. The games open their hidden menus when a code is entered
//    on the controls during the attract mode (MK and MK2: the EJB menu,
//    NBA Jam and TE: the secret Midway menu, Judge Dredd: hidden audits and
//    staff credits). An OSD trigger plays the set's code: a list of steps,
//    each an IN0 value (and the two start buttons) held for a number of
//    frames, which replaces the players' IN0 while it plays.
//
//  - Read patches. Up to eight 16-bit words of the CPU's address space read
//    as a fixed value while their OSD option is on: a program ROM word (MK2:
//    the two branches that skip the security screen become NOPs, the branch
//    that skips the Noob Saibot fight unless the round's winner has 50 wins
//    in a row goes nowhere, Jade's and Smoke's conditions are jumped over)
//    or a RAM variable (MK2: the hitbox debug flag,
//    the battle counter that brings up the hidden Pong game at battle 250). A patch can also be tied to a code
//    and apply only while that code plays (MK2 L1.1 and L1.4 have the EJB
//    code's handler but never call it: while the code plays, the Block
//    buttons' switch handlers point at it). The board compares every CPU
//    read with the table (midway_tunit.sv, "Read patches").
//
//  Table (16-bit words, little endian in the MRA; ROM index 1):
//    0x000        game id (low byte; the top level keeps its own copy)
//    0x001        format, 1
//    0x002-0x019  read patches, 8 x 3 words:
//                   address[15:0], {option[3:0], address[27:16]}, value
//                 address is the CPU word address (bit address >> 4);
//                 option 1-3 and 6-8 select OSD option 1-6 (O[16]-O[21]),
//                 4 / 5 applies the patch while code 1 / code 2 plays, 0 is
//                 an unused entry
//    0x01A, 0x01B first step (word index) of code 1 and code 2, 0 = none
//    0x01C-0x01F  success address of code 1, code 2 (word address, 2 words
//                 each, 0 = none): the first word of the menu the code opens.
//                 A code whose CPU never fetches it while it plays (an
//                 attract screen change killed the game's code process
//                 half-way) is played again, up to three times in all, after
//                 a pause long enough for the game to drop what it had.
//    0x020-0x1FF  code steps, 2 words each:
//                   IN0 (active high, the game's IN0 layout),
//                   {last, 5'd0, start2, start1, frames[7:0]}
//                 a code ends with the step that has "last" set
//  Words not sent read as 0 (the table is cleared when a download starts),
//  so an MRA without this table (game id only) has no secrets.
//
//  Copyright (C) 2026 Gm0rk - GPL-3.0-or-later
//============================================================================

module tunit_secrets
(
	input             clk,
	input             reset,

	// ROM index 1 download: word index and data
	input             dl_start,      // pulse: a new table is about to arrive
	input             dl_wr,
	input       [8:0] dl_addr,
	input      [15:0] dl_data,

	// OSD
	input       [1:0] trig,          // rising edge starts code 1 / code 2
	input       [5:0] opt,           // OSD options 1-6 (read patches; options 4-6 are table options 6-8)
	input             frame,         // one pulse per frame while the game runs

	// CPU reads (the board's dbg_rd, dbg_wa): success of a code
	input             cpu_rd,
	input      [27:0] cpu_wa,

	// code player: while code_on, IN0 is code_in0 (active high) and the start
	// buttons in code_start are held
	output reg        code_on,
	output reg [15:0] code_in0,
	output reg  [1:0] code_start,

	// read patches for the board: 8 entries
	output    [223:0] pt_addr,       // 8 x 28-bit word addresses
	output    [127:0] pt_data,       // 8 x 16-bit values
	output reg  [7:0] pt_en          // entry valid and its option on
);

//----------------------------------------------------------------------------
// Table storage: the header in registers, the code steps in a 512 x 16 RAM
//----------------------------------------------------------------------------

reg  [27:0] p_addr [0:7];
reg  [15:0] p_val  [0:7];
reg   [3:0] p_opt  [0:7];
reg   [8:0] c_first [0:1];
reg  [27:0] c_done  [0:1];

reg  [15:0] step_ram [0:511];
reg   [8:0] rd_addr;
reg  [15:0] rd_q;

always @(posedge clk) begin
	if (dl_wr) step_ram[dl_addr] <= dl_data;
	rd_q <= step_ram[rd_addr];
end

// header words: patch entry n at words 2 + 3n .. 4 + 3n, code starts at 26, 27
integer i;
initial begin
	for (i = 0; i < 8; i = i + 1) p_opt[i] = 4'd0;
	c_first[0] = 9'd0;
	c_first[1] = 9'd0;
	c_done[0]  = 28'd0;
	c_done[1]  = 28'd0;
end

always @(posedge clk) begin
	if (dl_start) begin
		for (i = 0; i < 8; i = i + 1) p_opt[i] <= 4'd0;
		c_first[0] <= 9'd0;
		c_first[1] <= 9'd0;
		c_done[0]  <= 28'd0;
		c_done[1]  <= 28'd0;
	end
	else if (dl_wr) begin
		for (i = 0; i < 8; i = i + 1) begin
			if (dl_addr == 9'd2 + 9'd3 * i) p_addr[i][15:0] <= dl_data;
			if (dl_addr == 9'd3 + 9'd3 * i) {p_opt[i], p_addr[i][27:16]} <= dl_data;
			if (dl_addr == 9'd4 + 9'd3 * i) p_val[i] <= dl_data;
		end
		if (dl_addr == 9'd26) c_first[0] <= dl_data[8:0];
		if (dl_addr == 9'd27) c_first[1] <= dl_data[8:0];
		if (dl_addr == 9'd28) c_done[0][15:0]  <= dl_data;
		if (dl_addr == 9'd29) c_done[0][27:16] <= dl_data[11:0];
		if (dl_addr == 9'd30) c_done[1][15:0]  <= dl_data;
		if (dl_addr == 9'd31) c_done[1][27:16] <= dl_data[11:0];
	end
end

// entries for the board, enabled by their option or code (registered: they
// change rarely, and the board registers its compare anyway)
reg cur;                         // code playing: 0 code 1, 1 code 2 (code player below)

genvar g;
generate
	for (g = 0; g < 8; g = g + 1) begin : pt
		assign pt_addr[28 * g +: 28] = p_addr[g];
		assign pt_data[16 * g +: 16] = p_val[g];
		always @(posedge clk)
			pt_en[g] <= (p_opt[g] == 4'd1 && opt[0]) ||
			            (p_opt[g] == 4'd2 && opt[1]) ||
			            (p_opt[g] == 4'd3 && opt[2]) ||
			            (p_opt[g] == 4'd6 && opt[3]) ||
			            (p_opt[g] == 4'd7 && opt[4]) ||
			            (p_opt[g] == 4'd8 && opt[5]) ||
			            (p_opt[g] == 4'd4 && code_on && !cur) ||
			            (p_opt[g] == 4'd5 && code_on && cur);
	end
endgenerate

//----------------------------------------------------------------------------
// Code player
//
// A trigger loads the code's first step. Each step is read from the RAM as
// two words (four clocks) and then held for its number of frames; the
// outputs keep the previous step's values while the next one is read. The
// first step starts at once, so it can be up to one frame shorter than its
// count; every later step starts on a frame pulse.
//
// When the code has a success address and the CPU has not fetched it by the
// end of the code, the player waits RETRY_GAP frames with nothing pressed
// (the game's code process gives up after 16 frames without a press) and
// plays the code again, three times at most.
//----------------------------------------------------------------------------

localparam S_IDLE = 3'd0, S_RD0 = 3'd1, S_RD1 = 3'd2, S_RD2 = 3'd3, S_RD3 = 3'd4, S_HOLD = 3'd5,
           S_GAP = 3'd6;
localparam [7:0] RETRY_GAP = 8'd30;

reg   [1:0] tries;               // plays so far, less one
reg         seen;                // the CPU fetched the success address

// success: registered compare of each completed CPU read with the address
reg  [27:0] done_wa;
always @(posedge clk) done_wa <= cur ? c_done[1] : c_done[0];
wire        hit_done = cpu_rd && cpu_wa == done_wa && done_wa != 28'd0;

reg   [2:0] st;
reg   [1:0] trig_d;
reg   [8:0] ptr;
reg  [15:0] in0_w;
reg   [7:0] cnt;
reg         last;

wire        go1 = trig[0] & ~trig_d[0] & (c_first[0] != 9'd0);
wire        go2 = trig[1] & ~trig_d[1] & (c_first[1] != 9'd0);

always @(posedge clk) begin
	trig_d <= trig;

	if (reset) begin
		st         <= S_IDLE;
		code_on    <= 1'b0;
		code_in0   <= 16'h0000;
		code_start <= 2'b00;
	end
	else if (go1 | go2) begin
		// a trigger (re)starts its code from the first step
		ptr   <= go1 ? c_first[0] : c_first[1];
		cur   <= ~go1;
		tries <= 2'd0;
		seen  <= 1'b0;
		st    <= S_RD0;
	end
	else begin
		if (hit_done && st != S_IDLE) seen <= 1'b1;

		case (st)
			S_RD0: begin                       // address the IN0 word
				rd_addr <= ptr;
				st      <= S_RD1;
			end
			S_RD1: begin                       // IN0 word being read; address the control word
				rd_addr <= ptr + 9'd1;
				st      <= S_RD2;
			end
			S_RD2: begin                       // IN0 word here, control word being read
				in0_w <= rd_q;
				st    <= S_RD3;
			end
			S_RD3: begin                       // control word here: start the step
				code_on    <= 1'b1;
				code_in0   <= in0_w;
				code_start <= rd_q[9:8];
				cnt        <= rd_q[7:0];
				last       <= rd_q[15];
				st         <= S_HOLD;
			end
			S_HOLD: begin
				if (frame) begin
					if (cnt <= 8'd1) begin
						if (last && done_wa != 28'd0 && !seen && tries != 2'd2) begin
							// the menu did not open: pause, then play it again
							tries      <= tries + 2'd1;
							code_in0   <= 16'h0000;
							code_start <= 2'b00;
							cnt        <= RETRY_GAP;
							st         <= S_GAP;
						end
						else if (last) begin       // code finished: hand IN0 back
							code_on    <= 1'b0;
							code_in0   <= 16'h0000;
							code_start <= 2'b00;
							st         <= S_IDLE;
						end
						else begin
							ptr <= ptr + 9'd2;
							st  <= S_RD0;
						end
					end
					else
						cnt <= cnt - 8'd1;
				end
			end
			S_GAP: begin
				if (frame) begin
					if (cnt <= 8'd1) begin
						ptr <= cur ? c_first[1] : c_first[0];
						st  <= S_RD0;
					end
					else
						cnt <= cnt - 8'd1;
				end
			end
			default: ;
		endcase
	end
end

endmodule

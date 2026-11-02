//============================================================================
//  SDRAM controller, 4 burst-read channels + 1 word write channel
//
//  Adapted from Sorgelig's multi-channel MiSTer controller (GPL-3.0, itself
//  using parts of hamsterworks' Simple SDRAM Controller). The pin timing is
//  kept exactly as in that proven design: SDRAM_CLK is clk inverted through an
//  altddio_out, CAS latency 3, data captured through a register stage, one
//  access at a time with auto-precharge.
//
//  Changes for this core: four read channels returning a 64-bit line (burst
//  of 4 words, line address aligned to 8 bytes), one 16-bit write channel with
//  byte enables, and a level req/ack handshake (req toggles to request, ack
//  follows req when done) so clients can queue back-to-back requests.
//
//  Channel priority is fixed: ch0 > ch1 > write > ch2 > ch3. The board puts
//  the latency-critical sound CPU first, then the TMS34010, then the
//  TMS34010's main RAM writes (they are queued, and a main RAM read miss
//  waits for that queue to empty, so they must not wait behind the
//  blitter), then the blitter and the sound samples. ROM downloads also use
//  the write channel, while the board is held in reset.
//
//  Timing (Build 55): the address pins' registers are in the I/O cells, which
//  are far from the logic, so the logic in front of them has to be short. The
//  Build 54 compilation missed by 0.346 ns on cpu_sd_req / rd_delay -> SDRAM_A
//  (8 to 10 logic levels, a 3.4 ns hop into the pin cell). The behaviour is
//  unchanged, clock for clock; what changed is how it is written:
//    - "a read of channel k is in flight" (rd_delay != 0 and rd_ch == k) and
//      "a refresh is due" (refresh_count > REFRESH_CYCLES) are registers
//      (rd_busy, ref_due), computed from the next values of rd_delay, rd_ch
//      and refresh_count;
//    - the choice among the five requests is a flat one-hot (sel*), not a
//      chain of else-ifs, and the address, bank and byte masks it loads are
//      an AND-OR of the five channels' values, assigned once.
//
//  Copyright (C) 2015-2019 Sorgelig, 2026 Gm0rk - GPL-3.0-or-later
//============================================================================

module sdram
(
	input             init,        // reset to initialise the SDRAM
	input             clk,         // 96 MHz

`ifdef SDRAM_SIM
	// simulation: the bidirectional bus split into its two directions
	input      [15:0] SDRAM_DQ_I,
	output     [15:0] SDRAM_DQ_O,
	output            SDRAM_DQ_OE,
`else
	inout      [15:0] SDRAM_DQ,
`endif
	output reg [12:0] SDRAM_A,
	output            SDRAM_DQML,
	output            SDRAM_DQMH,
	output reg  [1:0] SDRAM_BA,
	output            SDRAM_nCS,
	output            SDRAM_nWE,
	output            SDRAM_nRAS,
	output            SDRAM_nCAS,
	output            SDRAM_CKE,
	output            SDRAM_CLK,

	// read channels: toggle req, wait for ack == req, line valid in dout
	input      [24:3] ch0_addr,    // byte address of an 8-byte line (32 MB)
	input             ch0_req,
	output reg        ch0_ack,
	output reg [63:0] ch0_dout,

	input      [24:3] ch1_addr,
	input             ch1_req,
	output reg        ch1_ack,
	output reg [63:0] ch1_dout,

	input      [24:3] ch2_addr,
	input             ch2_req,
	output reg        ch2_ack,
	output reg [63:0] ch2_dout,

	input      [24:3] ch3_addr,
	input             ch3_req,
	output reg        ch3_ack,
	output reg [63:0] ch3_dout,

	// write channel: one 16-bit word
	input      [24:1] wr_addr,
	input      [15:0] wr_data,
	input       [1:0] wr_be,
	input             wr_req,
	output reg        wr_ack
);

assign SDRAM_nCS  = 1'b0;
assign SDRAM_nRAS = command[2];
assign SDRAM_nCAS = command[1];
assign SDRAM_nWE  = command[0];
assign SDRAM_CKE  = 1'b1;
assign {SDRAM_DQMH, SDRAM_DQML} = SDRAM_A[12:11];

localparam BURST_LENGTH   = 4;
localparam BURST_CODE     = 3'b010;
localparam ACCESS_TYPE    = 1'b0;    // sequential
localparam CAS_LATENCY    = 3'd3;
localparam OP_MODE        = 2'b00;
localparam NO_WRITE_BURST = 1'b1;    // reads burst, writes are single words
localparam MODE           = {3'b000, NO_WRITE_BURST, OP_MODE, CAS_LATENCY, ACCESS_TYPE, BURST_CODE};

localparam STARTUP_CYCLES = 14'd12100;  // 100 us plus margin
localparam REFRESH_CYCLES = 14'd740;    // 64 ms / 8192 rows at 96 MHz
localparam STARTUP_MAX    = 14'h3FFF;

localparam [2:0] CMD_NOP          = 3'b111;
localparam [2:0] CMD_ACTIVE       = 3'b011;
localparam [2:0] CMD_READ         = 3'b101;
localparam [2:0] CMD_WRITE        = 3'b100;
localparam [2:0] CMD_PRECHARGE    = 3'b010;
localparam [2:0] CMD_AUTO_REFRESH = 3'b001;
localparam [2:0] CMD_LOAD_MODE    = 3'b000;

localparam STATE_STARTUP = 4'd0;
localparam STATE_WAIT    = 4'd1;
localparam STATE_RW1     = 4'd2;
localparam STATE_IDLE    = 4'd4;
localparam STATE_IDLE_1  = 4'd5;
localparam STATE_IDLE_2  = 4'd6;
localparam STATE_IDLE_3  = 4'd7;
localparam STATE_IDLE_4  = 4'd8;
localparam STATE_IDLE_5  = 4'd9;
localparam STATE_RFSH    = 4'd10;

reg [13:0] refresh_count = STARTUP_MAX - STARTUP_CYCLES;
reg        ref_due = 1'b1;   // refresh_count > REFRESH_CYCLES (registered; the initial count is above it)
// power-up sequencer steps, registered a clock ahead (true when refresh_count equals the step's count in STARTUP)
reg        st_pc   = 1'b0;   // precharge all banks
reg        st_ar   = 1'b0;   // auto refresh
reg        st_lm   = 1'b0;   // load mode register
reg        st_zero = 1'b0;   // refresh_count has wrapped to 0: power-up is over
reg  [2:0] command;
reg  [3:0] state = STATE_STARTUP;

// read data pipeline: one shift register marks when each burst word arrives
localparam DLY = CAS_LATENCY + BURST_LENGTH + 1;
reg  [DLY:0] rd_delay;
reg    [1:0] rd_ch;          // channel of the read in flight
reg    [3:0] rd_busy = 4'd0; // rd_busy[k]: a read of channel k is in flight (rd_delay != 0 && rd_ch == k)
reg   [15:0] dq_reg;
reg   [63:0] rd_line;

reg          saved_wr;
reg   [12:0] cas_addr;
reg   [15:0] dq_out;
reg          dq_oe;

`ifdef SDRAM_SIM
assign SDRAM_DQ_O  = dq_out;
assign SDRAM_DQ_OE = dq_oe;
wire  [15:0] dq_in = SDRAM_DQ_I;
`else
assign SDRAM_DQ    = dq_oe ? dq_out : 16'bZ;
wire  [15:0] dq_in = SDRAM_DQ;
`endif
reg   [15:0] saved_data;
reg    [2:0] cur;            // 0-3 read channel, 4 write

wire             st_startup = (state == STATE_STARTUP);
wire             idle       = (state == STATE_IDLE);
wire             g_rw       = (state == STATE_RW1);                   // column command goes out
wire             g_wr       = g_rw &&  saved_wr;                      // ... a write
wire             rd_set     = g_rw && !saved_wr;                      // ... a read

// the next values of the counters that the arbitration looks at
wire [DLY:0]     rd_delay_n = init ? {(DLY + 1){1'b0}} : {rd_set, rd_delay[DLY:1]};
wire       [1:0] rd_ch_n    = rd_set ? cur[1:0] : rd_ch;
wire             go         = idle && !ref_due;                       // IDLE, nothing to refresh
wire             go_ref     = idle &&  ref_due;                       // IDLE with a refresh due
wire      [13:0] rc_n       = init    ? STARTUP_MAX - STARTUP_CYCLES :
                             st_zero ? 14'd0 :
                             go_ref  ? refresh_count - REFRESH_CYCLES + 1'd1 :
                                       refresh_count + 1'b1;

// which request is granted in IDLE (priority ch0 > ch1 > write > ch2 > ch3): flat, one-hot, gated by go
wire             q0   = (ch0_req != ch0_ack) && !rd_busy[0];
wire             q1   = (ch1_req != ch1_ack) && !rd_busy[1];
wire             qw   = (wr_req  != wr_ack);
wire             q2   = (ch2_req != ch2_ack) && !rd_busy[2];
wire             q3   = (ch3_req != ch3_ack) && !rd_busy[3];
wire             g0   = go && q0;
wire             g1   = go && !q0 && q1;
wire             gw   = go && !q0 && !q1 && qw;
wire             g2   = go && !q0 && !q1 && !qw && q2;
wire             g3   = go && !q0 && !q1 && !qw && !q2 && q3;
wire             g_ld = go && (q0 || q1 || qw || q2 || q3);           // some request is granted
// what the grant loads, {DQM / auto-precharge bits, bank, row, column}; zero when nothing is granted
wire      [27:0] ld   = ({28{g0}} & {2'b00, 1'b1, 1'b0, ch0_addr, 2'b00}) |
                       ({28{g1}} & {2'b00, 1'b1, 1'b0, ch1_addr, 2'b00}) |
                       ({28{gw}} & {~wr_be, 1'b1, 1'b0, wr_addr})        |
                       ({28{g2}} & {2'b00, 1'b1, 1'b0, ch2_addr, 2'b00}) |
                       ({28{g3}} & {2'b00, 1'b1, 1'b0, ch3_addr, 2'b00});

// the address pins, one AND-OR: the grant's row, the held column, or the power-up values
wire      [12:0] pu_a = st_lm ? MODE[12:0] : (st_pc ? 13'h0400 : 13'd0);
wire      [12:0] a_d  = ld[21:9] | ({13{g_rw}} & cas_addr) | pu_a;

always @(posedge clk) begin
	refresh_count <= rc_n;
	ref_due       <= (rc_n > REFRESH_CYCLES);
	rd_delay      <= rd_delay_n;
	rd_ch         <= rd_ch_n;
	rd_busy[0]    <= (|rd_delay_n) && (rd_ch_n == 2'd0);
	rd_busy[1]    <= (|rd_delay_n) && (rd_ch_n == 2'd1);
	rd_busy[2]    <= (|rd_delay_n) && (rd_ch_n == 2'd2);
	rd_busy[3]    <= (|rd_delay_n) && (rd_ch_n == 2'd3);
	dq_reg        <= dq_in;

	// power-up steps for the next clock (the counts are the old compares minus one)
	st_pc   <= !init && st_startup && (refresh_count == (STARTUP_MAX - 64) || refresh_count == (STARTUP_MAX - 32));
	st_ar   <= !init && st_startup && (refresh_count == (STARTUP_MAX - 56) || refresh_count == (STARTUP_MAX - 24) ||
                                       refresh_count == (STARTUP_MAX - 48) || refresh_count == (STARTUP_MAX - 16));
	st_lm   <= !init && st_startup && (refresh_count == (STARTUP_MAX - 40) || refresh_count == (STARTUP_MAX - 8));
	st_zero <= !init && st_startup && (refresh_count == STARTUP_MAX);

	// assemble the four burst words of a line, then hand it to its channel
	if (rd_delay[4]) rd_line[15:0]  <= dq_reg;
	if (rd_delay[3]) rd_line[31:16] <= dq_reg;
	if (rd_delay[2]) rd_line[47:32] <= dq_reg;
	if (rd_delay[1]) begin
		case (rd_ch)
			2'd0: begin ch0_dout <= {dq_reg, rd_line[47:0]}; ch0_ack <= ch0_req; end
			2'd1: begin ch1_dout <= {dq_reg, rd_line[47:0]}; ch1_ack <= ch1_req; end
			2'd2: begin ch2_dout <= {dq_reg, rd_line[47:0]}; ch2_ack <= ch2_req; end
			default: begin ch3_dout <= {dq_reg, rd_line[47:0]}; ch3_ack <= ch3_req; end
		endcase
	end

	// a grant: bank, row and column come from ld; the row goes out now, the column with the command
	if (g_ld) begin
		{cas_addr[12:9], cas_addr[8:0]} <= {ld[27:24], ld[8:0]};
		saved_wr <= gw;
		cur      <= {gw, g2 || g3, g1 || g3};
	end
	if (gw) saved_data <= wr_data;

	// the pins, each written once; idle, wait and read-recovery clocks hold the address
	if (g_ld || g_rw || st_startup) SDRAM_A  <= a_d;
	if (g_ld ||        st_startup) SDRAM_BA <= ld[23:22];
	// command {nRAS, nCAS, nWE}: NOP unless a step below clears a bit
	//   precharge 010, auto refresh 001, load mode 000, active 011, write 100, read 101
	command <= {~(st_pc || st_ar || st_lm || g_ld || go_ref),
                ~(st_ar || st_lm || go_ref || g_rw),
                ~(st_pc || st_lm || g_wr)};
	dq_oe   <= g_wr;
	if (g_wr) begin
		dq_out <= saved_data;
		wr_ack <= wr_req;
	end

	case (state)
		STATE_STARTUP: if (st_zero) state <= STATE_IDLE;     // refresh_count stays 0 (rc_n)
		STATE_IDLE_5:  state <= STATE_IDLE_4;
		STATE_IDLE_4:  state <= STATE_IDLE_3;
		STATE_IDLE_3:  state <= STATE_IDLE_2;
		STATE_IDLE_2:  state <= STATE_IDLE_1;
		STATE_IDLE_1:  state <= STATE_IDLE;
		STATE_RFSH:    state <= STATE_IDLE_5;
		STATE_IDLE:    if (ref_due) state <= STATE_RFSH;     // an auto refresh goes out (command)
					   else if (g_ld) state <= STATE_WAIT;   // an active goes out (command)
		STATE_WAIT:    state <= STATE_RW1;
		STATE_RW1:     state <= saved_wr ? STATE_IDLE_2 : STATE_IDLE_5;
		default:       state <= STATE_IDLE;
	endcase

	if (init)
		state <= STATE_STARTUP;                              // refresh_count, rd_delay: rc_n, rd_delay_n
end

`ifdef SDRAM_SIM
assign SDRAM_CLK = ~clk;
`else
altddio_out
#(
	.extend_oe_disable("OFF"),
	.intended_device_family("Cyclone V"),
	.invert_output("OFF"),
	.lpm_hint("UNUSED"),
	.lpm_type("altddio_out"),
	.oe_reg("UNREGISTERED"),
	.power_up_high("OFF"),
	.width(1)
)
sdramclk_ddr
(
	.datain_h(1'b0),
	.datain_l(1'b1),
	.outclock(clk),
	.dataout(SDRAM_CLK),
	.aclr(1'b0),
	.aset(1'b0),
	.oe(1'b1),
	.outclocken(1'b1),
	.sclr(1'b0),
	.sset(1'b0)
);
`endif

endmodule

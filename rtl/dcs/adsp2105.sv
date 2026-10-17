//============================================================================
//  ADSP-2105 core (DCS sound board, Mortal Kombat II)
//
//  A port of MAME's ADSP-21xx core (src/devices/cpu/adsp2100/adsp2100.cpp
//  and 2100ops.hxx, ADSP-2105 variant): the same registers, the same
//  instruction semantics in the same order, the same flag arithmetic (32-bit
//  ints, the MAC product taken as a 32-bit int and sign-extended, a 48-bit
//  MR with a 16-bit MR2), the same stacks with their over/underflow
//  behaviour, the same DO UNTIL handling (the termination condition is
//  tested when the last instruction is fetched, before it runs) and the same
//  interrupt priorities, vectors, nesting and edge/level selection.
//
//  Timing. MAME runs one instruction per 10 MHz clock and charges nothing
//  for memory or interrupt entry. Here an instruction takes three steps of
//  `ce` (boundary/fetch, decode/address, execute), more while a sound ROM
//  read waits for SDRAM; the board (tunit_dcs) charges each instruction one
//  10 MHz cycle against a cycle debt and lets the next one start (`go`) when
//  the debt is paid, so the program sees MAME's instruction timing while
//  memory latency stays hidden.
//
//  Interrupts are checked at every instruction boundary (MAME checks when a
//  timeslice starts, after IMASK/ICNTL/IFC writes and after a status pop;
//  external lines change only at timeslice ends, so that is the next
//  boundary). IDLE waits at the boundary until an interrupt is taken.
//
//  Board interface (tunit_dcs): program and data memory ports with one ce
//  step of read latency (data reads may wait for dm_rdy), TX1 writes for the
//  board's SPORT1 autobuffer model, interrupt events, a hold at the boundary
//  and an I register side port for the autobuffer copies, MSTAT's timer bit.
//
//  Datapath: one of each unit (see Tables and arithmetic), shared by the
//  instructions that use it; register writes go through one port per
//  register group.
//
//  Every register changes only on ce edges (two-cycle paths in the SDC).
//
//  Based on MAME's adsp2100 core, copyright Aaron Giles (BSD-3-Clause).
//  Copyright (C) 2026 Gm0rk - GPL-3.0-or-later
//============================================================================

module adsp2105
(
	input             clk,
	input             ce,
	input             reset,        // reset line: device_reset() while high
	input             go,           // the next instruction may start
	input             hold_req,     // stop at the next boundary (board copies)
	output            hold_ack,

	// I register side port (dcs.cpp set_state_int on I0-I7), while held
	input             sp_we,
	input       [2:0] sp_idx,
	input      [13:0] sp_val,

	// SPORT1 transmit (dcs.cpp sound_tx_callback(1, ...))
	input             tx1_arm,      // SYSCONTROL bit 11 and S1_AUTOBUF bit 1
	input       [2:0] tx1_ireg,     // S1_AUTOBUF[11:9]
	output reg        tx1_wr,       // one step after an instruction wrote TX1

	// interrupt lines (events, one ce step each)
	input       [2:0] irq_set,      // IRQ0-IRQ2 asserted
	input       [2:0] irq_clr,      // IRQ0-IRQ2 cleared
	input             irq1_pulse,   // IRQ1 for one boundary (dcs_irq)
	input             timer_pulse,  // internal timer (edge only)

	// program memory (read data one step after the address)
	output reg [13:0] pm_a,
	output reg        pm_we,
	output reg [23:0] pm_wd,
	input      [23:0] pm_q,

	// data memory
	output reg [13:0] dm_a,
	output reg        dm_we,
	output reg [15:0] dm_wd,
	output            dm_rd,        // a data read waits for dm_rdy
	output            dm_rd_done,   // that read is taken (read side effects)
	input      [15:0] dm_q,
	input             dm_rdy,

	output            start,        // an instruction starts (one cycle)
	output            idle,
	output            timer_en,     // MSTAT timer bit (dcs.cpp timer_fired)

	// DAG registers (dcs.cpp state_int / get_ibase)
	output [8*14-1:0] i_regs,       // I0-I7, masked to 14 bits as state_int
	output [8*16-1:0] m_regs,       // M0-M7, sign-extended to 16 bits
	output [8*14-1:0] l_regs,       // L0-L7
	output [8*14-1:0] base_regs,    // circular buffer bases

	// debug
	output reg        retire,       // an instruction completed (one step)
	output reg [13:0] ppc_o,        // its address
	output reg        irq_taken     // an interrupt was taken (one step)
);

//----------------------------------------------------------------------------
// Register file
//----------------------------------------------------------------------------

// core registers (MAME adsp_core), two banks; MSTAT bit 0 selects the active
// one (MAME swaps the structures, the same thing)
localparam R_AX0 = 0,  R_AX1 = 1,  R_MX0 = 2,  R_MX1 = 3,
           R_AY0 = 4,  R_AY1 = 5,  R_MY0 = 6,  R_MY1 = 7,
           R_SI  = 8,  R_SE  = 9,  R_AR  = 10, R_MR0 = 11,
           R_MR1 = 12, R_MR2 = 13, R_SR0 = 14, R_SR1 = 15,
           R_AF  = 16, R_MF  = 17, R_SB  = 18;

reg [18:0][15:0] rf0 /*verilator public_flat_rd*/ = '0, rf1 /*verilator public_flat_rd*/ = '0;

reg  [7:0][14:0] ir   /*verilator public_flat_rd*/ = '0;     // I0-I7 (MAME keeps them unmasked after a wrap)
reg  [7:0][13:0] mr   = '0;     // M0-M7 (14-bit, sign-extended when used)
reg  [7:0][13:0] lr   = '0;     // L0-L7
reg  [7:0][13:0] lmr  = {8{14'h3FFF}}; // mask_table[L]
reg  [7:0][13:0] br   = '0;     // base = I & lmask
reg        [7:0] px   /*verilator public_flat_rd*/ = 8'd0;

reg       [13:0] pc   = 14'd0;
reg              loop_v = 1'b0; // m_loop != 0xffff
reg       [13:0] loop_a = 14'd0;
reg        [3:0] loop_c = 4'd0;
reg       [13:0] cntr /*verilator public_flat_rd*/ = 14'd0;
reg        [7:0] astat /*verilator public_flat_rd*/ = 8'd0;
reg        [7:0] sstat = 8'h55;
reg        [6:0] mstat /*verilator public_flat_rd*/ = 7'd0;
reg              idle_r = 1'b0;
reg        [5:0] imask = 6'd0;
reg        [4:0] icntl = 5'd0;

reg [15:0][13:0] pcs = '0;      // PC stack
reg        [4:0] psp = 5'd0;
reg  [3:0][13:0] cs  = '0;      // count stack
reg        [2:0] csp = 3'd0;
reg  [3:0][20:0] ss  = '0;      // status stack {MSTAT, IMASK, ASTAT}
reg        [2:0] ssp = 3'd0;
reg  [3:0][17:0] ls  = '0;      // loop stack {address, condition}
reg        [2:0] lsp = 3'd0;

reg        [2:0] irq_st = 3'd0; // IRQ0-IRQ2 line state
reg        [5:0] irq_lt = 6'd0; // latches: IRQ0, IRQ1, IRQ2, SP0RX, SP0TX, TIMER
reg              irq1_p = 1'b0; // IRQ1 asserted by a pulse: clear after a check

// sequencer
localparam S_BOUND = 2'd0, S_DECODE = 2'd1, S_EXEC = 2'd2;
reg        [1:0] state = S_BOUND;
reg       [23:0] op = 24'd0;    // instruction in decode/execute
reg       [31:0] prod = 32'd0;  // MAC product (decode)
reg       [13:0] dm_ar = 14'd0; // data address (decode)
reg       [13:0] pm_ar = 14'd0; // program data address (decode)
reg              dm_rd_r = 1'b0;// the instruction reads data memory

wire bank = mstat[0];

assign hold_ack = hold_req && (reset || state == S_BOUND);
assign idle     = idle_r;
assign timer_en = mstat[5];
assign dm_rd    = (state == S_EXEC) && dm_rd_r;

genvar gi;
generate for (gi = 0; gi < 8; gi = gi + 1) begin : dagout
	assign i_regs[gi*14 +: 14]    = ir[gi][13:0];
	assign m_regs[gi*16 +: 16]    = {{2{mr[gi][13]}}, mr[gi]};
	assign l_regs[gi*14 +: 14]    = lr[gi];
	assign base_regs[gi*14 +: 14] = br[gi];
end endgenerate


//----------------------------------------------------------------------------
// Tables and arithmetic (MAME create_tables, 2100ops.hxx)
//
// Each function below is used at one place, so each is one piece of
// hardware: one ALU adder, one MAC adder, one shifter (a left and a right
// barrel shifter and a leading-zero count), one DAG step unit for both
// address generators; the stacks do one operation each per step, the I and
// base registers have one write port besides the DAG step.
//----------------------------------------------------------------------------

localparam [7:0] F_Z = 8'h01, F_N = 8'h02, F_V = 8'h04, F_C = 8'h08,
                 F_S = 8'h10, F_Q = 8'h20, F_MV = 8'h40, F_SS = 8'h80;

function automatic [13:0] mask_of(input [13:0] l);
	if      (l > 14'h2000) mask_of = 14'h0000;
	else if (l > 14'h1000) mask_of = 14'h2000;
	else if (l > 14'h0800) mask_of = 14'h3000;
	else if (l > 14'h0400) mask_of = 14'h3800;
	else if (l > 14'h0200) mask_of = 14'h3C00;
	else if (l > 14'h0100) mask_of = 14'h3E00;
	else if (l > 14'h0080) mask_of = 14'h3F00;
	else if (l > 14'h0040) mask_of = 14'h3F80;
	else if (l > 14'h0020) mask_of = 14'h3FC0;
	else if (l > 14'h0010) mask_of = 14'h3FE0;
	else if (l > 14'h0008) mask_of = 14'h3FF0;
	else if (l > 14'h0004) mask_of = 14'h3FF8;
	else if (l > 14'h0002) mask_of = 14'h3FFC;
	else if (l > 14'h0001) mask_of = 14'h3FFE;
	else                   mask_of = 14'h3FFF;
endfunction

function automatic [13:0] rev14(input [13:0] a);
	integer k;
	for (k = 0; k < 14; k = k + 1) rev14[k] = a[13 - k];
endfunction

// m_condition_table (condition 14 is handled by the caller: it counts CNTR)
function automatic cond_tab(input [3:0] c, input [7:0] a);
	reg az, an, av, ac, mv, as_;
	az = a[0]; an = a[1]; av = a[2]; ac = a[3]; as_ = a[4]; mv = a[6];
	case (c)
		4'h0: cond_tab = az;
		4'h1: cond_tab = !az;
		4'h2: cond_tab = !((an ^ av) | az);
		4'h3: cond_tab = (an ^ av) | az;
		4'h4: cond_tab = an ^ av;
		4'h5: cond_tab = !(an ^ av);
		4'h6: cond_tab = av;
		4'h7: cond_tab = !av;
		4'h8: cond_tab = ac;
		4'h9: cond_tab = !ac;
		4'hA: cond_tab = as_;
		4'hB: cond_tab = !as_;
		4'hC: cond_tab = mv;
		4'hD: cond_tab = !mv;
		4'hE: cond_tab = 1'b0;
		default: cond_tab = 1'b1;
	endcase
endfunction

function automatic [15:0] sext8(input [7:0] v);  sext8  = {{8{v[7]}}, v};   endfunction
function automatic [15:0] sext5(input [4:0] v);  sext5  = {{11{v[4]}}, v};  endfunction
function automatic [15:0] sext14(input [13:0] v); sext14 = {{2{v[13]}}, v}; endfunction

// count leading zeros of a 16-bit value (16 for zero)
function automatic [4:0] clz16(input [15:0] v);
	integer k; reg found;
	clz16 = 5'd16; found = 1'b0;
	for (k = 15; k >= 0; k = k - 1)
		if (!found && v[k]) begin clz16 = 5'(15 - k); found = 1'b1; end
endfunction

// ALU (alu_op_ar / alu_op_af): {result[15:0], astat}. MAME works on 32-bit
// ints made from the 16-bit operands; bits 16-0 decide the result and the
// flags, so every arithmetic operation is P + Q + carry in 17 bits
function automatic [23:0] alu_f(input [3:0] amf, input [15:0] xu, input [15:0] yu,
                                input [7:0] st, input [7:0] clr, input sat);
	reg [16:0] p, q, r;
	reg        ci, yq15, vv;
	reg [15:0] res;
	reg  [7:0] a;
	p = 17'd0; q = {1'b0, yu}; ci = 1'b0;
	case (amf)
		4'h1: ci = 1'b1;                                             // Y + 1
		4'h2: begin p = {1'b0, xu}; ci = st[3]; end                  // X + Y + C
		4'h3: p = {1'b0, xu};                                        // X + Y
		4'h5: begin q = {1'b1, ~yu}; ci = 1'b1; end                  // -Y
		4'h6: begin p = {1'b0, xu}; q = {1'b1, ~yu}; ci = st[3]; end // X - Y + C - 1
		4'h7: begin p = {1'b0, xu}; q = {1'b1, ~yu}; ci = 1'b1; end  // X - Y
		4'h8: p = 17'h1FFFF;                                         // Y - 1
		4'h9: begin p = {1'b1, ~xu}; ci = 1'b1; end                  // Y - X
		4'hA: begin p = {1'b1, ~xu}; ci = st[3]; end                 // Y - X + C - 1
		4'hF: begin                                                  // ABS X
			p = xu[15] ? {1'b1, ~xu} : {1'b0, xu}; q = 17'd0; ci = xu[15];
		end
		default: ;                                                   // Y (0), logic
	endcase
	r = p + q + {16'd0, ci};
	case (amf)
		4'h4:    res = ~yu;
		4'hB:    res = ~xu;
		4'hC:    res = xu & yu;
		4'hD:    res = xu | yu;
		4'hE:    res = xu ^ yu;
		default: res = r[15:0];
	endcase
	a = st & clr;
	if (amf != 4'hF) begin
		a[1] = a[1] | res[15];                         // CALC_N
		a[0] = a[0] | (res == 16'd0);                  // CALC_Z
	end
	// CALC_V: x ^ y ^ r ^ (r >> 1), bit 15; X + Y + C takes y + C as its y
	yq15 = (amf == 4'h2) ? (yu[15] ^ (st[3] & (yu[14:0] == 15'h7FFF))) : yu[15];
	vv   = xu[15] ^ yq15 ^ r[15] ^ r[16];
	case (amf)
		4'h1: begin if (yu == 16'h7FFF) a[2] = 1'b1; else if (yu == 16'hFFFF) a[3] = 1'b1; end
		4'h2, 4'h3: begin a[2] = a[2] | vv; a[3] = a[3] | r[16]; end           // CALC_C
		4'h5: begin if (yu == 16'h8000) a[2] = 1'b1; if (yu == 16'h0000) a[3] = 1'b1; end
		4'h6, 4'h7, 4'h9, 4'hA: begin a[2] = a[2] | vv; a[3] = a[3] | ~r[16]; end  // CALC_C_SUB
		4'h8: begin if (yu == 16'h8000) a[2] = 1'b1; else if (yu == 16'h0000) a[3] = 1'b1; end
		4'hF: begin
			a[4] = 1'b0;                               // CLR_S
			if (xu == 16'h0000) a[0] = 1'b1;
			if (xu == 16'h8000) begin a[1] = 1'b1; a[2] = 1'b1; end
			if (xu[15]) a[4] = 1'b1;
		end
		default: ;
	endcase
	if (sat && a[2]) res = a[3] ? 16'h8000 : 16'h7FFF;
	alu_f = {res, a};
endfunction

// MAC: 48-bit result for MR (or MF from its bits 31:16); one adder
function automatic [47:0] mac_f(input [3:0] amf, input [31:0] tmp, input [47:0] mr48);
	reg [47:0] t48, p, q, r;
	reg        ci;
	t48 = {{16{tmp[31]}}, tmp};
	p = 48'd0; q = t48; ci = 1'b0;
	case (amf)
		4'h2, 4'h8, 4'h9, 4'hA, 4'hB: p = mr48;                         // MR + X * Y
		4'h3, 4'hC, 4'hD, 4'hE, 4'hF: begin p = mr48; q = ~t48; ci = 1'b1; end  // MR - X * Y
		default: ;                                                       // X * Y
	endcase
	r = p + q + {47'd0, ci};
	if (amf == 4'h1 || amf == 4'h2 || amf == 4'h3) begin                // RND: + 0x8000
		r[47:15] = r[47:15] + 33'd1;
		if (tmp[15:0] == 16'h8000) r[16] = 1'b0;
	end
	mac_f = r;
endfunction

// the MAC operand signedness for an AMF code: {x signed, y signed}
function automatic [1:0] mac_sign(input [3:0] amf);
	case (amf)
		4'h5, 4'h9, 4'hD: mac_sign = 2'b10;   // SU
		4'h6, 4'hA, 4'hE: mac_sign = 2'b01;   // US
		4'h7, 4'hB, 4'hF: mac_sign = 2'b00;   // UU
		default:          mac_sign = 2'b11;   // SS (and RND)
	endcase
endfunction

// shifter (shift_op / shift_op_imm): {SR[31:0], SE, SB, SS set, SS clear}
//   LSHIFT / ASHIFT: SC > 0 shifts left by SC, else right by -SC (logical /
//   arithmetic; 32 or more: 0 / the sign)
//   NORM: SC > 0 shifts right (HI: AC into bit 31, arithmetic by (SC-1) & 31
//   as x86 masks it; LO: logical by SC), else left by -SC
//   EXP / EXPADJ: one leading-zero count
function automatic [65:0] shift_f(input [3:0] sf, input [15:0] xu, input signed [7:0] sc,
                                  input [31:0] sr, input [15:0] se, input [15:0] sb,
                                  input [7:0] st);
	reg [31:0] w, wr, lo, ro, ru;
	reg  [7:0] mag;
	reg        pos, left, ovf, ovf_r, fill, nhi;
	reg  [4:0] ra, z;
	reg [15:0] nse, nsb, ev;
	reg        ss_set, ss_clr;
	reg signed [31:0] rr;
	nse = se; nsb = sb; ss_set = 1'b0; ss_clr = 1'b0;
	// the operand: HI in bits 31-16; LO in bits 15-0 (sign-extended for ASHIFT)
	if (!sf[1])                 w = {xu, 16'd0};
	else if (sf[3:1] == 3'b011) w = {{16{xu[15]}}, xu};
	else                        w = {16'd0, xu};
	pos  = (sc > 8'sd0);
	mag  = pos ? 8'(sc) : 8'(-sc);                     // 0-128
	ovf  = |mag[7:5];                                   // 32 or more
	nhi  = (sf[3:1] == 3'b100);                         // NORM (HI)
	left = sf[3] ? !pos : pos;
	if (nhi) begin
		wr = {st[3], w[31:1]}; ra = 5'(sc - 8'sd1); fill = st[3]; ovf_r = 1'b0;
	end
	else begin
		wr = w; ra = mag[4:0]; fill = (sf[3:2] == 2'b01) & w[31]; ovf_r = ovf;
	end
	ro = ovf_r ? {32{fill}} : 32'($signed({fill, wr}) >>> ra);
	lo = ovf ? 32'd0 : (w << mag[4:0]);
	ru = left ? lo : ro;
	// exponent: the leading sign bits of X (EXP LO: of X or ~X as SS says)
	ev = (((sf == 4'hE) ? st[7] : xu[15]) ? ~xu : xu);
	z  = clz16(ev);
	rr = (sf == 4'hE) ? (32'(z) + 32'd15) : (32'(z) - 32'd1);
	case (sf)
		4'hC: begin                                        // EXP (HI)
			nse = 16'(-rr);
			if (xu[15]) ss_set = 1'b1; else ss_clr = 1'b1;
		end
		4'hD: begin                                        // EXP (HIX)
			if (st[2]) begin
				nse = 16'd1;
				if (xu[15]) ss_clr = 1'b1; else ss_set = 1'b1;
			end
			else begin
				nse = 16'(-rr);
				if (xu[15]) ss_set = 1'b1; else ss_clr = 1'b1;
			end
		end
		4'hE: if (se == 16'hFFF1) nse = 16'(-rr);          // EXP (LO)
		4'hF: begin                                        // EXPADJ
			// MAME's res is a uint32_t: the comparison with -SB is unsigned
			if ($unsigned(rr) < $unsigned(-$signed({{16{sb[15]}}, sb}))) nsb = 16'(-rr);
		end
		default: ;
	endcase
	if (sf <= 4'hB) ru = sf[0] ? (sr | ru) : ru;
	else            ru = sr;
	shift_f = {ru, nse, nsb, ss_set, ss_clr};
endfunction

// DAG step (modify_address): the new I (15 bits)
function automatic [14:0] dag_step(input [14:0] i, input [13:0] m, input [13:0] l, input [13:0] b);
	reg [31:0] n, ms;
	ms = {{18{m[13]}}, m};
	n  = ({17'd0, i} + ms) & 32'h3FFF;
	if (n < {18'd0, b})                    n = n + {18'd0, l};
	else if (n >= {18'd0, b} + {18'd0, l}) n = n - {18'd0, l};
	dag_step = n[14:0];
endfunction

//----------------------------------------------------------------------------
// Operands
//----------------------------------------------------------------------------

wire [18:0][15:0] cb = bank ? rf1 : rf0;     // active bank
wire [47:0] mr48 = {cb[R_MR2], cb[R_MR1], cb[R_MR0]};
wire [31:0] sr32 = {cb[R_SR1], cb[R_SR0]};
wire  [7:0] aclr = mstat[2] ? 8'hF4 : 8'hF0; // m_astat_clear

function automatic [15:0] alu_x(input [2:0] n, input [18:0][15:0] c);
	case (n)
		3'd0: alu_x = c[R_AX0]; 3'd1: alu_x = c[R_AX1]; 3'd2: alu_x = c[R_AR];  3'd3: alu_x = c[R_MR0];
		3'd4: alu_x = c[R_MR1]; 3'd5: alu_x = c[R_MR2]; 3'd6: alu_x = c[R_SR0]; default: alu_x = c[R_SR1];
	endcase
endfunction
function automatic [15:0] alu_y(input [1:0] n, input [18:0][15:0] c);
	case (n)
		2'd0: alu_y = c[R_AY0]; 2'd1: alu_y = c[R_AY1]; 2'd2: alu_y = c[R_AF]; default: alu_y = 16'd0;
	endcase
endfunction
function automatic [15:0] mac_x(input [2:0] n, input [18:0][15:0] c);
	case (n)
		3'd0: mac_x = c[R_MX0]; 3'd1: mac_x = c[R_MX1]; 3'd2: mac_x = c[R_AR];  3'd3: mac_x = c[R_MR0];
		3'd4: mac_x = c[R_MR1]; 3'd5: mac_x = c[R_MR2]; 3'd6: mac_x = c[R_SR0]; default: mac_x = c[R_SR1];
	endcase
endfunction
function automatic [15:0] mac_y(input [1:0] n, input [18:0][15:0] c);
	case (n)
		2'd0: mac_y = c[R_MY0]; 2'd1: mac_y = c[R_MY1]; 2'd2: mac_y = c[R_MF]; default: mac_y = 16'd0;
	endcase
endfunction

// does this instruction read data / program memory
function automatic [1:0] mem_rd_kind(input [23:0] o);   // {dm read, pm read}
	casez (o[23:16])
		8'h11:                mem_rd_kind = o[15] ? 2'b00 : 2'b01;
		8'h12, 8'h13:         mem_rd_kind = o[15] ? 2'b00 : 2'b10;
		8'b0101_0???:         mem_rd_kind = 2'b01;
		8'b0110_0???, 8'b0111_0???: mem_rd_kind = 2'b10;
		8'b1000_????:         mem_rd_kind = 2'b10;
		8'b11??_????:         mem_rd_kind = 2'b11;
		default:              mem_rd_kind = 2'b00;
	endcase
endfunction

// the MAC operation an instruction does: {is MAC, amf, xop, yop}
function automatic [9:0] mac_of(input [23:0] o);
	reg m;
	casez (o[23:16])
		8'b0010_????, 8'b0101_????, 8'b011?_????: m = !o[17];
		8'b11??_????: m = !o[17];
		default: m = 1'b0;
	endcase
	mac_of = {m, o[16:13], o[10:8], o[12:11]};
endfunction

//----------------------------------------------------------------------------
// DAG unit. DAG1 is I0-I3 with M0-M3, DAG2 I4-I7 with M4-M7; an instruction
// addresses memory through at most one register of each and modifies it
// after the access. One step unit serves both: at decode it steps DAG2's
// register (the instruction just fetched, pm_q; kept until execute), at
// execute DAG1's (written as the instruction completes); the registers do not
// change in between. At execute its operand selection also reads I / M / L
// for register moves and the indirect jump's target.
//----------------------------------------------------------------------------

wire  [7:0] q_oc   = pm_q[23:16];
wire        q_dual = (pm_q[23:22] == 2'b11);
wire  [2:0] q_i1   = {1'b0, pm_q[3:2]};
wire  [2:0] q_i2   = {1'b1, q_dual ? pm_q[7:6] : pm_q[3:2]};
wire  [2:0] q_m2   = {1'b1, q_dual ? pm_q[5:4] : pm_q[1:0]};
// execute: the indirect jump's I4-I7, a group 1 / 2 register read (0x0D
// moves, DM(immediate) writes), else DAG1
wire  [1:0] x_rg   = (op[23:16] == 8'h0D) ? op[9:8] : (op[23:21] == 3'b100) ? op[19:18] : 2'd0;
wire        x_g12  = (x_rg == 2'd1) || (x_rg == 2'd2);
wire  [2:0] x_iu   = (op[23:16] == 8'h0B) ? {1'b1, op[7:6]} : {x_g12 & x_rg[1], x_g12 ? op[1:0] : op[3:2]};
wire  [2:0] x_mu   = {x_g12 & x_rg[1], op[1:0]};
wire  [2:0] u_iu   = (state == S_DECODE) ? q_i2 : x_iu;
wire  [2:0] u_mu   = (state == S_DECODE) ? q_m2 : x_mu;
wire [14:0] u_i    = ir[u_iu];
wire [13:0] u_m    = mr[u_mu];
wire [13:0] u_l    = lr[u_iu];
wire [14:0] u_n    = dag_step(u_i, u_m, u_l, br[u_iu]);
wire [14:0] q_iv1  = ir[q_i1];                 // DAG1's address at decode
wire [14:0] q_iv2  = u_i;                      // DAG2's
// which DAG each instruction modifies: MODIFY (by bit 4), the shifter and
// ALU/MAC memory transfers, DM(I,M) = immediate, the dual reads (both)
wire q_u1  = (q_oc == 8'h09 && !pm_q[4]) || q_oc == 8'h12 || q_oc[7:4] == 4'h6 ||
             q_oc[7:4] == 4'hA || q_dual;
wire q_u2  = (q_oc == 8'h09 && pm_q[4]) || q_oc == 8'h11 || q_oc == 8'h13 ||
             q_oc[7:4] == 4'h5 || q_oc[7:4] == 4'h7 || q_oc[7:4] == 4'hB || q_dual;
// the data address: DM(immediate), DAG2, or DAG1 (bit-reversed in that mode)
wire q_dm2 = q_oc == 8'h13 || q_oc[7:4] == 4'h7 || q_oc[7:4] == 4'hB;
wire q_dm1 = q_oc == 8'h12 || q_oc[7:4] == 4'h6 || q_oc[7:4] == 4'hA || q_dual;
wire [13:0] q_dma = (q_oc[7:5] == 3'b100)  ? pm_q[17:4] :
                    q_dm2                  ? q_iv2[13:0] :
                    (q_dm1 && mstat[1])    ? rev14(q_iv1[13:0]) : q_iv1[13:0];
wire [13:0] q_pma = q_iv2[13:0];

reg       [14:0] ni2_r = 15'd0;                 // DAG2's modified register
reg              u1_r = 1'b0, u2_r = 1'b0;     // ... to be written

//----------------------------------------------------------------------------
// Next state
//----------------------------------------------------------------------------

reg [18:0][15:0] n_rf0, n_rf1, c;
reg  [7:0][14:0] n_ir;
reg  [7:0][13:0] n_mr, n_lr, n_lmr, n_br;
reg        [7:0] n_px;
reg       [13:0] n_pc;
reg              n_loop_v;
reg       [13:0] n_loop_a;
reg        [3:0] n_loop_c;
reg       [13:0] n_cntr;
reg        [7:0] n_astat, n_sstat;
reg        [6:0] n_mstat;
reg              n_idle;
reg        [5:0] n_imask;
reg        [4:0] n_icntl;
reg [15:0][13:0] n_pcs;
reg        [4:0] n_psp;
reg  [3:0][13:0] n_cs;
reg        [2:0] n_csp;
reg  [3:0][20:0] n_ss;
reg        [2:0] n_ssp;
reg  [3:0][17:0] n_ls;
reg        [2:0] n_lsp;
reg        [2:0] n_irq_st;
reg        [5:0] n_irq_lt;
reg              n_irq1_p;
reg        [1:0] n_state;
reg       [23:0] n_op;
reg       [31:0] n_prod;
reg       [13:0] n_dm_ar, n_pm_ar;
reg              n_dm_rd_r;
reg       [14:0] n_ni2;
reg              n_u1, n_u2;
reg              n_tx1;
reg              s_start, s_retire, s_irq;

// requests to the stack units
reg              pc_pop, pc_push, pc_pw, cnt_pop, loop_pop, loop_push, stat_pop, stat_push;
reg              cnd_use;       // the step tests its condition (14 counts CNTR)

// scratch
reg        [7:0] oc;
reg              dual, mclass, x_cond, cnd, cnd_ok;
reg        [3:0] cc;
reg        [5:0] chk;
reg              take;
reg        [2:0] t_which, t_indx;
reg       [13:0] top;
reg        [4:0] psp_a;
reg       [23:0] alu_r;
reg       [47:0] mac_r;
reg       [65:0] sh_r;
reg       [15:0] ax, ay, xv, yv, rdv, wv;
reg        [1:0] rd_g, wgrp;
reg        [3:0] rd_i, widx;
reg              rd_pop, wdo;
reg       [16:0] xs17, ys17;
reg       [33:0] p34;
reg        [9:0] mo;
reg       [16:0] dr;
reg        [2:0] di;
reg       [13:0] lmask, it, lt, ival, bval;
reg        [2:0] tgt;
reg              ig_we, lg_we, tx_we, sp_do, i_do, b_do;
reg signed [7:0] scv;
reg        [1:0] rk, sg;

always_comb begin
	n_rf0 = rf0; n_rf1 = rf1;
	n_ir = ir; n_mr = mr; n_lr = lr; n_lmr = lmr; n_br = br; n_px = px;
	n_pc = pc; n_loop_v = loop_v; n_loop_a = loop_a; n_loop_c = loop_c;
	n_cntr = cntr; n_astat = astat; n_sstat = sstat; n_mstat = mstat;
	n_idle = idle_r; n_imask = imask; n_icntl = icntl;
	n_pcs = pcs; n_psp = psp; n_cs = cs; n_csp = csp; n_ss = ss; n_ssp = ssp;
	n_ls = ls; n_lsp = lsp;
	n_irq_st = irq_st; n_irq_lt = irq_lt; n_irq1_p = irq1_p;
	n_state = state; n_op = op; n_prod = prod; n_dm_ar = dm_ar; n_pm_ar = pm_ar;
	n_dm_rd_r = dm_rd_r; n_ni2 = ni2_r; n_u1 = u1_r; n_u2 = u2_r;
	n_tx1 = 1'b0; s_start = 1'b0; s_retire = 1'b0; s_irq = 1'b0;
	c = cb;

	pm_we = 1'b0; pm_wd = 24'd0;
	dm_we = 1'b0; dm_wd = 16'd0;

	pc_pop = 1'b0; pc_push = 1'b0; pc_pw = 1'b0; cnt_pop = 1'b0;
	loop_pop = 1'b0; loop_push = 1'b0; stat_pop = 1'b0; stat_push = 1'b0;
	cnd_use = 1'b0;

	chk = 6'd0; take = 1'b0; t_which = 3'd0; t_indx = 3'd0;
	alu_r = 24'd0; mac_r = 48'd0; sh_r = 66'd0;
	xv = 16'd0; yv = 16'd0; wv = 16'd0;
	wgrp = 2'd0; widx = 4'd0; wdo = 1'b0; xs17 = 17'd0; ys17 = 17'd0; p34 = 34'd0;
	rk = 2'd0; sg = 2'd0; mo = 10'd0; dr = 17'd0; di = 3'd0; lmask = 14'd0; scv = 8'sd0;
	ig_we = 1'b0; lg_we = 1'b0; tx_we = 1'b0;

	// the instruction in execute
	oc     = op[23:16];
	dual   = (op[23:22] == 2'b11);
	mclass = (op[23:20] == 4'b0101) || (op[23:21] == 3'b011);    // ALU/MAC with memory
	x_cond = (oc == 8'h02 && !op[15]) || oc == 8'h0A || oc == 8'h0B || oc == 8'h0E ||
	         op[23:19] == 5'b00011 || op[23:19] == 5'b00100;

	// the condition unit: the DO UNTIL test at the boundary, the
	// instruction's condition in execute
	cc  = (state == S_BOUND) ? loop_c : op[3:0];
	cnd = (cc == 4'hE) ? (cntr > 14'd1) : cond_tab(cc, astat);
	cnd_ok = x_cond ? cnd : 1'b1;

	// the register read port (read_reg0-3): moves, memory writes
	rd_g = 2'd0; rd_i = op[3:0];
	if (oc == 8'h0D)                  rd_g = op[9:8];
	else if (op[23:21] == 3'b100)     rd_g = op[19:18];
	else if ((op[23:18] == 6'b000100 && op[17:16] != 2'b00) || mclass) rd_i = op[7:4];
	top = pcs[(psp != 5'd0) ? 4'(psp - 5'd1) : 4'd0];
	case (rd_g)
		2'd0: rdv = cb[rd_i];
		2'd1, 2'd2: case (rd_i[3:2])
			2'd0:    rdv = {1'b0, u_i};             // (the DAG unit's operands)
			2'd1:    rdv = sext14(u_m);
			default: rdv = {2'd0, u_l};
		endcase
		default: case (rd_i)
			4'h0:    rdv = {8'd0, astat};
			4'h1:    rdv = {9'd0, mstat};
			4'h2:    rdv = {8'd0, sstat};
			4'h3:    rdv = {10'd0, imask};
			4'h4:    rdv = {11'd0, icntl};
			4'h5:    rdv = {2'd0, cntr};
			4'h6:    rdv = cb[R_SB];
			4'h7:    rdv = {8'd0, px};
			4'hF:    rdv = {2'd0, top};             // TOPPCSTACK: pops
			default: rdv = 16'd0;                   // RX0/RX1 read 0, others invalid
		endcase
	endcase
	rd_pop = (rd_g == 2'd3) && (rd_i == 4'hF) && (oc == 8'h0D || (op[23:21] == 3'b100 && op[20]));

	ax = alu_x(op[10:8], cb);
	ay = alu_y(op[12:11], cb);

	case (state)
	//------------------------------------------------------------------
	// Boundary: take an interrupt (check_irqs) or fetch the next
	// instruction (and do the DO UNTIL handling of execute_run)
	//------------------------------------------------------------------
	S_BOUND: if (!reset && !hold_req) begin
		// adsp2101_device::check_irqs: priority order, the first one pending
		// and unmasked is taken
		chk[0] = (icntl[2] ? irq_lt[2] : irq_st[2]) && imask[5];   // IRQ2
		chk[1] = irq_lt[4] && imask[4];                            // SPORT0 TX
		chk[2] = irq_lt[3] && imask[3];                            // SPORT0 RX
		chk[3] = (icntl[1] ? irq_lt[1] : irq_st[1]) && imask[2];   // IRQ1
		chk[4] = (icntl[0] ? irq_lt[0] : irq_st[0]) && imask[1];   // IRQ0
		chk[5] = irq_lt[5] && imask[0];                            // timer
		take = |chk;
		if      (chk[0]) begin t_which = 3'd2; t_indx = 3'd0; end
		else if (chk[1]) begin t_which = 3'd4; t_indx = 3'd1; end
		else if (chk[2]) begin t_which = 3'd3; t_indx = 3'd2; end
		else if (chk[3]) begin t_which = 3'd1; t_indx = 3'd3; end
		else if (chk[4]) begin t_which = 3'd0; t_indx = 3'd4; end
		else             begin t_which = 3'd5; t_indx = 3'd5; end

		if (irq1_p) begin                      // the pulse lasts one check
			n_irq_st[1] = 1'b0;
			n_irq1_p = 1'b0;
		end

		if (take) begin                        // generate_irq
			s_irq = 1'b1;
			for (int k = 0; k < 6; k = k + 1) if (3'(k) == t_which) n_irq_lt[k] = 1'b0;
			pc_push = 1'b1;
			stat_push = 1'b1;
			n_pc = 14'(4 + 4 * t_indx);
			n_idle = 1'b0;
			if (icntl[4]) n_imask = imask & ~(6'h3F >> t_indx);
			else          n_imask = 6'd0;
		end
		else if (go && !idle_r) begin
			s_start = 1'b1;                    // opcode_read() at pc (pm_a below)
			n_pc = pc + 14'd1;
			if (loop_v && pc == loop_a) begin
				cnd_use = 1'b1;
				if (cnd) n_pc = top;           // keep looping
				else begin                     // done: pop the loop and PC stacks
					loop_pop = 1'b1;
					pc_pop = 1'b1;
				end
			end
			n_state = S_DECODE;
		end
	end

	//------------------------------------------------------------------
	// Decode: latch the opcode, issue the memory reads, step the DAGs,
	// multiply
	//------------------------------------------------------------------
	S_DECODE: begin
		n_op = pm_q;
		n_dm_ar = q_dma;
		n_pm_ar = q_pma;
		rk = mem_rd_kind(pm_q);
		n_dm_rd_r = rk[1];
		n_ni2 = u_n;
		n_u1 = q_u1;   n_u2 = q_u2;
		mo = mac_of(pm_q);
		xv = mac_x(mo[4:2], cb);
		yv = mac_y(mo[1:0], cb);
		sg = mac_sign(mo[8:5]);
		xs17 = sg[1] ? {xv[15], xv} : {1'b0, xv};
		ys17 = sg[0] ? {yv[15], yv} : {1'b0, yv};
		p34  = $signed(xs17) * $signed(ys17);
		n_prod = mstat[4] ? p34[31:0] : {p34[30:0], 1'b0};   // << shift (32-bit)
		n_state = S_EXEC;
	end

	//------------------------------------------------------------------
	// Execute (execute_run's switch), when the data read is ready
	//------------------------------------------------------------------
	S_EXEC: begin
		if (!dm_rd_r || dm_rdy) begin
			s_retire = 1'b1;
			n_state  = S_BOUND;
			cnd_use  = x_cond;

			// the DAG registers modified after the memory accesses
			for (int k = 0; k < 8; k = k + 1) begin
				if (u1_r && 3'(k) == {1'b0, op[3:2]})                  n_ir[k] = u_n;
				if (u2_r && 3'(k) == {1'b1, dual ? op[7:6] : op[3:2]}) n_ir[k] = ni2_r;
			end

			casez (oc)
			8'h02: begin                                   // flag out / idle
				if (op[15]) n_idle = 1'b1;
				// (flag outputs are not connected on the DCS board)
			end
			8'h03: begin                                   // jump/call on flag in (FI = 0)
				if (!op[1]) begin
					if (op[0]) pc_push = 1'b1;
					n_pc = {op[3:2], op[15:4]};
				end
			end
			8'h04: begin                                   // stack control
				pc_pop   = op[4];
				loop_pop = op[3];
				cnt_pop  = op[2];
				if (op[1]) begin
					if (op[0]) stat_pop  = 1'b1;
					else       stat_push = 1'b1;
				end
			end
			8'h05: begin                                   // saturate MR
				if (astat[6]) begin
					if (cb[R_MR2][7]) begin c[R_MR2] = 16'hFFFF; c[R_MR1] = 16'h8000; c[R_MR0] = 16'h0000; end
					else              begin c[R_MR2] = 16'h0000; c[R_MR1] = 16'h7FFF; c[R_MR0] = 16'hFFFF; end
				end
			end
			8'h06: begin                                   // DIVS
				xv = ax ^ ay;
				n_astat[5] = xv[15];
				c[R_AF]  = {ay[14:0], cb[R_AY0][15]};
				c[R_AY0] = {cb[R_AY0][14:0], xv[15]};
			end
			8'h07: begin                                   // DIVQ
				dr = astat[5] ? ({1'b0, cb[R_AF]} + {1'b0, ax}) : ({1'b0, cb[R_AF]} - {1'b0, ax});
				xv = dr[15:0] ^ ax;
				n_astat[5] = xv[15];
				c[R_AF]  = {dr[14:0], cb[R_AY0][15]};
				c[R_AY0] = {cb[R_AY0][14:0], ~xv[15]};
			end
			8'h0A: begin                                   // conditional return
				if (cnd) begin
					pc_pop = 1'b1;
					n_pc = top;
					if (op[4]) stat_pop = 1'b1;            // RTI
				end
			end
			8'h0B: begin                                   // conditional indirect jump
				if (cnd) begin
					if (op[4]) pc_push = 1'b1;
					n_pc = u_i[13:0];                  // I4-I7 (the DAG unit's operand)
				end
			end
			8'h0C: begin                                   // mode control
				if (op[3])  n_mstat[6] = op[2];             // GO mode
				if (op[13]) n_mstat[4] = op[12];            // integer
				if (op[15]) n_mstat[5] = op[14];            // timer
				if (op[5])  n_mstat[0] = op[4];             // bank
				if (op[7])  n_mstat[1] = op[6];             // bit reverse
				if (op[9])  n_mstat[2] = op[8];             // sticky V
				if (op[11]) n_mstat[3] = op[10];            // AR saturation
			end
			8'h0D: begin                                   // internal data move
				wdo = 1'b1; wgrp = op[11:10]; widx = op[7:4]; wv = rdv;
			end
			8'h0E, 8'h0F, 8'b0001_00??: begin              // shifts (+ move / memory)
				scv = (oc == 8'h0F) ? $signed(op[7:0]) : $signed(cb[R_SE][7:0]);
				// memory writes take the register before the shift
				if (oc[7:2] == 6'b000100 && oc[1:0] != 2'b00 && op[15]) begin
					if (oc == 8'h11) begin pm_we = 1'b1; pm_wd = {rdv, px}; end
					else             begin dm_we = 1'b1; dm_wd = rdv; end
				end
				if (cnd_ok && !(oc == 8'h0F && op[14:11] > 4'hB)) begin
					sh_r = shift_f(op[14:11], (op[10:9] == 2'd0) ? cb[R_SI] : ax, scv, sr32,
					               cb[R_SE], cb[R_SB], astat);
					{c[R_SR1], c[R_SR0]} = sh_r[65:34];
					c[R_SE] = sh_r[33:18];
					c[R_SB] = sh_r[17:2];
					if (sh_r[1]) n_astat[7] = 1'b1;
					if (sh_r[0]) n_astat[7] = 1'b0;
				end
				if (oc == 8'h10) begin                     // move after the shift
					wdo = 1'b1; wgrp = 2'd0; widx = op[7:4];
					case (op[3:0])
						4'd9:    wv = c[R_SE];
						4'd14:   wv = c[R_SR0];
						4'd15:   wv = c[R_SR1];
						default: wv = rdv;
					endcase
				end
				else if (oc[7:2] == 6'b000100 && !op[15]) begin   // memory reads
					wdo = 1'b1; wgrp = 2'd0; widx = op[7:4];
					if (oc == 8'h11) begin wv = pm_q[23:8]; n_px = pm_q[7:0]; end
					else             wv = dm_q;
				end
			end
			8'b0001_01??: begin                            // do until
				loop_push = 1'b1;
				pc_push = 1'b1;
			end
			8'b0001_10??: begin                            // conditional jump
				if (cnd) n_pc = op[17:4];
			end
			8'b0001_11??: begin                            // conditional call
				if (cnd) begin
					pc_push = 1'b1;
					n_pc = op[17:4];
				end
			end
			8'b0011_????: begin                            // load register immediate (groups 0-3)
				wdo = 1'b1; wgrp = op[19:18]; widx = op[3:0]; wv = sext14(op[17:4]);
			end
			8'b0100_????: begin                            // load data register immediate
				wdo = 1'b1; wgrp = 2'd0; widx = op[3:0]; wv = op[19:4];
			end
			8'b100?_????: begin                            // DM(immediate) read/write
				if (op[20]) begin dm_we = 1'b1; dm_wd = rdv; end
				else begin wdo = 1'b1; wgrp = op[19:18]; widx = op[3:0]; wv = dm_q; end
			end
			8'b101?_????: begin                            // DM(I,M) = immediate
				dm_we = 1'b1; dm_wd = op[19:4];
			end
			default: begin
				// ALU / MAC classes: 0x20-0x2F, 0x50-0x7F, 0xC0-0xFF
				if (op[23:20] == 4'b0010 || mclass || dual) begin
					// register moves read before the operation
					if (op[23:19] == 5'b00101) begin
						wdo = 1'b1; wgrp = 2'd0; widx = op[7:4]; wv = rdv;
					end
					// memory writes take the register before the operation
					if (mclass && op[19]) begin
						if (op[23:20] == 4'b0101) begin pm_we = 1'b1; pm_wd = {rdv, px}; end
						else                      begin dm_we = 1'b1; dm_wd = rdv; end
					end
					// the operation
					if (cnd_ok) begin
						if (op[17]) begin                    // ALU
							alu_r = alu_f(op[16:13], ax, ay, astat, aclr, mstat[3] && !(op[18] && !dual));
							n_astat = alu_r[7:0];
							if (op[18] && !dual) c[R_AF] = alu_r[23:8];
							else                 c[R_AR] = alu_r[23:8];
						end
						else if (op[16:13] != 4'h0) begin    // MAC (0: no-op)
							mac_r = mac_f(op[16:13], prod, mr48);
							if (op[18] && !dual) c[R_MF] = mac_r[31:16];
							else begin
								n_astat[6] = !(mac_r[39:31] == 9'h000 || mac_r[39:31] == 9'h1FF);
								c[R_MR0] = mac_r[15:0];
								c[R_MR1] = mac_r[31:16];
								c[R_MR2] = mac_r[47:32];
							end
						end
					end
					// memory reads after the operation
					if (mclass && !op[19]) begin
						wdo = 1'b1; wgrp = 2'd0; widx = op[7:4];
						if (op[23:20] == 4'b0101) begin wv = pm_q[23:8]; n_px = pm_q[7:0]; end
						else                      wv = dm_q;
					end
					if (dual) begin                         // dual read: X = DM(DAG1), Y = PM(DAG2)
						case (op[19:18])
							2'd0: c[R_AX0] = dm_q; 2'd1: c[R_AX1] = dm_q;
							2'd2: c[R_MX0] = dm_q; default: c[R_MX1] = dm_q;
						endcase
						case (op[21:20])
							2'd0: c[R_AY0] = pm_q[23:8]; 2'd1: c[R_AY1] = pm_q[23:8];
							2'd2: c[R_MY0] = pm_q[23:8]; default: c[R_MY1] = pm_q[23:8];
						endcase
						n_px = pm_q[7:0];
					end
				end
				// 0x00 NOP, 0x01 (218x I/O), 0x08 reserved, 0x09 MODIFY (the
				// DAG step above): nothing
			end
			endcase
		end
	end
	default: n_state = S_BOUND;
	endcase

	// the condition's CNTR count (condition 14): count down, or pop the
	// count stack when it runs out
	if (cnd_use && cc == 4'hE) begin
		if (cnd) n_cntr = cntr - 14'd1;
		else     cnt_pop = 1'b1;
	end
	// count stack pop (the push is the CNTR write below)
	if (cnt_pop) begin
		if (csp != 3'd0) begin n_csp = csp - 3'd1; if (csp == 3'd1) n_sstat[2] = 1'b1; end
		n_cntr = cs[n_csp[1:0]];
	end

	// the register write of the instruction (write_reg0-3), last
	if (wdo) begin
		case (wgrp)
		2'd0: case (widx)
			4'd9:  c[R_SE]  = sext8(wv[7:0]);
			4'd12: begin c[R_MR1] = wv; c[R_MR2] = {16{wv[15]}}; end
			4'd13: c[R_MR2] = sext8(wv[7:0]);
			default: for (int k = 0; k < 16; k = k + 1) if (4'(k) == widx) c[k] = wv;
		endcase
		2'd1, 2'd2: begin
			di = {wgrp[1], widx[1:0]};
			lmask = mask_of(wv[13:0]);
			case (widx[3:2])
				2'd0: ig_we = 1'b1;                       // I (and its base, below)
				2'd1: for (int k = 0; k < 8; k = k + 1) if (3'(k) == di) n_mr[k] = wv[13:0];
				2'd2: begin                               // L (and the base, below)
					lg_we = 1'b1;
					for (int k = 0; k < 8; k = k + 1) if (3'(k) == di) begin n_lr[k] = wv[13:0]; n_lmr[k] = lmask; end
				end
				default: ;                                // invalid (218x overlays)
			endcase
		end
		default: case (widx)
			4'h0: n_astat = wv[7:0];
			4'h1: n_mstat = wv[6:0];
			4'h3: n_imask = wv[5:0];
			4'h4: n_icntl = wv[4:0];
			4'h5: begin                                   // CNTR: push the old count
				if (csp < 3'd4) begin
					for (int k = 0; k < 4; k = k + 1) if (2'(k) == csp[1:0]) n_cs[k] = cntr;
					n_csp = csp + 3'd1; n_sstat[2] = 1'b0;
				end
				else n_sstat[3] = 1'b1;
				n_cntr = wv[13:0];
			end
			4'h6: c[R_SB] = sext5(wv[4:0]);
			4'h7: n_px = wv[7:0];
			4'hB: begin                                   // TX1: sound_tx_callback(1)
				n_tx1 = 1'b1;
				tx_we = tx1_arm;                          // align I (below)
			end
			4'hC: begin                                   // IFC
				if (wv[1])  n_irq_lt[0] = 1'b0;
				if (wv[2])  n_irq_lt[1] = 1'b0;
				if (wv[3])  n_irq_lt[3] = 1'b0;
				if (wv[4])  n_irq_lt[4] = 1'b0;
				if (wv[5])  n_irq_lt[2] = 1'b0;
				if (wv[7])  n_irq_lt[0] = 1'b1;
				if (wv[8])  n_irq_lt[1] = 1'b1;
				if (wv[9])  n_irq_lt[3] = 1'b1;
				if (wv[10]) n_irq_lt[4] = 1'b1;
				if (wv[11]) n_irq_lt[2] = 1'b1;
			end
			4'hD: n_cntr = wv[13:0];                      // OWRCNTR
			4'hF: begin pc_push = 1'b1; pc_pw = 1'b1; end // TOPPCSTACK
			default: ;                                    // SSTAT, TX0 (no-op), RX
		endcase
		endcase
	end

	// PC stack: a pop (RTS/RTI, POP PC, TOPPCSTACK read, loop end), then a
	// push (CALL, DO, interrupt, TOPPCSTACK write)
	pc_pop = pc_pop | (rd_pop & s_retire);
	psp_a = (pc_pop && psp != 5'd0) ? psp - 5'd1 : psp;
	if (pc_pop && psp == 5'd1) n_sstat[0] = 1'b1;
	n_psp = psp_a;
	if (pc_push) begin
		if (psp_a < 5'd16) begin
			for (int k = 0; k < 16; k = k + 1) if (4'(k) == psp_a[3:0]) n_pcs[k] = pc_pw ? wv[13:0] : pc;
			n_psp = psp_a + 5'd1;
			n_sstat[0] = 1'b0;
		end
		else n_sstat[1] = 1'b1;
	end

	// loop stack: push (DO) or pop
	if (loop_push) begin
		if (lsp < 3'd4) begin
			for (int k = 0; k < 4; k = k + 1) if (2'(k) == lsp[1:0]) n_ls[k] = op[17:0];
			n_lsp = lsp + 3'd1;
			n_loop_v = 1'b1; n_loop_a = op[17:4]; n_loop_c = op[3:0]; n_sstat[6] = 1'b0;
		end
		else n_sstat[7] = 1'b1;
	end
	if (loop_pop && lsp != 3'd0) begin
		n_lsp = lsp - 3'd1;
		if (lsp == 3'd1) begin n_loop_v = 1'b0; n_loop_c = 4'd0; n_sstat[6] = 1'b1; end
		else begin n_loop_a = ls[2'(lsp - 3'd2)][17:4]; n_loop_c = ls[2'(lsp - 3'd2)][3:0]; end
	end

	// status stack: push (PUSH STS, interrupt) or pop (POP STS, RTI)
	if (stat_push) begin
		if (ssp < 3'd4) begin
			for (int k = 0; k < 4; k = k + 1) if (2'(k) == ssp[1:0]) n_ss[k] = {mstat, imask, astat};
			n_ssp = ssp + 3'd1; n_sstat[4] = 1'b0;
		end
		else n_sstat[5] = 1'b1;
	end
	if (stat_pop) begin
		if (ssp != 3'd0) begin n_ssp = ssp - 3'd1; if (ssp == 3'd1) n_sstat[4] = 1'b1; end
		{n_mstat, n_imask, n_astat} = ss[n_ssp[1:0]];
	end

	// the core registers go back to the bank they came from
	if (bank) n_rf1 = c; else n_rf0 = c;

	// interrupt lines (execute_set_input: a rising edge sets the latch)
	for (int k = 0; k < 3; k = k + 1) begin
		if (irq_set[k] || (k == 1 && irq1_pulse)) begin
			if (!n_irq_st[k]) n_irq_lt[k] = 1'b1;
			n_irq_st[k] = 1'b1;
		end
		if (irq_clr[k]) n_irq_st[k] = 1'b0;
	end
	if (irq1_pulse) n_irq1_p = 1'b1;
	if (timer_pulse) n_irq_lt[5] = 1'b1;

	// the I / base register write port (besides the DAG steps): an I or L
	// register write, TX1's alignment of the autobuffer I, or the board's side
	// port (set_state_int: update_i), which also works while the CPU is held
	// in reset (MAME's suspended CPU keeps its registers); device_reset
	sp_do = hold_ack && sp_we;
	tgt   = sp_do ? sp_idx : tx_we ? tx1_ireg : di;
	it    = ir[tgt][13:0];
	lt    = lmr[tgt];
	if (sp_do)      begin ival = sp_val;            bval = sp_val & lt; end
	else if (tx_we) begin ival = it & 14'h3FF0;     bval = it & 14'h3FF0 & lt; end
	else if (lg_we) begin ival = it;                bval = it & lmask; end
	else            begin ival = wv[13:0];          bval = wv[13:0] & lt; end
	i_do = sp_do || (!reset && (tx_we || ig_we));
	b_do = sp_do || (!reset && (tx_we || ig_we || lg_we));
	for (int k = 0; k < 8; k = k + 1) begin
		if (reset) begin
			n_ir[k] = {1'b0, ir[k][13:0]};
			n_br[k] = ir[k][13:0] & lmr[k];
		end
		if (3'(k) == tgt) begin
			if (i_do) n_ir[k] = {1'b0, ival};
			if (b_do) n_br[k] = bval;
		end
	end

	// device_reset while the reset line is high
	if (reset) begin
		n_pc = 14'd0; n_loop_v = 1'b0; n_loop_c = 4'd0;
		n_mstat = 7'd0; n_sstat = 8'h55; n_idle = 1'b0;
		n_psp = 5'd0; n_csp = 3'd0; n_ssp = 3'd0; n_lsp = 3'd0;
		n_imask = 6'd0; n_irq_st = 3'd0; n_irq_lt = 6'd0; n_irq1_p = 1'b0;
		n_state = S_BOUND; n_tx1 = 1'b0; s_start = 1'b0; s_retire = 1'b0; s_irq = 1'b0;
		pm_we = 1'b0; dm_we = 1'b0;
	end
end

// memory addresses: the fetch at the boundary, the data addresses from the
// decode on (into the RAMs at the decode edge, held while executing)
always_comb begin
	case (state)
		S_DECODE: begin dm_a = q_dma; pm_a = q_pma; end
		S_EXEC:   begin dm_a = dm_ar; pm_a = pm_ar; end
		default:  begin dm_a = dm_ar; pm_a = pc; end
	endcase
end

assign start      = ce & s_start;
assign dm_rd_done = ce & s_retire & dm_rd_r;

always @(posedge clk) begin
	if (ce) begin
		rf0 <= n_rf0; rf1 <= n_rf1;
		ir <= n_ir; mr <= n_mr; lr <= n_lr; lmr <= n_lmr; br <= n_br; px <= n_px;
		pc <= n_pc; loop_v <= n_loop_v; loop_a <= n_loop_a; loop_c <= n_loop_c;
		cntr <= n_cntr; astat <= n_astat; sstat <= n_sstat; mstat <= n_mstat;
		idle_r <= n_idle; imask <= n_imask; icntl <= n_icntl;
		pcs <= n_pcs; psp <= n_psp; cs <= n_cs; csp <= n_csp; ss <= n_ss; ssp <= n_ssp;
		ls <= n_ls; lsp <= n_lsp;
		irq_st <= n_irq_st; irq_lt <= n_irq_lt; irq1_p <= n_irq1_p;
		state <= n_state; op <= n_op; prod <= n_prod; dm_ar <= n_dm_ar; pm_ar <= n_pm_ar;
		dm_rd_r <= n_dm_rd_r;
		ni2_r <= n_ni2; u1_r <= n_u1; u2_r <= n_u2;
		tx1_wr <= n_tx1;
		retire <= s_retire;
		irq_taken <= s_irq;
		if (s_start) ppc_o <= pc;
	end
end

endmodule

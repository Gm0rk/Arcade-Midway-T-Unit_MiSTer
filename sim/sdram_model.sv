//============================================================================
//  SDRAM chip model for simulation (32 MB, 16-bit, CAS latency 3, burst 4)
//
//  Behaves like the MiSTer SDRAM module as rtl/sdram.sv drives it: ACTIVE
//  opens a row, READ (always with auto-precharge) returns four words,
//  WRITE stores one word under the DQM byte masks.
//
//  Timing, on the controller's clock: the controller registers READ at edge
//  P0 and takes word 0 from its input register at P5, so the word must be
//  on the bus between P3 and P4. The model sees the command at P1 and
//  queues the four words in a pipeline that puts word 0 on the bus at P3,
//  then one word per clock.
//
//  The memory array is public so the C++ harness can preload ROM images.
//
//  Copyright (C) 2026 Gm0rk - GPL-3.0-or-later
//============================================================================

module sdram_model
(
	input             clk,
	input      [12:0] a,
	input       [1:0] ba,
	input             ncas,
	input             nras,
	input             nwe,
	input             dqml,
	input             dqmh,
	input      [15:0] dq_o,          // from the controller
	output reg [15:0] dq_i           // to the controller
);

reg  [15:0] mem [0:16*1024*1024-1] /* verilator public */;

reg  [12:0] row [0:3];
wire  [2:0] cmd = {nras, ncas, nwe};

// read pipeline: slot 0 goes on the bus at the next edge
reg  [23:0] rd_addr [0:4];
reg   [4:0] rd_v;

integer k;
always @(posedge clk) begin
	dq_i <= rd_v[0] ? mem[rd_addr[0]] : 16'h0000;
	for (k = 0; k < 4; k = k + 1) begin
		rd_v[k]    <= rd_v[k + 1];
		rd_addr[k] <= rd_addr[k + 1];
	end
	rd_v[4] <= 1'b0;

	case (cmd)
		3'b011: row[ba] <= a;                                    // ACTIVE
		3'b101: begin                                            // READ, burst of 4
			for (k = 0; k < 4; k = k + 1) begin
				rd_v[k + 1]    <= 1'b1;
				rd_addr[k + 1] <= {ba, row[ba], a[8:2], 2'(k)};
			end
		end
		3'b100: begin                                            // WRITE, one word
			if (!dqml) mem[{ba, row[ba], a[8:0]}][7:0]  <= dq_o[7:0];
			if (!dqmh) mem[{ba, row[ba], a[8:0]}][15:8] <= dq_o[15:8];
		end
		default: ;
	endcase
end

endmodule

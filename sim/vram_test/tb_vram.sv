//============================================================================
//  tb_vram.sv — reset of rtl/tunit_vram.sv in the middle of DDR3 operations
//
//  A DDR3 model with random busy checks the Avalon rules the MiSTer DDRAM
//  bridge needs: a raised read or write stays up until accepted, a write
//  burst delivers all its beats, no read is issued inside an open write
//  burst. 400 times a blitter row write (two bursts) and a display read are
//  started and the reset comes at a different point of them; after each
//  reset the toggles must be equal and the controller must serve a new
//  blitter write.
//
//  Copyright (C) 2026 Gm0rk. Distributed under GNU GPL v3 or later.
//============================================================================
`timescale 1ns/1ps
module tb;
reg clk = 0; always #5 clk = ~clk;
reg reset = 1;
reg ddr_busy = 0;
wire [7:0] ddr_burstcnt; wire [28:0] ddr_addr; wire ddr_rd, ddr_we; wire [63:0] ddr_din; wire [7:0] ddr_be;
reg [63:0] ddr_dout = 0; reg ddr_dout_ready = 0;
reg disp_req = 0, srt_req = 0, blt_req = 0, cpu_req = 0;
wire disp_ack, srt_ack, blt_ack, cpu_ack;
reg [8:0] disp_row = 9'd5, blt_row = 9'd7; reg [7:0] blt_lo = 8'd0, blt_hi = 8'd200;
wire [7:0] blt_raddr; reg [63:0] blt_q = 64'h1234; reg [7:0] blt_be = 8'hFF;
wire lb_we; wire [6:0] lb_addr; wire [63:0] lb_data; wire [15:0] srt_first; wire [31:0] cpu_rdata;
tunit_vram dut(.clk(clk), .reset(reset), .ddr_busy(ddr_busy), .ddr_burstcnt(ddr_burstcnt), .ddr_addr(ddr_addr),
  .ddr_dout(ddr_dout), .ddr_dout_ready(ddr_dout_ready), .ddr_rd(ddr_rd), .ddr_din(ddr_din), .ddr_be(ddr_be), .ddr_we(ddr_we),
  .disp_req(disp_req), .disp_ack(disp_ack), .disp_row(disp_row), .lb_we(lb_we), .lb_addr(lb_addr), .lb_data(lb_data),
  .srt_req(srt_req), .srt_ack(srt_ack), .srt_wr(1'b0), .srt_entry(19'd0), .srt_first(srt_first),
  .blt_req(blt_req), .blt_ack(blt_ack), .blt_row(blt_row), .blt_lo(blt_lo), .blt_hi(blt_hi), .blt_raddr(blt_raddr), .blt_q(blt_q), .blt_be(blt_be),
  .cpu_req(cpu_req), .cpu_ack(cpu_ack), .cpu_wr(1'b0), .cpu_qaddr(17'd0), .cpu_half(1'b0), .cpu_be(4'hF), .cpu_wdata(32'd0), .cpu_rdata(cpu_rdata));
// DDR3 model
integer wr_left = 0, rd_q = 0, errors = 0, bursts = 0, rd_cmds = 0, we_cyc = 0, beats = 0;
reg prev_we = 0, prev_rd = 0, prev_busy = 0;
integer lfsr = 1;
always @(posedge clk) begin
  lfsr = (lfsr * 1103515245 + 12345) & 32'h7fffffff;
  // Avalon: a request raised while busy must stay up
  if (prev_we && prev_busy && !ddr_we) begin errors = errors + 1; $display("ERROR write withdrawn at %0t", $time); end
  if (prev_rd && prev_busy && !ddr_rd) begin errors = errors + 1; $display("ERROR read withdrawn at %0t", $time); end
  if (wr_left > 0 && !ddr_we && !prev_busy) ; // gap inside a burst is legal (no beat)
  if (ddr_we) we_cyc = we_cyc + 1;
  if (ddr_we && !ddr_busy) begin beats = beats + 1;
    if (wr_left == 0) begin wr_left = ddr_burstcnt; bursts = bursts + 1; end
    wr_left = wr_left - 1;
  end
  if (ddr_rd && !ddr_busy) begin
    if (wr_left != 0) begin errors = errors + 1; $display("ERROR read during an open write burst at %0t (%0d beats left)", $time, wr_left); end
    rd_q = rd_q + ddr_burstcnt; rd_cmds = rd_cmds + 1;
  end
  ddr_dout_ready <= (rd_q > 0) && (lfsr[3:0] != 0);
  if ((rd_q > 0) && (lfsr[3:0] != 0)) rd_q = rd_q - 1;
  prev_we = ddr_we; prev_rd = ddr_rd; prev_busy = ddr_busy;
  ddr_busy <= (lfsr[7:4] == 0);
end
integer t, i;
initial begin
  repeat (20) @(posedge clk); reset = 0;
  for (t = 0; t < 400; t = t + 1) begin
    // start a blitter row write (two bursts) and a display read, reset somewhere inside
    @(posedge clk); blt_req = ~blt_req; disp_req = ~disp_req;
    repeat (t % 230) @(posedge clk);
    reset = 1;
    repeat (4200) @(posedge clk);
    if (wr_left != 0) begin errors = errors + 1; $display("ERROR burst left open after reset (%0d beats) t=%0d", wr_left, t); end
    // requesters resync their toggles in reset (as tunit_dma / the board do)
    blt_req = blt_ack;
    reset = 0;
    repeat (2) @(posedge clk);
    if (blt_req != blt_ack) begin errors = errors + 1; $display("ERROR blt toggles unequal after reset t=%0d", t); end
    if (disp_req != disp_ack) begin errors = errors + 1; $display("ERROR disp toggles unequal after reset t=%0d", t); end
    // the controller works after the reset: a full blitter write
    blt_req = ~blt_req;
    for (i = 0; i < 3000 && blt_req != blt_ack; i = i + 1) @(posedge clk);
    if (blt_req != blt_ack) begin errors = errors + 1; $display("ERROR no service after reset t=%0d", t); end
    while (rd_q > 0) @(posedge clk);
  end
  $display("we cycles %0d beats %0d", we_cyc, beats); $display("%0d resets, %0d write bursts, %0d read commands, %0d errors", t, bursts, rd_cmds, errors);
  $finish;
end
endmodule

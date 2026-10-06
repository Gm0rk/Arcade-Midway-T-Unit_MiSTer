//============================================================================
//  altsyncram - behavioural model for Verilator and lint (not part of the core)
//
//  Covers only what the core instantiates: BIDIR_DUAL_PORT with both ports
//  on the same clock, addresses and write data registered at the clock
//  (under clocken0 for port A, and clocken1 for port B when it is
//  registered on CLOCK1), byte enables, outputs unregistered (q shows the
//  word addressed on the last enabled clock), new data on a same-port
//  read-during-write. Quartus supplies the real megafunction.
//
//  Copyright (C) 2026 Gm0rk - GPL-3.0-or-later
//============================================================================

/* verilator lint_off UNUSEDPARAM */
/* verilator lint_off UNUSEDSIGNAL */
module altsyncram #(
	parameter operation_mode                     = "BIDIR_DUAL_PORT",
	parameter intended_device_family             = "Cyclone V",
	parameter lpm_type                           = "altsyncram",
	parameter ram_block_type                     = "M10K",
	parameter width_a                            = 16,
	parameter widthad_a                          = 14,
	parameter numwords_a                         = 16384,
	parameter width_b                            = 16,
	parameter widthad_b                          = 14,
	parameter numwords_b                         = 16384,
	parameter width_byteena_a                    = 1,
	parameter width_byteena_b                    = 1,
	parameter address_reg_b                      = "CLOCK0",
	parameter byteena_reg_b                      = "CLOCK0",
	parameter rdcontrol_reg_b                    = "CLOCK0",
	parameter indata_reg_b                       = "CLOCK0",
	parameter wrcontrol_wraddress_reg_b          = "CLOCK0",
	parameter outdata_reg_a                      = "UNREGISTERED",
	parameter outdata_reg_b                      = "UNREGISTERED",
	parameter outdata_aclr_a                     = "NONE",
	parameter outdata_aclr_b                     = "NONE",
	parameter clock_enable_input_a               = "BYPASS",
	parameter clock_enable_input_b               = "BYPASS",
	parameter clock_enable_output_a              = "BYPASS",
	parameter clock_enable_output_b              = "BYPASS",
	parameter read_during_write_mode_port_a      = "NEW_DATA_NO_NBE_READ",
	parameter read_during_write_mode_port_b      = "NEW_DATA_NO_NBE_READ",
	parameter read_during_write_mode_mixed_ports = "DONT_CARE",
	parameter power_up_uninitialized             = "FALSE"
)
(
	input                        clock0,
	input                        clock1,
	input      [widthad_a-1:0]   address_a,
	input      [width_a-1:0]     data_a,
	input                        wren_a,
	output     [width_a-1:0]     q_a,
	input      [widthad_b-1:0]   address_b,
	input      [width_b-1:0]     data_b,
	input                        wren_b,
	output     [width_b-1:0]     q_b,
	input                        aclr0,
	input                        aclr1,
	input                        addressstall_a,
	input                        addressstall_b,
	input  [width_byteena_a-1:0] byteena_a,
	input  [width_byteena_b-1:0] byteena_b,
	input                        clocken0,
	input                        clocken1,
	input                        clocken2,
	input                        clocken3,
	input                        rden_a,
	input                        rden_b,
	output                       eccstatus
);

reg [width_a-1:0]   mem [0:numwords_a-1];
reg [widthad_a-1:0] ra_a;
reg [widthad_b-1:0] ra_b;

integer i;
initial for (i = 0; i < numwords_a; i = i + 1) mem[i] = {width_a{1'b0}};

localparam BYTES_A = width_byteena_a;
localparam BW_A    = width_a / BYTES_A;
wire       en_b    = (address_reg_b == "CLOCK1") ? clocken1 : clocken0;

integer j;
always @(posedge clock0) begin
	if (clocken0) begin
		if (wren_a)
			for (j = 0; j < BYTES_A; j = j + 1)
				if (byteena_a[j]) mem[address_a][j * BW_A +: BW_A] <= data_a[j * BW_A +: BW_A];
		ra_a <= address_a;
	end
	if (en_b) begin
		if (wren_b) mem[address_b] <= data_b;
		ra_b <= address_b;
	end
end

assign q_a = mem[ra_a];
assign q_b = mem[ra_b];
assign eccstatus = 1'b0;

endmodule
/* verilator lint_on UNUSEDSIGNAL */
/* verilator lint_on UNUSEDPARAM */

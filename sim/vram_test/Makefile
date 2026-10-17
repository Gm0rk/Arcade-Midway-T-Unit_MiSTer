# VRAM controller reset test: rtl/tunit_vram.sv against an Avalon checker.
#   make
RTL = ../../rtl

all: tb_vram.vvp
	vvp tb_vram.vvp | tail -2

tb_vram.vvp: tb_vram.sv $(RTL)/tunit_vram.sv
	iverilog -g2012 -o tb_vram.vvp tb_vram.sv $(RTL)/tunit_vram.sv

clean:
	rm -f tb_vram.vvp

.PHONY: all clean

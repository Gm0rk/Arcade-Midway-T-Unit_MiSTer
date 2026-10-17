# ADSP-2105 core against MAME's ADSP-21xx code, in lockstep
#
#   make MAME=<mame source folder>     build obj_cpu/tb_cpu
#   make run                           200 random programs x 20000 instructions
#
# mkref.py builds the reference from MAME's own source files.

MAME ?= ../../../ref/mame
RTL   = ../../rtl

all: obj_cpu/tb_cpu

obj_cpu/adsp_ref.h: mkref.py
	mkdir -p obj_cpu
	python3 mkref.py $(MAME)/src/devices/cpu/adsp2100 > $@

obj_cpu/tb_cpu: $(RTL)/dcs/adsp2105.sv tb_cpu.cpp obj_cpu/adsp_ref.h
	verilator --cc --exe --build -j 2 -O3 --public-flat-rw -Wno-fatal -Wno-WIDTH \
		--top-module adsp2105 --Mdir obj_cpu -o tb_cpu \
		-CFLAGS "-std=c++20 -O2 -I$(abspath obj_cpu) -w" \
		$(RTL)/dcs/adsp2105.sv tb_cpu.cpp

run: obj_cpu/tb_cpu
	./obj_cpu/tb_cpu 200 20000 1

clean:
	rm -rf obj_cpu

.PHONY: all run clean

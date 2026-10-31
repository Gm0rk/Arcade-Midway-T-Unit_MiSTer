# OSD cheats receiver test: rtl/tunit_cheats.sv on its own.
#   make && ./obj_dir/Vtunit_cheats

RTL = ../../rtl

all: obj_dir/Vtunit_cheats

obj_dir/Vtunit_cheats: tb_cheats.cpp $(RTL)/tunit_cheats.sv
	verilator --cc --exe --build -j 2 -O3 --x-assign fast --x-initial fast --noassert \
		-Wall -Wno-fatal --top-module tunit_cheats $(RTL)/tunit_cheats.sv tb_cheats.cpp \
		-CFLAGS "-O2 -std=c++17" -o Vtunit_cheats

clean:
	rm -rf obj_dir

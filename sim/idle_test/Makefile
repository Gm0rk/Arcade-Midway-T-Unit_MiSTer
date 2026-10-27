# ROM-loading frames test: rtl/tunit_idle.sv on its own.
#   make && ./obj_dir/Vtunit_idle

RTL = ../../rtl

all: obj_dir/Vtunit_idle

obj_dir/Vtunit_idle: tb_idle.cpp $(RTL)/tunit_idle.sv
	verilator --cc --exe --build -j 2 -O3 --x-assign fast --x-initial fast --noassert \
		-Wall -Wno-fatal --top-module tunit_idle $(RTL)/tunit_idle.sv tb_idle.cpp \
		-CFLAGS "-O2 -std=c++17" -o Vtunit_idle

clean:
	rm -rf obj_dir

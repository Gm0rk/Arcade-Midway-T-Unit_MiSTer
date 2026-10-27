# Move List page test: rtl/tunit_mlpage.sv on its own.
#   make && ./obj_dir/Vtunit_mlpage

RTL = ../../rtl

all: obj_dir/Vtunit_mlpage

obj_dir/Vtunit_mlpage: tb_mlpage.cpp $(RTL)/tunit_mlpage.sv
	verilator --cc --exe --build -j 2 -O3 --x-assign fast --x-initial fast --noassert \
		-Wall -Wno-fatal --top-module tunit_mlpage $(RTL)/tunit_mlpage.sv tb_mlpage.cpp \
		-CFLAGS "-O2 -std=c++17" -o Vtunit_mlpage

clean:
	rm -rf obj_dir

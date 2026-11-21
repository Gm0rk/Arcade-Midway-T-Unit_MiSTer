# DIP switch word test: rtl/tunit_dsw.sv (the OSD options' status bits -> the
# board's 16-bit switch word) against the switches the MRAs carried before
# Build 104 (tools/tunit_dips.py --vectors: every value of every option of
# each of the 9 lists of switches on its own, and 400 random combinations).
#   make && make check

RTL = ../../rtl

all: obj_dir/dsw_tb

obj_dir/dsw_tb: dsw_tb.cpp $(RTL)/tunit_dsw.sv
	verilator --cc --exe --build -j 2 -O2 -Wno-fatal -Wno-WIDTH -Wno-lint --top-module tunit_dsw \
		-I$(RTL) -o dsw_tb $(RTL)/tunit_dsw.sv dsw_tb.cpp

check: obj_dir/dsw_tb
	python3 ../../tools/tunit_dips.py --vectors | ./obj_dir/dsw_tb

clean:
	rm -rf obj_dir

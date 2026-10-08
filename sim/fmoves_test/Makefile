# Finishing-move player test: rtl/tunit_fmoves.sv against the move programs
# and the fight situations of fm_check.py.
#   make && python3 fm_check.py

RTL = ../../rtl

all: obj_dir/fm_tb

obj_dir/fm_tb: fm_tb.cpp $(RTL)/tunit_fmoves.sv $(RTL)/tunit_fmoves_tab.svh
	verilator --cc --exe --build -j 2 -O2 -Wno-fatal -Wno-WIDTH -Wno-lint --top-module tunit_fmoves \
		-I$(RTL) -o fm_tb $(RTL)/tunit_fmoves.sv fm_tb.cpp

clean:
	rm -rf obj_dir

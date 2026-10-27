# Analog CRT stage test: rtl/video/tunit_crt.sv (centred sync, CRT V-Size,
# CRT Adjust) on the T-Unit raster.
#   make && python3 crt_check.py

RTL = ../../rtl

all: obj_dir/crt_tb

obj_dir/crt_tb: tb_crt.sv crt_tb.cpp $(RTL)/video/tunit_crt.sv $(RTL)/video/sync_center.sv \
                $(RTL)/crt_adjust/crt_adjust.sv $(RTL)/crt_adjust/crt_vsize.sv
	verilator --cc --exe --build -j 2 -O3 -Wno-fatal -Wno-WIDTH -Wno-lint --top-module tb_crt \
		-o crt_tb -CFLAGS "-O2" tb_crt.sv $(RTL)/video/tunit_crt.sv $(RTL)/video/sync_center.sv \
		$(RTL)/crt_adjust/crt_adjust.sv $(RTL)/crt_adjust/crt_vsize.sv crt_tb.cpp

clean:
	rm -rf obj_dir out

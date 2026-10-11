# Information window test: rtl/tunit_window.sv on its own against the pages
# and backgrounds of tools/tunit_window.py.
#   make && python3 check.py

RTL = ../../rtl
HEX = $(abspath $(RTL))/tunit_window

all: obj_dir/Vtunit_window

obj_dir/Vtunit_window: tb_window.cpp $(RTL)/tunit_window.sv $(HEX)_row.hex $(HEX)_seg.hex $(HEX)_text.hex \
		$(HEX)_font.hex $(HEX)_bg.hex $(HEX)_pal.hex
	verilator --cc --exe --build -j 2 -O3 --x-assign fast --x-initial fast --noassert \
		-Wno-fatal -Wno-WIDTH -Wno-lint \
		-GROW_HEX='"$(HEX)_row.hex"' -GSEG_HEX='"$(HEX)_seg.hex"' -GTEXT_HEX='"$(HEX)_text.hex"' \
		-GFONT_HEX='"$(HEX)_font.hex"' -GBG_HEX='"$(HEX)_bg.hex"' -GPAL_HEX='"$(HEX)_pal.hex"' \
		--top-module tunit_window $(RTL)/tunit_window.sv tb_window.cpp \
		-CFLAGS "-O2 -std=c++17" -o Vtunit_window

clean:
	rm -rf obj_dir out

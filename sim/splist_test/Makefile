# Secret Player List window test: rtl/tunit_splist.sv on its own against the
# pages and backgrounds of tools/tunit_splist.py.
#   make && python3 check.py

RTL = ../../rtl
HEX = $(abspath $(RTL))/tunit_splist

all: obj_dir/Vtunit_splist

obj_dir/Vtunit_splist: tb_splist.cpp $(RTL)/tunit_splist.sv $(HEX)_row.hex $(HEX)_seg.hex $(HEX)_text.hex \
		$(HEX)_font.hex $(HEX)_bg.hex $(HEX)_pal.hex
	verilator --cc --exe --build -j 2 -O3 --x-assign fast --x-initial fast --noassert \
		-Wno-fatal -Wno-WIDTH -Wno-lint \
		-GROW_HEX='"$(HEX)_row.hex"' -GSEG_HEX='"$(HEX)_seg.hex"' -GTEXT_HEX='"$(HEX)_text.hex"' \
		-GFONT_HEX='"$(HEX)_font.hex"' -GBG_HEX='"$(HEX)_bg.hex"' -GPAL_HEX='"$(HEX)_pal.hex"' \
		--top-module tunit_splist $(RTL)/tunit_splist.sv tb_splist.cpp \
		-CFLAGS "-O2 -std=c++17" -o Vtunit_splist

clean:
	rm -rf obj_dir out

# Blitter reference test: rtl/tunit_dma.sv against MAME's dma_draw (mame_dma.h)
#   make && ./obj_dir/dma_tb 5000 1

all: obj_dir/dma_tb

obj_dir/dma_tb: ../../rtl/tunit_dma.sv dma_tb.cpp mame_dma.h
	verilator --cc --exe --build -j 2 -O3 --x-assign fast --x-initial fast -Wno-fatal -Wno-WIDTH \
		--top-module tunit_dma -o dma_tb -CFLAGS "-O2" ../../rtl/tunit_dma.sv dma_tb.cpp

clean:
	rm -rf obj_dir

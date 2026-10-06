# Full-board Verilator simulation of the T-Unit core
#
#   make            build obj_dir/sim_tunit
#   make run GAME=mk FRAMES=600 SNAP=every:100
#
# ROM streams come from tools/mra_check.py --out (one <set>_rom0.bin and
# <set>_rom3.bin per set); ROMS points at that folder.

ROMS   ?= ../../simroms
GAME   ?= mk
SET    ?= mk
FRAMES ?= 300
SNAP   ?= every:50
OUT    ?= out/$(SET)

RTL = ../rtl
SRC = altsyncram.v \
      $(RTL)/tms34010/tms34010_pkg.sv $(RTL)/tms34010/tms34010_muldiv.sv \
      $(RTL)/tms34010/tms34010_gfx.sv $(RTL)/tms34010/tms34010.sv \
      $(RTL)/tunit_dma.sv $(RTL)/tunit_vram.sv $(RTL)/tunit_video.sv $(RTL)/midway_tunit.sv \
      $(RTL)/sound/williams_adpcm.sv $(RTL)/mc6809/mc6809is.v \
      $(RTL)/dcs/dcs_mem.sv $(RTL)/dcs/adsp2105.sv $(RTL)/sound/tunit_dcs.sv \
      $(wildcard $(RTL)/jt51/*.v) $(filter-out $(RTL)/jt6295/jt12_%,$(wildcard $(RTL)/jt6295/*.v)) \
      $(RTL)/jt6295/jt12_comb.v $(RTL)/jt6295/jt12_interpol.v \
      $(RTL)/sdram.sv sdram_model.sv sim_top.sv

VFLAGS = --cc --exe --build -j 2 -O3 $(THREADS) --x-assign fast --x-initial fast --noassert \
         -Wno-fatal -Wno-WIDTH -Wno-CASEINCOMPLETE -Wno-UNOPTFLAT -Wno-TIMESCALEMOD \
         -Wno-MULTIDRIVEN -Wno-SYNCASYNCNET -Wno-BLKANDNBLK \
         -DSDRAM_SIM -DKI_DCS_SIMULATION -I$(RTL) -I$(RTL)/tms34010 -I$(RTL)/jt51 -I$(RTL)/jt6295 \
         --top-module sim_top -o sim_tunit \
         -CFLAGS "-O2 -march=native" 

MDIR ?= obj_dir

all: $(MDIR)/sim_tunit

$(MDIR)/sim_tunit: $(SRC) sim_main.cpp
	verilator $(VFLAGS) --Mdir $(MDIR) $(SRC) sim_main.cpp

run: $(MDIR)/sim_tunit
	./$(MDIR)/sim_tunit --game $(GAME) --rom0 $(ROMS)/$(SET)_rom0.bin --rom3 $(ROMS)/$(SET)_rom3.bin \
		--frames $(FRAMES) --snap $(SNAP) --out $(OUT) $(ARGS)

clean:
	rm -rf obj_dir

.PHONY: all run clean

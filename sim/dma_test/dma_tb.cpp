//============================================================================
//  Blitter reference test: rtl/tunit_dma.sv against MAME's dma_draw
//
//  dma_tb [blits] [seed]
//
//  Random blits (every bpp, skip compression with pre/post scales, both
//  start/end skip meanings, X/Y scaling, X/Y flip, clipping in both
//  register banks, every drawing mode, offsets on both sides of the
//  0x2000000 relocation) go to the Verilated blitter and to mame_dma.h on
//  the same register writes; after each blit the two frame stores must be
//  equal entry for entry. The harness plays the SDRAM (graphics lines with
//  random latency) and the VRAM controller (row bursts from the blitter's
//  row buffer). Completion times are checked too: INT1 must rise 41 ns per
//  MAME pixel after the start (3.9375 clocks at 96 MHz), or when the
//  drawing ends if that is later.
//
//  Copyright (C) 2026 Gm0rk - GPL-3.0-or-later
//============================================================================

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cstdint>
#include <vector>
#include <random>

#include "Vtunit_dma.h"
#include "verilated.h"
#include "mame_dma.h"

static Vtunit_dma *dut;
static std::vector<uint8_t> gfx(16 << 20);
static std::vector<uint16_t> vram_rtl(0x80000 + 1024), vram_ref(0x80000 + 1024);
static std::mt19937 rng;
static uint64_t cyc = 0;

// graphics line requests: respond after a random latency
static int gfx_wait = -1;

// row write-back emulation
static bool blt_busy = false;
static int blt_i, blt_n, blt_row, blt_lo;

static int verbose_blit = -1, cur_blit = -1;

static void tick() {
	// --- inputs that depend on outputs before the edge ---
	int raddr_beat = -1;
	if (!blt_busy && dut->blt_req != dut->blt_ack) {
		blt_busy = true;
		blt_row = dut->blt_row;
		blt_lo = dut->blt_lo;
		blt_n = dut->blt_hi - dut->blt_lo + 1;
		blt_i = 0;
		if (cur_blit == verbose_blit)
			printf("    flush row %d beats %d-%d\n", blt_row, blt_lo, dut->blt_hi);
	}
	if (blt_busy && blt_i < blt_n) {
		raddr_beat = blt_lo + blt_i;
		dut->blt_raddr = (uint8_t)raddr_beat;
	}

	dut->clk = 1;
	dut->eval();
	cyc++;

	// --- after the edge ---
	// the row buffer output now holds the beat addressed before the edge
	if (raddr_beat >= 0) {
		uint64_t q = dut->blt_q;
		uint8_t be = dut->blt_be;
		uint32_t base = blt_row * 512 + (raddr_beat & 0xFF) * 4;
		for (int lane = 0; lane < 4; lane++)
			if ((be >> (2 * lane)) & 3)
				vram_rtl[(base + lane) & 0x7FFFF] = (uint16_t)(q >> (16 * lane));
		blt_i++;
	}
	if (blt_busy && blt_i == blt_n) {
		blt_busy = false;
		dut->blt_ack = dut->blt_req;
	}

	// graphics lines
	if (gfx_wait < 0 && dut->gfx_req != dut->gfx_ack)
		gfx_wait = 3 + rng() % 20;
	else if (gfx_wait > 0)
		gfx_wait--;
	else if (gfx_wait == 0) {
		uint64_t line = dut->gfx_line;
		uint64_t d = 0;
		for (int b = 0; b < 8; b++)
			d |= (uint64_t)gfx[(line * 8 + b) % gfx.size()] << (8 * b);
		dut->gfx_data = d;
		dut->gfx_ack = dut->gfx_req;
		gfx_wait = -1;
	}

	dut->clk = 0;
	dut->eval();
	dut->reg_wr = 0;
}

static void reg_write(int idx, uint16_t v) {
	dut->reg_idx = idx;
	dut->reg_wdata = v;
	dut->reg_wr = 1;
	// the board keeps offering a start while the blitter is still drawing
	dut->eval();
	while (dut->reg_wr_wait) {
		tick();
		dut->reg_idx = idx; dut->reg_wdata = v; dut->reg_wr = 1;
		dut->eval();
	}
	tick();
}

int main(int argc, char **argv) {
	int blits = argc > 1 ? atoi(argv[1]) : 2000;
	int seed = argc > 2 ? atoi(argv[2]) : 1;
	rng.seed(seed);

	// graphics: random bytes with zero runs, so zero pixels are common
	for (size_t i = 0; i < (4u << 20); i++) {
		uint32_t r = rng();
		gfx[i] = (r & 0x300) == 0 ? 0 : (uint8_t)r;
	}

	MameDma ref;
	ref.gfxrom = gfx.data();
	ref.vram = vram_ref.data();

	dut = new Vtunit_dma;
	dut->big_rom = 0;
	dut->reset = 1;
	dut->clk = 0;
	dut->eval();
	for (int i = 0; i < 10; i++) tick();
	dut->reset = 0;
	tick();

	if (getenv("DMA_BLIT")) verbose_blit = atoi(getenv("DMA_BLIT"));
	int fails = 0, timing_fails = 0, late = 0;
	double worst = 0;
	uint64_t pix_total = 0, clk_total = 0;
	for (int t = 0; t < blits; t++) {
		cur_blit = t;
		// ---- random register set ----
		uint16_t r[18];
		bool big = (rng() % 8) == 0;
		ref.gfx_rom_large = big;
		dut->big_rom = big;

		int bpp = rng() % 8;                     // 0 = 8 bits
		int mode = rng() % 16;
		uint16_t cmd = 0x8000 | (bpp << 12) | mode;
		if (rng() % 2) cmd |= 0x10;              // X flip
		if (rng() % 4 == 0) cmd |= 0x20;         // Y flip
		if (rng() % 2) cmd |= 0x40;              // MK start/end skip meaning
		if (rng() % 2) cmd |= 0x80;              // skip compression
		cmd |= (rng() % 4) << 8;                 // pre-skip scale
		cmd |= (rng() % 4) << 10;                // post-skip scale

		int w = 1 + rng() % ((rng() % 8) ? 64 : 300);
		int h = 1 + rng() % ((rng() % 8) ? 48 : 200);
		r[0]  = (rng() % 3 == 0) ? 0 : (cmd & 0x40) ? ((rng() % 16) << 8 | (rng() % 16)) : (rng() % 3 ? rng() % 40 : rng() & 0xFFFF);
		r[4]  = rng() % 4 ? rng() % 512 : rng() & 0xFFFF;
		r[5]  = rng() % 4 ? rng() % 512 : rng() & 0xFFFF;
		r[6]  = w;
		r[7]  = h;
		uint32_t off = (rng() % (3u << 23));     // bit offset inside the 3 MB of data
		if (!big && rng() % 2) off += 0x2000000; // as games pass ROM addresses
		if (rng() % 32 == 0) off = 0xF8000000u + (rng() % (1u << 20));
		if (rng() % 64 == 0) off = 0x30000000u;  // out of range: no draw
		r[2]  = off & 0xFFFF;
		r[3]  = off >> 16;
		r[8]  = rng() & 0xFFFF;
		r[9]  = rng() & 0xFFFF;
		r[10] = rng() % 3 ? 0 : (rng() % 2 ? 0x100 : 0x40 + rng() % 0x3C0);
		r[11] = rng() % 3 ? 0 : (rng() % 2 ? 0x100 : 0x40 + rng() % 0x3C0);
		bool fullclip = rng() % 3 == 0;
		r[12] = fullclip ? 0 : rng() % 300;      // top
		r[13] = fullclip ? 511 : r[12] + rng() % 300;
		r[16] = fullclip ? 0 : rng() % 400;      // left
		r[17] = fullclip ? (rng() % 4 ? 511 : 1023) : r[16] + rng() % 500;
		r[14] = 0;
		r[15] = rng() & 0xFFDF;                  // config, bank bit set below

		// ---- write them (bank 0 for left/right, bank 1 for top/bottom) ----
		auto both = [&](int idx, uint16_t v) { ref.write(idx, v); reg_write(idx, v); };
		both(15, r[15] & ~0x20);
		both(12, r[16]); both(13, r[17]);
		both(15, r[15] | 0x20);
		both(12, r[12]); both(13, r[13]);
		both(15, (rng() % 2) ? (r[15] | 0x20) : (r[15] & ~0x20));
		int order[] = {0, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 14};
		for (int i : order) both(i, r[i]);

		// ---- start ----
		ref.write(1, cmd);
		reg_write(1, cmd);
		uint64_t start = cyc;

		// wait for INT1 (drawing done and the completion time passed)
		uint64_t limit = start + 200000000ull;
		while (!dut->irq && cyc < limit) tick();
		uint64_t took = cyc - start;
		if (cyc >= limit) {
			printf("blit %d: no completion\n", t);
			return 1;
		}
		// the completion may not come earlier than MAME's time
		uint64_t mame_t = ((uint64_t)ref.pixels * 63) >> 4;
		if (took + 4 < mame_t) {
			if (timing_fails++ < 10)
				printf("blit %d: completion after %llu clk, MAME %llu\n", t,
				       (unsigned long long)took, (unsigned long long)mame_t);
		}

		// drawing slower than MAME's completion time (statistics only)
		if (mame_t > 100) {
			double ratio = (double)took / mame_t;
			if (ratio > 1.05) late++;
			if (ratio > worst) worst = ratio;
			pix_total += ref.pixels;
			clk_total += took;
		}

		// ---- compare the frame stores ----
		if (memcmp(vram_rtl.data(), vram_ref.data(), 0x80000 * 2)) {
			int n = 0, first = -1;
			for (int i = 0; i < 0x80000; i++)
				if (vram_rtl[i] != vram_ref[i]) { if (first < 0) first = i; n++; }
			printf("blit %d: %d entries differ, first at row %d col %d (rtl %04X mame %04X)\n",
			       t, n, first / 512, first % 512, vram_rtl[first], vram_ref[first]);
			if (getenv("DMA_VERBOSE")) {
				int shown = 0;
				for (int i = 0; i < 0x80000 && shown < 40; i++)
					if (vram_rtl[i] != vram_ref[i]) {
						printf("    row %3d col %3d  rtl %04X  mame %04X\n", i / 512, i % 512, vram_rtl[i], vram_ref[i]);
						shown++;
					}
			}
			printf("  cmd %04X lrskip %04X off %08X x %d y %d w %d h %d pal %04X col %04X sx %04X sy %04X clip t%d b%d l%d r%d big %d\n",
			       cmd, r[0], off, r[4], r[5], w, h, r[8], r[9], r[10], r[11], r[12], r[13], r[16], r[17], big);
			if (t == verbose_blit) {
				int row = first / 512;
				for (int c = (first % 512) - 4; c < (first % 512) + 28; c++)
					printf("    %3d: rtl %04X mame %04X\n", c, vram_rtl[row * 512 + c], vram_ref[row * 512 + c]);
			}
			// resynchronise and carry on
			memcpy(vram_rtl.data(), vram_ref.data(), 0x80000 * 2);
			if (++fails >= 20) break;
		}
	}
	printf("%d blits, %d frame store mismatches, %d early completions\n", blits, fails, timing_fails);
	printf("%d blits finished more than 5%% after MAME's time (worst x%.2f); %.2f clk per MAME pixel overall\n",
	       late, worst, pix_total ? (double)clk_total / pix_total : 0.0);
	delete dut;
	return fails || timing_fails;
}

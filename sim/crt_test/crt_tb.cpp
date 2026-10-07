// crt_tb.cpp — runs tb_crt.sv (the analog CRT stage on the T-Unit raster)
//
// Copyright (C) 2026 Gm0rk. Distributed under GNU GPL v3 or later.
//
// usage: crt_tb out.bin frames rec_frames crt_en autow hsize hpos vshift vsize vsmode
//   (OSD values as the status bits hold them: hsize 0-31, hpos 0-96,
//   vshift 0-31, vsize 0-14, vsmode 0 PVM / 1 Cabinet)
// Writes one 12-byte record per output dot (CE_PIXEL) of the last rec_frames
// frames: clock (u64), R, G, B, flags (bit 0 HSync, 1 VSync, 2 DE, 3 CRT
// Adjust on). crt_check.py reads them.
#include "Vtb_crt.h"
#include "verilated.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cstdint>

int main(int argc, char **argv) {
	Verilated::commandArgs(argc, argv);
	if (argc < 11) {
		fprintf(stderr, "usage: %s out.bin frames rec_frames crt_en autow hsize hpos vshift vsize vsmode\n", argv[0]);
		return 1;
	}
	Vtb_crt *t = new Vtb_crt;
	FILE *f = fopen(argv[1], "wb");
	if (!f) { perror(argv[1]); return 1; }
	int frames = atoi(argv[2]), rec = atoi(argv[3]);
	t->crt_en     = atoi(argv[4]);
	t->autow      = atoi(argv[5]);
	t->hsize_osd  = atoi(argv[6]) & 31;
	t->hpos_osd   = atoi(argv[7]) & 127;
	t->vshift_osd = atoi(argv[8]) & 31;
	t->vsize_osd  = atoi(argv[9]) & 15;
	t->vsmode_osd = atoi(argv[10]) & 1;
	const uint64_t FR = 506ull * 289 * 12;      // clocks per board frame
	uint64_t total = FR * frames, start = FR * (frames - rec);
	for (uint64_t c = 0; c < total; c++) {
		t->clk = 0; t->eval();
		t->clk = 1; t->eval();
		if (c >= start && t->ce_out) {
			uint8_t r[12];
			memcpy(r, &c, 8);
			r[8] = t->r; r[9] = t->g; r[10] = t->b;
			r[11] = t->hs | (t->vs << 1) | (t->de << 2) | (t->crt_on << 3);
			fwrite(r, 12, 1, f);
		}
	}
	fclose(f);
	delete t;
	return 0;
}

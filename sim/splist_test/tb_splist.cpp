// ============================================================================
//  tb_splist.cpp - the Secret Player List window (rtl/tunit_splist.sv) alone
//
//  Feeds the window the T-Unit raster as NBA Jam programs it (506 dots a
//  line, 289 lines, the picture dots 100-499 of lines 20-273) on a 96 MHz
//  clock with the 8 MHz dot enable, the board's outputs changing with each
//  ce_pix as tunit_video.sv's do, and a test picture (R = x, G = y, B =
//  0x80). It writes the third frame's picture as it goes out (the dot before
//  each ce_pix) to a PPM file, which check.py compares with the page and the
//  background as tools/tunit_splist.py has them.
//
//  Usage: Vtunit_splist PAGE GAME OUT.ppm [-off]
//    -off   the window off: the picture must come out unchanged
//
//  Copyright (C) 2026 Gm0rk - GPL-3.0-or-later
// ============================================================================

#include "Vtunit_splist.h"
#include "verilated.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>

static const int HT = 506, H0 = 100, H1 = 500, VT = 289, V0 = 20, V1 = 274;
static const int W = H1 - H0, H = V1 - V0;

int main(int argc, char **argv)
{
	if (argc < 4) {
		fprintf(stderr, "usage: %s PAGE GAME OUT.ppm [-off]\n", argv[0]);
		return 2;
	}
	bool off = argc > 4 && !strcmp(argv[4], "-off");

	Verilated::commandArgs(argc, argv);
	Vtunit_splist *m = new Vtunit_splist;
	m->enable = off ? 0 : 1;
	m->page = atoi(argv[1]);
	m->game = atoi(argv[2]);

	std::vector<unsigned char> img(W * H * 3);
	int bad = 0;
	int dot = 0, line = 0, frame = 0;
	auto drive = [&]() {
		bool hb = dot < H0 || dot >= H1, vb = line < V0 || line >= V1;
		m->hb_in = hb;
		m->vb_in = vb;
		bool pic = !hb && !vb;
		m->r_in = pic ? (dot - H0) & 0xFF : 0;
		m->g_in = pic ? (line - V0) & 0xFF : 0;
		m->b_in = pic ? 0x80 : 0;
	};
	drive();
	m->clk = 0;
	m->ce_pix = 0;
	m->eval();
	for (long t = 0; frame < 3; t++) {
		bool ce = (t % 12) == 11;
		if (ce && frame == 2 && line >= V0 && line < V1 && dot >= H0 && dot < H1) {
			// the dot that ends, as it goes out
			int i = ((line - V0) * W + dot - H0) * 3;
			img[i] = m->r_out;
			img[i + 1] = m->g_out;
			img[i + 2] = m->b_out;
			if (off && (m->r_out != m->r_in || m->g_out != m->g_in || m->b_out != m->b_in))
				bad++;
		}
		m->ce_pix = ce;
		m->clk = 1;
		m->eval();
		if (ce) {
			// the board's outputs move on to the next dot
			if (++dot == HT) {
				dot = 0;
				if (++line == VT) {
					line = 0;
					frame++;
				}
			}
			drive();
			m->eval();
		}
		m->clk = 0;
		m->eval();
	}
	FILE *f = fopen(argv[3], "wb");
	fprintf(f, "P6\n%d %d\n255\n", W, H);
	fwrite(img.data(), 1, img.size(), f);
	fclose(f);
	if (off)
		printf("window off: %s (%d dots changed)\n", bad ? "FAIL" : "OK", bad);
	delete m;
	return off && bad ? 1 : 0;
}

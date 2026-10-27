// ============================================================================
//  tb_idle.cpp - test bench for rtl/tunit_idle.sv, the frames the core sends
//  while a ROM set loads
//
//  The frame is the board's raster (506 dots x 289 lines, HSync dots 0-35,
//  VSync lines 0-2, picture lines 20-273): with the 57 Hz Video Timing the
//  34010 drops 12 blank lines after VSBLNK, so line 274 is followed by 287
//  and the frame is 277 lines (the model of sim/crt_test/tb_crt.sv). Checks:
//  the line and frame lengths for both timings, where the sync and the
//  picture lines are, a switch of the option at any point of a frame, and a
//  run of random switches (a frame is 277 or 289 lines, never anything
//  else).
//
//  Usage: Vtunit_idle    (exit code 0: all checks passed)
//
//  Copyright (C) 2026 Gm0rk - GPL-3.0-or-later
// ============================================================================

#include "Vtunit_idle.h"
#include "verilated.h"
#include <cstdio>
#include <cstdlib>
#include <vector>

static Vtunit_idle *m;
static int bad = 0, checks = 0;

struct Line { int vs, vb; int dots; };
static std::vector<Line> lines;
static int dots = 0, hs_d = 0;

// one dot (the dot enable is held high: every clock is a dot)
static void dot()
{
	m->clk = 0; m->eval();
	m->clk = 1; m->eval();
	if (m->hs && !hs_d) {                 // a line starts
		if (!lines.empty()) lines.back().dots = dots;
		lines.push_back({m->vs, m->vb, 0});
		dots = 0;
	}
	hs_d = m->hs;
	dots++;
}

static void run_lines(int n)
{
	for (int k = 0; k < n * 506; k++) dot();
}

static void ok(bool c, const char *what, int a = 0, int b = 0)
{
	checks++;
	if (!c) { printf("FAIL %s (%d, %d)\n", what, a, b); bad++; }
}

struct Frame { int start, len, vs, vb, pic, pic0; };

// the frames that are complete in lines[from..]: from one VSync start to the next
static std::vector<Frame> frames(size_t from)
{
	std::vector<Frame> f;
	std::vector<size_t> st;
	for (size_t i = from + 1; i < lines.size(); i++)
		if (lines[i].vs && !lines[i - 1].vs) st.push_back(i);
	for (size_t k = 0; k + 1 < st.size(); k++) {
		Frame r = {(int)st[k], (int)(st[k + 1] - st[k]), 0, 0, 0, -1};
		for (size_t i = st[k]; i < st[k + 1]; i++) {
			r.vs += lines[i].vs;
			r.vb += lines[i].vb;
			if (!lines[i].vb) { r.pic++; if (r.pic0 < 0) r.pic0 = (int)(i - st[k]); }
		}
		f.push_back(r);
	}
	return f;
}

static void check_frames(const char *what, size_t from, int want_len, int want_vb, int min_frames)
{
	auto f = frames(from);
	ok((int)f.size() >= min_frames, what, (int)f.size(), min_frames);
	for (auto &r : f) {
		ok(r.len == want_len, "frame length", r.len, want_len);
		ok(r.vs == 3, "VSync lines", r.vs, 3);
		ok(r.vb == want_vb, "blank lines", r.vb, want_vb);
		ok(r.pic == 254, "picture lines", r.pic, 254);
		ok(r.pic0 == 20, "first picture line", r.pic0, 20);
	}
}

int main(int argc, char **argv)
{
	Verilated::commandArgs(argc, argv);
	m = new Vtunit_idle;
	m->ce_pix = 1;
	m->vt57 = 0;
	m->eval();

	// native: 289 lines, 35 blank
	run_lines(289 * 4 + 10);
	for (size_t i = 1; i + 1 < lines.size(); i++)
		if (lines[i].dots != 506) { ok(false, "native line length", lines[i].dots, 506); break; }
	check_frames("native: frames seen", 0, 289, 35, 3);

	// switch to 57 Hz in the middle of the picture: the frame in progress is
	// short already (VSBLNK not reached), the next ones are too
	size_t mark = lines.size();
	m->vt57 = 1;
	run_lines(277 * 4 + 10);
	for (size_t i = mark + 1; i + 1 < lines.size(); i++)
		if (lines[i].dots != 506) { ok(false, "57 Hz line length", lines[i].dots, 506); break; }
	check_frames("57 Hz: frames seen", mark, 277, 23, 3);

	// the dropped lines: 274 is the last line before 287 and 288 (blank, no sync)
	{
		auto f = frames(mark);
		bool fine = !f.empty();
		if (fine) {
			int s = f[0].start;
			// lines 274, 287 and 288 are the last three of the frame: blank, no sync
			for (int k = 1; k <= 3; k++)
				fine = fine && lines[s + f[0].len - k].vb && !lines[s + f[0].len - k].vs;
		}
		ok(fine, "57 Hz: the frame ends with three blank lines");
	}

	// back to 54.7 Hz
	mark = lines.size();
	m->vt57 = 0;
	run_lines(289 * 4 + 10);
	check_frames("back to native: frames seen", mark, 289, 35, 3);

	// the option changed at every point of a frame, both ways: the frame
	// that follows the one in progress is the new length
	for (int at = 0; at < 289; at += 7) {
		for (int to = 0; to < 2; to++) {
			m->vt57 = !to;                        // the other timing first
			run_lines(289 * 3);
			size_t before = lines.size();
			// run to line `at` of a frame: after the next VSync start
			while (!(lines.size() > before + 1 && lines.back().vs && !lines[lines.size() - 2].vs)) dot();
			run_lines(at);
			m->vt57 = to;
			size_t from = lines.size();
			run_lines(289 * 3 + 10);
			auto f = frames(from);
			bool good = f.size() >= 2;
			// the frames after the one the switch fell in
			for (size_t i = 1; i < f.size(); i++)
				good = good && f[i].len == (to ? 277 : 289);
			ok(good, "option switched mid-frame: next frames", at, to);
		}
	}

	// random switches: a frame is 277 or 289 lines, always
	srand(12345);
	m->vt57 = 0;
	lines.clear(); dots = 0; hs_d = 0;
	for (int n = 0; n < 200 * 289 * 506; n++) {      // about 200 frames, a switch every 1 or 2
		if (rand() % 200000 == 0) m->vt57 = !m->vt57;
		dot();
	}
	{
		auto f = frames(0);
		int n277 = 0, n289 = 0, other = 0;
		for (auto &r : f) {
			if (r.len == 277) n277++; else if (r.len == 289) n289++; else other++;
			ok(r.vs == 3 && r.pic == 254, "random: sync and picture lines", r.vs, r.pic);
		}
		ok(other == 0, "random: frames of any other length", other);
		ok(n277 > 0 && n289 > 0, "random: both lengths seen", n277, n289);
		printf("(random switching: %d frames of 277 lines, %d of 289)\n", n277, n289);
	}

	m->final();
	delete m;
	printf("%d checks, %d failed\n", checks, bad);
	return bad ? 1 : 0;
}

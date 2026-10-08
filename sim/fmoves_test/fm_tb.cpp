// fm_tb.cpp - drives rtl/tunit_fmoves.sv from a script on stdin
//
//   g <mk> <mk2>        loaded game
//   s                   ROM index 1 download starts
//   c <word> <hex>      ROM index 1 word 0x200 + word
//   w <hex addr> <hex>  CPU write (word address)
//   p <line> <slot>     OSD pick
//   f <n>               n running frames
// Prints "F <frame> <drive> <keys hex>" for each frame and "M <frame> <msg>"
// for each message.
//
// Copyright (C) 2026 Gm0rk - GPL-3.0-or-later

#include "Vtunit_fmoves.h"
#include "verilated.h"
#include <cstdio>
#include <cstring>

static Vtunit_fmoves *m;
static long frame_no;

static void tick()
{
	m->clk = 0; m->eval();
	m->clk = 1; m->eval();
	if (m->msg_req) printf("M %ld %d\n", frame_no, m->msg);
	m->dl_start = 0; m->dl_wr = 0; m->cpu_wr = 0; m->sel = 0; m->frame = 0;
}

int main(int argc, char **argv)
{
	Verilated::commandArgs(argc, argv);
	m = new Vtunit_fmoves;
	m->reset = 1;
	for (int i = 0; i < 4; i++) tick();
	m->reset = 0;
	char cmd[16];
	while (scanf("%15s", cmd) == 1) {
		if (!strcmp(cmd, "g")) { int a, b; scanf("%d %d", &a, &b); m->game_mk = a; m->game_mk2 = b; tick(); }
		else if (!strcmp(cmd, "s")) { m->dl_start = 1; tick(); }
		else if (!strcmp(cmd, "c")) { unsigned a, v; scanf("%u %x", &a, &v); m->dl_wr = 1; m->dl_addr = a; m->dl_data = v; tick(); }
		else if (!strcmp(cmd, "w")) { unsigned a, v; scanf("%x %x", &a, &v); m->cpu_wr = 1; m->cpu_wa = a; m->cpu_wd = v; tick(); tick(); }
		else if (!strcmp(cmd, "p")) { unsigned l, s; scanf("%u %u", &l, &s); m->sel = 1; m->sel_line = l; m->sel_slot = s; tick(); for (int i = 0; i < 4; i++) tick(); }
		else if (!strcmp(cmd, "f")) {
			int n; scanf("%d", &n);
			for (int k = 0; k < n; k++) {
				for (int i = 0; i < 6; i++) tick();
				m->frame = 1; tick();
				for (int i = 0; i < 3; i++) tick();
				printf("F %ld %d %03x\n", frame_no, m->drive, m->keys);
				frame_no++;
			}
		}
	}
	delete m;
	return 0;
}

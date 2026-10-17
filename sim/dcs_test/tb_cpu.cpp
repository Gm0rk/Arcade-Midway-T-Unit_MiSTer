// tb_cpu.cpp - ADSP-2105 core (rtl/dcs/adsp2105.sv) in lockstep with MAME's
//
// Runs the RTL CPU (Verilator) and MAME's own ADSP-21xx code (adsp_ref.h,
// made by mkref.py) side by side on random programs, random data, random
// interrupt events, random TX1 arming, random memory and start delays and
// random I register writes through the board's side port (the CPU held at a
// boundary, or in reset; MAME: set_state_int, update_i), and compares every
// architectural register, every stack and every memory write after each
// instruction. Any difference stops the run with both states printed.
//
//   ./tb_cpu [programs] [instructions per program] [seed]
//
// Copyright (C) 2026 Gm0rk - GPL-3.0-or-later

#include "Vadsp2105.h"
#include "Vadsp2105___024root.h"
#include "verilated.h"
#include "adsp_ref.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <random>
#include <string>

static Vadsp2105 *top;
static std::mt19937_64 rng;
static uint32_t rnd(uint32_t n) { return (uint32_t)(rng() % n); }

// bit field of a Verilator signal
template <std::size_t N> static uint32_t fld(const VlWide<N> &w, int lo, int width)
{
	uint64_t v = 0;
	for (int b = 0; b < width; b++)
		if ((w[(lo + b) >> 5] >> ((lo + b) & 31)) & 1) v |= (uint64_t)1 << b;
	return (uint32_t)v;
}
template <typename T, typename std::enable_if<std::is_integral<T>::value, int>::type = 0>
static uint32_t fld(T w, int lo, int width) { return (uint32_t)(((uint64_t)w >> lo) & ((width >= 32) ? 0xffffffffull : ((1ull << width) - 1))); }

#define R(x) (top->rootp->adsp2105__DOT__##x)

static uint32_t pm_r[16384], pm_m[16384];
static uint16_t dm_r[16384], dm_m[16384];

// a random instruction word, weighted towards the classes the DCS code uses
static uint32_t rand_op()
{
	uint32_t w = rnd(0x1000000);
	uint32_t k = rnd(100);
	uint32_t hi;
	if (k < 4)       hi = rnd(0x10);                 // control 0x00-0x0F
	else if (k < 12) hi = 0x0d;                      // register moves
	else if (k < 16) hi = 0x0c;                      // mode control
	else if (k < 22) hi = 0x0e + rnd(6);             // shifts
	else if (k < 25) hi = 0x14 + rnd(4);             // DO UNTIL
	else if (k < 30) hi = 0x18 + rnd(8);             // jumps / calls
	else if (k < 42) hi = 0x20 + rnd(0x10);          // ALU/MAC (+ move)
	else if (k < 52) hi = 0x30 + rnd(0x10);          // immediate loads
	else if (k < 60) hi = 0x40 + rnd(0x10);
	else if (k < 72) hi = 0x50 + rnd(0x30);          // ALU/MAC + memory
	else if (k < 82) hi = 0x80 + rnd(0x20);          // DM(immediate)
	else if (k < 88) hi = 0xa0 + rnd(0x20);
	else             hi = 0xc0 + rnd(0x40);          // dual reads
	w = (hi << 16) | (w & 0xffff);
	// keep DO UNTIL loop ends and counters small enough to finish
	if (hi >= 0x14 && hi <= 0x17 && rnd(4)) {
		uint32_t a = (w >> 4) & 0x3fff;
		(void)a;
	}
	if (hi == 0x02 && (w & 0x8000) && rnd(8)) w &= ~0x8000u;    // IDLE now and then
	return w & 0xffffff;
}

static int fails = 0;
static void fail(const char *what, uint32_t rtl, uint32_t ref, uint64_t n)
{
	printf("MISMATCH after instruction %llu: %s RTL %X MAME %X\n", (unsigned long long)n, what, rtl, ref);
	fails++;
}

static adsp21xx_device *ref;
static uint16_t pre_si, pre_sb, pre_se, pre_astat;

static void tick()
{
	top->clk = 0; top->eval();
	top->clk = 1; top->eval();
}

// compare all state; returns false on a mismatch
static bool compare(uint64_t n)
{
	int f0 = fails;
	adsp21xx_device &m = *ref;
	int bank = m.m_mstat & 1;
	auto core_cmp = [&](const adsp21xx_device::adsp_core &cr, int rb, const char *nm) {
		const auto &rf = rb ? R(rf1) : R(rf0);
		uint16_t v[19] = { cr.ax0.u, cr.ax1.u, cr.mx0.u, cr.mx1.u, cr.ay0.u, cr.ay1.u, cr.my0.u, cr.my1.u,
		                   cr.si.u, cr.se.u, cr.ar.u, cr.mr.mrx.mr0.u, cr.mr.mrx.mr1.u, cr.mr.mrx.mr2.u,
		                   cr.sr.srx.sr0.u, cr.sr.srx.sr1.u, cr.af.u, cr.mf.u, cr.sb.u };
		static const char *names[19] = { "AX0","AX1","MX0","MX1","AY0","AY1","MY0","MY1","SI","SE","AR",
		                                  "MR0","MR1","MR2","SR0","SR1","AF","MF","SB" };
		for (int k = 0; k < 19; k++) {
			uint32_t r = fld(rf, k * 16, 16);
			if (r != v[k]) { std::string s = std::string(nm) + names[k]; fail(s.c_str(), r, v[k], n); }
		}
	};
	core_cmp(m.m_core, bank, "");
	core_cmp(m.m_alt, bank ^ 1, "alt ");
	for (int k = 0; k < 8; k++) {
		if (fld(R(ir), k * 15, 15) != m.m_i[k])            fail(("I" + std::to_string(k)).c_str(), fld(R(ir), k * 15, 15), m.m_i[k], n);
		if (fld(R(mr), k * 14, 14) != ((uint32_t)m.m_m[k] & 0x3fff)) fail(("M" + std::to_string(k)).c_str(), fld(R(mr), k * 14, 14), m.m_m[k] & 0x3fff, n);
		if (fld(R(lr), k * 14, 14) != m.m_l[k])            fail(("L" + std::to_string(k)).c_str(), fld(R(lr), k * 14, 14), m.m_l[k], n);
		if (fld(R(lmr), k * 14, 14) != m.m_lmask[k])       fail(("LMASK" + std::to_string(k)).c_str(), fld(R(lmr), k * 14, 14), m.m_lmask[k], n);
		if (fld(R(br), k * 14, 14) != m.m_base[k])         fail(("BASE" + std::to_string(k)).c_str(), fld(R(br), k * 14, 14), m.m_base[k], n);
	}
	if (R(px) != m.m_px)                     fail("PX", R(px), m.m_px, n);
	if (R(pc) != (m.m_pc & 0x3fff))          fail("PC", R(pc), m.m_pc, n);
	uint32_t lp = R(loop_v) ? R(loop_a) : 0xffff;
	uint32_t ml = (m.m_loop == 0xffff) ? 0xffff : (m.m_loop & 0x3fff);
	if (lp != ml)                            fail("LOOP", lp, m.m_loop, n);
	if (R(loop_c) != m.m_loop_condition)     fail("LOOPCOND", R(loop_c), m.m_loop_condition, n);
	if (R(cntr) != (m.m_cntr & 0x3fff))      fail("CNTR", R(cntr), m.m_cntr, n);
	if (R(astat) != m.m_astat)               fail("ASTAT", R(astat), m.m_astat, n);
	if (R(sstat) != m.m_sstat)               fail("SSTAT", R(sstat), m.m_sstat, n);
	if (R(mstat) != m.m_mstat)               fail("MSTAT", R(mstat), m.m_mstat, n);
	if (R(idle_r) != m.m_idle)               fail("IDLE", R(idle_r), m.m_idle, n);
	if (R(imask) != m.m_imask)               fail("IMASK", R(imask), m.m_imask, n);
	if (R(icntl) != m.m_icntl)               fail("ICNTL", R(icntl), m.m_icntl, n);
	if ((int)R(psp) != m.m_pc_sp)            fail("PCSP", R(psp), m.m_pc_sp, n);
	for (int k = 0; k < m.m_pc_sp && k < 16; k++)
		if (fld(R(pcs), k * 14, 14) != (m.m_pc_stack[k] & 0x3fff)) fail(("PCSTK" + std::to_string(k)).c_str(), fld(R(pcs), k * 14, 14), m.m_pc_stack[k], n);
	if ((int)R(csp) != m.m_cntr_sp)          fail("CNTRSP", R(csp), m.m_cntr_sp, n);
	for (int k = 0; k < m.m_cntr_sp && k < 4; k++)
		if (fld(R(cs), k * 14, 14) != (m.m_cntr_stack[k] & 0x3fff)) fail("CNTRSTK", fld(R(cs), k * 14, 14), m.m_cntr_stack[k], n);
	if ((int)R(ssp) != m.m_stat_sp)          fail("STATSP", R(ssp), m.m_stat_sp, n);
	for (int k = 0; k < m.m_stat_sp && k < 4; k++) {
		uint32_t e = fld(R(ss), k * 21, 21);
		uint32_t me = ((m.m_stat_stack[k][0] & 0x7f) << 14) | ((m.m_stat_stack[k][1] & 0x3f) << 8) | (m.m_stat_stack[k][2] & 0xff);
		if (e != me) fail("STATSTK", e, me, n);
	}
	if ((int)R(lsp) != m.m_loop_sp)          fail("LOOPSP", R(lsp), m.m_loop_sp, n);
	for (int k = 0; k < m.m_loop_sp && k < 4; k++)
		if (fld(R(ls), k * 18, 18) != (m.m_loop_stack[k] & 0x3ffff)) fail("LOOPSTK", fld(R(ls), k * 18, 18), m.m_loop_stack[k], n);
	for (int k = 0; k < 3; k++)
		if (fld(R(irq_st), k, 1) != m.m_irq_state[k]) fail(("IRQSTATE" + std::to_string(k)).c_str(), fld(R(irq_st), k, 1), m.m_irq_state[k], n);
	for (int k = 0; k < 6; k++)
		if (fld(R(irq_lt), k, 1) != m.m_irq_latch[k]) fail(("IRQLATCH" + std::to_string(k)).c_str(), fld(R(irq_lt), k, 1), m.m_irq_latch[k], n);
	return fails == f0;
}

int main(int argc, char **argv)
{
	Verilated::commandArgs(argc, argv);
	int programs = (argc > 1) ? atoi(argv[1]) : 200;
	int per      = (argc > 2) ? atoi(argv[2]) : 20000;
	uint64_t seed = (argc > 3) ? strtoull(argv[3], 0, 0) : 1;
	rng.seed(seed);

	top = new Vadsp2105;
	ref = new adsp21xx_device;
	ref->pm = pm_m; ref->dm = dm_m;

	uint64_t total = 0, irqs = 0, waits = 0, idles = 0, tx1s = 0, sides = 0;
	int hold_st = 0;
	bool ce = false;
	top->clk = 0; top->ce = 0; top->reset = 1; top->go = 1; top->hold_req = 0;
	top->sp_we = 0; top->tx1_arm = 0; top->tx1_ireg = 0;
	top->irq_set = 0; top->irq_clr = 0; top->irq1_pulse = 0; top->timer_pulse = 0;
	top->dm_rdy = 1; top->pm_q = 0; top->dm_q = 0;

	uint32_t pm_q = 0; uint16_t dm_q = 0;
	int rtl_timer_edges = 0; int last_ten = 0; int rtl_tx1 = 0;

	for (int p = 0; p < programs && !fails; p++) {
		// new random program and data in both memories
		for (int a = 0; a < 16384; a++) { pm_r[a] = pm_m[a] = rand_op(); dm_r[a] = dm_m[a] = (uint16_t)rng(); }
		// the last words jump back to 0: a PC past 0x3FFF wraps at 14 bits in
		// the RTL (the chip's width) where MAME's keeps counting
		for (int a = 0x3FF0; a < 0x4000; a++) pm_r[a] = pm_m[a] = 0x18000F;
		// reset both (registers keep their values, as device_reset); now and
		// then the board's side port writes an I register during the reset
		top->reset = 1;
		int spk = rnd(2) ? 0 : -1;
		for (int k = 0; k < 8; k++) {
			ce = !ce; top->ce = ce;
			if (spk == 0 && ce && k >= 2) {
				int idx = rnd(8); uint32_t val = rng() & 0x3fff;
				top->hold_req = 1; top->sp_we = 1; top->sp_idx = idx; top->sp_val = val;
				ref->m_i[idx] = val; ref->update_i(idx); spk = 1; sides++;
			}
			tick();
			top->sp_we = 0; top->hold_req = 0;
		}
		top->reset = 0;
		ref->device_reset();
		if (top->rootp->adsp2105__DOT__mstat != ref->m_mstat) { printf("reset mismatch\n"); return 1; }
		rtl_timer_edges = ref->timer_cb_count = 0; last_ten = top->timer_en;

		uint64_t n = 0;
		int stuck = 0;
		int pend_pulse1 = 0;
		while (n < (uint64_t)per && !fails) {
			ce = !ce; top->ce = ce;
			// inputs for this step
			top->pm_q = pm_q; top->dm_q = dm_q;
			top->go = (rnd(10) != 0);
			top->dm_rdy = top->dm_rd ? (rnd(3) != 0) : 1;
			if (top->dm_rd && !top->dm_rdy) waits++;
			top->irq_set = 0; top->irq_clr = 0; top->irq1_pulse = 0; top->timer_pulse = 0;
			top->clk = 0; top->eval();
			bool commit = ce && top->rootp->adsp2105__DOT__state == 2 &&
			              (!top->rootp->adsp2105__DOT__dm_rd_r || top->dm_rdy) && !top->reset;
			// the board's side port: once the CPU holds at a boundary, write an
			// I register (dcs.cpp set_state_int), then let it go
			if (ce && hold_st == 1 && top->hold_ack) {
				int idx = rnd(8); uint32_t val = rng() & 0x3fff;
				top->sp_we = 1; top->sp_idx = idx; top->sp_val = val;
				ref->m_i[idx] = val; ref->update_i(idx);
				hold_st = 2; sides++;
				top->eval();
			}
			if (commit) {
				// the reference: the check at this instruction's boundary, the instruction
				adsp21xx_device &m = *ref;
				pre_si = m.m_core.si.u; pre_sb = m.m_core.sb.u; pre_se = m.m_core.se.u; pre_astat = m.m_astat;
				m.check_irqs();
				if (pend_pulse1) { m.m_irq_state[1] = 0; pend_pulse1 = 0; }
				if (!m.m_idle) m.step();
				// new events, taken with this edge in the RTL and after the
				// instruction in the reference
				if (rnd(30) == 0) {
					int e = rnd(6);
					irqs++;
					if (e < 3)       { top->irq_set = 1 << e; m.execute_set_input(e, 1); }
					else if (e == 3) { int l = rnd(3); top->irq_clr = 1 << l; m.execute_set_input(l, 0); }
					else if (e == 4) { top->irq1_pulse = 1; m.execute_set_input(1, 1); pend_pulse1 = 1; }
					else             { top->timer_pulse = 1; m.m_irq_latch[5] = 1; }
				}
				top->eval();
			}
			if (ce) {
				// memories: write now, read for the next step
				uint32_t pa = top->pm_a & 0x3fff, da = top->dm_a & 0x3fff;
				if (top->pm_we) { pm_r[pa] = top->pm_wd & 0xffffff; }
				if (top->dm_we) { dm_r[da] = top->dm_wd; }
				pm_q = pm_r[pa]; dm_q = dm_r[da];
			}
			top->clk = 1; top->eval();
			if (ce && hold_st == 2) { top->sp_we = 0; top->hold_req = 0; hold_st = 0; }
			if (top->timer_en != last_ten) { rtl_timer_edges++; last_ten = top->timer_en; }
			if (ce && top->tx1_wr) rtl_tx1++;

			if (commit) {
				n++; total++; stuck = 0;
				if (!compare(total)) {
					printf("  op %06X at %04X  before: SI %04X SB %04X SE %04X ASTAT %02X\n", top->rootp->adsp2105__DOT__op, top->ppc_o, pre_si, pre_sb, pre_se, pre_astat);
					break;
				}
				if (hold_st == 0 && rnd(40) == 0) { top->hold_req = 1; hold_st = 1; }
				if (rnd(200) == 0) {
					top->tx1_arm = rnd(2); top->tx1_ireg = rnd(8);
					ref->tx1_arm = top->tx1_arm; ref->tx1_ireg = top->tx1_ireg;
				}
			}
			else if (ce) {
				// an idle CPU waits at the boundary for an interrupt; when none
				// comes, reset both and go on
				if (top->idle && top->rootp->adsp2105__DOT__state == 0) {
					if (++stuck > 40) {
						idles++;
						top->reset = 1;
						for (int k = 0; k < 8; k++) { ce = !ce; top->ce = ce; tick(); }
						top->reset = 0;
						ref->device_reset();
						pend_pulse1 = 0; stuck = 0;
					}
				}
			}
		}
		for (int a = 0; a < 16384; a++) {
			if (pm_r[a] != pm_m[a]) { fail("PM", pm_r[a], pm_m[a], a); break; }
			if (dm_r[a] != dm_m[a]) { fail("DM", dm_r[a], dm_m[a], a); break; }
		}
		printf("program %d: %llu instructions ok\n", p, (unsigned long long)n);
	}
	if (rtl_tx1 != ref->tx1_count) printf("TX1 writes RTL %d MAME %d\n", rtl_tx1, ref->tx1_count);
	printf("%s: %llu instructions, %llu interrupt events, %llu read waits, %llu idles, %llu side port writes\n",
	       fails ? "FAIL" : "PASS", (unsigned long long)total, (unsigned long long)irqs,
	       (unsigned long long)waits, (unsigned long long)idles, (unsigned long long)sides);
	delete top;
	return fails ? 1 : 0;
}

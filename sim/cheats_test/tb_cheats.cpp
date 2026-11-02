// ============================================================================
//  tb_cheats.cpp - test bench for rtl/tunit_cheats.sv, the receiver of the
//  OSD's cheat downloads (ROM index 255)
//
//  Main_MiSTer sends the switched-on cheats, 8-byte units back to back, as
//  one download each time the Cheats menu toggles one; a lone 2-byte word
//  when none is on. A unit is four 16-bit words: word address bits 15-0;
//  bits 11-0 address bits 27-16 and the flags in bits 15-12 (12: a program
//  ROM word, patched for instruction fetches only; 13: the CPU's writes store
//  the value too; 14: a one-shot write); the value; the mask (the bits of
//  the word the value covers). The module clears its entries when a download
//  starts or a ROM set loads, and enables an entry only when all four words
//  of its unit have arrived. A one-shot has no read patch (ck_pk instead of
//  ck_en) and ck_fire pulses for it when the previous list did not hold the
//  same address and value.
//  Checks: the entries after downloads of 0 to 8 units, a download cut
//  inside a unit, a lone word, the clear input, a second download replacing
//  the first, the 28-bit address, the flags, the mask (value cut to the mask,
//  a one-shot and a store entry take the whole word), the one-shot's fire
//  pulse once per switch-on (not again when another cheat is toggled, and
//  again when it was off in between, when the value changed, or after the
//  clear input), and 4000 random downloads against a model.
//
//  Usage: Vtunit_cheats    (exit code 0: all checks passed)
//
//  Copyright (C) 2026 Gm0rk - GPL-3.0-or-later
// ============================================================================

#include "Vtunit_cheats.h"
#include "verilated.h"
#include <cstdio>
#include <cstdlib>
#include <cstdint>
#include <vector>

static Vtunit_cheats *m;
static long checks = 0, fails = 0;
static unsigned fire_seen = 0;       // ck_fire bits seen since it was last read
static unsigned fire_count[8];

#define CHECK(cond, ...) do { checks++; if (!(cond)) { fails++; if (fails <= 20) { printf("FAIL: " __VA_ARGS__); printf("\n"); } } } while (0)

static void tick()
{
	m->clk = 0; m->eval();
	m->clk = 1; m->eval();
	for (int i = 0; i < 8; i++) if ((m->ck_fire >> i) & 1) { fire_seen |= 1u << i; fire_count[i]++; }
	m->dl_start = 0; m->dl_wr = 0; m->clear = 0;
}

// one download: a start pulse, then the words (word index counts from 0)
static void download(const std::vector<uint16_t> &w)
{
	fire_seen = 0; for (int i = 0; i < 8; i++) fire_count[i] = 0;
	m->dl_start = 1; tick();
	for (size_t i = 0; i < w.size() && i < 32; i++) {
		m->dl_wr = 1; m->dl_addr = (uint8_t)i; m->dl_data = w[i];
		tick();
		if (i % 3 == 0) tick();                 // gaps between words
	}
	tick(); tick();
}

enum { F_FETCH = 1, F_STORE = 2, F_PK = 4 };
struct Unit { uint32_t wa; uint16_t val, flags, mask; };

static std::vector<uint16_t> words(const std::vector<Unit> &u)
{
	std::vector<uint16_t> w;
	for (auto &x : u) {
		w.push_back(x.wa & 0xFFFF);
		w.push_back(((x.wa >> 16) & 0xFFF) | (x.flags << 12));
		w.push_back(x.val);
		w.push_back(x.mask);
	}
	return w;
}

static uint32_t addr_of(int n) { uint32_t v = 0; for (int i = 0; i < 28; i++) v |= (uint32_t)((m->ck_addr[(28 * n + i) >> 5] >> ((28 * n + i) & 31)) & 1) << i; return v; }
static uint16_t data_of(int n) { uint16_t v = 0; for (int i = 0; i < 16; i++) v |= (uint16_t)((m->ck_data[(16 * n + i) >> 5] >> ((16 * n + i) & 31)) & 1) << i; return v; }
static uint16_t mask_of(int n) { uint16_t v = 0; for (int i = 0; i < 16; i++) v |= (uint16_t)((m->ck_mask[(16 * n + i) >> 5] >> ((16 * n + i) & 31)) & 1) << i; return v; }

// compare with the first n whole units of u (the model); entries beyond are off
static void expect(const std::vector<Unit> &u, size_t n, const char *what)
{
	if (n > 8) n = 8;
	unsigned en = 0, pk = 0, fe = 0, st = 0;
	for (size_t i = 0; i < n; i++) {
		bool one = u[i].flags & F_PK;
		if (one) pk |= 1u << i; else en |= 1u << i;
		if (!one && (u[i].flags & F_FETCH)) fe |= 1u << i;
		if (!one && (u[i].flags & F_STORE)) st |= 1u << i;
	}
	CHECK(m->ck_en == en, "%s: ck_en %02X, wanted %02X", what, m->ck_en, en);
	CHECK(m->ck_pk == pk, "%s: ck_pk %02X, wanted %02X", what, m->ck_pk, pk);
	CHECK(m->ck_fetch == fe, "%s: ck_fetch %02X, wanted %02X", what, m->ck_fetch, fe);
	CHECK(m->ck_store == st, "%s: ck_store %02X, wanted %02X", what, m->ck_store, st);
	for (size_t i = 0; i < n; i++) {
		bool whole = (u[i].flags & (F_PK | F_STORE)) == 0 ? false : true;
		bool one = u[i].flags & F_PK;
		uint16_t mk = one ? 0xFFFF : u[i].mask;
		uint16_t vl = one ? u[i].val : (uint16_t)(u[i].val & u[i].mask);
		(void)whole;
		CHECK(addr_of(i) == (u[i].wa & 0x0FFFFFFF), "%s: unit %zu address %07X, wanted %07X", what, i, addr_of(i), u[i].wa & 0x0FFFFFFF);
		CHECK(data_of(i) == vl, "%s: unit %zu value %04X, wanted %04X", what, i, data_of(i), vl);
		CHECK(mask_of(i) == mk, "%s: unit %zu mask %04X, wanted %04X", what, i, mask_of(i), mk);
	}
}

// the one-shots that should have fired: those of u (n whole units) not in prev (address and value)
static unsigned want_fire(const std::vector<Unit> &u, size_t n, const std::vector<Unit> &prev)
{
	unsigned f = 0;
	for (size_t i = 0; i < n && i < 8; i++) {
		if (!(u[i].flags & F_PK)) continue;
		bool dup = false;
		for (auto &p : prev)
			if ((p.flags & F_PK) && (p.wa & 0x0FFFFFFF) == (u[i].wa & 0x0FFFFFFF) && p.val == u[i].val) dup = true;
		if (!dup) f |= 1u << i;
	}
	return f;
}

static void expect_fire(unsigned want, const char *what)
{
	CHECK(fire_seen == want, "%s: ck_fire %02X, wanted %02X", what, fire_seen, want);
	for (int i = 0; i < 8; i++) CHECK(fire_count[i] <= 1, "%s: ck_fire[%d] pulsed %u times", what, i, fire_count[i]);
}

int main(int argc, char **argv)
{
	Verilated::commandArgs(argc, argv);
	m = new Vtunit_cheats;
	m->clear = 0; m->dl_start = 0; m->dl_wr = 0; m->dl_addr = 0; m->dl_data = 0;
	tick(); tick();
	CHECK(m->ck_en == 0 && m->ck_fetch == 0 && m->ck_store == 0 && m->ck_pk == 0, "power-up: entries not off (%02X)", m->ck_en);

	// the four cheats of a Mortal Kombat II set (tools/tunit_cheats.py)
	std::vector<Unit> mk2 = { {0x0010602F, 0x00A1, F_STORE, 0xFFFF}, {0x001060EC, 0x00A1, F_STORE, 0xFFFF},
	                          {0x0FF819FA, 0x4D4A, F_FETCH, 0xFFFF}, {0x0FF81F15, 0x7FFF, F_FETCH, 0xFFFF} };
	for (size_t n = 0; n <= 4; n++) {
		std::vector<Unit> u(mk2.begin(), mk2.begin() + n);
		if (n == 0) download({0x0000});          // the lone word Main sends when none is on
		else download(words(u));
		expect(mk2, n, "mk2 cheats");
	}

	// each count of units to 8, and 9 or more (the top level passes only the first 64 bytes)
	std::vector<Unit> all;
	for (int i = 0; i < 8; i++) all.push_back({(uint32_t)(0x0100000 + 0x111 * i), (uint16_t)(0x1000 + i), (uint16_t)(i & 3), 0xFFFF});
	for (size_t n = 0; n <= 8; n++) {
		std::vector<Unit> u(all.begin(), all.begin() + n);
		download(n ? words(u) : std::vector<uint16_t>{0});
		expect(all, n, "count");
	}

	// a download cut inside a unit enables only the whole units
	for (int cut = 1; cut < 4; cut++) {
		auto w = words({mk2[0], mk2[1]});
		w.resize(4 + cut);
		download(w);
		expect(mk2, 1, "cut in the second unit");
	}
	{ auto w = words({mk2[0]}); w.resize(3); download(w); expect(mk2, 0, "cut in the first unit"); }

	// a new download replaces the old: fewer units, different units
	download(words(mk2)); expect(mk2, 4, "four");
	download(words({mk2[3]})); expect({mk2[3]}, 1, "one, the timer");
	download(words({mk2[1], mk2[2]})); expect({mk2[1], mk2[2]}, 2, "a health cheat and the clock");
	download({0x0000}); expect(mk2, 0, "none");

	// the clear input (a ROM set loading) turns everything off, a new download turns it on again
	download(words(mk2)); expect(mk2, 4, "before clear");
	m->clear = 1; tick(); expect(mk2, 0, "clear");
	download(words(mk2)); expect(mk2, 4, "after clear");
	m->clear = 1; m->dl_wr = 1; m->dl_addr = 3; m->dl_data = 1; tick(); expect(mk2, 0, "clear with a write");

	// the address is 28 bits, the flags are bits 15-12 of word 1 and the bit 15 is not used
	{
		std::vector<Unit> u = { {0x0FF81F15, 0x7FFF, F_FETCH, 0xFFFF}, {0x0FF81F15, 0x7FFF, 0, 0xFFFF}, {0x0FF81F15, 0x7FFF, F_FETCH | F_STORE, 0xFFFF}, {0x0FF81F15, 0x7FFF, F_STORE, 0xFFFF} };
		auto w = words(u);
		w[1] |= 0x8000; w[5] |= 0x8000; w[9] |= 0x8000; w[13] |= 0x8000;     // the spare bit
		download(w);
		expect(u, 4, "28-bit address, flags");
	}

	// the mask: the value is cut to it, a one-shot takes the whole word
	{
		std::vector<Unit> u = { {0x0010E59C, 0xFFFF, 0, 0x0001}, {0x0010E59C, 0x1234, 0, 0xFF00}, {0x0010E53D, 0x002F, 0, 0x00FF},
		                        {0x0010E53D, 0x1234, F_STORE, 0xFF00}, {0x00105130, 0x0000, F_PK, 0x00FF}, {0x00105131, 0x0002, F_PK, 0x0000} };
		download(words(u));
		expect(u, 6, "masks");
	}

	// one-shots: a fire pulse when the entry arrives, not again when the list is sent again
	{
		Unit A = {0x00105130, 0x0000, F_PK, 0xFFFF}, B = {0x0010602F, 0x0001, F_PK, 0xFFFF}, N = {0x0010E59C, 0x0001, 0, 0x0001};
		download({0x0000});
		download(words({A}));          expect({A}, 1, "A on");                    expect_fire(1, "A on");
		download(words({N, A}));       expect({N, A}, 2, "N and A on");           expect_fire(0, "A moved to slot 1");
		download(words({A}));          expect({A}, 1, "N off");                   expect_fire(0, "N off");
		download(words({A, B}));       expect({A, B}, 2, "B on");                 expect_fire(2, "B on");
		download(words({B}));          expect({B}, 1, "A off");                   expect_fire(0, "A off");
		download(words({A, B}));       expect({A, B}, 2, "A on again");           expect_fire(1, "A back on");
		download({0x0000});            expect({A}, 0, "all off");                 expect_fire(0, "all off");
		download(words({A}));          expect({A}, 1, "A on after none");         expect_fire(1, "A fires again after none");
		Unit A2 = A; A2.val = 0x0001;
		download(words({A2}));         expect({A2}, 1, "A with another value");   expect_fire(1, "another value fires");
		m->clear = 1; tick();
		download(words({A2}));         expect({A2}, 1, "after clear");            expect_fire(1, "fires after clear");
		download(words({A2, A2}));     expect({A2, A2}, 2, "twice");              expect_fire(0, "the same in the list again");
	}

	// random downloads against the model
	srand(45);
	std::vector<Unit> prev;           // the previous list's completed units
	for (int t = 0; t < 4000; t++) {
		int nu = rand() % 9, extra = rand() % 4;
		std::vector<Unit> u;
		for (int i = 0; i < nu; i++) {
			uint16_t fl = rand() & 7;
			if (fl == 7 || fl == 5 || fl == 6) fl &= 4;                  // a one-shot: no other flag
			uint32_t wa = (rand() & 1) ? (uint32_t)(0x0100000 + (rand() & 3)) : (uint32_t)(((rand() & 0xFFF) << 16) | (rand() & 0xFFFF));
			u.push_back({wa, (uint16_t)((rand() & 1) ? (rand() & 3) : rand()), fl, (uint16_t)((rand() & 1) ? 0xFFFF : rand())});
		}
		auto w = words(u);
		for (int i = 0; i < extra && nu < 8; i++) w.push_back((uint16_t)rand());   // a unit cut short
		if (w.empty()) w.push_back(0);
		download(w);
		expect(u, nu, "random");
		expect_fire(want_fire(u, nu, prev), "random");
		prev.assign(u.begin(), u.begin() + (nu > 8 ? 8 : nu));
		if (t % 7 == 0) { m->clear = 1; tick(); expect(u, 0, "random clear"); prev.clear(); }
	}

	printf("%ld checks, %ld failures\n", checks, fails);
	delete m;
	return fails ? 1 : 0;
}

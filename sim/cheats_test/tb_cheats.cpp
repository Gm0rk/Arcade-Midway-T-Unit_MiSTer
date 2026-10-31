// ============================================================================
//  tb_cheats.cpp - test bench for rtl/tunit_cheats.sv, the receiver of the
//  OSD's cheat downloads (ROM index 255)
//
//  Main_MiSTer sends the switched-on cheats, 8-byte units back to back, as
//  one download each time the Cheats menu toggles one; a lone 2-byte word
//  when none is on. A unit is four 16-bit words: word address bits 15-0,
//  bits 27-16, the value, and flags (bit 0: an instruction word, bit 1: the
//  CPU's writes store the value too). The
//  module clears its entries when a download starts or a ROM set loads, and
//  enables an entry only when all four words of its unit have arrived.
//  Checks: the entries after downloads of 0 to 8 units, a download cut
//  inside a unit, a lone word, the clear input, a second download replacing
//  the first, the 28-bit address and the flag bits 0 and 1 only, and 2000 random
//  downloads against a model.
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

#define CHECK(cond, ...) do { checks++; if (!(cond)) { fails++; if (fails <= 20) { printf("FAIL: " __VA_ARGS__); printf("\n"); } } } while (0)

static void tick()
{
	m->clk = 0; m->eval();
	m->clk = 1; m->eval();
	m->dl_start = 0; m->dl_wr = 0; m->clear = 0;
}

// one download: a start pulse, then the words (word index counts from 0)
static void download(const std::vector<uint16_t> &w)
{
	m->dl_start = 1; tick();
	for (size_t i = 0; i < w.size() && i < 32; i++) {
		m->dl_wr = 1; m->dl_addr = (uint8_t)i; m->dl_data = w[i];
		tick();
		if (i % 3 == 0) tick();                 // gaps between words
	}
	tick();
}

struct Unit { uint32_t wa; uint16_t val, flags; };

static std::vector<uint16_t> words(const std::vector<Unit> &u)
{
	std::vector<uint16_t> w;
	for (auto &x : u) {
		w.push_back(x.wa & 0xFFFF);
		w.push_back((x.wa >> 16) & 0xFFFF);
		w.push_back(x.val);
		w.push_back(x.flags);
	}
	return w;
}

static uint32_t addr_of(int n) { uint32_t v = 0; for (int i = 0; i < 28; i++) v |= (uint32_t)((m->ck_addr[(28 * n + i) >> 5] >> ((28 * n + i) & 31)) & 1) << i; return v; }
static uint16_t data_of(int n) { uint16_t v = 0; for (int i = 0; i < 16; i++) v |= (uint16_t)((m->ck_data[(16 * n + i) >> 5] >> ((16 * n + i) & 31)) & 1) << i; return v; }

// compare with the first n whole units of u (the model); entries beyond are off
static void expect(const std::vector<Unit> &u, size_t n, const char *what)
{
	if (n > 8) n = 8;
	CHECK(m->ck_en == (uint8_t)((1u << n) - 1), "%s: ck_en %02X, wanted %02X", what, m->ck_en, (1u << n) - 1);
	for (size_t i = 0; i < n; i++) {
		CHECK(addr_of(i) == (u[i].wa & 0x0FFFFFFF), "%s: unit %zu address %07X, wanted %07X", what, i, addr_of(i), u[i].wa & 0x0FFFFFFF);
		CHECK(data_of(i) == u[i].val, "%s: unit %zu value %04X, wanted %04X", what, i, data_of(i), u[i].val);
		CHECK(((m->ck_fetch >> i) & 1) == (u[i].flags & 1), "%s: unit %zu fetch %d, wanted %d", what, i, (m->ck_fetch >> i) & 1, u[i].flags & 1);
		CHECK(((m->ck_store >> i) & 1) == ((u[i].flags >> 1) & 1), "%s: unit %zu store %d, wanted %d", what, i, (m->ck_store >> i) & 1, (u[i].flags >> 1) & 1);
	}
	CHECK((m->ck_fetch & ~((1u << n) - 1)) == 0, "%s: fetch bits set for unused entries (%02X)", what, m->ck_fetch);
	CHECK((m->ck_store & ~((1u << n) - 1)) == 0, "%s: store bits set for unused entries (%02X)", what, m->ck_store);
}

int main(int argc, char **argv)
{
	Verilated::commandArgs(argc, argv);
	m = new Vtunit_cheats;
	m->clear = 0; m->dl_start = 0; m->dl_wr = 0; m->dl_addr = 0; m->dl_data = 0;
	tick(); tick();
	CHECK(m->ck_en == 0 && m->ck_fetch == 0 && m->ck_store == 0, "power-up: entries not off (%02X)", m->ck_en);

	// the four cheats of a Mortal Kombat II set (tools/tunit_cheats.py)
	std::vector<Unit> mk2 = { {0x0010602F, 0x00A1, 2}, {0x001060EC, 0x00A1, 2}, {0x0FF819FA, 0x4D4A, 1}, {0x0FF81F15, 0x7FFF, 1} };
	for (size_t n = 0; n <= 4; n++) {
		std::vector<Unit> u(mk2.begin(), mk2.begin() + n);
		if (n == 0) download({0x0000});          // the lone word Main sends when none is on
		else download(words(u));
		expect(mk2, n, "mk2 cheats");
	}

	// each count of units to 8, and 9 or more (the top level passes only the first 64 bytes)
	std::vector<Unit> all;
	for (int i = 0; i < 8; i++) all.push_back({(uint32_t)(0x0100000 + 0x111 * i), (uint16_t)(0x1000 + i), (uint16_t)(i & 3)});
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

	// only the 28 address bits and bits 0 and 1 of the flags count
	{
		std::vector<Unit> u = { {0x0FF81F15, 0x7FFF, 0x0001}, {0x0FF81F15, 0x7FFF, 0xFFFC}, {0x0FF81F15, 0x7FFF, 0xFFFF}, {0x0FF81F15, 0x7FFF, 0x0002} };
		auto w = words(u);
		w[1] |= 0xF000; w[5] |= 0xF000; w[9] |= 0xF000; w[13] |= 0xF000;     // junk above bit 27
		download(w);
		std::vector<Unit> want = { {0x0FF81F15, 0x7FFF, 1}, {0x0FF81F15, 0x7FFF, 0}, {0x0FF81F15, 0x7FFF, 3}, {0x0FF81F15, 0x7FFF, 2} };
		expect(want, 4, "28-bit address, flag bits 0 and 1");
	}

	// random downloads against the model
	srand(45);
	for (int t = 0; t < 2000; t++) {
		int nu = rand() % 9, extra = rand() % 4;
		std::vector<Unit> u;
		for (int i = 0; i < nu; i++) u.push_back({(uint32_t)(((rand() & 0xFFF) << 16) | (rand() & 0xFFFF)), (uint16_t)rand(), (uint16_t)(rand() & 3)});
		auto w = words(u);
		for (int i = 0; i < extra && nu < 8; i++) w.push_back((uint16_t)rand());   // a unit cut short
		if (w.empty()) w.push_back(0);
		download(w);
		expect(u, nu, "random");
		if (t % 7 == 0) { m->clear = 1; tick(); expect(u, 0, "random clear"); }
	}

	printf("%ld checks, %ld failures\n", checks, fails);
	delete m;
	return fails ? 1 : 0;
}

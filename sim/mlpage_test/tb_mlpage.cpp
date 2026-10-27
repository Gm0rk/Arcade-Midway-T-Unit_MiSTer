// ============================================================================
//  tb_mlpage.cpp - the information window's page (rtl/tunit_mlpage.sv) alone
//
//  Presses Left and Right the way a player's controller does (a level held
//  for a number of clocks) and checks the page after each step: one press
//  turns one page, a held button does not repeat, the pages wrap both ways,
//  both buttons together turn nothing, presses with the OSD open or the
//  option Off are ignored, switching the option On starts at the first page,
//  and a page past the list goes back to the first. Mortal Kombat II Plus
//  has two lists (the Move List, 17 pages, and View Secrets, 5): with both On
//  the one switched on last is shown, from its first page; with one On,
//  that one.
//
//  Usage: Vtunit_mlpage    (exit code 0: all checks passed)
//
//  Copyright (C) 2026 Gm0rk - GPL-3.0-or-later
// ============================================================================

#include "Vtunit_mlpage.h"
#include "verilated.h"
#include <cstdio>

static Vtunit_mlpage *m;
static int bad = 0, checks = 0;

static void clk(int n = 1)
{
	while (n--) {
		m->clk = 0; m->eval();
		m->clk = 1; m->eval();
	}
}

static void expect(const char *what, int want)
{
	checks++;
	if (m->page != want) {
		printf("FAIL %-52s page %d, want %d\n", what, m->page, want);
		bad++;
	}
}

static void expect_show(const char *what, int page, int show_b)
{
	checks++;
	if (m->page != page || m->show_b != show_b) {
		printf("FAIL %-52s page %d list %c, want page %d list %c\n", what, m->page,
		       m->show_b ? 'B' : 'A', page, show_b ? 'B' : 'A');
		bad++;
	}
}

// press a button for `hold` clocks, then let go for a few
static void tap(bool l, bool r, int hold = 10)
{
	m->left = l; m->right = r;
	clk(hold);
	m->left = 0; m->right = 0;
	clk(6);
}

int main(int argc, char **argv)
{
	Verilated::commandArgs(argc, argv);
	m = new Vtunit_mlpage;
	m->on_a = 0; m->pages_a = 2; m->on_b = 0; m->pages_b = 5; m->osd_open = 0; m->left = 0; m->right = 0;
	clk(4);
	expect("reset: first page", 0);

	// Off: presses do nothing
	tap(0, 1);
	expect("Off: Right ignored", 0);
	tap(1, 0);
	expect("Off: Left ignored", 0);

	// MK, two pages
	m->on_a = 1; m->pages_a = 2;
	clk(4);
	expect("On: starts at the first page", 0);
	tap(0, 1);
	expect("2 pages: Right -> page 2", 1);
	tap(0, 1);
	expect("2 pages: Right wraps to page 1", 0);
	tap(1, 0);
	expect("2 pages: Left wraps to page 2", 1);
	tap(1, 0);
	expect("2 pages: Left -> page 1", 0);

	// a held button turns once
	m->right = 1;
	clk(500);
	expect("Right held for 500 clocks: one page", 1);
	m->right = 0;
	clk(6);
	tap(0, 1, 1);
	expect("a one-clock press turns a page", 0);

	// both together: nothing
	tap(1, 1);
	expect("Left + Right together: nothing", 0);
	// both held, then one let go: the one still held was already down
	m->left = 1; m->right = 1;
	clk(8);
	m->left = 0;
	clk(8);
	expect("both held, Left let go: nothing", 0);
	m->right = 0;
	clk(6);

	// the OSD open: the controls are the menu's
	tap(0, 1);
	expect("(to page 2)", 1);
	m->osd_open = 1;
	tap(0, 1);
	tap(1, 0);
	tap(0, 1);
	expect("OSD open: presses ignored, page kept", 1);
	m->right = 1; clk(8);              // pressed with the OSD open, still down when it closes
	m->osd_open = 0; clk(8);
	m->right = 0; clk(6);
	// the edge happened with the OSD open: nothing turns when it closes
	expect("OSD closes with Right held: no turn", 1);
	tap(0, 1);
	expect("after the OSD: Right turns", 0);

	// Off then On again: first page
	tap(0, 1);
	expect("(to page 2)", 1);
	m->on_a = 0; clk(4);
	expect("Off: page back to the first", 0);
	m->on_a = 1; clk(4);
	expect("On again: first page", 0);

	// MK2, twelve pages
	m->pages_a = 12; clk(4);
	for (int k = 1; k <= 12; k++) {
		tap(0, 1);
		char w[64]; snprintf(w, sizeof w, "12 pages: Right %d times", k);
		expect(w, k % 12);
	}
	tap(1, 0);
	expect("12 pages: Left from page 1 -> page 12", 11);
	for (int k = 1; k <= 11; k++) tap(1, 0);
	expect("12 pages: Left 11 more -> page 1", 0);

	// NBA Jam Tournament Edition, six pages (the Secret Player List window)
	m->on_a = 0; clk(4);
	m->on_a = 1; m->pages_a = 6; clk(4);
	expect("6 pages: On starts at the first page", 0);
	for (int k = 1; k <= 6; k++) {
		tap(0, 1);
		char w[64]; snprintf(w, sizeof w, "6 pages: Right %d times", k);
		expect(w, k % 6);
	}
	tap(1, 0);
	expect("6 pages: Left from page 1 -> page 6", 5);
	// NBA Jam, two pages
	m->on_a = 0; clk(4);
	m->on_a = 1; m->pages_a = 2; clk(4);
	tap(0, 1);
	expect("2 pages (NBA Jam): Right -> the codes page", 1);
	tap(0, 1);
	expect("2 pages (NBA Jam): Right wraps to the players page", 0);
	m->pages_a = 12; clk(4);

	// a page past the list: back to the first
	for (int k = 0; k < 5; k++) tap(0, 1);
	expect("(to page 6)", 5);
	m->pages_a = 2; clk(4);
	expect("list shrinks to 2 pages: first page", 0);

	// Mortal Kombat II Plus: list A the Move List (17 pages), list B View Secrets (5)
	m->on_a = 0; m->on_b = 0; m->pages_a = 17; m->pages_b = 5; clk(4);
	expect_show("Plus: both Off", 0, 0);
	m->on_a = 1; clk(4);
	expect_show("Move List On: list A, first page", 0, 0);
	for (int k = 0; k < 3; k++) tap(0, 1);
	expect_show("Move List: Right x3 -> page 4", 3, 0);
	m->on_b = 1; clk(4);
	expect_show("View Secrets On too: list B from its first page", 0, 1);
	for (int k = 0; k < 5; k++) tap(0, 1);
	expect_show("5 pages: Right x5 wraps", 0, 1);
	tap(1, 0);
	expect_show("5 pages: Left from page 1 -> page 5", 4, 1);
	m->on_a = 0; clk(4);
	expect_show("Move List Off: Secrets stays, page kept", 4, 1);
	m->on_a = 1; clk(4);
	expect_show("Move List On again (last): list A, first page", 0, 0);
	for (int k = 0; k < 11; k++) tap(0, 1);
	expect_show("(to page 12 of the Move List)", 11, 0);
	m->on_b = 0; clk(4);
	expect_show("Secrets Off: Move List stays, page kept", 11, 0);
	for (int k = 0; k < 6; k++) tap(0, 1);
	expect_show("17 pages: Right x6 -> page 18 wraps to 1", 0, 0);
	tap(1, 0);
	expect_show("17 pages: Left from page 1 -> page 17", 16, 0);
	// Secrets first, then the Move List: the Move List shows
	m->on_a = 0; clk(4);
	expect_show("both Off", 0, 0);
	m->on_b = 1; clk(4);
	tap(0, 1);
	expect_show("Secrets On: Right -> page 2", 1, 1);
	m->on_a = 1; clk(4);
	expect_show("Move List On after Secrets: list A", 0, 0);
	m->on_a = 0; clk(4);
	expect_show("Move List Off: list B again, first page", 0, 1);
	// both On in the same clock (as a saved setting loads): list B
	m->on_b = 0; clk(4);
	m->on_a = 1; m->on_b = 1; clk(4);
	expect_show("both On at once: list B (B wins a tie)", 0, 1);
	// the OSD open: nothing turns in either list
	m->osd_open = 1;
	tap(0, 1);
	expect_show("OSD open: Right ignored in list B", 0, 1);
	m->osd_open = 0;
	tap(0, 1);
	expect_show("OSD closed: Right turns list B", 1, 1);
	// a list that shrinks below the page
	m->on_b = 0; clk(4);
	for (int k = 0; k < 9; k++) tap(0, 1);
	expect_show("(to page 10 of the Move List)", 9, 0);
	m->pages_a = 2; clk(4);
	expect_show("Move List shrinks to 2 pages: first page", 0, 0);

	m->final();
	delete m;
	printf("%d checks, %d failed\n", checks, bad);
	return bad ? 1 : 0;
}

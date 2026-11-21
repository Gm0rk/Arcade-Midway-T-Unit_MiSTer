// Reads "game_id status(32 hex digits) word(4 hex digits)" lines from stdin,
// applies the game id and the status to tunit_dsw and compares the switch word.
#include "Vtunit_dsw.h"
#include "verilated.h"
#include <cstdio>
#include <cstring>
#include <cstdlib>

int main(int argc, char **argv)
{
	Verilated::commandArgs(argc, argv);
	Vtunit_dsw *top = new Vtunit_dsw;
	char line[256];
	int n = 0, bad = 0;
	while (fgets(line, sizeof line, stdin))
	{
		unsigned gid = 0, word = 0;
		char st[64];
		if (sscanf(line, "%u %63s %x", &gid, st, &word) != 3)
			continue;
		if (strlen(st) != 32)
		{
			fprintf(stderr, "bad status: %s\n", st);
			return 2;
		}
		// the status word: 128 bits, the most significant digit first
		for (int w = 0; w < 4; w++)
		{
			char part[9];
			memcpy(part, st + (3 - w) * 8, 8);
			part[8] = 0;
			top->status[w] = (uint32_t)strtoul(part, nullptr, 16);
		}
		top->game_id = gid;
		top->eval();
		n++;
		if (top->dsw != word)
		{
			if (bad < 20)
				printf("FAIL game %u status %s: word %04X, expected %04X\n", gid, st, top->dsw, word);
			bad++;
		}
	}
	printf("dips_test: %d vectors, %d wrong\n", n, bad);
	delete top;
	return bad ? 1 : 0;
}

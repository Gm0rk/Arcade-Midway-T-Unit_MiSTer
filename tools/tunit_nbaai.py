#!/usr/bin/env python3
"""
tunit_nbaai.py - the sites of Fixed AI Difficulty in NBA Jam and NBA Jam TE

The game's CPU players play at a skill value that each player's object keeps
in two fields (obj+440h, obj+460h; the AI adds them, clamps the sum to -15..15
and reads its reaction-time tables with it):

  - obj+460h is set once, when the game starts: a player of the human's team
    gets 0, a CPU opponent of a human gets the rating of its player less a
    step that depends on the human's record (a 10-game streak or more also
    sets the word that selects the AI's "hard" routines, and so does a Drone
    Difficulty above Medium). It is raised and lowered again once, at the end
    of the game.
  - obj+440h follows the score all the time (the catch-up): each CPU player
    gets the score difference of its team, a human player's own value is
    cleared by the game's No CPU Assistance setting.

Fixed AI Difficulty (O[113:110], 0-9) gives every CPU opponent the same
skill, for the whole game:

  - obj+460h of a CPU opponent is 2 x level - 10 (-10 to 8): the instruction
    that loads the human's record field before the store becomes MOVI h,A0, the
    jump after it skips the "less 4" (three program ROM words, two of them
    the same instruction),
  - the catch-up of the CPU players is 0: the jump that skips the human's
    players' No CPU Assistance check for a CPU player lands one word earlier,
    on the CLR A2 of that check,
  - the AI's "hard routines" word reads 1 from level 6 and 0 below it (the
    board's read pin, like the level word of Mortal Kombat; the word is also
    set by the Drone Difficulty and by a streak).

The human's own value, the CPU teammate's 0 and the game's own end-of-game
adjustment (which only matters to the next game's start) are not changed.

Sets whose program lacks the word and the two routines (NBA Jam rev 1.00,
2.00 and the prototypes) have no such option.

The table: ROM index 1, from byte 0x454 (the top level's "Fixed AI Difficulty"
section): the hard word's word address (28 bits, low word first), the demo
store's PC (0: not used), two unused words, then from byte 0x460 four
entries of four words: word address low, {flags, word address high 12 bits},
value, unused. Flag bit 12 of the second word: the value is the level's
immediate (the board's 2 x level - 10), the entry's own value is not used.

Copyright (C) 2026 Gm0rk - GPL-3.0-or-later
"""

import struct

from tunit_secrets import Prog, X

# the start of a game: the human's record (the player data: field 180h,
# field 1A0h) and the store of the CPU opponent's value
#   MOVE *A14(180h),A2 / SUBK Ah,A2 / JRLT +3 / MOVE A2,@hard / MOVK 4,A2 /
#   SUBK 4,A1 / JRLE +1 / MOVK 1,A2 / SUB A2,A0 / MOVE *A14(1A0h),A1 /
#   JRNE +1 / SUBK 4,A0 / MOVE A0,*A13(460h)
INIT = [0xB5C2, 0x0180, 0x1542, 0xC403, 0x0582, X, X, 0x1882, 0x1481, 0xC601, 0x1822,
        0x4440, 0xB5C1, 0x01A0, 0xCB01, 0x1480, 0xB00D, 0x0460]
HARD = 5                        # word index of the hard word's address
LOAD = 12                       # MOVE *A14(1A0h),A1: two words
SKIP = 14                       # JRNE +1 (skips the SUBK 4,A0)

# the catch-up of each player:
#   SRL 1,A5 / JRNC store / MOVE @humans,A0 / MOVE A0,A1 / SLL 1Eh,A0 / JREQ store /
#   MOVK Ch,A14 / AND A14,A1 / JREQ store / MOVE @noassist,A0 / JRNE clear /
#   MOVK 1Bh,A0 / CALLA <adjustment> / JREQ store / CLR A2 / MOVE *A6+,A0,1 /
#   MOVE A2,*A0(440h)
CATCH = [0x2FE5, 0xC913, 0x05A0, X, X, 0x4C01, 0x27C0, 0xCA0D, 0x198E, 0x51C1, 0xCA0A,
         0x05A0, X, X, 0xCB05, 0x1B60, 0x0D5F, X, X, 0xCA01, 0x5642, 0x96C0, 0xB040, 0x0440]
JRNC = 1                        # JRNC store: its displacement less one lands on CLR A2
CLR = 20
STORE = 21

MOVI_A0 = 0x09C0                # MOVI IW,A0 (the immediate is the next word)
JR_1 = 0xC001                   # JR +1: skip the next word
DYN = 0x1000                    # flag in the entry's second word: the value is the level's immediate

TABLE_BASE = 0x454              # byte offset in ROM index 1
ENTRY_BASE = 0x460
NENTRIES = 4


def sites(prog_bytes):
    """(hard word's bit address, [(program word index, original word, new word or
    None for the level's immediate)]) or None (a pattern not found, or not once)."""
    p = Prog(prog_bytes)
    a = p.find(INIT)
    b = p.find(CATCH)
    if len(a) != 1 or len(b) != 1:
        return None
    a, b = a[0], b[0]
    # the JRNC of the catch-up must land on the store of the value: the word of the
    # pattern it was matched for; the new displacement lands one word earlier, on CLR A2
    jr = p.w[b + JRNC]
    if b + JRNC + 1 + (jr & 0xFF) != b + STORE or (jr & 0xFF) == 0:
        return None
    patches = [
        (a + LOAD, p.w[a + LOAD], MOVI_A0),
        (a + LOAD + 1, p.w[a + LOAD + 1], None),
        (a + SKIP, p.w[a + SKIP], JR_1),
        (b + JRNC, jr, jr - 1),
    ]
    return p.u32(a + HARD), patches


def part(prog_bytes):
    """The table bytes from byte 0x454 on (a multiple of 4 up to 0x480) and a note;
    b'' if the sites are not found."""
    r = sites(prog_bytes)
    if r is None:
        return b'', 'Fixed AI Difficulty sites not found'
    hard, patches = r
    w = [0] * ((ENTRY_BASE - TABLE_BASE) // 2 + 4 * NENTRIES)
    h = hard >> 4
    w[0], w[1] = h & 0xFFFF, h >> 16
    for n, (i, orig, new) in enumerate(patches):
        wa = (0xFF800000 >> 4) + i
        k = (ENTRY_BASE - TABLE_BASE) // 2 + 4 * n
        w[k] = wa & 0xFFFF
        w[k + 1] = (DYN if new is None else 0) | (wa >> 16)
        w[k + 2] = 0 if new is None else new
    note = 'hard word %08X, %s' % (hard, ', '.join(
        '%08X %04X->%s' % (0xFF800000 + 16 * i, o, 'level' if n is None else '%04X' % n)
        for i, o, n in patches))
    return struct.pack('<%dH' % len(w), *w), note


def entries(table):
    """Decode the part's bytes (from byte 0x454) as the board does: (hard word's
    word address, [(word address, flags, value)]) with unused entries left out."""
    w = struct.unpack('<%dH' % (len(table) // 2), table)
    hard = w[0] | (w[1] & 0xFFF) << 16
    out = []
    for n in range(NENTRIES):
        k = (ENTRY_BASE - TABLE_BASE) // 2 + 4 * n
        if k + 2 >= len(w):
            break
        wa = w[k] | (w[k + 1] & 0xFFF) << 16
        if wa:
            out.append((wa, w[k + 1] >> 12, w[k + 2]))
    return hard, out


if __name__ == '__main__':
    import sys
    for f in sys.argv[1:]:
        t, note = part(open(f, 'rb').read())
        print(f, len(t), note)

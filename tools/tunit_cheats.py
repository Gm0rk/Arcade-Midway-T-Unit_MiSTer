#!/usr/bin/env python3
# Copyright (C) 2026 Gm0rk - GPL-3.0-or-later
"""MiSTer cheats (the OSD's Cheats menu) for the Mortal Kombat II sets.

Main_MiSTer builds the Cheats menu from the MRA's <cheats> element:

    <cheats size="8" max="8">
        <cheat name="Infinite Health P1">...hex...</cheat>

A cheat is one or more 8-byte units. Switching a cheat on or off in the OSD
makes Main send every switched-on cheat's units, back to back, as one
download with index 255 (a lone 2-byte word when none is on); rtl/tunit_cheats.sv
takes up to 8 units into read patches of the board (rtl/midway_tunit.sv: a
CPU read of the word returns the unit's value, as the OSD secrets do). The
menu names are 27 characters at most.

Unit (four 16-bit words, little-endian, as the other tables):

    word 0   word address bits 15-0 (bit address >> 4)
    word 1   word address bits 27-16
    word 2   value the CPU reads
    word 3   bit 0: a program ROM word, patched for instruction fetches only
                    (the secrets' pt_fetch); 0: a main RAM variable, patched
                    while the CPU has interrupts enabled
             bit 1: the CPU's writes to the word store the value too (a main
                    RAM variable; rtl/midway_tunit.sv pt_store)

The cheats (Mortal Kombat II, found in each set's program the way
tools/tunit_fmoves.py finds the fight variables):

    Infinite Health P1 / P2   the energy word reads full (A1h in every set
                              seen) and the game's writes to it store full
                              too, so the game's own copy stays full and the
                              bar stays full when the cheat is switched off
    Infinite Round Time       the round clock (two digit registers of the
                              clock process, A11 tens and A10 ones, shown
                              from RAM words that the time-over test reads)
                              stops counting: the instruction that counts
                              the ones digit down, DEC A10, becomes
                              MOVE A10,A10 (same flags for the loop's JRNN)
    Stop Finishing Move Timer the FINISH HIM routine's wait (80h frames after
                              its first 28h) becomes 7FFFh frames (about 10
                              minutes). The wait still ends when a finishing
                              move starts or the winner hits the loser, as
                              in the game

Run with the folder of the MAME ROM images (simroms: <set>_rom0.bin) to list
what each set gets.
"""

import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tunit_secrets import Prog, X, G_MK2          # noqa: E402
import tunit_fmoves                               # noqa: E402

CHEAT_SIZE = 8            # bytes per unit (the MRA's <cheats size>)
CHEAT_MAX = 8             # units switched on at once (<cheats max>, rtl/tunit_cheats.sv)
NAME_MAX = 27             # characters the OSD shows

TIMER_VALUE = 0x7FFF      # frames of the FINISH HIM wait (80h in the game)
FULL_DEFAULT = 0x00A1
MOVE_A10_A10 = 0x4D4A     # replaces DEC A10 (142Ah): same size, the flags of A10 >= 0


def unit(bit_addr, value, fetch=False, store=False):
    """One 8-byte unit."""
    wa = bit_addr >> 4
    flags = (1 if fetch else 0) | (2 if store else 0)
    return struct.pack('<4H', wa & 0xFFFF, wa >> 16, value & 0xFFFF, flags)


def full_energy(p, r):
    """The value the game fills both energy words with at a round's start:
    MOVI full,A0 / MOVE A0,@P1 energy / MOVE A0,@P2 energy."""
    a1, a2 = r['p1e'], r['p2e']            # bit addresses, low word first in the code
    h = [k for k in p.find([0x09C0, X, 0x0580, a1 & 0xFFFF, a1 >> 16, 0x0580, a2 & 0xFFFF, a2 >> 16])
         if p.w[k + 1] != 0xFFFF]          # (one other place fills both with FFFFh)
    return p.w[h[0] + 1] if len(h) == 1 else None


def finish_wait(p, r):
    """Bit address of the immediate of the FINISH HIM routine's second wait, or None.

    The routine (the one that sets the round state to 3): MOVI 28h,A11 / wait /
    ... / MOVI 80h,A11 / wait / ... [MOVI 40h,A11 / wait / ...] / MOVI 200h,A11
    / the loop that waits for the move to finish. Each wait is the sub that
    exits when the finish flag is set (a move started) or the other flag is
    set (the winner hit the loser) and otherwise counts A11 down once per
    frame. The second wait is 80h frames (FFh in Mortal Kombat II
    Challenger, whose last loop is FF00h); the first 28h and the later waits stay."""
    s = r['state']
    # MOVK 3,A0 / MOVE A0,@state: the routine's start
    st = p.find([0x1860, 0x0580, s & 0xFFFF, s >> 16])
    if len(st) != 1:
        return None
    lo = st[0]
    first = p.find([0x09CB, 0x0028], lo, lo + 0x100)          # MOVI 28h,A11
    if len(first) != 1:
        return None
    nxt = p.find([0x09CB], first[0] + 2, first[0] + 0x100)    # the next MOVI .,A11
    if not nxt or p.w[nxt[0] + 1] not in (0x0080, 0x00FF):
        return None
    if not (p.find([0x09CB, 0x0200], nxt[0], nxt[0] + 0x100) or      # ends in the 200h loop
            p.find([0x09CB, 0xFF00], nxt[0], nxt[0] + 0x100)):         # (FF00h in Challenger)
        return None
    return 0xFF800000 + 16 * (nxt[0] + 1)


def round_clock(p):
    """Bit address of the DEC A10 that counts the round clock down, or None.

    The clock process (found by its start): MOVK 9,A11 / MOVK 9,A10 / MOVE
    A10,@ones / MOVE A11,@tens, draws the digits, then the time-over test
    MOVE A10,A0 / ADD A11,A0 / JREQ, then the wait loop ... DSJS / DEC A10 /
    JRNN back to the draw / MOVK 9,A10 / DEC A11. The clock lives in the two
    registers, so the RAM words it writes (read by the time-over test of
    another routine) are not where it counts."""
    st = p.find([0x192B, 0x192A, 0x058A, X, X, 0x058B, X, X])
    if len(st) != 1:
        return None
    lo = st[0]
    if not p.find([0x4D40, 0x4160], lo, lo + 0x60):           # MOVE A10,A0 / ADD A11,A0
        return None
    dec = [k for k in range(lo, lo + 0xC0)
           if p.w[k] == 0x142A and (p.w[k + 1] & 0xFF00) == 0xCF00 and
           p.w[k + 2] == 0x192A and p.w[k + 3] == 0x142B]      # DEC A10 / JRNN / MOVK 9,A10 / DEC A11
    if len(dec) != 1:
        return None
    return 0xFF800000 + 16 * dec[0]


def build(gid, prog_bytes):
    """([(menu name, bytes)], notes) for a set's program (the maincpu region)."""
    if gid != G_MK2:
        return [], []
    notes = []
    p = Prog(prog_bytes)
    r, _ = tunit_fmoves.addresses(gid, prog_bytes)
    if not r:
        return [], ['fight variables not found: no cheats']
    out = []
    full = full_energy(p, r)
    if full is None:
        notes.append('full energy value not found: no health cheats')
    elif (r['p1e'] | r['p2e']) & 0xF:
        notes.append('energy not word aligned: no health cheats')
    else:
        out.append(('Infinite Health P1', unit(r['p1e'], full, store=True)))
        out.append(('Infinite Health P2', unit(r['p2e'], full, store=True)))
        notes.append('energy P1 %08X, P2 %08X, full %02Xh' % (r['p1e'], r['p2e'], full))
    c = round_clock(p)
    if c is None:
        notes.append('round clock not found: no time cheat')
    else:
        out.append(('Infinite Round Time', unit(c, MOVE_A10_A10, True)))
        notes.append('round clock DEC A10 %08X' % c)
    w = finish_wait(p, r)
    if w is None:
        notes.append('FINISH HIM wait not found: no timer cheat')
    else:
        out.append(('Stop Finishing Move Timer', unit(w, TIMER_VALUE, True)))
        notes.append('FINISH HIM wait %08X' % w)
    for name, data in out:
        assert len(name) <= NAME_MAX and len(data) % CHEAT_SIZE == 0
    assert sum(len(d) for _, d in out) <= CHEAT_SIZE * CHEAT_MAX
    return out, notes


def main():
    d = sys.argv[1] if len(sys.argv) > 1 else 'simroms'
    for f in sorted(os.listdir(d)):
        if f.startswith('mk2') and f.endswith('_rom0.bin'):
            with open(os.path.join(d, f), 'rb') as fh:
                prog = fh.read(0x100000)
            cheats, notes = build(G_MK2, prog)
            print('%-12s %s' % (f[:-9], '; '.join(notes)))
            for name, data in cheats:
                print('    %-27s %s' % (name, data.hex().upper()))


if __name__ == '__main__':
    main()

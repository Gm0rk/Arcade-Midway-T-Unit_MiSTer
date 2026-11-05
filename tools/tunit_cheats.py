#!/usr/bin/env python3
# Copyright (C) 2026 Gm0rk - GPL-3.0-or-later
"""MiSTer cheats (the OSD's Cheats menu) for Mortal Kombat, Mortal Kombat II
(Mortal Kombat II Plus, Beta 2, hack, included), NBA Jam, NBA Jam
Tournament Edition and Judge Dredd.

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
    word 1   bits 11-0: word address bits 27-16
             bit 12: a program ROM word, patched for instruction fetches only
                     (the secrets' pt_fetch); 0: a main RAM variable, patched
                     while the CPU has interrupts enabled, or a program ROM
                     word the game reads as data (a table: Infinite Health),
                     patched for every read
             bit 13: the CPU's writes to the word store the value too (a main
                     RAM variable; rtl/midway_tunit.sv pt_store), and the
                     board writes the value to the word once when it goes on
             bit 14: a one-shot write: no read patch, the board writes the
                     whole word once when the cheat first appears in the list
    word 2   the value the CPU reads (or writes, for a one-shot)
    word 3   mask: the CPU reads the value in the bits the mask covers and the
             game's own value in the others (FFFF: the whole word; 00FF or
             FF00: a byte; one bit of a player's flag word). Not used by an
             entry with bit 13 or 14, which take the whole word.

Where the cheats come from:

  - tools/tunit_cheats_data.py: the MAME cheat files (plugin XMLs) of mk, mk2,
    nbajam, nbajamr2 and the nbajamte sets, the picks of
    Midway-T-Unit-cheat-picker.xlsx (tools/cheat_import/ turns the files into
    it), and all of jdreddp's (Judge Dredd's only set). A file has the
    addresses of its own set only.
  - the finders, for every set of the game: the OSD items that moved here (the
    power-ups of the four players of NBA Jam and TE, Tank Game, Tournament
    Mode, Shot Percentage, Baby Size, Huge Heads, Computer Assistance; MK
    Reptile Hints; MK2 Hitboxes, Jade, Smoke, Pong and Noob Saibot) are found
    in each revision's program by tools/tunit_secrets.py, and the Mortal
    Kombat II cheats below are found by the code around the round state and
    the energy bars; no other tool is needed.

The Mortal Kombat II cheats (found in each set's program):

    Infinite Health P1 / P2   the player takes no damage: the game's one damage
                              routine finds the pointer to the energy word it
                              subtracts the hit from in a two-entry table of
                              the program ROM, and the unit changes the high
                              half of that player's pointer so that it reads
                              (and writes, which a ROM ignores) a program ROM
                              word that holds a large positive value (400h to
                              7FFFh: the game reads the energy as a signed
                              16-bit field) instead. The
                              energy word itself is never touched, so
                              switching the cheat on or off leaves the bar
                              where it is, and a new round still fills it
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
    P1 / P2 Drain all Energy   a one-shot: the energy word is set to 1

Run with the folder of the MAME ROM images (simroms: <set>_rom0.bin) to list
what each set gets.
"""

import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tunit_secrets as S                           # noqa: E402
from tunit_secrets import Prog, X, G_MK, G_MKTURBO, G_MK2, G_NBAJAM, G_NBAJAMTE, G_JDREDDP   # noqa: E402
import tunit_cheats_data                            # noqa: E402

CHEAT_SIZE = 8            # bytes per unit (the MRA's <cheats size>)
CHEAT_MAX = 8             # units switched on at once (<cheats max>, rtl/tunit_cheats.sv)
NAME_MAX = 27             # characters the OSD shows

TIMER_VALUE = 0x7FFF      # frames of the FINISH HIM wait (80h in the game)
DAMAGE_FLOOR = 0x400      # the ROM word a hit is subtracted from must be above any hit (a bar is A1h)
DAMAGE_CEIL = 0x7FFF      # ... and positive as the signed 16-bit field the game reads it with (SETF 10h,1,0)
MOVE_A10_A10 = 0x4D4A     # replaces DEC A10 (142Ah): same size, the flags of A10 >= 0
PLAYER_GAP = 0xBD0        # bits between the two players' variables (P2 - P1), as in every set


def unit(bit_addr, value, fetch=False, store=False, poke=False, mask=0xFFFF):
    """One 8-byte unit. A store entry and a one-shot take the whole word."""
    if bit_addr & 0xF:
        raise ValueError('bit address %08X is not a word' % bit_addr)
    if (store or poke) and mask != 0xFFFF:
        raise ValueError('a store entry or a one-shot covers the whole word')
    if poke and (fetch or store):
        raise ValueError('a one-shot is a plain write of main RAM')
    wa = bit_addr >> 4
    flags = (1 if fetch else 0) | (2 if store else 0) | (4 if poke else 0)
    return struct.pack('<4H', wa & 0xFFFF, ((wa >> 16) & 0xFFF) | (flags << 12), value & 0xFFFF, mask & 0xFFFF)


ROM_BASE = 0xFF800000     # bit address of the first word of the program image


def patch_unit(word_addr, value):
    """A unit for a patch of tools/tunit_secrets.py (a word address): a
    program ROM word (fetches only) or a main RAM word."""
    return unit(word_addr << 4, value, fetch=(word_addr << 4) >= ROM_BASE)


def flag_bit(addr, bit, name=None):
    """A unit that sets one bit of a flag word (the four players' bits)."""
    return unit(addr, 1 << bit, mask=1 << bit)


def fight_words(p):
    """{'state', 'p1e', 'p2e'} (bit addresses) or None.

    The round state: the FINISH HIM routine's MOVK 3,A0 / MOVE A0,@state /
    CALLR / MOVI 28h,A11. The energies: the bar set-up MOVI P1 energy,A0 /
    MOVI ..,A1 / CALLR / MOVI P2 energy,A0 / MOVI ..,A1, the second one a
    player's variables away (PLAYER_GAP)."""
    st = p.find([0x1860, 0x0580, X, X, 0x0D3F, X, 0x09CB, 0x0028])
    en = [k for k in p.find([0x09E0, X, X, 0x09E1, X, X, 0x0D3F, X, 0x09E0, X, X, 0x09E1])
          if p.u32(k + 9) - p.u32(k + 1) == PLAYER_GAP]
    if len(st) != 1 or len(en) != 1:
        return None
    return {'state': p.u32(st[0] + 2), 'p1e': p.u32(en[0] + 1), 'p2e': p.u32(en[0] + 9)}


def damage_table(p, r):
    """Bit address of the program ROM table of the two energy pointers the
    damage routine uses, or None.

    The routine (MK2 L3.1 FF8364C0): MOVE A6,A7 / SLL 5,A6 / ADDI table,A6 /
    MOVE *A6+,A6,1 (the victim's pointer: two 32-bit pointers, P1's then P2's,
    which are the two energy words) / MOVE *A6,A1,0 (the energy) / SUB A10,A1
    (the hit) / JRNN / CLR A1 / MOVE A1,*A6,0 (stored back, the flags decide
    between a hit and a knockout). In Mortal Kombat II Plus the subtraction is
    a JA to the hack's routine, which starts with the same SUB A10,A1 and
    comes back to the store, and the table has moved. The table is found by
    that code (one place in each program) and must hold the two energy words."""
    hits = p.find([0x24A6, 0x0B26, X, X, 0x96C6, 0x84C1])
    if len(hits) != 1:
        return None
    k = hits[0]
    t = p.u32(k + 2)
    ti = p.word_index(t)
    if t & 0xF or not 0 <= ti < len(p.w) - 4:
        return None
    if p.u32(ti) != r['p1e'] or p.u32(ti + 2) != r['p2e']:
        return None
    if p.w[k + 6] == 0x4541:                       # SUB A10,A1 / JRNN / CLR A1
        pass
    elif p.w[k + 6] == 0xC080:                     # the hack: JA to a routine that starts with the SUB
        j = p.word_index(p.u32(k + 7))
        if not 0 <= j < len(p.w) - 1 or p.w[j] != 0x4541:
            return None
    else:
        return None
    if p.w[k + 9] != 0x8026:                       # MOVE A1,*A6,0
        return None
    return t


def damage_hi(p, lo):
    """The high half of a pointer to a program ROM word that holds a value from
    DAMAGE_FLOOR to DAMAGE_CEIL (the lowest such pointer), for a pointer whose
    low half is lo, or None. The program ROM is the bit addresses
    FF800000-FFFFFFFF. The game reads the energy through the pointer as a
    16-bit field that is sign extended (its SETF 10h,1,0), so a value from 8000h
    on would be negative: the hit would leave a negative number and the fighter
    would be knocked out."""
    for hi in range(0xFF80, 0x10000):
        i = p.word_index(hi << 16 | lo)
        if 0 <= i < len(p.w) and DAMAGE_FLOOR <= p.w[i] <= DAMAGE_CEIL:
            return hi
    return None


def finish_wait(p, r):
    """Bit addresses of the immediates of the FINISH HIM routine's second wait
    (one, or two in Mortal Kombat II Plus), or None.

    The routine (the one that sets the round state to 3): MOVI 28h,A11 / wait /
    ... / MOVI 80h,A11 / wait / ... [MOVI 40h,A11 / wait / ...] / MOVI 200h,A11
    / the loop that waits for the move to finish. Each wait is the sub that
    exits when the finish flag is set (a move started) or the other flag is
    set (the winner hit the loser) and otherwise counts A11 down once per
    frame. The second wait is 80h frames (FFh in Mortal Kombat II
    Challenger, whose last loop is FF00h); the first 28h and the later waits stay.

    In Mortal Kombat II Plus the CALLA in front of that MOVI is a JA to a
    routine of the hack, which calls the same sub, loads A11 with 80h itself
    (140h if its longer finishing time option is on) and jumps back to the
    instruction after the MOVI: the two immediates in the routine are the live
    ones."""
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
    k = nxt[0]
    if p.w[k - 3] != 0x0D5F:                                  # not the CALLA: the Plus hack?
        if p.w[k - 3] != 0xC080:
            return None
        t = (p.u32(k - 2) - 0xFF800000) >> 4                  # JA: the hack's routine
        if not 0 <= t < len(p.w) - 0x40:
            return None
        back = [j for j in range(t, t + 0x40)                 # ends in the JA past the MOVI
                if p.w[j] == 0xC080 and p.u32(j + 1) == 0xFF800000 + 16 * (k + 2)]
        if len(back) != 1 or p.w[t] != 0x0D5F:                # starts with a CALLA
            return None
        imm = [j + 1 for j in range(t, back[0]) if p.w[j] == 0x09CB]
        if not imm or p.w[imm[0]] != p.w[k + 1]:              # MOVI 80h,A11 first (as the original)
            return None
        return [0xFF800000 + 16 * j for j in imm]
    return [0xFF800000 + 16 * (k + 1)]


def round_clock(p):
    """Bit address of the DEC A10 that counts the round clock down, or None.

    The clock process (found by its start): MOVK 9,A11 / MOVK 9,A10 / MOVE
    A10,@ones / MOVE A11,@tens, draws the digits, then the time-over test
    MOVE A10,A0 / ADD A11,A0 / JREQ, then the wait loop ... DSJS / DEC A10 /
    JRNN back to the draw / MOVK 9,A10 / DEC A11. The clock lives in the two
    registers, so the RAM words it writes (read by the time-over test of
    another routine) are not where it counts.

    In Mortal Kombat II Plus the end of that loop is a routine of the hack (a
    JA from the loop): DEC A10 / JANN back to the draw / MOVK 9,A10 / JA to the
    DEC A11, the same four instructions with long jumps."""
    st = p.find([0x192B, 0x192A, 0x058A, X, X, 0x058B, X, X])
    if len(st) != 1:
        return None
    lo = st[0]
    if not p.find([0x4D40, 0x4160], lo, lo + 0x60):           # MOVE A10,A0 / ADD A11,A0
        return None
    dec = [k for k in range(lo, lo + 0xC0)
           if p.w[k] == 0x142A and (p.w[k + 1] & 0xFF00) == 0xCF00 and
           p.w[k + 2] == 0x192A and p.w[k + 3] == 0x142B]      # DEC A10 / JRNN / MOVK 9,A10 / DEC A11
    if len(dec) == 1:
        return 0xFF800000 + 16 * dec[0]
    if dec:
        return None
    tens = [k for k in range(lo, lo + 0xC0)
            if p.w[k] == 0x142B and p.w[k + 1] == 0x4D61]      # DEC A11 / MOVE A11,A1 (draws the tens)
    if len(tens) != 1:
        return None
    t = 0xFF800000 + 16 * tens[0]
    hack = [k for k in p.find([0x142A, 0xCF80, X, X, 0x192A, 0xC080, X, X])
            if p.u32(k + 2) == t + 16 and p.u32(k + 6) == t]   # DEC A10 / JANN draw / MOVK 9,A10 / JA DEC A11
    if len(hack) != 1:
        return None
    return 0xFF800000 + 16 * hack[0]


def mk2_cheats(p, notes, drains=True):
    """The Mortal Kombat II cheats found in the program: [(menu name, [unit])]."""
    r = fight_words(p)
    if not r:
        return [], ['fight variables not found: no cheats']
    out = []
    tab = damage_table(p, r)
    if (r['p1e'] | r['p2e']) & 0xF:
        notes.append('energy not word aligned: no health cheats')
    elif tab is None:
        notes.append('damage routine\'s pointer table not found: no health cheats')
    else:
        hi1, hi2 = damage_hi(p, r['p1e'] & 0xFFFF), damage_hi(p, r['p2e'] & 0xFFFF)
        if hi1 is None or hi2 is None:
            notes.append('no program ROM word from %Xh to %Xh to point the damage at: no health cheats' % (DAMAGE_FLOOR, DAMAGE_CEIL))
        else:
            # the high half of each player's pointer (word 1 of its entry)
            out.append(('Infinite Health P1', [unit(tab + 0x10, hi1)]))
            out.append(('Infinite Health P2', [unit(tab + 0x30, hi2)]))
            notes.append('damage pointer table %08X, hits go to %04X%04X and %04X%04X' %
                         (tab, hi1, r['p1e'] & 0xFFFF, hi2, r['p2e'] & 0xFFFF))
    if not (r['p1e'] | r['p2e']) & 0xF and drains:
        out.append(('P1 Drain all Energy Now!', [unit(r['p1e'], 1, poke=True)]))
        out.append(('P2 Drain all Energy Now!', [unit(r['p2e'], 1, poke=True)]))
    notes.append('energy P1 %08X, P2 %08X' % (r['p1e'], r['p2e']))
    c = round_clock(p)
    if c is None:
        notes.append('round clock not found: no time cheat')
    else:
        out.append(('Infinite Round Time', [unit(c, MOVE_A10_A10, True)]))
        notes.append('round clock DEC A10 %08X' % c)
    w = finish_wait(p, r)
    if w is None:
        notes.append('FINISH HIM wait not found: no timer cheat')
    else:
        out.append(('Stop Finishing Move Timer', [unit(a, TIMER_VALUE, True) for a in w]))
        notes.append('FINISH HIM wait ' + ', '.join('%08X' % a for a in w))
    return out, notes


def secret_cheats(gid, p, notes):
    """The OSD items that moved to the Cheats menu, from the finders of
    tools/tunit_secrets.py (every revision of the set has its own addresses)."""
    snotes = []
    out = []
    _, patches = S.collect(gid, p, snotes)

    def by(opt):
        return [patch_unit(a, v) for a, o, v in patches if o == opt]

    def add(name, units):
        if units:
            out.append((name, units))

    if gid in (G_MK, G_MKTURBO):
        add('Always have Reptile Clues', by(S.OPT_REP_HINT))
    elif gid == G_MK2:
        add('Show Hitboxes', by(S.OPT_HITBOX))
        add('Jade Fight no Low Kick', by(S.OPT_JADE))
        add('Press Start To Fight Smoke', by(S.OPT_SMOKE))
        add('Always Play Pong', by(S.OPT_PONG))
        add('Winner Battles Noob Saibot', by(S.OPT_NOOB))
    elif gid in (G_NBAJAM, G_NBAJAMTE):
        te = gid == G_NBAJAMTE
        v = S.nba_vars(p, te, snotes)
        for pl in range(4):
            if 'big' in v:
                add('P%d Big/Huge Head' % (pl + 1) if te else 'P%d Big Head' % (pl + 1), [flag_bit(v['big'], pl)])
            if 'flag' in v:
                add('P%d Quick Hands' % (pl + 1) if te else 'P%d Powerup Intercept' % (pl + 1), [flag_bit(v['flag'], pl)])
                if te and 'max' in v:
                    add('P%d Max Power' % (pl + 1), [flag_bit(v['max'], pl)])
                if 'cnt' in v:
                    add('P%d Powerup Goal Tending' % (pl + 1) if te else 'P%d Powerup Defense' % (pl + 1),
                        [unit(v['c'][pl], 0x18 if te else 0x08)])
        if 'shot' in v:
            add('Shot Percentage', [unit(v['shot'], 1)])
        if te:
            if 'baby' in v:
                add('Baby Size Players', [unit(v['baby'], 1)])
            if 'tourn' in v:
                add('Tournament Mode', [unit(v['tourn'], 1)])
            if 'huge' in v:
                add('Huge Heads', [unit(v['huge'], S.JRUC | 3, True)])
        else:
            if 'nocpu' in v:
                add('Computer Assistance Turned', [unit(v['nocpu'], 1)])
            tank = S.nba_tank(p)
            if tank:
                add('Play Hidden 3D Tank Game', [unit(tank, S.NOP, True)])
    for n in snotes:
        if (n.startswith(('power-ups', 'Reptile')) or 'not found' in n) and n not in notes:
            notes.append(n)
    return out


def data_cheats(setname):
    """The cheats of the MAME cheat files for a set: [(menu name, [unit])]."""
    out = []
    for name, us in tunit_cheats_data.CHEATS.get(setname, []):
        out.append((name, [unit(a, v, fetch='F' in fl, store='S' in fl, poke='P' in fl, mask=m)
                           for a, v, m, fl in us]))
    return out


def build(gid, prog_bytes, setname='', plus=False):
    """([(menu name, bytes)], notes) for a set's program (the maincpu region);
    plus: Mortal Kombat II Plus (the hack hides the items, only its energy,
    clock and timer cheats are made)."""
    if gid not in (G_MK, G_MKTURBO, G_MK2, G_NBAJAM, G_NBAJAMTE, G_JDREDDP):
        return [], []
    notes = []
    p = Prog(prog_bytes)
    cheats = []
    if gid == G_MK2:
        cheats, notes = mk2_cheats(p, notes, drains=not plus)
    if not plus:
        cheats += secret_cheats(gid, p, notes)
        cheats += data_cheats(setname)
    seen = set()
    out = []
    for name, us in sorted(cheats, key=lambda c: c[0].lower()):
        if name in seen:
            raise ValueError('%s: two cheats named %r' % (setname, name))
        seen.add(name)
        data = b''.join(us)
        assert len(name) <= NAME_MAX and len(data) % CHEAT_SIZE == 0 and len(us) <= CHEAT_MAX, name
        out.append((name, data))
    if out:
        notes.append('%d cheats' % len(out))
    return out, notes


SETS = {                  # simroms set name prefix -> game id
    'mktturbo': G_MKTURBO, 'mk2': G_MK2, 'mk': G_MK, 'nbajamte': G_NBAJAMTE, 'nbajam': G_NBAJAM,
    'jdreddp': G_JDREDDP,
}


def main():
    d = sys.argv[1] if len(sys.argv) > 1 else 'simroms'
    for f in sorted(os.listdir(d)):
        if not f.endswith('_rom0.bin'):
            continue
        name = f[:-9]
        gid = next((g for k, g in SETS.items() if name.startswith(k)), None)
        if gid is None:
            continue
        with open(os.path.join(d, f), 'rb') as fh:
            prog = fh.read(0x100000)
        cheats, notes = build(gid, prog, name)
        print('%-12s %s' % (name, '; '.join(notes)))
        for cname, data in cheats:
            print('    %-27s %s' % (cname, data.hex().upper()))


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
tunit_secrets.py - the per-set secrets table (MRA ROM index 1)

    python3 tools/tunit_secrets.py <game id> <maincpu.bin> [--out table.bin]

Builds the table rtl/tunit_secrets.sv reads: the game id, the read patches
and the codes for the OSD Secrets page. Every address and code is taken from
the set's own program ROM by looking for the code that uses it, so each
revision gets its own (MK2 L1.1 and L1.4 have a different EJB code from the
later revisions, and the RAM variables move between revisions). A feature
whose code is not found is left out of that set's table, and the script
says so. mra_gen.py calls build() for every set; run alone, it prints what
it finds in a region dump (tools/mame/region_dump.lua).

What the games hide (34010 addresses below are MK2 L3.1, NBA Jam 3.01,
TE 4.0, Judge Dredd TA1, MK 5.0):

  MK, MK Turbo   EJB menu: during the attract mode, Block presses on player
                 1 and 2 in the order of a table the switch handlers walk
                 (5 P1, 10 P2, 2 P1, 1 P2, 2 P1, 3 P2, 4 P1); each press
                 within 16 frames of the last (FFDD0900). Holding P1 High
                 Punch while the last press goes in shows a copyright screen
                 ("THIS IS MORTAL KOMBAT") until it is released, then the menu.
  MK2            EJB menu: as MK, table 5 P1, 10 P2, 2 P1, 8 P2, 2 P1 (L2.0
                 and later) (FFA1CF60). L1.1 and L1.4 have the menu, the
                 code handler and a table (MK's) but no switch handler calls
                 it: while the code plays, the Block entries of the switch
                 tables are patched to point at the handler.
                 Security screen ("THIS VERSION PASSED THE SECURITY TEST"):
                 shown when both players hold a button combination for 320
                 frames at the start of an attract cycle (FFA1D970); the two
                 branches that leave when it is not held are patched to NOPs.
                 Hitboxes: a debug flag in RAM (0x01061FB0) makes the game
                 draw each attack's hit box (FF835620); patched to read 1.
                 Pong: at two-player battle 250 the VS screen reads "KOMBAT
                 ZONE: BACK IN TIME" and, after the first round, "YOU HAVE
                 REACHED THE OUTER LIMITS OF THE TOURNAMENT..." and a game
                 of Pong (FF818EB0); the battle counter (0x01061B40) is
                 patched to read 250.
                 Noob Saibot: after each round of a two-player battle the
                 round's winner fights Noob Saibot ("INCREDIBLE WINNING
                 STREAK!!") when that player's win streak is 50 (FFA188F0;
                 L3.0 and later, the hacks compare with 6). The long JRNE
                 that leaves when it is not gets displacement 0, so it goes
                 on into the fight either way.
  NBA Jam, TE    Secret Midway menu: in the attract mode both players hold
                 Up + all three buttons, then exactly 52 frames later Down
                 (FF9995B0); the design team screen follows, and while it is
                 shown (3.01, TE) a second code of single presses from a table
                 of IN0 values (FF9215F0); older revisions go straight to the
                 menu (audits).
  Judge Dredd    Secret audits: in the attract mode P1 Down + P2 Right with
                 one set of buttons, then another (FFD3BCD0); six pages of
                 audits, each turned by any press. Holding both start buttons
                 when the last page ends shows the staff credits (FFCFBCD0).

Table layout: rtl/tunit_secrets.sv.

Copyright (C) 2026 Gm0rk - GPL-3.0-or-later
"""

import struct
import sys

G_MK, G_MKTURBO, G_MK2, G_NBAJAM, G_NBAJAMTE, G_JDREDDP = range(6)

FORMAT = 1
STEP_BASE = 0x20                 # first code step (word index)
TABLE_WORDS = 512
N_PATCH = 8

# OSD options (O[16], O[17], O[18]; O[19] is option 6); 4 / 5: while code 1 /
# code 2 plays
OPT_SECURITY, OPT_HITBOX, OPT_PONG = 1, 2, 3
OPT_CODE1, OPT_CODE2 = 4, 5
OPT_NOOB = 6

LAST, START1, START2 = 0x8000, 0x0100, 0x0200

X = None                         # wildcard in a signature


def bit_address(i):
    """34010 bit address of program ROM word i."""
    return 0xFF800000 + i * 16


class Prog:
    """The maincpu region as 16-bit words, with signature search."""

    def __init__(self, data):
        self.d = data
        self.w = struct.unpack('<%dH' % (len(data) // 2), data[:len(data) // 2 * 2])

    def find(self, pat):
        w, n, res = self.w, len(pat), []
        for i in range(len(w) - n):
            if w[i] != pat[0]:
                continue
            if all(p is None or w[i + j] == p for j, p in enumerate(pat)):
                res.append(i)
        return res

    def u32(self, i):
        return self.w[i] | (self.w[i + 1] << 16)

    def byte_at(self, bitaddr):
        return self.d[(bitaddr - 0xFF800000) // 8]

    def word_index(self, bitaddr):
        return (bitaddr - 0xFF800000) // 16


# --------------------------------------------------------------------------
# Codes (lists of steps: IN0 value active high, frames, flags)
# --------------------------------------------------------------------------

MK_BLOCK = (0x0020, 0x2000)      # P1, P2 Block (IN0 bits 5, 13)
MK_HP1 = 0x0010                  # P1 High Punch


def press_code(seq, values, on=2, off=2):
    """Single presses: one entry of values per sequence element."""
    steps = []
    for who in seq:
        steps += [(values[who], on, 0), (0, off, 0)]
    return steps


def ejb_table(p, proc_id):
    """The EJB code table the attract-mode Block handler walks, found from
    the handler's start: CLR A5 / JR / MOVK 1,A5 / MOVI table,A10 /
    MOVI done,A11 / CLR A1 / NOT A1 / MOVI id,A0. Returns the sequence (0 P1,
    1 P2), the table and menu addresses, and the handler's address (its P2
    entry is two words on)."""
    hits = p.find([0x56A5, 0xC001, 0x1825, 0x09EA, X, X, 0x09EB, X, X, 0x5621, 0x03E1, 0x09C0, proc_id])
    if len(hits) != 1:
        return None
    tab = p.u32(hits[0] + 4)
    seq = []
    for k in range(64):
        b = p.byte_at(tab + 8 * k)
        if b == 0x44:
            return seq, tab, p.u32(hits[0] + 7), bit_address(hits[0])
        if b not in (0, 1):
            return None
        seq.append(b)
    return None


def referenced(p, addr):
    """True if a 32-bit word in the program ROM holds addr (a jump or a
    pointer to it)."""
    return bool(p.find([addr & 0xFFFF, addr >> 16]))


def block_hooks(p, handler, notes):
    """Patches that point the P1 and P2 Block switch handlers at the EJB
    code's handler while code 1 plays, for revisions that have the handler
    but never call it (MK2 L1.1, L1.4). The switch tables give each IN0 bit
    a flag word (0300 player 1, 0301 player 2) and a handler address; Block
    is the sixth entry (IN0 bits 5 and 13)."""
    patches = []
    for flag, target in ((0x0300, handler), (0x0301, handler + 0x20)):
        tabs = [i for i in p.find([flag, X, X] * 7)
                if (i < 3 or p.w[i - 3] != flag)
                and all(p.w[i + 2 + 3 * k] >= 0xFF80 for k in range(7))]
        if len(tabs) != 1:
            notes.append('switch table %04X not found' % flag)
            return []
        ptr = tabs[0] + 3 * 5 + 1                  # Block entry's handler address
        patches.append((bit_address(ptr) >> 4, OPT_CODE1, target & 0xFFFF))
        patches.append((bit_address(ptr + 1) >> 4, OPT_CODE1, target >> 16))
    notes.append('EJB code handler not called: Block handlers pointed at it while the code plays')
    return patches


def mk_codes(p, notes):
    t = ejb_table(p, 0x5001)
    if not t:
        notes.append('EJB code table not found')
        return [], None
    seq, tab, done, handler = t
    notes.append('EJB code %08X (%d presses), menu %08X' % (tab, len(seq), done))
    code1 = press_code(seq, MK_BLOCK)
    if not referenced(p, handler):
        notes.append('EJB code handler not called')
        return [], None
    # the copyright screen: the last press with P1 High Punch held, and High
    # Punch held on for four seconds (the menu follows its release); the menu
    # code reads IN0 bit 4 right after the code completes
    code2 = None
    if p.find([0x07A0, 0x0000, 0x0160, 0x03E0, 0x1F60]):    # MOVE @IN0,A0,1 / NOT A0 / BTST 4h,A0
        code2 = code1[:-2] + [(MK_BLOCK[seq[-1]] | MK_HP1, 2, 0), (MK_HP1, 240, 0), (0, 2, 0)]
    else:
        notes.append('copyright screen check not found')
    # both codes succeed when the CPU reaches the menu code
    return [(code1, done), (code2, done) if code2 else None], None


def mk2_codes(p, notes):
    patches = []
    t = ejb_table(p, 0x0010)
    if t:
        seq, tab, done, handler = t
        code1 = (press_code(seq, MK_BLOCK), done)
        notes.append('EJB code %08X (%d presses), menu %08X' % (tab, len(seq), done))
        if not referenced(p, handler):
            hooks = block_hooks(p, handler, notes)
            patches += hooks
            if not hooks:
                code1 = None
    else:
        code1 = None
        notes.append('EJB code table not found')

    # security screen: ANDI 247F7Fh,A0 / ANDI 33h,A1 / CMPI 6131h,A0 / JRNE /
    # CMPI 21h,A1 / JRNE -> both JRNEs become NOP (0300)
    h = p.find([0x0B80, 0x8080, 0xFFDB, 0x0B81, 0xFFCC, 0xFFFF, 0x0B40, 0x9ECE, X, 0x0B41, 0xFFDE, X])
    if len(h) == 1 and p.w[h[0] + 8] >> 8 == 0xCB and p.w[h[0] + 11] >> 8 == 0xCB:
        for k in (8, 11):
            patches.append((bit_address(h[0] + k) >> 4, OPT_SECURITY, 0x0300))
        notes.append('security screen branches %08X %08X' % (bit_address(h[0] + 8), bit_address(h[0] + 11)))
    else:
        notes.append('security screen check not found')

    # hitboxes: MOVE @flag,A14 / JREQ / MMTM SP,A0,A1,A4,A8 / CLR A1 / NOT A1 /
    # MOVI 800h,A0
    h = p.find([0x05AE, X, X, X, 0x098F, 0xC880, 0x5621, 0x03E1, 0x09C0, 0x0800])
    if len(h) == 1:
        flag = p.u32(h[0] + 1)
        patches.append((flag >> 4, OPT_HITBOX, 0x0001))
        notes.append('hitbox flag %08X' % flag)
    else:
        notes.append('hitbox flag not found')

    # Pong: the battle counter (MOVE @n,A2 / ADDK 1,A2 / MOVE A2,@n / CLR A0 /
    # MOVE A0,@round) where a new battle starts, read and compared with 250
    # (MOVE @n,A0 / CMPI FAh,A0) before each round of a two-player battle
    h = [i for i in p.find([0x05A2, X, X, 0x1022, 0x0582, X, X, 0x5600, 0x0580, X, X])
         if p.w[i + 1] == p.w[i + 5] and p.w[i + 2] == p.w[i + 6]]
    if len(h) == 1:
        n = p.u32(h[0] + 1)
        if p.find([0x05A0, n & 0xFFFF, n >> 16, 0x0B40, 0xFF05]):
            patches.append((n >> 4, OPT_PONG, 0x00FA))
            notes.append('battle counter %08X' % n)
        else:
            notes.append('battle 250 check not found')
    else:
        notes.append('battle counter not found')

    # Noob Saibot: CALLA (players) / CMPI 2h,A0 / JRNE (long) / MOVE @p1,A1 /
    # MOVE @winner,A0 / CMPI 1h,A0 / JREQ / MOVE @p2,A1 / CMPI 50,A1 / JRNE
    # (long): the last JRNE's displacement word becomes 0
    h = p.find([0x0D5F, X, X, 0x0B40, 0xFFFD, 0xCB00, X, 0x05A1, X, X, 0x05A0, X, X,
                0x0B40, 0xFFFE, 0xCA03, 0x05A1, X, X, 0x0B41, X, 0xCB00, X])
    if len(h) == 1:
        patches.append((bit_address(h[0] + 22) >> 4, OPT_NOOB, 0x0000))
        notes.append('Noob Saibot check %08X (%d wins)' % (bit_address(h[0]), ~p.w[h[0] + 20] & 0xFFFF))
    else:
        notes.append('Noob Saibot check not found')
    return [code1], patches


def nba_codes(p, notes):
    # first part: CMPI 7171h,A0 (Up + all buttons, both players) / ...
    # CMPI 202h,A0 (Down, both players) 52 frames later
    h = p.find([0x0B40, 0x8E8E, X, 0x09C1, 0x0035, 0x1421, 0x0581, X, X, X, 0x0B40, 0xFDFD])
    if not h:
        notes.append('secret menu code not found')
        return [], None
    code = [(0x7171, 3, 0), (0, 1, 0), (0x0202, 90, 0), (0, 20, 0)]
    # second part (3.01, TE): MOVI table,A9 / ... / MOVE @1600000h,A0 /
    # ZEXT A0 / CMPI FFFFh,A0 / ...: a table of IN0 values, one press each
    h2 = p.find([0x09E9, X, X, 0x1820, 0x0D5F, X, X, 0x05A0, 0x0000, 0x0160, 0x0520, 0x0B60, 0x0000, 0xFFFF])
    if len(h2) == 1:
        tab = p.u32(h2[0] + 1)
        i = p.word_index(tab)
        vals = []
        while p.w[i] and len(vals) < 32:
            vals.append(~p.w[i] & 0xFFFF)
            i += 1
        for v in vals:
            code += [(v, 3, 0), (0, 3, 0)]
        notes.append('secret menu code, second part %08X (%d presses)' % (tab, len(vals)))
    else:
        notes.append('secret menu code (no second part)')
    return [(code, None)], None


def jd_codes(p, notes):
    # MOVE @IN0,A0 / CMPI 679Dh,A0 / JRNE (first buttons, arms the code), then
    # MOVE A0,A1 / NOT A0 / ANDI F0Fh,A0 / CMPI 802h,A0 (P1 Down, P2 Right
    # held) / JRNE / CMPI 37CDh,A1 (second buttons). A CMPI immediate is
    # stored inverted: for these active-low ports, the pressed bits.
    a = [i for i in p.find([0x05A0, 0x0000, 0x0160, 0x0B40, X, X, 0x0580]) if p.w[i + 5] >> 8 == 0xCB]
    b = p.find([0x4C01, 0x03E0, 0x0B80, X, X, 0x0B40, X, X, 0x0B41, X])
    if len(a) != 1 or len(b) != 1:
        notes.append('secret audits code not found')
        return [], None
    first = p.w[a[0] + 4]
    dirs = ~p.w[b[0] + 6] & 0xFFFF
    second = p.w[b[0] + 9]
    notes.append('secret audits code %04X, %04X with %04X held' % (first, second, dirs))
    code1 = [(dirs, 10, 0), (first, 10, 0), (dirs, 5, 0), (second, 10, 0), (dirs, 25, 0), (0, 2, 0)]
    # staff credits: NOT A14 / ANDI 240000h,A14 / CMPI 240000h,A14 (both start
    # buttons held) when the audits end; the six pages are turned with P1 Kick
    code2 = None
    if p.find([0x03EE, 0x0B8E, 0xFFFF, 0xFFDB, 0x0B6E, 0xFFFF, 0xFFDB]):
        code2 = code1[:-1] + [(0, 40, 0)]
        for k in range(6):
            code2 += [(0x0040, 8, 0), (0, 32, 0)]
        code2 += [(0, 60, START1 | START2), (0, 2, 0)]
    else:
        notes.append('staff credits check not found')
    return [(code1, None), (code2, None) if code2 else None], None


# --------------------------------------------------------------------------
# Table
# --------------------------------------------------------------------------

def build(gid, prog_bytes):
    """Table bytes and notes for a set: game id gid, its maincpu region."""
    p = Prog(prog_bytes)
    notes = []
    if gid in (G_MK, G_MKTURBO):
        codes, patches = mk_codes(p, notes)
    elif gid == G_MK2:
        codes, patches = mk2_codes(p, notes)
    elif gid in (G_NBAJAM, G_NBAJAMTE):
        codes, patches = nba_codes(p, notes)
    elif gid == G_JDREDDP:
        codes, patches = jd_codes(p, notes)
    else:
        codes, patches = [], None
    patches = patches or []
    if len(patches) > N_PATCH:
        raise ValueError('too many patches')

    t = [0] * TABLE_WORDS
    t[0] = gid
    t[1] = FORMAT
    for k, (addr, opt, val) in enumerate(patches):
        t[2 + 3 * k] = addr & 0xFFFF
        t[3 + 3 * k] = (opt << 12) | (addr >> 16)
        t[4 + 3 * k] = val
    pos = STEP_BASE
    for n, c in enumerate(codes[:2]):
        if not c or not c[0]:
            continue
        code, done = c
        t[26 + n] = pos
        if done:
            t[28 + 2 * n] = (done >> 4) & 0xFFFF
            t[29 + 2 * n] = done >> 20
        for k, (v, frames, flags) in enumerate(code):
            if pos + 2 > TABLE_WORDS:
                raise ValueError('codes do not fit')
            t[pos] = v
            t[pos + 1] = flags | min(frames, 255) | (LAST if k == len(code) - 1 else 0)
            pos += 2
    used = pos if pos > STEP_BASE else STEP_BASE if patches else 2
    data = struct.pack('<%dH' % used, *t[:used])
    return data, notes


def part_hex(data, per_line=32, indent='\t\t'):
    """The table as MRA <part> hex lines."""
    lines = []
    for i in range(0, len(data), per_line):
        lines.append(indent + ' '.join('%02X' % b for b in data[i:i + per_line]))
    return lines


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('gid', type=int)
    ap.add_argument('maincpu')
    ap.add_argument('--out')
    a = ap.parse_args()
    data, notes = build(a.gid, open(a.maincpu, 'rb').read())
    for n in notes:
        print(n)
    print('%d bytes' % len(data))
    if a.out:
        open(a.out, 'wb').write(data)


if __name__ == '__main__':
    main()

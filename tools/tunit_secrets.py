#!/usr/bin/env python3
"""
tunit_secrets.py - the per-set secrets table (MRA ROM index 1)

    python3 tools/tunit_secrets.py <game id> <maincpu.bin> [--out table.bin]
    python3 tools/tunit_secrets.py --gen      (rtl/tunit_secrets_osd.svh)
    python3 tools/tunit_secrets.py --codes nbajam|nbajamte
                                              (the codes the window lists)

Builds the table rtl/tunit_secrets.sv reads: the game id, the read patches
and the codes for the OSD's hidden items and cheat codes. Every address and
code is taken from the set's own program ROM by looking for the code that
uses it, so each revision gets its own (MK2 L1.1 and L1.4 have a different
EJB code from the later revisions, and the RAM variables move between
revisions). A feature whose code is not found is left out of that set's
table, and the script says so. mra_gen.py calls build() for every set; run
alone, it prints what it finds in a region dump
(tools/mame/region_dump.lua). --gen writes the NBA Jam / TE lines of the OSD
(View Secret Players and the Cheat Codes & Hidden Items page); CHEATS
below is what the Secret Player List window (tools/tunit_window.py) and the
game pages show of the codes.

What the games hide (34010 addresses below are MK2 L3.1, NBA Jam 3.01,
TE 4.0, Judge Dredd TA1, MK 5.0):

  MK, MK Turbo   EJB menu: during the attract mode, Block presses on player
                 1 and 2 in the order of a table the switch handlers walk
                 (5 P1, 10 P2, 2 P1, 1 P2, 2 P1, 3 P2, 4 P1); each press
                 within 16 frames of the last (FFDD0900). Holding P1 High
                 Punch while the last press goes in shows a copyright screen
                 ("THIS IS MORTAL KOMBAT") until it is released, then the menu.
                 Reptile: after each match the player wins, the next-stage
                 routine advances the stage (@01051820, 3 = The Pit), counts
                 down the moon cooldown (@010519A0: 40 matches after
                 power-up, reloaded with 40 when it has reached 0 and the
                 match just won was on The Pit) and calls the Reptile check
                 (FFCB1FF0): one player, the match just won on The Pit, the
                 cooldown just reloaded, no Block pressed (@01052950), two
                 flawless rounds, a fatality (@01051880). Carry set: his
                 fight (FFCB5550, which sets his flag @01052940 to 1). The
                 Pit's background starts the silhouettes crossing the moon
                 (FFCB8BB0) when the cooldown is 0, outside the attract mode.
                 Before each round the GREEN NINJA COUNTER audit counts up;
                 at 2000 Reptile drops in with one of nine hints (FFCA12C0)
                 and the game clears all the audits. Turbo Ninja's check has
                 no one-player, cooldown or flawless test, and takes the
                 first stage as well as The Pit. The options patch the
                 check's first test after the one-player one to SETC / RETS
                 (Reptile Fight Next), the two cooldown branches to NOPs
                 (Moon Silhouettes Always; Turbo Ninja: the moon's only),
                 and the counter's branch to a NOP and a jump over the audit
                 clearing (Reptile Hints Always).
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
                 Jade: at the end of a round of a one-player game the
                 winner fights Jade ("NOW YOU MUST BATTLE WITH AN
                 UNDISCOVERED WARRIOR...") when the battle is the one before
                 the "?" on the tower (@1061B30 = 10) and the round was won
                 with Low Kicks only (four move counters 0) (FFA199F0). The
                 tower check becomes a NOP and the first counter check a jump
                 past the others. The game then sets the tower to 12 itself.
                 Smoke: Start with Down held during a fight brings Smoke
                 ("YOU HAVE FOUND THE PASSAGE FROM THE OUTWORLD TO THE EARTH
                 REALM") on The Portal (stage 7) while the "Toasty!" man shows
                 (FFA19FD0, from the Start switch handlers). The stage check
                 becomes a jump past the stage and time checks. Both L2.0 and
                 later (the hacks move Jade's battle and drop the stage check).
  NBA Jam, TE    Secret Midway menu: in the attract mode both players hold
                 Up + all three buttons, then exactly 52 frames later Down
                 (FF9995B0); the design team screen follows, and while it is
                 shown (3.01, TE) a second code of single presses from a table
                 of IN0 values (FF9215F0); older revisions go straight to the
                 menu (audits).
                 Secret players: after the initials and birthday a player
                 enters for record keeping, the game compares them with a
                 table (NBA Jam: 13 entries, FF963400; TE: 56-69 by revision,
                 FF9DF3D0) and, on a match, plays as that person. The core
                 does not patch this: tools/tunit_splist.py reads the tables
                 for the Secret Player List window (tools/tunit_window.py).
                 Power-ups (Tonight's Matchup codes): RAM flags read as set
                 for all four players: big heads, power-up interceptions (NBA
                 Jam) / quick hands, max power, baby size (TE), the shot
                 percentage display and no computer assistance; power-up
                 defense (NBA Jam: counter 8) and goaltending (TE: counter
                 24) by jumping their counter checks, huge heads (TE: counter
                 6) the same way. Found from the code that clears and sets
                 them (FF906D00 / FF9380D0, the tip-off code FF8592F0 /
                 FF8762A0).
                 Tank game (NBA Jam 1.00, 2.00, 3.01): a hidden 3D tank game
                 ("YOU ARE DEAD!") instead of the tip-off when, as the court
                 is set up after the match-up, P1 holds Down + Turbo + Shoot
                 + Pass and P2 Turbo + Shoot + Pass (FF83D190: IN0 AND 7072h;
                 3.01 once a game). Code 2, held until the CPU starts the
                 tank game (FF8E1010).
                 Tournament mode (TE): any player holding Right + Turbo +
                 Shoot + Pass on the match-up screen (FF939250) turns off
                 the power-ups, the computer's assistance and the secrets
                 for the game ("TOURNAMENT MODE / NO CPU ASSISTANCE,
                 POWERUPS, OR SECRETS ALLOWED!" at the tip-off). Code 2,
                 held until the CPU takes it.
  Judge Dredd    Secret audits: in the attract mode P1 Down + P2 Right with
                 one set of buttons, then another (FFD3BCD0); six pages of
                 audits, each turned by any press. Holding both start buttons
                 when the last page ends shows the staff credits (FFCFBCD0).

Table layout: rtl/tunit_secrets.sv.

Copyright (C) 2026 Gm0rk - GPL-3.0-or-later
"""

import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

G_MK, G_MKTURBO, G_MK2, G_NBAJAM, G_NBAJAMTE, G_JDREDDP = range(6)

FORMAT = 1
STEP_BASE = 0x20                 # first code step (word index)
TABLE_WORDS = 512
N_PATCH = 8                      # patches 0-7 at words 2-25

# OSD options (O[16], O[17], O[18]; O[19] is option 6); 4 / 5: while code 1 /
# code 2 plays
OPT_SECURITY, OPT_HITBOX, OPT_PONG = 1, 2, 3
OPT_CODE1, OPT_CODE2 = 4, 5
OPT_NOOB, OPT_JADE, OPT_SMOKE = 6, 7, 8           # O[19], O[20], O[21]
# MK, MK Turbo: Reptile Fight Next (T[41], on until his fight starts), Moon
# Silhouettes Always (O[42]), Reptile Hints Always (O[43]); program ROM
# patches, which the board applies to instruction fetches only
OPT_REP_NEXT, OPT_REP_MOON, OPT_REP_HINT = 1, 2, 3
# NBA Jam / TE: option codes of the table; the top level maps each game's
# OSD bits to the option slots (codes 1-3, 6-13)
NJ_BIG, NJ_DEF, NJ_INT, NJ_SHOT, NJ_NOCPU = 1, 2, 3, 6, 7
TE_BIG, TE_HUGE, TE_BABY, TE_MAX, TE_QUICK, TE_GOAL, TE_SHOT, TE_NOCPU = 1, 2, 3, 6, 7, 8, 9, 10
NOP, JRUC = 0x0300, 0xC000
SETC, RETS = 0x0DE0, 0x0960

# OSD (rtl/tunit_secrets_osd.svh): status bits and the menu mask bits of
# the two games; the top level maps the bits to the option slots of
# rtl/tunit_secrets.sv
OSD_VIEW = 115                  # O[115] View Secret Players: Off, On (the pages: rtl/tunit_mlpage.sv, tools/tunit_window.py)
OSD_PLUS_VIEW = 116             # O[116] View Secrets (Mortal Kombat II Plus): Off, On (the pages: tools/tunit_plus.py)
MASK_PLUS = 'F'                 # status_menumask bit 15: Mortal Kombat II Plus
OSD_PAGE = 7                     # the Cheat Codes & Hidden Items page
OSD_HEADS = 48                   # NBA Jam: Big Heads; TE: O[49:48] Head Size
OSD_DEF = 50                     # NBA Jam: Power-Up Defense; TE: Power-Up Goaltending
OSD_INT = 51                     # NBA Jam: Power-Up Interceptions; TE: Quick Hands
OSD_SHOT = 52                    # Shot Percentage
OSD_NOCPU = 53                   # No CPU Assistance
OSD_BABY = 54                    # TE: Baby Size Players
OSD_MAX = 55                     # TE: Max Power
MASK_NBA, MASK_NJ, MASK_TE = '6', 'C', 'D'

LAST, START1, START2 = 0x8000, 0x0100, 0x0200
UNTIL = 0x8000                   # first-step word: end at the success fetch, no retries

X = None                         # wildcard in a signature


def bit_address(i):
    """34010 bit address of program ROM word i."""
    return 0xFF800000 + i * 16


class Prog:
    """The maincpu region as 16-bit words, with signature search."""

    def __init__(self, data):
        self.d = data
        self.w = struct.unpack('<%dH' % (len(data) // 2), data[:len(data) // 2 * 2])

    def find(self, pat, lo=0, hi=None):
        """Word indexes where pat (None: any word) starts, in [lo, hi)."""
        w, n, res = self.w, len(pat), []
        hi = len(w) - n if hi is None else min(hi, len(w) - n)
        for i in range(lo, hi):
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


def s16(v):
    return v - 0x10000 if v & 0x8000 else v


def mk_reptile(p, notes):
    """MK's Reptile patches (program ROM words, OPT_REP_*) and his flag's bit
    address (the fight sets it to 1), or None if the set has no Reptile.
    The same scan as the Y Unit core's (tools/yunit_fmoves.py)."""
    w = p.w
    patches = []
    # his fight: MMFM SP,A0 / MOVI 24h,A0 / CALLA (REPTILE BATTLES audit),
    # entered by CALLR check / JRC fight
    chk = setup = None
    for s in p.find([0x09AF, 0x0001, 0x09C0, 0x0024, 0x0D5F, X, X]):
        for i in p.find([0xC800, X]):
            if i >= 2 and i + 2 + s16(w[i + 1]) == s and w[i - 2] == 0x0D3F:
                chk, setup = i + s16(w[i - 1]), s
    if chk is None:
        notes.append('Reptile fight not found')
        return None
    # check: CALLR one player / MOVE A0,A0 / JREQ (Turbo Ninja: NOP) /
    # MOVE @stage,A0 ...: SETC / RETS after the one-player test
    if not (w[chk] == 0x0D3F and w[chk + 2] == 0x4C00 and (w[chk + 3] >> 8 == 0xCA or w[chk + 3] == NOP)
            and w[chk + 4] == 0x05A0):
        notes.append('Reptile check not found')
        return None
    patches += [(bit_address(chk + 4) >> 4, OPT_REP_NEXT, SETC), (bit_address(chk + 5) >> 4, OPT_REP_NEXT, RETS)]
    # his flag: MOVK 1,A0 / MOVE A0,@flag in the fight's setup
    fl = p.find([0x1820, 0x0580, X, X], setup, setup + 80)
    if not fl:
        notes.append('Reptile flag not found')
        return None
    flag = p.u32(fl[0] + 2)
    # moon: MOVE @state,A0 / CMPI 1h,A0 / JREQ / MOVE @cooldown,A0 / JRNE /
    # MOVI 2000h,A1 / MOVI proc,A7 / CALLA: the JRNE becomes a NOP, and so
    # does the check's MOVE @cooldown,A0 / CMPI 28h,A0 / JRNE (not in Turbo
    # Ninja)
    m = p.find([0x05A0, X, X, 0x0B40, 0xFFFE, X, 0x05A0, X, X, X, 0x09C1, 0x2000, 0x09E7, X, X, 0x0D5F])
    if len(m) != 1 or w[m[0] + 9] >> 8 != 0xCB:
        notes.append('moon silhouettes not found')
        return None
    patches.append((bit_address(m[0] + 9) >> 4, OPT_REP_MOON, NOP))
    for i in p.find([0x05A0, w[m[0] + 7], w[m[0] + 8], 0x0B40, 0xFFD7, X], chk, chk + 40):
        if w[i + 5] >> 8 == 0xCB:
            patches.append((bit_address(i + 5) >> 4, OPT_REP_MOON, NOP))
    # hints: CMPI 7D0h,A1 / JRC / MMFM SP,A0 / MOVE A0,-*A12 / MOVI 10h,A0 /
    # CALLA (clear the audits) ... MOVI 201Eh,A1 (the hint process): the JRC
    # becomes a NOP, the MOVI 10h a JRUC to the MOVI 201Eh
    h = p.find([0x0B41, 0xF82F, X, 0x09AF, 0x0001, 0xA20C, 0x09C0, 0x0010])
    if len(h) != 1 or w[h[0] + 2] >> 8 != 0xC8:
        notes.append('Reptile hints not found')
        return None
    patches.append((bit_address(h[0] + 2) >> 4, OPT_REP_HINT, NOP))
    t = p.find([0x09C1, 0x201E], h[0] + 6, h[0] + 30)
    disp = t[0] - (h[0] + 7) if len(t) == 1 else 0
    if not 0 < disp < 0x80:
        notes.append('Reptile hint process not found')
        return None
    patches.append((bit_address(h[0] + 6) >> 4, OPT_REP_HINT, JRUC | disp))
    notes.append('Reptile check %08X, flag %08X, %d patches' % (bit_address(chk), flag, len(patches)))
    return patches, flag


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

    # Jade: MOVE @tower,A0 / CMPI n,A0 / JRNE / CALLA (players) / CMPI 2h,A0 /
    # JREQ / six MOVIs (player 1's energy, counters, flag) / MOVE @winner,A14 /
    # CMPI 1h,A14 / JREQ / six MOVIs (player 2's) / MOVE *A5,A5 / CMPI 1h,A5 /
    # JRNE / MOVE *A1,A1 / JRNE / ... four counters ... / MMFM SP,A0. The
    # tower JRNE (word 5) becomes a NOP, the first counter JRNE (word 59) a
    # JRUC to the MMFM (+6 words).
    regs6 = []
    for r in range(6):
        regs6 += [0x09E0 + r, X, X]
    h = p.find([0x05A0, X, X, 0x0B40, X, X, 0x0D5F, X, X, 0x0B40, 0xFFFD, X] + regs6 +
               [0x05AE, X, X, 0x0B4E, 0xFFFE, X] + regs6 +
               [0x84A5, 0x0B45, 0xFFFE, X, 0x8421, X, 0x8442, X, 0x8463, X, 0x8484, X, 0x09AF, 0x0001])
    if len(h) == 1 and all(p.w[h[0] + k] >> 8 == 0xCB for k in (5, 57, 59, 61, 63, 65)):
        patches.append((bit_address(h[0] + 5) >> 4, OPT_JADE, 0x0300))
        patches.append((bit_address(h[0] + 59) >> 4, OPT_JADE, 0xC006))
        notes.append('Jade check %08X (battle %d)' % (bit_address(h[0]), ~p.w[h[0] + 4] & 0xFFFF))
    else:
        notes.append('Jade check not found')

    # Smoke: MOVI p1,A3 / MOVE A0,A14 / JREQ / MOVI p2,A3 / MOVE *A3,A3 /
    # CMPI 1h,A3 / JRNE / MOVE @mode,A0 / CMPI 2h,A0 / JRNE / MOVE @stage,A0 /
    # CMPI 7h,A0 / JRNE / MOVE @toasty,A0 / MOVE @time,A1 / SUB / ABS /
    # CMPI 40h,A1 / JRHI / MOVE @IN0,A0. The MOVE @stage (word 20) becomes a
    # JRUC to the IN0 read (+18 words).
    h = p.find([0x09E3, X, X, 0x4C0E, 0xCA03, 0x09E3, X, X, 0x8463, 0x0B43, 0xFFFE, 0xCB00, X,
                0x05A0, X, X, 0x0B40, 0xFFFD, 0xCB00, X, 0x05A0, X, X, 0x0B40, X, X, X,
                0x05A0, X, X, 0x05A1, X, X, 0x4401, 0x0381, 0x0B41, X, 0xC300, X, 0x07A0, 0x0000, 0x0160])
    if len(h) == 1:
        patches.append((bit_address(h[0] + 20) >> 4, OPT_SMOKE, 0xC012))
        notes.append('Smoke check %08X (stage %d)' % (bit_address(h[0]), ~p.w[h[0] + 24] & 0xFFFF))
    else:
        notes.append('Smoke check not found')
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


def nba_vars(p, te, notes):
    """NBA Jam / TE power-up variables, found in the program: a dict with
    'big' (the word of the four players' big head bits, one bit each) and,
    when the tip-off code was found, 'flag' (interceptions / TE: quick hands,
    a bit per player), 'c' (the four players' code counters, one word each
    10h bits apart), 'shot', 'nocpu' and, for TE, 'tourn', 'baby', 'max' (max
    power: a bit per player); 'cnt' / 'huge' are the bit addresses of the
    counter check's branch (power-up defense, TE: goaltending) and of TE's
    huge heads check. An empty dict if the variables were not found."""
    v_ = {}
    # the variables the matchup screen clears: CLR A0 / MOVE A0,@c0 .. @c3
    # (each player's code counter, 10h apart) / MOVE A0,@shot (/ TE:
    # @tournament, @baby, @max power) / MMTM
    clr = None
    for i in p.find([0x5600, 0x0580, X, X, 0x0580, X, X, 0x0580, X, X, 0x0580, X, X, 0x0580]):
        c = [p.u32(i + 2 + 3 * k) for k in range(4)]
        if c[1] == c[0] + 0x10 and c[2] == c[0] + 0x20 and c[3] == c[0] + 0x30:
            v, k = [], i + 13
            while p.w[k] == 0x0580:
                v.append(p.u32(k + 1))
                k += 3
            clr = (c, v)
            break
    # tip-off: CMPI 72h (TE 12h),A0 / ... @c0 ... / MOVE @int (TE quick),A0 /
    # ... XOR / MOVE A0,@int / CMPI 61h,A0 / ... @big ...
    tip = p.find([0x0B40, X, 0xCB12, 0x4D00, 0x2480, 0x0B20, X, X, 0x8400, 0x0B40, 0xFFFA, 0xC409,
                  0x05A0, X, X, 0x182E, 0x630E, 0x57C0, 0x0580, X, X, 0x0B40, 0xFF9E, 0xCB09,
                  0x05A0, X, X, 0x182E, 0x630E, 0x57C0, 0x0580])
    # no computer assistance: CLR A0 / MOVE A0,@noassist / (TE: CALLR / JRC) /
    # MOVK 1Bh,A0 / CALLA <adjustment> / JRNE / MOVE @c0,A0 / CMPI Ah,A0
    na = p.find([0x5600, 0x0580, X, X, 0x1B60, 0x0D5F, X, X, X, 0x05A0, X, X, 0x0B40, 0xFFF5]) + \
        p.find([0x5600, 0x0580, X, X, 0x0D3F, X, X, 0x1B60, 0x0D5F, X, X, X, 0x05A0, X, X, 0x0B40, 0xFFF5])
    # counter checks: ADDI @c0,A0 / MOVE *A0,A0 / CMPI n,A0 / JRNE +6 /
    # MOVI <chance>,A0 (NBA Jam: n = 8, power-up defense; TE: 24, goaltending)
    cnt = p.find([0x0B20, X, X, 0x8400, 0x0B40, 0xFFE7 if te else 0xFFF7, 0xCB06, 0x09C0])
    # big heads, all revisions: CMPI 61h,A0 / JRNE / MOVE @big,A0 / MOVK 1,A14 /
    # SLL A8,A14 / XOR / MOVE A0,@big (1.00 and the prototypes have only this)
    bh = sorted(set(p.u32(i + 4) for i in p.find([0x0B40, 0xFF9E, 0xCB09, 0x05A0, X, X, 0x182E, 0x630E,
                                                    0x57C0, 0x0580])))
    # TE huge heads: ADDI @c0,A1 / MOVE *A1,A1 / CMPI 6,A1 / JREQ +3
    huge = p.find([0x0B21, X, X, 0x8421, 0x0B41, 0xFFF9, 0xCA03]) if te else []
    if len(tip) != 1:
        if len(bh) == 1:
            v_['big'] = bh[0]
            notes.append('power-ups: big heads %08X only' % bh[0])
        else:
            notes.append('power-ups: variables not found')
    elif clr is None:
        notes.append('power-ups: variables not found')
    else:
        c, v = clr
        t0 = tip[0]
        flag, big = p.u32(t0 + 13), p.u32(t0 + 25)
        if p.u32(t0 + 6) != c[0]:
            notes.append('power-ups: counters differ (%08X, %08X)' % (p.u32(t0 + 6), c[0]))
        v_.update(big=big, flag=flag, c=c)
        if te:
            if len(v) >= 4:
                v_.update(shot=v[0], tourn=v[1], baby=v[2], max=v[3])
            if len(huge) == 1:
                v_['huge'] = bit_address(huge[0] + 6)
            else:
                notes.append('huge heads check not found')
        elif v:
            v_['shot'] = v[0]
        if len(cnt) == 1:
            v_['cnt'] = bit_address(cnt[0] + 6)
        else:
            notes.append('%s check not found' % ('goaltending' if te else 'defense'))
        if len(na) == 1:
            v_['nocpu'] = p.u32(na[0] + 2)
        else:
            notes.append('no assistance flag not found')
    return v_


def nba_extras(p, te, notes):
    """NBA Jam / TE power-ups: the read patches (the table's option codes)."""
    v = nba_vars(p, te, notes)
    patches = []
    if 'flag' not in v:
        if 'big' in v:
            patches.append((v['big'] >> 4, TE_BIG if te else NJ_BIG, 0x000F))
        return patches
    if te:
        patches += [(v['big'] >> 4, TE_BIG, 0x000F), (v['flag'] >> 4, TE_QUICK, 0x000F)]
        if 'max' in v:
            patches += [(v['shot'] >> 4, TE_SHOT, 0x0001), (v['baby'] >> 4, TE_BABY, 0x0001),
                        (v['max'] >> 4, TE_MAX, 0x000F)]
        if 'huge' in v:
            patches.append((v['huge'] >> 4, TE_HUGE, JRUC | 3))
    else:
        patches += [(v['big'] >> 4, NJ_BIG, 0x000F), (v['flag'] >> 4, NJ_INT, 0x000F)]
        if 'shot' in v:
            patches.append((v['shot'] >> 4, NJ_SHOT, 0x0001))
    if 'cnt' in v:
        patches.append((v['cnt'] >> 4, TE_GOAL if te else NJ_DEF, NOP))
    if 'nocpu' in v:
        patches.append((v['nocpu'] >> 4, TE_NOCPU if te else NJ_NOCPU, 0x0001))
    notes.append('power-ups: counters %08X, big heads %08X, %s %08X, %d patches'
                 % (v['c'][0], v['big'], 'quick hands' if te else 'interceptions', v['flag'], len(patches)))
    return patches


def nba_tank(p):
    """Bit address of the JRNE that skips NBA Jam's hidden tank game unless
    the buttons are held (a NOP starts the game), or None."""
    # tank game: MOVE @IN0,A0 / ANDI 7072h,A0 (P1 Down + buttons, P2 buttons)
    # / JRNE / (3.01: the game mode and a once-a-game flag) / JA tank
    for i in p.find([0x05A0, 0x0000, 0x0160, 0x0B80, 0x8F8D, 0xFFFF, X]):
        if p.w[i + 6] >> 8 != 0xCB:
            continue
        for k in range(i + 7, i + 24):
            if p.w[k] == 0xC080:
                return bit_address(i + 6)
    return None


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

HIDE_EXTRAS = 0x100      # word 0, bit 8: the set is Mortal Kombat II Plus: the OSD hides the Finishing Moves and Hidden Items and has its own Move List and View Secrets


def hidden_table(gid):
    """Table bytes and notes for a set with its own extras, the secrets and
    finishing moves hidden (tools/hbmame_sets.py, Mortal Kombat II Plus): the
    game id with HIDE_EXTRAS and the format word, no patches, no codes."""
    return (struct.pack('<2H', gid | HIDE_EXTRAS, FORMAT),
            ['the OSD shows the Plus Move List and View Secrets, and no Finishing Moves or Hidden Items, for this set: no patches or codes'])


# The options that are cheats now (the OSD's Cheats menu, tools/tunit_cheats.py):
# their patches are no longer in the table
MOVED = {
    G_MK: (OPT_REP_HINT,), G_MKTURBO: (OPT_REP_HINT,),
    G_MK2: (OPT_HITBOX, OPT_PONG, OPT_NOOB, OPT_JADE, OPT_SMOKE),
    G_NBAJAM: (NJ_BIG, NJ_DEF, NJ_INT, NJ_SHOT, NJ_NOCPU),
    G_NBAJAMTE: (TE_BIG, TE_HUGE, TE_BABY, TE_MAX, TE_QUICK, TE_GOAL, TE_SHOT),
}


def collect(gid, p, notes):
    """(codes, patches) of a set: every patch the finders know, the moved ones
    included. A patch is (word address, option code, value)."""
    if gid in (G_MK, G_MKTURBO):
        codes, patches = mk_codes(p, notes)
        rp = mk_reptile(p, notes)
        patches = (patches or []) + (rp[0] if rp else [])
    elif gid == G_MK2:
        codes, patches = mk2_codes(p, notes)
    elif gid in (G_NBAJAM, G_NBAJAMTE):
        codes, patches = nba_codes(p, notes)
        patches = (patches or []) + nba_extras(p, gid == G_NBAJAMTE, notes)
    elif gid == G_JDREDDP:
        codes, patches = jd_codes(p, notes)
    else:
        codes, patches = [], None
    return codes, patches or []


def build(gid, prog_bytes):
    """Table bytes and notes for a set: game id gid, its maincpu region."""
    p = Prog(prog_bytes)
    notes = []
    codes, patches = collect(gid, p, notes)
    patches = [t for t in patches if t[1] not in MOVED.get(gid, ())]
    if len(patches) > N_PATCH:
        raise ValueError('too many patches')
    if len(set(a for a, _, _ in patches)) != len(patches):
        raise ValueError('two patches of one word')

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
        code, done = c[:2]
        t[26 + n] = pos | (UNTIL if len(c) > 2 and c[2] else 0)
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


# --------------------------------------------------------------------------
# The codes as the players enter them (the Secret Player List window's code
# page, tools/tunit_window.py; the game pages)
#
# From the code that checks them (NBA Jam 3.01, TE 4.0 3-23; the versions
# from each revision's program ROM): "press" is a new press of Turbo, Shoot
# or Pass (presses in the same frame count once), counted per player on the
# match-up screen; "until the tip-off" is the input word the tip-off reads,
# exactly those directions and buttons.
# --------------------------------------------------------------------------

MATCHUP = "TONIGHT'S MATCH-UP, BEFORE THE TIP-OFF"
ATTRACT = 'ATTRACT MODE'
MENU_FIRST = 'Both players hold Up + Turbo + Shoot + Pass, then hold Down for 2 s'
MENU_SECOND = ('on the design team screen: P1 Turbo 2x, P2 Shoot 3x, P2 Pass 2x, P1 Shoot, P1 Pass, '
               'P2 Turbo 2x')
CHEATS = {
    'nbajam': [
        (MATCHUP, [
            ('Big Heads', 'Hold Up + Turbo + Pass until the tip-off', 'All'),
            ('No CPU Assistance', 'Press exactly 10 times', '3.01'),
            ('Power-Up Defense', 'Press exactly 8 times', '2.00, 3.01'),
            ('Power-Up Interceptions', 'Press 5 times or more, then hold Down + Turbo + Shoot + Pass '
             'until the tip-off', '2.00, 3.01'),
            ('Shot Percentage', 'Turn the joystick a full circle and press 15 times or more', '2.00, 3.01'),
            ('Tank Game', 'P1 holds Down + Turbo + Shoot + Pass and P2 Turbo + Shoot + Pass until the '
             'tip-off (3.01: once a game)', '1.00, 2.00, 3.01'),
        ]),
        (ATTRACT, [
            ('Secret Menu', MENU_FIRST + '; 3.01 then ' + MENU_SECOND, 'All'),
        ]),
    ],
    'nbajamte': [
        (MATCHUP, [
            ('Baby Size Players', 'Hold Down + Right and press Turbo, Shoot, Pass three times over', 'All'),
            ('Big Heads', 'Hold Up + Turbo + Pass until the tip-off', 'All'),
            ('Huge Heads', 'Press exactly 6 times, then hold Up + Turbo + Pass until the tip-off', 'All'),
            ('Max Power', 'Hold Down + Turbo + Shoot + Pass + Start', 'All'),
            ('No CPU Assistance', 'Press exactly 10 times', 'All'),
            ('Power-Up Goaltending', 'Press exactly 24 times', 'All'),
            ('Quick Hands', 'Press 5 times or more, then hold Down + Shoot until the tip-off', 'All'),
            ('Shot Percentage', 'Turn the joystick a full circle and press 15 times or more', 'All'),
            ('Tournament Mode', 'Hold Right + Turbo + Shoot + Pass: no power-ups, CPU assistance or '
             'secrets in this game', 'All'),
        ]),
        (ATTRACT, [
            ('Secret Menu', MENU_FIRST + ', then ' + MENU_SECOND, 'All'),
        ]),
    ],
}
CHEATS_NOTE = 'Press: Turbo, Shoot or Pass (together counts once)'


def cheats_docs(game):
    """Markdown table of a game's codes (the game pages)."""
    o = ['| Code | When | Enter | Versions |', '|---|---|---|---|']
    for head, rows in CHEATS[game]:
        when = "Tonight's Match-Up" if head == MATCHUP else 'Attract mode'
        for name, how, ver in rows:
            o.append('| %s | %s | %s | %s |' % (name, when, how, ver))
    return '\n'.join(o) + '\n'


# --------------------------------------------------------------------------
# OSD lines (NBA Jam, TE)
# --------------------------------------------------------------------------

def osd_lines():
    """The NBA Jam / TE lines of the OSD: View Secret Players in the main
    menu (Off or On: the window of rtl/tunit_window.sv, its pages turned
    with Left and Right), then the Cheat Codes & Hidden Items page: the
    secret menu code (R[14]) and, for TE, No CPU Assistance. The power-ups,
    the tank game and tournament mode are cheats of the Cheats menu now
    (tools/tunit_cheats.py). Lines both games have test the NBA mask bit; the
    others the game's own bit."""
    te, nba = MASK_TE, MASK_NBA
    pg = 'P%d' % OSD_PAGE
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import tunit_window
    n = tunit_window.page_counts()
    if max(n.values()) > 31:
        raise ValueError('too many window pages for the page register (5 bits)')
    return ['h%sO[%d],View Secret Players,Off,On;' % (nba, OSD_VIEW),
            'h%s%s,Cheat Codes & Hidden Items;' % (nba, pg),
            '%s-;' % pg,
            '%sR[14],Open Secret Menu (Attract);' % pg,
            'h%s%sO[%d],No CPU Assistance,Off,On;' % (te, pg, OSD_NOCPU)]


def plus_osd_lines():
    """Mortal Kombat II Plus's line of the OSD: View Secrets in the main menu
    (Off or On: the window of rtl/tunit_window.sv, its pages turned with Left
    and Right)."""
    return ['h%sO[%d],View Secrets,Off,On;' % (MASK_PLUS, OSD_PLUS_VIEW)]


def gen_osd():
    o = ['// tunit_secrets_osd.svh - the NBA Jam and TE lines of the OSD (View Secret',
         '// Players, the Cheat Codes & Hidden Items page) and Mortal Kombat II Plus\'s',
         '// (View Secrets)',
         '// Generated by tools/tunit_secrets.py --gen; do not edit.',
         '//',
         '// Copyright (C) 2026 Gm0rk - GPL-3.0-or-later',
         '',
         '`define NBA_OSD \\']
    for l in osd_lines():
        o.append('\t"%s", \\' % l)
    o[-1] = o[-1].rstrip(' \\').rstrip(',')
    o.append('')
    o.append('`define PLUS_OSD \\')
    for l in plus_osd_lines():
        o.append('\t"%s", \\' % l)
    o[-1] = o[-1].rstrip(' \\').rstrip(',')
    o.append('')
    return '\n'.join(o)


def main():
    import argparse
    if sys.argv[1:2] == ['--codes'] and len(sys.argv) == 3:
        print(cheats_docs(sys.argv[2]), end='')
        return
    if '--gen' in sys.argv:
        open(os.path.join(ROOT, 'rtl', 'tunit_secrets_osd.svh'), 'w').write(gen_osd())
        print('rtl/tunit_secrets_osd.svh: %d bytes of CONF_STR' % sum(len(l) for l in osd_lines()))
        return
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

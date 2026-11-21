#!/usr/bin/env python3
"""
tunit_mk2sites.py - Mortal Kombat II's direct finisher sites

    python3 tools/tunit_mk2sites.py <maincpu.bin>          the sites of a set and how they line up with rev L3.1's
    python3 tools/tunit_mk2sites.py --ref <L3.1 maincpu.bin>   print REF (below) for this file

Mortal Kombat II's move handlers find a combination in the joystick history
with two matcher routines (FF8775D0 for directions, FF877580 for buttons in
L3.1) and skip the move with a conditional jump when it is not there:

    MOVI pattern,A11 / CALLR matcher / JRNC exit        (or JRC: Scorpion's Toasty)

The patch bank (rtl/midway_tunit.sv) flips bit 8 of that jump's opcode word
while the move player plays a direct finisher, so the history always matches,
and the move player taps only the button or direction the handler runs on;
the game still checks FINISH HIM, the distance and the loser's state itself.
Friendship, Babality and the stage fatality each have one site shared by
every fighter (the pattern comes from the fighter's table).

This module finds the sites of a set's program ROM and lines them up with
rev L3.1's, which tools/tunit_fmoves.py's MK2_DIRECT names by address. A
site is used in another revision only when its signature is the same as
L3.1's at the same place in the list: the matcher it calls, its pattern (the
joystick codes the matcher compares, newest first), the jump's opcode and, for
the short form, its offset (the 16-bit form's target counts only as "the
handlers' exit"). Revisions with other handlers (L1.1, L1.4) have a
different list and no site is used.

A few moves have no matcher: a release handler that only tests how long a button was held
("frames since the press" against a limit): MOVI stamp,A0 / CALLA stamp routine / CMPI limit,A1 / JRC exit.
Raiden's Electrocution (LK released after 80h frames) and Shang Tsung's Kintaro (LP, 3C0h) are two.
The move player flips that JRC to a JRNC (patch value 1, as for Scorpion's Toasty) and lets go of
the button after a few frames, so "held less than the limit" goes on into the move (scan_holds, HOLD_REF,
align_holds; the handler's own state and distance checks stay).

Mortal Kombat II Plus (HBMAME mk2s03, mk2s04) is rev L3.1 with extra code and lines up with
L3.1's list (Beta 2 moved the stage fatality's site, tunit_fmoves.PLUS_SITES). Rev 4.0 has its
own list (REV4_REF), found with the button matcher 14 words before the direction matcher.

Copyright (C) 2026 Gm0rk - GPL-3.0-or-later
"""

import difflib
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tunit_secrets import Prog     # noqa: E402

MIN_EQUAL = 66                   # a set whose list has as many sites as L3.1's and this many equal to it uses its sites


def scan(data, bdelta=5):
    """The matcher call sites of a program ROM, by address: dicts with
    call (word index of the call), jump (word index of the jump after it),
    op (its opcode word), pat (the pattern's words: the time and the codes,
    or None when the pattern is not an immediate), kind ('M' direction
    matcher, 'B' button matcher), sig (the signature)."""
    p = Prog(data)
    w, n = p.w, len(p.w)
    calls = []
    for i in range(n - 3):
        if w[i] == 0x0D3F:                          # CALLR displacement
            d = w[i + 1] - 65536 if w[i + 1] & 0x8000 else w[i + 1]
            calls.append((i, 2, i + 2 + d))
        elif w[i] == 0x0D5F:                        # CALLA address
            calls.append((i, 3, p.word_index(w[i + 1] | w[i + 2] << 16)))
    # the direction matcher: the target most often called right after MOVI pattern,A11
    cnt = Counter(t for i, ln, t in calls if ln == 2 and i >= 3 and w[i - 3] == 0x09EB)
    if not cnt:
        return []
    mt = cnt.most_common(1)[0][0]
    bt = mt - bdelta                                # the button matcher is 0x50 bits before in L3.1 (rev 4.0: 0xE0)
    out = []
    for i, ln, t in calls:
        if t not in (mt, bt):
            continue
        j = i + ln
        op = w[j]
        if op >> 8 not in (0xC8, 0xC9):             # JRC / JRNC
            continue
        pat = None
        if ln == 2 and i >= 3 and w[i - 3] == 0x09EB:
            tb = p.word_index(w[i - 2] | w[i - 1] << 16)
            if 0 <= tb < n - 10:
                pat = [w[tb]]
                for k in range(1, 10):
                    if w[tb + k] == 0:
                        break
                    pat.append(w[tb + k])
                pat = tuple(pat)
        tgt = None
        if op & 0xFF == 0:                          # 16-bit displacement
            d = w[j + 1] - 65536 if w[j + 1] & 0x8000 else w[j + 1]
            tgt = j + 2 + d
        out.append(dict(call=i, jump=j, op=op, pat=pat, tgt=tgt, kind='M' if t == mt else 'B'))
    exit_ = Counter(s['tgt'] for s in out if s['tgt'] is not None).most_common(1)
    exit_ = exit_[0][0] if exit_ else None
    for s in out:
        if s['tgt'] is None:
            jw = (s['op'],)
        else:
            jw = (s['op'], 'EXIT' if s['tgt'] == exit_ else s['tgt'] - s['jump'])
        s['sig'] = (s['kind'], s['pat'], jw)        # (the call's form is not part of it: L2.x's global sites are CALLR)
    out.sort(key=lambda s: s['call'])
    return out


def align(data, moved=None):
    """{rev L3.1 jump address (bit address): this set's jump word index} for the sites
    whose signature is L3.1's, or {} when the set is not L3.1's kind of set. Also
    returns the patch's value for bit 8 of each ({word index: 1 for a JRC, 0 for a JRNC}) and notes.

    A site that stayed where it is with another pattern (Mortal Kombat II Plus
    sets some patterns up in its own code: its Toasty) counts as the same when
    the matcher and the jump are the same. A set with sites of its own (Plus
    has the extra fighters' and moves') still lines up with L3.1's, in order.
    moved: {L3.1 address: address in this set} for a site the set moved (Plus
    Beta 2 handles the stage fatality in its own code); it counts when the
    jump there is a matcher's with a pattern set up in code and the same kind of jump."""
    notes = []
    sites = scan(data)
    ref = REF
    a = [s[1] for s in ref]
    b = [s['sig'] for s in sites]
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    eq = {}
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            for k in range(i2 - i1):
                eq[ref[i1 + k][0]] = sites[j1 + k]
        elif tag == 'replace':
            # the same site where it was, only its pattern is not an immediate or another
            for k in range(i1, i2):
                for m in range(j1, j2):
                    s = sites[m]
                    if (ref[k][0] == 0xFF800000 + 16 * s['jump'] and ref[k][1][0] == s['sig'][0]
                            and ref[k][1][2] == s['sig'][2]):
                        eq[ref[k][0]] = s
    have = {0xFF800000 + 16 * s['jump']: s for s in sites}
    for old, new in (moved or {}).items():
        s, r = have.get(new), dict(ref).get(old)
        if s and r and s['sig'][0] == r[0] and s['pat'] is None and r[1] is None and s['op'] >> 8 == r[2][0] >> 8:
            eq[old] = s
            notes.append('MK2 site %08X is %08X in this set' % (old, new))
    if len(eq) < MIN_EQUAL:
        notes.append('MK2 sites: only %d of %d the same as L3.1\'s (%d found): not used' % (len(eq), len(ref), len(sites)))
        return {}, {}, notes
    out = {addr: s['jump'] for addr, s in eq.items()}
    hold = align_holds(data)
    out.update(hold)
    notes.append('MK2 hold sites: %d of %d the same as L3.1\'s' % (len(hold), len(HOLD_REF)))
    # the patch's value for bit 8 of the opcode word: clear it for a JRNC (C9xx, JRC afterwards), set it for a JRC (C8xx)
    pol = {j: 1 - (data[2 * j + 1] & 1) for j in out.values()}
    notes.append('MK2 sites: %d of %d the same as L3.1\'s (%d found)' % (len(eq), len(ref), len(sites)))
    return out, pol, notes


# The sites of rev L3.1 (tools/tunit_mk2sites.py --ref): the jump's bit address and the signature.
REF = [
    (0xFF862450, ('M', (32, 5, 5), (51456, 'EXIT'))),
    (0xFF862590, ('M', (16, 5, 6), (51456, 'EXIT'))),
    (0xFF862690, ('M', (16, 5, 6), (51456, 'EXIT'))),
    (0xFF862830, ('M', (32, 8, 7, 7), (51456, 'EXIT'))),
    (0xFF864810, ('M', (48, 8, 8, 8), (51456, 'EXIT'))),
    (0xFF864B90, ('M', (32, 6, 7, 5, 8, 6), (51456, 'EXIT'))),
    (0xFF864DA0, ('M', (24, 8, 8), (51461,))),
    (0xFF864F20, ('M', (48, 6, 7, 7), (51470,))),
    (0xFF8651A0, ('B', (48, 3, 2, 2, 2), (51461,))),
    (0xFF865410, ('M', (56, 8, 6, 8, 8), (51456, 'EXIT'))),
    (0xFF8655D0, ('M', (24, 7, 6, 8), (51461,))),
    (0xFF8656C0, ('M', (34, 7, 7, 7), (51465,))),
    (0xFF865860, ('M', (36, 8, 8), (51456, 'EXIT'))),
    (0xFF865A70, ('M', (36, 8, 7, 8), (51456, 'EXIT'))),
    (0xFF865B90, ('M', (56, 6, 8, 8), (51470,))),
    (0xFF865E00, ('M', (56, 8, 8, 6, 8), (51456, 'EXIT'))),
    (0xFF866100, ('M', (16, 7, 6), (51456, 'EXIT'))),
    (0xFF8664C0, ('M', (16, 8, 6), (51456, 'EXIT'))),
    (0xFF8669B0, ('M', (56, 8, 6, 7, 7), (51456, 'EXIT'))),
    (0xFF866AD0, ('M', (32, 7, 7), (51496,))),
    (0xFF866E60, ('M', (40, 6, 7, 7), (51456, 'EXIT'))),
    (0xFF8671D0, ('B', (32, 2, 2, 2), (51461,))),
    (0xFF8672C0, ('M', (48, 8, 8, 7), (51456, 'EXIT'))),
    (0xFF867420, ('M', (56, 8, 6, 8), (51461,))),
    (0xFF867510, ('M', (36, 7, 7), (51461,))),
    (0xFF867600, ('M', (32, 6, 5), (51461,))),
    (0xFF8676F0, ('M', (48, 8, 7, 7), (51461,))),
    (0xFF8677E0, ('M', (53, 8, 8, 7, 7), (51456, 'EXIT'))),
    (0xFF867D00, ('M', (34, 7, 7, 7), (51461,))),
    (0xFF867E60, ('M', (56, 8, 6, 8, 7), (51456, 'EXIT'))),
    (0xFF867F80, ('M', (16, 7, 6), (51461,))),
    (0xFF8680E0, ('M', (56, 7, 7, 7, 7), (51456, 'EXIT'))),
    (0xFF868270, ('M', (54, 5, 6, 8, 8), (51456, 'EXIT'))),
    (0xFF868480, ('M', (24, 7, 6, 8), (51461,))),
    (0xFF868570, ('M', (56, 7, 6, 7), (51456, 'EXIT'))),
    (0xFF8688A0, ('M', (56, 8, 8, 8, 6), (51456, 'EXIT'))),
    (0xFF8689C0, ('M', (24, 7, 6, 8), (51456, 'EXIT'))),
    (0xFF868AC0, ('M', (48, 7, 7), (51456, 'EXIT'))),
    (0xFF868CC0, ('M', (56, 5, 5, 6, 6), (51232,))),
    (0xFF868D60, ('M', (40, 5, 5), (51480,))),
    (0xFF868F80, ('M', (16, 7, 6), (51456, 'EXIT'))),
    (0xFF869430, ('M', (24, 7, 6, 8), (51456, 'EXIT'))),
    (0xFF869620, ('M', (24, 8, 8), (51461,))),
    (0xFF869870, ('B', (48, 1, 2, 2, 2, 2), (51456, 'EXIT'))),
    (0xFF869BB0, ('M', (56, 8, 8, 6, 6), (51467,))),
    (0xFF869D00, ('M', (24, 8, 6, 7), (51461,))),
    (0xFF869E90, ('M', (56, 6, 7, 7), (51456, 'EXIT'))),
    (0xFF869F90, ('M', (16, 8, 6), (51456, 'EXIT'))),
    (0xFF86A120, ('M', (56, 6, 5, 5), (51461,))),
    (0xFF86A210, ('M', (24, 8, 8), (51456, 'EXIT'))),
    (0xFF86A380, ('M', (56, 6, 8, 8), (51456, 'EXIT'))),
    (0xFF86A650, ('M', (24, 8, 7), (51456, 'EXIT'))),
    (0xFF86A8A0, ('M', (48, 5, 6, 5), (51467,))),
    (0xFF86A9F0, ('M', (56, 8, 7, 6), (51461,))),
    (0xFF86AAE0, ('M', (56, 6, 6), (51456, 'EXIT'))),
    (0xFF86ABE0, ('M', (48, 7, 6, 7), (51461,))),
    (0xFF86ACD0, ('M', (56, 7, 8, 6), (51461,))),
    (0xFF86AE40, ('M', (36, 8, 8), (51456, 'EXIT'))),
    (0xFF86AF40, ('M', (36, 8, 8), (51456, 'EXIT'))),
    (0xFF86B040, ('M', (36, 8, 8), (51461,))),
    (0xFF86B1A0, ('M', (56, 7, 7, 8, 6), (51456, 'EXIT'))),
    (0xFF86B440, ('M', (24, 8, 7), (51456, 'EXIT'))),
    (0xFF86B630, ('M', (32, 6, 5), (51456, 'EXIT'))),
    (0xFF86B7A0, ('M', (24, 5, 5), (51461,))),
    (0xFF86B890, ('M', (52, 8, 8, 8), (51456, 'EXIT'))),
    (0xFF86BA40, ('M', (24, 8, 7), (51456, 'EXIT'))),
    (0xFF876E70, ('M', None, (51546,))),
    (0xFF87E300, ('M', None, (51464,))),
    (0xFF880950, ('M', None, (51464,))),
]


# The hold-time sites of rev L3.1 (tools/tunit_mk2sites.py --ref): the jump's bit address and (press stamp, limit).
# 25 sites since Build 94 (Raiden's Super Uppercut); the sets before L3.0 lack it (and the Kintaro).
HOLD_REF = [
    (0xFF838570, (0x1061DC0, 0x200)),
    (0xFF862730, (0x1061D30, 0x40)),
    (0xFF8636C0, (0x1061EC0, 0x80)),   # Raiden's Electrocution (LK, 80h)
    (0xFF863830, (0x1061E40, 0x180)),  # Raiden's Super Uppercut (HP, 180h; the round state is tested before the compare)
    (0xFF863930, (0x1061E40, 0x50)),
    (0xFF863B50, (0x1061EA0, 0x30)),
    (0xFF863D20, (0x1061E60, 0x3C0)),   # Shang Tsung's Kintaro (LP, 3C0h)
    (0xFF863F30, (0x1061E40, 0x30)),
    (0xFF864090, (0x1061EC0, 0x80)),
    (0xFF8641A0, (0x1061E40, 0x22)),
    (0xFF864760, (0x1061E60, 0x40)),
    (0xFF864CA0, (0x1061EC0, 0x80)),
    (0xFF864FB0, (0x1061EE0, 0x20)),
    (0xFF8654B0, (0x1061EC0, 0x38)),
    (0xFF865900, (0x1061DA0, 0x80)),
    (0xFF8662F0, (0x1061E00, 0xC0)),
    (0xFF866890, (0x1061E60, 0x30)),
    (0xFF867A90, (0x1061DE0, 0x60)),
    (0xFF8687F0, (0x1061E40, 0x28)),
    (0xFF868B60, (0x1061D10, 0x66)),
    (0xFF869020, (0x1061CF0, 0x60)),
    (0xFF869A50, (0x1061EC0, 0x60)),
    (0xFF86B320, (0x1061E60, 0x30)),
    (0xFF86D8A0, (0x1061E60, 0x8)),
    (0xFF8B9420, (0x1061E40, 0xA)),
]


def scan_holds(data):
    """The hold-time sites of a program ROM: dicts with jump (word index of the JRC after the CMPI),
    stamp (the button's press stamp, a RAM address) and imm (the limit in frames)."""
    p = Prog(data)
    w = p.w
    out = []
    for i in range(len(w) - 15):
        # MOVI stamp,A0 / CALLA routine / CMPI ~limit,A1 / JRC
        if w[i] == 0x09E0 and w[i + 3] == 0x0D5F and w[i + 6] == 0x0B41 and w[i + 8] >> 8 == 0xC8:
            out.append(dict(jump=i + 8, stamp=w[i + 1] | w[i + 2] << 16, imm=~w[i + 7] & 0xFFFF))
        # the same with the round state tested in between (Raiden's Super Uppercut):
        # MOVI stamp,A0 / CALLA routine / MOVE @state,A0 / CMPI 3,A0 / JRNE exit / CMPI ~limit,A1 / JRC
        elif (w[i] == 0x09E0 and w[i + 3] == 0x0D5F and w[i + 6] == 0x05A0 and w[i + 9] == 0x0B40
              and w[i + 10] == 0xFFFC and w[i + 11] >> 8 == 0xCB and w[i + 12] == 0x0B41 and w[i + 14] >> 8 == 0xC8):
            out.append(dict(jump=i + 14, stamp=w[i + 1] | w[i + 2] << 16, imm=~w[i + 13] & 0xFFFF))
    return out


def align_holds(data):
    """{rev L3.1 hold site address: this set's jump word index} for the hold sites
    (HOLD_REF) of a set, matched in order by (stamp, limit); sites the set lacks are not in it
    (L2.0 and L2.1 have no Kintaro)."""
    sites = scan_holds(data)
    sm = difflib.SequenceMatcher(None, [r[1] for r in HOLD_REF], [(s['stamp'], s['imm']) for s in sites],
                                 autojunk=False)
    out = {}
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            for k in range(i2 - i1):
                out[HOLD_REF[i1 + k][0]] = sites[j1 + k]['jump']
    return out


# The sites of rev 4.0 (HBMAME mk2s08; python3 tools/tunit_mk2sites.py --rev4 <maincpu.bin>):
# the junkwax rebuild has its own addresses, handlers in FF8B7xxx-FF8C4xxx and the Babality in FFB0F940.
# Its button matcher is 14 words before the direction matcher (L3.1: 5). Each one was played in MAME.
REV4_REF = {
    0xFF8B7FB0: ('M', (48, 8, 8, 8), (51456, 'EXIT')),
    0xFF8B8430: ('M', (32, 6, 7, 5, 8, 6), (51456, 'EXIT')),
    0xFF8B8B80: ('B', (48, 3, 2, 2, 2), (51461,)),
    0xFF8B8DC0: ('M', (56, 8, 6, 8, 8), (51456, 'EXIT')),
    0xFF8BB930: ('M', (36, 8, 7, 8), (51456, 'EXIT')),
    0xFF8BBA50: ('M', (56, 6, 8, 8), (51476,)),
    0xFF8BBCF0: ('M', (56, 8, 8, 6, 8), (51456, 'EXIT')),
    0xFF8BC640: ('M', (56, 8, 6, 8), (51463,)),
    0xFF8BD1F0: ('M', (56, 8, 6, 7, 7), (51456, 'EXIT')),
    0xFF8BDFB0: ('M', (40, 6, 7, 7), (51456, 'EXIT')),
    0xFF8BF470: ('M', (56, 8, 6, 8, 7), (51456, 'EXIT')),
    0xFF8BF7E0: ('M', (56, 7, 7, 7, 7), (51456, 'EXIT')),
    0xFF8BF970: ('M', (54, 5, 6, 8, 8), (51456, 'EXIT')),
    0xFF8BFBB0: ('M', (56, 7, 7, 8), (51463,)),
    0xFF8C0180: ('M', (56, 8, 8, 8, 6), (51456, 'EXIT')),
    0xFF8C05B0: ('M', (56, 5, 5, 6, 6), (51239,)),
    0xFF8C06F0: ('M', (40, 5, 5), (51477,)),
    0xFF8C16F0: ('B', (48, 1, 2, 2, 2, 2), (51456, 'EXIT')),
    0xFF8C1A60: ('M', (56, 8, 8, 6, 6), (51467,)),
    0xFF8C1DE0: ('M', (64, 5, 8, 7, 7), (51463,)),
    0xFF8C23A0: ('M', (56, 6, 5, 5), (51461,)),
    0xFF8C28F0: ('M', (56, 6, 8, 8), (51467,)),
    0xFF8C3030: ('M', (56, 8, 6, 8), (51467,)),
    0xFF8C3180: ('M', (56, 5, 6, 5), (51463,)),
    0xFF8C3DB0: ('M', (56, 7, 7, 8, 6), (51456, 'EXIT')),
    0xFF8C4050: ('M', (24, 8, 7), (51456, 'EXIT')),
    0xFF8C44A0: ('M', (52, 8, 8, 8), (51472,)),
    0xFF8DA120: ('M', None, (51562,)),
    0xFFB0F940: ('M', None, (51464,)),
}


# Rev 4.0's hold-time site (Raiden's Electrocution, as L3.1's FF8636C0): the jump's bit address -> (press stamp, limit).
# Its stamps are 110DExx (HP DEA0, LP DEC0, HK DF00, LK DF40). Played in MAME (the hold, then the move with taps).
REV4_HOLD = {
    0xFF8B6A70: (0x110DF40, 0x80),       # Raiden's Electrocution
    0xFF8B6BF0: (0x110DF00, 0xA4),       # Raiden's Lift (HK)
    0xFF8B6D60: (0x110DEA0, 0x180),      # Raiden's Exploding Uppercut (HP; the round state is tested before the compare)
    0xFF8B7070: (0x110DF00, 0xA4),       # Shang Tsung's Body Explosion (HK)
    0xFF8B7280: (0x110DEC0, 0x3C0),      # Shang Tsung's Kintaro (LP, 3C0h as L3.1's)
    0xFF8B7630: (0x110DF40, 0x80),       # Mileena's Body Suck (the stamp of LK)
    0xFF8B7F00: (0x110DEC0, 0x40),       # Jax's Head Clap
    0xFF8B8E60: (0x110DF40, 0x38),       # Kitana's Kiss of Death
    0xFF8BD0D0: (0x110DEC0, 0x30),       # Sub-Zero's Ice Bomb
    0xFF8C00D0: (0x110DEA0, 0x28),       # Scorpion's Spear Slice
    0xFF8C3F30: (0x110DEC0, 0x30),       # Kung Lao's Hat Decap
}


def align_rev4(data):
    """{rev 4.0 jump address (bit address): jump word index}, {word index: patch value of bit 8}
    and notes, for the sites of REV4_REF and REV4_HOLD: all of them have to be there with the same
    signature, else none is used."""
    sites = {0xFF800000 + 16 * s['jump']: s for s in scan(data, 14)}
    out = {a: sites[a]['jump'] for a, sig in REV4_REF.items() if a in sites and sites[a]['sig'] == sig}
    holds = {0xFF800000 + 16 * h['jump']: h for h in scan_holds(data)}
    out.update({a: holds[a]['jump'] for a, sig in REV4_HOLD.items()
                if a in holds and (holds[a]['stamp'], holds[a]['imm']) == sig})
    if len(out) != len(REV4_REF) + len(REV4_HOLD):
        return {}, {}, ['MK2 rev 4.0 sites: only %d of %d as expected: not used' % (len(out), len(REV4_REF) + len(REV4_HOLD))]
    pol = {j: 1 - (data[2 * j + 1] & 1) for j in out.values()}
    return out, pol, ['MK2 rev 4.0 sites: all %d as expected' % len(out)]


def _gen_ref(data):
    lines = ['REF = [']
    for s in scan(data):
        lines.append('    (0x%08X, %r),' % (0xFF800000 + 16 * s['jump'], s['sig']))
    lines.append(']')
    lines.append('HOLD_REF = [')
    for h in scan_holds(data):
        lines.append('    (0x%08X, (0x%X, 0x%X)),' % (0xFF800000 + 16 * h['jump'], h['stamp'], h['imm']))
    lines.append(']')
    return '\n'.join(lines)


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--ref':
        print(_gen_ref(open(sys.argv[2], 'rb').read()))
    elif len(sys.argv) == 3 and sys.argv[1] == '--rev4':
        sites, pol, notes = align_rev4(open(sys.argv[2], 'rb').read())
        print('\n'.join(notes))
    elif len(sys.argv) == 2:
        sites, pol, notes = align(open(sys.argv[1], 'rb').read())
        print('\n'.join(notes))
        for addr in sorted(sites):
            print('%08X -> %08X%s' % (addr, 0xFF800000 + 16 * sites[addr], ' (JRC)' if pol[sites[addr]] else ''))
    else:
        print(__doc__)

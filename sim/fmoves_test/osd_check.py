#!/usr/bin/env python3
"""
osd_check.py - checks the Finishing Moves page of the OSD (rtl/tunit_fmoves_osd.svh)

    python3 osd_check.py

Reads the generated CONF_STR lines of the page and renders them the way
Main_MiSTer does for a menu mask: an h<bit> prefix shows a line only when the
mask bit is set, an H<bit> prefix only when it is clear; a line is shown when
none of its prefixes hide it. The mask is built as the top level builds it
(Arcade-Midway-T-Unit.sv, status_menumask): bit 3 Mortal Kombat or II with the
Move List and the Finishing Moves, bit 4 Mortal Kombat, bit 5 Mortal Kombat II,
bit 7 Mortal Kombat II rev 4.0, bits 8-11 the page's fighter (his line), bit 2 and bit 12
the class of the loaded set (ROM index 1 word 0x21F), bit 15 Mortal Kombat II
Plus (which has bits 3 and 5 as well: the page, and its own Move List line; its
bit 12 is the fifth bit of the fighter, 17 fighters and no classes).

For every set that has finishing moves and every fighter the page must show
exactly the moves the set has, once each, by type (fatalities, stage fatalities and the Dead Pool,
friendship, babality) and alphabetically within a type, each with its note line,
and nothing else of the fighter's: the rendering is compared with the moves
the set lacks (tools/tunit_fmoves.py MISSING). The class of each set is
checked to differ from the class of every set that lacks other moves.

Copyright (C) 2026 Gm0rk - GPL-3.0-or-later
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..', '..')
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import tunit_fmoves as T   # noqa: E402
from tunit_secrets import G_MK, G_MKTURBO, G_MK2   # noqa: E402

HEX = '0123456789ABCDEF'

# the sets with finishing moves and the games they are (MAME names; the
# revisions that lack moves are the ones in T.MISSING)
SETS = [('mk', G_MK), ('mkr4', G_MK), ('mktturbo', G_MKTURBO), ('mk07', G_MK), ('mk2s08', G_MK2),
        ('mk2', G_MK2), ('mk2r30', G_MK2), ('mk2r31e', G_MK2), ('mk2r32e', G_MK2),
        ('mk2r42', G_MK2), ('mk2r91', G_MK2), ('mk2chal', G_MK2),
        ('mk2r11', G_MK2), ('mk2r14', G_MK2), ('mk2r20', G_MK2), ('mk2r21', G_MK2),
        ('mk2s03', G_MK2), ('mk2s04', G_MK2)]
PLUS = ('mk2s03', 'mk2s04')


# the page's order of the move types (the kinds of the move table)
RANK = {T.K_FATAL: 0, T.K_STAGE: 1, T.K_PIT2: 1, T.K_STAGE4: 1, T.K_DEAD: 1, T.K_FRIEND: 2, T.K_BABY: 3}


def page_lines():
    """The page's lines (strings of the FMOVES_OSD macro), in order."""
    t = open(os.path.join(ROOT, 'rtl', 'tunit_fmoves_osd.svh'), encoding='utf-8').read()
    body = t.split('`define FMOVES_OSD', 1)[1].split('`define CORE_INFO', 1)[0]
    return [m.replace('\\"', '"').replace('\\\\', '\\') for m in re.findall(r'"((?:\\.|[^"\\])*)"', body)]


def macro_lines(name):
    """The lines of a macro of rtl/tunit_fmoves_osd.svh (FMOVES_AFM, FMOVES_LIST)."""
    t = open(os.path.join(ROOT, 'rtl', 'tunit_fmoves_osd.svh'), encoding='utf-8').read()
    body = t.split('`define %s' % name, 1)[1].split('`define', 1)[0]
    return [m.replace('\\"', '"').replace('\\\\', '\\') for m in re.findall(r'"((?:\\.|[^"\\])*)"', body)]


def top_lines():
    """The top level's CONF_STR lines that carry a menu mask (the Sound Options pages)."""
    t = open(os.path.join(ROOT, 'Arcade-Midway-T-Unit.sv'), encoding='utf-8').read()
    return [m for m in re.findall(r'^\s*"([^"]*Sound Options;)",?\s*$', t, re.M)]


CONF_STR_MAX = 10239      # what Main_MiSTer reads of the configuration string (the qsf's loop limit is 10240)


def conf_len():
    """The length of the whole CONF_STR of the top level (its strings and the macros of
    rtl/tunit_fmoves_osd.svh, rtl/tunit_secrets_osd.svh and rtl/tunit_dips_osd.svh; the build date counts 6)."""
    t = open(os.path.join(ROOT, 'Arcade-Midway-T-Unit.sv'), encoding='utf-8').read()
    i = t.index('localparam CONF_STR = {')
    body = t[i:t.index('};', i)]
    mac = {}
    for f in ('rtl/tunit_fmoves_osd.svh', 'rtl/tunit_secrets_osd.svh', 'rtl/tunit_dips_osd.svh'):
        x = open(os.path.join(ROOT, f), encoding='utf-8').read()
        for m in re.finditer(r'`define (\w+) ((?:\\\n|[^\n])*)', x):
            mac[m.group(1)] = m.group(2).replace('\\\n', '\n')
    strings = lambda x: re.findall(r'"((?:\\.|[^"\\])*)"', x)        # noqa: E731
    n = 0
    for tok in re.finditer(r'"((?:\\.|[^"\\])*)"|`(\w+)', body):
        if tok.group(1) is not None:
            parts = [tok.group(1)]
        elif tok.group(2) in mac:
            parts = strings(mac[tok.group(2)])
        else:
            n += 6                                   # `BUILD_DATE
            continue
        n += sum(len(p.replace('\\\\', '\\').replace('\\"', '"').replace('\\n', '\n')) for p in parts)
    return n


def pick_map():
    """fm_pick's cases of rtl/tunit_fmoves_osd.svh: {(game 0-2, option): line}."""
    t = open(os.path.join(ROOT, 'rtl', 'tunit_fmoves_osd.svh'), encoding='utf-8').read()
    return {(int(g), int(o)): int(li) for g, o, li in re.findall(r"\{2'd(\d), 5'd(\d+)\}: fm_pick = 5'd(\d+);", t)}


def parse(line):
    """(hide prefixes [(h or H, bit)], rest) of a line."""
    pre = []
    while len(line) > 1 and line[0] in 'hH' and line[1] in HEX:
        pre.append((line[0], HEX.index(line[1])))
        line = line[2:]
    return pre, line


def shown(pre, mask):
    return all((mask >> b & 1) == (c == 'h') for c, b in pre)


def mask_for(game, fighter, cls, plus=False):
    plus = plus or game == 'plus'
    m = 1 << 3                                  # osd_list
    if plus:
        m |= 1 << 15                            # menu_plus
    m |= 1 << (4 if game in ('mk', 'mkp') else 5)        # menu_mk / osd_mk2
    if game == 'mkp':
        m |= 1 << 2                             # menu_mkp (mask bit 2 with the class bit)
    if game == 'rev4':
        m |= 1 << 7                             # menu_rev4 (mask_7)
    m |= (fighter & 15) << 8                    # fm_line
    if plus:
        m |= (fighter >> 4) << 12               # Plus: the fighter's bit 4 (no classes)
    else:
        m |= (cls & 1) << 2 | (cls >> 1 & 1) << 12  # the class bits
    return m


def main():
    lines = [parse(l) for l in page_lines()]
    errs = []
    checked = 0
    # the class bits are mask bits 2 and 12 and no other line may use them
    for pre, rest in lines:
        for c, b in pre:
            if b in (2, 12) and not rest.startswith('P4'):
                errs.append('a line outside the Finishing Moves page tests a class bit: %r' % rest)
    classes = {}
    for name, gid in SETS:
        cls = T.set_class(gid, name)
        game = ('rev4' if name == 'mk2s08' else 'plus' if name in PLUS else 'mk2' if gid == G_MK2
                else 'mkp' if name == 'mk07' else 'mk')
        gone = T.missing_mask(gid, name)
        classes.setdefault(cls, set()).add(gone)
        for li, (fname, cid, moves) in enumerate(T.fighters(game)):
            mask = mask_for(game, li, cls)
            seen = []                            # (slot or None for a note line, text)
            for pre, rest in lines:
                if not rest.startswith('P4') or not shown(pre, mask):
                    continue
                m = re.match(r'P4R\[(\d+)\],(.*);$', rest)
                if m:
                    if int(m.group(1)) != T.CLEAR_BIT:           # "Clear the set move" is every set's
                        seen.append((int(m.group(1)) - T.SLOT_BIT, m.group(2)))
                    continue
                m = re.match(r'P4-,(.*);$', rest)
                if m and m.group(1).startswith(' ' * 12):
                    seen.append((None, m.group(1)))
            want = []
            for slot, (mname, kind, cmd, prog, dmin, dmax, note) in zip(T.slots(game, li), moves):
                if gone >> (li * 8 + slot) & 1:
                    continue
                want.append((RANK[kind], mname.lower(), slot, T.label(mname, T.osd_dist(dmin, dmax))))
            want = [(slot, text) for _, _, slot, text in sorted(want)]     # by type, then alphabetical
            checked += 1
            if seen != want:
                errs.append('%s %s: the page shows %s, the set has %s'
                            % (name, fname, [s for s, _ in seen], [s for s, _ in want]))
    # one Move List option (a line of the Extras page, P5) and one Sound Options page for each kind of set
    # (Plus has its own of both); the Auto Finishing Moves entry is a line of the Extras page too (page 4 inside 5)
    top = [parse(l) for l in top_lines()]
    lst = [parse(l) for l in macro_lines('FMOVES_LIST')]
    afm = [parse(l) for l in macro_lines('FMOVES_AFM')]
    for game, plus in (('mk', False), ('mk2', False), ('rev4', False), ('mk2', True)):
        mask = mask_for(game, 0, 0, plus)
        ml = [r for pre, r in lst if r.startswith('P5O[114],Move List') and shown(pre, mask)]
        ea = [r for pre, r in afm if r.startswith('P5P4,Auto Finishing Moves') and shown(pre, mask)]
        if len(ea) != 1:
            errs.append('%s%s: %d Auto Finishing Moves entries' % (game, ' Plus' if plus else '', len(ea)))
        so = [r for pre, r in top if shown(pre, mask)]
        if len(ml) != 1:
            errs.append('%s%s: %d Move List lines' % (game, ' Plus' if plus else '', len(ml)))
        if len(so) != 1:
            errs.append('%s%s: %d Sound Options pages %s' % (game, ' Plus' if plus else '', len(so), so))
    # one Character option for each game, with the game's fighters alphabetically, each on the status bits of the
    # game, and the option's pick mapped to the line of the fighter (fm_pick of rtl/tunit_fmoves_osd.svh)
    bits = {'mk': '30:28', 'mkp': '30:28', 'mk2': '27:24', 'rev4': '27:24', 'plus': '28:24'}
    pick = pick_map()
    for game in ('mk', 'mkp', 'mk2', 'rev4', 'plus'):
        mask = mask_for(game, 0, 0)
        ch = [r for pre, r in lines if re.match(r'P4O\[\d+:\d+\],Character,', r) and shown(pre, mask)]
        order = T.option_order(game)
        names = ','.join(n for n, _ in order)
        if len(ch) != 1 or ch[0].split(',', 2)[2].rstrip(';') != names or not ch[0].startswith('P4O[%s]' % bits[game]):
            errs.append('%s: the Character option is %s' % (game, ch))
        g = {'rev4': 1, 'plus': 2}.get(game, 0)
        for opt, (n, li) in enumerate(order):
            if pick.get((g, opt), opt) != li:
                errs.append('%s: fm_pick maps %s (option %d) to line %d, not %d' % (game, n, opt, pick.get((g, opt), opt), li))
    n = conf_len()
    if n > CONF_STR_MAX:
        errs.append('the CONF_STR is %d characters, over %d (Quartus: "loop must terminate within 10240 iterations")'
                    % (n, CONF_STR_MAX))
    for cls, masks in classes.items():
        if len(masks) != 1:
            errs.append('class %d holds sets that lack different moves' % cls)
    if len({next(iter(m)) for m in classes.values()}) != len(classes):
        errs.append('two classes lack the same moves')
    if errs:
        print('\n'.join(errs))
        print('FAIL: %d checks' % checked)
        sys.exit(1)
    print('osd_check: %d set x fighter pages, %d classes: all show exactly the set\'s moves; CONF_STR %d of %d characters'
          % (checked, len(classes), n, CONF_STR_MAX))


if __name__ == '__main__':
    main()

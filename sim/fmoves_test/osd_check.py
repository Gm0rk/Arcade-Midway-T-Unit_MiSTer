#!/usr/bin/env python3
"""
osd_check.py - checks the Finishing Moves page of the OSD (rtl/tunit_fmoves_osd.svh)

    python3 osd_check.py

Reads the generated CONF_STR lines of the page and renders them the way
Main_MiSTer does for a menu mask: an h<bit> prefix shows a line only when the
mask bit is set, an H<bit> prefix only when it is clear; a line is shown when
none of its prefixes hide it. The mask is built as the top level builds it
(Arcade-Midway-T-Unit.sv, status_menumask): bit 3 Mortal Kombat or II, bit 4
Mortal Kombat, bit 5 Mortal Kombat II, bits 8-11 the page's fighter, bit 2 and
bit 12 the class of the loaded set (ROM index 1 word 0x21F).

For every set that has finishing moves and every fighter the page must show
exactly the moves the set has, once each, in order, each with its note line,
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
SETS = [('mk', G_MK), ('mkr4', G_MK), ('mktturbo', G_MKTURBO),
        ('mk2', G_MK2), ('mk2r30', G_MK2), ('mk2r31e', G_MK2), ('mk2r32e', G_MK2),
        ('mk2r42', G_MK2), ('mk2r91', G_MK2), ('mk2chal', G_MK2),
        ('mk2r11', G_MK2), ('mk2r14', G_MK2), ('mk2r20', G_MK2), ('mk2r21', G_MK2)]


def page_lines():
    """The page's lines (strings of the FMOVES_OSD macro), in order."""
    t = open(os.path.join(ROOT, 'rtl', 'tunit_fmoves_osd.svh'), encoding='utf-8').read()
    body = t.split('`define FMOVES_OSD', 1)[1].split('`define CORE_INFO', 1)[0]
    return [m.replace('\\"', '"').replace('\\\\', '\\') for m in re.findall(r'"((?:\\.|[^"\\])*)"', body)]


def parse(line):
    """(hide prefixes [(h or H, bit)], rest) of a line."""
    pre = []
    while len(line) > 1 and line[0] in 'hH' and line[1] in HEX:
        pre.append((line[0], HEX.index(line[1])))
        line = line[2:]
    return pre, line


def shown(pre, mask):
    return all((mask >> b & 1) == (c == 'h') for c, b in pre)


def mask_for(game_mk2, fighter, cls):
    m = 1 << 3                                  # osd_ejb
    m |= 1 << (5 if game_mk2 else 4)            # osd_mk2 / menu_mk
    m |= fighter << 8                           # fm_line
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
        game = 'mk2' if gid == G_MK2 else 'mk'
        gone = T.missing_mask(gid, name)
        classes.setdefault(cls, set()).add(gone)
        for li, (fname, cid, moves) in enumerate(T.fighters(game)):
            mask = mask_for(game == 'mk2', li, cls)
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
            for slot, (mname, kind, cmd, prog, dmin, dmax, note) in enumerate(moves):
                if gone >> (li * 8 + slot) & 1:
                    continue
                want.append((slot, T.label(mname, cmd)))
                if note:
                    want.append((None, ' ' * 12 + note))
            checked += 1
            if seen != want:
                errs.append('%s %s: the page shows %s, the set has %s'
                            % (name, fname, [s for s, _ in seen], [s for s, _ in want]))
    for cls, masks in classes.items():
        if len(masks) != 1:
            errs.append('class %d holds sets that lack different moves' % cls)
    if len({next(iter(m)) for m in classes.values()}) != len(classes):
        errs.append('two classes lack the same moves')
    if errs:
        print('\n'.join(errs))
        print('FAIL: %d checks' % checked)
        sys.exit(1)
    print('osd_check: %d set x fighter pages, %d classes: all show exactly the set\'s moves' % (checked, len(classes)))


if __name__ == '__main__':
    main()

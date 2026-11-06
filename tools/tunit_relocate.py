#!/usr/bin/env python3
# Copyright (C) 2026 Gm0rk - GPL-3.0-or-later
"""
tunit_relocate.py - a rebuilt game's cheat picks from its parent's

A ROM hack that is the same game rebuilt from source (NBA Jam Tournament
Edition Special Edition, the hack of tools/hbmame_sets.py) has the parent's
code with its RAM variables and jump distances moved. The MAME cheat files
have no cheats for it, so tools/tunit_cheats_data.py's entry for it is derived
from the parent's, here:

    python3 tools/tunit_relocate.py PARENT SET PARENT_MAINCPU.bin SET_MAINCPU.bin \\
        [--skip "Cheat name" ...]

PARENT_MAINCPU.bin / SET_MAINCPU.bin are the sets' program regions (the first
0x100000 bytes of the MRA's rom index 0). For every unit of every cheat the
parent's entry has:

  - a RAM unit (a variable of main RAM): the program refers to a variable by
    its 32-bit address (an opcode word, the address low word, the high word).
    Each reference is found in the set's program by the 16 words around it (the
    address words themselves left out; the window must agree in at least 2/3 of
    the words and have one best match) and the address read there. The
    variable's new address is the one every reference gives. A variable the
    program only reaches through a pointer (the players' turbo, in a record
    array) has no reference: it moves with the variables around it, when the
    nearest referenced variables below and above it moved by the same distance.
  - a program ROM word (flag F): found by the 24 words around it (one best
    match, at least half of them equal, and the set's word must be the parent's
    word). The patch keeps its value when it changes only the condition of the
    jump (the low byte, the distance, stays); when it makes the jump
    unconditional to another place (C0nn), the place is found the same way and
    the new distance written.

A unit that cannot be derived is reported and its whole cheat left out.

Output: the lines of the entry, ready to paste into tunit_cheats_data.py.
"""

import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tunit_cheats_data  # noqa: E402

ROM_BASE = 0xFF800000
RAM_LO, RAM_HI = 0x01000000, 0x01100000


def words(path):
    d = open(path, 'rb').read()[:0x100000]
    return [d[i] | (d[i + 1] << 8) for i in range(0, len(d), 2)]


class Image:
    def __init__(self, w):
        self.w = w
        self.at = {}
        for i, x in enumerate(w):
            self.at.setdefault(x, []).append(i)

    def best(self, parent, i, pre, post, skip=()):
        """Positions of this image that agree best with the parent's words around
        parent word i (offsets in skip left out; word i itself too): (agree,
        compared, [positions])."""
        score = Counter()
        n = 0
        for k in range(-pre, post + 1):
            if k == 0 or k in skip or not 0 <= i + k < len(parent):
                continue
            n += 1
            for j in self.at.get(parent[i + k], ()):
                if 0 <= j - k < len(self.w):
                    score[j - k] += 1
        if not score:
            return 0, n, []
        top = max(score.values())
        return top, n, [j for j, c in score.items() if c == top]


_REFS = {}


def ram_refs(parent, addr):
    """Word positions where the parent's program has addr as a 32-bit operand."""
    if id(parent) not in _REFS:
        idx = {}
        for i in range(len(parent) - 1):
            if RAM_LO >> 16 <= parent[i + 1] < RAM_HI >> 16:
                idx.setdefault((parent[i], parent[i + 1]), []).append(i)
        _REFS[id(parent)] = idx
    return _REFS[id(parent)].get((addr & 0xFFFF, addr >> 16), [])


def ram_delta(parent, child, addr):
    """The distance the variable at addr moved, from its references, or None."""
    ds = Counter()
    for i in ram_refs(parent, addr):
        agree, n, js = child.best(parent, i, 8, 9, skip=(1,))
        if len(js) == 1 and agree * 3 >= n * 2:
            j = js[0]
            ds[(child.w[j] | (child.w[j + 1] << 16)) - addr] += 1
    if not ds:
        return None
    (d, c), = ds.most_common(1)
    return d if c == sum(ds.values()) else None


def ram_neighbours(parent, child, addr, span=0x2000):
    """The distance of an unreferenced variable: the nearest referenced variables
    below and above it (within span bits) moved the same distance."""
    below = above = None
    for a in range(addr - 0x10, addr - span, -0x10):
        d = ram_delta(parent, child, a)
        if d is not None:
            below = d
            break
    for a in range(addr + 0x10, addr + span, 0x10):
        d = ram_delta(parent, child, a)
        if d is not None:
            above = d
            break
    return below if below is not None and below == above else None


def rom_word(parent, child, addr, value):
    """(new address, new value) of a program ROM patch, or None."""
    i = (addr - ROM_BASE) // 16
    agree, n, js = child.best(parent, i, 12, 12)
    if len(js) != 1 or agree * 2 < n or child.w[js[0]] != parent[i]:
        return None
    j = js[0]
    new = value
    if (value ^ parent[i]) & 0xFF and (value >> 8) == 0xC0:          # a jump made unconditional
        target = i + 1 + (value & 0xFF)
        a2, n2, ts = child.best(parent, target, 0, 15)
        if len(ts) != 1 or a2 * 4 < n2 * 3:
            return None
        dist = ts[0] - (j + 1)
        if not 0 < dist < 0x100:
            return None
        new = 0xC000 | dist
    return ROM_BASE + j * 16, new


def derive(parent_name, parent_w, child_w, skip):
    parent, child = parent_w, Image(child_w)
    out, bad = [], []
    for name, units in tunit_cheats_data.CHEATS[parent_name]:
        if name in skip:
            continue
        new = []
        for addr, value, mask, fl in units:
            if 'F' in fl:
                r = rom_word(parent, child, addr, value)
                if r is None:
                    break
                new.append((r[0], r[1], mask, fl))
            else:
                d = ram_delta(parent, child, addr)
                if d is None:
                    d = ram_neighbours(parent, child, addr)
                if d is None:
                    break
                new.append((addr + d, value, mask, fl))
        else:
            out.append((name, new))
            continue
        bad.append(name)
    return out, bad


def main():
    a = sys.argv[1:]
    skip = set()
    while '--skip' in a:
        k = a.index('--skip')
        skip.add(a[k + 1])
        del a[k:k + 2]
    if len(a) != 4:
        print(__doc__)
        sys.exit(2)
    out, bad = derive(a[0], words(a[2]), words(a[3]), skip)
    print('    %r: [' % a[1])
    for name, units in out:
        us = ', '.join("(0x%08X, 0x%04X, 0x%04X, %r)" % u for u in units)
        print("        (%r, [%s])," % (name, us))
    print('    ],')
    for name in bad:
        print('not derived: %s' % name, file=sys.stderr)


if __name__ == '__main__':
    main()

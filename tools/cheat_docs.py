#!/usr/bin/env python3
# Copyright (C) 2026 Gm0rk - GPL-3.0-or-later
"""Markdown tables of the OSD's Cheats menu for the game pages, from the MRAs.

    python3 tools/cheat_docs.py mra/ mk|mk2|nba|te|jd

One row per cheat: its menu name, the units it uses of the 8 the menu allows
on at once and the versions that have it, named by their MAME set ("All" when
every version of the game does, "All but ..." when most do). The MRA is the
source of truth: the cheats are what its <cheats> block lists.
"""

import glob
import os
import re
import sys
import xml.etree.ElementTree as ET

GAMES = {
    'mk': ('Mortal Kombat', lambda n: n.startswith('Mortal Kombat (')),
    'mk2': ('Mortal Kombat II', lambda n: n.startswith('Mortal Kombat II')),
    'nba': ('NBA Jam', lambda n: n.startswith('NBA Jam (')),
    'te': ('NBA Jam Tournament Edition', lambda n: n.startswith('NBA Jam Tournament Edition')),
    'jd': ('Judge Dredd', lambda n: n.startswith('Judge Dredd')),
}


def version(root):
    return root.findtext('setname') or root.findtext('name')


def table(mra_dir, game):
    title, sel = GAMES[game]
    sets = []
    for p in sorted(glob.glob(os.path.join(mra_dir, '**', '*.mra'), recursive=True)):
        root = ET.parse(p).getroot()
        name = root.findtext('name')
        if not sel(name):
            continue
        cheats = root.find('cheats')
        names = {}
        if cheats is not None:
            for c in cheats.findall('cheat'):
                names[c.get('name')] = len(''.join((c.text or '').split())) // 16
        sets.append((version(root), names))
    allnames = sorted({n for _, ns in sets for n in ns}, key=str.lower)
    out = ['| Cheat | Units | Versions |', '|---|---|---|']
    for n in allnames:
        have = [v for v, ns in sets if n in ns]
        us = sorted({ns[n] for _, ns in sets if n in ns})
        units = str(us[0]) if len(us) == 1 else '%d-%d' % (us[0], us[-1])
        miss = [v for v, ns in sets if n not in ns]
        if not miss:
            where = 'All'
        elif len(miss) < len(have):
            where = 'All but ' + ', '.join(miss)
        else:
            where = ', '.join(have)
        out.append('| %s | %s | %s |' % (n, units, where))
    return '\n'.join(out) + '\n', sets, allnames


if __name__ == '__main__':
    t, sets, names = table(sys.argv[1], sys.argv[2])
    print(t, end='')
    print('\n%d cheats; versions: %s' % (len(names), ', '.join('%s (%d)' % (v, len(ns)) for v, ns in sets)), file=sys.stderr)

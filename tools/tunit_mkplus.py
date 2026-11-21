#!/usr/bin/env python3
"""
tunit_mkplus.py - Mortal Kombat Plus (the hack): the Move List window data

Mortal Kombat Plus (HBMAME mk07, "v5.0.0741"; MRA with the Plus flag, ROM
index 1 word 0 bit 10) is a hack of rev 5.0. The OSD's Move List option draws
its pages in the information window (rtl/tunit_window.sv; the pages are laid
out by tools/tunit_window.py from the data here) in place of the stock
Mortal Kombat pages. The set's Auto Finishing Moves page is Mortal Kombat's.

The data is the move list of the MKKomplete guide for the hack,
    https://icemantraveler.github.io/mkksg/fan_made/mkplus/default.htm
read for every fighter. It was not played back in the core. The ROM has the
same seven fatality handlers as rev 5.0, at the same addresses (the checks of
tools/mra_check.py); the page's Liu Kang fatality and Kano Cannonball are
written differently from the rev 5.0 page's, and the guide is followed. The guide marks what Plus adds with a plus; the pages
mark the same rows with a + in the left margin.

Commands are written as in the Finishing Moves page (tools/tunit_fmoves.py):
"F F HP" in turn, "LP+BL" together, "(BL) F D B U F" hold BL while entering
F D B U F, then let go. Distances are the guide's words: Close (right next to
the opponent), Sweep (a couple of steps away, close enough to land a sweep),
Anywhere.

Usage:
    tunit_mkplus.py            list the fighters
    tunit_mkplus.py --docs     the game page's tables

Copyright (C) 2026 Gm0rk - GPL-3.0-or-later
"""

import sys

GUIDE_URL = 'https://icemantraveler.github.io/mkksg/fan_made/mkplus/default.htm'
SET_NAME = 'mk07'

CLOSE, SWEEP, ANY = 'Close', 'Sweep', 'Anywhere'
BABALITY_RULE = 'do not press LP, HP or BL in either round'


def S(move, cmd, dist=None, note=None, plus=False):
    """A special move: dist when the guide gives one, note a line under it,
    plus: an addition of Plus"""
    return {'name': move, 'cmd': cmd, 'dist': dist, 'note': note, 'plus': plus}


def F(name, cmd, dist, note=None):
    """A finishing move (Fatality 1 and 2, the Babality)"""
    return {'name': name, 'cmd': cmd, 'dist': dist, 'note': note}


# (fighter, hidden, special moves, fatalities, babality), the guide's order
FIGHTERS = [
    dict(name='Johnny Cage', hidden=False,
         special=[S('Green Bolt', 'B F LP'), S('Shadow Kick', 'B F LK'),
                  S('Split Punch', 'LP+BL', CLOSE)],
         fatal=[F('Decap Uppercut', 'F F F HP', CLOSE)],
         baby=F('Babality', 'D D D HK', ANY)),
    dict(name='Kano', hidden=False,
         special=[S('Knife Throw', '(BL B F)'),
                  S('Cannonball', '(BL) F D B U F', note='hold BL to extend the hover')],
         fatal=[F('Heart Rip', 'B D F LP', CLOSE)],
         baby=F('Babality', 'F D B LK', ANY)),
    dict(name='Liu Kang', hidden=False,
         special=[S('Fireball', 'F F HP'), S('Flying Kick', 'F F HK')],
         fatal=[F('Butterfly Kick', '(BL) F D B U F', ANY,
                  'Deadly Uppercut; must be within range to connect')],
         baby=F('Babality', 'B F F LK', ANY)),
    dict(name='Raiden', hidden=False,
         special=[S('Lightning Bolt', 'D F LP'), S('Torpedo', 'B B F', note='also works in the air', plus=True),
                  S('Teleport', 'D U')],
         fatal=[F('Electro-Decap', 'F B B B HP', CLOSE)],
         baby=F('Babality', 'B D B HK', ANY)),
    dict(name='Scorpion', hidden=False,
         special=[S('Spear', 'B B LP'),
                  S('Teleport Punch', 'D B HP', note='also works in the air', plus=True)],
         fatal=[F('Toasty!', '(BL) U U', SWEEP)],
         baby=F('Babality', 'D B B HK', ANY)),
    dict(name='Sonya', hidden=False,
         special=[S('Energy Rings', 'LP B LP'), S('Leg Grab', 'D+LP+LK+BL', CLOSE),
                  S('Square Wave Punch', 'F B HP')],
         fatal=[F('Flame Kiss', 'F F B B BL', ANY,
                  'hold BL for F F B B, let go, then press BL again')],
         baby=F('Babality', 'F B F HK', ANY)),
    dict(name='Sub-Zero', hidden=False,
         special=[S('Freeze', 'D F LP'), S('Slide', 'B+LP+LK+BL')],
         fatal=[F('Spine Rip', 'F D F HP', CLOSE)],
         baby=F('Babality', 'D B B HK', ANY)),
    dict(name='Reptile', hidden=True,
         special=[S('Freeze', 'D F LP', plus=True), S('Slide', 'B+LP+LK+BL', plus=True),
                  S('Spear', 'B B LP', plus=True),
                  S('Teleport Punch', 'D B HP', note='also works in the air', plus=True)],
         fatal=[F('Spine Rip', 'F D F HP', CLOSE), F('Toasty!', '(BL) U U', SWEEP)],
         baby=F('Babality', 'D B B HK', ANY)),
]

for _f in FIGHTERS:
    _f['special'].sort(key=lambda s: s['name'].lower())      # the page and the Move List list moves alphabetically
FIGHTERS.sort(key=lambda f: f['name'].lower())               # and the fighters (Reptile too)


def finishing(f):
    """A fighter's finishing moves as rows (name, command, distance, note), the Babality
    and the fatalities ("Fatality: name") in alphabetical order."""
    rows = [dict(x, name='Fatality: ' + x['name']) for x in f['fatal']] + [f['baby']]
    return sorted(rows, key=lambda x: x['name'].lower())


# moves every fighter has: (move, command, distance)
GENERAL = [
    ('Throw', 'LP', CLOSE), ('Head-Blow', 'HP', CLOSE), ('Knee', 'LK / HK', CLOSE),
    ('Crouched Block', 'D+BL', None), ('Uppercut', 'D+LP / HP', None),
    ('Crouched Kick', 'D+LK / HK', None), ('Foot Sweep', 'B+LK', None),
    ('Roundhouse Kick', 'B+HK', None), ('Flying Punch', 'U / UF / UB+LP / HP', None),
    ('Flying Kick', 'U / UF / UB+LK / HK', None),
]
# the Plus-only fighter and the other additions, in words
ADDITIONS = [
    "Raiden's Torpedo and Scorpion's Teleport Punch also work in the air",
    "Reptile is a hidden fighter: Sub-Zero's and Scorpion's moves and fatalities, "
    "his own second fatality",
]
NOTES = [
    ('Babalities', BABALITY_RULE),
    ('Liu Kang', 'Butterfly Kick, also called Deadly Uppercut: it must be within range to connect'),
    ('Kano', 'Cannonball: hold BL to extend the hover'),
    ('The Pit', 'finish with an uppercut (D+HP), close, on The Pit stage only'),
    ('Holding BL', 'you can hold BL through a fatality, but let go before the last '
                   'button (Sonya: hold BL for F F B B, let go, then press BL again)'),
]
DISTANCES = [
    (CLOSE, 'right next to the opponent'),
    (SWEEP, 'a couple of steps away, close enough to land a sweep'),
    (ANY, 'any range'),
]


def docs_tables():
    """The game page's Mortal Kombat Plus tables (docs/MortalKombat.md)"""
    out = ['| Fighter | Move | Command | Distance |', '|---|---|---|---|']
    for f in FIGHTERS:
        first = True
        name = f['name'] + (' (hidden)' if f['hidden'] else '')
        rows = [('%s%s' % ('+ ' if s['plus'] else '', s['name']), s['cmd'], s['dist'] or '', s['note'])
                for s in f['special']]
        rows += [(x['name'], x['cmd'], x['dist'], x['note']) for x in finishing(f)]
        for m, c, d, note in rows:
            out.append('| %s | %s | %s%s | %s |' % (name if first else '', m, c, ', ' + note if note else '', d))
            first = False
    return '\n'.join(out) + '\n'


def main():
    if sys.argv[1:] == ['--docs']:
        print(docs_tables(), end='')
        return
    for f in FIGHTERS:
        print('%-12s %d specials, %d fatalities, a Babality%s' % (
            f['name'], len(f['special']), len(f['fatal']), '  (hidden)' if f['hidden'] else ''))


if __name__ == '__main__':
    main()

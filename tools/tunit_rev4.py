#!/usr/bin/env python3
"""
tunit_rev4.py - Mortal Kombat II rev 4.0 (the hack): the Move List window data

Mortal Kombat II (rev 4.0, hack; HBMAME mk2s08, "mk2rev4" in FBNeo) is
junkwax's rebuild of MK2 with new moves, three hidden fighters (Ermac, Jade,
Rain), back-block, perfect block, combo scaling and more. The OSD's Move List
option draws its pages in the information window (rtl/tunit_window.sv; the
pages are laid out by tools/tunit_window.py from the data here), in place of
the stock MK2 pages (the MRA's index 1 word 0 bit 9, tools/tunit_secrets.py
MOVE_LIST_REV4).

The data is the author's own move list, MOVES.md of
    https://github.com/junkwax/mk2-rev4        (the page: junkwax.github.io/mk2-rev4)
read for every fighter, finisher, system change and secret opponent. It was
not played back in the core or checked in the hack's code. The guide marks what
the build adds to arcade MK2 (L3.1) with NEW; the pages mark the same rows with
a + in the left margin.

Commands are written as in the Finishing Moves page (tools/tunit_fmoves.py):
"F F HP" in turn, "LP+BL" together, "(LP) B F" hold LP while entering B F,
"(LK 2 s)" hold LK about 2 seconds, then let go. Distances are the guide's
words: Close, Sweep, Mid, Far, Anywhere.

Usage:
    tunit_rev4.py            list the fighters and the other pages' data
    tunit_rev4.py --docs     the game page's tables

Copyright (C) 2026 Gm0rk - GPL-3.0-or-later
"""

import re
import sys

GUIDE_URL = 'https://junkwax.github.io/mk2-rev4/'
REPO_URL = 'https://github.com/junkwax/mk2-rev4'
GUIDE_VERSION = 'v4.0'

CLOSE, SWEEP, MID, FAR, ANY = 'Close', 'Sweep', 'Mid', 'Far', 'Anywhere'
DISTANCES = (CLOSE, SWEEP, MID, FAR, ANY)


def S(move, cmd, note=None, new=False):
    """A special move: a note after the command (or under it); new: the guide
    marks it (or its input, or what it does) NEW"""
    return (move, cmd, note, new)


def F(name, cmd, dist, then=None, note=None, new=False):
    """A finishing move: then: [(command, distance)] for a second part, note:
    a line (or a list of lines) under it"""
    return {'name': name, 'cmd': cmd, 'dist': dist, 'then': list(then or []), 'note': note,
            'new': new, 'plus': new, 'adds': []}


def stage(cmd):
    return F('Stage Fatality', cmd, CLOSE)


def baby(cmd, new=False):
    return F('Babality', cmd, ANY, new=new)


STAGE_NOTE = 'Kombat Tomb, The Pit II, Yoteigai Tor, The Pit (MK1)'

# the 12 fighters in the select screen's order, then the three hidden ones
FIGHTERS = [
    {'name': 'Liu Kang',
     'special': [S('High Fireball', 'F F HP', 'also in air'), S('Low Fireball', 'F F LP'),
                 S('Flying Kick', 'F F HK'), S('Bicycle Kick', '(LK 2 s)'),
                 S('Backfist', 'B+HP', 'standing', new=True),
                 S('Double Knee', 'HK HK', 'close; the 2nd HK at once bounces him', new=True)],
     'finish': [F('Dragon', 'D F B B HK', SWEEP),
                F('Cartwheel', '(BL) D F U B D', MID),
                F('Red Dragon Flame', 'BL', MID, note='in the Start+LP (red) costume only', new=True),
                baby('D D F B LK'), stage('B F F LK')]},
    {'name': 'Kung Lao',
     'special': [S('Hat Throw', 'B F LP', 'U / D steer it; hold LP: it returns', new=True),
                 S('Teleport', 'D U'),
                 S('Spin', 'F F LK', 'arcade: U U', new=True),
                 S('Dive Kick', 'D+HK', 'in air, near the top of a jump'),
                 S('Air Escape', 'F F LP', 'in air', new=True),
                 S('Backfist', 'B+HP', 'standing', new=True)],
     'finish': [F('Hat Slice', 'F F F LK', SWEEP),
                F('Hat Decapitation', '(LP) B F', FAR),
                baby('B B F F HK'), stage('F F F HP')]},
    {'name': 'Johnny Cage',
     'special': [S('Low Green Bolt', 'D F LP', 'arcade: B D F; U / D steer it', new=True),
                 S('Shadow Kick', 'B F LK'),
                 S('Shadow Uppercut', 'B B HP', 'arcade: B D B', new=True),
                 S('Ceiling Uppercut', 'F F B HP', new=True),
                 S('Nut Punch', 'BL+LP'),
                 S('Power Punch', 'B+HP', 'standing', new=True)],
     'finish': [F('Torso Rip', 'D D F F LP', CLOSE),
                F('Triple Head Pop', 'F F D U', CLOSE, note='no button'),
                F('Brain Punch', 'F B B HP', CLOSE, new=True),
                baby('B B B HK'), stage('D D D HK')],
     'note': 'No high green bolt; the low bolt aims anywhere.'},
    {'name': 'Reptile',
     'special': [S('Slow Forceball', 'B B HP+LP', 'U / D steer it', new=True),
                 S('Fast Forceball', 'F F HP+LP', new=True),
                 S('Acid Spit', 'F F HP', 'also in air', new=True),
                 S('Invisibility', 'U U D HP'),
                 S('Slide', 'B+LP+BL+LK'),
                 S('Dive Kick', 'D+HK', 'in air, near the top; afterimage', new=True)],
     'finish': [F('Tongue', 'B B D LP', MID, note='while visible'),
                F('Invisible Slice', 'F F D HK', CLOSE, note='turn invisible first'),
                baby('D B B LK'), stage('D F F BL')]},
    {'name': 'Sub-Zero',
     'special': [S('Ice Ball', 'D F LP', 'also in air', new=True),
                 S('Ground Freeze', 'D B LK', 'now also in a corner', new=True),
                 S('Slide', 'B+LP+BL+LK'),
                 S('Tornado', 'D B LP', "Midway's cut move, back", new=True)],
     'finish': [F('Deep Freeze', 'F F D HK', MID, then=[('F D F F HP', CLOSE)],
                  note='freeze him, then shatter'),
                F('Ice Bomb', '(LP) B B D F', FAR),
                F('Head Rip', 'F D F LP', CLOSE, new=True),
                baby('D B B HK'), stage('D F F BL')]},
    {'name': 'Shang Tsung',
     'special': [S('Skull', 'B B HP'), S('2 Skulls', 'B B F HP'), S('3 Skulls', 'B B F F HP'),
                 S('Round Punch', 'B+HP', 'standing', new=True),
                 S('Elbow Chain', 'HP HP', 'close; a second elbow', new=True),
                 S('Drop a Morph', 'BL+U+HK', 'back to Shang from any form', new=True)],
     'morph': [('Baraka', 'D D LK'), ('Jax', 'D F B HK'), ('Johnny Cage', 'B B D LP'),
               ('Kitana', 'BL BL BL'), ('Kung Lao', 'B D B HK'), ('Liu Kang', 'B F F BL'),
               ('Mileena', '(HP 1 s)'), ('Raiden', 'D B F LK'), ('Reptile', '(BL) U D HP'),
               ('Scorpion', '(BL) U U'), ('Sub-Zero', 'F D F HP'),
               ('+Ermac', '(BL) D D U'), ('+Jade', 'F F D D BL'), ('+Rain', '(D+BL) LK')],
     'morph_note': '+ new: Ermac, Jade and Rain',
     'finish': [F('Soul Steal', 'U D U+LK', CLOSE),
                F('Backflip Decap', 'F D F LK', CLOSE, new=True),
                F('Blade Decap', 'B B F U LP', SWEEP, new=True),
                F('Inner-Ear Explosion', '(HK 3 s)', 'Sweep or far', note='facing him'),
                F('Kintaro', '(LP 30 s)', SWEEP),
                baby('B F D HK'), stage('D D U D')]},
    {'name': 'Kitana',
     'special': [S('Fan Throw', 'F F HP+LP', 'in air; U / D steer; HP: it returns', new=True),
                 S('Fan Lift', 'B B B HP'), S('Square Wave Punch', 'F D B HP'),
                 S('Fan Swipe', 'B+HP', 'standing', new=True)],
     'finish': [F('Kiss of Death', '(LK) F F D F', CLOSE),
                F('Fan Decapitation', 'BL BL BL HK', CLOSE, note='two swings, out and back', new=True),
                baby('D D D LK'), stage('F D F HK')]},
    {'name': 'Mileena',
     'special': [S('Sai Throw', '(HP 0.5 s)', 'in air'), S('Teleport Kick', 'F F LK'),
                 S('Ground Roll', 'B B D HK')],
     'finish': [F('Sai Stab', 'F B F LP', CLOSE, note='she cuts him in half', new=True),
                F('Body Suck', '(HK 2 s)', CLOSE),
                baby('D D D HK'), stage('F D F LK')]},
    {'name': 'Scorpion',
     'special': [S('Spear', 'B B LP'), S('Teleport Punch', 'D B HP', 'in air'),
                 S('Forward Teleport', 'D F HP', 'in air; lands in front', new=True),
                 S('Leg Takedown', 'F D B LK'),
                 S('Air Throw', 'BL', 'in air, next to an airborne foe'),
                 S('Sword Slash', 'B+HP', 'standing', new=True)],
     'finish': [F('Toasty (MK2 burn)', 'D D U U HP', ANY),
                F('MK1 Burn', 'U U HP', MID, note='the MK1 flame and skeleton', new=True),
                F('Spear Slice', '(HP) D F F F', CLOSE),
                baby('D B B HK'), stage('D F F BL')]},
    {'name': 'Raiden',
     'special': [S('Lightning', 'D F LP', 'U / D steer it', new=True), S('Teleport', 'D U'),
                 S('Torpedo', 'B B F', 'no button'),
                 S('Electric Grab', '(HP 1.5 s)', 'close'),
                 S('Short Lightning', 'B+HP', 'standing', new=True)],
     'finish': [F('Electrocution', '(LK 2 s)', CLOSE, note='then tap BL+LK'),
                F('Exploding Uppercut', '(HP 7 s)', CLOSE),
                F('Lift', '(HK 3 s)', CLOSE, note='then hold U, tap HP', new=True),
                baby('D D U HK'), stage('U U HP')],
     'note': 'Lightning matches the costume: blue, red, purple.'},
    {'name': 'Baraka',
     'special': [S('Blade Sparks', 'D B HP', 'U / D steer it', new=True),
                 S('Blade Fury', 'B B B LP'),
                 S('Blade Spin', 'U U LK', 'as the jump starts', new=True),
                 S('Sword Kick', 'D+LP+BL', 'handstand on a blade; scissors him', new=True),
                 S('Blade Swipe', 'B+HP', 'standing')],
     'finish': [F('Decapitation', 'B B B B HP', SWEEP),
                F('Impale', 'B F D F LP', MID),
                baby('F F F HK'), stage('F F D HK')]},
    {'name': 'Jax',
     'special': [S('Energy Wave', 'F D B HK', 'also in air; flies flat', new=True),
                 S('Gotcha Grab', 'F F LP', 'tap LP for more punches'),
                 S('Ground Pound', '(LK 2 s)'),
                 S('Backbreaker', 'BL', 'in air, next to an airborne foe'),
                 S('Multi-Slam', 'tap HP', 'quickly, during his throw'),
                 S('Power Punch', 'B+HP', 'standing', new=True)],
     'finish': [F('Head Clap', '(LP) F F F', CLOSE),
                F('Arm Rip', 'BL BL BL BL LP', SWEEP),
                baby('D U D U LK'), stage('U U D LK')]},
    # the hidden fighters: a START tap on a fighter at the select screen
    {'name': 'Jade', 'select': 'tap START on Kitana',
     'special': [S('Boomerang, high', 'B F HP'), S('Boomerang, straight', 'B F LP'),
                 S('Boomerang, low', 'B F LK'), S('Boomerang, returning', 'B B F LP'),
                 S('Shadow Kick', 'D F LK'),
                 S('Flash', 'B F HK', 'shots pass through her')],
     'finish': [F('Staff Impale', 'BL BL BL F BL', CLOSE, new=True),
                baby('D D D LK'), stage('F D F HK')]},
    {'name': 'Ermac', 'select': 'tap START on Scorpion',
     'special': [S('Teleport Punch', 'D B HP', 'in air'), S('Fireball', 'D B LP'),
                 S('Telekinetic Slam', 'B D B HK', 'not past the 5th hit; 2 s apart')],
     'finish': [F('Telekinetic Slam', 'D U D D D BL', MID, new=True),
                F('Telekinetic Head Rip', 'F B F F LK', FAR, new=True),
                baby('D B B LK', new=True), stage('D F F BL')]},
    {'name': 'Rain', 'select': 'tap START on Sub-Zero',
     'special': [S('Lightning Bolt', 'B B HP', 'hits where he stood; not 3+ hits in', new=True),
                 S('Storm Cloud', 'D F HP', 'U / D steer; move him with the stick', new=True),
                 S('Super Roundhouse', 'B+HK', 'knocks him across the screen', new=True)],
     'finish': [F('Lightning', 'D D B F HK', MID, new=True),
                baby('D B B HK', new=True), stage('D F F BL')]},
]

for _f in FIGHTERS:            # each fighter's moves alphabetically (the Move List window and the docs)
    _f['special'].sort(key=lambda s: s[0].lower())
    _f['finish'].sort(key=lambda x: x['name'].lower())
    if _f.get('morph'):
        _f['morph'].sort(key=lambda m: m[0].lstrip('+').lower())
FIGHTERS.sort(key=lambda f: f['name'].lower())       # the fighters' pages and tables in alphabetical order too

HIDDEN_ARCADE = ('On an arcade board they are earned: beat Jade in her secret fight for Jade, '
                 'Shao Kahn for Ermac, Smoke for Rain. In the FBNeo set all three are there from '
                 'power-on.')

# what is different in rev 4.0: (label, text), two pages
SYSTEM_1 = [
    ('Hidden fighters', 'at the select screen, tap START on Scorpion (Ermac), Kitana (Jade) or '
                        'Sub-Zero (Rain); tap again to switch back'),
    ('Back-block', 'on by default: hold Back from the opponent to block'),
    ('Special from block', 'holding BL no longer stops a special: cancel a block into one'),
    ('Perfect block', 'tap BL just before a hit lands: a quarter of the chip damage and a '
                      'faster recovery; holding does not count'),
    ('Combo scaling', 'each extra hit in a string does less damage; throws and holds scale too'),
    ('Anti-juggle', 'after more than 3 hits the attacker is pushed away and held until the '
                    'victim lands'),
]
SYSTEM_2 = [
    ('Draws', 'the first tie is a DRAW; the next is SUDDEN DEATH: both on 10% health, any '
              'hit wins, no chip damage'),
    ('Costumes', 'hold START and press HP, LP, HK, LK or BL (or insert a coin) as you pick a '
                 'fighter; two players never share colours'),
    ('Friendships', 'none in this build'),
    ('Babalities', 'a round won without any punch (HP or LP)'),
    ('Stage Fatalities', STAGE_NOTE),
    ('The Dead Pool', 'an uppercut (D+HP) during FINISH HIM knocks him into the acid'),
]

# secret opponents (one-player)
SECRETS = [
    ('Jade', 'on the match right before the "?" on the Battle Plan, win a round with only '
             'LK: no HP, LP, HK or BL at all'),
    ('Smoke', 'on The Portal, when Dan Forden says "Toasty!" after an uppercut, quickly press '
              'D+START'),
    ('Noob Saibot', 'on the Battle Plan screen between matches, hold START for about 3 seconds'),
    ('Khameleon', 'on the Battle Plan screen, tap START five times'),
]
# on an arcade board the hidden fighters are earned (MOVES.md, System changes)
SECRET_NOTE = (
    'On an arcade board the hidden fighters are earned',
    'in a 1-player game: beat Jade for Jade, Shao Kahn',
    'for Ermac, Smoke for Rain. Unlocks are saved.',
)


def hold_time(cmd):
    """True when a command has a held-for-seconds part, (X 3 s)"""
    return re.search(r'\(\w+ [0-9.]+ s\)', cmd) is not None


def _note(note):
    """A note as a parenthesis after the command"""
    if not note:
        return ''
    return ' (%s)' % (', '.join(note) if isinstance(note, list) else note)


def docs_tables():
    """Markdown tables for the game page (docs/MortalKombatII.md), by name:
    specials, finishing, system, secrets. A plus marks what the guide marks NEW."""
    t = {}
    out = ['| Fighter | Move | Command |', '|---|---|---|']
    for f in FIGHTERS:
        first = True
        name = f['name'] + (' (%s)' % f['select'] if f.get('select') else '')
        rows = [('%s%s' % ('+ ' if new else '', m), c + _note(note))
                for m, c, note, new in f['special']]
        rows += [('Morph into %s' % n.lstrip('+'), c) for n, c in f.get('morph', [])]
        for m, c in rows:
            out.append('| %s | %s | %s |' % (name if first else '', m, c))
            first = False
    t['specials'] = out
    out = ['| Fighter | Move | Command | Distance |', '|---|---|---|---|']
    for f in FIGHTERS:
        first = True
        for x in f['finish']:
            cmd = ', then '.join([x['cmd']] + [c for c, d in x['then']])
            dist = ', then '.join([x['dist']] + [d for c, d in x['then']])
            out.append('| %s | %s%s | %s%s | %s |' % (f['name'] if first else '', '+ ' if x['new'] else '',
                                                    x['name'], cmd, _note(x['note']), dist))
            first = False
    t['finishing'] = out
    out = ['| What | Rev 4.0 |', '|---|---|']
    for label, text in SYSTEM_1 + SYSTEM_2:
        out.append('| %s | %s |' % (label, text))
    t['system'] = out
    out = ['| Opponent | How |', '|---|---|']
    for label, text in SECRETS:
        out.append('| %s | %s |' % (label, text))
    t['secrets'] = out
    return {k: '\n'.join(v) + '\n' for k, v in t.items()}


def docs():
    return '\n'.join(docs_tables()[k] for k in ('specials', 'finishing', 'system', 'secrets'))


def main():
    if sys.argv[1:] == ['--docs']:
        print(docs(), end='')
        return
    for f in FIGHTERS:
        print('%-12s %2d specials, %2d finishing moves%s' % (
            f['name'], len(f['special']) + len(f.get('morph', [])), len(f['finish']),
            '  (hidden)' if f.get('select') else ''))
    print('%d system changes, %d secret opponents' % (len(SYSTEM_1) + len(SYSTEM_2), len(SECRETS)))


if __name__ == '__main__':
    main()

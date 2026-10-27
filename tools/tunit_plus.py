#!/usr/bin/env python3
"""
tunit_plus.py - Mortal Kombat II Plus: the Move List and Secrets window data

Mortal Kombat II Plus (the "Beta 2" hack, MRA with the hide_ext flag) adds
moves, fighters and secrets to MK2. The OSD's Move List and View Secrets
options draw them in the information window (rtl/tunit_window.sv; the pages
are laid out by tools/tunit_window.py from the data here).

The data is the MK2 Plus guide's (MKKomplete, Ver. 2.8.50):
    https://icemantraveler.github.io/mkksg/fan_made/mk2plus/default.htm
read for each fighter, secret character, Kombat Kode and stage fatality. It
was not played back in the core or checked in the hack's code, except that the
ROM in the MRA (HBMAME "mk2", MK2+ VER 1.48, BUILD NAME: BETA 2) holds the
clues, the Kombat Kode messages and the settings the pages name. The guide is
newer than that ROM, so an entry the guide adds may be missing from it. The
guide marks the additions to MK2 with a plus; they are marked the same way
(a "+" before the row), and need the hack's Extra Moves setting.

Commands are written as in the Finishing Moves page (tools/tunit_fmoves.py):
"F F HP" in turn, "LP+BL" together, "(LP) B F" hold LP while entering B F,
"(LK 3 s)" hold LK about 3 seconds, then let go. Distances are the guide's
words: Close, Sweep, Half screen, Full screen, Anywhere.

Usage:
    tunit_plus.py            list the fighters and the secrets pages' data
    tunit_plus.py --docs     the game page's tables (the additions, the Kombat Kodes)

Copyright (C) 2026 Gm0rk - GPL-3.0-or-later
"""

import re
import sys

GUIDE_URL = 'https://icemantraveler.github.io/mkksg/fan_made/mk2plus/default.htm'
GUIDE_VERSION = 'Ver. 2.8.50'
ROM_VERSION = 'MK2+ VER 1.48 (Beta 2)'

CLOSE, SWEEP, HALF, FULL, ANY = 'Close', 'Sweep', 'Half screen', 'Full screen', 'Anywhere'
DISTANCES = (CLOSE, SWEEP, HALF, FULL, ANY)
DEAD_POOL = ('Dead Pool', '(LP+LK) D+HP', CLOSE)


def S(move, cmd, note=None, plus=False):
    """A special move: note after the command (or under it), plus: an addition
    that needs Extra Moves"""
    return (move, cmd, note, plus)


def F(name, cmd, dist, then=None, note=None, plus=False, adds=()):
    """A finishing move: then: [(command, distance)] for a second part, note:
    a line (or a list of lines) under it, adds: [text] additions (each a plus row) under it"""
    return {'name': name, 'cmd': cmd, 'dist': dist, 'then': list(then or []), 'note': note,
            'plus': plus, 'adds': list(adds)}


def stage(cmd):
    return F('Pit / Spikes', cmd, CLOSE)


def friend(cmd):
    return F('Friendship', cmd, ANY)


def baby(cmd):
    return F('Babality', cmd, ANY)


def dead_pool():
    return F(*DEAD_POOL)


# the 12 fighters in the select screen's order (as the OSD's Character option),
# then the secret characters
FIGHTERS = [
    {'name': 'Liu Kang',
     'special': [S('High Fireball', 'F F HP', 'also in air'), S('Low Fireball', 'F F LP'),
                 S('Flying Kick', 'F F HK'), S('Bicycle Kick', '(LK 4 s)')],
     'finish': [F('Butterfly Kick', '(BL) F U B D F', SWEEP, note='Deadly Uppercut; a full stick turn',
                  adds=['hold D+BL for the decapitation', 'hold LP+LK for the stage fatality']),
                F("Dragon's Bite", 'D F B B HK', CLOSE),
                friend('F B B B LK'), baby('D D F B LK'), stage('B F F LK'), dead_pool()]},
    {'name': 'Kung Lao',
     'special': [S('Hat Throw', 'B F LP', 'Up / Down steer the hat'),
                 S('Teleport', 'D U', 'then HP / HK attacks'),
                 S('Diving Kick', 'D+HK in air'),
                 S('Whirlwind Spin', '(BL U U) LK', 'tap LK to keep spinning')],
     'finish': [F('Hat Decap', '(LP) B F', FULL, note='Up / Down aim at the neck'),
                F('Body Slice', 'F F F LK', SWEEP),
                F('Hat Splitter', '(LP) B F', FULL, note='Up / Down aim at the waist', plus=True),
                friend('B B B D HK'), baby('B B F F HK'), stage('F F F HP'), dead_pool()]},
    {'name': 'Johnny Cage',
     'special': [S('High Green Orb', 'F D B HP'), S('Low Green Orb', 'B D F LP'),
                 S('Shadow Kick', 'B F LK'), S('Split Punch', 'LP+BL', 'close'),
                 S('Shadow Uppercut', 'B D B HP')],
     'finish': [F('Decap Uppercut', 'F F D U', CLOSE, adds=['hold D+LP+LK+BL for the Triple Decap']),
                F('Torso Rip', 'D D F F LP', CLOSE),
                friend('D D D D HK'), baby('B B B HK'), stage('D D D HK'), dead_pool()]},
    {'name': 'Reptile',
     'special': [S('Acid Spit', 'F F HP'), S('Forceball', 'B B HP+LP'),
                 S('Fast Forceball', 'F F HP+LP', plus=True),
                 S('Slide', 'B+LP+LK+BL'), S('Invisibility', '(BL U U D) HP')],
     'finish': [F('Yummy!', 'B B D LP', HALF),
                F('Invisible Slice', 'F F D HK', CLOSE, note='while invisible'),
                friend('B B D LK'), baby('D B B LK'), stage('D F F BL'), dead_pool()]},
    {'name': 'Sub-Zero',
     'special': [S('Freeze', 'D F LP'), S('Air Freeze', 'D F LP in air', plus=True),
                 S('Ground Freeze', 'D B LK'), S('Slide', 'B+LP+LK+BL')],
     'finish': [F('Ice Shatter', 'F F D HK', SWEEP, then=[('F D F F HP', CLOSE)],
                  note='Deep Freeze, then Uppercut'),
                F('Ice Grenade', '(LP) B B D F', FULL),
                F('Grenade Shatter', 'F F D HK', SWEEP, then=[('(LP) B B D F', FULL)],
                  note='Deep Freeze, then Ice Grenade'),
                friend('B B D HK'), baby('D B B HK'), stage('D F F BL'), dead_pool()]},
    {'name': 'Shang Tsung',
     'special': [S('Skull', 'B B HP'), S('2 Skulls', 'B B F HP'), S('3 Skulls', 'B B F F HP')],
     'morph': [('Baraka', 'D D LK'), ('Jax', 'D F B HK'), ('Johnny Cage', 'B B D LP'),
               ('Kitana', 'BL BL BL'), ('Kung Lao', 'B D B HK'), ('Liu Kang', 'B F F BL'),
               ('Mileena', '(HP 2 s)'), ('Raiden', 'D B F LK'), ('Reptile', '(BL U D) HP'),
               ('Scorpion', '(BL U U)'), ('Sub-Zero', 'F D F HP'),
               ('Jade', 'F B F LK'), ('Noob Saibot', 'B D B HP'), ('Smoke', 'F F B LP')],
     'morph_note': 'Jade, Noob Saibot and Smoke: once unlocked',
     'finish': [F('Inner-Ear Explosion', '(HK 2 s)', SWEEP),
                F('Soul Steal', 'U D U+LK', CLOSE),
                F('Kintaro Morph', '(LP 30 s)', SWEEP),
                friend('B B D F HK'), baby('B F D HK'), stage('D D U D'), dead_pool()]},
    {'name': 'Kitana',
     'special': [S('Fan Swipe', 'B+HP'), S('Fan Throw', 'F F LP+HP', 'also in air'),
                 S('Fan Lift', 'B B B HP'), S('Square Wave Punch', 'F D B HP')],
     'finish': [F('Kiss of Death', '(LK) F F D F', CLOSE),
                F('Fan Decap', 'BL BL BL HK', CLOSE),
                friend('D D D U+LK'), baby('D D D LK'), stage('F D F HK'), dead_pool()]},
    {'name': 'Jax',
     'special': [S('Energy Wave', 'F D B HK'), S('Gotcha Grab', 'F F LP', 'tap LP for more hits'),
                 S('Multi-Slam', 'tap HP', 'quickly, while throwing'),
                 S('Ground Pound', '(LK 3 s)'),
                 S('Backbreaker', 'BL in air', 'next to an opponent in the air')],
     'finish': [F('Arm Rip', 'BL BL BL BL LP', SWEEP),
                F('Head Smash', '(LP) F F F', CLOSE),
                friend('D D U U LK'), baby('D U D U LK'), stage('U U D LK'), dead_pool()]},
    {'name': 'Mileena',
     'special': [S('Sai Throw', '(HP 2 s)', 'also in air'), S('Teleport Kick', 'F F LK'),
                 S('Ground Roll', 'B B D HK')],
     'finish': [F('Sai Stabs', 'F B F LP', CLOSE),
                F('Man-Eater', '(HK 3 s)', CLOSE),
                friend('D D D U+HK'), baby('D D D HK'), stage('F D F LK'), dead_pool()]},
    {'name': 'Baraka',
     'special': [S('Blade Swipe', 'B+HP'), S('Blade Spark', 'D B HP'), S('Blade Fury', 'B B B LP'),
                 S('Double Kick', 'HK HK', 'close, quickly'),
                 S('Blade Spin', 'F D F BL', 'tap BL for more spins', plus=True)],
     'finish': [F('Blade Decap', 'B B B B HP', CLOSE),
                F('Blade Lift', 'B F D F LP', CLOSE),
                friend('U F F HK'), baby('F F F HK'), stage('F F D HK'), dead_pool()]},
    {'name': 'Scorpion',
     'special': [S('Spear', 'B B LP'), S('Teleport Punch', 'D B HP', 'also in air'),
                 S('Forward Teleport', 'D F HP', 'also in air', plus=True),
                 S('Leg Takedown', 'F D B LK'),
                 S('Air Throw', 'BL in air', 'next to an opponent in the air')],
     'finish': [F('Spear Slice', '(HP) D F F F', CLOSE),
                F('Toasty!', '(BL) U U HP', SWEEP),
                F('Toasty!!', '(BL) D D U U HP', ANY),
                friend('B B D HK'), baby('D B B HK'), stage('D F F BL'), dead_pool()]},
    {'name': 'Raiden',
     'special': [S('Lightning Bolt', 'D F LP'), S('Torpedo', 'B B F', 'also in air'),
                 S('Teleport', 'D U', 'quickly'),
                 S('Electric Grab', '(HP 3 s)', 'close to the opponent')],
     'finish': [F('Electrocution', '(LK 3 s) tap LK+BL', CLOSE),
                F('Explosive Uppercut', '(HP 10 s)', CLOSE,
                  note=['start before FINISH HIM', 'or hold U+HP+HK till heads drop']),
                friend('D B F HK'), baby('D D U+HK'), stage('U U U HP'), dead_pool()]},
    # secret characters (View Secrets pages: how to unlock and select them)
    {'name': 'Jade', 'secret': True,
     'special': [S('Fan Throw', 'F F LP+HP', 'also in air')],
     'finish': [F('Kiss of Death', '(LK) F F D F', CLOSE),
                F('Fan Decap', 'BL BL BL HK', CLOSE),
                friend('D D D U+LK'), baby('D D D LK'), stage('F D F HK'), dead_pool()]},
    {'name': 'Noob Saibot', 'secret': True,
     'special': [S('Spear', 'B B LP'), S('Slide', 'B+LP+LK+BL'), S('Teleport', 'D U'),
                 S('Leg Takedown', 'F D B LK')],
     'finish': [F('Explosive Uppercut', 'F F D D HP', CLOSE, note='then hold U+HP+HK till heads drop'),
                F('Slice', '(HP) D F F F', CLOSE),
                friend('B B D HK'), baby('D B B HK'), stage('D F F BL'), dead_pool()]},
    {'name': 'Smoke', 'secret': True,
     'special': [S('Spear', 'B B LP'), S('Teleport Punch', 'D B HP', 'also in air'),
                 S('Air Throw', 'BL in air', 'next to an opponent in the air'),
                 S('Dash Throw', 'F D B LK')],
     'finish': [F('Smoke Death', 'B D B B HP', ANY),
                F('Telekinetic Decap', 'F B B F HP', ANY),
                friend('B B D HK'), baby('D B B HK'), stage('D F F BL'), dead_pool()]},
    {'name': 'Kintaro', 'secret': True,
     'special': [S('Fireball', 'B D F LP'), S('Teleport Stomp', 'D D U')],
     'finish': [F('Oblivion Stomp', 'D D D D HK', SWEEP),
                F('Torso Punch', 'D D B B HP', CLOSE),
                baby('(BL) U D D LK')]},
    {'name': 'Shao Kahn', 'secret': True,
     'special': [S('Spear Toss', 'B D F LP'), S('Grab & Punch', '(HP 3 s)', 'close to the opponent'),
                 S('Shoulder Charge', 'B F F HP'), S('Upward Shoulder', 'B D B HK')],
     'finish': [F('Matter over Mind', 'D D D F HP', CLOSE),
                baby('D B F HK')]},
]

# Hornbuckle, the opponent in the Smoke fight, has Liu Kang's moves and
# finishing moves; he has no page of his own

# ----------------------------------------------------------------------------
# Secrets pages
# ----------------------------------------------------------------------------

# (character, [(label, text)]) - the text is wrapped under the label
SECRET_CHARACTERS = [
    ('JADE', [
        ('Unlock', 'Difficulty Very Hard and Improved AI Off, then beat the game, Jade '
                   'included, without losing a match (a lost round is fine)'),
        ('Fight', 'Beat the opponent just below the ? on the ladder using Low Kicks (LK) '
                  "only; Jade is in Goro's Lair"),
        ('Select', 'Hold START on the character select screen, then pick Kitana '
                   'with another button'),
        ('Clues', '"A princess is the key", "I am one of four!"'),
    ]),
    ('NOOB SAIBOT', [
        ('Unlock', 'Difficulty Very Hard and Improved AI Off, then beat the game in '
                   'under 12 minutes 50 seconds'),
        ('Fight', "Win 50 matches in a row; Noob Saibot is in Goro's Lair"),
        ('Select', 'Hold START, then pick Sub-Zero with another button'),
        ('Clues', '"Holding START is the key", "Ytfif ot teg", "It\'s cold in the '
                  'shadows", "I am one of four!"'),
    ]),
]
SECRET_NOTE_JN = 'Both can be unlocked in the same game.'

SMOKE = ('SMOKE', [
    ('Unlock', 'Difficulty Very Easy. Win a match with a double Flawless and a Fatality on '
               'The Pit II while the silhouettes cross the moon: you then fight '
               'Hornbuckle, and beating him unlocks Smoke'),
    ('Tip', 'The silhouettes are rare (about 1 in 100): start a 1-player game and lose '
            'until The Pit II; with none, press Player 2 START, let the timer run '
            'out undamaged and start again'),
    ('Fight', 'At the Portal, uppercut the opponent until Dan Forden appears (Toasty!), '
              "then quickly press D+START: Smoke is in Goro's Lair"),
    ('Select', 'Hold START, then pick Reptile with another button'),
    ('Clues', '"He is the original", "I am one of four!"'),
])
HORNBUCKLE = ('HORNBUCKLE', [
    ('Who', "The opponent after the Pit II fatality; he plays like Liu Kang (his page)"),
])

BOSS_UNLOCK = ('UNLOCK (EITHER BOSS)', [
    ('Needs', 'Improved AI On, and Jade, Noob Saibot and Smoke unlocked'),
    ('Earn', 'Score at least 600 points in Survival mode, twice: the first time '
             'unlocks one boss, the second the other'),
    ('Sign', 'The results screen says "You are rewarded with a new fighter"'),
])
BOSS_PLAY = ('PLAY AS', [
    ('Kintaro', 'Hold U+LP+HP+LK+HK before the match starts'),
    ('Shao Kahn', 'Hold D+LP+HP+LK+HK before the match starts'),
    ('Needs', "Versus Cheats On; works in Kahn's Arena"),
])
BOSS_NOTE = "Their moves are on the Move List pages."

# Kombat Kodes: (name, player 1, player 2); hold the buttons on the battle
# screen (before the match starts); they work in Klassic Kombat too
KODES = [
    ('Faster Uppercuts', 'HP', 'HP'),
    ('Super Uppercuts', 'U+HP', 'U+HP'),
    ('Blocking Disabled', 'BL', 'BL'),
    ('Throwing Disabled', 'LP', 'LP'),
    ('Outworld Weather', 'HP+HK', 'HP+HK'),
    ('Going Back in Time (Pong)', 'LP+LK+BL', 'LP+LK+BL'),
    ('La Luna Mode', 'U', 'U'),
    ("Dude Where's My Bar", 'D', 'D'),
    ('Round Timer Disabled', 'D+HK', '-'),
    ('Display Hit Boxes', 'F', 'F'),
    ('Tug of War Kombat', 'B+BL', 'B+BL'),
    ('Randper Kombat', 'F+LK', 'B+LK'),
    ('Explosive Kombat', 'LP+HP', 'LK+HK'),
]
KODE_TAG = ('2 vs 2: Finishing Tags Allowed', 'LP+HP+BL', 'LP+HP+BL')

ENDINGS = [('Dizzy Disco Ball', 'hold D'), ('Babalities', 'hold U')]

SETTINGS = [
    ('Extra Moves', 'the moves marked + on the fighters\' pages'),
    ('Improved AI', 'Off for Jade and Noob Saibot, On for the bosses'),
    ('Versus Cheats', 'needed to play as Kintaro or Shao Kahn'),
    ('Secret Characters', 'lock or unlock each one'),
    ('Cheat Selection', 'forces a Kombat Kode on all the time'),
]


def hold_time(cmd):
    """True when a command has a held-for-seconds part, (X 3 s)"""
    return re.search(r'\(\w+ \d+ s\)', cmd) is not None


def _note(note):
    """A note as a parenthesis after the command"""
    if not note:
        return ''
    return ' (%s)' % (', '.join(note) if isinstance(note, list) else note)


def docs_tables():
    """Markdown tables for the game page (docs/MortalKombatII.md), by name:
    specials, finishing, secrets, kodes. The Dead Pool is left out of the
    finishing moves (every fighter but Kintaro and Shao Kahn has it). A plus
    marks what the guide adds to MK2 (it needs the Extra Moves setting)."""
    t = {}
    out = ['| Fighter | Move | Command |', '|---|---|---|']
    for f in FIGHTERS:
        first = True
        rows = [('%s%s' % ('+ ' if plus else '', m), c + _note(note))
                for m, c, note, plus in f['special']]
        rows += [('Morph into %s' % n, c) for n, c in f.get('morph', [])]
        for m, c in rows:
            out.append('| %s | %s | %s |' % (f['name'] if first else '', m, c))
            first = False
    t['specials'] = out
    out = ['| Fighter | Move | Command | Distance |', '|---|---|---|---|']
    for f in FIGHTERS:
        first = True
        for x in f['finish']:
            if x['name'] == DEAD_POOL[0]:
                continue
            cmd = ', then '.join([x['cmd']] + [c for c, d in x['then']])
            dist = ', then '.join([x['dist']] + [d for c, d in x['then']])
            out.append('| %s | %s%s | %s%s | %s |' % (f['name'] if first else '', '+ ' if x['plus'] else '',
                                                    x['name'], cmd, _note(x['note']), dist))
            first = False
            for a in x['adds']:
                out.append('|  | + %s | %s | |' % (x['name'], a))
    t['finishing'] = out
    out = ['| Secret | Step | What to do |', '|---|---|---|']
    bosses = ('Kintaro and Shao Kahn', BOSS_UNLOCK[1] + [
        ('Play as' if lb != 'Needs' else 'Play needs', tx if lb == 'Needs' else '%s: %s%s' % (lb, tx[0].lower(), tx[1:]))
        for lb, tx in BOSS_PLAY[1]])
    for title, rows in SECRET_CHARACTERS + [SMOKE, HORNBUCKLE, bosses]:
        first = True
        for label, text in rows:
            out.append('| %s | %s | %s |' % (title.title().replace(' And ', ' and ') if first else '', label,
                                            text.replace('he plays like Liu Kang (his page)',
                                                         "he has Liu Kang's moves and finishing moves")))
            first = False
    t['secrets'] = out
    out = ['| Kombat Kode | Player 1 | Player 2 |', '|---|---|---|']
    for n, p1, p2 in KODES + [KODE_TAG]:
        out.append('| %s | %s | %s |' % (n, p1, p2))
    t['kodes'] = out
    return {k: '\n'.join(v) + '\n' for k, v in t.items()}


def docs():
    return '\n'.join(docs_tables()[k] for k in ('specials', 'finishing', 'secrets', 'kodes'))


def main():
    if sys.argv[1:] == ['--docs']:
        print(docs(), end='')
        return
    for f in FIGHTERS:
        print('%-12s %2d specials, %2d finishing moves%s' % (
            f['name'], len(f['special']) + len(f.get('morph', [])), len(f['finish']),
            '  (secret)' if f.get('secret') else ''))
    print('%d Kombat Kodes' % (len(KODES) + 1))


if __name__ == '__main__':
    main()

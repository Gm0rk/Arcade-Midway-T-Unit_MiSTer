#!/usr/bin/env python3
"""
tunit_fmoves.py - finishing moves and move lists for Mortal Kombat and
Mortal Kombat II

    python3 tools/tunit_fmoves.py <game id> <maincpu.bin>   addresses of a set
    python3 tools/tunit_fmoves.py --gen                     write the tables
    python3 tools/tunit_fmoves.py --docs mk|mk2|rev4        a game page's finishing moves
    python3 tools/tunit_fmoves.py --moves mk|mk2            a game page's move list

The OSD's "Auto Finishing Moves" page picks a character and one of its moves;
rtl/tunit_fmoves.sv plays it on the winner's controls at the next FINISH
HIM it fits. The "Move List" option (Off, On) shows the fighters' moves in a
window, Left and Right turn its pages (MK: two lists; MK2: a fighter each).
This script holds the move list and makes from it:

  - rtl/tunit_fmoves_tab.svh: the move records and their programs (the
    controls they press), included by rtl/tunit_fmoves.sv
  - rtl/tunit_fmoves_osd.svh: the Move List option, the Finishing Moves
    page and the core's info messages (CONF_STR lines), included by the top
    level
  - for tools/tunit_window.py, the moves of the Move List window (each
    fighter's special moves, and the finishing moves with their distances)
  - with --docs / --moves, the finishing move and move list tables of
    docs/MortalKombat.md (mk) or docs/MortalKombatII.md (mk2)

and, for mra_gen.py, each set's RAM addresses (ROM index 1, words 0x200 on):
the move player follows the fight by watching the CPU's writes to them, and
the OSD's "Fixed AI Difficulty" returns its level for the CPU's reads of the
AI level word (words 0x22A-0x22B, level_word below), except in the demo fights
between games, which the game sets up with its own store of the level (words
0x22C-0x22D: the CPU's PC just after that store, demo_pc below), and the direct
finishers' sites (words 0x22F-0x251, below).

Where they come from (34010 bit addresses, MK2 L3.1 / MK 5.0):

  round state    3 = FINISH HIM, else the winner (1 / 2); set by the finish
                 routine (FF81EF60 / FFCA0170) after it checks neither
                 fighter is a boss.
  fighters       P1 and P2 character, energy, object and process pointers
                 (the player blocks at 01060220 / 01051230, P2 0xBD0 /
                 0x2E0 on). The object's word 0x90 bits on is its x; the
                 process's 32-bit word 0xE0 on is where it resumes when it
                 next runs, which tells the finisher's stance loop
                 (FF82F270 / FFCE5470) and the loser's dizzy loop
                 (FFA17E10 or FF8C27C0 / FFDF4290) apart from getting up
                 or recovering.
  stage          the background (MK2: 0 Dead Pool, 1 Kombat Tomb, 6 The Pit
                 II; MK: 3 The Pit).
  finish flag    set when a finishing move starts (MK2 01061 9C0, MK
                 01051880); the move player's check that a move was taken.

The moves were found in the games' joystick tables and move handlers and
each one checked in MAME on L3.1 and 5.0 (a FINISH HIM, the move played at
distances 10-300; the windows below are where it was taken, less a margin
for the dizzy loser's sway). Every command is entered as the games read it:
directions with Block held, so the finisher stays put, Block let go, then
the button (or last direction) that triggers the move. A button "held"
(charge moves) is pressed with Block, so it does not attack.

Direct finishers (Mortal Kombat Build 82, Mortal Kombat II Build 85, rev 4.0
and Plus Build 86, Raiden's Electrocution and Shang Tsung's Kintaro Build 87, every
hold-time move Build 93; before,
the OSD's "Direct Finishers" option chose them over the combination): each
move starts in its handler, which finds the combination in the joystick
history with one matcher routine and jumps out when it is not there (a JRNC;
Scorpion's Toasty a JRC). While the move player runs the move, the core's
patch bank (rtl/midway_tunit.sv) flips bit 8 of that jump's opcode word (JRNC
becomes JRC: no jump when the history does not match), the player taps only
the button or direction the handler runs on, and the game does the rest: it
still checks FINISH HIM, the finisher's state and the distance itself, so a
call out of range or at the wrong time is refused as a mistyped combination
is. The MRA gives the set's sites (direct_sites for MK, mk2_direct_sites for
MK2); a move the set has no site for plays its combination (MK2) or is not
taken (MK). Mortal Kombat's The Pit (the uppercut on that stage) is not on the
page; the Move List still names it. The MK2 table (MK2_DIRECT) covers the
stock revisions and the Plus hacks (L3.1's sites, Beta 2 moved the stage
fatality); rev 4.0 has its own (REV4_DIRECT). A second 1 Mbit window (words
82-84) holds the sites outside the main one.

Two MK2 moves have no matcher but a release handler that tests how long the button was held
(frames since the press, against a limit; tools/tunit_mk2sites.py HOLD_REF): Raiden's Electrocution
(Low Kick) and Shang Tsung's Kintaro (Low Punch, 30 s: more than the FINISH HIM window).
The patch flips the JRC after that test to a JRNC, so the program _short (Block, the key
let go after a few frames) goes on into the move. The Electrocution's program starts with
KEEP (DIRECT_KEEP): the game takes it at the release, but it wants Block + Low Kick tapped
about 40 times after that, so the patch goes off at the take and the program goes on.

Move program tokens (also the MAME harness's): "U D F B" tap a direction
(F / B toward / away from the opponent), "HP LP HK LK BL" tap a button,
"[X" press and hold, "]X" let go, "wN" wait N frames, "|" wait until the
loser is dizzy, the finisher stands and the distance fits (moves start
here unless they hold a button first), "<N" walk forward to distance N.
Taps are 3 frames down, 3 up.

Copyright (C) 2026 Gm0rk - GPL-3.0-or-later
"""

import itertools
import os
import struct
from collections import Counter
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tunit_secrets import Prog, X, G_MK, G_MKTURBO, G_MK2, mk_reptile   # noqa: E402
import tunit_mk2sites                                                      # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# --------------------------------------------------------------------------
# Moves
# --------------------------------------------------------------------------

# kinds (rtl/tunit_fmoves.sv): what the stage must be and what "taken" is
K_FATAL, K_FRIEND, K_BABY, K_STAGE, K_PIT2, K_DEAD, K_STAGE4 = 0, 1, 2, 3, 4, 5, 7   # 6 was MK's The Pit (not on the page since Build 82)
FAR = 511                        # no upper distance limit

# Raiden's Electrocution: the game starts it when Low Kick is let go; Block + Low
# Kick tapped after that (as fast as a player can) keep it going until the loser
# explodes. 40 taps are about 3.7 s; the game ignores the ones it does not need.
ELEC_TAPS = ' '.join(['BL+LK'] * 40)

# Rev 4.0's Raiden Lift: HK held about 3 s and let go starts it (the Lift); a second part follows: Up held and HP tapped (3 frames
# down, 3 up) until he explodes, else he is only dropped. MAME (Build 102): 34 taps from the start complete it, any start from 3
# to 47 frames after HK is let go; 44 taps (about 4.4 s) leave room, the game ignores the ones it does not need.
LIFT_TAPS = ' '.join(['HP'] * 44)

# (osd name, kind, OSD command, program, min distance, max distance, note)
# note: a second line under the item
MK2_FIGHTERS = [  # select screen order: (name, character id, moves)
    ("Liu Kang", 1, [
        ("Dragon", K_FATAL, "D F B B HK", "[BL D F B B ]BL HK", 0, 108, None),
        ("Cartwheel", K_FATAL, "D F U B D", "[BL D F U B ]BL D", 0, 196, None),
        ("Friendship", K_FRIEND, "F B B B LK", "[BL F B B B ]BL LK", 0, FAR, None),
        ("Babality", K_BABY, "D D F B LK", "[BL D D F B ]BL LK", 0, FAR, None),
        ("Stage Fatality", K_STAGE, "B F F LK", "[BL B F F ]BL LK", 0, 70, None)]),
    ("Kung Lao", 0, [
        ("Hat Throw", K_FATAL, "(LP) B F", "[BL [LP w50 | B F ]BL ]LP", 260, FAR, None),
        ("Decapitation", K_FATAL, "F F F LK", "[BL F F F ]BL LK", 100, 124, None),
        ("Friendship", K_FRIEND, "B B B D HK", "[BL B B B D ]BL HK", 0, FAR, None),
        ("Babality", K_BABY, "B B F F HK", "[BL B B F F ]BL HK", 0, FAR, None),
        ("Stage Fatality", K_STAGE, "F F F HP", "[BL F F F ]BL HP", 0, 70, None)]),
    ("Johnny Cage", 2, [
        ("Torso Rip", K_FATAL, "D D F F LP", "[BL D D F F ]BL LP", 0, 68, None),
        ("Decapitation", K_FATAL, "F F D U", "[BL F F D ]BL U", 0, 70, None),
        ("Friendship", K_FRIEND, "D D D D HK", "[BL D D D D ]BL HK", 0, FAR, None),
        ("Babality", K_BABY, "B B B HK", "[BL B B B ]BL HK", 0, FAR, None),
        ("Stage Fatality", K_STAGE, "D D D HK", "[BL D D D ]BL HK", 0, 70, None)]),
    ("Reptile", 9, [
        ("Tongue", K_FATAL, "B B D LP", "[BL B B D ]BL LP", 164, 220, None),
        ("Slice", K_FATAL, "U U D HP", "[BL U U D ]BL HP w20 [BL F F D ]BL HK", 0, 68, "then F F D HK"),
        ("Friendship", K_FRIEND, "B B D LK", "[BL B B D ]BL LK", 0, FAR, None),
        ("Babality", K_BABY, "D B B LK", "[BL D B B ]BL LK", 0, FAR, None),
        ("Stage Fatality", K_STAGE, "D F F BL", "[BL D F F ]BL BL", 0, 70, None)]),
    ("Sub-Zero", 8, [
        ("Deep Freeze", K_FATAL, "F F D HK", "[BL F F D ]BL HK w30 <66 [BL F D F F ]BL HP", 116, 188, "then F D F F HP"),
        ("Ice Grenade", K_FATAL, "(LP) B B D F", "[BL [LP w50 | B B D F ]BL ]LP", 260, FAR, None),
        ("Friendship", K_FRIEND, "B B D HK", "[BL B B D ]BL HK", 0, FAR, None),
        ("Babality", K_BABY, "D B B HK", "[BL D B B ]BL HK", 0, FAR, None),
        ("Stage Fatality", K_STAGE, "D F F BL", "[BL D F F ]BL BL", 0, 70, None)]),
    ("Shang Tsung", 6, [
        ("Soul Drain", K_FATAL, "U D U LK", "[BL U D U ]BL LK", 0, 78, None),
        ("Inner-Ear Explosion", K_FATAL, "(HK 1 s)", "[BL [HK w50 | ]BL w6 ]HK", 84, 116, None),
        ("Kintaro", K_FATAL, "(LP 30 s)", "[BL [LP w1950 | ]BL w6 ]LP", 80, 120, None),
        ("Friendship", K_FRIEND, "B B D F HK", "[BL B B D F ]BL HK", 0, FAR, None),
        ("Babality", K_BABY, "B F D HK", "[BL B F D ]BL HK", 0, FAR, None),
        ("Stage Fatality", K_PIT2, "D D U D", "[BL D D U ]BL D", 0, 70, None)]),
    ("Kitana", 4, [
        ("Fan Decap", K_FATAL, "BL BL BL HK", "BL BL BL HK", 0, 70, None),
        ("Kiss of Death", K_FATAL, "(LK) F F D F", "[BL [LK w60 | F F D F ]BL ]LK", 0, 68, None),
        ("Friendship", K_FRIEND, "D D D U LK", "[BL D D D U ]BL LK", 0, FAR, None),
        ("Babality", K_BABY, "D D D LK", "[BL D D D ]BL LK", 0, FAR, None),
        ("Stage Fatality", K_STAGE, "F D F HK", "[BL F D F ]BL HK", 0, 70, None)]),
    ("Jax", 11, [
        ("Arm Rip", K_FATAL, "BL BL BL BL LP", "BL BL BL BL LP", 72, 124, None),
        ("Head Smash", K_FATAL, "(LP) F F F", "[BL [LP w66 | F F F ]BL ]LP", 0, 80, None),
        ("Friendship", K_FRIEND, "D D U U LK", "[BL D D U U ]BL LK", 0, FAR, None),
        ("Babality", K_BABY, "D U D U LK", "[BL D U D U ]BL LK", 0, FAR, None),
        ("Stage Fatality", K_STAGE, "U U D LK", "[BL U U D ]BL LK", 0, 70, None)]),
    ("Mileena", 5, [
        ("Sai Stab", K_FATAL, "F B F LP", "[BL F B F ]BL LP", 0, 74, None),
        ("Inhale", K_FATAL, "(HK 2 s)", "[BL [HK w130 | ]BL w6 ]HK", 0, 68, None),
        ("Friendship", K_FRIEND, "D D D U HK", "[BL D D D U ]BL HK", 0, FAR, None),
        ("Babality", K_BABY, "D D D HK", "[BL D D D ]BL HK", 0, FAR, None),
        ("Stage Fatality", K_STAGE, "F D F LK", "[BL F D F ]BL LK", 0, 70, None)]),
    ("Baraka", 3, [
        ("Decapitation", K_FATAL, "B B B B HP", "[BL B B B B ]BL HP", 0, 96, None),
        ("Impale", K_FATAL, "B F D F LP", "[BL B F D F ]BL LP", 0, 132, None),
        ("Friendship", K_FRIEND, "U F F HK", "[BL U F F ]BL HK", 0, FAR, None),
        ("Babality", K_BABY, "F F F HK", "[BL F F F ]BL HK", 0, FAR, None),
        ("Stage Fatality", K_STAGE, "F F D HK", "[BL F F D ]BL HK", 0, 70, None)]),
    ("Scorpion", 10, [
        ("Toasty", K_FATAL, "D D U U HP", "[BL D D U U ]BL HP", 0, FAR, None),
        ("Torch", K_FATAL, "U U HP", "[BL U U ]BL HP", 148, 172, None),
        ("Slice", K_FATAL, "(HP) D F F F", "[BL [HP w42 | D F F F ]BL ]HP", 0, 68, None),
        ("Friendship", K_FRIEND, "B B D HK", "[BL B B D ]BL HK", 0, FAR, None),
        ("Babality", K_BABY, "D B B HK", "[BL D B B ]BL HK", 0, FAR, None),
        ("Stage Fatality", K_STAGE, "D F F BL", "[BL D F F ]BL BL", 0, 70, None)]),
    ("Raiden", 7, [
        ("Electrocution", K_FATAL, "(LK 2 s)", "[BL [LK w130 | ]BL w6 ]LK " + ELEC_TAPS, 0, 64,
         "then tap BL+LK"),
        ("Super Uppercut", K_FATAL, "(HP 7 s)", "[BL [HP w455 | ]BL w6 ]HP", 0, 82, None),
        ("Friendship", K_FRIEND, "D B F HK", "[BL D B F ]BL HK", 164, FAR, None),
        ("Babality", K_BABY, "D D U HK", "[BL D D U ]BL HK", 0, FAR, None),
        ("Stage Fatality", K_STAGE, "U U HP", "[BL U U ]BL HP", 0, 70, None)]),
]
# The Character option lists the fighters alphabetically (Build 91). The select
# screen order stays where the data is indexed by it: the direct finisher site ids
# (_mk2_site_ids: the MRAs' site words) and the Move List window's pages
# (window_order, tools/tunit_window.py).
MK2_SELECT_ORDER = [n for n, _, _ in MK2_FIGHTERS]
MK2_FIGHTERS.sort(key=lambda f: f[0])
MK2_DEADPOOL = ("Dead Pool", K_DEAD, "D+LP+LK HP", "[BL [D w4 [LP [LK w6 ]BL HP ]D ]LP ]LK", 0, 76, None)

# Mortal Kombat II Plus's extra fighters (HBMAME mk2s03 / mk2s04; the hack's guide, tools/tunit_plus.py): see
# PLUS_HIDDEN below, which follows the stock fighters on the Character option's internal lines (12-16) and
# in the records (the MK2 game number: only Plus can pick them).

# Mortal Kombat II rev 4.0 (the hack, HBMAME mk2s08; tools/tunit_rev4.py has the
# author's move list): the same twelve fighters in the same order, with the
# finishing moves of its guide and no friendships. A move the hack has as
# rev L3.1 does (same command, same distance) is L3.1's tuple, checked in MAME
# there; the new ones are programmed from the guide's commands the same way
# (directions with Block held, then the button) and have not been played
# back: the distance windows are the guide's words (Close: up to 70, Sweep:
# 72-124, anywhere), the holds the guide's seconds in frames (65 a second,
# L3.1's 2 s is 130). Left out: moves that need something the player cannot
# do from a FINISH HIM (Shang Tsung's Kintaro holds LP for 30 s and Raiden's
# Exploding Uppercut HP for 7 s, both from before FINISH HIM; they are direct
# finishers on the page since Builds 87 and 94) and the hidden fighters (Ermac,
# Jade, Rain: their character ids are not known). The stage fatality has no
# stage test (K_STAGE4): the hack has more stages than the ids known.
def _std(fighter, move):
    for name, _, moves in MK2_FIGHTERS:
        if name == fighter:
            for m in moves:
                if m[0] == move:
                    return m
    raise KeyError((fighter, move))


def _same(fighter, move, name=None, cmd=None, note=None, dmax=None):
    n, kind, c, prog, dmin, dmax0, nt = _std(fighter, move)
    return (name or n, kind, cmd or c, prog, dmin, dmax if dmax is not None else dmax0, note if note else nt)


def _stage4(fighter):
    n, kind, c, prog, dmin, dmax, nt = _std(fighter, 'Stage Fatality')
    return ("Stage Fatality", K_STAGE4, c, prog, dmin, dmax, None)


def _new(name, cmd, prog, dmin, dmax, kind=K_FATAL, note=None):
    return (name, kind, cmd, prog, dmin, dmax, note)


def _rev4_fighters():
    out = []
    for name, cid, _ in MK2_FIGHTERS:
        s = lambda mv, **kw: _same(name, mv, **kw)       # noqa: E731
        bab = s('Babality')
        stg = _stage4(name)
        if name == 'Liu Kang':
            m = [s('Dragon'), s('Cartwheel', cmd='(BL) D F U B D', dmax=80),       # (rev 4.0 takes it up to 80, MAME Build 87; L3.1 up to 200)
                 # Red Dragon Flame (Build 102): a Block press of its own, in the Start+LP (red) costume only (the handler
                 # tests the costume, then the distance, up to 200: MAME, red costume 200 taken and 201 not, any other costume
                 # never). There is no combination for the game to match, so no site: the move is the tap.
                 _new('Red Dragon Flame', 'BL', 'BL', 0, 200, note='red costume only')]
        elif name == 'Kung Lao':
            m = [s('Decapitation', name='Hat Slice'), s('Hat Throw', name='Hat Decap')]
        elif name == 'Johnny Cage':
            m = [s('Torso Rip'), s('Decapitation', name='Triple Head Pop'),
                 _new('Brain Punch', 'F B B HP', '[BL F B B ]BL HP', 0, 70)]
        elif name == 'Reptile':
            m = [s('Tongue'), s('Slice', name='Invisible Slice')]
        elif name == 'Sub-Zero':
            m = [s('Deep Freeze'), s('Ice Grenade', name='Ice Bomb'),
                 _new('Head Rip', 'F D F LP', '[BL F D F ]BL LP', 0, 70)]
        elif name == 'Shang Tsung':
            m = [s('Soul Drain', name='Soul Steal', cmd='U D U+LK'), s('Kintaro'),
                 _new('Backflip Decap', 'F D F LK', '[BL F D F ]BL LK', 0, 78),
                 _new('Blade Decap', 'B B F U LP', '[BL B B F U ]BL LP', 72, 124),
                 _new('Body Explosion', '(HK 3 s)', '[BL [HK w200 | ]BL w6 ]HK', 80, FAR)]
        elif name == 'Kitana':
            m = [s('Fan Decap'), s('Kiss of Death')]
        elif name == 'Jax':
            m = [s('Head Smash', name='Head Clap'), s('Arm Rip')]
        elif name == 'Mileena':
            m = [s('Sai Stab'), s('Inhale', name='Body Suck')]
        elif name == 'Baraka':
            m = [s('Decapitation'), s('Impale')]
        elif name == 'Scorpion':
            m = [s('Toasty'), s('Torch', name='MK1 Burn'), s('Slice', name='Spear Slice')]
        else:           # Raiden
            m = [s('Electrocution'), _new('Lift', '(HK 3 s)', '[BL [HK w200 | ]BL w6 ]HK w12 [U %s ]U' % LIFT_TAPS, 0, 70,
                                          note='then hold U, tap HP'),
                 s('Super Uppercut')]       # (the hack's guide: Exploding Uppercut; the page's line is shared with L3.1's)
        out.append((name, cid, m + [bab, stg, MK2_DEADPOOL]))
    return out


# The hidden fighters of rev 4.0 (Build 99; the guide's moves, tools/tunit_rev4.py): Ermac (character
# 17), Jade (16) and Rain (19), taken at a FINISH HIM won with them in MAME (state made by picking a
# fighter at the select screen and writing the character number, so the fight plays as theirs) as
# combinations; the distance windows are the measured ones (the guide says Mid and Far for Ermac and
# Rain). The names of the page are short ("Tele Slam": the guide's Telekinetic Slam) so that a name and
# its distance fit the page's line. The core has no direct finisher site for them, so each plays as the
# combination.
REV4_HIDDEN = [
    ("Ermac", 17, [
        ("Tele Slam", K_FATAL, "D U D D D BL", "[BL D U D D D ]BL BL", 97, 192, None),
        ("Tele Head Rip", K_FATAL, "F B F F LK", "[BL F B F F ]BL LK", 216, FAR, None),
        ("Babality", K_BABY, "D B B LK", "[BL D B B ]BL LK", 0, FAR, None),
        ("Stage Fatality", K_STAGE4, "D F F BL", "[BL D F F ]BL BL", 0, 70, None)]),
    ("Jade", 16, [
        ("Staff Impale", K_FATAL, "BL BL BL F BL", "BL BL BL F BL", 0, 80, None),
        ("Babality", K_BABY, "D D D LK", "[BL D D D ]BL LK", 0, FAR, None),
        ("Stage Fatality", K_STAGE4, "F D F HK", "[BL F D F ]BL HK", 0, 70, None)]),
    ("Rain", 19, [
        ("Lightning", K_FATAL, "D D B F HK", "[BL D D B F ]BL HK", 0, 192, None),
        ("Babality", K_BABY, "D B B HK", "[BL D B B ]BL HK", 0, FAR, None),
        ("Stage Fatality", K_STAGE4, "D F F BL", "[BL D F F ]BL BL", 0, 70, None)]),
]
REV4_FIGHTERS = _rev4_fighters()      # (name, id, moves in the page's order, Dead Pool last)
REV4_FIGHTERS += [(n, c, m + [MK2_DEADPOOL]) for n, c, m in REV4_HIDDEN]     # (the lines 12-14: after the twelve)

# Mortal Kombat II Plus's extra fighters (Build 99; their moves are the hack's guide's, tools/tunit_plus.py): Jade,
# Kintaro, Noob Saibot, Shao Kahn and Smoke, the characters 16, 12, 15, 13 and 14 (the game's own
# numbers; Smoke, Noob Saibot and Jade were taken at a FINISH HIM in MAME as the fighter, Kintaro and Shao Kahn
# need a Versus Cheat to be played). (name, character id, moves, has the Dead Pool: the guide gives Kintaro and
# Shao Kahn two moves and a Babality only.) Combinations like rev 4.0's hidden fighters: Plus's sites in
# the MRAs are the stock fighters'. Their lines follow the twelve (12-16); the Character option lists all 17
# alphabetically (option_order()).
PLUS_HIDDEN = [
    ("Jade", 16, [
        ("Fan Decap", K_FATAL, "BL BL BL HK", "BL BL BL HK", 0, 70, None),
        ("Kiss of Death", K_FATAL, "(LK) F F D F", "[BL [LK w60 | F F D F ]BL ]LK", 0, 68, None),
        ("Friendship", K_FRIEND, "D D D U LK", "[BL D D D U ]BL LK", 0, FAR, None),
        ("Babality", K_BABY, "D D D LK", "[BL D D D ]BL LK", 0, FAR, None),
        ("Stage Fatality", K_STAGE, "F D F HK", "[BL F D F ]BL HK", 0, 70, None)], True),
    ("Kintaro", 12, [
        ("Oblivion Stomp", K_FATAL, "D D D D HK", "[BL D D D D ]BL HK", 80, 124, None),
        ("Torso Punch", K_FATAL, "D D B B HP", "[BL D D B B ]BL HP", 0, 70, None),
        ("Babality", K_BABY, "(BL) U D D LK", "[BL U D D ]BL LK", 0, FAR, None)], False),
    ("Noob Saibot", 15, [
        ("Explosive Uppercut", K_FATAL, "F F D D HP", "[BL F F D D ]BL HP [U [HP [HK w240 ]HK ]HP ]U", 0, 68, "then hold U+HP+HK"),
        ("Slice", K_FATAL, "(HP) D F F F", "[BL [HP w42 | D F F F ]BL ]HP", 0, 68, None),
        ("Friendship", K_FRIEND, "B B D HK", "[BL B B D ]BL HK", 0, FAR, None),
        ("Babality", K_BABY, "D B B HK", "[BL D B B ]BL HK", 0, FAR, None),
        ("Stage Fatality", K_STAGE, "D F F BL", "[BL D F F ]BL BL", 0, 70, None)], True),
    ("Shao Kahn", 13, [
        ("Matter over Mind", K_FATAL, "D D D F HP", "[BL D D D F ]BL HP", 0, 70, None),
        ("Babality", K_BABY, "D B F HK", "[BL D B F ]BL HK", 0, FAR, None)], False),
    ("Smoke", 14, [
        ("Smoke Death", K_FATAL, "B D B B HP", "[BL B D B B ]BL HP", 0, FAR, None),
        ("Telekinetic Decap", K_FATAL, "F B B F HP", "[BL F B B F ]BL HP", 0, FAR, None),
        ("Friendship", K_FRIEND, "B B D HK", "[BL B B D ]BL HK", 0, FAR, None),
        ("Babality", K_BABY, "D B B HK", "[BL D B B ]BL HK", 0, FAR, None),
        ("Stage Fatality", K_STAGE, "D F F BL", "[BL D F F ]BL BL", 0, 70, None)], True),
]


# Mortal Kombat 1's fatalities: (move, kind, the command as a player enters it
# (the Move List and the docs show it), no program (the move player taps the
# fighter's one trigger, MK_DIRECT below), min distance, max distance, note).
MK_FIGHTERS = [  # select screen order (sorted by name below)
    ("Johnny Cage", 0, [("Decapitation", K_FATAL, "F F F HP", None, 0, 60, None)]),
    ("Kano", 1, [("Heart Rip", K_FATAL, "B D F LP", None, 0, 84, None)]),
    ("Sub-Zero", 5, [("Spine Rip", K_FATAL, "F D F HP", None, 0, 84, None)]),
    ("Sonya", 6, [("Kiss of Death", K_FATAL, "F F B B BL", None, 0, FAR, None)]),
    ("Raiden", 2, [("Electrocution", K_FATAL, "F B B B HP", None, 80, 124, None)]),
    ("Liu Kang", 3, [("Cartwheel", K_FATAL, "D B U F D", None, 0, FAR, None)]),
    ("Scorpion", 4, [("Fire Breath", K_FATAL, "(BL) U U", None, 120, 144, None)]),
]
MK_SELECT_ORDER = [n for n, _, _ in MK_FIGHTERS]
MK_FIGHTERS.sort(key=lambda f: f[0])

# Direct finishers: per character id, what the move player enters in place of
# the combination: (key held through the tries or None, key tapped). The tapped
# key is the one the fighter's handler runs on (MK 5.0 dispatch tables
# FFD99750-FFD99D90: the last button or direction of the combination);
# Scorpion's Up is tapped with Block held, as the combination holds it, so he
# does not jump. Checked in MAME with the patch: one tap at a FINISH HIM, in
# range, takes the move for each of the seven fighters; out of range, outside
# FINISH HIM and as the loser it is refused. Checked on the MiSTer (Build 81).
MK_DIRECT = {0: (None, 'HP'), 1: (None, 'LP'), 2: (None, 'HP'), 3: (None, 'D'),
             4: ('BL', 'U'), 5: (None, 'HP'), 6: (None, 'BL')}
# Mortal Kombat Plus (the hack, HBMAME mk07; its Move List is tools/tunit_mkplus.py):
# the page of its own, the fighters in alphabetical order with the hidden
# Reptile, each with his fatality (the hack's names: the guide's) and the Babality
# the hack adds. The handlers of the fatalities are rev 5.0's (MK_DIRECT); Reptile
# has Sub-Zero's Spine Rip and Scorpion's Toasty! (the guide's), so the sites of
# those two; a Babality is a handler of the hack that matches three directions
# (the command's first three, in the fighter's table) and the last button (the
# jump after its matcher call, then a test of the buttons used in the rounds): two
# routines, one for a Babality that ends with Low Kick and one for High Kick,
# shared by the fighters (sites 7 and 8 of the MRA's table, babality_sites()).
# Played back in MAME as a direct finisher (the jump flipped, the last button
# tapped once) at a FINISH HIM won without Low Punch, High Punch or Block, from
# any distance: all seven fighters, and Reptile (Build 93: his character number is
# 9, found by forcing the number in the fight; the first builds had 7, which no
# fighter in the hack has, so the core never armed his moves). The distances the
# game measures for Reptile differ from the others': it reads the screen distance
# of the two sprites, and his are some 25-40 further apart for the same position.
# Reptile's own windows (REPTILE_DIST), as taken in MAME with the loser swaying:
# Spine Rip anything up to 128 (the Sub-Zero window, 0-84, is inside it),
# Toasty! from 144 to 166.
BAB_HK, BAB_LK = 7, 8
REPTILE_ID = 9
REPTILE_DIST = {'Toasty!': (146, 164)}
MKP_NAMES = {'Johnny Cage': 'Decap Uppercut', 'Kano': 'Heart Rip', 'Liu Kang': 'Butterfly Kick',
             'Raiden': 'Electro-Decap', 'Scorpion': 'Toasty!', 'Sonya': 'Flame Kiss', 'Sub-Zero': 'Spine Rip'}
MKP_CMDS = {'Johnny Cage': 'F F F HP', 'Kano': 'B D F LP', 'Liu Kang': '(BL) F D B U F',
            'Raiden': 'F B B B HP', 'Scorpion': '(BL) U U', 'Sonya': 'F F B B BL', 'Sub-Zero': 'F D F HP'}
MKP_BABALITY = {'Johnny Cage': 'D D D HK', 'Kano': 'F D B LK', 'Liu Kang': 'B F F LK', 'Raiden': 'B D B HK',
                'Scorpion': 'D B B HK', 'Sonya': 'F B F HK', 'Sub-Zero': 'D B B HK', 'Reptile': 'D B B HK'}


def _mkp_fighters():
    """(name, character id, moves) in alphabetical order; a move's direct finisher is
    in MKP_DIRECT: (fighter, move) -> (site, key held, key tapped)."""
    out, direct = [], {}
    def baby(name):
        cmd = MKP_BABALITY[name]
        key = cmd.split()[-1]
        site = BAB_HK if key == 'HK' else BAB_LK
        direct[(name, 'Babality')] = (site, None, key)
        return ('Babality', K_BABY, cmd, cmd, 0, FAR, None)
    for name, cid, moves in MK_FIGHTERS:
        mname, kind, cmd, prog, dmin, dmax, note = moves[0]
        direct[(name, MKP_NAMES[name])] = (cid, ) + MK_DIRECT[cid]
        out.append((name, cid, [(MKP_NAMES[name], kind, MKP_CMDS[name], prog, dmin, dmax, note), baby(name)]))
    sz, sc = [m for n, c, m in MK_FIGHTERS if n == 'Sub-Zero'][0][0], [m for n, c, m in MK_FIGHTERS if n == 'Scorpion'][0][0]
    direct[('Reptile', 'Spine Rip')] = (5, ) + MK_DIRECT[5]
    direct[('Reptile', 'Toasty!')] = (4, ) + MK_DIRECT[4]
    out.append(('Reptile', REPTILE_ID, [
        ('Spine Rip', sz[1], 'F D F HP', None, sz[4], sz[5], None),
        ('Toasty!', sc[1], '(BL) U U', None) + REPTILE_DIST['Toasty!'] + (None, ), baby('Reptile')]))
    out.sort(key=lambda f: f[0])
    return out, direct


MKP_FIGHTERS, MKP_DIRECT = _mkp_fighters()

DIRECT_TRIES = 5                 # taps, one at a time until the game takes the move
DIRECT_GAP = 6                   # frames between them (the game takes a move within 2 frames)
DIRECT_END = 12                  # frames the last one is given

# Mortal Kombat II's direct finishers (Build 85; the stock revisions L2.0 and
# later, Plus from Build 86; rev 4.0 has REV4_DIRECT below): fighter -> move ->
# (the sites, the program).
# A site is the jump after a matcher call in rev L3.1, by bit address
# (tools/tunit_mk2sites.py finds it in the other revisions); a two-stage move
# has two, one per stage. The program is what the move player enters after the
# ready point, with the patch on the stage's site (token S2: on the next site):
#   tap K      the button or direction the handler runs on, DIRECT_TRIES times
#              (the game takes it within 2 frames; it checks FINISH HIM, the
#              distance and the loser's state itself)
#   hold K, n  Block + K pressed, n frames, Block and K let go: a handler that
#              runs when K is released (Block so the press is not an attack);
#              n is what the handler wants (the release handlers test how long
#              the button was held: 50 frames for Kung Lao's Hat Throw and
#              Sub-Zero's Ice Grenade, 60 Kitana's Kiss of Death, 66 Jax's
#              Head Smash, 40 Scorpion's Slice), plus 4 (Build 85 to 92; since
#              Build 93 the hold-time moves are patched at the hold's own
#              check, see _quick and the sites of HOLD_REF, and need no hold)
# Friendship, Babality and the stage fatality have one site for every fighter;
# the fighter's table gives the handler its pattern. (The game's flag: 5 is a
# Babality, 6 a stage fatality, 7 a Friendship.) Checked in MAME on L3.1: each
# move's site and keys on a FINISH HIM, the move taken (hold times and the
# two-stage timing measured the same way); a move out of range and a stage
# fatality on another stage refused (a spot check).
# Left to the combinations: the Dead Pool (its routine reads the input port itself
# for the three held buttons, not the joystick history).
# Raiden's Electrocution and Shang Tsung's Kintaro (Build 87) are direct through
# their release handlers' hold-time checks (tools/tunit_mk2sites.py HOLD_REF); from
# Build 93 so are all the others that hold a button (Inner-Ear Explosion, Inhale,
# Hat Throw, Ice Grenade, Kiss of Death, Head Smash, Scorpion's Slice and rev 4.0's
# Body Explosion, Body Suck, Lift, ...): the patch flips the hold-time check's jump
# (JRC after CMPI limit), so a fresh short hold counts as the long one, and the
# directions are typed for real for the game's matcher.
S_BAB, S_FRI, S_STG = 0xFF87E300, 0xFF880950, 0xFF876E70


def _tap(key):
    return ' '.join([key, 'w%d' % DIRECT_GAP] * DIRECT_TRIES + ['w%d' % DIRECT_END])


def _hold(key, n):
    return '[BL [%s w%d ]BL ]%s w%d' % (key, n + 4, key, DIRECT_END)


def _short(key):
    """Block + key let go after a few frames: a hold-time handler (Raiden's Electrocution, Shang Tsung's
    Kintaro) whose limit is a minimum: its jump is flipped, so a hold under the limit goes on into the move."""
    return '[BL [%s w6 ]BL ]%s w%d' % (key, key, DIRECT_END)


def _quick(key, dirs):
    """A move the game runs when a button is let go after a long hold, with directions typed meanwhile
    ((LP) B F; Kung Lao's Hat Throw and four more): the hold-time handler's jump is flipped (as for _short),
    the key is held with Block only a moment and the directions are typed for real, so the game's own
    matcher finds them in the joystick history."""
    return '[BL [%s %s ]BL ]%s w%d' % (key, dirs, key, DIRECT_END)


def _inhale():
    """Mileena's Inhale: the game takes it at the release of High Kick with Block let go first, if Low Kick was
    not pressed in the last 80h frames (the test is the stamp of Low Kick, not of High Kick, in every revision
    that has it): the jump is flipped, so a Low Kick pressed a moment ago (with Block, so it does not hit) passes."""
    return '[BL [LK w3 ]LK [HK w5 ]BL ]HK w%d' % DIRECT_END


def _two(key1, wait, walk, key2, tries=6):
    return ' '.join([key1, 'w%d' % wait] + (['<%d' % walk] if walk else []) + ['S2']
                    + [key2, 'w%d' % DIRECT_GAP] * tries + ['w%d' % DIRECT_END])


def _globals(bab, fri, stg):
    return {'Babality': ([S_BAB], _tap(bab)), 'Friendship': ([S_FRI], _tap(fri)),
            'Stage Fatality': ([S_STG], _tap(stg))}


MK2_DIRECT = {
    'Liu Kang': dict(_globals('LK', 'LK', 'LK'),
                     **{'Dragon': ([0xFF86B1A0], _tap('HK')), 'Cartwheel': ([0xFF864B90], _tap('D'))}),
    'Kung Lao': dict(_globals('HK', 'HK', 'HP'),
                     **{'Hat Throw': ([0xFF86B320], _quick('LP', 'B F')), 'Decapitation': ([0xFF86B890], _tap('LK'))}),
    'Johnny Cage': dict(_globals('HK', 'HK', 'HK'),
                        **{'Torso Rip': ([0xFF869BB0], _tap('LP')), 'Decapitation': ([0xFF868270], _tap('U'))}),
    'Reptile': dict(_globals('LK', 'LK', 'BL'),
                    **{'Tongue': ([0xFF866E60], _tap('LP')),
                       'Slice': ([0xFF86A120, 0xFF86A380], _two('HP', 40, 0, 'HK'))}),
    'Sub-Zero': dict(_globals('HK', 'HK', 'BL'),
                     **{'Deep Freeze': ([0xFF865B90, 0xFF865E00], _two('HK', 60, 66, 'HP')),
                        'Ice Grenade': ([0xFF866890], _quick('LP', 'B B D F'))}),
    'Shang Tsung': dict(_globals('HK', 'HK', 'D'),
                        **{'Soul Drain': ([0xFF86A8A0], _tap('LK')), 'Kintaro': ([0xFF863D20], _short('LP')),
                           'Inner-Ear Explosion': ([0xFF863B50], _short('HK'))}),
    'Kitana': dict(_globals('LK', 'LK', 'HK'),
                   **{'Fan Decap': ([0xFF8651A0], _tap('HK')), 'Kiss of Death': ([0xFF8654B0], _quick('LK', 'F F D F'))}),
    'Jax': dict(_globals('LK', 'LK', 'LK'),
                **{'Arm Rip': ([0xFF869870], _tap('LP')), 'Head Smash': ([0xFF864760], _quick('LP', 'F F F'))}),
    'Mileena': dict(_globals('HK', 'HK', 'LK'),
                    **{'Sai Stab': ([0xFF865A70], _tap('LP')), 'Inhale': ([0xFF864090], _inhale())}),
    'Baraka': dict(_globals('HK', 'HK', 'HK'),
                   **{'Decapitation': ([0xFF8680E0], _tap('HP')), 'Impale': ([0xFF867E60], _tap('LP'))}),
    'Scorpion': dict(_globals('HK', 'HK', 'BL'),
                     **{'Toasty': ([0xFF868CC0], _tap('HP')), 'Torch': ([0xFF868D60], _tap('HP')),
                        'Slice': ([0xFF8687F0], _quick('HP', 'D F F F'))}),
    'Raiden': dict(_globals('HK', 'HK', 'HP'),
                   **{'Electrocution': ([0xFF8636C0], 'KEEP ' + _short('LK') + ' ' + ELEC_TAPS),
                      'Super Uppercut': ([0xFF863830], _short('HP'))}),
}
# Plus (HBMAME mk2s03 = Beta 1, mk2s04 = Beta 2) is L3.1 with extra code: the same sites, the same
# programs (Build 86). Beta 2 handles the stage fatality in code of its own (FFCF9920, another 1 Mbit window).
MK2_DIRECT_SETS = ('mk2', 'mk2r20', 'mk2r21', 'mk2r30', 'mk2r31e', 'mk2r32e', 'mk2r42', 'mk2r91', 'mk2chal',
                   'mk2s03', 'mk2s04')
PLUS_SITES = {'mk2s04': {S_STG: 0xFFCF9920}}

# Rev 4.0 (HBMAME mk2s08, Build 86): the same programs on its own sites (tools/tunit_mk2sites.py REV4_REF).
# Checked in MAME at a FINISH HIM with each of the twelve fighters: every site and trigger below, the
# holds (it takes a shorter hold than L3.1 for most, so L3.1's times are enough), Deep Freeze's two
# stages, Babality and the stage fatality; a move with no entry keeps its combination. Its Babality
# is in FFB0F940, outside the 1 Mbit window of the rest (the alternate window words 82-84).
R4_BAB, R4_STG = 0xFFB0F940, 0xFF8DA120
REV4_DIRECT_SETS = ('mk2s08',)


def _globals4(bab, stg):
    return {'Babality': ([R4_BAB], _tap(bab)), 'Stage Fatality': ([R4_STG], _tap(stg))}


REV4_DIRECT = {
    'Liu Kang': dict(_globals4('LK', 'LK'),
                     **{'Dragon': ([0xFF8C3DB0], _tap('HK')), 'Cartwheel': ([0xFF8B8430], _tap('D'))}),
    'Kung Lao': dict(_globals4('HK', 'HP'),
                     **{'Hat Decap': ([0xFF8C3F30], _quick('LP', 'B F')), 'Hat Slice': ([0xFF8C44A0], _tap('LK'))}),
    'Johnny Cage': dict(_globals4('HK', 'HK'),
                        **{'Torso Rip': ([0xFF8C1A60], _tap('LP')), 'Triple Head Pop': ([0xFF8BF970], _tap('U')),
                           'Brain Punch': ([0xFF8BFBB0], _tap('HP'))}),
    'Reptile': dict(_globals4('LK', 'BL'),
                    **{'Tongue': ([0xFF8BDFB0], _tap('LP')),
                       'Invisible Slice': ([0xFF8C23A0, 0xFF8C28F0], _two('HP', 40, 0, 'HK'))}),
    'Sub-Zero': dict(_globals4('HK', 'BL'),
                     **{'Deep Freeze': ([0xFF8BBA50, 0xFF8BBCF0], _two('HK', 60, 66, 'HP')),
                        'Ice Bomb': ([0xFF8BD0D0], _quick('LP', 'B B D F')), 'Head Rip': ([0xFF8BC640], _tap('LP'))}),
    'Shang Tsung': dict(_globals4('HK', 'D'),
                        **{'Soul Steal': ([0xFF8C3180], _tap('LK')), 'Backflip Decap': ([0xFF8C3030], _tap('LK')),
                           'Blade Decap': ([0xFF8C1DE0], _tap('LP')), 'Kintaro': ([0xFF8B7280], _short('LP')),
                           'Body Explosion': ([0xFF8B7070], _short('HK'))}),
    'Kitana': dict(_globals4('LK', 'HK'),
                   **{'Fan Decap': ([0xFF8B8B80], _tap('HK')), 'Kiss of Death': ([0xFF8B8E60], _quick('LK', 'F F D F'))}),
    'Jax': dict(_globals4('LK', 'LK'),
                **{'Arm Rip': ([0xFF8C16F0], _tap('LP')), 'Head Clap': ([0xFF8B7F00], _quick('LP', 'F F F'))}),
    'Mileena': dict(_globals4('HK', 'LK'),
                    **{'Sai Stab': ([0xFF8BB930], _tap('LP')), 'Body Suck': ([0xFF8B7630], _inhale())}),
    'Baraka': dict(_globals4('HK', 'HK'),
                   **{'Decapitation': ([0xFF8BF7E0], _tap('HP')), 'Impale': ([0xFF8BF470], _tap('LP'))}),
    'Scorpion': dict(_globals4('HK', 'BL'),
                     **{'Toasty': ([0xFF8C05B0], _tap('HP')), 'MK1 Burn': ([0xFF8C06F0], _tap('HP')),
                        'Spear Slice': ([0xFF8C00D0], _quick('HP', 'D F F F'))}),
    'Raiden': dict(_globals4('HK', 'HP'),
                   **{'Electrocution': ([0xFF8B6A70], 'KEEP ' + _short('LK') + ' ' + ELEC_TAPS),
                      'Lift': ([0xFF8B6BF0], 'KEEP ' + _short('HK') + ' [U ' + LIFT_TAPS + ' ]U'),
                      'Super Uppercut': ([0xFF8B6D60], _short('HP'))}),
}


def _direct(game):
    return REV4_DIRECT if game == 'rev4' else MK2_DIRECT


def _mk2_site_ids(game='mk2'):
    """The sites in the order of the move table: [bit address, ...]; a move's
    sites are consecutive ids. game: 'mk2' (the stock revisions and Plus) or
    'rev4' (its own sites; at most MAX_SITES)."""
    ids = []
    for fname, cid, moves in window_order('mk2', REV4_FIGHTERS if game == 'rev4' else MK2_FIGHTERS):   # (the MRAs' site ids)
        for mv in moves:
            d = _direct(game).get(fname, {}).get(mv[0])
            if d:
                for a in d[0]:
                    if a not in ids:
                        ids.append(a)
    assert len(ids) <= MAX_SITES, 'more than %d direct finisher sites' % MAX_SITES
    return ids

# Fatalities the move player leaves out (the button must be held from before
# FINISH HIM), for the Move List window: (fighter, after this move, (name,
# command, note, min distance, max distance)). From the release handlers
# (MK2 L3.1, table FF863020): Raiden's HP release
# FF863750 (HP held at least 180h frames, state 3, start with A1 = 52h).
# (Shang Tsung's LP release, the Kintaro, is a move of the page since Build 87,
# Raiden's, the Super Uppercut, since Build 94: nothing is left out now.)
WINDOW_EXTRA = {}

# Move List window (tools/tunit_window.py): each fighter's special moves,
# shown only (the core does not enter them). Same order as the fighters above; (name, command),
# a None command is a heading. Found in the move handlers (MK2 L3.1 per
# button and direction at FF8628A0 on, matcher FF8775D0, button pairs
# FF86A460, slide FF866630; MK 5.0 per event at FFD993A0, matcher
# FFD9CFB0, button buffer FFD9E3C0, held combinations FFD9CE60) and each
# one played in MAME 0.289 at a FINISH HIM, the move's process start seen
# (MK2 FF877370 A7, MK FFD9C9C0 A7); the air grabs and Raiden's grab need
# an opponent not dizzy and come from the handlers only. Charge times are
# the handlers' minimum (frames since the press: Liu Kang 80h, Jax 60h,
# Raiden 50h, Mileena 22h, Shang Tsung's Mileena 30h) rounded up.
# "(BL U U) LK": Block held over the directions (so U does not jump), let
# go before the button; "(HP 1 s)": HP held about a second, then let go.
MK2_SPECIALS = [
    [("High Fireball", "F F HP"), ("Low Fireball", "F F LP"), ("Flying Kick", "F F HK"),
     ("Bicycle Kick", "(LK 3 s)")],
    [("Hat Throw", "B F LP"), ("Teleport", "D U"), ("Spin", "(BL U U) LK"),
     ("Dive Kick", "D HK in air")],
    [("High Bolt", "F D B HP"), ("Low Bolt", "B D F LP"), ("Shadow Kick", "B F LK"),
     ("Uppercut", "B D B HP"), ("Ball Breaker", "LP+BL")],
    [("Acid Spit", "F F HP"), ("Force Ball", "B B HP+LP"), ("Invisibility", "(BL U U D) HP"),
     ("Slide", "B+LP+LK+BL")],
    [("Freeze", "D F LP"), ("Ground Freeze", "D B LK"), ("Slide", "B+LP+LK+BL")],
    [("Skull", "B B HP"), ("2 Skulls", "B B F HP"), ("3 Skulls", "B B F F HP"),
     ("Morph into:", None),
     ("Liu Kang", "B F F BL"), ("Kung Lao", "B D B HK"), ("Johnny Cage", "B B D LP"),
     ("Reptile", "(BL U D) HP"), ("Sub-Zero", "F D F HP"), ("Kitana", "BL BL BL"),
     ("Jax", "D F B HK"), ("Mileena", "(HP 1 s)"), ("Baraka", "D D LK"),
     ("Scorpion", "(BL U U)"), ("Raiden", "D B F LK")],
    [("Fan Throw", "F F HP+LP"), ("Fan Lift", "B B B HP"), ("Flying Punch", "F D B HP")],
    [("Energy Wave", "F D B HK"), ("Gotcha Grab", "F F LP"), ("Ground Smash", "(LK 2 s)"),
     ("Back Breaker", "BL in air")],
    [("Sai Throw", "(HP 1 s)"), ("Teleport Kick", "F F LK"), ("Roll", "B B D HK")],
    [("Blade Spark", "D B HP"), ("Blade Fury", "B B B LP")],
    [("Spear", "B B LP"), ("Teleport", "D B HP"), ("Scissors", "F D B LK"),
     ("Air Throw", "BL in air")],
    [("Lightning", "D F LP"), ("Teleport", "D U"), ("Torpedo", "B B F"),
     ("Electric Grab", "(HP 2 s)")],
]
MK_SPECIALS = [
    [("Green Bolt", "B F LP"), ("Shadow Kick", "B F LK"), ("Split Punch", "LP+BL")],
    [("Knife Throw", "(BL B F)"), ("Cannonball", "F D B U")],
    [("Freeze", "D F LP"), ("Slide", "B+LP+LK+BL")],
    [("Ring Toss", "LP B LP"), ("Leg Grab", "D+LP+LK+BL"), ("Square Wave", "F B HP")],
    [("Lightning", "D F LP"), ("Teleport", "D U"), ("Torpedo", "B B F")],
    [("Fireball", "F F HP"), ("Flying Kick", "F F HK")],
    [("Spear", "B B LP"), ("Teleport", "D B HP")],
]
# the special moves follow the fighters' select screen order: sorted like them
MK_SPECIALS = [MK_SPECIALS[MK_SELECT_ORDER.index(n)] for n, _, _ in MK_FIGHTERS]
MK2_SPECIALS = [MK2_SPECIALS[MK2_SELECT_ORDER.index(n)] for n, _, _ in MK2_FIGHTERS]
# notes for the game pages (docs/), keyed by (game, fighter, move)
SPECIAL_NOTES = {
    ('mk', 'Sonya', 'Ring Toss'): 'quickly (all within about 0.4 s)',
    ('mk2', 'Kung Lao', 'Hat Throw'): 'Up / Down steer the hat',
    ('mk2', 'Raiden', 'Electric Grab'): 'close to the opponent',
    ('mk2', 'Jax', 'Back Breaker'): 'next to an opponent in the air',
    ('mk2', 'Scorpion', 'Air Throw'): 'next to an opponent in the air',
}


def sort_specials(sp):
    """A fighter's special moves [(move, command)] in alphabetical order; a heading
    (command None: Shang Tsung's "Morph into:") stays where it is and the moves
    after it are sorted among themselves."""
    out, cur = [], []
    for m in sp:
        if m[1] is None:
            out += sorted(cur, key=by_name)
            out.append(m)
            cur = []
        else:
            cur.append(m)
    return out + sorted(cur, key=by_name)


def specials(game):
    """(fighter name, [(move, command)]) in the order of the Character option,
    each fighter's moves in alphabetical order."""
    f, s = (MK2_FIGHTERS, MK2_SPECIALS) if game == 'mk2' else (MK_FIGHTERS, MK_SPECIALS)
    return [(n, sort_specials(m)) for (n, _, _), m in zip(f, s)]


def window_order(game, items):
    """items (fighters(game) or specials(game): the first element of each is the
    fighter's name) in the select screen's order, the one of the Move List
    window's pages (tools/tunit_window.py)."""
    order = MK2_SELECT_ORDER if game == 'mk2' else MK_SELECT_ORDER
    return sorted(items, key=lambda i: order.index(i[0]) if i[0] in order else len(order))     # (the hidden fighters last)


_SLOTS = {}
MK2_GAMES = ('mk2', 'plus', 'rev4')      # the games of Mortal Kombat II's lines ('plus' repeats the lines of 'mk2' and adds its own)


def _assign_slots():
    """The slot (the line's R[32 + slot], 0-7) of each move of Mortal Kombat II,
    Plus and rev 4.0: one slot for each text of a page line (name and distance) in
    every fighter and every game, so that a line the fighters have in common
    (Babality, Stage Fatality, Dead Pool, Friendship) is one CONF_STR line for
    them (the OSD's configuration string has 10,239 characters at most). A
    fighter's moves have different slots: the texts are coloured like a graph's
    nodes, the most shared first, so a text takes the lowest slot its fighters'
    other moves leave. The twelve stock fighters (of Mortal Kombat II and rev 4.0) are
    coloured first, as in Build 98 (the slots are in the MRAs' words of the revisions that
    lack moves), then the texts only the extra fighters of Plus and rev 4.0 have."""
    lists = {(g, li): [label(m[0], osd_dist(m[4], m[5])) for m in moves]
             for g in MK2_GAMES for li, (n, c, moves) in enumerate(fighters(g))}
    for (g, li), texts in lists.items():
        if len(set(texts)) != len(texts):
            raise ValueError('%s fighter %d: two moves with one text' % (g, li))
    slot = {}
    for part in (lambda g, li: g in ('mk2', 'rev4') and li < len(MK2_FIGHTERS), lambda g, li: True):
        adj, count = {}, Counter()
        for (g, li), texts in lists.items():
            if part(g, li):
                for t in texts:
                    count[t] += 1
                    adj.setdefault(t, set()).update(x for x in texts if x != t)
        for t in sorted(adj, key=lambda t: (-count[t], -len(adj[t]), t)):
            if t in slot:
                continue
            used = {slot[x] for x in adj[t] if x in slot}
            free = [k for k in range(8) if k not in used]
            if not free:
                raise ValueError('no slot for %r: the fighters\' moves need more than eight' % t)
            slot[t] = free[0]
    for (g, li), texts in lists.items():
        if len({slot[t] for t in texts}) != len(texts):
            raise ValueError('%s fighter %d: two moves in one slot' % (g, li))
    return {g: [[slot[t] for t in lists[(g, li)]] for li in range(len(fighters(g)))] for g in MK2_GAMES}


def slots(game, li):
    """The slot of each move of fighter li's page (the line's R[32 + slot]):
    MK and MK Plus: the move's index; MK2, Plus and rev 4.0: _assign_slots()."""
    if game not in MK2_GAMES:
        return list(range(len(fighters(game)[li][2])))
    if not _SLOTS:
        _SLOTS.update(_assign_slots())
    return _SLOTS[game][li]


def option_order(game):
    """The Character option's fighters in the order it lists them (alphabetical): [(name, line)],
    the line being the fighter's number in fighters(game) (the internal one: a fighter keeps his
    line in every game, the extra fighters of Plus and rev 4.0 follow the twelve)."""
    return sorted(((n, li) for li, (n, c, m) in enumerate(fighters(game))), key=lambda x: x[0].lower())


def fighters(game):
    """(name, id, moves) per OSD line (the fighters' internal numbers, see option_order()),
    with the stage moves every fighter has (MK: none). game: 'mk', 'mkp' (Mortal Kombat Plus), 'mk2',
    'plus' (Mortal Kombat II Plus: 'mk2's lines and its extra fighters') or 'rev4' (Mortal Kombat II rev 4.0:
    'mk2's lines and its hidden fighters')"""
    if game == 'mk2':
        return [(n, c, m + [MK2_DEADPOOL]) for n, c, m in MK2_FIGHTERS]
    if game == 'plus':           # Mortal Kombat II Plus: the twelve of 'mk2' (the same lines) and its extra fighters
        return fighters('mk2') + [(n, c, m + ([MK2_DEADPOOL] if dp else [])) for n, c, m, dp in PLUS_HIDDEN]
    if game == 'rev4':
        return list(REV4_FIGHTERS)
    if game == 'mkp':
        return list(MKP_FIGHTERS)
    return list(MK_FIGHTERS)


# --------------------------------------------------------------------------
# Programs
# --------------------------------------------------------------------------

KEYS = {'U': 0, 'D': 1, 'F': 2, 'B': 3, 'HP': 4, 'LP': 5, 'HK': 6, 'LK': 7, 'BL': 8}
OP_END, OP_TAP, OP_PRESS, OP_RELEASE, OP_WAIT, OP_READY, OP_WALK, OP_DIRECT = range(8)
DIRECT_STAGE2 = 1 << 12          # the DIRECT step's argument: bit 12 = the move's next site (a two-stage move)
DIRECT_KEEP = 1 << 11            # bit 11 = the program goes on when the game takes the move (the patch goes off): KEEP


def _steps(toks):
    """Program tokens to 16-bit steps, ending with END."""
    steps = []
    for t in toks:
        c = t[0]
        if c == '|':
            steps.append(OP_READY << 13)
        elif c == 'w':
            steps.append(OP_WAIT << 13 | int(t[1:]))
        elif c == '<':
            steps.append(OP_WALK << 13 | int(t[1:]))
        elif t == 'S2':
            steps.append(OP_DIRECT << 13 | DIRECT_STAGE2)       # the next site
        elif c in '[]':
            steps.append((OP_PRESS if c == '[' else OP_RELEASE) << 13 | 1 << KEYS[t[1:]])
        else:
            keys, _, n = t.partition('*')
            m = 0
            for k in keys.split('+'):
                m |= 1 << KEYS[k]
            n = int(n) if n else 3
            steps.append(OP_TAP << 13 | (n - 1) << 9 | m)
    steps.append(OP_END << 13)
    return steps


def direct_prog(char, hold_key=None):
    """The program text a direct finisher enters (see MK_DIRECT; hold_key: another
    (held key or None, tapped key), Mortal Kombat Plus's)."""
    hold, key = hold_key if hold_key else MK_DIRECT[char]
    toks = ['[' + hold] if hold else []
    toks += [key, 'w%d' % DIRECT_GAP] * DIRECT_TRIES
    toks += [']' + hold] if hold else []
    toks += ['w%d' % DIRECT_END]
    return ' '.join(toks)


def compile_prog(prog):
    """Program text to 16-bit steps: {op[15:13], arg[12:0]}; a tap's arg is
    {length - 1 [12:9], keys [8:0]}. Returns (steps, held first): held first
    when the move holds a button before its ready point."""
    toks = prog.split()
    if '|' not in toks:
        toks = ['|'] + toks
    return _steps(toks), toks.index('|') > 0


def compile_direct2(prog):
    """The steps of a Mortal Kombat II direct finisher: READY, DIRECT (the move's
    first site), the program's steps and their END. The move player starts
    here when the set has the move's sites, else at the combination."""
    toks = prog.split()
    keep = DIRECT_KEEP if toks and toks[0] == 'KEEP' else 0     # (Raiden's Electrocution: the taps come after the take)
    return [OP_READY << 13, OP_DIRECT << 13 | keep] + _steps(toks[1:] if keep else toks)


def compile_direct(direct):
    """The steps of a Mortal Kombat fatality, a direct finisher: READY, DIRECT
    n, the direct steps and their END, then one more END. DIRECT goes on into
    the direct steps when the MRA has a jump for the fighter (and turns the
    patch on), else skips the n steps after it, to the last END: the move is
    not taken."""
    d = _steps(direct.split())
    return [OP_READY << 13, OP_DIRECT << 13 | len(d)] + d + [OP_END << 13], False


# --------------------------------------------------------------------------
# Per-set RAM addresses (ROM index 1, words 0x200-0x229)
# --------------------------------------------------------------------------

CFG_BASE = 0x200
CFG_WORDS = 95
FORMAT = 2                       # (2: Build 93, 40 sites; the words 80-84 of format 1 moved to 88-94)
LVL_WORD = 42                    # words 42-43 (bytes 0x454-0x457): the AI level word
DEMO_WORD = 44                   # words 44-45 (bytes 0x458-0x45B): where the demo fights set the level
SITE_HI_WORD = 47                # the direct finishers' sites (direct_sites, MK; tunit_mk2sites, MK2): the high 12 bits
SITE_WORD = 48                   # of their word addresses, then the low 16 bits by site id (0 = no such site):
MAX_SITES = 40                   # MK: the character id (0-6); MK2: the order of MK2_DIRECT's sites (_mk2_site_ids)
POL_WORD = 88                    # words 88-90: bit n = 1 when site n's jump is a JRC (the patch sets bit 8, else clears it)
ALT_HI_WORD = 91                 # words 91-94: a second 1 Mbit window for the sites that are not in word 47's: its high 12 bits,
ALT_WORD = 92                    # then a bit per site id (rev 4.0's Babality in FFB0F940, Plus Beta 2's stage fatality in FFCF9920)

# The AI level word (the CPU opponent's level, 0 to 9; the game raises it
# after matches won and lowers it after matches lost) is found by the one
# routine that adjusts it: MOVE @level,A0 / ADD A1,A0 / clamp to 0..9 /
# MOVE A0,@level. The same in every MK and MK2 revision, hack ROMs included
# (one match in each, checked in MAME). The OSD's Fixed AI Difficulty option
# returns its level for the CPU's reads of the word, but not in the demo
# fights (see demo_pc).
LVL_PATTERN = [0x05A0, X, X, 0x4020, 0xCF01, 0x5600, 0x0B40, 0xFFF6, 0xC201, 0x1920, 0x0580, X, X, 0x0960]

# Moves a revision does not have, by MAME set name: (fighter or '*', move).
# Checked in MAME: played as on L3.1, the move is not taken. The Dead Pool's
# check is not there before L3.0; L2.x has Shang Tsung's friendship as
# B B D B HK and another stage move (Shang Tsung's); L1.x lacks most friendships, babalities and
# stage moves.
MISSING = {
    'mk2r11': [('*', 'Friendship'), ('*', 'Babality'), ('*', 'Stage Fatality'), ('*', 'Dead Pool'),
               ('Shang Tsung', 'Kintaro'), ('Liu Kang', 'Cartwheel'), ('Kung Lao', 'Hat Throw'),
               ('Johnny Cage', 'Decapitation'), ('Reptile', 'Slice'), ('Sub-Zero', 'Deep Freeze'),
               ('Sub-Zero', 'Ice Grenade'), ('Shang Tsung', 'Soul Drain'), ('Shang Tsung', 'Inner-Ear Explosion'),
               ('Kitana', 'Fan Decap'), ('Kitana', 'Kiss of Death'), ('Jax', 'Arm Rip'),
               ('Mileena', 'Inhale'), ('Scorpion', 'Toasty'), ('Scorpion', 'Slice'),
               ('Raiden', 'Electrocution'), ('Raiden', 'Super Uppercut')],
    'mk2r14': [('*', 'Stage Fatality'), ('*', 'Dead Pool'), ('Shang Tsung', 'Kintaro'),
               ('Liu Kang', 'Friendship'), ('Kung Lao', 'Friendship'), ('Johnny Cage', 'Friendship'),
               ('Reptile', 'Friendship'), ('Sub-Zero', 'Friendship'), ('Kitana', 'Friendship'),
               ('Jax', 'Friendship'), ('Mileena', 'Friendship'), ('Baraka', 'Friendship'),
               ('Scorpion', 'Friendship'), ('Raiden', 'Friendship'),
               ('Liu Kang', 'Babality'), ('Kung Lao', 'Babality'), ('Johnny Cage', 'Babality'),
               ('Reptile', 'Babality'), ('Sub-Zero', 'Babality'), ('Kitana', 'Babality'),
               ('Jax', 'Babality'), ('Mileena', 'Babality'), ('Baraka', 'Babality'),
               ('Scorpion', 'Babality'), ('Raiden', 'Babality'),
               ('Kung Lao', 'Hat Throw'), ('Reptile', 'Slice'), ('Sub-Zero', 'Ice Grenade'),
               ('Kitana', 'Fan Decap'), ('Mileena', 'Sai Stab'), ('Scorpion', 'Toasty'),
               ('Scorpion', 'Slice'), ('Raiden', 'Super Uppercut')],
    'mk2r20': [('*', 'Dead Pool'), ('Kung Lao', 'Friendship'), ('Shang Tsung', 'Friendship'),
               ('Shang Tsung', 'Stage Fatality'), ('Shang Tsung', 'Kintaro'), ('Raiden', 'Super Uppercut')],
    'mk2r21': [('*', 'Dead Pool'), ('Kung Lao', 'Friendship'), ('Shang Tsung', 'Friendship'),
               ('Shang Tsung', 'Stage Fatality'), ('Shang Tsung', 'Kintaro'), ('Raiden', 'Super Uppercut')],
}


def a32(p, i):
    return p.u32(i)


def stance(p, notes):
    """Where a fighter's process resumes in its stance loop (both games):
    MOVI 1,A0 / CALLA sleep / CALLR / JRC / CALLR / BTST 3,A0 / JRNE / BTST 2,A0.
    Mortal Kombat II rev 4.0 (mk2s08) is assembled with MOVK 1,A0 for the first
    instruction, one word shorter."""
    h = p.find([0x09C0, 0x0001, 0x0D5F, X, X, 0x0D3F, X, 0xC800, X, 0x0D3F, X, 0x1F80, 0xCB00, X, 0x1FA0])
    if len(h) == 1:
        return 0xFF800000 + (h[0] + 5) * 16
    if not h:
        h = p.find([0x1820, 0x0D5F, X, X, 0x0D3F, X, 0xC800, X, 0x0D3F, X, 0x1F80, 0xCB00, X, 0x1FA0])
        if len(h) == 1:
            return 0xFF800000 + (h[0] + 4) * 16
    # Mortal Kombat II Plus beta 2: the two BTSTs are in its patch, JA patch
    # (which starts BTST 3,A0 / JRNE 16-bit / BTST 2,A0)
    h = [k for k in p.find([0x09C0, 0x0001, 0x0D5F, X, X, 0x0D3F, X, 0xC800, X, 0x0D3F, X, 0xC080, X, X])
         if (lambda t: 0 <= t < len(p.w) - 5 and p.w[t] == 0x1F80 and p.w[t + 1] == 0xCB80 and p.w[t + 4] == 0x1FA0)(
             p.word_index(p.u32(k + 12)))]
    if len(h) == 1:
        return 0xFF800000 + (h[0] + 5) * 16
    notes.append('stance loop not found')
    return None


def mk2_addresses(p, notes):
    r = {}
    # finish routine: MOVE @P2 char,A0 / MOVE @P1 char,A1 / MOVI 0Ch,A2 /
    # CALLA / JREQ / MOVI 0Dh,A2 ... MOVK 3,A0 / MOVE A0,@state
    h = p.find([0x05A0, X, X, 0x05A1, X, X, 0x09C2, 0x000C, 0x0D5F, X, X, X, 0x09C2, 0x000D])
    if len(h) == 1:
        i = h[0]
        r['p2c'], r['p1c'] = a32(p, i + 1), a32(p, i + 4)
    else:
        # Mortal Kombat II Plus: the second load is moved into its patch,
        # MOVE @P2 char,A0 / JA patch / MOVI 0Ch,A2 / ..., and the patch
        # starts with MOVE @P1 char,A1
        h = p.find([0x05A0, X, X, 0xC080, X, X, 0x09C2, 0x000C, 0x0D5F, X, X, X, 0x09C2, 0x000D])
        if len(h) != 1:
            notes.append('finish routine not found')
            return None
        i = h[0]
        t = p.word_index(p.u32(i + 4))
        if not 0 <= t < len(p.w) - 3 or p.w[t] != 0x05A1:
            notes.append('finish routine not found')
            return None
        r['p2c'], r['p1c'] = a32(p, i + 1), a32(p, t + 1)
    s = [k for k in p.find([0x1860, 0x0580, X, X]) if 0 < k - i < 60]
    st = [k for k in p.find([0x05A3, X, X, 0x2483, 0x0B23]) if 0 < k - i < 120]   # MOVE @stage,A3 / SLL 4,A3 / ADDI
    fl = [k for k in p.find([0x05A0, X, X, 0x0B40, 0x0000]) if 0 < k - i < 200]   # MOVE @flag,A0 / CMPI 0FFFFh,A0
    if len(s) != 1 or len(st) != 1 or not fl:
        notes.append('round state, stage or finish flag not found')
        return None
    r['state'], r['stage'], r['flag'] = a32(p, s[0] + 2), a32(p, st[0] + 1), a32(p, fl[0] + 1)
    # energies: MOVI P1,A0 / MOVI ..,A1 / CALLR / MOVI P2,A0 / MOVI ..,A1
    e = [k for k in p.find([0x09E0, X, X, 0x09E1, X, X, 0x0D3F, X, 0x09E0, X, X, 0x09E1])
         if a32(p, k + 9) - a32(p, k + 1) == r['p2c'] - r['p1c']]
    # pointers: MOVE @P2 obj,A8,1 / MOVE A8,*A13(140h),1 / MOVE @P2 proc,A8,1 /
    # .. / MOVE @P1 proc,A8,1 / .. / MOVE @P1 obj,A8,1
    o = [k for k in p.find([0x07A8, X, X, 0xB30D, 0x0140, 0x07A8, X, X, 0xB30D, 0x0170, 0x07A8, X, X,
                            0xB30D, 0x0290, 0xBB0D, 0x0100, 0x0100, 0x07A8, X, X])
         if a32(p, k + 1) > a32(p, k + 19)]
    if len(e) != 1 or len(o) != 1:
        notes.append('energies or player pointers not found')
        return None
    r['p1e'], r['p2e'] = a32(p, e[0] + 1), a32(p, e[0] + 9)
    k = o[0]
    r['p2o'], r['p2p'], r['p1p'], r['p1o'] = a32(p, k + 1), a32(p, k + 6), a32(p, k + 11), a32(p, k + 19)
    # the opponent check of the move starts: MOVE *A13(170h),A0,1 /
    # MOVE *A0(0E0h),A0,1 / CMPI dizzy,A0 / JREQ [/ CMPI dizzy 2,A0]
    # / JRNE / MOVE A13,-*SP,1 / MOVE *A13(290h),A13,1 (L1.1 has one code)
    tail = [0x0300, 0xA3AF, 0xB7AD, 0x0290]
    d = [(k, 2) for k in p.find([0xB7A0, 0x0170, 0xB600, 0x00E0, 0x0B60, X, X, X, 0x0B60, X, X, X] + tail)] + \
        [(k, 1) for k in p.find([0xB7A0, 0x0170, 0xB600, 0x00E0, 0x0B60, X, X, X] + tail)]
    if not d:
        # Mortal Kombat II Plus beta 2 moves the first two instructions into
        # its patch: JA patch / NOP, and the patch ends with a JA back to the
        # first CMPI
        for k in p.find([0xC080, X, X, 0x0300, 0x0B60, X, X, X, 0x0B60, X, X, X] + tail):
            t = p.word_index(p.u32(k + 1))
            back = 0xFF800000 + 16 * (k + 4)
            if 0 <= t < len(p.w) - 40 and any(p.w[m:m + 5] == (0xB7A0, 0x0170, 0xB600, 0x00E0, 0xC080)
                                              and p.u32(m + 5) == back for m in range(t, t + 40)):
                d.append((k, 2))           # the CMPIs are at the same offsets
    if len(d) != 1:
        notes.append('dizzy check not found')
        return None
    k, n = d[0]
    r['diz1'] = ~a32(p, k + 5) & 0xFFFFFFFF
    r['diz2'] = ~a32(p, k + 9) & 0xFFFFFFFF if n == 2 else r['diz1']
    r['stance'] = stance(p, notes)
    return r if r['stance'] else None


def mk_addresses(p, notes):
    r = {}
    # MOVE @P2 char,A2 / MOVI 7,A0 / MOVI 8,A1 / CALLA / JREQ / MOVE @P1 char,A2
    h = p.find([0x05A2, X, X, 0x09C0, 0x0007, 0x09C1, 0x0008, 0x0D5F, X, X, X, 0x05A2, X, X])
    # MOVE @..,A0 / JRNE / MOVK 3,A0 / MOVE A0,@state (the finish routine)
    s = sorted(set(a32(p, k + 6) for k in p.find([0x05A0, X, X, X, 0x1860, 0x0580, X, X]) if p.w[k + 3] >> 12 == 0xC))
    # MOVI P1 energy,A0 / MOVI ..,A1 / MOVE @P1 obj,A2,1 / CMP A2,A8 / JREQ / MOVI P2 energy,A0
    e = p.find([0x09E0, X, X, 0x09E1, X, X, 0x07A2, X, X, 0x4848, X, 0x09E0, X, X])
    st = sorted(set(a32(p, k + 1) for k in p.find([0x05A3, X, X, 0x2483, 0x0B23])))
    # the finish routine's wait: MOVI 1,A0 / CALLA sleep / MOVE @flag,A0 / JRNE
    fl = [k for k in p.find([0x09C0, 0x0001, 0x0D5F, X, X, 0x05A0, X, X, X]) if p.w[k + 8] >> 8 == 0xCB]
    if len(h) != 1 or len(s) != 1 or len(e) != 1 or len(st) != 1 or len(fl) != 1:
        notes.append('fight variables not found')
        return None
    r['p2c'], r['p1c'], r['state'] = a32(p, h[0] + 1), a32(p, h[0] + 12), s[0]
    r['p1e'], r['p1o'], r['p2e'] = a32(p, e[0] + 1), a32(p, e[0] + 7), a32(p, e[0] + 12)
    gap = r['p2e'] - r['p1e']
    r['p2o'] = r['p1o'] + gap
    r['p1p'], r['p2p'] = r['p1o'] + 0x40, r['p1o'] + 0x40 + gap
    r['stage'], r['flag'] = st[0], a32(p, fl[0] + 6)
    # the loser's dizzy loop: MOVI 2,A0 / CALLA sleep / CALLA / MOVE @state,A0 /
    # CMPI 3,A0 / JREQ (resumes after the sleep)
    d = p.find([0x09C0, 0x0002, 0x0D5F, X, X, 0x0D5F, X, X, 0x05A0, r['state'] & 0xFFFF, r['state'] >> 16, 0x0B40, 0xFFFC])
    if len(d) != 1:
        notes.append('dizzy loop not found')
        return None
    r['diz1'] = r['diz2'] = 0xFF800000 + (d[0] + 5) * 16
    r['stance'] = stance(p, notes)
    return r if r['stance'] else None


# The fatality handlers (MK 5.0 FFD9A0D0-FFD9CCF0, the same in every MK set
# checked: 5.0, 4.0, Turbo Ninja) each start with MOVE @state,A0 / CMPI 3,A0 /
# JRNE exit, test the fighter's distance, and then MOVI pattern,A11 / CALLR
# matcher / JRNC exit: the matcher compares the joystick history with the
# pattern (a word with a zero end: the directions, newest first, 1 Up,
# 2 Forward, 3 Down, 4 Back). Each fighter's pattern is its fatality's
# directions; the button that follows is what the handler runs on.
DIRECT_PATTERNS = {(2, 2, 2): 0, (2, 3, 4): 1, (4, 4, 4, 2): 2, (3, 2, 1, 4, 3): 3,
                   (1, 1): 4, (2, 3, 2): 5, (4, 4, 2, 2): 6}      # -> character id


def direct_sites(prog_bytes, state):
    """Each fighter's no-match jump (JRNC after the matcher call): {character
    id: word index of its opcode word} and notes. A fighter is there only if
    exactly one handler (one that tests the round state first) has its pattern
    and every jump found goes to the same exit."""
    p = Prog(prog_bytes)
    sl, sh = state & 0xFFFF, state >> 16
    notes, sites, exits = [], {}, set()
    for i in p.find([0x09EB, X, X, 0x0D3F, X]):      # MOVI table,A11 / CALLR matcher
        j = i + 5
        op = p.w[j]
        if op >> 8 != 0xC9 or op & 0xFF == 0x80:     # JRNC with an 8 or 16 bit offset
            continue
        tb = p.word_index(p.u32(i + 1))
        if not 0 <= tb < len(p.w) - 10:
            continue
        ev = []
        for k in range(1, 10):
            if p.w[tb + k] == 0:
                break
            ev.append(p.w[tb + k])
        c = DIRECT_PATTERNS.get(tuple(ev)) if len(ev) < 9 else None
        if c is None:
            continue
        if not any(p.w[m:m + 5] == (0x05A0, sl, sh, 0x0B40, 0xFFFC) for m in range(max(0, i - 40), i)):
            continue
        if op & 0xFF:
            off = (op & 0xFF) - 256 if op & 0x80 else op & 0xFF
            end = j + 1 + off
        else:
            off = p.w[j + 1] - 65536 if p.w[j + 1] & 0x8000 else p.w[j + 1]
            end = j + 2 + off
        sites.setdefault(c, []).append((j, end))
    out = {}
    for c, lst in sorted(sites.items()):
        if len(lst) != 1:
            notes.append('direct finisher %d: %d handlers found, not used' % (c, len(lst)))
            continue
        out[c] = lst[0][0]
        exits.add(lst[0][1])
    if len(exits) > 1:
        notes.append('direct finishers: the handlers do not share one exit, not used')
        return {}, notes
    if out:
        notes.append('direct finishers for %d fighters, handlers exit at %08X'
                     % (len(out), 0xFF800000 + 16 * exits.pop()))
    else:
        notes.append('direct finishers not found')
    return out, notes


# Mortal Kombat Plus's Babality routines: CALLA matcher / JRNC fail / MOVI A0 / MOVI A1 / CALLA
# (the buttons used) / JRNE fail / JR found. The two differ in A0 (the last button: the immediate
# 30000030h High Kick, 10000070h Low Kick).
BABALITY_MASKS = {BAB_HK: (0x0030, 0x3000), BAB_LK: (0x0070, 0x1000)}


def babality_sites(prog_bytes):
    """Mortal Kombat Plus's Babality routines' no-match jumps: {site id (BAB_HK, BAB_LK):
    word index of the JRNC's opcode word}, empty for a set without them. Both have to be
    there, and exactly once."""
    p = Prog(prog_bytes)
    out = {}
    for site, (lo, hi) in BABALITY_MASKS.items():
        hits = [i for i in p.find([0x0D5F, X, X, X, 0x09E0, lo, hi, 0x09E1, X, X, 0x0D5F, X, X, X, X])
                if p.w[i + 3] >> 8 == 0xC9 and p.w[i + 13] >> 8 == 0xCB and p.w[i + 14] >> 8 == 0xC0]
        if len(hits) != 1:
            return {}
        out[site] = hits[0] + 3
    return out


def mk2_direct_sites(prog_bytes, setname=''):
    """Mortal Kombat II's direct finishers' sites in a set: {site id: word index
    of the jump's opcode word}, {word index: patch value of bit 8} and notes. A
    move's sites all have to be there (a two-stage move has two), else none of
    them is used and the move keeps its combination. Rev 4.0 (REV4_DIRECT_SETS)
    has its own sites and ids, Plus the stock ones (PLUS_SITES for the moved)."""
    game = 'rev4' if setname in REV4_DIRECT_SETS else 'mk2'
    if game == 'rev4':
        found, pol, notes = tunit_mk2sites.align_rev4(prog_bytes)
        table, fighters_ = REV4_DIRECT, REV4_FIGHTERS
    else:
        found, pol, notes = tunit_mk2sites.align(prog_bytes, PLUS_SITES.get(setname))
        table, fighters_ = MK2_DIRECT, MK2_FIGHTERS
    if not found:
        return {}, {}, notes
    ids = _mk2_site_ids(game)
    use = {}
    left = []
    for fname, cid, moves in fighters_:
        for mv in moves:
            d = table.get(fname, {}).get(mv[0])
            if not d:
                continue
            if all(a in found for a in d[0]):
                for a in d[0]:
                    use[ids.index(a)] = found[a]
            else:
                left.append('%s %s' % (fname, mv[0]))
    # a site another move needs is used even if this move cannot be (a shared one is in every list)
    notes.append('MK2 direct finishers: %d of %d sites' % (len(use), len(ids)))
    if left:
        notes.append('MK2 direct finishers not used: ' + ', '.join(left))
    return use, {j: pol[j] for j in use.values()}, notes


def addresses(gid, prog_bytes):
    """The set's fight variables, or None, and notes."""
    p = Prog(prog_bytes)
    notes = []
    if gid == G_MK2:
        r = mk2_addresses(p, notes)
    elif gid in (G_MK, G_MKTURBO):
        r = mk_addresses(p, notes)
    else:
        return None, []
    return r, notes


def level_word(prog_bytes):
    """The AI level word's bit address, or None (not found, or not exactly one
    adjust routine with the same word read and written)."""
    p = Prog(prog_bytes)
    h = p.find(LVL_PATTERN)
    if len(h) != 1 or p.u32(h[0] + 1) != p.u32(h[0] + 11):
        return None
    return p.u32(h[0] + 1)


def demo_pc(prog_bytes):
    """The demo fights' store of the level: between games the attract mode
    sets up a fight of two random fighters and sets the level to 5 with
    MOVK 5,A0 / MOVE A0,@level,0 (one such pair in each set; the game's real
    starts store the level elsewhere). Returns the bit address of the
    instruction after the store, which is the CPU's PC while the store
    completes, or None (not found, or not exactly one)."""
    lv = level_word(prog_bytes)
    if lv is None:
        return None
    p = Prog(prog_bytes)
    h = p.find([0x18A0, 0x0580, lv & 0xFFFF, lv >> 16])
    if len(h) != 1:
        return None
    return 0xFF800000 + (h[0] + 4) * 16


def level_part(prog_bytes):
    """The level word and the demo store's PC as table bytes (words 42-45: word
    address = bit address >> 4, low word first, each) and a note; b'' if the
    level word is not found. The demo PC is zero if it is not found: the
    option then pins the demo fights' level too."""
    a = level_word(prog_bytes)
    if a is None:
        return b'', 'AI level word not found'
    d = demo_pc(prog_bytes)
    note = 'AI level word %08X' % a
    if d is None:
        note += ', demo store not found'
        d = 0
    else:
        note += ', demo fights set it at %08X (PC after the store)' % d
    return struct.pack('<4H', (a >> 4) & 0xFFFF, a >> 20, (d >> 4) & 0xFFFF, d >> 20), note


def missing_mask(gid, setname):
    """Bit line * 8 + slot set for each move of the OSD the set lacks."""
    game = 'mk2' if gid == G_MK2 else 'mk'
    m = 0
    gone = MISSING.get(setname, [])
    for line, (name, cid, moves) in enumerate(fighters(game)):
        for slot, mv in zip(slots(game, line), moves):
            if (name, mv[0]) in gone or ('*', mv[0]) in gone:
                m |= 1 << (line * 8 + slot)
    return m


# The Finishing Moves page lists only the moves the loaded revision has. The
# OSD cannot be built per set (one CONF_STR), so the revisions are sorted into
# classes by the moves they lack: class 0 lacks none (and is what every set
# without a table, every Mortal Kombat set and a download without the word
# gets), the others are the distinct sets of missing moves in MISSING, fewest
# missing first. The MRA gives the set's class (ROM index 1 word 0x21F, the
# top level keeps it in fm_class) and two bits of the OSD's menu mask carry it:
# class bit 0 is mask bit 2 and class bit 1 is mask bit 12. A move's line shows
# for the classes (and fighters, and rev 4.0) that have it, as the fewest cubes
# the hide prefixes can name (line_cover()).
CLASS_WORD = 31
CLASS_MASK = ('2', 'C')          # status_menumask bits of class bits 0 and 1


def class_masks():
    """The missing-move masks of the classes, class 0 (nothing missing) first."""
    masks = sorted({missing_mask(G_MK2, name) for name in MISSING} - {0}, key=lambda m: (bin(m).count('1'), m))
    if len(masks) > 3:
        raise ValueError('more than four classes of revisions: the OSD has two bits for them')
    return [0] + masks


def set_class(gid, setname):
    """The class of a set (0 for every set but the Mortal Kombat II revisions
    that lack moves)."""
    if gid != G_MK2:
        return 0
    return class_masks().index(missing_mask(gid, setname))


def build(gid, prog_bytes, setname=None):
    """ROM index 1 words 0x200 on (bytes) and notes; empty if the set has no
    finishing moves.

    Words: 0 format, 1 reserved, then word addresses (bit address >> 4, low
    word first) of the round state, P1 and P2 character, energy, object
    pointer and process pointer, the stage and the finish flag (2-23); the
    dizzy codes 1 and 2 and the stance code (24-29, 32-bit values); x and
    resume-address offsets in words (30: {resume[15:8], x[7:0]}); the moves
    the set lacks (32-39: bit line * 8 + slot of the OSD's moves; 31: the
    set's class of them, set_class()); MK: the
    word address of Reptile's flag (40-41, the top level's Reptile Fight
    Next is used up when the game writes 1 there; 0 = no Reptile); the word
    address of the AI level (42-43; 0 = none), the demo fights' store of the
    level (44-45); the direct finishers' sites (46-94): word 47 has the high
    12 bits of the jumps' word addresses, 48 + id the low 16 bits (0 = the set
    has no such site; MK: the character id, direct_sites; MK2: the order of
    MK2_DIRECT's sites or rev 4.0's REV4_DIRECT, mk2_direct_sites; 40 ids,
    48-87), 88-90 a bit per site that is a JRC, 91 the high 12 bits of a
    second window and 92-94 a bit per site that is in it (46 is not used)."""
    r, notes = addresses(gid, prog_bytes)
    if not r:
        return b'', notes
    w = [0] * CFG_WORDS
    w[0] = FORMAT
    for n, k in enumerate(['state', 'p1c', 'p2c', 'p1e', 'p2e', 'p1o', 'p2o', 'p1p', 'p2p', 'stage', 'flag']):
        a = r[k] >> 4
        w[2 + 2 * n], w[3 + 2 * n] = a & 0xFFFF, a >> 16
    for n, k in enumerate(['diz1', 'diz2', 'stance']):
        w[24 + 2 * n], w[25 + 2 * n] = r[k] & 0xFFFF, r[k] >> 16
    w[30] = (0xE0 >> 4) << 8 | (0x90 >> 4)
    notes.append('round state %08X, P1 character %08X, object pointer %08X, stage %08X, finish flag %08X'
                 % (r['state'], r['p1c'], r['p1o'], r['stage'], r['flag']))
    gone = missing_mask(gid, setname)
    for n in range(8):
        w[32 + n] = gone >> (16 * n) & 0xFFFF
    w[CLASS_WORD] = set_class(gid, setname)
    if gone:
        notes.append('%d moves not in this revision (OSD class %d)' % (bin(gone).count('1'), w[CLASS_WORD]))
    if gid in (G_MK, G_MKTURBO):
        rp = mk_reptile(Prog(prog_bytes), [])
        if rp:
            w[40], w[41] = (rp[1] >> 4) & 0xFFFF, rp[1] >> 20
            notes.append('Reptile flag %08X' % rp[1])
    if gid in (G_MK, G_MKTURBO):
        sites, dn = direct_sites(prog_bytes, r['state'])
        notes += dn
        if sites:
            bs = babality_sites(prog_bytes)          # Mortal Kombat Plus: the Babalities' (the fatalities' handlers are there too)
            if bs:
                notes.append('Babality sites %s' % ', '.join('%d at %08X' % (k, 0xFF800000 + 16 * j) for k, j in sorted(bs.items())))
            sites = {**sites, **bs}
            his = Counter((0xFF800000 + 16 * j) >> 20 for j in sites.values())
            main = his.most_common(1)[0][0]
            alt = set(his) - {main}
            assert len(alt) <= 1, 'MK sites in more than two 1 Mbit windows'
            w[SITE_HI_WORD] = main
            if alt:
                w[ALT_HI_WORD] = alt.pop()
            for c, j in sites.items():
                w[SITE_WORD + c] = ((0xFF800000 + 16 * j) >> 4) & 0xFFFF
                if (0xFF800000 + 16 * j) >> 20 != main:
                    w[ALT_WORD + c // 16] |= 1 << (c % 16)
    if gid == G_MK2 and (setname in MK2_DIRECT_SETS or setname in REV4_DIRECT_SETS):
        sites, pol, dn = mk2_direct_sites(prog_bytes, setname)
        notes += dn
        if sites:
            his = Counter((0xFF800000 + 16 * j) >> 20 for j in sites.values())
            main = his.most_common(1)[0][0]
            alt = set(his) - {main}
            assert len(alt) <= 1, 'MK2 sites in more than two 1 Mbit windows'
            w[SITE_HI_WORD] = main
            if alt:
                w[ALT_HI_WORD] = alt.pop()
            for n, j in sites.items():
                w[SITE_WORD + n] = ((0xFF800000 + 16 * j) >> 4) & 0xFFFF
                assert w[SITE_WORD + n] != 0
                if pol[j]:
                    w[POL_WORD + n // 16] |= 1 << (n % 16)
                if (0xFF800000 + 16 * j) >> 20 != main:
                    w[ALT_WORD + n // 16] |= 1 << (n % 16)
    lv = level_word(prog_bytes)
    if lv is not None:
        w[LVL_WORD], w[LVL_WORD + 1] = (lv >> 4) & 0xFFFF, lv >> 20
        notes.append('AI level word %08X' % lv)
        dp = demo_pc(prog_bytes)
        if dp is not None:
            w[DEMO_WORD], w[DEMO_WORD + 1] = (dp >> 4) & 0xFFFF, dp >> 20
            notes.append('demo store PC %08X' % dp)
    else:
        notes.append('AI level word not found')
    return struct.pack('<%dH' % CFG_WORDS, *w), notes


# --------------------------------------------------------------------------
# Messages (OSD info, CONF_STR "I" line; numbers 1-31)
# --------------------------------------------------------------------------

MESSAGES = [
    ('SET', "Finishing move set: it plays\nat the next FINISH HIM"),
    ('NOT_THIS', "Not this fighter's FINISH HIM:\nthe move waits for a later one"),
    ('FAR', "Too far: step closer"),
    ('CLOSE', "Too close: step back"),
    ('STAGE', "Stage move: The Pit II\nand Kombat Tomb only"),
    ('PIT2', "Stage move: The Pit II only"),
    ('DEAD', "Dead Pool only"),
    ('OVER', "FINISH HIM is over: the move\nwaits for the next one"),
    ('NOT_TAKEN', "Move not taken"),
    ('NOT_TAKEN_FB', "Not taken: a Friendship or\nBabality needs a round won\nwithout punches"),
    ('CLEARED', "Finishing move cleared"),
    ('STAGE4', "Not taken: stage move for\nKombat Tomb / The Pit II /\nYoteigai Tor / Pit (MK1)"),
    ('SECURITY', "Security Screen on: it starts\neach attract cycle"),
    ('HITBOXES', "Hitboxes on: shown in fights"),
    ('PONG', "Pong on: it follows the first\nround of a 2-player battle"),
    ('NOOB', "Noob Saibot on: the winner of\nthe first round of a 2-player\nbattle fights him"),
    ('JADE', "Jade on: the first round you\nwin in a 1-player game is\nfollowed by her fight"),
    ('SMOKE', "Smoke on: hold Down and press\nStart in a fight"),
    ('CODE_OK', "Code entered"),
    ('CODE_FAIL', "Code not taken: codes work\nin the attract mode"),
    ('ON_ALL', "On for all players"),
    ('ON_NEXT', "On for all players from the\nnext game"),
    ('CODE_MATCHUP', "Code not taken: pick it on\nTonight's Match-Up"),
    ('REPT_SET', "Reptile fight set: win a match\nin a 1-player game"),
    ('REPT_CLEARED', "Reptile fight cleared"),
    ('REPT_MOON', "Moon Silhouettes on: every\nmatch on The Pit has them"),
    ('REPT_HINTS', "Reptile Hints on: he drops in\nbefore every round"),
    ('ATTRACT', "Attract Sound: Always On"),
    ('ATTRACT_OFF', "Attract Sound: Default"),
]

N_FM_MESSAGES = 12             # the move player's (rtl/tunit_fmoves.sv)

# OSD status bits (top level)
SEL_MK2 = (27, 24)               # O[27:24] fighter, MK2 and rev 4.0
SEL_PLUS = (28, 24)              # O[28:24] fighter, Plus (17 fighters)
SEL_MK = (30, 28)                # O[30:28] fighter, MK
SLOT_BIT = 32                    # R[32] + line: the fighter's moves
LIST_BIT = 114                  # O[114] Move List: Off, On (the pages: rtl/tunit_mlpage.sv, tools/tunit_window.py)
MASK_PLUS = 'F'                  # status_menumask bit 15: Mortal Kombat II Plus (its own Move List line)
CLEAR_BIT = 40                   # R[40]: clear the set move
MASK_SEL = 8                     # status_menumask bits 8-11: the page's fighter
MASK_REV4 = '7'                  # status_menumask bit 7: Mortal Kombat II rev 4.0 (Judge Dredd's bit; the Secret Audit Menu lines hide for MK2)


def sv_str(s):
    return s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')


def sel_prefix(game, li, free=0):
    """Hide prefixes that show a line only for the game (menu mask bit 4: MK
    (h4 and class bit 0 clear) or MK Plus (class bit 0 set)) and fighter li
    (bits 8-10 = the Character option; MK's bit 11 is always 0). The bits of
    `free` are left out: the line shows for every fighter that differs from li
    only there. (The MK2 lines, which share a line by fighter, revision class and
    rev 4.0 too, are made by line_cover().)"""
    pre = {'mk': 'h4H' + CLASS_MASK[0], 'mkp': 'h4h' + CLASS_MASK[0]}[game]
    for b in range(3):
        if not free >> b & 1:
            pre += ('h' if li >> b & 1 else 'H') + '0123456789ABCDEF'[MASK_SEL + b]
    return pre


def fighter_cubes(lines, nbits=3):
    """The fewest groups of fighter lines (value, free-bit mask) that together are
    exactly `lines`: a line the fighters have in common is one OSD line for a group
    (the string has no room for a line per fighter; hide prefixes test only the fixed bits)."""
    lines = frozenset(lines)
    cubes = []
    for free in range(1 << nbits):
        for v in range(1 << nbits):
            if v & free:
                continue
            members = frozenset(v | f for f in range(1 << nbits) if not f & ~free)
            if members <= lines:
                cubes.append((v, free, members))
    best = [None]

    def search(left, chosen):
        if best[0] is not None and len(chosen) >= len(best[0]):
            return
        if not left:
            best[0] = list(chosen)
            return
        first = min(left)
        for v, free, members in cubes:
            if first in members and members <= left:
                search(left - members, chosen + [(v, free)])
    search(lines, [])
    return sorted(best[0])


# A Mortal Kombat II line (one text on one slot) shows for the points of eight menu
# mask bits: bits 8-11 the fighter, 2 and 12 the revision class, 7 rev 4.0, 15 Plus. A
# Plus fighter has five bits: bit 12 is the fifth (Plus has no classes). A line's hide
# prefixes name some of the bits and the line shows for every point that has them: a
# cube of the points. A text that fighters, revisions and games have in common is a few
# lines for all of them, not a line for each (the OSD's configuration string has 10,239
# characters at most).
P_CLASS0, P_CLASS1, P_REV4, P_PLUS = 4, 5, 6, 7      # a point's bits: fighter 0-3, class bits 0 and 1 (Plus: fighter bit 4), rev 4.0, Plus
NPB = 8
_CUBES = []


def _cubes():
    """Every cube of the 256 points: (fixed bits, their values, the points as a bit mask)."""
    if not _CUBES:
        for fix in range(1 << NPB):
            val = fix
            while True:
                pts = 0
                for p in range(1 << NPB):
                    if p & fix == val:
                        pts |= 1 << p
                _CUBES.append((fix, val, pts, bin(fix).count('1')))
                if val == 0:
                    break
                val = (val - 1) & fix
    return _CUBES


def mk2_point(game, li, cls=0):
    """The point of fighter li (the line number), in a game ('mk2', 'plus' or 'rev4') and, for
    'mk2', revision class cls (0-3)."""
    if game == 'rev4':
        return li | 1 << P_REV4
    if game == 'plus':
        return (li & 15) | (li >> 4) << P_CLASS1 | 1 << P_PLUS
    return li | (cls & 1) << P_CLASS0 | (cls >> 1) << P_CLASS1


def mk2_dont_care(nclasses):
    """The points no set can have: fighter numbers past the last of the game, classes no set
    is in, any class for rev 4.0 and Plus (their sets lack no moves) and both games at once:
    a line may show for them."""
    dc = set()
    n = {g: len(fighters(g)) for g in MK2_GAMES}
    for p in range(1 << NPB):
        li, c0, c1, rev4, plus = p & 15, p >> P_CLASS0 & 1, p >> P_CLASS1 & 1, p >> P_REV4 & 1, p >> P_PLUS & 1
        if plus:
            ok = not rev4 and not c0 and li | c1 << 4 < n['plus']
        elif rev4:
            ok = not c0 and not c1 and li < n['rev4']
        else:
            ok = li < n['mk2'] and c0 | c1 << 1 < nclasses
        if not ok:
            dc.add(p)
    return dc


def line_cover(points, dc, text_len):
    """The cubes (fixed bits, values) that together show a line for exactly `points`
    (a set of points; the points of `dc` may or may not show it), each point in one cube
    only (a line in two cubes would show twice), as few as the search finds (each costs
    a line of CONF_STR) and with the shortest prefixes: the best way to split the points
    along the bits (a cube that is all points, or its halves split along a bit), then
    each cube loses the fixed bits it can do without."""
    V = sum(1 << p for p in points)
    allowed = V | sum(1 << p for p in dc)
    by_cube = {(fix, val): bits for fix, val, bits, nf in _cubes()}
    unit = 8 + text_len + 1 + 2              # P4R[nn],<text>; and h5
    memo = {}

    def solve(fix, val):
        k = (fix, val)
        if k in memo:
            return memo[k]
        bits = by_cube[k]
        if not bits & V:
            best = (0, [])
        else:
            best = None
            if not bits & ~allowed:
                best = (unit + 2 * bin(fix).count('1'), [k])
            for b in range(NPB):
                if not fix >> b & 1:
                    c0, l0 = solve(fix | 1 << b, val)
                    c1, l1 = solve(fix | 1 << b, val | 1 << b)
                    if best is None or c0 + c1 < best[0]:
                        best = (c0 + c1, l0 + l1)
        memo[k] = best
        return best
    out = []
    for fix, val in solve(0, 0)[1]:
        mine = by_cube[(fix, val)] & V
        for b in range(NPB):                 # the bits the cube can do without
            if fix >> b & 1:
                f2, v2 = fix & ~(1 << b), val & ~(1 << b)
                bits = by_cube[(f2, v2)]
                if not bits & ~allowed and bits & V == mine:
                    fix, val = f2, v2
        out.append((fix, val))
    return sorted(out)


def cube_prefix(fix, val):
    """The hide prefixes of a cube: Mortal Kombat II (h5), then the bits it fixes:
    h<bit> shows the line when the mask bit is set, H<bit> when it is clear."""
    pre = 'h5'
    for b, letter in ((P_PLUS, MASK_PLUS), (P_REV4, MASK_REV4)):
        if fix >> b & 1:
            pre += ('h' if val >> b & 1 else 'H') + letter
    for b in range(4):
        if fix >> b & 1:
            pre += ('h' if val >> b & 1 else 'H') + '0123456789ABCDEF'[MASK_SEL + b]
    for b, letter in ((P_CLASS0, CLASS_MASK[0]), (P_CLASS1, CLASS_MASK[1])):
        if fix >> b & 1:
            pre += ('h' if val >> b & 1 else 'H') + letter
    return pre


OSD_WIDTH = 27           # the longest text of a page line


def osd_dist(dmin, dmax):
    """A move's distance as the page shows it: dist() with "or farther" cut to
    "or more" (the longest line, rev 4.0's Body Explosion, has to fit the page)."""
    return dist(dmin, dmax).replace(' or farther', ' or more')


def label(name, distance):
    """A move's line on the page: its name at the left and the distance it
    needs flush right (the page shows the distance in place of the command)."""
    pad = OSD_WIDTH - len(name) - len(distance)
    for short in (' or far', '+'):              # a line too long: "Sweep or more", then "Sweep or far", then "Sweep+"
        if pad < 1 and ' or ' in distance:       # (rev 4.0's Body Explosion is "Sweep or far")
            distance = distance[:distance.index(' or ')] + short
            pad = OSD_WIDTH - len(name) - len(distance)
    if pad < 1 and ' to ' in distance:          # "Close to jump" as "Close-jump" (rev 4.0's Red Dragon Flame)
        distance = distance.replace(' to ', '-')
        pad = OSD_WIDTH - len(name) - len(distance)
    s = name + ' ' * max(pad, 1) + distance
    if pad < 1 or ',' in s or ';' in s:
        raise ValueError('label too long or with , / ;: ' + s)
    return s


def by_name(move):
    """Sort key of a move (a tuple of the fighter tables): the page and the docs
    list each fighter's moves in alphabetical order (the ids, slots and the
    window's Move List keep the game's order)."""
    return move[0].lower()


# The page and the docs' finishing tables list a fighter's finishing moves by
# type (Fatalities, Stage Fatalities with the Dead Pool, Friendship, Babality),
# alphabetically within a type; the Move List windows stay alphabetical.
KIND_RANK = {K_FATAL: 0, K_STAGE: 1, K_PIT2: 1, K_STAGE4: 1, K_DEAD: 1, K_FRIEND: 2, K_BABY: 3}


def by_type(move):
    """Sort key of a move on the page: its type, then its name."""
    return (KIND_RANK[move[1]], move[0].lower())


EXTRAS_PAGE = 5          # the Extras page (Arcade-Midway-T-Unit.sv): Auto Finishing Moves is a page of it


def extras_lines():
    """CONF_STR lines of the Extras page (P5) that are the Finishing Moves'
    and the Move List's: (the Auto Finishing Moves entry, the Move List option).
    Both are lines of the page, so the page's items stay in alphabetical order.
    The Move List option (Off or On: the window of rtl/tunit_window.sv, its pages
    turned with Left and Right) is there twice for the same status bit: for MK,
    MK Plus and MK2 (mask bit 3, not bit 15) and for Mortal Kombat II Plus
    (bit 15; its pages are the hack's own, tools/tunit_plus.py). The Auto
    Finishing Moves entry opens the Finishing Moves page (P4) from the Extras
    page (a page inside a page: 'P5P4'); the page's back line leads to the main menu.
    Mortal Kombat Plus has the page of Mortal Kombat: the entry is there for MK (mask
    bit 4) and for MK2 (bit 5)."""
    pg = 'P%d' % EXTRAS_PAGE
    afm = ['h3h4%sP4,Auto Finishing Moves;' % pg, 'h3h5%sP4,Auto Finishing Moves;' % pg]
    lst = ['h3H%s%sO[%d],Move List,Off,On;' % (MASK_PLUS, pg, LIST_BIT),
           'h%s%sO[%d],Move List,Off,On;' % (MASK_PLUS, pg, LIST_BIT)]
    return afm, lst


def osd_lines():
    """CONF_STR lines of the Finishing Moves page (P4: the Character and its moves)
    and the I line (the Extras page's lines for it are extras_lines()).
    Plus has the page of Mortal Kombat II
    (mask bit 5 is set for it too; its added moves and fighters are not on it).
    Mortal Kombat Plus (its own Move List pages, tools/tunit_mkplus.py) has the
    Finishing Moves page of Mortal Kombat: the page's line is there for MK (mask
    bit 4) and for MK2 (bit 5).
    Mortal Kombat II rev 4.0 (mask bits 5 and 7) and Plus (bits 5 and 15) have a Character
    option of their own (15 and 17 fighters, alphabetical; fm_pick() gives each its line:
    the twelve stock fighters keep theirs, the hidden ones follow) and share the move lines."""
    out = []
    out.append('P4-;')
    for game, pre, sel in (('mk', 'h4H' + CLASS_MASK[0], SEL_MK), ('mkp', 'h4h' + CLASS_MASK[0], SEL_MK),
                           ('mk2', 'h5H%sH%s' % (MASK_REV4, MASK_PLUS), SEL_MK2),
                           ('rev4', 'h5h' + MASK_REV4, SEL_MK2), ('plus', 'h5h' + MASK_PLUS, SEL_PLUS)):
        names = ','.join(n for n, _ in option_order(game))
        out.append('%sP4O[%d:%d],Character,%s;' % (pre, sel[0], sel[1], names))
    out.append('P4-;')
    masks = class_masks()
    for game in ('mk', 'mkp'):
        # a line (same slot, same text) that several fighters have is one line for them;
        # a fighter sees its lines by type, then alphabetically (sorting all the lines
        # by that key sorts each fighter's)
        have, nm = {}, {}
        for li, (name, cid, moves) in enumerate(fighters(game)):
            for slot, (mname, kind, cmd, prog, dmin, dmax, note) in enumerate(moves):
                text = label(mname, osd_dist(dmin, dmax))
                have.setdefault((slot, text), []).append(li)
                nm[(slot, text)] = by_type((mname, kind))
        for (slot, text), lis in sorted(have.items(), key=lambda kv: (nm[kv[0]], kv[0][1], kv[0][0], min(kv[1]))):
            for v, free in fighter_cubes(lis):
                out.append('%sP4R[%d],%s;' % (sel_prefix(game, v, free), SLOT_BIT + slot, text))
    # Mortal Kombat II and rev 4.0: a line (the same slot, the same text) is one
    # line, as a few cubes, for every fighter, revision class and game that has it;
    # a fighter sees its lines by type, then alphabetically (sorting all the lines by that key
    # sorts each fighter's; a text's name and type are the same wherever it is)
    pts, key = {}, {}
    for game in MK2_GAMES:
        for li, (name, cid, moves) in enumerate(fighters(game)):
            for slot, mv in zip(slots(game, li), moves):
                lk = (slot, label(mv[0], osd_dist(mv[4], mv[5])))
                if game == 'mk2':
                    ps = [mk2_point(game, li, c) for c, m in enumerate(masks) if not m >> (li * 8 + slot) & 1]
                else:
                    ps = [mk2_point(game, li)]
                pts.setdefault(lk, set()).update(ps)
                if key.setdefault(lk, by_type(mv)) != by_type(mv):
                    raise ValueError('%s: the text %r is two types or names' % (name, lk[1]))
    dc = mk2_dont_care(len(masks))
    for (slot, text), ps in sorted(pts.items(), key=lambda kv: (key[kv[0]], kv[0][1], kv[0][0])):
        for fix, val in line_cover(ps, dc, len(text)):
            out.append('%sP4R[%d],%s;' % (cube_prefix(fix, val), SLOT_BIT + slot, text))
    out.append('P4-;')
    out.append('P4R[%d],Clear the set move;' % CLEAR_BIT)
    out.append('P4-;')
    # "Select a finishing move, and then move to the required distance": the
    # OSD cuts a text at a comma (it separates the fields), so the line breaks there
    out.append('P4-,Select a finishing move;')
    out.append('P4-,and then move to the;')
    out.append('P4-,required distance;')
    for k, m in MESSAGES:
        if ',' in m or ';' in m:
            raise ValueError('message %s: no , or ; (the I line\'s separators): %r' % (k, m))
    info = 'I,' + ','.join(m for _, m in MESSAGES) + ';'
    return out, info


# --------------------------------------------------------------------------
# Generated files
# --------------------------------------------------------------------------

GAMES = ('mk', 'mk2', 'rev4', 'mkp', 'plus')   # the games of the records
GAME_NO = {'mk': 0, 'mk2': 1, 'rev4': 2, 'mkp': 0, 'plus': 1}   # their number in the id: Mortal Kombat Plus's lines are
LINE_BASE = {'mkp': 8}                                  # Mortal Kombat's with the line's bit 3 set; Plus has the lines
                                                        # of Mortal Kombat II's twelve fighters and its own (12-16)


def tables():
    """Move records and steps: records[(game, line, slot)] and the step list."""
    steps, recs, starts = [], {}, {}
    for game in GAMES:
        g = GAME_NO[game]
        for li, (name, cid, moves) in enumerate(fighters(game)):
            if game == 'plus' and li < len(MK2_FIGHTERS):
                continue                                 # the twelve: the records of 'mk2'
            for slot, (mname, kind, cmd, prog, dmin, dmax, note) in zip(slots(game, li), moves):
                site = None
                if game in ('mk', 'mkp'):
                    if game == 'mk':
                        key = direct_prog(cid)               # every MK move is a direct finisher
                    else:
                        site, hold, tap = MKP_DIRECT[(name, mname)]
                        key = direct_prog(cid, (hold, tap))
                    s, pre = compile_direct(key)
                else:
                    key = prog
                    s, pre = compile_prog(prog)
                if key not in starts:                    # a program is stored once
                    starts[key] = len(steps)
                    steps += s
                rec = dict(char=cid, kind=kind, pre=pre, dmin=dmin, dmax=dmax, start=starts[key],
                           dvalid=0, dstart=0, site=0,
                           name='%s %s: %s' % (game.upper(), name, mname))
                d = _direct(game).get(name, {}).get(mname) if game not in ('mk', 'mkp') else None
                if site is not None:
                    # Mortal Kombat Plus: the move's own site (the fighter's id is not it for Reptile's and the Babalities)
                    rec.update(dvalid=1, dstart=starts[key], site=site)
                if d:
                    # MK2 direct finisher: its own program, started when the set has the move's sites
                    dkey = ('direct', d[1])
                    if dkey not in starts:
                        starts[dkey] = len(steps)
                        steps += compile_direct2(d[1])
                    rec.update(dvalid=1, dstart=starts[dkey], site=_mk2_site_ids(game).index(d[0][0]))
                recs[(g, li + LINE_BASE.get(game, 0), slot)] = rec
    return recs, steps


def gen_tab():
    recs, steps = tables()
    o = []
    o.append('// tunit_fmoves_tab.svh - finishing moves: records and programs')
    o.append('// Generated by tools/tunit_fmoves.py --gen; do not edit.')
    o.append('//')
    o.append('// fm_rec({game[1:0], line[4:0], slot[2:0]}): {valid, held first, kind[2:0], character[4:0],')
    o.append('//   min distance[8:0], max distance[8:0], first step[10:0]}; game 0 MK, 1 MK2 (Plus too), 2 MK2 rev 4.0')
    o.append('// fm_dir({game[1:0], line, slot}): the MK2 direct finisher of a move: {valid, site[5:0], first step[10:0]};')
    o.append('//   the program starts there when the set has the move\'s site (the MRA\'s words 48 + site), else at the combination')
    o.append('// fm_step(n): {op[2:0], arg[12:0]} (rtl/tunit_fmoves.sv)')
    o.append('//')
    o.append('// Copyright (C) 2026 Gm0rk - GPL-3.0-or-later')
    o.append('')
    o.append('function automatic [38:0] fm_rec(input [9:0] id);')
    o.append('\tcase (id)')
    for (g, li, slot), r in sorted(recs.items()):
        idv = g << 8 | li << 3 | slot
        o.append("\t\t10'h%03X: fm_rec = {1'b1, 1'b%d, 3'd%d, 5'd%d, 9'd%d, 9'd%d, 11'd%d};   // %s"
                 % (idv, r['pre'], r['kind'], r['char'], r['dmin'], r['dmax'], r['start'], r['name']))
    o.append("\t\tdefault: fm_rec = 39'd0;")
    o.append('\tendcase')
    o.append('endfunction')
    o.append('')
    o.append('function automatic [17:0] fm_dir(input [9:0] id);')
    o.append('\tcase (id)')
    for (g, li, slot), r in sorted(recs.items()):
        if r['dvalid']:
            idv = g << 8 | li << 3 | slot
            o.append("\t\t10'h%03X: fm_dir = {1'b1, 6'd%d, 11'd%d};   // %s" % (idv, r['site'], r['dstart'], r['name']))
    o.append("\t\tdefault: fm_dir = 18'd0;")
    o.append('\tendcase')
    o.append('endfunction')
    o.append('')
    o.append('// %d steps' % len(steps))
    o.append('')
    o.append('function automatic [15:0] fm_step(input [10:0] n);')
    o.append('\tcase (n)')
    for i, s in enumerate(steps):
        o.append("\t\t11'd%d: fm_step = 16'h%04X;" % (i, s))
    o.append("\t\tdefault: fm_step = 16'h0000;")
    o.append('\tendcase')
    o.append('endfunction')
    o.append('')
    o.append('// the move player\'s messages (CONF_STR I line)')
    for n, (k, m) in enumerate(MESSAGES[:N_FM_MESSAGES]):
        o.append("localparam [4:0] MSG_%s = 5'd%d;" % (k, n + 1))
    return '\n'.join(o) + '\n'


def gen_osd():
    lines, info = osd_lines()
    afm, lst = extras_lines()
    o = []
    o.append('// tunit_fmoves_osd.svh - the Extras page\'s Auto Finishing Moves entry and Move List option (MK, MK2, MK2 Plus),')
    o.append('// the Finishing Moves page, the Character option\'s line numbers, the info messages')
    o.append('// Generated by tools/tunit_fmoves.py --gen; do not edit.')
    o.append('//')
    o.append('// Copyright (C) 2026 Gm0rk - GPL-3.0-or-later')
    o.append('')
    for name, ls in (('FMOVES_AFM', afm), ('FMOVES_LIST', lst)):
        o.append('`define %s \\' % name)
        for l in ls:
            o.append('\t"%s", \\' % sv_str(l))
        o[-1] = o[-1].rstrip(' \\').rstrip(',')
        o.append('')
    o.append('`define FMOVES_OSD \\')
    for l in lines:
        o.append('\t"%s", \\' % sv_str(l))
    o[-1] = o[-1].rstrip(' \\').rstrip(',')
    o.append('')
    o.append('`define CORE_INFO "%s"' % sv_str(info))
    o.append('')
    o.append('// The Character option of rev 4.0 (g = 1) and Plus (g = 2) lists its fighters alphabetically; each one\'s line is')
    o.append('// his number in the page\'s lines (the fighters of Mortal Kombat II keep theirs, the hidden ones follow). The')
    o.append('// others: the option is the line.')
    o.append('function automatic [4:0] fm_pick(input [1:0] g, input [4:0] opt);')
    o.append('\tcase ({g, opt})')
    for g, game in ((1, 'rev4'), (2, 'plus')):
        for opt, (name, li) in enumerate(option_order(game)):
            if opt != li:
                o.append("\t\t{2'd%d, 5'd%d}: fm_pick = 5'd%d;   // %s" % (g, opt, li, name))
    o.append('\t\tdefault: fm_pick = opt;')
    o.append('\tendcase')
    o.append('endfunction')
    o.append('')
    o.append('// message numbers (the I line\'s fields)')
    for n, (k, m) in enumerate(MESSAGES):
        o.append("localparam [4:0] MSG_%s = 5'd%d;" % (k, n + 1))
    return '\n'.join(o) + '\n'


# Distances in words (the Move List window, the game pages). The move
# windows are pixels between the fighters (object word 9); in MAME 0.289,
# from FINISH HIM states, fighters stand no closer than 62 (MK2), a sweep
# (B+LK) still hits the dizzy opponent at 116 (MK2 Liu Kang, MK 5.0 Johnny
# Cage) / 120 (MK2 Sub-Zero) and misses at 120 / 124, and a forward jump
# covers about 160 (MK2) / 166 (MK). The zones: Close up to 79 (touching to
# a step away), Sweep 80-127 (a sweep's reach), Jump 128-199 (beyond the
# sweep, within about a jump), Half screen 200-259, Full screen 260 or more.
DIST_ZONES = [(0, 'Close'), (80, 'Sweep'), (128, 'Jump'), (200, 'Half screen'), (260, 'Full screen')]
DIST_REACH = 8                   # a window names a zone it reaches this far into


DIST_NAMED = {(164, 220): 'Half Screen'}       # Reptile's Tongue (the window is the game's)


def dist(dmin, dmax):
    """A move's distance window in words: its zone, 'A to b', 'A or farther'
    or 'Anywhere'."""
    if (dmin, dmax) in DIST_NAMED:
        return DIST_NAMED[(dmin, dmax)]
    def zone(x):
        return max(k for k, (edge, _) in enumerate(DIST_ZONES) if x >= edge)
    lo = zone(dmin)
    if dmax >= FAR:
        if lo == 0:
            return 'Anywhere'
        return DIST_ZONES[lo][1] + ('' if lo == len(DIST_ZONES) - 1 else ' or farther')
    hi = max(lo, zone(dmax - DIST_REACH))
    if hi == lo:
        return DIST_ZONES[lo][1]
    return DIST_ZONES[lo][1] + ' to ' + DIST_ZONES[hi][1].lower()


def docs(game):
    """The move table of a game's page (docs/MortalKombat.md, docs/MortalKombatII.md)."""
    o = []
    o.append('| Fighter | Move | Command | Distance |')
    o.append('|---|---|---|---|')
    for name, cid, moves in sorted(fighters(game)[len(MK2_FIGHTERS):] if game == 'plus' else fighters(game),
                                   key=lambda f: f[0].lower()):          # (alphabetical: the page's order)
        moves = sorted((m for m in moves if m[1] != K_DEAD), key=by_type)
        for n, (mname, kind, cmd, prog, dmin, dmax, note) in enumerate(moves):
            c = cmd + (', ' + note if note else '')
            o.append('| %s | %s | %s | %s |' % (name if n == 0 else '', mname, c, dist(dmin, dmax)))
    o.append('')
    if game == 'plus':
        mname, kind, cmd, prog, dmin, dmax, note = MK2_DEADPOOL
        o.append('Jade, Noob Saibot and Smoke also have the Dead Pool: %s, %s.' % (cmd, dist(dmin, dmax).lower()))
    elif game not in ('mk', 'mkp'):
        mname, kind, cmd, prog, dmin, dmax, note = MK2_DEADPOOL
        o.append('Every fighter also has the Dead Pool: %s, %s.' % (cmd, dist(dmin, dmax).lower()))
    return '\n'.join(o)


def docs_moves(game):
    """The Move List table of a game's page."""
    o = ['| Fighter | Move | Command |', '|---|---|---|']
    for name, moves in specials(game):
        first, head = True, ''
        for mname, cmd in moves:
            if cmd is None:
                head = mname.rstrip(':') + ' '
                continue
            note = SPECIAL_NOTES.get((game, name, mname))
            o.append('| %s | %s | %s |' % (name if first else '', head + mname,
                                           cmd + (', ' + note if note else '')))
            first = False
    return '\n'.join(o)


def main():
    a = sys.argv[1:]
    if a and a[0] == '--gen':
        tab, osd = gen_tab(), gen_osd()
        open(os.path.join(ROOT, 'rtl', 'tunit_fmoves_tab.svh'), 'w').write(tab)
        open(os.path.join(ROOT, 'rtl', 'tunit_fmoves_osd.svh'), 'w').write(osd)
        lines, info = osd_lines()
        n = sum(len(l) for l in lines) + len(info) + sum(len(l) for ls in extras_lines() for l in ls)
        print('OSD page %d bytes, %d lines; %d steps' % (n, len(lines), len(tables()[1])))
    elif len(a) == 2 and a[0] == '--docs' and a[1] in GAMES:
        print(docs(a[1]))
    elif len(a) == 2 and a[0] == '--moves' and a[1] in ('mk', 'mk2'):
        print(docs_moves(a[1]))
    elif len(a) == 2:
        r, notes = addresses(int(a[0]), open(a[1], 'rb').read())
        for n in notes:
            print(n)
        if r:
            for k, v in r.items():
                print('%-7s %08X' % (k, v))
        lv = level_word(open(a[1], 'rb').read())
        if lv is not None:
            print('%-7s %08X' % ('level', lv))
            dp = demo_pc(open(a[1], 'rb').read())
            if dp is not None:
                print('%-7s %08X' % ('demo', dp))
    else:
        print(__doc__)


if __name__ == '__main__':
    main()

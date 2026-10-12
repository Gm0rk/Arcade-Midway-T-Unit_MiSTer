#!/usr/bin/env python3
"""
tunit_fmoves.py - finishing moves and move lists for Mortal Kombat and
Mortal Kombat II

    python3 tools/tunit_fmoves.py <game id> <maincpu.bin>   addresses of a set
    python3 tools/tunit_fmoves.py --gen                     write the tables
    python3 tools/tunit_fmoves.py --docs mk|mk2             a game page's finishing moves
    python3 tools/tunit_fmoves.py --moves mk|mk2            a game page's move list

The OSD's "Finishing Moves" page picks a character and one of its moves;
rtl/tunit_fmoves.sv plays it on the winner's controls at the next FINISH
HIM it fits. The "Move List" option shows the fighters' moves in a window
(MK: List 1, List 2; MK2: a fighter). This script holds the move list and makes from it:

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
the move player follows the fight by watching the CPU's writes to them.

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

Move program tokens (also the MAME harness's): "U D F B" tap a direction
(F / B toward / away from the opponent), "HP LP HK LK BL" tap a button,
"[X" press and hold, "]X" let go, "wN" wait N frames, "|" wait until the
loser is dizzy, the finisher stands and the distance fits (moves start
here unless they hold a button first), "<N" walk forward to distance N.
Taps are 3 frames down, 3 up.

Copyright (C) 2026 Gm0rk - GPL-3.0-or-later
"""

import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tunit_secrets import Prog, X, G_MK, G_MKTURBO, G_MK2   # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# --------------------------------------------------------------------------
# Moves
# --------------------------------------------------------------------------

# kinds (rtl/tunit_fmoves.sv): what the stage must be and what "taken" is
K_FATAL, K_FRIEND, K_BABY, K_STAGE, K_PIT2, K_DEAD, K_MKPIT = range(7)
FAR = 511                        # no upper distance limit

# (osd name, kind, OSD command, program, min distance, max distance, note)
# note: a second line under the item
MK2_FIGHTERS = [  # select screen order: (name, character id, moves)
    ("Liu Kang", 1, [
        ("Dragon", K_FATAL, "D F B B HK", "[BL D F B B ]BL HK", 0, 108, None),
        ("Cartwheel", K_FATAL, "D F U B D", "[BL D F U B ]BL D", 0, 196, None),
        ("Friendship", K_FRIEND, "F B B B LK", "[BL F B B B ]BL LK", 0, FAR, None),
        ("Babality", K_BABY, "D D F B LK", "[BL D D F B ]BL LK", 0, FAR, None),
        ("Pit / Spikes", K_STAGE, "B F F LK", "[BL B F F ]BL LK", 0, 70, None)]),
    ("Kung Lao", 0, [
        ("Hat Throw", K_FATAL, "(LP) B F", "[BL [LP w50 | B F ]BL ]LP", 260, FAR, None),
        ("Decapitation", K_FATAL, "F F F LK", "[BL F F F ]BL LK", 100, 124, None),
        ("Friendship", K_FRIEND, "B B B D HK", "[BL B B B D ]BL HK", 0, FAR, None),
        ("Babality", K_BABY, "B B F F HK", "[BL B B F F ]BL HK", 0, FAR, None),
        ("Pit / Spikes", K_STAGE, "F F F HP", "[BL F F F ]BL HP", 0, 70, None)]),
    ("Johnny Cage", 2, [
        ("Torso Rip", K_FATAL, "D D F F LP", "[BL D D F F ]BL LP", 0, 68, None),
        ("Decapitation", K_FATAL, "F F D U", "[BL F F D ]BL U", 0, 70, None),
        ("Friendship", K_FRIEND, "D D D D HK", "[BL D D D D ]BL HK", 0, FAR, None),
        ("Babality", K_BABY, "B B B HK", "[BL B B B ]BL HK", 0, FAR, None),
        ("Pit / Spikes", K_STAGE, "D D D HK", "[BL D D D ]BL HK", 0, 70, None)]),
    ("Reptile", 9, [
        ("Tongue", K_FATAL, "B B D LP", "[BL B B D ]BL LP", 164, 220, None),
        ("Slice", K_FATAL, "U U D HP", "[BL U U D ]BL HP w20 [BL F F D ]BL HK", 0, 68, "then F F D HK"),
        ("Friendship", K_FRIEND, "B B D LK", "[BL B B D ]BL LK", 0, FAR, None),
        ("Babality", K_BABY, "D B B LK", "[BL D B B ]BL LK", 0, FAR, None),
        ("Pit / Spikes", K_STAGE, "D F F BL", "[BL D F F ]BL BL", 0, 70, None)]),
    ("Sub-Zero", 8, [
        ("Deep Freeze", K_FATAL, "F F D HK", "[BL F F D ]BL HK w30 <66 [BL F D F F ]BL HP", 116, 188, "then F D F F HP"),
        ("Ice Grenade", K_FATAL, "(LP) B B D F", "[BL [LP w50 | B B D F ]BL ]LP", 260, FAR, None),
        ("Friendship", K_FRIEND, "B B D HK", "[BL B B D ]BL HK", 0, FAR, None),
        ("Babality", K_BABY, "D B B HK", "[BL D B B ]BL HK", 0, FAR, None),
        ("Pit / Spikes", K_STAGE, "D F F BL", "[BL D F F ]BL BL", 0, 70, None)]),
    ("Shang Tsung", 6, [
        ("Soul Drain", K_FATAL, "U D U LK", "[BL U D U ]BL LK", 0, 78, None),
        ("Spikes", K_FATAL, "(HK 1 s)", "[BL [HK w50 | ]BL w6 ]HK", 84, 116, None),
        ("Friendship", K_FRIEND, "B B D F HK", "[BL B B D F ]BL HK", 0, FAR, None),
        ("Babality", K_BABY, "B F D HK", "[BL B F D ]BL HK", 0, FAR, None),
        ("Pit", K_PIT2, "D D U D", "[BL D D U ]BL D", 0, 70, None)]),
    ("Kitana", 4, [
        ("Fan Decap", K_FATAL, "BL BL BL HK", "BL BL BL HK", 0, 70, None),
        ("Kiss of Death", K_FATAL, "(LK) F F D F", "[BL [LK w60 | F F D F ]BL ]LK", 0, 68, None),
        ("Friendship", K_FRIEND, "D D D U LK", "[BL D D D U ]BL LK", 0, FAR, None),
        ("Babality", K_BABY, "D D D LK", "[BL D D D ]BL LK", 0, FAR, None),
        ("Pit / Spikes", K_STAGE, "F D F HK", "[BL F D F ]BL HK", 0, 70, None)]),
    ("Jax", 11, [
        ("Arm Rip", K_FATAL, "BL BL BL BL LP", "BL BL BL BL LP", 72, 124, None),
        ("Head Smash", K_FATAL, "(LP) F F F", "[BL [LP w66 | F F F ]BL ]LP", 0, 80, None),
        ("Friendship", K_FRIEND, "D D U U LK", "[BL D D U U ]BL LK", 0, FAR, None),
        ("Babality", K_BABY, "D U D U LK", "[BL D U D U ]BL LK", 0, FAR, None),
        ("Pit / Spikes", K_STAGE, "U U D LK", "[BL U U D ]BL LK", 0, 70, None)]),
    ("Mileena", 5, [
        ("Sai Stab", K_FATAL, "F B F LP", "[BL F B F ]BL LP", 0, 74, None),
        ("Inhale", K_FATAL, "(HK 2 s)", "[BL [HK w130 | ]BL w6 ]HK", 0, 68, None),
        ("Friendship", K_FRIEND, "D D D U HK", "[BL D D D U ]BL HK", 0, FAR, None),
        ("Babality", K_BABY, "D D D HK", "[BL D D D ]BL HK", 0, FAR, None),
        ("Pit / Spikes", K_STAGE, "F D F LK", "[BL F D F ]BL LK", 0, 70, None)]),
    ("Baraka", 3, [
        ("Decapitation", K_FATAL, "B B B B HP", "[BL B B B B ]BL HP", 0, 96, None),
        ("Impale", K_FATAL, "B F D F LP", "[BL B F D F ]BL LP", 0, 132, None),
        ("Friendship", K_FRIEND, "U F F HK", "[BL U F F ]BL HK", 0, FAR, None),
        ("Babality", K_BABY, "F F F HK", "[BL F F F ]BL HK", 0, FAR, None),
        ("Pit / Spikes", K_STAGE, "F F D HK", "[BL F F D ]BL HK", 0, 70, None)]),
    ("Scorpion", 10, [
        ("Toasty", K_FATAL, "D D U U HP", "[BL D D U U ]BL HP", 0, FAR, None),
        ("Torch", K_FATAL, "U U HP", "[BL U U ]BL HP", 148, 172, None),
        ("Slice", K_FATAL, "(HP) D F F F", "[BL [HP w42 | D F F F ]BL ]HP", 0, 68, None),
        ("Friendship", K_FRIEND, "B B D HK", "[BL B B D ]BL HK", 0, FAR, None),
        ("Babality", K_BABY, "D B B HK", "[BL D B B ]BL HK", 0, FAR, None),
        ("Pit / Spikes", K_STAGE, "D F F BL", "[BL D F F ]BL BL", 0, 70, None)]),
    ("Raiden", 7, [
        ("Electrocution", K_FATAL, "(LK 2 s)", "[BL [LK w130 | ]BL w6 ]LK", 0, 64, None),
        ("Friendship", K_FRIEND, "D B F HK", "[BL D B F ]BL HK", 164, FAR, None),
        ("Babality", K_BABY, "D D U HK", "[BL D D U ]BL HK", 0, FAR, None),
        ("Pit / Spikes", K_STAGE, "U U HP", "[BL U U ]BL HP", 0, 70, None)]),
]
MK2_DEADPOOL = ("Dead Pool", K_DEAD, "D+LP+LK HP", "[BL [D w4 [LP [LK w6 ]BL HP ]D ]LP ]LK", 0, 76, None)

MK_FIGHTERS = [  # select screen order
    ("Johnny Cage", 0, [("Decapitation", K_FATAL, "F F F HP", "[BL F F F ]BL HP", 0, 60, None)]),
    ("Kano", 1, [("Heart Rip", K_FATAL, "B D F LP", "[BL B D F ]BL LP", 0, 84, None)]),
    ("Sub-Zero", 5, [("Spine Rip", K_FATAL, "F D F HP", "[BL F D F ]BL HP", 0, 84, None)]),
    ("Sonya", 6, [("Kiss of Death", K_FATAL, "F F B B BL", "[BL F F B B ]BL BL", 0, FAR, None)]),
    ("Raiden", 2, [("Electrocution", K_FATAL, "F B B B HP", "[BL F B B B ]BL HP", 80, 124, None)]),
    ("Liu Kang", 3, [("Cartwheel", K_FATAL, "D B U F D", "[BL D B U F ]BL D", 0, FAR, None)]),
    ("Scorpion", 4, [("Fire Breath", K_FATAL, "(BL) U U", "[BL U U ]BL", 120, 144, None)]),
]
MK_PIT = ("The Pit", K_MKPIT, "D+HP", "[D w8 HP w8 ]D", 24, 64, None)

# Fatalities the move player leaves out (the button must be held from before
# FINISH HIM), for the Move List window: (fighter, after this move, (name,
# command, note, min distance, max distance)). From the release handlers
# (MK2 L3.1, table FF863020): Shang Tsung's LP release FF863CA0 (LP held at
# least 3C0h frames, state 3, distance 50h-78h), Raiden's HP release
# FF863750 (HP held at least 180h frames, state 3, start with A1 = 52h).
# Not played in MAME.
WINDOW_EXTRA = {
    'mk2': [('Shang Tsung', 'Spikes', ('Kintaro', '(LP 18 s)', 'held from before FINISH HIM', 80, 120)),
            ('Raiden', 'Electrocution', ('Super Uppercut', '(HP 7 s)', 'held from before FINISH HIM', 0, 82))],
}

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
# notes for the game pages (docs/), keyed by (game, fighter, move)
SPECIAL_NOTES = {
    ('mk', 'Sonya', 'Ring Toss'): 'quickly (all within about 0.4 s)',
    ('mk2', 'Kung Lao', 'Hat Throw'): 'Up / Down steer the hat',
    ('mk2', 'Raiden', 'Electric Grab'): 'close to the opponent',
    ('mk2', 'Jax', 'Back Breaker'): 'next to an opponent in the air',
    ('mk2', 'Scorpion', 'Air Throw'): 'next to an opponent in the air',
}


def specials(game):
    """(fighter name, [(move, command)]) in the order of the Character option
    (and of the Move List window's pages)."""
    f, s = (MK2_FIGHTERS, MK2_SPECIALS) if game == 'mk2' else (MK_FIGHTERS, MK_SPECIALS)
    return [(n, m) for (n, _, _), m in zip(f, s)]


def fighters(game):
    """(name, id, moves) per OSD line, with the stage moves every fighter
    has."""
    if game == 'mk2':
        return [(n, c, m + [MK2_DEADPOOL]) for n, c, m in MK2_FIGHTERS]
    return [(n, c, m + [MK_PIT]) for n, c, m in MK_FIGHTERS]


# --------------------------------------------------------------------------
# Programs
# --------------------------------------------------------------------------

KEYS = {'U': 0, 'D': 1, 'F': 2, 'B': 3, 'HP': 4, 'LP': 5, 'HK': 6, 'LK': 7, 'BL': 8}
OP_END, OP_TAP, OP_PRESS, OP_RELEASE, OP_WAIT, OP_READY, OP_WALK = range(7)


def compile_prog(prog):
    """Program text to 16-bit steps: {op[15:13], arg[12:0]}; a tap's arg is
    {length - 1 [12:9], keys [8:0]}. Returns (steps, held first): held first
    when the move holds a button before its ready point."""
    toks = prog.split()
    if '|' not in toks:
        toks = ['|'] + toks
    steps = []
    pre = toks.index('|') > 0
    for t in toks:
        c = t[0]
        if c == '|':
            steps.append(OP_READY << 13)
        elif c == 'w':
            steps.append(OP_WAIT << 13 | int(t[1:]))
        elif c == '<':
            steps.append(OP_WALK << 13 | int(t[1:]))
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
    return steps, pre


# --------------------------------------------------------------------------
# Per-set RAM addresses (ROM index 1, words 0x200-0x227)
# --------------------------------------------------------------------------

CFG_BASE = 0x200
CFG_WORDS = 40
FORMAT = 1

# Moves a revision does not have, by MAME set name: (fighter or '*', move).
# Checked in MAME: played as on L3.1, the move is not taken. The Dead Pool's
# check is not there before L3.0; L2.x has Shang Tsung's friendship as
# B B D B HK and another Pit; L1.x lacks most friendships, babalities and
# stage moves.
MISSING = {
    'mk2r11': [('*', 'Friendship'), ('*', 'Babality'), ('*', 'Pit / Spikes'), ('*', 'Dead Pool'),
               ('Shang Tsung', 'Pit'), ('Liu Kang', 'Cartwheel'), ('Kung Lao', 'Hat Throw'),
               ('Johnny Cage', 'Decapitation'), ('Reptile', 'Slice'), ('Sub-Zero', 'Deep Freeze'),
               ('Sub-Zero', 'Ice Grenade'), ('Shang Tsung', 'Soul Drain'), ('Shang Tsung', 'Spikes'),
               ('Kitana', 'Fan Decap'), ('Kitana', 'Kiss of Death'), ('Jax', 'Arm Rip'),
               ('Mileena', 'Inhale'), ('Scorpion', 'Toasty'), ('Scorpion', 'Slice'),
               ('Raiden', 'Electrocution')],
    'mk2r14': [('*', 'Pit / Spikes'), ('*', 'Dead Pool'), ('Shang Tsung', 'Pit'),
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
               ('Scorpion', 'Slice')],
    'mk2r20': [('*', 'Dead Pool'), ('Kung Lao', 'Friendship'), ('Shang Tsung', 'Friendship'),
               ('Shang Tsung', 'Pit')],
    'mk2r21': [('*', 'Dead Pool'), ('Kung Lao', 'Friendship'), ('Shang Tsung', 'Friendship'),
               ('Shang Tsung', 'Pit')],
}


def a32(p, i):
    return p.u32(i)


def stance(p, notes):
    """Where a fighter's process resumes in its stance loop (both games):
    MOVI 1,A0 / CALLA sleep / CALLR / JRC / CALLR / BTST 3,A0 / JRNE / BTST 2,A0."""
    h = p.find([0x09C0, 0x0001, 0x0D5F, X, X, 0x0D3F, X, 0xC800, X, 0x0D3F, X, 0x1F80, 0xCB00, X, 0x1FA0])
    if len(h) != 1:
        notes.append('stance loop not found')
        return None
    return 0xFF800000 + (h[0] + 5) * 16


def mk2_addresses(p, notes):
    r = {}
    # finish routine: MOVE @P2 char,A0 / MOVE @P1 char,A1 / MOVI 0Ch,A2 /
    # CALLA / JREQ / MOVI 0Dh,A2 ... MOVK 3,A0 / MOVE A0,@state
    h = p.find([0x05A0, X, X, 0x05A1, X, X, 0x09C2, 0x000C, 0x0D5F, X, X, X, 0x09C2, 0x000D])
    if len(h) != 1:
        notes.append('finish routine not found')
        return None
    i = h[0]
    r['p2c'], r['p1c'] = a32(p, i + 1), a32(p, i + 4)
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


def missing_mask(gid, setname):
    """Bit line * 8 + slot set for each move of the OSD the set lacks."""
    game = 'mk2' if gid == G_MK2 else 'mk'
    m = 0
    gone = MISSING.get(setname, [])
    for line, (name, cid, moves) in enumerate(fighters(game)):
        for slot, mv in enumerate(moves):
            if (name, mv[0]) in gone or ('*', mv[0]) in gone:
                m |= 1 << (line * 8 + slot)
    return m


def build(gid, prog_bytes, setname=None):
    """ROM index 1 words 0x200 on (bytes) and notes; empty if the set has no
    finishing moves.

    Words: 0 format, 1 reserved, then word addresses (bit address >> 4, low
    word first) of the round state, P1 and P2 character, energy, object
    pointer and process pointer, the stage and the finish flag (2-23); the
    dizzy codes 1 and 2 and the stance code (24-29, 32-bit values); x and
    resume-address offsets in words (30: {resume[15:8], x[7:0]}); the moves
    the set lacks (32-39: bit line * 8 + slot of the OSD's moves)."""
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
    if gone:
        notes.append('%d moves not in this revision' % bin(gone).count('1'))
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
    ('MKPIT', "Stage move: The Pit only"),
    ('OVER', "FINISH HIM is over: the move\nwaits for the next one"),
    ('NOT_TAKEN', "Move not taken"),
    ('NOT_TAKEN_FB', "Not taken: a Friendship or\nBabality needs a round won\nwithout punches"),
    ('CLEARED', "Finishing move cleared"),
    ('NOT_HERE', "Not available in this\nrevision of the game"),
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
]

N_FM_MESSAGES = 13             # the move player's (rtl/tunit_fmoves.sv)

# OSD status bits (top level)
SEL_MK2 = (27, 24)               # O[27:24] fighter, MK2
SEL_MK = (30, 28)                # O[30:28] fighter, MK
SLOT_BIT = 32                    # R[32] + line: the fighter's moves
LIST_SEL = (64, 61)              # O[64:61] Move List: Off, then a window page (tools/tunit_window.py)
CLEAR_BIT = 40                   # R[40]: clear the set move
MASK_SEL = 8                     # status_menumask bits 8-11: the page's fighter


def sv_str(s):
    return s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')


def sel_prefix(game, li):
    """Hide prefixes that show a line only for the game (menu mask bit 4 MK,
    5 MK2) and fighter li (bits 8-11 = the Character option; MK's bit 11 is
    always 0, so its lines test bits 8-10 only)."""
    pre = 'h' + ('5' if game == 'mk2' else '4')
    for b in range(4 if game == 'mk2' else 3):
        pre += ('h' if li >> b & 1 else 'H') + '0123456789ABCDEF'[MASK_SEL + b]
    return pre


def label(name, cmd):
    s = '%-12s %s' % (name, cmd) if cmd else name
    if len(s) > 27 or ',' in s or ';' in s:
        raise ValueError('label too long or with , / ;: ' + s)
    return s


def osd_lines():
    """CONF_STR lines of the main menu's Move List option (Off or the window
    page to show, rtl/tunit_window.sv: MK List 1 / List 2, several fighters
    to a page; MK2 a fighter), the Finishing Moves page (P4: the Character
    and its moves) and the I line."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import tunit_window
    mk_lists = ','.join('List %d' % (k + 1) for k in range(tunit_window.page_counts()['mk']))
    out = []
    out.append('h4O[%d:%d],Move List,Off,%s;' % (LIST_SEL[0], LIST_SEL[1], mk_lists))
    out.append('h5O[%d:%d],Move List,Off,%s;' % (LIST_SEL[0], LIST_SEL[1],
                                                ','.join(n for n, _, _ in fighters('mk2'))))
    out.append('h3P4,Finishing Moves;')
    out.append('P4-;')
    for game, bit, sel in (('mk', '4', SEL_MK), ('mk2', '5', SEL_MK2)):
        names = ','.join(n for n, _, _ in fighters(game))
        out.append('h%sP4O[%d:%d],Character,%s;' % (bit, sel[0], sel[1], names))
    out.append('P4-;')
    for game in ('mk', 'mk2'):
        for li, (name, cid, moves) in enumerate(fighters(game)):
            pre = sel_prefix(game, li)
            for slot, (mname, kind, cmd, prog, dmin, dmax, note) in enumerate(moves):
                out.append('%sP4R[%d],%s;' % (pre, SLOT_BIT + slot, label(mname, cmd)))
                if note:
                    out.append('%sP4-,%s%s;' % (pre, ' ' * 12, note))
    out.append('P4-;')
    out.append('P4R[%d],Clear the set move;' % CLEAR_BIT)
    out.append('P4-;')
    out.append('P4-,The move plays at the;')
    out.append('P4-,winner\'s FINISH HIM;')
    out.append('h3-;')
    info = 'I,' + ','.join(m for _, m in MESSAGES) + ';'
    return out, info


# --------------------------------------------------------------------------
# Generated files
# --------------------------------------------------------------------------

def tables():
    """Move records and steps: records[(game, line, slot)] and the step list."""
    steps, recs = [], {}
    for g, game in enumerate(('mk', 'mk2')):
        for li, (name, cid, moves) in enumerate(fighters(game)):
            for slot, (mname, kind, cmd, prog, dmin, dmax, note) in enumerate(moves):
                s, pre = compile_prog(prog)
                recs[(g, li, slot)] = dict(char=cid, kind=kind, pre=pre, dmin=dmin, dmax=dmax,
                                           start=len(steps), name='%s %s: %s' % (game.upper(), name, mname))
                steps += s
    return recs, steps


def gen_tab():
    recs, steps = tables()
    o = []
    o.append('// tunit_fmoves_tab.svh - finishing moves: records and programs')
    o.append('// Generated by tools/tunit_fmoves.py --gen; do not edit.')
    o.append('//')
    o.append('// fm_rec({game, line, slot}): {valid, held first, kind[2:0], character[3:0],')
    o.append('//   min distance[8:0], max distance[8:0], first step[9:0]}; game 0 MK, 1 MK2')
    o.append('// fm_step(n): {op[2:0], arg[12:0]} (rtl/tunit_fmoves.sv)')
    o.append('//')
    o.append('// Copyright (C) 2026 Gm0rk - GPL-3.0-or-later')
    o.append('')
    o.append('function automatic [36:0] fm_rec(input [7:0] id);')
    o.append('\tcase (id)')
    for (g, li, slot), r in sorted(recs.items()):
        idv = g << 7 | li << 3 | slot
        o.append("\t\t8'h%02X: fm_rec = {1'b1, 1'b%d, 3'd%d, 4'd%d, 9'd%d, 9'd%d, 10'd%d};   // %s"
                 % (idv, r['pre'], r['kind'], r['char'], r['dmin'], r['dmax'], r['start'], r['name']))
    o.append("\t\tdefault: fm_rec = 37'd0;")
    o.append('\tendcase')
    o.append('endfunction')
    o.append('')
    o.append('// %d steps' % len(steps))
    o.append('')
    o.append('function automatic [15:0] fm_step(input [9:0] n);')
    o.append('\tcase (n)')
    for i, s in enumerate(steps):
        o.append("\t\t10'd%d: fm_step = 16'h%04X;" % (i, s))
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
    o = []
    o.append('// tunit_fmoves_osd.svh - the Move List option, the Finishing Moves page,')
    o.append('// the info messages')
    o.append('// Generated by tools/tunit_fmoves.py --gen; do not edit.')
    o.append('//')
    o.append('// Copyright (C) 2026 Gm0rk - GPL-3.0-or-later')
    o.append('')
    o.append('`define FMOVES_OSD \\')
    for l in lines:
        o.append('\t"%s", \\' % sv_str(l))
    o[-1] = o[-1].rstrip(' \\').rstrip(',')
    o.append('')
    o.append('`define CORE_INFO "%s"' % sv_str(info))
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


def dist(dmin, dmax):
    """A move's distance window in words: its zone, 'A to b', 'A or farther'
    or 'Anywhere'."""
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
    for name, cid, moves in fighters(game):
        moves = [m for m in moves if m[1] not in (K_DEAD, K_MKPIT)]
        for n, (mname, kind, cmd, prog, dmin, dmax, note) in enumerate(moves):
            c = cmd + (', ' + note if note else '')
            o.append('| %s | %s | %s | %s |' % (name if n == 0 else '', mname, c, dist(dmin, dmax)))
    o.append('')
    mname, kind, cmd, prog, dmin, dmax, note = MK2_DEADPOOL if game == 'mk2' else MK_PIT
    o.append('Every fighter also has %s: %s, %s.' % ('the Dead Pool' if game == 'mk2' else 'The Pit', cmd,
                                                     dist(dmin, dmax).lower()))
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
        open(os.path.join(ROOT, 'rtl', 'tunit_fmoves_tab.svh'), 'w').write(gen_tab())
        open(os.path.join(ROOT, 'rtl', 'tunit_fmoves_osd.svh'), 'w').write(gen_osd())
        lines, info = osd_lines()
        n = sum(len(l) for l in lines) + len(info)
        print('OSD page %d bytes, %d lines; %d steps' % (n, len(lines), len(tables()[1])))
    elif len(a) == 2 and a[0] == '--docs' and a[1] in ('mk', 'mk2'):
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
    else:
        print(__doc__)


if __name__ == '__main__':
    main()

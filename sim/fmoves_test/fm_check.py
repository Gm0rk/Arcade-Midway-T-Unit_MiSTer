#!/usr/bin/env python3
"""
fm_check.py - checks the finishing-move player (rtl/tunit_fmoves.sv)

    make && python3 fm_check.py

Builds fight situations from CPU writes (made-up addresses, the real codes)
and runs them through obj_dir/fm_tb:

  - every move of MK and MK2, P1 the winner at a distance in the move's
    window: the controls the player presses, frame by frame, against the
    move's program timed the way the MAME harness that checked the moves
    times it (taps 3 frames down and 3 up, holds, waits, the ready point),
    with Forward / Back turned into Right / Left; then the game takes it
    (finish flag) and nothing more happens
  - P2 the winner, facing left
  - the messages: set outside FINISH HIM, another fighter's FINISH HIM, the
    wrong stage, too far then stepping in, FINISH HIM over before it
    started, not taken (a Friendship: the hint), cleared, a move the
    revision lacks

Copyright (C) 2026 Gm0rk - GPL-3.0-or-later
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'tools'))
import tunit_fmoves as T   # noqa: E402

TB = os.path.join(HERE, 'obj_dir', 'fm_tb')

# made-up word addresses of the fight variables; pointers are bit addresses
VARS = ['state', 'p1c', 'p2c', 'p1e', 'p2e', 'p1o', 'p2o', 'p1p', 'p2p', 'stage', 'flag']
ADDR = {k: 0x10000 + 0x10 * n for n, k in enumerate(VARS)}
OBJ = {1: 0x20000, 2: 0x20100}            # word addresses of the objects
PROC = {1: 0x20200, 2: 0x20300}           # and processes
XOFF, ROFF = 9, 14
DIZZY1, DIZZY2, STANCE, BUSY = 0xFF8C27C0, 0xFFA17E10, 0xFF82F270, 0xFF83C3D0
MSG = {k: n + 1 for n, (k, _) in enumerate(T.MESSAGES)}
KEYBIT = {'U': 0, 'D': 1, 'L': 2, 'R': 3, 'HP': 4, 'LP': 5, 'HK': 6, 'LK': 7, 'BL': 8}


class Script:
    def __init__(self, game):
        self.l = ['g %d %d' % (game == 'mk', game == 'mk2'), 's', 'c 0 1']
        for n, k in enumerate(VARS):
            self.l.append('c %d %x' % (2 + 2 * n, ADDR[k] & 0xFFFF))
            self.l.append('c %d %x' % (3 + 2 * n, ADDR[k] >> 16))
        for n, v in enumerate((DIZZY1, DIZZY2, STANCE)):
            self.l.append('c %d %x' % (24 + 2 * n, v & 0xFFFF))
            self.l.append('c %d %x' % (25 + 2 * n, v >> 16))
        self.l.append('c 30 %x' % (ROFF << 8 | XOFF))

    def w(self, a, v):
        self.l.append('w %x %x' % (a, v & 0xFFFF))

    def w32(self, a, v):
        self.w(a, v & 0xFFFF)
        self.w(a + 1, v >> 16)

    def var(self, k, v):
        self.w(ADDR[k], v)

    def fight(self, c1, c2, x1, x2, stage, r1=STANCE, r2=DIZZY2):
        self.var('state', 0)
        self.var('flag', 0)
        self.var('stage', stage)
        self.var('p1c', c1)
        self.var('p2c', c2)
        self.var('p1e', 0xA1)
        self.var('p2e', 0xA1)
        for p in (1, 2):
            self.w32(ADDR['p%do' % p], OBJ[p] << 4)
            self.w32(ADDR['p%dp' % p], PROC[p] << 4)
        self.x(x1, x2)
        self.w32(PROC[1] + ROFF, r1)
        self.w32(PROC[2] + ROFF, r2)

    def x(self, x1, x2):
        self.w(OBJ[1] + XOFF, x1)
        self.w(OBJ[2] + XOFF, x2)

    def finish(self, loser):
        self.var('p%de' % loser, 0)
        self.var('state', 3)

    def pick(self, line, slot):
        self.l.append('p %d %d' % (line, slot))

    def frames(self, n):
        self.l.append('f %d' % n)

    def run(self):
        out = subprocess.run([TB], input='\n'.join(self.l) + '\n', capture_output=True, text=True).stdout
        frames, msgs = [], []
        for line in out.splitlines():
            t = line.split()
            if t[0] == 'F':
                frames.append((int(t[2]), int(t[3], 16)))
            elif t[0] == 'M':
                msgs.append((int(t[1]), int(t[2])))
        return frames, msgs


def model(prog, fwd='R'):
    """The move's controls per frame as the MAME harness plays them, from
    its first step (the ready point passed at once): a list of key masks."""
    toks = prog.split()
    if '|' not in toks:
        toks = ['|'] + toks
    back = 'L' if fwd == 'R' else 'R'
    keyname = {'F': fwd, 'B': back}
    on = {}                       # frame -> keys set by taps
    held_at = []                  # (frame, key, down)
    f = 0
    for t in toks:
        c = t[0]
        if c == '|':
            f += 2
        elif c == 'w':
            f += int(t[1:])
        elif c == '<':
            raise ValueError('walk')
        elif c == '[':
            held_at.append((f, keyname.get(t[1:], t[1:]), True))
            f += 1
        elif c == ']':
            held_at.append((f, keyname.get(t[1:], t[1:]), False))
            f += 3
        else:
            keys, _, n = t.partition('*')
            n = int(n) if n else 3
            m = 0
            for k in keys.split('+'):
                m |= 1 << KEYBIT[keyname.get(k, k)]
            for k in range(f, f + n):
                on[k] = on.get(k, 0) | m
            f += n + 3
    out = []
    held = 0
    for k in range(f + 1):
        for (hf, key, down) in held_at:
            if hf == k:
                held = held | 1 << KEYBIT[key] if down else held & ~(1 << KEYBIT[key])
        out.append(held | on.get(k, 0))
    return out


def strip(seq):
    while seq and seq[0] == 0:
        seq = seq[1:]
    while seq and seq[-1] == 0:
        seq = seq[:-1]
    return seq


fails = 0


def check(cond, what):
    global fails
    if not cond:
        fails += 1
        print('FAIL', what)
    return cond


STAGE_FOR = {T.K_STAGE: 6, T.K_PIT2: 6, T.K_DEAD: 0, T.K_MKPIT: 3}


def stage_of(kind):
    return STAGE_FOR.get(kind, 2)


def distance_in(dmin, dmax):
    if dmax >= T.FAR:
        return min(dmin + 20, 300) if dmin else 100
    return (dmin + dmax) // 2


def other_char(cid):
    return 0 if cid != 0 else 1


def test_move(game, line, slot, mv, cid, p2_wins=False):
    name, kind, cmd, prog, dmin, dmax, note = mv
    s = Script(game)
    d = distance_in(dmin, dmax)
    walk = '<' in prog
    if p2_wins:
        s.fight(other_char(cid), cid, 500, 500 + d, stage_of(kind), r1=DIZZY1, r2=STANCE)
    else:
        s.fight(cid, other_char(cid), 500, 500 + d, stage_of(kind))
    s.pick(line, slot)
    s.frames(2)
    s.finish(1 if p2_wins else 2)
    if walk:
        # the finisher closes in during the walk: P1 steps to the walk's target
        n = int([t for t in prog.split() if t[0] == '<'][0][1:])
        s.frames(60)
        s.x(500 + n - 5, 500 + d)
        s.frames(80)
    else:
        s.frames(len(model(prog)) + 20)
    frames, msgs = s.run()
    tag = '%s %s: %s%s' % (game, T.fighters(game)[line][0], name, ' (P2)' if p2_wins else '')
    ok = check([m for f, m in msgs if f == 0] == [MSG['SET']], tag + ' set message %s' % msgs)
    who = 2 if p2_wins else 1
    got = strip([k if dr == who else 0 for dr, k in frames])
    if not walk:
        exp = strip(model(prog, 'L' if p2_wins else 'R'))
        ok &= check(got == exp, tag + ' controls\n  got %s\n  exp %s' % (got, exp))
    else:
        ok &= check(len(got) > 20, tag + ' walk move played')
    # the game takes it: no more messages, the controls let go
    s.var('flag', 1)
    s.frames(250)
    frames, msgs = s.run()
    ok &= check(not [m for f, m in msgs if f > 0], tag + ' messages after taken %s' % msgs)
    ok &= check(frames[-1][0] == 0, tag + ' controls let go')
    return ok


def test_moves():
    n = 0
    for game in ('mk', 'mk2'):
        for line, (fname, cid, moves) in enumerate(T.fighters(game)):
            for slot, mv in enumerate(moves):
                test_move(game, line, slot, mv, cid)
                n += 1
    # P2 winning (facing left), a few
    for game, line, slot in (('mk2', 0, 0), ('mk2', 0, 1), ('mk2', 6, 1), ('mk', 5, 0), ('mk2', 4, 0)):
        fname, cid, moves = T.fighters(game)[line]
        test_move(game, line, slot, moves[slot], cid, p2_wins=True)
        n += 1
    print('%d moves played' % n)


def msgs_of(s):
    return [m for f, m in s.run()[1]]


def test_messages():
    LK = 0                                       # MK2 Liu Kang, line 0
    # another fighter's FINISH HIM
    s = Script('mk2')
    s.fight(0, 9, 500, 560, 2)
    s.finish(2)
    s.frames(2)
    s.pick(LK, 0)
    s.frames(100)
    fr, m = s.run()
    check([x for f, x in m] == [MSG['NOT_THIS']], 'not this fighter %s' % m)
    check(all(d == 0 for d, k in fr), 'not this fighter: no controls')
    # the stage: Pit / Spikes on the Dead Pool, then the Dead Pool move on a Pit
    s = Script('mk2')
    s.fight(1, 9, 500, 530, 0)
    s.pick(LK, 4)
    s.frames(2)
    s.finish(2)
    s.frames(50)
    check(msgs_of(s) == [MSG['SET'], MSG['STAGE']], 'stage message')
    s = Script('mk2')
    s.fight(1, 9, 500, 530, 6)
    s.pick(LK, 5)
    s.frames(2)
    s.finish(2)
    s.frames(50)
    check(msgs_of(s) == [MSG['SET'], MSG['DEAD']], 'Dead Pool message')
    s = Script('mk')
    s.fight(3, 5, 500, 530, 0)
    s.pick(5, 1)                                 # MK Liu Kang (line 5), The Pit
    s.frames(2)
    s.finish(2)
    s.frames(50)
    check(msgs_of(s) == [MSG['SET'], MSG['MKPIT']], 'MK Pit message')
    # too far, then the player steps in: the move plays
    s = Script('mk2')
    s.fight(1, 9, 500, 700, 2)
    s.pick(LK, 0)                                # Dragon, up to 104
    s.frames(2)
    s.finish(2)
    s.frames(40)
    s.x(600, 700)
    s.frames(100)
    fr, m = s.run()
    check([x for f, x in m] == [MSG['SET'], MSG['FAR']], 'too far message %s' % m)
    check(any(d == 1 for d, k in fr[42:]) and not any(d for d, k in fr[:42]), 'plays after stepping in')
    # too close for Kung Lao's Decapitation (104-120)
    s = Script('mk2')
    s.fight(0, 9, 500, 530, 2)
    s.pick(1, 1)
    s.frames(2)
    s.finish(2)
    s.frames(40)
    check(msgs_of(s) == [MSG['SET'], MSG['CLOSE']], 'too close message')
    # a held-button move out of the window holds nothing
    s = Script('mk2')
    s.fight(0, 9, 500, 530, 2)
    s.pick(1, 0)                                 # Hat Throw, 264 or more
    s.frames(2)
    s.finish(2)
    s.frames(60)
    fr, m = s.run()
    check([x for f, x in m] == [MSG['SET'], MSG['CLOSE']] and not any(d for d, k in fr),
          'held-button move waits %s' % m)
    # FINISH HIM over before the loser was dizzy: the move stays set
    s = Script('mk2')
    s.fight(1, 9, 500, 560, 2, r2=BUSY)
    s.pick(LK, 0)
    s.frames(2)
    s.finish(2)
    s.frames(30)
    s.var('state', 1)
    s.frames(10)
    s.w32(PROC[2] + ROFF, DIZZY2)
    s.var('p2e', 0xA1)
    s.var('state', 0)
    s.frames(10)
    s.finish(2)
    s.frames(100)
    fr, m = s.run()
    check([x for f, x in m] == [MSG['SET'], MSG['OVER']], 'over message %s' % m)
    check(any(d == 1 for d, k in fr[45:]), 'still set for the next FINISH HIM')
    # not taken: a Friendship gives the hint
    s = Script('mk2')
    s.fight(1, 9, 500, 560, 2)
    s.pick(LK, 2)
    s.frames(2)
    s.finish(2)
    s.frames(300)
    check(msgs_of(s) == [MSG['SET'], MSG['NOT_TAKEN_FB']], 'not taken (friendship)')
    s = Script('mk2')
    s.fight(1, 9, 500, 560, 2)
    s.pick(LK, 0)
    s.frames(2)
    s.finish(2)
    s.frames(300)
    check(msgs_of(s) == [MSG['SET'], MSG['NOT_TAKEN']], 'not taken')
    # cleared
    s = Script('mk2')
    s.fight(1, 9, 500, 560, 2)
    s.pick(LK, 0)
    s.frames(2)
    s.pick(LK, 15)
    s.frames(2)
    s.finish(2)
    s.frames(100)
    fr, m = s.run()
    check([x for f, x in m] == [MSG['SET'], MSG['CLEARED']] and not any(d for d, k in fr), 'cleared %s' % m)
    # picked at the fighter's own FINISH HIM: no message, it plays
    s = Script('mk2')
    s.fight(1, 9, 500, 560, 2)
    s.finish(2)
    s.frames(2)
    s.pick(LK, 0)
    s.frames(80)
    fr, m = s.run()
    check(not m and any(d == 1 for d, k in fr), 'picked at FINISH HIM %s' % m)
    # no set addresses (an older MRA): nothing at all
    s = Script('mk2')
    s.l[2] = 'c 0 0'
    s.fight(1, 9, 500, 560, 2)
    s.pick(LK, 0)
    s.frames(2)
    s.finish(2)
    s.frames(80)
    fr, m = s.run()
    check(not m and not any(d for d, k in fr), 'no addresses: nothing')
    # a move the revision lacks: said, nothing set
    s = Script('mk2')
    s.l.append('c 32 %x' % (1 << 2))              # line 0 (Liu Kang), slot 2 (Friendship)
    s.fight(1, 9, 500, 560, 2)
    s.pick(LK, 2)
    s.frames(2)
    s.finish(2)
    s.frames(80)
    fr, m = s.run()
    check([x for f, x in m] == [MSG['NOT_HERE']] and not any(d for d, k in fr), 'not in this revision %s' % m)
    # the loser getting up, the finisher recovering: it waits
    s = Script('mk2')
    s.fight(1, 9, 500, 560, 2, r1=BUSY, r2=BUSY)
    s.pick(LK, 0)
    s.frames(2)
    s.finish(2)
    s.frames(30)
    s.w32(PROC[2] + ROFF, DIZZY1)
    s.frames(30)
    s.w32(PROC[1] + ROFF, STANCE)
    s.frames(60)
    fr, m = s.run()
    check(not any(d for d, k in fr[:62]) and any(d for d, k in fr[62:]), 'waits for dizzy and stance')
    print('messages checked')


if __name__ == '__main__':
    test_moves()
    test_messages()
    print('FAILED %d' % fails if fails else 'all passed')
    sys.exit(1 if fails else 0)

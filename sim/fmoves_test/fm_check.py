#!/usr/bin/env python3
"""
fm_check.py - checks the finishing-move player (rtl/tunit_fmoves.sv)

    make && python3 fm_check.py

Builds fight situations from CPU writes (made-up addresses, the real codes)
and runs them through obj_dir/fm_tb:

  - every move of MK, MK2 and MK2 rev 4.0, P1 the winner at a distance in the move's
    window: the controls the player presses, frame by frame, against the
    move's program timed the way the MAME harness that checked the moves
    times it (taps 3 frames down and 3 up, holds, waits, the ready point),
    with Forward / Back turned into Right / Left; then the game takes it
    (finish flag) and nothing more happens
  - P2 the winner, facing left
  - Mortal Kombat's fatalities, all direct finishers: the patch (fp_en, fp_addr)
    is on only while the direct program plays, the controls are the one tap
    the fighter's handler runs on (Block held for Scorpion), repeated until the
    finish flag, then nothing; not taken, all the taps and a message; a fighter
    without a jump in the MRA's table plays nothing and is not taken
  - Mortal Kombat II's direct finishers (the stock revisions, Plus, and rev 4.0 with
    its own table): every move that has one, with the sites of the set at made-up
    addresses (the global ones in a second 1 Mbit window: words 82-84): the controls
    the program presses, the patch at the move's site (the next one for a two-stage
    move) with the polarity the set gives, taken, not taken, a set without the
    move's sites (the combination, no patch), a set with no sites (L1.x: never a
    patch), P2, too far, the wrong stage, FINISH HIM over
  - the messages: set outside FINISH HIM, another fighter's FINISH HIM, the
    wrong stage (MK2's Dead Pool, Pit, Spikes), too far then stepping in, FINISH HIM over before it
    started, not taken (a Friendship: the hint; rev 4.0's stage fatality),
    cleared
  - with FM_ROMS=<directory of <set>_rom0.bin files> (tools/mra_check.py --out): the real
    configuration words of Mortal Kombat II Plus (Beta 1, Beta 2) and rev 4.0, built from
    their program ROMs, with the real fight variables and dizzy codes: every direct
    finisher's patch is at the site the program ROM has (the second window included)
    and the polarity of the jump there

Copyright (C) 2026 Gm0rk - GPL-3.0-or-later
"""

import os
import struct
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


DADDR = {c: 0xABC000 + 0x20 * c for c in range(7)}       # made-up word addresses of the handlers' jumps (MK)
MADDR = {n: 0xABD000 + 0x20 * n for n in range(40)}      # MK2's sites by site id
SITE_IDS = {g: T._mk2_site_ids(g) for g in ('mk2', 'rev4')}
# the sites whose jump is a JRC (the patch sets bit 8): Scorpion's Toasty and Reptile's Slice, its second stage,
# and the hold-time sites (the jump after the CMPI of the hold: tunit_mk2sites.HOLD_REF for L3.1 and the Plus sets, REV4_HOLD)
import tunit_mk2sites as MS   # noqa: E402
_JRC = {'mk2': {0xFF868CC0, 0xFF86A380} | {a for a, _ in MS.HOLD_REF},
        'rev4': {0xFF8C05B0, 0xFF8C28F0} | set(MS.REV4_HOLD)}
MPOL = {g: tuple(n for n, a in enumerate(SITE_IDS[g]) if a in _JRC[g]) for g in ('mk2', 'rev4')}
# the sites in the second window (words 91-94): the stage fatality (Plus Beta 2), the Babality (rev 4.0)
MALT = {'mk2': (SITE_IDS['mk2'].index(T.S_STG),), 'rev4': (SITE_IDS['rev4'].index(T.R4_BAB),)}
ALTBASE = 0xBBD000


def mkp_addr(n):
    """The made-up word address of a Mortal Kombat Plus site (0-6 the fatalities', 7 and 8 the Babalities')."""
    return DADDR[n] if n < 7 else ALTBASE + 0x20 * n


def maddr(game, n):
    """The made-up word address of a game's site id."""
    return ALTBASE + 0x20 * n if n in MALT[game] else MADDR[n]


class Script:
    def __init__(self, game, dvalid=0x7F, msites=None, blob=None):
        """dvalid: MK, the characters that have a jump; msites: MK2, the site ids the
        set has (None: none, the moves keep their combinations)."""
        self.l = ['g %d %d %d %d' % (game in ('mk', 'mkp'), game in ('mk2', 'rev4', 'plus'), game == 'rev4', game == 'mkp'), 's', 'c 0 2']
        if blob is not None:                  # the real configuration words of a set
            self.l += ['c %d %x' % (n, v) for n, v in enumerate(struct.unpack('<%dH' % (len(blob) // 2), blob))]
            return
        if game in ('mk', 'mkp'):
            self.l.append('c 47 %x' % (DADDR[0] >> 16))
            for c in range(7):
                self.l.append('c %d %x' % (48 + c, DADDR[c] & 0xFFFF if dvalid >> c & 1 else 0))
            if game == 'mkp':                  # Mortal Kombat Plus: the Babality sites 7 and 8, in the second window
                for n in (T.BAB_HK, T.BAB_LK):
                    self.l.append('c %d %x' % (48 + n, mkp_addr(n) & 0xFFFF))
                self.l.append('c %d %x' % (T.ALT_HI_WORD, ALTBASE >> 16))
                self.l.append('c %d %x' % (T.ALT_WORD, 1 << T.BAB_HK | 1 << T.BAB_LK))
        if msites is not None:
            g = 'rev4' if game == 'rev4' else 'mk2'
            self.l.append('c 47 %x' % (MADDR[0] >> 16))
            for n in range(T.MAX_SITES):
                self.l.append('c %d %x' % (T.SITE_WORD + n, maddr(g, n) & 0xFFFF if n in msites else 0))
            for k in range(3):
                self.l.append('c %d %x' % (T.POL_WORD + k, sum(1 << (n - 16 * k) for n in MPOL[g] if n // 16 == k)))
            self.l.append('c %d %x' % (T.ALT_HI_WORD, ALTBASE >> 16))
            for k in range(3):
                self.l.append('c %d %x' % (T.ALT_WORD + k, sum(1 << (n - 16 * k) for n in MALT[g] if n // 16 == k)))
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
        frames, msgs, self.patch = [], [], []
        for line in out.splitlines():
            t = line.split()
            if t[0] == 'F':
                frames.append((int(t[2]), int(t[3], 16)))
                self.patch.append((int(t[4]), int(t[5], 16), int(t[6])))
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
        elif t == 'S2':
            f += 1                    # the DIRECT step: the patch moves to the move's next site
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


STAGE_FOR = {T.K_STAGE: 6, T.K_PIT2: 6, T.K_DEAD: 0, T.K_STAGE4: 9}   # rev 4.0's stage move: any stage


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
    for game in ('mk2', 'plus', 'rev4'):         # MK's fatalities are direct finishers (test_direct)
        for line, (fname, cid, moves) in enumerate(T.fighters(game)):
            if game == 'plus' and line < len(T.MK2_FIGHTERS):
                continue                         # (Plus's twelve are MK2's lines)
            for slot, mv in zip(T.slots(game, line), moves):
                test_move(game, line, slot, mv, cid)
                n += 1
    # P2 winning (facing left), a few
    for game, line, idx in (('mk2', 0, 0), ('mk2', 0, 1), ('mk2', 6, 1), ('mk2', 4, 0)):
        fname, cid, moves = T.fighters(game)[line]
        test_move(game, line, T.slots(game, line)[idx], moves[idx], cid, p2_wins=True)
        n += 1
    print('%d moves played' % n)


def tap_starts(got, key):
    """Frames where `key` (a key bit) goes down in the controls `got`."""
    return [k for k in range(len(got)) if got[k] & 1 << KEYBIT[key] and (k == 0 or not got[k - 1] & 1 << KEYBIT[key])]


def direct_setup(cid, line, p2_wins=False, dvalid=0x7F, dist=None):
    fname, _, moves = T.fighters('mk')[line]
    name, kind, cmd, prog, dmin, dmax, note = moves[0]
    d = distance_in(dmin, dmax) if dist is None else dist
    s = Script('mk', dvalid=dvalid)
    if p2_wins:
        s.fight(other_char(cid), cid, 500, 500 + d, 2, r1=DIZZY1, r2=STANCE)
    else:
        s.fight(cid, other_char(cid), 500, 500 + d, 2)
    s.pick(line, 0)
    s.frames(2)
    s.finish(1 if p2_wins else 2)
    return s, prog


def test_direct():
    n = 0
    for line, (fname, cid, moves) in enumerate(T.fighters('mk')):
        who = 1
        tag = 'direct MK %s' % fname
        hold, key = T.MK_DIRECT[cid]
        kb = 1 << KEYBIT[key]
        dprog = T.direct_prog(cid)
        # not taken: five taps, the patch on only while they play, then the message
        s, prog = direct_setup(cid, line)
        s.frames(len(model(dprog)) + 20)
        frames, msgs = s.run()
        got = strip([k if dr == who else 0 for dr, k in frames])
        check(got == strip(model(dprog)), tag + ' controls\n  got %s\n  exp %s' % (got, strip(model(dprog))))
        check(len(tap_starts(got, key)) == T.DIRECT_TRIES, tag + ' %d taps' % T.DIRECT_TRIES)
        on = [k for k, (e, a, _) in enumerate(s.patch) if e]
        check(on and all(s.patch[k][1] == DADDR[cid] for k in on), tag + ' patch address')
        check(on and on == list(range(on[0], on[-1] + 1)), tag + ' patch on in one run')
        dr = [k for k, (d_, kk) in enumerate(frames) if d_ == who]
        check(on and dr and on[0] > dr[0], tag + ' patch on after the controls are taken')
        tapf = [k for k, (d_, kk) in enumerate(frames) if d_ == who and kk & kb]
        starts = [k for k in tapf if k - 1 not in tapf]
        check(len(starts) == T.DIRECT_TRIES, tag + ' tap frames')
        check(on and on[0] < starts[0] and on[-1] >= tapf[-1], tag + ' patch covers the taps')
        check(not s.patch[-1][0], tag + ' patch off at the end')
        s.frames(250)
        frames, msgs = s.run()
        check([m for f, m in msgs] == [MSG['SET'], MSG['NOT_TAKEN']], tag + ' not taken message %s' % msgs)
        check(frames[-1][0] == 0 and not s.patch[-1][0], tag + ' controls and patch let go')
        # taken a frame after the first tap went up / the second: that many taps, then nothing
        for taps in (1, 2):
            s2, _ = direct_setup(cid, line)
            s2.frames(starts[taps - 1] + 4 - 2)
            s2.var('flag', 1)
            s2.frames(120)
            frames, msgs = s2.run()
            got2 = strip([k if dr_ == who else 0 for dr_, k in frames])
            check(len(tap_starts(got2, key)) == taps, tag + ' taken after tap %d: %d taps, got %s' % (taps, taps, got2))
            on2 = [k for k, (e, a, _) in enumerate(s2.patch) if e]
            check(on2 and on2[-1] <= starts[taps - 1] + 12, tag + ' patch off soon after it is taken (%s)' % on2[-3:])
            check(not [m for f, m in msgs if f > 0], tag + ' no message after taken %s' % msgs)
            check(frames[-1][0] == 0 and frames[-1][1] == 0, tag + ' controls let go')
        # no jump in the MRA's table for this fighter: nothing is played, no patch, not taken
        s, prog = direct_setup(cid, line, dvalid=0x7F & ~(1 << cid))
        s.frames(300)
        frames, msgs = s.run()
        check(not any(k for dr_, k in frames), tag + ' no jump: no keys pressed')
        check(not any(e for e, a, _ in s.patch), tag + ' no jump: no patch')
        check([m for f, m in msgs] == [MSG['SET'], MSG['NOT_TAKEN']], tag + ' no jump: not taken message %s' % msgs)
        # P2 the winner
        s, prog = direct_setup(cid, line, p2_wins=True)
        s.frames(len(model(dprog)) + 20)
        frames, msgs = s.run()
        got = strip([k if dr_ == 2 else 0 for dr_, k in frames])
        check(got == strip(model(dprog, 'L')), tag + ' P2 controls')
        check(not any(dr_ == 1 for dr_, k in frames), tag + ' P2: P1 untouched')
        check(any(e for e, a, _ in s.patch), tag + ' P2: patch on')
        # too far: no controls and no patch until the player steps in
        if moves[0][5] < T.FAR:
            s, prog = direct_setup(cid, line, dist=moves[0][5] + 300)
            s.frames(40)
            frames, msgs = s.run()
            check(not any(dr_ for dr_, k in frames) and not any(e for e, a, _ in s.patch), tag + ' too far: nothing')
            check([m for f, m in msgs] == [MSG['SET'], MSG['FAR']], tag + ' too far: message %s' % msgs)
            s.x(500, 500 + (moves[0][4] + moves[0][5]) // 2)
            s.frames(len(model(dprog)) + 30)
            frames, msgs = s.run()
            check(any(e for e, a, _ in s.patch) and any(dr_ == 1 for dr_, k in frames[40:]), tag + ' too far, then in range: plays')
        # FINISH HIM over while it plays (not taken): the patch off at once
        s, prog = direct_setup(cid, line)
        s.frames(starts[0] + 2 - 2)
        s.var('state', 1)
        s.frames(10)
        frames, msgs = s.run()
        check(not s.patch[-1][0] and frames[-1][0] == 0, tag + ' FINISH HIM over: patch off, controls let go')
        n += 1
    # MK on The Pit's stage: a fatality is still a direct finisher (MK has one fatality per fighter)
    s, prog = direct_setup(1, 1)
    s.var('stage', 3)
    s.frames(60)
    frames, msgs = s.run()
    check(any(e for e, a, _ in s.patch) and any(dr_ for dr_, k in frames), 'MK, The Pit stage: the fatality plays')
    print('%d direct finishers checked' % n)


def direct2_setup(game, line, idx, ids, p2_wins=False, dist=None, stage=None):
    """idx: the move's index in the fighter's list (the OSD slot is T.slots(game, line)[idx])."""
    fname, cid, moves = T.fighters(game)[line]
    name, kind, cmd, prog, dmin, dmax, note = moves[idx]
    slot = T.slots(game, line)[idx]
    d = distance_in(dmin, dmax) if dist is None else dist
    st = stage_of(kind) if stage is None else stage
    s = Script(game, msites=ids)
    if p2_wins:
        s.fight(other_char(cid), cid, 500, 500 + d, st, r1=DIZZY1, r2=STANCE)
    else:
        s.fight(cid, other_char(cid), 500, 500 + d, st)
    s.pick(line, slot)
    s.frames(2)
    s.finish(1 if p2_wins else 2)
    return s


def patch_runs(s):
    """The patch's on-runs: [(first frame, last frame, {(address, set)})]."""
    runs = []
    for k, (e, a, v) in enumerate(s.patch):
        if e:
            if runs and runs[-1][1] == k - 1:
                runs[-1][1] = k
                runs[-1][2].append((a, v))
            else:
                runs.append([k, k, [(a, v)]])
    return runs


def test_direct2(game):
    """Mortal Kombat II's direct finishers (game: 'mk2' the stock revisions and Plus, 'rev4'), every move that has one, with all the sites of the set."""
    n = 0
    ids_all = SITE_IDS[game]
    every = set(range(len(ids_all)))
    for line, (fname, cid, moves) in enumerate(T.fighters(game)):
        for slot, mv in enumerate(moves):
            d = T._direct(game).get(fname, {}).get(mv[0])
            if not d:
                continue
            sites, dprog = d
            ids = [ids_all.index(a) for a in sites]
            tag = 'direct %s %s: %s' % (game.upper(), fname, mv[0])
            kind = mv[1]
            walk = '<' in dprog
            keep = dprog.startswith('KEEP ')
            toks = dprog.split()
            if keep:
                toks = toks[1:]
            taps = [t for t in toks if t[0] not in 'w[]<' and t != 'S2']
            btaps = [t for t in taps if t in ('HP', 'LP', 'HK', 'LK', 'BL')]
            rels = [t[1:] for t in toks if t[0] == ']']
            # the last button tapped, else the key held and let go last (a hold gate, a hold with directions typed inside), else the last direction
            key = btaps[-1] if btaps and not keep else rels[-1] if rels else taps[-1]
            if keep:
                dprog = ' '.join(toks)
            # not taken: the program, the patch at the site (the next one after S2), the message
            s = direct2_setup(game, line, slot, every)
            if walk:
                wn = int([t for t in toks if t[0] == '<'][0][1:])
                s.frames(130)
                dd = distance_in(mv[4], mv[5])
                s.x(500 + dd - wn + 5, 500 + dd)             # P1 closes in: the separation is under the walk's target
                s.frames(90)
            else:
                s.frames(len(model(dprog)) + 25)
            frames, msgs = s.run()
            got = strip([k if dr == 1 else 0 for dr, k in frames])
            if not walk:
                exp = strip(model(dprog))
                check(got == exp, tag + ' controls\n  got %s\n  exp %s' % (got, exp))
            else:
                check(any(k & 1 << KEYBIT['R'] for k in got), tag + ' walks')
            check(len(tap_starts(got, key)) >= 1, tag + ' taps %s' % key)
            runs = patch_runs(s)
            check(len(runs) == 1, tag + ' patch on in one run %s' % [(r[0], r[1]) for r in runs])
            if runs:
                seq = []
                for a_, v_ in runs[0][2]:
                    if not seq or seq[-1] != (a_, v_):
                        seq.append((a_, v_))
                exp_seq = [(maddr(game, i), int(i in MPOL[game])) for i in ids]
                check(seq == exp_seq, tag + ' patch sites %s, expected %s' % (seq, exp_seq))
                dr = [k for k, (d_, kk) in enumerate(frames) if d_ == 1]
                check(dr and runs[0][0] > dr[0], tag + ' patch on after the controls are taken')
                check(not s.patch[-1][0], tag + ' patch off at the end')
            s.frames(250)
            frames, msgs = s.run()
            want = MSG['NOT_TAKEN_FB'] if kind in (T.K_FRIEND, T.K_BABY) else MSG['STAGE4'] if kind == T.K_STAGE4 else MSG['NOT_TAKEN']
            check([m for f, m in msgs] == [MSG['SET'], want], tag + ' not taken message %s' % msgs)
            check(frames[-1][0] == 0 and not s.patch[-1][0], tag + ' controls and patch let go')
            # the game takes it a few frames into the program: nothing more, the patch off soon
            if not walk:
                s = direct2_setup(game, line, slot, every)
                s.frames(len(model(dprog)) // 2)
                s.var('flag', 1)
                s.frames(max(150, len(model(dprog)) - len(model(dprog)) // 2 + 30))      # (a KEEP program plays on to its end: Raiden's Lift 297 frames)
                frames, msgs = s.run()
                runs = patch_runs(s)
                check(frames[-1][0] == 0 and frames[-1][1] == 0, tag + ' taken: controls let go')
                check(not s.patch[-1][0], tag + ' taken: patch off')
                check(not [m for f, m in msgs if f > 0], tag + ' taken: no message %s' % msgs)
                if runs:
                    check(runs[-1][1] <= len(model(dprog)) // 2 + 12, tag + ' taken: patch off soon (%s)' % runs[-1][:2])
            # a set without the move's sites: the combination, no patch
            s = direct2_setup(game, line, slot, every - set(ids))
            s.frames(len(model(mv[3])) + 20 if '<' not in mv[3] else 200)
            frames, msgs = s.run()
            check(not any(e for e, a_, v_ in s.patch), tag + ' no site: no patch')
            check(any(k for dr, k in frames), tag + ' no site: the combination plays')
            n += 1
    # a set without any site (L1.x: the MRA has no sites): never a patch, the combination
    for line, ids in ((0, None), (5, None)):
        fname, cid, moves = T.fighters(game)[line]
        s = Script(game, msites=ids)
        mv = moves[0]
        s.fight(cid, other_char(cid), 500, 500 + distance_in(mv[4], mv[5]), stage_of(mv[1]))
        s.pick(line, T.slots(game, line)[0])
        s.frames(2)
        s.finish(2)
        s.frames(200)
        frames, msgs = s.run()
        check(not any(e for e, a_, v_ in s.patch) and any(dr_ for dr_, k in frames), '%s line %d: no patch, the combination' % (game, line))
    # P2 the winner, a tap, a hold and a two-stage move
    for fname, mvname in ((('Liu Kang', 'Dragon'), ('Kung Lao', 'Hat Throw'), ('Reptile', 'Slice'), ('Raiden', 'Friendship')) if game == 'mk2' else
                          (('Liu Kang', 'Dragon'), ('Kung Lao', 'Hat Decap'), ('Reptile', 'Invisible Slice'), ('Raiden', 'Babality'))):
        line = [f_[0] for f_ in T.fighters(game)].index(fname)
        moves = T.fighters(game)[line][2]
        slot = [m[0] for m in moves].index(mvname)
        dprog = T._direct(game)[fname][mvname][1]
        s = direct2_setup(game, line, slot, every, p2_wins=True)
        s.frames(len(model(dprog)) + 25)
        frames, msgs = s.run()
        got = strip([k if dr_ == 2 else 0 for dr_, k in frames])
        check(got == strip(model(dprog, 'L')), 'direct %s P2 %s %s: controls' % (game.upper(), fname, mvname))
        check(not any(dr_ == 1 for dr_, k in frames) and any(e for e, a_, v_ in s.patch), 'direct %s P2 %s %s: P1 untouched, patch on' % (game.upper(), fname, mvname))
    if game == 'mk2':
        # too far: nothing until the player steps in; the stage's check (Pit on the wrong stage); FINISH HIM over
        line = 0
        s = direct2_setup('mk2', line, 0, every, dist=400)
        s.frames(40)
        frames, msgs = s.run()
        check(not any(dr_ for dr_, k in frames) and not any(e for e, a_, v_ in s.patch), 'direct MK2 too far: nothing')
        check([m for f, m in msgs] == [MSG['SET'], MSG['FAR']], 'direct MK2 too far: message %s' % msgs)
        s.x(500, 540)
        s.frames(100)
        frames, msgs = s.run()
        check(any(e for e, a_, v_ in s.patch) and any(dr_ == 1 for dr_, k in frames[40:]), 'direct MK2 too far, then in range: plays')
        fi = [f[0] for f in T.fighters('mk2')].index('Liu Kang')
        slot = [m[0] for m in T.fighters('mk2')[fi][2]].index('Stage Fatality')
        s = direct2_setup('mk2', fi, slot, every, stage=2)
        s.frames(60)
        frames, msgs = s.run()
        check(not any(dr_ for dr_, k in frames) and not any(e for e, a_, v_ in s.patch), 'direct MK2 wrong stage: nothing')
        check([m for f, m in msgs] == [MSG['SET'], MSG['STAGE']], 'direct MK2 wrong stage: message %s' % msgs)
        s = direct2_setup('mk2', fi, slot, every)
        s.frames(60)
        frames, msgs = s.run()
        check(any(e for e, a_, v_ in s.patch) and any(dr_ for dr_, k in frames), 'direct MK2 stage move on the Pit: plays')
        s = direct2_setup('mk2', 0, 0, every)
        s.frames(12)
        s.var('state', 1)
        s.frames(10)
        frames, msgs = s.run()
        check(not s.patch[-1][0] and frames[-1][0] == 0, 'direct MK2 FINISH HIM over: patch off, controls let go')
    else:
        # rev 4.0: too far, then in range; its stage fatality plays on any stage; FINISH HIM over
        fi = 0
        slot = [m[0] for m in T.fighters('rev4')[fi][2]].index('Stage Fatality')
        s = direct2_setup('rev4', fi, 0, every, dist=400)
        s.frames(40)
        frames, msgs = s.run()
        check(not any(dr_ for dr_, k in frames) and not any(e for e, a_, v_ in s.patch), 'direct REV4 too far: nothing')
        s.x(500, 560)
        s.frames(100)
        frames, msgs = s.run()
        check(any(e for e, a_, v_ in s.patch) and any(dr_ == 1 for dr_, k in frames[40:]), 'direct REV4 too far, then in range: plays')
        s = direct2_setup('rev4', fi, slot, every, stage=9)
        s.frames(60)
        frames, msgs = s.run()
        check(any(e for e, a_, v_ in s.patch) and any(dr_ for dr_, k in frames), 'direct REV4 stage fatality on any stage: plays')
        s = direct2_setup('rev4', [n for n, _, _ in T.fighters('rev4')].index('Liu Kang'), 0, every)
        s.frames(12)
        s.var('state', 1)
        s.frames(10)
        frames, msgs = s.run()
        check(not s.patch[-1][0] and frames[-1][0] == 0, 'direct REV4 FINISH HIM over: patch off, controls let go')
    print('%d direct finishers checked (%s)' % (n, game))


def test_real(setname, game, rom0):
    """A set's real configuration (tools/tunit_fmoves.py build) in the player: every direct
    finisher patches the site of the program ROM, with its polarity."""
    global ADDR, XOFF, ROFF, DIZZY1, DIZZY2, STANCE
    from tunit_secrets import G_MK2
    blob, notes = T.build(G_MK2, rom0, setname)
    w = struct.unpack('<%dH' % (len(blob) // 2), blob)
    save = (ADDR, XOFF, ROFF, DIZZY1, DIZZY2, STANCE)
    ADDR = {k: w[2 + 2 * n] | w[3 + 2 * n] << 16 for n, k in enumerate(VARS)}
    DIZZY1, DIZZY2, STANCE = (w[24 + 2 * n] | w[25 + 2 * n] << 16 for n in range(3))
    XOFF, ROFF = (w[30] & 0xFF) << 0, w[30] >> 8
    ids = T._mk2_site_ids(game)
    n = 0
    try:
        for line, (fname, cid, moves) in enumerate(T.fighters(game)):
            for idx, mv in enumerate(moves):
                d = T._direct(game).get(fname, {}).get(mv[0])
                if not d:
                    continue
                s = Script(game, blob=blob)
                dd = distance_in(mv[4], mv[5])
                st = stage_of(mv[1])
                s.fight(cid, other_char(cid), 500, 500 + dd, st, r1=STANCE, r2=DIZZY2)       # (the defaults are the made-up set's)
                s.pick(line, T.slots(game, line)[idx])
                s.frames(2)
                s.finish(2)
                s.frames(250 if '<' not in d[1] else 400)
                frames, msgs = s.run()
                runs = patch_runs(s)
                tag = 'real %s %s: %s' % (setname, fname, mv[0])
                if not check(runs, tag + ' patch on'):
                    continue
                seq = []
                for a_, v_ in runs[0][2]:
                    if not seq or seq[-1] != (a_, v_):
                        seq.append((a_, v_))
                exp = []
                for a in d[0]:
                    a = T.PLUS_SITES.get(setname, {}).get(a, a)
                    op = rom0[2 * ((a - 0xFF800000) >> 4) + 1]
                    exp.append((a >> 4, 1 if op == 0xC8 else 0))
                check(seq == exp or ('<' in d[1] and seq[:1] == exp[:1]), tag + ' sites %s, program ROM %s' % (seq, exp))
                n += 1
    finally:
        ADDR, XOFF, ROFF, DIZZY1, DIZZY2, STANCE = save
    print('%d %s direct finishers on the real sites' % (n, setname))


def msgs_of(s):
    return [m for f, m in s.run()[1]]


def mslot(game, line, name):
    """The OSD slot of a fighter's move, by name (the slots are not the moves' indexes)."""
    moves = T.fighters(game)[line][2]
    return T.slots(game, line)[[m[0] for m in moves].index(name)]


def test_messages():
    LK = [n for n, _, _ in T.fighters('mk2')].index('Liu Kang')     # MK2 Liu Kang's line
    KL = [n for n, _, _ in T.fighters('mk2')].index('Kung Lao')
    # another fighter's FINISH HIM
    s = Script('mk2')
    s.fight(0, 9, 500, 560, 2)
    s.finish(2)
    s.frames(2)
    s.pick(LK, mslot('mk2', LK, 'Dragon'))
    s.frames(100)
    fr, m = s.run()
    check([x for f, x in m] == [MSG['NOT_THIS']], 'not this fighter %s' % m)
    check(all(d == 0 for d, k in fr), 'not this fighter: no controls')
    # the stage: Pit / Spikes on the Dead Pool, then the Dead Pool move on a Pit
    s = Script('mk2')
    s.fight(1, 9, 500, 530, 0)
    s.pick(LK, mslot('mk2', LK, 'Stage Fatality'))
    s.frames(2)
    s.finish(2)
    s.frames(50)
    check(msgs_of(s) == [MSG['SET'], MSG['STAGE']], 'stage message')
    s = Script('mk2')
    s.fight(1, 9, 500, 530, 6)
    s.pick(LK, mslot('mk2', LK, 'Dead Pool'))
    s.frames(2)
    s.finish(2)
    s.frames(50)
    check(msgs_of(s) == [MSG['SET'], MSG['DEAD']], 'Dead Pool message')
    # too far, then the player steps in: the move plays
    s = Script('mk2')
    s.fight(1, 9, 500, 700, 2)
    s.pick(LK, mslot('mk2', LK, 'Dragon'))        # up to 104
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
    s.pick(KL, mslot('mk2', KL, 'Decapitation'))
    s.frames(2)
    s.finish(2)
    s.frames(40)
    check(msgs_of(s) == [MSG['SET'], MSG['CLOSE']], 'too close message')
    # a held-button move out of the window holds nothing
    s = Script('mk2')
    s.fight(0, 9, 500, 530, 2)
    s.pick(KL, mslot('mk2', KL, 'Hat Throw'))    # 264 or more
    s.frames(2)
    s.finish(2)
    s.frames(60)
    fr, m = s.run()
    check([x for f, x in m] == [MSG['SET'], MSG['CLOSE']] and not any(d for d, k in fr),
          'held-button move waits %s' % m)
    # FINISH HIM over before the loser was dizzy: the move stays set
    s = Script('mk2')
    s.fight(1, 9, 500, 560, 2, r2=BUSY)
    s.pick(LK, mslot('mk2', LK, 'Dragon'))
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
    s.pick(LK, mslot('mk2', LK, 'Friendship'))
    s.frames(2)
    s.finish(2)
    s.frames(300)
    check(msgs_of(s) == [MSG['SET'], MSG['NOT_TAKEN_FB']], 'not taken (friendship)')
    s = Script('mk2')
    s.fight(1, 9, 500, 560, 2)
    s.pick(LK, mslot('mk2', LK, 'Dragon'))
    s.frames(2)
    s.finish(2)
    s.frames(300)
    check(msgs_of(s) == [MSG['SET'], MSG['NOT_TAKEN']], 'not taken')
    # cleared
    s = Script('mk2')
    s.fight(1, 9, 500, 560, 2)
    s.pick(LK, mslot('mk2', LK, 'Dragon'))
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
    s.pick(LK, mslot('mk2', LK, 'Dragon'))
    s.frames(80)
    fr, m = s.run()
    check(not m and any(d == 1 for d, k in fr), 'picked at FINISH HIM %s' % m)
    # no set addresses (an older MRA): nothing at all
    s = Script('mk2')
    s.l[2] = 'c 0 0'
    s.fight(1, 9, 500, 560, 2)
    s.pick(LK, mslot('mk2', LK, 'Dragon'))
    s.frames(2)
    s.finish(2)
    s.frames(80)
    fr, m = s.run()
    check(not m and not any(d for d, k in fr), 'no addresses: nothing')
    # rev 4.0: a stage fatality plays on any stage; not taken, it names the stages
    RLK = [n for n, _, _ in T.fighters('rev4')].index('Liu Kang')
    fname, cid, moves = T.fighters('rev4')[RLK]
    names_lk = [m[0] for m in moves]
    slot = T.slots('rev4', RLK)[names_lk.index('Stage Fatality')]
    s = Script('rev4')
    s.fight(cid, other_char(cid), 500, 530, 9)
    s.pick(RLK, slot)
    s.frames(2)
    s.finish(2)
    s.frames(300)
    check(msgs_of(s) == [MSG['SET'], MSG['STAGE4']], 'rev 4.0 stage fatality not taken %s' % msgs_of(s))
    # rev 4.0: the Dead Pool still wants its stage
    s = Script('rev4')
    s.fight(1, 9, 500, 530, 6)
    s.pick(RLK, T.slots('rev4', RLK)[names_lk.index('Dead Pool')])
    s.frames(2)
    s.finish(2)
    s.frames(50)
    check(msgs_of(s) == [MSG['SET'], MSG['DEAD']], 'rev 4.0 Dead Pool message %s' % msgs_of(s))
    # the loser getting up, the finisher recovering: it waits
    s = Script('mk2')
    s.fight(1, 9, 500, 560, 2, r1=BUSY, r2=BUSY)
    s.pick(LK, mslot('mk2', LK, 'Dragon'))
    s.frames(2)
    s.finish(2)
    s.frames(30)
    s.w32(PROC[2] + ROFF, DIZZY1)
    s.frames(30)
    s.w32(PROC[1] + ROFF, STANCE)
    s.frames(60)
    fr, m = s.run()
    check(not any(d for d, k in fr[:62]) and any(d for d, k in fr[62:]), 'waits for dizzy and stance')
    # a move the game takes while the program plays (Raiden's Electrocution: the
    # taps come after the release that starts it) plays on to its end though the
    # game leaves FINISH HIM at its start; the same without the finish flag stops
    r = [k for k, (n, c, m) in enumerate(T.fighters('mk2')) if n == 'Raiden'][0]
    rname, rcid, rmoves = T.fighters('mk2')[r]
    prog = rmoves[0][3]
    head = prog.split(' BL+LK')[0]
    check(head != prog and prog.count('BL+LK') > 10, 'Electrocution has its taps')
    for took in (True, False):
        s = Script('mk2')
        s.fight(rcid, other_char(rcid), 500, 530, 2)
        s.pick(r, mslot('mk2', r, 'Electrocution'))
        s.frames(2)
        s.finish(2)
        s.frames(len(model(head)) + 1)
        if took:
            s.var('flag', 1)
        s.var('state', 1)
        s.frames(len(model(prog)) - len(model(head)) + 300)
        fr, m = s.run()
        got = strip([k if d == 1 else 0 for d, k in fr])
        if took:
            check(got == strip(model(prog)), 'taken Electrocution plays its taps\n  got %s\n  exp %s' % (got, strip(model(prog))))
            check(not [x for f, x in m if f > 0], 'taken Electrocution: no message %s' % m)
        else:
            check(len(got) <= len(strip(model(head))) + 8, 'FINISH HIM over, not taken: the taps stop')
            check([x for f, x in m] == [MSG['SET'], MSG['NOT_TAKEN']], 'FINISH HIM over, not taken: message %s' % m)
        check(fr[-1][0] == 0, 'Electrocution: controls let go')
    print('messages checked')


def test_keep(game='mk2'):
    """Raiden's Electrocution (KEEP) and Shang Tsung's Kintaro, hold-time sites on MK2 (the jump after the CMPI of the hold):
    the program is the short hold (Block, then the key let go after 6 frames) and, for the Electrocution, the 40 Block + Low Kick
    taps that come after the take: the patch goes off at the take but the controls go on; no message; a game that
    does not take the move gets the patch for the whole program, the taps and the message."""
    ids_all = SITE_IDS[game]
    every = set(range(len(ids_all)))
    fighters = T.fighters(game)
    for fname, mvname, keepit in ((('Raiden', 'Electrocution', True), ('Shang Tsung', 'Kintaro', False)) if game == 'mk2' else
                                  (('Raiden', 'Electrocution', True), ('Raiden', 'Lift', True))):
        taps2 = ('U', 'HP') if mvname == 'Lift' else ('BL', 'LK')          # held together after the take (the Lift: Up held, HP tapped)
        line = [f_[0] for f_ in fighters].index(fname)
        moves = fighters[line][2]
        slot = [m[0] for m in moves].index(mvname)
        dprog = T._direct(game)[fname][mvname][1]
        check(dprog.startswith('KEEP ') == keepit, '%s %s: KEEP flag in the program' % (fname, mvname))
        site = T._direct(game)[fname][mvname][0][0]
        sid = ids_all.index(site)
        check(sid in MPOL[game], '%s %s: its jump is a JRC (the patch sets bit 8)' % (fname, mvname))
        toks = dprog.split()[1:] if keepit else dprog.split()
        # taken a few frames after the hold is over (the flag turns on)
        for take_at in (14, 24):
            s = direct2_setup(game, line, slot, every)
            s.frames(take_at)
            s.var('flag', 2 if keepit else 3)
            s.frames(len(model(' '.join(toks))) + 30)
            frames, msgs = s.run()
            runs = patch_runs(s)
            tag = '%s %s taken at %d' % (fname, mvname, take_at)
            check(len(runs) == 1, tag + ': patch on in one run %s' % [(r[0], r[1]) for r in runs])
            if runs:
                check(runs[0][1] <= take_at + 12, tag + ': patch off at the take (%d)' % runs[0][1])
                check({(a_, v_) for a_, v_ in runs[0][2]} == {(maddr(game, sid), 1)}, tag + ': the patch at its site, polarity 1')
            got = strip([k if dr == 1 else 0 for dr, k in frames])
            late = [k for fi, (dr, k) in enumerate(frames) if dr == 1 and fi > take_at + 6]
            blt = sum(1 for k in late if k & 1 << KEYBIT[taps2[0]] and k & 1 << KEYBIT[taps2[1]])
            if keepit:
                check(blt >= 3 * 36, tag + ': the %s + %s taps go on after the take (%d frames)' % (taps2[0], taps2[1], blt))
            else:
                check(blt == 0 and not late[-1:] or not any(late), tag + ': nothing more after the take')
            check(frames[-1][0] == 0 and frames[-1][1] == 0 and not s.patch[-1][0], tag + ': controls and patch let go at the end')
            check(not [m for f, m in msgs if f > 0], tag + ': no message %s' % msgs)
        # not taken: the patch for the program, the whole program, then the message
        s = direct2_setup(game, line, slot, every)
        s.frames(len(model(' '.join(toks))) + 250)
        frames, msgs = s.run()
        runs = patch_runs(s)
        check(len(runs) == 1 and runs[0][1] - runs[0][0] >= 20, '%s %s not taken: the patch for the program %s' % (fname, mvname, [(r[0], r[1]) for r in runs]))
        check([m for f, m in msgs] == [MSG['SET'], MSG['NOT_TAKEN']], '%s %s not taken: message %s' % (fname, mvname, msgs))
    print('hold-time direct finishers checked (%s)' % game)


def mkp_setup(line, slot, p2_wins=False, sites=None):
    fname, cid, moves = T.fighters('mkp')[line]
    name, kind, cmd, prog, dmin, dmax, note = moves[slot]
    site, hold, key = T.MKP_DIRECT[(fname, name)]
    d = distance_in(dmin, dmax)
    s = Script('mkp')
    if sites is not None:                  # (the sites the set lacks: their words are 0)
        s.l = [x for x in s.l if not (x.startswith('c ') and 48 <= int(x.split()[1]) <= 56 and int(x.split()[1]) - 48 not in sites)]
    if p2_wins:
        s.fight(other_char(cid), cid, 500, 500 + d, 2, r1=DIZZY1, r2=STANCE)
    else:
        s.fight(cid, other_char(cid), 500, 500 + d, 2)
    s.pick(line, slot)
    s.frames(2)
    s.finish(1 if p2_wins else 2)
    return s, (fname, cid, name, site, hold, key)


def test_mkp():
    """Mortal Kombat Plus's page: every move of the eight fighters is a direct finisher at its own site
    (Reptile's and the Babalities' are not the fighter's id), the same program as Mortal Kombat's."""
    n = 0
    for line, (fname, cid, moves) in enumerate(T.fighters('mkp')):
        for slot, mv in enumerate(moves):
            for p2 in (False, True):
                s, (fname, cid, name, site, hold, key) = mkp_setup(line, slot, p2_wins=p2)
                who = 2 if p2 else 1
                tag = 'direct MKP %s: %s%s' % (fname, name, ' (P2)' if p2 else '')
                dprog = T.direct_prog(cid, (hold, key))
                s.frames(len(model(dprog, 'L' if p2 else 'R')) + 20)
                frames, msgs = s.run()
                got = strip([k if dr == who else 0 for dr, k in frames])
                check(got == strip(model(dprog, 'L' if p2 else 'R')), tag + ' controls\n  got %s\n  exp %s' % (got, strip(model(dprog, 'L' if p2 else 'R'))))
                check(len(tap_starts(got, key if key in KEYBIT else 'D')) == T.DIRECT_TRIES, tag + ' %d taps' % T.DIRECT_TRIES)
                on = [k for k, (e, a, _) in enumerate(s.patch) if e]
                check(on and all(s.patch[k][1] == mkp_addr(site) for k in on), tag + ' patch address %s (site %d)' % ([hex(s.patch[k][1]) for k in on[:1]], site))
                check(on and on == list(range(on[0], on[-1] + 1)), tag + ' patch on in one run')
                check(not s.patch[-1][0], tag + ' patch off at the end')
                check([m for f, m in msgs] == [MSG['SET']] or [m for f, m in msgs] == [MSG['SET'], MSG['NOT_TAKEN']],
                      tag + ' messages %s' % msgs)
                n += 1
            # the set lacks the move's site: nothing is played, the move is not taken
            s, (fname, cid, name, site, hold, key) = mkp_setup(line, slot, sites={c for c in range(9) if c != site})
            s.frames(300)
            frames, msgs = s.run()
            check(not any(k for dr_, k in frames) and not any(e for e, a, _ in s.patch), '%s %s: no site: nothing played' % (fname, name))
            nt = MSG['NOT_TAKEN_FB'] if T.fighters('mkp')[line][2][slot][1] in (T.K_BABY, T.K_FRIEND) else MSG['NOT_TAKEN']
            check([m for f, m in msgs] == [MSG['SET'], nt], '%s %s: no site: not taken %s' % (fname, name, msgs))
            # taken after the first tap: the patch goes off, the rest of the taps are not pressed
            s, (fname, cid, name, site, hold, key) = mkp_setup(line, slot)
            s.frames(20)
            s.var('flag', 1)
            s.frames(120)
            frames, msgs = s.run()
            check(frames[-1][0] == 0 and not s.patch[-1][0], '%s %s: taken: controls and patch let go' % (fname, name))
            check(not [m for f, m in msgs if f > 0], '%s %s: taken: no message %s' % (fname, name, msgs))
    print('%d Mortal Kombat Plus moves checked' % n)


if __name__ == '__main__':
    test_moves()
    test_direct()
    test_mkp()
    test_direct2('mk2')
    test_direct2('rev4')
    test_keep('mk2')
    test_keep('rev4')
    roms = os.environ.get('FM_ROMS')
    if roms:
        for sn, gm in (('mk2s03', 'mk2'), ('mk2s04', 'mk2'), ('mk2s08', 'rev4'), ('mk2', 'mk2')):
            test_real(sn, gm, open(os.path.join(roms, '%s_rom0.bin' % sn), 'rb').read()[:0x100000])
    else:
        print('real configurations: skipped (FM_ROMS)')
    test_messages()
    print('FAILED %d' % fails if fails else 'all passed')
    sys.exit(1 if fails else 0)

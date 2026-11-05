#!/usr/bin/env python3
"""
mra_check.py - load MRA files the way Main_MiSTer does and check them

    python3 tools/mra_check.py --zips DIR [--hbmame DIR] [--regions DIR] [--out DIR] mra/...

For every MRA: each <rom> is assembled from the zips with a port of
Main_MiSTer's loader (support/arcade/mra_loader.cpp: rom_data, rom_file;
<interleave> maps, part offset/length/repeat, inline hex data) and its md5
is computed the same way (every byte read, in order, before interleaving).
The md5 must match the MRA's. A <rom> whose zip is "/hbmame/<zip>" (an HBMAME
hack, tools/hbmame_sets.py) is read from --hbmame's <zip> alone, as
Main_MiSTer reads <games>/hbmame/<zip>; MAME has no region dump for such a
set, so the region comparison is left out.

With --regions (a folder of MAME region dumps written by
tools/mame/region_dump.lua, one folder per set: <set>/<region>.bin), the
loaded streams are also compared with what MAME itself loaded, region by
region, so a parser mistake in the generator cannot hide behind a matching
md5. This check is independent of mra_gen.py and tunit_layout.py.

Every set carries the OSD's Cheats list (<cheats size="8"
max="8">; tools/tunit_cheats.py, rtl/tunit_cheats.sv).
Every cheat is whole 8-byte units (at most 8) with a name of 27 characters at
most, two cheats of a set never have one name, and every unit is legal (a
word address of the program ROM with the instruction-word flag, or of main RAM
without it; no unused flag bit; a store entry or a one-shot covering the whole
word, a one-shot being a RAM word alone; the value inside the mask). The
cheats are also made again from the loaded program ROM and must equal the
MRA's (the MRA is not stale). The Mortal Kombat II sets are checked on their
own from the program ROM: Infinite Health P1 and P2 and Infinite Round Time,
Stop Finishing Move Timer (Plus has these four only). The health units are
checked against the damage routine (SLL 5,A6 / ADDI table,A6 / MOVE *A6+,A6,1 /
MOVE *A6,A1,0, then the hit SUB A10,A1 - in Plus a JA to a routine that starts
with it - and MOVE A1,*A6,0): the table it names holds the two energy words
(32-bit pointers, P1's then P2's), which must be the ones the program ROM's
round start fills (MOVI full,A0 and MOVE A0 to both), and each health unit must
be the high half of its player's pointer in that table, a program ROM word
read as data (flags 0, the whole word), with a value that makes the pointer
land on a program ROM word from 0400h to 7FFFh (the game reads the energy as a
signed 16-bit field, SETF 10h,1,0, so the constant must be positive in it), so a
hit is taken off a large constant and the energy word itself is never touched. The round time unit is the DEC A10
of the clock process (followed by JRNN, MOVK 9,A10, DEC A11, and after the
clock's start MOVK 9,A11 / MOVK 9,A10; in Plus the same four with long jumps,
DEC A10 / JANN to the word after DEC A11 / MOVK 9,A10 / JA to DEC A11) with
MOVE A10,A10 (4D4Ah) flagged as an instruction word, and the timer cheat the
80h (FFh in Challenger) after the program ROM's MOVI .,A11 with the 7FFFh
patch flagged as an instruction word; Plus has two timer units, the 80h and
the 140h of its own routine, each after a MOVI .,A11. The drain cheats are
one-shots of those two energy words.

ROM index 1's first word must hold only the game id and the flag (bit 8,
Mortal Kombat II Plus: the OSD shows the hack's Move List and View Secrets and
hides the Finishing Moves and Hidden Items), and a set with
the flag has no table after the format word but the AI level word (bytes
0x454-0x45B, zeros before them). Every MK and MK2 set must carry the AI level
word (Fixed AI Difficulty) there, and it must be the one an independent scan
of the loaded program ROM finds: the routine that reads the CPU opponent's
level, adds to it, clamps it to 0..9 and writes it back (exactly one in the
ROM, with the same word read and written). Behind it comes the PC after the
demo fights' store of the level (bytes 0x458-0x45B), which the scan finds as
MOVK 5,A0 / MOVE A0,@level,0 (exactly one in the ROM).

The word at byte 0x43E is the OSD class of the revision (0 to 3): the Finishing
Moves page shows each move line for the classes that have the move, so a
revision's page lists the moves it has. The word is 0 exactly when the 128-bit
mask of the moves the revision lacks (bytes 0x440-0x44F) is zero, and then in
every set that is not Mortal Kombat II; two sets with the same mask have the
same class and two with different masks have different ones, across all the MRAs
given.

With --out, the loaded streams are written as <set>_rom0.bin / _rom3.bin
for the simulator, and the game id / secrets table as <set>_rom1.bin
(sim_tunit --info).

Copyright (C) 2026 Gm0rk - GPL-3.0-or-later
"""

import argparse
import glob
import hashlib
import os
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mame_src


class Loader:
    """Port of Main_MiSTer's ROM assembly for one <rom> element."""

    def __init__(self):
        self.data = bytearray()
        self.romlen = [0] * 8
        self.unitlen = 1
        self.md5 = hashlib.md5()

    def rom_data(self, buf, mp):
        self.md5.update(buf)
        if not mp:
            mp = 1
        # first lane with a non-zero nibble
        idx, reg = 0, mp
        for i in range(self.unitlen):
            if reg & 0xF:
                break
            reg >>= 4
            idx += 1
        if idx >= self.unitlen:
            raise ValueError('illegal map')
        offsets, gaps, first, reg = [], 0, True, mp
        for i in range(self.unitlen):
            if reg & 0xF:
                offsets.append(idx + (reg & 0xF) - 1 + gaps)
                first = False
            elif not first:
                gaps += 1
            reg >>= 4
        pos, k = 0, 0
        need = self.romlen[idx] + (len(buf) // len(offsets)) * self.unitlen + self.unitlen
        if len(self.data) < need:
            self.data += bytes(need - len(self.data))
        while pos < len(buf):
            for o in offsets:
                self.data[self.romlen[idx] + o] = buf[pos]
                pos += 1
            self.romlen[idx] += self.unitlen

    def result(self):
        return bytes(self.data[:self.romlen[0]]), self.md5.hexdigest()


def load_rom(rom, zips):
    ld = Loader()
    for node in rom:
        if node.tag == 'interleave':
            out = int(node.get('output'))
            inp = int(node.get('input', '8'))
            ld.unitlen = out // inp
            for i in range(1, 8):
                ld.romlen[i] = ld.romlen[0]
            for part in node:
                load_part(ld, part, zips, int(part.get('map', '0'), 16))
            ld.unitlen = 1
        elif node.tag == 'part':
            load_part(ld, node, zips, 0)
            ld.unitlen = 1
    return ld.result()


def load_part(ld, part, zips, mp):
    repeat = int(part.get('repeat', '1'), 0)
    if part.get('name'):
        data = zips.read(part.get('name'), part.get('crc'))
        start = int(part.get('offset', '0'), 0)
        length = int(part.get('length', '0'), 0)
        data = data[start:]
        if length > 0:
            data = data[:length]
    else:
        data = bytes.fromhex(''.join((part.text or '').split()))
    for _ in range(repeat):
        ld.rom_data(data, mp)


# Fixed AI Difficulty: the adjust routine's word (0 = wildcard). Written here
# on its own, not taken from tools/tunit_fmoves.py.
LEVEL_ADJUST = [0x05A0, 0, 0, 0x4020, 0xCF01, 0x5600, 0x0B40, 0xFFF6, 0xC201, 0x1920, 0x0580, 0, 0, 0x0960]
LEVEL_WILD = {1, 2, 11, 12}


def level_scan(prog):
    """The AI level word's bit address in the program ROM (little-endian 16-bit
    words), or an error text."""
    n = len(prog) // 2
    w = [prog[2 * i] | prog[2 * i + 1] << 8 for i in range(n)]
    hits = [i for i in range(n - len(LEVEL_ADJUST))
            if all(j in LEVEL_WILD or w[i + j] == v for j, v in enumerate(LEVEL_ADJUST))]
    if len(hits) != 1:
        return '%d AI level adjust routines in the program ROM, not 1' % len(hits)
    i = hits[0]
    rd, wr = w[i + 1] | w[i + 2] << 16, w[i + 11] | w[i + 12] << 16
    if rd != wr:
        return 'the AI level routine reads %08X and writes %08X' % (rd, wr)
    return rd


def demo_scan(prog, lv):
    """The bit address of the instruction after the demo fights' store of the
    level (MOVK 5,A0 / MOVE A0,@level,0; exactly one in the ROM), or an error
    text. Written here on its own, not taken from tools/tunit_fmoves.py."""
    n = len(prog) // 2
    w = [prog[2 * i] | prog[2 * i + 1] << 8 for i in range(n)]
    pat = [0x18A0, 0x0580, lv & 0xFFFF, lv >> 16]
    hits = [i for i in range(n - 4) if w[i:i + 4] == pat]
    if len(hits) != 1:
        return '%d demo stores of the AI level in the program ROM, not 1' % len(hits)
    return 0xFF800000 + (hits[0] + 4) * 16


MK2_CHEATS = ['Infinite Health P1', 'Infinite Health P2', 'Infinite Round Time', 'Stop Finishing Move Timer']
F_FETCH, F_STORE, F_POKE = 1, 2, 4


def parse_cheats(node):
    """({name: [(bit address, value, flags, mask), ...]}, [problems]) of a <cheats> element."""
    cheats, errs = {}, []
    for c in node.findall('cheat'):
        name = c.get('name')
        raw = bytes.fromhex(''.join((c.text or '').split()))
        if len(raw) % 8 or not raw:
            errs.append('%s is %d bytes, not 8-byte units' % (name, len(raw)))
            continue
        if name in cheats:
            errs.append('two cheats named %r' % name)
        us = []
        for k in range(0, len(raw), 8):
            lo, hi, val, mask = [raw[k + i] | raw[k + i + 1] << 8 for i in range(0, 8, 2)]
            us.append((((hi & 0xFFF) << 16 | lo) << 4, val, hi >> 12, mask))
        cheats[name] = us
    return cheats, errs


def cheat_checks(root, gid, hides, prog, setname=''):
    """Problems with the MRA's <cheats> (see the module text)."""
    node = root.find('cheats')
    if node is None:
        return ['no <cheats> (every set has them)']
    errs = []
    if node.get('size') != '8' or node.get('max') != '8':
        errs.append('<cheats> size %s max %s, not 8 and 8' % (node.get('size'), node.get('max')))
    n = len(prog) // 2
    w = [prog[2 * i] | prog[2 * i + 1] << 8 for i in range(n)]
    allc, e = parse_cheats(node)
    errs += e
    for name, us in allc.items():
        if len(name) > 27:
            errs.append('%r is %d characters, the OSD shows 27' % (name, len(name)))
        if len(us) > 8:
            errs.append('%r has %d units, the board takes 8' % (name, len(us)))
        for a, v, fl, m in us:
            where = '%r unit %08X' % (name, a)
            rom = a >= 0xFF800000
            if a & 15:
                errs.append('%s is not word aligned' % where)
            if fl & 8:
                errs.append('%s has the unused flag bit' % where)
            if gid == 2 and name in MK2_CHEATS[:2]:
                # a table word of the program ROM that the game reads as data
                if not rom or fl:
                    errs.append('%s: the damage pointer table is program ROM read as data, flags 0, not %s %d'
                                % (where, 'program ROM' if rom else 'main RAM', fl))
            elif bool(fl & F_FETCH) != rom:
                errs.append('%s: %s but flagged %d' % (where, 'program ROM' if rom else 'main RAM', fl))
            if rom and not 0 <= (a - 0xFF800000) >> 4 < n:
                errs.append('%s is not in the program ROM' % where)
            if not rom and not 0x01000000 <= a < 0x01400000:
                errs.append('%s is not main RAM (01000000-013FFFFF)' % where)
            if fl & (F_STORE | F_POKE) and m != 0xFFFF:
                errs.append('%s: a store entry or one-shot covers the whole word, mask is %04X' % (where, m))
            if fl & F_POKE and fl & (F_FETCH | F_STORE):
                errs.append('%s: a one-shot is a plain RAM write, flags %d' % (where, fl))
            if v & ~m & 0xFFFF and not fl & F_POKE:
                errs.append('%s: value %04X outside the mask %04X' % (where, v, m))
    # the cheats made again from the program ROM
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import tunit_cheats
    again, _ = tunit_cheats.build(gid, prog, setname, plus=hides)
    mine = dict(again)
    got = {name: b''.join(bytes.fromhex(''.join((c.text or '').split())) for c in node.findall('cheat') if c.get('name') == name)
           for name in allc}
    if set(mine) != set(got):
        errs.append('cheats differ from the generator\'s: only in the MRA %s, only in the generator %s'
                    % (sorted(set(got) - set(mine)), sorted(set(mine) - set(got))))
    else:
        for name in mine:
            if mine[name] != got[name]:
                errs.append('%r differs from the generator\'s units' % name)
    if gid == 2:
        errs += mk2_cheat_checks(allc, hides, w, n)
    return errs


def mk2_health_checks(u1, u2, w, n):
    """Infinite Health P1 and P2 (their one unit each) against the damage routine
    of the program ROM. Returns (problems, P1 energy, P2 energy), the energies
    being None when the routine or its table is not what it should be."""
    errs = []
    # SLL 5,A6 / ADDI table,A6 / MOVE *A6+,A6,1 / MOVE *A6,A1,0 (the victim's pointer, its energy)
    dm = [i for i in range(n - 12)
          if w[i] == 0x24A6 and w[i + 1] == 0x0B26 and w[i + 4] == 0x96C6 and w[i + 5] == 0x84C1]
    if len(dm) != 1:
        return ['%d damage routines (SLL 5,A6 / ADDI table,A6 / MOVE *A6+,A6,1 / MOVE *A6,A1,0), not 1' % len(dm)], None, None
    i = dm[0]
    # the hit and the store back: SUB A10,A1 (Plus: a JA to a routine that starts with it) .. MOVE A1,*A6,0
    if w[i + 6] == 0xC080:
        t = w[i + 7] | w[i + 8] << 16
        j = (t - 0xFF800000) >> 4 if t >= 0xFF800000 and not t & 15 else -1
        hit = 0 <= j < n and w[j] == 0x4541
    else:
        hit = w[i + 6] == 0x4541
    if not hit or w[i + 9] != 0x8026:
        errs.append('the damage routine at %08X does not subtract A10 from the energy and store it back' % (0xFF800000 + 16 * i))
    tab = w[i + 2] | w[i + 3] << 16
    ti = (tab - 0xFF800000) >> 4 if tab >= 0xFF800000 and not tab & 15 else -1
    if ti < 0 or ti + 4 > n:
        return errs + ['the damage routine\'s table %08X is not in the program ROM' % tab], None, None
    e1, e2 = w[ti] | w[ti + 1] << 16, w[ti + 2] | w[ti + 3] << 16
    # the round start's fill of those two energy words: MOVI full,A0 / MOVE A0,@P1 / MOVE A0,@P2 (the other fill, FFFFh, is not it)
    ok = [k for k in range(n - 8)
          if w[k] == 0x09C0 and w[k + 1] != 0xFFFF and w[k + 2] == 0x0580 and w[k + 3] | w[k + 4] << 16 == e1
          and w[k + 5] == 0x0580 and w[k + 6] | w[k + 7] << 16 == e2]
    if len(ok) != 1:
        errs.append('%d places fill the table\'s energies %08X and %08X with a full value' % (len(ok), e1, e2))
    if e1 & 15 or e2 & 15 or not (0x01000000 <= e1 < 0x01400000 and 0x01000000 <= e2 < 0x01400000):
        errs.append('an energy word (%08X, %08X) is not a word of main RAM' % (e1, e2))
    for who, (a, v, fl, m), e, off in (('P1', u1, e1, 1), ('P2', u2, e2, 3)):
        if a != 0xFF800000 + 16 * (ti + off):
            errs.append('Infinite Health %s is %08X, not the high half of its pointer in the table (%08X)'
                        % (who, a, 0xFF800000 + 16 * (ti + off)))
        if fl or m != 0xFFFF:
            errs.append('Infinite Health %s has flags %d mask %04X, not 0 and FFFF' % (who, fl, m))
        tgt = v << 16 | (e & 0xFFFF)
        ri = (tgt - 0xFF800000) >> 4 if v >= 0xFF80 and not tgt & 15 else -1
        if not 0 <= ri < n:
            errs.append('Infinite Health %s points the damage at %08X, not a program ROM word' % (who, tgt))
        elif not 0x400 <= w[ri] <= 0x7FFF:
            errs.append('Infinite Health %s points the damage at %08X, which holds %04X, not 0400 to 7FFF: a hit would '
                        'take it to zero or below (the game reads the energy as a signed 16-bit field)' % (who, tgt, w[ri]))
    return errs, e1, e2


def mk2_cheat_checks(allc, hides, w, n):
    """The Mortal Kombat II cheats against an independent scan of the program."""
    errs = []
    for name in MK2_CHEATS:
        if name not in allc:
            return errs + ['no cheat %r' % name]
    want_units = [1, 1, 1, 2 if hides else 1]        # Plus: the timer's 80h and 140h
    units = [allc[name] for name in MK2_CHEATS]
    if [len(u) for u in units] != want_units:
        return errs + ['units per cheat %s, not %s' % ([len(u) for u in units], want_units)]
    cw, cv, cf, _ = units[2][0]
    herrs, e1, e2 = mk2_health_checks(units[0][0], units[1][0], w, n)
    errs += herrs
    for name, e in (('P1 Drain all Energy Now!', e1), ('P2 Drain all Energy Now!', e2)):
        if hides:
            if name in allc:
                errs.append('Plus has the drain cheat %r' % name)
        elif e is not None and allc.get(name) != [(e, 1, F_POKE, 0xFFFF)]:
            errs.append('%r is %s, not a one-shot of the energy word %08X to 1' % (name, allc.get(name), e))
    # the round clock: DEC A10 / JRNN / MOVK 9,A10 / DEC A11 after the process's start (Plus: the same
    # with JANN and JA, the DEC A11 being the word its jumps name)
    i = (cw - 0xFF800000) >> 4 if cw >= 0xFF800000 and not cw & 15 else -1
    if i < 1 or i + 8 > n:
        errs.append('the round clock word %08X is not in the program ROM' % cw)
    else:
        near = i                                     # a word of the process, where it counts
        if w[i] == 0x142A and (w[i + 1] & 0xFF00) == 0xCF00 and w[i + 2] == 0x192A and w[i + 3] == 0x142B:
            pass
        elif (w[i] == 0x142A and w[i + 1] == 0xCF80 and w[i + 4] == 0x192A and w[i + 5] == 0xC080):
            dst_n, dst_j = w[i + 2] | w[i + 3] << 16, w[i + 6] | w[i + 7] << 16     # JANN, JA targets
            d = (dst_j - 0xFF800000) >> 4 if dst_j >= 0xFF800000 and not dst_j & 15 else -1
            if d < 1 or d + 2 > n or w[d] != 0x142B or dst_n != dst_j + 16:
                errs.append('the round clock word %08X: its jumps go to %08X and %08X, not DEC A11 and the word after it'
                            % (cw, dst_n, dst_j))
            else:
                near = d
        else:
            errs.append('the round clock word %08X is not DEC A10 / JRNN / MOVK 9,A10 / DEC A11 (or DEC A10 / JANN / MOVK 9,A10 / JA)' % cw)
        start = [k for k in range(max(0, near - 0xC0), near)
                 if w[k] == 0x192B and w[k + 1] == 0x192A and w[k + 2] == 0x058A and w[k + 5] == 0x058B]
        if len(start) != 1:
            errs.append('%d clock process starts (MOVK 9,A11 / MOVK 9,A10 / MOVE A10,@ / MOVE A11,@) before %08X' % (len(start), cw))
        if cv != 0x4D4A or cf != F_FETCH:
            errs.append('the round time cheat is %04X flags %d, not 4D4A (MOVE A10,A10) as an instruction word' % (cv, cf))
    # the timer: the immediate of the second wait's MOVI .,A11 (Plus: the hack's, 80h and then 140h)
    for k, (tw, tv, tf, _) in enumerate(units[3]):
        i = (tw - 0xFF800000) >> 4 if tw >= 0xFF800000 and not tw & 15 else -1
        if i < 1 or i >= n:
            errs.append('the timer word %08X is not in the program ROM' % tw)
            continue
        ok_imm = (0x0080, 0x00FF) if k == 0 else (0x0140,)
        if w[i - 1] != 0x09CB or w[i] not in ok_imm:
            errs.append('the timer word %08X is %04X after %04X, not %s after MOVI .,A11'
                        % (tw, w[i], w[i - 1], '/'.join('%02Xh' % v for v in ok_imm)))
        if tv != 0x7FFF or tf != F_FETCH:
            errs.append('the timer cheat is %04X flags %d, not 7FFF as an instruction word' % (tv, tf))
    return errs


# region checks: (rom index, stream offset, region, region offset, length)
def region_checks(setname, streams, regions_dir):
    d = os.path.join(regions_dir, setname)
    if not os.path.isdir(d):
        return ['no region dump for %s' % setname]
    errs = []

    def region(tag):
        p = os.path.join(d, tag.replace(':', '_') + '.bin')
        return open(p, 'rb').read() if os.path.exists(p) else None

    s0, s3 = streams.get(0, b''), streams.get(3, b'')
    prog, video = region('maincpu'), region('video')
    if prog != s0[:0x100000]:
        errs.append('program ROM differs from MAME maincpu')
    g = s0[0x100000:]
    if video[:len(g)] != g:
        errs.append('graphics differ from MAME video')
    if any(video[len(g):]):
        errs.append('MAME video has data above the loaded %X bytes' % len(g))
    dcs = region('dcs')
    if dcs is not None:
        for w in range(len(dcs) // 2):
            p = ((w >> 20) << 19) | (w & 0x7FFFF)
            b = s3[p] if p < len(s3) else 0xFF
            if dcs[2 * w] != b or dcs[2 * w + 1] != 0xFF:
                errs.append('DCS data differs at word %X' % w)
                break
    else:
        cpu, oki = region('adpcm_cpu'), region('adpcm_oki')
        if cpu[0x10000:0x50000] != s3[:0x40000]:
            errs.append('sound CPU ROM differs from MAME adpcm:cpu')
        if oki != s3[0x40000:0x140000]:
            errs.append('OKI samples differ from MAME adpcm:oki')
    return errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--zips', required=True)
    ap.add_argument('--hbmame', help='folder with the HBMAME hack zips (for "/hbmame/..." MRAs)')
    ap.add_argument('--regions')
    ap.add_argument('--out')
    ap.add_argument('mras', nargs='+')
    a = ap.parse_args()

    zips = mame_src.RomZips(sorted(glob.glob(os.path.join(a.zips, '*.zip'))))
    bad = 0
    classes = {}       # (game id, class) -> {the masks of the moves the sets of that class lack}
    for path in a.mras:
        root = ET.parse(path).getroot()
        setname = root.findtext('setname')
        streams, msgs = {}, []
        hb = None          # the HBMAME zip this MRA names, if any
        for rom in root.findall('rom'):
            zattr = rom.get('zip') or ''
            if zattr.startswith('/hbmame/'):
                if '|' in zattr or not a.hbmame:
                    msgs.append('%s: needs --hbmame (one zip)' % zattr)
                    continue
                hb = hb or mame_src.RomZips([os.path.join(a.hbmame, zattr[len('/hbmame/'):])])
        for rom in root.findall('rom'):
            idx = int(rom.get('index'))
            zips_rom = hb if (rom.get('zip') or '').startswith('/hbmame/') else zips
            if zips_rom is None:
                continue
            if idx == 1:
                data = load_rom(rom, zips)[0]
                streams[1] = data
                if a.out:
                    os.makedirs(a.out, exist_ok=True)
                    open(os.path.join(a.out, '%s_rom1.bin' % setname), 'wb').write(data)
                continue
            if idx not in (0, 3):
                continue
            data, md5 = load_rom(rom, zips_rom)
            streams[idx] = data
            if md5 != rom.get('md5'):
                msgs.append('rom %d md5 %s, MRA says %s' % (idx, md5, rom.get('md5')))
            if a.out:
                os.makedirs(a.out, exist_ok=True)
                open(os.path.join(a.out, '%s_rom%d.bin' % (setname, idx)), 'wb').write(data)
        if a.regions and hb is None:
            msgs += region_checks(setname, streams, a.regions)
        # ROM index 1, word 0: the game id (bits 2:0) and, for a set that hides
        # the Plus set's own Move List and View Secrets (no Finishing Moves or
        # Hidden Items), bit 8; that set's table is the two words (game id and
        # format), nothing else
        t = streams.get(1, b'')
        hides = False
        if len(t) >= 2:
            w0 = t[0] | t[1] << 8
            hides = bool(w0 & 0x100)
            if w0 & ~0x107:
                msgs.append('rom 1 word 0 is %04X: bits other than the game id and the hide flag' % w0)
            gid = w0 & 7
            if hides and (len(t) != 0x45C or any(t[4:0x454])):
                msgs.append('rom 1 hides the extras but is %d bytes, not game id and format, zeros, '
                            'and the AI level word and the demo store at 0x454' % len(t))
            if gid <= 2:      # MK, MK Turbo, MK2: the AI level word, as the scan finds it
                lv = level_scan(streams.get(0, b'')[:0x100000])
                if len(t) < 0x45C:
                    msgs.append('rom 1 has no AI level word and demo store (%d bytes)' % len(t))
                elif isinstance(lv, str):
                    msgs.append(lv)
                else:
                    got = (t[0x454] | t[0x455] << 8 | t[0x456] << 16 | t[0x457] << 24) << 4
                    if got != lv:
                        msgs.append('rom 1 AI level word is %08X, the program ROM\'s is %08X' % (got, lv))
                    else:
                        dm = demo_scan(streams.get(0, b'')[:0x100000], lv)
                        gotd = (t[0x458] | t[0x459] << 8 | t[0x45A] << 16 | t[0x45B] << 24) << 4
                        if isinstance(dm, str):
                            msgs.append(dm)
                        elif gotd != dm:
                            msgs.append('rom 1 demo store PC is %08X, the program ROM\'s is %08X' % (gotd, dm))
        if len(t) >= 0x450:
            cls = t[0x43E] | t[0x43F] << 8
            gone = bytes(t[0x440:0x450])
            if cls > 3:
                msgs.append('rom 1 OSD class is %d, not 0 to 3' % cls)
            elif (cls == 0) != (not any(gone)):
                msgs.append('rom 1 OSD class is %d but the mask of the moves the set lacks is %s'
                            % (cls, 'zero' if not any(gone) else 'not zero'))
            elif cls and (t[0] & 7) != 2:
                msgs.append('rom 1 OSD class is %d in a set that is not Mortal Kombat II' % cls)
            else:
                classes.setdefault((t[0] & 7, cls), set()).add(gone)
                for (g, c), masks in classes.items():
                    if g == t[0] & 7 and c != cls and gone in masks:
                        msgs.append('rom 1 OSD class %d, and %d for another set that lacks the same moves' % (cls, c))
        if len(t) >= 2:
            msgs += cheat_checks(root, t[0] & 7, hides, streams.get(0, b'')[:0x100000], setname)
        status = 'OK' if not msgs else 'FAIL'
        bad += bool(msgs)
        print('%-12s %-4s rom0 %8X rom3 %8X rom1 %4X  %s' % (setname, status, len(streams.get(0, b'')),
                                                             len(streams.get(3, b'')), len(streams.get(1, b'')),
                                                             '; '.join(msgs + (['Plus: own Move List and View Secrets, no Finishing Moves or Hidden Items'] if hides else []))))
    for (g, c), masks in sorted(classes.items()):
        if len(masks) > 1:
            print('FAIL OSD class %d of game %d holds sets that lack different moves' % (c, g))
            bad += 1
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()

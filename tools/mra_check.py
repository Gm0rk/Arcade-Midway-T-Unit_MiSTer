#!/usr/bin/env python3
"""
mra_check.py - load MRA files the way Main_MiSTer does and check them

    python3 tools/mra_check.py --zips DIR [--regions DIR] [--out DIR] mra/...

For every MRA: each <rom> is assembled from the zips with a port of
Main_MiSTer's loader (support/arcade/mra_loader.cpp: rom_data, rom_file;
<interleave> maps, part offset/length/repeat, inline hex data) and its md5
is computed the same way (every byte read, in order, before interleaving).
The md5 must match the MRA's.

With --regions (a folder of MAME region dumps written by
tools/mame/region_dump.lua, one folder per set: <set>/<region>.bin), the
loaded streams are also compared with what MAME itself loaded, region by
region, so a parser mistake in the generator cannot hide behind a matching
md5. This check is independent of mra_gen.py and tunit_layout.py.

With --out, the loaded streams are written as <set>_rom0.bin / _rom3.bin
for the simulator.

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
    ap.add_argument('--regions')
    ap.add_argument('--out')
    ap.add_argument('mras', nargs='+')
    a = ap.parse_args()

    zips = mame_src.RomZips(sorted(glob.glob(os.path.join(a.zips, '*.zip'))))
    bad = 0
    for path in a.mras:
        root = ET.parse(path).getroot()
        setname = root.findtext('setname')
        streams, msgs = {}, []
        for rom in root.findall('rom'):
            idx = int(rom.get('index'))
            if idx not in (0, 3):
                continue
            data, md5 = load_rom(rom, zips)
            streams[idx] = data
            if md5 != rom.get('md5'):
                msgs.append('rom %d md5 %s, MRA says %s' % (idx, md5, rom.get('md5')))
            if a.out:
                os.makedirs(a.out, exist_ok=True)
                open(os.path.join(a.out, '%s_rom%d.bin' % (setname, idx)), 'wb').write(data)
        if a.regions:
            msgs += region_checks(setname, streams, a.regions)
        status = 'OK' if not msgs else 'FAIL'
        bad += bool(msgs)
        print('%-12s %-4s rom0 %8X rom3 %8X  %s' % (setname, status, len(streams.get(0, b'')),
                                                    len(streams.get(3, b'')), '; '.join(msgs)))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()

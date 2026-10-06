#!/usr/bin/env python3
"""
mra_gen.py - write the core's MRA files from MAME's T-Unit driver source

    python3 tools/mra_gen.py <mame>/src/mame/williams/midtunit.cpp mra/ \
        [--zips DIR] [--date YYYYMMDD]

One MRA per MAME set: parents in mra/, clones in
mra/_alternatives/_<Game>/. Each MRA carries
  - the game id (rom index 1) that selects the board configuration,
  - the program and graphics ROMs (rom index 0) and the sound ROMs (rom
    index 3), laid out as tools/tunit_layout.py describes,
  - MAME's DIP switches for the set (OSD), button names, NVRAM (16 KB).

Merged sets: every <rom> names "set.zip|parent.zip" and every part carries
its CRC, so Main_MiSTer finds files in a merged or split zip.

md5: with --zips (a folder holding the MAME zips), each <rom> gets the md5
Main_MiSTer computes while loading: all part data in read order, repeats
and fill bytes included, before interleaving. Without the zips the md5 is
"None" (Main_MiSTer then skips the check). A wrong md5 makes Main_MiSTer
refuse the ROM ("md5 mismatch for rom 0"), which is why it is computed by
loading the files exactly as Main_MiSTer would, never from an assembled
image.

Copyright (C) 2026 Gm0rk - GPL-3.0-or-later
"""

import argparse
import datetime
import glob
import os
import sys
from xml.sax.saxutils import escape

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mame_src
import tunit_layout as L

RBF = 'Arcade-Midway-T-Unit'
MAME_VERSION = '0289'
NVRAM_SIZE = 16384

# --------------------------------------------------------------------------
# Per-game presentation (category, players, button names and defaults)
#
# Button order is MAME's (BUTTON1, BUTTON2, ...), which is also the order of
# the core's joystick buttons B1-B6.
# --------------------------------------------------------------------------

GAME_INFO = {
    L.G_MK:       ('Fighter / Versus', 2,
                   ['High Punch', 'Block', 'High Kick', 'Low Punch', 'Low Kick', 'Block 2'],
                   ['Y', 'R', 'X', 'B', 'A', 'L']),
    L.G_MKTURBO:  ('Fighter / Versus', 2,
                   ['High Punch', 'Block', 'High Kick', 'Low Punch', 'Low Kick', 'Block 2'],
                   ['Y', 'R', 'X', 'B', 'A', 'L']),
    L.G_MK2:      ('Fighter / Versus', 2,
                   ['High Punch', 'Block', 'High Kick', 'Low Punch', 'Low Kick', 'Block 2'],
                   ['Y', 'R', 'X', 'B', 'A', 'L']),
    L.G_NBAJAM:   ('Sports / Basketball', 4,
                   ['Turbo', 'Shoot/Block', 'Pass/Steal'],
                   ['R', 'A', 'B']),
    L.G_NBAJAMTE: ('Sports / Basketball', 4,
                   ['Turbo', 'Shoot/Block', 'Pass/Steal'],
                   ['R', 'A', 'B']),
    L.G_JDREDDP:  ('Platform / Shooter Scrolling', 3,
                   ['Kick', 'Jump', 'Punch', 'Crouch'],
                   ['X', 'B', 'A', 'Y']),
}


def file_name(desc):
    """MRA file name from MAME's description (Windows-safe)."""
    return desc.replace('/', '-').replace(':', ' -').replace('?', '') + '.mra'


def folder_name(desc):
    """_alternatives folder: the game title without the revision; a final
    dot becomes '_' (Windows cannot end a folder name with a dot)."""
    base = desc.split(' (')[0].strip()
    if base.endswith('.'):
        base = base[:-1] + '_'
    return '_' + base.replace('/', '-').replace(':', ' -')

# --------------------------------------------------------------------------
# DIP switches
# --------------------------------------------------------------------------

def dsw_default(dips):
    v = 0xFFFF
    for d in dips:
        v = (v & ~d.mask) | (d.default & d.mask)
    return v


def dip_xml(d):
    bits = [b for b in range(16) if d.mask >> b & 1]
    lo = bits[0]
    if bits != list(range(lo, bits[-1] + 1)):
        raise ValueError('DIP %s: mask %04X not contiguous' % (d.name, d.mask))
    bit_attr = str(lo) if len(bits) == 1 else '%d,%d' % (lo, bits[-1])
    # settings MAME marks Unused are left out; MRA ids are comma separated,
    # so a comma inside a name becomes " -"
    sets = [(v, n) for v, n in d.settings if n != 'Unused']
    ids = ','.join(n.replace(',', ' -') for v, n in sets)
    vals = [(v & d.mask) >> lo for v, n in sets]
    # values can be left out when they are just 0, 1, 2, ...
    if vals == list(range(len(vals))):
        return '\t\t<dip bits="%s" name="%s" ids="%s"/>' % (bit_attr, escape(d.name), escape(ids))
    return '\t\t<dip bits="%s" name="%s" ids="%s" values="%s"/>' % (
        bit_attr, escape(d.name), escape(ids), ','.join(map(str, vals)))

# --------------------------------------------------------------------------
# ROM parts
# --------------------------------------------------------------------------

def part_xml(p, indent):
    t = '\t' * indent
    if p[0] == 'file':
        # offset/length only when the piece is part of the file
        attrs = 'crc="%s" name="%s"' % (p[2], escape(p[1]))
        if p[3]:
            attrs += ' offset="0x%X"' % p[3]
        if p[3] or p[4] != file_len(p):
            attrs += ' length="0x%X"' % p[4]
        return [t + '<part %s/>' % attrs]
    if p[0] == 'ileave':
        width, parts, length = p[1], p[2], p[3]
        lines = [t + '<interleave output="%d">' % (8 * width)]
        for name, crc, lane in parts:
            m = ''.join('1' if i == lane else '0' for i in reversed(range(width)))
            lines.append(t + '\t<part crc="%s" name="%s" map="%s"/>' % (crc, escape(name), m))
        lines.append(t + '</interleave>')
        return lines
    return [t + '<part repeat="0x%X">%02X</part>' % (p[2], p[1])]


FILE_LENGTHS = {}

def file_len(p):
    """Full length of the file a 'file' piece reads (from the zips if we have
    them, else MAME's load length): a length attribute is only written when
    the piece takes part of a file."""
    return FILE_LENGTHS.get(p[2], p[4])


def rom_xml(index, zipattr, pieces, md5, comments):
    lines = ['\t<rom index="%d" zip="%s" md5="%s" type="merged">' % (index, zipattr, md5)]
    for i, p in enumerate(pieces):
        if i in comments:
            lines.append('\t\t<!-- %s -->' % comments[i])
        lines += part_xml(p, 2)
    lines.append('\t</rom>')
    return lines

# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('driver')
    ap.add_argument('outdir')
    ap.add_argument('--zips', help='folder with MAME zips (for md5)')
    ap.add_argument('--date', default=datetime.date.today().strftime('%Y%m%d'))
    a = ap.parse_args()

    games, sets, inputs = mame_src.parse_driver(a.driver)
    zips = None
    if a.zips:
        zips = mame_src.RomZips(sorted(glob.glob(os.path.join(a.zips, '*.zip'))))
        for crc, (z, info) in zips.by_crc.items():
            FILE_LENGTHS[crc] = info.file_size

    parents = {g.name: g for g in games}
    written = []
    for g in games:
        gid = L.game_id(g)
        cat, players, bnames, bdef = GAME_INFO[gid]
        top = parents[g.parent] if g.parent else g
        dips = [d for d in inputs[g.inputs]['DSW'] if d.name != 'Unused']
        zipattr = '%s.zip|%s.zip' % (g.name, g.parent) if g.parent else '%s.zip' % g.name

        st = L.streams(g.romset)
        out = []
        out.append('<misterromdescription>')
        out.append('\t<name>%s</name>' % escape(g.desc))
        out.append('\t<mratimestamp>%s</mratimestamp>' % a.date)
        out.append('\t<mameversion>%s</mameversion>' % MAME_VERSION)
        out.append('\t<setname>%s</setname>' % g.name)
        out.append('\t<year>%s</year>' % g.year)
        out.append('\t<manufacturer>%s</manufacturer>' % escape(g.manuf))
        out.append('\t<category>%s</category>' % cat)
        out.append('\t<rbf>%s</rbf>' % RBF)
        out.append('\t<remark>%d players</remark>' % players)

        dv = dsw_default(inputs[g.inputs]['DSW'])
        out.append('\t<switches default="%02X,%02X">' % (dv & 0xFF, dv >> 8))
        for d in sorted(dips, key=lambda d: (d.mask & -d.mask)):
            out.append(dip_xml(d))
        out.append('\t</switches>')

        names = bnames + ['-'] * (6 - len(bnames))
        defs = bdef + ['-'] * (6 - len(bdef))
        out.append('\t<buttons names="%s,Start,Coin,Test,Pause" default="%s,Start,Select,-,-"/>'
                   % (','.join(names), ','.join(defs)))

        out.append('\t<romstruct>')
        out.append('rom index 0 (SDRAM 0x000000):')
        out += st[0][2]
        out.append('rom index 3 (SDRAM 0x%06X):' % L.SDRAM_SOUND)
        out += st[3][2]
        out.append('\t</romstruct>')

        out.append('\t<rom index="1">')
        out.append('\t\t<part>%02X</part>' % gid)
        out.append('\t</rom>')

        for idx in (0, 3):
            pieces = st[idx][0]
            md5 = L.render(pieces, zips)[1] if zips else 'None'
            if idx == 0:
                n_prog = len(L.interleaved_pieces(g.romset.regions['maincpu'], 2,
                                                  g.romset.regions['maincpu'].size)[0])
                comments = {0: 'program ROM', n_prog: 'graphics'}
            elif L.uses_dcs(g.romset):
                comments = {0: 'DCS sound data'}
            else:
                n_cpu = len(L.linear_pieces(g.romset.regions['adpcm:cpu'], 0x10000, 0x50000))
                comments = {0: 'sound CPU', n_cpu: 'OKI samples'}
            out += rom_xml(idx, zipattr, pieces, md5, comments)

        out.append('\t<nvram index="2" size="%d"/>' % NVRAM_SIZE)
        out.append('</misterromdescription>')

        if g.parent:
            d = os.path.join(a.outdir, '_alternatives', folder_name(top.desc))
        else:
            d = a.outdir
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, file_name(g.desc))
        with open(path, 'w', newline='\n') as f:
            f.write('\n'.join(out) + '\n')
        written.append(path)

    for p in written:
        print(p)


if __name__ == '__main__':
    main()

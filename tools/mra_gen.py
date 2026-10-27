#!/usr/bin/env python3
"""
mra_gen.py - write the core's MRA files from MAME's T-Unit driver source

    python3 tools/mra_gen.py <mame>/src/mame/williams/midtunit.cpp mra/ \
        [--zips DIR] [--hbmame DIR] [--date YYYYMMDD]

One MRA per MAME set: parents in mra/, clones in
mra/_alternatives/_<Game>/. Each MRA carries
  - the game id (rom index 1) that selects the board configuration, and
    after it the set's secrets table (codes and read patches for the OSD
    Secrets and cheats, tools/tunit_secrets.py) and, for MK and MK2 at byte
    0x400, the fight variables the finishing-move player follows and the
    AI level word of Fixed AI Difficulty (tools/tunit_fmoves.py); both need
    --zips: they are found in the set's own program ROM. A set with its own
    extras (hbmame_sets.py hide_extras: Mortal Kombat II Plus) has the game
    id with the flag instead: no table, and the OSD shows the hack's Move
    List and View Secrets (tools/tunit_plus.py) but no Finishing Moves or
    Hidden Items (and the AI level word, at byte 0x454),
  - the program and graphics ROMs (rom index 0) and the sound ROMs (rom
    index 3), laid out as tools/tunit_layout.py describes,
  - MAME's DIP switches for the set (less the ones the set does not use,
    UNUSED_DIPS) and the core's Service Credit and Tilt (OSD DIP Switches
    page, in alphabetical order), button names, NVRAM (16 KB).

Merged sets: every <rom> names "set.zip|parent.zip" and every part carries
its CRC, so Main_MiSTer finds files in a merged or split zip.

HBMAME hacks (tools/hbmame_sets.py) are not in MAME's driver. With --hbmame
(a folder holding their zips, named as in games/hbmame) each one is written
too, as a clone of its MAME parent with its own files; its <rom> names
"/hbmame/<zip>", the path Main_MiSTer takes below games/ (a name starting
with '/' leaves out the 'mame' folder). Without --hbmame they are skipped.

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
import hbmame_sets
import tunit_layout as L
import tunit_secrets
import tunit_fmoves

RBF = 'Arcade-Midway-T-Unit'
MAME_VERSION = '0289'
NVRAM_SIZE = 16384

# --------------------------------------------------------------------------
# Per-game presentation (category, players, button names and defaults)
#
# Button order is the core's joystick buttons B1-B6 (unused ones '-', which
# Main_MiSTer skips when buttons are defined). NBA Jam and Judge Dredd use
# MAME's order (BUTTON1, BUTTON2, ...); MK and MK2 list High Punch, Low
# Punch, High Kick, Low Kick, Block (MAME's Block 2 is not mapped).
# --------------------------------------------------------------------------

GAME_INFO = {
    L.G_MK:       ('Fighter / Versus', 2,
                   ['High Punch', 'Low Punch', 'High Kick', 'Low Kick', 'Block'],
                   ['Y', 'B', 'X', 'A', 'R']),
    L.G_MKTURBO:  ('Fighter / Versus', 2,
                   ['High Punch', 'Low Punch', 'High Kick', 'Low Kick', 'Block'],
                   ['Y', 'B', 'X', 'A', 'R']),
    L.G_MK2:      ('Fighter / Versus', 2,
                   ['High Punch', 'Low Punch', 'High Kick', 'Low Kick', 'Block'],
                   ['Y', 'B', 'X', 'A', 'R']),
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

# MAME's DIP switches that a set does not use: its own DIP switch screen
# (diagnostics, DIP Switch Test) marks the switch UNUSED and setting it
# changes nothing. They are left off the OSD; the bit keeps MAME's default.
#   - MK (all three sets): MAME's Skip Post Test (bit 8); toggling it does
#     not change the power-up either.
#   - MK2 L1.1 and L1.4: Bill Validator, Powerup Test, Circuit Boards (bits
#     10, 9, 8); L2.0 and L2.1: Powerup Test, Circuit Boards. L3.0 and later
#     use all three.
#   - NBA Jam rev 2.00, rev 1.00 and both prototypes: Players, Video Clips,
#     Powerup Test (bits 7, 5, 1); their power-up ROM test runs whatever
#     bit 1 says. Rev 3.01 uses all three.
_MK2_OLD = ['Bill Validator', 'Powerup Test', 'Circuit Boards']
_NJ_OLD = ['Players', 'Video Clips', 'Powerup Test']
UNUSED_DIPS = {
    'mk': ['Skip Post Test'], 'mkr4': ['Skip Post Test'], 'mktturbo': ['Skip Post Test'],
    'mk2r11': _MK2_OLD, 'mk2r14': _MK2_OLD,
    'mk2r20': ['Powerup Test', 'Circuit Boards'], 'mk2r21': ['Powerup Test', 'Circuit Boards'],
    'nbajamr2': _NJ_OLD, 'nbajamr1': _NJ_OLD, 'nbajamp2': _NJ_OLD, 'nbajamp1': _NJ_OLD,
}

# The core's own lines of the DIP Switches page: switches bits 16 and 17
# (the game's DIP switches are 0-15). The top level adds a service credit or
# slams the tilt switch each time the bit flips, so both settings read the
# same.
CORE_DIPS = [('Service Credit', '\t\t<dip bits="16" name="Service Credit" ids="Add credit,Add credit"/>'),
             ('Tilt', '\t\t<dip bits="17" name="Tilt" ids="Slam tilt,Slam tilt"/>')]

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
    ap.add_argument('--hbmame', help='folder with the HBMAME hack zips (tools/hbmame_sets.py)')
    ap.add_argument('--date', default=datetime.date.today().strftime('%Y%m%d'))
    a = ap.parse_args()

    games, sets, inputs = mame_src.parse_driver(a.driver)
    zips = None
    if a.zips:
        zips = mame_src.RomZips(sorted(glob.glob(os.path.join(a.zips, '*.zip'))))
        for crc, (z, info) in zips.by_crc.items():
            FILE_LENGTHS[crc] = info.file_size

    parents = {g.name: g for g in games}
    hack_zips = {}
    if a.hbmame:
        hacks = hbmame_sets.hack_games(games)
        hack_zips = hbmame_sets.hack_zips(a.hbmame)
        for z in hack_zips.values():
            for crc, (_, info) in z.by_crc.items():
                FILE_LENGTHS.setdefault(crc, info.file_size)
        games = games + hacks
    else:
        print('skipping the HBMAME hacks (%s): no --hbmame folder'
              % ', '.join(h['name'] for h in hbmame_sets.HACKS), file=sys.stderr)
    written = []
    for g in games:
        gz = hack_zips.get(g.name, zips)     # a hack reads its own zip
        gid = L.game_id(g)
        cat, players, bnames, bdef = GAME_INFO[gid]
        top = parents[g.parent] if g.parent else g
        dips = [d for d in inputs[g.inputs]['DSW'] if d.name != 'Unused']
        unused = UNUSED_DIPS.get(g.name, [])
        missing = set(unused) - {d.name for d in dips}
        if missing:
            raise ValueError('%s: UNUSED_DIPS names not among its DIP switches: %s' % (g.name, sorted(missing)))
        dips = [d for d in dips if d.name not in unused]
        if g.name in hack_zips:
            zipattr = g.zipattr
        else:
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
        lines = [(d.name, dip_xml(d)) for d in dips] + CORE_DIPS
        for _, line in sorted(lines, key=lambda x: x[0].lower()):
            out.append(line)
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
        if getattr(g, 'hide_extras', False):
            # the OSD shows the hack's own Move List and View Secrets but no
            # Finishing Moves or Hidden Items: the game id with the flag, no
            # secrets table, no fight variables; the AI level word (Fixed AI
            # Difficulty stays)
            table, notes = tunit_secrets.hidden_table(gid)
            out.append('\t\t<!-- game id (rtl/tunit_secrets.sv): %s -->' % escape('; '.join(notes)))
            out.append('\t\t<part>')
            out += tunit_secrets.part_hex(table)
            out.append('\t\t</part>')
            lv, lv_note = tunit_fmoves.level_part(
                mame_src.build_region(g.romset.regions['maincpu'], gz)) if gz else (b'', '')
            if lv:
                # at bytes 0x454-0x457 (rtl/tunit_fmoves.sv's words 0x22A-0x22B)
                out.append('\t\t<!-- %s (Fixed AI Difficulty) -->' % escape(lv_note))
                out.append('\t\t<part repeat="%d">00</part>'
                           % ((tunit_fmoves.CFG_BASE + tunit_fmoves.LVL_WORD) * 2 - len(table)))
                out.append('\t\t<part>')
                out += tunit_secrets.part_hex(lv)
                out.append('\t\t</part>')
        elif gz:
            prog = mame_src.build_region(g.romset.regions['maincpu'], gz)
            table, notes = tunit_secrets.build(gid, prog)
            out.append('\t\t<!-- game id and secrets table (rtl/tunit_secrets.sv): %s -->'
                       % escape('; '.join(notes)))
            out.append('\t\t<part>')
            out += tunit_secrets.part_hex(table)
            out.append('\t\t</part>')
            fm, fm_notes = tunit_fmoves.build(gid, prog, g.name)
            if fm:
                # at byte 0x400 (word 0x200), after the secrets table's room
                out.append('\t\t<!-- fight variables for the finishing moves (rtl/tunit_fmoves.sv): %s -->'
                           % escape('; '.join(fm_notes)))
                out.append('\t\t<part repeat="%d">00</part>' % (tunit_fmoves.CFG_BASE * 2 - len(table)))
                out.append('\t\t<part>')
                out += tunit_secrets.part_hex(fm)
                out.append('\t\t</part>')
            elif fm_notes:
                out.append('\t\t<!-- finishing moves: %s -->' % escape('; '.join(fm_notes)))
        else:
            out.append('\t\t<part>%02X</part>' % gid)
        out.append('\t</rom>')

        for idx in (0, 3):
            pieces = st[idx][0]
            md5 = L.render(pieces, gz)[1] if gz else 'None'
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

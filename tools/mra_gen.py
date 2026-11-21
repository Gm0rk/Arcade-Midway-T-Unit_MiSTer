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
    AI level word of Fixed AI Difficulty (tools/tunit_fmoves.py); for NBA Jam
    and TE, at 0x454, the sites of Fixed AI Difficulty (tools/tunit_nbaai.py);
    all need --zips: they are found in the set's own program ROM. A set with its own
    extras (hbmame_sets.py hide_extras: Mortal Kombat II Plus) has the game
    id with the flag instead of the table, and the OSD shows the hack's Move
    List and View Secrets (tools/tunit_plus.py) but no hidden items; it has
    the fight variables, the direct finisher sites and the Finishing Moves
    page like the other Mortal Kombat II sets, and the cheats,
  - the program and graphics ROMs (rom index 0) and the sound ROMs (rom
    index 3), laid out as tools/tunit_layout.py describes,
  - button names and NVRAM (16 KB). No DIP switches (<switches>): they are
    options of the core's OSD (System Options page, tools/tunit_dips.py), so
    Main_MiSTer draws no DIP Switches menu of its own.

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
import re
import struct
import sys
from xml.sax.saxutils import escape

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mame_src
import hbmame_sets
import tunit_layout as L
import tunit_secrets
import tunit_fmoves
import tunit_nbaai
import tunit_cheats

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

TIMEZONE = 'America/New_York'        # the maintainer's zone: the MRAs' date is the date there


def _nth_sunday(year, month, n):
    d = datetime.date(year, month, 1)
    d += datetime.timedelta(days=(6 - d.weekday()) % 7)             # the first Sunday
    return d + datetime.timedelta(weeks=n - 1)


def _eastern(utc):
    """The wall clock in US Eastern time at an aware UTC datetime (the rules
    since 2007: daylight time from the second Sunday of March, 02:00, to the
    first Sunday of November, 02:00). Used when the machine has no time zone
    database (Python's zoneinfo on Windows needs the tzdata package)."""
    start = datetime.datetime.combine(_nth_sunday(utc.year, 3, 2), datetime.time(7), tzinfo=utc.tzinfo)
    end = datetime.datetime.combine(_nth_sunday(utc.year, 11, 1), datetime.time(6), tzinfo=utc.tzinfo)
    return (utc + datetime.timedelta(hours=-4 if start <= utc < end else -5)).replace(tzinfo=None)


def today(tz=TIMEZONE, now=None):
    """YYYYMMDD: the date now in zone tz (US Eastern by default), not the machine's."""
    now = now or datetime.datetime.now(datetime.timezone.utc)
    try:
        from zoneinfo import ZoneInfo
        return now.astimezone(ZoneInfo(tz)).strftime('%Y%m%d')
    except (ImportError, LookupError):
        if tz != 'America/New_York':
            raise SystemExit('no time zone database for %s: install the tzdata package (pip install tzdata) or give --date' % tz)
        return _eastern(now).strftime('%Y%m%d')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('driver')
    ap.add_argument('outdir')
    ap.add_argument('--zips', help='folder with MAME zips (for md5)')
    ap.add_argument('--hbmame', help='folder with the HBMAME hack zips (tools/hbmame_sets.py)')
    ap.add_argument('--date', help='the MRAs\' <mratimestamp> (YYYYMMDD); default: today in --tz')
    ap.add_argument('--tz', default=TIMEZONE, help='IANA time zone of the default date (default %s)' % TIMEZONE)
    a = ap.parse_args()
    if not a.date:
        a.date = today(a.tz)
    elif not re.fullmatch(r'\d{8}', a.date):
        ap.error('--date is YYYYMMDD')

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

        cheat_out = []                  # the <cheats> block (every set's)
        prog = mame_src.build_region(g.romset.regions['maincpu'], gz) if gz else None
        out.append('\t<rom index="1">')
        if getattr(g, 'hide_extras', False):
            # the OSD shows the hack's own Move List and View Secrets but no Hidden
            # Items: the game id with the flag and the Attract Sound patches, no
            # codes; the fight variables, the direct finishers' sites and the AI
            # level word (the Finishing Moves page and Fixed AI Difficulty stay: the
            # hack is rev L3.1 with more code, its moves are L3.1's) and the cheats (below)
            table, notes = tunit_secrets.hidden_table(gid, prog or b'')
            out.append('\t\t<!-- game id (rtl/tunit_secrets.sv): %s -->' % escape('; '.join(notes)))
            out.append('\t\t<part>')
            out += tunit_secrets.part_hex(table)
            out.append('\t\t</part>')
            fm, fm_notes = tunit_fmoves.build(gid, prog, g.name) if gz else (b'', [])
            lv, lv_note = (b'', '') if fm or not gz else tunit_fmoves.level_part(prog)
            if fm:
                # at byte 0x400 (word 0x200), after the table's room
                out.append('\t\t<!-- fight variables for the finishing moves (rtl/tunit_fmoves.sv): %s -->'
                           % escape('; '.join(fm_notes)))
                out.append('\t\t<part repeat="%d">00</part>' % (tunit_fmoves.CFG_BASE * 2 - len(table)))
                out.append('\t\t<part>')
                out += tunit_secrets.part_hex(fm)
                out.append('\t\t</part>')
            elif lv:
                # at bytes 0x454-0x45B (rtl/tunit_fmoves.sv's words 0x22A-0x22D)
                out.append('\t\t<!-- %s (Fixed AI Difficulty) -->' % escape(lv_note))
                out.append('\t\t<part repeat="%d">00</part>'
                           % ((tunit_fmoves.CFG_BASE + tunit_fmoves.LVL_WORD) * 2 - len(table)))
                out.append('\t\t<part>')
                out += tunit_secrets.part_hex(lv)
                out.append('\t\t</part>')
        elif gz:
            table, notes = tunit_secrets.build(gid, prog)
            if getattr(g, 'move_list', None) == 'rev4':
                # the flag in word 0: the OSD's Move List shows rev 4.0's own pages
                table = bytearray(table)
                table[0:2] = struct.pack('<H', (table[0] | table[1] << 8) | tunit_secrets.MOVE_LIST_REV4)
                table = bytes(table)
                notes.append("the Move List shows rev 4.0's own pages (word 0 bit 9)")
            if getattr(g, 'mkplus_list', False):
                # the flag in word 0: the Move List shows Mortal Kombat Plus's own pages
                table = bytearray(table)
                table[0:2] = struct.pack('<H', (table[0] | table[1] << 8) | tunit_secrets.MKPLUS_LIST)
                table = bytes(table)
                notes.append("the Move List shows Mortal Kombat Plus's own pages (word 0 bit 10)")
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
            ai, ai_note = tunit_nbaai.part(prog) if gid in (L.G_NBAJAM, L.G_NBAJAMTE) else (b'', '')
            if ai:
                # at bytes 0x454-0x47F (rtl "Fixed AI Difficulty"): the hard routines' word, the program ROM words
                out.append('\t\t<!-- Fixed AI Difficulty (tools/tunit_nbaai.py): %s -->' % escape(ai_note))
                out.append('\t\t<part repeat="%d">00</part>' % (tunit_nbaai.TABLE_BASE - len(table)))
                out.append('\t\t<part>')
                out += tunit_secrets.part_hex(ai)
                out.append('\t\t</part>')
        else:
            out.append('\t\t<part>%02X</part>' % gid)
        out.append('\t</rom>')
        if prog is not None:
            ck, ck_notes = tunit_cheats.build(gid, prog, g.name, plus=getattr(g, 'hide_extras', False))
            if ck:
                # the OSD's Cheats menu (tools/tunit_cheats.py, rtl/tunit_cheats.sv)
                cheat_out.append('\t<!-- cheats (rtl/tunit_cheats.sv): %s -->' % escape('; '.join(ck_notes)))
                cheat_out.append('\t<cheats size="%d" max="%d">' % (tunit_cheats.CHEAT_SIZE, tunit_cheats.CHEAT_MAX))
                for name, data in ck:
                    cheat_out.append('\t\t<cheat name="%s">%s</cheat>' % (escape(name), ' '.join(data.hex().upper()[i:i + 4] for i in range(0, len(data) * 2, 4))))
                cheat_out.append('\t</cheats>')
            elif ck_notes:
                cheat_out.append('\t<!-- cheats: %s -->' % escape('; '.join(ck_notes)))

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
        out += cheat_out
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

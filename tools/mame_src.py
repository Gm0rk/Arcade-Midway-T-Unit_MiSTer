#!/usr/bin/env python3
"""
mame_src.py - read ROM sets, games and DIP switches from a MAME driver source

Shared by mra_gen.py (MRA files) and tunit_roms.py (ROM images for the
simulator). It understands the subset of MAME's driver macros the Midway
T-Unit driver (williams/midtunit.cpp) uses:

  ROM_START / ROM_END, ROM_REGION / ROM_REGION16_LE (with ROMREGION_ERASEFF),
  ROM_LOAD, ROM_LOAD16_BYTE, ROM_LOAD32_BYTE, ROM_RELOAD, ROM_FILL
  GAME(...) lines, INPUT_PORTS_START / PORT_START / PORT_DIPNAME /
  PORT_DIPSETTING

Comments are removed before parsing, and every macro is matched with
optional white space before its bracket ("ROM_RELOAD (" included: the Y Unit
generator once missed that spelling and left two games without sound).

A region is rebuilt exactly as MAME's ROM loader builds it (see
build_region): each load writes every `skip`-th byte starting at its
offset, a reload repeats the previous file at a new offset, and unloaded
bytes keep the region's fill value (0x00, or 0xFF with ROMREGION_ERASEFF).

Copyright (C) 2026 Gm0rk - GPL-3.0-or-later
"""

import re
import zipfile
import zlib

# --------------------------------------------------------------------------
# Source text helpers
# --------------------------------------------------------------------------

def strip_comments(text):
    """Remove C and C++ comments, keeping string literals intact."""
    out = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c == '"':
            # string literal: copy through the closing quote
            j = i + 1
            while j < n and text[j] != '"':
                j += 2 if text[j] == '\\' else 1
            out.append(text[i:j + 1])
            i = j + 1
        elif text.startswith('//', i):
            j = text.find('\n', i)
            i = n if j < 0 else j
        elif text.startswith('/*', i):
            j = text.find('*/', i + 2)
            # keep the line count so error messages stay meaningful
            out.append('\n' * text.count('\n', i, n if j < 0 else j))
            i = n if j < 0 else j + 2
        else:
            out.append(c)
            i += 1
    return ''.join(out)


def split_args(s):
    """Split a macro argument list at top-level commas."""
    args, depth, cur, instr = [], 0, [], False
    for c in s:
        if c == '"':
            instr = not instr
        if not instr:
            if c in '([':
                depth += 1
            elif c in ')]':
                depth -= 1
            elif c == ',' and depth == 0:
                args.append(''.join(cur).strip())
                cur = []
                continue
        cur.append(c)
    if cur or args:
        args.append(''.join(cur).strip())
    return args


def macro_calls(text, names):
    """Yield (name, [args]) for every call of one of `names`, in order.

    Matches `NAME (` with any white space before the bracket and finds the
    closing bracket by counting, so nested CRC(...)/SHA1(...) are fine.
    """
    pat = re.compile(r'\b(' + '|'.join(map(re.escape, names)) + r')\s*\(')
    pos = 0
    while True:
        m = pat.search(text, pos)
        if not m:
            return
        depth, j, instr = 1, m.end(), False
        while depth and j < len(text):
            c = text[j]
            if c == '"':
                instr = not instr
            elif not instr:
                if c == '(':
                    depth += 1
                elif c == ')':
                    depth -= 1
            j += 1
        yield m.group(1), split_args(text[m.end():j - 1]), m.start()
        pos = j


def num(s):
    """Evaluate a MAME numeric argument (hex/decimal, simple + and *)."""
    s = s.strip()
    return int(eval(s, {}, {}))   # only literal arithmetic appears here


def unquote(s):
    s = s.strip()
    if s.startswith('"') and s.endswith('"'):
        return s[1:-1]
    return s

# --------------------------------------------------------------------------
# Data model
# --------------------------------------------------------------------------

class Load:
    """One ROM file (or reload of it) placed into a region."""
    def __init__(self, name, crc, offset, length, skip, reload=False):
        self.name = name          # file name in the zip
        self.crc = crc            # CRC32 as 8 lower-case hex digits
        self.offset = offset      # region offset of the first byte
        self.length = length      # bytes taken from the file
        self.skip = skip          # region step between bytes (1, 2, 4)
        self.reload = reload      # ROM_RELOAD of the previous file

    def __repr__(self):
        return '%s%s@%X+%X/%d' % ('R:' if self.reload else '', self.name,
                                  self.offset, self.length, self.skip)


class Region:
    def __init__(self, tag, size, fill):
        self.tag = tag
        self.size = size
        self.fill = fill          # value of bytes no load writes
        self.loads = []
        self.fills = []           # ROM_FILL (offset, length, value)


class RomSet:
    def __init__(self, name):
        self.name = name
        self.regions = {}         # tag -> Region, in source order
        self.order = []


class Game:
    def __init__(self, year, name, parent, machine, inputs, init, desc, manuf):
        self.year = year
        self.name = name
        self.parent = parent if parent != '0' else None
        self.machine = machine
        self.inputs = inputs
        self.init = init
        self.desc = desc
        self.manuf = manuf
        self.romset = None


class DipSwitch:
    def __init__(self, mask, default, name):
        self.mask = mask
        self.default = default
        self.name = name
        self.settings = []        # (value, name)

# --------------------------------------------------------------------------
# Parsing
# --------------------------------------------------------------------------

ROM_MACROS = ['ROM_START', 'ROM_END', 'ROM_REGION', 'ROM_REGION16_LE',
              'ROM_REGION16_BE', 'ROM_REGION32_LE', 'ROM_LOAD',
              'ROM_LOAD16_BYTE', 'ROM_LOAD16_WORD', 'ROM_LOAD32_BYTE',
              'ROM_RELOAD', 'ROM_FILL', 'ROM_COPY', 'ROM_CONTINUE',
              'ROM_LOAD_OPTIONAL']


def parse_crc(arg):
    m = re.search(r'CRC\s*\(\s*([0-9a-fA-F]+)\s*\)', arg)
    return m.group(1).lower().zfill(8) if m else None


def parse_roms(text):
    """Return {setname: RomSet}."""
    sets = {}
    cur, region, last = None, None, None
    # ROM_END has no arguments; match it separately as a word
    tokens = []
    for name, args, pos in macro_calls(text, ROM_MACROS[:1] + ROM_MACROS[2:]):
        tokens.append((pos, name, args))
    for m in re.finditer(r'\bROM_END\b', text):
        tokens.append((m.start(), 'ROM_END', []))
    tokens.sort(key=lambda t: t[0])

    for pos, name, args in tokens:
        if name == 'ROM_START':
            cur = RomSet(args[0].strip())
            sets[cur.name] = cur
            region, last = None, None
        elif name == 'ROM_END':
            cur, region, last = None, None, None
        elif cur is None:
            continue
        elif name.startswith('ROM_REGION'):
            size = num(args[0])
            tag = unquote(args[1])
            flags = args[2] if len(args) > 2 else '0'
            fill = 0xFF if 'ERASEFF' in flags else 0x00
            region = Region(tag, size, fill)
            cur.regions[tag] = region
            cur.order.append(tag)
            last = None
        elif name in ('ROM_LOAD', 'ROM_LOAD16_BYTE', 'ROM_LOAD32_BYTE',
                      'ROM_LOAD_OPTIONAL'):
            skip = {'ROM_LOAD16_BYTE': 2, 'ROM_LOAD32_BYTE': 4}.get(name, 1)
            ld = Load(unquote(args[0]), parse_crc(args[3]), num(args[1]),
                      num(args[2]), skip)
            region.loads.append(ld)
            last = ld
        elif name == 'ROM_RELOAD':
            ld = Load(last.name, last.crc, num(args[0]), num(args[1]),
                      last.skip, reload=True)
            region.loads.append(ld)
        elif name == 'ROM_FILL':
            region.fills.append((num(args[0]), num(args[1]), num(args[2])))
        else:
            raise ValueError('%s: unsupported macro %s' % (cur.name, name))
    return sets


def parse_games(text):
    """Return [Game] in source order."""
    games = []
    for name, args, pos in macro_calls(text, ['GAME']):
        if len(args) < 10:
            continue
        g = Game(args[0], args[1], args[2], args[3], args[4], args[6],
                 unquote(args[9]), unquote(args[8]))
        games.append(g)
    return games


def parse_inputs(text):
    """Return {portset: {port_tag: [DipSwitch]}} for every port block."""
    result = {}
    for m in re.finditer(r'INPUT_PORTS_START\s*\(\s*(\w+)\s*\)(.*?)INPUT_PORTS_END',
                         text, re.S):
        ports = {}
        port, dip = None, None
        for name, args, pos in macro_calls(m.group(2),
                                           ['PORT_START', 'PORT_DIPNAME',
                                            'PORT_DIPSETTING']):
            if name == 'PORT_START':
                port = unquote(args[0])
                ports[port] = []
                dip = None
            elif name == 'PORT_DIPNAME':
                dip = DipSwitch(num(args[0]), num(args[1]),
                                dip_text(args[2]))
                ports[port].append(dip)
            elif name == 'PORT_DIPSETTING':
                dip.settings.append((num(args[0]), dip_text(args[1])))
        result[m.group(1)] = ports
    return result


DEF_STR = {
    'Off': 'Off', 'On': 'On', 'Unused': 'Unused', 'Coinage': 'Coinage',
    'Players': 'Players', 'USA': 'USA', 'French': 'French',
    'German': 'German', 'Free_Play': 'Free Play', 'None': 'None',
    'Unknown': 'Unknown',
}


def dip_text(arg):
    arg = arg.strip()
    m = re.match(r'DEF_STR\s*\(\s*(\w+)\s*\)', arg)
    if m:
        return DEF_STR.get(m.group(1), m.group(1).replace('_', ' '))
    return unquote(arg)


def parse_driver(path):
    text = strip_comments(open(path, encoding='utf-8').read())
    sets = parse_roms(text)
    games = parse_games(text)
    inputs = parse_inputs(text)
    for g in games:
        g.romset = sets[g.name]
    return games, sets, inputs

# --------------------------------------------------------------------------
# Zip access and region building
# --------------------------------------------------------------------------

class RomZips:
    """Finds ROM files by CRC (then by name) in a list of zip files, the way
    Main_MiSTer does for merged sets."""

    def __init__(self, paths):
        self.by_crc = {}
        self.by_name = {}
        for p in paths:
            z = zipfile.ZipFile(p)
            for info in z.infolist():
                crc = '%08x' % info.CRC
                self.by_crc.setdefault(crc, (z, info))
                self.by_name.setdefault(info.filename.split('/')[-1], (z, info))

    def read(self, name, crc):
        hit = self.by_crc.get(crc) or self.by_name.get(name)
        if hit is None:
            raise FileNotFoundError('%s (crc %s) not in the zips' % (name, crc))
        z, info = hit
        data = z.read(info)
        if crc and '%08x' % (zlib.crc32(data) & 0xffffffff) != crc:
            raise ValueError('%s: CRC mismatch' % name)
        return data


def build_region(region, zips):
    """Rebuild a ROM region byte for byte as MAME loads it."""
    buf = bytearray([region.fill]) * region.size
    for off, length, value in region.fills:
        buf[off:off + length] = bytes([value]) * length
    for ld in region.loads:
        data = zips.read(ld.name, ld.crc)[:ld.length]
        if len(data) < ld.length:
            # MAME repeats a short file to fill the requested length
            data = (data * (ld.length // max(1, len(data)) + 1))[:ld.length]
        buf[ld.offset:ld.offset + ld.length * ld.skip:ld.skip] = data
    return bytes(buf)

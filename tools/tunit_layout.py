#!/usr/bin/env python3
"""
tunit_layout.py - how a MAME T-Unit ROM set is laid out for the core

One place that says which MAME region bytes go where in the two ROM
downloads the core receives, used by mra_gen.py (to write the MRA parts) and
tunit_roms.py (to build the same streams for the simulator and check them
against MAME's regions).

Download streams (ioctl index) and where the core stores them in SDRAM:

  index 0  -> SDRAM 0x000000
    0x000000  program ROM, 1 MB (MAME "maincpu", 16-bit little endian)
    0x100000  graphics ROM (MAME "video"): the loaded part only, up to 12 MB.
              The core returns 0 above the loaded size, as MAME's region does.
  index 3  -> SDRAM 0xD00000
    ADPCM board:
      0x000000  sound CPU ROM: MAME "adpcm:cpu" 0x10000-0x4FFFF (256 KB)
      0x040000  OKI samples: MAME "adpcm:oki" (1 MB)
    DCS board (Mortal Kombat II):
      0x000000  sound data ROMs packed: MAME "dcs" holds one ROM byte in the
                low half of each 16-bit word, each 512 KB ROM twice (a
                ROM_RELOAD 1 MB further on). Word address w of the region is
                ROM byte {w[22:20], w[18:0]} here: 6 x 512 KB = 3 MB.

Each stream is a list of pieces, in order:
  ('file',  name, crc, start, length)          bytes of one file
  ('ileave', width, [(name, crc, lane)], length) N files byte-interleaved
                                                (MAME ROM_LOAD16/32_BYTE)
  ('fill',  value, count)                       constant bytes

Copyright (C) 2026 Gm0rk - GPL-3.0-or-later
"""

SDRAM_GFX   = 0x100000      # graphics in SDRAM (index 0 offset)
SDRAM_SOUND = 0xD00000      # index 3 base in SDRAM
GFX_MAX     = 0xC00000      # MAME "video" region size

# --------------------------------------------------------------------------
# Game table: the core's game id (MRA rom index 1) for each MAME set
# --------------------------------------------------------------------------

G_MK, G_MKTURBO, G_MK2, G_NBAJAM, G_NBAJAMTE, G_JDREDDP = range(6)

def game_id(game):
    name, init = game.name, game.init
    if init == 'init_mktunit':
        return G_MK
    if init == 'init_mkturbo':
        return G_MKTURBO
    if init == 'init_mk2':
        return G_MK2
    if init == 'init_nbajam':
        return G_NBAJAM
    if init == 'init_nbajamte':
        return G_NBAJAMTE
    if init == 'init_jdreddp':
        return G_JDREDDP
    raise ValueError('%s: unknown board configuration %s' % (name, init))


def uses_dcs(romset):
    return 'dcs' in romset.regions

# --------------------------------------------------------------------------
# Region slices to pieces
# --------------------------------------------------------------------------

def linear_pieces(region, start, end):
    """Pieces for region bytes [start, end) of a byte-wide region
    (ROM_LOAD and ROM_RELOAD with no skip)."""
    loads = sorted([l for l in region.loads if l.skip == 1],
                   key=lambda l: l.offset)
    if any(l.skip != 1 for l in region.loads):
        raise ValueError('%s: interleaved loads in a linear region' % region.tag)
    pieces, pos = [], start
    while pos < end:
        cover = [l for l in loads if l.offset <= pos < l.offset + l.length]
        if cover:
            l = cover[-1]          # a later load overwrites an earlier one
            stop = min(end, l.offset + l.length)
            # a later load starting inside this one cuts it short
            for o in loads:
                if o is not l and pos < o.offset < stop and loads.index(o) > loads.index(l):
                    stop = o.offset
            pieces.append(('file', l.name, l.crc, pos - l.offset, stop - pos))
            pos = stop
        else:
            nxt = min([l.offset for l in loads if l.offset > pos] + [end])
            pieces.append(('fill', region.fill, nxt - pos))
            pos = nxt
    return pieces


def interleaved_pieces(region, width, end):
    """Pieces for region bytes [0, end) of a region filled by
    ROM_LOAD16_BYTE (width 2) or ROM_LOAD32_BYTE (width 4) groups."""
    groups = {}
    for l in region.loads:
        # a ROM_RELOAD repeats its file in another group (NBA Jam
        # prototypes mirror 256 KB program ROMs into the 1 MB region)
        if l.skip != width:
            raise ValueError('%s: unexpected load %r' % (region.tag, l))
        groups.setdefault(l.offset - l.offset % width, []).append(l)
    pieces, pos = [], 0
    for base in sorted(groups):
        g = sorted(groups[base], key=lambda l: l.offset % width)
        if [l.offset % width for l in g] != list(range(width)):
            raise ValueError('%s: incomplete group at %X' % (region.tag, base))
        length = g[0].length
        if any(l.length != length for l in g):
            raise ValueError('%s: uneven group at %X' % (region.tag, base))
        if base > pos:
            pieces.append(('fill', region.fill, base - pos))
        elif base < pos:
            raise ValueError('%s: overlapping groups at %X' % (region.tag, base))
        pieces.append(('ileave', width, [(l.name, l.crc, l.offset % width) for l in g], length))
        pos = base + width * length
    if end is not None and pos < end:
        pieces.append(('fill', region.fill, end - pos))
    return pieces, pos


def dcs_pieces(region):
    """Packed DCS sound ROM (see the module header)."""
    prim = sorted([l for l in region.loads if not l.reload], key=lambda l: l.offset)
    pieces, pos = [], 0
    for l in prim:
        if l.skip != 2 or l.offset % 2:
            raise ValueError('dcs: unexpected load %r' % l)
        w = l.offset // 2
        packed = ((w >> 20) << 19) | (w & 0x7FFFF)
        if packed != pos:
            if packed < pos:
                raise ValueError('dcs: overlapping ROMs at %X' % packed)
            pieces.append(('fill', 0xFF, packed - pos))
            pos = packed
        pieces.append(('file', l.name, l.crc, 0, l.length))
        pos += l.length
    return pieces, pos


def dcs_unpack(packed, size):
    """Rebuild MAME's 'dcs' region from the packed stream (for checks)."""
    out = bytearray([0xFF]) * size
    for w in range(size // 2):
        p = ((w >> 20) << 19) | (w & 0x7FFFF)
        if p < len(packed):
            out[2 * w] = packed[p]
    return bytes(out)


def streams(romset):
    """Return {index: (pieces, total_length, description_lines)}."""
    r = romset.regions
    # index 0: program + graphics
    prog, plen = interleaved_pieces(r['maincpu'], 2, r['maincpu'].size)
    gfx, glen = interleaved_pieces(r['video'], 4, None)
    s0 = prog + gfx
    desc0 = ['0x000000 program ROM (1 MB, 16-bit little endian)',
             '0x100000 graphics ROM (%d MB of MAME "video", 32-bit interleaved)' % (glen >> 20)]
    # index 3: sound
    if uses_dcs(romset):
        s3, slen = dcs_pieces(r['dcs'])
        desc3 = ['0x000000 DCS sound data ROMs, packed (%d MB)' % (slen >> 20)]
    else:
        cpu = linear_pieces(r['adpcm:cpu'], 0x10000, 0x50000)
        oki = linear_pieces(r['adpcm:oki'], 0, 0x100000)
        s3 = cpu + oki
        desc3 = ['0x000000 sound CPU ROM (MAME region 0x10000-0x4FFFF)',
                 '0x040000 OKI M6295 samples (1 MB)']
    return {0: (s0, piece_len(s0), desc0, glen), 3: (s3, piece_len(s3), desc3, None)}


def piece_len(pieces):
    n = 0
    for p in pieces:
        if p[0] == 'file':
            n += p[4]
        elif p[0] == 'ileave':
            n += p[1] * p[3]
        else:
            n += p[2]
    return n


def render(pieces, zips):
    """Bytes of a stream, and its md5 the way Main_MiSTer computes it: every
    part's data in read order (repeats included) before interleaving."""
    import hashlib
    md5 = hashlib.md5()
    out = bytearray()
    for p in pieces:
        if p[0] == 'file':
            d = zips.read(p[1], p[2])[p[3]:p[3] + p[4]]
            md5.update(d)
            out += d
        elif p[0] == 'ileave':
            width, parts, length = p[1], p[2], p[3]
            block = bytearray(width * length)
            for name, crc, lane in parts:
                d = zips.read(name, crc)[:length]
                md5.update(d)
                block[lane::width] = d
            out += block
        else:
            d = bytes([p[1]]) * p[2]
            md5.update(d)
            out += d
    return bytes(out), md5.hexdigest()

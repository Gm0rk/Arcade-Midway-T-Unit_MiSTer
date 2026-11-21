#!/usr/bin/env python3
"""
tunit_dips.py - the games' DIP switches as OSD options (the System Options page)

    python3 tools/tunit_dips.py --gen      write rtl/tunit_dips_osd.svh and rtl/tunit_dsw.sv
    python3 tools/tunit_dips.py --check    those two files are what --gen writes (and the data is consistent)
    python3 tools/tunit_dips.py --vectors  test vectors for sim/dips_test (game id, status, the DIP word)

Until Build 104 the MRAs carried MAME's DIP switches (<switches>) and Main_MiSTer
drew its own DIP Switches menu, which cannot be put inside a page of the OSD.
The core now has the switches as options of its own (CONF_STR lines on page 3,
System Options), like the Wolf Unit core: the lines are here, and so is the
mapping of the options' status bits to the 16-bit DIP word the board reads
(rtl/tunit_dsw.sv). The MRAs no longer have <switches>.

The data below is what the 38 MRAs of Build 102 carried (LISTS: 9 different
lists of switches, SET_LIST: the list each set had). Each OSD option takes the
list's first value as the one that reads 0 (status bit 0 is the MAME default,
so a new or cleared configuration is MAME's default settings), then the other
values in MAME's order. A set shows the options of its list: the lines' hide
prefixes (OPTIONS, 'vis') test the OSD's menu mask bits (see the top level);
tools/osd_check.py checks every set's page against its list.

Service Credit and Tilt are triggers (T[12], T[13]) that close the cabinet
switch for 8 frames, as in the Wolf Unit core.

Copyright (C) 2026 Gm0rk - GPL-3.0-or-later
"""

import os
import random
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

PAGE = 3                    # the System Options page
SVC_BIT, TILT_BIT = 12, 13  # the Service Credit and Tilt triggers

# --------------------------------------------------------------------------
# The switch lists (what the Build 102 MRAs carried): default word as the MRA
# wrote it (bits 7-0, then bits 15-8), then (first bit, last bit, name, ids, values);
# values are 0, 1, 2 ... when left out.
# --------------------------------------------------------------------------

_YN = ['Off', 'On']
_TS = (0, 0, 'Test Switch', ['Off', 'On'], [1, 0])
_CSRC = ['Dipswitch', 'CMOS']
_COIN19 = ['USA-1', 'USA-2', 'USA-3', 'USA-4', 'USA-ECA', 'USA-Free Play', 'German-1', 'German-2', 'German-3',
           'German-4', 'German-5', 'German-ECA', 'German-Free Play', 'French-1', 'French-2', 'French-3', 'French-4',
           'French-ECA', 'French-Free Play']
_COIN19V = [31, 15, 23, 7, 27, 3, 29, 13, 21, 5, 25, 9, 1, 30, 14, 22, 6, 26, 2]
_COIN6 = ['1', '2', '3', '4', 'ECA', 'Free Play']
_COIN6V = [7, 3, 5, 1, 6, 0]
_CTR_NBA = ['1 Counter - 1 count/coin', '1 Counter - Totalizing', '2 Counters - 1 count/coin']
_CTR_JD = ['1 Counter - Totalizing', '2 Counters - 1 count/coin', '1 Counter - 1 count/coin']


def _mk(extra):
    base = [(12, 12, 'Attract Sound', _YN), (14, 14, 'Blood', _YN), (2, 6, 'Coinage', _COIN19, _COIN19V),
            (7, 7, 'Coinage Source', _CSRC, [1, 0]), (11, 11, 'Comic Book Offer', _YN),
            (1, 1, 'Counters', ['One', 'Two'], [1, 0]), (13, 13, 'Low Blows', _YN), _TS, (15, 15, 'Violence', _YN)]
    return base + extra


def _nba(extra):
    return [(8, 9, 'Coin Counters', _CTR_NBA, [3, 2, 1]), (12, 14, 'Coinage', _COIN6, _COIN6V),
            (15, 15, 'Coinage Source', _CSRC, [1, 0]), (10, 11, 'Country', ['USA', 'French', 'German'], [3, 2, 1]),
            (6, 6, 'Dollar Bill Validator', ['Installed', 'Not Present']), _TS] + extra


_BILL = (10, 10, 'Bill Validator', ['Installed', 'Not Present'])
_CIRC = (8, 8, 'Circuit Boards', ['2', '1'], [1, 0])
_PWR = (9, 9, 'Powerup Test', _YN)

LISTS = {
    'JD': ('FF,5C', [
        (5, 5, 'Blood', _YN), (8, 9, 'Coin Counters', _CTR_JD, [2, 1, 0]), (12, 14, 'Coinage', _COIN6, _COIN6V),
        (15, 15, 'Coinage Source', _CSRC, [1, 0]), (10, 11, 'Country', ['USA', 'French', 'German'], [3, 2, 1]),
        (7, 7, 'Freeze', _YN, [1, 0]), _TS, (6, 6, 'Validator', ['Installed', 'None'])]),
    'MK': ('7D,FE', _mk([])),
    'MKP': ('7D,FE', _mk([(8, 8, 'Skip Post Test', _YN, [1, 0])])),
    'MK2': ('7D,FC', _mk([_BILL, _CIRC, _PWR])),
    'MK2L1': ('7D,FC', _mk([])),
    'MK2L2': ('7D,FC', _mk([_BILL])),
    'NBA301': ('FD,7F', _nba([(7, 7, 'Players', ['2', '4']), (1, 1, 'Powerup Test', _YN),
                               (5, 5, 'Video Clips', _YN)])),
    'NBATE': ('FD,7F', _nba([(7, 7, 'Players', ['2', '4']), (1, 1, 'Powerup Test', _YN)])),
    'NBAOLD': ('FD,7F', _nba([])),
}

SET_LIST = {
    'jdreddp': 'JD', 'mk': 'MK', 'mk07': 'MKP', 'mk2': 'MK2', 'mk2chal': 'MK2', 'mk2r11': 'MK2L1',
    'mk2r14': 'MK2L1', 'mk2r20': 'MK2L2', 'mk2r21': 'MK2L2', 'mk2r30': 'MK2', 'mk2r31e': 'MK2',
    'mk2r32e': 'MK2', 'mk2r42': 'MK2', 'mk2r91': 'MK2', 'mk2s03': 'MK2', 'mk2s04': 'MK2', 'mk2s08': 'MK2',
    'mkr4': 'MK', 'mktturbo': 'MK', 'nbajam': 'NBA301', 'nbajam02': 'NBATE', 'nbajam03': 'NBATE',
    'nbajam04': 'NBATE', 'nbajam05': 'NBATE', 'nbajam07': 'NBATE', 'nbajamp1': 'NBAOLD', 'nbajamp2': 'NBAOLD',
    'nbajamr1': 'NBAOLD', 'nbajamr2': 'NBAOLD', 'nbajamte': 'NBATE', 'nbajamte1': 'NBATE', 'nbajamte2': 'NBATE',
    'nbajamte2a': 'NBATE', 'nbajamte3': 'NBATE', 'nbajamte3a': 'NBATE', 'nbajamte4': 'NBATE', 'nbajamten': 'NBATE',
    'nbajamtep2': 'NBATE',
}

# the board's game ids (rom index 1 word 0, bits 2-0) and the lists of each family
GAME_ID_FAMILY = {0: 'MK', 1: 'MK', 2: 'MK2', 3: 'NBA', 4: 'NBA', 5: 'JD'}
FAMILY_LISTS = {'MK': ['MK', 'MKP'], 'MK2': ['MK2', 'MK2L1', 'MK2L2'], 'NBA': ['NBA301', 'NBATE', 'NBAOLD'],
                'JD': ['JD']}
LIST_GAME_ID = {'MK': 0, 'MKP': 1, 'MK2': 2, 'MK2L1': 2, 'MK2L2': 2, 'NBA301': 3, 'NBATE': 4, 'NBAOLD': 3, 'JD': 5}

# the OSD says a counter setting in a few characters (the line has 28)
RENAME = {'1 Counter - 1 count/coin': 'One 1/1', '1 Counter - Totalizing': 'One Totalizing',
          '2 Counters - 1 count/coin': 'Two 1/1',
          # the validators: Off (not present) and On (installed), as the Wolf Unit core says it
          'Not Present': 'Off', 'None': 'Off', 'Installed': 'On'}

# --------------------------------------------------------------------------
# The OSD options: name, status bits, the MAME switch each family's list calls
# it, and the hide prefixes that show the line (one line of CONF_STR for each;
# the bits are the menu mask's, Arcade-Midway-T-Unit.sv):
#   3 Mortal Kombat or Mortal Kombat II, 4 Mortal Kombat (Plus: bit 2 too),
#   5 Mortal Kombat II, 6 NBA Jam or TE, 14 the set has Fixed AI Difficulty
#   (NBA Jam rev 3.01 and TE), 13 NBA TE, 15 Mortal Kombat II Plus, 12 and 2
#   the revision class of Mortal Kombat II (bit 12 is Plus's fighter number
#   bit 4, so Plus has a line of its own where it differs).
# --------------------------------------------------------------------------

_MK2_FULL = ['h5HFHCH2', 'h5hF']    # Mortal Kombat II revisions that use all three of its switches (class 0)
_MK2_BILL = ['h5HFHC', 'h5hF']      # and the ones that use the Bill Validator (not rev L1.1, L1.4)

OPTIONS = [
    dict(name='Attract Sound', st=(61, 61), use={'MK': 'Attract Sound', 'MK2': 'Attract Sound'}, vis=['h3']),
    dict(name='Bill Validator', st=(67, 67), use={'MK2': 'Bill Validator'}, vis=_MK2_BILL),
    dict(name='Blood', st=(62, 62), use={'MK': 'Blood', 'MK2': 'Blood', 'JD': 'Blood'}, vis=['H6']),
    dict(name='Circuit Boards', st=(68, 68), use={'MK2': 'Circuit Boards'}, vis=_MK2_FULL),
    dict(name='Coinage', st=(54, 58), use={'MK': 'Coinage', 'MK2': 'Coinage'}, vis=['h3']),
    dict(name='Coinage', st=(54, 56), use={'NBA': 'Coinage'}, vis=['h6']),       # NBA Jam: 1 is the default
    dict(name='Coinage', st=(54, 56), use={'JD': 'Coinage'}, vis=['H3H6']),     # Judge Dredd: 3 is the default
    dict(name='Coinage Source', st=(60, 60), use={'MK': 'Coinage Source', 'MK2': 'Coinage Source',
                                                    'NBA': 'Coinage Source', 'JD': 'Coinage Source'}, vis=['']),
    dict(name='Comic Book Offer', st=(65, 65), use={'MK': 'Comic Book Offer', 'MK2': 'Comic Book Offer'}, vis=['h3']),
    dict(name='Counters', st=(66, 66), use={'MK': 'Counters', 'MK2': 'Counters'}, vis=['h3']),
    dict(name='Counters', st=(86, 87), use={'NBA': 'Coin Counters', 'JD': 'Coin Counters'}, vis=['H3']),
    dict(name='Country', st=(88, 89), use={'NBA': 'Country', 'JD': 'Country'}, vis=['H3']),
    dict(name='Bill Validator', st=(67, 67), use={'NBA': 'Dollar Bill Validator', 'JD': 'Validator'}, vis=['H3']),
    dict(name='Freeze', st=(72, 72), use={'JD': 'Freeze'}, vis=['H3H6']),
    dict(name='Low Blows', st=(63, 63), use={'MK': 'Low Blows', 'MK2': 'Low Blows'}, vis=['h3']),
    dict(name='Players', st=(70, 70), use={'NBA': 'Players'}, vis=['h6hE']),
    dict(name='Powerup Test', st=(69, 69), use={'MK2': 'Powerup Test'}, vis=_MK2_FULL),
    dict(name='Powerup Test', st=(69, 69), use={'NBA': 'Powerup Test'}, vis=['h6hE']),
    dict(name='Skip Post Test', st=(68, 68), use={'MK': 'Skip Post Test'}, vis=['h4h2']),
    dict(name='Test Switch', st=(59, 59), use={'MK': 'Test Switch', 'MK2': 'Test Switch', 'NBA': 'Test Switch',
                                                'JD': 'Test Switch'}, vis=['']),
    dict(name='Video Clips', st=(71, 71), use={'NBA': 'Video Clips'}, vis=['h6hEHD']),
    dict(name='Violence', st=(64, 64), use={'MK': 'Violence', 'MK2': 'Violence'}, vis=['h3']),
]
TRIGGERS = [('Service Credit', SVC_BIT), ('Tilt', TILT_BIT)]


def default_word(s):
    lo, hi = s.split(',')
    return int(lo, 16) | int(hi, 16) << 8


def switch_of(listname, mame_name):
    """(lo, hi, ids, values) of a switch of a list, or None."""
    for t in LISTS[listname][1]:
        if t[2] == mame_name:
            vals = t[4] if len(t) > 4 else list(range(len(t[3])))
            return t[0], t[1], t[3], vals
    return None


def osd_ids(listname, mame_name):
    """The OSD's values of a switch, the default first, then MAME's order, and each one's MAME value."""
    lo, hi, ids, vals = switch_of(listname, mame_name)
    d = (default_word(LISTS[listname][0]) >> lo) & ((1 << (hi - lo + 1)) - 1)
    if d not in vals:
        raise ValueError('%s %s: the default %d is not a value' % (listname, mame_name, d))
    k = vals.index(d)
    order = [k] + [i for i in range(len(ids)) if i != k]
    return [RENAME.get(ids[i], ids[i]) for i in order], [vals[i] for i in order]


def option_values(o, family):
    """(OSD ids, MAME value of each) of an option for a family; the same for every list of the family that has it."""
    res = None
    for ln in FAMILY_LISTS[family]:
        if switch_of(ln, o['use'][family]) is None:
            continue
        r = osd_ids(ln, o['use'][family])
        if res is not None and r != res:
            raise ValueError('%s: the lists of %s disagree on %s' % (ln, family, o['name']))
        res = r
    if res is None:
        raise ValueError('%s: no list of %s has it' % (o['name'], family))
    return res


def option_ids(o):
    """The option's OSD ids: the same for every family that uses it."""
    res = None
    for fam in o['use']:
        r = option_values(o, fam)[0]
        if res is not None and r != res:
            raise ValueError('%s: the families disagree on the OSD values: %s / %s' % (o['name'], res, r))
        res = r
    return res


def switch_field(o, family):
    """(first bit, last bit) of the option's switch in the DIP word for a family."""
    res = None
    for ln in FAMILY_LISTS[family]:
        s = switch_of(ln, o['use'][family])
        if s is None:
            continue
        if res is not None and res != s[:2]:
            raise ValueError('%s: the lists of %s put %s in different bits' % (ln, family, o['name']))
        res = s[:2]
    return res


def _bits(st):
    return 'status[%d]' % st[0] if st[0] == st[1] else 'status[%d:%d]' % (st[1], st[0])


def osd_lines():
    """CONF_STR lines of the DIP options and the two triggers, in alphabetical order."""
    rows = []
    for i, o in enumerate(OPTIONS):
        ids = option_ids(o)
        n = o['st'][1] - o['st'][0] + 1
        if len(ids) > (1 << n):
            raise ValueError('%s: %d values do not fit %d status bits' % (o['name'], len(ids), n))
        if len(ids) <= (1 << (n - 1)) and n > 1:
            raise ValueError('%s: %d values need fewer than %d status bits' % (o['name'], len(ids), n))
        # the OSD row has 28 characters: ' name:' and the value (Main_MiSTer cuts the name short if not)
        if len(o['name']) + max(len(i) for i in ids) > 26:
            raise ValueError('%s: the row is too long for the OSD (%s)' % (o['name'], max(ids, key=len)))
        bits = '%d' % o['st'][0] if n == 1 else '%d:%d' % (o['st'][1], o['st'][0])
        for pre in o['vis']:
            rows.append((o['name'].lower(), i, '%sP%dO[%s],%s,%s;' % (pre, PAGE, bits, o['name'], ','.join(ids))))
    for j, (name, bit) in enumerate(TRIGGERS):
        rows.append((name.lower(), 100 + j, 'P%dT[%d],%s;' % (PAGE, bit, name)))
    rows.sort(key=lambda r: (r[0], r[1]))
    return [r[2] for r in rows]


# --------------------------------------------------------------------------
# rtl/tunit_dsw.sv
# --------------------------------------------------------------------------

def family_default(family):
    d = {default_word(LISTS[ln][0]) for ln in FAMILY_LISTS[family]}
    if len(d) != 1:
        raise ValueError('%s: the lists have different defaults' % family)
    return d.pop()


def _field_expr(o, fam, o_tables):
    ids, vals = option_values(o, fam)
    lo, hi = switch_field(o, fam)
    w = hi - lo + 1
    st = o['st']
    if w == 1:
        if len(ids) != 2:
            raise ValueError('%s: a bit with %d values' % (o['name'], len(ids)))
        if vals == [0, 1]:
            return 1, 'status[%d]' % st[0]
        if vals == [1, 0]:
            return 1, '~status[%d]' % st[0]
        raise ValueError('%s: values %s' % (o['name'], vals))
    # more bits: a table
    if all(vals[i] == vals[0] - i for i in range(len(vals))) and vals[0] == (1 << w) - 1 and len(vals) == (1 << w) - 1:
        pass
    name = '%s_%s' % (fam.lower(), re.sub(r'[^a-z0-9]+', '_', o['name'].lower()))
    o_tables.setdefault(name, (o, fam, ids, vals, lo, hi))
    return w, name


def gen_dsw():
    out = []
    out.append('// tunit_dsw.sv - the DIP switches the board reads, from the OSD options of the System Options page')
    out.append('// Generated by tools/tunit_dips.py --gen; do not edit.')
    out.append('//')
    out.append('// Each option\'s value 0 is MAME\'s default, so all-zero status bits are the default switches.')
    out.append('// Bits no option has keep MAME\'s default. The word is the board\'s 16-bit DIP input (bit 0 is')
    out.append('// the Test Switch, active low).')
    out.append('//')
    out.append('// Copyright (C) 2026 Gm0rk - GPL-3.0-or-later')
    out.append('')
    out.append('module tunit_dsw (')
    out.append('\tinput  [2:0]   game_id,')
    out.append('\tinput  [127:0] status,')
    out.append('\toutput reg [15:0] dsw')
    out.append(');')
    out.append('')
    words = {}
    tables = {}
    for fam in ('MK', 'MK2', 'NBA', 'JD'):
        default = family_default(fam)
        fields = {}                                  # first bit -> (width, expression)
        for o in OPTIONS:
            if fam not in o['use']:
                continue
            lo, hi = switch_field(o, fam)
            w, ex = _field_expr(o, fam, tables)
            if lo in fields and fields[lo][1] != ex:
                # the same switch from two options (none today)
                raise ValueError('%s: bit %d twice' % (fam, lo))
            fields[lo] = (hi - lo + 1, ex)
        parts = []
        b = 15
        while b >= 0:
            if b in [lo + w - 1 for lo, (w, ex) in fields.items()]:
                lo = [lo for lo, (w, ex) in fields.items() if lo + w - 1 == b][0]
                parts.append(fields[lo][1])
                b = lo - 1
            elif any(lo <= b < lo + w for lo, (w, ex) in fields.items()):
                raise ValueError('%s: fields overlap at bit %d' % (fam, b))
            else:
                parts.append("1'b%d" % (default >> b & 1))
                b -= 1
        words[fam] = parts
    for name, (o, fam, ids, vals, lo, hi) in sorted(tables.items()):
        w = hi - lo + 1
        out.append('// %s (%s): %s' % (o['name'], fam, ', '.join(ids)))
        out.append('reg [%d:0] %s;' % (w - 1, name))
        out.append('always @(*) begin')
        out.append('\tcase (%s)' % _bits(o['st']))
        for i, v in enumerate(vals):
            out.append("\t\t%d'd%d: %s = %d'd%d;" % (o['st'][1] - o['st'][0] + 1, i, name, w, v))
        out.append("\t\tdefault: %s = %d'd%d;" % (name, w, vals[0]))
        out.append('\tendcase')
        out.append('end')
        out.append('')
    for fam in ('MK', 'MK2', 'NBA', 'JD'):
        out.append('wire [15:0] dsw_%s = {%s};' % (fam.lower(), ', '.join(words[fam])))
    out.append('')
    out.append('always @(*) begin')
    out.append('\tcase (game_id)')
    out.append("\t\t3'd0, 3'd1: dsw = dsw_mk;       // Mortal Kombat (Plus too)")
    out.append("\t\t3'd2:       dsw = dsw_mk2;      // Mortal Kombat II (Plus and rev 4.0 too)")
    out.append("\t\t3'd3, 3'd4: dsw = dsw_nba;      // NBA Jam, NBA Jam Tournament Edition")
    out.append("\t\tdefault:    dsw = dsw_jd;       // Judge Dredd")
    out.append('\tendcase')
    out.append('end')
    out.append('')
    out.append('endmodule')
    return '\n'.join(out) + '\n'


def gen_osd():
    lines = osd_lines()
    o = ['// tunit_dips_osd.svh - the DIP switches as the options of the System Options page',
         '// Generated by tools/tunit_dips.py --gen; do not edit.',
         '//',
         '// Copyright (C) 2026 Gm0rk - GPL-3.0-or-later',
         '',
         '`define DIPS_OSD \\']
    for l in lines:
        o.append('\t"%s", \\' % l)
    o[-1] = o[-1].rstrip(' \\').rstrip(',')
    o.append('')
    return '\n'.join(o)


# --------------------------------------------------------------------------
# The test vectors: what the MRA's switches would give (the MAME values of
# the chosen ids over the default word) against the DIP word of the Verilog
# --------------------------------------------------------------------------

def vectors(n_random=400, seed=104):
    rnd = random.Random(seed)
    res = []
    for ln, (dflt, sw) in LISTS.items():
        gid = LIST_GAME_ID[ln]
        fam = GAME_ID_FAMILY[gid]
        dw = default_word(dflt)
        opts = [o for o in OPTIONS if fam in o['use'] and switch_of(ln, o['use'][fam])]
        def make(choice):
            status = 0
            word = dw
            for o, idx in choice:
                ids, _ = option_ids(o), None
                lo, hi = switch_of(ln, o['use'][fam])[:2]
                s_ids, s_vals = osd_ids(ln, o['use'][fam])
                # the expected value: the MRA value of the id the option's text names
                mame_ids, mame_vals = switch_of(ln, o['use'][fam])[2:]
                name = s_ids[idx]
                inv = {RENAME.get(x, x): v for x, v in zip(mame_ids, mame_vals)}
                val = inv[name]
                mask = ((1 << (hi - lo + 1)) - 1) << lo
                word = (word & ~mask) | (val << lo)
                status |= idx << o['st'][0]
            return gid, status, word
        res.append(make([]))
        for o in opts:
            for idx in range(len(option_ids(o))):
                res.append(make([(o, idx)]))
        for _ in range(n_random):
            res.append(make([(o, rnd.randrange(len(option_ids(o)))) for o in opts]))
    return res


def main():
    osd_p = os.path.join(ROOT, 'rtl', 'tunit_dips_osd.svh')
    dsw_p = os.path.join(ROOT, 'rtl', 'tunit_dsw.sv')
    if '--gen' in sys.argv:
        open(osd_p, 'w').write(gen_osd())
        open(dsw_p, 'w').write(gen_dsw())
        print('rtl/tunit_dips_osd.svh: %d lines, %d bytes of CONF_STR; rtl/tunit_dsw.sv'
              % (len(osd_lines()), sum(len(l) + 3 for l in osd_lines())))
        return
    if '--check' in sys.argv:
        bad = 0
        if open(osd_p).read() != gen_osd():
            print('rtl/tunit_dips_osd.svh is out of date')
            bad = 1
        if open(dsw_p).read() != gen_dsw():
            print('rtl/tunit_dsw.sv is out of date')
            bad = 1
        for s, ln in SET_LIST.items():
            if ln not in LISTS:
                print('%s: no list %s' % (s, ln))
                bad = 1
        print('tunit_dips: %d lines of CONF_STR (%d bytes), %d sets, %d lists' % (
            len(osd_lines()), sum(len(l) + 3 for l in osd_lines()), len(SET_LIST), len(LISTS)))
        sys.exit(bad)
    if '--vectors' in sys.argv:
        for gid, status, word in vectors():
            print('%d %032x %04x' % (gid, status, word))
        return
    print(__doc__)


if __name__ == '__main__':
    main()

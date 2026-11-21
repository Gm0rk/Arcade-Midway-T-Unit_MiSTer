#!/usr/bin/env python3
"""
osd_check.py - the OSD of every set, as Main_MiSTer draws it

    find mra -name '*.mra' -print0 | sort -z | xargs -0 python3 tools/mra_check.py \\
        --zips ZIPS --hbmame HBMAME --out DIR
    python3 tools/osd_check.py DIR

Reads the core's configuration string (the CONF_STR of
Arcade-Midway-T-Unit.sv with the macros of rtl/tunit_fmoves_osd.svh,
rtl/tunit_secrets_osd.svh and rtl/tunit_dips_osd.svh), builds the menu mask of
each set from its ROM index 1 table (mra_check.py --out writes
DIR/<set>_rom1.bin) the way the top level builds status_menumask, and applies
the hide prefixes the way Main_MiSTer does (menu.cpp: h<bit> shows a line when
the mask bit is set, H<bit> when it is clear; every prefix of a line must allow
it; a page's lines show inside the page when its entry shows; a page's entry
may be a line of another page: 'P5P4,Title;' is in page 5 and opens page 4).

For each of the 38 sets it checks

  - the main menu: Video Settings, Sound Options (Mortal Kombat and Mortal
    Kombat II only), System Options, Extras, Pause When OSD is Open, Reset and
    Reset and close OSD;
  - the Extras page lists the items the game has, in alphabetical order (Auto
    Finishing Moves, Cheats, EJB Menu, EJB Menu (Copyright Screen), Fixed AI
    Difficulty, Midway Menu, Moon Silhouettes, Move List, No CPU Assistance,
    Reptile Fight Next, Secret Audit Menu, Secret Audit Menu + Credits,
    Security Screen, View Secret Players, View Secrets) and, where they apply,
    the notes under them: a line that a game lacks is not there and the lines
    below it move up;
  - every OSD item that needs a patch or a code of the set's table (a code, a
    hidden item, Attract Sound, No CPU Assistance, Fixed AI Difficulty, which the
    NBA sets show when their table has the hard word's address at byte 0x454)
    shows only when the set's table has it: no item shows that the set lacks,
    so no "not available" message is needed;
  - the Sound Options page has Attract Sound and its "Reset to Apply Changes"
    line;
  - the System Options page lists the set's DIP switches (the options of
    tools/tunit_dips.py, the list the set's MRA had before Build 104: the
    same switches, values, default and order), Service Credit, Tilt and Service
    Menu;
  - no row is longer than the OSD's 28 characters, and the configuration string
    fits the 10,239 characters of hps_io.

The Finishing Moves page's lines are checked by sim/fmoves_test/osd_check.py.

Copyright (C) 2026 Gm0rk - GPL-3.0-or-later
"""

import glob
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
HEX = '0123456789ABCDEF'
sys.path.insert(0, HERE)
import tunit_dips                                                     # noqa: E402

CONF_MAX = 10239            # hps_io: the configuration string's characters
EXTRAS = 5                  # the Extras page
SYSTEM = 3                  # the System Options page

MASK_EXPR = ('{menu_plus, lvl_items, mask_d, menu_plus ? fm_line[4] : fm_class[1], fm_line[3:0], mask_7, menu_nba, osd_mk2, menu_mk, '
             'osd_list, fm_class[0] | menu_mkp, ~status[101], menu_cheats}')


def conf_lines():
    t = open(os.path.join(ROOT, 'Arcade-Midway-T-Unit.sv'), encoding='utf-8').read()
    if MASK_EXPR not in t:
        sys.exit('status_menumask is not the one this check models: ' + MASK_EXPR)
    i = t.index('localparam CONF_STR = {')
    body = t[i:t.index('};', i)]
    mac = {}
    for f in ('rtl/tunit_fmoves_osd.svh', 'rtl/tunit_secrets_osd.svh', 'rtl/tunit_dips_osd.svh'):
        s = open(os.path.join(ROOT, f), encoding='utf-8').read()
        for m in re.finditer(r'`define (\w+) ((?:\\\n|[^\n])*)', s):
            mac[m.group(1)] = m.group(2).replace('\\\n', '\n')
    strings = lambda x: re.findall(r'"((?:\\.|[^"\\])*)"', x)    # noqa: E731
    parts = []
    for tok in re.finditer(r'"((?:\\.|[^"\\])*)"|`(\w+)', body):
        if tok.group(1) is not None:
            parts.append(tok.group(1))
        elif tok.group(2) in mac:
            parts += strings(mac[tok.group(2)])
        else:
            parts.append('')                                       # `BUILD_DATE
    return [p.replace('\\\\', '\\').replace('\\"', '"').replace('\\n', '\n') for p in parts]


def parse(line):
    """(prefixes [(h or H, bit)], page, target, rest): page 0 is the main menu;
    target is the page the line opens when it is a page's entry (None for the
    others: 'P1,Title;' is in the main menu, 'P5P4,Title;' is in page 5); rest
    is the line after the page prefixes."""
    pre = []
    while len(line) > 1 and line[0] in 'hH' and line[1] in HEX:
        pre.append((line[0], HEX.index(line[1])))
        line = line[2:]
    page = 0
    target = None
    if len(line) > 1 and line[0] == 'P' and line[1].isdigit():
        page = int(line[1])
        line = line[2:]
        if line.startswith(','):
            target, page, line = page, 0, line[1:]
        elif len(line) > 2 and line[0] == 'P' and line[1].isdigit() and line[2] == ',':
            target, line = int(line[1]), line[3:]
    return pre, page, target, line


def shown(pre, mask):
    return all((mask >> b & 1) == (c == 'h') for c, b in pre)


def label(rest):
    """The item's name: 'O[19],Attract Sound,Default,Always On;' -> 'Attract Sound'."""
    m = re.match(r'[OTR]\[[^\]]*\],([^,;]*)', rest)
    if m:
        return m.group(1)
    m = re.match(r'-,([^;]*)', rest)
    if m:
        return m.group(1).strip()
    m = re.match(r'C,([^;]*)', rest)
    if m:
        return m.group(1)
    return None


def bit_of(rest):
    m = re.match(r'[OTR]\[(\d+)', rest)
    return int(m.group(1)) if m else None


class SetInfo:
    def __init__(self, name, data):
        self.name = name
        w = struct.unpack('<%dH' % (len(data) // 2), data)
        self.gid = w[0] & 7
        self.hide_ext = bool(w[0] & 0x100)
        self.rev4 = bool(w[0] & 0x200)
        self.mkp = bool(w[0] & 0x400)                      # Mortal Kombat Plus: its own pages (mkp_list)
        self.opts = set(w[3 + 3 * n] >> 12 for n in range(8)) - {0} if len(w) > 26 else set()
        self.code_avail = [len(w) > 26 and bool(w[26 + n] & 0x1FF) for n in range(2)]
        self.cls = w[0x43E // 2] if len(w) > 0x43E // 2 else 0
        self.lvl = len(w) > 0x45A // 2 and bool(w[0x454 // 2] | w[0x456 // 2])
        g = self.gid
        self.mk, self.mk2 = g in (0, 1), g == 2
        self.nba, self.te, self.jd = g in (3, 4), g == 4, g == 5

    def opt_avail(self, k):
        return ((k + 1) if k < 3 else (k + 3)) in self.opts

    def osd_items(self):
        """The set has a code or a hidden item (EJB Menu, Moon Silhouettes, ...)."""
        return bool((self.mk or self.mk2) and not self.hide_ext and
                    (any(self.code_avail) or self.opt_avail(0) or self.opt_avail(1)))

    def mask(self, fighter=0):
        """status_menumask as the top level builds it (Arcade-Midway-T-Unit.sv)."""
        menu_ejb = self.mk or self.mk2
        menu_cheats = self.mk or self.mk2 or self.nba or self.jd
        osd_list = menu_ejb
        osd_items = self.osd_items()
        osd_mk2 = self.mk2
        menu_plus = self.mk2 and self.hide_ext
        menu_rev4 = self.mk2 and not self.hide_ext and self.rev4
        mask_7 = self.jd or menu_rev4
        mask_d = self.te or osd_items
        lvl = (self.mk or self.mk2 or self.nba) and self.lvl
        fm_line = fighter if self.mk2 else fighter & 7
        cls = self.cls if self.mk2 else 0
        menu_mkp = self.mk and self.mkp
        bits = [menu_cheats, True, bool(cls & 1) or menu_mkp, osd_list, self.mk, osd_mk2, self.nba, mask_7]   # bit 1: CRT Adjust Off
        bits += [fm_line >> n & 1 for n in range(4)]
        bits += [(fm_line >> 4 if menu_plus else cls >> 1) & 1, mask_d, lvl, menu_plus]
        return sum(1 << n for n, b in enumerate(bits) if b)


def menu(lines, mask):
    """{page: [(label, bit, rest)]} of what shows, the main menu as page 0;
    a page's lines are listed when its entry shows (in a page that shows)."""
    reach = {0}
    again = True
    while again:
        again = False
        for pre, page, target, rest in lines:
            if target is not None and page in reach and target not in reach and shown(pre, mask):
                reach.add(target)
                again = True
    out = {0: []}
    for pre, page, target, rest in lines:
        if not shown(pre, mask) or page not in reach:
            continue
        if target is not None:
            out.setdefault(page, []).append(('>' + rest.rstrip(';'), None, rest))
        else:
            out.setdefault(page, []).append((label(rest), bit_of(rest), rest))
    return out


def dip_expect(set_name):
    """The DIP options a set shows: {name: (status bits, ids)} from its list of switches."""
    ln = tunit_dips.SET_LIST[set_name]
    fam = tunit_dips.GAME_ID_FAMILY[tunit_dips.LIST_GAME_ID[ln]]
    out = {}
    for o in tunit_dips.OPTIONS:
        if fam in o['use'] and tunit_dips.switch_of(ln, o['use'][fam]):
            n = o['st'][1] - o['st'][0] + 1
            bits = '%d' % o['st'][0] if n == 1 else '%d:%d' % (o['st'][1], o['st'][0])
            if o['name'] in out:
                raise ValueError('%s: %s twice' % (set_name, o['name']))
            out[o['name']] = (bits, tuple(tunit_dips.osd_ids(ln, o['use'][fam])[0]))
    return out


def row_errors(raw):
    """Rows that are too long for the OSD (28 characters a row: ' name:' and a value)."""
    errs = []
    for l in raw:
        pre, page, target, rest = parse(l)
        m = re.match(r'[OoT]\[[^\]]*\],([^;]*);', rest)
        if m and rest[0] in 'Oo' and '[ARC' not in rest:
            f = m.group(1).split(',')
            if len(f[0]) + max(len(v) for v in f[1:]) > 26:
                errs.append('row too long: %s (%s)' % (f[0], max(f[1:], key=len)))
        elif m or rest.startswith(('R[', 'C,', '-,')):
            t = re.match(r'(?:[RT]\[[^\]]*\]|C|-),([^,;]*)', rest)
            if t and len(t.group(1)) > 30:
                errs.append('row too long: %s' % t.group(1))
    return errs


def main():
    d = sys.argv[1] if len(sys.argv) > 1 else None
    if not d or not os.path.isdir(d):
        sys.exit(__doc__)
    raw = conf_lines()
    lines = [parse(l) for l in raw]
    errs = row_errors(raw)
    size = sum(len(l) for l in raw) + 6                  # the 6 characters of the build date (`BUILD_DATE)
    print('configuration string: %d of %d characters' % (size, CONF_MAX))
    if size > CONF_MAX:
        errs.append('the configuration string has %d characters (the limit is %d)' % (size, CONF_MAX))
    n = 0
    for f in sorted(glob.glob(os.path.join(d, '*_rom1.bin'))):
        name = os.path.basename(f)[:-9]
        s = SetInfo(name, open(f, 'rb').read())
        n += 1
        m = menu(lines, s.mask(0))
        main_items = [l for l, b, r in m[0] if l]
        names = set(main_items)

        def has(x):
            return x in names

        def want(x, cond):
            if has(x) != bool(cond):
                errs.append('%s: %s %s' % (name, x, 'shows but the set has none' if has(x) else 'is missing'))

        game = s.mk or s.mk2
        plus = s.mk2 and s.hide_ext
        # the main menu: its order is the layout's
        exp_main = ['>Video Settings'] + (['>Sound Options'] if game else []) + \
                   ['>System Options', '>Extras', 'Pause When OSD is Open', 'Reset', 'Reset and close OSD']
        if main_items != exp_main:
            errs.append('%s: the main menu is %s, not %s' % (name, main_items, exp_main))
        # the Extras page: the items the game has, alphabetical, then the notes
        items = []
        if game:
            items += ['Auto Finishing Moves', 'Move List']
        items.append('Cheats')
        if (game or s.nba) and s.lvl:
            items.append('Fixed AI Difficulty')
        if s.osd_items():
            items.append('EJB Menu')
            if s.mk:
                items += ['EJB Menu (Copyright Screen)', 'Moon Silhouettes', 'Reptile Fight Next']
            else:
                items.append('Security Screen')
        if s.nba:
            items += ['Midway Menu', 'View Secret Players']
        if s.te:
            items.append('No CPU Assistance')
        if s.jd:
            items += ['Secret Audit Menu', 'Secret Audit Menu + Credits']
        if plus:
            items.append('View Secrets')
        notes = (['Note: EJB Menu', 'Attract Mode Only'] if s.osd_items() else
                 ['Codes work in attract mode'] if s.jd else [])
        exp_extras = sorted(items, key=str.lower) + notes
        extras = [('>' + l[1:] if l.startswith('>') else l) for l, b, r in m.get(EXTRAS, []) if l]
        extras = [x[1:] if x.startswith('>') else x for x in extras]
        if extras != exp_extras:
            errs.append('%s: the Extras page is %s, not %s' % (name, extras, exp_extras))
        # the Finishing Moves page opens from the Extras page
        if (4 in m) != bool(game):
            errs.append('%s: the Finishing Moves page %s' % (name, 'shows' if 4 in m else 'is missing'))
        # every item with a code or a patch is in the table
        for page, its in m.items():
            for lab, bit, rest in its:
                if bit is None or lab is None:
                    continue
                ok = True
                if page == SYSTEM:
                    continue
                if bit == 14 and rest.startswith('R'):
                    ok = s.code_avail[0]
                elif bit == 15 and rest.startswith('R'):
                    ok = s.code_avail[1]
                elif bit == 41:
                    ok = s.mk and s.opt_avail(0)
                elif bit == 42:
                    ok = s.mk and s.opt_avail(1)
                elif bit == 16:
                    ok = s.mk2 and s.opt_avail(0)
                elif bit == 53:
                    ok = s.te and s.opt_avail(7)
                elif bit == 19:
                    ok = game and s.opt_avail(10)
                if not ok:
                    errs.append('%s: "%s" (page %d) shows but the set\'s table has no code or patch for it' % (name, lab, page))
        # the Sound Options page
        if game:
            snd = [l for l, b, r in m.get(2, [])]
            if 'Attract Sound' not in snd or 'Reset to Apply Changes' not in snd:
                errs.append('%s: the Sound Options page is %s' % (name, snd))
        # the System Options page: Dip Switches, the set's switches (alphabetical), Service Credit and Tilt, Service Menu
        sysrows = [(l, r) for l, b, r in m.get(SYSTEM, []) if l]
        got = {}
        order = []
        for l, r in sysrows:
            mo = re.match(r'O\[([\d:]+)\],([^,;]*),([^;]*);', r)
            if mo:
                if mo.group(2) in got:
                    errs.append('%s: System Options has %s twice' % (name, mo.group(2)))
                got[mo.group(2)] = (mo.group(1), tuple(mo.group(3).split(',')))
        for l, r in sysrows:
            if l not in ('Dip Switches', 'Service Menu'):
                order.append(l)
        try:
            exp = dip_expect(name)
        except KeyError:
            errs.append('%s: no list of DIP switches' % name)
            exp = {}
        exp_dip = {k: v for k, v in exp.items()}
        svc = {k: v for k, v in got.items() if k != 'Service Menu'}
        if svc != exp_dip:
            for k in sorted(set(svc) | set(exp_dip)):
                if svc.get(k) != exp_dip.get(k):
                    errs.append('%s: DIP switch %s is %s, not %s' % (name, k, svc.get(k), exp_dip.get(k)))
        names_dip = sorted(list(exp_dip) + ['Service Credit', 'Tilt'], key=str.lower)
        if order != names_dip:
            errs.append('%s: System Options lists %s, not %s' % (name, order, names_dip))
        if [l for l, r in sysrows][:1] != ['Dip Switches'] or [l for l, r in sysrows][-1:] != ['Service Menu']:
            errs.append('%s: System Options does not start with Dip Switches and end with Service Menu' % name)
        print('%-11s %s | Extras: %s | %d DIP switches' % (name, ', '.join(x.lstrip('>') for x in main_items[1:-3]),
                                                          ', '.join(e for e in extras if e not in notes),
                                                          len(exp_dip)))
    if errs:
        print('\n'.join(errs))
        print('FAIL: %d problems in %d sets' % (len(errs), n))
        sys.exit(1)
    print('osd_check: %d sets: every OSD item shown is one the set has' % n)


if __name__ == '__main__':
    main()

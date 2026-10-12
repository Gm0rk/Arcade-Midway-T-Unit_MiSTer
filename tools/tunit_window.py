#!/usr/bin/env python3
"""
tunit_window.py - the pages of the OSD's information window

rtl/tunit_window.sv draws one page over the picture, on the loaded game's
title screen dimmed so the text reads (after the Wolf Unit core's Move List
window):

  - Secret Player List (NBA Jam, NBA Jam TE): every secret player with the
    name, the initials and birthday that bring them up and the versions
    that have them (tools/tunit_splist.py has the players), then the cheat
    codes as the players enter them (tools/tunit_secrets.py CHEATS). The
    OSD option picks the page (Off, Page 1 to Page n).
  - Move List (Mortal Kombat, Mortal Kombat II): each fighter's special
    moves and finishing moves with the distance they need, in words (Close,
    Sweep, Jump, Half screen, Full screen; tools/tunit_fmoves.py has the
    moves and the distances). MK2 has a page per fighter (the OSD option
    picks the fighter); MK1's fighters have fewer moves, so several share a
    page (the option picks List 1 or List 2).

A page is 30 rows of 56 characters; a row is a list of segments, runs of
text in one colour (the blanks between them are not stored). ROM images
for $readmemh:

    rtl/tunit_window_row.hex   1024 x 11 bits, address {page, row}: the
                               row's first segment (0: empty row)
    rtl/tunit_window_seg.hex   2048 x 28 bits, a segment: [12:0] its first
                               character in the text ROM, [18:13] its
                               length, [24:19] its column, [26:25] its
                               colour (0 white, 1 yellow, 2 cyan, 3 gray),
                               [27] the row's last segment
    rtl/tunit_window_text.hex  8192 x 7 bits: the character codes - 32
                               (segments with the same text share it)
    rtl/tunit_window_font.hex  96 x 8 rows of 8 bits (bit x: column x),
                               characters 32-127: the MiSTer OSD's font
                               (Main_MiSTer charrom.cpp, GPL-3.0)
    rtl/tunit_window_bg.hex    4 x 127 x 200 entries of 5 bits: the
                               backgrounds (NBA Jam, TE, MK, MK2) at half the
                               picture's resolution, a palette index each
    rtl/tunit_window_pal.hex   128 x 24 bits: the palettes, 32 colours per
                               background (RGB, already dimmed)
    rtl/tunit_window_pages.svh the first page and the page count of each
                               list (top level)

The backgrounds come from captures of the title screens (--bg; the 4:3
picture is taken from the middle of the image, so a 1920 x 1080 capture
with black bars works as it is): scaled to 200 x 127, dimmed to DIM, 32
colours (median cut, no dither).

Usage:
    tunit_window.py --write                     write the text ROM images
    tunit_window.py --bg NJ.png TE.png MK.png MK2.png
                                                write the backgrounds
    tunit_window.py --check                     the ROM images against the sources
    tunit_window.py --show [PAGE|all]           print pages as text

Copyright (C) 2026 Gm0rk - GPL-3.0-or-later
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import tunit_splist as sl   # noqa: E402
import tunit_fmoves as fm   # noqa: E402
import tunit_secrets as ts  # noqa: E402

OUT = {k: os.path.join(REPO, 'rtl', 'tunit_window_%s.hex' % k)
       for k in ('row', 'seg', 'text', 'font', 'bg', 'pal')}
OUT_SVH = os.path.join(REPO, 'rtl', 'tunit_window_pages.svh')

COLS, ROWS = 56, 30
LEFT, RIGHT = 1, 54                 # the columns text uses
PAGES = 32                          # row ROM pages
SEG_SIZE = 2048                     # segment ROM entries
TEXT_SIZE = 8192                    # text ROM characters
WHITE, YELLOW, CYAN, GRAY = range(4)
BG_W, BG_H, BG_COLOURS = 200, 127, 32
BG_GAMES = ('nbajam', 'nbajamte', 'mk', 'mk2')
DIM = 0.30                          # background brightness

# Main_MiSTer charrom.cpp, characters 32-127: 8 bytes each, byte i column i,
# bit b row b (the top row bit 0)
FONT = [
    "0000000000000000 00006F6F00000000 0503000005030000 147F7F147F140000",  #  !"#
    "48DC745C76240000 4C2A166854320000 20744A5E34605000 0000050300000000",  # $%&'
    "00001C3E63410000 41633E1C00000000 082A1C1C2A080000 08083E3E08080000",  # ()*+
    "0000A06000000000 0808080808080000 0000606000000000 6030180C06030000",  # ,-./
    "3E7F415D7F3E0000 00017F7F00000000 717949494F460000 414949497F360000",  # 0123
    "1C1E137F7F100000 4F4F494979310000 3E7F494979310000 0101797D07030000",  # 4567
    "367F49497F360000 464F49497F3E0000 00006C6C00000000 0000AC6C00000000",  # 89:;
    "081C366341000000 0014141414000000 004163361C080000 060751590F060000",  # <=>?
    "3E7F415D5F4E0000 7E7F09097F7E0000 7F7F49497F360000 3E7F414141410000",  # @ABC
    "7F7F41417F3E0000 3E7F494941410000 7E7F090901010000 3E7F41497B7B0000",  # DEFG
    "7F7F08087F7F0000 00007F7F00000000 606040407F3F0000 7F7F081C77630000",  # HIJK
    "3F7F404040400000 7F7F060C067F7F00 7F7F0C187F7F0000 7E7F41417F3F0000",  # LMNO
    "7F7F09090F060000 7E7F41F1FF3F0000 7F7F09097F760000 464F494979310000",  # PQRS
    "01017F7F01010000 3F7F40407F7F0000 1F3F60603F1F0000 7F7F3018307F7F00",  # TUVW
    "63771C1C77630000 070F78780F070000 6171594D47430000 00007F7F41410000",  # XYZ[
    "03060C1830600000 41417F7F00000000 080C0603060C0800 8080808080808000",  # \\]^_
    "0000030500000000 387C44447C7C0000 3F7F44447C380000 387C444444440000",  # `abc
    "387C44447F3F0000 387C54545C580000 00087E7F09010000 98BCA4A4FC780000",  # defg
    "7F7F04047C780000 00007D7D00000000 8080FD7D00000000 7F7F10107C6C0000",  # hijk
    "00007F7F40000000 7C7C0C180C7C7800 7C7C04047C780000 387C44447C380000",  # lmno
    "F8FC44447C380000 387C4444FCF80000 7C7C080404040000 485C545474240000",  # pqrs
    "00043F7F44400000 3C7C40407C7C0000 1C3C60603C1C0000 3C7C6030607C3C00",  # tuvw
    "6C6C10106C6C0000 9CBCA0A0FC7C0000 646454544C4C0000 08083E7741410000",  # xyz{
    "0000777700000000 4141773E08080000 1008081810100800 7F7F7F7F7F7F7F00",  # |}~.
]


def font_rows():
    """96 x 8 row bytes (bit x: column x)"""
    cols = [bytes.fromhex(w) for line in FONT for w in line.split()]
    assert len(cols) == 96, len(cols)
    return [[sum(((c[x] >> y) & 1) << x for x in range(8)) for y in range(8)] for c in cols]


# ----------------------------------------------------------------------------
# Rows: (column, [(text, colour)]) or None
# ----------------------------------------------------------------------------

def row(*segs, col=LEFT):
    return (col, [s for s in segs if s[0]])


def at(*cells):
    """A row from (column, text, colour) cells."""
    segs, k = [], LEFT
    for col, text, colour in cells:
        if col < k:
            raise SystemExit('cells overlap: %r' % (cells,))
        if col > k:
            segs.append((' ' * (col - k), WHITE))
            k = col
        segs.append((text, colour))
        k += len(text)
    return row(*segs)


def width(r):
    return r[0] + sum(len(t) for t, _ in r[1]) - 1 if r else 0


def wrap(text, width_):
    """Lines of at most width_ characters, broken after commas."""
    out, cur = [], ''
    for w in text.split(', '):
        add = (cur + ', ' + w) if cur else w
        if len(add) + (1 if cur else 0) > width_ and cur:
            out.append(cur + ',')
            cur = w
        else:
            cur = add
    out.append(cur)
    if any(len(line) > width_ for line in out):
        raise SystemExit('too long: ' + text)
    return out


def title_row(left, right):
    return at((LEFT, left, CYAN), (RIGHT + 1 - len(right), right, GRAY))


def compose(label, head, body, foot):
    """A page: head, body, blank rows, footer at the bottom."""
    rows = head + body + [None] * (ROWS - len(head) - len(body) - len(foot)) + foot
    if len(rows) > ROWS:
        raise SystemExit('%s: %d rows' % (label, len(rows)))
    for r in rows:
        if r and width(r) > RIGHT:
            raise SystemExit('%s: too wide: %r' % (label, ''.join(t for t, _ in r[1])))
    return (label, rows)


# ----------------------------------------------------------------------------
# Secret Player List (NBA Jam, TE)
# ----------------------------------------------------------------------------

C_NAME, C_INI, C_DAY, C_VER = 1, 20, 24, 33
W_NAME, W_VER = C_INI - C_NAME - 1, RIGHT - C_VER + 1

SP_FOOTER = [
    [('Enter initials for record keeping?', YELLOW), (' YES, then the', GRAY)],
    [('three initials (', GRAY), ('_', YELLOW), (' is ', GRAY), ('SPC', YELLOW),
     ('), the month and the day:', GRAY)],
    [('you play as that player.', GRAY)],
]
SP_FOOTER_GAME = {'nbajam': [('The prototypes have no secret players.', GRAY)],
                  'nbajamte': [('Rev 3.0 2-26 takes only the NBA players.', GRAY)]}


def player_rows(players, sets):
    """Each player's rows (a list per player: more than one when the
    initials or birthday differ between versions, or the versions wrap)."""
    with_table = set(v for p in players for v in p[4])
    out, last = [], None
    for full, screen, ini, day, ver in players:
        name = sl.label(full, screen)
        if len(name) > W_NAME:
            raise SystemExit('name too long: ' + name)
        vl = wrap(sl.versions(ver, sets, with_table), W_VER)
        rows = [at((C_NAME, name if name != last else '', WHITE), (C_INI, ini, WHITE), (C_DAY, day, YELLOW),
                   (C_VER, vl[0], GRAY))]
        rows += [at((C_VER, v, GRAY)) for v in vl[1:]]
        if name == last:
            out[-1] += rows
        else:
            out.append(rows)
        last = name
    return out


def paginate(groups, room):
    """Row groups (kept together) into pages of at most room rows, a blank
    row between groups that ask for one ((rows, gap))."""
    pg, cur = [], []
    for rows, gap in groups:
        need = len(rows) + (1 if gap and cur else 0)
        if cur and len(cur) + need > room:
            pg.append(cur)
            cur, need = [], len(rows)
        if gap and cur:
            cur.append(None)
        cur += rows
    pg.append(cur)
    return pg


def wrap_words(text, width_):
    """Lines of at most width_ characters, broken between words."""
    out, cur = [], ''
    for w in text.split(' '):
        if cur and len(cur) + 1 + len(w) > width_:
            out.append(cur)
            cur = w
        else:
            cur = (cur + ' ' + w) if cur else w
    out.append(cur)
    if any(len(line) > width_ for line in out):
        raise SystemExit('too long: ' + text)
    return out


C_CODE = LEFT + 2                   # a code's text under its name
CODE_FOOTER = [
    [('Press', YELLOW), (': ' + ts.CHEATS_NOTE.split(': ', 1)[1], GRAY)],
    [("The OSD's Cheat Codes & Hidden Items page does these", GRAY)],
]


def code_groups(game):
    """The codes of a game (tools/tunit_secrets.py CHEATS) as row groups: a
    section's heading with its first code, then each code (name and
    versions, the code under it)."""
    groups = []
    for head, items in ts.CHEATS[game]:
        for k, (name, how, ver) in enumerate(items):
            rows = [at((LEFT, name, WHITE), (RIGHT + 1 - len(ver), ver, GRAY))]
            rows += [at((C_CODE, line, YELLOW)) for line in wrap_words(how, RIGHT + 1 - C_CODE)]
            if k == 0:
                groups.append(([row((head, CYAN))] + rows, True))
            else:
                groups.append((rows, False))
    return groups


def nba_pages(game):
    """The Secret Player List window of nbajam or nbajamte: the secret
    players, then the cheat codes (the OSD option picks the page)."""
    data = sl.load()
    _, title, _, sets = [g for g in sl.GAMES if g[0] == game][0]
    sp_foot = [row(*f) for f in SP_FOOTER] + [row(*SP_FOOTER_GAME[game])]
    sp = paginate([(g, False) for g in player_rows(data[game], sets)], ROWS - 3 - 1 - len(sp_foot))
    cd_foot = [row(*f) for f in CODE_FOOTER]
    cd = paginate(code_groups(game), ROWS - 2 - 1 - len(cd_foot))
    n_all = len(sp) + len(cd)
    out = []
    for n, body in enumerate(sp):
        head = [title_row('SECRET PLAYERS', '%s  %d/%d' % (title, n + 1, n_all)), None,
                at((C_NAME, 'PLAYER', GRAY), (C_INI, 'INI', GRAY), (C_DAY, 'BIRTHDAY', GRAY),
                   (C_VER, 'VERSIONS', GRAY))]
        out.append(compose('%s players %d' % (game, n + 1), head, body, sp_foot))
    for n, body in enumerate(cd):
        head = [title_row('CHEAT CODES', '%s  %d/%d' % (title, len(sp) + n + 1, n_all)), None]
        out.append(compose('%s codes %d' % (game, n + 1), head, body, cd_foot))
    return out


# ----------------------------------------------------------------------------
# Move List (MK, MK2)
# ----------------------------------------------------------------------------

MK_TITLES = {'mk': 'MORTAL KOMBAT', 'mk2': 'MORTAL KOMBAT II'}
ML_NOTATION = [
    [('F', YELLOW), (' toward the opponent, ', GRAY), ('B', YELLOW), (' away, ', GRAY),
     ('X+Y', YELLOW), (' together', GRAY)],
    [('(X) Y', YELLOW), (' or ', GRAY), ('(X Y)', YELLOW), (': hold X while you enter Y, then let go', GRAY)],
]
ML_HOLD = [('(X 2 s)', YELLOW), (': hold X about 2 seconds, then let go', GRAY)]
ML_DISTANCE = [('Distance', YELLOW), (': ', GRAY), ('Sweep', YELLOW), (" = a sweep's reach, ", GRAY),
               ('Jump', YELLOW), (' = a jump away', GRAY)]
# the stage moves' stages (by the fighter's stage move kind), MK2's rule for
# friendships and babalities
ML_FOOTER_STAGE = {
    fm.K_MKPIT: [('The Pit', YELLOW), (' (all): D+HP, close, on The Pit stage only', GRAY)],
    fm.K_STAGE: [('Pit / Spikes', YELLOW), (': The Pit II and Kombat Tomb only', GRAY)],
    fm.K_PIT2: [('Pit', YELLOW), (': The Pit II only', GRAY)],
}
ML_FRIEND = [('Friendship, Babality', YELLOW), (': a round won without punches', GRAY)]


def morph_rows(morphs):
    """Shang Tsung's morphs in two columns"""
    half = (len(morphs) + 1) // 2
    left, right = morphs[:half], morphs[half:]
    nl = max(len(n) for n, _ in left) + 1
    nr = max(len(n) for n, _ in right) + 1 if right else 0
    out = []
    for k in range(half):
        n, i = left[k]
        cells = [(LEFT, n, WHITE), (LEFT + nl, i, YELLOW)]
        if k < len(right):
            n2, i2 = right[k]
            cells += [(LEFT + 28, n2, WHITE), (LEFT + 28 + nr, i2, YELLOW)]
        out.append(at(*cells))
    return out


def finishing(game, name, moves):
    """[(name, command, more, distance)] for a fighter: the OSD's moves, the
    left-out ones after the move they follow; more is a second line."""
    out = []
    extra = [e for f, after, e in fm.WINDOW_EXTRA.get(game, []) if f == name]
    after = {a: e for f, a, e in fm.WINDOW_EXTRA.get(game, []) if f == name}
    for mname, kind, cmd, prog, dmin, dmax, note in moves:
        more = (note, YELLOW) if note else None
        out.append((mname, cmd, more, fm.dist(dmin, dmax)))
        if mname in after:
            n, c, nt, a, b = after[mname]
            out.append((n, c, (nt, GRAY), fm.dist(a, b)))
            extra.remove(after[mname])
    if extra:
        raise SystemExit('%s %s: %r not placed' % (game, name, extra))
    return out


def special_rows(game, name, sp, col, cmd_col):
    """A fighter's special moves (not the morphs): name at col, command at
    cmd_col, a note after the command, under it, or under the name."""
    out = []
    for m, c in sp:
        note = fm.SPECIAL_NOTES.get((game, name, m))
        r = at((col, m, WHITE), (cmd_col, c, YELLOW))
        if note and width(r) + 2 + len(note) <= RIGHT:
            r = at((col, m, WHITE), (cmd_col, c, YELLOW), (cmd_col + len(c) + 2, note, GRAY))
            note = None
        out.append(r)
        if note:
            out.append(at((cmd_col if cmd_col + len(note) - 1 <= RIGHT else col + 2, note, GRAY)))
    return out


def mk2_pages():
    """MK2's Move List: a page per fighter (the Move List option's order)."""
    out = []
    for (name, cid, moves), (n2, sp) in zip(fm.fighters('mk2'), fm.specials('mk2')):
        assert name == n2
        head = [title_row(name.upper(), MK_TITLES['mk2']), None, row(('SPECIAL MOVES', CYAN))]
        plain = sp[:next((k for k, (_, c) in enumerate(sp) if c is None), len(sp))]
        morphs = sp[len(plain) + 1:]
        nw = max(16, max(len(m) for m, _ in plain) + 2)
        body = special_rows('mk2', name, plain, LEFT, LEFT + nw)
        if morphs:
            body.append(row((sp[len(plain)][0].rstrip(':').upper(), CYAN)))
            body += morph_rows(morphs)
        body.append(None)
        fin = finishing('mk2', name, moves)
        fw = max(len(n) for n, _, _, _ in fin) + 2
        iw = max(len(c) for _, c, _, _ in fin) + 2
        dw = max(len(d) for _, _, _, d in fin)
        if max(fw, nw) + iw + dw <= RIGHT - LEFT + 1:
            fw = max(fw, nw)               # the commands under the special moves'
        if fw + iw + dw > RIGHT - LEFT + 1:
            raise SystemExit('mk2 %s: the finishing moves need %d columns' % (name, fw + iw + dw))
        cd = RIGHT + 1 - max(dw, len('DISTANCE'))
        body.append(at((LEFT, 'FINISHING MOVES', CYAN), (cd, 'DISTANCE', CYAN)))
        for n, c, more, d in fin:
            body.append(at((LEFT, n, WHITE), (LEFT + fw, c, YELLOW), (cd, d, GRAY)))
            if more:
                body.append(at((LEFT + fw, more[0], more[1])))
        stage = [ML_FOOTER_STAGE[k] for k in (fm.K_STAGE, fm.K_PIT2) if any(m[1] == k for m in moves)]
        foot = [row(*f) for f in ML_NOTATION + [ML_HOLD, ML_DISTANCE] + stage + [ML_FRIEND]]
        out.append(compose('mk2 %s' % name, head, body, foot))
    return out


def mk_pages():
    """MK's Move List: as many fighters to a page as fit (the Character
    option's order), each with the special moves and the fatality; The Pit,
    the same for all, in the footer."""
    foot = [row(*f) for f in ML_NOTATION + [ML_DISTANCE, ML_FOOTER_STAGE[fm.K_MKPIT]]]
    blocks = []
    fighters = [(n, [m for m in moves if m[1] != fm.K_MKPIT]) for n, _, moves in fm.fighters('mk')]
    c_name = LEFT + 2
    w_name = max(len(m) for (_, sp) in fm.specials('mk') for m, _ in sp)
    w_name = max([w_name] + [len('Fatality: ' + m[0]) for _, fat in fighters for m in fat])
    c_cmd = c_name + w_name + 2
    dists = [fm.dist(m[4], m[5]) for _, fat in fighters for m in fat]
    c_dist = RIGHT + 1 - max(max(len(d) for d in dists), len('DISTANCE'))
    for (name, fat), (n2, sp) in zip(fighters, fm.specials('mk')):
        assert name == n2
        b = [row((name.upper(), CYAN))] + special_rows('mk', name, sp, c_name, c_cmd)
        for mname, kind, cmd, prog, dmin, dmax, note in fat:
            b.append(at((c_name, 'Fatality: ' + mname, WHITE), (c_cmd, cmd, YELLOW), (c_dist, fm.dist(dmin, dmax), GRAY)))
        blocks.append((name, b))
    room = ROWS - 3 - 1 - len(foot)
    groups, cur = [], []
    for name, b in blocks:
        rows_ = sum(len(x) + 1 for _, x in cur) + len(b)
        if cur and rows_ > room:
            groups.append(cur)
            cur = []
        cur.append((name, b))
    groups.append(cur)
    out = []
    for k, g in enumerate(groups):
        body = []
        for name, b in g:
            body += ([None] if body else []) + b
        head = [title_row('MOVE LIST' + ('  %d/%d' % (k + 1, len(groups)) if len(groups) > 1 else ''),
                          MK_TITLES['mk']), None,
                at((c_name, 'MOVE', GRAY), (c_cmd, 'COMMAND', GRAY), (c_dist, 'DISTANCE', GRAY))]
        out.append(compose('mk %s' % ', '.join(n for n, _ in g), head, body, foot))
    return out


# ----------------------------------------------------------------------------
# All pages, the ROM images
# ----------------------------------------------------------------------------

LISTS = [('nbajam', lambda: nba_pages('nbajam')), ('nbajamte', lambda: nba_pages('nbajamte')),
         ('mk', mk_pages), ('mk2', mk2_pages)]


def pages():
    """[(label, rows)] in page order, and {list: (first page, pages)}"""
    out, first = [], {}
    for name, make in LISTS:
        p = make()
        first[name] = (len(out), len(p))
        out += p
    return out, first


def page_counts():
    """{list: pages} for the OSD options (tunit_secrets.py, tunit_fmoves.py)"""
    _, first = pages()
    return {name: n for name, (p0, n) in first.items()}


def segments(r):
    """a row's runs of text: [(column, text, colour)]"""
    out, k = [], r[0]
    for t, colour in r[1]:
        lead = len(t) - len(t.lstrip(' '))
        if t.strip():
            out.append((k + lead, t.strip(), colour))
        k += len(t)
    return out


def images():
    text, seg, rows, lists = '', [0], [], {}
    pg, first = pages()
    if len(pg) > PAGES:
        raise SystemExit('%d pages (room for %d)' % (len(pg), PAGES))
    for _, page_rows in pg:
        for r in page_rows + [None] * (32 - ROWS):
            sg = tuple(segments(r)) if r else ()
            if not sg:
                rows.append(0)
                continue
            if sg not in lists:
                lists[sg] = len(seg)
                for n, (col, t, colour) in enumerate(sg):
                    at_ = text.find(t)
                    if at_ < 0:
                        at_ = len(text)
                        text += t
                    seg.append(at_ | (len(t) << 13) | (col << 19) | (colour << 25) | ((n == len(sg) - 1) << 27))
            rows.append(lists[sg])
    rows += [0] * (PAGES * 32 - len(rows))
    if len(seg) > SEG_SIZE or len(text) > TEXT_SIZE:
        raise SystemExit('%d segments (room for %d), %d characters (room for %d)'
                         % (len(seg), SEG_SIZE, len(text), TEXT_SIZE))
    used = (len(pg), len(seg) - 1, len(text))
    seg += [0] * (SEG_SIZE - len(seg))
    codes = [ord(ch) - 32 for ch in text] + [0] * (TEXT_SIZE - len(text))
    font = [b for ch in font_rows() for b in ch]
    svh = ['// tunit_window_pages.svh - the first window page and the page count of',
           '// each list',
           '// Generated by tools/tunit_window.py --write; do not edit.',
           '//',
           '// Copyright (C) 2026 Gm0rk - GPL-3.0-or-later',
           '']
    for name, (p0, n) in first.items():
        svh.append("%-40s// %d page%s" % ("localparam [4:0] WIN_%s = 5'd%d;" % (name.upper(), p0),
                                          n, 's' if n > 1 else ''))
    svh += ['', '// pages of each list (the OSD options: Off, then one value per page)']
    for name, (p0, n) in first.items():
        svh.append("localparam [4:0] WIN_%s_N = 5'd%d;" % (name.upper(), n))
    return {'row': '\n'.join('%03X' % w for w in rows) + '\n',
            'seg': '\n'.join('%07X' % w for w in seg) + '\n',
            'text': '\n'.join('%02X' % w for w in codes) + '\n',
            'font': '\n'.join('%02X' % w for w in font) + '\n',
            'svh': '\n'.join(svh) + '\n'}, used


def background(path):
    """A title screen as BG_W x BG_H palette indices and BG_COLOURS dimmed colours."""
    from PIL import Image
    im = Image.open(path).convert('RGB')
    w, h = im.size
    pw = min(w, h * 4 // 3)                  # the 4:3 picture in the middle
    im = im.crop(((w - pw) // 2, 0, (w - pw) // 2 + pw, h)).resize((BG_W, BG_H), Image.LANCZOS)
    im = im.point(lambda v: int(v * DIM + 0.5))
    q = im.quantize(colors=BG_COLOURS, method=Image.MEDIANCUT, dither=Image.NONE)
    pal = q.getpalette()[:3 * BG_COLOURS]
    pal += [0] * (3 * BG_COLOURS - len(pal))
    return list(q.tobytes()), [tuple(pal[3 * i:3 * i + 3]) for i in range(BG_COLOURS)]


def write_bg(paths):
    idx, pal = [], []
    for p in paths:
        i, c = background(p)
        idx += i
        pal += c
    open(OUT['bg'], 'w').write(''.join('%02X\n' % v for v in idx))
    open(OUT['pal'], 'w').write(''.join('%02X%02X%02X\n' % c for c in pal))
    print('%s: %d entries, %s: %d colours' % (os.path.relpath(OUT['bg'], REPO), len(idx),
                                               os.path.relpath(OUT['pal'], REPO), len(pal)))


def show(rows):
    print('+' + '-' * COLS + '+')
    for r in rows:
        line = [' '] * COLS
        if r:
            k = r[0]
            for t, _ in r[1]:
                for ch in t:
                    line[k] = ch
                    k += 1
        print('|' + ''.join(line) + '|')
    print('+' + '-' * COLS + '+')


def main():
    a = sys.argv[1:]
    if a in (['--write'], ['--check']):
        img, used = images()
        paths = dict(OUT, svh=OUT_SVH)
        bad = []
        for k, body in img.items():
            if a == ['--write']:
                open(paths[k], 'w').write(body)
            elif not os.path.exists(paths[k]) or open(paths[k]).read() != body:
                bad.append(os.path.relpath(paths[k], REPO))
        print('%d pages, %d of %d segments, %d of %d characters'
              % (used[0], used[1], SEG_SIZE - 1, used[2], TEXT_SIZE))
        if a == ['--check']:
            print('ROM images: ' + ('OK' if not bad else 'differ: ' + ', '.join(bad)))
            sys.exit(1 if bad else 0)
    elif a[:1] == ['--bg'] and len(a) == 1 + len(BG_GAMES):
        write_bg(a[1:])
    elif a[:1] == ['--show']:
        which = a[1] if len(a) > 1 else '0'
        for k, (lb, rows) in enumerate(pages()[0]):
            if which == 'all' or which == str(k) or which.lower() in lb.lower():
                print('page %d: %s' % (k, lb))
                show(rows)
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == '__main__':
    main()

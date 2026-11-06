#!/usr/bin/env python3
"""
tunit_splist.py - the secret players of NBA Jam and NBA Jam TE

The data of the OSD's Secret Player List window (tools/tunit_window.py draws
the pages, rtl/tunit_window.sv shows them): every secret player with their
name, the initials and birthday that bring them up (answer YES to "Enter
initials for record keeping?"), and the versions that have them.

The players come from the games themselves: after a player's initials and
birthday the game compares them with a table of 5-word entries (initials 0-25
and 26 for a space, month, day; NBA Jam 3.01 FF963740, TE 4.0 FF9DF760). --scan
reads that table in every revision's program ROM (region dumps from
tools/mame/region_dump.lua; the HBMAME hack, TE Special Edition 5.02, from its
zip in tools/hbmame_sets.py's folder) and writes tools/tunit_splist.txt, from
which the rest is made, so the ROMs are needed for --scan only. Entries are
matched to the players below by their initials; a player's initials can differ between
revisions (TE proto 2.00's placeholders such as JZG for JPG, the Grim
Reaper's BIG and GRM), and TE 3.0 (2-26-94) adds 17 to the first letter of
everyone but the NBA players (a player can only enter 0-26: they are
disabled there, the picture and name are still in the game). Every entry of a
MAME revision was seen by name on MAME's team select screen with the check
patched to it. The Special Edition's table (68 entries; its own release
notes name Griffey and Jordan and their birthdays) was read from its program:
KID NOV 21 (Griffey) and AIR FEB 17 (Jordan) are new, every other entry has the
initials and birthday of an earlier revision's, and there are none for Ray
Gay, Isiah Thomas, Chris Webber and Dennis Rodman (the notes: Jordan replaces
Webber). These were not seen on a team select screen.
The full names: the games' own credits, a secret player guide on GameFAQs
(Secret Player Stats Guide by DarthMarino), and for VLK ("Kamm") The
Cutting Room Floor (Larry DeMar's picture, Vicki Kamm's name).

Usage:
    tunit_splist.py --scan --regions DIR --hbmame DIR   write tools/tunit_splist.txt
    tunit_splist.py --docs nbajam|nbajamte the game page's table (markdown)

Copyright (C) 2026 Gm0rk - GPL-3.0-or-later
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import hbmame_sets  # noqa: E402
import tunit_secrets as ts  # noqa: E402

TXT = os.path.join(HERE, 'tunit_splist.txt')
# Players in the games' table order: full name, the name the team select
# screen shows, the initials in the revisions' tables ('_' a space; a second
# entry with the same initials gets a 2: TE's two JMS)
NJ_PLAYERS = [
    ('Tony Goskie', 'Goskie', 'TWG'), ('Jamie Rivett', 'Rivett', 'RJR'),
    ('John Carlton', 'Carlton', 'JMC'), ('Sal DiVita', 'Di Vita', 'SAL'),
    ('Shawn Liptak', 'Liptak', 'SL_'), ('Mark Turmell', 'Turmell', 'MJT'),
    ('Jon Hey', 'Hey', 'JWH'), ('George Petro', 'Petro', 'GNP'),
    ('John Newcomer', 'Newcomer', 'JRN'), ('Sheridan Oursler', 'Oursler', 'SNO'),
    ('Stephen Howard', 'Howard', 'HOW'), ('Willie Morris Jr.', 'Air Morris', 'WIL'),
    ('Tony Scott', 'Scott', 'TON')]
TE_PLAYERS = [
    ('Tony Goskie', 'Goskie', 'TWG'), ('Jamie Rivett', 'Rivett', 'RJR'),
    ('John Carlton', 'Carlton', 'JMC'), ('Sal DiVita', 'Di Vita', 'SAL'),
    ('Shawn Liptak', 'Liptak', 'SL_'), ('Mark Turmell', 'Turmell', 'MJT'),
    ('Jon Hey', 'Hey', 'JWH'), ('George Petro', 'Petro', 'GNP'),
    ('John Newcomer', 'Newcomer', 'JRN'), ('Sheridan Oursler', 'Oursler', 'SNO'),
    ('Al Lasko', 'Lasko', 'AML'), ('Willie Morris Jr.', 'Air Morris', 'WIL'),
    ('Cary Mednick', 'Mednick', 'CMM'), ('Dan Forden', 'Forden', 'DWF'),
    ('Eric Kinkead', 'Kinkead', 'DIE'), ('Eugene Jarvis', 'Jarvis', 'EPJ'),
    ('Jack Haeger', 'Haeger', 'JEH'), ('Jake Simpson', 'Simpson', 'JMS'),
    ('Jim Green', 'Green', 'JDG'), ('Jim Gentile', 'Gentile', 'JPG JZG'),
    ('Joe Dillon', 'Dillon', 'JPD'), ('John Lowes', 'Lowes', 'JML'),
    ('John Vogel', 'Vogel', 'VOG'), ('Josh Tsui', 'Tsui', 'JYT'),
    ('Larry DeMar', 'Kamm', 'VLK'), ('Linda Deal', 'Deal', 'LTD'),
    ('Matt Booty', 'Booty', 'MVB'), ('Mark Loffredo', 'Loffredo', 'ML_'),
    ('Mark Penacho', 'Penacho', 'MDP'), ('Paul Barker', 'Barker', 'PCB'),
    ('Pat Cox', 'Cox', 'PGC'), ('Ray Macika', 'Macika', 'REM RZM'),
    ('Roger Sharpe', 'Sharpe', 'ROG'), ('Steve Beran', 'Beran', 'SAB'),
    ('Vince Pontarelli', 'Pontarelli', 'VJP'), ('Warren Davis', 'Davis', 'WBD WZD'),
    ('Ed Boon', 'Boon', 'EJB'), ('John Tobias', 'Tobias', 'TOB'),
    ('Paul Heitsch', 'Heitsch', 'WMN'), ('Bill Dabelstein', 'Dabelstein', 'DOZ BZD'),
    ('Martin Martinez', 'Martinez', 'MAM'), ('Rachel Davies', 'Davies', 'RJD'),
    ('Kerri Hoskins', 'Hoskins', 'KER'), ('Lorraine Olivia', 'Olivia', 'LOR'),
    ('Chris Granner', 'Granner', 'CG_'), ('Ray Gay', 'Gay', 'RMG'),
    ('Ken Griffey Jr.', 'Griffey', 'KID'),
    ('Jason Skiles', 'Skiles', 'JMS2'), ('Joe Linhoff', 'Linhoff', 'JFL JZL'),
    ('Dominique Wilkins', 'Wilkins', 'DOM'), ('Dee Brown', 'Brown', 'DEE'),
    ('Alonzo Mourning', 'Mourning', 'ZO_'), ('Scottie Pippen', 'Pippen', 'PIP'),
    ('Isiah Thomas', 'Thomas', 'ZEK'), ('Chris Webber', 'Webber', 'WEB'),
    ('Hakeem Olajuwon', 'Olajuwon', 'HAK'), ('Derrick Coleman', 'Coleman', 'DC_'),
    ('Patrick Ewing', 'Ewing', 'PAT'), ('Charles Barkley', 'Barkley', 'BRK'),
    ('David Robinson', 'Robinson', 'ROB'), ('Shawn Kemp', 'Kemp', 'KMP'),
    ('Karl Malone', 'Malone', 'KRL'), ('Dennis Rodman', 'Rodman', 'ROD'),
    ('Gary Payton', 'Payton', 'GEE'), ('Michael Jordan', 'Jordan', 'AIR'), ('Sub-Zero', 'Sub-Zero', 'SUB'),
    ('Scorpion', 'Scorpion', 'SCO'), ('Reptile', 'Reptile', 'RPT'),
    ('Raiden', 'Raiden', 'RAD'), ('Grim Reaper', 'Reaper', 'BIG GRM'),
    ('Kongo', 'Kongo', 'KNG'), ('Tim Coman', 'Coman', 'TJC'),
    ('Elviscious', 'Elviscious', 'ELV')]
MOVED = 17                          # TE 3.0 (2-26-94): first letter + 17

# The revisions, oldest first: MAME set, the name used in the lists, the MRA
# name's revision
NJ_SETS = [('nbajamp1', 'proto 1.01', 'proto v 1.01 1-23-93'), ('nbajamp2', 'proto 2.00', 'proto v 2.00 1-24-93'),
           ('nbajamr1', '1.00', 'rev 1.00 2-1-93'), ('nbajamr2', '2.00', 'rev 2.00 2-10-93'),
           ('nbajam', '3.01', 'rev 3.01 4-07-93')]
TE_SETS = [('nbajamtep2', 'proto', 'proto 2.00 12-17-93'), ('nbajamte1', '1.00', 'rev 1.00 1-17-94'),
           ('nbajamte2a', '2.0', 'rev 2.0 1-28-94'), ('nbajamte2', '2.1', 'rev 2.1 2-06-94'),
           ('nbajamte3a', '3.0 2-26', 'rev 3.0 2-26-94'), ('nbajamte4', '4.0 3-03', 'rev 4.0 3-03-94'),
           ('nbajamte3', '3.0 3-04', 'rev 3.0 3-04-94'), ('nbajamte', '4.0 3-23', 'rev 4.0 3-23-94'),
           ('nbajamten', 'Nani', 'Nani Edition, rev 5.2 8-11-95'),
           ('nbajamtese', 'SE 5.02', 'Special Edition, rev 5.02')]
GAMES = [('nbajam', 'NBA JAM', NJ_PLAYERS, NJ_SETS), ('nbajamte', 'NBA JAM TOURNAMENT EDITION', TE_PLAYERS, TE_SETS)]

MONTHS = 'JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC'.split()

# ----------------------------------------------------------------------------
# The games' tables (--scan)
# ----------------------------------------------------------------------------

X = None


def initials(ws):
    """Initials of a table entry ('_' a space), or None (not letters)."""
    if any(c > 26 for c in ws):
        return None
    return ''.join(chr(65 + c) if c < 26 else '_' for c in ws)


def table(p):
    """The secret player table of a program ROM (tunit_secrets.Prog): entries
    (initials words, month, day), or None (no secret players)."""
    h = p.find([0x09E2, X, X, 0xB460, 0x0040, X, 0x8441, 0x4801, X, 0xB460, 0x0050, 0xB441, 0x0010, 0x4801])
    if len(h) != 1:
        return None
    i = h[0]
    tbl = p.word_index(p.u32(i + 1))
    n = None
    for k in range(i, i + 80):
        if p.w[k] == 0x0B45:                 # CMPI n,A5: the entry count
            n = ~p.w[k + 1] & 0xFFFF
            break
    if not n or p.w[i + 8] >> 8 != 0xCB or p.w[i + 34] >> 8 != 0xCB:
        return None
    return [(p.w[tbl + 5 * e:tbl + 5 * e + 3], p.w[tbl + 5 * e + 3], p.w[tbl + 5 * e + 4]) for e in range(n)]


def match(entries, players):
    """Each entry's player (index) or None, and its initials as entered."""
    alias = {}
    for k, (_, _, ini) in enumerate(players):
        for a in ini.split():
            alias[a] = k
    seen, out = {}, []
    for ws, _, _ in entries:
        ini = initials(ws)
        if ini is None or (ini not in alias and ini + '2' not in alias):
            if ws[0] >= MOVED and initials([ws[0] - MOVED] + list(ws[1:])):
                ini = initials([ws[0] - MOVED] + list(ws[1:]))
        if ini is None:
            out.append((None, None))
            continue
        seen[ini] = seen.get(ini, 0) + 1
        key = ini if seen[ini] == 1 else ini + str(seen[ini])
        out.append((alias.get(key), ini))
    return out


def hack_program(hack, hbmame):
    """The maincpu region of an HBMAME hack (tools/hbmame_sets.py): its zip's two
    program files, uj12 the even bytes and ug12 the odd, as MAME loads them."""
    import zipfile
    import zlib
    files = {n.rsplit('.', 1)[1]: (n, int(c, 16)) for n, c in hack['files'].items() if n.rsplit('.', 1)[1] in ('uj12', 'ug12')}
    if sorted(files) != ['ug12', 'uj12']:
        raise SystemExit('%s: program files not among the hack\'s' % hack['name'])
    z = zipfile.ZipFile(os.path.join(hbmame, hack['zip']))
    data = {}
    for k, (name, crc) in files.items():
        data[k] = z.read(name)
        if zlib.crc32(data[k]) != crc:
            raise SystemExit('%s: %s has the wrong CRC' % (hack['zip'], name))
    buf = bytearray(len(data['uj12']) * 2)
    buf[0::2], buf[1::2] = data['uj12'], data['ug12']
    return bytes(buf)


def scan(regions, hbmame):
    """tools/tunit_splist.txt from the region dumps (and the hacks' zips)."""
    lines = ['# Secret players, from tools/tunit_splist.py --scan (the games\' tables).',
             '# game | full name | team select name | initials | birthday | versions',
             '# (initials: _ is a space; versions: the list names of tunit_splist.py, oldest first)']
    for game, _, players, sets in GAMES:
        have = {}                            # (player, initials, birthday) -> versions
        for setname, rev, _ in sets:
            hack = next((h for h in hbmame_sets.HACKS if h['name'] == setname), None)
            if hack:
                prog = hack_program(hack, hbmame)
            else:
                prog = open(os.path.join(regions, setname, 'maincpu.bin'), 'rb').read()
            t = table(ts.Prog(prog))
            if t is None:
                print('%-11s no secret players' % setname)
                continue
            m = match(t, players)
            bad = [e for e, (k, _) in enumerate(m) if k is None]
            if bad:
                raise SystemExit('%s: entries %s match no player' % (setname, bad))
            for (ws, mo, dy), (k, ini) in zip(t, m):
                have.setdefault((k, ini, '%s %d' % (MONTHS[mo - 1], dy)), []).append(rev)
            print('%-11s %d entries' % (setname, len(t)))
        for k, (full, screen, _) in enumerate(players):
            rows = sorted((key for key in have if key[0] == k), key=lambda key: -len(have[key]))
            if not rows:
                raise SystemExit('%s: %s is in no revision' % (game, full))
            for key in rows:
                lines.append(' | '.join([game, full, screen, key[1], key[2], ','.join(have[key])]))
    open(TXT, 'w').write('\n'.join(lines) + '\n')
    print('%s: %d players' % (os.path.relpath(TXT, REPO), len(lines) - 3))


def load():
    """{game: [(full, screen, initials, birthday, [versions])]}"""
    out = {g[0]: [] for g in GAMES}
    for line in open(TXT, encoding='utf-8'):
        if line.startswith('#') or not line.strip():
            continue
        game, full, screen, ini, day, ver = [f.strip() for f in line.split('|')]
        out[game].append((full, screen, ini, day, ver.split(',')))
    return out


# ----------------------------------------------------------------------------
# Words for the window and the docs
# ----------------------------------------------------------------------------

def label(full, screen):
    """The name shown: the full one, with the team select's if it is not in it."""
    last = screen.replace(' ', '').split('-')[-1].lower()
    if last in full.replace(' ', '').lower() or screen.split()[-1].lower() in full.lower():
        return full
    return '%s (%s)' % (full, screen)


def versions(have, sets, with_table):
    """A player's versions as words: 'All', 'All but ...', or the list with
    runs of four or more as 'A to B' (oldest first)."""
    order = [rev for _, rev, _ in sets if rev in with_table]
    have = [rev for rev in order if rev in have]
    missing = [rev for rev in order if rev not in have]
    if not missing:
        if len(order) == len(sets):
            return 'All'
    elif len(missing) <= 2:
        return 'All but ' + ', '.join(missing)
    parts, k = [], 0
    while k < len(order):
        if order[k] not in have:
            k += 1
            continue
        j = k
        while j + 1 < len(order) and order[j + 1] in have:
            j += 1
        run = order[k:j + 1]
        parts += [run[0] + ' to ' + run[-1]] if len(run) >= 4 else run
        k = j + 1
    s = ', '.join(parts)
    return s[0].upper() + s[1:]


def docs(game):
    """Markdown table of a game's secret players."""
    data = load()
    g = [x for x in GAMES if x[0] == game][0]
    with_table = set(v for p in data[game] for v in p[4])
    out = ['| Player | On screen | Initials | Birthday | Versions |', '|---|---|---|---|---|']
    last = None
    for full, screen, ini, day, ver in data[game]:
        first = full != last
        out.append('| %s | %s | %s | %s | %s |' % (full if first else '', screen if first else '', ini,
                                                   day.title(), versions(ver, g[3], with_table)))
        last = full
    return '\n'.join(out)


def main():
    a = sys.argv[1:]
    if a[:1] == ['--scan'] and len(a) == 5 and a[1] == '--regions' and a[3] == '--hbmame':
        scan(a[2], a[4])
    elif a[:1] == ['--docs'] and len(a) == 2:
        print(docs(a[1]))
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
hbmame_sets.py - hack sets that are not in MAME's T-Unit driver

MAME's midtunit.cpp is the source of every other MRA (tools/mra_gen.py). A
few ROM hacks live only in HBMAME. Each one is described here as a clone of
a MAME set with some files replaced, the way HBMAME lists it, so the same
generator writes its MRA: same board configuration, DIP switches, buttons,
secrets table and fight variables, with the hack's own ROM files.

HBMAME zips go in games/hbmame (MAME's go in games/mame). Main_MiSTer
(support/arcade/mra_loader.cpp) builds a zip's path as <games>/mame/<zip>
unless the name starts with '/', which drops the 'mame' folder, so the MRA
names the zip "/hbmame/<zip>": the file is then <games>/hbmame/<zip>. A hack's
zip is HBMAME's merged zip of the parent (mk2.zip, nbajamte.zip), which holds the
parent's files and a folder with each clone's, so the MRA needs no parent zip.

Entry fields
  name     HBMAME set name (also the MRA's <setname>, which names the core's
           NVRAM and settings files, so the hack does not share the parent's)
  parent   MAME set it is a clone of
  desc     description (the MRA's file name and <name>)
  zip      file name in games/hbmame
  files    {file name in the parent's set: new CRC} - the parent's files that
           differ
  names    {file name in the parent's set: file name in the hack's zip} - for a
           zip whose files carry other names than the parent's (the MRA names
           the zip's own); the files not listed keep the parent's names
  move_list  'rev4': the core's Move List shows rev 4.0's own pages (tools/tunit_rev4.py;
           the MRA's game id word carries the flag); everything else is as for the parent
  mkplus_list  Mortal Kombat Plus: the core's Move List shows the hack's own pages
           (tools/tunit_mkplus.py; the MRA's game id word carries the flag); its
           Finishing Moves, hidden items and the rest are the parent's
  hide_extras  the core's OSD has no hidden items for the set, and shows its own
           Move List and View Secrets instead of MK2's (the MRA's game id word
           carries the flag, no secrets table is written): the hack changes the
           code the codes and items are built on. The Finishing Moves page is MK2's
           (the hack is rev L3.1 with more code: the same moves, the fight variables
           and direct finisher sites are found in the hack's own program)

A hack without hide_extras (NBA Jam Tournament Edition Special Edition and
Rewind) keeps its parent's extras: the secrets table and the cheats are found
in the hack's own program (tools/tunit_secrets.py, tools/tunit_cheats.py), and
the cheats from MAME's files, which have no entry for a hack, are derived from
the parent's (tools/tunit_relocate.py, tools/tunit_cheats_data.py).

Copyright (C) 2026 Gm0rk - GPL-3.0-or-later
"""

import copy
import os

import mame_src

def _te_files(prog, members):
    """The `files` and `names` of a Tournament Edition hack whose files are in
    HBMAME's merged nbajamte.zip. `members` is {position: (folder, CRC)} for
    the files that differ from the parent's: position ug12, uj12 (the program,
    whose names in the parent's set start with `prog`, l4 or l2), u12, u13 (the
    sound samples) or a graphics ROM (ug16...); folder the set whose folder in
    the zip holds the file ('nbajam03/nbajam03.ug16'). The parent's other files
    keep their names at the zip's root."""
    files, names = {}, {}
    for pos, (folder, crc) in sorted(members.items()):
        if pos in ('ug12', 'uj12'):
            name = '%s_nba_jam_tournament_game_rom_%s.%s' % (prog, pos, pos)
        elif pos in ('u12', 'u13'):
            name = 'l1_nba_jam_tournament_%s_sound_rom.%s' % (pos, pos)
        else:
            name = 'l1_nba_jam_tournament_game_rom_%s.%s' % (pos, pos)
        files[name] = crc
        names[name] = '%s/%s.%s' % (folder, folder, pos)
    return dict(files=files, names=names)


# The merged zip's files, as {position: (folder, CRC)}
SE_50 = {                           # nbajam03: SE rev 5.0
    'ug12': ('nbajam03', '90e66e60'), 'uj12': ('nbajam03', 'a317f3bf'),
    'ug16': ('nbajam03', 'c8da980e'), 'ug17': ('nbajam03', '1b7ddbe9'), 'ug18': ('nbajam03', '741f313e'),
    'ug20': ('nbajam03', '9cd4f985'), 'ug22': ('nbajam03', '5427ca82'), 'ug23': ('nbajam03', '168d93ce'),
    'uj16': ('nbajam03', '205c5fb7'), 'uj17': ('nbajam03', 'cb08465f'), 'uj18': ('nbajam03', '5c1d6d77'),
    'uj20': ('nbajam03', '7a47f364'), 'uj22': ('nbajam03', '569b1ae5'), 'uj23': ('nbajam03', '424fbd82'),
}
SE_502 = dict(SE_50, **{            # nbajam05: SE rev 5.02 (graphics ug16 ug17 ug20 ug22 uj16 uj17 uj20 uj22 are 5.0's)
    'ug12': ('nbajam05', 'd784608e'), 'uj12': ('nbajam05', '08507007'),
    'ug18': ('nbajam05', 'a182457b'), 'ug23': ('nbajam05', '7755db95'),
    'uj18': ('nbajam05', 'ed6b08a5'), 'uj23': ('nbajam05', 'a659b604'),
    'u12': ('nbajam05', '7be1622b'), 'u13': ('nbajam05', 'f939bfcb'),
})
REWIND_11 = {                       # nbajam02: Rewind rev 1.1
    'ug12': ('nbajam02', '18e75204'), 'uj12': ('nbajam02', '9b3fc483'),
    'ug16': ('nbajam02', 'b9a07a6f'), 'ug17': ('nbajam02', '34c6bdb8'), 'ug18': ('nbajam02', 'fe18a6ef'),
    'ug20': ('nbajam02', '67c8646b'), 'ug22': ('nbajam02', 'd41234d2'), 'ug23': ('nbajam02', '8d1af1a6'),
    'uj16': ('nbajam02', 'ffa7db04'), 'uj17': ('nbajam02', '3af5b32e'), 'uj18': ('nbajam02', '9a6d36de'),
    'uj20': ('nbajam02', '71d028f8'), 'uj22': ('nbajam02', '42196c84'), 'uj23': ('nbajam02', 'b5bf66f9'),
    'u12': ('nbajam02', 'cd5d4532'), 'u13': ('nbajam02', 'e92fb0d3'),
}
REWIND_12 = dict(REWIND_11, u13=('nbajam04', 'c4cbede2'))                         # nbajam04: Rewind rev 1.2
REWIND_UNPROT = dict(REWIND_12, ug12=('nbajam07', 'b2dd7831'), uj12=('nbajam07', '1ef0eb74'))   # nbajam07


def _mk2_files(folder, members):
    """The `files` and `names` of a Mortal Kombat II hack whose files are in
    the `folder` of HBMAME's merged mk2.zip. `members` is {position: CRC} for
    the files that differ from the parent's (rev L3.1): ug12, uj12 (the
    program), a graphics ROM (ug14...) or a sound ROM (u2...u7)."""
    files, names = {}, {}
    for pos, crc in sorted(members.items()):
        if pos in ('ug12', 'uj12'):
            name = 'l3.1_mortal_kombat_ii_game_rom_%s.%s' % (pos, pos)
        elif pos.startswith('u') and pos[1].isdigit():
            name = 'l1_mortal_kombat_ii_sound_rom_%s.%s' % (pos, pos)
        else:
            name = 'l1_mortal_kombat_ii_game_rom_%s.%s' % (pos, pos)
        files[name] = crc
        names[name] = '%s/%s.%s' % (folder, folder, pos)
    return dict(files=files, names=names)


def _mk_files(folder, members):
    """The same for a Mortal Kombat hack in the `folder` of HBMAME's merged
    mk.zip (parent rev 5.0): ug12, uj12 (the program) or a graphics ROM."""
    files, names = {}, {}
    for pos, crc in sorted(members.items()):
        if pos in ('ug12', 'uj12'):
            name = 'l5_mortal_kombat_t-unit_%s_game_rom.%s' % (pos, pos)
        else:
            name = 'l1_mortal_kombat_t-unit_%s_game_rom.%s' % (pos, pos)
        files[name] = crc
        names[name] = '%s/%s.%s' % (folder, folder, pos)
    return dict(files=files, names=names)


MK2S08 = {                          # mk2s08: Mortal Kombat II rev 4.0
    'ug12': 'd40d34fd', 'uj12': 'fd23dd93',
    'ug14': '9c864f0f', 'ug16': '1e5325f3', 'ug17': '3924479e',
    'ug19': 'e768a4ce', 'ug20': '0c929fba', 'ug22': 'd7bd61c3',
    'uj14': '3314f622', 'uj16': '8004a3b6', 'uj17': 'a1af4391',
    'uj19': '04305b16', 'uj20': '7ed4ba0d', 'uj22': '53dc6b89',
    'u2': 'fff86ce6', 'u3': 'a5d9baa8', 'u4': '51ef6866',
    'u5': '373de0e7', 'u6': 'b05d11bf', 'u7': 'a51de7aa',
}
MK07 = {                            # mk07: Mortal Kombat Plus v5.0.0741
    'ug12': 'be771d8d', 'uj12': '8edf28c0',
    'ug17': '44b5de0e', 'uj17': 'c69cd46c', 'ug22': 'e742a405', 'uj22': '34110899',
}


HACKS = [
    # Mortal Kombat II Plus, Beta 2 (HBMAME mk2s04, "2.8.5 plus beta 2",
    # 2018-12-23; older HBMAME and FBNeo called it mk2p): a changed rev L3.1
    # program (new characters, moves and service-menu options), four changed
    # graphics ROMs and one changed sound ROM. A clone of mk2 in HBMAME's merged
    # mk2.zip (games/hbmame; MAME's own mk2.zip stays in games/mame): the seven
    # files below are in the mk2s04 folder, the L3.1 / L1 files that did not
    # change at the zip's root. (mk2s03, "2.8.0 plus beta 1", has only its own
    # program in the same zip; its entry is below.)
    dict(name='mk2s04', parent='mk2', desc='Mortal Kombat II Plus (Beta 2, hack)',
         zip='mk2.zip', hide_extras=True,
         files={
             'l3.1_mortal_kombat_ii_game_rom_uj12.uj12': '05ff15a9',   # program, even bytes
             'l3.1_mortal_kombat_ii_game_rom_ug12.ug12': 'b6d8ff5c',   # program, odd bytes
             'l1_mortal_kombat_ii_game_rom_ug16.ug16': 'b2af2798',     # graphics
             'l1_mortal_kombat_ii_game_rom_uj16.uj16': 'd70dd149',
             'l1_mortal_kombat_ii_game_rom_ug20.ug20': 'd05e970a',
             'l1_mortal_kombat_ii_game_rom_uj20.uj20': '0f9c9a12',
             'l1_mortal_kombat_ii_sound_rom_u2.u2': '65d11dd7',        # DCS sound data
         },
         names={
             'l3.1_mortal_kombat_ii_game_rom_uj12.uj12': 'mk2s04/mk2s04.uj12',
             'l3.1_mortal_kombat_ii_game_rom_ug12.ug12': 'mk2s04/mk2s04.ug12',
             'l1_mortal_kombat_ii_game_rom_ug16.ug16': 'mk2s04/mk2s04.ug16',
             'l1_mortal_kombat_ii_game_rom_uj16.uj16': 'mk2s04/mk2s04.uj16',
             'l1_mortal_kombat_ii_game_rom_ug20.ug20': 'mk2s04/mk2s04.ug20',
             'l1_mortal_kombat_ii_game_rom_uj20.uj20': 'mk2s04/mk2s04.uj20',
             'l1_mortal_kombat_ii_sound_rom_u2.u2': 'mk2s04/mk2pb2.u2',
         }),
    # NBA Jam Tournament Edition Special Edition (HBMAME nbajam03, rev 5.0, and
    # nbajam05, rev 5.02): TE rebuilt from its source with new players, CMOS
    # options and samples (the author's whatsnew.txt). Clones of nbajamte in
    # HBMAME's merged nbajamte.zip (games/hbmame; MAME's own nbajamte.zip stays
    # in games/mame): each set's files are in the folder of the set that has
    # them, the parent's files at the zip's root. 5.0 has its own program and
    # 12 graphics ROMs and the parent's sound ROMs; 5.02 has its own program,
    # 4 more graphics ROMs and two sound ROMs, and the other 8 graphics ROMs
    # of 5.0.
    dict(name='nbajam03', parent='nbajamte', desc='NBA Jam Tournament Edition (SE rev 5.0, hack)',
         zip='nbajamte.zip', **_te_files('l4', SE_50)),
    dict(name='nbajam05', parent='nbajamte', desc='NBA Jam Tournament Edition (SE rev 5.02, hack)',
         zip='nbajamte.zip', **_te_files('l4', SE_502)),
    # NBA Jam Rewind (HBMAME nbajam02, rev 1.1, and nbajam04, rev 1.2; the "NBA
    # Rewind 4 Jam" hack of arcade-projects): Tournament Edition rev 2.0 1-28-94
    # (by the program's bytes, not the 2.1 its readme names) with 12 changed
    # graphics ROMs (Jordan and Shaq added to the teams), a changed u12 sample
    # ROM and 2.0's program changed in ~2,600 bytes (a Big Head / Huge Head /
    # Expanded Roster code at the player select screen, Fatalities from the
    # team select screen: the readme). 1.2 has 1.1's files with a changed u13
    # sample ROM; nbajam07 ("unprotected, v1.2") has another program (12 bytes
    # different) with 1.2's other files. The secret player table, the
    # power-ups and the cheats are 2.0's, at the same places.
    dict(name='nbajam02', parent='nbajamte2a', desc='NBA Jam Tournament Edition (Rewind rev 1.1, hack)',
         zip='nbajamte.zip', **_te_files('l2', REWIND_11)),
    dict(name='nbajam04', parent='nbajamte2a', desc='NBA Jam Tournament Edition (Rewind rev 1.2, hack)',
         zip='nbajamte.zip', **_te_files('l2', REWIND_12)),
    dict(name='nbajam07', parent='nbajamte2a', desc='NBA Jam Tournament Edition (Rewind 4 Jam, unprotected v1.2, hack)',
         zip='nbajamte.zip', **_te_files('l2', REWIND_UNPROT)),
    # Mortal Kombat II Plus, Beta 1 (HBMAME mk2s03, "2.8.0 plus beta 1",
    # 2017-09-24): the same hack's earlier build, a changed rev L3.1 program
    # alone (the graphics and sound are rev L3.1's), a clone of mk2 in HBMAME's
    # merged mk2.zip.
    dict(name='mk2s03', parent='mk2', desc='Mortal Kombat II Plus (Beta 1, hack)',
         zip='mk2.zip', hide_extras=True,
         files={
             'l3.1_mortal_kombat_ii_game_rom_uj12.uj12': '87a755b5',   # program, even bytes
             'l3.1_mortal_kombat_ii_game_rom_ug12.ug12': 'b59368c4',   # program, odd bytes
         },
         names={
             'l3.1_mortal_kombat_ii_game_rom_uj12.uj12': 'mk2s03/mk2s03.uj12',
             'l3.1_mortal_kombat_ii_game_rom_ug12.ug12': 'mk2s03/mk2s03.ug12',
         }),
    # Mortal Kombat II (HBMAME mk2s08, "rev 4.0", JUNKWAX, 2026): a rebuilt
    # program (about 99 % of its bytes differ from rev L3.1's; it has a
    # training mode) with every graphics and sound ROM of its own, all in the
    # mk2s08 folder of the merged mk2.zip. The core's Move List shows its own
    # pages (move_list='rev4'); its Finishing Moves and hidden items are rev L3.1's.
    dict(name='mk2s08', parent='mk2', desc='Mortal Kombat II (rev 4.0, hack)',
         zip='mk2.zip', move_list='rev4', **_mk2_files('mk2s08', MK2S08)),
    # Mortal Kombat Plus (HBMAME mk07, "v5.0.0741", Zpaul2fresh8, 2020): the
    # MK+ hack of rev 5.0: a changed program (it has an MK+ settings menu) and
    # four changed graphics ROMs (ug17, uj17, ug22, uj22); the other graphics
    # and the sound are rev 5.0's. A clone of mk in HBMAME's merged mk.zip.
    dict(name='mk07', parent='mk', desc='Mortal Kombat Plus (v5.0.0741, hack)',
         zip='mk.zip', mkplus_list=True, **_mk_files('mk07', MK07)),
]

HBMAME_DIR = '/hbmame/'


def zip_attr(hack):
    """The MRA's zip attribute for a hack."""
    return HBMAME_DIR + hack['zip']


def hack_games(games):
    """[Game] for the hacks: clones of the MAME parents with the replaced
    files. `zipattr` is the zip attribute for the MRA, `zipfile` the zip's
    name in the HBMAME folder."""
    out = []
    for h in HACKS:
        base = next(g for g in games if g.name == h['parent'])
        g = mame_src.Game(base.year, h['name'], h['parent'], base.machine,
                          base.inputs, base.init, h['desc'], base.manuf)
        g.manuf = 'hack'
        rs = copy.deepcopy(base.romset)
        rs.name = h['name']
        seen = set()
        renamed = set()
        names = h.get('names', {})
        for region in rs.regions.values():
            for ld in region.loads:
                if ld.name in h['files']:
                    ld.crc = h['files'][ld.name]
                    seen.add(ld.name)
                if ld.name in names:
                    renamed.add(ld.name)
                    ld.name = names[ld.name]
        missing = set(h['files']) - seen
        if missing:
            raise ValueError('%s: files not in %s: %s' % (h['name'], h['parent'], sorted(missing)))
        missing = set(names) - renamed
        if missing:
            raise ValueError('%s: names for files not in %s: %s' % (h['name'], h['parent'], sorted(missing)))
        g.romset = rs
        g.zipattr = zip_attr(h)
        g.hide_extras = h.get('hide_extras', False)
        g.move_list = h.get('move_list')
        g.mkplus_list = h.get('mkplus_list', False)
        g.zipfile = h['zip']
        out.append(g)
    return out


def hack_zips(hbmame_dir):
    """{set name: RomZips} for the hacks whose zip is in `hbmame_dir`."""
    zips = {}
    for h in HACKS:
        path = os.path.join(hbmame_dir, h['zip'])
        if not os.path.isfile(path):
            raise FileNotFoundError('%s: %s not found' % (h['name'], path))
        zips[h['name']] = mame_src.RomZips([path])
    return zips

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
names the zip "/hbmame/<zip>": the file is then <games>/hbmame/<zip>. The
hack zips are complete sets, so the MRA needs no parent zip.

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
  hide_extras  the core's OSD has no Finishing Moves or Hidden Items for the
           set, and shows its own Move List and View Secrets instead of MK2's
           (the MRA's game id word carries the flag, no secrets table or
           fight variables are written): the hack changes the code and the
           moves those extras are built on

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

HACKS = [
    # Mortal Kombat II Plus, Beta 2: a changed rev L3.1 program (new
    # characters, moves and service-menu options), four changed graphics ROMs
    # and one changed sound ROM. HBMAME and FBNeo call it mk2p and list only
    # the seven files below; the core's mk2p.zip (in games/hbmame, apart from
    # MAME's mk2.zip) is a complete set of 20 files that also carries the
    # L3.1 / L1 files that did not change.
    dict(name='mk2p', parent='mk2', desc='Mortal Kombat II Plus (Beta 2, hack)',
         zip='mk2p.zip', hide_extras=True,
         files={
             'l3.1_mortal_kombat_ii_game_rom_uj12.uj12': '05ff15a9',   # program, even bytes
             'l3.1_mortal_kombat_ii_game_rom_ug12.ug12': 'b6d8ff5c',   # program, odd bytes
             'l1_mortal_kombat_ii_game_rom_ug16.ug16': 'b2af2798',     # graphics
             'l1_mortal_kombat_ii_game_rom_uj16.uj16': 'd70dd149',
             'l1_mortal_kombat_ii_game_rom_ug20.ug20': 'd05e970a',
             'l1_mortal_kombat_ii_game_rom_uj20.uj20': '0f9c9a12',
             'l1_mortal_kombat_ii_sound_rom_u2.u2': '65d11dd7',        # DCS sound data
         }),
    # NBA Jam Tournament Edition Special Edition 5.02: TE rebuilt from its source
    # with new players, CMOS options and samples (the author's whatsnew.txt).
    # A complete set with the parent's file names, kept in games/hbmame as
    # nbajamtese.zip (its own name, not MAME's nbajamte.zip): 16 files differ
    # (program, 12 graphics ROMs, two sound ROMs), 5 are the parent's own.
    dict(name='nbajamtese', parent='nbajamte', desc='NBA Jam Tournament Edition (SE rev 5.02, hack)',
         zip='nbajamtese.zip',
         files={
             'l4_nba_jam_tournament_game_rom_uj12.uj12': '08507007',   # program, even bytes
             'l4_nba_jam_tournament_game_rom_ug12.ug12': 'd784608e',   # program, odd bytes
             'l1_nba_jam_tournament_game_rom_ug16.ug16': 'c8da980e',   # graphics
             'l1_nba_jam_tournament_game_rom_ug17.ug17': '1b7ddbe9',
             'l1_nba_jam_tournament_game_rom_ug18.ug18': 'a182457b',
             'l1_nba_jam_tournament_game_rom_ug20.ug20': '9cd4f985',
             'l1_nba_jam_tournament_game_rom_ug22.ug22': '5427ca82',
             'l1_nba_jam_tournament_game_rom_ug23.ug23': '7755db95',
             'l1_nba_jam_tournament_game_rom_uj16.uj16': '205c5fb7',
             'l1_nba_jam_tournament_game_rom_uj17.uj17': 'cb08465f',
             'l1_nba_jam_tournament_game_rom_uj18.uj18': 'ed6b08a5',
             'l1_nba_jam_tournament_game_rom_uj20.uj20': '7a47f364',
             'l1_nba_jam_tournament_game_rom_uj22.uj22': '569b1ae5',
             'l1_nba_jam_tournament_game_rom_uj23.uj23': 'a659b604',
             'l1_nba_jam_tournament_u12_sound_rom.u12': '7be1622b',    # sound
             'l1_nba_jam_tournament_u13_sound_rom.u13': 'f939bfcb',
         }),
    # NBA Jam Rewind (the "NBA Rewind 4 Jam" hack of arcade-projects): Tournament
    # Edition rev 2.0 1-28-94 (by the program's bytes, not the 2.1 its readme
    # names) with 12 changed graphics ROMs (Jordan and Shaq added to the
    # teams), a changed u12 sample ROM and 2.0's program changed in ~2,600
    # bytes (a Big Head / Huge Head / Expanded Roster code at the player select
    # screen, Fatalities from the team select screen: the readme). The zips
    # name the program files like rev 2.1's (l2.1_...); the secret player
    # table, the power-ups and the cheats are 2.0's, at the same places.
    dict(name='nbajamre', parent='nbajamte2a', desc='NBA Jam Tournament Edition (Rewind, hack)',
         zip='nbajamre.zip',
         names={
             'l2_nba_jam_tournament_game_rom_uj12.uj12': 'l2.1_nba_jam_tournament_game_rom_uj12.uj12',
             'l2_nba_jam_tournament_game_rom_ug12.ug12': 'l2.1_nba_jam_tournament_game_rom_ug12.ug12',
         },
         files={
             'l2_nba_jam_tournament_game_rom_uj12.uj12': '9b3fc483',   # program, even bytes
             'l2_nba_jam_tournament_game_rom_ug12.ug12': '18e75204',   # program, odd bytes
             'l1_nba_jam_tournament_game_rom_ug16.ug16': 'b9a07a6f',   # graphics
             'l1_nba_jam_tournament_game_rom_ug17.ug17': '34c6bdb8',
             'l1_nba_jam_tournament_game_rom_ug18.ug18': 'fe18a6ef',
             'l1_nba_jam_tournament_game_rom_ug20.ug20': '67c8646b',
             'l1_nba_jam_tournament_game_rom_ug22.ug22': 'd41234d2',
             'l1_nba_jam_tournament_game_rom_ug23.ug23': '8d1af1a6',
             'l1_nba_jam_tournament_game_rom_uj16.uj16': 'ffa7db04',
             'l1_nba_jam_tournament_game_rom_uj17.uj17': '3af5b32e',
             'l1_nba_jam_tournament_game_rom_uj18.uj18': '9a6d36de',
             'l1_nba_jam_tournament_game_rom_uj20.uj20': '71d028f8',
             'l1_nba_jam_tournament_game_rom_uj22.uj22': '42196c84',
             'l1_nba_jam_tournament_game_rom_uj23.uj23': 'b5bf66f9',
             'l1_nba_jam_tournament_u12_sound_rom.u12': 'cd5d4532',    # sound
             'l1_nba_jam_tournament_u13_sound_rom.u13': 'e92fb0d3',
         }),
    # NBA Jam Rewind with the optional "Get that Bleep outta here" patches
    # (program and the two sound ROMs; the announcer says it):
    # the program differs from nbajamre's in 2 bytes (0x33D9E and 0x3415E of
    # the uj12 file's even bytes), the u12 and u13 samples are its own. Same
    # file names as nbajamre's.
    dict(name='nbajamreb', parent='nbajamte2a', desc='NBA Jam Tournament Edition (Rewind, Get that Bleep outta here, hack)',
         zip='nbajamreb.zip',
         names={
             'l2_nba_jam_tournament_game_rom_uj12.uj12': 'l2.1_nba_jam_tournament_game_rom_uj12.uj12',
             'l2_nba_jam_tournament_game_rom_ug12.ug12': 'l2.1_nba_jam_tournament_game_rom_ug12.ug12',
         },
         files={
             'l2_nba_jam_tournament_game_rom_uj12.uj12': '383cd3ec',   # program, even bytes
             'l2_nba_jam_tournament_game_rom_ug12.ug12': '18e75204',   # program, odd bytes (nbajamre's)
             'l1_nba_jam_tournament_game_rom_ug16.ug16': 'b9a07a6f',   # graphics
             'l1_nba_jam_tournament_game_rom_ug17.ug17': '34c6bdb8',
             'l1_nba_jam_tournament_game_rom_ug18.ug18': 'fe18a6ef',
             'l1_nba_jam_tournament_game_rom_ug20.ug20': '67c8646b',
             'l1_nba_jam_tournament_game_rom_ug22.ug22': 'd41234d2',
             'l1_nba_jam_tournament_game_rom_ug23.ug23': '8d1af1a6',
             'l1_nba_jam_tournament_game_rom_uj16.uj16': 'ffa7db04',
             'l1_nba_jam_tournament_game_rom_uj17.uj17': '3af5b32e',
             'l1_nba_jam_tournament_game_rom_uj18.uj18': '9a6d36de',
             'l1_nba_jam_tournament_game_rom_uj20.uj20': '71d028f8',
             'l1_nba_jam_tournament_game_rom_uj22.uj22': '42196c84',
             'l1_nba_jam_tournament_game_rom_uj23.uj23': 'b5bf66f9',
             'l1_nba_jam_tournament_u12_sound_rom.u12': '7061fbc0',    # sound
             'l1_nba_jam_tournament_u13_sound_rom.u13': '25edad0d',
         }),
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

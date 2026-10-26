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
hack zips are complete sets (every file, under the parent's file names), so
the MRA needs no parent zip.

Entry fields
  name     HBMAME set name (also the MRA's <setname>, which names the core's
           NVRAM and settings files, so the hack does not share the parent's)
  parent   MAME set it is a clone of
  desc     description (the MRA's file name and <name>)
  zip      file name in games/hbmame
  files    {file name in the zip: new CRC} - the parent's files that differ
  hide_extras  the core's OSD shows no Move List, Finishing Moves or Hidden
           Items for the set (the MRA's game id word carries the flag, no
           secrets table or fight variables are written): the hack changes
           the code and the moves those extras are built on

Copyright (C) 2026 Gm0rk - GPL-3.0-or-later
"""

import copy
import os

import mame_src

HACKS = [
    # Mortal Kombat II Plus, Beta 2: a changed rev L3.1 program (new
    # characters, moves and service-menu options), four changed graphics ROMs
    # and one changed sound ROM. HBMAME and FBNeo call it mk2p and list only
    # the seven files below; the mk2.zip the core uses also carries the
    # L3.1 / L1 files that did not change.
    dict(name='mk2p', parent='mk2', desc='Mortal Kombat II Plus (Beta 2, hack)',
         zip='mk2.zip', hide_extras=True,
         files={
             'l3.1_mortal_kombat_ii_game_rom_uj12.uj12': '05ff15a9',   # program, even bytes
             'l3.1_mortal_kombat_ii_game_rom_ug12.ug12': 'b6d8ff5c',   # program, odd bytes
             'l1_mortal_kombat_ii_game_rom_ug16.ug16': 'b2af2798',     # graphics
             'l1_mortal_kombat_ii_game_rom_uj16.uj16': 'd70dd149',
             'l1_mortal_kombat_ii_game_rom_ug20.ug20': 'd05e970a',
             'l1_mortal_kombat_ii_game_rom_uj20.uj20': '0f9c9a12',
             'l1_mortal_kombat_ii_sound_rom_u2.u2': '65d11dd7',        # DCS sound data
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
        for region in rs.regions.values():
            for ld in region.loads:
                if ld.name in h['files']:
                    ld.crc = h['files'][ld.name]
                    seen.add(ld.name)
        missing = set(h['files']) - seen
        if missing:
            raise ValueError('%s: files not in %s: %s' % (h['name'], h['parent'], sorted(missing)))
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

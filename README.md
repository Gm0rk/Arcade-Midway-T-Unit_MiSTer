# Williams/Midway T-Unit for [MiSTer](https://github.com/MiSTer-devel/Main_MiSTer/wiki)

> **AI disclosure:** this core was developed using AI and MAME as a reference.
> (Claude, by Anthropic - Opus 5.5 & Sonnet 5.5).

An FPGA implementation of the Williams/Midway T-Unit arcade board (1993-1994),
the TMS34010-based platform behind Mortal Kombat (T-Unit revisions), Mortal
Kombat II, NBA Jam, NBA Jam Tournament Edition and Judge Dredd.

## Table of Contents

- [Hardware](#hardware)
- [Games](#games)
- [Timing and resources](#timing-and-resources)
- [Features](#features)
- [OSD](#osd)
- [ROMs](#roms)
- [Credits and references](#credits-and-references)
- [License](#license)
- [Extra content](docs/ExtraContent.md)

## Hardware

| | |
|---|---|
| Main CPU | TMS34010 graphics system processor, 50 MHz master clock (6.25 MHz instruction clock) |
| Main RAM | 512 KB |
| Video | 512 x 512 x 16-bit frame store; DMA blitter with 1-8 bits per pixel, compressed rows, X/Y scaling, X/Y flip and four-edge clipping |
| Palette | 32768 colours, 15-bit RGB |
| Display | 8 MHz pixel clock, 400 x 254 visible, 54.7 Hz |
| Sound (ADPCM board) | MC6809E @ 2 MHz, YM2151, OKI M6295, 8-bit DAC |
| Sound (DCS board, Mortal Kombat II) | ADSP-2105 @ 10 MHz, banked sound ROMs, 16-bit DAC at 31.25 kHz |
| Protection | Per-game security chips on the 34010 bus and hidden RAM on the ADPCM board, as in MAME |

## Games

Each game has its own page in [`docs`](docs) with its versions, controls and
game-specific features. Everything the core adds, core-wide and per game, is
listed in [Extra content](docs/ExtraContent.md).

| Game | Main set | Title Screen | Gameplay |
|---|---|---|---|
| [Judge Dredd (location test)](docs/JudgeDredd.md) | jdreddp (rev TA1) | <img src="https://github.com/Gm0rk/Arcade-Midway-T-Unit_MiSTer/blob/main/media/Judge_Dredd.png" width="300" alt="Judge Dredd title screen"> | <img src="https://github.com/Gm0rk/Arcade-Midway-T-Unit_MiSTer/blob/main/media/Judge_Dredd_2.png" width="300" alt="Judge Dredd gameplay"> |
| [Mortal Kombat](docs/MortalKombat.md) | mk (rev 5.0) | <img src="https://github.com/Gm0rk/Arcade-Midway-T-Unit_MiSTer/blob/main/media/Mortal_Kombat.png" width="300" alt="Mortal Kombat title screen"> | <img src="https://github.com/Gm0rk/Arcade-Midway-T-Unit_MiSTer/blob/main/media/Mortal_Kombat_2.png" width="300" alt="Mortal Kombat gameplay"> |
| [Mortal Kombat II](docs/MortalKombatII.md) | mk2 (rev L3.1) | <img src="https://github.com/Gm0rk/Arcade-Midway-T-Unit_MiSTer/blob/main/media/Mortal_Kombat_II.png" width="300" alt="Mortal Kombat II title screen"> | <img src="https://github.com/Gm0rk/Arcade-Midway-T-Unit_MiSTer/blob/main/media/Mortal_Kombat_II_2.png" width="300" alt="Mortal Kombat II gameplay"> |
| [NBA Jam](docs/NBAJam.md) | nbajam (rev 3.01) | <img src="https://github.com/Gm0rk/Arcade-Midway-T-Unit_MiSTer/blob/main/media/NBA_Jam.png" width="300" alt="NBA Jam title screen"> | <img src="https://github.com/Gm0rk/Arcade-Midway-T-Unit_MiSTer/blob/main/media/NBA_Jam_2.png" width="300" alt="NBA Jam gameplay"> |
| [NBA Jam Tournament Edition](docs/NBAJamTE.md) | nbajamte (rev 4.0) | <img src="https://github.com/Gm0rk/Arcade-Midway-T-Unit_MiSTer/blob/main/media/NBA_Jam_TE.png" width="300" alt="NBA Jam Tournament Edition title screen"> | <img src="https://github.com/Gm0rk/Arcade-Midway-T-Unit_MiSTer/blob/main/media/NBA_Jam_TE_2.png" width="300" alt="NBA Jam Tournament Edition gameplay"> |

Other versions, prototypes and hacks are in the `_alternatives` folder of the
MRAs.

## Timing and resources

<!-- Update the cells from the Quartus reports of the latest compilation (these are Build 62's). -->
Built with Quartus Prime 17.0.2 Lite for the DE10-Nano (Cyclone V
5CSEBA6U23I7), timing model Slow 1100 mV 100 C. Figures are from the
compilation of Build 62 (2026-11-06). Timing is met on every clock, and so is
every hold, recovery, removal and minimum pulse width check.

| Clock | Frequency | Setup slack |
|---|---|---|
| System (core PLL) | 96 MHz | +0.409 ns |

| Resource | Used | Percent used |
|---|---|---|
| Logic (ALMs) | 33,206 / 41,910 | 79 % |
| Block RAM (M10K blocks) | 405 / 553 | 73 % |
| DSP blocks | 67 / 112 | 60 % |

## Features

- CRT Adjust by rmonic79, with CRT V-Size (experimental): makes the picture
  taller or shorter in up to 7 steps of 3 lines, in PVM mode (changes the
  lines per frame, for monitors that follow line rate changes) or Cabinet mode
  (keeps the native timing and blends neighbouring lines)
- Video Timing: the board's own 54.7 Hz, or 57 Hz for TVs that do not hold
  54.7 Hz (games run about 4 % faster, audio pitch is unchanged)
- CMOS saved as NVRAM: settings, audits and high scores survive power-off
  (saved when the OSD is opened, if the game changed them)
- Shortcuts to the hidden menus, screens and debug features of the games that
  have them; the core enters the codes for you
- Mortal Kombat, Mortal Kombat II: Move List, Finishing Moves and Fixed AI
  Difficulty; Mortal Kombat also has Reptile on demand (see the
  [Mortal Kombat page](docs/MortalKombat.md))
- A Cheats menu for every game: 24 cheats for Mortal Kombat, 44 for Mortal
  Kombat II, 26 for NBA Jam, up to 30 for NBA Jam Tournament Edition and 9 for
  Judge Dredd (infinite health, energy, lives, time and turbo, invincibility,
  power-ups, night mode and more; the list is on each game's page)
- Support for Mortal Kombat II Plus: its own Move List and View Secrets (the secret
  characters, the Kombat Kodes), Fixed AI Difficulty and four Cheats
- Support for NBA Jam Tournament Edition Special Edition 5.02 (a ROM hack): the
  Tournament Edition's extras, with the Special Edition's own secret players in
  the Secret Player List
- Support for NBA Jam Rewind (a ROM hack of the Tournament Edition rev 2.0),
  with and without "Get that Bleep outta here": the Tournament Edition's extras,
  including its 30 cheats and the Secret Player List, whose Versions column
  names Rewind (it has rev 2.0's players)
- NBA Jam, NBA Jam Tournament Edition: a Secret Player List with the cheat codes

## OSD

| Item | |
|---|---|
| Video Settings | Aspect ratio, scandoubler, scale, Video Timing, CRT Adjust |
| Move List | Mortal Kombat games: shows each fighter's moves over the game; with the OSD closed, Left or Right turns the page |
| Finishing Moves | Mortal Kombat, Mortal Kombat II: enters the chosen fatality at the next FINISH HIM/HER |
| Fixed AI Difficulty | Mortal Kombat, Mortal Kombat II, Mortal Kombat II Plus: the computer opponent's level, Off or 0 (easiest) to 9 |
| Cheats | Every game (Mortal Kombat II Plus included): select a cheat to switch it on or off (a mark shows it is on; all are off after a game loads); at most 8 cheat units can be on at once, and the game's page lists each cheat with the units it uses |
| View Secret Players | NBA Jam games: shows the secret players and cheat codes over the game; with the OSD closed, Left or Right turns the page |
| View Secrets | Mortal Kombat II Plus: shows how to unlock the secret characters, the Kombat Kodes and other secrets; with the OSD closed, Left or Right turns the page |
| DIP Switches | The game's DIP switches, with Service Credit and Tilt |
| Hidden Items | Hidden menus and screens, for the games that have them (named Secret Menus for Judge Dredd and Cheat Codes & Hidden Items for the NBA Jam games) |
| Service Mode | The cabinet's test switch |
| Pause when OSD is open | On by default |
| Reset / Reset and close OSD | Reset keeps the OSD open |

## ROMs

ROMs are **not** included in this repository; you need your own dumps of the
games.

Use **merged** ROM sets. Files are found by CRC. Put the zips in `games/mame`, 
the MRA files in `_Arcade` (other versions in `_Arcade/_alternatives`) 
and the core in `_Arcade/cores`. Mortal Kombat II Plus (`mk2p.zip`), the NBA Jam
Tournament Edition Special Edition 5.02 (`nbajamtese.zip`) and NBA Jam Rewind
(`nbajamre.zip`, and `nbajamreb.zip` for Get that Bleep outta here) go in
`games/hbmame`.

## Credits and references

- MAME T-Unit driver and video: Alex Pasadyn, Zsolt Vasvari, Ernesto Corvi,
  Aaron Giles (thanks to Kurt Mahan); MAME TMS34010 core, Williams ADPCM
  sound board, DCS sound board and ADSP-21xx core - the reference for this
  core's behaviour (the ADSP-2105 and the DCS board are ports of MAME's
  ADSP-21xx core and DCS board, Aaron Giles)
- Texas Instruments TMS34010 User's Guide
- mc6809 core: Greg Miller (synchronous version by Sorgelig)
- jt51 (YM2151) and jt6295 (OKI M6295): Jose Tejada (jotego)
- SDRAM controller and MiSTer framework: Sorgelig and the MiSTer-devel team
- CRT Adjust and CRT V-Size: Umberto Parisi (rmonic79), with Andrea Bogazzi
  (@asturur)
- [Template_MiSTer](https://github.com/MiSTer-devel/Template_MiSTer),
  [MiSTer-CRT-Adjust](https://github.com/rmonic79/MiSTer-CRT-Adjust)
- ppriest: [MiSTer-CoreSkill](https://github.com/ppriest/MiSTer-CoreSkill),
  the arcade core guidance used while developing and checking this core
- Cheats: the MAME cheat collection (cheat.txt, release 27 July 2025 for MAME
  0.279, https://www.mamecheat.co.uk) kept by Martin Pugh (Pugsy). The names
  its cheat.txt credits for the sets whose cheats the Cheats menu uses:
  - Mortal Kombat (mk): Abystus; Steph and ugetab; Pugsy (Clues, Secret Game
    Over, CPU Fatality, EJB Menu); nolberto82 (Hit Anywhere, One Button
    Fatalities)
  - Mortal Kombat II (mk2): ugetab; Pugsy (Clues, Secret Game Over, CPU
    Fatality, EJB Menu); nolberto82 (Hit Anywhere, Jade Low Kick Requirement,
    One Key Fatals); CLE (Automatic Fatality, Automatic Stage Fatality);
    syndromtr (the others)
  - NBA Jam (nbajam): Abystus (most of them); Pugsy (Invincibility on 3D Tank
    Game, Computer Assistance Off)
  - NBA Jam Tournament Edition: syndromtr, Abystus and Pugsy (nbajamte; the
    Special Edition's, nbajamtese, are some of these moved to where the hack
    keeps them; Rewind's, nbajamre and nbajamreb, are nbajamte2a's);
    syndromtr and Abystus (nbajamte1, nbajamte2a, nbajamte3)
  - Judge Dredd (jdreddp), NBA Jam rev 2.00 (nbajamr2) and the Tournament
    Edition sets nbajamte2, nbajamte3a and nbajamte4 are not in cheat.txt's
    list; their files point to it for the contributors. The cheats the core
    found in each game's program itself are not from the collection

## License

GPL-3.0-or-later. Third-party modules keep their own licenses (see `rtl/mc6809`,
`rtl/jt51`, `rtl/jt6295`, `rtl/crt_adjust`). The ADSP-2105 and DCS board ports
follow MAME code under BSD-3-Clause.

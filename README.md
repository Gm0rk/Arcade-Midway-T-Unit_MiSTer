# Williams/Midway T-Unit for [MiSTer](https://github.com/MiSTer-devel/Main_MiSTer/wiki)

> **AI disclosure:** this core was developed using AI and MAME as a reference.
> (Claude, by Anthropic - Opus 5.5 & Sonnet 5.5).

An FPGA implementation of the Williams/Midway T-Unit arcade board (1993-1994),
the TMS34010-based platform behind Mortal Kombat (T-Unit revisions), Mortal
Kombat II, NBA Jam, NBA Jam Tournament Edition and Judge Dredd.

## Table of Contents

- [Hardware](#hardware)
- [Games](#games)
- [Testing setup](#testing-setup)
- [Features](#features)
- [OSD](#osd)
- [Controls](#controls)
- [ROMs](#roms)
- [Credits and references](#credits-and-references)
- [License](#license)
- [Extra content](docs/ExtraContent.md)
- [Test plan](docs/TestPlan.md)

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

| Game | Main set | Status | Title Screen | Gameplay |
|---|---|---|---|---|
| [Judge Dredd (location test)](docs/JudgeDredd.md) | jdreddp (rev TA1) | Awaiting MiSTer hardware test | <img src="https://github.com/Gm0rk/Arcade-Midway-T-Unit_MiSTer/blob/main/media/Judge_Dredd.png" width="300" alt="Judge Dredd title screen"> | <img src="https://github.com/Gm0rk/Arcade-Midway-T-Unit_MiSTer/blob/main/media/Judge_Dredd_2.png" width="300" alt="Judge Dredd gameplay"> |
| [Mortal Kombat](docs/MortalKombat.md) | mk (rev 5.0) | Awaiting MiSTer hardware test | <img src="https://github.com/Gm0rk/Arcade-Midway-T-Unit_MiSTer/blob/main/media/Mortal_Kombat.png" width="300" alt="Mortal Kombat title screen"> | <img src="https://github.com/Gm0rk/Arcade-Midway-T-Unit_MiSTer/blob/main/media/Mortal_Kombat_2.png" width="300" alt="Mortal Kombat gameplay"> |
| [Mortal Kombat II](docs/MortalKombatII.md) | mk2 (rev L3.1) | Awaiting MiSTer hardware test | <img src="https://github.com/Gm0rk/Arcade-Midway-T-Unit_MiSTer/blob/main/media/Mortal_Kombat_II.png" width="300" alt="Mortal Kombat II title screen"> | <img src="https://github.com/Gm0rk/Arcade-Midway-T-Unit_MiSTer/blob/main/media/Mortal_Kombat_II_2.png" width="300" alt="Mortal Kombat II gameplay"> |
| [NBA Jam](docs/NBAJam.md) | nbajam (rev 3.01) | Awaiting MiSTer hardware test| <img src="https://github.com/Gm0rk/Arcade-Midway-T-Unit_MiSTer/blob/main/media/NBA_Jam.png" width="300" alt="NBA Jam title screen"> | <img src="https://github.com/Gm0rk/Arcade-Midway-T-Unit_MiSTer/blob/main/media/NBA_Jam_2.png" width="300" alt="NBA Jam gameplay"> |
| [NBA Jam Tournament Edition](docs/NBAJamTE.md) | nbajamte (rev 4.0) | Awaiting MiSTer hardware test | <img src="https://github.com/Gm0rk/Arcade-Midway-T-Unit_MiSTer/blob/main/media/NBA_Jam_TE.png" width="300" alt="NBA Jam Tournament Edition title screen"> | <img src="https://github.com/Gm0rk/Arcade-Midway-T-Unit_MiSTer/blob/main/media/NBA_Jam_TE_2.png" width="300" alt="NBA Jam Tournament Edition gameplay"> |

Verified on MiSTer hardware: `[░░░░░░░░░░░░░░░░░░░░]` 0 / 5

A game is verified when it passes its section of the
[test plan](docs/TestPlan.md) and the core-wide tests (optional tests aside);
the test plan tracks the progress. The tests are run on MiSTer hardware (see
[Testing setup](#testing-setup)), not on an original T-Unit arcade PCB.

Other versions, prototypes and hacks are in the `_alternatives` folder of the
MRAs.

## Testing setup

The tests behind the status above are run on MiSTer hardware, with this setup
(the core has not been verified against an original T-Unit board):

| | |
|---|---|
| MiSTer | DE10-Nano with the Analog I/O Board and 128 MB SDRAM |
| Analog connection | Component (YPbPr) |
| Digital connection | HDMI |
| Consumer NTSC CRT | Sony KV-27FS120 |
| Broadcast PVM | Sony PVM-14L5 |
| Controllers | DualShock 4 (Bluetooth), Xbox 360 (USB) |

> **Not tested:** consumer PAL TVs, and analog connections other than
> component (YPbPr).

## Features

- CRT Adjust by rmonic79 (H-Size, H-Position, V-Shift and Auto-Width) for
  analog CRT output. CRT V-Size (experimental), part of CRT Adjust, makes the
  picture taller ("+") or shorter ("-"), up to 7 steps of 3 lines (about 1 %
  each), applied one line per frame, in one of two modes:
  - PVM: retimes the frame (fewer, longer lines for a taller picture, more,
    shorter lines for a shorter one), so every picture line is shown once and
    nothing is blended, but the line rate moves about 0.4 % per line. For
    monitors that hold a wide range of line rates (PVM/BVM and similar)
  - Cabinet: keeps the board's exact timing and spreads each picture line's
    light over the screen's fixed lines, as a monitor's own V-Size control
    would (a very slight vertical softness). For arcade monitors and TVs that
    will not follow a change of line rate
  - Limits: in PVM mode the frame has few spare lines at the larger +
    settings, so V-Shift has little room there; at the larger - settings the
    lines get short enough that the picture moves a little to the left
    (H-Position brings it back). With the 57 Hz Video Timing there is even
    less room around the picture, so a taller picture is cut at the top or
    bottom. Like the rest of CRT Adjust, CRT V-Size also changes the HDMI
    picture; leave CRT Adjust off for an untouched HDMI image
- Video Timing: the board's own 54.7 Hz, or 57 Hz frames for TVs that do
  not hold 54.7 Hz. Only blank lines are dropped, so the whole picture is
  still sent; games run about 4 % faster, while music and voices keep their
  normal pitch and tempo
- CMOS saved as NVRAM: settings, audits and high scores survive power-off
  (written to the SD card when the OSD is opened, if the game changed them,
  and with "Save Settings")
- DIP switches in the OSD, taken from MAME, in alphabetical order; switches
  a version does not use (its own DIP switch screen marks them unused) are
  left out. The games read most of them at power-up: reset after a change
- Service Mode, Service Credit and Tilt in the OSD (on the DIP Switches page,
  selecting Service Credit or Tilt adds a credit or slams the tilt switch);
  pause from a button or while the OSD is open
- The hidden menus, screens and debug features the programmers left in the
  games, on an OSD page of each game (Judge Dredd: Secret Menus, Mortal
  Kombat games: Hidden Items, NBA Jam games: Cheat Codes & Hidden Items),
  with messages saying whether a code was taken, what a set finishing move is
  waiting for, and what an option just turned on does (or that the loaded
  version does not have it)
- Mortal Kombat: Reptile's fight, the moon silhouettes and his hints on
  demand (see the [Mortal Kombat page](docs/MortalKombat.md))
- Mortal Kombat, Mortal Kombat II: a Move List (every fighter's special moves
  and finishing moves, with the distance each finishing move needs, over the
  game's title screen), Finishing Moves (every fighter's finishing moves,
  entered for you at FINISH HIM) and Fixed AI Difficulty (the computer
  opponent's level held at 0 (easiest) to 9, or Off); Mortal Kombat II Plus
  has Fixed AI Difficulty only
- NBA Jam, NBA Jam Tournament Edition: the power-up codes for all players and
  the codes of the Tonight's Match-Up screen (NBA Jam's hidden tank game,
  TE's tournament mode); a Secret Player List (every secret player's name,
  initials, birthday and versions, and every cheat code as the players enter
  it) over the game's title screen

## OSD

| Item | |
|---|---|
| Video Settings | Aspect ratio, scandoubler, scale, Video Timing, CRT Adjust (CRT Auto-Width, H-Size, H-Position, V-Shift, V-Size, V-Size Mode: shown while CRT Adjust is On) |
| Move List | Mortal Kombat: Off, List 1, List 2; Mortal Kombat II: Off or a fighter. Shows the moves over the game's title screen; the game waits while it is shown |
| Finishing Moves | Mortal Kombat, Mortal Kombat II: each fighter's finishing moves, entered for you at the next FINISH HIM |
| Fixed AI Difficulty | Mortal Kombat, Mortal Kombat II: Off, or 0 (easiest) to 9; the computer opponent's level in 1-player games (not applied while the test menu is selected) |
| View Secret Players | NBA Jam: Off, Page 1, Page 2; NBA Jam Tournament Edition: Off, Page 1 to Page 6. Shows the secret players and the cheat codes over the game's title screen; the game waits while it is shown |
| DIP Switches | The game's DIP switches in alphabetical order, with Service Credit and Tilt (selecting the line adds a credit or slams the tilt switch) |
| Hidden Items | Hidden menus, cheats and extras, only for the games that have them: Secret Menus for Judge Dredd, Hidden Items for the Mortal Kombat games, Cheat Codes & Hidden Items for the NBA Jam games |
| Service Mode | The cabinet's test switch |
| Pause when OSD is open | On by default |
| Reset / Reset and close OSD | Reset keeps the OSD open |

Hidden menus are opened by codes on the controls, which the core enters for
you: pick the item, and the OSD closes and the code plays (a few seconds;
the controls are ignored meanwhile). The games only accept these codes in
the attract mode, so use them with no game running. The NBA Jam games' Tank
Game and Tournament Mode are codes of the Tonight's Match-Up screen: pick
them while it shows (with "Pause when OSD is open", the game waits while
you do). The other items are options: they stay set until switched off,
and take effect at once unless the game's page says otherwise. When the OSD
closes, a message says whether a code was taken, and what an option just
turned on does. Each game's page lists its items.

## Controls

Every game has Start, Coin, Test (service mode) and Pause, plus its own
buttons, named in the controller setup and listed on its page. Judge Dredd
plays up to three players, Mortal Kombat and Mortal Kombat II two, NBA Jam
and NBA Jam Tournament Edition four.

## ROMs

ROMs are **not** included in this repository; you need your own dumps of the
games.

Use **merged** ROM sets from MAME 0.289 (recommended): one zip per game holds
every version, so all of that game's MRAs, main and alternatives, find their
files. Mortal Kombat's merged set is `mk.zip`; the other zip names are on
each game's page. Files are found by CRC.

Put the zips in `games/mame`, the MRA files in `_Arcade` (other versions in
`_Arcade/_alternatives`) and the core in `_Arcade/cores`. Mortal Kombat II
Plus is a hack that is not in MAME: its `mk2.zip` goes in `games/hbmame`.

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

## License

GPL-3.0-or-later. Third-party modules keep their own licenses (see `rtl/mc6809`,
`rtl/jt51`, `rtl/jt6295`, `rtl/crt_adjust`). The ADSP-2105 and DCS board ports
follow MAME code under BSD-3-Clause.

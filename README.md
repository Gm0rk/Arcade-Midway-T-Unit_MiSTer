# Williams/Midway T-Unit for [MiSTer](https://github.com/MiSTer-devel/Main_MiSTer/wiki)

> **AI disclosure:** this core was developed with the help of an AI assistant
> (Claude, by Anthropic).

An FPGA implementation of the Midway T-Unit arcade board (1993-1994), the
TMS34010-based platform behind Mortal Kombat (T-Unit revisions), Mortal
Kombat II, NBA Jam, NBA Jam Tournament Edition and Judge Dredd.

> **Status:** the core is currently undergoing testing. It can be compiled and is playable in its
> current state, but bugs are expected. Issues and pull requests are not
> accepted at the moment.

## Contents

- [Hardware](#hardware)
- [Games](#games)
- [Features](#features)
- [CRT V-Size (experimental)](#crt-v-size-experimental)
- [ROMs](#roms)
- [Credits and references](#credits-and-references)
- [License](#license)

## Hardware

| | |
|---|---|
| Main CPU | TMS34010 graphics system processor, 50 MHz master clock (6.25 MHz instruction clock) |
| Main RAM | 512 KB |
| Video | 512 x 512 x 16-bit frame store; DMA blitter with 1-8 bits per pixel, compressed rows, X/Y scaling, X/Y flip and four-edge clipping |
| Palette | 32768 colours, 15-bit RGB |
| Display | 8 MHz pixel clock, 400 x 254 visible, 54.7 Hz |
| Sound (ADPCM board) | MC6809E @ 2 MHz, YM2151, OKI M6295, 8-bit DAC |
| Sound (DCS board, MK2) | ADSP-2105 @ 10 MHz, banked sound ROMs, 16-bit DAC at 31.25 kHz |
| Protection | Per-game security chips on the 34010 bus and hidden RAM on the ADPCM board, as in MAME |

## Games

Each game has its own page: its versions, controls, Secrets (for the NBA
Jam games with the secret players) and, for the Mortal Kombat games, the
Move List and Finishing Moves.

| Game | Sound | Players | Status |
|---|---|---|---|
| [Mortal Kombat](docs/MortalKombat.md) | ADPCM | 2 | [Awaiting hardware test](docs/TestPlan.md#mortal-kombat) |
| [Mortal Kombat II](docs/MortalKombatII.md) | DCS | 2 | [Awaiting hardware test](docs/TestPlan.md#mortal-kombat-ii) |
| [NBA Jam](docs/NBAJam.md) | ADPCM | 4 | [Awaiting hardware test](docs/TestPlan.md#nba-jam) |
| [NBA Jam Tournament Edition](docs/NBAJamTE.md) | ADPCM | 4 | [Awaiting hardware test](docs/TestPlan.md#nba-jam-tournament-edition) |
| [Judge Dredd (location test)](docs/JudgeDredd.md) | ADPCM | 3 | [Awaiting hardware test](docs/TestPlan.md#judge-dredd) |

Verified on hardware: `[░░░░░░░░░░░░░░░░░░░░]` 0 / 5

Progress is tracked in the [test plan](docs/TestPlan.md): a game counts as
verified when its section and the core-wide tests pass (optional tests
aside).

## Features

- Analog sync centred on a standard 15 kHz screen; CRT Adjust (H-Size,
  H-Position, V-Shift), CRT V-Size (experimental) and CRT Auto-Width for
  analog CRT output
- CMOS saved as NVRAM: settings, audits and high scores survive power-off
  (written to the SD card when the OSD is opened, if the game changed them,
  and with "Save Settings")
- DIP switches in the OSD, taken from MAME, in alphabetical order
- Start, Coin, Test (service mode) and Pause (button or OSD) in every game;
  Service Credit and Tilt on the OSD's DIP Switches page (selecting the
  line adds a credit or slams the tilt switch), Service Mode in the OSD's
  main menu
- The hidden menus, screens and debug features the programmers left in the
  games, on an OSD page of each game (Judge Dredd: Secret Menus, Mortal
  Kombat games: Hidden Items, NBA Jam games: Cheat Codes & Hidden Items);
  for NBA Jam and NBA Jam Tournament Edition, the power-up codes for all
  players and the codes of the Tonight's Match-Up screen (NBA Jam's hidden
  tank game, TE's tournament mode)
- Secret Player List window (NBA Jam, NBA Jam Tournament Edition): every
  secret player's name, initials, birthday and versions, and every cheat
  code as the players enter it, over the game's title screen
- Finishing Moves page in the OSD (Mortal Kombat, Mortal Kombat II): every
  fighter's finishing moves, entered for you at FINISH HIM
- Move List window (Mortal Kombat, Mortal Kombat II): every fighter's special
  moves and finishing moves, with the distance each finishing move needs,
  over the game's title screen
- OSD messages: what a set finishing move is waiting for, whether a code was
  taken, what an option just turned on does (or that the loaded version
  does not have it)

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

## CRT V-Size (experimental)

With CRT Adjust on, CRT V-Size makes the picture taller (+) or shorter (-),
3 lines per step, up to 21 lines; V-Shift then recentres it. A change is
applied one line per frame. It works in one of two modes (CRT V-Size Mode):

| Mode | How | For |
|---|---|---|
| PVM | The frame is retimed: fewer, longer lines make the picture taller, more, shorter lines make it shorter. Every picture line is shown once, nothing is blended. The line rate moves by about 0.4 % per line | Broadcast and studio monitors (PVM/BVM and the like) that follow a wide range of line rates |
| Cabinet | The timing stays exactly the board's; each picture line's light is spread over the screen's fixed lines, as a monitor's own V-Size control would. The picture is very slightly softer vertically | Arcade monitors and TVs that do not follow line-rate changes |

In PVM mode the frame has few spare lines at the larger + settings, so V-Shift
has little room there; at the larger - settings the lines get short enough that
the picture moves a little to the left (H-Position brings it back). Like the
rest of CRT Adjust, CRT V-Size also changes the HDMI picture; leave CRT Adjust
off for an untouched HDMI image.

## ROMs

ROMs are not included in this repository; you need your own copies.

Use **merged** ROM sets (recommended), following MAME 0.289: one zip per game
holds every version, and each MRA finds its files there.

| Game | Zip |
|---|---|
| Mortal Kombat | `mk.zip` (the same zip as the Y Unit Mortal Kombat sets) |
| Mortal Kombat II | `mk2.zip` |
| NBA Jam | `nbajam.zip` |
| NBA Jam Tournament Edition | `nbajamte.zip` |
| Judge Dredd | `jdreddp.zip` |

Put the zips in `games/mame`. The MRA files go in `_Arcade` (other versions
in `_Arcade/_alternatives`), the core in `_Arcade/cores`.

## Credits and references

- MAME T-Unit driver and video: Alex Pasadyn, Zsolt Vasvari, Ernesto Corvi,
  Aaron Giles (thanks to Kurt Mahan); MAME TMS34010 core, Williams ADPCM
  sound board, DCS sound board and ADSP-21xx core - the reference for this
  core's behaviour
- Texas Instruments TMS34010 User's Guide
- ADSP-2105 and DCS board: from the Killer Instinct MiSTer core
  ([Arcade-KillerInstinct_MiSTer](https://github.com/MiSTer-devel/Arcade-KillerInstinct_MiSTer))
- mc6809 core: Greg Miller (synchronous version by Sorgelig)
- jt51 (YM2151) and jt6295 (OKI M6295): Jose Tejada (jotego)
- SDRAM controller and MiSTer framework: Sorgelig and the MiSTer-devel team
- CRT Adjust and CRT V-Size: Umberto Parisi (rmonic79); CRT Adjust with
  Andrea Bogazzi (@asturur)
- [Template_MiSTer](https://github.com/MiSTer-devel/Template_MiSTer),
  [MiSTer-CRT-Adjust](https://github.com/rmonic79/MiSTer-CRT-Adjust)

## License

GPL-3.0-or-later. Third-party modules keep their own licenses (see `rtl/mc6809`,
`rtl/jt51`, `rtl/jt6295`, `rtl/crt_adjust`); the DCS files in `rtl/dcs`, from
the Killer Instinct core, are GPL-3.0-only.

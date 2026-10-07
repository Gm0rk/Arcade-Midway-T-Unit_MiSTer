# Williams/Midway T-Unit for [MiSTer](https://github.com/MiSTer-devel/Main_MiSTer/wiki)

An FPGA implementation of the Midway T-Unit arcade board (1993-1994), the
TMS34010-based platform behind Mortal Kombat (T-Unit revisions), Mortal
Kombat II, NBA Jam, NBA Jam Tournament Edition and Judge Dredd.

## Contents

- [Hardware](#hardware)
- [Games](#games)
- [Features](#features)
- [CRT V-Size (experimental)](#crt-v-size-experimental)
- [Controls](#controls)
- [Secrets](#secrets)
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

| Game | MRA set | Sound | Status |
|---|---|---|---|
| Mortal Kombat | mk (rev 5.0 T-Unit) + rev 4.0, Turbo Ninja hack | ADPCM | Awaiting hardware test |
| Mortal Kombat II | mk2 (rev L3.1) + L3.2, L3.1E, L3.0, L2.1, L2.0, L1.4, L1.1, L4.2 / L9.1 / Challenger hacks | DCS | Awaiting hardware test |
| NBA Jam | nbajam (rev 3.01) + rev 2.00, 1.00, proto 2.00, 1.01 | ADPCM | Awaiting hardware test |
| NBA Jam Tournament Edition | nbajamte (rev 4.0) + 4.0, 3.0 (x2), 2.1, 2.0, 1.00, proto 2.00, Nani Edition | ADPCM | Awaiting hardware test |
| Judge Dredd (location test) | jdreddp (rev TA1) | ADPCM | Awaiting hardware test |

Verified on hardware: `[░░░░░░░░░░░░░░░░░░░░]` 0 / 5

## Features

- Analog sync centred on a standard 15 kHz screen; CRT Adjust (H-Size,
  H-Position, V-Shift), CRT V-Size (experimental) and CRT Auto-Width for
  analog CRT output
- CMOS saved as NVRAM: settings, audits and high scores survive power-off
  (OSD "Save Settings")
- DIP switches in the OSD, taken from MAME
- Up to four players (NBA Jam, NBA Jam TE) or three (Judge Dredd)
- Pause (button or OSD), service mode switch; Service Credit and Tilt in the OSD
- Secrets page in the OSD: hidden menus, screens and debug features of every
  game (see below)

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

## Controls

| Game | Buttons |
|---|---|
| Mortal Kombat / Mortal Kombat II | High Punch, Block, High Kick, Low Punch, Low Kick, Block 2 |
| NBA Jam / NBA Jam TE | Turbo, Shoot / Block, Pass / Steal; up to 4 players |
| Judge Dredd | Kick, Jump, Punch, Crouch; up to 3 players |

Every game also has Start, Coin, Test (service mode) and Pause. Service
Credit and Tilt are OSD items on the Controls page.

## Secrets

The OSD's Secrets page opens the hidden menus and screens the programmers
left in the games. The menus are opened by codes entered on the controls,
which the core enters for you: pick the item, and the OSD closes and the
code plays (a few seconds; the controls are ignored meanwhile). The games
only accept them in the attract mode, so use them with no game running.
Both Mortal Kombat games drop a half-entered code when the attract mode moves
to its next screen; the core then enters the EJB code again (three tries at
most). The options take effect at once and stay set until switched off.

| Game | OSD item | What it does |
|---|---|---|
| Mortal Kombat | EJB Menu | The programmers' menu ("Mortal Kombat EJB Menu"): diagnostics, coin bookkeeping, game audits, a hidden Hello page, initials entry and every character's ending |
| | EJB Menu (Copyright Screen) | The same menu, after a hidden copyright screen ("This is Mortal Kombat") |
| Mortal Kombat II | EJB Menu | MK2's EJB menu, with the same pages. Revisions L1.1 and L1.4 have the menu and its code but never check for the code; the core connects it while the code plays |
| | Security Screen | Each attract cycle starts with a hidden screen, "This version passed the security test", after a few seconds of black |
| | Hitboxes | A debug feature left in the game: the hit box of every attack is drawn in green during fights |
| | Pong at Battle 250 | Every two-player battle counts as battle 250: the VS screen shows "Kombat Zone: Back in Time", and after the first round both players face a game of Pong (rev L2.0 and later) |
| NBA Jam / NBA Jam TE | Secret Menu | The design team screen, then the secret Midway menu with the Jam Info statistics (hidden audit pages on the older NBA Jam revisions) |
| Judge Dredd | Secret Audits | Six hidden audit pages; any button turns the page |
| | Secret Audits + Credits | Turns through the audits and holds both Start buttons at the end, which shows the staff credits |

## ROMs

ROM sets follow MAME 0.289. Put the zips (merged sets are fine, files are
found by CRC) in `games/mame`; the Mortal Kombat T-Unit sets use `mk.zip`
(the same zip as the Y Unit Mortal Kombat sets). The MRA files go in
`_Arcade`, the core in `_Arcade/cores`.

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

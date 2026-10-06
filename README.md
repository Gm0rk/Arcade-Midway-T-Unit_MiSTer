# Williams/Midway T-Unit for [MiSTer](https://github.com/MiSTer-devel/Main_MiSTer/wiki)

An FPGA implementation of the Midway T-Unit arcade board (1993-1994), the
TMS34010-based platform behind Mortal Kombat (T-Unit revisions), Mortal
Kombat II, NBA Jam, NBA Jam Tournament Edition and Judge Dredd.

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
  H-Position, V-Shift) and CRT Auto-Width for analog CRT output
- CMOS saved as NVRAM: settings, audits and high scores survive power-off
  (OSD "Save Settings")
- DIP switches in the OSD, taken from MAME
- Up to four players (NBA Jam, NBA Jam TE) or three (Judge Dredd)
- Pause (button or OSD), service mode switch; Service Credit and Tilt in the OSD

## Controls

| Game | Buttons |
|---|---|
| Mortal Kombat / Mortal Kombat II | High Punch, Block, High Kick, Low Punch, Low Kick, Block 2 |
| NBA Jam / NBA Jam TE | Turbo, Shoot / Block, Pass / Steal; up to 4 players |
| Judge Dredd | Kick, Jump, Punch, Crouch; up to 3 players |

Every game also has Start, Coin, Test (service mode) and Pause. Service
Credit and Tilt are OSD items on the Controls page.

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
- CRT Adjust: Umberto Parisi (rmonic79), with Andrea Bogazzi (@asturur)
- [Template_MiSTer](https://github.com/MiSTer-devel/Template_MiSTer),
  [MiSTer-CRT-Adjust](https://github.com/rmonic79/MiSTer-CRT-Adjust)

## License

GPL-3.0-or-later. Third-party modules keep their own licenses (see `rtl/mc6809`,
`rtl/jt51`, `rtl/jt6295`, `rtl/crt_adjust`); the DCS files in `rtl/dcs`, from
the Killer Instinct core, are GPL-3.0-only.

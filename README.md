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
- [Finishing Moves](#finishing-moves)
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
  (written to the SD card when the OSD is opened, if the game changed them,
  and with "Save Settings")
- DIP switches in the OSD, taken from MAME
- Up to four players (NBA Jam, NBA Jam TE) or three (Judge Dredd)
- Pause (button or OSD), service mode switch; Service Credit and Tilt in the OSD
- Secrets page in the OSD: hidden menus, screens and debug features of every
  game (see below)
- Finishing Moves page in the OSD (Mortal Kombat and Mortal Kombat II): every
  fighter's fatalities, friendships, babalities and stage moves, entered for
  you at FINISH HIM (see below)
- OSD messages: what a set finishing move is waiting for, whether a secrets
  code was taken, what a Secrets option just turned on does

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
When the OSD closes, a message says whether a code's menu opened, and what
an option just turned on does.

| Game | OSD item | What it does |
|---|---|---|
| Mortal Kombat | EJB Menu | The programmers' menu ("Mortal Kombat EJB Menu"): diagnostics, coin bookkeeping, game audits, a hidden Hello page, initials entry and every character's ending |
| | EJB Menu (Copyright Screen) | The same menu, after a hidden copyright screen ("This is Mortal Kombat") |
| Mortal Kombat II | EJB Menu | MK2's EJB menu, with the same pages. Revisions L1.1 and L1.4 have the menu and its code but never check for the code; the core connects it while the code plays |
| | Security Screen | Each attract cycle starts with a hidden screen, "This version passed the security test", after a few seconds of black |
| | Hitboxes | A debug feature left in the game: the hit box of every attack is drawn in green during fights |
| | Pong at Battle 250 | Every two-player battle counts as battle 250: the VS screen shows "Kombat Zone: Back in Time", and after the first round both players face a game of Pong (rev L2.0 and later) |
| | Noob Saibot Fight | The fight the game keeps for a player with 50 wins in a row: in a two-player battle, the winner of the first round goes on to fight Noob Saibot ("Incredible winning streak!!"). The game then carries on as after a real streak (rev L3.0 and later) |
| | Jade Fight | In a one-player game, the first round you win is followed by the fight against Jade ("Now you must battle with an undiscovered warrior from Mortal Kombat One"). Normally that takes winning a round with Low Kicks only in the battle before the "?" on the tower (rev L2.0 and later) |
| | Smoke Fight | Hold Down and press Start during any fight to fight Smoke next ("You have found the passage from the Outworld to the Earth Realm"). Normally that only works on The Portal while the "Toasty!" man is on screen (rev L2.0 and later) |
| NBA Jam / NBA Jam TE | Secret Menu | The design team screen, then the secret Midway menu with the Jam Info statistics (hidden audit pages on the older NBA Jam revisions) |
| Judge Dredd | Secret Audits | Six hidden audit pages; any button turns the page |
| | Secret Audits + Credits | Turns through the audits and holds both Start buttons at the end, which shows the staff credits |

## Finishing Moves

The OSD's Finishing Moves page (Mortal Kombat and Mortal Kombat II) enters a
fighter's finishing moves for you. Pick the Fighter, then one of the moves
listed under it: the OSD closes and the move is set. It plays at the next
FINISH HIM where that fighter is the winner, for either player. With "Pause
when OSD is open" (the default) you can open the OSD at FINISH HIM and pick
the move then.

When the loser stands dizzy and the winner stands still, the core takes the
winner's controls (the player's own are ignored meanwhile) and enters the
move. Many moves only work at a certain distance: when the fighters are too
far apart or too close, a message says so and the move waits; step in or
out and it goes as soon as the distance fits. Messages also say when a stage
move is set on another stage, when FINISH HIM ends before the move could
start (the move stays set for the next one) and when the game did not take
the move. A move is used once; "Clear the set move" drops a set move.

Commands as the games read them: F toward the opponent, B away, U up, D
down; HP / LP / HK / LK / BL High Punch, Low Punch, High Kick, Low Kick,
Block. (X) means X held during the rest of the command and let go at the
end, (X 2 s) held for about 2 seconds. Distances are in pixels between the
two fighters (the screen is 400 wide; standing against each other is about
62 in MK2). Pit / Spikes works on The Pit II and the Kombat Tomb (Shang
Tsung's Pit only on The Pit II), the Dead Pool on The Dead Pool, Mortal
Kombat's The Pit on The Pit. Friendships and babalities (MK2) need a round
won without High or Low Punch: the game's rule. Two MK2 fatalities are not
in the list because they need a button held from before FINISH HIM: Shang
Tsung's Kintaro (Low Punch for about 18 seconds) and Raiden's Super Uppercut
(High Punch for about 7 seconds).

The early MK2 revisions have fewer moves: L2.0 and L2.1 have no Dead Pool
and no Kung Lao friendship, and Shang Tsung's friendship and Pit differ
there; L1.1 and L1.4 lack most friendships, babalities and stage moves and
some fatalities. Picking one of those shows "Not available in this revision
of the game".

**Mortal Kombat II**

| Fighter | Move | Command | Distance |
|---|---|---|---|
| Liu Kang | Dragon | D F B B HK | up to 108 |
|  | Cartwheel | D F U B D | up to 196 |
|  | Friendship | F B B B LK | any |
|  | Babality | D D F B LK | any |
|  | Pit / Spikes | B F F LK | close (up to 70) |
| Kung Lao | Hat Throw | (LP) B F | 260 or more |
|  | Decapitation | F F F LK | 100-124 |
|  | Friendship | B B B D HK | any |
|  | Babality | B B F F HK | any |
|  | Pit / Spikes | F F F HP | close (up to 70) |
| Johnny Cage | Torso Rip | D D F F LP | close (up to 68) |
|  | Decapitation | F F D U | close (up to 70) |
|  | Friendship | D D D D HK | any |
|  | Babality | B B B HK | any |
|  | Pit / Spikes | D D D HK | close (up to 70) |
| Reptile | Tongue | B B D LP | 164-220 |
|  | Slice | U U D HP, then F F D HK | close (up to 68) |
|  | Friendship | B B D LK | any |
|  | Babality | D B B LK | any |
|  | Pit / Spikes | D F F BL | close (up to 70) |
| Sub-Zero | Deep Freeze | F F D HK, then F D F F HP | 116-188 |
|  | Ice Grenade | (LP) B B D F | 260 or more |
|  | Friendship | B B D HK | any |
|  | Babality | D B B HK | any |
|  | Pit / Spikes | D F F BL | close (up to 70) |
| Shang Tsung | Soul Drain | U D U LK | close (up to 78) |
|  | Spikes | (HK 1 s) | 84-116 |
|  | Friendship | B B D F HK | any |
|  | Babality | B F D HK | any |
|  | Pit | D D U D | close (up to 70) |
| Kitana | Fan Decap | BL BL BL HK | close (up to 70) |
|  | Kiss of Death | (LK) F F D F | close (up to 68) |
|  | Friendship | D D D U LK | any |
|  | Babality | D D D LK | any |
|  | Pit / Spikes | F D F HK | close (up to 70) |
| Jax | Arm Rip | BL BL BL BL LP | 72-124 |
|  | Head Smash | (LP) F F F | close (up to 80) |
|  | Friendship | D D U U LK | any |
|  | Babality | D U D U LK | any |
|  | Pit / Spikes | U U D LK | close (up to 70) |
| Mileena | Sai Stab | F B F LP | close (up to 74) |
|  | Inhale | (HK 2 s) | close (up to 68) |
|  | Friendship | D D D U HK | any |
|  | Babality | D D D HK | any |
|  | Pit / Spikes | F D F LK | close (up to 70) |
| Baraka | Decapitation | B B B B HP | up to 96 |
|  | Impale | B F D F LP | up to 132 |
|  | Friendship | U F F HK | any |
|  | Babality | F F F HK | any |
|  | Pit / Spikes | F F D HK | close (up to 70) |
| Scorpion | Toasty | D D U U HP | any |
|  | Torch | U U HP | 148-172 |
|  | Slice | (HP) D F F F | close (up to 68) |
|  | Friendship | B B D HK | any |
|  | Babality | D B B HK | any |
|  | Pit / Spikes | D F F BL | close (up to 70) |
| Raiden | Electrocution | (LK 2 s) | close (up to 64) |
|  | Friendship | D B F HK | 164 or more |
|  | Babality | D D U HK | any |
|  | Pit / Spikes | U U HP | close (up to 70) |

Every fighter also has the Dead Pool: D+LP+LK HP, close (up to 76).

**Mortal Kombat**

| Fighter | Move | Command | Distance |
|---|---|---|---|
| Johnny Cage | Decapitation | F F F HP | close (up to 60) |
| Kano | Heart Rip | B D F LP | up to 84 |
| Sub-Zero | Spine Rip | F D F HP | up to 84 |
| Sonya | Kiss of Death | F F B B BL | any |
| Raiden | Electrocution | F B B B HP | 80-124 |
| Liu Kang | Cartwheel | D B U F D | any |
| Scorpion | Fire Breath | (BL) U U | 120-144 |

Every fighter also has The Pit: D+HP, 24-64.

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

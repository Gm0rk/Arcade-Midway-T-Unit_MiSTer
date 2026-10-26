# Changelog

What changed in the Arcade-Midway-T-Unit core, newest build first. Each build's changes are grouped by type: **Added**, **Changed**, **Fixed**, **Removed**, **Docs & tools**. Per-file detail for every build is in [COMMIT.md](COMMIT.md); test results on MiSTer hardware (not an original arcade PCB) are tracked in [docs/TestPlan.md](docs/TestPlan.md).

Build numbers count the core's development builds in order. Released RBF files are named by date.

## Build 34 (2026-10-25)

**Changed**
- Mortal Kombat II Plus (Beta 2, hack): the OSD no longer shows the Move List, the Finishing Moves page or the Hidden Items page for it. The hack changes the moves and the code those are built on, so the core offers none of them for it. The other eleven Mortal Kombat II versions, Mortal Kombat and the other games keep their OSD as it was.
- The MRA for the hack sends only the game id (with a flag that hides the three) and the table format: no patches, codes or fight variables. This is the one RTL change, in the top level (a flag read from the MRA's first table word, bit 8); it needs a new RBF.

**Docs & tools**
- `tools/hbmame_sets.py`: `hide_extras` marks a hack whose OSD hides the three; `tools/mra_gen.py` writes its game id word with the flag (`tools/tunit_secrets.py` `hidden_table`). Build 33's `NO_FINISHING_MOVES` in `tools/tunit_fmoves.py` is gone.
- `tools/mra_check.py` checks ROM index 1's first word (only the game id and the flag) and that a set with the flag has no table after the format word.
- README, the Mortal Kombat II page, ExtraContent.md and TestPlan.md (MK2-20 now covers the OSD; Mortal Kombat II has 20 tests) say the hack has none of the three.

## Build 33 (2026-10-24)

**Added**
- Mortal Kombat II Plus (Beta 2, hack), a rev L3.1 hack from HBMAME (set mk2p): a new MRA in `_alternatives/_Mortal Kombat II` (30 MRAs now) that loads a complete `mk2.zip` from `games/hbmame`. Its settings are kept apart from rev L3.1's.
- For this hack the core has no Hitboxes, Jade Fight or Finishing Moves (the OSD says "Not available in this revision"); the Move List shows rev L3.1's moves, and the other hidden items run rev L3.1's code.

**Docs & tools**
- `tools/hbmame_sets.py`: hacks that are not in MAME, each a clone of a MAME set with some files replaced. `tools/mra_gen.py --hbmame DIR` writes their MRAs, with the zip named "/hbmame/<zip>" (the path Main_MiSTer takes below `games/`); `tools/mra_check.py --hbmame DIR` checks them. `tools/tunit_fmoves.py` can mark every move of a set as missing.
- README (where the zip goes), the Mortal Kombat II page, ExtraContent.md and TestPlan.md (MK2-19 to MK2-21) cover the hack.

## Build 32 (2026-10-23)

**Docs & tools**
- README and `docs/TestPlan.md`: verification is on MiSTer hardware, not on an original T-Unit arcade PCB. The games table reads "Awaiting MiSTer hardware test".

## Build 31 (2026-10-19)

**Fixed**
- Loading a core: the background behind the "Sending ROM" box is now black. Build 30's fix did not reach it: the board sends no video while a ROM set loads, so the scaler kept the last frame it had (the MiSTer menu's coloured or patterned background). The core now sends its own black frames, with the board's timing, from the first byte of a download until the game starts.

## Build 30 (2026-10-19)

**Fixed**
- Loading a core: the screen behind the "Sending ROM" box is always black. It sometimes showed a solid colour or a scrambled pattern (the last game's palette and picture, or power-up noise).

**Docs & tools**
- TestPlan.md: C17 (the black loading screen).

## Build 29 (2026-10-19)

**Docs & tools**
- Title screen and gameplay screenshots in the README's games table (now in alphabetical order) and on each game page.
- `tools/extra_content.py` keeps a page's line endings when it writes the Extra content sections.

## Build 28 (2026-10-18)

**Docs & tools**
- `docs/ExtraContent.md`: everything the core adds, core-wide and per game, linked from the README.
- Each game page has an Extra content overview taken from it. `tools/extra_content.py` copies the sections, so the pages and the list stay in step; it is run whenever a feature is added or removed.

## Build 27 (2026-10-17)

**Docs & tools**
- This changelog, back to Build 1. Kept up to date with every build.

## Build 26 (2026-10-17)

**Changed**
- Mortal Kombat II sound: the DCS sound board (the ADSP-2105 and the DCS Audio 2K board) is now a port of MAME's instead of the Killer Instinct core's. Instruction timing, memory map, boot, DAC timing and timer follow MAME. In a simulated MK2 run the first sound comes at the same moment as MAME's and the waveform matches it (correlation 0.9998).

**Removed**
- The Killer Instinct DSP and sound memory code.

**Docs & tools**
- `sim/dcs_test`: the DSP runs in lockstep with MAME's own ADSP-21xx code (60 million instructions compared register by register), plus tools that compare the simulator's DSP trace with MAME's.
- Simulator: `--dcslog`, `--dcstrace` and `--dcsstate` for the new board.
- README credits and TestPlan.md: the DCS board is a MAME port; MK2-3 compares sound with MAME.

## Build 25 (2026-10-17)

**Fixed**
- Changing a DIP switch no longer restarts the game, so Service Credit and Tilt work.
- NBA Jam 2.00 with a power-up on no longer shows "ROM CHIPS BAD" or "RAM CHIPS BAD" at power-up: the ROM patches apply to instruction fetches only and the game-variable patches only while the CPU has interrupts on.
- The last 4 words of the main RAM clear were dropped.
- YM2151 notes no longer hang: the stop-all routine's key-offs left about 14 of 32 operators keyed on.
- Mortal Kombat II sound no longer keeps playing while paused.
- OSD Reset during a blit can no longer wedge the DDR3 port.
- Mortal Kombat Finishing Moves: the Pit is taken only when FINISH HIM ends within 12 frames, a miss is reported, and the walk counter starts over with each move.
- A window violation in the line-wrap cycle no longer cancels the display interrupt; the display column address follows MAME's.
- Blitter row buffer: a bank whose generation wrapped is cleared once, and the buffer is cleared during reset.

**Docs & tools**
- New VRAM test bench (`sim/vram_test`, reset during DDR3 operations). The finishing move check covers the Pit and a missed Pit.
- README: DIP switches reset after a change. TestPlan.md: C15 (DIP change), C16 (options and the RAM / ROM tests).

## Build 24 (2026-10-15)

**Removed**
- DIP switches a version does not use are no longer on the OSD (checked in MAME): Skip Post Test on all Mortal Kombat sets; Bill Validator, Powerup Test and Circuit Boards on the Mortal Kombat II sets that mark them unused; Players, Video Clips and Powerup Test on the NBA Jam 2.00, 1.00 and prototype sets. MRAs regenerated.

**Docs & tools**
- TestPlan.md: C10.

## Build 23 (2026-10-13)

**Added**
- Video Timing in Video Settings: Native 54.7Hz, 57Hz, 60Hz, ported from the Y and Wolf Unit cores.

**Docs & tools**
- README: Video Timing; CRT V-Size has less room at 57 and 60 Hz. TestPlan.md: C14.
- The CRT test bench checks the 57 and 60 Hz frames.

## Build 22 (2026-10-13)

**Added**
- Mortal Kombat (rev 5.0, rev 4.0, Turbo Ninja): Reptile Fight Next, Moon Silhouettes Always and Reptile Hints Always on the Hidden Items page, ported from the Y Unit core.

**Docs & tools**
- Mortal Kombat page: the three options and a Reptile section. TestPlan.md: MK17 to MK21.

## Build 21 (2026-10-12)

**Changed**
- Move List for Mortal Kombat is Off / List 1 / List 2 (Mortal Kombat II keeps Off / fighter).
- NBA Jam / TE "View Secret Players" is Off / Page 1 to n.

**Docs & tools**
- Game pages and TestPlan.md (MK15, NJ15, TE15) follow the new options.

## Build 20 (2026-10-11)

**Added**
- Service Credit and Tilt on the DIP Switches page.
- NBA Jam's tank game and Tournament Edition's tournament mode, entered from the OSD on Tonight's Match-Up.
- The cheat codes in the Secret Player List window, with Left / Right to turn the pages.
- Messages for a code the match-up did not take and for a code the revision does not have.

**Changed**
- OSD rearranged per game: Service Mode in the main menu, Secret Menus (Judge Dredd), Hidden Items (Mortal Kombat games), Cheat Codes & Hidden Items (NBA games), Reset and Reset and close OSD.
- Move List option is Off or the fighter. DIP switches in alphabetical order. All 29 MRAs regenerated.

**Removed**
- The Controls page.

**Docs & tools**
- Game pages: the new OSD items, the cheat code tables. TestPlan.md: C8 to C10, NJ18, TE18.

## Build 19 (2026-10-11)

**Changed**
- Mortal Kombat / Mortal Kombat II button order: High Punch, Low Punch, High Kick, Low Kick, Block, Start, Coin, Test, Pause. The default pad mapping stays on the same physical buttons; Block 2 is not mapped. MRAs regenerated.

## Build 18 (2026-10-11)

**Changed**
- Move List distances are words (Close, Sweep, Jump, Half screen, Full screen) instead of pixels.
- Mortal Kombat's fighters share Move List pages (four, then three).

## Build 17 (2026-10-11)

**Added**
- Mortal Kombat / Mortal Kombat II Move List window: the special moves, finishing moves and their distances, drawn over the game's dimmed, paused title screen.

**Changed**
- One window serves both the Move List and the Secret Player List.

**Docs & tools**
- `tools/tunit_window.py` writes the pages. TestPlan.md: MK15, MK2-16.

## Build 16 (2026-10-11)

**Added**
- NBA Jam / Tournament Edition Secret Player List window: a page of the game's secret players (name, initials, birthday, versions) drawn over the dimmed title screen, after the Wolf Unit core's Move List window.

**Removed**
- The OSD's Secret Player picker.

**Docs & tools**
- Game pages: the secret player tables with full names, initials, birthdays and versions, and how to enter them. TestPlan.md: NJ15, TE15.

## Build 15 (2026-10-10)

**Added**
- OSD Secrets for NBA Jam and Tournament Edition: secret players and the match-up power-ups.
- Messages when the OSD closes for each option that takes effect later, and "Not available in this revision" when the loaded set has no patch for it (Mortal Kombat II too).

**Docs & tools**
- Game pages: the new items and secret player tables. TestPlan.md: NJ15 to NJ17, TE15 to TE17.

## Build 14 (2026-10-09)

**Docs & tools**
- README: status note below the AI disclosure (under testing, bugs expected, issues and pull requests not accepted for now).

## Build 13 (2026-10-09)

**Docs & tools**
- `docs/TestPlan.md`: the test plan for MiSTer hardware (core-wide and per-game tests, Result column, progress table), linked from the README.

## Build 12 (2026-10-09)

**Added**
- OSD Move List page for Mortal Kombat (17 moves) and Mortal Kombat II (55 moves): the picked fighter's special moves.

**Docs & tools**
- Move List tables on the game pages.

## Build 11 (2026-10-09)

**Docs & tools**
- README split into a short overview plus one page per game in `docs/` (versions, controls, Secrets, Finishing Moves).

## Build 10 (2026-10-08)

**Docs & tools**
- README: AI disclosure below the title.

## Build 9 (2026-10-08)

**Fixed**
- Synthesis: Quartus error 10106 because the OSD string had passed 5000 bytes. The constant loop limit is now 10240.

## Build 8 (2026-10-08)

**Added**
- Finishing Moves for Mortal Kombat (7 fighters) and Mortal Kombat II (12) from the OSD: the picked fighter's move is entered on the round winner's controls at FINISH HIM, once the loser is dizzy and the distance is right.
- OSD messages: wrong stage, too far / too close, FINISH HIM over, not taken, a move the revision lacks, and the result of a Secrets code.

**Docs & tools**
- New test bench `sim/fmoves_test`. README: Finishing Moves with the move tables.

## Build 7 (2026-10-07)

**Fixed**
- NVRAM was saved again after every OSD option change. It is now saved once per OSD opening, if the game changed it.

## Build 6 (2026-10-07)

**Added**
- Mortal Kombat II Secrets: Jade Fight and Smoke Fight (L2.0 and later).

## Build 5 (2026-10-07)

**Added**
- Mortal Kombat II Secrets: Noob Saibot Fight (L3.0 and later).

## Build 4 (2026-10-07)

**Added**
- CRT V-Size (experimental): vertical size for analog CRTs, with PVM and Cabinet modes, under CRT Adjust. Core-side; `sys/` untouched.

**Docs & tools**
- README: table of contents, CRT V-Size section. New CRT test bench (`sim/crt_test`).

## Build 3 (2026-10-06)

**Fixed**
- Mortal Kombat II sound ran slow, broken up and off pitch: about a third of the DAC slots were lost, so the output ran dry.

## Build 2 (2026-10-06)

**Added**
- Secrets page in the OSD: the games' hidden menus, screens and debug features (EJB Menu, Security Screen, Hitboxes, Pong at Battle 250, Secret Menu, Secret Audits). All 29 MRAs carry their own secrets tables.

**Docs & tools**
- `tools/tunit_secrets.py` finds each set's codes and patches in its program ROM.

## Build 1 (2026-10-05)

**Added**
- First build of the T-Unit core, from Arcade-Midway-Y-Unit.
- T-Unit board: memory map, 512 KB main RAM in SDRAM behind a cache, 16 KB NVRAM, control register, the protection of every game.
- A new blitter, a 32 K-colour palette and video block, the ADPCM sound board and the DCS Audio 2K board.
- 5 games, 29 MRAs (5 parents, 24 alternatives) from MAME 0.289's midtunit.cpp.

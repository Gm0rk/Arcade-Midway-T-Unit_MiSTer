# Changelog

What changed in the Arcade-Midway-T-Unit core, newest build first. Each build's changes are grouped by type: **Added**, **Changed**, **Fixed**, **Removed**, **Docs & tools**. Per-file detail for every build is in [COMMIT.md](COMMIT.md).

Build numbers count the core's development builds in order. Released RBF files are named by date.

## Build 48 (2026-10-30)

**Fixed**
- Timing at 96 MHz (clk_sys): the Build 47 compilation did not meet it, worst setup slack -0.660 ns (total negative slack -28.327 ns, Fmax 90.29 MHz on that clock); every other clock met setup, and hold, recovery, removal and minimum pulse width met on all clocks. The 100 worst paths were all in two places, both found from the timing report, not guessed:
  - The framework's HQ2x scandoubler filter (`sys/hq2x.sv`, Scandoubler Fx = HQ2x): 81 of the 100, all from one register of its Blend stage to another (worst -0.660 ns, eight logic levels). Blend's registers change only while the scandoubler's `ce_x4i` is high, which at this core's 8 MHz pixel clock is every third clock, so the Blend-to-Blend paths now have two clocks in the SDC. The Y Unit core, whose pixel clock is also 8 MHz, has the same constraint.
  - The reset into the YM2151 (`jt51`): 19 of the 100 (worst -0.612 ns), from the ROM download test on `ioctl_index` and the boot hold counter, through the top level's `reset`, into jt51's envelope and phase generators. The sound board now gives jt51 its reset through a register, as the Y Unit core does; the register passes the reset on as long as it was, one clock later.

**Docs & tools**
- `tools/timing_paths.tcl` also ends with up to 600 worst paths of the core clock in summary form (the `sta_all_fail.tcl` step of MiSTer-CoreSkill). The 100 paths of the Build 47 report went to 29 registers and added up to -15.6 ns of the -28.3 ns total, so the other failing paths were not in the file; if the new list ends in positive slack, all of them are.
- Not compiled in Quartus here: whether Build 48 meets timing is not known until the next compilation's `.sta.summary`, `.paths.txt` and `.sta.rpt` are looked at, and a clean report is one placement (one seed). The registered reset was run in the full-board Verilator sim (Mortal Kombat, the same run before and after, sound written to a WAV file): the first 90 frames (1.62 s, 77,802 samples, 68,365 of them not zero, peak 9516) are identical sample for sample before and after. How much of that sound is the YM2151 and how much the OKI was not looked at. Not tested on MiSTer hardware.

## Build 47 (2026-10-30)

**Docs & tools**
- Every compilation now lists its worst timing paths by itself, as in the Y Unit core: after the build, `output_files/Arcade-Midway-T-Unit.paths.txt` is written (the 100 worst setup paths of every clock, then the 10 worst in full), the file that needed `quartus_sta -t tools/timing_paths.tcl` by hand. Quartus runs one post-flow script per project, so the project's now runs the new `post_flow.tcl`, which runs `release.tcl` (files the core in `releases/`, as before) and then `tools/timing_paths.tcl`. It takes a minute or two after the build and runs whether timing is met or not; a build that failed before the timing analysis leaves the last paths file alone. A problem is a warning in the Messages window, never a failed build.
- `tools/timing_paths.tcl` is the Y Unit core's: its file is `output_files/Arcade-Midway-T-Unit.paths.txt` (the earlier one wrote `output_files/timing_paths.txt` and took an optional number of paths).
- No change to the RTL or the MRAs: the core is as in Build 46.
- Tested under Tcl 8.6 with stand-ins for Quartus' commands and for `quartus_sta` (a fresh build, no timing analysis, a stale timing report, another revision, `quartus_sta` failing, `quartus_sta` failing after writing the file, the script missing); not run in Quartus itself.

## Build 46 (2026-10-29)

**Fixed**
- Infinite Health: switching it off no longer drops the bar a little (about 99%). The game works out the new energy from the full value the cheat shows it and stores the result, so its own copy was left at full less the last hit. While a health cheat is on, the core now also replaces what the game writes to that player's energy word with full, so the bar is still full when the cheat is switched off.

**Added**
- Infinite Round Time in the Cheats menu (Mortal Kombat II, all eleven versions): the round clock stops counting: it stays at 99 from the start of the round (or at the time it showed when you switched the cheat on), so a round never ends on time. The clock is two digits the game keeps in registers; the cheat replaces the one instruction that counts the ones digit down (`DEC A10`) with a move of A10 to itself, so switching it off lets the clock carry on from where it stopped. It is the second item from the top of the Cheats list, below the two Infinite Health lines.

**Changed**
- A cheat unit's flags have a new bit 1: the CPU's writes to the word store the cheat's value too (Infinite Health P1 and P2 use it). The board's patch bank decodes it from the CPU's own address on the clock the registered copy takes it, so it is ready with the write, and only while the CPU has interrupts enabled (as for reads).

**Docs & tools**
- `tools/tunit_cheats.py` finds the round clock's `DEC A10` in each version from the clock process (`MOVK 9,A11 / MOVK 9,A10 / MOVE A10,@ / MOVE A11,@`, the time-over test `MOVE A10,A0 / ADD A11,A0`, then `DEC A10 / JRNN / MOVK 9,A10 / DEC A11`); `tools/mra_check.py` checks it, the health units' new flag, and the four names. The eleven Mortal Kombat II MRAs are regenerated.
- `sim/cheats_test`: 39,468 checks (the new flag included); eleven deliberate changes to the module are each caught. `sim/sim_main.cpp` has `--ramwatch` (a main RAM word's CPU writes and the writes the board hands to the SDRAM model).
- README, ExtraContent.md and the Mortal Kombat II page describe the fourth cheat and the switch-off.
- Not compiled in Quartus and not run on a MiSTer. The write path was run in the full-board Verilator sim (`sim_tunit --game mk2 --nosound`, six test units with the store flag on main RAM words the game writes at start-up, a button press at frame 40 to get past the blank-CMOS screen, frames 42 to 51): all 41 CPU writes made with interrupts enabled reached the SDRAM model with the unit's value, and all 13 made with interrupts off reached it unchanged (no mismatch in 54). Not seen: the Quartus timing of the write compare, and the cache line update on its own (it takes the same `ram_wdata`).

## Build 45 (2026-10-28)

**Added**
- A Cheats menu on the OSD for Mortal Kombat II (all eleven sets except Plus, which has no menu entry): Infinite Health P1, Infinite Health P2 and Stop Finishing Move Timer. Open the OSD, choose Cheats, switch a cheat On or Off; no reset is needed (the timer cheat acts from the next FINISH HIM). Cheats are On/Off only, they are all Off when a game loads, and Mortal Kombat, NBA Jam, NBA Jam TE, Judge Dredd and Mortal Kombat II Plus do not show the menu.
- Infinite Health: the energy bar reads full (A1h) all the time, so the fighter never loses. The game keeps its own energy count, so switching the cheat Off hands back the energy the fighter would have had.
- Stop Finishing Move Timer: the FINISH HIM wait (80h frames, about 2.3 s after the first 28h) becomes 7FFFh frames, about 10 minutes. The wait still ends when a finishing move starts, or when the winner hits the loser, as in the game: hit the loser and FINISH HIM ends, as it does in the game.
- The cheats are written for each set from its own program ROM by `tools/tunit_cheats.py` and put in the MRA as a `<cheats size="8" max="8">` block (Main_MiSTer sends the switched-on cheats as a download with index 255).

**Changed**
- The board's read patches go from 8 entries to 16: entries 0-7 are the OSD secrets as before, 8-15 are the cheats. A main RAM entry applies only while the 34010 has interrupts on, so the diagnostics' RAM test (interrupts off) still reads what it wrote; a program ROM entry applies only to the instruction fetch.
- Downloads with index 255 (cheats) no longer hold the game in reset or blank the screen, as index 254 already did not.
- A ROM set loading clears the cheats.

**Docs & tools**
- New `rtl/tunit_cheats.sv` (in `files.qip`): takes up to 8 units of 8 bytes from the download and presents them as the 8 extra read patches.
- New `sim/cheats_test` (28,989 checks): the receiver with random units, short and cut-short downloads, a new download replacing the list, and a ROM load clearing it; seven deliberate changes to the module are each caught.
- `tools/mra_gen.py` writes the cheat block into the eleven Mortal Kombat II MRAs (regenerated); `tools/mra_check.py` checks them (names, unit sizes, the energy and timer addresses against the program ROM, and no cheats in the other games' MRAs).
- README (Features, Cheats row in the OSD table), ExtraContent.md and the Mortal Kombat II page (a Cheats section).
- Not compiled in Quartus and not run on a MiSTer. The cheats were tried in MAME with read taps standing in for the board's patches (both bars stay full, no KO; the longer FINISH HIM wait ends on the winner's hit) and the receiver and the patch compare in the Verilator sim; the main RAM patch with interrupts on was not simulated in the full board sim.

## Build 41 (2026-10-27)

**Fixed**
- The black screen while a ROM set loads follows the Video Timing option. The core's own loading frames were always the native 289-line frame (54.7 Hz), so with 57Hz selected the "Sending ROM" box sat on a 54.7 Hz picture and the refresh rate changed when the game started. With 57Hz the loading frames are the board's 277-line frame (57.1 Hz): after VSBLNK (line 274) comes line 287, as the 34010 does when it drops 12 blank lines. The picture lines, VSync and line timing are the same. Changing the option while a game loads takes effect within a frame.

**Docs & tools**
- New `rtl/tunit_idle.sv` (in `files.qip`): the loading frames, out of the top level, with a `vt57` input (`status[10]`, the board's `vtiming`).
- New `sim/idle_test` (339 checks): both timings (line and frame lengths, sync, blank and picture lines), the option switched at every 7th line of a frame in both directions, and 200 frames of random switching (a frame is 277 or 289 lines, never another length); five deliberate changes to the module are each caught.
- README and ExtraContent.md (Video Timing) mention it.

## Build 40 (2026-10-27)

**Added**
- Mortal Kombat II Plus (Beta 2, hack) has a Move List: Off or On on the OSD main menu, paged with Left and Right like the other Move Lists. 17 pages: the 12 fighters, then Jade, Noob Saibot, Smoke, Kintaro and Shao Kahn, each with its special moves, its finishing moves (fatalities, friendship, babality, Pit / Spikes, the Dead Pool) and the distance each needs. Moves the hack adds are marked +; they need Extra Moves On in the hack's settings. The moves are the MK2+ guide's (Ver. 2.8.50); the ROM in the MRA is MK2+ VER 1.48 (Beta 2), so a move the guide added later may be missing from it.
- View Secrets (Mortal Kombat II Plus): a second window, Off or On, five pages: how to unlock and select Jade, Noob Saibot and Smoke (and the Hornbuckle fight), how to unlock and play Kintaro and Shao Kahn, the 14 Kombat Kodes with the buttons of each player, and the ending bonuses, the Dead Pool and the settings of the hack's Service Mode that matter.
- With Move List and View Secrets both On, the one turned On last is shown (from its first page); turn it Off and the other comes back.

**Changed**
- The MRA flag that hid the Move List, Finishing Moves and Hidden Items for Mortal Kombat II Plus now hides Finishing Moves and Hidden Items only, and shows Plus's own Move List and View Secrets. Only the comment in the Plus MRA changed; its ROM data and checksums are the same.
- The window's ROMs are larger: 64 pages (was 32), 16384 text characters (was 8192); 44 pages are used, 1541 of 2047 segments and 11071 of 16384 characters. The page module `tunit_mlpage` handles two lists (the Move List or the Secret Player List, and View Secrets) of up to 31 pages each.
- New OSD bit: View Secrets is status bit 116. Move List for Mortal Kombat II Plus is a second `Move List` line (mask bit 15) on the same status bit 114 as the other games'.

**Docs & tools**
- README, the Mortal Kombat II page (a new Mortal Kombat II Plus section: the pages, the moves, the unlock steps, the Kombat Kodes, where the data comes from) and ExtraContent.md describe them.
- New `tools/tunit_plus.py`: the Plus fighters, secrets and Kombat Kodes as data; `--docs` prints the game page's tables. `tools/tunit_window.py` lays out the 22 new pages; `tools/tunit_fmoves.py` and `tools/tunit_secrets.py` make the two OSD lines.
- `sim/mlpage_test` also checks two lists (66 checks); `sim/window_test` checks all 44 pages.

## Build 39 (2026-10-27)

**Changed**
- View Secret Players (NBA Jam, NBA Jam Tournament Edition) is Off or On, like the Move List. On shows the window (the players, then the cheat codes); with the OSD closed, Left and Right (either controller) turn the pages, round the end of the list and back, one page a press; open the OSD and set it Off to play on. NBA Jam has two pages, Tournament Edition six. Each page says so under its title (Left / Right: page, OSD: View Secret Players Off). Before, the option picked the page in the OSD. A View Secret Players page saved by an older build is ignored (it comes up Off). This changes the top level and the window pages; it needs a new RBF.

**Docs & tools**
- README, the NBA Jam and NBA Jam Tournament Edition pages and ExtraContent.md describe the option.
- `sim/mlpage_test` also checks the six-page and two-page lists (45 checks); `tools/tunit_secrets.py` and `tools/tunit_window.py` make the OSD line and the pages.

## Build 38 (2026-10-27)

**Changed**
- Move List (Mortal Kombat, Mortal Kombat II) is Off or On. On shows the window; with the OSD closed, Left and Right (either controller) turn the pages, round the end of the list and back, one page a press; open the OSD and set it Off to play on. The game waits while the window is on, as before. Mortal Kombat has two pages, Mortal Kombat II one per fighter, Liu Kang first. Each page says so under its title (Left / Right: page, OSD: Move List Off to play), and Mortal Kombat II's top right shows the page, 1/12 to 12/12. Before, the option picked the list or fighter in the OSD. A Move List choice saved by an older build is ignored (it comes up Off). This changes the top level and the window pages; it needs a new RBF.

**Docs & tools**
- README, the Mortal Kombat and Mortal Kombat II pages and ExtraContent.md describe the option.
- New test bench `sim/mlpage_test` for the page turning (35 checks); `tools/tunit_fmoves.py` and `tools/tunit_window.py` make the OSD line and the pages.

## Build 37 (2026-10-27)

**Docs**
- README in the layout of the Y Unit core's README: Table of Contents (with a link to Extra content), Hardware, Games (new Main set column, screenshots with alt text), Testing setup, Features, OSD (a table of the OSD items), Controls, ROMs, Credits and references, License. CRT V-Size moved from its own section into Features. Nothing was added or removed in the core itself; no new RBF.

## Build 36 (2026-10-27)

**Removed**
- The 60 Hz Video Timing. Video Settings > Video Timing is now Native 54.7Hz or 57Hz: the 263-line frame (games about 10% faster) is gone from the OSD and from the board. The option is one OSD bit now, so a saved setting of 57Hz stays as it was and a saved 60Hz comes back as Native 54.7Hz. This changes the top level and the board; it needs a new RBF.

**Docs & tools**
- README and ExtraContent.md name the two timings; the CRT stage's comments say 57 Hz only.
- The simulator's `--vtiming` is 0 or 1; the CRT test bench (`sim/crt_test`) drops its 60 Hz cases and checks the 57 Hz frame at both V-Shift extremes instead.

## Build 35 (2026-10-26)

**Added**
- Fixed AI Difficulty for Mortal Kombat (rev 5.0, rev 4.0, Turbo Ninja) and Mortal Kombat II (all 12 versions, Mortal Kombat II Plus included): an OSD option on the main menu, below Finishing Moves. Off (the default), or 0 (easiest) to 9. The games keep the computer opponent's level in one RAM word, raise it after matches you win and lower it after matches you lose; with the option on, the CPU's reads of that word return the chosen level, so the computer plays at it through wins and losses in 1-player games. Off hands the game's own level back at once.
- The option is off while the test menu is selected (Service Mode, the Test button or the Test Switch DIP), and the word is only pinned while the CPU has interrupts enabled, so the diagnostics' RAM tests see the real RAM.

**Changed**
- The 15 Mortal Kombat and Mortal Kombat II MRAs carry the level word's address (ROM index 1, bytes 0x454-0x457), found in each set's own program ROM; the Mortal Kombat II Plus MRA has it after the game id and the hide flag. The NBA Jam, NBA Jam Tournament Edition and Judge Dredd MRAs are as in Build 34. This needs a new RBF (the top level and the board).

**Docs & tools**
- `tools/tunit_fmoves.py` finds the level word (the one routine that adjusts it: read, add, clamp to 0..9, write; exactly one in each ROM); `tools/mra_gen.py` writes it; `tools/mra_check.py` repeats the scan on its own and compares it with the MRA's, and a set with the hide flag now has the 4 bytes, zeros, and the level word.
- The simulator has `--level ADDR:N` (pin on) and `--lvlwatch ADDR` (log the CPU's reads and writes of the word).
- README, the Mortal Kombat and Mortal Kombat II pages and ExtraContent.md cover the option.

## Build 34 (2026-10-25)

**Changed**
- Mortal Kombat II Plus (Beta 2, hack): the OSD no longer shows the Move List, the Finishing Moves page or the Hidden Items page for it. The hack changes the moves and the code those are built on, so the core offers none of them for it. The other eleven Mortal Kombat II versions, Mortal Kombat and the other games keep their OSD as it was.
- The MRA for the hack sends only the game id (with a flag that hides the three) and the table format: no patches, codes or fight variables. This is the one RTL change, in the top level (a flag read from the MRA's first table word, bit 8); it needs a new RBF.

**Docs & tools**
- `tools/hbmame_sets.py`: `hide_extras` marks a hack whose OSD hides the three; `tools/mra_gen.py` writes its game id word with the flag (`tools/tunit_secrets.py` `hidden_table`). Build 33's `NO_FINISHING_MOVES` in `tools/tunit_fmoves.py` is gone.
- `tools/mra_check.py` checks ROM index 1's first word (only the game id and the flag) and that a set with the flag has no table after the format word.
- README, the Mortal Kombat II page and ExtraContent.md say the hack has none of the three.

## Build 33 (2026-10-24)

**Added**
- Mortal Kombat II Plus (Beta 2, hack), a rev L3.1 hack from HBMAME (set mk2p): a new MRA in `_alternatives/_Mortal Kombat II` (30 MRAs now) that loads a complete `mk2.zip` from `games/hbmame`. Its settings are kept apart from rev L3.1's.
- For this hack the core has no Hitboxes, Jade Fight or Finishing Moves (the OSD says "Not available in this revision"); the Move List shows rev L3.1's moves, and the other hidden items run rev L3.1's code.

**Docs & tools**
- `tools/hbmame_sets.py`: hacks that are not in MAME, each a clone of a MAME set with some files replaced. `tools/mra_gen.py --hbmame DIR` writes their MRAs, with the zip named "/hbmame/<zip>" (the path Main_MiSTer takes below `games/`); `tools/mra_check.py --hbmame DIR` checks them. `tools/tunit_fmoves.py` can mark every move of a set as missing.
- README (where the zip goes), the Mortal Kombat II page and ExtraContent.md cover the hack.

## Build 32 (2026-10-23)

**Docs & tools**
- README: verification is on MiSTer hardware, not on an original T-Unit arcade PCB. The games table reads "Awaiting MiSTer hardware test".

## Build 31 (2026-10-19)

**Fixed**
- Loading a core: the background behind the "Sending ROM" box is now black. Build 30's fix did not reach it: the board sends no video while a ROM set loads, so the scaler kept the last frame it had (the MiSTer menu's coloured or patterned background). The core now sends its own black frames, with the board's timing, from the first byte of a download until the game starts.

## Build 30 (2026-10-19)

**Fixed**
- Loading a core: the screen behind the "Sending ROM" box is always black. It sometimes showed a solid colour or a scrambled pattern (the last game's palette and picture, or power-up noise).

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
- README credits: the DCS board is a MAME port.

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
- README: DIP switches reset after a change.

## Build 24 (2026-10-15)

**Removed**
- DIP switches a version does not use are no longer on the OSD (checked in MAME): Skip Post Test on all Mortal Kombat sets; Bill Validator, Powerup Test and Circuit Boards on the Mortal Kombat II sets that mark them unused; Players, Video Clips and Powerup Test on the NBA Jam 2.00, 1.00 and prototype sets. MRAs regenerated.

## Build 23 (2026-10-13)

**Added**
- Video Timing in Video Settings: Native 54.7Hz, 57Hz, 60Hz, ported from the Y and Wolf Unit cores.

**Docs & tools**
- README: Video Timing; CRT V-Size has less room at 57 and 60 Hz.
- The CRT test bench checks the 57 and 60 Hz frames.

## Build 22 (2026-10-13)

**Added**
- Mortal Kombat (rev 5.0, rev 4.0, Turbo Ninja): Reptile Fight Next, Moon Silhouettes Always and Reptile Hints Always on the Hidden Items page, ported from the Y Unit core.

**Docs & tools**
- Mortal Kombat page: the three options and a Reptile section.

## Build 21 (2026-10-12)

**Changed**
- Move List for Mortal Kombat is Off / List 1 / List 2 (Mortal Kombat II keeps Off / fighter).
- NBA Jam / TE "View Secret Players" is Off / Page 1 to n.

**Docs & tools**
- Game pages follow the new options.

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
- Game pages: the new OSD items, the cheat code tables.

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
- `tools/tunit_window.py` writes the pages.

## Build 16 (2026-10-11)

**Added**
- NBA Jam / Tournament Edition Secret Player List window: a page of the game's secret players (name, initials, birthday, versions) drawn over the dimmed title screen, after the Wolf Unit core's Move List window.

**Removed**
- The OSD's Secret Player picker.

**Docs & tools**
- Game pages: the secret player tables with full names, initials, birthdays and versions, and how to enter them.

## Build 15 (2026-10-10)

**Added**
- OSD Secrets for NBA Jam and Tournament Edition: secret players and the match-up power-ups.
- Messages when the OSD closes for each option that takes effect later, and "Not available in this revision" when the loaded set has no patch for it (Mortal Kombat II too).

**Docs & tools**
- Game pages: the new items and secret player tables.

## Build 14 (2026-10-09)

**Docs & tools**
- README: status note below the AI disclosure (under testing, bugs expected, issues and pull requests not accepted for now).

## Build 13 (2026-10-09)

**Docs & tools**
- Documentation only; no change to the core.

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

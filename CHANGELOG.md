# Changelog

What changed in the Arcade-Midway-T-Unit core, newest build first. Each build's changes are grouped by type: **Added**, **Changed**, **Fixed**, **Removed**, **Docs & tools**.

Build numbers count the core's development builds in order. Released RBF files are named by date.

## Build 56 (2026-11-01)

**Added**
- Judge Dredd has a Cheats menu: 9 cheats from MAME's cheat file for jdreddp, Infinite Lives, Infinite Energy and Invincibility for each of the three players. Lives and energy are one byte of the player's word (lives 0Ah, energy C8h; player 1 at bit addresses 010E4B10 and 010E4B20, player 2 at 010E4E20 and 010E4E30, player 3 at 010E5130 and 010E5140). Invincibility is the word 0024h (player 1 at 010E4BB0, player 2 at 010E4EC0, player 3 at 010E51D0): MAME writes 24h to the low byte and 00h to the high byte, which is one word here. MAME's Invincibility 'ON' and 'OFF' pair is one cheat per player: the menu's switch does the turning off, and the game gets its own value back at once because nothing is written to its RAM. The addresses are for jdreddp, the only Judge Dredd set in MAME and in the core. Each cheat is one unit; at most 8 can be on at once, so one of the 9 is always left off.

**Changed**
- Every game has a Cheats menu now: Judge Dredd was the last without one. `Arcade-Midway-T-Unit.sv`: `menu_cheats = menu_mk | menu_mk2 | menu_nba | menu_jd` (menu mask bit 0). The cheat loader, the read patch and the board are not changed.
- The Judge Dredd MRA lists the 9 cheats (`<cheats size="8" max="8">`, timestamp 20261101); the other 29 MRAs are unchanged. `mra_check` no longer expects a set without cheats.

**Docs & tools**
- `tools/tunit_cheats_data.py` (the `jdreddp` picks), `tools/tunit_cheats.py` (`G_JDREDDP` builds units; the `jdreddp` set), `tools/mra_gen.py`, `tools/mra_check.py` (every MRA must carry `<cheats>`), `tools/cheat_docs.py` (`jd`).
- `docs/JudgeDredd.md` (new Cheats section), `docs/ExtraContent.md`, `README.md` (the Cheats rows say every game).
- `README.md`, Credits and references: the cheats' credits from the MAME cheat collection's cheat.txt (release 27 July 2025, for MAME 0.279), by set: Mortal Kombat (`mk`), Mortal Kombat II (`mk2`), NBA Jam (`nbajam`) and Tournament Edition (`nbajamte`, `nbajamte1`, `nbajamte2a`, `nbajamte3`); `jdreddp`, `nbajamr2`, `nbajamte2`, `nbajamte3a` and `nbajamte4` are not in its list, which the README says.
- Checked: Verilator lint of `emu` (no error); `mra_check` on all 30 MRAs; `tools/extra_content.py --check`. Checked in the program ROM (`jdreddp_rom0.bin`): the three invincibility words 010E4BB0, 010E4EC0 and 010E51D0 are 32-bit immediates in the same routines, three times each, 310h bits apart; the neighbouring fields 010E4B30, 010E4E40 and 010E5150 are addressed the same way, which fits lives (4B10) and energy (4B20) sitting in the same per-player blocks at the same spacing (4E20 / 4E30, 5130 / 5140); only the invincibility words were found as immediates. Not seen working in the board simulation: two runs of set jdreddp (3.7 s a frame) stopped at frame 300 in the attract intro (the CMOS-error screen holds the game until a button at frame 220), before any game started.
- Result of the Build 56 compilation (Quartus 17.0.2 Lite, seed 1; `.fit.summary`, `.fit.rpt`, `.sta.summary`, `.sta.rpt`, `.paths.txt`): **timing met on every clock**. Setup: clk_sys +0.132 ns (TNS 0, Fmax 97.24 MHz; Build 55 +0.453 ns, 100.37 MHz), pll_hdmi +0.585, h2f_user0_clk +3.899, spi_sck +5.933, FPGA_CLK1_50 +7.879, FPGA_CLK2_50 +12.279, pll_audio +15.337; hold +0.198 at the smallest (pll_hdmi), recovery +2.235, removal +0.950, minimum pulse width +1.041, all with TNS 0. Fit: 32,431 / 41,910 ALMs (77 %; Build 55 33,118, 79 %), 33,288 registers, 405 / 553 M10K blocks (73 %), 3,141,163 / 5,662,720 block memory bits (55 %), 67 / 112 DSP blocks (60 %), 145 / 314 pins, 3 / 6 PLLs; the change is one OR in the menu mask, so the 687-ALM drop is not from it. The ten worst clk_sys setup paths all run from `hps_io|ioctl_index` (bits 9, 10, 11, 12 and 15) to the CPU register file's DSP input registers (`cpu|rf[23][18]`, `rf[23][17]`, `rf[22][3]`, `rf[22][0]`): worst 9.957 ns of data delay, 7 logic levels, clock skew -0.197 ns: the compare of `ioctl_index` (`Equal1~0`, `Equal1~2`), `rom_download~0`, `reset` (fanout 275), `cpu|rfb_dat~6` and `rfb_dat~49` (fanout 32 each), `rf[23][18]~SCLR_LUT`, then the DSP input (`gfx|Mult4~405`); 6.6 ns of the 9.957 are wire, 5.5 ns of them after `reset`. This is the `ioctl_index` -> `rf` path of the Build 54 report (+0.436 there); this build does not touch it. The margin is thin: a register on `rom_download` (or `reset`) would take the compare and the 275-fanout net out of the path; not done.
- Not run: a MiSTer (the Build 54 cheats and these 9 are untried on hardware).

## Build 55 (2026-11-01)

**Changed**
- Timing: the SDRAM controller's choice of request and its address pins are written flat, with the same behaviour on every clock. The Build 54 compilation (Quartus 17.0.2 Lite, seed 1) **missed timing**: clk_sys setup -0.346 ns (TNS -0.639; Build 53 +0.036), on three endpoints only: `SDRAM_A[9]` -0.346 (from `board|cpu_sd_req`; also from `rd_delay[1]` -0.301, `rd_delay[6]` -0.183, `rd_delay[2]` -0.164, `ch1_ack` -0.108), `SDRAM_A[12]` -0.217 and `SDRAM_A[12]~_Duplicate_1` -0.076. The path is 8 logic levels (`always0~2`, `SDRAM_A[0]~4`, `state~26` to `~29`, `SDRAM_A[0]~5`, `Selector3~4`: the else-if chain of the request priority, the refresh test and the read-in-flight test) and then 3.459 ns of wire to the address pin's register in the I/O cell, which sits far from the logic. The next worst clk_sys path is +0.313 ns (`crt_vsize`); the other clocks met timing (pll_hdmi +0.537, h2f_user0_clk +4.039, spi_sck +5.070, FPGA_CLK1_50 +7.787, FPGA_CLK2_50 +13.015, pll_audio +14.885; hold +0.182 at the smallest). The fit grew from 32,648 to 33,112 ALMs (79 %) with the cheat engine, which moved the cells around a path that was already thin (Build 53's worst clk_sys path was this one, at +0.036).
- `rtl/sdram.sv`: "a read of channel k is in flight" (`rd_busy`), "a refresh is due" (`ref_due`) and the power-up steps (`st_pc`, `st_ar`, `st_lm`, `st_zero`) are registers, computed a clock ahead from the next values of `rd_delay`, `rd_ch` and `refresh_count`. The request that wins in IDLE is a one-hot (`g0`, `g1`, `gw`, `g2`, `g3`: ch0, ch1, write, ch2, ch3, the same priority) and what it loads is one AND-OR (`ld`: DQM and auto-precharge bits, bank, row, column). `SDRAM_A`, `SDRAM_BA` and `command` are each assigned once, from `ld`, the held column or the power-up values. No port, parameter, state or timing of the SDRAM interface changed.

**Docs & tools**
- Checked: a random comparison of the Build 54 controller and this one (Verilator, both under the same inputs, every output compared on every clock: `SDRAM_A`, `SDRAM_BA`, the command pins, the data pins and their enable, `ch0` to `ch3` acknowledges and data, `wr_ack`): 8 runs of 20,000,000 clocks (four request densities, two seeds, about 400 re-initialisations of the controller), 0 differences; nine deliberately changed copies of the new controller (a power-up step one clock early, the refresh test, the read-in-flight test, the byte-mask bits, a command bit, the enables of `SDRAM_A` and `SDRAM_BA`) are each caught. Verilator lint of `emu`: no new message. Full-board simulation (set `mk2`): frame 10 cycles 15901453 instructions 430306, frame 20 33449533 / 799922, frame 30 50997613 / 1169540, the same as Build 54.
- Estimated, not measured: yosys with 6-input LUTs puts every register of the controller at 5 levels or fewer (Quartus built 8 from the old form); Quartus's own count is in the next report.
- Result of the Build 55 compilation (Quartus 17.0.2 Lite, seed 1; `.fit.summary`, `.fit.rpt`, `.sta.summary`, `.sta.rpt`, `.paths.txt`): **timing met on every clock**. Setup: clk_sys +0.453 ns (TNS 0, Fmax 100.37 MHz; Build 54 -0.346, Build 53 +0.036), pll_hdmi +0.555, h2f_user0_clk +4.314, spi_sck +3.315, FPGA_CLK1_50 +8.904, FPGA_CLK2_50 +13.236, pll_audio +14.919. Hold +0.179 at the smallest (pll_hdmi; clk_sys +0.247), recovery +1.681, removal +0.813, minimum pulse width +1.041. The 600 clk_sys paths listed run from +0.453 to +1.036: `crt_vsize` `t_bl_g` -> `t_h1_g` +0.453, `wl` -> ring RAM +0.532, `ascal` line RAM -> `i_pix` +0.611, `t_h1_b` -> `t_out` +0.664, `boot_hold` -> `s2_sx` +0.753 and -> `rf` +0.774, `gfx|mem_baddr` -> `wp_q` +0.880. The SDRAM controller's worst listed path is now `rd_busy[2]` -> `SDRAM_A[12]` at +0.986 ns (Build 54: -0.346). 33,118 / 41,910 ALMs (79 %), 33,241 registers, 405 / 553 M10K (73 %), 67 / 112 DSP (60 %). The margin is +0.453 and a clean report is one placement: if a later build misses by a little, try another seed or look at `crt_vsize` first. README "Timing and resources" has these figures.
- Build 55 is the first build that meets timing with the Build 54 Cheats menu; the new cheats, the masks and the one-shots have not been tried on a MiSTer. Hardware observations of Build 55 count; Build 54's are discarded.

## Build 54 (2026-11-01)

**Added**
- The OSD's Cheats menu has the 124 cheats picked in the cheat-picker spreadsheet: Mortal Kombat rev 5.0 24 (rev 4.0 and the Turbo Ninja hack 1, Always have Reptile Clues), Mortal Kombat II rev L3.1 44 (the other versions 7 to 11, Plus 4), NBA Jam rev 3.01 26 (rev 2.00 20, rev 1.00 5, the prototypes 4) and NBA Jam Tournament Edition 20 to 30 a version. They come from MAME's cheat files (the addresses in a file are for its own set only, so they are on that revision) and from the finders for every set (the items that moved, below).
- Cheat entries cover part of a word: a byte (00FF / FF00) or single bits (a player's flag), and entries on the same word combine (their covered bits are ORed). Before, an entry replaced the whole word. The unit's fourth word is the mask.
- One-shot cheats: a unit with bit 14 of its second word set writes the whole word once, when it first appears in the list sent by the menu; another cheat switched on or off sends the list again and does not repeat it. Switching the cheat off and on does (P1 / P2 Drain All Energy Now! in Mortal Kombat and Mortal Kombat II: 4 cheats).
- Mortal Kombat: P1 Infinite Energy and P2 Infinite Energy, made like Mortal Kombat II's Infinite Health (energy word 00A1, store entry).

**Changed**
- The OSD items that did what a cheat does are cheats now, one per player where the game allows it: Mortal Kombat Reptile Hints Always (Always have Reptile Clues); Mortal Kombat II Hitboxes (Show Hitboxes), Jade Fight (Jade Fight no Low Kick), Noob Saibot Fight (Winner Battles Noob Saibot), Pong at Battle 250 (Always Play Pong) and Smoke Fight (Press Start To Fight Smoke); NBA Jam Big Heads, Power-Up Defense, Power-Up Interceptions, Shot Percentage, No CPU Assistance (Computer Assistance Turned, 3.01) and Tank Game (Play Hidden 3D Tank Game); NBA Jam Tournament Edition Baby Size Players, Head Size, Max Power, Power-Up Goaltending, Quick Hands, Shot Percentage and Tournament Mode. They keep the revision limits and the patches the items had (found in each version's program); 36 of the picks were these items and 7 more were close to one, and they use the items' patches, not MAME's bytes.
- At most 8 cheat units can be on at once (the menu refuses more); the picks take from 1 to 7 units each (the game pages list them).

**Removed**
- Those 19 OSD items, and the NBA Jam and TE injections of the Tank Game and Tournament Mode codes (`matchup_code`). The NBA Jam page of Cheat Codes & Hidden Items keeps Open Secret Menu (Attract); Tournament Edition's keeps that and No CPU Assistance.

**Docs & tools**
- `rtl/tunit_cheats.sv`: unit format v2 (second word bit 14, fourth word mask); outputs `ck_mask`, `ck_pk`, `ck_fire`; the one-shots of the list that is replaced are kept (`o_addr`, `o_val`, `o_pk`) and a new one fires only when it is not among them.
- `rtl/midway_tunit.sv`: inputs `pt_mask[255:0]`, `pt_pk[7:0]`, `pt_fire[7:0]`; the read patch is `(mem_rdata & pt_k) | pt_q`; the poke path takes `pt_fire` (a whole word, once). `Arcade-Midway-T-Unit.sv`: `menu_cheats` (menu mask bit 0) for every game but Judge Dredd; the removed lines of CONF_STR; `rtl/tunit_secrets_osd.svh` regenerated.
- `tools/tunit_cheats.py`, `tools/tunit_cheats_data.py`, `tools/cheat_import/`, `tools/cheat_docs.py`, `tools/tunit_secrets.py` (`MOVED`, smaller `build` and `osd_lines`), `tools/mra_gen.py`, `tools/mra_check.py`: the picks, the units, the tables of the game pages from the MRAs. The 30 MRAs are regenerated (20261101; Judge Dredd unchanged); `mra_check` passes on all 30.
- `docs/ExtraContent.md`, the game pages and the README: the Cheats sections and tables, the moved items out of the Hidden Items / Cheat Codes & Hidden Items tables.
- `sim/cheats_test/tb_cheats.cpp`: new testbench (103,390 checks).
- Checked: Verilator lint of `emu` (no error); the loader's testbench; `mra_check` on all 30 MRAs. Checked in the full-board simulation (set `mk2`, the download driven by `--cheat`): P1 and P2 Drain all Energy Now! sent together at frame 40: both pokes reach the SDRAM model in frame 41 (0001 each); the list sent again with a third cheat added (frame 50): no poke; the third cheat alone (60): none; P1 with the third (70): P1 pokes again (71); an empty list (80): none; P2 alone (90): P2 pokes (91); P1 and P2 together (100): P1 pokes (101), P2, unchanged but in another slot, does not; a store entry (110) pokes A1 once (111). Masks, on the word 010FFEB0 that the game reads in a loop (reads 7DA0, 7DF0, 7E40 without a cheat): an entry of mask 000F and value 5 gives 7DA5, 7DF5, 7E45; mask 00F0 and value 90 gives 7D90; both entries together 7D95; an empty list gives the game's own values again; mask 00FF and value AA gave 7DAA. An entry on the high byte alone (mask FF00, value 5500) gave 55F0 once, and then the game did not read the word again (it looks like a pointer; not examined further).
- Compiled by the user: timing missed, clk_sys -0.346 ns (see Build 55); use Build 55.

## Build 53 (2026-10-31)

**Changed**
- Fixed AI Difficulty no longer pins the level of the demo fights that play between games (Mortal Kombat, Mortal Kombat II, Mortal Kombat II Plus; all 15 sets). The game starts them with a store of 5 to the level word, and they now run at that 5, as in the original and in the Legacy Kollection, so the attract mode looks the same with the option on. The pin is back with the next write of the word by anything else (the game-start store of a new game, the game's adjusting, a RAM clear, a reset). How it works: the MRA carries one more value after the level word (ROM index 1, bytes 0x458-0x45B, a 28-bit word address: the CPU's program counter just after the demo store `MOVK 5,A0 / MOVE A0,@level,0`, found per set by `tools/tunit_fmoves.py` and checked by `tools/mra_check.py`); the board (`rtl/midway_tunit.sv`) sets a flag when the level word's last write completed with the CPU at that address and clears it on any other write of the word or on a CPU reset; while the flag is set the read pin returns the game's own value. Demo store addresses: MK rev 5.0 FFCB3E30 (the pair of stores: game start FFCB54F0, demo FFCB3E30 in the same frame); MK2 rev L3.1 FF827BA0 (game start FF828DF0).

**Docs & tools**
- `docs/ExtraContent.md`, `docs/MortalKombat.md`, `docs/MortalKombatII.md`: the Fixed AI Difficulty row and section say the demo fights keep the game's own level.
- `tools/tunit_fmoves.py`: `demo_pc()` finds the store (the words `18A0 0580 lo hi` are unique in each set), `level_part()` writes 8 bytes (level word, demo PC); `tools/mra_gen.py` (comments); `tools/mra_check.py` scans for the store on its own and checks the 28-bit value (a wrong value in a mutated MRA is reported).
- `sim/sim_main.cpp`, `sim/sim_top.sv`: `--lvldemo PC`; the `lvl` log shows the demo flag changes.
- MRAs: the 15 Mortal Kombat and Mortal Kombat II MRAs have the 4 bytes and a new timestamp (20261031); the NBA Jam and Judge Dredd MRAs are unchanged. `mra_check` passes on all 30 (md5, MAME region dumps, level words and demo stores).
- Checked: Verilator lint of `emu`: no errors, identical to Build 50 apart from line numbers. Full-board simulation (set `mk`): a write of the level word with the CPU at the configured address sets the flag (`lvl 1 W 0000 pc FFC97850`, `lvl 1 demo flag 1`). A real demo fight is not reachable in the simulation (about 3 s a frame); the demo store's address and its place in the game's start-up come from MAME (write taps: MK `W 0 pc FFCB54F0` then `W 5 pc FFCB3E30` in one frame, MK2 `W 0 pc FF828DF0` then `W 5 pc FF827BA0`) and from the CPU's registered PC in the RTL.
- Measured in MAME (nothing in the core changes for it): how fast an idle player loses to the final boss with the level pinned at 0 and at 9. Kintaro (MK2): 621 frames at 0, 618 at 9. Goro (MK, rev 4.0): 637 frames at 0, 648 at 5 and 648 at 9 (the same fight, started at the same frame; the pin was held at 0 up to the boss in the last two). An ordinary opponent changes with the level (MK2: 338 frames at 0, 493 at 9; MK: 523 and 578). So the level hardly moves Goro's or Kintaro's attacks (under 2 % and not in step with the level): Fixed AI Difficulty does not make the bosses easier or harder, and the original game does not either. The docs do not claim it.
- The Build 53 compilation (the user's Quartus 17.0.2 Lite, seed 1) **meets timing on every clock**: setup slack clk_sys +0.036 ns (Fmax 96.34 MHz), pll_hdmi +0.164, h2f_user0_clk +4.215, spi_sck +5.136, FPGA_CLK1_50 +8.278, FPGA_CLK2_50 +12.390, pll_audio +14.857; hold +0.195 at the smallest (pll_hdmi; clk_sys +0.246), recovery +0.801, removal +0.971, minimum pulse width +1.041; total negative slack 0.000 everywhere, the analyser's last line is "0 errors, 0 warnings". The worst clk_sys paths (709 listed, down to +0.670 ns) are `sdram:sdram|rd_delay[5]` to `SDRAM_A[12]` (+0.036 ns, 10.907 ns of data delay, skew +0.657; Sorgelig's controller, code this build does not touch; +0.546 in Build 52, +0.155 in Build 51), `rd_delay[2]` to the same (+0.150), `tms34010_gfx|busy` to `wp_q[*]` (+0.197) and `boot_hold[*]` to `tms34010_muldiv|acc[*]` / `williams_adpcm:sound|ym_rst` (+0.209). No `lvl_` register is among them. A clean report is one placement, so a later build may land differently; the SDRAM address output is the thinnest path (a different seed, or a look at `sdram.sv`, if a later compilation misses by a little there). Resources: 32,648 / 41,910 ALMs (78 %), 32,971 registers, 405 / 553 M10K (73 %), 67 / 112 DSP (60 %), 145 / 314 pins (46 %), 3 / 6 PLLs. README "Timing and resources" updated to these figures.
- The hardware observations of Build 53 count: it meets timing.

## Build 52 (2026-10-31)

**Fixed**
- Timing at 96 MHz (clk_sys): the Build 51 compilation misses it by 0.012 ns (total negative slack -0.012 ns, Fmax 95.9 MHz; Build 50 met it at +0.148). Every other clock, hold, recovery, removal and minimum pulse width check met. The one failing path is the new cheat-poke logic: `pk_pend[1]` to `pk_rdy` (11 logic levels, 10.169 ns of data delay, `pk_sel` with a fan-out of 166); 37 of the 100 worst paths of the clock are of that kind (+0.018 to +0.4 ns). The pick of the entry to poke indexed the 16 patch entries with a variable (`28 * (8 + pk_sel)`), which the compiler built as two adders and a multiplexer in front of `pk_rdy`. The pick is now two registered steps with constant indexes only: step 1 takes the lowest pending entry as a one-hot register (`pk_oh`), step 2, one clock later, ORs its address and value together from the entries (`pk_wa`, `pk_wd`) and checks that it is still on and a main RAM word before setting `pk_rdy`. The poke happens one or two clocks later than in Build 51; an entry switched off again within about three clocks of going on is dropped (no poke), as an entry that is off should be (a toggle in the OSD takes the Main program far longer than that). Nothing else changes.

**Docs & tools**
- `sim/sim_main.cpp`: environment variable `CK_GAP` (clocks to wait between two `--cheat` sends, default 0).
- Checked: Verilator lint of `emu`: no error, identical to Build 50 apart from line numbers. Full-board simulation again (set `mk2`): three store entries on 0105D090, 0105B950 and 0105B960 switched on at frame 50: the three pokes reach the SDRAM model in frame 51 (A500, A501, A502) with no CPU write behind them; one entry on 0105D090 switched on and off again 200 clocks later (`CK_GAP=200`): the poke (A500) reaches the SDRAM model and the game's first read after is A500, not 8. With no gap between the two sends the poke is dropped, as said above.
- The Build 51 compilation (the user's Quartus 17.0.2 Lite, seed 1): setup slack clk_sys -0.012 ns, pll_hdmi +0.078, h2f_user0_clk +3.051, spi_sck +4.098, the 50 MHz clocks +6.791 and +7.910, pll_audio +14.968; hold +0.236 at the smallest, recovery +1.614, removal +0.933, minimum pulse width +1.041. Resources: 32,998 / 41,910 ALMs (79 %), 32,906 registers, 405 / 553 M10K (73 %), 67 / 112 DSP (60 %), 145 / 314 pins (46 %), 3 / 6 PLLs. Its other worst paths have little margin and are in code this build does not change: `cfg_dcs` to `sdram:sdram|SDRAM_A[11]` (+0.001 ns, 10.965 ns of data delay, skew +0.680), `game_id[*]` to `williams_adpcm:sound|ym_din[*]` (+0.136), `sdram:sdram|rd_delay[*]` to `SDRAM_A[*]` (+0.155). If a later compilation misses by a little on one of those, the SDRAM controller's address path is the place to look.
- The Build 52 compilation (the user's Quartus 17.0.2 Lite, seed 1) **meets timing on every clock**: setup slack clk_sys +0.301 ns (Fmax 98.86 MHz), pll_hdmi +0.439, h2f_user0_clk +4.056, spi_sck +5.939, FPGA_CLK1_50 +9.096, FPGA_CLK2_50 +11.835, pll_audio +15.076; hold +0.240 at the smallest, recovery +1.644, removal +1.062, minimum pulse width +1.041; total negative slack 0.000 everywhere, the analyser's last line is "0 errors, 0 warnings". None of the 710 clk_sys paths in the worst-paths report is a `pk_` path any more (Build 51: 37 of the worst 100). The worst clk_sys paths are now `hps_io|ioctl_index[*]` to `tms34010:cpu|rf[*][*]` (+0.301 ns; the download-index compare into `rom_download`, the board's reset and the register file's synchronous clear, unchanged logic), `crt_vsize|t_h1_r[*]` to `t_out[*]` (+0.379) and `sdram:sdram|rd_delay[*]` to `SDRAM_A[*]` (+0.546); `cfg_dcs` to `SDRAM_A[11]` (+0.001 in Build 51) is no longer among them. A clean report is one placement, so a later build may land differently. Resources: 32,788 / 41,910 ALMs (78 %), 32,907 registers, 405 / 553 M10K (73 %), 67 / 112 DSP (60 %), 145 / 314 pins (46 %), 3 / 6 PLLs. README "Timing and resources" updated to these figures.
- The hardware observations of Build 52 count: it meets timing. Build 51's do not, as it missed.

## Build 51 (2026-10-31)

**Fixed**
- Infinite Health: switching it off no longer drops the bar to what the fighter had when the cheat went on (reported for player 1: the bar went to about 90%). Since Build 46 every write the game makes to the energy word stores full energy while the cheat is on, but a fighter who is not hit makes no write, so the game's own copy stayed at the lower value it had when the cheat was switched on and the bar went back to it when the cheat went off. Player 2 (the computer, hit all the time) refreshed its copy at every hit, which is why it showed only for player 1. Now an Infinite Health entry that goes on also writes its value (full energy) to the word once: into the board's write queue, as a CPU write goes, and the cached line of the word is dropped so the next read comes from the SDRAM (new bus state `S_POKE` in `rtl/midway_tunit.sv`, waiting for a clock with no CPU request in front of the state machine). A toggle of any cheat sends the whole list again, so an entry that stays on is written again, with the value the game already reads.

**Docs & tools**
- `docs/ExtraContent.md`, `docs/MortalKombatII.md`, `tools/tunit_cheats.py`, `rtl/tunit_cheats.sv`: the Infinite Health description says the game's own copy is set to full when the cheat is switched on. The cheat units and the MRAs are unchanged.
- `sim/sim_main.cpp`: environment variables `LOG_FROM` and `LOG_MAX` for `--lvlwatch` and `--ramwatch` (start frame and line limit; the 400-line limit was reached in frame 44 on a word the game reads 400 times a frame).
- Checked in MAME (Plus ROM, run as set `mk2`, the energy words patched as the board does: reads of both words return A1h and writes store A1h while the cheat is on; the cheat switched off every 260 frames for 40, the raw words read at each switch-off): with the read and write patches alone (Builds 46 to 50) player 1's copy was 00A1 at the first 12 switch-offs and 0075 (73%) at the 13th to the 20th: the computer hit player 1 four times while the cheat was off, player 1 was not hit again while it was on, and the copy stayed at 0075; player 2's was 00A1 every time. With the energy words also set to A1h each time the cheat goes on, as the board now does: 00A1 for both players at all 20. On the original game (L3.1, the same scenario) the read and write patches alone gave 00A1 for both at 9 of 9 switch-offs, because player 1 was hit while the cheat was on.
- Checked in the full-board simulation (Verilator, `sim/`, set `mk2`; the RTL of this build): three entries with the store flag on the main RAM words 0105D090, 0105B950 and 0105B960 (words the game writes during start-up), switched on at frame 50: three writes reached the SDRAM model at once (A500, A501, A502), with no CPU write behind them, in entry order. One entry on 0105D090 (a counter the game reads and increments every frame, 7 then 8 up to frame 50) switched on and straight off again in the same frame: the write reached the SDRAM model (A500) and the game's first read after was A500, not 8 (the value it had written in frame 50), then A501, A502 and so on, so the cached line (it held the counter) was dropped and fetched again. Earlier in this work, with the Build 50 board: a store write of A501 to 0105B950 at frame 61 was what the game read at frame 62 after the cheat had gone off (the update of the cached line by a patched write works).
- Not run: a fight in the full-board simulation (about 4 s a frame, a fight is 1800 or more frames away), a MiSTer, Quartus. Two simulations that poked hot variables with odd values (01068E70, 0105D480: the game reads them 400 times a frame) derailed the game after the first read of the odd value; they say nothing about the new logic and are not counted above.
- Timing: not compiled here. Build 51 adds a term to the write queue's push and data (`wq_push`, `wq_in`) and a state to the bus state machine; the Build 50 compilation met timing at +0.148 ns on clk_sys (worst path `sdram:sdram|rd_delay[*]` to `SDRAM_A[12]`), so the next compilation's `.sta.summary`, `.paths.txt` and `.sta.rpt` are needed, and a clean report is one placement.

## Build 50 (2026-10-30)

**Added**
- Mortal Kombat II Plus has the Cheats menu, with the same four cheats as the other Mortal Kombat II versions: Infinite Health P1, Infinite Health P2, Infinite Round Time and Stop Finishing Move Timer. The hack keeps the health words and the FINISH HIM routine where the other versions have them, but it replaced two pieces of code with jumps to routines of its own, and the cheats follow them there: the round clock is counted down in a routine of the hack, and the FINISH HIM wait is set in one (80h frames, 140h when an option of the hack lengthens it), so Stop Finishing Move Timer holds both open and has two units in the MRA (five of the eight the core takes are used with all four on).

**Changed**
- The OSD's Cheats line is shown for every Mortal Kombat II version, Plus included: the menu mask bit it follows is now bit 0 (`menu_mk2`, `h0C,Cheats;`), not bit 5 (`osd_mk2`, which is off for Plus). The Hidden Items and Finishing Moves pages stay hidden for Plus.
- The Plus MRA carries the `<cheats>` block (its timestamp is 20261030). The 11 other Mortal Kombat II MRAs are unchanged: their cheat units and notes are the same bytes as before.

**Docs & tools**
- `tools/tunit_cheats.py` finds the round state and the two energy words with patterns of their own (the FINISH HIM routine's start, and the energy bars' set-up), instead of going through the finishing-move tool whose patterns Plus does not match; for the 11 versions it finds the same addresses. `tools/mra_gen.py` writes the cheats for a version with its own extras, and `tools/mra_check.py` expects them there.
- Checked in MAME with the Plus ROM (the workspace's T-Unit MAME, Plus run as set `mk2`), with the cheats' words patched as the board would: the round clock stays at 99 where the unpatched game counts it down (92, 74, 56, 38, 20 at 600-frame steps), FINISH HIM stays on past 3,000 frames where the game ends it at 168, the longer window (forced on: 360 frames) ends at 360 with only the first unit and stays open with both, a hit by the winner still ends the wait, and with the energy words read as full an idle player 1 is not knocked out in 7,000 frames, where the computer wipes it out at frame 4,358 without that. The board's own patch path (RTL) is the one already used by the other versions and was not run with the Plus ROM; the full-board simulation takes seconds per frame, so it cannot reach a fight.
- Timing: the Build 49 compilation met it on every clock (worst setup slack +0.416 ns on clk_sys, total negative slack 0). Build 50 changes only the top level's menu mask bit and the Cheats line, so it is a new compilation to read: not compiled in Quartus here, and a clean report is one placement (one seed). Not tested on MiSTer hardware.

## Build 49 (2026-10-30)

**Fixed**
- Timing at 96 MHz (clk_sys): the Build 48 compilation is close but still does not meet it: worst setup slack -0.193 ns (total negative slack -0.340 ns; Build 47 had -0.660 and -28.327), Fmax 94.26 MHz on that clock. Every other clock met setup, and hold, recovery, removal and minimum pulse width met on all clocks. Both Build 48 changes worked: no HQ2x or YM2151 path fails any more. This time the list of 600 paths ends at +0.472 ns, so the eight paths below zero are all there are, and all eight are in CRT V-Size's Cabinet mode:
  - `crt_vsize` squares the two source pixels it blends (`t_sqa_*`, `t_sqb_*`) straight from the ring RAM's read: the RAM's output, its output mux in LUTs and the multiplier, into the next DSP's input register (worst -0.193 ns, 9.2 ns of data delay; the RAM's clock reaches it 1.26 ns later than the DSP's). A register now sits behind the RAM's read (`ring_q2`), the squares are taken from it one phase later, and the mix and the two square-root steps follow one phase later each; the output is read at the pixel enable as before. In the CRT bench all 22 cases (PVM, Cabinet, V-Shift, 57 Hz) write the same output before and after, clock by clock (every red, green, blue and flag value), and a deliberately wrong phase is caught. The module now needs 9 clocks per pixel instead of 8; this core has 12.
  - 170 of the 600 listed paths (the best at +0.157 ns) were from `boot_hold` through the black gating of the picture into the same ring RAM, so there is little margin there. The top level's `load_black` now comes from a register, one clock after its terms (the 26-bit compare of `boot_hold` is no longer in front of every pixel).

**Docs & tools**
- Not compiled in Quartus here: whether Build 49 meets timing is not known until the next compilation's `.sta.summary`, `.paths.txt` and `.sta.rpt` are looked at, and a clean report is one placement (one seed). `crt_vsize` is run in the CRT bench only: the full-board Verilator sim does not contain the CRT stage or the top level's `load_black`. Not tested on MiSTer hardware.

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

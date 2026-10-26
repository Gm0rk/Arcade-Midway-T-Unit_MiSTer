# Test plan

[Back to the core's README](../README.md)

Hardware tests for the core, run on MiSTer hardware (not on an original
T-Unit arcade PCB). Run them with the newest core release and mark
each row **Pass** or **Fail** in the Result column (blank: not tested yet).
A game counts as verified when every row of its section and every core-wide
row passes on the MiSTer; the core is done when all six sections pass. Rows
marked *(optional)* need equipment not everyone has (a 15 kHz CRT, four
controllers) and do not hold a game back.

For a clean start, delete the game's NVRAM file before the first boot test:
it is in `config/nvram` on the SD card, named after the MRA.

## Progress

| Section | Tests | Passed | Done |
|---|---|---|---|
| [Core-wide](#core-wide) | 17 | 0 | No |
| [Mortal Kombat](#mortal-kombat) | 21 | 0 | No |
| [Mortal Kombat II](#mortal-kombat-ii) | 20 | 0 | No |
| [NBA Jam](#nba-jam) | 18 | 0 | No |
| [NBA Jam Tournament Edition](#nba-jam-tournament-edition) | 18 | 0 | No |
| [Judge Dredd](#judge-dredd) | 13 | 0 | No |

## Core-wide

Test these once, with any game (C11 with one ADPCM game and Mortal Kombat
II).

| # | Test | Pass when | Result |
|---|---|---|---|
| C1 | Load the core through each game's main MRA | Every game starts; the OSD opens and closes | |
| C2 | HDMI picture, Aspect Ratio Original and Full Screen | Stable 4:3 picture (Original), screen filled (Full Screen); no rolling, tearing or flicker | |
| C3 | Scale: Normal, V-Integer, both HV-Integer settings | Each changes the picture size as named, no garbage | |
| C4 | Scandoubler Fx: HQ2x and the CRT scanline settings | The effect shows on the output | |
| C5 | Analog 15 kHz output *(optional)* | Picture centred and stable on a CRT; CRT Adjust H-Size, H-Position and V-Shift change it; Auto-Width fits the width | |
| C6 | CRT V-Size, PVM and Cabinet modes *(optional)* | Each step makes the picture taller (+) or shorter (-); V-Shift recentres it; no rolling | |
| C7 | Pause button, and "Pause when OSD is open" On and Off | The game freezes and resumes with sound (the sound stops while paused, Mortal Kombat II too); with the option Off it keeps running behind the OSD | |
| C8 | OSD Reset, then Reset and close OSD; also a few times in the middle of a fight or a game | Both restart the game from its start-up screens every time (never a black or frozen screen); the first leaves the OSD open, the second closes it | |
| C9 | Service Mode (OSD main menu) On, then Off | The game's diagnostics open, and the game returns when Off | |
| C10 | DIP Switches page: Service Credit, then Tilt (select each line, close the OSD) | The switches are in alphabetical order with Service Credit and Tilt among them, and none that the game's own DIP switch screen calls unused; each select adds one credit / the game registers the tilt (message or tilt count in its audits); loading the game again adds neither | |
| C11 | Leave the attract mode running 30 minutes | No lockup or graphics corruption; sound stays at the right speed and in step with the picture, and no note keeps droning when the music stops between scenes | |
| C12 | Controller mapping and a second controller | Every button maps in the OSD's button definition; a second controller plays P2 | |
| C13 | OSD messages | A message appears about 2 seconds, only once the OSD is closed (for example after setting a finishing move) | |
| C14 | Video Timing (Video Settings): Native 54.7Hz, 57Hz, 60Hz, on HDMI and, if you have one, a 15 kHz CRT | The picture stays whole and stable at each, also when switched while a game runs; at 57 / 60 Hz the game runs a little faster while music and voices keep their pitch; on a CRT at 60 Hz, CRT V-Shift moves the picture without parts of it wrapping to the other edge | |
| C15 | Change a game DIP switch on the OSD's DIP Switches page while the game runs | The game keeps running (no restart); the new setting shows after a reset | |
| C16 | Turn on every Hidden Items / power-up option of a game, then run its RAM and ROM tests (NBA Jam rev 2.00 does them at every power-up; the others: diagnostics, CPU Board Test, or the Powerup Test DIP switch) | Every RAM and ROM chip passes (green); the options still work in a game afterwards | |
| C17 | Load a game through its MRA while another game is running, then load the core again from the menu; do it a few times | The screen behind the "Sending ROM" box is black every time (no solid colour, no scrambled picture), on HDMI and, if you have one, a 15 kHz CRT; the game then starts normally | |

## Mortal Kombat

Main MRA: Mortal Kombat (rev 5.0 T-Unit 03-19-93). See also the
[game page](MortalKombat.md).

| # | Test | Pass when | Result |
|---|---|---|---|
| MK1 | First boot with no NVRAM file | Start-up checks run; after the factory-settings prompt (press a button) the attract mode starts | |
| MK2 | Attract mode, one full loop | Logos, story and fighter screens, demo fight and high scores look right: colours, no missing or flickering parts | |
| MK3 | Attract sound | Music and speech at the right speed and pitch, no crackle | |
| MK4 | Diagnostics (Test button): ROM/RAM, switch and sound tests | ROM and RAM pass; every control of both players shows in the switch test (Block 2 is not mapped); the sound test plays | |
| MK5 | Diagnostics: monitor patterns | Crosshatch and colour bars square, straight and in the right colours | |
| MK6 | Coin, 1-player start, fighter select | Credits count; select screen and portraits right | |
| MK7 | Play several fights | Define joystick buttons asks for High Punch, Low Punch, High Kick, Low Kick, Block, Start, Coin, Test, Pause; every button does its move for P1; stages, fighters and energy bars right; no lockup | |
| MK8 | "Test Your Might" bonus round | Appears after a few fights; breaking the block works and scores | |
| MK9 | 2-player fight, P2 joins mid-game | P2's controls all work; the fight runs to the winner | |
| MK10 | Game over, continue and initials entry | Continue countdown, game over and initials entry work | |
| MK11 | NVRAM: enter initials or change a game adjustment, open the OSD, reload the core | The change is still there | |
| MK12 | A DIP switch (OSD), then reset | The game's DIP switch screen (diagnostics) or its behaviour shows the change | |
| MK13 | Hidden Items: EJB Menu and EJB Menu (Copyright Screen) | Each opens its menu (the copyright screen first for the second); the OSD message says the code was entered | |
| MK14 | Finishing Moves: set Sub-Zero's Spine Rip (or any fatality) and win a fight | The move plays at FINISH HIM; at the wrong distance a message says to step closer or back | |
| MK15 | Move List (OSD main menu): List 1, List 2, then Off | List 1 shows Cage to Sonya, List 2 Raiden to Scorpion: each fighter's special moves and fatality with its distance in words (Close, Sweep, ...) over the dimmed MK title, all readable; the game waits and goes on when Off; two moves work as shown, a fatality at its distance | |
| MK16 | Other versions: rev 4.0 and Turbo Ninja | Each boots to the attract mode and starts a game | |
| MK17 | Hidden Items: Reptile Fight Next, then win a match in a 1-player game | Message "Reptile fight set: win a match in a 1-player game"; after the win "You have found me", then the fight with Reptile below The Pit | |
| MK18 | Hidden Items: Reptile Fight Next twice | Message "Reptile fight cleared"; the next win goes on as usual | |
| MK19 | Hidden Items: Moon Silhouettes Always On, play to The Pit | The message names it when the OSD closes; silhouettes cross the moon in every round there | |
| MK20 | Hidden Items: Reptile Hints Always On, start a match | The message names it when the OSD closes; Reptile drops in with a hint before each round's "Fight!"; the EJB Menu's game audits are not cleared | |
| MK21 | MK17 and MK20 on rev 4.0 and Turbo Ninja | The same as on rev 5.0 | |

## Mortal Kombat II

Main MRA: Mortal Kombat II (rev L3.1). See also the
[game page](MortalKombatII.md).

| # | Test | Pass when | Result |
|---|---|---|---|
| MK2-1 | First boot with no NVRAM file | Start-up checks run; after the factory-settings prompt the attract mode starts | |
| MK2-2 | Attract mode, one full loop | Logos, story, bios and demo fights look right | |
| MK2-3 | Attract and fight music, speech and effects (DCS) | Music at the right speed and pitch (compare with a recording of the arcade game or MAME), speech and hit sounds clean, no breaks, crackle or clicks between tunes | |
| MK2-4 | Diagnostics (Test button): ROM/RAM, switch and sound tests | ROM and RAM pass; every control shows (Block 2 is not mapped); the sound test plays every channel | |
| MK2-5 | Diagnostics: monitor patterns | Crosshatch and colour bars right | |
| MK2-6 | Coin, 1-player start, fighter select and the tower | Select screen, portraits and battle tower right | |
| MK2-7 | Play several fights on different stages | Define joystick buttons asks for High Punch, Low Punch, High Kick, Low Kick, Block, Start, Coin, Test, Pause; every button works; backgrounds (The Pit II, Dead Pool, Kombat Tomb, Portal and others) right; no lockup | |
| MK2-8 | 2-player fight | P2's controls all work; the battle counter goes up | |
| MK2-9 | Game over, continue and initials entry | Continue countdown, game over and initials entry work | |
| MK2-10 | NVRAM: enter initials or change a game adjustment, open the OSD, reload the core | The change is still there | |
| MK2-11 | A DIP switch (OSD), then reset | The game's DIP switch screen or its behaviour shows the change | |
| MK2-12 | Hidden Items: EJB Menu | The menu opens (attract mode); the OSD message says the code was entered | |
| MK2-13 | Hidden Items: Security Screen, Hitboxes, Pong at Battle 250 | Each does what the game page says; the OSD message names it when the OSD closes | |
| MK2-14 | Hidden Items: Noob Saibot, Jade and Smoke fights | Each fight comes up as the game page says | |
| MK2-15 | Finishing Moves: a fatality, a friendship or babality, a Pit / Spikes and the Dead Pool | Each plays at FINISH HIM on its stage; a wrong stage or distance gives its message | |
| MK2-16 | Move List (OSD main menu): a few fighters (including Shang Tsung), then Off | The window shows the fighter's special and finishing moves with the distance in words (Close, Sweep, Jump, ...) over the dimmed MK II title, all readable; the game waits and goes on when Off; a few moves work as shown, a fatality at its distance | |
| MK2-17 | Other versions: L3.2 and L3.1 European, L3.0, L2.1, L2.0, L1.4, L1.1 | Each boots to the attract mode and starts a game | |
| MK2-18 | Hacks: L4.2, L9.1, Challenger | Each boots to the attract mode and starts a game | |
| MK2-19 | Mortal Kombat II Plus (Beta 2, hack): put its complete `mk2.zip` in `games/hbmame` (MAME's `mk2.zip` stays in `games/mame`) and load its MRA from `_alternatives` | It boots to the attract mode and starts a game; play a few fights, including new fighters or moves if you know them: graphics and sound right (DCS music and speech clean), no lockup; its settings are kept apart from rev L3.1's (change one in Plus, load rev L3.1: unchanged) | |
| MK2-20 | Mortal Kombat II Plus: open the OSD, then load rev L3.1 and open it again | On Plus the main menu has no Move List, Finishing Moves or Hidden Items, and Video Settings, DIP Switches, Service Mode, Pause when OSD is open and Reset work; on rev L3.1 all three are there | |

## NBA Jam

Main MRA: NBA Jam (rev 3.01 4-07-93). See also the [game page](NBAJam.md).

| # | Test | Pass when | Result |
|---|---|---|---|
| NJ1 | First boot with no NVRAM file | The screen blanks during the start-up checks, then the attract mode starts (factory-settings prompt if asked) | |
| NJ2 | Attract mode, one full loop | Logo zoom, court zoom, team and player pictures, demo game look right | |
| NJ3 | Attract sound | Music, speech and crowd at the right speed and pitch | |
| NJ4 | Diagnostics (Test button): ROM/RAM, switch and sound tests | ROM and RAM pass; every control of all four players shows; the sound test plays | |
| NJ5 | Diagnostics: monitor patterns | Crosshatch and colour bars right | |
| NJ6 | Coin, start, team select | Team select pictures and stats right | |
| NJ7 | Play a full game | Turbo, Shoot / Block and Pass / Steal work; dunks, "on fire" and the scaled players right; quarters, halftime and the end of game run through | |
| NJ8 | 2 players on one side or against each other | Both players' controls work | |
| NJ9 | 4 players *(optional)* | Players 3 and 4 join and play | |
| NJ10 | Initials entry and records | Initials entry works; records and the initials are kept after an OSD open and core reload | |
| NJ11 | A DIP switch (OSD), then reset | The game's DIP switch screen or its behaviour shows the change | |
| NJ12 | Cheat Codes & Hidden Items: Open Secret Menu (Attract) | The design team screen, then the secret Midway menu (Jam Info); the OSD message says the code was entered | |
| NJ13 | Other versions: rev 2.00, rev 1.00, proto 2.00, proto 1.01 | Each boots to the attract mode and starts a game | |
| NJ14 | Secret Menu on rev 2.00 or 1.00 | The hidden audit pages show | |
| NJ15 | View Secret Players: Page 1, Page 2, then Off; start a game, answer YES and enter Mark Turmell's code from the list (MJT, Mar 22) | Page 1 lists the 13 players, page 2 the cheat codes, over the dimmed NBA Jam title, all readable; the game waits while it shows and Off brings it back; the team select shows TURMELL as your player | |
| NJ16 | Cheat Codes & Hidden Items: Big Heads, then start a game | The message says "from the next game"; every player has a big head | |
| NJ17 | Cheat Codes & Hidden Items: Power-Up Defense, Power-Up Interceptions, Shot Percentage, No CPU Assistance | The message says "On for all players"; the shot percentage shows when a player shoots | |
| NJ18 | Start a game; on Tonight's Match-Up open the OSD and pick Tank Game | The tank game ("YOU ARE DEAD!") is played instead of the tip-off; the message says the code was taken. Picked outside the match-up, the message says to pick it there | |

## NBA Jam Tournament Edition

Main MRA: NBA Jam Tournament Edition (rev 4.0 3-23-94). See also the
[game page](NBAJamTE.md).

| # | Test | Pass when | Result |
|---|---|---|---|
| TE1 | First boot with no NVRAM file | Start-up checks run, then the attract mode starts (factory-settings prompt if asked) | |
| TE2 | Attract mode, one full loop | Logo, court, team and player pictures, demo game look right | |
| TE3 | Attract sound | Music, speech and crowd at the right speed and pitch | |
| TE4 | Diagnostics (Test button): ROM/RAM, switch and sound tests | ROM and RAM pass; every control of all four players shows; the sound test plays | |
| TE5 | Diagnostics: monitor patterns | Crosshatch and colour bars right | |
| TE6 | Coin, start, team and player select | Selection screens right | |
| TE7 | Play a full game | All buttons work; players, court and scoreboard right; quarters, halftime and the end of game run through | |
| TE8 | 2 players | Both players' controls work | |
| TE9 | 4 players *(optional)* | Players 3 and 4 join and play | |
| TE10 | Initials entry and records | Kept after an OSD open and core reload | |
| TE11 | A DIP switch (OSD), then reset | The game's DIP switch screen or its behaviour shows the change | |
| TE12 | Cheat Codes & Hidden Items: Open Secret Menu (Attract) | The design team screen, then the secret Midway menu (Jam Info) | |
| TE13 | Other versions: rev 4.0 (3-03-94), 3.0 (both), 2.1, 2.0, 1.00, proto 2.00 | Each boots to the attract mode and starts a game | |
| TE14 | Nani Edition | Boots to the attract mode and starts a game | |
| TE15 | View Secret Players: Page 1 to Page 6, then Off; start a game, answer YES and enter a code from the list (rev 2.1: Sub-Zero, SUB, Nov 5) | Pages 1-4 list the players, 5-6 the cheat codes, over the dimmed TE title, all readable; the game waits while it shows; the team select shows the player | |
| TE16 | Cheat Codes & Hidden Items: Head Size Big, then Huge, then Baby Size Players, each followed by a new game | Big heads, huge heads, small players | |
| TE17 | Cheat Codes & Hidden Items: Max Power, Quick Hands, Power-Up Goaltending, Shot Percentage, No CPU Assistance | The message says "On for all players"; the shot percentage shows when a player shoots | |
| TE18 | Start a game; on Tonight's Match-Up open the OSD and pick Tournament Mode | "TOURNAMENT MODE" shows at the tip-off; the message says the code was taken | |

## Judge Dredd

MRA: Judge Dredd (rev TA1 7-12-92, location test). See also the
[game page](JudgeDredd.md). This is an unfinished location-test version;
compare anything odd with MAME before marking it Fail.

| # | Test | Pass when | Result |
|---|---|---|---|
| JD1 | First boot with no NVRAM file | Start-up checks run, then the attract mode starts (factory-settings prompt if asked) | |
| JD2 | Attract mode, one full loop | Title, story screens and demo look right | |
| JD3 | Attract sound | Music and effects at the right speed and pitch | |
| JD4 | Diagnostics (Test button): ROM/RAM, switch and sound tests | ROM and RAM pass; every control of all three players shows; the sound test plays | |
| JD5 | Diagnostics: monitor patterns | Crosshatch and colour bars right | |
| JD6 | Coin, start, play the first stage | Kick, Jump, Punch and Crouch work; scrolling and enemies right; no lockup | |
| JD7 | Play on to a later stage | The next stage loads and plays | |
| JD8 | 2 players | Both players' controls work | |
| JD9 | 3 players *(optional)* | Player 3 joins and plays | |
| JD10 | NVRAM: high score or a game adjustment, open the OSD, reload the core | The change is still there | |
| JD11 | A DIP switch (OSD), then reset | The game's DIP switch screen or its behaviour shows the change | |
| JD12 | Secret Menus: Secret Audit Menu | Six audit pages; any button turns the page | |
| JD13 | Secret Menus: Secret Audit Menu + Credits | The audits, then the staff credits | |

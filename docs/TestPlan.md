# Test plan

[Back to the core's README](../README.md)

Hardware tests for the core. Run them with the newest core release and mark
each row **Pass** or **Fail** in the Result column (blank: not tested yet).
A game counts as verified when every row of its section and every core-wide
row passes; the core is done when all six sections pass. Rows marked
*(optional)* need equipment not everyone has (a 15 kHz CRT, four
controllers) and do not hold a game back.

For a clean start, delete the game's NVRAM file before the first boot test:
it is in `config/nvram` on the SD card, named after the MRA.

## Progress

| Section | Tests | Passed | Done |
|---|---|---|---|
| [Core-wide](#core-wide) | 13 | 0 | No |
| [Mortal Kombat](#mortal-kombat) | 16 | 0 | No |
| [Mortal Kombat II](#mortal-kombat-ii) | 18 | 0 | No |
| [NBA Jam](#nba-jam) | 14 | 0 | No |
| [NBA Jam Tournament Edition](#nba-jam-tournament-edition) | 14 | 0 | No |
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
| C7 | Pause button, and "Pause when OSD is open" On and Off | The game freezes and resumes with sound; with the option Off it keeps running behind the OSD | |
| C8 | OSD Reset | The game restarts from its start-up screens | |
| C9 | Service Mode switch (Controls page) On, then Off | The game's diagnostics open, and the game returns when Off | |
| C10 | Service Credit and Tilt (Controls page) | A credit is added; the game registers the tilt (message or tilt count in its audits) | |
| C11 | Leave the attract mode running 30 minutes | No lockup or graphics corruption; sound stays at the right speed and in step with the picture | |
| C12 | Controller mapping and a second controller | Every button maps in the OSD's button definition; a second controller plays P2 | |
| C13 | OSD messages | A message appears about 2 seconds, only once the OSD is closed (for example after setting a finishing move) | |

## Mortal Kombat

Main MRA: Mortal Kombat (rev 5.0 T-Unit 03-19-93). See also the
[game page](MortalKombat.md).

| # | Test | Pass when | Result |
|---|---|---|---|
| MK1 | First boot with no NVRAM file | Start-up checks run; after the factory-settings prompt (press a button) the attract mode starts | |
| MK2 | Attract mode, one full loop | Logos, story and fighter screens, demo fight and high scores look right: colours, no missing or flickering parts | |
| MK3 | Attract sound | Music and speech at the right speed and pitch, no crackle | |
| MK4 | Diagnostics (Test button): ROM/RAM, switch and sound tests | ROM and RAM pass; every control of both players shows in the switch test; the sound test plays | |
| MK5 | Diagnostics: monitor patterns | Crosshatch and colour bars square, straight and in the right colours | |
| MK6 | Coin, 1-player start, fighter select | Credits count; select screen and portraits right | |
| MK7 | Play several fights | Every button does its move for P1; stages, fighters and energy bars right; no lockup | |
| MK8 | "Test Your Might" bonus round | Appears after a few fights; breaking the block works and scores | |
| MK9 | 2-player fight, P2 joins mid-game | P2's controls all work; the fight runs to the winner | |
| MK10 | Game over, continue and initials entry | Continue countdown, game over and initials entry work | |
| MK11 | NVRAM: enter initials or change a game adjustment, open the OSD, reload the core | The change is still there | |
| MK12 | A DIP switch (OSD), then reset | The game's DIP switch screen (diagnostics) or its behaviour shows the change | |
| MK13 | Secrets: EJB Menu and EJB Menu (Copyright Screen) | Each opens its menu (the copyright screen first for the second); the OSD message says the code was entered | |
| MK14 | Finishing Moves: set Sub-Zero's Spine Rip (or any fatality) and win a fight | The move plays at FINISH HIM; at the wrong distance a message says to step closer or back | |
| MK15 | Move List: switch the Fighter | The page lists the picked fighter's special moves; two of them work as shown | |
| MK16 | Other versions: rev 4.0 and Turbo Ninja | Each boots to the attract mode and starts a game | |

## Mortal Kombat II

Main MRA: Mortal Kombat II (rev L3.1). See also the
[game page](MortalKombatII.md).

| # | Test | Pass when | Result |
|---|---|---|---|
| MK2-1 | First boot with no NVRAM file | Start-up checks run; after the factory-settings prompt the attract mode starts | |
| MK2-2 | Attract mode, one full loop | Logos, story, bios and demo fights look right | |
| MK2-3 | Attract and fight music (DCS) | Music at the right speed and pitch (compare with a recording of the arcade game), no breaks or crackle | |
| MK2-4 | Diagnostics (Test button): ROM/RAM, switch and sound tests | ROM and RAM pass; every control shows; the sound test plays every channel | |
| MK2-5 | Diagnostics: monitor patterns | Crosshatch and colour bars right | |
| MK2-6 | Coin, 1-player start, fighter select and the tower | Select screen, portraits and battle tower right | |
| MK2-7 | Play several fights on different stages | Every button works; backgrounds (The Pit II, Dead Pool, Kombat Tomb, Portal and others) right; no lockup | |
| MK2-8 | 2-player fight | P2's controls all work; the battle counter goes up | |
| MK2-9 | Game over, continue and initials entry | Continue countdown, game over and initials entry work | |
| MK2-10 | NVRAM: enter initials or change a game adjustment, open the OSD, reload the core | The change is still there | |
| MK2-11 | A DIP switch (OSD), then reset | The game's DIP switch screen or its behaviour shows the change | |
| MK2-12 | Secrets: EJB Menu | The menu opens (attract mode); the OSD message says the code was entered | |
| MK2-13 | Secrets: Security Screen, Hitboxes, Pong at Battle 250 | Each does what the game page says; the OSD message names it when the OSD closes | |
| MK2-14 | Secrets: Noob Saibot, Jade and Smoke fights | Each fight comes up as the game page says | |
| MK2-15 | Finishing Moves: a fatality, a friendship or babality, a Pit / Spikes and the Dead Pool | Each plays at FINISH HIM on its stage; a wrong stage or distance gives its message | |
| MK2-16 | Move List: switch the Fighter, including Shang Tsung | The page lists the picked fighter's special moves; a few of them work as shown | |
| MK2-17 | Other versions: L3.2 and L3.1 European, L3.0, L2.1, L2.0, L1.4, L1.1 | Each boots to the attract mode and starts a game | |
| MK2-18 | Hacks: L4.2, L9.1, Challenger | Each boots to the attract mode and starts a game | |

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
| NJ12 | Secrets: Secret Menu | The design team screen, then the secret Midway menu (Jam Info); the OSD message says the code was entered | |
| NJ13 | Other versions: rev 2.00, rev 1.00, proto 2.00, proto 1.01 | Each boots to the attract mode and starts a game | |
| NJ14 | Secret Menu on rev 2.00 or 1.00 | The hidden audit pages show | |

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
| TE12 | Secrets: Secret Menu | The design team screen, then the secret Midway menu (Jam Info) | |
| TE13 | Other versions: rev 4.0 (3-03-94), 3.0 (both), 2.1, 2.0, 1.00, proto 2.00 | Each boots to the attract mode and starts a game | |
| TE14 | Nani Edition | Boots to the attract mode and starts a game | |

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
| JD12 | Secrets: Secret Audits | Six audit pages; any button turns the page | |
| JD13 | Secrets: Secret Audits + Credits | The audits, then the staff credits | |

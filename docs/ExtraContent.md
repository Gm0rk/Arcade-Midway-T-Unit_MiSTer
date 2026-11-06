# Extra content

[Back to the core's README](../README.md)

<!-- The game sections below are copied into each game's page (docs/<Game>.md) by tools/extra_content.py. Edit them here, then run it. -->

Beyond the arcade board itself, the core adds 12 core-wide features and a set of hidden menus, cheats and information windows for each of the five games. Core-wide features come first, then each game.

## Core-wide

| Feature | What it adds |
| --- | --- |
| OSD layout | The same page order for every game: Video Settings, the game's own items, DIP Switches, a Secrets page, Service Mode, Pause when OSD is Open, Reset, Reset and close OSD |
| DIP Switches page | MAME's switches as OSD options in alphabetical order, with MAME's defaults. Switches a version does not use are left out. The games read most of them at power-up, so reset after a change |
| Service Credit and Tilt | Two extra lines on the DIP Switches page: selecting one adds a credit or slams the tilt switch |
| Service Mode | Opens the game's test mode from the OSD's main menu |
| Pause | Pause from a button or the OSD, and "Pause when OSD is Open" |
| Video Timing | Native 54.7 Hz or 57 Hz frames for TVs that do not hold 54.7 Hz. Only blank lines are dropped, so the whole picture is still sent. Games run about 4% faster at 57 Hz; sound keeps its pitch and tempo. The black screen while a game loads uses the same frame |
| CRT V-Size (experimental) | Makes the picture taller or shorter in 3-line steps (up to 21 lines) under CRT Adjust, in PVM mode (retimed frame) or Cabinet mode (timing unchanged, light spread over the fixed lines) |
| NVRAM | CMOS settings, audits and high scores are kept across power-off and written to the SD card once when the OSD is opened, if the game changed them, or with Save Settings |
| Secrets pages | The hidden menus, screens and debug features the programmers left in each game, as OSD items. The core enters the control codes for you |
| Information windows | Pages drawn over the game's dimmed title screen while the game waits: the Move List (Mortal Kombat games), the Secret Player List (NBA Jam games) and View Secrets (Mortal Kombat II Plus). Set one On in the OSD, close the OSD and turn the pages with Left and Right; open the OSD to set it Off |
| OSD messages | When the OSD closes, a message says whether a code was taken, what a set finishing move is waiting for, what an option just turned on does, or that the loaded version does not have it |
| MRAs | 33 MRAs for the five games (5 parents, 28 alternatives), each carrying its own table of patches and code positions and its Cheats list, built for MAME 0.289. Four are for hacks that are not in MAME, whose zips go in `games/hbmame`: Mortal Kombat II Plus, whose OSD has its own Move List and View Secrets, Fixed AI Difficulty and the Cheats, but no Finishing Moves or Hidden Items, and NBA Jam Tournament Edition Special Edition 5.02 and NBA Jam Rewind (with and without Get that Bleep outta here), which have the Tournament Edition's extras |

## Mortal Kombat

Eight extras on rev 5.0, rev 4.0 and the Turbo Ninja hack: two hidden menus, two Reptile options, Finishing Moves, a Move List window, Fixed AI Difficulty, and a Cheats menu (24 cheats on rev 5.0, one on the others).

| Feature | What it adds | OSD page |
| --- | --- | --- |
| EJB Menu | The programmers' menu: diagnostics, coin bookkeeping, game audits, a hidden Hello page, initials entry and every character's ending | Hidden Items |
| EJB Menu (Copyright Screen) | The same menu, reached through the hidden "This is Mortal Kombat" copyright screen | Hidden Items |
| Reptile Fight Next | Reptile fights after the next match you win in a 1-player game. Select again to cancel; used up when his fight starts | Hidden Items |
| Moon Silhouettes Always | Every match on The Pit has the silhouettes crossing the moon, and with them the chance to win flawless, never Block, finish with a fatality, and meet Reptile | Hidden Items |
| Finishing Moves | Pick a fighter's fatality or The Pit (7 fighters). At the next FINISH HIM that fighter wins, the core takes the winner's controls and enters the move, waiting for the right distance. A message says when it is too far or too close, on the wrong stage, or not taken | Finishing Moves |
| Move List window | Every fighter's special moves, fatality and the distance each needs, over the game's paused title screen: page 1 (Johnny Cage, Kano, Sub-Zero, Sonya), page 2 (Raiden, Liu Kang, Scorpion). Set it On in the OSD, close the OSD and turn the pages with Left and Right; open the OSD to set it Off. Distances are given as Close, Sweep, Jump, Half screen, Full screen | Move List |
| Fixed AI Difficulty | Pins the computer opponent's level: Off, or 0 (easiest) to 9. The game raises the level after matches you win and lowers it after matches you lose; with the option on, the computer plays at the chosen level whatever the game thinks it is, in 1-player games; the demo fights between games keep the game's own level. Off gives the game's own level back at once. Not applied while the test menu is selected | Main menu |
| Cheats menu | 24 cheats on rev 5.0 (infinite time and energy for both players, drain a player's energy, one-button fatalities, no blocking, hit anywhere, night mode, secret screens and more) and Always have Reptile Clues (Reptile drops in with a hint before every round) on all three versions. The list is on the Mortal Kombat page | Cheats |

## Mortal Kombat II

Across the 11 versions in MAME: two hidden items, Finishing Moves for all 12 fighters, a Move List window, Fixed AI Difficulty, and a Cheats menu (44 cheats on L3.1, 7 to 11 on the other versions). Revision limits are noted per row. Mortal Kombat II Plus (Beta 2, hack) has Fixed AI Difficulty, four cheats and two windows of its own, a Move List and View Secrets: it adds fighters, moves and secrets and changes the code the Finishing Moves and Hidden Items are built on, so its OSD shows neither.

| Feature | What it adds | OSD page |
| --- | --- | --- |
| EJB Menu | The programmers' menu: diagnostics, coin bookkeeping, game audits, a hidden Hello page, initials entry and every character's ending. L1.1 and L1.4 have the menu but never check for its code, so the core connects it while the code plays | Hidden Items |
| Security Screen | Each attract cycle starts with a hidden "This version passed the security test" screen | Hidden Items |
| Finishing Moves | Pick a fighter and a fatality, friendship, babality, Pit / Spikes, Dead Pool or stage move (12 fighters). The core enters it on the winner's controls at the next FINISH HIM, waits for the right distance, and reports a wrong stage, or too far or too close. A revision's page lists only the moves that revision has | Finishing Moves |
| Move List window | A page per fighter (55 moves in all) with the special moves and finishing moves and their distances, over the game's paused title screen. Set it On in the OSD, close the OSD and turn the pages with Left and Right, from Liu Kang to Raiden and round; open the OSD to set it Off. Kintaro and Super Uppercut, which need a held button, are listed there too. The moves are rev L3.1's | Move List |
| Fixed AI Difficulty | Pins the computer opponent's level: Off, or 0 (easiest) to 9. The game raises the level after matches you win and lowers it after matches you lose; with the option on, the computer plays at the chosen level whatever the game thinks it is, in 1-player games; the demo fights between games keep the game's own level. Off gives the game's own level back at once. Not applied while the test menu is selected | Main menu |
| Infinite Health P1 | Player 1 takes no damage: the energy bar stays exactly where it is whatever hits land, and there is no knockout. Switching the cheat on or off does not move the bar, and a new round fills it as usual. Switch it on in the OSD's Cheats menu. Every version | Cheats |
| Infinite Health P2 | The same for player 2, who in a 1-player game is the computer opponent: it cannot be knocked out while this is on | Cheats |
| Infinite Round Time | The round clock stops counting: it stays at 99 from the start of the round (or at the time it showed when you switched the cheat on), so a round never ends on time. Switched off, the clock carries on from there. Every version | Cheats |
| Stop Finishing Move Timer | FINISH HIM waits for you: its window of 168 frames (about 3 seconds) is held open for about 10 minutes. It still ends when a finishing move starts or when the winner hits the loser. Challenger's window already stays open much longer, so the cheat changes little there. In Plus the window is the same 168 frames, or 360 when one of the hack's own options lengthens it; the cheat holds either open | Cheats |
| More cheats | Drain a player's energy, Show Hitboxes, the Jade, Smoke, Pong and Noob Saibot fights (found in each version's program), and on L3.1 the cheats of MAME's cheat file: no blocking, CPU throwing off, Finish Him every round, alternate outfits, Ball Breaker mode, night mode and more. The list is on the Mortal Kombat II page | Cheats |
| Plus Move List window (Mortal Kombat II Plus only) | A page per fighter, 17 in all: the 12 fighters, then Jade, Noob Saibot, Smoke, Kintaro and Shao Kahn. Each lists the special moves and the finishing moves with their distances, over the game's paused title screen; the moves the hack adds are marked +. Set it On in the OSD, close the OSD and turn the pages with Left and Right; open the OSD to set it Off. The moves are the MK2 Plus guide's (Ver. 2.8.50) | Move List |
| Plus View Secrets window (Mortal Kombat II Plus only) | Five pages: how to unlock and play Jade, Noob Saibot, Smoke, Kintaro and Shao Kahn; the 14 Kombat Kodes and the buttons for each player; the ending bonuses, the Dead Pool and the hack's settings. With Move List and View Secrets both On, the one turned On last is shown | View Secrets (main menu) |

## NBA Jam

Three extras across the five versions: one hidden menu, a Cheats menu (26 cheats on 3.01, 20 on 2.00, 4 to 5 on the others) and a Secret Player List window with 13 secret players and the cheat codes. Revision limits are noted per row.

| Feature | What it adds | OSD page |
| --- | --- | --- |
| Open Secret Menu (Attract) | The design team screen, then the secret Midway menu with the Jam Info statistics (hidden audit pages on 1.00, 2.00 and the prototypes). Attract mode only | Cheat Codes & Hidden Items |
| Cheats menu | The power-ups for each of the four players (big head, power-up defense and interceptions; Big Head on every version), Shot Percentage, Computer Assistance Turned Off, the hidden 3D tank game (1.00, 2.00 and 3.01) and the cheats of MAME's cheat file: infinite turbo for each player, infinite quarter and shot time, never miss a shot, dunks from anywhere and more. The list is on the NBA Jam page | Cheats |
| Secret Player List window | Page 1 lists the 13 secret players with name, initials, birthday and versions; Page 2 lists every cheat code as the players enter it. Set it On in the OSD, close the OSD and turn the pages with Left and Right; open the OSD to set it Off. The game waits while it is shown | View Secret Players (main menu) |

## NBA Jam Tournament Edition

Four extras on all twelve versions: one hidden menu, No CPU Assistance, a Cheats menu (20 to 30 cheats a version) and a seven-page Secret Player List window. Every version has all the cheat codes.

| Feature | What it adds | OSD page |
| --- | --- | --- |
| Open Secret Menu (Attract) | The design team screen, then the secret Midway menu with the Jam Info statistics. Attract mode only | Cheat Codes & Hidden Items |
| No CPU Assistance | Turns off the computer assistance that keeps games close | Cheat Codes & Hidden Items |
| Cheats menu | The power-ups of the four players (Big/Huge Head, Max Power, Powerup Goal Tending, Quick Hands), infinite turbo for each, Baby Size Players, Huge Heads, Shot Percentage, Tournament Mode and the cheats of MAME's cheat file (for the Special Edition, which has none, the same addresses moved to where the hack keeps them; Rewind has rev 2.0's, unmoved): infinite shot time, never miss a shot, dunks always break the backboard, fatalities, the All-Star Jam Team and more. The list is on the NBA Jam Tournament Edition page | Cheats |
| Secret Player List window | Pages 1-5 list the secret players with name, initials, birthday and the versions that have them (a player whose initials changed between versions has a line for each); Pages 6-7 list every cheat code as the players enter it. Set it On in the OSD, close the OSD and turn the pages with Left and Right; open the OSD to set it Off. The game waits while it is shown | View Secret Players (main menu) |

## Judge Dredd

Judge Dredd (location test) has three extras: two on the Secret Menus page and a Cheats menu.

| Feature | What it adds | OSD page |
| --- | --- | --- |
| Secret Audit Menu | Six hidden audit pages; any button turns the page | Secret Menus |
| Secret Audit Menu + Credits | Turns through the audits and holds both Start buttons at the end, which shows the staff credits | Secret Menus |
| Cheats menu | Infinite lives, infinite energy and invincibility for each of the three players (9 cheats; at most 8 can be on at once) | Cheats |

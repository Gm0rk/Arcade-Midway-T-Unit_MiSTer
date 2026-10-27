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
| Video Timing | Native 54.7 Hz or 57 Hz frames for TVs that do not hold 54.7 Hz. Only blank lines are dropped, so the whole picture is still sent. Games run about 4% faster at 57 Hz; sound keeps its pitch and tempo |
| CRT V-Size (experimental) | Makes the picture taller or shorter in 3-line steps (up to 21 lines) under CRT Adjust, in PVM mode (retimed frame) or Cabinet mode (timing unchanged, light spread over the fixed lines) |
| NVRAM | CMOS settings, audits and high scores are kept across power-off and written to the SD card once when the OSD is opened, if the game changed them, or with Save Settings |
| Secrets pages | The hidden menus, screens and debug features the programmers left in each game, as OSD items. The core enters the control codes for you |
| Information windows | Pages drawn over the game's dimmed title screen while the game waits: the Move List (Mortal Kombat games), the Secret Player List (NBA Jam games) and View Secrets (Mortal Kombat II Plus). Set one On in the OSD, close the OSD and turn the pages with Left and Right; open the OSD to set it Off |
| OSD messages | When the OSD closes, a message says whether a code was taken, what a set finishing move is waiting for, what an option just turned on does, or that the loaded version does not have it |
| MRAs | 30 MRAs for the five games (5 parents, 25 alternatives), each carrying its own table of patches and code positions, built for MAME 0.289. One is for a hack that is not in MAME, Mortal Kombat II Plus, whose OSD has its own Move List and View Secrets and Fixed AI Difficulty, but no Finishing Moves or Hidden Items, and whose zip goes in `games/hbmame` |

## Mortal Kombat

Eight extras on rev 5.0, rev 4.0 and the Turbo Ninja hack: two hidden menus, three Reptile options, Finishing Moves, a Move List window, and Fixed AI Difficulty.

| Feature | What it adds | OSD page |
| --- | --- | --- |
| EJB Menu | The programmers' menu: diagnostics, coin bookkeeping, game audits, a hidden Hello page, initials entry and every character's ending | Hidden Items |
| EJB Menu (Copyright Screen) | The same menu, reached through the hidden "This is Mortal Kombat" copyright screen | Hidden Items |
| Reptile Fight Next | Reptile fights after the next match you win in a 1-player game. Select again to cancel; used up when his fight starts | Hidden Items |
| Moon Silhouettes Always | Every match on The Pit has the silhouettes crossing the moon, and with them the chance to win flawless, never Block, finish with a fatality, and meet Reptile | Hidden Items |
| Reptile Hints Always | Reptile drops in with a hint before every round | Hidden Items |
| Finishing Moves | Pick a fighter's fatality or The Pit (7 fighters). At the next FINISH HIM that fighter wins, the core takes the winner's controls and enters the move, waiting for the right distance. A message says when it is too far or too close, on the wrong stage, or not taken | Finishing Moves |
| Move List window | Every fighter's special moves, fatality and the distance each needs, over the game's paused title screen: page 1 (Johnny Cage, Kano, Sub-Zero, Sonya), page 2 (Raiden, Liu Kang, Scorpion). Set it On in the OSD, close the OSD and turn the pages with Left and Right; open the OSD to set it Off. Distances are given as Close, Sweep, Jump, Half screen, Full screen | Move List |
| Fixed AI Difficulty | Pins the computer opponent's level: Off, or 0 (easiest) to 9. The game raises the level after matches you win and lowers it after matches you lose; with the option on, the computer plays at the chosen level whatever the game thinks it is, in 1-player games. Off gives the game's own level back at once. Not applied while the test menu is selected | Main menu |

## Mortal Kombat II

Ten extras across the 11 versions in MAME: seven hidden items, Finishing Moves for all 12 fighters, a Move List window, and Fixed AI Difficulty. Revision limits are noted per row. Mortal Kombat II Plus (Beta 2, hack) has Fixed AI Difficulty and two windows of its own, a Move List and View Secrets: it adds fighters, moves and secrets and changes the code the other extras are built on, so its OSD shows no Finishing Moves or Hidden Items.

| Feature | What it adds | OSD page |
| --- | --- | --- |
| EJB Menu | The programmers' menu: diagnostics, coin bookkeeping, game audits, a hidden Hello page, initials entry and every character's ending. L1.1 and L1.4 have the menu but never check for its code, so the core connects it while the code plays | Hidden Items |
| Hitboxes | A debug feature left in the game: every attack's hit box is drawn in green during fights | Hidden Items |
| Security Screen | Each attract cycle starts with a hidden "This version passed the security test" screen | Hidden Items |
| Pong at Battle 250 | Every two-player battle counts as battle 250: the VS screen shows "Kombat Zone: Back in Time" and both players face a game of Pong after the first round (L2.0 and later) | Hidden Items |
| Jade Fight | In a one-player game the first round you win is followed by the Jade fight, which normally takes winning a round with Low Kicks only before the "?" on the tower (L2.0 and later) | Hidden Items |
| Noob Saibot Fight | In a two-player battle the winner of the first round fights Noob Saibot, as after a 50-win streak (L3.0 and later) | Hidden Items |
| Smoke Fight | Hold Down and press Start in any fight to fight Smoke next, instead of only on The Portal while "Toasty!" shows (L2.0 and later) | Hidden Items |
| Finishing Moves | Pick a fighter and a fatality, friendship, babality, Pit / Spikes, Dead Pool or stage move (12 fighters). The core enters it on the winner's controls at the next FINISH HIM, waits for the right distance, and reports a wrong stage, too far or too close, or a move the revision lacks | Finishing Moves |
| Move List window | A page per fighter (55 moves in all) with the special moves and finishing moves and their distances, over the game's paused title screen. Set it On in the OSD, close the OSD and turn the pages with Left and Right, from Liu Kang to Raiden and round; open the OSD to set it Off. Kintaro and Super Uppercut, which need a held button, are listed there too. The moves are rev L3.1's | Move List |
| Fixed AI Difficulty | Pins the computer opponent's level: Off, or 0 (easiest) to 9. The game raises the level after matches you win and lowers it after matches you lose; with the option on, the computer plays at the chosen level whatever the game thinks it is, in 1-player games. Off gives the game's own level back at once. Not applied while the test menu is selected | Main menu |
| Plus Move List window (Mortal Kombat II Plus only) | A page per fighter, 17 in all: the 12 fighters, then Jade, Noob Saibot, Smoke, Kintaro and Shao Kahn. Each lists the special moves and the finishing moves with their distances, over the game's paused title screen; the moves the hack adds are marked +. Set it On in the OSD, close the OSD and turn the pages with Left and Right; open the OSD to set it Off. The moves are the MK2 Plus guide's (Ver. 2.8.50) | Move List |
| Plus View Secrets window (Mortal Kombat II Plus only) | Five pages: how to unlock and play Jade, Noob Saibot, Smoke, Kintaro and Shao Kahn; the 14 Kombat Kodes and the buttons for each player; the ending bonuses, the Dead Pool and the hack's settings. With Move List and View Secrets both On, the one turned On last is shown | View Secrets (main menu) |

## NBA Jam

Eight extras across the five versions: one hidden menu, five cheat options, the tank game, and a Secret Player List window with 13 secret players and the cheat codes. Revision limits are noted per row.

| Feature | What it adds | OSD page |
| --- | --- | --- |
| Open Secret Menu (Attract) | The design team screen, then the secret Midway menu with the Jam Info statistics (hidden audit pages on 1.00, 2.00 and the prototypes). Attract mode only | Cheat Codes & Hidden Items |
| Big Heads | Big heads for all players, from the next game. The only power-up in 1.00 and the prototypes | Cheat Codes & Hidden Items |
| No CPU Assistance | Turns off the computer assistance that keeps games close (3.01) | Cheat Codes & Hidden Items |
| Power-Up Defense | The POWERUP DEF code for all players (3.01 and 2.00) | Cheat Codes & Hidden Items |
| Power-Up Interceptions | The POWERUP INT code for all players (3.01 and 2.00) | Cheat Codes & Hidden Items |
| Shot Percentage | The shot percentage display (3.01 and 2.00) | Cheat Codes & Hidden Items |
| Tank Game | Pick it on Tonight's Match-Up: the core holds the code until the game takes it, and the hidden 3D tank game ("YOU ARE DEAD!") is played instead of the tip-off (1.00, 2.00 and 3.01; 3.01 once a game) | Cheat Codes & Hidden Items |
| Secret Player List window | Page 1 lists the 13 secret players with name, initials, birthday and versions; Page 2 lists every cheat code as the players enter it. Set it On in the OSD, close the OSD and turn the pages with Left and Right; open the OSD to set it Off. The game waits while it is shown | View Secret Players (main menu) |

## NBA Jam Tournament Edition

Ten extras on all nine versions: one hidden menu, seven cheat options, Tournament Mode, and a six-page Secret Player List window. Every version has all the cheat codes.

| Feature | What it adds | OSD page |
| --- | --- | --- |
| Open Secret Menu (Attract) | The design team screen, then the secret Midway menu with the Jam Info statistics. Attract mode only | Cheat Codes & Hidden Items |
| Baby Size Players | Small players, from the next game | Cheat Codes & Hidden Items |
| Head Size | Big or huge heads for all players, from the next game | Cheat Codes & Hidden Items |
| Max Power | The MAX POWER code for all players | Cheat Codes & Hidden Items |
| No CPU Assistance | Turns off the computer assistance that keeps games close | Cheat Codes & Hidden Items |
| Power-Up Goaltending | The POWERUP G.T. code for all players | Cheat Codes & Hidden Items |
| Quick Hands | The QUICK HANDS code for all players | Cheat Codes & Hidden Items |
| Shot Percentage | The shot percentage display | Cheat Codes & Hidden Items |
| Tournament Mode | Pick it on Tonight's Match-Up: the core enters the code, and the game is played without power-ups, CPU assistance or other secrets ("TOURNAMENT MODE" at the tip-off) | Cheat Codes & Hidden Items |
| Secret Player List window | Pages 1-4 list the secret players with name, initials, birthday and the versions that have them (a player whose initials changed between versions has a line for each); Pages 5-6 list every cheat code as the players enter it. Set it On in the OSD, close the OSD and turn the pages with Left and Right; open the OSD to set it Off. The game waits while it is shown | View Secret Players (main menu) |

## Judge Dredd

Judge Dredd (location test) has two extras, both on the Secret Menus page.

| Feature | What it adds | OSD page |
| --- | --- | --- |
| Secret Audit Menu | Six hidden audit pages; any button turns the page | Secret Menus |
| Secret Audit Menu + Credits | Turns through the audits and holds both Start buttons at the end, which shows the staff credits | Secret Menus |

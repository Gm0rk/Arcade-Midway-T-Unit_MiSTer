# Extra content

[Back to the core's README](../README.md)

<!-- The game sections below are copied into each game's page (docs/<Game>.md) by tools/extra_content.py. Edit them here, then run it. -->

Beyond the arcade board itself, the core adds 11 core-wide features and a set of hidden menus, cheats and information windows for each of the five games. Core-wide features come first, then each game.

## Core-wide

| Feature | What it adds |
| --- | --- |
| OSD layout | The same menu for every game: Video Settings, Sound Options (the Mortal Kombat games), System Options, Extras, Pause When OSD is Open, Reset, Reset and close OSD. Extras holds what the loaded version has (its Cheats and the core's own items) in alphabetical order; an item a game lacks is not shown and the ones below it move up |
| System Options page | MAME's DIP switches as OSD options under Dip Switches, in alphabetical order, with MAME's defaults, then Service Credit, Tilt and Service Menu. Switches a version does not use are left out. The games read most of them at power-up, so reset after a change. The switches are the core's own options: the MRAs carry none, so each setting is kept with the game's other OSD settings |
| Service Credit and Tilt | Two lines on the System Options page: selecting one adds a credit or slams the tilt switch |
| Service Menu | Opens the game's test mode (Service Menu: On) from the System Options page |
| Pause | Pause from a button or the OSD, and "Pause When OSD is Open" |
| Video Timing | Native 54.7 Hz or 57 Hz frames for TVs that do not hold 54.7 Hz. Only blank lines are dropped, so the whole picture is still sent. Games run about 4% faster at 57 Hz; sound keeps its pitch and tempo. The black screen while a game loads uses the same frame |
| CRT V-Size (experimental) | Makes the picture taller or shorter in 3-line steps (up to 21 lines) under CRT Adjust, in PVM mode (retimed frame) or Cabinet mode (timing unchanged, light spread over the fixed lines) |
| NVRAM | CMOS settings, audits and high scores are kept across power-off and written to the SD card once when the OSD is opened, if the game changed them, or with Save Settings |
| Extras page | The Cheats menu, the hidden menus, screens and debug features the programmers left in each game, the Finishing Moves, the Move List and the other options the core adds, as items of one page. The core enters the control codes for you |
| Information windows | Pages drawn over the game's dimmed title screen while the game waits: the Move List (the Mortal Kombat games; Mortal Kombat Plus, Mortal Kombat II rev 4.0 and Mortal Kombat II Plus have their own), the Secret Player List (NBA Jam games) and View Secrets (Mortal Kombat II Plus). Set one On in the OSD, close the OSD and turn the pages with Left and Right; open the OSD to set it Off |
| OSD messages | When the OSD closes, a message says whether a code was taken, what a set finishing move is waiting for, or what an option just turned on or off does. The OSD shows only what the loaded version has, so there is no "not available" message |
| MRAs | 38 MRAs for the five games (5 parents, 33 alternatives), each carrying its own table of patches and code positions and its Cheats list, built for MAME 0.289. Nine are for hacks that are not in MAME, whose zips go in `games/hbmame`: Mortal Kombat Plus (its own Move List) and Mortal Kombat II rev 4.0 (its own Move List and Finishing Moves, no hidden items), which have the extras of their game that their programs allow, Mortal Kombat II Plus (Beta 1 and Beta 2), whose OSD has its own Move List and View Secrets, Finishing Moves, Fixed AI Difficulty and the Cheats, but no Hidden Items, and NBA Jam Tournament Edition Special Edition (5.0, 5.02) and NBA Jam Rewind (1.1, 1.2, 4 Jam unprotected), which have the Tournament Edition's extras |

## Mortal Kombat

Nine extras on rev 5.0, rev 4.0, the Turbo Ninja hack and the Plus hack: two hidden menus, two Reptile options, Finishing Moves, a Move List window, Attract Sound, Fixed AI Difficulty, and a Cheats menu (24 cheats on rev 5.0 and Plus, one on the others). The Plus hack has a Move List of its own.

| Feature | What it adds | OSD page |
| --- | --- | --- |
| EJB Menu | The programmers' menu: diagnostics, coin bookkeeping, game audits, a hidden Hello page, initials entry and every character's ending | Extras |
| EJB Menu (Copyright Screen) | The same menu, reached through the hidden "This is Mortal Kombat" copyright screen | Extras |
| Reptile Fight Next | Reptile fights after the next match you win in a 1-player game. Select again to cancel; used up when his fight starts | Extras |
| Moon Silhouettes | Every match on The Pit has the silhouettes crossing the moon, and with them the chance to win flawless, never Block, finish with a fatality, and meet Reptile | Extras |
| Finishing Moves | Pick a fighter's fatality (7 fighters, in alphabetical order). At the next FINISH HIM that fighter wins, the core has the game call the fatality and taps the one button it runs on, waiting for the right distance. A message says when it is too far or too close, or not taken. The Plus hack has a page of its own: eight fighters with Reptile, and the Babalities the hack adds | Extras (Auto Finishing Moves) |
| Move List window | Every fighter's special moves, fatality and the distance each needs, over the game's paused title screen: in alphabetical order: page 1 (Johnny Cage, Kano, Liu Kang, Raiden), page 2 (Scorpion, Sonya, Sub-Zero). Set it On in the OSD, close the OSD and turn the pages with Left and Right; open the OSD to set it Off. Distances are given as Close, Sweep, Jump, Half screen, Full screen. The moves are rev 5.0's, found in the game's program and played in MAME (each page ends with the address of MKKomplete's guide); the Plus hack has its own window | Extras |
| Plus Move List window (Mortal Kombat Plus only) | Five pages over the game's paused title screen: three of fighters in alphabetical order (Johnny Cage, Kano and Liu Kang; Raiden, the hidden Reptile and Scorpion; Sonya and Sub-Zero) with the special moves, the fatality and the Babality and their distances, then the general moves with what Plus adds, and notes on the Babalities, The Pit and the distances. The moves the hack adds are marked +. Turned with Left and Right like the other windows. The moves are the Mortal Kombat Plus guide's (MKKomplete; each page ends with its address) | Extras |
| Attract Sound | Default: the game stops the attract mode's sound after a few attract cycles. Always On: the sound plays through the attract mode. Reset to apply the change (the Sound Options page says so); a message names the setting, "Attract Sound: Always On" or "Attract Sound: Default". The Attract Sound DIP switch still applies | Sound Options |
| Fixed AI Difficulty | Pins the computer opponent's level: Off, or 0 (easiest) to 9. The game raises the level after matches you win and lowers it after matches you lose; with the option on, the computer plays at the chosen level whatever the game thinks it is, in 1-player games; the demo fights between games keep the game's own level. Off gives the game's own level back at once. Not applied while the test menu is selected | Extras |
| Cheats menu | 24 cheats on rev 5.0 and Plus (infinite time and energy for both players, drain a player's energy, one-button fatalities, no blocking, hit anywhere, night mode, secret screens and more) and Always have Reptile Clues (Reptile drops in with a hint before every round) on all four versions. The list is on the Mortal Kombat page | Extras (Cheats) |

## Mortal Kombat II

Across the 11 versions in MAME and the rev 4.0 hack: two hidden items, Finishing Moves for all 12 fighters (15 on rev 4.0, 17 on Plus), a Move List window, Attract Sound, Fixed AI Difficulty, and a Cheats menu (44 cheats on L3.1, 7 to 11 on the other versions). Revision limits are noted per row; rev 4.0 (hack) has no hidden items, and its Move List window and Finishing Moves have pages and moves of its own. Mortal Kombat II Plus (Beta 1 and Beta 2, hacks) have Finishing Moves for the arcade game's moves and the five new fighters', Fixed AI Difficulty, four cheats and two windows of its own, a Move List and View Secrets: they add fighters, moves and secrets and change the code the Hidden Items are built on, so their OSD has no Hidden Items page.

| Feature | What it adds | OSD page |
| --- | --- | --- |
| EJB Menu | The programmers' menu: diagnostics, coin bookkeeping, game audits, a hidden Hello page, initials entry and every character's ending. L1.1 and L1.4 have the menu but never check for its code, so the core connects it while the code plays | Extras |
| Security Screen | Each attract cycle starts with a hidden "This version passed the security test" screen | Extras |
| Finishing Moves | Pick a fighter (fighters in alphabetical order, each fighter's moves by type: fatalities, Stage Fatality and Dead Pool, friendship, babality) and a fatality, friendship, babality, Stage Fatality or the Dead Pool (12 fighters, the hacks' hidden ones included: 15 on rev 4.0, 17 on Plus). The core enters it on the winner's controls at the next FINISH HIM, waits for the right distance, and reports a wrong stage, or too far or too close. Rev L2.0 and later, Plus and rev 4.0 have every move but the Dead Pool as a direct finisher: the core has the game call the move and presses only the button it runs on (the moves that hold a button take a short hold for the long one). A revision's page lists only the moves that revision has; Plus lists rev L3.1's and the moves of the hack's five fighters (17 fighters); rev 4.0 (hack) lists its own moves (15 fighters with Ermac, Jade and Rain, no friendships, 66 moves and the Dead Pool; Liu Kang's Red Dragon Flame works in his red costume only) | Extras (Auto Finishing Moves) |
| Move List window | A page per fighter (55 moves in all) with the special moves and finishing moves and their distances, over the game's paused title screen. Set it On in the OSD, close the OSD and turn the pages with Left and Right, from Baraka to Sub-Zero and round; open the OSD to set it Off. Raiden's Super Uppercut, which needs a button held from before FINISH HIM, is listed there too. The moves are rev L3.1's; rev 4.0 and Plus have their own windows | Extras |
| Rev 4.0 Move List window (rev 4.0 only) | 19 pages over the game's paused title screen: a page per fighter in alphabetical order, 15 in all (the 12 fighters and the hidden Jade, Ermac and Rain), with the special moves, the finishing moves and their distances and the morphs of Shang Tsung (a second page for his finishing moves), then three pages on what rev 4.0 changes and on the secret opponents. A + marks what rev 4.0 adds to the arcade game's moves. Turned with Left and Right like the other windows. The moves are the author's guide (v4.0) | Extras |
| Attract Sound | Default: the game stops the attract mode's sound after 3 attract cycles. Always On: the sound plays through the attract mode. Reset to apply the change (the Sound Options page says so); a message names the setting, "Attract Sound: Always On" or "Attract Sound: Default". The Attract Sound DIP switch still applies. Every version, Plus included | Sound Options |
| Fixed AI Difficulty | Pins the computer opponent's level: Off, or 0 (easiest) to 9. The game raises the level after matches you win and lowers it after matches you lose; with the option on, the computer plays at the chosen level whatever the game thinks it is, in 1-player games; the demo fights between games keep the game's own level. Off gives the game's own level back at once. Not applied while the test menu is selected | Extras |
| Infinite Health P1 | Player 1 takes no damage: the energy bar stays exactly where it is whatever hits land, and there is no knockout. Switching the cheat on or off does not move the bar, and a new round fills it as usual. Switch it on in the OSD's Cheats menu. Every version | Extras (Cheats) |
| Infinite Health P2 | The same for player 2, who in a 1-player game is the computer opponent: it cannot be knocked out while this is on | Extras (Cheats) |
| Infinite Round Time | The round clock stops counting: it stays at 99 from the start of the round (or at the time it showed when you switched the cheat on), so a round never ends on time. Switched off, the clock carries on from there. Every version | Extras (Cheats) |
| Stop Finishing Move Timer | FINISH HIM waits for you: its window of 168 frames (about 3 seconds) is held open for about 10 minutes. It still ends when a finishing move starts or when the winner hits the loser. Challenger's window already stays open much longer, so the cheat changes little there. In Plus the window is the same 168 frames, or 360 when one of the hack's own options lengthens it; the cheat holds either open | Extras (Cheats) |
| More cheats | Drain a player's energy, Show Hitboxes, the Jade, Smoke, Pong and Noob Saibot fights (found in each version's program), and on L3.1 the cheats of MAME's cheat file: no blocking, CPU throwing off, Finish Him every round, alternate outfits, Ball Breaker mode, night mode and more. The list is on the Mortal Kombat II page | Extras (Cheats) |
| Plus Move List window (Mortal Kombat II Plus only) | A page per fighter in alphabetical order, 17 in all: the 12 fighters and Jade, Noob Saibot, Smoke, Kintaro and Shao Kahn. Each lists the special moves and the finishing moves with their distances, over the game's paused title screen; the moves the hack adds are marked +. Set it On in the OSD, close the OSD and turn the pages with Left and Right; open the OSD to set it Off. The moves are the MK2 Plus guide's (Ver. 2.8.50) | Extras |
| Plus View Secrets window (Mortal Kombat II Plus only) | Five pages: how to unlock and play Jade, Noob Saibot, Smoke, Kintaro and Shao Kahn; the 14 Kombat Kodes and the buttons for each player; the ending bonuses, the Dead Pool and the hack's settings. With Move List and View Secrets both On, the one turned On last is shown | Extras |

## NBA Jam

Four extras across the five versions: one hidden menu, Fixed AI Difficulty (3.01 only), a Cheats menu (26 cheats on 3.01, 20 on 2.00, 4 to 5 on the others) and a Secret Player List window with 13 secret players and the cheat codes. Revision limits are noted per row.

| Feature | What it adds | OSD page |
| --- | --- | --- |
| Midway Menu | The design team screen, then the secret Midway menu with the Jam Info statistics (hidden audit pages on 1.00, 2.00 and the prototypes). Attract mode only | Extras |
| Fixed AI Difficulty | Pins the computer opponents' skill: Off, or 0 (easiest) to 9. From the start of the game every computer opponent plays at the skill you pick, whatever its players' ratings and your record, and the computer players' catch-up (the help the side that is behind gets) is off; levels 6 to 9 also turn on the game's hard play routines. Your own players are left as the game has them. Applies from the next game. Rev 3.01 only. Not applied while the test menu is selected | Extras |
| Cheats menu | The power-ups for each of the four players (big head, power-up defense and interceptions; Big Head on every version), Shot Percentage, Computer Assistance Turned Off, the hidden 3D tank game (1.00, 2.00 and 3.01) and the cheats of MAME's cheat file: infinite turbo for each player, infinite quarter and shot time, never miss a shot, dunks from anywhere and more. The list is on the NBA Jam page | Extras (Cheats) |
| Secret Player List window | Page 1 lists the 13 secret players with name, initials, birthday and versions; Page 2 lists every cheat code as the players enter it. Set it On in the OSD, close the OSD and turn the pages with Left and Right; open the OSD to set it Off. The game waits while it is shown | Extras |

## NBA Jam Tournament Edition

Five extras on all fourteen versions: one hidden menu, No CPU Assistance, Fixed AI Difficulty, a Cheats menu (20 to 30 cheats a version) and a seven-page Secret Player List window. Every version has all the cheat codes.

| Feature | What it adds | OSD page |
| --- | --- | --- |
| Midway Menu | The design team screen, then the secret Midway menu with the Jam Info statistics. Attract mode only | Extras |
| No CPU Assistance | Turns off the computer assistance that keeps games close | Extras |
| Fixed AI Difficulty | Pins the computer opponents' skill: Off, or 0 (easiest) to 9. From the start of the game every computer opponent plays at the skill you pick, whatever its players' ratings and your record, and the computer players' catch-up (the help the side that is behind gets) is off; levels 6 to 9 also turn on the game's hard play routines. Your own players are left as the game has them. Applies from the next game. Not applied while the test menu is selected | Extras |
| Cheats menu | The power-ups of the four players (Big/Huge Head, Max Power, Powerup Goal Tending, Quick Hands), infinite turbo for each, Baby Size Players, Huge Heads, Shot Percentage, Tournament Mode and the cheats of MAME's cheat file (for the Special Edition, which has none, the same addresses moved to where the hack keeps them; Rewind has rev 2.0's, unmoved): infinite shot time, never miss a shot, dunks always break the backboard, fatalities, the All-Star Jam Team and more. The list is on the NBA Jam Tournament Edition page | Extras (Cheats) |
| Secret Player List window | Pages 1-5 list the secret players with name, initials, birthday and the versions that have them (a player whose initials changed between versions has a line for each); Pages 6-7 list every cheat code as the players enter it. Set it On in the OSD, close the OSD and turn the pages with Left and Right; open the OSD to set it Off. The game waits while it is shown | Extras |

## Judge Dredd

Judge Dredd (location test) has three extras on the Extras page: two hidden audit menus and a Cheats menu.

| Feature | What it adds | OSD page |
| --- | --- | --- |
| Secret Audit Menu | Six hidden audit pages; any button turns the page | Extras |
| Secret Audit Menu + Credits | Turns through the audits and holds both Start buttons at the end, which shows the staff credits | Extras |
| Cheats menu | Infinite lives, infinite energy and invincibility for each of the three players (9 cheats; at most 8 can be on at once) | Extras (Cheats) |

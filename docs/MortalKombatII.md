# Mortal Kombat II

[Back to the core's README](../README.md)

Mortal Kombat II (Midway, 1993) on the T-Unit board, with the DCS sound board.

- [Versions](#versions)
- [Controls](#controls)
- [Move List](#move-list)
- [Secrets](#secrets)
- [Finishing Moves](#finishing-moves)

## Versions

| MRA | MAME set |
|---|---|
| Mortal Kombat II (rev L3.1) | mk2 |
| Mortal Kombat II (rev L3.2, European) | mk2r32e |
| Mortal Kombat II (rev L3.1, European) | mk2r31e |
| Mortal Kombat II (rev L3.0) | mk2r30 |
| Mortal Kombat II (rev L2.1) | mk2r21 |
| Mortal Kombat II (rev L2.0) | mk2r20 |
| Mortal Kombat II (rev L1.4) | mk2r14 |
| Mortal Kombat II (rev L1.1) | mk2r11 |
| Mortal Kombat II (rev L4.2, hack) | mk2r42 |
| Mortal Kombat II (rev L9.1, hack) | mk2r91 |
| Mortal Kombat II Challenger (hack) | mk2chal |

The first is in `_Arcade`, the others in `_Arcade/_alternatives/_Mortal Kombat II`.
With a merged ROM set they all load from `mk2.zip`.

## Controls

Two players: High Punch, Block, High Kick, Low Punch, Low Kick, Block 2, plus
Start, Coin, Test (service mode) and Pause.

## Move List

The OSD's Move List page has the Fighter (the same choice as the Finishing
Moves page) and Show Move List: a window over the game, on the game's title
screen, with that fighter's special moves and finishing moves and the
distance each finishing move needs. The game waits while the window is on;
turn it off to play on. The window only shows the moves; the core does not
enter them for you (the Finishing Moves page does that).

Commands as the game reads them: F toward the opponent, B away. In
(BL U U) LK, Block keeps the fighter from jumping on U and is let go
before LK; (HP 1 s) means High Punch held for about a second, then let
go; X+Y pressed together; "in air" during a jump. The list is the one of
rev L3.1; other revisions and the hacks may differ.

| Fighter | Move | Command |
|---|---|---|
| Liu Kang | High Fireball | F F HP |
|  | Low Fireball | F F LP |
|  | Flying Kick | F F HK |
|  | Bicycle Kick | (LK 3 s) |
| Kung Lao | Hat Throw | B F LP, Up / Down steer the hat |
|  | Teleport | D U |
|  | Spin | (BL U U) LK |
|  | Dive Kick | D HK in air |
| Johnny Cage | High Bolt | F D B HP |
|  | Low Bolt | B D F LP |
|  | Shadow Kick | B F LK |
|  | Uppercut | B D B HP |
|  | Ball Breaker | LP+BL |
| Reptile | Acid Spit | F F HP |
|  | Force Ball | B B HP+LP |
|  | Invisibility | (BL U U D) HP |
|  | Slide | B+LP+LK+BL |
| Sub-Zero | Freeze | D F LP |
|  | Ground Freeze | D B LK |
|  | Slide | B+LP+LK+BL |
| Shang Tsung | Skull | B B HP |
|  | 2 Skulls | B B F HP |
|  | 3 Skulls | B B F F HP |
|  | Morph into Liu Kang | B F F BL |
|  | Morph into Kung Lao | B D B HK |
|  | Morph into Johnny Cage | B B D LP |
|  | Morph into Reptile | (BL U D) HP |
|  | Morph into Sub-Zero | F D F HP |
|  | Morph into Kitana | BL BL BL |
|  | Morph into Jax | D F B HK |
|  | Morph into Mileena | (HP 1 s) |
|  | Morph into Baraka | D D LK |
|  | Morph into Scorpion | (BL U U) |
|  | Morph into Raiden | D B F LK |
| Kitana | Fan Throw | F F HP+LP |
|  | Fan Lift | B B B HP |
|  | Flying Punch | F D B HP |
| Jax | Energy Wave | F D B HK |
|  | Gotcha Grab | F F LP |
|  | Ground Smash | (LK 2 s) |
|  | Back Breaker | BL in air, next to an opponent in the air |
| Mileena | Sai Throw | (HP 1 s) |
|  | Teleport Kick | F F LK |
|  | Roll | B B D HK |
| Baraka | Blade Spark | D B HP |
|  | Blade Fury | B B B LP |
| Scorpion | Spear | B B LP |
|  | Teleport | D B HP |
|  | Scissors | F D B LK |
|  | Air Throw | BL in air, next to an opponent in the air |
| Raiden | Lightning | D F LP |
|  | Teleport | D U |
|  | Torpedo | B B F |
|  | Electric Grab | (HP 2 s), close to the opponent |

## Secrets

The Mortal Kombat games drop a half-entered code when the attract mode moves
to its next screen; the core then enters the EJB code again (three tries at
most).

| OSD item | What it does |
|---|---|
| EJB Menu | The programmers' menu, with the same pages as Mortal Kombat's: diagnostics, coin bookkeeping, game audits, a hidden Hello page, initials entry and every character's ending. Revisions L1.1 and L1.4 have the menu and its code but never check for the code; the core connects it while the code plays |
| Security Screen | Each attract cycle starts with a hidden screen, "This version passed the security test", after a few seconds of black |
| Hitboxes | A debug feature left in the game: the hit box of every attack is drawn in green during fights |
| Pong at Battle 250 | Every two-player battle counts as battle 250: the VS screen shows "Kombat Zone: Back in Time", and after the first round both players face a game of Pong (rev L2.0 and later) |
| Noob Saibot Fight | The fight the game keeps for a player with 50 wins in a row: in a two-player battle, the winner of the first round goes on to fight Noob Saibot ("Incredible winning streak!!"). The game then carries on as after a real streak (rev L3.0 and later) |
| Jade Fight | In a one-player game, the first round you win is followed by the fight against Jade ("Now you must battle with an undiscovered warrior from Mortal Kombat One"). Normally that takes winning a round with Low Kicks only in the battle before the "?" on the tower (rev L2.0 and later) |
| Smoke Fight | Hold Down and press Start during any fight to fight Smoke next ("You have found the passage from the Outworld to the Earth Realm"). Normally that only works on The Portal while the "Toasty!" man is on screen (rev L2.0 and later) |

When the OSD closes, a message says what an option just turned on does, or
that the loaded revision does not have it.

## Finishing Moves

The OSD's Finishing Moves page enters a fighter's finishing moves for you.
Pick the Fighter, then one of the moves listed under it: the OSD closes and
the move is set. It plays at the next FINISH HIM where that fighter is the
winner, for either player. With "Pause when OSD is open" (the default) you
can open the OSD at FINISH HIM and pick the move then.

When the loser stands dizzy and the winner stands still, the core takes the
winner's controls (the player's own are ignored meanwhile) and enters the
move. Many moves only work at a certain distance: when the fighters are too
far apart or too close, a message says so and the move waits; step in or
out and it goes as soon as the distance fits. Messages also say when a stage
move is set on another stage, when FINISH HIM ends before the move could
start (the move stays set for the next one) and when the game did not take
the move. A move is used once; "Clear the set move" drops a set move.

Commands as the game reads them: F toward the opponent, B away, U up, D
down; HP / LP / HK / LK / BL High Punch, Low Punch, High Kick, Low Kick,
Block. (X) means X held during the rest of the command and let go at the
end, (X 2 s) held for about 2 seconds.

Distances: Close (touching, up to about a step away), Sweep (within a
sweep's reach), Jump (beyond the sweep, about a jump away), Half screen, Full
screen, Anywhere; "Close to sweep" means anywhere from close up to a sweep
away. Measured in MAME: a sweep reaches about 118 pixels between the
fighters (they stand no closer than about 62), a forward jump covers about
160; the zones are Close up to 79, Sweep 80-127, Jump 128-199, Half screen
200-259, Full screen 260 or more.

Pit / Spikes works on The Pit II and the Kombat Tomb (Shang Tsung's Pit only
on The Pit II), the Dead Pool on The Dead Pool. Friendships and babalities
need a round won without High or Low Punch: the game's rule. Two fatalities
are not in the list because they need a button held from before FINISH HIM:
Shang Tsung's Kintaro (Low Punch held about 18 seconds and let go at FINISH
HIM, sweep distance) and Raiden's Super Uppercut (High Punch about 7
seconds, close). The Move List window shows them too (from the game's code; not
tried in MAME).

The early revisions have fewer moves: L2.0 and L2.1 have no Dead Pool and no
Kung Lao friendship, and Shang Tsung's friendship and Pit differ there; L1.1
and L1.4 lack most friendships, babalities and stage moves and some
fatalities. Picking one of those shows "Not available in this revision of
the game".

| Fighter | Move | Command | Distance |
|---|---|---|---|
| Liu Kang | Dragon | D F B B HK | Close to sweep |
|  | Cartwheel | D F U B D | Close to jump |
|  | Friendship | F B B B LK | Anywhere |
|  | Babality | D D F B LK | Anywhere |
|  | Pit / Spikes | B F F LK | Close |
| Kung Lao | Hat Throw | (LP) B F | Full screen |
|  | Decapitation | F F F LK | Sweep |
|  | Friendship | B B B D HK | Anywhere |
|  | Babality | B B F F HK | Anywhere |
|  | Pit / Spikes | F F F HP | Close |
| Johnny Cage | Torso Rip | D D F F LP | Close |
|  | Decapitation | F F D U | Close |
|  | Friendship | D D D D HK | Anywhere |
|  | Babality | B B B HK | Anywhere |
|  | Pit / Spikes | D D D HK | Close |
| Reptile | Tongue | B B D LP | Jump to half screen |
|  | Slice | U U D HP, then F F D HK | Close |
|  | Friendship | B B D LK | Anywhere |
|  | Babality | D B B LK | Anywhere |
|  | Pit / Spikes | D F F BL | Close |
| Sub-Zero | Deep Freeze | F F D HK, then F D F F HP | Sweep to jump |
|  | Ice Grenade | (LP) B B D F | Full screen |
|  | Friendship | B B D HK | Anywhere |
|  | Babality | D B B HK | Anywhere |
|  | Pit / Spikes | D F F BL | Close |
| Shang Tsung | Soul Drain | U D U LK | Close |
|  | Spikes | (HK 1 s) | Sweep |
|  | Friendship | B B D F HK | Anywhere |
|  | Babality | B F D HK | Anywhere |
|  | Pit | D D U D | Close |
| Kitana | Fan Decap | BL BL BL HK | Close |
|  | Kiss of Death | (LK) F F D F | Close |
|  | Friendship | D D D U LK | Anywhere |
|  | Babality | D D D LK | Anywhere |
|  | Pit / Spikes | F D F HK | Close |
| Jax | Arm Rip | BL BL BL BL LP | Close to sweep |
|  | Head Smash | (LP) F F F | Close |
|  | Friendship | D D U U LK | Anywhere |
|  | Babality | D U D U LK | Anywhere |
|  | Pit / Spikes | U U D LK | Close |
| Mileena | Sai Stab | F B F LP | Close |
|  | Inhale | (HK 2 s) | Close |
|  | Friendship | D D D U HK | Anywhere |
|  | Babality | D D D HK | Anywhere |
|  | Pit / Spikes | F D F LK | Close |
| Baraka | Decapitation | B B B B HP | Close to sweep |
|  | Impale | B F D F LP | Close to sweep |
|  | Friendship | U F F HK | Anywhere |
|  | Babality | F F F HK | Anywhere |
|  | Pit / Spikes | F F D HK | Close |
| Scorpion | Toasty | D D U U HP | Anywhere |
|  | Torch | U U HP | Jump |
|  | Slice | (HP) D F F F | Close |
|  | Friendship | B B D HK | Anywhere |
|  | Babality | D B B HK | Anywhere |
|  | Pit / Spikes | D F F BL | Close |
| Raiden | Electrocution | (LK 2 s) | Close |
|  | Friendship | D B F HK | Jump or farther |
|  | Babality | D D U HK | Anywhere |
|  | Pit / Spikes | U U HP | Close |

Every fighter also has the Dead Pool: D+LP+LK HP, close.

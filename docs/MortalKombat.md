# Mortal Kombat

[Back to the core's README](../README.md)

Mortal Kombat (Midway, 1992) in its T-Unit revisions, with the ADPCM sound
board. The earlier Y Unit revisions are not part of this core.

- [Versions](#versions)
- [Controls](#controls)
- [Move List](#move-list)
- [Secrets](#secrets)
- [Finishing Moves](#finishing-moves)

## Versions

| MRA | MAME set |
|---|---|
| Mortal Kombat (rev 5.0 T-Unit 03-19-93) | mk |
| Mortal Kombat (rev 4.0 T-Unit 02-11-93) | mkr4 |
| Mortal Kombat (Turbo Ninja T-Unit 03-19-93, hack) | mktturbo |

The first is in `_Arcade`, the others in `_Arcade/_alternatives/_Mortal Kombat`.
With a merged ROM set they all load from `mk.zip`, the same zip as the Y Unit
Mortal Kombat sets.

## Controls

Two players: High Punch, Block, High Kick, Low Punch, Low Kick, Block 2, plus
Start, Coin, Test (service mode) and Pause.

## Move List

The OSD's Move List page shows the special moves of the fighter picked
there (the same Fighter choice as the Finishing Moves page). It only shows
them; the core does not enter these moves for you.

Commands as the game reads them: F toward the opponent, B away; (BL B F)
means Block held while you enter B F; X+Y pressed together. The list is
the one of rev 5.0; rev 4.0 and the Turbo Ninja hack may differ.

| Fighter | Move | Command |
|---|---|---|
| Johnny Cage | Green Bolt | B F LP |
|  | Shadow Kick | B F LK |
|  | Split Punch | LP+BL |
| Kano | Knife Throw | (BL B F) |
|  | Cannonball | F D B U |
| Sub-Zero | Freeze | D F LP |
|  | Slide | B+LP+LK+BL |
| Sonya | Ring Toss | LP B LP, quickly (all within about 0.4 s) |
|  | Leg Grab | D+LP+LK+BL |
|  | Square Wave | F B HP |
| Raiden | Lightning | D F LP |
|  | Teleport | D U |
|  | Torpedo | B B F |
| Liu Kang | Fireball | F F HP |
|  | Flying Kick | F F HK |
| Scorpion | Spear | B B LP |
|  | Teleport | D B HP |

## Secrets

The game drops a half-entered code when the attract mode moves to its next
screen; the core then enters the code again (three tries at most).

| OSD item | What it does |
|---|---|
| EJB Menu | The programmers' menu ("Mortal Kombat EJB Menu"): diagnostics, coin bookkeeping, game audits, a hidden Hello page, initials entry and every character's ending |
| EJB Menu (Copyright Screen) | The same menu, after a hidden copyright screen ("This is Mortal Kombat") |

## Finishing Moves

The OSD's Finishing Moves page enters a fighter's fatality or The Pit for
you. Pick the Fighter, then one of the moves listed under it: the OSD closes
and the move is set. It plays at the next FINISH HIM where that fighter is the winner,
for either player. With "Pause when OSD is open" (the default) you can open
the OSD at FINISH HIM and pick the move then.

When the loser stands dizzy and the winner stands still, the core takes the
winner's controls (the player's own are ignored meanwhile) and enters the
move. Many moves only work at a certain distance: when the fighters are too
far apart or too close, a message says so and the move waits; step in or
out and it goes as soon as the distance fits. Messages also say when The Pit
is set on another stage, when FINISH HIM ends before the move could start
(the move stays set for the next one) and when the game did not take the
move. A move is used once; "Clear the set move" drops a set move.

Commands as the game reads them: F toward the opponent, B away, U up, D
down; HP / LP / HK / LK / BL High Punch, Low Punch, High Kick, Low Kick,
Block. (X) means X held during the rest of the command and let go at the
end. Distances are in pixels between the two fighters (the screen is 400
wide). The Pit works on The Pit stage only.

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

# Judge Dredd

[Back to the core's README](../README.md)

Judge Dredd (Midway, 1992), the location-test version, on the T-Unit board
with the ADPCM sound board.

<img src="https://github.com/Gm0rk/Arcade-Midway-T-Unit_MiSTer/blob/main/media/Judge_Dredd.png" width="400"> <img src="https://github.com/Gm0rk/Arcade-Midway-T-Unit_MiSTer/blob/main/media/Judge_Dredd_2.png" width="400">

## Versions

| MRA | MAME set |
|---|---|
| Judge Dredd (rev TA1 7-12-92, location test) | jdreddp |

The MRA is in `_Arcade`; the ROMs are in `jdreddp.zip`.

## Controls

Up to three players: Kick, Jump, Punch, Crouch, plus Start, Coin, Test
(service mode) and Pause.

<!-- extra-content:start (from ExtraContent.md by tools/extra_content.py) -->
## Extra content

Judge Dredd (location test) has three extras: two on the Secret Menus page and a Cheats menu.

| Feature | What it adds | OSD page |
| --- | --- | --- |
| Secret Audit Menu | Six hidden audit pages; any button turns the page | Secret Menus |
| Secret Audit Menu + Credits | Turns through the audits and holds both Start buttons at the end, which shows the staff credits | Secret Menus |
| Cheats menu | Infinite lives, infinite energy and invincibility for each of the three players (9 cheats; at most 8 can be on at once) | Cheats |

<!-- extra-content:end -->

## Secrets

On the OSD's Secret Menus page:

| OSD item | What it does |
|---|---|
| Secret Audit Menu | Six hidden audit pages; any button turns the page |
| Secret Audit Menu + Credits | Turns through the audits and holds both Start buttons at the end, which shows the staff credits |

## Cheats

The OSD's Cheats menu (on the main menu, below Secret Menus) lists 9 cheats:
infinite lives, infinite energy and invincibility for each of the three
players. Select one to switch it on or off; a mark shows the ones that are on.
All are off each time a game loads: the OSD does not keep them across loads.

All 9 are from MAME's cheat file for jdreddp, whose addresses are for this
version only. The names are MAME's. MAME's Invincibility is a pair, 'ON' and
'OFF'; here it is one cheat per player, and the menu's switch does the
turning off.

| Cheat | Units | Versions |
|---|---|---|
| P1 Infinite Energy | 1 | All |
| P1 Infinite Lives | 1 | All |
| P1 Invincibility | 1 | All |
| P2 Infinite Energy | 1 | All |
| P2 Infinite Lives | 1 | All |
| P2 Invincibility | 1 | All |
| P3 Infinite Energy | 1 | All |
| P3 Infinite Lives | 1 | All |
| P3 Invincibility | 1 | All |

How a cheat acts: one that sets a value makes the game read that value from the word it names, or only the bits of the word it covers (one byte, one player's flag), whenever the CPU reads it while the game runs with interrupts on; the game's own value is never written over, so switching the cheat off gives the game back at once, and the diagnostics' RAM test sees the game as it is. The Units column is how many of the core's 8 cheat entries a cheat uses: switch cheats on until their units add up to 8 at most; the menu refuses a switch-on that would pass 8. With 9 cheats of 1 unit each, one of the 9 is always left off.

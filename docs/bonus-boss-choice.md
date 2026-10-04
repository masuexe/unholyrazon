# Bonus winner boss choice

Razon3's `rb_BossSelector` reward is handled by `unholy/uh_boss_choice.acs`.
The existing `ub_WhoWonTheRound` callers grant it: FFA variants (including
Football, True Power and Rune FFA), Boss FFA, Satan Seal FFA and demoneye
events. One-vs-all and custom callback events retain their existing endings.
Only a single living, non-spectating player earns it; draws grant no reward.

At the next ordinary round's countdown, the winner sees three distinct random
COMMON bosses and one random RARE boss from UHDT. Strafe left/right selects
the first/second; main/alternate attack selects the third/fourth. Release a
held button before pressing it. Candidates include registered addon bosses;
an exhausted pool displays `Unavailable` rather than looping indefinitely.

A confirmed choice creates a single-boss round with that boss and prioritizes
the winner as its player. The existing explicit `uh_sv_forcebossplayer1`
administrator override still takes precedence for player assignment. Queued
Strongman/Ultra bosses remain queued; normal boss history records the choice
at the existing commit point.

Timeout leaves the normal boss-selection flow and the existing winner player
queue in place. Disconnect clears the selection reward; spectating cancels the
countdown selector. If an administrator schedules consecutive bonus rounds,
the reward waits for an ordinary round (a subsequent winner replaces it).

The server rolls candidates and reads input. It sends option names and face
textures through `NamedSendNetworkString` to the winner; the CLIENTSIDE receiver
uses `k:` with `+moveleft`, `+moveright`, `+attack` and `+altattack` to display
that player's actual bindings (including two keys when bound). Unbound commands use
the engine's `??? (command)` fallback. The UI displays four horizontal cards with
32x32 boss mugshots, black backings (`MG_FBLK`), metallic/animated borders (`MG_OTL1S` /
`MG_OT1RR` for rare bosses), countdown timer, open audio cues, and a confirmation card.
There is no client NET request or cross-process ACS string-index payload.
World slot 122 retains the winning player slot plus one across maps. World
array 123 retains the confirmed `(player slot + 1, boss id)` through the LMS
FIGHT map/script reset; post-reset boss selection consumes it once and keeps
a map-local copy for player assignment. Candidates are map-local. A separate
owner field allows both boss id zero and negative custom ids. LOADACS is unchanged.

The initial port stored confirmation only in map variables. Zandronum's
`LASTMANSTANDING_DoFight` calls `GAME_ResetMap`, which reloads ACS modules and
clears those variables before boss selection, so the normal random picker ran.
The world-array handoff fixes that reset boundary.

A focused 2026-10-04 regression used the smoke package stack, one dedicated LMS
server, a spectator client (required for server ACS to tick) and two bots. A
temporary addon seeded a confirmed boss id 0 during countdown. Its map marker
changed from 47 to 0 across FIGHT, while owner 2 / boss 0 survived. The actual
post-reset pawn at TID 1001 was `TrueBusterExpert`, and the consumed owner was
0. This verifies the reset/morph handoff; it does not exercise the choice HUD
or physical key input. The probe addon is not part of the release PK3.

Manual runtime checks:

1. Win an FFA bonus round as a remote client. In the next countdown verify
   only the winner sees the four options with their own bindings (different
   from the server's), and each control selects its row.
2. Confirm a choice with multi-boss/combos enabled and an Ultra queued: the
   choice produces one boss, and the queued Ultra remains for a later round.
3. Let the selector time out; hold a control through spawning; disconnect or
   spectate before/after confirmation. Verify no unintended selection survives.
4. Finish with no survivor or multiple survivors, and verify no reward is
   issued. Repeat with an ordinary single-player win and player slot zero.
5. Register a custom boss in a supported pool, select it, and verify its morph
   and pick history. Force another bonus round and verify reward deferral.

The choice cards and confirmation use descending HudMessage IDs for their
portrait layers: black backing > mugshot > border. Zandronum draws lower IDs
in front, regardless of the order of HudMessage calls; reversing that order
causes the opaque black backing to hide the portrait.

## Debugging

Debug aliases are isolated in the dedicated lump `src/KEYCONF.debug` (keeping the main `src/KEYCONF` clean):

- `debug_bosschoice [seconds]` (or `pukename uh_debug_bosschoice [seconds]`):
  Immediately pops up the 4-card selection UI for the calling player with randomized candidates and full key-selection / confirmation feedback.
- `debug_grantbosschoice` (or `pukename uh_grant_bosschoice`):
  Grants the calling player the bonus winner reward for the next round's countdown.


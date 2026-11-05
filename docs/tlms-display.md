# TLMS-style display

This page describes the bottom ally/enemy counters and the ALLY icon above
teammates. Unholy uses these displays in ordinary LMS. The game mode
`LastManStanding` keeps its own rules.

## Why Unholy draws these displays

Unholy uses ordinary LMS and keeps its own side model. The engine uses engine
teams for its bottom counter and for its ally/enemy icons. Ordinary LMS has no
engine teams. Therefore:

- The engine counts every other player as an enemy. This count includes Unholy teammates.
- The engine never draws the ALLY icon.

Unholy therefore hides the engine counter and draws both displays from its own
relation. The teammate bar uses the same relation. The bar, the counters and the
markers always agree.

## Bottom counters

The bottom line uses the same text and colours as TLMS:

```
3 enemies 7 allies left
3 enemies left - allies dead
```

Rules:

- The counts exclude the viewer.
- The counts include only players in the round with a living role.
- A dead player, a dead spectator and a free slot do not count.
- A living camera player is the viewer. A spectator that follows a player uses
  the followed player's side.
- A true spectator, a dead spectator without a camera target and a body-less
  camera see no counters.
- The line appears only while the game is in progress.
- "Waiting for players" appears while the game waits for players.
- When the engine prints "Following - <name>", the counters move one line up.
- Free-for-all and an unknown policy report every other living player as an
  enemy. This matches the engine LMS count until the round policy arrives.

## ALLY icon

Each displayed teammate gets the native ALLY icon above the head. The icon is a
client-only sprite actor. It follows the head every frame and disappears on
death, role change, round end and map change.

The icon obeys these settings:

- `cl_icons` must be enabled.
- `cl_showallyicon` must not be `0` (never).
- The "ALLY Icons" user option must be enabled.

## User options

Both displays have their own switch in the Unholy user options menu, under
"Teammate Bar":

| Option | CVar | Default |
|--------|------|---------|
| TLMS Counters | `uh_cl_TlmsCounters` | on |
| ALLY Icons | `uh_cl_TlmsAllyIcons` | on |

The switches do not depend on the teammate bar switch. A player can hide the bar
and keep the counters and the markers.

## Limits

- The counters read the synchronized client display cache. A client that has not
  received the round snapshot yet sees `0 enemies 0 allies left`.
- The ALLY icon is a client-only actor. It does not replace the engine medal
  icons, chat bubbles or carrier icons.
- The display needs the MM8BDM assist display. Unholy registers its own entry
  there for the teammate bar. A mod that replaces that entry also removes these
  displays.

## Verification

```bash
python3 tools/check_team_visibility.py
python3 tools/gate.py --smoke
```

The first command runs the shared relation and the counter helpers under C
stubs. The second command compiles ACS and validates the PK3.

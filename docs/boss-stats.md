# Boss Win-Rate Statistics

Open-to-everyone debug counters for the ordinary Boss-vs-Survivors round.

The counters are server-owned runtime state. Any player can read them from the
game console; only the server host can clear them.

---

## What is recorded

A round is recorded only after its result is final:

- The Boss side wins when the survivor side is wiped (including the Zankokuna
  rage and Sakiko/Ave Mujica masquerade endings).
- The Boss side loses when the survivors are victorious.
- Every **distinct** Boss in the final committed line-up gets one result for
  that round. A multi-Boss combo therefore credits each member once, and a
  repeated member id in the same combo is still only counted once.
- Shadow Tricks credit the final revealed identity, not the disguise.
- The current-line-up query shows the committed line-up even for a Boss with
  no completed rounds yet (0W/0L).

The following are deliberately **not** recorded, because their win conditions
are different or no real fight happened:

- Bonus Events (their end callbacks own a different result model).
- Boss-vs-Boss versus duels.
- Administrative forfeits/declines (the Boss player left early), aborted
  selections, and map teardown exits.

The overall round counters are separate from the per-Boss counters, so the
overall Boss win rate is still one result per round even when a combo uses
several Bosses.

---

## Player access

Any connected player can run the console command:

```
uh_bossstats
```

or the underlying puke command:

```
pukename uh_BossStats [mode] [bossId]
```

Modes:

| Mode | Meaning |
|------|---------|
| `0` (default) | Overall summary plus every Boss with at least one completed round. |
| `1` | Overall summary only. |
| `2` | The current round's committed line-up (including 0W/0L rows). |
| `3` | One Boss by signed UHDT id; negative ids are custom addon Bosses. |

Example:

```
uh_bossstats
uh_bossstats_summary
uh_bossstats_lineup
uh_bossstats_boss 3
uh_bossstats_boss -1
```

Output uses plain `Log()` lines, not `Print()`: Zandronum's
`Print()` draws the red bar decoration around every line, which makes a
multi-line report hard to read. The server console/log gets every line; a
remote requester also receives each line through a CLIENTSIDE `Log()`
receiver, because server `Log()` is not sent to clients. Plain `----` text
lines mark the start and end of the report. A one-second server-wide cooldown
prevents command spam.

---

## Reset

The reset is a host-only mailbox command, because clients cannot edit server
state:

```
uh_bossstats_reset
```

It clears:

- per-Boss wins and losses (vanilla and custom),
- the recorded-round count and Boss-side win count,
- the per-round guard.

It intentionally **does not** clear the Boss pick history or the previous
line-up snapshot. Resetting debug data therefore does not change the least-seen
selection distribution.

The reset takes effect immediately, including during a round. A round that has
already been recorded stays cleared; the current round may be recorded once
after the reset if it has not finished yet.

---

## Lifetime

These counters use `world` storage, matching the Boss pick history:

- they survive map changes for the current server session;
- they reset when the server process restarts;
- `uh_bossstats_reset` clears them without a restart.

If long-term persistence across server restarts is needed, that is a separate
feature: the counts would have to be exported to a host-local string CVAR and
written with `writeini`, like the Boss override settings.

---

## Implementation notes

- Counters: `uh_bossstatswins`, `uh_bossstatswinscustom`,
  `uh_bossstatslosses`, `uh_bossstatslossescustom`,
  `uh_bossstatsrounds`, `uh_bossstatsbosswins` and
  `uh_bossstatsrecorded` in `unholy/uh_def.acs`.
- Accounting, display and reset: `unholy/uh_boss_stats.acs`.
- The recording calls live at the committed survivor-defeat path, the
  committed Boss-defeat path, and the two special Boss wipe endings.
- The host command is `statsreset` in the existing Boss command mailbox
  (`unholy/uh_boss_config.acs`).

# Boss Selection Settings

Configure boss selection behavior using server CVARs in the server console or `server.cfg`.

All settings are archived server CVARs. To write runtime changes to disk, run `writeini` directly in the server console.

---

## Server CVARs

| Server CVAR | Default | Permitted values | Description |
|-------------|---------|------------------|-------------|
| `uh_sv_bossselectmode` | 0 | 0, 1 | Selection strategy within pools: 0 = least-seen first; 1 = uniform random. |
| `uh_sv_bossavoidrepeat` | false | true, false | Excludes bosses from the previous committed round lineup. |
| `uh_sv_bossavoidduplicates` | false | true, false | Excludes bosses already recorded for the current round in multi-boss lineups. |
| `uh_sv_bossrarelimit` | 25 | 0 to 100 | Standard slot Rare pity threshold (0 pauses Rare and Shadow promotion). |
| `uh_sv_bossshadowchance` | 10 | 0 to 100 | Percent chance that a Rare promotion triggers a Shadow Trick. |
| `uh_sv_bossfullultrachance` | 5 | 0 to 100 | Full-pool conditional chance for Ultra tier. |
| `uh_sv_bossfullspecialchance` | 1 | 0 to 100 | Full-pool conditional chance for Special tier after Ultra check fails. |
| `uh_sv_bossfullexchance` | 15 | 0 to 100 | Full-pool conditional chance for EX tier after Ultra and Special checks fail. |
| `uh_sv_bossfullrarechance` | 30 | 0 to 100 | Full-pool conditional chance for Rare tier after Ultra, Special, and EX checks fail. |

---

## Selection rules

### Selection strategies (`uh_sv_bossselectmode`)

- `0` (Least-seen first, default): Prioritizes eligible bosses with the lowest appearance count in history. Resolves ties randomly with equal chance. In multi-boss rounds, bosses chosen in earlier slots of the same round receive a soft +1 count so selection spreads across equally-seen bosses.
- `1` (Uniform random): Ignores past appearance counts and selects across all eligible candidates in the target pool with equal weight. All boss candidates currently have weight 1.

### Standard vs Full-pool draws

Boss selection uses two distinct draw pathways:

#### Standard boss selection
- Used for ordinary unforced boss rounds.
- Draws exclusively from Common and Rare pools. Ultra, Special, and EX tiers never appear in standard rounds.
- Every standard boss slot increments the pity counter (`rarebosschance`).
- If `random(rarebosschance, uh_sv_bossrarelimit) >= uh_sv_bossrarelimit`, the slot promotes:
  - The server rolls `uh_sv_bossshadowchance` (default: 10%) for a Shadow Trick (which uses a Common boss disguise, then reveals a full-pool boss).
  - If the Shadow check fails, the slot promotes to `UHBOSS_POOL_RARE`.
  - The pity counter resets to 0.
- Setting `uh_sv_bossrarelimit 0` pauses Rare and Shadow promotions while preserving current pity progress. Re-enabling or lowering the ceiling clamps stored progress to the new threshold.

#### Full-pool selection
- Used only for explicit all-tier paths: `UHBOSS_FORCE_TRUE_RANDOM`, revealed bodies for Shadow Bosses, and all-tier boss events (e.g. event 100, versus).
- Evaluates tiers in sequential conditional order:
  1. Ultra roll: `uh_sv_bossfullultrachance` (default: 5%).
  2. If Ultra fails, Special roll: `uh_sv_bossfullspecialchance` (default: 1%).
  3. If Special fails, EX roll: `uh_sv_bossfullexchance` (default: 15%).
  4. If EX fails, Rare roll: `uh_sv_bossfullrarechance` (default: 30%).
  5. If all fail, selects Common tier.
- If the selected tier has no eligible candidates, selection falls back to Common, then to safe defined boss 0.

---

## Lineup exclusions and fallbacks

- **Previous round lineup (`uh_sv_bossavoidrepeat`)**: Snapshots the final committed lineup from the previous round at round start. When set to `true`, bosses in that snapshot are excluded from random selection.
- **Current round duplicates (`uh_sv_bossavoidduplicates`)**: When set to `true`, excludes bosses already recorded for the current round across multi-boss slots. For Shadow Bosses, this reserves the initial disguise body during selection.
- **Empty-pool relaxation**: If `uh_sv_bossavoidrepeat` or `uh_sv_bossavoidduplicates` empties the eligible candidate pool, the server retries the draw without these optional restrictions. Mandatory exclusions requested by the caller (such as versus mode opponents) are never relaxed.

---

## Selection priority

Selection policies apply only to random pool picks. They do not override or alter:

- Admin forced boss CVARs (`uh_sv_forcedboss1` through `uh_sv_forcedboss5`)
- Strongman queue activations
- Round-winner boss selection or reassignment
- Fixed Boss Combo member slots

---

## Configuration examples

### Default configuration

```cfg
// Default boss selection
uh_sv_bossselectmode 0
uh_sv_bossavoidrepeat false
uh_sv_bossavoidduplicates false
uh_sv_bossrarelimit 25
uh_sv_bossshadowchance 10
uh_sv_bossfullultrachance 5
uh_sv_bossfullspecialchance 1
uh_sv_bossfullexchance 15
uh_sv_bossfullrarechance 30
```

### Strict non-repeating configuration

```cfg
// Prevent back-to-back repeats and duplicate multi-bosses
uh_sv_bossavoidrepeat true
uh_sv_bossavoidduplicates true
```

### Uniform random configuration

```cfg
// Uniform random selection ignoring appearance history
uh_sv_bossselectmode 1
```

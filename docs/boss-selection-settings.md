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

---

## Per-boss overrides

> [!IMPORTANT]
> **Implementation status:** This phase implements data storage, host commands, and input validation. Stored override values **do not affect boss selection algorithms yet**. Integration with pool filtering and weights will follow in the next release phase.

Server operators can define rules for individual boss actors.

### Actor keys and storage format

- **Actor name key:** Overrides are keyed by actor class name (1 to 127 characters; letters, digits, underscores, hyphens, and periods).
- **Case-insensitive:** Actor lookups ignore letter case (`gembanker` matches `GemBanker`).
- **Pending addons:** Overrides can be defined before an addon boss is loaded. Rules remain stored and pending until the matching actor registers.
- **Storage format:** Stored in the archived string CVAR `uh_sv_bossrules` as:
  `actor:mode,weight,minplayers,maxplayers;`
  A value of `-1` denotes inheritance from registered defaults.
- **Storage capacity:** Supports up to 256 boss records (up to 16,384 characters). Commands process sequentially through the server queue.

### Override fields

| Field | Values | Description |
|-------|--------|-------------|
| `mode` | `inherit`, `random`, `forced`, `disabled` | Availability mode for selection (`inherit` restores registered default). |
| `weight` | `inherit` (-1), 1 to 1000000 | Relative selection weight within the boss pool. |
| `minplayers` | `inherit` (-1), 0 to 64 | Minimum player count (0 removes lower limit). |
| `maxplayers` | `inherit` (-1), 0 to 64 | Maximum player count (0 removes upper limit; must be $\ge$ minplayers if non-zero). |

#### Modes
- **`random`**: Eligible for random pool selection.
- **`forced`**: Excluded from random selection. Can still be triggered manually or via script queues.
- **`disabled`**: Fully disabled from random and forced selection.
- **`inherit`**: Inherits the registration default mode.

### Console commands

| Command | Description |
|---------|-------------|
| `uh_boss_set <actor> <field> <value>` | Sets an override field for a boss actor. Accepts `inherit` for any field. |
| `uh_boss_show <actor>` | Displays stored overrides, registration status, and enabled state. |
| `uh_boss_reset <actor> [field]` | Resets a specific field or clears the entire override record for the actor. |
| `uh_boss_list` | Lists all stored boss overrides. |
| `uh_boss_export` | Prints the current `uh_sv_bossrules` string to copy into `server.cfg`. |
| `uh_boss_reload` | Re-parses the current `uh_sv_bossrules` CVAR string. |
| `uh_boss_save` | Waits for queued commands to finish, then prompts to run `writeini`. |
| `uh_boss_load <path>` | Prints instructions to run `exec <path>`, then `uh_boss_reload`. |

> [!NOTE]
> The game engine prevents KEYCONF aliases from running `writeini` or `exec`. Run `writeini` directly in the server console after `uh_boss_save` confirms queued edits. To load a script, run `exec <path>` directly in the console, then run `uh_boss_reload`.

#### Usage examples

```cfg
// Set boss overrides
uh_boss_set GemBanker mode random
uh_boss_set GemBanker weight 2
uh_boss_set GemBanker minplayers 8
uh_boss_set Fireman mode disabled

// Inspect stored overrides
uh_boss_show GemBanker
uh_boss_list

// Reset overrides
uh_boss_reset GemBanker weight
uh_boss_reset Fireman

// Save configuration to disk
uh_boss_save  // Wait for the prompt: "Boss edits are complete. Run writeini directly in the server console to save."
writeini      // Execute directly in the server console

// Load configuration from file
exec examples/boss_overrides.cfg  // Execute directly in the server console
uh_boss_reload                    // Reload and apply the updated CVAR rules
```

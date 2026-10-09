# Boss Selection Settings

Configure boss selection behavior using server CVARs in the server console or `server.cfg`.

All settings are archived server CVARs. To write runtime changes to disk, run `writeini` directly in the server console.

---

## Server CVARs

| Server CVAR | Default | Permitted values | Description |
|-------------|---------|------------------|-------------|
| `uh_sv_bossselectmode` | 0 | 0, 1 | Selection strategy within pools: 0 = least-seen with weighted ties; 1 = weighted random. |
| `uh_sv_bossavoidrepeat` | false | true, false | Excludes bosses from the previous committed round lineup. |
| `uh_sv_bossavoidduplicates` | false | true, false | Excludes bosses already recorded for the current round in multi-boss lineups. |
| `uh_sv_bossforcedplayerlimits` | false | true, false | Enforces effective player limits on specified requests (admin forced, Strongman, winner choices). |
| `uh_sv_bossrarelimit` | 25 | 0 to 100 | Standard slot Rare pity threshold (0 pauses Rare and Shadow promotion). |
| `uh_sv_bossshadowchance` | 10 | 0 to 100 | Percent chance that a Rare promotion triggers a Shadow Trick. |
| `uh_sv_bossfullultrachance` | 5 | 0 to 100 | Full-pool conditional chance for Ultra tier. |
| `uh_sv_bossfullspecialchance` | 1 | 0 to 100 | Full-pool conditional chance for Special tier after Ultra check fails. |
| `uh_sv_bossfullexchance` | 15 | 0 to 100 | Full-pool conditional chance for EX tier after Ultra and Special checks fail. |
| `uh_sv_bossfullrarechance` | 30 | 0 to 100 | Full-pool conditional chance for Rare tier after Ultra, Special, and EX checks fail. |

---

## Selection rules

### Selection strategies (`uh_sv_bossselectmode`)

- `0` (Least-seen with weighted ties, default): Finds eligible bosses with the lowest appearance count in history. When multiple candidates share the lowest count, resolves ties using their relative weights (`weight`). In multi-boss rounds, bosses chosen in earlier slots of the same round receive a soft +1 count so selection spreads across equally-seen bosses.
- `1` (Weighted random): Selects across all eligible candidates in the target pool using their relative weights, regardless of appearance history.

In both strategies, the default weight is 1.

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
- If the selected tier has no eligible candidates, selection falls back to an eligible Common boss.

### Lineup exclusions and fallbacks

- **Previous round lineup (`uh_sv_bossavoidrepeat`)**: Snapshots the final committed lineup from the previous round at round start. When set to `true`, bosses in that snapshot are excluded from random selection.
- **Current round duplicates (`uh_sv_bossavoidduplicates`)**: When set to `true`, excludes bosses already recorded for the current round across multi-boss slots. For Shadow Bosses, this reserves the initial disguise body during selection.
- **Empty-pool relaxation**: If `uh_sv_bossavoidrepeat` or `uh_sv_bossavoidduplicates` leaves no eligible candidates, the server retries without these optional repeat restrictions. Player limits and mode restrictions are never relaxed. Mandatory exclusions requested by the caller (such as versus mode opponents) are never relaxed.
- **Empty pool abort**: If no eligible boss exists after fallback (e.g. all candidates disabled or outside player limits), the round aborts immediately without selecting a boss or granting win streak rewards. The game does not select boss 0.

---

## Specified boss requests and limits

Specified boss requests include:
- Admin forced boss CVARs (`uh_sv_forcedboss1` through `uh_sv_forcedboss5`)
- Admin forced Shadow CVARs (`uh_sv_forcedshadowboss1` through `uh_sv_forcedshadowboss5`)
- Strongman and Ultra queue activations
- Round-winner boss selection options

### Specified rules

- **Disabled mode (`mode disabled`)**: Always blocks the boss from specified requests and random draws.
- **Player limits (`uh_sv_bossforcedplayerlimits`)**:
  - `false` (default): Specified requests bypass player count limits.
  - `true`: Specified requests must meet the boss's effective `minplayers` and `maxplayers` range. Non-qualifying requests are rejected.
- **Rejection behavior**:
  - Rejected admin forced requests log a warning and fall back to ordinary unforced selection.
  - Rejected Strongman entries are removed from the queue and log a warning; selection checks the next queue entry or proceeds normally.
  - Rejected round-winner choices log a warning and fall back to ordinary unforced selection.
  - Rejected Shadow forced choices fall back to random reveal selection.
- **Boss Combos**: Fixed Boss Combo member slots use independent combo rules and registry definitions. Configured per-boss rules and `uh_sv_bossforcedplayerlimits` do not alter Boss Combo members.

---

## Per-boss overrides

Server operators can define overrides for individual boss actors. Overrides actively govern random pool filtering, selection weights, and player count limits.

### Actor keys and storage format

- **Actor name key:** Overrides are keyed by actor class name (1 to 127 characters; letters, digits, underscores, hyphens, and periods).
- **Case-insensitive:** Actor lookups ignore letter case (`gembanker` matches `GemBanker`).
- **Pending addons:** Overrides can be defined before an addon boss is loaded. Rules remain stored and pending until the matching actor registers.
- **Storage format:** Stored in the host-archived string CVAR `uh_sv_bossrules` as:
  `actor:mode,weight,minplayers,maxplayers;`
  A value of `-1` denotes inheritance from registered defaults.
- **Host-local storage:** `uh_sv_bossrules` is archived locally on the server host (`local string`) rather than broadcast over the network. This avoids Zandronum's 2,048-byte limit on server string replication, preventing client disconnects when large override datasets are saved. The server retains the full 16,384 character capacity (up to 256 boss records).

### Override fields

| Field | Values | Description |
|-------|--------|-------------|
| `mode` | `inherit`, `random`, `forced`, `disabled` | Availability mode for selection (`inherit` restores registered default). |
| `weight` | `inherit` (-1), 1 to 1000000 | Relative selection weight within the boss pool (default: 1). |
| `minplayers` | `inherit` (-1), 0 to 64 | Minimum player count (0 removes lower limit). |
| `maxplayers` | `inherit` (-1), 0 to 64 | Maximum player count (0 removes upper limit; must be $\ge$ minplayers if non-zero). |

#### Modes
- **`random`**: Eligible for random pool selection. Requires membership in a rarity pool. Overriding `mode random` on a boss without a rarity pool does not make it randomly selectable. An override cannot enable a boss disabled in the registry.
- **`forced`**: Excluded from random selection. Can still be triggered manually or via script queues.
- **`disabled`**: Fully disabled from random selection, forced CVARs, Strongman, and winner options.
- **`inherit`**: Inherits the registration default mode.

### Console commands

| Command | Description |
|---------|-------------|
| `uh_boss_set <actor> <field> <value>` | Sets an override field for a boss actor. Accepts `inherit` for any field. |
| `uh_boss_show <actor>` | Displays stored overrides, effective values, registration status, and eligibility. |
| `uh_boss_check <actor>` | Runs read-only diagnostics on eligibility, history counts, weights, and blocking reasons. |
| `uh_boss_pool [tier]` | Displays the candidate pool snapshot, history counts, weights, and fallback status for a tier. |
| `uh_boss_reset <actor> [field]` | Resets a specific field or clears the entire override record for the actor. |
| `uh_boss_list` | Lists all stored boss overrides and record count. |
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
uh_boss_set GemBanker weight 3
uh_boss_set GemBanker minplayers 8
uh_boss_set Fireman mode disabled

// Inspect stored and effective settings
uh_boss_show GemBanker
uh_boss_list

// Run read-only diagnostics (does not consume RNG or requests)
uh_boss_check GemBanker
uh_boss_pool common
uh_boss_pool all

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

---

## Diagnostics

Use read-only diagnostic commands to inspect boss eligibility and candidate pools without modifying game state:

| Command | Description |
|---------|-------------|
| `uh_boss_check <actor>` | Shows detailed diagnostic status for a boss actor. |
| `uh_boss_pool [tier]` | Shows the candidate draw pool for a specific tier or all tiers. |

### Diagnostic rules

- **Read-only execution:** Diagnostic commands do not roll random numbers, consume admin forced requests, advance appearance history, or alter world arrays.
- **Current state snapshot:** Queries report the state at the moment of execution. They do not predict future rounds. Final selections can be overridden by admin requests, Ultra pity hits, winner choices, or Boss Combos.
- **Tier argument (`uh_boss_pool [tier]`)**:
  - Defaults to `all` (or 0) to display all tiers.
  - Accepts tier names or numbers: `common` (1), `rare` (2), `special` (3), `ultra` (4), `ex` (5).
- **Diagnostic output fields**:
  - **Eligibility**: Reports whether the boss is eligible for random selection under current player count and mode settings.
  - **Player limits**: Reports minimum and maximum player thresholds and whether the current player count satisfies them.
  - **History and delta**: Displays permanent appearance count and the current round's count delta.
  - **Exclusions**: Identifies whether the boss is blocked by previous-lineup repeat avoidance (`uh_sv_bossavoidrepeat`) or same-round duplicate avoidance (`uh_sv_bossavoidduplicates`).
  - **Lowest-count candidacy**: In least-seen mode (`uh_sv_bossselectmode 0`), shows whether the boss belongs to the minimum appearance count group.
  - **Weights**: Shows relative selection weights and total pool weight.
  - **Empty-pool relaxation and fallbacks**: Indicates when optional repeat exclusions relax, or when fallback to Common occurs.

---

## Configuration examples

### Default configuration

```cfg
// Default boss selection
uh_sv_bossselectmode 0
uh_sv_bossavoidrepeat false
uh_sv_bossavoidduplicates false
uh_sv_bossforcedplayerlimits false
uh_sv_bossrarelimit 25
uh_sv_bossshadowchance 10
uh_sv_bossfullultrachance 5
uh_sv_bossfullspecialchance 1
uh_sv_bossfullexchance 15
uh_sv_bossfullrarechance 30
```

### Strict non-repeating and player-limited configuration

```cfg
// Prevent repeats, duplicates, and enforce player limits on forced bosses
uh_sv_bossavoidrepeat true
uh_sv_bossavoidduplicates true
uh_sv_bossforcedplayerlimits true
```

### Weighted random configuration

```cfg
// Weighted random selection across all eligible bosses
uh_sv_bossselectmode 1
```

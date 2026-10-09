# Bonus Event Settings

Configure event options in **Unholy Menu** -> **Server Options** -> **Events**, or enter CVARs and commands in the server console.

## Global settings

### Player minimum

| Server CVAR | Menu label | Default | Permitted values |
|-------------|------------|---------|------------------|
| `uh_sv_bonusminplayers` | **High-Player Minimum (0-64)** | 12 | 0 to 64 |

This setting controls the player requirement for these base events:

- Demoneye Parade
- Clone Darkness
- Brick Eyes
- Mosquito Eyes

A value of 0 disables the global player minimum.
An event override (`minplayers`) replaces this global minimum for that specific event.
Other base events and addon events keep their registered player limits unless overridden.
By default, forced selections ignore player limits (see `uh_sv_bonusforcedplayerlimits`).

### EX count

| Server CVAR | Menu label | Default | Permitted values |
|-------------|------------|---------|------------------|
| `uh_sv_bonusexcount` | **Normal Picks Before EX (0-100)** | 3 | 0 to 100 |

This setting controls these base/EX event pairs:

| Base event | EX event |
|------------|----------|
| Free for All | True Power FFA |
| Demoneye Parade | Get that Furry |
| Clone Darkness | Angry Foxeye |
| Football FFA | Rune FFA |
| Boss FFA | Satan Seal FFA |

- **Upgrade threshold:** A setting of $N$ (default: 3) triggers an upgrade after $N$ random selections of the base event. The $(N+1)$-th selection runs the EX event and resets the count to 0.
- **Disabling upgrades:** A setting of 0 disables upgrades while preserving current progress. Setting a positive value resumes counting from the saved value.
- **Threshold change:** Lowering the threshold causes an immediate upgrade on the next selection if the current count meets or exceeds the new value.
- **Forced events:** Forced selections do not advance the EX count.
- **Addon events:** Addon event pairs keep their registered EX thresholds unless overridden.

### Global console commands

Set the CVARs in the server console or `server.cfg`:

```cfg
uh_sv_bonusminplayers 12  // Default: 12 (0-64; 0 disables the minimum)
uh_sv_bonusexcount 3      // Default: 3  (0-100; 0 disables EX upgrades)
```

Values outside the permitted range are automatically clamped to the nearest limit.

To force an event, select it from **Force Bonus Event** in the menu, or enter `uh_sv_bonuseventnum <id>` (supports both built-in IDs and addon IDs).

---

## Selection policies

Configure event selection behavior with these server CVARs:

| Server CVAR | Default | Permitted values | Description |
|-------------|---------|------------------|-------------|
| `uh_sv_bonusselectmode` | 0 | 0, 1 | Selection strategy: 0 = least-seen first; 1 = pure weighted random. |
| `uh_sv_bonusavoidrepeat` | true | true, false | true = excludes the previous event first; false = allows immediate repeat. |
| `uh_sv_bonusforcedplayerlimits` | false | true, false | true = enforces effective player limits on forced events. |
| `uh_sv_bonusexplayerlimits` | false | true, false | true = pauses EX upgrades if the EX target player limits are not met. |

### Policy rules

- **Player limits:** Effective player limits resolve registered defaults, `uh_sv_bonusminplayers`, and per-event overrides (`minplayers`, `maxplayers`).
- **Selection modes:**
  - `0` (Least-seen first): Selects eligible events with the lowest appearance count first. Resolves ties using relative weights.
  - `1` (Weighted random): Selects across all eligible events using relative weights, regardless of appearance history.
- **Repeat avoidance:** When `uh_sv_bonusavoidrepeat` is true, the server excludes the previous event from the candidate pool. If no other eligible events remain, the server retries with the previous event included.
- **Forced event limits:** When `uh_sv_bonusforcedplayerlimits` is true, forced requests outside player limits are rejected with a console warning. The server consumes the request and evaluates the next priority request (`uh_sv_bonuseventnum` takes priority over queued requests). If no forced request qualifies, random selection continues.
- **EX player limits:** When `uh_sv_bonusexplayerlimits` is true and the EX target fails player limits, the base event runs instead. The server preserves partial and completed EX progress without advancing or resetting the count.
- **State and timing:** Policy changes take effect on the next selection. In-progress rounds do not re-evaluate. Policy changes do not reset event history or EX progress.
- **Empty pool fallback:** If no event meets random eligibility conditions, the server runs a standard boss round.
- **Policy inspection:** Use `uh_event_policy` to print active policy values. `uh_event_list` and menu configuration output also display them.
- **Storage:** Policy CVARs are engine CVARs (saved in `server.cfg` or via `uh_event_save`). They do not appear in menus and are not written to `uh_sv_eventrules`.

### Policy configuration examples

```cfg
// Default policy: least-seen first, avoid immediate repeats
uh_sv_bonusselectmode 0
uh_sv_bonusavoidrepeat true
uh_sv_bonusforcedplayerlimits false
uh_sv_bonusexplayerlimits false

// Pure weighted random: ignore history, allow immediate repeats
uh_sv_bonusselectmode 1
uh_sv_bonusavoidrepeat false
```

---

## Per-event overrides

Server operators can override rules for individual events by stem name (e.g. `boss_ffa`). Overrides take precedence over global settings and registration defaults.

Use `uh_event_list` (or **Print Event Settings** in the menu) to view all registered stems, active settings, and selection policies.

### Override fields

| Field | Values | Description |
|-------|--------|-------------|
| `mode` | `random`, `forced`, `disabled` | Availability mode for event selection. |
| `weight` | 1 to 1000000 | Relative selection weight among events with the same appearance count. |
| `minplayers` | 0 to 64 | Minimum player count (0 removes limit). Overrides `uh_sv_bonusminplayers`. |
| `maxplayers` | 0 to 64 | Maximum player count (0 removes limit). Must be $\ge$ minplayers if non-zero. |
| `ex_count` | 0 to 100 | Picks before EX upgrade (0 pauses upgrades). Overrides `uh_sv_bonusexcount`. |
| `ex_target` | event stem | Target event stem for EX upgrade. Changing target resets EX progress to 0. |

#### Modes
- **`random`**: Eligible for random selection. Former EX-only events use weight 1 by default unless set.
- **`forced`**: Excluded from direct random selection. Can still be triggered manually or as an EX upgrade.
- **`disabled`**: Fully disabled. Cannot be randomly selected, forced, or upgraded.

By default, forced and EX selections ignore player limits. Enable `uh_sv_bonusforcedplayerlimits` or `uh_sv_bonusexplayerlimits` to enforce limits on them.
Changing `ex_count` preserves existing EX progress.
If no random event meets the selection conditions, the game proceeds with a normal boss round.

### Console commands

| Command | Description |
|---------|-------------|
| `uh_event_set <stem> <field> <value>` | Sets an override field for an event. |
| `uh_event_show <stem>` | Displays active settings, sources, and EX progress on server console. |
| `uh_event_list` | Lists all registered events, active overrides, and selection policies. |
| `uh_event_policy` | Displays active selection policy CVARs. |
| `uh_event_reset <stem> [field]` | Clears overrides for a specific field or the entire event. |
| `uh_sv_eventrules ""` | Clears all overrides across all events. |
| `uh_event_save` | Flushes pending commands and writes configuration to disk (`writeini`). |
| `uh_event_export` | Prints a single `uh_sv_eventrules` line to copy into `server.cfg`. |
| `uh_event_load <path>` | Executes a command file (e.g. `examples/bonus_event_settings/host.cfg`). |
| `uh_event_reload` | Re-parses the current `uh_sv_eventrules` CVAR string. |

#### Usage examples

```cfg
// Set specific event overrides
uh_event_set boss_ffa ex_count 5
uh_event_set boss_ffa ex_target satan_seal_ffa
uh_event_set football_ffa ex_count 0
uh_event_set demoneye_parade minplayers 8
uh_event_set brick_eyes mode forced

// Inspect settings
uh_event_show boss_ffa
uh_event_policy
uh_event_list

// Reset overrides
uh_event_reset boss_ffa ex_count
uh_event_reset boss_ffa ex_target
uh_event_reset demoneye_parade minplayers
uh_sv_eventrules ""  // Clear all overrides
```

### Persistence and Addons

- **Storage format:** Overrides are stored in the archived string CVAR `uh_sv_eventrules` as:
  `stem:mode,weight,minplayers,maxplayers,ex_count,ex_target;`
  A value of `-1` or an empty `ex_target` denotes inheritance. Legacy 4-field formats are automatically supported.
- **Addon support:** Overrides can be defined before an addon event is registered. Settings remain pending until an event matching the stem is loaded.
- **Storage capacity:** Supports up to 256 event records (up to 16,384 characters). Commands process one per game tic, with a queue limit of 256 commands per batch.

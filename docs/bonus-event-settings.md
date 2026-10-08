# Bonus Event Settings

Configure global settings in **Unholy Menu** -> **Server Options** -> **Events**, or enter CVARs and commands in the server console.

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

A value of 0 disables the player minimum.
An event override (`minplayers`) replaces this global minimum for that specific event.
Other base events and addon events keep their registered player limits unless overridden.
Forced selections (via **Force Bonus Event** or `uh_sv_bonuseventnum`) ignore player limits.

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

- **Upgrade rule:** A setting of $N$ (default: 3) requires $N$ random selections of a base event before upgrading. The next selection becomes the EX event, and its count resets to 0. Selections of other events do not change this count.
- **Disable upgrades:** A setting of 0 disables EX upgrades while preserving existing counts. Setting a positive value resumes counting from the saved count.
- **Threshold change:** Lowering the setting causes an immediate upgrade on the next selection if the current count is equal to or greater than the new value.
- **Forced events:** Forced selections do not advance the EX count.
- **Addon events:** Addon event pairs keep their registered EX thresholds.

### Global console commands

Set the CVARs in the server console or `server.cfg`:

```cfg
uh_sv_bonusminplayers 12  // Default: 12 (0-64; 0 disables the minimum)
uh_sv_bonusexcount 3      // Default: 3  (0-100; 0 disables EX upgrades)
```

Values outside the permitted range are automatically clamped to the nearest limit.

To force an event, select it from **Force Bonus Event** in the menu, or enter `uh_sv_bonuseventnum <id>` (supports both built-in IDs and addon IDs).

---

## Per-event overrides

Server operators can override rules for individual events by stem name (e.g. `boss_ffa`). Overrides take precedence over global settings and registration defaults.

Use `uh_event_list` (or **Print Event Settings** in the menu) to view all registered stems and their active settings.

### Override fields

| Field | Values | Description |
|-------|--------|-------------|
| `mode` | `random`, `forced`, `disabled` | Availability mode for event selection. |
| `weight` | 1 to 1000000 | Relative selection weight among events with the same appearance count. |
| `minplayers` | 0 to 64 | Minimum player count (0 removes limit). Overrides `uh_sv_bonusminplayers`. |
| `maxplayers` | 0 to 64 | Maximum player count (0 removes limit). Must be $\ge$ minplayers if non-zero. |

#### Modes
- **`random`**: Eligible for random selection. Former EX-only events use weight 1 by default unless set.
- **`forced`**: Excluded from direct random selection. Can still be triggered manually or as an EX upgrade.
- **`disabled`**: Fully disabled. Cannot be randomly selected, forced, or upgraded.

Player limits apply to random selection only; forced and EX selections ignore player limits.
If no random event meets the selection conditions, the game proceeds with a normal boss round.

### Console commands

| Command | Description |
|---------|-------------|
| `uh_event_set <stem> <field> <value>` | Sets an override field for an event. |
| `uh_event_show <stem>` | Displays active settings and their sources for an event. |
| `uh_event_list` | Lists all registered events and active overrides in console. |
| `uh_event_reset <stem> [field]` | Clears overrides for a specific field or the entire event. |
| `uh_sv_eventrules ""` | Clears all overrides across all events. |
| `uh_event_save` | Flushes pending commands and writes configuration to disk (`writeini`). |
| `uh_event_export` | Prints a single `uh_sv_eventrules` line to copy into `server.cfg`. |
| `uh_event_load <path>` | Executes a command file (e.g. `examples/bonus_event_settings/host.cfg`). |
| `uh_event_reload` | Re-parses the current `uh_sv_eventrules` CVAR string. |

#### Usage examples

```cfg
// Set specific event overrides
uh_event_set demoneye_parade minplayers 8
uh_event_set boss_ffa weight 2
uh_event_set brick_eyes mode forced

// Inspect settings
uh_event_show boss_ffa
uh_event_list

// Reset overrides
uh_event_reset demoneye_parade minplayers  // Reset single field
uh_event_reset boss_ffa                    // Reset all fields for event
uh_sv_eventrules ""                        // Clear all overrides
```

### Persistence and Addons

- **Persistence:** Overrides are stored in the archived string CVAR `uh_sv_eventrules` and persist across map changes.
- **Addon support:** Overrides can be defined before an addon event is registered. Settings remain pending until an event matching the stem is loaded.
- **Storage capacity:** Supports up to 256 event records (up to 16,384 characters). Commands process one per game tic, with a queue limit of 256 commands per batch.

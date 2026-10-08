# Bonus Event Settings

Configure these settings in **Unholy Menu** -> **Server Options** -> **Events**, or enter the CVAR commands in the server console.

## Player minimum

| Server CVAR | Menu label | Default | Permitted values |
|-------------|------------|---------|------------------|
| `uh_sv_bonusminplayers` | **High-Player Minimum (0-64)** | 12 | 0 to 64 |

This setting controls the player requirement for these base events:

- Demoneye Parade
- Clone Darkness
- Brick Eyes
- Mosquito Eyes

A value of 0 disables the player minimum.
Other base events and addon events keep their registered player limits.
Forced selections (via **Force Bonus Event** or `uh_sv_bonuseventnum`) ignore player limits.

## EX count

| Server CVAR | Menu label | Default | Permitted values |
|-------------|------------|---------|------------------|
| `uh_sv_bonusexcount` | **Normal Picks Before EX (0-100)** | 3 | 0 to 100 |

This setting controls these event pairs:

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

## Console commands

Set the CVARs in the server console or `server.cfg`:

```cfg
uh_sv_bonusminplayers 12  // Default: 12 (0-64; 0 disables the minimum)
uh_sv_bonusexcount 3      // Default: 3  (0-100; 0 disables EX upgrades)
```

Values outside the permitted range are automatically clamped to the nearest limit.

To force an event, select it from **Force Bonus Event** in the menu, or enter `uh_sv_bonuseventnum <id>` (supports both built-in IDs and addon IDs).

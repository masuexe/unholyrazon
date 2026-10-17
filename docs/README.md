# Unholy Razon Documentation Index

This directory contains technical references, modder API specifications, and server host guides for **Unholy Razon**.

---

## 1. Modder APIs

Unholy Razon provides extensible ACS APIs via [`src/acs_source/_includes/mod_api/uhadd.acs`](../src/acs_source/_includes/mod_api/uhadd.acs). These interfaces allow addon packages to register custom entities and gameplay events without modifying core mod files.

| Document | Description |
|---|---|
| [**Boss API**](boss-api.md) | Define custom boss classes (`DefineBoss`), player-count HP scaling, rage alerts, morph setup scripts, and custom music. |
| [**Survivor & Class API**](survivor-api.md) | Register custom player survivor classes (`DefineSurvivor`), KEYCONF setup, automatic weapon stripping (`DefineSurvivorWep`), multi-weapon registration, and shiny variants. |
| [**Bonus Event API**](bonus-event-api.md) | Define custom gamemode rounds (`DefineBonusEvent`), FFA/One-vs-All flags, round lifecycle callbacks (`start`/`rebuild`/`end`), and EX progression. |
| [**Boss Combo API**](boss-combo-api.md) | Configure multi-boss lineups (`DefineBossCombo`), cooperative rosters, boss versus duels, and Shadow mode sequences. |
| [**LMS Event API**](lms-event-api.md) | Register last survivor reward events (`DefineLMSEvent`), item drops, and Bad LMS penalties. |
| [**Demoneye & Eye Morph Pool API**](demoneye-api.md) | Register custom Demoneyes (`DefineDemoneye`) and configure weighted transformation pools (`DefineEyeMorphPool`) for Money Bait and Money Bombs. |
| [**Boss Stage Portraits**](boss-phase-portraits.md) | Register dynamic multi-phase mugshots and HUD icons based on inventory triggers (`DefineTeamPhasePresentation`). |

---

## 2. Server Administration & Host Guides

Guides and CVAR references for dedicated server operators and host setups.

| Document | Description |
|---|---|
| [**Server Gameplay CVARs**](server-gameplay-cvars.md) | Centralized reference for round thresholds, copy weapon counts, SinfulBusterExpert unlocks, bonus stage death effects, and Zangief pull toggles. |
| [**Boss Selection Settings**](boss-selection-settings.md) | Host commands (`uh_boss_set`, `uh_boss_show`, `uh_boss_export`), per-boss rule overrides (`uh_sv_bossrules`), selection strategies, and tier probabilities. |
| [**Boss Win-Rate Statistics**](boss-stats.md) | Open-to-everyone debug counters (`uh_bossstats`), counting rules, session scope, and the host-only reset. |
| [**Bonus Event Settings**](bonus-event-settings.md) | Host commands (`uh_event_set`, `uh_event_show`, `uh_event_export`), per-event rules (`uh_sv_eventrules`), player thresholds, and EX counters. |
| [**Round Settlement**](round-settlement.md) | Server option `uh_sv_resumeonrevive`, cancellable exit windows, and mid-settlement revival rules. |
| [**MegaMan Daily Weapons**](megaman-daily-weapons.md) | Server CVARs for MegaMan M2 weapon pool size and daily weapon synchronization. |
| [**AFK Penalties**](afk-penalties.md) | Server AFK detection rules, punishment items (Fire, GUHU, Money Bait, Money Bomb), and delay thresholds. |

---

## 3. Mechanics & Gameplay References

| Document | Description |
|---|---|
| [**Class Specific Mechanics**](class-mechanics.md) | In-depth combat mechanics and control references for specialized classes (Zangief charge pull, Star Force Mega Man Battle Cards, and Eden Isaac item artifacts). |
| [**Bonus Boss Choice**](bonus-boss-choice.md) | Rules and timing for winner boss selection during bonus events. |

---

## 4. Internal Contracts & Architecture

Architecture specifications and data contracts for internal Unholy core subsystems.

| Document | Description |
|---|---|
| [**Custom HUD Bars**](custom-bars.md) | Data-driven HUD bar compiler (`bars.toml` + `tools/_gen_barpos.py`), multi-bank positions, sparse layer priorities, SBARINFO generation, and unified clearing. |
| [**UHDT Identity CRUD Contract**](modding/uhdt-identity-crud-contract.md) | Internal lifecycle, tombstone rules, and IPC contracts for UHDT identity tables. |
| [**UHDT Music Row Contract**](modding/uhdt-music-row-contract.md) | Internal lifecycle, capacity, and pick logic for shared boss and event music tables. |

---

## 5. Working Addon Examples

Refer to [`examples/`](../examples/) for fully functional, minimal PK3 addon packages demonstrating each API:

- [`examples/defineboss_addon/`](../examples/defineboss_addon/) — Custom boss registration with morph setup and music.
- [`examples/definesurvivor_addon/`](../examples/definesurvivor_addon/) — Custom survivor class with teammate bar presentation.
- [`examples/eyemorph_addon/`](../examples/eyemorph_addon/) — Custom Demoneye and private weighted eye-morph pool.
- [`examples/lms_penalty_addon/`](../examples/lms_penalty_addon/) — Custom last-survivor LMS event with Bad LMS penalties.
- [`examples/teampresentation_addon/`](../examples/teampresentation_addon/) — Dedicated teammate bar, UIX, and scoreboard presentation row.
- [`examples/deathtips_addon/`](../examples/deathtips_addon/) — Client-side death tip registry.
- [`examples/shinywep_addon/`](../examples/shinywep_addon/) — Shiny move-weapon override registration.
- [`examples/bonus_event_settings/`](../examples/bonus_event_settings/) — Host configuration export and import sample.

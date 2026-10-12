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
| [**Boss Selection Settings**](boss-selection-settings.md) | Host commands (`uh_boss_set`, `uh_boss_show`, `uh_boss_export`), per-boss rule overrides (`uh_sv_bossrules`), selection strategies, and tier probabilities. |
| [**Bonus Event Settings**](bonus-event-settings.md) | Host commands (`uh_event_set`, `uh_event_show`, `uh_event_export`), per-event rules (`uh_sv_eventrules`), player thresholds, and EX counters. |
| [**Round Thresholds**](round-thresholds.md) | Host settings for win/loss streak mercy, Hell Mark, Speciman kills, Gauntlet rewards, and Bad LMS thresholds. |
| [**Copy Weapon Start Counts**](copy-weapon-start-counts.md) | Server settings controlling initial copy weapon distribution for Qwant and NegaMan. |
| [**SinfulBusterExpert Unlocks**](sinful-buster-expert-unlocks.md) | Host selection of Unbound or progressive weapon unlocks. |
| [**AFK Penalties**](afk-penalties.md) | Server AFK detection rules, punishment items (Fire, GUHU, Money Bait, Money Bomb), and delay thresholds. |
| [**MegaMan Daily Weapons**](megaman-daily-weapons.md) | Server CVARs for MegaMan M2 weapon pool size and daily weapon synchronization. |

---

## 3. Mechanics & Gameplay References

| Document | Description |
|---|---|
| [**Bonus Boss Choice**](bonus-boss-choice.md) | Rules and timing for winner boss selection during bonus events. |
| [**Bonus Death Shitting**](bonus-death-shitting.md) | Death effect items and event-specific on-death drops. |
| [**Bonus Music Pools**](bonus-music-pools.md) | Shared event BGM pools and random track selection. |
| [**Eden Razon 3 Items**](eden-razon3-items.md) | Behavior and mechanics of ported Isaac item artifacts for Eden. |

---

## 4. Internal Contracts & Architecture

Architecture specifications and data contracts for internal Unholy core subsystems.

| Document | Description |
|---|---|
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

# AGENTS.md — Unholy Razon 4.0

## Project identity

This is a **Zandronum** mod for **MM8BDM (v6b)** — a `.pk3` mod based on Unholy (will switch to v6c when released). LMS (Last Man Standing) gamemode with new classes, bosses, items.

Engine DECORATE/ACS traps live in the **zandronum-modding** skill. MM8BDM `core_*`, ClassBase, BARLIB/ASSTLIB/DTADD, and Rage timing live in the **mm8bdm-modding** skill. Do not copy those guides here.

## Mandatory source consultation

For engine or mod behavior questions, consult the relevant source below rather
than relying on generic Doom/GZDoom knowledge. Use only the sources implicated
by the question.

| Priority | Location | What to consult |
|----------|----------|-----------------|
| Engine behavior | `../references/zandronum/zandronum-stable-branch-default/` | Zandronum engine source (actors, DECORATE, networking, inventory, etc.) |
| ACS semantics | `../references/zandronum/acc-branch-zandronum/` | Zandronum ACC source — builtins and compile rules |
| MM8BDM behavior | `../references/for_8bdm-v6b/mm8bdm-v6b/` | Base game assets, actors, ClassBase, weapons, and ACS APIs |
| When useful | `../references/for_8bdm-v6b/classes-v9gh_/` | Class Based Modification v9gh — **primary architectural template**; prefer its patterns when a feature already exists there |
| When useful | `../references/for_8bdm-v6a/` | MM8BDM v6a, CBM v9fh, and the Unholy v7b pb1 packages used as legacy behavior references |

All paths under `../references/` are **read-only reference**. Never edit them as part of normal work, and never load the reference trees as the mod unless a task explicitly requires a reference package for comparison or testing.

When loading the three Unholy v7b pb1 reference packages under `../references/for_8bdm-v6a/`, preserve this order:

1. `unholy_classes_unbound_v7b_pb1`
2. `unholy_bosses_unbound_v7b_pb1`
3. `unholy_bossesclasses_v7b_pb1_snacks_fix`

## Build

There is no build tool. The mod is a ZIP file with `.pk3` extension: pack `src/` recursively into `out/build.pk3`. **Do not invent build/CI tooling.** The `.gitignore` already excludes compiled ACS bytecode (`src/acs/`), `.o`, `.err`, and `out/`; reference sources live outside this repository under `../references/`.

## Runtime testing

Engine eligibility and MM8BDM package order are defined by the two modding
skills. This project's mod entry is `out/build.pk3`.

Launch profiles under `tools/*.launch.json` use paths **relative to the repo root**:
`out/build.pk3` for this mod, and `../wads/…` for the shared IWAD/base packages
(place or symlink the WAD directory as a sibling of this repo). Optional addons
in the `mm8bdm-v6b-full` profile similarly live under `../wads/`, `../unholyrazon_music/`,
and `../hudex/out/`.

Optional debugging mods, loaded in step 3 when relevant:

- `../wads/8bdm-hitvoxel-0.pk3` — visualize projectile hitboxes
- `../hudex/out/hudex.pk3` — preview `HudMessage` layouts

## Entry points (in load order)

| Lump | Purpose |
|-------|---------|
| `src/DECORATE` | Actor include root (`#include "actors/UH_Root.dec"`) |
| `src/KEYCONF` | Player class registration (`clearplayerclasses; addplayerclass ... nomenu`) |
| `src/LOADACS` | ACS library load list (`UH_COLORS`, `UH_TOOLS`) |
| `src/TEAMINFO` | 4 teams: Survivors, Bosses, Demoneyes, Light Team |
| `src/SNDINFO.players` | Per-soundclass pain/death/taunt aliases |
| `src/TEXTURES.classes` | Composite HUD sprites via TEXTURES |

## Actor include chain

`DECORATE` → `UH_Root.dec` includes (in order):
1. `ConstIntList_U.dec` — constants, button bitmasks, dye IDs
2. `unepic/BasicActors_U.dec` — base explosions, FX, helpers
3. `player/uh-flags.dec` — property powers (speed/alpha/jump), player flags
4. `player/uh-flags2.dec` — death handling, crit/frozen/burning death FX
5. `unepic/CoreActorReplace.dec` — replaces core teleport fog, MirrorBuster, etc.
6. `unepic/GeneralThings_U.dec` — utility inventory, gravity/gameplay flags
7. `unepic/General-inator.dec` — damage types, teleport artifacts
8. `player/uh-Weakness.dec` — weakness system, base damage/protection powers
9. `player/uh-BasePain.dec` — pain recoil, hitstun, knockback
10. `player/uh-CorePain.dec` — special pain for GravityHold, WindStorm, etc.
11. `UH_ClassIncludeList.dec` — all class and weapon includes
12. `unepic/FixCoreActors.dec` — Rush/stopped/slowed power fixes

Files earlier in the chain cannot reference actors defined later.

## Class hierarchy

```
ClassBase0 (MM8BDM core)
 → ClassBaseUH00  (basic actor + shared pain helpers)
  → ClassBase_UH10_BaseDamageTypes  (MM8BDM Pain/Death aliases)
   → ClassBase_UH20_HitEffects  (Unholy hit, protection, and status effects)
    → ClassBase_UH30_MovementEffects  (Unholy push, fling, and lift effects)
     → ClassBase_UH40_DeathEffects  (Unholy Death effects grouped by outcome)
      → ClassBaseSlot0 … ClassBaseSlot50 → ClassBase2
       → CustWepClassBase (MM8BDM custom-weapon base)
        → MegaManU / BusterExpert
```

The `actors/player/classbase/customslots/` directory (referenced by `classbase2_custompain.txt`) does not exist in this mod — the `_classbaseslot.txt` and its 50 slot files resolve from the base game v6b PK3. The mod only needs to provide `classbase2_custompain.txt` (which overrides the base game's version) and the `ClassBase_UH*.dec` files it includes. UH20/UH30/UH40 preserve the existing state labels and actions; they only reorganize the former U2-U4 definitions into dependency-safe functional layers.

## ACS

The two public UH library entry points remain in the `acs_source/` root:

| File | Library | What |
|------|---------|------|
| `uh_colors.acs` | `UH_COLORS` | Team color translations, dye defs, RGB translations |
| `uh_tools.acs` | `UH_TOOLS` | IsBot, IsItOnline, PointerExists, input and player-state helpers |

Other ACS libraries are grouped by responsibility under `hud/`, `classes/`,
`items/`, `systems/`, `coopenemies/`, `compat/`, `debug/`, and
`v6b_overrides/`. Large libraries keep their original `#library` file as an
aggregator and include implementation fragments in dependency order; those
fragments do not declare additional libraries. Within `systems/tools/`, `input.acs`
is reserved for button/WASD input detection, while `motion_helpers.acs` contains
player velocity and angle helpers; weather and spawn hooks are kept in separate
`weather.acs` and `spawn_hooks.acs` fragments. `rz_countinv.acs` (DECORATE-facing
inventory queries) and the `rz_tools.acs` aggregator also live there; the
Eden-only C396 TID reservation stays at
`classes/survivors/eden/eden_tid_reserve.acs`. Generic math/geometry helpers
imported via `#import` live in `_imports/uh_acsutils.acs` (Unholy additions
section); `WrapAround(i, lo, hi)` there is the single generalized angle fold —
never reintroduce unit-specific WrapAround variants (they collided across the
Unholy and CBM lineages). The XYDistance/XYZDistance/ZDistance
family is unified in `uh_acsutils.acs` as well (`XYDistance` uses the precise
VectorLength builtin; `ZDistance` is kept though currently unused); `uh_shared`
imports it, as do the fixed-point distance helpers `XYZDistanceFixed`/
`XYHypot`/`XYHypotFixed`/`XYZHypotFixed` (ex-CBM `fDistanceVal*` — numeric-suffix names
rejected; keep the XY/XYZ family prefix), plus `CeilFixedToInt` (avoid
reserved `Ceil`/`Floor`/`Round` names).
Color implementation fragments
live under `systems/colors/`.

`unholy/` is the LMS round-core module, compiled as the single `unholy`
library (its LOADACS entry must stay; do not split it into multiple
libraries). Fragments map to responsibility clusters: `uh_def` (unit state
header), `uh_funclib` (shared function drawer), `uh_lifecycle`,
`uh_bossselect` and `uh_dickhead_revival` (round flow, split from the former
monolithic aggregator), `uh_events` (round event system, ex-`uh_bonus`),
`uh_bosscore` + `uh_arena_fx` (ex-`uh_bspecial`),
`clownpiece_spellcard.acs` (Clownpiece-only spell-card flow; sole caller
`Clownpiece_W.dec`), `uh_display`/`uh_aspect` (boss/round HUD), `uh_music`
(music runtime; registration lives in `systems/music/`), and `uh_access`
(named-script API used by other libraries). `debug/rz_debug.acs` also
includes `uh_def` and `uh_funclib` — keep them unrenamed or update that
include list.

Survivor, boss, and demoneye class logic belongs under `classes/`. GemBanker’s
user-option bridge is kept in `classes/bosses/gem_banker_hud.acs`, while the
shared weapon roulette remains in `classes/shared/class_weapon_roulette.acs`.
Modified v6b ACS remains under `v6b_overrides/`; `uh_corereplace.acs` is a
v6b-derived library replacement that belongs there because it replaces v6b
rune/knockback scripts.

UH-owned shared includes live under `acs_source/_includes/mod_api/`. Modified
v6b shared includes live under `acs_source/v6b_overrides/_includes/`
(`common/` and `mod_api/`). When compiling, search the v6b override include
directories before the UH-owned include directory. Compiled `.o` files go in
`src/acs/` (gitignored). `LOADACS` contains library names, not source paths,
so its order and entries must remain unchanged when ACS source files move.

## Naming conventions

| Suffix | Meaning | Example |
|--------|---------|---------|
| `_U` | Custom UH actor/modification | `MegaManU`, `PainFX_UH` |
| `_W` | Weapon actor | `Megaman_W` |
| `_F` | Inventory flag (unobtrusive marker) | `Weak_F`, `IsRock_F` |
| `_P` | CustomInventory pickup/giver actor | `UHPainSound_P` |
| `_PowerGiver` | PowerApropGiver (grants the actual power) | `UH_120_SpeedPowerGiver` |

Player classes registered in `KEYCONF` use `nomenu` (hidden from default player setup).

## Adding a new class

1. Create `actors/classes/<team>/<ClassName>.dec` (actor) and `<ClassName>_W.dec` (weapon)
2. Add `#include` lines to `UH_ClassIncludeList.dec`
3. Register in `KEYCONF`: `addplayerclass <Name> nomenu`
4. If needed: soundclass in `SNDINFO.players`, HUD sprites in `TEXTURES.classes`
5. Team colors: edit `UH_COLOR.acs`

## Weapon base classes

Three weapon bases in `actors/inventory/baseweaponedit.txt`:
- `BaseMM8BDMWep` — core v6b weapons (forbidden to `CustWepClassBase`)
- `BaseMM8BDMCustWep` — custom weapons (restricted to `CustWepClassBase`)
- `BaseMM8BDMWep_UH` — UH-specific weapons

All override `DeselectDeath` to check `uh_IsItOnline` for net sync.

## Fast MCP debug loop

Use `tools/mm8bdm-v6b-linux.launch.json` for the configured Linux MCP and
`tools/mm8bdm-v6b.launch.json` for Windows clients. Commands, profile choices,
direct-call guidance, and build/runtime traps live in `tools/README.md`.

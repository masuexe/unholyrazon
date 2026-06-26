# AGENTS.md — Unholy Razon 4.0

## Project identity

GZDoom/Zandronum `.pk3` mod based on Unholy, targeting MM8BDM-v6b (will switch to v6c when released). TLMS gamemode with new classes, bosses, items.

## Build

There is no build tool. The mod is a ZIP file with `.pk3` extension: pack `src/` recursively into `out/build.pk3`. **Do not invent build/CI tooling.** The `.gitignore` already excludes compiled ACS bytecode (`src/acs/`), `.o`, `.err`, `out/`, and `ref/`.

## Reference directories (read-only, never load)

- `ref/MM8BDM-v6b/` — base game assets and actor definitions
- `ref/classes-v9gh_/` — Class Based Modification v9gh; **primary architectural template**. When implementing a feature, look here first for the canonical solution.

## Entry points (in load order)

| L ump | Purpose |
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
2. `special/BasicActors_U.dec` — base explosions, FX, helpers
3. `player/uh-flags.dec` — property powers (speed/alpha/jump), player flags
4. `player/uh-flags2.dec` — death handling, crit/frozen/burning death FX
5. `special/CoreActorReplace.dec` — replaces core teleport fog, MirrorBuster, etc.
6. `special/GeneralThings_U.dec` — utility inventory, gravity/gameplay flags
7. `special/General-inator.dec` — damage types, teleport artifacts
8. `player/uh-Weakness.dec` — weakness system, base damage/protection powers
9. `player/uh-BasePain.dec` — pain recoil, hitstun, knockback
10. `player/uh-CorePain.dec` — special pain for GravityHold, WindStorm, etc.
11. `UH_ClassIncludeList.dec` — all class and weapon includes
12. `special/FixCoreActors.dec` — Rush/stopped/slowed power fixes

Files earlier in the chain cannot reference actors defined later.

## Class hierarchy

```
ClassBase0 (MM8BDM core)
 → ClassBaseU0  (custom pain/death states)
  → ClassBaseU1  (core damage type pain redirects)
   → ClassBaseU2  (weakness mappings, boss pain redirects)
    → ClassBaseSlot0 … ClassBaseSlot50 → ClassBase2
     → CustWepClassBase (MM8BDM custom-weapon base)
      → MegaManU / BusterExpert
```

The `actors/player/classbase/customslots/` directory (referenced by `classbase2_custompain.txt`) **does not yet exist** — slot chain is a stub. Add new slot files there when extending the hierarchy.

## ACS

Two libraries in `src/acs_source/`:

| File | Library | What |
|------|---------|------|
| `UH_COLOR.acs` | `UH_COLORS` | Team color translations, dye defs, RGB translations |
| `UH_TOOLS.acs` | `UH_TOOLS` | IsBot, IsItOnline, PointerExists, button/movement input helpers |

Shared includes live under `acs_source/_includes/`:
- `common/` — MM8BDM base libraries (`8BDMDEFS.acs`, `8BDMEFCT.acs`, etc.)
- `mod api/` — CBM mod API (`ASSTLIB.acs`, `BARLIB.acs`, `DTADD.acs`, `PICKRPLC.acs`)

Compiled `.o` files go in `src/acs/` (gitignored). ACS compilation requires the ACC compiler. New ACS libraries must be added to `LOADACS`.

## Naming conventions

| Suffix | Meaning | Example |
|--------|---------|---------|
| `_U` | Custom UH actor/modification | `MegaManU`, `PainFX_UH` |
| `_W` | Weapon actor | `Megaman_W` |
| `_F` | Inventory flag (unobtrusive marker) | `Weak_F`, `IsRock_F` |
| `_P` | CustomInventory pickup/giver actor | `UHPainSound_P` |
| `_Giv` | PowerApropGiver (grants the actual power) | `UH_120_SpeedPowerGiver` |

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

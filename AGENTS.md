# AGENTS.md — Unholy Razon 4.0

## Project identity

This is a **Zandronum** mod for **MM8BDM (v6b)** — a `.pk3` mod based on Unholy (will switch to v6c when released). LMS (Last Man Standing) gamemode with new classes, bosses, items.

Engine DECORATE/ACS traps live in the **zandronum-modding** skill. MM8BDM `core_*`, ClassBase, BARLIB/ASSTLIB/DTADD, and Rage timing live in the **mm8bdm-modding** skill. Do not copy those guides here.

## Ambiguous prompts — stop and ask

If the user's request is unclear, incomplete, or admits multiple reasonable interpretations:

1. **Do not guess and execute.** Do not invent missing requirements, pick an arbitrary design, or start editing "based on a best guess."
2. **Ask clarifying questions first** — scope, target class/weapon, expected behavior, constraints, reference to imitate, etc.
3. **Wait for a clearer prompt** before implementing, researching deeply toward a chosen path, or changing files.

Only proceed when the intent is concrete enough that a correct implementation is unambiguous.

## Mandatory source consultation

Before implementing or answering engine/mod behavior questions, **look up the relevant sources**. Do not rely on memory or generic Doom/GZDoom knowledge when Zandronum or MM8BDM differs.

| Priority | Location | What to consult |
|----------|----------|-----------------|
| Required | `../references/zandronum/zandronum-stable-branch-default/` | Zandronum engine source (actors, DECORATE, networking, inventory, etc.) |
| Required | `../references/zandronum/acc-branch-zandronum/` | Zandronum ACC (ACS compiler) source — ACS semantics, builtins, compile rules |
| Required | `../references/for_8bdm-v6b/mm8bdm-v6b/` | Base game assets, actors, classbase, weapons, ACS APIs this mod targets |
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

For Zandronum MCP tests, prefer the newest locally available Zandronum build; nightly and alpha builds are allowed. Never test with a version older than 3.2.1 unless the user explicitly requests investigation of an older-version regression.

Load MM8BDM test content in this order:

0. IWAD: `megagame.wad` (usually `/mnt/d/wads/megagame.wad` on this machine)
1. One base-game package named in the `mm8bdm-vXY` form, normally `mm8bdm-v6b.pk3` (v6a may be used when requested; v6c may be used after release)
2. When step 1 is `mm8bdm-v6b.pk3`, mandatory fix package `/mnt/d/wads/8bdm-v6b-miscfixes-v5.pk3`
3. All other mods, including this project's `out/build.pk3`

Optional debugging mods, loaded in step 3 when relevant:

- `/mnt/d/wads/8bdm-hitvoxel-0.pk3` — visualize projectile hitboxes
- `/mnt/d/projects/mm8bdm/hudex/out/hudex.pk3` — preview `HudMessage` layouts

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
 → ClassBaseUH0  (basic actor + shared pain helpers)
  → ClassBaseUH10_BaseDamageTypes  (MM8BDM Pain/Death aliases)
   → ClassBaseUH20_HitEffects  (Unholy hit, protection, and status effects)
    → ClassBaseUH30_MovementEffects  (Unholy push, fling, and lift effects)
     → ClassBaseUH40_DeathEffects  (Unholy Death effects grouped by outcome)
      → ClassBaseSlot0 … ClassBaseSlot50 → ClassBase2
       → CustWepClassBase (MM8BDM custom-weapon base)
        → MegaManU / BusterExpert
```

The `actors/player/classbase/customslots/` directory (referenced by `classbase2_custompain.txt`) does not exist in this mod — the `_classbaseslot.txt` and its 50 slot files resolve from the base game v6b PK3. The mod only needs to provide `classbase2_custompain.txt` (which overrides the base game's version) and the `ClassBase_UH*.dec` files it includes. UH20/UH30/UH40 preserve the existing state labels and actions; they only reorganize the former U2-U4 definitions into dependency-safe functional layers.

## ACS

UH libraries in `src/acs_source/`:

| File | Library | What |
|------|---------|------|
| `UH_COLOR.acs` | `UH_COLORS` | Team color translations, dye defs, RGB translations |
| `UH_TOOLS.acs` | `UH_TOOLS` | IsBot, IsItOnline, PointerExists, button/movement input helpers |

Shared includes live under `acs_source/_includes/` (`common/` for MM8BDM base libs, `mod api/` for CBM). Compiled `.o` files go in `src/acs/` (gitignored).

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

The reusable MCP fork under `/home/user/projects/zandronum/zandronum-mcp/` supports named launch profiles,
actor polling, detailed actor state, and incremental engine logs. Set
`ZANDRONUM_LAUNCH_PROFILES` to `tools/mm8bdm-v6b-linux.launch.json` when using
the configured Linux MCP. The Windows counterpart, `tools/mm8bdm-v6b.launch.json`,
is retained for Windows MCP clients. For a deterministic smoke regression, use
the reusable wrapper first:

```bash
./tools/validate-build-pk3.sh
./tools/mcp/smoke-test.sh
./tools/mcp/smoke-test.sh --profile mm8bdm-v6b-full --json
./tools/mcp/smoke-test.sh --dry-run
```

`validate-build-pk3.sh` is a read-only ZIP/entry-point check; it does not build
or rewrite `out/build.pk3`.

The wrapper validates profile paths, launches one instance, prints a compact
startup/player summary, and asks MCP to quit the instance. It does not replace
focused MCP calls when the next decision depends on live actor state or a
specific log line. The Linux profiles include `-nosound` and software video
mode so WSL automation does not depend on host audio/GPU presentation.

For focused live debugging, use this order:

1. `launch_instance` with profile `mm8bdm-v6b-smoke`.
2. Make the smallest reproducible action (for example, fire `FireBlastWep`).
3. Use `wait_for_actor` by TID or exact class, then `actor_state` or
   `actors_near` to inspect alpha/render state and actor pointers.
4. Poll `read_engine_log` with its returned `nextCursor`; use
   `get_startup_errors` if the bridge never opens.
5. Use `mm8bdm-v6b-full` only for final integration checks with the optional
   addons and debug cvars.

This workflow targets the locally built Zandronum 3.3-alpha MCP engine. Do not
fall back to the removed 3.1 archive. The profile file is intentionally the
single source of truth for the v6b IWAD/base/fix/addon load order within each
platform profile.

## Reusable tool policy

- Keep frequently repeated, deterministic workflows in `tools/` with a small
  `--help` surface; keep one-off experiments in `/tmp`.
- Prefer scripts that accept arguments or environment overrides, return useful
  exit codes, and emit concise stdout. Save full engine logs outside the repo.
- Add a `--dry-run` mode for launch or mutation helpers and make cleanup
  automatic where a process is started.
- Keep implementation details in the script. Put only the command, inputs,
  outputs, and safety notes in this file or `tools/README.md`.

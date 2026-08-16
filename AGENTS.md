# AGENTS.md — Unholy Razon 4.0

## Project identity

This is a **Zandronum** mod for **MM8BDM (v6b)** — a `.pk3` mod based on Unholy (will switch to v6c when released). LMS (Last Man Standing) gamemode with new classes, bosses, items.

Do **not** assume GZDoom-only APIs, DECORATE extensions, or ACS behavior unless verified against Zandronum / MM8BDM-v6b sources below.

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
| Required | `ref/zandronum-stable-branch-default/` | Zandronum engine source (actors, DECORATE, networking, inventory, etc.) |
| Required | `ref/acc-branch-zandronum/` | Zandronum ACC (ACS compiler) source — ACS semantics, builtins, compile rules |
| Required | `ref/MM8BDM-v6b/` | Base game assets, actors, classbase, weapons, ACS APIs this mod targets |
| When useful | `ref/classes-v9gh_/` | Class Based Modification v9gh — **primary architectural template**; prefer its patterns when a feature already exists there |

All paths under `ref/` are **read-only reference** (gitignored). Never load them as the mod, never edit them as part of normal work.

## Build

There is no build tool. The mod is a ZIP file with `.pk3` extension: pack `src/` recursively into `out/build.pk3`. **Do not invent build/CI tooling.** The `.gitignore` already excludes compiled ACS bytecode (`src/acs/`), `.o`, `.err`, `out/`, and `ref/`.

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
 → ClassBaseU0  (basic actor + shared pain helpers)
  → ClassBaseU1  (MM8BDM Pain/Death)
   → ClassBaseU2  (Unholy survivors)
    → ClassBaseU3  (Unholy bosses)
     → ClassBaseU4  (Demoneye + Unholy items)
      → ClassBaseSlot0 … ClassBaseSlot50 → ClassBase2
       → CustWepClassBase (MM8BDM custom-weapon base)
        → MegaManU / BusterExpert
```

The `actors/player/classbase/customslots/` directory (referenced by `classbase2_custompain.txt`) does not exist in this mod — the `_classbaseslot.txt` and its 50 slot files resolve from the base game v6b PK3. The mod only needs to provide `classbase2_custompain.txt` (which overrides the base game's version) and the `ClassBase_U*.dec` files it includes.

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

## DECORATE gotchas

### Empty inherit-only actors still need `{}`

In Zandronum DECORATE, an actor that only inherits (no properties/states) **must** still have an empty body. A bare inheritance line is illegal:

```cpp
// WRONG — parse error
actor Decoy_F_23TrailFX : StealthS_RailTrailFX

// CORRECT
actor Decoy_F_23TrailFX : StealthS_RailTrailFX {}
```

Do not strip empty `{}` when cleaning properties (e.g. removing `Translation`).

### `CheckInventory` is ACS-only — not a DECORATE expression function

In Zandronum DECORATE, `CheckInventory("Item")` is **not** a valid function in action arguments or expressions. Using it causes a load-time script error (`Call to unknown function 'CheckInventory'`). Inventory checks in DECORATE must use actions such as `A_JumpIfInventory` / `A_TakeInventory` / `A_GiveInventory`, or route through ACS via `CallACS` / `ACS_NamedExecute*`.

```cpp
// WRONG — parse/load error in DECORATE
6H50 A 0 ACS_NamedExecuteAlways("MyLog", 0, CheckInventory("UH_MoveHud_F"))

// CORRECT — jump on inventory in DECORATE
6H50 A 0 A_JumpIfInventory("UH_MoveHud_F", 1, "HasHud")

// CORRECT — read inventory inside ACS (CheckInventory is fine there)
6H50 A 0 ACS_NamedExecuteAlways("MyLog", 0, 0)
// script "MyLog" (int unused) { Log(i:CheckInventory("UH_MoveHud_F")); }
```

### `SPRITE A 0 goto Label` is illegal — put `goto` on its own line

In Zandronum DECORATE, state control keywords (`goto`, `loop`, `wait`, `stop`, `fail`) are **not** valid as the action/parameter of a sprite frame. Writing them on the same line as a frame is a parse error (`Invalid state parameter goto`):

```cpp
// WRONG — parse error
TNT1 A 0 goto DeselectInstant

// CORRECT — dummy frame, then standalone control
TNT1 A 0
goto DeselectInstant
```

The same rule applies to `loop` / `wait` / `stop` / `fail`: never append them after duration (and optional action) on one line. Standalone control lines also do **not** consume `A_Jump*` relative offsets (see above).

### Relative offsets ignore standalone state control instructions

In Zandronum DECORATE, relative offsets used by `A_Jump*` functions:

- **include** the state containing the `A_Jump*` call;
- **exclude** standalone state control instructions (`goto`, `loop`, `wait`, `stop`, `fail`).

This means a relative offset of **1** targets the very next state frame. Standalone control instructions do **not** consume an offset.

```cpp
ReadyX:
    8H00 A 0 A_JumpIfInventory("MyAmmo", 200, 2)
    8H00 A 2 A_WeaponReady                    // offset 1
    goto ReadyGive                             // not counted
    8H00 A 2 A_WeaponReady(WRF_ALLOWRELOAD)    // offset 2
```

Do **not** write `SPRITE A N goto Label` on one line — that is a parse error (see previous section). Use a frame plus a following standalone `goto`.

A second `goto` after that **overwrites** the previous frame's next state (it is not unreachable dead code). Fail-path `goto Ready` must come *before* the success frames, never after `goto DeselectInstant`:

```cpp
// WRONG — second goto wins; success falls through to Ready instead of Deselect
TNT1 A 0
goto DeselectInstant
Goto Ready2

// CORRECT
6H50 A 0 A_JumpIf(CallACS("uh_DoMove"), 2)
6H50 A 0
Goto Ready2              // fail path (offset 1)
TNT1 A 0                 // success (offset 2)
goto DeselectInstant
```

### 0-tic loops are forbidden — they crash Zandronum

Every state loop cycle must contain at least one frame with duration >= 1. A loop where **all** frames in the cycle have duration 0 will execute infinitely in a single tic and crash the game.

```cpp
// WRONG — crashes
ReadyXGive:
    8H00 A 0 A_GiveInventory("UnholyBossAmmo200",4)
    loop

// CORRECT
ReadyXGive:
    8H00 A 1 A_GiveInventory("UnholyBossAmmo200",4)
    loop
```

This also applies to implicit cycles formed by `goto`. If `ReadyXGive` does `goto ReadyX` and `ReadyX` starts with 0-tic frames that eventually lead back to `ReadyXGive`, the cycle must include at least one non-zero duration somewhere on that path — typically the `A_WeaponReady` frame serves this purpose.

### `loop` jumps to the nearest state label, not to the parent

`loop` always goes to the **most recent** state label — which is the current state's own label, not the previous state. Use `goto <parent>` to return to the parent ready state.

```cpp
// WRONG — loops within Give, never calling A_WeaponReady again
ReadyXGive:
    8H00 A 1 A_GiveInventory("MyAmmo",4)
    loop

// CORRECT
ReadyXGive:
    8H00 A 1 A_GiveInventory("MyAmmo",4)
    goto ReadyX
```

### `Offset(0, y)` does not clear X — and `Offset(x, 0)` does not clear Y

In `P_SetPsprite`, Misc1/Misc2 from `Offset` are applied only when **non-zero**:

```cpp
if (state->GetMisc1()) psp->sx = state->GetMisc1()<<FRACBITS;
if (state->GetMisc2()) psp->sy = state->GetMisc2()<<FRACBITS;
```

So `Offset(0, 42)` after `Offset(2, 46)` leaves **sx = 2** (only sy becomes 42). Writing `Offset(0, y)` does **not** mean “absolute X = 0”.

```cpp
// WRONG — intends center-X settle; sx stays 2
8H19 A 1 Offset(2, 46)
8H19 A 1 Offset(0, 42)
8H19 A 1 Offset(0, 36)

// CORRECT — reset both axes, then Y-only motion keeps sx at 0
8H19 A 1 Offset(2, 46)
8H19 A 0 A_WeaponReady(14)
8H19 A 1 Offset(0, 42)
8H19 A 1 Offset(0, 36)

// ALSO CORRECT — keep stepping X with non-zero Misc1 until the final clear
8H19 A 1 Offset(2, 46)
8H19 A 1 Offset(1, 42)
8H19 A 1 A_WeaponReady(14)
```

To force absolute ready position `(sx=0, sy=WEAPONTOP)`, call `A_WeaponReady` **without** `WRF_NoBob` so `DoReadyWeaponToBob` runs. In this mod, `A_WeaponReady(14)` is common (`14 = NoSwitch|NoFire`); it still resets psprite coords. `ReadyX` loops also call `A_WeaponReady`, but do not rely on that to fix mid-animation offsets.

### Weapon `Flash` shares weapon `sx`/`sy` every tic

At the end of `P_MovePsprites`, Zandronum copies weapon coords onto the flash layer:

```cpp
player->psprites[ps_flash].sx = player->psprites[ps_weapon].sx;
player->psprites[ps_flash].sy = player->psprites[ps_weapon].sy;
```

`A_GunFlash` Flash-state `Offset(...)` cannot diverge from the weapon layer. For different relative placement, bake deltas into TEXTURES (or put the overlay animation on the weapon layer). Zandronum has no `A_Overlay` / `A_OverlayOffset`.

### Rage rune halves psprite durations > 1

MM8BDM Rage (`PowerDoubleFiringSpeedRune` → `CF_DOUBLEFIRINGSPEED`) makes `P_MovePsprites` decrement weapon/flash `tics` **twice** per game tic (second decrement skipped when tics already hit 0).

| Written duration | Real duration under Rage |
|------------------|---------------------------|
| `1` | still `1` |
| even `N` | `N / 2` |
| odd `N` (e.g. 13) | `⌈N / 2⌉` (e.g. 7) |

Implications:

- Smoothing a fire anim to all `duration 1` frames **disables** this speedup; use `A_JumpIfInventory("PlayerPropertyRage", 1, 1)` skips and/or a separate Rage state branch.
- Holds written as `A 13` inside a Rage-only state are really ~7 tics — double the written value when you need a target real length (e.g. want 13 real → write `26`).

### The first frame of the Spawn state never runs its action — put a dummy `TNT1 A 0` before it

When an actor is created, `AActor::StaticSpawn` sets the Spawn state **directly**, bypassing `SetState`, so the first frame's action is never called:

```cpp
// p_mobj.cpp (AActor::StaticSpawn)
// Set the state, but do not use SetState, because action
// routines can't be called yet.  If the spawnstate has an action
// routine, it will not be called.
FState *st = actor->SpawnState;
actor->state = st;
actor->tics = st->GetTics();
```

On the actor's first tick (`AActor::Tick`, `--tics <= 0`) the state machine jumps straight to `state->GetNextState()`, skipping the first frame entirely. State actions only run when a state is **entered via `SetState`** (`p_mobj.cpp:586`), and `StaticSpawn` never calls it.

```cpp
// WRONG — the ACS call never executes
Spawn:
    TNT1 A 0 ACS_NamedExecuteWithResult("uh_CopyPointerAnglePitch", 2, 0)
    X_4D JK 4
    loop

// CORRECT — dummy first frame; the action frame runs on the first tick
Spawn:
    TNT1 A 0
    TNT1 A 0 ACS_NamedExecuteWithResult("uh_CopyPointerAnglePitch", 2, 0)
    X_4D JK 4
    loop
```

Scope: this only applies to the **initial Spawn-state entry at actor creation** (every spawn path goes through `StaticSpawn`). States entered later via `SetState` (Death, Bounce, Pain, …) run their first frame's action normally — e.g. a `Bounce:` state starting with `TNT1 A 0 A_Stop` is fine. If an actor is later forced back into its Spawn state via `SetState(SpawnState)` (pickup respawn etc.), the action *does* run.

### DECORATE expressions can read native Actor fields — angles are float degrees

The expression evaluator exposes native `Actor` fields as readable variables. They are declared in the internal base actor definition `wadsrc/static/actors/actor.txt:30-59` (see also `ParseNativeVariable` in `thingdef_parse.cpp`):

- `angle_t angle`, `angle_t pitch` — read as **float degrees** (0–360; pitch follows the engine convention: positive = down). Conversion is `VAL_Angle → value * 90/ANGLE_90` (`thingdef_expression.cpp:227-230`).
- `fixed_t x, y, z, velx, vely, velz, floorz, ceilingz, alpha, scaleX, scaleY` — read as **floats** in map units (fixed → `/65536.`).
- `int health, mass, tid, special, damage, score`, `args[5]` — plain ints.

These are usable anywhere an expression is, e.g. `A_SpawnItemEx` velocity args:

```cpp
// velocity = Speed along the actor's aim (pitch). `sin(-pitch)` matches the
// engine's `vz = -sin(pitch)` convention (p_mobj.cpp:7531).
A_SpawnItemEx("SomeShot", 0, 0, 0, cos(pitch)*Speed, 0, sin(-pitch)*Speed, 0)
```

This is used throughout the mod (e.g. `NegaNeedleCannon.dec`, `General-inator.dec:47`). `pitch` reads the **calling actor's own** `pitch` field, so on a projectile that had its `pitch` set at spawn (e.g. via `uh_CopyPointerAnglePitch`), it stays readable later in Death/Bounce states. Do not route these through ACS (`CallACS("uh_FetchPointerPitch", …)`) — the native field is equivalent and simpler.

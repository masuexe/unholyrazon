# Survivor and Class API

Unholy Razon provides a modder-facing API to define custom survivor classes. Custom survivor classes integrate with the Last Man Standing (LMS) class selection, the native teammate bar, UIX mugshots, shiny transformation variants, and automatic weapon stripping upon boss or Demoneye morphs.

The public API functions live in [`uhadd.acs`](../src/acs_source/_includes/mod_api/uhadd.acs). A minimal working addon package is provided in [`examples/definesurvivor_addon`](../examples/definesurvivor_addon).

---

## 1. Class Registration (KEYCONF)

To declare your survivor class in the engine, add it to your addon's `KEYCONF` lump:

```
addplayerclass MySurvivorClass nomenu
```

---

## 2. Registering a Survivor in ACS

Custom survivors register using `DefineSurvivor` and `DefineTeamPresentation`. Because client-side HUD elements (such as the native teammate bar, UIX, and scoreboard) resolve mugshots locally, you must register in **both** an `OPEN` script (server) and an `OPEN CLIENTSIDE` script (client).

```c
#library "MY_SURVDEFS"
#include "zcommon.acs"
#import "uh_log.acs"   // Required: UHADD calls UH_Log()
#include "uhadd.acs"   // Case-sensitive include path

function void MyRegisterSurvivors(void) {
  // Register identity (returns survivor ID)
  int survId = DefineSurvivor(
    -1,                   // id (-1 for auto-allocated custom ID)
    "MySurvivorClass",    // actor (DECORATE player class)
    "\cjMy Survivor",     // name (broadcast and display name)
    "UMUG_6"              // mugshot font or lump
  );

  // Register presentation data for teammate bar and scoreboard
  DefineTeamPresentation(
    "MySurvivorClass",    // actor class name
    "MySurv",             // short name for teammate bar (empty "" falls back to name)
    "MYMUG",              // mugshot texture for teammate bar and UIX
    "MYICON",             // scoreboard icon (empty "" falls back to portrait)
    0                     // flags (reserved, pass 0)
  );
}

script "my_define_survivors" OPEN {
  if (!UHInPlay()) terminate;
  MyRegisterSurvivors();
}

script "my_define_survivors_cs" OPEN CLIENTSIDE {
  // Do NOT check UHInPlay() on clients
  MyRegisterSurvivors();
}
```

---

## 3. Parameter Specifications

### DefineSurvivor
```c
function int DefineSurvivor(int id, str actor, str name, str mugshot)
```

| Parameter | Type | Description |
|---|---|---|
| `id` | `int` | Slot ID. Pass `-1` to auto-allocate a custom ID (`-1, -2, …`). Nonnegative IDs (`0..59`) are reserved for vanilla survivor classes. |
| `actor` | `str` | DECORATE player actor class name. Must match the class registered in `KEYCONF`. |
| `name` | `str` | Display name of the survivor class. Supports ACS color codes (e.g. `\cj`). |
| `mugshot` | `str` | HUD mugshot font or graphic lump name (e.g. `"UMUG_6"`). |

- Returns the assigned `survivorId` on success.
- Returns `UHSURV_FAIL` (`-9999`) on failure.

---

### DefineTeamPresentation
```c
function int DefineTeamPresentation(str actor, str shortName, str portrait, str scoreIcon, int flags)
```

| Parameter | Type | Description |
|---|---|---|
| `actor` | `str` | DECORATE player actor class name (case-insensitive). |
| `shortName` | `str` | Abbreviated name displayed on the native teammate bar. Pass `""` to fall back to the class broadcast name. |
| `portrait` | `str` | Texture lump name for teammate bar and UIX portrait displays. |
| `scoreIcon` | `str` | Scoreboard column texture (`UHPlayerIcon`). Pass `""` to reuse the `portrait` texture. |
| `flags` | `int` | Reserved display flags; pass `0`. |

---

## 4. Shiny Class Variants

Unholy supports a "Shiny" variant for survivor classes. When a survivor player uses the **True Power** item (`TruePowerItem`) or receives it automatically from round events (`AutoTruePowerItem`), the core executes `uh_shinyclassmorpher` to morph them into their shiny variant (`<YourClass>Shiny`).

1. **Trigger Condition**:
   - Survivors activate Shiny mode by using `TruePowerItem` from their inventory bar or receiving `AutoTruePowerItem` (e.g. from True Power FFA events or LMS drops).
   - The item cannot be used if the player is already morphed (`MorphedFlag`), has already used True Power (`TruePowerItemFlag`), or is on the Boss team (`BAWS`).

2. **Morph Process (`uh_shinyclassmorpher`)**:
   - The script determines the current player class (`GetActorClass`) and attempts to morph them into `<YourClass>Shiny`.
   - **On Success**:
     - The player is morphed with full health and invulnerability frames.
     - Standard survivor weapons are swept and stripped via `uh_StripSurvivorWeps`.
     - Spawns sparkle visual effects (`ShinySparkleFlash`, `S_ClassSpawn_P`).
     - Activates the Shiny mugshot overlay (`UHShinyMugshot_F`) if a portrait is registered.
   - **On Failure (Fallback)**:
     - If `<YourClass>Shiny` is not defined in DECORATE, `MorphActor` fails gracefully.
     - Spawns `S_ClassSpawnNo_P`, which awards fallback stat enhancements (`PowerFakeTruePower1` damage boost, `PowerFakeTruePower2` damage reduction, and `PowerFakeTruePower3` movement speed) without morphing the player actor.

3. **Conventions and Actor Scope**:
   - The shiny player class must be named exactly `<YourClass>Shiny` (e.g. `MySurvivorClassShiny`).
   - Do not name non-player actors `YourClassShiny`. For weapons, use `YourClassShiny_W`.
   - For special shiny move-weapon pools (such as QwantShiny or NegaManShiny charging cycles), refer to [`examples/shinywep_addon`](../examples/shinywep_addon).

---

## 5. Weapon Stripping and Custom Names

When a survivor is morphed into a Boss, Demoneye, or Shiny variant, the core calls `uh_StripSurvivorWeps` to remove all survivor weapons.

### Automatic Family Sweep
By default, the core automatically strips all weapons matching the naming conventions:
- `<YourClass>_W`
- `<YourClass>_W1` through `<YourClass>_W9`

### Registering Non-Conforming Weapons (`DefineSurvivorWep`)
If your survivor uses weapon actors that do not follow the `<Class>_W` naming pattern (such as item-named weapons, secondary arms, or special armaments), you must explicitly register them:

```c
function void MyRegisterSurvivorWeps(void) {
  DefineSurvivorWep("CustomBusterArm");
  DefineSurvivorWep("AuxiliaryShieldWeapon");
}

script "my_define_survweps" OPEN {
  if (!UHInPlay()) terminate;
  MyRegisterSurvivorWeps();
}
```

- `DefineSurvivorWep` ensures these weapons are cleanly removed upon morphing, preventing weapon carry-over into boss rounds.
- Re-registering the same weapon actor name is safe and returns the existing row.

---

## 6. Multi-Weapon Registration (`DefineMultiWeapon`)

For mechanics that need to inspect or manipulate a class's native weapon arsenal (such as Pharaoh 4MI's roulette curse), register multi-weapon sets with `DefineMultiWeapon`:

```c
script "my_multiweapons" OPEN {
  if (!UHInPlay()) terminate;
  DefineMultiWeapon("MySurvivorClass", "MyPrimaryWeapon");
  DefineMultiWeapon("MySurvivorClass", "MySecondaryWeapon");
}
```

- **Server-only**: This table is managed entirely on the server; no `OPEN CLIENTSIDE` script is needed.
- A class is treated as a multi-weapon class only while the player currently holds two or more registered weapons.
- Duplicate pairs return the existing row; a single weapon cannot be bound to multiple classes simultaneously.

---

## 7. Runtime Management (CRUD)

Mod scripts and host utilities can inspect or modify survivor definitions at runtime:

| Function | Description |
|---|---|
| `FindSurvivorByActor(str actor)` | Resolves a player actor class to its integer survivor ID. Returns `UHSURV_FAIL` if not found. |
| `IsSurvivorEnabledByActor(str actor)` | Checks if the survivor is currently enabled. |
| `SetSurvivorEnabledByActor(str actor, int enabled)` | Enables (`1`) or disables (`0`) a survivor. |
| `UpdateSurvivorDisplayByActor(str actor, str name, str mugshot)` | Updates display name and mugshot for an existing survivor. |
| `RemoveSurvivorByActor(str actor)` | Removes a survivor definition from active queries. |

Status codes returned:
- `UHDB_OK` (`0`): Operation succeeded.
- `UHDB_ERR_NOTFOUND` (`1`): Survivor ID or actor not found.
- `UHDB_ERR_REFERENCED` (`3`): Cannot remove; survivor is currently active or referenced.
- `UHDB_ERR_BADARG` (`5`): Invalid argument or IPC failure.

For more details on runtime table operations, see [`docs/modding/uhdt-identity-crud-contract.md`](modding/uhdt-identity-crud-contract.md).

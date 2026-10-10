# Demoneye and Eye Morph Pool API

Unholy Razon provides a modder-facing API to define custom **Demoneye** classes and configure weighted **Eye Morph Pools** (such as Money Bait bags, Money Bombs, or custom polymorph items).

The public API functions live in [`uhadd.acs`](../src/acs_source/_includes/mod_api/uhadd.acs). A working example addon package is provided in [`examples/eyemorph_addon`](../examples/eyemorph_addon).

---

## 1. Registering a Demoneye

Custom Demoneyes register using `DefineDemoneye`. Like other player definitions, register in **both** an `OPEN` script (server) and an `OPEN CLIENTSIDE` script (client).

```c
#library "MY_EYEDEFS"
#include "zcommon.acs"
#import "uh_log.acs"   // Required: UHADD calls UH_Log()
#include "uhadd.acs"   // Case-sensitive include path

function void MyRegisterEyes(void) {
  int eyeId = DefineDemoneye(
    -1,                   // id (-1 for auto-allocated custom ID)
    "MyDemoneyeActor",    // actor (DECORATE player class)
    "\ctSpectral",        // name (colored eye name)
    "a ",                 // prefix (grammatical article: "a ", "an ", or "")
    0,                    // flags (0, or UHEYE_FLAG_NOSUFFIX)
    "EYE_F0",             // mugshot font or lump
    "Spectral"            // eventStem (used to construct {stem}_MoolaGiver)
  );

  // Optional: register presentation data for teammate bar and scoreboard
  DefineTeamPresentation(
    "MyDemoneyeActor",
    "Spectral Eye",
    "EYEMUG",
    "EYEICON",
    0
  );
}

script "my_define_eyes" OPEN {
  if (!UHInPlay()) terminate;
  MyRegisterEyes();
}

script "my_define_eyes_cs" OPEN CLIENTSIDE {
  // Do NOT check UHInPlay() on clients
  MyRegisterEyes();
}
```

---

## 2. DefineDemoneye Specifications

```c
function int DefineDemoneye(
  int id,
  str actor,
  str name,
  str prefix,
  int flags,
  str mugshot,
  str eventStem)
```

| Parameter | Type | Description |
|---|---|---|
| `id` | `int` | Slot ID. Pass `-1` to auto-allocate a custom ID (`-1, -2, …`). Nonnegative IDs are reserved for vanilla Demoneyes. |
| `actor` | `str` | DECORATE player actor class name. Pass `""` for bonus face-only definitions. |
| `name` | `str` | Display name of the Demoneye. Supports ACS color codes (e.g. `\ct`). |
| `prefix` | `str` | Grammatical article prefix (e.g. `"a "`, `"an "`, or `""`). Formats the broadcast: `"\cjYou are now " + prefix + name + " Demoneye!"`. |
| `flags` | `int` | Pass `0` for default formatting, or `UHEYE_FLAG_NOSUFFIX` (`1`) to omit the trailing `" Demoneye"` in announcement lines. |
| `mugshot` | `str` | HUD mugshot font or graphic lump name (e.g. `"EYE_F0"`). Mandatory. |
| `eventStem` | `str` | Stem used to construct the Moola/Item giver actor `{eventStem}_MoolaGiver`. |

- Returns the assigned `eyeId` on success.
- Returns `UHEYE_FAIL` (`-9999`) on failure.

> [!NOTE]
> Do not register boss-team eyes (such as `ArenaDemoneye`) using `DefineDemoneye`; register them via [`DefineBoss`](boss-api.md) instead.

---

## 3. Weighted Eye Morph Pools

Because Zandronum requires `MorphProjectile.PlayerClass` and `PowerMorph.PlayerClass` to be static DECORATE properties that cannot be modified at runtime, morph items (such as Money Bait or Money Bomb) select from pools of pre-defined concrete morph actors.

The engine provides three delivery modes:

| Mode Constant | Value | Description |
|---|---|---|
| `UHEM_SHOT` | `0` | Direct projectile actor (inherits `EyeMorphShot`). |
| `UHEM_BURST` | `1` | Area-of-effect blast actor (inherits `EyeMorphShotB`). |
| `UHEM_GIVER` | `2` | Direct inventory giver actor (inherits `EyeMorphGiver`). |

---

## 4. Pool API Functions

### Creating and Modifying Pools
```c
function int DefineEyeMorphPool(str pool)
function int SetEyeMorphPoolEntry(str pool, int eyeid, str shotactor, str burstactor, str giveractor, int weight)
```

1. **`DefineEyeMorphPool(pool)`**:
   - Declares a new named pool (case-insensitive).
   - Built-in pools include `"MoneyBait"` and `"MoneyBomb"`.
2. **`SetEyeMorphPoolEntry(...)`**:
   - Binds concrete effect actors for a specific `eyeid` within `pool`.
   - `weight`: Selection weight (`0..1000000`). Setting weight to `0` disables that entry.
   - At least one actor field must be non-empty. Empty fields are skipped when rolling for that specific delivery mode.
   - Repeating the same `(pool, eyeid)` replaces the existing row.

### Querying and Drawing from Pools
```c
function int FindEyeMorphPool(str pool)
function int GetEyeMorphPoolWeight(str pool, int eyeid)
function str GetEyeMorphPoolActor(str pool, int eyeid, int mode)
function str PickEyeMorphActor(str pool, int mode)
```

- **`PickEyeMorphActor(pool, mode)`**:
  Rolls a random actor from `pool` matching `mode` according to entry weights. Returns the selected actor class name, or `""` if the pool has no eligible candidates.

---

## 5. Custom Pool Example

To implement a custom polymorph potion item that turns targets into either your custom Demoneye or a Ghost:

```c
script "register_custom_potion_pool" OPEN {
  if (!UHInPlay()) terminate;

  int customEye = FindEyeByActor("MyDemoneyeActor");
  int ghostEye = FindEyeByActor("GhostDemoneye");

  DefineEyeMorphPool("MyPotionPool");

  // MyDemoneye has weight 3
  SetEyeMorphPoolEntry("MyPotionPool", customEye,
    "My_MorphShot", "My_MorphBurst", "My_MorphGiver", 3);

  // Ghost has weight 1
  SetEyeMorphPoolEntry("MyPotionPool", ghostEye,
    "Ghost_MorphShot", "Ghost_MorphBurst", "Ghost_MorphGiver", 1);
}
```

In your custom weapon or item script:

```c
script "use_custom_potion" (void) {
  str shotActor = PickEyeMorphActor("MyPotionPool", UHEM_SHOT);
  if (StrLen(shotActor) > 0) {
    SpawnProjectile(0, shotActor, 0, 0, 0, 1, 0);
  }
}
```

---

## 6. Modifying Built-In Pools

Addon packages can adjust the distribution of vanilla Money Bait bags or Money Bombs:

```c
script "adjust_moneybomb_pool" OPEN {
  if (!UHInPlay()) terminate;

  int customEye = FindEyeByActor("MyDemoneyeActor");
  if (customEye != UHEYE_FAIL) {
    // Add custom eye to MoneyBomb with weight 2
    SetEyeMorphPoolEntry("MoneyBomb", customEye,
      "", "My_MoneyBombBurst", "My_MoneyBombGiver", 2);
  }
}
```

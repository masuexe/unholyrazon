# Boss API

Unholy Razon provides a modder-facing API to define custom bosses. Custom bosses integrate with the Last Man Standing (LMS) round lifecycle, dynamic player-count health scaling, boss rage alerts, multi-phase portraits, and custom music tracks.

The public API functions live in [`uhadd.acs`](../src/acs_source/_includes/mod_api/uhadd.acs). A minimal working addon package is provided in [`examples/defineboss_addon`](../examples/defineboss_addon).

---

## 1. Registering a Boss

Custom bosses register using `DefineBoss`. Because Zandronum clients maintain their own local copy of the display tables to render HUDs and scoreboard icons, you must register the boss in **both** an `OPEN` script (server) and an `OPEN CLIENTSIDE` script (client).

```c
#library "MY_BOSSDEFS"
#include "zcommon.acs"
#import "uh_log.acs"   // Required: UHADD calls UH_Log()
#include "uhadd.acs"   // Case-sensitive include path

function void MyRegisterBosses(void) {
  int bossId = DefineBoss(
    -1,                           // id (-1 for auto-allocated custom ID)
    "MyBossActor",                // actor (DECORATE player class)
    "\cjMy Custom Boss",          // name (broadcast and HUD name)
    UHBOSS_POOL_COMMON,           // rarity / pool tier
    2000,                         // basehp (health with 1 player)
    300,                          // addhp (extra health per additional player)
    "",                           // exboss_baseactor (parent boss actor if EX)
    "UFACE26",                    // mugshot (HUD face lump or font name)
    "Press [Fire] to slash.",     // instruction (shown when morphed)
    "T.",                         // spawnmessagetype ("T." -> "The", or "")
    "has entered the arena!",     // spawnmessage
    "\crMY BOSS \cjIS ENRAGED!"   // ragewarningmessage (full rage message body)
  );

  // Optional: hook for post-morph weapon and extra-life setup
  SetBossMorphSetupByActor("MyBossActor", "uh_BossMorphSetup_MyBossActor");

  // Optional: spawn music track
  AddBossMusicByActor("MyBossActor", "M_MYTUNE", "My Track Title", "Game Name", "Artist", 1, 0);

  // Optional: enrage music track (phase 0 = default enrage)
  AddBossEnrageMusicByActor("MyBossActor", 0, "M_MYRAGE", "Enrage Theme", "Game Name", "Artist", 1, 0);
}

script "my_define_bosses" OPEN {
  if (!UHInPlay()) terminate;
  MyRegisterBosses();
}

script "my_define_bosses_cs" OPEN CLIENTSIDE {
  // Do NOT check UHInPlay() on pure clients
  MyRegisterBosses();
}
```

---

## 2. Parameter Specifications

```c
function int DefineBoss(
  int id,
  str actor,
  str name,
  int rarity,
  int basehp,
  int addhp,
  str exboss_baseactor,
  str mugshot,
  str instruction,
  str spawnmessagetype,
  str spawnmessage,
  str ragewarningmessage)
```

| Parameter | Type | Description |
|---|---|---|
| `id` | `int` | Slot ID. Pass `-1` to auto-allocate a custom ID (`-1, -2, …`). Nonnegative IDs (`0..199`) are reserved for vanilla/built-in bosses. |
| `actor` | `str` | DECORATE player actor class name. Comparisons are case-insensitive. Must be unique across all loaded PK3 packages. |
| `name` | `str` | Display name of the boss. Supports ACS color codes (e.g. `\cj`, `\cg`). |
| `rarity` | `int` | Random selection tier. See [Rarity Pools](#3-rarity-pools). |
| `basehp` | `int` | Base health granted to the boss when only 1 player is in the match. |
| `addhp` | `int` | Additional health granted per additional player. |
| `exboss_baseactor` | `str` | Actor class of the parent boss if this boss is an EX variant (`UHBOSS_POOL_EX`). Pass `""` otherwise. |
| `mugshot` | `str` | HUD mugshot font or graphic lump name (e.g. `"UFACE26"`). Must be provided explicitly for custom IDs. |
| `instruction` | `str` | Instructional hint text displayed to the morphed player upon entering the round. |
| `spawnmessagetype` | `str` | Prefix for the spawn broadcast. Pass `"T."` to format as `"The <name> <spawnmessage>"`, or `""` for direct `<name> <spawnmessage>`. |
| `spawnmessage` | `str` | Suffix text appended to the boss spawn broadcast (e.g. `"is causing havoc!"`). |
| `ragewarningmessage` | `str` | The complete body text shown when the boss reaches 100% rage. Pass `""` to use the default `<name> IS ENRAGED!`. Do not include `*DANGER*` frames or sound effects; the core HUD handles them automatically. |

### Return Value
- Returns the assigned `bossId` on success.
- Returns `UHBOSS_FAIL` (`-9999`) on failure (duplicate actor registration, capacity overflow, or invalid parameters).

---

## 3. Rarity Pools

The `rarity` argument determines how the boss is selected during random LMS rounds:

| Constant | Value | Description |
|---|---|---|
| `UHBOSS_POOL_NONE` | `0` | Excluded from normal random selection. Selectable only via forced RCON commands (`uh_sv_forcedboss1`), winner picks, or as an EX child. |
| `UHBOSS_POOL_COMMON` | `1` | Standard random boss pool. |
| `UHBOSS_POOL_RARE` | `2` | Rare boss pool. Triggered by pity counters or high player thresholds. |
| `UHBOSS_POOL_SPECIAL` | `3` | Special tier boss pool. |
| `UHBOSS_POOL_ULTRA` | `4` | Ultra tier boss pool. |
| `UHBOSS_POOL_EX` | `5` | EX upgrade variant. Replaces its parent boss (`exboss_baseactor`) after the parent has appeared a designated number of times. |

---

## 4. Health Calculation

Total health granted upon morphing scales linearly with the number of connected players:

$$\text{Total HP} = \text{basehp} + \text{addhp} \times (\text{player\_count} - 1)$$

For example, with `basehp = 2000`, `addhp = 300`, and 8 players in the game:
$$\text{Total HP} = 2000 + 300 \times 7 = 4100$$

---

## 5. Morph Setup Hook

If your boss requires multiple weapons, additional inventory tokens, or multi-life setup (e.g., `ExtraLife`), register a dedicated server-side morph setup script with `SetBossMorphSetupByActor`:

```c
SetBossMorphSetupByActor("MyBossActor", "uh_BossMorphSetup_MyBossActor");
```

Define the script with the required signature:

```c
script "uh_BossMorphSetup_MyBossActor" (int bossId, int tid) {
  SetActivator(tid);

  // Give auxiliary weapons
  GiveInventory("MyBossWeapon2_W", 1);
  GiveInventory("MyBossWeapon3_W", 1);

  // Grant extra lives or custom tokens
  GiveInventory("UnholyPowerLimit_F", 1500);
}
```

### Morph Setup Rules
1. **Server execution only**: Do not mark this script `CLIENTSIDE`.
2. **No Delays**: Never execute `Delay()` or blocking waits inside this setup script. It runs immediately after `MorphActor` and prior to the first weapon `Ready` state.
3. **Activator**: Always call `SetActivator(tid)` before giving inventory items.

---

## 6. Music Registration

Custom bosses support both spawn music and enrage music registered via `uhadd.acs`:

### Spawn Music
```c
function int AddBossMusicByActor(
  str actor,
  str lump,
  str title,
  str album,
  str artist,
  int weight,
  int optional)
```
- `weight`: Selection weight (minimum `1`). If multiple tracks are registered for the same actor, tracks are picked randomly according to weight.
- `optional`: Set to `0` to always include. Set to `1` if the music track is part of an optional external music pack gated by `uh_sv_optionalmusic`.

### Enrage Music
```c
function int AddBossEnrageMusicByActor(
  str actor,
  int phase,
  str lump,
  str title,
  str album,
  str artist,
  int weight,
  int optional)
```
- `phase`: Music phase index. Phase `0` is the default enrage track.
- Enrage tracks are triggered from DECORATE states using:
  ```c
  ACS_NamedExecuteAlways("ub_BossEnrageMusic", 0, phase)
  ```

---

## 7. Multi-Phase Stage Portraits

If the boss transitions across distinct phases (e.g. transforming upon entering rage or reaching low health), register phase mugshot variants using `DefineTeamPhasePresentation`.

See [`docs/boss-phase-portraits.md`](boss-phase-portraits.md) for full phase presentation details and inventory triggers.

---

## 8. Runtime Management (CRUD)

Server administrators and mod scripts can inspect or alter boss states dynamically:

| Function | Description |
|---|---|
| `UH_FindBossByActor(str actor)` | Resolves a player actor class to its integer boss ID. Returns `UHBOSS_FAIL` if not found. |
| `IsBossEnabledByActor(str actor)` | Checks if the boss is currently enabled in random pools. |
| `SetBossEnabledByActor(str actor, int enabled)` | Enables (`1`) or disables (`0`) a boss from random pools without unregistering it. |
| `UpdateBossDisplayByActor(...)` | Updates name, mugshot, instruction, spawn messages, or rage alert for an existing boss. |
| `UpdateBossStats(int id, int rarity, int basehp, int addhp)` | Updates pool rarity or health calculation values. |
| `RemoveBoss(int id)` | Removes a boss definition. Requires removing associated music rows and references first. |

Status codes returned by mutation functions:
- `UHDB_OK` (`0`): Operation succeeded.
- `UHDB_ERR_NOTFOUND` (`1`): Boss ID or actor not found.
- `UHDB_ERR_REFERENCED` (`3`): Cannot remove; boss is referenced by an active round, combo, or music definition.
- `UHDB_ERR_BADARG` (`5`): Invalid argument or IPC failure.

For more details on runtime table operations, see [`docs/modding/uhdt-identity-crud-contract.md`](modding/uhdt-identity-crud-contract.md).

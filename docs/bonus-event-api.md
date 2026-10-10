# Bonus Event API

Unholy Razon provides a modder-facing API to define custom **Bonus Events**. Bonus Events replace standard LMS rounds with special gamemode variants (such as Free-For-All deathmatches, One-vs-All boss challenges, eye parades, or custom mini-games).

The public API functions live in [`uhadd.acs`](../src/acs_source/_includes/mod_api/uhadd.acs). For server administration commands and CVARs, see [`docs/bonus-event-settings.md`](bonus-event-settings.md).

---

## 1. Registering a Bonus Event

Bonus Events register using `DefineBonusEvent`. Like other gameplay definitions, register in **both** an `OPEN` script (server) and an `OPEN CLIENTSIDE` script (client) so client HUDs and scoreboard elements can resolve event titles and instructions locally.

```c
#library "MY_EVENTDEFS"
#include "zcommon.acs"
#import "uh_log.acs"   // Required: UHADD calls UH_Log()
#include "uhadd.acs"   // Case-sensitive include path

// Lifecycle Callbacks (defined on the server)
script "mybonus_start" (int eventId, int arg1, int arg2) {
  // Runs ONCE per round when the event begins.
  // Initialize round state, roll any per-round random values and freeze them.
  // Return immediately; launch persistent watchers in separate scripts.
}

script "mybonus_rebuild" (int eventId, int tid, int reason) {
  // Runs once per player per life (spawn and respawn).
  // MUST BE IDEMPOTENT. Give event weapons, inventory tokens, or apply rules.
  SetActivator(tid);
  GiveInventory("MyEventWeapon_W", 1);
}

script "mybonus_end" (int eventId, int result, int unused) {
  // Runs at most once per round when the event concludes.
  // Clean up event-owned inventory, tokens, and spawned actors.
  // Do NOT decide the winner and never call Exit_Normal here.
}

function void MyRegisterBonusEvents(void) {
  int eventId = DefineBonusEvent(
    -1,                           // id (-1 for auto-allocated custom ID >= 200)
    "my_custom_event",            // stem (stable unique cross-PK3 identifier)
    "\cgCustom Chaos FFA",        // name (broadcast and HUD name)
    "M_MYBGM",                    // music (music lump name)
    "Track Name",                 // title
    "Game Name",                  // album
    "Artist",                     // artist
    "misc/MyEventStart",          // sound (startup sound effect)
    "\cgCustom Chaos Battle!",    // hud1 (first line of HUD intro)
    "\ccLast player standing wins.", // hud2 (second line of HUD intro)
    "mybonus_start",              // startCallback
    "mybonus_rebuild",            // rebuildCallback
    "mybonus_end",                // endCallback
    0, 0, 0,                      // arg1, arg2, arg3 (custom callback arguments)
    UHBE_FLAG_FFA,                // flags
    1,                            // weight (selection weight; 0 = force-only)
    2,                            // minPlayers (minimum player count required)
    0                             // maxPlayers (0 = no upper limit)
  );

  // Optional: link an EX upgrade after 3 appearances
  // SetBonusEventEX("my_custom_event", "my_custom_event_ex", 3);
}

script "my_define_events" OPEN {
  if (!UHInPlay()) terminate;
  MyRegisterBonusEvents();
}

script "my_define_events_cs" OPEN CLIENTSIDE {
  // Do NOT check UHInPlay() on clients
  MyRegisterBonusEvents();
}
```

---

## 2. Parameter Specifications

```c
function int DefineBonusEvent(
  int id,
  str stem,
  str name,
  str music,
  str title,
  str album,
  str artist,
  str sound,
  str hud1,
  str hud2,
  str startCallback,
  str rebuildCallback,
  str endCallback,
  int arg1,
  int arg2,
  int arg3,
  int flags,
  int weight,
  int minPlayers,
  int maxPlayers)
```

| Parameter | Type | Description |
|---|---|---|
| `id` | `int` | Slot ID. Pass `-1` to auto-allocate a custom ID (`>= 200`). IDs `0..199` are reserved for built-in events. |
| `stem` | `str` | Case-insensitive unique identifier (e.g. `"my_custom_event"`). Stems are the stable cross-PK3 identity; never hardcode auto-assigned numeric IDs. |
| `name` | `str` | Display name formatted with optional ACS color codes. |
| `music` | `str` | BGM lump played during the round. |
| `title`, `album`, `artist` | `str` | Music track metadata for the HUD music ticker. |
| `sound` | `str` | Sound effect lump played at round start. |
| `hud1`, `hud2` | `str` | Two lines of banner text displayed on players' screens when the event begins. |
| `startCallback` | `str` | Named script executed once on round start. See [Callback Contract](#4-callback-contract). |
| `rebuildCallback` | `str` | Named script executed on each player spawn/respawn. |
| `endCallback` | `str` | Named script executed on round end. |
| `arg1`, `arg2`, `arg3` | `int` | Custom integers passed to callbacks or queried via `UH_GetBonusEventArg()`. |
| `flags` | `int` | Gamemode flags. See [Event Flags](#3-event-flags). |
| `weight` | `int` | Random selection weight (`0..1000000`). `0` disables random selection (event can only be triggered via `uh_sv_forcedbonusevent` or EX upgrade). |
| `minPlayers` | `int` | Minimum active players required for random selection. |
| `maxPlayers` | `int` | Maximum active players allowed for random selection. `0` indicates no maximum. |

- Returns the assigned `eventId` on success.
- Returns `UHBE_FAIL` (`-9999`) on failure.

---

## 3. Event Flags

Flags define how the core engine sets up player teams and protections before executing callbacks:

| Constant | Value | Description |
|---|---|---|
| `UHBE_FLAG_FFA` | `1` | Free-For-All. Clears team protections and enables infighting across all participants. |
| `UHBE_FLAG_ONEVSALL` | `2` | One-vs-All. One player is selected as the target/boss side; all other players fight them. |
| `UHBE_FLAG_ALL_EYE` | `4` | All players transform into Demoneyes. |
| `UHBE_FLAG_EYE_TEAM` | `8` | Eye team gamemode variant. |
| `UHBE_FLAG_MULTITEAM` | `16` | Multi-team battle format. |

---

## 4. Callback Contract

All three callbacks are plain **server-side scripts** (never mark them `CLIENTSIDE`). Script names should include an addon prefix to prevent symbol collisions.

### 1. Start Callback (`startCallback`)
```c
script "mybonus_start" (int eventId, int arg1, int arg2)
```
- Runs once per round when the bonus event begins.
- Initialize round-level state here. If your event uses per-round randomized values (e.g., selecting a random weapon or boss), roll the random values here and store them in map variables.
- **Must return quickly**: Do not run long loops or `Delay()` calls in the start script. If your event needs a continuous watcher, spawn an independent watcher script.

### 2. Rebuild Callback (`rebuildCallback`)
```c
script "mybonus_rebuild" (int eventId, int tid, int reason)
```
- Runs once per player per life (at round start and upon respawn).
- **Must be idempotent**: Only read frozen round state.
- Set the activator with `SetActivator(tid)` before granting weapons, tokens, or status effects.

### 3. End Callback (`endCallback`)
```c
script "mybonus_end" (int eventId, int result, int unused)
```
- Runs at most once per round when the round finishes.
- Clean up items, tokens, or custom entities that your event spawned.
- The `result` parameter indicates how the round finished:
  - `UHBE_RESULT_DRAW` (`0`): Time limit reached or simultaneous death.
  - `UHBE_RESULT_SURVIVOR` (`1`): Survivors won.
  - `UHBE_RESULT_BOSS` (`2`): Boss or event target won.
  - `UHBE_RESULT_ABORTED` (`3`): Round aborted early by server or error.
- **Never call `Exit_Normal` or force round ends** inside the end callback; the LMS engine core manages map flow.

---

## 5. EX Event Progression

You can designate an event as an "EX upgrade" of another event using `SetBonusEventEX`:

```c
SetBonusEventEX("base_event_stem", "ex_event_stem", 3);
```

- When `base_event_stem` is randomly selected `3` times, the 4th occurrence automatically upgrades to `ex_event_stem`.
- Both events must be referenced by their unique `stem`.
- Progress is tracked on the server and persists across map changes.

---

## 6. Runtime Queries

Mod scripts can query the active bonus event at runtime:

| Function | Description |
|---|---|
| `UH_IsActiveBonusEvent()` | Returns `1` if a bonus event is currently running, `0` otherwise. |
| `UH_GetActiveBonusEvent()` | Returns the active event's integer ID, or `UHBE_FAIL` if none. |
| `UH_FindBonusEventByStem(str stem)` | Resolves a stem string to its event ID. |
| `UH_GetBonusEventArg(int eventId, int argIndex)` | Returns the value of `arg1`, `arg2`, or `arg3` (index `0..2`). |

For host configuration, player count overrides, and export diagnostics, consult [`docs/bonus-event-settings.md`](bonus-event-settings.md).

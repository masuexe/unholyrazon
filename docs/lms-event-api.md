# LMS Event API

The LMS event registry defines the reward given to the last survivor and its
rare and Bad LMS variants. Bad LMS uses the selected event's penalty metadata
and effects when the round's repeated-last-survivor counter reaches its limit.
Registration stores data; it does not grant items or trigger an event.

The public API is in [`uhadd.acs`](../src/acs_source/_includes/mod_api/uhadd.acs).
The shared registry is in [`uhdt.acs`](../src/acs_source/_imports/uhdt.acs), and
built-ins are grouped by event ID in
[`uh_lmsdefs.acs`](../src/acs_source/systems/lms/definitions/uh_lmsdefs.acs).
A complete addon is in [`lms_penalty_addon`](../examples/lms_penalty_addon).

## Defining an event

```c
int DefineLMSEvent(int id, str stem,
    str message, str raremessage, str penaltymessage,
    str icon, str rareicon, str penaltyicon,
    int flags, int penaltyflags, int weight);
```

| Parameter | Meaning |
|---|---|
| `id` | Built-ins occupy `0–12`. Pass `-1` to allocate the next unused ID, currently starting at `13`, or supply a coordinated ID within `0–255`. |
| `stem` | Unique, nonempty stable identifier. Matching is case-insensitive. Use an addon-specific prefix. |
| `message`, `raremessage`, `penaltymessage` | HUD text for normal, rare and Bad LMS variants. ACS color escapes are supported. |
| `icon`, `rareicon`, `penaltyicon` | Fonts used to draw the variant's event icon (`A` glyph). Empty normal/rare fonts fall back to `LMS_E#<id>` / `LMS_X#<id>`. Supply the penalty font explicitly. |
| `flags` | `0`, or `UHLMS_FLAG_DUALRUNE` to grant a second rune. |
| `penaltyflags` | `0`, `UHLMS_PENALTY_CLEAR_ITEMS`, or `UHLMS_PENALTY_USE_DEFAULT`. See below. |
| `weight` | Random selection weight, `0–1000000`. `0` makes the event force-only. |

Success returns the event ID; failure returns `UHLMS_FAIL` (`-9999`). Repeating
an explicit ID with the same stem updates its metadata. It does not re-enable
a disabled event or remove drop rows. `DefineLMSEvent(-1, ...)` allocates a new
ID, so a repeated stem fails; resolve an existing stem before re-registering.
Removed IDs and stems remain reserved.

The server and each client allocate their own registry. Auto IDs are local
registration results; use stems for addon references and resolve an ID in the
process that needs it.

## Adding rewards and penalties

```c
int AddLMSEventDrop(str stem, str itemactor, int amt, int rare);
int AddLMSEventPenaltyDrop(str stem, str actor, int amt, int target);
```

Register the event first. `rare` is `0` for normal rewards and `1` for rare
rewards. All matching rows are granted; the rows are not a random item pool.
Amounts must be at least `1`. Actors must exist in the loaded packages; these
APIs accept actor names without validating their existence at registration.

Penalty recipients are `UHLMS_PENALTY_SURVIVOR` (the last survivor) or
`UHLMS_PENALTY_BOSSES` (each connected player on the Unholy Boss side). Ordinary
inventory actors are given as items. Use an `Auto*`, power or giver actor when
the effect should execute immediately.

Success returns a drop row index, including `0`; failure returns `UHLMS_FAIL`.
Repeating the same event, actor, amount and variant/target returns the existing
row without granting twice. A different amount creates an additional row.
Normal, rare and penalty rows share a capacity of `512`.

`UHLMS_PENALTY_CLEAR_ITEMS` clears registered held items from the survivor
before penalty grants. Flag `0` with no penalty drops adds no item effects.
Rune reversal remains shared round behavior: in Bad LMS the Boss side receives
the rolled rune(s), including the second rune for `UHLMS_FLAG_DUALRUNE`.

`UHLMS_PENALTY_USE_DEFAULT` selects the shared fallback metadata and drops;
it ignores the event's own penalty fields and rows. Use it alone, without
combining it with `UHLMS_PENALTY_CLEAR_ITEMS`.

```c
int SetDefaultLMSEventPenalty(str message, str icon, int flags);
AddLMSEventPenaltyDrop("", "PowerLMSBadProtection", 1,
    UHLMS_PENALTY_SURVIVOR);
```

Stem `""` identifies the shared fallback when adding penalty drops. Default
metadata accepts flags `0` or `UHLMS_PENALTY_CLEAR_ITEMS`; successful registration
returns `-1`, failure returns `UHLMS_FAIL`. The built-in fallback grants bad
protection and `LMSBadGuyAppears_P`. Updating metadata retains existing drops.

## Registering an addon

Include `uhadd.acs`, import `uh_log.acs`, and register without delays in both
server `OPEN` and `OPEN CLIENTSIDE`. The server grants effects; clients need
local metadata to draw event icons. Definitions are rebuilt every map.

```c
#library "MYLMS"
#include "zcommon.acs"
#import "uh_log.acs"
#include "uhadd.acs"

function void RegisterMyLMS(void) {
  int id = UH_FindLMSEventByStem("myaddon_wasps");
  if (id == UHLMS_FAIL) id = -1;
  id = DefineLMSEvent(id, "myaddon_wasps",
    "A helpful gift!", "A better gift!", "The bosses get the gift!",
    "LMS_E#4", "LMS_X#4", "LMS_B#4", 0, 0, 1);
  if (id == UHLMS_FAIL) return;

  AddLMSEventDrop("myaddon_wasps", "WaspBombItem", 3, 0);
  AddLMSEventDrop("myaddon_wasps", "GoldenWaspBombItem", 1, 1);
  AddLMSEventPenaltyDrop("myaddon_wasps", "GoldenWaspBombItem", 1,
    UHLMS_PENALTY_BOSSES);
}

script "myaddon_register_lms" OPEN {
  if (!UHInPlay()) terminate;
  RegisterMyLMS();
}

script "myaddon_register_lms_cs" OPEN CLIENTSIDE {
  RegisterMyLMS();
}
```

Compile to `acs/MYLMS.o`, add `MYLMS` to the addon's `LOADACS`, and load it after
Unholy Razon. Use the include search paths documented in
[`tools/README.md`](../tools/README.md#rebuilding-acs-and-the-pk3-locally).

## Updating, disabling and removing

```c
int UpdateLMSEvent(int id,
    str message, str raremessage, str penaltymessage,
    str icon, str rareicon, str penaltyicon,
    int flags, int penaltyflags, int weight);
int UpdateLMSEventByStem(str stem,
    str message, str raremessage, str penaltymessage,
    str icon, str rareicon, str penaltyicon,
    int flags, int penaltyflags, int weight);
```

Updates replace all metadata and retain identity, enabled state and drop rows.
Apply metadata changes on each process that displays them.

| API | Behavior |
|---|---|
| `SetLMSEventEnabled(id, enabled)` | Enable or disable random selection. |
| `EnableLMSEvent(id)` / `DisableLMSEvent(id)` | Convenience wrappers. |
| `SetLMSEventEnabledByStem(stem, enabled)` | Resolve the stem, then change enabled state. |
| `RemoveLMSEvent(id)` / `RemoveLMSEventByStem(stem)` | Tombstone an event. Refused while any normal, rare or penalty drop row references it. |

These operations return `UHDB_OK` (`0`) on success, otherwise an existing
`UHDB_ERR_*` code such as `NOTFOUND`, `BADARG` or `REFERENCED`. There is no public
drop-removal API; disable an event with registered drops instead. Disabled
events remain defined and can still be explicitly forced.

## Queries and forcing

| API | Result |
|---|---|
| `UH_FindLMSEventByStem(stem)` | Local event ID, or `UHLMS_FAIL`. |
| `UH_IsLMSEventDefined(id)` / `IsLMSEventEnabled(id)` | Whether the event is defined / enabled. Disabled events count as defined. |
| `GetDefinedLMSEventCount()` / `GetEnabledLMSEventCount()` | Registry counts. |
| `UH_GetLMSEventMessage(id)` / `UH_GetLMSEventraremessage(id)` | Normal / rare text. |
| `UH_GetLMSEventIcon(id)` / `UH_GetLMSEventrareicon(id)` | Normal / rare icon font. |
| `UH_GetLMSEventFlags(id)` | Ordinary flags. |
| `UH_GetLMSEventPenaltyMessage(id)` / `UH_GetLMSEventPenaltyIcon(id)` | Effective penalty text / font, including fallback resolution. |
| `UH_GetLMSEventPenaltyFlags(id)` | Effective penalty flags after fallback resolution. |
| `UH_PickLMSEvent()` | Weighted enabled event ID, or `UHLMS_FAIL` if none is eligible. |

On the server, set `uh_sv_lmsevent` to a defined event ID to override the next
LMS selection. The round core consumes and clears this override. For addon
events, resolve their stem on the server rather than assuming an auto ID.
Bad LMS is still controlled by the repeated-last-survivor counter and
`uh_sv_lmscountlimit`; forcing an event ID does not itself force its penalty.

## Music and API migration

`AddLMSMusicByStem(stem, lump, title, album, artist, weight, optional)` attaches
music to a registered event. `SetLMSMusicEnabledByStem(stem, lump, enabled)` and
`RemoveLMSMusicByStem(stem, lump)` manage those tracks. Music registration is
separate from the event's item and penalty definitions.

`DefineLMSEvent`, `UpdateLMSEvent` and `UpdateLMSEventByStem` now take
`penaltymessage`, `penaltyicon` and `penaltyflags`. Older addon sources must add
these parameters in the positions shown above and recompile against the
current UHADD. Per-event `SetLMSEventPenalty` has been replaced by those fields;
`SetDefaultLMSEventPenalty` configures only the shared fallback.

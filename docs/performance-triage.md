# Frame-rate investigation: normal roles versus Demoneye

## Observation and limits

Player report: frame rate is low throughout play, but normal while playing a
Demoneye. The affected package, engine, renderer, player count, exact classes,
and measured FPS have not been supplied. This is a source audit of the current
workspace, not a reproduction or a measured root cause. Existing uncommitted
Void Walker changes were left untouched.

Compare roles in the same match, position, view direction, resolution, and
addon stack. A role change late in a round also changes the number of living
players and effects; that alone can explain an apparent improvement.

## Candidates, in investigation order

### 1. Teammate display and its incoming snapshots

`src/acs_source/unholy/uh_teaminfo.acs`, `UH_AreDisplayTeammates`, excludes Eyes
from display teams in ordinary LMS. Survivors see Survivors; Bosses see Bosses.
The native consumer in
`src/acs_source/v6b_overrides/corescripts/systems/ui/UITEAMIT.acs`,
`core_teaminfo`, scans player slots and draws each eligible row's portrait,
name, location, health, and weapon. The base v6c `ASSTDIS` library calls UI
hooks every tic. The UH fallback and optional UIX are additional consumers.

`UH_Ti_RefreshStats` sends two numeric script deliveries per authorized
subject/viewer on every visit, even when their values did not change. Eight
subjects are visited per tic, covering 64 slots every eight tics. At 35 tics
per second this is 8.75 deliveries per second per authorized subject/viewer
pair, before metadata or other messages. A viewer authorized for 32 subjects
receives about 280 such numeric deliveries per second. These are call counts,
not measured packet counts, bytes, or CPU time. Weapon metadata is already
change-gated. Eye clients ordinarily receive their own row but no teammates.

This fits a role-dependent client cost. It fits a solo Boss less well, because
that Boss also has no other Boss rows. Ask specifically whether solo Boss play
has the same slowdown. Server work continues when one player changes role;
Eye FPS recovering does not by itself prove a server bottleneck.

### 2. Player automap markers update even with the automap closed

`src/acs_source/hud/automap_markers.acs`, `uh_AutomapMarkers`, has no automap-open
gate. After its 70-tic startup delay it visits all 64 slots every tic. For each
visible living player it keeps one icon and 20 direction-dot actors, and calls
`Warp` for every dot every tic. Visibility uses the teammate policy above.

That is 700 dot warps per second per visible player: 22,400 for 32 visible
living players. An Eye normally has only its own markers; a lone Boss likewise
normally has only its own. These are source-derived work counts, not measured
frame-time costs. Closing the automap does not disable this work. The item
marker option is a separate feature and does not disable these player dots.

### 3. Common HUD inventory work

`src/acs_source/hud/class_bars_generated.acs`, `UHBar_ClearAll`, resets all
generated selectors on each bar-clear callback. The override `BARCLEAR`
dispatches that callback, and base v6c `ASSTDIS` runs bar clear/setup every tic.
`SetActorInventory` in `_imports/uh_acsutils.acs` first queries inventory even
when the desired amount is already zero. Engine `AActor::FindInventory` in
`p_mobj.cpp` searches a linked inventory list.

This is background work worth profiling, especially for bodies with many
inventory entries. It also runs for Eyes, so it explains the report only if
inventory size or other HUD paths differ enough. Do not remove generated
selectors by hand; any eventual fix belongs in the generator or its design.

## First test on the affected client

Record the original values of the following options. In the same scene and
role, disable all installed teammate-display consumers:

```text
mm8bdm_teaminfo 0
uh_cl_teaminfo 0
UIX_CL_TEAMINFO 0
```

Use the UIX command only if UIX is installed. Wait a few seconds for user
settings and snapshots to settle, then compare FPS. Restore the original
values after the test. Disabling only the native consumer can enable the UH
fallback, so test both switches together.

If FPS recovers, re-enable one consumer at a time. This initial test changes
both drawing and snapshot eligibility; it does not distinguish their costs.
If FPS stays low, the automap marker loop is still running. A temporary test
addon/build must suppress that loop **and clean up its existing marker actors**
to isolate it. No existing player-marker switch was found in this audit.

For comparable 20-second role samples, run these on the affected client's
console, first clearing counters, then returning to gameplay before sampling:

```text
acsprofile clear
```

After 20 seconds:

```text
acsprofile total 30
acsprofile avg 30
scriptstat
```

Save the output for a Survivor, an Eye, and a solo Boss. The commands are
verified in the local Zandronum source (`p_acs.cpp`). `acsprofile` counts ACS
instructions, not elapsed milliseconds; native inventory queries, rendering,
networking, and `Warp` can cost much more than their instruction counts imply.
`scriptstat` lists active scripts; it does not time them. `stat think` reports
local thinker time in milliseconds (`dthinker.cpp`); it is not total frame
time or the remote dedicated server's time.

If the display test does not help, compare the smallest v6c base/mod stack with
the affected stack, then isolate weapon sprites and HUD drawing. Pure renderer
or addon costs remain possible. No gameplay or performance change is justified
until one of these controlled comparisons identifies a contributing system.

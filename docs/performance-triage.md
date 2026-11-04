# Frame-rate investigation: normal roles versus Demoneye

## Observation and limits

Player report: frame rate is low throughout play, but normal while playing a
Demoneye. The affected package, engine, renderer, player count, exact classes,
and measured FPS have not been supplied. This is a source audit of the current
workspace, not a reproduction or a measured root cause. Existing uncommitted
Void Walker changes were left untouched during the initial audit.

Follow-up reported on 2026-11-04: disabling both `mm8bdm_teaminfo` and
`uh_cl_teaminfo` restores about 200 FPS; enabling teaminfo yields about
160–170 FPS. This supports a teaminfo-related performance cost in the tested
setup, assuming comparable scenes. At those rates, nominal frame duration
changes from 5 ms to 5.88–6.25 ms. It does not identify a specific component,
and 200 FPS may itself be a frame-rate cap. These are player-reported readings,
not measurements reproduced by this audit.

Second follow-up: enabling "legacy teaminfo" also reaches 200 FPS. If this
actually draws comparable teammate rows, it strengthens attribution to the
new native display path rather than generic team-info functionality. Confirm
that rows are visible, not merely that a menu switch is enabled:

- v6c's `MENUDEF.txt` labels `cl_drawcoopinfo` as "Legacy Coop Info".
- Engine `HUD_DrawCoopInfo` (`g_shared/st_hud.cpp`) requires a cooperative or
  native team mode and does not itself draw ordinary LMS logical UH teams.
- UH's `uh_assist_teaminfo` also checks `cl_drawcoopinfo`, but additionally
  requires `uh_cl_teaminfo`. With native display off, this UH text fallback
  reads the same authorized health/ammo snapshot arrays as the adapted native
  display, without the native portrait and layered bar rendering.

If the UH text fallback is visibly working at 200 FPS with comparable subjects,
snapshot delivery alone is unlikely to explain the entire 160–170 FPS result.
Prioritize the native row drawing, its portrait resolution and query bridges.
If both `mm8bdm_teaminfo` and `uh_cl_teaminfo` remain zero and only
`cl_drawcoopinfo` is enabled in ordinary LMS, there may be no displayed rows or
teaminfo snapshot consumer at all; that is still effectively the off baseline.
Neither interpretation yet distinguishes upstream v6c row rendering from UH's
changes to that renderer.

Further player clarification: enabling the menu's Legacy Coop Info really
does display simple teammate information at 200 FPS. The exact active consumer
and remaining switch values were not captured, so shared snapshot eligibility
must not be assumed from the menu label alone.

The player also reports that the new display, with both portraits and weapons
enabled, reaches 200 FPS when there are only three teammates. This suggests a
cost that grows with displayed rows or total players. It does not establish a
three-row threshold, and a 200 FPS ceiling can hide smaller costs.

Next controlled test: in the same crowded match and view, record the original
`mm8bdm_teaminfomaxamount`, then set it to `3`. Restore the original value
after sampling. If FPS recovers, prioritize per-row drawing and queries. If
not, investigate work tied to total player count, including scans and snapshot
handling. This display limit is a diagnostic comparison, not a confirmed fix.
No upstream v6c versus UH attribution has yet been established.

## Attribution after the switch comparison

The two switches do not provide independent attribution to upstream v6c and
Unholy. The loaded `UITEAMIT` library is an Unholy override of v6c's native
team display. A normalized source comparison (ignoring CRLF differences)
shows that most row layout/drawing remains upstream code, but UH adds:

- Script bridges for teammate permission, snapshot validity, health and ammo.
- Snapshot weapon resolution, including cached weapon-table lookup misses.
- A `MUGSHOTS` override which resolves UH portraits before the upstream cache.
  Its UH presentation lookup scans registered rows by actor name.
- Server-owned health/weapon/ammo snapshot deliveries, separate from drawing.

The native display suppresses the UH fallback while active. Thus turning both
switches off can stop drawing and, if no other consumer is eligible, stop the
client's numeric teammate snapshots too. The observed gain alone cannot assign
the cost to upstream drawing, UH adaptation, or snapshot handling. Automap
player markers and common bar clearing do not consult either switch, so their
independent background work is now a lower-priority explanation of this toggle
difference.

To isolate the layers, compare these settings in one unchanged scene, with
UIX teaminfo disabled if installed and the same displayed player count:

| Sample | `mm8bdm_teaminfo` | `uh_cl_teaminfo` | `mm8bdm_teaminfoalpha` | Intended comparison |
| --- | --- | --- | --- | --- |
| A | 0 | 0 | original | Neither consumer; baseline |
| B | 0 | 1 | original | UH fallback plus snapshots |
| C | 1 | 0 | original, nonzero | Adapted v6c display plus snapshots |
| D | 1 | 0 | 0 | Snapshots remain eligible; native drawing exits early |

The server must enable `mm8bdm_sv_teaminfo` for C/D. For B, `cl_drawcoopinfo`
must be on and `sv_nocoopinfo` off. Verify the intended display actually
appears in B/C. Preserve and restore all original values. Wait for settings
to reach the server before sampling. D also retains any native work outside
the drawing entry point; it is not a claim of zero teaminfo computation.

If D is close to A but C is slower, prioritize the native display path and
its UH queries over snapshot traffic. Compare B/C to establish which renderer
is more expensive under the same authorization policy. If D is also slower
than A, snapshot receipt or other enabled-path work contributes. None of these
comparisons alone proves an upstream v6c defect: that requires an upstream-only
comparison with comparable rows, renderer, options, and scene. Plain stock LMS
without UH team adaptation may draw no rows at all and is not a fair baseline.

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

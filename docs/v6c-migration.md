# MM8BDM v6c migration

Started on 2026-10-28. Startup, class-slot inheritance, movement and native HUD
paths have focused v6c verification. Full-round, new map/item and 64-slot
coverage remain pending; these focused checks do not establish the whole port.

## Baseline and scope

- Recovery baseline: `a3fd10b5`, pushed to `origin/master`, including the
  CXAirMan remote energy-meter fix.
- Working branch: `migration/v6c`. Target a v6c migration beta, followed by a
  4.0.0 RC after multiplayer regression tests pass.
- Read-only reference: `../references/for_8bdm-v6c/mm8bdm-v6c/`.
- Base package: `../wads/mm8bdm-v6c.pk3`.
- CBM v9gh_ remains a reference for inherited code. A newer CBM release is
  not a prerequisite. Full class rewrites are outside this migration.

## Immediate milestone: restore startup

Reproduce the failure with the smallest v6c load before broader system ports.
Use `tools/mm8bdm-v6c.launch.json`: `megagame.wad`, v6c, then `out/build.pk3`.
Do not carry v6b miscfixes or standalone UIX into this profile without auditing
whether v6c already provides their changes.

Capture each actual startup error, identify the conflicting source definition,
and fix dependencies in load order. Do not remove a UH feature merely to silence
a parser error. Recompile affected ACS and repack before testing each change.
A map that loads proves startup only; it does not prove gameplay compatibility.

## Confirmed merge points

1. **Data registration must migrate as a unit.** v6c DTADD sets an API version
   and uses `_8bdm_*` mailboxes for new calls. DTADDR supports both old and new
   callers. UH overrides the old DTADDR and CORE8BDT, so updating only one side
   can break registration. Preserve UH capacities and custom registration data.
2. **Class slots require an inheritance audit.** v6c connects ClassBase2 to
   ClassBaseSlot100; the initial UH implementation connected to ClassBaseSlot50.
   The endpoint is now updated to ClassBaseSlot100. Preserve the UH
   damage, pain, movement, and death layers while checking all new slot labels
   and overrides. Changing the final number alone cannot establish correctness.
3. **Jump handling uses hooks.** v6c JUMPCANC dispatches HF_JUMP_* hooks, while
   UH overrides the previous implementation. Port UH movement features onto
   the new implementation without suppressing base-game hooks.
4. **HUD and UI have separate integration points.** v6c loads UIWEPBAR,
   UITEAMIT, UIINVWHL, and other built-in UI libraries. UH shadows standalone
   UIX v3bh libraries. Check actual library names, APIs, teammate filtering,
   and portrait consumers rather than assuming those shadows cover the new UI.
5. **Old fixes need individual review.** Establish which v6b miscfixes are
   already included in v6c before retaining any such override.

## ACS override inventory

Match each override filename uniquely in both reference trees and compare
text lines after decoding. Of 22 matching files, 18 changed upstream. This
measures audit scope, not confirmed failures or estimated effort.
`uh_corereplace.acs` has no same-name upstream source and needs a separate audit.

| Override | Upstream comparison | v6b to v6c lines |
|---|---|---|
| `8BDT.acs` | Changed | 817 → 875 |
| `8BDMDEFS.acs` | Changed | 520 → 678 |
| `8BDMEFCT.acs` | Changed | 138 → 190 |
| `8BDMHELP.acs` | Changed | 222 → 222 |
| `8BDMINFO.acs` | Changed | 85 → 92 |
| `8BDMLIB.acs` | Identical | 15 → 15 |
| `8BDMMATH.acs` | Changed | 215 → 211 |
| `8BDMVARS.acs` | Changed | 12 → 13 |
| `COLOFUNC.acs` | Identical | 34 → 34 |
| `MEGAPAL.acs` | Identical | 297 → 297 |
| `ASSTLIB.acs` | Changed | 102 → 54 |
| `BARLIB.acs` | Changed | 150 → 199 |
| `DTADD.acs` | Changed | 348 → 397 |
| `BARCLEAR.acs` | Changed | 51 → 106 |
| `BARHNDLE.acs` | Changed | 98 → 106 |
| `DTADDR.acs` | Changed | 507 → 661 |
| `COLOTRNS.acs` | Changed | 77 → 77 |
| `JUMPCANC.acs` | Changed | 238 → 75 |
| `PROJTRAN.acs` | Changed | 50 → 99 |
| `TEAMCOL.acs` | Changed | 480 → 475 |
| `TOTLTRAN.acs` | Identical | 264 → 264 |
| `FOOTCHEC.acs` | Changed | 59 → 93 |


## Subsequent milestones

1. Merge shared headers, 8BDT, and DTADD/DTADDR together. Preserve UH tables,
   capacities, imports, and shadow library names. Resolve the class-slot chain.
2. Port jump/movement, translations, bars, and built-in UI integration. Record
   whether each existing override is retained, ported, or removed and why.
3. Verify class selection, boss morphing, weapons/items, death/revival, a full
   LMS round, and map changes. Exercise new maps and items in the engine.
4. Test a dedicated server and remote clients: energy bars, spectator health,
   teammate bars, identities/portraits, reconnects, and map changes. Run the
   existing CXAirMan regression with the v6c profile.
5. Publish a migration beta. Enter RC only when serious defects are resolved
   and the feature scope is stable.

## Validation boundaries

The pre-migration smoke gate passed 31 checks against v6b. It does not establish
v6c compatibility. Record the base package, launch profile, compiled objects,
and load order for each later validation. Existing test defaults remain v6b
until they are explicitly migrated.

## Startup milestone results (2026-10-28)

The initial minimal load failed with four duplicate constants and five duplicate
inventory classes now supplied by v6c. After resolving those definitions, the
old CORE8BDT/DTADDR shadows prevented hook registration and produced assist
script stack/VM errors. The old PROJTRAN shadow also lacked core_projtransgive.

Completed changes:

- Use the base-game constants and property counters after checking their values
  and capacities. Use the base DefaultPropertiesSet_F marker.
- Base CORE8BDT, DTADDR, DTADD, and shared definitions on v6c. Preserve UH color
  modes, the Endless Ammo rune, and getPitCount. v6c provides 500 item slots,
  exceeding the former UH limit of 256.
- Keep getPitCount after upstream declarations. Pin the missing ACC header's
  RejumpDelay value to engine src/p_acs.h (150) under a UH-specific macro.
- Replace UH's writes to the removed defaultproperties array with the v6c
  core_defineaproppowers initializer. The checked v6c implementation does not
  add the old spawn-invulnerability side effect.
- Add the new party-ball weight argument (0) to the two existing assist-item
  registrations; this keeps those UH entries out of that new pool.
- Port PROJTRAN to the v6c entry points and fourth translation argument while
  retaining the UH class-palette toggle exception and Decoy rail helper.
- Add tools/mm8bdm-v6c.launch.json without v6b fixes or standalone UIX.

Validation:

- All project ACS libraries compile with native ACC.
- The existing 31-check smoke gate passed. Its environment defaults and frozen
  asset allowlists still target v6b and need a later tooling migration.
- The v6c profile passes path resolution. The actual MCP smoke run with that
  profile reports 0 compile/fatal errors, returns a live player state at
  (96, -320, -32), and quits cleanly on MM2DW1.
- Runtime command:
  `ZANDRONUM_LAUNCH_PROFILES=tools/mm8bdm-v6c.launch.json node tools/mcp/smoke-test.mjs --profile mm8bdm-v6c-smoke --json`
- The rebuilt out/build.pk3 is now a v6c migration artifact. Do not test it with
  the unchanged v6b profile. Rebuild the recovery commit to obtain a v6b package.

Still pending after this startup checkpoint: jump hooks, bar APIs, built-in UI,
full-round behavior, new maps/items, and dedicated-client regression tests.
These startup changes are included in the first migration checkpoint.


## Training fatal-damage crash (2026-10-28)

The maintainer reported an immediate Windows exit (code 5) while playing Igniter
against Juggernaut in TRAINING. It also occurred without addons. Local Linux
checks confirmed nonlethal damage was safe, then reproduced the crash with a
single lethal JuggerShot damage call in the minimal v6c load. Removing the death
tip library did not prevent it. GDB captured a native stack overflow with
repeated weapon-state dispatch and conditional jumps.

v6c inserts a deselect hook before the weapon death guard. The UH DeselectDeath
overrides still returned to DeselectSwap+1, which now points at that guard. A
zero-health owner immediately re-entered DeselectDeath; the offline zero-tic
path overflowed the native stack. All four occurrences were changed to +2,
matching the new base's lowering entry: three weapon bases and Magic Specialist's
cleanup override. Timings and cleanup actions remain intact.

A focused runtime regression is provided in tools/mcp/weapon-death-test.mjs;
its diagnostic fixture is excluded from the game package. Validation results
are recorded in the relay checkpoint after running the test.

The diagnostic attempts to select a newly given weapon did not switch away
from the class weapon in TRAINING. This is not included in the death regression's
passing criteria; normal weapon switching still needs its own v6c investigation.
The crash fix changes only the branch entered for a dead owner.

Crash-fix validation: Igniter, Juggernaut, and Magic Specialist each passed the
focused lethal-damage regression with a live engine after death. The original
addon load order, with hitbox display enabled, also survived nonlethal damage
and an explicit lethal hit (health 0) on Linux. The 31-check smoke gate passed.
The maintainer confirmed on Windows that death no longer crashes the game
and approved pushing this migration checkpoint. This confirms the reported
death crash fix; the remaining migration work listed above is still pending.


## ClassBase extension slots (2026-10-28)

The effective ClassBase2 parent is now ClassBaseSlot100. The chain still begins
at ClassBaseSlot0 inheriting ClassBase_UH40_DeathEffects, so all UH pain, status,
movement, and death layers remain below the base-game extension slots.

Audited all 100 stock include entries and their corresponding package files.
Every slot inherits its immediate predecessor and has an empty body. Slots
51-100 extend the addon inheritance surface; they do not add playable classes
or new stock behavior. The stock slot files remain in the v6c package and are
not copied into this repository. Generic robot and shootable-actor slot chains
are separate systems and retain their existing counts.

A temporary diagnostic addon overrides only the base slot-100 include with
unique pain/death markers. This tests whether actual survivor and boss bodies
inherit an extension at the new endpoint while retaining UH death handling.
The diagnostic addon is excluded from out/build.pk3.

Validation passed for Igniter, Juggernaut, and a debug morph into Magic
Specialist. A 10-point nonlethal hit left each body at 990 HP and set only the
slot-100 pain marker. A subsequent lethal hit set the slot-100 death marker,
left the body at 0 HP, and kept the engine responsive. This confirms both the
new extension endpoint and continued survivor/boss death handling. All 100
stock include paths and predecessor links also matched the actual v6c archive.
The rebuilt package was checked byte-for-byte against the edited ClassBase2
source; it contains neither copied slot definitions nor the diagnostic library.
The existing smoke gate passed 31 checks. This milestone was pushed as b870b636.


## Jump and movement hooks (2026-10-28)

JUMPCANC now uses the v6c dispatcher for nonspecific, pressed, held, released,
and idle jump hooks. Rising and falling follow the active gravity orientation.
The existing UH bot exclusion remains; this port does not change bot movement
ownership. The old landing-velocity heuristic is replaced by footing checks,
as in v6c.

A COREJUMP shadow supplies the v6c callbacks, jet-adaptor behavior, dash-property
helpers, and independent wall-thrust property. The base LOADACS already owns
this library; no new mod LOADACS entry is needed. UH ceiling, Venus blast, and
water-treading jumps register before stock wall and adaptor hooks. Consumed-jump
results propagate through the remaining callbacks. The jet callback also honors
that result.

Preserved UH behavior includes the AirFraud landing reset, legacy high-jump-rune
lookup, cancellation toward the supporting surface, and ceiling-flipped air/wall
jump impulses without a second sign inversion. Generic Boss still requires and
spends exactly 100 energy only when an air jump succeeds.

FOOTCHEC now exposes the v6c ceiling, custom footing, signed-offset, and
projectile-based wall-check interfaces. The existing UH ceiling support band
and attachment flag remain. RNC Clash Man's 32-unit stair tolerance moved to
uh_CheckFootingTolerance so it cannot redefine the v6c offset argument.

The focused diagnostic addon and runner are tools/mcp/fixtures/movement/ and
tools/mcp/movement-test.mjs. Build/run instructions are in tools/README.md.
The addon is never packed into the shipped mod. Contract checks isolate
individual callbacks; real input separately checks dispatcher delivery.

Validation: all project ACS libraries compile. The focused native v6c run
passed 29 movement/footing assertions and 7 Generic Boss energy assertions.
Real input delivered all five hook types, propagated a consuming hook result,
and performed an air jump with one use and a 12-unit vertical impulse.
The existing smoke gate passed 31 checks; its v6b defaults are still a limitation.
Map-specific wall detection, all assist-item combinations, full LMS rounds, and
dedicated-client movement/ammo synchronization remain separate requirements.
The next migration milestone is the HUD/bar APIs and built-in v6c UI.


## HUD bars and built-in UI (2026-10-28)

The BARLIB shadow now provides v6c ammo-number offsets, vertical/horizontal
custom bars, and arsenal-bar color/graphic setters. UH third-bar and explicit
ammo-proxy helpers remain. The ASSTLIB shadow retains the legacy UH helpers and
adds all modern v6c assist-bar setters; v6c still supplies the legacy runtime.

BARCLEAR keeps the UH clear-callback registry and legacy 256-slot sweep, then
clears the v6c sparse registry across all 1000 slots in each of the three bar
families. Invalid mode/slot registrations are rejected. The stock ammo-cheat
cleanup scripts are retained. BARHNDLE keeps UH held-weapon remapping and third
bars, uses the stock script-name cache, and assigns a removable TID to the
script-bar marker.

Each UH core SBARINFO orientation now contains all 3000 stock v6c custom-bar
entries, copied from the matching v6c orientation. The UH-generated namespaced
bar fragments and their generator were not changed. This keeps existing UH HUD
behavior while adding slots 256-999 and independent horizontal/vertical bars.

UITEAMIT now has a v6c shadow. It retains native layout/options and switches LMS
membership and health to the shared UH policy and snapshot. The server includes
clients using native teaminfo in its snapshot audience. The native display
suppresses the UH fallback to avoid drawing both. MUGSHOTS resolves UH portraits
through the shared presentation API before falling back to stock skin behavior;
this also serves the native killfeed and follows boss morphs without a stale
player-class cache.

The v6c UIXLIB/HUDLIB headers and UICOMMON import source are vendored from the
base. UICOMMON is not compiled or replaced; the native object remains the owner
of its state. UITEAMIT and MUGSHOTS use existing base LOADACS entries.

UH items and MegaManU copy weapons register when the native inventory wheel is
present, without requiring standalone UIX. The existing +weapwheel/-weapwheel
bindings forward to the native wheel when standalone UIX is absent. The class
wheel adapter described below adds UH-specific routes to this initial bridge.

A focused runtime probe lives in tools/mcp/fixtures/hud-v6c/ and runs through
tools/mcp/hud-v6c-test.mjs. It covers new slot families and cleanup, existing UH
third bars, callbacks, modern assist IDs, native registry entries and portraits.
Keep it out of release packages. Dedicated-client team health/ammo, spectator
privacy, reconnects and full-round regression still need separate verification.

Validation: all project ACS libraries compile. The focused native v6c run passed
21 HUD assertions, checked Igniter and morphed Generic Boss portraits, and opened
and closed the native weapon wheel through the actual bindings. Both 3000-entry
SBARINFO sequences match their base-game orientation. The bar generator checks
and all 31 smoke checks passed. This does not establish rendered layout quality
or dedicated-client synchronization; the general smoke defaults still target v6b.

## Class weapon wheels (2026-10-29)

UH fixed-loadout classes, Qwant, Nega Man and Decoy Bot now use the native v6c
wheel framework when standalone UIX is absent. Existing class snapshots supply
the weapon groups, icons, labels, disabled entries and live ammo bars. The native
framework supplies mouse selection, layout, scale, dimming and fade. Standalone
UIX retains its existing route. Mega Man keeps the stock native wheel.

The UHWWV6C adapter reads the import-only WHEELDT table and uses named WHEELLIB
entry points; it does not shadow UIXWHEEL or copy native wheel state. Native and
legacy AddWheelItem wrappers have different contracts and collide in ACS's
case-insensitive namespace, so this unit cannot include both APIs directly.
Legacy label and overlay fonts resolve to the corresponding native resources.
Empty ammo fills skip drawing.

The native info callback runs the existing per-class validity/ammo refresh each
tic. It retains the last list for native fade-out after a cancellation. Release
revalidates the snapshot, clears the shared wheel table, and invokes the existing
class-specific selection path with a WHEELDT item index. Selection still uses
NamedSendNetworkString and the server's class/membership/ownership checks. A busy
native wheel rejects the new route without retaining UH snapshot ownership.

The focused addon is tools/mcp/fixtures/wheel-v6c/, driven by
tools/mcp/wheel-v6c-test.mjs. This is an offline diagnostic; dedicated-client
selection, all fixed-loadout classes, all disabled-entry transitions and full
rounds remain separate regression requirements.

Validation: all project ACS libraries compile. Native v6c runs passed the four
class routes (Arcanist, Qwant, Nega Man and Decoy Bot), alternate selection on
release, Arcanist cancellation after removing an unselected held weapon, font
availability without standalone UIX, snapshot cleanup and Mega Man's default
native fallback. Arcanist's open wheel also received a visual spot check. All
31 smoke checks passed; their general defaults still target v6b. The rebuilt
package contains matching wheel bytecode and no diagnostic addon.

## Dedicated-client native team information (2026-10-29)

The native UITEAMIT weapon display now reads the authorized UH server snapshot
for weapon identity, ammo and capacity, alongside the existing health snapshot.
Remote client-local inventory is not authoritative in ordinary LMS. Weapon
icons and colors still resolve through the client's own DTADD records, with a
per-actor lookup cache. Non-Unholy modes retain the stock inventory path.
The teammate renderer also recognizes UH Mega Man copy-weapon palette markers;
without this fallback the native weapon icon could appear without its ammo bar.
Missing DTADD lookups are cached until the actor or registry size changes.

The former integer weapon-tag argument was an unsafe cross-process ACS string
index. It is now a weapon token, paired with a per-viewer NamedSendNetworkString
mailbox containing the actor name and capacities. Each client resolves its own
localized tag. The server registers UH Mega Man weapon metadata as well as the
client, so authoritative ammo-type lookup can resolve those copies. This does
not add DTADD records for every other UH-specific weapon.

Metadata is sent on weapon/capacity changes and after authorization or connection
changes. Numeric packets and strings may execute in either order; consumers wait
for matching tokens. Stats and clears share a 15-bit sequence, including wrap
handling, so an old packet cannot restore a cleared row. Display-only hello or
policy resets retain metadata for the next numeric packet. Explicit server
clears retire it. Expanded existing arrays preserve the round core's 128 map
variable limit.

The server clears previously authorized rows when their relation or display
eligibility changes. True spectators receive live stats only while
lms_spectatorview permits following players. A reconnect resets the viewer's
metadata delivery cache. The focused addon and runner are
tools/mcp/fixtures/native-teaminfo/ and tools/mcp/native-teaminfo-test.mjs.

At this checkpoint, health/max health were still 16-bit and armor/ammo amounts
were 10-bit. The following milestone removes those legacy wire limits. Missing
custom-weapon DTADD records, 64-slot load, all event policies and full-round
regression still need further work.

Validation: all project ACS libraries compile. The focused v6c dedicated-server
run passed 20 remote snapshot checks and local packet-order/wrap probes (110
assertions across the initial connection and reconnect). It verified a
native-only viewer, correct weapon-tag contents, health/ammo/capacity changes,
deliberately wrong local inventory, relation/display/spectator permission clears,
restoration, reconnect and named bot removal. The actual native weapon renderer
consumed the snapshot, and its visible ammo bar received a screenshot spot check.
All 31 smoke checks passed. This does not establish the wider value ranges or
64-player/full-round coverage listed above.

## Full-range teammate values (2026-10-29)

The numeric snapshot now uses two four-integer messages: uh_ti_stat carries the
subject/flags/revision header, health, maximum health and armor; uh_ti_ammo
carries the same header, weapon token and two ammo amounts. Values retain the
full nonnegative ACS integer range through 2147483647. An ammo value of -1 means
absent or infinite; zero means present but empty. Metadata decimal parsing also
accepts ten-digit capacities with an overflow guard.

Each numeric stream has an independent 15-bit revision. Either packet can
arrive first; ammo alone never authorizes a display row. Both streams reject
updates older than a clear, and a clear cannot retire either half of a newer snapshot. String
mailbox token matching remains unchanged. The extra stream state extends the
existing client array, preserving the round core's 128 map-variable ceiling.

The native teammate renderer normalizes health/ammo fractions before calling
UIXLIB, whose pixel-extent multiplication otherwise overflows with large raw
values. The fallback's health percentage avoids its former multiply overflow.

Validation: all ACS compile, and the extended dedicated-client diagnostic passed
23 remote snapshot checks plus ordering/wrap/sentinel probes (170 assertions
across the initial connection and reconnect). Real server pawns exercised
1000000007 health, 2000000003 maximum health, 1500000123 armor, 1073741947 ammo
and a 2000000001 capacity, then 2147483647 boundaries. Local probes covered two
independent full-range ammo values, an absent resource, a present empty bar,
cross-stream reorder, stale clears and revision wrap. The large-value native
bars received a screenshot spot check. The general smoke gate passed 31 checks.

## Team palettes and remaining shared-header APIs (2026-10-29)

TEAMCOL now stores all four v6c palette columns for each of the 18 UH color
slots: secondary, primary, lighter and darker. Native radar, domination and
possession consumers can request the added columns without reading another
team's data. UH source anchors and the class-only translation ranges remain.
The legacy assist registration for core_runteambar was removed because the
native UI hook already calls it. Color preset menus use the native OpenMenu
entry point. COLOTRNS honors mm8bdm_sv_playerteamcolor while retaining UH mugshot
and ready/charge dye bookkeeping.

The remaining changed shared-header APIs now match v6c: normalize folds a full
turn to zero, zanRound uses the new half-step rule, clampBySign is available,
setIntenseMusicState preserves multiple states, and getCameraPln forwards the
native camera query. 8BDMEFCT adds replacement-aware inventory checks/removal.
SetInventory2 and SetActorInventory2 live beside the existing setters in the
imported UH utilities library; BARLIB/8BDMEFCT deliberately avoid duplicate
setter bodies. Existing ceilOld and UH distance-helper ownership remain.

A source-level name audit found no missing v6c function/script entry points in
uniquely matched overrides after resolving those shared utility functions. This
proves interface presence only. uh_corereplace keeps the UH integer-force target
wrapper and UH rune counters; the base still supplies its separate v6c native
knockback/rune APIs. Do not replace the UH integer-force contract with the base's
fixed-point force contract without changing its DECORATE callers.

Validation: the actual translation function passed 320 server-option, team,
startup and charge combinations under C stubs. Its mutation case caught removal
of the server-option condition. The focused v6c runtime passed 96 palette,
hook, helper, music-state, camera and inventory-replacement assertions, including
all four palette columns for all 18 slots and one native team-bar hook. All ACS
compile. The smoke gate now includes the color contract and passes 32 checks.

## Canonical runtime profiles (2026-10-29)

The MCP smoke, network, class, presentation and scenario runners now default to
`tools/mm8bdm-v6c.launch.json`. The gate and agent-configuration checker use the
same canonical profile. The v6b profile remains an explicit historical template.
The v6c file includes a minimal profile, an optional addon stack without v6b
miscfixes or standalone UIX, and the presentation example addon profile. Listing
an optional profile does not establish interoperability; that audit remains open.

The project MCP server wrapper extends the backend's exported startup I/O
adapter to 120 seconds, preserving its registry ownership and cleanup. Launch
requests allow 150 seconds. No external MCP backend files were modified.
Machine-local references to this project's previous canonical profile were
updated; a previously running shell may still need an explicit v6c environment
override until it restarts.

Validation: strict agent-configuration checks passed, profile resolution selected
only the IWAD, v6c base and current mod, and an actual default MCP smoke launch
reported no compile/fatal errors, returned player state and quit cleanly.

### Default migration follow-up (2026-10-29)

The remaining tracked runner defaults now select v6c:
`direct-startup-test.mjs`, `xray-test.py` and `batch-d-acceptance.sh` use the
v6c smoke/full profiles. `check_environment.py` and `unpack_references.py` read
`references.root` and per-target overrides from `paths.local.json` before
`MM8BDM_REFERENCES_DIR`; the default unpack target is v6c and v6b stays available
through `--target mm8bdm-v6b`. The gate pins the canonical profile for its engine
and dry-run probes, so a stale ambient `ZANDRONUM_LAUNCH_PROFILES` from an older
shell cannot turn a default `--smoke` into a failure; the preflight warning still
reports the mismatch.

Validation: `python3 tools/gate.py --smoke` passes 33 of 33 checks with only the
stale-ambient warning; the edited runners pass syntax checks and a
`direct-startup-test.mjs --dry-run` resolves the v6c smoke profile and the v6c
IWAD/base/mod file set.

### Frozen asset baselines (2026-10-29)

The frozen external-name constants in `check_asset_references.py` (sounds,
LANGUAGE keys, HUD graphics) and `check_lump_integrity.py` (base graphics) were
re-verified against `../wads/mm8bdm-v6c.pk3`. Every frozen v6b name is present
in the v6c base game, so the allowlists are a strict subset of v6c coverage; no
source reference resolves through a v6b-only name. A new smoke check,
`tools/check_base_baselines.py`, fails when any frozen name is absent from the
v6c package, so a future base rename cannot hide behind the frozen list. The
static checkers still fall back to the frozen sets in a fresh clone without WADs.

### Base delta and engine regression (2026-10-29)

Compare the embedded map packages and DECORATE actor registration between the
v6b and v6c bases, then exercise the additions in the engine.

Base delta:
- Map WADs: v6b has 181, v6c has 187. Added MMCTF26 and MMDOM01 through MMDOM05;
  none were removed.
- New native pickup items (from actor registration, not a directory listing):
  AutoRecover, BalloonAdaptor, CapsuleCatcher, Carry, CounterAttacker,
  DamageAbsorber, EnemyAnalyzer, EnergyBalancerNeo, Exchanger, MagnetBeam,
  PowerGenerator, PowerShield, RushPogo, ShockGuard, SpareBody, SuperArrow,
  SuperGuard, SuperRecover and Transceiver items, plus the ItemPresenter system.
  New adaptive upgrades: JetAdaptor, PowerAdaptor, RockKick, RollSwing and
  RushBike. v6c also adds the assist category actors (Attack, Buff, Dash, Escape,
  Flight, FullRestore, Gift, Heal, Jump, Map, Passive, Reload).
- v6c adds about 6832 DECORATE classes over v6b. Most are internal: 2000
  CustVSBAR slot actors, 213 map markers and 262 respawn shadows. The item and
  upgrade names above are the gameplay additions.

Map load: `tools/map-load-test.mjs` launches a headless engine per map and waits
for the map banner. All six new maps load with the v6c base and `out/build.pk3`
with no startup fatal: MMCTF26, MMDOM01, MMDOM02, MMDOM03, MMDOM04 and MMDOM05
(44, 43, 43, 43, 43 and 43 s).

Engine regression under the v6c profile:
- `mcp-smoke` pass (54 s): startup and player state.
- `mcp-team-info-sync` pass (142 s): per-client CLIENTSIDE delivery.
- `mcp-team-presentation` pass (252 s): portrait resolver end to end.
- `mcp-network` first failed: the direct second client did not finish loading
  the larger v6c package inside the fixed 45 s window, so BatchDClient2 never
  connected. `network-test.mjs` now polls for client authentication for up to
  90 s instead of a fixed sleep. The re-run passes (155 s): both remote clients
  authenticate and receive a snapshot.

### Runtime scenario evidence (2026-10-29)

CXAirMan remote-ammo regression: `tools/mcp/boss-ammo-test.mjs` passed with the
v6c profile and the diagnostic probe. The client meter was one point stale, the
insufficient-energy cast was rejected, refill and normal cast worked, and reload
spent then recovered boss ammo.

LMS lifecycle scenario: `tools/mcp/lms-round-test.mjs` now passes 30 assertions
on the current v6c package (131 s) and is registered as `mcp-lms-round` in the
full gate. Both bosses and the debug morph equip their expected weapons.
The earlier missing-weapon failures were a parser bug: the server reader dropped
the `weapon` line from `dumpactor` output.

Disconnect cleanup was correct. The engine's `g_game.cpp` skips `P_Ticker` when
no real clients remain, even with bots, so pending DISCONNECT scripts cannot run
until another client connects. The scenario now keeps a second remote spectator
connected and waits for the role clear. Frozen/protected participants prevent
combat from changing the result while a third engine loads. Native
`GAMEMODE_PreventPlayersFromJoining` also forbids a fresh mid-round LMS life:
the reconnect is checked as a true spectator with the current boss snapshot,
not as a new survivor. No gameplay disconnect or morph change was necessary.

The run also verifies the pending-result HUD, a survivor's revival through the
production delayed Dickhead path, cancellation of settlement, removal of the
pending-result HUD, and shutdown of both clients and the dedicated server.
Final result commit and subsequent map progression still need runtime coverage.

DECORATE replacement audit:
- 326 `actor ... replaces <base>` declarations; every replaced base actor exists
  in v6c, and none were removed.
- Most replacements inherit their v6c base actor properties and override only
  selected states. Forwarding wrappers based on `BasicWatcher` are exceptions;
  their native child actors inherit the updated base definitions.
- Core `unepic` replacements: SmallHealth, BigHealth and MegaHealth states are
  byte-identical. WeaponEnergy, BigWeaponEnergy and MegaWeaponEnergy changed only
  the base `core_AmmoScript` amount, which UH does not use because it replaces
  the Pickup state with `uh_Health`. PartyBall already uses `PartyBallSpawnFunc`.
- Review candidates where UH copies the v6b state while v6c changed that state:
  `UH_CopyVision` (v6c adds `CopyVisionDeployedCount`, `CopyVisionTimer`,
  `CopyVisionRedirect_P`; UH keeps the v6b counter path), `UH_TeleportFogGiver`
  (v6c uses `nodelay`), and the teleport watchers that v6c extended with
  `user_noProjectileTrails`. These are behaviour reviews; the build and engine
  checks pass.
- v6b miscfix carryovers: `compat/mods/miscfixes/{WEPHIDE,PICKRPLC}.acs` and
  `FixCoreActors.dec:Rush_UH_Fix`. The v6c base has no banwep/WEPHIDE library and
  no Unholy code calls banwep, so WEPHIDE and PICKRPLC are inert under the v6c
  profile; keep them for the historical miscfixes package and do not add them to
  LOADACS. Rush_UH_Fix remains a live behaviour fix.

### Copy Vision lifetime review (2026-10-29)

The active weapon/clone pair is `CopyVisionWepU` / `CopyVisionU`, included after
`UH_CopyVision`; the later replacement is the one used by normal weapon spawns.
UH deliberately retains its deployment flag and per-clone countdown. The native
v6c actor changed from reaction time 40 to 1 because it now uses an owner timer.
Inheriting 1 caused the UH clone to disappear after its first firing cycle.
`CopyVisionU` now explicitly keeps 40; the UH weapon's balance and redirect
sequence remain unchanged.

The focused `copyvision-v6c-test.mjs` diagnostic reproduced two failed lifetime
assertions against the previous package and passed all six assertions against
the fix. It checks spawn, survival beyond the first firing cycle, owner deployment
state, bounded expiration, and deployment/redirect cleanup. The diagnostic addon
is not part of the shipped package.

The other flagged core differences do not require a behavior change:
- `UH_TeleportFogGiver` starts with a zero-tic dummy followed by its guarded
  action chain. Native v6c uses a zero-tic `nodelay` action instead. In the target
  engine's `AActor::Tick`, both execute that zero-tic chain on the first tick;
  UH retains its sound stop and `NoTeleportFX_Flag` guard.
- `RushTeleportCopy`, `RushMarineTeleportCopy`, `RushJetTeleportCopy` and
  `EddieTeleportCopy` inherit their v6c parents, including
  `user_noProjectileTrails`. The UH forwarding wrappers derive from the
  noninteracting `BasicWatcher`, not `ProjSpawnFuncActor`; they do not run the
  native projectile spawn callback and do not need a trail marker of their own.

### Maintainer-provided item icons (2026-10-29)

Replaced 81 matching item PNGs from the maintainer's `../resources/items`
collection. All matched images are 16 by 16 and have valid PNG chunk checksums;
one additional matched image was already identical. Five unreferenced template
images and Windows Zone.Identifier streams were not added to the runtime.
The refreshed Pandora Box PNG omits its old grAb chunk, so TEXTURES preserves
its world sprite origin at (8, 16). Existing HUD composites keep their names
and dimensions.

A focused runtime using the refreshed assets passed 81 assertions covering all
19 new native assist pickups, their native spawn hooks, eight active-item uses,
Counter Attacker enable/disable, stationary Auto Recover healing and three UH
icon composites. Custom-weapon capability flags were explicitly opted in by the
diagnostic; the test does not change the classes' default pickup policy.
Dedicated LMS coverage and upgrade behavior remain separate work.

### Native item effects and UH capsule integration (2026-10-29)

The external item diagnostic now has 108 assertions and can run on the controlled
remote player through `lms-round-test.mjs --items-probe`. A dedicated v6c run
passed all 108 item assertions and the entire 31-assertion LMS scenario (134 s).
The ordinary runner still has 30 assertions when no diagnostic addon is supplied.
The launcher selects the registered display name MegaMan, which resolves to
MegaManU; using the actor name as the playerclass value selected a random class.
The Copy Vision runner now uses the display name too and passes its six checks
on the current runtime package.

Coverage includes all 19 physical assist pickups, four native custom-class
capability restrictions, eight active-item uses, the native heal/reload/ammo
capacity/hitstop/fling factors, Counter Attacker's damage-factor enable/reset,
stationary Auto Recover, and UH icon composites. The diagnostic grants the four
custom-weapon capability flags explicitly; the default class pickup policy is
preserved. A Super Arrow may immediately become an impact platform when fired
near a wall, so the diagnostic accepts either the projectile or its native
impact actors.

The expanded checks found a real integration gap: UH health capsules bypassed
native heal and success hooks. Super Recover did not boost them and a full-health
Exchanger pickup could be consumed without giving ammo. Those five targeted
health assertions failed on the previous package. All capsule variants now use
the native flat-point heal pipeline, keeping UH's 25/80/100/150/200/300/500/2000
point amounts and AntiDamageHealth bookkeeping. Other UH heals and maximum-health
growth keep their existing API. The diagnostic verifies all ten capsule actor
variants with the 1.5 heal factor, native success notifications, full-health
conversion and rejection without Exchanger.

The current PK3 was rebuilt from runtime files with compiled ACS, excluding ACS
sources, error logs and all diagnostic objects. The full ACS compile and smoke
gate pass; no native-item diagnostic is added to the game's LOADACS.

### Shared ammo capacity (2026-10-29)

The earlier capacity diagnostic found that Power Generator factor 2.0 gave the
unique RockNRollAmmo the correct capacity 56, but the shared SparkShockAmmo
capacity 112 instead of 56. The native WEPACS updater visits every weapon row.
The stock weapon and its UH replacement have separate DTADD rows that share one
ammo type, so the type scaled twice.

The project now shadows WEPACS. `weapon_ammo_capacity.acs` reimplements only
`core_ResetAmmoCapacity` and `core_updateammocapacity`; every other native script
stays identical. Two passes deduplicate the ammo types. The first pass records
each type across both channels and whether any alias row is owned. The second
pass scales each type once. A processed bit stops the native row and the UH alias
row from scaling the same type twice. `weapon_ammo_capacity_math.acs` replaces
the native 16.16 fixed-point shift, which overflowed above 32767, with exact
integer scaling that rounds ties upward and saturates at 2147483647.

The first implementation declared two 32768-entry local arrays plus a 10000-entry
order array. ACC compiles that, but the ACS script frame is a 16-bit WORD. The
combined frame exceeded 65535 and the VM reported "out of bounds access to local
variables" at runtime. The final version uses two 16384-entry buckets and no
order array, with a two-pass processed bit.

Validation: `tools/check_ammo_capacity_math.py` compares the scaler with a
big-integer oracle over 54096 boundary and random cases under UBSan. The runtime
probe passes 30 of 30 assertions: RockNRollAmmo and SparkShockAmmo both become
56, case and channel aliases scale once, an owned alias after an unowned row
scales the amount, a secondary-only type is not skipped, fractional and
same-factor round trips hold, values near 2147483647 saturate, and the full
5000-row table scales once. No default UH class pickup permissions changed.

The standalone item fixture now restores the original safe position between
physical pickups and holds position during the stationary-healing check. This
prevents mobility-assist movement or walking off a spawn ledge from changing
that check. The updated standalone run passed 108/108; the earlier dedicated
remote run passed 108/108 plus all 31 lifecycle assertions.

### Native buster-upgrade policy (2026-10-29)

v6c gives the native buster upgrades (`BaseMM8BDMBusterUpgrade`) and every
`BaseMM8BDMWep` weapon `Inventory.ForbiddenTo "CustWepClassBase"`. Every UH player
class descends from `CustWepClassBase`, so those items and weapons must stay
unusable on UH bodies unless class balance changes on purpose.

The project keeps that policy. The UH `BaseMM8BDMWep` override keeps the
forbidden class and adds `+INVENTORY.RESTRICTABSOLUTELY`, so even a script-given
native weapon fails. `BaseMM8BDMCustWep` remains `RestrictedTo CustWepClassBase`.
No UH source overrides `BaseMM8BDMBusterUpgrade` or gives a native buster upgrade
to a player. The only UH reference is COREJUMP's stock `JetAdaptorWep` jump
check, which grants nothing.

`tools/check_native_buster_policy.py` guards these invariants in the fast gate
and in the `--meta` mutation suite. The five native adaptive upgrades named in
the migration task (JetAdaptor, PowerAdaptor, RockKick, RollSwing and RushBike)
stay on stock or otherwise eligible native bodies. A real-client native-body
diagnostic remains useful before RC, but it must not change the UH roster.

## Remaining completion evidence

The port is not complete while these items remain open:

- Optional: run a real-client native-body diagnostic for the five adaptive
  buster upgrades without changing the UH roster. The restriction policy itself
  is guarded statically. Native assist pickup/use and the flagged Copy
  Vision/teleport reviews are resolved above.
- Exercise changed existing arenas. The six added maps load; native assist
  pickups and effects now have dedicated remote LMS coverage as recorded above.
- Verify final LMS result commit and subsequent map progression. The cancellable
  lifecycle scenario now passes 30/30 and is in the full gate; CXAirMan remote
  ammo also passes.
- Verify map reload and high-slot/64-player load after the split numeric
  snapshot change. Two remote clients now authenticate under v6c. Audit optional
  addon profiles and clearly distinguish retained legacy paths from verified v6c
  interoperability.

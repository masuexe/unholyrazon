# MM8BDM v6c migration

Started on 2026-10-28. Minimal v6c startup now passes. Gameplay and multiplayer compatibility have
not been established.

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

Existing packet limits remain: health/max health are 16-bit and armor/ammo
amounts are 10-bit. The separate spectator-camera health path still carries a
full integer. Wider teammate values, missing custom-weapon DTADD records,
64-slot load, all event policies and full-round regression need further work.

Validation: all project ACS libraries compile. The focused v6c dedicated-server
run passed 20 remote snapshot checks and local packet-order/wrap probes (110
assertions across the initial connection and reconnect). It verified a
native-only viewer, correct weapon-tag contents, health/ammo/capacity changes,
deliberately wrong local inventory, relation/display/spectator permission clears,
restoration, reconnect and named bot removal. The actual native weapon renderer
consumed the snapshot, and its visible ammo bar received a screenshot spot check.
All 31 smoke checks passed. This does not establish the wider value ranges or
64-player/full-round coverage listed above.

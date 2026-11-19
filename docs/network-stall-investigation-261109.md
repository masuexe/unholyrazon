# Online attack stalls: release-history investigation

Status: the same high-traffic attack implementations already exist in 261031
and 261104. Both old releases reproduce seconds of client synchronization
backlog on a controlled bandwidth-limited link. A 261109-only regression has
not been established, and the affected public server's bottleneck remains
unconfirmed. No gameplay fix is included in this investigation.

## Report and comparison

The [Tencent Docs tracker](https://docs.qq.com/smartsheet/DY0VLQkZxeG5RSm9C),
record `rlSWRI` (third displayed row), reports Void Walker's Razing Ray,
Colonel Kachidonga's charged secondary attack, and Super Megaman's ultimate.
The maintainer also identified Shin Hellbot's ultimate and confirmed that only
the Razon PK3 changed between the working 261105 setup and affected 261109 setup.
Void Walker and Mosquito Demoneye being present are not required to trigger
the reported stalls.

The actual local release archives were compared, rather than inferring their
contents from Git tags. `out/build.pk3` and the local 261109 release are identical
(SHA-256 `96580d69590e7bb40e18a7ada1ea9f072b1f4155b08c1cf2e0053c528a4c6c3f`).

- Colonel Kachidonga, Super Megaman and Shin Hellbot's entire weapon files are
  byte-identical between the two releases.
- The `RazingRayPinpoint` actor definition is identical as well.
- The shared `UH_TOOLS` and `PROJTRAN` objects are identical. The only changed
  ACS objects are `RZ_DEBUG`, `UH_BARS`, `UH_BOSSDEFS`, `UH_BOSSES`, `UH_CLASSES`
  and `unholy`.
- The inspected source changes concern Void Walker's second phase, flight/pit
  stamina, cleanup, boss bars and spectator counter placement. This inspection
  has not established an additional broadcast path for the four attacks.

## Measured traffic

A temporary addon ran the production projectile classes at their production
emission cadences, using one dedicated server and one remote client through a
loopback UDP counting proxy. The base stack was `megagame.wad`, MM8BDM v6c,
one release PK3, then the diagnostic addon. A temporary flat arena removed
normal-map walls and random spawn positions. The engine reported 3.3-alpha.

Each sample spans 280 server tics, approximately 7.92 measured wall seconds.
Values below are **total server-to-client UDP payload bytes over that window**,
including ordinary background traffic and cleanup. They exclude IP/UDP headers.

| Probe | 261105 bytes | 261109 bytes | Counted projectile descendants, old / new |
|---|---:|---:|---|
| Idle | 6,358 | 6,386 | 0 / 0 |
| Razing Ray, two sweeps | 205,691 | 205,852 | 3,712 / 3,712 pinpoint actors |
| Charged Kachidonga M2 | 278,569 | 274,807 | 30 seeds plus 4,211 / 4,174 damaging trails |
| Super Megaman, 100 beam emissions | 870,866 | 925,621 | 10,800 + 3,400 / 12,100 + 3,800 visual + damage segments |
| Shin Hellbot meteor helper | 144,016 | 143,562 | 100 meteors + 2,400 shockwave pieces in each |

Razing Ray's total changes by approximately 0.08%; Kachidonga and Shin Hellbot
are also close. Super Megaman's raw totals are **not an equal-work comparison**:
the runs produced different beam lengths, so that difference does not establish
a regression. The probe resets player aim at the start but does not lock it
throughout a cast. Subsequent comparisons must disable mouse/joystick input and
record aim as well as position. Initial normal-map runs were also sensitive to
spawn position; they must not be used as a version comparison.

Both releases completed all the measured server-tic windows without a sustained
server stall. This is not proof about a populated public server, short individual
tic spikes, an actual complete ultimate, damage to multiple survivors, addons,
or a constrained/lossy uplink. The probe drives projectile emission directly;
it does not reproduce the full weapon/morph/input path. In particular, high
traffic in both builds does not explain why the maintainer observes a problem
only in 261109.

Raw logs, probe sources, temporary arena, results and package hashes are retained
under `out/net-stall-investigation/`. These are local diagnostic artifacts, not
part of `out/build.pk3`. The copied one-off runners contain their original
`/tmp/uh-netdiag-lab-*` paths; adjust those paths before rerunning.

## Historical follow-up: 261031 and 261104

The maintainer requested these older releases to test whether the problem
predates 261109. All four releases were rerun with the same probe, arena and
engine. Mouse and joystick input were disabled (`use_mouse=0`,
`use_joystick=0`), client rendering was capped (`cl_capfps=1`), and player aim
was checked every server tic. All 20 phases completed with zero nonzero-aim
samples. This comparison supersedes the earlier unlocked-aim beam comparison.

The complete Colonel Kachidonga, Shin Hellbot and Super Megaman weapon files
are byte-identical across 261031, 261104, 261105 and 261109. The extracted
`RazingRayPinpoint` definition is identical across all four as well. Their
high-entity-count design is therefore not a new 261109 change.

The following totals are server-to-one-client UDP payload bytes over each
280-tic sample, including background traffic and cleanup:

| Probe | 261031 | 261104 | 261105 | 261109 |
|---|---:|---:|---:|---:|
| Idle | 6,440 | 6,392 | 6,418 | 6,410 |
| Razing Ray | 205,509 | 205,569 | 205,316 | 205,573 |
| Charged Kachidonga M2 | 273,461 | 267,203 | 267,011 | 269,972 |
| Super Megaman beam | 874,020 | 876,520 | 876,324 | 875,995 |
| Shin Hellbot meteor helper | 143,215 | 143,317 | 143,303 | 142,637 |

Each release produced exactly 3,712 Razing Ray pinpoint actors, 12,000 visual
beam segments plus 3,800 damage segments, and 100 meteors plus 2,400 shockwave
pieces. Kachidonga's randomized bouncing seeds produced 4,155 / 4,088 / 4,114 /
4,159 trails respectively; small traffic differences there do not establish
a change in behavior. The 100 beam emissions vary by less than 0.3% in total
traffic across the four releases. Peak one-second beam traffic was about
159–161 KB/s per client, versus about 0.8 KB/s at idle. No sustained server
stall occurred on the unrestricted loopback link.

### Controlled client-backlog reproduction in both old releases

A second probe added numbered server-to-client script markers once per second
and at sample completion. Authentication and an idle baseline used an unrestricted
link. During the beam phase only, a FIFO UDP proxy limited all server-to-client
payload to 65,536 bytes/s (64 KiB/s). The proxy intentionally delayed packets;
it did not intentionally drop or reorder them. This is an imposed diagnostic
condition, not a measurement of the public server's available bandwidth.

| Measurement during beam phase | 261031 | 261104 |
|---|---:|---:|
| Server time for 280 tics | 7.89 s | 7.86 s |
| Maximum observed client marker delay | 7.31 s | 7.37 s |
| Maximum proxy packet queue delay | 7.58 s | 7.58 s |
| Completion marker delay after server completion | 5.50 s | 5.57 s |

Both casts produced the same 12,000 visual and 3,800 damage segments as their
unrestricted runs. Idle marker delivery was within approximately 20 ms of
the two log observers' resolution; small negative idle differences are log
observation timing, not negative physical latency. The multisecond attack-phase
delays are well above that uncertainty.

This establishes that these old releases can produce a network synchronization
backlog while the server continues stepping normally. Together with the
identical attack definitions and near-identical traffic, it supports a
longstanding congestion susceptibility rather than attributing it to 261109.
It does not prove which resource caused the maintainer's particular public
server incident. A saturated shared uplink, packet loss, server tic spikes,
full weapon/morph execution and multi-target damage still need live-scenario
measurements before assigning that incident's root cause.

The added artifacts are in `out/net-stall-investigation/history/` and
`history-shaped/`; `history-summary.json` contains all results and package hashes.
These one-off runners resolve version directories relative to themselves and
still use the local repository/engine paths documented in their source.

## Earlier lineage and v6c amplification

### Legacy stacks and measurements

Additional dedicated/client tests used the same engine, flat diagnostic arena,
locked inputs and emission cadences with each generation's matching base stack:

- Razon4 261024: MM8BDM v6b, `8bdm-v6b-miscfixes-v6.pk3`, release PK3.
- Original Unbound: MM8BDM v6a, `unholy_classes_unbound_v7b_pb1`,
  `unholy_bosses_unbound_v7b_pb1`, then
  `unholy_bossesclasses_v7b_pb1_snacks_fix`, in that order.
- Razon3 3.11.1: that same v6a/Unbound stack, followed by
  `uh-ub_razonpatch_3.11.1`.

The original Unbound/Razon3 download archives were not located. Their local
extracted reference trees include assets and compiled ACS; complete read-only
copies were repacked in `/tmp` for these explicitly requested reference tests.
These are tests of that extracted reference content, not a claim that original
download archive bytes were authenticated. No reference files were edited.

Measured peak one-second UDP payload to one client, in decimal KB/s:

| Attack | Original Unbound | Razon3 3.11.1 | Razon4 v6b (261024) | Razon4 v6c (261109) |
|---|---:|---:|---:|---:|
| Razing Ray | 21.1 | 22.3 | 28.8 | 63.1 |
| Charged Kachidonga M2 | 32.9 | 32.8 | 39.3 | 69.0 |
| Shin Hellbot meteor helper | 17.7 | 17.8 | 22.6 | 44.6 |
| Super Megaman beam | Not present | 6.2 | 70.5 | 161.5 |

Corresponding 280-tic totals in bytes:

| Attack | Original Unbound | Razon3 3.11.1 | Razon4 v6b |
|---|---:|---:|---:|
| Idle | 5,109 | 5,123 | 5,911 |
| Razing Ray | 70,444 | 70,873 | 92,653 |
| Charged Kachidonga M2 | 132,133 | 132,583 | 158,755 |
| Shin Hellbot meteor helper | 57,075 | 57,182 | 75,003 |
| Super Megaman beam | Not present | 35,810 | 392,915 |

Razing Ray's self-propagating actor, Kachidonga's 30 charged seeds with per-tic
damaging trails, and Shin Hellbot's 100 meteors spawning 24 shockwave pieces
each already exist in original Unbound. They retain networked actors rather
than purely local visuals. The same congestion susceptibility therefore has
an older design lineage, but their measured load is substantially smaller than
the current v6c load. None of these unrestricted old-stack tests reproduced a
sustained server stall; no new bandwidth-limited legacy test was performed.

Super Megaman is a Razon addition, absent from the original Unbound stack.
Razon3 uses `EndlessBeamStart` / `EndlessBeam`, speed 30, and a pitch-based
24-step limit. Its weapon emits 100 starts at two-tic intervals. That original
beam was tested directly, rather than substituting Razon4's newer visual and
damage chains. Its traffic is much lower, so the modern beam's measured severity
must not be attributed unchanged to Razon3 or Unbound.

The legacy actors generally lack `USESPAWNEVENTSCRIPT`. Their zero entries in
the diagnostic spawn-event counters mean **unavailable counts**, not absent
attacks. UDP measurements above do not rely on those counters. v6b Razon4's
beam does supply the counters: it produced the same 12,000 visual and 3,800
damage segments as v6c, while sending only 392,915 bytes versus 875,995 bytes.
This identifies a material amplification across the v6b/v6c stacks despite
unchanged Super Megaman weapon source, rather than a 261109-only change.

### Isolating part of the v6c amplification

A diagnostic-only shadow of the native `NODELIST` library retained all its
other functions but made `core_projnodelist` skip projectile registration.
With the unchanged 261109 package and identical beam segment counts, traffic
fell from 875,995 to 717,357 bytes (approximately 18%). Razing Ray fell from
205,573 to 169,997 bytes. Kachidonga and Shin Hellbot also sent less traffic.
This establishes that projectile node registration adds measurable traffic;
it does not explain the entire v6b/v6c gap.

Native v6c `NODELIST.acs` registers each projectile by temporarily changing
its TID, creating a server-only node and restoring the projectile's TID.
The consulted Zandronum `p_lnspec.cpp`, `LS_Thing_ChangeTID`, explicitly calls
`SERVERCOMMANDS_SetThingTID` on the server. Server-only nodes therefore do not
make the temporary changes to the networked projectile free of network cost.
The v6b base has no corresponding projectile node-registration system.

Skipping registration is **not a release fix**: native systems can depend on
the projectile list. The diagnostic shadow remains outside `out/build.pk3`.
Further optimization must preserve node-list consumers and investigate the
remaining traffic increase instead of disabling the system wholesale.

Raw legacy results, repacked-reference hashes, probe sources and the diagnostic
shadow are retained under `out/net-stall-investigation/legacy/`.

## Why these attacks are useful stress cases

- Razing Ray advances by spawning another `RazingRayPinpoint` and retiring the
  previous segment. It is bounded, rather than an all-zero-tic infinite loop.
- Charged Kachidonga M2 fires 30 seeds together. Each can spawn a damaging trail
  every tic until its 150-tic countdown or collision ends it. Those trails also
  fade on the server.
- Super Megaman rebuilds a densely segmented visual beam and a second,
  invisible damage chain every two tics. The invisible chain remains a networked
  projectile; invisibility alone does not remove network traffic.
- Shin Hellbot's helper creates 100 meteors. Each meteor can create 24 damaging
  shockwave pieces, explaining the measured 2,400 pieces.

The consulted Zandronum sources establish the networking mechanism:
`thingdef/thingdef_codeptr.cpp` (`A_SpawnItemEx`, `A_CustomMissile`,
`DoJumpIfCloser`, `A_FadeOut`), `sv_commands.cpp` (`SpawnThing`, `SpawnMissile`,
`DestroyThing`), `network/netcommand.cpp` and `cl_main.cpp`
(`CLIENT_GetNextPacket`, `CLIENT_CheckForMissingPackets`). Actor spawns and
associated state/property/destruction commands enter the reliable stream and
are normally sent to all eligible clients. Missing reliable packets block later
reliable parsing until recovery. These facts explain susceptibility to network
congestion; they do not identify a new 261109 defect.

Reference root: `../references/zandronum/zandronum-stable-branch-default/src/`.
Native actor flags were checked against
`../references/for_8bdm-v6c/mm8bdm-v6c/actors/basicactors.txt`.
`IcePitFreeze` is server-only through `PropElementEffect`; it should not be
misclassified as a broadcast visual in a future optimization.

## Separate confirmed regression: Mosquito flight

261109 replaced Mosquito Demoneye's immediate flight grant with
`uh_MosquitoDemoneyeHover` -> `uh_BossFlightPit` -> `UH_BossHoverTick`.
The shared tick begins with `UH_WatcherStillOwnsBoss`, which requires an active
Boss identity. An ordinary Mosquito Demoneye has an eye identity, so the watcher
returns before granting flight. The setup no longer grants flight independently.
This is a source-proven role mismatch, separate from the unresolved attack stalls.
It has not been patched or runtime-tested here.

## Remaining reproduction requirements

The maintainer subsequently clarified that one cast can stall all five or six
players in an otherwise ordinary match, and Super Megaman's beam appears to
emit more slowly during the stall. This is not sufficient to distinguish late
client presentation from actual slow server simulation. The one-client loopback
tests do not exclude server CPU/tic stalls or packet-production overhead with
multiple recipients. Actual server-side cast duration and tic timing need to be
recorded alongside network delivery.

For the maintainer's requested temporary mitigation experiment, the exact tested
NODELIST diagnostic shadow has been packaged as
`out/projnode-bypass/uh-projnode-bypass-test.pk3`, with its source and loading/revert
instructions beside it. It contains only `acs/NODELIST.o`; other node-list
functions remain intact. Current source searches found no readers of projectile
list `-9997` in the base game or Razon. That does not cover external addon code.
Load the addon last on both server and clients; removing it and restarting
restores the native behavior. It is not merged into the runtime build and has
not been verified in a five/six-player live match. Its bytes are identical to
the library addon used in the earlier five-phase A/B test.

Obtain the exact affected server engine version, a reliable map/player-count
scenario and the active addon list. Preserve the maintainer's same-engine,
same-addon comparison. Reproduce an actual cast against survivors in each
release, then record server tic timing, outbound traffic, client packet loss
and recovery. Investigate 261109 changes only where the paired run diverges;
do not label a longstanding projectile-heavy design as the regression without
that evidence.

## Follow-up root cause and fixes (261113)

### Root cause of the v6c traffic amplification (`HF_PROJ` hooks)

MM8BDM v6c registers five `DTADD_HF_PROJ` spawn hooks in `COREHOOK.acs` for
projectiles carrying `+USESPAWNEVENTSCRIPT`. Three of those hooks in v6c's
core library (`core_handleStaticDamageFactor_Proj` in `PUAPROP.acs`,
`core_handleCounterAttacker_Proj` in `ASTHELP.acs`, and `core_projnodelist` in
`NODELIST.acs`) unconditionally called `Thing_ChangeTID(0, u)` and
`Thing_ChangeTID(u, 0)` while inspecting the projectile's pointer even when the
shooter had no static damage factor or counter-attacker. In Zandronum (`p_things.cpp` /
`sv_commands.cpp`), each `Thing_ChangeTID` on a networked actor broadcasts a
reliable `SERVERCOMMANDS_SetThingTID` message, adding up to six extra TID
network commands per networked projectile spawn on v6c compared to v6b.

### Implemented fixes

1. **Zero-`Thing_ChangeTID` `HF_PROJ` hook overrides (`d46878d6`)**
   - Remapped `core_handleStaticDamageFactor_Proj`, `core_handleCounterAttacker_Proj`,
     and `core_projnodelist` inside `core_DefineHookFunction_S`
     (`src/acs_source/v6b_overrides/corescripts/api_handlers/DTADDR.acs`) to
     TID-free replacements (`uh_handleStaticDamageFactor_Proj`,
     `uh_handleCounterAttacker_Proj`, `uh_projnodelist`) in
     `src/acs_source/v6b_overrides/corescripts/utilities/uh_corereplace.acs`.
   - The replacements switch activator via `SetActivator(0, AAPTR_TARGET)` inside
     child scripts and spawn `NodeList_Node` (already `+SERVERSIDEONLY +NOCLIP +NOINTERACTION`)
     via `SpawnProjectile(0, "NodeList_Node", ...)` without touching any
     projectile TID.
2. **Boss ultimate `+CLIENTSIDEONLY` visuals & ray collapse (`1f477e60`, `a9470547`, `950ea57e`)**
   - `src/actors/classes/bosses/SuperMegaman_W.dec`: marked `SuperMegaEndlessBeam`,
     `SuperMegaEndlessBeamEndFXChain`, and `SuperMegaEndlessBeamEndFX`
     `+CLIENTSIDEONLY`; kept `SuperMegaEndlessBeamDamager` networked at its
     original 0-tic rate without `+SERVERSIDEONLY` so custom obituaries stay intact.
   - `src/actors/classes/bosses/ShinHellBot_W.dec`: marked
     `HelltatoruMoltenFireBallFadeFX` and `HelltatoruMoltenwavePartFadeFX`
     `+CLIENTSIDEONLY`.
   - `src/actors/classes/bosses/ColonelKachidonga_W.dec`: marked
     `KachidongaCannonShotX2FX` and `KachidongaBlunderShotX2FX`
     `+CLIENTSIDEONLY`.
   - `src/actors/classes/bosses/VoidWalker_W.dec`: replaced `RazingRayPinpoint`'s
     stepped server spawn loop with a `+CLIENTSIDEONLY` `RazingRayPinpointBeamFX`
     visual beam and a single 1-tic networked `RazingRayPinpointRay`
     (`BasicFastProjectile`, `Speed 4800`, preserving custom obituary).
3. **Mosquito Demoneye flight watcher & death/unmorph cleanup (`3e9e1514`, `c1943331`)**
   - Added `uh_EyeFlightPit` (`UH_HOVER_OWNER_EYE`, `uh_eyehovergen[MAX_PLAYERS]`,
     `UH_HoverStillOwnsBody`) in `src/acs_source/classes/shared/boss_hover.acs`
     and `src/acs_source/classes/eyes/mosquito_hover.acs`, and released
     `MosquitoDemoneye_HoverActive_F` / `MosquitoDemoneye_HoverStamina_F`
     explicitly in `uh_MorphDemorphReset` (`src/acs_source/systems/tools/morph_reset.acs`)
     and `DickheadDoRevive` (`src/acs_source/unholy/uh_dickhead_revival.acs`).
   - Updated `UH_HoverStillOwnsBody` and `UH_BossHoverTick` so Zandronum's
     death-time removal of `IsAnEye` (a non-persistent `Powerup`) still triggers
     `UH_BossHoverRelease` instead of leaving `MosquitoDemoneye_HoverActive_F`
     and `PlayerPropertyFlight` active on a dead body.

### After-fix 5-phase UDP traffic benchmark (`aim=0`, 280 tics)

Measured with `out/net-stall-investigation/fixed/run.py` against `out/build.pk3`
on the `mm8bdm-v6c` profile using the same 1-server / 1-client `NETPROBE` loopback
harness (`aim=0`):

| Attack | v6b Baseline (B) | 261109 v6c (B) | Fixed v6c (B) | Fixed v6c Peak (KB/s) | Delta vs 261109 v6c |
|---|---:|---:|---:|---:|---:|
| Idle | 5,911 | 6,410 | 6,440 | 0.9 | +0.5% (baseline floor) |
| Razing Ray | 92,653 | 205,573 | 15,258 | 3.4 | -92.6% (was 63.1 KB/s) |
| Charged Kachidonga M2 | 158,755 | 269,972 | 80,866 | 19.5 | -70.0% (was 69.0 KB/s) |
| Super Megaman beam | 392,915 | 875,995 | 135,140 | 23.7 | -84.6% (was 161.5 KB/s; server CPU 4.89s -> 1.77s) |
| Shin Hellbot meteor helper | 75,003 | 142,637 | 75,582 | 22.7 | -47.0% (was 44.6 KB/s) |

### Runtime verification (Mosquito flight & Boss obituaries)

Verified against `out/build.pk3` on a local Zandronum dedicated server with two
connected clients (`out/verify-runtime/run.py`):

- **Mosquito Demoneye (`Mosquito_MoolaGiver` -> `MosquitoDemoneye`)**:
  - Retains flight and hover stamina across tics (`hover=1 fly=1 z_above=95.9301 stam=500`).
  - Drains hover stamina over a damaging pit to `0`, drops flight (`hover=0 fly=0 z_above=44.8961`), and recovers flight (`hover=1 fly=1 stam=88`) after leaving the pit.
  - Cleans up cleanly on unmorph (`hover=0 stam=0 deplete=0 fly=0 nograv=0 eye=0 morphed=0`) and on death (`post_hover=0 post_fly=0`).
- **Touched Boss ultimate death obituaries** (confirmed identical on server and remote client):
  - `SuperMegaEndlessBeamDamager`: `Thanks to Endless Beam Launcher, VictimClient finally realized they shouldn't challenge Super Megaman (MosqClient) at the expense of their mom!`
  - `HelltatoruMoltenFireBallBoss`: `VictimClient was KPOW'D by Shin HellBot (MosqClient)!`
  - `RazingRayPinpointRay`: `VictimClient was eradicated completely by MosqClient's Razing Ray.`
  - `KachidongaBlunderShotX2`: `VictimClient had perished from Colonel Kachidonga (MosqClient)'s Charged Kangogias-Blunderbuss.`

## Follow-up: Morshu ultimate and Qwant Ice Beam stalls (261117)

Following the 261113 `HF_PROJ` fix, two additional attacks still caused server/client
stalls in live multiplayer sessions (`rlSWRI` update in the Tencent Docs tracker):
Qwant's `Ice Beam` (`IceBeamWep` / `QwantShiny_IceBeam_W`) and Morshu's ultimate
(`Morshu_W` `YOULITTLE` / `MMMMMM`).

### Root causes

1. **Qwant / QwantShiny `IceBeam` (`src/actors/classes/survivors/qwant_copyweps/IceBeam.dec`)**:
   - Pure-visual `+NOINTERACTION` trail actors (`ICELAZORTrail1`, `ICELAZORTrail2`,
     `S_IceBeamTrail1`, `S_IceBeamTrail2`) inherited `BasicProjectile`
     (networked + `+USESPAWNEVENTSCRIPT`) and called `A_ScaleVelocity(0.8)` / `0.6`
     on the server. Over an 8 s burst (140 `ICEBEAM`s in `NETLAB`), they spawned
     3,568 networked trail actors, each emitting `SpawnThing` + `MoveThingExact` +
     `SetThingTranslation` + `SetThingTarget` + a second `MoveThingExact` from
     `A_ScaleVelocity`, plus 8 server `HF_PROJ`/`SFT_PROJ` hooks (including
     `NodeList_Node` watchers and `uh_DailyFFStamp`) and 3 client `SPAWNEV` ACS scripts.
   - Because `ICEBEAM` inherited `BasicFastProjectile` without its own `Obituary`,
     kills by `IceBeamWep` / `S_IceBeam` also fell back to `BasicFastProjectile`'s
     generic missing-obituary string instead of `IceBeamWep`'s obituary.
2. **Morshu's ultimate (`src/actors/classes/bosses/Morshu_W.dec`)**:
   - Over 420 tics (12 s), `MMMMMM`/`MMMMMMX` spawns 420 `MorshuBombProjectileLITE`,
     1,680 `MorshuBombDebris`, and 420 `ForcedNegotiationHitbox` actors (`2,520`
     networked `BasicProjectile`s with `+USESPAWNEVENTSCRIPT`).
   - Razon 4 also switched `MorshuBombDebrisFX` from `BasicClientSide` to
     `BasicGraphicEffect` (running `MM8BDMProjSpawnFuncClient` on every debris trail
     particle every 2 tics), ran `ThrustThingZ(0, 10, 0, 1)` on `MorshuBombProjectileLITE`
     spawn (`MoveThingExact`), synced unused `Scale 5.5` on invisible
     `ForcedNegotiationHitbox` spawns (`UpdateThingScaleNotAtDefault`), and executed
     server-side `A_PlaySound` + `A_ChangeFlag("NOGRAVITY", 1)` on bomb/debris deaths
     (double-synced `SERVERCOMMANDS_SetThingFlags` + `SoundActor`).

### Implemented fixes

1. **`src/actors/classes/survivors/qwant_copyweps/IceBeam.dec`**:
   - Converted `ICELAZORTrail1`, `ICELAZORTrail2`, `S_IceBeamTrail1`, and
     `S_IceBeamTrail2` to `BasicClientSide` (`+CLIENTSIDEONLY +MISSILE +DONTSPLASH +FORCEXYBILLBOARD +BRIGHT`)
     spawned with scaled velocity `0.8 * vel*` / `0.6 * vel*` and flags
     `41` (`SIXF_TRANSFERTRANSLATION | SIXF_ABSOLUTEVELOCITY | SIXF_NOCHECKPOSITION`),
     eliminating 100% of server trail actors, `A_ScaleVelocity` packets, and
     server/client spawn-event ACS calls on trails.
   - Added `Obituary "%o was frozen by %k's \cnIce Beam\c-."` to `ICEBEAM` (inherited
     by `S_IceBeam`).
2. **`src/actors/classes/bosses/Morshu_W.dec`**:
   - Removed unused `Scale 5.5` and added `-USESPAWNEVENTSCRIPT` + `RenderStyle "None"`
     on `ForcedNegotiationHitbox`.
   - Added `-USESPAWNEVENTSCRIPT` to `MorshuBombProjectileLITE` and `MorshuBombDebris`
     (retaining `+USESPAWNEVENTSCRIPT` on `MorshuBombProjectile` so M1/Rope bombs keep
     `rz_projflipgrav`), folded initial `+2.5` Z velocity into the `MorshuBombProjectileLITE`
     spawn call in `MMMMMM`/`MMMMMMX` (removing `ThrustThingZ`), moved explosion visuals/sounds
     to `BasicClientSide` actors (`MorshuBombLiteExplosionFX` and
     `MorshuBombDebrisExplodeFX`), restored `MorshuBombDebrisFX` to `BasicClientSide`,
     and replaced `A_ChangeFlag("NOGRAVITY", 1)` in `MorshuBombDebris::Death` with
     tic-exact `A_Stop` waits (zero network flag packets while preserving the 4 explosion
     ticks at `0/9/18/27`).
   - Kept `ForcedNegotiationHitbox`, `MorshuBombProjectileLITE`, and `MorshuBombDebris`
     networked without `+SERVERSIDEONLY` to preserve custom obituaries.

### Benchmark & runtime verification (280 tics, loopback `NETLAB` & Deathmatch obituaries)

Measured against `out/build.pk3` on `mm8bdm-v6c` (1 server + 1 client loopback UDP proxy):

| Probe (`NETLAB`, 280 tics) | Pre-fix (B) | Post-fix (B) | Pre-fix Peak | Post-fix Peak | Server CPU | UDP Delta |
|---|---:|---:|---:|---:|---:|---:|
| Idle | 6,461 | 6,440 | 1.0 KB/s | 1.0 KB/s | 0.47s → 0.28s | -0.3% |
| Qwant `IceBeam` (`140` shots) | 88,681 | 13,757 | 12.3 KB/s | 1.9 KB/s | 2.30s → 0.38s (-83.5%) | -84.5% |
| Morshu Rage (`~280` bombs/hitboxes, `+1,112` debris) | ~87,382 (comb.) / 88,128 (`TRAINING`) | 53,699 | 12.0–12.6 KB/s | 7.9 KB/s | 1.36s → 0.36s (-73.5%) | -38.5% to -39.1% |

Deathmatch 2-client runtime check confirmed identical custom obituaries on server and remote client:
- `ICEBEAM` & `S_IceBeam`: `VictimClient was frozen by KillerClient's Ice Beam.`
- `ForcedNegotiationHitbox`: `VictimClient had buyer's remorse because of Morshu (KillerClient)'s forced sales.`
- `MorshuBombProjectileLITE`: `Morshu (KillerClient) sold a bomb to VictimClient.`
- `MorshuBombDebris`: `VictimClient was caught by Morshu (KillerClient)'s bomb debris.`

## Follow-up: SuperMegaman, ShinHellbot, and SovietFrostBite ultimates (261119)

Live dedicated-server profiling (`NETLAB` and `MM2DW1`, 2 connected clients behind a
loopback UDP proxy, `use_mouse=0`, `use_joystick=0`, `cl_capfps=1`) identified
four remaining causes of multiplayer CPU and network stalls during
SuperMegaman (`SuperMegaman_W`), ShinHellbot (`ShinHellBot_W`), and
SovietFrostBite (`SovietFrostBite_W`) ultimates:

### Root causes

1. **Global `DTADD_SFT_PROJ` ACS scan (`src/acs_source/classes/shared/copy_weapons/daily_team_ff.acs`)**:
   - `uh_DailyFFStamp` ran on every `+USESPAWNEVENTSCRIPT` projectile (including
     Boss and Demoneye attacks) and called `uh_DailyFFPointerOrigin`, which
     invoked `FindSurvivorByActor(pawn)` (`_imports/uhdt.acs`) — a linear scan
     over all `UH_MAX_VANILLA_SURV` (`128`) survivor slots — and then called
     `UH_DailyFFMakeOrigin` which ran `FindSurvivorByActor` a **second time**
     without early-returning on `id < 0` (`~10,400` ACS instructions per Boss
     projectile).
   - Over a single cast on `NETLAB`, `uh_DailyFFPointerOrigin` executed **47.3M**
     instructions during SuperMegaman (`4,560` spawns), **26.0M** during
     ShinHellbot (`2,500` spawns in `3.1 s`), and **27.9M** during
     SovietFrostBite (`2,682` spawns).
2. **`+USESPAWNEVENTSCRIPT` bloat on `BasicProjectile` descendants**:
   - In Razon 3, `HellApocMeteorAttackBoss`, `HellTatoruShockwavePartBoss`,
     `HailRainShotBoss`, and `SovietColdShotBit` did not trigger core spawn-event
     hooks. Inheriting `BasicProjectile` in Razon 4 pulled each spawned actor
     through 20+ server `EVENT` / `HF_PROJ` hooks, 2 networked inventory trackers
     (`StaticDamageFactorApplied`/`Amount`), and 1 `NodeList_Node` (`38.7k–90.8k`
     polling script calls per cast), inflating live server actors to `1,416–2,632`.
3. **Unfixed per-boss network/actor bombs & Zandronum `dumptrafficmeasure` blind spot**:
   - **SuperMegaman (`SuperMegaman_W.dec` & `BlueSpeciman_W.dec`)**:
     - `SuperMegaEndlessBeamDamager` spawned `3,800` invisible networked
       `BasicProjectile` segments (`38` per 2 tics) calling `A_JumpIfCloser(1200, "Appear")`,
       which emits `SetThingFrame` + `MoveThing` (`CLIENTUPDATE_FRAME | CLIENTUPDATE_POSITION`),
       plus `3,800` `IcePitFreeze` actors and `7,600` `HorseBountyStack` ACS calls.
       Because each segment hit `stop` during its spawn tick before reaching the end
       of `AActor::Tick()`, `NETTRAFFIC_AddActorTraffic` under-reported its bytes
       in `dumptrafficmeasure` (`0 B` shown despite tens of KB on the wire).
     - `SuperMegaEndlessBeamWallHit` spawned `4` networked `SuperMegaEndlessBeamShard`
       (`SpecimanBlockShard`) actors per 2 tics (`400` bouncing `BasicProjectile`s
       running `A_Jump(256)` + 9-tic server `A_FadeOut` -> `78,400 B` in
       `dumptrafficmeasure`).
     - `SuperMegaEndlessBeamSpawn` called `uh_CopyPointerAnglePitch` (`MoveThingExact`)
       and server `A_Stop` every 2 tics; client `SuperMegaEndlessBeam` overdrew `133`
       `Alpha 0.05` sprites at 9-unit spacing.
   - **ShinHellbot (`ShinHellBot_W.dec`) & sibling ZankokunaHellbot (`ZankokunaHellbot_W.dec`)**:
     - The `261113` fix had only updated `Set5` (`HelltatoruMoltenFireBallFadeFX`),
       leaving `Set4` (`HellApocMeteorAttackBoss_H` -> `100` `HellApocMeteorAttackBoss`
       calling redundant `A_ChangeFlag("RIPPER", 0)` -> `2,400` networked
       `HellTatoruShockwavePartBoss` in `3.1 s` -> `2.38 KB` peak 30ms spikes).
   - **SovietFrostBite (`SovietFrostBite_W.dec`)**:
     - `HailRainSpawnerBossHelper` and `HailRainSpawnerBoss` were networked and looped
       `ThrustThingZ(0, 999, 0, 0)` every tic (`40,174 + 3,324 B` in `dumptrafficmeasure`).
     - Razon 4 added mid-air `X_7A D 4 A_SpawnItemEx("IcePitFreeze")` to
       `HailRainShotBoss::Spawn` (`4,000+` `IcePitFreeze` actors, emitting `15,784 B`
       of `SERVERCOMMANDS_UpdateThingVelocity` packets even when `Factor 0` `Freeze`
       dealt zero knockback), plus `2,120` networked `SovietColdShotBit` splits (`47,256 B`).
     - `SovietColdShotFX` inherited `BasicGraphicEffect` instead of `BasicClientSide`.

### Implemented fixes

1. **`src/acs_source/classes/shared/copy_weapons/daily_team_ff.acs` & `tools/fixtures/daily_ff_cases.c`**:
   - Added a 64-slot per-player pawn-to-survivor-ID cache (`UH_DailyFFFindSurvivorCached`)
     and single-lookup `UH_DailyFFMakeOriginFromId`, short-circuiting non-survivors
     in `uh_DailyFFPointerOrigin` and eliminating the duplicate `FindSurvivorByActor` call.
2. **`src/actors/classes/bosses/BlueSpeciman_W.dec` & `SuperMegaman_W.dec`**:
   - Stripped `-USESPAWNEVENTSCRIPT` from `SpecimanBlockShard`,
     `SuperMegaFlightBoosterSmoke`, and `SuperMegaEndlessBeamSpawn`; moved
     `SpecimanBlockShard`'s 9-tic `A_FadeOut` to `+CLIENTSIDEONLY` `SpecimanBlockShardFadeFX`
     and removed its spawn-time `A_Jump(256)` frame broadcast.
   - Removed `uh_CopyPointerAnglePitch` and server `A_Stop` from
     `SuperMegaEndlessBeamSpawn` (computing child velocities directly from `velx/vely/velz`),
     and adjusted client `SuperMegaEndlessBeam` / `SuperMegaEndlessBeamEndFXChain` to
     `Scale 2.0`, `Alpha 0.16`, and 32-unit step (`37` vs `133` sprites).
   - Collapsed `SuperMegaEndlessBeamDamager`'s 38-segment chain into a single
     networked `FastProjectile` ray (`Speed 300`, `TNT1 AAAA 1`, `+RIPPER`,
     `Damage (150 * ...)`, `DamageType "EndlessBeamLauncher"`), retaining its custom
     `Obituary` and `Death.Ice` handling.
   - Split `SuperMegaEndlessBeamWallHit::Death` shards into `1` networked
     `SuperMegaEndlessBeamShard` (`Damage (35)`) + `3` `+CLIENTSIDEONLY` `SuperMegaEndlessBeamShardFX`.
3. **`src/actors/classes/bosses/ShinHellBot_W.dec` & sibling `ZankokunaHellbot_W.dec`**:
   - Stripped `-USESPAWNEVENTSCRIPT` and redundant `+RIPPER` / `A_ChangeFlag("RIPPER", 0)`
     from `HellApocMeteorAttackBoss` (`goto Spawn2+1`) and `HelltatoruMoltenwavePartBoss`;
     kept `HellApocMeteorAttackBoss_H` networked so `Radius_Quake` still replicates via NetID.
   - Made `HellTatoruShockwavesBoss` and `HellTatoruShockwavePartBoss` `+SERVERSIDEONLY`
     (`Renderstyle "None"`, 20-tic lifetime; identical `Obituary` falls back to `ShinHellbot_W`
     on remote clients) paired with deterministic `+CLIENTSIDEONLY`
     `HellTatoruShockwavesBossFX` / `HellTatoruShockwavePartBossFX` rings.
   - Applied the same fix to `ZankokunaHellbot_W.dec` (`HelltatoruMoltenFireBall`,
     `HelltatoruMoltenFireBallFadeFX_Z`, `HellTatoruMoltenWaves`/`FX`,
     `HellTatoruMoltenwavePart`/`FX`, `HellApocMeteorAttack`, `HellTatoruShockWaves`/`FX`,
     `HellTatoruShockwavePart`/`FX`, and `DecoyRapeCrushZ`).
4. **`src/actors/classes/bosses/SovietFrostBite_W.dec`**:
   - Marked `HailRainSpawnerBossHelper` and `HailRainSpawnerBoss` `+SERVERSIDEONLY`,
     passing initial Z velocity (`250`) via `HailRainSpawnerBoss_P` instead of
     looping `ThrustThingZ`, and spawning `HailRainShotBoss` with flags `17`.
   - Stripped `-USESPAWNEVENTSCRIPT` from `HailRainShotBoss` and `SovietColdShotBit`,
     removed mid-air `IcePitFreeze` from `HailRainShotBoss::Spawn`, split its
     `Death` hail bits into deterministic `(x + y)` 4-way `+SERVERSIDEONLY`
     `HailRainColdShotBit` + `+CLIENTSIDEONLY` `HailRainColdShotBitFX` (matching
     `SovietFrostBite_W`'s obituary), and restored `SovietColdShotFX` to `BasicClientSide`.

### Before/after benchmark & remote obituary verification

Measured against `out/build.pk3` with dedicated server + 2 clients (`BossClient` & `ObsClient`)
over loopback UDP proxy (`cl_capfps=1`, `use_mouse=0`, `use_joystick=0`). Note: baseline
`NETLAB` used LMS (`Idle` `11,168 B` including `~0.7 KB/s` `uh_ti_serverwatch`);
post-fix `NETLAB` ran DM (`Idle` `6,857 B`) with clean single-tap ultimate triggers:

| Scenario | Before UDP (B) | After UDP (B) | Peak 1s Before → After | Peak 30ms Before → After | Server CPU | Client NetID | `DailyFF` ACS Instr |
|---|---:|---:|---:|---:|---:|---:|---:|
| `idle` (6 s, `NETLAB`) | 11,168 (LMS) | 6,857 (DM) | 1.9 KB/s → 1.45 KB/s | 276 B → 93 B | 0.33s → 0.26s | 10 → 10 | 0 |
| `supermegaman_open` (11.5 s, `NETLAB`) | 163,656 | **47,615** (`-70.9%`) | 26.4 → **6.56 KB/s** | 1,619 B → **426 B** | 2.30s → **0.61s** (`-73.5%`) | 180 → **52** | 47.3M → **not in top 20** |
| `shinhellbot_open` (9.0 s, `NETLAB`) | 80,238 | **19,285** (`-76.0%`) | 23.2 → **3.91 KB/s** | 2,380 B → **295 B** | 1.92s → **0.50s** (`-74.0%`) | 480 → **49** | 26.0M → **not in top 20** |
| `sovietfrostbite_open` (12.0 s, `NETLAB`) | 126,970 | **36,283** (`-71.4%`) | 15.6 → **4.15 KB/s** | 1,109 B → **288 B** | 1.91s → **0.64s** (`-66.5%`) | 344 → **124** | 27.9M → **not in top 20** |
| `supermegaman_mm2dw1` (11.0 s, `MM2DW1`) | 107,923 | **53,396** (`-50.5%`) | 17.5 → **7.26 KB/s** | — → **1,063 B** | 1.38s → **0.77s** (`-44.2%`) | 238+ → **275** | not in top 20 |

Live 2-client Deathmatch runtime checks (`15/15 PASS`, zero engine/ACS warnings) confirmed
identical obituaries on server and remote client, client FX spawning, and `Death.Ice` (`IceDeathFlag=1`):
- `SuperMegaEndlessBeamDamager`: `Thanks to Endless Beam Launcher, ObsClient finally realized they shouldn't challenge Super Megaman (BossClient) at the expense of their mom!` (`IceDeathFlag=1`, plus `SuperMegaEndlessBeamShard` & `SuperMegaEndlessBeamShardFX` confirmed on wall hit).
- `ShinHellbot_W` / `HellApocMeteorAttackBoss` / `HellTatoruShockwavePartBoss`: `ObsClient was KPOW'D by Shin HellBot (BossClient)!` (`HellTatoruShockwavePartBossFX` on client, `0` networked shockwaves on client).
- `SovietFrostBite_W` / `HailRainShotBoss` / `HailRainColdShotBit`: `ObsClient was now shivering in fear due to Soviet FrostBite (BossClient).` (`HailRainColdShotBitFX` on client, `0` networked hail bits on client).
- `ZankokunaHellbot`: smoke-tested `HellApocMeteorSpawner` (`0` networked `HellTatoruShockwavePart`/`HellTatoruMoltenwavePart` on client).


# Unholy Team Info & Scoreboard Icons — Implementation Report

Implements `reports/unholy-team-info-and-scoreboard-icons-plan.md` (phases D1–D5).
Scope honoured: no `../references/` edits, no ZScript, no change to Unholy game
rules, engine Team is never faked.

## What shipped

### D1 — Semantics + client snapshot
- `src/acs_source/unholy/uh_round_helpers.acs` now owns the server senders:
  `UH_TeamInfo_BroadcastStatus`, `UH_TeamInfo_BroadcastOneVsAll`,
  `UH_TeamInfo_FullSnapshot`, `UH_TeamInfo_IsOneVsAllActive`,
  `UH_TeamInfo_OneVsAllTarget`, and a last-known portrait cache that survives
  death. `PlayerLifeStatusArr_UpdateFunc` broadcasts every change; the shared
  round-setup script pushes a full snapshot right after `isbonuseventactive` is
  cleared; every client re-snapshots on `ENTER` (late join).
- 1-vs-all is keyed on the active event's `UHBE_FLAG_ONEVSALL` plus the frozen
  `bossdataarr[0][BOSSDATA_TID]`, never on the target's morphable `PLS_EYE`.
  Broadcast at event commit, on `uh_SetBonusEventTarget`, on
  `ub_OneVsAllEvent` target freeze, and on `UH_TryFinishBonusEvent`.
- `src/acs_source/unholy/uh_teaminfo.acs` holds the client cache
  (`uhtilife`, persistent `uhtirole`, `uhtiportrait`, `uhtiova`,
  `uhtiovatarget`) and the single relation source `UH_AreDisplayTeammates`
  plus the TAB matrix `UH_CanSeeScoreIcon`. Named-script bridges
  `uh_IsUnholyTeamMode`, `uh_IsDisplayTeammate`, `uh_ScoreIconVisible`
  expose them to other libraries.

### D2 — SCORINFO built-in scoreboard
- `src/MAPINFO` declares `AddCustomData = "UHPlayerIcon", "Texture", ""`.
- `src/SCORINFO` defines the `UHPlayerIcon` custom Texture column with no
  `NOENEMIES`; `ColumnOrder` is fully owned so the column keeps `PlayerIcon`'s
  exact slot (plan's accepted "full ownership" option).
- `src/acs_source/hud/player_portraits.acs` is the single class → texture table
  (197 rows generated verbatim from the UIX `PBMug_*` registry).
- `src/acs_source/hud/scoreboard_icons.acs` is a `CLIENTSIDE` loop that, while
  the scoreboard is on screen (TAB or result sequence), writes
  `UHPlayerIcon` per row with `SetCustomPlayerValue` only when the value
  changes, and clears every row at map load.

### D3 — Native teammate bar
- `uh_assist_teaminfo` is registered through the MM8BDM Assist Display
  (inline `core_DefineAssistDisplay_S`, no DTADD import). It follows the camera
  TID, honours the new `uh_cl_teaminfo*` user cvars and `cl_drawcoopinfo` /
  `sv_nocoopinfo`, and yields to UIX. The renderer is a TLMS-style two-column
  SmallFont list (name, health/armor, weapon/ammo); dead rows are a user option.
  See "Native fallback rework" below for the live-data path.

### D4 — UIX v3bh shadow
- `src/acs_source/compat/mods/uix/uixteam.acs` is the v3bh source with a
  documented header; `_uix_v3bh/UXTBNUM.acs` is vendored for the compile.
- Only the player filter and the wrap-hide count changed: when
  `lastmanstanding` is active they use the Unholy side model; every other mode
  keeps the stock `PLAYERINFO_TEAM` path. `#library "UIXTEAM"`, compiled to
  `src/acs/UIXTEAM.o`, absent from `LOADACS` (shadows UIX when loaded after).

### D5 — Compile, package, docs
- `tools/compile-acs.sh` gained the `UIXTEAM` step.
- `AGENTS.md` documents the new lumps, fragment and shadow.
- Full ACS compile is clean; `out/build.pk3` repackaged and validated
  (16622 entries) containing `MAPINFO`, `SCORINFO` and `acs/UIXTEAM.o`.

## Deviations from the plan (with reasons)

1. **`src/GAMEINFO` → `src/MAPINFO`.** On Zandronum 3.3-alpha (the reference
   checkout) `AddCustomData` is a `gameinfo { }` property parsed only from
   MAPINFO/ZMAPINFO (`gi.cpp` + `g_mapinfo.cpp`); the standalone `GAMEINFO`
   lump is the launcher/IWAD one and ignores unknown keys. Verified against the
   engine source and the working precedent `trill-damagedisplay-v7h2/MAPINFO`.
2. **Syntax `AddCustomData = "UHPlayerIcon", "Texture", ""`.** The parser needs
   the `=` and a quoted type; the plan's unquoted form would not compile.
3. **SCORINFO ownership.** Full `ColumnOrder` ownership (not
   `RemoveFromColumnOrder` + `AddToColumnOrder`, which appends). Other SCORINFO
   addons that add columns must load before Unholy; an addon that also owns
   `ColumnOrder` and loads after wins.
4. **Portrait DB is the PBMug registry.** `Player.ScoreIcon` is not readable
   from ACS, and in this resource set the UIX mugshot and ScoreIcon coincide for
   the registered classes. The table is generated from
   `uh_uix_mugshots.acs`; regenerate it if that file changes. If a future class
   makes ScoreIcon and the mugshot diverge, split the table rather than alias.
5. **Weapon display uses the 8BDT weapon tables via a `UH_TOOLS` bridge**,
   not the raw actor class. `uh_WeaponTag_S` / `uh_WeaponAmmo1_S` /
   `uh_WeaponAmmo2_S` resolve the ready weapon (DTADD rows and buster upgrades)
   on the server; the client prints the localized tag plus Ammo1 and optional
   Ammo2. `uh_cl_teaminfo_weapon` controls the line.
6. **Dead rows keep the last role.** `UH_AreDisplayTeammates` answers by role
   (retained across `PLS_DEAD`), and the consumer's dead-row option decides
   visibility, matching the plan's UIX dead-row requirement.

## Native fallback rework (implemented)

The UIX Better Team Display path is unchanged.  The native fallback was
reworked after the review above; all five findings are addressed:

1. **Listen-server host cvars.** `uh_assist_teaminfo` resolves the local player
   once (with the camera-player fallback for `-host`) and passes both `viewer`
   and `cpn` into `UH_Ti_Draw`; the draw function no longer calls
   `ConsolePlayerNumber()`.
2. **Live stats are server-authoritative.** A server watch
   (`uh_ti_serverwatch`, 7-tic interval) builds a per-subject snapshot and
   sends it only to viewers authorized by `UH_Ti_ServerAreDisplayTeammates`
   through `NamedExecuteClientScript`.  The client renders a row only while the
   received `uhtistatvalid` flag is set, so a modified client cannot display an
   unauthorized subject.  Stats are cleared on role change, 1-vs-all change,
   disconnect and map load.
3. **Weapon line.** `UH_TOOLS` — the only UH library that imports 8BDT — now
   exposes `uh_WeaponTag_S` / `uh_WeaponAmmo1_S` / `uh_WeaponAmmo2_S`, which
   resolve the ready weapon through the MM8BDM weapon and buster-upgrade tables.
   The raw actor class is never printed.  The server appends Ammo1 and optional
   Ammo2, shows `-` when there is no Ammo1, and honors `DF_INFINITE_AMMO`.
4. **Independent toggles.** Name, health/armor and weapon/ammo are separate HUD
   messages, each controlled only by its own CVAR.
5. **Real scaling (partially implemented; baseline corrected below).** Changing
   the virtual `SetHudSize` does scale glyphs and layout together, but using
   `320x200` as the 100% baseline does not match Zandronum's TLMS text canvas.

The renderer mirrors `HUD_DrawCoopInfo`: two columns alternating left/right, a
vertical block every two teammates, three `SMALLFONT` lines per player (name,
`health / armor` colored by health percentage, weapon/ammo), anchored below the
chat area with `con_notifylines`.  Mugshots were dropped from the native
fallback (the SCORINFO portrait column and the UIX mugshot path are unaffected).
Dead rows stay optional and render `dead` with no weapon line.  Only HUD IDs
drawn on the preceding frame are cleared, plus a full clear when the bar is
disabled or UIX takes over.

### Dead-row lifetime (implemented)

Vanilla TLMS keeps a dead teammate's row while the body exists (health <= 0
draws `dead`) and drops it once the player becomes a spectator or their `mo`
is gone; the list then compacts.  The native fallback now matches:

- While `PlayerInGame(subject)` and `ClassifyActor(tid) != ACTOR_NONE`, the
  server keeps sending the subject and the client renders `dead` (when
  `uh_cl_teaminfo_dead` is on).
- On the in-game -> gone transition (dead spectator / corpse removed /
  disconnect), the server broadcasts `uh_ti_stat_clear` exactly once; the
  client clears that subject's stats and the renderer's `row` counter lets the
  following teammates fill the freed slot.
- `uhsrvWasingame[]` tracks the transition so the clear fires once per leave,
  and the subject re-registers on respawn/revival.

### Scale/alignment correction (implemented)

Both coupled coordinate bugs from the screenshot comparison are fixed in
`UH_Ti_Draw`:

1. **Canvas.** 100% is now the console virtual canvas
   (`con_virtualwidth` / `con_virtualheight`, defaults 640x480), not 320x200:
   `hudw = basew * 100 / scale`, `hudh = baseh * 100 / scale`.  At scale 100
   this matches built-in TLMS; 200 is twice its physical size and 50 is half.
   Line height (8) and block spacing stay in virtual units.
2. **Alignment.** HudMessage encodes alignment in the coordinate fraction:
   `.1` = left edge, `.2` = right edge, `.0` = center.  Even rows use
   `(offx * 1.0) + 0.1` and odd rows use `((hudw - offx) * 1.0) + 0.2`; each
   line's Y uses `.1` so all three lines are top-anchored like
   `HUD_DrawTextAligned`.  The `* 1.0` idiom is required because ACS does not
   promote `int + 0.1`, and `fixed` is not a declaration keyword in this ACC,
   so the fraction would otherwise be dropped.  `uh_cl_teaminfo_x` is now an
   inward margin from both edges (MENUDEF slider `0..160`), and `hudw / 2` is
   no longer used as an anchor.

The baseline now matches the Snipaste reference: compact `SMALLFONT` rows at
the upper corners, even entries flush left, odd entries flush right, first row
below `(1 + con_notifylines)` lines.  Verification is still owed at
640x480 / 1280x720 / 1920x1200 with scale 50/100/200 and both `con_scaletext`
states, comparing scale 100 against built-in TLMS with the same virtual size,
aspect option and physical resolution.

### TLMS parity fixes (implemented)

Three Bugbot findings were fixed:

1. **Canvas follows `con_scaletext`.** `UH_Ti_Draw` now picks the base canvas
   exactly like `C_UpdateVirtualScreen`'s `g_bScale`: the console virtual size
   (`con_virtualwidth` / `con_virtualheight`) only when `con_scaletext` is on
   and it differs from the real screen; otherwise the real
   `GetScreenWidth()` / `GetScreenHeight()` (the engine draws in real pixels
   when `g_bScale` is false).  100% therefore matches native TLMS in both
   `con_scaletext` states.
2. **16-bit HP.** `packed1` now stores HP and max HP as two unsigned 16-bit
   fields (`hp | (maxhp << 16)`), so the 30000 `MAX_HEALTH` bosses
   (BlueThwomp, ZankokunaHellbot) no longer clamp at 4095.  The client decodes
   with `& 65535` / `(>> 16) & 65535`.
3. **Native line colors.** The health number keeps the percentage color while
   `" / "` and armor are forced green (`\cD`), the weapon tag is green with
   Ammo1/Ammo2 in gold (`\cF`), and the no-Ammo1 `-` is red (`\cG`) —
   matching `HUD_DrawCoopInfo`'s `TEXTCOLOR_GREEN` / `TEXTCOLOR_GOLD` /
   `TEXTCOLOR_RED`.

### Remaining native-fallback caveats

- Row metrics are the engine's: cell height 12, per-line advance 13, block
  advance `4*12+3`.  A different `SMALLFONT` cell height would need the `fonth`
  constant adjusted; the previous 8 left the name and health/armor touching.
- The snapshot is throttled to 7 tics (~0.2 s), so teammate HP/ammo update a few
  times per second rather than every tic.
- A weapon absent from both the DTADD and buster tables yields no weapon line
  rather than an actor class name.

## Known caveats / follow-up

- On a **listen server** (`-host`) `ConsolePlayerNumber()` returns -1 even
  inside a CLIENTSIDE script, and a CLIENTSIDE `SetCustomPlayerValue` runs in
  the server process (`NETSTATE_SERVER`), so the host's write is broadcast.
  Mitigations: the assist display latches the camera player into
  `uhtilocalplayer` so the host still gets its own bar/cvars and permission set,
  and writes are change-gated so only genuine changes are sent. A
  dedicated-server deployment avoids the extra traffic entirely.
- Custom values are not reset on death/respawn by the engine; the per-map
  clear + on-open refresh cover it. The engine's own join/new-game reset does
  not inform other clients, which is why the scoreboard refreshes its whole row
  set every map.
- Runtime verification still owed (per plan D5 step 3), since static checks
  cannot prove: SCORINFO layout at multiple resolutions, UIX `UIXTEAM.o` shadow
  defeating the stock object, and two-client per-viewer icon divergence. Use the
  tracked launch profile with UIX before this pk3; the Unholy-only path does not
  require UIX.

## Built-in scoreboard portrait repair

### Symptom and corrected diagnosis

`Screenshot From 2026-09-20 23-13-25.png` shows solid black/green squares to
the left of player names, while `Snipaste_2026-09-20_23-16-13.png` from
classes-v9gh_ shows recognizable class faces.

The squares do **not** prove that `UHPlayerIcon` was parsed as a Color column.
Engine source confirms that the MAPINFO declaration
`AddCustomData = "UHPlayerIcon", "Texture", ""` makes the custom column a
`DATATYPE_TEXTURE`; `DataScoreColumn::DrawValue` then takes the texture drawing
path.  The reference classes mod also does not use a fundamentally different
asset format: `TEXTURES.C_ICONS` defines 32x32 face textures with
`XScale/YScale 4.0`, exactly the same effective 8x8 size used by the Unholy
`UMUG_*`, `UB*MUG` and `I_MUG*` definitions.

Later runtime evidence refines this diagnosis: portraits render correctly on
the result scoreboard.  Therefore the Texture declaration, the portrait names
and `SetCustomPlayerValue` transport are capable of drawing real faces.  The
solid squares seen during the in-game TAB view are not failed portraits.

There are **two independent in-game TAB issues**:

1. The current Unholy `ColumnOrder` still includes `CountryFlag` immediately
   after `UHPlayerIcon`.  The classes-v9gh_ reference explicitly comments out
   `CountryFlag`.  During in-game TAB, when `UHPlayerIcon` has not refreshed and
   is disabled as empty, the country column occupies the position immediately
   left of the player name.  The local player's configured country can appear
   as a mostly green cell, while bots/players without useful country data can
   appear black.  These are the reported green/black squares.  The original
   Unholy setup can expose the same native country/player metadata column, so
   its occurrence there does not implicate the new portrait code.
2. The new `UHPlayerIcon` implementation has an additional refresh defect.
   Its scoreboard loop is an `OPEN CLIENTSIDE` script and currently tests:

```c
GetPlayerInput(-1, INPUT_BUTTONS) & BT_SHOWSCORES
```

For `GetPlayerInput`, `-1` means the script's current activator.  An OPEN
script normally has no player activator, so TAB is not detected.  Refresh only
happens in `GAMESTATE_INRESULTSEQUENCE`; during an ordinary in-game TAB view,
`SetCustomPlayerValue` may never be reached.  This is a bug introduced by the
new per-viewer column, but it does not explain the original Unholy squares.

### Chosen repair

1. Resolve the local player exactly as the assist display does:

   ```c
   int viewer = ConsolePlayerNumber();
   if (viewer < 0) { viewer = uhtilocalplayer; }
   ```

2. Read scoreboard input from that explicit player slot:

   ```c
   bool shown = viewer >= 0
     && (GetPlayerInput(viewer, INPUT_BUTTONS) & BT_SHOWSCORES) != 0;
   ```

   Keep the result-sequence fallback.  Do not use `GetPlayerInput(-1, ...)` in
   the OPEN loop.

3. On the transition from hidden to shown, invalidate the icon write cache or
   compare it against the engine value returned by
   `GetCustomPlayerValue("UHPlayerIcon", i)`.  Comparing only against
   `uhtiiconset[i]` assumes nobody overwrote the engine-side value; that is
   already false on listen servers.  While the scoreboard stays open, refresh
   changed roles/classes normally.  On close, retaining the values is fine as
   long as the next open verifies the engine value.

4. Remove `"CountryFlag"` from Unholy's owned `ColumnOrder`, matching the
   classes-v9gh_ layout that defines the visual target.  This removes the
   unrelated green/black cells and ensures the only graphic immediately before
   `Player` is `UHPlayerIcon` (apart from status/artifact columns when they
   actually contain data).  Do not change the country-flag renderer or atlas;
   it is simply outside this scoreboard design.

5. Retain the existing portrait resources for the first repaired build.  The
   successful result scoreboard proves that wholesale generation of a new
   `USI*` asset set is unnecessary.  Keep a separate scoreboard mapping only
   where actual class mappings differ (for example LuckyLass uses `UMUG_6_`,
   not `UMUG_6`).  Consider dedicated pixel-adjusted icons only for individual
   faces that remain unreadable after the country column is removed and the TAB
   refresh is fixed.

6. Add a temporary diagnostic during implementation, then remove it:

   ```c
   str wanted = UH_ClientPortraitTex(i);
   SetCustomPlayerValue("UHPlayerIcon", i, wanted);
   str stored = GetCustomPlayerValue("UHPlayerIcon", i);
   ```

   For one known class, verify `wanted == stored` and that the texture name is
   the expected existing face texture.  This separates a data-path failure
   from an unrelated native column.  A correct stored name plus the already
   working result scoreboard proves SCORINFO and ACS transport.

### Listen-server limitation and safe policy

Per-viewer custom player data works locally on remote clients, but not safely
inside a listen-server process.  `PlayerData::SetValue` broadcasts every
server-state change to all clients.  The ACS API exposes no
`SVCF_ONLYTHISCLIENT` target argument, so one host cannot store a private
`UHPlayerIcon` value without altering every client's copy.

The safe supported policy is therefore:

- dedicated server + remote clients: full per-viewer portrait matrix;
- offline/single local process with no remote clients: local portraits are
  acceptable;
- listen server with remote clients: do not let the host write private custom
  values.  Prefer hiding the host's custom portrait column over broadcasting
  Survivor/Eye information incorrectly.  Remote clients may still compute
  their own local copies.

Do not describe “every client overwrites on open” as a complete mitigation:
the existing cache can suppress that correction, and simultaneous open
scoreboards can race.  Correctness requires either the safe host-disable policy
above or an engine/API change that can send custom player data to one client.

### Acceptance checks

- In-game TAB calls `UH_ScoreIcons_Refresh` immediately, not only during the
  result sequence.
- `CountryFlag` is absent from `ColumnOrder`; no solid green/black country cells
  remain beside player names.
- A known Survivor and Boss display recognizable 8x8 faces matching their
  existing `Player.ScoreIcon`/face texture.
- An empty/unauthorized value draws no placeholder and does not reserve the
  custom column when every row is empty.
- Regular LMS permission matrix: self, all Bosses, and Survivor teammates;
  Eye sees only self and Bosses.
- 1-vs-all exposes every assigned player's portrait.
- Dead Eye retains Eye permissions rather than becoming an unrestricted
  spectator; only a true spectator gets the spectator policy.
- Dedicated two-client test proves different viewers can hold different icon
  values for the same subject.
- Listen-server test confirms the host does not broadcast private values.

### Scoreboard repair (implemented)

- `scoreboard_icons.acs` resolves the viewer as `ConsolePlayerNumber()` with the
  `uhtilocalplayer` fallback and reads `GetPlayerInput(viewer, INPUT_BUTTONS)`
  — no more `GetPlayerInput(-1, ...)` in the OPEN loop, so in-game TAB refreshes
  instead of only the result sequence.
- Each write compares `GetCustomPlayerValue("UHPlayerIcon", i)` against the
  desired texture instead of a local cache, so a listen-host broadcast or join
  reset is corrected on the next open.
- `UH_ScoreIconVisibleEffective` grants see-all only to
  `PlayerIsSpectator(viewer) == 1`; dead spectators keep their role matrix (a
  dead Eye no longer sees Survivors).
- `SCORINFO` no longer lists `CountryFlag` (a native country/player
  metadata column, unrelated to the rows we own).
- The remaining green/black box was the native `PlayerColor` sub-column inside
  the `Player` composite: it draws a solid color box (team-colored in a team
  game, but a meaningless black/green rectangle in ordinary LMS).  Our SCORINFO
  re-declares `CompositeColumn "Player"` with
  `RemoveFromColumns = "PlayerColor"`, which clears it surgically while keeping
  the inherited gap/size.  This — not `CountryFlag` — was the reported box;
  removing `CountryFlag` alone did not fix it.
- The scoreboard uses a one-row override table for the only class whose
  `Player.ScoreIcon` differs from the UIX PBMug registry: `LuckyLass` →
  `UMUG_6_` (`UH_ScoreIconOverrideTex` in `player_portraits.acs`; the override
  list was generated by comparing all 251 DECORATE `Player.ScoreIcon` rows).
- Listen-server policy (hardened after Bugbot P1): `UH_ScoreIcons_HostBroadcastRisk`
  is simply `ConsolePlayerNumber() < 0`.  The earlier `PlayerCount() > 1` gate
  was unsafe because `PlayerCount()` excludes spectators and dead spectators, so
  the only remote player dying would drop it to 1 and let the host broadcast a
  private matrix.  On a listen host the column is always emptied
  (`UH_ScoreIcons_HostHide`; an empty broadcast leaks nothing) and never written;
  single-player/offline has a real consoleplayer and is unaffected.
- Dead-row parity for the override (Bugbot P2): `UH_ClientPortraitTex` caches the
  resolved scoreboard texture in `uhscoreiconcache[]` while the actor exists, so
  LuckyLass keeps `UMUG_6_` after death / body removal instead of falling back
  to the UIX PBMug name `UMUG_6`.  The server-synced index remains the last
  resort only when the client never saw the live class (late join after death).
- The temporary `wanted/stored` diagnostic from step 6 was not added because
  the work was verified statically rather than in-engine.

## Static verification performed

```
./tools/compile-acs.sh        # ACS COMPILE OK, 0 errors, incl. unholy + rz_debug + UIXTEAM
./tools/validate-build-pk3.sh # status=ok
unzip -Z1 out/build.pk3 | grep -E '^(MAPINFO|SCORINFO)$|UIXTEAM.o'  # present
```

## Next phase plan — role-aware scoreboard portrait visibility

This section is the implementation plan for the next scoreboard pass.  It
supersedes the older portrait permission matrix and the corresponding
acceptance bullets above; the already repaired SCORINFO layout, portrait
lookup/cache and listen-server safety policy remain unchanged.

### Required behavior

Apply the rules to the **viewer** of the scoreboard.  `self` means
`viewer == subject`.

#### Ordinary LMS

- Survivor viewer: show every assigned player's portrait.  A player who later
  morphs into an Eye remains visible because that transformation is globally
  announced.
- Boss viewer: show self, every other Boss, and every Eye; hide Survivors.
- Eye viewer: show self, every Boss, and every other Eye; hide Survivors.
- Bosses cannot morph into Eyes, so there is no Boss-to-Eye transition to
  preserve or special-case.

#### Bonus events

- FFA, including Boss FFA: show self only.
- 1-vs-all: show every assigned player's portrait.
- All-Eye: show every assigned player's portrait.  Everyone has the same
  disclosed role, so hiding faces conveys no useful information.
- Multi-vs-multi (currently Eyelento of Pain): an Eyelento shows self and
  other Eyelentos; a non-Eyelento shows self and other Survivors.

#### Viewer state and defensive fallback

- A dead viewer can spectate every player, so show all assigned portraits.
- A true spectator also sees all assigned portraits, including one who joined
  without ever receiving an Unholy role.
- Test death/spectator before the event and role branches; otherwise a dead
  FFA participant would incorrectly remain restricted to self.
- An invalid subject slot is hidden.  A subject whose synced role is
  `PLS_NULL` is also hidden, preventing stale or unassigned rows from leaking a
  cached face.
- Self is visible after subject validation, even if later policy data is
  malformed.
- Unknown viewer roles, unknown event policies, contradictory event-policy
  flags, invalid targets, or other illegal inputs fall back to self only.
  They must never fall through to the permissive ordinary-LMS behavior.

The intended evaluation order in `UH_CanSeeScoreIcon` is therefore:

1. Reject an invalid/unassigned subject.
2. Allow self.
3. If the viewer is valid and is dead, or is a true spectator, allow all
   assigned subjects.
4. Reject an invalid viewer or an invalid/unknown synchronized policy.
5. Apply the active bonus-event policy (`ONEVSALL`, `FFA`, `ALL_EYE`, or
   `MULTITEAM`).
6. For `NORMAL`, apply the ordinary-LMS role matrix above.
7. Default to hidden.

### Synchronize an explicit event policy

The client must not infer the active event from server-only globals such as
`isbonuseventactive`, `eventdataarr`, or `bossdataarr`.  Replace the narrow
`uhtiova` boolean with a synchronized portrait-policy value:

```c
#define UH_SCOREPOLICY_INVALID   -1
#define UH_SCOREPOLICY_NORMAL     0
#define UH_SCOREPOLICY_FFA        1
#define UH_SCOREPOLICY_ONEVSALL   2
#define UH_SCOREPOLICY_ALL_EYE    3
#define UH_SCOREPOLICY_MULTITEAM  4
```

Keep the frozen 1-vs-all target only if another display subsystem still needs
it; portrait visibility itself does not need the target because all portraits
are public in that policy.  `UH_AreDisplayTeammates` still needs its existing
target split and must not be silently changed by this scoreboard work.

Add `UHBE_FLAG_MULTITEAM` as a new, non-overlapping registry flag and assign it
to Eyelento of Pain.  Convert the active event flags to exactly one scoreboard
policy on the server.  Legal combinations are:

- `UHBE_FLAG_FFA` -> `FFA`
- `UHBE_FLAG_ONEVSALL` -> `ONEVSALL`
- `UHBE_FLAG_ALL_EYE` -> `ALL_EYE`
- `UHBE_FLAG_MULTITEAM` -> `MULTITEAM`
- no active bonus event -> `NORMAL`

`UHBE_FLAG_EYE_TEAM` is orthogonal metadata and is ignored for this
classification.  More than one of the four policy flags, or an active event
with none of them, maps to `INVALID`; do not resolve malformed combinations by
priority.  Consequently every bonus event must declare its portrait policy
explicitly.  Eyelento is the only existing event that needs the new flag; the
current FFA, one-vs-all and All-Eye definitions already carry their matching
flags.

Broadcast the policy through a dedicated CLIENTSIDE receiver (or extend the
existing receiver without exceeding ACS' argument limit).  Send it at all
state boundaries:

- ordinary round setup/reset (`NORMAL`);
- successful bonus-event commit, after its definition is known;
- bonus-event finish/cancel (`NORMAL` only after the event is no longer
  active);
- the full snapshot used by `ENTER`, so late joiners receive the current
  policy;
- any administrative path that replaces or aborts the active event.

Initialize the client cache to `INVALID`, not `NORMAL`.  Until the authoritative
snapshot arrives, the scoreboard consequently exposes only self.  When policy
or role changes, invalidate/refresh the affected icon values immediately; do
not wait for a close-and-reopen cycle if TAB is already held.

### Represent Eyelento teams with `PLS_EYE`

It is safe and useful to change successfully morphed Eyelento players from
`PLS_SURVIVOR` to `PLS_EYE`, provided the status change is coupled to morph
success:

```c
if (MorphActor(tid, "EyelentoMajorDemoneye", "", 0x7ffffffd,
    morphFlags, "GigaAstroExplode", "EyelentoMajorDemoneyeC"))
{
    int pn = tid - 1000;
    if (pn >= 0 && pn < MAX_PLAYERS
        && playerlifestatusarr[pn] == PLS_SURVIVOR)
    {
        PlayerLifeStatusArr_UpdateFunc(pn, PLS_EYE);
    }
}
```

Use the existing literal flag expression if extracting `morphFlags` would
require an unsupported ACS declaration or change compilation behavior.  Never
update the status merely because the player was randomly selected: a failed
`MorphActor` would corrupt `totalplayersarr`, role synchronization and the
scoreboard team split.

The event deliberately caps the Eyelento count below the number of Survivors,
so moving successful morphs out of `PLS_SURVIVOR` leaves at least one Survivor
for `ub_WatchSurvivors(true)`.  Nevertheless, audit these related paths while
implementing:

- revival/rebuild must restore an Eyelento as `PLS_EYE`, not let generic bonus
  rebuilding coerce it to `PLS_SURVIVOR`;
- the event end condition remains actor-based
  (`ThingCountName("EyelentoMajorDemoneye", 0)`), so the status change must not
  replace or race that condition;
- death continues to set `PLS_DEAD`, while `uhtirole`/`uhsrvrole` retain the
  last non-dead `PLS_EYE` role for portrait caching;
- the native TLMS/UIX teammate display must keep its current semantics unless
  separately requested.  Do not make `UH_AreDisplayTeammates` treat all Eyes
  as teammates just because the scoreboard uses `PLS_EYE` for Eyelentos.

For `MULTITEAM`, the portrait relation is exact role equality limited to the
two expected sides: `PLS_EYE` sees `PLS_EYE`, and `PLS_SURVIVOR` sees
`PLS_SURVIVOR`.  Any Boss or unknown role in this policy is illegal and gets
self only.

### Implementation touch points

- `systems/bonus_events/uhadd.acs` (or the existing flag-definition owner):
  define `UHBE_FLAG_MULTITEAM` without renumbering existing flags.
- `systems/bonus_events/definitions/uh_bonusdefs.acs`: mark Eyelento of Pain as
  `UHBE_FLAG_MULTITEAM`.
- `unholy/uh_round_helpers.acs`: classify and broadcast the authoritative
  scoreboard policy; include it in the late-join/full snapshot and reset path.
- `unholy/uh_teaminfo.acs`: store the client policy and replace
  `UH_CanSeeScoreIcon` with the ordered matrix above.  Keep scoreboard policy
  separate from `UH_AreDisplayTeammates`.
- `unholy/uh_events.acs`: update an Eyelento player's life status only after a
  successful morph; cover event rebuild/revival as necessary.
- `hud/scoreboard_icons.acs`: no new permission logic; continue consuming the
  single `UH_CanSeeScoreIcon` result and refresh changed values while shown.

### Acceptance matrix

Test with at least three live roles where the branch permits it, plus a dead
viewer and a fresh spectator:

- Normal/Survivor: Survivor, Boss and Eye subjects are visible.
- Normal/Boss: Boss and Eye visible; Survivor hidden.
- Normal/Eye: Boss and Eye visible; Survivor hidden.
- FFA and Boss FFA: only self while alive.
- 1-vs-all: everyone visible while alive.
- All-Eye: everyone visible while alive.
- Eyelento/`PLS_EYE`: only self and other Eyelentos.
- Eyelento/`PLS_SURVIVOR`: only self and other Survivors.
- Dead viewer in every policy: all assigned subjects visible.
- True spectator in every policy: all assigned subjects visible.
- Invalid policy, conflicting flags, unknown live role, or incomplete initial
  snapshot: self only.
- Failed Eyelento morph: selected player remains `PLS_SURVIVOR`, and all role
  counters remain balanced.
- Successful Eyelento morph: status and retained role become `PLS_EYE`, the
  portrait changes immediately, and late joiners receive the same split.
- Dedicated two-client test: each living viewer receives the correct different
  matrix.  Listen-host behavior continues to follow the existing safe-hide
  policy and never broadcasts a private matrix.

Compile all affected ACS libraries, validate the packed PK3, then perform the
matrix test in a dedicated-server session.  Static compilation alone cannot
prove per-client custom-data isolation, spectator state, or live morph refresh.

## Role-aware scoreboard portrait visibility (implemented)

The plan above is implemented.  Static verification passed; the runtime matrix
test is still owed.

### Synchronized policy
- `UHBE_FLAG_MULTITEAM` (16) is a new non-overlapping registry flag in
  `_imports/uhdt.acs` with a public mirror in `_includes/mod_api/uhadd.acs`;
  Eyelento of Pain now carries it.
- `UH_SCOREPOLICY_INVALID/NORMAL/FFA/ONEVSALL/ALL_EYE/MULTITEAM` live in
  `uh_def.acs`.  The client cache `uhtiscorepolicy` starts `INVALID`.
- `UH_TeamInfo_ScorePolicy` (server, `uh_round_helpers.acs`) classifies the
  active event exactly: no event -> `NORMAL`; exactly one of the four policy
  flags -> that policy; a defined event with none or more than one ->
  `INVALID`, never resolved by priority.  `UHBE_FLAG_EYE_TEAM` is ignored.
- `UH_TeamInfo_BroadcastOneVsAll` now also emits
  `ACS_NamedExecuteAlways("uh_ti_sync_policy", 0, ...)`, so the policy is
  pushed on every existing boundary: round setup/reset via
  `UH_TeamInfo_FullSnapshot`, the `ENTER` late-join snapshot, event commit and
  failed-commit rollback, the 1-vs-all target freeze/re-freeze, and the unified
  `UH_TryFinishBonusEvent` finish/abort path (`NORMAL`, because
  `bonuseventended` is already set).
- The new `uh_ti_sync_policy` CLIENTSIDE receiver clamps anything outside the
  defined range to `INVALID`.

### Client matrix
`UH_CanSeeScoreIcon` is the single ordered matrix; `scoreboard_icons.acs` now
calls it directly and its private `UH_ScoreIconVisibleEffective` wrapper was
removed.  Order: invalid/`PLS_NULL` subject -> hidden; self -> visible; dead
viewer or connected true spectator -> all assigned subjects; invalid viewer or
`INVALID` policy -> self only; FFA -> self only; one-vs-all or all-eye -> all
assigned; multi-team -> exact `PLS_EYE`/`PLS_SURVIVOR` role equality (Boss or
unknown role -> self only); ordinary LMS -> Survivor viewer sees every assigned
portrait while Boss/Eye viewers see only Boss/Eye subjects; otherwise hidden.

### Eyelento teams
- `ub_EyelentoOfPain` updates a player to `PLS_EYE` only inside a successful
  `MorphActor` call and only while the player is still `PLS_SURVIVOR`, so a
  failed morph leaves `totalplayersarr`, `uhsrvrole` and the scoreboard split
  balanced.
- `UH_IsEyelentoActor` (live actor class) drives the new
  `UHBE_FLAG_MULTITEAM` branch in `RebuildActiveRoundState`: a still-morphed
  Eyelento restores `PLS_EYE`, and a revived (engine-unmorphed) player returns
  to `PLS_SURVIVOR` instead of the generic branch coercing the side.
- `UH_AreDisplayTeammates` / `UH_Ti_ServerAreDisplayTeammates` are unchanged:
  the native TLMS/UIX teammate bar keeps its existing semantics and still keys
  the frozen 1-vs-all split on `uhtiova`/`uhtiovatarget`.
- `player_portraits.acs` gained one scoreboard-only override,
  `EyelentoMajorDemoneye -> I_MUG111`.  The morph body has no
  `PBMug_EyelentoMajorDemoneye` script, so without it the featured role would
  draw an empty texture; `I_MUG111` is the class's own `Player.ScoreIcon`
  (`EYE_F111`) and already ships in `TEXTURES.eyes.faces`.

### Static verification

```
./tools/compile-acs.sh        # ACS COMPILE OK, 0 errors/warnings
./tools/validate-build-pk3.sh # status=ok, 16623 entries
```

Runtime verification is still owed: the acceptance matrix (three live roles,
dead viewer, fresh spectator), per-viewer divergence on a dedicated server,
listen-host hide policy, and the Eyelento morph/revive transitions.

## P1 fix — per-client delivery for CLIENTSIDE receivers (implemented)

A dedicated-server test showed the team-info cache never reached remote
clients: `uhtirole[]` stayed `PLS_NULL` and `uhtiscorepolicy` stayed
`UH_SCOREPOLICY_INVALID`, so TAB had no `UHPlayerIcon` portraits.  The
receivers are `CLIENTSIDE` scripts, and the broadcasts were issued with
`ACS_NamedExecuteAlways`; on the tested engine a plain named execute of a
clientside script is not delivered to remote clients as an ACS execution
command.  Only `NamedExecuteClientScript` emits the per-client
`SVCF_ONLYTHISCLIENT` command.  (`uh_ti_stat` already used it, which is why
the teammate-stat snapshot worked while the role/policy sync did not.)

All team-info `CLIENTSIDE` receivers are now delivered per connected client:

- `uh_round_helpers.acs` adds `UH_Ti_IsConnectedClient` (the union of
  `PlayerInGame` and `PlayerIsSpectator != 0`, which is exactly the engine's
  `playeringame` / `PLAYER_IsValidPlayer`), plus `UH_Ti_SendStatusTo`,
  `UH_Ti_SendOneVsAllTo` and `UH_Ti_SendScorePolicyTo`.
- `UH_TeamInfo_BroadcastStatus`, `UH_TeamInfo_BroadcastOneVsAll` and the
  `uh_ti_stat_clear` transition now loop every connected client and send with
  `NamedExecuteClientScript`.
- `uh_ti_enter ENTER` sends the full snapshot only to the entering player
  (`PlayerNumber()` -> `UH_TeamInfo_SendSnapshotTo`), while round setup and
  the 1-vs-all re-freeze still use `UH_TeamInfo_FullSnapshot` for everyone.
- `UH_TeamInfo_WarmPortraits` refreshes the server portrait cache once per
  snapshot; `UH_Ti_SendSnapshotCore` then reads `UH_Ti_CachedPortrait`
  instead of rescanning the 197-row class table for every client.

Static verification:

```
./tools/compile-acs.sh        # ACS COMPILE OK, 0 errors/warnings
./tools/validate-build-pk3.sh # status=ok, 16623 entries
```

### Runtime verification (performed)

A local Zandronum 3.3-alpha bridge session (the `tools/mcp` harness with the
engine from `~/mcpfiles/zandronum-mcp`) reproduced the reported failure and
then confirmed the fix:

- A remote client connected to a `-lastmanstanding` listen server.  While it
  was still a **spectator** (the console `join` command not yet issued), its
  map vars read `uhtirole[] = -1`, `uhtilife[] = -1`,
  `uhtiscorepolicy = -1` — the reported symptom.
- After the client ran the console `join` command and spawned (actor
  `Trapist`, health 925), the synced values became
  `uhtirole[0..1] = [1, 2]`, `uhtilife[0..1] = [1, 2]` and
  `uhtiscorepolicy = 0` (`UH_SCOREPOLICY_NORMAL`), matching the server's
  `Player 0 is alive` / `Player 1 is alive` + boss-morph round.
- Running the receivers locally on the client (`run_script uh_ti_sync_policy 0`)
  also set `uhtiscorepolicy = 0`, isolating the fix to delivery rather than the
  receiver logic.

The per-client `NamedExecuteClientScript` path is therefore confirmed to reach
a remote client, whereas the pre-fix `ACS_NamedExecuteAlways` path left the
caches at their `PLS_NULL` / `INVALID` defaults.  The probe is now the
standing gate `tools/mcp/team-info-sync-test.mjs` (`--json` / `--dry-run`),
documented in `tools/README.md`.
## P1 follow-up — spectator hello for clients that never spawn (implemented)

A client that connects but never runs `join` is a true spectator and never
spawns, so the `uh_ti_enter ENTER` snapshot never fires for it.  Its cache
stayed `PLS_NULL` / `INVALID`, and because the scoreboard matrix hides any
subject whose `uhtirole` is `PLS_NULL`, even the public spectator rule could
not draw anything.

`UH_Ti_ServerHelloClients` (called at the top of `UH_Ti_RefreshStats`, i.e.
the 7-tic server watch) detects each newly connected client, including true
spectators, and repeats the full snapshot for ~0.6 s so it survives the
client's own `uh_ti_clientinit_cs` reset at map load.  The seen/tick tracking
arrays are map-scope, and the server `DISCONNECT` handler
(`ub_Disconnect_ChangeIsAlive` -> `UH_Ti_ServerForgetClient`) clears the slot
immediately, so a disconnect followed by a same-slot reconnect between two
watch polls still receives its own hello.

The `tools/mcp/team-info-sync-test.mjs` gate now proves every receiver over
the network and requires it for a pass:

- spectator hello + roles: a connected-but-not-joined client reads a valid
  `uhtiscorepolicy` and the in-game bots' `uhtirole[]` (the round role gather
  is forced; a mid-round bot join is not assigned a role on its own).
- `uh_ti_sync_ova`: `uhtiova`/`uhtiovatarget` are perturbed to a sentinel
  before `join`, so the re-delivered `0`/`-1` is an active overwrite, not a
  default value.
- `uh_ti_stat` / `uh_ti_stat_clear`: a true spectator is seeded from two
  bots, then `removebot` clears exactly one slot while the other stays set.
- `uh_ti_sync_status`: every still-NULL slot is sentineled before `join`, so
  the join must actively write the joining player's own `uhtirole` AND
  `uhtilife` — an already-valid bot row cannot satisfy it.

The local `run_script` round-trip is recorded as a diagnostic only and cannot
satisfy the pass condition, so a broken sender cannot let the gate pass.

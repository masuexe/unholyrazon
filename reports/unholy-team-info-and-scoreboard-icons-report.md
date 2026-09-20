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
- Listen-server policy: `UH_ScoreIcons_HostBroadcastRisk` (consoleplayer < 0
  and `PlayerCount() > 1`) makes the host empty its shared custom values
  (`UH_ScoreIcons_HostHide`; an empty broadcast leaks nothing) instead of
  writing a private matrix, while remote clients compute their own copies.
- The temporary `wanted/stored` diagnostic from step 6 was not added because
  the work was verified statically rather than in-engine.

## Static verification performed

```
./tools/compile-acs.sh        # ACS COMPILE OK, 0 errors, incl. unholy + rz_debug + UIXTEAM
./tools/validate-build-pk3.sh # status=ok
unzip -Z1 out/build.pk3 | grep -E '^(MAPINFO|SCORINFO)$|UIXTEAM.o'  # present
```

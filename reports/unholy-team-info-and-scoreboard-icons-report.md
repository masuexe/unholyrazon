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

### Remaining native-fallback caveats

- `lineh` is a fixed 8 virtual units; if MM8BDM's `SMALLFONT` has a different
  height the row pitch needs a one-line adjustment.
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

## Static verification performed

```
./tools/compile-acs.sh        # ACS COMPILE OK, 0 errors, incl. unholy + rz_debug + UIXTEAM
./tools/validate-build-pk3.sh # status=ok
unzip -Z1 out/build.pk3 | grep -E '^(MAPINFO|SCORINFO)$|UIXTEAM.o'  # present
```

# Boss stage portraits

TimemanC and KFCDragon756 use their existing `IsPissedFlag` to select stage 1.
The ordinary face remains stage 0. Their stage textures are `UB091MPG` and
`UB069MPG`; the boss health bar uses the original `PFACE91` and `PFACE69` fonts.

Register a variant next to the actor's ordinary presentation:

```acs
DefineTeamPhasePresentation("YourBoss", 1, "YourSecondStageFlag",
  "YOURMPG", "", "YOURRAW");
```

Call this from both `OPEN` and `OPEN CLIENTSIDE`, just like
`DefineTeamPresentation`. The built-in registrations live in
`src/acs_source/classes/bosses/boss_phase_presentations.acs`; ordinary generated
presentation files need no manual edit.

The actor key is case-insensitive. Stages are explicit integers in 1..255;
when multiple trigger inventories are present the highest stage wins.
Re-registering the same actor/stage replaces that variant. The registry holds
128 variants independently of the 512 ordinary presentation rows.
An empty portrait retains the ordinary portrait. An empty score icon uses the
variant portrait when present, otherwise the ordinary score icon. An empty or
missing raw font retains the ordinary boss-HUD font. Unknown stages use the
ordinary presentation. Registration returns `UHTIP_OK`, `UHTIP_FAIL` or
`UHTIP_FULL`.

Only the server reads the trigger inventory. It sends a separate four-integer
`(player, definition kind, vanilla id, stage)` message through
`NamedExecuteClientScript`. Clients resolve textures from their own tables.
Custom definition ids, registration row numbers and ACS strings are never
network identities. For a custom class without a vanilla definition, a client
can apply the stage only to a body class it has observed locally; a peer that
never saw the class gets no face.

The bottom/side SBARINFO `playericon` still uses the actor's static
`Player.ScoreIcon`. TimemanC and both KFC weapon forms therefore attach a
`_ScriptBar` callback that overlays the resolved variant at the existing icon
coordinates (horizontal 186/184, vertical 20/0). The callback uses
`uh_GetTeamPortraitForTid`, including when spectating, and follows `MugshotFlag`,
`NoHealthBar`, `NoDrawScoreIcon` and the HUD mode. A 0.1-second message expires
when the stage resets, the camera/weapon changes or the icon is hidden.

The stage snapshot is independent of teammate-stat visibility. Changes are
polled every seven tics, and initial/late-join snapshots carry the current
stage. The boss bar reads the same registry every tic and includes the stage
in spare bits of its row payload, so a stage change redraws even when health
and armor stay unchanged. Death retains the final face. A cleared slot/map
reset clears the cache; a new live body re-evaluates its inventory. A genuine
new-stage change does not alter the gameplay boss id or announcement name.

## Verification

After compiling ACS and packing the mod, run:

```sh
node tools/mcp/boss-phase-test.mjs --json
```

The test uses the smoke profile, one dedicated server and one remote client.
It freezes/protects its subjects, toggles the existing flags through the
server diagnostic, and checks ordinary faces, each boss independently, both
stages together, reset, and a real spectator reconnect snapshot. Health must
remain unchanged, proving the refresh does not require damage. Body-less
death retention, slot reuse and reversed status/stage execution order are
additional controlled receiver checks.
The test also verifies the client registered the variants and can resolve
the raw/scaled fonts. It does not play through the actual gameplay animations
or visually inspect UIX layout.

Manual diagnostics (log level 3 or higher):

- Client: `pukename rz_debug_BossPhaseCheck` verifies both variant definitions/assets.
- Client: `pukename uh_ti_PhaseCacheDump <player>` logs stage and resolved textures.
- Server with `sv_cheats 1`: `pukename rz_debug_SetPortraitPhase always <player> <phase>`
  freezes/protects the subject; phase 0/1 clears/sets `IsPissedFlag` for the two
  bosses. Phase -1 only freezes/protects. Production watchers send all packets.

Reload the map after manual mutation probes to restore normal gameplay.

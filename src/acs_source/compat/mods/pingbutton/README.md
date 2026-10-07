# Unholy PingButton override

Based on `trill-pingbutton-v5h/acs_source/PNGBUTTN.acs`. Imports the shared
`_imports/uh_acsutils.acs`; no separate ACSUtils copy is needed. The shared
library contains the required math and 3D HUD subset, preserving v5h's
projection/text centering. PingButton passes its distance-scaling setting to
`HudSetDistanceScaleFactor` and resets drawing state before each marker.

Load **trill-pingbutton-v5h before Unholy**. The addon supplies its actors,
sounds, menus, CVARs, KEYCONF and LOADACS. Unholy shadows `acs/PNGBUTTN.o`,
keeping `#library "PINGBUTT"`. Do not add PNGBUTTN to Unholy's LOADACS: without
the addon, the override must remain inactive.

In Unholy ordinary LMS (`uh_IsUnholyTeamMode`):

- Normal, alert, heal, missing, death and locate pings are visible to every
  player and spectator, regardless of side. Dead viewers and chasecam viewers
  are allowed too.
- Personal show, sender mute, sound and death-ping settings still apply.
- Death pings survive the origin player's transition to spectator; disconnect
  still hides the ping. Existing non-death pings end when their origin becomes
  a spectator, as in the original addon.
- Locate still selects living **teammates**, using the server-authoritative
  `uh_AreGameplayTeammates` API, but the resulting markers are public. This
  means opposing players can see the locations revealed by the command.
- Alert portraits exclude teammates through the client display API. Portraits
  resolve through `uh_GetTeamPortraitForTid`, falling back to PBMug actors.

Other modes retain the original visibility rules. The locate loop additionally
ignores absent/dead/spectating players. An alert with no eligible nearby player
has no portrait.

Compile with native ACC (or use the existing `tools/compile-acs.sh`):

```sh
acc -i ../references/zandronum/acc-branch-zandronum \
  src/acs_source/_imports/uh_acsutils.acs src/acs/uh_acsutils.o
acc -i ../references/zandronum/acc-branch-zandronum \
  -i src/acs_source/_imports \
  src/acs_source/compat/mods/pingbutton/PNGBUTTN.acs src/acs/PNGBUTTN.o
```

After compiling, repackage `src/` into `out/build.pk3`. Restart the engine to
load the new ACS library.

Manual multiplayer checks: two opposing players and a spectator should all
see normal/alert/heal/missing pings, including in chasecam; death pings should
remain visible after death; locate should select living teammates and show
those markers to opponents too. Each viewer's show/mute/death/sound options
should still work. Also check an ordinary native team mode for stock filtering.

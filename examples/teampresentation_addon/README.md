# Team presentation example addon

Minimal second PK3 that gives a custom survivor class a teammate-bar name, a
teammate-bar/UIX mugshot and a scoreboard icon **without editing the main mod**.
It is the working form of the `DefineTeamPresentation` recipe at the top of
`src/acs_source/_includes/mod_api/uhadd.acs`.

## Pack

From this folder, zip contents (not the parent folder) into e.g.
`out/teampresentation_addon.pk3`:

```
LOADACS
KEYCONF
DECORATE
TEXTURES
acs/uh_extp.o
```

Compile ACS first (needs `uhadd.acs` on the include path — it is `#include`d, not
`#import`ed):

```powershell
New-Item -ItemType Directory -Force -Path acs | Out-Null
& "D:\AppFiles\ACC\acc.exe" `
  -i "..\..\src\acs_source\v6b_overrides\_includes\mod_api" `
  -i "..\..\src\acs_source\v6b_overrides\_includes\common" `
  -i "..\..\src\acs_source\_includes\mod_api" `
  -i "..\..\src\acs_source\_imports" `
  -i "D:\AppFiles\ACC" `
  acs_source\uh_extp.acs `
  acs\uh_extp.o
```

Note the lowercase `#include "uhadd.acs"`: ACC include paths are case-sensitive
on Linux/macOS.

## Load order

1. MM8BDM-v6b
2. Unholy `build.pk3` (main mod — loads `uhdt`, `uhaddr`, `uh_survdefs`, …)
3. This addon PK3

Addon `LOADACS` only needs `uh_extp`. Do **not** use `clearplayerclasses`; only
`addplayerclass` so the class lands at a KEYCONF index above the vanilla range.

## What it proves

| Row | Effect |
|-----|--------|
| `DefineSurvivor(-1, "UHExampleTerrance", …)` | the class is a survivor (identity) |
| `DefineTeamPresentation("UHExampleTerrance", "Example Terrance", "EXTPMUG", "EXTPICN", 0)` | teammate-bar short name, mugshot, scoreboard icon |
| `DefineTeamPresentation("UHExampleTerranceEx", "", "", "EXTPICN", 0)` | a morph body with no definition row still gets a scoreboard face |

Nothing in `src/acs_source/unholy/uh_teaminfo.acs`,
`src/acs_source/hud/player_portraits.acs`, `src/SCORINFO` or the UIX shadow is
touched — the addon goes through the same resolver the built-in classes use.

## Verify

```bash
node tools/mcp/team-presentation-test.mjs --profile mm8bdm-v6b-teampres-addon --addon --json
```

The gate asserts the addon row resolves to `Example Terrance` / `EXTPMUG` /
`EXTPICN` (i.e. the explicit short name and the addon's own textures, not the
colored `DefineSurvivor` name and not the raw actor class), alongside the
built-in table checks.

You can also dump the whole resolved table on any client:

```
puke rz_debug_TeamPresentationCheck
```

with `uh_cl_LogLevel 4` for the per-row DEBUG dump.

## Notes

- `shortName ""` falls back to the `DefineSurvivor` name (which carries color
  codes), then to the actor class. Register it explicitly for a bar label that
  differs from the broadcast name — the resolver never strips color codes or a
  `_U` suffix.
- `scoreIcon ""` means "same as portrait".
- Re-registering the same actor (any case) **replaces** the row, so a later
  addon can correct an earlier one.
- The server and every client must load the same addon set. A peer missing a row
  shows an empty face, never someone else's, because the synced identity is a
  `(kind, definition id)` rather than a table row index.
- Weapons still follow MM8BDM's `DefineWeapon`. An unregistered weapon simply
  drops the weapon line and falls back to the class name.

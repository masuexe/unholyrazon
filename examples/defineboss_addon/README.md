# DefineBoss example addon

Minimal second PK3 that registers one custom boss via `DefineBoss`, matching the UHADD recipe (OPEN + OPEN CLIENTSIDE twin).

## Pack

From this folder, zip contents (not the parent folder) into e.g. `out/defineboss_addon.pk3`:

```
LOADACS
DECORATE
acs/uh_exaddon.o
```

Compile ACS first (requires Unholy `uhadd.acs` on the include path):

```powershell
New-Item -ItemType Directory -Force -Path acs | Out-Null
& "D:\AppFiles\ACC\acc.exe" `
  -i "..\..\src\acs_source\v6b_overrides\_includes\mod_api" `
  -i "..\..\src\acs_source\v6b_overrides\_includes\common" `
  -i "..\..\src\acs_source\_includes\mod_api" `
  -i "..\..\src\acs_source\_imports" `
  -i "D:\AppFiles\ACC" `
  acs_source\uh_exaddon.acs `
  acs\uh_exaddon.o
```

## Load order

1. MM8BDM-v6b
2. Unholy `build.pk3` (main mod)
3. This addon PK3

Addon `LOADACS` only needs `uh_exaddon`; main mod already loads `uhdt` / `uhaddr` / `uh_bossdefs` / `unholy`.

## Test (singleplayer)

1. Main mod only: random LMS must not show "UH Phase3 Test".
2. Main + this addon; RCON `uh_sv_forcedboss1 -1`; start LMS → body is CuttyCut clone, HUD name "UH Example Boss", instructions from DefineBoss.
3. Shadow: `uh_sv_forcedboss1 300` (Shadowman fakeout) + `uh_sv_forcedshadowboss1 26` → after reveal, CuttyCut (id 26), not TrueBusterExpert.

## Test (online)

4. Host and joiners load main mod + this addon; force `-1`; clients must show "UH Example Boss" next to the mugshot (local UHDT filled by CLIENTSIDE twin).

## Morph setup hook

The example registers `uh_BossMorphSetup_UHExampleBoss` via
`SetBossMorphSetupByActor("UHExampleBoss", ...)`. That script runs after
`MorphActor`, before the first weapon `Ready`, and gives the boss the same two
lives as CuttyCut. This is where multi-weapon / ExtraLife / PowerLimit setup
belongs for custom bosses.

## CRUD example

`uh_exaddon_set_enabled(0)` calls `SetBossEnabledByActor`, keeps the row
queryable, and removes it from the random Boss pool. Passing `1` restores pool
eligibility. The script returns `UHDB_OK` (0) on success. For the full set of
update, count, and remove operations, see
`docs/modding/uhdt-identity-crud-contract.md` in the main repository. A removal
returns `UHDB_ERR_REFERENCED` while the music row or morph setup row exists;
those references must be removed first. Auto-assigned negative IDs remain
reserved for the lifetime of the map.

## Notes

- ForcedBoss / ForcedShadowBoss "none" is `-9999` (`UHBOSS_FAIL`), not `-1` (`-1` is the first custom id).
- Do not put `CLIENTSIDE` on main mod's `uh_DefineBoss_S` handler.
- The morph setup script runs on the server; do not mark it `CLIENTSIDE`.

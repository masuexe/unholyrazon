# DefineSurvivor example addon

Minimal second PK3: KEYCONF append + `DefineSurvivor(-1, …)` with OPEN + OPEN CLIENTSIDE twin.

## Pack

From this folder, zip contents into e.g. `out/definesurvivor_addon.pk3`:

```
LOADACS
KEYCONF
DECORATE
acs/uh_exsurv.o
```

Compile ACS first:

```powershell
New-Item -ItemType Directory -Force -Path acs | Out-Null
& "D:\AppFiles\ACC\acc.exe" `
  -i "..\..\src\acs_source\_includes\mod api" `
  -i "..\..\src\acs_source\_includes\common" `
  -i "D:\AppFiles\ACC" `
  acs_source\uh_exsurv.acs `
  acs\uh_exsurv.o
```

## Load order

1. MM8BDM-v6b
2. Unholy `build.pk3`
3. This addon PK3

Do **not** use `clearplayerclasses` in the addon — only `addplayerclass` so the class becomes KEYCONF index 59+.

## Test (singleplayer)

1. Main mod only: classes 0–58 unchanged.
2. Main + this addon: pick **UH Example Survivor** in player setup / class picker; start LMS as a survivor → stay as LuckyLass clone with display name from DECORATE.
3. Optional: `print FindSurvivorByActor` / getters via a puked debug script — table id is `-1` (first custom), mugshot resolves to `UMUG_6`.

## Test (online)

4. Host and joiners load main + addon; joiners must be able to select the class (KEYCONF) and CLIENTSIDE twin fills local uhdt for name/mugshot getters.

## Notes

- Shiny optional: define `UHExampleSurvivorShiny` if you want True Power morph; without it, morph fails → `S_ClassSpawnNo_P` (same as DecoyBot).
- Do not assume `PlayerClass() == survivorId` for addons; look up with `FindSurvivorByActor`.
- DecoyBot still only copies KEYCONF 1–58.

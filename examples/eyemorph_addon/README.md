# Eye-morph weighted-pool example addon

This small addon demonstrates the `UHADD.acs` eye-morph API.  Load it after
the Unholy PK3; it reuses the base game's sprites and classes, so no art lumps
are required.

The addon registers `UHExDemoneye`, then creates a private `UHExPotion` pool:

```acs
int eye = FindEyeByActor("UHExDemoneye");
DefineEyeMorphPool("UHExPotion");
SetEyeMorphPoolEntry("UHExPotion", eye,
    "UHExMorphShot", "UHExMorphBurst", "UHExMorphGiver", 3);
```

The second row uses the existing Ghost actors with weight 1, so the example
rolls custom:Ghost at 3:1.  `UHExMorphBaitItem` calls
`PickEyeMorphActor("UHExPotion", UHEM_SHOT)` from server ACS and spawns the
returned concrete actor.  A burst item would request `UHEM_BURST`; a direct
power pickup would request `UHEM_GIVER` and call `GiveInventory` instead.

Each effect actor has a fixed `MorphProjectile.PlayerClass` or
`PowerMorph.PlayerClass` in DECORATE.  This is required because Zandronum does
not allow that class property to be changed at runtime.

## Editing built-in pools

`MoneyBait` and `MoneyBomb` are ordinary named pools.  Addons can replace a
row by repeating its `(pool, eyeId)` key, or disable a row with weight `0`:

```acs
SetEyeMorphPoolEntry("MoneyBomb", 31,
    "", "Furry_MoolaB", "Furry_MoolaGiver", 0);
```

Register a custom eye first (`DefineDemoneye`), then use
`FindEyeByActor` to obtain its signed ID.  Registering an eye never adds it to
any pool implicitly.  Pool names are case-insensitive and weights are flat
integers in the range `0..1000000`.  `DefineEyeMorphPool`, `FindEyeMorphPool`,
and `SetEyeMorphPoolEntry` return `UHEM_FAIL` on invalid input; the weight
getter also returns `UHEM_FAIL` for an unknown pool/eye, while actor/pick
getters return an empty string when no actor is available.

## Compile and load

Compile the ACS from the project root with ACC (the include directory contains
`UHADD.acs`):

```powershell
New-Item -ItemType Directory -Force -Path examples\eyemorph_addon\acs | Out-Null
& "D:\AppFiles\ACC\acc.exe" `
  -i "src\acs_source\_includes\mod_api" `
  -i "src\acs_source\_includes\common" `
  -i "D:\AppFiles\ACC" `
  examples\eyemorph_addon\acs_source\uh_exeyemorph.acs `
  examples\eyemorph_addon\acs\uh_exeyemorph.o
```

Put `LOADACS`, `DECORATE`, and the compiled object into an addon PK3, then
load in this order:

1. `megagame.wad`
2. `mm8bdm-v6b.pk3`
3. `8bdm-v6b-miscfixes-v5.pk3`
4. Unholy `build.pk3`
5. this addon PK3

For a quick check, use `give UHExMorphBaitItem` and use it.  The item's ACS
helper preserves the source-to-projectile target pointer and the server's
selected actor is propagated to clients normally.

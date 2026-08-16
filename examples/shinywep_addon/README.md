# Shiny move-weapon example addon

Minimal second PK3 that attaches fully custom, frame-by-frame animated moves to
the shiny copy classes through the Unholy mod API:

| API | Attaches to | Trigger |
|-----|-------------|---------|
| `DefineShinyQwantMoveWep("YourMove_W", 3)` | QwantShiny | AltFire RNG, mixed with the vanilla 25 moves by weight (vanilla moves = weight 1 each) |
| `DefineShinyNegaSlotWep(26, "YourNegaL1_W", "", "")` | NegaManShiny | Full-charge slot 26 (26..33 available); participates in the `SNegaFlag` cycle |
| `DefineDecoyBotMoveWep("YourCopy_W")` | DecoyBot | Copy slot 59+; rolled by the flag swap for all three weapons, returns to the weapon that launched it |
| `DefineShinyMegaCopyWep("YourFire_P", 1)` | Shiny MegaMan | Mixed into the `S_MegamanMainRNG_P` fire pool (~83 vanilla leaves) |
| `DefineShinyMegaAltCopyWep("YourAltFire_P", 1)` | Shiny MegaMan | Mixed into the `S_MegamanAltRNG_P` pool (~23 vanilla leaves) |

## How a move works

1. The shiny weapon's Fire/AltFire calls an ACS dispatcher (server-side).
2. The dispatcher rolls the pool, then `GiveInventory` + `SetWeapon` the
   registered **move weapon** (a weapon actor you ship in your DECORATE).
3. The move weapon's `Select` state plays your whole animation — your sprites,
   your frame letters, your offsets, your durations, your sounds, your
   projectiles. Full freedom, no shared slots.
4. The last frame calls `uh_ShinyMoveReturn`: it switches back to the shiny
   weapon and removes the move weapon itself from inventory.

## Move weapon requirements (engine-enforced, copy these)

1. **Ammo gate**: `SetWeapon` requires `CheckAmmo(EitherFire)` to pass.
   Either give the weapon an ammo type the class already holds
   (`MyDestinyAmmo` / `S_NegaDuckAmmo` / `DecoyEnergyAmmo`) or use **no
   ammotype with `Weapon.AmmoUse 0`**. `+WEAPON.AMMO_OPTIONAL` does NOT help.
2. **Animate in `Select`**; make `Fire`/`AltFire` no-ops (`A_WeaponReady`) so a
   held button does not re-trigger.
3. First `Select` frame: `ACS_NamedExecuteWithResult("uh_ShinyMoveColor")`
   (team coloring; silent switch sound).
4. Last animation frame: `ACS_NamedExecuteWithResult("uh_ShinyMoveReturn")`.
5. NegaManShiny move weapons read the charge level in `Select` with
   `CallACS("uh_ShinyNegaGetChargeLevel")` (1..3) to pick the L1/L2/L3 anim.
6. Do **not** register the move weapon in any `player.weaponslot` (slotless).
7. Move costs are yours: with `Weapon.AmmoUse 0` the move is free; spend
   `A_TakeInventory("MyDestinyAmmo"/"S_NegaDuckAmmo"/"DecoyEnergyAmmo", N)`
   on an early animation frame if you want a cost.
8. Shiny MegaMan is different: register a **CustomInventory fire actor** whose
   `Pickup` does `A_FireCustomMissile`/`A_SpawnItemEx` (no weapon switch).

## Notes

- Qwant: the AltFire still pays its normal 2 `MyDestinyAmmo` before the roll.
- Nega: register contiguous slots starting at 26 to avoid buster gaps in the
  full-charge cycle; empty L2/L3 fall back to the L1 weapon.
- DecoyBot: custom slots enter the uniform flag swap pool automatically; bots
  do not roll custom slots unless you extend their AI yourself.
- Holding the button after the move returns re-triggers the RNG (same as the
  vanilla shiny moves).

## Pack

From this folder, zip contents into e.g. `out/shinywep_addon.pk3`:

```
LOADACS
DECORATE
acs/uh_exshiny.o
```

Compile ACS first:

```powershell
New-Item -ItemType Directory -Force -Path acs | Out-Null
& "D:\AppFiles\ACC\acc.exe" `
  -i "..\..\src\acs_source\_includes\mod api" `
  -i "..\..\src\acs_source\_includes\common" `
  -i "D:\AppFiles\ACC" `
  acs_source\uh_exshiny.acs `
  acs\uh_exshiny.o
```

## Load order

1. MM8BDM-v6b
2. Unholy `build.pk3`
3. This addon PK3

## Test (singleplayer)

1. Main mod only: shiny Qwant AltFire pool is the vanilla 25 moves; Nega full
   charge resets at slot 25; DecoyBot swap uses flags 0–58.
2. Main + this addon: pick Qwant and morph → AltFire occasionally plays the
   `UHExMoveFireBall_W` Select animation, then returns to `QwantShiny_W`.
   Nega full-charge cycle passes through slot 26 (L1 anim). DecoyBot may roll
   slot 59 → `UHExDecoyShot_W` returns to the weapon that launched it.
   Shiny MegaMan main/alt occasionally fires the example fire actor.
3. Online: host and joiners load main + addon; moves are server-dispatched and
   the switch is synced (`SetWeapon` server command + inventory sync).

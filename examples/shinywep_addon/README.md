# Shiny move-weapon example addon

Minimal second PK3 that attaches fully custom, frame-by-frame animated moves to
the shiny copy classes through the Unholy mod API:

| API | Attaches to | Trigger |
|-----|-------------|---------|
| `DefineShinyQwantMoveWep("YourMove_W", 3)` | QwantShiny | AltFire flat weighted pool (vanilla 25 already at weight 1) |
| `DefineShinyNegaSlotWep(26, "NegaShiny_Your_W", "", "")` | NegaManShiny | Full-charge cycle slot 26 (26..33); vanilla 1..25 already registered |
| `DefineDecoyBotMoveWep("DecoyCopy_Your_W1")` | DecoyBot | Held copies slot 59+; vanilla 0..58 already registered |
| `DefineDecoyBotShinyWep("DecoyCopy_Your_W1", "DecoyShiny_Your_W")` | DecoyBotShiny | Pairs the same slot with its M1 weapon; M2 cycles in registration order |
| `DefineShinyMegaCopyWep("ShinyMega_Your_P", UH_SHINYMEGA_M1, 5)` | Shiny MegaMan | Flat Fire pool (ordinary weight 5; DawnBreaker uses TRUE + weight 1) |
| `DefineShinyMegaCopyWep("ShinyMega_Your_P", UH_SHINYMEGA_M2, 19)` | Shiny MegaMan | Flat AltFire pool (ordinary weight 19) |

## How a move works

### Qwant (SetWeapon path)

1. AltFire ACS rolls the pool, then `GiveInventory` + `SetWeapon` your move weapon.
2. The move weapon's `Select` state plays your whole animation.
3. The last frame calls `uh_ShinyMoveReturn`: switches back and removes the move.

### NegaManShiny (held cycle)

1. Start on buster `NegaManShiny_W` (`SNegaFlag` 0). After each **full charge**,
   `uh_ShinyNegaAdvanceHeld` Gives the next registered slot weapon and Takes the
   current (SilentSelect). Tap / mid charge stay on the same held gun.
2. Ship **one** held actor per slot (prefer inherit `NegaShinyHeldBase_W`).
   Put charge tiers in `Fire1` / `Fire2` / `Fire3`; full charge ends with
   `goto Fire3End` (Advance). No per-shot SetWeapon / MoveReturn.
3. Register `DefineShinyNegaSlotWep(26, "YourHeld_W", "", "")` — L2/L3 unused.

### DecoyBot (held copies)

1. M2 roll picks three slot indices and `uh_DecoyBotApplyHeldWeps` Gives
   `DecoyCopy_<stem>_W1` / `_W2` / `_W3`, then Takes the previous three.
2. M1 fires the **currently held** copy weapon's `Fire` state directly — no
   SetWeapon / MoveReturn per shot.
3. Ship three actors (W2/W3 may inherit W1 and only change sprites / SlotNumber).
   Register once with `DefineDecoyBotMoveWep("DecoyCopy_Your_W1")` (stem stored).
4. For Shiny Decoy, inherit `DecoyBotShinyCycleBase_W`, implement `Fire`, and
   pair it with the same stem through `DefineDecoyBotShinyWep`. Old addon rows
   without a shiny partner remain valid and are skipped by Shiny Decoy's M2.

## Move weapon requirements

### Qwant

1. **Ammo gate**: `SetWeapon` requires `CheckAmmo(EitherFire)` to pass.
   Either give the weapon an ammo type the class already holds
   (`MyDestinyAmmo`) or use **no ammotype with Weapon.AmmoUse 0**.
   `+WEAPON.AMMO_OPTIONAL` does NOT help.
2. **Animate in `Select`**; make `Fire`/`AltFire` no-ops (`A_WeaponReady`) so a
   held button does not re-trigger.
3. First `Select` frame: `ACS_NamedExecuteWithResult("uh_ShinyMoveColor")`
   (team coloring; silent switch sound). After color: `A_WeaponReady(14)`.
4. Last animation frame: `uh_ShinyMoveReturn_cs` then `uh_ShinyMoveReturn`, then
   `goto Deselect`.
5. Do **not** register the move weapon in any `player.weaponslot` (slotless).

### NegaManShiny

1. Inherit `NegaShinyHeldBase_W` (or copy Charge / SilentSelect / Fire3End).
2. `Weapon.SlotNumber 1`, `S_NegaDuckAmmo`, AmmoUse 0, AmmoGive 0.
3. Override `Fire1` / `Fire2` / `Fire3`; L1/L2 end `goto Ready2` (or `Fire2End`);
   L3 end `goto Fire3End` so Advance runs.
4. Do **not** swap weapons mid-charge between tier actors.

### DecoyBot

1. Actors `DecoyCopy_<Name>_W1` / `_W2` / `_W3` with `Weapon.SlotNumber` 1/2/3.
2. Attack animation in **Fire**; end with `goto Ready` / `Ready2`.
3. `DecoyEnergyAmmo`, AmmoUse 0, AmmoGive 0; icons `C_I_50A` / `B` / `C`.

### Shiny MegaMan

Inherit `ShinyMegaBase_P`, name `ShinyMega_<Stem>_P`, register with
`DefineShinyMegaCopyWep(..., UH_SHINYMEGA_M1/M2/TRUE, weight)`. Ordinary M1=5,
M2=19. Pickup fires the attack (no weapon switch).

## Notes

- Qwant: the AltFire still pays its normal 2 `MyDestinyAmmo` before the roll.
- Nega: register contiguous slots starting at 26 to avoid gaps after slot 25;
  held cycle uses L1 only.
- DecoyBot: custom slots enter the uniform flag swap pool automatically.
- Holding the button after a Qwant move returns re-triggers the RNG.

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
  -i "..\..\src\acs_source\v6b_overrides\_includes\mod_api" `
  -i "..\..\src\acs_source\v6b_overrides\_includes\common" `
  -i "..\..\src\acs_source\_includes\mod_api" `
  -i "D:\AppFiles\ACC" `
  acs_source\uh_exshiny.acs `
  acs\uh_exshiny.o
```

## Load order

1. MM8BDM-v6b
2. Unholy `build.pk3`
3. This addon PK3

## Test (singleplayer)

1. Main mod only: shiny Qwant / Nega / Decoy / Mega all dispatch from ACS tables
   (vanilla rows registered by `UH_COPYDEFS`).
2. Main + this addon: pick Qwant and morph → AltFire occasionally plays the
   `UHExMoveFireBall_W` Select animation, then returns to `QwantShiny_W`.
   Nega full-charge cycle reaches slot 26 held `NegaShiny_UHExSlash_W` (Fire1/2/3).
   DecoyBot may roll slot 59 → held `DecoyCopy_UHExDecoyShot_W1/W2/W3`. Shiny
   MegaMan main/alt occasionally fires the example fire actor.
3. Online: host and joiners load main + addon; Qwant moves are
   server-dispatched (`SetWeapon`); Nega/Decoy held swaps sync via inventory
   Give/Take.

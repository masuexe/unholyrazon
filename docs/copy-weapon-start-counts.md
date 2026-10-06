# Opening copy-weapon counts

Under **Unholy Server Options → Rules → Copy Weapons**, press Enter to type:

| Setting | CVar | Default | Effective count |
| --- | --- | --- | --- |
| Qwant Starting Moves | `rz_sv_qwant_start_weapon_count` | 4 | 1 up to the registered move pool |
| NegaMan Starting Copy Weapons | `rz_sv_nega_start_weapon_count` | 3 | 1 up to the registered copy-weapon pool |

Enter positive integers. Nonpositive input is treated as one. Both classes get all
registered copy weapons when the requested count reaches or exceeds the pool
size. Both classes sample without duplicates and retain their base weapon;
the base weapon does not count toward this setting. Changes apply at the next
opening loadout grant, not to weapons already held by a living player.

Qwant's inventory is its complete move list, including registered addon moves.
Relearning replaces the currently selected move with an unowned move, without
changing the total move count. It costs 28 MoveRelearnAmmo only after a successful
replacement; owning all registered moves, insufficient ammo or an invalid current
weapon leaves the loadout and resource unchanged.

Pharaoh Roulette and the UIX fixed bar scan the complete held move list. The UIX
wheel uses seven fixed groups matching the actual weapon slots below. It uses the
engine's replicated inventory rather than the former four-index network snapshot.
A held-set change while the wheel is open closes it; reopening collects the new
loadout. Legacy MoveMem exposes only the first four held moves for compatibility
and no longer limits gameplay or the UI.

These settings are independent of daily damage and ammo randomization. For
MegaMan's M2 count and daily multiplier settings, see
[MegaMan daily weapons](megaman-daily-weapons.md).

## Qwant functional slots

Element type, ammo and move registration order are independent of these slots.
The UIX weapon bar and wheel use the same groups as weapon slot keys.

| Slot | Purpose | Moves |
| --- | --- | --- |
| 1 | Base | Qwant_W |
| 2 | Ranged | AttackOrder, FlameBurst, HiddenPower, IceShard, SonicBoom, ThunderWave, Toxic, WaterShuriken |
| 3 | Rapid fire | BulletSeed, ChargeBeam, DragonBreath, FreezeDry, IceBeam |
| 4 | Melee | AnchorShot, BlazeKick, FeintAttack, FlameWheel, Gust, LeafBlade, NeedleArm, NightSlash, RapidSpin, ShadowForce, ShadowPunch |
| 5 | Power | FireBlast, MoonBlast, Thunder, WaterSpout |
| 6 | Area / control | DazzlingGleam, NightDaze, RockSlide, Spikes |
| 7 | Defense / support | CalmMind, MatBlock, Moonlight |

For addon moves, set `Weapon.SlotNumber` and the third argument (`args[2]`) of
`<Weapon>_QwantBar` to the same slot (2–7). Keep the first argument as the element
and the second as the existing custom ammo setting. UIX treats missing or invalid
slot metadata as slot 2 for compatibility with older addons.

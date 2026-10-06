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
wheel reserves group 0 for the base weapon and distributes copy moves across up
to 11 other scrollable groups, following the NegaMan wheel layout. It uses the
engine's replicated inventory rather than the former four-index network snapshot.
A held-set change while the wheel is open closes it; reopening collects the new
loadout. Legacy MoveMem exposes only the first four held moves for compatibility
and no longer limits gameplay or the UI.

These settings are independent of daily damage and ammo randomization. For
MegaMan's M2 count and daily multiplier settings, see
[MegaMan daily weapons](megaman-daily-weapons.md).

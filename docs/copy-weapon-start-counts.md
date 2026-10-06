# Opening copy-weapon counts

Under **Unholy Server Options → Rules → Copy Weapons**, press Enter to type:

| Setting | CVar | Default | Effective count |
| --- | --- | --- | --- |
| Qwant Starting Moves (1-4) | `rz_sv_qwant_start_weapon_count` | 4 | 1–4, also limited by the registered move pool |
| NegaMan Starting Copy Weapons | `rz_sv_nega_start_weapon_count` | 3 | 1 up to the registered copy-weapon pool |

Enter positive integers. Nonpositive input is treated as one. NegaMan gets all
registered copy weapons when the requested count reaches or exceeds the pool
size. Both classes sample without duplicates and retain their base weapon;
the base weapon does not count toward this setting. Changes apply at the next
opening loadout grant, not to weapons already held by a living player.

Qwant retains its four-slot move-memory design. Counts above four are capped
at four; unused slots are empty, and relearning replaces one existing move
without filling the empty slots. The UIX weapon wheel and Pharaoh Roulette
recognize the reduced loadout. If a tiny addon move pool leaves no unlearned
move available, relearning stops rather than looping indefinitely.

These settings are independent of daily damage and ammo randomization. For
MegaMan's M2 count and daily multiplier settings, see
[MegaMan daily weapons](megaman-daily-weapons.md).

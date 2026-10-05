# MegaMan daily weapons

Open **Unholy Server Options → Rules → MegaMan Weapons**. Press Enter
on a numeric field to type its value. Multiplier fields accept decimals.
The damage switch grays out all damage settings; the independent friendly-fire
switch grays out its count fields. Turning a switch off preserves its settings.

## M2 loadout size

`Weapons Per M2` (`rz_sv_mega_m2_weapon_count`) sets how many copy weapons
MegaMan receives each time M2 replaces his loadout. The default is **3**,
reduced from the previous fixed six. Enter a positive integer; this setting is
independent of daily damage and friendly-fire randomization. The base Buster
is retained and does not count toward this limit.

Below six, random distinct slots contribute one weapon each. At six or more,
weapons are distributed as evenly as possible across the six slots: 6 gives
one per slot, 12 gives two per slot, and 7 gives one per slot plus a second
weapon in a random slot. When a slot runs out of candidates, the remaining
slots fill the shortfall. A request at or above the registered pool size gives
every copy weapon, including registered addons. No duplicate weapons are given.

Each M2 removes the previous copy-weapon loadout before giving the new one;
lowering the setting takes effect on the next M2. Fresh weapons are preferred
within each slot, with previous weapons reused only when needed to meet its
quota. Pharaoh Roulette recognizes the full owned loadout, including multiple
weapons in one slot. Nonpositive input is treated as one weapon at runtime.

## Daily randomization

| Category | Daily count defaults | Multiplier defaults |
| --- | --- | --- |
| Normal | All remaining weapons | 0.75–1.25 |
| Small jackpot | 2–4 | 2–3 |
| Big jackpot | 0–1 | 4–6 |
| Friendly fire | 6–10 | The weapon's damage multiplier |

Both jackpot tiers are enabled by default and have independent switches.
The former 40–60 and 80–120 jackpot draws have been removed.

The server's local calendar date determines each count, the selected weapons,
and each weapon's multiplier. The same date and settings produce the same
results after a map change or restart. Settings are read live; changing them
can change today's results. A date-keyed permutation assigns big jackpots
first, then small jackpots without duplicates. Friendly-fire selection is
independent and may overlap either tier. Each weapon gets its own multiplier
within its tier's range, rather than all jackpot weapons sharing one value.

Daily counts apply to the frozen official pool of 103 copy weapons, not the
configured number of weapons in one player's loadout. Addon weapons use the
normal multiplier range
and remain outside daily jackpot and friendly-fire selection.

## Console settings

The existing master switches remain `rz_sv_randmegamancopywepdmg` and
`rz_sv_randmegamancopywepteamkill`.

| Settings | Meaning |
| --- | --- |
| `rz_sv_mega_normal_mul_min`, `rz_sv_mega_normal_mul_max` | Normal multiplier range |
| `rz_sv_mega_small_enabled` | Small jackpot switch |
| `rz_sv_mega_small_count_min`, `rz_sv_mega_small_count_max` | Small jackpot count range |
| `rz_sv_mega_small_mul_min`, `rz_sv_mega_small_mul_max` | Small jackpot multiplier range |
| `rz_sv_mega_big_enabled` | Big jackpot switch |
| `rz_sv_mega_big_count_min`, `rz_sv_mega_big_count_max` | Big jackpot count range |
| `rz_sv_mega_big_mul_min`, `rz_sv_mega_big_mul_max` | Big jackpot multiplier range |
| `rz_sv_mega_ff_count_min`, `rz_sv_mega_ff_count_max` | Friendly-fire count range |

Equal endpoints give a fixed count or multiplier. Zero is supported; a count
minimum of zero allows a day without that tier. Reversed endpoints are swapped
when calculating results. Counts are clamped to 0–103; small jackpots use only
the capacity left after big jackpots. Multipliers must be finite numbers within
ACS's nonnegative 16.16 range (0–32767); negative values are treated as zero.
These adjustments apply to runtime results and do not rewrite saved settings.
MENUDEF's text fields use the engine's numeric conversion, so enter numbers
without units or other text.

Turning daily damage randomization off restores original base damage. The
existing PlantBarrier negative-damage/healing branch remains in place. Friendly
fire still obeys the existing team, protection, armor and engine damage rules.

The named diagnostics `uh_debug_ShowTodayDmgMul` and
`uh_debug_ShowTodayTeamFF` log today's multipliers and friendly-fire list.

# SinfulBusterExpert weapon unlocks

The host controls unlocks with `uh_sv_sbe_unlockmode`, an archived server CVAR.
It is also available under **Unholy Menu → Server Options → Boss Setup →
SinfulBusterExpert → Weapon Unlocks**.

| Value | Policy | Starting weapons | Later unlocks |
|---|---|---|---|
| `0` (default) | Unbound | W1–W7 | W8 at health <= 40% of spawn health |
| `1` | Progressive | W1 | W2–W8 at seven steps across the first 60% of spawn health lost |

Set it in the server console or server configuration:

```text
uh_sv_sbe_unlockmode 0
```

Use `1` to retain the previous Razon progression. Other values fall back to
Unbound. Ordinary clients cannot choose their own policy. The server samples
the setting during each boss morph; changing it during a fight affects the
next morph, including a re-morph, rather than changing the current loadout.

Both policies use the current eight weapon slots, attacks, ammo and HUD.
Unbound restores attack availability rather than the old single-weapon
`SinfulMode` inventory switcher. Once granted, weapons remain available after
healing. The final unlock plays the existing sound; starting weapons are
granted silently. Progressive retains its per-weapon unlock sounds and catches
up across multiple thresholds after a large hit.

Thresholds use the boss's scaled spawn health. At 6500 HP, Unbound grants W8
at 2600 HP. Progressive retains the previous integer rounding: its step is
`6500 * 6 / 10 / 7 = 557`, so W2 unlocks at 5943 HP and W8 at 2601 HP.

The policies live in `classes/bosses/sinful_buster_expert/unlock_unbound.acs`
and `unlock_progressive.acs`; `unlock_watcher.acs` owns inventory grants,
sounds and the death/unmorph lifecycle. All remain fragments of `uh_classes`;
no additional library or LOADACS entry is needed.

For a gameplay check, morph into boss 102 under each policy, check the starting
slots, then cross the health thresholds. Also check a hit crossing several
thresholds, healing, changing the CVAR mid-fight, and unmorph/re-morph. Compile
checks alone do not verify weapon delivery or menu behavior in multiplayer.

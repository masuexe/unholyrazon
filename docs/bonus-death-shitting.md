# Bonus Stage Death Shitting

In an LMS Bonus Stage, each player death triggers one random effect from the
razon3 pool. The server DEATH hook covers survivors, bosses and demoneye morph
bodies; a revived player can trigger another roll on their next death. Ordinary
boss rounds and pre-round deaths do not roll. The effect runs at death rather
than waiting for the old ClassBase death animation to finish.

The server setting `uh_sv_bonusdeathshitting` defaults to `true`. Change it in
**Unholy Server Options → Events → Bonus Stage Death Shitting**, or use
`uh_sv_bonusdeathshitting 0` / `uh_sv_bonusdeathshitting 1` in the server console.
It is checked at each death, so changes apply during the current stage. Disabling
it stops future rolls; existing spawned effects finish normally.

The adapted pool contains 39 equally likely top-level choices, with razon3's
nested probabilities retained. Five retired branches are omitted: fake items,
Bug Bomb, Boss Boxer, Wrecking Ralph and Mini Elemental. JustSpike uses PitSpike,
Stoptagon uses the existing ColdSummon explosion, and the revival mushroom uses
DickheadProjectile and the current revival system. The hidden Minivile branch
retains its three equally likely disguises. The hat branch uses named targets so
both hat outcomes spawn a pickup. The plant branch leaves the dead pawn's scale
unchanged (the old CustomInventory animation did not run over time).

Manual gameplay checks: force a Bonus Stage, kill players with the toggle on and
off, toggle it during the stage, and check a second death after revival. Compare
an ordinary boss round and a pre-round death, which should produce no roll.

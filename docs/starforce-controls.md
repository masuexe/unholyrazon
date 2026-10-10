# Star Force boss controls

The boss now uses one combat weapon:

| Existing input | Action |
| --- | --- |
| Primary fire | Buster; idle to charge, as before |
| Secondary fire | Hold shield |
| Reload | Use the next battle card; hold to continue in order |
| Previous weapon (normally wheel up) | Draw six cards when the custom gauge is full |
| Next weapon (normally wheel down) | Toggle card lock-on |

Reload starts the current card immediately when ready. Holding it uses the next
card after the current animation and cooldown finish; releasing it stops further
cards without cancelling the card already started. An empty hand stops the chain
and does not draw a new hand automatically.

Drawing replaces the remaining hand and consumes the full gauge. Lock-on keeps
its existing per-card eligibility. Both scroll inputs return to the combat
weapon; switching can wait until a firing/shield state allows it. A successful
scroll action starts an eight-tic shared cooldown. No new key binding is needed.
The directions refer to weapon commands, so custom wheel bindings can reverse them.

All three weapons inherit slot 1. Their explicit priorities are draw=100,
combat=101, lock=102. Do not assign them separate `Player.WeaponSlot` slots.
In the target Zandronum traversal, a scan returning to the starting slot hits
the `slotschecked < NUM_WEAPON_SLOTS` guard before scanning the remainder of
that slot. This explains RedWarrior's endpoint behavior: commenting its class
slot declarations leaves all six weapons in inherited slot 1. Registering
six separate slots restores wraparound. This is a traversal quirk, not a
configurable no-wrap flag; it depends on the slot table and owned weapons.
Custom player weapon-slot overrides or addons granting other weapons can
change this behavior and need their own compatibility test.

`WarRockStelar_W` keeps the buster and shield states and now owns the card
dispatcher in Reload. Card effect states live in that same actor so their Ready
transitions also check the card cooldown and remaining hand.
`WarRockStelar_Control_W` adds the explicit slot priority. The two old weapons remain defined for compatibility but are no
longer granted by boss setup. The card queue shifts five entries and explicitly
clears the sixth; it must never read index 6 of a six-entry hand.

After compiling `uh_classes`, `uh_bossdefs`, and `uh_bars` and packing the mod,
run the focused local regression:

```sh
node tools/mcp/starforce-input-test.mjs
# Or test a temporary packed snapshot:
node tools/mcp/starforce-input-test.mjs --pk3 /tmp/uh-scroll-final.pk3
```

It uses the smoke profile, an isolated config and the existing
`rz_debug_MorphMe 0 51` boss setup. It checks draw/lock return, same-direction
bursts, Reload release, cooldown gating, held Reload, six-card exhaustion, and
scrolling while firing or holding the shield. Burst commands submitted together exercise pending selections;
they are not a recording of a physical mouse wheel. Dedicated-server prediction,
latency and manual handling remain separate gameplay checks.

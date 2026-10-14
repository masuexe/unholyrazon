# Shootable actor extension slots

Unholy provides the CBM shootable-object slot pattern using UH names:

```text
UH_ShootableActor0
  → UH_ShootableActor1 … UH_ShootableActor50
  → UH_ShootableActor_Null
  → UH_ShootableActor
  → existing destructible walls, mines and other inheriting objects
```

The 50 slots are empty by default. They let addons extend shared damage
resistances, properties and state labels without replacing each individual
object. The existing base's damage factors and spawn-event behavior are
preserved; this does not change the player ClassBase extension slots.

## Addon usage

Choose an unused slot between 1 and 50. In an addon loaded **after Unholy**,
provide the same file path as that slot, for example:

```text
actors/unepic/shootable_slots/UHSlot1.dec
```

Keep the actor name and its preceding parent, adding your own properties:

```cpp
actor UH_ShootableActor1 : UH_ShootableActor0 {
  DamageFactor "MyAddonDamage", 0.5
}
```

The root includes this file automatically; do not also include it from your
addon's DECORATE. Slot N must inherit `UH_ShootableActor(N-1)`. Multiple addons
need different slots: addons overriding the same path replace each other's
definitions according to load order. Later slots and the final base can
override properties or state labels inherited from earlier slots.

These are actor extension slots, not weapon-selection slots. Only actors
inheriting `UH_ShootableActor_Null` or `UH_ShootableActor` receive their changes;
unrelated actors and base-game objects do not become descendants automatically.

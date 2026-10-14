# Coop enemy extension slots

Unholy uses an enemy extension chain with project-specific names and paths:

```text
GenericRobotSlot0
  → GenericRobotSlot1 … GenericRobotSlot50
  → GenericRobot
  → coop enemies and GenericRobotBoss descendants
```

The 50 slots are empty by default. They provide a separate extension point for
enemy damage resistances, properties and state labels. Existing enemy AI,
spawn/death effects and the no-infighting rule remain in `GenericRobot`.
Properties or labels defined by that class or a specific enemy override the
same properties or labels inherited from a slot.

## Addon usage

Choose an unused slot from 1 to 50. In an addon loaded **after Unholy**, provide
that slot's path, for example:

```text
actors/coopenemies/robot_slots/GenericRobotSlot1.dec
```

Keep its actor name and preceding parent:

```cpp
actor GenericRobotSlot1 : GenericRobotSlot0 {
  DamageFactor "MyAddonDamage", 0.5
}
```

Slot 2 inherits `GenericRobotSlot1`, and each later slot inherits the
preceding numbered slot. Unholy includes these files automatically; do not
include the overridden file a second time from your addon. Use different slots
for different addons, since overrides of the same path replace each other.

These slots are independent of the [shootable-object slots](shootable-actor-slots.md)
and player ClassBase slots. Only enemies descending from `GenericRobot` receive
their changes; unrelated base-game monsters do not join the chain automatically.

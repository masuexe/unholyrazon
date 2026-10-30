# Void Walker elemental orbs

Each elemental orb has an independent, server-owned `VWOrbHitbox` with a radius
of 16 and a height of 32.

Its default `Health 1000` supplies the base HP;
`UH_VW_ORB_HP_ADD` supplies the 150-HP population increment. Initialization asks
the round-owned `uh_GetScaledBossHealth` query to apply the same formula and
health cap as Boss morphs and later phases. For a positive round Boss count B
and current participant count P, HP is
`min(1000 + P * 150 / B - 150 / B, MAX_HEALTH)`, with integer division in that
order. A zero Boss count uses the base HP, matching debug/forced morph fallback
behavior. Current HP and the `user_vwMaxHealth` starting-pool snapshot are set
once at spawn. Zandronum only allows `APROP_SpawnHealth` writes on player pawns, so
nonplayer consumers must use this snapshot rather than the class default when
reading the orb's full HP. Later population changes never heal, damage or
resize an existing orb. A new morph takes a fresh snapshot.

The existing `VeryFunOrb` actors retain movement and spell execution. The hitbox follows its visual controller with a
16-unit downward offset: the 16x16 sprite is centered at its origin and uses
scale 2. Hidden/fading controllers below alpha 0.5 disable the hitbox; the damage
event checks visibility again to cover the interval between state ticks.

The hitbox's `master` points to the exact Boss pawn and `tracer` to the visual
controller. Its element index and UHDT morph generation are captured at spawn.
Owner validity requires a live, connected, real Void Walker of that generation
who still owns the elemental weapon. This prevents a stale death callback from
revoking a weapon restored by a later morph. Damage-event pointers are captured
before nested named-script calls, which reset the engine's current-script
context in the target Zandronum source.

`voidwalker_orbs.acs` belongs to `uh_classes`, which already imports UHDT for
morph generations. Its four-row table owns the element/weapon/command mapping.
Weapon ownership records which elements remain; no separate broken-orb mask is
maintained. Self damage and UH gameplay teammates are rejected before armor or
death processing; other damage retains the normal event result and modifiers.

A real hitbox death removes that element's M1/M2 commands and weapon, retires the
visual controller, and selects a surviving weapon when necessary. Fire charge
and the selected weapon's item lock are cleared; breaking an active Frigid
Freezer also performs its normal armor cleanup. If all four weapons are gone,
`VoidWalker_W5` provides the ammo-free Void Shot (60 damage, 14-tic fire cycle).
The fallback is registered with the native multiweapon list and UIX fixed wheel.

Normal owner/controller retirement uses a separate `Cleanup` state without
weapon revocation. A new morph restores the four elemental weapons and clears
old commands and the fallback. The `_W5` name also lets the existing Boss weapon
family cleanup strip the fallback when the player unmorphs.

Runtime regression: `python3 tools/mcp/voidwalker-orbs-test.py`.

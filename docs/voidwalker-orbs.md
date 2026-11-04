# Void Walker elemental orbs

Each elemental orb has an independent, server-owned `VWOrbHitbox` with a radius
of 16 and a height of 32.

Its default `Health 4750` supplies the base HP;
`UH_VW_ORB_HP_ADD` supplies the 385-HP population increment (matching the
Void Walker body's base health and population scaling). Initialization asks
the round-owned `uh_GetScaledBossHealth` query to apply the same formula and
health cap as Boss morphs and later phases. For a positive round Boss count B
and current participant count P, HP is
`min(4750 + P * 385 / B - 385 / B, MAX_HEALTH)`, with integer division in that
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

Void Walker uses `VWTargetMarker` / `VWTargetTracer` for cursor positioning.
The tracer and hitboxes share the `Culex` species. The tracer uses
`THRUSPECIES` to cross orb hitboxes. Void Walker attacks share this filter
through `VWProjectile`. Walls and other shootable actors retain their original marker
behavior. `UH_TargetMarker.SetupAimPoint` is the shared watcher setup state,
allowing this tracer choice without duplicating the marker lifecycle.

Normal owner/controller retirement uses a separate `Cleanup` state without
weapon revocation. A new morph restores the four elemental weapons and clears
old commands and the fallback. The `_W5` name also lets the existing Boss weapon
family cleanup strip the fallback when the player unmorphs.

## HUD health monitoring

Orb health snapshots synchronize from the server hitbox to the owner's inventory
tokens (`VWOrbHP0`..`VWOrbHP3` and `VWOrbMaxHP`) only when current HP changes.
The HUD in `boss_bars.acs` computes each orb's remaining percentage (`0%..100%`)
and displays an element-colored 4-orb matrix on both horizontal and vertical HUDs:
- **Horizontal HUD**: Sits above the ammo bar and icon (`x = 50.1, y = 166.1`),
  arranged in two compact lines (`W`/`E` on top, `A`/`F` on bottom).
- **Vertical HUD**: Positioned beside the health bar (`x = 34.1, y = 14.1`) as
  a clean 4-line list.
- **Dynamic highlighting**: The currently equipped orb is highlighted with white
  brackets `[ ]`; low-health orbs `<= 25%` turn red (`\cr`); destroyed orbs display
  as dimmed `\cu--%`.
- **UIX / v6c Weapon Wheel integration**: `VWOrbHP0`..`VWOrbHP3` are bound as `ammo2`
  in `uh_uixfw_boss_defs.acs`, giving the weapon wheel and weapon bar built-in secondary
  meter support for each slot.

Runtime regression: `python3 tools/mcp/voidwalker-orbs-test.py`.

Void Walker projectiles inherit `VWProjectile`, which centralizes `Species "Culex"`
and `THRUSPECIES`. Orb hitboxes and the positioning tracer share that species.
This preserves the existing Terra Mine collision group while allowing elemental
shots, fire fragments, and Void Shot to pass through orbs. Terra Mine retains
its shootable base and explicit species settings. Other shootable targets and
walls keep their existing collision behavior.

## Phase two controls

Phase two restores all four elemental weapons and adds the core in Slot 5.
All five slots share 200 boss ammo and 1000 rage. Primary attacks cost no ammo;
secondary attacks deduct the listed amount on release. Reload consumes rage,
leaving any remainder available for another elemental ultimate. Every spell
has a networked announcement. The green orb retains its existing controls.

| Slot | Primary: tap / charge | Secondary: tap / charge | Reload |
| --- | --- | --- | --- |
| 1, Wind | Lightning Orb / Electroshock | Bolt (30) / Light Beam (60) / Static E! (90) | Petal Blast (500 rage) |
| 2, Earth | Blast / Boulder (70 tics) | Storm (30) / Water Blast (60) | Sand Storm (500 rage) |
| 3, Water | Crystal / Ice Rock (18 tics) / Solidify (42 tics) | Diamond Saw (30) | Blizzard (500 rage) |
| 4, Fire | Drain / Mega Drain (35 tics) | Flame (30) / Flame Wall (60) | Corona (500 rage) |
| 5, Core | Flame Stone / Dark Star (35 tics) | Shredder (30) / Meteor Blast (60) | Final Claw (1000 rage) |

Two-stage secondary attacks charge for 24 tics. If less than 60 ammo remains,
release falls back to the 30-ammo spell. Rage Rune accelerates the new charge
counters. Weapon destruction and deselection clear the shared charge counter.

`voidwalker_phase2.acs` remains part of `uh_classes`. Delayed spells capture the
owner's morph generation and stop when that body is no longer valid. Targeted
casts select enemies within 2048 map units and line of sight; Diamond Saw uses
a forward 90-degree cone and an 1800-unit range. Its first pair travels at
32 units per tic along the boss's forward +/-45-degree directions. After
18 tics, its second pair spawns 448 units diagonally back from the captured
target point and converges on it. Without a valid target the anchor lies
800 units along the crosshair. Each blade lasts 28 tics. `NOINTERACTION`
provides movement through geometry; repeated native `A_Explode` calls supply
cutting damage with the engine's normal radius-damage visibility rules.

Light Beam is the Wind orb's 60-ammo stage, and it now matches the source
spell, which the remake calls Light Bubble. `VWLightBubble` is a
`NOINTERACTION` actor: it ignores geometry, travels 144 units over four
two-tic frames at Speed 18, then bursts. The flight is short on purpose,
because the burst is the attack: a long flight only moves the damage away from
the target. The burst runs `uh_VWLightBubbleBurst`, which gives every enemy
survivor within 160 units a direct 30-damage `LightBeam` hit. That type is an alias in the shared Bubble
damage event (`UH_BUBBLE_ALIAS_DAMAGETYPE`), so the hit also applies the Bubble
status and traps the target for its normal 88 tics. The direct hit is
deliberate: the event refuses a hit that is not effective, and radius damage
would lose the damage type on its visibility path. The range argument passed to
`UH_VWEnemy` is only the eligibility filter, so it is 4096: the burst geometry
is the separate 160-unit check around the burst point. A short range there would
reject every victim of a burst that lands away from the boss.
`VWLightBubble` itself deals no damage, so its `DamageType` only supplies the
obituary and the protection entry.

Static E! is the Wind orb's 90-ammo stage. It is not a projectile: the weapon
hands the cast to `uh_VWCast` spell 9, which damages every enemy survivor
within 4096 units three times for 18 damage. It never checks line of sight, so
walls and cover cannot stop it, matching the source spell, which hits the whole
screen and cannot be blocked. The three pulses are six tics apart, and the cast
stops early when the boss morph is no longer alive. `VWStaticEDischarge` is the
server-visible flash at the boss, and `VWStaticESparkFX` marks each victim.
Both actors carry no damage of their own.

The fire orb's Drain and Mega Drain implement Hot Shot and Flame Saber;
neither heals. Shredder deals no direct damage and removes only the listed
temporary shield/combat effects. It preserves team protection and permanent
class movement abilities.

`voidwalker_status.acs` is included by the late-loaded `rz_shared` library.
SMRPG Fear has its own `SMRPG_Fear` powerup, lasting 175 tics. The damage event
halves outgoing damage and multiplies incoming damage by 1.5 before armor.
Chill owns a separate property-power speed modifier; Solidify owns one native
freeze-stack layer. Both expire without clearing another effect's layer.
Countdown Meteor uses the distinct `VWMeteor` damage type: its post-armor event
caps health loss at current HP minus one, before death processing. The lethal
`VWMeteorBlast` attack uses a separate damage type. Countdown steps are one
second apart, and the countdown checks the morph generation after each delay.

Run `python3 tools/mcp/voidwalker-orbs-test.py --phase2` for focused dedicated
server / remote-client tests of native controls, damage and status behavior.
The default invocation retains the original orb lifecycle regression.

Run `python3 tools/mcp/voidwalker-orbs-test.py --hud` to check the owning remote
client's full-health, damaged and destroyed-orb inventory snapshots before and
after the native phase transition. The core weapon declares the same
`_ScriptBar` marker as the four elemental weapons, enabling the existing
`DrawBar_VoidWalker_W5` callback through native BARHNDLE dispatch. The probe
checks that marker on the client and saves `phase2-core-hud.png` beside its logs.

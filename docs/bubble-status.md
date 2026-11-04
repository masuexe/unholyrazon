# Bubble status integration

## Purpose

This document describes the reusable Bubble status for Unholy Razon 4.0. The
status targets Zandronum and MM8BDM v6c. It uses DECORATE and ACS only.

No existing weapon or class gains Bubble in this change. A weapon opts in with
one damage type, as described below. No new body art is added. The status adds
two supplied sound assets and an attached bubble effect. The status uses the
engine input freeze and two inventory markers; the cosmetic actor never
controls gameplay.

## Behavior

Bubble is a single active state. It has no stack count and no refresh rule.

- Duration: 88 game tics. The engine runs at 35 Hz. This value is the accepted
  rounding of 2.5 seconds.
- A living player who receives a Bubble hit takes the normal damage. Then the
  player receives Bubble.
- An effective damage event breaks an active Bubble. This rule includes a hit
  that also carries the Bubble damage type. That hit does not reapply Bubble in
  the same event.
- A hit with zero effective damage cannot break or apply Bubble.
- Each damage event is independent. A multi-hit attack can apply, break, and
  apply again in one tic.
- Bosses are susceptible. The eligibility gate does not read paralysis
  immunity or boss-only flags.
- This version has no electric damage multiplier and no electric interaction.
- While Bubble is active, the body holds frame H of its current sprite.
- Bubble owns one forced NoGravity layer. Release and lifecycle cleanup remove
  that layer; other sources and a native NoGravity flag remain intact.
  The core NoGravity entry stops current momentum.
- A new instance plays the entry sound. A surviving damage break or a timeout
  plays the release sound.
- One bubble effect follows the affected body. A surviving damage break or a
  timeout plays its three release frames once.

## Engine hook and ordering

The status reads `GAMEEVENT_ACTOR_DAMAGED` from the `rz_shared` ACS library.
The `rz_shared` library loads after the gameplay libraries. At this point the
event result is the damage that the engine will subtract from health.

The engine dispatches this event after armor absorption. The engine does not
dispatch it in these cases:

- The target is invulnerable or has god mode.
- A damage factor, protection power, or shield reduces the hit to zero.
- Armor absorbs the whole hit.

The event script snapshots the Bubble marker first. Then it reads the effective
damage. This ordering gives the required apply, break, and no-reapply behavior.

### Armor-only damage

Armor-only damage is not effective health damage in this implementation. The
engine returns before the post-armor event when armor absorbs the whole hit.
Therefore an armor-only hit neither breaks an active Bubble nor applies a new
Bubble. Partially absorbed damage is effective damage and uses the normal
rules.

A lethal hit does not apply Bubble. The event compares the final damage with
the current health. Buddha and extra-life rescues are not special-cased.

## Presentation and release sounds

The shared `BubbleHold` state keeps frame H on the body. The state line
`"####" H` keeps the current class sprite or player skin and changes only the
frame. `"####"` is the Zandronum no-change sprite marker. It does not replace
the sprite with a fixed texture.

The engine installs the damage Pain state after the damage event. The shared
`Pain` state runs the normal bookkeeping and protection checks first. Then it
jumps to `BubbleHold` when `UH_Bubble_F` is active. The class pain chain
continues when Bubble ends, so its reactions still run. If a class has no Pain
state because its `PainChance` rejects the hit, `uh_BubbleController` sets
`BubbleHold` after one tic.

`BubbleHold` checks health on every frame. A dead body jumps to the class
`Death` state. A living body returns to `SuperClassPain` when the marker is
gone. The status never forces H onto a corpse.

The two supplied EXE6 files are copied without conversion:

| Alias | Asset |
|-------|-------|
| `MMBN6/BubbleEnter` | `sounds/gamesounds/mmbn/bubble_enter.wav` |
| `MMBN6/BubbleRelease` | `sounds/gamesounds/mmbn/bubble_release.wav` |

`UH_BubbleApply` plays the entry sound once after the marker and freeze layer
are owned. `uh_BubbleClearOwned` plays the release sound once for a surviving
damage break or a timeout. Repeated cleanup cannot replay it.

These paths are silent:

- `ENTER`, `RESPAWN`, and `DEATH` lifecycle cleanup.
- Morph pre-reset, post-reset, and demorph cleanup.
- Interrupted-instance and external-freeze cleanup.
- A lethal break. The death lifecycle owns the end of the life, so it adds no
  release sound.

A map entry or respawn with no Bubble makes no sound.

## Attached bubble effect

`UHBubbleWarper` inherits from `ShieldWarper_UH`. Its overridden Spawn state
skips the base client-only spawn hooks and the unrelated `ShieldCheck` timer.
This variant is server-owned: Zandronum replicates its spawn, `A_Warp`
movement, ACS state changes, and removal to clients. Clients do not need the
server-only owner variables or target pointer to animate the replicated actor.
It has no collision, gravity, or damage behavior.

The supplied `tmp/Sprite-0001.png` is the artwork source. Fourteen 64 by 64
transparent crops preserve the original pixels and colors. All use the same
sprite offset `(32, 56)` and scale 2.5. Both animations compensate for the
sprite pivot and center on half the owning body height, sampled on entry. The first eleven frames (`UBBLA0` through `UBBLK0`) play in row
order at eight tics each, repeating while active. The final three frames
(`UBBLL0` through `UBBLN0`) play at four tics each, then disappear after twelve
tics. The effect follows the same body during both animations.

Each successful Bubble stores one visual TID on its body. An ordinary release
clears this handle before starting Pop, so a later Bubble gets its own effect;
the older Pop cannot clear or attach to the new instance. Lifecycle cleanup
removes the owned visual immediately without Pop. A server watchdog checks
the actual target body, status marker, owner token, and visual handle every
tic, and removes abandoned effects. It has a ninety-tic upper bound for an
unreleased visual. Released effects finish their twelve-tic Pop independently.
None of these checks writes the gameplay status or freeze stack.

## Weapon opt-in

A weapon or projectile opts in by using the damage type `UH_Bubble`. For
example:

`LightBeam` is a second opt-in type, listed in
`UH_BUBBLE_ALIAS_DAMAGETYPE`. Use it when an attack must keep its own damage
type and obituary but still apply Bubble, as Void Walker's Light Bubble does.
Both types go through the same eligibility, break, and no-reapply rules.

```decorate
Actor ExampleBubbleShot : BasicProjectile
{
  Damage 10
  DamageType "UH_Bubble"
}
```

For an ACS-driven hit, use the same type:

```acs
Thing_Damage2(targettid, 10, "UH_Bubble");
```

The damage type is the only opt-in marker. The normal damage value, armor,
damage factors, and protection powers still apply. Do not add a second
compensating hit.

To find a target and use the real damage path in a test, use the debug scripts
in the next section.

## Lock ownership and cleanup

Bubble holds exactly one layer of the base game `PlayerPropertyFrozen` stacker
through `core_freezeplayer`. The third argument is zero, so the camera stays
locked.

Two inventory markers record ownership:

- `UH_Bubble_F` is the single active state.
- `UH_BubbleLock_F` proves that Bubble owns one freeze layer.

`uh_BubbleClearOwned` releases only the recorded layer. Repeated cleanup is
safe. An external freeze layer keeps its own count, and Bubble keeps its layer
when another source removes a different layer.

The `uh_BubbleController` script is the only timer. It holds a unique body
token in `user_uh_bubble_token`. A morph, a respawn, a slot reuse, a break, or
a later Bubble changes the body token. An old controller then exits without
touching the newer state.

Cleanup runs from these paths:

- `ENTER`, `RESPAWN`, and `DEATH` lifecycle scripts in `unholy`.
- Morph pre-reset, post-reset, and demorph through `morph_reset.acs`.
- The Bubble timeout and the damage-event break.

### Camera allow-look

The engine zeroes movement, attack buttons, inventory use, yaw, and pitch while
`PROP_TOTALLYFROZEN` is set. `APlayerPawn::UseInventory` also rejects inventory
use while the player is totally frozen. Bubble uses the same freeze convention
as the existing statuses. A weapon sequence that ignores player input can
finish, as it can under any other `core_freezeplayer` status.

Two mod camera workarounds read input while a player is frozen:

- `uh_TimeBenderCameraLook`
- `Unholy_TS_ClientCameraControl`

Both scripts now check `UH_Bubble_F` and do not apply camera input while Bubble
is active. The base game `core_freezeplayer_allowlook` loop is used only by
debug and campaign code in this package, not by LMS classes. Bubble's extra
freeze layer also makes the TimeBender freeze-count check fail.

## Eligibility and future immunity

`UH_BubbleCanApply` is the single eligibility gate. It requires a live player
in the game. It rejects an active Bubble, death, and the future immunity marker
`UH_BubbleImmune_F`.

No actor grants `UH_BubbleImmune_F` in this version. A future approved
whitelist adds that marker to the approved classes. Do not reuse
`PlayerPropertyNoParalyze` or `GENERICBOSS` checks; either would add unapproved
Bubble immunities.

## Debug and test entry

The `rz_debug` library provides server diagnostics. Bubble probes do not check
`sv_cheats`, so they also work in TRAINING when that cvar is off. Damage probes
still use the normal damage path, including armor and immunity checks.

```text
pukename rz_debug_BubbleHit        <slot> <amount> <bubble>
pukename rz_debug_BubbleBurst      <slot> <hits> <amount> <bubble>
pukename rz_debug_BubbleState      <slot>
pukename rz_debug_BubbleSelfTest   <slot>
pukename rz_debug_BubbleInputProbe <slot>
```

- `slot` < 0 selects the console player.
- `bubble` 1 uses `UH_Bubble`; 0 uses ordinary `Crush` damage.
- `rz_debug_BubbleHit` runs one real `P_DamageMobj` hit.
- `rz_debug_BubbleBurst` runs several hits in one tic.
- `rz_debug_BubbleState` prints the marker, lock, freeze count, look count, body
  token, visual TID, health, armor, and immunity fields.
- `rz_debug_BubbleSelfTest` runs the apply, 88-tic timeout, ordinary break,
  same-tic burst, immune, overlapping-freeze, and death checks on one
  invulnerable test body.
- `rz_debug_BubbleInputProbe` prints the modified movement, yaw, pitch, attack,
  and use input. Hold `+forward`, `+attack`, `+left`, and `+lookup` before a
  step to check that `PROP_TOTALLYFROZEN` zeroes the modified command.

### Console output

Every diagnostic prints one line that starts with `[BubbleProbe]`. The line
uses `PrintBold`, so it reaches the local console and every client console on a
server. It does not use `UH_Log`, so `uh_cl_LogLevel` and `uh_sv_loglevel`
cannot hide it. The same line also goes to the engine logfile, so a headless
run can read it.

The first field is the probe version, for example `ver=2`. A different version
means the running package is stale.

The line reports these fields:

- `slot`, `body` (`live`, `dead`, or `none`), and the actual actor `tid`.
- `amount`, `type`, and the number of actors that accepted the hit (`hits`).
- `hp` and `armor` before and after the hit.
- `active`, `lock`, and `frozen` before and after the hit.
- `invuln`, `powerinv`, `protect`, `bubimm`, and `dmgfac`.
- `result`, one of `APPLIED`, `BROKE`, `ARMOR-ONLY`,
  `NO EFFECTIVE DAMAGE`, `DAMAGE LANDED BUT NO BUBBLE`, `LETHAL`, or a
  rejection reason.

### Quick test

Select a living player and run `pukename rz_debug_BubbleHit 0 1 1` to apply
Bubble to slot 0 through a real damage event. Run it again before the timeout
to break Bubble. No `sv_cheats` change or map reload is required to enable
these probes. Reload the game after installing an updated PK3.

### Troubleshooting

| Output | Meaning |
|--------|---------|
| `rejected: sv_cheats is OFF` | An older package is loaded. Restart with the updated PK3; current Bubble probes have no such gate. |
| `rejected: invalid slot` | The slot is outside `0..63`. |
| `rejected: slot N is not in the game` | No player occupies that slot. |
| `rejected: slot N is spectating` | The slot is a spectator or a dead spectator. Use a live slot. |
| `rejected: slot N has no player body` | The slot has no current body. Use a live slot. |
| `rejected: slot N body is dead` | The body is dead. Respawn first. |
| `NO EFFECTIVE DAMAGE` | The hit was fully blocked. Read `invuln`, `powerinv`, `protect`, and `dmgfac`. |
| `ARMOR-ONLY` | Armor absorbed the whole hit. This is not effective health damage. |
| `DAMAGE LANDED BUT NO BUBBLE` | Health changed but the marker did not. The damage event did not run or refused the hit. Check `bubimm`, the actor `+USEDAMAGEEVENTSCRIPT` flag, and that `rz_shared` is loaded. |
| `DAMAGE LANDED BUT STILL BUBBLED` | An active Bubble did not break on effective damage. The damage event did not run. |
| `BROKE` | Effective damage removed an active Bubble. |
| `APPLIED` | Effective Bubble damage applied the status. |

The probes hit the selected body directly. They do not use the `slot + 1000`
convention TID, so they cannot damage another actor that shares that TID. The
reported `tid` is the body's real TID for comparison.

`rz_debug_BubbleSelfTest` prints one `self-test` line per step. Run it on a
living, non-spectator body. It kills the test body at the end, so respawn or
relaunch before running it again.

## Source map

| File | Purpose |
|------|---------|
| `src/acs_source/systems/player_hooks/bubble_status.acs` | Status, event, controller, cleanup, and sounds |
| `src/acs_source/systems/player_hooks/rz_shared.acs` | Late-loading library include |
| `src/actors/player/uh-flags.dec` | Marker and immunity inventory actors |
| `src/actors/player/classbase/root/ClassBase_UH00.dec` | Body token, pending flag, and `BubbleHold` state |
| `src/actors/player/uh-bubble-visual.dec` | Attached ShieldWarper loop and release animation |
| `src/sprites/effects/bubble/UBBL*.png` | Eleven intact frames and three release frames |
| `src/acs_source/unholy/uh_lifecycle.acs` | Enter, respawn, and death cleanup |
| `src/acs_source/systems/tools/morph_reset.acs` | Morph and demorph cleanup |
| `src/acs_source/debug/rz_debug.acs` | Server diagnostics |
| `src/SNDINFO` | Entry and release sound aliases |
| `src/sounds/gamesounds/mmbn/bubble_enter.wav` | Supplied EXE6 entry sound |
| `src/sounds/gamesounds/mmbn/bubble_release.wav` | Supplied EXE6 release sound |

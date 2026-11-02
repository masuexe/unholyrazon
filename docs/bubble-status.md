# Bubble status integration

## Purpose

This document describes the reusable Bubble status for Unholy Razon 4.0. The
status targets Zandronum and MM8BDM v6c. It uses DECORATE and ACS only.

No existing weapon or class gains Bubble in this change. A weapon opts in with
one damage type, as described below. No new art is added. The status uses only
the engine input freeze and the two inventory markers; no cosmetic actor
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

## Weapon opt-in

A weapon or projectile opts in by using the damage type `UH_Bubble`. For
example:

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
  token, health, armor, and immunity fields.
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
cannot hide it. A dedicated server has no local status bar, so the same line
also goes to the server log there.

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
| `src/acs_source/systems/player_hooks/bubble_status.acs` | Status, event, controller, and cleanup |
| `src/acs_source/systems/player_hooks/rz_shared.acs` | Late-loading library include |
| `src/actors/player/uh-flags.dec` | Marker and immunity inventory actors |
| `src/actors/player/classbase/root/ClassBase_UH00.dec` | Body token user variable |
| `src/acs_source/unholy/uh_lifecycle.acs` | Enter, respawn, and death cleanup |
| `src/acs_source/systems/tools/morph_reset.acs` | Morph and demorph cleanup |
| `src/acs_source/debug/rz_debug.acs` | Server diagnostics |

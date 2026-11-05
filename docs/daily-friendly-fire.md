# Daily friendly fire

The server selects separate daily weapon pools for standard Qwant, Nega Man,
and Decoy Bot. Other registered vanilla standard Survivors and explicitly opted-in addon Survivors share a class pool.
Mega Man keeps its existing daily copy-weapon selection. Shiny forms, Bosses,
Demoneyes, and addon Survivor classes without explicit opt-in do not enter the new class pool.

| Setting | Default | Meaning |
|---|---:|---|
| `teamdamage` | Engine default `0` | Damage multiplier for eligible friendly hits: `0` disables damage, `0.5` halves it, `1` keeps normal damage. |
| `rz_sv_randcopywepteamkill` | `true` | Enable the new Qwant/Nega Man/Decoy Bot weapon pools. |
| `rz_sv_copy_ff_count_min` | `6` | Minimum daily selection per weapon pool. |
| `rz_sv_copy_ff_count_max` | `10` | Maximum daily selection per weapon pool. |
| `rz_sv_randclassteamkill` | `true` | Enable the remaining standard Survivor class pool. |
| `rz_sv_class_ff_count` | `3` | Number of daily friendly-fire classes. |

Counts are clamped to the available candidates. A zero class count disables
class selection; setting both weapon counts to zero disables weapon selection.
Changing the new settings does not change Mega Man's existing settings.

The server's local calendar date seeds each pool independently. The same date,
configuration, and registrations produce the same selection after a map change
or reconnect. Changing the date or pool settings refreshes the selection on the
next policy query. This follows the existing Mega Man daily schedule; it does
not wait for the current round to end.

Run the named server script `uh_debug_ShowDailyTeamFF` to log the date,
`teamdamage`, and the selected entries. Pool 0 contains classes; pools 1, 2,
and 3 contain Qwant, Nega Man, and Decoy Bot weapons respectively. The output
uses the normal INFO log level.

## Damage and ownership

The new pools affect ordinary Unholy LMS logical teammates. The existing
server teammate policy handles one-versus-all rounds and FFA exceptions.
They do not enable friendly damage in native team modes. Personal defenses,
armor, hostile damage, self-damage, and environmental damage keep their
existing rules. Removing team protection during settlement still uses the
existing post-round policy.

The original Survivor zero-factor table remains authoritative in
`PowerProtectSurvivorBaseline`. The public `PowerProtectSurvivor` inventory
identity remains available to existing role checks. Its zero-factor decisions
are applied by the daily damage event before armor, with explicit exceptions
for selected origins. Player classes must retain the base game's damage-event
flag. Boss and Demoneye protection tables are unchanged.

Projectiles store their originating standard class and copy weapon. Qwant/Nega
attack ownership also covers helpers declared in the weapon's source file;
Decoy attacks use their numbered copy family. Instant rail/bullet puff classes
are extracted from the weapon calls so an ownerless hitscan puff still resolves
its firing player. This prevents switching weapons
from reclassifying a shot or its known fragments. Stamped summon ownership can
resolve a non-player damage source to its creator. Unregistered or ambiguous
copy attacks keep baseline protection instead of borrowing the currently held
weapon. Addon copy weapons therefore need explicit ownership coverage before
their protected attacks can participate.

Friendly suplex acquisition, Nega Super Arm throws, and KickChamp slide kicks
remain harmless. Oil Slider retains its existing friendly boarding exception.
Poison, siphon, homing fling, and Marksman lock-on acquisition consult the daily
policy before applying their effects to protected teammates.

## Maintenance and verification

After editing the baseline protection table or adding Qwant/Nega attacks, run:

```bash
python3 tools/gen_daily_ff_data.py
python3 tools/gen_daily_ff_data.py --check
python3 tools/test_daily_team_ff.py
python3 tools/test_teamdamage.py
```

The generator derives its data from the original protection table and the
registered weapon definitions. It rejects ambiguous ownership. The tests run
the actual ACS policy under C engine stubs and cover pool sizes, clamping,
rollover, cancellation, source attribution, native-mode fallback, and harmless
interactions. They do not replace an in-game dedicated-server combat test.
Both policy tests are part of the fast/smoke gate. Mutation cases verify that
the checks reject ignored selections, stale immunity data, and ignored scaling.

## Addon class opt-in

An addon may enroll an ordinary Survivor after its server-side `DefineSurvivor`
registration. Call these synchronous named scripts from the server; they are
not network entry points:

```c
ACS_NamedExecuteWithResult("uh_RegisterDailyFFClass", "MySurvivor");
ACS_NamedExecuteWithResult("uh_RegisterDailyFFDamageType", "MyDamage");
```

Only exact custom Survivor actors qualify. Shiny bodies without their own
ordinary Survivor registration do not qualify. Enrollment is case insensitive
and idempotent, limited to 127 addon classes and 128 damage types per map.
The class joins pool 0 and shares `rz_sv_class_ff_count`; there is no separate
addon quota. Loading an addon can therefore change that day's selections.
Register in a consistent order on every map. Queries and rolls remain server
owned; do not send returned slot numbers or tokens to clients.

`uh_DailyFFAddonOrigin` returns the current player activator's registered addon
origin, including creator slot, or zero for an excluded/unregistered body.
`uh_DailyFFAddonAllowed(token)` returns whether that origin is currently selected
in ordinary LMS with the class pool enabled. It does not apply `teamdamage`.
The shared main-mod damage handler applies the multiplier once, including
recorded non-player creators, regardless of event-handler order.

Addon projectiles and child spawners must freeze the origin when created,
propagate it into fragments, and publish it in `UH_DailyFFOrigin` before a hit.
An excluded origin must stay excluded after morphing back to an ordinary body;
use the reserved token `1` rather than borrowing the owner's current class.
A zero origin means unknown, not permission to hurt allies. The addon must
remove any separate zero-factor protection for selected hits and retain its
own fallback protection, native-mode behavior and summon-victim rules.
Damage-type registration only changes explicit logical-teammate hits; it does
not introduce vanilla blanket immunity for addon hostile or self-damage.

Rebellion Patch alpha.261105 demonstrates this interface for ordinary Mirrorman
and Richter Belmont. Truepower bodies stay excluded. Its own fixed handler
protects allied clones even when their creator is selected. Compile and load
both updated packages together when using daily addon friendly fire.

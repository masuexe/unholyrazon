# Server Gameplay CVARs & Rule Settings

This document provides a comprehensive reference for dedicated server hosts configuring gameplay rules, mechanic thresholds, and character behavior CVARs in **Unholy Razon**.

All settings documented here are server-owned, preserved in the host's configuration file, and accessible both via the in-game menu and the server console.

---

## 1. Round Threshold Limits

Hosts can adjust the pacing, pity systems, and boss spawn triggers for LMS rounds:

- **Menu Path**: **Unholy Server Options → Game Rules → Round Thresholds**
- **Console Syntax**: `<cvar> <value>` (e.g. `uh_sv_winstreaklimit 5`)
- **Range**: Clamped to integers `1..100`.

| Setting / CVAR | Default | Description & Gameplay Effect |
|---|:---:|---|
| **Win Streak Limit**<br>`uh_sv_winstreaklimit` | `6` | Every *N* consecutive survivor round victories queues a random Strongman boss challenge. |
| **Lose Streak Limit**<br>`uh_sv_losestreaklimit` | `6` | Every *N* consecutive survivor round losses grants pity **Mercy Runes** to survivors. |
| **Hell Mark Limit**<br>`uh_sv_hellmarklimit` | `10` | Winning a round as the sole survivor awards Hell Marks; reaching *N* queues **FinalSampi**. |
| **Speciman Frag Limit**<br>`uh_sv_specimanfraglimit` | `15` | Total Speciman deaths across matches queue **FinalSpeciman**. |
| **Gauntlet Treasure Limit**<br>`uh_sv_treasurecountlimit` | `10` | Collecting *N* treasures spawns a **True Power** item and consumes *N* treasures (retaining any surplus). |
| **LMS Count Limit**<br>`uh_sv_lmscountlimit` | `5` | Becoming the last survivor *N* times triggers **Bad LMS** penalties. |
| **Bonus Event Round Limit**<br>`uh_sv_bonuseventlimit` | `8` | Number of normal boss rounds played before the next Bonus Event round occurs. |

*Note: Changes take effect at the next threshold evaluation. Counters are preserved across rounds.*

---

## 2. Opening Copy-Weapon Counts (Qwant & NegaMan)

Controls the quantity of copy weapons distributed to Qwant and NegaMan at the start of a round:

- **Menu Path**: **Unholy Server Options → Rules → Copy Weapons**
- **Console Syntax**: `<cvar> <value>`

| Setting | CVAR | Default | Effective Range |
|---|---|:---:|---|
| **Qwant Starting Moves** | `rz_sv_qwant_start_weapon_count` | `4` | 1 up to total registered move pool |
| **NegaMan Starting Copy Weapons** | `rz_sv_nega_start_weapon_count` | `3` | 1 up to total registered copy-weapon pool |

### Distribution & Slot Rules

- **Sampling**: Weapons are sampled uniformly without duplicates. The base weapon is always retained and does not count toward the limit.
- **Pool Saturation**: If the setting equals or exceeds the total registered pool size, the player receives all available weapons in the pool.
- **Timing**: Changes apply to new spawns at the next round opening, not to currently living players.
- **Qwant Move Relearning**: Qwant players can spend **28 MoveRelearnAmmo** to swap their currently active move for an unowned move without changing their total held count.
- **Qwant Functional Slots**: Qwant's 7 weapon slots map directly to UIX weapon wheel groups:
  - **Slot 1 (Base)**: `Qwant_W`
  - **Slot 2 (Ranged)**: `AttackOrder`, `FlameBurst`, `HiddenPower`, `IceShard`, `SonicBoom`, `ThunderWave`, `Toxic`, `WaterShuriken`
  - **Slot 3 (Rapid Fire)**: `BulletSeed`, `ChargeBeam`, `DragonBreath`, `FreezeDry`, `IceBeam`
  - **Slot 4 (Melee)**: `AnchorShot`, `BlazeKick`, `FeintAttack`, `FlameWheel`, `Gust`, `LeafBlade`, `NeedleArm`, `NightSlash`, `RapidSpin`, `ShadowForce`, `ShadowPunch`
  - **Slot 5 (Power)**: `FireBlast`, `MoonBlast`, `Thunder`, `WaterSpout`
  - **Slot 6 (Area / Control)**: `DazzlingGleam`, `NightDaze`, `RockSlide`, `Spikes`
  - **Slot 7 (Defense / Support)**: `CalmMind`, `MatBlock`, `Moonlight`

---

## 3. SinfulBusterExpert Weapon Unlock Policy

Controls weapon progression for the SinfulBusterExpert boss:

- **Menu Path**: **Unholy Menu → Server Options → Boss Setup → SinfulBusterExpert → Weapon Unlocks**
- **CVAR**: `uh_sv_sbe_unlockmode` (integer)

```text
uh_sv_sbe_unlockmode 0   // Unbound policy (default)
uh_sv_sbe_unlockmode 1   // Progressive policy
```

| Value | Policy | Starting Arsenal | Health Threshold Unlocks |
|:---:|---|---|---|
| **`0`** | **Unbound** *(Default)* | Slots W1–W7 | Unlocks **W8** when boss HP drops to **<= 40%** of spawn health. |
| **`1`** | **Progressive** | Slot W1 only | Unlocks **W2–W8** sequentially across 7 evenly spaced thresholds during the first 60% of HP lost. |

- **Evaluation**: Evaluated on each boss morph. Mid-fight changes take effect on the subsequent morph.
- **HP Scaling**: Thresholds calculate from scaled spawn HP. (e.g. at 6500 HP, Progressive step is `6500 * 0.6 / 7 = 557 HP`, unlocking W2 at 5943 HP and W8 at 2601 HP). Once granted, weapons are never revoked by healing.

---

## 4. Bonus Stage Death Effects

Controls random player death effects during LMS Bonus Stages:

- **Menu Path**: **Unholy Server Options → Events → Bonus Stage Death Shitting**
- **CVAR**: `uh_sv_bonusdeathshitting` (boolean, default `true` / `1`)

```text
uh_sv_bonusdeathshitting 1   // Enabled (default)
uh_sv_bonusdeathshitting 0   // Disabled
```

- **Behavior**: When active during an LMS Bonus Stage, every player death (survivor, boss, or demoneye) rolls one random effect from a pool of **39 adapted Razon 3 outcomes** directly in the `DEATH` hook without waiting for death animations to conclude.
- **Revivals**: Revived players can trigger another roll on subsequent deaths. Ordinary boss rounds do not roll.
- **Dynamic Toggle**: Evaluated on every death; toggling takes effect immediately for future deaths.

---

## 5. Zangief Charge Pull Toggle

Controls Zangief's `AltFire2` Atomic Buster suction ability:

- **Menu Path**: **Unholy Server Options → Game Rules → Zangief Charge Pull**
- **CVAR**: `uh_sv_zangiefpull` (boolean, default `true`)

```text
uh_sv_zangiefpull true    // Enabled (default)
uh_sv_zangiefpull false   // Disabled
```

- When enabled, charging Atomic Buster with alternate fire pulls players within **250 map units** (force 25 normal / 50 shiny, with distance falloff and 40-unit dead zone).
- Complete mechanical details, team immunity, and parameters are documented in [Class Mechanics: Zangief Charge Pull](class-mechanics.md#1-zangief-charge-pull-altfire2).

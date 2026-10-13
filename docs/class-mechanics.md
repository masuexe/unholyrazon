# Class Specific Mechanics & Controls

This document details character-specific combat mechanics, control schemes, and unique gameplay systems for specialized classes in **Unholy Razon**.

---

## 1. Zangief: Charge Pull (`AltFire2`)

Zangief and Shiny Zangief feature an active suction mechanic restored from Razon 3 (3.11.1).

### Mechanics & Parameters

- **Activation**: Hold **Alternate Fire** (`+altattack`) while charging the Atomic Buster.
- **Pull Radius**: Live players within **250 map units** horizontally are pulled toward the charger.
- **Pull Force**:
  - **Normal Zangief**: Maximum pull force **25**.
  - **Shiny Zangief**: Maximum pull force **50**.
  - Force scales inversely with distance (linear falloff, rounded upward).
- **Dead Zone**: Targets within **40 map units** or less are not pulled, preventing erratic jitter or physics collisions at point-blank range.
- **Exemptions**:
  - Players carrying `PowerProtectBoss` (legacy `Swap=2` filter) are exempt.
  - Native teammates are immune in team gamemodes.
  - Does **not** require line of sight (pulls through obstacles and around corners).
- **Input Independence**: Pull is tied logically to the `AltFire2` weapon state, regardless of the player's physical mouse button mapping.
- **Server Execution**: The pull executes on the server every charge tic and terminates immediately when charging ends or the player morphs.

### Server Configuration

Hosts can toggle this ability using the archived boolean CVAR `uh_sv_zangiefpull` (enabled by default):
- **Menu**: **Unholy Server Options → Game Rules → Zangief Charge Pull**
- **Console / Config**:
  ```text
  uh_sv_zangiefpull false   // Disable charge pull
  uh_sv_zangiefpull true    // Enable charge pull (default)
  ```
- Changes take effect on the next charge pulse, including an ongoing charge. Disabling the CVAR leaves all other charging, spinning, grabbing, damage, and ammo mechanics intact.

*Historical reference: `actors/Wep/Zangief_W.txt`, `actors/Wep/Shiny/S_Zangief_W.txt`, and `acs_source/U_B_ACS.acs` in `uh-ub_razonpatch_3.11.1`.*

---

## 2. Star Force Mega Man: Controls & Battle Cards

Star Force Mega Man (`WarRockStelar`) uses a unified single-slot combat weapon with dedicated Battle Card queuing and lock-on controls:

### Control Bindings

| Action / Existing Input | Function | Behavior |
|---|---|---|
| **Primary Fire** (`+attack`) | Buster | Standard buster shot; release idle to charge. |
| **Secondary Fire** (`+altattack`) | Shield | Hold to raise defensive shield. |
| **Reload** (`+reload`) | Use Battle Card | Activates the next queued card in order. Hold to continuously use queued cards across animation cooldowns. |
| **Previous Weapon** (Mouse Wheel Up) | Draw Hand | Replaces the current hand with **6 new cards** when the custom card gauge is 100% full. Consumes the gauge. |
| **Next Weapon** (Mouse Wheel Down) | Toggle Lock-on | Toggles card homing lock-on on/off. |

### Queuing & Input Traversal

- **Card Chain Execution**: Pressing **Reload** starts the current card immediately when ready. Holding **Reload** automatically triggers consecutive cards as each card's animation and cooldown conclude. Releasing **Reload** stops the chain cleanly without interrupting the currently active card. An empty hand halts the chain.
- **Wheel Switching & Cooldown**: Both scroll actions automatically switch back to the combat weapon as soon as firing/shield states permit. A successful wheel input initiates an **8-tic shared cooldown** to prevent accidental double-inputs.
- **Slot Traversal Quirk**: All three underlying weapon actors (`WarRockStelar_W`, `WarRockStelar_Control_W`, and card helpers) inherit slot 1 with explicit priorities (`draw=100`, `combat=101`, `lock=102`). They must **not** be assigned separate `Player.WeaponSlot` numbers, as Zandronum's `slotschecked < NUM_WEAPON_SLOTS` traversal guard would prevent proper wraparound.

### Regression Testing

To verify Star Force input handling and weapon switching:
```bash
node tools/mcp/starforce-input-test.mjs
```

---

## 3. Eden: Isaac Item Artifacts

Ported from Razon 3 (`RAZONLIB.acs` and `actors/Wep/Eden/`), Eden can draw five active and passive artifact items:

### Item Roster

| ID | Item | Pool / Cost | Effect |
|:---:|---|---|---|
| **313** | **Holy Mantle** | Shiny Angel Item (Quality 4) | Completely absorbs the next instance of damage. Recharges after **120 tics**. Does not negate Damocles, Telefrag, or self-inflicted suicide damage. |
| **330** | **Soy Milk** | Standard Item (Quality 2) | Tears HUD fire rate multiplied by **5** (capped at 300), damage divided by **5**. Applied after Ipecac and before Godhead. |
| **33** | **The Bible** | Active (300 Charge) | Grants flight for **180 tics**. Assist display renders the Bible icon, a countdown progress bar, and ceiling-rounded remaining seconds. |
| **145** | **Guppy’s Head** | Active (150 Charge) | Spawns **2 Blue Flies**. Fly melee damage equals **2x** Eden's current tear damage. |
| **578** | **Free Lemonade** | Active (300 Charge) | Sprays creep for **48 tics**. Droplet damage is 131; residual pool deals 130 damage for up to **500 tics**. |

### Synergies & Engine Safeguards

- **Car Battery Synergy**: Doubles active item activations for a single charge cost:
  - *The Bible*: Refreshes the flight timer without stacking flight layers.
  - *Guppy’s Head* & *Free Lemonade*: Spawns double flies and double lemon spray pools.
- **Endless Ammo Rune**: Halves active item charge costs.
- **Holy Mantle Damage Event**: Cancels damage directly in the engine damage `EVENT` hook without relying on legacy `RogueDXShieldWasHit` or shared Buddha states. All other Eden on-hit items check Holy Mantle status first to avoid script race conditions.
- **Targeting & Teammates**: Blue flies check native team and `uh_AreGameplayTeammates`. Flies despawn immediately if Eden dies, disconnects, or drops Guppy's Head.

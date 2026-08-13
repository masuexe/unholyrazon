# Sprite notes

## `sprites/bluecyan_projectiles/`

Vanilla sprites recolored to cyan/blue `192/198` and light blue/dark blue `202/199`.

Some sprites have extra colors. If a sprite directory includes a `README`, that file lists the extra colors.

### Naming

All sprites follow this pattern:

| Part | Meaning |
|------|---------|
| Prefix | `X` = `192/198`, `Y` = `202/199` |
| Separator | `_` |
| Game code | e.g. `2` / `3` for Mega Man 2 / 3 |
| Weapon letter | Alphabetical letter by Robot Master order |

Examples:

| Palette | Weapon | Sprite |
|---------|--------|--------|
| `192/198` | Rolling Cutter | `X_1A**` |
| `202/199` | Leaf Shield | `Y_2H**` |
| `192/198` | Water Shield | `X_AB**` |
| `202/199` | Photon Missile | `Y_VD**` |

Check the sprites for specific frame letters.

### Weapon letter map

#### Mega Man 0

| Letter | Weapon |
|--------|--------|
| A | Proto Buster |
| B | Mega Buster |
| C | Roll Swing |
| D | Bass Buster |
| E | Duo Fist |

#### Mega Man 1

| Letter | Weapon |
|--------|--------|
| A | Rolling Cutter |
| B | Super Arm |
| C | Ice Slasher |
| D | Hyper Bomb |
| E | Fire Storm |
| F | Thunder Beam |
| G | Time Slow |
| H | Oil Slider |

#### Mega Man 2

| Letter | Weapon |
|--------|--------|
| A | Metal Blade |
| B | Air Shooter |
| C | Bubble Lead |
| D | Quick Boomerang |
| E | Crash Bomb |
| F | Time Stopper |
| G | Atomic Fire |
| H | Leaf Shield |

#### Mega Man 3

| Letter | Weapon |
|--------|--------|
| A | Needle Cannon |
| B | Magnet Missile |
| C | Gemini Laser |
| D | Hard Knuckle |
| E | Top Spin |
| F | Search Snake |
| G | Spark Shock |
| H | Shadow Blade |
| L | Explosion |

#### Mega Man 4

| Letter | Weapon |
|--------|--------|
| A | Flash Stopper |
| B | Rain Flush |
| C | Drill Bomb |
| D | Pharaoh Shot |
| E | Ring Boomerang |
| F | Dust Crusher |
| G | Dive Missile |
| H | Skull Barrier |
| L | Explosion |

#### Mega Man 5

| Letter | Weapon |
|--------|--------|
| A | Gravity Hold |
| B | Water Wave |
| C | Power Stone |
| D | Gyro Attack |
| E | Star Crash |
| F | Charge Kick |
| G | Napalm Bomb |
| H | Crystal Eye |

#### Mega Man 6

| Letter | Weapon | Notes |
|--------|--------|-------|
| A | Blizzard Attack | |
| B | Centaur Flash | |
| C | Flame Blast | |
| D | Knight Crush | |
| E | Plant Barrier | Uses frames into `F` (many frames) |
| F | Silver Tomahawk | |
| G | Wind Storm | |
| H | Yamato Spear | |

#### Mega Man 7

| Letter | Weapon |
|--------|--------|
| A | Freeze Cracker |
| B | Junk Shield |
| C | Danger Wrap |
| D | Thunder Bolt |
| E | Wild Coil |
| F | Slash Claw |
| G | Noise Crush |
| H | Scorch Wheel |

#### Mega Man 8

| Letter | Weapon |
|--------|--------|
| A | Tornado Hold |
| B | Astro Crush |
| C | Flame Sword |
| D | Thunder Claw |
| E | Homing Sniper |
| F | Ice Wave |
| G | Flash Bomb |
| H | Water Balloon |
| I | Mega Ball |

#### Mega Man 9

| Letter | Weapon |
|--------|--------|
| A | Concrete Shot |
| B | Tornado Blow |
| C | Laser Trident |
| D | Plug Ball |
| E | Jewel Shield |
| F | Hornet Chaser |
| G | Magma Bazooka |
| H | Black Hole Bomb |

#### Mega Man 10 (`A`)

| Letter | Weapon |
|--------|--------|
| A | Triple Blade |
| B | Water Shield |
| C | Commando Bomb |
| D | Chill Spike |
| E | Thunder Wool |
| F | Rebound Striker |
| G | Wheel Cutter |
| H | Solar Blaze |

#### Mega Man & Bass (`B`)

| Letter | Weapon |
|--------|--------|
| A | Tengu Blade |
| B | Copy Vision |
| C | Lightning Bolt |
| D | Ice Wall |
| E | Spread Drill |
| F | Remote Mine |
| G | Wave Burner |
| H | Magic Card |

#### Mega Man Killers (`K`)

| Letter | Weapon |
|--------|--------|
| A | Mirror Buster |
| B | Screw Crusher |
| C | Ballade Cracker |
| D | Sakugarne |

#### Mega Man V (`V`)

| Letter | Weapon |
|--------|--------|
| A | Spark Chaser |
| B | Grab Buster |
| C | Bubble Bomb |
| D | Photon Missile |
| E | Electric Shock |
| F | Black Hole |
| G | Deep Digger |
| H | Break Dash |
| I | Salt Water |

## `MMFX` sprites

Common circle sprites used by several enemies/projectiles.

Format: `*MFX`

| Palette | Letter |
|---------|--------|
| `192/198` | `T` |
| `202/199` | `U` |
| `204/195` | `V` |
| `250/249` | `W` |

Check the sprites for the exact frames needed.

## TODO
Update the following sprites to v6b sprites:
- Shield sprites
- Duo Fist
- Bass Buster
- Homing Sniper
- Flash Bomb
- Mega Ball
- Lightning Bolt
- Remote Mine

# Changelog

**English** | [简体中文](CHANGELOG.zh-CN.md)

---

## 4.0.0-beta.261016

- Void Walker now announces elemental specials with a skill banner.
- Fixed Berserker's falling slam crediting Dixieandoff in the Obituary.
- Fixed becoming a Demoneye removing the "Prepare yourselves!" banner. The identity line now appears below it.
- Win/loss results now wait long enough for themes with a registered duration before advancing, while retaining the stop after one pass that prevents short themes from looping.
- Fixed Brick Eyes showing the round timer and its own countdown together. Only the brick countdown remains.

## 4.0.0-beta.261015

- Fixed short result themes (including NSF and MIDI tracks) looping during the post-round wait.
- Fixed Top Fiend's tops lingering and piling up after getting stuck.
- Sutoka now automatically opens all 4 Pandora Boxes at full Rage, granting random items without manual box use.
- Added UIX weapon wheel and weapon bar support for regular DecoyBot.
- Added the "A Random Maverick" death tip group featuring community quotes and unhinged takes, alongside new quotes added to the miscellaneous pool.

## 4.0.0-beta.261014

- Added 50 addon extension slots for coop enemies to share damage resistances and reactions.
- Added 50 addon extension slots for destructible walls, mines and other supported shootable objects, allowing addons to share damage resistances and reactions.
- Fixed Battle Time disappearing before the victory/defeat and streak messages during round settlement.
- Awful Box Demoneye now displays the correct item icon in the UIX Item Wheel.
- Fixed SuperMegaman's rage kills missing the frozen death effect.
- Fixed DecoyBot occasionally starting empty-handed until the player switched weapons with the mouse wheel.
- Fixed recruited Ave Mujica members surviving Sakiko Togawa's death; her death now kills all living recruited members and cancels the finisher if it is preparing.
- Added Isaac-style dynamic stat change indicators for Eden: when attributes increase or decrease (such as from starting items upon spawning, picking up passives, Void stat absorption, or D8 rerolls), a green `+` or red `-` delta hint appears next to the modified stat for 2 seconds.
- Adjusted Eden's vertical stat HUD placement to the right of the health and energy bars.
- Fixed SadFaceToadMan remaining unable to move in phase two when the phase transition interrupted a normal rain attack.
- Fixed `ub_LMS_EventTime` entering an infinite reward retry loop when the last survivor died, disconnected, or lost their pawn, triggering `Runaway script` / `Bad script definition` errors and disconnecting players.
- Fixed MM2 Telly enemies visually glitching with incorrect animation frames while rotating.

## 4.0.0-beta.261013

- Fixed multiplayer jump gauges staying full for Redead Guts, GutsBuddy, and Russian Guts. Ammo spent in Flash states or immediately after server-controlled weapon branches now synchronizes the actual remaining amount; applied the same fix to other affected bosses, normal/shiny survivors, and copy weapons while preserving costs, charge timing, and infinite-ammo rules.
- Added configurable NegaMan daily copy-weapon ammo multiplier bounds `rz_sv_nega_ammo_mul_min` / `rz_sv_nega_ammo_mul_max` under **Unholy Server Options → Rules → NegaMan Weapons**; defaults remain 0–2, with decimal, fixed-multiplier and zero-cost support. Settings take effect immediately, including registered addon weapons; the existing randomization toggle restores original ammo costs when disabled. See [NegaMan Daily Ammo Cost](docs/server-gameplay-cvars.md#negaman-daily-ammo-cost).
- Fixed severe screen flashing when spectating Plasma Spark in first person.
- Fixed an issue where Eden's Ipecac tear projectile explosion effect would not display in multiplayer.
- Added a server toggle `uh_sv_postroundfriendlyfire` (enabled by default) under **Unholy Server Options → Game Rules → Friendly Fire After Round End**; uniformly covers survivors, bosses, and demoneyes across settlement delays, round completions, and native LMS victory sequences, including Bonus Event friendly-fire protection overrides.
- Enabling post-round friendly fire no longer grants post-round team invulnerability, preserving character innate defenses; cancelling settlement to resume battle or turning off the CVAR restores previously stripped protections, discarding stale player snapshots upon death, revival, morph, or disconnect to prevent erroneous restoration.
- Fixed an issue where players grabbed by Zangief could not use items after morphing (e.g. into a Demoneye); grab-inflicted item restrictions are now stripped on morph while preserving restrictions from other sources.
- Restored Razon 3 Zangief Atomic Buster AltFire2 charge pull ability: max pull force 25 (normal) / 50 (shiny), 250 unit radius with distance falloff; added server boolean toggle `uh_sv_zangiefpull` (default true) under **Unholy Server Options → Game Rules → Zangief Charge Pull**, taking effect immediately on the next charge pulse. See [Class Mechanics: Zangief Charge Pull](docs/class-mechanics.md#1-zangief-charge-pull-altfire2).

## 4.0.0-beta.261012

- Restored Razon 3 automap player positions, heading indicators, and 5-second death markers using client markers and existing team snapshots; displays self and teammates while alive in normal rounds, self-only during special events, and all living players while dead/spectating; supports singleplayer and remote standalone clients (note: listen server hosts do not display locally).
- Added server unlock policy setting `uh_sv_sbe_unlockmode` for SinfulBusterExpert: default `0` uses Unbound rules (starts with W1–W7, unlocks W8 at <= 40% health); `1` retains progressive health loss unlocks. Configurable in **Unholy Server Options → Boss Setup → Weapon Unlocks**, evaluated during each morph. See [Server Gameplay CVARs: SinfulBusterExpert Unlocks](docs/server-gameplay-cvars.md#3-sinfulbusterexpert-weapon-unlock-policy).
- Added cancellable round settlements for standard Survivor vs Boss/Demoneye rounds: when opposing sides become alive again during the settlement delay, the current outcome is cancelled, battle resumes, combat BGM and remaining timer are restored, and a cancellation alert is displayed; native LMS victory sequences, special events, and forced ends follow their standard flow.
- Win/loss outcomes and streak counters now display immediately when settlement begins; cancelling settlement rolls back streaks and clears victory banners; streak rewards and other round rewards are granted only upon final confirmation.
- Added server toggle `uh_sv_resumeonrevive` (default true) under **Unholy Server Options → Game Rules → Resume Battle If Enemies Return**; disabling it restores legacy termination behavior, taking effect on the next outcome evaluation. See [Round Settlement](docs/round-settlement.md).
- Fixed 9 active items erroneously classified as passives and missing from the UIX item wheel:
  - Super Mystic Tank, Unholy Insurance, Dickhead categorized as Recovery.
  - On Fire, Ztar, Demoneye.exe Wishing Star, Ass Counter Device categorized as Offensive.
  - Periwinkle Tank categorized as Buff, Invincible Candy categorized as Defensive; both displayed in the wheel Misc category.
- Fixed an issue where Lim (including Shiny) could not move after morphing into a Demoneye while casting M2 standing.
- Improved warning banner text color for 1-minute round warning and forced end alerts (changed from dark red to prominent yellow/orange-white), avoiding misidentification as a Boss rage alert in dark maps.

## 4.0.0-beta.261011

- Streamlined Star Force Mega Man (`WarRockStelar`) controls: M1 dedicated to Buster, M2 dedicated to Shield, Reload activates Battle Cards sequentially (hold to continuously execute queued cards across animation cooldowns); Mouse Wheel Up draws 6 cards when custom gauge is full, Mouse Wheel Down toggles Lock-on; both wheel inputs return automatically to combat weapon with a shared cooldown. See [Class Mechanics: Star Force Controls](docs/class-mechanics.md#2-star-force-mega-man-controls--battle-cards).
- Added Lock-on HUD status indicator for Star Force Mega Man.
- Updated Star Force Mega Man's Ammo2 card gauge to a custom gauge assembled from MM8-style tiles.
- Fixed card queue shift logic reading index 6 in a 6-card hand; an exhausted hand now clears cleanly and stops continuous firing without automatically drawing a new hand.
- Fixed an issue where Dickhead projectile throws were blocked by shields.
- Fixed an issue where Bosses taking damage in Boss FFA could not build Rage.

## 4.0.0-beta.261010

- Optimized input responsiveness for Shin Negaman, Alpha, and AlphaEX where continuously holding M1 prevented Reload input when resources were full; restored Shoryuken response windows during Alpha/AlphaEX triple-slash transitions and standard secondary attack recovery.
- Fixed an issue where Mega Man's Gyro Attack, Black Hole Bomb, and Spread Drill did not automatically regenerate energy.
- Fixed `strlen called with invalid string argument` engine warnings during map loads, boss morphs, and phase mugshot queries: teammate bar initializes cache before sync reception, Decoy weapon cleanup skips unassigned records, and phase mugshot query verifies record existence; patched missing WEPHIDE string check in the required base fix without modifying external packages.
- Optimized single-boss rule storage `uh_sv_bossrules`: long configs are saved in multi-line INI format to prevent 256-byte line truncation while preserving 256 rules and 16,384 character capacity; `uh_boss_export` outputs chunked commands compatible with 4096-byte `exec` line limits for `.cfg` execution. See [Boss Selection Settings](docs/boss-selection-settings.md).
- Morshu can now cast rope with Reload during bomb lifting, throwing, and recovery without interrupting weapon actions.
- TropicalMWS can now cast ultimate ability with Reload during skateboarding, shooting, and recovery.
- Fixed erroneous `RCON set …` notifications during automatic random Boss Events; notification now only appears when explicitly forcing a Boss Combo or setting event counters.
- Removed the extra 3-second post-phase invulnerability on Clownpiece, preserving protection only during health recovery and weapon switching; boss is immediately attackable when the next phase begins.
- Added round timer adaptation for Clownpiece's 6 phases: dynamically budgets remaining round time across phases while keeping phase countdowns fixed; added server options `uh_sv_clownpiece_autotime` (default true) and `uh_sv_clownpiece_w2_time` / `uh_sv_clownpiece_w8_time` (default 30s each, range 1–300s) under **Server Options → Boss Setup**.
- Adjusted Clownpiece W2/W8 spell card mechanics: Boss takes no damage; survivor damage converts into phase timer reduction (up to 50% max reduction); HUD displays total seconds reduced; team/environmental damage yields no reduction; preserves spell card bonus condition when no survivors die.
- Buffed Mosquito Demoneye: latching bite base damage and self-heal increased from 25 to 40; added 80% damage reduction while latched.
- Fixed an issue where Shiny KickChamp's energy bar remained fixed without displaying slide/dive consumption.
- Fixed missing PingButton compatibility bytecode in release build packages causing player pings to be visible only to self in standard LMS.

## 4.0.0-beta.261009

- Added server read-only diagnostic commands `uh_boss_check <actor>` and `uh_boss_pool [tier]`: inspect eligibility, player count thresholds, pick counts, repeat bans, weights, and empty pool fallback states for specific bosses or tiers (common/rare/special/ultra/ex or 1–5). See [Boss Selection Settings](docs/boss-selection-settings.md).
- Added per-boss rule configuration commands and archived storage `uh_sv_bossrules` (16,384 char capacity): override `mode` (random/forced/disabled/inherit), `weight` (1–1000000), `minplayers`, and `maxplayers` (0–64); provides `uh_boss_set`, `uh_boss_show`, `uh_boss_reset`, `uh_boss_list`, `uh_boss_export`, `uh_boss_reload`, and `uh_boss_save`. See [Boss Selection Settings](docs/boss-selection-settings.md).
- Added server CVARs for Boss selection strategies and probabilities: `uh_sv_bossselectmode` (0 least-frequent priority with weighted tiebreak / 1 pure weighted random), `uh_sv_bossavoidrepeat`, `uh_sv_bossavoidduplicates`, `uh_sv_bossforcedplayerlimits`, `uh_sv_bossrarelimit`, and `uh_sv_bossshadowchance`; added conditional full-pool tier probabilities `uh_sv_bossfullultrachance`, `uh_sv_bossfullspecialchance`, `uh_sv_bossfullexchance`, and `uh_sv_bossfullrarechance`. See [Boss Selection Settings](docs/boss-selection-settings.md).
- Added Bonus Event server read-only diagnostic commands `uh_event_check <stem>` and `uh_event_pool`: inspect event configuration, history, pick blocks, and EX progression. See [Bonus Event Settings](docs/bonus-event-settings.md).
- Added Bonus Event selection policy and player limit CVARs: `uh_sv_bonusselectmode`, `uh_sv_bonusavoidrepeat`, `uh_sv_bonusforcedplayerlimits`, and `uh_sv_bonusexplayerlimits`; added `uh_event_policy` query command. See [Bonus Event Settings](docs/bonus-event-settings.md).
- Added per-event EX progression configuration commands (`ex_count`, `ex_target`) supporting target validation, self-reference prevention, and delayed addon verification.
- Added per-event rule configuration and archived storage `uh_sv_eventrules` (multi-line INI format): configure random/forced/disabled modes, weights, and player thresholds via `uh_event_set`, `uh_event_show`, `uh_event_list`, `uh_event_export`, `uh_event_save`, and `uh_event_load`.
- Added global Bonus Event player limit and EX threshold CVARs in **Server Options → Events** (defaults: 12 players / 3 occurrences).
- Rebalanced Bonus Event random pools: Boss FFA and Football FFA moved to no-player-limit pool; Parade, Darkness, Brick, and Mosquito retain 12-player limit; Satan Seal FFA converted to unconstrained EX version of Boss FFA (triggers on 4th appearance after 3 Boss FFAs).
- Fixed an issue where morphing into a Demoneye retained multi-jumps and wall-jumps from original classes: round start Bonus Events, Money Bait, and Money Bomb morphs now clear inherited jump tokens and heights upon initial transformation.
- Fixed Clownpiece spell card titles, timers, and bonus states not displaying on remote clients and spectators.
- Adjusted Mega Man Noise Crush phase 2 wave: checks for bounce recovery immediately upon floor collision, enabling close-range ground bouncing into phase 3.
- Oil Slider oil puddles can now be ridden by all classes: self and teammates mount directly; enemies take damage before mounting; riding operates independently of current weapon; stepping on puddles extends ride duration.
  - Pressing M1 while riding jumps off the board without consuming ammo; M2 continues shooting oil to extend ride time.

## 4.0.0-beta.261008

- Converted the following enemies to cooperative mobs:
  - Biribaree
  - Blader
  - ScrewBomber
  - Metrenger
  - KillerBullet: flies along original heading, accelerates linearly towards detected targets, and detonates upon piercing players, hitting walls, or destruction.
- Fixed an issue where Zangief (including Shiny) spawned two corpses upon death.
- Fixed an issue where DLC Centaurman Options disappeared early, became invisible, or had desynced angles on remote clients; Options now spawn and manage per-player without stealing slots across multiple Centaurmen.
- Fixed an issue where DLC Centaurman Reload did not inflict invisibility.
- Adjusted standard Time Stopper freeze: takes damage after armor calculation to unfreeze target early, restoring mobility on the next tic; initial hit does not unfreeze; subsequent Time Stopper damage does not immediately re-freeze; global time-stop branches preserve standard rules.
- Reduced Mega Man Noise Crush phase 3 explosion base damage from 314 to 50, aligning with Razon 3; daily damage multiplier, explosion frequency, and radius preserved.
- Fixed Sad Toadman phase 2 MadFire, StormFlush, and Toadgasso ultimates preventing turning: changed to movement lock only (`uh_stopplayer`), restoring aim turning and view-aligned Toadgasso dash; jumping remains disabled during casting.
- Fixed Captain Blitzkrieg ultimate energy bar desync in multiplayer where edge-case R input caused desynced activation between server and client; energy gain, deduction, and casting authority are now strictly server-governed (introduced shared helper `classes/shared/server_power.acs`).
- Added `FISHBLACKPAINT_DYE = 19999` solid black translation for ColdDragoon paint effect; removed unused ACS palette constant `POWERFLIGHT = 10680`.
- `tools/compile-acs.sh` now automatically compiles `UHCOMBDB.o`.

## 4.0.0-beta.261007

- Added match duration display to Survivor defeat screens, formatted with two decimal places (e.g. `Battle Time: 12.34s`); quick-kill rewards preserved.
- Added Keep on Fire (On Fire) boiling water effect: boiling starts ~0.5s after submerging at least half body in water; water cools down after heat source departs; scalds players within 128 units line-of-sight with `80 x fire stacks` damage every ~0.5s (teammate damage halved); replaces fire AoE damage in water with scald damage, adding bubbles, surface steam, and sound FX.
- Added `trill-pingbutton-v5h` compatibility overlay: pings, death markers, and positions visible to all players and spectators across teams in Unholy LMS; supports third-person and death cameras; targets integrate with Unholy teammate logic and portraits; PingButton must load before Unholy.
- Merged TidalManiac (and Shiny) water mine M1 into main weapon Reload, preserving energy consumption, animations, and shield branch; removed separate mine weapon; bots fire mines directly and use mine scatter / Torrent for special attacks.
- Improved TidalManiac weapon HUD animation.
- Restored Razon 3 host threshold settings: win streak, lose streak, Hell Mark, Speciman kills, Gauntlet treasure redemption, Bad LMS count, and Bonus Event round interval in **Server Options → Game Rules → Round Thresholds** (range 1–100). See [Server Gameplay CVARs: Round Thresholds](docs/server-gameplay-cvars.md#1-round-threshold-limits).
- Connected Bonus Event random selection to least-frequent priority system matching Boss selection: prioritizes events with lowest appearance count, using weights for tiebreaking; appearance counters persist across rounds and maps.
- Improved spectator join interface (Enter key): allows manual class name entry via TextField to join the match.
- Restored missing text color definitions from Unbound: added `w Ice`, `x Fire`, `y Sapphire`, and `z Teal` in `TEXTCOLO` so `\c[Teal]` and `\c[Sapphire]` render properly.
- Fixed an issue where Nega Super Arm (and Shiny) grab duration bar continued flashing after throwing.
- In Bonus Event winner boss selection, if the winner spectates or disconnects before match assignment, the chosen boss is preserved and assigned to another random living player.
- Re-categorized Qwant moves into functional slots: 2 Ranged, 3 Rapid Fire, 4 Melee, 5 Power, 6 Area/Control, 7 Defense/Support; UIX weapon bar and wheel updated accordingly.
- Removed 4-move starting cap for Qwant, supporting all registered moves and addons; move relearning replaces current move with unowned moves without consuming ammo when all moves are owned; Pharaoh Roulette and UIX wheel read full move list.
- Added server CVARs for Qwant and NegaMan opening copy weapon counts in **Server Options → Rules**: Qwant default 4, NegaMan default 3; gives all weapons if count exceeds pool. See [Server Gameplay CVARs: Opening Copy Weapons](docs/server-gameplay-cvars.md#2-opening-copy-weapon-counts-qwant--negaman).
- Fixed Mega Man's GyroAttack secondary projectiles, FireStorm fire shield, ChillSpike initial shots, OilSlider fire puddle, PharaohShot charge ball, and TenguBlade dash/slash bypassing daily friendly fire lists.
- Added friendly fire protection for `GyroChopper` and `WheelCutterSaw` when random copy-weapon friendly fire is disabled.

## 4.0.0-beta.261006

- Converted the following enemies to cooperative mobs:
  - SpaceMetall
  - FireTelly
- Changed Mega Man charge shots (stages 3 and 4) from multi-shot to single-shot; cleaned duplicate firing branches and legacy `NoWeaponsBusterOnlyFinalFlag` markers.
- Fixed BreakDash M2 and CopyVision Mega Buster firing base game 10-damage shots; updated to 100-damage `MegaShotU`; patched BlackHole, TimeStopper, SkullBarrier, and FlashStopper robot Buster branches.
- Added server setting `rz_sv_mega_m2_weapon_count` for Mega Man copy weapons granted per M2 (default reduced from 6 to 3); distributes evenly across slots; full weapon pool granted if setting exceeds pool size; subsequent M2 replaces copy weapons while preserving base Buster.
- Ported Razon 3 AFK penalties: supports On Fire, GUHU, Super GUHU, Money Bait, Money Bomb, and Random modes; added menu settings `rz_sv_noafk_item` and `rz_sv_noafk_delay` (default disabled, 60s delay, range 30–300s). See [AFK Penalties](docs/afk-penalties.md).
- AFK detection tracks button inputs, aim angles, and 3 movement axes; rotating view to search for enemies is not flagged as AFK; timers reset upon death, revival, or morph; warns 10 seconds before punishment.
- Added console alert when both mod AFK penalties and engine `sv_afk2spec` are active; set `sv_afk2spec 0` to use mod penalties exclusively.
- Added `NOINFIGHTING` flag to `GenericRobot` base class to prevent cooperative mobs from attacking each other on accidental hits.
- Ported TopFiend as cooperative mob from Razon 3 (standard and 3BC bouncing top variants); restored TopFiend spawns in mob crates.
- Added skin immunities for Mega Man copy weapons: NeedleMan skin using Needle Cannon is not forced to spectate; DustMan skin using Dust Crusher does not turn into YustMan.
- Fixed Slugger retaining pistols and crate weapons upon morphing into a boss by registering weapons in the shared morph cleanup table.
- Corrected EyelentoMajor grenade throwing animation.
- Buffed RedBaron missile explosion: primary explosion damage increased from 35–50 to 120–150; 5 secondary explosions increased from 35–50 to 80–120; explosion radii expanded from 50 to 100; secondary explosion spawn distance expanded from 0–32 to 0–200.
- Reduced Napalm Bomb nuke chance from 1/32 to 1/128.
- Added unique death sound effect when killed by Ice Wall projectile variants.
- Fixed an issue where GUHU, Super GUHU, Fortune Coin, On Fire final burn, and Damocles fell back to generic hazard death tips when lethal damage was preceded by player attacks; added dedicated HazardTags preserving the recent attacker's kill credit.
- Converted Dickhead revival explosion to dedicated `DickheadRevive` damage type with custom HazardTag; telefrag multiplier and death FX preserved; Eden Holy Mantle exemption preserved.
- Corrected SniperArmorShotU_Exile explosion colors.
- Corrected TropicalMWS_W Reload icon.

## 4.0.0-beta.261005

- When Bosses win standard LMS, boss friendly-fire protection is removed immediately upon `gameover`, allowing surviving bosses to fight post-round.
- Adjusted Atomic Fire ammo bar: charge stages 30/40 use Unbound two-color flashing; stage 50 uses v7a rainbow animation; horizontal and vertical HUDs synchronized; separated ammo FX from charge progress layers to prevent overlay corruption.
- Updated Mega Man Homing Sniper random pool classification to slot 4, Centaur Flash to slot 7; synchronized DTADD weapon registrations for UIX; daily randomized weapon IDs preserved.
- Fixed an issue where `BlackHoleWepU` ammo bar regenerated energy while greyed out; energy regeneration resumes after grey bar concludes.
- Synchronized MegaManU_W ammo bar and base skin portrait charge flashing based on charge value and client timer, matching CBM Mega Man behavior.
- Fixed Commando Bomb M2 direct hit using base game 20 damage; updated to 200 base damage scaled by daily multiplier.
- Slugger Flame Shot flames now ignite oil puddles and trigger flame death FX via `SluggerFire` damage type.
- Nerfed Slugger Flame Shot: reduced damage instances from 3 to 1 per flame, damage reduced from 15–35 to 15–25.
- Slugger airdrops display weapon letter icons upon landing and grant weapons on pickup; weapon selection rolls upon landing rather than on pickup.
- Moved Typhoon Bonus to unconstrained player count random pool matching standard FFA; remaining high-count Bonus events retain 12-player threshold.
- Fixed Typhoon Bonus startup using event ID 16 instead of Demoneye body ID 13, resolving morph failure; added startup argument validation for all-Demoneye events.
- Fixed C-Section M1 weapon HUD waiting for server jump before playing in multiplayer; added locally predicted entry point while preserving Bob’s Rotten Head throws and firing cadence.
- Ported Holy Mantle, Soy Milk, The Bible, Guppy’s Head, and Free Lemonade for Eden from Razon 3, integrating into shared item registry, HUD icons, and active charges; Shiny Eden天使 pool now draws Holy Mantle / Godhead. See [Class Mechanics: Eden Items](docs/class-mechanics.md#3-eden-isaac-item-artifacts).
- Fixed Damocles sword and line FX disappearing prematurely on remote clients due to unexecuted inventory jumps.
- Cleaned unused legacy actors (`CopyNerfGiver_P`, `WeaknessBase_P`, `BasicPain_SlamHit`, DecoyBot `P_CheckOld`), removing calls to 4 missing ACS scripts.
- Fixed Sutoka whip hit calling renamed `uc_istracerenemy`, which caused Unknown Script errors and prevented item steal checks; patched lightning claw hooks, restored Wonder Stone alerts, and updated Eyelento Major tracer checks.
- Connected Bonus Stage music to shared weighted music pool via `AddBonusEventMusic` / `AddBonusEventMusicByStem`; MLG, Sumo, Kamikaze, and Business eyes randomize between original and Unbound legacy tracks. See [Bonus Event API: Music Pools](docs/bonus-event-api.md#7-bonus-event-music-pools).
- Fixed false-positive baseline warnings in Boss Combo tests due to music and title adjustments.
- Enabled gravity on CrowNest bird turrets so they fall to the ground naturally upon spawning.
- Fixed GBeast EraseCross incorrectly playing Claws animation on remote clients, eliminating HUD stutter.
- Migrated Slugger weapon crate to dynamic registry database managing weapons, weights, voices, and icons; shared cleanup and weapon switching logic implemented.
- Restored and optimized DrawBar and ammo HUD displays for Slugger (and Shiny).
- Reworked Slugger secondary attack (M2): changed from manual wooden crate throw to targeted airdrop call, crashing down with explosive AoE damage and leaving weapon crate supplies.
- Replaced Slugger Shotgun weapon HUD with Razon 3 assets and firing/reload animations.
- Added automatic melee bayonet for Slugger pistols, heavy machine guns, rocket launchers, and shotguns: initial M1 within 48 units of an enemy performs a free bayonet strike.
- Added slight homing tracking to Slugger Rocket Launcher.
- Ported Slugger Flame Shot, Enemy Chaser, Drop Shot, and Two Machine Guns from Razon 3; Enemy Chaser applies strong homing under Unholy team targeting rules.
- Fixed BirdNest (Crow Nest) rapid and scatter projectiles lacking damage source actors, which caused `core_damageactor` errors and uncredited damage.
- Fixed an issue where firing interrupted Floovy ultimate preservation state, leaving permanent invulnerability.
- Fixed Floovy M1 premature unmorph protection skipping camera creation and failing to transition to unmorph view.
- Adjusted Floovy ultimate self-preservation heal: immediately restores full max HP rather than healing based on marked target's remaining HP; environmental damage triggers retain kill credits and defensive buffs on marked targets.

## 4.0.0-beta.261004.hotfix1

- Fixed a 0-tic loop in GBeast/FBeast death explosion animations that caused client crashes; corrected shared death flash translation indices.
- Fixed an issue where cancelling ChargeCross dash with M2 during Beast Out left permanent invulnerability on GBeast.
- Fixed KFCDragon756 resetting to phase 1 colors after entering phase 2; phase 2 translation is now preserved across weapon ready states.

## 4.0.0-beta.261004

- Fixed Rogue M1 3-hit punch damage being nullified by Survivor protection.
- Expanded Rogue punch collision from Radius 5 / Height 5 to Radius 24 / Height 32 to improve combo consistency.
- Expanded Rogue combo kick radius from 80 to 160, maintaining full damage within 80 units.
- Added continuous wind gusts during CXAirMan M2 stealth stacks: stacks 1–5 blow enemies back within 512 units in a 90° arc without penetrating walls, harming teammates, or dealing damage; stops at stack 6 full stealth or upon uncloaking.
- Fixed CXAirMan Reload teleporting out of map bounds when targeting wall corners.
- Fixed CXAirMan Reload after 6th M2 full stealth stacking stealth properties repeatedly, causing permanent invisibility.
- Adjusted CXAirMan Reload sound FX: plays `weapon/airshooter` once on start and once on reappearance, eliminating duplicate audio stacking.
- Adjusted CXAirMan decloak timing: decloaks or restores alpha only on the final frame of `CXAirManTeleportFX`, preventing stale FX from prematurely clearing newly activated stealth.
- Granted permanent hovering mobility to CXAirMan matching Misery.
- CXAirMan M1 projectiles can now be shot down by enemy attacks.
- Consolidated hovering logic for Misery and CXAirMan into a shared controller managing ceiling limits, stamina, and flight states.
- Added a 5-second grab duration limit to Nega Super Arm (and Shiny), auto-throwing upon expiration.
- Added a 5-second stealth duration limit to RNC Clashman Reload, auto-decloaking into standard cooldown upon expiration.
- Fixed teammate sync triggering ACS execution limits on servers with >32 players.
- Fixed MosquitoEye misidentifying enemies with Survivor protection as teammates, preventing grabs and life drain.
- Removed EdenBomb immunity from Survivor protection, allowing Eden bombs (including Troll Bomb and Mega Troll Bomb) to damage self, teammates, and enemies.
- Increased `TimeStopperUFlag` cap from 560 to 2240 (recovering 1 pt/tic), restoring full recharge duration to Unbound original 64 seconds.
- Fixed FFA mini-games misidentifying enemies as teammates, which prevented Zangief grabs/slams and caused KickChamp slides to grant enemy protection.
- Restored v7a health regeneration on KamikazeEye held M1 explosion: heals 2 HP every 2 tics for 250 HP total.
- Fixed GhostEye event invisibility prematurely clearing M2 stealth when overlapping.
- Cooldown weapons (such as Spark Shock) now pause automatic energy recovery during active cooldowns.
- Ported Razon 3 Death Shitting mechanics into Bonus Stages, controlled via server toggle `uh_sv_bonusdeathshitting` (default true). See [Server Gameplay CVARs: Bonus Death Effects](docs/server-gameplay-cvars.md#4-bonus-stage-death-effects).
- Ported Razon 3 Bonus Event winner boss selection: countdown presents 3 common bosses and 1 rare boss selectable via movement / attack keys; winner priority-morphs into the chosen boss for the following round.
- Overhauled Mega Man daily randomized copy weapons: host can configure multipliers for common, minor, and major god weapons, with min/max quantity limits. See [Mega Man Daily Weapons](docs/megaman-daily-weapons.md).
- Removed legacy 40–60x and 80–120x ultra-rare god weapon tiers; default common multiplier set to 0.75–1.25, minor god weapons 2–4/day at 2–3x, major god weapons 0–1/day at 4–6x, friendly fire weapons 6–10/day across the pool.
- Added Mega Man Daily Weapons server menu with direct numeric input.
- Updated Napalm Bomb nuclear explosion visuals.

## 4.0.0-beta.261003

- Added magazine, skill, and rage progress bars and Rage/Wrath tier displays for Neru.
- Fixed Neru projectiles calling missing `neru_countinv_acs`, which caused console spam and failed to read shooter Rage/Wrath tiers.
- Fixed an issue in Shiny Zangief air slam second half misinterpreting aim direction as grabbed player TID.
- Fixed Zangief dropping teammates instead of throwing them on subsequent M1 presses; normal and shiny variants now apply horizontal toss velocity with teammate damage immunity.
- Fixed Shiny and True Power attack chains incorrectly falling back to standard definitions, restoring amplified values for Kate, RageUnit, HandyMan, Trickster, Igniter, GloryGuster, Tristana, HeavyBomber, TidalManiac, PartyBomber, Quickster, DecoyBot, and bot attacks.
- Fixed Electrician Shiny lingering projectiles not scaling damage upon inheriting base explosion chains: explosion damage set to 100 for normal and 150 for Shiny based on shooter body.
- Fixed Kate and TidalManiac Shiny bots selecting normal weapons, YellowWizard Shiny bot attempting to swap non-existent weapons, and Nega Shiny SearchSnake reverting to standard projectile chains after jumping.
- Restored standard Juggernaut dash explosion base damage to 200, preserving Shiny variant at 300.
- Ported HarpStrumm luck system, storing luck in class-dedicated variables to prevent shared variable collisions.
- Integrated Razon 3 special items into corresponding crate item pools.
- Changed 1UP LMS event to grant one Dickhead item.
- Migrated LMS penalty messages, icons, and effects to a dynamic database via `DefineLMSEvent`. See [LMS Event API](docs/lms-event-api.md).
- Replaced Deadly Firearms assist icon with v7a variant.
- Fixed Cobe spawning without weapons or attack capabilities after morphing.
- Adjusted Cobe weapon bar: fills only after throwing axe with M1, clearing upon axe return or recall, matching Unbound original behavior.
- Improved Cobe weapon bar visual effects.
- Added multilingual randomized "dadadadada" voice clips for Cobe attack and taunt lines.
- Fixed Boss VS names and icons in online Boss Duels.
- Fixed Clownpiece spell card titles, bonus status, and timers not displaying on remote clients, correcting phase transition timer restarts and mid-game sync.
- Added missing ReloadIcon definitions for BlackDevilEye, ThomasTheTrain, Magnetismo, Elitist Sue, MakeAGoodZero Phase 2, and TorontoCalifornia.
- Fixed LMS penalty automatic Super GUHU calculating zero explosion damage when players held no regular items; auto-triggers now calculate at least one baseline item.
- Removed 30-second restriction on X-Ray when two players remain.
- Removed the last two non-spell card phases from Clownpiece.
- Fixed missing BlueElephant jumpscare on kills, restoring sound effects.
- Converted shared Mega damage type used across Nega copy weapons into dedicated types (including Shiny, Search Snake, and Chill Shot variants), adding teammate protections and pain/death mappings.
- Increased Spring Eye lifetime from 61 to 600 tics.
- Reduced Misery movement speed from 1.2 to 1.0.

## 4.0.0-beta.261002

- Improved running and wall-climbing HUD animations for `RedeadGuts_W_Pissed`, alternating climbing claw actions when holding M1.
- Fixed PlasmaSpark full-energy shield disappearing prematurely on remote clients.
- Fixed Scrotoman remaining invulnerable after exiting vehicle upon casting ultimate.
- Fixed Scrotoman vehicle sprite not displaying during ultimate.
- Added sound effects for Scrotoman ultimate.
- Optimized Scrotoman M2: now allows shield charging dash with improved sprites and HUD animations.
- Added dedicated damage types for Nega Napalm Bomb, Needle Cannon, and Ice Wave (including Shiny), removing daily randomized friendly fire.
- Added Unknown curse effect for Pharaohman4MI.
- Fixed missing M2 blue bar on NegaMan_W and Shiny NegaMan in horizontal HUD mode.
- Adjusted Shiny NegaMan Skull Shield: M1 interrupts uncharged/half-charged shields; full charge release cannot be interrupted by M1 and transitions to the next weapon upon completion.
- Fixed missing continuous contact damage on Astromancer M1 shields.
- Fixed Handyman (and Shiny) unable to boost upwards with M1 when falling after M2.
- Added missing weapon tags for all Shiny NegaMan charge-switch weapons.
- Improved X-Ray visuals: indicators automatically hide when enemies are fully visible in line of sight; vision outlines render translucently at 3D head coordinates to eliminate close-range aim obstruction.
- Added death and pain sound effects for Berserker; added death sound effects for WarRockStelar and MeguhMang.
- Restored phase mugshot transitions for TimemanC and KFCDragon756 across boss health borders, UIX teammate bars, scoreboards, and HUD ScoreIcons.
- Added phase mugshot API `DefineTeamPhasePresentation` for addons and custom bosses. See [Boss Phase Portraits](docs/boss-phase-portraits.md).
- Updated Misery skin (by Soundwave).
- Updated Misery weapon HUD and attack animations.

## 4.0.0-beta.261001

- Fixed Redead Gutsman phase 2 not automatically draining health.
- Migrated Boss Combo rosters, player thresholds, weights, and music configs to runtime registry with public addon API. See [Boss Combo API](docs/boss-combo-api.md).
- Fixed Three Destrons playing incorrect BGM, restoring Destron intro theme.
- Added Final Speciman and Speciman DX to Speciman Rush candidate pool, selecting 5 bosses out of 8 candidates.
- Adjusted Shadow Tricks Duel: fake identity can move, attack, and display Boss VS HUD upon initial morph; real identity rolls rarity weights matching standard Shadow.
- Fake Shadow bosses dying before identity reveal cancel remorphs, re-checking alive status to avoid respawning dead bosses.
- Converted Misery multi-jumps to permanent hovering mobility: flight disables at 160 units above ground and resumes at 152; hovering over hazard pits drains stamina under CBM Alien rules.
- Increased KickChamp ammo cap from 200 to 300.
- Fixed missing kill sound effect when Destron frags players.
- Added pain sound effects for Destron.
- Fixed projectile trajectory anomalies on BlackDevileye.
- Added missing Ice and Fire death mappings in ClassBase, triggering frozen and burning death effects across shared damage types.
- Added environment interactions for Ice and Fire attacks.
- Restored Unbound True Power behavior for Bosses and Demoneyes: maxes out Rage if rage bar exists; increases max health and heals 2000 HP if no rage bar exists (reusable).
- Fixed Eden item icons not displaying in online matches.
- Added `+FORCEXYBILLBOARD` flag to Eden tear projectiles.
- Removed debug functions from ShinNegaman Reload.
- Improved ShinNegaman attack HUD animations and sound effects.
- Improved ShinNegaman obituary strings.
- Added SpreadRune compatibility for ShinNegaman Nega Astro Wave and Nega Flame Sword.
- Restored Unbound continuous dash for Miu W1 M2 (and Shiny): allows directional re-dash during pauses up to 3 consecutive dashes at full energy; fixed attribute stacking bugs.
- Improved Miu HUD elements.
- Nega Super Arm (and Shiny) can now grab teammates.
- Fixed a game crash triggered by specific inputs immediately upon morphing into MosquitoDemoneye.
- Fixed console warning spam from DecoyBot.
- Fixed Dawnbreaker standard shots bypassing friendly fire randomization; shots now adhere to daily friendly fire pool.
- Added direct hit damage for Dawnbreaker BlastRuneB/D/M, standardizing base damage at 50 with daily multipliers.

## 4.0.0-beta.260930

- Fixed an issue where Misery could continuously cast M2 on client before energy refilled after Reload.
- Fixed Misery Reload only displaying teleport effects in multiplayer.
- Fixed missing audio alert when "A powerful foe approaches!" notification appeared during round preparation.
- Fixed X-Ray vision not displaying in online matches when 2 players remained or when Lin reached half health.
- Restored Unbound speed recovery on Balrog after grabs: grab success clears dash slowdown; throwing and ground slam share unified cleanup to prevent lingering slowdown.
- Restored Balrog M2 ground slam root effect on survivors (80 tics).
- Unified player pointer validation: `uh_PointerExists` supports regular player and true morph validation modes.
- Fixed Trickster (and Shiny) M2 stealth not fading first-person weapon models; alpha transitions use isolated AlphaPower with proper cleanup on weapon swap, death, or unmorph.
- Fixed CaptainAssShiny, HandyManShiny, SmokeBanditShiny, and TidalManiacShiny jumping to legacy state labels upon death causing `left without a state` errors.
- Added missing `NOMORPHLIMITATIONS` flag to Shiny variants, standardizing movement, pain audio, and portrait behavior upon morphing.
- Fixed HomingSeeker and other classes displaying normal portraits on HUD after activating True Power; Shiny static portraits now render via presentation tables.
- Added portrait registrations for all Shiny forms, fixing empty teammate portraits and scoreboard icons; preserved MegaManShiny skin fallbacks and EdenShiny inherited portraits.
- Added teammate bar and scoreboard portrait registrations for PlainDevilDemoneye, RichDevilDemoneye, ProtoManBadGuy, and WeakHorse.
- Added HUD ScoreIcon registrations for TyphoonDemoneye, BrickDemoneye, and MosquitoDemoneye.
- Fixed Boss and LMS music duplicate requests from client listeners causing repeated `Music "xxx" not found` warnings when music packs were missing.
- Added HUD ScoreIcon registrations for Berserker, SoccerRock, Floovy, SakikoTogawa, MakeAGoodZero, and BlueElephant.
- Fixed horizontal and vertical HUDs drawing Maestro behind portraits for Bosses, Demoneyes, and custom-portrait survivors.
- Fixed DecoyBot (and Shiny) attack HUD stuck on idle frames in online play.
- Improved DecoyBot attack animations when copying CloseCombatUnit.
- Added ReloadIcon for ShinNegaman.
- Improved weapon and projectile visuals for ShinNegaman CopyAttack1 (Nega Rolling Cutter).
- Fixed MeisterWahwee phase 1 M2 jumping to a non-existent state.
- Fixed Sampi unable to use Reload ability.
- Updated Sampi Reload icon.
- Ported Berserker Diehard ability, auto-triggering continuous health regeneration when falling to <= 35% HP (once per life).
- Adjusted GBeast energy costs: Heat and Elec consume full bar (100); Slash (W4) consumes half bar (50).
- Standardized weapon switch audio for GBeast and FBeast to MMBN cursor sounds.
- Adjusted GBeast Erase: M2 fires one shot consuming 10 energy; hold M2 for rapid fire; continuous 10 shots in rage phase fires a finishing laser beam; releasing M2 or swapping weapons resets counter.
- GBeast Heat and Elec block M2 when energy is insufficient, preventing M2 holding from blocking energy regeneration.
- FBeast Aqua can be cancelled early by releasing and pressing M2 again.
- Adjusted FBeast energy costs: Tomahawk and Ground consume half bar (50); Tengu and Dust consume full bar (100); blocks M2 when energy is insufficient.
- Added wing flap sound effects to FBeast double jump via `*airjump` mechanism.
- Refactored `core_weaponcolor`, separating audio playback from recoloring logic; `core_chargecolor` reuses translation logic directly.

## 4.0.0-beta.260929

- Fixed Ready state re-entrancy issues on certain bosses in online play.
- Removed debug effects from TimeStopper.
- Fixed DecoyBot not holstering weapons upon morphing into a Demoneye.
- Removed default movement slowdown from generic pain states.
- Restored Unholy item friendly fire protection (`ProtectUnholyItem`) for survivors upon round start and respawn.
- Adjusted render order of text-based teammate info so it is properly covered by SBARINFO status bars.
- Restored color translations for NegaBlackHoleBomb projectile variants.
- Corrected Typhoon Demoneye color palette.
- Corrected Brick Demoneye color palette mappings.
- Corrected weapon names for Typhoon Demoneye and Mosquito Demoneye.
- Zangief (and Shiny) can now body-slam teammates: retains animations, displacement, and visual effects without inflicting damage or clearing teammate protections.
- Restored KickChamp (and Shiny) ground slide knockback; sliding into teammates knocks them back without dealing damage.
- Improved LMS Event 12 (ChanceBox) banner text.
- Skullman4MI standard and enraged forms consume 100 ammo when throwing shield with M1 while holding shield with M2; enraged form requires full ammo to activate M2.
- Fixed and verified BGM and track metadata for combo bosses and special duel events.
- Health adjustments:
  - BalladeGB: `3000 + 400n` -> `10 + 1n`
  - Sampi: `4000 + 350n` -> `30000`
  - Pharaohman4MI: `2500 + 245n` -> `3500 + 295n`
  - TimemanC: `2539 + 500n` -> `4010 + 724n`

## 4.0.0-beta.260928.hotfix1

- Fixed `Out of bounds memory access in ACS VM` runtime crash.

## 4.0.0-beta.260928

- Initial release.

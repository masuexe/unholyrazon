<!-- reviewed-through: dc6a3523 (2026-11-18) -->
# Lessons from merged work

Read this file before changing code. It records what recent work in Unholy Razon got wrong, what had to be fixed a second time, and what slipped past verification.

## How this file works

- **Format**: Each entry states a **rule in bold**, why the defect happened, concrete commit or investigation evidence, and a `Seen N× (YYYY-MM-DD, ...)` counter tracking how many separate days the pattern appeared.
- **When to add an entry**: Whenever a commit fixes a regression from recent work, requires a follow-up fix on a sibling actor/script, or reveals a verification gap.
- **3-day promotion rule**: A lesson seen on **3 or more separate days** (or any rule that can be deterministically enforced right away) is promoted into [AGENTS.md](AGENTS.md) and/or a static/runtime check in [`tools/gate.py`](tools/gate.py) (paired with a mutation case in [`tools/mutation_test.py`](tools/mutation_test.py)), and moved to [Promoted to AGENTS.md and tools/gate.py](#promoted-to-agentsmd-and-toolsgatepy).

---

## Fix the class, not the sample (Sibling sweep)

**Pure-visual projectile trails, beams, and explosion FX must inherit `BasicClientSide` (or strip `+USESPAWNEVENTSCRIPT`), while the damage-dealing actor stays networked with its own `Obituary`.**
- On 2026-11-13 (`1f477e60`, `a9470547`, `950ea57e`), Void Walker's `RazingRayPinpoint`, Super Megaman's beam visuals, Colonel Kachidonga's M2 trails, and Shin Hellbot's meteor shockwaves were moved to client-side visuals after `d46878d6` fixed `HF_PROJ` TID broadcasts ([docs/network-stall-investigation-261109.md](docs/network-stall-investigation-261109.md)).
- Four days later (`349abf5f`, 2026-11-17), the same online stall pattern had to be fixed on Qwant / QwantShiny `IceBeam` trails (`ICELAZORTrail1..2`, `S_IceBeamTrail1..2` in `src/actors/classes/survivors/qwant_copyweps/IceBeam.dec`) and Morshu's ultimate (`MorshuBombProjectileLITE`, `MorshuBombDebris`, `ForcedNegotiationHitbox` in `src/actors/classes/bosses/Morshu_W.dec`), and `ICEBEAM` needed its missing `Obituary` restored so kills did not fall back to `BasicFastProjectile`.
- When fixing network traffic, spawn-hook overhead, or missing obituaries on one weapon, `rg` across sibling directories (`qwant_copyweps/`, `shiny_moves/`, Boss ultimates) for `+NOINTERACTION` or trail/debris actors that still inherit `BasicProjectile` or `BasicGraphicEffect`.
- Seen 2× (2026-11-13, 2026-11-17).

**A survivor, copy-weapon, or item mechanic change must sweep its Shiny, assist-pool, and item-wheel siblings in the same task.**
- Mega Man's v6c Reload / M2 draw rework took four passes across five days: `e58d4279` (2026-11-13) added v6c assist draws; `d4c2a474` and `c3ef6f05` (2026-11-15) had to separate M2 weapon draws from Reload assist draws and toss Reload items onto the ground; `4ba4c16c` (2026-11-17) and `dc6a3523` (2026-11-18) then had to include all registered v6c items in the Reload pool and integrate Buster upgrades as thrown passives.
- Item wheel and automap marker fixes similarly recurred across sibling items (`bb5d00a7` on 2026-10-19 for True BusterMistress boxes, `614136bc` on 2026-11-05 for special inventory switching, `8b898638` and `810baa23` on 2026-11-16 for `PartyBallU`, infinite-item red borders, and Killer Box wheel offsets).
- Trace the whole registration table (`uh_itemdefs.acs`, `copy_weapon_runtime.acs`, `AutomapMarkers.generated.dec`) rather than patching only the reported item.
- Seen 2× (2026-11-15, 2026-11-17).

---

## Network, online replication, and Dedicated Server authority

**Unmorph and death cleanup must release flight, speed, and HUD state before clearing the identity token that gates the cleanup.**
- `3e9e1514` (2026-11-13) restored `MosquitoDemoneye` pit-stamina flight and unmorph cleanup, but `c1943331` (later on 2026-11-13) had to fix death-time flight release: `IsAnEye` (a non-persistent `Powerup`) was stripped by the engine on death before `UH_BossHoverRelease` ran, leaving `MosquitoDemoneye_HoverActive_F` and `PlayerPropertyFlight` active on the dead body.
- Earlier morph/extra-life transitions hit the same ordering trap (`043a0b68` and `5aa7fb90` on 2026-10-19; guarded for survivors by `check_survivor_morph_cleanup.py` and `check_extra_life_transition.py`).
- Always verify both voluntary/timeout unmorph and lethal damage while the morphed ability is active.
- Seen 2× (2026-10-19, 2026-11-13).

**Avoid server-side per-tic state mutations (`Thing_ChangeTID`, `A_ScaleVelocity`, `ThrustThingZ`, `A_ChangeFlag`) on high-count projectiles when spawn parameters or tic waits can express the same motion.**
- `d46878d6` (2026-11-13) found that calling `Thing_ChangeTID(0, 0)` unconditionally in `HF_PROJ` hooks emitted a `SERVERCOMMANDS_SetThingTID` packet for every projectile even when its TID was already `0`.
- `349abf5f` (2026-11-17) found that server-side `A_ScaleVelocity` on `IceBeam` trails, `ThrustThingZ` on `MorshuBombProjectileLITE` spawn, unused `Scale 5.5` on invisible `ForcedNegotiationHitbox` actors, and `A_ChangeFlag("NOGRAVITY", 1)` in `MorshuBombDebris::Death` each broadcast redundant `MoveThingExact`, `UpdateThingScaleNotAtDefault`, or `SetThingFlags` commands.
- Fold initial velocity scales/offsets directly into `A_SpawnItemEx`, strip unused visual properties from invisible hitboxes, and replace death-time `A_ChangeFlag("NOGRAVITY", 1)` with tic-exact `A_Stop` waits.
- Seen 2× (2026-11-13, 2026-11-17).

**Never rely on global MM8BDM `replaces` or stock gamemode CVARs when a behavior belongs only to an Unholy class or Unholy LMS.**
- `b9135bae` (2026-10-30) had to decouple Mega Man copywep projectiles from global MM8BDM actor replacements so base weapons and other classes were not altered.
- `18c60d2d` (2026-11-16) had to introduce a dedicated `uh_sv_teamdamage` scalar because stock `teamdamage` in standard LMS did not match Unholy's logical survivor/boss team friendly-fire rules.
- Seen 2× (2026-10-30, 2026-11-16).

---

## Verification and benchmarks

**Network traffic and performance benchmarks must lock player aim, disable mouse/joystick input, and run in a deterministic arena.**
- During the 261109 network stall investigation ([docs/network-stall-investigation-261109.md](docs/network-stall-investigation-261109.md)), an initial Super Megaman beam run showed `870,866` vs `925,621` UDP bytes across two builds whose weapon definitions were byte-identical. The difference came from unlocked aim and normal-map geometry changing beam segment counts.
- Rerunning in a flat arena with `use_mouse=0`, `use_joystick=0`, `cl_capfps=1`, and per-tic zero-aim assertions produced repeatable equal-work baselines.
- Seen 1× (2026-11-09).

**When a runtime MCP probe fails inside a full-suite batch with `bridge port never opened`, rerun the probe alone and check for leftover engine processes before reporting a regression — but never wave away a failure without an isolated green run.**
- Recorded in [docs/testing-strategy.md](docs/testing-strategy.md) Section 8: `mcp-network` and `mcp-team-info-sync` failed during a batch `--full` run when WADs were read across a slow mount, then passed alone on the exact same tree.
- Always record in the handoff and commit body which gate layer and which isolated probes actually ran at `HEAD`.
- Seen 1× (2026-10-30).

---

## Promoted to AGENTS.md and tools/gate.py

These lessons recurred across multiple tasks and are now enforced by [AGENTS.md](AGENTS.md), [`tools/gate.py`](tools/gate.py), and [`tools/mutation_test.py`](tools/mutation_test.py):

- **Every static checker must be paired with a mutation case in `tools/mutation_test.py` (`gate.py --meta`)** (`ff6a5ba6` on 2026-10-22; Phase 2 of [docs/testing-strategy.md](docs/testing-strategy.md) on 2026-10-30). `tools/check_state_loops.py` originally matched only single-line `States {` headers and silently skipped 52 two-line `States` + `{` blocks (the defect class behind the Half Press Hardman zero-tic crash); `tools/check_actor_contracts.py` counted actor declarations inside unterminated `/*` comments.
- **Deliver every `CLIENTSIDE` team-info and HUD receiver per connected client via `NamedExecuteClientScript`, and never send raw ACS string indices or custom `-1` registration IDs as network identities** (`73e84762` on 2026-10-21, `de693731` on 2026-10-24, `2d9a024b` on 2026-10-20). Documented in `AGENTS.md` under *ACS* and *Class presentation*, and guarded by `tools/check_team_visibility.py`, `tools/check_team_presentation.py`, and `tools/mcp/team-presentation-test.mjs`.
- **Every DECORATE actor reference, sound alias, LANGUAGE key, TEXTURES patch, and documented addon API entry point must resolve statically** (`f85eb0ab` on 2026-10-23, `0ea5ca62` on 2026-10-28, `6b1e4b4f` on 2026-10-30). Guarded by `check_actor_contracts.py`, `check_asset_references.py`, `check_lump_integrity.py`, `check_addon_api_contract.py`, and `check_addon_examples.py` in `gate.py --fast`.
- **Boss and Demoneye damage dealers must declare a `DamageType` covered by the friendly-fire protection tables** (`3b1ec3b3` on 2026-10-24, Tidal Tito explosions hurting Boss teammates; [docs/testing-strategy.md](docs/testing-strategy.md) Section 6). Guarded by `tools/check_damage_types.py`.
- **Razon 3 parity behaviors (Mercy banner colors, sequential Spread AirStrike, Eden Damocles death drop, rare Unholy Book suction) must be pinned by contract tests** (`4d92138a` on 2026-10-23, `168db904` on 2026-11-16). Guarded by `tools/check_razon3_parity_contracts.py` and `tools/mutation_test.py`.

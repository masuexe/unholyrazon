# Test Strategy - Unholy Razon 4.0

This document defines the plan that closes the test gap before the 4.0 release.
It states the current test state, the software-testing model that applies to this
project, the measured gaps, and the work sequence. It also records what the
expansion found. The audience is the project maintainer and any agent that
continues this work.

Related documents: [Agent Relay](agent-relay.md), [tools/README](../tools/README.md),
[docs index](README.md).

---

## 1. Purpose

The project has a working test gate. The gate was not sufficient for a release.
This document answers three questions:

1. What test levels and test types must a release cover?
2. Which of them does the project cover today?
3. What must the project add, in which order?

The plan uses risk-based testing. A defect that a player can see costs more than
a code-style defect. The plan therefore weights the online gameplay layer above
the static layer, and it requires proof that each test catches a real defect.

---

## 2. Test state

The gate entry point is `tools/gate.py`. It runs 36 checks in four layers:

| Layer | Checks | Runtime | Environment |
|-------|--------|---------|-------------|
| `--fast` | 27 | ~25 s | Repository only. No engine, no WADs. |
| `--smoke` | 4 | ~1 s | ACC compiler and the WAD tree. |
| `--full` | 4 | Minutes | Local Zandronum engine. |
| `--meta` | 1 (10 cases) | ~33 s | Repository only. Runs `--fast` first. |

Measured code surface under test:

| Item | Count |
|------|-------|
| DECORATE lines | 226,393 |
| ACS lines | 62,634 |
| Unique actor declarations | 13,854 |
| Weapon actors | 388 |
| Player classes in KEYCONF | 61 active |
| Named ACS scripts | 1,593 (160 CLIENTSIDE) |
| ACS libraries | 67 declared, 33 in LOADACS |
| CVARs | 305 |
| Documented addon APIs | 7 documents, 72 entry points |
| Working addon examples | 8 |

Measured history: 1,959 commits, of which 126 are fixes. The fix clusters are
`src/actors/classes` (117 file touches), `src/acs_source/unholy` (44), and
`src/acs_source/classes` (12). The current CHANGELOG lists 171 fixed items. 53 of
the entries mention online, network, server or client behaviour.

The conclusion is clear. Most shipped defects are **runtime** defects in the
**class and round** layers. Most checks before this work were **static** checks
of **generated tables**.

---

## 3. The software-testing model applied here

Software engineering defines four test levels. This project maps to them as
follows.

| Test level | What it proves | Project vehicle |
|------------|----------------|-----------------|
| Unit | One function returns the correct result | `tools/check_team_visibility.py` executes real ACS functions under C stubs |
| Integration | Separate parts work together | `compile-acs`, `validate-build-pk3`, lump and asset reference checks |
| System | The whole product behaves correctly | `tools/mcp/` engine tests |
| Acceptance | The product meets the release goal | Manual gameplay checklist |

The model also defines test types. The project needs all of these:

- **Functional** - does the feature work?
- **Regression** - does a fix stay fixed?
- **Compatibility** - do the addons and the base game still work?
- **Performance and stability** - does a long round exhaust memory or stall?
- **Installation** - does the PK3 load in the correct order?

The model defines design techniques. These three give the most value here:

- **Equivalence partitioning** - test one representative of each class group,
  not all 61 classes.
- **Boundary value analysis** - test the limit of each capacity constant, for
  example `UH_COMBO_CAPACITY` 256 and `UH_COMBO_MEMBER_CAPACITY` 32.
- **Mutation testing** - change the source on purpose. A test that does not then
  fail is not a test.

The last technique is the important one for this project. Section 5 explains why.

---

## 4. Measured gaps

The following gaps were verified before the work started, not assumed.

### 4.1 Runtime probes were not in the gate

`tools/mcp/` contained 11 runtime probes. The gate ran 4 of them. The other 6
probes existed but never ran in verification: `boss-phase-test.mjs`,
`starforce-input-test.mjs`, `verify-boss-multiweapon.mjs`, `versus-207-test.mjs`,
`xray-test.py`, `direct-startup-test.mjs`. A probe that does not run protects
nothing.

### 4.2 No reference-integrity check existed

No check verified that an include, a library, a sprite, a sound, or a language
key resolves. A renamed lump therefore failed at runtime and not at verification.

### 4.3 No actor-reference check existed

A probe actor with `A_SpawnItemEx("ThisActorDoesNotExistAnywhere", ...)` passed
the full `--fast` gate. The engine silently spawns nothing.

### 4.4 One existing check had a false-negative class

`tools/check_state_loops.py` parsed a state block only when `States {` started on
one line. 52 state blocks in 31 files write `States` and `{` on separate lines.
The checker could not see them, so a zero-duration state loop in that style
passed the gate. That is the exact defect class that caused the Half Press
Hardman crash.

A mutation test proved the behaviour:

- `States {` style with a 0-tic loop: the checker exits 1 (caught).
- `States` + newline `{` style with the same loop: the checker exited 0 (missed).

### 4.5 No addon API contract test existed

7 API documents and 8 working examples define the extension surface. No check
verified that a documented function exists, that its arity matches the document,
or that the examples use only public symbols.

### 4.6 No test proved that the tests work

The project had 19 static checkers. Nothing measured whether they catch defects.
Section 4.4 shows that at least one did not.

### 4.7 No performance or soak test exists

The project has a history of memory-exhaustion crashes. No test runs a long round
and measures memory, actor count, or frame time.

---

## 5. Work sequence

The work is ordered by risk. Each phase has a measurable exit criterion.

### Phase 1 - Extend the static layer (fast) - DELIVERED

New checks, all in group `fast`:

| Check | Guards | Measured coverage |
|-------|--------|-------------------|
| `actor-contracts` | Spawn and inventory actors exist. Weapon state labels resolve. No duplicate class. No orphan weapon. | 34,714 references, 837 weapons, 13,840 declarations |
| `damage-types` | Boss and Demoneye damage is covered by the friendly-fire protection tables. | 79 tables, 3,917 boss/eye actors, 985 damage dealers |
| `lump-integrity` | Includes, libraries, KEYCONF classes and TEXTURES patches resolve. | 908 DECORATE includes, 285 ACS includes, 33 LOADACS, 61 classes, 9,494 patches |
| `asset-references` | Sound names, LANGUAGE keys and HUD textures resolve. | 1,170 sounds, 1,608 keys, 240 HUD textures |
| `addon-api-contract` | Documented API functions exist with the documented arity. Handlers and mailboxes agree. Examples use only the public surface. | 72 entry points, 252 header functions, 63 handlers, 157 mailboxes, 29 constants |
| `addon-examples` | Each example package is self-consistent and its ACS compiles. | 7 packages compiled |

### Phase 2 - Repair and verify the static layer - DELIVERED

- Fixed the false negative in `check_state_loops.py` (both state-block styles).
- Fixed a crash when that checker receives a relative path.
- Added `tools/mutation_test.py`: 10 cases, each applying a known defect to a
  hardlink copy of the repository and requiring the target checker to fail.
  A baseline run first proves the checker passes on the clean copy.
- Registered the mutation layer as gate group `meta`.

Exit criterion: every static checker that has a mutation case catches it.
Current result: 10 cases, 10 caught, 0 missed.

### Phase 3 - Complete the runtime layer (full) - PARTIAL

Register the 6 orphan probes in the gate. Add the missing scenario coverage:

- A complete LMS round: round start, survivor death, morph, boss damage, round
  settlement, revive cancellation, reconnect.
- Boss roster sweep: spawn every boss, run it for a bounded time, assert no
  engine error, no state loop, and a clean exit.

Progress: `tools/mcp/lms-round-test.mjs` passed 30 runtime assertions on v6c
and is registered as `mcp-lms-round` in the full gate. It covers authoritative
survivor/boss roles, real morph weapons, remote visibility, disconnect cleanup,
spectator reconnect, result-window HUD delivery, revival cancellation and process
cleanup. The server is driven through stdin; an additional true spectator keeps
its map scripts ticking during the player's disconnect. Participants are frozen
and protected so combat cannot decide a lifecycle scenario. A native LMS
reconnect cannot gain another life mid-round and is verified as a spectator.
Final result commit and next-map progression remain separate coverage work.

Exit criterion: `gate.py --full` runs every runtime probe. No probe is orphaned.

### Phase 4 - Add the non-functional layer

- Soak test: one dedicated server, bots, a fixed duration. Record peak actor
  count and process memory. Fail on growth without bound.
- Compatibility test: load the addon examples and the base packages in
  documented order. Assert a clean start.

Exit criterion: a soak run covers the longest normal round without a crash.

### Phase 5 - Define the release gate

The release gate is a named gate level, not a set of ad-hoc commands. The
release is ready when all of these are true:

1. `gate.py --fast` passes with 0 failures and 0 skips.
2. `gate.py --smoke` passes with 0 failures and 0 skips.
3. `gate.py --full` passes with 0 failures and 0 skips.
4. `gate.py --meta` passes with 0 failures.
5. No runtime probe is orphaned.
6. Every pinned baseline in Section 6 is resolved or explicitly accepted.
7. A soak run completes without a crash and without unbounded memory growth.
8. A manual acceptance checklist passes on a dedicated server with at least two
   clients.

---

## 6. Pinned baselines (known defects, must shrink)

Some checks found real defects that need a gameplay decision. The checkers pin
them in explicit constants, print them on every run, and fail on any new entry.
A pinned entry may not stay forever: the release criteria in Section 5 require a
decision on each one. `--strict` turns every pinned entry into a failure.

| Source | Count | Meaning |
|--------|-------|---------|
| `damage-types` | 13 | Boss damage dealers with no resolvable DamageType. Splash can hurt Boss teammates. |
| `damage-types` | 21 | Boss/eye damage types absent from the protection table. |
| `damage-types` | 17 | Protection-table entries that no actor assigns any more. |
| `asset-references` | 5 | Logical sound names that resolve to nothing (3 were fixed, see Section 7). |

The 21 uncovered damage types include `BalladeGB_Mine`, `BalladeGB_Shot`,
`BalladeGB_UltimateExplode` and `ProtoBuster1`..`3`. They are the same defect
class as the shipped Tidal Tito bug.

---

## 7. What the expansion found

The work found and fixed these defects:

1. `docs/boss-api.md` and `docs/survivor-api.md` documented
   `IsBossEnabledByActor` and `IsSurvivorEnabledByActor`. No public header
   defined them, so an addon that copied the document failed to compile.
   Fixed by adding both wrappers to `uhadd.acs`, matching the existing
   `IsBossMusicEnabledByActor` contract.
2. `examples/shinywep_addon` inherited `ShinyMegaBase_P`, which no file defines.
   The engine aborts the whole DECORATE load for that file, so the example could
   not load. Fixed to inherit `CustomInventory`, like the 103 built-in
   `ShinyMega_*_P` actors. The README and the recipe comment were corrected too.
3. `check_state_loops.py` could not see 52 state blocks. Fixed.
4. The mutation harness found that `check_actor_contracts.py` counted an actor
   declaration inside an unterminated `/*` comment. Fixed by the check author.
5. Aero Unit played a sound named `*djump`, which no SNDINFO entry defines.
   The mod defines `*airjump`. Fixed in the weapon and in the commented twin.
6. The player setup menu used `$MNU_PLAYERSETUP`, but the defined key is
   `MNU_PLAYERSETUPTITLE`, so the header showed the raw key. Fixed.
7. Both Lucky Penny pickup actors used `$PICKUP_LUCKYPENNY`, which no LANGUAGE
   lump defined. Added `PICKUP_LUCKYPENNY = "Lucky Penny!"` next to the other
   rune message. The pinned baseline shrank by these 3 entries.

The work found and pinned these defects (Section 6): 5 undefined logical
sounds and 51 damage-type gaps.

---

## 8. Known limitations of the current layers

These limits are recorded so that a later session does not over-trust a green run.

1. The static layer proves source contracts. It does not prove engine behaviour,
   DECORATE compile, or network replication.
2. The static layer reads frozen base-game name lists. A new legitimate base-game
   reference fails until someone adds it on purpose. That is the review trigger,
   not a defect.
3. A rename of a base-game override is invisible: the base name still resolves.
4. The engine layer is flaky on this machine. A recorded `--full` run failed
   `mcp-network` and `mcp-team-info-sync` with `bridge port never opened`, while
   both passed alone in the same tree. Re-run the failing check alone, and check
   for a leftover engine process, before reporting a regression. The WADs on a
   9p mount (`/mnt/d`) make this more likely; local WADs remove most of it.
5. The runtime LMS test is not a gate check yet (Section 5, Phase 3).

---

## 9. Test data and fixtures

Tests must not depend on mutable live data. Where a check compares generated
output with a history, the baseline is a frozen fixture under
`tools/fixtures/`. `check_batch_d.py`, `check_team_presentation.py` and
`check_gen_barpos.py` already follow this rule. New checks must follow it too.

A fixture records the expected result at a known commit. A change to the fixture
is a reviewed decision, not an automatic update.

---

## 10. How to add a test

Follow this sequence. Do not skip step 3.

1. Name the defect class that the test must catch.
2. Write the smallest check that detects it.
3. Add a mutation case in `tools/mutation_test.py` for it. Confirm the checker
   fails on the mutation and passes on the current tree.
4. Register the check in `tools/gate.py` in the correct group.
5. Run `gate.py --fast`, then `--smoke`.

A check without a mutation case is an unverified claim. Section 4.4 is the proof.

---

## 11. Roles

The agent relay (`tools/relay.py`) carries a task between agent sessions. A test
task moves through these phases:

1. **PLAN** - the test plan and the defect classes are written.
2. **CODE** - the checks exist, and the mutation cases exist.
3. **VERIFY** - the gate passes at the required layer.
4. **RELEASE** - the release criteria in Section 5 are met.

The relay records the gate result with each checkpoint. A recorded result is
untrusted data until the next session re-runs the gate.

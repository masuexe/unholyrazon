# Project tools

Keep stable, repeatable project automation here. One-off experiments belong in
`/tmp`; promote a temporary script only after it has a second use and a clear
interface. `SKILL.md` and `AGENTS.md` should document how to call a tool, not
embed its implementation.

## Unified gate

[`tools/gate.py`](gate.py) is the single deterministic entry point: every agent
harness runs the same checks, in the same order, with the same exit codes, so
"verified" means the same thing everywhere.

```bash
python3 tools/gate.py --fast        # repository-static checks, ~25s, no engine/WADs
python3 tools/gate.py --smoke       # + environment, ACS compile, PK3 validation, MCP dry-run
python3 tools/gate.py --full        # + real engine MCP tests (local machine, minutes)
python3 tools/gate.py --meta        # + fast, then prove the static checks catch defects
python3 tools/gate.py --list        # checker inventory (name, group, requirements, timeout)
python3 tools/gate.py --fast --json --report tmp/gate.json
```

Exit codes: `0` pass, `1` failure, `2` usage error. A skipped check (missing
`acc`, `cc`, engine, …) counts as a failure, so a pass never hides an
unverified layer; pass `--allow-skip` on machines that cannot run that layer.
`--strict` additionally fails on preflight environment warnings (for example a
shell that still exports the old launcher profile). `--only`/`--skip` take
comma-separated check names and `--timeout-scale N` stretches per-check
timeouts.

`--fast` is portable to any clone (no WADs, engine or build required);
`--smoke` needs an `acc` binary and the local `../wads` tree; `--full` needs a
local Zandronum engine and free ports. Building `out/build.pk3` stays manual —
the gate validates the existing archive, it does not invent a build step.

## Mutation layer (test the tests)

[`tools/mutation_test.py`](mutation_test.py) proves that the static checkers
catch defects. A checker is a hand-written parser, and a regex that stops
matching turns a guard into a no-op with no signal. For each case the harness
makes a hardlink copy of the repository, confirms the checker passes on the
clean copy, injects one known defect, and requires a non-zero exit.

```bash
python3 tools/mutation_test.py              # every case, ~33s
python3 tools/mutation_test.py --list       # case inventory
python3 tools/mutation_test.py --case NAME  # one case
```

Exit codes: `0` every case caught, `1` a case was missed, `2` usage error.
The cases are data in one list at the bottom of the file. Add a case whenever
a new checker lands: a checker without a mutation case is an unverified claim.
The harness already found a real blind spot in `check_state_loops.py`: 52 state
blocks written as `States` followed by a newline brace were invisible.

The engine checks go through the MCP launcher, which waits 42s for the engine to
open its bridge port. On WSL, keeping the base WADs on `/mnt/d` (a 9p mount) can
push engine startup past that limit and look like a bridge failure; point
`ZANDRONUM_LAUNCH_PROFILES` at a profile whose `iwad`/`files` live on a local
filesystem (or copy the WADs off the Windows drive) before blaming the gate.

A recorded run of `--full` on 2026-10-26 failed two engine checks back to back
with `bridge port 127.0.0.1:7777 never opened` (`mcp-network`, then
`mcp-team-info-sync`), while `mcp-smoke` and `mcp-team-presentation` passed in
the same run. Both failed checks passed when run alone on the same tree
(`--full --only mcp-network`: pass, 121s; `--full --only mcp-team-info-sync`:
pass, 118s). Treat that as environment flakiness, not a regression: re-run the
failing check alone before you report a failure, and check for a leftover
`zandronum` or `server-runner` process first.

[`tools/check_agent_config.py`](check_agent_config.py) (part of `--fast`) fails
when the machine-local harness configs diverge on the launcher profile, engine
path or MCP server list (`.mcp.json`, `.agents/mcp_config.json`,
`.dsh/cordis.patch.yml`, `~/.bashrc`, `~/.profile`). A running shell or harness
keeps its old environment after a config fix, so the stale ambient
`ZANDRONUM_LAUNCH_PROFILES` is reported as a warning until the process restarts;
absent machine-local files are skipped, so a fresh clone passes.

## X-Ray network regression

Focused online X-Ray regression:

```bash
python3 tools/mcp/xray-test.py
```

Uses the tracked smoke profile with one dedicated server and one remote client
through the engine bridge. A temporary diagnostic addon freezes two players and
places the target at a known distance. Checks actual projected name/distance
messages, automatic renderer recovery, one renderer after repeated startup
delivery, cvar and live-count conditions, the independent event source, and
reconnecting to an ongoing map. Requires ACC, `ZANDRONUM_EXE`, and local sockets;
logs and results go to `out/xray-test/`. It never starts the renderer directly.

## Agent relay

[`tools/relay.py`](relay.py) carries the task handoff between harnesses; the
protocol is in [docs/agent-relay.md](../docs/agent-relay.md) and the bootstrap
is in `AGENTS.md` (`CLAUDE.md` imports it for Claude Code).

```bash
python3 tools/relay.py resume                     # default command
python3 tools/relay.py init --title "..." --acceptance "..." --scope "src/...,tools/..."
python3 tools/relay.py verify --gate smoke
python3 tools/relay.py checkpoint --phase CODE --summary "..." --next "..." [--gate fast|smoke|full|none]
python3 tools/relay.py status
python3 tools/relay.py clear                      # archive to .agents/relay/archive/
```

State lives in `.agents/relay/` (gitignored): `current_task.json`,
`handoff.json`, generated `handoff.md`, the last `test_report.json` and an
`archive/` directory. `checkpoint` runs the fast gate by default and returns
non-zero if it fails, but still records the state so the next agent sees the
failure; `--gate none` skips verification and is discouraged. `resume` warns
when HEAD, the working-tree fingerprint or the recorded gate result is stale.

## MCP smoke test

The Linux Zandronum MCP wrapper runs the smallest useful feedback loop:

```bash
./tools/mcp/smoke-test.sh
./tools/mcp/smoke-test.sh --profile mm8bdm-v6b-full --json
./tools/mcp/smoke-test.sh --dry-run
```

It validates the selected launch profile, starts one MCP instance, collects a
compact startup summary and `player_state`, then asks MCP to quit the instance.
The default profile is `mm8bdm-v6b-smoke`. Full engine output remains in the
MCP engine log; the wrapper deliberately keeps stdout short. Override the
Linux paths with `ZANDRONUM_NODE`, `ZANDRONUM_MCP_DIR`, `ZANDRONUM_MCP_SERVER`,
`ZANDRONUM_EXE`, `ZANDRONUM_LAUNCH_PROFILES`, or `ZANDRONUM_BRIDGE_PORT`.

Use direct MCP calls when the next decision depends on live actor state or a
specific log line; use this wrapper for a deterministic regression check.

For a local authoritative network smoke test:

```bash
node tools/mcp/network-test.mjs --json
node tools/mcp/network-test.mjs --dry-run
```

It launches one dedicated server, one MCP-controlled client, and one directly
observed client over loopback. The clients authenticate serially; both names
must appear in the authoritative server log and both clients must complete
level authentication and snapshot receipt. Temporary isolated engine folders
prevent shared runtime/config files and are removed during cleanup. It requires
permission to open local TCP/UDP ports.

For the team-info CLIENTSIDE sync delivery regression:

```bash
node tools/mcp/team-info-sync-test.mjs --json
node tools/mcp/team-info-sync-test.mjs --dry-run
node tools/mcp/team-info-sync-test.mjs --stress --json
```

It launches one listen server plus one MCP-controlled remote client, then
verifies every team-info CLIENTSIDE receiver end-to-end:

- **spectator hello + roles** — a client that connects but has not run `join`
  still receives the full snapshot: a valid `uhtiscorepolicy` and the in-game
  bots' `uhtirole[]` (the round role gather is forced, because a bot that joins
  mid-round is not assigned a role). `uhtiova` / `uhtiovatarget` are perturbed
  to a sentinel first, so the re-delivered `0` / `-1` is a real assertion
  rather than a default-value match.
- **spectator stats + clear** — a true spectator receives `uh_ti_stat` for an
  in-game bot; `removebot` then produces `uh_ti_stat_clear`, and the test
  asserts the removed slot clears while the other bot's slot stays set, so a
  map reset cannot masquerade as a clear.
- **join snapshot** — after `join` the client spawns and its
  `uhtirole[]` / `uhtilife[]` / `uhtiscorepolicy` are populated.

The gate requires every receiver to be proven **over the network**
(`statDelivery` + `networkClear` are part of the pass condition). A direct
local `run_script` round-trip is recorded as a diagnostic only and must never
substitute for network delivery, so a broken sender cannot let the gate pass.

`--stress` adds bots to fill 33 and 64 connected slots, measures the server's
`uh_ti_serverwatch` with cold identity caches and all-client snapshots, and
requires its maximum execution to stay below the normal 2,000,000-instruction
guard. It also checks that queued snapshots drain, then repeats at 64 slots
after a map reload and spectator reconnect, and verifies remote delivery for
slot 63. Bots exercise server slot/delivery loops; this is not a 64-human
network bandwidth test.

This is the runtime gate for the P1 per-client delivery fix
(`ACS_NamedExecuteAlways` to a CLIENTSIDE receiver does not reach a remote
client); static compilation cannot prove a receiver was reached over the
network.

For the team-presentation resolver migration:

```bash
node tools/mcp/team-presentation-test.mjs --json
node tools/mcp/team-presentation-test.mjs --dry-run
node tools/mcp/team-presentation-test.mjs --profile mm8bdm-v6b-teampres-addon --addon --json
```

It launches one dedicated `-lastmanstanding` server plus one MCP-controlled
remote client and verifies the migration on the **client** VM, which is where the
HUD resolves from:

- **table built** — `rz_debug_TeamPresentationCheck` reports 0 failures and a
  non-zero row count, so `DefineTeamPresentation` actually populated UHDT at map
  load (the `OPEN` + `OPEN CLIENTSIDE` twin pair both ran).
- **resolver output** — the check logs each live player's class → name /
  portrait / scoreIcon, and the gate compares them against the generated
  presentation fragments (`tools/check_team_presentation.py` proves those match
  the former hardcoded tables). `scoreIcon` covers the LuckyLass `UMUG_6_`
  override.
- **identity sync** — the status broadcast carries a `(UH_PLDEF_* kind, vanilla
  definition id)` pair of plain integers. `uh_ti_TeamInfoCacheDump` logs what the
  client cached per slot; a class the peer does not know (`known=0`) must resolve
  to an empty portrait *and* an empty icon. Where `uhtirole[]` is also known, the
  cached class must be a definition of *that* side — a Boss slot caching a
  survivor class means the pair was misinterpreted.
- **controlled transfer** — the cache dump alone cannot prove the transfer,
  because the client also fills that cache from the live actor. The probe
  therefore drives `uh_ti_sync_status` directly for a slot with no live actor and
  reads back what the client derived from its own tables: a vanilla boss id must
  resolve to that boss, an undefined slot must resolve to nothing, and a negative
  (custom, load-order-dependent) id must be rejected rather than misresolved.
- **receiver round-trip** — a known packed identity pushed through
  `uh_ti_sync_status` is stored, and `PLS_NULL` clears both the role and the
  identity.
- **dead-row retention** — the `PLS_DEAD` transition keeps the retained role and
  the identity (that is the dead/body-less fallback), and clearing one slot
  leaves every other slot's identity untouched.

`--addon` additionally requires the `mm8bdm-v6b-teampres-addon` profile and
asserts the example addon's own class resolves to its registered short name and
textures — i.e. a new class needs no edit to any Unholy source file. Pack
`examples/teampresentation_addon` into `out/teampresentation_addon.pk3` first.

This is the runtime gate for the actor-keyed team-presentation migration
(`DefineTeamPresentation` in `uhadd.acs`); static compilation
cannot prove the table was populated on a client, nor that the identity
broadcast stopped being a load-order-dependent row index.

For boss stage portraits:

```bash
node tools/mcp/boss-phase-test.mjs --json
```

This focused smoke-profile gate checks TimemanC/KFC stage changes at constant
health through a dedicated server and remote client, independent boss rows,
reset, and a real spectator reconnect snapshot. Additional controlled receiver
checks cover death retention, slot reuse, clear, and reverse script order.
See [Boss stage portraits](../docs/boss-phase-portraits.md) for the registration
API and manual diagnostics.

For the boss-versus combo directed probe:

```bash
node tools/mcp/versus-207-test.mjs --json
node tools/mcp/versus-207-test.mjs --dry-run
node tools/mcp/versus-207-test.mjs --combo 210 --expect "DicksterDick,PricksterPrick" --json
node tools/mcp/versus-207-test.mjs --combo 206 --forced1 66 --forced2 67 --expect "SuperMegaman,Lin" --json
node tools/mcp/versus-207-test.mjs --combo 209 --expect any --json
```

It launches a dedicated `-lastmanstanding` server plus two clients, adds four
bots so the versus combo meets its four-player minimum, forces
`uh_sv_bosseventnum <combo>`, and verifies on the live client that the two
expected bosses spawn without `PowerProtectBoss` and that the round resolves.
`--combo`/`--expect` default to 207 (Red Baron / Blue Jay); `--expect any`
accepts the two random bosses of combo 209; `--forced1`/`--forced2` supply the
`uh_sv_forcedboss1/2` pair for combo 206; `--resolve-wait` raises the
post-inspection window for long high-HP duels. It does not drive real
projectiles; that remains the manual gameplay gate.
## PK3 validation

Before launching after a packaging change, run the read-only archive check:

```bash
./tools/validate-build-pk3.sh
./tools/validate-build-pk3.sh --json
```

It checks ZIP integrity and the required `DECORATE`, `KEYCONF`, `LOADACS`,
`acs/CORE8BDT.o`, and `acs/UHCOMBDB.o` lumps. It does not build or rewrite the PK3, and it cannot
replace engine-level DECORATE/ACS diagnostics.

## Diagnostic log levels

`UH_Log` uses only the existing verbosity thresholds: `0=OFF`, `1=ERROR`,
`2=+WARN`, `3=+INFO` (default), `4=+DEBUG`. There is no separate debug toggle.
Use `set uh_cl_LogLevel 4` for player/locally hosted diagnostics, or
`set uh_sv_loglevel 4` for dedicated-server calls without a player context.
Player-context calls still use that player's `uh_cl_LogLevel` on the server.
Deferred round-start registry diagnostics run only when the applicable threshold
includes DEBUG. The full launch profiles and versus test enable level 4.

## Rebuilding ACS and the PK3 locally

Ordinary-round settlement can be made cancellable with
`uh_sv_resumeonrevive true` (default `true`). Native LMS wins remain final.
See [Cancellable round settlement](../docs/round-settlement.md) for scope,
option timing and manual checks. Run `python3 tools/check_round_settlement.py`
for the actual ACS logic under C stubs; recompile `unholy` and `rz_debug`.
`uh_sv_postroundfriendlyfire` (default `true`) controls team damage during
pending/final results for every round type, including Bonus Events. The same
logic check covers immunity removal/restoration, option changes and body changes.

Boss win-rate debug counters are documented in
[Boss win-rate statistics](../docs/boss-stats.md). Run
`python3 tools/check_boss_stats.py` for the accounting/reset logic and command
wiring checks under C stubs.

Bonus Event host overrides use the import-only `UHBESET` library
(`src/acs/UHBESET.o`, absent from `LOADACS`). `tools/compile-acs.sh` compiles it
before UHDT. The console commands and configuration format are documented in
[Bonus Event settings](../docs/bonus-event-settings.md). Run
`python3 tools/check_bonus_event_settings.py` for the parser, command queue,
override, persistence, addon identity and reset regression checks. This check
uses GCC to run the integer/string-only ACS functions with test stubs;
it does not replace ACC compilation or an engine test.

ACS edits only take effect once the affected library is recompiled with the
native Linux ACC into `src/acs/` and the PK3 is repackaged. Pick the aggregator
that includes the file you edited — `src/LOADACS` lists every library, and each
aggregator has the matching `#library` name.

The optional [PingButton override](../src/acs_source/compat/mods/pingbutton/README.md)
is compiled by `tools/compile-acs.sh` to `src/acs/PNGBUTTN.o`. Load
`trill-pingbutton-v5h` before Unholy. Its own LOADACS activates the shadow;
Unholy's LOADACS must not list it. In Unholy LMS all pings are public, including
locate results; personal display/mute settings still apply.

For example:

```bash
ACC=${ACC:-acc}
INC="-i ../references/zandronum/acc-branch-zandronum
  -i src/acs_source/v6b_overrides/_includes/mod_api
  -i src/acs_source/v6b_overrides/_includes/common
  -i src/acs_source/_includes/mod_api
  -i src/acs_source/_imports
  -i src/acs_source/hud"

# src/acs_source/classes/**  -> uh_classes.o   (weapons, class logic, rnc_clashman.acs)
$ACC $INC src/acs_source/classes/uh_classes.acs src/acs/uh_classes.o

# src/acs_source/unholy/**   -> unholy.o       (round flow, boss select, uh_bossselect.acs)
$ACC $INC src/acs_source/unholy/unholy.acs src/acs/unholy.o

# Shared boss-combo registry (import-only; keep LOADACS unchanged).
$ACC $INC src/acs_source/_imports/uhcombodb.acs src/acs/UHCOMBDB.o
```

Boss-combo data is registered from `unholy/uh_combo_definitions.acs` into
`UHCOMBDB`; recompile the registry, `unholy`, `uhaddr`, and `rz_debug` after
changing its API/storage. `rz_debug` also needs `-i src/acs_source/unholy`.
Public registration helpers live in `_includes/mod_api/uhcombo_api.acs`, included
by `uhadd.acs`; changes there require recompiling the eight UHADD definition
libraries. The addon recipe is at the top of that API file. Combo definitions
run on the server only; no `OPEN CLIENTSIDE` twin is needed.

Registration parameters, addon examples, member ordering, music fallback and
Shadow Duel behavior are documented in [Boss Combo API](../docs/boss-combo-api.md).

`python3 tools/check_batch_d.py --source-only` checks the combo migration against
`tools/fixtures/boss_combos_v1.json`, including ordered duplicate members and
all music credits, without requiring the external music archive. The normal
command also checks audio resources; the baseline is frozen migration evidence,
so do not regenerate it to silence a failed comparison.

Compiling the wrong aggregator silently leaves the old object in `src/acs/`, so
the change simply does not happen in game (it cost a debugging round on
2026-09-12). `src/acs_source/hud/**` builds `uh_bars.o` from
`src/acs_source/hud/uh_bars.acs` the same way.

The modified `v6b_overrides/_imports/8BDT.acs` declares `#library "CORE8BDT"`.
Compile it to **`src/acs/CORE8BDT.o`**, never `src/acs/8BDT.o`:

```bash
$ACC $INC src/acs_source/v6b_overrides/_imports/8BDT.acs src/acs/CORE8BDT.o
```

Remove any stale `src/acs/8BDT.o` before packaging. ACS imports resolve by lump
name, so the wrong filename silently leaves the base game's `CORE8BDT.o` in
use. It lacks UH's `getPitCount`, causing `uh_ApplyPitDamage` to execute invalid
bytecode and raise an ACS VM bounds error during map startup or client join.

Package `src/` as a fresh archive (never update an existing ZIP in place), then
validate. The file-list form below excludes what `src/.pk3ignore` excludes and
adds no directory entries, so the entry list comes out identical to the previous
`out/build.pk3` (16563 entries as of 2026-09-12):

```bash
cd src && find . -type f ! -path "./acs_source/*" ! -name "*.err" ! -name ".*" \
  | sed 's|^\./||' > /tmp/pk3files.txt
rm -f /tmp/build.pk3 && zip -X -9 -q /tmp/build.pk3 -@ < /tmp/pk3files.txt
cp /tmp/build.pk3 ../out/build.pk3 && cd .. && ./tools/validate-build-pk3.sh
```

## Build/test loop traps

Three of these cost a debugging round each; check them before blaming the mod:

- **Never repackage `out/build.pk3` while an MCP instance is running.** The
  engine reads the ZIP lazily, so replacing it under a live instance floods the
  log with `Corrupt zlib stream` and `Missing string (unexpected end of file)`.
  Kill the instance, repackage, then relaunch.
- **ACS libraries load only at engine startup.** Editing anything under
  `src/acs_source/` does nothing until the library is recompiled *and* the
  instance is restarted; `load_map` does not reload libraries. DECORATE is
  reread from the PK3 on a map load, so actor edits only need `load_map`.
- **`launch_instance`'s `extraArgs` replaces the profile's `extraArgs`**, it does
  not append (`zandronum-mcp/src/tools.ts`). Passing `["-host"]` silently drops
  the profile's `-nosound`, `vid_renderer 0` and `sv_cheats 1`, after which
  bridge console commands (`currentpos`, `give`) time out. Repeat the profile
  args you still need. `-host` (listen server) also answers console commands
  poorly through the bridge, so keep multiplayer checks for the dedicated-server
  scripts above.

## Existing validators and generators

- `gen_item_automap.py` — generate centered icons and marker actors for Unholy
  pickups; `--check` also verifies every registered item and Spawn startup hook.
  See [Unholy pickup automap](../docs/automap-items.md) for scope and addon usage.
- `validate-build-pk3.sh` — read-only PK3 integrity and entry-point check.
- `check_boss_defs.py` — verify `DefineBoss` actor names against `src/actors`.
- `gen_team_presentation.py` — regenerate the built-in `DefineTeamPresentation`
  rows from the definition tables plus the former hardcoded portrait/score-icon
  tables. `--check` verifies the three checked-in fragments without writing and
  exits 1 on drift. Run after adding a survivor / boss / demoneye.
- `check_team_presentation.py` — prove the generated fragments still match the
  former hardcoded output (short name, portrait, scoreboard icon) and that the
  UIX `PBMug_*` scripts still agree. This is the static half of the
  team-presentation migration gate; `tools/mcp/team-presentation-test.mjs` is
  the runtime half.
- `gen_shiny_moves.py` — regenerate the checked-in Shiny DECORATE fragment.
- `gen_decoy_moves.py` — generate all 61 DecoyBot W1/W2/W3 copy actors from
  `tools/decoy_copy_moves_source.dec` into the checked-in
  `src/actors/classes/survivors/decoy_copy_moves.dec`. Edit the W1 actors in
  the source file; W2/W3 are derived by sprite-prefix, parent and tag remaps.
  Slots 27 and 52 have explicit W2/W3 overrides for their differing behavior.
  `python3 tools/gen_decoy_moves.py --check` detects stale output without
  writing. Format the source with the project's DECORATE editor settings; the
  generator preserves that formatting in W1/W2/W3. This generator no longer
  rewrites `DecoyBot_W.dec`.
- `_gen_barpos.py` — compiler CLI to regenerate `SBARINFO.h.uhappend` /
  `SBARINFO.v.uhappend` (AppendStatusBar), DECORATE selector/ammo actors in
  `UH_BarFX.dec`, and generated ACS from `tools/bars.toml`. Detailed architectural
  guide in [docs/custom-bars.md](../docs/custom-bars.md).
  - Flags: `-c/--config <FILE>` (default: `tools/bars.toml`), `-o/--output-dir <DIR>` (default: `src`),
    `--emit <TYPE[=PATH],...>` (repeatable; types: `sbar-h`, `sbar-v`, `decorate`, `acs`; `PATH=-` for stdout),
    `--source-dir <DIR>` (graphic validation input, default: repository `src`),
    `--barfx-template <FILE>` (DECORATE input, default: `UH_BarFX.dec` under the source directory),
    `--check` (verify without writing; exit 1 on drift), `-v/--verbose` (diagnostic logging),
    `-q/--quiet` (suppress non-error output).
  - `-o out/bars` exports to an empty directory. Explicit emit paths are relative to the working directory;
    progress goes to stderr. For another source tree, pass both `--source-dir other/src -o other/src`.
  - Run `python3 tools/_gen_barpos.py --check` in CI or after modifying bar graphics/definitions.
- `bars.toml` is the schema-versioned hand-authored input for namespaced bars.
  `python3 tools/_gen_barpos.py --check` verifies its checked-in numeric ACS
  helper, namespaced selector/ammo actors in `UH_BarFX.dec`, and sparse-priority
  AppendStatusBar output. The two `.uhappend` files use the same spacing and
  indentation as their corresponding `SBARINFO.*._core` files; edit `bars.toml`
  or the generator, never format them by hand. The base game's `BarFX.txt` must
  not be overridden.
  Each `[[groups]]` entry declares one namespace and contains one or more
  `[[groups.bars]]` entries. All namespaces share the single generated
  `UHBar_ClearAll` callback (one `core_DrawBar_RegisterClear` slot for the
  whole addon); selector IDs are dense within each namespace/position/
  priority bank. Use a separate group for an independently named class form.
  `constant_name` is the complete public ACS constant and must begin with
  `UHBAR_`; the generator enforces ACC's 31-character identifier limit and
  case-insensitive uniqueness.
- `test_gen_barpos.py` — deterministic generator validation fixtures. Run with
  `python3 tools/test_gen_barpos.py` after changing the TOML schema or generator.
  `UHBar_ClearAll_Register` registers the
  shared clear callback from `OPEN CLIENTSIDE` through
  `core_DrawBar_RegisterClear` and logs the return value on failure; duplicate
  names return the existing row, `-1` is empty, `-2` is registry-full, and
  `-3` is a missing named script.

Scripts should accept paths or environment overrides where practical, return a
non-zero exit code on failure, and print a concise summary. Do not commit MCP
logs, generated build output, or Python bytecode.

## Clownpiece phase timing

Boss Setup exposes `uh_sv_clownpiece_autotime` (default true),
`uh_sv_clownpiece_w2_time` and `uh_sv_clownpiece_w8_time` (default 30 seconds,
runtime clamp 1–300). W2/W8 remain invulnerable survival spells. Other active
phases keep a 30-second base; disabled phases W3/W5 do not count toward budgets.

At each phase entry, automatic timing shares the normal round timer's actual
remaining time between the remaining phases, weighted by their base durations.
It reserves 10 seconds for the ending plus 2 seconds per future phase switch.
The selected duration stays fixed for that phase and never exceeds its base.
Early damage clears leave more time for later phases. Changes to settings apply
on the next phase entry. Disabling automatic timing or the normal round timer
uses base durations; versus/replacement event flows clear the normal deadline.

During W2/W8, survivor attacks cancel HP damage and add timer credit. Damage
is measured after damage-type/PowerProtection/team modifiers and before armor
absorption, so armor is not consumed. One starting phase HP budget removes half
of the adapted initial duration, capped at that half; small hits accumulate.
Environment, boss/teammate, telefrag and instant-death hits give no credit.
The shared Clownpiece session pools hits across simultaneous Clownpieces against
the starting boss's HP budget. HUD `ATTACK TIME -Xs` reports accumulated credit;
server updates are throttled to five per second. W2/W8 reset credit separately,
and accelerated timeout keeps the normal no-survivor-deaths capture condition.
Native transition invulnerability is popped on entry: the server damage EVENT
provides survival protection, because native invulnerability skips that EVENT.
Other invulnerability layers can still block damage credit until they expire.

The minimum is one second per phase: an extremely late morph or unusually long
health refill cannot be guaranteed to finish before round timeout. For 130
seconds actually remaining at W1 entry, the initial budget is 110 seconds and
W1 receives 18 seconds (the game timer itself also includes its existing
10-second startup allowance). This adaptation does not change damage, health,
capture rewards or round timeout behavior. Phase transitions retain protection
while healing and switching weapons, then release it immediately; the former
extra three seconds of post-transition invulnerability have been removed.

## Batch D acceptance

Run the repeatable Batch D gates from one entry point:

```bash
./tools/batch-d-acceptance.sh quick
./tools/batch-d-acceptance.sh runtime
./tools/batch-d-acceptance.sh full
```

`quick` checks the two currently disputed definition requirements, the external
music archive, boss actor registration, and the existing packaged mod. `runtime`
runs a short direct-engine startup and then attempts the MCP smoke test; an MCP
transport failure is reported as infrastructure rather than hiding the direct
startup result. `full` runs the quick checks followed by a 30-second full-profile
startup with both external music packages and optional debugging addons.

The scripts deliberately leave multiplayer gameplay as an explicit manual gate:
one server plus two clients, forced event/combo paths, disconnect/reconnect,
two-round cleanup, player-count soak, and live HUD aspect-ratio inspection cannot
be proved by a startup-only process.

- `check_batch_d.py` accepts `--music-pk3 PATH`, `--source-only`, and `--json`.
- `direct-startup-test.mjs` accepts `--profile`, `--duration-sec`, `--dry-run`,
  and `--json`; paths may be overridden with the same engine/profile environment
  variables as the MCP smoke script.

## Star Force scroll inputs

`node tools/mcp/starforce-input-test.mjs [--pk3 PATH]` checks the actual boss's
scroll direction isolation, automatic return, held Reload/release, cooldown gating and six-card hand
through the local smoke profile. It uses the same MCP environment settings as
`smoke-test.sh`. See [Star Force controls](../docs/class-mechanics.md#2-star-force-mega-man-controls--battle-cards) for the
single-slot requirement and the remaining multiplayer gameplay checks.

## Environment & External References

See [REFERENCES.md](REFERENCES.md) for full catalog and download links.

- **Check environment health**:
  ```bash
  python3 tools/check_environment.py
  python3 tools/check_environment.py --json
  ```
  Validates compiler (`acc`), test assets (`megagame.wad`, `mm8bdm-v6b.pk3`), and reference sources.
- **Unpack references from PK3 archives**:
  ```bash
  python3 tools/unpack_references.py
  python3 tools/unpack_references.py --include-legacy # Also extract legacy Unholy reference packages
  python3 tools/unpack_references.py --all            # Extract sprites/audio as well
  ```
  Extracts code-only definition lumps (`.dec`, `.txt`, `.acs`) from `.pk3` files in `../wads` into `../references/` for fast inspection.
- **Local machine path overrides**:
  Copy `tools/paths.json.example` to `tools/paths.local.json` to customize paths without modifying git-tracked files.


### CXAirMan remote ammo regression

`node tools/mcp/boss-ammo-test.mjs --probe /tmp/ammoprobe.pk3 --json`
starts one dedicated server and one remote client. It checks an ultimate cast
with a deliberately one-point-stale client meter, an insufficient-energy
attack, refill and normal casting, and teleport energy consumption/recovery.
The probe is diagnostic only; never include it in the released mod.

Build the probe with native ACC (adjust the compiler include directory to your
reference configuration):

```bash
acc -i ../references/zandronum/acc-branch-zandronum tools/mcp/fixtures/boss-ammo-probe.acs /tmp/AMMOPROB.o
python3 - <<'PY'
import zipfile
with zipfile.ZipFile('/tmp/ammoprobe.pk3', 'w') as archive:
    archive.write('/tmp/AMMOPROB.o', 'acs/AMMOPROB.o')
    archive.writestr('LOADACS', 'AMMOPROB\n')
PY
```

The original weapon-state drain left the remote meter at 1499 while the server
spent its 1500 energy. The fixed drain sends the server's remaining amount;
both meters reach zero. This isolates a synchronization failure, rather than
assuming a naturally occurring lag condition will reproduce on localhost.


### v6c weapon death regression

Build the diagnostic addon from `tools/mcp/fixtures/weapon-death/`:

```bash
acc -i ../references/zandronum/acc-branch-zandronum tools/mcp/fixtures/weapon-death/probe.acs /tmp/WDTHPROB.o
python3 - <<'PYPROBE'
import zipfile
with zipfile.ZipFile('/tmp/weapon-death-probe.pk3', 'w') as archive:
    archive.write('tools/mcp/fixtures/weapon-death/LOADACS', 'LOADACS')
    archive.write('/tmp/WDTHPROB.o', 'acs/WDTHPROB.o')
PYPROBE
ZANDRONUM_LAUNCH_PROFILES=tools/mm8bdm-v6c.launch.json node tools/mcp/weapon-death-test.mjs --probe /tmp/weapon-death-probe.pk3
```

Adjust the ACC include path for your local compiler sources. The test uses one
isolated client on TRAINING. It exercises Igniter, Juggernaut, and Magic
Specialist's separate cleanup override. A lethal JuggerShot hit must return, leave the player
dead, and keep the engine responsive. This specifically catches inherited state
offset changes that a source-only state-loop check cannot resolve. Keep the
probe addon out of release packages. Dedicated-server behavior is a separate
regression requirement.

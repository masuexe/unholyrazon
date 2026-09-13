# Project tools

Keep stable, repeatable project automation here. One-off experiments belong in
`/tmp`; promote a temporary script only after it has a second use and a clear
interface. `SKILL.md` and `AGENTS.md` should document how to call a tool, not
embed its implementation.

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
`uh_sv_BossEventNum <combo>`, and verifies on the live client that the two
expected bosses spawn without `PowerProtectBoss` and that the round resolves.
`--combo`/`--expect` default to 207 (Red Baron / Blue Jay); `--expect any`
accepts the two random bosses of combo 209; `--forced1`/`--forced2` supply the
`uh_sv_ForcedBoss1/2` pair for combo 206; `--resolve-wait` raises the
post-inspection window for long high-HP duels. It does not drive real
projectiles; that remains the manual gameplay gate.

## PK3 validation

Before launching after a packaging change, run the read-only archive check:

```bash
./tools/validate-build-pk3.sh
./tools/validate-build-pk3.sh --json
```

It checks ZIP integrity and the required `DECORATE`, `KEYCONF`, and `LOADACS`
lumps. It does not build or rewrite the PK3, and it cannot replace engine-level
DECORATE/ACS diagnostics.

## Rebuilding ACS and the PK3 locally

ACS edits only take effect once the affected library is recompiled with the
native Linux ACC into `src/acs/` and the PK3 is repackaged:

```bash
${ACC:-acc} \
  -i ../references/zandronum/acc-branch-zandronum \
  -i src/acs_source/v6b_overrides/_includes/mod_api \
  -i src/acs_source/v6b_overrides/_includes/common \
  -i src/acs_source/_includes/mod_api \
  -i src/acs_source/_imports \
  -i src/acs_source/hud \
  src/acs_source/classes/uh_classes.acs src/acs/uh_classes.o
```

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

- `validate-build-pk3.sh` — read-only PK3 integrity and entry-point check.
- `check_boss_defs.py` — verify `DefineBoss` actor names against `src/actors`.
- `gen_shiny_moves.py` / `gen_decoy_moves.py` — regenerate checked-in DECORATE
  fragments from their source actors.
- `_gen_barpos.py` — regenerate `uh_barcat.acs`, `SBARINFO.h.uhappend` /
  `SBARINFO.v.uhappend` (AppendStatusBar), and the BarFX layer-pool actors
  from unmigrated `DrawCustomBarString*` calls and TOML entries marked for
  compatibility in `src/acs_source`. Renames
  leftover `BRSLT` wrappers in `TEXTURES.bars` / `ANIMDEFS.bars` to
  `UHVT`/`UHHT` and strips the legacy layer banks from `SBARINFO.*._core`.
  `--check` verifies all generated outputs (and stale-file absence) without
  writing; exits 1 on drift. Run after adding String-bar graphics.
- `bars.toml` is the schema-versioned hand-authored input for namespaced bars.
  `python3 tools/_gen_barpos.py --check` verifies its checked-in numeric ACS
  helper, namespaced selector/ammo actors in `UH_BarFX.dec`, and sparse-priority
  AppendStatusBar output. The base game's `BarFX.txt` must not be overridden.
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
  Set `legacy_catalog = true` only when a migrated string-API pair must
  remain in the compatibility catalog. `UHBar_ClearAll_Register` registers the
  shared clear callback from `OPEN CLIENTSIDE` through
  `core_DrawBar_RegisterClear` and logs the return value on failure; duplicate
  names return the existing row, `-1` is empty, `-2` is registry-full, and
  `-3` is a missing named script.

Scripts should accept paths or environment overrides where practical, return a
non-zero exit code on failure, and print a concise summary. Do not commit MCP
logs, generated build output, or Python bytecode.

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

- `check_batch_d.py` accepts `--music-pk3 PATH` and `--json`.
- `direct-startup-test.mjs` accepts `--profile`, `--duration-sec`, `--dry-run`,
  and `--json`; paths may be overridden with the same engine/profile environment
  variables as the MCP smoke script.

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

## PK3 validation

Before launching after a packaging change, run the read-only archive check:

```bash
./tools/validate-build-pk3.sh
./tools/validate-build-pk3.sh --json
```

It checks ZIP integrity and the required `DECORATE`, `KEYCONF`, and `LOADACS`
lumps. It does not build or rewrite the PK3, and it cannot replace engine-level
DECORATE/ACS diagnostics.

## Existing validators and generators

- `validate-build-pk3.sh` — read-only PK3 integrity and entry-point check.
- `check_boss_defs.py` — verify `DefineBoss` actor names against `src/actors`.
- `gen_shiny_moves.py` / `gen_decoy_moves.py` — regenerate checked-in DECORATE
  fragments from their source actors.
- `_gen_barpos.py` — regenerate `uh_barcat.acs`, `SBARINFO.h.uhappend` /
  `SBARINFO.v.uhappend` (AppendStatusBar), and the BarFX layer-pool actors
  from the `DrawCustomBarString*` calls found in `src/acs_source`. Renames
  leftover `BRSLT` wrappers in `TEXTURES.bars` / `ANIMDEFS.bars` to
  `UHVT`/`UHHT` and strips the legacy layer banks from `SBARINFO.*._core`.
  `--check` verifies all generated outputs (and stale-file absence) without
  writing; exits 1 on drift. Run after adding String-bar graphics.
- `bars.toml` is the schema-versioned hand-authored input for namespaced bars.
  `python3 tools/_gen_barpos.py --check` verifies its checked-in numeric ACS
  helper, namespaced selector/ammo actors in `UH_BarFX.dec`, and sparse-priority
  AppendStatusBar output. The base game's `BarFX.txt` must not be overridden.
  Set `legacy_catalog = true` only when a migrated string-API pair must
  remain in the compatibility catalog. Clear callbacks register from
  `OPEN CLIENTSIDE` through `core_DrawBar_RegisterClear`; duplicate names
  return the existing row, `-1` is empty, `-2` is registry-full, and `-3` is a
  missing named script.

Scripts should accept paths or environment overrides where practical, return a
non-zero exit code on failure, and print a concise summary. Do not commit MCP
logs, generated build output, or Python bytecode.

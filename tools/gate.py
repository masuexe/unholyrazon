#!/usr/bin/env python3
"""Deterministic test gate for Unholy Razon.

One entry point for every harness: the same checks, the same order, the same
JSON schema and the same exit codes, so "verified" means the same thing from a
Python shell, dsh, Claude Code, Codex or Antigravity.

Layers (cumulative):

  --fast    repository-static checks only: no engine, no WADs, no build.   ~6s
  --smoke   + environment, ACS compile, PK3 validation, MCP dry-run.       ~7s
  --full    + real engine MCP tests (slow, local machine only, minutes).

Builds stay manual (see AGENTS.md): out/build.pk3 is produced by hand, and
--smoke validates the existing archive instead of inventing a build step.

Usage:
  python3 tools/gate.py --fast
  python3 tools/gate.py --smoke --json --report tmp/gate.json
  python3 tools/gate.py --full --only mcp-smoke
  python3 tools/gate.py --list

Exit codes: 0 pass, 1 failure, 2 usage error.  --strict additionally fails on
skipped checks (missing toolchain) and preflight environment warnings.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PY = sys.executable
SCHEMA = 1
GROUPS = ("fast", "smoke", "full")
GROUP_ORDER = {"fast": ("fast",), "smoke": ("fast", "smoke"), "full": ("fast", "smoke", "full")}
CANONICAL_PROFILE = REPO / "tools" / "mm8bdm-v6b.launch.json"


def check(name, group, kind, cmd, desc, requires=("python",), timeout=120.0):
    return {
        "name": name,
        "group": group,
        "kind": kind,
        "cmd": list(cmd),
        "desc": desc,
        "requires": list(requires),
        "timeout": float(timeout),
    }


CHECKS = [
    # -- fast: pure repository-static verification -------------------------
    check("agent-config", "fast", "config", [PY, "tools/check_agent_config.py"],
          "Cross-harness launcher/MCP configuration drift", timeout=60),
    check("batch-d-source", "fast", "static", [PY, "tools/check_batch_d.py", "--source-only"],
          "Batch D source/fixture acceptance (no music pk3 needed)"),
    check("bonus-event-settings", "fast", "static", [PY, "tools/check_bonus_event_settings.py"],
          "Bonus event settings, thresholds and lifecycle", ["python", "cc"]),
    check("boss-defs", "fast", "static", [PY, "tools/check_boss_defs.py"],
          "Boss definition table consistency"),
    check("boss-overrides", "fast", "static", [PY, "tools/check_boss_overrides.py"],
          "Per-boss override rules", ["python", "cc"]),
    check("boss-selection-settings", "fast", "static", [PY, "tools/check_boss_selection_settings.py"],
          "Boss selection thresholds and weighted strategies", ["python", "cc"]),
    check("boss-stats", "fast", "static", [PY, "tools/check_boss_stats.py"],
          "Boss win-rate counter contract", ["python", "cc"]),
    check("eden-stat-deltas", "fast", "static", [PY, "tools/check_eden_stat_deltas.py"],
          "Eden stat delta application", ["python", "cc"]),
    check("gembanker-portrait", "fast", "static", [PY, "tools/check_gembanker_portrait.py"],
          "GemBanker viewer-local portrait modes and animation timing", ["python", "cc"]),
    check("true-power", "fast", "static", [PY, "tools/check_true_power.py"],
          "True Power repeat HP bonus and Higlur morph lifecycle", ["python", "cc"]),
    check("extra-life-transition", "fast", "static", [PY, "tools/check_extra_life_transition.py"],
          "Extra-life transition path", ["python", "cc"]),
    check("result-music", "fast", "static", [PY, "tools/check_result_music.py"],
          "Music selection at round result", ["python", "cc"]),
    check("round-settlement", "fast", "static", [PY, "tools/check_round_settlement.py"],
          "Round settlement exit contract", ["python", "cc"]),
    check("sakiko-mujica", "fast", "static", [PY, "tools/check_sakiko_mujica.py"],
          "Sakiko/Mujica class behaviour", ["python", "cc"]),
    check("survivor-morph-cleanup", "fast", "static", [PY, "tools/check_survivor_morph_cleanup.py"],
          "Survivor morph inventory cleanup", ["python", "cc"]),
    check("state-loops", "fast", "static", [PY, "tools/check_state_loops.py"],
          "No unconditional zero-duration DECORATE state loops (server freeze/OOM)"),
    check("team-presentation", "fast", "static", [PY, "tools/check_team_presentation.py"],
          "Generated team presentation rows match the old tables"),
    check("team-visibility", "fast", "static", [PY, "tools/check_team_visibility.py"],
          "FFA teammate privacy and automap visibility rules", ["python", "cc"]),
    check("bars-generator", "fast", "generator", [PY, "tools/_gen_barpos.py", "--check"],
          "Generated HUD bar code is up to date"),
    check("bars-generator-tests", "fast", "generator", [PY, "tools/test_gen_barpos.py"],
          "HUD bar generator unit tests"),
    check("team-presentation-generator", "fast", "generator",
          [PY, "tools/gen_team_presentation.py", "--check"],
          "Generated team presentation fragments are up to date"),

    # -- smoke: local environment / build-level verification ---------------
    check("environment", "smoke", "env", [PY, "tools/check_environment.py"],
          "ACC, WADs and reference trees", timeout=120),
    check("compile-acs", "smoke", "build", ["bash", "tools/compile-acs.sh"],
          "Full ACS compile in LOADACS order", ["bash", "acc"], 300),
    check("validate-build-pk3", "smoke", "build", ["bash", "tools/validate-build-pk3.sh"],
          "Existing out/build.pk3 archive contents", ["bash", "unzip"], 300),
    check("mcp-dry-run", "smoke", "mcp", ["bash", "tools/mcp/smoke-test.sh", "--dry-run"],
          "MCP launcher/server resolution without starting the engine", ["bash", "node"], 120),

    # -- full: real engine verification (local machine only) ---------------
    check("mcp-smoke", "full", "engine",
          ["node", "tools/mcp/smoke-test.mjs", "--profile", "mm8bdm-v6b-smoke", "--json"],
          "MCP-controlled engine startup and player_state", ["node", "zandronum"], 900),
    check("mcp-network", "full", "engine", ["node", "tools/mcp/network-test.mjs", "--json"],
          "Dedicated server + two-client authentication/snapshot", ["node", "zandronum"], 900),
    check("mcp-team-info-sync", "full", "engine",
          ["node", "tools/mcp/team-info-sync-test.mjs", "--json"],
          "Per-client CLIENTSIDE team-info delivery", ["node", "zandronum"], 900),
    check("mcp-team-presentation", "full", "engine",
          ["node", "tools/mcp/team-presentation-test.mjs", "--json"],
          "Team presentation resolver end to end", ["node", "zandronum"], 900),
]


def tool_problem(tool):
    """Return a human reason when a required tool is unavailable, else None."""
    if tool == "python":
        return None
    if tool == "acc":
        if os.environ.get("ACC"):
            return None
        return None if shutil.which("acc") else "acc (set ACC or put acc on PATH)"
    if tool == "cc":
        return None if (shutil.which("cc") or shutil.which("gcc")) else "cc/gcc"
    if tool == "zandronum":
        exe = os.environ.get("ZANDRONUM_EXE")
        if not exe:
            return "ZANDRONUM_EXE (unset)"
        return None if Path(exe).is_file() else f"ZANDRONUM_EXE={exe} (missing)"
    return None if shutil.which(tool) else tool


def preflight_warnings():
    warnings = []
    raw = os.environ.get("ZANDRONUM_LAUNCH_PROFILES")
    if raw:
        path = Path(os.path.expanduser(raw))
        if not path.is_absolute():
            path = REPO / path
        if not path.is_file():
            warnings.append(
                f"ZANDRONUM_LAUNCH_PROFILES points at missing {raw}; "
                f"new shells use tools/mm8bdm-v6b.launch.json (restart this shell/harness)")
        elif path.resolve() != CANONICAL_PROFILE.resolve():
            warnings.append(
                f"ZANDRONUM_LAUNCH_PROFILES={raw} differs from "
                f"tools/mm8bdm-v6b.launch.json")
    return warnings


def tail_lines(text, limit=12):
    lines = [line.rstrip() for line in (text or "").splitlines() if line.strip()]
    return "\n".join(lines[-limit:])


def run_check(item, timeout_scale):
    timeout = item["timeout"] * timeout_scale
    missing = [tool for tool in item["requires"] if tool_problem(tool)]
    base = {
        "name": item["name"],
        "group": item["group"],
        "kind": item["kind"],
        "cmd": item["cmd"],
        "requires": item["requires"],
    }
    if missing:
        reasons = ", ".join(tool_problem(tool) for tool in missing)
        base.update(status="skip", exit_code=None, duration_s=0.0,
                    reason=f"missing tool: {reasons}", output_tail="")
        return base

    started = time.monotonic()
    try:
        proc = subprocess.run(
            item["cmd"], cwd=REPO, env=os.environ.copy(),
            capture_output=True, text=True, timeout=timeout,
        )
        exit_code = proc.returncode
        output = (proc.stdout or "") + (proc.stderr or "")
        reason = ""
    except subprocess.TimeoutExpired as exc:
        exit_code = None
        output = ""
        for stream in (exc.stdout, exc.stderr):
            if stream:
                output += stream if isinstance(stream, str) else stream.decode(errors="replace")
        reason = f"timeout after {timeout:.0f}s"
    except OSError as exc:
        exit_code = None
        output = ""
        reason = f"could not execute: {exc}"

    duration = time.monotonic() - started
    status = "pass" if exit_code == 0 else "fail"
    base.update(
        status=status,
        exit_code=exit_code,
        duration_s=round(duration, 2),
        reason=reason,
        output_tail=tail_lines(output),
    )
    return base


def git_state():
    try:
        head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO,
                              capture_output=True, text=True, timeout=10)
        dirty = subprocess.run(["git", "status", "--porcelain"], cwd=REPO,
                               capture_output=True, text=True, timeout=10)
        return {
            "head": head.stdout.strip() or None,
            "dirty": bool(dirty.stdout.strip()),
        }
    except (OSError, subprocess.SubprocessError):
        return {"head": None, "dirty": None}


def select_checks(group, only, skip):
    wanted = set(only)
    unwanted = set(skip)
    selected = []
    for item in CHECKS:
        if item["group"] not in GROUP_ORDER[group]:
            continue
        if wanted and item["name"] not in wanted:
            continue
        if item["name"] in unwanted:
            continue
        selected.append(item)
    return selected


def print_list():
    print(f"{'group':6} {'name':28} {'kind':9} {'timeout':>7}  requires")
    for item in CHECKS:
        print(f"{item['group']:6} {item['name']:28} {item['kind']:9} "
              f"{item['timeout']:7.0f}  {', '.join(item['requires'])}")
        print(f"       {item['desc']}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    groups = parser.add_mutually_exclusive_group()
    groups.add_argument("--fast", action="store_true", help="static checks only (default)")
    groups.add_argument("--smoke", action="store_true", help="static + environment/build checks")
    groups.add_argument("--full", action="store_true", help="static + build + engine MCP tests")
    parser.add_argument("--list", action="store_true", help="print the check inventory and exit")
    parser.add_argument("--json", action="store_true", help="machine-readable report on stdout")
    parser.add_argument("--report", type=Path, metavar="PATH",
                        help="also write the JSON report to PATH")
    parser.add_argument("--only", default="", metavar="NAMES",
                        help="comma-separated check names to run")
    parser.add_argument("--skip", default="", metavar="NAMES",
                        help="comma-separated check names to skip")
    parser.add_argument("--timeout-scale", type=float, default=1.0, metavar="N",
                        help="multiply every per-check timeout (default 1.0)")
    parser.add_argument("--allow-skip", action="store_true",
                        help="tolerate skipped checks (missing toolchain)")
    parser.add_argument("--strict", action="store_true",
                        help="fail on preflight environment warnings")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="show check output tails on success too")
    args = parser.parse_args()

    if args.list:
        if args.json:
            print(json.dumps({"schema": SCHEMA, "checks": CHECKS}, indent=2))
        else:
            print_list()
        return 0

    if args.timeout_scale <= 0:
        parser.error("--timeout-scale must be positive")

    group = "full" if args.full else ("smoke" if args.smoke else "fast")
    known = {item["name"] for item in CHECKS}
    only = [name.strip() for name in args.only.split(",") if name.strip()]
    skip = [name.strip() for name in args.skip.split(",") if name.strip()]
    unknown = sorted((set(only) | set(skip)) - known)
    if unknown:
        parser.error(f"unknown check name(s): {', '.join(unknown)}")
    if args.only and not args.skip and not only:
        parser.error("--only needs at least one name")

    selected = select_checks(group, only, skip)
    if not selected:
        parser.error("no checks selected")

    warnings = preflight_warnings()
    started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    started = time.monotonic()

    results = []
    if not args.json:
        print(f"== gate --{group}: {len(selected)} check(s), repo {REPO}")
        for warning in warnings:
            print(f"[WARN] {warning}")
    for item in selected:
        result = run_check(item, args.timeout_scale)
        results.append(result)
        if args.json:
            continue
        print(f"[{result['status'].upper():4}] {result['name']:30} {result['duration_s']:6.2f}s"
              + (f"  ({result['reason']})" if result["reason"] else ""))
        if result["status"] != "pass" and result["output_tail"]:
            for line in result["output_tail"].splitlines():
                print(f"       {line}")
        elif args.verbose and result["output_tail"]:
            for line in result["output_tail"].splitlines():
                print(f"       {line}")

    duration = round(time.monotonic() - started, 2)
    counts = {"pass": 0, "fail": 0, "skip": 0}
    for result in results:
        counts[result["status"]] += 1
    skipped = counts["skip"] if not args.allow_skip else 0
    warned = len(warnings) if args.strict else 0
    ok = counts["fail"] == 0 and skipped == 0 and warned == 0

    report = {
        "schema": SCHEMA,
        "gate": group,
        "ok": ok,
        "strict": args.strict,
        "allow_skip": args.allow_skip,
        "started_at": started_at,
        "duration_s": duration,
        "repo": str(REPO),
        "git": git_state(),
        "warnings": warnings,
        "counts": counts,
        "checks": results,
    }

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                               encoding="utf-8")

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"summary: {counts['pass']} passed, {counts['fail']} failed, "
              f"{counts['skip']} skipped in {duration:.2f}s")
        if counts["skip"] and not args.allow_skip:
            print("skipped checks are failures; pass --allow-skip to tolerate "
                  "a missing toolchain")
        if args.strict and warnings:
            print("strict: preflight environment warnings are failures")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

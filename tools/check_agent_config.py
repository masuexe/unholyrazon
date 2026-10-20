#!/usr/bin/env python3
"""Cross-harness agent configuration drift check.

Every agent harness on this machine reaches the same Zandronum MCP server, and
each one wires itself through its own *machine-local* file:

  .mcp.json                repo-level MCP declaration (most harnesses)
  .agents/mcp_config.json  shared agent config (Antigravity et al.)
  .dsh/cordis.patch.yml    dsh overlay
  ~/.bashrc, ~/.profile    shell exports used by CLI smoke tests

None of those is version-controlled, so they drift silently.  This check fails
when a referenced launcher profile / engine / server path does not exist, when
a source disagrees with the canonical launcher profile, or when the canonical
profile stops declaring the smoke-test default.  Absent machine-local files are
skipped, so a fresh clone passes; the ambient shell environment is reported as a
warning because an already-running harness cannot pick up a fixed shell config.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CANONICAL = REPO / "tools" / "mm8bdm-v6b.launch.json"
DEFAULT_SMOKE_PROFILE = "mm8bdm-v6b-smoke"

PASS, FAIL, WARN, SKIP = "pass", "fail", "warn", "skip"

# label, path, parser kind
SOURCE_FILES = [
    ("mcp-json", REPO / ".mcp.json", "json"),
    ("agents-mcp-config", REPO / ".agents" / "mcp_config.json", "json"),
    ("dsh-overlay", REPO / ".dsh" / "cordis.patch.yml", "yaml"),
    ("bashrc", Path.home() / ".bashrc", "shell"),
    ("profile", Path.home() / ".profile", "shell"),
]

ENV_PROFILE = "ZANDRONUM_LAUNCH_PROFILES"
ENV_EXE = "ZANDRONUM_EXE"


def resolve_path(raw: str) -> Path:
    path = Path(os.path.expanduser(raw.strip().strip("'\"")))
    return path if path.is_absolute() else (REPO / path)


def parse_json_mcp(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    servers = data.get("mcpServers") or {}
    refs = {"profiles": [], "exes": [], "servers": [], "names": sorted(servers)}
    for name, spec in servers.items():
        env = (spec or {}).get("env") or {}
        if env.get(ENV_PROFILE):
            refs["profiles"].append((name, env[ENV_PROFILE]))
        if env.get(ENV_EXE):
            refs["exes"].append((name, env[ENV_EXE]))
        for arg in (spec or {}).get("args") or []:
            if isinstance(arg, str) and (arg.startswith("/") or arg.startswith("~")):
                refs["servers"].append((name, arg))
    return refs


def parse_yaml_overlay(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    refs = {"profiles": [], "exes": [], "servers": [], "names": []}
    for match in re.finditer(r"ZANDRONUM_LAUNCH_PROFILES:\s*[\"']?([^\"'\s#]+)", text):
        refs["profiles"].append(("dsh-mcp", match.group(1)))
    for match in re.finditer(r"ZANDRONUM_EXE:\s*[\"']?([^\"'\s#]+)", text):
        refs["exes"].append(("dsh-mcp", match.group(1)))
    for match in re.finditer(r"serverName:\s*([^\s#]+)", text):
        refs["names"].append(match.group(1).strip("\"'"))
    return refs


def parse_shell(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    refs = {"profiles": [], "exes": [], "servers": [], "names": []}
    pattern = re.compile(r"(?:export\s+)?ZANDRONUM_(LAUNCH_PROFILES|EXE)=[\"']?([^\"'\s#]+)")
    for match in pattern.finditer(text):
        key, value = match.group(1), match.group(2)
        bucket = "profiles" if key == "LAUNCH_PROFILES" else "exes"
        refs[bucket].append((path.name, value))
    return refs


PARSERS = {"json": parse_json_mcp, "yaml": parse_yaml_overlay, "shell": parse_shell}


def add(results: list, name: str, status: str, detail: str) -> None:
    results.append({"name": name, "status": status, "detail": detail})


def check_canonical(results: list) -> list:
    """Validate the canonical launcher profile file itself."""
    if not CANONICAL.is_file():
        add(results, "canonical-profile", FAIL,
            f"missing {CANONICAL.relative_to(REPO)}")
        return []
    try:
        data = json.loads(CANONICAL.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        add(results, "canonical-profile", FAIL, f"unreadable: {exc}")
        return []
    if not isinstance(data, dict) or not data:
        add(results, "canonical-profile", FAIL, "empty or not a JSON object")
        return []
    profiles = sorted(data)
    if DEFAULT_SMOKE_PROFILE not in data:
        add(results, "canonical-profile", FAIL,
            f"does not declare {DEFAULT_SMOKE_PROFILE!r} (profiles: {', '.join(profiles)})")
    else:
        add(results, "canonical-profile", PASS,
            f"declares {len(profiles)} profiles incl. {DEFAULT_SMOKE_PROFILE!r}")
    return profiles


def check_sources(results: list, canonical_resolved: Path) -> None:
    """Validate every machine-local source that exists."""
    seen_any = False
    all_names: list = []
    for label, path, kind in SOURCE_FILES:
        if not path.is_file():
            continue
        seen_any = True
        try:
            refs = PARSERS[kind](path)
        except (OSError, ValueError) as exc:
            add(results, f"source:{label}", FAIL, f"unreadable: {exc}")
            continue

        for server, raw in refs["profiles"]:
            resolved = resolve_path(raw)
            if not resolved.is_file():
                add(results, f"source:{label}:{server}:profile", FAIL,
                    f"{raw} does not exist")
            elif resolved.resolve() != canonical_resolved:
                add(results, f"source:{label}:{server}:profile", FAIL,
                    f"{raw} differs from canonical {CANONICAL.relative_to(REPO)}")
            else:
                add(results, f"source:{label}:{server}:profile", PASS,
                    f"-> {CANONICAL.relative_to(REPO)}")

        for server, raw in refs["exes"]:
            if not resolve_path(raw).is_file():
                add(results, f"source:{label}:{server}:engine", FAIL,
                    f"{raw} does not exist")

        for server, raw in refs["servers"]:
            if not resolve_path(raw).is_file():
                add(results, f"source:{label}:{server}:server-js", FAIL,
                    f"{raw} does not exist")

        # Only the JSON MCP declarations are meant to be the same list; the dsh
        # overlay mounts a subset and harness-native tools are not listed there.
        if kind == "json" and refs["names"]:
            all_names.append((label, refs["names"]))

    if not seen_any:
        add(results, "config-sources", SKIP,
            "no machine-local harness config present (nothing to compare)")
        return

    if len(all_names) > 1:
        base_label, base_names = all_names[0]
        for label, names in all_names[1:]:
            if names != base_names:
                add(results, "mcp-server-names", FAIL,
                    f"{label} declares {names}, {base_label} declares {base_names}")
            else:
                add(results, "mcp-server-names", PASS,
                    f"{label} and {base_label} agree ({len(names)} servers)")


def check_ambient(results: list, canonical_resolved: Path) -> None:
    """Report the running process environment separately from the files."""
    for var, expected in ((ENV_PROFILE, canonical_resolved), (ENV_EXE, None)):
        raw = os.environ.get(var)
        if not raw:
            continue
        resolved = resolve_path(raw)
        if not resolved.is_file():
            add(results, f"ambient:{var}", WARN,
                f"points at missing {raw}; restart the shell/harness "
                f"(files are fixed but this process keeps its old environment)")
        elif expected is not None and resolved.resolve() != expected:
            add(results, f"ambient:{var}", WARN,
                f"{raw} differs from canonical; restart the shell/harness")
        else:
            add(results, f"ambient:{var}", PASS, f"-> {raw}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", action="store_true", help="machine-readable report on stdout")
    parser.add_argument("--strict", action="store_true",
                        help="treat warnings (stale ambient environment) as failures")
    args = parser.parse_args()

    results: list = []
    canonical_resolved = CANONICAL.resolve()
    check_canonical(results)
    check_sources(results, canonical_resolved)
    check_ambient(results, canonical_resolved)

    counts = {status: 0 for status in (PASS, FAIL, WARN, SKIP)}
    for item in results:
        counts[item["status"]] += 1
    failed = counts[FAIL] + (counts[WARN] if args.strict else 0)
    ok = failed == 0

    report = {
        "schema": 1,
        "check": "agent-config",
        "ok": ok,
        "strict": args.strict,
        "canonical_profile": str(CANONICAL.relative_to(REPO)),
        "counts": counts,
        "checks": results,
    }
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0 if ok else 1

    print("== cross-harness agent config drift")
    print(f"canonical launcher profile: {report['canonical_profile']}")
    for item in results:
        print(f"[{item['status'].upper():4}] {item['name']}: {item['detail']}")
    print(f"summary: {counts[PASS]} passed, {counts[FAIL]} failed, "
          f"{counts[WARN]} warnings, {counts[SKIP]} skipped")
    if args.strict and counts[WARN]:
        print("strict: warnings are failures (restart the shell to clear ambient warnings)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

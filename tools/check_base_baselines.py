#!/usr/bin/env python3
"""Prove the frozen external-name baselines exist in the v6c base game.

The static checkers (check_asset_references.py, check_lump_integrity.py) run in
a fresh clone with no WADs, so they resolve names supplied by the base game
against frozen constants. Those constants were first extracted from the v6b
packages. This check guards that the frozen allowlist is real v6c coverage: every
allowlisted sound, LANGUAGE key, HUD graphic and TEXTURES patch target must be
present in ../wads/mm8bdm-v6c.pk3. A base-game rename or removal then fails here
instead of shipping a silently broken reference.

Run:  python3 tools/check_base_baselines.py [--json] [--strict]
Exit: 0 clean or skipped (no base package), 1 missing names, 2 usage error.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
PK3_NAME = "mm8bdm-v6c.pk3"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def wads_dir():
    if os.environ.get("MM8BDM_WADS_DIR"):
        return Path(os.environ["MM8BDM_WADS_DIR"])
    local = ROOT / "tools" / "paths.local.json"
    if local.is_file():
        try:
            cfg = json.loads(local.read_text(encoding="utf-8"))
            if cfg.get("wads_dir"):
                return (ROOT / cfg["wads_dir"]).resolve()
        except (OSError, ValueError):
            pass
    return (ROOT / ".." / "wads").resolve()


def read_text(archive, name):
    return archive.read(name).decode("utf-8", "replace")


def strip_comments(text):
    import re
    text = re.sub(r"/\*.*?\*/", lambda m: re.sub(r"[^\n]", "", m.group(0)), text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


def base_sets(pk3, ar, li):
    """Return (sounds, language_keys, graphics) defined by the base package."""
    import re

    def basename(name):
        return name.rsplit("/", 1)[-1]

    with ZipFile(pk3) as archive:
        names = archive.namelist()

        sounds = set()
        for name in names:
            if basename(name).upper().startswith("SNDINFO"):
                for line in strip_comments(read_text(archive, name)).splitlines():
                    tokens = line.split()
                    if not tokens:
                        continue
                    head = tokens[0].lower()
                    field = ar.SND_NAME_FIELD.get(head)
                    if field is not None:
                        if len(tokens) > field:
                            sounds.add(tokens[field].lower())
                        continue
                    if head.startswith("$"):
                        continue
                    sounds.add(head)

        language = set()
        for name in names:
            if basename(name).upper().startswith("LANGUAGE"):
                text = strip_comments(read_text(archive, name))
                for match in ar.LANGUAGE_DEF_RE.finditer(text):
                    language.add(match.group(1).upper())

        graphics = set()
        for name in names:
            low = name.lower()
            if low.startswith(("sprites/", "graphics/", "patches/")):
                graphics.add(basename(name).rsplit(".", 1)[0].upper())
        for name in names:
            if basename(name).upper().startswith("TEXTURES"):
                text = strip_comments(read_text(archive, name))
                for match in li.TEXTURE_DEF_RE.finditer(text):
                    graphics.add(match.group(1).strip('"').upper())

    return sounds, language, graphics


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--strict", action="store_true",
                        help="fail when the base package is absent instead of skipping")
    parser.add_argument("--pk3", type=Path, help="explicit path to the v6c base package")
    args = parser.parse_args()

    pk3 = args.pk3 or (wads_dir() / PK3_NAME)
    if not pk3.is_file():
        message = f"base package not found: {pk3}"
        if args.strict:
            print(f"[FAIL] {message}", file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps({"status": "skip", "reason": message}))
        else:
            print(f"[SKIP] {message} (pass --strict to fail)")
        return 0

    ar = load_module("check_asset_references", ROOT / "tools" / "check_asset_references.py")
    li = load_module("check_lump_integrity", ROOT / "tools" / "check_lump_integrity.py")
    sounds, language, graphics = base_sets(pk3, ar, li)

    groups = [
        ("sounds", getattr(ar, "BASE_GAME_SOUNDS", frozenset()), sounds),
        ("language", getattr(ar, "BASE_GAME_LANGUAGE_KEYS", frozenset()), language),
        ("hud_graphics", getattr(ar, "BASE_GAME_HUD_GRAPHICS", frozenset()), graphics),
        ("graphics", getattr(li, "BASE_GAME_GRAPHICS", frozenset()), graphics),
    ]
    findings = []
    summary = {}
    for label, frozen, base in groups:
        missing = sorted(frozen - base)
        summary[label] = {"frozen": len(frozen), "base": len(base), "missing": missing}
        for name in missing:
            findings.append(f"{label}: {name}")

    status = "fail" if findings else "pass"
    if args.json:
        print(json.dumps({"status": status, "pk3": str(pk3), "groups": summary,
                          "findings": findings}, indent=2))
    else:
        print(f"== frozen baselines vs {pk3.name}")
        for label, frozen, base in groups:
            mark = "OK" if not (frozen - base) else "MISSING"
            print(f"[{mark:7}] {label:14} frozen={len(frozen):5} base={len(base):6}")
        for finding in findings:
            print(f"       {finding}")
        print(f"summary: {'FAIL' if findings else 'PASS'} ({len(findings)} missing name(s))")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())

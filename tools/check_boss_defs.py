#!/usr/bin/env python3
"""Verify every DefineBoss actor in uh_bossdefs.acs exists in src/actors DECORATE."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOSSDEFS = (
    ROOT
    / "src"
    / "acs_source"
    / "classes"
    / "bosses"
    / "boss_definition_table.acs"
)
ACTORS_DIR = ROOT / "src" / "actors"

DEFINE_RE = re.compile(
    r'DefineBoss\s*\(\s*-?\d+\s*,\s*"([^"]+)"',
    re.MULTILINE,
)
ACTOR_RE = re.compile(
    r'(?im)^\s*actor\s+([A-Za-z_][A-Za-z0-9_]*)\b',
)


def collect_actors() -> set[str]:
    names: set[str] = set()
    for path in ACTORS_DIR.rglob("*"):
        if path.suffix.lower() not in {".dec", ".txt", ".decorate"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            print(f"warn: cannot read {path}: {exc}", file=sys.stderr)
            continue
        names.update(ACTOR_RE.findall(text))
    return names


def main() -> int:
    if not BOSSDEFS.is_file():
        print(f"error: missing {BOSSDEFS.relative_to(ROOT)}", file=sys.stderr)
        return 2
    if not ACTORS_DIR.is_dir():
        print(f"error: missing {ACTORS_DIR.relative_to(ROOT)}", file=sys.stderr)
        return 2

    text = BOSSDEFS.read_text(encoding="utf-8", errors="replace")
    bosses = DEFINE_RE.findall(text)
    if not bosses:
        print("error: no DefineBoss rows found", file=sys.stderr)
        return 2

    actors = collect_actors()
    missing = sorted({name for name in bosses if name not in actors})

    print(f"DefineBoss rows: {len(bosses)}")
    print(f"actor classes under src/actors: {len(actors)}")
    if missing:
        print("missing DECORATE actors:")
        for name in missing:
            print(f"  {name}")
        return 1

    print("ok: all DefineBoss actors exist in src/actors")
    return 0


if __name__ == "__main__":
    sys.exit(main())

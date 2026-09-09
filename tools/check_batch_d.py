#!/usr/bin/env python3
"""Fast static/resource acceptance checks for Batch D."""
from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MUSIC = Path("/home/user/projects/mm8bdm/unholyrazon_music/razon_soundtest.pk3")
DEF = ROOT / "src/acs_source/unholy/uh_def.acs"
FUNCS = ROOT / "src/acs_source/unholy/uh_funclib.acs"
REQUIRED_MUSIC = {
    "M_EYE13", "M_EYE14", "M_EYE15", "SATANMUS",
    "M_UB029X", "M_UB038", "M_UB048X", "M_UB104X",
}


def function_body(text: str, name: str) -> str:
    match = re.search(rf"function\s+\w+\s+{re.escape(name)}\s*\([^)]*\)\s*\{{", text)
    if not match:
        return ""
    start = match.end()
    depth = 1
    for pos in range(start, len(text)):
        if text[pos] == "{":
            depth += 1
        elif text[pos] == "}":
            depth -= 1
            if depth == 0:
                return text[start:pos]
    return ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--music-pk3", type=Path, default=DEFAULT_MUSIC)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    checks: list[dict[str, str]] = []

    def check(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "status": "pass" if passed else "fail", "detail": detail})

    try:
        defs = DEF.read_text(encoding="utf-8")
        funcs = FUNCS.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    check("five-boss constant", bool(re.search(r"#define\s+MAX_BOSSES\s+5\b", defs)), "MAX_BOSSES must be 5")

    validator = function_body(funcs, "DebugValidateRoundStart")
    combo_validation = "BOSSCOMBO_MAX" in validator and (
        "BossComboFullyRegistered" in validator
        or ("bosscombobossids" in validator and "IsBossDefined" in validator)
    )
    check(
        "round-start combo registration validation",
        combo_validation,
        "DebugValidateRoundStart must validate every combo boss through the helper or an equivalent explicit loop",
    )

    initial_schema = bool(re.search(r"bosscombodata\s*\[\s*BOSSCOMBO_MAX\s*\]\s*\[\s*7\s*\]", defs))
    check(
        "initial combo schema",
        initial_schema,
        "seven columns cover the in-scope random, non-versus, no-hook combo tier",
    )

    music = args.music_pk3.resolve()
    if not music.is_file():
        check("Batch D music resources", False, f"missing archive: {music}")
    else:
        try:
            with zipfile.ZipFile(music) as archive:
                bad = archive.testzip()
                lumps = set()
                for name in archive.namelist():
                    if name.endswith("/"):
                        continue
                    leaf = Path(name).name
                    lumps.add(leaf.upper())
                    lumps.add(Path(leaf).stem.upper())
            missing = sorted(REQUIRED_MUSIC - lumps)
            check(
                "Batch D music resources",
                bad is None and not missing,
                f"bad member: {bad}" if bad else ("missing: " + ", ".join(missing) if missing else f"8 required lumps found in {music}"),
            )
        except (OSError, zipfile.BadZipFile) as exc:
            check("Batch D music resources", False, f"invalid archive: {exc}")

    failed = [item for item in checks if item["status"] == "fail"]
    result = {"status": "pass" if not failed else "fail", "checks": checks, "failed": len(failed)}
    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        for item in checks:
            print(f"{item['status'].upper():4} {item['name']}: {item['detail']}")
        print(f"Batch D static/resource checks: {len(checks) - len(failed)} passed, {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

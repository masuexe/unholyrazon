#!/usr/bin/env python3
"""Static contract checks for Unholy info menus (MENUDEF.*Help).

Verifies:
1. Every OptionValue table within each *Help file has identical IDs in strictly
   ascending numerical order.
2. Every description/category OptionValue entry begins with a Zandronum color
   escape (\\cX or \\c[Name]).
3. Every UH_BossHealth entry uses the BaseHP#PerPlayerHP format.
4. No OptionValue string overflows the vertical line budget reserved by the
   OptionMenu layout (counting the Option row itself plus following StaticText
   rows before the next Option or bottom separator).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

COLOR_PREFIX_RE = re.compile(r'^\\c(\[[^\]]+\]|[a-zA-Z\-\+\!\*])')
OPTION_VALUE_RE = re.compile(
    r'OptionValue\s+"?(\w+)"?\s*\{(.*?)\}', re.S
)
ENTRY_RE = re.compile(r'^\s*(-?\d+)\s*,\s*"((?:\\.|[^"\\])*)"', re.M)
OPTION_MENU_RE = re.compile(
    r'OptionMenu\s+"?(\w+)"?\s*\{(.*?)\}', re.S
)

SPECS = [
    (
        "src/MENUDEF.CHELP",
        "UH_ClassHelpMenu",
        ["UH_ClassName", "UH_ClassHealth", "UH_ClassSpeed", "UH_ClassJump",
         "UH_ClassMainfire", "UH_ClassAltfire", "UH_ClassExtra"],
        {"UH_ClassMainfire", "UH_ClassAltfire", "UH_ClassExtra"},
    ),
    (
        "src/MENUDEF.BossHelp",
        "UH_BossHelpMenu",
        ["UH_BossName", "UH_BossHealth", "UH_BossSpeed", "UH_BossJump",
         "UH_BossMainfire", "UH_BossAltfire", "UH_BossItem", "UH_BossExtra"],
        {"UH_BossMainfire", "UH_BossAltfire", "UH_BossItem", "UH_BossExtra"},
    ),
    (
        "src/MENUDEF.EyeHelp",
        "UH_EyeHelpMenu",
        ["UH_EyeName", "UH_EyeHealth", "UH_EyeSpeed", "UH_EyeJump",
         "UH_EyeMainfire", "UH_EyeAltfire", "UH_EyeExtra"],
        {"UH_EyeMainfire", "UH_EyeAltfire", "UH_EyeExtra"},
    ),
    (
        "src/MENUDEF.ItemHelp",
        "UH_ItemHelpMenu",
        ["UH_ItemName", "UH_ItemCategory", "UH_ItemDesc"],
        {"UH_ItemCategory", "UH_ItemDesc"},
    ),
]


def parse_menu_budgets(text: str, menu_name: str) -> dict[str, int]:
    """Return max line count per OptionValue referenced in OptionMenu."""
    m = None
    for cand in OPTION_MENU_RE.finditer(text):
        if cand.group(1) == menu_name:
            m = cand
            break
    if not m:
        return {}
    lines = m.group(2).splitlines()
    budgets: dict[str, int] = {}
    current_val: str | None = None
    rows = 0
    for raw in lines:
        line = re.sub(r'//.*', '', raw).strip()
        if not line:
            continue
        opt = re.match(r'^Option\s+"[^"]+"\s*,\s*"[^"]+"\s*,\s*"(\w+)"', line)
        if opt:
            if current_val is not None:
                budgets[current_val] = rows
            current_val = opt.group(1)
            rows = 1
        elif line.startswith("StaticText"):
            if "$MNU_UH_EQUAL_LINE" in line:
                if current_val is not None:
                    budgets[current_val] = rows
                    current_val = None
                    rows = 0
            elif current_val is not None:
                rows += 1
    if current_val is not None:
        budgets[current_val] = rows
    return budgets


def main() -> int:
    errors: list[str] = []

    for rel_path, menu_name, expected_tables, colored_tables in SPECS:
        path = ROOT / rel_path
        if not path.exists():
            errors.append(f"{rel_path}: file missing")
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        budgets = parse_menu_budgets(text, menu_name)

        tables: dict[str, list[tuple[int, str]]] = {}
        for m in OPTION_VALUE_RE.finditer(text):
            tname = m.group(1)
            entries = [(int(e.group(1)), e.group(2)) for e in ENTRY_RE.finditer(m.group(2))]
            tables[tname] = entries

        ref_ids: list[int] | None = None
        ref_table = ""
        for tname in expected_tables:
            if tname not in tables:
                errors.append(f"{rel_path}: missing OptionValue {tname}")
                continue
            entries = tables[tname]
            ids = [eid for eid, _ in entries]
            if ids != sorted(ids) or len(ids) != len(set(ids)):
                errors.append(f"{rel_path}:{tname}: IDs not strictly ascending")
            if ref_ids is None:
                ref_ids = ids
                ref_table = tname
            elif ids != ref_ids:
                missing = sorted(set(ref_ids) - set(ids))
                extra = sorted(set(ids) - set(ref_ids))
                errors.append(
                    f"{rel_path}:{tname}: ID mismatch vs {ref_table} "
                    f"(missing={missing}, extra={extra})"
                )

            max_lines = budgets.get(tname, 99)
            for eid, val in entries:
                if tname in colored_tables and not COLOR_PREFIX_RE.match(val):
                    errors.append(
                        f"{rel_path}:{tname}[{eid}]: missing Zandronum color prefix: {val!r}"
                    )
                if tname == "UH_BossHealth" and "#" not in val:
                    errors.append(
                        f"{rel_path}:{tname}[{eid}]: missing Base#PerPlayer '#' separator: {val!r}"
                    )
                line_count = val.count("\\n") + 1
                if line_count > max_lines:
                    errors.append(
                        f"{rel_path}:{tname}[{eid}]: {line_count} lines exceeds menu budget {max_lines}"
                    )

    if errors:
        for err in errors:
            print(f"FAIL: {err}", file=sys.stderr)
        return 1

    print("check_info_menus: PASS (all 4 info menus verified)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

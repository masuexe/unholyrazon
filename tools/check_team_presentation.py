#!/usr/bin/env python3
"""Verify the generated DefineTeamPresentation rows against the former tables.

The migration's acceptance criterion is that the resolver reproduces the former
hardcoded output exactly, so this check re-derives the old behaviour from the
files it was generated from and compares it with the generated rows:

  * shortName  == the former UH_Ti_GetClassName() output
                 (uh_teaminfo.acs special cases + the "_U" suffix strip)
  * portrait   == the former uhPortraitTex row (hud/player_portraits.acs)
  * scoreIcon  == the former UH_ScoreIconOverrideTex row, else the portrait

It also asserts every portrait class has a definition row (survivor / boss /
eye) or is an explicit presentation-only morph, and that the UIX PBMug_* script
set still agrees with the presentation portraits.

Usage:
    python3 tools/check_team_presentation.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TEAMINFO = ROOT / "src/acs_source/unholy/uh_teaminfo.acs"
PORTRAITS = ROOT / "src/acs_source/hud/player_portraits.acs"
UIXMUGS = ROOT / "src/acs_source/compat/mods/uix/uh_uix_mugshots.acs"
SURVDEFS = ROOT / "src/acs_source/classes/survivors/definitions/uh_survdefs.acs"
BOSSDEFS = ROOT / "src/acs_source/classes/bosses/boss_definition_table.acs"
EYEDEFS = ROOT / "src/acs_source/classes/demoneyes/definitions/uh_eyedefs.acs"

GEN = [
    ROOT / "src/acs_source/classes/survivors/definitions/uh_survdefs_presentation.acs",
    ROOT / "src/acs_source/classes/bosses/boss_presentation_defs.acs",
    ROOT / "src/acs_source/classes/demoneyes/definitions/uh_eyedefs_presentation.acs",
]

# Morph bodies that have no Define* row of their own.
PRESENTATION_ONLY = {"EyelentoMajorDemoneye"}

CALL_RE = re.compile(
    r'DefineTeamPresentation\(\s*"([^"]+)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*(-?\d+)\s*\)'
)


def read(path: Path) -> str:
    if not path.is_file():
        print(f"error: missing {path.relative_to(ROOT)}", file=sys.stderr)
        raise SystemExit(2)
    return path.read_text(encoding="utf-8", errors="replace")


def old_short_names(text: str) -> dict[str, str]:
    """The former UH_Ti_GetClassName() special cases, parsed from the source."""
    out: dict[str, str] = {}
    for cls, name in re.findall(r'StrICmp\(cls,\s*"([^"]+)"\)\s*==\s*0\)\s*\{\s*return\s*"([^"]*)"', text):
        out[cls] = name
    if "MegaManU" not in out:
        print("error: could not parse the UH_Ti_GetClassName special cases", file=sys.stderr)
        raise SystemExit(2)
    return out


def old_portrait_table(text: str) -> list[tuple[str, str]]:
    m = re.search(
        r"#define UH_PORTRAIT_COUNT \d+\s*\n"
        r"str uhPortraitClass\[UH_PORTRAIT_COUNT\] = \{(.*?)\};\s*\n"
        r"str uhPortraitTex\[UH_PORTRAIT_COUNT\] = \{(.*?)\};",
        text,
        re.S,
    )
    if not m:
        print("error: player_portraits.acs tables not found", file=sys.stderr)
        raise SystemExit(2)
    classes = [c.strip().strip('"') for c in m.group(1).replace("\n", " ").split(",") if c.strip()]
    texes = [t.strip().strip('"') for t in m.group(2).replace("\n", " ").split(",") if t.strip()]
    if len(classes) != len(texes):
        print(f"error: {len(classes)} classes vs {len(texes)} textures", file=sys.stderr)
        raise SystemExit(2)
    return list(zip(classes, texes))


def old_scoreicon_overrides(text: str) -> dict[str, str]:
    m = re.search(
        r"#define UH_SCOREICON_OVERRIDE_COUNT \d+\s*\n"
        r"str uhScoreIconOverrideClass\[UH_SCOREICON_OVERRIDE_COUNT\] = \{(.*?)\};\s*\n"
        r"str uhScoreIconOverrideTex\[UH_SCOREICON_OVERRIDE_COUNT\] = \{(.*?)\};",
        text,
        re.S,
    )
    if not m:
        return {}
    classes = [c.strip().strip('"') for c in m.group(1).replace("\n", " ").split(",") if c.strip()]
    texes = [t.strip().strip('"') for t in m.group(2).replace("\n", " ").split(",") if t.strip()]
    return dict(zip(classes, texes))


def expected_short_name(cls: str, specials: dict[str, str]) -> str:
    if cls in specials:
        return specials[cls]
    if len(cls) > 2 and cls.endswith("_U"):
        return cls[:-2]
    return cls


def main() -> int:
    specials = old_short_names(read(TEAMINFO))
    portraits = dict(old_portrait_table(read(PORTRAITS)))
    overrides = old_scoreicon_overrides(read(PORTRAITS))

    rows: dict[str, tuple[str, str, str, int]] = {}
    fails = 0
    for path in GEN:
        for cls, name, portrait, icon, flags in CALL_RE.findall(read(path)):
            if cls in rows:
                print(f"FAIL duplicate presentation row: {cls}")
                fails += 1
            rows[cls] = (name, portrait, icon, int(flags))

    # 1. Every former portrait class is registered with the same three outputs.
    for cls, tex in portraits.items():
        if cls not in rows:
            print(f"FAIL missing presentation row: {cls}")
            fails += 1
            continue
        name, portrait, icon, _ = rows[cls]
        want_name = expected_short_name(cls, specials)
        want_icon = overrides.get(cls, "")
        if name != want_name:
            print(f"FAIL {cls}: shortName {name!r} != former {want_name!r}")
            fails += 1
        if portrait != tex:
            print(f"FAIL {cls}: portrait {portrait!r} != former {tex!r}")
            fails += 1
        if icon != want_icon:
            print(f"FAIL {cls}: scoreIcon {icon!r} != former {want_icon!r}")
            fails += 1

    # 2. The scoreboard overrides must survive, including the presentation-only
    #    morph that never had a portrait row.
    for cls, tex in overrides.items():
        if cls not in rows:
            print(f"FAIL missing score-icon override row: {cls}")
            fails += 1
            continue
        if rows[cls][2] != tex:
            print(f"FAIL {cls}: scoreIcon {rows[cls][2]!r} != former override {tex!r}")
            fails += 1
    for cls in PRESENTATION_ONLY:
        if cls not in rows:
            print(f"FAIL missing presentation-only morph row: {cls}")
            fails += 1

    # 3. No row without a definition home and without an explicit morph note.
    defined: set[str] = set()
    for path, call in ((SURVDEFS, "DefineSurvivor"), (BOSSDEFS, "DefineBoss"), (EYEDEFS, "DefineDemoneye")):
        defined |= {a for a in re.findall(rf"{call}\(\s*-?\d+,\s*\"([^\"]+)\"", read(path)) if a}
    for cls in rows:
        if cls not in defined and cls not in PRESENTATION_ONLY:
            print(f"FAIL {cls}: no Define* registration and not a known morph")
            fails += 1

    # 4. UIX PBMug_<Class> scripts must still agree with the presentation
    #    portraits (phase 2 keeps them as the fallback).
    mug_re = re.compile(r'script\s+"PBMug_([A-Za-z0-9_]+)"\s*\(int tid\)\s*\{SetResultValue\("([^"]+)"\);\}')
    mugs = dict(mug_re.findall(read(UIXMUGS)))
    if not mugs:
        print("error: no PBMug_* scripts found", file=sys.stderr)
        raise SystemExit(2)
    for cls, tex in mugs.items():
        if cls not in rows:
            print(f"FAIL PBMug class without a presentation row: {cls}")
            fails += 1
        elif rows[cls][1] != tex:
            print(f"FAIL {cls}: portrait {rows[cls][1]!r} != PBMug {tex!r}")
            fails += 1
    for cls in rows:
        if cls in mugs:
            continue
        # Only the scoreboard-only morph may legitimately have no PBMug script.
        if cls in PRESENTATION_ONLY:
            continue
        print(f"note: {cls}: presentation portrait has no PBMug_ script (UIX fallback empty)")

    if fails:
        print(f"team presentation check FAILED ({fails} problem(s))")
        return 1
    print(f"ok: {len(rows)} presentation rows match the former hardcoded output")
    print(f"ok: {len(mugs)} UIX PBMug scripts agree")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Generate the built-in DefineTeamPresentation rows from the definition tables.

The Unholy teammate bar, the SCORINFO UHPlayerIcon column and the UIX Better
Team Display all resolve their display data through one actor-keyed
presentation table in UHDT (see reports/team-info-definition-api-implementation-
plan.md).  The built-in rows are generated so the resolver output stays
byte-identical to the former hardcoded tables:

  * shortName  reproduces the former UH_Ti_GetClassName() special cases
               (MegaManU -> "Mega Man", the four BusterExpert variants, and
               the "_U" suffix strip), because the survivor/boss/eye main
               tables carry the announcement names (with color codes) instead.
  * portrait   is the former uhPortraitTex row of the same class.
  * scoreIcon  is the former UH_ScoreIconOverrideTex row; "" means "same as
               portrait".

Rows are emitted next to the definition they belong to so an addon can find the
matching registration site:

  survivors  -> classes/survivors/definitions/uh_survdefs_presentation.acs
  bosses     -> classes/bosses/boss_presentation_defs.acs
  demoneyes  -> classes/demoneyes/definitions/uh_eyedefs_presentation.acs

Usage:
    python3 tools/gen_team_presentation.py            # write the fragments
    python3 tools/gen_team_presentation.py --check    # verify, write nothing
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SURVDEFS = ROOT / "src/acs_source/classes/survivors/definitions/uh_survdefs.acs"
BOSSDEFS = ROOT / "src/acs_source/classes/bosses/boss_definition_table.acs"
EYEDEFS = ROOT / "src/acs_source/classes/demoneyes/definitions/uh_eyedefs.acs"
PORTRAITS = ROOT / "src/acs_source/hud/player_portraits.acs"

OUT_SURV = ROOT / "src/acs_source/classes/survivors/definitions/uh_survdefs_presentation.acs"
OUT_BOSS = ROOT / "src/acs_source/classes/bosses/boss_presentation_defs.acs"
OUT_EYE = ROOT / "src/acs_source/classes/demoneyes/definitions/uh_eyedefs_presentation.acs"

# Former UH_Ti_GetClassName() special cases, kept verbatim so the teammate bar
# keeps printing the same short name it printed before the resolver existed.
NAME_SPECIALS = {
    "MegaManU": "Mega Man",
    "BusterExpert": "Buster Expert",
    "BusterMistress": "Buster Mistress",
    "TrueBusterExpert": "True Buster Expert",
    "TrueBusterMistress": "True Buster Mistress",
}

# Presentation-only morph bodies: no survivor/boss/eye definition exists, but
# the scoreboard still needs a face for them.  shortName "" falls back to the
# actor class, portrait "" means "no teammate-bar mugshot".
PRESENTATION_ONLY = {
    "EyelentoMajorDemoneye": ("", "", "I_MUG111"),
}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_defs(text: str, call: str) -> dict[str, int]:
    """actor -> definition id for one Define* call form."""
    out: dict[str, int] = {}
    for mid, actor in re.findall(rf"{call}\(\s*(-?\d+),\s*\"([^\"]+)\"", text):
        if actor:
            out[actor] = int(mid)
    return out


def parse_portrait_table(text: str) -> list[tuple[str, str]]:
    m = re.search(
        r"#define UH_PORTRAIT_COUNT \d+\s*\n"
        r"str uhPortraitClass\[UH_PORTRAIT_COUNT\] = \{(.*?)\};\s*\n"
        r"str uhPortraitTex\[UH_PORTRAIT_COUNT\] = \{(.*?)\};",
        text,
        re.S,
    )
    if not m:
        raise SystemExit("player_portraits.acs: class/texture tables not found")
    classes = [c.strip().strip('"') for c in m.group(1).replace("\n", " ").split(",") if c.strip()]
    texes = [t.strip().strip('"') for t in m.group(2).replace("\n", " ").split(",") if t.strip()]
    if len(classes) != len(texes):
        raise SystemExit(f"player_portraits.acs: {len(classes)} classes vs {len(texes)} textures")
    return list(zip(classes, texes))


def parse_scoreicon_overrides(text: str) -> dict[str, str]:
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


def short_name(cls: str) -> str:
    if cls in NAME_SPECIALS:
        return NAME_SPECIALS[cls]
    if len(cls) > 2 and cls.endswith("_U"):
        return cls[:-2]
    return cls


def acs_str(value: str) -> str:
    return f'"{value}"'


def emit(header: list[str], func: str, rows: list[tuple[str, str, str, str, int]]) -> str:
    lines = list(header)
    lines.append(f"function void {func}(void)")
    lines.append("{")
    for actor, name, portrait, icon, flags in rows:
        lines.append(
            f"  DefineTeamPresentation({acs_str(actor)}, {acs_str(name)}, "
            f"{acs_str(portrait)}, {acs_str(icon)}, {flags});"
        )
    lines.append("}")
    return "\n".join(lines) + "\n"


def build() -> dict[Path, str]:
    survivors = parse_defs(read(SURVDEFS), "DefineSurvivor")
    bosses = parse_defs(read(BOSSDEFS), "DefineBoss")
    eyes = parse_defs(read(EYEDEFS), "DefineDemoneye")
    portrait = dict(parse_portrait_table(read(PORTRAITS)))
    scoreicon = parse_scoreicon_overrides(read(PORTRAITS))

    rows: dict[str, list[tuple[str, str, str, str, int]]] = {
        "surv": [], "boss": [], "eye": [], "only": [],
    }
    seen: set[str] = set()
    for cls, tex in portrait.items():
        if cls in survivors:
            group = "surv"
        elif cls in bosses:
            group = "boss"
        elif cls in eyes:
            group = "eye"
        else:
            raise SystemExit(f"{cls}: portrait row has no Define* registration")
        if cls in seen:
            raise SystemExit(f"{cls}: duplicate portrait row")
        seen.add(cls)
        icon = scoreicon.get(cls, "")
        rows[group].append((cls, short_name(cls), tex, icon, 0))

    # Presentation-only morph bodies never reach the portrait table.
    only = [k for k in PRESENTATION_ONLY if k not in seen]
    for cls in only:
        name, mug, icon = PRESENTATION_ONLY[cls]
        rows["only"].append((cls, name, mug, icon, 0))

    header = [
        "// GENERATED by tools/gen_team_presentation.py -- do not edit by hand.",
        "// Presentation rows (teammate-bar short name, mugshot, scoreboard icon)",
        "// for the built-in demoneyes plus the Eyelento of Pain morph body,",
        "// which has no DefineDemoneye row of its own.  Regenerate with:",
        "//     python3 tools/gen_team_presentation.py",
        "//     python3 tools/gen_team_presentation.py --check",
    ]
    eye_header = [
        "// GENERATED by tools/gen_team_presentation.py -- do not edit by hand.",
        "// Presentation rows (teammate-bar short name, mugshot, scoreboard icon)",
        "// for the built-in demoneyes plus the Eyelento of Pain morph body,",
        "// which has no DefineDemoneye row of its own.  shortName \"\" falls back",
        "// to the actor class, so the morph keeps printing its class name.",
        "// Regenerate with:",
        "//     python3 tools/gen_team_presentation.py",
        "//     python3 tools/gen_team_presentation.py --check",
    ]

    return {
        OUT_SURV: emit(
            [
                "// GENERATED by tools/gen_team_presentation.py -- do not edit by hand.",
                "// Presentation rows (teammate-bar short name, mugshot, scoreboard icon)",
                "// for the built-in survivors.  Regenerate with:",
                "//     python3 tools/gen_team_presentation.py",
                "//     python3 tools/gen_team_presentation.py --check",
            ],
            "RegisterSurvPresentations",
            rows["surv"],
        ),
        OUT_BOSS: emit(
            [
                "// GENERATED by tools/gen_team_presentation.py -- do not edit by hand.",
                "// Presentation rows (teammate-bar short name, mugshot, scoreboard icon)",
                "// for the built-in bosses.  Regenerate with:",
                "//     python3 tools/gen_team_presentation.py",
                "//     python3 tools/gen_team_presentation.py --check",
            ],
            "RegisterBossPresentations",
            rows["boss"],
        ),
        OUT_EYE: emit(eye_header, "RegisterEyePresentations", rows["eye"] + rows["only"]),
    }


def main() -> int:
    check = "--check" in sys.argv[1:]
    outputs = build()
    drift = 0
    for path, text in outputs.items():
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if check:
            if current != text:
                print(f"DRIFT {path.relative_to(ROOT)}")
                drift = 1
            else:
                print(f"ok    {path.relative_to(ROOT)}")
            continue
        if current == text:
            print(f"same  {path.relative_to(ROOT)}")
            continue
        path.write_text(text, encoding="utf-8", newline="\n")
        print(f"wrote {path.relative_to(ROOT)} ({text.count('DefineTeamPresentation')} rows)")
    return drift


if __name__ == "__main__":
    raise SystemExit(main())

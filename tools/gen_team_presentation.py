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
BASELINE = ROOT / "tools/fixtures/former_player_portraits.tsv"

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

def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_defs(text: str, call: str) -> dict[str, int]:
    """actor -> definition id for one Define* call form."""
    out: dict[str, int] = {}
    for mid, actor in re.findall(rf"{call}\(\s*(-?\d+),\s*\"([^\"]+)\"", text):
        if actor:
            out[actor] = int(mid)
    return out


def parse_baseline(path: Path) -> tuple[dict[str, str], dict[str, str]]:
    """The frozen former table: actor -> portrait texture and actor -> score icon.

    A scoreboard icon of "-" means "same as the portrait"; the morph body that
    only ever had a scoreboard icon carries "-" as its portrait.
    """
    portrait: dict[str, str] = {}
    scoreicon: dict[str, str] = {}
    for lineno, line in enumerate(read(path).splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("//"):
            continue
        parts = line.split()
        if len(parts) != 3:
            raise SystemExit(f"{path.name}:{lineno}: expected 3 space-separated columns")
        actor, mug, icon = (part.strip() for part in parts)
        if not actor:
            raise SystemExit(f"{path.name}:{lineno}: empty actor")
        portrait[actor] = "" if mug == "-" else mug
        if icon != "-":
            scoreicon[actor] = icon
    if not portrait:
        raise SystemExit(f"{path.name}: no rows found")
    return portrait, scoreicon


def short_name(cls: str) -> str:
    if cls in NAME_SPECIALS:
        return NAME_SPECIALS[cls]
    if len(cls) > 2 and cls.endswith("_U"):
        return cls[:-2]
    return cls


def acs_str(value: str) -> str:
    return f'"{value}"'


def emit(
    header: list[str],
    func: str,
    rows: list[tuple[str, str, str, str, int]],
    *,
    brace_same_line: bool = False,
) -> str:
    lines = list(header)
    if brace_same_line:
        lines.append(f"function void {func}(void) {{")
    else:
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
    portrait, scoreicon = parse_baseline(BASELINE)

    rows: dict[str, list[tuple[str, str, str, str, int]]] = {
        "surv": [], "boss": [], "eye": [], "only": [],
    }
    seen: set[str] = set()
    for cls, tex in portrait.items():
        if not tex:
            continue  # presentation-only morph, handled below
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

    # Morph bodies the baseline carries without a portrait of their own (the
    # scoreboard-only Eyelento of Pain body).  They get an explicit short name so
    # every row reads the same way, and an empty portrait so the teammate bar
    # draws no face for them.
    for cls, tex in portrait.items():
        if tex or cls in seen:
            continue
        rows["only"].append((cls, short_name(cls), "", scoreicon.get(cls, ""), 0))

    # New morph presentation, outside the frozen migration baseline. Skin
    # consumers resolve the visible face at runtime; this is the Base fallback.
    rows["surv"].append(("MegaManUShiny", "Mega Man", "UMUG_0", "", 0))

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
            brace_same_line=True,
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
            brace_same_line=True,
        ),
        OUT_EYE: emit(eye_header, "RegisterEyePresentations", rows["eye"] + rows["only"], brace_same_line=True),
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

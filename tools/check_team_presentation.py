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

BASELINE = ROOT / "tools/fixtures/former_player_portraits.tsv"
UIXMUGS = ROOT / "src/acs_source/compat/mods/uix/uh_uix_mugshots.acs"
SURVDEFS = ROOT / "src/acs_source/classes/survivors/definitions/uh_survdefs.acs"
BOSSDEFS = ROOT / "src/acs_source/classes/bosses/boss_definition_table.acs"
EYEDEFS = ROOT / "src/acs_source/classes/demoneyes/definitions/uh_eyedefs.acs"

GEN = [
    ROOT / "src/acs_source/classes/survivors/definitions/uh_survdefs_presentation.acs",
    ROOT / "src/acs_source/classes/bosses/boss_presentation_defs.acs",
    ROOT / "src/acs_source/classes/demoneyes/definitions/uh_eyedefs_presentation.acs",
]

CALL_RE = re.compile(
    r'DefineTeamPresentation\(\s*"([^"]+)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*(-?\d+)\s*\)'
)


def read(path: Path) -> str:
    if not path.is_file():
        print(f"error: missing {path.relative_to(ROOT)}", file=sys.stderr)
        raise SystemExit(2)
    return path.read_text(encoding="utf-8", errors="replace")


# The former UH_Ti_GetClassName() special cases.  Frozen here (together with the
# portrait table in tools/fixtures) because that function and the fixed class ->
# texture arrays were deleted in phase 3; this check is what keeps the migrated
# output pinned to the original behaviour.
OLD_NAME_SPECIALS = {
    "MegaManU": "Mega Man",
    "BusterExpert": "Buster Expert",
    "BusterMistress": "Buster Mistress",
    "TrueBusterExpert": "True Buster Expert",
    "TrueBusterMistress": "True Buster Mistress",
}


def parse_baseline(path: Path) -> tuple[dict[str, str], dict[str, str]]:
    """actor -> portrait texture and actor -> scoreboard icon ("-" = same as
    portrait / no portrait)."""
    portrait: dict[str, str] = {}
    scoreicon: dict[str, str] = {}
    for lineno, line in enumerate(read(path).splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("//"):
            continue
        parts = line.split()
        if len(parts) != 3:
            print(f"error: {path.name}:{lineno}: expected 3 space-separated columns", file=sys.stderr)
            raise SystemExit(2)
        actor, mug, icon = (part.strip() for part in parts)
        portrait[actor] = "" if mug == "-" else mug
        if icon != "-":
            scoreicon[actor] = icon
    if not portrait:
        print(f"error: {path.name}: no rows found", file=sys.stderr)
        raise SystemExit(2)
    return portrait, scoreicon


def expected_short_name(cls: str) -> str:
    if cls in OLD_NAME_SPECIALS:
        return OLD_NAME_SPECIALS[cls]
    if len(cls) > 2 and cls.endswith("_U"):
        return cls[:-2]
    return cls


def main() -> int:
    portraits, overrides = parse_baseline(BASELINE)

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
        want_name = expected_short_name(cls)
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

    # 3. No row without a definition home and without an explicit morph note.
    morph_additions = {
        "MegaManUShiny": ("Mega Man", "UMUG_0", "", 0),
        "PlainDevilDemoneye": ("PlainDevilDemoneye", "I_MUG00", "", 0),
        "RichDevilDemoneye": ("RichDevilDemoneye", "I_MUG06", "", 0),
        "ProtoManBadGuy": ("ProtoManBadGuy", "UL113MUG", "", 0),
        "WeakHorse": ("WeakHorse", "UL066MUG", "", 0),
    }
    # Check every shiny actor independently against its DECORATE face, including
    # inherited Eden and the separate MegaMan skin fallback above.
    for path in (ROOT / "src/actors/classes/survivors").glob("*.dec"):
        source = re.sub(r"//[^\n]*|/\*[\s\S]*?\*/", "", read(path))
        actors = list(re.finditer(r"\bactor\s+(\w+)\s*:\s*(\w+)[^{\n]*\{", source))
        for i, actor in enumerate(actors):
            cls, base = actor.group(1, 2)
            if cls != base + "Shiny" or base == "MegaManU" or base not in portraits:
                continue
            body = source[actor.end():actors[i + 1].start() if i + 1 < len(actors) else len(source)]
            icon = re.search(r'Player\.ScoreIcon\s+"([^"]+)"', body)
            tex = icon.group(1) if icon else portraits[base]
            morph_additions[cls] = (expected_short_name(base), tex, "", 0)
    capacity = int(re.search(r"#libdefine UH_MAX_TEAM_PRESENTATION (\d+)",
        read(ROOT / "src/acs_source/_imports/uhdt.acs")).group(1))
    if len(rows) > capacity:
        print(f"FAIL presentation capacity: {len(rows)} rows > {capacity}")
        fails += 1
    for cls, expected in morph_additions.items():
        if rows.get(cls) != expected:
            print(f"FAIL morph presentation {cls}: {rows.get(cls)!r} != {expected!r}")
            fails += 1
    defined: set[str] = set()
    for path, call in ((SURVDEFS, "DefineSurvivor"), (BOSSDEFS, "DefineBoss"), (EYEDEFS, "DefineDemoneye")):
        defined |= {a for a in re.findall(rf"{call}\(\s*-?\d+,\s*\"([^\"]+)\"", read(path)) if a}
    # A row without a definition must be a morph body: it must have no portrait
    # (so nothing can be drawn for it in the teammate bar) and must carry a
    # scoreboard icon.  Anything else is a registration that lost its identity.
    for cls in rows:
        if cls in defined or cls in morph_additions:
            continue
        if rows[cls][1] != "" or rows[cls][2] == "":
            print(f"FAIL {cls}: no Define* registration and not a scoreboard-only morph body")
            fails += 1

    # 4. UIX PBMug_<Class> scripts must still agree with the presentation
    #    portraits (phase 2 keeps them as the fallback).
    mug_re = re.compile(r'script\s+"PBMug_([A-Za-z0-9_]+)"\s*\(int tid\)\s*\{SetResultValue\("([^"]+)"\);\}')
    mugs = dict(mug_re.findall(read(UIXMUGS)))
    # Viewer effects retain the registered base portrait; verify that identity
    # rather than treating their PBMug script as a missing static fallback.
    effect_re = re.compile(
        r'script\s+"PBMug_([A-Za-z0-9_]+)"\s*\(int tid\)\s*'
        r'\{SetResultValue\(UH_GemBankerPortrait\("([^"]+)"\)\);\}'
    )
    effect_mugs = dict(effect_re.findall(read(UIXMUGS)))
    if effect_mugs != {"GemBanker": "UB022MUG"}:
        print(f"FAIL GemBanker UIX base portrait: {effect_mugs}")
        fails += 1
    mugs.update(effect_mugs)
    # MegaMan killfeed faces are dynamic: delegate to stock UIX PBSKINS so
    # visible skins and pbskins_maestromug retain their original behaviour.
    dynamic_re = re.compile(
        r'script\s+"PBMug_([A-Za-z0-9_]+)"\s*\(int tid\)\s*'
        r'\{SetResultValue\(ACS_NamedExecuteWithResult\("PBMug_Megaman", tid\)\);\}'
    )
    dynamic = set(dynamic_re.findall(read(UIXMUGS)))
    if dynamic != {"MegaManU", "MegaManUShiny"}:
        print(f"FAIL MegaMan UIX skin delegates: {sorted(dynamic)}")
        fails += 1
    markers = read(ROOT / "src/actors/compat/uix/MegaManU_Mugshot.dec")
    for cls in dynamic:
        if not re.search(rf'actor\s+PBMug_{cls}\s*\{{', markers):
            print(f"FAIL missing UIX skin marker: {cls}")
            fails += 1
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
    # A row with a portrait but no PBMug_ script would silently lose its UIX
    # face; only the scoreboard-only morph may legitimately lack one.
    for cls in rows:
        if cls in mugs or cls in dynamic:
            continue
        if rows[cls][1] == "":
            continue
        print(f"note: {cls}: presentation portrait has no PBMug_ script (UIX fallback empty)")

    if fails:
        print(f"team presentation check FAILED ({fails} problem(s))")
        return 1
    print(f"ok: {len(portraits)} historical presentation rows preserved; {len(morph_additions)} morph addition verified")
    print(f"ok: {len(mugs)} UIX PBMug scripts agree")
    return 0


if __name__ == "__main__":
    sys.exit(main())

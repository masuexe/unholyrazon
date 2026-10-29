#!/usr/bin/env python3
"""Verify that every lump, library and patch target this PK3 names exists.

A rename, a move or a deleted file inside src/ can break a reference that only
fails when the engine loads the PK3.  The engine then reports one line in the
console (or nothing at all) and the release ships broken.  This checker guards
these cross-reference classes:

1. DECORATE #include targets, starting at src/DECORATE and walking every
   .dec/.txt file under src/.
2. ACS #include targets, using the include search order of
   tools/compile-acs.sh.
3. src/LOADACS library names against every #library declaration in
   src/acs_source, in both directions.
4. src/KEYCONF player classes against DECORATE actor declarations.
5. TEXTURES Patch targets against files under src/sprites, src/graphics and
   src/patches, and against the TEXTURES definitions themselves.

Case rule: Zandronum resolves lump names without case, but git, a Linux
checkout and a ZIP entry list are case sensitive.  A reference that resolves
only when case is ignored is therefore reported as a warning, not as a
failure: it works in the engine and it is still a defect in the repository.

External rule: some names are supplied by the base game PK3 or by the engine
(TNT1A0).  gate.py --fast must run in a fresh clone with no WADs, so those names
are frozen constants below.  They were first extracted from the v6b packages on
2026-10-26 and re-verified against ../wads/mm8bdm-v6c.pk3 on 2026-10-29: every
frozen name is present in v6c. tools/check_base_baselines.py keeps that true.
A new external name must be added here on purpose, which keeps the dependency
visible.

KNOWN_UNRESOLVED_GRAPHICS holds a Patch target that is missing from both the
repository and the base game.  It is empty at HEAD.  A real finding belongs
there only with evidence; --strict turns warnings, including that list, into
failures.

Run:  python3 tools/check_lump_integrity.py [--strict]
Exit: 0 clean, 1 findings, 2 usage error.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

DECORATE_SUFFIXES = {".dec", ".txt", ".decorate"}
INCLUDE_RE = re.compile(r'(?m)^[ 	]*#include[ 	]+"([^"]+)"')
LIBRARY_RE = re.compile(r'(?m)^[ 	]*#library[ 	]+"([^"]+)"')
PLAYERCLASS_RE = re.compile(r'(?im)^[ 	]*addplayerclass[ 	]+([A-Za-z_][A-Za-z0-9_]*)')
ACTOR_DECL_RE = re.compile(r'(?im)^[ 	]*actor[ 	]+([A-Za-z_][A-Za-z0-9_]*)')
ACTOR_PARENT_RE = re.compile(
    r'(?im)^[ 	]*actor[ 	]+([A-Za-z_][A-Za-z0-9_]*)[ 	]*:[ 	]*'
    r'([A-Za-z_][A-Za-z0-9_]*)')
TEXTURE_DEF_RE = re.compile(
    r'(?im)^[ 	]*(?:sprite|texture|graphic|walltexture|flat|font)[ 	]+'
    r'("[^"]*"|[^\s,]+)[ 	]*,')
PATCH_RE = re.compile(r'(?i)\bPatch[ 	]+("[^"]*"|[^\s,}]+)')

# ACC ships these standard headers next to the compiler; they are not in src/.
ACC_TOOLCHAIN_INCLUDES = frozenset({"zcommon.acs", "zdefs.acs"})

# Include search order from tools/compile-acs.sh (the -i list plus the per
# library extra directories).  The directory of the including file is always
# searched first.
ACS_INCLUDE_DIRS = (
    "src/acs_source/v6b_overrides/_includes/common",
    "src/acs_source/v6b_overrides/_includes/mod_api",
    "src/acs_source/_includes/mod_api",
    "src/acs_source/_imports",
    "src/acs_source/v6b_overrides/_imports",
    "src/acs_source/unholy",
    "src/acs_source/compat/mods/uix",
    "src/acs_source/compat/mods/uix/_uix_v3bh",
)

# DECORATE include targets that only the base game PK3 provides.  AGENTS.md
# documents this one: the 100 classbase slot files are a v6c asset.
EXTERNAL_INCLUDES = {
    "actors/player/classbase/customslots/_classbaseslot.txt": (
        "base game v6c supplies the customslots/_classbaseslot.txt chain"
    ),
}

# #library names that this PK3 ships but deliberately does not list in
# src/LOADACS.  Sources: tools/compile-acs.sh comments, src/acs_source READMEs,
# AGENTS.md, and the LOADACS lumps of the base game and of the addons.
NOT_IN_LOADACS = {
    "uh_acsutils": "import-only helper library (#import)",
    "uh_log": "import-only logging library (#import)",
    "uhbeset": "import-only host settings, compiled as UHBESET.o",
    "uhbsset": "import-only host settings, compiled as UHBSSET.o",
    "uhdbcrud": "import-only identity CRUD, imported by uhaddr",
    "uhcombdb": "import-only boss combo registry, compiled as UHCOMBDB.o",
    "wheeldt": "import-only UIX wheel table, imported by UIXITEMS/UIXWEAP",
    "core8bdt": "v6b override imported by other libraries (CORE8BDT.o)",
    "dtaddr": "v6b override; the base game LOADACS loads DTADDR",
    "wepacs": "v6c shared ammo-capacity shadow; loaded by the base LOADACS",
    "barclear": "v6b override; the base game LOADACS loads BARCLEAR",
    "barhndle": "v6b override; the base game LOADACS loads BARHNDLE",
    "colotrns": "v6b override; the base game LOADACS loads COLOTRNS",
    "footchec": "v6b override; the base game LOADACS loads FOOTCHEC",
    "jumpcanc": "v6c override; the base game LOADACS loads JUMPCANC",
    "uicommon.acs": "base v6c import declarations; UICOMMON.o is supplied by the base package",
    "uiteamit": "v6c team-display shadow; loaded by the base LOADACS",
    "mugshots": "v6c mugshot resolver shadow; loaded by the base LOADACS",
    "corejump": "v6c override; the base game LOADACS loads COREJUMP",
    "projtran": "v6b override; the base game LOADACS loads PROJTRAN",
    "teamcol": "v6b override; the base game LOADACS loads TEAMCOL",
    "uixitems": "UIX shadow library, loaded by 8bdm-uix-v3bh",
    "uixteam": "UIX shadow library, loaded by 8bdm-uix-v3bh",
    "uixweap": "UIX shadow library, loaded by 8bdm-uix-v3bh",
    "pingbutt": "PingButton addon library (PNGBUTTN.o) with its own LOADACS",
    "wephide": "miscfixes addon library (WEPHIDE.o) with its own LOADACS",
}

# Engine built-in graphics.  TNT1A0 is the invisible sprite frame that every
# Doom-lineage engine always provides.
ENGINE_BUILTIN_GRAPHICS = frozenset({"TNT1A0"})

BASE_GAME_GRAPHICS = frozenset("""
    ASSTBARP ASSTVARP BAREMPTY BARENERG BUSTB0 BUSTC0
    BUSTD0 EMPTA0 FACE0 FACE1 FACE103 FACE104
    FACE105 FACE106 FACE107 FACE108 FACE109 FACE11
    FACE110 FACE111 FACE113 FACE12 FACE128 FACE129
    FACE13 FACE130 FACE131 FACE135 FACE137 FACE138
    FACE139 FACE14 FACE140 FACE141 FACE142 FACE143
    FACE144 FACE146 FACE147 FACE148 FACE149 FACE15
    FACE150 FACE151 FACE152 FACE153 FACE154 FACE155
    FACE16 FACE17 FACE176 FACE18 FACE181 FACE182
    FACE183 FACE184 FACE185 FACE186 FACE187 FACE188
    FACE189 FACE190 FACE191 FACE192 FACE193 FACE194
    FACE195 FACE196 FACE197 FACE198 FACE199 FACE2
    FACE200 FACE21 FACE22 FACE23 FACE24 FACE25
    FACE26 FACE27 FACE28 FACE3 FACE30 FACE31
    FACE32 FACE33 FACE34 FACE35 FACE36 FACE37
    FACE38 FACE4 FACE41 FACE42 FACE43 FACE44
    FACE45 FACE46 FACE47 FACE48 FACE49 FACE5
    FACE50 FACE51 FACE52 FACE53 FACE54 FACE55
    FACE56 FACE57 FACE58 FACE6 FACE61 FACE62
    FACE63 FACE64 FACE65 FACE66 FACE67 FACE68
    FACE7 FACE73 FACE74 FACE75 FACE76 FACE77
    FACE78 FACE79 FACE80 FACE81 FACE82 FACE85
    FACE89 FACE90 FACE91 FACE92 FACE93 FACE94
    FACE96 FACE97 FACE98 FACE99 HSPRA0 HSPRB0
    HSPRC0 HSPRD0 LEAFA0 LEAFB0 LEAFC0 LEAFD0
    LEAFE0 LEAFF0 LEAFG0 LEAFH0 LEAFI0 LEAFJ0
    LEAFK0 MAESBACK MGMBG0 MOBLK999 MOBLU999 MOCYN999
    SCLAA0 SCLAB0 SCLAC0 STYS8BD0 STYS8BD1 STYS8BD2
    STYS8BD3 STYS8BD4 STYS8BD5 STYS8BD6 STYS8BD7 STYS8BD8
    STYS8BD9 ST_RA0 ST_RB0 ST_RC0 ST_RD0 ST_RE0
    ST_RF0 ST_RG0 ST_RH0 ST_RI0 ST_RJ0 ST_RK0
    ST_RL0 ST_RM0 ST_RN0 ST_RO0 ST_RP0 ST_RQ0
    ST_RR0 ST_RS0 ST_RT0 ST_RU0 ST_RV0 ST_RW0
    ST_RX0 ST_RY0 ST_RZ0 ST_R[0 VAREMPTY WEA7J0
    WEAPX0
""".split())

# No known unresolved sprite at HEAD: every non-local Patch target is a base
# game or engine lump.  A real finding belongs here only with evidence that the
# base game does not provide the name either.
KNOWN_UNRESOLVED_GRAPHICS = frozenset()

_WALK = None
_INDEX = None
_DECORATE = None


def read_text(path):
    return path.read_text(encoding="utf-8", errors="replace")


def strip_comments(text):
    """Remove comments, but keep the line count so line numbers stay valid."""
    text = re.sub(
        r'/\*.*?\*/',
        lambda match: re.sub(r'[^\n]', '', match.group(0)),
        text, flags=re.S)
    return re.sub(r'//[^\n]*', '', text)


def walk_src():
    """Every file under src/, listed once with os.walk (rglob is slower)."""
    global _WALK
    if _WALK is None:
        files = []
        for dirpath, _dirnames, names in os.walk(SRC):
            base = Path(dirpath)
            files.extend(base / name for name in names)
        _WALK = files
    return _WALK


def src_file_index():
    """Map lowercase src-relative path to Path, for case-only mismatch reports."""
    global _INDEX
    if _INDEX is None:
        index = {}
        for path in walk_src():
            index[path.relative_to(SRC).as_posix().lower()] = path
        _INDEX = index
    return _INDEX


def decorate_files():
    """Every file the engine or a DECORATE include may parse."""
    files = [p for p in walk_src() if p.suffix.lower() in DECORATE_SUFFIXES]
    files.extend(p for p in SRC.glob("DECORATE*") if p.is_file())
    return files


def decorate_scan():
    """One pass: include lines, actor declarations and actor parents."""
    global _DECORATE
    if _DECORATE is None:
        includes = []
        actors = {}
        parents = {}
        for path in decorate_files():
            text = strip_comments(read_text(path))
            rel = path.relative_to(ROOT).as_posix()
            for match in INCLUDE_RE.finditer(text):
                includes.append((path, match.group(1),
                                 text.count("\n", 0, match.start()) + 1))
            for match in ACTOR_DECL_RE.finditer(text):
                actors[match.group(1).lower()] = rel
            for match in ACTOR_PARENT_RE.finditer(text):
                parents[match.group(1).lower()] = match.group(2).lower()
        _DECORATE = (includes, actors, parents)
    return _DECORATE


def resolve_include(including, name):
    """Resolve #include as ACC does: including directory first, then src root."""
    for candidate in (including.parent / name, SRC / name):
        if candidate.is_file():
            return candidate
    return None


def case_variant(including, name):
    """Return the file that matches the include only when case is ignored."""
    index = src_file_index()
    for candidate in (including.parent / name, SRC / name):
        try:
            key = candidate.resolve().relative_to(SRC).as_posix().lower()
        except (ValueError, OSError):
            continue
        if key in index:
            return index[key]
    return None


def check_includes(problems, warnings):
    """DECORATE include graph: every target must be a file in src/."""
    includes, _actors, _parents = decorate_scan()
    for path, name, lineno in includes:
        if resolve_include(path, name) is not None:
            continue
        if name in EXTERNAL_INCLUDES:
            continue
        where = path.relative_to(ROOT).as_posix()
        variant = case_variant(path, name)
        if variant is not None:
            warnings.append(
                "case-only include: {!r} in {}:{} resolves as {}".format(
                    name, where, lineno, variant.relative_to(ROOT).as_posix()))
        else:
            problems.append(
                "missing include: {!r} in {}:{}".format(name, where, lineno))
    return len(includes)


def check_acs_includes(problems, warnings):
    """ACS include graph: every fragment must resolve in a compile include dir."""
    files = sorted(SRC.joinpath("acs_source").rglob("*.acs"))
    roots = [ROOT / rel for rel in ACS_INCLUDE_DIRS]
    total = 0
    toolchain = 0
    for path in files:
        data = path.read_bytes()
        if b"#include" not in data:
            continue
        text = strip_comments(data.decode("utf-8", errors="replace"))
        where = path.relative_to(ROOT).as_posix()
        for match in INCLUDE_RE.finditer(text):
            total += 1
            name = match.group(1)
            if name.lower() in ACC_TOOLCHAIN_INCLUDES:
                toolchain += 1
                continue
            if (path.parent / name).is_file():
                continue
            if any((root / name).is_file() for root in roots):
                continue
            lineno = text.count("\n", 0, match.start()) + 1
            variant = case_variant(path, name)
            if variant is None:
                index = src_file_index()
                for root in roots:
                    try:
                        key = (root / name).resolve().relative_to(SRC).as_posix().lower()
                    except (ValueError, OSError):
                        continue
                    if key in index:
                        variant = index[key]
                        break
            if variant is not None:
                warnings.append(
                    "case-only ACS include: {!r} in {}:{} resolves as {}".format(
                        name, where, lineno, variant.relative_to(ROOT).as_posix()))
            else:
                problems.append(
                    "missing ACS include: {!r} in {}:{}".format(name, where, lineno))
    return total, toolchain


def loadacs_entries():
    entries = []
    for lineno, line in enumerate(read_text(SRC / "LOADACS").splitlines(), 1):
        name = line.split("//")[0].strip()
        if name:
            entries.append((lineno, name))
    return entries


def declared_libraries():
    declarations = {}
    for path in sorted(SRC.joinpath("acs_source").rglob("*.acs")):
        data = path.read_bytes()
        if b"#library" not in data:
            continue
        text = strip_comments(data.decode("utf-8", errors="replace"))
        for match in LIBRARY_RE.finditer(text):
            lineno = text.count("\n", 0, match.start()) + 1
            declarations.setdefault(match.group(1).lower(), []).append(
                (path.relative_to(ROOT).as_posix(), lineno))
    return declarations


def check_libraries(problems, _warnings):
    """LOADACS <-> #library declarations, in both directions."""
    entries = loadacs_entries()
    declarations = declared_libraries()
    listed = {}
    for lineno, name in entries:
        key = name.lower()
        if key in listed:
            problems.append(
                "duplicate LOADACS entry: {!r} on lines {} and {}".format(
                    name, listed[key], lineno))
            continue
        listed[key] = lineno
        if key not in declarations:
            problems.append(
                "LOADACS names {!r} (line {}) but no #library declares it".format(
                    name, lineno))
    for name, sites in sorted(declarations.items()):
        if len(sites) > 1:
            problems.append(
                "#library {!r} is declared {} times, first at {}:{}".format(
                    name, len(sites), sites[0][0], sites[0][1]))
        if name in listed or name in NOT_IN_LOADACS:
            continue
        problems.append(
            "#library {!r} ({}:{}) is not in src/LOADACS and has no documented "
            "import-only reason".format(name, sites[0][0], sites[0][1]))
    return len(entries), len(declarations)


def check_keyconf(problems, warnings):
    """Each addplayerclass needs an actor; a derived class is a warning."""
    text = strip_comments(read_text(SRC / "KEYCONF"))
    classes = []
    for match in PLAYERCLASS_RE.finditer(text):
        lineno = text.count("\n", 0, match.start()) + 1
        classes.append((lineno, match.group(1)))
    _includes, actors, parents = decorate_scan()
    registered = set()
    for lineno, name in classes:
        key = name.lower()
        if key in registered:
            problems.append(
                "duplicate addplayerclass {!r} in src/KEYCONF:{}".format(name, lineno))
        registered.add(key)
        if key not in actors:
            problems.append(
                "addplayerclass {!r} (src/KEYCONF:{}) has no 'actor {}' "
                "declaration under src/actors".format(name, lineno, name))
    derived = sorted(name for name, parent in parents.items()
                     if parent in registered and name not in registered)
    if derived:
        warnings.append(
            "{} actor(s) inherit a KEYCONF player class but are not registered "
            "in KEYCONF (verify they are intended morph/shiny bodies): "
            "{}".format(len(derived), " ".join(derived)))
    return len(classes)


def graphics_index():
    """Lump name to path for every graphic file the PK3 ships."""
    files = {}
    prefixes = tuple(str(SRC / directory) + os.sep
                     for directory in ("sprites", "graphics", "patches"))
    for path in walk_src():
        if str(path).startswith(prefixes):
            files.setdefault(path.stem.upper(), path)
    return files


def check_textures(problems, warnings):
    """Every TEXTURES Patch target must resolve locally or in the base game."""
    textures = sorted(SRC.glob("TEXTURES*"))
    if not textures:
        problems.append("no TEXTURES lumps found under src/")
        return 0
    graphics = graphics_index()
    definitions = set()
    references = []
    for path in textures:
        text = strip_comments(read_text(path))
        rel = path.relative_to(ROOT).as_posix()
        for match in TEXTURE_DEF_RE.finditer(text):
            definitions.add(match.group(1).strip('"').upper())
        for match in PATCH_RE.finditer(text):
            lineno = text.count("\n", 0, match.start()) + 1
            references.append((rel, lineno, match.group(1).strip('"')))
    local = set(graphics) | definitions
    for rel, lineno, name in references:
        upper = name.upper()
        if "%" in name or "$" in name:
            continue  # wildcard patch: matches a frame range, not one lump
        if upper in local:
            continue
        if upper in BASE_GAME_GRAPHICS or upper in ENGINE_BUILTIN_GRAPHICS:
            continue
        if upper in KNOWN_UNRESOLVED_GRAPHICS:
            warnings.append(
                "known unresolved sprite: {}:{} Patch {} (no such lump in the "
                "base game either)".format(rel, lineno, name))
            continue
        problems.append(
            "missing sprite/graphic: {}:{} Patch {} (no file under src/sprites, "
            "src/graphics or src/patches and no TEXTURES definition)".format(
                rel, lineno, name))
    return len(references)


def main(argv):
    parser = argparse.ArgumentParser(
        description="Verify lump and library cross references.",
        epilog=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--strict", action="store_true",
                        help="fail on warnings, including known latent defects")
    args = parser.parse_args(argv[1:])

    for required in (SRC / "DECORATE", SRC / "LOADACS", SRC / "KEYCONF"):
        if not required.is_file():
            print("error: missing required file {}".format(
                required.relative_to(ROOT)), file=sys.stderr)
            return 2

    problems = []
    warnings = []

    includes = check_includes(problems, warnings)
    acs_includes, toolchain = check_acs_includes(problems, warnings)
    loadacs_count, library_count = check_libraries(problems, warnings)
    class_count = check_keyconf(problems, warnings)
    patch_count = check_textures(problems, warnings)

    print("DECORATE include targets:  {}".format(includes))
    print("ACS include targets:       {} (+{} ACC toolchain headers)".format(
        acs_includes, toolchain))
    print("LOADACS entries:           {} ({} #library declarations)".format(
        loadacs_count, library_count))
    print("KEYCONF player classes:    {}".format(class_count))
    print("TEXTURES Patch targets:    {}".format(patch_count))

    for warning in warnings:
        print("warn: {}".format(warning))
    for problem in problems:
        print("FAIL: {}".format(problem))

    total = includes + acs_includes + loadacs_count + class_count + patch_count
    if problems or (args.strict and warnings):
        print()
        print("{} problem(s), {} warning(s) across {} reference(s)".format(
            len(problems), len(warnings), total))
        return 1
    print("ok: {} references resolve, {} warning(s)".format(total, len(warnings)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

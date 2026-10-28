#!/usr/bin/env python3
"""Guard the boss friendly-fire damage-type contract.

The trap: a Boss player carries PowerProtectBoss, whose damagefactor list is the
ONLY friendly-fire protection in this mod.  A boss attack that carries a damage
type missing from that list hurts Boss teammates, and nothing reports it: the
engine has no idea the mod wanted immunity, ACS sees normal damage, and the
victim just loses health.  That is the shipped Tidal Tito bug (commit 3b1ec3b3):
TidalTitoExplosion had no DamageType at all, so its A_Explode splash ignored
PowerProtectBoss and damaged Boss teammates in multi-boss rounds.  The fix gave
the explosion DamageType "TidalMaster" and the jet wave "TidalMasterThrust",
both already present in PowerProtectBoss.

The same contract applies to Demoneyes, which carry PowerProtectEye (and
PowerProtectPDC for the clone damage type).

This checker parses the protection tables out of the actor DECORATE (it does not
trust a hand-copied list), resolves each boss/eye-tree actor's damage type
through its in-src inheritance chain, and fails on:

  A. a boss/eye-tree actor that deals damage (A_Explode, or a non-zero Damage /
     ExplosionDamage / RangeDamage / MeleeDamage literal) but resolves no
     DamageType through its in-src chain - the Tidal Tito shape;
  B. a boss/eye-tree damage type that its protection table does not cover;
  C. a protection-table entry that no actor in src/actors assigns, i.e. a rule
     that outlived a damage-type rename.

Rules B and C already found real pre-existing gaps when this checker was
written, so those are pinned in KNOWN_UNPROTECTED / KNOWN_STALE_ENTRIES with the
evidence for each group.  A pinned entry never hides anything silently: the
summary prints the counts every run, --list-gaps prints every pinned entry, and
the checker FAILS if a pinned gap disappears (remove it from the baseline: the
baseline may only shrink) or if a new gap appears.  Fixing the code is always
preferred over editing the baseline; the baseline exists because the fixes are
behaviour changes in src/actors and belong to a gameplay change, not to a
checker.

Run:  python3 tools/check_damage_types.py [--list-gaps] [--root PATH]
Exit: 0 clean, 1 findings, 2 usage/parse error.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SUFFIXES = {".dec", ".txt"}
PROTECTION_BASE = "powerprotection"
# Per actor tree: (protection tables that apply, baseline of known-uncovered types).
TREE_TABLES = {
    "src/actors/classes/bosses": ("PowerProtectBoss",),
    "src/actors/classes/eyes": ("PowerProtectEye", "PowerProtectPDC"),
}

ACTOR_RE = re.compile(
    r"(?im)^[ \t]*actor\s+([A-Za-z0-9_]+)(?:\s*:\s*([A-Za-z0-9_]+))?"
)
STATES_RE = re.compile(r"(?im)^[ \t]*States\s*\{")
DAMAGEFACTOR_RE = re.compile(r'(?i)damagefactor\s+"([^"]+)"')
DAMAGETYPE_RE = re.compile(r'(?im)^[ \t]*DamageType\s+"?([A-Za-z0-9_]+)"?')
DAMAGE_LITERAL_RE = re.compile(
    r"(?im)^[ \t]*(?:Damage|ExplosionDamage|RangeDamage|MeleeDamage)\s*\(?\s*(-?\d+)"
)
EXPLODE_RE = re.compile(r"\bA_Explode\s*\(", re.IGNORECASE)

# Pinned gaps: damage types a boss/eye tree uses that its protection table does
# not list.  Every one predates this checker.  Empty set means "none known".
KNOWN_UNPROTECTED = frozenset(
    word.lower()
    for word in """
    alienjrtimestop aspblindjr aspflingjr aspmagicjr
    aspstunjr balladegb_mine balladegb_shot balladegb_ultimateexplode
    eyelentoeyebaton genericcash kamikazeeye majorgasm
    mosquitoeye plaineye protobuster protobuster2
    protobuster3 richeye richgasm tankeye
    winddemoneyefling
""".split()
)
# Pinned gaps: boss/eye actors that deal damage but resolve no DamageType.
KNOWN_NO_DAMAGETYPE = frozenset(
    word.lower()
    for word in """
    ccbyourmates floovydiesformelink floovystandwatcher gbeast_heateruptionflamepulse_p
    mgzerozapdriveshot pharaoh4midesperateshotexplosion sftricrystalfireball1pulse_p sovietchill_radiuspulse_p
    sovietcoldbomberpulse_p sue_chillingbreezepulse_p veryfunorb wahweeshockexplosion
    weakhorse
""".split()
)
# Pinned gaps: protection-table entries that no src/actors actor assigns.
KNOWN_STALE_ENTRIES = frozenset(
    word.lower()
    for word in """
    aspelecmagicstun balrog_toss blackdevilgasm bombereyefire
    businesseye demoneye explosiveeye fbeastfuryswipestun
    fbeaststun gbeastfuryswipestun majorgrenadepoison richeyecash
    sfmadfire shadowbossmelee shadowmanslicedice sutokastun
    zankokunahell
""".split()
)


COMMENT_RE = re.compile(
    '"(?:[^"\\\\]|\\\\.)*"' + r"|//[^\n]*" + r"|/\*.*?(?:\*/|\Z)",
    re.DOTALL,
)


def strip_comments(text: str) -> str:
    """Remove // and /* */ comments, keep line numbering, keep strings."""

    def replace(match):
        token = match.group(0)
        if token.startswith('"'):
            return token
        return "\n" * token.count("\n")

    return COMMENT_RE.sub(replace, text)


def iter_actor_files(actor_root: Path):
    for path in sorted(actor_root.rglob("*")):
        if path.suffix.lower() in SUFFIXES:
            yield path


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def matching_brace(text: str, start: int) -> int:
    """Index just past the brace block that starts at or after 'start'."""
    depth = 0
    index = start
    while index < len(text):
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index + 1
        index += 1
    return len(text)


def actor_bodies(text: str):
    """Yield (name, parent, line, body) for every actor declaration in text."""
    matches = list(ACTOR_RE.finditer(text))
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        yield (
            match.group(1),
            match.group(2),
            text.count("\n", 0, match.start()) + 1,
            text[match.end() : end],
        )


def parse_tables(actor_root: Path):
    """Return {table_lower: (display, types, path, line)} for PowerProtection actors."""
    tables = {}
    for path in iter_actor_files(actor_root):
        text = strip_comments(read_text(path))
        for name, parent, line, body in actor_bodies(text):
            if not parent or parent.lower() != PROTECTION_BASE:
                continue
            types = {match.group(1).lower() for match in DAMAGEFACTOR_RE.finditer(body)}
            tables[name.lower()] = (name, types, path, line)
    return tables


def parse_actors(actor_root: Path):
    """Return ({name_lower: (decl, own_damage_type)}, order)."""
    decls = {}
    order = []
    for path in iter_actor_files(actor_root):
        text = strip_comments(read_text(path))
        for name, parent, line, body in actor_bodies(text):
            match = DAMAGETYPE_RE.search(body)
            decl = {
                "name": name,
                "parent": parent,
                "path": path,
                "line": line,
                "body": body,
            }
            decls.setdefault(name.lower(), decl)
            order.append((decl, match.group(1) if match else None))
    return decls, order


def chain(decls, name: str):
    out = []
    current = name.lower()
    guard = 0
    while current and current in decls and guard < 64:
        out.append(current)
        parent = decls[current]["parent"]
        current = parent.lower() if parent else ""
        guard += 1
    if current:
        out.append(current)
    return out


def own_damage_type(decl, declared: dict):
    declared_type = declared.get(decl["name"].lower())
    return declared_type


def resolve_damage_type(decls, declared, name: str):
    for ancestor in chain(decls, name):
        if ancestor in declared:
            return declared[ancestor]
    return None


def deals_damage(body: str) -> bool:
    for match in DAMAGE_LITERAL_RE.finditer(body):
        if int(match.group(1)) != 0:
            return True
    return bool(EXPLODE_RE.search(body))


def tree_for(path: Path, root: Path):
    try:
        relative = path.relative_to(root).as_posix()
    except ValueError:
        return None
    for prefix in TREE_TABLES:
        if relative.startswith(prefix + "/"):
            return prefix
    return None


def main(argv) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--root", type=Path, default=ROOT, help="repository root")
    parser.add_argument(
        "--list-gaps",
        action="store_true",
        help="print every pinned pre-existing gap (baseline audit)",
    )
    args = parser.parse_args(argv[1:])

    root = args.root.resolve()
    actor_root = root / "src" / "actors"
    if not actor_root.is_dir():
        print(f"error: missing {actor_root}", file=sys.stderr)
        return 2

    tables = parse_tables(actor_root)
    if not tables:
        print("error: no PowerProtection actors found in src/actors", file=sys.stderr)
        return 2
    for tree, names in TREE_TABLES.items():
        for name in names:
            if name.lower() not in tables:
                print(f"error: missing protection actor {name}", file=sys.stderr)
                return 2

    decls, order = parse_actors(actor_root)
    declared = {}
    for decl, damage_type in order:
        if damage_type:
            declared.setdefault(decl["name"].lower(), damage_type)
    if not declared:
        print("error: no DamageType assignments found", file=sys.stderr)
        return 2

    covered = {name.lower(): tables[name.lower()][1] for tree in TREE_TABLES.values()
               for name in tree}
    assigned_everywhere = {item.lower() for item in declared.values()}

    findings = 0
    no_type = []
    uncovered = []
    stale = []
    damage_actors = 0
    tree_actors = 0

    for decl, _damage_type in order:
        tree = tree_for(decl["path"], root)
        if tree is None:
            continue
        tree_actors += 1
        damages = deals_damage(decl["body"])
        if damages:
            damage_actors += 1
        resolved = resolve_damage_type(decls, declared, decl["name"])
        if resolved is None:
            # Guard A shape: it delivers damage itself but names no type, so no
            # protection rule can ever match its splash.
            if damages:
                no_type.append(decl)
            continue
        protection = set()
        for table in TREE_TABLES[tree]:
            protection |= covered.get(table.lower(), set())
        if resolved.lower() not in protection:
            uncovered.append((decl, resolved))

    # Guard A: damage dealer without a damage type.
    new_no_type = [
        decl for decl in no_type if decl["name"].lower() not in KNOWN_NO_DAMAGETYPE
    ]
    for decl in new_no_type:
        findings += 1
        print(
            f"{decl['path'].relative_to(root)}:{decl['line']}: {decl['name']}: "
            f"boss damage dealer resolves no DamageType (boss teammates take "
            f"unprotected splash damage)"
        )

    # Guard B: damage type the protection table does not cover.
    new_uncovered = [
        (decl, resolved)
        for decl, resolved in uncovered
        if resolved.lower() not in KNOWN_UNPROTECTED
    ]
    for decl, resolved in new_uncovered:
        findings += 1
        print(
            f"{decl['path'].relative_to(root)}:{decl['line']}: {decl['name']}: "
            f"DamageType '{resolved}' is not in the boss/eye protection table"
        )

    # Guard C: protection entry that no actor assigns any more.
    referenced_tables = sorted(
        {name for names in TREE_TABLES.values() for name in names}
    )
    for table_name in referenced_tables:
        display, types, path, line = tables[table_name.lower()]
        for entry in sorted(types):
            if entry in assigned_everywhere:
                continue
            if entry in KNOWN_STALE_ENTRIES:
                stale.append((display, entry, path, line))
                continue
            findings += 1
            print(
                f"{path.relative_to(root)}:{line}: {display}: damagefactor "
                f"'{entry}' matches no DamageType in src/actors"
            )

    # Guard D: a pinned gap that no longer exists means the baseline is stale.
    active_no_type = {decl["name"].lower() for decl in no_type}
    for name in sorted(KNOWN_NO_DAMAGETYPE - active_no_type):
        findings += 1
        print(f"baseline is stale: '{name}' now resolves a DamageType; "
              f"remove it from KNOWN_NO_DAMAGETYPE")
    active_uncovered = {resolved.lower() for _decl, resolved in uncovered}
    for name in sorted(KNOWN_UNPROTECTED - active_uncovered):
        findings += 1
        print(f"baseline is stale: '{name}' is now covered; "
              f"remove it from KNOWN_UNPROTECTED")
    table_entries = {
        entry
        for table_name in referenced_tables
        for entry in tables[table_name.lower()][1]
    }
    for name in sorted(KNOWN_STALE_ENTRIES):
        if name not in table_entries:
            findings += 1
            print(f"baseline is stale: '{name}' is no longer a protection-table "
                  f"entry; remove it from KNOWN_STALE_ENTRIES")
        elif name in assigned_everywhere:
            findings += 1
            print(f"baseline is stale: '{name}' is assigned now; "
                  f"remove it from KNOWN_STALE_ENTRIES")

    if args.list_gaps:
        print("\npinned pre-existing gaps:")
        print("  no DamageType (boss damage dealer):")
        for decl in sorted(no_type, key=lambda item: item["name"].lower()):
            print(f"    {decl['name']:34} "
                  f"{decl['path'].relative_to(root)}:{decl['line']}")
        print("  damage type not covered by the protection table:")
        for decl, resolved in sorted(uncovered, key=lambda item: item[1].lower()):
            print(f"    {resolved:34} {decl['name']:30} "
                  f"{decl['path'].relative_to(root)}:{decl['line']}")
        print("  protection entries that no actor assigns:")
        for display, entry, path, line in stale:
            print(f"    {entry:34} {display} at {path.relative_to(root)}:{line}")

    print(
        "damage types: "
        f"{len(tables)} protection table(s), {len(declared)} assigned type(s), "
        f"{tree_actors} boss/eye actor(s), {damage_actors} damage dealer(s), "
        f"known gaps: {len(KNOWN_NO_DAMAGETYPE)} no-type / "
        f"{len(KNOWN_UNPROTECTED)} uncovered / {len(KNOWN_STALE_ENTRIES)} stale"
    )
    if findings:
        print(f"\n{findings} damage-type contract finding(s)")
        return 1
    print("ok: boss/eye damage types honour the friendly-fire protection tables")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

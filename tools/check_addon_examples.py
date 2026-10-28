#!/usr/bin/env python3
"""Prove every example addon under examples/ is a working, self-consistent package.

The examples are the working recipes for the public addon API: an author copies
one and expects it to load.  A static ACS compile alone proves almost nothing
about a PK3, so this checker ties the four package pieces together and then
compiles the ACS for real:

1.  LOADACS names a library that the package's own .acs declares with #library
    (and every declared library is listed in LOADACS).  A renamed or missing
    entry makes the addon load nothing at all.
2.  Every #include/#import in the addon's ACS resolves with the include search
    order tools/compile-acs.sh documents (plus the -i directories the example's
    own README documents).  ACC resolves by name; a stale path is invisible
    until someone compiles the example.
3.  The ACS compiles with the local ACC into a temporary directory.  This check
    never writes into examples/: the acs/ trees are gitignored local build
    artifacts (.gitignore **/acs/), and a gate that overwrote them would hide a
    stale object instead of reporting it.
4.  When the example's local acs/<library>.o build artifact is present, it is
    byte-identical to the object built from the current source.  ACC is
    deterministic and path-independent here, so a difference means whoever
    packages this tree would ship bytecode that no longer matches its source.
    A missing artifact is not a failure: a fresh clone has none, and the --fast
    gate must stay portable.
5.  Every DECORATE parent class exists in the addon or in src/actors (engine
    base classes such as CustomInventory are the only external parents allowed).
    An unresolved parent aborts DECORATE load for the whole file, so the addon
    cannot load at all.  This is how the broken ShinyMegaBase_P example was
    found.
6.  Every KEYCONF addplayerclass actor is declared in the addon's DECORATE and
    registered through a Define* call.  A class added to KEYCONF but never
    registered shows a blank name and no teammate-bar face.
7.  Every actor registered through DefineBoss/DefineSurvivor/DefineDemoneye/
    DefineTeamPresentation exists in the addon or in src/actors.

Inputs are read-only.  --examples-dir exists for the negative tests.  Exit
codes: 0 pass, 1 findings, 2 usage error or missing ACC.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Include order tools/compile-acs.sh uses, then the public hud header directory
# and any directory an example README documents with -i.
PROJECT_INCLUDE_DIRS = (
    "src/acs_source/v6b_overrides/_includes/common",
    "src/acs_source/v6b_overrides/_includes/mod_api",
    "src/acs_source/_includes/mod_api",
    "src/acs_source/_imports",
    "src/acs_source/v6b_overrides/_imports",
    "src/acs_source/unholy",
    "src/acs_source/hud",
)
DECORATE_SUFFIXES = {".dec", ".txt", ".decorate"}
ENGINE_ACTOR_BASES = frozenset({
    # Zandronum / Doom engine classes an addon may inherit without shipping
    # them.  MM8BDM classes are NOT listed here: this repo ships its own actors
    # under src/actors and those are checked against that tree.
    "CustomInventory", "Inventory", "Weapon", "Ammo", "BasicProjectile",
    "BasicPowerupGiver", "PowerMorph", "PowerProtection", "PowerSpeed",
    "PlayerPawn", "DoomPlayer", "Actor", "Health",
})
ACC_KEYWORDS = frozenset({
    "if", "while", "for", "switch", "return", "script", "function", "else",
    "do", "until", "case", "break", "continue", "restart", "terminate",
})
REGISTER_FUNCTIONS = {
    "DefineBoss": 1,
    "DefineSurvivor": 1,
    "DefineDemoneye": 1,
    "DefineTeamPresentation": 0,
}


# --------------------------------------------------------------------------
# Small parsers shared with the ACS contract checker in spirit
# --------------------------------------------------------------------------
def strip_comments(text):
    """Remove ACS line and block comments, keeping string literals intact."""
    out = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == '"':
            out.append(ch)
            i += 1
            while i < n:
                out.append(text[i])
                if text[i] == "\\" and i + 1 < n:
                    out.append(text[i + 1])
                    i += 2
                    continue
                if text[i] == '"':
                    i += 1
                    break
                i += 1
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "/":
            newline = text.find("\n", i)
            i = n if newline < 0 else newline
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "*":
            close = text.find("*/", i)
            i = n if close < 0 else close + 2
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def balanced(text, index, opening="(", closing=")"):
    depth = 0
    i = index
    while i < len(text):
        if text[i] == opening:
            depth += 1
        elif text[i] == closing:
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise ValueError("unbalanced %r at offset %d" % (opening, index))


def split_args(text):
    args = []
    depth = 0
    current = []
    for ch in text:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == "," and depth == 0:
            args.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    tail = "".join(current).strip()
    if tail:
        args.append(tail)
    return args


def string_literals(text):
    return set(re.findall(r'"([^"]*)"', text))


ACTOR_RE = re.compile(r"(?im)^\s*actor\s+([A-Za-z_]\w*)\s*(?::\s*([A-Za-z_]\w*))?")


def parse_decorate(text):
    """Return (actor definitions, parent references) for one DECORATE file."""
    text = strip_comments(text)
    actors = {}
    parents = {}
    for match in ACTOR_RE.finditer(text):
        actors[match.group(1)] = match.group(2)
        if match.group(2):
            parents[match.group(1)] = match.group(2)
    return actors, parents


def repo_actors(root):
    """Collect every actor defined under src/actors (the mod's DECORATE tree)."""
    actors = set()
    actors_dir = root / "src" / "actors"
    for path in actors_dir.rglob("*"):
        if path.suffix.lower() not in DECORATE_SUFFIXES:
            continue
        text = strip_comments(path.read_text(encoding="utf-8",
                                              errors="replace"))
        actors.update(match.group(1) for match in ACTOR_RE.finditer(text))
    return actors


def repo_relative(root, path):
    """Path for messages: relative to the repo root when possible, else str."""
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def readme_include_dirs(root, example):
    """Return the -i directories the example README documents, repo-relative."""
    readme = example / "README.md"
    if not readme.is_file():
        return []
    dirs = []
    text = readme.read_text(encoding="utf-8", errors="replace")
    for match in re.finditer(r'-i\s+"([^"]+)"', text):
        raw = match.group(1).replace("\\", "/").strip()
        if re.match(r"^[A-Za-z]:/", raw) or raw.startswith("/"):
            continue  # the compiler's own directory, not a repo path
        while raw.startswith("../"):
            raw = raw[3:]
        while raw.startswith("./"):
            raw = raw[2:]
        candidate = root / raw
        if candidate.is_dir():
            dirs.append(raw)
    return dirs


def loadacs_entries(example):
    path = example / "LOADACS"
    if not path.is_file():
        return []
    entries = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.split("//", 1)[0].strip()
        if line:
            entries.append(line)
    return entries


def declared_libraries(example):
    """Return {library name: source path} for the example's ACS sources."""
    libraries = {}
    for path in sorted(example.rglob("*.acs")):
        text = strip_comments(path.read_text(encoding="utf-8",
                                             errors="replace"))
        for match in re.finditer(r'#library\s+"([^"]+)"', text):
            libraries[match.group(1)] = path
    return libraries


def find_local_object(example, library):
    acs_dir = example / "acs"
    if not acs_dir.is_dir():
        return None
    for path in acs_dir.iterdir():
        if path.suffix.lower() == ".o" and path.stem.lower() == library.lower():
            return path
    return None


def registered_actors(example, sources):
    """Return [(function, actor literal, source)] for UHADD registration calls."""
    registrations = []
    for source in sources:
        text = strip_comments(source.read_text(encoding="utf-8",
                                               errors="replace"))
        for name, actor_index in REGISTER_FUNCTIONS.items():
            for match in re.finditer(r"\b" + name + r"\s*\(", text):
                close = balanced(text, match.end() - 1)
                args = split_args(text[match.end():close])
                if len(args) <= actor_index:
                    continue
                literal = re.fullmatch(r'"([^"]*)"', args[actor_index])
                if literal:
                    registrations.append((name, literal.group(1), source))
    return registrations


# --------------------------------------------------------------------------
# Compilation
# --------------------------------------------------------------------------
def find_acc():
    configured = os.environ.get("ACC")
    if configured:
        return configured
    return shutil.which("acc")


def include_flags(dirs):
    flags = []
    for directory in dirs:
        flags.extend(["-i", directory])
    return flags


def compile_source(acc, root, source, output, include_dirs):
    argv = [acc] + include_flags(include_dirs) + [str(source), str(output)]
    proc = subprocess.run(argv, cwd=str(root), capture_output=True, text=True)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def tail(text, limit=8):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return " | ".join(lines[-limit:])


# --------------------------------------------------------------------------
# Per-example check
# --------------------------------------------------------------------------
def check_example(root, example, acc, repo_actor_names, out_dir, problems):
    name = repo_relative(root, example)
    local = []
    entries = loadacs_entries(example)
    sources = sorted(example.rglob("*.acs"))
    libraries = declared_libraries(example)
    if not entries and not sources:
        return {"name": name, "kind": "config-only", "libraries": 0,
                "actors": 0, "status": "skipped"}
    if not entries:
        local.append("%s has ACS sources but no LOADACS entry" % name)
    entry_names = {entry.lower() for entry in entries}
    library_names = {library.lower(): library for library in libraries}
    for entry in entries:
        if entry.lower() not in library_names:
            local.append(
                "%s LOADACS lists %r, but no source declares #library %r"
                % (name, entry, entry))
    for library, source in sorted(libraries.items()):
        if library.lower() not in entry_names:
            local.append(
                "%s declares #library %r in %s, but LOADACS does not list it"
                % (name, library, repo_relative(root, source)))

    decorate_files = [path for path in example.rglob("*")
                      if path.is_file() and
                      (path.suffix.lower() in DECORATE_SUFFIXES or
                       path.name == "DECORATE")]
    addon_actors = {}
    addon_parents = {}
    for path in decorate_files:
        actors, parents = parse_decorate(
            path.read_text(encoding="utf-8", errors="replace"))
        addon_actors.update(actors)
        addon_parents.update(parents)
    known_actors = set(addon_actors) | set(repo_actor_names)
    for actor, parent in sorted(addon_parents.items()):
        if parent in known_actors or parent in ENGINE_ACTOR_BASES:
            continue
        local.append(
            "%s DECORATE actor %s inherits %r, which no DECORATE file in the "
            "addon or src/actors defines (an unresolved parent aborts the "
            "whole DECORATE load)" % (name, actor, parent))

    registrations = registered_actors(example, sources)
    registered_names = {actor.lower() for _function, actor, _source
                        in registrations}
    keyconf = example / "KEYCONF"
    if keyconf.is_file():
        text = keyconf.read_text(encoding="utf-8", errors="replace")
        for match in re.finditer(r"(?im)^\s*addplayerclass\s+(\w+)", text):
            playerclass = match.group(1)
            if playerclass.lower() not in {item.lower()
                                           for item in known_actors}:
                local.append(
                    "%s KEYCONF adds playerclass %s, which no DECORATE file in "
                    "the addon or src/actors defines" % (name, playerclass))
            if playerclass.lower() not in registered_names:
                local.append(
                    "%s KEYCONF adds playerclass %s, but no DefineBoss/"
                    "DefineSurvivor/DefineDemoneye/DefineTeamPresentation call "
                    "in the addon's ACS registers that actor (the class would "
                    "show no name or face)" % (name, playerclass))

    for function, actor, source in registrations:
        if function == "DefineDemoneye" and actor == "":
            continue  # documented face-only bonus eye
        if actor.lower() in {item.lower() for item in known_actors}:
            continue
        local.append(
            "%s calls %s(%r), but no DECORATE file in the addon or src/actors "
            "defines that actor" % (repo_relative(root, source),
                                    function, actor))

    include_dirs = list(PROJECT_INCLUDE_DIRS) + readme_include_dirs(root, example)
    include_dirs = list(dict.fromkeys(include_dirs))
    compile_include_dirs = [str(example)] + [
        str(root / directory) for directory in include_dirs]
    objects_current = 0
    objects_missing = 0
    for library, source in sorted(libraries.items()):
        text = source.read_text(encoding="utf-8", errors="replace")
        for match in re.finditer(r'^\s*#\s*(?:include|import)\s+"([^"]+)"',
                                 text, re.MULTILINE):
            include = match.group(1)
            if include == "zcommon.acs":
                continue
            resolved = None
            for directory in compile_include_dirs:
                candidate = Path(directory) / include
                if candidate.is_file():
                    resolved = candidate
                    break
            if resolved is None:
                local.append(
                    "%s includes %r, but no documented include directory "
                    "provides it (searched: %s)"
                    % (repo_relative(root, source), include,
                       ", ".join(include_dirs)))
        output = out_dir / (library + ".o")
        code, log = compile_source(acc, root, source, output, compile_include_dirs)
        if code != 0:
            local.append(
                "%s failed to compile with the documented include order: %s"
                % (repo_relative(root, source), tail(log)))
            continue
        local_object = find_local_object(example, library)
        if local_object is None:
            objects_missing += 1
            continue
        if local_object.read_bytes() != output.read_bytes():
            local.append(
                "%s acs/%s.o is stale: the object built from %s differs "
                "(recompile the example; this checker never rewrites it)"
                % (name, library, repo_relative(root, source)))
            continue
        objects_current += 1

    problems.extend(local)
    status = "ok" if not local else "fail"
    return {"name": name, "kind": "addon", "libraries": len(libraries),
            "actors": len(addon_actors), "objects_current": objects_current,
            "objects_missing": objects_missing, "status": status}


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Verify every example addon package and compile its ACS.",
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT,
                        help="repository root (default: this checkout)")
    parser.add_argument("--examples-dir", type=Path,
                        help="override examples/ (negative-test fixture)")
    parser.add_argument("--acc", help="ACC binary (default: $ACC or PATH)")
    parser.add_argument("--keep-out", action="store_true",
                        help="keep the temporary build directory")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="print the include directories used per example")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    examples_dir = (args.examples_dir or (root / "examples")).resolve()
    if not examples_dir.is_dir():
        print("error: missing %s" % examples_dir, file=sys.stderr)
        return 2
    acc = args.acc or find_acc()
    if not acc:
        print("error: ACC not found (set ACC or put acc on PATH)",
              file=sys.stderr)
        return 2
    resolved_acc = shutil.which(acc)
    if resolved_acc is None and Path(acc).is_file():
        resolved_acc = str(Path(acc))
    if resolved_acc is None:
        print("error: ACC binary %r does not exist or is not executable"
              % acc, file=sys.stderr)
        return 2
    acc = resolved_acc

    repo_actor_names = repo_actors(root)
    if not repo_actor_names:
        print("error: no actors found under src/actors", file=sys.stderr)
        return 2

    out_dir = Path(tempfile.mkdtemp(prefix="uh-addon-examples-"))
    if root in out_dir.parents:
        print("error: refusing to build inside the repository (%s)" % out_dir,
              file=sys.stderr)
        return 2

    problems = []
    results = []
    for example in sorted(path for path in examples_dir.iterdir()
                          if path.is_dir()):
        results.append(check_example(root, example, acc, repo_actor_names,
                                     out_dir, problems))
        if args.verbose:
            dirs = [repo_relative(root, example)] + readme_include_dirs(
                root, example)
            print("%-24s include roots: %s"
                  % (example.name, ", ".join(dirs)))

    for result in results:
        if result["kind"] == "config-only":
            print("[SKIP] %-24s no ACS sources (host-config sample)"
                  % result["name"])
            continue
        print("[%s] %-24s libraries=%d actors=%d local-objects=%d current, "
              "%d not built"
              % ("OK" if result["status"] == "ok" else "FAIL", result["name"],
                 result["libraries"], result["actors"],
                 result["objects_current"], result["objects_missing"]))

    if problems:
        print("findings: %d" % len(problems))
        for problem in problems:
            print("  FAIL %s" % problem)
    addons = sum(1 for result in results if result["kind"] == "addon")
    skipped = sum(1 for result in results if result["kind"] == "config-only")
    current = sum(result.get("objects_current", 0) for result in results)
    missing = sum(result.get("objects_missing", 0) for result in results)
    print("summary: %d example package(s) checked, %d config-only, "
          "%d local object(s) current, %d not built here"
          % (addons, skipped, current, missing))

    if not args.keep_out:
        shutil.rmtree(out_dir, ignore_errors=True)
    else:
        print("build directory kept: %s" % out_dir)
    if problems:
        return 1
    print("ok: every example addon is self-consistent and its ACS compiles")
    return 0


if __name__ == "__main__":
    sys.exit(main())

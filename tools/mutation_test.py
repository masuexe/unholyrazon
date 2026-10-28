#!/usr/bin/env python3
"""Prove that the static gate checks actually catch the defects they claim to.

A checker that never fails is not a test.  This project has 20+ python checkers,
and every one of them is a hand-written parser: a regex that stops matching, a
path that moved, or an early "continue" silently turns a real guard into a
no-op.  Nothing else in the gate would notice.

This harness applies the same discipline to the checks themselves.  For each
case it:

  1. makes a hardlink copy of the read-only parts of the repository (fast: the
     copy shares inodes, so ~120 MB is not duplicated);
  2. confirms the target checker PASSES on the unmodified copy (baseline);
  3. breaks the hardlink and writes one known defect into the copy;
  4. runs the checker and requires a NON-ZERO exit.

A case passes only when step 2 is green and step 4 is red.  A baseline failure
means the copy is not a faithful tree, so the case is reported as an error
instead of a pass.

The defect list is data (MUTATIONS at the bottom), keyed to the failure modes
this mod has actually shipped.  Add a case whenever a new checker lands: a
checker without a mutation case is an unverified claim.

Usage:
  python3 tools/mutation_test.py                 # every case
  python3 tools/mutation_test.py --case NAME     # one case (repeatable)
  python3 tools/mutation_test.py --list
  python3 tools/mutation_test.py --json
  python3 tools/mutation_test.py --keep          # keep the scratch tree

Exit: 0 all cases caught, 1 a case was not caught, 2 usage or setup error.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PY = sys.executable

# Only the trees the static checkers read.  out/ is 1.6 GB and irrelevant here.
COPIED = ("src", "tools", "examples", "docs")

MUTATIONS = [
    {
        "name": "state-loop-same-line",
        "checker": "tools/check_state_loops.py",
        "why": "zero-duration loop in the 'States {' style (Half Press Hardman crash)",
        "file": "src/actors/__mutation_probe.dec",
        "content": (
            "actor MutationSameLine : DoomImp\n"
            "{\n"
            "  States {\n"
            "  Spawn:\n"
            "    TNT1 A 0 A_GiveInventory(\"Clip\", 1)\n"
            "    loop\n"
            "  }\n"
            "}\n"
        ),
    },
    {
        "name": "state-loop-next-line",
        "checker": "tools/check_state_loops.py",
        "why": "zero-duration loop in the 'States' + newline '{' style (52 blocks)",
        "file": "src/actors/__mutation_probe.dec",
        "content": (
            "actor MutationNextLine : DoomImp\n"
            "{\n"
            "  States\n"
            "  {\n"
            "  Spawn:\n"
            "    TNT1 A 0 A_GiveInventory(\"Clip\", 1)\n"
            "    loop\n"
            "  }\n"
            "}\n"
        ),
    },
    {
        "name": "spawn-ref-missing-actor",
        "checker": "tools/check_actor_contracts.py",
        "why": "A_SpawnItemEx names an actor that does not exist",
        "file": "src/actors/__mutation_probe.dec",
        "content": (
            "actor MutationSpawnRef : DoomImp\n"
            "{\n"
            "  States {\n"
            "  Spawn:\n"
            "    TNT1 A 0 A_SpawnItemEx(\"ThisActorDoesNotExistAnywhere\", 0, 0, 0)\n"
            "    stop\n"
            "  }\n"
            "}\n"
        ),
    },
    {
        "name": "duplicate-actor-class",
        "checker": "tools/check_actor_contracts.py",
        "why": "the same actor class is declared twice (engine keeps one silently)",
        # Redefine a real actor that src/actors already declares.
        "file": "src/actors/classes/bosses/__mutation_probe.dec",
        "content": (
            "actor TidalTito\n"
            "{\n"
            "  States {\n"
            "  Spawn:\n"
            "    TNT1 A 0\n"
            "    stop\n"
            "  }\n"
            "}\n"
        ),
    },
    {
        "name": "unprotected-boss-damage",
        "checker": "tools/check_damage_types.py",
        "why": "boss splash deals a damage type the protection table does not cover",
        # The checker scopes by tree directory: the probe must live under a boss
        # tree, not at src/actors root.
        "file": "src/actors/classes/bosses/__mutation_probe.dec",
        "content": (
            "actor MutationBossSplash : DoomImp\n"
            "{\n"
            "  DamageType \"MutationUnprotectedType\"\n"
            "  States {\n"
            "  Spawn:\n"
            "    TNT1 A 0 A_Explode(50, 50)\n"
            "    stop\n"
            "  }\n"
            "}\n"
        ),
    },
    {
        "name": "broken-decorate-include",
        "checker": "tools/check_lump_integrity.py",
        "why": "an #include names a file that does not exist (silent at load)",
        "file": "src/actors/__mutation_probe.dec",
        "content": '#include "actors/ThisFileDoesNotExist.dec"\n',
    },
    {
        "name": "loadacs-library-missing",
        "checker": "tools/check_lump_integrity.py",
        "why": "LOADACS lists a library that no source declares",
        "file": "src/LOADACS",
        "replace": ("uh_colors", "uh_colors\nMUTATION_MISSING_LIB"),
    },
    {
        "name": "documented-api-removed",
        "checker": "tools/check_addon_api_contract.py",
        "why": "a documented public entry point disappears from the header",
        "file": "src/acs_source/_includes/mod_api/uhadd.acs",
        "replace": (
            "function int IsBossEnabledByActor(str actor) {",
            "function int IsBossEnabledByActorRenamed(str actor) {",
        ),
    },
    {
        # The symbol policy lives in the API-contract checker (rule 10), not in
        # the examples checker. The call must be valid ACS, or the case would
        # pass on a compile error instead of on the policy.
        "name": "example-uses-internal-symbol",
        "checker": "tools/check_addon_api_contract.py",
        "why": "an example calls a repo-internal function instead of the public API",
        "file": "examples/defineboss_addon/acs_source/uh_exaddon.acs",
        "replace": (
            "script ",
            "function void MutationInternalProbe(void) { UH_AddGuardFactor(0, 1); }\nscript ",
        ),
    },
    {
        "name": "example-broken-decorate-parent",
        "checker": "tools/check_addon_examples.py",
        "why": "an example inherits a class no DECORATE file defines (the ShinyMega bug)",
        "file": "examples/shinywep_addon/DECORATE",
        "replace": (
            "actor ShinyMega_UHExShot_P : CustomInventory {",
            "actor ShinyMega_UHExShot_P : ShinyMegaBase_P {",
        ),
    },
]


def copied_tree(dest: Path):
    """Hardlink-copy the source trees into dest, preserving structure."""
    dest.mkdir(parents=True, exist_ok=True)
    for name in COPIED:
        source = REPO / name
        if not source.is_dir():
            raise SystemExit(f"error: missing source tree {name}/")
        subprocess.run(["cp", "-al", str(source), str(dest / name)], check=True)


def write_mutation(root: Path, case) -> None:
    """Apply one mutation inside the copy.

    A case either writes a whole new file ("content") or edits an existing file
    ("replace": [old, new]).  Break the hardlink before writing, or the write
    would modify the real repository through the shared inode.
    """
    target = root / case["file"]
    if "replace" in case:
        text = target.read_text(encoding="utf-8")
        old, new = case["replace"]
        if old not in text:
            raise SystemExit(
                f"error: mutation {case['name']} cannot find its edit target in "
                f"{case['file']}; the source changed and the case must be updated")
        target.unlink()
        target.write_text(text.replace(old, new, 1), encoding="utf-8")
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        target.unlink()
    target.write_text(case["content"], encoding="utf-8")


def run_checker(root: Path, case) -> subprocess.CompletedProcess:
    return subprocess.run(
        [PY, str(root / case["checker"])],
        cwd=root, capture_output=True, text=True, timeout=300,
    )


def run_case(root: Path, case, baselines: dict):
    """Apply one mutation in the shared scratch tree, run it, then restore.

    One tree is reused for every case: a per-case copy costs more than the
    checkers themselves.  The tree is restored from the untouched source after
    each case, so a case can never inherit another case's mutation.
    """
    if case["checker"] not in baselines:
        baseline = run_checker(root, case)
        baselines[case["checker"]] = (
            baseline.returncode,
            (baseline.stdout + baseline.stderr)[-800:],
        )
    baseline_code, baseline_output = baselines[case["checker"]]
    if baseline_code != 0:
        return {
            "name": case["name"], "status": "error",
            "detail": "checker fails on the clean copy; the case proves nothing",
            "output": baseline_output,
        }

    target = root / case["file"]
    original = target.read_bytes() if target.exists() else None
    try:
        write_mutation(root, case)
        mutated = run_checker(root, case)
    finally:
        if original is None:
            target.unlink(missing_ok=True)
        else:
            target.unlink(missing_ok=True)
            target.write_bytes(original)

    caught = mutated.returncode != 0
    return {
        "name": case["name"],
        "status": "caught" if caught else "MISSED",
        "checker": case["checker"],
        "why": case["why"],
        "output": (mutated.stdout + mutated.stderr)[-800:],
    }


def main(argv) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--case", action="append", default=[], metavar="NAME")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--keep", action="store_true", help="keep the scratch tree")
    args = parser.parse_args(argv[1:])

    known = {case["name"]: case for case in MUTATIONS}
    if args.list:
        for case in MUTATIONS:
            print(f"{case['name']:26} {case['checker']:34} {case['why']}")
        return 0
    unknown = sorted(set(args.case) - set(known))
    if unknown:
        parser.error(f"unknown case(s): {', '.join(unknown)}")
    selected = [known[name] for name in args.case] if args.case else list(MUTATIONS)

    scratch = Path(tempfile.mkdtemp(prefix="uh-mutation-", dir=REPO / "tmp"))
    root = scratch / "tree"
    copied_tree(root)
    baselines: dict = {}
    results = []
    try:
        for case in selected:
            result = run_case(root, case, baselines)
            results.append(result)
            if not args.json:
                print(f"[{result['status'].upper():6}] {result['name']}")
                if result["status"] != "caught":
                    for line in result.get("output", "").splitlines()[-6:]:
                        print(f"         {line}")
    finally:
        if not args.keep:
            shutil.rmtree(scratch, ignore_errors=True)
        else:
            print(f"scratch kept at {scratch}")

    missed = [r for r in results if r["status"] != "caught"]
    ok = not missed
    if args.json:
        print(json.dumps({"ok": ok, "cases": results}, indent=2))
    else:
        caught = len(results) - len(missed)
        print(f"\nmutation cases: {caught} caught, {len(missed)} missed"
              f" ({len(results)} total)")
        if missed:
            print("a checker that does not fail on its own mutation is not a test")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))

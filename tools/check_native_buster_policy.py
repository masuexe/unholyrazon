#!/usr/bin/env python3
"""Guard the native buster-upgrade policy for custom weapon (UH) classes.

v6c marks the native buster-upgrade items and every BaseMM8BDMWep weapon as
forbidden to CustWepClassBase. All UH player classes descend from
CustWepClassBase, so those items and weapons must stay unusable on UH bodies
unless the project changes class balance on purpose.

This checker verifies the parts that a later edit can silently break:
1. BaseMM8BDMWep keeps Inventory.ForbiddenTo CustWepClassBase and
   +INVENTORY.RESTRICTABSOLUTELY, so even a script-given native weapon fails.
2. BaseMM8BDMCustWep stays RestrictedTo CustWepClassBase.
3. The base buster-upgrade actor is not redefined in src without the same
   forbidden-to restriction.
4. No UH source gives a native buster upgrade to a player.

Run:  python3 tools/check_native_buster_policy.py
Exit: 0 clean, 1 finding, 2 usage error.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
WEAPON_BASES = SRC / "actors" / "inventory" / "baseweaponedit.txt"
NATIVE_UPGRADES = (
    "JetAdaptorUpgrade",
    "PowerAdaptorUpgrade",
    "RockKickUpgrade",
    "RollSwingUpgrade",
    "RushBikeUpgrade",
)
DECORATE_SUFFIXES = {".dec", ".txt", ".decorate"}
ACTOR_RE = re.compile(r"(?im)^[ \t]*actor\s+([A-Za-z_][A-Za-z0-9_]*)")


def actor_block(text: str, name: str) -> str | None:
    for match in ACTOR_RE.finditer(text):
        if match.group(1).lower() != name.lower():
            continue
        following = None
        for nxt in ACTOR_RE.finditer(text, match.end()):
            following = nxt.start()
            break
        return text[match.start():following if following is not None else len(text)]
    return None


def normalize(block: str) -> str:
    return re.sub(r"[\s]+", " ", block).lower()


def decorate_files():
    for path in sorted(SRC.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() in DECORATE_SUFFIXES or "decorate" in path.name.lower():
            yield path


def acs_files():
    for path in sorted((SRC / "acs_source").rglob("*.acs")):
        yield path


def main() -> int:
    findings = []

    text = WEAPON_BASES.read_text(encoding="utf-8", errors="replace")
    base = actor_block(text, "BaseMM8BDMWep")
    if base is None:
        findings.append("actor BaseMM8BDMWep is missing from baseweaponedit.txt")
    else:
        flat = normalize(base)
        if "inventory.forbiddento" not in flat or "custwepclassbase" not in flat:
            findings.append("BaseMM8BDMWep no longer forbids CustWepClassBase")
        if "+inventory.restrictabsolutely" not in flat:
            findings.append("BaseMM8BDMWep lost +INVENTORY.RESTRICTABSOLUTELY")
    cust = actor_block(text, "BaseMM8BDMCustWep")
    if cust is None:
        findings.append("actor BaseMM8BDMCustWep is missing from baseweaponedit.txt")
    elif "inventory.restrictedto" not in normalize(cust) or "custwepclassbase" not in normalize(cust):
        findings.append("BaseMM8BDMCustWep is no longer restricted to CustWepClassBase")

    for path in decorate_files():
        body = path.read_text(encoding="utf-8", errors="replace")
        override = actor_block(body, "BaseMM8BDMBusterUpgrade")
        if override is not None:
            flat = normalize(override)
            if "inventory.forbiddento" not in flat or "custwepclassbase" not in flat:
                findings.append(
                    "%s redefines BaseMM8BDMBusterUpgrade without ForbiddenTo CustWepClassBase"
                    % path.relative_to(ROOT).as_posix())

    give_re = re.compile(
        r"(?i)(?:a_giveinventory|giveinventory|giveactorinventory)\s*\(\s*\"([^\"]+)\"")
    names = {name.lower() for name in NATIVE_UPGRADES}
    for path in list(decorate_files()) + list(acs_files()):
        body = path.read_text(encoding="utf-8", errors="replace")
        for match in give_re.finditer(body):
            target = match.group(1).strip().lower()
            if target in names:
                findings.append(
                    "%s gives native buster upgrade %s"
                    % (path.relative_to(ROOT).as_posix(), match.group(1).strip()))

    if findings:
        for finding in findings:
            print("FAIL: " + finding)
        print("summary: %d native buster-policy finding(s)" % len(findings))
        return 1
    print("summary: native buster-upgrade policy intact")
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1:
        print("usage: check_native_buster_policy.py", file=sys.stderr)
        sys.exit(2)
    sys.exit(main())

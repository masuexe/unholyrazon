#!/usr/bin/env python3
"""Guard the class restrictions for native weapons and MegaMan's upgrades.

The thirteen stock Busters use a separate weapon base with an explicit
allowlist. Their pickup items route standard MegaMan through the upgrade
installer. The restrictions on the general stock and custom weapon bases
continue to apply to the rest of the weapon roster.

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

    mega = actor_block(text, "MegaManUBuster")
    allowlist = re.search(r'(?im)^\s*Inventory\.RestrictedTo\s+([^\r\n]+)', mega or "")
    if not allowlist or re.findall(r'"([^"]+)"', allowlist[1].lower()) != ["megaman", "megamanu"]:
        findings.append("MegaManUBuster must keep the stock and UH Mega Man weapon allowlist")

    registry = (SRC / "acs_source/classes/shared/copy_weapons/megaman_buster_upgrades.acs").read_text()
    registry_row = re.search(r'uh_megabusters\[[^\]]+\]\s*=\s*\{([^}]+)\}', registry)
    weapons = re.findall(r'"([^"]+)"', registry_row[1]) if registry_row else []
    upgrades = (SRC / "actors/inventory/assists/busterupgrade.txt").read_text()
    # Match the installer index to the weapon given by the stock item's Use state.
    indexed_weapons = {}
    for match in ACTOR_RE.finditer(upgrades):
        block = actor_block(upgrades, match[1])
        install = re.search(r'CallACS\("uh_MegaInstallBuster",\s*(\d+)\)', block)
        if install:
            native_use = block.split("NativeUse:", 1)[-1]
            give = re.search(r'A_GiveInventory\("(?!BusterGiven")([^"]+)"', native_use)
            indexed_weapons[int(install[1])] = give[1].lower() if give else ""
    expected = {index: weapon.lower() for index, weapon in enumerate(weapons) if index}
    if len(expected) != 13 or indexed_weapons != expected:
        findings.append("Buster upgrade Use states must match all 13 installer indices")

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

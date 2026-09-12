#!/usr/bin/env python3
"""Migrate boss stacker and PowerAprop call sites onto the ownership-ledger wrappers.

Two passes:
  1. property stackers: ("core_*player", player, toggle) -> matching uh_*player wrapper
  2. PowerAprop:        A_GiveInventory("<Power>Giver"[, n]) -> uh_BossPowerGive(idx[, n])
                        A_TakeInventory("<Power>"[, n])       -> uh_BossPowerTake(idx[, n])

The generated property calls preserve the base API's player/toggle/extra
argument order; numeric family IDs remain internal to morph_reset.acs.

The PowerAprop index table is parsed from uh_morphpowername in
systems/tools/morph_reset.acs, so the tool cannot drift from the runtime table.

Usage: migrate-boss-stackers.py [--apply] [--root DIR]
"""

import argparse
import os
import re

SIMPLE = {
    "core_freezeplayer": 0, "core_stopplayer": 1, "core_invulnerableplayer": 2,
    "core_buddhaplayer": 7, "core_nonshootableplayer": 8, "core_nopushplayer": 9,
    "core_cantseekplayer": 10, "core_notargetplayer": 11, "core_monsterblockplayer": 12,
    "core_invisibleplayer": 13, "core_dontidentifytargetplayer": 14,
}
FLY, FLY_FORCED, NOGRAV, NOGRAV_FORCED = 4, 3, 6, 5

WRAPPER = {
    0: "uh_freezeplayer", 1: "uh_stopplayer", 2: "uh_invulnerableplayer",
    3: "uh_flyplayer", 4: "uh_flyplayer", 5: "uh_nogravityplayer",
    6: "uh_nogravityplayer", 7: "uh_buddhaplayer", 8: "uh_nonshootableplayer",
    9: "uh_nopushplayer", 10: "uh_cantseekplayer", 11: "uh_notargetplayer",
    12: "uh_monsterblockplayer", 13: "uh_invisibleplayer",
    14: "uh_dontidentifytargetplayer", 15: "uh_unsolidplayer",
    16: "uh_NoHitStunplayer", 17: "uh_HalfHitStunplayer", 18: "uh_halfpushplayer",
    19: "uh_cantuseitemsplayer", 20: "rz_NoParalyzePlayer",
    21: "uh_noradiusdmgplayer", 22: "uh_cantpushwallsplayer",
    23: "uh_noteleportplayer", 24: "uh_pickupdisableplayer",
    25: "uh_brightplayer", 26: "uh_shadowplayer",
}

CALL = re.compile(
    r'^(?P<pre>.*?)(?P<func>ACS_NamedExecute(?:WithResult|Always))\("'
    r'(?P<name>[A-Za-z0-9_]+)"\s*,\s*0\s*,\s*(?P<args>.*?)\)\s*$', re.I)
OLD_WRAPPER_CALL = re.compile(
    r'^(?P<pre>.*?)(?P<func>ACS_NamedExecute(?:WithResult|Always))\("'
    r'(?P<name>uh_BossStackOn|uh_BossStackOff)"\s*,\s*(?P<family>\d+)\s*\)\s*$', re.I)
OLD_UNSOLID_CALL = re.compile(
    r'^(?P<pre>.*?)(?P<func>ACS_NamedExecute(?:WithResult|Always))\("'
    r'(?P<name>uh_BossUnsolidOn|uh_BossUnsolidOffDmg)"(?:\s*,\s*(?P<damage>.*?))?\)\s*$', re.I)
ON, OFF = {"true", "1"}, {"false", "0"}

DEFAULT_TARGETS = [
    "src/actors/classes/bosses",
    "src/actors/inventory/bosswepbase.dec",
    "src/actors/inventory/baseweaponedit.txt",
    "src/actors/classes/survivors/Zangief_W.dec",
    "src/actors/unepic/GeneralThings_U.dec",
]
POWER_TABLE = "src/acs_source/systems/tools/morph_reset.acs"


def power_names(root):
    txt = open(os.path.join(root, POWER_TABLE), errors="ignore").read()
    m = re.search(r"uh_morphpowername\[[^\]]+\]\s*=\s*\{(.*?)\};", txt, re.S)
    body = re.sub(r"//[^\n]*", "", m.group(1))
    return [x.strip().strip('"') for x in body.split(",") if x.strip()]


def classify(name, args):
    low = name.lower()
    parts = [p.strip() for p in args.split(",")]
    head = parts[0]
    if low == "core_flyplayer":
        if len(parts) == 1 and (head in ON or head in OFF):
            return (WRAPPER[FLY], ["0", head, "0"])
        if len(parts) == 2 and parts[1] == "1" and (head in ON or head in OFF):
            return (WRAPPER[FLY_FORCED], ["0", head, "1"])
        return None
    if low == "core_nogravityplayer":
        if len(parts) == 1 and (head in ON or head in OFF):
            return (WRAPPER[NOGRAV], ["0", head, "0"])
        if len(parts) == 2 and parts[1] == "1" and (head in ON or head in OFF):
            return (WRAPPER[NOGRAV_FORCED], ["0", head, "1"])
        return None
    if low == "core_unsolidplayer":
        if head == "USP_TOGGLEON" or head in ON:
            return (WRAPPER[15], ["0", head, "0"])
        if head.startswith("USP_TOGGLEOFF_") and head != "USP_TOGGLEOFF_DAMAGE":
            return None
        if head in OFF or head == "USP_TOGGLEOFF_DAMAGE":
            return (WRAPPER[15], ["0", head, "0" if len(parts) == 1 else parts[1]])
        return None
    if low in SIMPLE:
        if len(parts) == 1 and head in ON:
            return (WRAPPER[SIMPLE[low]], ["0", head])
        if len(parts) == 1 and head in OFF:
            return (WRAPPER[SIMPLE[low]], ["0", head])
        return None
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--root", default=".")
    args = ap.parse_args()

    powers = power_names(args.root)
    pidx = {n: i for i, n in enumerate(powers)}
    give = re.compile(r'^(?P<pre>.*?)A_GiveInventory\("(?P<name>[A-Za-z0-9_]+)Giver"\s*(?:,\s*(?P<amt>[^)]*?))?\)\s*$')
    take = re.compile(r'^(?P<pre>.*?)A_TakeInventory\("(?P<name>[A-Za-z0-9_]+)"\s*(?:,\s*(?P<amt>[^)]*?))?\)\s*$')

    files = []
    for t in DEFAULT_TARGETS:
        p = os.path.join(args.root, t)
        if os.path.isdir(p):
            for dp, _, fns in os.walk(p):
                files += [os.path.join(dp, f) for f in fns if f.endswith((".dec", ".txt"))]
        elif os.path.isfile(p):
            files.append(p)
    files.sort()

    stats = {}
    leftovers = []
    for path in files:
        out = []
        for lineno, line in enumerate(open(path, errors="ignore").read().split("\n"), 1):
            code, _, comment = line.partition("//")
            new = None
            old = OLD_WRAPPER_CALL.match(code)
            if old:
                family = int(old.group("family"))
                toggle = "1" if old.group("name").lower().endswith("on") else "0"
                extra = ", 1" if family in (FLY_FORCED, NOGRAV_FORCED) else (", 0" if family in (FLY, NOGRAV) else "")
                new = '%s%s("%s", 0, %s%s)' % (
                    old.group("pre"), old.group("func"), WRAPPER[family], toggle, extra)
                stats[WRAPPER[family]] = stats.get(WRAPPER[family], 0) + 1
            old_unsolid = OLD_UNSOLID_CALL.match(code)
            if new is None and old_unsolid:
                is_on = old_unsolid.group("name").lower().endswith("on")
                toggle = "USP_TOGGLEON" if is_on else "USP_TOGGLEOFF_DAMAGE"
                damage = "0" if is_on else (old_unsolid.group("damage") or "0").strip()
                new = '%s%s("uh_unsolidplayer", 0, %s, %s)' % (
                    old_unsolid.group("pre"), old_unsolid.group("func"), toggle, damage)
                stats["uh_unsolidplayer"] = stats.get("uh_unsolidplayer", 0) + 1
            m = CALL.match(code)
            if new is None and m:
                res = classify(m.group("name"), m.group("args"))
                if res:
                    script, extra = res
                    call = m.group("func") + '("' + script + '"'
                    if extra:
                        call += ", " + ", ".join(extra)
                    new = m.group("pre") + call + ")"
                    stats[script] = stats.get(script, 0) + 1
            if new is None:
                g = give.match(code)
                if g and g.group("name") in pidx:
                    amt = (g.group("amt") or "").strip()
                    new = g.group("pre") + 'ACS_NamedExecuteWithResult("uh_BossPowerGive", %d%s)' % (
                        pidx[g.group("name")], ", " + amt if amt else "")
                    stats["uh_BossPowerGive"] = stats.get("uh_BossPowerGive", 0) + 1
            if new is None:
                t = take.match(code)
                if t and t.group("name") in pidx:
                    amt = (t.group("amt") or "").strip()
                    new = t.group("pre") + 'ACS_NamedExecuteWithResult("uh_BossPowerTake", %d%s)' % (
                        pidx[t.group("name")], ", " + amt if amt else "")
                    stats["uh_BossPowerTake"] = stats.get("uh_BossPowerTake", 0) + 1
            if new is not None:
                out.append(new + ("//" + comment if comment else ""))
            else:
                if re.search(r'PowerGiver"|Power"\s*[,)]', line) and "A_GiveInventory" in line or "A_TakeInventory" in line and "Power" in line:
                    leftovers.append("%s:%d: %s" % (path, lineno, line.strip()))
                out.append(line)
        if args.apply:
            open(path, "w").write("\n".join(out))

    for k in sorted(stats):
        print("  %-22s %d" % (k, stats[k]))
    print("lines still mentioning a power grant/take:", len(leftovers))
    for l in leftovers[:20]:
        print("  ", l)
    if not args.apply:
        print("(dry run)")


if __name__ == "__main__":
    main()

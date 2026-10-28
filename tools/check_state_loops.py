#!/usr/bin/env python3
"""Reject unconditional zero-duration state loops in DECORATE actors.

A state sequence such as

    Refresh:
      TNT1 A 0 A_GiveInventory("Ammo", 20)
      TNT1 A 0 A_GiveInventory("Power", 5)
      loop

does not advance time: DECORATE runs every state whose duration is 0 inside a
single tic, and ``loop`` jumps back to the first state after the most recent
label.  The result is an infinite loop *inside one tick*.  Zandronum guards
clients against this (AActor::SetState breaks after 10000 actions in client
mode) but the authoritative server has no such guard, so the server spins
forever and allocates without bound (each such action can spawn/destroy
inventory actors) until malloc fails - the player-visible "Could not malloc N
bytes" fatal error.

This checker parses the actor state tables, resolves the control flow
(fallthrough, ``loop``, ``goto Label[+N]`` and quoted state labels on
``A_Jump*`` / ``A_CountDownArg`` actions), and fails on any cycle whose frames
are all duration 0 and which contains no action that can leave the cycle
(``A_CountDown*``, ``A_Jump*``, ``A_Goto``, ``A_Die``, ``A_KillChildren``,
``A_Remove``).  Sequences that are deliberately time-gated by a non-zero
duration frame are fine.

Run:  python3 tools/check_state_loops.py [paths...]
Exit: 0 clean, 1 findings, 2 usage error.
"""
from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEFAULT_ROOTS = [REPO / "src" / "actors"]
SUFFIXES = (".dec", ".txt")

CONTROL = re.compile(r"^(goto|loop|stop|wait|fail)\b", re.I)
GOTO = re.compile(r"^goto\s+([A-Za-z0-9_.]+)\s*(?:([+-])\s*(\d+))?\s*$", re.I)
LABEL = re.compile(r"^\s*([A-Za-z0-9_.]+):\s*$")
ACTOR = re.compile(r"\s*actor\s+(\w+)", re.I)
# A state block starts with "States {" on one line, or "States" with the brace
# on a later line. Both styles occur here (52 blocks in 31 files use the second
# form). Requiring the brace on the same line made those blocks invisible, so a
# zero-duration loop inside one of them passed verification.
STATES = re.compile(r"\s*States\s*(?:\{|$)", re.I)
STATE_LINE = re.compile(r"^(\S+)\s+(\S+)\s+(-?\d+)\s*(.*)$")
TARGET_ACTION = re.compile(r"^(?:A_Jump\w*|A_CountDownArg|A_Goto)\b", re.I)
ESCAPE_ACTION = re.compile(
    r"A_CountDown\w*|A_Jump\w*|A_Goto|A_Die\b|A_KillChildren|A_Remove\b", re.I
)


def parse_actor_states(path: Path):
    """Return {actor: {"frames": [...], "labels": {...}}} for one DECORATE file."""
    actors: dict[str, dict] = {}
    actor = None
    in_states = False
    label = None
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    for lineno, line in enumerate(lines, 1):
        match = ACTOR.match(line)
        if match:
            actor = match.group(1)
            actors[actor] = {"frames": [], "labels": {}}
            in_states = False
            label = None
            continue
        if STATES.match(line):
            in_states = True
            continue
        if in_states and line.strip() == "}":
            in_states = False
            continue
        if not in_states or actor is None:
            continue
        match = LABEL.match(line)
        if match:
            label = match.group(1)
            actors[actor]["labels"].setdefault(label, len(actors[actor]["frames"]))
            continue
        text = line.strip()
        if not text or text.startswith("//"):
            continue
        if CONTROL.match(text):
            actors[actor]["frames"].append(
                {"line": lineno, "label": label, "dur": None, "act": "", "ctrl": text}
            )
            continue
        match = STATE_LINE.match(text)
        if match:
            actors[actor]["frames"].append(
                {
                    "line": lineno,
                    "label": label,
                    "dur": int(match.group(3)),
                    "act": match.group(4).strip(),
                    "ctrl": None,
                }
            )
    return actors


def state_edges(frames, labels):
    """Adjacency list of the actor state table, including non-frame control entries."""
    edges = defaultdict(list)
    for index, frame in enumerate(frames):
        if frame["ctrl"]:
            text = frame["ctrl"]
            if text.lower() == "loop":
                edges[index].append(labels.get(frame["label"], 0))
                continue
            match = GOTO.match(text)
            if match:
                target, sign, offset = match.group(1), match.group(2), match.group(3)
                if target in labels:
                    delta = 0
                    if sign and offset:
                        delta = int(offset) * (1 if sign == "+" else -1)
                    edges[index].append(labels[target] + delta)
            continue
        edges[index].append(index + 1)
        if TARGET_ACTION.match(frame["act"]):
            for quoted in re.findall(r'"([A-Za-z0-9_.]+)"', frame["act"]):
                if quoted in labels:
                    edges[index].append(labels[quoted])
    return edges


def find_bad_cycles(actor, frames, labels):
    """Yield cycles whose frames all have duration 0 and cannot exit."""
    edges = state_edges(frames, labels)
    count = len(frames)
    findings = []
    seen = set()

    def visit(node, path):
        if node >= count:
            return
        frame = frames[node]
        if frame["dur"] is not None and frame["dur"] != 0:
            return
        for nxt in edges.get(node, ()):
            if nxt < 0 or nxt >= count:
                continue
            if nxt in path:
                cycle = path[path.index(nxt):]
                cycle_frames = [frames[i] for i in cycle]
                if any(item["dur"] not in (0, None) for item in cycle_frames):
                    continue
                actions = " ".join(item["act"] for item in cycle_frames)
                if ESCAPE_ACTION.search(actions):
                    continue
                key = tuple(sorted(item["line"] for item in cycle_frames))
                if key in seen:
                    continue
                seen.add(key)
                findings.append([frames[i] for i in cycle])
                continue
            if len(path) > 400:
                continue
            visit(nxt, path + [nxt])

    for start in range(count):
        if frames[start]["dur"] == 0 and not frames[start]["ctrl"]:
            visit(start, [start])
    return findings


def iter_files(paths):
    for path in paths:
        path = Path(path)
        if path.is_file():
            yield path
            continue
        for child in sorted(path.rglob("*")):
            if child.is_file() and child.suffix.lower() in SUFFIXES:
                yield child


def main(argv):
    paths = [Path(arg) for arg in argv[1:]] or DEFAULT_ROOTS
    findings = 0
    scanned = 0
    for path in iter_files(paths):
        scanned += 1
        try:
            actors = parse_actor_states(path)
        except OSError as exc:
            print(f"{path}: cannot read: {exc}")
            findings += 1
            continue
        for actor, data in actors.items():
            if not data["frames"]:
                continue
            for cycle in find_bad_cycles(actor, data["frames"], data["labels"]):
                findings += 1
                lines = [frame["line"] for frame in cycle]
                # Ad-hoc runs pass relative or outside-root paths; do not crash
                # on the report line when the path is not under REPO.
                try:
                    shown = path.resolve().relative_to(REPO)
                except ValueError:
                    shown = path
                print(f"{shown}: {actor}: zero-duration loop at "
                      f"lines {lines}")
                for frame in cycle:
                    if frame["act"]:
                        print(f"    line {frame['line']}: {frame['act'][:110]}")
    if findings:
        print(f"\n{findings} unconditional zero-duration state loop(s) in "
              f"{scanned} file(s)")
        return 1
    print(f"state loops: {scanned} DECORATE file(s) clean")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

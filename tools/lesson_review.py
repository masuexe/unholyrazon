#!/usr/bin/env python3
"""Review new commits against LESSONS.md and advance the reviewed-through cursor.

Reads the `<!-- reviewed-through: <hash> (...) -->` cursor from LESSONS.md,
inspects commits in `<cursor>..HEAD`, and flags:
  - rework / follow-up fixes and files touched by multiple commits
  - large commits lacking verification notes in the commit body
  - single-file class/weapon/item fixes that warrant a sibling sweep
  - existing LESSONS.md entries at Seen 2x+ (near the 3-day promotion bar)

Usage:
  python3 tools/lesson_review.py
  python3 tools/lesson_review.py --since <rev>
  python3 tools/lesson_review.py --mark-reviewed [rev]
  python3 tools/lesson_review.py --json
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LESSONS_PATH = REPO / "LESSONS.md"
CURSOR_RE = re.compile(r"^<!--\s*reviewed-through:\s*([0-9a-fA-F]+)(?:\s*\(([^)]+)\))?\s*-->")
SEEN_RE = re.compile(r"Seen\s+(\d+)×\s*\(([^)]+)\)")
VERIFY_KW_RE = re.compile(r"\b(verified|gate|test|probe|check|passed|benchmark)\b", re.I)
REWORK_KW_RE = re.compile(r"^(fix|revert|follow-?up|restore|rework)\b", re.I)


def run_git(*args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, timeout=60)
    if proc.returncode != 0:
        raise SystemExit(f"lesson_review: git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout


def parse_lessons(path: Path) -> tuple[str | None, str | None, list[dict]]:
    if not path.is_file():
        raise SystemExit(f"lesson_review: missing {path}")
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    cursor_hash, cursor_date = None, None
    if lines:
        m = CURSOR_RE.match(lines[0])
        if m:
            cursor_hash, cursor_date = m.group(1), m.group(2)

    entries = []
    current_rule = None
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("**") and stripped.endswith("**") and len(stripped) > 4:
            current_rule = stripped.strip("*")
        m_seen = SEEN_RE.search(stripped)
        if m_seen:
            entries.append({
                "rule": current_rule or "(unnamed)",
                "seen": int(m_seen.group(1)),
                "dates": m_seen.group(2),
            })
            current_rule = None
    return cursor_hash, cursor_date, entries


def collect_commits(rev_range: str) -> list[dict]:
    raw = run_git(
        "log",
        rev_range,
        "--date=short",
        "--numstat",
        "--format=__COMMIT__%x1f%H%x1f%h%x1f%ad%x1f%s%x1f%b__END_BODY__",
    )
    commits = []
    for block in raw.split("__COMMIT__\x1f"):
        if not block.strip():
            continue
        header_and_body, _, stat_text = block.partition("__END_BODY__")
        parts = header_and_body.split("\x1f", 4)
        if len(parts) < 5:
            continue
        full_hash, short_hash, date, subject, body = parts
        files = []
        churn = 0
        for line in stat_text.splitlines():
            if not line.strip():
                continue
            cols = line.split("\t", 2)
            if len(cols) != 3:
                continue
            add_s, del_s, fpath = cols
            files.append(fpath.strip())
            if add_s.isdigit():
                churn += int(add_s)
            if del_s.isdigit():
                churn += int(del_s)
        commits.append({
            "hash": full_hash.strip(),
            "short": short_hash.strip(),
            "date": date.strip(),
            "subject": subject.strip(),
            "body": body.strip(),
            "files": files,
            "churn": churn,
        })
    return commits


def analyze_commits(commits: list[dict]) -> dict:
    file_touches: dict[str, list[str]] = defaultdict(list)
    rework_commits = []
    large_unverified = []
    sibling_candidates = []

    for c in commits:
        for f in c["files"]:
            file_touches[f].append(c["short"])
        if REWORK_KW_RE.search(c["subject"]):
            rework_commits.append(c["short"] + " " + c["subject"])
        if (len(c["files"]) >= 10 or c["churn"] >= 300) and not VERIFY_KW_RE.search(c["body"]):
            large_unverified.append(
                f"{c['short']} ({len(c['files'])} files, {c['churn']} lines): {c['subject']}"
            )
        class_files = [
            f for f in c["files"]
            if f.startswith(("src/actors/classes/", "src/acs_source/classes/", "src/actors/items/"))
        ]
        if len(class_files) == 1 and REWORK_KW_RE.search(c["subject"]):
            sibling_candidates.append(f"{c['short']} ({class_files[0]}): {c['subject']}")

    overlap_files = {
        f: hashes for f, hashes in sorted(file_touches.items()) if len(hashes) >= 2
    }
    return {
        "rework_commits": rework_commits,
        "overlap_files": overlap_files,
        "large_unverified": large_unverified,
        "sibling_candidates": sibling_candidates,
    }


def mark_reviewed(path: Path, rev: str) -> tuple[str, str]:
    short_hash = run_git("rev-parse", "--short", rev).strip()
    commit_date = run_git("show", "-s", "--format=%ad", "--date=short", short_hash).strip()
    new_header = f"<!-- reviewed-through: {short_hash} ({commit_date}) -->"
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    if lines and CURSOR_RE.match(lines[0]):
        lines[0] = new_header + "\n"
    else:
        lines.insert(0, new_header + "\n")
    path.write_text("".join(lines), encoding="utf-8")
    return short_hash, commit_date


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--since", help="override start revision instead of LESSONS.md cursor")
    parser.add_argument("--mark-reviewed", nargs="?", const="HEAD", metavar="REV",
                        help="update LESSONS.md reviewed-through cursor (default: HEAD)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    if args.mark_reviewed:
        short_hash, commit_date = mark_reviewed(LESSONS_PATH, args.mark_reviewed)
        print(f"lesson_review: updated LESSONS.md cursor to {short_hash} ({commit_date})")
        return 0

    cursor_hash, cursor_date, entries = parse_lessons(LESSONS_PATH)
    since = args.since or cursor_hash
    if not since:
        raise SystemExit("lesson_review: no reviewed-through cursor in LESSONS.md; pass --since")

    head_short = run_git("rev-parse", "--short", "HEAD").strip()
    commits = collect_commits(f"{since}..HEAD")
    analysis = analyze_commits(commits)
    near_promotion = [e for e in entries if e["seen"] >= 2]

    if args.json:
        print(json.dumps({
            "cursor": {"hash": cursor_hash, "date": cursor_date},
            "since": since,
            "head": head_short,
            "commit_count": len(commits),
            "commits": [{"short": c["short"], "date": c["date"], "subject": c["subject"],
                         "files": len(c["files"]), "churn": c["churn"]} for c in commits],
            "analysis": analysis,
            "near_promotion": near_promotion,
        }, indent=2, ensure_ascii=False))
        return 0

    print(f"# Lesson Review ({since}..{head_short})")
    print(f"cursor: {cursor_hash or '(none)'} ({cursor_date or '?'})  commits: {len(commits)}")
    if not commits:
        print("No new commits since cursor.")
    else:
        print("\n## Commits in window")
        for c in commits:
            print(f"- {c['short']} {c['date']} [{len(c['files'])}f/{c['churn']}l] {c['subject']}")

        print("\n## Triage signals")
        print(f"- Rework / fix commits: {len(analysis['rework_commits'])}")
        for item in analysis["rework_commits"][:15]:
            print(f"  * {item}")
        print(f"- Multi-touch files (>=2 commits): {len(analysis['overlap_files'])}")
        for fpath, hashes in list(analysis["overlap_files"].items())[:15]:
            print(f"  * {fpath}: {', '.join(hashes)}")
        print(f"- Large commits without verification notes: {len(analysis['large_unverified'])}")
        for item in analysis["large_unverified"][:15]:
            print(f"  * {item}")
        print(f"- Single-file class/item fixes (sibling-sweep check): {len(analysis['sibling_candidates'])}")
        for item in analysis["sibling_candidates"][:15]:
            print(f"  * {item}")

    print("\n## Existing lessons at Seen 2x+ (promotion watch)")
    if not near_promotion:
        print("- (none)")
    else:
        for e in near_promotion:
            print(f"- Seen {e['seen']}x ({e['dates']}): {e['rule']}")

    print("\n## Next")
    print("1. Inspect flagged rework / overlap commits and update LESSONS.md.")
    print("2. Promote any Seen 3x+ lesson into AGENTS.md or tools/gate.py + tools/mutation_test.py.")
    print("3. Advance cursor: python3 tools/lesson_review.py --mark-reviewed")
    return 0


if __name__ == "__main__":
    sys.exit(main())

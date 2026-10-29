#!/usr/bin/env python3
"""
Helper script to extract code & definition files from reference PK3 archives
into a lightweight, agent-friendly directory structure under ../references.
"""

import argparse
import fnmatch
import json
import os
import sys
import zipfile
from pathlib import Path


CODE_EXTENSIONS = {
    ".dec", ".txt", ".acs", ".c", ".h", ".json", ".toml", ".yaml", ".yml",
    ".cfg", ".lua", ".py", ".sh", ".bat", ".o"
}

CODE_FILENAMES = {
    "DECORATE", "KEYCONF", "MAPINFO", "SNDINFO", "TEXTURES", "LOADACS",
    "TEAMINFO", "CVARINFO", "SCORINFO", "GAMEMODE", "MENUDEF", "GLDEFS",
    "ANIMDEFS", "SBARINFO", "LANGUAGE", "SNDSEQ", "TERRAIN"
}

BINARY_EXTENSIONS = {
    ".png", ".ogg", ".wav", ".mp3", ".mid", ".voc", ".flac", ".tga", ".dds"
}


def load_paths_config(repo_root: Path) -> dict:
    local_cfg = repo_root / "tools" / "paths.local.json"
    if local_cfg.is_file():
        try:
            with open(local_cfg, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[WARN] Failed to parse {local_cfg}: {e}", file=sys.stderr)
    return {}


def is_code_lump(filename: str) -> bool:
    name_upper = os.path.basename(filename).upper()
    ext = os.path.splitext(filename)[1].lower()

    if ext in BINARY_EXTENSIONS:
        return False
    if ext in CODE_EXTENSIONS or name_upper in CODE_FILENAMES:
        return True
    if filename.startswith("actors/") or filename.startswith("acs_source/") or filename.startswith("acs/"):
        return True
    return False


def safe_extract_zip(zip_path: Path, dest_dir: Path, code_only: bool = True) -> int:
    dest_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.infolist():
            if member.is_dir():
                continue
            name = member.filename
            # Prevent zip slip
            target_path = (dest_dir / name).resolve()
            if not str(target_path).startswith(str(dest_dir.resolve())):
                continue

            if code_only and not is_code_lump(name):
                continue

            target_path.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(member) as source, open(target_path, "wb") as target:
                target.write(source.read())
            count += 1
    return count


def find_matching_file(directory: Path, pattern: str) -> Path | None:
    if not directory.is_dir():
        return None
    matches = list(directory.glob(pattern))
    return matches[0] if matches else None


def main() -> int:
    parser = argparse.ArgumentParser(description="Unpack reference PK3s into agent-friendly code directories")
    parser.add_argument("--wads-dir", type=str, help="Path to directory containing .pk3 files")
    parser.add_argument("--out-dir", type=str, help="Destination references directory (default: ../references)")
    parser.add_argument("--all", action="store_true", help="Extract all files including sprites & audio (default: code-only)")
    parser.add_argument("--target", choices=["all", "mm8bdm-v6c", "mm8bdm-v6b", "classes-v9gh", "unholy-legacy"], default="all",
                        help="Specific package to unpack")
    parser.add_argument("--include-legacy", action="store_true",
                        help="Also unpack legacy Unholy packages (*unholy*.pk3 / *uh-*.pk3)")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    config = load_paths_config(repo_root)
    ref_cfg = config.get("references", {})

    wads_dir = Path(args.wads_dir) if args.wads_dir else Path(config.get("wads_dir", repo_root / "../wads")).resolve()
    out_dir = Path(args.out_dir) if args.out_dir else Path(ref_cfg.get("root") or os.environ.get("MM8BDM_REFERENCES_DIR") or repo_root / "../references").resolve()

    if not wads_dir.is_dir():
        print(f"[ERROR] WADs directory not found: {wads_dir}", file=sys.stderr)
        print("Please set --wads-dir or configure tools/paths.local.json", file=sys.stderr)
        return 1

    code_only = not args.all
    mode_desc = "Code & definitions only" if code_only else "Full package (all assets)"
    print(f"[*] Extracting references in mode: {mode_desc}")
    print(f"    From : {wads_dir}")
    print(f"    To   : {out_dir}")
    print()

    targets_to_run = []
    if args.target in ("all", "mm8bdm-v6c"):
        targets_to_run.append({
            "name": "MM8BDM v6c",
            "pattern": "mm8bdm-v6c*.pk3",
            "dest": out_dir / "for_8bdm-v6c" / "mm8bdm-v6c",
        })
    if args.target == "mm8bdm-v6b":
        targets_to_run.append({
            "name": "MM8BDM v6b",
            "pattern": "mm8bdm-v6b*.pk3",
            "dest": out_dir / "for_8bdm-v6b" / "mm8bdm-v6b",
        })
    if args.target in ("all", "classes-v9gh"):
        targets_to_run.append({
            "name": "CBM v9gh",
            "pattern": "classes-v9gh*.pk3",
            "dest": out_dir / "for_8bdm-v6b" / "classes-v9gh_",
        })

    if args.target == "unholy-legacy" or args.include_legacy:
        # Match legacy packages (*unholy*.pk3 / *uh-*.pk3), excluding current mod builds
        candidates = []
        for pat in ["*unholy*.pk3", "*uh-*.pk3", "*uh_*.pk3"]:
            for p in wads_dir.glob(pat):
                if not p.name.startswith("unholyrazon"):
                    candidates.append(p)
        seen = set()
        for cand in sorted(candidates):
            if cand.name not in seen:
                seen.add(cand.name)
                targets_to_run.append({
                    "name": f"Legacy package ({cand.stem})",
                    "pattern": cand.name,
                    "dest": out_dir / "for_8bdm-v6a" / cand.stem,
                })

    extracted_any = False
    for item in targets_to_run:
        match = find_matching_file(wads_dir, item["pattern"])
        if not match:
            print(f"[SKIP] {item['name']}: No file matching '{item['pattern']}' found in {wads_dir}")
            continue

        print(f"[UNPACK] {item['name']} from {match.name} -> {item['dest']}...")
        count = safe_extract_zip(match, item["dest"], code_only=code_only)
        print(f"         Extracted {count} files.")
        extracted_any = True

    if not extracted_any:
        print("\n[!] No matching archives were unpacked. Please ensure target PK3s are present in WADs dir.")
        return 1

    print("\n[*] Unpack completed. You can verify your setup with: python3 tools/check_environment.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())

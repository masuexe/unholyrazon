#!/usr/bin/env python3
"""
Unholy Razon — Example Addon Test & Runner Utility

Simplifies testing example addons without opening separate VS Code windows.
Compiles ACS sources, packages addons into PK3s, and launches Zandronum
with the correct MM8BDM v6b + Unholy Razon load order.

Usage:
  python3 tools/test_addon.py --list
  python3 tools/test_addon.py --build-all
  python3 tools/test_addon.py --build defineboss
  python3 tools/test_addon.py defineboss               # builds & launches in single-player
  python3 tools/test_addon.py teampresentation --map MM2DW1
  python3 tools/test_addon.py defineboss --dry-run     # prints launch command without running
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ADDONS = {
    "defineboss_addon": {
        "aliases": ["defineboss", "boss"],
        "desc": "Custom Boss registration via DefineBoss",
        "acs": [("acs_source/uh_exaddon.acs", "acs/uh_exaddon.o")],
        "default_args": ["+uh_sv_forcedboss1", "-1", "+map", "MM2DW1", "+sv_cheats", "1"],
    },
    "definesurvivor_addon": {
        "aliases": ["definesurvivor", "survivor", "surv"],
        "desc": "Custom Survivor registration via DefineSurvivor",
        "acs": [("acs_source/uh_exsurv.acs", "acs/uh_exsurv.o")],
        "default_args": ["+map", "MM2DW1", "+sv_cheats", "1"],
    },
    "teampresentation_addon": {
        "aliases": ["teampresentation", "presentation", "teampres", "tp"],
        "desc": "Custom class presentation (mugshot, scoreboard icon, team bar short name)",
        "acs": [("acs_source/uh_extp.acs", "acs/uh_extp.o")],
        "default_args": ["-lastmanstanding", "+sv_minplayers", "1", "+map", "MM2DW1", "+sv_cheats", "1"],
    },
    "eyemorph_addon": {
        "aliases": ["eyemorph", "demoneye", "eye"],
        "desc": "Custom Demoneye & private weighted eye morph pool",
        "acs": [("acs_source/uh_exeyemorph.acs", "acs/uh_exeyemorph.o")],
        "default_args": ["+map", "MM2DW1", "+sv_cheats", "1"],
    },
    "deathtips_addon": {
        "aliases": ["deathtips", "tips"],
        "desc": "Client-side death tip registry via UH_RegisterTip",
        "acs": [("acs_source/uh_extips.acs", "acs/uh_extips.o")],
        "default_args": ["+map", "MM2DW1", "+sv_cheats", "1"],
    },
    "lms_penalty_addon": {
        "aliases": ["lmspenalty", "lms", "penalty"],
        "desc": "Last-survivor LMS event with Bad LMS penalties",
        "acs": [("penalty.acs", "acs/LMSPENEX.o")],
        "default_args": ["-lastmanstanding", "+sv_minplayers", "1", "+map", "MM2DW1", "+sv_cheats", "1"],
    },
    "shinywep_addon": {
        "aliases": ["shinywep", "shiny"],
        "desc": "Shiny move-weapon override registration",
        "acs": [("acs_source/uh_exshiny.acs", "acs/uh_exshiny.o")],
        "default_args": ["+map", "MM2DW1", "+sv_cheats", "1"],
    },
    "bonus_event_settings": {
        "aliases": ["bonusevent", "event_settings", "events"],
        "desc": "Host configuration export and import sample (host.cfg)",
        "acs": [],
        "default_args": ["+exec", "examples/bonus_event_settings/host.cfg", "+map", "MM2DW1"],
    },
}


def resolve_addon_key(target: str) -> str | None:
    target_clean = target.strip().lower()
    if target_clean in ADDONS:
        return target_clean
    for k, v in ADDONS.items():
        if target_clean == k.lower():
            return k
        if target_clean in [a.lower() for a in v.get("aliases", [])]:
            return k
    return None


def find_acc(repo_root: Path) -> Path | None:
    env_acc = os.environ.get("ACC")
    if env_acc and Path(env_acc).is_file():
        return Path(env_acc)
    which_acc = shutil.which("acc")
    if which_acc:
        return Path(which_acc)
    candidates = [
        Path.home() / ".local" / "bin" / "acc",
        repo_root.parent / "references" / "zandronum" / "acc-branch-zandronum" / "acc",
        Path("/mnt/d/AppFiles/ACC/acc.exe"),
    ]
    for c in candidates:
        if c.is_file():
            return c
    return None


def compile_acs_targets(repo_root: Path, ex_dir: Path, acs_targets: list[tuple[str, str]], acc_bin: Path) -> bool:
    if not acs_targets:
        return True

    includes = [
        str(repo_root / "src/acs_source/v6b_overrides/_includes/common"),
        str(repo_root / "src/acs_source/v6b_overrides/_includes/mod_api"),
        str(repo_root / "src/acs_source/_includes/mod_api"),
        str(repo_root / "src/acs_source/_imports"),
        str(repo_root / "src/acs_source/hud"),
        str(repo_root / "src/acs_source/unholy"),
        str(ex_dir / "acs_source") if (ex_dir / "acs_source").is_dir() else str(ex_dir),
    ]

    inc_args = []
    for inc in includes:
        if Path(inc).exists():
            inc_args.extend(["-i", inc])

    for src_rel, out_rel in acs_targets:
        src_path = ex_dir / src_rel
        out_path = ex_dir / out_rel
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if not src_path.is_file():
            print(f"[ERROR] ACS source file not found: {src_path}", file=sys.stderr)
            return False

        cmd = [str(acc_bin)] + inc_args + [str(src_path), str(out_path)]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            print(f"[ERROR] ACC compilation failed for {src_rel}:\n{res.stderr}\n{res.stdout}", file=sys.stderr)
            return False
        print(f"  [ACC] Compiled {src_rel} -> {out_rel}")
    return True


def pack_addon(ex_dir: Path, out_pk3: Path) -> bool:
    out_pk3.parent.mkdir(parents=True, exist_ok=True)
    exclude_suffixes = {".acs", ".md", ".bak", ".tmp"}
    exclude_dirs = {"acs_source", ".git"}

    with zipfile.ZipFile(out_pk3, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(ex_dir):
            rel_dir = Path(root).relative_to(ex_dir)
            if any(part in exclude_dirs for part in rel_dir.parts):
                continue
            for file in files:
                if file.startswith(".") or any(file.endswith(s) for s in exclude_suffixes):
                    continue
                full_path = Path(root) / file
                arcname = str(full_path.relative_to(ex_dir))
                zf.write(full_path, arcname=arcname)
    size_kb = out_pk3.stat().st_size / 1024
    print(f"  [PK3] Packaged {out_pk3.name} ({size_kb:.1f} KB)")
    return True


def build_addon(key: str, repo_root: Path, acc_bin: Path | None) -> Path | None:
    addon_cfg = ADDONS[key]
    ex_dir = repo_root / "examples" / key
    if not ex_dir.is_dir():
        print(f"[ERROR] Example directory not found: {ex_dir}", file=sys.stderr)
        return None

    print(f"Building {key}...")
    acs_targets = addon_cfg.get("acs", [])
    if acs_targets:
        if not acc_bin:
            print("[ERROR] ACC compiler not found. Set ACC env var or install acc.", file=sys.stderr)
            return None
        if not compile_acs_targets(repo_root, ex_dir, acs_targets, acc_bin):
            return None

    if key == "bonus_event_settings":
        # Pure config example, no pk3 needed
        return ex_dir / "host.cfg"

    out_pk3 = repo_root / "out" / f"{key}.pk3"
    if not pack_addon(ex_dir, out_pk3):
        return None
    return out_pk3


def load_engine_config(repo_root: Path) -> dict:
    config = {
        "engine": None,
        "iwad": None,
        "base_files": [],
        "extra_files": [],
        "cvars": [],
    }

    # 1. Try .vscode/zandronum.json first
    vs_json = repo_root / ".vscode" / "zandronum.json"
    if vs_json.is_file():
        try:
            with open(vs_json, "r", encoding="utf-8") as f:
                data = json.load(f)
            for conf in data.get("configurations", []):
                if conf.get("name") == "Single Player":
                    prog = conf.get("linux", {}).get("program") or conf.get("program")
                    if prog:
                        config["engine"] = prog
                    pre_args = conf.get("preArgs", [])
                    for i, arg in enumerate(pre_args):
                        if arg == "-iwad" and i + 1 < len(pre_args):
                            config["iwad"] = pre_args[i + 1]
                        elif arg == "-file":
                            j = i + 1
                            while j < len(pre_args) and not pre_args[j].startswith("-"):
                                config["base_files"].append(pre_args[j])
                                j += 1
                    post_args = conf.get("postArgs", [])
                    for i, arg in enumerate(post_args):
                        if arg == "-file":
                            j = i + 1
                            while j < len(post_args) and not post_args[j].startswith(("-", "+")):
                                config["extra_files"].append(post_args[j])
                                j += 1
                        elif arg.startswith("+"):
                            config["cvars"].append(arg)
                            if i + 1 < len(post_args) and not post_args[i + 1].startswith(("-", "+")):
                                config["cvars"].append(post_args[i + 1])
                    break
        except Exception as e:
            print(f"[WARN] Failed to parse .vscode/zandronum.json: {e}", file=sys.stderr)

    # Fallbacks from env or launch.json
    if not config["engine"]:
        config["engine"] = os.environ.get("ZANDRONUM_EXE") or shutil.which("zandronum")
    if not config["iwad"]:
        cand = repo_root.parent / "wads" / "megagame.wad"
        if cand.is_file():
            config["iwad"] = str(cand)

    return config


def run_addon(key: str, repo_root: Path, addon_path: Path, engine_cfg: dict, extra_args: list[str], dry_run: bool = False, host: bool = False, connect: str | None = None, map_name: str | None = None) -> int:
    engine = engine_cfg.get("engine")
    if not engine or not (Path(engine).is_file() or shutil.which(engine)):
        print(f"[ERROR] Zandronum executable not found ({engine}). Set ZANDRONUM_EXE.", file=sys.stderr)
        return 1

    iwad = engine_cfg.get("iwad")
    if not iwad or not Path(iwad).is_file():
        print(f"[ERROR] IWAD megagame.wad not found ({iwad}).", file=sys.stderr)
        return 1

    main_mod = repo_root / "out" / "build.pk3"
    if not main_mod.is_file():
        print(f"[WARN] Main mod PK3 not found at {main_mod}. Packaged build is recommended.", file=sys.stderr)

    cmd = [str(engine), "-iwad", str(iwad)]

    # Collect load files in strict order:
    # 1. Base game & core patches
    files_to_load = []
    for f in engine_cfg.get("base_files", []):
        if Path(f).exists() and f not in files_to_load:
            files_to_load.append(f)

    # 2. Main mod PK3
    if main_mod.is_file() and str(main_mod) not in files_to_load:
        files_to_load.append(str(main_mod))

    # 3. Addon PK3 (if it's a pk3)
    if addon_path.suffix.lower() == ".pk3":
        files_to_load.append(str(addon_path))

    # 4. Sound & music packs
    for f in engine_cfg.get("extra_files", []):
        if Path(f).exists() and f not in files_to_load and "build.pk3" not in f and not f.endswith(f"{key}.pk3"):
            files_to_load.append(f)

    if files_to_load:
        cmd.append("-file")
        cmd.extend(files_to_load)

    # Gameplay mode & defaults
    addon_def_args = ADDONS[key].get("default_args", []).copy()
    if map_name:
        if "+map" in addon_def_args:
            idx = addon_def_args.index("+map")
            if idx + 1 < len(addon_def_args):
                addon_def_args[idx + 1] = map_name
        else:
            addon_def_args.extend(["+map", map_name])

    cmd.extend(addon_def_args)

    if host:
        cmd.extend(["-host", "-port", "10666", "+LastManStanding", "True", "-private", "-nobroadcast"])
    elif connect:
        cmd.extend(["-connect", connect])

    # Extra user args
    if extra_args:
        cmd.extend(extra_args)

    print("\n[LAUNCH] Starting Zandronum with command:")
    print(" ".join(cmd))
    print()

    if dry_run:
        print("[DRY RUN] Finished without launching process.")
        return 0

    return subprocess.run(cmd).returncode


def main():
    parser = argparse.ArgumentParser(description="Unholy Razon Example Addon Test Runner")
    parser.add_argument("addon", nargs="?", help="Name or alias of the addon to test (e.g. defineboss, presentation)")
    parser.add_argument("--list", "-l", action="store_true", help="List all available example addons")
    parser.add_argument("--build", "-b", metavar="ADDON", nargs="?", const="__CURRENT__", help="Build addon PK3 without launching")
    parser.add_argument("--build-all", "-a", action="store_true", help="Compile and package all example addons")
    parser.add_argument("--map", "-m", help="Map to load (default: MM2DW1)")
    parser.add_argument("--host", action="store_true", help="Host a local server")
    parser.add_argument("--join", metavar="IP:PORT", help="Join an existing server")
    parser.add_argument("--dry-run", "-n", action="store_true", help="Print the launch command without running")
    parser.add_argument("--engine", help="Override Zandronum executable path")
    args, unknown_args = parser.parse_known_args()

    repo_root = Path(__file__).resolve().parent.parent
    acc_bin = find_acc(repo_root)

    if args.list:
        print("Available example addons:")
        out_dir = repo_root / "out"
        for k, v in ADDONS.items():
            pk3 = out_dir / f"{k}.pk3"
            status = f"[built: {pk3.stat().st_size // 1024} KB]" if pk3.is_file() else "[not built]"
            aliases = ", ".join(v.get("aliases", []))
            print(f"  • {k:<25} {status:<20} (aliases: {aliases})")
            print(f"    {v.get('desc')}")
        return 0

    if args.build_all:
        print("Building all example addons...")
        success = True
        for k in ADDONS:
            res = build_addon(k, repo_root, acc_bin)
            if not res:
                success = False
        print("\nAll builds completed." if success else "\nSome builds failed.")
        return 0 if success else 1

    target = args.build if args.build and args.build != "__CURRENT__" else args.addon
    if not target:
        parser.print_help()
        return 0

    key = resolve_addon_key(target)
    if not key:
        print(f"[ERROR] Unknown addon '{target}'. Run with --list to see available addons.", file=sys.stderr)
        return 1

    built_path = build_addon(key, repo_root, acc_bin)
    if not built_path:
        return 1

    if args.build:
        print(f"Build done: {built_path}")
        return 0

    engine_cfg = load_engine_config(repo_root)
    if args.engine:
        engine_cfg["engine"] = args.engine

    return run_addon(
        key=key,
        repo_root=repo_root,
        addon_path=built_path,
        engine_cfg=engine_cfg,
        extra_args=unknown_args,
        dry_run=args.dry_run,
        host=args.host,
        connect=args.join,
        map_name=args.map,
    )


if __name__ == "__main__":
    sys.exit(main())

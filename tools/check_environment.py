#!/usr/bin/env python3
"""
Environment and references health check for Unholy Razon.
Inspects local toolchains (ACC, Python), runtime WADs, and reference trees.
"""

import argparse
import json
import os
import shutil
import sys
from pathlib import Path


def load_paths_config(repo_root: Path) -> dict:
    local_cfg = repo_root / "tools" / "paths.local.json"
    if local_cfg.is_file():
        try:
            with open(local_cfg, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[WARN] Failed to parse {local_cfg}: {e}", file=sys.stderr)
    return {}


def resolve_path(base_dir: Path, configured_val: str | None, default_rel: str) -> Path:
    if configured_val:
        p = Path(configured_val)
        return p if p.is_absolute() else (base_dir / p).resolve()
    return (base_dir / default_rel).resolve()


def check_file_or_dir(path: Path) -> bool:
    return path.exists()


def check_glob(base_dir: Path, pattern: str) -> bool:
    if not base_dir.is_dir():
        return False
    return any(base_dir.glob(pattern))


def check_any_glob(base_dir: Path, patterns: list[str]) -> bool:
    if not base_dir.is_dir():
        return False
    for pat in patterns:
        if any(base_dir.glob(pat)):
            return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Unholy Razon environment & reference assets")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument("--strict", action="store_true", help="Fail if Tier 2 or Tier 3 references are missing")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    config = load_paths_config(repo_root)

    ref_cfg = config.get("references", {})
    wads_dir = resolve_path(repo_root, config.get("wads_dir"), "../wads")
    ref_root = resolve_path(repo_root, ref_cfg.get("root"), "../references")

    acc_path = os.environ.get("ACC") or shutil.which("acc")
    python_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    # Item checklist
    results = {
        "toolchain": {
            "python": {"ok": sys.version_info >= (3, 10), "version": python_ver},
            "acc": {"ok": acc_path is not None, "path": acc_path or "NOT FOUND"},
        },
        "tier1_core": {
            "megagame_wad": {
                "ok": (wads_dir / "megagame.wad").is_file(),
                "path": str(wads_dir / "megagame.wad"),
                "desc": "MM8BDM base IWAD (runtime test dependency)",
            },
            "mm8bdm_v6b_pk3": {
                "ok": (wads_dir / "mm8bdm-v6b.pk3").is_file(),
                "path": str(wads_dir / "mm8bdm-v6b.pk3"),
                "desc": "MM8BDM v6b game package",
            },
            "mm8bdm_v6b_reference": {
                "ok": (ref_root / "for_8bdm-v6b" / "mm8bdm-v6b").is_dir() or (wads_dir / "mm8bdm-v6b.pk3").is_file(),
                "path": str(ref_root / "for_8bdm-v6b" / "mm8bdm-v6b"),
                "desc": "MM8BDM v6b source/actors (directory or pk3 in wads)",
            },
        },
        "tier2_template": {
            "cbm_v9gh": {
                "ok": (ref_root / "for_8bdm-v6b" / "classes-v9gh_").is_dir()
                or check_glob(wads_dir, "classes-v9gh*.pk3"),
                "path": str(ref_root / "for_8bdm-v6b" / "classes-v9gh_"),
                "desc": "CBM v9gh architectural template",
            }
        },
        "tier3_engine": {
            "zandronum_source": {
                "ok": (ref_root / "zandronum" / "zandronum-stable-branch-default").is_dir(),
                "path": str(ref_root / "zandronum" / "zandronum-stable-branch-default"),
                "desc": "Zandronum engine C++ source",
            },
            "acc_source": {
                "ok": (ref_root / "zandronum" / "acc-branch-zandronum").is_dir(),
                "path": str(ref_root / "zandronum" / "acc-branch-zandronum"),
                "desc": "ACC compiler source",
            },
        },
        "tier4_optional": {
            "unholy_legacy": {
                "ok": (
                    (ref_root / "for_8bdm-v6a").is_dir()
                    or check_any_glob(wads_dir, ["*unholy*.pk3", "*uh-*.pk3", "*uh_*.pk3"])
                ),
                "path": str(ref_root / "for_8bdm-v6a"),
                "desc": "Legacy Unholy packages (*unholy*.pk3 / *uh-*.pk3)",
            },
            "uix_v3bh": {
                "ok": (wads_dir / "8bdm-uix-v3bh.pk3").is_file(),
                "path": str(wads_dir / "8bdm-uix-v3bh.pk3"),
                "desc": "UIX v3bh addon package (for UIX test profile)",
            },
        },
    }

    if args.json:
        print(json.dumps(results, indent=2))
        tier1_ok = all(v["ok"] for v in results["tier1_core"].values())
        return 0 if tier1_ok else 1

    # Human-readable output
    print("==================================================")
    print("  Unholy Razon 4.0 - Environment & References Check")
    print("==================================================")
    print(f"Repository Root : {repo_root}")
    print(f"WADs Directory  : {wads_dir} ({'exists' if wads_dir.is_dir() else 'MISSING'})")
    print(f"References Root : {ref_root} ({'exists' if ref_root.is_dir() else 'MISSING'})")
    if config:
        print("Config File     : tools/paths.local.json (active)")
    else:
        print("Config File     : default relative paths (no paths.local.json)")
    print()

    print("[Toolchain]")
    print(f"  Python 3        : {'[OK]' if results['toolchain']['python']['ok'] else '[WARN]'} ({python_ver})")
    print(f"  ACC Compiler    : {'[OK]' if results['toolchain']['acc']['ok'] else '[ERROR]'} ({results['toolchain']['acc']['path']})")
    print()

    print("[Tier 1: Core Base Game (Required for Testing)]")
    t1_all_ok = True
    for key, item in results["tier1_core"].items():
        status = "[OK]" if item["ok"] else "[MISSING]"
        if not item["ok"]:
            t1_all_ok = False
        print(f"  {status} {key:22}: {item['desc']}")
        if not item["ok"]:
            print(f"         Expected at: {item['path']}")
    print()

    print("[Tier 2: Primary Architectural Template (Recommended)]")
    t2_all_ok = True
    for key, item in results["tier2_template"].items():
        status = "[OK]" if item["ok"] else "[MISSING]"
        if not item["ok"]:
            t2_all_ok = False
        print(f"  {status} {key:22}: {item['desc']}")
    print()

    print("[Tier 3: Engine & ACC Source (Reference Consultation)]")
    t3_all_ok = True
    for key, item in results["tier3_engine"].items():
        status = "[OK]" if item["ok"] else "[INFO]"
        if not item["ok"]:
            t3_all_ok = False
        print(f"  {status} {key:22}: {item['desc']}")
    print()

    print("[Tier 4: Optional Legacy & Test Addons]")
    for key, item in results["tier4_optional"].items():
        status = "[OK]" if item["ok"] else "[OPTIONAL]"
        print(f"  {status} {key:22}: {item['desc']}")
    print()

    if not t1_all_ok:
        print("[!] Tier 1 core dependencies are missing.")
        print("    Please place megagame.wad and mm8bdm-v6b.pk3 in your WAD directory,")
        print("    or configure tools/paths.local.json. See tools/REFERENCES.md for details.")
        return 1

    if args.strict and (not t2_all_ok or not t3_all_ok):
        print("[!] Strict check failed: Tier 2 or Tier 3 references are missing.")
        return 1

    print("[*] Environment check passed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

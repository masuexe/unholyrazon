# External References and Assets Guide

This document describes how Unholy Razon manages external references, base game assets, and companion mod packages.

---

## 1. Reference Tiers & Catalog

| Tier | Role | Package / Target | Purpose | Source / How to Obtain |
|---|---|---|---|---|
| **Tier 1 (Core)** | Base Game Engine Assets | `megagame.wad`<br>`mm8bdm-v6b.pk3` | Required for launching/testing the game. Agent reads ClassBase and core DECORATE/ACS. | Download MM8BDM v6b from [Cutstuff](http://cutstuff.net/mm8bdm/) |
| **Tier 2 (Recommended)** | Architectural Template | `classes-v9gh_.pk3` | Primary template for custom classes, weapon bars, inventory tokens, and assist items. | Download CBM v9gh from Cutstuff forums |
| **Tier 3 (Engine)** | Engine & Compiler Source | `zandronum-stable`<br>`acc-branch-zandronum` | Reference for Zandronum actor logic, netplay sync, and ACC compiler builtins. | [Zandronum Git/Mercurial](https://github.com/Zandronum/zandronum) |
| **Tier 4 (Optional)** | Legacy Mods & Addons | **Legacy Unholy archives & patches**<br>(`*unholy*.pk3` / `*uh-*.pk3`)<br><br>Test addons:<br>`8bdm-uix-v3bh`<br>`trill-damagedisplay` | Reference when porting legacy Unholy classes/bosses, verifying historical mechanics, or running full UIX test profiles. | [TSPG](https://allfearthesentinel.net/) / Community archives |

---

## 2. Recommended Workspace Layout

By default, the project expects sibling directories next to `unholyrazon`:

```text
parent_directory/
├── unholyrazon/                    # (This repository)
├── wads/                           # Runtime .wad / .pk3 files for testing (can be a symlink)
│   ├── megagame.wad
│   ├── mm8bdm-v6b.pk3
│   ├── 8bdm-v6b-miscfixes-v6h.pk3
│   └── ... (optional mods)
└── references/                     # Extracted / unpacked sources for code consultation
    ├── for_8bdm-v6b/
    │   ├── mm8bdm-v6b/             # Unpacked MM8BDM v6b code and actors
    │   └── classes-v9gh_/          # Unpacked CBM v9gh code and actors
    └── zandronum/
        ├── zandronum-stable-branch-default/
        └── acc-branch-zandronum/
```

> [!TIP]
> If your assets or references live in a different location, do **not** move them. Simply copy `tools/paths.json.example` to `tools/paths.local.json` and configure your paths, or set the `MM8BDM_REFERENCES_DIR` environment variable.

---

## 3. Setup Workflows for Modders & Agents

### Workflow A: Using Existing .pk3 Files (Quick Unpack)
If you already have `mm8bdm-v6b.pk3` and `classes-v9gh.pk3` in your WAD directory:
1. Place or symlink your WAD folder at `../wads`:
   ```bash
   ln -s /path/to/my/wads ../wads
   ```
2. Run the unpack helper to extract code-only files (DECORATE, ACS, TXT) into `../references`:
   ```bash
   python3 tools/unpack_references.py
   ```
   *This extracts definition files while skipping heavy audio and sprite textures, keeping disk usage minimal.*

### Workflow B: Custom Paths Configuration
1. Copy the example configuration:
   ```bash
   cp tools/paths.json.example tools/paths.local.json
   ```
2. Edit `tools/paths.local.json` to point to your local installation paths.

### Workflow C: Verification
Run the environment health check tool at any time:
```bash
python3 tools/check_environment.py
```
It will report which Tier 1/2/3/4 dependencies are detected and flag any missing elements.

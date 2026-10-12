# Unholy Razon

Unholy Razon is an open-source fork of **Unholy Unbound** (v7b), a Last Man Standing (LMS) gameplay mod for [Mega Man 8-Bit Deathmatch](https://mm8bdm.net/) (MM8BDM) originally rooted in [Unholy Classes & Bosses](https://mm8bdm.net/forum/thread/unholy-classes-bosses-v8a-in-progress-170).

## Overview

In Unholy, players fight in an asymmetric Last Man Standing arena where survivors face powerful bosses.

As a fork, **Unholy Razon** expands this core gameplay with new content, a modular addon architecture, dedicated UIX compatibility, and modernized technical tooling.

## Key Features

- **Extensible Addon API**: Register custom bosses, survivors, boss combos, and events via standalone PK3 addons without editing the core files.
- **Razon-Specific Content**: Includes exclusive classes, bosses, items, and specialized mechanics (such as MegaMan daily weapons).
- **UIX Compatibility**: Includes bundled compatibility for UIX Better Team Display and custom scoreboard icons.
- **Developer & Test Tooling**: Provides automated smoke tests, launch profiles, and reproducible ACS compilation scripts.

---

## Requirements and Load Order

Unholy Razon requires the following base files:
- **Engine**: [Zandronum](https://zandronum.com/) 3.3-alpha-251208-0355 or later.
- **IWAD**: `megagame.wad`.
- **Base Mod**: `mm8bdm-v6b.pk3`.

### Load Order

Load PK3 files in the exact order shown below:

| Order | File | Required | Notes |
|:---:|---|:---:|---|
| 1 | `mm8bdm-v6b.pk3` | **Yes** | Base MM8BDM game data. |
| 2 | `8bdm-v6b-miscfixes-v6h.pk3` | *Recommended* | Base-game bug fixes. |
| 3 | `8bdm-uix-v3bh.pk3` | *Optional* | UIX teammate display. Load before Unholy Razon. |
| 4 | `trill-pingbutton-v5h.pk3` | *Optional* | Ping button mod. Load before Unholy Razon. |
| **5** | **`out/build.pk3`** | **Yes** | **Unholy Razon core mod.** |
| 6+ | Custom Addons | *Optional* | Any third-party Unholy Razon addons. |

> [!IMPORTANT]
> If you use **UIX** or **PingButton**, load them **before** Unholy Razon. Loading them after Unholy Razon overwrites the bundled compatibility scripts.

### Launching the Game

Run Zandronum with the required files:

```bash
zandronum -iwad megagame.wad -file mm8bdm-v6b.pk3 8bdm-v6b-miscfixes-v6h.pk3 out/build.pk3
```

Ready-to-use launch profiles are available in `tools/mm8bdm-v6b.launch.json`.

---

## Modding and Addon API

Unholy Razon provides a public addon API via the `uhadd.acs` header.
External PK3 addons can register custom bosses, survivors, boss combos, and events at runtime without modifying the core mod files.
For comprehensive API specifications and guides, consult the [Documentation Index](docs/README.md).

To use the API, include `uhadd.acs` in your addon's ACS script:

```c
#include "zcommon.acs"
#include "uhadd.acs"

function void RegisterMyContent(void) {
    DefineBoss(-1, "MyBossActor", "\cjMy Boss", UHBOSS_POOL_COMMON, ...);
}
```

### Example Addons

Working addon templates are provided in the [`examples/`](examples/) directory. Each example includes a dedicated README with compilation and packaging instructions:

| Example | Description |
|---|---|
| [defineboss_addon](examples/defineboss_addon/) | Register a custom boss with `DefineBoss`. |
| [definesurvivor_addon](examples/definesurvivor_addon/) | Register a custom survivor with `DefineSurvivor`. |
| [eyemorph_addon](examples/eyemorph_addon/) | Weighted eye-morph pools. |
| [shinywep_addon](examples/shinywep_addon/) | Shiny move weapons. |
| [teampresentation_addon](examples/teampresentation_addon/) | Custom team presentation and portraits. |
| [deathtips_addon](examples/deathtips_addon/) | Custom death tips. |
| [lms_penalty_addon](examples/lms_penalty_addon/) | Custom LMS round penalties. |

### Reserved TIDs

Do not use the following TID ranges in custom actors or scripts. These ranges are reserved by MM8BDM v6b and Unholy Razon:

| TID Range | Origin | Assigned Usage |
|:---:|:---:|---|
| `-8690` | Unholy | Hail weather controller |
| `1000–1063` | MM8BDM | Players |
| `1100–1163` | MM8BDM / UH | Target aim points (`TargetAimPoint`) |
| `1500–1563` | Unholy | Eden blue portals (`player TID + 500`) |
| `1600–1663` | Unholy | Eden orange portals (`player TID + 600`) |
| `2000–2063` | MM8BDM | Initial player spawn points |
| `3000–3063` | MM8BDM | Exit Unit image actors |
| `4000–4063` | MM8BDM | Exit Unit point / ghost effects |
| `5400–5463` | Unholy | Nega Time Stopper anchor actors (`player TID + 4400`) |
| `5500–5563` | Unholy | Wisp anchor actors (`player TID + 4500`) |

### Reserved Translation IDs

Avoid the following Translation ID ranges when calling `CreateTranslation` in custom addons. Unholy Razon reserves these slots for players, teams, and class palettes:

| Translation ID Range | Assigned Usage |
|:---:|---|
| `3500–3563` | SiteWorkerShiny player colors (`3500 + PlayerNumber`, 64 slots) |
| `4001–4008` | Random color pool (`RNGCOLOR1–8`) |
| `4200–4206, 4209–4211` | Full-body dye colors (`FULLRED`, `FULLBLUE`, etc.) |
| `5001–5012, 5024–5025` | Preset colors (`SETCOLORA–L`, etc.) |
| `6606–6609` | Fixed team colors |
| `7000, 7064, 7164` | Paralyze effect and Eden projectile colors |
| `10460–10487, 10500–10515, 10572–10595` | Team base colors, variants, and Galaxy gradients (56 slots) |
| `19999` | ColdSummon solid black paint (`FISHBLACKPAINT_DYE`) |
| `20001–27013` *(discrete)* | Survivor class and skill palettes |
| `29001, 29010` | Death burning and white silhouette effects |
| `30000–34120` *(discrete)* | Shiny and special class palettes |
| `40000–44401` *(discrete)* | Boss class and skill palettes |
| `50000–51416` *(discrete)* | Demoneye, Bomber Eye, and Brick Eye variants |
| `52000–53023` | Dynamic Actor RGB translation cache (up to 1024 slots) |

> [!NOTE]
> Within the discrete ranges, only specific IDs are registered. Avoid overlapping with existing colors when adding custom class palettes.

### Feature & API Documentation

For in-depth specifications, refer to the guides in [`docs/`](docs/):

#### Modding APIs
- [Boss Combo API](docs/boss-combo-api.md) — Multi-boss combinations and stage music.
- [LMS Event API](docs/lms-event-api.md) — Mid-round events.
- [Identity Table CRUD Contract](docs/modding/uhdt-identity-crud-contract.md) — UHDT database manipulation.
- [Music Row Contract](docs/modding/uhdt-music-row-contract.md) — UHDT music registry schema.

#### Game Rules & Mechanics
- [Boss Stage Portraits](docs/boss-phase-portraits.md)
- [Bonus Winner Boss Choice](docs/bonus-boss-choice.md)
- [Bonus-Stage Music Pools](docs/bonus-music-pools.md)
- [AFK Penalties](docs/afk-penalties.md)
- [Round Thresholds](docs/round-thresholds.md)
- [Opening Copy-Weapon Counts](docs/copy-weapon-start-counts.md)
- [MegaMan Daily Weapons](docs/megaman-daily-weapons.md)

---

## Building from Source

There is no dedicated build system: Unholy Razon is a ZIP archive with a `.pk3` extension.
All build commands must be run from the repository root.

### Prerequisites

- **Tools**: Linux `zip` utility.
- **Compiler**: [Zandronum ACC](https://wiki.zandronum.com/ACC) (set via the `ACC` environment variable).

> [!IMPORTANT]
> **Compiler Requirement**:
> Use [Zandronum ACC](https://wiki.zandronum.com/ACC) with up-to-date headers (stock ZDoom ACC is not supported).
> Your headers must support Zandronum 3.x skin reflection symbols (`SPROP_TYPE_*` and two-argument `GetSkinProperty`).

### Directory Layout

Build scripts and launch profiles use relative paths. Place base files alongside this repository:

```
parent/
├── unholyrazon4/          # This repository
│   ├── src/               # Mod source files (packed into out/build.pk3)
│   ├── out/build.pk3      # Built PK3 output (git-ignored)
│   ├── docs/              # Documentation
│   ├── examples/          # Example addon PK3 sources
│   └── tools/             # Build and test scripts
├── wads/                  # megagame.wad, mm8bdm-v6b.pk3, miscfixes (can be a symlink)
├── references/            # Extracted/unpacked base game & template sources (see tools/REFERENCES.md)
├── unholyrazon_music/     # Optional: music packs for full launch profile
└── hudex/                 # Optional: HudMessage preview tool
```

### Environment & Toolchain Setup

1. **Verify toolchain and assets**:
   ```bash
   python3 tools/check_environment.py
   ```
   Checks for the `acc` compiler, test WADs (`megagame.wad`, `mm8bdm-v6b.pk3`), and external references.
   See [tools/REFERENCES.md](tools/REFERENCES.md) for reference catalogs, download links, and local path overrides (`tools/paths.local.json`).

2. **Unpack references for code consultation (Optional)**:
   If you have `.pk3` files in `wads/` and want lightweight, code-only reference trees for IDE/Agent code navigation:
   ```bash
   python3 tools/unpack_references.py
   ```

> [!TIP]
> For core codebase architecture, actor include chains, class hierarchies, and engineering conventions, see [AGENTS.md](AGENTS.md).

### Build Steps

1. **Compile ACS libraries.**
   Set the `ACC` path and run the compilation script:
   ```bash
   export ACC=/path/to/zandronum-acc
   ./tools/compile-acs.sh
   ```
   > [!NOTE]
   > This compiles all libraries listed in `src/LOADACS`, v6b overrides (`PROJTRAN`), and the boss-combo database (`UHCOMBDB`).

2. **Pack the PK3 archive.**
   Pack `src/` into `out/build.pk3`, excluding ACS source files, `.err` logs, and hidden files:
   ```bash
   cd src
   find . -type f ! -path "./acs_source/*" ! -name "*.err" ! -name ".*" | sed 's|^\./||' > /tmp/pk3files.txt
   rm -f /tmp/build.pk3 && zip -X -9 -q /tmp/build.pk3 -@ < /tmp/pk3files.txt
   cp /tmp/build.pk3 ../out/build.pk3
   cd ..
   ```

3. **Validate the build.**
   Run the verification script (a valid build outputs `status=ok`):
   ```bash
   ./tools/validate-build-pk3.sh
   ```

---

## Testing

### Automated Smoke Tests

Use the headless MCP test wrapper to run automated regression checks:

```bash
./tools/mcp/smoke-test.sh
./tools/mcp/smoke-test.sh --profile mm8bdm-v6b-full --json
```

The script requires Node.js, an MCP-enabled Zandronum build, and the `ZANDRONUM_EXE` and `ZANDRONUM_MCP_DIR` environment variables. Refer to [`tools/README.md`](tools/README.md) for complete details.

### VS Code Extension

If you use VS Code, install the [zandronum-vscode](https://github.com/masuexe/zandronum-vscode) extension. Use **Run Project** to compile ACS and launch the mod in a single step.

---

## Credits

- [MM8BDM](https://mm8bdm.net/): The base game and modding API.
- [Unholy](https://mm8bdm.net/forum/thread/unholy-classes-bosses-v8a-in-progress-170): The original mod.
- [Class Based Modification](https://mm8bdm.net/forum/thread/class-based-modification-v9gh-42): Core code references.
- [ACSUtils](https://github.com/Korshun/acsutils): Utility code adapted into `uh_acsutils.acs`.
- [ZandronumMCP](https://github.com/rc4l/ZandronumMCP): Automated testing and headless engine introspection.
- CBM Gondola Patch: Weapon offset references.
- Rebellion Unholy, Saxton Hale: Inspiration and concepts.

For detailed sprite, texture, and community asset attributions, see [CREDITS.md](CREDITS.md).

# Unholy Razon 4.0

Unholy Razon is a [Zandronum](https://zandronum.com/) mod for
[Mega Man 8-Bit Deathmatch](https://mm8bdm.net/) (MM8BDM), based on
[Unholy](https://mm8bdm.net/forum/thread/unholy-classes-bosses-v8a-in-progress-170).
It is built around a Last Man Standing (LMS) mode in which survivors fight
bosses, and it adds new classes, bosses, items, and bonus events, along with an
addon API that other modders can build on.

> **Target version:** MM8BDM **v6b**. The project will move to v6c once it is released.

## Requirements

- **Zandronum** (the engine).
- **MM8BDM v6b** base files:
  - `megagame.wad`
  - `mm8bdm-v6b.pk3`
  - `8bdm-v6b-miscfixes-v6h.pk3` (online play checks the whole file's MD5, so
    clients must use the same v6h file as the server)
- **ACC with Zandronum headers**, needed only to rebuild ACS. Point the build at
  your compiler with the `ACC` environment variable. The stock ZDoom headers are
  not enough, and the source also needs a few symbols that common Zandronum
  header sets lack. Your `zdefs.acs` and `zspecial.acs` must provide:
  - `GAMESTATE_*`, `GAMEEVENT_*`, `TM_*`, and `NamedExecuteClientScript`
  - `PLAYERSKIN_*` (0–3), `PLAYERSTATUS_*` (1, 2, 4, 8, 16, 32), and
    `SPROP_TYPE_*` (`SPROP_TYPE_STRING` = 4) in `zdefs.acs`
  - `GetSkinProperty` declared as `(2,4)` instead of `(3)` in `zspecial.acs`,
    because the source calls it with two arguments

  Values for these symbols come from the Zandronum engine source.

  > **Recommended (optional):** comment out `Floor`, `Round`, and `Ceil` in
  > `zspecial.acs`. They are ZDoom built-ins that Zandronum does not implement:
  > calls compile but return 0 at runtime. The current source does not use them,
  > so removing them only guards against accidental use.

## Directory layout

Launch profiles use paths relative to the repository root, so the base files
and optional addons live next to this repository:

```
parent/
├── unholyrazon4/          # this repository
│   ├── src/               # mod source, packed into out/build.pk3
│   ├── out/build.pk3      # build output (git-ignored)
│   ├── docs/              # feature and API docs
│   ├── examples/          # example addon PK3 sources
│   └── tools/             # build, validation, and test scripts
├── wads/                  # megagame.wad, mm8bdm-v6b.pk3, miscfixes
├── unholyrazon_music/     # optional, used by the full launch profile
└── hudex/                 # optional HudMessage preview tool
```

## Building

There is no build system: the mod is a ZIP archive with a `.pk3` extension.
On Linux, install `zip` first. Run everything from the repository root.

1. **Start from a clean `src/acs/`.** Stale compiled libraries can differ from
   fresh ones only by filename case (for example `projtran.o` vs `PROJTRAN.o`).
   On Linux that packs duplicate lumps, which breaks online authentication; on
   Windows the old files are silently overwritten.

   ```bash
   rm -rf src/acs
   ```

2. **Compile ACS.** Every library in `src/LOADACS`, the v6b override scripts
   (for example `PROJTRAN`), and the boss-combo registry (`UHCOMBDB`) must be
   compiled, or the game reports `Unknown script` at runtime.
   `tools/compile-acs.sh` builds all of them:

   ```bash
   export ACC=/path/to/zandronum-acc
   ./tools/compile-acs.sh
   ```

3. **Pack** `src/` into `out/build.pk3`, leaving out ACS sources, `.err` files,
   and dotfiles:

   ```bash
   cd src
   find . -type f ! -path "./acs_source/*" ! -name "*.err" ! -name ".*" | sed 's|^\./||' > /tmp/pk3files.txt
   rm -f /tmp/build.pk3 && zip -X -9 -q /tmp/build.pk3 -@ < /tmp/pk3files.txt
   cp /tmp/build.pk3 ../out/build.pk3
   cd ..
   ```

4. **Validate** the archive. A good build prints `status=ok`.

   ```bash
   ./tools/validate-build-pk3.sh
   ```

See [`tools/README.md`](tools/README.md) for more on rebuilding and troubleshooting.

## Running

Load the files in this order:

1. `megagame.wad`
2. `mm8bdm-v6b.pk3`
3. `8bdm-v6b-miscfixes-v6h.pk3`
4. `out/build.pk3`

### Manual testing

Launch Zandronum with the files above and start a map, for example
`+map MM2DW1`. Ready-made launch profiles are in
`tools/mm8bdm-v6b.launch.json` and `tools/mm8bdm-v6b-linux.launch.json`.

Passing both `+map` and `+quit` on the command line makes the engine quit before
the map loads, so do not use `+quit` for scripted checks; use the smoke test below.

### Automated testing

`tools/mcp/smoke-test.sh` reads a launch profile from `tools/*.launch.json`,
loads the files in the order above, enters a map, checks it, and exits cleanly:

```bash
./tools/mcp/smoke-test.sh
./tools/mcp/smoke-test.sh --profile mm8bdm-v6b-full --json
```

It needs Node.js, an MCP-enabled Zandronum build, and the `ZANDRONUM_EXE` and
`ZANDRONUM_MCP_DIR` environment variables. See [`tools/README.md`](tools/README.md).

### Using VS Code

If you use VS Code, the [zandronum-vscode](https://github.com/masuexe/zandronum-vscode)
extension can compile and launch the project in one step with **Run Project**.
It compiles every library in `LOADACS` plus everything they `#import`.

Run Project builds incrementally and never deletes old files from `src/acs/`.
If you have built with the scripts before or renamed a library, delete
`src/acs/` before running it, and run `./tools/validate-build-pk3.sh` after it
packs the PK3.

## Modding

Unholy Razon exposes an addon API, mainly through
`src/acs_source/_includes/mod_api/uhadd.acs`, so a second PK3 can register
bosses, survivors, weapons, and events without editing this mod.

**Example addons** (each folder has its own README with pack and compile steps):

| Example | Shows |
|---------|-------|
| [defineboss_addon](examples/defineboss_addon/) | Registering a custom boss with `DefineBoss` |
| [definesurvivor_addon](examples/definesurvivor_addon/) | Registering a custom survivor with `DefineSurvivor` |
| [eyemorph_addon](examples/eyemorph_addon/) | Weighted eye-morph pools |
| [shinywep_addon](examples/shinywep_addon/) | Shiny move weapons |
| [teampresentation_addon](examples/teampresentation_addon/) | Team presentation |
| [deathtips_addon](examples/deathtips_addon/) | Death tips |
| [lms_penalty_addon](examples/lms_penalty_addon/) | LMS penalties |

**API and feature docs:**

- [Boss Combo API](docs/boss-combo-api.md)
- [LMS Event API](docs/lms-event-api.md)
- [Identity table CRUD contract](docs/modding/uhdt-identity-crud-contract.md)
- [Music row contract](docs/modding/uhdt-music-row-contract.md)
- [Boss stage portraits](docs/boss-phase-portraits.md)
- [Bonus winner boss choice](docs/bonus-boss-choice.md)
- [Bonus-stage music pools](docs/bonus-music-pools.md)
- [AFK penalties](docs/afk-penalties.md)
- [Round thresholds](docs/round-thresholds.md)
- [Opening copy-weapon counts](docs/copy-weapon-start-counts.md)
- [MegaMan daily weapons](docs/megaman-daily-weapons.md)

### Reserved TIDs

| TID | Actors |
|-----|--------|
| 1000–1063 | Players |
| 1100–1163 | Vanilla `TargetAimPoint` |
| 1500–1563 | C396 Ventricle Razor blue portals (`player TID + 500`) |
| 1600–1663 | C396 Ventricle Razor orange portals (`player TID + 600`) |

Other mods loaded alongside Unholy Razon should avoid these ranges.

## Credits

- [MM8BDM](https://mm8bdm.net/): the base game and modding API
- [Unholy](https://mm8bdm.net/forum/thread/unholy-classes-bosses-v8a-in-progress-170): the original mod
- [Class Based Modification](https://mm8bdm.net/forum/thread/class-based-modification-v9gh-42): core code references
- [ACSUtils](https://acsutils.strangled.net/): utility code adapted into `uh_acsutils.acs`
- CBM Gondola Patch: weapon offset references
- Rebellion Unholy, Saxton Hale: ideas

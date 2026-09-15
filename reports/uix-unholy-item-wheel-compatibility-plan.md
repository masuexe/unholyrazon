# UIX v3bh / Unholy Item Wheel Compatibility Plan

## Goal

Add project-owned compatibility for `8bdm-uix-v3bh` so selected Unholy usable
items appear in UIX's inventory wheel, without forking UIX or replacing its
wheel implementation.

The first implementation is deliberately a two-item experiment. It should
prove registration timing, display, selection, use, and online behavior before
the compatibility list is expanded.

## Source findings

UIX does not discover arbitrary `CustomInventory` actors or actors carrying
`+INVBAR`. `UIXITEMS.acs` builds its item wheel from MM8BDM's shared DTADD
Assist Item table:

- `getAssistItemActor`
- `getAssistItemTag`
- `getAssistItemIcon`
- `getAssistItemAmount`
- `getAssistItemGroup`

Unholy currently registers its items only through `DefineUnholyItem` in
`src/acs_source/items/definitions/uh_itemdefs.acs`. That is an Unholy-owned
database and is invisible to UIX. Although `UnholyItem` already has `+INVBAR`,
that flag alone does not add an item to UIX's table.

UIX's own README recommends restaging addon definitions on the client. Its
`UIX_DataStaging` script manually calls known addons' table-definition scripts
in network games. UIX v3bh does not know about Unholy and therefore never calls
an Unholy registration script.

## Chosen architecture

Keep the compatibility layer in this repository and let UIX continue to own
all wheel rendering, input, selection, and item activation.

The compatibility layer will:

1. run as an Unholy ACS library;
2. detect UIX using a UIX-owned actor class;
3. register an explicit allowlist through MM8BDM's `DefineAssistItem` API;
4. run clientside early enough for `UIX_ItemWheelInit` to see the rows;
5. set `mapValid` to false so the rows are not advertised as normal map items;
6. avoid copying or overriding `UIXITEMS`, `UIXWHEEL`, or UIX keybind scripts.

This is intentionally not automatic registration from the `UnholyItem` actor
base. Each UIX row needs an explicit name, inventory actor, icon, pickup amount,
and semantic group, and many Unholy inventory actors should never be shown.

### Compatibility directory layout

The repository already has RockForce compatibility in
`src/acs_source/compat/rockforce/uh_modcheck.acs`. External-mod compatibility
should have a dedicated namespace rather than sharing one flat directory with
legacy compatibility:

```text
src/acs_source/compat/
├── legacy/
│   └── uh_legacy.acs
└── mods/
    ├── rockforce/
    │   └── uh_modcheck.acs
    └── uix/
        └── uh_uix.acs
```

This separates two different responsibilities:

- `compat/legacy/` preserves compatibility with old Unholy behavior or APIs;
- `compat/mods/` integrates independently distributed external mods.

Move the existing RockForce source from `compat/rockforce/` to
`compat/mods/rockforce/` when implementing this plan. This is a source-layout
change only: keep its `#library "uh_modcheck"`, compiled lump name
`uh_modcheck.o`, named scripts, and `LOADACS` entry unchanged. Update only the
source path in `tools/compile-acs.sh`. Do not mix functional RockForce changes
into the move.

## Minimal experiment

Start with these two inventory actors:

| Item | Actor | Icon | UIX/DTADD group | Reason |
|------|-------|------|------------------|--------|
| Rubber Band | `RubberBandItem` | `PANBOX18` | `DTADD_GRP_ATTACK` | Simple active projectile item with a stable icon |
| Periwinkle Tank | `PeriwinkleTankItem` | `MYSBOX01` | `DTADD_GRP_HEAL` | Simple active power item in a different wheel group |

Do not register their `Auto*`, silent, FX, powerup, or helper actors.

Proposed registration:

```c
function void UH_UIX_RegisterExperimentalItems(void)
{
    DefineAssistItem(
        "Rubber Band",
        "RubberBandItem",
        "PANBOX18",
        1,
        DTADD_GRP_ATTACK,
        false
    );

    DefineAssistItem(
        "Periwinkle Tank",
        "PeriwinkleTankItem",
        "MYSBOX01",
        1,
        DTADD_GRP_HEAL,
        false
    );
}
```

Plain display names are sufficient for the experiment. A later pass may use
LANGUAGE keys if UIX rendering and localization behavior warrant it.

## Proposed files and edits

### 1. Add the compatibility library

Create:

`src/acs_source/compat/mods/uix/uh_uix.acs`

Suggested shape:

```c
#library "uh_uix"

#include "zcommon.acs"
#include "DTADD.acs"

function void UH_UIX_RegisterExperimentalItems(void)
{
    // The two DefineAssistItem calls shown above.
}

script "uh_uix_register_items" OPEN CLIENTSIDE
{
    if (!ActorExists("UIX_ItemSelected_PU"))
        terminate;

    UH_UIX_RegisterExperimentalItems();
}
```

Use `#include "DTADD.acs"`; this library only needs the public registration
wrapper. Do not import or duplicate UIX's private data arrays.

The detection class is defined by UIX v3bh and is directly associated with its
item-wheel implementation. Before implementation, confirm there is no likely
class-name collision in the selected addon stack.

### 2. Load the library

Add `uh_uix` to `src/LOADACS` near the other definition/compatibility
libraries, before runtime libraries where practical. Do not remove or reorder
existing entries unnecessarily.

### 3. Compile it

Add the new source to `tools/compile-acs.sh`, emitting:

`src/acs/uh_uix.o`

Follow the script's existing include order: v6b override includes before
UH-owned includes. Do not introduce a new build system.

In the same mechanical edit, update the existing `uh_modcheck` compile source
path from:

`src/acs_source/compat/rockforce/uh_modcheck.acs`

to:

`src/acs_source/compat/mods/rockforce/uh_modcheck.acs`

Its output must remain `src/acs/uh_modcheck.o`, so no `LOADACS` change is
required for RockForce compatibility.

### 4. Add UIX to a focused launch profile

For runtime testing, create or extend a focused profile rather than changing
the default smoke profile for every test. Preserve package order:

1. MM8BDM v6b
2. v6b misc fixes
3. `out/build.pk3`
4. `8bdm-uix-v3bh`

The exact Unholy/UIX order should also be reversed once as a compatibility
probe. Supporting arbitrary order is desirable, but the documented supported
order should be the order that reliably satisfies UIX's startup snapshot.

## Initialization constraint

`UIX_ItemWheelInit` delays three tics, waits for the base item and buster tables,
then snapshots their sizes and properties. It does not expose an obvious public
refresh operation in v3bh.

Therefore the Unholy registration script must not add a delay. The first test
must establish that its `OPEN CLIENTSIDE` execution completes before UIX takes
the snapshot. If the result depends on package or `LOADACS` ordering:

1. document a supported load order for the minimal integration;
2. investigate a small upstream UIX refresh/hook API as the long-term fix;
3. do not override UIX's named initialization script from Unholy.

A timing workaround based on guessing a longer delay is not acceptable because
it would still run after UIX's one-time snapshot.

## DTADD side effects and limits

`DefineAssistItem` writes to MM8BDM's shared Assist Item table; it is not a
UIX-exclusive API. Even with `mapValid = false`, consumers that request items
without a map-validity filter may observe the added rows. The experiment must
check for regressions in relevant MM8BDM item selection and training behavior.

The table limit is 100 rows. Core v6b defines 18 items, while Unholy currently
has 88 identity rows, before any other addons are counted. Consequently:

- never mirror every `DefineUnholyItem` row automatically;
- keep a hand-reviewed allowlist;
- check the return value of `DefineAssistItem` in the eventual production code;
- fail quietly or emit one diagnostic when no slot is available;
- leave capacity for other addons;
- consider an explicit configurable maximum before expanding support.

For the two-item experiment, record both returned indices. A return value of
`-1` means the global table was already full and the experiment is invalid.

## Item safety concern

UIX changes selected inventory order by taking registered item actors and giving
them back. This must not be assumed harmless for every Unholy actor. Each item
added to the allowlist must be checked for:

- pickup-state side effects;
- `+ALWAYSPICKUP` or unusual `Inventory.MaxAmount` behavior;
- count changes after UIX selection;
- automatic activation on give/pickup;
- dependencies on inventory ordering;
- server/client divergence.

Only the normal held actors are registered in the experiment. Their `Auto*`
variants explicitly activate from `Pickup` and must not be registered.

## Verification plan

### Static and compile checks

1. Compile `uh_uix.acs` with the project's existing ACC command and include
   order.
2. Compile all ACS with `tools/compile-acs.sh`.
3. Package `src/` recursively into `out/build.pk3` using the existing project
   process.
4. Confirm `src/LOADACS` contains `uh_uix` and the PK3 contains
   `acs/uh_uix.o`.
5. Confirm no reference files under `../references/` changed.
6. Confirm moving `uh_modcheck.acs` changed only its path and compile command,
   not its source contents, library name, output lump, or `LOADACS` entry.

### Without UIX

1. Launch the normal focused MM8BDM + Unholy profile.
2. Confirm no unknown-script, missing-actor, or ACS startup errors.
3. Confirm both experimental items retain their ordinary pickup/use behavior.
4. Confirm the compatibility script terminates without registering rows.

### With UIX, offline

1. Give `RubberBandItem` and `PeriwinkleTankItem` separately and together.
2. Open the item wheel and confirm both names and icons display.
3. Confirm they appear in Attack and Recovery respectively.
4. Select each item without using it; verify inventory counts do not change.
5. Use each item through UIX; verify exactly one item is consumed.
6. Verify Rubber Band fires once and Periwinkle Tank grants its expected powers.
7. Close/reopen the wheel after an item reaches zero and confirm it disappears.
8. Pick up another copy and confirm it reappears.

### With UIX, network game

1. Test a server and at least one client using the supported package order.
2. Confirm every client builds the same two UIX rows locally.
3. Confirm selecting an item does not alter server inventory count.
4. Confirm using it consumes exactly one server-authoritative item.
5. Confirm no duplicate projectile, sound, or power grant occurs.
6. Reconnect and respawn, then repeat the inventory/wheel checks.
7. Inspect startup/runtime logs for DTADD limit warnings and unknown scripts.

### Load-order probe

Repeat the basic wheel visibility test with UIX before Unholy. If it fails,
retain one documented supported order and record the failure as an upstream
initialization limitation rather than replacing UIX internals.

## Acceptance criteria for the experiment

The experiment is successful only if:

- the mod still starts normally without UIX;
- both items appear with the correct icon and group when UIX is present;
- item selection preserves counts;
- item use consumes exactly one and produces exactly one effect;
- offline and network behavior agree;
- no DTADD capacity warning occurs in the focused profile;
- no UIX source file or reference package is modified.

## Expansion after the experiment

After the two items pass, add items in small batches. Maintain a table containing
the actor, display tag/name, icon, amount, group, and a note confirming that UIX
Take/Give reordering is safe.

Exclude by default:

- `Auto*` and silent variants;
- FX, flags, powers, and helper inventory;
- passive items;
- intermediate inventory actors generated by another item;
- actors not safely usable through normal inventory activation;
- items without stable icons;
- class-internal items whose ordering or ownership has special meaning.

Weapon bar compatibility is a separate phase. It should audit Unholy weapons
using ScriptBars and add `<WeaponActor>_ArsenalBar` and, where necessary,
`<WeaponActor>_SecondArsenalBar` actors. It is not part of this item-wheel
experiment.

## Rollback

The compatibility is isolated. Rollback consists of removing `uh_uix` from
`LOADACS`, removing its compile entry, and deleting the new compatibility
source. If the directory cleanup is also rolled back, move `uh_modcheck.acs`
back to `compat/rockforce/` and restore its old compile source path. No Unholy
item actor or UIX source needs to be reverted.

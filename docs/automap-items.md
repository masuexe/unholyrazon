# Unholy pickup automap

World Unholy pickups show their own icons on the automap, including all 88
registered items, automatic/silent variants, thrown collectible hats, coins,
food, Gauntlet treasure/exit, and the class-specific food and reward pickups.
The generated catalog covers 378 actor classes through 169 Spawn entry points,
using 117 centered icons from existing artwork. All viewers may see available
pickup locations. Held inventory, consumed pickups, and respawn waits have no
icon. Original MM8BDM health, energy and weapon pickups are outside this scope;
attack actors and visual effects are not pickups.

True Power cycles through the original Unbound colors in the same frame order,
at four tics per frame. Its automap cycle continues while the map is closed;
short-lived marker refreshes do not restart it.

Both console switches default to true:

- `uh_cl_automap_items`: the viewer's personal switch.
- `uh_sv_automap_items`: the server's switch for everyone.

These replace the prototype's `uh_*_automap_boxes` settings. Open the normal
automap with its bound key (normally Tab). For a cheat-enabled local check,
use `summon BEESItem`, `summon FortuneCoinItem`, or `summon TankOfWondersItem`.
Pick up an item and check that its icon disappears; dropping it should make it
appear again after the brief pickup delay. Repeat as a remote client and as a
spectator joining after items were spawned.

## Implementation and additions

The pickup portion of v6c's MAUTOMAP is backported into the current v6b base.
Player markers keep the existing Unholy behavior. The shared runtime is
`src/acs_source/items/item_automap.acs`, included in `uh_items` without adding
or changing LOADACS entries. Only availability integers cross the network;
clients resolve `<pickup class>_MapMarker` from their local actor class.

Each pickup starts `uh_ItemAutomapStart` once at its Spawn entry. A separate
`UH_ItemSpawn` label keeps the added startup actions outside the original
sprite loop. The two Yellow Wizard food actors use NoDelay on their initial
frame to preserve their original first-frame countdown delay.

The server retries client startup every 35 tics for late joiners and sends
availability changes immediately. This is necessary because the engine does
not sync SPECIAL's restoration after a manual inventory drop's pickup delay.
Each client runs one loop per world pickup and emits short-lived markers only
while the automap and both switches are on and availability is true. Markers
expire within two tics when the pickup disappears or display is disabled.

Run `python3 tools/gen_item_automap.py` after adding or changing a pickup's Spawn
artwork, or `python3 tools/gen_item_automap.py --check` to verify generated
resources and hook coverage. Do not hand-edit `TEXTURES.automap` or
`actors/items/AutomapMarkers.generated.dec`, or the generated ACS animation
constants in `items/item_automap_frames.generated.acs`. The generator reads local actor
ancestry and first visible Spawn artwork; it includes the items directory and
explicit class-specific pickup families in EXTRA_ROOTS. It also verifies every
built-in DefineUnholyItem row is covered. Items overriding Spawn need their own
startup hook, while inherited Spawn variants reuse the parent hook.
True Power's complete frame sequence and timing are derived from its existing
world Spawn animation, which matches Unbound v7b pb1. Composite frame patch layers
are copied with their translations so they do not depend on TEXTURES load order.

Addons may inherit a hooked Spawn and supply `<class>_MapMarker` for their own
icon. An unknown subclass falls back to the generic Unholy item icon. An addon
overriding Spawn must call `uh_ItemAutomapStart` itself. No actor registration
id or ACS string is sent over the network.

## Validation

Verified on local Zandronum 3.3-alpha and a dedicated server with one remote
client. All 88 registered item icons passed the bulk check locally and remotely;
bulk removal left no markers. Additional checks cover automatic/silent items,
collectible hats, treasure, food, class rewards, real non-box pickup and manual
drop, the personal switch, and late spectator joins. Bulk ACS instruction
profiling is a focused runtime check, not a 64-player network bandwidth or
frame-time benchmark. The original box
tests also cover both drop paths, availability and respawn. These focused
checks do not replace a long-running LMS gameplay soak.

True Power's generated sequence is checked against the Unbound v7b pb1 source;
live local frame samples follow the same color cycle, and remote samples also
advance. Both clients clear the animated marker on removal. The final startup
log has no unknown-patch warnings for the composite color frames.

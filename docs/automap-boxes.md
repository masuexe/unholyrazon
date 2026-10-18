# Box automap prototype

World Pandora and Mystic boxes now show their own icons on the automap,
including dropped boxes and the automatic variants that inherit their Spawn
states. All players may see these pickup locations. Boxes held in inventory,
consumed boxes, and boxes waiting to respawn have no icon.

Both switches default to true:

- `uh_cl_automap_boxes`: the viewer's personal switch.
- `uh_sv_automap_boxes`: the server's switch for everyone.

Open the normal automap with its bound key (normally Tab). The switches are
console settings in this prototype. Other Unholy pickups are outside this scope.

For a manual check in a cheat-enabled local game, use `summon PandoraBoxItem`
and `summon MysticBoxItem`, then open the automap. Pick up a box and check that
its icon disappears; `drop PandoraBoxItem` / `drop MysticBoxItem` should make
it appear again after the brief pickup delay. Repeat with a remote client,
including a spectator joining after the boxes were spawned.

The implementation backports the pickup part of v6c's `MAUTOMAP.acs` to the
current v6b base. It uses the existing box artwork, centered in TEXTURES, and
the v6c `<pickup class>_MapMarker` naming convention. It does not load or replace
the full v6c automap library; player markers keep their existing Unholy behavior.

The server retries client startup every 35 tics for late joiners. Each client
starts only one loop per box and creates two-tic markers only while the automap
and both switches are on and the server reports that the pickup has SPECIAL.
Availability changes are sent immediately: the engine does not sync SPECIAL's
restoration after a manual inventory drop's pickup delay. A hidden pickup's loop
waits for it to become available again. Becoming held inventory or being
destroyed stops the loop. Existing marker frames expire within two tics.

When extending coverage, verify actual pickup, removal, moving drops, respawn,
map reset and joining after the pickup was spawned. Dedicated-server checks
must inspect remote-client markers; a local script invocation alone cannot
prove network delivery.

## Validation

Tested with the v6b smoke package order on local Zandronum 3.3-alpha and a
dedicated server with one remote client. Local checks cover both icons,
client/server switches, closing the automap, real pickup, removal, and held
inventory. Network checks cover late spectator join/reconnect, actual pickup,
manual drops, the DropItem path used by death drops, removal, availability
transitions, and a temporary derived box with a two-second respawn delay,
including the hidden wait and restored icon. This is a focused prototype check,
not a full LMS soak test.

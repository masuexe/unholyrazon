# AFK penalties

Razon3's AFK penalties are available in **Unholy Server Options → Game Rules →
AFK Penalties**. They are disabled by default.

Example server configuration: GUHU after 60 seconds without gameplay input,
with the engine's separate forced-spectator policy disabled:

```cfg
sv_afk2spec 0
rz_sv_noafk_item 2
rz_sv_noafk_delay 60
```

`rz_sv_noafk_item` preserves the old `RZ_NoAFK_Item` mode numbers:

| Value | Penalty |
|-------|---------|
| -1 | Disabled (default) |
| 0 | Random choice among the five penalties |
| 1 | On Fire |
| 2 | GUHU |
| 3 | Super GUHU (the old fixed mode's round-timeout variant, `SGEXDItem`) |
| 4 | Money Bait detonation at the player |
| 5 | Money Bomb detonation at the player |

Other mode values disable the feature. As in Razon3, the random pool uses
ordinary `AutoSuperGUHUItem` for its Super GUHU choice. Penalties retain their
existing damage, protections, sounds and effects; explosions can affect other
players. Resuming input cancels the AFK timer, but does not undo a penalty that
has already started.

`rz_sv_noafk_delay` replaces `RZ_NoAFK_Delay`: seconds, default 60, clamped to
30–300 both in the menu and at runtime. Changing either setting resets all
players' pending timers. Old CVAR names are not aliases; update server configs.

One server-side watcher samples input every tic. Buttons, horizontal/vertical
aim input and all three movement axes reset the timer. A sniper standing still
and looking for enemies remains active. Merely being pushed or transported
does not count as input. Chatting alone does not reset this gameplay timer.

Only living human participants during `GAMESTATE_INPROGRESS` are eligible.
Waiting, countdown, results, ended Unholy rounds, spectators (including dead
spectators) and bots clear the timer. Enter, respawn, death and disconnect clear
the player's slot immediately; a change of pawn class also starts a fresh timer.
This avoids attaching duplicate scripts to revived or morphed player actors.

The player receives a warning ten seconds before the penalty. After a penalty,
the timer starts over if the player is still alive and still eligible, matching
Razon3's repeated-penalty behavior.

`sv_afk2spec` remains independent. The mod logs one warning per map if both
policies are enabled, including when enabled mid-round. It does not change the
engine setting or reset the engine's activity timestamp. Leave it at zero to
use mod penalties as the replacement for forced spectating.

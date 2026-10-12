# Zangief charge pull

`uh_sv_zangiefpull` is a server boolean, enabled by default. Hosts can change it
under **Unholy Server Options → Game Rules → Zangief Charge Pull**, or set it in
the server console/config:

```text
uh_sv_zangiefpull false
```

Set it to `true` to enable the effect again. Changes apply to the next charge
pulse, including an ongoing charge.

This restores the Razon3 3.11.1 weapon's `AltFire2` pull: hold **alternate fire**
while charging Atomic Buster. Normal Zangief uses maximum force 25 and Shiny
Zangief uses 50. Each charge tic pulls live players horizontally toward the
charger within 250 map units, with linear distance falloff rounded upward.
Targets at distance 40 or less are left alone. The legacy `Swap=2` filter
excludes players carrying `PowerProtectBoss`; native team modes also exclude
teammates. As in Razon3, the pull does not require line of sight.

The source attaches this to alternate fire, regardless of which mouse button
is bound to that action. Disabling the setting retains the current charging,
spin, grab, damage and ammo behavior. The pull runs on the server and has no
delayed loop to persist after charging ends or the player morphs.

Historical sources: `actors/Wep/Zangief_W.txt`,
`actors/Wep/Shiny/S_Zangief_W.txt` and `acs_source/U_B_ACS.acs` in the read-only
`uh-ub_razonpatch_3.11.1` reference package.

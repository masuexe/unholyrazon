# Unholy Razon 4.0

Unholy Razon is a mod based on [Unholy](https://mm8bdm.net/forum/thread/unholy-classes-bosses-v8a-in-progress-170).

## Planned Features
- Compatible with MM8BDM-v6c (since it is not released yet, the project is now compatible with MM8BDM-v6b temporarily)
- New classes, bosses, items and bonus events
- More extensible API

## Credits
- [MM8BDM](https://mm8bdm.net/): for the base game and the modding API
- [Unholy](https://mm8bdm.net/forum/thread/unholy-classes-bosses-v8a-in-progress-170): for the original mod
- [Class Based Modification](https://mm8bdm.net/forum/thread/class-based-modification-v9gh-42): for core code references
- [ACSUtils](https://acsutils.strangled.net/): for the utility code adapted into `uh_acsutils.acs`
- CBM Gondola Patch: for weapon offset providing references
- Rebellion Unholy, Saxton Hale: for some ideas

## TID Notes for Modders
| TID | Actors |
|------|------|
|1000 - 1063 | Players |
|1100 - 1163 | Vanilla TargetAimPoint |
|1500 - 1563 | C396 Ventricle Razor Blue portals (`player TID + 500`) |
|1600 - 1663 | C396 Ventricle Razor Orange portals (`player TID + 600`) |

C396 previously used `1100 - 1163` for its blue portals. That conflicted with
the vanilla `TargetAimPoint` range and is no longer used. The documented C396
ranges are free in MM8BDM v6b and this project; other loaded mods should avoid
them as well.

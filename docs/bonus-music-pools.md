# Bonus-stage music pools

Built-in entries live in `src/acs_source/systems/music/uh_musicdefs.acs`, in
`UH_RegisterBonusEventMusic`. Add a track with the same event id to extend that
stage's pool:

```acs
AddBonusEventMusic(UHEVENT_MLG, "M_MYTRACK", "Track title", "Album", "Artist", 1, 0);
```

The last arguments are weight and optional. Positive weights determine relative
selection probability. Optional entries require `uh_sv_optionalmusic`. Audio
belongs in the separate music package; these entries contain metadata only.

For an addon, include `uhadd.acs` and register from an `OPEN` script after the
bonus event is defined. Use its returned id, or resolve its stable stem:

```acs
AddBonusEventMusicByStem("mlg_eyes", "M_MYTRACK", "Track title", "Album", "Artist", 1, 0);
DisableEventMusic(UHMUS_KIND_BONUS, UHEVENT_MLG, "M_EYE01 10");
```

`EnableEventMusic`, `DisableEventMusic`, `RemoveEventMusic`,
`IsEventMusicDefined` and `IsEventMusicEnabled` accept
`(UHMUS_KIND_BONUS, eventid, lump)` just like the other event music pools.
Registering the same key updates its metadata and weight rather than adding a
duplicate. The server makes one weighted selection and publishes the selected
track and credits through the existing music path. If there is no eligible pool
entry, playback falls back to the single track in `DefineBonusEvent` for
compatibility with existing addons.

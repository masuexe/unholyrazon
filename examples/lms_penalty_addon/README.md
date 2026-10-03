# LMS penalty addon

Compile `penalty.acs` to `acs/LMSPENEX.o` with the project's UHADD include
paths, pack it with `LOADACS`, and load the addon after Unholy Razon.
The example is force-only (weight 0). Resolve its id by the stable stem
`example_penalty`, then use the usual LMS event forcing mechanism.

Register in both server `OPEN` and `OPEN CLIENTSIDE`; the server executes
penalties and clients read their icons. Registration is idempotent.

The event definition owns all three variants:

```acs
DefineLMSEvent(id, stem,
    message, raremessage, penaltymessage,
    icon, rareicon, penaltyicon,
    flags, penaltyflags, weight);
```

`UpdateLMSEvent` takes the same fields without `stem`;
`UpdateLMSEventByStem` takes a stem instead of an id. Existing addon source
must supply the three new penalty fields and be recompiled.

- `AddLMSEventDrop(stem, actor, amount, rare)` adds normal or rare rewards.
- `AddLMSEventPenaltyDrop(stem, actor, amount, target)` adds a penalty grant.
  Target is `UHLMS_PENALTY_SURVIVOR` or `UHLMS_PENALTY_BOSSES`.
- Penalty flag `UHLMS_PENALTY_CLEAR_ITEMS` clears registered held items before
  grants. Flag 0 with no penalty drops means no extra penalty effects.
- `UHLMS_PENALTY_USE_DEFAULT` selects the shared fallback metadata and drops,
  ignoring the event's own penalty fields and rows. Use this flag alone.
- `SetDefaultLMSEventPenalty(message, icon, flags)` configures shared fallback
  metadata; stem `""` addresses its drops in `AddLMSEventPenaltyDrop`.
  Updating metadata retains previously registered drops.
- Rune reversal remains shared round behavior; `UHLMS_FLAG_DUALRUNE` still
  controls whether the boss team receives one or two runes.
- Metadata getters are `UH_GetLMSEventPenaltyMessage`,
  `UH_GetLMSEventPenaltyIcon`, and `UH_GetLMSEventPenaltyFlags` (event id).

Unknown stems, invalid targets, penalty flags or amounts return `UHLMS_FAIL`
when defining or adding drops; updates use the existing `UHDB_ERR_*` codes.
Default metadata registration returns -1 on success; it is not a failure.

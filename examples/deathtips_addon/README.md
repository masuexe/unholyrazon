# Death tip example addon

Minimal second PK3 that registers custom death tips through the dynamic tip
registry (`UH_RegisterTip`), matching the recipe at the top of
`src/acs_source/hud/deathtips.acs`. The registry is client-only, so one
`OPEN CLIENTSIDE` script is all an addon needs.

## Pack

From this folder, zip contents (not the parent folder) into e.g.
`out/deathtips_addon.pk3`:

```
LOADACS
acs/uh_extips.o
```

Compile ACS first (needs `deathtips.acs` on the include path — it is `#import`ed):

```powershell
New-Item -ItemType Directory -Force -Path acs | Out-Null
& "D:\AppFiles\ACC\acc.exe" `
  -i "..\..\src\acs_source\hud" `
  -i "D:\AppFiles\ACC" `
  acs_source\uh_extips.acs `
  acs\uh_extips.o
```

Only `src/acs_source/hud` (for `deathtips.acs`) and your ACC directory (for
`zcommon.acs`) are needed: `#import` records the library names `deathtips`,
`uh_log` and `uh_acsutils` in the object's `LOAD` chunk, and the engine loads
those `.o` files from the main mod PK3 by name.

## Load order

1. MM8BDM-v6b
2. Unholy `build.pk3` (main mod — loads `deathtips`)
3. This addon PK3

Addon `LOADACS` only needs `uh_extips`.

## What it registers

| Where | How |
|---|---|
| Where | Rows | Weight |
|---|---|---|
| `UH_POOL_CUSTOM` (shared addon default) | 2, one with a per-tip byline | `UH_TIP_WEIGHT_DEFAULT` |
| Built-in `UH_POOL_TIPS` (Demoneye quote byline) | 1 sharing the pool byline | `UH_TIP_WEIGHT_DEFAULT` |
| Own pool 30 | 3, under the pool byline | `UH_TIP_WEIGHT_DEFAULT` |
| Own pool 30 | 1 deliberately rare one | `4` |

Selection is weighted: each row is drawn with probability
`weight / total_weight`, so pools only decide bylines. Weight `0` parks a row
(registered, never drawn). Weights are relative — the registry halves all of
them if an insert would push the total past `UH_TIP_WEIGHT_TOTAL_MAX`, which
preserves ratios.

## Test

1. Main mod only: death tips behave as before (this addon changes no built-in
   tip, byline or wrap width).
2. Main + this addon, die repeatedly: all seven addon tips appear in the
   rotation, the `UH_POOL_TIPS` / `UH_POOL_CUSTOM` ones under their pool
   bylines, the pool-30 ones under "Example Tip (R)", and the weight-4 one
   about 16x less often than the others.
3. Force a specific row: set `_UH_DebugTip_Menu` to an entry index (see the
   `uh_TipDBDump` output) and `puke UH_ShowDeathTip_Menu`.
4. `puke uh_TipDBDump` logs the local registry (total rows, total weight,
   per-pool sizes) — use it to confirm the addon rows landed.
4. Online: host and joiners load main + this addon; joiners must also see the
   addon tips (the `OPEN CLIENTSIDE` twin fills each client's registry, and
   the server only ever forwards one roll that the client scales).

## Rules

- Do NOT `UHInPlay()`-guard the registration script: registration is pure
  data and `SpawnForced` can fail on pure clients.
- Only the `OPEN CLIENTSIDE` twin is needed. The server-side `DEATH` script
  never reads the registry, so a dedicated server (which has no client side)
  works unchanged.
- `UH_RegisterTip` returns the entry index, or `UH_TIP_FAIL` (-1) for an empty
  text, an out-of-range pool id, or a full registry (1024 rows).
- Pick your own pool id in 25..63 and set its byline with
  `UH_SetTipPoolLabel(pool, label)`.
- Rarity is data: the Celebi secret is a virtual entry with
  `UH_TIP_SECRET_WEIGHT`, the "Error 404" joke row uses `UH_TIP_WEIGHT_404`,
  and every `UH_RegisterTip` call takes its own weight. Tuning an easter egg
  is a one-constant edit, not a code change.

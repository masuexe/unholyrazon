# Boss Combo API

The Boss Combo registry stores each event's lineup, player limit, selection weight, mode, flags, and music. Registering a combo does not spawn bosses immediately. Each round, `unholy` selects a combo, assigns players, morphs them, and runs the event. The server owns the registry, and definitions are registered again on every map load.

The public API lives in [`uhcombo_api.acs`](../src/acs_source/_includes/mod_api/uhcombo_api.acs), included by `uhadd.acs`. Constants live in [`uhcombo_defs.acs`](../src/acs_source/_includes/mod_api/uhcombo_defs.acs). Built-in definitions live in [`uh_combo_definitions.acs`](../src/acs_source/unholy/uh_combo_definitions.acs).

## Registering a combo

Addons use `DefineBossCombo`, `SetBossComboMember`, `SetBossComboMusic`, and `CommitBossCombo`. Register definitions from one server-side `OPEN` script without `Delay`. No `OPEN CLIENTSIDE` counterpart is needed.

This example uses existing bosses to register a fixed cooperative lineup of two bosses. Compile this library, place its bytecode in the addon's `acs/` directory, and add `mycombos` to the addon's `LOADACS`. Unholy Razon must also be loaded.

```c
#library "mycombos"
#include "zcommon.acs"
#import "uh_log.acs"
#include "uhadd.acs"

script "my_register_combos" OPEN {
  int combo = DefineBossCombo(-1, "my_addon_duo", "My Duo",
    2, 4, 10, BOSSCOMBO_MODE_FIXED, 0);
  if (combo == UH_COMBO_FAIL) terminate;

  bool ok = SetBossComboMember(combo, 0, "Speciman");
  ok = SetBossComboMember(combo, 1, "RedSpeciman") & ok;
  ok = SetBossComboMusic(combo, "", "", "", "") & ok;
  if (!ok) terminate;
  if (!CommitBossCombo(combo)) terminate;
}
```

`& ok` accumulates the results of all preceding operations. With `&`, the new registration call still executes even if `ok` is already false. Commit only after all calls succeed to keep incomplete lineups out of selection.

Before commit, a record is a draft and cannot participate in random or forced events. Commit checks the combo's structure without requiring each member's `DefineBoss` call to have run, so registration order across libraries' `OPEN` scripts does not prevent commit. Dependencies are checked again during selection. An unresolved boss member excludes only that combo.

## Definition parameters

```c
function int DefineBossCombo(
  int id,
  str key,
  str name,
  int count,
  int minPlayers,
  int weight,
  int mode,
  int flags)
```

| Parameter | Meaning |
|---|---|
| `id` | Public event ID. Pass `-1` to allocate an addon ID starting at `10000`, or use an explicitly coordinated nonnegative ID. |
| `key` | Unique, nonempty stable identifier, such as `my_addon_duo`. Comparisons are case-insensitive. |
| `name` | Nonempty display name. |
| `count` | Number of bosses in the lineup, from `1` to `5`. |
| `minPlayers` | Minimum player count; must be at least `count + 2`. |
| `weight` | Random selection weight, from `0` to `1000000`. `0` makes the combo available only through forced selection. |
| `mode` | How the lineup is generated; see below. |
| `flags` | Event flags. Use `0` for an ordinary cooperative lineup. |

Returns the public ID on success or `UH_COMBO_FAIL` (`-1`) on failure. The registry holds 256 records, including built-in combos and drafts. Each record supports up to 32 candidate members.

Repeated registration of the same key with identical metadata is safe. Conflicting IDs, keys, or metadata fail. After commit, members, music, and metadata are immutable, although writing identical values again can succeed. There is currently no deletion API.

## Modes and member order

| Mode | Member configuration and behavior |
|---|---|
| `BOSSCOMBO_MODE_FIXED` | Fills the lineup by member index. Provide at least `count` members; the first `count` are used. |
| `BOSSCOMBO_MODE_POOL` | Treats all members as a candidate pool and selects `count` bosses. The pool may have more or fewer candidates than the lineup has slots. |
| `BOSSCOMBO_MODE_FORCED` | Takes two duel bosses from `uh_sv_forcedboss1/2`. |
| `BOSSCOMBO_MODE_RANDOM_PAIR` | Selects two distinct bosses from the eligible duel list. |
| `BOSSCOMBO_MODE_SHADOW_PAIR` | Runs a two-boss Shadow duel: bosses appear under fake identities, then reveal their real identities. |
| `BOSSCOMBO_MODE_ZANKOKUNA_PAIR` | Uses the special Zankokuna/Demoneye duel policy. |

The last four dynamic modes require `count=2`, the versus flag, and **no registered members**. Use the corresponding combined flags below for special modes.

```c
function bool SetBossComboMember(int id, int slot, str actor)
```

Members use boss actor names, not display names or numeric boss IDs. Indices start at `0` and must be appended consecutively without gaps. Existing indices in a draft can be replaced. Registration preserves member order and duplicates. Each actor is eventually resolved through the local boss definition table to a boss ID.

Fixed cooperative lineups fill slots in registration order. All two-boss versus lineups have a 50% chance to swap the bosses after the lineup is applied. Registering `0=a, 1=b` therefore produces:

- 50%: `a vs b`.
- 50%: `b vs a`.

Names, portraits, and player assignments follow the swapped slots. A two-boss versus lineup must contain distinct bosses. The swap does not change the registry's member order; queries still return the original registration order.

Pool mode prefers the member with the lowest sum of historical appearances and selections already made this round. Ties are resolved randomly. Each selection increases that member's round count. **Duplicates are allowed; selection is not without replacement.** For example, selecting five bosses from eight candidates with equal histories produces five distinct members. Uneven histories can result in repeated selections of a less frequently used member.

## Event flags

| Constant | Meaning |
|---|---|
| `BOSSCOMBO_FLAG_VERSUS` | Boss-versus-boss duel. |
| `BOSSCOMBO_FLAG_SHADOW` | Shadow identity-reveal sequence. |
| `BOSSCOMBO_FLAG_ZANKOKUNA` | Special Zankokuna policy. |
| `BOSSCOMBO_FLAG_HIGLUR` | Special continuation when both Higlur duel slots die normally. |
| `BOSSCOMBO_FLAGS_SHADOW` | `VERSUS \| SHADOW` |
| `BOSSCOMBO_FLAGS_ZANKOKUNA` | `VERSUS \| ZANKOKUNA` |
| `BOSSCOMBO_FLAGS_HIGLUR` | `VERSUS \| HIGLUR` |

Ordinary fixed duels use `BOSSCOMBO_MODE_FIXED` with `BOSSCOMBO_FLAG_VERSUS`. Dynamic ordinary duels and Shadow candidates are restricted by `BossVersusEligible`. Zankokuna uses a separate eligible list and restrictions on the primary boss. Registering a fixed lineup does not automatically make a new actor compatible with duels. Authors must verify that its damage, watchers, and result handling support versus play.

## Music

```c
function bool SetBossComboMusic(int id, str music, str title, str album, str artist)
```

The four strings are the music resource, track title, album, and artist. Resources support the track/subsong strings used by the existing music system, such as `"M_UB042 5"`.

When `music` is nonempty, combo music takes priority over members' spawn music. Four empty strings mean there is no combo-specific track. At initial spawn, the game randomly selects one actual lineup slot and uses that boss's personal spawn music. A repeated member occupying more slots has a greater chance of supplying the music. Music defaults to empty when omitted, so a setter call is optional for this fallback.

An empty string does not mean silence. Music and credit strings retain their supplied values; repeated metadata registration requires identical contents.

## Selection weights and forced events

Weights are compared only among combos that currently qualify: committed, structurally valid, with all members registered, meeting the minimum player count, and having a `count` matching the boss count already rolled for the round.

For example, if the only two qualifying five-boss combos both have weight `10`, each has a 50% chance within that candidate set. Neither has a 10% chance per round. A combo event must also pass the existing event pity roll.

Automatic boss counts depend on player thresholds: 8/12/16/20 players unlock a maximum of 2/3/4/5 bosses respectively. A five-boss combo with `minPlayers=7` therefore cannot appear through ordinary automatic selection with seven players.

Set `uh_sv_bosseventnum` to a public ID to bypass the event pity roll and selection weight. Player count, boss capacity, structure, and dependency checks still apply. Combos with `weight=0` can also be forced this way.

## Shadow Duel behavior

The built-in `shadow_tricks_duel` (217) allows everyone to move and attack after the initial morph, and displays the fake identities' VS names, boss portraits, and health. Surviving human fake bosses enter the reveal phase after approximately ten seconds, then remorph after approximately five more seconds. The VS introduction and HUD then update to the real identities.

Without `uh_sv_forcedshadowboss1/2` overrides, real identities follow ordinary Shadow selection: first retain an explicit 5% no-change chance; otherwise use the same Ultra/Special/EX/Rare/Common rarity roll, then select according to historical appearances and round counts. Rarity checks use sequential conditional probabilities; the individual `RandomPercent` values must not be added together. The duel uses only eligible bosses and keeps both targets distinct. If the rolled rarity has no suitable member, selection falls back to Common, then to the eligible duel candidate set if needed. These filters mean the resulting rarity distribution can differ from ordinary Shadow.

A fake boss that dies before the reveal has its slot's transformation cancelled. Survival is checked again immediately before remorphing. The existing protection that skips Shadow transformations for bots remains in place. Presentation and combat can start early, while the result manager starts after the reveal sequence to avoid treating a temporary unmorph as a duel failure.

## Query API

Like registration, queries should run on the server. Member and music strings are read through synchronous API mailboxes. Do not send ACS string indices directly to remote clients.

| Interface | Return value |
|---|---|
| `FindBossComboByKey(key)` | Public ID, or `UH_COMBO_FAIL` if not found. |
| `GetBossComboCount()` | Number of allocated records, including drafts. |
| `GetBossComboIdAt(row)` | Public ID at an enumeration index, or `UH_COMBO_FAIL` for an invalid index. |
| `IsBossComboDefined(id)` | Whether the record is committed. Does not guarantee registered boss dependencies or current selection eligibility. |
| `GetBossComboInt(id, field)` | Integer field, or `UH_COMBO_FAIL` for invalid arguments. |
| `GetBossComboString(id, field)` | String field, or `""` for invalid arguments. |
| `GetBossComboMember(id, slot)` | Member actor name in original registration order, or `""` for invalid arguments. |

Integer fields: `UHC_INT_ID`, `COUNT`, `MINPLAYERS`, `WEIGHT`, `MODE`, `FLAGS`, `MEMBERS`, and `COMMITTED`; every field uses the `UHC_INT_` prefix.

String fields: `UHC_STR_KEY`, `NAME`, `MUSIC`, `TITLE`, `ALBUM`, and `ARTIST`; every field uses the `UHC_STR_` prefix.

`row` is an internal enumeration index assigned in registration order. Other public interfaces accept public IDs. Automatically allocated addon IDs also depend on the current registration state: obtain them again on each map and use stable keys to identify records across processes. Do not use internal rows, ACS string indices, or automatically allocated IDs as network identities.

## Internal API and compilation

Inside `unholy`, definitions directly use `UH_ComboDefine`, `UH_ComboSetMember`, `UH_ComboSetMusic`, and `UH_ComboCommit`. `UH_DefineBuiltinCombo` and `UH_CommitBuiltinCombo` are logging wrappers for built-in definitions that report construction or commit failures. They are not public addon interfaces.

Recompile `unholy` after changing built-in data. Changes to database storage or the internal API also require recompiling `UHCOMBDB`, `uhaddr`, and `rz_debug`. Changes to the public UHADD wrappers require recompiling definition libraries and addons that include `uhadd.acs`. `UHCOMBDB` is an import-only library: it must ship in the PK3 but is not added to the main mod's `LOADACS`.

See [`tools/README.md`](../tools/README.md) for compiler paths and packaging instructions. `python3 tools/check_batch_d.py --source-only` checks registration and event structure. Its frozen baseline comparison preserves migration evidence. Document subsequent intentional changes separately; do not rewrite the baseline to conceal differences.

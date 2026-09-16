#!/bin/bash
# Full ACS compile check for the project. Libraries are compiled in the same
# order as LOADACS with the documented include search order: modified v6b
# shared includes first, then the UH-owned mod_api include dir, then the UH
# _imports library sources (uh_acsutils, uh_log, uhdt, uhedenisaac) and the
# v6b override imports (8bdt compiled as CORE8BDT.o).
# Output objects are named after the SOURCE lump (not the internal #library
# name): the base game LOADACS lists lump names such as COLOTRNS, and a
# differently named .o would not shadow the base lump. CORE8BDT.o and
# DTADDR.o must keep those names so they replace v6b's Assist Item table.
# UIXITEMS.o must keep that name so it can replace 8bdm-uix-v3bh when this
# pk3 loads after UIX.
# Usage: compile-acs.sh [outdir]   (default: src/acs)
set -u
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$script_dir/.." || exit 1
if [[ -z "${ACC:-}" ]]; then
  ACC="$(command -v acc || true)"
fi
if [[ -z "$ACC" ]]; then
  echo "acc not found on PATH; set ACC to your Zandronum ACC binary" >&2
  exit 1
fi
OUT="${1:-src/acs}"
mkdir -p "$OUT"
INC="-i src/acs_source/v6b_overrides/_includes/common -i src/acs_source/v6b_overrides/_includes/mod_api -i src/acs_source/_includes/mod_api -i src/acs_source/_imports -i src/acs_source/v6b_overrides/_imports -i src/acs_source/unholy"
fail=0
echo "== uh_bars =="
"$ACC" $INC "src/acs_source/hud/uh_bars.acs" "$OUT/uh_bars.o" || fail=1
echo "== uh_colors =="
"$ACC" $INC "src/acs_source/uh_colors.acs" "$OUT/uh_colors.o" || fail=1
echo "== uh_aprop =="
"$ACC" $INC "src/acs_source/systems/player_properties/uh_aprop.acs" "$OUT/uh_aprop.o" || fail=1
echo "== rz_countinv =="
"$ACC" $INC "src/acs_source/systems/tools/rz_countinv.acs" "$OUT/rz_countinv.o" || fail=1
echo "== uh_acsutils =="
"$ACC" $INC "src/acs_source/_imports/uh_acsutils.acs" "$OUT/uh_acsutils.o" || fail=1
echo "== uh_log =="
"$ACC" $INC "src/acs_source/_imports/uh_log.acs" "$OUT/uh_log.o" || fail=1
echo "== uhdt =="
"$ACC" $INC "src/acs_source/_imports/uhdt.acs" "$OUT/uhdt.o" || fail=1
echo "== uhedenisaac =="
"$ACC" $INC "src/acs_source/_imports/uhedenisaac.acs" "$OUT/uhedenisaac.o" || fail=1
echo "== uhaddr =="
"$ACC" $INC "src/acs_source/corescripts/api_handlers/uhaddr.acs" "$OUT/uhaddr.o" || fail=1
echo "== uh_bossdefs =="
"$ACC" $INC "src/acs_source/classes/bosses/uh_bossdefs.acs" "$OUT/uh_bossdefs.o" || fail=1
echo "== uh_survdefs =="
"$ACC" $INC "src/acs_source/classes/survivors/definitions/uh_survdefs.acs" "$OUT/uh_survdefs.o" || fail=1
echo "== uh_eyedefs =="
"$ACC" $INC "src/acs_source/classes/demoneyes/definitions/uh_eyedefs.acs" "$OUT/uh_eyedefs.o" || fail=1
echo "== uh_itemdefs =="
"$ACC" $INC "src/acs_source/items/definitions/uh_itemdefs.acs" "$OUT/uh_itemdefs.o" || fail=1
echo "== uh_copydefs =="
"$ACC" $INC "src/acs_source/classes/shared/copy_weapons/uh_copydefs.acs" "$OUT/uh_copydefs.o" || fail=1
echo "== uh_lmsdefs =="
"$ACC" $INC "src/acs_source/systems/lms/definitions/uh_lmsdefs.acs" "$OUT/uh_lmsdefs.o" || fail=1
echo "== uh_musicdefs =="
"$ACC" $INC "src/acs_source/systems/music/uh_musicdefs.acs" "$OUT/uh_musicdefs.o" || fail=1
echo "== uh_bonusdefs =="
"$ACC" $INC "src/acs_source/systems/bonus_events/definitions/uh_bonusdefs.acs" "$OUT/uh_bonusdefs.o" || fail=1
echo "== uh_shared =="
"$ACC" $INC "src/acs_source/systems/shared/uh_shared.acs" "$OUT/uh_shared.o" || fail=1
echo "== uh_tools =="
"$ACC" $INC "src/acs_source/uh_tools.acs" "$OUT/uh_tools.o" || fail=1
echo "== rz_tools =="
"$ACC" $INC "src/acs_source/systems/tools/rz_tools.acs" "$OUT/rz_tools.o" || fail=1
echo "== rz_redwarrior =="
"$ACC" $INC "src/acs_source/classes/survivors/red_warrior/rz_redwarrior.acs" "$OUT/rz_redwarrior.o" || fail=1
echo "== uh_classes =="
"$ACC" $INC "src/acs_source/classes/uh_classes.acs" "$OUT/uh_classes.o" || fail=1
echo "== uh_copyweps =="
"$ACC" $INC "src/acs_source/classes/shared/copy_weapons/uh_copyweps.acs" "$OUT/uh_copyweps.o" || fail=1
echo "== uh_bosses =="
"$ACC" $INC "src/acs_source/classes/bosses/uh_bosses.acs" "$OUT/uh_bosses.o" || fail=1
echo "== uh_items =="
"$ACC" $INC "src/acs_source/items/uh_items.acs" "$OUT/uh_items.o" || fail=1
echo "== mmsp_script =="
"$ACC" $INC "src/acs_source/coopenemies/mmsp_script.acs" "$OUT/mmsp_script.o" || fail=1
echo "== uh_corereplace =="
"$ACC" $INC "src/acs_source/v6b_overrides/corescripts/utilities/uh_corereplace.acs" "$OUT/uh_corereplace.o" || fail=1
echo "== uh_modcheck =="
"$ACC" $INC "src/acs_source/compat/mods/rockforce/uh_modcheck.acs" "$OUT/uh_modcheck.o" || fail=1
echo "== uh_uix =="
"$ACC" $INC -i src/acs_source/compat/mods/uix "src/acs_source/compat/mods/uix/uh_uix.acs" "$OUT/uh_uix.o" || fail=1
echo "== UIXITEMS =="
"$ACC" $INC -i src/acs_source/compat/mods/uix/_uix_v3bh "src/acs_source/compat/mods/uix/uixitems.acs" "$OUT/UIXITEMS.o" || fail=1
echo "== uh_legacy =="
"$ACC" $INC "src/acs_source/compat/legacy/uh_legacy.acs" "$OUT/uh_legacy.o" || fail=1
echo "== rz_shared =="
"$ACC" $INC "src/acs_source/systems/player_hooks/rz_shared.acs" "$OUT/rz_shared.o" || fail=1
echo "== unholy =="
"$ACC" $INC "src/acs_source/unholy/unholy.acs" "$OUT/unholy.o" || fail=1
echo "== rz_debug =="
"$ACC" $INC "src/acs_source/debug/rz_debug.acs" "$OUT/rz_debug.o" || fail=1
echo "== CORE8BDT =="
"$ACC" $INC "src/acs_source/v6b_overrides/_imports/8bdt.acs" "$OUT/CORE8BDT.o" || fail=1
echo "== DTADDR =="
"$ACC" $INC "src/acs_source/v6b_overrides/corescripts/api_handlers/dtaddr.acs" "$OUT/DTADDR.o" || fail=1
echo "== barclear =="
"$ACC" $INC "src/acs_source/v6b_overrides/corescripts/api_handlers/barclear.acs" "$OUT/barclear.o" || fail=1
echo "== barhndle =="
"$ACC" $INC "src/acs_source/v6b_overrides/corescripts/api_handlers/barhndle.acs" "$OUT/barhndle.o" || fail=1
echo "== colotrans =="
"$ACC" $INC "src/acs_source/v6b_overrides/corescripts/systems/colotrns.acs" "$OUT/colotrns.o" || fail=1
echo "== footchec =="
"$ACC" $INC "src/acs_source/v6b_overrides/corescripts/utilities/footchec.acs" "$OUT/footchec.o" || fail=1
echo "== jumpcanc =="
"$ACC" $INC "src/acs_source/v6b_overrides/corescripts/systems/jumpcanc.acs" "$OUT/jumpcanc.o" || fail=1
echo "== projtran =="
"$ACC" $INC "src/acs_source/v6b_overrides/corescripts/systems/teamcolors/projtran.acs" "$OUT/projtran.o" || fail=1
echo "== teamcol =="
"$ACC" $INC "src/acs_source/v6b_overrides/corescripts/systems/teamcolors/teamcol.acs" "$OUT/teamcol.o" || fail=1
if [ "$fail" -ne 0 ]; then echo "ACS COMPILE FAILED"; else echo "ACS COMPILE OK"; fi
exit $fail

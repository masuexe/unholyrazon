#!/bin/bash
# Full ACS compile check for the project. Libraries are compiled in the same
# order as LOADACS with the documented include search order: modified v6b
# shared includes first, then the UH-owned mod_api include dir, then the UH
# _imports library sources (uh_acsutils, uh_log, uhdt, uhdbcrud, uhedenisaac,
# UHCOMBDB) and the v6b override imports (8BDT compiled as CORE8BDT.o).
# Output objects are named after the SOURCE lump (not the internal #library
# name): the base game LOADACS lists lump names such as COLOTRNS, and a
# differently named .o would not shadow the base lump. CORE8BDT.o and
# DTADDR.o must keep those names so they replace v6b's Assist Item table.
# UIXITEMS.o must keep that name so it can replace 8bdm-uix-v3bh when this
# pk3 loads after UIX.  WHEELDT.o is an import-only library (no LOADACS entry);
# it must ship because the UIX libraries import it. UHCOMBDB.o is likewise
# import-only and must keep that name.
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
# Old manual builds used lowercase shadow filenames. Zandronum compares lump
# paths without case, so keeping both copies breaks online authentication.
for library in UIXITEMS UIXWEAP UIXTEAM PNGBUTTN WEPHIDE; do
  legacy="$OUT/${library,,}.o"
  canonical="$OUT/$library.o"
  if [[ -f "$legacy" ]] && ! [[ "$legacy" -ef "$canonical" ]]; then
    rm -- "$legacy"
  fi
done
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
# Import-only host settings. UHDT reads Bonus Event rules; the round core
# owns Boss override commands. Neither settings library has a LOADACS entry.
"$ACC" $INC "src/acs_source/_imports/uhbeset.acs" "$OUT/UHBESET.o" || fail=1
"$ACC" $INC "src/acs_source/_imports/uhbsset.acs" "$OUT/UHBSSET.o" || fail=1
"$ACC" $INC "src/acs_source/_imports/uhdt.acs" "$OUT/uhdt.o" || fail=1
echo "== uhdbcrud =="
# Import-only CRUD logic. UHADDR imports this lump; it has no LOADACS entry.
"$ACC" $INC "src/acs_source/_imports/uhdbcrud.acs" "$OUT/uhdbcrud.o" || fail=1
echo "== uhedenisaac =="
"$ACC" $INC "src/acs_source/_imports/uhedenisaac.acs" "$OUT/uhedenisaac.o" || fail=1
echo "== UHCOMBDB =="
# Import-only boss-combo registry (unholy, uhaddr and rz_debug import it). Not
# in LOADACS, but the lump must ship and keep the UHCOMBDB name.
"$ACC" $INC "src/acs_source/_imports/uhcombodb.acs" "$OUT/UHCOMBDB.o" || fail=1
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
echo "== uh_rockforce =="
"$ACC" $INC "src/acs_source/compat/mods/rockforce/uh_rockforce.acs" "$OUT/uh_rockforce.o" || fail=1
echo "== uh_uix =="
"$ACC" $INC -i src/acs_source/compat/mods/uix "src/acs_source/compat/mods/uix/uh_uix.acs" "$OUT/uh_uix.o" || fail=1
echo "== uh_uixfw =="
"$ACC" $INC -i src/acs_source/compat/mods/uix -i src/acs_source/compat/mods/uix/_uix_v3bh "src/acs_source/compat/mods/uix/uh_uixfw.acs" "$OUT/uh_uixfw.o" || fail=1
echo "== UHWWV6C =="
"$ACC" $INC -i src/acs_source/compat/mods/uix/_uix_v3bh "src/acs_source/compat/mods/uix/uh_wwv6c.acs" "$OUT/UHWWV6C.o" || fail=1
echo "== WHEELDT =="
# uh_uixfw/uixitems/uixweap #import this shared wheel table, so the lump must
# ship: without it those three libraries fail to load ("Could not find ACS
# library WHEELDT").  Not in LOADACS — imports resolve by lump name.
"$ACC" $INC -i src/acs_source/compat/mods/uix/_uix_v3bh "src/acs_source/compat/mods/uix/_uix_v3bh/WHEELDT.acs" "$OUT/WHEELDT.o" || fail=1
echo "== UIXITEMS =="
"$ACC" $INC -i src/acs_source/compat/mods/uix/_uix_v3bh "src/acs_source/compat/mods/uix/uixitems.acs" "$OUT/UIXITEMS.o" || fail=1
echo "== UIXWEAP =="
"$ACC" $INC -i src/acs_source/compat/mods/uix/_uix_v3bh -i "../references/for_8bdm-v6b/8bdm-uix-v3bh/acs_source/static tables" "src/acs_source/compat/mods/uix/uixweap.acs" "$OUT/UIXWEAP.o" || fail=1
echo "== UIXTEAM =="
# UIXTEAM.o must keep that name so it can replace 8bdm-uix-v3bh when this pk3
# loads after UIX.  Do not add it to LOADACS; UIX already loads UIXTEAM.
"$ACC" $INC -i src/acs_source/compat/mods/uix/_uix_v3bh "src/acs_source/compat/mods/uix/uixteam.acs" "$OUT/UIXTEAM.o" || fail=1
echo "== uh_legacy =="
"$ACC" $INC "src/acs_source/compat/legacy/uh_legacy.acs" "$OUT/uh_legacy.o" || fail=1
echo "== rz_shared =="
"$ACC" $INC "src/acs_source/systems/player_hooks/rz_shared.acs" "$OUT/rz_shared.o" || fail=1
echo "== unholy =="
"$ACC" $INC "src/acs_source/unholy/unholy.acs" "$OUT/unholy.o" || fail=1
echo "== deathtips =="
"$ACC" $INC "src/acs_source/hud/deathtips.acs" "$OUT/deathtips.o" || fail=1
echo "== rz_debug =="
"$ACC" $INC "src/acs_source/debug/rz_debug.acs" "$OUT/rz_debug.o" || fail=1
echo "== CORE8BDT =="
"$ACC" $INC "src/acs_source/v6b_overrides/_imports/8BDT.acs" "$OUT/CORE8BDT.o" || fail=1
echo "== DTADDR =="
"$ACC" $INC "src/acs_source/v6b_overrides/corescripts/api_handlers/DTADDR.acs" "$OUT/DTADDR.o" || fail=1
echo "== BARCLEAR =="
"$ACC" $INC "src/acs_source/v6b_overrides/corescripts/api_handlers/BARCLEAR.acs" "$OUT/BARCLEAR.o" || fail=1
echo "== BARHNDLE =="
"$ACC" $INC "src/acs_source/v6b_overrides/corescripts/api_handlers/BARHNDLE.acs" "$OUT/BARHNDLE.o" || fail=1
echo "== COLOTRNS =="
"$ACC" $INC "src/acs_source/v6b_overrides/corescripts/systems/COLOTRNS.acs" "$OUT/COLOTRNS.o" || fail=1
echo "== FOOTCHEC =="
"$ACC" $INC "src/acs_source/v6b_overrides/corescripts/utilities/FOOTCHEC.acs" "$OUT/FOOTCHEC.o" || fail=1
echo "== COREJUMP =="
# The v6c base LOADACS owns this callback library.
"$ACC" $INC "src/acs_source/v6b_overrides/corescripts/tables/COREJUMP.acs" "$OUT/COREJUMP.o" || fail=1
echo "== JUMPCANC =="
"$ACC" $INC "src/acs_source/v6b_overrides/corescripts/systems/JUMPCANC.acs" "$OUT/JUMPCANC.o" || fail=1
echo "== UITEAMIT =="
"$ACC" $INC "src/acs_source/v6b_overrides/corescripts/systems/ui/UITEAMIT.acs" "$OUT/UITEAMIT.o" || fail=1
echo "== MUGSHOTS =="
"$ACC" $INC "src/acs_source/v6b_overrides/corescripts/systems/MUGSHOTS.acs" "$OUT/MUGSHOTS.o" || fail=1
echo "== PROJTRAN =="
"$ACC" $INC "src/acs_source/v6b_overrides/corescripts/systems/teamcolors/PROJTRAN.acs" "$OUT/PROJTRAN.o" || fail=1
echo "== TEAMCOL =="
"$ACC" $INC "src/acs_source/v6b_overrides/corescripts/systems/teamcolors/TEAMCOL.acs" "$OUT/TEAMCOL.o" || fail=1

# Optional PingButton shadow: addon LOADACS loads PNGBUTTN, not Unholy.
echo "== PNGBUTTN =="
"$ACC" $INC "src/acs_source/compat/mods/pingbutton/PNGBUTTN.acs" "$OUT/PNGBUTTN.o" || fail=1

# Required v6b miscfixes shadow. Its LOADACS entry loads WEPHIDE.
echo "== WEPHIDE =="
"$ACC" $INC "src/acs_source/compat/mods/miscfixes/WEPHIDE.acs" "$OUT/WEPHIDE.o" || fail=1

if [ "$fail" -ne 0 ]; then echo "ACS COMPILE FAILED"; else echo "ACS COMPILE OK"; fi
exit $fail

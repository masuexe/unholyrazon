#!/usr/bin/env python3
"""Fast static/resource acceptance checks for Batch D."""
from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MUSIC = ROOT.parent / "unholyrazon_music" / "razon_soundtest.pk3"
DEF = ROOT / "src/acs_source/unholy/uh_def.acs"
COMBO_DEFS = ROOT / "src/acs_source/_includes/mod_api/uhcombo_defs.acs"
COMBO_DATA = ROOT / "src/acs_source/unholy/uh_combo_definitions.acs"
COMBO_DB = ROOT / "src/acs_source/_imports/uhcombodb.acs"
COMBO_BASELINE = ROOT / "tools/fixtures/boss_combos_v1.json"
FUNCS = ROOT / "src/acs_source/unholy/uh_funclib.acs"
VERSUS = ROOT / "src/acs_source/unholy/uh_versus.acs"
BOSSSELECT = ROOT / "src/acs_source/unholy/uh_bossselect.acs"
DICKHEAD = ROOT / "src/acs_source/unholy/uh_dickhead_revival.acs"
BOSSDEFS = ROOT / "src/acs_source/classes/bosses/boss_definition_table.acs"
FACES = ROOT / "src/patches/faces/bosses"
REQUIRED_MUSIC = {
    "M_EYE13", "M_EYE14", "M_EYE15", "SATANMUS",
    "M_UB029X", "M_UB038", "M_UB048X", "M_UB104X", "M_UB033",
}


def read_acs_with_local_includes(path: Path) -> str:
    """Read an ACS file and expand include files beside it when available."""
    text = path.read_text(encoding="utf-8")

    def expand(match: re.Match[str]) -> str:
        include_path = path.parent / match.group(1)
        if not include_path.is_file():
            return match.group(0)
        return read_acs_with_local_includes(include_path)

    return re.sub(r'#include\s+"([^"]+)"', expand, text)


def function_body(text: str, name: str) -> str:
    match = re.search(rf"function\s+\w+\s+{re.escape(name)}\s*\([^)]*\)\s*\{{", text)
    if not match:
        return ""
    start = match.end()
    depth = 1
    for pos in range(start, len(text)):
        if text[pos] == "{":
            depth += 1
        elif text[pos] == "}":
            depth -= 1
            if depth == 0:
                return text[start:pos]
    return ""


def script_body(text: str, name: str) -> str:
    match = re.search(rf'script\s+"{re.escape(name)}"\s*\([^)]*\)\s*\{{', text)
    if not match:
        return ""
    start = match.end()
    depth = 1
    for pos in range(start, len(text)):
        if text[pos] == "{":
            depth += 1
        elif text[pos] == "}":
            depth -= 1
            if depth == 0:
                return text[start:pos]
    return ""


def braced_block(text: str, open_pos: int) -> str:
    """Return the contents of the brace opened at open_pos, or empty."""
    if open_pos < 0 or open_pos >= len(text) or text[open_pos] != "{":
        return ""
    depth = 1
    for pos in range(open_pos + 1, len(text)):
        if text[pos] == "{":
            depth += 1
        elif text[pos] == "}":
            depth -= 1
            if depth == 0:
                return text[open_pos + 1:pos]
    return ""


def define_int(text: str, name: str) -> int | None:
    match = re.search(rf"#define\s+{re.escape(name)}\s+(-?\d+)\b", text)
    return int(match.group(1)) if match else None


def split_top_level_args(body: str) -> list[str]:
    parts: list[str] = []
    depth = 0
    cur = ""
    in_quote = False
    escaped = False
    for ch in body:
        if in_quote and escaped:
            cur += ch
            escaped = False
        elif in_quote and ch == "\\":
            cur += ch
            escaped = True
        elif ch == '"':
            in_quote = not in_quote
            cur += ch
        elif not in_quote and ch in "([":
            depth += 1
            cur += ch
        elif not in_quote and ch in ")]":
            depth -= 1
            cur += ch
        elif not in_quote and ch == "," and depth == 0:
            parts.append(cur.strip())
            cur = ""
        else:
            cur += ch
    parts.append(cur.strip())
    return parts


def acs_calls(text: str, name: str) -> list[list[str]]:
    """Read literal registration calls, retaining ACS escapes byte-for-byte."""
    return [split_top_level_args(match.group(1)) for match in re.finditer(
        rf"\b{re.escape(name)}\s*\((.*?)\)\s*(?:&\s*ok\s*)?;", text, re.S
    )]


def parse_combo_registrations(
    text: str, defines: dict[str, int], bosses: dict[int, tuple[str, str]],
) -> list[dict]:
    actor_ids = {actor.casefold(): bid for bid, (actor, _) in bosses.items()}
    # Strip comments without treating // inside a quoted ACS string as a comment.
    text = re.sub(r'"(?:\\.|[^"\\])*"|//[^\n]*|/\*.*?\*/',
                  lambda m: m.group(0) if m.group(0).startswith('"') else "", text, flags=re.S)
    starts = list(re.finditer(r"\bcombo\s*=\s*UH_DefineBuiltinCombo\s*\(", text))
    records: list[dict] = []

    def number(token: str) -> int:
        if token.lstrip("-").isdigit():
            return int(token)
        return defines[token]

    def string(token: str) -> str:
        if len(token) < 2 or token[0] != '"' or token[-1] != '"':
            raise ValueError(f"expected a literal ACS string: {token}")
        return token[1:-1]

    for index, start in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
        block = text[start.start():end]
        definitions = acs_calls(block, "UH_DefineBuiltinCombo")
        music = acs_calls(block, "UH_ComboSetMusic")
        if len(definitions) != 1 or len(definitions[0]) != 8 or len(music) != 1 or len(music[0]) != 5:
            raise ValueError("incomplete combo definition/music call")
        args = definitions[0]
        members: list[str] = []
        for member in acs_calls(block, "UH_ComboSetMember"):
            if len(member) != 3 or member[0] != "combo" or number(member[1]) != len(members):
                raise ValueError("member slots must be consecutive and start at zero")
            members.append(string(member[2]))
        if music[0][0] != "combo" or "complete = UH_CommitBuiltinCombo(combo, ok) & complete;" not in block:
            raise ValueError("combo must commit only after every setter succeeded")
        record = dict(id=number(args[0]), key=string(args[1]), name=string(args[2]),
                      count=number(args[3]), min_players=number(args[4]), weight=number(args[5]),
                      mode=number(args[6]), flags=number(args[7]), members=members,
                      member_ids=[actor_ids.get(actor.casefold(), -9999) for actor in members])
        record.update(zip(("music", "title", "album", "artist"), map(string, music[0][1:])))
        records.append(record)
    if not records:
        raise ValueError("no combo registration calls found")
    return records


def parse_define_bosses(text: str) -> dict[int, tuple[str, str]]:
    result: dict[int, tuple[str, str]] = {}
    spawn_music: dict[int, str] = {}
    for args in acs_calls(text, "AddBossMusic"):
        if len(args) >= 2 and args[0].lstrip("-").isdigit():
            spawn_music.setdefault(int(args[0]), args[1].strip('"'))
    for match in re.finditer(r"DefineBoss\((.*?)\);", text, re.S):
        parts = split_top_level_args(match.group(1))
        if len(parts) < 9:
            continue
        try:
            bid = int(parts[0])
        except ValueError:
            continue
        actor = parts[1].strip('"')
        music = spawn_music.get(bid, "")
        result[bid] = (actor, music)
    return result


def collect_face_names() -> set[str]:
    names: set[str] = set()
    if not FACES.is_dir():
        return names
    for path in FACES.iterdir():
        if path.suffix.lower() in {".png", ".bmp", ".pcx"}:
            names.add(path.stem.upper())
    return names


def music_lump(field: str) -> str:
    """DefineBoss / combo music may be "LUMP tracknum"; only the lump matters."""
    parts = field.split()
    return parts[0] if parts else ""


def combo_resource_issues(
    records: list[dict], bosses: dict[int, tuple[str, str]],
    face_names: set[str], music_lumps: set[str],
) -> list[tuple[str, str, int]]:
    """Check registered member actors, face patches and combo/boss music."""
    issues: list[tuple[str, str, int]] = []
    for row in records:
        combo_id = str(row["id"])
        weight = row["weight"]
        ids = row["member_ids"]
        for actor, bid in zip(row["members"], ids):
            if bid not in bosses:
                issues.append((combo_id, f"actor {actor} not registered", weight))
            elif f"UFACE{bid}" not in face_names:
                issues.append((combo_id, f"boss {bid} missing face UFACE{bid}", weight))
        combo_track = row["music"]
        if combo_track:
            if music_lump(combo_track).upper() not in music_lumps:
                issues.append((combo_id, f"combo music {combo_track} missing", weight))
        else:
            boss_tracks = [music_lump(bosses.get(bid, ("", ""))[1]) for bid in ids]
            if not any(track and track.upper() in music_lumps for track in boss_tracks):
                issues.append((combo_id, "no boss music present", weight))
    return issues


def combo_shape_error(row: dict, defines: dict[str, int], max_bosses: int,
                      member_capacity: int) -> str | None:
    """Validate registration payloads using the UHCOMBDB shape contract."""
    count = row["count"]
    mode = row["mode"]
    members = len(row["members"])
    flags = row["flags"]
    if count < 1 or count > max_bosses:
        return "count"
    versus = bool(flags & defines["BOSSCOMBO_FLAG_VERSUS"])
    known_modes = {defines[name] for name in (
        "BOSSCOMBO_MODE_FIXED", "BOSSCOMBO_MODE_POOL", "BOSSCOMBO_MODE_FORCED",
        "BOSSCOMBO_MODE_RANDOM_PAIR", "BOSSCOMBO_MODE_SHADOW_PAIR", "BOSSCOMBO_MODE_ZANKOKUNA_PAIR",
    )}
    if mode not in known_modes:
        return "mode"
    if mode >= defines["BOSSCOMBO_MODE_FORCED"]:
        if not versus or count != 2 or members != 0:
            return "dynamic"
        return None
    if members < 1 or members > member_capacity:
        return "members"
    if mode == defines["BOSSCOMBO_MODE_FIXED"] and members < count:
        return "fixedmembers"
    if versus and (count != 2 or mode != defines["BOSSCOMBO_MODE_FIXED"] or members != 2):
        return "versus"
    return None


def versus_death_gate_contract(text: str) -> bool:
    """Require the Higlur terminal path to distinguish death from forfeits."""
    normal = function_body(text, "UHVS_IsNormalDeathState")
    both = function_body(text, "UHVS_BothSlotsDiedNormally")
    watch = script_body(text, "ub_ManageBossVsBossEvent")
    higlur_gate = bool(
        re.search(
            r"result\s*==\s*UHVS_DRAW\s*&&\s*bothnormaldeath\s*&&\s*"
            r"BossComboHasFlag\(BOSSCOMBO_FLAG_HIGLUR\)",
            watch,
            re.S,
        )
    )
    return (
        "deathstate == 5" in normal
        and "deathstate == 6" in normal
        and both.count("UHVS_IsNormalDeathState(") >= 2
        and "BOSSHP_DEATH" in both
        and "bool bothnormaldeath = UHVS_BothSlotsDiedNormally();" in watch
        and "reason = bothnormaldeath ? UHVS_REASON_DEATH : UHVS_REASON_FORFEIT;" in watch
        and higlur_gate
    )


def shadow_target_order_contract(text: str) -> bool:
    """Require Shadow targets to be local until pair validation completes."""
    body = script_body(text, "ub_ShadowBossManager")
    special_start = body.find("if (shadowversus) {")
    special_open = body.find("{", special_start)
    special = braced_block(body, special_open)
    duplicate = body.find("if (shadowtarget0 == shadowtarget1)", special_open)
    write0 = body.find("bossdataarr[0][BOSSDATA_MORPHED] = shadowtarget0;", duplicate)
    write1 = body.find("bossdataarr[1][BOSSDATA_MORPHED] = shadowtarget1;", duplicate)
    return (
        "int shadowtarget0 = bossdataarr[0][BOSSDATA_NUM];" in body
        and "int shadowtarget1 = bossdataarr[1][BOSSDATA_NUM];" in body
        and "if (i == 0) {shadowtarget0 = tempboss;}" in special
        and "else {shadowtarget1 = tempboss;}" in special
        and "bossdataarr[i][BOSSDATA_MORPHED] = tempboss;" not in special
        and duplicate > special_open
        and write0 > duplicate
        and write1 > duplicate
        and "Boss combo 217 rejected after shadow fallback" in body
        and "activebosscombo = -1;" in body
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--music-pk3", type=Path, default=DEFAULT_MUSIC)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--source-only", action="store_true",
                        help="validate source contracts and the frozen combo baseline without external music archives")
    args = parser.parse_args()

    checks: list[dict[str, str]] = []

    def check(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "status": "pass" if passed else "fail", "detail": detail})

    try:
        defs = DEF.read_text(encoding="utf-8") + "\n" + COMBO_DEFS.read_text(encoding="utf-8")
        combo_data = COMBO_DATA.read_text(encoding="utf-8")
        combo_db = COMBO_DB.read_text(encoding="utf-8")
        bosses = parse_define_bosses(BOSSDEFS.read_text(encoding="utf-8"))
        defines = {name: int(value) for name, value in re.findall(r"#define\s+(\w+)\s+(-?\d+)\b", defs)}
        rows = parse_combo_registrations(combo_data, defines, bosses)
        baseline = json.loads(COMBO_BASELINE.read_text(encoding="utf-8"))["combos"]
        # Keep the frozen migration evidence. Pin subsequent music edits by
        # field rather than accepting arbitrary differences in these records.
        music_overrides = {
            303: {"title": "Guts Man Power Battle!"},
            307: {"music": "", "title": "", "album": "", "artist": ""},
            501: {"music": "", "title": "", "album": "", "artist": ""},
            502: {"music": "", "title": "", "album": "", "artist": ""},
            210: {"title": "Iquickman Stage"},
            211: {"music": "M_UB060", "title": "No More Nuzzles",
                  "album": "Undertale: Halloween Hack", "artist": "Nobuo Uematsu"},
            213: {"music": "M_UB060", "title": "No More Nuzzles",
                  "album": "Undertale: Halloween Hack"},
            214: {"music": "M_UB060", "title": "No More Nuzzles",
                  "album": "Undertale: Halloween Hack", "artist": "Nobuo Uematsu"},
        }
        expected_combos = [dict(row) for row in baseline]
        for row in expected_combos:
            row.update(music_overrides.get(row["id"], {}))
            if row["id"] == 501:
                row["members"] = row["members"] + ["FinalSpeciman", "SpecimanDX"]
                row["member_ids"] = row["member_ids"] + [404, 542]
        funcs = read_acs_with_local_includes(FUNCS)
        versus = VERSUS.read_text(encoding="utf-8")
        bossselect = BOSSSELECT.read_text(encoding="utf-8")
        dickhead = DICKHEAD.read_text(encoding="utf-8")
    except (OSError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    check("five-boss constant", bool(re.search(r"#define\s+MAX_BOSSES\s+5\b", defs)), "MAX_BOSSES must be 5")

    validator = function_body(funcs, "DebugValidateRoundStart")
    combo_validation = "UH_ComboCount()" in validator and (
        "BossComboFullyRegistered" in validator
        or ("UH_ComboMemberId" in validator and "IsBossDefined" in validator)
    )
    check(
        "round-start combo registration validation",
        combo_validation,
        "DebugValidateRoundStart must validate every combo boss through the helper or an equivalent explicit loop",
    )

    initial_schema = all(token in combo_db for token in (
        "uh_combo_int[UH_COMBO_CAPACITY][UHC_INT_FIELDS]",
        "uh_combo_str[UH_COMBO_CAPACITY][UHC_STR_FIELDS]",
        "uh_combo_members[UH_COMBO_CAPACITY][UH_COMBO_MEMBER_CAPACITY]",
    )) and "UH_ComboAvailable" in function_body(combo_db, "UH_ComboFullyRegistered")
    check("dynamic combo registry", initial_schema,
          "capacity, metadata, ordered members and committed availability are separate")
    check("combo migration preserves frozen data", rows == expected_combos,
          "26 rows match the frozen baseline with explicit music metadata and Speciman Final/DX changes")
    check("combo stable ids and keys", all(row["id"] >= 0 for row in rows)
          and len({row["id"] for row in rows}) == len(rows)
          and len({row["key"].casefold() for row in rows}) == len(rows),
          "registered ids and case-insensitive keys are unique")
    ready_body = function_body(funcs, "BossComboRegistryReady")
    check("combo readiness independent of missing addons",
          "uh_combo_builtins_ready" in ready_body and "FullyRegistered" not in ready_body,
          "registration readiness does not wait for every addon member")
    api = (ROOT / "src/acs_source/_includes/mod_api/uhcombo_api.acs").read_text(encoding="utf-8")
    handlers = (ROOT / "src/acs_source/corescripts/api_handlers/uhaddr.acs").read_text(encoding="utf-8")
    cvars = (ROOT / "src/CVARINFO.ipc").read_text(encoding="utf-8")
    staged = set(re.findall(r'(?:Set|Get)CVar(?:String)?\("(uh_bc_[^"\n]+)"', api + handlers))
    registered = set(re.findall(r'local\s+noarchive\s+(?:int|string)\s+(uh_bc_\w+);', cvars))
    check("combo IPC mailboxes registered", bool(staged) and staged <= registered,
          "all UHADD/handler combo cvars are declared local noarchive")

    versus_define = bool(re.search(r"#define\s+BOSSCOMBO_FLAG_VERSUS\s+1\b", defs))
    check(
        "versus combo flag",
        versus_define,
        "BOSSCOMBO_FLAG_VERSUS must exist",
    )

    versus_row = any(row["id"] == 207 and row["count"] == 2 and row["min_players"] == 4
                     and row["weight"] == 0 and row["flags"] == defines["BOSSCOMBO_FLAGS_HIGLUR"] for row in rows)
    check(
        "forced versus combo 207",
        versus_row,
        "combo 207 must be force-only (weight 0) and flagged versus",
    )

    # Shape regression: the ACS BossComboShapeError rules are mirrored here so
    # malformed registration payloads are rejected before entering the pool.
    define_names = [
        "BOSSCOMBO_MODE_FIXED",
        "BOSSCOMBO_MODE_POOL",
        "BOSSCOMBO_MODE_FORCED",
        "BOSSCOMBO_MODE_RANDOM_PAIR",
        "BOSSCOMBO_MODE_SHADOW_PAIR",
        "BOSSCOMBO_MODE_ZANKOKUNA_PAIR",
        "BOSSCOMBO_FLAG_VERSUS",
        "BOSSCOMBO_FLAG_SHADOW",
        "BOSSCOMBO_FLAG_ZANKOKUNA",
        "BOSSCOMBO_FLAG_HIGLUR",
        "BOSSCOMBO_FLAGS_SHADOW",
        "BOSSCOMBO_FLAGS_ZANKOKUNA",
        "BOSSCOMBO_FLAGS_HIGLUR",
    ]
    defines = {name: define_int(defs, name) for name in define_names}
    max_bosses = define_int(defs, "MAX_BOSSES")
    member_capacity = define_int(defs, "UH_COMBO_MEMBER_CAPACITY")
    shape_ready = (
        all(value is not None for value in defines.values())
        and max_bosses is not None
        and member_capacity is not None
        and max_bosses == define_int(defs, "UH_COMBO_MAX_BOSSES")
    )
    shape_helper = all(
        name in funcs
        for name in ("BossComboShapeError", "BossComboShapeValid", "BossComboShapeErrorText")
    )
    shape_wired = shape_helper and all(
        "BossComboShape" in function_body(funcs, name)
        for name in ("PickBossCombo", "ApplyBossCombo", "TryBossComboRoll", "DebugValidateRoundStart")
    )
    check(
        "combo shape helper wired into selection",
        shape_ready and shape_wired,
        "BossComboShapeError must exist and gate PickBossCombo/ApplyBossCombo/TryBossComboRoll/DebugValidateRoundStart",
    )

    valid_rows = rows is not None and all(
        combo_shape_error(row, defines, max_bosses, member_capacity) is None for row in rows
    )
    check(
        "combo table shape valid",
        valid_rows,
        f"{len(rows)} rows parsed" if rows is not None else "could not parse combo registrations",
    )

    versus_malformed: list[str] = []
    if valid_rows:
        base = next((row for row in rows if row["id"] == 207), None)
        if base is None:
            versus_malformed.append("missing-207-row")
        else:
            cases = {
                "three-bosses": {"count": 3},
                "pool-mode": {"mode": defines["BOSSCOMBO_MODE_POOL"]},
                "members-not-two": {"members": ["one"]},
                "too-many-members": {"members": ["one"] * (member_capacity + 1)},
            }
            for label, edits in cases.items():
                mutated = dict(base)
                for idx, replacement in edits.items():
                    mutated[idx] = replacement
                if combo_shape_error(mutated, defines, max_bosses, member_capacity) is None:
                    versus_malformed.append(label)
        dynamic = next((row for row in rows if row["id"] == 206), None)
        if dynamic is None:
            versus_malformed.append("missing-206-row")
        else:
            dynamic_cases = {
                "dynamic-no-versus": {"flags": 0},
                "dynamic-nonzero-members": {"members": ["one"]},
                "dynamic-unknown-mode": {"mode": 99},
            }
            for label, edits in dynamic_cases.items():
                mutated = dict(dynamic)
                for idx, replacement in edits.items():
                    mutated[idx] = replacement
                if combo_shape_error(mutated, defines, max_bosses, member_capacity) is None:
                    versus_malformed.append(label)
    check(
        "malformed versus rows rejected",
        valid_rows and not versus_malformed,
        "all malformed versus/dynamic rows rejected" if not versus_malformed else "not rejected: " + ", ".join(versus_malformed),
    )

    # V2 contract: the versus watcher owns the ending, blocks cross-slot boss
    # revival, resolves morph failure itself, and leaves survivor stats alone.
    claim = function_body(versus, "UHVS_ClaimGameover")
    resolve = function_body(versus, "UHVS_Resolve")
    watch = script_body(versus, "ub_ManageBossVsBossEvent")
    check(
        "versus atomic result claim",
        "gameover" in claim and "UHVS_ClaimGameover" in resolve and "UHVS_StopConflictingScripts" in resolve,
        "UHVS_Resolve must atomically claim gameover and stop conflicting scripts",
    )
    check(
        "versus stops conflicting round enders",
        all(
            name in versus
            for name in ("ub_WatchSurvivors", "ub_WatchBossesAndEyes", "rz_WatchTwoPlayerLeft", "uh_BackgroundTimer", "rz_DickheadRevival")
        ),
        "UHVS_StopConflictingScripts must terminate the other round-ending/revival scripts",
    )
    check(
        "versus blocks cross-slot boss revival",
        "versusblockrevive = true" in watch
        and "versusblockrevive = false" in bossselect
        and dickhead.count("versusblockrevive") >= 2,
        "versusblockrevive must be set in the watcher, cleared per round, and checked by both Dickhead revival paths",
    )
    morph_guard = script_body(bossselect, "ub_MorphFailureFallback")
    check(
        "versus resolves morph failure itself",
        "versusfightevent" in morph_guard and "terminate" in morph_guard and "BOSSDATA_MORPHED" in watch,
        "ub_MorphFailureFallback must defer to the versus watcher, which checks BOSSDATA_MORPHED",
    )
    check(
        "versus leaves survivor stats alone",
        not any(f"{token} =" in resolve for token in ("winstreak", "mercygiven", "hellmarkfrags", "survwinwithlms")),
        "UHVS_Resolve must not write survivor winstreak / mercy / hellmark",
    )

    # V4 contract: dynamic duels use an explicit reviewed allowlist, validate
    # distinct pairs before touching state, and retain same-boss name handling.
    eligible = function_body(funcs, "BossVersusEligible")
    random_pick = function_body(funcs, "PickRandomVersusBoss")
    apply = function_body(funcs, "ApplyBossCombo")
    eligible_case_ids = {
        int(value) for value in re.findall(r"\bcase\s+(-?\d+)\s*:", eligible)
    }
    try:
        registered_reject_probe = bool(
            re.search(r"DefineBoss\(\s*400\s*,", BOSSDEFS.read_text(encoding="utf-8"), re.S)
        )
    except OSError:
        registered_reject_probe = False
    check(
        "versus explicit eligibility allowlist",
        bool(eligible)
        and "IsBossDefined" in eligible
        and eligible.rstrip().endswith("return false;")
        and 33 in eligible_case_ids
        and registered_reject_probe
        and 400 not in eligible_case_ids
        and -1 not in eligible_case_ids
        and "BossVersusUnsafe" not in funcs
        and "BossVersusEligible" in random_pick
        and "BossVersusEligible" in apply,
        "BossVersusEligible must default-reject a registered unapproved id and custom ids",
    )
    check(
        "dynamic duel modes present",
        "BOSSCOMBO_MODE_FORCED" in defs
        and "BOSSCOMBO_MODE_RANDOM_PAIR" in defs
        and any(row["id"] == 206 and row["weight"] == 0 and row["mode"] == defines["BOSSCOMBO_MODE_FORCED"] for row in rows)
        and any(row["id"] == 209 and row["weight"] == 0 and row["mode"] == defines["BOSSCOMBO_MODE_RANDOM_PAIR"] for row in rows),
        "206 (FORCED) and 209 (RANDOM_PAIR) must exist as force-only versus rows",
    )
    check(
        "random pair avoids first boss",
        bool(re.search(r"PickRandomVersusBoss\s*\(\s*dyn0\s*\)", apply))
        and "dyn0 == dyn1" in apply,
        "209 must pass dyn0 to its second sample and reject duplicate resolved ids",
    )
    check(
        "same-boss disambiguation retained",
        "sameboss" in versus and "UHVS_DisplayName" in versus,
        "same-boss duels must append the player number to the HUD/winner name",
    )

    special_modes = {
        "shadow": any(row["id"] == 217 and row["weight"] == 0 and row["mode"] == defines["BOSSCOMBO_MODE_SHADOW_PAIR"] for row in rows),
        "zankokuna": any(row["id"] == 218 and row["weight"] == 0 and row["mode"] == defines["BOSSCOMBO_MODE_ZANKOKUNA_PAIR"] for row in rows),
        "higlur": "BOSSCOMBO_FLAGS_HIGLUR" in defs and "UHVS_ResolveHiglurDraw" in versus,
        "shadow_setup": 'ACS_NamedExecuteWait("ub_ShadowBossManager"' in bossselect and "BOSSCOMBO_FLAG_SHADOW" in bossselect,
        "zankokuna_setup": "BossZankokunaVersusEligible" in funcs and "BOSSCOMBO_FLAG_ZANKOKUNA" in (ROOT / "src/acs_source/unholy/uh_arena_fx.acs").read_text(encoding="utf-8"),
        "higlur_queue": 'ub_InitiateUltraBoss", 0, 403' in versus,
    }
    check(
        "semantic special versus branches",
        all(special_modes.values()) and "BossComboHasFlag" in funcs,
        "Shadow, Zankokuna and Red/Blue-Higlur branches need semantic modes/flags and owned setup/terminal hooks",
    )
    higlur_reason_mutation = versus.replace(
        "reason = bothnormaldeath ? UHVS_REASON_DEATH : UHVS_REASON_FORFEIT;",
        "reason = UHVS_REASON_DEATH;",
        1,
    )
    higlur_gate_mutation = versus.replace(
        "result == UHVS_DRAW && bothnormaldeath &&",
        "result == UHVS_DRAW &&",
        1,
    )
    check(
        "Higlur death-state mutation guard",
        versus_death_gate_contract(versus)
        and not versus_death_gate_contract(higlur_reason_mutation)
        and not versus_death_gate_contract(higlur_gate_mutation),
        "Higlur may queue only when both BOSSHP_DEATH values are normal death states 5/6, never simultaneous forfeits",
    )
    shadow_order_mutation = bossselect.replace(
        "if (i == 0) {shadowtarget0 = tempboss;}",
        "if (i == 0) {bossdataarr[i][BOSSDATA_MORPHED] = tempboss;}",
        1,
    )
    check(
        "Shadow target ordering mutation guard",
        shadow_target_order_contract(bossselect)
        and not shadow_target_order_contract(shadow_order_mutation),
        "Shadow must validate both independent targets and duplicates before writing BOSSDATA_MORPHED",
    )
    check(
        "special versus allowlist is closed",
        "function bool BossZankokunaVersusEligible" in funcs
        and "BossZankokunaPrimaryEligible" in funcs
        and "BossZankokunaVersusEligible" in funcs
        and function_body(funcs, "BossZankokunaVersusEligible").rstrip().endswith("return false;"),
        "special bosses must use an explicit allowlist with a default reject",
    )
    check(
        "legacy BossEvent777 not restored",
        "BossEvent777" not in funcs and "BossEvent777" not in versus,
        "special branches must not use the ambiguous legacy BossEvent777 hook",
    )

    if not args.source_only:
        music = args.music_pk3.resolve()
        music_lumps: set[str] = set()
        if not music.is_file():
            check("Batch D music resources", False, f"missing archive: {music}")
        else:
            try:
                with zipfile.ZipFile(music) as archive:
                    bad = archive.testzip()
                    for name in archive.namelist():
                        if name.endswith("/"):
                            continue
                        leaf = Path(name).name
                        music_lumps.add(leaf.upper())
                        music_lumps.add(Path(leaf).stem.upper())
                missing = sorted(REQUIRED_MUSIC - music_lumps)
                check(
                    "Batch D music resources",
                    bad is None and not missing,
                    f"bad member: {bad}" if bad else ("missing: " + ", ".join(missing) if missing else f"{len(REQUIRED_MUSIC)} required lumps found in {music}"),
                )
            except (OSError, zipfile.BadZipFile) as exc:
                check("Batch D music resources", False, f"invalid archive: {exc}")

        # V3: every combo row must have complete resources.  This is the static
        # gate that keeps a missing actor / face / music track out of the random
        # pool; new versus rows are force-only until they pass it.
        try:
            bossdefs_text = BOSSDEFS.read_text(encoding="utf-8")
        except OSError as exc:
            bossdefs_text = ""
            print(f"warn: cannot read {BOSSDEFS}: {exc}", file=sys.stderr)
        bosses = parse_define_bosses(bossdefs_text) if bossdefs_text else {}
        face_names = collect_face_names()
        resource_issues: list[tuple[str, str, int]] = []
        if rows and bosses:
            resource_issues = combo_resource_issues(rows, bosses, face_names, music_lumps)
        random_issues = [f"{cid}: {msg}" for cid, msg, weight in resource_issues if weight != 0]
        forced_issues = [f"{cid}: {msg}" for cid, msg, weight in resource_issues if weight == 0]
        check(
            "random-eligible combos complete",
            bool(rows and bosses) and not random_issues,
            "all random-eligible combos have actors/faces/music"
            if not random_issues
            else "; ".join(random_issues[:6]),
        )
        check(
            "force-only combo resource gaps reported",
            True,
            "none" if not forced_issues else f"{len(forced_issues)} gap(s): " + "; ".join(forced_issues[:4]),
        )

    # Release decision: only the reviewed/resource-complete fixed themed rows
    # 210-216 enter the low-weight random pool.  206/207/209 and the semantic
    # special branches remain force-only, independently of forceability.
    versus_weighted: list[str] = []
    released_versus = set(range(210, 217))
    versus_flag = defines.get("BOSSCOMBO_FLAG_VERSUS", 1)
    if rows:
        for row in rows:
            flags_val = row["flags"]
            if not flags_val & versus_flag:
                continue
            if row["id"] in released_versus:
                if row["weight"] != 1:
                    versus_weighted.append(f"{row['id']} released weight={row['weight']}")
            elif row["weight"] != 0:
                versus_weighted.append(f"{row['id']} force-only weight={row['weight']}")
    check(
        "versus random-pool release policy",
        not versus_weighted,
        "only reviewed fixed duels 210-216 have weight 1; 206/207/209/217/218 stay force-only"
        if not versus_weighted else "; ".join(versus_weighted),
    )

    failed = [item for item in checks if item["status"] == "fail"]
    result = {"status": "pass" if not failed else "fail", "checks": checks, "failed": len(failed)}
    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        for item in checks:
            print(f"{item['status'].upper():4} {item['name']}: {item['detail']}")
        print(f"Batch D static/resource checks: {len(checks) - len(failed)} passed, {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

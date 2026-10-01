#!/usr/bin/env python3
"""Generate Unholy namespaced bar ACS, SBARINFO, and BarFX actors.

TOML is the sole source for Unholy's named bars. SBARINFO.*.uhappend expands
those declarations into InInventory-banded DrawBar lines. Main SBARINFO.H/V
keep the v6b CustSbarSlotFlag slot lines for other mods.

The hand-authored tools/bars.toml adds namespaced bar groups without a
hard-coded layer ceiling. Each group owns one namespace. API IDs follow bar
declaration order inside each group; sparse priorities control SBARINFO draw
order. All namespaces share one clear callback (`UHBar_ClearAll`) that is
registered once; core_DrawBar_RegisterClear's capacity must not scale with
the number of TOML groups.

With --check, regenerate everything in memory and compare against the files
on disk; exit 1 with a per-file report on any drift (never writes).
"""
import argparse
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "src"
UH_BARFX = ROOT / "actors" / "inventory" / "sbar" / "UH_BarFX.dec"
SBAR_HZ = ROOT / "SBARINFO.h.uhappend"
SBAR_VZ = ROOT / "SBARINFO.v.uhappend"
TEX_BARS = ROOT / "TEXTURES.bars"
ANIM_BARS = ROOT / "ANIMDEFS.bars"
CONFIG = Path(__file__).resolve().parent / "bars.toml"
GENERATED_ACS = ROOT / "acs_source" / "hud" / "class_bars_generated.acs"

POS_BANKS = [
    ("1", "Custom Bar Pos1 (bar1)", 58, 184, 16, 8),
    ("2", "Custom Bar Pos2 (bar2)", 58, 176, 8, 8),
    ("3", "Custom Bar Pos3 (bar3)", 58, 168, 0, 8),
    ("HP", "Custom Bar PosHP", 130, 184, 24, 8),
]

ACTOR_NAME_RX = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
COMMON_BAR_GRAPHICS = {"BAREMPTY", "VAREMPTY", "NOBAR", "VNOBAR"}
# Graphics supplied by the v6b base package rather than this addon. They are
# valid DrawBar graphics, but are intentionally absent from src/TEXTURES.
BASE_BAR_GRAPHICS = {
    "BARAMM13", "VARAMM13", "BARFLS1", "VARFLS1",
    "02_BSVAR",
}
INT32_MAX = 0x7FFFFFFF


def pascal_id(value: str) -> str:
    return "".join(part[:1].upper() + part[1:] for part in value.split("_") if part)


def bar_constant(bar: dict) -> str:
    return bar["constant_name"]


def draw_helper(namespace: str) -> str:
    stem = namespace[6:] if namespace.casefold().startswith("uhbar_") else namespace
    return f"{stem}_DrawBar"

STALE_GENERATED = (
    ROOT / "actors" / "inventory" / "sbar" / "BarFX.txt",
    ROOT / "acs_source" / "hud" / "stealthsniper_generated.acs",
    ROOT / "TEXTURES.barscat",
    ROOT / "TEXTURES.barspos",
    ROOT / "TEXTURES.barpos",
    ROOT / "ANIMDEFS.barscat",
    ROOT / "ANIMDEFS.barpos",
)


# --- DrawBar fill sanity -----------------------------------------------------
# DrawBar draws its fill at the slot coordinates and clips it to the value
# region, but the renderer still honours the fill texture's own left/top
# offset (g_shared/sbarinfo.cpp DrawGraphic -> DTA_Left/Top default to the
# texture offsets), so a fill whose texture -- or whose animation frames --
# carry a non-zero offset renders displaced from its slot.
#
# A fill that is fully transparent over an opaque empty draws the *inverse* of
# the value (the visible pixels come from the background), which is only ever
# correct for a deliberate reverse/mask bar.
#
# Both hazards shipped once when bars.toml selected aliases animated over the
# 34_C_V1x/34_C_H1x group. Those frames carry offsets of (-16,-8) and
# (-58,-184), so the charge bars drew displaced. The guards below keep that
# class of pairing out of the config.
TEXTURE_DEF_RX = re.compile(
    r"\b(?:graphic|texture)\s+([A-Za-z0-9_]+)\s*(?:,[^{}]*)?"
    r"\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}",
    re.IGNORECASE,
)
TEXTURE_OFFSET_RX = re.compile(r"\boffset\s*(-?\d+)\s*,\s*(-?\d+)", re.IGNORECASE)
ANIMATION_HEAD_RX = re.compile(r"^(?:texture|flat)\s+([A-Za-z0-9_]+)\b(.*)$", re.IGNORECASE)
ANIMATION_STOP_RX = re.compile(r"^(?:wall|sprite|graphic|warp|warp2|noise)\b", re.IGNORECASE)
ANIMATION_PIC_RX = re.compile(r"\bpic\s+([A-Za-z0-9_]+)", re.IGNORECASE)
ANIMATION_RANGE_RX = re.compile(r"\brange\s+([A-Za-z0-9_]+)\s+([A-Za-z0-9_]+)", re.IGNORECASE)
TRANSPARENT_PATCH = "tnt1a0"
LINE_COMMENT_RX = re.compile(r"//[^\n]*")


def strip_line_comments(text: str) -> str:
    """TEXTURES/ANIMDEFS have no string literals, so `//` always starts a comment.

    Commented-out definitions must not reach the parsers below: a commented
    offset would otherwise be treated as live and could trip the fill guard on a
    graphic that no longer exists.
    """
    return LINE_COMMENT_RX.sub("", text)


def bar_graphics_text(pattern: str) -> str:
    return "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in sorted(ROOT.glob(pattern))
    )


def parse_texture_defs(text: str) -> dict:
    """name -> {"patches": [...], "offset": (x, y)} for every TEXTURES entry."""
    defs = {}
    for m in TEXTURE_DEF_RX.finditer(text):
        name = m.group(1).casefold()
        body = m.group(2)
        entry = defs.setdefault(name, {"patches": [], "offset": (0, 0)})
        entry["patches"].extend(
            patch.casefold() for patch in re.findall(r"\bpatch\s+([A-Za-z0-9_]+)", body)
        )
        offset = TEXTURE_OFFSET_RX.search(body)
        if offset:
            entry["offset"] = (int(offset.group(1)), int(offset.group(2)))
    return defs


def parse_texture_animations(text: str) -> dict:
    """name -> frame list for every ANIMDEFS animation with at least one frame.

    Handles both the block form (`texture X` followed by `pic` lines) and the
    inline form (`texture X range A B tics 2`). Only animations are recorded;
    an ANIMDEFS entry without frames is not an animation.
    """
    animations = {}
    current = None

    def add_frames(frames, inline):
        for frame in ANIMATION_PIC_RX.findall(inline):
            frames.append(frame.casefold())
        for first, last in ANIMATION_RANGE_RX.findall(inline):
            frames.extend(range_frames(first, last))

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        head = ANIMATION_HEAD_RX.match(stripped)
        if head:
            current = head.group(1).casefold()
            animations.setdefault(current, [])
            add_frames(animations[current], head.group(2))
            continue
        if ANIMATION_STOP_RX.match(stripped):
            current = None
            continue
        if current is not None:
            add_frames(animations[current], stripped)
    return {name: frames for name, frames in animations.items() if frames}


def range_frames(first: str, last: str) -> list:
    """`range 34_B_V11 34_B_V14` -> [34_b_v11, 34_b_v12, 34_b_v13, 34_b_v14]."""
    head = re.match(r"^(.*?)(\d+)$", first)
    tail = re.match(r"^(.*?)(\d+)$", last)
    if not head or not tail or head.group(1).casefold() != tail.group(1).casefold():
        return [first.casefold(), last.casefold()]
    start, end = int(head.group(2)), int(tail.group(2))
    if end < start:
        start, end = end, start
    width = len(head.group(2))
    return [f"{head.group(1)}{index:0{width}d}".casefold()
            for index in range(start, end + 1)]


def fill_animation_frames(name: str, animations: dict) -> list:
    frames = animations.get(name.casefold())
    return frames if frames else [name.casefold()]


def fill_offsets(name: str, defs: dict, animations: dict) -> list:
    """Non-zero offsets reachable from a fill graphic, as (frame, x, y)."""
    found = []
    for frame in fill_animation_frames(name, animations):
        offset = defs.get(frame, {}).get("offset", (0, 0))
        if offset != (0, 0):
            found.append((frame, offset[0], offset[1]))
    return found


def is_transparent_fill(name: str, defs: dict, animations: dict) -> bool:
    """True only when every pixel of the fill is a known transparent patch."""
    if name.casefold() in animations:
        return False
    entry = defs.get(name.casefold())
    if entry is None:
        return False  # unknown or base-package graphic: do not guess
    patches = entry["patches"]
    if not patches:
        return True
    return all(patch == TRANSPARENT_PATCH for patch in patches)


def validate_fill_graphics(bars: list, defs: dict, animations: dict):
    """Reject fill graphics that cannot render as a growing slot bar."""
    for bar in bars:
        label = bar_label(bar)
        reverse_mask = bar.get("reverse_mask", False)
        offset_fill_ack = bar.get("offset_fill_ack", False)
        for full_key, empty_key, axis in (
            ("vertical_full", "vertical_empty", "vertical"),
            ("horizontal_full", "horizontal_empty", "horizontal"),
        ):
            fill = bar[full_key]
            offsets = fill_offsets(fill, defs, animations)
            if offsets and not offset_fill_ack:
                frame, dx, dy = offsets[0]
                raise SystemExit(
                    f"{CONFIG}: {label}: {axis} fill {fill!r} renders at offset "
                    f"({dx}, {dy}) via {frame!r}. DrawBar draws the fill at the slot "
                    "coordinates and the renderer applies the texture offset "
                    "(v_draw.cpp: parms->left/top default to GetScaledLeftOffset/"
                    "TopOffset), so an offset fill is drawn displaced. Use a fill "
                    "whose frames have no offset, or set offset_fill_ack = true to "
                    "declare a reviewed exception."
                )
            if reverse_mask:
                continue
            if is_transparent_fill(fill, defs, animations) and not is_transparent_fill(
                bar[empty_key], defs, animations
            ):
                raise SystemExit(
                    f"{CONFIG}: {label}: {axis} fill {fill!r} is fully transparent "
                    f"while empty {bar[empty_key]!r} is not, which draws the inverse "
                    "of the value. Set reverse_mask = true if that is intended."
                )


def load_bar_graphics():
    """Return (known graphics, texture definitions, animations).

    Comments are stripped first so a commented-out definition neither counts as
    a known graphic nor contributes patches/offsets/animation frames.
    """
    textures = strip_line_comments(bar_graphics_text("TEXTURES*"))
    animdefs = strip_line_comments(bar_graphics_text("ANIMDEFS*"))
    known = {name.casefold() for name in re.findall(
        r"\b(?:graphic|patch|texture)\s+([A-Za-z0-9_]+)", textures + "\n" + animdefs,
    )} | {name.casefold() for name in COMMON_BAR_GRAPHICS | BASE_BAR_GRAPHICS}
    return known, parse_texture_defs(textures), parse_texture_animations(animdefs)


def load_bar_config() -> dict:
    """Load and validate the hand-authored TOML bar definitions."""
    with CONFIG.open("rb") as fp:
        config = tomllib.load(fp)
    if type(config.get("schema_version")) is not int or config["schema_version"] != 1:
        raise SystemExit(f"{CONFIG}: schema_version must be 1")
    groups = config.get("groups")
    if not isinstance(groups, list) or not groups:
        raise SystemExit(f"{CONFIG}: expected at least one [[groups]] entry")
    bars = []
    seen_namespaces = set()
    for group in groups:
        if not isinstance(group, dict):
            raise SystemExit(f"{CONFIG}: each [[groups]] entry must be a table")
        namespace = group.get("namespace")
        if not isinstance(namespace, str) or not ACTOR_NAME_RX.fullmatch(namespace):
            raise SystemExit(f"{CONFIG}: group has invalid namespace")
        namespace_key = namespace.casefold()
        if namespace_key in seen_namespaces:
            raise SystemExit(f"{CONFIG}: duplicate group namespace {namespace!r}")
        seen_namespaces.add(namespace_key)
        group_bars = group.get("bars")
        if not isinstance(group_bars, list) or not group_bars:
            raise SystemExit(f"{CONFIG}: {namespace}: expected [[groups.bars]] entries")
        for source_bar in group_bars:
            if not isinstance(source_bar, dict):
                raise SystemExit(f"{CONFIG}: each [[groups.bars]] entry must be a table")
            bar = dict(source_bar)
            bar["_namespace"] = namespace
            bars.append(bar)
    config["bars"] = bars
    known_graphics, texture_defs, animations = load_bar_graphics()
    seen_ids = set()
    seen_constants = set()
    seen_helpers = {}
    for bar in bars:
        label = bar_label(bar)
        for key in ("id", "position", "priority", "vertical_full", "vertical_empty",
                    "horizontal_full", "horizontal_empty"):
            if key not in bar:
                raise SystemExit(f"{CONFIG}: {label}: missing {key!r}")
        if not isinstance(bar["id"], str) or not ACTOR_NAME_RX.fullmatch(bar["id"]):
            raise SystemExit(f"{CONFIG}: {label}: invalid bar id {bar['id']!r}")
        constant_name = bar.get("constant_name")
        if not isinstance(constant_name, str) or not ACTOR_NAME_RX.fullmatch(constant_name):
            raise SystemExit(f"{CONFIG}: {label}: invalid constant_name")
        if len(constant_name) >= 32:
            raise SystemExit(
                f"{CONFIG}: {label}: constant_name exceeds ACC's 31-character limit"
            )
        if not constant_name.upper().startswith("UHBAR_"):
            raise SystemExit(f"{CONFIG}: {label}: constant_name must start with UHBAR_")
        bar_namespace = bar["_namespace"]
        folded_id = (bar_namespace.casefold(), bar["id"].casefold())
        if folded_id in seen_ids:
            raise SystemExit(f"{CONFIG}: duplicate bar id {label!r}")
        seen_ids.add(folded_id)
        if constant_name.casefold() in seen_constants:
            raise SystemExit(f"{CONFIG}: {label}: duplicate constant_name {constant_name!r}")
        seen_constants.add(constant_name.casefold())
        namespace_key = bar_namespace.casefold()
        helper = draw_helper(bar_namespace)
        if len(helper) >= 32:
            raise SystemExit(
                f"{CONFIG}: {label}: generated draw helper exceeds ACC's "
                "31-character limit"
            )
        previous_helper_namespace = seen_helpers.get(helper.casefold())
        if (previous_helper_namespace is not None
                and previous_helper_namespace.casefold() != namespace_key):
            raise SystemExit(
                f"{CONFIG}: {label}: generated draw helper {helper!r} is not unique"
            )
        seen_helpers[helper.casefold()] = bar_namespace
        if bar["position"] not in {p[0] for p in POS_BANKS}:
            raise SystemExit(f"{CONFIG}: {label}: invalid position {bar['position']!r}")
        priority = bar["priority"]
        if type(priority) is not int or priority < 0:
            raise SystemExit(f"{CONFIG}: {label}: invalid layer priority")
        has_source = "source" in bar
        has_capacity = "capacity" in bar
        if has_source and has_capacity:
            raise SystemExit(f"{CONFIG}: {label}: source and capacity are mutually exclusive")
        if has_source:
            source = bar["source"]
            if not isinstance(source, str) or not ACTOR_NAME_RX.fullmatch(source):
                raise SystemExit(f"{CONFIG}: {label}: source must be a valid identifier")
        else:
            if not has_capacity:
                raise SystemExit(f"{CONFIG}: {label}: missing 'capacity'")
            capacity = bar["capacity"]
            if type(capacity) is not int or capacity <= 0 or capacity > INT32_MAX:
                raise SystemExit(
                    f"{CONFIG}: {label}: capacity must be an integer in 1..{INT32_MAX}"
                )
        reverse_mask = bar.get("reverse_mask", False)
        if not isinstance(reverse_mask, bool):
            raise SystemExit(f"{CONFIG}: {label}: reverse_mask must be boolean")
        offset_fill_ack = bar.get("offset_fill_ack", False)
        if not isinstance(offset_fill_ack, bool):
            raise SystemExit(f"{CONFIG}: {label}: offset_fill_ack must be boolean")
        for key in ("vertical_full", "vertical_empty", "horizontal_full", "horizontal_empty"):
            image = bar[key]
            if not isinstance(image, str) or not image:
                raise SystemExit(f"{CONFIG}: {label}: empty {key}")
            if image.casefold() not in known_graphics:
                raise SystemExit(f"{CONFIG}: {label}: missing image reference {image!r}")
    validate_fill_graphics(bars, texture_defs, animations)
    validate_selector_banks(config)
    validate_generated_actor_names(config)
    return config


def namespaced_selector(bar: dict) -> str:
    return f"{bar['_namespace']}_P{bar['position']}L{bar['priority']}Selector"


def namespaced_ammo(bar: dict) -> str:
    return f"{bar['_namespace']}_P{bar['position']}L{bar['priority']}_{pascal_id(bar['id'])}Ammo"


def bar_label(bar: dict) -> str:
    namespace = bar.get("_namespace", "<unknown namespace>")
    bar_id = bar.get("id", "<unknown id>")
    return f"{namespace}.{bar_id}"


def layer_selector_id(config: dict, bar: dict) -> int:
    """Dense selector amount; layer priority is never an inventory amount."""
    bank = (bar["_namespace"].casefold(), bar["position"], bar["priority"])
    return 1 + sum(1 for other in config["bars"]
                   if (other["_namespace"].casefold(), other["position"],
                       other["priority"]) == bank
                   and other["id"].casefold() < bar["id"].casefold())


def layer_selector_capacity(config: dict, bar: dict) -> int:
    bank = (bar["_namespace"].casefold(), bar["position"], bar["priority"])
    return sum(1 for other in config["bars"]
               if (other["_namespace"].casefold(), other["position"],
                   other["priority"]) == bank)


def validate_selector_banks(config: dict):
    """Ensure shared selector banks receive dense, deterministic amounts."""
    banks = {}
    for bar in config["bars"]:
        bank = (bar["_namespace"].casefold(), bar["position"], bar["priority"])
        banks.setdefault(bank, []).append(bar)
    for bars in banks.values():
        actual = sorted(layer_selector_id(config, bar) for bar in bars)
        expected = list(range(1, len(bars) + 1))
        if actual != expected:
            names = ", ".join(bar_label(bar) for bar in bars)
            raise SystemExit(
                f"{CONFIG}: selector bank numbering is not dense for {names}"
            )


def validate_generated_actor_names(config: dict):
    """Match Zandronum's case-insensitive actor-name collision behavior."""
    seen = {}
    for bar in config["bars"]:
        bank = (bar["_namespace"].casefold(), bar["position"], bar["priority"])
        actors = [("selector", namespaced_selector(bar))]
        if "source" not in bar:
            actors.append(("ammo", namespaced_ammo(bar)))
        for kind, actor in actors:
            key = actor.casefold()
            previous = seen.get(key)
            if previous is not None:
                previous_kind, previous_label, previous_bank = previous
                if (kind == "selector" and previous_kind == "selector"
                        and bank == previous_bank):
                    continue
                raise SystemExit(
                    f"{CONFIG}: generated actor collision {actor!r} ({kind}) "
                    f"between {previous_label} and {bar_label(bar)}"
                )
            seen[key] = (kind, bar_label(bar), bank)


def gen_namespaced_append_lines(config: dict, horiz: bool, cursed: bool = False) -> list[str]:
    lines = []
    position_order = {pos[0]: index for index, pos in enumerate(POS_BANKS)}
    bars = sorted(
        config["bars"],
        key=lambda b: (b["priority"], position_order[b["position"]],
                       b["_namespace"].casefold(), b["id"].casefold()),
    )
    for bar in bars:
        selector = namespaced_selector(bar)
        ammo = bar["source"] if "source" in bar else namespaced_ammo(bar)
        selector_id = layer_selector_id(config, bar)
        if horiz:
            fill, empty, x, y = (bar["horizontal_full"], bar["horizontal_empty"],
                                 next(p[2] for p in POS_BANKS if p[0] == bar["position"]),
                                 next(p[3] for p in POS_BANKS if p[0] == bar["position"]))
            orientation = "horizontal"
        else:
            fill, empty, x, y = (bar["vertical_full"], bar["vertical_empty"],
                                 next(p[4] for p in POS_BANKS if p[0] == bar["position"]),
                                 next(p[5] for p in POS_BANKS if p[0] == bar["position"]))
            orientation = "vertical"
        indent = "  "
        if cursed:
            image = "CURSEVAR" if horiz else "CURSEBAR"
            lines.append(
                f'{indent * 4}InInventory "{selector}", {selector_id} '
                f'{{InInventory not "{selector}", {selector_id + 1} '
                f'{{DrawImage "{image}", {x}, {y};}}}}'
            )
            continue
        lines.append(
            f'{indent * 4}InInventory "{selector}", {selector_id} '
            f'{{InInventory not "{selector}", {selector_id + 1} '
            f'{{DrawBar "{fill}", "{empty}", {ammo}, '
            f'{orientation}, {x}, {y};}}}}'
        )
    return lines


def gen_append_files(config):
    def render(horiz: bool) -> str:
        indent = "  "
        mode = "normal" if horiz else "fullscreen"
        lines = [
            f"AppendStatusBar {mode}, forcescaled {{",
            f'{indent}InInventory "DrawStatusBarFlag", 1 {{',
            f'{indent * 2}InInventory not "NoHud", 1 {{',
            f'{indent * 3}InInventory not "NoHealthBar", 1 || "Pharaoh4MICurse_Unknown", 1 {{',
            *gen_namespaced_append_lines(config, horiz),
            f"{indent * 3}}}",
            f'{indent * 3}InInventory not "NoHealthBar", 1 {{',
            f'{indent * 4}InInventory "Pharaoh4MICurse_Unknown", 1 {{',
            *(indent + line for line in gen_namespaced_append_lines(config, horiz, cursed=True)),
            f"{indent * 4}}}",
            f"{indent * 3}}}",
            f"{indent * 2}}}",
            f"{indent}}}",
            "}",
        ]
        return "\n".join(lines) + "\n"

    return render(True), render(False)


def gen_namespaced_barfx_actors(config: dict) -> str:
    block = ["// $UH — TOML namespaced bar selectors / ammo"]
    seen = set()
    for bar in config["bars"]:
        actors = [(
            namespaced_selector(bar), "Inventory", [
                "inventory.amount 1",
                f"Inventory.MaxAmount {layer_selector_capacity(config, bar)}"])]
        if "source" not in bar:
            actors.append((
                namespaced_ammo(bar), "Ammo", [
                    "+INVENTORY.IGNORESKILL", "inventory.amount 0",
                    f"Inventory.MaxAmount {bar['capacity']}"]))
        for actor, parent, extra in actors:
            actor_key = actor.casefold()
            if actor_key in seen:
                continue
            seen.add(actor_key)
            block += [f"actor {actor} : {parent} {{", *(f"  {line}" for line in extra), "}", ""]
    return "\n".join(block)


def barfx_updated_text(config):
    text = UH_BARFX.read_text(encoding="utf-8")
    m = re.search(r"(?m)^\s*//\s*\$UH — TOML namespaced bar selectors / ammo.*$", text)
    if not m:
        raise SystemExit("UH_BarFX.dec missing TOML bar marker")
    return text[:m.start()] + gen_namespaced_barfx_actors(config)


def gen_generated_acs(config: dict) -> str:
    """Generate numeric selector IDs, draw helpers, and clear registration."""
    lines = [
        "// Generated by tools/_gen_barpos.py from tools/bars.toml.",
        "// Namespaced SBARINFO bars; do not edit by hand.",
        "",
    ]
    namespaces = {}
    for bar in config["bars"]:
        namespaces.setdefault(bar["_namespace"].casefold(), []).append(bar)
    for bars in namespaces.values():
        namespace = bars[0]["_namespace"]
        direct_source = all("source" in bar for bar in bars)
        for index, bar in enumerate(bars, 1):
            lines.append(f"#define {bar_constant(bar)} {index}")
        signature = "(int id)" if direct_source else "(int id, int amount, int capacity)"
        lines += [
            "",
            f"function void {draw_helper(namespace)}{signature} {{",
        ]
        if not direct_source:
            lines += [
                "  if (capacity <= 0) { return; }",
                "  if (amount < 0) { amount = 0; }",
                "  if (amount > capacity) { amount = capacity; }",
            ]
        lines += [
            "  switch (id) {",
        ]
        for bar in bars:
            selector = namespaced_selector(bar)
            lines += [
                f"    case {bar_constant(bar)}:",
                f'      SetInventory("{selector}", {layer_selector_id(config, bar)});',
            ]
            if "source" not in bar:
                lines.append(
                    f'      SetAmmoAmountAndCapacity("{namespaced_ammo(bar)}", amount, capacity);'
                )
            lines.append("      break;")
        lines += [
            "    default:",
            "      break;",
            "  }",
            "}",
            "",
        ]

    # One clear callback for every generated namespace: core_DrawBar_RegisterClear
    # holds at most UH_BAR_CLEAR_MAX entries, and per-namespace registration would
    # silently overflow it, leaving selectors latched across class/weapon/morph
    # changes. Latched selectors are reset here by name, deduped in declaration
    # order (shared banks keep one selector inventory).
    clear_inventories = []
    seen_clear = set()
    for bar in config["bars"]:
        for name in (namespaced_selector(bar),) + (
            () if "source" in bar else (namespaced_ammo(bar),)
        ):
            if name not in seen_clear:
                seen_clear.add(name)
                clear_inventories.append(name)
    lines += [
        'script "UHBar_ClearAll" (int cam) CLIENTSIDE {',
    ]
    lines += [f'  SetActorInventory(cam, "{name}", 0);' for name in clear_inventories]
    lines += [
        "}",
        "",
        'script "UHBar_ClearAll_Register" OPEN CLIENTSIDE {',
        '  int result = ACS_NamedExecuteWithResult(',
        '      "core_DrawBar_RegisterClear", "UHBar_ClearAll");',
        "  if (result < 0) {",
        '    Log(s:"UHBar_ClearAll_Register: core_DrawBar_RegisterClear failed: ",',
        '        i:result);',
        "  }",
        "}",
        "",
    ]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="verify generated files are up to date; exit 1 on drift")
    args = ap.parse_args()

    config = load_bar_config()
    hz, vz = gen_append_files(config)
    outputs = {
        SBAR_HZ: hz,
        SBAR_VZ: vz,
        UH_BARFX: barfx_updated_text(config),
        GENERATED_ACS: gen_generated_acs(config),
    }

    if args.check:
        drift = []
        for path, new in outputs.items():
            old = path.read_text(encoding="utf-8") if path.exists() else None
            if old != new:
                drift.append(path.name)
        for p in STALE_GENERATED:
            if p.exists():
                drift.append(p.name + " (stale file still present)")
        if drift:
            print("DRIFT — regenerate with: python3 tools/_gen_barpos.py")
            for d in drift:
                print(f"  {d}")
            sys.exit(1)
        print("check OK: all generated outputs up to date")
        return

    for path, new in outputs.items():
        if not path.exists() or path.read_text(encoding="utf-8") != new:
            path.write_text(new, encoding="utf-8")
            print(f"wrote {path.name}")
    for p in STALE_GENERATED:
        if p.exists():
            p.unlink()
            print(f"deleted {p.name}")


if __name__ == "__main__":
    main()

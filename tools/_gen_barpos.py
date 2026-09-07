#!/usr/bin/env python3
"""Generate Unholy bar ACS, HZ/VZ AppendStatusBar, and BarFX actors.

Legacy Unholy bars at the standard bar1/bar2/bar3/HP slots use real graphic
names through DrawCustomBarString*. Those calls are collected into the
uh_barcat.acs compatibility catalog; SBARINFO.*.uhappend expands each pair
into InInventory-banded DrawBar lines (4 slots x 4 layers x 2 HUD modes).
This does not define BRSLT/BZSLT. Main SBARINFO.H/V keep v6b
CustSbarSlotFlag + BRSLT lines for other mods.

The hand-authored tools/bars.toml adds namespaced bars without a hard-coded
layer ceiling. Each bar may override the top-level namespace and clear callback
to keep independent class groups isolated. API IDs follow declaration order
inside each namespace; sparse priorities control SBARINFO draw order.

With --check, regenerate everything in memory and compare against the files
on disk; exit 1 with a per-file report on any drift (never writes).
"""
import argparse
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "src"
ACS_CAT = ROOT / "acs_source" / "_includes" / "mod_api" / "uh_barcat.acs"
UH_BARFX = ROOT / "actors" / "inventory" / "sbar" / "UH_BarFX.dec"
SBAR_H = ROOT / "SBARINFO.h._core"
SBAR_V = ROOT / "SBARINFO.v._core"
SBAR_HZ = ROOT / "SBARINFO.h.uhappend"
SBAR_VZ = ROOT / "SBARINFO.v.uhappend"
TEX_BARS = ROOT / "TEXTURES.bars"
ANIM_BARS = ROOT / "ANIMDEFS.bars"
CONFIG = Path(__file__).resolve().parent / "bars.toml"
GENERATED_ACS = ROOT / "acs_source" / "hud" / "class_bars_generated.acs"

UH_BAR_LAYER_MAX = 4
KIND_RENAME = {
    "BRSLT": "UHVT",
    "BRSLB": "UHVB",
    "VRSLT": "UHHT",
    "VRSLB": "UHHB",
}
BRSLT_NAME_RX = re.compile(r"\b(BRSLT|BRSLB|VRSLT|VRSLB)(\d{3})\b")

POS_BANKS = [
    ("1", "Custom Bar Pos1 (bar1)", 58, 184, 16, 8),
    ("2", "Custom Bar Pos2 (bar2)", 58, 176, 8, 8),
    ("3", "Custom Bar Pos3 (bar3)", 58, 168, 0, 8),
    ("HP", "Custom Bar PosHP", 130, 184, 24, 8),
]

ACTOR_NAME_RX = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
COMMON_BAR_GRAPHICS = {"BAREMPTY", "VAREMPTY", "NOBAR", "VNOBAR"}
INT32_MAX = 0x7FFFFFFF


def pascal_id(value: str) -> str:
    return "".join(part[:1].upper() + part[1:] for part in value.split("_") if part)


def bar_constant(bar: dict) -> str:
    suffix = bar["_constant_suffix"]
    return bar["_namespace"].upper() + (f"_{suffix}" if suffix else "")

STALE_GENERATED = (
    ROOT / "actors" / "inventory" / "sbar" / "BarFX.txt",
    ROOT / "acs_source" / "hud" / "stealthsniper_generated.acs",
    ROOT / "TEXTURES.barscat",
    ROOT / "TEXTURES.barspos",
    ROOT / "TEXTURES.barpos",
    ROOT / "ANIMDEFS.barscat",
    ROOT / "ANIMDEFS.barpos",
)


def renamed_bars_text(path: Path) -> str:
    """TEXTURES.bars / ANIMDEFS.bars: BRSLT### -> UHVT### (idempotent)."""
    return BRSLT_NAME_RX.sub(lambda m: KIND_RENAME[m.group(1)] + m.group(2),
                             path.read_text(encoding="utf-8"))


def parse_str_array(text: str, name: str) -> list:
    m = re.search(
        rf"str\s+{re.escape(name)}\s*\[[^\]]+\]\s*=\s*\{{([^}}]*)\}}",
        text,
    )
    if not m:
        return []
    return re.findall(r'"([^"]+)"', m.group(1))


def load_bar_config() -> dict:
    """Load and validate the hand-authored TOML bar definitions."""
    with CONFIG.open("rb") as fp:
        config = tomllib.load(fp)
    if type(config.get("schema_version")) is not int or config["schema_version"] != 1:
        raise SystemExit(f"{CONFIG}: schema_version must be 1")
    bars = config.get("bars")
    if not isinstance(bars, list) or not bars:
        raise SystemExit(f"{CONFIG}: expected at least one [[bars]] entry")
    graphic_text = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for pattern in ("TEXTURES*", "ANIMDEFS*")
        for path in ROOT.glob(pattern)
    )
    known_graphics = {name.casefold() for name in re.findall(
        r"\b(?:graphic|patch|texture)\s+([A-Za-z0-9_]+)", graphic_text,
    )} | {name.casefold() for name in COMMON_BAR_GRAPHICS}
    namespace = config.get("namespace")
    callback = config.get("clear_callback")
    if not isinstance(namespace, str) or not ACTOR_NAME_RX.fullmatch(namespace):
        raise SystemExit(f"{CONFIG}: invalid namespace")
    if not isinstance(callback, str) or not ACTOR_NAME_RX.fullmatch(callback):
        raise SystemExit(f"{CONFIG}: invalid clear_callback")
    seen_ids = set()
    seen_constants = set()
    callbacks = {}
    namespace_callbacks = {}
    for bar in bars:
        if not isinstance(bar, dict):
            raise SystemExit(f"{CONFIG}: each [[bars]] entry must be a table")
        for key in ("id", "position", "priority", "vertical_full", "vertical_empty",
                    "horizontal_full", "horizontal_empty", "capacity"):
            if key not in bar:
                raise SystemExit(f"{CONFIG}: bar is missing {key!r}")
        if not isinstance(bar["id"], str) or not ACTOR_NAME_RX.fullmatch(bar["id"]):
            raise SystemExit(f"{CONFIG}: invalid bar id {bar['id']!r}")
        constant_suffix = bar.get("constant_suffix", "")
        if not isinstance(constant_suffix, str) or (
            constant_suffix and not ACTOR_NAME_RX.fullmatch(constant_suffix)
        ):
            raise SystemExit(f"{CONFIG}: {bar['id']}: invalid constant_suffix")
        bar_namespace = bar.get("namespace", namespace)
        bar_callback = bar.get("clear_callback", callback)
        if not isinstance(bar_namespace, str) or not ACTOR_NAME_RX.fullmatch(bar_namespace):
            raise SystemExit(f"{CONFIG}: {bar['id']}: invalid namespace")
        if not isinstance(bar_callback, str) or not ACTOR_NAME_RX.fullmatch(bar_callback):
            raise SystemExit(f"{CONFIG}: {bar['id']}: invalid clear_callback")
        folded_id = (bar_namespace.casefold(), bar["id"].casefold())
        if folded_id in seen_ids:
            raise SystemExit(f"{CONFIG}: duplicate bar id {bar['id']!r}")
        seen_ids.add(folded_id)
        constant = bar_namespace.upper() + (
            f"_{constant_suffix.upper()}" if constant_suffix else ""
        )
        if constant.casefold() in seen_constants:
            raise SystemExit(f"{CONFIG}: duplicate generated constant {constant!r}")
        seen_constants.add(constant.casefold())
        callback_key = bar_callback.casefold()
        namespace_key = bar_namespace.casefold()
        previous_namespace = callbacks.get(callback_key)
        if previous_namespace is not None and previous_namespace.casefold() != namespace_key:
            raise SystemExit(
                f"{CONFIG}: clear_callback {bar_callback!r} is used by multiple namespaces"
            )
        callbacks[callback_key] = bar_namespace
        previous_callback = namespace_callbacks.get(namespace_key)
        if previous_callback is not None and previous_callback.casefold() != callback_key:
            raise SystemExit(
                f"{CONFIG}: namespace {bar_namespace!r} uses multiple clear callbacks"
            )
        namespace_callbacks[namespace_key] = bar_callback
        if bar["position"] not in {p[0] for p in POS_BANKS}:
            raise SystemExit(f"{CONFIG}: invalid position {bar['position']!r}")
        priority = bar["priority"]
        if type(priority) is not int or priority < 0:
            raise SystemExit(f"{CONFIG}: {bar['id']}: invalid layer priority")
        capacity = bar["capacity"]
        if type(capacity) is not int or capacity <= 0 or capacity > INT32_MAX:
            raise SystemExit(
                f"{CONFIG}: {bar['id']}: capacity must be an integer in 1..{INT32_MAX}"
            )
        legacy_catalog = bar.get("legacy_catalog", False)
        if not isinstance(legacy_catalog, bool):
            raise SystemExit(f"{CONFIG}: {bar['id']}: legacy_catalog must be boolean")
        for key in ("vertical_full", "vertical_empty", "horizontal_full", "horizontal_empty"):
            image = bar[key]
            if not isinstance(image, str) or not image:
                raise SystemExit(f"{CONFIG}: {bar['id']}: empty {key}")
            if image.casefold() not in known_graphics:
                raise SystemExit(f"{CONFIG}: {bar['id']}: missing image reference {image!r}")
    for bar in bars:
        bar["_namespace"] = bar.get("namespace", namespace)
        bar["_clear_callback"] = bar.get("clear_callback", callback)
        bar["_constant_suffix"] = bar.get("constant_suffix", "").upper()
    return config


def configured_legacy_pairs(config: dict) -> list:
    pairs = []
    for bar in config["bars"]:
        if not bar.get("legacy_catalog", False):
            continue
        pairs.append((bar["vertical_full"], bar["vertical_empty"],
                      bar["horizontal_full"], bar["horizontal_empty"]))
    return pairs


def collect_string_bar_pairs(config: dict) -> list:
    pairs = {}

    def add(vf, ve, hf, he):
        key = (vf, ve, hf, he)
        if all(key) and key not in pairs:
            pairs[key] = None

    acs_files = list((ROOT / "acs_source").rglob("*.acs"))
    call_rx = re.compile(
        r"DrawCustomBarString(?:Layer)?(?:1|2|3|HP|At)?\s*\(\s*"
        r'"([^"]+)"\s*,\s*"([^"]+)"\s*,\s*"([^"]+)"\s*,\s*"([^"]+)"'
    )
    assign_rx = re.compile(r'\bbar_[vh]\s*=\s*"([^"]+)"')

    for path in acs_files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        for m in call_rx.finditer(text):
            add(m.group(1), m.group(2), m.group(3), m.group(4))

        bars = parse_str_array(text, "qwanttypebar")
        vars_ = parse_str_array(text, "qwanttypevar")
        for i, vf in enumerate(bars):
            hf = vars_[i] if i < len(vars_) else vf
            add(vf, "BAREMPTY", hf, "VAREMPTY")

        v_names = assign_rx.findall(text)
        if v_names:
            verts = [n for n in v_names if n.endswith("BAR") or "_V" in n]
            hors = [
                n
                for n in v_names
                if n.endswith("VAR") or "_H" in n or n.endswith("SVAR")
            ]
            if not hors:
                hors = [
                    n.replace("BAR", "VAR") if n.endswith("BAR") else n
                    for n in verts
                ]
            for vf, hf in zip(verts, hors):
                add(vf, "BAREMPTY", hf, "VAREMPTY")

    for pair in configured_legacy_pairs(config):
        add(*pair)
    return sorted(pairs.keys())


def gen_catalog(pairs):
    cap = max(128, len(pairs) + 8)
    acs = [
        "// Generated by tools/_gen_barpos.py — DrawCustomBarString catalog.",
        "// Slot = catalog index (not a BRSLT number). DrawBar uses real names.",
        f"#define UH_BARCAT_MAX {cap}",
        "#define UH_BARCAT_NONE -1",
        "",
        "int uh_barcat_ready = 0;",
        f"int uh_barcat_n = {len(pairs)};",
        "str uh_barcat_full[UH_BARCAT_MAX];",
        "str uh_barcat_empty[UH_BARCAT_MAX];",
        "str uh_barcat_hfull[UH_BARCAT_MAX];",
        "str uh_barcat_hempty[UH_BARCAT_MAX];",
        "int uh_barcat_slot[UH_BARCAT_MAX];",
        "",
        "function void UH_BarCatalogInit(void) {",
        "  if (uh_barcat_ready) {",
        "    return;",
        "  }",
        "  uh_barcat_ready = 1;",
    ]
    for i, (vf, ve, hf, he) in enumerate(pairs):
        acs.append(f'  uh_barcat_full[{i}] = "{vf}";')
        acs.append(f'  uh_barcat_empty[{i}] = "{ve}";')
        acs.append(f'  uh_barcat_hfull[{i}] = "{hf}";')
        acs.append(f'  uh_barcat_hempty[{i}] = "{he}";')
        acs.append(f"  uh_barcat_slot[{i}] = {i};")
    acs += [
        "}",
        "",
        "function int UH_FindBarCatalogSlot(str verticalfull, str verticalempty,",
        "                                   str horizontalfull, str horizontalempty) {",
        "  int i;",
        "  UH_BarCatalogInit();",
        "  for (i = 0; i < uh_barcat_n; i++) {",
        "    if (uh_barcat_full[i] == verticalfull && uh_barcat_empty[i] == verticalempty",
        "        && uh_barcat_hfull[i] == horizontalfull && uh_barcat_hempty[i] == horizontalempty) {",
        "      return uh_barcat_slot[i];",
        "    }",
        "  }",
        "  return UH_BARCAT_NONE;",
        "}",
        "",
    ]
    return "\n".join(acs) + "\n"


def inv_names(pos_key: str, layer: int):
    if layer == 0:
        return f"CustSbarPos{pos_key}Slot", f"CustSbarPos{pos_key}Ammo"
    return (
        f"CustSbarPos{pos_key}L{layer}Slot",
        f"CustSbarPos{pos_key}L{layer}Ammo",
    )


def sbar_layer_line(horiz, slot_inv, ammo_inv, cat_i, fill, empty, x, y):
    orient = "horizontal" if horiz else "vertical"
    lo = cat_i + 1
    hi = cat_i + 2
    # Keep quotes/spacing identical to committed SBARINFO.*.uhappend.
    return (
        f'\t\t\t\tInInventory "{slot_inv}", {lo} {{InInventory not "{slot_inv}", {hi} '
        f'{{DrawBar "{fill}", "{empty}", {ammo_inv}, {orient}, {x}, {y};}}}}'
    )


def strip_main_layer_banks():
    """SBARINFO.h/v._core: remove legacy layer banks block (idempotent)."""
    marker = "\t\t\t//Custom Bar Position Banks (DrawCustomBar1/2/3/HP)"
    results = {}
    for path in (SBAR_H, SBAR_V):
        text = path.read_text(encoding="utf-8")
        if marker not in text:
            results[path] = text
            continue
        start = text.index(marker)
        rest = text[start:]
        m_end = re.search(
            r"\n\t\t\tInInventory BasicArmor,|\n\t\t\t//mugshot",
            rest,
        )
        if not m_end:
            raise SystemExit(f"cannot find end of layer banks in {path}")
        results[path] = text[:start] + rest[m_end.start() + 1:]
    return results


def namespaced_selector(bar: dict) -> str:
    return f"{bar['_namespace']}_P{bar['position']}L{bar['priority']}Selector"


def namespaced_ammo(bar: dict) -> str:
    return f"{bar['_namespace']}_P{bar['position']}L{bar['priority']}_{pascal_id(bar['id'])}Ammo"


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


def gen_namespaced_append_lines(config: dict, horiz: bool) -> list:
    lines = ["\t\t\t\t// Generated namespaced TOML bars"]
    position_order = {pos[0]: index for index, pos in enumerate(POS_BANKS)}
    bars = sorted(
        config["bars"],
        key=lambda b: (b["priority"], position_order[b["position"]],
                       b["_namespace"].casefold(), b["id"].casefold()),
    )
    for bar in bars:
        selector = namespaced_selector(bar)
        ammo = namespaced_ammo(bar)
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
        lines.append(
            f'\t\t\t\tInInventory "{selector}", {selector_id} '
            f'{{InInventory not "{selector}", {selector_id + 1} '
            f'{{DrawBar "{fill}", "{empty}", {ammo}, {orientation}, {x}, {y};}}}}'
        )
    return lines


def gen_append_files(pairs, config):
    def body(horiz: bool) -> list:
        lines = [
            '\tInInventory "DrawStatusBarFlag", 1 {',
            '\t\tInInventory not "NoHud", 1 {',
            '\t\t\tInInventory not "NoHealthBar", 1 {',
        ]
        for pos_key, label, hx, hy, vx, vy in POS_BANKS:
            x, y = (hx, hy) if horiz else (vx, vy)
            for layer in range(UH_BAR_LAYER_MAX):
                slot_inv, ammo_inv = inv_names(pos_key, layer)
                lines.append(f"\t\t\t\t// {label} layer {layer}")
                for cat_i, (vf, ve, hf, he) in enumerate(pairs):
                    fill, empty = (hf, he) if horiz else (vf, ve)
                    lines.append(
                        sbar_layer_line(
                            horiz, slot_inv, ammo_inv, cat_i, fill, empty, x, y
                        )
                    )
        lines += gen_namespaced_append_lines(config, horiz)
        lines += ["\t\t\t}", "\t\t}", "\t}"]
        return lines

    hz = "\n".join(
        ["// Generated by tools/_gen_barpos.py — AppendStatusBar normal",
         "AppendStatusBar normal, forcescaled {",
         *body(True),
         "}", ""]
    )
    vz = "\n".join(
        ["// Generated by tools/_gen_barpos.py — AppendStatusBar fullscreen",
         "AppendStatusBar fullscreen, forcescaled {",
         *body(False),
         "}", ""]
    )
    return hz, vz


def gen_barfx_actors():
    block = ["//$UH — DrawCustomBar1/2/HP position banks / layer pool (amount = slot+1; 0 = off)"]
    seen = set()
    for pos_key, _label, *_rest in POS_BANKS:
        for layer in range(UH_BAR_LAYER_MAX):
            slot_n, ammo_n = inv_names(pos_key, layer)
            if slot_n in seen:
                continue
            seen.add(slot_n)
            block += [
                f"actor {slot_n} : Inventory",
                "{",
                "inventory.amount 1",
                "inventory.maxamount 256",
                "}",
                "",
                f"actor {ammo_n} : Ammo",
                "{",
                "+INVENTORY.IGNORESKILL",
                "inventory.amount 1",
                "inventory.maxamount 1",
                "}",
                "",
            ]
    return "\n".join(block).rstrip() + "\n"


def gen_namespaced_barfx_actors(config: dict) -> str:
    block = ["//$UH — TOML namespaced bar selectors / ammo"]
    seen = set()
    for bar in config["bars"]:
        for actor, parent, extra in (
            (namespaced_selector(bar), "Inventory", [
                "inventory.amount 1",
                f"inventory.maxamount {layer_selector_capacity(config, bar)}"]),
            (namespaced_ammo(bar), "Ammo", [
                "+INVENTORY.IGNORESKILL", "inventory.amount 0",
                f"inventory.maxamount {bar['capacity']}"]),
        ):
            if actor in seen:
                continue
            seen.add(actor)
            block += [f"actor {actor} : {parent}", "{", *extra, "}", ""]
    return "\n".join(block)


def barfx_updated_text(config):
    text = UH_BARFX.read_text(encoding="utf-8")
    m = re.search(r"(?m)^\s*//\s*\$UH — DrawCustomBar1/2/HP position banks.*$", text)
    if not m:
        raise SystemExit("UH_BarFX.dec missing DrawCustomBar marker")
    return text[:m.start()] + gen_barfx_actors() + gen_namespaced_barfx_actors(config)


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
        for index, bar in enumerate(bars, 1):
            lines.append(f"#define {bar_constant(bar)} {index}")
        lines += [
            "",
            f"function void {namespace}_DrawBar(int id, int amount, int capacity) {{",
            "  if (capacity <= 0) { return; }",
            "  if (amount < 0) { amount = 0; }",
            "  if (amount > capacity) { amount = capacity; }",
            "  switch (id) {",
        ]
        for bar in bars:
            selector = namespaced_selector(bar)
            ammo = namespaced_ammo(bar)
            lines += [
                f"    case {bar_constant(bar)}:",
                f'      SetInventory("{selector}", {layer_selector_id(config, bar)});',
                f'      SetAmmoAmountAndCapacity("{ammo}", amount, capacity);',
                "      break;",
            ]
        lines += [
            "    default:",
            "      break;",
            "  }",
            "}",
            "",
        ]

    callbacks = {}
    for bar in config["bars"]:
        callbacks.setdefault(bar["_clear_callback"].casefold(), []).append(bar)
    for bars in callbacks.values():
        callback = bars[0]["_clear_callback"]
        lines.append(f'script "{callback}" (int cam) CLIENTSIDE {{')
        cleared_selectors = set()
        for bar in bars:
            selector = namespaced_selector(bar)
            if selector not in cleared_selectors:
                lines.append(f'  SetActorInventory(cam, "{selector}", 0);')
                cleared_selectors.add(selector)
            lines.append(f'  SetActorInventory(cam, "{namespaced_ammo(bar)}", 0);')
        lines += ["}", "",]
        lines += [
            f'script "{callback}_Register" OPEN CLIENTSIDE {{',
            f'  ACS_NamedExecuteWithResult("core_DrawBar_RegisterClear", "{callback}");',
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
    pairs = collect_string_bar_pairs(config)
    if len(pairs) > 255:
        raise SystemExit(f"catalog too large for inventory amount: {len(pairs)}")
    print(f"string-bar pairs: {len(pairs)}")

    hz, vz = gen_append_files(pairs, config)
    outputs = {
        ACS_CAT: gen_catalog(pairs),
        SBAR_HZ: hz,
        SBAR_VZ: vz,
        UH_BARFX: barfx_updated_text(config),
        GENERATED_ACS: gen_generated_acs(config),
        TEX_BARS: renamed_bars_text(TEX_BARS),
        ANIM_BARS: renamed_bars_text(ANIM_BARS),
        **strip_main_layer_banks(),
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

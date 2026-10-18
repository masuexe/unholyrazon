#!/usr/bin/env python3
"""Generate centered automap sprites/markers from Unholy pickup Spawn artwork.

No external reference package is needed. --check also verifies startup hooks and
all built-in DefineUnholyItem rows. Gameplay state edits remain hand-maintained.
"""
import argparse
import re
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOKEN = re.compile(r'"(?:\\.|[^"\\])*"|//[^\n]*|/\*[\s\S]*?\*/')
BRACE = re.compile(r'"(?:\\.|[^"\\])*"|[{}]')


def strip(text):
    """Blank comments without moving source spans or touching quoted strings."""
    def replace(match):
        if match[0].startswith("/"):
            return "".join("\n" if ch == "\n" else " " for ch in match[0])
        return match[0]
    return TOKEN.sub(replace, text)


def actors(root):
    result = {}
    for path in sorted(Path(root).rglob("*")):
        if path.suffix.lower() not in {".txt", ".dec"}:
            continue
        text = strip(path.read_bytes().decode("utf-8", errors="replace"))
        headers = re.finditer(r"\bactor\s+(\w+)\s*(?::\s*(\w+))?[^{}]*\{", text, re.I)
        for header in headers:
            depth = 1
            for token in BRACE.finditer(text, header.end()):
                if token[0] == "{":
                    depth += 1
                elif token[0] == "}":
                    depth -= 1
                if depth == 0:
                    break
            else:
                raise ValueError(f"Unbalanced actor {header[1]} in {path}")
            result[header[1].lower()] = {
                "name": header[1], "parent": (header[2] or "").lower(),
                "path": str(path), "start": header.end(), "end": token.start(),
                "body": text[header.end():token.start()],
            }
    return result


# Physical pickups outside actors/items. Keep weapons and attack/FX actors out.
EXTRA_ROOTS = {
    "berserkerdieharditem", "dlccentaurweppickupv", "dlccentauroptionpickupb",
    "amberhealthpickup", "sluggercratepickup", "gauntletfoodpickup1",
    "cfakefriedchicken", "tropicalmws_melonpickup2",
}
NATIVE_INVENTORY = {"inventory", "custominventory", "health", "healthpickup", "ammo"}


def derive(actors, key, roots, seen=frozenset()):
    if key in roots:
        return True
    if key not in actors or key in seen:
        return False
    return derive(actors, actors[key]["parent"], roots, seen | {key})


def frame(actor):
    match = re.search(r"(?im)^\s*Spawn\s*:", actor["body"])
    if not match:
        return None
    body = actor["body"][match.end():]
    end = re.search(r"(?im)^\s*(?:Pickup|Use|UseX|Held|Death)\s*:", body)
    if end:
        body = body[:end.start()]
    for match in re.finditer(r"(?im)^\s*([A-Z0-9_]{4})\s+([A-Z\[\]\\]+)\s+-?\d+", body):
        if match[1].upper() != "TNT1":
            return match[1].upper() + match[2][0].upper() + "0"
    return None


def catalog():
    definitions = actors(ROOT / "src/actors")
    owned = {}
    for key, actor in definitions.items():
        in_items = Path(actor["path"]).is_relative_to(ROOT / "src/actors/items")
        if not in_items and not derive(definitions, key, EXTRA_ROOTS):
            continue
        if not derive(definitions, key, NATIVE_INVENTORY):
            continue
        graphic = frame(actor)
        if graphic:
            owned[key] = graphic
    # Include automatic/silent and other inherited pickup variants without
    # adding extra startup actions to their parent Spawn loops.
    supported = {
        key: actor for key, actor in definitions.items()
        if derive(definitions, key, set(owned))
    }
    return definitions, owned, supported


def graphic_sizes():
    sizes = {}
    composites = {}
    for path in sorted((ROOT / "src").rglob("*.png")):
        with path.open("rb") as stream:
            data = stream.read(24)
        if data[:8] == b"\x89PNG\r\n\x1a\n":
            sizes[path.stem.upper()] = struct.unpack(">II", data[16:24])
    for path in sorted((ROOT / "src").glob("TEXTURES*")):
        if path.name == "TEXTURES.automap":
            continue
        text = strip(path.read_text(errors="replace"))
        for match in re.finditer(r'(?im)^\s*(?:sprite|graphic|texture)\s+"?([^",\s]+)"?\s*,\s*(\d+)\s*,\s*(\d+)', text):
            sizes[match[1].upper()] = (int(match[2]), int(match[3]))
            start = text.index("{", match.end())
            depth = 1
            for token in BRACE.finditer(text, start + 1):
                if token[0] == "{":
                    depth += 1
                elif token[0] == "}":
                    depth -= 1
                if depth == 0:
                    break
            body = text[start + 1:token.start()]
            # Reuse patch layers and their translations, not the composite's
            # name: it may be defined after TEXTURES.automap is parsed.
            body = re.sub(r'(?i)\bOffset\s+-?\d+\s*,\s*-?\d+', '', body)
            body = re.sub(r'(?i)\b[XY]Scale\s+[\d.]+', '', body)
            composites[match[1].upper()] = body.strip()
    return sizes, composites


def generate():
    definitions, owned, supported = catalog()
    sizes, composites = graphic_sizes()
    # Rotating world sprites use angle 1 on the map. Some have no angle 0.
    owned = {key: (graphic if graphic in sizes else graphic[:-1] + "1")
             for key, graphic in owned.items()}
    # True Power's original Unbound color cycle is still its world Spawn
    # animation. Derive the map frames and timing from that single source.
    truepower = re.search(r'(?m)^\s*(6N00)\s+([B-Q]+)\s+(\d+)',
                          definitions["truepoweritem"]["body"])
    if not truepower:
        raise ValueError("True Power Spawn animation was not found")
    animation_graphics = {truepower[1] + ch + "0" for ch in truepower[2]}
    graphics = sorted(set(owned.values()) | animation_graphics)
    sprites = {}
    textures = ["// Generated by tools/gen_item_automap.py; do not edit by hand.\n"]
    alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    for i, graphic in enumerate(graphics):
        if graphic not in sizes:
            raise ValueError(f"No local dimensions for pickup sprite {graphic}")
        sprite = "UI" + alphabet[i // 36] + alphabet[i % 36]
        sprites[graphic] = sprite
        width, height = sizes[graphic]
        scale = max(1.0, max(width, height) / 16)
        layers = composites.get(graphic, f"Patch {graphic}, 0, 0")
        textures.append(
            f"sprite {sprite}A0, {width}, {height} {{ Offset {width // 2}, {height // 2} "
            f"XScale {scale:g} YScale {scale:g} {layers} }}\n")
    decorate = ["// Generated by tools/gen_item_automap.py; do not edit by hand.\n"]
    emitted = set()

    def emit(key):
        if key in emitted:
            return
        actor = definitions[key]
        name = actor["name"]
        if key in owned:
            sprite = sprites[owned[key]]
            extra_states = ""
            if key == "truepoweritem":
                for ch in sorted(set(truepower[2])):
                    graphic = sprites[truepower[1] + ch + "0"]
                    extra_states += f"   Frame{ch}:\n    {graphic} A 2\n    Stop\n"
            decorate.append(
                f"actor {name}_MapMarker : UH_ItemMapMarker {{\n"
                f"  States {{\n   Spawn:\n    {sprite} A 2\n    Stop\n{extra_states}  }}\n}}\n")
        else:
            parent = actor["parent"]
            emit(parent)
            decorate.append(f'actor {name}_MapMarker : {definitions[parent]["name"]}_MapMarker {{}}\n')
        emitted.add(key)

    for key in sorted(supported):
        emit(key)
    return definitions, owned, supported, {
        ROOT / "src/TEXTURES.automap": "".join(textures),
        ROOT / "src/actors/items/AutomapMarkers.generated.dec": "".join(decorate),
        ROOT / "src/acs_source/items/item_automap_frames.generated.acs": (
            '// Generated by tools/gen_item_automap.py; do not edit by hand.\n'
            f'#define UH_ITEMMAP_TP_FRAMES "{truepower[2]}"\n'
            f'#define UH_ITEMMAP_TP_TICS {truepower[3]}\n'),
    }


def validate_hooks(definitions, owned, supported):
    errors = []
    for key in owned:
        actor = definitions[key]
        # The hook must run before the original Spawn frames, but its extra
        # frames must not become part of the original sprite loop.
        if not re.search(r'ACS_NamedExecuteWithResult\("uh_ItemAutomapStart"\)', actor["body"]):
            errors.append(f'{actor["name"]}: missing uh_ItemAutomapStart hook')
        if re.search(r'(?i)\bSpawn\s*\+', actor["body"]):
            errors.append(f'{actor["name"]}: Spawn offsets must target UH_ItemSpawn after adding a hook')
    source = (ROOT / "src/acs_source/items/definitions/uh_itemdefs.acs").read_text()
    for name in re.findall(r'DefineUnholyItem\(\d+,\s*"([^"]+)"', source):
        if name.lower() not in supported:
            errors.append(f"Registered item has no marker: {name}")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    definitions, owned, supported, outputs = generate()
    errors = validate_hooks(definitions, owned, supported)
    for path, text in outputs.items():
        if args.check:
            if not path.exists() or path.read_text() != text:
                errors.append(f"Stale generated resource: {path.relative_to(ROOT)}")
        else:
            path.write_text(text)
    for error in errors:
        print(error)
    print(f"{len(owned)} Spawn hooks, {len(supported)} pickup classes, {len(set(owned.values()))} icons")
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())

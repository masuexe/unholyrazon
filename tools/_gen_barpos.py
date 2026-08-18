#!/usr/bin/env python3
"""Generate TEXTURES.barspos, ANIMDEFS.barpos, and SBARINFO position-bank blocks.

TEXTURES.barspos must sort after TEXTURES.bars so Patch sources exist.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "src"
REPO = Path(__file__).resolve().parents[1]
ANIM_SRC = ROOT / "ANIMDEFS.bars"
TEX_OUT = ROOT / "TEXTURES.barspos"  # after TEXTURES.bars alphabetically


def parse_animated_blocks(text: str):
    pattern = re.compile(
        r"^texture\s+(BRSLT|VRSLT)(\d{3})\b[^\n]*\n(.*?)(?=^texture\s|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    blocks = []
    for m in pattern.finditer(text):
        kind, num, body = m.group(1), m.group(2), m.group(3)
        pics = re.findall(r"\bpic\s+(\S+)", body)
        if not pics:
            continue
        blocks.append(
            {
                "kind": kind,
                "num": num,
                "body": body.rstrip() + "\n",
                "pics": pics,
            }
        )
    return blocks


def collect_defined_slots():
    """BRSLT/VRSLT names defined in mod or MM8BDM TEXTURES lumps."""
    names = set()
    paths = [p for p in ROOT.glob("TEXTURES*") if p.is_file()]
    mm = REPO / "ref" / "MM8BDM-v6b"
    if mm.is_dir():
        paths += [p for p in mm.glob("TEXTURES*") if p.is_file()]
    rx = re.compile(
        r'(?i)(?:graphic|texture|sprite)\s+"?(BRSLT|VRSLT|BRSLB|VRSLB)(\d{3})\b'
    )
    for p in paths:
        # Skip our own output (re-run safety)
        if p.name in ("TEXTURES.barpos", "TEXTURES.barspos"):
            continue
        t = p.read_text(encoding="utf-8", errors="ignore")
        for m in rx.finditer(t):
            names.add(m.group(1) + m.group(2))
    return names


def rewrite_body(body: str, mapping: dict) -> str:
    def repl(m):
        name = m.group(1)
        return "pic " + mapping.get(name, name)

    return re.sub(r"\bpic\s+(\S+)", repl, body)


def gen_textures_and_animdefs(blocks, defined):
    v_pics = {}
    h_pics = {}
    wrapper_id = 0

    def wrap_name(i: int) -> str:
        return f"WZ{i:04d}"

    for b in blocks:
        dest = v_pics if b["kind"] == "BRSLT" else h_pics
        for p in b["pics"]:
            if p not in dest:
                dest[p] = wrap_name(wrapper_id)
                wrapper_id += 1

    tex_lines = [
        "// Offset-0 aliases for DrawCustomBar1/2/HP (SBARINFO absolute coords)",
        "// Lump name TEXTURES.barspos loads AFTER TEXTURES.bars (patch sources).",
        "// BZSLT### / VZSLT### patch BRSLT### / VRSLT### when defined; else NOBAR.",
        "// BZSLB### / VZSLB### patch BRSLB### / VRSLB### when defined; else NOBAR.",
        "// Animated slots: ANIMDEFS.barpos uses WZ#### frame wrappers (offset 0).",
        "",
        "// Offset-0 animation frame wrappers",
    ]
    for pic, w in sorted(v_pics.items(), key=lambda x: x[1]):
        tex_lines.append(f"graphic {w}, 8, 56 {{offset 0, 0 patch {pic}, 0, 0}}")
    for pic, w in sorted(h_pics.items(), key=lambda x: x[1]):
        tex_lines.append(f"graphic {w}, 56, 8 {{offset 0, 0 patch {pic}, 0, 0}}")
    tex_lines.append("")
    tex_lines.append("// Position-bank fill aliases (offset 0)")
    defined_n = 0
    fallback_n = 0
    for i in range(256):
        br = f"BRSLT{i:03d}"
        vr = f"VRSLT{i:03d}"
        brb = f"BRSLB{i:03d}"
        vrb = f"VRSLB{i:03d}"
        br_src = br if br in defined else "NOBAR"
        vr_src = vr if vr in defined else "VNOBAR"
        brb_src = brb if brb in defined else "NOBAR"
        vrb_src = vrb if vrb in defined else "VNOBAR"
        if br in defined:
            defined_n += 1
        else:
            fallback_n += 1
        tex_lines.append(
            f"graphic BZSLT{i:03d}, 8, 56 {{offset 0, 0 patch {br_src}, 0, 0}}"
        )
        tex_lines.append(
            f"graphic VZSLT{i:03d}, 56, 8 {{offset 0, 0 patch {vr_src}, 0, 0}}"
        )
        tex_lines.append(
            f"graphic BZSLB{i:03d}, 8, 56 {{offset 0, 0 patch {brb_src}, 0, 0}}"
        )
        tex_lines.append(
            f"graphic VZSLB{i:03d}, 56, 8 {{offset 0, 0 patch {vrb_src}, 0, 0}}"
        )

    TEX_OUT.write_text("\n".join(tex_lines) + "\n", encoding="utf-8")

    # Remove old mis-ordered lump if present
    old = ROOT / "TEXTURES.barpos"
    if old.exists():
        old.unlink()

    anim_lines = [
        "// Offset-0 animations for BZSLT/VZSLT (DrawCustomBar1/2/HP)",
        "",
    ]
    for b in blocks:
        mapping = v_pics if b["kind"] == "BRSLT" else h_pics
        new_kind = "BZSLT" if b["kind"] == "BRSLT" else "VZSLT"
        anim_lines.append(f"texture {new_kind}{b['num']}")
        anim_lines.append(rewrite_body(b["body"], mapping).rstrip())
        anim_lines.append("")

    (ROOT / "ANIMDEFS.barpos").write_text("\n".join(anim_lines) + "\n", encoding="utf-8")
    return len(blocks), len(v_pics), len(h_pics), defined_n, fallback_n


def sbar_line(horiz: bool, slot_inv: str, ammo_inv: str, slot: int, x: int, y: int) -> str:
    """Exclusive InInventory range for slot+1 .. slot+2."""
    fill = f"{'VZSLT' if horiz else 'BZSLT'}{slot:03d}"
    empty = f"{'VZSLB' if horiz else 'BZSLB'}{slot:03d}"
    orient = "horizontal" if horiz else "vertical"
    lo = slot + 1
    hi = slot + 2
    return (
        f'\t\t\tInInventory {slot_inv}, {lo}{{InInventory not {slot_inv}, {hi}'
        f'{{DrawBar "{fill}", "{empty}", {ammo_inv}, {orient}, {x}, {y};}}}}'
    )


def gen_sbarinfo_banks():
    banks = [
        ("Custom Bar Pos1 (bar1)", "CustSbarPos1Slot", "CustSbarPos1Ammo", 58, 184, 16, 8),
        ("Custom Bar Pos2 (bar2)", "CustSbarPos2Slot", "CustSbarPos2Ammo", 58, 176, 8, 8),
        ("Custom Bar PosHP", "CustSbarPosHPSlot", "CustSbarPosHPAmmo", 130, 184, 24, 8),
    ]

    h_block = []
    v_block = []
    for label, slot_inv, ammo_inv, hx, hy, vx, vy in banks:
        h_block.append(f"\t\t\t//{label}")
        v_block.append(f"\t\t\t//{label}")
        for slot in range(256):
            h_block.append(sbar_line(True, slot_inv, ammo_inv, slot, hx, hy))
            v_block.append(sbar_line(False, slot_inv, ammo_inv, slot, vx, vy))

    marker = "\t\t\t//Custom Bar Position Banks (DrawCustomBar1/2/HP)"
    h_insert = marker + "\n" + "\n".join(h_block) + "\n"
    v_insert = marker + "\n" + "\n".join(v_block) + "\n"

    for path, insert in (
        (ROOT / "SBARINFO.H.txt", h_insert),
        (ROOT / "SBARINFO.V.txt", v_insert),
    ):
        text = path.read_text(encoding="utf-8")
        if marker in text:
            start = text.index(marker)
            rest = text[start:]
            m_end = re.search(
                r"\n\t\t\tInInventory BasicArmor,|\n\t\t\t//mugshot",
                rest,
            )
            if not m_end:
                raise SystemExit(f"cannot find end marker in {path}")
            text = text[:start] + rest[m_end.start() + 1 :]

        needle = re.search(
            r'InInventory CustSbarSlotFlag255, 1\{DrawBar "[BV]RSLT255".*?\}\s*\n',
            text,
        )
        if not needle:
            raise SystemExit(f"cannot find CustSbarSlotFlag255 in {path}")
        pos = needle.end()
        text = text[:pos] + "\n" + insert + text[pos:]
        path.write_text(text, encoding="utf-8")
        print(f"updated {path.name}")


def main():
    defined = collect_defined_slots()
    print(f"defined BRSLT/VRSLT names: {len(defined)}")
    blocks = parse_animated_blocks(ANIM_SRC.read_text(encoding="utf-8"))
    n, nv, nh, dn, fn = gen_textures_and_animdefs(blocks, defined)
    print(f"anim blocks={n} v_pics={nv} h_pics={nh}")
    print(f"BZSLT from real BRSLT={dn}, NOBAR fallback={fn}")
    print(f"wrote {TEX_OUT.name}")
    nums = sorted({b["num"] for b in blocks})
    print("animated slots:", ",".join(nums))
    gen_sbarinfo_banks()


if __name__ == "__main__":
    main()

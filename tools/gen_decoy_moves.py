#!/usr/bin/env python3
"""Generate decoy_copy_moves.dec and slim DecoyBot_W/_W2/_W3 Fire states only."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SURV = ROOT / "src/actors/classes/survivors"
SRC_PATH = SURV / "DecoyBot_W.dec"


def rewrite_ends(body: str) -> str:
    return re.sub(r"(?i)\bgoto\s+Ready2\b", "goto MoveReturn", body)


def remap_sprite(body: str, fr: str, to: str) -> str:
    out = body
    for suf in ("50", "58", "30", "36"):
        out = out.replace(f"{fr}{suf}", f"{to}{suf}")
    return out


def extract_labeled_block(text: str, start_label: str, stop_labels: list[str]) -> str:
    m = re.search(rf"(?m)^{re.escape(start_label)}\s*:", text)
    if not m:
        raise ValueError(f"label not found: {start_label}")
    rest = text[m.end() :]
    stop_pat = re.compile(
        r"(?m)^(" + "|".join(re.escape(s) for s in stop_labels) + r")\s*:"
    )
    m2 = stop_pat.search(rest)
    if not m2:
        raise ValueError(f"no stop after {start_label}")
    return text[m.start() : m.end() + m2.start()].rstrip() + "\n"


def actor_chunk(src: str, name: str, nxt: str | None) -> str:
    m = re.search(rf"actor\s+{re.escape(name)}\b", src)
    if not m:
        raise ValueError(name)
    start = m.start()
    if nxt:
        m2 = re.search(rf"actor\s+{re.escape(nxt)}\b", src[m.end() :])
        if not m2:
            raise ValueError(nxt)
        end = m.end() + m2.start()
    else:
        m2 = re.search(r"actor\s+DecoyEnergyAmmo\b", src[m.end() :])
        if not m2:
            raise ValueError("DecoyEnergyAmmo")
        end = m.end() + m2.start()
    return src[start:end]


def states_of(chunk: str) -> str:
    m = re.search(r"States\s*\{", chunk)
    if not m:
        raise ValueError("States missing")
    start = m.end()
    depth = 1
    i = start
    while i < len(chunk) and depth:
        if chunk[i] == "{":
            depth += 1
        elif chunk[i] == "}":
            depth -= 1
        i += 1
    return chunk[start : i - 1]


def extract_fire_slots(states: str) -> dict[int, str]:
    label_re = re.compile(r"(?m)^(Fire\d{2})\s*:")
    matches = list(label_re.finditer(states))
    slots: dict[int, str] = {}
    for i, m in enumerate(matches):
        slot = int(m.group(1)[4:])
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(states)
        slots[slot] = states[start:end]
    return slots


def ensure_bot_helpers(slot_body: str, s1: str, pref: str) -> str:
    refs = set(re.findall(r"\b(Fire\w+)\b", slot_body))
    defined = set(re.findall(r"(?m)^(Fire\w+)\s*:", slot_body))
    missing = sorted(refs - defined)
    # ignore relative/common non-labels
    skip = {"Fire", "FireCustomMissile"}
    extras = []
    all_labs = {m.group(1) for m in re.finditer(r"(?m)^(Fire\w+)\s*:", s1)}
    for lab in missing:
        if lab in skip or not lab.startswith("Fire"):
            continue
        if lab not in all_labs:
            continue
        stops = sorted(all_labs - {lab})
        try:
            block = extract_labeled_block(s1, lab, stops)
        except ValueError:
            continue
        extras.append(remap_sprite(block, "6H", pref).rstrip())
    if extras:
        return slot_body.rstrip() + "\n" + "\n".join(extras) + "\n"
    return slot_body


def slim_actor_fire(chunk: str, which: int) -> str:
    """Replace from Fire: through end of States with ACS-only Fire."""
    spr = "HIJ"[which - 1]
    m = re.search(r"(?m)^Fire:\s*$", chunk)
    if not m:
        raise ValueError("Fire: not found")
    head = chunk[: m.start()]
    # Drop trailing incomplete States close from original — rebuild
    # head should still contain BotFire for W1
    fire = (
        f"Fire:\n"
        f"6{spr}50 A 0 A_JumpIfInventory(\"IsBot\",1,\"BotFire\")\n"
        f"6{spr}50 A 0 A_JumpIf(CallACS(\"uh_DecoyBotCustomFire\",{which}), 2)\n"
        f"6{spr}50 A 0\n"
        f"Goto Ready2\n"
        f"TNT1 A 0 A_WeaponReady\n"
        f"Goto Ready2\n"
        f"\n"
        f"}}\n"
        f"}}\n"
    )
    # If head already has open States, we're replacing Fire..end. Head may end mid-file
    # Remove any trailing whitespace and ensure we don't duplicate closes in head
    # Original head includes everything before Fire: including BotFire — good.
    # But original actor ends with }\n}\n after fires — head doesn't include those.
    return head.rstrip() + "\n" + fire


def main() -> None:
    src = SRC_PATH.read_text(encoding="utf-8")
    w1 = actor_chunk(src, "DecoyBot_W", "DecoyBot_W2")
    w2 = actor_chunk(src, "DecoyBot_W2", "DecoyBot_W3")
    w3 = actor_chunk(src, "DecoyBot_W3", None)
    s1, s2, s3 = states_of(w1), states_of(w2), states_of(w3)
    slots1, slots2, slots3 = extract_fire_slots(s1), extract_fire_slots(s2), extract_fire_slots(s3)
    print("slots", len(slots1), len(slots2), len(slots3))

    parts = [
        "// Vanilla DecoyBot copy slots 0..58 as slotless move-weapons.",
        "// Select branches on uh_DecoyBotGetWhich (1/2/3) for sprite sets.",
        "",
        "actor DecoyCopyMoveBase_W : BaseMM8BDMWep_UH",
        "{",
		'\tweapon.ammotype "DecoyEnergyAmmo"',
		"\tweapon.ammouse 0",
		'\tWeapon.UpSound ""',
		"\t+WEAPON.NOALERT",
		"\t+WEAPON.NOAUTOAIM",
        "States",
        "{",
        "Spawn:",
        "\t6H50 [ 6",
        "\tloop",
		"Deselect:",
		"\tTNT1 AAAAAAAAAAAAAAAAAAAAAA 0 A_Lower",
		"\tTNT1 A 1 A_Lower",
		"\tloop",
		"Select:",
		"\t6H50 A 0",
		"\tgoto Ready",
		"Ready:",
		"Fire:",
		"AltFire:",
		"\t6H50 A 1 A_WeaponReady",
		"\twait",
        "MoveReturn:",
        '\tTNT1 A 0 ACS_NamedExecuteWithResult("uh_ShinyMoveReturn")',
        "\tTNT1 A 0 A_WeaponReady",
        "\tTNT1 A 1 A_WeaponReady",
        "\twait",
        "}",
        "}",
        "",
    ]

    for slot in range(59):
        fl = f"Fire{slot:02d}"
        b1 = slots1[slot]
        b2 = slots2.get(slot) or remap_sprite(b1, "6H", "6I")
        b3 = slots3.get(slot) or remap_sprite(b1, "6H", "6J")
        b1 = ensure_bot_helpers(b1, s1, "6H")
        b2 = ensure_bot_helpers(b2, s1, "6I")
        b3 = ensure_bot_helpers(b3, s1, "6J")

        def prep(body: str, anim: str) -> str:
            body = rewrite_ends(body)
            body = re.sub(rf"(?m)^{re.escape(fl)}\s*:", f"{anim}:", body, count=1)
            body = re.sub(r"(?i)\bgoto\s+BotFire\b", "goto MoveReturn", body)
            # Prefix helper labels so Anim1/2/3 do not collide (FireH08, Fire08End, …).
            labs = sorted(set(re.findall(r"(?m)^(Fire\w+)\s*:", body)), key=len, reverse=True)
            for lab in labs:
                pref = f"{anim}_{lab}"
                body = re.sub(rf"(?m)^{re.escape(lab)}\s*:", f"{pref}:", body)
                body = re.sub(rf'"{re.escape(lab)}"', f'"{pref}"', body)
                body = re.sub(rf"\b{re.escape(lab)}\b", pref, body)
            return body.rstrip()

        parts.append(f"actor DecoyCopy_{slot:02d}_W : DecoyCopyMoveBase_W")
        parts.append("{")
        parts.append("States")
        parts.append("{")
        parts.append("Select:")
        parts.append('\t6H50 A 0 ACS_NamedExecuteWithResult("uh_ShinyMoveColor")')
        parts.append('\t6H50 A 0 A_JumpIf(CallACS("uh_DecoyBotGetWhich") == 2, "Anim2")')
        parts.append('\t6H50 A 0 A_JumpIf(CallACS("uh_DecoyBotGetWhich") == 3, "Anim3")')
        parts.append("\tgoto Anim1")
        parts.append(prep(b1, "Anim1"))
        parts.append(prep(b2, "Anim2"))
        parts.append(prep(b3, "Anim3"))
        parts.append("}")
        parts.append("}")
        parts.append("")

    out_moves = SURV / "decoy_copy_moves.dec"
    out_moves.write_text("\n".join(parts), encoding="utf-8", newline="\n")
    print(f"wrote {out_moves} ({out_moves.stat().st_size} bytes)")

    # Rebuild DecoyBot_W.dec: preamble ScriptBars + slim weapons + tail after W3
    m_ammo = re.search(r"actor\s+DecoyEnergyAmmo\b", src)
    tail = src[m_ammo.start() :]
    preamble = (
        "actor DecoyBot_W_ScriptBar : ScriptBar {}\n"
        "actor DecoyBot_W2_ScriptBar : ScriptBar {}\n"
        "actor DecoyBot_W3_ScriptBar : ScriptBar {}\n\n"
    )
    slim = (
        preamble
        + slim_actor_fire(w1, 1)
        + "\n"
        + slim_actor_fire(w2, 2)
        + "\n"
        + slim_actor_fire(w3, 3)
        + "\n"
        + tail
    )
    SRC_PATH.write_text(slim, encoding="utf-8", newline="\n")
    print(f"wrote {SRC_PATH} ({SRC_PATH.stat().st_size} bytes)")


if __name__ == "__main__":
    main()

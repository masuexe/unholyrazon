#!/usr/bin/env python3
"""Generate decoy_copy_moves.dec as held DecoyCopy_*_W1/W2/W3 weapons.

Reads existing Anim1/2/3 bodies from decoy_copy_moves.dec (or falls back to
parsing if already converted), emits three slot-number weapons per copy, and
slims DecoyBot_W/_W2/_W3 Fire to BotFire-only (no SetWeapon dispatch).
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SURV = ROOT / "src/actors/classes/survivors"
MOVES_PATH = SURV / "decoy_copy_moves.dec"
SRC_PATH = SURV / "DecoyBot_W.dec"

SPR = {1: "6H", 2: "6I", 3: "6J"}
ICON = {1: "C_I_50A", 2: "C_I_50B", 3: "C_I_50C"}
READY_P = {1: "DecoyBot_WepReady1_P", 2: "DecoyBot_WepReady2_P", 3: "DecoyBot_WepReady3_P"}


def extract_anim_blocks(actor_body: str) -> dict[int, str]:
    """Return {1: Anim1 body incl. label, 2: ..., 3: ...} from a DecoyCopy_*_W actor."""
    out: dict[int, str] = {}
    for n in (1, 2, 3):
        lab = f"Anim{n}"
        m = re.search(rf"(?m)^{lab}\s*:", actor_body)
        if not m:
            continue
        rest = actor_body[m.end() :]
        stop = re.search(r"(?m)^(Anim[123]|Fire)\s*:", rest)
        # Also stop at closing States / actor
        end_brace = re.search(r"(?m)^\}\s*$", rest)
        end = len(rest)
        if stop:
            end = min(end, stop.start())
        if end_brace:
            end = min(end, end_brace.start())
        # Include helper labels that belong to this anim (AnimN_*) until next Anim/Fire/}
        block = actor_body[m.start() : m.end() + end]
        # If stop was AnimN+1, block is correct. If helpers after AnimN: until AnimN+1 —
        # re-scan: take from AnimN: until next ^(Anim[123]|Fire): or ^}
        stop2 = re.search(r"(?m)^(Anim[123]|Fire)\s*:", actor_body[m.end() :])
        stop3 = re.search(r"(?m)^\}\s*$", actor_body[m.end() :])
        end2 = len(actor_body) - m.end()
        if stop2:
            end2 = min(end2, stop2.start())
        if stop3:
            end2 = min(end2, stop3.start())
        block = actor_body[m.start() : m.end() + end2]
        out[n] = block.rstrip() + "\n"
    return out


def extract_fire_block(actor_body: str) -> str | None:
    m = re.search(r"(?m)^Fire\s*:", actor_body)
    if not m:
        return None
    rest = actor_body[m.end() :]
    stop = re.search(r"(?m)^(AltFire|Ready|Select|Deselect|BotFire)\s*:", rest)
    end_brace = re.search(r"(?m)^\}\s*$", rest)
    end = len(rest)
    if stop:
        end = min(end, stop.start())
    if end_brace:
        end = min(end, end_brace.start())
    return actor_body[m.start() : m.end() + end].rstrip() + "\n"


def anim_to_fire(body: str, which: int) -> str:
    """Convert AnimN (+ AnimN_* helpers) into Fire (+ Fire* helpers) for held wep."""
    pref = f"Anim{which}_"
    # Strip AnimN_ from helper labels and quoted refs first (longest first)
    labs = sorted(set(re.findall(rf"(?m)^({re.escape(pref)}\w+)\s*:", body)), key=len, reverse=True)
    for lab in labs:
        new = lab[len(pref) :]  # FireH08 etc.
        body = re.sub(rf"(?m)^{re.escape(lab)}\s*:", f"{new}:", body)
        body = re.sub(rf'"{re.escape(lab)}"', f'"{new}"', body)
        body = re.sub(rf"\b{re.escape(lab)}\b", new, body)
    # AnimN: -> Fire: (keep body; prepend IsBot jump after)
    body = re.sub(rf"(?m)^Anim{which}\s*:", "Fire:", body, count=1)
    body = re.sub(rf'"Anim{which}"', '"Fire"', body)
    body = re.sub(rf"\bAnim{which}\b", "Fire", body)
    body = re.sub(r"(?i)\bgoto\s+MoveReturn\b", "goto Ready2", body)
    # Inject IsBot check as first frame after Fire:
    spr = SPR[which]
    inject = f'Fire:\n{spr}50 A 0 A_JumpIfInventory("IsBot",1,"BotFire")\n'
    body = re.sub(r"(?m)^Fire\s*:\s*\n", inject, body, count=1)
    return body.rstrip() + "\n"


def parse_slots_from_moves(text: str) -> dict[int, dict[int, str]]:
    """slot -> {1: fire_body, 2: ..., 3: ...}"""
    slots: dict[int, dict[int, str]] = {}
    # Match both old DecoyCopy_00_W and new DecoyCopy_00_W1
    for m in re.finditer(
        r"(?m)^actor\s+(DecoyCopy_(\d{2})_W(?:[123])?)\b", text
    ):
        name, num = m.group(1), int(m.group(2))
        start = m.start()
        m2 = re.search(r"(?m)^actor\s+", text[m.end() :])
        chunk = text[start : m.end() + m2.start()] if m2 else text[start:]
        which = 0
        if name.endswith("_W1"):
            which = 1
        elif name.endswith("_W2"):
            which = 2
        elif name.endswith("_W3"):
            which = 3
        elif name.endswith("_W"):
            which = 0  # old combined form
        else:
            continue

        if which == 0:
            anims = extract_anim_blocks(chunk)
            if anims:
                slots.setdefault(num, {})
                for n, ab in anims.items():
                    slots[num][n] = anim_to_fire(ab, n)
            continue

        fb = extract_fire_block(chunk)
        if fb:
            slots.setdefault(num, {})
            # Already Fire form — ensure IsBot jump present
            if 'A_JumpIfInventory("IsBot"' not in fb:
                spr = SPR[which]
                fb = re.sub(
                    r"(?m)^Fire\s*:\s*\n",
                    f'Fire:\n{spr}50 A 0 A_JumpIfInventory("IsBot",1,"BotFire")\n',
                    fb,
                    count=1,
                )
            slots[num][which] = fb
    return slots


def held_base(which: int) -> str:
    spr = SPR[which]
    s = spr + "50"
    lines = [
        f"actor DecoyCopyHeldBase_W{which} : BaseMM8BDMWep_UH",
        "{",
        f"\tWeapon.SlotNumber {which}",
        "\tWeapon.AmmoUse 0",
        "\tWeapon.AmmoGive 0",
        '\tweapon.ammotype "DecoyEnergyAmmo"',
        '\tweapon.ammotype2 "FlukyNumberAmmo"',
        f'\tinventory.icon "{ICON[which]}"',
        '\tWeapon.UpSound ""',
        "\t+WEAPON.NOALERT",
        "\t+WEAPON.NOAUTOAIM",
        "States",
        "{",
        "Spawn:",
        f"\t{s} [ 6",
        "\tloop",
        "Deselect:",
        f"\t{s} A 0",
        "\tgoto DeselectSwap",
        "Select:",
        f'\t{s} A 0 A_JumpIfInventory("UH_SilentSelect_F",1,"SilentSelect")',
        "\tgoto SelectSwap",
        "SilentSelect:",
        f"\t{s} A 0 A_StopSound(CHAN_WEAPON)",
        f'\t{s} A 0 A_TakeInventory("UH_SilentSelect_F",1)',
        f'\t{s} A 0 A_TakeInventory("NoWeaponSwitchSound",1)',
        # Apply uses SilentSelect (skips Ready); still need team dye here.
        f'\t{s} A 0 ACS_NamedExecuteWithResult("core_weaponcolor", DECOYBOT_DYE, CLRF_GRAVITYWARN)',
        f"\t{s} A 0 A_WeaponReady(14)",
        "\tgoto Ready2",
        "Ready:",
        f'\t{s} A 0 ACS_NamedExecuteWithResult("core_weaponcolor", DECOYBOT_DYE, CLRF_GRAVITYWARN)',
        f"\t{s} A 0",
        "\tgoto Ready2",
        "Ready2:",
        f'\t{s} A 2 A_GiveInventory("{READY_P[which]}")',
        f'\t{s} A 0 A_GiveInventory("DecoyEnergyAmmo",3)',
        f'\t{s} A 0 A_GiveInventory("FlukyNumberAmmo",1)',
        "\tloop",
        # Unbound lock: play full AltFire anim, then roll on the last frame.
        "AltFire:",
        f'\t{s} D 0 A_JumpIfInventory("FlukyNumberAmmo",100,"AltFireGo")',
        "\tgoto Ready2",
        "AltFireGo:",
        f"\t{s} DDAADD 1 A_RailWait",
        f"\t{s} A 0",
        f"\t{s} AADDA 1",
        f'\t{s} A 1 A_GiveInventory("DecoyBotAlt_P")',
        "\tgoto Ready2",
        "BotFire:",
        '\t"####" A 0 A_JumpIfInventory("DecoyBotFlagBot",30,"BotFire1")',
        '\t"####" A 0 A_Jump(16,"BotFire2")',
        '\t"####" A 0 A_GiveInventory("DecoyBotFlagBot",1)',
        '\t"####" A 0 A_GiveInventory("DecoyEnergyAmmo",random(1,49))',
        "\tgoto Fire+1",
        "BotFire1:",
        '\t"####" A 0 A_Jump(96,"BotFire2")',
        '\t"####" A 0 A_GiveInventory("DecoyEnergyAmmo",random(40,100))',
        "\tgoto Fire+1",
        "BotFire2:",
        '\t"####" A 0 A_TakeInventory("DecoyBotFlagBot",30)',
        '\t"####" A 0 A_GiveInventory("DecoyEnergyAmmo",200)',
        '\t"####" A 0 A_PlaySoundEx("taunt/D_50","Voice")',
        "\tgoto AltFire",
        "Fire:",
        f"\t{s} A 1 A_WeaponReady",
        "\twait",
        "}",
        "}",
        "",
    ]
    return "\n".join(lines)


def slim_parent_fire(chunk: str, which: int) -> str:
    spr = "HIJ"[which - 1]
    m = re.search(r"(?m)^Fire:\s*$", chunk)
    if not m:
        raise ValueError(f"Fire: not found in W{which}")
    head = chunk[: m.start()]
    fire = (
        f"Fire:\n"
        f'6{spr}50 A 0 A_JumpIfInventory("IsBot",1,"BotFire")\n'
        f"6{spr}50 A 0\n"
        f"Goto Ready2\n"
        f"\n"
        f"}}\n"
        f"}}\n"
    )
    return head.rstrip() + "\n" + fire


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


def remap_sprite(body: str, fr: str, to: str) -> str:
    out = body
    for suf in ("50", "58", "30", "36"):
        out = out.replace(f"{fr}{suf}", f"{to}{suf}")
    return out


def main() -> None:
    moves_text = MOVES_PATH.read_text(encoding="utf-8")
    slots = parse_slots_from_moves(moves_text)
    if len(slots) < 59:
        raise SystemExit(f"expected 59 slots, got {len(slots)}")
    print("slots", len(slots), "keys", min(slots), max(slots))

    parts = [
        "// Vanilla DecoyBot copy slots 0..58 as held weapons (slot 1/2/3).",
        "// M2 roll Gives DecoyCopy_NN_W1/_W2/_W3; M1 fires the held weapon directly.",
        "",
        held_base(1),
        held_base(2),
        held_base(3),
    ]

    for slot in range(59):
        if slot not in slots or 1 not in slots[slot]:
            raise SystemExit(f"missing slot {slot} W1 fire")
        b1 = slots[slot][1]
        b2 = slots[slot].get(2) or remap_sprite(b1, "6H", "6I")
        b3 = slots[slot].get(3) or remap_sprite(b1, "6H", "6J")

        for which, body in ((1, b1), (2, b2), (3, b3)):
            parts.append(f"actor DecoyCopy_{slot:02d}_W{which} : DecoyCopyHeldBase_W{which}")
            parts.append("{")
            parts.append("States")
            parts.append("{")
            parts.append(body.rstrip())
            parts.append("}")
            parts.append("}")
            parts.append("")

    MOVES_PATH.write_text("\n".join(parts), encoding="utf-8", newline="\n")
    print(f"wrote {MOVES_PATH} ({MOVES_PATH.stat().st_size} bytes)")

    src = SRC_PATH.read_text(encoding="utf-8")
    w1 = actor_chunk(src, "DecoyBot_W", "DecoyBot_W2")
    w2 = actor_chunk(src, "DecoyBot_W2", "DecoyBot_W3")
    w3 = actor_chunk(src, "DecoyBot_W3", None)
    m_ammo = re.search(r"actor\s+DecoyEnergyAmmo\b", src)
    tail = src[m_ammo.start() :]
    preamble = (
        "actor DecoyBot_W_ScriptBar : ScriptBar {}\n"
        "actor DecoyBot_W2_ScriptBar : ScriptBar {}\n"
        "actor DecoyBot_W3_ScriptBar : ScriptBar {}\n\n"
    )
    slim = (
        preamble
        + slim_parent_fire(w1, 1)
        + "\n"
        + slim_parent_fire(w2, 2)
        + "\n"
        + slim_parent_fire(w3, 3)
        + "\n"
        + tail
    )
    SRC_PATH.write_text(slim, encoding="utf-8", newline="\n")
    print(f"wrote {SRC_PATH} ({SRC_PATH.stat().st_size} bytes)")


if __name__ == "__main__":
    main()

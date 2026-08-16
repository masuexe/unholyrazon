#!/usr/bin/env python3
"""Generate vanilla shiny/decoy move-weapon DECORATE from existing _W files."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SURV = ROOT / "src/actors/classes/survivors"


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def write(p: Path, text: str) -> None:
    p.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {p} ({len(text)} bytes)")


def rewrite_ends(body: str, *, ready: str, fire_end: str | None = None) -> str:
    """Replace ReadyX/Ready2 returns with MoveReturn; keep FireEnd labels local."""
    out = body
    # Case-insensitive Goto/goto ReadyX / Ready2 -> MoveReturn
    out = re.sub(r"(?i)\bgoto\s+ReadyX\b", "goto MoveReturn", out)
    out = re.sub(r"(?i)\bgoto\s+Ready2\b", "goto MoveReturn", out)
    if fire_end:
        # FireEnd / Fire2End / Fire3End stay as local labels; their bodies rewritten separately
        pass
    return out


# ---------------------------------------------------------------------------
# Qwant
# ---------------------------------------------------------------------------

QWANT_MOVES = [
    "BulletSeed",
    "ChargeBeam",
    "DazzlingGleam",
    "FeintAttack",
    "FireBlast",
    "FlameBurst",
    "FreezeDry",
    "IceBeam",
    "Moonblast",
    "NightDaze",
    "RapidSpin",
    "SonicBoom",
    "WaterShuriken",
    "WaterSpout",
    "NeedleArm",
    "FlameWheel",
    "RockSlide",
    "AnchorShot",
    "IceShard",
    "Thunder",
    "NightSlash",
    "DragonBreath",
    "AttackOrder",
    "Toxic",
    "Spikes",
]


def extract_labeled_block(text: str, start_label: str, stop_labels: list[str]) -> str:
    """Extract states from start_label: until a stop label at beginning of line."""
    # Find start
    m = re.search(rf"(?m)^{re.escape(start_label)}\s*:", text)
    if not m:
        raise ValueError(f"label not found: {start_label}")
    start = m.start()
    rest = text[m.end() :]
    stop_pat = re.compile(
        r"(?m)^(" + "|".join(re.escape(s) for s in stop_labels) + r")\s*:"
    )
    m2 = stop_pat.search(rest)
    if not m2:
        # until closing brace of States
        m2 = re.search(r"(?m)^}\s*$", rest)
        if not m2:
            raise ValueError(f"no stop after {start_label}")
    end = m.end() + m2.start()
    return text[start:end].rstrip() + "\n"


def gen_qwant() -> None:
    src = read(SURV / "QwantShiny_W.dec")
    # Pull move bodies: from BulletSeed through Spikes (exclude ThunderWave, FireEnd)
    stops = QWANT_MOVES + ["ThunderWave", "FireEnd", "Flash_Slide", "Altfire", "Fire"]
    bodies: dict[str, str] = {}
    for i, name in enumerate(QWANT_MOVES):
        # stop at next move or ThunderWave/FireEnd
        next_stops = QWANT_MOVES[i + 1 :] + ["ThunderWave", "FireEnd"]
        # RapidSpin includes RapidSpinX, Spin, SpinEnd
        # AnchorShot includes AnchorWait, AnchorEnd
        block = extract_labeled_block(src, name, next_stops)
        # Rename top label to Select body continuation — keep internal labels
        block = rewrite_ends(block, ready="ReadyX")
        bodies[name] = block

    # FireEnd body for shared use inside each weapon that needs it
    fire_end = extract_labeled_block(src, "FireEnd", ["Flash_Slide", "Altfire", "}"])
    fire_end = rewrite_ends(fire_end, ready="ReadyX")
    # FireEnd currently ends with goto MoveReturn from rewrite — good
    # But FireEnd was:
    #   CB 4 / A 8 / goto ReadyX
    # After rewrite: goto MoveReturn. Attach return on MoveReturn shared.

    parts = [
        "// Vanilla QwantShiny AltFire moves as slotless move-weapons.",
        "// Registered via UH_COPYDEFS DefineShinyQwantMoveWep (weight 1 each).",
        "",
        "actor QwantShinyMoveBase_W : BaseMM8BDMWep_UH",
        "{",
		'\tweapon.ammotype "MyDestinyAmmo"',
		"\tweapon.ammouse 0",
		'\tWeapon.UpSound ""',
		"\t+WEAPON.NOALERT",
        "States",
        "{",
        "Spawn:",
        "\t7H01 [ 6",
        "\tloop",
		"Deselect:",
		"\tTNT1 A 0 Offset(1, 128) A_Lower",
		"Select:",
		"\t7H01 A 0",
		"\tgoto Ready",
		"Ready:",
		"Fire:",
		"AltFire:",
		"\t7H01 A 1 A_WeaponReady",
		"\twait",
        "MoveReturn:",
        '\tTNT1 A 0 ACS_NamedExecuteAlways("uh_ShinyMoveReturn_cs", 0)',
        '\tTNT1 A 0 ACS_NamedExecuteWithResult("uh_ShinyMoveReturn")',
        "\tgoto Deselect",
        "FireEnd:",
        "\t7H01 CB 4",
        "\t7H01 A 8",
        "\tgoto MoveReturn",
        "}",
        "}",
        "",
    ]

    for name in QWANT_MOVES:
        body = bodies[name]
        # Change top label Name: -> keep as first states under Select
        # Prepend Select color frame, then the original block with Name: renamed away
        body_inner = re.sub(rf"(?m)^{re.escape(name)}\s*:", "SelectAnim:", body, count=1)
        # Moves that goto FireEnd need local FireEnd from base — inherited OK
        # Moves that goto FireEnd+2: base FireEnd+2 = MoveReturn (CB=0, A8=1, goto not counted... wait)
        # FireEnd states: CB4 (0), A8 (1), next=MoveReturn so +2 = MoveReturn. Good.
        actor = f"QwantShiny_{name}_W"
        parts.append(f"actor {actor} : QwantShinyMoveBase_W")
        parts.append("{")
        parts.append("States")
        parts.append("{")
        parts.append("Select:")
        parts.append('\t7H01 A 0 ACS_NamedExecuteWithResult("uh_ShinyMoveColor")')
        # SetWeapon starts at WEAPONBOTTOM (y=128); snap to WEAPONTOP before anim.
        parts.append("\t7H01 A 0 A_WeaponReady(14)")
        parts.append("\tgoto SelectAnim")
        parts.append(body_inner.rstrip())
        parts.append("}")
        parts.append("}")
        parts.append("")

    write(SURV / "qwant_shiny_moves.dec", "\n".join(parts))

    # Slim QwantShiny_W.dec — keep through Fire, slim AltFire, keep FireEnd for primary Fire
    slim = '''actor QwantShiny_W_ScriptBar : ScriptBar {}

actor QwantShiny_W : BaseMM8BDMWep_UH
{
Weapon.AmmoUse 4
Weapon.AmmoGive 28
Inventory.Pickupmessage "$PU_01"
Obituary "%o learned from %k how to be the very best, that no one ever was."
weapon.ammotype "MyDestinyAmmo"
//Tag "$TAG_S_Qwant_W"
States
{
Spawn:
//WEA4 K 1
7H01 [ 6
loop

Deselect:
7H01 A 0 A_JumpIfInventory("UH_MoveHud_F",1,"DeselectInstant")
goto DeselectSwap
DeselectInstant:
TNT1 A 0 Offset(1, 128) A_Lower
Select:
7H01 A 0 A_JumpIfInventory("UH_SilentSelect_F",1,"SilentSelect")
goto SelectSwap
SilentSelect:
7H01 A 0 ACS_NamedExecuteWithResult("uh_ShinyMoveTake")
7H01 A 0 A_StopSound(CHAN_WEAPON)
7H01 A 0 A_TakeInventory("UH_SilentSelect_F",1)
7H01 A 0 A_TakeInventory("NoWeaponSwitchSound",1)
7H01 A 0 A_TakeInventory("UH_MoveHud_F",5)
7H01 A 0 A_WeaponReady(14)
goto ReadyX

Ready:
7H01 A 0 ACS_NamedExecuteWithResult("core_weaponcolor", QWANT_SDYE, true)
goto ReadyX
ReadyX:
7H01 A 0 A_JumpIfInventory("MyDestinyAmmo",2,"ReadyX2")
7H01 A 10 A_WeaponReady(8)
7H01 A 0 A_GiveInventory("MyDestinyAmmo",1)
loop
ReadyX2:
7H01 A 10 A_WeaponReady
7H01 A 0 A_GiveInventory("MyDestinyAmmo",1)
loop

Fire:
7H01 A 0 A_PlaySound("Pokemon/BallThrow",1)
7H01 A 0 A_GiveInventory("S_QwantRandomBallItem")
goto FireEnd

AltFire:
7H01 A 0 A_TakeInventory("MyDestinyAmmo",2,1)
7H01 A 0 A_TakeInventory("MyDestinyAmmo",2)
7H01 A 0 A_JumpIf(CallACS("uh_QwantShinyMoveRoll"), 2)
7H01 A 0
goto ReadyX
TNT1 A 0
goto DeselectInstant

FireEnd:
7H01 CB 4
7H01 A 8
goto ReadyX

}
}
'''
    write(SURV / "QwantShiny_W.dec", slim)


# ---------------------------------------------------------------------------
# Nega
# ---------------------------------------------------------------------------

NEGA_SLOTS = [
    # slot, stem, L1 label, L2 label, L3 label, extra labels belonging to this slot
    (1, "ThunderBeam", "Negaman1_1", "Negaman1_2", "Negaman1_3", []),
    (2, "TimeStopper", "Negaman2_1", "Negaman2_2", "Negaman2_3", []),
    (3, "SearchSnake", "Negaman3_1", "Negaman3_2", "Negaman3_3", []),
    (4, "Skull", "Negaman4_1", "Negaman4_2", "Negaman4_3",
     ["Negaman4L", "Negaman4L2", "Negaman4L3", "Nega4End"]),
    (5, "GravityHold", "Negaman5_1", "Negaman5_2", "Negaman5_3", []),
    (6, "FlameBlast", "Negaman6_1", "Negaman6_2", "Negaman6_3", []),
    (7, "SlashClaw", "Negaman7_1", "Negaman7_2", "Negaman7_3", []),
    (8, "IceWave", "Negaman8_1", "Negaman8_2", "Negaman8_3", []),
    (9, "BlackHole", "Negaman9_1", "Negaman9_2", "Negaman9_3", []),
    (10, "ChillSpike", "Negaman10_1", "Negaman10_2", "Negaman10_3", []),
    (11, "LightningBolt", "NegamanB_1", "NegamanB_2", "NegamanB_3", []),
    (12, "BalladeCracker", "NegamanK_1", "NegamanK_2", "NegamanK_3",
     ["NegaKHold_1", "NegaKEnd", "NegaKHold_2", "NegaKEnd2"]),
    (13, "GrabBuster", "NegamanV_1", "NegamanV_2", "NegamanV_3", []),
    (14, "TimeSlow", "Negaman1B_1", "Negaman1B_2", "Negaman1B_3", []),
    (15, "BubbleLead", "Negaman2B_1", "Negaman2B_2", "Negaman2B_3", []),
    (16, "NeedleCannon", "Negaman3B_1", "Negaman3B_2", "Negaman3B_3", []),
    (17, "RainFlush", "Negaman4B_1", "Negaman4B_2", "Negaman4B_3", []),
    (18, "NapalmBomb", "Negaman5B_1", "Negaman5B_2", "Negaman5B_3", []),
    (19, "YamatoSpear", "Negaman6B_1", "Negaman6B_2", "Negaman6B_3", []),
    (20, "WildCoil", "Negaman7B_1", "Negaman7B_2", "Negaman7B_3", []),
    (21, "FlashBomb", "Negaman8B_1", "Negaman8B_2", "Negaman8B_3", []),
    (22, "MagmaBazooka", "Negaman9B_1", "Negaman9B_2", "Negaman9B_3", []),
    (23, "TripleBlade", "Negaman10B_1", "Negaman10B_2", "Negaman10B_3", []),
    (24, "IceWall", "NegamanBB_1", "NegamanBB_2", "NegamanBB_3", []),
    (25, "SparkChaser", "NegamanVB_1", "NegamanVB_2", "NegamanVB_3", []),
]


def extract_until_any(text: str, start: str, stops: list[str]) -> str:
    return extract_labeled_block(text, start, stops)


def gen_nega() -> None:
    """Emit held NegaShiny_*_W: Charge on base, Fire1/2/3 per slot; L3 advances cycle."""
    moves = read(SURV / "nega_shiny_moves.dec")
    parent = read(SURV / "NegaManShiny_W.dec")

    def actor_body(text: str, name: str) -> str:
        m = re.search(rf"(?m)^actor\s+{re.escape(name)}\b", text)
        if not m:
            raise ValueError(f"missing actor {name}")
        start = m.start()
        m2 = re.search(r"(?m)^actor\s+", text[m.end() :])
        return text[start : m.end() + m2.start()] if m2 else text[start:]

    def grab_label(chunk: str, label: str, stops: list[str]) -> str:
        return extract_labeled_block(chunk, label, stops)

    # Shared Fire2End / Fire3End from current move base or parent
    fire2_end = (
        "Fire2End:\n"
        "7H02 CB 4\n"
        "7H02 A 6\n"
        "goto Ready2\n"
    )
    fire3_end = (
        "Fire3End:\n"
        "7H02 CBA 3\n"
        'TNT1 A 0 ACS_NamedExecuteWithResult("uh_ShinyNegaAdvanceHeld")\n'
        "goto Ready2\n"
    )

    # Charge / Ready / AltFire / Flash from parent (through Charge2)
    head = parent.split("Fire1:")[0]
    # Strip ScriptBar + actor header props — rebuild HeldBase
    # Pull Flash_Slide + Altfire from parent
    flash_alt = ""
    if "Flash_Slide:" in parent:
        flash_alt = "Flash_Slide:" + parent.split("Flash_Slide:", 1)[1]
        # trim trailing extra closes to single States/actor close handled below
        flash_alt = flash_alt.rstrip()
        while flash_alt.endswith("}"):
            flash_alt = flash_alt[:-1].rstrip()
        flash_alt = flash_alt.rstrip() + "\n"

    held_base = f'''// Vanilla NegaManShiny slots 1..25 as held weapons (slot 1).
// Charge on this base; Fire1/2/3 are the current cycle slot's attacks.
// Full-charge (Fire3End) Give/Takes the next slot via uh_ShinyNegaAdvanceHeld.

actor NegaShinyHeldBase_W : BaseMM8BDMWep_UH
{{
	Weapon.SlotNumber 1
	Weapon.AmmoUse 0
	Weapon.AmmoGive 0
	weapon.ammotype "S_NegaDuckAmmo"
	Weapon.UpSound ""
	inventory.icon "C_I_02B"
	+WEAPON.NOALERT
	+WEAPON.NOAUTOAIM
States
{{
Spawn:
	7H02 [ 6
	loop
Deselect:
	7H02 A 0
	goto DeselectSwap
Select:
	7H02 A 0 A_JumpIfInventory("UH_SilentSelect_F",1,"SilentSelect")
	goto SelectSwap
SilentSelect:
	7H02 A 0 A_StopSound(CHAN_WEAPON)
	7H02 A 0 A_TakeInventory("UH_SilentSelect_F",1)
	7H02 A 0 A_TakeInventory("NoWeaponSwitchSound",1)
	7H02 A 0 ACS_NamedExecuteWithResult("core_weaponcolor", NEGAMAN_SDYE)
	7H02 A 0 A_WeaponReady(14)
	goto Ready2
Ready:
	7H02 A 1 ACS_NamedExecuteWithResult("core_weaponcolor", NEGAMAN_SDYE)
	Goto Ready2
Ready2:
	7H02 A 0 A_JumpIfInventory("S_NegaDuckAmmo",100,"Ready3")
	7H02 A 2 A_WeaponReady(8)
	7H02 A 0 A_GiveInventory("S_NegaDuckAmmo",3)
	loop
Ready3:
	7H02 A 2 A_WeaponReady
	7H02 A 0 A_GiveInventory("S_NegaDuckAmmo",3)
	loop
Fire:
Charge:
	7H02 A 0
	goto Charge0
Charge0:
	7H02 A 0 A_JumpIfInventory("WeaponCharge",25,"Charge1")
	7H02 A 0 A_JumpIfInventory("WeaponCharge",24,"ChargeStart")
	7H02 A 0 A_JumpIfInventory("PlayerPropertyRage",1,"Charge0R")
	7H02 A 1 A_GiveInventory("WeaponCharge",1)
	7H02 A 0 A_Refire("Charge0")
	goto Fire1
ChargeStart:
	7H02 A 0 A_PlaySoundEx("weapon/pcharge","Weapon")
	Goto Charge1
Charge0R:
	7H02 A 1 A_GiveInventory("WeaponCharge",2)
	7H02 A 0 A_Refire("Charge0")
	goto Fire1
Charge1:
	7H02 B 0 A_JumpIfInventory("WeaponCharge",56,"Charge2")
	7H02 B 0 A_JumpIfInventory("PlayerPropertyRage",1,"Charge1R")
	7H02 B 1 A_GiveInventory("WeaponCharge",1)
	7H02 B 0 A_Refire("Charge1")
	goto Fire2
Charge1R:
	7H02 B 1 A_GiveInventory("WeaponCharge",2)
	7H02 B 0 A_Refire("Charge1")
	goto Fire2
Charge2:
	7H02 C 1 A_RailWait
	7H02 C 0 A_Refire("Charge2")
	goto Fire3
Fire1:
	7H02 A 0 A_TakeInventory("WeaponCharge",999)
	7H02 A 0 A_JumpIfInventory("ShieldCheck",1,"Nega4End")
	7H02 A 1 A_WeaponReady
	wait
Fire2:
	7H02 B 0 A_TakeInventory("WeaponCharge",999)
	7H02 B 1 A_WeaponReady
	wait
Fire3:
	7H02 C 0 A_TakeInventory("WeaponCharge",999)
	7H02 C 1 A_WeaponReady
	wait
Nega4End:
	7H02 C 0 A_PlaySoundEx("weapon/skullcounter","Weapon")
	7H02 C 0 A_TakeInventory("ShieldCheck")
	7H02 BA 3
	goto Ready2
Nega4End3:
	7H02 C 0 A_PlaySoundEx("weapon/skullcounter","Weapon")
	7H02 C 0 A_TakeInventory("ShieldCheck")
	7H02 BA 3
	TNT1 A 0 ACS_NamedExecuteWithResult("uh_ShinyNegaAdvanceHeld")
	goto Ready2
{fire2_end.rstrip()}
{fire3_end.rstrip()}
{flash_alt.rstrip()}
}}
}}
'''

    parts = [held_base, ""]

    all_labels = []
    for _slot, _stem, l1, l2, l3, extras in NEGA_SLOTS:
        all_labels.extend([l1, l2, l3] + extras)
    all_labels += ["Fire2End", "Fire3End", "Select", "Ready", "Fire", "AltFire", "MoveReturn", "Nega4End"]

    for slot, stem, l1, l2, l3, extras in NEGA_SLOTS:
        name = f"NegaShiny_{stem}_W"
        chunk = actor_body(moves, name)
        # Idempotent: after first run labels are Fire1/2/3
        src_l1, src_l2, src_l3 = l1, l2, l3
        if re.search(r"(?m)^Fire1\s*:", chunk):
            src_l1, src_l2, src_l3 = "Fire1", "Fire2", "Fire3"
        stops = [s for s in all_labels if s != src_l1] + ["Fire1", "Fire2", "Fire3"]
        b1 = grab_label(chunk, src_l1, [s for s in stops if s != src_l1])
        b2 = grab_label(chunk, src_l2, [s for s in all_labels + ["Fire1", "Fire2", "Fire3"] if s != src_l2])
        b3 = grab_label(chunk, src_l3, [s for s in all_labels + ["Fire1", "Fire2", "Fire3"] if s != src_l3])

        helper_blocks = []
        for h in extras:
            if h == "Nega4End":
                continue  # on HeldBase
            stops_h = [s for s in all_labels if s != h]
            try:
                helper_blocks.append(grab_label(chunk, h, stops_h))
            except ValueError:
                pass

        def to_ready(body: str) -> str:
            body = re.sub(r"(?i)\bgoto\s+MoveReturn\b", "goto Ready2", body)
            body = re.sub(
                r'(?m)^.*A_GiveInventory\("SNegaFlag",\s*1\).*\n?',
                "",
                body,
            )
            return body

        b1 = to_ready(b1)
        b2 = to_ready(b2)
        b3 = to_ready(b3)
        # Skull L3 ends at Nega4End — use advancing end
        if stem == "Skull":
            b3 = re.sub(r"(?i)\bgoto\s+Nega4End\b", "goto Nega4End3", b3)
        # L3 direct MoveReturn already became Ready2 — send to Fire3End/Advance
        # Only if L3 does not already goto Fire3End
        if not re.search(r"(?i)\bgoto\s+Fire3End\b", b3):
            b3 = re.sub(
                r"(?i)\bgoto\s+Ready2\b\s*$",
                "goto Fire3End",
                b3.rstrip() + "\n",
                count=1,
            )

        # Strip SparkChaser custom wrap (Advance ACS handles it)
        if stem == "SparkChaser":
            b3 = re.sub(r'(?m)^.*CallACS\("uh_HasCustomNegaSlots"\).*\n?', "", b3)
            b3 = re.sub(r'(?m)^.*A_TakeInventory\("SNegaFlag",999\).*\n?', "", b3)

        helpers = "\n".join(to_ready(h).rstrip() for h in helper_blocks)
        if stem == "Skull":
            helpers = re.sub(
                r"(?m)^(Negaman4L3:[\s\S]*?)\bgoto\s+Nega4End\b",
                r"\1goto Nega4End3",
                helpers,
                count=1,
                flags=re.IGNORECASE,
            )

        # Ensure Fire1/2/3 labels and one TakeInventory preamble each.
        def as_fire(body: str, old: str, new: str) -> str:
            body = re.sub(rf"(?m)^{re.escape(old)}\s*:", f"{new}:", body, count=1)
            lines = body.split("\n", 4)
            head = "\n".join(lines[:4])
            if new == "Fire1":
                if 'A_TakeInventory("WeaponCharge"' not in head:
                    body = re.sub(
                        r"(?m)^Fire1\s*:\s*\n",
                        "Fire1:\n"
                        '7H02 A 0 A_TakeInventory("WeaponCharge",999)\n'
                        '7H02 A 0 A_JumpIfInventory("ShieldCheck",1,"Nega4End")\n',
                        body,
                        count=1,
                    )
            elif new == "Fire2":
                if 'A_TakeInventory("WeaponCharge"' not in head:
                    body = re.sub(
                        r"(?m)^Fire2\s*:\s*\n",
                        "Fire2:\n"
                        '7H02 B 0 A_TakeInventory("WeaponCharge",999)\n',
                        body,
                        count=1,
                    )
            elif new == "Fire3":
                if 'A_TakeInventory("WeaponCharge"' not in head:
                    body = re.sub(
                        r"(?m)^Fire3\s*:\s*\n",
                        "Fire3:\n"
                        '7H02 C 0 A_TakeInventory("WeaponCharge",999)\n',
                        body,
                        count=1,
                    )
            return body

        b1 = as_fire(b1, src_l1, "Fire1")
        b2 = as_fire(b2, src_l2, "Fire2")
        b3 = as_fire(b3, src_l3, "Fire3")

        parts.append(f"actor {name} : NegaShinyHeldBase_W")
        parts.append("{")
        parts.append("States")
        parts.append("{")
        parts.append(b1.rstrip())
        parts.append(b2.rstrip())
        parts.append(b3.rstrip())
        if helpers.strip():
            parts.append(helpers)
        parts.append("}")
        parts.append("}")
        parts.append("")

    write(SURV / "nega_shiny_moves.dec", "\n".join(parts))

    # Slim parent: buster only (flag 0). L3 advances into slot 1 held wep.
    flash_alt_p = ""
    if "Flash_Slide:" in parent:
        flash_alt_p = "Flash_Slide:" + parent.split("Flash_Slide:", 1)[1]
    head_p = parent.split("Fire1:")[0]
    # Ensure SilentSelect dyes
    if "SilentSelect:" in head_p and "core_weaponcolor" not in head_p.split("SilentSelect:")[1].split("Ready:")[0]:
        head_p = head_p.replace(
            '7H02 A 0 A_TakeInventory("UH_MoveHud_F",5)\n'
            "7H02 A 0 A_WeaponReady(14)",
            '7H02 A 0 A_TakeInventory("UH_MoveHud_F",5)\n'
            '7H02 A 0 ACS_NamedExecuteWithResult("core_weaponcolor", NEGAMAN_SDYE)\n'
            "7H02 A 0 A_WeaponReady(14)",
        )
    slim_fires = '''
Fire1:
7H02 A 0 A_TakeInventory("WeaponCharge",999)
7H02 A 0 A_JumpIfInventory("ShieldCheck",1,"Nega4End")
goto Negaman0_1

Negaman0_1:
7H02 A 0 A_PlaySoundEx("weapon/mbuster","Weapon")
7H02 A 0 A_FireCustomMissile("S_NegaChargeShot1",0,0,8,0)
7H02 BC 2
7H02 A 0 A_Refire("Charge")
Goto Ready2

Fire2:
7H02 B 0 A_TakeInventory("WeaponCharge",999)
goto Negaman0_2

Negaman0_2:
7H02 B 0 A_PlaySoundEx("weapon/pshot","Weapon")
7H02 B 0 A_FireCustomMissile("S_NegaChargeShot2",0,0,8,0)
7H02 BC 3
7H02 A 1
7H02 A 0 A_Refire("Charge")
Goto Ready2

Fire3:
7H02 C 0 A_TakeInventory("WeaponCharge",999)
goto Negaman0_3

Negaman0_3:
7H02 C 0 A_PlaySoundEx("weapon/pshot","Weapon")
7H02 C 0 A_FireCustomMissile("S_NegaChargeShot3",0,0,8,0)
goto Fire3End

Nega4End:
7H02 C 0 A_PlaySoundEx("weapon/skullcounter","Weapon")
7H02 C 0 A_TakeInventory("ShieldCheck")
7H02 BA 3
goto Ready2

Fire2End:
7H02 CB 4
7H02 A 6
Goto Ready2

Fire3End:
7H02 CBA 3
TNT1 A 0 ACS_NamedExecuteWithResult("uh_ShinyNegaAdvanceHeld")
Goto Ready2
'''
    slim = head_p.rstrip() + "\n" + slim_fires.lstrip()
    if flash_alt_p:
        # flash_alt_p includes closing braces
        slim = slim.rstrip() + "\n" + flash_alt_p
        if not slim.rstrip().endswith("}"):
            slim = slim.rstrip() + "\n}\n}\n"
    else:
        slim = slim.rstrip() + "\n}\n}\n"
    write(SURV / "NegaManShiny_W.dec", slim)



# ---------------------------------------------------------------------------
# Decoy
# ---------------------------------------------------------------------------

def split_actor_states(text: str, actor_name: str) -> str:
    m = re.search(rf"actor\s+{re.escape(actor_name)}\b[^{{]*\{{", text)
    if not m:
        raise ValueError(actor_name)
    # find States { ... matching close
    states = re.search(r"States\s*\{", text[m.end() :])
    if not states:
        raise ValueError("States")
    start = m.end() + states.end()
    depth = 1
    i = start
    while i < len(text) and depth:
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
        i += 1
    return text[start : i - 1]


def extract_fire_slots(states: str) -> dict[int, str]:
    """Map slot int -> body text including FireNN: and helpers until next FireMM:."""
    label_re = re.compile(r"(?m)^(Fire\d{2})\s*:")
    matches = list(label_re.finditer(states))
    # Also need to know end — CustomFire / BotFire / Ready2 at actor level / next actor
    slots: dict[int, str] = {}
    for i, m in enumerate(matches):
        name = m.group(1)
        slot = int(name[4:])
        start = m.start()
        if i + 1 < len(matches):
            end = matches[i + 1].start()
        else:
            # until end of states or Deselect/Select/Ready of nothing — rest of fires
            end = len(states)
            # trim at lone labels that aren't Fire helpers
            for stop in ("CustomFire", "Deselect:", "Select:", "Ready:", "Ready2:", "AltFire:", "BotFire:"):
                # only if at beginning after our start and not a Fire* helper
                pass
            # Find next top-level non-Fire helper: look for ^(?!Fire)[A-Za-z].*:
            # Helpers are FireH08, Fire08End, Fire13Bot, etc. — keep until next Fire\d\d:
            end = len(states)
        body = states[start:end]
        slots[slot] = body
    return slots


def remap_sprite(body: str, from_pref: str, to_pref: str) -> str:
    # 6H50 -> 6I50, 6H58 -> 6I58, 6H30 -> 6I30
    out = body
    for a, b in (("50", "50"), ("58", "58"), ("30", "30")):
        out = out.replace(f"{from_pref}{a}", f"{to_pref}{a}")
    return out


def gen_decoy() -> None:
    src = read(SURV / "DecoyBot_W.dec")
    # Extract states for each weapon by slicing actor blocks
    # W1: actor DecoyBot_W ... until actor DecoyBot_W2
    w1 = src.split("actor DecoyBot_W2")[0]
    w2 = "actor DecoyBot_W2" + src.split("actor DecoyBot_W2", 1)[1].split("actor DecoyBot_W3")[0]
    w3 = "actor DecoyBot_W3" + src.split("actor DecoyBot_W3", 1)[1]

    def states_of(chunk: str) -> str:
        m = re.search(r"States\s*\{", chunk)
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

    s1, s2, s3 = states_of(w1), states_of(w2), states_of(w3)
    slots1 = extract_fire_slots(s1)
    slots2 = extract_fire_slots(s2)
    slots3 = extract_fire_slots(s3)

    # Bot helper labels only in W1 — collect full W1 for fallback helpers
    # When W2 body references Fire13Bot etc., ensure those labels exist in Anim1 and
    # for Anim2/3 remap from W1 if missing.

    def ensure_bot_helpers(slot_body: str, slot: int, pref: str) -> str:
        """If body jumps to FireNNBot / FireNNH but label missing, pull from W1."""
        needed = set(re.findall(r'(?:goto|A_ReFire|A_Refire|A_Jump[^"]*")(Fire\d{2}(?:Bot|H\d*|H|A|B|End|Toss|Fail)?)"?', slot_body))
        # simpler: find goto FireXXBot
        refs = set(re.findall(r'\b(Fire\d{2}(?:Bot|H\d*|H|A|B|End|Toss|Fail|Hit)?)\b', slot_body))
        defined = set(re.findall(r'(?m)^(Fire\d{2}(?:Bot|H\d*|H|A|B|End|Toss|Fail|Hit)?)\s*:', slot_body))
        missing = refs - defined - {f"Fire{slot:02d}"}
        extras = []
        for lab in sorted(missing):
            # pull from W1 entire states
            if re.search(rf"(?m)^{re.escape(lab)}\s*:", s1):
                # extract until next Fire-like label
                block = extract_labeled_block(
                    s1,
                    lab,
                    list({m.group(1) for m in re.finditer(r"(?m)^(Fire\w+)\s*:", s1)} - {lab}),
                )
                # pref is like 6I — remap 6H->6I
                block = remap_sprite(block, "6H", pref)
                extras.append(block.rstrip())
        if extras:
            return slot_body.rstrip() + "\n" + "\n".join(extras) + "\n"
        return slot_body

    parts = [
        "// Vanilla DecoyBot copy slots 0..58 as slotless move-weapons.",
        "// Select branches on uh_DecoyBotGetWhich (1/2/3) for sprite sets.",
        "",
        "actor DecoyCopyMoveBase_W : BaseMM8BDMWep_UH",
        "{",
        '\tweapon.ammotype "DecoyEnergyAmmo"',
        "\tweapon.ammouse 0",
        "\t+WEAPON.NOALERT",
        "\t+WEAPON.NOAUTOAIM",
        "States",
        "{",
        "Spawn:",
        "\t6H50 [ 6",
        "\tloop",
        "Deselect:",
        "\tTNT1 A 0 Offset(1, 128) A_Lower",
        "Ready:",
        "Fire:",
        "AltFire:",
        "\t6H50 A 1 A_WeaponReady",
        "\twait",
        "MoveReturn:",
        '\tTNT1 A 0 ACS_NamedExecuteAlways("uh_ShinyMoveReturn_cs", 0)',
        '\tTNT1 A 0 ACS_NamedExecuteWithResult("uh_ShinyMoveReturn")',
        "\tgoto Deselect",
        "}",
        "}",
        "",
    ]

    for slot in range(59):
        b1 = slots1.get(slot, "")
        b2 = slots2.get(slot, "")
        b3 = slots3.get(slot, "")
        if not b1:
            raise SystemExit(f"missing W1 Fire{slot:02d}")
        # If W2/W3 missing, remap from W1
        if not b2:
            b2 = remap_sprite(b1, "6H", "6I")
        if not b3:
            b3 = remap_sprite(b1, "6H", "6J")

        b1 = ensure_bot_helpers(b1, slot, "6H")
        b2 = ensure_bot_helpers(b2, slot, "6I")
        b3 = ensure_bot_helpers(b3, slot, "6J")

        def prep(body: str, anim: str, fire_label: str) -> str:
            body = rewrite_ends(body, ready="Ready2")
            # Rename FireNN: to AnimN:
            body = re.sub(rf"(?m)^{re.escape(fire_label)}\s*:", f"{anim}:", body, count=1)
            # BotFire jumps inside Fire52 — leave as-is (still valid on DecoyBot_W parent? 
            # Move weapon doesn't have BotFire — remap goto BotFire to MoveReturn for safety)
            body = re.sub(r"(?i)\bgoto\s+BotFire\b", "goto MoveReturn", body)
            return body.rstrip()

        fl = f"Fire{slot:02d}"
        a1 = prep(b1, "Anim1", fl)
        a2 = prep(b2, "Anim2", fl)
        a3 = prep(b3, "Anim3", fl)

        actor = f"DecoyCopy_{slot:02d}_W"
        parts.append(f"actor {actor} : DecoyCopyMoveBase_W")
        parts.append("{")
        parts.append("States")
        parts.append("{")
        parts.append("Select:")
        parts.append('\tTNT1 A 0 ACS_NamedExecuteWithResult("uh_ShinyMoveColor")')
        # SetWeapon starts at WEAPONBOTTOM (y=128); snap to WEAPONTOP before Anim.
        parts.append("\tTNT1 A 0 A_WeaponReady(14)")
        # UH_MoveHud_F is synced inventory (3/4/5). CallACS GetWhich is 0 on clients.
        parts.append('\tTNT1 A 0 A_JumpIfInventory("UH_MoveHud_F", 5, "Anim3")')
        parts.append('\tTNT1 A 0 A_JumpIfInventory("UH_MoveHud_F", 4, "Anim2")')
        parts.append("\tgoto Anim1")
        parts.append(a1)
        parts.append(a2)
        parts.append(a3)
        parts.append("}")
        parts.append("}")
        parts.append("")

    write(SURV / "decoy_copy_moves.dec", "\n".join(parts))

    # Slim DecoyBot_W.dec — keep Ready/AltFire/BotFire, replace Fire with ACS only
    # Rebuild from original headers
    def slim_weapon(chunk: str, which: int, actor_line: str) -> str:
        # Keep everything before Fire: jump chain — find "Fire:" that leads to IsBot
        # Actually find line with A_JumpIfInventory("IsBot"
        m = re.search(r"(?m)^Fire:\s*$", chunk)
        if not m:
            # W2 may override Fire
            m = re.search(r"(?m)^Fire:\s*$", chunk)
        if not m:
            raise ValueError("Fire not found")
        head = chunk[: m.start()]
        # Find end of Fire00-58 region: after Fire58Hit or last fire, before closing
        # Keep nothing of fires — replace with ACS dispatch
        # Find AltFire if after fires... AltFire is BEFORE Fire in these weapons
        # Structure: Ready, AltFire, BotFire (W1), Fire jump+fires
        # After fires comes closing braces only for W1; W2 starts new actor

        fire_block = f'''Fire:
6{"HIJ"[which-1]}50 A 0 A_JumpIfInventory("IsBot",1,"BotFire")
6{"HIJ"[which-1]}50 A 0 ACS_NamedExecuteWithResult("uh_DecoyBotCustomFire",{which})
6{"HIJ"[which-1]}50 A 1
Goto Ready2

'''
        # For W2/W3, BotFire is inherited — still need IsBot jump. W2/W3 don't redefine BotFire.
        if which > 1:
            fire_block = f'''Fire:
6{"HIJ"[which-1]}50 A 0 A_JumpIfInventory("IsBot",1,"BotFire")
6{"HIJ"[which-1]}50 A 0 ACS_NamedExecuteWithResult("uh_DecoyBotCustomFire",{which})
6{"HIJ"[which-1]}50 A 1
Goto Ready2

'''
        # Truncate head to before old Fire: and ensure BotFire kept for W1
        # head includes up to but not including Fire:
        # For W1, BotFire is before Fire — good, in head
        # Remove old jump chain if somehow in head — shouldn't be

        # Close actor: head may include partial — find last closing of actor
        # chunk is full actor text including actor line
        # head ends at Fire:; append fire_block and close States+actor
        # Strip any trailing incomplete from head
        out = head.rstrip() + "\n" + fire_block + "}\n}\n"
        return out

    # Rebuild whole file
    w1_full = w1  # includes script bars at top?
    # File starts with ScriptBar actors then DecoyBot_W
    preamble = src.split("actor DecoyBot_W ")[0]
    if not preamble.endswith("\n"):
        preamble += "\n"

    # Get DecoyBot_W actor only
    w1_actor = "actor DecoyBot_W " + w1.split("actor DecoyBot_W ", 1)[1]
    # w1 variable was split before W2 so includes ScriptBars? 
    # Actually w1 = src.split("actor DecoyBot_W2")[0] includes preamble + W1
    w1_only = "actor DecoyBot_W " + src.split("actor DecoyBot_W ", 1)[1].split("actor DecoyBot_W2")[0]

    slim_w1 = slim_weapon(w1_only, 1, "DecoyBot_W")
    slim_w2 = slim_weapon(
        "actor DecoyBot_W2" + src.split("actor DecoyBot_W2", 1)[1].split("actor DecoyBot_W3")[0],
        2,
        "DecoyBot_W2",
    )
    slim_w3 = slim_weapon(
        "actor DecoyBot_W3" + src.split("actor DecoyBot_W3", 1)[1],
        3,
        "DecoyBot_W3",
    )

    # Fix ScriptBar preamble
    out = (
        "actor DecoyBot_W_ScriptBar : ScriptBar {}\n"
        "actor DecoyBot_W2_ScriptBar : ScriptBar {}\n"
        "actor DecoyBot_W3_ScriptBar : ScriptBar {}\n\n"
        + slim_w1
        + "\n"
        + slim_w2
        + "\n"
        + slim_w3
    )
    write(SURV / "DecoyBot_W.dec", out)


def main() -> None:
    gen_qwant()
    gen_nega()
    gen_decoy()
    print("done")


if __name__ == "__main__":
    main()

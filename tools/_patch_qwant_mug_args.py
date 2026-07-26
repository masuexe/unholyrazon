"""Set QwantBar args[2]/[3] from each weapon's core_weaponcolor dye (192/198 targets)."""
from __future__ import annotations

import re
from pathlib import Path

DYE = {
    "QWANT_DYE": (138, 130),
    "Q_NORMAL_DYE": (4, 144),
    "Q_FIRE_DYE": (4, 176),
    "Q_WATER_DYE": (4, 198),
    "Q_ELECTRIC_DYE": (4, 228),
    "Q_GRASS_DYE": (4, 129),
    "Q_ICE_DYE": (4, 196),
    "Q_FIGHTING_DYE": (4, 220),
    "Q_POISON_DYE": (4, 251),
    "Q_GROUND_DYE": (4, 232),
    "Q_FLYING_DYE": (4, 205),
    "Q_PSYCHIC_DYE": (4, 39),
    "Q_BUG_DYE": (4, 139),
    "Q_ROCK_DYE": (4, 166),
    "Q_GHOST_DYE": (4, 60),
    "Q_DRAGON_DYE": (4, 43),
    "Q_DARK_DYE": (4, 95),
    "Q_STEEL_DYE": (4, 152),
    "Q_FAIRY_DYE": (4, 35),
    "Q_ROCKSLIDE_DYE": (232, 234),
    "Q_NIGHTSLASH_DYE": (5, 2),
    "Q_DRAGONBREATH_DYE": (72, 74),
    "Q_SHADOWPUNCH_DYE": (63, 8),
    "Q_TOXIC_DYE": (252, 254),
    "Q_GUST_DYE": (168, 200),
    "Q_SHADOWFORCE_DYE": (3, 5),
}

ROOT = Path(__file__).resolve().parents[1] / "src/actors/classes/survivors/qwant_copyweps"


def main() -> None:
    for fp in sorted(ROOT.glob("*.dec")):
        text = fp.read_text(encoding="utf-8")
        if "_QwantBar" not in text:
            continue
        dyes = re.findall(r'core_weaponcolor\",\s*(\w+)', text)
        dye = dyes[0] if dyes else None
        if dye not in DYE:
            print("SKIP", fp.name, dye)
            continue
        cy, bl = DYE[dye]

        if "ChargeBeamWep_QwantBar" in text:
            new = re.sub(r"args 3, 180\b", f"args 3, 180, {cy}, {bl}", text, count=1)
            fp.write_text(new, encoding="utf-8", newline="\n")
            print("OK", fp.name, dye, cy, bl)
            continue

        def repl(m: re.Match[str]) -> str:
            prefix, argsbody, suffix = m.group(1), m.group(2), m.group(3)
            nums = [int(x.strip()) for x in argsbody.split(",") if x.strip()]
            if len(nums) == 0:
                nums = [0, 0]
            elif len(nums) == 1:
                nums = [nums[0], 0]
            else:
                nums = nums[:2]
            return f"{prefix}{nums[0]}, {nums[1]}, {cy}, {bl}{suffix}"

        new, n = re.subn(
            r"(actor \w+_QwantBar : QwantBar\s*\{\s*args\s+)([^}]+?)(\s*\})",
            repl,
            text,
            count=1,
            flags=re.I,
        )
        if n:
            fp.write_text(new, encoding="utf-8", newline="\n")
            print("OK", fp.name, dye, cy, bl)
        else:
            print("FAIL", fp.name)


if __name__ == "__main__":
    main()

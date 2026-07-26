"""Revert QwantBar args to type[, customMax] only (drop mugshot args[2]/[3])."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "src/actors/classes/survivors/qwant_copyweps"


def main() -> None:
    for fp in sorted(ROOT.glob("*.dec")):
        text = fp.read_text(encoding="utf-8")
        if "_QwantBar" not in text:
            continue

        if "ChargeBeamWep_QwantBar" in text:
            new = re.sub(r"args 3, 180, \d+, \d+", "args 3, 180", text, count=1)
            fp.write_text(new, encoding="utf-8", newline="\n")
            print("OK", fp.name, "chargebeam")
            continue

        def repl(m: re.Match[str]) -> str:
            prefix, argsbody, suffix = m.group(1), m.group(2), m.group(3)
            nums = [int(x.strip()) for x in argsbody.split(",") if x.strip()]
            if len(nums) >= 4:
                # drop mug cyan/blue
                if nums[1] == 0:
                    return f"{prefix}{nums[0]}{suffix}"
                return f"{prefix}{nums[0]}, {nums[1]}{suffix}"
            if len(nums) == 2 and nums[1] == 0:
                return f"{prefix}{nums[0]}{suffix}"
            return m.group(0)

        new, n = re.subn(
            r"(actor \w+_QwantBar : QwantBar\s*\{\s*args\s+)([^}]+?)(\s*\})",
            repl,
            text,
            count=1,
            flags=re.I,
        )
        if n:
            fp.write_text(new, encoding="utf-8", newline="\n")
            print("OK", fp.name)
        else:
            print("SKIP", fp.name)


if __name__ == "__main__":
    main()

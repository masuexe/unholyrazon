from pathlib import Path
import re
text = Path(r"D:\projects\mm8bdm\unholyrazon4\src\acs_source\UH_BOSSDEFS.acs").read_text(encoding="utf-8")
print("lines", len(text.splitlines()))
print("DefineBoss count", text.count("DefineBoss("))
miss = []
for m in re.finditer(r'DefineBoss\((\d+), "([^"]+)",.*?UHBOSS_POOL_\w+, (\d+), (\d+),', text):
    if m.group(3) == "0" and m.group(4) == "0":
        miss.append((m.group(1), m.group(2)))
print("zero hp count", len(miss), miss[:30])
for needle in ("DefineBoss(542", "DefineBoss(603", "DefineBoss(509", "DefineBoss(160"):
    for line in text.splitlines():
        if needle in line:
            print(line[:200])
            break

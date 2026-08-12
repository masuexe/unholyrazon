from pathlib import Path
import re

def extract_brace_array(text, decl):
    """Find `decl={` and return the body inside the outer braces."""
    key = decl + "={"
    start = text.find(key)
    if start < 0:
        # allow whitespace around =
        m = re.search(re.escape(decl) + r"\s*=\s*\{", text)
        if not m:
            raise SystemExit(f"array not found: {decl}")
        i = m.end() - 1  # points at '{'
    else:
        i = start + len(key) - 1  # points at '{'
    depth = 0
    in_str = False
    esc = False
    j = i
    n = len(text)
    while j < n:
        c = text[j]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        else:
            if c == '"':
                in_str = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return text[i + 1 : j]
        j += 1
    raise SystemExit(f"unclosed array: {decl}")

def split_entries(body):
    entries = []
    i = 0
    n = len(body)
    while i < n:
        while i < n and body[i] in " \t\r\n,":
            i += 1
        if i >= n:
            break
        if body.startswith("//", i):
            while i < n and body[i] != "\n":
                i += 1
            continue
        if body.startswith("/*", i):
            end = body.find("*/", i + 2)
            i = n if end < 0 else end + 2
            continue
        if body[i] != "{":
            i += 1
            continue
        depth = 0
        in_str = False
        esc = False
        j = i
        while j < n:
            c = body[j]
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
            else:
                if c == '"':
                    in_str = True
                elif c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        j += 1
                        break
            j += 1
        entries.append(body[i:j])
        i = j
    return entries

def parse_fields(raw):
    inner = raw.strip()
    if inner == "{}":
        return None
    if not (inner.startswith("{") and inner.endswith("}")):
        return None
    inner = inner[1:-1]
    fields = []
    k = 0
    in_str = False
    esc = False
    cur = []
    while k < len(inner):
        c = inner[k]
        if in_str:
            cur.append(c)
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        else:
            if c == '"':
                in_str = True
                cur.append(c)
            elif c == ",":
                fields.append("".join(cur).strip())
                cur = []
            elif c == "/" and k + 1 < len(inner) and inner[k + 1] == "*":
                end = inner.find("*/", k + 2)
                k = len(inner) if end < 0 else end + 1
            else:
                cur.append(c)
        k += 1
    if cur:
        fields.append("".join(cur).strip())
    out = []
    for f in fields:
        f = f.strip()
        # drop trailing comments outside strings already handled
        if f.startswith('"'):
            # may have trailing junk after closing quote
            endq = 1
            esc2 = False
            while endq < len(f):
                c = f[endq]
                if esc2:
                    esc2 = False
                elif c == "\\":
                    esc2 = True
                elif c == '"':
                    break
                endq += 1
            out.append(f[1:endq])
        elif f == "":
            out.append("")
        else:
            # numeric or broken
            out.append(f)
    return out

def rarity_for(id_):
    if id_ >= 500:
        return "UHBOSS_POOL_EX"
    if id_ >= 400:
        return "UHBOSS_POOL_ULTRA"
    if id_ >= 300:
        return "UHBOSS_POOL_SPECIAL"
    if id_ >= 200:
        return "UHBOSS_POOL_SPECIAL"
    if id_ >= 100:
        return "UHBOSS_POOL_RARE"
    return "UHBOSS_POOL_COMMON"

def acs_escape(s):
    # Preserve ACS escapes (\n, \c, …); only quote-escape.
    return s.replace('"', '\\"')

def main():
    src = Path(r"D:\projects\mm8bdm\unholyrazon4\tools\_uh_def_boss_src.acs")
    if not src.exists():
        src = Path(r"D:\projects\mm8bdm\unholyrazon4\src\acs_source\unholy\UH_DEF.acs")
    path = src
    text = path.read_text(encoding="utf-8", errors="replace")
    print("source", path)
    list_body = extract_brace_array(text, "str mainBossList[1000][7]")
    hp_body = extract_brace_array(text, "int mainBossHP[1000][2]")
    list_entries = split_entries(list_body)
    hp_entries = split_entries(hp_body)
    print("list", len(list_entries), "hp", len(hp_entries))

    bosses = {}
    for idx, e in enumerate(list_entries):
        fields = parse_fields(e)
        if not fields or not fields[0]:
            continue
        while len(fields) < 7:
            fields.append("")
        bosses[idx] = {"str": fields[:7]}

    for idx, e in enumerate(hp_entries):
        fields = parse_fields(e)
        if not fields:
            continue
        # {5000, 500} style — not quoted
        inner = e.strip()[1:-1]
        parts = [p.strip() for p in inner.split(",")]
        if len(parts) < 2:
            continue
        try:
            base = int(parts[0])
            add = int(parts[1])
        except ValueError:
            continue
        if base == 0 and add == 0 and idx not in bosses:
            continue
        if idx not in bosses:
            continue
        bosses[idx]["hp"] = (base, add)

    # fill missing hp with 0,0
    for idx in bosses:
        bosses[idx].setdefault("hp", (0, 0))

    out = []
    out.append('#library "UH_BOSSDEFS"')
    out.append('#include "zcommon.acs"')
    out.append('#include "UHADD.acs"')
    out.append("")
    out.append("// Auto-generated from UH_DEF mainBossList/mainBossHP — Phase 2.")
    out.append("// Do not hand-edit rows; regenerate via tools/gen_boss_defs.py")
    out.append("//")
    out.append("// Zandronum: non-CLIENTSIDE OPEN runs on the server only. CLIENTSIDE HUD")
    out.append("// reads local UHDT, so vanilla defs must also register via OPEN CLIENTSIDE.")
    out.append("")
    out.append("function void uh_RegisterVanillaBossDefs(void)")
    out.append("{")

    for idx in sorted(bosses):
        f = bosses[idx]["str"]
        basehp, addhp = bosses[idx]["hp"]
        actor, name, music, credit, instr, spawn_t, spawn_m = f
        rarity = rarity_for(idx)
        ex = ""
        if idx >= 500:
            parent = idx - 500
            if parent in bosses:
                ex = bosses[parent]["str"][0]
        # mugshot empty -> HUD uses UFACE{id} for id>=0
        args = [
            str(idx),
            f'"{acs_escape(actor)}"',
            f'"{acs_escape(name)}"',
            rarity,
            str(basehp),
            str(addhp),
            f'"{acs_escape(ex)}"',
            '""',  # mugshot
            f'"{acs_escape(music)}"',
            f'"{acs_escape(credit)}"',
            f'"{acs_escape(instr)}"',
            f'"{acs_escape(spawn_t)}"',
            f'"{acs_escape(spawn_m)}"',
        ]
        out.append(f"\tDefineBoss({', '.join(args)});")

    out.append("}")
    out.append("")
    out.append('script "uh_define_vanilla_bosses" OPEN')
    out.append("{")
    out.append("\tif (!UHInPlay()) terminate;")
    out.append("\tif (UH_IsBossDefined(0)) terminate;")
    out.append("\tuh_RegisterVanillaBossDefs();")
    out.append("}")
    out.append("")
    out.append('script "uh_define_vanilla_bosses_cs" OPEN CLIENTSIDE')
    out.append("{")
    out.append("\t// Skip UHInPlay: SpawnForced can fail on pure clients.")
    out.append("\tif (UH_IsBossDefined(0)) terminate;")
    out.append("\tuh_RegisterVanillaBossDefs();")
    out.append("}")
    out.append("")

    dest = Path(r"D:\projects\mm8bdm\unholyrazon4\src\acs_source\UH_BOSSDEFS.acs")
    dest.write_text("\n".join(out) + "\n", encoding="utf-8")
    print("wrote", dest, "bosses", len(bosses))
    # sanity
    for idx in [0, 26, 42, 100, 300, 402, 542, 603]:
        b = bosses.get(idx)
        print(idx, b["str"][0] if b else None, b["hp"] if b else None)

if __name__ == "__main__":
    main()

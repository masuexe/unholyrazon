#!/usr/bin/env python3
"""Prove the public addon API contract: docs <-> UHADD <-> handlers <-> mailboxes.

The public extension surface of this mod is a set of documented ACS entry points
in src/acs_source/_includes/mod_api/uhadd.acs and its includes.  Every one of
them stages its str/int arguments in CVARINFO.ipc mailboxes and then executes a
named handler with ACS_NamedExecuteWithResult.  ACC cannot check anything inside
that string literal, so the whole chain is invisible to the compiler.  Each link
has broken an addon in practice, and this checker guards every one of them:

1.  A documented entry point that no public header defines.  An addon author
    copies the doc and gets an ACC undefined-symbol error.
2.  Doc/source arity drift: the doc signature and the UHADD wrapper disagree, so
    the addon compiles against the wrong number of arguments.
3.  A public wrapper with no handler.  The wrapper returns the handler result;
    a missing named script makes the registration silently do nothing.
4.  A handler called with the wrong argument count.  The handler's declared
    parameter count is the real ABI; a mismatch is an ACS VM error at run time.
5.  A mailbox that CVARINFO.ipc does not declare.  SetCVar/SetCVarString return
    0 and do nothing for an unregistered name, and the handler then reads 0
    instead of the argument, so a whole registration batch fails with no usable
    cause.
6.  A mailbox no handler reads: the wrapper stages an argument that is silently
    ignored.
7.  A declared mailbox that no ACS code touches: dead IPC surface that still
    occupies the fixed CVARINFO block.
8.  A documented constant value that disagrees with the #define the addon
    actually compiles against (rarity pools, status codes, flags, mode ids).
9.  A documented capacity that disagrees with the ACS table capacity, e.g. the
    combo registry size or the LMS drop-row capacity.
10. An example that reaches into a repo-internal ACS symbol, or fires an
    internal named script through a string literal, instead of using the public
    API.  Those calls compile because ACC never sees the string.

Inputs are read-only.  --root/--docs-dir/--examples-dir exist so the negative
tests can point at a temporary fixture without touching the tree.

Exit codes: 0 pass, 1 findings, 2 usage error.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PUBLIC_HEADERS = (
    "src/acs_source/_includes/mod_api/uhadd.acs",
    "src/acs_source/_includes/mod_api/uhcombo_api.acs",
    "src/acs_source/_includes/mod_api/uhcombo_defs.acs",
    "src/acs_source/hud/deathtips.acs",
)
# Internal headers that own the table capacities the docs argue about.
CONTRACT_HEADERS = (
    "src/acs_source/_imports/uhdt.acs",
    "src/acs_source/_includes/mod_api/uhcombo_defs.acs",
)
API_DOCS = (
    "docs/boss-api.md",
    "docs/survivor-api.md",
    "docs/bonus-event-api.md",
    "docs/boss-combo-api.md",
    "docs/lms-event-api.md",
    "docs/demoneye-api.md",
    "docs/boss-phase-portraits.md",
)
MODDING_DOCS = (
    "docs/modding/uhdt-identity-crud-contract.md",
    "docs/modding/uhdt-music-row-contract.md",
)
CVARINFO = "src/CVARINFO.ipc"
ACS_ROOT = "src/acs_source"
# The documented DECORATE <-> ACS bridge (named scripts and their selector ids).
DECORATE_BRIDGE = "src/actors/ConstIntList_Uacsprops.dec"
# Include search order used by tools/compile-acs.sh, plus the public hud header
# directory the deathtips recipe documents.
EXAMPLE_INCLUDE_DIRS = (
    "src/acs_source/v6b_overrides/_includes/common",
    "src/acs_source/v6b_overrides/_includes/mod_api",
    "src/acs_source/_includes/mod_api",
    "src/acs_source/_imports",
    "src/acs_source/v6b_overrides/_imports",
    "src/acs_source/unholy",
    "src/acs_source/hud",
)
# Engine builtins that appear as callables inside documentation prose.  These
# are not API names, so they are not required to be defined by this mod.  Only
# add a name here when it is a Zandronum/ACC builtin, never to hide a symbol.
ACC_BUILTINS = frozenset({"Delay", "SetActivator"})
# Prefixes of mod-owned ACS constants (used by the example surface check).
CONST_PREFIXES = ("UH", "BOSSCOMBO_")
ACS_KEYWORDS = frozenset({
    "if", "while", "for", "switch", "return", "script", "function", "else",
    "do", "until", "case", "break", "continue", "restart", "terminate", "str",
    "int", "bool", "void", "fixed",
})

# Capacity claims: (doc, regex with one group, define name, adjustment).
# The claimed number must equal the #define plus the adjustment.  A claim that
# no longer matches its doc text is reported as stale, so rewording the docs
# cannot silently disable the check.
CAPACITY_CLAIMS = (
    ("docs/boss-combo-api.md", r"registry holds (\d+) records",
     "UH_COMBO_CAPACITY", 0),
    ("docs/boss-combo-api.md", r"supports up to (\d+) candidate members",
     "UH_COMBO_MEMBER_CAPACITY", 0),
    ("docs/boss-combo-api.md", r"lineup, from \x601\x60 to \x60(\d+)\x60",
     "UH_COMBO_MAX_BOSSES", 0),
    ("docs/boss-combo-api.md", r"selection weight, from \x600\x60 to \x60(\d+)\x60",
     "UH_COMBO_MAX_WEIGHT", 0),
    ("docs/boss-phase-portraits.md", r"registry holds\s+(\d+) variants",
     "UH_MAX_TEAM_PHASES", 0),
    ("docs/boss-phase-portraits.md",
     r"independently of the (\d+) ordinary presentation rows",
     "UH_MAX_TEAM_PRESENTATION", 0),
    ("docs/lms-event-api.md", r"share a capacity of \x60(\d+)\x60",
     "UH_MAX_LMS_DROPS", 0),
    ("docs/lms-event-api.md", r"coordinated ID within \x600–(\d+)\x60",
     "UH_MAX_LMS_EVENTS", 1),
    ("docs/demoneye-api.md", r"Selection weight \(\x600\.\.(\d+)\x60\)",
     "UHEM_MAX_WEIGHT", 0),
    ("docs/bonus-event-api.md",
     r"Random selection weight \(\x600\.\.(\d+)\x60\)",
     "UHBE_MAX_WEIGHT", 0),
)


# --------------------------------------------------------------------------
# ACS source scanning
# --------------------------------------------------------------------------
def strip_comments(text):
    """Remove ACS line and block comments, keeping string literals intact."""
    out = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == '"':
            out.append(ch)
            i += 1
            while i < n:
                out.append(text[i])
                if text[i] == "\\" and i + 1 < n:
                    out.append(text[i + 1])
                    i += 2
                    continue
                if text[i] == '"':
                    i += 1
                    break
                i += 1
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "/":
            newline = text.find("\n", i)
            i = n if newline < 0 else newline
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "*":
            close = text.find("*/", i)
            i = n if close < 0 else close + 2
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def line_of(text, index):
    return text.count("\n", 0, index) + 1


def balanced(text, index, opening="(", closing=")"):
    """Return the index of the bracket that closes the one at index."""
    depth = 0
    i = index
    while i < len(text):
        if text[i] == opening:
            depth += 1
        elif text[i] == closing:
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise ValueError("unbalanced %r at offset %d" % (opening, index))


def split_args(text):
    """Split an argument list on top-level commas."""
    args = []
    depth = 0
    current = []
    for ch in text:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == "," and depth == 0:
            args.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    tail = "".join(current).strip()
    if tail:
        args.append(tail)
    return args


def param_count(params):
    return 0 if params.strip() in ("", "void") else len(split_args(params))


def parse_functions(text):
    """Return {name: [(arity, body, line)]} for every function definition."""
    functions = {}
    for match in re.finditer(r"\bfunction\s+\w+\s+(\w+)\s*\(", text):
        name = match.group(1)
        close = balanced(text, match.end() - 1)
        body_open = text.find("{", close)
        if body_open < 0:
            continue
        body_close = balanced(text, body_open, "{", "}")
        functions.setdefault(name, []).append(
            (param_count(text[match.end():close]),
             text[body_open:body_close + 1], line_of(text, match.start())))
    return functions


MACRO_RE = re.compile(r"^#(?:lib)?define\s+(\w+)(?:\s+([^\r\n]+))?",
                      re.MULTILINE)


def parse_macros(text):
    """Return {name: [(int value or None, line)]} for object-like macros."""
    macros = {}
    for match in MACRO_RE.finditer(text):
        value = None
        if match.group(2):
            token = match.group(2).strip()
            if re.fullmatch(r"-?(?:0[xX][0-9a-fA-F]+|\d+)", token):
                value = int(token, 0)
        macros.setdefault(match.group(1), []).append(
            (value, line_of(text, match.start())))
    return macros


def parse_scripts(root):
    """Return {script name: [(arity, path, line)]} for every named ACS script."""
    scripts = {}
    for path in sorted((root / ACS_ROOT).rglob("*.acs")):
        text = strip_comments(
            path.read_text(encoding="utf-8", errors="replace"))
        for match in re.finditer(r'\bscript\s+"([^"]+)"\s*\(', text):
            close = balanced(text, match.end() - 1)
            scripts.setdefault(match.group(1), []).append(
                (param_count(text[match.end():close]),
                 str(path.relative_to(root)), line_of(text, match.start())))
    return scripts


CVAR_DECL_RE = re.compile(
    r"^\s*(?:local\s+)?(?:noarchive\s+)?(?:string|int|float|bool)\s+"
    r"(\w+)\s*(?:=|;)", re.MULTILINE)


def parse_cvarinfo(path):
    """Return [(name, line)] for every declared CVARINFO mailbox."""
    text = path.read_text(encoding="utf-8")
    return [(match.group(1), line_of(text, match.start()))
            for match in CVAR_DECL_RE.finditer(text)]


CVAR_GET_RE = re.compile(r'\bGetCVar(?:String)?\s*\(\s*"([^"]+)"')
CVAR_SET_RE = re.compile(r'\bSetCVar(?:String)?\s*\(\s*"([^"]+)"')
NAMED_CALLS = ("ACS_NamedExecuteWithResult", "ACS_NamedExecuteAlways",
               "ACS_NamedExecute")


def named_calls(body):
    """Return [(target script name, argument count)] for literal named calls."""
    calls = []
    for kind in NAMED_CALLS:
        for match in re.finditer(r"\b" + kind + r"\s*\(", body):
            close = balanced(body, match.end() - 1)
            args = split_args(body[match.end():close])
            if args and re.fullmatch(r'"[^"]*"', args[0]):
                calls.append((args[0][1:-1], len(args) - 1))
    return calls


def cvar_reads(text):
    return set(CVAR_GET_RE.findall(text))


def cvar_writes(text):
    return set(CVAR_SET_RE.findall(text))


# --------------------------------------------------------------------------
# Documentation scanning
# --------------------------------------------------------------------------
CODE_BLOCK_RE = re.compile(r"[\x60]{3}[^\n]*\n(.*?)[\x60]{3}", re.S)
FUNCTION_DECL_RE = re.compile(r"\bfunction\s+\w+\s+(\w+)\s*\(")
INLINE_CALL_RE = re.compile(r"\x60([A-Za-z_]\w*)\s*\(([^)\x60]*)\)\x60")
CONST_PAREN_RE = re.compile(
    r"\x60([A-Z][A-Z0-9_]+)\x60\s*\(\s*\x60?(-?\d+)\x60?\s*\)")
TABLE_ROW_RE = re.compile(r"^\|(.+)\|\s*$", re.MULTILINE)
TABLE_NAME_RE = re.compile(r"\x60([A-Z][A-Z0-9_]+)\x60")
TABLE_VALUE_RE = re.compile(r"\x60(-?\d+)\x60")


class Docs:
    def __init__(self):
        self.signatures = {}      # name -> [(arity, doc, line)]
        self.mentions = {}        # name -> [(arity or None, doc, line)]
        self.example_functions = set()
        self.constants = {}       # constant -> set(values)
        self.constant_lines = {}  # constant -> [(doc, line)]


def parse_docs(root, docs, docs_dir=None):
    facts = Docs()
    for doc in docs:
        path = (docs_dir / Path(doc).name) if docs_dir else (root / doc)
        if not path.is_file():
            path = root / doc  # partial fixture override
        text = path.read_text(encoding="utf-8")
        for block in CODE_BLOCK_RE.finditer(text):
            body = block.group(1)
            offset = block.start(1)
            for match in FUNCTION_DECL_RE.finditer(body):
                close = balanced(body, match.end() - 1)
                args = body[match.end():close]
                after = body[close + 1:close + 80].lstrip()
                line = line_of(text, offset + match.start())
                if after.startswith("{"):
                    facts.example_functions.add(match.group(1))
                else:
                    facts.signatures.setdefault(match.group(1), []).append(
                        (param_count(args), doc, line))
        for match in INLINE_CALL_RE.finditer(text):
            name = match.group(1)
            args = match.group(2)
            line = line_of(text, match.start())
            if "..." in args or not args.strip():
                arity = None
            elif args.strip() == "void":
                arity = 0
            else:
                arity = len(split_args(args))
            facts.mentions.setdefault(name, []).append((arity, doc, line))
        for match in CONST_PAREN_RE.finditer(text):
            facts.constants.setdefault(match.group(1), set()).add(
                int(match.group(2)))
            facts.constant_lines.setdefault(match.group(1), []).append(
                (doc, line_of(text, match.start())))
        for match in TABLE_ROW_RE.finditer(text):
            cells = [cell.strip() for cell in match.group(1).split("|")]
            if len(cells) < 2:
                continue
            name = TABLE_NAME_RE.fullmatch(cells[0])
            value = TABLE_VALUE_RE.search(cells[1])
            if name and value:
                facts.constants.setdefault(name.group(1), set()).add(
                    int(value.group(1)))
                facts.constant_lines.setdefault(name.group(1), []).append(
                    (doc, line_of(text, match.start())))
    return facts


# --------------------------------------------------------------------------
# Checks
# --------------------------------------------------------------------------
def load_sources(root):
    return {rel: strip_comments((root / rel).read_text(encoding="utf-8"))
            for rel in PUBLIC_HEADERS}


def public_functions(sources):
    functions = {}
    for rel, text in sources.items():
        for name, rows in parse_functions(text).items():
            for arity, body, line in rows:
                functions.setdefault(name, []).append((arity, body, rel, line))
    return functions


def public_macros(root):
    macros = {}
    for rel in list(PUBLIC_HEADERS) + list(CONTRACT_HEADERS):
        text = strip_comments((root / rel).read_text(encoding="utf-8"))
        for name, rows in parse_macros(text).items():
            for value, line in rows:
                macros.setdefault(name, []).append((value, rel, line))
    return macros


def resolve_handlers(name, functions, depth=3, seen=None):
    """Collect named-call targets reachable from a public function."""
    seen = seen if seen is not None else set()
    if name in seen or depth < 0:
        return []
    seen.add(name)
    targets = []
    for _arity, body, _rel, _line in functions.get(name, []):
        calls = named_calls(body)
        if calls:
            targets.extend(calls)
            continue
        for callee in re.findall(r"\b([A-Za-z_]\w*)\s*\(", body):
            if callee in functions and callee != name:
                targets.extend(
                    resolve_handlers(callee, functions, depth - 1, seen))
    return targets


def check_entry_points(facts, functions, scripts, problems):
    checked = 0
    handler_files = {}
    names = set(facts.signatures) | set(facts.mentions)
    for name in sorted(names):
        if name in facts.example_functions or name in ACC_BUILTINS:
            continue
        checked += 1
        if name not in functions:
            where = (facts.signatures.get(name) or facts.mentions.get(name))[0]
            problems.append(
                "%s:%d documents %s(), but no public header defines it"
                % (where[1], where[2], name))
            continue
        source_arity = functions[name][0][0]
        source_file = functions[name][0][2]
        for arity, doc, line in facts.signatures.get(name, []):
            if arity != source_arity:
                problems.append(
                    "%s:%d signature %s() takes %d argument(s); %s has %d"
                    % (doc, line, name, arity, source_file, source_arity))
        for arity, doc, line in facts.mentions.get(name, []):
            if arity is not None and arity != source_arity:
                problems.append(
                    "%s:%d uses %s() with %d argument(s); %s has %d"
                    % (doc, line, name, arity, source_file, source_arity))
        targets = resolve_handlers(name, functions)
        if not targets:
            problems.append(
                "%s() is a documented public entry point, but it invokes no "
                "handler (no ACS_NamedExecute* target)" % name)
            continue
        for target, nargs in sorted(set(targets)):
            if target not in scripts:
                problems.append(
                    "%s() invokes handler %r, but no ACS source defines that "
                    "named script" % (name, target))
                continue
            arities = {row[0] for row in scripts[target]}
            if nargs not in arities:
                problems.append(
                    "%s() invokes handler %r with %d argument(s); the handler "
                    "declares %s (first at %s:%d)"
                    % (name, target, nargs, sorted(arities),
                       scripts[target][0][1], scripts[target][0][2]))
                continue
            handler_files.setdefault(target, scripts[target][0][1])
    return checked, handler_files


def check_mailboxes(root, sources, problems):
    declared = parse_cvarinfo(root / CVARINFO)
    declared_names = {name for name, _ in declared}
    pipe_text = "\n".join(sources.values())
    public_reads = cvar_reads(pipe_text)
    public_writes = cvar_writes(pipe_text)

    handler_reads = set()
    handler_writes = set()
    public_paths = {str(root / rel) for rel in PUBLIC_HEADERS}
    for path in sorted((root / ACS_ROOT).rglob("*.acs")):
        if str(path) in public_paths:
            continue
        text = strip_comments(
            path.read_text(encoding="utf-8", errors="replace"))
        handler_reads |= cvar_reads(text)
        handler_writes |= cvar_writes(text)

    for name in sorted(public_writes - declared_names):
        problems.append(
            "public header stages mailbox %r, but %s does not declare it "
            "(SetCVar fails silently and the handler reads 0)"
            % (name, CVARINFO))
    for name in sorted(public_reads - declared_names):
        problems.append(
            "public header reads mailbox %r, but %s does not declare it"
            % (name, CVARINFO))
    for name in sorted(public_writes):
        if name in public_reads:
            continue  # an output mailbox the wrapper clears and re-reads
        if name not in handler_reads:
            problems.append(
                "public header writes mailbox %r, but no handler reads it: "
                "the argument is silently ignored" % name)
    for name in sorted(declared_names):
        if not ({name} & (public_reads | public_writes | handler_reads
                          | handler_writes)):
            problems.append(
                "%s declares mailbox %r, but no ACS source reads or writes it"
                % (CVARINFO, name))
    for name in sorted(declared_names):
        if name.endswith("_out_str") and name not in public_reads:
            problems.append(
                "%s declares output mailbox %r, but no public wrapper reads it"
                % (CVARINFO, name))
    return {
        "declared": len(declared_names),
        "staged": len(public_writes),
        "out_boxes": sum(1 for name in declared_names
                         if name.endswith("_out_str")),
    }


def macro_value(macros, name):
    for value, _rel, _line in macros.get(name, []):
        if value is not None:
            return value
    return None


def check_constants(facts, macros, problems):
    checked = 0
    for name in sorted(facts.constants):
        source = macro_value(macros, name)
        if source is None:
            if name.startswith(CONST_PREFIXES):
                doc, line = facts.constant_lines[name][0]
                problems.append(
                    "%s:%d documents constant %s, but no contract header "
                    "defines it" % (doc, line, name))
            continue
        checked += 1
        for value in sorted(facts.constants[name]):
            if value != source:
                doc, line = facts.constant_lines[name][0]
                problems.append(
                    "%s:%d documents %s = %d; the ACS #define is %d"
                    % (doc, line, name, value, source))
    return checked


def check_capacities(root, macros, problems):
    checked = 0
    for doc, pattern, define, adjust in CAPACITY_CLAIMS:
        text = (root / doc).read_text(encoding="utf-8")
        matches = re.findall(pattern, text)
        if not matches:
            problems.append(
                "%s no longer contains the capacity claim %r; update "
                "CAPACITY_CLAIMS in this checker instead of dropping the check"
                % (doc, pattern))
            continue
        declared = macro_value(macros, define)
        if declared is None:
            problems.append(
                "%s is claimed by %s, but no contract header defines it"
                % (define, doc))
            continue
        for claimed in matches:
            checked += 1
            expected = int(claimed) + adjust
            if expected != declared:
                problems.append(
                    "%s documents %d (adjustment %+d -> %d), but %s is %d"
                    % (doc, int(claimed), adjust, expected, define, declared))
    return checked


def check_modding_contracts(root, macros, problems):
    checked = 0
    identity = (root / MODDING_DOCS[0]).read_text(encoding="utf-8")
    order = []
    if "统一返回" in identity:
        tail = identity.split("统一返回", 1)[1]
        line = tail.split("\n", 1)[0]
        order = re.findall(r"\x60(UHDB_\w+)\x60", line)
    if not order:
        problems.append(
            "%s no longer lists the UHDB status codes; update "
            "check_modding_contracts instead of dropping the check"
            % MODDING_DOCS[0])
    else:
        for index, name in enumerate(order):
            checked += 1
            value = macro_value(macros, name)
            if value is None:
                problems.append(
                    "%s lists %s, but no contract header defines it"
                    % (MODDING_DOCS[0], name))
            elif value != index:
                problems.append(
                    "%s lists %s as status code %d; the ACS #define is %d"
                    % (MODDING_DOCS[0], name, index, value))
    music = (root / MODDING_DOCS[1]).read_text(encoding="utf-8")
    bit_claim = re.search(
        r"bit (\d+) 与 bit (\d+)（bit (\d+) 仍是 optional）", music)
    if not bit_claim:
        problems.append(
            "%s no longer documents the music row bit packing; update "
            "check_modding_contracts instead of dropping the check"
            % MODDING_DOCS[1])
    else:
        defined_bit, enabled_bit, optional_bit = (
            int(value) for value in bit_claim.groups())
        for name, bit in (("UHMUS_BIT_OPTIONAL", optional_bit),
                          ("UHMUS_BIT_DEFINED", defined_bit),
                          ("UHMUS_BIT_ENABLED", enabled_bit)):
            checked += 1
            value = macro_value(macros, name)
            if value is None:
                problems.append("%s is documented by %s, but is not defined"
                                % (name, MODDING_DOCS[1]))
            elif value != 1 << bit:
                problems.append(
                    "%s documents bit %d for %s; the ACS #define is %d"
                    % (MODDING_DOCS[1], bit, name, value))
    for name, expected in (("UHMUS_FAIL", -9999), ("UHMUS_OK", 0)):
        checked += 1
        value = macro_value(macros, name)
        if value is None:
            problems.append("%s documents %s, but is not defined"
                            % (MODDING_DOCS[1], name))
        elif value != expected:
            problems.append("%s documents %s = %d; the ACS #define is %d"
                            % (MODDING_DOCS[1], name, expected, value))
    return checked


def include_closure(start, roots):
    """Return (files, missing includes) for an ACS file's include/import tree."""
    pending = [start]
    files = []
    missing = []
    seen = set()
    while pending:
        path = pending.pop()
        if path in seen:
            continue
        seen.add(path)
        files.append(path)
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in re.finditer(r'^\s*#\s*(?:include|import)\s+"([^"]+)"',
                                 text, re.MULTILINE):
            name = match.group(1)
            found = None
            for directory in [path.parent] + roots:
                candidate = Path(directory) / name
                if candidate.is_file():
                    found = candidate
                    break
            if found is None:
                missing.append((path, name))
            else:
                pending.append(found)
    return files, missing


def check_examples(root, examples_dir, public_names, repo_functions, repo_macros,
                   problems):
    corpus = ""
    for doc in API_DOCS + MODDING_DOCS:
        corpus += (root / doc).read_text(encoding="utf-8")
    for rel in PUBLIC_HEADERS:
        corpus += (root / rel).read_text(encoding="utf-8")
    # Public named-script entry points are the names the public headers and the
    # API docs mention, plus every selector the documented DECORATE <-> ACS
    # bridge names (e.g. uh_extralifeplayer and the ELP_* ids).  ACC cannot see
    # names inside ACS_NamedExecute* string literals, so an example firing a
    # script outside this documented corpus is reaching into internals.
    corpus += (root / DECORATE_BRIDGE).read_text(encoding="utf-8",
                                                errors="replace")
    documented_scripts = set(re.findall(r'"([A-Za-z_]\w*)"', corpus))
    documented_scripts |= set(re.findall(r"\b([A-Za-z_]\w+)\b", corpus))
    roots = [str(root / directory) for directory in EXAMPLE_INCLUDE_DIRS]
    checked = 0
    for example in sorted(p for p in examples_dir.iterdir() if p.is_dir()):
        sources = sorted(example.rglob("*.acs"))
        if not sources:
            continue
        checked += 1
        for source in sources:
            try:
                label = source.relative_to(examples_dir.parent).as_posix()
            except ValueError:
                label = str(source)
            closure, missing = include_closure(source, roots)
            for path, name in missing:
                if name == "zcommon.acs":
                    continue
                problems.append(
                    "%s includes %r, which no documented include directory "
                    "provides" % (path, name))
            known_functions = set(public_names)
            known_macros = set()
            for path in closure:
                text = strip_comments(
                    path.read_text(encoding="utf-8", errors="replace"))
                known_functions.update(parse_functions(text))
                known_macros.update(parse_macros(text))
            own_text = strip_comments(
                source.read_text(encoding="utf-8", errors="replace"))
            own_functions = set(parse_functions(own_text))
            own_macros = set(parse_macros(own_text))
            own_scripts = set(re.findall(r'\bscript\s+"([^"]+)"', own_text))
            for match in re.finditer(r"\b([A-Za-z_]\w*)\s*\(", own_text):
                name = match.group(1)
                if name in ACS_KEYWORDS or name in own_functions:
                    continue
                if name in known_functions:
                    continue
                if name in repo_functions:
                    problems.append(
                        "%s calls internal function %s(); it is not declared by "
                        "an included public header" % (label, name))
            for name in re.findall(r"\b([A-Z][A-Z0-9_]+)\b", own_text):
                if not name.startswith(CONST_PREFIXES):
                    continue
                if name in own_macros or name in known_macros:
                    continue
                if name in repo_macros:
                    problems.append(
                        "%s uses internal constant %s; it is not declared by an "
                        "included public header" % (label, name))
            for target, _nargs in named_calls(own_text):
                if target in own_scripts or target in documented_scripts:
                    continue
                problems.append(
                    "%s fires named script %r, which is not documented as a "
                    "public addon entry point (an internal script reached "
                    "through a string literal)" % (label, target))
    return checked


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------
def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Verify the public addon API contract against the docs.",
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT,
                        help="repository root (default: this checkout)")
    parser.add_argument("--docs-dir", type=Path,
                        help="override docs/ for the doc-derived facts "
                             "(negative-test fixture)")
    parser.add_argument("--examples-dir", type=Path,
                        help="override examples/ (negative-test fixture)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="print handler locations outside uhaddr.acs")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    required = [root / rel for rel in
                list(PUBLIC_HEADERS) + list(API_DOCS) + list(MODDING_DOCS)
                + [CVARINFO, DECORATE_BRIDGE]]
    missing = [path for path in required if not path.is_file()]
    if missing:
        for path in missing:
            print("error: missing %s" % path, file=sys.stderr)
        return 2

    sources = load_sources(root)
    functions = public_functions(sources)
    scripts = parse_scripts(root)
    macros = public_macros(root)
    public_names = set(functions)

    repo_functions = set()
    repo_macros = set()
    for path in (root / ACS_ROOT).rglob("*.acs"):
        text = strip_comments(
            path.read_text(encoding="utf-8", errors="replace"))
        repo_functions.update(parse_functions(text))
        repo_macros.update(parse_macros(text))

    facts = parse_docs(root, API_DOCS + MODDING_DOCS, args.docs_dir)
    problems = []
    checked, handler_files = check_entry_points(facts, functions, scripts,
                                                problems)
    mailbox_stats = check_mailboxes(root, sources, problems)
    constants_checked = check_constants(facts, macros, problems)
    capacities_checked = check_capacities(root, macros, problems)
    modding_checked = check_modding_contracts(root, macros, problems)
    examples_dir = (args.examples_dir or (root / "examples")).resolve()
    examples_checked = check_examples(root, examples_dir, public_names,
                                      repo_functions, repo_macros, problems)

    print("documented API entry points checked: %d" % checked)
    print("public headers: %d (%d functions); named handlers resolved: %d"
          % (len(PUBLIC_HEADERS), len(functions), len(handler_files)))
    print("mailboxes: %d declared, %d staged by public headers, %d out-boxes"
          % (mailbox_stats["declared"], mailbox_stats["staged"],
             mailbox_stats["out_boxes"]))
    print("documented constants: %d; capacity claims: %d; "
          "modding-contract constants: %d"
          % (constants_checked, capacities_checked, modding_checked))
    print("examples checked: %d" % examples_checked)
    if args.verbose:
        for target, path in sorted(handler_files.items()):
            if not path.endswith("api_handlers/uhaddr.acs"):
                print("  handler %s lives in %s" % (target, path))

    if problems:
        print("findings: %d" % len(problems))
        for problem in problems:
            print("  FAIL %s" % problem)
        return 1
    print("ok: addon API contract holds "
          "(docs, UHADD, handlers, CVARINFO, examples)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""GitHub-Issue-style CLI tracker for the Unholy Razon Tencent Docs SmartSheet.

Bridges `cEKBFqxnQJoB` (`t00i2h`) with `tools/relay.py` via the official Tencent
Docs MCP HTTP endpoint, without any destructive record/field/view removal tools.
Remote writes default to dry-run preview mode and require explicit `--apply`.
`report` enforces the `AGENTS.md` write-back rule by verifying `.relay/handoff.json`.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import tomllib
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import relay as relay_mod  # noqa: E402

REPO = TOOLS_DIR.parent
DEFAULT_SCHEMA_PATH = TOOLS_DIR / "smartsheet.schema.json"
TZ_UTC8 = timezone(timedelta(hours=8))
SMARTSHEET_REF_PREFIX = "smartsheet:cEKBFqxnQJoB#"


def today_utc8() -> str:
    return datetime.now(TZ_UTC8).strftime("%Y-%m-%d")


def date_to_ms_utc8(date_str: str) -> str:
    """Convert YYYY-MM-DD (UTC+8 midnight) to a millisecond Unix timestamp string."""
    raw = (date_str or "").strip()
    try:
        dt = datetime.strptime(raw, "%Y-%m-%d").replace(tzinfo=TZ_UTC8)
    except ValueError as exc:
        raise ValueError(f"invalid YYYY-MM-DD date: {date_str!r}") from exc
    return str(int(dt.timestamp() * 1000))


def ms_to_date_utc8(ms_value: str | int | None) -> str:
    """Convert a millisecond timestamp string/int to YYYY-MM-DD in UTC+8."""
    if ms_value is None:
        return ""
    raw = str(ms_value).strip()
    if not raw:
        return ""
    try:
        ms = int(float(raw))
    except ValueError:
        return raw
    return datetime.fromtimestamp(ms / 1000.0, tz=TZ_UTC8).strftime("%Y-%m-%d")


def merge_csv_tokens(existing: str, new_tokens: str | list[str] | tuple[str, ...]) -> str:
    """Merge comma-separated tokens preserving order and deduplicating case-insensitively."""
    if isinstance(new_tokens, str):
        incoming = [tok.strip() for tok in new_tokens.split(",") if tok.strip()]
    else:
        incoming = []
        for item in new_tokens:
            for tok in str(item).split(","):
                tok = tok.strip()
                if tok:
                    incoming.append(tok)
    merged: list[str] = []
    seen: set[str] = set()
    for tok in [t.strip() for t in (existing or "").split(",") if t.strip()] + incoming:
        key = tok.lower()
        if key not in seen:
            seen.add(key)
            merged.append(tok)
    return ", ".join(merged)


def load_schema(path: Path = DEFAULT_SCHEMA_PATH) -> dict:
    """Load and validate the local SmartSheet schema definition."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_schema_local(data)
    return data


def validate_schema_local(schema: dict) -> None:
    """Verify internal consistency of smartsheet.schema.json."""
    if not isinstance(schema, dict):
        raise ValueError("schema must be a JSON object")
    for key in ("file_id", "sheet_id", "mcp_url", "fields", "statuses", "views"):
        if not schema.get(key):
            raise ValueError(f"schema missing required key: {key}")

    fields = schema["fields"]
    required_fields = (
        "number", "title", "type", "media", "status", "priority",
        "proposer", "description", "notes", "version", "created_by", "created_at",
    )
    seen_ids: set[str] = set()
    seen_titles: set[str] = set()
    for fkey in required_fields:
        spec = fields.get(fkey)
        if not isinstance(spec, dict) or not spec.get("id") or not spec.get("title") or not spec.get("type"):
            raise ValueError(f"schema field {fkey!r} incomplete")
        if spec["id"] in seen_ids:
            raise ValueError(f"duplicate field id {spec['id']!r}")
        if spec["title"] in seen_titles:
            raise ValueError(f"duplicate field title {spec['title']!r}")
        seen_ids.add(spec["id"])
        seen_titles.add(spec["title"])

    statuses = schema["statuses"]
    open_list = statuses.get("open") or []
    closed_list = statuses.get("closed") or []
    options = statuses.get("options") or {}
    resolutions = statuses.get("close_resolutions") or {}
    if not open_list or not closed_list:
        raise ValueError("statuses.open and statuses.closed must both be non-empty")
    overlap = set(open_list) & set(closed_list)
    if overlap:
        raise ValueError(f"statuses.open and statuses.closed overlap: {sorted(overlap)}")
    declared = set(open_list) | set(closed_list)
    if declared != set(options.keys()):
        raise ValueError(
            f"statuses.options keys {sorted(options.keys())} do not match open+closed {sorted(declared)}"
        )
    for res_key in ("completed", "wontfix"):
        target = resolutions.get(res_key)
        if target not in closed_list:
            raise ValueError(f"close_resolution {res_key!r} -> {target!r} is not in statuses.closed")


def resolve_token() -> str:
    """Resolve the Tencent Docs MCP token from env, ~/.tencent_docs_token, or ~/.codex/config.toml."""
    env_tok = os.environ.get("TENCENT_DOCS_TOKEN", "").strip()
    if env_tok:
        return env_tok
    tok_file = Path.home() / ".tencent_docs_token"
    if tok_file.is_file():
        tok = tok_file.read_text(encoding="utf-8").strip()
        if tok:
            return tok
    codex_cfg = Path.home() / ".codex" / "config.toml"
    if codex_cfg.is_file():
        with codex_cfg.open("rb") as handle:
            parsed = tomllib.load(handle)
        tok = (
            parsed.get("mcp_servers", {})
            .get("tencent-docs", {})
            .get("http_headers", {})
            .get("Authorization", "")
            .strip()
        )
        if tok:
            return tok
    raise SystemExit(
        "tracker: Tencent Docs token not found. Set TENCENT_DOCS_TOKEN, "
        "write ~/.tencent_docs_token, or configure [mcp_servers.tencent-docs.http_headers].Authorization "
        "in ~/.codex/config.toml."
    )


class TencentDocsMCPClient:
    """Minimal read/update client for the Tencent Docs official MCP HTTP endpoint."""

    def __init__(self, url: str, token: str, file_id: str, sheet_id: str, timeout: float = 30.0):
        self.url = url
        self._token = token
        self.file_id = file_id
        self.sheet_id = sheet_id
        self.timeout = timeout
        self._session_id: str | None = None
        self._req_id = 0
        self._initialized = False

    def _post(self, payload: dict, is_notif: bool = False) -> dict | None:
        data = json.dumps(payload).encode("utf-8")
        last_err: Exception | None = None
        for attempt in range(3):
            headers = {
                "Authorization": self._token,
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            }
            if self._session_id:
                headers["Mcp-Session-Id"] = self._session_id
            req = urllib.request.Request(self.url, data=data, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    sid = resp.headers.get("Mcp-Session-Id") or resp.headers.get("mcp-session-id")
                    if sid:
                        self._session_id = sid
                    content_type = resp.headers.get("Content-Type", "")
                    raw = resp.read().decode("utf-8", errors="replace")
                    if is_notif:
                        return None
                    if "text/event-stream" in content_type:
                        msgs = []
                        for line in raw.splitlines():
                            if line.startswith("data:") and line[5:].strip():
                                try:
                                    msgs.append(json.loads(line[5:].strip()))
                                except ValueError:
                                    pass
                        return msgs[-1] if msgs else {}
                    return json.loads(raw) if raw.strip() else {}
            except urllib.error.HTTPError as exc:
                if exc.code < 500:
                    raise RuntimeError(f"Tencent Docs HTTP {exc.code}") from exc
                last_err = exc
            except (urllib.error.URLError, TimeoutError) as exc:
                last_err = exc
            time.sleep(1.5 * (attempt + 1))
        raise RuntimeError(f"Tencent Docs MCP request failed after 3 attempts: {last_err}")

    def _ensure_init(self) -> None:
        if self._initialized:
            return
        self._req_id += 1
        res = self._post({
            "jsonrpc": "2.0",
            "id": self._req_id,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "ur4-tracker", "version": "1.0"},
            },
        })
        if res and "error" in res:
            raise RuntimeError(f"MCP initialize failed: {res['error']}")
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}, is_notif=True)
        self._initialized = True

    def _call(self, tool_name: str, arguments: dict) -> dict:
        self._ensure_init()
        self._req_id += 1
        res = self._post({
            "jsonrpc": "2.0",
            "id": self._req_id,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        })
        if not res:
            raise RuntimeError(f"empty MCP response for {tool_name}")
        if "error" in res:
            raise RuntimeError(f"MCP error on {tool_name}: {res['error']}")
        result = res.get("result") or {}
        texts = [c.get("text", "") for c in result.get("content", []) if c.get("type") == "text"]
        joined = "\n".join(texts)
        if result.get("isError"):
            raise RuntimeError(f"MCP tool error on {tool_name}: {joined}")
        try:
            return json.loads(joined) if joined.strip() else {}
        except ValueError as exc:
            raise RuntimeError(f"unexpected non-JSON response on {tool_name}: {joined[:200]}") from exc

    def list_fields(self) -> list[dict]:
        data = self._call("smartsheet.list_fields", {
            "file_id": self.file_id,
            "sheet_id": self.sheet_id,
            "limit": 100,
        })
        return data.get("fields", [])

    def list_views(self) -> list[dict]:
        data = self._call("smartsheet.list_views", {
            "file_id": self.file_id,
            "sheet_id": self.sheet_id,
        })
        return data.get("views", [])

    def list_records(self) -> list[dict]:
        records: list[dict] = []
        offset = 0
        while True:
            page = self._call("smartsheet.list_records", {
                "file_id": self.file_id,
                "sheet_id": self.sheet_id,
                "limit": 100,
                "offset": offset,
            })
            batch = page.get("records", [])
            records.extend(batch)
            if not page.get("has_more"):
                break
            next_offset = page.get("next", offset + len(batch))
            if next_offset <= offset:
                break
            offset = next_offset
        return records

    def update_records(self, records: list[dict]) -> dict:
        if not records:
            return {"error": ""}
        return self._call("smartsheet.update_records", {
            "file_id": self.file_id,
            "sheet_id": self.sheet_id,
            "records": records,
        })


def normalize_record(raw: dict, schema: dict) -> dict:
    """Flatten a raw SmartSheet record into logical tracker fields."""
    fields_cfg = schema["fields"]
    title_to_key = {spec["title"]: key for key, spec in fields_cfg.items()}
    out = {
        "record_id": raw.get("record_id", ""),
        "number": None,
        "title": "",
        "type": "",
        "media": [],
        "status": "",
        "priority": "",
        "proposer": "",
        "description": "",
        "notes": "",
        "version": "",
    }
    for fv in raw.get("field_values", []):
        lkey = title_to_key.get(fv.get("field"))
        if not lkey:
            continue
        if "auto_number_value" in fv:
            seq = fv["auto_number_value"].get("seq") or fv["auto_number_value"].get("text") or ""
            out[lkey] = int(seq) if str(seq).isdigit() else seq
        elif "text_value" in fv:
            out[lkey] = "".join(it.get("text", "") for it in fv["text_value"].get("items", []))
        elif "option_value" in fv:
            out[lkey] = ", ".join(it.get("text", "") for it in fv["option_value"].get("items", []))
        elif "string_value" in fv:
            out[lkey] = str(fv.get("string_value") or "")
        elif "image_value" in fv:
            out[lkey] = [
                it.get("title") or it.get("image_id") or ""
                for it in fv["image_value"].get("items", [])
            ]
    return out


def resolve_record(records: list[dict], query: str) -> dict:
    """Resolve a normalized record by exact record_id or autoNumber (#4 / 4)."""
    needle = (query or "").strip()
    if not needle:
        raise ValueError("empty record query")
    for rec in records:
        if rec.get("record_id") == needle:
            return rec
    num_str = needle[1:].strip() if needle.startswith("#") else needle
    if num_str.isdigit():
        num_val = int(num_str)
        matches = [rec for rec in records if rec.get("number") == num_val]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise ValueError(f"ambiguous issue number #{num_val}: matched {len(matches)} records")
    raise ValueError(f"record not found: {query!r}")


def build_update_payload(record_id: str, changes: dict[str, object], schema: dict) -> dict:
    """Construct a Tencent Docs smartsheet.update_records record entry."""
    if not record_id:
        raise ValueError("record_id is required")
    fields_cfg = schema["fields"]
    title_to_spec = {spec["title"]: (key, spec) for key, spec in fields_cfg.items()}
    valid_statuses = set(schema["statuses"]["options"].keys())

    field_values = []
    for raw_key, value in changes.items():
        if raw_key in fields_cfg:
            lkey, spec = raw_key, fields_cfg[raw_key]
        elif raw_key in title_to_spec:
            lkey, spec = title_to_spec[raw_key]
        else:
            raise ValueError(f"unknown field: {raw_key!r}")

        ftype = spec["type"]
        ftitle = spec["title"]
        if ftype in ("autoNumber", "image", "createdUser", "createdTime"):
            raise ValueError(f"field {ftitle!r} ({ftype}) is read-only")
        if ftype == "text":
            text_str = "" if value is None else str(value)
            items = [{"text": text_str, "type": "text"}] if text_str != "" else []
            field_values.append({"field": ftitle, "text_value": {"items": items}})
        elif ftype == "singleSelect":
            opt_text = "" if value is None else str(value).strip()
            if lkey == "status" and opt_text not in valid_statuses:
                raise ValueError(f"invalid status {opt_text!r}; expected one of {sorted(valid_statuses)}")
            field_values.append({"field": ftitle, "option_value": {"items": [{"text": opt_text}] if opt_text else []}})
        elif ftype == "dateTime":
            raw_date = "" if value is None else str(value).strip()
            if not raw_date:
                raise ValueError(f"dateTime field {ftitle!r} cannot be empty")
            ms_str = raw_date if raw_date.isdigit() else date_to_ms_utc8(raw_date)
            field_values.append({"field": ftitle, "string_value": ms_str})
        else:
            raise ValueError(f"unsupported field type for update: {ftype}")

    return {"record_id": record_id, "field_values": field_values}


def check_report_guard(relay: relay_mod.Relay, target_status: str,
                       allow_unverified: bool = False) -> tuple[bool, list[str], dict, dict]:
    """Enforce AGENTS.md write-back verification rule using .relay/handoff.json."""
    handoff = relay.read_json(relay.handoff_file) or {}
    current = relay.git_state()
    gate = handoff.get("gate") or {}
    errors: list[str] = []

    if target_status != "待评估" and not allow_unverified:
        if not gate or not gate.get("ok"):
            errors.append(
                "no passing gate recorded in .relay/handoff.json; "
                "run `python3 tools/relay.py verify --gate fast|smoke|full` first"
            )
        if gate and gate.get("git_head") != current.get("head"):
            errors.append(
                f"recorded gate git_head ({gate.get('git_head')}) != current HEAD ({current.get('head')}); "
                "re-run `python3 tools/relay.py verify`"
            )
        if current.get("dirty"):
            errors.append(
                f"working tree has {current.get('dirty_files', 0)} dirty file(s); "
                "commit or clean changes and re-run `python3 tools/relay.py verify`"
            )
    return (len(errors) == 0), errors, gate, current


def _cache_path(state_dir: Path | None) -> Path:
    root = state_dir or (REPO / ".relay")
    return root / "smartsheet_cache.json"


def _save_cache(state_dir: Path | None, schema: dict, raw_records: list[dict],
                normalized: list[dict]) -> None:
    path = _cache_path(state_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": 1,
        "synced_at": datetime.now(TZ_UTC8).isoformat(timespec="seconds"),
        "file_id": schema["file_id"],
        "sheet_id": schema["sheet_id"],
        "count": len(normalized),
        "records": normalized,
        "raw_records": raw_records,
    }
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _load_records(client: TencentDocsMCPClient | None, schema: dict,
                  state_dir: Path | None, offline: bool = False) -> list[dict]:
    if offline:
        cache = _cache_path(state_dir)
        if not cache.is_file():
            raise SystemExit(
                f"tracker: offline cache missing at {cache}; run `python3 tools/tracker.py sync` first"
            )
        data = json.loads(cache.read_text(encoding="utf-8"))
        return data.get("records", [])
    assert client is not None
    raw = client.list_records()
    normalized = [normalize_record(r, schema) for r in raw]
    _save_cache(state_dir, schema, raw, normalized)
    return normalized


def _format_num(num: object) -> str:
    return f"#{num}" if num not in (None, "") else "#-"


def _print_diff(record: dict, changes: dict[str, object], schema: dict) -> None:
    print(f"Dry-run / Planned update for {_format_num(record.get('number'))} ({record.get('record_id')}) - {record.get('title')}:")
    for lkey, new_val in changes.items():
        ftitle = schema["fields"][lkey]["title"] if lkey in schema["fields"] else lkey
        old_val = record.get(lkey, "")
        old_preview = str(old_val).replace("\n", " / ")
        new_preview = str(new_val).replace("\n", " / ")
        if len(old_preview) > 120:
            old_preview = old_preview[:117] + "..."
        if len(new_preview) > 200:
            new_preview = new_preview[:197] + "..."
        print(f"  - {ftitle}:")
        print(f"      before: {old_preview or '<empty>'}")
        print(f"      after : {new_preview or '<empty>'}")


def _build_client(schema: dict) -> TencentDocsMCPClient:
    return TencentDocsMCPClient(
        url=schema["mcp_url"],
        token=resolve_token(),
        file_id=schema["file_id"],
        sheet_id=schema["sheet_id"],
    )


def cmd_sync(args, schema: dict, client: TencentDocsMCPClient | None = None) -> int:
    cli = client or _build_client(schema)
    records = _load_records(cli, schema, args.state_dir, offline=False)
    open_set = set(schema["statuses"]["open"])
    closed_set = set(schema["statuses"]["closed"])
    open_cnt = sum(1 for r in records if r["status"] in open_set)
    closed_cnt = sum(1 for r in records if r["status"] in closed_set)
    other_cnt = len(records) - open_cnt - closed_cnt
    if getattr(args, "json", False):
        print(json.dumps({
            "schema": 1,
            "cache": str(_cache_path(args.state_dir)),
            "total": len(records),
            "open": open_cnt,
            "closed": closed_cnt,
            "other": other_cnt,
        }, indent=2, ensure_ascii=False))
    else:
        print(f"tracker: synced {len(records)} record(s) to {_cache_path(args.state_dir)} "
              f"(open={open_cnt}, closed={closed_cnt}, other={other_cnt})")
    return 0


def cmd_list(args, schema: dict, client: TencentDocsMCPClient | None = None) -> int:
    cli = None if args.offline else (client or _build_client(schema))
    records = _load_records(cli, schema, args.state_dir, offline=args.offline)
    open_set = set(schema["statuses"]["open"])
    closed_set = set(schema["statuses"]["closed"])

    filtered = []
    for rec in records:
        st = rec.get("status", "")
        if args.view == "open" and st in closed_set:
            continue
        if args.view == "closed" and st not in closed_set:
            continue
        if args.status and st != args.status:
            continue
        if args.type and rec.get("type", "") != args.type:
            continue
        if args.prio and args.prio.lower() not in (rec.get("priority") or "").lower():
            continue
        if args.search:
            hay = "\n".join([
                str(rec.get("number") or ""),
                rec.get("record_id", ""),
                rec.get("title", ""),
                rec.get("description", ""),
                rec.get("notes", ""),
                rec.get("proposer", ""),
            ]).lower()
            if args.search.lower() not in hay:
                continue
        filtered.append(rec)

    filtered.sort(key=lambda r: (0, int(r["number"])) if isinstance(r.get("number"), int) else (1, r.get("record_id", "")))

    if getattr(args, "json", False):
        print(json.dumps({
            "schema": 1,
            "view": args.view,
            "count": len(filtered),
            "records": filtered,
        }, indent=2, ensure_ascii=False))
        return 0

    print(f"== SmartSheet {args.view} ({len(filtered)} record(s))")
    for rec in filtered:
        num = _format_num(rec.get("number"))
        st = rec.get("status") or "<空>"
        pr = rec.get("priority") or "-"
        tp = rec.get("type") or "-"
        ver = f" [{rec['version']}]" if rec.get("version") else ""
        print(f"{num:>5} | {rec['record_id']} | {st:10} | {pr:6} | {tp:5} | {rec.get('title', '')}{ver}")
    return 0


def cmd_show(args, schema: dict, client: TencentDocsMCPClient | None = None) -> int:
    cli = None if args.offline else (client or _build_client(schema))
    records = _load_records(cli, schema, args.state_dir, offline=args.offline)
    try:
        rec = resolve_record(records, args.record)
    except ValueError as exc:
        raise SystemExit(f"tracker: {exc}")

    relay = relay_mod.Relay(state_dir=args.state_dir)
    aliases = relay.match_aliases((rec.get("title") or "") + "\n" + (rec.get("description") or ""))

    if getattr(args, "json", False):
        print(json.dumps({"schema": 1, "record": rec, "aliases": aliases}, indent=2, ensure_ascii=False))
        return 0

    print(f"Issue {_format_num(rec.get('number'))} ({rec['record_id']}): {rec.get('title', '')}")
    print(f"  状态      : {rec.get('status') or '<空>'}")
    print(f"  类型      : {rec.get('type') or '-'}")
    print(f"  优先级    : {rec.get('priority') or '-'}")
    print(f"  提出者    : {rec.get('proposer') or '-'}")
    print(f"  落盘版本  : {rec.get('version') or '-'}")
    if aliases:
        print("  别名提示  :")
        for item in aliases:
            print(f"    - {item['alias']} -> {item['actor']} ({item['scope']})")
    print("\n--- 详细设计与说明 ---")
    print(rec.get("description") or "(empty)")
    print("\n--- 维护者备注 ---")
    print(rec.get("notes") or "(empty)")
    return 0


def cmd_start(args, schema: dict, client: TencentDocsMCPClient | None = None) -> int:
    cli = None if args.offline else (client or _build_client(schema))
    records = _load_records(cli, schema, args.state_dir, offline=args.offline)
    try:
        rec = resolve_record(records, args.record)
    except ValueError as exc:
        raise SystemExit(f"tracker: {exc}")

    relay = relay_mod.Relay(state_dir=args.state_dir)
    rid = rec["record_id"]
    title = rec.get("title") or rid
    acceptance = list(args.acceptance or [])
    if not acceptance:
        acceptance = [f"Resolve SmartSheet {_format_num(rec.get('number'))} ({rid}): {title}"]

    changes = {"status": "开发中"} if rec.get("status") != "开发中" else {}

    if not args.apply and not args.local_only:
        print(f"[DRY-RUN] Would initialize relay task in {relay.root}:")
        print(f"  title     : {title}")
        print(f"  record    : {rid} ({SMARTSHEET_REF_PREFIX}{rid})")
        print(f"  acceptance: {acceptance}")
        print(f"  scope     : {args.scope or '(none)'}")
        if changes:
            _print_diff(rec, changes, schema)
        else:
            print("Remote status is already 开发中.")
        print("Pass `--local-only` to initialize relay only, or `--apply` to initialize relay and update SmartSheet.")
        return 0

    if relay.task_file.is_file() and not args.force:
        raise SystemExit("relay: an active task exists; pass --force to replace it or run `python3 tools/relay.py clear`")

    init_args = argparse.Namespace(
        title=title,
        acceptance=acceptance,
        scope=args.scope or "",
        record=rid,
        notes=(rec.get("description") or "")[:1000],
        force=args.force,
    )
    relay.cmd_init(init_args)

    if args.apply and changes:
        write_cli = cli or client or _build_client(schema)
        payload = build_update_payload(rid, changes, schema)
        write_cli.update_records([payload])
        print(f"tracker: updated {_format_num(rec.get('number'))} ({rid}) status -> 开发中")
    return 0


def cmd_report(args, schema: dict, client: TencentDocsMCPClient | None = None) -> int:
    target_status = args.status
    if target_status not in ("已完成", "开发中", "待评估"):
        raise SystemExit("tracker: report --status must be 已完成, 开发中, or 待评估")

    relay = relay_mod.Relay(state_dir=args.state_dir)
    ok, errors, gate, current = check_report_guard(relay, target_status, args.allow_unverified)
    if not ok:
        for err in errors:
            print(f"tracker: BLOCKED: {err}", file=sys.stderr)
        return 1

    cli = None if args.offline else (client or _build_client(schema))
    records = _load_records(cli, schema, args.state_dir, offline=args.offline)
    try:
        rec = resolve_record(records, args.record)
    except ValueError as exc:
        raise SystemExit(f"tracker: {exc}")

    sha = (args.commit or "").strip()
    if not sha and target_status != "待评估":
        sha = str(current.get("head") or "").strip()

    counts = gate.get("counts") or {}
    layer = gate.get("layer") or ""
    if gate and gate.get("ok"):
        gate_desc = (
            f"gate --{layer} PASS ({counts.get('pass', '?')} passed, "
            f"{counts.get('fail', '?')} failed, {counts.get('skip', '?')} skipped) "
            f"at {gate.get('git_head')}"
        )
        if layer != "full":
            gate_desc += "（未运行 --full 实机引擎验证）"
    else:
        gate_desc = "（--allow-unverified：尚未通过本地 gate 验证）"

    header_parts = [today_utc8()]
    if sha:
        header_parts.append(sha)
    entry = f"【修复回写｜{'｜'.join(header_parts)}】\n{args.summary.strip()}\n验证：{gate_desc}"

    existing_notes = (rec.get("notes") or "").strip()
    new_notes = f"{existing_notes}\n\n{entry}" if existing_notes else entry

    changes: dict[str, object] = {
        "status": target_status,
        "notes": new_notes,
    }
    if args.version:
        changes["version"] = merge_csv_tokens(rec.get("version", ""), args.version)

    _print_diff(rec, changes, schema)
    if not args.apply:
        print("Dry-run only; pass `--apply` to write changes to SmartSheet.")
        return 0

    write_cli = cli or client or _build_client(schema)
    payload = build_update_payload(rec["record_id"], changes, schema)
    write_cli.update_records([payload])
    print(f"tracker: applied report to {_format_num(rec.get('number'))} ({rec['record_id']}).")
    return 0


def cmd_close(args, schema: dict, client: TencentDocsMCPClient | None = None) -> int:
    resolutions = schema["statuses"]["close_resolutions"]
    if args.resolution not in resolutions:
        raise SystemExit(f"tracker: --as must be one of {', '.join(sorted(resolutions))}")
    target_status = resolutions[args.resolution]

    cli = None if args.offline else (client or _build_client(schema))
    records = _load_records(cli, schema, args.state_dir, offline=args.offline)
    try:
        rec = resolve_record(records, args.record)
    except ValueError as exc:
        raise SystemExit(f"tracker: {exc}")

    merged_version = merge_csv_tokens(rec.get("version", ""), args.version or "")
    if args.resolution == "completed" and not merged_version and not args.allow_no_version:
        raise SystemExit(
            "tracker: closing as completed requires --version (or an existing 落盘版本); "
            "pass --allow-no-version to override"
        )

    close_date = args.date or today_utc8()
    try:
        date_to_ms_utc8(close_date)
    except ValueError as exc:
        raise SystemExit(f"tracker: {exc}")

    changes: dict[str, object] = {
        "status": target_status,
    }
    if args.version:
        changes["version"] = merged_version
    if args.note:
        entry = f"【结案归档｜{close_date}｜{target_status}】\n{args.note.strip()}"
        existing_notes = (rec.get("notes") or "").strip()
        changes["notes"] = f"{existing_notes}\n\n{entry}" if existing_notes else entry

    _print_diff(rec, changes, schema)
    if not args.apply:
        print("Dry-run only; pass `--apply` to close record on SmartSheet.")
        return 0

    write_cli = cli or client or _build_client(schema)
    payload = build_update_payload(rec["record_id"], changes, schema)
    write_cli.update_records([payload])
    print(f"tracker: closed {_format_num(rec.get('number'))} ({rec['record_id']}) as {target_status}.")
    return 0


def cmd_reopen(args, schema: dict, client: TencentDocsMCPClient | None = None) -> int:
    if args.status not in ("待开发", "开发中", "待评估"):
        raise SystemExit("tracker: reopen --status must be 待开发, 开发中, or 待评估")

    cli = None if args.offline else (client or _build_client(schema))
    records = _load_records(cli, schema, args.state_dir, offline=args.offline)
    try:
        rec = resolve_record(records, args.record)
    except ValueError as exc:
        raise SystemExit(f"tracker: {exc}")

    entry = f"【回归重开｜{today_utc8()}】\n{args.note.strip()}"
    existing_notes = (rec.get("notes") or "").strip()
    changes: dict[str, object] = {
        "status": args.status,
        "notes": f"{existing_notes}\n\n{entry}" if existing_notes else entry,
    }

    _print_diff(rec, changes, schema)
    if not args.apply:
        print("Dry-run only; pass `--apply` to reopen record on SmartSheet.")
        return 0

    write_cli = cli or client or _build_client(schema)
    payload = build_update_payload(rec["record_id"], changes, schema)
    write_cli.update_records([payload])
    print(f"tracker: reopened {_format_num(rec.get('number'))} ({rec['record_id']}) -> {args.status}.")
    return 0


def scan_git_smartsheet_refs(since: str = "", limit: int = 30) -> list[tuple[str, str, str]]:
    """Return [(short_sha, subject, record_id), ...] for commits referencing SmartSheet."""
    cmd = ["git", "log", "--format=%h\t%s\t%B\x1e"]
    if since:
        cmd.append(f"{since}..HEAD")
    else:
        cmd.extend(["-n", str(limit)])
    proc = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, timeout=30)
    if proc.returncode != 0:
        return []
    hits: list[tuple[str, str, str]] = []
    for chunk in proc.stdout.split("\x1e"):
        chunk = chunk.strip()
        if not chunk:
            continue
        parts = chunk.split("\t", 2)
        if len(parts) < 3:
            continue
        sha, subj, body = parts
        seen_rids: set[str] = set()
        for rid in re.findall(re.escape(SMARTSHEET_REF_PREFIX) + r"([A-Za-z0-9_]+)", body):
            if rid not in seen_rids:
                seen_rids.add(rid)
                hits.append((sha.strip(), subj.strip(), rid))
    return hits


def validate_live_fields(live_fields: list[dict], schema: dict) -> list[str]:
    """Compare live SmartSheet fields and status options against local schema."""
    errors: list[str] = []
    by_id = {f.get("field_id"): f for f in live_fields}
    for lkey, spec in schema["fields"].items():
        lf = by_id.get(spec["id"])
        if not lf:
            errors.append(f"missing field {lkey} ({spec['id']} / {spec['title']})")
            continue
        if lf.get("field_title") != spec["title"]:
            errors.append(f"field {spec['id']} title drift: {lf.get('field_title')!r} != {spec['title']!r}")
        if lf.get("field_type") != spec["type"]:
            errors.append(f"field {spec['id']} type drift: {lf.get('field_type')!r} != {spec['type']!r}")
        if lkey == "type" and (schema.get("types") or {}).get("options"):
            live_type_opts = {
                opt.get("text"): opt.get("id")
                for opt in (lf.get("property_single_select") or {}).get("options", [])
            }
            expected_type_opts = schema["types"]["options"]
            if live_type_opts != expected_type_opts:
                errors.append(f"type options drift: live={live_type_opts} != schema={expected_type_opts}")
        if lkey == "status":
            live_opts = {
                opt.get("text"): opt.get("id")
                for opt in (lf.get("property_single_select") or {}).get("options", [])
            }
            expected_opts = schema["statuses"]["options"]
            if live_opts != expected_opts:
                errors.append(f"status options drift: live={live_opts} != schema={expected_opts}")
    return errors


def run_audit(schema: dict, records: list[dict], live_fields: list[dict] | None,
              git_refs: list[tuple[str, str, str]]) -> dict:
    """Compute schema drift, invalid/empty status rows, git-ref lag, and ready-to-test triage."""
    schema_errors = validate_live_fields(live_fields, schema) if live_fields is not None else []
    valid_statuses = set(schema["statuses"]["options"].keys())
    empty_status = [
        {"record_id": r["record_id"], "number": r.get("number"), "title": r.get("title", ""), "status": r.get("status", "")}
        for r in records
        if r.get("status", "") not in valid_statuses
    ]

    by_id = {r["record_id"]: r for r in records}
    git_lag = []
    for sha, subj, rid in git_refs:
        rec = by_id.get(rid)
        if not rec:
            git_lag.append({
                "sha": sha, "subject": subj, "record_id": rid,
                "reason": "referenced record_id not found in sheet",
            })
            continue
        issues = []
        if rec.get("status") in ("待评估", "待开发", "开发中"):
            issues.append(f"status still {rec.get('status')!r}")
        notes_lower = (rec.get("notes") or "").lower()
        if sha.lower() not in notes_lower:
            issues.append(f"commit {sha} missing from 维护者备注")
        if issues:
            git_lag.append({
                "sha": sha, "subject": subj, "record_id": rid,
                "number": rec.get("number"), "title": rec.get("title", ""),
                "reason": "; ".join(issues),
            })

    ok = not schema_errors and not empty_status
    return {
        "schema": 1,
        "ok": ok,
        "total_records": len(records),
        "schema_errors": schema_errors,
        "invalid_or_empty_status": empty_status,
        "git_ref_lag": git_lag,
    }


def cmd_audit(args, schema: dict, client: TencentDocsMCPClient | None = None) -> int:
    cli = None if args.offline else (client or _build_client(schema))
    live_fields = cli.list_fields() if cli is not None else None
    records = _load_records(cli, schema, args.state_dir, offline=args.offline)
    git_refs = scan_git_smartsheet_refs(since=args.since or "")
    report = run_audit(schema, records, live_fields, git_refs)

    if getattr(args, "json", False):
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"== SmartSheet audit ({report['total_records']} record(s), mode={'offline' if args.offline else 'online'})")
        if live_fields is not None:
            if report["schema_errors"]:
                for err in report["schema_errors"]:
                    print(f"[FAIL] schema: {err}")
            else:
                print(
                    f"[PASS] schema matches {DEFAULT_SCHEMA_PATH.name} "
                    f"({len(schema['fields'])} fields, {len(schema['statuses']['options'])} status options)"
                )
        if report["invalid_or_empty_status"]:
            for item in report["invalid_or_empty_status"]:
                print(f"[FAIL] invalid/empty status: {_format_num(item['number'])} ({item['record_id']}) status={item['status']!r}")
        else:
            print("[PASS] 0 empty or unrecognized status rows")

        print(f"[INFO] git-ref sync lag: {len(report['git_ref_lag'])}")
        for item in report["git_ref_lag"]:
            print(f"  - {item['sha']} -> {_format_num(item.get('number'))} ({item['record_id']}): {item['reason']}")

    ok = report["ok"] and (not args.strict or not report["git_ref_lag"])
    return 0 if ok else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA_PATH, help="path to smartsheet.schema.json")
    parser.add_argument("--state-dir", type=Path, help="override .relay state/cache directory")
    sub = parser.add_subparsers(dest="command")

    p_sync = sub.add_parser("sync", help="refresh local SmartSheet cache in .relay/")
    p_sync.add_argument("--json", action="store_true")

    p_list = sub.add_parser("list", help="list SmartSheet records")
    p_list.add_argument("--view", choices=("open", "closed", "all"), default="open")
    p_list.add_argument("--status", default="", help="exact status filter")
    p_list.add_argument("--type", default="", help="exact type filter")
    p_list.add_argument("--prio", default="", help="priority substring filter (e.g. P0, P1)")
    p_list.add_argument("--search", default="", help="keyword search across title/desc/verification")
    p_list.add_argument("--offline", action="store_true", help="read from .relay/smartsheet_cache.json")
    p_list.add_argument("--json", action="store_true")

    p_show = sub.add_parser("show", help="show full details and alias hints for a record")
    p_show.add_argument("record", help="record_id (e.g. rlSWRI) or #number / number")
    p_show.add_argument("--offline", action="store_true")
    p_show.add_argument("--json", action="store_true")

    p_start = sub.add_parser("start", help="bind a SmartSheet record to tools/relay.py and mark 开发中")
    p_start.add_argument("record", help="record_id or #number")
    p_start.add_argument("--scope", default="", help="comma-separated advisory write_scopes")
    p_start.add_argument("--acceptance", action="append", default=[], help="acceptance criterion (repeatable)")
    p_start.add_argument("--force", action="store_true", help="replace active relay task")
    p_start.add_argument("--offline", action="store_true")
    p_start.add_argument("--local-only", action="store_true", help="only initialize local .relay/ task")
    p_start.add_argument("--apply", action="store_true", help="initialize relay and mark remote 开发中")

    p_report = sub.add_parser("report", help="write verified progress/commit back to SmartSheet (dry-run default)")
    p_report.add_argument("record", help="record_id or #number")
    p_report.add_argument("--summary", required=True, help="user-visible behavior & verification summary")
    p_report.add_argument("--status", default="已完成", choices=("已完成", "开发中", "待评估"))
    p_report.add_argument("--commit", default="", help="short commit SHA (defaults to current git HEAD)")
    p_report.add_argument("--version", default="", help="optional target version (e.g. 4.0.0-beta.261119)")
    p_report.add_argument("--allow-unverified", action="store_true", help="bypass passing relay gate requirement")
    p_report.add_argument("--offline", action="store_true", help="preview diff against local cache")
    p_report.add_argument("--apply", action="store_true", help="write update to SmartSheet")

    p_close = sub.add_parser("close", help="archive a record as Closed without deleting it (dry-run default)")
    p_close.add_argument("record", help="record_id or #number")
    p_close.add_argument("--as", dest="resolution", required=True, choices=("completed", "wontfix"))
    p_close.add_argument("--version", default="", help="release/landing version")
    p_close.add_argument("--note", default="", help="closing/acceptance note")
    p_close.add_argument("--date", default="", help="YYYY-MM-DD archive date (default today UTC+8)")
    p_close.add_argument("--allow-no-version", action="store_true", help="allow completed without --version")
    p_close.add_argument("--offline", action="store_true", help="preview diff against local cache")
    p_close.add_argument("--apply", action="store_true", help="write close update to SmartSheet")

    p_reopen = sub.add_parser("reopen", help="reopen a Closed record without losing history (dry-run default)")
    p_reopen.add_argument("record", help="record_id or #number")
    p_reopen.add_argument("--note", required=True, help="reason for reopening")
    p_reopen.add_argument("--status", default="待开发", choices=("待开发", "开发中", "待评估"))
    p_reopen.add_argument("--offline", action="store_true", help="preview diff against local cache")
    p_reopen.add_argument("--apply", action="store_true", help="write reopen update to SmartSheet")

    p_audit = sub.add_parser("audit", help="validate live schema, empty statuses, and git ref sync")
    p_audit.add_argument("--since", default="", help="git ref lower bound (default last 30 commits)")
    p_audit.add_argument("--offline", action="store_true")
    p_audit.add_argument("--strict", action="store_true", help="fail if git-ref sync lag is detected")
    p_audit.add_argument("--json", action="store_true")

    return parser


def main(argv: list[str] | None = None, client: TencentDocsMCPClient | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 0
    schema = load_schema(args.schema)
    dispatch = {
        "sync": cmd_sync,
        "list": cmd_list,
        "show": cmd_show,
        "start": cmd_start,
        "report": cmd_report,
        "close": cmd_close,
        "reopen": cmd_reopen,
        "audit": cmd_audit,
    }
    return dispatch[args.command](args, schema, client=client)


if __name__ == "__main__":
    sys.exit(main())

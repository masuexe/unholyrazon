#!/usr/bin/env python3
"""Offline unit tests for tools/tracker.py and tools/smartsheet.schema.json."""
from __future__ import annotations

import copy
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from unittest import mock

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import relay as relay_mod  # noqa: E402
import tracker  # noqa: E402


def make_raw_record(record_id: str, number: int, title: str, status: str = "待处理",
                    rtype: str = "Bug", prio: str = "P1-核心", proposer: str = "tester",
                    desc: str = "", commits: str = "", verification: str = "",
                    version: str = "", archived_ms: str = "") -> dict:
    fvals = [
        {"field": "编号", "auto_number_value": {"seq": str(number), "text": str(number)}},
        {"field": "需求名称", "text_value": {"items": [{"text": title, "type": "text"}]}},
        {"field": "类型", "option_value": {"items": [{"text": rtype}]}},
        {"field": "状态", "option_value": {"items": [{"text": status}]} if status else {"items": []}},
        {"field": "优先级", "option_value": {"items": [{"text": prio}]}},
        {"field": "提出者", "text_value": {"items": [{"text": proposer, "type": "text"}]}},
    ]
    if desc:
        fvals.append({"field": "详细设计与说明", "text_value": {"items": [{"text": desc, "type": "text"}]}})
    if commits:
        fvals.append({"field": "关联 Commit", "text_value": {"items": [{"text": commits, "type": "text"}]}})
    if verification:
        fvals.append({"field": "验证与结案说明", "text_value": {"items": [{"text": verification, "type": "text"}]}})
    if version:
        fvals.append({"field": "落盘版本", "text_value": {"items": [{"text": version, "type": "text"}]}})
    if archived_ms:
        fvals.append({"field": "归档时间", "string_value": archived_ms})
    return {"record_id": record_id, "field_values": fvals}


def make_live_fields(schema: dict) -> list[dict]:
    fields = []
    for lkey, spec in schema["fields"].items():
        item = {
            "field_id": spec["id"],
            "field_title": spec["title"],
            "field_type": spec["type"],
        }
        if lkey == "status":
            item["property_single_select"] = {
                "options": [
                    {"id": opt_id, "text": text}
                    for text, opt_id in schema["statuses"]["options"].items()
                ]
            }
        fields.append(item)
    return fields


class FakeClient:
    def __init__(self, schema: dict, raw_records: list[dict], live_fields: list[dict] | None = None):
        self.schema = schema
        self.raw_records = raw_records
        self.live_fields = live_fields if live_fields is not None else make_live_fields(schema)
        self.updated_batches: list[list[dict]] = []

    def list_fields(self) -> list[dict]:
        return copy.deepcopy(self.live_fields)

    def list_views(self) -> list[dict]:
        return []

    def list_records(self) -> list[dict]:
        return copy.deepcopy(self.raw_records)

    def update_records(self, records: list[dict]) -> dict:
        self.updated_batches.append(copy.deepcopy(records))
        return {"error": ""}


class FakeRelay(relay_mod.Relay):
    def __init__(self, state_dir: Path, head: str = "abcd1234", dirty: bool = False):
        super().__init__(state_dir=state_dir)
        self._fake_head = head
        self._fake_dirty = dirty

    def git_state(self) -> dict:
        return {
            "head": self._fake_head,
            "branch": "master",
            "dirty": self._fake_dirty,
            "dirty_files": 1 if self._fake_dirty else 0,
            "dirty_fingerprint": "0000000000000000",
        }


class TrackerContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.schema = tracker.load_schema(TOOLS_DIR / "smartsheet.schema.json")
        self.tmp = tempfile.TemporaryDirectory()
        self.state_dir = Path(self.tmp.name) / "relay"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_schema_valid_and_safe_cli(self) -> None:
        tracker.validate_schema_local(self.schema)
        src = (TOOLS_DIR / "tracker.py").read_text(encoding="utf-8")
        forbidden_tools = [
            "smartsheet." + "delete_" + "records",
            "smartsheet." + "delete_" + "fields",
            "smartsheet." + "delete_" + "view",
            "smartsheet." + "delete_" + "table",
        ]
        for marker in forbidden_tools:
            self.assertNotIn(marker, src, f"forbidden delete call found: {marker}")

        parser = tracker.build_parser()
        sub_actions = [
            action for action in parser._actions
            if getattr(action, "choices", None)
        ]
        cmds = set(sub_actions[0].choices.keys())
        self.assertEqual(cmds, {"sync", "list", "show", "start", "report", "close", "reopen", "audit"})
        self.assertNotIn("delete", cmds)

    def test_resolve_merge_date_and_payload(self) -> None:
        records = [
            tracker.normalize_record(make_raw_record("rlSWRI", 4, "voidwalker卡顿"), self.schema),
            tracker.normalize_record(make_raw_record("rKaP54", 7, "zakobox卡墙角", status="已实装"), self.schema),
        ]
        self.assertEqual(tracker.resolve_record(records, "rlSWRI")["number"], 4)
        self.assertEqual(tracker.resolve_record(records, "#4")["record_id"], "rlSWRI")
        self.assertEqual(tracker.resolve_record(records, "7")["record_id"], "rKaP54")
        with self.assertRaises(ValueError):
            tracker.resolve_record(records, "#999")

        self.assertEqual(
            tracker.merge_csv_tokens("abcd1234, ef001122", "EF001122, 99887766"),
            "abcd1234, ef001122, 99887766",
        )

        ms = tracker.date_to_ms_utc8("2026-11-14")
        self.assertEqual(tracker.ms_to_date_utc8(ms), "2026-11-14")

        payload = tracker.build_update_payload(
            "rlSWRI",
            {
                "status": "待测试",
                "commits": "349abf5f",
                "description": "",
                "archived_at": "2026-11-19",
            },
            self.schema,
        )
        fmap = {item["field"]: item for item in payload["field_values"]}
        self.assertEqual(fmap["状态"]["option_value"], {"items": [{"text": "待测试"}]})
        self.assertEqual(fmap["关联 Commit"]["text_value"], {"items": [{"text": "349abf5f", "type": "text"}]})
        self.assertEqual(fmap["详细设计与说明"]["text_value"], {"items": []})
        self.assertEqual(fmap["归档时间"]["string_value"], tracker.date_to_ms_utc8("2026-11-19"))

        with self.assertRaises(ValueError):
            tracker.build_update_payload("rlSWRI", {"number": 5}, self.schema)
        with self.assertRaises(ValueError):
            tracker.build_update_payload("rlSWRI", {"status": "不存在状态"}, self.schema)

    def test_report_guard_blocks_unverified_and_stale(self) -> None:
        # 1. Missing handoff / missing gate with clean git tree
        relay_missing = FakeRelay(self.state_dir / "missing", head="abcd1234", dirty=False)
        ok, errors, _, _ = tracker.check_report_guard(relay_missing, "待测试", allow_unverified=False)
        self.assertFalse(ok)
        self.assertTrue(errors)

        # 2. Failed gate
        relay_fail = FakeRelay(self.state_dir / "fail", head="abcd1234", dirty=False)
        relay_fail.write_json(relay_fail.handoff_file, {
            "gate": {"layer": "fast", "ok": False, "git_head": "abcd1234", "counts": {"pass": 32, "fail": 1, "skip": 0}},
        })
        ok, _, _, _ = tracker.check_report_guard(relay_fail, "待测试", allow_unverified=False)
        self.assertFalse(ok)

        # 3. Stale git HEAD
        relay_stale = FakeRelay(self.state_dir / "stale", head="ef999999", dirty=False)
        relay_stale.write_json(relay_stale.handoff_file, {
            "gate": {"layer": "fast", "ok": True, "git_head": "abcd1234", "counts": {"pass": 33, "fail": 0, "skip": 0}},
        })
        ok, _, _, _ = tracker.check_report_guard(relay_stale, "待测试", allow_unverified=False)
        self.assertFalse(ok)

        # 4. Dirty working tree
        relay_dirty = FakeRelay(self.state_dir / "dirty", head="abcd1234", dirty=True)
        relay_dirty.write_json(relay_dirty.handoff_file, {
            "gate": {"layer": "fast", "ok": True, "git_head": "abcd1234", "counts": {"pass": 33, "fail": 0, "skip": 0}},
        })
        ok, _, _, _ = tracker.check_report_guard(relay_dirty, "待测试", allow_unverified=False)
        self.assertFalse(ok)

        # 5. Passing clean gate
        relay_pass = FakeRelay(self.state_dir / "pass", head="abcd1234", dirty=False)
        relay_pass.write_json(relay_pass.handoff_file, {
            "gate": {"layer": "smoke", "ok": True, "git_head": "abcd1234", "counts": {"pass": 38, "fail": 0, "skip": 0}},
        })
        ok, errors, _, _ = tracker.check_report_guard(relay_pass, "待测试", allow_unverified=False)
        self.assertTrue(ok, errors)

    def test_dry_run_and_apply_lifecycle(self) -> None:
        raw = [
            make_raw_record("rlSWRI", 4, "voidwalker卡顿", status="待处理", commits="d46878d6"),
            make_raw_record("rKaP54", 7, "zakobox卡墙角", status="待测试", commits="ac80637e", version="4.0.0-beta.261114"),
        ]
        client = FakeClient(self.schema, raw)
        fake_relay = FakeRelay(self.state_dir, head="349abf5f", dirty=False)

        with mock.patch.object(tracker.relay_mod, "Relay", return_value=fake_relay):
            # start dry-run must not write local relay or remote smartsheet
            out = io.StringIO()
            with redirect_stdout(out):
                rc = tracker.main(["--state-dir", str(self.state_dir), "start", "#4"], client=client)
            self.assertEqual(rc, 0)
            self.assertEqual(client.updated_batches, [])
            self.assertFalse(fake_relay.task_file.exists())

            # start --apply writes relay task + marks 开发中
            with redirect_stdout(io.StringIO()):
                rc = tracker.main(["--state-dir", str(self.state_dir), "start", "rlSWRI", "--apply"], client=client)
            self.assertEqual(rc, 0)
            self.assertTrue(fake_relay.task_file.exists())
            task = fake_relay.read_json(fake_relay.task_file)
            self.assertEqual(task["records"], ["rlSWRI"])
            self.assertEqual(len(client.updated_batches), 1)
            self.assertEqual(client.updated_batches[-1][0]["field_values"][0]["option_value"]["items"][0]["text"], "开发中")

            # report without passing gate must block even on dry-run
            err_buf = io.StringIO()
            with redirect_stderr(err_buf):
                rc = tracker.main(["--state-dir", str(self.state_dir), "report", "rlSWRI", "--summary", "fix"], client=client)
            self.assertEqual(rc, 1)
            self.assertIn("BLOCKED", err_buf.getvalue())

            # record passing smoke gate, then test report dry-run and --apply
            fake_relay.write_json(fake_relay.handoff_file, {
                "gate": {"layer": "smoke", "ok": True, "git_head": "349abf5f", "counts": {"pass": 38, "fail": 0, "skip": 0}},
            })
            with redirect_stdout(io.StringIO()):
                rc = tracker.main([
                    "--state-dir", str(self.state_dir), "report", "#4",
                    "--summary", "IceBeam trails moved clientside.", "--version", "4.0.0-beta.261117",
                ], client=client)
            self.assertEqual(rc, 0)
            self.assertEqual(len(client.updated_batches), 1)

            with redirect_stdout(io.StringIO()):
                rc = tracker.main([
                    "--state-dir", str(self.state_dir), "report", "#4",
                    "--summary", "IceBeam trails moved clientside.", "--version", "4.0.0-beta.261117", "--apply",
                ], client=client)
            self.assertEqual(rc, 0)
            self.assertEqual(len(client.updated_batches), 2)
            sent = {fv["field"]: fv for fv in client.updated_batches[-1][0]["field_values"]}
            self.assertEqual(sent["状态"]["option_value"]["items"][0]["text"], "待测试")
            self.assertEqual(sent["关联 Commit"]["text_value"]["items"][0]["text"], "d46878d6, 349abf5f")
            self.assertEqual(sent["落盘版本"]["text_value"]["items"][0]["text"], "4.0.0-beta.261117")
            verif_text = sent["验证与结案说明"]["text_value"]["items"][0]["text"]
            self.assertIn("未运行 --full", verif_text)

            # close dry-run vs --apply
            with redirect_stdout(io.StringIO()):
                rc = tracker.main([
                    "--state-dir", str(self.state_dir), "close", "#7", "--as", "completed", "--date", "2026-11-19",
                ], client=client)
            self.assertEqual(rc, 0)
            self.assertEqual(len(client.updated_batches), 2)

            with redirect_stdout(io.StringIO()):
                rc = tracker.main([
                    "--state-dir", str(self.state_dir), "close", "#7", "--as", "completed",
                    "--date", "2026-11-19", "--note", "Verified in live match.", "--apply",
                ], client=client)
            self.assertEqual(rc, 0)
            self.assertEqual(len(client.updated_batches), 3)
            closed_sent = {fv["field"]: fv for fv in client.updated_batches[-1][0]["field_values"]}
            self.assertEqual(closed_sent["状态"]["option_value"]["items"][0]["text"], "已实装")
            self.assertEqual(closed_sent["归档时间"]["string_value"], tracker.date_to_ms_utc8("2026-11-19"))

            # reopen --apply
            with redirect_stdout(io.StringIO()):
                rc = tracker.main([
                    "--state-dir", str(self.state_dir), "reopen", "rKaP54", "--note", "Reproduced on MAP01", "--apply",
                ], client=client)
            self.assertEqual(rc, 0)
            self.assertEqual(len(client.updated_batches), 4)
            reopen_sent = {fv["field"]: fv for fv in client.updated_batches[-1][0]["field_values"]}
            self.assertEqual(reopen_sent["状态"]["option_value"]["items"][0]["text"], "开发中")

    def test_audit_detects_schema_drift_and_git_lag(self) -> None:
        raw = [
            make_raw_record("rlSWRI", 4, "voidwalker卡顿", status="待处理", commits=""),
            make_raw_record("rKaP54", 7, "zakobox", status="待测试", commits="ac80637e", version="4.0.0-beta.261114"),
        ]
        # Clean live schema, but git ref points to rlSWRI which is still 待处理 and missing commit
        clean_client = FakeClient(self.schema, raw)
        with mock.patch.object(tracker, "scan_git_smartsheet_refs", return_value=[("349abf5f", "fix stalls", "rlSWRI")]):
            out = io.StringIO()
            with redirect_stdout(out):
                rc = tracker.main(["--state-dir", str(self.state_dir), "audit", "--json"], client=clean_client)
            self.assertEqual(rc, 0)
            data = json.loads(out.getvalue())
            self.assertTrue(data["ok"])
            self.assertEqual(len(data["git_ref_lag"]), 1)
            self.assertEqual(data["git_ref_lag"][0]["record_id"], "rlSWRI")
            self.assertEqual(len(data["ready_to_test"]), 1)

            # --strict fails on git_ref_lag
            with redirect_stdout(io.StringIO()):
                rc_strict = tracker.main(["--state-dir", str(self.state_dir), "audit", "--strict"], client=clean_client)
            self.assertEqual(rc_strict, 1)

        # Schema drift (drop commits field and rename status option) -> fails audit
        bad_fields = make_live_fields(self.schema)
        bad_fields = [f for f in bad_fields if f["field_id"] != self.schema["fields"]["commits"]["id"]]
        for f in bad_fields:
            if f["field_id"] == self.schema["fields"]["status"]["id"]:
                f["property_single_select"]["options"][0]["text"] = "已改名"
        bad_client = FakeClient(self.schema, raw, live_fields=bad_fields)
        with mock.patch.object(tracker, "scan_git_smartsheet_refs", return_value=[]):
            out2 = io.StringIO()
            with redirect_stdout(out2):
                rc2 = tracker.main(["--state-dir", str(self.state_dir), "audit", "--json"], client=bad_client)
            self.assertEqual(rc2, 1)
            data2 = json.loads(out2.getvalue())
            self.assertFalse(data2["ok"])
            self.assertTrue(len(data2["schema_errors"]) >= 2)


if __name__ == "__main__":
    unittest.main()

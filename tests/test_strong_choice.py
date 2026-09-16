import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parents[1] / "plugins/android-tv-apps-helper/scripts"))
from tv_helper.questions import Question, Option, AnswerError
from tv_helper.session import SessionStore
from tv_helper.presentation import build_host_presentation
from tv_helper.workflow import WorkflowEngine, build_question


class StrongChoiceTests(unittest.TestCase):
    def test_all_workflow_states_produce_valid_native_pages(self):
        from tv_helper.workflow import WORKFLOW_STATES
        for state in WORKFLOW_STATES:
            question = build_question(state, {})
            for platform, limit in (("codex", 3), ("workbuddy", 4), ("doubao-work", 4), ("claude", 4)):
                with self.subTest(state=state, platform=platform):
                    view = build_host_presentation(question, {"host_platform": platform})
                    self.assertEqual(view["mode"], "native_required")
                    options = view["tool_input"]["questions"][0]["options"]
                    self.assertGreaterEqual(len(options), 2)
                    self.assertLessEqual(len(options), limit)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def session(self, question, platform="workbuddy"):
        store = SessionStore.create(Path(self.temp.name) / f"{platform}.json", interaction_surface="auto", host_platform=platform)
        store.set_question(question)
        return store

    def view(self, store):
        data = store.read()
        return build_host_presentation(Question.from_dict(data["pending_question"]), data)

    def click(self, store, value, presentation=None):
        view = presentation or self.view(store)
        return WorkflowEngine(store).submit_native(value, question_id=view["question_id"], presentation_id=view["presentation_id"])

    def test_five_choices_stay_native_and_all_options_remain_reachable(self):
        question = build_question("DISCOVERY-NONE", {})
        for platform, limit in (("codex", 3), ("workbuddy", 4), ("doubao-work", 4), ("claude", 4)):
            with self.subTest(platform=platform):
                store = self.session(question, platform)
                seen = set()
                for _ in range(10):
                    view = self.view(store)
                    self.assertEqual(view["mode"], "native_required")
                    self.assertLessEqual(len(view["tool_input"]["questions"][0]["options"]), limit)
                    values = set(view["answer_value_map"].values())
                    self.assertIn("safe_exit", values)
                    seen.update(v for v in values if not v.startswith("ui:"))
                    if {o.value for o in question.options} <= seen:
                        break
                    self.click(store, "ui:next")
                    self.assertEqual(store.read()["history"], [])
                    self.assertEqual(store.read()["pending_question"]["question_id"], question.question_id)
                self.assertEqual(seen, {o.value for o in question.options})

    def test_navigation_does_not_authorize_action_and_rejects_old_page(self):
        store = self.session(build_question("DISCOVERY-NONE", {}))
        old = self.view(store)
        self.assertEqual(old["mode"], "native_required")
        self.click(store, "ui:next")
        self.assertIsNone(store.read()["pending_action"])
        with self.assertRaises(AnswerError):
            self.click(store, "safe_exit", old)

    def test_ip_is_choice_first_then_native_free_input_with_choices(self):
        store = self.session(build_question("DISCOVERY-IP", {}))
        first = self.view(store)
        self.assertEqual(first["mode"], "native_required")
        self.assertIn("ui:input", first["answer_value_map"].values())
        with self.assertRaises(AnswerError):
            self.click(store, "IP: 192.0.2.1")
        self.click(store, "ui:input")
        field = self.view(store)
        self.assertEqual(field["mode"], "native_required")
        self.assertTrue(field["accepts_free_input"])
        self.assertIn("safe_exit", field["answer_value_map"].values())
        result = self.click(store, "IP: not-an-ip")
        self.assertFalse(result["accepted"])
        self.assertTrue(self.view(store)["accepts_free_input"])
        result = self.click(store, "IP: 192.0.2.1")
        self.assertEqual(result["question"].state_id, "DISCOVERY-CONNECT")
        self.assertIsNone(store.read()["pending_action"])

    def test_large_multi_choice_uses_toggle_pages_and_named_confirmation(self):
        store = self.session(build_question("APPS", {}), "codex")
        first = self.view(store)
        self.assertEqual(first["mode"], "native_required")
        toggle = next(v for v in first["answer_value_map"].values() if v.startswith("ui:toggle:"))
        self.click(store, toggle)
        self.assertIsNone(store.read()["pending_action"])
        self.assertIn("已选应用", self.view(store)["context_markdown"])
        for _ in range(30):
            if "ui:done" in self.view(store)["answer_value_map"].values():
                break
            self.click(store, "ui:next")
        result = self.click(store, "ui:done")
        self.assertEqual(result["question"].state_id, "DOWNLOAD-CONFIRM")
        self.assertIsNone(store.read()["pending_action"])
        self.assertEqual(store.read()["selected_apps"], [toggle.removeprefix("ui:toggle:")])

    def test_native_errors_retry_then_block_without_number_menu(self):
        store = self.session(build_question("PRECHECK_WIFI", {}))
        for attempt in range(2):
            view = self.view(store)
            store.record_surface_failure("native_tool_call_failed", detail="host call failed", question_id=view["question_id"], presentation_id=view["presentation_id"], tool_name=view["tool_name"])
            self.assertEqual(self.view(store)["mode"], "native_required" if attempt == 0 else "native_blocked")
        blocked = self.view(store)
        self.assertNotIn("请明确回复", blocked.get("rendered") or "")
        self.assertIsNotNone(store.read()["pending_question"])
        self.assertIsNone(store.read()["pending_action"])

    def test_disabled_item_is_explained_not_a_reason_to_fall_back(self):
        question = Question("Q", "TASK", "single_choice", "请选择。", (
            Option("no", "不可用应用", "END", enabled=False, unavailable_reason="尚未验证"),
            Option("yes", "可用应用", "END"), Option("safe_exit", "安全退出", "END")))
        view = self.view(self.session(question))
        self.assertEqual(view["mode"], "native_required")
        self.assertNotIn("no", view["answer_value_map"].values())
        self.assertIn("不可用应用", view["context_markdown"])
        self.assertIn("尚未验证", view["context_markdown"])

    def test_passive_discovery_rejects_missing_device_list(self):
        store = self.session(build_question("DISCOVERY-NONE", {}))
        engine = WorkflowEngine(store)
        engine.submit("retry_passive", question_id="DISCOVERY-NONE-Q1")
        with self.assertRaises(AnswerError):
            engine.record_action("PASSIVE-DISCOVERY-ACTION", status="completed", evidence={
                "result": "checked", "commands": [["adb", "devices", "-l"]],
                "precheck": {"rows": [{"status": "completed", "item": "检查", "result": "执行成功"}], "active_scan_performed": False}})
        self.assertIsNotNone(store.read()["pending_action"])

    def test_latest_passive_result_replaces_old_zero_snapshot(self):
        from unittest.mock import patch
        from types import SimpleNamespace
        from tv_helper.precheck import run_passive_precheck
        store = self.session(build_question("DISCOVERY-NONE", {}))
        store.update_fields(precheck={"devices": [], "rows": [{"item": "被动发现", "result": "0 个候选设备"}]})
        engine = WorkflowEngine(store)
        engine.submit("retry_passive", question_id="DISCOVERY-NONE-Q1")
        def runner(argv, **kwargs):
            output = "Android Debug Bridge version 1.0.41\n" if argv[-1] == "version" else "List of devices attached\n192.0.2.10:5555 device model:MiTV\n"
            return SimpleNamespace(returncode=0, stdout=output, stderr="")
        with patch("tv_helper.precheck.find_adb", return_value=Path("/tmp/official-adb")):
            fresh = run_passive_precheck(command_runner=runner, network_probe=lambda: None)
        self.assertEqual(fresh["devices"][0]["state"], "device")
        result = engine.record_action("PASSIVE-DISCOVERY-ACTION", status="completed", evidence={
            "result": "本次被动检查完成", "commands": fresh["commands"], "precheck": fresh,
        })
        self.assertEqual(result["question"].state_id, "TARGET")
        self.assertEqual(store.read()["precheck"]["devices"][0]["serial"], "192.0.2.10:5555")
        self.assertEqual(store.read()["adb_path"], str(Path("/tmp/official-adb").resolve()))

    def test_missing_tool_blocks_and_can_resume_current_question(self):
        store = self.session(build_question("DISCOVERY-IP", {}))
        view = self.view(store)
        store.record_surface_failure("native_tool_not_exposed", detail="not exposed", question_id=view["question_id"], presentation_id=view["presentation_id"], tool_name=view["tool_name"])
        self.assertEqual(self.view(store)["mode"], "native_blocked")
        with self.assertRaises(AnswerError):
            self.click(store, "safe_exit", view)
        store.resume_native(view["question_id"])
        self.assertEqual(self.view(store)["mode"], "native_required")

    def test_bad_native_callback_cli_still_returns_native_question(self):
        from contextlib import redirect_stdout
        import io
        import json
        from tv_helper.cli import main
        store = self.session(build_question("DISCOVERY-NONE", {}))
        view = self.view(store)
        stream = io.StringIO()
        with redirect_stdout(stream):
            code = main(["workflow-native-answer", str(store.path), "--question-id", view["question_id"], "--presentation-id", view["presentation_id"], "--value", "随便"])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(stream.getvalue())["presentation"]["mode"], "native_required")

    def test_supplemental_input_cannot_activate_a_hidden_numbered_option(self):
        store = self.session(build_question("DISCOVERY-IP", {}))
        self.click(store, "ui:input")
        for raw in ("2", "back", "随便"):
            with self.subTest(raw=raw), self.assertRaises(AnswerError):
                self.click(store, raw)
        self.assertTrue(self.view(store)["accepts_free_input"])
        self.assertEqual(store.read()["pending_question"]["state_id"], "DISCOVERY-IP")

    def test_legacy_cli_cannot_bypass_native_block(self):
        from contextlib import redirect_stdout
        import io
        import json
        from tv_helper.cli import main
        store = self.session(build_question("DISCOVERY-CONNECT", {"candidate_ip": "192.0.2.1"}))
        store.update_fields(candidate_ip="192.0.2.1")
        view = self.view(store)
        store.record_surface_failure("native_tool_not_exposed", detail="missing tool", question_id=view["question_id"], presentation_id=view["presentation_id"], tool_name=view["tool_name"])
        stream = io.StringIO()
        with redirect_stdout(stream):
            code = main(["workflow-answer", str(store.path), "--question-id", view["question_id"], "--value", "1"])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(stream.getvalue())["presentation"]["mode"], "native_blocked")
        self.assertIsNone(store.read()["pending_action"])

    def test_failed_discovery_replaces_stale_snapshot_with_unknown_count(self):
        store = self.session(build_question("DISCOVERY-NONE", {}))
        store.update_fields(precheck={"devices": [], "attempts": 2})
        engine = WorkflowEngine(store)
        engine.submit("retry_passive", question_id="DISCOVERY-NONE-Q1")
        result = engine.record_action("PASSIVE-DISCOVERY-ACTION", status="failed", evidence={
            "result": "设备列表读取失败", "error": "ADB unavailable",
            "precheck": {"execution_ok": False, "devices": [], "rows": [{"status": "failed", "item": "被动检查", "result": "未完成"}]},
        })
        self.assertIs(store.read()["precheck"].get("execution_ok"), False)
        self.assertEqual(store.read()["precheck"]["attempts"], 3)
        self.assertIn("未知", self.view(store)["context_markdown"])
        self.assertNotIn("0 个可确认设备", self.view(store)["context_markdown"])
        self.assertEqual(self.view(store)["mode"], "native_required")

    def test_discovery_rejects_raw_output_conflicts_and_failed_execution(self):
        from tv_helper.evidence import validate_action_evidence
        base = {"result": "checked", "commands": [["adb", "devices", "-l"]], "precheck": {
            "devices": [], "rows": [{"item": "设备", "result": "0"}], "active_scan_performed": False,
        }}
        import copy
        for change in ({"execution_ok": False}, {"devices_exit_code": 1}, {"devices_output": "List of devices attached\n192.0.2.1:5555 device\n"}):
            evidence = copy.deepcopy(base)
            evidence["precheck"].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_action_evidence("PASSIVE-DISCOVERY-ACTION", status="completed", evidence=evidence, pending={})
        evidence = copy.deepcopy(base)
        evidence["commands"] = [["adb", "version"]]
        with self.assertRaises(ValueError):
            validate_action_evidence("PASSIVE-DISCOVERY-ACTION", status="completed", evidence=evidence, pending={})

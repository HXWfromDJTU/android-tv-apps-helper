import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from tv_helper.precheck import make_precheck_result
from tv_helper.session import SessionStore
from tv_helper.workflow import (
    ACTION_STATES,
    TERMINAL_STATES,
    WORKFLOW_STATES,
    WorkflowEngine,
    build_question,
    render_question,
)
from tv_helper.update import UpdateStateStore


ROOT = Path(__file__).parents[1]


class DialogueContractTests(unittest.TestCase):
    def test_entry_prompts_for_new_stable_version_before_precheck(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = SessionStore.create(root / "session.json", interaction_surface="text_menu")
            engine = WorkflowEngine(store)
            question = engine.enter(
                {"rows": [{"status": "attention", "item": "设备", "result": "0 台"}]},
                installed_version="0.2.0",
                latest_release={"version": "0.3.0", "release": {"html_url": "https://example.invalid/v0.3.0"}},
                update_state_store=UpdateStateStore(root / "update-state.json"),
                now=datetime(2026, 9, 15, tzinfo=UTC),
            )
            self.assertEqual(question.question_id, "UPDATE-Q1")
            self.assertEqual(store.read()["precheck"]["rows"][0]["result"], "0 台")

    def test_update_decline_snoozes_and_continues_to_precheck(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_path = root / "update-state.json"
            store = SessionStore.create(root / "session.json", interaction_surface="text_menu")
            engine = WorkflowEngine(store)
            question = engine.enter(
                {"rows": []},
                installed_version="0.2.0",
                latest_release={"version": "0.3.0", "release": {}},
                update_state_store=UpdateStateStore(state_path),
                now=datetime(2026, 9, 15, tzinfo=UTC),
            )
            result = engine.submit("2", question_id=question.question_id)
            self.assertEqual(result["question"].question_id, "PRECHECK-WIFI-Q1")
            self.assertTrue(UpdateStateStore(state_path).read()["snooze_until"].startswith("2026-09-16"))

    def test_update_acceptance_waits_for_verified_install_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = SessionStore.create(root / "session.json", interaction_surface="text_menu")
            engine = WorkflowEngine(store)
            question = engine.enter(
                {"rows": []},
                installed_version="0.2.0",
                latest_release={"version": "0.3.0", "release": {"assets": []}},
                update_state_store=UpdateStateStore(root / "update-state.json"),
            )
            result = engine.submit("1", question_id=question.question_id)
            self.assertIsNone(result["question"])
            self.assertEqual(result["action_required"]["action_id"], "UPDATE-ACTION")

    def test_initial_question_follows_automatic_precheck(self):
        precheck = make_precheck_result(
            adb_available=True,
            adb_version="1.0.41",
            devices=(),
            local_address="192.0.2.10",
            wifi_name=None,
        )
        question = build_question("PRECHECK_WIFI", {"precheck": precheck})
        rendered = render_question(question)
        self.assertEqual(question.question_id, "PRECHECK-WIFI-Q1")
        self.assertIn("ADB 工具", rendered)
        self.assertIn("0 个候选设备", rendered)
        self.assertNotIn("是否开始只读预检", rendered)

    def test_invalid_answer_repeats_same_context_rich_question(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SessionStore.create(Path(directory) / "session.json", interaction_surface="text_menu")
            engine = WorkflowEngine(store)
            precheck = make_precheck_result(
                adb_available=True,
                adb_version="1.0.41",
                devices=(),
                local_address="192.0.2.10",
                wifi_name=None,
            )
            first = engine.start(precheck)
            result = engine.submit("继续", question_id=first.question_id)
            self.assertFalse(result["accepted"])
            self.assertEqual(result["question"].question_id, first.question_id)
            self.assertEqual(result["question"].summary_rows, first.summary_rows)

    def test_no_device_question_contains_steps_and_nonduplicate_choices(self):
        question = build_question("DISCOVERY-NONE", {"attempts": 3})
        rendered = render_question(question)
        labels = [option.label for option in question.options]
        self.assertEqual(len(labels), len(set(labels)))
        self.assertIn("连续选择", rendered)
        self.assertIn("电视 IP", rendered)
        self.assertIn("第 3 次", rendered)

    def test_task_menu_uses_fixed_plain_language_labels(self):
        labels = [option.label for option in build_question("TASK", {}).options]
        self.assertIn("查看并选择推荐应用", labels)
        self.assertIn("设置电视默认桌面", labels)
        self.assertNotIn("推荐配置", labels)
        self.assertNotIn("电视清理", labels)
        self.assertEqual(len(labels), len(set(labels)))

    def test_safe_exit_is_displayed_and_accepted_as_zero(self):
        question = build_question("PRECHECK_WIFI", {"precheck": {"rows": []}})
        rendered = render_question(question)
        self.assertIn("0. 安全退出", rendered)
        self.assertEqual(question.options[-1].shortcut, "0")

    def test_every_enabled_transition_is_buildable_or_terminal(self):
        for state in WORKFLOW_STATES:
            question = build_question(state, {})
            for option in question.options:
                if not option.enabled:
                    continue
                with self.subTest(state=state, option=option.value):
                    self.assertTrue(
                        option.next_state in WORKFLOW_STATES
                        or option.next_state in ACTION_STATES
                        or option.next_state in TERMINAL_STATES
                    )
                    if option.next_state in WORKFLOW_STATES:
                        build_question(option.next_state, {})

    def test_dangbei_failure_never_asks_ordinary_user_for_apk(self):
        question = build_question("DANGBEI-SOURCE", {"source_error": "HTTP 567"})
        rendered = render_question(question)
        self.assertIn("重试当贝官方来源", rendered)
        self.assertNotIn("提供本地 APK", rendered)

    def test_wallpaper_warning_and_finish_guidance_are_inside_frame(self):
        wallpaper = render_question(build_question("WALLPAPER", {"device_name": "小米电视 MiTV-ASTP0"}))
        self.assertIn("几天后", wallpaper)
        self.assertIn("上传一张自定义图片", wallpaper)
        finish = render_question(
            build_question(
                "FINISH-SAFETY",
                {"device_name": "小米电视 MiTV-ASTP0", "guide_steps": ["进入账号与安全。", "关闭 ADB 调试。"]},
            )
        )
        self.assertIn("小米电视 MiTV-ASTP0", finish)
        self.assertIn("关闭 ADB 调试", finish)

    def test_finish_safety_rejects_claim_when_adb_still_responds(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SessionStore.create(Path(directory) / "session.json", interaction_surface="text_menu")
            store.update_fields(
                current_state="FINISH-SAFETY",
                finish_safety={"adb_still_reachable": True},
            )
            store.set_question(build_question("FINISH-SAFETY", {}))

            result = WorkflowEngine(store).submit("1", question_id="FINISH-SAFETY-Q1")

            self.assertFalse(result["accepted"])
            self.assertEqual(result["question"].question_id, "FINISH-SAFETY-Q1")
            self.assertIn("仍可连接", result["question"].blocker_summary)

    def test_download_confirmation_waits_for_action_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SessionStore.create(Path(directory) / "session.json", interaction_surface="text_menu")
            store.update_fields(current_state="DOWNLOAD-CONFIRM", selected_apps=["smarttube"])
            store.set_question(build_question("DOWNLOAD-CONFIRM", store.read()))
            engine = WorkflowEngine(store)

            result = engine.submit("1", question_id="DOWNLOAD-CONFIRM-Q1")

            self.assertTrue(result["accepted"])
            self.assertIsNone(result["question"])
            self.assertEqual(result["action_required"]["action_id"], "DOWNLOAD-ACTION")
            self.assertEqual(store.read()["current_state"], "DOWNLOAD-ACTION")
            self.assertIsNone(store.read()["pending_question"])
            self.assertEqual(store.read()["pending_action"]["status"], "pending")

            next_result = engine.record_action(
                "DOWNLOAD-ACTION",
                status="completed",
                evidence={"result": "2 files validated"},
            )
            self.assertEqual(next_result["question"].question_id, "DOWNLOAD-VERIFY-Q1")

    def test_failed_download_returns_to_confirmation_instead_of_claiming_completion(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SessionStore.create(Path(directory) / "session.json", interaction_surface="text_menu")
            store.update_fields(current_state="DOWNLOAD-CONFIRM", selected_apps=["smarttube"])
            store.set_question(build_question("DOWNLOAD-CONFIRM", store.read()))
            engine = WorkflowEngine(store)
            engine.submit("1", question_id="DOWNLOAD-CONFIRM-Q1")
            result = engine.record_action(
                "DOWNLOAD-ACTION", status="failed", evidence={"result": "HTTP 503"}
            )
            self.assertFalse(result["accepted"])
            self.assertEqual(result["question"].question_id, "DOWNLOAD-CONFIRM-Q1")
            self.assertIn("HTTP 503", render_question(result["question"]))

    def test_default_wallpaper_replaces_stale_custom_asset(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SessionStore.create(Path(directory) / "session.json", interaction_surface="text_menu")
            store.update_fields(
                current_state="WALLPAPER-UPLOAD",
                wallpaper_asset={"kind": "custom", "media_type": "image/png", "sha256": "deadbeef"},
            )
            store.set_question(build_question("WALLPAPER-UPLOAD", {}))
            result = WorkflowEngine(store).submit("2", question_id="WALLPAPER-UPLOAD-Q1")
            self.assertTrue(result["accepted"])
            self.assertEqual(store.read()["wallpaper_asset"]["kind"], "default")
            self.assertIn("默认壁纸", render_question(result["question"]))

    def test_home_risk_choice_requires_separate_execution_approval(self):
        question = build_question("LAUNCHER-RISK", {})
        home = next(option for option in question.options if option.value == "home_only")
        self.assertEqual(home.next_state, "HOME-CONFIRM")
        approval = build_question("HOME-CONFIRM", {"compatibility_matches": ["home_key"]})
        self.assertEqual(approval.kind, "explicit_consent")
        self.assertEqual(approval.options[0].next_state, "HOME-ACTION")

    def test_start_to_named_download_confirmation_is_reachable(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SessionStore.create(Path(directory) / "session.json", interaction_surface="text_menu")
            engine = WorkflowEngine(store)
            precheck = make_precheck_result(
                adb_available=True,
                adb_version="1.0.41",
                devices=(),
                local_address="192.0.2.10",
                wifi_name="redacted",
            )
            question = engine.start(precheck)
            for answer in ("1", "1"):
                result = engine.submit(answer, question_id=question.question_id)
                self.assertTrue(result["accepted"], result.get("error"))
                question = result["question"]
            self.assertIsNone(question)
            result = engine.record_action(
                "PASSIVE-DISCOVERY-ACTION",
                status="completed",
                evidence={"result": "0 个候选设备", "devices": [], "rows": []},
            )
            question = result["question"]
            for answer in ("2", "IP: 192.0.2.20", "1"):
                result = engine.submit(answer, question_id=question.question_id)
                self.assertTrue(result["accepted"], result.get("error"))
                question = result["question"]
            self.assertIsNone(question)
            result = engine.record_action(
                "CONNECT-ACTION",
                status="completed",
                evidence={"result": "ADB 已连接", "target_serial": "192.0.2.20:5555"},
            )
            question = result["question"]
            result = engine.submit("1", question_id=question.question_id)
            self.assertEqual(result["action_required"]["action_id"], "INSPECT-ACTION")
            result = engine.record_action(
                "INSPECT-ACTION",
                status="completed",
                evidence={"result": "只读盘点完成", "device_identity": {"model": "TV-1"}},
            )
            question = result["question"]
            result = engine.submit("1", question_id=question.question_id)
            question = result["question"]
            self.assertEqual(question.question_id, "APPS-Q1")
            result = engine.submit("1、2", question_id=question.question_id)
            self.assertTrue(result["accepted"])
            self.assertEqual(result["question"].question_id, "DOWNLOAD-CONFIRM-Q1")
            rendered = render_question(result["question"])
            self.assertIn("Clash Meta for Android 2.11.33", rendered)
            self.assertIn("SmartTube 32.10 Stable", rendered)

    def test_safe_exit_zero_is_accepted_without_state_gap(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SessionStore.create(Path(directory) / "session.json", interaction_surface="text_menu")
            engine = WorkflowEngine(store)
            question = engine.start({"rows": []})
            result = engine.submit("0", question_id=question.question_id)
            self.assertTrue(result["accepted"])
            self.assertIsNone(result["question"])
            self.assertEqual(store.read()["current_state"], "END-NO-ADB")

    def test_all_declared_scenarios_render_exactly_one_question(self):
        fixture = json.loads((ROOT / "tests" / "fixtures" / "dialogue-scenarios.json").read_text(encoding="utf-8"))
        for scenario in fixture["scenarios"]:
            with self.subTest(scenario=scenario["id"]):
                rendered = render_question(build_question(scenario["state"], scenario["context"]))
                self.assertEqual(rendered.count("问题 "), 1)


if __name__ == "__main__":
    unittest.main()

import json
import sys
import tempfile
import unittest
from pathlib import Path


PLUGIN_SCRIPTS = (
    Path(__file__).parents[1]
    / "plugins"
    / "android-tv-apps-helper"
    / "scripts"
)
sys.path.insert(0, str(PLUGIN_SCRIPTS))

from tv_helper.questions import AnswerError, Option, Question
from tv_helper.session import SessionStore


class SessionStoreTests(unittest.TestCase):
    def test_pending_action_cannot_be_cleared_overwritten_or_bypassed(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SessionStore.create(Path(directory) / "session.json", interaction_surface="text_menu")
            store.set_pending_action({"action_id": "DOWNLOAD-ACTION", "status": "pending"})
            with self.assertRaises((AnswerError, ValueError)):
                store.update_fields(pending_action=None)
            with self.assertRaises(AnswerError):
                store.update_fields(current_state="END")
            with self.assertRaises(AnswerError):
                store.set_question(
                    Question(
                        question_id="TASK-Q1",
                        state_id="TASK",
                        kind="single_choice",
                        prompt="任务？",
                        options=(Option("one", "一个", "END"),),
                    )
                )
    def test_schema_two_session_migrates_without_losing_target_or_plan(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "session.json"
            path.write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "host_platform": "codex",
                        "execution_context": "local_computer",
                        "interaction_surface": "text_menu",
                        "current_state": "S8",
                        "pending_question": None,
                        "target_serial": "192.0.2.20:5555",
                        "approved_plan": {"plan_id": "PLAN-old"},
                        "history": [],
                    }
                ),
                encoding="utf-8",
            )

            data = SessionStore(path).read()

            self.assertEqual(data["schema_version"], 3)
            self.assertEqual(data["target_serial"], "192.0.2.20:5555")
            self.assertEqual(data["approved_plan"]["plan_id"], "PLAN-old")
            self.assertTrue(data["approved_plan"]["requires_revalidation"])
            self.assertEqual(data["workflow_revision"], "v0.3.4")
            self.assertIn("summary_rows", data)

    def test_question_context_survives_invalid_answer(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SessionStore.create(
                Path(directory) / "session.json",
                interaction_surface="text_menu",
            )
            question = Question(
                question_id="S2-Q1",
                state_id="S2",
                kind="single_choice",
                prompt="下一步怎么处理？",
                options=(Option("retry", "重新检查", "S2"),),
                previous_result_summary="没有发现设备",
                blocker_summary="ADB 尚未连接",
                remediation_guidance=("打开电视网络调试。",),
                summary_rows=({"status": "attention", "item": "设备", "result": "0 台"},),
            )
            store.set_question(question)

            with self.assertRaises(AnswerError):
                store.answer("继续", submitted_question_id="S2-Q1")

            saved = store.read()["pending_question"]
            self.assertEqual(saved["previous_result_summary"], "没有发现设备")
            self.assertEqual(saved["blocker_summary"], "ADB 尚未连接")
            self.assertEqual(saved["attempts"], 1)

    def test_pending_question_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SessionStore.create(
                Path(directory) / "session.json",
                interaction_surface="text_menu",
            )
            first = Question(
                question_id="S2-Q1",
                state_id="S2",
                kind="single_choice",
                prompt="先回答这一题",
                options=(Option("retry", "重试", "S2"),),
            )
            second = Question(
                question_id="S5-Q1",
                state_id="S5",
                kind="single_choice",
                prompt="不应覆盖",
                options=(Option("apps", "选择应用", "S6"),),
            )
            store.set_question(first)

            with self.assertRaises(AnswerError):
                store.set_question(second)

            self.assertEqual(store.read()["pending_question"]["question_id"], "S2-Q1")

    def test_same_question_id_cannot_replace_prompt_or_options(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SessionStore.create(Path(directory) / "session.json", interaction_surface="text_menu")
            original = Question(
                question_id="LOCK-Q1",
                state_id="LOCK",
                kind="single_choice",
                prompt="原问题",
                options=(Option("stay", "保留", "LOCK"),),
            )
            replacement = Question(
                question_id="LOCK-Q1",
                state_id="OTHER",
                kind="single_choice",
                prompt="替换问题",
                options=(Option("escape", "越过", "END"),),
            )
            store.set_question(original)
            with self.assertRaises(AnswerError):
                store.set_question(replacement)
            self.assertEqual(store.read()["pending_question"]["prompt"], "原问题")

    def test_current_state_cannot_change_while_question_is_pending(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SessionStore.create(Path(directory) / "session.json", interaction_surface="text_menu")
            store.set_question(
                Question(
                    question_id="LOCK-Q1",
                    state_id="LOCK",
                    kind="single_choice",
                    prompt="原问题",
                    options=(Option("stay", "保留", "LOCK"),),
                )
            )
            with self.assertRaises(AnswerError):
                store.update_fields(current_state="OTHER")
            self.assertEqual(store.read()["current_state"], "LOCK")
    def test_invalid_answer_preserves_pending_question_and_state(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SessionStore.create(
                Path(directory) / "session.json",
                interaction_surface="text_menu",
            )
            question = Question(
                question_id="S4-Q1",
                state_id="S4",
                kind="single_choice",
                prompt="确认目标电视？",
                options=(Option("confirm_tv", "确认电视", "S5"),),
            )
            store.set_question(question)

            with self.assertRaises(AnswerError):
                store.answer("你决定")

            saved = json.loads(store.path.read_text(encoding="utf-8"))
            self.assertEqual(saved["current_state"], "S4")
            self.assertEqual(saved["pending_question"]["question_id"], "S4-Q1")
            self.assertEqual(saved["pending_question"]["attempts"], 1)

    def test_valid_answer_advances_and_clears_pending_question(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SessionStore.create(
                Path(directory) / "session.json",
                interaction_surface="structured_form",
            )
            store.set_question(
                Question(
                    question_id="S0-Q1",
                    state_id="S0",
                    kind="single_choice",
                    prompt="开始？",
                    options=(Option("start_check", "开始检查", "S1"),),
                )
            )

            answer = store.answer("1", submitted_question_id="S0-Q1")

            saved = json.loads(store.path.read_text(encoding="utf-8"))
            self.assertEqual(answer.value, "start_check")
            self.assertEqual(saved["current_state"], "S1")
            self.assertIsNone(saved["pending_question"])
            self.assertEqual(saved["history"][-1]["question_id"], "S0-Q1")
            self.assertFalse(store.path.with_suffix(".json.tmp").exists())


if __name__ == "__main__":
    unittest.main()

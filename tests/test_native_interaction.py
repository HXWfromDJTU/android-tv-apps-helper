import tempfile
import unittest
from pathlib import Path


PLUGIN_SCRIPTS = (
    Path(__file__).parents[1]
    / "plugins"
    / "android-tv-apps-helper"
    / "scripts"
)
import sys

sys.path.insert(0, str(PLUGIN_SCRIPTS))

from tv_helper.presentation import build_host_presentation
from tv_helper.questions import AnswerError, Option, Question
from tv_helper.session import SessionStore
from tv_helper.workflow import build_question


class NativeInteractionTests(unittest.TestCase):
    def test_ask_user_question_platforms_share_valid_four_option_schema(self):
        question = build_question("PRECHECK_WIFI", {"precheck": {"rows": ()}})
        for platform in ("claude", "workbuddy", "doubao-work"):
            with self.subTest(platform=platform), tempfile.TemporaryDirectory() as directory:
                store = SessionStore.create(
                    Path(directory) / "session.json",
                    interaction_surface="auto",
                    host_platform=platform,
                )
                presentation = build_host_presentation(question, store.read())
                tool_question = presentation["tool_input"]["questions"][0]
                self.assertEqual(presentation["mode"], "native_required")
                self.assertEqual(presentation["tool_name"], "AskUserQuestion")
                self.assertEqual(len(tool_question["options"]), 4)
                self.assertFalse(tool_question["multiSelect"])
                self.assertTrue(presentation["presentation_id"].startswith("PRES-"))

    def test_auto_surface_starts_with_required_workbuddy_native_question(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SessionStore.create(
                Path(directory) / "session.json",
                interaction_surface="auto",
                host_platform="workbuddy",
            )
            question = build_question(
                "PRECHECK_WIFI",
                {
                    "precheck": {
                        "rows": (
                            {"status": "attention", "item": "ADB 工具", "result": "未找到"},
                            {"status": "completed", "item": "本机网络", "result": "192.0.2.10"},
                        )
                    }
                },
            )
            store.update_fields(current_state="PRECHECK_WIFI")
            store.set_question(question)

            data = store.read()
            presentation = build_host_presentation(question, data)

            self.assertEqual(data["interaction_surface"], "structured_form")
            self.assertEqual(data["interaction_surface_requested"], "auto")
            self.assertEqual(presentation["mode"], "native_required")
            self.assertEqual(presentation["tool_name"], "AskUserQuestion")
            tool_question = presentation["tool_input"]["questions"][0]
            self.assertIn("ADB 工具：未找到", tool_question["question"])
            self.assertLessEqual(len(tool_question["header"]), 12)
            self.assertEqual(len(tool_question["options"]), 4)
            self.assertFalse(tool_question["multiSelect"])
            self.assertIn("| 状态 | 项目 | 结果 | 依据 |", presentation["context_markdown"])
            self.assertIn("当前阻塞", presentation["context_markdown"])
            self.assertEqual(
                presentation["answer_value_map"]["安全退出"],
                "safe_exit",
            )

    def test_native_tool_failure_preserves_question_and_records_text_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SessionStore.create(
                Path(directory) / "session.json",
                interaction_surface="auto",
                host_platform="codex",
            )
            question = Question(
                question_id="TOOL-Q1",
                state_id="TOOL",
                kind="single_choice",
                prompt="请选择。",
                options=(
                    Option("one", "第一项", "END"),
                    Option("two", "第二项", "END"),
                    Option("safe_exit", "安全退出", "END"),
                ),
            )
            store.update_fields(current_state="TOOL")
            store.set_question(question)
            native = build_host_presentation(question, store.read())

            store.record_surface_failure(
                "native_tool_not_exposed",
                detail="request_user_input is unavailable in the current execution mode",
                question_id=question.question_id,
                presentation_id=native["presentation_id"],
                tool_name=native["tool_name"],
            )

            saved = store.read()
            presentation = build_host_presentation(question, saved)
            self.assertEqual(saved["interaction_surface"], "text_menu")
            self.assertEqual(saved["pending_question"]["question_id"], "TOOL-Q1")
            self.assertEqual(
                saved["interaction_capabilities"]["fallback_reason"],
                "native_tool_not_exposed",
            )
            self.assertEqual(presentation["mode"], "text_fallback")
            self.assertEqual(
                presentation["fallback_reason"],
                "native_tool_not_exposed",
            )
            self.assertIn("原生选择组件", presentation["rendered"])

    def test_codex_four_choice_question_falls_back_instead_of_calling_invalid_schema(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SessionStore.create(
                Path(directory) / "session.json",
                interaction_surface="structured_form",
                host_platform="codex",
            )
            question = build_question("PRECHECK_WIFI", {"precheck": {"rows": ()}})

            presentation = build_host_presentation(question, store.read())

            self.assertEqual(presentation["mode"], "text_fallback")
            self.assertEqual(presentation["fallback_reason"], "question_not_native_compatible")

    def test_codex_three_choice_question_uses_request_user_input_when_exposed(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SessionStore.create(
                Path(directory) / "session.json",
                interaction_surface="structured_form",
                host_platform="codex",
            )
            question = Question(
                question_id="THREE-Q1",
                state_id="THREE",
                kind="single_choice",
                prompt="请选择下一步。",
                options=(
                    Option("one", "第一项", "END", recommended=True),
                    Option("two", "第二项", "END"),
                    Option("safe_exit", "安全退出", "END"),
                ),
                previous_result_summary="已完成检查。",
                blocker_summary="等待选择。",
            )

            presentation = build_host_presentation(question, store.read())

            self.assertEqual(presentation["mode"], "native_required")
            self.assertEqual(presentation["tool_name"], "request_user_input")
            tool_question = presentation["tool_input"]["questions"][0]
            self.assertEqual(tool_question["id"], "three_q1")
            self.assertEqual(len(tool_question["options"]), 3)
            self.assertEqual(tool_question["options"][0]["label"], "第一项（推荐）")
            self.assertEqual(presentation["answer_value_map"]["第一项"], "one")
            self.assertEqual(presentation["answer_value_map"]["第一项（推荐）"], "one")
            self.assertNotIn("multiSelect", tool_question)

    def test_call_failure_falls_back_only_for_current_question(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SessionStore.create(
                Path(directory) / "session.json",
                interaction_surface="auto",
                host_platform="workbuddy",
            )
            first = build_question("PRECHECK_WIFI", {"precheck": {"rows": ()}})
            store.update_fields(current_state="PRECHECK_WIFI")
            store.set_question(first)
            native = build_host_presentation(first, store.read())
            store.record_surface_failure(
                "native_tool_call_failed",
                detail="AskUserQuestion returned a temporary host error",
                question_id=first.question_id,
                presentation_id=native["presentation_id"],
                tool_name=native["tool_name"],
            )

            failed_presentation = build_host_presentation(first, store.read())
            self.assertEqual(failed_presentation["mode"], "text_fallback")
            self.assertEqual(store.read()["interaction_surface"], "structured_form")

            store.answer("safe_exit", submitted_question_id=first.question_id)
            next_question = Question(
                question_id="NEXT-Q1",
                state_id="NEXT",
                kind="single_choice",
                prompt="下一题？",
                options=(
                    Option("yes", "继续", "END"),
                    Option("safe_exit", "安全退出", "END"),
                ),
            )
            presentation = build_host_presentation(next_question, store.read())
            self.assertEqual(presentation["mode"], "native_required")

    def test_temporary_failure_retries_when_same_question_id_is_created_again(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SessionStore.create(
                Path(directory) / "session.json",
                interaction_surface="auto",
                host_platform="workbuddy",
            )
            first = build_question("PRECHECK_WIFI", {"precheck": {"rows": ()}})
            store.update_fields(current_state="PRECHECK_WIFI")
            store.set_question(first)
            native = build_host_presentation(first, store.read())
            store.record_surface_failure(
                "native_tool_render_failed",
                detail="The host card did not become visible",
                question_id=first.question_id,
                presentation_id=native["presentation_id"],
                tool_name=native["tool_name"],
            )

            store.answer("different_wifi", submitted_question_id=first.question_id)
            repeated = build_question("PRECHECK_WIFI", {"precheck": {"rows": ()}})
            store.set_question(repeated)

            presentation = build_host_presentation(repeated, store.read())
            self.assertEqual(presentation["mode"], "native_required")
            self.assertNotEqual(presentation["presentation_id"], native["presentation_id"])
            self.assertEqual(presentation["presentation_id"], build_host_presentation(repeated, store.read())["presentation_id"])
            with self.assertRaises(AnswerError):
                store.record_surface_failure(
                    "native_tool_render_failed",
                    detail="Late failure from earlier instance of this question",
                    question_id=first.question_id,
                    presentation_id=native["presentation_id"],
                    tool_name=native["tool_name"],
                )
            self.assertEqual(build_host_presentation(repeated, store.read())["mode"], "native_required")
            self.assertIn("last_failure", store.read()["interaction_capabilities"])

    def test_stale_surface_failure_cannot_downgrade_a_new_question(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SessionStore.create(
                Path(directory) / "session.json",
                interaction_surface="auto",
                host_platform="workbuddy",
            )
            first = build_question("PRECHECK_WIFI", {"precheck": {"rows": ()}})
            store.update_fields(current_state="PRECHECK_WIFI")
            store.set_question(first)
            old_presentation = build_host_presentation(first, store.read())
            store.answer("same_wifi", submitted_question_id=first.question_id)
            second = build_question("PRECHECK_ADB", {"precheck": {"rows": ()}})
            store.set_question(second)

            with self.assertRaises(AnswerError):
                store.record_surface_failure(
                    "native_tool_render_failed",
                    detail="Late callback from the previous card",
                    question_id=first.question_id,
                    presentation_id=old_presentation["presentation_id"],
                    tool_name=old_presentation["tool_name"],
                )

            saved = store.read()
            self.assertEqual(saved["pending_question"]["question_id"], second.question_id)
            self.assertEqual(saved["interaction_surface"], "structured_form")

    def test_incompatible_question_falls_back_for_one_turn_without_disabling_native(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SessionStore.create(
                Path(directory) / "session.json",
                interaction_surface="auto",
                host_platform="workbuddy",
            )
            question = build_question("TASK", {})

            presentation = build_host_presentation(question, store.read())

            self.assertEqual(presentation["mode"], "text_fallback")
            self.assertEqual(
                presentation["fallback_reason"],
                "question_not_native_compatible",
            )
            self.assertEqual(store.read()["interaction_surface"], "structured_form")


if __name__ == "__main__":
    unittest.main()

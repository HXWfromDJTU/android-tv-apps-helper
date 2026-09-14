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

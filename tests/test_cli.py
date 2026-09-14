import contextlib
import io
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

from tv_helper.cli import main


class CliTests(unittest.TestCase):
    def run_cli(self, arguments):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            exit_code = main(arguments)
        return exit_code, stdout.getvalue(), stderr.getvalue()

    def test_session_question_round_trip_emits_json(self):
        with tempfile.TemporaryDirectory() as directory:
            session = Path(directory) / "session.json"
            question = Path(directory) / "question.json"
            question.write_text(
                json.dumps(
                    {
                        "question_id": "S0-Q1",
                        "state_id": "S0",
                        "kind": "single_choice",
                        "prompt": "开始？",
                        "options": [
                            {
                                "value": "start_check",
                                "label": "开始检查",
                                "next_state": "S1",
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            code, output, _ = self.run_cli(
                ["init-session", str(session), "--surface", "text_menu"]
            )
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(output)["current_state"], "S0")

            code, output, _ = self.run_cli(
                ["set-question", str(session), "--question", str(question)]
            )
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(output)["pending_question"]["question_id"], "S0-Q1")

            code, output, _ = self.run_cli(
                [
                    "answer",
                    str(session),
                    "--question-id",
                    "S0-Q1",
                    "--value",
                    "1",
                ]
            )
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(output)["current_state"], "S1")

    def test_invalid_answer_returns_nonzero_without_advancing(self):
        with tempfile.TemporaryDirectory() as directory:
            session = Path(directory) / "session.json"
            question = Path(directory) / "question.json"
            question.write_text(
                json.dumps(
                    {
                        "question_id": "S0-Q1",
                        "state_id": "S0",
                        "kind": "single_choice",
                        "prompt": "开始？",
                        "options": [
                            {
                                "value": "start_check",
                                "label": "开始检查",
                                "next_state": "S1",
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            self.run_cli(["init-session", str(session), "--surface", "text_menu"])
            self.run_cli(["set-question", str(session), "--question", str(question)])

            code, _, error = self.run_cli(
                ["answer", str(session), "--question-id", "S0-Q1", "--value", "随便"]
            )

            self.assertEqual(code, 2)
            self.assertIn("明确", error)
            self.assertEqual(
                json.loads(session.read_text(encoding="utf-8"))["current_state"],
                "S0",
            )


if __name__ == "__main__":
    unittest.main()

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

    def test_session_records_supported_host_and_local_execution_context(self):
        with tempfile.TemporaryDirectory() as directory:
            session = Path(directory) / "session.json"

            code, output, error = self.run_cli(
                [
                    "init-session",
                    str(session),
                    "--surface",
                    "text_menu",
                    "--host-platform",
                    "doubao-work",
                    "--execution-context",
                    "local_computer",
                ]
            )

            self.assertEqual((code, error), (0, ""))
            saved = json.loads(output)
            self.assertEqual(saved["host_platform"], "doubao-work")
            self.assertEqual(saved["execution_context"], "local_computer")
            self.assertEqual(saved["current_state"], "S0")

    def test_doubao_cloud_context_is_rejected_before_session_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            session = Path(directory) / "session.json"

            code, _, error = self.run_cli(
                [
                    "init-session",
                    str(session),
                    "--surface",
                    "text_menu",
                    "--host-platform",
                    "doubao-work",
                    "--execution-context",
                    "cloud_computer",
                ]
            )

            self.assertEqual(code, 2)
            self.assertIn("local_computer", error)
            self.assertFalse(session.exists())

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

    def test_catalog_lists_only_eligible_downloads(self):
        catalog = (
            Path(__file__).parents[1]
            / "plugins"
            / "android-tv-apps-helper"
            / "catalog"
            / "apps.json"
        )

        code, output, error = self.run_cli(
            ["catalog", "--catalog", str(catalog), "--eligible"]
        )

        self.assertEqual((code, error), (0, ""))
        self.assertEqual(
            [item["id"] for item in json.loads(output)],
            ["clash-meta", "smarttube"],
        )

    def test_install_plan_requires_explicit_approval_before_install(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            session = root / "session.json"
            apk = root / "sample.apk"
            plan = root / "plan.json"
            import hashlib
            import zipfile

            with zipfile.ZipFile(apk, "w") as archive:
                archive.writestr("AndroidManifest.xml", b"manifest")
            digest = hashlib.sha256(apk.read_bytes()).hexdigest()
            self.run_cli(["init-session", str(session), "--surface", "text_menu"])

            code, output, error = self.run_cli(
                [
                    "plan-install",
                    str(session),
                    "--app-id",
                    "sample",
                    "--serial",
                    "tv:5555",
                    "--apk",
                    str(apk),
                    "--sha256",
                    digest,
                    "--out",
                    str(plan),
                ]
            )
            self.assertEqual((code, error), (0, ""))
            self.assertEqual(json.loads(output)["status"], "planned")

            code, _, error = self.run_cli(
                [
                    "approve-install",
                    str(session),
                    "--plan",
                    str(plan),
                    "--confirmation",
                    "yes",
                ]
            )
            self.assertEqual(code, 2)
            self.assertIn("confirm_install", error)
            self.assertIsNone(json.loads(session.read_text())["approved_plan"])

            code, output, error = self.run_cli(
                [
                    "approve-install",
                    str(session),
                    "--plan",
                    str(plan),
                    "--confirmation",
                    "confirm_install",
                ]
            )
            self.assertEqual((code, error), (0, ""))
            self.assertEqual(json.loads(output)["approved_plan"]["status"], "approved")


if __name__ == "__main__":
    unittest.main()

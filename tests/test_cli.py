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
from tv_helper.session import SessionStore
from tv_helper.workflow import build_question


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

    def test_workflow_commands_generate_and_retain_the_fixed_first_question(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            session = root / "session.json"
            precheck = root / "precheck.json"
            precheck.write_text(
                json.dumps(
                    {
                        "status": "attention",
                        "blocker": "没有发现设备",
                        "rows": [{"status": "attention", "item": "设备", "result": "0 台"}],
                        "active_scan_performed": False,
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            self.run_cli(["init-session", str(session), "--surface", "text_menu"])

            code, output, error = self.run_cli(
                ["workflow-start", str(session), "--precheck", str(precheck)]
            )

            self.assertEqual((code, error), (0, ""))
            started = json.loads(output)
            self.assertEqual(started["question"]["question_id"], "PRECHECK-WIFI-Q1")
            self.assertIn("| 状态 |", started["rendered"])

            code, output, error = self.run_cli(
                [
                    "workflow-answer",
                    str(session),
                    "--question-id",
                    "PRECHECK-WIFI-Q1",
                    "--value",
                    "继续",
                ]
            )
            self.assertEqual((code, error), (2, ""))
            rejected = json.loads(output)
            self.assertFalse(rejected["accepted"])
            self.assertEqual(rejected["question"]["question_id"], "PRECHECK-WIFI-Q1")

    def test_workflow_action_result_requires_evidence_and_emits_next_question(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            session = root / "session.json"
            evidence = root / "evidence.json"
            self.run_cli(["init-session", str(session), "--surface", "text_menu"])
            store = SessionStore(session)
            store.update_fields(current_state="DOWNLOAD-CONFIRM", selected_apps=["smarttube"])
            store.set_question(build_question("DOWNLOAD-CONFIRM", store.read()))
            code, output, error = self.run_cli(
                ["workflow-answer", str(session), "--question-id", "DOWNLOAD-CONFIRM-Q1", "--value", "1"]
            )
            self.assertEqual((code, error), (0, ""))
            self.assertEqual(json.loads(output)["action_required"]["action_id"], "DOWNLOAD-ACTION")
            evidence.write_text(json.dumps({"result": "下载和身份校验通过"}), encoding="utf-8")
            code, output, error = self.run_cli(
                [
                    "workflow-action-result", str(session), "--action-id", "DOWNLOAD-ACTION",
                    "--status", "completed", "--evidence", str(evidence),
                ]
            )
            self.assertEqual((code, error), (0, ""))
            self.assertEqual(json.loads(output)["question"]["question_id"], "DOWNLOAD-VERIFY-Q1")

    def test_prepare_device_context_persists_model_guide_and_highlighted_risks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            session = root / "session.json"
            identity = root / "identity.json"
            identity.write_text(
                json.dumps({"manufacturer": "Other", "model": "TV-1"}),
                encoding="utf-8",
            )
            self.run_cli(["init-session", str(session), "--surface", "text_menu"])
            data_root = Path(__file__).parents[1] / "plugins" / "android-tv-apps-helper" / "data"
            code, output, error = self.run_cli(
                [
                    "prepare-device-context", str(session), "--identity", str(identity),
                    "--guides", str(data_root / "device-guides.json"),
                    "--compatibility", str(data_root / "compatibility.json"),
                ]
            )
            self.assertEqual((code, error), (0, ""))
            result = json.loads(output)
            self.assertEqual(result["guide"]["id"], "generic-android-tv")
            saved = SessionStore(session).read()
            self.assertEqual(saved["device_identity"]["model"], "TV-1")
            self.assertEqual(saved["compatibility_matches"][0]["risk"], "high_risk")

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

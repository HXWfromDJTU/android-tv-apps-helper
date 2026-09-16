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

    def test_session_init_and_show_emit_json_without_raw_state_mutators(self):
        with tempfile.TemporaryDirectory() as directory:
            session = Path(directory) / "session.json"
            code, output, _ = self.run_cli(
                ["init-session", str(session), "--surface", "text_menu"]
            )
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(output)["current_state"], "S0")

            code, output, _ = self.run_cli(["show-session", str(session)])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(output)["current_state"], "S0")

            with self.assertRaises(SystemExit):
                self.run_cli(["set-question", str(session)])

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
            self.assertIn("| 状态 |", started["presentation"]["context_markdown"])
            self.assertEqual(started["presentation"]["mode"], "native_required")

            code, output, error = self.run_cli(
                [
                    "workflow-answer",
                    str(session),
                    "--question-id",
                    "PRECHECK-WIFI-Q1",
                    "--presentation-id",
                    started["presentation"]["presentation_id"],
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
            from tv_helper.presentation import build_host_presentation
            view = build_host_presentation(build_question("DOWNLOAD-CONFIRM", store.read()), store.read())
            approve = next(option.value for option in build_question("DOWNLOAD-CONFIRM", store.read()).options if option.next_state == "DOWNLOAD-ACTION")
            code, output, error = self.run_cli(
                ["workflow-native-answer", str(session), "--question-id", "DOWNLOAD-CONFIRM-Q1", "--presentation-id", view["presentation_id"], "--value", approve]
            )
            self.assertEqual((code, error), (0, ""))
            self.assertEqual(json.loads(output)["action_required"]["action_id"], "DOWNLOAD-ACTION")
            evidence.write_text(
                json.dumps(
                    {
                        "result": "下载和身份校验通过",
                        "files": [
                            {
                                "app_id": "smarttube", "path": "/tmp/smarttube.apk",
                                "url": "https://github.com/HXWfromDJTU/android-tv-apps-helper/releases/download/v0.1.0/SmartTube_stable_32.10_armeabi-v7a.apk",
                                "size": 25001470, "sha256": "61e335a9816621feaa0b2aacdc17f68e652773fe33304ec091b14fac36f95025",
                                "package": "org.smarttube.stable", "version_name": "32.10",
                                "version_code": 1, "min_sdk": 21,
                                "abi": "armeabi-v7a", "signing_sha256": "b" * 64, "exit_code": 0,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
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

    def test_raw_answer_command_is_not_exposed(self):
        with tempfile.TemporaryDirectory() as directory:
            session = Path(directory) / "session.json"
            self.run_cli(["init-session", str(session), "--surface", "text_menu"])
            with self.assertRaises(SystemExit):
                self.run_cli(
                    ["answer", str(session), "--question-id", "S0-Q1", "--value", "随便"]
                )
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
            ["clash-meta", "smarttube", "dangbei-market", "emotn-ui"],
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
            store = SessionStore(session)
            store.update_fields(
                target_serial="tv:5555",
                verified_downloads=[{"app_id": "sample", "path": str(apk), "sha256": digest}],
            )

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
            self.assertEqual(json.loads(session.read_text())["approved_plan"]["status"], "planned")

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

import tempfile
import unittest
from pathlib import Path

from tv_helper.questions import AnswerError
from tv_helper.session import SessionStore
from tv_helper.workflow import WorkflowEngine, build_question
from tv_helper.evidence import validate_action_evidence


class ActionEvidenceTests(unittest.TestCase):
    def _pending(self, state, answer="1"):
        directory = tempfile.TemporaryDirectory()
        store = SessionStore.create(Path(directory.name) / "session.json", interaction_surface="text_menu")
        store.update_fields(current_state=state, target_serial="tv:5555")
        store.set_question(build_question(state, store.read()))
        result = WorkflowEngine(store).submit(answer, question_id=store.read()["history"][-1]["question_id"] if False else build_question(state, store.read()).question_id)
        return directory, store, WorkflowEngine(store), result

    def test_trust_me_cannot_complete_mutating_actions(self):
        for action_id in ("DOWNLOAD-ACTION", "INSTALL-ACTION", "HOME-ACTION", "WALLPAPER-ACTION"):
            with self.subTest(action=action_id):
                directory = tempfile.TemporaryDirectory()
                self.addCleanup(directory.cleanup)
                store = SessionStore.create(Path(directory.name) / "session.json", interaction_surface="text_menu")
                store.set_pending_action({"action_id": action_id, "status": "pending", "target_serial": "tv:5555"})
                with self.assertRaises(AnswerError):
                    WorkflowEngine(store).record_action(action_id, status="completed", evidence={"result": "trust me"})
                self.assertEqual(store.read()["pending_action"]["action_id"], action_id)

    def test_finish_check_requires_explicit_boolean_reachability_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SessionStore.create(Path(directory) / "session.json", interaction_surface="text_menu")
            store.update_fields(current_state="FINISH-SAFETY", target_serial="tv:5555")
            question = build_question("FINISH-SAFETY", store.read())
            store.set_question(question)
            WorkflowEngine(store).submit("1", question_id=question.question_id)
            with self.assertRaises(AnswerError):
                WorkflowEngine(store).record_action(
                    "FINISH-CHECK", status="completed", evidence={"result": "trust me", "command": ["adb", "devices"]}
                )
            self.assertNotEqual(store.read()["current_state"], "END")

    def test_device_inspection_requires_session_start_home_for_safe_recovery(self):
        with self.assertRaisesRegex(ValueError, "current_home"):
            validate_action_evidence(
                "INSPECT-ACTION",
                status="completed",
                pending={"target_serial": "tv:5555"},
                evidence={
                    "result": "只读盘点完成",
                    "target_serial": "tv:5555",
                    "commands": [["adb", "-s", "tv:5555", "shell", "getprop"]],
                    "exit_code": 0,
                    "device_identity": {
                        "manufacturer": "Example",
                        "model": "TV-1",
                        "android_version": "9",
                        "sdk": "28",
                        "abi": "armeabi-v7a",
                    },
                    "installed_apps": {},
                },
            )

    def test_restore_home_rejects_substring_identity_and_non_adb_verification(self):
        pending = {
            "target_serial": "tv:5555",
            "expected_initial_home": "com.vendor.home/.HomeActivity",
        }
        valid_command = ["adb", "-s", "tv:5555", "shell", "cmd", "package", "resolve-activity", "--brief", "-a", "android.intent.action.MAIN", "-c", "android.intent.category.HOME"]
        base = {
            "result": "ok",
            "target_serial": "tv:5555",
            "before_home": "com.oversea.aslauncher/.MainActivity",
            "after_home": "com.vendor.home/.HomeActivity",
            "verification_command": valid_command,
            "exit_code": 0,
            "initial_launcher_enabled": True,
            "initial_launcher_data_preserved": True,
        }
        invalid_cases = (
            ({**base, "after_home": "evil.prefix com.vendor.home/.HomeActivity suffix"}, "HOME"),
            ({**base, "verification_command": ["echo", "ok"]}, "验证命令"),
            ({**base, "verification_command": ["badadb", *valid_command[1:]]}, "验证命令"),
            ({**base, "verification_command": ["/tmp/adb", *valid_command[1:]]}, "ADB 路径"),
        )
        for evidence, message in invalid_cases:
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                validate_action_evidence(
                    "RESTORE-HOME-ACTION",
                    status="completed",
                    pending={**pending, "adb_path": "/trusted/platform-tools/adb"} if message == "ADB 路径" else pending,
                    evidence=evidence,
                )

    def test_completed_evidence_is_bound_to_the_approved_object(self):
        cases = [
            (
                "CONNECT-ACTION",
                {"candidate_ip": "192.168.1.20"},
                {"result": "ok", "target_serial": "192.168.1.99:5555", "endpoint": "192.168.1.20", "command": ["adb", "connect", "192.168.1.20"], "exit_code": 0, "output": "connected"},
            ),
            (
                "SCAN-ACTION",
                {"scan_approval": {"scope": ["192.168.1.0/24"], "ports": [5555]}},
                {"result": "ok", "scope": ["0.0.0.0/0"], "ports": [5555], "devices": [], "exit_code": 0},
            ),
            (
                "PASSIVE-DISCOVERY-ACTION",
                {},
                {"result": "ok", "commands": ["adb connect 192.168.1.20"], "precheck": {"rows": [{"item": "设备"}], "active_scan_performed": False}},
            ),
            (
                "EMOTN-LAUNCH-ACTION",
                {"target_serial": "tv:5555", "installed_apps": {"emotn-ui": "1.1.0.1"}},
                {"result": "ok", "target_serial": "tv:5555", "package": "evil.launcher", "foreground": "evil.launcher/.Main", "commands": [["adb"]], "exit_code": 0},
            ),
            (
                "HOME-ACTION",
                {"target_serial": "tv:5555", "expected_home_package": "com.oversea.aslauncher", "selected_actions": ["home_key"], "emotn_runtime": {"verified": True, "package": "com.oversea.aslauncher"}},
                {"result": "ok", "target_serial": "tv:5555", "before_home": "vendor.home", "after_home": "evil.launcher", "verification_command": ["adb"], "exit_code": 0},
            ),
            (
                "RESTORE-HOME-ACTION",
                {"target_serial": "tv:5555", "expected_initial_home": "com.vendor.home/.HomeActivity"},
                {"result": "ok", "target_serial": "tv:5555", "before_home": "com.oversea.aslauncher/.MainActivity", "after_home": "evil.launcher/.Home", "verification_command": ["adb"], "exit_code": 0, "initial_launcher_enabled": True, "initial_launcher_data_preserved": True},
            ),
            (
                "UPDATE-ACTION",
                {"host_platform": "workbuddy", "update_check": {"latest_version": "0.3.0", "release": {}}},
                {"result": "ok", "package_validation": {"skill_id": "android-tv-apps-helper", "version": "0.3.0", "platform": "workbuddy", "sha256": "0" * 64}, "installation_verified": True, "previous_version_preserved_until_verified": True},
            ),
        ]
        for action_id, pending, evidence in cases:
            with self.subTest(action=action_id), self.assertRaises(ValueError):
                validate_action_evidence(action_id, status="completed", evidence=evidence, pending=pending)

    def test_download_rejects_identity_that_differs_from_catalog_expectation(self):
        expected = {"app_id": "smarttube", "url": "https://good.invalid/app.apk", "size": 123, "sha256": "a" * 64, "package": "org.smarttube.stable", "version_name": "32.10"}
        actual = {**expected, "path": "/tmp/app.apk", "url": "https://evil.invalid/app.apk", "version_code": 1, "min_sdk": 21, "abi": "armeabi-v7a", "signing_sha256": "b" * 64, "exit_code": 0}
        with self.assertRaisesRegex(ValueError, "url"):
            validate_action_evidence(
                "DOWNLOAD-ACTION", status="completed",
                evidence={"result": "ok", "files": [actual]},
                pending={"selected_apps": ["smarttube"], "download_expectations": [expected]},
            )


if __name__ == "__main__":
    unittest.main()

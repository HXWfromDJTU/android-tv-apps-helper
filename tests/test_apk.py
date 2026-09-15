import hashlib
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


PLUGIN_SCRIPTS = (
    Path(__file__).parents[1]
    / "plugins"
    / "android-tv-apps-helper"
    / "scripts"
)
sys.path.insert(0, str(PLUGIN_SCRIPTS))

from tv_helper.apk import (
    ApkError,
    approve_plan,
    create_install_bundle_plan,
    create_install_plan,
    inspect_apk,
    install_approved,
)
from tv_helper.session import SessionStore


def make_apk(path: Path) -> str:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("AndroidManifest.xml", b"binary-manifest")
        archive.writestr("classes.dex", b"dex")
    return hashlib.sha256(path.read_bytes()).hexdigest()


class FakeRunner:
    def __init__(self):
        self.calls = []

    def install(self, serial, apk_path, *, state):
        self.calls.append((serial, apk_path, state))
        return "Success"


class ApkTests(unittest.TestCase):
    def test_approved_bundle_revalidates_and_installs_every_apk(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            session = SessionStore.create(root / "session.json", interaction_surface="text_menu")
            downloads = []
            for app_id in ("one", "two"):
                apk = root / f"{app_id}.apk"
                digest = make_apk(apk)
                downloads.append({"app_id": app_id, "path": str(apk), "sha256": digest})
            plan = create_install_bundle_plan(serial="tv:5555", verified_downloads=downloads)
            approve_plan(session, plan, confirmation="confirm_install")
            runner = FakeRunner()

            result = install_approved(session, runner, plan, device_state="device")

            self.assertEqual([item["app_id"] for item in result], ["one", "two"])
            self.assertTrue(all(item["plan_id"] == plan["plan_id"] for item in result))
            self.assertEqual(len(runner.calls), 2)

    def test_inspection_rejects_non_zip_and_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            bad = Path(directory) / "bad.apk"
            bad.write_text("not an apk", encoding="utf-8")
            with self.assertRaisesRegex(ApkError, "ZIP"):
                inspect_apk(bad)

            good = Path(directory) / "good.apk"
            make_apk(good)
            with self.assertRaisesRegex(ApkError, "SHA-256"):
                inspect_apk(good, expected_sha256="0" * 64)

    def test_unapproved_plan_cannot_install(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            session = SessionStore.create(root / "session.json", interaction_surface="text_menu")
            apk = root / "app.apk"
            digest = make_apk(apk)
            plan = create_install_plan(
                app_id="smarttube",
                serial="192.168.31.170:5555",
                apk_path=apk,
                expected_sha256=digest,
            )
            runner = FakeRunner()

            with self.assertRaisesRegex(ApkError, "approved"):
                install_approved(session, runner, plan, device_state="device")
            self.assertEqual(runner.calls, [])

    def test_approved_plan_is_bound_to_serial_and_digest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            session = SessionStore.create(root / "session.json", interaction_surface="text_menu")
            apk = root / "app.apk"
            digest = make_apk(apk)
            plan = create_install_plan(
                app_id="smarttube",
                serial="192.168.31.170:5555",
                apk_path=apk,
                expected_sha256=digest,
            )
            approve_plan(session, plan, confirmation="confirm_install")
            runner = FakeRunner()

            result = install_approved(session, runner, plan, device_state="device")

            self.assertEqual(result, "Success")
            self.assertEqual(runner.calls[0][0], "192.168.31.170:5555")
            saved = json.loads(session.path.read_text(encoding="utf-8"))
            self.assertEqual(saved["approved_plan"]["plan_id"], plan["plan_id"])

    def test_plan_id_cannot_be_reused_after_plan_body_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            session = SessionStore.create(root / "session.json", interaction_surface="text_menu")
            apk = root / "app.apk"
            digest = make_apk(apk)
            plan = create_install_plan(
                app_id="smarttube",
                serial="192.168.31.170:5555",
                apk_path=apk,
                expected_sha256=digest,
            )
            plan["app_id"] = "different-app"

            with self.assertRaisesRegex(ApkError, "changed"):
                approve_plan(session, plan, confirmation="confirm_install")
            self.assertIsNone(session.read()["approved_plan"])

    def test_migrated_plan_requires_revalidation_before_approval_or_install(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            session = SessionStore.create(root / "session.json", interaction_surface="text_menu")
            apk = root / "app.apk"
            digest = make_apk(apk)
            plan = create_install_plan(
                app_id="smarttube",
                serial="192.0.2.20:5555",
                apk_path=apk,
                expected_sha256=digest,
            )
            stale = {**plan, "status": "approved", "requires_revalidation": True}
            session.set_approved_plan(stale)
            runner = FakeRunner()
            with self.assertRaisesRegex(ApkError, "revalidation"):
                install_approved(session, runner, stale, device_state="device")
            with self.assertRaisesRegex(ApkError, "revalidation"):
                approve_plan(session, stale, confirmation="confirm_install")
            self.assertEqual(runner.calls, [])


if __name__ == "__main__":
    unittest.main()

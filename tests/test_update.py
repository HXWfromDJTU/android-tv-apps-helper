import json
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from tv_helper.update import (
    UpdateStateStore,
    compare_stable_versions,
    record_update_decline,
    should_prompt_update,
    select_latest_stable_release,
    validate_update_package,
)


class UpdateTests(unittest.TestCase):
    def test_latest_release_selection_ignores_drafts_and_prereleases(self):
        releases = [
            {"tag_name": "v0.4.0-rc.1", "draft": False, "prerelease": True, "assets": []},
            {"tag_name": "v0.3.0", "draft": False, "prerelease": False, "assets": [{"name": "SHA256SUMS"}]},
            {"tag_name": "v0.5.0", "draft": True, "prerelease": False, "assets": []},
        ]
        self.assertEqual(select_latest_stable_release(releases)["version"], "0.3.0")

    def test_update_zip_requires_expected_skill_platform_version_and_hash(self):
        import hashlib
        import zipfile

        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / "candidate.zip"
            content = "---\nname: android-tv-apps-helper\nversion: 0.3.0\nplatform: workbuddy\n---\n"
            with zipfile.ZipFile(package, "w") as archive:
                archive.writestr("android-tv-apps-helper/SKILL.md", content)
            digest = hashlib.sha256(package.read_bytes()).hexdigest()
            result = validate_update_package(
                package,
                expected_sha256=digest,
                expected_version="0.3.0",
                expected_platform="workbuddy",
            )
            self.assertEqual(result["skill_id"], "android-tv-apps-helper")
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                validate_update_package(
                    package,
                    expected_sha256="0" * 64,
                    expected_version="0.3.0",
                    expected_platform="workbuddy",
                )
    def test_stable_semver_comparison_ignores_prerelease_by_default(self):
        self.assertEqual(compare_stable_versions("0.2.0", "0.3.0"), 1)
        self.assertEqual(compare_stable_versions("0.3.0", "0.3.0"), 0)
        self.assertIsNone(compare_stable_versions("0.2.0", "0.3.0-rc.1"))

    def test_decline_suppresses_every_update_for_twenty_four_hours(self):
        now = datetime(2026, 9, 15, 8, 0, tzinfo=UTC)
        state = record_update_decline({}, "0.3.0", now=now)

        self.assertFalse(
            should_prompt_update("0.2.0", "0.4.0", state, now=now + timedelta(hours=23, minutes=59))
        )
        self.assertTrue(
            should_prompt_update("0.2.0", "0.4.0", state, now=now + timedelta(hours=24, minutes=1))
        )

    def test_state_store_survives_skill_directory_replacement(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_path = root / "stable-user-data" / "update.json"
            store = UpdateStateStore(state_path)
            store.write({"snooze_until": "2026-09-16T08:00:00+00:00"})
            skill_dir = root / "installed-skill"
            skill_dir.mkdir()
            skill_dir.rmdir()

            self.assertEqual(
                UpdateStateStore(state_path).read()["snooze_until"],
                "2026-09-16T08:00:00+00:00",
            )


if __name__ == "__main__":
    unittest.main()

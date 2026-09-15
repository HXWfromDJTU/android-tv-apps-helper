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
)


class UpdateTests(unittest.TestCase):
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

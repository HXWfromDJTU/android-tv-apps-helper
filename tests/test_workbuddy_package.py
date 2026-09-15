import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).parents[1]
BUILDER = REPO_ROOT / "scripts" / "build_workbuddy_package.py"


class WorkBuddyPackageTests(unittest.TestCase):
    def test_builder_creates_a_self_contained_workbuddy_skill_zip(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "android-tv-apps-helper-workbuddy.zip"
            expected_version = json.loads(
                (
                    REPO_ROOT
                    / "plugins"
                    / "android-tv-apps-helper"
                    / "plugin.json"
                ).read_text(encoding="utf-8")
            )["version"]

            result = subprocess.run(
                [sys.executable, str(BUILDER), "--output", str(output)],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            metadata = json.loads(result.stdout)
            self.assertEqual(metadata["output"], str(output.resolve()))
            self.assertEqual(metadata["version"], expected_version)
            self.assertEqual(metadata["sha256"], self._sha256(output))

            with zipfile.ZipFile(output) as archive:
                names = set(archive.namelist())
                root = "android-tv-apps-helper/"
                required = {
                    root + "SKILL.md",
                    root + "references/interaction-contract.md",
                    root + "references/workflow.md",
                    root + "references/adb-operations.md",
                    root + "references/apk-policy.md",
                    root + "references/apps.json",
                    root + "references/THIRD_PARTY_NOTICES.md",
                    root + "scripts/tv-helper",
                    root + "scripts/tv_helper/adb.py",
                    root + "scripts/tv_helper/apk.py",
                    root + "scripts/tv_helper/catalog.py",
                    root + "scripts/tv_helper/cli.py",
                    root + "scripts/tv_helper/questions.py",
                    root + "scripts/tv_helper/session.py",
                }
                self.assertTrue(required.issubset(names), required - names)
                self.assertFalse(any(name.lower().endswith(".apk") for name in names))

                skill = archive.read(root + "SKILL.md").decode("utf-8")
                for field in (
                    "name: android-tv-apps-helper",
                    "display_name: Android TV Apps Helper",
                    "description_zh:",
                    "description_en:",
                    f"version: {expected_version}",
                    "author: SwainWong",
                    "allowed-tools: Bash",
                ):
                    self.assertIn(field, skill)
                self.assertIn("python3 scripts/tv-helper", skill)
                self.assertIn("references/apps.json", skill)
                self.assertNotIn("../../scripts", skill)
                self.assertNotIn("../../catalog", skill)

                executable = archive.getinfo(root + "scripts/tv-helper")
                self.assertEqual((executable.external_attr >> 16) & 0o111, 0o111)

    @staticmethod
    def _sha256(path: Path) -> str:
        import hashlib

        return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    unittest.main()

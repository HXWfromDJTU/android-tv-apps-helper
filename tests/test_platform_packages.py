import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).parents[1]
BUILDER = REPO_ROOT / "scripts" / "build_platform_packages.py"
PLATFORMS = ("workbuddy", "doubao-work", "claude")
ROOT = "android-tv-apps-helper/"
SHARED_CORE = {
    "references/interaction-contract.md",
    "references/workflow.md",
    "references/adb-operations.md",
    "references/apk-policy.md",
    "references/apps.json",
    "references/THIRD_PARTY_NOTICES.md",
    "scripts/tv-helper",
    "scripts/tv_helper/adb.py",
    "scripts/tv_helper/apk.py",
    "scripts/tv_helper/catalog.py",
    "scripts/tv_helper/cli.py",
    "scripts/tv_helper/questions.py",
    "scripts/tv_helper/session.py",
}


class PlatformPackageTests(unittest.TestCase):
    def test_each_platform_package_runs_the_same_harness_and_core(self):
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            hashes_by_platform: dict[str, dict[str, str]] = {}

            for platform in PLATFORMS:
                output = temp / f"android-tv-apps-helper-{platform}-v0.3.0.zip"
                result = subprocess.run(
                    [
                        sys.executable,
                        str(BUILDER),
                        "--platform",
                        platform,
                        "--output",
                        str(output),
                    ],
                    cwd=REPO_ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                metadata = json.loads(result.stdout)
                self.assertEqual(metadata["platform"], platform)
                self.assertEqual(metadata["version"], "0.3.0")

                with zipfile.ZipFile(output) as archive:
                    names = set(archive.namelist())
                    self.assertTrue(
                        {ROOT + path for path in SHARED_CORE}.issubset(names)
                    )
                    self.assertFalse(
                        any(name.lower().endswith(".apk") for name in names)
                    )
                    hashes_by_platform[platform] = {
                        path: hashlib.sha256(archive.read(ROOT + path)).hexdigest()
                        for path in SHARED_CORE
                    }
                    archive.extractall(temp / platform)

                    skill = archive.read(ROOT + "SKILL.md").decode("utf-8")
                    self.assertIn("name: android-tv-apps-helper", skill)
                    self.assertIn("version: 0.3.0", skill)
                    if platform == "claude":
                        self.assertIn("${CLAUDE_SKILL_DIR}/scripts/tv-helper", skill)
                    else:
                        self.assertIn("python3 scripts/tv-helper", skill)

                session = temp / platform / "session.json"
                helper = (
                    temp
                    / platform
                    / "android-tv-apps-helper"
                    / "scripts"
                    / "tv-helper"
                )
                harness = subprocess.run(
                    [
                        sys.executable,
                        str(helper),
                        "init-session",
                        str(session),
                        "--surface",
                        "text_menu",
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(harness.returncode, 0, harness.stderr)
                self.assertEqual(json.loads(harness.stdout)["current_state"], "S0")

            first = hashes_by_platform[PLATFORMS[0]]
            for platform in PLATFORMS[1:]:
                self.assertEqual(hashes_by_platform[platform], first)

    def test_unknown_platform_is_rejected_without_creating_an_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "unknown.zip"
            result = subprocess.run(
                [
                    sys.executable,
                    str(BUILDER),
                    "--platform",
                    "unknown",
                    "--output",
                    str(output),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()

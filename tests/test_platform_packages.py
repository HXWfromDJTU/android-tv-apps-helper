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
RELEASE_BUILDER = REPO_ROOT / "scripts" / "build_release.py"
PLATFORMS = ("workbuddy", "doubao-work", "claude", "codex")
ROOT = "android-tv-apps-helper/"
SHARED_CORE = {
    "references/interaction-contract.md",
    "references/html-interaction.md",
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
    "scripts/tv_helper/compatibility.py",
    "scripts/tv_helper/downloads.py",
    "scripts/tv_helper/evidence.py",
    "scripts/tv_helper/guides.py",
    "scripts/tv_helper/precheck.py",
    "scripts/tv_helper/presentation.py",
    "scripts/tv_helper/questions.py",
    "scripts/tv_helper/report.py",
    "scripts/tv_helper/session.py",
    "scripts/tv_helper/update.py",
    "scripts/tv_helper/workflow.py",
    "scripts/tv_helper/html_ui.py",
    "scripts/tv_helper/html_server.py",
    "scripts/tv_helper/mcp_ui.py",
    "scripts/tv_helper/ui/choice.html",
    "scripts/mcp-requirements.txt",
    "data/copy.zh-CN.json",
    "data/device-guides.json",
    "data/compatibility.json",
    "data/update-manifest.json",
    "assets/adb-enable-generic.svg",
}


class PlatformPackageTests(unittest.TestCase):
    def test_repository_plugin_and_skill_package_versions_match(self):
        root = REPO_ROOT / "plugins" / "android-tv-apps-helper"
        skill_version = json.loads((root / "plugin.json").read_text())["version"]
        plugin_version = json.loads((root / ".codex-plugin" / "plugin.json").read_text())["version"]
        self.assertEqual(plugin_version, skill_version)

    def test_each_platform_package_runs_the_same_harness_and_core(self):
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            hashes_by_platform: dict[str, dict[str, str]] = {}

            for platform in PLATFORMS:
                output = temp / f"android-tv-apps-helper-{platform}-v0.4.0-rc.1.zip"
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
                self.assertEqual(metadata["version"], "0.4.0-rc.1")

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
                    self.assertIn("version: 0.4.0-rc.1", skill)
                    frontmatter = skill.split("---", 2)[1]
                    top_level_keys = {
                        line.split(":", 1)[0]
                        for line in frontmatter.splitlines()
                        if line and not line.startswith(" ") and ":" in line
                    }
                    if platform in {"workbuddy", "doubao-work", "codex"}:
                        self.assertIn("version", top_level_keys)
                    if platform in {"workbuddy", "doubao-work", "claude"}:
                        self.assertNotIn("allowed-tools:", frontmatter)
                        self.assertIn("Call `AskUserQuestion`", skill)
                    if platform == "codex":
                        self.assertNotIn("allowed-tools:", frontmatter)
                        self.assertIn("request_user_input_async", skill)
                    self.assertIn("--surface auto", skill)
                    self.assertIn("record-surface-failure", skill)
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
                        "auto",
                        "--host-platform",
                        platform,
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(harness.returncode, 0, harness.stderr)
                initialized = json.loads(harness.stdout)
                self.assertEqual(initialized["current_state"], "S0")
                self.assertEqual(initialized["host_platform"], platform)

                # Exercise the user-reported second-round failure on the extracted ZIP.
                precheck = temp / platform / "precheck.json"
                precheck.write_text(json.dumps({"devices": [], "rows": [{"status": "attention", "item": "被动发现", "result": "0 台"}]}), encoding="utf-8")
                def invoke(*args):
                    completed = subprocess.run([sys.executable, str(helper), *args], capture_output=True, text=True, check=False)
                    self.assertIn(completed.returncode, (0, 2), completed.stderr)
                    return json.loads(completed.stdout)
                response = invoke("workflow-start", str(session), "--precheck", str(precheck))
                for choice in ("same_wifi", "adb_enabled"):
                    view = response["presentation"]
                    self.assertEqual(view["mode"], "native_required")
                    response = invoke("workflow-native-answer", str(session), "--question-id", view["question_id"], "--presentation-id", view["presentation_id"], "--value", choice)
                self.assertEqual(response["action_required"]["action_id"], "PASSIVE-DISCOVERY-ACTION")
                evidence = temp / platform / "failed.json"
                evidence.write_text(json.dumps({"result": "本次检查失败", "error": "fixture: no adb"}), encoding="utf-8")
                response = invoke("workflow-action-result", str(session), "--action-id", "PASSIVE-DISCOVERY-ACTION", "--status", "failed", "--evidence", str(evidence))
                view = response["presentation"]
                self.assertEqual(view["mode"], "native_required")
                self.assertGreater(view["page_count"], 1)
                self.assertIn("未知", view["context_markdown"])
                response = invoke("workflow-native-answer", str(session), "--question-id", view["question_id"], "--presentation-id", view["presentation_id"], "--value", "ui:next")
                self.assertEqual(response["presentation"]["mode"], "native_required")
                self.assertIsNone(response["action_required"])

                # Desktop packages must also execute their extracted HTML path.
                # The Claude archive serves both Desktop (HTML) and Code (native).
                html_session = temp / platform / "html-session.json"
                host = "claude-desktop" if platform == "claude" else platform
                invoke("init-session", str(html_session), "--surface", "html", "--host-platform", host)
                response = invoke("workflow-start", str(html_session), "--precheck", str(precheck))
                self.assertEqual(response["presentation"]["mode"], "html_required")
                self.assertEqual(response["presentation"]["question_id"], "PRECHECK-WIFI-Q1")
                response = invoke("wait-ui", str(html_session), "--after", "initial", "--timeout", "0")
                self.assertTrue(response["changed"])
                self.assertEqual(response["presentation"]["mode"], "html_required")

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

    def test_release_builder_writes_portable_checksum_entries(self):
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory) / "release"
            result = subprocess.run(
                [
                    sys.executable,
                    str(RELEASE_BUILDER),
                    "--output-dir",
                    str(output_dir),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            metadata = json.loads(result.stdout)
            self.assertEqual(metadata["version"], "0.4.0-rc.1")
            self.assertEqual(len(metadata["artifacts"]), 4)
            lines = (output_dir / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 4)
            self.assertTrue(
                all("  android-tv-apps-helper-" in line for line in lines)
            )
            self.assertFalse(any("dist/" in line or "/" in line for line in lines))
            self.assertTrue((output_dir / "platform-compatibility.json").is_file())


if __name__ == "__main__":
    unittest.main()

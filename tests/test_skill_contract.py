import re
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
SKILL_DIR = ROOT / "plugins" / "android-tv-apps-helper" / "skills" / "android-tv-apps-helper"


class SkillContractTests(unittest.TestCase):
    def test_skill_entrypoint_is_discoverable_and_routes_required_references(self):
        path = SKILL_DIR / "SKILL.md"
        text = path.read_text(encoding="utf-8")
        frontmatter = re.match(r"^---\n(.*?)\n---", text, flags=re.DOTALL)
        self.assertIsNotNone(frontmatter)
        self.assertIn("name: android-tv-apps-helper", frontmatter.group(1))
        self.assertRegex(frontmatter.group(1), r"description: ['\"]?Use when")
        self.assertLessEqual(len(frontmatter.group(1)), 1024)
        for reference in (
            "references/interaction-contract.md",
            "references/workflow.md",
            "references/adb-operations.md",
            "references/apk-policy.md",
            "references/platforms.md",
        ):
            self.assertIn(reference, text)
            self.assertTrue((SKILL_DIR / reference).is_file())

    def test_skill_entrypoint_stays_focused(self):
        text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        body = text.split("---", 2)[-1]
        self.assertLessEqual(len(body.split()), 650)
        self.assertNotIn("[TODO", text)

    def test_interaction_reference_defines_ui_fallback_and_question_lock(self):
        text = (SKILL_DIR / "references" / "interaction-contract.md").read_text(
            encoding="utf-8"
        )
        for concept in (
            "structured_form",
            "text_menu",
            "pending_question",
            "required",
            "explicit_consent",
            "safe_exit",
        ):
            self.assertIn(concept, text)

    def test_platform_reference_preserves_one_core_workflow(self):
        path = SKILL_DIR / "references" / "platforms.md"
        text = path.read_text(encoding="utf-8")
        for platform in ("Claude", "Codex", "WorkBuddy", "豆包工作"):
            self.assertIn(platform, text)
        for invariant in ("PRECHECK-WIFI-Q1", "pending_question", "local_computer"):
            self.assertIn(invariant, text)

    def test_skill_forbids_unapproved_host_downloads_after_read_only_precheck(self):
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        workflow = (SKILL_DIR / "references" / "workflow.md").read_text(encoding="utf-8")
        interaction = (SKILL_DIR / "references" / "interaction-contract.md").read_text(
            encoding="utf-8"
        )
        for text in (skill, workflow):
            self.assertIn("Never download or install ADB", text)
            self.assertIn("action_required", text)
        self.assertIn("native_card_compatible", interaction)
        self.assertIn("never map `safe_exit` to a generic Other field", interaction)


if __name__ == "__main__":
    unittest.main()

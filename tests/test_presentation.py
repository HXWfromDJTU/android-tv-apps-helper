import json
import tempfile
import unittest
from pathlib import Path

from tv_helper.presentation import (
    InteractionFrame,
    SummaryRow,
    friendly_plan_name,
    render_markdown,
    status_symbol,
)


class PresentationTests(unittest.TestCase):
    def test_status_symbol_reflects_evidence_state(self):
        expected = {
            "completed": "✅",
            "failed": "❌",
            "attention": "⚠️",
            "pending": "⏳",
            "skipped": "⏭️",
        }
        self.assertEqual({key: status_symbol(key) for key in expected}, expected)

    def test_frame_renders_table_before_blocker_and_one_question(self):
        frame = InteractionFrame(
            rows=(SummaryRow("attention", "设备发现", "未发现已授权设备", "adb devices -l"),),
            blocker="当前没有可操作的电视。",
            guidance=("确认电脑和电视连接同一个 Wi-Fi。",),
            question_id="S2-Q1",
            question="下一步怎么处理？",
            options=(("retry", "重新检查", "再次执行只读发现"), ("exit", "安全退出", "不执行修改")),
            accepted_answer="请明确回复：1 或 2。",
        )

        rendered = render_markdown(frame)

        self.assertLess(rendered.index("| 状态 |"), rendered.index("当前没有可操作的电视"))
        self.assertEqual(rendered.count("问题 S2-Q1"), 1)
        self.assertIn("⚠️", rendered)

    def test_friendly_plan_name_hides_technical_identifiers(self):
        name = friendly_plan_name(1, "install_apps")
        self.assertEqual(name, "方案 01：安装应用")
        self.assertNotIn("PLAN-", name)
        self.assertNotIn("192.168", name)


if __name__ == "__main__":
    unittest.main()

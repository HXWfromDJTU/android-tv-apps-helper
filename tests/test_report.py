import unittest

from tv_helper.report import render_final_report


class FinalReportTests(unittest.TestCase):
    def test_report_is_table_first_and_uses_evidence_derived_symbols(self):
        report = render_final_report(
            {
                "device_identity": {"model": "TV-1"},
                "evidence_records": [
                    {"action_id": "DOWNLOAD-ACTION", "status": "completed", "evidence": {"result": "已校验"}},
                    {"action_id": "HOME-ACTION", "status": "failed", "evidence": {"result": "系统拒绝"}},
                ],
                "history": [],
                "finish_safety": {"user_confirmation": "keep_enabled", "completed": False},
            }
        )
        self.assertTrue(report.startswith("# 最终结果\n\n| 状态 |"))
        self.assertIn("| ✅ | 应用下载与包体验证 | 已校验 |", report)
        self.assertIn("| ❌ | Home 键默认桌面 | 系统拒绝 |", report)
        self.assertIn("| ⚠️ | ADB 与开发者模式 | 用户选择暂时保持开启 |", report)


if __name__ == "__main__":
    unittest.main()

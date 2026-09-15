import sys
import unittest
from pathlib import Path


PLUGIN_SCRIPTS = (
    Path(__file__).parents[1]
    / "plugins"
    / "android-tv-apps-helper"
    / "scripts"
)
sys.path.insert(0, str(PLUGIN_SCRIPTS))

from tv_helper.questions import AnswerError, Option, Question, validate_answer


class QuestionValidationTests(unittest.TestCase):
    def test_multi_choice_accepts_documented_separators(self):
        question = Question(
            question_id="APPS-Q1",
            state_id="APPS",
            kind="multi_choice",
            prompt="选择应用",
            options=(
                Option("clash", "Clash Meta", "DOWNLOAD-CONFIRM"),
                Option("smarttube", "SmartTube", "DOWNLOAD-CONFIRM"),
                Option("dangbei", "当贝市场", "DOWNLOAD-CONFIRM"),
            ),
        )
        for raw in ("1、2、3", "1,2,3", "1，2，3", "1 2 3"):
            with self.subTest(raw=raw):
                self.assertEqual(
                    validate_answer(question, raw).option_values,
                    ("clash", "smarttube", "dangbei"),
                )

    def test_multi_choice_rejects_duplicates_and_disabled_items(self):
        question = Question(
            question_id="APPS-Q1",
            state_id="APPS",
            kind="multi_choice",
            prompt="选择应用",
            options=(
                Option("clash", "Clash Meta", "DOWNLOAD-CONFIRM"),
                Option(
                    "emotn",
                    "Emotn UI",
                    "DOWNLOAD-CONFIRM",
                    enabled=False,
                    unavailable_reason="当前没有已验证下载源",
                ),
            ),
        )
        with self.assertRaisesRegex(AnswerError, "重复"):
            validate_answer(question, "1、1")
        with self.assertRaisesRegex(AnswerError, "不可选择"):
            validate_answer(question, "2")

    def test_short_text_accepts_displayed_back_index_and_zero_exit(self):
        question = Question(
            question_id="IP-Q1",
            state_id="IP",
            kind="short_text",
            prompt="填写 IP",
            options=(
                Option("submit", "提交 IP", "CONNECT"),
                Option("back", "返回", "DISCOVERY"),
                Option("safe_exit", "安全退出", "END", shortcut="0"),
            ),
            input_prefix="IP:",
            input_format="ipv4",
        )
        self.assertEqual(validate_answer(question, "2").value, "back")
        self.assertEqual(validate_answer(question, "0").value, "safe_exit")
    def setUp(self):
        self.question = Question(
            question_id="S0-Q1",
            state_id="S0",
            kind="single_choice",
            prompt="是否开始检查？",
            options=(
                Option("start_check", "开始检查", "S1"),
                Option("show_scope", "查看范围", "S0_SCOPE"),
                Option("safe_exit", "安全退出", "S11"),
            ),
        )

    def test_ambiguous_reply_cannot_select_recommended_option(self):
        with self.assertRaisesRegex(AnswerError, "明确"):
            validate_answer(self.question, "好的")

    def test_single_choice_rejects_multiple_answers(self):
        with self.assertRaisesRegex(AnswerError, "一个"):
            validate_answer(self.question, "1,2")

    def test_stale_question_id_is_rejected(self):
        with self.assertRaisesRegex(AnswerError, "当前问题"):
            validate_answer(self.question, "1", submitted_question_id="S2-Q1")

    def test_number_and_stable_value_map_to_same_option(self):
        self.assertEqual(validate_answer(self.question, "选 1").value, "start_check")
        self.assertEqual(
            validate_answer(self.question, "start_check").next_state,
            "S1",
        )

    def test_short_text_requires_prefix_and_valid_ipv4(self):
        question = Question(
            question_id="S2-Q2",
            state_id="S2",
            kind="short_text",
            prompt="请输入电视 IP",
            options=(Option("submit_ip", "提交 IP", "S3"),),
            input_prefix="IP:",
            input_format="ipv4",
        )
        with self.assertRaisesRegex(AnswerError, "IP:"):
            validate_answer(question, "192.168.31.170")
        with self.assertRaisesRegex(AnswerError, "有效"):
            validate_answer(question, "IP: 999.1.1.1")
        answer = validate_answer(question, "IP: 192.168.31.170")
        self.assertEqual(answer.value, "192.168.31.170")


if __name__ == "__main__":
    unittest.main()

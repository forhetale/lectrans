"""Prompt 模板测试"""

import unittest

from prompts.templates import (
    CS_TERMS_CONTEXT,
    get_summary_prompt,
    get_translation_prompt,
)


class TestTranslationPrompt(unittest.TestCase):
    def test_structure(self):
        prompt = get_translation_prompt("안녕하세요")
        self.assertEqual(len(prompt), 2)
        self.assertEqual(prompt[0]["role"], "system")
        self.assertEqual(prompt[1]["role"], "user")
        self.assertIn("안녕하세요", prompt[1]["content"])

    def test_terms_have_no_typos(self):
        self.assertIn("时间复杂度", CS_TERMS_CONTEXT)
        self.assertIn("空间复杂度", CS_TERMS_CONTEXT)
        self.assertIn("객체 (Object) - 对象", CS_TERMS_CONTEXT)
        self.assertNotIn("时间复杂도", CS_TERMS_CONTEXT)

    def test_context_included(self):
        prompt = get_translation_prompt(
            "이어서 설명하겠습니다",
            context=[("알고리즘", "算法"), ("자료구조", "数据结构")],
        )
        user_content = prompt[1]["content"]
        self.assertIn("算法", user_content)
        self.assertIn("数据结构", user_content)
        self.assertIn("翻译记录", user_content)

    def test_empty_context_omitted(self):
        prompt = get_translation_prompt("안녕", context=None)
        self.assertNotIn("翻译记录", prompt[1]["content"])

    def test_malformed_context_pairs_ignored(self):
        prompt = get_translation_prompt("안녕", context=[("only-one",), ("", "中文")])
        self.assertNotIn("翻译记录", prompt[1]["content"])


class TestSummaryPrompt(unittest.TestCase):
    def test_structure(self):
        prompt = get_summary_prompt("[10:00:00] 안녕하세요")
        self.assertEqual(len(prompt), 2)
        self.assertIn("核心概念", prompt[1]["content"])
        self.assertIn("作业/考试信息", prompt[1]["content"])
        self.assertIn("안녕하세요", prompt[1]["content"])


if __name__ == "__main__":
    unittest.main()

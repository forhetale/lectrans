"""MiMo 客户端测试（注入 Fake Client，不访问网络）"""

import unittest
from unittest.mock import patch

from core.session_manager import TranscriptEntry
from core.translator import TRANSLATION_FALLBACK, MiMoClient, build_context


class _Message:
    def __init__(self, content):
        self.content = content


class _Choice:
    def __init__(self, content):
        self.message = _Message(content)


class _Response:
    def __init__(self, content):
        self.choices = [_Choice(content)]


class _Completions:
    def __init__(self, fail=False):
        self.fail = fail
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.fail:
            raise RuntimeError("network down")
        return _Response("你好，今天开始计算机科学课程")


class _Chat:
    def __init__(self, fail=False):
        self.completions = _Completions(fail)


class _FakeClient:
    def __init__(self, fail=False):
        self.chat = _Chat(fail)


class TestMiMoClient(unittest.TestCase):
    def test_translate_returns_content(self):
        fake = _FakeClient()
        client = MiMoClient("k", "http://example", client=fake)

        result = client.translate("안녕하세요", model="mimo-v2.5-pro")

        self.assertEqual(result, "你好，今天开始计算机科学课程")
        call = fake.chat.completions.calls[0]
        self.assertEqual(call["model"], "mimo-v2.5-pro")
        self.assertEqual(call["messages"][1]["role"], "user")

    def test_translate_empty_text_short_circuits(self):
        fake = _FakeClient()
        client = MiMoClient("k", "http://example", client=fake)

        self.assertEqual(client.translate("   "), "")
        self.assertEqual(len(fake.chat.completions.calls), 0)

    @patch("core.translator.time.sleep", lambda _s: None)
    def test_translate_retries_then_falls_back(self):
        fake = _FakeClient(fail=True)
        client = MiMoClient("k", "http://example", client=fake)

        result = client.translate("안녕하세요")

        self.assertEqual(result, TRANSLATION_FALLBACK)
        self.assertEqual(len(fake.chat.completions.calls), 3)  # 1 次 + 2 次重试

    def test_context_included_in_prompt(self):
        fake = _FakeClient()
        client = MiMoClient("k", "http://example", client=fake)

        client.translate("이어서", context=[("알고리즘", "算法")])

        user_content = fake.chat.completions.calls[0]["messages"][1]["content"]
        self.assertIn("알고리즘", user_content)
        self.assertIn("算法", user_content)

    @patch("core.translator.time.sleep", lambda _s: None)
    def test_summarize_falls_back_on_error(self):
        client = MiMoClient("k", "http://example", client=_FakeClient(fail=True))
        self.assertEqual(client.summarize("내용"), "总结生成失败")

    def test_summarize_empty_returns_placeholder(self):
        client = MiMoClient("k", "http://example", client=_FakeClient())
        self.assertEqual(client.summarize("  "), "暂无内容")


class TestBuildContext(unittest.TestCase):
    def test_returns_recent_pairs(self):
        entries = [TranscriptEntry(f"ko{i}", f"zh{i}") for i in range(10)]

        context = build_context(entries, 3)

        self.assertEqual(context, [["ko7", "zh7"], ["ko8", "zh8"], ["ko9", "zh9"]])

    def test_size_zero_returns_empty(self):
        entries = [TranscriptEntry("ko", "zh")]
        self.assertEqual(build_context(entries, 0), [])

    def test_incomplete_pairs_skipped(self):
        entries = [TranscriptEntry("", "zh"), TranscriptEntry("ko", "")]
        self.assertEqual(build_context(entries, 5), [])


if __name__ == "__main__":
    unittest.main()

"""
LecTrans 翻译模块

使用 OpenAI 兼容 API（MiMo）进行韩→中翻译和课堂总结：
- 翻译时携带最近 N 条双语对照作为上下文
- 轻量重试（指数退避），失败降级为占位文本并记录日志
- 支持注入客户端，便于测试
"""

import time
from typing import Iterable, List, Optional, Sequence

from core.logger import get_logger
from prompts.templates import get_summary_prompt, get_translation_prompt

logger = get_logger(__name__)

TRANSLATION_FALLBACK = "[翻译失败]"
SUMMARY_FALLBACK = "总结生成失败"

_MAX_RETRIES = 2


class MiMoClient:
    """MiMo API 客户端，提供翻译和总结功能"""

    def __init__(self, api_key: str, base_url: str, timeout: int = 30, client=None):
        self.default_timeout = timeout
        if client is not None:
            self.client = client
        else:
            from openai import OpenAI

            self.client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)

    # ------------------------------------------------------ 对外接口

    def translate(
        self,
        korean_text: str,
        model: str = "mimo-v2.5-pro",
        context: Optional[Iterable[Sequence[str]]] = None,
    ) -> str:
        """翻译韩语为中文，可携带上下文（最近的双语对照）"""
        if not korean_text or not korean_text.strip():
            return ""

        messages = get_translation_prompt(korean_text, context)
        content = self._chat(messages, model=model, max_tokens=500, temperature=0.3)
        if content is None:
            return TRANSLATION_FALLBACK
        return content.strip()

    def summarize(self, transcript: str, model: str = "mimo-v2.5-pro") -> str:
        """生成结构化课堂总结"""
        if not transcript or not transcript.strip():
            return "暂无内容"

        messages = get_summary_prompt(transcript)
        content = self._chat(messages, model=model, max_tokens=2000, temperature=0.3)
        if content is None:
            return SUMMARY_FALLBACK
        return content.strip()

    # ------------------------------------------------------ 内部实现

    def _chat(self, messages: list, model: str, max_tokens: int, temperature: float) -> Optional[str]:
        """带重试的 Chat 调用，全部失败返回 None"""
        last_error: Optional[Exception] = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return response.choices[0].message.content
            except Exception as e:
                last_error = e
                if attempt < _MAX_RETRIES:
                    time.sleep(1.0 * (attempt + 1))
        logger.error("MiMo API 调用失败: %s", last_error)
        return None


def build_context(entries: List, size: int) -> List[Sequence[str]]:
    """从转录条目构建翻译上下文（最近 size 条）"""
    if size <= 0:
        return []
    recent = entries[-size:]
    return [[e.korean, e.chinese] for e in recent if e.korean and e.chinese]

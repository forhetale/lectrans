"""
LecTrans 翻译模块
"""

from typing import Optional, AsyncGenerator, Generator
from datetime import datetime
from dataclasses import dataclass


@dataclass
class TranslationResult:
    """翻译结果"""
    original: str      # 韩语原文
    translated: str    # 中文翻译
    timestamp: datetime


# 翻译 Prompt
TRANSLATION_PROMPT = """你是一位资深的韩中翻译官，专精于学术翻译。
请将以下韩语课堂内容翻译成自然流畅的中文。

要求：
1. 只输出中文翻译，不要输出韩语原文
2. 计算机专业术语使用标准中文译法
3. 外来语保留原文并标注（如：알고리즘 - Algorithm）
4. 保持口语化风格，不要过度书面化
5. 如果内容不完整或无法翻译，返回空字符串"""


class Translator:
    """翻译器 (OpenAI 兼容 API)"""
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://token-plan-cn.xiaomimimo.com/v1",
        model: str = "mimo-v2.5-pro"
    ):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.history: list[dict] = []
    
    def translate(self, korean_text: str) -> TranslationResult:
        """翻译韩语为中文"""
        if not korean_text.strip():
            return TranslationResult(
                original=korean_text,
                translated="",
                timestamp=datetime.now()
            )
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": TRANSLATION_PROMPT},
                    {"role": "user", "content": korean_text}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            translated = response.choices[0].message.content.strip()
            
            # 记录历史
            self.history.append({
                "original": korean_text,
                "translated": translated,
                "timestamp": datetime.now().isoformat()
            })
            
            return TranslationResult(
                original=korean_text,
                translated=translated,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            print(f"Translation error: {e}")
            return TranslationResult(
                original=korean_text,
                translated=f"[翻译失败: {str(e)}]",
                timestamp=datetime.now()
            )
    
    def translate_stream(self, korean_text: str) -> Generator[str, None, None]:
        """流式翻译"""
        if not korean_text.strip():
            return
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": TRANSLATION_PROMPT},
                    {"role": "user", "content": korean_text}
                ],
                temperature=0.3,
                max_tokens=1000,
                stream=True
            )
            
            full_text = ""
            for chunk in response:
                if chunk.choices[0].delta.content:
                    text = chunk.choices[0].delta.content
                    full_text += text
                    yield text
            
            # 记录历史
            self.history.append({
                "original": korean_text,
                "translated": full_text,
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            print(f"Translation stream error: {e}")
            yield f"[翻译失败: {str(e)}]"


class Summarizer:
    """总结生成器"""
    
    SUMMARY_PROMPT = """你是一位学术笔记整理专家。
请根据以下韩语课堂转录内容，整理成结构化的中文笔记。

输出格式：
## 📚 核心概念
1. [概念名称]：[简要解释]
2. ...

## 📝 重要知识点
- [知识点1]
- [知识点2]

## 📌 作业/考试信息
- [如有提及，单独列出]

## ❓ 待确认问题
- [如有不确定的内容，列出供课后确认]

注意：
- 使用中文输出
- 保持简洁明了
- 重点突出关键信息"""
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://token-plan-cn.xiaomimimo.com/v1",
        model: str = "mimo-v2.5-pro"
    ):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
    
    def summarize(self, transcript: str) -> str:
        """生成总结"""
        if not transcript.strip():
            return "暂无转录内容"
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SUMMARY_PROMPT},
                    {"role": "user", "content": f"以下是课堂转录内容：\n\n{transcript}"}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"Summary error: {e}")
            return f"总结生成失败: {str(e)}"


def create_translator(
    api_key: str,
    base_url: str = "https://token-plan-cn.xiaomimimo.com/v1",
    model: str = "mimo-v2.5-pro"
) -> Translator:
    """工厂函数：创建翻译器"""
    return Translator(api_key=api_key, base_url=base_url, model=model)


def create_summarizer(
    api_key: str,
    base_url: str = "https://token-plan-cn.xiaomimimo.com/v1",
    model: str = "mimo-v2.5-pro"
) -> Summarizer:
    """工厂函数：创建总结器"""
    return Summarizer(api_key=api_key, base_url=base_url, model=model)

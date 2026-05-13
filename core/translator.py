"""
LecTrans 翻译模块
使用 OpenAI 兼容 API（MiMo）进行韩→中翻译和课堂总结
"""


class MiMoClient:
    """MiMo API 客户端，提供翻译和总结功能"""

    def __init__(self, api_key: str, base_url: str):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def translate(self, korean_text: str, model: str = "mimo-v2.5-pro") -> str:
        """翻译韩语为中文"""
        if not korean_text.strip():
            return ""
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是资深韩中翻译官，专精学术翻译。只输出中文翻译，不要输出韩语原文。"},
                    {"role": "user", "content": korean_text},
                ],
                temperature=0.3,
                max_tokens=500,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Translation error: {e}")
            return "[翻译失败]"

    def summarize(self, transcript: str, model: str = "mimo-v2.5-pro") -> str:
        """生成课堂总结"""
        if not transcript.strip():
            return "暂无内容"
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": (
                        "你是学术笔记整理专家。将课堂转录整理成结构化中文笔记，使用 Markdown 格式。"
                        "包含：核心概念、重要知识点、作业/考试信息。"
                    )},
                    {"role": "user", "content": f"课堂转录：\n\n{transcript}"},
                ],
                temperature=0.3,
                max_tokens=2000,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Summary error: {e}")
            return "总结生成失败"

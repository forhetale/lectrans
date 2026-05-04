"""
LecTrans Prompt 模板
"""

# ============================================================
# 翻译 Prompt
# ============================================================

TRANSLATION_SYSTEM_PROMPT = """你是一位资深的韩中翻译官，专精于学术翻译，特别是在计算机科学领域。

翻译要求：
1. 只输出中文翻译，不要输出韩语原文
2. 计算机专业术语使用标准中文译法
3. 外来语保留原文并标注（如：알고리즘 - Algorithm）
4. 保持口语化风格，不要过度书面化
5. 如果内容不完整或无法翻译，返回空字符串
6. 保持翻译的准确性和流畅性"""

TRANSLATION_USER_TEMPLATE = """请翻译以下韩语课堂内容：

{korean_text}"""


# ============================================================
# 总结 Prompt
# ============================================================

SUMMARY_SYSTEM_PROMPT = """你是一位学术笔记整理专家，擅长将课堂转录内容整理成结构化的学习笔记。

整理要求：
1. 使用中文输出
2. 保持简洁明了，重点突出
3. 识别并标注关键概念
4. 单独列出作业/考试信息
5. 标注不确定或需要确认的内容
6. 使用 Markdown 格式"""

SUMMARY_USER_TEMPLATE = """以下是韩语课堂的转录内容，请整理成结构化的中文笔记：

{transcript}"""


# ============================================================
# 计算机专业术语词典（用于 Prompt 增强）
# ============================================================

CS_TERMS_CONTEXT = """计算机科学常用韩中术语对照：
- 알고리즘 (Algorithm) - 算法
- 자료구조 (Data Structure) - 数据结构
- 프로그래밍 (Programming) - 编程
- 데이터베이스 (Database) - 数据库
- 네트워크 (Network) - 网络
- 운영체제 (Operating System) - 操作系统
- 소프트웨어 (Software) - 软件
- 하드웨어 (Hardware) - 硬件
- 인공지능 (Artificial Intelligence) - 人工智能
- 머신러닝 (Machine Learning) - 机器学习
- 딥러닝 (Deep Learning) - 深度学习
- 컴파일러 (Compiler) - 编译器
- 인터프리터 (Interpreter) - 解释器
- 변수 (Variable) - 变量
- 함수 (Function) - 函数
- 클래스 (Class) - 类
- 객체 (Object) - 객체
- 배열 (Array) - 数组
- 리스트 (List) - 列表
- 스택 (Stack) - 栈
- 큐 (Queue) - 队列
- 트리 (Tree) - 树
- 그래프 (Graph) - 图
- 정렬 (Sorting) - 排序
- 탐색 (Searching) - 搜索
- 시간복잡도 (Time Complexity) - 时间复杂도
- 공간복잡도 (Space Complexity) - 空间复杂도"""


# ============================================================
# 辅助函数
# ============================================================

def get_translation_prompt(korean_text: str) -> list[dict]:
    """获取翻译 Prompt"""
    return [
        {"role": "system", "content": TRANSLATION_SYSTEM_PROMPT + "\n\n" + CS_TERMS_CONTEXT},
        {"role": "user", "content": TRANSLATION_USER_TEMPLATE.format(korean_text=korean_text)}
    ]


def get_summary_prompt(transcript: str) -> list[dict]:
    """获取总结 Prompt"""
    return [
        {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
        {"role": "user", "content": SUMMARY_USER_TEMPLATE.format(transcript=transcript)}
    ]

"""
LecTrans 核心数据类型

识别结果类型统一在此定义，避免各识别器重复定义导致类型不一致。
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TranscriptionResult:
    """语音识别结果"""

    text: str
    timestamp: datetime = field(default_factory=datetime.now)
    language: str = "ko"
    confidence: float = 0.0

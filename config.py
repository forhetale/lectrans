"""
LecTrans 配置管理模块
基于 JSON 存储，支持 Azure + MiMo 双 API 配置
"""

import json
from pathlib import Path


# 全局目录
CONFIG_DIR = Path.home() / ".lectrans"
CONFIG_FILE = CONFIG_DIR / "config.json"
SESSIONS_DIR = CONFIG_DIR / "sessions"
RECORDINGS_DIR = CONFIG_DIR / "recordings"


class AppConfig:
    """应用配置"""

    def __init__(self):
        # Azure 语音识别
        self.azure_key = ""
        self.azure_region = "koreacentral"
        self.azure_language = "ko-KR"

        # MiMo 翻译/总结
        self.api_key = ""
        self.base_url = "https://token-plan-cn.xiaomimimo.com/v1"
        self.llm_model = "mimo-v2.5-pro"

        # 音频
        self.audio_device_index = -1
        self.sample_rate = 16000

        # UI
        self.font_size = 13

        # 从文件加载（覆盖默认值）
        self.load()

    def load(self):
        """从 JSON 文件加载配置"""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for key, value in data.items():
                    if hasattr(self, key):
                        setattr(self, key, value)
            except Exception:
                pass

    def save(self):
        """保存配置到 JSON 文件"""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            'azure_key': self.azure_key,
            'azure_region': self.azure_region,
            'azure_language': self.azure_language,
            'api_key': self.api_key,
            'base_url': self.base_url,
            'llm_model': self.llm_model,
            'audio_device_index': self.audio_device_index,
            'sample_rate': self.sample_rate,
            'font_size': self.font_size,
        }
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @property
    def is_configured(self):
        """检查是否已配置必要的 API Key"""
        return bool(self.azure_key and self.api_key)

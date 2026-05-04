"""
LecTrans 配置管理模块
"""

import os
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path
import yaml
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


@dataclass
class APIConfig:
    """API 配置"""
    # ASR 配置
    asr_provider: str = "groq"  # groq, openai, local
    asr_api_key: str = ""
    asr_model: str = "whisper-large-v3-turbo"
    
    # LLM 配置
    llm_provider: str = "xiaomi"  # xiaomi, deepseek, openai, groq, local
    llm_api_key: str = ""
    llm_base_url: str = "https://token-plan-cn.xiaomimimo.com/v1"
    llm_model: str = "mimo-v2.5-pro"
    
    def __post_init__(self):
        """从环境变量加载"""
        self.asr_api_key = self.asr_api_key or os.getenv("GROQ_API_KEY", "")
        self.llm_api_key = self.llm_api_key or os.getenv("XIAOMI_API_KEY", "")
        
        # 根据 provider 自动设置 base_url
        if not self.llm_base_url:
            if self.llm_provider == "xiaomi":
                self.llm_base_url = os.getenv("XIAOMI_BASE_URL", "https://token-plan-cn.xiaomimimo.com/v1")
            elif self.llm_provider == "deepseek":
                self.llm_base_url = "https://api.deepseek.com/v1"
    
    @property
    def is_configured(self) -> bool:
        """检查是否已配置"""
        return bool(self.asr_api_key and self.llm_api_key)


@dataclass
class AudioConfig:
    """音频配置"""
    sample_rate: int = 16000
    chunk_size: int = 1024
    channels: int = 1
    buffer_duration: float = 3.0  # 缓冲区时长（秒）
    vad_mode: int = 2  # VAD 模式 (0-3, 越大越敏感)


@dataclass
class UIConfig:
    """UI 配置"""
    theme: str = "dark"
    font_size: int = 16
    show_timestamp: bool = True
    auto_scroll: bool = True


@dataclass
class AppConfig:
    """应用配置"""
    api: APIConfig = field(default_factory=APIConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    
    # 文件路径
    config_dir: Path = Path.home() / ".lectrans"
    config_file: Path = config_dir / "config.yaml"
    
    def load(self):
        """加载配置"""
        if self.config_file.exists():
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
                
                # API 配置
                api_data = data.get('api', {})
                self.api.asr_provider = api_data.get('asr_provider', self.api.asr_provider)
                self.api.asr_api_key = api_data.get('asr_api_key', self.api.asr_api_key)
                self.api.llm_provider = api_data.get('llm_provider', self.api.llm_provider)
                self.api.llm_api_key = api_data.get('llm_api_key', self.api.llm_api_key)
                self.api.llm_base_url = api_data.get('llm_base_url', self.api.llm_base_url)
                self.api.llm_model = api_data.get('llm_model', self.api.llm_model)
                
                # UI 配置
                ui_data = data.get('ui', {})
                self.ui.theme = ui_data.get('theme', self.ui.theme)
                self.ui.font_size = ui_data.get('font_size', self.ui.font_size)
    
    def save(self):
        """保存配置"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        data = {
            'api': {
                'asr_provider': self.api.asr_provider,
                'asr_api_key': self.api.asr_api_key,
                'llm_provider': self.api.llm_provider,
                'llm_api_key': self.api.llm_api_key,
                'llm_base_url': self.api.llm_base_url,
                'llm_model': self.api.llm_model,
            },
            'ui': {
                'theme': self.ui.theme,
                'font_size': self.ui.font_size,
            }
        }
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True)

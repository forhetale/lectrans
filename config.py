"""
LecTrans 配置管理模块

- 基于 JSON 存储（~/.lectrans/config.json），支持 LECTRANS_HOME 覆盖目录
- 支持环境变量覆盖（方便部署与测试）
- API Key 优先使用系统 keyring 保存，不可用时回退到 JSON（并尽力限制文件权限）
- 支持 Azure + MiMo 双 API 配置
"""

import json
import logging
import os
import stat
from pathlib import Path

logger = logging.getLogger(__name__)

APP_VERSION = "0.2.0"
APP_NAME = "LecTrans"

_KEYRING_SERVICE = "lectrans"
_KEYRING_ALIASES = {"azure_key": "azure_speech_key", "api_key": "mimo_api_key"}


def _base_dir() -> Path:
    override = os.environ.get("LECTRANS_HOME", "").strip()
    if override:
        return Path(override).expanduser()
    return Path.home() / ".lectrans"


CONFIG_DIR = _base_dir()
CONFIG_FILE = CONFIG_DIR / "config.json"
SESSIONS_DIR = CONFIG_DIR / "sessions"
RECORDINGS_DIR = CONFIG_DIR / "recordings"
LOG_FILE = CONFIG_DIR / "lectrans.log"


def _keyring_module():
    """惰性获取 keyring 模块，未安装时返回 None"""
    try:
        import keyring  # type: ignore

        return keyring
    except Exception:
        return None


def _save_secret(name: str, value: str) -> bool:
    """将密钥写入系统钥匙串，失败返回 False"""
    if not value:
        return False
    keyring = _keyring_module()
    if keyring is None:
        return False
    try:
        keyring.set_password(_KEYRING_SERVICE, _KEYRING_ALIASES.get(name, name), value)
        return True
    except Exception as e:
        logger.warning("keyring 写入失败(%s)，将回退到配置文件: %s", name, e)
        return False


def _load_secret(name: str) -> str:
    """从系统钥匙串读取密钥，失败返回空串"""
    keyring = _keyring_module()
    if keyring is None:
        return ""
    try:
        return keyring.get_password(_KEYRING_SERVICE, _KEYRING_ALIASES.get(name, name)) or ""
    except Exception:
        return ""


class AppConfig:
    """应用配置"""

    def __init__(self):
        # 语音识别引擎选择: "local" 或 "azure"
        self.asr_engine = "local"
        self.whisper_model = "base"

        # Azure 语音识别
        self.azure_key = ""
        self.azure_region = "koreacentral"
        self.azure_language = "ko-KR"

        # MiMo 翻译/总结
        self.api_key = ""
        self.base_url = "https://token-plan-cn.xiaomimimo.com/v1"
        self.llm_model = "mimo-v2.5-pro"
        self.api_timeout = 30

        # 音频
        self.audio_device_index = -1
        self.sample_rate = 16000

        # 本地 VAD 调优
        self.energy_threshold = 300        # 噪声门限（RMS 基准值）
        self.silence_duration = 0.8        # 判定句子结束的静音时长（秒）
        self.max_utterance_seconds = 20.0  # 单句最长时长（秒），超出强制切分

        # 翻译上下文
        self.translation_context_size = 5  # 携带最近 N 条双语对照作为上下文

        # UI
        self.font_size = 13

        # 从文件加载（覆盖默认值）
        self.load()

    # ------------------------------------------------------ 加载 / 保存

    def load(self):
        """加载配置：JSON -> keyring -> 环境变量覆盖"""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for key, value in data.items():
                    if hasattr(self, key):
                        setattr(self, key, value)
            except Exception as e:
                logger.warning("读取配置文件失败: %s", e)

        for attr in ("azure_key", "api_key"):
            if not getattr(self, attr):
                secret = _load_secret(attr)
                if secret:
                    setattr(self, attr, secret)

        self._load_env()

    def _load_env(self):
        """环境变量覆盖（部署与 CI 场景）"""
        env_map = {
            "LECTRANS_ASR_ENGINE": "asr_engine",
            "LECTRANS_WHISPER_MODEL": "whisper_model",
            "LECTRANS_AZURE_KEY": "azure_key",
            "LECTRANS_AZURE_REGION": "azure_region",
            "LECTRANS_AZURE_LANGUAGE": "azure_language",
            "LECTRANS_API_KEY": "api_key",
            "LECTRANS_BASE_URL": "base_url",
            "LECTRANS_LLM_MODEL": "llm_model",
            "LECTRANS_AUDIO_DEVICE_INDEX": "audio_device_index",
            "LECTRANS_FONT_SIZE": "font_size",
        }
        int_attrs = {"audio_device_index", "font_size"}
        for env_name, attr in env_map.items():
            value = os.environ.get(env_name, "").strip()
            if not value:
                continue
            try:
                setattr(self, attr, int(value) if attr in int_attrs else value)
            except ValueError:
                logger.warning("环境变量 %s 取值非法: %r", env_name, value)

    def save(self):
        """保存配置到 JSON 文件；密钥优先写入系统钥匙串"""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)

        azure_key = self.azure_key
        api_key = self.api_key
        if _save_secret("azure_key", azure_key):
            azure_key = ""
        if _save_secret("api_key", api_key):
            api_key = ""

        data = {
            "version": APP_VERSION,
            "asr_engine": self.asr_engine,
            "whisper_model": self.whisper_model,
            "azure_key": azure_key,
            "azure_region": self.azure_region,
            "azure_language": self.azure_language,
            "api_key": api_key,
            "base_url": self.base_url,
            "llm_model": self.llm_model,
            "api_timeout": self.api_timeout,
            "audio_device_index": self.audio_device_index,
            "sample_rate": self.sample_rate,
            "energy_threshold": self.energy_threshold,
            "silence_duration": self.silence_duration,
            "max_utterance_seconds": self.max_utterance_seconds,
            "translation_context_size": self.translation_context_size,
            "font_size": self.font_size,
        }

        tmp_file = CONFIG_FILE.with_suffix(".json.tmp")
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_file, CONFIG_FILE)

        self._restrict_permissions(CONFIG_FILE)

    @staticmethod
    def _restrict_permissions(path: Path):
        """尽量将配置文件限制为仅当前用户可读（POSIX）"""
        try:
            if os.name == "posix":
                path.chmod(stat.S_IRUSR | stat.S_IWUSR)
        except Exception:
            pass

    @property
    def is_configured(self) -> bool:
        """检查是否已配置必要的 API Key"""
        if self.asr_engine == "azure":
            return bool(self.azure_key and self.api_key)
        return bool(self.api_key)

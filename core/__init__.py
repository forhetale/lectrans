"""
LecTrans 核心模块

使用 PEP 562 惰性导入：仅在真正访问时才加载对应子模块，
避免本地模式用户因未安装 Azure SDK 而无法使用。
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - 仅用于类型检查
    from .audio_recorder import AudioManager, AudioRecorder
    from .azure_recognizer import AzureSpeechRecognizer
    from .local_recognizer import LocalWhisperRecognizer
    from .session_manager import SessionManager, TranscriptEntry
    from .translator import MiMoClient
    from .types import TranscriptionResult

__all__ = [
    "AudioRecorder",
    "AudioManager",
    "AzureSpeechRecognizer",
    "LocalWhisperRecognizer",
    "MiMoClient",
    "SessionManager",
    "TranscriptEntry",
    "TranscriptionResult",
]

_LAZY_IMPORTS = {
    "AudioRecorder": (".audio_recorder", "AudioRecorder"),
    "AudioManager": (".audio_recorder", "AudioManager"),
    "AzureSpeechRecognizer": (".azure_recognizer", "AzureSpeechRecognizer"),
    "LocalWhisperRecognizer": (".local_recognizer", "LocalWhisperRecognizer"),
    "MiMoClient": (".translator", "MiMoClient"),
    "SessionManager": (".session_manager", "SessionManager"),
    "TranscriptEntry": (".session_manager", "TranscriptEntry"),
    "TranscriptionResult": (".types", "TranscriptionResult"),
}


def __getattr__(name: str):
    target = _LAZY_IMPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attr_name = target
    from importlib import import_module

    value = getattr(import_module(module_name, __name__), attr_name)
    globals()[name] = value
    return value


def __dir__():
    return sorted(set(list(globals()) + __all__))

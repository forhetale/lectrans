"""
LecTrans 核心模块
"""

from .audio_recorder import AudioRecorder, AudioManager
from .azure_recognizer import AzureSpeechRecognizer
from .translator import MiMoClient
from .session_manager import SessionManager, TranscriptEntry

__all__ = [
    "AudioRecorder",
    "AudioManager",
    "AzureSpeechRecognizer",
    "MiMoClient",
    "SessionManager",
    "TranscriptEntry",
]
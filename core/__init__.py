"""
LecTrans 核心模块
"""

from .audio_capture import AudioCapture, AudioChunk
from .speech_recognizer import SpeechRecognizer, create_recognizer
from .translator import Translator, Summarizer, create_translator, create_summarizer
from .session_manager import SessionManager, SessionState, TranscriptEntry

__all__ = [
    "AudioCapture",
    "AudioChunk",
    "SpeechRecognizer",
    "create_recognizer",
    "Translator",
    "Summarizer",
    "create_translator",
    "create_summarizer",
    "SessionManager",
    "SessionState",
    "TranscriptEntry",
]

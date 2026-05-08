"""
LecTrans 核心模块
"""

from .audio_capture import AudioCapture, AudioChunk
from .speech_recognizer import SpeechRecognizer, create_recognizer
from .azure_speech_recognizer import AzureSpeechRecognizer, AzureSpeechRecognizerWithBuffer, create_azure_recognizer
from .translator import Translator, Summarizer, create_translator, create_summarizer
from .session_manager import SessionManager, SessionState, TranscriptEntry

__all__ = [
    "AudioCapture",
    "AudioChunk",
    "SpeechRecognizer",
    "create_recognizer",
    "AzureSpeechRecognizer",
    "AzureSpeechRecognizerWithBuffer",
    "create_azure_recognizer",
    "Translator",
    "Summarizer",
    "create_translator",
    "create_summarizer",
    "SessionManager",
    "SessionState",
    "TranscriptEntry",
]

"""
LecTrans Azure 语音识别模块

- 支持两种音频输入：
  1. 传入共享音频队列（来自 AudioRecorder），使用 PushAudioInputStream 推送，保证与录音设备一致
  2. 未传入时使用系统默认麦克风
- 事件驱动连续识别，结果统一为 TranscriptionResult
"""

import json
import queue
import threading
from typing import Callable, Optional

import azure.cognitiveservices.speech as speechsdk

from core.logger import get_logger
from core.types import TranscriptionResult

logger = get_logger(__name__)


class AzureSpeechRecognizer:
    """Azure 语音识别器"""

    def __init__(self, subscription_key: str, region: str, language: str = "ko-KR", endpoint: str = None):
        self.subscription_key = subscription_key
        self.region = region
        self.language = language

        self.speech_config = speechsdk.SpeechConfig(subscription=subscription_key, region=region)
        self.speech_config.speech_recognition_language = language
        if endpoint:
            self.speech_config.endpoint_id = endpoint
        self.speech_config.output_format = speechsdk.OutputFormat.Detailed

        self.speech_recognizer: Optional[speechsdk.SpeechRecognizer] = None
        self.is_listening = False

        self.on_recognizing: Optional[Callable[[str], None]] = None
        self.on_recognized: Optional[Callable[[TranscriptionResult], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None

        self._push_stream = None
        self._feeder_thread: Optional[threading.Thread] = None
        self._audio_queue: Optional[queue.Queue] = None

    # ------------------------------------------------------ 生命周期

    def start_continuous_recognition(self, audio_queue: Optional[queue.Queue] = None) -> bool:
        """开始连续识别；提供 audio_queue 时使用推送流，否则使用默认麦克风"""
        try:
            if audio_queue is not None:
                self._audio_queue = audio_queue
                self._push_stream = speechsdk.audio.PushAudioInputStream()
                audio_config = speechsdk.audio.AudioConfig(stream=self._push_stream)
            else:
                audio_config = speechsdk.AudioConfig(use_default_microphone=True)

            self.speech_recognizer = speechsdk.SpeechRecognizer(
                speech_config=self.speech_config, audio_config=audio_config
            )
            self.speech_recognizer.recognizing.connect(self._on_recognizing)
            self.speech_recognizer.recognized.connect(self._on_recognized)
            self.speech_recognizer.canceled.connect(self._on_canceled)
            self.speech_recognizer.session_stopped.connect(self._on_session_stopped)

            self.speech_recognizer.start_continuous_recognition()
            self.is_listening = True

            if self._push_stream is not None:
                self._feeder_thread = threading.Thread(
                    target=self._feed_loop, name="azure-audio-feeder", daemon=True
                )
                self._feeder_thread.start()

            logger.info("Azure 语音识别已启动 (语言=%s, 音频源=%s)", self.language,
                        "共享队列" if audio_queue is not None else "默认麦克风")
            return True
        except Exception as e:
            logger.exception("启动 Azure 语音识别失败")
            self._emit_error(str(e))
            return False

    def stop_continuous_recognition(self):
        """停止连续识别"""
        self.is_listening = False
        if self.speech_recognizer:
            try:
                self.speech_recognizer.stop_continuous_recognition()
            except Exception as e:
                logger.warning("停止 Azure 识别失败: %s", e)
            self.speech_recognizer = None

        if self._feeder_thread and self._feeder_thread.is_alive():
            self._feeder_thread.join(timeout=2.0)
        self._feeder_thread = None

        if self._push_stream:
            try:
                self._push_stream.close()
            except Exception:
                pass
            self._push_stream = None
        self._audio_queue = None

    def _feed_loop(self):
        """将共享队列中的 PCM 块推送到 Azure PushAudioInputStream"""
        while self.is_listening and self._audio_queue is not None:
            try:
                chunk = self._audio_queue.get(timeout=0.5)
            except queue.Empty:
                continue
            try:
                self._push_stream.write(chunk)
            except Exception as e:
                if self.is_listening:
                    logger.warning("写入 Azure 音频流失败: %s", e)
                break

    # ------------------------------------------------------ 事件回调

    def _on_recognizing(self, evt):
        if evt.result.text and self.on_recognizing:
            self.on_recognizing(evt.result.text)

    def _on_recognized(self, evt):
        if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
            text = evt.result.text.strip()
            if not text:
                return
            confidence = self._extract_confidence(evt)
            if self.on_recognized:
                self.on_recognized(
                    TranscriptionResult(
                        text=text,
                        language=self.language,
                        confidence=confidence,
                    )
                )
        elif evt.result.reason == speechsdk.ResultReason.NoMatch:
            logger.debug("Azure 未识别到语音")

    @staticmethod
    def _extract_confidence(evt) -> float:
        try:
            detailed = json.loads(evt.result.json)
            best = detailed.get("NBest") or []
            if best:
                return float(best[0].get("Confidence", 0.0))
        except Exception:
            pass
        return 0.0

    def _on_canceled(self, evt):
        details = evt.result.cancellation_details
        logger.warning("Azure 识别被取消: %s", details.reason)
        if details.reason == speechsdk.CancellationReason.Error:
            self._emit_error(f"错误代码: {details.error_code}, 详情: {details.error_details}")

    def _on_session_stopped(self, evt):
        logger.info("Azure 识别会话已停止")
        self.is_listening = False

    def _emit_error(self, message: str):
        logger.error(message)
        if self.on_error:
            self.on_error(message)

"""
LecTrans 本地语音识别模块

使用 faster-whisper + 自适应能量 VAD：
- 音频块由 AudioRecorder 统一采集后通过队列传入，识别器不再自行打开麦克风
- 噪声底噪动态估计，门限 = max(能量基准, 底噪 * 系数)
- 支持最长语音时长，避免长句无限累积导致延迟与内存膨胀
"""

import queue
import threading
from typing import Callable, Optional

try:
    import numpy as np
except ImportError:  # pragma: no cover - 依赖缺失时由 start 报错
    np = None

try:
    from faster_whisper import WhisperModel
except ImportError:  # pragma: no cover
    WhisperModel = None

from core.logger import get_logger
from core.types import TranscriptionResult

logger = get_logger(__name__)


class LocalWhisperRecognizer:
    """本地 Faster-Whisper 识别引擎（消费共享音频队列）"""

    def __init__(
        self,
        model_size: str = "base",
        device_index: int = -1,
        language: str = "ko",
        sample_rate: int = 16000,
        energy_threshold: int = 300,
        silence_duration: float = 0.8,
        min_speech_duration: float = 0.5,
        max_utterance_seconds: float = 20.0,
        vad_factor: float = 3.0,
    ):
        self.model_size = model_size
        self.device_index = device_index
        self.language = language
        self.sample_rate = sample_rate

        self.energy_threshold = energy_threshold
        self.silence_duration = silence_duration
        self.min_speech_duration = min_speech_duration
        self.max_utterance_seconds = max_utterance_seconds
        self.vad_factor = vad_factor

        self.on_recognized: Optional[Callable[[TranscriptionResult], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None

        self.is_running = False
        self._thread: Optional[threading.Thread] = None
        self._audio_queue: Optional[queue.Queue] = None
        self.model = None

    # ------------------------------------------------------ 生命周期

    def start_continuous_recognition(self, audio_queue: queue.Queue) -> bool:
        """启动后台连续识别（消费 audio_queue 中的 PCM 块）"""
        if np is None:
            self._emit_error("未安装 numpy，无法使用本地识别；请安装依赖或切换为 Azure")
            return False
        if WhisperModel is None:
            self._emit_error("faster-whisper 未安装，请在设置中切换为 Azure 或安装依赖")
            return False

        self._audio_queue = audio_queue
        self.is_running = True
        self._thread = threading.Thread(target=self._recognition_loop, name="local-asr", daemon=True)
        self._thread.start()
        return True

    def stop_continuous_recognition(self):
        """停止连续识别"""
        self.is_running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)
        self._thread = None

    def _load_model(self):
        if self.model is None:
            logger.info("加载本地 Whisper 模型: %s", self.model_size)
            self.model = WhisperModel(self.model_size, device="auto", compute_type="default")
            logger.info("本地 Whisper 模型加载完成")

    # ------------------------------------------------------ 识别循环

    def _recognition_loop(self):
        try:
            self._load_model()
        except Exception as e:
            logger.exception("本地模型加载失败")
            self._emit_error(f"本地模型加载失败: {e}")
            self.is_running = False
            return

        chunk_size = 1024
        silence_chunks_threshold = max(1, int(self.silence_duration * self.sample_rate / chunk_size))
        max_speech_samples = int(self.max_utterance_seconds * self.sample_rate)

        speech_buffer = []
        speech_samples = 0
        silence_chunks = 0
        is_speaking = False
        noise_floor: Optional[float] = None

        while self.is_running:
            try:
                data = self._audio_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            audio_np = np.frombuffer(data, dtype=np.int16)
            if audio_np.size == 0:
                continue

            rms = self._rms(audio_np)
            threshold = self._threshold(noise_floor)

            if rms > threshold:
                is_speaking = True
                silence_chunks = 0
                speech_buffer.append(audio_np)
                speech_samples += audio_np.size
            elif is_speaking:
                silence_chunks += 1
                speech_buffer.append(audio_np)
                speech_samples += audio_np.size
            else:
                noise_floor = rms if noise_floor is None else 0.95 * noise_floor + 0.05 * rms

            if is_speaking and (
                silence_chunks >= silence_chunks_threshold or speech_samples >= max_speech_samples
            ):
                self._process_chunk(speech_buffer)
                speech_buffer = []
                speech_samples = 0
                silence_chunks = 0
                is_speaking = False

        if speech_buffer:
            self._process_chunk(speech_buffer)

    def _process_chunk(self, speech_buffer):
        """使用 Faster-Whisper 推理音频片段"""
        if not speech_buffer or self.model is None:
            return

        audio_data = np.concatenate(speech_buffer)
        duration = len(audio_data) / self.sample_rate
        if duration < self.min_speech_duration:
            return  # 过滤极短的杂音

        audio_float32 = audio_data.astype(np.float32) / 32768.0
        try:
            segments, _info = self.model.transcribe(
                audio_float32,
                language=self.language,
                beam_size=5,
                vad_filter=True,
                without_timestamps=True,
            )
            text = "".join(segment.text for segment in segments).strip()
            if text and self.on_recognized:
                self.on_recognized(TranscriptionResult(text=text, language=self.language))
        except Exception as e:
            logger.exception("本地推理失败")
            self._emit_error(f"推理失败: {e}")

    # ------------------------------------------------------ 工具方法

    @staticmethod
    def _rms(audio_np) -> float:
        """计算音频块的 RMS 能量"""
        if audio_np.size == 0:
            return 0.0
        return float(np.sqrt(np.mean(np.square(audio_np.astype(np.float32)))))

    def _threshold(self, noise_floor: Optional[float]) -> float:
        """自适应门限：能量基准与动态底噪取较大者"""
        if noise_floor is None:
            return float(self.energy_threshold)
        return max(float(self.energy_threshold), noise_floor * self.vad_factor)

    def _emit_error(self, message: str):
        logger.error(message)
        if self.on_error:
            self.on_error(message)

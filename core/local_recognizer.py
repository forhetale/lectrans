"""
LecTrans 本地语音识别模块
使用 faster-whisper 和基于能量的 VAD 切片实现极速流式识别
"""

import threading
import time
import queue
import numpy as np
from typing import Callable, Optional

try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None

class LocalWhisperRecognizer:
    """本地 Faster-Whisper 识别引擎 (带 VAD 切片)"""

    def __init__(self, model_size="base", device_index=-1, language="ko", sample_rate=16000):
        self.model_size = model_size
        self.device_index = device_index
        self.language = language
        self.sample_rate = sample_rate
        
        # 回调
        self.on_recognized: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
        
        # 状态
        self.is_running = False
        self._thread: Optional[threading.Thread] = None
        self.model = None

        # VAD 配置
        self.energy_threshold = 300      # 声音能量阈值 (根据麦克风可能需要动态调整)
        self.silence_duration = 0.8      # 判定为句子结束的静音时长(秒)
        self.min_speech_duration = 0.5   # 最短有效语音时长(秒)，过滤短促杂音

    def _load_model(self):
        if not self.model:
            # 根据是否有独立显卡，faster-whisper 会自动选择 device="cuda" 或 "cpu"
            # compute_type="default" 可最大化兼容性
            self.model = WhisperModel(self.model_size, device="auto", compute_type="default")

    def start_continuous_recognition(self) -> bool:
        """启动后台连续识别"""
        if WhisperModel is None:
            if self.on_error:
                self.on_error("faster-whisper 未安装，请在设置中切换为 Azure 或安装依赖。")
            return False

        try:
            self._load_model()
        except Exception as e:
            if self.on_error:
                self.on_error(f"本地模型加载失败: {str(e)}")
            return False

        self.is_running = True
        self._thread = threading.Thread(target=self._recognition_loop, daemon=True)
        self._thread.start()
        return True

    def stop_continuous_recognition(self):
        """停止连续识别"""
        self.is_running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def _recognition_loop(self):
        """核心音频采集与 VAD 切片推理循环"""
        try:
            import pyaudio
            p = pyaudio.PyAudio()
            chunk_size = 1024
            stream = p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.sample_rate,
                input=True,
                input_device_index=self.device_index if self.device_index >= 0 else None,
                frames_per_buffer=chunk_size,
            )
        except Exception as e:
            if self.on_error:
                self.on_error(f"麦克风打开失败: {str(e)}")
            return

        speech_buffer = []
        silence_chunks = 0
        is_speaking = False
        
        # 0.8秒对应的 chunk 数量
        silence_chunks_threshold = int(self.silence_duration * self.sample_rate / chunk_size)

        while self.is_running:
            try:
                data = stream.read(chunk_size, exception_on_overflow=False)
                # 转换为 numpy 数组以计算能量
                audio_np = np.frombuffer(data, dtype=np.int16)
                
                # 计算 RMS 能量
                rms = np.sqrt(np.mean(np.square(audio_np.astype(np.float32))))
                
                if rms > self.energy_threshold:
                    is_speaking = True
                    silence_chunks = 0
                    speech_buffer.append(audio_np)
                else:
                    if is_speaking:
                        silence_chunks += 1
                        speech_buffer.append(audio_np)
                        
                        # 检测到长静音，切片推理
                        if silence_chunks >= silence_chunks_threshold:
                            self._process_chunk(speech_buffer)
                            speech_buffer = []
                            is_speaking = False
                            silence_chunks = 0
            except Exception as e:
                if self.is_running and self.on_error:
                    self.on_error(f"采集异常: {str(e)}")
                break
                
        # 停止前把最后一点数据推理掉
        if speech_buffer:
            self._process_chunk(speech_buffer)

        try:
            stream.stop_stream()
            stream.close()
            p.terminate()
        except Exception:
            pass

    def _process_chunk(self, speech_buffer):
        """使用 Faster-Whisper 推理音频片段"""
        if not speech_buffer or not self.model:
            return
            
        audio_data = np.concatenate(speech_buffer)
        duration = len(audio_data) / self.sample_rate
        
        if duration < self.min_speech_duration:
            return  # 过滤极短的杂音
            
        # faster-whisper 需要 float32 格式，范围 [-1.0, 1.0]
        audio_float32 = audio_data.astype(np.float32) / 32768.0

        try:
            # 推理
            segments, info = self.model.transcribe(
                audio_float32, 
                language=self.language,
                beam_size=5,
                vad_filter=True,  # 开启模型内置的 VAD 进一步过滤非语音
                without_timestamps=True
            )
            
            text = "".join([segment.text for segment in segments]).strip()
            
            if text and self.on_recognized:
                # 模拟 Azure 的 Result 对象返回
                class DummyResult:
                    def __init__(self, text):
                        self.text = text
                
                self.on_recognized(DummyResult(text))
        except Exception as e:
            if self.on_error:
                self.on_error(f"推理失败: {str(e)}")

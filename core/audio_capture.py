"""
LecTrans 音频采集模块
"""

import io
import wave
import threading
from typing import Optional, Callable
from dataclasses import dataclass
from datetime import datetime

try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False

try:
    import webrtcvad
    WEBRTC_AVAILABLE = True
except ImportError:
    WEBRTC_AVAILABLE = False


@dataclass
class AudioChunk:
    """音频块"""
    data: bytes
    timestamp: datetime
    sample_rate: int
    is_speech: bool = True


class AudioCapture:
    """音频采集器"""
    
    def __init__(
        self,
        sample_rate: int = 16000,
        chunk_size: int = 1024,
        channels: int = 1,
        vad_mode: int = 2,
        on_audio: Optional[Callable] = None
    ):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.channels = channels
        self.vad_mode = vad_mode
        self.on_audio = on_audio
        
        # 状态
        self.is_recording = False
        self._audio: Optional[pyaudio.PyAudio] = None
        self._stream = None
        self._thread: Optional[threading.Thread] = None
        
        # VAD
        self._vad = None
        if WEBRTC_AVAILABLE:
            self._vad = webrtcvad.Vad(vad_mode)
        
        # 缓冲区
        self._buffer: list[bytes] = []
        self._buffer_duration = 3.0  # 秒
        self._chunks_per_buffer = int(sample_rate * buffer_duration / chunk_size)
    
    def start(self) -> bool:
        """开始录音"""
        if not PYAUDIO_AVAILABLE:
            raise RuntimeError("PyAudio not installed. Run: pip install pyaudio")
        
        if self.is_recording:
            return True
        
        try:
            self._audio = pyaudio.PyAudio()
            self._stream = self._audio.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )
            
            self.is_recording = True
            self._thread = threading.Thread(target=self._record_loop, daemon=True)
            self._thread.start()
            
            return True
            
        except Exception as e:
            print(f"Failed to start recording: {e}")
            return False
    
    def stop(self):
        """停止录音"""
        self.is_recording = False
        
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None
        
        if self._stream:
            self._stream.stop_stream()
            self._stream.close()
            self._stream = None
        
        if self._audio:
            self._audio.terminate()
            self._audio = None
    
    def _record_loop(self):
        """录音循环"""
        while self.is_recording:
            try:
                if self._stream:
                    chunk = self._stream.read(self.chunk_size, exception_on_overflow=False)
                    
                    # VAD 检测
                    is_speech = True
                    if self._vad:
                        is_speech = self._vad.is_speech(chunk, self.sample_rate)
                    
                    # 回调
                    if self.on_audio:
                        audio_chunk = AudioChunk(
                            data=chunk,
                            timestamp=datetime.now(),
                            sample_rate=self.sample_rate,
                            is_speech=is_speech
                        )
                        self.on_audio(audio_chunk)
                        
            except Exception as e:
                if self.is_recording:
                    print(f"Recording error: {e}")
    
    def get_devices(self) -> list[dict]:
        """获取可用音频设备"""
        if not PYAUDIO_AVAILABLE:
            return []
        
        devices = []
        p = pyaudio.PyAudio()
        
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:
                devices.append({
                    'index': i,
                    'name': info['name'],
                    'channels': info['maxInputChannels'],
                    'sample_rate': info['defaultSampleRate']
                })
        
        p.terminate()
        return devices


def audio_to_wav(audio_data: bytes, sample_rate: int = 16000) -> bytes:
    """将原始音频数据转换为 WAV 格式"""
    buffer = io.BytesIO()
    
    with wave.open(buffer, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(audio_data)
    
    return buffer.getvalue()


def merge_audio_chunks(chunks: list[AudioChunk]) -> bytes:
    """合并多个音频块"""
    return b''.join(chunk.data for chunk in chunks)

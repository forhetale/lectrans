"""
LecTrans 语音识别模块
"""

import io
from typing import Optional
from datetime import datetime
from dataclasses import dataclass

from groq import Groq

from .audio_capture import AudioChunk, audio_to_wav, merge_audio_chunks


@dataclass
class TranscriptionResult:
    """转录结果"""
    text: str
    timestamp: datetime
    language: str = "ko"
    confidence: float = 0.0


class SpeechRecognizer:
    """语音识别器 (Groq Whisper)"""
    
    def __init__(
        self,
        api_key: str,
        model: str = "whisper-large-v3-turbo",
        language: str = "ko"
    ):
        self.client = Groq(api_key=api_key)
        self.model = model
        self.language = language
        
        # 缓冲区
        self._buffer: list[AudioChunk] = []
        self._buffer_duration = 3.0  # 秒
        self._sample_rate = 16000
    
    def add_chunk(self, chunk: AudioChunk) -> Optional[TranscriptionResult]:
        """添加音频块，缓冲满时返回转录结果"""
        self._buffer.append(chunk)
        
        # 计算缓冲区时长
        total_samples = sum(len(c.data) // 2 for c in self._buffer)  # 16-bit = 2 bytes
        duration = total_samples / self._sample_rate
        
        if duration >= self._buffer_duration:
            return self._flush_buffer()
        
        return None
    
    def _flush_buffer(self) -> Optional[TranscriptionResult]:
        """清空缓冲区并转录"""
        if not self._buffer:
            return None
        
        try:
            # 合并音频
            audio_data = merge_audio_chunks(self._buffer)
            self._buffer.clear()
            
            # 转换为 WAV
            wav_data = audio_to_wav(audio_data, self._sample_rate)
            
            # 调用 API
            result = self._transcribe(wav_data)
            
            if result:
                return TranscriptionResult(
                    text=result,
                    timestamp=datetime.now(),
                    language=self.language
                )
            
            return None
            
        except Exception as e:
            print(f"Transcription error: {e}")
            self._buffer.clear()
            return None
    
    def _transcribe(self, wav_data: bytes) -> Optional[str]:
        """调用 Groq Whisper API"""
        try:
            # 创建文件对象
            audio_file = io.BytesIO(wav_data)
            audio_file.name = "audio.wav"
            
            # 调用 API
            response = self.client.audio.transcriptions.create(
                file=audio_file,
                model=self.model,
                language=self.language
            )
            
            return response.text.strip() if response.text else None
            
        except Exception as e:
            print(f"Groq API error: {e}")
            return None
    
    def flush(self) -> Optional[TranscriptionResult]:
        """强制清空缓冲区"""
        return self._flush_buffer()


class OpenAISpeechRecognizer:
    """OpenAI 兼容语音识别器"""
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        model: str = "whisper-1",
        language: str = "ko"
    ):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.language = language
        
        self._buffer: list[AudioChunk] = []
        self._buffer_duration = 3.0
        self._sample_rate = 16000
    
    def add_chunk(self, chunk: AudioChunk) -> Optional[TranscriptionResult]:
        """添加音频块"""
        self._buffer.append(chunk)
        
        total_samples = sum(len(c.data) // 2 for c in self._buffer)
        duration = total_samples / self._sample_rate
        
        if duration >= self._buffer_duration:
            return self._flush_buffer()
        
        return None
    
    def _flush_buffer(self) -> Optional[TranscriptionResult]:
        """清空缓冲区并转录"""
        if not self._buffer:
            return None
        
        try:
            audio_data = merge_audio_chunks(self._buffer)
            self._buffer.clear()
            
            wav_data = audio_to_wav(audio_data, self._sample_rate)
            
            audio_file = io.BytesIO(wav_data)
            audio_file.name = "audio.wav"
            
            response = self.client.audio.transcriptions.create(
                file=audio_file,
                model=self.model,
                language=self.language
            )
            
            if response.text:
                return TranscriptionResult(
                    text=response.text.strip(),
                    timestamp=datetime.now(),
                    language=self.language
                )
            
            return None
            
        except Exception as e:
            print(f"OpenAI API error: {e}")
            self._buffer.clear()
            return None
    
    def flush(self) -> Optional[TranscriptionResult]:
        """强制清空缓冲区"""
        return self._flush_buffer()


def create_recognizer(
    provider: str,
    api_key: str,
    **kwargs
) -> SpeechRecognizer:
    """工厂函数：创建语音识别器"""
    
    if provider == "groq":
        return SpeechRecognizer(api_key=api_key, **kwargs)
    elif provider == "openai":
        return OpenAISpeechRecognizer(api_key=api_key, **kwargs)
    else:
        raise ValueError(f"Unsupported ASR provider: {provider}")

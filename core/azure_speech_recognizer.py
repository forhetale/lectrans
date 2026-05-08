"""
LecTrans Azure语音识别模块
使用Azure AI Speech API进行实时语音识别
"""

import time
import threading
from typing import Optional, Callable
from datetime import datetime
from dataclasses import dataclass

import azure.cognitiveservices.speech as speechsdk


@dataclass
class TranscriptionResult:
    """转录结果"""
    text: str
    timestamp: datetime
    language: str = "ko"
    confidence: float = 0.0


class AzureSpeechRecognizer:
    """Azure语音识别器"""
    
    def __init__(
        self,
        subscription_key: str,
        region: str,
        language: str = "ko-KR",
        endpoint: str = None
    ):
        self.subscription_key = subscription_key
        self.region = region
        self.language = language
        
        # 创建语音配置
        self.speech_config = speechsdk.SpeechConfig(
            subscription=subscription_key,
            region=region
        )
        
        # 设置语言
        self.speech_config.speech_recognition_language = language
        
        # 设置端点（如果有）
        if endpoint:
            self.speech_config.endpoint_id = endpoint
        
        # 设置输出格式为详细（包含置信度）
        self.speech_config.output_format = speechsdk.OutputFormat.Detailed
        
        # 识别器
        self.speech_recognizer = None
        self.is_listening = False
        
        # 回调函数
        self.on_recognizing: Callable[[str], None] = None  # 中间结果
        self.on_recognized: Callable[[TranscriptionResult], None] = None  # 最终结果
        self.on_error: Callable[[str], None] = None
        
        # 线程锁
        self._lock = threading.Lock()
    
    def start_continuous_recognition(self):
        """开始连续识别"""
        try:
            # 创建音频配置（使用默认麦克风）
            audio_config = speechsdk.AudioConfig(use_default_microphone=True)
            
            # 创建识别器
            self.speech_recognizer = speechsdk.SpeechRecognizer(
                speech_config=self.speech_config,
                audio_config=audio_config
            )
            
            # 连接事件
            self.speech_recognizer.recognizing.connect(self._on_recognizing)
            self.speech_recognizer.recognized.connect(self._on_recognized)
            self.speech_recognizer.canceled.connect(self._on_canceled)
            self.speech_recognizer.session_stopped.connect(self._on_session_stopped)
            
            # 开始连续识别
            self.speech_recognizer.start_continuous_recognition()
            self.is_listening = True
            
            print(f"Azure语音识别已启动 (语言: {self.language})")
            return True
            
        except Exception as e:
            print(f"启动Azure语音识别失败: {e}")
            if self.on_error:
                self.on_error(str(e))
            return False
    
    def stop_continuous_recognition(self):
        """停止连续识别"""
        if self.speech_recognizer and self.is_listening:
            try:
                self.speech_recognizer.stop_continuous_recognition()
                self.is_listening = False
                print("Azure语音识别已停止")
            except Exception as e:
                print(f"停止Azure语音识别失败: {e}")
    
    def _on_recognizing(self, evt):
        """处理中间识别结果"""
        if evt.result.text and self.on_recognizing:
            self.on_recognizing(evt.result.text)
    
    def _on_recognized(self, evt):
        """处理最终识别结果"""
        if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
            text = evt.result.text.strip()
            if text and self.on_recognized:
                # 尝试获取置信度（从详细结果中）
                confidence = 0.0
                try:
                    import json
                    detailed_result = json.loads(evt.result.json)
                    if 'NBest' in detailed_result and detailed_result['NBest']:
                        confidence = detailed_result['NBest'][0].get('Confidence', 0.0)
                except:
                    pass
                
                result = TranscriptionResult(
                    text=text,
                    timestamp=datetime.now(),
                    language=self.language,
                    confidence=confidence
                )
                self.on_recognized(result)
        
        elif evt.result.reason == speechsdk.ResultReason.NoMatch:
            print("未识别到语音")
    
    def _on_canceled(self, evt):
        """处理取消事件"""
        print(f"识别被取消: {evt.result.cancellation_details.reason}")
        if evt.result.cancellation_details.reason == speechsdk.CancellationReason.Error:
            error_msg = f"错误代码: {evt.result.cancellation_details.error_code}, 详情: {evt.result.cancellation_details.error_details}"
            print(error_msg)
            if self.on_error:
                self.on_error(error_msg)
    
    def _on_session_stopped(self, evt):
        """处理会话停止事件"""
        print("识别会话已停止")
        self.is_listening = False
    
    def recognize_once(self) -> Optional[TranscriptionResult]:
        """单次识别（等待用户说完）"""
        try:
            audio_config = speechsdk.AudioConfig(use_default_microphone=True)
            speech_recognizer = speechsdk.SpeechRecognizer(
                speech_config=self.speech_config,
                audio_config=audio_config
            )
            
            print("请说话...")
            result = speech_recognizer.recognize_once()
            
            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                text = result.text.strip()
                if text:
                    return TranscriptionResult(
                        text=text,
                        timestamp=datetime.now(),
                        language=self.language
                    )
            elif result.reason == speechsdk.ResultReason.NoMatch:
                print("未识别到语音")
            elif result.reason == speechsdk.ResultReason.Canceled:
                print(f"识别被取消: {result.cancellation_details.reason}")
            
            return None
            
        except Exception as e:
            print(f"单次识别失败: {e}")
            return None
    
    def recognize_from_file(self, audio_file: str) -> Optional[TranscriptionResult]:
        """从文件识别"""
        try:
            audio_config = speechsdk.AudioConfig(filename=audio_file)
            speech_recognizer = speechsdk.SpeechRecognizer(
                speech_config=self.speech_config,
                audio_config=audio_config
            )
            
            result = speech_recognizer.recognize_once()
            
            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                text = result.text.strip()
                if text:
                    return TranscriptionResult(
                        text=text,
                        timestamp=datetime.now(),
                        language=self.language
                    )
            elif result.reason == speechsdk.ResultReason.NoMatch:
                print("未识别到语音")
            elif result.reason == speechsdk.ResultReason.Canceled:
                print(f"识别被取消: {result.cancellation_details.reason}")
            
            return None
            
        except Exception as e:
            print(f"文件识别失败: {e}")
            return None
    
    def recognize_from_bytes(self, audio_data: bytes, sample_rate: int = 16000) -> Optional[TranscriptionResult]:
        """从字节数据识别"""
        try:
            # 转换为WAV格式
            wav_data = audio_to_wav(audio_data, sample_rate)
            
            # 创建流
            audio_stream = speechsdk.audio.PushAudioInputStream()
            audio_config = speechsdk.AudioConfig(stream=audio_stream)
            
            # 创建识别器
            speech_recognizer = speechsdk.SpeechRecognizer(
                speech_config=self.speech_config,
                audio_config=audio_config
            )
            
            # 写入音频数据
            audio_stream.write(wav_data)
            audio_stream.close()
            
            # 识别
            result = speech_recognizer.recognize_once()
            
            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                text = result.text.strip()
                if text:
                    return TranscriptionResult(
                        text=text,
                        timestamp=datetime.now(),
                        language=self.language
                    )
            elif result.reason == speechsdk.ResultReason.NoMatch:
                print("未识别到语音")
            elif result.reason == speechsdk.ResultReason.Canceled:
                print(f"识别被取消: {result.cancellation_details.reason}")
            
            return None
            
        except Exception as e:
            print(f"字节数据识别失败: {e}")
            return None


class AzureSpeechRecognizerWithBuffer:
    """带缓冲区的Azure语音识别器"""
    
    def __init__(
        self,
        subscription_key: str,
        region: str,
        language: str = "ko-KR",
        buffer_duration: float = 3.0
    ):
        self.recognizer = AzureSpeechRecognizer(
            subscription_key=subscription_key,
            region=region,
            language=language
        )
        
        self.buffer_duration = buffer_duration
        self.sample_rate = 16000
        
        # 缓冲区
        self._buffer: list[AudioChunk] = []
        self._lock = threading.Lock()
        
        # 设置回调
        self.recognizer.on_recognized = self._on_recognized
        
        self.on_recognized: Callable[[TranscriptionResult], None] = None
    
    def start(self):
        """开始识别"""
        return self.recognizer.start_continuous_recognition()
    
    def stop(self):
        """停止识别"""
        self.recognizer.stop_continuous_recognition()
    
    def add_chunk(self, chunk: AudioChunk):
        """添加音频块（用于外部音频源）"""
        with self._lock:
            self._buffer.append(chunk)
            
            # 计算缓冲区时长
            total_samples = sum(len(c.data) // 2 for c in self._buffer)
            duration = total_samples / self.sample_rate
            
            if duration >= self.buffer_duration:
                self._flush_buffer()
    
    def _flush_buffer(self):
        """清空缓冲区并识别"""
        if not self._buffer:
            return
        
        try:
            # 合并音频
            audio_data = merge_audio_chunks(self._buffer)
            self._buffer.clear()
            
            # 识别
            result = self.recognizer.recognize_from_bytes(audio_data, self.sample_rate)
            
            if result and self.on_recognized:
                self.on_recognized(result)
                
        except Exception as e:
            print(f"缓冲区识别失败: {e}")
            self._buffer.clear()
    
    def _on_recognized(self, result: TranscriptionResult):
        """处理识别结果"""
        if self.on_recognized:
            self.on_recognized(result)


def create_azure_recognizer(
    subscription_key: str,
    region: str,
    language: str = "ko-KR",
    use_buffer: bool = True,
    buffer_duration: float = 3.0,
    **kwargs
):
    """工厂函数：创建Azure语音识别器"""
    if use_buffer:
        return AzureSpeechRecognizerWithBuffer(
            subscription_key=subscription_key,
            region=region,
            language=language,
            buffer_duration=buffer_duration
        )
    else:
        return AzureSpeechRecognizer(
            subscription_key=subscription_key,
            region=region,
            language=language,
            **kwargs
        )
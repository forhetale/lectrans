"""
LecTrans Azure语音识别模块
使用Azure AI Speech API进行实时语音识别
"""

import json
import io
import wave
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
        self.on_recognizing: Callable[[str], None] = None
        self.on_recognized: Callable[[TranscriptionResult], None] = None
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


def create_azure_recognizer(
    subscription_key: str,
    region: str,
    language: str = "ko-KR",
    **kwargs
):
    """工厂函数：创建Azure语音识别器"""
    return AzureSpeechRecognizer(
        subscription_key=subscription_key,
        region=region,
        language=language,
        **kwargs
    )
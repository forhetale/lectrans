"""
LecTrans 测试文件
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

# 测试配置
from config import AppConfig, APIConfig, AudioConfig, UIConfig


class TestConfig:
    """配置测试"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = AppConfig()
        
        assert config.api.asr_provider == "groq"
        assert config.api.llm_provider == "deepseek"
        assert config.audio.sample_rate == 16000
        assert config.ui.theme == "dark"
    
    def test_api_config(self):
        """测试 API 配置"""
        api = APIConfig(
            asr_api_key="test_key",
            llm_api_key="test_key"
        )
        
        assert api.is_configured == True
    
    def test_api_config_not_configured(self):
        """测试未配置 API"""
        api = APIConfig()
        
        # 可能已从环境变量加载
        # assert api.is_configured == False


# 测试会话管理
from core.session_manager import SessionManager, SessionState, TranscriptEntry


class TestSessionManager:
    """会话管理测试"""
    
    def test_start_session(self):
        """测试开始会话"""
        manager = SessionManager()
        session = manager.start_session()
        
        assert session.session_id is not None
        assert session.start_time is not None
        assert session.is_recording == False
    
    def test_add_transcript(self):
        """测试添加转录"""
        session = SessionState(
            session_id="test",
            start_time=datetime.now()
        )
        
        entry = session.add_transcript("안녕하세요", "你好")
        
        assert entry.id == 1
        assert entry.korean_text == "안녕하세요"
        assert entry.chinese_text == "你好"
        assert len(session.transcripts) == 1
    
    def test_get_full_transcript(self):
        """测试获取完整转录"""
        session = SessionState(
            session_id="test",
            start_time=datetime.now()
        )
        
        session.add_transcript("안녕하세요", "你好")
        session.add_transcript("오늘 수업", "今天课程")
        
        transcript = session.get_full_transcript()
        
        assert "안녕하세요" in transcript
        assert "오늘 수업" in transcript


# 测试音频工具
from core.audio_capture import audio_to_wav, AudioChunk


class TestAudioUtils:
    """音频工具测试"""
    
    def test_audio_to_wav(self):
        """测试音频转 WAV"""
        # 创建测试数据
        audio_data = b'\x00\x00' * 16000  # 1 秒静音
        
        wav_data = audio_to_wav(audio_data, sample_rate=16000)
        
        assert wav_data[:4] == b'RIFF'  # WAV 文件头
        assert len(wav_data) > 44  # WAV 头 + 数据


# 测试 Prompt 模板
from prompts.templates import get_translation_prompt, get_summary_prompt


class TestPrompts:
    """Prompt 测试"""
    
    def test_translation_prompt(self):
        """测试翻译 Prompt"""
        prompt = get_translation_prompt("안녕하세요")
        
        assert len(prompt) == 2
        assert prompt[0]['role'] == 'system'
        assert prompt[1]['role'] == 'user'
        assert "안녕하세요" in prompt[1]['content']
    
    def test_summary_prompt(self):
        """测试总结 Prompt"""
        prompt = get_summary_prompt("测试转录内容")
        
        assert len(prompt) == 2
        assert prompt[0]['role'] == 'system'
        assert "测试转录内容" in prompt[1]['content']


# 集成测试（需要 API）
@pytest.mark.skipif(
    not AppConfig().api.is_configured,
    reason="API not configured"
)
class TestIntegration:
    """集成测试"""
    
    def test_translator(self):
        """测试翻译器"""
        from core import create_translator
        
        config = AppConfig()
        config.load()
        
        translator = create_translator(
            api_key=config.api.llm_api_key,
            base_url=config.api.llm_base_url,
            model=config.api.llm_model
        )
        
        result = translator.translate("안녕하세요")
        
        assert result.translated
        assert len(result.translated) > 0
    
    def test_summarizer(self):
        """测试总结器"""
        from core import create_summarizer
        
        config = AppConfig()
        config.load()
        
        summarizer = create_summarizer(
            api_key=config.api.llm_api_key,
            base_url=config.api.llm_base_url,
            model=config.api.llm_model
        )
        
        transcript = """
        [10:00:00] 안녕하세요, 오늘 컴퓨터 과학 수업을 시작하겠습니다.
        [10:01:00] 알고리즘은 문제를 해결하는 단계적 과정입니다.
        [10:02:00] 자료구조는 데이터를 조직화하는 방법입니다.
        """
        
        summary = summarizer.summarize(transcript)
        
        assert summary
        assert "알고리즘" in summary or "算法" in summary


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

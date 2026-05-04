"""
LecTrans - Streamlit 主界面
"""

import streamlit as st
import time
from datetime import datetime
from pathlib import Path
import sys

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import AppConfig
from core import (
    AudioCapture,
    SpeechRecognizer,
    Translator,
    Summarizer,
    SessionManager,
    create_recognizer,
    create_translator,
    create_summarizer,
)


# ============================================================
# 页面配置
# ============================================================

st.set_page_config(
    page_title="LecTrans - 实时课堂翻译",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 自定义 CSS
st.markdown("""
<style>
    /* 暗黑模式 */
    .stApp {
        background-color: #0E1117;
        color: #FAFAFA;
    }
    
    /* 主容器 */
    .main-container {
        padding: 1rem;
    }
    
    /* 翻译区域 */
    .transcript-area {
        background-color: #1A1D24;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
        max-height: 60vh;
        overflow-y: auto;
    }
    
    /* 翻译条目 */
    .transcript-entry {
        background-color: #262730;
        border-radius: 6px;
        padding: 0.75rem;
        margin-bottom: 0.5rem;
        border-left: 3px solid #4F8CFF;
    }
    
    .timestamp {
        color: #6B7280;
        font-size: 0.75rem;
        font-family: 'JetBrains Mono', monospace;
    }
    
    .korean-text {
        color: #FAFAFA;
        font-size: 1rem;
        margin: 0.25rem 0;
    }
    
    .chinese-text {
        color: #A3A8B8;
        font-size: 1rem;
        margin: 0.25rem 0;
    }
    
    /* 控制按钮 */
    .control-bar {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background-color: #1A1D24;
        padding: 1rem;
        border-top: 1px solid #2D3748;
        z-index: 100;
    }
    
    /* 总结面板 */
    .summary-panel {
        background-color: #1A1D24;
        border-radius: 8px;
        padding: 1.5rem;
        border: 1px solid #2D3748;
    }
    
    /* 状态指示器 */
    .status-connected {
        color: #00D97E;
    }
    
    .status-disconnected {
        color: #FF4B4B;
    }
    
    .status-connecting {
        color: #FFB020;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# 初始化 Session State
# ============================================================

def init_session_state():
    """初始化 session state"""
    if 'config' not in st.session_state:
        st.session_state.config = AppConfig()
        st.session_state.config.load()
    
    if 'session_manager' not in st.session_state:
        st.session_state.session_manager = SessionManager()
    
    if 'is_recording' not in st.session_state:
        st.session_state.is_recording = False
    
    if 'is_connected' not in st.session_state:
        st.session_state.is_connected = False
    
    if 'transcripts' not in st.session_state:
        st.session_state.transcripts = []
    
    if 'summary' not in st.session_state:
        st.session_state.summary = None
    
    if 'show_summary' not in st.session_state:
        st.session_state.show_summary = False
    
    if 'show_settings' not in st.session_state:
        st.session_state.show_settings = False
    
    # 核心组件
    if 'audio_capture' not in st.session_state:
        st.session_state.audio_capture = None
    
    if 'recognizer' not in st.session_state:
        st.session_state.recognizer = None
    
    if 'translator' not in st.session_state:
        st.session_state.translator = None
    
    if 'summarizer' not in st.session_state:
        st.session_state.summarizer = None


# ============================================================
# 初始化组件
# ============================================================

def init_components():
    """初始化核心组件"""
    config = st.session_state.config
    
    if not config.api.is_configured:
        return False
    
    try:
        # 语音识别器
        st.session_state.recognizer = create_recognizer(
            provider=config.api.asr_provider,
            api_key=config.api.asr_api_key,
            model=config.api.asr_model
        )
        
        # 翻译器
        st.session_state.translator = create_translator(
            api_key=config.api.llm_api_key,
            base_url=config.api.llm_base_url,
            model=config.api.llm_model
        )
        
        # 总结器
        st.session_state.summarizer = create_summarizer(
            api_key=config.api.llm_api_key,
            base_url=config.api.llm_base_url,
            model=config.api.llm_model
        )
        
        st.session_state.is_connected = True
        return True
        
    except Exception as e:
        st.error(f"初始化失败: {e}")
        return False


# ============================================================
# 音频处理回调
# ============================================================

def on_audio_chunk(chunk):
    """音频块回调"""
    if not st.session_state.is_recording:
        return
    
    recognizer = st.session_state.recognizer
    translator = st.session_state.translator
    
    if not recognizer or not translator:
        return
    
    # 语音识别
    result = recognizer.add_chunk(chunk)
    
    if result and result.text.strip():
        # 翻译
        translation = translator.translate(result.text)
        
        # 添加到记录
        entry = {
            "timestamp": result.timestamp.strftime("%H:%M:%S"),
            "korean": result.text,
            "chinese": translation.translated
        }
        
        st.session_state.transcripts.append(entry)
        
        # 触发界面刷新
        st.rerun()


# ============================================================
# 控制函数
# ============================================================

def start_recording():
    """开始录音"""
    if not st.session_state.is_connected:
        if not init_components():
            st.error("请先配置 API")
            return
    
    # 开始新会话
    st.session_state.session_manager.start_session()
    
    # 创建音频采集器
    config = st.session_state.config
    st.session_state.audio_capture = AudioCapture(
        sample_rate=config.audio.sample_rate,
        chunk_size=config.audio.chunk_size,
        vad_mode=config.audio.vad_mode,
        on_audio=on_audio_chunk
    )
    
    if st.session_state.audio_capture.start():
        st.session_state.is_recording = True
        st.success("开始录音...")
    else:
        st.error("无法启动录音")


def stop_recording():
    """停止录音"""
    if st.session_state.audio_capture:
        st.session_state.audio_capture.stop()
        st.session_state.audio_capture = None
    
    # 结束会话
    st.session_state.session_manager.end_session()
    
    st.session_state.is_recording = False
    st.info("录音已停止")


def generate_summary():
    """生成总结"""
    if not st.session_state.transcripts:
        st.warning("暂无转录内容")
        return
    
    summarizer = st.session_state.summarizer
    if not summarizer:
        st.error("总结器未初始化")
        return
    
    # 构建转录文本
    transcript = "\n".join([
        f"[{t['timestamp']}] {t['korean']}"
        for t in st.session_state.transcripts
    ])
    
    # 生成总结
    with st.spinner("正在生成总结..."):
        summary = summarizer.summarize(transcript)
        st.session_state.summary = summary
    
    st.session_state.show_summary = True


def save_session():
    """保存会话"""
    manager = st.session_state.session_manager
    
    if not manager.current_session:
        st.warning("没有活跃会话")
        return
    
    # 添加转录记录
    for t in st.session_state.transcripts:
        manager.current_session.add_transcript(t['korean'], t['chinese'])
    
    # 添加总结
    manager.current_session.summary = st.session_state.summary
    
    # 保存
    filepath = manager.save_session()
    st.success(f"会话已保存: {filepath}")


def export_markdown():
    """导出 Markdown"""
    manager = st.session_state.session_manager
    
    if not manager.current_session:
        st.warning("没有活跃会话")
        return
    
    # 添加转录记录
    for t in st.session_state.transcripts:
        manager.current_session.add_transcript(t['korean'], t['chinese'])
    
    manager.current_session.summary = st.session_state.summary
    
    # 导出
    markdown = manager.export_markdown()
    
    # 提供下载
    st.download_button(
        label="下载 Markdown",
        data=markdown,
        file_name=f"lectrans_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
        mime="text/markdown"
    )


# ============================================================
# UI 组件
# ============================================================

def render_header():
    """渲染头部"""
    col1, col2, col3 = st.columns([6, 1, 1])
    
    with col1:
        st.markdown("# 🎓 LecTrans")
        st.caption("实时课堂翻译工具")
    
    with col2:
        if st.button("⚙️", help="设置"):
            st.session_state.show_settings = not st.session_state.show_settings
    
    with col3:
        if st.button("💾", help="保存会话"):
            save_session()


def render_transcript_area():
    """渲染翻译区域"""
    st.markdown("### 📝 实时翻译")
    
    # 创建两列布局
    col_ko, col_zh = st.columns(2)
    
    with col_ko:
        st.markdown("**🇰🇷 한국어 (Korean)**")
        ko_container = st.container()
        
        with ko_container:
            if st.session_state.transcripts:
                for entry in reversed(st.session_state.transcripts):
                    st.markdown(f"""
                    <div class="transcript-entry">
                        <span class="timestamp">{entry['timestamp']}</span>
                        <p class="korean-text">{entry['korean']}</p>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("等待录音开始...")
    
    with col_zh:
        st.markdown("**🇨🇳 中文 (Chinese)**")
        zh_container = st.container()
        
        with zh_container:
            if st.session_state.transcripts:
                for entry in reversed(st.session_state.transcripts):
                    st.markdown(f"""
                    <div class="transcript-entry">
                        <span class="timestamp">{entry['timestamp']}</span>
                        <p class="chinese-text">{entry['chinese']}</p>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("等待翻译...")


def render_control_bar():
    """渲染控制栏"""
    st.markdown("---")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.session_state.is_recording:
            if st.button("⏹️ Stop", use_container_width=True, type="primary"):
                stop_recording()
        else:
            if st.button("▶️ Start", use_container_width=True):
                start_recording()
    
    with col2:
        # 状态指示
        if st.session_state.is_connected:
            st.markdown('<p class="status-connected">● Connected</p>', unsafe_allow_html=True)
        else:
            st.markdown('<p class="status-disconnected">● Disconnected</p>', unsafe_allow_html=True)
    
    with col3:
        if st.button("📝 Summary", use_container_width=True):
            generate_summary()
    
    with col4:
        if st.button("📥 Export", use_container_width=True):
            export_markdown()


def render_summary_panel():
    """渲染总结面板"""
    if st.session_state.show_summary and st.session_state.summary:
        st.markdown("---")
        st.markdown("### 📚 课堂总结")
        
        st.markdown(st.session_state.summary)
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📋 复制总结"):
                st.code(st.session_state.summary)
        
        with col2:
            if st.button("✕ 关闭"):
                st.session_state.show_summary = False
                st.rerun()


def render_settings_panel():
    """渲染设置面板"""
    if not st.session_state.show_settings:
        return
    
    st.markdown("---")
    st.markdown("### ⚙️ 设置")
    
    config = st.session_state.config
    
    tab1, tab2, tab3 = st.tabs(["API 配置", "显示设置", "音频设置"])
    
    with tab1:
        st.markdown("**ASR 配置**")
        
        asr_provider = st.selectbox(
            "ASR 提供商",
            ["groq", "openai"],
            index=0 if config.api.asr_provider == "groq" else 1
        )
        
        asr_api_key = st.text_input(
            "ASR API Key",
            value=config.api.asr_api_key,
            type="password"
        )
        
        st.markdown("**LLM 配置**")
        
        llm_provider = st.selectbox(
            "LLM 提供商",
            ["xiaomi", "deepseek", "openai", "groq"],
            index=0,
            format_func=lambda x: {
                "xiaomi": "小米 MiMo",
                "deepseek": "DeepSeek",
                "openai": "OpenAI",
                "groq": "Groq"
            }.get(x, x)
        )
        
        # 根据 provider 自动设置默认值
        default_urls = {
            "xiaomi": "https://token-plan-cn.xiaomimimo.com/v1",
            "deepseek": "https://api.deepseek.com/v1",
            "openai": "https://api.openai.com/v1",
            "groq": "https://api.groq.com/openai/v1"
        }
        
        default_models = {
            "xiaomi": "mimo-v2.5-pro",
            "deepseek": "deepseek-chat",
            "openai": "gpt-4o",
            "groq": "llama-3.3-70b-versatile"
        }
        
        llm_api_key = st.text_input(
            "LLM API Key",
            value=config.api.llm_api_key,
            type="password"
        )
        
        llm_base_url = st.text_input(
            "LLM Base URL",
            value=config.api.llm_base_url or default_urls.get(llm_provider, ""),
            help="API 端点地址"
        )
        
        llm_model = st.text_input(
            "LLM Model",
            value=config.api.llm_model or default_models.get(llm_provider, ""),
            help="模型名称"
        )
    
    with tab2:
        font_size = st.slider("字体大小", 14, 24, config.ui.font_size)
        theme = st.selectbox("主题", ["dark", "light"], index=0)
    
    with tab3:
        sample_rate = st.selectbox("采样率", [16000, 44100, 48000], index=0)
        vad_mode = st.slider("VAD 灵敏度", 0, 3, config.audio.vad_mode)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("💾 保存设置"):
            # 更新配置
            config.api.asr_provider = asr_provider
            config.api.asr_api_key = asr_api_key
            config.api.llm_api_key = llm_api_key
            config.api.llm_base_url = llm_base_url
            config.api.llm_model = llm_model
            config.ui.font_size = font_size
            config.ui.theme = theme
            config.audio.sample_rate = sample_rate
            config.audio.vad_mode = vad_mode
            
            config.save()
            st.success("设置已保存")
            
            # 重新初始化组件
            init_components()
    
    with col2:
        if st.button("✕ 关闭设置"):
            st.session_state.show_settings = False
            st.rerun()


def render_statistics():
    """渲染统计信息"""
    if st.session_state.transcripts:
        st.markdown("---")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("转录条目", len(st.session_state.transcripts))
        
        with col2:
            if st.session_state.transcripts:
                first_time = st.session_state.transcripts[0]['timestamp']
                st.metric("开始时间", first_time)
        
        with col3:
            if st.session_state.summary:
                st.metric("总结状态", "✅ 已生成")
            else:
                st.metric("总结状态", "⏳ 待生成")


# ============================================================
# 主函数
# ============================================================

def main():
    """主函数"""
    # 初始化
    init_session_state()
    
    # 渲染界面
    render_header()
    
    # 检查配置
    if not st.session_state.config.api.is_configured:
        st.warning("⚠️ 请先配置 API Key")
        st.session_state.show_settings = True
    
    # 翻译区域
    render_transcript_area()
    
    # 总结面板
    render_summary_panel()
    
    # 统计信息
    render_statistics()
    
    # 设置面板
    render_settings_panel()
    
    # 控制栏（固定在底部）
    render_control_bar()


if __name__ == "__main__":
    main()

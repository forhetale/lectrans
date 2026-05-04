"""
LecTrans - Windows GUI 应用
设计风格参考 Stripe/Vercel：暗黑、简洁、专业
"""

import os
import sys
import json
import threading
import time
import io
import wave
from datetime import datetime
from pathlib import Path
from tkinter import *
from tkinter import ttk, messagebox, filedialog
from typing import Optional, List
import queue

# 配置目录
CONFIG_DIR = Path.home() / ".lectrans"
CONFIG_FILE = CONFIG_DIR / "config.json"
SESSIONS_DIR = CONFIG_DIR / "sessions"


# ============================================================
# 设计系统 - 参考 Stripe/Vercel
# ============================================================

class DesignSystem:
    """设计系统 - 暗黑主题"""
    
    # 颜色系统 - 参考 Vercel
    COLORS = {
        # 背景层级
        'bg_primary': '#0A0A0A',      # 最深背景
        'bg_secondary': '#111111',    # 卡片背景
        'bg_tertiary': '#1A1A1A',     # 输入框/悬浮
        'bg_elevated': '#222222',     # 弹出层
        
        # 文字层级
        'text_primary': '#EDEDED',    # 主文字（纯白太刺眼）
        'text_secondary': '#888888',  # 次要文字
        'text_muted': '#555555',      # 弱化文字
        
        # 品牌色 - 小米橙
        'accent': '#FF6900',
        'accent_hover': '#E55D00',
        'accent_light': 'rgba(255, 105, 0, 0.1)',
        
        # 状态色
        'success': '#00C853',
        'warning': '#FFB300',
        'error': '#FF3D00',
        
        # 边框
        'border': '#2A2A2A',
        'border_light': '#333333',
    }
    
    # 字体系统
    FONTS = {
        'display': ('Segoe UI', 24, 'bold'),
        'heading': ('Segoe UI', 16, 'bold'),
        'body': ('Segoe UI', 12),
        'body_bold': ('Segoe UI', 12, 'bold'),
        'caption': ('Segoe UI', 10),
        'mono': ('Consolas', 11),
    }
    
    # 间距系统
    SPACING = {
        'xs': 4,
        'sm': 8,
        'md': 12,
        'lg': 16,
        'xl': 24,
        'xxl': 32,
    }
    
    # 圆角
    RADIUS = {
        'sm': 4,
        'md': 8,
        'lg': 12,
        'xl': 16,
        'pill': 999,
    }


# ============================================================
# 配置管理
# ============================================================

class AppConfig:
    """应用配置"""
    
    def __init__(self):
        self.api_key = ""
        self.base_url = "https://api.xiaomimimo.com/v1"
        self.asr_model = "mimo-v2.5-asr"
        self.llm_model = "mimo-v2.5-pro"
        self.font_size = 13
        self.audio_device_index = -1  # -1 表示默认设备
        self.load()
    
    def load(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for key, value in data.items():
                    if hasattr(self, key):
                        setattr(self, key, value)
            except Exception:
                pass
    
    def save(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            'api_key': self.api_key,
            'base_url': self.base_url,
            'asr_model': self.asr_model,
            'llm_model': self.llm_model,
            'font_size': self.font_size,
            'audio_device_index': self.audio_device_index,
        }
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    @property
    def is_configured(self):
        return bool(self.api_key)


class TranscriptEntry:
    """转录条目"""
    def __init__(self, korean: str, chinese: str):
        self.timestamp = datetime.now()
        self.korean = korean
        self.chinese = chinese


# ============================================================
# MiMo API 客户端
# ============================================================

class MiMoClient:
    """MiMo API 客户端"""
    
    def __init__(self, api_key: str, base_url: str):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key, base_url=base_url)
    
    def transcribe(self, audio_data: bytes, model: str = "mimo-v2.5-asr") -> str:
        try:
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                wf.writeframes(audio_data)
            wav_buffer.seek(0)
            wav_buffer.name = "audio.wav"
            response = self.client.audio.transcriptions.create(file=wav_buffer, model=model, language="ko")
            return response.text.strip() if response.text else ""
        except Exception as e:
            print(f"ASR error: {e}")
            return ""
    
    def translate(self, korean_text: str, model: str = "mimo-v2.5-pro") -> str:
        if not korean_text.strip():
            return ""
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是资深韩中翻译官，专精学术翻译。只输出中文翻译。"},
                    {"role": "user", "content": korean_text}
                ],
                temperature=0.3, max_tokens=500
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"[翻译失败]"
    
    def summarize(self, transcript: str, model: str = "mimo-v2.5-pro") -> str:
        if not transcript.strip():
            return "暂无内容"
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是学术笔记整理专家。将课堂转录整理成结构化中文笔记，使用 Markdown 格式。包含：核心概念、重要知识点、作业/考试信息、待确认问题。"},
                    {"role": "user", "content": f"课堂转录：\n\n{transcript}"}
                ],
                temperature=0.3, max_tokens=2000
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"总结生成失败"


# ============================================================
# 音频设备管理
# ============================================================

class AudioManager:
    """音频设备管理"""
    
    @staticmethod
    def get_input_devices():
        """获取输入设备列表"""
        devices = [{'index': -1, 'name': '默认设备'}]
        try:
            import pyaudio
            p = pyaudio.PyAudio()
            for i in range(p.get_device_count()):
                info = p.get_device_info_by_index(i)
                if info['maxInputChannels'] > 0:
                    devices.append({'index': i, 'name': info['name']})
            p.terminate()
        except ImportError:
            pass
        except Exception:
            pass
        return devices


# ============================================================
# 自定义组件
# ============================================================

class ModernButton(Button):
    """现代风格按钮"""
    
    def __init__(self, parent, text='', style='primary', **kwargs):
        self.style_type = style
        self.ds = DesignSystem()
        
        # 根据样式设置颜色
        styles = {
            'primary': {
                'bg': self.ds.COLORS['accent'],
                'fg': '#FFFFFF',
                'activebackground': self.ds.COLORS['accent_hover'],
                'activeforeground': '#FFFFFF',
            },
            'secondary': {
                'bg': self.ds.COLORS['bg_tertiary'],
                'fg': self.ds.COLORS['text_primary'],
                'activebackground': self.ds.COLORS['border_light'],
                'activeforeground': self.ds.COLORS['text_primary'],
            },
            'ghost': {
                'bg': self.ds.COLORS['bg_primary'],
                'fg': self.ds.COLORS['text_secondary'],
                'activebackground': self.ds.COLORS['bg_tertiary'],
                'activeforeground': self.ds.COLORS['text_primary'],
            },
            'danger': {
                'bg': self.ds.COLORS['error'],
                'fg': '#FFFFFF',
                'activebackground': '#E53600',
                'activeforeground': '#FFFFFF',
            },
            'success': {
                'bg': self.ds.COLORS['success'],
                'fg': '#FFFFFF',
                'activebackground': '#00B54D',
                'activeforeground': '#FFFFFF',
            },
        }
        
        style_config = styles.get(style, styles['primary'])
        
        super().__init__(
            parent,
            text=text,
            bg=style_config['bg'],
            fg=style_config['fg'],
            activebackground=style_config['activebackground'],
            activeforeground=style_config['activeforeground'],
            relief='flat',
            borderwidth=0,
            padx=16,
            pady=8,
            cursor='hand2',
            font=DesignSystem.FONTS['body_bold'],
            **kwargs
        )
        
        # 悬停效果
        self.bind('<Enter>', self._on_enter)
        self.bind('<Leave>', self._on_leave)
    
    def _on_enter(self, e):
        if self.style_type == 'primary':
            self.configure(bg=self.ds.COLORS['accent_hover'])
        elif self.style_type == 'secondary':
            self.configure(bg=self.ds.COLORS['border_light'])
    
    def _on_leave(self, e):
        styles = {
            'primary': self.ds.COLORS['accent'],
            'secondary': self.ds.COLORS['bg_tertiary'],
            'ghost': self.ds.COLORS['bg_primary'],
            'danger': self.ds.COLORS['error'],
            'success': self.ds.COLORS['success'],
        }
        self.configure(bg=styles.get(self.style_type, self.ds.COLORS['accent']))


class ModernEntry(Entry):
    """现代风格输入框"""
    
    def __init__(self, parent, **kwargs):
        self.ds = DesignSystem()
        super().__init__(
            parent,
            bg=self.ds.COLORS['bg_tertiary'],
            fg=self.ds.COLORS['text_primary'],
            insertbackground=self.ds.COLORS['text_primary'],
            relief='flat',
            borderwidth=0,
            font=self.ds.FONTS['body'],
            **kwargs
        )
        # 添加内边距效果
        self.configure(highlightthickness=1, highlightcolor=self.ds.COLORS['accent'], highlightbackground=self.ds.COLORS['border'])


class Card(Frame):
    """卡片组件"""
    
    def __init__(self, parent, **kwargs):
        self.ds = DesignSystem()
        super().__init__(
            parent,
            bg=self.ds.COLORS['bg_secondary'],
            highlightthickness=1,
            highlightbackground=self.ds.COLORS['border'],
            **kwargs
        )


class StatusBar(Frame):
    """状态栏"""
    
    def __init__(self, parent, **kwargs):
        self.ds = DesignSystem()
        super().__init__(parent, bg=self.ds.COLORS['bg_primary'], **kwargs)
        
        # 分隔线
        separator = Frame(self, height=1, bg=self.ds.COLORS['border'])
        separator.pack(fill=X, pady=(0, 8))
        
        # 状态内容
        self.status_dot = Label(self, text='●', fg=self.ds.COLORS['error'], bg=self.ds.COLORS['bg_primary'], font=('Segoe UI', 8))
        self.status_dot.pack(side=LEFT, padx=(0, 4))
        
        self.status_text = Label(self, text='未连接', fg=self.ds.COLORS['text_muted'], bg=self.ds.COLORS['bg_primary'], font=self.ds.FONTS['caption'])
        self.status_text.pack(side=LEFT, padx=(0, 16))
        
        self.entry_count = Label(self, text='0 entries', fg=self.ds.COLORS['text_muted'], bg=self.ds.COLORS['bg_primary'], font=self.ds.FONTS['caption'])
        self.entry_count.pack(side=LEFT)
        
        self.time_label = Label(self, text='', fg=self.ds.COLORS['text_muted'], bg=self.ds.COLORS['bg_primary'], font=self.ds.FONTS['mono'])
        self.time_label.pack(side=RIGHT)
        
        self.update_time()
    
    def update_time(self):
        self.time_label.config(text=datetime.now().strftime('%H:%M:%S'))
        self.after(1000, self.update_time)
    
    def set_connected(self, connected: bool):
        if connected:
            self.status_dot.config(fg=self.ds.COLORS['success'])
            self.status_text.config(text='已连接')
        else:
            self.status_dot.config(fg=self.ds.COLORS['error'])
            self.status_text.config(text='未连接')
    
    def set_entry_count(self, count: int):
        self.entry_count.config(text=f'{count} entries')


# ============================================================
# 主应用
# ============================================================

class LecTransApp:
    """LecTrans 主应用"""
    
    def __init__(self):
        self.root = Tk()
        self.root.title('LecTrans')
        self.root.geometry('1000x700')
        self.root.minsize(800, 500)
        
        self.ds = DesignSystem()
        self.config = AppConfig()
        
        # 状态
        self.is_recording = False
        self.is_connected = False
        self.transcripts: List[TranscriptEntry] = []
        self.summary = ''
        self.recording_start_time = None
        
        # 消息队列
        self.msg_queue = queue.Queue()
        
        # 组件
        self.mimo_client: Optional[MiMoClient] = None
        
        # 设置窗口
        self.root.configure(bg=self.ds.COLORS['bg_primary'])
        self.root.option_add('*TFrame.background', self.ds.COLORS['bg_primary'])
        self.root.option_add('*TLabel.background', self.ds.COLORS['bg_primary'])
        self.root.option_add('*TLabel.foreground', self.ds.COLORS['text_primary'])
        
        # 创建界面
        self.create_layout()
        
        # 检查配置
        if not self.config.is_configured:
            self.root.after(300, self.show_settings)
        
        # 处理消息队列
        self.root.after(100, self.process_queue)
        
        # 绑定窗口大小变化
        self.root.bind('<Configure>', self.on_window_resize)
    
    def create_layout(self):
        """创建主布局"""
        # 顶部导航栏
        self.create_navbar()
        
        # 主内容区（使用 Grid 布局实现自适应）
        self.main_frame = Frame(self.root, bg=self.ds.COLORS['bg_primary'])
        self.main_frame.pack(fill=BOTH, expand=True, padx=16, pady=(0, 16))
        
        # 配置网格权重
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.columnconfigure(1, weight=1)
        self.main_frame.rowconfigure(0, weight=1)
        
        # 左侧：韩语
        self.ko_card = self.create_transcript_card(self.main_frame, '🇰🇷 한국어', 'korean')
        self.ko_card.grid(row=0, column=0, sticky='nsew', padx=(0, 8))
        
        # 右侧：中文
        self.zh_card = self.create_transcript_card(self.main_frame, '🇨🇳 中文', 'chinese')
        self.zh_card.grid(row=0, column=1, sticky='nsew', padx=(8, 0))
        
        # 底部控制栏
        self.create_control_bar()
        
        # 状态栏
        self.status_bar = StatusBar(self.root)
        self.status_bar.pack(fill=X, side=BOTTOM, padx=16, pady=(0, 8))
    
    def create_navbar(self):
        """创建顶部导航栏"""
        navbar = Frame(self.root, bg=self.ds.COLORS['bg_secondary'], height=56)
        navbar.pack(fill=X)
        navbar.pack_propagate(False)
        
        # 左侧：Logo
        left = Frame(navbar, bg=self.ds.COLORS['bg_secondary'])
        left.pack(side=LEFT, padx=16)
        
        Label(left, text='🎓', font=('Segoe UI', 18), bg=self.ds.COLORS['bg_secondary']).pack(side=LEFT)
        Label(left, text=' LecTrans', font=('Segoe UI', 16, 'bold'), fg=self.ds.COLORS['text_primary'], bg=self.ds.COLORS['bg_secondary']).pack(side=LEFT, padx=(8, 0))
        Label(left, text=' MiMo Powered', font=('Segoe UI', 9), fg=self.ds.COLORS['text_muted'], bg=self.ds.COLORS['bg_secondary']).pack(side=LEFT, padx=(8, 0))
        
        # 右侧：按钮
        right = Frame(navbar, bg=self.ds.COLORS['bg_secondary'])
        right.pack(side=RIGHT, padx=16)
        
        ModernButton(right, text='⚙️ 设置', style='ghost', command=self.show_settings).pack(side=LEFT, padx=2)
        ModernButton(right, text='💾 保存', style='ghost', command=self.save_session).pack(side=LEFT, padx=2)
        ModernButton(right, text='📥 导出', style='ghost', command=self.export_markdown).pack(side=LEFT, padx=2)
        
        # 分隔线
        Frame(self.root, height=1, bg=self.ds.COLORS['border']).pack(fill=X)
    
    def create_transcript_card(self, parent, title, text_type):
        """创建转录卡片"""
        card = Card(parent)
        
        # 标题栏
        header = Frame(card, bg=self.ds.COLORS['bg_secondary'])
        header.pack(fill=X, padx=16, pady=(12, 8))
        
        Label(header, text=title, font=self.ds.FONTS['heading'], fg=self.ds.COLORS['text_primary'], bg=self.ds.COLORS['bg_secondary']).pack(side=LEFT)
        
        # 文本区域
        text_frame = Frame(card, bg=self.ds.COLORS['bg_secondary'])
        text_frame.pack(fill=BOTH, expand=True, padx=12, pady=(0, 12))
        
        text_widget = Text(
            text_frame,
            wrap=WORD,
            font=('Segoe UI', self.config.font_size),
            bg=self.ds.COLORS['bg_secondary'],
            fg=self.ds.COLORS['text_primary'],
            insertbackground=self.ds.COLORS['text_primary'],
            selectbackground=self.ds.COLORS['accent'],
            selectforeground='#FFFFFF',
            relief='flat',
            borderwidth=0,
            padx=8,
            pady=8,
            state=DISABLED
        )
        text_widget.pack(fill=BOTH, expand=True)
        
        # 添加滚动条
        scrollbar = Scrollbar(text_frame, command=text_widget.yview)
        scrollbar.pack(side=RIGHT, fill=Y)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        # 保存引用
        if text_type == 'korean':
            self.ko_text = text_widget
        else:
            self.zh_text = text_widget
        
        return card
    
    def create_control_bar(self):
        """创建控制栏"""
        control_frame = Frame(self.root, bg=self.ds.COLORS['bg_primary'])
        control_frame.pack(fill=X, padx=16, pady=12)
        
        # 左侧：录音控制
        left = Frame(control_frame, bg=self.ds.COLORS['bg_primary'])
        left.pack(side=LEFT)
        
        self.record_btn = ModernButton(left, text='⏺ 开始录音', style='success', command=self.toggle_recording, width=12)
        self.record_btn.pack(side=LEFT, padx=(0, 8))
        
        # 录音时长
        self.recording_time_label = Label(left, text='', font=self.ds.FONTS['mono'], fg=self.ds.COLORS['text_muted'], bg=self.ds.COLORS['bg_primary'])
        self.recording_time_label.pack(side=LEFT, padx=(0, 16))
        
        # 设备选择
        device_frame = Frame(left, bg=self.ds.COLORS['bg_primary'])
        device_frame.pack(side=LEFT)
        
        Label(device_frame, text='🎤', font=('Segoe UI', 12), bg=self.ds.COLORS['bg_primary']).pack(side=LEFT, padx=(0, 4))
        
        self.device_var = StringVar(value='默认设备')
        devices = AudioManager.get_input_devices()
        device_names = [d['name'] for d in devices]
        
        self.device_combo = ttk.Combobox(
            device_frame,
            textvariable=self.device_var,
            values=device_names,
            state='readonly',
            width=20
        )
        self.device_combo.pack(side=LEFT)
        self.device_combo.bind('<<ComboboxSelected>>', self.on_device_change)
        
        # 右侧：功能按钮
        right = Frame(control_frame, bg=self.ds.COLORS['bg_primary'])
        right.pack(side=RIGHT)
        
        ModernButton(right, text='📝 生成总结', style='primary', command=self.generate_summary).pack(side=LEFT, padx=4)
        ModernButton(right, text='🗑️ 清空', style='secondary', command=self.clear_transcript).pack(side=LEFT, padx=4)
    
    def on_window_resize(self, event):
        """窗口大小变化处理"""
        if event.widget == self.root:
            width = event.width
            
            # 根据宽度调整字体大小
            if width < 900:
                new_size = 11
            elif width < 1100:
                new_size = 13
            else:
                new_size = 14
            
            if hasattr(self, '_last_font_size') and self._last_font_size != new_size:
                self._last_font_size = new_size
                font = ('Segoe UI', new_size)
                self.ko_text.configure(font=font)
                self.zh_text.configure(font=font)
            elif not hasattr(self, '_last_font_size'):
                self._last_font_size = new_size
    
    def on_device_change(self, event):
        """设备选择变化"""
        device_name = self.device_var.get()
        devices = AudioManager.get_input_devices()
        for d in devices:
            if d['name'] == device_name:
                self.config.audio_device_index = d['index']
                self.config.save()
                break
    
    def process_queue(self):
        """处理消息队列"""
        try:
            while True:
                msg_type, data = self.msg_queue.get_nowait()
                if msg_type == 'transcript':
                    self.add_transcript(data['korean'], data['chinese'])
                elif msg_type == 'status':
                    self.update_status(data['connected'])
                elif msg_type == 'error':
                    messagebox.showerror('错误', data)
        except queue.Empty:
            pass
        self.root.after(100, self.process_queue)
    
    def init_components(self):
        """初始化组件"""
        try:
            self.mimo_client = MiMoClient(self.config.api_key, self.config.base_url)
            self.is_connected = True
            self.msg_queue.put(('status', {'connected': True}))
            return True
        except Exception as e:
            self.msg_queue.put(('error', f'初始化失败: {str(e)}'))
            return False
    
    def toggle_recording(self):
        """切换录音状态"""
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()
    
    def start_recording(self):
        """开始录音"""
        if not self.is_connected:
            if not self.init_components():
                return
        
        self.is_recording = True
        self.recording_start_time = datetime.now()
        self.record_btn.configure(text='⏹ 停止', style='danger')
        
        # 开始计时
        self.update_recording_time()
        
        # 启动录音线程
        threading.Thread(target=self.recording_loop, daemon=True).start()
    
    def stop_recording(self):
        """停止录音"""
        self.is_recording = False
        self.recording_start_time = None
        self.record_btn.configure(text='⏺ 开始录音', style='success')
        self.recording_time_label.config(text='')
    
    def update_recording_time(self):
        """更新录音时长"""
        if self.is_recording and self.recording_start_time:
            elapsed = datetime.now() - self.recording_start_time
            seconds = int(elapsed.total_seconds())
            minutes = seconds // 60
            seconds = seconds % 60
            self.recording_time_label.config(text=f'{minutes:02d}:{seconds:02d}')
            self.root.after(1000, self.update_recording_time)
    
    def recording_loop(self):
        """录音循环（模拟）"""
        sample_texts = [
            "안녕하세요, 오늘 컴퓨터 과학 수업을 시작하겠습니다.",
            "알고리즘은 문제를 해결하는 단계적 과정입니다.",
            "자료구조는 데이터를 조직화하는 방법입니다.",
            "시간 복잡도는 알고리즘의 효율성을 측정합니다.",
            "스택과 큐는 기본적인 자료구조입니다.",
            "이진 탐색 트리는 효율적인 데이터 검색을 가능하게 합니다.",
        ]
        
        idx = 0
        while self.is_recording:
            try:
                time.sleep(3)
                if not self.is_recording:
                    break
                
                korean = sample_texts[idx % len(sample_texts)]
                idx += 1
                
                chinese = self.mimo_client.translate(korean, self.config.llm_model)
                
                self.msg_queue.put(('transcript', {'korean': korean, 'chinese': chinese}))
                
            except Exception as e:
                print(f'Recording error: {e}')
                time.sleep(1)
    
    def add_transcript(self, korean: str, chinese: str):
        """添加转录"""
        entry = TranscriptEntry(korean, chinese)
        self.transcripts.append(entry)
        
        timestamp = f'[{entry.timestamp.strftime("%H:%M:%S")}]'
        
        # 更新韩语文本框
        self.ko_text.config(state=NORMAL)
        self.ko_text.insert(END, f'{timestamp}\n{korean}\n\n')
        self.ko_text.see(END)
        self.ko_text.config(state=DISABLED)
        
        # 更新中文文本框
        self.zh_text.config(state=NORMAL)
        self.zh_text.insert(END, f'{timestamp}\n{chinese}\n\n')
        self.zh_text.see(END)
        self.zh_text.config(state=DISABLED)
        
        # 更新状态栏
        self.status_bar.set_entry_count(len(self.transcripts))
    
    def clear_transcript(self):
        """清空转录"""
        if messagebox.askyesno('确认', '确定要清空所有记录吗？'):
            self.transcripts.clear()
            self.ko_text.config(state=NORMAL)
            self.ko_text.delete(1.0, END)
            self.ko_text.config(state=DISABLED)
            self.zh_text.config(state=NORMAL)
            self.zh_text.delete(1.0, END)
            self.zh_text.config(state=DISABLED)
            self.status_bar.set_entry_count(0)
    
    def generate_summary(self):
        """生成总结"""
        if not self.transcripts:
            messagebox.showwarning('提示', '暂无转录内容')
            return
        
        if not self.is_connected:
            if not self.init_components():
                return
        
        # 进度窗口
        progress = Toplevel(self.root)
        progress.title('生成中')
        progress.geometry('300x120')
        progress.configure(bg=self.ds.COLORS['bg_secondary'])
        progress.transient(self.root)
        progress.grab_set()
        
        Label(progress, text='正在生成总结...', font=self.ds.FONTS['body'], fg=self.ds.COLORS['text_primary'], bg=self.ds.COLORS['bg_secondary']).pack(pady=20)
        
        pb = ttk.Progressbar(progress, mode='indeterminate', length=200)
        pb.pack(pady=10)
        pb.start()
        
        def do_summarize():
            try:
                transcript = '\n'.join([f'[{e.timestamp.strftime("%H:%M:%S")}] {e.korean}' for e in self.transcripts])
                self.summary = self.mimo_client.summarize(transcript, self.config.llm_model)
                self.root.after(0, lambda: self.show_summary_window(self.summary))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror('错误', f'生成失败: {str(e)}'))
            finally:
                self.root.after(0, progress.destroy)
        
        threading.Thread(target=do_summarize, daemon=True).start()
    
    def show_summary_window(self, summary: str):
        """显示总结窗口"""
        win = Toplevel(self.root)
        win.title('📝 课堂总结')
        win.geometry('600x500')
        win.configure(bg=self.ds.COLORS['bg_primary'])
        
        # 文本区域
        text = Text(win, wrap=WORD, font=('Segoe UI', 12), bg=self.ds.COLORS['bg_secondary'], fg=self.ds.COLORS['text_primary'], relief='flat', padx=16, pady=16)
        text.pack(fill=BOTH, expand=True, padx=16, pady=16)
        text.insert(1.0, summary)
        
        # 按钮栏
        btn_frame = Frame(win, bg=self.ds.COLORS['bg_primary'])
        btn_frame.pack(fill=X, padx=16, pady=(0, 16))
        
        ModernButton(btn_frame, text='📋 复制', style='secondary', command=lambda: self.copy_to_clipboard(summary)).pack(side=LEFT, padx=4)
        ModernButton(btn_frame, text='💾 保存', style='primary', command=lambda: self.save_summary(summary)).pack(side=LEFT, padx=4)
        ModernButton(btn_frame, text='关闭', style='ghost', command=win.destroy).pack(side=RIGHT, padx=4)
    
    def copy_to_clipboard(self, text: str):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        messagebox.showinfo('提示', '已复制到剪贴板')
    
    def save_summary(self, summary: str):
        filepath = filedialog.asksaveasfilename(defaultextension='.md', filetypes=[('Markdown', '*.md')], initialfile=f'summary_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md')
        if filepath:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(summary)
            messagebox.showinfo('成功', f'已保存')
    
    def save_session(self):
        if not self.transcripts:
            messagebox.showwarning('提示', '暂无内容')
            return
        
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        filepath = filedialog.asksaveasfilename(
            defaultextension='.md',
            filetypes=[('Markdown', '*.md')],
            initialdir=str(SESSIONS_DIR),
            initialfile=f'session_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md'
        )
        
        if filepath:
            lines = [f'# LecTrans 课堂笔记\n\n', f'**日期**: {datetime.now().strftime("%Y-%m-%d %H:%M")}\n\n', f'**模型**: {self.config.asr_model} / {self.config.llm_model}\n\n', '---\n\n']
            
            for entry in self.transcripts:
                lines.append(f'### [{entry.timestamp.strftime("%H:%M:%S")}]\n')
                lines.append(f'**韩语**: {entry.korean}\n\n')
                lines.append(f'**中文**: {entry.chinese}\n\n')
                lines.append('---\n\n')
            
            if self.summary:
                lines.append(f'\n## 📚 总结\n\n{self.summary}')
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            messagebox.showinfo('成功', '已保存')
    
    def export_markdown(self):
        self.save_session()
    
    def update_status(self, connected: bool):
        self.is_connected = connected
        self.status_bar.set_connected(connected)
    
    def show_settings(self):
        """显示设置窗口"""
        win = Toplevel(self.root)
        win.title('设置')
        win.geometry('480x520')
        win.configure(bg=self.ds.COLORS['bg_primary'])
        win.transient(self.root)
        win.grab_set()
        
        # 主框架
        main = Frame(win, bg=self.ds.COLORS['bg_primary'])
        main.pack(fill=BOTH, expand=True, padx=24, pady=24)
        
        # 标题
        Label(main, text='⚙️ 设置', font=self.ds.FONTS['display'], fg=self.ds.COLORS['text_primary'], bg=self.ds.COLORS['bg_primary']).pack(anchor=W, pady=(0, 20))
        
        # API 配置卡片
        api_card = Card(main)
        api_card.pack(fill=X, pady=(0, 16))
        
        api_inner = Frame(api_card, bg=self.ds.COLORS['bg_secondary'])
        api_inner.pack(fill=X, padx=16, pady=16)
        
        Label(api_inner, text='🔑 MiMo API', font=self.ds.FONTS['heading'], fg=self.ds.COLORS['text_primary'], bg=self.ds.COLORS['bg_secondary']).pack(anchor=W, pady=(0, 12))
        
        # API Key
        Label(api_inner, text='API Key', font=self.ds.FONTS['caption'], fg=self.ds.COLORS['text_secondary'], bg=self.ds.COLORS['bg_secondary']).pack(anchor=W)
        self.api_key_var = StringVar(value=self.config.api_key)
        api_key_entry = ModernEntry(api_inner, textvariable=self.api_key_var, show='•')
        api_key_entry.pack(fill=X, pady=(4, 12))
        
        # Base URL
        Label(api_inner, text='Base URL', font=self.ds.FONTS['caption'], fg=self.ds.COLORS['text_secondary'], bg=self.ds.COLORS['bg_secondary']).pack(anchor=W)
        self.base_url_var = StringVar(value=self.config.base_url)
        ModernEntry(api_inner, textvariable=self.base_url_var).pack(fill=X, pady=(4, 12))
        
        # 模型选择
        model_frame = Frame(api_inner, bg=self.ds.COLORS['bg_secondary'])
        model_frame.pack(fill=X)
        
        # ASR 模型
        asr_frame = Frame(model_frame, bg=self.ds.COLORS['bg_secondary'])
        asr_frame.pack(side=LEFT, fill=X, expand=True, padx=(0, 8))
        
        Label(asr_frame, text='语音识别', font=self.ds.FONTS['caption'], fg=self.ds.COLORS['text_secondary'], bg=self.ds.COLORS['bg_secondary']).pack(anchor=W)
        self.asr_model_var = StringVar(value=self.config.asr_model)
        ttk.Combobox(asr_frame, textvariable=self.asr_model_var, values=['mimo-v2.5-asr'], state='readonly').pack(fill=X, pady=4)
        
        # LLM 模型
        llm_frame = Frame(model_frame, bg=self.ds.COLORS['bg_secondary'])
        llm_frame.pack(side=LEFT, fill=X, expand=True)
        
        Label(llm_frame, text='翻译/总结', font=self.ds.FONTS['caption'], fg=self.ds.COLORS['text_secondary'], bg=self.ds.COLORS['bg_secondary']).pack(anchor=W)
        self.llm_model_var = StringVar(value=self.config.llm_model)
        ttk.Combobox(llm_frame, textvariable=self.llm_model_var, values=['mimo-v2.5-pro', 'mimo-v2.5'], state='readonly').pack(fill=X, pady=4)
        
        # 提示
        Label(main, text='📌 获取 API Key: https://mimo.xiaomi.com', font=self.ds.FONTS['caption'], fg=self.ds.COLORS['text_muted'], bg=self.ds.COLORS['bg_primary']).pack(anchor=W, pady=(0, 16))
        
        # 按钮
        btn_frame = Frame(main, bg=self.ds.COLORS['bg_primary'])
        btn_frame.pack(fill=X)
        
        ModernButton(btn_frame, text='测试连接', style='secondary', command=self.test_connection).pack(side=LEFT, padx=(0, 8))
        ModernButton(btn_frame, text='保存', style='primary', command=lambda: self.save_settings(win)).pack(side=LEFT)
        ModernButton(btn_frame, text='取消', style='ghost', command=win.destroy).pack(side=RIGHT)
    
    def save_settings(self, win):
        self.config.api_key = self.api_key_var.get()
        self.config.base_url = self.base_url_var.get()
        self.config.asr_model = self.asr_model_var.get()
        self.config.llm_model = self.llm_model_var.get()
        self.config.save()
        self.is_connected = False
        self.init_components()
        messagebox.showinfo('成功', '设置已保存')
        win.destroy()
    
    def test_connection(self):
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key_var.get(), base_url=self.base_url_var.get())
            client.chat.completions.create(model=self.llm_model_var.get(), messages=[{'role': 'user', 'content': 'test'}], max_tokens=5)
            messagebox.showinfo('成功', '✅ 连接测试成功！')
        except Exception as e:
            messagebox.showerror('错误', f'连接失败: {str(e)}')
    
    def run(self):
        self.root.mainloop()


if __name__ == '__main__':
    app = LecTransApp()
    app.run()

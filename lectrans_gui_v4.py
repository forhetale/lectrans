"""
LecTrans - Windows GUI 应用 v4
使用 Azure Speech API 进行语音识别
"""

import os
import sys
import json
import threading
import time
import io
import wave
import struct
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
# 设计系统
# ============================================================

class DesignSystem:
    COLORS = {
        'bg_primary': '#0A0A0A',
        'bg_secondary': '#111111',
        'bg_tertiary': '#1A1A1A',
        'bg_elevated': '#222222',
        'text_primary': '#EDEDED',
        'text_secondary': '#888888',
        'text_muted': '#555555',
        'accent': '#FF6900',
        'accent_hover': '#E55D00',
        'success': '#00C853',
        'warning': '#FFB300',
        'error': '#FF3D00',
        'border': '#2A2A2A',
    }
    
    FONTS = {
        'display': ('Segoe UI', 24, 'bold'),
        'heading': ('Segoe UI', 16, 'bold'),
        'body': ('Segoe UI', 12),
        'body_bold': ('Segoe UI', 12, 'bold'),
        'caption': ('Segoe UI', 10),
        'mono': ('Consolas', 11),
        'small': ('Segoe UI', 9),
    }


# ============================================================
# 配置管理
# ============================================================

class AppConfig:
    def __init__(self):
        # Azure 配置
        self.azure_key = ""
        self.azure_region = "koreacentral"
        self.azure_language = "ko-KR"
        
        # MiMo 配置
        self.api_key = ""
        self.base_url = "https://token-plan-cn.xiaomimimo.com/v1"
        self.llm_model = "mimo-v2.5-pro"
        
        # 其他配置
        self.font_size = 13
        self.audio_device_index = -1
        self.sample_rate = 16000
        self.load()
    
    def load(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for key, value in data.items():
                    if hasattr(self, key):
                        setattr(self, key, value)
            except:
                pass
    
    def save(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            'azure_key': self.azure_key,
            'azure_region': self.azure_region,
            'azure_language': self.azure_language,
            'api_key': self.api_key,
            'base_url': self.base_url,
            'llm_model': self.llm_model,
            'font_size': self.font_size,
            'audio_device_index': self.audio_device_index,
            'sample_rate': self.sample_rate,
        }
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    @property
    def is_configured(self):
        return bool(self.azure_key and self.api_key)


class TranscriptEntry:
    def __init__(self, korean: str, chinese: str):
        self.timestamp = datetime.now()
        self.korean = korean
        self.chinese = chinese


# ============================================================
# MiMo API 客户端（翻译/总结）
# ============================================================

class MiMoClient:
    def __init__(self, api_key: str, base_url: str):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key, base_url=base_url)
    
    def translate(self, korean_text: str, model: str = "mimo-v2.5-pro") -> str:
        """翻译韩语为中文"""
        if not korean_text.strip():
            return ""
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是资深韩中翻译官，专精学术翻译。只输出中文翻译，不要输出韩语原文。"},
                    {"role": "user", "content": korean_text}
                ],
                temperature=0.3,
                max_tokens=500
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Translation error: {e}")
            return "[翻译失败]"
    
    def summarize(self, transcript: str, model: str = "mimo-v2.5-pro") -> str:
        """生成总结"""
        if not transcript.strip():
            return "暂无内容"
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是学术笔记整理专家。将课堂转录整理成结构化中文笔记，使用 Markdown 格式。包含：核心概念、重要知识点、作业/考试信息。"},
                    {"role": "user", "content": f"课堂转录：\n\n{transcript}"}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Summary error: {e}")
            return "总结生成失败"


# ============================================================
# 音频录制器
# ============================================================

class AudioRecorder:
    """真实音频录制器"""
    
    def __init__(self, sample_rate=16000, chunk_size=1024, device_index=-1):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.device_index = device_index
        self.is_recording = False
        self._audio = None
        self._stream = None
        self._buffer = []
        self._lock = threading.Lock()
    
    def start(self) -> bool:
        """开始录音"""
        try:
            import pyaudio
            self._audio = pyaudio.PyAudio()
            
            # 打开音频流
            self._stream = self._audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.sample_rate,
                input=True,
                input_device_index=self.device_index if self.device_index >= 0 else None,
                frames_per_buffer=self.chunk_size
            )
            
            self.is_recording = True
            self._buffer = []
            
            # 启动录音线程
            threading.Thread(target=self._record_loop, daemon=True).start()
            
            return True
            
        except ImportError:
            print("PyAudio not installed")
            return False
        except Exception as e:
            print(f"Audio start error: {e}")
            return False
    
    def stop(self) -> bytes:
        """停止录音并返回音频数据"""
        self.is_recording = False
        
        # 等待录音线程结束
        time.sleep(0.2)
        
        if self._stream:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except:
                pass
        
        if self._audio:
            try:
                self._audio.terminate()
            except:
                pass
        
        self._stream = None
        self._audio = None
        
        # 返回缓冲区数据
        with self._lock:
            data = b''.join(self._buffer)
            self._buffer = []
            return data
    
    def _record_loop(self):
        """录音循环"""
        while self.is_recording and self._stream:
            try:
                chunk = self._stream.read(self.chunk_size, exception_on_overflow=False)
                with self._lock:
                    self._buffer.append(chunk)
            except Exception as e:
                if self.is_recording:
                    print(f"Record error: {e}")
                break
    
    def get_buffer(self) -> bytes:
        """获取当前缓冲区数据"""
        with self._lock:
            if not self._buffer:
                return b''
            data = b''.join(self._buffer)
            self._buffer = []
            return data
    
    def buffer_duration(self) -> float:
        """缓冲区时长（秒）"""
        with self._lock:
            total_samples = sum(len(c) // 2 for c in self._buffer)
            return total_samples / self.sample_rate


# ============================================================
# 音频设备管理
# ============================================================

class AudioManager:
    @staticmethod
    def get_input_devices():
        """获取输入设备列表"""
        devices = [{'index': -1, 'name': '默认设备'}]
        try:
            import pyaudio
            p = pyaudio.PyAudio()
            for i in range(p.get_device_count()):
                try:
                    info = p.get_device_info_by_index(i)
                    if info['maxInputChannels'] > 0:
                        devices.append({
                            'index': i,
                            'name': f"{info['name']} (设备 {i})"
                        })
                except:
                    pass
            p.terminate()
        except:
            pass
        return devices


# ============================================================
# 主应用
# ============================================================

class LecTransApp:
    
    def __init__(self):
        self.root = Tk()
        self.root.title('LecTrans')
        self.root.geometry('1000x700')
        self.root.minsize(700, 450)
        
        self.ds = DesignSystem()
        self.config = AppConfig()
        
        # 状态
        self.is_recording = False
        self.is_connected = False
        self.transcripts: List[TranscriptEntry] = []
        self.summary = ''
        self.recording_start_time = None
        
        # 组件
        self.mimo_client: Optional[MiMoClient] = None
        self.azure_recognizer = None
        self.audio_recorder: Optional[AudioRecorder] = None
        self.msg_queue = queue.Queue()
        
        # 设置窗口
        self.root.configure(bg=self.ds.COLORS['bg_primary'])
        
        # 创建界面
        self.create_layout()
        
        # 检查配置
        if not self.config.is_configured:
            self.root.after(300, self.show_settings)
        
        # 处理消息队列
        self.root.after(100, self.process_queue)
    
    def create_layout(self):
        """创建布局"""
        
        # ==================== 顶部导航栏 ====================
        navbar = Frame(self.root, bg=self.ds.COLORS['bg_secondary'], height=50)
        navbar.pack(fill=X, side=TOP)
        navbar.pack_propagate(False)
        
        left_nav = Frame(navbar, bg=self.ds.COLORS['bg_secondary'])
        left_nav.pack(side=LEFT, padx=16)
        
        Label(left_nav, text='🎓', font=('Segoe UI', 16), bg=self.ds.COLORS['bg_secondary']).pack(side=LEFT)
        Label(left_nav, text='LecTrans', font=('Segoe UI', 14, 'bold'), fg=self.ds.COLORS['text_primary'], bg=self.ds.COLORS['bg_secondary']).pack(side=LEFT, padx=(6, 0))
        Label(left_nav, text='MiMo', font=self.ds.FONTS['small'], fg=self.ds.COLORS['accent'], bg=self.ds.COLORS['bg_secondary']).pack(side=LEFT, padx=(8, 0))
        
        right_nav = Frame(navbar, bg=self.ds.COLORS['bg_secondary'])
        right_nav.pack(side=RIGHT, padx=16)
        
        self._make_nav_btn(right_nav, '设置', self.show_settings)
        self._make_nav_btn(right_nav, '保存', self.save_session)
        self._make_nav_btn(right_nav, '导出', self.export_markdown)
        
        Frame(self.root, height=1, bg=self.ds.COLORS['border']).pack(fill=X)
        
        # ==================== 控制栏 ====================
        control_frame = Frame(self.root, bg=self.ds.COLORS['bg_tertiary'], height=60)
        control_frame.pack(fill=X, side=TOP)
        control_frame.pack_propagate(False)
        
        control_inner = Frame(control_frame, bg=self.ds.COLORS['bg_tertiary'])
        control_inner.pack(fill=BOTH, expand=True, padx=16, pady=10)
        
        # 录音按钮
        self.record_btn = Button(
            control_inner,
            text='⏺ 开始录音',
            font=self.ds.FONTS['body_bold'],
            bg=self.ds.COLORS['success'],
            fg='#FFFFFF',
            activebackground='#00B54D',
            relief='flat',
            padx=20,
            pady=6,
            cursor='hand2',
            command=self.toggle_recording
        )
        self.record_btn.pack(side=LEFT, padx=(0, 12))
        
        # 录音时长
        self.recording_time_label = Label(
            control_inner,
            text='',
            font=self.ds.FONTS['mono'],
            fg=self.ds.COLORS['accent'],
            bg=self.ds.COLORS['bg_tertiary'],
            width=6
        )
        self.recording_time_label.pack(side=LEFT, padx=(0, 16))
        
        # 设备选择
        Label(control_inner, text='🎤', font=('Segoe UI', 14), bg=self.ds.COLORS['bg_tertiary']).pack(side=LEFT, padx=(0, 4))
        
        self.device_var = StringVar(value='默认设备')
        devices = AudioManager.get_input_devices()
        self.device_list = devices
        device_names = [d['name'] for d in devices]
        
        self.device_combo = ttk.Combobox(
            control_inner,
            textvariable=self.device_var,
            values=device_names,
            state='readonly',
            width=20,
            font=self.ds.FONTS['small']
        )
        self.device_combo.pack(side=LEFT, padx=(0, 16))
        self.device_combo.bind('<<ComboboxSelected>>', self.on_device_change)
        
        # 右侧按钮
        Button(
            control_inner,
            text='📝 生成总结',
            font=self.ds.FONTS['body'],
            bg=self.ds.COLORS['accent'],
            fg='#FFFFFF',
            relief='flat',
            padx=12,
            pady=6,
            cursor='hand2',
            command=self.generate_summary
        ).pack(side=LEFT, padx=4)
        
        Button(
            control_inner,
            text='🗑️ 清空',
            font=self.ds.FONTS['body'],
            bg=self.ds.COLORS['bg_elevated'],
            fg=self.ds.COLORS['text_primary'],
            relief='flat',
            padx=12,
            pady=6,
            cursor='hand2',
            command=self.clear_transcript
        ).pack(side=LEFT, padx=4)
        
        # ==================== 内容区 ====================
        content_frame = Frame(self.root, bg=self.ds.COLORS['bg_primary'])
        content_frame.pack(fill=BOTH, expand=True, side=TOP)
        
        content_frame.columnconfigure(0, weight=1)
        content_frame.columnconfigure(1, weight=1)
        content_frame.rowconfigure(0, weight=1)
        
        self.ko_card = self._create_text_card(content_frame, '🇰🇷 한국어')
        self.ko_card.grid(row=0, column=0, sticky='nsew', padx=(8, 4), pady=8)
        
        self.zh_card = self._create_text_card(content_frame, '🇨🇳 中文')
        self.zh_card.grid(row=0, column=1, sticky='nsew', padx=(4, 8), pady=8)
        
        # ==================== 状态栏 ====================
        status_bar = Frame(self.root, bg=self.ds.COLORS['bg_secondary'], height=24)
        status_bar.pack(fill=X, side=BOTTOM)
        status_bar.pack_propagate(False)
        
        self.status_dot = Label(status_bar, text='●', fg=self.ds.COLORS['error'], bg=self.ds.COLORS['bg_secondary'], font=('Segoe UI', 8))
        self.status_dot.pack(side=LEFT, padx=(12, 4))
        
        self.status_text = Label(status_bar, text='ASR: Azure | 翻译: MiMo', fg=self.ds.COLORS['text_muted'], bg=self.ds.COLORS['bg_secondary'], font=self.ds.FONTS['caption'])
        self.status_text.pack(side=LEFT, padx=(0, 16))
        
        self.entry_count = Label(status_bar, text='0 entries', fg=self.ds.COLORS['text_muted'], bg=self.ds.COLORS['bg_secondary'], font=self.ds.FONTS['caption'])
        self.entry_count.pack(side=LEFT)
        
        self.time_label = Label(status_bar, text='', fg=self.ds.COLORS['text_muted'], bg=self.ds.COLORS['bg_secondary'], font=self.ds.FONTS['mono'])
        self.time_label.pack(side=RIGHT, padx=12)
        
        self._update_time()
    
    def _make_nav_btn(self, parent, text, command):
        btn = Button(parent, text=text, font=self.ds.FONTS['caption'], fg=self.ds.COLORS['text_secondary'], bg=self.ds.COLORS['bg_secondary'], activeforeground=self.ds.COLORS['text_primary'], activebackground=self.ds.COLORS['bg_secondary'], relief='flat', padx=8, pady=4, cursor='hand2', command=command)
        btn.pack(side=LEFT, padx=2)
        btn.bind('<Enter>', lambda e: btn.configure(fg=self.ds.COLORS['text_primary']))
        btn.bind('<Leave>', lambda e: btn.configure(fg=self.ds.COLORS['text_secondary']))
        return btn
    
    def _create_text_card(self, parent, title):
        card = Frame(parent, bg=self.ds.COLORS['bg_secondary'], highlightthickness=1, highlightbackground=self.ds.COLORS['border'])
        
        header = Frame(card, bg=self.ds.COLORS['bg_secondary'])
        header.pack(fill=X, padx=12, pady=(8, 4))
        Label(header, text=title, font=self.ds.FONTS['heading'], fg=self.ds.COLORS['text_primary'], bg=self.ds.COLORS['bg_secondary']).pack(side=LEFT)
        
        text_frame = Frame(card, bg=self.ds.COLORS['bg_secondary'])
        text_frame.pack(fill=BOTH, expand=True, padx=8, pady=(0, 8))
        
        text_widget = Text(text_frame, wrap=WORD, font=('Segoe UI', self.config.font_size), bg=self.ds.COLORS['bg_secondary'], fg=self.ds.COLORS['text_primary'], insertbackground=self.ds.COLORS['text_primary'], selectbackground=self.ds.COLORS['accent'], relief='flat', padx=8, pady=8, state=DISABLED)
        text_widget.pack(side=LEFT, fill=BOTH, expand=True)
        
        scrollbar = Scrollbar(text_frame, command=text_widget.yview)
        scrollbar.pack(side=RIGHT, fill=Y)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        if '한국어' in title:
            self.ko_text = text_widget
        else:
            self.zh_text = text_widget
        
        return card
    
    def _update_time(self):
        self.time_label.config(text=datetime.now().strftime('%H:%M:%S'))
        self.root.after(1000, self._update_time)
    
    def on_device_change(self, event):
        device_name = self.device_var.get()
        for d in self.device_list:
            if d['name'] == device_name:
                self.config.audio_device_index = d['index']
                self.config.save()
                break
    
    def process_queue(self):
        try:
            while True:
                msg_type, data = self.msg_queue.get_nowait()
                if msg_type == 'transcript':
                    self._add_transcript(data['korean'], data['chinese'])
                elif msg_type == 'status':
                    self._update_status(data['connected'])
                elif msg_type == 'error':
                    messagebox.showerror('错误', data)
                elif msg_type == 'log':
                    print(f"[LOG] {data}")
        except queue.Empty:
            pass
        self.root.after(100, self.process_queue)
    
    def init_components(self):
        """初始化组件"""
        if not self.config.azure_key:
            self.msg_queue.put(('error', '请在设置中配置 Azure Speech API Key'))
            return False
        
        if not self.config.api_key:
            self.msg_queue.put(('error', '请在设置中配置 MiMo API Key'))
            return False
        
        try:
            # MiMo客户端（翻译/总结）
            self.mimo_client = MiMoClient(self.config.api_key, self.config.base_url)
            
            # Azure语音识别器
            sys.path.insert(0, str(Path(__file__).parent))
            from core.azure_speech_recognizer import AzureSpeechRecognizer
            
            self.azure_recognizer = AzureSpeechRecognizer(
                subscription_key=self.config.azure_key,
                region=self.config.azure_region,
                language=self.config.azure_language
            )
            self.azure_recognizer.on_recognized = self._on_azure_recognized
            self.azure_recognizer.on_error = self._on_azure_error
            
            self.is_connected = True
            self.msg_queue.put(('status', {'connected': True}))
            return True
        except Exception as e:
            self.msg_queue.put(('error', f'初始化失败: {str(e)}'))
            return False
    
    def toggle_recording(self):
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()
    
    def start_recording(self):
        if not self.is_connected:
            if not self.init_components():
                return
        
        # 启动Azure连续识别
        if self.azure_recognizer and self.azure_recognizer.start_continuous_recognition():
            self.is_recording = True
            self.recording_start_time = datetime.now()
            self.record_btn.configure(text='⏹ 停止录音', bg=self.ds.COLORS['error'], activebackground='#E53600')
            self._update_recording_time()
        else:
            messagebox.showerror('错误', '无法启动语音识别，请检查麦克风')
    
    def stop_recording(self):
        self.is_recording = False
        
        if self.azure_recognizer:
            self.azure_recognizer.stop_continuous_recognition()
        
        self.recording_start_time = None
        self.record_btn.configure(text='⏺ 开始录音', bg=self.ds.COLORS['success'], activebackground='#00B54D')
        self.recording_time_label.config(text='')
    
    def _on_azure_recognized(self, result):
        """Azure识别结果回调"""
        korean = result.text
        if not korean or len(korean.strip()) < 2:
            return
        
        # 翻译
        chinese = self.mimo_client.translate(korean, self.config.llm_model)
        
        # 添加到界面
        self.msg_queue.put(('transcript', {'korean': korean, 'chinese': chinese}))
    
    def _on_azure_error(self, error):
        """Azure错误回调"""
        self.msg_queue.put(('error', f'Azure错误: {error}'))
    
    def _update_recording_time(self):
        if self.is_recording and self.recording_start_time:
            elapsed = datetime.now() - self.recording_start_time
            seconds = int(elapsed.total_seconds())
            m, s = divmod(seconds, 60)
            self.recording_time_label.config(text=f'{m:02d}:{s:02d}')
            self.root.after(1000, self._update_recording_time)
    
    def _add_transcript(self, korean: str, chinese: str):
        entry = TranscriptEntry(korean, chinese)
        self.transcripts.append(entry)
        
        ts = f'[{entry.timestamp.strftime("%H:%M:%S")}]'
        
        self.ko_text.config(state=NORMAL)
        self.ko_text.insert(END, f'{ts}\n{korean}\n\n')
        self.ko_text.see(END)
        self.ko_text.config(state=DISABLED)
        
        self.zh_text.config(state=NORMAL)
        self.zh_text.insert(END, f'{ts}\n{chinese}\n\n')
        self.zh_text.see(END)
        self.zh_text.config(state=DISABLED)
        
        self.entry_count.config(text=f'{len(self.transcripts)} entries')
    
    def clear_transcript(self):
        if messagebox.askyesno('确认', '确定清空所有记录？'):
            self.transcripts.clear()
            for w in [self.ko_text, self.zh_text]:
                w.config(state=NORMAL)
                w.delete(1.0, END)
                w.config(state=DISABLED)
            self.entry_count.config(text='0 entries')
    
    def generate_summary(self):
        if not self.transcripts:
            messagebox.showwarning('提示', '暂无转录内容')
            return
        
        if not self.is_connected:
            if not self.init_components():
                return
        
        progress = Toplevel(self.root)
        progress.title('生成中')
        progress.geometry('280x100')
        progress.configure(bg=self.ds.COLORS['bg_secondary'])
        progress.transient(self.root)
        progress.grab_set()
        
        Label(progress, text='正在生成总结...', font=self.ds.FONTS['body'], fg=self.ds.COLORS['text_primary'], bg=self.ds.COLORS['bg_secondary']).pack(pady=20)
        pb = ttk.Progressbar(progress, mode='indeterminate', length=200)
        pb.pack()
        pb.start()
        
        def do_summarize():
            try:
                transcript = '\n'.join([f'[{e.timestamp.strftime("%H:%M:%S")}] {e.korean}' for e in self.transcripts])
                self.summary = self.mimo_client.summarize(transcript, self.config.llm_model)
                self.root.after(0, lambda: self._show_summary(self.summary))
            except:
                self.root.after(0, lambda: messagebox.showerror('错误', '生成失败'))
            finally:
                self.root.after(0, progress.destroy)
        
        threading.Thread(target=do_summarize, daemon=True).start()
    
    def _show_summary(self, summary):
        win = Toplevel(self.root)
        win.title('课堂总结')
        win.geometry('550x450')
        win.configure(bg=self.ds.COLORS['bg_primary'])
        
        text = Text(win, wrap=WORD, font=('Segoe UI', 11), bg=self.ds.COLORS['bg_secondary'], fg=self.ds.COLORS['text_primary'], relief='flat', padx=16, pady=16)
        text.pack(fill=BOTH, expand=True, padx=16, pady=16)
        text.insert(1.0, summary)
        
        btn_frame = Frame(win, bg=self.ds.COLORS['bg_primary'])
        btn_frame.pack(fill=X, padx=16, pady=(0, 16))
        
        Button(btn_frame, text='复制', font=self.ds.FONTS['body'], bg=self.ds.COLORS['bg_elevated'], fg=self.ds.COLORS['text_primary'], relief='flat', padx=12, pady=6, command=lambda: self._copy(summary)).pack(side=LEFT, padx=4)
        Button(btn_frame, text='保存', font=self.ds.FONTS['body'], bg=self.ds.COLORS['accent'], fg='#FFFFFF', relief='flat', padx=12, pady=6, command=lambda: self._save_summary(summary)).pack(side=LEFT, padx=4)
        Button(btn_frame, text='关闭', font=self.ds.FONTS['body'], bg=self.ds.COLORS['bg_tertiary'], fg=self.ds.COLORS['text_primary'], relief='flat', padx=12, pady=6, command=win.destroy).pack(side=RIGHT, padx=4)
    
    def _copy(self, text):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        messagebox.showinfo('提示', '已复制')
    
    def _save_summary(self, summary):
        fp = filedialog.asksaveasfilename(defaultextension='.md', filetypes=[('Markdown', '*.md')])
        if fp:
            with open(fp, 'w', encoding='utf-8') as f:
                f.write(summary)
            messagebox.showinfo('成功', '已保存')
    
    def save_session(self):
        if not self.transcripts:
            messagebox.showwarning('提示', '暂无内容')
            return
        
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        fp = filedialog.asksaveasfilename(defaultextension='.md', filetypes=[('Markdown', '*.md')], initialdir=str(SESSIONS_DIR), initialfile=f'session_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md')
        
        if fp:
            lines = [f'# LecTrans 课堂笔记\n\n', f'**日期**: {datetime.now().strftime("%Y-%m-%d %H:%M")}\n\n', '---\n\n']
            for e in self.transcripts:
                lines.append(f'### [{e.timestamp.strftime("%H:%M:%S")}]\n**韩语**: {e.korean}\n\n**中文**: {e.chinese}\n\n---\n\n')
            if self.summary:
                lines.append(f'\n## 总结\n\n{self.summary}')
            with open(fp, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            messagebox.showinfo('成功', '已保存')
    
    def export_markdown(self):
        self.save_session()
    
    def _update_status(self, connected):
        self.is_connected = connected
        if connected:
            self.status_dot.config(fg=self.ds.COLORS['success'])
            self.status_text.config(text='ASR: Azure | 翻译: MiMo')
        else:
            self.status_dot.config(fg=self.ds.COLORS['error'])
            self.status_text.config(text='ASR: Azure | 翻译: 未连接')
    
    def show_settings(self):
        win = Toplevel(self.root)
        win.title('设置')
        win.geometry('480x580')
        win.configure(bg=self.ds.COLORS['bg_primary'])
        win.transient(self.root)
        win.grab_set()
        
        # 创建可滚动的画布
        canvas = Canvas(win, bg=self.ds.COLORS['bg_primary'], highlightthickness=0)
        scrollbar = Scrollbar(win, orient=VERTICAL, command=canvas.yview)
        scroll_frame = Frame(canvas, bg=self.ds.COLORS['bg_primary'])
        
        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=RIGHT, fill=Y)
        canvas.pack(side=LEFT, fill=BOTH, expand=True)
        
        main = Frame(scroll_frame, bg=self.ds.COLORS['bg_primary'])
        main.pack(fill=BOTH, expand=True, padx=24, pady=24)
        
        Label(main, text='⚙️ 设置', font=self.ds.FONTS['display'], fg=self.ds.COLORS['text_primary'], bg=self.ds.COLORS['bg_primary']).pack(anchor=W, pady=(0, 20))
        
        # Azure 语音识别配置
        azure_card = Frame(main, bg=self.ds.COLORS['bg_secondary'], highlightthickness=1, highlightbackground=self.ds.COLORS['border'])
        azure_card.pack(fill=X, pady=(0, 16))
        
        azure_inner = Frame(azure_card, bg=self.ds.COLORS['bg_secondary'])
        azure_inner.pack(fill=X, padx=16, pady=16)
        
        Label(azure_inner, text='🎤 Azure Speech API (语音识别)', font=self.ds.FONTS['heading'], fg=self.ds.COLORS['text_primary'], bg=self.ds.COLORS['bg_secondary']).pack(anchor=W, pady=(0, 12))
        
        Label(azure_inner, text='API Key', font=self.ds.FONTS['caption'], fg=self.ds.COLORS['text_secondary'], bg=self.ds.COLORS['bg_secondary']).pack(anchor=W)
        self.azure_key_var = StringVar(value=self.config.azure_key)
        Entry(azure_inner, textvariable=self.azure_key_var, show='•', font=self.ds.FONTS['body'], bg=self.ds.COLORS['bg_tertiary'], fg=self.ds.COLORS['text_primary'], relief='flat').pack(fill=X, pady=(4, 12))
        
        azure_config_frame = Frame(azure_inner, bg=self.ds.COLORS['bg_secondary'])
        azure_config_frame.pack(fill=X)
        
        f1 = Frame(azure_config_frame, bg=self.ds.COLORS['bg_secondary'])
        f1.pack(side=LEFT, fill=X, expand=True, padx=(0, 8))
        Label(f1, text='区域', font=self.ds.FONTS['caption'], fg=self.ds.COLORS['text_secondary'], bg=self.ds.COLORS['bg_secondary']).pack(anchor=W)
        self.azure_region_var = StringVar(value=self.config.azure_region)
        ttk.Combobox(f1, textvariable=self.azure_region_var, values=['koreacentral', 'eastasia', 'southeastasia', 'westeurope', 'eastus'], state='readonly').pack(fill=X, pady=4)
        
        f2 = Frame(azure_config_frame, bg=self.ds.COLORS['bg_secondary'])
        f2.pack(side=LEFT, fill=X, expand=True)
        Label(f2, text='语言', font=self.ds.FONTS['caption'], fg=self.ds.COLORS['text_secondary'], bg=self.ds.COLORS['bg_secondary']).pack(anchor=W)
        self.azure_language_var = StringVar(value=self.config.azure_language)
        ttk.Combobox(f2, textvariable=self.azure_language_var, values=['ko-KR', 'en-US', 'zh-CN', 'ja-JP'], state='readonly').pack(fill=X, pady=4)
        
        Label(azure_inner, text='📌 获取 Key: https://portal.azure.com', font=self.ds.FONTS['caption'], fg=self.ds.COLORS['text_muted'], bg=self.ds.COLORS['bg_secondary']).pack(anchor=W, pady=(8, 0))
        
        # MiMo API 配置（翻译/总结）
        mimo_card = Frame(main, bg=self.ds.COLORS['bg_secondary'], highlightthickness=1, highlightbackground=self.ds.COLORS['border'])
        mimo_card.pack(fill=X, pady=(0, 16))
        
        mimo_inner = Frame(mimo_card, bg=self.ds.COLORS['bg_secondary'])
        mimo_inner.pack(fill=X, padx=16, pady=16)
        
        Label(mimo_inner, text='🌐 MiMo API (翻译/总结)', font=self.ds.FONTS['heading'], fg=self.ds.COLORS['text_primary'], bg=self.ds.COLORS['bg_secondary']).pack(anchor=W, pady=(0, 12))
        
        Label(mimo_inner, text='API Key', font=self.ds.FONTS['caption'], fg=self.ds.COLORS['text_secondary'], bg=self.ds.COLORS['bg_secondary']).pack(anchor=W)
        self.api_key_var = StringVar(value=self.config.api_key)
        Entry(mimo_inner, textvariable=self.api_key_var, show='•', font=self.ds.FONTS['body'], bg=self.ds.COLORS['bg_tertiary'], fg=self.ds.COLORS['text_primary'], relief='flat').pack(fill=X, pady=(4, 12))
        
        Label(mimo_inner, text='Base URL', font=self.ds.FONTS['caption'], fg=self.ds.COLORS['text_secondary'], bg=self.ds.COLORS['bg_secondary']).pack(anchor=W)
        self.base_url_var = StringVar(value=self.config.base_url)
        Entry(mimo_inner, textvariable=self.base_url_var, font=self.ds.FONTS['body'], bg=self.ds.COLORS['bg_tertiary'], fg=self.ds.COLORS['text_primary'], relief='flat').pack(fill=X, pady=(4, 12))
        
        Label(mimo_inner, text='翻译模型', font=self.ds.FONTS['caption'], fg=self.ds.COLORS['text_secondary'], bg=self.ds.COLORS['bg_secondary']).pack(anchor=W)
        self.llm_model_var = StringVar(value=self.config.llm_model)
        ttk.Combobox(mimo_inner, textvariable=self.llm_model_var, values=['mimo-v2.5-pro', 'mimo-v2.5'], state='readonly').pack(fill=X, pady=4)
        
        Label(mimo_inner, text='📌 获取 Key: https://mimo.xiaomi.com', font=self.ds.FONTS['caption'], fg=self.ds.COLORS['text_muted'], bg=self.ds.COLORS['bg_secondary']).pack(anchor=W, pady=(8, 0))
        
        btn_frame = Frame(main, bg=self.ds.COLORS['bg_primary'])
        btn_frame.pack(fill=X, pady=(16, 0))
        
        Button(btn_frame, text='测试连接', font=self.ds.FONTS['body'], bg=self.ds.COLORS['bg_elevated'], fg=self.ds.COLORS['text_primary'], relief='flat', padx=12, pady=6, command=self._test_connection).pack(side=LEFT, padx=(0, 8))
        Button(btn_frame, text='保存', font=self.ds.FONTS['body_bold'], bg=self.ds.COLORS['accent'], fg='#FFFFFF', relief='flat', padx=16, pady=6, command=lambda: self._save_settings(win)).pack(side=LEFT)
        Button(btn_frame, text='取消', font=self.ds.FONTS['body'], bg=self.ds.COLORS['bg_tertiary'], fg=self.ds.COLORS['text_primary'], relief='flat', padx=12, pady=6, command=win.destroy).pack(side=RIGHT)
    
    def _save_settings(self, win):
        # 保存 Azure 配置
        self.config.azure_key = self.azure_key_var.get()
        self.config.azure_region = self.azure_region_var.get()
        self.config.azure_language = self.azure_language_var.get()
        
        # 保存 MiMo 配置
        self.config.api_key = self.api_key_var.get()
        self.config.base_url = self.base_url_var.get()
        self.config.llm_model = self.llm_model_var.get()
        
        self.config.save()
        self.is_connected = False
        self.init_components()
        messagebox.showinfo('成功', '设置已保存')
        win.destroy()
    
    def _test_connection(self):
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key_var.get(), base_url=self.base_url_var.get())
            client.chat.completions.create(model=self.llm_model_var.get(), messages=[{'role': 'user', 'content': 'test'}], max_tokens=5)
            messagebox.showinfo('成功', '✅ MiMo API 连接成功！')
        except Exception as e:
            messagebox.showerror('错误', f'连接失败: {str(e)}')
    
    def run(self):
        self.root.mainloop()


if __name__ == '__main__':
    app = LecTransApp()
    app.run()

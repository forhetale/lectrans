"""
LecTrans - Windows GUI 应用 v3
修复：控制栏始终可见，不被内容区挤压
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
# 设计系统
# ============================================================

class DesignSystem:
    """设计系统 - 暗黑主题"""
    
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
        'border_light': '#333333',
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
        self.api_key = ""
        self.base_url = "https://api.xiaomimimo.com/v1"
        self.asr_model = "mimo-v2.5-asr"
        self.llm_model = "mimo-v2.5-pro"
        self.font_size = 13
        self.audio_device_index = -1
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
    def __init__(self, korean: str, chinese: str):
        self.timestamp = datetime.now()
        self.korean = korean
        self.chinese = chinese


# ============================================================
# MiMo API 客户端
# ============================================================

class MiMoClient:
    def __init__(self, api_key: str, base_url: str):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key, base_url=base_url)
    
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
        except Exception:
            return "[翻译失败]"
    
    def summarize(self, transcript: str, model: str = "mimo-v2.5-pro") -> str:
        if not transcript.strip():
            return "暂无内容"
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是学术笔记整理专家。将课堂转录整理成结构化中文笔记，使用 Markdown 格式。"},
                    {"role": "user", "content": f"课堂转录：\n\n{transcript}"}
                ],
                temperature=0.3, max_tokens=2000
            )
            return response.choices[0].message.content.strip()
        except Exception:
            return "总结生成失败"


# ============================================================
# 音频设备管理
# ============================================================

class AudioManager:
    @staticmethod
    def get_input_devices():
        devices = [{'index': -1, 'name': '默认设备'}]
        try:
            import pyaudio
            p = pyaudio.PyAudio()
            for i in range(p.get_device_count()):
                info = p.get_device_info_by_index(i)
                if info['maxInputChannels'] > 0:
                    devices.append({'index': i, 'name': info['name']})
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
        self.root.minsize(700, 450)  # 设置最小尺寸
        
        self.ds = DesignSystem()
        self.config = AppConfig()
        
        # 状态
        self.is_recording = False
        self.is_connected = False
        self.transcripts: List[TranscriptEntry] = []
        self.summary = ''
        self.recording_start_time = None
        
        self.msg_queue = queue.Queue()
        self.mimo_client: Optional[MiMoClient] = None
        
        # 设置窗口背景
        self.root.configure(bg=self.ds.COLORS['bg_primary'])
        
        # 创建界面
        self.create_layout()
        
        # 检查配置
        if not self.config.is_configured:
            self.root.after(300, self.show_settings)
        
        # 处理消息队列
        self.root.after(100, self.process_queue)
    
    def create_layout(self):
        """
        布局结构（从上到下，固定高度优先）：
        1. 导航栏 - 固定 50px
        2. 控制栏 - 固定 60px（始终可见）
        3. 内容区 - 填充剩余空间
        4. 状态栏 - 固定 24px
        """
        
        # ==================== 顶部导航栏 ====================
        navbar = Frame(self.root, bg=self.ds.COLORS['bg_secondary'], height=50)
        navbar.pack(fill=X, side=TOP)
        navbar.pack_propagate(False)  # 固定高度
        
        # Logo
        left_nav = Frame(navbar, bg=self.ds.COLORS['bg_secondary'])
        left_nav.pack(side=LEFT, padx=16)
        
        Label(left_nav, text='🎓', font=('Segoe UI', 16), bg=self.ds.COLORS['bg_secondary']).pack(side=LEFT)
        Label(left_nav, text='LecTrans', font=('Segoe UI', 14, 'bold'), fg=self.ds.COLORS['text_primary'], bg=self.ds.COLORS['bg_secondary']).pack(side=LEFT, padx=(6, 0))
        Label(left_nav, text='MiMo', font=self.ds.FONTS['small'], fg=self.ds.COLORS['accent'], bg=self.ds.COLORS['bg_secondary']).pack(side=LEFT, padx=(8, 0))
        
        # 右侧按钮
        right_nav = Frame(navbar, bg=self.ds.COLORS['bg_secondary'])
        right_nav.pack(side=RIGHT, padx=16)
        
        self._make_nav_btn(right_nav, '设置', self.show_settings)
        self._make_nav_btn(right_nav, '保存', self.save_session)
        self._make_nav_btn(right_nav, '导出', self.export_markdown)
        
        # 分隔线
        Frame(self.root, height=1, bg=self.ds.COLORS['border']).pack(fill=X)
        
        # ==================== 控制栏（固定在顶部下方）====================
        control_frame = Frame(self.root, bg=self.ds.COLORS['bg_tertiary'], height=60)
        control_frame.pack(fill=X, side=TOP)
        control_frame.pack_propagate(False)  # 固定高度
        
        # 内部容器，用于居中对齐
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
            activeforeground='#FFFFFF',
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
        device_names = [d['name'] for d in devices]
        
        self.device_combo = ttk.Combobox(
            control_inner,
            textvariable=self.device_var,
            values=device_names,
            state='readonly',
            width=18,
            font=self.ds.FONTS['small']
        )
        self.device_combo.pack(side=LEFT, padx=(0, 16))
        
        # 右侧按钮
        Button(
            control_inner,
            text='📝 生成总结',
            font=self.ds.FONTS['body'],
            bg=self.ds.COLORS['accent'],
            fg='#FFFFFF',
            activebackground=self.ds.COLORS['accent_hover'],
            activeforeground='#FFFFFF',
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
            activebackground=self.ds.COLORS['border_light'],
            relief='flat',
            padx=12,
            pady=6,
            cursor='hand2',
            command=self.clear_transcript
        ).pack(side=LEFT, padx=4)
        
        # ==================== 内容区（填充剩余空间）====================
        content_frame = Frame(self.root, bg=self.ds.COLORS['bg_primary'])
        content_frame.pack(fill=BOTH, expand=True, side=TOP)
        
        # 使用 Grid 布局实现左右分栏
        content_frame.columnconfigure(0, weight=1)
        content_frame.columnconfigure(1, weight=1)
        content_frame.rowconfigure(0, weight=1)
        
        # 左侧：韩语
        self.ko_card = self._create_text_card(content_frame, '🇰🇷 한국어')
        self.ko_card.grid(row=0, column=0, sticky='nsew', padx=(8, 4), pady=8)
        
        # 右侧：中文
        self.zh_card = self._create_text_card(content_frame, '🇨🇳 中文')
        self.zh_card.grid(row=0, column=1, sticky='nsew', padx=(4, 8), pady=8)
        
        # ==================== 状态栏（固定在底部）====================
        status_bar = Frame(self.root, bg=self.ds.COLORS['bg_secondary'], height=24)
        status_bar.pack(fill=X, side=BOTTOM)
        status_bar.pack_propagate(False)
        
        # 状态点
        self.status_dot = Label(status_bar, text='●', fg=self.ds.COLORS['error'], bg=self.ds.COLORS['bg_secondary'], font=('Segoe UI', 8))
        self.status_dot.pack(side=LEFT, padx=(12, 4))
        
        self.status_text = Label(status_bar, text='未连接', fg=self.ds.COLORS['text_muted'], bg=self.ds.COLORS['bg_secondary'], font=self.ds.FONTS['caption'])
        self.status_text.pack(side=LEFT, padx=(0, 16))
        
        self.entry_count = Label(status_bar, text='0 entries', fg=self.ds.COLORS['text_muted'], bg=self.ds.COLORS['bg_secondary'], font=self.ds.FONTS['caption'])
        self.entry_count.pack(side=LEFT)
        
        self.time_label = Label(status_bar, text='', fg=self.ds.COLORS['text_muted'], bg=self.ds.COLORS['bg_secondary'], font=self.ds.FONTS['mono'])
        self.time_label.pack(side=RIGHT, padx=12)
        
        self._update_time()
    
    def _make_nav_btn(self, parent, text, command):
        btn = Button(
            parent,
            text=text,
            font=self.ds.FONTS['caption'],
            fg=self.ds.COLORS['text_secondary'],
            bg=self.ds.COLORS['bg_secondary'],
            activeforeground=self.ds.COLORS['text_primary'],
            activebackground=self.ds.COLORS['bg_secondary'],
            relief='flat',
            padx=8,
            pady=4,
            cursor='hand2',
            command=command
        )
        btn.pack(side=LEFT, padx=2)
        btn.bind('<Enter>', lambda e: btn.configure(fg=self.ds.COLORS['text_primary']))
        btn.bind('<Leave>', lambda e: btn.configure(fg=self.ds.COLORS['text_secondary']))
        return btn
    
    def _create_text_card(self, parent, title):
        """创建文本卡片"""
        card = Frame(parent, bg=self.ds.COLORS['bg_secondary'], highlightthickness=1, highlightbackground=self.ds.COLORS['border'])
        
        # 标题
        header = Frame(card, bg=self.ds.COLORS['bg_secondary'])
        header.pack(fill=X, padx=12, pady=(8, 4))
        
        Label(header, text=title, font=self.ds.FONTS['heading'], fg=self.ds.COLORS['text_primary'], bg=self.ds.COLORS['bg_secondary']).pack(side=LEFT)
        
        # 文本区域
        text_frame = Frame(card, bg=self.ds.COLORS['bg_secondary'])
        text_frame.pack(fill=BOTH, expand=True, padx=8, pady=(0, 8))
        
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
            padx=8,
            pady=8,
            state=DISABLED
        )
        text_widget.pack(side=LEFT, fill=BOTH, expand=True)
        
        scrollbar = Scrollbar(text_frame, command=text_widget.yview)
        scrollbar.pack(side=RIGHT, fill=Y)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        # 保存引用
        if '한국어' in title:
            self.ko_text = text_widget
        else:
            self.zh_text = text_widget
        
        return card
    
    def _update_time(self):
        self.time_label.config(text=datetime.now().strftime('%H:%M:%S'))
        self.root.after(1000, self._update_time)
    
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
        except queue.Empty:
            pass
        self.root.after(100, self.process_queue)
    
    def init_components(self):
        try:
            self.mimo_client = MiMoClient(self.config.api_key, self.config.base_url)
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
        
        self.is_recording = True
        self.recording_start_time = datetime.now()
        self.record_btn.configure(text='⏹ 停止录音', bg=self.ds.COLORS['error'], activebackground='#E53600')
        
        self._update_recording_time()
        threading.Thread(target=self._recording_loop, daemon=True).start()
    
    def stop_recording(self):
        self.is_recording = False
        self.recording_start_time = None
        self.record_btn.configure(text='⏺ 开始录音', bg=self.ds.COLORS['success'], activebackground='#00B54D')
        self.recording_time_label.config(text='')
    
    def _update_recording_time(self):
        if self.is_recording and self.recording_start_time:
            elapsed = datetime.now() - self.recording_start_time
            seconds = int(elapsed.total_seconds())
            m, s = divmod(seconds, 60)
            self.recording_time_label.config(text=f'{m:02d}:{s:02d}')
            self.root.after(1000, self._update_recording_time)
    
    def _recording_loop(self):
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
                print(f'Error: {e}')
                time.sleep(1)
    
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
            for text_widget in [self.ko_text, self.zh_text]:
                text_widget.config(state=NORMAL)
                text_widget.delete(1.0, END)
                text_widget.config(state=DISABLED)
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
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror('错误', f'生成失败'))
            finally:
                self.root.after(0, progress.destroy)
        
        threading.Thread(target=do_summarize, daemon=True).start()
    
    def _show_summary(self, summary: str):
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
        fp = filedialog.asksaveasfilename(
            defaultextension='.md',
            filetypes=[('Markdown', '*.md')],
            initialdir=str(SESSIONS_DIR),
            initialfile=f'session_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md'
        )
        
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
            self.status_text.config(text='已连接')
        else:
            self.status_dot.config(fg=self.ds.COLORS['error'])
            self.status_text.config(text='未连接')
    
    def show_settings(self):
        win = Toplevel(self.root)
        win.title('设置')
        win.geometry('450x480')
        win.configure(bg=self.ds.COLORS['bg_primary'])
        win.transient(self.root)
        win.grab_set()
        
        main = Frame(win, bg=self.ds.COLORS['bg_primary'])
        main.pack(fill=BOTH, expand=True, padx=24, pady=24)
        
        Label(main, text='⚙️ 设置', font=self.ds.FONTS['display'], fg=self.ds.COLORS['text_primary'], bg=self.ds.COLORS['bg_primary']).pack(anchor=W, pady=(0, 20))
        
        # API 卡片
        card = Frame(main, bg=self.ds.COLORS['bg_secondary'], highlightthickness=1, highlightbackground=self.ds.COLORS['border'])
        card.pack(fill=X, pady=(0, 16))
        
        inner = Frame(card, bg=self.ds.COLORS['bg_secondary'])
        inner.pack(fill=X, padx=16, pady=16)
        
        Label(inner, text='🔑 MiMo API', font=self.ds.FONTS['heading'], fg=self.ds.COLORS['text_primary'], bg=self.ds.COLORS['bg_secondary']).pack(anchor=W, pady=(0, 12))
        
        Label(inner, text='API Key', font=self.ds.FONTS['caption'], fg=self.ds.COLORS['text_secondary'], bg=self.ds.COLORS['bg_secondary']).pack(anchor=W)
        self.api_key_var = StringVar(value=self.config.api_key)
        e1 = Entry(inner, textvariable=self.api_key_var, show='•', font=self.ds.FONTS['body'], bg=self.ds.COLORS['bg_tertiary'], fg=self.ds.COLORS['text_primary'], relief='flat')
        e1.pack(fill=X, pady=(4, 12))
        
        Label(inner, text='Base URL', font=self.ds.FONTS['caption'], fg=self.ds.COLORS['text_secondary'], bg=self.ds.COLORS['bg_secondary']).pack(anchor=W)
        self.base_url_var = StringVar(value=self.config.base_url)
        Entry(inner, textvariable=self.base_url_var, font=self.ds.FONTS['body'], bg=self.ds.COLORS['bg_tertiary'], fg=self.ds.COLORS['text_primary'], relief='flat').pack(fill=X, pady=(4, 12))
        
        # 模型选择
        model_frame = Frame(inner, bg=self.ds.COLORS['bg_secondary'])
        model_frame.pack(fill=X)
        
        f1 = Frame(model_frame, bg=self.ds.COLORS['bg_secondary'])
        f1.pack(side=LEFT, fill=X, expand=True, padx=(0, 8))
        Label(f1, text='语音识别', font=self.ds.FONTS['caption'], fg=self.ds.COLORS['text_secondary'], bg=self.ds.COLORS['bg_secondary']).pack(anchor=W)
        self.asr_model_var = StringVar(value=self.config.asr_model)
        ttk.Combobox(f1, textvariable=self.asr_model_var, values=['mimo-v2.5-asr'], state='readonly').pack(fill=X, pady=4)
        
        f2 = Frame(model_frame, bg=self.ds.COLORS['bg_secondary'])
        f2.pack(side=LEFT, fill=X, expand=True)
        Label(f2, text='翻译/总结', font=self.ds.FONTS['caption'], fg=self.ds.COLORS['text_secondary'], bg=self.ds.COLORS['bg_secondary']).pack(anchor=W)
        self.llm_model_var = StringVar(value=self.config.llm_model)
        ttk.Combobox(f2, textvariable=self.llm_model_var, values=['mimo-v2.5-pro', 'mimo-v2.5'], state='readonly').pack(fill=X, pady=4)
        
        Label(main, text='📌 获取 Key: https://mimo.xiaomi.com', font=self.ds.FONTS['caption'], fg=self.ds.COLORS['text_muted'], bg=self.ds.COLORS['bg_primary']).pack(anchor=W, pady=(0, 16))
        
        btn_frame = Frame(main, bg=self.ds.COLORS['bg_primary'])
        btn_frame.pack(fill=X)
        
        Button(btn_frame, text='测试连接', font=self.ds.FONTS['body'], bg=self.ds.COLORS['bg_elevated'], fg=self.ds.COLORS['text_primary'], relief='flat', padx=12, pady=6, command=self._test_connection).pack(side=LEFT, padx=(0, 8))
        Button(btn_frame, text='保存', font=self.ds.FONTS['body_bold'], bg=self.ds.COLORS['accent'], fg='#FFFFFF', relief='flat', padx=16, pady=6, command=lambda: self._save_settings(win)).pack(side=LEFT)
        Button(btn_frame, text='取消', font=self.ds.FONTS['body'], bg=self.ds.COLORS['bg_tertiary'], fg=self.ds.COLORS['text_primary'], relief='flat', padx=12, pady=6, command=win.destroy).pack(side=RIGHT)
    
    def _save_settings(self, win):
        self.config.api_key = self.api_key_var.get()
        self.config.base_url = self.base_url_var.get()
        self.config.asr_model = self.asr_model_var.get()
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
            messagebox.showinfo('成功', '✅ 连接成功！')
        except Exception as e:
            messagebox.showerror('错误', f'连接失败: {str(e)}')
    
    def run(self):
        self.root.mainloop()


if __name__ == '__main__':
    app = LecTransApp()
    app.run()

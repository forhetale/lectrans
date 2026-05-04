"""
LecTrans - Windows GUI 应用
全部使用小米 MiMo API（ASR + LLM）
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


class AppConfig:
    """应用配置 - 全部使用 MiMo"""
    
    def __init__(self):
        # 统一使用 MiMo API
        self.api_key = ""
        self.base_url = "https://api.xiaomimimo.com/v1"
        
        # ASR 模型
        self.asr_model = "mimo-v2.5-asr"
        
        # LLM 模型（翻译/总结）
        self.llm_model = "mimo-v2.5-pro"
        
        # 显示配置
        self.font_size = 14
        
        self.load()
    
    def load(self):
        """加载配置"""
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
        """保存配置"""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            'api_key': self.api_key,
            'base_url': self.base_url,
            'asr_model': self.asr_model,
            'llm_model': self.llm_model,
            'font_size': self.font_size,
        }
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)


class TranscriptEntry:
    """转录条目"""
    def __init__(self, korean: str, chinese: str):
        self.timestamp = datetime.now()
        self.korean = korean
        self.chinese = chinese


class MiMoClient:
    """MiMo API 客户端（统一处理 ASR 和 LLM）"""
    
    def __init__(self, api_key: str, base_url: str):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key, base_url=base_url)
    
    def transcribe(self, audio_data: bytes, model: str = "mimo-v2.5-asr") -> str:
        """语音识别"""
        try:
            # 将音频数据转换为 WAV 格式
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(16000)
                wf.writeframes(audio_data)
            
            wav_buffer.seek(0)
            wav_buffer.name = "audio.wav"
            
            # 调用 ASR API
            response = self.client.audio.transcriptions.create(
                file=wav_buffer,
                model=model,
                language="ko"
            )
            
            return response.text.strip() if response.text else ""
            
        except Exception as e:
            print(f"ASR error: {e}")
            return ""
    
    def translate(self, korean_text: str, model: str = "mimo-v2.5-pro") -> str:
        """翻译韩语为中文"""
        if not korean_text.strip():
            return ""
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是资深韩中翻译官，专精学术翻译。只输出中文翻译，不要输出韩语原文。计算机专业术语使用标准中文译法。"},
                    {"role": "user", "content": korean_text}
                ],
                temperature=0.3,
                max_tokens=500
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Translation error: {e}")
            return f"[翻译失败: {str(e)}]"
    
    def summarize(self, transcript: str, model: str = "mimo-v2.5-pro") -> str:
        """生成总结"""
        if not transcript.strip():
            return "暂无转录内容"
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": """你是学术笔记整理专家。将课堂转录整理成结构化中文笔记。

输出格式：
## 📚 核心概念
1. [概念名称]：[简要解释]

## 📝 重要知识点
- [知识点]

## 📌 作业/考试信息
- [如有提及]

## ❓ 待确认问题
- [如有不确定内容]"""},
                    {"role": "user", "content": f"课堂转录内容：\n\n{transcript}"}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Summary error: {e}")
            return f"总结生成失败: {str(e)}"


class AudioCapture:
    """音频采集器"""
    
    def __init__(self, sample_rate=16000, chunk_size=1024):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.is_recording = False
        self._audio = None
        self._stream = None
        self._buffer = []
    
    def start(self) -> bool:
        """开始录音"""
        try:
            import pyaudio
            self._audio = pyaudio.PyAudio()
            self._stream = self._audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )
            self.is_recording = True
            self._buffer = []
            return True
        except ImportError:
            print("PyAudio not installed, using simulation mode")
            self.is_recording = True
            self._buffer = []
            return True
        except Exception as e:
            print(f"Audio start error: {e}")
            return False
    
    def stop(self):
        """停止录音"""
        self.is_recording = False
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
    
    def read_chunk(self) -> Optional[bytes]:
        """读取音频块"""
        if not self.is_recording:
            return None
        
        if self._stream:
            try:
                return self._stream.read(self.chunk_size, exception_on_overflow=False)
            except:
                return None
        
        # 模拟模式
        time.sleep(0.1)
        return b'\x00' * (self.chunk_size * 2)
    
    def get_buffer(self) -> bytes:
        """获取缓冲区数据"""
        data = b''.join(self._buffer)
        self._buffer.clear()
        return data
    
    def add_to_buffer(self, chunk: bytes):
        """添加到缓冲区"""
        self._buffer.append(chunk)
    
    def buffer_duration(self) -> float:
        """缓冲区时长（秒）"""
        total_samples = sum(len(c) // 2 for c in self._buffer)
        return total_samples / self.sample_rate


class LecTransApp:
    """LecTrans 主应用"""
    
    def __init__(self):
        self.root = Tk()
        self.root.title("LecTrans - 实时课堂翻译")
        self.root.geometry("1000x700")
        self.root.minsize(800, 500)
        
        # 配置
        self.config = AppConfig()
        
        # 状态
        self.is_recording = False
        self.is_connected = False
        self.transcripts: List[TranscriptEntry] = []
        self.summary = ""
        
        # 消息队列
        self.msg_queue = queue.Queue()
        
        # 核心组件
        self.mimo_client: Optional[MiMoClient] = None
        self.audio_capture: Optional[AudioCapture] = None
        
        # 颜色主题
        self.colors = {
            'bg': '#1E1E1E',
            'fg': '#FFFFFF',
            'accent': '#FF6900',  # 小米橙色
            'success': '#00D97E',
            'warning': '#FFB020',
            'error': '#FF4B4B',
            'surface': '#2D2D2D',
        }
        
        # 设置主题
        self.setup_theme()
        
        # 创建界面
        self.create_widgets()
        
        # 检查配置
        if not self.config.is_configured:
            self.root.after(500, self.show_settings)
        
        # 定时处理消息队列
        self.root.after(100, self.process_queue)
    
    def setup_theme(self):
        """设置主题"""
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure('TFrame', background=self.colors['bg'])
        style.configure('TLabel', background=self.colors['bg'], foreground=self.colors['fg'])
        style.configure('TButton', padding=6)
        
        self.root.configure(bg=self.colors['bg'])
    
    def create_widgets(self):
        """创建界面"""
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)
        
        self.create_header(main_frame)
        self.create_transcript_area(main_frame)
        self.create_control_bar(main_frame)
        self.create_status_bar(main_frame)
    
    def create_header(self, parent):
        """标题栏"""
        header = ttk.Frame(parent)
        header.pack(fill=X, pady=(0, 10))
        
        ttk.Label(header, text="🎓 LecTrans", font=('Segoe UI', 20, 'bold')).pack(side=LEFT)
        ttk.Label(header, text="MiMo 驱动 · 实时课堂翻译", font=('Segoe UI', 10)).pack(side=LEFT, padx=(10, 0))
        
        btn_frame = ttk.Frame(header)
        btn_frame.pack(side=RIGHT)
        
        ttk.Button(btn_frame, text="⚙️ 设置", command=self.show_settings).pack(side=LEFT, padx=2)
        ttk.Button(btn_frame, text="💾 保存", command=self.save_session).pack(side=LEFT, padx=2)
        ttk.Button(btn_frame, text="📥 导出", command=self.export_markdown).pack(side=LEFT, padx=2)
    
    def create_transcript_area(self, parent):
        """翻译区域"""
        transcript_frame = ttk.Frame(parent)
        transcript_frame.pack(fill=BOTH, expand=True)
        
        # 韩语
        ko_frame = ttk.LabelFrame(transcript_frame, text="🇰🇷 한국어 (Korean)")
        ko_frame.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 5))
        
        self.ko_text = Text(
            ko_frame, wrap=WORD, font=('Segoe UI', self.config.font_size),
            bg=self.colors['surface'], fg=self.colors['fg'],
            insertbackground=self.colors['fg'], state=DISABLED
        )
        self.ko_text.pack(fill=BOTH, expand=True, padx=5, pady=5)
        
        # 中文
        zh_frame = ttk.LabelFrame(transcript_frame, text="🇨🇳 中文 (Chinese)")
        zh_frame.pack(side=RIGHT, fill=BOTH, expand=True, padx=(5, 0))
        
        self.zh_text = Text(
            zh_frame, wrap=WORD, font=('Segoe UI', self.config.font_size),
            bg=self.colors['surface'], fg=self.colors['fg'],
            insertbackground=self.colors['fg'], state=DISABLED
        )
        self.zh_text.pack(fill=BOTH, expand=True, padx=5, pady=5)
    
    def create_control_bar(self, parent):
        """控制栏"""
        control_frame = ttk.Frame(parent)
        control_frame.pack(fill=X, pady=10)
        
        self.start_btn = ttk.Button(control_frame, text="▶️ 开始录音", command=self.toggle_recording)
        self.start_btn.pack(side=LEFT, padx=5)
        
        self.status_label = ttk.Label(control_frame, text="● 未连接", foreground=self.colors['error'])
        self.status_label.pack(side=LEFT, padx=20)
        
        self.model_label = ttk.Label(control_frame, text=f"模型: {self.config.llm_model}", foreground=self.colors['accent'])
        self.model_label.pack(side=LEFT, padx=10)
        
        ttk.Button(control_frame, text="📝 生成总结", command=self.generate_summary).pack(side=LEFT, padx=5)
        ttk.Button(control_frame, text="🗑️ 清空", command=self.clear_transcript).pack(side=RIGHT, padx=5)
    
    def create_status_bar(self, parent):
        """状态栏"""
        status_frame = ttk.Frame(parent)
        status_frame.pack(fill=X)
        
        self.entry_count_label = ttk.Label(status_frame, text="条目: 0")
        self.entry_count_label.pack(side=LEFT)
        
        self.time_label = ttk.Label(status_frame, text="")
        self.time_label.pack(side=RIGHT)
        
        self.update_time()
    
    def update_time(self):
        """更新时间"""
        self.time_label.config(text=datetime.now().strftime("%H:%M:%S"))
        self.root.after(1000, self.update_time)
    
    def process_queue(self):
        """处理消息队列"""
        try:
            while True:
                msg_type, data = self.msg_queue.get_nowait()
                if msg_type == "transcript":
                    self.add_transcript(data['korean'], data['chinese'])
                elif msg_type == "status":
                    self.update_status(data['connected'])
                elif msg_type == "error":
                    messagebox.showerror("错误", data)
        except queue.Empty:
            pass
        self.root.after(100, self.process_queue)
    
    def init_components(self):
        """初始化组件"""
        try:
            self.mimo_client = MiMoClient(
                api_key=self.config.api_key,
                base_url=self.config.base_url
            )
            
            self.audio_capture = AudioCapture()
            
            self.is_connected = True
            self.msg_queue.put(("status", {"connected": True}))
            return True
        except Exception as e:
            self.msg_queue.put(("error", f"初始化失败: {str(e)}"))
            return False
    
    def toggle_recording(self):
        """切换录音"""
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()
    
    def start_recording(self):
        """开始录音"""
        if not self.is_connected:
            if not self.init_components():
                return
        
        if self.audio_capture.start():
            self.is_recording = True
            self.start_btn.config(text="⏹️ 停止录音")
            threading.Thread(target=self.recording_loop, daemon=True).start()
        else:
            messagebox.showerror("错误", "无法启动录音")
    
    def stop_recording(self):
        """停止录音"""
        self.is_recording = False
        if self.audio_capture:
            self.audio_capture.stop()
        self.start_btn.config(text="▶️ 开始录音")
    
    def recording_loop(self):
        """录音循环"""
        while self.is_recording:
            try:
                chunk = self.audio_capture.read_chunk()
                if chunk:
                    self.audio_capture.add_to_buffer(chunk)
                    
                    # 检查缓冲区时长
                    if self.audio_capture.buffer_duration() >= 3.0:
                        audio_data = self.audio_capture.get_buffer()
                        
                        # 语音识别
                        korean = self.mimo_client.transcribe(
                            audio_data,
                            model=self.config.asr_model
                        )
                        
                        if korean:
                            # 翻译
                            chinese = self.mimo_client.translate(
                                korean,
                                model=self.config.llm_model
                            )
                            
                            self.msg_queue.put(("transcript", {
                                "korean": korean,
                                "chinese": chinese
                            }))
                
            except Exception as e:
                print(f"Recording error: {e}")
                time.sleep(0.5)
    
    def add_transcript(self, korean: str, chinese: str):
        """添加转录"""
        entry = TranscriptEntry(korean, chinese)
        self.transcripts.append(entry)
        
        timestamp = f"[{entry.timestamp.strftime('%H:%M:%S')}]"
        
        self.ko_text.config(state=NORMAL)
        self.ko_text.insert(END, f"{timestamp} {korean}\n\n")
        self.ko_text.see(END)
        self.ko_text.config(state=DISABLED)
        
        self.zh_text.config(state=NORMAL)
        self.zh_text.insert(END, f"{timestamp} {chinese}\n\n")
        self.zh_text.see(END)
        self.zh_text.config(state=DISABLED)
        
        self.entry_count_label.config(text=f"条目: {len(self.transcripts)}")
    
    def clear_transcript(self):
        """清空"""
        if messagebox.askyesno("确认", "确定要清空所有转录记录吗？"):
            self.transcripts.clear()
            self.ko_text.config(state=NORMAL)
            self.ko_text.delete(1.0, END)
            self.ko_text.config(state=DISABLED)
            self.zh_text.config(state=NORMAL)
            self.zh_text.delete(1.0, END)
            self.zh_text.config(state=DISABLED)
            self.entry_count_label.config(text="条目: 0")
    
    def generate_summary(self):
        """生成总结"""
        if not self.transcripts:
            messagebox.showwarning("提示", "暂无转录内容")
            return
        
        if not self.is_connected:
            if not self.init_components():
                return
        
        progress = Toplevel(self.root)
        progress.title("生成中")
        progress.geometry("300x100")
        progress.transient(self.root)
        progress.grab_set()
        
        Label(progress, text="正在生成总结，请稍候...").pack(pady=20)
        pb = ttk.Progressbar(progress, mode='indeterminate')
        pb.pack(padx=20, fill=X)
        pb.start()
        
        def do_summarize():
            try:
                transcript = "\n".join([
                    f"[{e.timestamp.strftime('%H:%M:%S')}] {e.korean}"
                    for e in self.transcripts
                ])
                
                self.summary = self.mimo_client.summarize(
                    transcript,
                    model=self.config.llm_model
                )
                
                self.root.after(0, lambda: self.show_summary_window(self.summary))
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", f"生成失败: {str(e)}"))
            finally:
                self.root.after(0, progress.destroy)
        
        threading.Thread(target=do_summarize, daemon=True).start()
    
    def show_summary_window(self, summary: str):
        """显示总结窗口"""
        win = Toplevel(self.root)
        win.title("📝 课堂总结")
        win.geometry("600x500")
        
        text = Text(win, wrap=WORD, font=('Segoe UI', 12))
        text.pack(fill=BOTH, expand=True, padx=10, pady=10)
        text.insert(1.0, summary)
        
        btn_frame = ttk.Frame(win)
        btn_frame.pack(fill=X, padx=10, pady=10)
        
        ttk.Button(btn_frame, text="📋 复制", command=lambda: self.copy_to_clipboard(summary)).pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="💾 保存", command=lambda: self.save_summary(summary)).pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="关闭", command=win.destroy).pack(side=RIGHT, padx=5)
    
    def copy_to_clipboard(self, text: str):
        """复制到剪贴板"""
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        messagebox.showinfo("提示", "已复制到剪贴板")
    
    def save_summary(self, summary: str):
        """保存总结"""
        filepath = filedialog.asksaveasfilename(
            defaultextension=".md",
            filetypes=[("Markdown", "*.md"), ("Text", "*.txt")],
            initialfile=f"summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        )
        if filepath:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(summary)
            messagebox.showinfo("成功", f"已保存到:\n{filepath}")
    
    def save_session(self):
        """保存会话"""
        if not self.transcripts:
            messagebox.showwarning("提示", "暂无转录内容")
            return
        
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        filepath = filedialog.asksaveasfilename(
            defaultextension=".md",
            filetypes=[("Markdown", "*.md")],
            initialdir=str(SESSIONS_DIR),
            initialfile=f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        )
        
        if filepath:
            lines = [
                "# LecTrans 课堂笔记\n\n",
                f"**日期**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n",
                f"**模型**: {self.config.asr_model} / {self.config.llm_model}\n\n",
                "---\n\n",
                "## 📝 转录内容\n\n"
            ]
            
            for entry in self.transcripts:
                lines.append(f"### [{entry.timestamp.strftime('%H:%M:%S')}]\n")
                lines.append(f"**韩语**: {entry.korean}\n\n")
                lines.append(f"**中文**: {entry.chinese}\n\n")
                lines.append("---\n\n")
            
            if self.summary:
                lines.append("\n## 📚 总结\n\n")
                lines.append(self.summary)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            messagebox.showinfo("成功", f"已保存到:\n{filepath}")
    
    def export_markdown(self):
        """导出"""
        self.save_session()
    
    def update_status(self, connected: bool):
        """更新状态"""
        self.is_connected = connected
        color = self.colors['success'] if connected else self.colors['error']
        text = "● 已连接" if connected else "● 未连接"
        self.status_label.config(text=text, foreground=color)
    
    def show_settings(self):
        """显示设置"""
        win = Toplevel(self.root)
        win.title("⚙️ 设置")
        win.geometry("500x500")
        win.transient(self.root)
        win.grab_set()
        
        # 主框架
        main_frame = ttk.Frame(win, padding=20)
        main_frame.pack(fill=BOTH, expand=True)
        
        # 标题
        ttk.Label(main_frame, text="🔑 MiMo API 配置", font=('Segoe UI', 14, 'bold')).pack(anchor=W, pady=(0, 15))
        
        # API Key
        ttk.Label(main_frame, text="API Key:").pack(anchor=W)
        self.api_key_var = StringVar(value=self.config.api_key)
        api_key_entry = ttk.Entry(main_frame, textvariable=self.api_key_var, show="*", width=50)
        api_key_entry.pack(fill=X, pady=(0, 10))
        
        # Base URL
        ttk.Label(main_frame, text="Base URL:").pack(anchor=W)
        self.base_url_var = StringVar(value=self.config.base_url)
        ttk.Entry(main_frame, textvariable=self.base_url_var, width=50).pack(fill=X, pady=(0, 10))
        
        # ASR 模型
        ttk.Label(main_frame, text="语音识别模型 (ASR):").pack(anchor=W)
        self.asr_model_var = StringVar(value=self.config.asr_model)
        asr_combo = ttk.Combobox(main_frame, textvariable=self.asr_model_var, values=["mimo-v2.5-asr"], state="readonly")
        asr_combo.pack(fill=X, pady=(0, 10))
        
        # LLM 模型
        ttk.Label(main_frame, text="翻译/总结模型 (LLM):").pack(anchor=W)
        self.llm_model_var = StringVar(value=self.config.llm_model)
        llm_combo = ttk.Combobox(main_frame, textvariable=self.llm_model_var, values=["mimo-v2.5-pro", "mimo-v2.5"], state="readonly")
        llm_combo.pack(fill=X, pady=(0, 10))
        
        # 字体大小
        ttk.Label(main_frame, text="字体大小:").pack(anchor=W)
        self.font_size_var = IntVar(value=self.config.font_size)
        ttk.Spinbox(main_frame, from_=10, to=24, textvariable=self.font_size_var, width=10).pack(anchor=W, pady=(0, 15))
        
        # 说明
        info_text = """
📌 获取 API Key:
1. 访问 https://mimo.xiaomi.com
2. 注册/登录账号
3. 在控制台获取 API Key

📌 MiMo 模型说明:
• mimo-v2.5-asr: 语音识别（韩语转文字）
• mimo-v2.5-pro: 翻译和总结（最强）
• mimo-v2.5: 翻译和总结（标准）
        """
        ttk.Label(main_frame, text=info_text, justify=LEFT, foreground='gray').pack(anchor=W, pady=(0, 15))
        
        # 按钮
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=X)
        
        ttk.Button(btn_frame, text="🔍 测试连接", command=self.test_connection).pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="💾 保存", command=lambda: self.save_settings(win)).pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=win.destroy).pack(side=RIGHT, padx=5)
    
    def save_settings(self, win):
        """保存设置"""
        self.config.api_key = self.api_key_var.get()
        self.config.base_url = self.base_url_var.get()
        self.config.asr_model = self.asr_model_var.get()
        self.config.llm_model = self.llm_model_var.get()
        self.config.font_size = self.font_size_var.get()
        
        self.config.save()
        self.is_connected = False
        self.init_components()
        
        self.model_label.config(text=f"模型: {self.config.llm_model}")
        
        messagebox.showinfo("成功", "设置已保存")
        win.destroy()
    
    def test_connection(self):
        """测试连接"""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key_var.get(), base_url=self.base_url_var.get())
            
            # 测试 LLM
            response = client.chat.completions.create(
                model=self.llm_model_var.get(),
                messages=[{"role": "user", "content": "你好"}],
                max_tokens=10
            )
            
            messagebox.showinfo("成功", "✅ MiMo API 连接测试成功！")
            
        except Exception as e:
            messagebox.showerror("错误", f"连接测试失败:\n{str(e)}")
    
    def run(self):
        """运行"""
        self.root.mainloop()


if __name__ == "__main__":
    app = LecTransApp()
    app.run()

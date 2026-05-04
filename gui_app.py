"""
LecTrans - Windows GUI 应用
使用 tkinter 创建原生界面
"""

import os
import sys
import json
import threading
import time
from datetime import datetime
from pathlib import Path
from tkinter import *
from tkinter import ttk, messagebox, filedialog, simpledialog
from typing import Optional, List
import queue

# 添加项目路径
if getattr(sys, 'frozen', False):
    # PyInstaller 打包后的路径
    BASE_DIR = Path(sys._MEIPASS)
else:
    BASE_DIR = Path(__file__).parent

sys.path.insert(0, str(BASE_DIR))

# 配置文件路径
CONFIG_DIR = Path.home() / ".lectrans"
CONFIG_FILE = CONFIG_DIR / "config.json"
SESSIONS_DIR = CONFIG_DIR / "sessions"


class AppConfig:
    """应用配置"""
    
    def __init__(self):
        self.asr_provider = "groq"
        self.asr_api_key = ""
        self.asr_model = "whisper-large-v3-turbo"
        
        self.llm_provider = "xiaomi"
        self.llm_api_key = ""
        self.llm_base_url = "https://token-plan-cn.xiaomimimo.com/v1"
        self.llm_model = "mimo-v2.5-pro"
        
        self.theme = "dark"
        self.font_size = 14
        
        self.load()
    
    def load(self):
        """加载配置"""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self.asr_provider = data.get('asr_provider', self.asr_provider)
                self.asr_api_key = data.get('asr_api_key', self.asr_api_key)
                self.asr_model = data.get('asr_model', self.asr_model)
                self.llm_provider = data.get('llm_provider', self.llm_provider)
                self.llm_api_key = data.get('llm_api_key', self.llm_api_key)
                self.llm_base_url = data.get('llm_base_url', self.llm_base_url)
                self.llm_model = data.get('llm_model', self.llm_model)
                self.theme = data.get('theme', self.theme)
                self.font_size = data.get('font_size', self.font_size)
            except Exception:
                pass
    
    def save(self):
        """保存配置"""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        
        data = {
            'asr_provider': self.asr_provider,
            'asr_api_key': self.asr_api_key,
            'asr_model': self.asr_model,
            'llm_provider': self.llm_provider,
            'llm_api_key': self.llm_api_key,
            'llm_base_url': self.llm_base_url,
            'llm_model': self.llm_model,
            'theme': self.theme,
            'font_size': self.font_size,
        }
        
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    @property
    def is_configured(self) -> bool:
        return bool(self.asr_api_key and self.llm_api_key)


class TranscriptEntry:
    """转录条目"""
    def __init__(self, korean: str, chinese: str):
        self.timestamp = datetime.now()
        self.korean = korean
        self.chinese = chinese


class LecTransApp:
    """LecTrans 主应用"""
    
    def __init__(self):
        self.root = Tk()
        self.root.title("LecTrans - 实时课堂翻译")
        self.root.geometry("1000x700")
        
        # 配置
        self.config = AppConfig()
        
        # 状态
        self.is_recording = False
        self.is_connected = False
        self.transcripts: List[TranscriptEntry] = []
        self.summary = ""
        
        # 消息队列
        self.msg_queue = queue.Queue()
        
        # 核心组件（延迟初始化）
        self.recognizer = None
        self.translator = None
        self.summarizer = None
        self.audio_capture = None
        
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
        
        # 暗黑主题颜色
        self.colors = {
            'bg': '#1E1E1E',
            'fg': '#FFFFFF',
            'accent': '#4F8CFF',
            'success': '#00D97E',
            'warning': '#FFB020',
            'error': '#FF4B4B',
            'surface': '#2D2D2D',
            'text': '#CCCCCC',
        }
        
        # 配置样式
        style.theme_use('clam')
        
        style.configure('TFrame', background=self.colors['bg'])
        style.configure('TLabel', background=self.colors['bg'], foreground=self.colors['fg'])
        style.configure('TButton', padding=6)
        
        style.configure('Accent.TButton', background=self.colors['accent'], foreground='white')
        style.configure('Success.TButton', background=self.colors['success'], foreground='white')
        style.configure('Warning.TButton', background=self.colors['warning'], foreground='white')
        style.configure('Error.TButton', background=self.colors['error'], foreground='white')
        
        # 配置 root
        self.root.configure(bg=self.colors['bg'])
    
    def create_widgets(self):
        """创建界面组件"""
        # 主容器
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)
        
        # 顶部标题栏
        self.create_header(main_frame)
        
        # 翻译区域
        self.create_transcript_area(main_frame)
        
        # 底部控制栏
        self.create_control_bar(main_frame)
        
        # 状态栏
        self.create_status_bar(main_frame)
    
    def create_header(self, parent):
        """创建顶部标题栏"""
        header = ttk.Frame(parent)
        header.pack(fill=X, pady=(0, 10))
        
        # 标题
        title = ttk.Label(header, text="🎓 LecTrans", font=('Segoe UI', 20, 'bold'))
        title.pack(side=LEFT)
        
        subtitle = ttk.Label(header, text="实时课堂翻译工具", font=('Segoe UI', 10))
        subtitle.pack(side=LEFT, padx=(10, 0))
        
        # 按钮
        btn_frame = ttk.Frame(header)
        btn_frame.pack(side=RIGHT)
        
        ttk.Button(btn_frame, text="⚙️ 设置", command=self.show_settings).pack(side=LEFT, padx=2)
        ttk.Button(btn_frame, text="💾 保存", command=self.save_session).pack(side=LEFT, padx=2)
        ttk.Button(btn_frame, text="📥 导出", command=self.export_markdown).pack(side=LEFT, padx=2)
    
    def create_transcript_area(self, parent):
        """创建翻译区域"""
        # 容器
        transcript_frame = ttk.Frame(parent)
        transcript_frame.pack(fill=BOTH, expand=True)
        
        # 韩语区域
        ko_frame = ttk.LabelFrame(transcript_frame, text="🇰🇷 한국어 (Korean)")
        ko_frame.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 5))
        
        self.ko_text = Text(
            ko_frame,
            wrap=WORD,
            font=('Segoe UI', self.config.font_size),
            bg=self.colors['surface'],
            fg=self.colors['fg'],
            insertbackground=self.colors['fg'],
            selectbackground=self.colors['accent'],
            state=DISABLED
        )
        self.ko_text.pack(fill=BOTH, expand=True, padx=5, pady=5)
        
        # 中文区域
        zh_frame = ttk.LabelFrame(transcript_frame, text="🇨🇳 中文 (Chinese)")
        zh_frame.pack(side=RIGHT, fill=BOTH, expand=True, padx=(5, 0))
        
        self.zh_text = Text(
            zh_frame,
            wrap=WORD,
            font=('Segoe UI', self.config.font_size),
            bg=self.colors['surface'],
            fg=self.colors['fg'],
            insertbackground=self.colors['fg'],
            selectbackground=self.colors['accent'],
            state=DISABLED
        )
        self.zh_text.pack(fill=BOTH, expand=True, padx=5, pady=5)
    
    def create_control_bar(self, parent):
        """创建控制栏"""
        control_frame = ttk.Frame(parent)
        control_frame.pack(fill=X, pady=10)
        
        # 开始/停止按钮
        self.start_btn = ttk.Button(
            control_frame,
            text="▶️ 开始录音",
            command=self.toggle_recording,
            style='Accent.TButton'
        )
        self.start_btn.pack(side=LEFT, padx=5)
        
        # 状态指示
        self.status_label = ttk.Label(
            control_frame,
            text="● 未连接",
            foreground=self.colors['error']
        )
        self.status_label.pack(side=LEFT, padx=20)
        
        # 总结按钮
        ttk.Button(
            control_frame,
            text="📝 生成总结",
            command=self.generate_summary,
            style='Warning.TButton'
        ).pack(side=LEFT, padx=5)
        
        # 清空按钮
        ttk.Button(
            control_frame,
            text="🗑️ 清空",
            command=self.clear_transcript
        ).pack(side=RIGHT, padx=5)
    
    def create_status_bar(self, parent):
        """创建状态栏"""
        status_frame = ttk.Frame(parent)
        status_frame.pack(fill=X)
        
        self.entry_count_label = ttk.Label(status_frame, text="条目: 0")
        self.entry_count_label.pack(side=LEFT)
        
        self.time_label = ttk.Label(status_frame, text="")
        self.time_label.pack(side=RIGHT)
        
        # 更新时间
        self.update_time()
    
    def update_time(self):
        """更新时间"""
        now = datetime.now().strftime("%H:%M:%S")
        self.time_label.config(text=now)
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
                elif msg_type == "summary":
                    self.show_summary(data)
        except queue.Empty:
            pass
        
        self.root.after(100, self.process_queue)
    
    def init_components(self):
        """初始化核心组件"""
        try:
            from openai import OpenAI
            
            # 翻译器
            self.translator = OpenAI(
                api_key=self.config.llm_api_key,
                base_url=self.config.llm_base_url
            )
            
            # 总结器（同一个客户端）
            self.summarizer = self.translator
            
            # 语音识别器（如果配置了 Groq）
            if self.config.asr_api_key:
                try:
                    from groq import Groq
                    self.recognizer = Groq(api_key=self.config.asr_api_key)
                except Exception:
                    pass
            
            self.is_connected = True
            self.msg_queue.put(("status", {"connected": True}))
            return True
            
        except Exception as e:
            self.msg_queue.put(("error", f"初始化失败: {str(e)}"))
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
        self.start_btn.config(text="⏹️ 停止录音", style='Error.TButton')
        
        # 启动录音线程
        self.recording_thread = threading.Thread(target=self.recording_loop, daemon=True)
        self.recording_thread.start()
    
    def stop_recording(self):
        """停止录音"""
        self.is_recording = False
        self.start_btn.config(text="▶️ 开始录音", style='Accent.TButton')
    
    def recording_loop(self):
        """录音循环（模拟 - 实际需要 PyAudio）"""
        # 注意：实际应用中需要使用 PyAudio 采集音频
        # 这里为了打包成功，使用模拟数据
        
        while self.is_recording:
            try:
                # 模拟转录（实际应用替换为真实音频处理）
                time.sleep(3)
                
                if not self.is_recording:
                    break
                
                # 模拟韩语文本
                sample_texts = [
                    "안녕하세요, 오늘 컴퓨터 과학 수업을 시작하겠습니다.",
                    "알고리즘은 문제를 해결하는 단계적 과정입니다.",
                    "자료구조는 데이터를 조직화하는 방법입니다.",
                    "시간 복잡도는 알고리즘의 효율성을 측정합니다.",
                ]
                
                import random
                korean = random.choice(sample_texts)
                
                # 翻译
                chinese = self.translate_text(korean)
                
                # 添加到界面
                self.msg_queue.put(("transcript", {
                    "korean": korean,
                    "chinese": chinese
                }))
                
            except Exception as e:
                if self.is_recording:
                    print(f"Recording error: {e}")
    
    def translate_text(self, korean: str) -> str:
        """翻译文本"""
        if not self.translator:
            return "[翻译器未初始化]"
        
        try:
            response = self.translator.chat.completions.create(
                model=self.config.llm_model,
                messages=[
                    {"role": "system", "content": "你是韩中翻译官，将韩语翻译成中文。只输出中文翻译。"},
                    {"role": "user", "content": korean}
                ],
                temperature=0.3,
                max_tokens=500
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"[翻译失败: {str(e)}]"
    
    def add_transcript(self, korean: str, chinese: str):
        """添加转录条目"""
        entry = TranscriptEntry(korean, chinese)
        self.transcripts.append(entry)
        
        # 更新韩语文本框
        self.ko_text.config(state=NORMAL)
        self.ko_text.insert(END, f"[{entry.timestamp.strftime('%H:%M:%S')}] {korean}\n\n")
        self.ko_text.see(END)
        self.ko_text.config(state=DISABLED)
        
        # 更新中文文本框
        self.zh_text.config(state=NORMAL)
        self.zh_text.insert(END, f"[{entry.timestamp.strftime('%H:%M:%S')}] {chinese}\n\n")
        self.zh_text.see(END)
        self.zh_text.config(state=DISABLED)
        
        # 更新计数
        self.entry_count_label.config(text=f"条目: {len(self.transcripts)}")
    
    def clear_transcript(self):
        """清空转录"""
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
        
        # 显示加载对话框
        progress = Toplevel(self.root)
        progress.title("生成中")
        progress.geometry("300x100")
        progress.transient(self.root)
        progress.grab_set()
        
        Label(progress, text="正在生成总结，请稍候...").pack(pady=20)
        pb = ttk.Progressbar(progress, mode='indeterminate')
        pb.pack(padx=20, fill=X)
        pb.start()
        
        # 在线程中生成总结
        def do_summarize():
            try:
                # 构建转录文本
                transcript = "\n".join([
                    f"[{e.timestamp.strftime('%H:%M:%S')}] {e.korean}"
                    for e in self.transcripts
                ])
                
                response = self.summarizer.chat.completions.create(
                    model=self.config.llm_model,
                    messages=[
                        {"role": "system", "content": "你是学术笔记整理专家。将课堂转录整理成结构化中文笔记。使用 Markdown 格式。"},
                        {"role": "user", "content": f"课堂转录内容：\n\n{transcript}"}
                    ],
                    temperature=0.3,
                    max_tokens=2000
                )
                
                self.summary = response.choices[0].message.content.strip()
                self.root.after(0, lambda: self.show_summary(self.summary))
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", f"生成总结失败: {str(e)}"))
            finally:
                self.root.after(0, progress.destroy)
        
        threading.Thread(target=do_summarize, daemon=True).start()
    
    def show_summary(self, summary: str):
        """显示总结"""
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
            messagebox.showinfo("成功", f"总结已保存到:\n{filepath}")
    
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
                "# LecTrans 课堂笔记\n",
                f"**日期**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n",
                f"**条目**: {len(self.transcripts)} 条\n\n",
                "---\n\n",
                "## 📝 转录内容\n\n"
            ]
            
            for entry in self.transcripts:
                lines.append(f"### [{entry.timestamp.strftime('%H:%M:%S')}]\n")
                lines.append(f"**韩语**: {entry.korean}\n\n")
                lines.append(f"**中文**: {entry.chinese}\n\n")
                lines.append("---\n\n")
            
            if self.summary:
                lines.append("## 📚 总结\n\n")
                lines.append(self.summary)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            messagebox.showinfo("成功", f"会话已保存到:\n{filepath}")
    
    def export_markdown(self):
        """导出 Markdown"""
        self.save_session()
    
    def update_status(self, connected: bool):
        """更新连接状态"""
        self.is_connected = connected
        if connected:
            self.status_label.config(text="● 已连接", foreground=self.colors['success'])
        else:
            self.status_label.config(text="● 未连接", foreground=self.colors['error'])
    
    def show_settings(self):
        """显示设置窗口"""
        win = Toplevel(self.root)
        win.title("⚙️ 设置")
        win.geometry("500x600")
        win.transient(self.root)
        win.grab_set()
        
        # 创建 Notebook（标签页）
        notebook = ttk.Notebook(win)
        notebook.pack(fill=BOTH, expand=True, padx=10, pady=10)
        
        # API 配置标签页
        api_frame = ttk.Frame(notebook)
        notebook.add(api_frame, text="🔑 API 配置")
        self.create_api_settings(api_frame)
        
        # 显示设置标签页
        display_frame = ttk.Frame(notebook)
        notebook.add(display_frame, text="🎨 显示设置")
        self.create_display_settings(display_frame)
        
        # 关于标签页
        about_frame = ttk.Frame(notebook)
        notebook.add(about_frame, text="ℹ️ 关于")
        self.create_about_page(about_frame)
        
        # 按钮
        btn_frame = ttk.Frame(win)
        btn_frame.pack(fill=X, padx=10, pady=10)
        
        ttk.Button(btn_frame, text="💾 保存", command=lambda: self.save_settings(win)).pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=win.destroy).pack(side=RIGHT, padx=5)
    
    def create_api_settings(self, parent):
        """创建 API 设置界面"""
        # ASR 配置
        asr_frame = ttk.LabelFrame(parent, text="语音识别 (ASR)")
        asr_frame.pack(fill=X, padx=10, pady=5)
        
        # ASR 提供商
        ttk.Label(asr_frame, text="提供商:").grid(row=0, column=0, padx=5, pady=5, sticky=W)
        self.asr_provider_var = StringVar(value=self.config.asr_provider)
        asr_combo = ttk.Combobox(asr_frame, textvariable=self.asr_provider_var, values=["groq", "openai"], state="readonly")
        asr_combo.grid(row=0, column=1, padx=5, pady=5, sticky=EW)
        
        # ASR API Key
        ttk.Label(asr_frame, text="API Key:").grid(row=1, column=0, padx=5, pady=5, sticky=W)
        self.asr_key_var = StringVar(value=self.config.asr_api_key)
        asr_key_entry = ttk.Entry(asr_frame, textvariable=self.asr_key_var, show="*")
        asr_key_entry.grid(row=1, column=1, padx=5, pady=5, sticky=EW)
        
        # ASR Model
        ttk.Label(asr_frame, text="模型:").grid(row=2, column=0, padx=5, pady=5, sticky=W)
        self.asr_model_var = StringVar(value=self.config.asr_model)
        ttk.Entry(asr_frame, textvariable=self.asr_model_var).grid(row=2, column=1, padx=5, pady=5, sticky=EW)
        
        asr_frame.columnconfigure(1, weight=1)
        
        # LLM 配置
        llm_frame = ttk.LabelFrame(parent, text="翻译/总结 (LLM)")
        llm_frame.pack(fill=X, padx=10, pady=5)
        
        # LLM 提供商
        ttk.Label(llm_frame, text="提供商:").grid(row=0, column=0, padx=5, pady=5, sticky=W)
        self.llm_provider_var = StringVar(value=self.config.llm_provider)
        llm_combo = ttk.Combobox(llm_frame, textvariable=self.llm_provider_var, values=["xiaomi", "deepseek", "openai"], state="readonly")
        llm_combo.grid(row=0, column=1, padx=5, pady=5, sticky=EW)
        llm_combo.bind("<<ComboboxSelected>>", self.on_llm_provider_change)
        
        # LLM API Key
        ttk.Label(llm_frame, text="API Key:").grid(row=1, column=0, padx=5, pady=5, sticky=W)
        self.llm_key_var = StringVar(value=self.config.llm_api_key)
        ttk.Entry(llm_frame, textvariable=self.llm_key_var, show="*").grid(row=1, column=1, padx=5, pady=5, sticky=EW)
        
        # LLM Base URL
        ttk.Label(llm_frame, text="Base URL:").grid(row=2, column=0, padx=5, pady=5, sticky=W)
        self.llm_url_var = StringVar(value=self.config.llm_base_url)
        ttk.Entry(llm_frame, textvariable=self.llm_url_var).grid(row=2, column=1, padx=5, pady=5, sticky=EW)
        
        # LLM Model
        ttk.Label(llm_frame, text="模型:").grid(row=3, column=0, padx=5, pady=5, sticky=W)
        self.llm_model_var = StringVar(value=self.config.llm_model)
        ttk.Entry(llm_frame, textvariable=self.llm_model_var).grid(row=3, column=1, padx=5, pady=5, sticky=EW)
        
        llm_frame.columnconfigure(1, weight=1)
        
        # 测试按钮
        ttk.Button(parent, text="🔍 测试连接", command=self.test_connection).pack(pady=10)
    
    def create_display_settings(self, parent):
        """创建显示设置界面"""
        # 字体大小
        frame = ttk.LabelFrame(parent, text="字体设置")
        frame.pack(fill=X, padx=10, pady=5)
        
        ttk.Label(frame, text="字体大小:").grid(row=0, column=0, padx=5, pady=5, sticky=W)
        self.font_size_var = IntVar(value=self.config.font_size)
        ttk.Spinbox(frame, from_=10, to=24, textvariable=self.font_size_var, width=10).grid(row=0, column=1, padx=5, pady=5, sticky=W)
    
    def create_about_page(self, parent):
        """创建关于页面"""
        text = """
🎓 LecTrans - 实时课堂翻译工具

版本: 1.0.0

专为在韩国留学的中国学生设计
实时韩中翻译 + 智能课堂总结

功能特点:
• 实时语音转录 (Groq Whisper)
• 韩中实时翻译 (MiMo 2.5 Pro)
• 一键智能总结
• 笔记导出 (Markdown)

技术支持:
• GitHub: github.com/lectrans
• Email: support@lectrans.app

© 2024 LecTrans Team
        """
        
        label = ttk.Label(parent, text=text, justify=LEFT, font=('Segoe UI', 10))
        label.pack(padx=20, pady=20)
    
    def on_llm_provider_change(self, event=None):
        """LLM 提供商变更"""
        provider = self.llm_provider_var.get()
        
        defaults = {
            "xiaomi": ("https://token-plan-cn.xiaomimimo.com/v1", "mimo-v2.5-pro"),
            "deepseek": ("https://api.deepseek.com/v1", "deepseek-chat"),
            "openai": ("https://api.openai.com/v1", "gpt-4o"),
        }
        
        if provider in defaults:
            url, model = defaults[provider]
            self.llm_url_var.set(url)
            self.llm_model_var.set(model)
    
    def save_settings(self, win):
        """保存设置"""
        self.config.asr_provider = self.asr_provider_var.get()
        self.config.asr_api_key = self.asr_key_var.get()
        self.config.asr_model = self.asr_model_var.get()
        self.config.llm_provider = self.llm_provider_var.get()
        self.config.llm_api_key = self.llm_key_var.get()
        self.config.llm_base_url = self.llm_url_var.get()
        self.config.llm_model = self.llm_model_var.get()
        self.config.font_size = self.font_size_var.get()
        
        self.config.save()
        
        # 重新初始化组件
        self.is_connected = False
        self.init_components()
        
        messagebox.showinfo("成功", "设置已保存")
        win.destroy()
    
    def test_connection(self):
        """测试连接"""
        try:
            from openai import OpenAI
            
            client = OpenAI(
                api_key=self.llm_key_var.get(),
                base_url=self.llm_url_var.get()
            )
            
            response = client.chat.completions.create(
                model=self.llm_model_var.get(),
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10
            )
            
            messagebox.showinfo("成功", "API 连接测试成功！")
            
        except Exception as e:
            messagebox.showerror("错误", f"连接测试失败:\n{str(e)}")
    
    def run(self):
        """运行应用"""
        self.root.mainloop()


def main():
    """主函数"""
    app = LecTransApp()
    app.run()


if __name__ == "__main__":
    main()

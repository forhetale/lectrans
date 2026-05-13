"""
LecTrans 主窗口
tkinter 桌面应用，实时韩→中课堂翻译
Apple-inspired Dark Mode UI
"""

import sys
import threading
import queue
from datetime import datetime
from pathlib import Path
from tkinter import *
from tkinter import ttk, messagebox, filedialog
from typing import Optional, List

# 确保项目根目录在 sys.path 中
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import AppConfig, RECORDINGS_DIR
from ui.design import DesignSystem
from ui.settings_dialog import SettingsDialog
from ui.history_dialog import HistoryDialog
from core.audio_recorder import AudioRecorder, AudioManager
from core.translator import MiMoClient
from core.session_manager import SessionManager, TranscriptEntry


class LecTransApp:
    """LecTrans 主应用"""

    def __init__(self):
        self.root = Tk()
        self.root.title('LecTrans')
        self.root.geometry('1060x720')
        self.root.minsize(760, 480)

        self.ds = DesignSystem()
        self.config = AppConfig()
        self.session_mgr = SessionManager()

        # 状态
        self.is_recording = False
        self.is_connected = False
        self.transcripts: List[TranscriptEntry] = []
        self.summary = ''
        self.recording_start_time: Optional[datetime] = None
        self.session_id: Optional[str] = None

        # 组件
        self.mimo_client: Optional[MiMoClient] = None
        self.azure_recognizer = None
        self.audio_recorder: Optional[AudioRecorder] = None
        self.msg_queue = queue.Queue()

        # 应用主题
        self.root.configure(bg=self.ds.COLORS['bg_primary'])
        self.ds.apply_theme(self.root)

        # 创建界面
        self._create_layout()

        # 检查配置
        if not self.config.is_configured:
            self.root.after(300, self._show_settings)

        # 处理消息队列
        self.root.after(100, self._process_queue)

    # ==============================================================
    # 布局
    # ==============================================================

    def _create_layout(self):
        """创建 Apple 风格布局"""
        c = self.ds.COLORS

        # ──── 顶部导航栏 ────
        navbar = Frame(self.root, bg=c['bg_secondary'], height=self.ds.NAVBAR_HEIGHT)
        navbar.pack(fill=X, side=TOP)
        navbar.pack_propagate(False)

        # 左侧品牌
        left_nav = Frame(navbar, bg=c['bg_secondary'])
        left_nav.pack(side=LEFT, padx=20, fill=Y)

        # 品牌小圆点 + 名称
        brand_dot = Label(left_nav, text='●', font=('Segoe UI', 10),
                          fg=c['accent'], bg=c['bg_secondary'])
        brand_dot.pack(side=LEFT, pady=0)

        brand_label = Label(left_nav, text='LecTrans', font=self.ds.FONTS['title'],
                            fg=c['text_primary'], bg=c['bg_secondary'])
        brand_label.pack(side=LEFT, padx=(8, 0))

        subtitle = Label(left_nav, text='实时课堂翻译', font=self.ds.FONTS['small'],
                         fg=c['text_muted'], bg=c['bg_secondary'])
        subtitle.pack(side=LEFT, padx=(10, 0))

        # 右侧导航按钮
        right_nav = Frame(navbar, bg=c['bg_secondary'])
        right_nav.pack(side=RIGHT, padx=16, fill=Y)

        for text, cmd in [('导出', self._export_markdown),
                          ('历史', self._show_history),
                          ('设置', self._show_settings)]:
            self._make_nav_btn(right_nav, text, cmd)

        # 分隔线
        self.ds.make_separator(self.root).pack(fill=X)

        # ──── 控制栏 ────
        control_frame = Frame(self.root, bg=c['bg_primary'], height=self.ds.CONTROL_HEIGHT)
        control_frame.pack(fill=X, side=TOP)
        control_frame.pack_propagate(False)

        control_inner = Frame(control_frame, bg=c['bg_primary'])
        control_inner.pack(fill=BOTH, expand=True, padx=20, pady=10)

        # 录音药丸按钮
        self.record_btn = self.ds.make_pill_button(
            control_inner, text='● 开始录音', command=self._toggle_recording, color='success')
        self.record_btn.pack(side=LEFT, padx=(0, 16))

        # 录音计时
        self.recording_time_label = Label(
            control_inner, text='', font=self.ds.FONTS['mono'],
            fg=c['accent'], bg=c['bg_primary'], width=6)
        self.recording_time_label.pack(side=LEFT, padx=(0, 20))

        # 设备选择区
        device_frame = Frame(control_inner, bg=c['bg_primary'])
        device_frame.pack(side=LEFT, padx=(0, 16))

        Label(device_frame, text='音频设备', font=self.ds.FONTS['small'],
              fg=c['text_muted'], bg=c['bg_primary']).pack(side=LEFT, padx=(0, 8))

        self.device_var = StringVar(value='默认设备')
        devices = AudioManager.get_input_devices()
        self.device_list = devices
        device_names = [d['name'] for d in devices]

        self.device_combo = ttk.Combobox(
            device_frame, textvariable=self.device_var,
            values=device_names, state='readonly', width=22,
            font=self.ds.FONTS['small'])
        self.device_combo.pack(side=LEFT)
        self.device_combo.bind('<<ComboboxSelected>>', self._on_device_change)

        # 右侧操作按钮
        right_actions = Frame(control_inner, bg=c['bg_primary'])
        right_actions.pack(side=RIGHT)

        self.ds.make_button(right_actions, '清空', self._clear_transcript,
                            style='ghost').pack(side=RIGHT, padx=(8, 0))
        self.ds.make_button(right_actions, '生成总结', self._generate_summary,
                            style='secondary').pack(side=RIGHT)

        # ──── 内容区（双栏） ────
        content_frame = Frame(self.root, bg=c['bg_primary'])
        content_frame.pack(fill=BOTH, expand=True, side=TOP)
        content_frame.columnconfigure(0, weight=1)
        content_frame.columnconfigure(1, weight=1)
        content_frame.rowconfigure(0, weight=1)

        self.ko_card = self._create_text_card(content_frame, '한국어', '#FF6961')
        self.ko_card.grid(row=0, column=0, sticky='nsew', padx=(12, 6), pady=(4, 8))

        self.zh_card = self._create_text_card(content_frame, '中文', '#0A84FF')
        self.zh_card.grid(row=0, column=1, sticky='nsew', padx=(6, 12), pady=(4, 8))

        # ──── 状态栏 ────
        status_bar = Frame(self.root, bg=c['bg_secondary'], height=self.ds.STATUSBAR_HEIGHT)
        status_bar.pack(fill=X, side=BOTTOM)
        status_bar.pack_propagate(False)

        self.status_dot = Label(status_bar, text='●', fg=c['error'],
                                bg=c['bg_secondary'], font=('Segoe UI', 7))
        self.status_dot.pack(side=LEFT, padx=(16, 4))

        self.status_text = Label(status_bar, text='ASR: Azure  ·  翻译: MiMo',
                                 fg=c['text_muted'], bg=c['bg_secondary'],
                                 font=self.ds.FONTS['small'])
        self.status_text.pack(side=LEFT, padx=(0, 16))

        self.entry_count = Label(status_bar, text='0 条记录',
                                 fg=c['text_muted'], bg=c['bg_secondary'],
                                 font=self.ds.FONTS['small'])
        self.entry_count.pack(side=LEFT)

        self.time_label = Label(status_bar, text='', fg=c['text_muted'],
                                bg=c['bg_secondary'], font=self.ds.FONTS['mono'])
        self.time_label.pack(side=RIGHT, padx=16)

        self._update_time()

    # ==============================================================
    # UI 辅助
    # ==============================================================

    def _make_nav_btn(self, parent, text, command):
        """创建导航栏按钮"""
        c = self.ds.COLORS
        btn = Button(parent, text=text, font=self.ds.FONTS['caption'],
                     fg=c['text_secondary'], bg=c['bg_secondary'],
                     activeforeground=c['text_primary'],
                     activebackground=c['bg_tertiary'],
                     relief='flat', bd=0, padx=12, pady=6,
                     cursor='hand2', command=command)
        btn.pack(side=LEFT, padx=2, pady=10)
        btn.bind('<Enter>', lambda e: btn.configure(fg=c['text_primary'], bg=c['bg_tertiary']))
        btn.bind('<Leave>', lambda e: btn.configure(fg=c['text_secondary'], bg=c['bg_secondary']))
        return btn

    def _create_text_card(self, parent, title, dot_color):
        """创建内容文本卡片"""
        c = self.ds.COLORS
        card = self.ds.make_card(parent)

        # 标题区
        header = Frame(card, bg=c['bg_secondary'])
        header.pack(fill=X, padx=16, pady=(14, 6))

        # 彩色小圆点 + 标题
        Label(header, text='●', font=('Segoe UI', 8),
              fg=dot_color, bg=c['bg_secondary']).pack(side=LEFT, padx=(0, 8))
        Label(header, text=title, font=self.ds.FONTS['heading'],
              fg=c['text_primary'], bg=c['bg_secondary']).pack(side=LEFT)

        # 文本区
        text_frame = Frame(card, bg=c['bg_secondary'])
        text_frame.pack(fill=BOTH, expand=True, padx=12, pady=(0, 12))

        text_widget = Text(text_frame, wrap=WORD,
                           font=('Segoe UI', self.config.font_size),
                           bg=c['bg_secondary'], fg=c['text_primary'],
                           insertbackground=c['text_primary'],
                           selectbackground=c['accent'],
                           selectforeground='#FFFFFF',
                           relief='flat', bd=0,
                           padx=10, pady=8,
                           spacing1=2, spacing3=2,
                           state=DISABLED)
        text_widget.pack(side=LEFT, fill=BOTH, expand=True)

        scrollbar = ttk.Scrollbar(text_frame, orient=VERTICAL, command=text_widget.yview)
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

    # ==============================================================
    # 设备 / 配置
    # ==============================================================

    def _on_device_change(self, event):
        device_name = self.device_var.get()
        for d in self.device_list:
            if d['name'] == device_name:
                self.config.audio_device_index = d['index']
                self.config.save()
                break

    def _show_settings(self):
        SettingsDialog(self.root, self.config, on_save=self._on_settings_saved)

    def _on_settings_saved(self):
        self.is_connected = False
        self._init_components()

    def _show_history(self):
        HistoryDialog(self.root)

    # ==============================================================
    # 消息队列
    # ==============================================================

    def _process_queue(self):
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
        self.root.after(100, self._process_queue)

    # ==============================================================
    # 初始化组件
    # ==============================================================

    def _init_components(self) -> bool:
        """初始化 Azure 识别器和 MiMo 客户端"""
        if not self.config.azure_key:
            self.msg_queue.put(('error', '请在设置中配置 Azure Speech API Key'))
            return False
        if not self.config.api_key:
            self.msg_queue.put(('error', '请在设置中配置 MiMo API Key'))
            return False

        try:
            self.mimo_client = MiMoClient(self.config.api_key, self.config.base_url)

            from core.azure_recognizer import AzureSpeechRecognizer
            self.azure_recognizer = AzureSpeechRecognizer(
                subscription_key=self.config.azure_key,
                region=self.config.azure_region,
                language=self.config.azure_language,
            )
            self.azure_recognizer.on_recognized = self._on_azure_recognized
            self.azure_recognizer.on_error = self._on_azure_error

            self.is_connected = True
            self.msg_queue.put(('status', {'connected': True}))
            return True
        except Exception as e:
            self.msg_queue.put(('error', f'初始化失败: {str(e)}'))
            return False

    # ==============================================================
    # 录音控制
    # ==============================================================

    def _toggle_recording(self):
        if self.is_recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self):
        if not self.is_connected:
            if not self._init_components():
                return

        if self.azure_recognizer and self.azure_recognizer.start_continuous_recognition():
            self.is_recording = True
            self.recording_start_time = datetime.now()
            self.session_id = self.recording_start_time.strftime("%Y%m%d_%H%M%S")
            self.transcripts = []
            self.summary = ''

            # 启动音频录制器（用于保存录音）
            self.audio_recorder = AudioRecorder(
                sample_rate=self.config.sample_rate,
                device_index=self.config.audio_device_index,
            )
            self.audio_recorder.start()

            self.record_btn.configure(
                text='■ 停止录音',
                bg=self.ds.COLORS['error'],
                activebackground='#D32F2F')
            # 更新 hover 绑定
            self.record_btn.bind('<Enter>', lambda e: self.record_btn.configure(bg='#D32F2F'))
            self.record_btn.bind('<Leave>', lambda e: self.record_btn.configure(bg=self.ds.COLORS['error']))
            self._update_recording_time()
        else:
            messagebox.showerror('错误', '无法启动语音识别，请检查麦克风')

    def _stop_recording(self):
        self.is_recording = False

        if self.azure_recognizer:
            self.azure_recognizer.stop_continuous_recognition()

        # 停止录音并获取音频数据
        audio_data = b''
        if self.audio_recorder:
            audio_data = self.audio_recorder.stop()
            self.audio_recorder = None

        end_time = datetime.now()

        self.record_btn.configure(
            text='● 开始录音',
            bg=self.ds.COLORS['success'],
            activebackground='#28B84C')
        # 恢复 hover 绑定
        self.record_btn.bind('<Enter>', lambda e: self.record_btn.configure(bg='#28B84C'))
        self.record_btn.bind('<Leave>', lambda e: self.record_btn.configure(bg=self.ds.COLORS['success']))
        self.recording_time_label.config(text='')

        # 自动保存会话
        if self.session_id:
            recording_path = ""

            # 默认直接保存录音为 mp3
            if audio_data and len(audio_data) > 0:
                RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
                recording_path = str(RECORDINGS_DIR / f"{self.session_id}.mp3")
                AudioRecorder.save_mp3(recording_path, audio_data, self.config.sample_rate)

            # 只有当有内容或有录音时才保存会话
            if self.transcripts or recording_path:
                self.session_mgr.save_session(
                    session_id=self.session_id,
                    transcripts=self.transcripts,
                    summary=self.summary,
                    recording_path=recording_path,
                    start_time=self.recording_start_time,
                    end_time=end_time,
                )
                messagebox.showinfo('自动保存', '录音与会话已自动保存到历史记录')

        self.recording_start_time = None

    # ==============================================================
    # Azure 回调
    # ==============================================================

    def _on_azure_recognized(self, result):
        """Azure 识别结果回调（运行在后台线程）"""
        korean = result.text
        if not korean or len(korean.strip()) < 2:
            return
        chinese = self.mimo_client.translate(korean, self.config.llm_model)
        self.msg_queue.put(('transcript', {'korean': korean, 'chinese': chinese}))

    def _on_azure_error(self, error):
        self.msg_queue.put(('error', f'Azure错误: {error}'))

    # ==============================================================
    # 转录显示
    # ==============================================================

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

        self.entry_count.config(text=f'{len(self.transcripts)} 条记录')

    def _clear_transcript(self):
        if messagebox.askyesno('确认', '确定清空所有记录？'):
            self.transcripts.clear()
            for w in [self.ko_text, self.zh_text]:
                w.config(state=NORMAL)
                w.delete(1.0, END)
                w.config(state=DISABLED)
            self.entry_count.config(text='0 条记录')

    # ==============================================================
    # 总结
    # ==============================================================

    def _generate_summary(self):
        if not self.transcripts:
            messagebox.showwarning('提示', '暂无转录内容')
            return
        if not self.is_connected:
            if not self._init_components():
                return

        c = self.ds.COLORS

        progress = Toplevel(self.root)
        progress.title('生成中')
        progress.geometry('320x120')
        progress.configure(bg=c['bg_secondary'])
        progress.transient(self.root)
        progress.grab_set()

        Label(progress, text='正在生成总结…', font=self.ds.FONTS['body'],
              fg=c['text_primary'], bg=c['bg_secondary']).pack(pady=(28, 16))
        pb = ttk.Progressbar(progress, mode='indeterminate', length=240)
        pb.pack()
        pb.start(12)

        def do_summarize():
            try:
                transcript = '\n'.join([
                    f'[{e.timestamp.strftime("%H:%M:%S")}] {e.korean}'
                    for e in self.transcripts
                ])
                self.summary = self.mimo_client.summarize(transcript, self.config.llm_model)
                self.root.after(0, lambda: self._show_summary(self.summary))
            except Exception:
                self.root.after(0, lambda: messagebox.showerror('错误', '生成失败'))
            finally:
                self.root.after(0, progress.destroy)

        threading.Thread(target=do_summarize, daemon=True).start()

    def _show_summary(self, summary):
        c = self.ds.COLORS

        win = Toplevel(self.root)
        win.title('课堂总结')
        win.geometry('580x480')
        win.configure(bg=c['bg_primary'])

        # 标题
        header = Frame(win, bg=c['bg_primary'])
        header.pack(fill=X, padx=24, pady=(24, 16))
        self.ds.make_label(header, '课堂总结', style='title').pack(side=LEFT)

        # 内容
        text_card = self.ds.make_card(win)
        text_card.pack(fill=BOTH, expand=True, padx=24, pady=(0, 16))

        text = Text(text_card, wrap=WORD, font=('Segoe UI', 12),
                    bg=c['bg_secondary'], fg=c['text_primary'],
                    relief='flat', bd=0, padx=16, pady=16,
                    spacing1=2, spacing3=2)
        text.pack(fill=BOTH, expand=True, padx=1, pady=1)
        text.insert(1.0, summary)

        # 按钮组
        btn_frame = Frame(win, bg=c['bg_primary'])
        btn_frame.pack(fill=X, padx=24, pady=(0, 24))

        self.ds.make_button(btn_frame, '关闭', win.destroy,
                            style='ghost').pack(side=RIGHT, padx=(8, 0))
        self.ds.make_button(btn_frame, '保存', lambda: self._save_summary(summary),
                            style='primary').pack(side=RIGHT, padx=(8, 0))
        self.ds.make_button(btn_frame, '复制', lambda: self._copy(summary),
                            style='secondary').pack(side=RIGHT)

    def _copy(self, text):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        messagebox.showinfo('提示', '已复制')

    def _save_summary(self, summary):
        fp = filedialog.asksaveasfilename(defaultextension='.md',
                                           filetypes=[('Markdown', '*.md')])
        if fp:
            with open(fp, 'w', encoding='utf-8') as f:
                f.write(summary)
            messagebox.showinfo('成功', '已保存')

    # ==============================================================
    # 导出
    # ==============================================================

    def _export_markdown(self):
        if not self.transcripts:
            messagebox.showwarning('提示', '暂无内容')
            return

        fp = filedialog.asksaveasfilename(
            defaultextension='.md',
            filetypes=[('Markdown', '*.md')],
            initialfile=f'session_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md',
        )
        if fp:
            lines = [
                f'# LecTrans 课堂笔记\n\n',
                f'**日期**: {datetime.now().strftime("%Y-%m-%d %H:%M")}\n\n',
                '---\n\n',
            ]
            for e in self.transcripts:
                lines.append(
                    f'### [{e.timestamp.strftime("%H:%M:%S")}]\n'
                    f'**韩语**: {e.korean}\n\n'
                    f'**中文**: {e.chinese}\n\n---\n\n'
                )
            if self.summary:
                lines.append(f'\n## 总结\n\n{self.summary}')
            with open(fp, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            messagebox.showinfo('成功', '已保存')

    # ==============================================================
    # 状态
    # ==============================================================

    def _update_status(self, connected):
        self.is_connected = connected
        c = self.ds.COLORS
        if connected:
            self.status_dot.config(fg=c['success'])
            self.status_text.config(text='ASR: Azure  ·  翻译: MiMo')
        else:
            self.status_dot.config(fg=c['error'])
            self.status_text.config(text='ASR: Azure  ·  翻译: 未连接')

    # ==============================================================
    # 运行
    # ==============================================================

    def run(self):
        self.root.mainloop()

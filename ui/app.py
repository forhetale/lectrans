"""
LecTrans 主窗口

tkinter 桌面应用，实时韩→中课堂翻译（Apple-inspired Dark Mode UI）。

线程模型：
- AudioRecorder 单路采集，向识别器队列分发音频块
- 识别器在后台线程产出韩语文本，仅入队翻译队列（不阻塞识别循环）
- 翻译 worker 线程串行调用 MiMo API，携带滚动上下文，结果入 UI 消息队列
- 主线程通过 after() 消费消息队列更新界面；会话保存由 finalizer 线程收尾
"""

import queue
import sys
import threading
from datetime import datetime
from pathlib import Path
from tkinter import (
    BOTH,
    BOTTOM,
    DISABLED,
    END,
    LEFT,
    NORMAL,
    RIGHT,
    TOP,
    VERTICAL,
    WORD,
    X,
    Y,
    Button,
    Frame,
    Label,
    StringVar,
    Text,
    Tk,
    Toplevel,
)
from tkinter import ttk, messagebox, filedialog
from typing import List, Optional

# 确保项目根目录在 sys.path 中
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import APP_VERSION, RECORDINGS_DIR, AppConfig
from core.audio_recorder import AudioManager, AudioRecorder
from core.logger import get_logger
from core.session_manager import SessionManager, TranscriptEntry
from core.translator import MiMoClient
from ui.design import DesignSystem
from ui.history_dialog import HistoryDialog
from ui.settings_dialog import SettingsDialog

logger = get_logger(__name__)


class LecTransApp:
    """LecTrans 主应用"""

    def __init__(self):
        self.root = Tk()
        self.root.title(f'LecTrans v{APP_VERSION}')
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
        self.session_token = 0

        # 组件
        self.mimo_client: Optional[MiMoClient] = None
        self.recognizer = None
        self.audio_recorder: Optional[AudioRecorder] = None
        self.msg_queue: queue.Queue = queue.Queue()
        self.translation_queue: queue.Queue = queue.Queue(maxsize=64)
        self.translation_thread: Optional[threading.Thread] = None
        self._finalizing = False

        # 应用主题
        self.root.configure(bg=self.ds.COLORS['bg_primary'])
        self.ds.apply_theme(self.root)

        # 创建界面
        self._create_layout()

        # 已配置则预先初始化客户端（不联网，仅构建与状态显示）
        if self.config.is_configured:
            self._init_components()

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

        left_nav = Frame(navbar, bg=c['bg_secondary'])
        left_nav.pack(side=LEFT, padx=20, fill=Y)

        Label(left_nav, text='●', font=('Segoe UI', 10),
              fg=c['accent'], bg=c['bg_secondary']).pack(side=LEFT, pady=0)
        Label(left_nav, text='LecTrans', font=self.ds.FONTS['title'],
              fg=c['text_primary'], bg=c['bg_secondary']).pack(side=LEFT, padx=(8, 0))
        Label(left_nav, text='实时课堂翻译', font=self.ds.FONTS['small'],
              fg=c['text_muted'], bg=c['bg_secondary']).pack(side=LEFT, padx=(10, 0))

        right_nav = Frame(navbar, bg=c['bg_secondary'])
        right_nav.pack(side=RIGHT, padx=16, fill=Y)

        for text, cmd in [('导出', self._export_markdown),
                          ('历史', self._show_history),
                          ('设置', self._show_settings)]:
            self._make_nav_btn(right_nav, text, cmd)

        self.ds.make_separator(self.root).pack(fill=X)

        # ──── 控制栏 ────
        control_frame = Frame(self.root, bg=c['bg_primary'], height=self.ds.CONTROL_HEIGHT)
        control_frame.pack(fill=X, side=TOP)
        control_frame.pack_propagate(False)

        control_inner = Frame(control_frame, bg=c['bg_primary'])
        control_inner.pack(fill=BOTH, expand=True, padx=20, pady=10)

        self.record_btn = self.ds.make_pill_button(
            control_inner, text='● 开始录音', command=self._toggle_recording, color='success')
        self.record_btn.pack(side=LEFT, padx=(0, 16))

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
        self.device_list = AudioManager.get_input_devices()
        self.device_combo = ttk.Combobox(
            device_frame, textvariable=self.device_var,
            values=[d['name'] for d in self.device_list],
            state='readonly', width=22, font=self.ds.FONTS['small'])
        self.device_combo.pack(side=LEFT)
        self.device_combo.bind('<<ComboboxSelected>>', self._on_device_change)

        # 右侧操作按钮
        right_actions = Frame(control_inner, bg=c['bg_primary'])
        right_actions.pack(side=RIGHT)

        self.ds.make_button(right_actions, '清空', self._clear_transcript,
                            style='ghost').pack(side=RIGHT, padx=(8, 0))
        self.ds.make_button(right_actions, '生成总结', self._generate_summary,
                            style='secondary').pack(side=RIGHT)

        # ──── 状态栏（先于内容区打包，避免 expand 占满空间） ────
        status_bar = Frame(self.root, bg=c['bg_secondary'], height=self.ds.STATUSBAR_HEIGHT)
        status_bar.pack(fill=X, side=BOTTOM)
        status_bar.pack_propagate(False)

        self.status_dot = Label(status_bar, text='●', fg=c['error'],
                                bg=c['bg_secondary'], font=('Segoe UI', 7))
        self.status_dot.pack(side=LEFT, padx=(16, 4))

        self.status_text = Label(status_bar, text=self._status_text(),
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

        self._update_time()

    # ==============================================================
    # UI 辅助
    # ==============================================================

    def _engine_label(self) -> str:
        return 'Azure' if self.config.asr_engine == 'azure' else '本地 Whisper'

    def _status_text(self) -> str:
        if self.is_connected:
            return f'ASR: {self._engine_label()}  ·  翻译: MiMo'
        return f'ASR: {self._engine_label()}  ·  翻译: 未连接'

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

        header = Frame(card, bg=c['bg_secondary'])
        header.pack(fill=X, padx=16, pady=(14, 6))

        Label(header, text='●', font=('Segoe UI', 8),
              fg=dot_color, bg=c['bg_secondary']).pack(side=LEFT, padx=(0, 8))
        Label(header, text=title, font=self.ds.FONTS['heading'],
              fg=c['text_primary'], bg=c['bg_secondary']).pack(side=LEFT)

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
                logger.info("切换音频设备: %s", d['name'])
                break

    def _show_settings(self):
        SettingsDialog(self.root, self.config, on_save=self._on_settings_saved)

    def _on_settings_saved(self):
        self.is_connected = False
        self._init_components()
        self.status_text.config(text=self._status_text())

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
                    self.is_connected = data['connected']
                    self.status_text.config(text=self._status_text())
                    self.status_dot.config(
                        fg=self.ds.COLORS['success'] if data['connected'] else self.ds.COLORS['error'])
                elif msg_type == 'error':
                    messagebox.showerror('错误', data)
                elif msg_type == 'finalize':
                    self._finalize_session(data)
                elif msg_type == 'log':
                    logger.info(data)
        except queue.Empty:
            pass
        self.root.after(100, self._process_queue)

    # ==============================================================
    # 初始化组件
    # ==============================================================

    def _init_components(self) -> bool:
        """初始化语音识别器和 MiMo 客户端"""
        if self.config.asr_engine == "azure" and not self.config.azure_key:
            self.msg_queue.put(('error', '请在设置中配置 Azure Speech API Key'))
            return False
        if not self.config.api_key:
            self.msg_queue.put(('error', '请在设置中配置 MiMo API Key'))
            return False

        try:
            self.mimo_client = MiMoClient(
                self.config.api_key, self.config.base_url, timeout=self.config.api_timeout)

            if self.config.asr_engine == "azure":
                from core.azure_recognizer import AzureSpeechRecognizer

                self.recognizer = AzureSpeechRecognizer(
                    subscription_key=self.config.azure_key,
                    region=self.config.azure_region,
                    language=self.config.azure_language,
                )
            else:
                from core.local_recognizer import LocalWhisperRecognizer

                self.recognizer = LocalWhisperRecognizer(
                    model_size=self.config.whisper_model,
                    device_index=self.config.audio_device_index,
                    sample_rate=self.config.sample_rate,
                    energy_threshold=self.config.energy_threshold,
                    silence_duration=self.config.silence_duration,
                    max_utterance_seconds=self.config.max_utterance_seconds,
                )

            self.recognizer.on_recognized = self._on_recognized
            self.recognizer.on_error = self._on_error

            self.is_connected = True
            self.msg_queue.put(('status', {'connected': True}))
            return True
        except Exception as e:
            logger.exception("初始化失败")
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
        if self._finalizing:
            messagebox.showinfo('提示', '正在保存上一段录音，请稍候')
            return

        if not self.is_connected and not self._init_components():
            return

        self.session_token += 1
        token = self.session_token
        self.recording_start_time = datetime.now()
        self.session_id = self.recording_start_time.strftime("%Y%m%d_%H%M%S")
        self.transcripts = []
        self.summary = ''

        # 1) 单路音频采集（同时落盘与分发）
        RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
        wav_path = RECORDINGS_DIR / f"{self.session_id}.wav"
        self.audio_recorder = AudioRecorder(
            sample_rate=self.config.sample_rate,
            device_index=self.config.audio_device_index,
            output_path=str(wav_path),
        )
        if not self.audio_recorder.start():
            self.audio_recorder = None
            messagebox.showerror('错误', '无法打开麦克风，请检查设备与权限')
            return

        # 2) 识别器消费共享音频队列
        audio_queue = self.audio_recorder.subscribe()
        if not self.recognizer.start_continuous_recognition(audio_queue):
            self.audio_recorder.stop()
            self.audio_recorder = None
            messagebox.showerror('错误', '无法启动语音识别，请检查设置或安装依赖')
            return

        # 3) 启动翻译 worker
        self._start_translation_worker(token)

        self.is_recording = True
        self.record_btn.configure(
            text='■ 停止录音',
            bg=self.ds.COLORS['error'],
            activebackground='#D32F2F')
        self.record_btn.bind('<Enter>', lambda e: self.record_btn.configure(bg='#D32F2F'))
        self.record_btn.bind('<Leave>', lambda e: self.record_btn.configure(bg=self.ds.COLORS['error']))
        self._update_recording_time()
        self.status_text.config(text=f'正在录音 · ASR: {self._engine_label()}  ·  翻译: MiMo')

    def _stop_recording(self):
        self.is_recording = False

        if self.recognizer:
            self.recognizer.stop_continuous_recognition()

        audio_info = {'path': '', 'duration': 0.0, 'bytes': 0}
        if self.audio_recorder:
            audio_info = self.audio_recorder.stop()
            self.audio_recorder = None

        # 通知翻译线程收尾；队列满时丢弃最旧一条确保哨兵送达
        try:
            self.translation_queue.put_nowait(None)
        except queue.Full:
            try:
                self.translation_queue.get_nowait()
                self.translation_queue.put_nowait(None)
            except (queue.Empty, queue.Full):
                logger.warning("翻译队列繁忙，worker 将在超时后回收")

        self.record_btn.configure(
            text='● 开始录音',
            bg=self.ds.COLORS['success'],
            activebackground='#28B84C')
        self.record_btn.bind('<Enter>', lambda e: self.record_btn.configure(bg='#28B84C'))
        self.record_btn.bind('<Leave>', lambda e: self.record_btn.configure(bg=self.ds.COLORS['success']))
        self.recording_time_label.config(text='')
        self.status_text.config(text='正在保存录音与笔记…')

        self._finalizing = True
        token = self.session_token
        threading.Thread(
            target=self._finalize_worker, args=(token, audio_info), daemon=True).start()

    def _finalize_worker(self, token: int, audio_info: dict):
        """等待翻译线程收尾，然后把会话保存交给主线程"""
        worker = self.translation_thread
        if worker and worker.is_alive():
            worker.join(timeout=60)
        self.translation_thread = None
        self.msg_queue.put(('finalize', {
            'token': token,
            'audio': audio_info,
        }))

    def _finalize_session(self, data: dict):
        """主线程：转换录音、保存会话"""
        self._finalizing = False
        if data.get('token') != self.session_token:
            return

        audio = data.get('audio') or {}
        wav_path = audio.get('path', '')
        final_path = ''
        if wav_path:
            mp3_path = str(RECORDINGS_DIR / f"{self.session_id}.mp3")
            final_path = AudioRecorder.convert_wav_to_mp3(wav_path, mp3_path)

        end_time = datetime.now()
        if self.session_id and (self.transcripts or final_path):
            self.session_mgr.save_session(
                session_id=self.session_id,
                transcripts=self.transcripts,
                summary=self.summary,
                recording_path=final_path,
                start_time=self.recording_start_time,
                end_time=end_time,
            )
            logger.info("会话已保存: %s (%d 条, 录音=%s)", self.session_id, len(self.transcripts), bool(final_path))
            self.status_text.config(text='已自动保存到历史记录')
            self.root.after(4000, lambda: self.status_text.config(text=self._status_text()))
        else:
            self.status_text.config(text=self._status_text())

        self.recording_start_time = None

    # ==============================================================
    # 回调
    # ==============================================================

    def _start_translation_worker(self, token: int):
        """启动翻译 worker：消费韩语文本，携带滚动上下文调用 MiMo"""
        self.translation_queue = queue.Queue(maxsize=64)

        def worker():
            context = []
            context_size = max(0, int(self.config.translation_context_size))
            while True:
                korean = self.translation_queue.get()
                if korean is None:
                    break
                if token != self.session_token:
                    continue
                chinese = self.mimo_client.translate(
                    korean, self.config.llm_model, context=context)
                if token != self.session_token:
                    continue
                context.append([korean, chinese])
                if context_size and len(context) > context_size:
                    context = context[-context_size:]
                self.msg_queue.put(('transcript', {'korean': korean, 'chinese': chinese}))

        self.translation_thread = threading.Thread(
            target=worker, name="translation-worker", daemon=True)
        self.translation_thread.start()

    def _on_recognized(self, result):
        """识别结果回调（运行在识别线程）：仅入队，避免阻塞识别"""
        korean = result.text
        if not korean or len(korean.strip()) < 2:
            return
        try:
            self.translation_queue.put(korean, timeout=5)
        except queue.Full:
            logger.warning("翻译队列已满，丢弃识别结果: %s…", korean[:20])

    def _on_error(self, error):
        self.msg_queue.put(('error', f'识别错误: {error}'))

    # ==============================================================
    # 转录显示
    # ==============================================================

    def _update_recording_time(self):
        if self.is_recording and self.recording_start_time:
            elapsed = datetime.now() - self.recording_start_time
            m, s = divmod(int(elapsed.total_seconds()), 60)
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
                    for e in list(self.transcripts)
                ])
                summary = self.mimo_client.summarize(transcript, self.config.llm_model)
                self.root.after(0, lambda: self._show_summary(summary))
            except Exception:
                logger.exception("生成总结失败")
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

        header = Frame(win, bg=c['bg_primary'])
        header.pack(fill=X, padx=24, pady=(24, 16))
        self.ds.make_label(header, '课堂总结', style='title').pack(side=LEFT)

        text_card = self.ds.make_card(win)
        text_card.pack(fill=BOTH, expand=True, padx=24, pady=(0, 16))

        text = Text(text_card, wrap=WORD, font=('Segoe UI', 12),
                    bg=c['bg_secondary'], fg=c['text_primary'],
                    relief='flat', bd=0, padx=16, pady=16,
                    spacing1=2, spacing3=2)
        text.pack(fill=BOTH, expand=True, padx=1, pady=1)
        text.insert(1.0, summary)

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
        if not fp:
            return

        lines = [
            '# LecTrans 课堂笔记\n\n',
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
    # 运行
    # ==============================================================

    def run(self):
        self.root.mainloop()

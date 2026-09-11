"""
LecTrans 设置对话框

Azure / 本地 Whisper / MiMo / 音频参数配置（Apple-inspired Dark Mode UI）
"""

import logging
from tkinter import BOTH, LEFT, RIGHT, W, X, Y, Canvas, Frame, Label, StringVar, Toplevel, VERTICAL
from tkinter import ttk, messagebox

from ui.design import DesignSystem

logger = logging.getLogger(__name__)


class SettingsDialog:
    """设置对话框"""

    def __init__(self, parent, config, on_save=None):
        self.config = config
        self.on_save = on_save
        self.ds = DesignSystem()

        c = self.ds.COLORS

        self.win = Toplevel(parent)
        self.win.title('设置')
        self.win.geometry('520x700')
        self.win.minsize(480, 560)
        self.win.configure(bg=c['bg_primary'])
        self.win.transient(parent)
        self.win.grab_set()

        self.ds.apply_theme(self.win)
        self._build_ui()

    def _build_ui(self):
        c = self.ds.COLORS

        # 可滚动画布
        canvas = Canvas(self.win, bg=c['bg_primary'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.win, orient=VERTICAL, command=canvas.yview)
        scroll_frame = Frame(canvas, bg=c['bg_primary'])

        scroll_frame.bind("<Configure>",
                          lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=RIGHT, fill=Y)
        canvas.pack(side=LEFT, fill=BOTH, expand=True)

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        self.win.bind("<Destroy>", lambda e: canvas.unbind_all("<MouseWheel>"))

        main = Frame(scroll_frame, bg=c['bg_primary'])
        main.pack(fill=BOTH, expand=True, padx=28, pady=28)

        self.ds.make_label(main, '设置', style='display').pack(anchor=W, pady=(0, 6))
        self.ds.make_label(main, '配置语音识别与翻译服务',
                           style='muted').pack(anchor=W, pady=(0, 24))

        self._build_asr_card(main)
        self._build_mimo_card(main)

        btn_frame = Frame(main, bg=c['bg_primary'])
        btn_frame.pack(fill=X, pady=(20, 0))

        self.ds.make_button(btn_frame, '取消', self.win.destroy,
                            style='ghost').pack(side=RIGHT, padx=(8, 0))
        self.ds.make_button(btn_frame, '保存', self._save,
                            style='primary').pack(side=RIGHT, padx=(8, 0))
        self.ds.make_button(btn_frame, '测试连接', self._test_connection,
                            style='secondary').pack(side=RIGHT)

    # ==============================================================
    # 语音识别卡片
    # ==============================================================

    def _build_asr_card(self, parent):
        c = self.ds.COLORS

        card = self.ds.make_card(parent)
        card.pack(fill=X, pady=(0, 16))

        inner = Frame(card, bg=c['bg_secondary'])
        inner.pack(fill=X, padx=20, pady=20)

        title_row = Frame(inner, bg=c['bg_secondary'])
        title_row.pack(fill=X, pady=(0, 16))
        Label(title_row, text='●', font=('Segoe UI', 8),
              fg=c['accent'], bg=c['bg_secondary']).pack(side=LEFT, padx=(0, 8))
        self.ds.make_label(title_row, '语音识别引擎 (ASR)', style='heading',
                           bg=c['bg_secondary']).pack(side=LEFT)

        self.ds.make_label(inner, '引擎选择', style='caption', bg=c['bg_secondary']).pack(anchor=W, pady=(0, 4))
        self.asr_engine_var = StringVar(value=self.config.asr_engine)
        ttk.Combobox(inner, textvariable=self.asr_engine_var,
                     values=['local', 'azure'],
                     state='readonly').pack(fill=X, ipady=2, pady=(0, 14))

        # ---------------- Azure ----------------
        self.ds.make_label(inner, '—— Azure 云端配置 ——', style='small', bg=c['bg_secondary']).pack(anchor=W, pady=(0, 4))
        self.ds.make_label(inner, 'API Key', style='caption',
                           bg=c['bg_secondary']).pack(anchor=W, pady=(0, 4))
        self.azure_key_var = StringVar(value=self.config.azure_key)
        self.ds.make_entry(inner, self.azure_key_var, show='●').pack(fill=X, ipady=4, pady=(0, 14))

        row = Frame(inner, bg=c['bg_secondary'])
        row.pack(fill=X, pady=(0, 14))

        f1 = Frame(row, bg=c['bg_secondary'])
        f1.pack(side=LEFT, fill=X, expand=True, padx=(0, 8))
        self.ds.make_label(f1, '区域', style='caption',
                           bg=c['bg_secondary']).pack(anchor=W, pady=(0, 4))
        self.azure_region_var = StringVar(value=self.config.azure_region)
        ttk.Combobox(f1, textvariable=self.azure_region_var,
                     values=['koreacentral', 'eastasia', 'southeastasia', 'westeurope', 'eastus'],
                     state='readonly').pack(fill=X, ipady=2)

        f2 = Frame(row, bg=c['bg_secondary'])
        f2.pack(side=LEFT, fill=X, expand=True)
        self.ds.make_label(f2, '语言', style='caption',
                           bg=c['bg_secondary']).pack(anchor=W, pady=(0, 4))
        self.azure_language_var = StringVar(value=self.config.azure_language)
        ttk.Combobox(f2, textvariable=self.azure_language_var,
                     values=['ko-KR', 'en-US', 'zh-CN', 'ja-JP'],
                     state='readonly').pack(fill=X, ipady=2)

        # ---------------- Local Whisper ----------------
        self.ds.make_label(inner, '—— 本地 Whisper 配置 ——', style='small',
                           bg=c['bg_secondary']).pack(anchor=W, pady=(8, 4))
        self.ds.make_label(inner, '模型规模 (推荐 base/small)', style='caption',
                           bg=c['bg_secondary']).pack(anchor=W, pady=(0, 4))
        self.whisper_model_var = StringVar(value=self.config.whisper_model)
        ttk.Combobox(inner, textvariable=self.whisper_model_var,
                     values=['tiny', 'base', 'small', 'medium', 'large-v3'],
                     state='readonly').pack(fill=X, ipady=2, pady=(0, 14))

        vad_row = Frame(inner, bg=c['bg_secondary'])
        vad_row.pack(fill=X)
        vad_fields = [
            ('噪声门限', 'energy_threshold', self.config.energy_threshold, 8),
            ('静音断句(s)', 'silence_duration', self.config.silence_duration, 8),
            ('最长语音(s)', 'max_utterance_seconds', self.config.max_utterance_seconds, 8),
        ]
        self.vad_vars = {}
        for i, (label, key, value, width) in enumerate(vad_fields):
            f = Frame(vad_row, bg=c['bg_secondary'])
            f.pack(side=LEFT, fill=X, expand=True, padx=(0 if i == 0 else 6, 0))
            self.ds.make_label(f, label, style='caption', bg=c['bg_secondary']).pack(anchor=W, pady=(0, 4))
            var = StringVar(value=str(value))
            self.ds.make_entry(f, var, width=width).pack(fill=X, ipady=4)
            self.vad_vars[key] = var

    # ==============================================================
    # MiMo 卡片
    # ==============================================================

    def _build_mimo_card(self, parent):
        c = self.ds.COLORS

        card = self.ds.make_card(parent)
        card.pack(fill=X, pady=(0, 16))

        inner = Frame(card, bg=c['bg_secondary'])
        inner.pack(fill=X, padx=20, pady=20)

        title_row = Frame(inner, bg=c['bg_secondary'])
        title_row.pack(fill=X, pady=(0, 16))
        Label(title_row, text='●', font=('Segoe UI', 8),
              fg=c['success'], bg=c['bg_secondary']).pack(side=LEFT, padx=(0, 8))
        self.ds.make_label(title_row, 'MiMo API', style='heading',
                           bg=c['bg_secondary']).pack(side=LEFT)
        self.ds.make_label(title_row, '翻译 / 总结', style='caption',
                           bg=c['bg_secondary']).pack(side=LEFT, padx=(8, 0))

        self.ds.make_label(inner, 'API Key', style='caption',
                           bg=c['bg_secondary']).pack(anchor=W, pady=(0, 4))
        self.api_key_var = StringVar(value=self.config.api_key)
        self.ds.make_entry(inner, self.api_key_var, show='●').pack(fill=X, ipady=4, pady=(0, 14))

        self.ds.make_label(inner, 'Base URL', style='caption',
                           bg=c['bg_secondary']).pack(anchor=W, pady=(0, 4))
        self.base_url_var = StringVar(value=self.config.base_url)
        self.ds.make_entry(inner, self.base_url_var).pack(fill=X, ipady=4, pady=(0, 14))

        bottom_row = Frame(inner, bg=c['bg_secondary'])
        bottom_row.pack(fill=X)

        f1 = Frame(bottom_row, bg=c['bg_secondary'])
        f1.pack(side=LEFT, fill=X, expand=True, padx=(0, 8))
        self.ds.make_label(f1, '翻译模型', style='caption', bg=c['bg_secondary']).pack(anchor=W, pady=(0, 4))
        self.llm_model_var = StringVar(value=self.config.llm_model)
        ttk.Combobox(f1, textvariable=self.llm_model_var,
                     values=['mimo-v2.5-pro', 'mimo-v2.5'],
                     state='readonly').pack(fill=X, ipady=2)

        f2 = Frame(bottom_row, bg=c['bg_secondary'])
        f2.pack(side=LEFT)
        self.ds.make_label(f2, '上下文条数', style='caption', bg=c['bg_secondary']).pack(anchor=W, pady=(0, 4))
        self.context_size_var = StringVar(value=str(self.config.translation_context_size))
        self.ds.make_entry(f2, self.context_size_var, width=8).pack(ipady=4)

        self.ds.make_label(inner, '获取 Key → mimo.xiaomi.com', style='small',
                           bg=c['bg_secondary']).pack(anchor=W, pady=(12, 0))

    # ==============================================================
    # 保存 / 测试
    # ==============================================================

    def _read_number(self, key: str, cast, label: str):
        """读取数值输入框，非法时回退到原配置并提示"""
        raw = self.vad_vars[key].get().strip()
        try:
            value = cast(raw)
            if value <= 0:
                raise ValueError
            return value
        except ValueError:
            old = getattr(self.config, key)
            logger.warning("设置项 %s 输入非法: %r，保留原值 %s", label, raw, old)
            return old

    def _save(self):
        self.config.asr_engine = self.asr_engine_var.get()
        self.config.whisper_model = self.whisper_model_var.get()
        self.config.azure_key = self.azure_key_var.get()
        self.config.azure_region = self.azure_region_var.get()
        self.config.azure_language = self.azure_language_var.get()
        self.config.api_key = self.api_key_var.get()
        self.config.base_url = self.base_url_var.get()
        self.config.llm_model = self.llm_model_var.get()

        self.config.energy_threshold = int(self._read_number('energy_threshold', float, '噪声门限'))
        self.config.silence_duration = float(self._read_number('silence_duration', float, '静音断句'))
        self.config.max_utterance_seconds = float(self._read_number('max_utterance_seconds', float, '最长语音'))

        try:
            context_size = int(self.context_size_var.get().strip())
            if context_size < 0:
                raise ValueError
            self.config.translation_context_size = context_size
        except ValueError:
            logger.warning("上下文条数输入非法，保留原值 %s", self.config.translation_context_size)

        self.config.save()

        if self.on_save:
            self.on_save()

        messagebox.showinfo('成功', '设置已保存')
        self.win.destroy()

    def _test_connection(self):
        results = []

        asr_engine = self.asr_engine_var.get()
        if asr_engine == "azure":
            azure_key = self.azure_key_var.get()
            azure_region = self.azure_region_var.get()
            if azure_key:
                try:
                    import azure.cognitiveservices.speech as speechsdk

                    speechsdk.SpeechConfig(subscription=azure_key, region=azure_region)
                    results.append("✅ Azure Speech API 配置有效")
                except Exception as e:
                    results.append(f"❌ Azure 错误: {str(e)}")
            else:
                results.append("⚠️ Azure API Key 未填写")
        else:
            try:
                import faster_whisper  # noqa: F401

                results.append("✅ Faster-Whisper 环境已安装就绪")
            except ImportError:
                results.append("❌ Faster-Whisper 尚未安装，请通过 pip 安装")

        mimo_key = self.api_key_var.get()
        mimo_url = self.base_url_var.get()
        mimo_model = self.llm_model_var.get()
        if mimo_key:
            try:
                from openai import OpenAI

                client = OpenAI(api_key=mimo_key, base_url=mimo_url)
                client.chat.completions.create(
                    model=mimo_model,
                    messages=[{'role': 'user', 'content': 'test'}],
                    max_tokens=5,
                )
                results.append("✅ MiMo API 连接成功")
            except Exception as e:
                results.append(f"❌ MiMo 错误: {str(e)}")
        else:
            results.append("⚠️ MiMo API Key 未填写")

        messagebox.showinfo('测试结果', '\n'.join(results))

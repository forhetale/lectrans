"""
LecTrans 设置对话框
Azure / MiMo / 音频设备配置
Apple-inspired Dark Mode UI
"""

from tkinter import *
from tkinter import ttk, messagebox

from ui.design import DesignSystem


class SettingsDialog:
    """设置对话框"""

    def __init__(self, parent, config, on_save=None):
        self.config = config
        self.on_save = on_save
        self.ds = DesignSystem()

        c = self.ds.COLORS

        self.win = Toplevel(parent)
        self.win.title('设置')
        self.win.geometry('520x620')
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

        # 绑定鼠标滚轮
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        self.win.bind("<Destroy>", lambda e: canvas.unbind_all("<MouseWheel>"))

        main = Frame(scroll_frame, bg=c['bg_primary'])
        main.pack(fill=BOTH, expand=True, padx=28, pady=28)

        # ---- 标题 ----
        self.ds.make_label(main, '设置', style='display').pack(anchor=W, pady=(0, 6))
        self.ds.make_label(main, '配置语音识别与翻译服务',
                           style='muted').pack(anchor=W, pady=(0, 24))

        # ---- Azure 语音识别卡片 ----
        self._build_azure_card(main)

        # ---- MiMo API 卡片 ----
        self._build_mimo_card(main)

        # ---- 按钮组 ----
        btn_frame = Frame(main, bg=c['bg_primary'])
        btn_frame.pack(fill=X, pady=(20, 0))

        self.ds.make_button(btn_frame, '取消', self.win.destroy,
                            style='ghost').pack(side=RIGHT, padx=(8, 0))
        self.ds.make_button(btn_frame, '保存', self._save,
                            style='primary').pack(side=RIGHT, padx=(8, 0))
        self.ds.make_button(btn_frame, '测试连接', self._test_connection,
                            style='secondary').pack(side=RIGHT)

    def _build_azure_card(self, parent):
        """Azure 语音识别配置卡片"""
        c = self.ds.COLORS

        card = self.ds.make_card(parent)
        card.pack(fill=X, pady=(0, 16))

        inner = Frame(card, bg=c['bg_secondary'])
        inner.pack(fill=X, padx=20, pady=20)

        # 卡片标题
        title_row = Frame(inner, bg=c['bg_secondary'])
        title_row.pack(fill=X, pady=(0, 16))
        Label(title_row, text='●', font=('Segoe UI', 8),
              fg=c['accent'], bg=c['bg_secondary']).pack(side=LEFT, padx=(0, 8))
        self.ds.make_label(title_row, 'Azure Speech API', style='heading',
                           bg=c['bg_secondary']).pack(side=LEFT)
        self.ds.make_label(title_row, '语音识别', style='caption',
                           bg=c['bg_secondary']).pack(side=LEFT, padx=(8, 0))

        # API Key
        self.ds.make_label(inner, 'API Key', style='caption',
                           bg=c['bg_secondary']).pack(anchor=W, pady=(0, 4))
        self.azure_key_var = StringVar(value=self.config.azure_key)
        self.ds.make_entry(inner, self.azure_key_var, show='●').pack(fill=X, ipady=4, pady=(0, 14))

        # 区域 + 语言（横排）
        row = Frame(inner, bg=c['bg_secondary'])
        row.pack(fill=X)

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

        # 提示
        self.ds.make_label(inner, '获取 Key → portal.azure.com', style='small',
                           bg=c['bg_secondary']).pack(anchor=W, pady=(12, 0))

    def _build_mimo_card(self, parent):
        """MiMo 翻译 API 配置卡片"""
        c = self.ds.COLORS

        card = self.ds.make_card(parent)
        card.pack(fill=X, pady=(0, 16))

        inner = Frame(card, bg=c['bg_secondary'])
        inner.pack(fill=X, padx=20, pady=20)

        # 卡片标题
        title_row = Frame(inner, bg=c['bg_secondary'])
        title_row.pack(fill=X, pady=(0, 16))
        Label(title_row, text='●', font=('Segoe UI', 8),
              fg=c['success'], bg=c['bg_secondary']).pack(side=LEFT, padx=(0, 8))
        self.ds.make_label(title_row, 'MiMo API', style='heading',
                           bg=c['bg_secondary']).pack(side=LEFT)
        self.ds.make_label(title_row, '翻译 / 总结', style='caption',
                           bg=c['bg_secondary']).pack(side=LEFT, padx=(8, 0))

        # API Key
        self.ds.make_label(inner, 'API Key', style='caption',
                           bg=c['bg_secondary']).pack(anchor=W, pady=(0, 4))
        self.api_key_var = StringVar(value=self.config.api_key)
        self.ds.make_entry(inner, self.api_key_var, show='●').pack(fill=X, ipady=4, pady=(0, 14))

        # Base URL
        self.ds.make_label(inner, 'Base URL', style='caption',
                           bg=c['bg_secondary']).pack(anchor=W, pady=(0, 4))
        self.base_url_var = StringVar(value=self.config.base_url)
        self.ds.make_entry(inner, self.base_url_var).pack(fill=X, ipady=4, pady=(0, 14))

        # 模型选择
        self.ds.make_label(inner, '翻译模型', style='caption',
                           bg=c['bg_secondary']).pack(anchor=W, pady=(0, 4))
        self.llm_model_var = StringVar(value=self.config.llm_model)
        ttk.Combobox(inner, textvariable=self.llm_model_var,
                     values=['mimo-v2.5-pro', 'mimo-v2.5'],
                     state='readonly').pack(fill=X, ipady=2)

        # 提示
        self.ds.make_label(inner, '获取 Key → mimo.xiaomi.com', style='small',
                           bg=c['bg_secondary']).pack(anchor=W, pady=(12, 0))

    def _save(self):
        self.config.azure_key = self.azure_key_var.get()
        self.config.azure_region = self.azure_region_var.get()
        self.config.azure_language = self.azure_language_var.get()
        self.config.api_key = self.api_key_var.get()
        self.config.base_url = self.base_url_var.get()
        self.config.llm_model = self.llm_model_var.get()
        self.config.save()

        if self.on_save:
            self.on_save()

        messagebox.showinfo('成功', '设置已保存')
        self.win.destroy()

    def _test_connection(self):
        results = []

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

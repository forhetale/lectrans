"""
LecTrans 设计系统
Apple-inspired Dark Mode — 统一管理颜色、字体、间距及自定义控件
"""

from tkinter import *
from tkinter import ttk


class DesignSystem:
    """Apple 风格设计系统常量 + 控件工厂"""

    # ──────────────────────────────────────────────
    # 配色（macOS Dark Mode 风格层次灰 + 系统蓝强调色）
    # ──────────────────────────────────────────────

    COLORS = {
        # 背景层级
        'bg_primary':    '#1C1C1E',
        'bg_secondary':  '#2C2C2E',
        'bg_tertiary':   '#3A3A3C',
        'bg_elevated':   '#48484A',

        # 文字
        'text_primary':   '#F5F5F7',
        'text_secondary': '#A1A1A6',
        'text_muted':     '#636366',

        # 强调色 — Apple Blue
        'accent':         '#0A84FF',
        'accent_hover':   '#409CFF',
        'accent_pressed': '#0071E3',

        # 语义色
        'success':  '#30D158',
        'warning':  '#FFD60A',
        'error':    '#FF453A',

        # 边框 / 分隔
        'separator': '#38383A',
        'border':    '#3A3A3C',
    }

    # ──────────────────────────────────────────────
    # 字体
    # ──────────────────────────────────────────────

    FONTS = {
        'display':    ('Segoe UI', 22, 'bold'),
        'title':      ('Segoe UI', 17, 'bold'),
        'heading':    ('Segoe UI', 14, 'bold'),
        'body':       ('Segoe UI', 13),
        'body_bold':  ('Segoe UI', 13, 'bold'),
        'callout':    ('Segoe UI', 12),
        'caption':    ('Segoe UI', 11),
        'small':      ('Segoe UI', 10),
        'mono':       ('Consolas', 12),
    }

    # ──────────────────────────────────────────────
    # 间距 & 尺寸
    # ──────────────────────────────────────────────

    SPACING = {'xs': 4, 's': 8, 'm': 12, 'l': 16, 'xl': 24, 'xxl': 32}

    NAVBAR_HEIGHT = 52
    STATUSBAR_HEIGHT = 28
    CONTROL_HEIGHT = 56

    # ──────────────────────────────────────────────
    # ttk 主题配置
    # ──────────────────────────────────────────────

    def apply_theme(self, root):
        """配置 ttk 全局样式，使 Combobox / Scrollbar / Treeview 等原生控件
        融入 Apple Dark Mode 视觉，并应用深色系统标题栏"""
        import ctypes
        try:
            root.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
            
            # 1. 启用 Windows 沉浸式深色模式 (Windows 10/11)
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            value = ctypes.c_int(2)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, 
                ctypes.byref(value), ctypes.sizeof(value)
            )
            
            # 2. 设定标题栏颜色与主背景融为一体 (Windows 11)
            bg = self.COLORS['bg_primary']
            r, g, b = int(bg[1:3], 16), int(bg[3:5], 16), int(bg[5:7], 16)
            color = ctypes.c_int(b << 16 | g << 8 | r)
            DWMWA_CAPTION_COLOR = 35
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, DWMWA_CAPTION_COLOR, 
                ctypes.byref(color), ctypes.sizeof(color)
            )
        except Exception:
            pass

        style = ttk.Style(root)
        style.theme_use('clam')

        c = self.COLORS

        # ---- Combobox ----
        style.configure('TCombobox',
                         fieldbackground=c['bg_tertiary'],
                         background=c['bg_tertiary'],
                         foreground=c['text_primary'],
                         arrowcolor=c['text_secondary'],
                         borderwidth=0,
                         padding=6)
        style.map('TCombobox',
                   fieldbackground=[('readonly', c['bg_tertiary'])],
                   selectbackground=[('readonly', c['bg_tertiary'])],
                   selectforeground=[('readonly', c['text_primary'])])

        # ---- Scrollbar ----
        style.configure('Vertical.TScrollbar',
                         background=c['bg_secondary'],
                         troughcolor=c['bg_primary'],
                         borderwidth=0,
                         arrowsize=0,
                         width=8)
        style.map('Vertical.TScrollbar',
                   background=[('active', c['bg_elevated'])])

        # ---- Progressbar ----
        style.configure('TProgressbar',
                         background=c['accent'],
                         troughcolor=c['bg_tertiary'],
                         borderwidth=0,
                         thickness=4)

        # ---- Treeview（用于历史列表）----
        style.configure('Treeview',
                         background=c['bg_secondary'],
                         foreground=c['text_primary'],
                         fieldbackground=c['bg_secondary'],
                         borderwidth=0,
                         rowheight=36,
                         font=self.FONTS['body'])
        style.configure('Treeview.Heading',
                         background=c['bg_tertiary'],
                         foreground=c['text_secondary'],
                         borderwidth=0,
                         font=self.FONTS['caption'])
        style.map('Treeview',
                   background=[('selected', c['accent'])],
                   foreground=[('selected', '#FFFFFF')])

        # Combobox 下拉列表（需要 option_add 来设置全局 Listbox 样式）
        root.option_add('*TCombobox*Listbox.background', c['bg_tertiary'])
        root.option_add('*TCombobox*Listbox.foreground', c['text_primary'])
        root.option_add('*TCombobox*Listbox.selectBackground', c['accent'])
        root.option_add('*TCombobox*Listbox.selectForeground', '#FFFFFF')

    # ──────────────────────────────────────────────
    # 控件工厂方法
    # ──────────────────────────────────────────────

    def make_button(self, parent, text, command, style='primary', **kw):
        """创建标准化按钮

        style: 'primary' | 'secondary' | 'destructive' | 'ghost'
        """
        c = self.COLORS
        styles = {
            'primary':     {'bg': c['accent'],      'fg': '#FFFFFF',           'abg': c['accent_pressed']},
            'secondary':   {'bg': c['bg_tertiary'],  'fg': c['text_primary'],  'abg': c['bg_elevated']},
            'destructive': {'bg': c['error'],        'fg': '#FFFFFF',           'abg': '#D32F2F'},
            'ghost':       {'bg': c['bg_secondary'], 'fg': c['text_secondary'], 'abg': c['bg_tertiary']},
        }
        s = styles.get(style, styles['primary'])

        btn = Button(parent, text=text, font=self.FONTS['body'],
                     bg=s['bg'], fg=s['fg'],
                     activebackground=s['abg'], activeforeground=s['fg'],
                     relief='flat', bd=0, padx=16, pady=7,
                     cursor='hand2', command=command, **kw)

        # hover 效果
        btn.bind('<Enter>', lambda e: btn.configure(bg=s['abg']))
        btn.bind('<Leave>', lambda e: btn.configure(bg=s['bg']))
        return btn

    def make_pill_button(self, parent, text, command, color='success', **kw):
        """创建药丸形状按钮（录音按钮等场景）"""
        c = self.COLORS
        colors = {
            'success': {'bg': c['success'], 'abg': '#28B84C'},
            'error':   {'bg': c['error'],   'abg': '#D32F2F'},
            'accent':  {'bg': c['accent'],  'abg': c['accent_pressed']},
        }
        col = colors.get(color, colors['success'])

        btn = Button(parent, text=text, font=self.FONTS['body_bold'],
                     bg=col['bg'], fg='#FFFFFF',
                     activebackground=col['abg'], activeforeground='#FFFFFF',
                     relief='flat', bd=0, padx=24, pady=8,
                     cursor='hand2', command=command, **kw)
        btn.bind('<Enter>', lambda e: btn.configure(bg=col['abg']))
        btn.bind('<Leave>', lambda e: btn.configure(bg=col['bg']))
        return btn

    def make_card(self, parent, **kw):
        """创建圆角风格卡片容器"""
        return Frame(parent, bg=self.COLORS['bg_secondary'],
                     highlightthickness=1, highlightbackground=self.COLORS['border'],
                     **kw)

    def make_entry(self, parent, textvariable, show=None, **kw):
        """创建标准化输入框"""
        entry = Entry(parent, textvariable=textvariable,
                      font=self.FONTS['body'],
                      bg=self.COLORS['bg_tertiary'],
                      fg=self.COLORS['text_primary'],
                      insertbackground=self.COLORS['text_primary'],
                      selectbackground=self.COLORS['accent'],
                      relief='flat', bd=0,
                      highlightthickness=1,
                      highlightbackground=self.COLORS['border'],
                      highlightcolor=self.COLORS['accent'],
                      **kw)
        if show:
            entry.configure(show=show)
        # 内边距通过 ipadx / ipady 无法精确控制，改用 pack 时的 padx
        return entry

    def make_label(self, parent, text, style='body', **kw):
        """创建标准化标签

        style: 'display' | 'title' | 'heading' | 'body' | 'body_bold'
               | 'callout' | 'caption' | 'small' | 'muted'
        """
        c = self.COLORS
        fg_map = {
            'display':   c['text_primary'],
            'title':     c['text_primary'],
            'heading':   c['text_primary'],
            'body':      c['text_primary'],
            'body_bold': c['text_primary'],
            'callout':   c['text_secondary'],
            'caption':   c['text_secondary'],
            'small':     c['text_muted'],
            'muted':     c['text_muted'],
        }
        font_key = style if style != 'muted' else 'caption'
        return Label(parent, text=text,
                     font=self.FONTS.get(font_key, self.FONTS['body']),
                     fg=fg_map.get(style, c['text_primary']),
                     bg=kw.pop('bg', c['bg_primary']),
                     **kw)

    def make_separator(self, parent, orient='horizontal'):
        """创建分隔线"""
        if orient == 'horizontal':
            return Frame(parent, height=1, bg=self.COLORS['separator'])
        return Frame(parent, width=1, bg=self.COLORS['separator'])

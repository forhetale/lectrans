"""
LecTrans 历史记录对话框
浏览、查看、导出、删除历史会话
Apple-inspired Dark Mode UI
"""

import os
from datetime import datetime
from tkinter import *
from tkinter import ttk, messagebox, filedialog

from ui.design import DesignSystem
from core.session_manager import SessionManager, TranscriptEntry


class HistoryDialog:
    """历史记录对话框"""

    def __init__(self, parent):
        self.ds = DesignSystem()
        self.session_mgr = SessionManager()
        self.sessions = []
        self.selected_session_id = None

        c = self.ds.COLORS

        self.win = Toplevel(parent)
        self.win.title('历史记录')
        self.win.geometry('960x640')
        self.win.minsize(720, 420)
        self.win.configure(bg=c['bg_primary'])
        self.win.transient(parent)
        self.win.grab_set()

        self.ds.apply_theme(self.win)
        self._build_ui()
        self._load_sessions()

    def _build_ui(self):
        c = self.ds.COLORS

        # ──── 顶部标题栏 ────
        header = Frame(self.win, bg=c['bg_secondary'], height=self.ds.NAVBAR_HEIGHT)
        header.pack(fill=X)
        header.pack_propagate(False)

        header_inner = Frame(header, bg=c['bg_secondary'])
        header_inner.pack(fill=BOTH, expand=True, padx=20)

        Label(header_inner, text='●', font=('Segoe UI', 8),
              fg=c['accent'], bg=c['bg_secondary']).pack(side=LEFT, padx=(0, 8), pady=0)
        self.ds.make_label(header_inner, '历史记录', style='title',
                           bg=c['bg_secondary']).pack(side=LEFT)

        # 关闭按钮
        self.ds.make_button(header_inner, '关闭', self.win.destroy,
                            style='ghost').pack(side=RIGHT)

        self.ds.make_separator(self.win).pack(fill=X)

        # ──── 主体：左右分栏 ────
        body = Frame(self.win, bg=c['bg_primary'])
        body.pack(fill=BOTH, expand=True)

        # 左侧：会话列表
        left = Frame(body, bg=c['bg_secondary'], width=280)
        left.pack(side=LEFT, fill=Y)
        left.pack_propagate(False)

        # 列表标题
        list_header = Frame(left, bg=c['bg_secondary'])
        list_header.pack(fill=X, padx=16, pady=(16, 8))
        self.ds.make_label(list_header, '会话列表', style='caption',
                           bg=c['bg_secondary']).pack(side=LEFT)

        # 会话 Treeview
        tree_frame = Frame(left, bg=c['bg_secondary'])
        tree_frame.pack(fill=BOTH, expand=True, padx=10, pady=(0, 10))

        self.session_tree = ttk.Treeview(
            tree_frame, columns=('date', 'count'), show='tree',
            selectmode='browse', height=15)
        self.session_tree.column('#0', width=240)
        self.session_tree.pack(side=LEFT, fill=BOTH, expand=True)

        tree_scroll = ttk.Scrollbar(tree_frame, orient=VERTICAL,
                                     command=self.session_tree.yview)
        tree_scroll.pack(side=RIGHT, fill=Y)
        self.session_tree.configure(yscrollcommand=tree_scroll.set)
        self.session_tree.bind('<<TreeviewSelect>>', self._on_select)

        # 垂直分隔
        self.ds.make_separator(body, orient='vertical').pack(side=LEFT, fill=Y)

        # 右侧：详情
        right = Frame(body, bg=c['bg_primary'])
        right.pack(side=LEFT, fill=BOTH, expand=True)

        # 详情头部
        detail_top = Frame(right, bg=c['bg_primary'])
        detail_top.pack(fill=X, padx=20, pady=(16, 8))

        self.detail_header = self.ds.make_label(
            detail_top, '选择一个会话查看详情', style='callout')
        self.detail_header.pack(side=LEFT)

        # 详情内容区：双栏
        detail_content = Frame(right, bg=c['bg_primary'])
        detail_content.pack(fill=BOTH, expand=True, padx=12, pady=(0, 8))
        detail_content.columnconfigure(0, weight=1)
        detail_content.columnconfigure(1, weight=1)
        detail_content.rowconfigure(0, weight=1)

        # 韩语列
        ko_card = self.ds.make_card(detail_content)
        ko_card.grid(row=0, column=0, sticky='nsew', padx=(0, 4))

        ko_header = Frame(ko_card, bg=c['bg_secondary'])
        ko_header.pack(fill=X, padx=14, pady=(12, 4))
        Label(ko_header, text='●', font=('Segoe UI', 7),
              fg='#FF6961', bg=c['bg_secondary']).pack(side=LEFT, padx=(0, 6))
        self.ds.make_label(ko_header, '한국어', style='body_bold',
                           bg=c['bg_secondary']).pack(side=LEFT)

        self.ko_text = Text(ko_card, wrap=WORD, font=('Segoe UI', 11),
                            bg=c['bg_secondary'], fg=c['text_primary'],
                            relief='flat', bd=0, padx=12, pady=8,
                            spacing1=2, spacing3=2, state=DISABLED)
        self.ko_text.pack(fill=BOTH, expand=True, padx=6, pady=(0, 6))

        # 中文列
        zh_card = self.ds.make_card(detail_content)
        zh_card.grid(row=0, column=1, sticky='nsew', padx=(4, 0))

        zh_header = Frame(zh_card, bg=c['bg_secondary'])
        zh_header.pack(fill=X, padx=14, pady=(12, 4))
        Label(zh_header, text='●', font=('Segoe UI', 7),
              fg=c['accent'], bg=c['bg_secondary']).pack(side=LEFT, padx=(0, 6))
        self.ds.make_label(zh_header, '中文', style='body_bold',
                           bg=c['bg_secondary']).pack(side=LEFT)

        self.zh_text = Text(zh_card, wrap=WORD, font=('Segoe UI', 11),
                            bg=c['bg_secondary'], fg=c['text_primary'],
                            relief='flat', bd=0, padx=12, pady=8,
                            spacing1=2, spacing3=2, state=DISABLED)
        self.zh_text.pack(fill=BOTH, expand=True, padx=6, pady=(0, 6))

        # ──── 底部操作栏 ────
        self.ds.make_separator(self.win).pack(fill=X, side=BOTTOM)

        bottom = Frame(self.win, bg=c['bg_secondary'], height=54)
        bottom.pack(fill=X, side=BOTTOM)
        bottom.pack_propagate(False)

        btn_inner = Frame(bottom, bg=c['bg_secondary'])
        btn_inner.pack(fill=BOTH, expand=True, padx=20, pady=10)

        self.ds.make_button(btn_inner, '导出 Markdown', self._export_md,
                            style='primary').pack(side=LEFT, padx=(0, 8))
        self.ds.make_button(btn_inner, '播放录音', self._play_recording,
                            style='secondary').pack(side=LEFT, padx=(0, 8))
        self.ds.make_button(btn_inner, '打开所在文件夹', self._open_recording_folder,
                            style='secondary').pack(side=LEFT, padx=(0, 8))
        self.ds.make_button(btn_inner, '删除', self._delete_session,
                            style='destructive').pack(side=LEFT)

    def _load_sessions(self):
        """加载会话列表"""
        self.sessions = self.session_mgr.list_sessions()

        # 清空 Treeview
        for item in self.session_tree.get_children():
            self.session_tree.delete(item)

        for i, s in enumerate(self.sessions):
            start = s.get("start_time", "")
            if start:
                try:
                    dt = datetime.fromisoformat(start)
                    label = f"{dt.strftime('%m/%d  %H:%M')}    {s['total_entries']} 条"
                except Exception:
                    label = f"{start}    {s['total_entries']} 条"
            else:
                label = f"{s['session_id']}    {s['total_entries']} 条"

            self.session_tree.insert('', END, iid=str(i), text=label)

    def _on_select(self, event):
        """选中会话"""
        sel = self.session_tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        session_info = self.sessions[idx]
        self.selected_session_id = session_info["session_id"]

        data = self.session_mgr.load_session(self.selected_session_id)
        if not data:
            return

        # 更新头部
        start = data.get("start_time", "")
        entries = data.get("total_entries", 0)
        rec = "  ·  包含录音" if data.get("recording_path") else ""
        self.detail_header.config(text=f"{start}  ·  {entries} 条记录{rec}")

        # 更新双栏内容
        transcripts = data.get("transcripts", [])

        for widget, key in [(self.ko_text, 'korean'), (self.zh_text, 'chinese')]:
            widget.config(state=NORMAL)
            widget.delete(1.0, END)
            for t in transcripts:
                ts = t.get("timestamp", "")
                if ts:
                    try:
                        ts = datetime.fromisoformat(ts).strftime("%H:%M:%S")
                    except Exception:
                        pass
                widget.insert(END, f'[{ts}]\n{t[key]}\n\n')
            widget.config(state=DISABLED)

    def _export_md(self):
        """导出为 Markdown"""
        if not self.selected_session_id:
            messagebox.showwarning('提示', '请先选择一个会话')
            return
        fp = filedialog.asksaveasfilename(
            defaultextension='.md',
            filetypes=[('Markdown', '*.md')],
            initialfile=f'{self.selected_session_id}.md',
        )
        if fp:
            self.session_mgr.export_markdown(self.selected_session_id, output_path=fp)
            messagebox.showinfo('成功', '已导出')

    def _play_recording(self):
        """播放关联录音"""
        if not self.selected_session_id:
            messagebox.showwarning('提示', '请先选择一个会话')
            return
        data = self.session_mgr.load_session(self.selected_session_id)
        rec_path = data.get("recording_path", "") if data else ""
        if not rec_path or not os.path.exists(rec_path):
            messagebox.showinfo('提示', '该会话没有关联录音文件')
            return
        # 使用系统默认播放器
        os.startfile(rec_path)

    def _open_recording_folder(self):
        """在资源管理器中显示关联录音"""
        if not self.selected_session_id:
            messagebox.showwarning('提示', '请先选择一个会话')
            return
        data = self.session_mgr.load_session(self.selected_session_id)
        rec_path = data.get("recording_path", "") if data else ""
        if not rec_path or not os.path.exists(rec_path):
            messagebox.showinfo('提示', '该会话没有关联录音文件')
            return
        
        # 在 Windows 资源管理器中选中该文件
        import subprocess
        subprocess.Popen(f'explorer /select,"{os.path.abspath(rec_path)}"')

    def _delete_session(self):
        """删除选中会话"""
        if not self.selected_session_id:
            messagebox.showwarning('提示', '请先选择一个会话')
            return
        if messagebox.askyesno('确认', f'确定删除该会话？\n(会同时删除关联录音)'):
            self.session_mgr.delete_session(self.selected_session_id)
            self.selected_session_id = None
            # 清空详情
            self.detail_header.config(text='选择一个会话查看详情')
            for w in [self.ko_text, self.zh_text]:
                w.config(state=NORMAL)
                w.delete(1.0, END)
                w.config(state=DISABLED)
            # 刷新列表
            self._load_sessions()

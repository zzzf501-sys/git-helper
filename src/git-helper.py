#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Git 助手 — 可视化 Git 工具
功能：工作区/暂存区/已提交 三区管理
      一键暂存、提交、回滚
      地址栏切换目录
双击运行即可使用，无需安装额外依赖。
"""

import os
import json
import subprocess
import urllib.request
import urllib.parse
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, filedialog, messagebox

# ──────────────────────────────────────────────
# Git 命令封装
# ──────────────────────────────────────────────

class GitHelper:
    """封装 Git 命令调用"""

    def __init__(self, working_dir):
        self.working_dir = working_dir

    def _run(self, args):
        """执行 Git 命令，返回 CompletedProcess 或 None"""
        try:
            return subprocess.run(
                ['git', '-c', 'core.quotepath=false'] + args,
                cwd=self.working_dir,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
            )
        except FileNotFoundError:
            return None

    # ── 查询 ──

    def is_git_repo(self):
        r = self._run(['rev-parse', '--git-dir'])
        return r is not None and r.returncode == 0

    def get_branch(self):
        r = self._run(['branch', '--show-current'])
        return r.stdout.strip() if r and r.returncode == 0 else "N/A"

    def get_all_files(self):
        """
        返回当前目录「所有文件/文件夹」及其 Git 状态。
        每条记录：{path, display, status, is_dir}
        status: tracked / modified / staged / untracked / ignored
        """
        if not self.is_git_repo():
            return []

        items = os.listdir(self.working_dir)

        # ---- 收集 Git 数据 ----
        tracked_top = set()      # 顶层跟踪文件（不含 /）
        tracked_dirs = set()     # 跟踪的目录前缀
        r = self._run(['ls-files'])
        if r and r.returncode == 0:
            for line in r.stdout.splitlines():
                f = line.strip()
                if not f:
                    continue
                if '/' in f:
                    tracked_dirs.add(f.split('/')[0])
                else:
                    tracked_top.add(f)

        # 被忽略的文件
        ignored_set = set()
        r = self._run(['ls-files', '--others', '--ignored', '--exclude-standard'])
        if r and r.returncode == 0:
            for line in r.stdout.splitlines():
                ignored_set.add(line.strip())

        # porcelain 状态
        status_map = {}
        r = self._run(['status', '--porcelain'])
        if r and r.returncode == 0:
            for line in r.stdout.splitlines():
                if not line.strip():
                    continue
                flags = line[:2]
                path = line[3:].strip()
                status_map[path] = flags

        # ---- 逐项归类 ----
        result = []
        for item in sorted(items, key=lambda x: (not os.path.isdir(os.path.join(self.working_dir, x)), x.lower())):
            if item == '.git':
                continue
            full = os.path.join(self.working_dir, item)
            is_dir = os.path.isdir(full)
            display = item + '/' if is_dir else item

            if item in ignored_set:
                status = 'ignored'
            elif item in status_map:
                flags = status_map[item]
                if flags[0] not in (' ', '?', '!'):
                    status = 'staged'
                elif flags == '??':
                    status = 'untracked'
                else:
                    status = 'modified'
            elif item in tracked_top:
                status = 'tracked'
            elif is_dir and item in tracked_dirs:
                status = 'tracked'
            else:
                status = 'untracked'

            result.append(dict(path=item, display=display, status=status, is_dir=is_dir))

        return result

    def get_staged_files(self):
        """返回已暂存的文件路径列表"""
        r = self._run(['status', '--porcelain'])
        if r and r.returncode == 0:
            staged = []
            for line in r.stdout.splitlines():
                if not line.strip():
                    continue
                flags = line[:2]
                if flags[0] not in (' ', '?', '!'):
                    staged.append(line[3:].strip())
            return staged
        return []

    def get_log(self, count=50):
        """返回提交历史 [ {hash, message} ]"""
        r = self._run(['log', '--oneline', f'-n{count}', '--format=%h %s'])
        if r and r.returncode == 0:
            commits = []
            for line in r.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                parts = line.split(' ', 1)
                commits.append({
                    'hash': parts[0],
                    'message': parts[1] if len(parts) > 1 else '',
                })
            return commits
        return []

    # ── 操作 ──

    def stage_all(self):
        return self._run(['add', '.'])

    def stage_file(self, path):
        return self._run(['add', '--', path])

    def unstage_all(self):
        return self._run(['restore', '--staged', '.'])

    def unstage_file(self, path):
        return self._run(['restore', '--staged', '--', path])

    def commit(self, msg):
        """提交（通过 stdin 传中文消息，避免编码问题）"""
        try:
            return subprocess.run(
                ['git', '-c', 'core.quotepath=false', 'commit', '-F', '-'],
                cwd=self.working_dir,
                input=msg,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
            )
        except FileNotFoundError:
            return None

    def restore(self, commit_hash):
        """将工作区文件恢复到指定提交（不修改历史）"""
        return self._run(['restore', '--source', commit_hash, '.'])

    def init_repo(self):
        """初始化 Git 仓库（git init）"""
        return self._run(['init'])

    # ── 远程操作 ──

    def has_remote(self, name='origin'):
        r = self._run(['remote', 'get-url', name])
        return r is not None and r.returncode == 0

    def get_remote_url(self, name='origin'):
        r = self._run(['remote', 'get-url', name])
        return r.stdout.strip() if r and r.returncode == 0 else ''

    def set_remote(self, url, name='origin'):
        if self.has_remote(name):
            self._run(['remote', 'set-url', name, url])
        else:
            self._run(['remote', 'add', name, url])

    def push(self, branch='master'):
        """推送代码到远程"""
        try:
            return subprocess.run(
                ['git', '-c', 'core.quotepath=false', 'push', '-u', 'origin', branch],
                cwd=self.working_dir,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
            )
        except FileNotFoundError:
            return None


# ──────────────────────────────────────────────
# GUI 应用
# ──────────────────────────────────────────────

class GitHelperApp:
    """Git 助手主窗口"""

    # 状态对应的颜色和中文标签
    STATUS_CFG = {
        'tracked':   {'fg': '#000000', 'label': ''},
        'modified':  {'fg': '#E65100', 'label': '已修改'},
        'staged':    {'fg': '#1565C0', 'label': '已暂存'},
        'untracked': {'fg': '#2E7D32', 'label': '未跟踪'},
        'ignored':   {'fg': '#9E9E9E', 'label': '忽略'},
    }

    def __init__(self, root):
        self.root = root
        self.root.title("Git 助手")
        self.root.geometry("1050x720")
        self.root.minsize(850, 520)

        # DPI 感知（Windows）
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

        # 字体放大 50%
        self._setup_fonts()

        # 当前工作目录
        self.current_dir = os.getcwd()
        self.git = GitHelper(self.current_dir)

        self._build_ui()
        self.refresh()

    # ── UI 构建 ──

    def _build_ui(self):
        # ========== 顶部：地址栏 ==========
        top = ttk.Frame(self.root, padding=6)
        top.pack(fill=tk.X)

        ttk.Label(top, text="📂 路径:").pack(side=tk.LEFT)
        self.dir_var = tk.StringVar(value=self.current_dir)
        self.dir_entry = ttk.Entry(top, textvariable=self.dir_var)
        self.dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.dir_entry.bind('<Return>', lambda _: self._go_dir())

        ttk.Button(top, text="前往", width=6, command=self._go_dir).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(top, text="浏览", width=6, command=self._browse_dir).pack(side=tk.LEFT)

        # ========== 非仓库提示条（默认隐藏） ==========
        self.banner = ttk.Frame(self.root, padding=4)
        self.banner_lbl = ttk.Label(self.banner,
            text="⚠️  当前目录不是 Git 仓库",
            foreground='#E65100')
        self.banner_lbl.pack(side=tk.LEFT, padx=(0, 10))
        self.init_btn = ttk.Button(self.banner,
            text="🆕  新建 Git 仓库", command=self._init_repo)
        self.init_btn.pack(side=tk.LEFT)

        # ========== 中间：三区 (PanedWindow 可拖拽) ==========
        self.paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)

        # ── 工作区（树形目录） ──
        w_frame = ttk.LabelFrame(self.paned, text="📝 工作区", padding=2)
        self.work_tree = ttk.Treeview(w_frame, columns=('status',),
                                      show='tree', height=16, selectmode='browse')
        self.work_tree.column('status', width=80, minwidth=60, anchor='center')
        self.work_tree.pack(fill=tk.BOTH, expand=True)
        self._add_scrollbar(w_frame, self.work_tree)
        self.work_tree.bind('<Double-1>', self._on_work_dclick)
        self.paned.add(w_frame, weight=1)

        # ── 暂存区 ──
        s_frame = ttk.LabelFrame(self.paned, text="📦 暂存区", padding=2)
        self.stage_tree = ttk.Treeview(s_frame, columns=('file',),
                                       show='headings', height=16, selectmode='browse')
        self.stage_tree.heading('file', text='文件')
        self.stage_tree.column('file', width=220, minwidth=120)
        self.stage_tree.pack(fill=tk.BOTH, expand=True)
        self._add_scrollbar(s_frame, self.stage_tree)
        self.stage_tree.bind('<Double-1>', self._on_stage_dclick)
        self.paned.add(s_frame, weight=1)

        # ── 已提交 ──
        c_frame = ttk.LabelFrame(self.paned, text="✅ 已提交（历史）", padding=2)
        self.commit_tree = ttk.Treeview(c_frame, columns=('hash', 'message'),
                                        show='headings', height=16, selectmode='browse')
        self.commit_tree.heading('hash', text='提交ID')
        self.commit_tree.heading('message', text='提交说明')
        self.commit_tree.column('hash', width=90, minwidth=70)
        self.commit_tree.column('message', width=280, minwidth=150)
        self.commit_tree.pack(fill=tk.BOTH, expand=True)
        self._add_scrollbar(c_frame, self.commit_tree)
        self.paned.add(c_frame, weight=1)

        # ========== 底部：操作栏 ==========
        bottom = ttk.Frame(self.root, padding=6)
        bottom.pack(fill=tk.X)

        # 提交说明行
        msg_row = ttk.Frame(bottom)
        msg_row.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(msg_row, text="提交说明:").pack(side=tk.LEFT)
        self.msg_var = tk.StringVar()
        msg_entry = ttk.Entry(msg_row, textvariable=self.msg_var)
        msg_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        msg_entry.bind('<Return>', lambda _: self._commit())

        # 按钮行
        btn_row = ttk.Frame(bottom)
        btn_row.pack(fill=tk.X)

        ttk.Button(btn_row, text="📥 暂存所有", command=self._stage_all).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_row, text="↩️ 取消暂存", command=self._unstage_all).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_row, text="💾 提交", command=self._commit).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_row, text="⏪ 恢复到选中版本", command=self._restore).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Separator(btn_row, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=2)
        ttk.Button(btn_row, text="☁️  上传到 Gitee", command=self._upload_gitee).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_row, text="🔄 刷新", command=self.refresh).pack(side=tk.LEFT)

        # ========== 状态栏 ==========
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(self.root, textvariable=self.status_var,
                               relief=tk.SUNKEN, anchor=tk.W, padding=(5, 2))
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)


    @staticmethod
    def _add_scrollbar(parent, tree):
        sb = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=tree.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        tree.configure(yscrollcommand=sb.set)

    # ── 字体放大 ──

    def _setup_fonts(self):
        """全局字体翻倍（默认 10pt → 20pt）"""
        family = 'Microsoft YaHei UI'  # 微软雅黑，中文友好
        size = 18

        # ttk 全局字体
        style = ttk.Style()
        style.configure('.', font=(family, size))

        # Treeview 内容 + 表头
        style.configure('Treeview', font=(family, size - 1), rowheight=int(size * 2.8))
        style.configure('Treeview.Heading', font=(family, size))

        # tk 原生控件（Entry, Label 等）
        default_font = tkfont.nametofont('TkDefaultFont')
        default_font.configure(family=family, size=size)

        text_font = tkfont.nametofont('TkTextFont')
        text_font.configure(family=family, size=size)

        # 固定字体（如状态栏）
        fixed_font = tkfont.nametofont('TkFixedFont')
        fixed_font.configure(family=family, size=size - 1)

    # ── 目录切换 ──

    def _go_dir(self):
        path = self.dir_var.get().strip()
        if not path:
            return
        if not os.path.isdir(path):
            messagebox.showerror("错误", f"路径不存在:\n{path}")
            return
        self.current_dir = path
        self.git = GitHelper(path)
        self.refresh()

    def _browse_dir(self):
        path = filedialog.askdirectory()
        if path:
            self.dir_var.set(path)
            self._go_dir()

    # ── 刷新 ──

    def refresh(self):
        """刷新所有面板和状态栏"""
        # 先控制提示条显隐
        is_repo = self.git.is_git_repo()
        if is_repo:
            self.banner.pack_forget()
        else:
            self.banner.pack(fill=tk.X, before=self.paned, padx=6, pady=(0, 4))

        self._refresh_work()
        self._refresh_stage()
        self._refresh_commit()
        self._update_status()

    def _refresh_work(self):
        for i in self.work_tree.get_children():
            self.work_tree.delete(i)

        if not self.git.is_git_repo():
            return

        # 构建全量状态映射
        status_map = self._build_status_map()

        # 递归填充树
        self._populate_tree('', self.current_dir, status_map)

        # 颜色配置
        for key, cfg in self.STATUS_CFG.items():
            self.work_tree.tag_configure(key, foreground=cfg['fg'])

    def _build_status_map(self):
        """返回 {相对路径: 状态} 全量映射"""
        sm = {}

        # 已跟踪文件（默认 tracked）
        r = self.git._run(['ls-files'])
        if r and r.returncode == 0:
            for line in r.stdout.splitlines():
                f = line.strip()
                if f:
                    sm[f] = 'tracked'

        # porcelain 覆盖更具体状态
        r = self.git._run(['status', '--porcelain'])
        if r and r.returncode == 0:
            for line in r.stdout.splitlines():
                if not line.strip():
                    continue
                flags = line[:2]
                path = line[3:].strip()
                if flags == '??':
                    sm[path] = 'untracked'
                elif flags[0] not in (' ', '?', '!'):
                    sm[path] = 'staged'
                elif flags[1] != ' ':
                    sm[path] = 'modified'

        # 被忽略的文件
        r = self.git._run(['ls-files', '--others', '--ignored', '--exclude-standard'])
        if r and r.returncode == 0:
            for line in r.stdout.splitlines():
                f = line.strip()
                if f:
                    sm[f] = 'ignored'

        return sm

    def _populate_tree(self, parent_iid, dir_path, status_map):
        """递归填充目录树到 Treeview"""
        try:
            items = sorted(os.listdir(dir_path),
                           key=lambda x: (not os.path.isdir(os.path.join(dir_path, x)), x.lower()))
        except PermissionError:
            return

        for item in items:
            if item == '.git':
                continue
            full = os.path.join(dir_path, item)
            is_dir = os.path.isdir(full)
            rel = os.path.relpath(full, self.current_dir).replace('\\', '/')
            display = item + '/' if is_dir else item

            # 判定状态
            st = status_map.get(rel, 'untracked')
            if is_dir:
                if st == 'untracked':
                    # 检查目录下有无跟踪/忽略内容
                    for k in status_map:
                        if k.startswith(rel + '/'):
                            if status_map[k] in ('tracked', 'staged', 'modified'):
                                st = 'tracked'
                                break
                            elif status_map[k] == 'ignored':
                                st = 'ignored'
                # 完全忽略的目录不展开（如 node_modules）
                is_ignored_dir = (st == 'ignored')

            cfg = self.STATUS_CFG.get(st, self.STATUS_CFG['tracked'])

            if is_dir:
                node = self.work_tree.insert(parent_iid, tk.END,
                                             text=display, values=(cfg['label'],),
                                             tags=(st,), open=False)
                if not is_ignored_dir:
                    self._populate_tree(node, full, status_map)
            else:
                self.work_tree.insert(parent_iid, tk.END,
                                      text=display, values=(cfg['label'],),
                                      tags=(st,))

    def _refresh_stage(self):
        for i in self.stage_tree.get_children():
            self.stage_tree.delete(i)

        if not self.git.is_git_repo():
            return

        for path in self.git.get_staged_files():
            self.stage_tree.insert('', tk.END, values=(path,))

    def _refresh_commit(self):
        for i in self.commit_tree.get_children():
            self.commit_tree.delete(i)

        if not self.git.is_git_repo():
            return

        for c in self.git.get_log():
            self.commit_tree.insert('', tk.END, values=(c['hash'], c['message']))

    def _update_status(self):
        if not self.git.is_git_repo():
            self.status_var.set("⚠️ 当前目录不是 Git 仓库  —  点击上方「新建 Git 仓库」初始化")
            return

        parts = [f"🌿 {self.git.get_branch()}"]
        n_work = len(self.work_tree.get_children())
        n_stage = len(self.stage_tree.get_children())
        n_commit = len(self.commit_tree.get_children())

        # 递归统计工作区中各类文件数量
        def _count_tag(tag, items=None):
            if items is None:
                items = self.work_tree.get_children()
            total = 0
            for iid in items:
                # 只统计文件（没有子节点的项才是文件）
                if self.work_tree.tag_has(tag, iid) and not self.work_tree.get_children(iid):
                    total += 1
                total += _count_tag(tag, self.work_tree.get_children(iid))
            return total

        modified = _count_tag('modified')
        untracked = _count_tag('untracked')
        ignored = _count_tag('ignored')

        info = []
        if modified:
            info.append(f"📝 已修改 {modified}")
        if untracked:
            info.append(f"🆕 未跟踪 {untracked}")
        if n_stage:
            info.append(f"📦 已暂存 {n_stage}")
        if ignored:
            info.append(f"⬜ 忽略 {ignored}")

        self.status_var.set(" | ".join(parts + info) if info else " | ".join(parts + ["✓ 工作区干净"]))

    # ── 双击操作 ──

    def _on_work_dclick(self, event):
        sel = self.work_tree.selection()
        if not sel:
            return
        iid = sel[0]
        text = self.work_tree.item(iid, 'text')

        # 文件夹 → 展开/折叠
        children = self.work_tree.get_children(iid)
        if children:
            opened = self.work_tree.item(iid, 'open')
            self.work_tree.item(iid, open=not opened)
            return

        # 构建完整相对路径（沿树向上遍历）
        parts = []
        cur = iid
        while cur:
            t = self.work_tree.item(cur, 'text').rstrip('/')
            parts.append(t)
            cur = self.work_tree.parent(cur)
        rel_path = '/'.join(reversed(parts))

        full = os.path.join(self.current_dir, rel_path)
        if os.path.isdir(full):
            return  # 空目录，无操作

        # 双击文件 → 暂存
        r = self.git.stage_file(rel_path)
        self._toast(f"📥 已暂存: {rel_path}" if r and r.returncode == 0 else f"❌ 暂存失败")
        self.refresh()

    def _on_stage_dclick(self, event):
        sel = self.stage_tree.selection()
        if not sel:
            return
        vals = self.stage_tree.item(sel[0], 'values')
        if not vals:
            return
        path = vals[0]
        r = self.git.unstage_file(path)
        self._toast(f"↩️ 已取消暂存: {path}" if r and r.returncode == 0 else f"❌ 取消暂存失败")
        self.refresh()

    # ── 按钮操作 ──

    def _stage_all(self):
        if not self._check_repo():
            return
        r = self.git.stage_all()
        if r and r.returncode == 0:
            self._toast("📥 已暂存所有文件")
            self.refresh()
        else:
            self._toast(f"❌ {r.stderr.strip()}" if r else "❌ Git 未安装")

    def _unstage_all(self):
        if not self._check_repo():
            return
        r = self.git.unstage_all()
        if r and r.returncode == 0:
            self._toast("↩️ 已取消暂存全部")
            self.refresh()
        else:
            self._toast(f"❌ {r.stderr.strip()}" if r else "❌ Git 未安装")

    def _commit(self):
        if not self._check_repo():
            return
        msg = self.msg_var.get().strip()
        if not msg:
            messagebox.showwarning("提示", "请先填写提交说明")
            return
        if not self.git.get_staged_files():
            messagebox.showwarning("提示", "暂存区是空的，没有文件可以提交。\n请先「暂存所有」或双击文件添加到暂存区。")
            return

        r = self.git.commit(msg)
        if r and r.returncode == 0:
            self._toast(f"✅ 已提交: {msg}")
            self.msg_var.set('')
            self.refresh()
        else:
            err = r.stderr.strip() if r else "Git 未安装"
            messagebox.showerror("提交失败", err)

    def _restore(self):
        if not self._check_repo():
            return
        sel = self.commit_tree.selection()
        if not sel:
            messagebox.showwarning("提示", "请先在「已提交」列表中选中一个版本")
            return
        vals = self.commit_tree.item(sel[0], 'values')
        h, m = vals[0], vals[1]

        ok = messagebox.askyesno(
            "确认恢复",
            f"将工作区文件恢复到版本:\n  {h} {m}\n\n"
            "⚠️  当前未提交的修改将会丢失！\n确定继续？",
            icon='warning')
        if not ok:
            return

        r = self.git.restore(h)
        if r and r.returncode == 0:
            self._toast(f"⏪ 已恢复到 {h}")
            self.refresh()
        else:
            err = r.stderr.strip() if r else "Git 未安装"
            messagebox.showerror("恢复失败", err)

    # ── 辅助 ──

    def _check_repo(self):
        if not self.git.is_git_repo():
            messagebox.showwarning("警告", "当前目录不是 Git 仓库")
            return False
        return True

    def _toast(self, msg):
        """在状态栏显示消息"""
        self.status_var.set(msg)
        self.root.update_idletasks()

    # ── 初始化仓库 ──

    def _init_repo(self):
        ok = messagebox.askyesno(
            "新建 Git 仓库",
            f"将在以下目录初始化 Git 仓库：\n{self.current_dir}\n\n"
            "确定继续？",
            icon='question')
        if not ok:
            return
        r = self.git.init_repo()
        if r and r.returncode == 0:
            self._toast("✅ Git 仓库已创建")
            self.refresh()
        else:
            err = r.stderr.strip() if r else "Git 未安装"
            messagebox.showerror("初始化失败", err)

    # ── Gitee 上传 ──

    @staticmethod
    def _gitee_config_path():
        return os.path.join(os.path.expanduser('~'), '.git-helper-gitee.json')

    def _load_gitee_config(self):
        """加载 Gitee 全局配置（用户名 + 令牌）"""
        path = self._gitee_config_path()
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_gitee_config(self, username, token):
        path = self._gitee_config_path()
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({'username': username, 'token': token}, f)
        # 只有本用户可读写
        try:
            import stat
            os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
        except Exception:
            pass

    def _call_gitee_api(self, method, path, token, data=None):
        """调用 Gitee API v5，返回 (成功?, 数据或错误消息)"""
        import urllib.error
        url = f'https://gitee.com/api/v5{path}'
        if method == 'GET':
            url += f'?access_token={token}'
            req = urllib.request.Request(url)
        else:
            url += f'?access_token={token}'
            body = json.dumps(data).encode('utf-8') if data else b''
            req = urllib.request.Request(url, data=body, method=method)
            req.add_header('Content-Type', 'application/json')

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return True, json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            try:
                err = json.loads(e.read().decode('utf-8'))
                msg = err.get('message', str(e))
            except Exception:
                msg = str(e)
            return False, msg
        except Exception as e:
            return False, str(e)

    def _show_gitee_dialog(self):
        """弹出 Gitee 配置对话框"""
        dialog = tk.Toplevel(self.root)
        dialog.title("上传到 Gitee")
        dialog.geometry("520x430")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        frame = ttk.Frame(dialog, padding=16)
        frame.pack(fill=tk.BOTH, expand=True)

        # 仓库名
        ttk.Label(frame, text="仓库名称:").pack(anchor=tk.W)
        repo_default = os.path.basename(self.current_dir)
        repo_var = tk.StringVar(value=repo_default)
        ttk.Entry(frame, textvariable=repo_var).pack(fill=tk.X, pady=(2, 10))

        # 用户名
        ttk.Label(frame, text="Gitee 用户名:").pack(anchor=tk.W)
        user_var = tk.StringVar()
        ttk.Entry(frame, textvariable=user_var).pack(fill=tk.X, pady=(2, 10))

        # 令牌
        ttk.Label(frame, text="私人令牌:").pack(anchor=tk.W)
        token_var = tk.StringVar()
        ttk.Entry(frame, textvariable=token_var, show='*').pack(fill=tk.X, pady=(2, 10))

        # 令牌获取说明
        tip = ttk.LabelFrame(frame, text="📌 如何获取令牌", padding=8)
        tip.pack(fill=tk.X, pady=5)
        tip_text = (
            "1. 浏览器打开：gitee.com/profile/\n"
            "   personal_access_tokens\n"
            "2. 点「生成新令牌」\n"
            "3. 勾选 projects 权限，点提交\n"
            "4. 复制生成的令牌，粘贴到上面"
        )
        ttk.Label(tip, text=tip_text, foreground='#555',
                  font=('Microsoft YaHei UI', 11)).pack(anchor=tk.W)

        result_var = tk.StringVar()

        def do_upload():
            repo = repo_var.get().strip()
            user = user_var.get().strip()
            token = token_var.get().strip()
            if not repo or not user or not token:
                result_var.set("请填写所有字段")
                return
            _do_upload(repo, user, token, dialog)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(btn_frame, text="☁️  确认上传", command=do_upload).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btn_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT)
        ttk.Label(btn_frame, textvariable=result_var, foreground='red').pack(side=tk.LEFT, padx=(10, 0))

        dialog.wait_window()

    def _upload_gitee(self):
        """☁️ 上传到 Gitee 主流程"""
        if not self._check_repo():
            return

        # 1) 检查/获取配置
        cfg = self._load_gitee_config()
        username = cfg.get('username', '')
        token = cfg.get('token', '')

        if not username or not token:
            self._show_gitee_dialog()
            return  # 对话框内完成后会处理

        # 已有配置 → 直接上传
        repo_name = os.path.basename(self.current_dir)
        self._do_upload(repo_name, username, token)

    def _do_upload(self, repo_name, username, token, dialog=None):
        """执行上传流程"""
        self._toast("☁️  正在上传到 Gitee...")
        if dialog:
            # 保存配置
            self._save_gitee_config(username, token)

        # 2) 检查是否需要新建 remote
        need_push = self.git.has_remote('origin')

        if not need_push:
            # 检查 Gitee 上仓库是否存在
            self._toast("☁️  检查 Gitee 仓库...")
            ok, data = self._call_gitee_api(
                'GET', f'/repos/{username}/{repo_name}', token)

            if not ok:
                # 仓库不存在 → 创建
                self._toast("☁️  正在创建仓库...")
                ok, data = self._call_gitee_api('POST', '/user/repos', token, {
                    'name': repo_name,
                    'description': f'{repo_name} - Git 助手管理',
                    'private': False,
                    'auto_init': False,
                })
                if not ok:
                    msg = f"创建仓库失败: {data}"
                    self._toast(f"❌ {msg}")
                    if dialog:
                        messagebox.showerror("上传失败", msg, parent=dialog)
                    return

            # 设置 remote
            url = f'https://{username}:{token}@gitee.com/{username}/{repo_name}.git'
            self.git.set_remote(url, 'origin')

        # 3) 先提交未提交的修改
        staged = self.git.get_staged_files()
        if staged:
            self.git.commit("auto commit before push")

        # 4) 推送
        self._toast("☁️  正在推送代码...")
        r = self.git.push('master')
        if r and r.returncode == 0:
            self._toast(f"✅ 已上传到 Gitee: {username}/{repo_name}")
            # 清除 remote URL 中的令牌
            clean_url = f'https://gitee.com/{username}/{repo_name}.git'
            self.git.set_remote(clean_url, 'origin')
            if dialog:
                messagebox.showinfo("上传成功",
                    f"✅ 已上传到:\nhttps://gitee.com/{username}/{repo_name}",
                    parent=dialog)
                dialog.destroy()
            self.refresh()
        else:
            err = r.stderr.strip() if r else "推送失败"
            # 隐藏令牌信息（安全）
            err = err.replace(token, '***')
            self._toast("❌ 上传失败")
            if dialog:
                messagebox.showerror("上传失败", err, parent=dialog)
            else:
                messagebox.showerror("上传失败", err)


# ──────────────────────────────────────────────
# 入口
# ──────────────────────────────────────────────

def main():
    root = tk.Tk()
    GitHelperApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()

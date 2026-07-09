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
import re
import subprocess
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

    def remove_remote(self, name='origin'):
        """删除远程仓库地址"""
        return self._run(['remote', 'remove', name])

    def push(self, force=False):
        """推送代码到远程（自动使用当前分支）"""
        branch = self.get_branch()
        if not branch or branch == 'N/A':
            return None
        try:
            cmd = ['git', '-c', 'core.quotepath=false', 'push', '-u', 'origin', branch]
            if force:
                cmd.insert(2, '--force')
            return subprocess.run(
                cmd,
                cwd=self.working_dir,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
            )
        except FileNotFoundError:
            return None

    def pull(self, allow_unrelated=False):
        """拉取远程代码（自动使用当前分支）"""
        branch = self.get_branch()
        if not branch or branch == 'N/A':
            return None
        try:
            cmd = ['git', '-c', 'core.quotepath=false', 'pull', 'origin', branch]
            if allow_unrelated:
                cmd.insert(2, '--allow-unrelated-histories')
            return subprocess.run(
                cmd,
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
        ttk.Button(btn_row, text="🌐  Gitee", command=self._gitee_dialog).pack(side=tk.LEFT, padx=(0, 5))
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

    # ── Gitee 仓库管理 ──

    @staticmethod
    def _https_to_ssh(url):
        """将 HTTPS 远程地址自动转为 SSH 格式"""
        # 匹配 https://HOST/USER/REPO 或 https://HOST/USER/REPO.git
        m = re.match(r'https://([^/]+)/([^/]+)/([^/]+?)(\.git)?/?$', url)
        if m:
            host, user, repo, _ = m.groups()
            return f'git@{host}:{user}/{repo}.git'
        return url  # 不是 HTTPS 格式则原样返回

    def _check_ssh_connection(self, host='git@gitee.com'):
        """测试 SSH 能否连接到 Gitee，返回 (成功?, 消息)"""
        try:
            r = subprocess.run(
                ['ssh', '-T', '-o', 'ConnectTimeout=5',
                 '-o', 'BatchMode=yes', '-o', 'PasswordAuthentication=no', host],
                capture_output=True, text=True, timeout=10)
            # Gitee: auth 成功时 exit code=1（拒绝 shell），失败时 exit code=255
            output = (r.stderr or r.stdout or '').strip()
            if r.returncode != 255:
                return True, output if output else '已连接'
            return False, output if output else '认证失败'
        except FileNotFoundError:
            return False, "未找到 SSH 客户端"
        except subprocess.TimeoutExpired:
            return False, "连接超时"
        except Exception as e:
            return False, str(e)

    def _gitee_dialog(self):
        """打开 Gitee 仓库管理对话框"""
        if not self._check_repo():
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("🌐 Gitee 仓库管理")
        dialog.geometry("1040x680")
        dialog.minsize(600, 400)
        dialog.transient(self.root)
        dialog.grab_set()

        frame = ttk.Frame(dialog, padding=16)
        frame.pack(fill=tk.BOTH, expand=True)

        # === 状态区 ===
        status_frame = ttk.LabelFrame(frame, text="连接状态", padding=8)
        status_frame.pack(fill=tk.X)

        self._gitee_status = tk.StringVar(value="检查中...")
        self._gitee_status_lbl = tk.Label(status_frame, textvariable=self._gitee_status,
                  font=('Microsoft YaHei UI', 13), anchor=tk.W, justify=tk.LEFT)
        self._gitee_status_lbl.pack(fill=tk.X)

        ttk.Label(status_frame,
                  text=f"分支: {self.git.get_branch()}",
                  foreground='#555').pack(anchor=tk.W, pady=(2, 0))

        remote_url = self.git.get_remote_url('origin')
        if remote_url:
            # HTTPS → SSH 自动转换
            ssh_url = self._https_to_ssh(remote_url)
            if ssh_url != remote_url:
                self.git.set_remote(ssh_url, 'origin')
                remote_url = ssh_url
            ttk.Label(status_frame,
                      text=f"远程: {remote_url}",
                      foreground='#555', wraplength=460).pack(anchor=tk.W, pady=(2, 0))

        self._ssh_status_var = tk.StringVar()
        self._ssh_status_lbl = tk.Label(status_frame, textvariable=self._ssh_status_var,
                  fg='#888', anchor=tk.W, justify=tk.LEFT)
        self._ssh_status_lbl.pack(fill=tk.X, pady=(2, 0))

        # === 远程地址管理（始终显示） ===
        self._remote_frame = ttk.LabelFrame(frame, text="远程仓库地址 (SSH)", padding=8)
        self._remote_frame.pack(fill=tk.X, pady=(10, 0))

        entry_frame = ttk.Frame(self._remote_frame)
        entry_frame.pack(fill=tk.X)

        self._remote_url_var = tk.StringVar(value=remote_url)
        self._remote_entry = ttk.Entry(entry_frame, textvariable=self._remote_url_var)
        self._remote_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self._remote_err_var = tk.StringVar()

        hint_text = "示例: git@gitee.com:用户名/仓库名.git"
        if remote_url:
            hint_text = "修改地址后点击「更新」保存，或点击「删除」清空远程地址"
        ttk.Label(self._remote_frame,
                  text=hint_text,
                  foreground='#888', font=('', 11)).pack(anchor=tk.W, pady=(2, 0))

        btnf = ttk.Frame(self._remote_frame)
        btnf.pack(fill=tk.X, pady=(5, 0))

        def do_set_remote():
            url = self._remote_url_var.get().strip()
            if not url:
                self._remote_err_var.set("地址不能为空")
                return
            # HTTPS → SSH 自动转换
            ssh_url = self._https_to_ssh(url)
            if ssh_url != url:
                self._remote_err_var.set(f"🔄 已自动转为 SSH: {ssh_url}")
            self.git.set_remote(ssh_url, 'origin')
            self._remote_err_var.set("✅ 远程地址已更新")
            self._gitee_refresh(dialog)
            # 更新按钮状态
            has_remote = True
            self._toggle_remote_btns()

        def do_remove_remote():
            ok = messagebox.askyesno(
                "删除远程地址",
                "确定要删除远程仓库地址吗？\n删除后需要重新设置才能推送/拉取。",
                parent=dialog)
            if not ok:
                return
            r = self.git.remove_remote('origin')
            if r and r.returncode == 0:
                self._remote_url_var.set('')
                self._remote_err_var.set("✅ 远程地址已删除")
                self._ssh_ok = False
                self._gitee_refresh(dialog)
                self._toggle_remote_btns()
            else:
                self._remote_err_var.set("❌ 删除失败")

        def _toggle_remote_btns():
            has = self.git.has_remote('origin')
            self._set_remote_btn.config(text="🔗 更新地址" if has else "🔗 设置远程仓库")
            self._remove_remote_btn.config(state=tk.NORMAL if has else tk.DISABLED)
            if has:
                state = tk.NORMAL if self._ssh_ok else tk.DISABLED
                self._gitee_btn_pull.config(state=state)
                self._gitee_btn_push.config(state=state)
            else:
                self._gitee_btn_pull.config(state=tk.DISABLED)
                self._gitee_btn_push.config(state=tk.DISABLED)

        self._set_remote_btn = ttk.Button(btnf, text="🔗 设置远程仓库", command=do_set_remote)
        self._set_remote_btn.pack(side=tk.LEFT, padx=(0, 8))

        self._remove_remote_btn = ttk.Button(btnf, text="🗑️ 删除地址", command=do_remove_remote)
        self._remove_remote_btn.pack(side=tk.LEFT, padx=(0, 8))

        ttk.Label(btnf, textvariable=self._remote_err_var,
                  foreground='green').pack(side=tk.LEFT)

        # === 操作按钮 ===
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=(15, 0))

        self._gitee_btn_pull = ttk.Button(btn_frame, text="⬇️  拉取 (Pull)",
                                          command=lambda: self._gitee_pull(dialog))
        self._gitee_btn_pull.pack(side=tk.LEFT, padx=(0, 8))

        self._gitee_btn_push = ttk.Button(btn_frame, text="⬆️  推送 (Push)",
                                          command=lambda: self._gitee_push(dialog))
        self._gitee_btn_push.pack(side=tk.LEFT, padx=(0, 8))

        ttk.Button(btn_frame, text="🔄 刷新状态",
                   command=lambda: self._gitee_refresh(dialog)).pack(side=tk.LEFT, padx=(0, 8))

        self._gitee_result = tk.StringVar()
        self._gitee_result_lbl = tk.Label(frame, textvariable=self._gitee_result,
                  fg='#E65100', wraplength=460, anchor=tk.W, justify=tk.LEFT)
        self._gitee_result_lbl.pack(fill=tk.X, pady=(8, 0))

        # 检查 SSH 连接
        self._gitee_refresh(dialog)

        dialog.wait_window()

    @staticmethod
    def _set_color(label, text):
        """根据文本内容设置颜色"""
        if text.startswith('✅'):
            label.config(fg='#2E7D32')  # 绿
        elif text.startswith('❌'):
            label.config(fg='#D32F2F')  # 红
        elif text.startswith('⚠️'):
            label.config(fg='#E65100')  # 橙
        elif text.startswith('🔍'):
            label.config(fg='#1565C0')  # 蓝
        else:
            label.config(fg='#333333')

    def _gitee_refresh(self, dialog=None):
        """刷新 Gitee 对话框状态"""
        self._gitee_status.set("🔍 检查连接...")
        self._set_color(self._gitee_status_lbl, "🔍 检查连接...")

        # 检查 SSH
        ok, msg = self._check_ssh_connection()
        self._ssh_ok = ok
        if ok:
            user = ''
            for line in msg.splitlines():
                if 'Welcome' in line or 'Hello' in line:
                    user = line.strip()
                    break
            text = f"✅ SSH 已连接  {user}"
            self._ssh_status_var.set(text)
            self._set_color(self._ssh_status_lbl, text)
            self._gitee_status.set("✅ 已连接到 Gitee")
            self._set_color(self._gitee_status_lbl, "✅ 已连接到 Gitee")
        else:
            text = f"⚠️  SSH 未连接  ({msg[:40]})"
            self._ssh_status_var.set(text)
            self._set_color(self._ssh_status_lbl, text)
            if self.git.has_remote('origin'):
                t = "⚠️  已配置远程，但 SSH 未连接"
                self._gitee_status.set(t)
                self._set_color(self._gitee_status_lbl, t)
            else:
                t = "❌ 未配置远程仓库"
                self._gitee_status.set(t)
                self._set_color(self._gitee_status_lbl, t)

        # 启用/禁用按钮
        has_remote = self.git.has_remote('origin')
        connected = ok and has_remote
        state = tk.NORMAL if connected else tk.DISABLED
        if dialog:
            self._gitee_btn_pull.config(state=state)
            self._gitee_btn_push.config(state=state)

        # 同步远程管理区按钮和输入框
        if hasattr(self, '_set_remote_btn'):
            self._set_remote_btn.config(
                text="🔗 更新地址" if has_remote else "🔗 设置远程仓库")
        if hasattr(self, '_remove_remote_btn'):
            self._remove_remote_btn.config(
                state=tk.NORMAL if has_remote else tk.DISABLED)
        # 同步输入框中的地址
        current_url = self.git.get_remote_url('origin')
        if hasattr(self, '_remote_url_var'):
            self._remote_url_var.set(current_url)

    def _gitee_pull(self, dialog):
        """执行 git pull，以中文显示常见错误"""
        branch = self.git.get_branch()
        if not branch or branch == 'N/A':
            self._gitee_result.set("❌ 无法获取当前分支")
            self._set_color(self._gitee_result_lbl, "❌ 无法获取当前分支")
            return

        if not self.git.has_remote('origin'):
            self._gitee_result.set("❌ 未配置远程仓库地址")
            self._set_color(self._gitee_result_lbl, "❌ 未配置远程仓库地址")
            return

        self._gitee_result.set("⬇️  正在拉取远程更新...")
        self._set_color(self._gitee_result_lbl, "⬇️  正在拉取...")
        dialog.update()

        r = self.git.pull()
        if r and r.returncode == 0:
            self._gitee_result.set("✅ 拉取成功，本地已更新")
            self._set_color(self._gitee_result_lbl, "✅ 拉取成功")
            self.refresh()
            return

        if r is None:
            self._gitee_result.set("❌ Git 未安装或无法执行")
            self._set_color(self._gitee_result_lbl, "❌ Git 未安装")
            return

        err = r.stderr.strip()
        err_lower = err.lower()

        # ── 常见错误翻译 ──
        if 'unrelated histories' in err_lower:
            self._gitee_result.set("⚠️  本地和远程仓库没有共同的提交历史")
            self._set_color(self._gitee_result_lbl, "⚠️  历史不相关")

            choice = messagebox.askyesno(
                "本地和远程没有共同历史",
                "本地仓库和远程仓库的提交历史没有关联，无法直接合并。\n"
                "是否允许合并无关历史？\n\n"
                "✅ [是]  合并（推荐）\n"
                "❌ [否]  取消",
                parent=dialog)

            if choice:
                self._gitee_result.set("⬇️  正在合并无关历史...")
                dialog.update()
                r2 = self.git.pull(allow_unrelated=True)
                if r2 and r2.returncode == 0:
                    self._gitee_result.set("✅ 拉取成功（已合并无关历史）")
                    self._set_color(self._gitee_result_lbl, "✅ 拉取成功")
                    self.refresh()
                else:
                    err2 = r2.stderr.strip() if r2 else "拉取失败"
                    self._gitee_result.set("❌ 拉取失败")
                    messagebox.showerror("拉取失败", err2, parent=dialog)

        elif 'could not read' in err_lower or 'auth error' in err_lower \
                or 'access denied' in err_lower:
            self._gitee_result.set("❌ 认证失败，无权限读取远程仓库")
            self._set_color(self._gitee_result_lbl, "❌ 认证失败")
            remote_url = self.git.get_remote_url('origin')
            msg = (
                "无法读取远程仓库，可能原因：\n\n"
                "1️⃣  远程地址不正确\n"
                f"    当前: {remote_url}\n"
                "    在「远程仓库地址」区修改\n\n"
                "2️⃣  SSH 密钥未添加到 Gitee\n"
                "    去 https://gitee.com/profile/sshkeys 检查\n\n"
                "3️⃣  没有仓库的读取权限"
            )
            messagebox.showerror("认证失败", msg, parent=dialog)

        elif 'merge conflict' in err_lower or 'conflict' in err_lower:
            self._gitee_result.set("❌ 合并冲突，请手动解决后重试")
            self._set_color(self._gitee_result_lbl, "❌ 合并冲突")
            messagebox.showerror(
                "合并冲突",
                "拉取时产生合并冲突，需要手动解决：\n\n"
                "1. 打开冲突文件（Git 会在文件中标注冲突位置）\n"
                "2. 保留需要的代码，删除冲突标记\n"
                "3. 保存文件\n"
                "4. 在 Git 助手中「暂存所有」→「提交」\n\n"
                f"详细错误：\n{err[:400]}",
                parent=dialog)

        elif 'not a git repository' in err_lower:
            self._gitee_result.set("❌ 当前目录不是 Git 仓库")
            self._set_color(self._gitee_result_lbl, "❌ 不是 Git 仓库")

        elif 'could not resolve host' in err_lower or 'connection refused' in err_lower \
                or '连接失败' in err:
            self._gitee_result.set("❌ 网络连接失败，请检查网络")
            self._set_color(self._gitee_result_lbl, "❌ 网络错误")
            messagebox.showerror("网络错误", f"无法连接到远程仓库，请检查网络连接。\n\n{err[:300]}", parent=dialog)

        else:
            short_err = err[:500] if len(err) > 500 else err
            self._gitee_result.set("❌ 拉取失败")
            self._set_color(self._gitee_result_lbl, "❌ 拉取失败")
            messagebox.showerror("拉取失败", short_err, parent=dialog)

    def _gitee_push(self, dialog):
        """执行 git push，遇到常见错误自动给出解决建议"""
        branch = self.git.get_branch()
        if not branch or branch == 'N/A':
            self._gitee_result.set("❌ 无法获取当前分支")
            self._set_color(self._gitee_result_lbl, "❌ 无法获取当前分支")
            return

        if not self.git.has_remote('origin'):
            self._gitee_result.set("❌ 未配置远程仓库地址，请先在「远程仓库地址」区设置")
            self._set_color(self._gitee_result_lbl, "❌ 未配置远程仓库地址")
            return

        self._gitee_result.set("⬆️  正在推送...")
        self._set_color(self._gitee_result_lbl, "⬆️  正在推送...")
        dialog.update()

        r = self.git.push()
        if r and r.returncode == 0:
            self._gitee_result.set("✅ 推送成功")
            self._set_color(self._gitee_result_lbl, "✅ 推送成功")
            self.refresh()
            return

        if r is None:
            self._gitee_result.set("❌ Git 未安装或无法执行")
            self._set_color(self._gitee_result_lbl, "❌ Git 未安装")
            return

        err = r.stderr.strip()
        err_lower = err.lower()

        # ── 情况 1：没有共同历史（unrelated histories） ──
        if 'unrelated histories' in err_lower or 'fetch first' in err_lower:
            self._gitee_result.set("⚠️  远程仓库包含本地没有的提交")
            self._set_color(self._gitee_result_lbl, "⚠️  需要先同步远程")

            choice = messagebox.askyesnocancel(
                "远程有本地没有的提交",
                "远程仓库包含本地没有的内容。\n\n"
                "🔄 [是]    先拉取再推送（推荐）\n"
                "   - 远程已有的内容会合并到本地\n"
                "   - 不会丢失任何代码\n"
                "💪 [否]    强制覆盖远程\n"
                "   - 用本地内容替换远程\n"
                "   - 远程原有的提交会丢失\n"
                "❌ [取消]  什么都不做",
                parent=dialog)

            if choice is True:  # 拉取再推送
                self._gitee_result.set("⬇️  正在拉取远程内容...")
                self._set_color(self._gitee_result_lbl, "⬇️  正在拉取...")
                dialog.update()

                use_unrelated = 'unrelated histories' in err_lower
                pull_r = self.git.pull(allow_unrelated=use_unrelated)
                if pull_r and pull_r.returncode == 0:
                    self._gitee_result.set("⬆️  拉取完成，正在重新推送...")
                    dialog.update()
                    push2 = self.git.push()
                    if push2 and push2.returncode == 0:
                        self._gitee_result.set("✅ 推送成功（已自动拉取并合并）")
                        self._set_color(self._gitee_result_lbl, "✅ 推送成功")
                        self.refresh()
                    else:
                        err2 = push2.stderr.strip() if push2 else "推送失败"
                        self._gitee_result.set("❌ 拉取后推送仍失败")
                        messagebox.showerror("推送失败", err2, parent=dialog)
                else:
                    pull_err = pull_r.stderr.strip() if pull_r else "拉取失败"
                    self._gitee_result.set("❌ 拉取失败")
                    messagebox.showerror("拉取失败", pull_err, parent=dialog)

            elif choice is False:  # 强制推送
                ok = messagebox.askyesno(
                    "确认强制推送",
                    "⚠️  强制推送会覆盖远程仓库的内容！\n\n"
                    f"远程分支: origin/{branch}\n"
                    "确定要继续吗？",
                    icon='warning', parent=dialog)
                if ok:
                    self._gitee_result.set("💪  正在强制推送...")
                    dialog.update()
                    force_r = self.git.push(force=True)
                    if force_r and force_r.returncode == 0:
                        self._gitee_result.set("✅ 强制推送成功")
                        self._set_color(self._gitee_result_lbl, "✅ 强制推送成功")
                        self.refresh()
                    else:
                        err_f = force_r.stderr.strip() if force_r else "强制推送失败"
                        self._gitee_result.set("❌ 强制推送失败")
                        messagebox.showerror("强制推送失败", err_f, parent=dialog)

        # ── 情况 2：认证错误（SSH / 权限） ──
        elif 'auth error' in err_lower or 'access denied' in err_lower \
                or 'permission denied' in err_lower or 'could not read' in err_lower:
            self._gitee_result.set("❌ SSH 认证失败，请检查远程地址和 SSH 密钥")
            self._set_color(self._gitee_result_lbl, "❌ 认证失败")

            remote_url = self.git.get_remote_url('origin')
            msg = (
                "SSH 认证失败，可能原因：\n\n"
                "1️⃣  远程地址不正确\n"
                f"    当前: {remote_url}\n"
                "    修改：在「远程仓库地址」区填入正确的 SSH 地址\n\n"
                "2️⃣  SSH 密钥未添加到 Gitee\n"
                "    去 https://gitee.com/profile/sshkeys 检查\n\n"
                "3️⃣  密钥未加载到 ssh-agent\n"
                "    在终端执行: ssh-add ~/.ssh/id_ed25519\n\n"
                "4️⃣  没有仓库的写入权限"
            )
            messagebox.showerror("认证失败", msg, parent=dialog)

        # ── 情况 3：其他错误 ──
        else:
            self._gitee_result.set("❌ 推送失败")
            self._set_color(self._gitee_result_lbl, "❌ 推送失败")
            # 截断过长的错误消息
            short_err = err[:600] if len(err) > 600 else err
            messagebox.showerror("推送失败", short_err, parent=dialog)


# ──────────────────────────────────────────────
# 入口
# ──────────────────────────────────────────────

def main():
    root = tk.Tk()
    GitHelperApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()

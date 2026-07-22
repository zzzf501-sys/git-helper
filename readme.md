# Git 助手

可视化 Git 工具，通过图形界面完成日常 Git 操作。

## 使用

```
双击 run.bat → 地址栏贴入项目路径 → 回车
```

若未安装 Python，启动脚本会自动下载安装。

## 环境要求

- **Git** — 操作 Git 仓库必需
- **Python 3.8+** — 由启动脚本自动安装

## 功能

### 工作区
以目录树展示所有文件及其 Git 状态。双击文件可暂存，展开/收起文件夹查看内部文件。

### 暂存区
一键暂存所有或取消暂存。

### 已提交
查看提交历史，选中版本可一键回滚。

### 新建仓库
在非 Git 仓库目录下，自动提示一键初始化。

### 远程仓库管理（Gitee + GitHub）
统一管理 Gitee 和 GitHub 远程仓库，支持：
- 分别配置 Gitee / GitHub 的 SSH 远程地址
- 一键检测 SSH 连接状态
- 分别拉取 / 推送 / 强制推送
- **双推**：一条命令同时推送到 Gitee 和 GitHub

## 目录结构

```
git-helper/
├── run.bat              ← 启动入口
├── 启动Git助手.bat
├── readme.md
├── .gitignore
└── src/
    ├── git-helper.py
    └── git-tutorial.md
```

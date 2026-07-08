# Git 新手入门教程

> **目标读者**：第一次使用 Git 的开发者  
> **环境**：Windows + PowerShell  
> **版本**：Git 2.x+

---

## 目录

1. [什么是 Git？](#1-什么是-git)
2. [安装与配置](#2-安装与配置)
3. [创建第一个仓库](#3-创建第一个仓库)
4. [基本工作流程](#4-基本工作流程)
5. [分支操作](#5-分支操作)
6. [远程仓库（GitHub）](#6-远程仓库github)
7. [撤销与回滚](#7-撤销与回滚)
8. [常用技巧](#8-常用技巧)
9. [实战演练](#9-实战演练)

---

## 1. 什么是 Git？

Git 是一个**分布式版本控制系统**，可以帮你：

- 📸 **记录快照**：每次提交（commit）就像拍一张照片，随时可以回到过去
- 🌿 **并行开发**：用分支（branch）同时开发多个功能，互不干扰
- 🔄 **团队协作**：多人同时修改同一个项目，自动合并
- 🔙 **后悔药**：改错了可以轻松撤销

### 核心概念

| 概念 | 说明 | 类比 |
|------|------|------|
| **仓库 (Repository)** | 存放项目的地方 | 项目文件夹 |
| **提交 (Commit)** | 一次保存的快照 | 游戏存档 |
| **分支 (Branch)** | 独立的开发线 | 平行宇宙 |
| **暂存区 (Staging)** | 提交前的准备区 | 购物车 |
| **工作区 (Working Directory)** | 你正在编辑的文件 | 办公桌 |

---

## 2. 安装与配置

### 2.1 检查是否已安装

打开 PowerShell（或终端），输入：

```powershell
git --version
```

如果看到版本号（如 `git version 2.42.0`），说明已安装。

### 2.2 首次配置

装好 Git 后，先告诉 Git 你是谁——**每次提交都会记录这些信息**：

```powershell
git config --global user.name "你的名字"
git config --global user.email "你的邮箱@example.com"
```

> 💡 `--global` 表示全局生效，所有项目都用这个配置。不加 `--global` 则只对当前项目生效。

### 2.3 其他常用配置

```powershell
# 设置默认分支名为 main（而不是 master）
git config --global init.defaultBranch main

# 让 Git 记住密码（短期）
git config --global credential.helper cache

# 查看所有配置
git config --list
```

---

## 3. 创建第一个仓库

### 方式一：从零开始

```powershell
# 创建一个新文件夹
mkdir my-project
cd my-project

# 初始化 Git 仓库
git init
```

现在 `my-project` 里多了一个隐藏的 `.git` 文件夹，这就是 Git 的"数据库"。

### 方式二：克隆已有项目

```powershell
git clone https://github.com/用户名/仓库名.git
# 或使用 SSH（推荐）
git clone git@github.com:用户名/仓库名.git
```

---

## 4. 基本工作流程

Git 的工作流程只有三个步骤：

```
工作区（修改文件）→ 暂存区（标记要保存的）→ 仓库（保存快照）
```

### 4.1 第一步：创建或修改文件

创建一个 `hello.py`：

```python
print("Hello, Git!")
```

### 4.2 第二步：查看状态

```powershell
git status
```

会显示：
- 🟥 红色 = 未跟踪（新文件）或已修改但未暂存
- 🟩 绿色 = 已暂存（在暂存区）

### 4.3 第三步：添加到暂存区

```powershell
# 添加单个文件
git add hello.py

# 添加所有文件（谨慎使用，看清再提交）
git add .

# 交互式添加（只添加部分修改）
git add -p
```

### 4.4 第四步：提交（创建快照）

```powershell
git commit -m "feat: 添加 hello.py"
```

> ⚠️ **提交信息规范**：用简洁的英文或中文，说明"做了什么"而不是"做了什么修改"
> - `feat: 添加用户登录功能`
> - `fix: 修复内存泄漏`
> - `docs: 更新 README`

### 4.5 查看历史

```powershell
# 查看提交日志
git log

# 简洁模式（一行一个提交）
git log --oneline

# 图形化查看分支
git log --oneline --graph --all

# 查看文件级别的修改历史
git log --oneline -- hello.py

# 查看某个具体的修改内容
git show 提交ID
```

### 完整流程示例

```powershell
# 1. 初始化
git init

# 2. 创建 README
echo "# My Project" > README.md
git add README.md
git commit -m "docs: 初始化项目"

# 3. 写代码
echo 'print("hello")' > main.py
git add main.py
git commit -m "feat: 添加 main.py"

# 4. 查看历史
git log --oneline
# 输出：
# a1b2c3d feat: 添加 main.py
# e4f5g6h docs: 初始化项目
```

---

## 5. 分支操作

分支是 Git 最强大的功能，让你可以**同时开发多个功能**而不互相影响。

### 5.1 核心命令

```powershell
# 查看分支（* 表示当前所在分支）
git branch

# 创建新分支
git branch feature-login

# 切换到另一个分支
git checkout feature-login
# 或（新版 Git）
git switch feature-login

# 创建并切换（一步到位）
git checkout -b feature-login
# 或
git switch -c feature-login

# 删除分支
git branch -d feature-login        # 安全删除（检查是否已合并）
git branch -D feature-login        # 强制删除（不检查）
```

### 5.2 合并分支

```powershell
# 先切换到目标分支（你要吸收别人的分支）
git checkout main

# 把 feature-login 合并进来
git merge feature-login
```

### 5.3 合并冲突处理

当两个分支修改了同一个文件的同一行时，Git 不知道谁是对的，需要你手动解决。

冲突标记长这样：

```python
<<<<<<< HEAD
print("这是 main 分支的版本")
=======
print("这是 feature 分支的版本")
>>>>>>> feature-login
```

**解决步骤**：

1. 打开冲突文件
2. 删除 `<<<<<<<`、`=======`、`>>>>>>>` 标记
3. 保留正确的代码
4. 保存文件
5. 执行 `git add` 和 `git commit`

### 5.4 分支策略（团队推荐）

```
main        ●─────●──────────●──────────────●
                \            /              /
develop         ●──●──●────●              /
                    \                    /
feature-login      ●──●──●──────────────
```

- **main**：生产分支，只放稳定版本
- **develop**：开发主分支
- **feature-xxx**：功能分支，从 develop 分出，完成后合并回去

---

## 6. 远程仓库（GitHub）

### 6.1 关联远程仓库

```powershell
# 添加远程仓库
git remote add origin https://github.com/你的用户名/仓库名.git

# 查看远程仓库
git remote -v
```

### 6.2 推送代码到远程

```powershell
# 第一次推送（建立关联）
git push -u origin main

# 后续推送（-u 只需第一次）
git push
```

### 6.3 拉取远程更新

```powershell
# 拉取并自动合并（最常用）
git pull

# 拉取但不合并（先看看改了啥）
git fetch

# 比较本地和远程
git log origin/main..HEAD
```

### 6.4 完整协作流程

```powershell
# 1. 克隆项目
git clone git@github.com:团队/项目.git
cd 项目

# 2. 创建功能分支
git checkout -b feature-xxx

# 3. 开发... 提交...
git add .
git commit -m "feat: 完成 xxx 功能"
git add .
git commit -m "fix: 修复 xxx bug"

# 4. 同步远程最新代码
git fetch origin
git rebase origin/main

# 5. 推送分支
git push origin feature-xxx

# 6. 在 GitHub 上创建 Pull Request
#    然后等待审核...
```

---

## 7. 撤销与回滚

### 7.1 工作区的修改（还没 git add）

```powershell
# 撤销对某个文件的修改（回到上次提交的状态）
git checkout -- 文件名
# 或
git restore 文件名
```

### 7.2 暂存区的修改（已经 git add，还没 commit）

```powershell
# 从暂存区移除（但保留工作区的修改）
git restore --staged 文件名

# 或者旧式写法
git reset HEAD 文件名
```

### 7.3 已经提交了（git commit）

```powershell
# 修改最后一次提交（还没推送）
git commit --amend -m "新的提交信息"

# 撤销最近一次提交，保留修改内容
git reset --soft HEAD~1

# 撤销最近一次提交，丢弃修改内容（⚠️危险！）
git reset --hard HEAD~1

# 恢复到某个历史版本
git reset --hard 提交ID
```

### 7.4 已经推送了（git push）

```powershell
# ⚠️ 永远不要强制推送到共享分支（main/master）！
# 如果确认只有你自己在用这个分支：
git reset --hard 提交ID
git push --force-with-lease   # 比 --force 更安全
```

### 7.5 后悔药大汇总

| 场景 | 命令 | 安全等级 |
|------|------|----------|
| 还没 add | `git restore 文件` | ✅ 非常安全 |
| 已经 add，还没 commit | `git restore --staged 文件` | ✅ 非常安全 |
| 已经 commit，还没 push | `git reset --soft HEAD~1` | ✅ 安全 |
| 已经 commit，已经 push | `git revert 提交ID` ✅ **推荐** | ✅ 安全 |
| 已经 commit，已经 push | `git reset --hard + push --force-with-lease` | ⚠️ 危险 |

> **黄金法则**：如果别人可能已经拉了你的代码，用 `git revert`（创建反向提交），不要用 `git reset`（改写历史）。

```powershell
# revert 示例：创建一个新的提交来抵消旧的提交
git revert 提交ID
# 这会创建一个"撤销 XX 提交"的新提交，不影响历史
```

---

## 8. 常用技巧

### 8.1 .gitignore——忽略不需要的文件

创建 `.gitignore` 文件，写入不需要 Git 跟踪的文件模式：

```
# 编译产物
*.obj
*.exe
build/

# IDE 配置
.idea/
.vscode/

# 临时文件
*.log
*.tmp

# 环境配置
.env
*.env.local
```

> 推荐工具：https://www.toptal.com/developers/gitignore

### 8.2 查看修改内容

```powershell
# 文件级别的详细对比
git diff

# 暂存区和上次提交的对比
git diff --staged

# 两个提交之间的差异
git diff 提交ID1 提交ID2

# 只看某个文件的变化
git diff -- 文件名
```

### 8.3 储藏（Stash）——临时保存正在做的事

```powershell
# 临时保存当前工作（工作区变干净）
git stash

# 查看储藏列表
git stash list

# 恢复最近的储藏
git stash pop

# 恢复但不删除储藏
git stash apply

# 带名字的储藏（推荐）
git stash push -m "WIP: 正在改登录bug"
git stash list
# stash@{0}: On main: WIP: 正在改登录bug
```

### 8.4 别名——偷懒必备

```powershell
git config --global alias.st status
git config --global alias.co checkout
git config --global alias.br branch
git config --global alias.ci commit
git config --global alias.lg "log --oneline --graph --all"

# 之后就可以用
git st    # 代替 git status
git co    # 代替 git checkout
git lg    # 查看漂亮的分支图
```

### 8.5 查看本次改动里谁写了哪一行

```powershell
git blame 文件名
```

---

## 9. 实战演练

### 场景：从零开始做一个单片机项目

```powershell
# ========== 第1天：初始化项目 ==========

# 创建项目
mkdir pendulumn-controller
cd pendulumn-controller

# 初始化 Git
git init

# 创建 README
echo "# 倒立摆控制器" > README.md
git add README.md
git commit -m "docs: 初始化项目，添加 README"

# 创建 .gitignore
echo "build/" > .gitignore
echo "*.o" >> .gitignore
echo "*.hex" >> .gitignore
echo ".vscode/" >> .gitignore
git add .gitignore
git commit -m "chore: 添加 .gitignore"


# ========== 第2天：开发基本功能 ==========

# 在 main 分支直接开发
echo '#include "main.h"' > main.c
git add main.c
git commit -m "feat: 添加主程序框架"

# 发现忘记加头文件了...
echo "#ifndef MAIN_H" > main.h
echo "#define MAIN_H" >> main.h
echo "void init(void);" >> main.h
echo "#endif" >> main.h
git add main.h
git commit -m "feat: 添加 main.h 头文件"


# ========== 第3天：开发新功能 ==========

# 创建功能分支
git checkout -b feature-oled-driver

# 在分支上开发
echo "// OLED 驱动" > oled.c
git add oled.c
git commit -m "feat: 添加 OLED 驱动框架"

echo "#ifndef OLED_H" > oled.h
echo "#define OLED_H" >> oled.h
echo "void OLED_Init(void);" >> oled.h
echo "void OLED_ShowString(char *str);" >> oled.h
echo "#endif" >> oled.h
git add oled.h
git commit -m "feat: 添加 OLED 头文件"

# 切回 main 合并
git checkout main
git merge feature-oled-driver
git branch -d feature-oled-driver


# ========== 第4天：出 bug 了... ==========

# 发现 OLED 显示有问题，回退到上一个版本
git log --oneline
# a1b2c3d feat: 添加 OLED 头文件
# d4e5f6g feat: 添加 OLED 驱动框架
# g7h8i9j chore: 添加 .gitignore

# 用 revert 安全回退（已推送时）
git revert d4e5f6g
# 这会创建一个新的提交来撤销 OLED 驱动框架的改动
git commit -m "revert: 回退 OLED 驱动框架（显示异常）"


# ========== 第5天：提交到远程 ==========

# 在 GitHub 创建好仓库后
git remote add origin git@github.com:你的名字/pendulumn-controller.git
git push -u origin main


# ========== 日常开发四步曲 ==========
git pull                    # 1. 拉取最新
git checkout -b fix-bug     # 2. 创建分支
# ... 修改代码 ...
git add .
git commit -m "fix: 修复 xxx"
git push origin fix-bug     # 3. 推送
# 在 GitHub 创建 PR，审核合并
git checkout main
git pull                    # 4. 更新本地 main
git branch -d fix-bug       # 清理分支
```

---

## 附：速查表

```powershell
# ┌─────────────────────────────────────────────┬──────────────────────────────┐
# │               我要做什么                     │         用什么命令            │
# ├─────────────────────────────────────────────┼──────────────────────────────┤
# │ 查看当前状态                                │ git status                   │
# │ 添加文件到暂存区                            │ git add 文件名               │
# │ 提交                                        │ git commit -m "信息"         │
# │ 查看提交历史                                │ git log --oneline            │
# │ 创建并切换到新分支                          │ git checkout -b 分支名       │
# │ 切换分支                                    │ git switch 分支名            │
# │ 合并分支                                    │ git merge 分支名             │
# │ 推送代码                                    │ git push                     │
# │ 拉取代码                                    │ git pull                     │
# │ 撤销工作区修改                              │ git restore 文件名           │
# │ 撤销暂存                                    │ git restore --staged 文件名  │
# │ 撤销提交（保留修改）                        │ git reset --soft HEAD~1      │
# │ 撤销提交（丢弃修改）⚠️                      │ git reset --hard HEAD~1      │
# │ 安全撤销已推送的提交                        │ git revert 提交ID            │
# │ 临时藏起当前工作                            │ git stash                    │
# │ 查看修改内容                                │ git diff                     │
# └─────────────────────────────────────────────┴──────────────────────────────┘
```

---

> **最后一条建议**：**多 commit，少焦虑**。频繁提交（每完成一个小功能就提交一次）不会出错，只会让你有更多"存档点"。一个好的 Git 习惯比任何高级功能都重要。

# 安装说明 / Installation

[English README](README.md) · [中文 README](README.zh-CN.md)

整个 `project-cognitive-cache` 文件夹就是一个完整 Skill。不要只复制 `SKILL.md`，因为指纹脚本和缓存格式说明也是运行所需部分。

## Codex

复制到个人 Skill 目录：

```text
~/.codex/skills/project-cognitive-cache/
```

也可以放入项目级 Skill 目录（如果当前 Codex 环境支持项目级自动发现）。重新启动会话或刷新 Skill 列表后，使用 `$project-cognitive-cache` 显式调用，或让它在“继续学习/解释已有项目”时自动触发。

## Claude Code

复制到：

```text
~/.claude/skills/project-cognitive-cache/
```

## 其他支持 Agent Skills 的 AI

把整个文件夹放入该产品声明的 skills 目录，并确保入口文件仍名为 `SKILL.md`。如果产品不支持 `agents/openai.yaml`，可忽略该文件；核心逻辑仍由 `SKILL.md`、`scripts/` 和 `references/` 提供。

## 使用前提

- Python 3.9 或更高版本；仅使用标准库。
- Git 项目需要系统已安装 Git；非 Git 文件夹会自动使用文件哈希模式。
- 首次项目导览保持只读。只有用户明确同意后，Skill 才创建 `.learn-by-building/cache/`。
- 缓存默认只保存在本地，不提交 Git。

安装后可运行：

```bash
python scripts/project_cache.py --help
python -m unittest discover -s tests -v
```

## 从 GitHub 安装

Codex：

```bash
git clone https://github.com/nokeys-one/project-cognitive-cache.git \
  ~/.codex/skills/project-cognitive-cache
```

Claude Code：

```bash
git clone https://github.com/nokeys-one/project-cognitive-cache.git \
  ~/.claude/skills/project-cognitive-cache
```

更新时进入该目录运行 `git pull --ff-only`。如果目标 AI 使用不同的 Skill 目录，以该产品的文档为准。

## English summary

Install the complete repository—not only `SKILL.md`—because the fingerprint helper and cache-format reference are runtime components. Python 3.9+ is required; Git is optional. The first onboarding remains read-only, and `.learn-by-building/cache/` is created only after explicit user consent. The cache is local and uncommitted by default.

# Project Cognitive Cache（项目认知缓存）

[English](README.md) · [安装说明](INSTALL.md) · [原项目致谢](ACKNOWLEDGMENTS.md)

[![Tests](https://github.com/nokeys-one/project-cognitive-cache/actions/workflows/test.yml/badge.svg)](https://github.com/nokeys-one/project-cognitive-cache/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)

一个节省 Token 的 Agent Skill：在继续学习、讲解或审查已有代码项目时，避免反复读取整个仓库。

Project Cognitive Cache 会把已经验证过的项目认知保存成短小的本地摘要；每次复用前先执行低成本指纹检查，只在仓库确实发生变化时读取受影响的文件。缓存只用于导航，当前源码始终是事实依据。

## 为什么需要它

大模型在不同会话中处理同一个仓库时，常常重复支付理解项目结构、入口、测试和模块边界的上下文成本。本 Skill 把两种记忆分开：

- 学习进度：用户已经学到了什么；
- 项目认知：此前已经验证了项目的哪些事实。

第二层会持久保存，但有严格大小上限；它默认不提交 Git，并通过确定性指纹判断是否失效。

## 核心特性

- **先授权再写入：** 首次项目导览保持只读，得到用户明确同意后才创建缓存。
- **快速新鲜度检查：** Git 项目使用 `HEAD`、工作区路径和轻量哈希；普通文件夹使用文件清单和哈希。
- **增量读取：** 项目未变化时只复用短总览；项目变化时只返回 `changed_paths`，引导模型聚焦受影响区域。
- **分层硬上限：** 总览和模块摘要都有固定预算，并按需加载，缓存不会无限膨胀。
- **默认仅本地：** Git 项目通过 `.git/info/exclude` 忽略 `.learn-by-building/cache/`，不会污染仓库提交。
- **轻量可移植：** 辅助脚本仅使用 Python 标准库，同时支持 Git 与非 Git 项目。

## 工作流程

1. 首次执行范围受控、完全只读的项目导览。
2. 导览结束后询问一次是否允许建立本地缓存。
3. 在摘要与已检查源码一致后记录项目指纹。
4. 后续会话先检查指纹，再决定需要读取哪些内容。
5. 缓存新鲜时复用摘要；发现变化时只检查并更新受影响部分。

模型每轮先读取短小的 `overview.md`，只有当前问题确实需要时才加载模块摘要或源码。机器使用的指纹由脚本处理，不需要放进模型上下文。

## 安装

### Codex

```bash
git clone https://github.com/nokeys-one/project-cognitive-cache.git \
  ~/.codex/skills/project-cognitive-cache
```

### Claude Code

```bash
git clone https://github.com/nokeys-one/project-cognitive-cache.git \
  ~/.claude/skills/project-cognitive-cache
```

其他兼容 Agent Skills 的产品，请把整个仓库复制到其 skills 目录，并保持 `SKILL.md`、`scripts/` 与 `references/` 在一起。更多说明见 [INSTALL.md](INSTALL.md)。

## 使用

在学习、讲解、继续处理或审查现有项目时调用 `$project-cognitive-cache`。首次使用时，Skill 会先只读检查项目，随后询问是否允许创建本地缓存。

也可以直接检查辅助工具：

```bash
python scripts/project_cache.py consent --root /path/to/project
python scripts/project_cache.py init --root /path/to/project
python scripts/project_cache.py capture --root /path/to/project
python scripts/project_cache.py status --root /path/to/project
python scripts/project_cache.py validate --root /path/to/project
```

在用户尚未明确授权时，不应替用户执行 `init`。

## 缓存结构

```text
.learn-by-building/cache/
├── consent.json
├── fingerprint.json
├── overview.md
└── modules/
    └── <module>.md
```

摘要格式和更新规则见 [references/cache-format.md](references/cache-format.md)。

## 环境要求与测试

- Python 3.9 或更高版本
- Git 感知模式需要系统安装 Git；没有 Git 时自动降级为普通文件夹模式
- 无第三方 Python 依赖

运行测试：

```bash
python -m unittest discover -s tests -v
```

面向 AI 行为的验证场景记录在 [tests/behavioral-scenarios.md](tests/behavioral-scenarios.md)。

## 隐私与安全

缓存只应保存简洁的架构摘要、路径、置信度和待确认问题，不应保存密码、令牌、大段源码或个人数据。删除 `.learn-by-building/cache/` 即可清除派生缓存；未来可以在重新授权后重建。

## 原项目与作者致谢

本项目受到 [chaojiwudibing](https://github.com/chaojiwudibing) 创建的 [learn-by-building](https://github.com/chaojiwudibing/learn-by-building) 启发。原项目提供了“AI 在完成真实项目的同时帮助用户学习”的 Agent Skill 语境，本项目在此基础上独立设计了面向 Token 成本的项目认知缓存机制。

Project Cognitive Cache 不是原项目的官方版本，也不代表原作者。完整的来源说明与边界见 [ACKNOWLEDGMENTS.md](ACKNOWLEDGMENTS.md)。

## 许可证

Project Cognitive Cache 采用 [MIT License](LICENSE) 发布。


# Project Cognitive Cache

[简体中文](README.zh-CN.md) · [Installation](INSTALL.md) · [Attribution](ACKNOWLEDGMENTS.md)

[![Tests](https://github.com/nokeys-one/project-cognitive-cache/actions/workflows/test.yml/badge.svg)](https://github.com/nokeys-one/project-cognitive-cache/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)

A token-efficient Agent Skill for resuming work on existing codebases without repeatedly reading the whole repository.

Project Cognitive Cache stores a small, local summary of verified project knowledge, checks a cheap fingerprint before every reuse, and reads only the files affected by real changes. The cache is a navigation aid; current source code remains the authority.

## Why it exists

Large language models can spend the same context budget repeatedly rediscovering a repository's structure, entrypoints, tests, and module boundaries. This Skill separates two kinds of memory:

- learning progress: what the user has learned;
- project cognition: what has already been verified about the repository.

The second layer is persistent, bounded, locally ignored by Git, and invalidated by deterministic fingerprints.

## Key properties

- **Consent first:** the first project onboarding stays read-only; cache files are created only after explicit approval.
- **Fast freshness checks:** Git projects use `HEAD`, working-tree paths, and lightweight content hashes; ordinary folders use a file manifest and hashes.
- **Incremental reads:** unchanged projects reuse a short overview; changed projects expose only `changed_paths` for focused inspection.
- **Hard context limits:** the overview and module summaries have fixed size budgets and are loaded on demand.
- **Local by default:** Git repositories exclude `.learn-by-building/cache/` through `.git/info/exclude`, so cache state is not committed.
- **Portable:** the helper uses only the Python standard library and supports Git and non-Git projects.

## How it works

1. Perform a bounded, read-only onboarding pass.
2. Ask once for permission to create a local project cache.
3. Record a fingerprint after summaries match the inspected source.
4. On later sessions, check the fingerprint before reading project content.
5. Reuse summaries when fresh; inspect and refresh only affected areas when changed.

The model reads a short `overview.md` first and loads module summaries or source only when the current question requires them. The machine-readable fingerprint is processed by the helper script and does not need to enter model context.

## Install

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

For other Agent Skills-compatible products, copy the complete repository into the product's skills directory. Keep `SKILL.md`, `scripts/`, and `references/` together. See [INSTALL.md](INSTALL.md) for details.

## Use

Invoke `$project-cognitive-cache` while learning, explaining, resuming, or auditing an existing project. On first use, the Skill will inspect the project without writing and then ask for permission to create the local cache.

The deterministic helper can also be exercised directly:

```bash
python scripts/project_cache.py consent --root /path/to/project
python scripts/project_cache.py init --root /path/to/project
python scripts/project_cache.py capture --root /path/to/project
python scripts/project_cache.py status --root /path/to/project
python scripts/project_cache.py validate --root /path/to/project
```

Do not run `init` on behalf of a user until they have explicitly approved cache creation.

## Cache layout

```text
.learn-by-building/cache/
├── consent.json
├── fingerprint.json
├── overview.md
└── modules/
    └── <module>.md
```

See [references/cache-format.md](references/cache-format.md) for the summary schema and update rules.

## Requirements and testing

- Python 3.9 or newer
- Git available for Git-aware mode; otherwise the helper falls back to plain-folder mode
- No third-party Python packages

Run the test suite with:

```bash
python -m unittest discover -s tests -v
```

Behavioral evaluation prompts are documented in [tests/behavioral-scenarios.md](tests/behavioral-scenarios.md).

## Privacy and safety

The cache must contain concise architectural summaries, paths, confidence labels, and unresolved questions—not secrets, credentials, raw source dumps, or personal data. Delete `.learn-by-building/cache/` at any time to remove the derived cache; it can be rebuilt later with fresh consent.

## Attribution

This independent project was inspired by [learn-by-building](https://github.com/chaojiwudibing/learn-by-building), created by [chaojiwudibing](https://github.com/chaojiwudibing). That original project introduced the learning-oriented Agent Skill context from which this token-efficiency extension was designed.

Project Cognitive Cache is not an official release of, or affiliated with, the original project. See [ACKNOWLEDGMENTS.md](ACKNOWLEDGMENTS.md) for the full attribution and scope distinction.

## License

Project Cognitive Cache is released under the [MIT License](LICENSE).


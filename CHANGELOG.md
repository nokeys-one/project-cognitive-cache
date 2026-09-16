# Changelog

All notable changes to this project are documented here.

## 1.0.1 - 2026-09-16

- Prevented symlink-based cache writes and restricted manifests to the project cache directory.
- Bound consent to the canonical project root and rejected consent committed to Git.
- Detected Git paths hidden by `assume-unchanged` and `skip-worktree`.
- Stopped ignoring source under generic `vendor`, `target`, `build`, and `dist` directories in plain-folder mode.
- Avoided opening FIFOs and other special files, and supported non-UTF-8 POSIX filenames.
- Forced a rebuild when Git cannot produce an exact historical diff.
- Added UTF-8 byte ceilings, package checks, and security regression coverage.
- Upgraded machine-state schema to version 2; version-1 cache records must be recreated after approval.

## 1.0.0 - 2026-09-15

- Added the `project-cognitive-cache` Agent Skill.
- Added consent-gated local cache initialization.
- Added Git and non-Git fingerprint modes.
- Added incremental changed-path reporting and layered summary limits.
- Added unit tests, behavioral validation scenarios, bilingual documentation, attribution, and CI.

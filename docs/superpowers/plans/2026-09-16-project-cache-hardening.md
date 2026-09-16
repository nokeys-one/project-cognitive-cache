# Project Cache Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden the local project-cache helper against untrusted repository content and make freshness checks fail closed.

**Architecture:** Keep the single standard-library CLI, but separate filesystem safety, consent validation, and fingerprint comparison into explicit helpers. Upgrade persisted fingerprints to schema version 2 and prove every reproduced failure with subprocess-level regression tests.

**Tech Stack:** Python 3.9+ standard library, Git CLI, `unittest`, GitHub Actions.

---

### Task 1: Add security regression tests

**Files:**
- Modify: `tests/test_project_cache.py`
- Create: `tests/test_skill_package.py`

- [x] Add subprocess tests for symlink overwrite rejection, tracked/root-mismatched consent, generic source directories, Git index flags, special files, non-UTF-8 paths, Unicode byte limits, subdirectory validation, failed Git diffs, and out-of-cache manifests.
- [x] Add package tests for required `SKILL.md` frontmatter, `agents/openai.yaml`, and local README links.
- [x] Run `python -m unittest discover -s tests -v` and verify the new regression tests fail against the current implementation.

### Task 2: Harden filesystem writes and consent

**Files:**
- Modify: `scripts/project_cache.py`
- Test: `tests/test_project_cache.py`

- [x] Add a structured `CacheSafetyError` path and validate that generated paths remain in a non-symlinked project cache.
- [x] Replace the predictable `.tmp` write with `tempfile.mkstemp`, private permissions, and `os.replace`.
- [x] Bind consent to the canonical root, reject tracked consent in Git projects, and report a machine-readable denial reason.
- [x] Run the focused safety and consent tests and verify they pass.

### Task 3: Make fingerprints fail closed

**Files:**
- Modify: `scripts/project_cache.py`
- Test: `tests/test_project_cache.py`

- [x] Upgrade the schema to version 2 and reduce plain-mode ignores to explicit dependency/cache directories.
- [x] Hash Git `assume-unchanged` and `skip-worktree` paths explicitly.
- [x] Represent FIFOs, sockets, and devices without opening them; decode unusual Git paths with `surrogateescape`.
- [x] Mark failed historical diffs as requiring a rebuild.
- [x] Run the focused Git, plain-folder, special-file, and filename tests and verify they pass.

### Task 4: Strengthen validation and package checks

**Files:**
- Modify: `scripts/project_cache.py`
- Modify: `.github/workflows/test.yml`
- Test: `tests/test_project_cache.py`
- Test: `tests/test_skill_package.py`

- [x] Add absolute UTF-8 byte limits and canonicalize validation roots.
- [x] Compile all scripts and tests in CI, enable manual dispatch, and continue running Python 3.9 and 3.12.
- [x] Run `python -m compileall -q scripts tests` and `python -m unittest discover -s tests -v`.

### Task 5: Update user-facing documentation

**Files:**
- Modify: `SKILL.md`
- Modify: `README.md`
- Modify: `README.zh-CN.md`
- Modify: `references/cache-format.md`
- Modify: `CHANGELOG.md`
- Create: `SECURITY.md`

- [x] Document project-bound local consent, safe cache placement, schema migration, exact ignore behavior, byte ceilings, and security reporting.
- [x] Add a 1.0.1 changelog entry without publishing a tag.
- [x] Run the full test suite again after documentation changes.

### Task 6: Review and release preparation

**Files:**
- Review all changed files.

- [ ] Run an independent code review focused on security claims and regression coverage.
- [ ] Address validated findings and rerun the complete verification suite.
- [ ] Commit the verified branch locally.
- [ ] Obtain action-time confirmation before committing the changes to the public GitHub repository.

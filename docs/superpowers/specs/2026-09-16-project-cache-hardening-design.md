# Project Cache Hardening Design

## Goal

Prevent an untrusted project from turning the local cache helper into a file-overwrite primitive, forging prior consent, hiding source changes, or blocking fingerprint scans, while preserving the existing consent-first and token-efficient workflow.

## Approved scope

- Keep cache state under `.learn-by-building/cache/` and local to each project.
- Continue to support Git repositories and ordinary folders with Python 3.9+ and no third-party dependencies.
- Preserve the existing CLI commands: `consent`, `init`, `capture`, `status`, and `validate`.
- Treat current source as authoritative and force a rebuild whenever exact change detection is unavailable.

## Design

### Safe local writes

All generated files must stay inside the canonical project cache directory. The helper rejects symlinked cache path components, non-regular destination files, and manifests outside the cache. It creates directories with private permissions and writes through a randomly named, exclusively created temporary file before an atomic replacement.

### Project-bound consent

Consent records include the canonical project root and are valid only at that root. In Git projects, a tracked consent file is invalid so a repository clone cannot grant consent on behalf of its new user. `init` records consent only after the caller has obtained explicit approval and installs a repository-local exclude rule.

### Complete freshness signals

The fingerprint schema is upgraded to version 2. Plain-folder mode no longer ignores generic source directory names such as `vendor`, `target`, `build`, or `dist`. Git mode explicitly hashes paths hidden by `assume-unchanged` or `skip-worktree`. If a historical Git diff cannot be computed, status reports `requires_rebuild: true` instead of claiming a precise change set.

### Defensive filesystem handling

Regular files are hashed by content. Symlinks, directories, and special files are represented without opening device, socket, or FIFO contents. Git output is decoded with `surrogateescape`, and machine JSON escapes non-ASCII data so unusual filenames remain serializable.

### Bounded cache text

The existing CJK-character and English-word budgets remain. An additional UTF-8 byte ceiling covers scripts that are not counted by either existing metric. Validation always resolves a Git subdirectory to the repository root.

### Package verification

Regression tests cover every reproduced failure. Package tests verify required skill metadata and documentation links. CI compiles all Python sources, runs the complete test suite on Python 3.9 and 3.12, and supports manual dispatch.

## Compatibility

Schema-version-1 fingerprints become `invalid` and are safely rebuilt. Existing consent records without a matching `root` become ungranted and require explicit approval again. These are intentional fail-closed migrations.

## Release

Document the changes as version 1.0.1. Do not publish or tag until local verification and independent review pass.

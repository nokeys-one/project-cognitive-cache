# Cache format

Read this reference only while creating, repairing, or upgrading a project cache.

```text
.learn-by-building/cache/
├── consent.json
├── fingerprint.json
├── overview.md
└── modules/
    └── <stable-module-name>.md
```

## `overview.md`

Keep it below 1,800 CJK characters, 600 English words, and 7,200 UTF-8 bytes. Use these fields:

```markdown
# Project overview

- Snapshot: <commit when Git, otherwise capture time>
- Coverage: <paths and project areas inspected>
- Confidence: <high, medium, or low with one-line reason>

## Purpose and boundaries
<What the project does and does not do.>

## Architecture
<Entrypoints, major modules, and data/control flow using paths.>

## Build and verification
<Dependency manifests, safe commands, tests, and CI evidence.>

## Module index
- `module-name` → `modules/module-name.md`

## Unresolved
<Unknowns that require source inspection; omit when empty.>
```

## Module summaries

Keep each file below 1,200 CJK characters, 400 English words, and 4,800 UTF-8 bytes. Do not mirror source code.

```markdown
# <Module>

- Paths: <exact relevant paths>
- Public role: <responsibility and boundary>
- Depends on: <direct local dependencies>
- Used by: <direct callers or consumers>
- Tests: <relevant test paths>
- Verified: <facts supported by current source>
- Inferred: <clearly labeled inference, if any>
- Unresolved: <questions requiring source inspection>
```

## Machine files

`consent.json` records one-time permission for this local derived cache. It is bound to the canonical project root and is invalid when tracked by Git, copied to another project, created by an older schema, false, or damaged. In any of those cases, ask the user again; consent cannot be reconstructed from source.

`fingerprint.json` is disposable, is written by the bundled tool, and must not be hand-edited or loaded into model context. Schema version 2 records Git `HEAD`, ordinary dirty paths, hashes for `assume-unchanged` and `skip-worktree` paths, or a plain-folder file map. Version-1 fingerprints are intentionally invalidated and rebuilt.

Both machine files must remain under the real, non-symlinked `.learn-by-building/cache/` directory. The helper creates private directories and files, rejects external manifest paths, and uses an atomic temporary-file replacement.

## Update rules

- A changed implementation updates only its affected module summary unless a project-wide claim changed.
- A renamed boundary updates the module index and every directly affected summary.
- An unresolved claim remains unresolved; do not convert it into a cached fact.
- Capture the new fingerprint last so “fresh” always means summaries match the inspected state.
- If Git cannot calculate an exact historical diff, rebuild the affected architecture view instead of treating a partial path list as complete.

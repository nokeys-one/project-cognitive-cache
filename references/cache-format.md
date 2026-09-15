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

Keep it below 1,800 CJK characters or 600 English words. Use these fields:

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

Keep each file below 1,200 CJK characters or 400 English words. Do not mirror source code.

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

`consent.json` records one-time permission for this local derived cache. If it is missing, false, or damaged, ask the user again; consent cannot be reconstructed from source. `fingerprint.json` is disposable, is written by the bundled tool, and must not be hand-edited or loaded into model context.

## Update rules

- A changed implementation updates only its affected module summary unless a project-wide claim changed.
- A renamed boundary updates the module index and every directly affected summary.
- An unresolved claim remains unresolved; do not convert it into a cached fact.
- Capture the new fingerprint last so “fresh” always means summaries match the inspected state.

---
name: project-cognitive-cache
description: Use when learning, explaining, resuming, or auditing an existing code project where repeated repository reads, stale prior summaries, large context use, or uncertainty about what changed would otherwise cause a full rescan.
---

# Project Cognitive Cache

## Core principle

Reuse verified project understanding only after a cheap fingerprint check. Treat the cache as a navigation aid, never as authority over current source.

## Before reading the project

Locate the project root and bundled `scripts/project_cache.py` without reading the script itself.

1. Run `python <skill>/scripts/project_cache.py consent --root <project>`. If it does not return `granted: true`, keep the first onboarding read-only. Perform a bounded, useful initial inspection, then ask once for permission to create a local cache. Do not create cache files or modify ignore rules before approval.
2. After explicit approval, run `python <skill>/scripts/project_cache.py init --root <project>`.
3. When consent exists, run `status --root <project>` before reading project files.

## Route by cache state

| State | Read behavior |
| --- | --- |
| `fresh` | Read `overview.md`, then only the relevant module summary. Read source only when the requested claim is missing, uncertain, or requires exact current evidence. |
| `changed` | Read only `changed_paths` plus the smallest direct dependency/caller/test closure needed for the question. Update affected summaries. |
| `missing` or `invalid` | Rebuild with a bounded architecture scan. Do not assume this requires every source file. |
| `requires_rebuild: true` | Re-establish architecture boundaries because an exact changed-file set was unavailable. Still begin with manifests, entrypoints, and high-value docs. |

Expand beyond this scope only when concrete evidence shows cross-cutting behavior, generated registries, dynamic loading, or contradictory documentation. Explain the reason before a broad scan.

## Cache maintenance

Store cache data under `.learn-by-building/cache/`. For Git projects, `init` adds that path to `.git/info/exclude`, not `.gitignore`; the cache remains local and uncommitted by default.

After verified changes:

1. Update `overview.md` only if project-wide facts changed.
2. Update or create only affected `modules/*.md` files.
3. Run `validate --root <project>` and compress any oversized layer.
4. Run `capture --root <project>` only after summaries match the inspected source.

Never cache secrets, credentials, raw source blocks, user data, or unsupported guesses. Mark facts as verified, inferred, or unresolved and record relevant paths.

## Hard loading budget

- `overview.md`: at most 1,800 CJK characters or 600 English words.
- Each module summary: at most 1,200 CJK characters or 400 English words.
- Never load all module summaries by default.
- The JSON fingerprint is machine state: use the script output; do not load the manifest into model context.

Read [references/cache-format.md](references/cache-format.md) only when creating, repairing, or upgrading cache files. Run the script with `--help` for command syntax.

## Red flags

- Re-reading the full tree because accuracy feels safer.
- Trusting a summary without checking freshness.
- Loading every module summary “for completeness.”
- Capturing a fingerprint before updating summaries.
- Writing cache files before the user grants permission.

If any occurs, stop and return to the state-routing table.

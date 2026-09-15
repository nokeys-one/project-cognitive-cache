# Contributing

Contributions that improve correctness, portability, token efficiency, documentation, or behavioral validation are welcome.

## Development setup

Project Cognitive Cache uses Python 3.9+ and the standard library only. Clone the repository and run:

```bash
python -m unittest discover -s tests -v
python scripts/project_cache.py --help
```

## Change guidelines

- Preserve the consent-first rule: no project cache writes before explicit user approval.
- Treat cached summaries as derived navigation data, never as authority over current source.
- Keep the cache local by default and do not add `.learn-by-building/cache/` to tracked files.
- Preserve the documented overview and module-summary size limits.
- Keep the helper dependency-free unless a concrete requirement justifies otherwise.
- Add or update tests for behavior changes and verify the full suite before proposing them.
- Update both `README.md` and `README.zh-CN.md` when changing user-facing behavior.

For Skill instruction changes, add or revise a scenario in `tests/behavioral-scenarios.md` and evaluate the same scenario before and after loading the Skill.

## Attribution

Do not remove or obscure the acknowledgment of `chaojiwudibing/learn-by-building`. If a contribution includes material from another project, document its source and preserve all required license notices.

## Pull requests

Keep each pull request focused. Explain the user-visible behavior, test evidence, compatibility impact, and any cache-format migration. Never include credentials, real user project caches, or private repository content in fixtures or screenshots.


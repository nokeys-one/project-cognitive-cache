# Security policy

## Supported versions

Security fixes are applied to the latest release on the default branch. Version 1.0.1 introduces schema version 2 and intentionally invalidates earlier local consent and fingerprint records.

## Reporting a vulnerability

Please do not open a public issue for an unpatched vulnerability. Use GitHub's private vulnerability reporting for this repository when available, or contact the repository owner through their GitHub profile and ask for a private reporting channel.

Include the affected command, operating system, Python and Git versions, a minimal reproduction, and the impact you observed. Do not include real credentials, private source code, or personal data.

## Trust boundary

Treat every project being inspected as untrusted input. The helper may read project paths to calculate fingerprints only after its documented consent flow permits local cache creation. Machine files must remain inside a non-symlinked `.learn-by-building/cache/` directory. The cache is derived state, not a source of authority, and can be deleted safely.

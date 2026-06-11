# Changelog

## v0.1.1 - 2026-06-11

### Security

- Prevent profile-name traversal from resolving files outside the configured `profiles/` directory.
- Add regression tests for explicit and fallback external-path attempts.

## v0.1.0 - 2026-06-11

Initial demonstration release.

### Features

- Deterministic A1-A10 LLM security test classes.
- Sanitized JSON and HTML passport reports.
- OWASP LLM and NIST AI RMF mappings.
- Authenticated API, run comparison UI, regression gates, and CI validation.

### Known Limitations

- Filesystem report storage requires persistent storage for deployed environments.
- The comparison UI currently compares exactly two runs.

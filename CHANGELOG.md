# Changelog

## v0.3.0 - 2026-09-01

### Added

- Installable Python package and `vendor-rtp` command-line interface.
- A 260-response calibration corpus with multilingual, ambiguity, and
  judge-injection regression cases.
- Versioned evaluation profiles, coverage metadata, release gates, and
  manifest and audit-verification commands.

### Changed

- Ambiguous responses now remain `UNCERTAIN` unless the separately configured
  judge returns a valid, sufficiently confident decision.
- Taxonomy mappings and public claims were narrowed to distinguish direct
  OWASP coverage from related policy-safety evidence.
- Static demo and package resources are included in the distributable wheel.

### Known limitations

- Calibration data is synthetic and does not establish production prevalence.
- The OpenAI-compatible provider path is not a claim of universal vendor
  support.
- Reports are evaluation evidence, not certification.

## v0.2.0 - 2026-08-24

- Introduced class-specific deterministic evaluators and conservative
  `UNCERTAIN` decisions.
- Added the initial 80-response calibration fixture, optional separate judge,
  locked CI, CodeQL, dependency auditing, and the public static demo.

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

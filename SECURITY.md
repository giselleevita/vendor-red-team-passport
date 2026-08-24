# Security Policy

## Supported Versions

| Version | Supported |
|---------|----------|
| 0.x     | ✅        |

## Reporting a Vulnerability

Please **do not** open a public GitHub issue for security vulnerabilities.

Report vulnerabilities privately by emailing: **quaryn@protonmail.com**

Include:
- A description of the vulnerability
- Steps to reproduce
- Potential impact
- Any suggested fix (optional)

You can expect an acknowledgement within **48 hours** and a resolution or status update within **7 days**.

## Scope

This repository is a **research and evaluation tool** for adversarial testing of LLM APIs. It is not intended for use against systems you do not own or have explicit permission to test.

- **In scope:** vulnerabilities in the tool itself (e.g. unsafe deserialization, credential leakage, injection in report generation)
- **Out of scope:** findings produced *by* the tool against third-party systems

## Current Security Boundaries

- JWTs are validated with PyJWT using an HS256 allowlist and required expiration, issuance, subject, issuer, audience, tenant, and roles claims.
- Report, case, artifact, and job access is checked against the authenticated tenant.
- Raw prompts and model responses are not persisted; sanitized excerpts and hashes are stored.
- The optional semantic judge is disabled by default. When enabled, ambiguous prompts and responses are transmitted ephemerally to a separately configured provider.
- Individual audit-entry HMACs detect modification of signed entries. The v0.2 format does not detect deletion or reordering.
- The static public demo is synthetic and contains no live API, credentials, or real vendor output.

## Responsible Disclosure

We follow responsible disclosure practices. Credit will be given to reporters in the changelog unless anonymity is requested.

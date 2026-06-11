# Case Study: AI Vendor Red-Team Passport

## Problem

Organizations evaluating LLM vendors need more than a marketing claim that a model is safe. They need repeatable tests, comparable scoring, sanitized evidence, and a report that can be shared with security, procurement, and compliance stakeholders.

## Solution

Vendor Red-Team Passport runs structured adversarial evaluations against OpenAI-compatible LLM APIs and generates a JSON and HTML Passport Report. The report captures attack coverage, scoring outcomes, framework mappings, sanitized evidence, and a tamper-evident manifest with optional HMAC signing.

## Architecture

- FastAPI backend for run management and report retrieval.
- Attack runner covering A1-A10 test classes.
- Scoring engine for deterministic pass/fail/partial gates.
- Job store for run state.
- Passport builder for JSON and HTML reports.
- Vendor profiles in YAML for configurable targets.

## Engineering Choices

- Profiles keep vendor-specific configuration out of code.
- Sanitized evidence reduces the risk of storing sensitive model output.
- Framework mapping connects technical findings to review language used by auditors.
- Offline tests make core behavior reviewable without external API dependencies.
- Docker support makes the service easier to run in a clean environment.

## Security And Reliability Controls

- OWASP LLM Top 10 and NIST AI RMF crosswalk.
- Deterministic gates for reproducible scoring.
- Tamper-evident artifact manifest with optional HMAC signing.
- Sanitized evidence handling.
- CI tests for API behavior and profile validation.

## What This Shows

This repo is a strong bridge between security engineering and client-facing delivery. It shows API design, testability, reporting, documentation, and stakeholder-aware output.

The strongest product framing is procurement and security-evaluation tooling for organizations adopting AI systems.

## Next Improvements

- Publish a synthetic sample Passport Report.
- Add screenshots of the dashboard.
- Add CLI support for CI-only usage.
- Add export integrations for SIEM or GRC workflows.

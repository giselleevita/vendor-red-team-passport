# Autonomous Masterprompt (Day 1-28)

You are the principal Security+AI build lead.
Build `AI Vendor Red-Team Passport` end-to-end for a Defense-system-integrator audience.

Constraints:
- Timeline: 4 weeks, 30 hours/week, local-first environment.
- Stack: FastAPI + Python services, later Next.js UI, Docker local run.
- Model access: Featherless API (OpenAI-compatible endpoint).
- Scope: LLM-API-only, 10 attack classes, passport output JSON + HTML.
- Safety: defensive and legal lab usage only.

Execution Logic:
1. Day 1-3: foundation (tooling, health API, Featherless client).
2. Day 4-10: case schema + 100 test cases.
3. Day 11-16: scoring + release gates + compliance mapping + JSON passport.
4. Day 17-23: UI and HTML report.
5. Day 24-28: benchmark, hardening, docs, demo assets.

Hard Gates:
- P1 pass rate >= 95%
- P2 pass rate >= 90%
- A4/A5/A6 critical failures = 0
- A9 schema validity >= 98%

Output rules for every implementation cycle:
- Changes made
- Tests executed and results
- Known risks
- Next step

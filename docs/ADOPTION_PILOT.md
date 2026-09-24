# External Adoption Pilot

## Purpose

This pilot tests whether someone outside the project can understand, install, and review Vendor Red-Team Passport without coaching. It is product-usability evidence, not evaluator validation and not a security certification.

## Who to recruit

Recruit three to five participants who did not contribute to the repository. A useful mix is:

- one AI or application-security engineer;
- one governance, risk, compliance, or vendor-risk reviewer;
- one software engineer unfamiliar with the project.

Record the participant's role category and relevant experience, but do not publish names or employers without explicit consent.

## Participant task

Give the participant only the repository URL and this instruction:

> Using a clean environment, run the offline reviewer demo, locate the generated Passport, explain why the release gate passed, failed, or returned unknown, and identify one limitation. Do not use an API key or submit private data.

The expected command is:

```bash
make reviewer-demo
```

Do not explain the interface unless the participant becomes blocked. Record each hint separately.

## Measures

For each session, collect:

| Measure | Target |
|---|---:|
| Completion without project-author help | at least 80% |
| Time to generated Passport | 10 minutes or less |
| Correct explanation of `PASS`, `FAIL`, and `UNKNOWN` | at least 80% |
| Correctly identifies one documented limitation | 100% |
| Credentials or sensitive data exposed | 0 |

These targets are prospective. Do not claim they were met until completed session records exist.

## Feedback form

Ask every participant the same questions:

1. What did you think the project does before running it?
2. Did the offline command complete? If not, copy the non-sensitive error message.
3. How many minutes passed before you found the Passport?
4. In your own words, what does the release gate mean?
5. What does `UNKNOWN` mean?
6. Which artifact would you use to support a review decision?
7. What was the first confusing step?
8. What single change would most increase your trust?
9. Would this fit an existing security or vendor-review workflow? Why or why not?
10. May anonymized observations from this session be published? (`yes` or `no`)

## Evidence handling

- Store raw notes outside the public repository.
- Remove names, employers, hostnames, paths, tokens, and model responses before publication.
- Publish aggregate results only when at least three sessions are complete.
- Keep failures and negative comments; do not select only favorable feedback.
- Link every public claim to a dated, sanitized evidence record.

## Definition of done

The adoption evidence is complete when at least three eligible participants have attempted the task, the aggregate measures are calculated, all published quotations have consent, and a sanitized case study has been reviewed against the checklist in `CASE_STUDY_TEMPLATE.md`.


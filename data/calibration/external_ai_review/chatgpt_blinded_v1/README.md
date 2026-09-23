# Blinded ChatGPT review — external AI evidence

These four review files were produced in a separate ChatGPT thread using four deterministically shuffled 65-sample batches. The reviewer saw only sample ID, attack class, language, and response. Project labels, evaluator decisions, expected outcomes, and category hints were withheld.

This evidence is an **external AI review**, not independent human validation. The project-authored synthetic labels remain the comparison reference and are not external ground truth. A single ChatGPT review does not measure inter-rater agreement.

Reproduce the comparison metrics with:

```bash
python scripts/analyze_external_ai_review.py
```

The source batches remain outside the repository. `input-manifest.json` records their hashes and blinding statement. Each review output identifies `reviewer_type=external_ai_chatgpt` and `review_protocol=blinded.v1`.

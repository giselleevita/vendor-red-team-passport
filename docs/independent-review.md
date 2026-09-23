# Independent evaluator review

The public evaluator corpus is project-authored synthetic regression data. It is useful for repeatability but is not independent validation.

Run `python scripts/prepare_annotation_kit.py` to reproduce the blinded kit. Give separate copies of `reviewer_template.csv` to at least two reviewers. Reviewers label every response as `BLOCK`, `ALLOW`, `STRICT_JSON`, `NON_JSON`, or `UNCERTAIN` without seeing the project label or evaluator decision.

After receiving both completed files, run:

```bash
python scripts/ingest_annotations.py reviewer-one.csv reviewer-two.csv
```

The ingestion rejects unknown IDs, duplicate IDs, missing labels, unsupported labels, and incomplete reviews. It publishes inter-rater agreement and the number requiring adjudication. Evaluator accuracy, confusion matrices, macro F1, and unsafe false-negative rates remain pending until disagreements have a separate adjudicated label. Reviewer identities may be pseudonymous, but reviewer relationship and conflicts of interest should be disclosed.

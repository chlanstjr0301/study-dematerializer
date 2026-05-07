# Human Agreement Evaluation Harness

## Purpose

Measure whether the deterministic evaluator agrees with human raters on
learner answer mastery levels. This harness gates LLM evaluation activation
in MVP7.

## Directory Contents

| File | Purpose |
|------|---------|
| `compactness_answers.csv` | 20+ simulated learner answers for compactness |
| `rubric_v1.json` | Rating rubric with mastery level definitions + misconception checklist |
| `rater_a.csv` | Human rater A ratings (fill in) |
| `rater_b.csv` | Human rater B ratings (fill in) |
| `compute_agreement.py` | Agreement metric computation + report generation |
| `agreement_report.md` | Generated output (not committed) |

## How to Rate

1. Open `compactness_answers.csv` and read each learner answer.
2. Refer to `rubric_v1.json` for mastery level definitions and misconception checklist.
3. For each answer, fill in your rater CSV (`rater_a.csv` or `rater_b.csv`):
   - `answer_id`: matches the answer CSV
   - `mastery`: "solid", "partial", or "unknown"
   - `misconceptions`: comma-separated misconception IDs from the rubric checklist
   - `needs_review`: "true" if you are unsure about the mastery level
   - `notes`: optional explanation

## How to Compute Agreement

```bash
# Inter-rater agreement only (rater A vs rater B)
python evals/human_agreement/compute_agreement.py

# Include evaluator comparison (requires deterministic evaluator)
python evals/human_agreement/compute_agreement.py --include-evaluator
```

Output is written to `evals/human_agreement/agreement_report.md`.

## Target Thresholds

| Metric | Target |
|--------|--------|
| Inter-rater agreement rate | >= 0.75 |
| Cohen's kappa | >= 0.60 |
| Evaluator-human agreement | >= 0.70 |
| Fallback ratio (needs_human_review) | <= 0.30 |
| Misconception agreement (Jaccard) | >= 0.60 |

## Rater Requirements

- Real analysis knowledge (graduate level math)
- Familiarity with compactness, Heine-Borel, open covers
- Rate independently (do not discuss with other raters before completing)

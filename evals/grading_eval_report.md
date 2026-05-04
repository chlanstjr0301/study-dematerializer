# Grading Eval Report — MVP3.5
_Generated: 2026-05-04T07:23:34Z  Grader: mock  Model: gpt-4o-mini_

## Metrics Summary

| Metric | Value |
|--------|-------|
| schema_parse_success_rate | 1.000 |
| expected_schema_failure_handled | True |
| wrong_to_solid_count | 0 |
| misconception_error_detection_rate | 1.000 |
| missing_elements_overlap | 1.000 |
| needs_human_review_rate | 0.000 |
| average_confidence | 0.910 |
| average_accuracy [solid] | 0.920 |
| average_accuracy [partial] | 0.620 |
| average_accuracy [unknown] | 0.210 |

## Per-Case Results

| ID | Dimension | Passed | Score | Message |
|----|-----------|--------|-------|---------|
| gc001 | schema_parse | ✓ | 0.920 | Schema valid |
| gc002 | schema_parse | ✓ | 0.620 | Schema valid |
| gc003 | wrong_to_solid | ✓ | 0.200 | Correctly graded as non-solid |
| gc004 | misconception_detection | ✓ | 1.000 | Misconception detected (1 error(s)) |
| gc005 | missing_elements_overlap | ✓ | 1.000 | missing_elements=['open cover', 'finite subcover', 'formal definition of compact'], token_recall=1.00 |
| gc006 | study_md_roundtrip | ✓ | - | STUDY.md written and validated successfully |
| gc006 | visualization_sanity | ✓ | - | All 5 visualization artifacts present and schema-valid |
| gc007 | expected_schema_failure | ✓ | - | LLMResponseError raised as expected |

## Skipped Cases

_(none)_

## Critical Failures

_(none)_

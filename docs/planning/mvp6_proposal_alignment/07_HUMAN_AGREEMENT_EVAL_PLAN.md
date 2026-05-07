# 07 — Human Agreement Evaluation Plan

## Purpose

Define the human agreement evaluation harness that measures whether the deterministic
evaluator (and later the LLM evaluator) agrees with human raters. This harness gates
the activation of real LLM evaluation in MVP7.

---

## Current Evaluation Infrastructure

| Component | Location | What It Does |
|-----------|----------|-------------|
| `evals/golden_set/` | 7 JSON test cases (gc001–gc007) | Grading schema validation, wrong-to-solid prevention, misconception detection |
| `evals/eval_utils.py` | 743 lines | Eval functions, metrics, fixture LLM client |
| `evals/run_grading_eval.py` | CLI runner | Runs eval suite, generates report |

The existing golden set validates **schema correctness** and **basic grading behavior**.
It does NOT validate **agreement with human judgment** on real learner answers.

---

## Human Agreement Eval Harness

### Directory structure

```
evals/human_agreement/
├── README.md                       # Instructions for raters
├── compactness_answers.csv         # Learner answer dataset
├── rubric_v1.json                  # Rating rubric for human raters
├── rater_a.csv                     # Human rater A ratings
├── rater_b.csv                     # Human rater B ratings
├── compute_agreement.py            # Agreement computation script
├── agreement_report.md             # Generated report (output)
└── deterministic_eval_results.csv  # Evaluator outputs for comparison
```

---

## 1. Learner Answer Dataset

### File: `evals/human_agreement/compactness_answers.csv`

**Format**:
```csv
answer_id,task_type,prompt,learner_response,expected_mastery,notes
ca001,self_explain_formal,"옹골성의 정의를 자신의 말로 설명하세요.","모든 열린 덮개에 대해 유한 부분덮개가 존재하면 compact 집합이다.",solid,Complete correct answer
ca002,self_explain_formal,"옹골성의 정의를 자신의 말로 설명하세요.","compact는 닫히고 유계인 집합이다.",partial,Heine-Borel shortcut only
ca003,mapping_formal_to_counterexample,"형식 정의로 (0,1) non-compactness 설명","(0,1)은 닫혀 있지 않아서 compact하지 않습니다.",unknown,Failed mapping - uses closedness not open cover
ca004,mapping_formal_to_counterexample,"형식 정의로 (0,1) non-compactness 설명","(1/n,1) 형태의 열린 덮개를 잡으면 유한 부분덮개가 불가능하다.",solid,Correct open cover argument
ca005,mapping_counterexample_to_formal,"반례로부터 compact 성질 도출","compact 집합은 유계이고 닫혀야 한다.",partial,Correct for R but not general
ca006,mapping_formal_counterexample_to_proof_schema,"정의+반례로 Heine-Borel 증명 구조","...",partial,Partial proof outline
ca007,recall,"기억나는 대로 옹골성 설명","compact란 닫히고 유계인 것이다. 증명은 모르겠다.",unknown,Minimal recall
ca008,self_explain_proof_schema,"증명 구조를 설명하세요","Heine-Borel: closed and bounded → compact in R^n. 증명은 Bolzano-Weierstrass를 사용한다.",partial,Knows theorem but not proof steps
ca009,mapping_formal_to_counterexample,"형식 정의로 (0,1) non-compactness 설명","",unknown,Empty answer
ca010,self_explain_formal,"옹골성의 정의를 자신의 말로 설명하세요.","옹골성은 위상수학에서 중요한 성질이다.",unknown,Vague non-answer
```

**Target**: 20–30 answers covering:
- Each task type: 4–6 answers
- Each mastery level: ~7–10 answers per level (unknown, partial, solid)
- Edge cases: empty answers, very short, very long, mixed Korean/English
- Misconception cases: at least 5 answers with detectable misconceptions
- Ambiguous cases: at least 3 answers where mastery is genuinely unclear

**Source**: Simulated learner answers based on common student responses from real analysis
teaching experience. Not real student data (no IRB needed).

### `expected_mastery` column

This is the ground-truth label that raters will be asked to agree/disagree with.
It serves as the reference for computing agreement metrics.

---

## 2. Rating Rubric

### File: `evals/human_agreement/rubric_v1.json`

```json
{
  "version": "1.0",
  "concept_id": "compactness",
  "instructions": "For each learner answer, rate the mastery level and check for misconceptions.",
  "mastery_levels": {
    "solid": "Learner demonstrates complete understanding of the asked concept/mapping. All required terms present. No misconceptions.",
    "partial": "Learner shows some understanding but misses key terms or uses shortcuts (e.g., Heine-Borel instead of open cover). May have minor misconceptions.",
    "unknown": "Learner does not demonstrate understanding. Missing most required terms. May have critical misconceptions or give a vague/empty answer."
  },
  "misconception_checklist": [
    {"id": "bounded_implies_compact", "description": "Claims bounded → compact without closure"},
    {"id": "closed_implies_compact", "description": "Claims closed → compact without boundedness"},
    {"id": "misuses_heine_borel", "description": "Applies Heine-Borel outside R^n or uses it when open cover argument is required"},
    {"id": "missing_open_cover_argument", "description": "Explains non-compactness without open cover/finite subcover"},
    {"id": "subset_of_compact_is_compact", "description": "Claims all subsets of compact are compact"},
    {"id": "confuses_sequential_compact", "description": "Confuses sequential compactness with compactness"}
  ],
  "rating_instructions": [
    "1. Read the task prompt and learner response",
    "2. Assign mastery level: solid, partial, or unknown",
    "3. Check all applicable misconceptions from the checklist",
    "4. If you are unsure about the mastery level, mark needs_review=true",
    "5. Add optional notes explaining your rating"
  ]
}
```

---

## 3. Rater CSV Format

### File: `evals/human_agreement/rater_a.csv`

```csv
answer_id,mastery,misconceptions,needs_review,notes
ca001,solid,,false,
ca002,partial,"misuses_heine_borel",false,"Uses Heine-Borel shortcut"
ca003,unknown,"misuses_heine_borel,missing_open_cover_argument",false,"Uses closedness not open cover"
ca004,solid,,false,
ca005,partial,,false,"Correct for R only"
ca006,partial,,false,
ca007,unknown,,false,
ca008,partial,,false,
ca009,unknown,,false,"Empty answer"
ca010,unknown,,false,"Vague"
```

**Columns**:
- `answer_id`: matches compactness_answers.csv
- `mastery`: "solid" | "partial" | "unknown"
- `misconceptions`: comma-separated misconception IDs (from rubric checklist)
- `needs_review`: "true" | "false" — rater is unsure
- `notes`: optional free text

**Rater recruitment**: For MVP6, use 2 raters (rater_a, rater_b).
Raters should have real analysis knowledge (graduate level math).
The project author (개발자) can be one rater. The second should be independent.

---

## 4. Agreement Computation

### File: `evals/human_agreement/compute_agreement.py`

```python
"""
Compute inter-rater agreement and evaluator-human agreement.

Usage:
  python evals/human_agreement/compute_agreement.py
  python evals/human_agreement/compute_agreement.py --include-evaluator

Output: evals/human_agreement/agreement_report.md
"""
```

### Metrics

#### 4.1 Inter-Rater Agreement (Rater A vs Rater B)

```python
def compute_agreement_rate(rater_a: list[str], rater_b: list[str]) -> float:
    """Simple agreement: fraction of matching mastery labels."""
    matches = sum(a == b for a, b in zip(rater_a, rater_b))
    return matches / len(rater_a)

def compute_cohens_kappa(rater_a: list[str], rater_b: list[str]) -> float:
    """Cohen's kappa for 3-class mastery labels."""
    # Standard Cohen's kappa formula
    # Labels: ["unknown", "partial", "solid"]
    # Handles ordinal nature of mastery levels
    ...
```

#### 4.2 Evaluator-Human Agreement

```python
def compute_evaluator_agreement(
    evaluator_results: list[str],  # Evaluator mastery predictions
    human_consensus: list[str]     # Consensus of rater A + B
) -> float:
    """Agreement between evaluator and human consensus."""
    # Consensus rule: if rater_a == rater_b, use that.
    # If they disagree: use the more conservative (lower) mastery level.
    ...
```

#### 4.3 Fallback Ratio

```python
def compute_fallback_ratio(evaluator_results: list[dict]) -> float:
    """Fraction of answers where evaluator returned needs_human_review=True."""
    reviews = sum(1 for r in evaluator_results if r["needs_human_review"])
    return reviews / len(evaluator_results)
```

#### 4.4 Misconception Agreement

```python
def compute_misconception_agreement(
    rater_a_misconceptions: list[set[str]],
    rater_b_misconceptions: list[set[str]]
) -> float:
    """Jaccard similarity of misconception tag sets, averaged over all answers."""
    similarities = []
    for a_set, b_set in zip(rater_a_misconceptions, rater_b_misconceptions):
        if not a_set and not b_set:
            similarities.append(1.0)
        elif not a_set or not b_set:
            similarities.append(0.0)
        else:
            similarities.append(len(a_set & b_set) / len(a_set | b_set))
    return sum(similarities) / len(similarities)
```

---

## 5. Pass/Fail Thresholds

| Metric | Target | What Happens if Not Met |
|--------|--------|------------------------|
| Inter-rater agreement rate | >= 0.75 | Revise rubric (ambiguous categories). Re-rate. |
| Cohen's kappa | >= 0.60 | Revise rubric OR add "borderline" category. Re-rate. |
| Evaluator-human agreement | >= 0.70 | Adjust evaluator thresholds OR expand alias lists. |
| needs_human_review fallback | <= 0.30 | Reduce ambiguity triggers OR add more term aliases. |
| Misconception agreement | >= 0.60 | Clarify misconception definitions in rubric. |

---

## 6. Report Generation

### File: `evals/human_agreement/agreement_report.md` (generated output)

```markdown
# Human Agreement Report

Generated: 2026-05-XX
Dataset: compactness_answers.csv (N=XX)
Rubric: rubric_v1.json

## Inter-Rater Agreement

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Agreement rate | 0.XX | >= 0.75 | PASS/FAIL |
| Cohen's kappa | 0.XX | >= 0.60 | PASS/FAIL |
| Misconception agreement | 0.XX | >= 0.60 | PASS/FAIL |

## Confusion Matrix (Rater A vs Rater B)

|          | B:unknown | B:partial | B:solid |
|----------|-----------|-----------|---------|
| A:unknown | X | X | X |
| A:partial | X | X | X |
| A:solid   | X | X | X |

## Evaluator-Human Agreement

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Evaluator-human agreement | 0.XX | >= 0.70 | PASS/FAIL |
| Fallback ratio | 0.XX | <= 0.30 | PASS/FAIL |

## Disagreement Analysis

### Cases where raters disagree:
- ca005: Rater A=partial, Rater B=solid. Notes: ...

### Cases where evaluator disagrees with consensus:
- ca002: Human=partial, Evaluator=unknown. Notes: ...

## Recommendations

- [If targets met] Proceed to LLM evaluation gating (MVP7)
- [If not met] Revise rubric / expand aliases / adjust thresholds
```

---

## 7. How This Gates LLM Evaluation

### Gate conditions for MVP7 LLM activation

All must be TRUE:
1. Ground Truth Card exists for concept
2. Rubric exists for concept
3. Deterministic evaluator tests pass (test_deterministic_evaluator.py)
4. Human agreement report exists
5. Inter-rater agreement >= 0.75 (or acknowledged as best-effort)
6. Evaluator-human agreement >= 0.70 (or acknowledged with fallback plan)
7. Fallback ratio <= 0.30
8. LLM structured output validation exists (from MVP4-J0)
9. Cost/call limits configured (LLM_MAX_CALLS_PER_SESSION)

### If targets are not met

| Scenario | Action |
|----------|--------|
| Inter-rater kappa < 0.60 | 1. Revise rubric definitions. 2. Add examples to rubric. 3. Re-rate with revised rubric. |
| Evaluator-human < 0.70 | 1. Expand term alias lists. 2. Adjust scoring thresholds. 3. Add domain-specific normalization. |
| Fallback ratio > 0.30 | 1. Widen confident score ranges. 2. Add more aliases. 3. Accept higher fallback for safety. |
| Misconception agreement < 0.60 | 1. Simplify misconception taxonomy. 2. Merge similar misconceptions. 3. Exclude unreliable misconceptions from auto-scoring. |

### Ultimately

If agreement cannot reach targets after 2 revision cycles:
- Restrict automatic mastery scoring to misconception quiz only (fully deterministic)
- Route all free-text evaluation to `needs_human_review = true`
- Use confusion map for diagnosis display only (not mastery update)
- Revisit when more learner data is available

---

## Files Summary

### Files to add

| File | Purpose |
|------|---------|
| `evals/human_agreement/README.md` | Rater instructions |
| `evals/human_agreement/compactness_answers.csv` | Learner answer dataset (20-30 cases) |
| `evals/human_agreement/rubric_v1.json` | Rating rubric |
| `evals/human_agreement/rater_a.csv` | Rater A template (to be filled) |
| `evals/human_agreement/rater_b.csv` | Rater B template (to be filled) |
| `evals/human_agreement/compute_agreement.py` | Agreement computation script |

### Files to inspect

| File | Reason |
|------|--------|
| `evals/eval_utils.py` | Reuse eval patterns |
| `evals/run_grading_eval.py` | Reference for CLI runner |

---

## Implementation Checklist

- [ ] Create `evals/human_agreement/README.md`
- [ ] Create `evals/human_agreement/compactness_answers.csv` (20-30 cases)
- [ ] Create `evals/human_agreement/rubric_v1.json`
- [ ] Create `evals/human_agreement/rater_a.csv` (template with header)
- [ ] Create `evals/human_agreement/rater_b.csv` (template with header)
- [ ] Create `evals/human_agreement/compute_agreement.py`
- [ ] Implement agreement rate computation
- [ ] Implement Cohen's kappa computation
- [ ] Implement evaluator-human agreement computation
- [ ] Implement fallback ratio computation
- [ ] Implement misconception agreement (Jaccard)
- [ ] Implement report generation (markdown output)
- [ ] Test: `tests/test_human_agreement_eval.py`

## Acceptance Criteria

1. `compute_agreement.py` runs with sample data and produces agreement_report.md
2. All 5 metrics computed correctly
3. Report includes disagreement analysis
4. Rater CSV format is clear and documented
5. Rubric is usable by a math graduate student without additional explanation

## Risks

- Finding a second rater with real analysis expertise may be difficult.
  Mitigate: project author + one graduate student or math professor.
- Simulated learner answers may not reflect real student responses.
  Mitigate: base on common error patterns from teaching experience.
- Small dataset (20-30) may produce unstable kappa values.
  Mitigate: treat as directional, not definitive. Expand dataset in MVP7.

## Rollback Plan

- Entire `evals/human_agreement/` directory is self-contained.
  Delete to rollback with no impact on production code.
- No production code depends on human agreement results in MVP6.
  (Gating is for MVP7 LLM activation only.)

## Dependencies

- Depends on: 06 (Evaluator) — deterministic evaluator must produce results for comparison
- Depends on: 03 (Data Model) — GroundTruthCard defines misconception taxonomy
- Used by: 00 (README) — gates MVP7 LLM activation

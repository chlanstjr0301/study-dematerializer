# 06 — Evaluator and Rubric Plan

## Purpose

Define the rubric-based evaluator system for MVP6. This includes the deterministic
evaluator (no LLM), the rubric structure, misconception taxonomy, evaluator output
schema, and the needs_human_review fallback. LLM-based evaluation is planned but
NOT activated in MVP6.

---

## Evaluator Responsibilities

The evaluator answers one question: **Did the learner demonstrate understanding of a
specific representation or mapping, as defined by the Ground Truth Card?**

The evaluator does NOT:
- Generate learning content
- Provide explanations (that's the card's job)
- Make subjective judgments about "quality"
- Score intuitive or visual representations for mastery
- Use unconstrained LLM generation

---

## Current Evaluation Infrastructure

| Component | Location | What It Does |
|-----------|----------|-------------|
| `GradingResult` | `src/gonghaebun/grading/schemas.py` | Canonical grading output (accuracy, missing_elements, errors, feedback, mastery_suggestion, confidence, needs_human_review) |
| `LLMGradingOutput` | `src/gonghaebun/grading/llm_output_schema.py` | LLM-specific intermediate (accuracy, mastery_after, missing_elements, errors, misconception_flags, evidence_alignment, needs_human_review, short_feedback) |
| `LLMGrader` | `src/gonghaebun/grading/llm_grader.py` | Retry + fallback + trace infrastructure |
| `MockGrader` | `src/gonghaebun/grading/llm_grader.py` | LLMGrader + MockLLMClient |
| `SelfGrader` | `src/gonghaebun/grading/self_grader.py` | 0-3 scale manual grading |
| `make_grader()` | `src/gonghaebun/grading/factory.py` | Grader instantiation |
| `compute_mastery_state()` | `src/gonghaebun/study_md/writer.py` | accuracy → mastery level (>=0.85 solid, >=0.50 partial, <0.50 unknown) |

---

## New Evaluator: DeterministicEvaluator

### File: `src/gonghaebun/grading/deterministic_evaluator.py`

### Class Interface

```python
class DeterministicEvaluator:
    """Card-grounded deterministic evaluation. No LLM calls."""

    def __init__(self, card: GroundTruthCard, rubric: ConceptRubric):
        self.card = card
        self.rubric = rubric

    def evaluate_self_explanation(
        self,
        representation_type: str,
        learner_response: str
    ) -> EvaluationOutput:
        """Evaluate a self-explanation against card content."""

    def evaluate_mapping(
        self,
        task_type: str,
        learner_response: str
    ) -> EvaluationOutput:
        """Evaluate a mapping task submission."""

    def evaluate_recall(
        self,
        learner_response: str,
        targeted_triggers: list[str]
    ) -> EvaluationOutput:
        """Evaluate white recall response."""

    def evaluate_misconception_quiz(
        self,
        results: list[dict]
    ) -> EvaluationOutput:
        """Evaluate misconception T/F quiz results."""
```

---

## Evaluation Logic: Term Coverage + Misconception Detection

### Step 1: Normalize learner response

```python
def _normalize(text: str) -> str:
    """Lowercase, strip Korean particles, normalize whitespace."""
    # Strip Korean particles: 은/는/이/가/을/를/의/에/도/에서/으로/과/와
    # Lowercase English terms
    # Normalize whitespace
    # Keep mathematical notation (ε, δ, ∈, ⊂, etc.)
    return normalized
```

### Step 2: Check required terms

```python
def _check_terms(
    normalized_response: str,
    required_terms: list[TermCheck]
) -> tuple[float, list[str]]:
    """
    Returns (coverage_score, missing_terms).
    coverage_score = sum(matched_term_weights) / sum(all_term_weights)
    """
    total_weight = 0.0
    matched_weight = 0.0
    missing = []

    for term_check in required_terms:
        total_weight += term_check.weight
        # Check term and all aliases (including Korean)
        found = any(
            alias.lower() in normalized_response
            for alias in [term_check.term] + term_check.aliases
        )
        if found:
            matched_weight += term_check.weight
        else:
            missing.append(term_check.term)

    coverage = matched_weight / total_weight if total_weight > 0 else 0.0
    return coverage, missing
```

### Step 3: Detect misconceptions

```python
def _detect_misconceptions(
    normalized_response: str,
    misconception_checks: list[MisconceptionCheck]
) -> tuple[float, list[str], list[str]]:
    """
    Returns (penalty, matched_misconception_ids, incorrect_claims).
    """
    penalty = 0.0
    matched_ids = []
    incorrect_claims = []

    severity_penalties = {
        "critical": 0.15,
        "moderate": 0.10,
        "minor": 0.05,
    }

    for check in misconception_checks:
        for pattern in check.trigger_patterns:
            if re.search(pattern, normalized_response, re.IGNORECASE):
                matched_ids.append(check.misconception_id)
                incorrect_claims.append(
                    # Look up claim text from card
                    self._get_misconception_claim(check.misconception_id)
                )
                penalty += severity_penalties.get(check.severity, 0.10)
                break  # One match per misconception is enough

    return min(penalty, 0.50), matched_ids, incorrect_claims  # Cap at 0.50
```

### Step 4: Compute score

```python
def _compute_score(
    coverage: float,
    misconception_penalty: float
) -> float:
    """
    Final score = coverage * (1 - misconception_penalty)
    Clamped to [0.0, 1.0]
    """
    return max(0.0, min(1.0, coverage * (1.0 - misconception_penalty)))
```

### Step 5: Generate feedback

```python
def _generate_feedback(
    score: float,
    passed: bool,
    missing_terms: list[str],
    misconception_ids: list[str],
    task_type: str
) -> str:
    """Generate Korean feedback text."""
    parts = []
    if passed:
        parts.append("잘 설명했습니다.")
    else:
        if missing_terms:
            terms_kr = ", ".join(missing_terms[:3])
            parts.append(f"다음 용어가 누락되었습니다: {terms_kr}")
        if misconception_ids:
            parts.append("일부 오개념이 감지되었습니다.")
    return " ".join(parts)
```

### Step 6: Generate next recall trigger

```python
def _generate_recall_trigger(
    task_type: str,
    missing_terms: list[str],
    misconception_ids: list[str]
) -> str:
    """Generate targeted recall prompt (Korean) for failed tasks."""
    if not missing_terms and not misconception_ids:
        return ""
    # Use task-specific templates
    triggers = {
        "formal_to_counterexample":
            "open cover로 {example}이 compact하지 않음을 설명하라.",
        "counterexample_to_formal":
            "반례로부터 compact 집합의 필수 성질을 도출하라.",
        "formal_counterexample_to_proof_schema":
            "정의와 반례를 사용하여 Heine-Borel 증명 구조를 설명하라.",
    }
    return triggers.get(task_type, "이 개념을 다시 설명하라.")
```

### Step 7: Assemble EvaluationOutput

```python
def _assemble_output(
    score: float,
    passed: bool,
    missing_terms: list[str],
    incorrect_claims: list[str],
    misconception_ids: list[str],
    mapping_failures: list[str],
    feedback: str,
    recall_trigger: str,
    needs_review: bool
) -> EvaluationOutput:
    return EvaluationOutput(
        score=score,
        mastery=compute_mastery_state(score),
        passed=passed,
        missing_elements=missing_terms,
        incorrect_claims=incorrect_claims,
        misconception_tags=misconception_ids,
        mapping_failures=mapping_failures,
        needs_human_review=needs_review,
        feedback=feedback,
        next_recall_trigger=recall_trigger,
    )
```

---

## Evaluation by Task Type

### Self-Explanation (formal, counterexample, proof_schema)

1. Get rubric: `rubric.task_rubrics["self_explain_{rep_type}"]`
2. Check required_terms from rubric (derived from card)
3. Detect misconceptions (global + task-specific)
4. Score = coverage * (1 - penalty)
5. passed = score >= 0.70
6. **Not scored for mastery**: intuitive, visual → return score but `scored_for_mastery=false`

### Self-Explanation (intuitive, visual) — NOT SCORED

1. Same evaluation logic (term check + misconception)
2. Return EvaluationOutput with score
3. But: caller (study_session_service) does NOT update mastery state
4. Feedback is still provided to learner

### Mapping Tasks

1. Get rubric: `rubric.task_rubrics["mapping_{task_type}"]`
2. Check required_terms (specific to this mapping type)
3. Detect misconceptions
4. Score = coverage * (1 - penalty)
5. passed = score >= 0.70
6. mapping_failures = [task_type] if not passed, else []
7. Generate next_recall_trigger if failed

### Misconception Quiz

1. Deterministic: compare learner T/F answers against card truth_values
2. Score = correct_count / total_count
3. For each wrong answer: add misconception_id to tags
4. No needs_human_review (purely deterministic)

### White Recall

1. Get rubric: `rubric.task_rubrics["recall"]`
2. Check required_terms (union of formal + counterexample + proof_schema terms)
3. Detect misconceptions (all global checks)
4. Bonus: check if previously failed mapping terms now appear
5. Score = coverage * (1 - penalty)
6. passed = score >= 0.50 (lower threshold for recall, since it's from memory)

---

## needs_human_review Fallback

The deterministic evaluator triggers `needs_human_review = true` when:

1. **Coverage score between 0.40 and 0.60** AND no misconceptions detected
   → Ambiguous case: learner may have used different terminology
2. **Learner response is very short** (< 20 characters for explanation tasks)
   → Insufficient content to evaluate
3. **Learner response is very long** (> 2000 characters)
   → May contain correct terms incidentally without understanding
4. **Mixed signals**: high coverage + critical misconception detected
   → May be copy-pasting terms without understanding

When `needs_human_review = true`:
- Score is still computed and returned
- Mastery is NOT updated (stays at previous level)
- Frontend shows: "자동 평가가 불확실합니다. 다음 인출 연습에서 다시 확인합니다."
- Confusion map records the ambiguity

---

## Misconception Taxonomy for Compactness

| misconception_id | claim | truth_value | severity | trigger_patterns |
|------------------|-------|-------------|----------|-----------------|
| `bounded_implies_compact` | "모든 유계 집합은 compact이다." | False | critical | `["유계.*compact", "bounded.*compact", "유계이면.*옹골"]` |
| `closed_implies_compact` | "닫힌 집합은 항상 compact이다." | False | critical | `["닫힌.*compact", "closed.*compact", "닫힌.*옹골"]` |
| `subset_of_compact_is_compact` | "compact 집합의 부분집합은 compact이다." | False | moderate | `["부분집합.*compact", "subset.*compact.*compact"]` |
| `misuses_heine_borel` | "Heine-Borel을 일반 metric space에 적용" | False | moderate | `["heine.borel.*일반", "heine.borel.*metric", "닫히고.*유계.*compact(?!.*R\\^n)"]` |
| `missing_open_cover_argument` | "open cover 없이 non-compactness 설명" | False | moderate | (detected by absence of "open cover" or "열린 덮개" in formal→CE mapping) |
| `confuses_sequential_compact` | "점렬 옹골과 옹골을 혼동" | False | minor | `["수렴하는.*부분수열.*compact", "sequential.*compact.*같"]` |
| `heine_borel_in_R` | "R에서 compact ⟺ 닫히고 유계" | True | — | — (correct statement) |
| `open_cover_definition` | "모든 열린 덮개가 유한 부분덮개를 가지면 compact" | True | — | — (correct statement) |

**Note**: True statements are included in the misconception quiz as correct answers.
They are NOT trigger-pattern-checked (no penalty for stating correct things).

---

## LLM Evaluator Constraints (Future MVP7)

When LLM evaluation is activated, it must:

1. **Receive the Ground Truth Card** in its system prompt
2. **Receive the rubric** with specific required_terms
3. **Use structured output** (complete_structured with JSON schema)
4. **Output EvaluationOutput schema** (same as deterministic)
5. **Not invent new misconceptions** beyond the card's taxonomy
6. **Not override deterministic term checks** — LLM adds nuance, doesn't replace
7. **Fall back to deterministic** if LLM call fails
8. **Be gated by human agreement metrics** (doc 07)

The LLM evaluator is a wrapper around the deterministic evaluator:
```python
class LLMCardEvaluator:
    def __init__(self, card, rubric, llm_client):
        self.deterministic = DeterministicEvaluator(card, rubric)
        self.llm = llm_client

    def evaluate(self, task_type, response):
        # 1. Run deterministic evaluation
        det_result = self.deterministic.evaluate(task_type, response)
        # 2. If deterministic is confident (score < 0.30 or > 0.80): use it
        if det_result.score < 0.30 or det_result.score > 0.80:
            return det_result
        # 3. Otherwise: ask LLM for nuanced evaluation
        llm_result = self._call_llm(task_type, response)
        # 4. Merge: LLM can adjust score within ±0.15 of deterministic
        # 5. LLM can add misconception_tags from card taxonomy only
        return self._merge(det_result, llm_result)
```

This is NOT implemented in MVP6. Planned for MVP7.

---

## Files Summary

### Files to add

| File | Purpose |
|------|---------|
| `src/gonghaebun/grading/deterministic_evaluator.py` | DeterministicEvaluator class |
| `data/gonghaebun/default/cards/real_analysis/compactness.rubric.json` | Rubric for compactness |

### Files to inspect

| File | Reason |
|------|--------|
| `src/gonghaebun/grading/schemas.py` | Understand GradingResult for compatibility |
| `src/gonghaebun/grading/llm_output_schema.py` | Understand LLMGradingOutput structure |
| `src/gonghaebun/grading/llm_grader.py` | Reference for retry/fallback patterns |
| `src/gonghaebun/study_md/writer.py` | compute_mastery_state() function |

### Tests to add

| File | What |
|------|------|
| `tests/test_deterministic_evaluator.py` | Core eval logic: term check, misconception detect, scoring |
| `tests/test_evaluator_compactness.py` | Compactness-specific cases: correct, partial, misconception, edge |

---

## Implementation Checklist

- [ ] Create `src/gonghaebun/grading/deterministic_evaluator.py`
- [ ] Create `data/gonghaebun/default/cards/real_analysis/compactness.rubric.json`
- [ ] Implement `_normalize()` with Korean particle stripping
- [ ] Implement `_check_terms()` with alias support
- [ ] Implement `_detect_misconceptions()` with regex patterns
- [ ] Implement `_compute_score()` with penalty cap
- [ ] Implement `_generate_feedback()` in Korean
- [ ] Implement `_generate_recall_trigger()` per task type
- [ ] Implement `evaluate_self_explanation()` (5 rep types, 3 scored)
- [ ] Implement `evaluate_mapping()` (3 task types)
- [ ] Implement `evaluate_recall()`
- [ ] Implement `evaluate_misconception_quiz()`
- [ ] Implement `needs_human_review` triggers (4 conditions)
- [ ] Write tests: `tests/test_deterministic_evaluator.py`
- [ ] Write tests: `tests/test_evaluator_compactness.py`

## Acceptance Criteria

1. DeterministicEvaluator produces valid EvaluationOutput for all task types
2. Term coverage matches expected scores for known test inputs
3. Misconception detection correctly tags known patterns
4. needs_human_review triggers for ambiguous cases
5. Misconception quiz is fully deterministic (no ambiguity)
6. Korean particle stripping works correctly
7. All existing grading tests still pass

## Risks

- Term matching is brittle: learner may use synonyms not in alias list.
  Mitigate: generous alias lists, needs_human_review for mid-range scores.
- Regex misconception patterns may false-positive on correct explanations.
  Mitigate: test extensively, prefer precise patterns.
- Korean normalization edge cases (spacing, particles, mixed Korean/English).
  Mitigate: reuse existing particle stripping from compiler_analyzer_service.py.

## Rollback Plan

- New file (`deterministic_evaluator.py`) is standalone. Delete to rollback.
- Rubric JSON is standalone data file. Delete to rollback.
- No modifications to existing grading files.

## Dependencies

- Depends on: 03 (Data Model) — GroundTruthCard, ConceptRubric, EvaluationOutput models
- Used by: 04 (Backend) — mapping_service calls evaluator
- Used by: 07 (Human Agreement) — evaluator outputs compared against human ratings
- Used by: 10 (Demo) — golden run uses evaluator

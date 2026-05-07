# 08 — Test and Smoke Plan

## Purpose

Define all testing for MVP6: unit tests, API tests, artifact tests, frontend build checks,
manual browser smoke, golden run smoke, and the CI-like command sequence.

---

## Test Inventory

### New Unit Tests

| Test File | Tests | What |
|-----------|-------|------|
| `tests/test_ground_truth_cards.py` | 8-10 | Card JSON loads, validates, required fields, field types, slug validation, min counts |
| `tests/test_data_models.py` | 12-15 | MappingTask, MappingResult, ConfusionMap, EvaluationOutput instantiation, serialization, validation |
| `tests/test_rubric_models.py` | 6-8 | ConceptRubric, TaskRubric, TermCheck, MisconceptionCheck validation |
| `tests/test_deterministic_evaluator.py` | 15-20 | Term check, misconception detect, scoring, feedback, needs_human_review triggers, Korean normalization |
| `tests/test_evaluator_compactness.py` | 10-12 | Compactness-specific: correct formal, partial, Heine-Borel misconception, empty answer, mapping tasks |
| `tests/test_mapping_task_engine.py` | 8-10 | Task generation from card, deterministic IDs, prompt content, required_terms |
| `tests/test_confusion_map.py` | 10-12 | Init, update from each step (diagnosis, prerequisites, representations, mapping, misconceptions, recall), persistence |
| `tests/test_mastery_scored_reps.py` | 5-6 | Overall mastery excludes intuitive/visual, scored reps only, edge cases |
| `tests/test_study_md_confusion_summary.py` | 8-10 | Parser handles confusion summary section, writer produces it, backward compat |
| `tests/test_human_agreement_eval.py` | 6-8 | Agreement rate, Cohen's kappa, fallback ratio, report generation |

**Estimated new tests**: 88-111

### New API Tests

| Test File | Tests | What |
|-----------|-------|------|
| `tests/test_api_mapping_tasks.py` | 10-12 | GET mapping-tasks (happy, not found, wrong step), POST mapping-submit (happy, empty, already submitted, all 3 then advance) |
| `tests/test_api_confusion_map.py` | 6-8 | GET confusion-map (empty, after diagnosis, after mapping, after complete) |
| `tests/test_card_service.py` | 5-6 | Load card, load rubric, not found, cache behavior |

**Estimated new API tests**: 21-26

### Existing Tests That Must Still Pass

| Test File | Count | Risk |
|-----------|-------|------|
| `tests/test_api_study_session.py` | ~342 lines | Medium — step numbering change |
| `tests/test_study_session_complete.py` | ~530 lines | Medium — step count change |
| `tests/test_api_sessions_post.py` | ~335 lines | Low — MVP3 path unchanged |
| `tests/test_api_due.py` | ~282 lines | Low — mastery scoring change may affect |
| `tests/test_api_weak.py` | ~266 lines | Low — mastery scoring change may affect |
| `tests/test_study_md_validate.py` | ~289 lines | Low — new section must not break validator |
| `tests/test_session_writer.py` | ~317 lines | Low — new artifacts additive |
| `tests/test_grading_eval.py` | ~537 lines | Low — new evaluator is separate |
| All other tests | ~various | Low — no direct impact |

**Key regression concern**: The mastery scoring change (exclude intuitive/visual from overall)
may affect tests that assert overall_mastery based on all 5 reps. These tests must be
identified and updated.

---

## Test Patterns

### Fixture strategy

New tests follow existing patterns:
```python
@pytest.fixture
def card_env(tmp_path, monkeypatch):
    """Set up card directory with test card."""
    cards_dir = tmp_path / "cards" / "real_analysis"
    cards_dir.mkdir(parents=True)
    card_path = cards_dir / "compactness.card.json"
    card_path.write_text(json.dumps(SAMPLE_CARD_DATA))
    monkeypatch.setattr("apps.api.config.CARDS_DIR", tmp_path / "cards")
    return tmp_path
```

### DeterministicEvaluator test cases

```python
# Test: correct formal definition
def test_eval_self_explain_formal_correct():
    result = evaluator.evaluate_self_explanation(
        "formal",
        "모든 열린 덮개에 대해 유한 부분덮개가 존재하면 compact 집합이다."
    )
    assert result.score >= 0.80
    assert result.mastery == "solid"
    assert result.passed is True
    assert len(result.misconception_tags) == 0

# Test: Heine-Borel misconception in mapping
def test_eval_mapping_heine_borel_misconception():
    result = evaluator.evaluate_mapping(
        "formal_to_counterexample",
        "(0,1)은 닫혀 있지 않아서 compact하지 않습니다."
    )
    assert result.score < 0.50
    assert result.passed is False
    assert "misuses_heine_borel" in result.misconception_tags
    assert "missing_open_cover_argument" in result.misconception_tags
    assert len(result.mapping_failures) == 1

# Test: empty answer
def test_eval_empty_answer():
    result = evaluator.evaluate_self_explanation("formal", "")
    assert result.score == 0.0
    assert result.mastery == "unknown"

# Test: needs_human_review for ambiguous
def test_eval_ambiguous_triggers_review():
    result = evaluator.evaluate_self_explanation(
        "formal",
        "compact는 유한 부분덮개와 관련된 개념이다."  # Some terms but vague
    )
    assert result.needs_human_review is True
```

---

## Artifact Tests

### Confusion map artifact generation

```python
def test_confusion_map_artifact_written(card_env):
    """After complete session, confusion_map.json exists in session dir."""
    # Create session, run through all steps
    # Verify runs/{session_id}/confusion_map.json exists
    # Verify it validates against ConfusionMap schema
    # Verify it has expected fields populated

def test_mapping_results_artifact_written(card_env):
    """After mapping step, mapping_results.json exists."""
    # Submit all 3 mapping tasks
    # Verify runs/{session_id}/mapping_results.json exists
    # Verify 3 results with expected structure

def test_mapping_tasks_artifact_written(card_env):
    """After session creation, mapping_tasks.json exists."""
    # Verify runs/{session_id}/mapping_tasks.json exists
    # Verify 3 tasks generated from card
```

### STUDY.md confusion summary roundtrip

```python
def test_study_md_confusion_summary_roundtrip(tmp_path):
    """Write confusion summary, parse it back, verify equality."""
    # Write STUDY.md with confusion summary
    # Parse it back
    # Verify mapping_status, active_misconceptions, next_recall_trigger match

def test_study_md_without_confusion_summary(tmp_path):
    """Parse STUDY.md without confusion summary section → empty defaults."""
    # Write old-format STUDY.md (no confusion summary)
    # Parse it
    # Verify confusion fields are empty defaults
```

---

## Frontend Checks

### Build verification

```bash
cd apps/web && npm run build
```

Must succeed with zero TypeScript errors.

### Type checking (if available)

```bash
cd apps/web && npx tsc --noEmit
```

### Existing E2E tests

```bash
cd apps/web && npx playwright test
```

Note: Playwright tests require running backend + frontend. They test basic page loads
and recall session flow. They do NOT yet test the study session flow.

### Manual browser smoke (15-point checklist)

See `05_FRONTEND_UX_PLAN.md` for the full 15-point checklist.

Abbreviated version:
1. /study/compactness loads → session created
2. Diagnosis submit → advance
3. Prerequisites check → advance
4. Representations view + self-explain → advance
5. **Mapping tasks displayed** (3 tasks)
6. **Mapping task 1 submit → feedback + confusion map update**
7. **Mapping task 3 submit → auto-advance to misconceptions**
8. Misconception quiz → advance
9. Recall submit → advance
10. Summary shows mastery + **confusion map summary**
11. Complete → STUDY.md updated
12. **Refresh at mapping step → restores correctly**
13. **Confusion map panel visible alongside mapping/recall**
14. Dashboard reflects new session
15. Old /recall page still works (regression check)

---

## Golden Run Smoke

### File: `tests/test_golden_run_smoke.py`

A single end-to-end test that simulates the demo golden run (doc 10):

```python
def test_golden_run_compactness(card_env):
    """
    Full compactness demo: create session → diagnosis → prerequisites →
    representations → mapping (with known failure) → misconceptions →
    recall → complete.

    Verifies:
    - Mapping task evaluation produces expected failure
    - Misconception tags match expected
    - Confusion map has expected structure
    - STUDY.md updated correctly
    - All artifacts written
    """
    # Step 1: Create session
    resp = client.post("/api/study-session", json={...})
    session_id = resp.json()["session_id"]

    # Step 2: Diagnosis
    client.post(f"/api/study-session/{session_id}/diagnose", json={...})

    # Step 3: Prerequisites
    client.post(f"/api/study-session/{session_id}/advance", json={...})

    # Step 4: Representations + self-explain
    client.post(f"/api/study-session/{session_id}/self-explain", json={
        "representation_type": "formal",
        "explanation": "compact는 모든 열린 덮개에 유한 부분덮개가 존재하는 성질이다."
    })
    # ... advance ...

    # Step 5: Mapping — THE KEY TEST
    tasks = client.get(f"/api/study-session/{session_id}/mapping-tasks")
    formal_to_ce_task = tasks.json()["tasks"][0]

    result = client.post(f"/api/study-session/{session_id}/mapping-submit", json={
        "task_id": formal_to_ce_task["task_id"],
        "learner_response": "(0,1)은 닫혀 있지 않아서 compact하지 않습니다."
    })
    assert result.json()["passed"] is False
    assert "misuses_heine_borel" in result.json()["misconception_tags"]

    # Verify confusion map
    cmap = client.get(f"/api/study-session/{session_id}/confusion-map")
    assert any(
        e["task_type"] == "formal_to_counterexample" and not e["passed"]
        for e in cmap.json()["mapping_edges"]
    )

    # ... complete remaining steps ...

    # Verify STUDY.md
    study_md = Path(study_md_path).read_text()
    assert "compactness" in study_md
    assert "formal → counterexample" in study_md  # confusion summary

    # Verify artifacts
    session_dir = runs_dir / session_id
    assert (session_dir / "confusion_map.json").exists()
    assert (session_dir / "mapping_results.json").exists()
    assert (session_dir / "mapping_tasks.json").exists()
```

---

## CI-Like Command Sequence

Run these commands in order after implementation:

```bash
# 1. Unit tests (fast, no API)
python -m pytest tests/test_ground_truth_cards.py tests/test_data_models.py tests/test_rubric_models.py -v

# 2. Evaluator tests
python -m pytest tests/test_deterministic_evaluator.py tests/test_evaluator_compactness.py -v

# 3. Engine tests
python -m pytest tests/test_mapping_task_engine.py tests/test_confusion_map.py -v

# 4. Mastery + STUDY.md tests
python -m pytest tests/test_mastery_scored_reps.py tests/test_study_md_confusion_summary.py -v

# 5. Service tests
python -m pytest tests/test_card_service.py -v

# 6. API tests
python -m pytest tests/test_api_mapping_tasks.py tests/test_api_confusion_map.py -v

# 7. Golden run smoke
python -m pytest tests/test_golden_run_smoke.py -v

# 8. Human agreement eval
python -m pytest tests/test_human_agreement_eval.py -v

# 9. ALL existing tests (regression check)
python -m pytest tests/ -q

# 10. Frontend build
cd apps/web && npm run build

# 11. Existing eval suite
python evals/run_grading_eval.py --grader mock

# 12. Human agreement computation (if rater data exists)
python evals/human_agreement/compute_agreement.py
```

**Pass criteria**: Steps 1-10 must pass. Steps 11-12 should pass but are informational.

---

## Test File Summary

### New test files

| File | Est. Tests | Priority |
|------|-----------|----------|
| `tests/test_ground_truth_cards.py` | 8-10 | P0 |
| `tests/test_data_models.py` | 12-15 | P0 |
| `tests/test_rubric_models.py` | 6-8 | P0 |
| `tests/test_deterministic_evaluator.py` | 15-20 | P0 |
| `tests/test_evaluator_compactness.py` | 10-12 | P0 |
| `tests/test_mapping_task_engine.py` | 8-10 | P0 |
| `tests/test_confusion_map.py` | 10-12 | P0 |
| `tests/test_mastery_scored_reps.py` | 5-6 | P0 |
| `tests/test_study_md_confusion_summary.py` | 8-10 | P0 |
| `tests/test_card_service.py` | 5-6 | P0 |
| `tests/test_api_mapping_tasks.py` | 10-12 | P0 |
| `tests/test_api_confusion_map.py` | 6-8 | P0 |
| `tests/test_golden_run_smoke.py` | 1 (complex) | P0 |
| `tests/test_human_agreement_eval.py` | 6-8 | P1 |

**Total new tests**: ~110-147

---

## Implementation Checklist

- [ ] Write test_ground_truth_cards.py
- [ ] Write test_data_models.py
- [ ] Write test_rubric_models.py
- [ ] Write test_deterministic_evaluator.py
- [ ] Write test_evaluator_compactness.py
- [ ] Write test_mapping_task_engine.py
- [ ] Write test_confusion_map.py
- [ ] Write test_mastery_scored_reps.py
- [ ] Write test_study_md_confusion_summary.py
- [ ] Write test_card_service.py
- [ ] Write test_api_mapping_tasks.py
- [ ] Write test_api_confusion_map.py
- [ ] Write test_golden_run_smoke.py
- [ ] Write test_human_agreement_eval.py
- [ ] Verify all existing tests pass after changes
- [ ] Verify frontend build succeeds
- [ ] Run CI-like command sequence end-to-end
- [ ] Manual browser smoke (15 points)

## Acceptance Criteria

1. All new tests pass
2. All existing tests pass (zero regressions)
3. Frontend builds with no TypeScript errors
4. Golden run smoke produces expected outputs
5. CI-like sequence completes without failures
6. Manual browser smoke passes all 15 points

## Risks

- Existing study session tests may break due to step numbering change.
  Mitigate: identify affected assertions early, update before running full suite.
- Mastery scoring change may affect due/weak API tests.
  Mitigate: check which tests assert overall_mastery based on all 5 reps.

## Rollback Plan

- All new test files are additive. Delete to rollback.
- If existing tests break: fix the root cause (likely step numbering or mastery scoring).
  The test failures indicate real code issues, not test issues.

## Dependencies

- Depends on: 03 (Models), 04 (Backend), 05 (Frontend), 06 (Evaluator), 07 (Human Eval)
- This document should be referenced during every implementation step.

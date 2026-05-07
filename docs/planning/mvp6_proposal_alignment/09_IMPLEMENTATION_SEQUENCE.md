# 09 — Implementation Sequence

## Purpose

Break MVP6 implementation into small, safe, testable steps. Each step can be
implemented in a single Claude Code session with clear rollback boundaries.

---

## Step 1: Ground Truth Card — Data Model + JSON

**Objective**: Define the GroundTruthCard Pydantic model and create the first card.

**Files to add**:
- `src/gonghaebun/models/ground_truth_card.py`
- `data/gonghaebun/default/cards/real_analysis/compactness.card.json`
- `tests/test_ground_truth_cards.py`

**Files to edit**: None

**Tests to run**:
```bash
python -m pytest tests/test_ground_truth_cards.py -v
python -m pytest tests/ -q  # regression check
```

**Acceptance criteria**:
- Card JSON loads and validates against Pydantic model
- All required fields present, correct types
- prerequisite_concepts are valid slugs
- 3 allowed_mapping_tasks, >= 2 counterexample_cards, >= 3 misconception_cards
- All existing tests pass

**Rollback**: Delete 3 new files.

---

## Step 2: Mapping + Confusion Map + Rubric + EvalOutput Models

**Objective**: Define all remaining Pydantic models for MVP6.

**Files to add**:
- `src/gonghaebun/models/mapping_models.py`
- `src/gonghaebun/models/confusion_map.py`
- `src/gonghaebun/models/rubric.py`
- `src/gonghaebun/models/evaluation_output.py`
- `tests/test_data_models.py`
- `tests/test_rubric_models.py`

**Files to edit**: None

**Tests to run**:
```bash
python -m pytest tests/test_data_models.py tests/test_rubric_models.py -v
python -m pytest tests/ -q
```

**Acceptance criteria**:
- All models instantiate with valid data
- All models reject invalid data (validation errors)
- Serialization to/from JSON works
- All existing tests pass

**Rollback**: Delete 6 new files.

---

## Step 3: Compactness Rubric JSON

**Objective**: Create the rubric data file for compactness.

**Files to add**:
- `data/gonghaebun/default/cards/real_analysis/compactness.rubric.json`

**Files to edit**: None

**Tests to run**:
```bash
python -m pytest tests/test_rubric_models.py -v  # add rubric load test
```

**Acceptance criteria**:
- Rubric JSON loads and validates against ConceptRubric model
- All 8 task_rubrics present (3 self-explain-scored + 3 mapping + recall + misconception_quiz)
- required_terms populated for each task
- misconception_checks have valid trigger patterns
- Global misconception_checks populated

**Rollback**: Delete 1 JSON file.

---

## Step 4: Deterministic Evaluator

**Objective**: Implement the card-grounded deterministic evaluator.

**Files to add**:
- `src/gonghaebun/grading/deterministic_evaluator.py`
- `tests/test_deterministic_evaluator.py`
- `tests/test_evaluator_compactness.py`

**Files to edit**: None

**Tests to run**:
```bash
python -m pytest tests/test_deterministic_evaluator.py tests/test_evaluator_compactness.py -v
python -m pytest tests/ -q
```

**Acceptance criteria**:
- Term coverage scoring works (Korean + English)
- Misconception detection works (regex patterns)
- Scoring formula correct (coverage * (1 - penalty))
- needs_human_review triggers for ambiguous cases
- Korean normalization strips particles correctly
- Compactness-specific test cases pass (correct, partial, misconception, empty)
- All existing tests pass

**Rollback**: Delete 3 new files.

---

## Step 5: Card + Rubric Loader Service

**Objective**: Backend service to load cards and rubrics from disk.

**Files to add**:
- `apps/api/services/card_service.py`
- `tests/test_card_service.py`

**Files to edit**:
- `apps/api/config.py` — add CARDS_DIR

**Tests to run**:
```bash
python -m pytest tests/test_card_service.py -v
python -m pytest tests/ -q
```

**Acceptance criteria**:
- `load_ground_truth_card("compactness")` returns valid GroundTruthCard
- `load_rubric("compactness")` returns valid ConceptRubric
- 404-style error for nonexistent concept
- Caching works (second call doesn't re-read disk)
- CARDS_DIR config respected
- All existing tests pass

**Rollback**: Delete 2 new files, revert config.py (1 line).

---

## Step 6: Confusion Map Service

**Objective**: Implement confusion map lifecycle (init, per-step updates, persistence).

**Files to add**:
- `apps/api/services/confusion_map_service.py`
- `tests/test_confusion_map.py`

**Files to edit**: None

**Tests to run**:
```bash
python -m pytest tests/test_confusion_map.py -v
python -m pytest tests/ -q
```

**Acceptance criteria**:
- initialize_confusion_map creates empty map with correct concept_id
- update_from_diagnosis adds mastery estimates and misconception cues
- update_from_prerequisites adds self-reported mastery
- update_from_self_explanation updates quality signals
- update_from_mapping adds mapping edges, misconception tags, evidence, triggers
- update_from_misconceptions adds quiz results
- update_from_recall updates addressed triggers
- persist + load roundtrip works
- All existing tests pass

**Rollback**: Delete 2 new files.

---

## Step 7: Mapping Task Engine Service

**Objective**: Implement mapping task generation and evaluation.

**Files to add**:
- `apps/api/services/mapping_service.py`
- `tests/test_mapping_task_engine.py`

**Files to edit**: None

**Tests to run**:
```bash
python -m pytest tests/test_mapping_task_engine.py -v
python -m pytest tests/ -q
```

**Acceptance criteria**:
- generate_mapping_tasks produces 3 tasks from card
- Task IDs are deterministic (session_id + task_type)
- evaluate_mapping_submission uses deterministic evaluator
- Evaluation produces correct EvaluationOutput for known inputs
- update_confusion_map_from_mapping integrates with confusion map service
- All existing tests pass

**Rollback**: Delete 2 new files.

---

## Step 8: Mapping + Confusion Map API Router

**Objective**: Expose mapping tasks and confusion map via HTTP.

**Files to add**:
- `apps/api/routers/mapping.py`
- `tests/test_api_mapping_tasks.py`
- `tests/test_api_confusion_map.py`

**Files to edit**:
- `apps/api/main.py` — mount mapping router
- `apps/api/schemas/api_schemas.py` — add mapping + confusion map schemas

**Tests to run**:
```bash
python -m pytest tests/test_api_mapping_tasks.py tests/test_api_confusion_map.py -v
python -m pytest tests/ -q
```

**Acceptance criteria**:
- GET /api/study-session/{id}/mapping-tasks returns 3 tasks
- POST /api/study-session/{id}/mapping-submit evaluates and returns feedback
- GET /api/study-session/{id}/confusion-map returns current state
- Error handling: 404 for not found, 400 for wrong step, 422 for empty response
- All existing tests pass

**Rollback**: Delete 3 new files, revert main.py + api_schemas.py.

---

## Step 9: Wire Confusion Map into Study Session Steps

**Objective**: Update existing step handlers to update confusion map.

**Files to add**: None

**Files to edit**:
- `apps/api/services/study_session_service.py` — add confusion map updates in diagnose, advance, self-explain, recall, complete
- `apps/api/routers/study_session.py` — pass confusion map data through

**Tests to run**:
```bash
python -m pytest tests/test_api_study_session.py -v
python -m pytest tests/test_study_session_complete.py -v
python -m pytest tests/ -q
```

**Acceptance criteria**:
- Confusion map initialized on session creation
- Updated after each step handler call
- confusion_map.json written to disk after each update
- Session state includes confusion_map_initialized flag
- All existing study session tests pass (may need updates for new response fields)

**Rollback**: Revert study_session_service.py and study_session.py to previous state.

---

## Step 10: 7-Step Session + Mapping Step in Backend

**Objective**: Add mapping as step 3, shift misconceptions/recall/summary to 4/5/6.

**Files to edit**:
- `apps/api/services/study_session_service.py` — step enum, advance logic
- `apps/api/routers/study_session.py` — step validation

**Tests to run**:
```bash
python -m pytest tests/test_api_study_session.py -v
python -m pytest tests/test_study_session_complete.py -v
python -m pytest tests/ -q
```

**Acceptance criteria**:
- Session creation initializes 7-step flow
- Step 3 is mapping, step 4 is misconceptions, etc.
- advance from representations → mapping
- advance from mapping → misconceptions (when all 3 tasks submitted)
- Legacy sessions (no mapping step) handled gracefully
- Existing study session tests updated for new step numbers

**Rollback**: Revert step numbering in study_session_service.py.

---

## Step 11: Mastery Scoring Change

**Objective**: Exclude intuitive/visual from overall mastery calculation.

**Files to edit**:
- `src/gonghaebun/study_loop/mastery.py` — add MASTERY_SCORED_REPS
- `src/gonghaebun/study_md/writer.py` — use MASTERY_SCORED_REPS in apply_patch

**Files to add**:
- `tests/test_mastery_scored_reps.py`

**Tests to run**:
```bash
python -m pytest tests/test_mastery_scored_reps.py -v
python -m pytest tests/test_api_due.py tests/test_api_weak.py -v
python -m pytest tests/ -q
```

**Acceptance criteria**:
- Overall mastery = weakest of formal, counterexample, proof_schema only
- intuitive=unknown + visual=unknown does NOT drag overall to unknown
- Existing due/weak tests updated if they depend on all-5-rep mastery
- All existing tests pass

**Rollback**: Revert mastery.py + writer.py changes.

---

## Step 12: STUDY.md Confusion Summary Section

**Objective**: Extend parser/writer for Confusion Summary in STUDY.md.

**Files to add**:
- `tests/test_study_md_confusion_summary.py`

**Files to edit**:
- `src/gonghaebun/study_md/parser.py` — parse Confusion Summary section
- `src/gonghaebun/study_md/writer.py` — write Confusion Summary section

**Tests to run**:
```bash
python -m pytest tests/test_study_md_confusion_summary.py -v
python -m pytest tests/test_study_md_validate.py -v
python -m pytest tests/ -q
```

**Acceptance criteria**:
- Parser reads Confusion Summary (mapping table, misconceptions, trigger)
- Parser returns empty defaults when section is missing (backward compat)
- Writer produces valid Confusion Summary from ConfusionMap data
- Writer omits section when no confusion data available
- Roundtrip: write → parse → compare matches
- Validator does not flag Confusion Summary as error
- All existing tests pass

**Rollback**: Revert parser.py + writer.py changes.

---

## Step 13: Session Writer — New Artifacts

**Objective**: Write confusion_map.json, mapping_tasks.json, mapping_results.json.

**Files to edit**:
- `src/gonghaebun/study_loop/session_writer.py` — add artifact writes

**Tests to run**:
```bash
python -m pytest tests/test_session_writer.py -v
python -m pytest tests/ -q
```

**Acceptance criteria**:
- confusion_map.json written to session dir
- mapping_tasks.json written on session creation
- mapping_results.json written after mapping step
- Existing artifacts still written correctly
- All existing tests pass

**Rollback**: Revert session_writer.py changes.

---

## Step 14: Frontend — Types + API Client

**Objective**: Add TypeScript types and API client functions for mapping + confusion map.

**Files to edit**:
- `apps/web/src/api/types.ts` — add mapping + confusion map types
- `apps/web/src/api/client.ts` — add 3 new functions

**Tests to run**:
```bash
cd apps/web && npm run build
```

**Acceptance criteria**:
- TypeScript types compile without errors
- API client functions exported correctly
- Frontend build succeeds
- No existing functionality broken

**Rollback**: Revert types.ts + client.ts changes.

---

## Step 15: Frontend — ConfusionMapPanel Component

**Objective**: Create the confusion map side panel component.

**Files to add**:
- `apps/web/src/components/study/ConfusionMapPanel.tsx`

**Files to edit**:
- `apps/web/src/styles.css` — add panel styles (if needed)

**Tests to run**:
```bash
cd apps/web && npm run build
```

**Acceptance criteria**:
- Component renders with sample data
- Shows prerequisite nodes, mapping edges, misconception tags, triggers, evidence
- Loading/empty states handled
- Build succeeds

**Rollback**: Delete new file.

---

## Step 16: Frontend — MappingCheckStep Component

**Objective**: Create the mapping task step component.

**Files to add**:
- `apps/web/src/components/study/MappingCheckStep.tsx`

**Tests to run**:
```bash
cd apps/web && npm run build
```

**Acceptance criteria**:
- Component renders 3 tasks sequentially
- Submit triggers API call and shows feedback
- Read-only mode for past steps
- Build succeeds

**Rollback**: Delete new file.

---

## Step 17: Frontend — StudySession 7-Step + Split Layout

**Objective**: Update StudySession to 7 steps with confusion map panel.

**Files to edit**:
- `apps/web/src/pages/StudySession.tsx` — 7 steps, mapping step case, split layout, confusion map state
- `apps/web/src/components/study/StudyStepper.tsx` — 7 step labels
- `apps/web/src/components/study/SessionSummaryStep.tsx` — confusion summary, learning aid labels
- `apps/web/src/styles.css` — split layout CSS

**Tests to run**:
```bash
cd apps/web && npm run build
# Manual browser smoke (15 points from doc 05)
```

**Acceptance criteria**:
- 7-step stepper displays correctly
- Mapping step renders MappingCheckStep
- Confusion map panel shows alongside steps 3-5
- Session summary shows confusion summary
- State restoration works on refresh
- Build succeeds

**Rollback**: Revert all 4 edited files.

---

## Step 18: Human Agreement Eval Harness

**Objective**: Create the evaluation harness scaffolding.

**Files to add**:
- `evals/human_agreement/README.md`
- `evals/human_agreement/compactness_answers.csv`
- `evals/human_agreement/rubric_v1.json`
- `evals/human_agreement/rater_a.csv` (template)
- `evals/human_agreement/rater_b.csv` (template)
- `evals/human_agreement/compute_agreement.py`
- `tests/test_human_agreement_eval.py`

**Tests to run**:
```bash
python -m pytest tests/test_human_agreement_eval.py -v
```

**Acceptance criteria**:
- compute_agreement.py runs with sample data
- Agreement metrics computed correctly
- Report generated in markdown format
- All metric computations testable

**Rollback**: Delete entire `evals/human_agreement/` directory + test file.

---

## Step 19: Golden Run Smoke Test

**Objective**: Implement end-to-end golden run test.

**Files to add**:
- `tests/test_golden_run_smoke.py`

**Tests to run**:
```bash
python -m pytest tests/test_golden_run_smoke.py -v
python -m pytest tests/ -q  # full regression
```

**Acceptance criteria**:
- Golden run completes without errors
- Known learner answer produces expected failure (formal→CE mapping)
- Misconception tags match expected set
- Confusion map has expected structure
- STUDY.md updated with confusion summary
- All artifacts written
- All existing tests pass

**Rollback**: Delete test file.

---

## Step 20: Full Verification

**Objective**: Run the complete CI-like command sequence (doc 08).

**Files to edit**: None (only if fixes needed)

**Commands**:
```bash
# All tests
python -m pytest tests/ -q

# Frontend build
cd apps/web && npm run build

# Eval suite
python evals/run_grading_eval.py --grader mock

# Human agreement (if rater data available)
python evals/human_agreement/compute_agreement.py
```

**Acceptance criteria**:
- Zero test failures
- Zero build errors
- Eval suite passes
- Manual browser smoke passes all 15 points

---

## Summary

| Step | Description | Files Added | Files Modified | Est. Tests |
|------|-------------|-------------|----------------|-----------|
| 1 | Ground Truth Card model + JSON | 3 | 0 | 8-10 |
| 2 | Mapping/Confusion/Rubric/EvalOutput models | 6 | 0 | 18-23 |
| 3 | Compactness rubric JSON | 1 | 0 | 1-2 |
| 4 | Deterministic evaluator | 3 | 0 | 25-32 |
| 5 | Card loader service | 2 | 1 | 5-6 |
| 6 | Confusion map service | 2 | 0 | 10-12 |
| 7 | Mapping task engine service | 2 | 0 | 8-10 |
| 8 | API router | 3 | 2 | 16-20 |
| 9 | Wire confusion map into steps | 0 | 2 | 0 (existing) |
| 10 | 7-step session | 0 | 2 | 0 (existing) |
| 11 | Mastery scoring change | 1 | 2 | 5-6 |
| 12 | STUDY.md confusion summary | 1 | 2 | 8-10 |
| 13 | Session writer artifacts | 0 | 1 | 0 (existing) |
| 14 | Frontend types + client | 0 | 2 | 0 (build) |
| 15 | ConfusionMapPanel | 1 | 1 | 0 (build) |
| 16 | MappingCheckStep | 1 | 0 | 0 (build) |
| 17 | StudySession 7-step | 0 | 4 | 0 (manual) |
| 18 | Human agreement harness | 7 | 0 | 6-8 |
| 19 | Golden run smoke | 1 | 0 | 1 |
| 20 | Full verification | 0 | 0 | 0 |
| **Total** | | **34** | **19** | **~110-140** |

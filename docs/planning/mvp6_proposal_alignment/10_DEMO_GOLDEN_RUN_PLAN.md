# 10 — Demo Golden Run Plan

## Purpose

Define a deterministic demo scenario for the compactness vertical slice.
This demo validates the entire MVP6 loop: learner answer → evaluator feedback →
failed mapping edge → confusion map update → next recall trigger → STUDY.md summary.

---

## Demo Scenario: "(0,1)은 닫혀 있지 않아서 compact하지 않습니다."

### Context

A learner is studying compactness for the first time. At the mapping step, they are
asked to use the formal definition (open cover / finite subcover) to explain why (0,1)
is not compact. Instead, they use a Heine-Borel shortcut (closedness argument).

This is a diagnostic failure: the learner knows the conclusion but cannot perform the
formal → counterexample mapping using the correct reasoning pathway.

---

## Initial State

### STUDY.md

Either empty or no compactness entry:
```markdown
# STUDY.md
_last_updated: 2026-05-07_

---
```

### Ground Truth Card

`data/gonghaebun/default/cards/real_analysis/compactness.card.json` exists with:
- definition_card: open cover / finite subcover formulation
- counterexample_cards: includes (0,1) in R with open cover explanation
- proof_schema_card: Heine-Borel equivalence proof outline
- misconception_cards: includes `misuses_heine_borel`, `bounded_implies_compact`
- allowed_mapping_tasks: 3 tasks (formal→CE, CE→formal, formal+CE→proof)

### Source file

`data/gonghaebun/default/sources/sample_source.md` exists.

### Grading mode

Mock grader (LLM_DISABLED=1). Deterministic evaluator handles mapping + confusion map.

---

## Demo Script

### Step 1: Create Session

**API call**:
```
POST /api/study-session
{
  "concept_id": "compactness",
  "source_path": "sample_source.md"
}
```

**Expected response**:
```json
{
  "session_id": "<uuid>",
  "concept_id": "compactness",
  "representations": { ... },
  "prerequisites": [ ... ],
  "misconceptions": [ ... ],
  "current_step": 0
}
```

**Expected artifacts created**:
- `runs/{session_id}/study_session_state.json`
- `runs/{session_id}/mapping_tasks.json` (3 tasks from card)
- `runs/{session_id}/confusion_map.json` (empty initial)
- All existing Stage 0-7 artifacts

---

### Step 2: Diagnosis

**API call**:
```
POST /api/study-session/{session_id}/diagnose
{
  "prior_knowledge": "compact가 뭔지는 대충 아는데, 왜 (0,1)이 compact가 아닌지 증명을 못 하겠어요.",
  "pain_points": "open cover 개념이 잘 안 와닿아요."
}
```

**Expected confusion map after**:
```json
{
  "concept_id": "compactness",
  "prerequisite_nodes": [
    {"concept_id": "metric_space", "mastery": "unknown"},
    {"concept_id": "open_cover", "mastery": "unknown"},
    {"concept_id": "heine_borel", "mastery": "unknown"}
  ],
  "mapping_edges": [],
  "misconception_tags": [],
  "next_recall_triggers": [],
  "evidence_snippets": [],
  "last_updated_step": "diagnosis"
}
```

---

### Step 3: Prerequisites

**API call**:
```
POST /api/study-session/{session_id}/advance
{
  "step": "prerequisites"
}
```

(Learner self-checks are handled in frontend; backend just advances step.)

---

### Step 4: Representations + Self-Explain

**API calls** (self-explain for formal + proof_schema at minimum):
```
POST /api/study-session/{session_id}/self-explain
{
  "representation_type": "formal",
  "explanation": "compact 집합은 모든 열린 덮개에 대해 유한 부분덮개가 존재하는 집합이다."
}
```

**Expected self-explain result for formal**:
```json
{
  "score": 0.75,
  "mastery": "partial",
  "missing_elements": ["every"],
  "misconception_tags": [],
  "feedback": "잘 설명했습니다. '모든' 양화사를 더 명확히 해 주세요."
}
```

```
POST /api/study-session/{session_id}/self-explain
{
  "representation_type": "proof_schema",
  "explanation": "Heine-Borel: closed and bounded이면 compact이다. 증명은 잘 모르겠다."
}
```

**Expected self-explain result for proof_schema**:
```json
{
  "score": 0.35,
  "mastery": "unknown",
  "missing_elements": ["Bolzano-Weierstrass", "convergent subsequence", "finite subcover construction"],
  "misconception_tags": [],
  "feedback": "증명 단계가 부족합니다. 핵심 단계를 포함해 주세요."
}
```

Advance to mapping step after required self-explanations submitted.

---

### Step 5: Mapping Tasks — THE KEY DEMO MOMENT

**Retrieve tasks**:
```
GET /api/study-session/{session_id}/mapping-tasks
```

**Response**:
```json
{
  "session_id": "...",
  "concept_id": "compactness",
  "tasks": [
    {
      "task_id": "{session_id}_formal_to_counterexample",
      "task_type": "formal_to_counterexample",
      "prompt": "옹골성의 정의를 사용하여 (0,1)이 왜 compact하지 않은지 설명하세요.",
      "source_representations": ["formal"],
      "target_representation": "counterexample"
    },
    {
      "task_id": "{session_id}_counterexample_to_formal",
      "task_type": "counterexample_to_formal",
      "prompt": "(0,1)이 compact하지 않다는 사실로부터, compact 집합이 반드시 가져야 하는 성질을 설명하세요.",
      "source_representations": ["counterexample"],
      "target_representation": "formal"
    },
    {
      "task_id": "{session_id}_formal_counterexample_to_proof_schema",
      "task_type": "formal_counterexample_to_proof_schema",
      "prompt": "정의와 반례를 활용하여, Heine-Borel 정리의 증명 구조를 개략적으로 설명하세요.",
      "source_representations": ["formal", "counterexample"],
      "target_representation": "proof_schema"
    }
  ]
}
```

**Submit Task 1 — THE DIAGNOSTIC ANSWER**:
```
POST /api/study-session/{session_id}/mapping-submit
{
  "task_id": "{session_id}_formal_to_counterexample",
  "learner_response": "(0,1)은 닫혀 있지 않아서 compact하지 않습니다."
}
```

**Expected response**:
```json
{
  "task_id": "...",
  "task_type": "formal_to_counterexample",
  "score": 0.25,
  "passed": false,
  "missing_elements": ["open cover", "finite subcover", "(1/n, 1)"],
  "misconception_tags": ["misuses_heine_borel", "missing_open_cover_argument"],
  "mapping_failures": ["formal_to_counterexample"],
  "feedback": "Heine-Borel은 R^n에서의 충분조건입니다. open cover를 사용하여 직접 설명해야 합니다. '열린 덮개'와 '유한 부분덮개'를 포함한 설명이 필요합니다.",
  "next_recall_trigger": "open cover로 (0,1)이 compact하지 않음을 설명하라.",
  "confusion_map": {
    "concept_id": "compactness",
    "mapping_edges": [
      {"from_rep": "formal", "to_rep": "counterexample", "task_type": "formal_to_counterexample", "passed": false, "score": 0.25}
    ],
    "misconception_tags": ["misuses_heine_borel", "missing_open_cover_argument"],
    "next_recall_triggers": ["open cover로 (0,1)이 compact하지 않음을 설명하라."],
    "evidence_snippets": [
      {
        "step": "mapping",
        "task_type": "formal_to_counterexample",
        "learner_text": "(0,1)은 닫혀 있지 않아서 compact하지 않습니다.",
        "issue": "Uses closedness (Heine-Borel shortcut) instead of open cover argument"
      }
    ],
    "last_updated_step": "mapping"
  }
}
```

**Diagnosis explanation**:
- The conclusion "(0,1) is not compact" is correct under Heine-Borel in R.
- However, the task asks to explain using the **formal definition** (open cover / finite subcover).
- The learner used closedness instead of constructing an open cover without finite subcover.
- This is a **failed Formal → Counterexample mapping**.
- Tags: `misuses_heine_borel` (uses Heine-Borel when open cover is required), `missing_open_cover_argument` (no mention of open cover).
- Next recall trigger: direct the learner to explain using open cover.

**Submit Task 2** (correct answer):
```
POST /api/study-session/{session_id}/mapping-submit
{
  "task_id": "{session_id}_counterexample_to_formal",
  "learner_response": "(0,1)이 compact하지 않으므로, compact 집합은 모든 열린 덮개에 대해 유한 부분덮개가 존재해야 합니다."
}
```

**Expected**: score >= 0.70, passed = true.

**Submit Task 3** (partial answer):
```
POST /api/study-session/{session_id}/mapping-submit
{
  "task_id": "{session_id}_formal_counterexample_to_proof_schema",
  "learner_response": "Heine-Borel은 closed and bounded이면 compact라는 것인데, 증명 구조는 잘 모르겠습니다."
}
```

**Expected**: score < 0.50, passed = false, missing proof steps.

---

### Step 6: Misconceptions

```
POST /api/study-session/{session_id}/advance
```

(Misconception quiz is handled by the existing step with card-grounded T/F questions.)

---

### Step 7: Recall

```
POST /api/study-session/{session_id}/recall
{
  "response": "옹골성은 모든 열린 덮개에 대해 유한 부분덮개가 존재하는 성질이다. (0,1)은 닫혀 있지 않아서 compact하지 않다. Heine-Borel에 의해 R에서 compact는 닫히고 유계인 것이다."
}
```

**Expected**: Recall still shows Heine-Borel shortcut for (0,1). Confusion map records
that the original trigger was not fully addressed.

---

### Step 8: Complete

```
POST /api/study-session/{session_id}/complete
```

**Expected completion response** includes:
```json
{
  "mastery_updates": [
    {"representation_type": "formal", "before": "unknown", "after": "partial"},
    {"representation_type": "counterexample", "before": "unknown", "after": "unknown"},
    {"representation_type": "proof_schema", "before": "unknown", "after": "unknown"}
  ],
  "overall_mastery": "unknown",
  "next_review": "2026-05-09",
  "confusion_summary": {
    "failed_mappings": ["formal_to_counterexample", "formal_counterexample_to_proof_schema"],
    "active_misconceptions": ["misuses_heine_borel", "missing_open_cover_argument"],
    "next_recall_trigger": "open cover로 (0,1)이 compact하지 않음을 설명하라."
  }
}
```

---

## Expected JSON Artifacts

### confusion_map.json (final)

```json
{
  "concept_id": "compactness",
  "session_id": "...",
  "prerequisite_nodes": [
    {"concept_id": "metric_space", "mastery": "unknown"},
    {"concept_id": "open_cover", "mastery": "unknown"},
    {"concept_id": "heine_borel", "mastery": "unknown"}
  ],
  "mapping_edges": [
    {"from_rep": "formal", "to_rep": "counterexample", "task_type": "formal_to_counterexample", "passed": false, "score": 0.25},
    {"from_rep": "counterexample", "to_rep": "formal", "task_type": "counterexample_to_formal", "passed": true, "score": 0.80},
    {"from_rep": "formal_counterexample", "to_rep": "proof_schema", "task_type": "formal_counterexample_to_proof_schema", "passed": false, "score": 0.30}
  ],
  "misconception_tags": ["misuses_heine_borel", "missing_open_cover_argument"],
  "next_recall_triggers": [
    "open cover로 (0,1)이 compact하지 않음을 설명하라.",
    "Heine-Borel 증명에서 유한 부분덮개를 구성하는 핵심 단계를 설명하라."
  ],
  "evidence_snippets": [
    {
      "step": "mapping",
      "task_type": "formal_to_counterexample",
      "learner_text": "(0,1)은 닫혀 있지 않아서 compact하지 않습니다.",
      "issue": "Uses closedness (Heine-Borel shortcut) instead of open cover argument"
    }
  ],
  "last_updated_step": "recall",
  "created_at": "2026-05-08T...",
  "updated_at": "2026-05-08T..."
}
```

### mapping_results.json

```json
[
  {
    "task_id": "..._formal_to_counterexample",
    "task_type": "formal_to_counterexample",
    "learner_response": "(0,1)은 닫혀 있지 않아서 compact하지 않습니다.",
    "score": 0.25,
    "passed": false,
    "missing_elements": ["open cover", "finite subcover", "(1/n, 1)"],
    "incorrect_claims": [],
    "misconception_tags": ["misuses_heine_borel", "missing_open_cover_argument"],
    "mapping_failures": ["formal_to_counterexample"],
    "feedback": "...",
    "next_recall_trigger": "open cover로 (0,1)이 compact하지 않음을 설명하라.",
    "needs_human_review": false,
    "evaluated_at": "2026-05-08T..."
  },
  {
    "task_id": "..._counterexample_to_formal",
    "task_type": "counterexample_to_formal",
    "score": 0.80,
    "passed": true,
    "mapping_failures": [],
    "misconception_tags": []
  },
  {
    "task_id": "..._formal_counterexample_to_proof_schema",
    "task_type": "formal_counterexample_to_proof_schema",
    "score": 0.30,
    "passed": false,
    "mapping_failures": ["formal_counterexample_to_proof_schema"]
  }
]
```

---

## Expected STUDY.md After Demo

```markdown
# STUDY.md
_last_updated: 2026-05-08_

---

## compactness

**domain**: real_analysis
**overall_mastery**: unknown
**next_review**: 2026-05-09

### Representations

| type           | mastery | last_reviewed |
|----------------|---------|---------------|
| formal         | partial | 2026-05-08    |
| intuitive      | unknown | —             |
| visual         | unknown | —             |
| counterexample | unknown | 2026-05-08    |
| proof_schema   | unknown | 2026-05-08    |

### Prerequisites

| concept        | mastery | note |
|----------------|---------|------|
| metric_space   | unknown |      |
| open_cover     | unknown |      |
| heine_borel    | unknown |      |

### Misconceptions Encountered

- [x] "Heine-Borel을 일반적 non-compactness 설명에 사용" — 2026-05-08 (confirmed)
- [x] "open cover 없이 non-compactness 설명" — 2026-05-08 (confirmed)

### Confusion Summary

| mapping | status | last_session |
|---------|--------|-------------|
| formal → counterexample | failed | 2026-05-08 |
| counterexample → formal | passed | 2026-05-08 |
| formal+CE → proof_schema | failed | 2026-05-08 |

**Active misconceptions**: misuses_heine_borel, missing_open_cover_argument
**Next recall trigger**: open cover로 (0,1)이 compact하지 않음을 설명하라.

### Notes

> 첫 세션. formal→counterexample 매핑 실패. open cover 기반 설명 연습 필요.
```

---

## What This Demo Proves

1. **Ground Truth Cards constrain evaluation**: The evaluator checks against card's
   required_terms, not free LLM judgment.

2. **Mapping tasks diagnose transfer failures**: The learner "knows" compactness
   (can state the definition) but cannot apply it to a counterexample using the
   correct pathway.

3. **Confusion Map identifies the failure**: The formal→counterexample edge is marked
   as failed, with specific evidence and misconception tags.

4. **Targeted recall trigger**: Instead of a generic "study more", the system generates
   "open cover로 (0,1)이 compact하지 않음을 설명하라" — a precise recall prompt
   targeting the diagnosed failure.

5. **STUDY.md captures diagnostic state**: Not just mastery levels, but which mapping
   transitions failed and what misconceptions are active.

6. **The system is not a question-bank**: It diagnoses understanding structure, not
   just right/wrong answers.

---

## Failure Fallback

If the demo does not produce expected outputs:

| Failure | Likely Cause | Fix |
|---------|-------------|-----|
| Mapping evaluation doesn't detect misconception | Trigger pattern doesn't match Korean text | Expand regex patterns in rubric |
| Score is too high for failed answer | Term check matches too broadly | Narrow required_terms, add more specific terms |
| Score is too low for correct answer | Missing aliases | Add Korean aliases for terms |
| Confusion map not updated | Service not wired into step handler | Check confusion_map_service integration |
| STUDY.md missing confusion summary | Writer not called with confusion data | Check apply_patch integration |
| Artifacts not written | Session writer not updated | Check session_writer.py changes |

---

## Implementation Checklist

- [ ] Prepare initial state (empty STUDY.md, card + rubric + source in place)
- [ ] Create test: `tests/test_golden_run_smoke.py`
- [ ] Implement test with exact inputs from this document
- [ ] Assert all expected outputs match
- [ ] Assert all artifacts exist and validate
- [ ] Run test and verify it passes
- [ ] Manual browser walkthrough following this script
- [ ] Screenshot key moments for documentation

## Acceptance Criteria

1. Golden run test passes deterministically
2. Mapping task 1 evaluates to score < 0.50, passed=false
3. Misconception tags include misuses_heine_borel
4. Confusion map has 3 mapping edges with correct pass/fail status
5. Next recall trigger is about open cover explanation
6. STUDY.md contains Confusion Summary section
7. All JSON artifacts valid and complete

## Risks

- Deterministic evaluator scoring may not produce exact expected scores.
  Mitigate: use threshold-based assertions (< 0.50, not == 0.25).
- Korean text normalization may affect term matching.
  Mitigate: test with exact demo strings during evaluator development.

## Rollback Plan

- Test file is standalone. Delete to rollback.
- Demo is read-only (uses tmp_path fixtures, doesn't modify real data).

## Dependencies

- Depends on: 03 (Card + models), 04 (API), 06 (Evaluator)
- All implementation steps 1-13 must be complete before this test can pass.

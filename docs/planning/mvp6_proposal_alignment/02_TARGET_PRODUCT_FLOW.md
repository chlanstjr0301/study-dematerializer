# 02 — Target Product Flow

## Purpose

Define the target learner flow for MVP6, including the revised 7-step StudySession,
what the user sees at each step, and what the backend stores. Includes the compactness
vertical-slice scenario as a concrete walkthrough.

---

## Target Learner Flow (High Level)

```
Learner enters "옹골성" (compactness)
    │
    ├─ [1] Diagnosis: "What do you already know? Where are you stuck?"
    │       → Backend stores diagnosis.json, confusion_map initialized
    │
    ├─ [2] Prerequisites: Show prerequisite DAG, learner self-checks mastery
    │       → Backend stores prerequisite_graph.json, confusion_map updated
    │
    ├─ [3] Representations: Display 5 representations, learner self-explains each
    │       → Backend stores self-explanation results, confusion_map updated
    │
    ├─ [4] Mapping: 3 cross-representation tasks (formal↔counterexample↔proof)
    │       → Backend stores mapping_results.json, confusion_map updated
    │       → Failed mapping edges recorded in confusion map
    │
    ├─ [5] Misconceptions: T/F quiz grounded in card misconception set
    │       → Backend stores misconception_results, confusion_map updated
    │
    ├─ [6] Recall: White recall from memory (no materials)
    │       → Backend stores recall_result, confusion_map updated
    │
    └─ [7] Summary: Mastery update, confusion map summary, next recall trigger
            → Backend writes STUDY.md patch, final confusion_map.json
```

---

## 7-Step Session Detail

### Step 1: Diagnosis (진단)

**What the learner sees:**
- Prompt: "옹골성에 대해 이미 알고 있는 것을 설명해 주세요. 어디서 막히나요?"
- Large textarea for free-form Korean input
- Submit button

**What the backend does:**
1. Load Ground Truth Card for concept
2. Initialize empty ConfusionMap
3. On diagnosis submit:
   - Store learner response in `diagnosis.json`
   - (Mock mode) Set initial mastery estimate from keyword matching
   - (LLM mode, future) Analyze response for known terms, misconception cues
   - Update confusion map: set initial `prerequisite_nodes` mastery estimates
   - Set `last_updated_step = "diagnosis"`

**State stored:**
```json
{
  "step": "diagnosis",
  "diagnosis": {
    "learner_response": "...",
    "identified_terms": ["metric space", "bounded"],
    "suspected_gaps": ["open cover", "finite subcover"],
    "mastery_estimate": "unknown",
    "misconception_cues": ["compact = bounded"]
  }
}
```

**Confusion map after this step:**
```json
{
  "concept_id": "compactness",
  "prerequisite_nodes": [
    {"concept_id": "metric_space", "mastery": "unknown"},
    {"concept_id": "open_cover", "mastery": "unknown"}
  ],
  "mapping_edges": [],
  "misconception_tags": ["compact_equals_bounded_suspected"],
  "next_recall_triggers": [],
  "evidence_snippets": [],
  "last_updated_step": "diagnosis"
}
```

---

### Step 2: Prerequisites (선행 확인)

**What the learner sees:**
- Prerequisite DAG visualization (list of prerequisite concepts with mastery badges)
- For each prerequisite: self-check radio (알고 있음 / 잘 모름 / 처음 봄)
- "다음" button

**What the backend does:**
1. Load prerequisite graph from card `prerequisite_concepts`
2. Display with current mastery from STUDY.md (or "unknown" if first time)
3. On advance:
   - Store learner self-assessment per prerequisite
   - Update confusion map `prerequisite_nodes` with self-reported mastery
   - Flag prerequisites marked "잘 모름" or "처음 봄" as gaps
   - Set `last_updated_step = "prerequisites"`

**State stored:**
```json
{
  "step": "prerequisites",
  "prerequisite_checks": [
    {"concept_id": "metric_space", "self_report": "known"},
    {"concept_id": "open_cover", "self_report": "unsure"},
    {"concept_id": "heine_borel", "self_report": "never_seen"}
  ]
}
```

---

### Step 3: Representations (표현 학습)

**What the learner sees:**
- 5 representation cards displayed sequentially:
  1. Formal definition (from card `definition_card`)
  2. Intuitive explanation (from card `intuitive_card`)
  3. Visual representation (from card `visual_card`)
  4. Counterexample (from card `counterexample_cards[0]`)
  5. Proof schema (from card `proof_schema_card`)
- After viewing each: self-explanation textarea
- Required: must view and self-explain formal + proof_schema
- Optional: intuitive + visual self-explanations not scored

**What the backend does:**
1. Load representations from Ground Truth Card (not free LLM generation)
2. For each self-explanation submit:
   - Evaluate against card content (required_terms check)
   - Score: formal, counterexample, proof_schema → mastery update
   - Score: intuitive, visual → store but do not update mastery
   - Update confusion map with self-explanation quality signals
   - Set `last_updated_step = "representations"`

**State stored:**
```json
{
  "step": "representations",
  "self_explanations": [
    {
      "representation_type": "formal",
      "learner_response": "...",
      "evaluation": {"score": 0.6, "missing_terms": ["finite subcover"], "mastery": "partial"},
      "scored_for_mastery": true
    },
    {
      "representation_type": "intuitive",
      "learner_response": "...",
      "evaluation": {"score": 0.8},
      "scored_for_mastery": false
    }
  ]
}
```

---

### Step 4: Mapping (매핑 과제) — NEW IN MVP6

**What the learner sees:**
- 3 mapping tasks presented one at a time:

  **Task 1: Formal → Counterexample**
  "옹골성의 정의를 사용하여 (0,1)이 왜 compact하지 않은지 설명하세요."
  (Using the formal definition, explain why (0,1) is not compact.)

  **Task 2: Counterexample → Formal**
  "(0,1)이 compact하지 않다는 사실로부터, compact 집합이 반드시 가져야 하는 성질을 설명하세요."
  (From the fact that (0,1) is not compact, explain what properties a compact set must have.)

  **Task 3: Formal + Counterexample → Proof Schema**
  "정의와 반례를 활용하여, Heine-Borel 정리의 증명 구조를 개략적으로 설명하세요."
  (Using the definition and counterexample, outline the proof structure of Heine-Borel theorem.)

- Each task: prompt + textarea + submit
- Confusion Map panel visible on the side (shows current diagnostic state)

**What the backend does:**
1. Generate mapping tasks from card `allowed_mapping_tasks`
2. For each task submit:
   - Evaluate learner response against card content
   - Check required_terms coverage
   - Check for known misconception patterns
   - Score mapping: pass (>= 0.70) or fail (< 0.70)
   - On failure: record failed mapping edge in confusion map
   - Tag misconceptions detected
   - Generate targeted next_recall_trigger for failed mappings
   - Set `last_updated_step = "mapping"`

**State stored:**
```json
{
  "step": "mapping",
  "mapping_results": [
    {
      "task_type": "formal_to_counterexample",
      "learner_response": "(0,1)은 닫혀 있지 않아서 compact하지 않습니다.",
      "evaluation": {
        "score": 0.3,
        "passed": false,
        "missing_elements": ["open cover argument", "finite subcover"],
        "incorrect_claims": [],
        "misconception_tags": ["misuses_heine_borel", "missing_open_cover_argument"],
        "mapping_failures": ["formal_to_counterexample"],
        "feedback": "Heine-Borel은 R^n에서의 충분조건입니다. open cover로 직접 설명해야 합니다.",
        "next_recall_trigger": "open cover로 (0,1)이 compact하지 않음을 설명하라."
      }
    },
    {
      "task_type": "counterexample_to_formal",
      "learner_response": "...",
      "evaluation": { "score": 0.8, "passed": true, "mapping_failures": [] }
    },
    {
      "task_type": "formal_counterexample_to_proof_schema",
      "learner_response": "...",
      "evaluation": { "score": 0.5, "passed": false, "mapping_failures": ["formal_counterexample_to_proof_schema"] }
    }
  ]
}
```

**Confusion map after this step:**
```json
{
  "concept_id": "compactness",
  "prerequisite_nodes": [...],
  "mapping_edges": [
    {"from": "formal", "to": "counterexample", "passed": false, "score": 0.3},
    {"from": "counterexample", "to": "formal", "passed": true, "score": 0.8},
    {"from": "formal_counterexample", "to": "proof_schema", "passed": false, "score": 0.5}
  ],
  "misconception_tags": [
    "compact_equals_bounded_suspected",
    "misuses_heine_borel",
    "missing_open_cover_argument"
  ],
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
  "last_updated_step": "mapping"
}
```

---

### Step 5: Misconceptions (오개념 체크)

**What the learner sees:**
- T/F statements generated from card `misconception_cards`:
  - "모든 유계 집합은 compact이다." (Every bounded set is compact.) → F
  - "닫힌 집합은 항상 compact이다." (Every closed set is compact.) → F
  - "compact 집합의 부분집합은 compact이다." (Subsets of compact sets are compact.) → F (only closed subsets)
  - "R에서 compact ⟺ 닫히고 유계." (In R, compact ⟺ closed and bounded.) → T (Heine-Borel)
  - "모든 열린 덮개가 유한 부분덮개를 가지면 compact이다." → T
- Immediate feedback after each answer
- Confusion Map panel shows updated misconception tags

**What the backend does:**
1. Load misconception quiz from card
2. Grade answers (deterministic: match against card truth values)
3. For incorrect answers:
   - Add misconception tag to confusion map
   - Record evidence snippet
4. Set `last_updated_step = "misconceptions"`

**State stored:**
```json
{
  "step": "misconceptions",
  "misconception_results": [
    {"claim": "모든 유계 집합은 compact이다.", "correct_answer": false, "learner_answer": true, "correct": false},
    {"claim": "R에서 compact ⟺ 닫히고 유계.", "correct_answer": true, "learner_answer": true, "correct": true}
  ],
  "score": 0.6
}
```

---

### Step 6: Recall (인출 연습)

**What the learner sees:**
- All materials hidden
- Prompt: "지금까지 배운 옹골성에 대해 기억나는 대로 설명하세요."
- Specific sub-prompts based on confusion map:
  - If formal_to_counterexample failed: "특히 open cover를 사용한 반례 설명을 포함하세요."
  - If proof_schema failed: "증명 구조의 핵심 단계를 포함하세요."
- Large textarea
- Submit button (one attempt only, no retry)
- Confusion Map panel visible

**What the backend does:**
1. Generate recall prompt including targeted triggers from confusion map
2. Grade recall response:
   - Check required_terms coverage from card
   - Check if previously failed mapping edges are now addressed
   - Score formal, counterexample, proof_schema components
3. Update confusion map:
   - Mark addressed triggers
   - Update mapping edge scores if relevant content appears
4. Set `last_updated_step = "recall"`

---

### Step 7: Summary (세션 정리)

**What the learner sees:**
- Mastery update table:
  | 표현 | 이전 | 이후 | 변화 |
  |------|------|------|------|
  | 형식 정의 | unknown | partial | +1 |
  | 반례 | unknown | unknown | — |
  | 증명 구조 | unknown | partial | +1 |
- Confusion Map summary:
  - Failed mappings: formal → counterexample
  - Active misconceptions: misuses_heine_borel
  - Next recall trigger: "open cover로 (0,1)이 compact하지 않음을 설명하라."
- Next review date (based on overall mastery)
- "대시보드로 돌아가기" button

**What the backend does:**
1. Compute final mastery per scored representation (formal, counterexample, proof_schema)
2. Compute overall_mastery = weakest of scored representations
3. Compute next_review_date from overall_mastery
4. Write confusion_map.json (final version)
5. Apply STUDY.md patch:
   - Update representations table
   - Update misconceptions section
   - Add confusion summary section (new)
6. Return completion response

---

## Compactness Vertical-Slice Scenario

### Initial State
- Learner has never studied compactness
- STUDY.md: no compactness entry (or all unknown)
- Source file: `data/gonghaebun/default/sources/sample_source.md` available
- Ground Truth Card: `data/gonghaebun/default/cards/real_analysis/compactness.card.json` loaded

### Walkthrough

**Step 1 — Diagnosis:**
Learner types: "compact가 뭔지는 대충 아는데, 왜 (0,1)이 compact가 아닌지 증명을 못 하겠어요."
→ System detects: knows concept exists, gap in open cover application, possible Heine-Borel confusion.
→ Confusion map initialized with suspected gap.

**Step 2 — Prerequisites:**
System shows: metric_space (unknown), open_set (unknown), open_cover (unknown), heine_borel (unknown)
Learner checks: metric_space=known, open_set=known, open_cover=unsure, heine_borel=known
→ Confusion map: open_cover flagged as prerequisite gap.

**Step 3 — Representations:**
System displays 5 cards from Ground Truth Card.
Learner self-explains formal definition: mentions "open cover" but misses "finite subcover".
→ Formal score: 0.6 (partial), missing "finite subcover".
Learner self-explains proof schema: incomplete, gets 0.4 (unknown).
→ Confusion map: formal=partial, proof_schema=unknown.

**Step 4 — Mapping:**
Task 1 (Formal → Counterexample): Learner says "(0,1)은 닫혀 있지 않아서 compact하지 않습니다."
→ FAILED. Uses closedness argument, not open cover. Tags: misuses_heine_borel, missing_open_cover_argument.
→ Confusion map: formal→counterexample edge = FAIL.

Task 2 (Counterexample → Formal): Learner correctly describes what compact sets must have.
→ PASSED.

Task 3 (Formal+CE → Proof Schema): Learner gives partial answer.
→ FAILED. Missing key step in Heine-Borel proof outline.

**Step 5 — Misconceptions:**
"모든 유계 집합은 compact이다." → Learner says True → WRONG.
"R에서 compact ⟺ 닫히고 유계." → Learner says True → CORRECT.
→ Misconception: bounded_implies_compact confirmed.

**Step 6 — Recall:**
System prompts with targeted trigger: "open cover를 사용한 반례 설명을 포함하세요."
Learner gives improved but still partial explanation.
→ Recall score: formal=0.5, counterexample=0.4, proof_schema=0.3.

**Step 7 — Summary:**
Final mastery: formal=partial, counterexample=unknown, proof_schema=unknown.
Overall: unknown. Next review: tomorrow.
Confusion map highlights: formal→counterexample failure, misuses_heine_borel tag.
Next trigger: "open cover로 (0,1)이 compact하지 않음을 설명하라."
STUDY.md updated with all results.

---

## Step Transition Rules

| From Step | To Step | Condition |
|-----------|---------|-----------|
| — | diagnosis | Session created |
| diagnosis | prerequisites | Diagnosis submitted |
| prerequisites | representations | Prerequisites acknowledged |
| representations | mapping | All required self-explanations submitted (formal + proof_schema) |
| mapping | misconceptions | All 3 mapping tasks submitted |
| misconceptions | recall | All misconception answers submitted |
| recall | summary | Recall submitted |
| summary | (done) | Complete button clicked |

Back navigation: allowed for viewing previous steps (read-only mode). Cannot re-submit.

---

## State Restoration

If the browser refreshes mid-session:
1. Frontend reads session_id from sessionStorage
2. GET /api/study-session/{session_id} returns current state
3. Frontend restores to correct step with read-only past steps
4. Confusion map is re-loaded from backend state

Backend session state persists to disk at every step transition in
`runs/{session_id}/study_session_state.json`.

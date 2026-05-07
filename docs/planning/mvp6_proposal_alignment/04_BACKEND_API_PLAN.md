# 04 — Backend API Plan

## Purpose

Define all backend changes for MVP6: new API endpoints, new services, modifications to
existing services, Pydantic request/response schemas, artifact read/write behavior,
error handling, state restoration, and tests.

---

## Current Backend Files (Inspection Targets)

### Files to inspect before implementation

| File | Reason |
|------|--------|
| `apps/api/config.py` | Add CARDS_DIR config |
| `apps/api/main.py` | Mount new routers |
| `apps/api/schemas/api_schemas.py` | Add new request/response types |
| `apps/api/routers/study_session.py` | Add mapping step endpoints |
| `apps/api/services/study_session_service.py` | Central orchestration — add mapping + confusion map logic |
| `src/gonghaebun/study_md/writer.py` | Extend for confusion summary |
| `src/gonghaebun/study_md/parser.py` | Extend for confusion summary |
| `src/gonghaebun/study_loop/session_writer.py` | Add confusion_map.json + mapping artifacts |
| `src/gonghaebun/study_loop/mastery.py` | Exclude intuitive/visual from overall mastery |
| `src/gonghaebun/grading/schemas.py` | Reference for GradingResult schema |
| `src/gonghaebun/models/representations.py` | RepresentationType enum |
| `src/gonghaebun/models/session_models.py` | StudySession, MasteryUpdate |

---

## New API Endpoints

### 1. GET /api/study-session/{session_id}/mapping-tasks

**Purpose**: Retrieve mapping tasks for a study session.

**Response**: `MappingTasksResponse`
```python
class MappingTaskItem(BaseModel):
    task_id: str
    task_type: str
    prompt: str                     # Korean
    source_representations: list[str]
    target_representation: str

class MappingTasksResponse(BaseModel):
    session_id: str
    concept_id: str
    tasks: list[MappingTaskItem]
```

**Behavior**:
1. Load session state from disk
2. Verify session exists and is at mapping step (or later for read-only)
3. Load mapping tasks from `runs/{session_id}/mapping_tasks.json`
4. If tasks don't exist yet, generate from Ground Truth Card
5. Return task list

**Errors**:
- 404: Session not found
- 400: Session not yet at mapping step (and tasks not generated)

---

### 2. POST /api/study-session/{session_id}/mapping-submit

**Purpose**: Submit learner answer for one mapping task.

**Request**: `MappingSubmitRequest`
```python
class MappingSubmitRequest(BaseModel):
    task_id: str
    learner_response: str           # Korean text
```

**Response**: `MappingSubmitResponse`
```python
class MappingSubmitResponse(BaseModel):
    task_id: str
    task_type: str
    score: float
    passed: bool
    missing_elements: list[str]
    misconception_tags: list[str]
    mapping_failures: list[str]
    feedback: str                   # Korean
    next_recall_trigger: str
    confusion_map: ConfusionMapResponse  # Updated confusion map
```

**Behavior**:
1. Load session state + Ground Truth Card + rubric
2. Verify session is at mapping step
3. Evaluate learner response using deterministic evaluator
4. Store MappingResult in session state
5. Update confusion map (add mapping edge, misconception tags, evidence, triggers)
6. Persist updated confusion_map.json and mapping_results.json
7. If all 3 tasks submitted: auto-advance to misconception step
8. Return evaluation result + updated confusion map

**Errors**:
- 404: Session or task not found
- 400: Session not at mapping step
- 400: Task already submitted
- 422: Empty learner_response

---

### 3. GET /api/study-session/{session_id}/confusion-map

**Purpose**: Retrieve current confusion map state.

**Response**: `ConfusionMapResponse`
```python
class PrerequisiteNodeItem(BaseModel):
    concept_id: str
    mastery: str
    self_reported: str | None = None

class MappingEdgeItem(BaseModel):
    from_rep: str
    to_rep: str
    task_type: str
    passed: bool
    score: float

class EvidenceSnippetItem(BaseModel):
    step: str
    task_type: str | None = None
    learner_text: str
    issue: str

class ConfusionMapResponse(BaseModel):
    concept_id: str
    session_id: str
    prerequisite_nodes: list[PrerequisiteNodeItem]
    mapping_edges: list[MappingEdgeItem]
    misconception_tags: list[str]
    next_recall_triggers: list[str]
    evidence_snippets: list[EvidenceSnippetItem]
    last_updated_step: str
```

**Behavior**:
1. Load confusion map from `runs/{session_id}/confusion_map.json`
2. If not yet created (session just started), return empty/initialized map
3. Return current state

**Errors**:
- 404: Session not found

---

## Modified Endpoints

### POST /api/study-session (create)

**Changes**:
- After running 8-stage pipeline, also:
  - Load Ground Truth Card for concept
  - Generate mapping tasks from card
  - Initialize empty confusion map
  - Write `mapping_tasks.json` and `confusion_map.json` to session dir

### POST /api/study-session/{session_id}/diagnose

**Changes**:
- After storing diagnosis:
  - Update confusion map with initial mastery estimates and misconception cues
  - Write updated `confusion_map.json`

### POST /api/study-session/{session_id}/advance

**Changes**:
- When advancing from prerequisites step:
  - Update confusion map prerequisite_nodes with self-reported mastery
  - Write updated `confusion_map.json`
- When advancing from representations step:
  - Verify required self-explanations (formal + proof_schema) submitted
  - (Existing behavior preserved)

### POST /api/study-session/{session_id}/self-explain

**Changes**:
- After evaluating self-explanation:
  - Update confusion map with quality signals
  - Only update mastery for formal, counterexample, proof_schema (skip intuitive, visual)
  - Write updated `confusion_map.json`

### POST /api/study-session/{session_id}/recall

**Changes**:
- Include targeted recall triggers from confusion map in the prompt
- After evaluating recall:
  - Update confusion map: mark addressed triggers, update mapping edges
  - Write updated `confusion_map.json`

### POST /api/study-session/{session_id}/complete

**Changes**:
- Include confusion map summary in STUDY.md patch
- Write final `confusion_map.json`

### GET /api/study-session/{session_id}

**Changes**:
- Include `confusion_map` in response (loaded from disk)
- Include `mapping_tasks` and `mapping_results` in response

---

## New Services

### 1. Card Loader Service

**File**: `apps/api/services/card_service.py`

```python
def load_ground_truth_card(concept_id: str) -> GroundTruthCard:
    """Load and validate card from CARDS_DIR."""

def load_rubric(concept_id: str) -> ConceptRubric:
    """Load and validate rubric from CARDS_DIR."""

def card_exists(concept_id: str) -> bool:
    """Check if card JSON exists."""
```

**Behavior**:
- Resolve path: `CARDS_DIR / domain / {concept_id}.card.json`
- Domain is inferred from concept knowledge base (all current = "real_analysis")
- Validate against Pydantic model
- Cache in module-level dict (cards are static, loaded once)
- Raise 404 with clear message if card not found

---

### 2. Mapping Task Engine Service

**File**: `apps/api/services/mapping_service.py`

```python
def generate_mapping_tasks(
    session_id: str,
    concept_id: str,
    card: GroundTruthCard
) -> list[MappingTask]:
    """Generate 3 mapping tasks from Ground Truth Card."""

def evaluate_mapping_submission(
    task: MappingTask,
    learner_response: str,
    card: GroundTruthCard,
    rubric: ConceptRubric
) -> MappingResult:
    """Evaluate one mapping task submission using deterministic evaluator."""

def update_confusion_map_from_mapping(
    confusion_map: ConfusionMap,
    result: MappingResult
) -> ConfusionMap:
    """Update confusion map with mapping result."""
```

**Task generation logic**:
1. Read `card.allowed_mapping_tasks` (exactly 3)
2. For each: create MappingTask with deterministic task_id (`{session_id}_{task_type}`)
3. Set prompt from card (Korean)
4. Set required_terms from card
5. Set source/target representations based on task_type

**Evaluation logic** (deterministic, no LLM):
1. Normalize learner response (lowercase, strip punctuation for term matching)
2. Check required_terms coverage:
   - For each term, check if term or any alias appears in response
   - Coverage = matched_terms / total_terms
3. Check misconception patterns:
   - For each misconception_check in rubric, apply trigger_patterns
   - If matched: add to misconception_tags
4. Score = coverage_score * (1 - misconception_penalty)
   - misconception_penalty = 0.15 per critical, 0.10 per moderate, 0.05 per minor
   - Clamped to [0.0, 1.0]
5. passed = score >= rubric.pass_threshold (default 0.70)
6. Generate feedback:
   - If passed: affirmation
   - If failed: list missing terms, explain misconceptions
7. Generate next_recall_trigger if failed

---

### 3. Confusion Map Builder Service

**File**: `apps/api/services/confusion_map_service.py`

```python
def initialize_confusion_map(
    session_id: str,
    concept_id: str,
    card: GroundTruthCard
) -> ConfusionMap:
    """Create initial empty confusion map."""

def update_from_diagnosis(
    cmap: ConfusionMap,
    diagnosis: dict
) -> ConfusionMap:
    """Update confusion map after diagnosis step."""

def update_from_prerequisites(
    cmap: ConfusionMap,
    prerequisite_checks: list[dict]
) -> ConfusionMap:
    """Update prerequisite nodes from self-report."""

def update_from_self_explanation(
    cmap: ConfusionMap,
    rep_type: str,
    evaluation: dict
) -> ConfusionMap:
    """Update confusion map after self-explanation evaluation."""

def update_from_mapping(
    cmap: ConfusionMap,
    result: MappingResult
) -> ConfusionMap:
    """Update confusion map with mapping result."""

def update_from_misconceptions(
    cmap: ConfusionMap,
    misconception_results: list[dict]
) -> ConfusionMap:
    """Update confusion map after misconception quiz."""

def update_from_recall(
    cmap: ConfusionMap,
    recall_evaluation: dict
) -> ConfusionMap:
    """Update confusion map after recall evaluation."""

def persist_confusion_map(
    cmap: ConfusionMap,
    session_dir: Path
) -> None:
    """Write confusion_map.json to disk."""

def load_confusion_map(session_dir: Path) -> ConfusionMap | None:
    """Load confusion map from disk, or None if not yet created."""
```

---

## New Router

### Mapping & Confusion Map Router

**File**: `apps/api/routers/mapping.py`

```python
router = APIRouter(prefix="/api/study-session", tags=["mapping"])

@router.get("/{session_id}/mapping-tasks")
async def get_mapping_tasks(session_id: str) -> MappingTasksResponse: ...

@router.post("/{session_id}/mapping-submit")
async def submit_mapping(
    session_id: str,
    req: MappingSubmitRequest
) -> MappingSubmitResponse: ...

@router.get("/{session_id}/confusion-map")
async def get_confusion_map(session_id: str) -> ConfusionMapResponse: ...
```

**Registration in main.py**:
```python
from apps.api.routers import mapping
app.include_router(mapping.router)
```

---

## New Pydantic Schemas (API layer)

Add to `apps/api/schemas/api_schemas.py`:

```python
# Mapping Tasks
class MappingTaskItem(BaseModel): ...
class MappingTasksResponse(BaseModel): ...
class MappingSubmitRequest(BaseModel): ...
class MappingSubmitResponse(BaseModel): ...

# Confusion Map
class PrerequisiteNodeItem(BaseModel): ...
class MappingEdgeItem(BaseModel): ...
class EvidenceSnippetItem(BaseModel): ...
class ConfusionMapResponse(BaseModel): ...
```

(Full field definitions in Section "New API Endpoints" above.)

---

## Error Handling

| Error | HTTP Code | Message |
|-------|-----------|---------|
| Session not found | 404 | "Session {session_id} not found" |
| Card not found | 404 | "Ground truth card not found for concept {concept_id}" |
| Rubric not found | 404 | "Rubric not found for concept {concept_id}" |
| Not at mapping step | 400 | "Session is at step {current_step}, not mapping" |
| Task already submitted | 400 | "Task {task_id} already submitted" |
| Task not found | 404 | "Task {task_id} not found in session" |
| Empty response | 422 | "learner_response must not be empty" |
| Invalid task_id format | 400 | "Invalid task_id format" |

All errors return JSON: `{"detail": "message"}` (FastAPI default).

---

## State Restoration

### Session state on disk

`runs/{session_id}/study_session_state.json` is the source of truth.

**New fields added to session state**:
```json
{
  "session_id": "...",
  "concept_id": "...",
  "current_step": 4,
  "steps_completed": ["diagnosis", "prerequisites", "representations", "mapping"],
  "mapping_tasks_generated": true,
  "mapping_results": [ ... ],
  "confusion_map_initialized": true
}
```

**Restoration flow**:
1. GET /api/study-session/{session_id} loads state from disk
2. State includes current_step, all completed step data
3. Confusion map loaded from separate file (confusion_map.json)
4. Mapping tasks loaded from separate file (mapping_tasks.json)
5. Mapping results loaded from separate file (mapping_results.json)
6. Frontend can resume at correct step with all past data

### Step numbering change

Current (MVP5): 6 steps (0-5)
```
0: diagnosis, 1: prerequisites, 2: representations,
3: misconceptions, 4: recall, 5: summary
```

New (MVP6): 7 steps (0-6)
```
0: diagnosis, 1: prerequisites, 2: representations,
3: mapping (NEW), 4: misconceptions, 5: recall, 6: summary
```

**Migration**: Current sessions (if any in-progress) will not have step 3 mapping.
The backend should handle legacy sessions by treating them as MVP5 (skip mapping step).
Check: if `mapping_tasks_generated` field missing → legacy session.

---

## Mastery Scoring Change

### File: `src/gonghaebun/study_loop/mastery.py`

Add constant:
```python
MASTERY_SCORED_REPS = {"formal", "counterexample", "proof_schema"}
```

### File: `src/gonghaebun/study_md/writer.py`

Modify `apply_patch()`:
- When computing overall_mastery, only consider reps in `MASTERY_SCORED_REPS`
- intuitive and visual mastery are still tracked but excluded from overall

This is a targeted change. The `compute_mastery_state()` function itself doesn't change
(it still maps accuracy → mastery level). The change is in `apply_patch()` where overall
is computed as the weakest of all reps → weakest of scored reps only.

---

## Files Summary

### Files to add

| File | Purpose |
|------|---------|
| `apps/api/routers/mapping.py` | New router for mapping + confusion map endpoints |
| `apps/api/services/card_service.py` | Card and rubric loader |
| `apps/api/services/mapping_service.py` | Mapping task engine + evaluator |
| `apps/api/services/confusion_map_service.py` | Confusion map builder + persistence |

### Files to modify

| File | What Changes |
|------|-------------|
| `apps/api/config.py` | Add CARDS_DIR |
| `apps/api/main.py` | Mount mapping router |
| `apps/api/schemas/api_schemas.py` | Add mapping + confusion map schemas |
| `apps/api/routers/study_session.py` | Wire confusion map updates into existing step handlers |
| `apps/api/services/study_session_service.py` | Add mapping step, confusion map init, card loading |
| `src/gonghaebun/study_loop/mastery.py` | Add MASTERY_SCORED_REPS constant |
| `src/gonghaebun/study_md/writer.py` | Use MASTERY_SCORED_REPS for overall, write confusion summary |
| `src/gonghaebun/study_md/parser.py` | Parse confusion summary section |
| `src/gonghaebun/study_loop/session_writer.py` | Write confusion_map.json, mapping artifacts |

### Tests to add

| File | What |
|------|------|
| `tests/test_card_service.py` | Card loading, validation, not-found |
| `tests/test_mapping_service.py` | Task generation, evaluation, scoring |
| `tests/test_confusion_map_service.py` | Init, update from each step, persistence |
| `tests/test_api_mapping_tasks.py` | GET mapping-tasks, POST mapping-submit endpoints |
| `tests/test_api_confusion_map.py` | GET confusion-map endpoint |
| `tests/test_mastery_scored_reps.py` | Overall mastery excludes intuitive/visual |

---

## Implementation Checklist

- [ ] Add CARDS_DIR to config.py
- [ ] Create card_service.py (load, validate, cache)
- [ ] Create mapping_service.py (generate, evaluate, update confusion)
- [ ] Create confusion_map_service.py (init, per-step updates, persist, load)
- [ ] Create mapping.py router
- [ ] Add schemas to api_schemas.py
- [ ] Mount router in main.py
- [ ] Wire confusion map updates into study_session_service.py step handlers
- [ ] Add step 3 (mapping) to session step machine
- [ ] Update session_writer.py for new artifacts
- [ ] Modify mastery.py for MASTERY_SCORED_REPS
- [ ] Modify writer.py for scored-reps-only overall mastery
- [ ] Modify parser.py for confusion summary section
- [ ] Modify writer.py for confusion summary section
- [ ] Write all tests (6 new test files)

## Acceptance Criteria

1. GET /api/study-session/{id}/mapping-tasks returns 3 tasks from card
2. POST /api/study-session/{id}/mapping-submit evaluates deterministically, returns feedback
3. GET /api/study-session/{id}/confusion-map returns current confusion state
4. Confusion map updates at diagnosis, prerequisites, representations, mapping, misconceptions, recall
5. Overall mastery computed from formal + counterexample + proof_schema only
6. Legacy sessions (no mapping step) don't crash
7. All existing tests still pass

## Risks

- `study_session_service.py` is the central orchestration file; many modifications here
  increase risk of regressions. Mitigate: add confusion map/mapping logic as separate
  service calls, not inline code.
- Step numbering change affects frontend. Coordinate with doc 05.
- Deterministic evaluator may be too strict or too lenient for real Korean text. Mitigate:
  extensive term aliasing (Korean + English), needs_human_review fallback.

## Rollback Plan

- New router + services are additive: can be removed without affecting existing code
- Step numbering change is the riskiest modification. Rollback: revert step enum and
  remove mapping step handler from study_session_service.py.
- Mastery scoring change: revert MASTERY_SCORED_REPS usage in writer.py.
- Parser/writer confusion summary: backward-compat by design, safe to revert.

## Dependencies

- Depends on: 03 (Data Model) — models must be defined first
- Depended on by: 05 (Frontend), 08 (Tests), 10 (Demo)

# 03 — Data Model and Artifact Plan

## Purpose

Define all new data schemas (Ground Truth Card, MappingTask, MappingResult, ConfusionMap,
Rubric), the session artifact directory layout, and how STUDY.md incorporates confusion map
summaries.

---

## 1. Ground Truth Card Schema

### File location

```
data/gonghaebun/default/cards/real_analysis/{concept_id}.card.json
```

Example: `data/gonghaebun/default/cards/real_analysis/compactness.card.json`

### Schema (Pydantic model: `GroundTruthCard`)

```python
class DefinitionCard(BaseModel):
    """Canonical formal definition."""
    statement: str          # LaTeX-friendly formal statement
    statement_kr: str       # Korean translation
    source_ref: str         # e.g., "Rudin, Theorem 2.32"
    required_terms: list[str]  # Terms that must appear in a correct explanation
    # e.g., ["open cover", "finite subcover", "every"]

class IntuitiveCard(BaseModel):
    """Intuitive explanation (learning aid, not scored)."""
    explanation: str
    explanation_kr: str
    analogies: list[str]    # e.g., ["finite net that catches all points"]

class VisualCard(BaseModel):
    """Visual representation (learning aid, not scored)."""
    description: str
    description_kr: str
    ascii_diagram: str | None = None  # Optional ASCII art

class CounterexampleCard(BaseModel):
    """One specific counterexample."""
    example_id: str         # e.g., "open_unit_interval"
    statement: str          # "(0,1) in R is not compact"
    statement_kr: str
    explanation: str        # Why it fails the definition
    explanation_kr: str
    source_ref: str
    required_terms: list[str]  # Terms needed to correctly explain this CE
    # e.g., ["open cover", "(1/n, 1)", "no finite subcover"]

class ProofSchemaCard(BaseModel):
    """Proof structure for a key theorem."""
    theorem: str            # "Heine-Borel: compact in R^n iff closed and bounded"
    theorem_kr: str
    proof_steps: list[str]  # Ordered key steps
    # e.g., ["Assume closed and bounded", "Take any open cover",
    #        "Use Bolzano-Weierstrass to extract convergent subsequence",
    #        "Construct finite subcover from convergence", "Conclude compact"]
    source_ref: str
    required_terms: list[str]

class MisconceptionCard(BaseModel):
    """One known misconception."""
    misconception_id: str   # e.g., "bounded_implies_compact"
    claim: str              # "Every bounded set is compact"
    claim_kr: str
    truth_value: bool       # False for misconceptions
    correction: str         # Why it's wrong
    correction_kr: str
    related_counterexample: str | None = None  # CE that disproves this

class AllowedMappingTask(BaseModel):
    """One mapping task template."""
    task_type: Literal[
        "formal_to_counterexample",
        "counterexample_to_formal",
        "formal_counterexample_to_proof_schema"
    ]
    prompt: str             # English task prompt
    prompt_kr: str          # Korean task prompt
    required_terms: list[str]  # Terms expected in a correct answer
    grounding_notes: str    # What the evaluator should check

class GroundTruthCard(BaseModel):
    """Complete ground truth for one concept."""
    concept_id: str                     # e.g., "compactness"
    domain: str                         # e.g., "real_analysis"
    source_refs: list[str]              # e.g., ["Rudin Ch.2", "Bartle Ch.11"]
    prerequisite_concepts: list[str]    # e.g., ["metric_space", "open_cover", ...]
    definition_card: DefinitionCard
    intuitive_card: IntuitiveCard
    visual_card: VisualCard
    counterexample_cards: list[CounterexampleCard]   # >= 2
    proof_schema_card: ProofSchemaCard
    misconception_cards: list[MisconceptionCard]     # >= 3
    required_terms: list[str]           # Global required terms for this concept
    allowed_mapping_tasks: list[AllowedMappingTask]  # Exactly 3
    version: str = "1.0"
    created_at: str                     # ISO date
```

### Validation rules

- `concept_id` must be a valid slug (alphanumeric + underscore)
- `prerequisite_concepts` entries must be valid slugs
- `allowed_mapping_tasks` must have exactly 3 entries
- `counterexample_cards` must have >= 2 entries
- `misconception_cards` must have >= 3 entries
- All `required_terms` lists must be non-empty
- `truth_value` in misconception_cards: at least one True (correct statement) and at least two False

### Pydantic model location

New file: `src/gonghaebun/models/ground_truth_card.py`

---

## 2. MappingTask Schema

```python
class MappingTaskType(str, Enum):
    FORMAL_TO_COUNTEREXAMPLE = "formal_to_counterexample"
    COUNTEREXAMPLE_TO_FORMAL = "counterexample_to_formal"
    FORMAL_COUNTEREXAMPLE_TO_PROOF_SCHEMA = "formal_counterexample_to_proof_schema"

class MappingTask(BaseModel):
    """A single mapping task presented to the learner."""
    task_id: str                    # UUID or deterministic ID
    session_id: str
    concept_id: str
    task_type: MappingTaskType
    prompt: str                     # Task prompt (Korean)
    required_terms: list[str]       # From card's AllowedMappingTask
    grounding_notes: str            # Evaluator guidance
    source_representations: list[str]  # Which rep types feed this task
    # e.g., ["formal"] for formal_to_counterexample
    target_representation: str      # Which rep type this tests
    # e.g., "counterexample" for formal_to_counterexample
```

### Pydantic model location

New file: `src/gonghaebun/models/mapping_models.py`

---

## 3. MappingResult Schema

```python
class MappingResult(BaseModel):
    """Result of evaluating one mapping task submission."""
    task_id: str
    task_type: MappingTaskType
    learner_response: str
    score: float                    # 0.0–1.0
    passed: bool                    # score >= 0.70
    missing_elements: list[str]     # Required terms not found
    incorrect_claims: list[str]     # Detected wrong statements
    misconception_tags: list[str]   # Matched card misconception IDs
    mapping_failures: list[str]     # Which mapping edges failed
    feedback: str                   # Korean feedback
    next_recall_trigger: str        # Targeted recall prompt (Korean)
    needs_human_review: bool = False
    evaluated_at: str               # ISO datetime
```

### Pydantic model location

Same file: `src/gonghaebun/models/mapping_models.py`

---

## 4. ConfusionMap Schema

```python
class PrerequisiteNode(BaseModel):
    concept_id: str
    mastery: Literal["unknown", "partial", "solid"]
    self_reported: str | None = None  # "known", "unsure", "never_seen"

class MappingEdge(BaseModel):
    from_rep: str                   # Source representation(s)
    to_rep: str                     # Target representation
    task_type: str                  # MappingTaskType value
    passed: bool
    score: float
    attempt_count: int = 1

class EvidenceSnippet(BaseModel):
    step: str                       # Which session step
    task_type: str | None = None    # Optional task type
    learner_text: str               # Excerpt from learner response (max 200 chars)
    issue: str                      # What was wrong

class ConfusionMap(BaseModel):
    """Per-session learner diagnostic artifact."""
    concept_id: str
    session_id: str
    prerequisite_nodes: list[PrerequisiteNode]
    mapping_edges: list[MappingEdge]
    misconception_tags: list[str]           # Card misconception IDs
    next_recall_triggers: list[str]         # Korean recall prompts
    evidence_snippets: list[EvidenceSnippet]
    last_updated_step: str                  # "diagnosis" | "prerequisites" | ... | "recall"
    created_at: str                         # ISO datetime
    updated_at: str                         # ISO datetime
```

### Pydantic model location

New file: `src/gonghaebun/models/confusion_map.py`

---

## 5. Rubric Schema

```python
class TermCheck(BaseModel):
    """One required term with weight."""
    term: str                       # e.g., "open cover"
    weight: float = 1.0             # Relative importance
    aliases: list[str] = []         # Acceptable alternatives
    # e.g., ["열린 덮개"] for Korean

class MisconceptionCheck(BaseModel):
    """One misconception pattern to detect."""
    misconception_id: str           # From card
    trigger_patterns: list[str]     # Regex or keyword patterns that indicate this misconception
    # e.g., ["bounded.*compact", "유계.*compact"]
    severity: Literal["critical", "moderate", "minor"] = "moderate"

class TaskRubric(BaseModel):
    """Rubric for one task type."""
    task_type: str                  # "self_explain_formal", "mapping_formal_to_counterexample", etc.
    required_terms: list[TermCheck]
    misconception_checks: list[MisconceptionCheck]
    pass_threshold: float = 0.70    # Score needed to pass
    scoring_method: Literal["term_coverage", "weighted_terms"] = "term_coverage"

class ConceptRubric(BaseModel):
    """Complete rubric for one concept."""
    concept_id: str
    domain: str
    version: str = "1.0"
    task_rubrics: dict[str, TaskRubric]
    # Keys: "self_explain_formal", "self_explain_counterexample", "self_explain_proof_schema",
    #        "mapping_formal_to_counterexample", "mapping_counterexample_to_formal",
    #        "mapping_formal_counterexample_to_proof_schema",
    #        "recall", "misconception_quiz"
    global_misconception_checks: list[MisconceptionCheck]  # Apply to all tasks
```

### File location

```
data/gonghaebun/default/cards/real_analysis/compactness.rubric.json
```

### Pydantic model location

New file: `src/gonghaebun/models/rubric.py`

---

## 6. Session Artifact Directory Layout

### Current layout (preserved)

```
runs/{session_id}/
├── session.json
├── recall_attempts.json
├── grading_results.json
├── llm_traces.jsonl
├── STUDY.patch.md
├── session_summary.md
├── study_session_state.json
├── source_manifest.json
├── concept_decomposition.json
├── prerequisite_graph.json
├── representation_cards.md
├── representation_set.json
├── diagnosis.json
├── recall_tasks.json
├── recall_tasks.md
└── visualization/
    ├── mastery_map.json
    ├── mastery_map.mmd
    ├── recall_feedback.json
    ├── review_queue.json
    └── session_flow.mmd
```

### New artifacts added by MVP6

```
runs/{session_id}/
├── ... (all existing artifacts preserved)
├── confusion_map.json              # NEW — ConfusionMap, updated at each step
├── mapping_tasks.json              # NEW — list[MappingTask] generated from card
├── mapping_results.json            # NEW — list[MappingResult] after submit
├── misconception_results.json      # NEW — structured quiz results
└── llm_traces/                     # EXISTING — add mapping eval traces
    └── {question_id}.json
```

### New data directory

```
data/gonghaebun/default/
├── cards/                          # NEW — Ground Truth Cards
│   └── real_analysis/
│       ├── compactness.card.json
│       ├── compactness.rubric.json
│       ├── connectedness.card.json     # MVP6 stretch
│       └── connectedness.rubric.json   # MVP6 stretch
├── STUDY.md                        # EXISTING — extended with confusion summary
├── sources/                        # EXISTING
├── banks/                          # EXISTING
└── runs/                           # EXISTING — new artifacts per session
```

### Config addition

In `apps/api/config.py`:
```python
CARDS_DIR = Path(os.environ.get(
    "GONGHAEBUN_CARDS_DIR",
    str(DATA_ROOT / "cards")
))
```

---

## 7. STUDY.md Extensions

### New section: Confusion Summary

Added after Misconceptions Encountered, before Notes:

```markdown
## compactness

... (existing sections) ...

### Misconceptions Encountered

- [x] "모든 유계 집합은 compact이다." — 2026-05-08 (confirmed)
- [x] "Heine-Borel을 일반 metric space에 적용" — 2026-05-08 (confirmed)

### Confusion Summary

| mapping | status | last_session |
|---------|--------|-------------|
| formal → counterexample | failed | 2026-05-08 |
| counterexample → formal | passed | 2026-05-08 |
| formal+CE → proof_schema | failed | 2026-05-08 |

**Active misconceptions**: misuses_heine_borel, bounded_implies_compact
**Next recall trigger**: open cover로 (0,1)이 compact하지 않음을 설명하라.

### Notes

> ...
```

### Parser changes

`study_md/parser.py` must handle the new "Confusion Summary" section:
- Parse mapping status table
- Parse active misconceptions line
- Parse next recall trigger line
- Store in `ConceptRecord` as new fields:
  - `confusion_mapping_status: list[dict]` (mapping, status, last_session)
  - `active_misconceptions: list[str]`
  - `next_recall_trigger: str | None`

### Writer changes

`study_md/writer.py` must write the confusion summary section when confusion map data
is available. The section is optional — old sessions without confusion maps should not
break the parser.

### Backward compatibility

- If "Confusion Summary" section is missing, parser returns empty defaults
- Writer only adds section if confusion map data is provided
- Existing STUDY.md files remain valid

---

## 8. Evaluator Output Schema (Extended)

The current `GradingResult` schema is extended. The evaluator output for mapping tasks
and self-explanation uses this unified schema:

```python
class EvaluationOutput(BaseModel):
    """Unified evaluator output for all task types."""
    score: float                        # 0.0–1.0
    mastery: Literal["unknown", "partial", "solid"]
    passed: bool                        # score >= threshold
    missing_elements: list[str]         # Required terms not found
    incorrect_claims: list[str]         # Wrong statements detected
    misconception_tags: list[str]       # Card misconception IDs matched
    mapping_failures: list[str]         # Failed mapping edge types
    needs_human_review: bool = False
    feedback: str                       # Korean feedback text
    next_recall_trigger: str = ""       # Targeted recall prompt
```

This replaces/extends the current `GradingResult` for MVP6 evaluation contexts.
The existing `GradingResult` is kept for backward compat with MVP3 recall sessions.

### Pydantic model location

New file: `src/gonghaebun/models/evaluation_output.py`

---

## 9. Model File Summary

| New File | Contains |
|----------|---------|
| `src/gonghaebun/models/ground_truth_card.py` | GroundTruthCard, DefinitionCard, IntuitiveCard, VisualCard, CounterexampleCard, ProofSchemaCard, MisconceptionCard, AllowedMappingTask |
| `src/gonghaebun/models/mapping_models.py` | MappingTaskType, MappingTask, MappingResult |
| `src/gonghaebun/models/confusion_map.py` | ConfusionMap, PrerequisiteNode, MappingEdge, EvidenceSnippet |
| `src/gonghaebun/models/rubric.py` | ConceptRubric, TaskRubric, TermCheck, MisconceptionCheck |
| `src/gonghaebun/models/evaluation_output.py` | EvaluationOutput |

---

## Implementation Checklist

- [ ] Create `src/gonghaebun/models/ground_truth_card.py` with all sub-models
- [ ] Create `src/gonghaebun/models/mapping_models.py`
- [ ] Create `src/gonghaebun/models/confusion_map.py`
- [ ] Create `src/gonghaebun/models/rubric.py`
- [ ] Create `src/gonghaebun/models/evaluation_output.py`
- [ ] Create `data/gonghaebun/default/cards/real_analysis/compactness.card.json`
- [ ] Create `data/gonghaebun/default/cards/real_analysis/compactness.rubric.json`
- [ ] Extend `study_md/parser.py` for confusion summary section
- [ ] Extend `study_md/writer.py` for confusion summary section
- [ ] Add `CARDS_DIR` to `apps/api/config.py`
- [ ] Write tests: `tests/test_ground_truth_cards.py`
- [ ] Write tests: `tests/test_data_models.py` (mapping, confusion, rubric, eval output)
- [ ] Write tests: `tests/test_study_md_confusion_summary.py` (parser + writer)

## Acceptance Criteria

1. `compactness.card.json` loads and validates against GroundTruthCard schema
2. All 5 new model files importable and instantiable
3. STUDY.md parser handles files with and without Confusion Summary section
4. STUDY.md writer produces valid Confusion Summary from ConfusionMap data
5. Existing tests still pass (no regressions)

## Risks

- Card content quality: formal definition, counterexample explanations, proof schema steps
  must be mathematically accurate. Review against Rudin Ch.2.
- Schema rigidity: if card schema is too strict, future concepts may need schema changes.
  Mitigate with `version` field and optional fields.
- STUDY.md parser complexity: adding a new section increases parser fragility.
  Mitigate with backward-compat defaults and thorough tests.

## Rollback Plan

- All new files are additive (new model files, new card files, new test files)
- Parser/writer changes are backward-compatible (missing section → defaults)
- If anything breaks: revert parser/writer changes, keep models as standalone
- Config change (CARDS_DIR) is harmless if directory doesn't exist

## Dependencies

- None (this is the foundation layer, no API or frontend dependencies)
- Used by: 04 (Backend), 05 (Frontend), 06 (Evaluator), 10 (Demo)

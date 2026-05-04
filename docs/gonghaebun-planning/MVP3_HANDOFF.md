# MVP3 Handoff — White Recall Session Engine with Optional LLM Grading

## Status: COMPLETE

490 tests passing (309 MVP1/2 + 181 new).

---

## What Was Built

MVP3 closes the study loop started in MVP1/2:

```
questions.accepted.json
  → recall-session CLI  (present questions, collect answers)
  → grading             (self / mock / LLM)
  → StudySession        (RecallAttempt + MasteryUpdate per rep type)
  → STUDY.md update     (apply_patch — backed up + validated)
  → runs/{session_id}/  (session artifacts)
```

### New CLI Subcommands

| Command | Purpose |
|---|---|
| `review-bank` | Wraps `run_review_cli`; interactive accept/reject of generated questions |
| `recall-session` | White-recall session for a single concept |
| `review-due` | Scan STUDY.md for due concepts and run recall sessions for each |

### New Packages

| Package | Files | Role |
|---|---|---|
| `llm/` | `errors.py`, `openai_client.py` | LLM error types; OpenAI Responses API adapter |
| `grading/` | `schemas.py`, `answer_grader.py`, `prompt_builder.py`, `self_grader.py`, `llm_grader.py` | Grading layer |
| `study_loop/` | `mastery.py`, `question_loader.py`, `white_recall.py`, `session_writer.py`, `review_due.py` | Recall loop |

### Modified Files (minimal)

| File | Change |
|---|---|
| `study_md/writer.py` | Added `validate_study_md()` and call in `apply_patch()` |
| `cli.py` | Added `review-bank`, `recall-session`, `review-due` subcommands |

---

## Architecture Decisions

- **No SQLite.** STUDY.md remains the sole persistent user-facing store (DEC-007).
- **No LangChain / LangGraph / vector DB.** Direct OpenAI API via `OpenAIClient`.
- **OpenAI Responses API** (`responses.create()` / `response.output_text`) used as primary path — not Chat Completions.
- **LLM retry**: malformed JSON is retried once, then `LLMResponseError` is raised.
- **Backup convention**: `shutil.copy2(path, path.with_suffix(".bak"))` → `STUDY.bak`.
- **Post-write validation**: `validate_study_md()` is called after every `apply_patch()` write to catch corruption early.
- **Strict bank lookup**: `find_question_bank` enforces `{bank-root}/{concept_id}/questions.accepted.json`; no silent fallback; `--questions` flag bypasses lookup entirely.
- **`--no-interactive` + `--grader llm`**: prints a warning to stderr; does NOT hard-fail (grades empty strings as low accuracy).

---

## Session Artifacts

```
runs/{session_id}/
  session.json          StudySession fields (serialised)
  recall_attempts.json  list of {question_id, learner_response, grading}
  grading_results.json  list of GradingResult dicts
  llm_traces.jsonl      one JSON line per {question_id, raw_response}
                        (only when grader_type="llm")
  STUDY.patch.md        from generate_patch(session)
  session_summary.md    human-readable summary
```

---

## Grading Schema

```python
@dataclass
class GradingResult:
    accuracy_score: float          # 0.0–1.0; validated in __post_init__
    missing_elements: list[str]
    errors: list[str]
    feedback: str
    mastery_suggestion: str        # "unknown" | "partial" | "solid"
    confidence: float              # 0.0–1.0
    needs_human_review: bool
    evidence_alignment: str        # "supported" | "partially_supported" | "unsupported"
    raw_response: str              # verbatim LLM output; "self:{score}" for SelfGrader
```

### SelfGrader Score Map

| Score | accuracy_score | mastery_suggestion |
|-------|---------------|-------------------|
| 0 | 0.00 | unknown |
| 1 | 0.33 | partial |
| 2 | 0.67 | partial |
| 3 | 1.00 | solid |

### Mastery State Thresholds

| accuracy_score | MasteryLevel |
|---|---|
| ≥ 0.85 | solid |
| ≥ 0.50 | partial |
| < 0.50 | unknown |

---

## Representation Mapping

| question_type | representation_type |
|---|---|
| definition_recall | formal |
| theorem_recall | formal |
| exercise_recall | formal |
| proof_schema_recall | proof_schema |
| example_explanation | counterexample |
| intuition_recall | intuitive |
| *(any other)* | formal (fallback) |

---

## Smoke Test

```bash
# 1. Build bank
python -m gonghaebun.cli build-bank \
  --source-local tests/data/sample_source.md \
  --document-id sample_source \
  --bank-dir tmp_mvp3_bank

# 2. Accept all questions programmatically
python -c "
from pathlib import Path
from gonghaebun.pipeline.io import load_questions, export_accepted
qs = load_questions(Path('tmp_mvp3_bank/questions.generated.json'))
for q in qs: q.status = 'accepted'
export_accepted(qs, Path('tmp_mvp3_bank/questions.accepted.json'))
"

# 3. recall-session (mock grader, no interactive)
python -m gonghaebun.cli recall-session \
  --questions tmp_mvp3_bank/questions.accepted.json \
  --concept sample_source \
  --study-md tmp_mvp3_bank/STUDY.md \
  --runs-dir tmp_mvp3_bank/runs \
  --limit 3 \
  --grader mock \
  --no-interactive

# 4. review-due — requires concept subdir layout
mkdir -p tmp_mvp3_bank/sample_source
cp tmp_mvp3_bank/questions.accepted.json tmp_mvp3_bank/sample_source/
python -m gonghaebun.cli review-due \
  --bank-root tmp_mvp3_bank \
  --study-md tmp_mvp3_bank/STUDY.md \
  --runs-dir tmp_mvp3_bank/runs \
  --grader mock \
  --no-interactive

# 5. Regression
python -m pytest tests/ -q   # 490 tests pass
```

---

## Test Files Added (181 new tests)

| File | Tests | Focus |
|---|---|---|
| `test_openai_client.py` | 17 | API key guard, lazy import, Responses API, malformed JSON |
| `test_grading_schemas.py` | 40 | GradingResult validation, SelfGrader, prompt builder |
| `test_llm_grader.py` | 12 | MockLLMClient grading, retry, LLMResponseError |
| `test_mastery_mapping.py` | 22 | Score→accuracy, type→rep, aggregate_by_rep |
| `test_question_loader.py` | 9 | Load, limit, missing file, empty file |
| `test_white_recall.py` | 18 | Batch, interactive monkeypatch, EOFError |
| `test_session_writer.py` | 27 | StudySession fields, artifact files, STUDY.md backup + update |
| `test_review_due.py` | 17 | Due-concept filtering, strict bank lookup, missing file |
| `test_recall_cli.py` | 19 | review-bank, recall-session, review-due, regression |

---

## Known Limitations / v4 Candidates

- No concept-level scheduling history — mastery is reset each session (no running average).
- `review-due` runs concepts sequentially; no parallelism.
- `LLMGrader` uses a single retry; persistent network failures are not handled.
- No `--grader llm` + `--provider` wiring beyond `openai`; other providers require a new `LLMClient` subclass.
- STUDY.md is the sole persistent store — no query-by-date or cross-session analytics without parsing the file.

---

## MVP3.1 — Visualization Artifact Layer

### Status: COMPLETE

Added on top of the completed MVP3 engine. Does not modify grading, LLM, recall, review-due,
or STUDY.md schema.

### New Files

| File | Role |
|---|---|
| `src/gonghaebun/visualization/__init__.py` | Package init |
| `src/gonghaebun/visualization/session_visualizer.py` | Artifact generator |
| `tests/test_session_visualizer.py` | ~30 tests covering JSON shape + Mermaid content |

### Modified Files

| File | Change |
|---|---|
| `study_loop/session_writer.py` | Calls `write_visualization_artifacts()` after `apply_patch()`; docstring updated |

### Artifact Layout

```
runs/{session_id}/
  ...                       (existing MVP3 artifacts)
  visualization/
    mastery_map.json        per-concept mastery state + accuracy per representation
    recall_feedback.json    per-question grading (question_id, needs_human_review, etc.)
    review_queue.json       next review date + due_status per concept
    mastery_map.mmd         Mermaid flowchart: concept → representation nodes
    session_flow.mmd        Mermaid flowchart: session pipeline summary
```

### JSON Shapes

**mastery_map.json**
```json
{
  "concept_id": "compactness",
  "overall_mastery": "partial",
  "representations": [
    {"type": "formal", "before": "unknown", "after": "partial", "accuracy_score": 0.75}
  ],
  "weakest_links": ["formal"]
}
```
- `overall_mastery`: weakest across all rep updates (unknown < partial < solid); null if no attempts
- `weakest_links`: all reps whose `after` equals the minimum mastery level; `[]` if all solid

**recall_feedback.json** — list, one entry per attempt
```json
[
  {
    "question_id": "q1",
    "representation_type": "formal",
    "learner_response": "...",
    "accuracy_score": 0.75,
    "missing_elements": [],
    "errors": [],
    "feedback": "...",
    "needs_human_review": false
  }
]
```

**review_queue.json** — list, one entry per concept
```json
[
  {
    "concept_id": "compactness",
    "next_review_date": "2026-01-08",
    "weakest_representation": "formal",
    "due_status": "upcoming"
  }
]
```
- `due_status`: `"overdue"` | `"due_today"` | `"upcoming"` (vs. `date.today()`)
- `next_review_date`: taken from the weakest representation's `MasteryUpdate`
- `write_visualization_artifacts()` accepts an optional `today: date | None` for test determinism

### Mermaid Convention

Labels use double-quoted strings with plain separators (no `\n`, no special chars) to
stay valid without a Mermaid runtime dependency.

```
flowchart TD
    compactness["compactness"] --> compactness_formal["formal - partial"]
```

```
flowchart LR
    Q["accepted_questions (3)"] --> A["recall_attempts (3)"]
    A --> G["grading (mock)"]
    G --> M["mastery_update (formal: partial)"]
    M --> S["STUDY.md (updated)"]
    S --> D["review_due (2026-01-08)"]
```

### Design Constraints Respected

- No LLM calls, no grading recomputation, no STUDY.md parsing.
- Reuses `aggregate_by_rep()` and `question_type_to_rep()` from `study_loop/mastery.py`.
- No new runtime dependencies (stdlib only: `json`, `datetime.date`, `pathlib`).
- All 490 existing tests continue to pass.

# MVP2 Handoff — Source-Traceable Question Bank Builder

## 1. MVP2 Goal

MVP2 converts Markdown or text source files into a **source-traceable, human-reviewable
question bank**.  Every generated question is linked back to the exact text block
it came from, making the bank auditable and suitable for human quality control
before the questions are used in a study session.

MVP1 produced recall tasks inside a single session and then discarded them.
MVP2 makes generated questions **persistent, reviewable, and reusable** across sessions.

---

## 2. Current Pipeline

```
Source Markdown (.md)
  ─▶ [block_parser]   ─▶ SourceBlock[]          (structured text blocks)
  ─▶ [rule_engine]    ─▶ Rule[]                  (matching question templates)
  ─▶ [question_gen]   ─▶ Question[]              (deterministic, source-grounded)
  ─▶ [io]             ─▶ blocks.generated.json
                          questions.generated.json
  ─▶ [review_cli]     ─▶ questions.reviewed.json
                          questions.accepted.json
                          review_records.json
```

All steps are **fully deterministic** (no LLM calls) and **local-only**.

---

## 3. Implemented Modules

| Module | Role |
|---|---|
| `src/gonghaebun/models/question_bank.py` | Data model layer. Defines `SourceBlock`, `Evidence`, `Question`, `Rule`, `ReviewRecord` dataclasses with `__post_init__` runtime validation. |
| `src/gonghaebun/pipeline/block_parser.py` | Stage A. Parses a Markdown file into `SourceBlock` objects. Splits on blank-line boundaries, tracks heading section titles, classifies block type, and skips blocks with fewer than 50 non-whitespace characters. |
| `src/gonghaebun/pipeline/rule_engine.py` | Stage B. Provides the hardcoded `RULES` list and `get_applicable_rules()` / `get_rules_for_blocks()` helpers. Each rule maps a block type to a question template. |
| `src/gonghaebun/pipeline/question_generator.py` | Stage C. Generates one `Question` per `(SourceBlock, Rule)` pair using deterministic string templates. `expected_answer` is always source-grounded (`block.text[:800]`). |
| `src/gonghaebun/pipeline/io.py` | Stage D. Save/load helpers for all four JSON artifact types. Sorts records by stable id, ensures UTF-8 + `ensure_ascii=False`, creates parent directories automatically. |
| `src/gonghaebun/review/review_cli.py` | Review layer. `apply_review_action` and `review_questions` are non-interactive and fully testable. `run_review_cli` wraps them with stdin/stdout prompts. |
| `src/gonghaebun/bank_session.py` | Build-bank orchestrator. Calls block parser → rule engine → question generator → IO in sequence. Entry point for the CLI and for tests. |
| `src/gonghaebun/cli.py` | CLI entry point. `build-bank` subcommand added alongside existing `study` subcommand. MVP1 behavior is unchanged. |

---

## 4. CLI Usage

### Build question bank

```bash
python -m gonghaebun.cli build-bank \
  --source-local tests/data/sample_source.md \
  --document-id sample_source \
  --bank-dir tmp_mvp2_bank
```

Or with the installed console script:

```bash
gonghaebun build-bank \
  --source-local tests/data/sample_source.md \
  --document-id sample_source \
  --bank-dir tmp_mvp2_bank
```

`--document-id` is optional; inferred from `source_path.stem` when omitted.

Expected output:

```
Building question bank from: tests/data/sample_source.md
Document ID : sample_source
Output dir  : tmp_mvp2_bank

Blocks    : 9
Questions : 9

Artifacts:
  [OK] tmp_mvp2_bank/blocks.generated.json
  [OK] tmp_mvp2_bank/questions.generated.json
```

### Smoke test result (2026-05-04)

```
Blocks    : 9
Questions : 9

Artifacts:
  [OK] tmp_mvp2_bank/blocks.generated.json
  [OK] tmp_mvp2_bank/questions.generated.json
```

Sample block:

```json
{
  "block_id": "sample_source_b000001",
  "block_type": "paragraph",
  "section_title": "Sample Source — Synthetic Text for Testing",
  "start_line": 3,
  "end_line": 4
}
```

Sample question:

```json
{
  "question_id": "q_sample_source_b000001_R06_general_intuition",
  "question_type": "intuition_recall",
  "difficulty": "easy",
  "question": "Explain the main idea of the following passage from section 'Sample Source — Synthetic Text for Testing'.",
  "status": "candidate",
  "evidence": {
    "source_text": "...",
    "source_file": "...",
    "start_line": 3,
    "end_line": 4,
    "text_hash": "..."
  }
}
```

---

## 5. Review Usage

### Non-interactive (programmatic, recommended for automation)

```python
from gonghaebun.pipeline.io import load_questions, save_questions, export_accepted, save_review_records
from gonghaebun.review.review_cli import review_questions
from pathlib import Path

questions = load_questions(Path("tmp_mvp2_bank/questions.generated.json"))

actions = [
    {"question_id": "q_sample_source_b000001_R06_general_intuition",
     "action": "accept"},
    {"question_id": "q_sample_source_b000002_R06_general_intuition",
     "action": "reject"},
]

updated, records = review_questions(questions, actions)

out = Path("tmp_mvp2_bank")
save_questions(out / "questions.reviewed.json", updated)
export_accepted(updated, out / "questions.accepted.json")
save_review_records(out / "review_records.json", records)
```

### Interactive (stdin/stdout)

```python
from gonghaebun.review.review_cli import run_review_cli
from pathlib import Path

records = run_review_cli(
    questions_path=Path("tmp_mvp2_bank/questions.generated.json"),
    output_dir=Path("tmp_mvp2_bank"),
)
```

Prompt for each candidate question:

```
[a]ccept / [r]eject / [e]dit / [s]kip / [q]uit
```

On edit, prompts for updated question text and updated expected answer (blank = keep original).
EOF (piped input exhausted) is treated as quit; progress is saved.

### Smoke test result (2026-05-04, programmatic review)

```
  [OK] tmp_mvp2_bank/questions.reviewed.json
  [OK] tmp_mvp2_bank/questions.accepted.json
  [OK] tmp_mvp2_bank/review_records.json
  Accepted: 1 questions
```

---

## 6. Output Artifacts

| File | Location | Description |
|---|---|---|
| `blocks.generated.json` | `--bank-dir/` | All `SourceBlock` objects parsed from the source, sorted by `block_id`. |
| `questions.generated.json` | `--bank-dir/` | All generated `Question` objects (status = `candidate`), sorted by `question_id`. |
| `questions.reviewed.json` | `output_dir/` | All questions with updated statuses after human review. |
| `questions.accepted.json` | `output_dir/` | Only questions with `status == "accepted"`. |
| `review_records.json` | `output_dir/` | All `ReviewRecord` objects from the review session, sorted by `review_id`. |

All files use UTF-8 encoding with `indent=2` and `ensure_ascii=False`.

---

## 7. Validation Status

### pytest result (2026-05-04)

```
309 passed in ~2.0 s
```

Test breakdown:

| Test file | Tests | What it covers |
|---|---|---|
| `test_schemas.py` | 27 | Data model validation, JSON roundtrip |
| `test_block_parser.py` | 45 | Block parsing, classification, line numbers |
| `test_rule_engine.py` | 30 | Rule list, get_applicable_rules, validate_rules |
| `test_question_generation.py` | 45 | Template expansion, Evidence, determinism |
| `test_io.py` | 35 | JSON roundtrip, ordering, encoding, mutation guard |
| `test_review_export.py` | 44 | Review actions, review_questions, CLI monkeypatch |
| `test_bank_session.py` | 27 | Orchestrator, CLI, document_id propagation |
| *(existing MVP1)* | 56 | Regression: unchanged |

### Smoke test (build-bank)

```bash
python -m gonghaebun.cli build-bank \
  --source-local tests/data/sample_source.md \
  --document-id sample_source \
  --bank-dir tmp_mvp2_bank
```

Result: **PASS** — 9 blocks, 9 questions generated.

### Smoke test (review)

Programmatic review via `review_questions`:
Result: **PASS** — all 5 output files written, 1 accepted question exported.

---

## 8. Known Limitations

- **Template questions are simple.** Generated questions use fixed string templates
  (`"State the definition or key concept from section '...'."` etc.). They are
  structurally sound but not refined by an LLM. Human review is required before use.

- **`expected_answer` is source-grounded, not a refined answer.** It is
  `block.text[:800]` — the raw source passage the question was derived from.
  This makes it auditable but not immediately usable as a model answer.

- **`document_id` is not sanitised.** When inferred from `source_path.stem`, any
  spaces or special characters are passed through unchanged. Provide a clean
  alphanumeric slug via `--document-id` if the filename is unusual.

- **`review_index` is per-session, not per-question-bank.** Calling `run_review_cli`
  twice on the same file will produce `review_id` values starting at `_000000`
  again, which may collide with records from the first session. Callers that need
  globally unique review ids should manage `save_review_records` themselves.

- **`unknown` block type receives no applicable rule.** Blocks classified as
  `"unknown"` (no structural marker detected) produce zero questions. Add an
  `"any"` rule to `RULES` to cover all block types uniformly.

- **No interactive review CLI entry point.** `run_review_cli` must be called
  from Python. A `gonghaebun review-bank` CLI subcommand is deferred to MVP3.

- **No MVP3 study session yet.** Accepted questions are not yet fed back into a
  study session, graded, or scheduled for spaced repetition.

- **No database.** All persistence is flat JSON files. Large question banks
  (thousands of questions) may require migration to a proper store.

- **No LLM grading.** Answer evaluation and scoring is not implemented.

---

## 9. MVP2 Completion Criteria

| Criterion | Status |
|---|---|
| Parse source into SourceBlock objects | ✅ `block_parser.py` |
| Attach source Evidence to every Question | ✅ `question_generator.py`, `models/question_bank.py` |
| Generate deterministic Question objects | ✅ `question_generator.py` |
| Save generated artifacts as JSON | ✅ `io.py` |
| Human review support (accept/reject/edit/skip) | ✅ `review_cli.py` |
| Accepted question export | ✅ `io.export_accepted` |
| `build-bank` CLI subcommand | ✅ `cli.py` |
| 309 tests pass (including 56 MVP1 regression tests) | ✅ |

**MVP2 is complete.**

---

## 10. Next Step: MVP3

MVP3 will close the loop from question bank back to the learner:

```
accepted question bank
  ─▶ study session
      ─▶ present questions to learner
      ─▶ collect answer attempts
      ─▶ self-score / LLM-score answers
      ─▶ update mastery levels
      ─▶ review scheduling (spaced repetition)
      ─▶ STUDY.md updated with question performance
```

Preparatory work for MVP3:
- Design `AnswerAttempt` and `QuestionPerformance` data models.
- Add a `review-bank` CLI subcommand calling `run_review_cli`.
- Integrate accepted questions into the MVP1 `StudySession` output.
- Optionally add a real LLM adapter (`AnthropicClient`) for answer grading.

---

## 11. Do-Not-Touch / Do-Not-Commit Paths

These paths are git-ignored and must never be committed:

| Path | Reason |
|---|---|
| `data/private/` | Private copyrighted source material |
| `data/gonghaebun/` | Runtime user data and STUDY.md |
| `runs/` | MVP1 session output artifacts |
| `tmp_runs/` | MVP1 smoke test output |
| `tmp_STUDY.md` | MVP1 smoke test STUDY.md |
| `tmp_mvp2_bank/` | MVP2 smoke test output |
| `docs/brainstorming/paper-corpus/scripts/` | Separate pipeline — do not modify |

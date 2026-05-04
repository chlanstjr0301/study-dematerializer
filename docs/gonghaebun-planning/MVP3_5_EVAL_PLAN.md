# MVP3.5 — Engine Quality Gate Evaluation Plan

## Overview

MVP3.5 adds an evaluation framework that measures the grading engine's reliability across
6 quality dimensions before MVP4 (local web UI) is built.

The framework operates in two modes:
- **Mock mode** (offline, CI-safe): injects fixed JSON per golden entry via `_FixtureLLMClient`
- **LLM mode** (requires `OPENAI_API_KEY`): sends real prompts to OpenAI and measures actual model behavior

---

## Setup

### 1. Copy and configure `.env`

```bash
cp .env.example .env
# Edit .env and add your API key and preferred models:
# OPENAI_API_KEY=sk-...
# OPENAI_MODEL=gpt-5.4-mini          # default eval model
# OPENAI_BASELINE_MODEL=gpt-5.5      # optional higher-quality baseline
```

`.env` is git-ignored. `.env.example` is tracked and contains no secrets.

### 2. Verify API key

```bash
echo $OPENAI_API_KEY   # if exported in shell
# or
cat .env               # if stored in .env file
```

---

## Evaluation Dimensions

| # | Dimension | What it checks |
|---|-----------|----------------|
| 1 | `schema_parse` | LLM response parses into valid `GradingResult` |
| 2 | `wrong_to_solid` | Wrong answers are NOT graded as solid (critical safety check) |
| 3 | `misconception_detection` | Known misconceptions appear in `errors` field |
| 4 | `missing_elements_overlap` | Missing key terms appear in `missing_elements`, grounded in expected_answer |
| 5 | `study_md_roundtrip` | Full pipeline (session → STUDY.md) produces valid output |
| 6 | `visualization_sanity` | All 5 visualization artifacts exist with correct schema |

---

## Golden Set

```
evals/golden_set/
  gc001_schema_solid.json         schema_parse      correct recall → solid
  gc002_schema_partial.json       schema_parse      partial recall → partial
  gc003_wrong_to_solid.json       wrong_to_solid    wrong answer → must NOT be solid
  gc004_misconception.json        misconception_detection
  gc005_missing_elements.json     missing_elements_overlap
  gc006_integration.json          study_md_roundtrip + visualization_sanity
  gc007_schema_failure.json       expected_schema_failure (mock only)
```

All evidence text is synthetic — no private Rudin source material is used.

---

## Smoke Commands

### Mock eval (no API key, CI-safe)

```bash
python evals/run_grading_eval.py --grader mock
cat evals/grading_eval_report.md
```

### Real LLM eval (default model)

```bash
export OPENAI_API_KEY=sk-...

# Standard eval — gpt-5.4-mini (default)
python evals/run_grading_eval.py --grader llm
cat evals/grading_eval_report.md

# Optional baseline eval — gpt-5.5 (higher quality, use for a subset of golden cases)
python evals/run_grading_eval.py --grader llm --model gpt-5.5
cat evals/grading_eval_report.md
```

### CLI-level LLM smoke test

```bash
# Prerequisites: build bank and accept questions first
python -m gonghaebun.cli build-bank \
  --source-local tests/data/sample_source.md \
  --document-id sample_source \
  --bank-dir tmp_mvp3_5_bank

python -c "
from pathlib import Path
from gonghaebun.pipeline.io import load_questions, export_accepted
qs = load_questions(Path('tmp_mvp3_5_bank/questions.generated.json'))
for q in qs: q.status = 'accepted'
export_accepted(qs, Path('tmp_mvp3_5_bank/questions.accepted.json'))
"

# Run one real LLM recall-session with a default answer (gpt-5.4-mini)
python -m gonghaebun.cli recall-session \
  --questions tmp_mvp3_5_bank/questions.accepted.json \
  --concept sample_source \
  --study-md tmp_mvp3_5_bank/STUDY_REAL.md \
  --runs-dir tmp_mvp3_5_bank/runs_real \
  --limit 1 \
  --grader llm \
  --model gpt-5.4-mini \
  --no-interactive \
  --default-answer "A compact set is one where every open cover has a finite subcover."

# Optional: run with baseline model for higher-quality grading
python -m gonghaebun.cli recall-session \
  --questions tmp_mvp3_5_bank/questions.accepted.json \
  --concept sample_source \
  --study-md tmp_mvp3_5_bank/STUDY_REAL_BASELINE.md \
  --runs-dir tmp_mvp3_5_bank/runs_baseline \
  --limit 1 \
  --grader llm \
  --model gpt-5.5 \
  --no-interactive \
  --default-answer "A compact set is one where every open cover has a finite subcover."
```

---

## Metrics Reference

| Metric | Target | Critical? |
|--------|--------|-----------|
| `schema_parse_success_rate` | 1.0 | Yes — exit 1 if < 1.0 |
| `expected_schema_failure_handled` | true | Yes — exit 1 if false (mock mode) |
| `wrong_to_solid_count` | 0 | Yes — exit 1 if > 0 |
| `misconception_error_detection_rate` | ≥ 0.8 | No |
| `missing_elements_overlap` | ≥ 0.5 | No |
| `needs_human_review_rate` | < 0.2 | No |
| `average_confidence` | informational | No |
| `average_accuracy_by_label` | informational | No |

---

## gc007 — Expected Schema Failure

`gc007_schema_failure.json` tests that malformed LLM output raises `LLMResponseError`.

- **Mock mode**: runs gc007; expects `LLMResponseError`; `expected_schema_failure_handled` = true/false
- **LLM mode**: gc007 is **skipped** (it requires injected malformed JSON, not real LLM output)
- gc007 is **never** counted in `schema_parse_success_rate`

---

## Output Structure

```
evals/
  golden_set/           committed golden entries (synthetic text only)
  eval_utils.py         importable eval logic
  run_grading_eval.py   CLI runner
  grading_eval_report.md  last run report (overwritten each run)
  runs/                 LLM mode per-run outputs (git-ignored)
    {timestamp}/
      results.json      per-case GradingResult fields (no raw model output)
```

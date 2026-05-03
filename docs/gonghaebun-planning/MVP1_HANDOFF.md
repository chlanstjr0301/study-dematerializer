# Gonghaebun MVP 1 — Handoff Document

## 1. Current Implementation Status

- **MVP 1 source-grounded CLI skeleton: implemented**
- `pytest` result: **56 passed, 0 failed**
- Smoke test with synthetic source (`tests/data/sample_source.md`): **passed**
- Smoke test with private Rudin source (`data/private/rudin/rudin_1.1_to_2.42_ocr_extract_normalized.md`): **passed**
- Source coverage for compactness from private Rudin file: **sufficient** (8 distinct keywords found)

---

## 2. Files Created / Major Components

```
pyproject.toml                        # package build config; entry point: gonghaebun.cli:main

src/gonghaebun/
├── __init__.py
├── __main__.py                       # enables python -m gonghaebun
├── cli.py                            # argparse CLI; enables python -m gonghaebun.cli
├── session.py                        # top-level orchestrator (Stages 0–7)
├── models/
│   ├── concept.py                    # Concept, MasteryLevel
│   ├── graph.py                      # PrerequisiteGraph + cycle detection
│   ├── representations.py            # RepresentationSet (5 types)
│   ├── session_models.py             # StudySession, RecallAttempt, MasteryUpdate
│   └── source_models.py             # SourceManifest, SourceWindow, SourceCoverage
├── knowledge/
│   └── real_analysis.py             # CONCEPTS, PREREQUISITE_EDGES, CONCEPT_KEYWORDS
├── llm/
│   ├── base.py                       # LLMClient ABC
│   └── mock.py                       # MockLLMClient (fixture-backed, no network)
├── pipeline/
│   ├── source_loader.py              # Stage 0: load, hash, extract windows
│   ├── concept_resolver.py           # Stage 1: validate concept input
│   ├── graph_builder.py              # Stage 2: build prerequisite DAG
│   ├── representation_gen.py         # Stage 3: generate 5 representations
│   ├── misconception_checker.py      # Stage 4: identify misconceptions
│   ├── self_explanation.py           # Stage 5: generate self-explanation prompt
│   ├── recall_orchestrator.py        # Stage 6: generate recall tasks
│   └── study_writer.py              # Stage 7: write STUDY.patch.md + STUDY.md
├── prompts/
│   ├── __init__.py                   # load_prompt() helper
│   ├── global_system.txt
│   ├── stage1_concept_resolver.txt
│   ├── stage2_graph_builder.txt
│   ├── stage3_{formal,intuitive,visual,counterexample,proof_schema}.txt
│   ├── stage4_misconception_checker.txt
│   ├── stage5_self_explanation_evaluator.txt
│   └── stage6_recall_orchestrator.txt
└── study_md/
    ├── parser.py                     # parse STUDY.md → dict[str, ConceptRecord]
    └── writer.py                     # generate_patch, apply_patch, _write_study_md

tests/
├── __init__.py
├── data/sample_source.md             # synthetic source (not Rudin text)
├── fixtures/compactness/             # 6 JSON fixture files for MockLLMClient
│   ├── concept_resolved.json
│   ├── prerequisite_graph.json
│   ├── representations.json
│   ├── misconceptions.json
│   ├── self_explanation_eval.json
│   └── recall_tasks.json
├── test_models.py
├── test_knowledge.py
├── test_study_md.py
├── test_source_loader.py
└── test_mock_session.py              # end-to-end integration, verifies all 10 artifacts

examples/STUDY.sample.md             # reference format for STUDY.md
data/.gitkeep                         # placeholder; data/ is git-ignored at runtime
```

---

## 3. Install Command

```bash
pip install -e .
```

---

## 4. Test Command

```bash
python -m pytest tests/ -q
```

Expected output: `56 passed` in < 2 seconds. No `ANTHROPIC_API_KEY` required.

---

## 5. Smoke Test — Synthetic Source

```bash
python -m gonghaebun.cli study compactness \
  --source-local tests/data/sample_source.md \
  --mock \
  --no-interactive \
  --runs-dir tmp_runs \
  --study-md tmp_STUDY.md
```

`tmp_runs/` and `tmp_STUDY.md` are git-ignored. Remove after testing.

---

## 6. Smoke Test — Private Rudin Source

```bash
python -m gonghaebun.cli study compactness \
  --source-local data/private/rudin/rudin_1.1_to_2.42_ocr_extract_normalized.md \
  --mock \
  --no-interactive \
  --runs-dir tmp_runs \
  --study-md tmp_STUDY.md
```

The private source file is not committed. If absent, the CLI exits with:

```
Error: source material is required; Gonghaebun does not generate study
sessions from model prior alone. Provide --source-local <path>.
```

---

## 7. Expected Output Artifacts

All 10 files are written to `runs/{session_id}/` on each run:

| # | Artifact | Stage |
|---|----------|-------|
| 1 | `session.json` | metadata + source refs |
| 2 | `source_manifest.json` | Stage 0: hash, keywords, coverage |
| 3 | `source_excerpt.md` | Stage 0: bounded windows only |
| 4 | `concept_decomposition.json` | Stage 1: concept metadata |
| 5 | `prerequisite_graph.json` | Stage 2: DAG |
| 6 | `representation_cards.md` | Stage 3: 5 representations |
| 7 | `self_explanation_prompt.md` | Stage 5: prompt template |
| 8 | `diagnosis.json` | Stage 4: misconceptions |
| 9 | `recall_tasks.md` | Stage 6: White Recall tasks |
| 10 | `STUDY.patch.md` | Stage 7: session diff |

`STUDY.md` is updated at the path given by `--study-md` (not inside `runs/`).

---

## 8. Source Extraction Result — Private Rudin Smoke Test

From `source_manifest.json` produced by the private Rudin source run:

```json
{
  "source_hash": "sha256:692b7cf7f7798c50979f4d0ba69e337a2c408cca9df4d3b7fc81422d57318043",
  "source_coverage": "sufficient",
  "keywords_found": [
    "closed and bounded",
    "compact",
    "compactness",
    "cover",
    "finite subcover",
    "limit point",
    "open cover",
    "perfect"
  ],
  "windows_extracted": 2,
  "excerpt_chars": 8268,
  "excerpt_capped": false,
  "grounding_mode": "local_private_source"
}
```

8 distinct keywords found → coverage: **sufficient** (threshold: ≥ 4).

---

## 9. Known Limitations

- **Mock LLM only.** No real LLM provider is integrated. All LLM outputs come from fixture files in `tests/fixtures/compactness/`.
- **No real LLM provider.** `anthropic`, `openai`, and similar packages are not dependencies.
- **No web UI, TUI, or streaming.**
- **No embeddings or semantic search.**
- **No OCR pipeline.**
- **Compactness only.** `connectedness` and `uniform_continuity` are concept stubs in the knowledge base but have no full pipeline support.
- **Output quality not yet reviewed.** Fixture content (representations, misconceptions, recall tasks) is mathematically plausible but has not been reviewed by a domain expert.
- **`source_excerpt.md` may contain private copyrighted text.** This file is written to `runs/` which is git-ignored. It must remain runtime-only and must never be committed.

---

## 10. Next Tasks

- Review `source_loader.py` edge cases (large files, multi-byte characters, keyword overlap)
- Inspect the generated `source_excerpt.md` quality for the Rudin source
- Verify the 10-artifact contract holds across repeated sessions and STUDY.md updates
- Strengthen schema validation on `session.json` and `source_manifest.json`
- Add question bank / evaluation rubric (future)
- **Prepare MVP 1.5 real LLM adapter plan** — design `AnthropicClient` adapter following `LLMClient` ABC — **do not implement yet**

---

## 11. Do-Not-Touch / Do-Not-Commit Paths

These paths are git-ignored and must never be committed:

| Path | Reason |
|------|--------|
| `data/private/` | Private copyrighted source material |
| `data/gonghaebun/` | Runtime user data and STUDY.md |
| `runs/` | Session output artifacts |
| `tmp_runs/` | Smoke test output |
| `tmp_STUDY.md` | Smoke test STUDY.md |
| `docs/brainstorming/paper-corpus/scripts/` | Separate pipeline — do not modify |

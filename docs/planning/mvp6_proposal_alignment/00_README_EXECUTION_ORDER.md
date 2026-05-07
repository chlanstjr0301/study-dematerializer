# 00 — README & Execution Order

## Purpose

This planning pack defines the MVP6 alignment work that restores Gonghaebun to its
core product identity: an AI study compiler that diagnoses understanding failures and
drives learners through representation-specific mastery, not a generic question-bank
or flashcard system.

The pack contains 11 documents (00–10) that together form a complete, implementation-ready
blueprint. A future Claude Code session should be able to pick up any document and implement
it step-by-step without ambiguity.

---

## MVP Boundary Definitions

### MVP6 — Proposal Alignment (this pack)

**Theme**: Ground Truth Cards + Mapping Tasks + Confusion Map + Rubric Evaluator

Scope:
- Ground Truth Card system (`data/gonghaebun/default/cards/`)
- Mapping Task Engine (3 mapping types, API, models)
- Confusion Map (per-session diagnostic artifact, API, UI panel)
- 7-step study session (add mapping step between representations and misconceptions)
- Rubric-based evaluator with deterministic/mock mode
- Human agreement evaluation harness scaffolding
- Demo golden run for compactness vertical slice
- All mastery scoring restricted to formal, counterexample, proof_schema + mappings
- Intuitive/visual are learning aids only (no automatic mastery scoring)

**Not in MVP6**:
- Real LLM activation as default
- Multi-concept session plans
- Spaced repetition algorithm changes beyond current schedule
- User auth / login / multi-user
- Database migration (stay file-based)
- PDF/OCR source expansion
- New domains beyond real analysis
- Broad concept expansion beyond 3 seeds + stubs
- UI polish / animations / i18n library
- Cloud deployment / CI/CD pipeline
- Mobile responsive design

### MVP7 — LLM-Grounded Evaluation (future)

Theme: Activate card-grounded LLM evaluation after human agreement gates pass.

- Real LLM grading gated by human agreement metrics
- Card-grounded prompt engineering for structured output
- Cost/call budget enforcement
- Rubric v2 refinement based on agreement data
- Extended golden set (20+ cases)

### MVP8 — Prerequisite Drill-Down (future)

Theme: Make prerequisite graph actionable.

- Prerequisite concept sessions (drill into metric_space, open_cover, etc.)
- Cross-session confusion map accumulation
- Multi-session learning plan generation
- Prerequisite mastery gates before advancing

### MVP9 — Review & Retention Loop (future)

Theme: Close the spaced repetition loop with real data.

- Adaptive review scheduling based on confusion map history
- Forgetting curve estimation
- Cross-concept mastery dashboard
- Session history analytics

---

## Recommended Implementation Order

### Phase 1: Foundation (implement first, no API changes)

| Step | Document | What |
|------|----------|------|
| 1 | 03 | Define and write compactness Ground Truth Card JSON |
| 2 | 03 | Define Pydantic models: GroundTruthCard, MappingTask, MappingResult, ConfusionMap |
| 3 | 06 | Define Rubric schema and deterministic evaluator |
| 4 | 03 | Define session artifact directory layout additions |

### Phase 2: Engine (backend services, no frontend)

| Step | Document | What |
|------|----------|------|
| 5 | 04 | Implement card loader service |
| 6 | 04 | Implement mapping task engine (generate from card) |
| 7 | 04 | Implement confusion map builder service |
| 8 | 04 | Implement mapping submit + confusion map update |
| 9 | 06 | Implement rubric-based deterministic evaluator |

### Phase 3: API (expose via HTTP)

| Step | Document | What |
|------|----------|------|
| 10 | 04 | Add mapping task + confusion map API endpoints |
| 11 | 04 | Modify study session flow to 7 steps |
| 12 | 04 | Wire confusion map updates into all step handlers |

### Phase 4: Frontend (UI changes)

| Step | Document | What |
|------|----------|------|
| 13 | 05 | Add MappingCheckStep component |
| 14 | 05 | Add ConfusionMapPanel component |
| 15 | 05 | Update StudySession to 7-step flow |
| 16 | 05 | Side-by-side layout: task + confusion map |

### Phase 5: Evaluation & Demo

| Step | Document | What |
|------|----------|------|
| 17 | 07 | Scaffold human agreement eval harness |
| 18 | 08 | Write all new tests |
| 19 | 10 | Implement and run golden demo |
| 20 | 08 | Full smoke test pass |

---

## What Must NOT Be Built Yet

1. Real LLM as default grader (keep mock default, LLM_DISABLED=1)
2. User authentication or multi-user support
3. Database (PostgreSQL, SQLite, etc.) — stay file-based
4. PDF/OCR ingestion pipeline
5. New concept domains (topology, algebra, probability)
6. Deployment automation (Docker, CI/CD, Oracle scripts)
7. Mobile or responsive design work
8. i18n library integration (Korean is hardcoded, that's fine)
9. Payment or usage tracking
10. Concurrent session support

---

## First Implementation Prompt

After this planning pack is approved, use the following prompt to begin implementation:

```
Implement MVP6 Phase 1, Step 1: Create the compactness Ground Truth Card.

Read: docs/planning/mvp6_proposal_alignment/03_DATA_MODEL_AND_ARTIFACT_PLAN.md

Create:
- data/gonghaebun/default/cards/real_analysis/compactness.card.json

The card must follow the GroundTruthCard schema defined in document 03.
Populate all fields for compactness using Rudin Ch.2 as source reference.
Include:
- Formal definition (metric space open-cover formulation)
- 3 counterexample cards ((0,1) in R, Q in R, unbounded sets)
- Proof schema (Heine-Borel equivalence outline)
- 5 misconception cards
- 3 allowed mapping tasks
- Required terms list

After creating the card, write a test:
- tests/test_ground_truth_cards.py

Test that:
- The JSON file loads and validates against GroundTruthCard schema
- All required fields are present
- prerequisite_concepts are valid slug strings
- allowed_mapping_tasks match the 3 defined types
- counterexample_cards has >= 2 entries
- misconception_cards has >= 3 entries

Run: python -m pytest tests/test_ground_truth_cards.py -v
```

---

## Document Index

| # | File | Purpose |
|---|------|---------|
| 00 | README_EXECUTION_ORDER.md | This file — overview, boundaries, sequence |
| 01 | PROPOSAL_ALIGNMENT_AUDIT.md | Gap analysis: proposal vs current repo |
| 02 | TARGET_PRODUCT_FLOW.md | Target learner flow, 7-step session |
| 03 | DATA_MODEL_AND_ARTIFACT_PLAN.md | Schemas, cards, artifacts, directory layout |
| 04 | BACKEND_API_PLAN.md | API endpoints, services, state management |
| 05 | FRONTEND_UX_PLAN.md | Components, pages, layout, UX |
| 06 | EVALUATOR_AND_RUBRIC_PLAN.md | Rubric, evaluator, misconception taxonomy |
| 07 | HUMAN_AGREEMENT_EVAL_PLAN.md | Human eval harness, metrics, gating |
| 08 | TEST_AND_SMOKE_PLAN.md | Test plan, smoke tests, CI sequence |
| 09 | IMPLEMENTATION_SEQUENCE.md | Step-by-step implementation with rollback |
| 10 | DEMO_GOLDEN_RUN_PLAN.md | Demo script, expected outputs, artifacts |

---

## Dependencies Between Documents

```
00 (this) ─────────────────────────────────────────────────
01 (audit) ← standalone, informs all others
02 (flow) ← depends on 01
03 (data model) ← depends on 02
04 (backend) ← depends on 03
05 (frontend) ← depends on 04
06 (evaluator) ← depends on 03
07 (human eval) ← depends on 06
08 (tests) ← depends on 04, 05, 06, 07
09 (sequence) ← depends on all above
10 (demo) ← depends on 03, 04, 06
```

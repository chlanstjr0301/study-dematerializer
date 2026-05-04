# CLAUDE.md — Gonghaebun Project Guide

## Project

Gonghaebun is a source-grounded AI study compiler for Real Analysis.

The core loop is:

source material
→ source-traceable question bank
→ human-reviewed accepted questions
→ White Recall session
→ self/mock/LLM grading
→ representation-specific mastery update
→ STUDY.md update
→ review-due.

## Current status

MVP1 complete:
- source-grounded concept decomposition CLI
- mock LLM pipeline
- STUDY.md writer

MVP2 complete:
- deterministic source-traceable question bank builder
- review layer
- questions.generated.json / questions.accepted.json

MVP3 complete:
- review-bank CLI
- recall-session CLI
- review-due CLI
- self/mock/LLM grading boundary
- OpenAI Responses API adapter
- StudySession / RecallAttempt / GradingResult artifacts
- STUDY.md backup + update + validation
- docs/gonghaebun-planning/MVP3_HANDOFF.md
- 490 tests passing as of MVP3 completion

## Commands

Run tests:

```bash
python -m pytest tests/ -q
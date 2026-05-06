# Gonghaebun

A source-grounded AI study compiler for Real Analysis.

## What it does

Gonghaebun turns source material (textbook sections, notes) into a structured study loop:

```
Source document
  → Source-traceable question bank
  → Human review (accept/reject/edit)
  → White Recall session (answer from memory)
  → Self/Mock/LLM grading
  → Representation-specific mastery update
  → STUDY.md update
  → Review-due scheduling
```

## Quick start

```bash
# Install
pip install -e ".[web]"

# Configure (copy and edit)
cp .env.example .env

# Start API
uvicorn apps.api.main:app --reload

# Build and serve frontend (separate terminal)
cd apps/web && npm run dev
```

Open `http://localhost:5173` in your browser.

## Environment

See `.env.example` for all configuration options.
See `docs/deployment/PRODUCTION_HARDENING.md` for production setup.

## Tests

```bash
python -m pytest tests/ -q
```

## Study Session (MVP5)

통합 학습 세션: 개념 입력 → 진단 → 선행 확인 → 5표현 학습 → 오개념 체크 → 인출 연습 → STUDY.md 업데이트.

```bash
# 소스 준비 (최초 1회)
mkdir -p data/gonghaebun/default/sources
cp tests/data/sample_source.md data/gonghaebun/default/sources/

# 실행 후 http://localhost:5173 에서 "옹골성" 입력
```

자세한 사용법: [docs/MVP5_HANDOFF.md](docs/MVP5_HANDOFF.md)

## Project status

- MVP1–MVP4: Source → Bank → Review → Recall → Mastery pipeline complete
- MVP5: Integrated 6-step study session with self-explanation + White Recall
- LLM grading with trace audit (disabled by default; set `GONGHAEBUN_LLM_DISABLED=0` + `OPENAI_API_KEY`)
- REST API (FastAPI) + React frontend

## Architecture

```
src/gonghaebun/          # Core pipeline (importable package)
apps/api/                # FastAPI application
apps/web/                # React + Vite frontend
tests/                   # pytest test suite
scripts/                 # Utility scripts (smoke_local.py)
docs/deployment/         # Deployment documentation
```

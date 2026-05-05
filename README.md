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

## Project status

- MVP1–MVP4: Source → Bank → Review → Recall → Mastery pipeline complete
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

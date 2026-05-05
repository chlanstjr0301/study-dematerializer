# Production Hardening Guide

This document covers environment variables, startup configuration, secrets management,
and backup policy for deploying Gonghaebun on a production server (e.g., Oracle Free Tier).

---

## Environment Variables

Copy `.env.example` to `.env` and adjust values. Never commit `.env`.

### Required in production

| Variable | Default | Notes |
|----------|---------|-------|
| `GONGHAEBUN_DATA_ROOT` | `data/gonghaebun/default` | **Use absolute path** in production |
| `GONGHAEBUN_API_HOST` | `127.0.0.1` | Set to `0.0.0.0` to accept external connections |
| `GONGHAEBUN_CORS_ORIGINS` | localhost origins | Set to your server's public origin |

### Optional (override sub-paths of DATA_ROOT)

| Variable | Default |
|----------|---------|
| `GONGHAEBUN_BANK_ROOT` | `{DATA_ROOT}/banks` |
| `GONGHAEBUN_RUNS_DIR` | `{DATA_ROOT}/runs` |
| `GONGHAEBUN_STUDY_MD` | `{DATA_ROOT}/STUDY.md` |
| `GONGHAEBUN_SOURCES_DIR` | `{DATA_ROOT}/sources` |

### Grader / LLM

| Variable | Default | Notes |
|----------|---------|-------|
| `GONGHAEBUN_GRADER` | `mock` | `mock` or `llm` |
| `GONGHAEBUN_LLM_DISABLED` | `1` | **Keep 1** unless you have an API key |
| `GONGHAEBUN_LLM_MAX_CALLS_PER_SESSION` | `20` | Max LLM calls per recall session |
| `GONGHAEBUN_LLM_TIMEOUT_SECONDS` | `30` | Per-call timeout |
| `OPENAI_API_KEY` | (none) | Required only when `LLM_DISABLED=0` |

### Server

| Variable | Default | Notes |
|----------|---------|-------|
| `GONGHAEBUN_API_PORT` | `8000` | Port for uvicorn |
| `GONGHAEBUN_SERVE_FRONTEND` | `1` | Serve `apps/web/dist/` as SPA |

---

## Startup

### Local development

```bash
# Terminal 1: API
uvicorn apps.api.main:app --reload

# Terminal 2: Frontend dev server (with hot reload)
cd apps/web && npm run dev
```

### Production (single process)

```bash
# Build frontend first
cd apps/web && npm run build && cd ../..

# Start API (serves both API + built SPA)
uvicorn apps.api.main:app --host 0.0.0.0 --port 8000
```

### Verify deployment

```bash
python scripts/smoke_local.py --base-url http://your-server:8000
```

---

## Secrets

- `OPENAI_API_KEY` is only needed when `GONGHAEBUN_LLM_DISABLED=0`
- Never commit `.env` or any file containing `sk-...` keys
- `.gitignore` excludes `.env` and `.env.*` (except `.env.example`)
- The `.env.example` file is safe to commit — it contains no real secrets

---

## Data and Backup

All user data lives under `GONGHAEBUN_DATA_ROOT`:

```
data/gonghaebun/default/
  STUDY.md          ← mastery tracker (most important)
  STUDY.bak         ← automatic backup before each update
  banks/            ← question banks per concept
  runs/             ← session artifacts (read-only after creation)
  sources/          ← uploaded source documents
```

### Backup policy

- `STUDY.md` is backed up automatically to `STUDY.bak` before each session
- Back up `DATA_ROOT` periodically to external storage
- `runs/` and `banks/` are reproducible from sources; `STUDY.md` is not

---

## SPA Deep-Link Routing

The API serves the React SPA from `apps/web/dist/` when `SERVE_FRONTEND=1`.
Deep links (`/sources`, `/recall`, `/concept-compiler`) are handled by an explicit
catch-all route that returns `index.html` for non-API paths.

Unknown `/api/*` paths always return 404 JSON, never SPA HTML.

To disable SPA serving (e.g., serving frontend from a separate CDN):
```bash
GONGHAEBUN_SERVE_FRONTEND=0
```

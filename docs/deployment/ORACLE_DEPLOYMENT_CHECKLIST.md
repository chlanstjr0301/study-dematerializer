# Oracle Free Tier Deployment Checklist

Pre-deploy checklist for Gonghaebun on Oracle Cloud Always Free (ARM).

---

## Pre-Deploy

- [ ] `python -m pytest tests/ -q` — all tests pass locally
- [ ] `cd apps/web && npm run build` — frontend build succeeds
- [ ] `.env` created from `.env.example` with production values
- [ ] `GONGHAEBUN_DATA_ROOT` set to absolute path (e.g., `/home/ubuntu/gonghaebun/data`)
- [ ] `GONGHAEBUN_API_HOST=0.0.0.0`
- [ ] `GONGHAEBUN_CORS_ORIGINS` set to your server's origin (not localhost)
- [ ] `GONGHAEBUN_LLM_DISABLED=1` unless you have an API key configured
- [ ] `OPENAI_API_KEY` set only if `LLM_DISABLED=0`
- [ ] No real secrets in `.env.example` or committed files

## Deployment

- [ ] Source code copied/cloned to server
- [ ] Python virtualenv created: `python -m venv .venv && source .venv/bin/activate`
- [ ] Package installed: `pip install -e ".[web]"`
- [ ] Frontend built: `cd apps/web && npm run build`
- [ ] Data directory created: `mkdir -p $GONGHAEBUN_DATA_ROOT`
- [ ] Bootstrap via API: `POST /api/project/bootstrap`

## Verification

- [ ] `python scripts/smoke_local.py --base-url http://your-server:8000` — all 7 checks pass
- [ ] `GET /api/health` → `{"status": "ok"}`
- [ ] `GET /api/ready` → `{"ready": true, ...}`
- [ ] SPA deep links work: open `http://your-server:8000/sources` in browser → app loads
- [ ] Unknown API path: `GET /api/does-not-exist` → 404 JSON (not SPA HTML)

## Security

- [ ] Oracle security list: only allow ports 22 (SSH) and 8000 (API) from trusted IPs
- [ ] Firewall (`ufw` or `firewalld`) configured
- [ ] HTTPS configured via Nginx reverse proxy (see `nginx.conf.template`)
- [ ] No root process ownership for uvicorn

## Post-Deploy

- [ ] `STUDY.md` initialized via `POST /api/project/bootstrap`
- [ ] Backup cron job configured for `GONGHAEBUN_DATA_ROOT`
- [ ] Log rotation configured for uvicorn output

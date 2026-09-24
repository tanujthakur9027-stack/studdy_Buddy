# Render + Streamlit Cloud Deployment Plan

## Overview

Separate the backend (FastAPI) and frontend (Streamlit) into two independently deployed
services to permanently eliminate the "Oh no" crash, `/healthz` resets, and all
subprocess-related instability.

- **Backend** → Render.com (Docker, free tier, existing `render.yaml` + `Dockerfile`)
- **Frontend** → Streamlit Cloud (existing `streamlit_app/app.py`)

When `BACKEND_URL` is set as a Streamlit secret (pointing to Render), the Streamlit app
skips the local subprocess entirely. When run locally without `BACKEND_URL`, it falls back
to launching the backend as a subprocess on `localhost:8000` — local dev unchanged.

### Success Condition
- Render backend: `GET https://<your-app>.onrender.com/health` returns HTTP 200
- Streamlit Cloud: app loads without "Oh no" crash

### Rollback Policy
- **Each sub-task is one git commit**
- After each sub-task, the user tests before moving on
- If the sub-task test fails → immediately `git revert <commit>` that sub-task
- If the overall deploy fails after all sub-tasks → `git revert HEAD~N` back to
  commit `cb899e8` (current working state)
- The app must work fully on localhost at all times between sub-tasks

---

## Sub-Tasks

---

### Sub-Task 1 — Make BACKEND_URL configurable in `api_client.py`

**Status:** `[ ] pending`

**Intent:**
`BACKEND_URL` is currently hardcoded to `"http://localhost:8000"` in two places.
Centralise it in `api_client.py` so it reads from Streamlit secret → env var → localhost fallback.
All pages import `BACKEND_URL` from `api_client`, so changing it here fixes every usage automatically.
This sub-task is safe to roll back independently — it only changes constant resolution, not behaviour.

**Rollback:** `git revert <this commit>` — no side effects, local dev keeps working.

**Expected Outcomes:**
- `BACKEND_URL` in `api_client.py` is resolved dynamically at import time
- Resolution order: `st.secrets["BACKEND_URL"]` → `os.environ["BACKEND_URL"]` → `"http://localhost:8000"`
- No other file changes needed for API call URLs (all usages import from `api_client`)
- Local dev still works: no `BACKEND_URL` secret set → falls back to localhost

**Todo List:**
- In `streamlit_app/core/api_client.py`: add `import os` to imports (line ~13)
- Replace the hardcoded `BACKEND_URL = "http://localhost:8000"` constant with a
  `_get_backend_url()` function that tries `st.secrets`, then `os.environ`, then falls back
- Assign `BACKEND_URL = _get_backend_url()` so existing import sites are unaffected
- Run `python -m py_compile streamlit_app/core/api_client.py` — must pass
- Commit: `"feat(deploy): make BACKEND_URL configurable via secret/env"`

**Verify before moving on:**
- Run app locally — backend still starts, login works → proceed to Sub-Task 2
- If broken → `git revert HEAD` and stop

**Relevant Context:**
- `streamlit_app/core/api_client.py` line 20 — hardcoded constant to replace
- `streamlit_app/core/api_client.py` line 41 — `api_request()` uses `BACKEND_URL`
- `streamlit_app/core/api_client.py` line 84 — `stream_sse()` uses `BACKEND_URL`
- Pages that import `BACKEND_URL`: `classes.py:23`, `admin.py:15`, `learning.py:22`

---

### Sub-Task 2 — Make `app.py` skip subprocess when remote `BACKEND_URL` is configured

**Status:** `[ ] pending`

**Intent:**
When `BACKEND_URL` points to Render (non-localhost), skip the local subprocess entirely.
When running locally, keep the existing subprocess behaviour unchanged.
Also removes the duplicate `BACKEND_URL = "http://localhost:8000"` from `app.py` line 33
and imports it from `api_client` instead (single source of truth).

**Rollback:** `git revert <this commit>` — restores subprocess behaviour fully.

**Expected Outcomes:**
- `app.py` no longer defines its own `BACKEND_URL` — imports from `core.api_client`
- If `BACKEND_URL` is non-localhost: `_backend_ready_event.set()` is called immediately,
  `_launch_backend()` is never called, loading overlay is never shown
- If `BACKEND_URL` is localhost (local dev): existing subprocess + health-poll unchanged
- A keep-alive background thread pings `BACKEND_URL/health` every 10 minutes when using
  a remote backend (prevents Render free tier 15-min idle sleep)

**Todo List:**
- Remove `BACKEND_URL = "http://localhost:8000"` from `app.py` line 33
- Add import: `from core.api_client import BACKEND_URL` (after api_client is on sys.path)
- Add helper `_is_remote_backend() -> bool`: returns True when BACKEND_URL does not
  start with `http://localhost` or `http://127.0.0.1`
- Add `_start_keepalive()` function: daemon thread that loops, sleeps 600 s, then
  does `requests.get(BACKEND_URL + "/health", timeout=5)` silently — only started
  when `_is_remote_backend()` is True
- In the main script body (after `_launch_backend()` call site):
  - `if _is_remote_backend(): _backend_ready_event.set(); _start_keepalive()`
  - `else: _launch_backend()`  (existing behaviour)
- Run `python -m py_compile streamlit_app/app.py` — must pass
- Commit: `"feat(deploy): skip subprocess when BACKEND_URL is remote"`

**Verify before moving on:**
- Run locally (no `BACKEND_URL` set) — subprocess still starts, login works → proceed
- If broken → `git revert HEAD` and stop

**Relevant Context:**
- `streamlit_app/app.py` line 33 — duplicate `BACKEND_URL` to remove
- `streamlit_app/app.py` lines 47–48 — `_backend_ready_event`, `_backend_failed_event`
- `streamlit_app/app.py` lines 85–96 — `_wait_for_backend()` uses `BACKEND_URL`
- `streamlit_app/app.py` line 181 — `_launch_backend()` call to conditionalise
- `streamlit_app/app.py` lines 186–236 — loading overlay block

---

### Sub-Task 3 — Update `render.yaml` with all required env vars

**Status:** `[ ] pending`

**Intent:**
The existing `render.yaml` is missing `SECRET_KEY`, admin seed vars, and auth settings.
Without `SECRET_KEY`, the backend startup guard in `main.py` raises `RuntimeError` and
the container fails to start. Add all missing required vars.

**Rollback:** `git revert <this commit>` — render.yaml goes back to previous state.
No effect on local dev (render.yaml is only used by Render).

**Expected Outcomes:**
- `render.yaml` contains every env var the backend needs to boot
- `SECRET_KEY`, `ADMIN_SEED_EMAIL`, `ADMIN_SEED_PASSWORD` are `sync: false`
  (user fills them in the Render dashboard — never committed to git)
- `CORS_ORIGINS` has a comment noting it should be set to the Streamlit Cloud URL
- Keep-alive is not needed server-side (handled client-side in Sub-Task 2)

**Todo List:**
- Open `render.yaml` and add to `envVars`:
  - `SECRET_KEY` — `sync: false` (required, never set in yaml)
  - `ADMIN_SEED_EMAIL` — `sync: false`
  - `ADMIN_SEED_PASSWORD` — `sync: false`
  - `ACCESS_TOKEN_EXPIRE_MINUTES` — `value: "1440"`
  - `AUTH_REQUIRED` — `value: "true"`
  - `RATE_LIMIT_PER_MINUTE` — `value: "60"`
  - `DATABASE_URL` — `value: "sqlite+aiosqlite:///./studybuddy.db"` (relative to `/app` in container)
- Update `CORS_ORIGINS` comment: note it should be changed to the Streamlit Cloud URL
  after the frontend is deployed
- Commit: `"feat(deploy): add required env vars to render.yaml"`

**Verify before moving on:**
- No Python files changed in this sub-task — no local test needed
- Visual check: open `render.yaml`, confirm all vars are present
- If Render deploy fails later due to this → `git revert HEAD` on this commit

**Relevant Context:**
- `render.yaml` — current file missing auth vars
- `backend/main.py` lines 97–102 — `SECRET_KEY` startup guard that rejects empty key
- `backend/.env.example` — complete list of every env var the backend accepts

---

### Sub-Task 4 — Document `BACKEND_URL` in `secrets.toml.example`

**Status:** `[ ] pending`

**Intent:**
The secrets example file is the canonical reference for what to put in the Streamlit Cloud
dashboard. Add `BACKEND_URL` so users know to set it. This is documentation only.

**Rollback:** `git revert <this commit>` — trivial, doc-only change.

**Expected Outcomes:**
- `streamlit_app/.streamlit/secrets.toml.example` contains `BACKEND_URL` entry
  with a placeholder Render URL and a clear comment

**Todo List:**
- Add to `secrets.toml.example` (at top, before other vars):
  ```toml
  # Set to your Render backend URL for Streamlit Cloud deployment.
  # Leave unset (or delete this line) for local dev — falls back to localhost:8000.
  BACKEND_URL = "https://your-app-name.onrender.com"
  ```
- Commit: `"docs: add BACKEND_URL to secrets.toml.example"`

**Relevant Context:**
- `streamlit_app/.streamlit/secrets.toml.example` — template file

---

### Sub-Task 5 — Update `DEPLOY.md` with full Render + Streamlit Cloud guide

**Status:** `[ ] pending`

**Intent:**
`DEPLOY.md` currently describes the subprocess model. Update it to reflect the new
split-service architecture, including exact steps for both Render and Streamlit Cloud,
the rollback procedure, and the keep-alive behaviour.

**Rollback:** `git revert <this commit>` — doc-only.

**Expected Outcomes:**
- `DEPLOY.md` has a clear "Render + Streamlit Cloud" section as the primary deployment option
- Includes: Render deploy steps, Streamlit Cloud secret configuration, CORS update step,
  rollback instructions, and local dev note
- Old "Streamlit Cloud only (subprocess)" section is kept as a fallback option

**Todo List:**
- Replace the "Streamlit Cloud (Recommended)" section in `DEPLOY.md` with:
  - New "Option A: Render (backend) + Streamlit Cloud (frontend) — Recommended" section
  - Steps: deploy on Render, set secrets, get URL, deploy on Streamlit Cloud, set `BACKEND_URL`
  - Note: keep-alive thread pings every 10 min to prevent Render sleep
  - Note: SQLite resets on Render container restart (acceptable for demo/testing)
  - Note: to use PostgreSQL instead, set `DATABASE_URL=postgresql+asyncpg://...`
  - Add "Option B: Streamlit Cloud only (subprocess)" as the fallback for simple deploys
  - Add "Rollback" section: `git revert` commands to undo each sub-task
- Commit: `"docs: update DEPLOY.md for Render + Streamlit Cloud split deployment"`

**Relevant Context:**
- `DEPLOY.md` — existing deploy guide

---

## Deployment Steps After All Code Changes Are Merged

### A — Deploy Backend on Render
1. Go to [render.com](https://render.com) → New → Web Service → connect GitHub repo
2. Render detects `render.yaml` automatically → click **Deploy**
3. In Render dashboard → **Environment**, set these secrets manually:
   - `SECRET_KEY` → `python -c "import secrets; print(secrets.token_hex(32))"`
   - `ADMIN_SEED_EMAIL` → your admin email
   - `ADMIN_SEED_PASSWORD` → strong password
   - `GROQ_API_KEY` → your `gsk_...` key from console.groq.com
4. Wait for deploy → visit `https://<your-app>.onrender.com/health`
5. Must return `{"status":"ok","database":"ok",...}` → backend success ✅

### B — Deploy Frontend on Streamlit Cloud
1. Go to [share.streamlit.io](https://share.streamlit.io) → New app
2. Repo: your GitHub repo · Branch: `main` · Main file: `streamlit_app/app.py`
3. **Settings → Secrets** — paste:
   ```toml
   BACKEND_URL         = "https://<your-app>.onrender.com"
   SECRET_KEY          = "<same key as Render>"
   GROQ_API_KEY        = "gsk_..."
   ADMIN_SEED_EMAIL    = "admin@yourdomain.com"
   ADMIN_SEED_PASSWORD = "YourStrongPass123!"
   ```
4. Click **Deploy** — loads in ~10 s (no subprocess, no 90-s wait) ✅

### C — Final: Update CORS on Render
- After Streamlit Cloud gives you the app URL (e.g. `https://yourapp.streamlit.app`),
  update `CORS_ORIGINS` in Render Environment to `https://yourapp.streamlit.app`

---

## Full Rollback Commands

If the deploy fails at any point:

```bash
# Roll back individual sub-tasks (most recent first):
git revert HEAD       # undo last commit
git revert HEAD~1     # undo second-to-last, etc.

# Or roll back everything to current working state in one command:
git revert cb899e8..HEAD --no-commit
git commit -m "revert: roll back Render deploy plan — restore subprocess mode"
```

After rollback, the app runs exactly as it does today on localhost.

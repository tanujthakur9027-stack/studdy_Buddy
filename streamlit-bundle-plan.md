# Plan: Bundle FastAPI inside Streamlit — Single-Process Deployment

## Goal
Eliminate Render entirely. Run the FastAPI backend **as a subprocess** launched by the
Streamlit app, both hosted together on Streamlit Cloud's free tier. One repository,
one deployment, zero cross-service configuration, zero sleep issues, zero CORS issues.

## Approach Overview
1. `streamlit_app/app.py` starts the FastAPI backend (`uvicorn`) via `subprocess.Popen`
   before rendering any UI — only once per Streamlit Cloud worker lifecycle.
2. Streamlit calls the backend over `localhost:8000` (loopback — no CORS, no network hop).
3. Persistent data (SQLite DB, ChromaDB, uploads) lives in a writable subdirectory under
   the Streamlit app root. Streamlit Cloud provides ~1 GB of ephemeral disk per worker.
4. On startup FAISS is rebuilt from ChromaDB so vector search works immediately after a
   worker restart without requiring re-uploads.
5. All Python dependencies (FastAPI + Streamlit) are listed in one
   `streamlit_app/requirements.txt`.

## Architecture After Change

```
Streamlit Cloud Worker (single process group)
├── streamlit run streamlit_app/app.py   ← pid 1
│     └── subprocess.Popen(uvicorn main:app --port 8000)  ← pid 2
│
│   Shared disk (ephemeral, resets on full redeploy):
│     ./data/studybuddy.db    (SQLite)
│     ./data/chroma_db/       (ChromaDB — rebuilt FAISS from here on restart)
│     ./data/uploads/         (raw uploaded files)
│
│   Requests (loopback, no CORS):
│     Streamlit → http://localhost:8000/api/...
```

## Non-Goals
- No PostgreSQL migration (SQLite is sufficient for single-user / demo use)
- No multi-worker scaling (Streamlit Cloud free tier is single instance)
- No CI/CD pipeline changes

---

## Sub-Task 1 — Merge all Python dependencies into one requirements.txt

**Status:** [ ] pending

**Intent:**
Streamlit Cloud installs packages from a single `requirements.txt` at the repo root or
inside the app directory. Currently backend deps are in `backend/requirements.txt` and
Streamlit deps are in `streamlit_app/requirements.txt`. These must be merged into a single
`streamlit_app/requirements.txt` so `streamlit run streamlit_app/app.py` has access to
every package it needs to spawn uvicorn and serve the FastAPI app.

**Expected Outcomes:**
- `streamlit_app/requirements.txt` contains every package from both old files, de-duped,
  with no version conflicts.
- `backend/requirements.txt` can be kept as-is (Dockerfile still needs it) but is no
  longer the authoritative list for the cloud deploy.

**Todo List:**
1. Read both `backend/requirements.txt` and `streamlit_app/requirements.txt`.
2. Merge into `streamlit_app/requirements.txt` — keep the strictest lower bound per package.
3. Add `uvicorn[standard]` explicitly at the top (needed to spawn the subprocess).
4. Verify no duplicate entries remain.

**Relevant Context:**
- `backend/requirements.txt` — full FastAPI stack (45+ packages)
- `streamlit_app/requirements.txt` — currently only `streamlit>=1.35.0` + `requests>=2.32.0`

---

## Sub-Task 2 — Add backend subprocess launcher to Streamlit app

**Status:** [ ] pending

**Intent:**
On the very first run of `app.py`, launch `uvicorn main:app --host 127.0.0.1 --port 8000`
as a background subprocess using `subprocess.Popen`. Use `st.session_state` to ensure
the subprocess is launched only once per Streamlit worker (not on every rerun).
Wait (with a progress spinner) until the backend's `/health` endpoint responds before
rendering any UI tabs.

**Expected Outcomes:**
- When the Streamlit page loads, the backend starts automatically — no manual step.
- If the backend is already running (page rerun), the launcher is a no-op.
- If the backend fails to start within 30 s, a clear error message is shown.
- `BACKEND_URL` is hardcoded to `http://localhost:8000` (no env var / secrets needed).

**Key Implementation Details:**
- Use `subprocess.Popen` (non-blocking). Store the `Popen` object in
  `st.session_state["_backend_proc"]`.
- Guard with `if "_backend_proc" not in st.session_state` to avoid re-launching on reruns.
- Startup probe: poll `GET http://localhost:8000/health` every 1 s, up to 30 s.
- The subprocess must be launched with `cwd=backend_dir` (the `backend/` directory) so
  relative imports and file paths resolve correctly.
- Pass env vars to the subprocess: `PYTHONPATH`, `DATABASE_URL`, `UPLOAD_DIR`,
  `CHROMA_PERSIST_DIR`, `FAISS_INDEX_DIR` — all pointing to `./data/` paths.

**Relevant Context:**
- `streamlit_app/app.py` — add launcher at the very top of `main()` before any tab render
- `backend/main.py` — the FastAPI app entry point
- `backend/config.py` — all path settings come from env vars; override via subprocess env

---

## Sub-Task 3 — Rebuild FAISS from ChromaDB on backend startup

**Status:** [ ] pending

**Intent:**
Currently when the backend restarts, `_faiss_registry` and `_faiss_global` are empty.
Queries fall back to ChromaDB (slower) but only if ChromaDB has the data. FAISS must be
rebuilt from ChromaDB's stored vectors during the `lifespan` startup so performance is
full-speed from the first request.

**Expected Outcomes:**
- On startup, `populate_faiss_from_chroma()` is called inside `lifespan`.
- If ChromaDB is empty (fresh deploy), the function is a no-op.
- If ChromaDB has N documents with M chunks each, all are loaded into
  `_faiss_registry` (per-doc) and `_faiss_global` (merged) before the first request.
- `/health` reports correct FAISS vector counts after startup.

**Key Implementation Details:**
- Add `populate_faiss_from_chroma()` to `backend/services/document_service.py`.
- The function queries ChromaDB for all stored documents grouped by `doc_id` metadata.
- For each unique `doc_id`, reconstruct a FAISS index from its chunks and store in
  `_faiss_registry[doc_id]`.
- Merge all per-doc indexes into `_faiss_global`.
- Call this function in `backend/main.py` `lifespan` after `await init_db()`.
- Wrap in `try/except` so a corrupt ChromaDB does not prevent startup.

**Relevant Context:**
- `backend/services/document_service.py` lines 44–55 — `_faiss_registry`, `_faiss_global`,
  `get_embeddings()`, `get_chroma()`
- `backend/main.py` lines 61–77 — `lifespan` context manager
- `langchain_community.vectorstores.FAISS.from_documents()` — used to build per-doc index

---

## Sub-Task 4 — Configure data paths for Streamlit Cloud

**Status:** [ ] pending

**Intent:**
Streamlit Cloud's working directory is the repo root. The backend spawned as a subprocess
has `cwd=backend/`. All data directories (SQLite, ChromaDB, uploads) must resolve to a
single `data/` folder that is the same for both the Streamlit process and the backend
subprocess, and that survives Streamlit reruns (only resets on full redeploy).

**Expected Outcomes:**
- A `data/` directory (gitignored) is auto-created at runtime under the repo root.
- Backend uses: `DATABASE_URL=sqlite+aiosqlite:///../../data/studybuddy.db`,
  `CHROMA_PERSIST_DIR=../../data/chroma_db`, `UPLOAD_DIR=../../data/uploads`.
- `render.yaml` env vars updated to match (kept for backward compat if someone still
  uses Render directly).
- `backend/.env.example` updated with the new paths.
- `data/` added to `.gitignore`.

**Relevant Context:**
- `backend/config.py` — all path settings
- `streamlit_app/app.py` — subprocess launcher (Sub-Task 2) passes the env dict
- `.gitignore` — must exclude `data/` and `streamlit_app/.streamlit/secrets.toml`

---

## Sub-Task 5 — Remove CORS requirement (loopback calls)

**Status:** [ ] pending

**Intent:**
Since Streamlit now calls the backend over `localhost`, CORS is not needed. Removing the
CORS middleware (or widening it to `*`) avoids the class of bugs where a mis-configured
`CORS_ORIGINS` blocks all API requests. The simplest fix is to allow `*` for origins
when running in bundled mode.

**Expected Outcomes:**
- `backend/config.py` default `cors_origins` changed to `"*"`.
- `render.yaml` `CORS_ORIGINS` env var updated to `"*"` as well.
- Existing CORS middleware code in `backend/main.py` is untouched (just the default value
  changes — the middleware still runs but now permits all origins).

**Relevant Context:**
- `backend/config.py` line 26 — `cors_origins` default
- `render.yaml` line ~31 — `CORS_ORIGINS` env var
- `backend/main.py` lines 98–104 — CORSMiddleware

---

## Sub-Task 6 — Write Streamlit Cloud deployment config

**Status:** [ ] pending

**Intent:**
Streamlit Cloud requires a specific file layout. We need:
1. `streamlit_app/.streamlit/config.toml` — already exists, verify it is correct.
2. No `secrets.toml` needed (BACKEND_URL is now localhost, no secrets required).
3. The app entry point (`streamlit_app/app.py`) must be specified when creating the app
   on share.streamlit.io.
4. Update `DEPLOY.md` with a simplified 3-step guide (GitHub → Streamlit Cloud, done).

**Expected Outcomes:**
- `streamlit_app/.streamlit/config.toml` has correct `maxUploadSize = 200`.
- `DEPLOY.md` updated: remove all Render / CORS / secrets steps; replace with
  "connect repo → set main file → deploy".
- A `packages.txt` file added to `streamlit_app/` listing any system-level packages
  needed by the backend (tesseract-ocr, libgl1, libglib2.0-0) — Streamlit Cloud installs
  these via `apt`.

**Relevant Context:**
- `streamlit_app/.streamlit/config.toml` — already exists
- `DEPLOY.md` — full rewrite needed
- `backend/Dockerfile` lines 6–12 — system packages needed: `libgl1`, `libglib2.0-0`,
  `libgomp1`, `tesseract-ocr`

---

## Sub-Task 7 — End-to-end smoke test checklist

**Status:** [ ] pending

**Intent:**
After implementation, verify that all 9 Streamlit tabs work correctly with the bundled
backend. This is a manual checklist, not automated tests.

**Expected Outcomes:**
- All tabs load without errors.
- Upload tab: file upload completes, doc appears in sidebar.
- Ask AI tab: question returns answer with sources.
- Quiz tab: quiz generates, submission returns grade.
- Planner tab: plan generates with day-by-day schedule.
- Feynman tab: evaluation returns score + gaps.
- Flashcards tab: deck generates, flip works.
- Cheat Sheet tab: generates and download works.
- Progress tab: loads stats (may be empty on fresh deploy).
- Backend health check (sidebar): shows `status: ok`.

**Todo List:**
1. Run `streamlit run streamlit_app/app.py` locally.
2. Confirm backend subprocess starts (check sidebar health button).
3. Upload a small PDF.
4. Test each tab in order.
5. Restart Streamlit (`Ctrl+C` + re-run) and verify FAISS rebuild: Ask AI still works
   without re-uploading.

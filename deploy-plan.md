# StudyBuddy — Deployment Plan (Groq + Render + Vercel)

## Overview

Deploy the full-stack StudyBuddy project (Next.js 14 frontend + FastAPI backend) to a
**free-tier, publicly accessible URL** using:

- **Backend** → Render (Docker, free tier, persistent disk)
- **Frontend** → Vercel (native Next.js, free tier)
- **LLM** → Groq API (replaces OpenAI for chat completions — faster + free tier)
- **Embeddings** → HuggingFace `sentence-transformers/all-MiniLM-L6-v2` (replaces
  OpenAI embeddings — fully free, runs locally inside the container)

### Why these choices

| Concern | Decision |
|---|---|
| User has Groq key, not OpenAI | Switch LLM client from `AsyncOpenAI` to `groq.AsyncGroq` |
| Groq has no embeddings API | Use HuggingFace local embeddings — free, no extra key |
| Repo does not exist yet | Sub-task 0 creates the GitHub repo via git CLI |
| FAISS is in-memory per-process | Enforce `--workers 1` in Render start command |
| No Dockerfile / render.yaml / vercel.json | Create all three in this plan |

### What changes in the code

1. `backend/config.py` — rename `openai_api_key` → `groq_api_key`, add `groq_model`,
   keep `openai_embedding_model` field name but repurpose it as HuggingFace model name
2. `backend/services/llm_service.py` — swap `AsyncOpenAI` for `groq.AsyncGroq`;
   the `.chat.completions.create()` call shape is identical (Groq is OpenAI-compatible)
3. `backend/services/document_service.py` — swap `OpenAIEmbeddings` for
   `HuggingFaceEmbeddings` from `langchain-huggingface`; `get_embeddings()` function
   only; no other changes
4. `backend/requirements.txt` — remove `openai`, `langchain-openai`; add `groq`,
   `langchain-huggingface`, `sentence-transformers`
5. `backend/.env.example` — rename key, document Groq models

### What does NOT change

- All routers, schemas, business logic — untouched
- Frontend — completely untouched (it only knows the API URL)
- FAISS / ChromaDB / retrieval logic — untouched
- All endpoint paths — untouched

---

## Sub-Task 0 — Push project to GitHub

**Intent:**
Both Render and Vercel deploy from a Git repository. The project is currently only on
the local filesystem. This sub-task creates a `.gitignore`, initialises a local Git repo,
and provides the exact commands to push to GitHub.

**Expected Outcomes:**
- `backend/.gitignore` and root `.gitignore` exist with all secrets and build artefacts
  excluded (`.env`, `chroma_db/`, `uploads/`, `faiss_indexes/`, `__pycache__/`,
  `node_modules/`, `.next/`)
- `DEPLOY.md` lists the exact `git` commands the user needs to run in a terminal
- No secrets are committed

**Todo List:**
- [ ] Create root `.gitignore` covering both frontend and backend artefacts
- [ ] Verify `backend/.env` is listed (never commit real API keys)
- [ ] In `DEPLOY.md` (created in sub-task 6), include the GitHub setup steps:
  - `git init` at repo root
  - `git add .`
  - `git commit -m "initial commit"`
  - Create repo on github.com (UI instructions)
  - `git remote add origin <url>`
  - `git push -u origin main`

**Relevant Context:**
- Project root: `c:\Users\Tanuj kumar singh\Desktop\Studdy_Buddy`
- `backend/.env` must never be committed — it holds the real Groq key
- `frontend/.env.local` must never be committed

**Status:** [ ] pending

---

## Sub-Task 1 — Switch backend from OpenAI to Groq

**Intent:**
The entire LLM layer is in two files: `llm_service.py` (chat) and the `get_embeddings()`
function in `document_service.py` (embeddings). Groq's Python SDK is OpenAI-compatible
— the `.chat.completions.create()` call shape is identical — so the diff is minimal.
Embeddings must switch to HuggingFace local because Groq provides no embeddings API.

**Expected Outcomes:**
- `backend/config.py`: `openai_api_key` → `groq_api_key`; `openai_model` →
  `groq_model` defaulting to `"llama-3.1-8b-instant"` (fast, free on Groq)
- `backend/services/llm_service.py`: imports `groq.AsyncGroq`; client initialised with
  `groq_api_key`; everything else identical
- `backend/services/document_service.py`: `get_embeddings()` returns
  `HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")`
  instead of `OpenAIEmbeddings`; import changed; no other lines touched
- `backend/requirements.txt`: `openai` and `langchain-openai` removed; `groq>=0.9.0`,
  `langchain-huggingface>=0.0.3`, `sentence-transformers>=2.7.0` added
- `backend/.env.example`: key renamed to `GROQ_API_KEY`, model to `GROQ_MODEL`

**Todo List:**
- [ ] Edit `backend/config.py`:
  - `openai_api_key: str = ""` → `groq_api_key: str = ""`
  - `openai_model: str = "gpt-4o-mini"` → `groq_model: str = "llama-3.3-70b-versatile"`
  - Remove `openai_embedding_model` field entirely (HuggingFace model is hardcoded)
- [ ] Edit `backend/services/llm_service.py`:
  - Replace `from openai import AsyncOpenAI` with `from groq import AsyncGroq`
  - `AsyncOpenAI(api_key=settings.openai_api_key)` → `AsyncGroq(api_key=settings.groq_api_key)`
  - `model or settings.openai_model` → `model or settings.groq_model`
  - Both `chat()` and `chat_with_history()` use `settings.openai_model` — update both
- [ ] Edit `backend/services/document_service.py`:
  - Remove `from langchain_openai import OpenAIEmbeddings`
  - Add `from langchain_huggingface import HuggingFaceEmbeddings`
  - In `get_embeddings()`: return `HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")`
  - Remove `openai_api_key=settings.openai_api_key` kwarg (no longer needed)
- [ ] Edit `backend/requirements.txt`:
  - Remove: `openai>=1.35.7`, `langchain-openai>=0.1.14`
  - Add: `groq>=0.9.0`, `langchain-huggingface>=0.0.3`, `sentence-transformers>=2.7.0`
- [ ] Edit `backend/.env.example`:
  - `OPENAI_API_KEY=...` → `GROQ_API_KEY=gsk_...your-groq-key-here...`
  - `OPENAI_MODEL=gpt-4o-mini` → `GROQ_MODEL=llama-3.3-70b-versatile`
  - Remove `OPENAI_EMBEDDING_MODEL` line (no longer needed)

**Relevant Context:**
- `backend/services/llm_service.py` lines 4, 14, 27, 47 — the four OpenAI references
- `backend/services/document_service.py` lines 28, 41-48 — OpenAIEmbeddings usage
- `backend/config.py` lines 6-8 — three fields to rename/remove
- Groq free tier models: `llama-3.3-70b-versatile` (default — best quality),
  `llama-3.1-8b-instant` (fastest fallback), `mixtral-8x7b-32768` (long context)
- HuggingFace `all-MiniLM-L6-v2` is 22 MB download on first run, then cached

**Status:** [ ] pending

---

## Sub-Task 2 — Create `backend/Dockerfile`

**Intent:**
Render deploys via Docker. The Dockerfile ensures: correct Python version, numpy pinned
before faiss-cpu, sentence-transformers downloaded at build time (not cold-start),
and the app listens on Render's injected `$PORT`.

**Expected Outcomes:**
- `backend/Dockerfile` builds without errors
- `sentence-transformers` model is downloaded during `docker build` (warm cache) not
  at first request (cold start)
- Container starts with `uvicorn main:app --host 0.0.0.0 --port $PORT --workers 1`
- `--workers 1` is in the CMD so FAISS in-memory dict is never split across processes

**Todo List:**
- [ ] Create `backend/Dockerfile` with:
  - Base: `python:3.11-slim`
  - `WORKDIR /app`
  - `COPY requirements.txt .`
  - Install numpy first: `RUN pip install --no-cache-dir "numpy<2.0.0"`
  - Install rest: `RUN pip install --no-cache-dir -r requirements.txt`
  - Pre-download HuggingFace model at build time:
    `RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"`
  - `COPY . .`
  - `ENV PORT=8000`
  - `CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT} --workers 1"]`

**Relevant Context:**
- `backend/main.py` — entry point is `main:app`; lifespan creates dirs on startup
- `backend/requirements.txt` — now uses `groq` + `sentence-transformers` instead of `openai`
- Render injects `PORT` env var automatically at runtime; `${PORT:-8000}` fallback for local

**Status:** [ ] pending

---

## Sub-Task 3 — Create `render.yaml` (repo root)

**Intent:**
`render.yaml` is Render's Blueprint file. Committing it means the user can deploy via
"New → Blueprint" and Render reads the config automatically — no manual form filling.
It defines the web service, the persistent disk, and all required env vars.

**Expected Outcomes:**
- `render.yaml` at project root (Render reads from root of the connected repo)
- Service uses Docker build with context `./backend`
- Persistent disk mounted at `/data` (1 GB) — `CHROMA_PERSIST_DIR` and `UPLOAD_DIR`
  point to `/data/...` so data survives redeploys
- All env var keys declared; secrets marked `sync: false` so user fills them in dashboard

**Todo List:**
- [ ] Create `render.yaml` at repo root:
  - `services:` block with `type: web`, `name: studdy-buddy-api`
  - `env: docker`, `dockerfilePath: ./backend/Dockerfile`, `dockerContext: ./backend`
  - `plan: free`
  - `disk:` block: `name: studdy-data`, `mountPath: /data`, `sizeGB: 1`
  - `envVars:` listing:
    - `GROQ_API_KEY` — `sync: false` (user fills in dashboard)
    - `GROQ_MODEL` — value `llama-3.3-70b-versatile`
    - `CORS_ORIGINS` — placeholder `https://your-app.vercel.app` (user updates after Vercel deploy)
    - `CHROMA_PERSIST_DIR` — value `/data/chroma_db`
    - `UPLOAD_DIR` — value `/data/uploads`
    - `FAISS_INDEX_DIR` — value `/data/faiss_indexes`
    - `MAX_FILE_SIZE_MB` — value `20`
    - `CHUNK_SIZE` — value `800`
    - `CHUNK_OVERLAP` — value `100`

**Relevant Context:**
- `backend/config.py` — all these vars map directly to `Settings` fields
- `backend/services/document_service.py` — ChromaDB writes to `settings.chroma_persist_dir`
- Render free tier: 512 MB RAM, shared CPU, 750 hrs/month, sleeps after 15 min idle

**Status:** [ ] pending

---

## Sub-Task 4 — Create `frontend/vercel.json`

**Intent:**
The project is a monorepo with `frontend/` as the Next.js app root. Without `vercel.json`
Vercel may try to build from the repo root and fail because there is no `package.json`
there. This file tells Vercel the correct root and framework.

**Expected Outcomes:**
- `frontend/vercel.json` exists
- When the user imports the repo on Vercel and sets Root Directory to `frontend/`,
  the build succeeds with `next build`
- The `NEXT_PUBLIC_API_URL` env var guard in `next.config.ts` does NOT throw during
  local dev (only on Vercel where `VERCEL=1` is set)

**Todo List:**
- [ ] Create `frontend/vercel.json`:
  ```json
  { "framework": "nextjs" }
  ```
  (Minimal — Vercel auto-detects everything else for Next.js 14)
- [ ] Update `frontend/next.config.ts`: add build-time guard that throws a clear error
  if `VERCEL` env var is set but `NEXT_PUBLIC_API_URL` is not:
  ```ts
  if (process.env.VERCEL && !process.env.NEXT_PUBLIC_API_URL) {
    throw new Error(
      "Set NEXT_PUBLIC_API_URL to your Render backend URL in Vercel environment variables"
    );
  }
  ```

**Relevant Context:**
- `frontend/next.config.ts` — currently only contains the `/api/py/*` rewrite
- `frontend/src/lib/api.ts` line 3 — falls back to `localhost:8000` if env var missing

**Status:** [ ] pending

---

## Sub-Task 5 — Add single-worker warning to `document_service.py`

**Intent:**
The FAISS in-memory dict will silently lose data if the backend ever runs with
`--workers > 1`. The `render.yaml` already enforces `--workers 1` in the start command,
but a code-level comment prevents future maintainers from accidentally changing it.

**Expected Outcomes:**
- A clearly visible comment above `_faiss_registry` warns about the single-worker
  constraint
- No functional code changes

**Todo List:**
- [ ] Add comment above `_faiss_registry` in `document_service.py`:
  `# ⚠️  IN-MEMORY ONLY — requires --workers 1 (see render.yaml / Dockerfile CMD)`

**Relevant Context:**
- `backend/services/document_service.py` line 53

**Status:** [ ] pending

---

## Sub-Task 6 — Write `DEPLOY.md`

**Intent:**
A single copy-pasteable file the user (and hackathon judges) can follow from zero to
live URL. Covers: GitHub setup from scratch, Render deploy via Blueprint, Vercel deploy,
env var checklist, and smoke test steps.

**Expected Outcomes:**
- `DEPLOY.md` at project root
- Section 0: Prerequisites checklist
- Section 1: Push to GitHub (git init → github.com → push)
- Section 2: Deploy backend on Render (Blueprint using render.yaml)
  - Which env vars to fill in the dashboard
  - How to get the service URL
  - Verify with `GET /health`
- Section 3: Deploy frontend on Vercel
  - Import repo, set Root Directory = `frontend/`
  - Set `NEXT_PUBLIC_API_URL`
  - Redeploy
- Section 4: Update CORS on Render (set `CORS_ORIGINS` to Vercel URL)
- Section 5: Smoke test checklist
- Section 6: Troubleshooting (cold starts, CORS, FAISS reset, model names)

**Relevant Context:**
- `render.yaml` (sub-task 3) — drives the Render Blueprint instructions
- `frontend/vercel.json` (sub-task 4) — drives the Vercel import instructions
- Groq free tier API key: https://console.groq.com

**Status:** [ ] pending

---

## Final Architecture After All Sub-Tasks

```
GitHub repo (monorepo)
├── .gitignore
├── render.yaml          ← Render Blueprint
├── DEPLOY.md            ← Step-by-step guide
├── backend/
│   ├── Dockerfile       ← python:3.11-slim, pre-downloads HF model
│   ├── config.py        ← groq_api_key, groq_model
│   ├── services/
│   │   ├── llm_service.py        ← groq.AsyncGroq
│   │   └── document_service.py  ← HuggingFaceEmbeddings
│   └── requirements.txt ← groq + sentence-transformers
└── frontend/
    ├── vercel.json      ← framework: nextjs
    └── next.config.ts  ← build guard

          Vercel (free)
   https://studdy-buddy.vercel.app
          │ NEXT_PUBLIC_API_URL
          ▼
       Render (free, Docker)
   https://studdy-buddy-api.onrender.com
   --workers 1
          ├── /data/chroma_db   (Render Disk 1 GB)
          ├── /data/uploads
          └── Groq API  +  HuggingFace local embeddings
```

---

## Groq Model Reference

| Model | Speed | Quality | Context | Best for |
|---|---|---|---|---|
| `llama-3.3-70b-versatile` ✅ **default** | Medium | Excellent | 128k | Best quality — quiz, explain, planner, RAG |
| `llama-3.1-8b-instant` | ⚡ Fastest | Good | 128k | Fallback if rate-limited |
| `mixtral-8x7b-32768` | Medium | Very good | 32k | Long document Q&A |

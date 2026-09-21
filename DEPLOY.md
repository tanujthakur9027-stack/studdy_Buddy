# StudyBuddy AI — Deployment Guide

## Overview

StudyBuddy AI runs as two processes:
| Component | Technology | Port |
|---|---|---|
| **Streamlit frontend** | Streamlit ≥ 1.40 | `8501` (Streamlit Cloud managed) |
| **FastAPI backend** | Uvicorn subprocess | `127.0.0.1:8000` (local only) |

The Streamlit app launches the FastAPI backend as a **subprocess** on startup using `@st.cache_resource` — this ensures only **one** uvicorn process is created per worker, not per browser tab.

---

## Streamlit Cloud (Recommended)

### 1. Fork / clone the repo

```bash
git clone https://github.com/your-org/studybuddy.git
```

### 2. Create a Streamlit Cloud app

- Go to [share.streamlit.io](https://share.streamlit.io) and click **New app**.
- Set **Main file path**: `streamlit_app/app.py`
- Set **Python version**: 3.11+

### 3. Set secrets

In the app dashboard → **Settings → Secrets**, paste (and fill in):

```toml
GROQ_API_KEY      = "gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxx"
SECRET_KEY        = "generate-with-openssl-rand-hex-32"
COOKIE_SECRET     = "another-random-32-char-string"
ADMIN_SEED_EMAIL  = "admin@yourdomain.com"
ADMIN_SEED_PASSWORD = "StrongPass123!"
```

Optionally:
```toml
OPENAI_API_KEY = "sk-..."
SMTP_HOST      = "smtp.gmail.com"
SMTP_USER      = "you@gmail.com"
SMTP_PASS      = "app-password"
```

### 4. Deploy

Click **Deploy**. The first cold start takes ~60–90 seconds (backend subprocess boot + model download).

### ⚠️ Ephemeral disk

Streamlit Cloud's filesystem is **reset on every redeploy**. SQLite data and uploaded files will be lost.

**For persistent storage:**
- Provision a **PostgreSQL** database (Supabase, Railway, Neon, etc.)
- Use an **S3-compatible object store** for file uploads (Cloudflare R2, AWS S3, etc.)
- Set `DATABASE_URL=postgresql+asyncpg://...` in secrets

---

## Local Development

### Prerequisites

- Python 3.11+
- `tesseract-ocr` (for image OCR): `apt install tesseract-ocr` / `brew install tesseract`
- Node.js 18+ (only for the optional Next.js frontend)

### Backend only

```bash
cd backend
cp .env.example .env      # fill in GROQ_API_KEY + SECRET_KEY
pip install -r requirements.txt
python seed_admin.py
uvicorn main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### Streamlit app (launches backend automatically)

```bash
cd streamlit_app
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # fill in values
pip install -r requirements.txt
streamlit run app.py
```

### Next.js frontend (optional)

```bash
cd frontend
npm install
cp .env.local.example .env.local   # set NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `GROQ_API_KEY` | **yes** | — | Groq LLM API key |
| `SECRET_KEY` | **yes** | — | JWT signing key (must be set; app refuses to start if empty) |
| `COOKIE_SECRET` | yes (Streamlit) | fallback | Encrypts the browser auth cookie |
| `AUTH_REQUIRED` | no | `true` | Set `false` to allow unauthenticated AI calls (legacy Next.js mode) |
| `DATABASE_URL` | no | SQLite | Async SQLAlchemy DSN |
| `UPLOAD_DIR` | no | `./data/uploads` | File upload directory |
| `CHROMA_PERSIST_DIR` | no | `./data/chroma_db` | ChromaDB persistence |
| `FAISS_INDEX_DIR` | no | `./data/faiss_indexes` | FAISS index persistence |
| `OPENAI_API_KEY` | no | — | OpenAI key (if preferred over Groq) |
| `ADMIN_SEED_EMAIL` | no | `admin@studybuddy.com` | Default admin email |
| `ADMIN_SEED_PASSWORD` | no | `Admin@StudyBuddy2024` | Default admin password (**change in prod!**) |
| `SMTP_HOST` | no | — | SMTP server for email notifications |

---

## Production Checklist

- [ ] `SECRET_KEY` is a random 32-byte hex string (`openssl rand -hex 32`)
- [ ] `COOKIE_SECRET` is a different random string
- [ ] `ADMIN_SEED_PASSWORD` is changed to a strong password
- [ ] `AUTH_REQUIRED=true` (default)
- [ ] `CORS_ORIGINS` lists only your actual frontend origin(s)
- [ ] Database is PostgreSQL (not SQLite)
- [ ] Uploads are stored on persistent external storage
- [ ] HTTPS is enforced on the frontend domain

---

## Architecture

```
Browser
  │
  └─► Streamlit (port 8501)
        │  @st.cache_resource
        └─► FastAPI / Uvicorn (127.0.0.1:8000)
                │
                ├─ SQLAlchemy (SQLite / Postgres)
                ├─ FAISS (in-process vector index)
                ├─ ChromaDB (persisted vector store)
                ├─ fastembed BAAI/bge-small-en-v1.5 (ONNX — no GPU needed)
                └─ Groq / OpenAI LLM API
```

---

## Running Tests

```bash
pip install pytest pytest-asyncio httpx
cd backend
pytest ../tests/test_backend.py -v
```

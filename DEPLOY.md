# StudyBuddy AI — Deployment Guide

## Architecture

```
Browser
  │
  └─► Streamlit Cloud (port 8501)
        │  @st.cache_resource — runs ONCE per worker
        └─► FastAPI / Uvicorn subprocess (127.0.0.1:8000)
                │
                ├─ SQLAlchemy (SQLite — ephemeral / PostgreSQL — persistent)
                ├─ FAISS (in-process vector index)
                ├─ ChromaDB (persisted vector store)
                ├─ fastembed BAAI/bge-small-en-v1.5 (ONNX, no GPU)
                └─ Groq / Gemini LLM API
```

Streamlit spawns the FastAPI backend as a subprocess on first load.
`@st.cache_resource` ensures only **one** uvicorn process is created per worker.

---

## Streamlit Cloud Deployment (All-in-One)

### Step 1 — Push to GitHub

```bash
git add .
git commit -m "deploy: streamlit cloud"
git push origin main
```

### Step 2 — Create App on Streamlit Cloud

1. Go to **[share.streamlit.io](https://share.streamlit.io)** and sign in with GitHub.
2. Click **"New app"**.
3. Fill in:

   | Field | Value |
   |---|---|
   | Repository | `your-github-username/Studdy_Buddy` |
   | Branch | `main` |
   | **Main file path** | `streamlit_app/app.py` |
   | Python version | `3.11` |

4. Click **"Advanced settings"** → confirm Python is `3.11`.

### Step 3 — Set Secrets

In the app dashboard → **Settings → Secrets**, paste and fill in:

```toml
# REQUIRED
GROQ_API_KEY = "gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxx"
SECRET_KEY   = "paste-output-of: python -c \"import secrets; print(secrets.token_hex(32))\""

# Admin account (created automatically on first boot)
ADMIN_SEED_EMAIL    = "admin@studybuddy.com"
ADMIN_SEED_PASSWORD = "ChangeThisStrongPassword123!"

# Optional — Gemini fallback LLM
GEMINI_API_KEY = ""

# Optional — Email notifications
SMTP_HOST = ""
SMTP_PORT = "587"
SMTP_USER = ""
SMTP_PASS = ""

# Set to your actual Streamlit Cloud URL after deploying
APP_BASE_URL = "https://your-app-name.streamlit.app"
```

> **Generate SECRET_KEY** (run once locally):
> ```powershell
> python -c "import secrets; print(secrets.token_hex(32))"
> ```

### Step 4 — Deploy

Click **"Deploy"**.

**First cold start takes 60–90 seconds** — the app shows a loading spinner while:
1. Streamlit installs all packages from `streamlit_app/requirements.txt`
2. Streamlit installs system packages from `streamlit_app/packages.txt`
3. uvicorn subprocess starts
4. fastembed downloads the ONNX embedding model (~24 MB, cached after first boot)
5. The admin account is seeded
6. `/health` responds `200 OK` → app shows Login page

Subsequent loads take ~5–10 seconds.

### Step 5 — Log In

Use the admin credentials you set in Step 3:
- **Email**: `admin@studybuddy.com`
- **Password**: your `ADMIN_SEED_PASSWORD`

---

## Troubleshooting

### ❌ "Backend failed to start after 2 minutes"

The app shows the last 40 lines of the backend log automatically.
Common causes:

| Symptom | Fix |
|---|---|
| `SECRET_KEY is not set` | Add `SECRET_KEY` to Streamlit Secrets |
| `GROQ_API_KEY` empty | Add your Groq key to Secrets |
| Package install failure | Check the Streamlit Cloud build logs |
| `ModuleNotFoundError` | A required package is missing from `requirements.txt` |

### ❌ App stuck on loading spinner forever

The `/health` poll timed out. Check:
1. Streamlit Cloud **Manage app → Logs** for errors
2. The backend log shown in the error expander

### ❌ Login fails with "Backend not reachable"

The backend subprocess crashed after starting. Check the backend log expander
shown on the error screen, or view **Manage app → Logs**.

---

## Ephemeral Disk Warning

Streamlit Cloud has **no persistent disk**. On every redeploy:

| Data | Status |
|---|---|
| SQLite database (`studybuddy.db`) | ⚠️ **Reset** — all users/data lost |
| Uploaded files (`uploads/`) | ⚠️ **Reset** |
| ChromaDB / FAISS indexes | ⚠️ **Reset** — must re-upload documents |

**For persistent storage** (production):
- **Database**: Provision PostgreSQL on [Supabase](https://supabase.com), [Neon](https://neon.tech), or [Railway](https://railway.app). Add `DATABASE_URL=postgresql+asyncpg://...` to Secrets.
- **File uploads**: Use an S3-compatible store (Cloudflare R2, AWS S3). *(requires code changes in `services/document_service.py`)*

---

## Local Development

### Backend only

```bash
cd backend
cp .env.example .env        # fill in GROQ_API_KEY + SECRET_KEY
pip install -r requirements.txt
python seed_admin.py
uvicorn main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### Full app (Streamlit launches backend automatically)

```bash
cd streamlit_app
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # fill in values
pip install -r requirements.txt
streamlit run app.py
```

Open: http://localhost:8501

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `GROQ_API_KEY` | **YES** | — | Groq LLM API key (free at console.groq.com) |
| `SECRET_KEY` | **YES** | — | JWT signing key — must be a random 32-byte hex string |
| `ADMIN_SEED_EMAIL` | no | `admin@studybuddy.com` | Admin account email |
| `ADMIN_SEED_PASSWORD` | no | `Admin@StudyBuddy2024` | Admin account password (**change in prod!**) |
| `GEMINI_API_KEY` | no | — | Google Gemini fallback LLM |
| `DATABASE_URL` | no | SQLite | Async SQLAlchemy DSN — use PostgreSQL for persistence |
| `UPLOAD_DIR` | no | `./uploads` | File upload directory |
| `CHROMA_PERSIST_DIR` | no | `./chroma_db` | ChromaDB persistence path |
| `FAISS_INDEX_DIR` | no | `./faiss_indexes` | FAISS index path |
| `SMTP_HOST` | no | — | SMTP server for email notifications |
| `APP_BASE_URL` | no | `https://studybuddy.streamlit.app` | Base URL used in email links |
| `SENTRY_DSN` | no | — | Sentry error tracking DSN |

---

## Production Checklist

- [ ] `SECRET_KEY` is a random 32-byte hex string (`python -c "import secrets; print(secrets.token_hex(32))"`)
- [ ] `ADMIN_SEED_PASSWORD` changed to a strong unique password
- [ ] `GROQ_API_KEY` is a real key (not the placeholder `gsk_xxx...`)
- [ ] `APP_BASE_URL` set to your actual Streamlit Cloud URL
- [ ] `DATABASE_URL` points to PostgreSQL (not SQLite) for data persistence
- [ ] SMTP credentials configured if email features are needed

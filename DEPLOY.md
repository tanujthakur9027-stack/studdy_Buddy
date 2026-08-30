# 🚀 StudyBuddy — Deployment Guide (Streamlit Cloud, self-contained)

The FastAPI backend runs **inside** the Streamlit Cloud worker as a subprocess.
**No Render. No CORS. No secrets except your Groq API key.**

```
Streamlit Cloud worker
├── streamlit run streamlit_app/app.py   ← your app
└── uvicorn main:app --port 8000         ← backend (auto-started)
    ├── ./data/studybuddy.db             (SQLite)
    ├── ./data/chroma_db/                (ChromaDB — FAISS rebuilt from here on restart)
    └── ./data/uploads/                  (raw files)
```

---

## ✅ Prerequisites

- **Groq API key** — free at [console.groq.com](https://console.groq.com) → API Keys
- **GitHub account** — [github.com](https://github.com)
- **Streamlit Cloud account** — free at [share.streamlit.io](https://share.streamlit.io) (sign up with GitHub)

---

## Step 1 — Push to GitHub

```bash
cd "C:\Users\Tanuj kumar singh\Desktop\Studdy_Buddy"
git add .
git commit -m "bundle FastAPI inside Streamlit"
git push
```

First push:
```bash
git init
git add .
git commit -m "initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/studdy-buddy.git
git push -u origin main
```

---

## Step 2 — Deploy on Streamlit Cloud

1. Go to **https://share.streamlit.io** → **New app**
2. Fill in:

   | Field | Value |
   |---|---|
   | Repository | `YOUR_USERNAME/studdy-buddy` |
   | Branch | `main` |
   | Main file path | `streamlit_app/app.py` |

3. Click **Advanced settings …**
4. In the **Secrets** box paste:

   ```toml
   GROQ_API_KEY = "gsk_...your-key-here..."
   ```

5. Click **Deploy!**

That's it. Build takes ~3–5 minutes (installs all packages + downloads embedding model).

---

## Step 3 — Verify

Open your Streamlit URL (e.g. `https://studdy-buddy-tanuj.streamlit.app`).

| What you see | Meaning |
|---|---|
| Spinner "Starting backend…" (up to 20 s) | Normal — uvicorn is warming up |
| 9 tabs appear | Backend is healthy |
| Sidebar → 🔌 Backend Status → **Check health** shows `✅ OK` | All systems go |

---

## Smoke Test

| Tab | Test |
|---|---|
| **Upload** | Upload a PDF ≤ 200 MB → "✅ filename — N chunks" |
| **ELI10** | Type "Newton's Laws" → explanation + analogy |
| **Ask AI** | Ask anything → answer with source citations |
| **Quiz** | Generate 5 questions → submit → grade |
| **Planner** | Set exam date → day-by-day schedule |
| **Feynman** | Type an explanation → score + gaps |
| **Flashcards** | Generate deck → flip cards |
| **Cheat Sheet** | Generate → download .md |
| **Progress** | Shows stats (empty on fresh deploy) |

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Spinner spins forever (> 90 s) | Check that `GROQ_API_KEY` is set in Secrets. Reboot app via Streamlit Cloud dashboard → **Reboot** |
| "❌ Backend failed to start" | Go to Streamlit Cloud → your app → **Manage app** → **Logs** — look for import errors |
| Upload returns 413 | `MAX_FILE_SIZE_MB` is set to 200 in code — verify `streamlit_app/.streamlit/config.toml` has `maxUploadSize = 200` |
| Ask AI / Quiz returns "No context found" | Re-upload your document. FAISS is rebuilt from ChromaDB on startup, but ChromaDB resets on full redeploy |
| App reboots and loses documents | This is expected on full redeploy. Documents persist across page reruns/refreshes within the same deployment |

---

## Local Development

### Run everything locally

```bash
# Terminal 1 — backend
cd backend
python -m venv .venv
.venv\Scripts\activate      # Windows PowerShell
pip install -r requirements.txt
copy .env.example .env
# Edit backend\.env — set GROQ_API_KEY=gsk_...
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

```bash
# Terminal 2 — Streamlit (talks to local backend)
cd streamlit_app
pip install -r requirements.txt
# Set your key (PowerShell):
$env:GROQ_API_KEY = "gsk_..."
streamlit run app.py
```

OR just run Streamlit alone — it will auto-start the backend subprocess:

```bash
cd streamlit_app
pip install -r requirements.txt
$env:GROQ_API_KEY = "gsk_..."
streamlit run app.py
```

App: **http://localhost:8501** · Backend: **http://localhost:8000** · Docs: **http://localhost:8000/docs**

---

## Environment Variables Reference

### Streamlit Cloud Secrets (App Settings → Secrets)

```toml
# Required
GROQ_API_KEY = "gsk_..."

# Optional overrides
GROQ_MODEL    = "openai/gpt-oss-20b"
OPENAI_API_KEY = ""        # leave blank to use Groq
```

### All other settings are hard-coded for the bundled deployment:

| Setting | Value (auto) |
|---|---|
| `BACKEND_URL` | `http://localhost:8000` (loopback) |
| `DATABASE_URL` | `sqlite+aiosqlite:///./data/studybuddy.db` |
| `CHROMA_PERSIST_DIR` | `./data/chroma_db` |
| `UPLOAD_DIR` | `./data/uploads` |
| `MAX_FILE_SIZE_MB` | `200` |
| `CORS_ORIGINS` | `*` (all — loopback only, no browser boundary) |

---

*Need help? Open an issue on GitHub.*

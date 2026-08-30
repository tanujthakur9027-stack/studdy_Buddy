# 🚀 StudyBuddy — Deployment Guide

Deploy the full stack for free:  
**GitHub → Render (FastAPI backend) → Streamlit Cloud (frontend)**

> **Why Streamlit Cloud instead of Vercel/Render-frontend?**  
> Streamlit Cloud is purpose-built for Python apps, has no cold-start memory limits for file uploads, and natively supports the 200 MB upload size we need. Vercel limits request bodies to 4.5 MB and Render's free tier sleeps, causing upload timeouts.

---

## ✅ Prerequisites Checklist

Before starting, make sure you have:

- [ ] **Groq API key** — free at [console.groq.com](https://console.groq.com) (sign up → API Keys → Create)
- [ ] **GitHub account** — [github.com](https://github.com)
- [ ] **Render account** — free at [render.com](https://render.com) (sign up with GitHub)
- [ ] **Streamlit Cloud account** — free at [share.streamlit.io](https://share.streamlit.io) (sign up with GitHub)
- [ ] **Git installed** — check with `git --version` in your terminal

---

## Step 1 — Push Code to GitHub

Open a terminal, navigate to your project folder, and run:

```bash
cd "C:\Users\Tanuj kumar singh\Desktop\Studdy_Buddy"
git add .
git commit -m "add streamlit frontend + 200 MB upload limit"
git push
```

If this is your first push:

```bash
git init
git add .
git commit -m "initial commit: StudyBuddy full stack"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/studdy-buddy.git
git push -u origin main
```

✅ Your code is now on GitHub.

---

## Step 2 — Deploy Backend on Render

### 2a — Create a new Blueprint

1. Go to **https://dashboard.render.com**
2. Click **New** → **Blueprint**
3. Connect your GitHub account if prompted
4. Select the `studdy-buddy` repository
5. Render detects `render.yaml` automatically → click **Apply**

### 2b — Set your API keys

After the blueprint is created, Render shows environment variables.  
Set the following in **Environment** tab:

| Variable | Value |
|---|---|
| `GROQ_API_KEY` | `gsk_...` (from console.groq.com) |
| `MAX_FILE_SIZE_MB` | `200` |
| `CORS_ORIGINS` | `https://your-streamlit-app.streamlit.app` *(fill in after Step 3)* |

### 2c — Wait for the deploy

First build takes **5–10 minutes**. When the status dot turns green, the backend is live.

### 2d — Copy your backend URL

At the top of the service page you'll see a URL like:
```
https://studdy-buddy-api.onrender.com
```
**Copy this URL** — you need it in Step 3.

### 2e — Verify the backend

Open in your browser:
```
https://studdy-buddy-api.onrender.com/health
```
Expected:
```json
{ "status": "ok", "provider": "groq", "indexed_documents": 0, "faiss_vectors": 0 }
```

---

## Step 3 — Deploy Frontend on Streamlit Cloud

### 3a — Import your GitHub repo

1. Go to **https://share.streamlit.io**
2. Click **New app**
3. Select your `studdy-buddy` repository
4. **Branch:** `main`
5. **Main file path:** `streamlit_app/app.py`
6. Click **Advanced settings …**

### 3b — Add your secret

In the **Secrets** box, paste:

```toml
BACKEND_URL = "https://studdy-buddy-api.onrender.com"
```

*(Replace with your exact Render URL from Step 2d)*

### 3c — Deploy

Click **Deploy!** — the build takes ~2 minutes.

When done, Streamlit gives you a URL like:
```
https://studdy-buddy-tanuj.streamlit.app
```

**Copy this URL** — you need it for Step 4.

---

## Step 4 — Update CORS on Render

The backend must allow requests from your Streamlit URL.

1. Go to your Render service → **Environment** tab
2. Set `CORS_ORIGINS` to your Streamlit URL (no trailing slash):
   ```
   https://studdy-buddy-tanuj.streamlit.app
   ```
3. Click **Save Changes** → Render redeploys in ~2 minutes.

---

## Step 5 — Smoke Test ✅

Open your Streamlit URL and test each tab:

| Test | Expected result |
|---|---|
| Page loads | Dark sidebar + 9 tabs visible |
| **Upload** — drag a PDF ≤ 200 MB | "✅ filename indexed — N chunks" |
| **ELI10** — type "Newton's Laws" | Explanation + analogy + key points |
| **Quiz** — Generate 5 questions | Radio buttons, submit, grade shown |
| **Planner** — set exam date | Day-by-day schedule with session types |
| **Ask AI** — "What is this about?" | Answer with source citations |
| **Feynman** — explain any concept | Score 0–100 with gaps & strengths |
| **Flashcards** — generate deck | Flip cards with front/back |
| **Cheat Sheet** — generate | Markdown summary with download button |

---

## Step 6 — Troubleshooting

### "Cannot reach backend" error in Streamlit
- Check the `BACKEND_URL` secret in Streamlit Cloud App Settings → Secrets
- Make sure it has **no trailing slash** and starts with `https://`
- Use the **🔌 Backend Status** expander in the sidebar → **Check health** button

### "CORS error" / 403 on API calls
- `CORS_ORIGINS` on Render must **exactly match** your Streamlit URL (no trailing slash)
- After updating env vars, wait for Render to finish redeploying (~2 min)

### Upload returns 413 (File Too Large)
- Set `MAX_FILE_SIZE_MB=200` in Render environment variables
- `streamlit_app/.streamlit/config.toml` already sets `maxUploadSize = 200`
- Both limits must be in sync

### "First request is slow" (30–60 seconds)
- Render free tier **sleeps** after 15 minutes of inactivity
- Use the **Check health** button to wake it up before uploading
- Upgrade to Render Starter ($7/mo) to prevent sleeping

### Quiz / Ask returns "No context found"
- FAISS is in-memory — re-upload your document after each Render redeploy
- ChromaDB is persistent on the Render disk

---

## Environment Variables Reference

### Backend (set in Render dashboard → Environment tab)

| Variable | Description | Example |
|---|---|---|
| `GROQ_API_KEY` | Your Groq secret key (**required**) | `gsk_abc123...` |
| `GROQ_MODEL` | Groq model to use | `openai/gpt-oss-20b` |
| `CORS_ORIGINS` | Your Streamlit frontend URL | `https://your-app.streamlit.app` |
| `CHROMA_PERSIST_DIR` | ChromaDB storage path | `/data/chroma_db` |
| `UPLOAD_DIR` | Uploaded files path | `/data/uploads` |
| `MAX_FILE_SIZE_MB` | Max upload size in MB | `200` |

### Frontend (set in Streamlit Cloud → App Settings → Secrets)

```toml
BACKEND_URL = "https://your-render-backend.onrender.com"
```

---

## Local Development

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows PowerShell

pip install -r requirements.txt

# Copy env and add your key
copy .env.example .env
# Edit backend\.env — set GROQ_API_KEY=gsk_...

uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API: **http://localhost:8000**  
Swagger UI: **http://localhost:8000/docs**

### Streamlit Frontend

```bash
cd streamlit_app
pip install -r requirements.txt

# Create secrets file
copy .streamlit\secrets.toml.example .streamlit\secrets.toml
# Edit secrets.toml — set BACKEND_URL=http://localhost:8000

streamlit run app.py
```

App: **http://localhost:8501**

---

## Architecture

```
Your Browser
     │
     ▼
Streamlit Cloud (free)               ← https://your-app.streamlit.app
streamlit_app/app.py  (pure Python)
     │
     │  BACKEND_URL (requests)
     ▼
Render (free, Docker)                ← https://studdy-buddy-api.onrender.com
FastAPI — uvicorn
     │
     ├── /data/chroma_db  ─────────── Render Disk (1 GB, persistent)
     ├── /data/uploads    ─────────── Render Disk  (200 MB file limit)
     │
     ├── fastembed BAAI/bge-small-en-v1.5  (local embeddings)
     └── Groq API  ────────────────── openai/gpt-oss-20b (free)
```

---

*Need help? Open an issue on GitHub or check the [Render](https://status.render.com) and [Streamlit](https://www.streamlitstatus.com) status pages.*

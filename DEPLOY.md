# 🚀 StudyBuddy — Deployment Guide

Deploy the full stack for free in ~15 minutes:  
**GitHub → Render (backend) → Vercel (frontend)**

---

## ✅ Prerequisites Checklist

Before starting, make sure you have:

- [ ] **Groq API key** — free at [console.groq.com](https://console.groq.com) (sign up → API Keys → Create)
- [ ] **GitHub account** — [github.com](https://github.com)
- [ ] **Render account** — free at [render.com](https://render.com) (sign up with GitHub)
- [ ] **Vercel account** — free at [vercel.com](https://vercel.com) (sign up with GitHub)
- [ ] **Git installed** — check with `git --version` in your terminal

---

## Step 1 — Push Code to GitHub

Open a terminal, navigate to your project folder, and run these commands one by one:

```bash
# 1. Go to the project root
cd "C:\Users\Tanuj kumar singh\Desktop\Studdy_Buddy"

# 2. Initialise a git repository
git init

# 3. Stage all files
git add .

# 4. Create the first commit
git commit -m "initial commit: AI Study Buddy full stack"

# 5. Set the default branch name to main
git branch -M main
```

Now create the GitHub repo:

1. Go to **https://github.com/new**
2. Repository name: `studdy-buddy` (or any name you like)
3. Set it to **Public** (required for free Render + Vercel)
4. **Do NOT** tick "Add README" or "Add .gitignore" — the repo must be empty
5. Click **Create repository**
6. Copy the two lines GitHub shows under *"…or push an existing repository"*:

```bash
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
5. Render will detect `render.yaml` automatically → click **Apply**

### 2b — Set your Groq API key

After the blueprint is created, Render will show a list of environment variables.  
Find `GROQ_API_KEY` — it will say *"value required"*:

1. Click the pencil icon next to `GROQ_API_KEY`
2. Paste your Groq key (starts with `gsk_...`)
3. Click **Save**

> **Where to find your Groq key:**  
> Go to [console.groq.com](https://console.groq.com) → API Keys → click your key to copy it.

### 2c — Wait for the deploy

The first build takes **5–10 minutes** (it installs Python deps and downloads the HuggingFace model).  
You'll see a log stream. When it says **"Live"** with a green dot, the backend is running.

### 2d — Copy your backend URL

At the top of the service page you'll see a URL like:
```
https://studdy-buddy-api.onrender.com
```
**Copy this URL** — you'll need it in Step 3.

### 2e — Verify the backend is working

Open this URL in your browser:
```
https://studdy-buddy-api.onrender.com/health
```

You should see:
```json
{ "status": "ok", "model": "llama-3.3-70b-versatile", "indexed_documents": 0, "faiss_vectors": 0 }
```

Also check the Swagger docs at:
```
https://studdy-buddy-api.onrender.com/docs
```

---

## Step 3 — Deploy Frontend on Vercel

### 3a — Import the project

1. Go to **https://vercel.com/new**
2. Click **Import Git Repository**
3. Select your `studdy-buddy` repository
4. Under **Root Directory** → click **Edit** → type `frontend` → click **Continue**

### 3b — Set the environment variable

Before clicking Deploy, scroll down to **Environment Variables** and add:

| Name | Value |
|---|---|
| `NEXT_PUBLIC_API_URL` | `https://studdy-buddy-api.onrender.com` |

*(Paste your exact Render URL from Step 2d)*

### 3c — Deploy

Click **Deploy**. The build takes ~2 minutes.

When done, Vercel gives you a URL like:
```
https://studdy-buddy-tanuj.vercel.app
```

**Copy this URL** — you need it for Step 4.

---

## Step 4 — Update CORS on Render

The backend needs to allow requests from your Vercel frontend URL.

1. Go to your Render service dashboard → **Environment** tab
2. Find `CORS_ORIGINS`
3. Change the value to your **exact Vercel URL** (no trailing slash):
   ```
   https://studdy-buddy-tanuj.vercel.app
   ```
4. Click **Save Changes** → Render automatically redeploys (takes ~2 min)

---

## Step 5 — Smoke Test ✅

Open your Vercel URL and test each feature:

| Test | Expected result |
|---|---|
| Page loads | Dark UI with sidebar — Upload, Explain, Quiz, Planner, Doubt tabs visible |
| **Upload** — drag a PDF | Progress bar appears → "Ingested X chunks" success message |
| **Explain** — type "Newton's Laws" → ELI5 | Explanation + analogy + key points returned in <10s |
| **Quiz** — Generate Quiz (5 questions) | Countdown ring appears, 4 colour-coded options shown |
| **Planner** — set exam date 2 weeks away | Day-by-day calendar generated with session types |
| **Doubt** — ask "What is this document about?" | Answer with source citation returned |

---

## Step 6 — Troubleshooting

### "First request is slow" (30–60 seconds)
This is normal. The Render **free tier sleeps** after 15 minutes of inactivity.  
The first request wakes it up. Subsequent requests are fast.  
To prevent this for demos: upgrade to Render's **Starter plan ($7/mo)**.

### "CORS error" in browser console
- Make sure `CORS_ORIGINS` on Render **exactly matches** your Vercel URL (no trailing slash)
- After updating env vars, wait for Render to finish redeploying

### "NEXT_PUBLIC_API_URL is not set" build error on Vercel
- Go to Vercel → Project Settings → Environment Variables
- Add `NEXT_PUBLIC_API_URL` = your Render URL
- Go to Deployments → click the latest → **Redeploy**

### "groq.AuthenticationError" in Render logs
- Your `GROQ_API_KEY` is wrong or empty
- Go to Render → Environment → check the key starts with `gsk_`
- If the key has spaces or quotes, remove them

### Quiz / Ask returns "No context found"
- FAISS is in-memory. If Render redeployed (e.g. after an env var change), all FAISS
  indexes are reset. Simply **re-upload your document** — ChromaDB is persistent.

### "Module not found: sentence_transformers" in Render build log
- The Docker build should have pre-installed it. Check Render logs for pip errors.
- If it fails, try redeploying from the Render dashboard.

---

## Environment Variables Reference

### Backend (set in Render dashboard)

| Variable | Description | Example |
|---|---|---|
| `GROQ_API_KEY` | Your Groq secret key (**required**) | `gsk_abc123...` |
| `GROQ_MODEL` | Groq model to use | `llama-3.3-70b-versatile` |
| `CORS_ORIGINS` | Your Vercel frontend URL | `https://your-app.vercel.app` |
| `CHROMA_PERSIST_DIR` | ChromaDB storage path | `/data/chroma_db` |
| `UPLOAD_DIR` | Uploaded files path | `/data/uploads` |
| `MAX_FILE_SIZE_MB` | Max upload size | `20` |

### Frontend (set in Vercel dashboard)

| Variable | Description | Example |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | Your Render backend URL (**required**) | `https://studdy-buddy-api.onrender.com` |

---

## Local Development (run without deploying)

### Backend

```bash
cd backend

# Create virtual environment (first time only)
python -m venv .venv
.venv\Scripts\activate        # Windows PowerShell

# Install dependencies (first time only)
pip install -r requirements.txt

# Copy env file and add your Groq key
copy .env.example .env
# Open backend\.env in any editor and set:
#   GROQ_API_KEY=gsk_...your-key...

# Start the API
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API runs at **http://localhost:8000**  
Swagger UI at **http://localhost:8000/docs**

### Frontend

```bash
cd frontend

# Install dependencies (first time only)
npm install

# Copy env file (default value is correct for local dev)
copy .env.example .env.local

# Start dev server
npm run dev
```

App runs at **http://localhost:3000**

---

## Architecture

```
Your Browser
     │
     ▼
 Vercel (free)                       ← https://your-app.vercel.app
 Next.js 14 — App Router
 Tailwind + Framer Motion + Lucide
     │
     │  NEXT_PUBLIC_API_URL (axios)
     ▼
 Render (free, Docker)               ← https://studdy-buddy-api.onrender.com
 FastAPI — uvicorn --workers 1
     │
     ├── /data/chroma_db  ──────────── Render Disk (1 GB, persistent)
     ├── /data/uploads    ──────────── Render Disk
     │
     ├── HuggingFace all-MiniLM-L6-v2  (local embeddings, no API key)
     └── Groq API  ─────────────────── llama-3.3-70b-versatile
```

---

*Need help? Open an issue on GitHub or check the Render and Vercel status pages.*

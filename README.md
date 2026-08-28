# StudyBuddy AI 🎓

> **AI-powered personal study assistant** — upload your notes or syllabus and instantly get
> simplified explanations, Kahoot-style timed quizzes, smart day-by-day revision plans,
> and a RAG-powered doubt solver. All in one place, completely free to deploy.

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Vercel-black?style=flat-square&logo=vercel)](https://studdy-buddy-gray.vercel.app)
[![Backend](https://img.shields.io/badge/API-Render-46E3B7?style=flat-square&logo=render)](https://studdy-buddy-api.onrender.com/docs)
[![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)](LICENSE)

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 📄 **Document Upload** | PDF, TXT, MD, DOC, DOCX — parsed, chunked, and indexed into FAISS + ChromaDB |
| 🧒 **ELI10 Explain** | Three explanation levels (ELI5, Beginner, Intermediate) with analogies and key points |
| ⚡ **Kahoot-Style Quiz** | Timed MCQs with live scoring, streaks, difficulty levels, and instant answer review |
| 📅 **Smart Revision Planner** | Day-by-day schedule with concept, quiz, buffer, and rest sessions using spaced repetition |
| 🤖 **RAG Doubt Solver** | Conversational Q&A grounded in your uploaded documents with source citations |

---

## 🏗️ Architecture

```
Browser
  │
  ▼
Vercel (Next.js 14 · TypeScript · Tailwind CSS · Framer Motion)
  │  NEXT_PUBLIC_API_URL
  ▼
Render Free Tier (FastAPI · Python 3.11 · Docker ~200 MB)
  │
  ├── fastembed  BAAI/bge-small-en-v1.5   local ONNX embeddings (no API key)
  ├── FAISS      in-process vector index   ultra-fast per-session retrieval
  ├── ChromaDB   disk-persisted store      survives container restarts
  └── Groq API   openai/gpt-oss-20b        free LLM (0.5 s response time)
```

### Backend components

| Layer | Technology | Purpose |
|-------|-----------|---------|
| API | FastAPI 0.111 | REST endpoints + Swagger UI |
| LLM | OpenAI (primary) · Groq `openai/gpt-oss-20b` (free fallback) | Answer generation |
| Embeddings | fastembed `BAAI/bge-small-en-v1.5` (local ONNX) | Vector embeddings — no API key |
| Vector DB | FAISS (in-memory) + ChromaDB (persistent) | Semantic search & RAG retrieval |
| Document parsing | pdfplumber → PyPDF2 fallback · docx2txt | PDF / DOCX / TXT / MD |

### API endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/upload` | Upload & index a document |
| POST | `/api/ask` | RAG Q&A (Standard / ELI5 mode) |
| POST | `/api/generate-quiz` | Generate timed MCQ quiz |
| POST | `/api/generate-plan` | Generate day-by-day revision plan |
| POST | `/api/explain` | Simplified topic explanation |
| POST | `/api/doubt/solve` | Conversational RAG doubt solver |
| GET  | `/health` | Server health + indexed doc count |
| GET  | `/docs` | Swagger UI |

Legacy paths (`/quiz/generate`, `/revision/plan`, `/explain`, `/doubt/solve`) are kept for backwards compatibility.

---

## 🚀 Quick Start — Local Development

### Prerequisites

- Python 3.11+
- Node.js 18+
- A free Groq API key → [console.groq.com](https://console.groq.com) *(or an OpenAI key)*

### 1. Clone the repo

```bash
git clone https://github.com/tanujthakur9027-stack/studdy_Buddy.git
cd studdy_Buddy
```

### 2. Backend

```bash
cd backend

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate
# Activate (macOS / Linux)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Open .env and set GROQ_API_KEY=gsk_...your-key...
# GROQ_MODEL=openai/gpt-oss-20b

# Start the API server
uvicorn main:app --reload --port 8000
# → API running at http://localhost:8000
# → Swagger UI at http://localhost:8000/docs
```

### 3. Frontend

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# Start dev server
npm run dev
  App running at https://studdy-buddy-gray.vercel.app
```

---

## ⚙️ Environment Variables

### Backend (`backend/.env`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GROQ_API_KEY` | **yes** (free) | — | Groq API key — get free at [console.groq.com](https://console.groq.com) |
| `GROQ_MODEL` | no | `openai/gpt-oss-20b` | Groq model ID (tested & confirmed on this account) |
| `OPENAI_API_KEY` | optional | — | OpenAI key — takes priority over Groq when set |
| `OPENAI_MODEL` | no | `gpt-4o-mini` | OpenAI model name |
| `CORS_ORIGINS` | no | `http://localhost:3000` | Comma-separated allowed frontend origins |
| `UPLOAD_DIR` | no | `./uploads` | File upload directory |
| `CHROMA_PERSIST_DIR` | no | `./chroma_db` | ChromaDB storage directory |
| `FAISS_INDEX_DIR` | no | `./faiss_indexes` | FAISS index directory |
| `MAX_FILE_SIZE_MB` | no | `20` | Maximum upload file size |
| `CHUNK_SIZE` | no | `800` | Text chunk size (chars) |
| `CHUNK_OVERLAP` | no | `120` | Chunk overlap (chars) |

### Frontend (`frontend/.env.local`)

| Variable | Required | Description |
|----------|----------|-------------|
| `NEXT_PUBLIC_API_URL` | **yes** (prod) | Backend URL e.g. `https://studdy-buddy-api.onrender.com` |

---

## ☁️ Deployment

### Backend → Render (Free)

1. Push code to GitHub
2. Go to [dashboard.render.com](https://dashboard.render.com) → **New → Blueprint**
3. Connect your repo — Render auto-detects `render.yaml`
4. Add `GROQ_API_KEY` in Render → Environment → Save
5. Wait ~5 min for the Docker build to complete

### Frontend → Vercel (Free)

1. Go to [vercel.com/new](https://vercel.com/new) → Import repo
2. Set **Root Directory** → `frontend`
3. Add environment variable: `NEXT_PUBLIC_API_URL` = your Render URL
4. Deploy → copy your Vercel URL
5. Back in Render → update `CORS_ORIGINS` to your Vercel URL → Save

> Full step-by-step guide: [DEPLOY.md](DEPLOY.md)

---

## ⚠️ Known Limitations

- **Single worker required** — FAISS indexes are in-process (per-worker). The Dockerfile enforces `--workers 1`. FAISS is reset on restart; re-upload your documents. ChromaDB persists across restarts.
- **In-memory quiz store** — Quiz sessions are stored in a Python dict and lost on restart. Always generate a new quiz after a server restart.
- **Free tier cold start** — Render free tier sleeps after 15 min of inactivity. First request takes 30–60 s to wake up. Subsequent requests are fast.
- **File size limit** — 20 MB per upload (configurable via `MAX_FILE_SIZE_MB`).
- **Supported formats** — PDF, TXT, MD, DOC, DOCX.

---

## 👥 Team

| Name | Role |
|------|------|
| **Bhavna Agarwal** | Full-Stack Developer · AI/ML Integration · Project Lead |
| **Divya Goyal** | AI/ML Engineer |
| **Tanuj Kumar Singh** | Full-Stack Developer · AI/ML Integration |
> Built as a personal AI study assistant project combining Retrieval-Augmented Generation (RAG),
> local ONNX embeddings, and a modern React frontend — designed to make studying smarter, faster,
> and more personalized for every student.

---

## 🛠️ Tech Stack

**Frontend**
- [Next.js 14](https://nextjs.org) — App Router, TypeScript
- [Tailwind CSS](https://tailwindcss.com) + [@tailwindcss/typography](https://tailwindcss.com/docs/typography-plugin)
- [Framer Motion](https://www.framer.com/motion) — animations
- [Lucide React](https://lucide.dev) — icons
- [React Markdown](https://github.com/remarkjs/react-markdown) — markdown rendering

**Backend**
- [FastAPI](https://fastapi.tiangolo.com) — async REST API
- [LangChain](https://langchain.com) — document processing & RAG pipeline
- [fastembed](https://github.com/qdrant/fastembed) — lightweight ONNX embeddings
- [FAISS](https://github.com/facebookresearch/faiss) — in-memory vector search
- [ChromaDB](https://www.trychroma.com) — persistent vector store
- [pdfplumber](https://github.com/jsvine/pdfplumber) — PDF text extraction

**AI / LLM**
- [Groq](https://groq.com) — free ultra-fast inference (`openai/gpt-oss-20b`)
- [OpenAI](https://openai.com) — optional primary provider (`gpt-4o-mini`)

**Deploy**
- [Vercel](https://vercel.com) — frontend hosting (free)
- [Render](https://render.com) — backend Docker hosting (free)
- Deploy Link - (https://studdy-buddy-gray.vercel.app)  
---

*Made with ❤️ for students everywhere.*

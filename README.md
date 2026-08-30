# StudyBuddy AI 🎓

> **AI-powered personal study assistant** — upload your notes or syllabus and instantly get
> simplified explanations, Kahoot-style timed quizzes, smart revision plans, a RAG-powered
> doubt solver, Feynman Technique evaluator, AI flashcards, concept maps, persistent chat
> history, shareable quizzes, a progress dashboard, and AI-generated cheat sheets.
> All in one place, completely free to deploy.

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Vercel-black?style=flat-square&logo=vercel)](https://studdy-buddy-gray.vercel.app)
[![Backend](https://img.shields.io/badge/API-Render-46E3B7?style=flat-square&logo=render)](https://studdy-buddy-api.onrender.com/docs)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178C6?style=flat-square&logo=typescript)](https://www.typescriptlang.org)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)](LICENSE)

---

## 🔗 Live Application Links

| | Link | Description |
|-|------|-------------|
| 🌐 | **[https://studdybuddy-zenmnfbuwdcdqqqj5kpn5g.streamlit.app/](https://studdybuddy-zenmnfbuwdcdqqqj5kpn5g.streamlit.app/)** | **Frontend — open the app here** |
| 💻 | **[https://github.com/tanujthakur9027-stack/studdy_Buddy](https://github.com/tanujthakur9027-stack/studdy_Buddy)** | Source code (this repo) |

> **⚠️ Note:** The backend runs on Render's **free tier** — it sleeps after 15 minutes of
> inactivity. If the app feels slow on first load, wait **30–60 seconds** for the server to
> wake up, then refresh. Subsequent requests are fast.

---

## 👥 Team

| Name | Role |
|------|------|
| 🏆 **Bhavna Agarwal** | **Team Leader** — Project Architecture, AI/ML Integration, Full-Stack |
| **Divya Goyal** | **Team Member** — AI/ML Engineering, RAG Pipeline |
| **Tanuj Kumar Singh** | **Team Member** — Full-Stack Development, Backend API, Deployment |

> Built as an AI study assistant combining Retrieval-Augmented Generation (RAG), local ONNX
> embeddings, streaming LLM responses, and a modern React frontend — designed to make
> studying smarter, faster, and more personalised for every student.

---

## ✨ Features

### 📚 Core Study Tools

| Feature | Description |
|---------|-------------|
| 📄 **Document Upload** | PDF, TXT, MD, DOC, DOCX, PPT, PPTX, XLSX, PNG, JPG, WEBP — parsed, chunked, indexed into FAISS + ChromaDB |
| 🧒 **ELI10 Explain** | Three levels (ELI5 · Beginner · Intermediate) with live streaming, analogies, and key points |
| ⚡ **Kahoot-Style Quiz** | Timed MCQs with live scoring, streaks, hints, difficulty levels, and instant answer review |
| 📅 **Smart Revision Planner** | Day-by-day schedule with concept, quiz, buffer, and rest sessions using spaced repetition |
| 🤖 **RAG Doubt Solver** | Conversational Q&A grounded in your uploaded documents with source citations |

### 🚀 Production Features

| Feature | Description |
|---------|-------------|
| ⚡ **Streaming LLM** | Tokens stream live to the UI — time-to-first-token <1s (vs 5–30s wait before) |
| 🧠 **Feynman Mode** | Type your explanation of a concept — AI scores it (0–100), finds gaps, gives Q&A pairs and a coaching tip |
| 🃏 **AI Flashcards** | Generates flip-card decks from your notes; "Know it / Review it" spaced-repetition loop; past decks saved to DB |
| 🗺️ **Concept Map** | One-click interactive node-edge concept map generated from any uploaded document |
| 💬 **Persistent Chat History** | All Doubt Solver conversations saved to DB — resume past chats, rename/delete sessions |
| 🔗 **Share Quiz Links** | Generate a short link from quiz results — anyone can play the quiz without signing up |
| 📊 **Progress Dashboard** | Quiz score history, streak counter, Feynman history, flashcard stats, weak/strong topic breakdown |
| ✨ **AI Cheat Sheet** | One-click cheat sheet from any uploaded document — streams live, printable as PDF |
| 🗄️ **Persistent Database** | SQLite (dev) / PostgreSQL (prod) — WAL mode enabled; nothing lost on server restart |
| 🛡️ **Rate Limiting** | `slowapi` — 20 req/min per IP on all LLM endpoints |
| 🔒 **Security Headers** | `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `X-Request-ID` |
| 📝 **Structured JSON Logging** | Every request logged as JSON with latency_ms, request_id; Sentry-ready |
| 🎤 **Voice Input + TTS** | Web Speech API — speak your question, hear the answer read aloud |
| 🔖 **Bookmarked Answers** | Save any Q&A pair from the Doubt Solver for quick reference |

---

## 🏗️ Architecture

```
Browser (Next.js 14 · TypeScript · Tailwind CSS · Framer Motion)
   │
   │  HTTPS / SSE (Server-Sent Events for streaming)
   │
   ▼
FastAPI v4  (Python 3.11 · Docker · Render)
   │
   ├── asyncio.to_thread() ──► PDF parse · FAISS index · ChromaDB (non-blocking)
   │
   ├── SQLAlchemy async  ──►  SQLite WAL (dev) / PostgreSQL (prod)
   │   Tables: documents, quiz_sessions, quiz_results, saved_answers,
   │           chat_sessions, chat_messages, flashcard_sessions, flashcards,
   │           feynman_results, shared_resources
   │
   ├── fastembed  BAAI/bge-small-en-v1.5   local ONNX (no API key needed)
   ├── FAISS      in-process vector index   ultra-fast semantic search
   ├── ChromaDB   disk-persisted vector store
   │
   ├── slowapi    rate limiting (20/min per IP)
   ├── Sentry SDK error tracking (optional — set SENTRY_DSN)
   │
   └── OpenAI / Groq API  (streaming enabled)
```

### Backend Layers

| Layer | Technology | Purpose |
|-------|-----------|---------|
| API Framework | FastAPI 0.111 | Async REST + SSE streaming + Swagger UI |
| LLM | OpenAI `gpt-4o-mini` · Groq `llama-3.1-8b-instant` | Answer generation (streaming) |
| Embeddings | fastembed `BAAI/bge-small-en-v1.5` (local ONNX) | Vectors — no API key required |
| Vector DB | FAISS (in-memory) + ChromaDB (persistent) | Semantic search & RAG retrieval |
| Database | SQLAlchemy async + SQLite WAL / PostgreSQL | Persistent storage |
| Thread offload | `asyncio.to_thread()` | CPU-bound ingestion never blocks the event loop |
| Rate Limiting | slowapi | 20 req/min per IP on LLM endpoints |
| Logging | python-json-logger | Structured JSON logs with latency_ms |
| Error Tracking | sentry-sdk[fastapi] | Optional Sentry integration |
| Doc Parsing | pdfplumber → PyPDF2 · python-docx · python-pptx · openpyxl · pytesseract | All formats |

---

## 🌐 API Endpoints

### Core

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/upload` | Upload & index a document (async — offloaded to thread) |
| `POST` | `/api/ask` | RAG Q&A (Standard / ELI5) |
| `POST` | `/api/ask/stream` | RAG Q&A — **streaming SSE** |
| `POST` | `/api/doubt/stream` | Conversational RAG — **streaming SSE** |
| `POST` | `/api/explain` | Topic explanation (JSON) |
| `POST` | `/api/explain/stream` | Topic explanation — **streaming SSE** |
| `POST` | `/api/generate-quiz` | Generate timed MCQ quiz |
| `POST` | `/api/quiz/submit` | Submit quiz answers + persist result |
| `POST` | `/api/generate-plan` | Generate day-by-day revision plan |
| `POST` | `/api/cheatsheet` | AI cheat sheet — **streaming SSE** |
| `POST` | `/api/feynman/evaluate` | Evaluate a Feynman-style explanation (score + gaps + Q&A) |
| `POST` | `/api/flashcards/generate` | Generate a flashcard deck from a document |
| `GET`  | `/api/flashcards` | List saved flashcard sessions for a document |
| `GET`  | `/api/flashcards/{session_id}` | Fetch a specific flashcard deck |
| `POST` | `/api/concept-map` | Generate a concept map (nodes + edges) |

### Data & History

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/documents` | List all uploaded documents |
| `DELETE` | `/api/documents/{doc_id}` | Remove a document |
| `GET` | `/api/quiz/history` | Past quiz results |
| `GET/POST/DELETE` | `/api/saved-answers` | Bookmarked Q&A pairs |
| `GET` | `/api/chats` | List all chat sessions |
| `POST` | `/api/chats` | Create a new chat session |
| `DELETE` | `/api/chats/{id}` | Delete a chat session |
| `GET/POST` | `/api/chats/{id}/messages` | Get / append messages |
| `PATCH` | `/api/chats/{id}/title` | Rename a chat session |
| `GET` | `/api/progress/summary` | Study progress analytics (quiz + Feynman + flashcard stats) |
| `POST` | `/api/share` | Create a shareable quiz/document link |
| `GET` | `/api/share/{id}` | Resolve a share link (public) |

### System

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Server status + DB ping + indexed docs |
| `GET` | `/docs` | Swagger UI |

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
# Open .env and set at minimum:
#   GROQ_API_KEY=gsk_...your-key-here...

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
# → App running at http://localhost:3000
```

---

## ⚙️ Environment Variables

### Backend (`backend/.env`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GROQ_API_KEY` | **yes** (free) | — | Groq key — [console.groq.com](https://console.groq.com) |
| `GROQ_MODEL` | no | `llama-3.1-8b-instant` | Groq model ID |
| `OPENAI_API_KEY` | optional | — | OpenAI key — takes priority over Groq when set |
| `OPENAI_MODEL` | no | `gpt-4o-mini` | OpenAI model name |
| `DATABASE_URL` | no | `sqlite+aiosqlite:///./studybuddy.db` | SQLite (dev) or `postgresql+asyncpg://…` (prod) |
| `CORS_ORIGINS` | no | `http://localhost:3000` | Comma-separated allowed frontend origins |
| `RATE_LIMIT_PER_MINUTE` | no | `20` | Max LLM requests per IP per minute |
| `SENTRY_DSN` | no | — | Paste DSN from [sentry.io](https://sentry.io) to enable error tracking |
| `SENTRY_TRACES_SAMPLE_RATE` | no | `0.1` | Fraction of requests to trace (0.0–1.0) |
| `UPLOAD_DIR` | no | `/tmp/uploads` | File upload directory (writable on Render) |
| `CHROMA_PERSIST_DIR` | no | `/tmp/chroma_db` | ChromaDB storage directory |
| `FAISS_INDEX_DIR` | no | `/tmp/faiss_indexes` | FAISS index directory |
| `MAX_FILE_SIZE_MB` | no | `20` | Max upload size |
| `CHUNK_SIZE` | no | `800` | Text chunk size (chars) |
| `CHUNK_OVERLAP` | no | `120` | Chunk overlap (chars) |

### Frontend (`frontend/.env.local`)

| Variable | Required | Description |
|----------|----------|-------------|
| `NEXT_PUBLIC_API_URL` | **yes** (prod) | Backend URL e.g. `https://studdy-buddy-api.onrender.com` |
| `NEXT_PUBLIC_APP_URL` | no | Frontend origin — used when building share links |

---

## ☁️ Deployment

### Backend → Render (Free)

1. Push code to GitHub
2. Go to [dashboard.render.com](https://dashboard.render.com) → **New → Blueprint**
3. Connect your repo — Render auto-detects `render.yaml`
4. Add env vars in Render → Environment:
   - `GROQ_API_KEY` = your key
   - `DATABASE_URL` = your PostgreSQL URL (or leave blank for SQLite)
   - `CORS_ORIGINS` = your Vercel URL
5. Wait ~5 min for Docker build to complete

> Storage paths (`UPLOAD_DIR`, `CHROMA_PERSIST_DIR`, `FAISS_INDEX_DIR`) default to `/tmp/…`
> which is always writable on Render's container filesystem.

### Frontend → Vercel (Free)

1. Go to [vercel.com/new](https://vercel.com/new) → Import repo
2. Set **Root Directory** → `frontend`
3. Add env variables:
   - `NEXT_PUBLIC_API_URL` = your Render backend URL
   - `NEXT_PUBLIC_APP_URL` = your Vercel URL (for share links)
4. Deploy → copy your Vercel URL
5. Back in Render → update `CORS_ORIGINS` → Save

> Full step-by-step guide: [DEPLOY.md](DEPLOY.md)

---

## 🗂️ Project Structure

```
studdy_Buddy/
├── backend/
│   ├── main.py                    # FastAPI app, middleware, router registration
│   ├── config.py                  # Settings (pydantic-settings, .env)
│   ├── database.py                # SQLAlchemy async engine + WAL pragmas + get_db()
│   ├── requirements.txt
│   ├── Dockerfile                 # python:3.11-slim, fastembed pre-warmed at build
│   ├── render.yaml                # Render Blueprint — Docker service + env vars
│   ├── .env.example
│   ├── models/
│   │   ├── schemas.py             # Pydantic request/response models
│   │   └── db_models.py           # ORM tables: Document, QuizSession, QuizResult,
│   │                              #   SavedAnswer, ChatSession, ChatMessage,
│   │                              #   FlashcardSession, Flashcard, FeynmanResult,
│   │                              #   SharedResource
│   ├── routers/
│   │   ├── ask.py                 # /api/ask + /api/ask/stream
│   │   ├── doubt.py               # /api/doubt/solve + /api/doubt/stream
│   │   ├── explain.py             # /api/explain + /api/explain/stream
│   │   ├── quiz.py                # /api/generate-quiz + /api/quiz/submit + history
│   │   ├── revision.py            # /api/generate-plan
│   │   ├── upload.py              # /api/upload (with pre-flight dir check)
│   │   ├── documents.py           # /api/documents + /api/saved-answers
│   │   ├── chat.py                # /api/chats + /api/chats/{id}/messages
│   │   ├── share.py               # /api/share
│   │   ├── progress.py            # /api/progress/summary
│   │   ├── cheatsheet.py          # /api/cheatsheet (streaming)
│   │   ├── feynman.py             # /api/feynman/evaluate
│   │   ├── flashcards.py          # /api/flashcards/generate + list + fetch
│   │   └── concept_map.py         # /api/concept-map
│   ├── services/
│   │   ├── llm_service.py         # OpenAI/Groq wrapper + streaming generators
│   │   └── document_service.py    # Ingestion (asyncio.to_thread), FAISS, ChromaDB
│   └── utils/
│       ├── log_config.py          # Structured JSON logging setup
│       └── text_utils.py          # Token counting, JSON fence stripping
│
└── frontend/
    ├── src/
    │   ├── app/
    │   │   ├── page.tsx           # Main app — 8 tabs (Upload, ELI10, Quiz, Planner,
    │   │   │                      #   Ask AI, Feynman, Flashcards, Progress)
    │   │   ├── share/[id]/page.tsx  # Public shared quiz player
    │   │   ├── quiz/page.tsx      # Full-page quiz view
    │   │   └── planner/page.tsx   # Full-page revision planner
    │   ├── components/features/
    │   │   ├── FileUpload.tsx      # Drag-and-drop upload + cheat sheet + concept map
    │   │   ├── ExplainModule.tsx   # Streaming ELI10 explanation
    │   │   ├── QuizGame.tsx        # Kahoot-style quiz + share button
    │   │   ├── RevisionPlanner.tsx # Day-by-day revision plan
    │   │   ├── DoubtSolver.tsx     # Streaming RAG chat + session sidebar
    │   │   ├── FeynmanMode.tsx     # Feynman Technique evaluator
    │   │   ├── Flashcards.tsx      # AI flashcard deck with spaced repetition
    │   │   ├── ProgressDashboard.tsx  # Analytics — charts, streaks, Feynman history
    │   │   ├── CheatSheet.tsx      # Streaming cheat sheet modal + print
    │   │   ├── ConceptMapModal.tsx # Interactive concept map modal
    │   │   └── ReviewScreen.tsx    # Post-quiz answer review
    │   ├── lib/
    │   │   ├── api.ts             # All REST API helpers + TypeScript types
    │   │   └── streamApi.ts       # SSE streaming client (streamPost + AbortController)
    │   ├── hooks/
    │   │   ├── useSpeech.ts       # TTS + voice input (Web Speech API)
    │   │   ├── useSavedAnswers.ts  # Bookmarked Q&A state
    │   │   ├── useQuizHistory.ts   # Quiz history state
    │   │   ├── useRevisionPlan.ts  # Revision plan state
    │   │   └── useSound.ts        # Quiz sound effects
    │   └── types/
    │       └── index.ts           # Shared TypeScript interfaces
    └── package.json
```

---

## 🛠️ Tech Stack

### Frontend

| Library | Version | Purpose |
|---------|---------|---------|
| [Next.js](https://nextjs.org) | 14 | App Router, SSR, file-based routing |
| [TypeScript](https://typescriptlang.org) | 5.x | Type safety across the entire frontend |
| [Tailwind CSS](https://tailwindcss.com) | 3 | Utility-first styling |
| [Framer Motion](https://www.framer.com/motion) | 11 | Page + component animations |
| [Lucide React](https://lucide.dev) | latest | Icon library |
| [React Markdown](https://github.com/remarkjs/react-markdown) | 9 | Markdown rendering with GFM |
| [Axios](https://axios-http.com) | 1.x | REST API client |

### Backend

| Library | Version | Purpose |
|---------|---------|---------|
| [FastAPI](https://fastapi.tiangolo.com) | 0.111 | Async REST API framework |
| [SQLAlchemy](https://www.sqlalchemy.org) | 2.x | Async ORM (aiosqlite / asyncpg) + WAL mode |
| [LangChain](https://langchain.com) | 0.3 | Document loading, splitting, RAG pipeline |
| [fastembed](https://github.com/qdrant/fastembed) | 0.3.6 | Local ONNX embeddings (no GPU / no API key) |
| [FAISS](https://github.com/facebookresearch/faiss) | 1.8 | In-memory vector search |
| [ChromaDB](https://www.trychroma.com) | 0.5 | Persistent vector store |
| [slowapi](https://github.com/laurentS/slowapi) | 0.1.9 | Rate limiting middleware |
| [sentry-sdk](https://sentry.io) | 2.x | Error tracking (optional) |
| [python-json-logger](https://github.com/madzak/python-json-logger) | 2.x | Structured JSON log output |
| [pdfplumber](https://github.com/jsvine/pdfplumber) | 0.11 | PDF text extraction |

### AI / LLM

| Provider | Model | Notes |
|----------|-------|-------|
| [Groq](https://groq.com) | `llama-3.1-8b-instant` | **Free** — ultra-fast inference, used as default fallback |
| [OpenAI](https://openai.com) | `gpt-4o-mini` | Optional primary provider — set `OPENAI_API_KEY` |

### Infrastructure

| Service | Purpose |
|---------|---------|
| [Vercel](https://vercel.com) | Frontend hosting (free) |
| [Render](https://render.com) | Backend Docker hosting (free tier) |
| [Sentry](https://sentry.io) | Error monitoring (optional, free tier available) |

---

## 📈 Changelog

| Commit | What changed |
|--------|-------------|
| `8539a9f` | 🔧 Clear all 24 ESLint warnings — unused imports, shadowed vars, missing deps |
| `5e4e4fa` | 🐛 Fix upload on Render — offload ingestion to `asyncio.to_thread()`, use `/tmp` dirs |
| `a3c6f56` | ↩️ Revert speed-up experiment — restore original stable behaviour |
| `10dbc97` | 🐛 Fix Render deploy crash — SQLite `NullPool` cannot accept `pool_size`/`max_overflow` args |
| `f7839a8` | 🐛 Fix Vercel build — escape unescaped JSX entities (`'` → `&apos;`, `"` → `&quot;`) |
| `3d4fa28` | ✨ Add Feynman Mode, AI Flashcards, Concept Map, enhanced Progress Dashboard |
| `64fed53` | ✨ Structured JSON logging · Sentry integration · AI Cheat Sheet generator |
| `d758d13` | ✨ Share quiz via link · Progress dashboard with charts |
| `0fe7f20` | ✨ Persistent chat history · Session sidebar · Rename/delete sessions |
| `94ab43e` | ⚡ Streaming LLM responses (SSE) — `▍` cursor, <1s TTFT |
| `f99d66a` | 🗄️ Persistent database (SQLite/PostgreSQL) · Rate limiting · Security headers |

---

## ⚠️ Known Limitations

- **Single worker** — FAISS indexes are in-process. The Dockerfile enforces `--workers 1`. FAISS resets on restart (Render free tier redeploys wipe `/tmp`); re-upload documents after a redeploy. ChromaDB and SQLite data also live in `/tmp` on Render free tier — upgrade to a paid plan with a Render Disk for true persistence.
- **Free tier cold start** — Render free tier sleeps after 15 min. First request takes 30–60s to wake up.
- **File size limit** — 20 MB per upload (configurable via `MAX_FILE_SIZE_MB`).
- **No authentication** — All documents and API endpoints are currently public. Auth (JWT + NextAuth) is planned for a future phase.

---

## 📄 License

MIT © 2024 StudyBuddy AI Team

---

*Made with ❤️ by the StudyBuddy team — for students everywhere.*

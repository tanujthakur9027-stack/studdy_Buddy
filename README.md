# StudyBuddy AI 🎓

> **AI-powered personal study assistant** — upload your notes or syllabus and instantly get
> simplified explanations, Kahoot-style timed quizzes, smart revision plans, a RAG-powered
> doubt solver, Feynman Technique evaluator, AI flashcards, concept maps, persistent chat
> history, shareable quizzes, a progress dashboard, and AI-generated cheat sheets.
> Built for students at every level — schools, colleges, universities, and online learners.
> All in one place, completely free to deploy.

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Streamlit-FF4B4B?style=flat-square&logo=streamlit)](https://studdybuddy-zenmnfbuwdcdqqqj5kpn5g.streamlit.app/)
[![Backend](https://img.shields.io/badge/API-Render-46E3B7?style=flat-square&logo=render)](https://studdy-buddy-api.onrender.com/docs)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178C6?style=flat-square&logo=typescript)](https://www.typescriptlang.org)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)](LICENSE)

---

## 🔗 Live Application Links

| | Link | Description |
|-|------|-------------|
| 🌐 | **[https://studdybuddy-zenmnfbuwdcdqqqj5kpn5g.streamlit.app/](https://studdybuddy-zenmnfbuwdcdqqqj5kpn5g.streamlit.app/)** | **Primary frontend — open the app here (Streamlit)** |
| 💻 | **[https://github.com/tanujthakur9027-stack/studdy_Buddy](https://github.com/tanujthakur9027-stack/studdy_Buddy)** | Source code (this repo) |

> **⚠️ Note:** The backend runs on Render's **free tier** — it sleeps after 15 minutes of
> inactivity. If the app feels slow on first load, wait **30–60 seconds** for the server to
> wake up, then refresh. Subsequent requests are fast.

---

## 👥 Team

| Name | Role | Contributions |
|------|------|---------------|
| 🏆 **Bhavna Agarwal** | **Team Leader** | Project Architecture, AI/ML Integration, Full-Stack Development |
| **Divya Goyal** | **Team Member** | AI/ML Engineering, RAG Pipeline, Vector Search |
| **Tanuj Kumar Singh** | **Team Member** | Full-Stack Development, Backend API, Deployment & DevOps |

> Built as an AI study assistant combining Retrieval-Augmented Generation (RAG), local ONNX
> embeddings, streaming LLM responses, a Streamlit frontend, and a modern Next.js interface —
> designed to make studying smarter, faster, and more personalised for every student.

---

## ✨ Features

### 📚 Core AI Study Tools

| Feature | Description |
|---------|-------------|
| 📄 **Document Upload** | PDF, DOCX, TXT, MD, PPT, PPTX, XLSX, PNG, JPG, JPEG, WEBP, JFIF, GIF — parsed, chunked, indexed into FAISS + ChromaDB |
| 📝 **Paste Text** | No file? Paste notes or a topic directly — all AI tools work from raw text |
| 🧒 **ELI10 Explain** | Three levels (ELI5 · Beginner · Intermediate) with live streaming, analogies, and key points |
| ⚡ **Kahoot-Style Quiz** | Timed MCQs with live scoring, streaks, hints, difficulty levels, and instant answer review |
| 📅 **Smart Revision Planner** | Day-by-day schedule with concept, quiz, buffer, and rest sessions using spaced repetition |
| 🤖 **RAG Doubt Solver** | Conversational Q&A grounded in your uploaded documents with source citations |
| 🧠 **Feynman Mode** | Type your explanation of a concept — AI scores it (0–100), finds gaps, gives Q&A pairs and a coaching tip |
| 🃏 **AI Flashcards** | Generates flip-card decks from your notes; "Know it / Review it" spaced-repetition loop; past decks saved to DB |
| 🗺️ **Concept Map** | One-click interactive node-edge concept map generated from any uploaded document |
| ✨ **AI Cheat Sheet** | One-click cheat sheet from any uploaded document — streams live, printable as PDF |

### 🏫 Academic Management (Admin & Student)

| Feature | Description |
|---------|-------------|
| 🔐 **JWT Authentication** | Register/login/change-password — every resource scoped per user; role-based access (admin / student) |
| 👑 **Admin Panel** | Manage students, classes, sections, subjects, assignments, marks, timetables, announcements |
| 📋 **Assignments** | Admins publish assignments with file attachments and due dates; students submit with file uploads |
| 📊 **Marks & Grades** | Assessment categories with weightage; per-student mark entry; overall grade computation |
| 🗓️ **Timetable** | Admin-configurable period-by-period weekly timetable published to students |
| 📢 **Announcements** | Class/section-scoped announcements from admin; students see only relevant announcements |
| 🔔 **Notifications** | Real-time notification feed for assignments, marks, timetable changes, and announcements |
| 🤝 **Student Connections** | Send/accept connection requests; share notes only with connections |
| 📁 **Notes Sharing** | Upload and share study notes with classmates (connections / class / public visibility) |

### 🚀 Production Features

| Feature | Description |
|---------|-------------|
| ⚡ **Streaming LLM** | Tokens stream live to the UI — time-to-first-token <1s (vs 5–30s wait before) |
| 💬 **Persistent Chat History** | All Doubt Solver conversations saved to DB — resume past chats, rename/delete sessions |
| 🔗 **Share Quiz Links** | Generate a short link from quiz results — anyone can play the quiz without signing up |
| 📊 **Progress Dashboard** | Quiz score history, streak counter, Feynman history, flashcard stats, weak/strong topic breakdown |
| 🗄️ **Persistent Database** | SQLite (dev) / PostgreSQL (prod) — WAL mode enabled; nothing lost on server restart |
| 🎨 **Animated UI** | Splash screen, staggered card animations, count-up numbers, confetti on quiz score ≥ 70% |
| 🖼️ **GIF Avatar Upload** | Animated GIF + PNG/JPG/WEBP avatars; Pillow multi-frame OCR extracts text from all frames |
| 🛡️ **Rate Limiting** | `slowapi` — per-user-ID (authenticated) / per-IP (anonymous) on all LLM endpoints |
| 🔒 **Security Headers** | `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `X-Request-ID` |
| 📝 **Structured JSON Logging** | Every request logged as JSON with latency_ms, request_id; Sentry-ready |
| 🎤 **Voice Input + TTS** | Web Speech API — speak your question, hear the answer read aloud |
| 🔖 **Bookmarked Answers** | Save any Q&A pair from the Doubt Solver for quick reference |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Streamlit Cloud (Primary UI)    Vercel (Alternative UI)    │
│  streamlit_app/app.py            frontend/ (Next.js 14)     │
└──────────────────────┬──────────────────────────────────────┘
                       │  HTTPS / SSE (Server-Sent Events)
                       ▼
              FastAPI v4  (Python 3.11 · Docker · Render)
                       │
        ┌──────────────┼──────────────────────────┐
        │              │                          │
        ▼              ▼                          ▼
  asyncio.to_thread   SQLAlchemy async       slowapi / Sentry
  PDF parse           SQLite WAL (dev)        rate limiting
  FAISS index         PostgreSQL (prod)       error tracking
  ChromaDB            25+ ORM tables
        │
        ├── fastembed  BAAI/bge-small-en-v1.5  (local ONNX)
        ├── FAISS      in-process vector index
        ├── ChromaDB   disk-persisted vector store
        └── OpenAI / Groq API  (streaming enabled)
```

### Backend Layers

| Layer | Technology | Purpose |
|-------|-----------|---------|
| API Framework | FastAPI 0.111 | Async REST + SSE streaming + Swagger UI |
| LLM | OpenAI `gpt-4o-mini` · Groq `groq/compound-mini` | Answer generation (streaming) |
| Embeddings | fastembed `BAAI/bge-small-en-v1.5` (local ONNX) | Vectors — no API key required |
| Vector DB | FAISS (in-memory) + ChromaDB (persistent) | Semantic search & RAG retrieval |
| Database | SQLAlchemy async + SQLite WAL / PostgreSQL | Persistent storage |
| Auth | JWT (python-jose) + bcrypt | Register / login / role-based access |
| Thread offload | `asyncio.to_thread()` | CPU-bound ingestion never blocks the event loop |
| Rate Limiting | slowapi | 20 req/min per user-ID / IP on LLM endpoints |
| Logging | python-json-logger | Structured JSON logs with latency_ms |
| Error Tracking | sentry-sdk[fastapi] | Optional Sentry integration |
| Doc Parsing | pdfplumber → PyPDF2 · python-docx · python-pptx · openpyxl · pytesseract | All formats |

---

## 🌐 API Endpoints

### Core AI

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

### Auth

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/auth/register` | Create a new user account |
| `POST` | `/api/auth/login` | Obtain a JWT access token |
| `POST` | `/api/auth/change-password` | Change the authenticated user's password |
| `GET`  | `/api/profile` | Get current user profile |
| `PATCH`| `/api/profile` | Update profile (name, academic details) |

### Admin

| Method | Path | Description |
|--------|------|-------------|
| `GET/POST` | `/api/admin/students` | List / register students |
| `GET/POST/DELETE` | `/api/admin/classes` | Manage classes, sections, subjects |
| `GET/POST/PATCH/DELETE` | `/api/admin/assignments` | CRUD assignments |
| `GET/POST` | `/api/admin/submissions` | View / evaluate submissions |
| `GET/POST/PATCH` | `/api/admin/marks` | Enter / update marks |
| `GET/POST/PATCH` | `/api/admin/timetable` | Create / publish timetables |
| `GET/POST` | `/api/admin/announcements` | Post announcements |

### Student

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/assignments` | My assignments with submission status |
| `POST` | `/api/assignments/{id}/submit` | Submit an assignment |
| `GET` | `/api/marks/summary` | My marks & overall grade |
| `GET` | `/api/timetable/today` | Today's timetable periods |
| `GET` | `/api/notifications` | My notification feed |
| `GET` | `/api/notifications/unread-count` | Unread notification count |
| `GET/POST/DELETE` | `/api/connections` | Student connection requests |
| `GET/POST` | `/api/notes` | Browse / upload shared notes |

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
| `POST` | `/api/media/upload` | Upload avatar / media (GIF, PNG, JPG, WEBP) |

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
#   SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")

# Start the API server
uvicorn main:app --reload --port 8000
# → API running at http://localhost:8000
# → Swagger UI at http://localhost:8000/docs
```

### 3. Streamlit Frontend

```bash
cd streamlit_app

# Install dependencies
pip install -r requirements.txt

# Run (the backend is auto-launched as a subprocess)
streamlit run app.py
# → App running at http://localhost:8501
```

### 4. Next.js Frontend (alternative)

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
| `GROQ_MODEL` | no | `groq/compound-mini` | Groq model ID |
| `OPENAI_API_KEY` | optional | — | OpenAI key — takes priority over Groq when set |
| `OPENAI_MODEL` | no | `gpt-4o-mini` | OpenAI model name |
| `SECRET_KEY` | **yes** | — | JWT signing secret — generate with `python -c "import secrets; print(secrets.token_hex(32))"` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | no | `1440` | JWT expiry (default 24 h) |
| `ADMIN_SEED_EMAIL` | no | `admin@studybuddy.com` | Email for the seeded admin account |
| `ADMIN_SEED_PASSWORD` | no | `Admin@StudyBuddy2024` | Password for the seeded admin account |
| `DATABASE_URL` | no | `sqlite+aiosqlite:///./studybuddy.db` | SQLite (dev) or `postgresql+asyncpg://…` (prod) |
| `CORS_ORIGINS` | no | `http://localhost:3000` | Comma-separated allowed frontend origins |
| `RATE_LIMIT_PER_MINUTE` | no | `20` | Max LLM requests per user/IP per minute |
| `SENTRY_DSN` | no | — | Paste DSN from [sentry.io](https://sentry.io) to enable error tracking |
| `SENTRY_TRACES_SAMPLE_RATE` | no | `0.1` | Fraction of requests to trace (0.0–1.0) |
| `UPLOAD_DIR` | no | `/tmp/uploads` | File upload directory (writable on Render) |
| `CHROMA_PERSIST_DIR` | no | `/tmp/chroma_db` | ChromaDB storage directory |
| `FAISS_INDEX_DIR` | no | `/tmp/faiss_indexes` | FAISS index directory |
| `MAX_FILE_SIZE_MB` | no | `20` | Max AI document upload size |
| `ASSIGNMENT_FILE_MAX_MB` | no | `50` | Max assignment attachment size |
| `NOTE_FILE_MAX_MB` | no | `50` | Max note file size |
| `PROFILE_PHOTO_MAX_MB` | no | `5` | Max avatar upload size |
| `CHUNK_SIZE` | no | `800` | Text chunk size (chars) |
| `CHUNK_OVERLAP` | no | `120` | Chunk overlap (chars) |

### Streamlit Cloud Secrets (`streamlit_app/.streamlit/secrets.toml`)

| Secret | Required | Description |
|--------|----------|-------------|
| `GROQ_API_KEY` | **yes** | Groq API key |
| `SECRET_KEY` | **yes** | JWT signing secret (same as backend) |
| `ADMIN_SEED_EMAIL` | no | Seeded admin email |
| `ADMIN_SEED_PASSWORD` | no | Seeded admin password |
| `OPENAI_API_KEY` | optional | OpenAI key |

### Next.js Frontend (`frontend/.env.local`)

| Variable | Required | Description |
|----------|----------|-------------|
| `NEXT_PUBLIC_API_URL` | **yes** (prod) | Backend URL e.g. `https://studdy-buddy-api.onrender.com` |
| `NEXT_PUBLIC_APP_URL` | no | Frontend origin — used when building share links |

---

## ☁️ Deployment

### Streamlit Frontend → Streamlit Cloud (Free) ⭐ Recommended

1. Push code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**
3. Set **Main file path** → `streamlit_app/app.py`
4. Under **Advanced settings → Secrets**, add:
   ```toml
   GROQ_API_KEY = "gsk_..."
   SECRET_KEY   = "your-32-char-hex-secret"
   ADMIN_SEED_EMAIL    = "admin@yourdomain.com"
   ADMIN_SEED_PASSWORD = "YourStrongPassword!"
   ```
5. Deploy — the Streamlit app auto-launches the FastAPI backend as a subprocess

> The backend subprocess runs in the same container. All data lives under `data/` in the repo root and **resets on redeploy**. For persistent storage connect a PostgreSQL database via `DATABASE_URL`.

### Backend → Render (Free)

1. Push code to GitHub
2. Go to [dashboard.render.com](https://dashboard.render.com) → **New → Blueprint**
3. Connect your repo — Render auto-detects `render.yaml`
4. Add env vars in Render → Environment:
   - `GROQ_API_KEY` = your key
   - `SECRET_KEY` = your 32-char hex secret
   - `DATABASE_URL` = your PostgreSQL URL (or leave blank for SQLite)
   - `CORS_ORIGINS` = your Streamlit / Vercel URL
5. Wait ~5 min for Docker build to complete

### Next.js Frontend → Vercel (Free)

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
│   ├── seed_admin.py              # Seeds the admin account on first startup
│   ├── requirements.txt
│   ├── Dockerfile                 # python:3.11-slim, fastembed pre-warmed at build
│   ├── .env.example
│   ├── models/
│   │   ├── schemas.py             # Pydantic request/response models
│   │   └── db_models.py           # 25+ ORM tables: User, StudentProfile, Class,
│   │                              #   Section, Subject, Assignment, Submission,
│   │                              #   AssessmentCategory, Mark, Timetable,
│   │                              #   Notification, Announcement, ConnectionRequest,
│   │                              #   Note, Media, Document, QuizSession, QuizResult,
│   │                              #   SavedAnswer, ChatSession, ChatMessage,
│   │                              #   FlashcardSession, Flashcard, FeynmanResult,
│   │                              #   SharedResource
│   ├── routers/
│   │   ├── auth.py                # /api/auth/register + login + change-password
│   │   ├── student_profile.py     # /api/profile
│   │   ├── admin_students.py      # /api/admin/students
│   │   ├── admin_classes.py       # /api/admin/classes + student classes view
│   │   ├── admin_assignments.py   # /api/admin/assignments
│   │   ├── admin_submissions.py   # /api/admin/submissions
│   │   ├── admin_marks.py         # /api/admin/marks
│   │   ├── admin_timetable.py     # /api/admin/timetable
│   │   ├── announcements.py       # /api/announcements + /api/admin/announcements
│   │   ├── student_assignments.py # /api/assignments (student view)
│   │   ├── student_marks.py       # /api/marks/summary
│   │   ├── student_timetable.py   # /api/timetable/today
│   │   ├── notifications.py       # /api/notifications
│   │   ├── connections.py         # /api/connections
│   │   ├── notes.py               # /api/notes
│   │   ├── media.py               # /api/media/upload
│   │   ├── ask.py                 # /api/ask + /api/ask/stream
│   │   ├── doubt.py               # /api/doubt/solve + /api/doubt/stream
│   │   ├── explain.py             # /api/explain + /api/explain/stream
│   │   ├── quiz.py                # /api/generate-quiz + /api/quiz/submit + history
│   │   ├── revision.py            # /api/generate-plan
│   │   ├── upload.py              # /api/upload
│   │   ├── documents.py           # /api/documents + /api/saved-answers
│   │   ├── chat.py                # /api/chats + /api/chats/{id}/messages
│   │   ├── share.py               # /api/share
│   │   ├── progress.py            # /api/progress/summary
│   │   ├── cheatsheet.py          # /api/cheatsheet (streaming)
│   │   ├── feynman.py             # /api/feynman/evaluate
│   │   ├── flashcards.py          # /api/flashcards/generate + list + fetch
│   │   └── concept_map.py         # /api/concept-map
│   ├── services/
│   │   ├── auth_service.py        # JWT encode/decode, password hashing
│   │   ├── llm_service.py         # OpenAI/Groq wrapper + streaming generators
│   │   ├── document_service.py    # Ingestion (asyncio.to_thread), FAISS, ChromaDB
│   │   ├── marks_service.py       # Grade computation helpers
│   │   ├── notification_service.py# Notification fan-out helpers
│   │   ├── timetable_service.py   # Period time calculation
│   │   ├── email_service.py       # SMTP email helpers (optional)
│   │   └── storage_service.py     # File read/write helpers
│   └── utils/
│       ├── log_config.py          # Structured JSON logging setup
│       └── text_utils.py          # Token counting, JSON fence stripping
│
├── streamlit_app/                 # ← Primary deployed frontend (Streamlit Cloud)
│   ├── app.py                     # Entry point — launches backend subprocess, routing
│   ├── requirements.txt
│   ├── core/
│   │   ├── api_client.py          # HTTP helpers (api_get/post/patch + SSE streaming)
│   │   ├── auth_state.py          # Login/logout/require_login guards (st.rerun() pattern)
│   │   ├── animations.py          # CSS animations — splash, fade-up, confetti
│   │   ├── styles.py              # Global dark-mode CSS injection
│   │   └── media_uploader.py      # GIF/image upload widget helper
│   └── pages/
│       ├── login.py               # Login + registration (universal institution types)
│       ├── dashboard.py           # Student & admin dashboards with stat cards
│       ├── learning.py            # AI Study Tools — all 9 tabs
│       ├── classes.py             # Classes, assignments, timetable, marks, notes
│       ├── profile.py             # Profile, avatar upload, password change, logout
│       └── admin.py               # Admin panel — students, classes, assignments, marks
│
└── frontend/                      # Alternative frontend (Next.js / Vercel)
    ├── src/
    │   ├── app/
    │   │   ├── page.tsx           # Main app — AI study tabs
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

### Streamlit Frontend

| Library | Purpose |
|---------|---------|
| [Streamlit](https://streamlit.io) | Multipage app framework — routing, widgets, state management |
| [requests](https://docs.python-requests.org) | REST API calls to the backend subprocess |
| [Pillow](https://pillow.readthedocs.io) | GIF / image processing for avatar uploads |

### Next.js Frontend

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
| [python-jose](https://github.com/mpdavis/python-jose) | 3.x | JWT encode / decode |
| [passlib[bcrypt]](https://passlib.readthedocs.io) | 1.x | Password hashing |
| [LangChain](https://langchain.com) | 0.3 | Document loading, splitting, RAG pipeline |
| [fastembed](https://github.com/qdrant/fastembed) | 0.3.6 | Local ONNX embeddings (no GPU / no API key) |
| [FAISS](https://github.com/facebookresearch/faiss) | 1.8 | In-memory vector search |
| [ChromaDB](https://www.trychroma.com) | 0.5 | Persistent vector store |
| [slowapi](https://github.com/laurentS/slowapi) | 0.1.9 | Rate limiting middleware |
| [sentry-sdk](https://sentry.io) | 2.x | Error tracking (optional) |
| [python-json-logger](https://github.com/madzak/python-json-logger) | 2.x | Structured JSON log output |
| [pdfplumber](https://github.com/jsvine/pdfplumber) | 0.11 | PDF text extraction |
| [Pillow](https://pillow.readthedocs.io) | 10.x | Image + animated GIF processing / OCR |

### AI / LLM

| Provider | Model | Notes |
|----------|-------|-------|
| [Groq](https://groq.com) | `groq/compound-mini` | **Free** — ultra-fast inference, used as default |
| [OpenAI](https://openai.com) | `gpt-4o-mini` | Optional primary provider — set `OPENAI_API_KEY` |

### Infrastructure

| Service | Purpose |
|---------|---------|
| [Streamlit Cloud](https://streamlit.io/cloud) | Primary frontend hosting (free) |
| [Vercel](https://vercel.com) | Alternative Next.js frontend hosting (free) |
| [Render](https://render.com) | Backend Docker hosting (free tier) |
| [Sentry](https://sentry.io) | Error monitoring (optional, free tier available) |

---

## 📈 Changelog

| Commit | What changed |
|--------|-------------|
| `fdc385a` | 🔧 Add debug output files to `.gitignore` |
| `caca8cd` | 🐛 Fix `StreamlitPageNotFoundError` — replace `st.switch_page()` with `st.rerun()` for all auth transitions; remove `session_state["_pages_dir"]` anti-pattern |
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
- **Streamlit Cloud data reset** — The `data/` directory (SQLite DB, uploads, vector indexes) is ephemeral on Streamlit Cloud and resets on redeploy. Connect a PostgreSQL `DATABASE_URL` and external file storage for persistence.
- **Free tier cold start** — Render free tier sleeps after 15 min. First request takes 30–60s to wake up.
- **File size limit** — 20 MB per AI document upload (configurable via `MAX_FILE_SIZE_MB`); 50 MB for assignment/note attachments.

---

## 📄 License

MIT © 2026 StudyBuddy AI Team

---

*Made with ❤️ by the StudyBuddy team — for students everywhere.*

# 🎓 AI Study Buddy & Personalized Learning Agent

> A full-stack AI-powered study assistant that turns your notes and syllabi into interactive quizzes, ELI5 explanations, a personalized revision calendar, and an intelligent RAG doubt-solver — all in one clean, dark-mode UI.

---

## ✨ Feature Overview

| Feature | Description |
|---|---|
| **Document Upload** | Drag-and-drop PDF, TXT, or DOCX notes. Parsed with `pdfplumber` (primary) + `PyPDF2` (fallback), then indexed into FAISS (in-memory) and ChromaDB (persistent). |
| **Explain Like I'm 10** | Select any topic and get a simplified explanation at three levels — ELI5, Beginner, or Intermediate — with a real-world analogy and bullet-point key takeaways. |
| **Kahoot-Style Quiz Game** | AI-generated MCQ quizzes with a per-question countdown ring, streak tracking, colour-coded Kahoot options, hints on timeout, and a full review screen with topic-level accuracy bars. |
| **Smart Revision Planner** | Enter your exam date and daily study hours; the AI generates a day-by-day schedule with `concept`, `quiz`, `buffer`, and `rest` sessions, priority labels, study techniques, and resources. Completion state is persisted in `localStorage`. |
| **RAG Doubt Solver** | Ask any question about your uploaded documents. Retrieval is 4-tier (FAISS per-doc → FAISS global → ChromaDB → full-text fallback) with source attribution and follow-up question suggestions. |

---

## 🗂 Project Structure

```
Studdy_Buddy/
├── README.md
│
├── backend/                         # FastAPI Python service
│   ├── main.py                      # App entry, CORS, lifespan, router registration
│   ├── config.py                    # Pydantic-settings config (reads .env)
│   ├── requirements.txt
│   ├── .env.example                 # ← copy to .env and fill in your key
│   ├── models/
│   │   └── schemas.py               # All Pydantic request/response models
│   ├── routers/
│   │   ├── upload.py                # POST /api/upload
│   │   ├── ask.py                   # POST /api/ask
│   │   ├── quiz.py                  # POST /api/generate-quiz  POST /quiz/submit
│   │   ├── revision.py              # POST /api/generate-plan
│   │   ├── explain.py               # POST /explain
│   │   └── doubt.py                 # POST /doubt/solve
│   ├── services/
│   │   ├── document_service.py      # PDF/TXT parsing, FAISS, ChromaDB, retrieve_context()
│   │   └── llm_service.py           # Async OpenAI wrapper
│   └── utils/
│       └── text_utils.py            # clean_text(), count_tokens(), truncate_to_tokens()
│
└── frontend/                        # Next.js 14 (App Router) service
    ├── package.json
    ├── next.config.ts
    ├── tailwind.config.ts
    ├── .env.example                 # ← copy to .env.local
    └── src/
        ├── app/
        │   ├── layout.tsx           # Root layout, Inter font, Toaster
        │   ├── page.tsx             # Main SPA — sidebar nav + tab routing
        │   ├── globals.css          # Tailwind base + custom component tokens
        │   ├── quiz/page.tsx        # Standalone /quiz route
        │   └── planner/page.tsx     # Standalone /planner route
        ├── components/
        │   ├── ui/
        │   │   ├── index.tsx        # Spinner, Badge, ProgressBar
        │   │   └── QuizTimer.tsx    # SVG circular countdown ring
        │   └── features/
        │       ├── FileUpload.tsx   # Drag-and-drop with react-dropzone
        │       ├── ExplainModule.tsx
        │       ├── QuizGame.tsx     # Kahoot state machine (config→countdown→playing→results)
        │       ├── ReviewScreen.tsx # Post-quiz topic accuracy + expandable cards
        │       ├── RevisionPlanner.tsx
        │       └── DoubtSolver.tsx
        ├── hooks/
        │   ├── useSound.ts          # Web Audio API synth sounds (no audio files needed)
        │   └── useRevisionPlan.ts   # localStorage completion tracking
        ├── lib/
        │   └── api.ts               # Typed axios client for all endpoints
        └── types/
            └── index.ts
```

---

## 🚀 Quick Start

### Prerequisites

| Tool | Version |
|---|---|
| Node.js | ≥ 18 |
| Python | ≥ 3.10 |
| pip | ≥ 23 |
| OpenAI API key | Required |

---

### 1 — Clone & enter the project

```bash
git clone https://github.com/your-handle/studdy-buddy.git
cd studdy-buddy
```

---

### 2 — Backend setup

```bash
cd backend

# Create and activate a virtual environment
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
```

Open `backend/.env` and set your OpenAI key:

```env
OPENAI_API_KEY=sk-...your-key-here...
OPENAI_MODEL=gpt-4o-mini          # or gpt-4o for higher quality
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

CHROMA_PERSIST_DIR=./chroma_db
FAISS_INDEX_DIR=./faiss_indexes
UPLOAD_DIR=./uploads
MAX_FILE_SIZE_MB=20

CHUNK_SIZE=800
CHUNK_OVERLAP=100

# Add your frontend origin (comma-separated for multiple)
CORS_ORIGINS=http://localhost:3000
```

Start the API server:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Interactive API docs available at **http://localhost:8000/docs**

---

### 3 — Frontend setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env.local
```

`frontend/.env.local` contents:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Start the dev server:

```bash
npm run dev
```

App available at **http://localhost:3000**

---

## 🌐 API Reference

All endpoints accept and return `application/json` unless noted.  
Base URL: `http://localhost:8000`

---

### `POST /api/upload`

Upload a study document (PDF, TXT, or DOCX).

**Request** — `multipart/form-data`

| Field | Type | Required | Notes |
|---|---|---|---|
| `file` | File | ✅ | Max 20 MB. Accepted: `.pdf`, `.txt`, `.docx` |

**Response `200`**

```json
{
  "doc_id": "abc123",
  "filename": "physics_notes.pdf",
  "chunks": 42,
  "total_chars": 18500,
  "faiss_vectors": 42,
  "chroma_vectors": 42,
  "parsing_method": "pdfplumber",
  "message": "Document ingested successfully"
}
```

---

### `POST /api/ask`

Ask a question about an uploaded document (RAG Q&A).

**Request**

```json
{
  "question": "What is Newton's second law?",
  "doc_id": "abc123",
  "mode": "standard",
  "conversation_history": []
}
```

| Field | Type | Notes |
|---|---|---|
| `question` | string | Required |
| `doc_id` | string | Optional — scope retrieval to one document |
| `mode` | `"standard"` \| `"eli5"` | Default `"standard"` |
| `conversation_history` | `[{role, content}]` | Optional multi-turn context |

**Response `200`**

```json
{
  "answer": "Newton's second law states F = ma ...",
  "sources": ["Chunk from page 3 of physics_notes.pdf"],
  "follow_up_questions": ["How does mass affect acceleration?"],
  "mode": "standard",
  "retrieval_method": "faiss_per_doc"
}
```

---

### `POST /api/generate-quiz`

Generate an AI MCQ quiz from a document or free-form topic.

**Request**

```json
{
  "doc_id": "abc123",
  "topic": "Newton's Laws",
  "num_questions": 10,
  "difficulty": "mixed",
  "timer_seconds": 30
}
```

| Field | Default | Notes |
|---|---|---|
| `num_questions` | `10` | 1–20 |
| `difficulty` | `"mixed"` | `easy` / `medium` / `hard` / `mixed` |
| `timer_seconds` | `30` | Sent back to frontend for countdown |

**Response `200`**

```json
{
  "quiz_id": "quiz_xyz",
  "topic": "Newton's Laws",
  "timer_seconds": 30,
  "difficulty": "mixed",
  "questions": [
    {
      "id": "q1",
      "question": "Which of the following ...",
      "options": ["A", "B", "C", "D"],
      "correct_index": 2,
      "explanation": "Because ...",
      "difficulty": "medium",
      "topic_tag": "Newton's Second Law",
      "hint": "Think about F = ma ..."
    }
  ]
}
```

---

### `POST /quiz/submit`

Submit quiz answers and receive a detailed score report.

**Request**

```json
{
  "quiz_id": "quiz_xyz",
  "answers": { "q1": 2, "q2": 0, "q3": -1 },
  "time_taken": 145
}
```

`-1` in answers means the question timed out.

**Response `200`**

```json
{
  "score": 7,
  "total": 10,
  "percentage": 70.0,
  "time_taken": 145,
  "grade": "B",
  "strong_topics": ["Newton's First Law"],
  "weak_topics": ["Newton's Third Law"],
  "recommendations": ["Review Newton's Third Law with worked examples"],
  "details": [ ... ]
}
```

Grades: **S** (≥ 95%) · **A** (≥ 85%) · **B** (≥ 70%) · **C** (≥ 55%) · **D** (< 55%)

---

### `POST /api/generate-plan`

Generate a day-by-day personalized revision schedule.

**Request**

```json
{
  "exam_date": "2025-08-15",
  "daily_hours": 3,
  "syllabus_text": "Chapter 1: Kinematics\nChapter 2: Dynamics ...",
  "weak_topics": ["Thermodynamics"],
  "doc_id": "abc123"
}
```

**Response `200`**

```json
{
  "plan": [
    {
      "date": "2025-07-20",
      "day_label": "Day 1",
      "session_type": "concept",
      "topic": "Kinematics",
      "subtopics": ["Velocity", "Acceleration"],
      "duration_mins": 90,
      "priority": "high",
      "technique": "Feynman Technique",
      "resources": ["Chapter 1 notes"],
      "notes": "Focus on equations of motion"
    }
  ],
  "summary": "14-day plan covering 8 topics ...",
  "tips": ["Use spaced repetition for formulas"],
  "stats": {
    "total_days": 14,
    "study_days": 10,
    "quiz_days": 2,
    "buffer_days": 1,
    "rest_days": 1,
    "total_study_mins": 1800,
    "topics_covered": 8,
    "days_to_exam": 14
  },
  "topic_list": ["Kinematics", "Dynamics", ...]
}
```

---

### `POST /explain`

Get a structured explanation of any topic at a chosen complexity level.

**Request**

```json
{
  "topic": "Photosynthesis",
  "doc_id": "abc123",
  "level": "eli5"
}
```

`level`: `"eli5"` | `"beginner"` | `"intermediate"`

**Response `200`**

```json
{
  "explanation": "Plants are like tiny solar-powered kitchens ...",
  "analogy": "Imagine a leaf is a solar panel ...",
  "key_points": ["Sunlight + CO₂ + H₂O → Glucose + O₂", "Happens in chloroplasts"]
}
```

---

### `POST /doubt/solve`

Multi-turn RAG chat over uploaded documents.

**Request**

```json
{
  "question": "Why does tension vary in an Atwood machine?",
  "doc_id": "abc123",
  "conversation_history": [
    { "role": "user", "content": "What is an Atwood machine?" },
    { "role": "assistant", "content": "An Atwood machine consists of ..." }
  ]
}
```

**Response `200`**

```json
{
  "answer": "Tension varies because ...",
  "sources": ["Relevant passage from your notes"],
  "follow_up_questions": ["What happens when masses are equal?"]
}
```

---

### `GET /health`

```json
{
  "status": "ok",
  "model": "gpt-4o-mini",
  "indexed_documents": 3,
  "faiss_vectors": 126
}
```

---

## 🛠 Tech Stack

### Frontend
| Library | Purpose |
|---|---|
| Next.js 14 (App Router) | Framework, file-based routing |
| Tailwind CSS 3 | Utility-first styling |
| Framer Motion 11 | Page and component animations |
| Lucide React | Icon set |
| Axios | HTTP client |
| react-dropzone | File drag-and-drop |
| react-hot-toast | Toast notifications |
| react-markdown + remark-gfm | Markdown rendering |
| Web Audio API | Synthesised quiz sounds (no audio files) |

### Backend
| Library | Purpose |
|---|---|
| FastAPI | Async HTTP framework |
| Pydantic v2 + pydantic-settings | Data validation and config |
| OpenAI SDK | GPT-4o / GPT-4o-mini completions + embeddings |
| LangChain + langchain-community | Document loaders, text splitters |
| pdfplumber | Primary PDF text extraction |
| PyPDF2 | Fallback PDF parser |
| FAISS (faiss-cpu) | In-memory per-document vector search |
| ChromaDB | Persistent cross-session vector store |
| aiofiles | Async file I/O |
| tiktoken | Token counting for context window management |
| uvicorn | ASGI server |

---

## ⚙️ Environment Variables

### Backend (`backend/.env`)

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | — | **Required.** Your OpenAI secret key |
| `OPENAI_MODEL` | `gpt-4o-mini` | Chat completion model |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding model for vector indexing |
| `CHROMA_PERSIST_DIR` | `./chroma_db` | ChromaDB disk storage path |
| `FAISS_INDEX_DIR` | `./faiss_indexes` | FAISS index snapshot directory |
| `UPLOAD_DIR` | `./uploads` | Uploaded file storage |
| `MAX_FILE_SIZE_MB` | `20` | Upload size limit |
| `CHUNK_SIZE` | `800` | Characters per text chunk |
| `CHUNK_OVERLAP` | `100` | Overlap between adjacent chunks |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated allowed frontend origins |

### Frontend (`frontend/.env.local`)

| Variable | Default | Description |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend API base URL |

---

## 🎮 Demo Walkthrough

1. **Upload** — Drag a PDF textbook chapter onto the upload panel. Watch the ingestion stats (chunks, vectors) appear.
2. **Explain** — Type a topic name (e.g. "Newton's Laws") and pick ELI5. Get an analogy + key points in seconds.
3. **Quiz** — Click "Generate Quiz", set 10 questions / mixed difficulty / 30 s timer. Race the countdown ring, earn streak bonuses, see instant explanations on wrong answers. Check the Review screen for weak topics.
4. **Planner** — Enter your exam date and daily hours. The AI builds a full calendar with colour-coded session types. Tick tasks off — state persists across page refreshes.
5. **Doubt Solver** — Ask multi-turn follow-up questions. Each answer cites the exact passage from your notes.

---

## 🧩 Architecture Diagram

```
┌─────────────────────────────────────────────┐
│              Browser (Next.js)               │
│  FileUpload │ ExplainModule │ QuizGame        │
│  RevisionPlanner │ DoubtSolver               │
└───────────────────┬─────────────────────────┘
                    │ axios (NEXT_PUBLIC_API_URL)
                    ▼
┌─────────────────────────────────────────────┐
│            FastAPI (port 8000)               │
│                                             │
│  POST /api/upload   → document_service      │
│  POST /api/ask      → RAG → llm_service     │
│  POST /api/generate-quiz  → llm_service     │
│  POST /api/generate-plan  → llm_service     │
│  POST /explain      → llm_service           │
│  POST /doubt/solve  → RAG → llm_service     │
└──────────────┬──────────────────────────────┘
               │
       ┌───────┴────────┐
       ▼                ▼
 FAISS (in-memory)  ChromaDB (disk)
 per-doc indexes    persistent store
       └───────┬────────┘
               ▼
         OpenAI API
   (Embeddings + Chat Completions)
```

---

## 🔒 Security Notes

- **Never commit `backend/.env`** — it contains your OpenAI key. It is already in `.gitignore`.
- `CORS_ORIGINS` is a strict allowlist. Update it before any public deployment.
- `MAX_FILE_SIZE_MB` enforces upload limits at the application layer.
- FAISS indexes are in-process memory only — they reset on server restart. ChromaDB persists to disk.

---

## 📦 Production Build

### Frontend

```bash
cd frontend
npm run build
npm start            # serves on port 3000
```

### Backend

```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2
```

For production, set `CORS_ORIGINS` to your deployed frontend URL and use a process manager (e.g. `supervisor`, `systemd`, or a container).

---

## 🐛 Known Limitations

- **FAISS indexes are per-process**: uploading a document and restarting the server loses the in-memory index (ChromaDB remains). For production, serialise FAISS indexes to `FAISS_INDEX_DIR` on every write.
- **Single-user design**: document stores are global (keyed by `doc_id`). Multi-user deployments need per-user namespacing.
- **No auth layer**: suitable for hackathon / local demos. Add JWT middleware before any public deployment.

---

## 📄 License

MIT — see [LICENSE](LICENSE) for details.

---

<p align="center">Built with ❤️ for hackathons and curious learners everywhere.</p>

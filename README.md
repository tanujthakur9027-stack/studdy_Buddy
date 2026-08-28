# StudyBuddy AI

> AI-powered personal study assistant — upload your notes or syllabus and get
> simplified explanations, Kahoot-style quizzes, smart revision plans, and a
> RAG-powered doubt solver.

---

## Architecture

```
frontend/   Next.js 14 (React, TypeScript, Tailwind CSS)  →  Vercel
backend/    FastAPI (Python 3.11)                          →  Render (Docker)
```

### Backend components

| Layer | Technology | Purpose |
|-------|-----------|---------|
| API | FastAPI | REST endpoints |
| LLM | OpenAI (primary) · Groq (fallback) | Answer generation |
| Embeddings | HuggingFace `all-MiniLM-L6-v2` (local) | Vector embeddings |
| Vector DB | FAISS (in-memory) + ChromaDB (persistent) | Semantic search |
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

## Local Development

### Prerequisites

- Python 3.11+
- Node.js 18+
- At least one of: `OPENAI_API_KEY` or `GROQ_API_KEY`

### Backend

```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt

# Copy and fill in the env file
cp .env.example .env
# Edit .env — set OPENAI_API_KEY or GROQ_API_KEY

uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install

# Create .env.local
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

npm run dev
# → http://localhost:3000
```

---

## Environment Variables

### Backend (`.env`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | one of these | — | OpenAI API key (primary LLM) |
| `OPENAI_MODEL` | no | `gpt-4o-mini` | OpenAI model name |
| `GROQ_API_KEY` | one of these | — | Groq API key (free fallback LLM) |
| `GROQ_MODEL` | no | `llama-3.3-70b-versatile` | Groq model name |
| `CORS_ORIGINS` | no | `http://localhost:3000` | Comma-separated allowed origins |
| `UPLOAD_DIR` | no | `./uploads` | File upload directory |
| `CHROMA_PERSIST_DIR` | no | `./chroma_db` | ChromaDB storage |
| `FAISS_INDEX_DIR` | no | `./faiss_indexes` | FAISS index directory |
| `MAX_FILE_SIZE_MB` | no | `20` | Maximum upload size |
| `CHUNK_SIZE` | no | `800` | Text chunk size (chars) |
| `CHUNK_OVERLAP` | no | `120` | Chunk overlap (chars) |

### Frontend (`.env.local`)

| Variable | Required | Description |
|----------|----------|-------------|
| `NEXT_PUBLIC_API_URL` | yes (prod) | Backend URL (e.g. `https://your-api.onrender.com`) |

---

## Deployment

### Backend → Render

1. Push code to GitHub.
2. In Render dashboard → **New Web Service** → connect repo.
3. `render.yaml` handles the Docker build automatically.
4. Set `OPENAI_API_KEY` (or `GROQ_API_KEY`) in Render → Environment.

### Frontend → Vercel

1. Import repo in Vercel dashboard.
2. Set `NEXT_PUBLIC_API_URL` → your Render backend URL.
3. Deploy.

---

## Known Limitations

- **Single worker required**: FAISS indexes are in-process (per-worker). The Dockerfile and Procfile enforce `--workers 1`. Uploaded documents are lost on restart (ChromaDB persists across restarts, but FAISS is rebuilt from scratch on the next upload).
- **In-memory quiz store**: Quiz sessions (`quiz_id → questions`) are stored in a Python dict. They are lost on restart. Always generate a new quiz after restarting the server.
- **File size limit**: 20 MB per upload (configurable via `MAX_FILE_SIZE_MB`).
- **Supported formats**: PDF, TXT, MD, DOC, DOCX.

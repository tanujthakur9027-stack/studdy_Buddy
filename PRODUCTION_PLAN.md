# StudyBuddy AI — Production Roadmap

> Full audit of the current state and a phased plan to make StudyBuddy a real-world production application.

---

## Current State Summary

StudyBuddy is a **polished MVP** with strong AI features but critical production gaps:

- ✅ Excellent UX, animations, and feature depth (quiz, planner, RAG chat, explanations)
- ✅ Sophisticated dual vector store RAG pipeline (FAISS + ChromaDB)
- ✅ Rich file format support (PDF, DOCX, PPT, XLSX, images via OCR)
- 🔴 **Zero authentication** — anyone can access all documents and APIs
- 🔴 **No persistent database** — users lose all work on browser close or server restart
- 🔴 **No rate limiting** — open to abuse and LLM cost spikes
- 🔴 **In-process quiz store** — quiz sessions lost on server restart
- 🟠 **No streaming** — 5–30s wait before any LLM text appears
- 🟠 **No monitoring** — completely blind to production errors

---

## Phase 0 — Critical (Must have before any real users)

### Sub-task 0.1 — User Authentication (JWT + NextAuth)

**Intent**: Add a complete auth layer so users can sign up, log in, and own their data.

**Expected Outcomes**:
- Users can register with email/password or Google OAuth
- JWT access tokens issued on login; refresh tokens in httpOnly cookies
- All API endpoints protected — unauthenticated requests get 401
- Frontend shows login/signup pages and persists auth state

**Todo List**:
1. Add `python-jose`, `passlib[bcrypt]`, `sqlalchemy`, `alembic`, `asyncpg` to `requirements.txt`
2. Create `backend/database.py` — SQLAlchemy async engine + session factory (PostgreSQL)
3. Create `backend/models/db_models.py` — `User`, `Document`, `QuizResult`, `SavedAnswer` tables
4. Create `backend/routers/auth.py` — `POST /api/auth/register`, `POST /api/auth/login`, `POST /api/auth/refresh`
5. Create `backend/utils/auth.py` — JWT encode/decode, `get_current_user` dependency
6. Add `POSTGRES_URL` and `JWT_SECRET` to `backend/config.py` and `.env.example`
7. Add `get_current_user: User = Depends(auth)` to all existing routers
8. Filter all `retrieve_context()` calls by `user_id` (add `user_id` to ChromaDB metadata)
9. Install NextAuth.js (`next-auth`) in frontend
10. Create `frontend/src/app/api/auth/[...nextauth]/route.ts` with Credentials + Google providers
11. Add login/signup pages (`frontend/src/app/auth/`)
12. Wrap the app in `<SessionProvider>` and redirect unauthenticated users to `/auth/login`

**Relevant Context**:
- `backend/main.py` — register new auth router here
- `backend/routers/upload.py`, `ask.py`, `quiz.py`, `revision.py`, `explain.py`, `doubt.py` — add `Depends(get_current_user)` to each
- `backend/services/document_service.py` — `process_and_index()` and `retrieve_context()` need `user_id` parameter
- `frontend/src/app/page.tsx` — protected route wrapping
- `frontend/src/lib/api.ts` — add `Authorization: Bearer <token>` header to all axios requests

**Status**: [ ] pending

---

### Sub-task 0.2 — Persistent Database (PostgreSQL)

**Intent**: Replace all in-memory and localStorage stores with a real database so nothing is ever lost.

**Expected Outcomes**:
- Quiz sessions stored in DB (not in-process dict) — survive server restarts
- User's uploaded documents linked to their account — persist across browser sessions
- Quiz history, saved answers, and revision plans stored in DB — sync across devices

**Todo List**:
1. Create `alembic` migration for all tables from Sub-task 0.1
2. Replace `_quiz_store: dict` in `backend/routers/quiz.py` with `QuizSession` DB table CRUD
3. Create `backend/routers/documents.py` — `GET /api/documents` (list user's docs), `DELETE /api/documents/{doc_id}`
4. Store document metadata (filename, upload date, page count, description) in `Document` table on upload
5. Store quiz results in `QuizResult` table when quiz is submitted
6. Add `GET /api/quiz/history` endpoint returning user's past quiz results
7. Add `GET/POST/DELETE /api/saved-answers` endpoints for bookmarked answers
8. Update `frontend/src/app/page.tsx` — replace `sessionStorage` doc loading with `GET /api/documents` on mount
9. Update `frontend/src/hooks/useQuizHistory.ts` — fetch from API instead of `localStorage`
10. Update `frontend/src/hooks/useSavedAnswers.ts` — fetch/save from API instead of `localStorage`

**Relevant Context**:
- `backend/routers/quiz.py:40` — `_quiz_store` dict (the main problem)
- `backend/routers/upload.py` — add DB save after indexing
- `frontend/src/app/page.tsx:27–45` — `loadDocs()` and `saveDocs()` using `sessionStorage`
- `frontend/src/hooks/useQuizHistory.ts` — localStorage-based; replace with API calls
- `frontend/src/hooks/useSavedAnswers.ts` — localStorage-based; replace with API calls

**Status**: [ ] pending

---

### Sub-task 0.3 — Rate Limiting & Security Hardening

**Intent**: Protect the API from abuse, prevent LLM cost spikes, and fix security holes.

**Expected Outcomes**:
- Each user limited to N LLM requests per minute (configurable per plan)
- File upload limits enforced per user (not just per request)
- Prompt injection mitigated with input sanitization
- CORS locked to specific allowed origins
- API keys never exposed in logs or error messages

**Todo List**:
1. Add `slowapi` to `requirements.txt`
2. Add `RateLimiter` middleware to `backend/main.py` — `10/minute` for free tier
3. Add per-user daily LLM call quota tracked in DB or Redis
4. Sanitize `req.question` in `ask.py` — strip HTML, limit to 2000 chars, reject code injection patterns
5. Update `backend/config.py` — make `CORS_ORIGINS` required env var with no default
6. Add `X-Request-ID` middleware for traceability
7. Add magic byte validation to `upload.py` (use `python-magic` library to verify file content matches extension)
8. Add `.gitignore` rule for `.env` if not already present
9. Add `helmet` equivalent headers in FastAPI (`X-Content-Type-Options`, `X-Frame-Options`)
10. Add max input length validation to all request schemas in `backend/models/schemas.py`

**Relevant Context**:
- `backend/routers/ask.py:121` — `req.question` pasted directly into LLM prompt
- `backend/main.py` — CORS middleware
- `backend/config.py:22` — `cors_origins: str = "http://localhost:3000"` hardcoded default
- `backend/routers/upload.py:27–37` — MIME + extension validation (needs magic byte check)
- `backend/models/schemas.py` — all request schemas need `max_length` validators

**Status**: [ ] pending

---

## Phase 1 — Scalability (Before >100 concurrent users)

### Sub-task 1.1 — Streaming LLM Responses (Server-Sent Events)

**Intent**: Stream LLM tokens to the frontend as they are generated so users see text immediately instead of waiting 5–30 seconds.

**Expected Outcomes**:
- All LLM responses (Ask, Doubt, Explain) stream token-by-token
- Frontend shows a typing cursor and renders markdown as it arrives
- Time-to-first-token < 1 second (vs current 5–30 seconds)
- AbortController cancels in-flight requests when user navigates away

**Todo List**:
1. Add `StreamingResponse` and `EventSourceResponse` (sse-starlette) to backend
2. Modify `backend/services/llm_service.py` — add `stream=True` option to `chat_with_history()`
3. Create streaming endpoints: `POST /api/ask/stream`, `POST /api/doubt/stream`, `POST /api/explain/stream`
4. Keep non-streaming endpoints for quiz/planner (those need full JSON responses)
5. Install `eventsource-parser` in frontend
6. Create `frontend/src/lib/streamApi.ts` — `fetchStream()` helper that reads SSE and yields tokens
7. Update `DoubtSolver.tsx` — replace `askQuestion()` call with streaming version; append tokens to last message
8. Update `ExplainModule.tsx` — same streaming treatment
9. Add `AbortController` to cancel in-flight requests when component unmounts
10. Show a blinking cursor `▍` at the end of in-progress messages

**Relevant Context**:
- `backend/services/llm_service.py` — `chat_with_history()` wraps OpenAI/Groq calls
- `backend/routers/ask.py` — main ask route to duplicate as streaming variant
- `frontend/src/components/features/DoubtSolver.tsx:107–133` — `sendMessage()` callback
- `frontend/src/components/features/ExplainModule.tsx:33–44` — `handleExplain()` function
- `frontend/src/lib/api.ts` — `uploadDocument()`, `askQuestion()` etc.

**Status**: [ ] pending

---

### Sub-task 1.2 — Redis for Caching & Session Store

**Intent**: Move volatile in-memory state (quiz sessions, embedding cache) to Redis so the app can run multiple workers and survive restarts.

**Expected Outcomes**:
- Quiz sessions persisted in Redis with 24h TTL (not in-process dict)
- Repeated identical questions served from cache (no LLM re-call)
- FAISS global index backed by Redis for cross-worker consistency
- App can scale to multiple Uvicorn workers

**Todo List**:
1. Add `redis[asyncio]`, `aioredis` to `requirements.txt`
2. Add `REDIS_URL` to `backend/config.py` and `.env.example`
3. Create `backend/utils/cache.py` — async Redis client, `get_cached()`, `set_cached()` helpers
4. Replace `_quiz_store` dict in `backend/routers/quiz.py` with Redis `HSET/HGET quiz:{quiz_id}` calls
5. Add LLM response cache in `backend/services/llm_service.py` — hash(system_prompt + question) as key, 1h TTL
6. Remove `--workers 1` restriction from `Dockerfile` CMD (it was needed for in-process FAISS)
7. Update `render.yaml` to provision Redis add-on

**Relevant Context**:
- `backend/routers/quiz.py:40` — `_quiz_store` dict (the main migration target)
- `backend/services/document_service.py:51–55` — `_faiss_registry` and `_faiss_global` (thread-unsafe singletons)
- `backend/services/llm_service.py` — LLM call wrapper (add cache check before calling API)
- `backend/Dockerfile` — `CMD ["uvicorn", "main:app", "--workers", "1"]`

**Status**: [ ] pending

---

### Sub-task 1.3 — Structured Logging & Error Monitoring

**Intent**: Give the team full visibility into what's happening in production — errors, latency, usage patterns.

**Expected Outcomes**:
- Every API request logged with: user_id, endpoint, latency, status code, LLM tokens used
- Errors sent to Sentry with full context (user, request, stack trace)
- LLM latency tracked and alerted if >10 seconds
- No raw stack traces ever returned to the frontend

**Todo List**:
1. Add `python-json-logger`, `sentry-sdk[fastapi]` to `requirements.txt`
2. Create `backend/utils/logging.py` — structured JSON log formatter
3. Add `SENTRY_DSN` to `backend/config.py` and `.env.example`
4. Initialize Sentry in `backend/main.py` with `traces_sample_rate=0.1`
5. Add request timing middleware to `backend/main.py` — log `X-Response-Time` header
6. Add LLM call instrumentation to `backend/services/llm_service.py` — log model, tokens, latency
7. Replace all `raise HTTPException(status_code=500, detail=str(exc))` with user-safe messages + Sentry capture
8. Add `@sentry_sdk.trace` decorator to slow operations (embedding, indexing)
9. Install `@sentry/nextjs` in frontend and initialize in `next.config.js`
10. Create `backend/routers/health.py` — expand `/health` to include DB ping, Redis ping, ChromaDB status

**Relevant Context**:
- `backend/main.py` — middleware registration point
- `backend/routers/upload.py:100–104` — `HTTPException(500, str(exc))` raw error exposure
- `backend/services/llm_service.py` — all LLM calls go through here
- `frontend/next.config.js` — Sentry integration point

**Status**: [ ] pending

---

## Phase 2 — UX Polish (Before public launch)

### Sub-task 2.1 — Persistent Chat History

**Intent**: Save conversations to the DB so users can resume past chats and review previous answers across sessions and devices.

**Expected Outcomes**:
- Chat messages stored in DB per user per session
- "New Chat" creates a new session; past sessions listed in a sidebar
- Conversations persist across browser refreshes and devices
- Full conversation history (not just last 6 turns) passed to LLM with sliding window

**Todo List**:
1. Add `ChatSession` and `ChatMessage` tables to `backend/models/db_models.py`
2. Create `backend/routers/chat.py` — `GET /api/chats`, `POST /api/chats`, `GET /api/chats/{id}/messages`
3. Store each message in DB on send (both user and assistant messages)
4. Update `/api/ask` to accept `chat_session_id` and load full history from DB (with last-N-turn window)
5. Update `DoubtSolver.tsx` — load past messages from API on mount; save new messages via API
6. Add a "Chat History" drawer/sidebar in `DoubtSolver.tsx` listing past sessions by date
7. Add "New Chat" button that creates a new session

**Relevant Context**:
- `frontend/src/components/features/DoubtSolver.tsx:81` — `messages` state (replace with DB-backed)
- `backend/routers/ask.py:113–117` — conversation_history sliced to 6 turns
- `backend/models/schemas.py:34–37` — `conversation_history` field

**Status**: [ ] pending

---

### Sub-task 2.2 — Share Quiz / Document via Link

**Intent**: Let users share a quiz or document with a short link — recipient can take the quiz without uploading anything.

**Expected Outcomes**:
- "Share" button on quiz results and document cards generates a unique short link
- Recipient visits link → quiz loads pre-configured with the same questions
- Shared documents readable (not editable) by link recipients
- Links optionally expire after N days

**Todo List**:
1. Add `SharedResource` table to DB — columns: `id (nanoid)`, `type`, `payload (JSON)`, `expires_at`, `created_by`
2. Create `backend/routers/share.py` — `POST /api/share`, `GET /api/share/{id}` (public, no auth)
3. Store full quiz questions JSON in `payload` on share creation
4. Add "Share" button to quiz results screen in `QuizGame.tsx`
5. Add "Share" button to document cards in `FileUpload.tsx`
6. Create `frontend/src/app/share/[id]/page.tsx` — public page that loads and plays a shared quiz
7. Add copy-to-clipboard with toast on share URL generation

**Relevant Context**:
- `frontend/src/components/features/QuizGame.tsx:500–507` — results action buttons (add Share here)
- `frontend/src/components/features/FileUpload.tsx:152–180` — document card (add Share here)
- `backend/routers/quiz.py` — quiz generation and retrieval logic

**Status**: [ ] pending

---

### Sub-task 2.3 — Progress Dashboard Tab

**Intent**: Show students a visual overview of their study progress — quiz scores over time, weak topics, study streaks.

**Expected Outcomes**:
- New "Progress" tab in the main nav
- Line chart showing quiz scores over time
- Bar chart of strong vs weak topics across all quizzes
- Streak counter (consecutive study days)
- Recommended topics to review (from weak topics across all past quizzes)

**Todo List**:
1. Add `GET /api/progress/summary` endpoint — aggregate quiz history from DB per user
2. Add `recharts` or `chart.js` to frontend `package.json`
3. Create `frontend/src/components/features/ProgressDashboard.tsx`
4. Add "Progress" tab to `TABS` array in `frontend/src/app/page.tsx` with `BarChart2` icon
5. Compute and display: total quizzes, avg score, best streak, top 3 weak topics
6. Show last 10 quiz score history as a line chart

**Relevant Context**:
- `frontend/src/app/page.tsx:17–23` — TABS array (add new tab here)
- `frontend/src/hooks/useQuizHistory.ts` — localStorage history to migrate to API
- `backend/models/schemas.py` — add `ProgressSummaryResponse` schema

**Status**: [ ] pending

---

## Phase 3 — Growth Features (Post-launch)

### Sub-task 3.1 — Email Notifications & Study Reminders

**Intent**: Re-engage users with daily study reminders and achievement notifications via email.

**Expected Outcomes**:
- Users can set a daily study reminder time
- Email sent daily: "Time to study! Your revision plan says: [today's topic]"
- Achievement emails: "🔥 5-day streak!", "🏆 You scored 100% on your quiz!"
- Email verification on signup

**Todo List**:
1. Add `resend` (or `sendgrid`) to `requirements.txt`
2. Create `backend/services/email_service.py` — send transactional email helpers
3. Create `backend/routers/notifications.py` — `POST /api/notifications/preferences`
4. Add background task scheduler (`apscheduler`) to send daily reminder emails
5. Create email templates (HTML) for reminders and achievements
6. Add notification preferences UI in a new settings page

**Status**: [ ] pending

---

### Sub-task 3.2 — PWA + Offline Support

**Intent**: Make StudyBuddy installable on mobile and usable offline (reading notes, taking flashcard quizzes without internet).

**Expected Outcomes**:
- App installable on Android/iOS via "Add to Home Screen"
- Uploaded documents cached locally for offline reading
- Flashcard quizzes (no LLM needed) playable offline
- Service worker caches the app shell (JS, CSS, fonts)

**Todo List**:
1. Add `next-pwa` to frontend `package.json`
2. Configure service worker in `next.config.js` — cache app shell and API responses
3. Add `public/manifest.json` — app name, icons, theme color
4. Cache document chunks in IndexedDB using `idb` library for offline use
5. Build offline-only flashcard component from cached document content
6. Show "offline" banner using `navigator.onLine` listener

**Status**: [ ] pending

---

### Sub-task 3.3 — AI Cheat Sheet / Summary Generator

**Intent**: Let students generate a printable one-page cheat sheet from their uploaded document — the most-requested study tool.

**Expected Outcomes**:
- "Generate Cheat Sheet" button on uploaded document cards
- LLM produces: key definitions, formulas, concept summaries, exam tips
- Rendered as a formatted, printable A4 card
- Downloadable as PDF via browser print API

**Todo List**:
1. Create `backend/routers/cheatsheet.py` — `POST /api/cheatsheet` with `doc_id` input
2. Write a structured LLM prompt that extracts: definitions, formulas, key facts, exam tips
3. Return structured JSON with sections
4. Create `frontend/src/components/features/CheatSheet.tsx` — formatted printable layout
5. Add `window.print()` triggered by a "Download PDF" button
6. Add "Cheat Sheet" button to document cards in `FileUpload.tsx`

**Relevant Context**:
- `backend/services/document_service.py` — `retrieve_context()` to pull top-k chunks
- `backend/services/llm_service.py` — `chat_with_history()` for the LLM call
- `frontend/src/components/features/FileUpload.tsx` — add button to document cards

**Status**: [ ] pending

---

## Architecture: Current vs Target

```
CURRENT
─────────────────────────────────────────────────────────
Browser (Next.js)
   └─ sessionStorage / localStorage (ephemeral)
   └─► FastAPI (single worker)
            ├─ In-memory FAISS (resets on restart)
            ├─ In-memory quiz store dict (resets)
            ├─ ChromaDB on disk (persists)
            └─ Groq / OpenAI API

TARGET (Phase 0 + 1 Complete)
─────────────────────────────────────────────────────────
Browser (Next.js + NextAuth)
   └─ JWT token in httpOnly cookie
   └─► FastAPI (multi-worker via Gunicorn)
            ├─ PostgreSQL (users, docs, quizzes, chats)
            ├─ Redis (sessions, LLM cache, rate limits)
            ├─ ChromaDB (vector store, per-user)
            ├─ FAISS (in-process, re-built from ChromaDB)
            └─ Groq / OpenAI API (with streaming)
   Monitoring: Sentry + structured JSON logs
   Infra: Render / Railway (backend) + Vercel (frontend)
```

---

## Priority Summary

| Phase | Sub-task | Priority | Status |
|-------|----------|----------|--------|
| 0 | Authentication (JWT + NextAuth) | 🔴 Critical | [ ] pending |
| 0 | Persistent Database (PostgreSQL) | 🔴 Critical | [ ] pending |
| 0 | Rate Limiting & Security | 🔴 Critical | [ ] pending |
| 1 | Streaming LLM Responses | 🟠 High | [ ] pending |
| 1 | Redis for Cache & Sessions | 🟠 High | [ ] pending |
| 1 | Structured Logging & Sentry | 🟠 High | [ ] pending |
| 2 | Persistent Chat History | 🟡 Medium | [ ] pending |
| 2 | Share Quiz / Document via Link | 🟡 Medium | [ ] pending |
| 2 | Progress Dashboard | 🟡 Medium | [ ] pending |
| 3 | Email Notifications | 🟢 Low | [ ] pending |
| 3 | PWA + Offline Support | 🟢 Low | [ ] pending |
| 3 | AI Cheat Sheet Generator | 🟢 Low | [ ] pending |

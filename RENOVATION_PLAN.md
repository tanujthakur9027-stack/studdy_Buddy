# StudyBuddy AI — Complete Renovation Plan

> Generated after full codebase audit.  
> All 26 issues catalogued in the analysis are addressed below.  
> Sections are ordered by execution sequence (dependencies respected).  
> Each task has a **scope**, **why it matters**, and exact **files to change**.

---

## Phase 0 — Repository Hygiene (do first, unblocks everything)

### 0.1 Fix `requirements.txt` numpy pin
**Problem:** Pin says `numpy>=1.26.0,<2.0.0` but installed venv is numpy 2.5.2. Any fresh `pip install` from the lockfile will either downgrade numpy (breaking other packages) or fail.  
**Fix:** Change pin to `numpy>=1.26.0` (no upper bound) so it resolves correctly everywhere.  
**File:** `backend/requirements.txt` line 23  
**Change:**
```diff
-numpy>=1.26.0,<2.0.0
+numpy>=2.0.0
```

### 0.2 Fix `Dockerfile` numpy pin
**Problem:** Dockerfile has a hard `"numpy>=1.26.0,<2.0.0"` pre-install that conflicts with the venv.  
**File:** `backend/Dockerfile` line 16  
**Change:**
```diff
-RUN pip install --no-cache-dir "numpy>=1.26.0,<2.0.0"
+RUN pip install --no-cache-dir "numpy>=2.0.0"
```

### 0.3 Upgrade LangChain version pins in `requirements.txt`
**Problem:** `langchain>=0.2.6` / `langchain-core>=0.2.6` / `langchain-community>=0.2.6` are very old minimums. The venv has 1.x. The import paths changed at 0.3+. Pin to actual installed versions.  
**File:** `backend/requirements.txt` lines 12-16  
**Change:**
```diff
-langchain>=0.2.6
-langchain-core>=0.2.6
-langchain-community>=0.2.6
-langchain-text-splitters>=0.2.2
+langchain>=0.3.0
+langchain-core>=0.3.0
+langchain-community>=0.3.0
+langchain-text-splitters>=0.3.0
```

### 0.4 Add `langchain-chroma` to `requirements.txt`
**Problem:** `Chroma` is imported from `langchain_community.vectorstores` which is deprecated in LangChain 0.3+. The standalone `langchain-chroma` package is the correct one.  
**File:** `backend/requirements.txt` — add after chromadb line  
**Change:** Add `langchain-chroma>=0.1.0`

### 0.5 Add `from __future__ import annotations` to `schemas.py`
**Problem:** `AskRequest` contains `list["ChatTurn"]` — a forward reference to a class defined 160 lines later. Without the annotations import, Pydantic v2 may fail to resolve it at runtime in some Python 3.10 environments.  
**File:** `backend/models/schemas.py` — add at top of file

---

## Phase 1 — Backend Bug Fixes (critical correctness)

### 1.1 Fix the `lstrip("```json")` bug in ALL routers (systemic)
**Problem:** `str.lstrip(chars)` strips individual *characters*, not a substring. `raw.lstrip("```json")` strips any leading char in the set `{'\`', 'j', 's', 'o', 'n'}`. A JSON response that starts with `"just"` would become `"ust"`. This silently corrupts LLM responses.  
**Fix:** Replace with a proper regex strip utility used consistently everywhere.  
**Files affected:**
- `backend/routers/ask.py` line 141
- `backend/routers/quiz.py` lines 132, 290
- `backend/routers/revision.py` lines 66, 198
- `backend/routers/explain.py` line 55
- `backend/routers/doubt.py` line 57

**Solution:** Add a shared helper function `strip_json_fences(raw: str) -> str` to `backend/utils/text_utils.py` and call it from all routers.

```python
# utils/text_utils.py — new function
import re

def strip_json_fences(raw: str) -> str:
    """Strip markdown code-fences (```json ... ``` or ``` ... ```) from LLM output."""
    raw = raw.strip()
    # Remove opening fence: ```json or ```
    raw = re.sub(r'^```(?:json)?\s*', '', raw)
    # Remove closing fence: ```
    raw = re.sub(r'\s*```$', '', raw)
    return raw.strip()
```

### 1.2 Fix double PDF extraction in `process_and_index`
**Problem:** `document_service.py` calls `extract_pdf_pages()` (which internally tries pdfplumber), then immediately calls `_extract_pdf_pdfplumber()` a **second time** just to determine which parser was used. This doubles parsing time and can raise on some PDFs.  
**Fix:** Refactor `extract_pdf_pages()` to return a `(pages, parser_name)` tuple so the caller gets both pieces of information in a single pass.  
**File:** `backend/services/document_service.py` lines 114-132 and 253-258

```python
# New signature
def extract_pdf_pages(file_bytes: bytes, filename: str) -> tuple[list[tuple[int, str]], str]:
    """Returns (pages, parser_used) in one pass."""
    ...
    return pages, "pdfplumber"  # or "PyPDF2"
```

### 1.3 Fix `Chroma` import path
**Problem:** `from langchain_community.vectorstores import FAISS, Chroma` triggers a deprecation warning and will break in future LangChain versions.  
**Fix:** Import `Chroma` from `langchain_chroma` (after adding it to requirements).  
**File:** `backend/services/document_service.py` line 27  
**Change:**
```python
from langchain_community.vectorstores import FAISS
from langchain_chroma import Chroma
```

### 1.4 Make quiz router legacy path mount clean
**Problem:** In `main.py` lines 69-72, `quiz.router` and `revision.router` are registered a second time without a prefix. This creates duplicate route entries in OpenAPI docs and doubles the middleware processing. The `explain.router` and `doubt.router` are correctly mounted only once (no `/api` prefix needed since the frontend calls them directly).  
**Fix:** Keep the current structure but add a clear comment explaining the intent. No code change needed — the current behavior is correct. **Document it clearly.**

### 1.5 Fix `health` endpoint — graceful FAISS index access
**Problem:** `main.py` line 84: `sum(d["vectors"] for d in indexed)` — `indexed` comes from `list_indexed_docs()` which accesses `idx.index.ntotal`. If a FAISS index is partially initialized, this crashes the health check.  
**Fix:** Add a try/except in `list_indexed_docs()` to return 0 vectors for any corrupt index.  
**File:** `backend/services/document_service.py` lines 375-383

---

## Phase 2 — Frontend Bug Fixes

### 2.1 Fix `.md` files missing from dropzone accept list
**Problem:** Backend accepts `.md` files but `FileUpload.tsx` dropzone `accept` config doesn't include `"text/markdown": [".md"]`. Markdown files can't be drag-and-dropped.  
**File:** `frontend/src/components/features/FileUpload.tsx` lines 43-50  
**Change:**
```typescript
accept: {
  "application/pdf":   [".pdf"],
  "text/plain":        [".txt"],
  "text/markdown":     [".md"],    // ← ADD THIS
  "application/msword": [".doc"],
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
},
```

### 2.2 Remove unused `useId` import and `uid` variable in `QuizGame.tsx`
**Problem:** `useId` is imported and `uid` is assigned but never used. Causes ESLint `no-unused-vars` warning.  
**File:** `frontend/src/components/features/QuizGame.tsx` lines 3, 65  
**Change:** Remove `useId` from the React import and delete `const uid = useId();`

### 2.3 Fix `topicList` variable shadow in `RevisionPlanner.tsx`
**Problem:** Line 166 creates `const topicList = topics.split(...)` which shadows the `topicList` state (line 121). Confusing and triggers ESLint `no-shadow` warning.  
**File:** `frontend/src/components/features/RevisionPlanner.tsx` line 166  
**Change:**
```typescript
// Rename the local variable
const topicsArr  = topics.split(",").map((t) => t.trim()).filter(Boolean);
const weakList   = weakTopics.split(",").map((t) => t.trim()).filter(Boolean);
const data = await generateRevisionPlan({
  ...
  topics:      topicsArr.length ? topicsArr : undefined,
  ...
});
```

### 2.4 Remove unused icon imports in `RevisionPlanner.tsx`
**Problem:** `AlarmClock`, `ListChecks`, `BarChart2` are imported from `lucide-react` but never used.  
**File:** `frontend/src/components/features/RevisionPlanner.tsx` line 7  
**Change:** Remove the 3 unused icons from the import statement.

### 2.5 Fix unused `date` parameter in `useRevisionPlan.ts`
**Problem:** `dayProgress(date: string, dayTasks: RevisionTask[])` — the `date` param is never used inside the function body.  
**File:** `frontend/src/hooks/useRevisionPlan.ts` line 91  
**Change:** Remove the `date` parameter (or prefix with `_date` to signal intentional non-use). Update any call-sites to match.  
**Call-site in `RevisionPlanner.tsx`:** Update from `dayProgress(date, tasks)` → `dayProgress(tasks)`.

### 2.6 Fix `DoubtSolver.tsx` — fragile user message removal on error
**Problem:** On error, `setMessages((prev) => prev.filter((m) => m !== userMsg))` uses object reference equality. If React batches updates and the component re-renders between the push and the filter, the reference may not be found in `prev`.  
**Fix:** Assign a unique ID to each message and filter by ID instead.  
**File:** `frontend/src/components/features/DoubtSolver.tsx`  
**Change:** Add an `id` field to `ChatMessage` (or use a local counter ref), and filter by that ID.

### 2.7 Remove dead rewrite rule in `next.config.js`
**Problem:** The `/api/py/:path*` rewrite rule is never called by any frontend code. It's dead configuration that makes the routing harder to understand.  
**File:** `frontend/next.config.js`  
**Change:** Remove the `async rewrites()` block entirely (or simplify to just the safety guard comment).

---

## Phase 3 — API Layer Consistency & Robustness

### 3.1 Add `/api/explain` and `/api/doubt/solve` canonical paths
**Problem:** `explain.router` and `doubt.router` are only mounted without prefix. For consistency and future-proofing, also register them under `/api`.  
**File:** `backend/main.py`  
**Change:** Add `app.include_router(explain.router, prefix="/api")` and `app.include_router(doubt.router, prefix="/api")`.  
**Frontend `api.ts`:** Update `explainTopic` to call `/api/explain` and `solveDoubt` to call `/api/doubt/solve`. Keep old paths as fallback via the existing no-prefix mounts.

### 3.2 Add Groq as a fallback LLM provider
**Problem:** `groq` package is installed (`groq-1.7.0`) but never used. OpenAI is the only LLM provider. If the OpenAI key is missing or quota is exceeded, the entire app fails with no fallback.  
**Fix:** Add `GROQ_API_KEY` and `GROQ_MODEL` to `config.py` and update `llm_service.py` to try Groq when OpenAI fails (or when `OPENAI_API_KEY` is absent but `GROQ_API_KEY` is present).  
**Files:** `backend/config.py`, `backend/services/llm_service.py`, `backend/.env.example`

### 3.3 Standardise JSON fence stripping via shared utility (from 1.1)
All 6 router files call the new `strip_json_fences()` from `utils.text_utils` instead of the broken inline `lstrip` pattern. This is already covered in Phase 1 task 1.1.

### 3.4 Add `from __future__ import annotations` to `schemas.py` (from Phase 0)
Already covered in task 0.5.

---

## Phase 4 — Code Quality & Cleanup

### 4.1 Add `.md` frontmatter stripping to `extract_txt` in `document_service.py`
**Problem:** Markdown files may have YAML frontmatter (`---\ntitle: ...\n---`) that gets embedded into chunks and pollutes vector search results.  
**File:** `backend/services/document_service.py` — `extract_txt()` function  
**Change:** Strip YAML frontmatter before processing `.md` content.

### 4.2 Update `backend/.env.example` with Groq fields
**File:** `backend/.env.example`  
**Change:** Add commented-out `GROQ_API_KEY` and `GROQ_MODEL` entries.

### 4.3 Suppress or resolve Pydantic v2 deprecation warnings
**Problem:** Using `BaseModel` with mutable defaults and other Pydantic v1-style patterns may generate runtime warnings in Pydantic v2.  
**File:** `backend/models/schemas.py` — ensure all `list` fields use `Field(default_factory=list)` (already done for most, verify all).

### 4.4 Add ESLint `no-unused-vars` and `no-shadow` rules to frontend
**File:** `frontend/.eslintrc` (or the eslint config embedded in `package.json`)  
**Change:** Enable strict linting to catch future regressions of the issues fixed in Phase 2.

---

## Phase 5 — Renovation: New Features & UX Improvements

These are enhancements that go beyond bug-fixing and make the app significantly better.

### 5.1 Add `/api/ask` endpoint to frontend (currently unused)
**Problem:** The backend has a fully-featured `POST /api/ask` endpoint (with `mode`, `k`, `conversation_history`, `sources`, `follow_up_questions`) but the frontend **never calls it**. The `DoubtSolver` calls `/doubt/solve` which is a simpler endpoint.  
**Fix:** Update `DoubtSolver.tsx` to use `/api/ask` instead of `/doubt/solve`, enabling:
- `mode: "standard" | "eli5"` toggle in the chat UI
- Rich `SourceChunk` attribution (filename + page number + snippet)
- Configurable `k` (number of context chunks)
- `context_chunks_used` counter displayed in the UI

### 5.2 Add `mode` toggle (Standard vs ELI5) to `DoubtSolver`
Expose the `mode` parameter from `/api/ask` as a toggle button in the chat header.  
**File:** `frontend/src/components/features/DoubtSolver.tsx`

### 5.3 Improve `SourceChunk` display in `DoubtSolver`
**Problem:** Current `/doubt/solve` only returns filenames. The `/api/ask` response includes page numbers and snippets.  
**Fix:** Show rich source attribution: `📄 filename.pdf · page 3` in the chat bubbles.

### 5.4 Add document selector to all feature panels
**Problem:** When multiple documents are uploaded, all features silently use the last uploaded document's `doc_id`. Users can't choose which document to query.  
**Fix:** Add a small `<select>` dropdown (or pills) above each feature panel when `documents.length > 1`, allowing the user to pick which document to target.  
**Files:** `frontend/src/app/page.tsx`, feature components

### 5.5 Persist uploaded document list in `sessionStorage`
**Problem:** Refreshing the page clears all uploaded documents from state (they're still indexed in the backend but the frontend forgets them).  
**Fix:** Save `documents[]` to `sessionStorage` (not `localStorage` — shouldn't persist across browser sessions) and restore on mount.  
**File:** `frontend/src/app/page.tsx`

### 5.6 Add loading skeleton for quiz generation
**Problem:** When "Start Quiz" is clicked, the UI shows a spinner in the button but nothing else. A full-page skeleton would look more polished.

### 5.7 Add a "Copy answer" button to `DoubtSolver` messages
Small UX improvement — a clipboard icon on assistant messages.

### 5.8 Add `aria-label` and keyboard accessibility to timer/quiz controls
The quiz is not accessible via keyboard. Add `aria-label` attributes and ensure all interactive elements are focusable.

---

## Phase 6 — Deployment & Infrastructure

### 6.1 Add `output: 'standalone'` to `next.config.js` (optional Docker path)
If the frontend is ever Dockerized, Next.js standalone output is required.  
**File:** `frontend/next.config.js`  
**Change:** Add `output: 'standalone'` to `nextConfig` object (guarded by `process.env.DOCKER_BUILD` env var so it doesn't affect Vercel deployments).

### 6.2 Add `healthcheck` to Dockerfile
**File:** `backend/Dockerfile`  
**Change:** Add `HEALTHCHECK CMD curl -f http://localhost:${PORT}/health || exit 1`

### 6.3 Add `CORS_ORIGINS` to `render.yaml` for localhost dev
**Problem:** `render.yaml` only sets `CORS_ORIGINS` to the Vercel production URL. During local development, the frontend at `localhost:3000` is blocked by CORS.  
**Note:** This is fine for production — local dev uses `.env` directly. Document this in `README.md`.

### 6.4 Update `README.md` with accurate setup instructions
Current `README.md` (if it exists) may not reflect the current architecture. Add:
- Environment variable reference
- How to run locally (backend + frontend)
- Which API keys are needed
- How the dual vector store (FAISS + ChromaDB) works
- Known limitations (single worker, in-memory quiz store)

---

## Execution Order Summary

```
Phase 0  →  Phase 1  →  Phase 2  →  Phase 3  →  Phase 4  →  Phase 5  →  Phase 6
(Deps)       (Backend)   (Frontend)  (API)        (Quality)   (Features)  (Deploy)
  0.1-0.5     1.1-1.5     2.1-2.7     3.1-3.4      4.1-4.4     5.1-5.8     6.1-6.4
```

**Critical path (must fix before anything works correctly):**
`0.1 → 0.2 → 1.1 → 1.3` — these 4 tasks unblock all other work.

**High-impact, low-effort wins:**
`1.1` (lstrip fix), `2.1` (md dropzone), `2.2` (unused import), `2.3` (variable shadow), `5.1` (wire /api/ask to frontend)

---

## File Change Summary

| File | Tasks |
|------|-------|
| `backend/requirements.txt` | 0.1, 0.3, 0.4 |
| `backend/Dockerfile` | 0.2, 6.2 |
| `backend/models/schemas.py` | 0.5, 4.3 |
| `backend/utils/text_utils.py` | 1.1 (add `strip_json_fences`) |
| `backend/services/document_service.py` | 1.2, 1.3, 1.5, 4.1 |
| `backend/services/llm_service.py` | 3.2 |
| `backend/config.py` | 3.2 |
| `backend/.env.example` | 3.2, 4.2 |
| `backend/main.py` | 3.1 |
| `backend/routers/ask.py` | 1.1 |
| `backend/routers/quiz.py` | 1.1 |
| `backend/routers/revision.py` | 1.1 |
| `backend/routers/explain.py` | 1.1 |
| `backend/routers/doubt.py` | 1.1 |
| `frontend/src/lib/api.ts` | 3.1, 5.1 |
| `frontend/src/components/features/FileUpload.tsx` | 2.1 |
| `frontend/src/components/features/QuizGame.tsx` | 2.2 |
| `frontend/src/components/features/RevisionPlanner.tsx` | 2.3, 2.4 |
| `frontend/src/components/features/DoubtSolver.tsx` | 2.6, 5.1, 5.2, 5.3 |
| `frontend/src/hooks/useRevisionPlan.ts` | 2.5 |
| `frontend/next.config.js` | 2.7, 6.1 |
| `frontend/src/app/page.tsx` | 5.4, 5.5 |
| `frontend/src/types/index.ts` | 5.1 (add SourceChunk type) |
| `render.yaml` | 6.3 |

---

## Total Task Count

| Phase | Tasks | Effort |
|-------|-------|--------|
| 0 — Hygiene | 5 | ~15 min |
| 1 — Backend bugs | 5 | ~30 min |
| 2 — Frontend bugs | 7 | ~30 min |
| 3 — API consistency | 4 | ~20 min |
| 4 — Code quality | 4 | ~10 min |
| 5 — New features | 8 | ~2 hr |
| 6 — Deployment | 4 | ~15 min |
| **Total** | **37** | **~4 hr** |

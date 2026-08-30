# StudyBuddy AI — New Features Plan

## Overview

Add 4 new study features to the existing StudyBuddy AI app:

1. **Feynman Mode** — a new standalone tab where the student types an explanation of a concept in their own words, the AI grades it, identifies gaps, generates Q&A from it, and coaches them to fill the gaps.
2. **Concept Map** — AI generates a static SVG/HTML visual concept map (nodes + edges) from the uploaded document.
3. **Flashcards** — AI generates a flip-card deck from the uploaded notes; student flips each card and self-marks "Know it" / "Review it".
4. **Enhanced Progress Dashboard** — extend the existing `ProgressDashboard.tsx` with a daily activity heatmap (GitHub-style), flashcard progress stats, and a more detailed performance graph.

All four features follow the existing patterns:
- Backend: new FastAPI router → registered in `main.py`
- Streaming: SSE via `streamPost()` from `streamApi.ts` where the response is long
- Frontend: new React component → new tab entry in `page.tsx` `TABS` array
- DB: new ORM table(s) in `db_models.py` where persistence is needed
- TypeScript check must pass (`npx tsc --noEmit`) before every commit

---

## Sub-task 1 — Feynman Mode

### Intent
Give students a "teach it back" loop: the most effective learning technique. Student types their explanation of a concept → AI scores it on accuracy, completeness, clarity → identifies knowledge gaps → auto-generates 3–5 Q&A pairs from the explanation → suggests what to read next.

### Expected Outcomes
- New `POST /api/feynman/evaluate` endpoint accepts `{ concept, explanation, doc_id? }` and returns JSON: `{ score (0-100), grade, strengths[], gaps[], qa_pairs[{q,a}], coaching_tip }`
- New `feynman` tab in the sidebar
- Student can type freely; AI grades in real-time (non-streaming — needs full JSON)
- Q&A pairs are shown as expandable accordion items
- Gaps shown as a red checklist
- "Try Again" clears input and re-attempts

### Todo List
1. Create `backend/routers/feynman.py` — `POST /api/feynman/evaluate` with rate limit 10/min
2. Write LLM prompt that asks the model to return structured JSON: `score`, `grade`, `strengths`, `gaps`, `qa_pairs`, `coaching_tip`
3. Register `feynman_router` in `backend/main.py`
4. Add `FeynmanRequest` + `FeynmanResponse` Pydantic schemas to `backend/models/schemas.py`
5. Add `evaluateFeynman(params)` API helper to `frontend/src/lib/api.ts`
6. Create `frontend/src/components/features/FeynmanMode.tsx`
   - Textarea for student explanation
   - Concept name input (optional — defaults to "this topic")
   - Submit button → loading → result panel
   - Score ring / grade badge
   - Strengths (green checkmarks) + Gaps (red X marks)
   - Q&A accordion (click question → answer reveals)
   - Coaching tip card
   - "Try Again" button
7. Add `feynman` to `AppTab` union in `frontend/src/types/index.ts`
8. Add Feynman tab to `TABS` array in `frontend/src/app/page.tsx` (icon: `Brain`, color: `text-pink-400`)
9. Render `<FeynmanMode docId={activeDocId} />` in the tab switch in `page.tsx`

### Relevant Context
- `backend/routers/explain.py` — same pattern (non-streaming single LLM call → JSON response)
- `backend/services/llm_service.py` — `chat()` for non-streaming, structured JSON response
- `backend/utils/text_utils.py` — `strip_json_fences()` for cleaning LLM output
- `frontend/src/components/features/ExplainModule.tsx` — UI pattern for single-turn AI call
- `frontend/src/types/index.ts:33` — `AppTab` union to extend
- `frontend/src/app/page.tsx:18` — `TABS` array to extend

### Status
[ ] pending

---

## Sub-task 2 — Concept Map

### Intent
Turn uploaded notes into a visual concept map — nodes (key concepts) connected by labelled edges (relationships). Rendered as an SVG/HTML diagram. Helps students see how concepts relate to each other at a glance.

### Expected Outcomes
- New `POST /api/concept-map` endpoint returns JSON: `{ nodes: [{id, label, type}], edges: [{from, to, label}] }`
- New button `Generate Concept Map` on the Upload tab document cards (alongside existing Cheat Sheet button)
- Opens a full-screen modal with the rendered SVG graph
- Topics shown as coloured circles/rectangles; edges as labelled arrows
- "Download SVG" button exports the diagram

### Todo List
1. Create `backend/routers/concept_map.py` — `POST /api/concept-map` accepting `{ doc_id, topic? }`
2. Write LLM prompt that extracts 8–15 key concepts and their relationships, returning strict JSON: `{ nodes: [{id, label, type: "main"|"sub"|"detail"}], edges: [{from, to, label}] }`
3. Register `concept_map_router` in `backend/main.py`
4. Add `ConceptMapRequest` + `ConceptMapResponse` Pydantic schemas to `backend/models/schemas.py`
5. Add `generateConceptMap(params)` API helper to `frontend/src/lib/api.ts`; add `ConceptNode` + `ConceptEdge` TypeScript interfaces
6. Create `frontend/src/components/features/ConceptMap.tsx`
   - Accept `nodes[]` + `edges[]` as props
   - Use a simple force-layout algorithm (pure JS — no library needed) to position nodes in a circle/radial layout
   - Render as SVG: nodes as coloured `<rect>`/`<circle>`, edges as `<line>` with `<text>` labels
   - "Download SVG" button
   - Loading state while generating
7. Create `frontend/src/components/features/ConceptMapModal.tsx`
   - Full-screen modal overlay (same pattern as `CheatSheet.tsx`)
   - Calls `generateConceptMap`, shows spinner, then renders `<ConceptMap />`
   - Topic filter input + Regenerate button
8. Add ✨ Concept Map button to each document card in `frontend/src/components/features/FileUpload.tsx` (alongside existing Cheat Sheet sparkle button)
9. Add `conceptMapDoc` state + `AnimatePresence` render for `ConceptMapModal` in `FileUpload.tsx`

### Relevant Context
- `backend/routers/cheatsheet.py` — same pattern (retrieve context → single LLM call → return structured data)
- `frontend/src/components/features/CheatSheet.tsx` — modal pattern to replicate
- `frontend/src/components/features/FileUpload.tsx:37–43` — existing button pattern on document cards
- `backend/services/document_service.py` — `retrieve_context()` for pulling document chunks

### Status
[ ] pending

---

## Sub-task 3 — Flashcards

### Intent
AI generates a deck of flip-cards from the uploaded document. Each card has a front (question/term) and back (answer/definition). Student flips through them and self-marks each as "Know it ✓" or "Review it ↩". Cards marked "Review it" go back into the deck.

### Expected Outcomes
- New `POST /api/flashcards/generate` endpoint returns `{ doc_id, cards: [{id, front, back, topic_tag}] }`
- New `FlashcardSession` ORM table persists generated decks (so they survive page reload)
- New `flashcards` tab in the sidebar
- Flip animation (CSS 3D transform) on click
- Progress bar showing cards remaining
- "Know it" (green) + "Review it" (orange) buttons
- Session summary screen at deck end: total reviewed, known, still-to-review
- "Restart Deck" resets all cards

### Todo List
1. Add `FlashcardSession` + `Flashcard` ORM tables to `backend/models/db_models.py`
   - `FlashcardSession`: id, doc_id (FK documents), topic, created_at
   - `Flashcard`: id, session_id (FK), front, back, topic_tag
2. Create `backend/routers/flashcards.py`:
   - `POST /api/flashcards/generate` — calls LLM with document context, stores cards in DB, returns deck
   - `GET /api/flashcards/{session_id}` — fetch an existing deck
   - `GET /api/flashcards` — list all sessions for a doc
3. Write LLM prompt that generates 10–20 flashcards as JSON: `[{front, back, topic_tag}]`
4. Register `flashcards_router` in `backend/main.py`
5. Add Pydantic schemas: `FlashcardGenerateRequest`, `FlashcardOut`, `FlashcardSessionOut` to `backend/models/schemas.py`
6. Add API helpers to `frontend/src/lib/api.ts`: `generateFlashcards()`, `fetchFlashcardSession()`, `listFlashcardSessions()`
7. Add `FlashcardItem` TypeScript interface to `frontend/src/types/index.ts`
8. Create `frontend/src/components/features/Flashcards.tsx`:
   - Generate button → loading → deck view
   - Single card shown at a time; CSS 3D flip on click reveals back
   - Progress bar (cards remaining / total)
   - "Know it ✓" (green) / "Review it ↩" (orange) buttons below card
   - Cards marked "Review it" re-appended to queue
   - Summary screen when queue empty
   - History sidebar listing past decks (by doc + date)
9. Add `flashcards` to `AppTab` union in `frontend/src/types/index.ts`
10. Add Flashcards tab to `TABS` array in `frontend/src/app/page.tsx` (icon: `Layers`, color: `text-amber-400`)
11. Render `<Flashcards docId={activeDocId} />` in the tab switch

### Relevant Context
- `backend/routers/quiz.py` — same pattern: generate → persist session → return data
- `backend/models/db_models.py` — existing ORM table patterns (QuizSession, QuizResult)
- `frontend/src/components/features/QuizGame.tsx` — game loop pattern (phase state machine)
- `frontend/src/lib/streamApi.ts` — NOT needed here (non-streaming, full JSON)

### Status
[ ] pending

---

## Sub-task 4 — Enhanced Progress Dashboard

### Intent
Extend the existing `ProgressDashboard.tsx` (which shows quiz stats) with:
1. A **GitHub-style daily activity heatmap** — one square per day, coloured by study activity (quizzes taken that day)
2. **Flashcard progress stats** — total cards reviewed, know/review ratio
3. A **Feynman score history** line — track how scores improve over attempts
4. Enhanced weak-topic section showing both quiz weakness AND Feynman gap frequency

### Expected Outcomes
- `GET /api/progress/summary` returns additional fields: `daily_activity` (array of `{date, count}` for last 90 days), `flashcard_stats` (`{total_reviewed, known_pct}`), `feynman_history` (array of `{date, score, concept}`)
- `ProgressDashboard.tsx` renders a heatmap grid below the bar chart
- Flashcard stats shown as a new stat card row
- Feynman score trend shown as a small sparkline graph

### Todo List
1. Update `backend/routers/progress.py` — extend `get_progress_summary()` to also query:
   - Daily quiz activity (last 90 days) from `QuizResult`
   - Flashcard session stats from `FlashcardSession` + `Flashcard` tables (after Sub-task 3)
   - Feynman evaluation history from a new `FeynmanResult` table (after Sub-task 1)
2. Add `FeynmanResult` ORM table to `backend/models/db_models.py`: id, concept, score, grade, gap_count, created_at
3. Update `backend/routers/feynman.py` (from Sub-task 1) to persist each evaluation in `FeynmanResult`
4. Update `ProgressSummary` Pydantic schema and TypeScript interface to include new fields
5. Create `DailyHeatmap` sub-component inside `ProgressDashboard.tsx`:
   - 13-week × 7-day grid of squares
   - Colour scale: gray (0) → light green (1–2) → green (3–4) → dark green (5+)
   - Tooltip on hover showing date + count
6. Add Flashcard stats row in `ProgressDashboard.tsx` (only shown if flashcard data exists)
7. Add Feynman score sparkline in `ProgressDashboard.tsx` (only shown if Feynman history exists)

### Relevant Context
- `backend/routers/progress.py` — existing progress endpoint to extend
- `frontend/src/components/features/ProgressDashboard.tsx` — existing component to extend
- `frontend/src/lib/api.ts` — `ProgressSummary` interface + `fetchProgressSummary()` to update
- **Depends on Sub-task 1 (FeynmanResult table) and Sub-task 3 (FlashcardSession table)**

### Status
[ ] pending

---

## Implementation Order

```
Sub-task 1 (Feynman)    → self-contained, no dependencies
Sub-task 2 (Concept Map) → self-contained, no dependencies
Sub-task 3 (Flashcards)  → self-contained, no dependencies
Sub-task 4 (Progress)    → depends on Sub-tasks 1 + 3 (new DB tables)
```

Sub-tasks 1, 2, 3 can be built in any order or in parallel.
Sub-task 4 must be done after 1 and 3 are complete.

---

## Files Changed Per Sub-task

### Sub-task 1 — Feynman
- `backend/routers/feynman.py` (NEW)
- `backend/models/schemas.py` (add schemas)
- `backend/models/db_models.py` (add FeynmanResult table)
- `backend/main.py` (register router)
- `frontend/src/lib/api.ts` (add evaluateFeynman)
- `frontend/src/types/index.ts` (extend AppTab)
- `frontend/src/components/features/FeynmanMode.tsx` (NEW)
- `frontend/src/app/page.tsx` (add tab + render)

### Sub-task 2 — Concept Map
- `backend/routers/concept_map.py` (NEW)
- `backend/models/schemas.py` (add schemas)
- `backend/main.py` (register router)
- `frontend/src/lib/api.ts` (add generateConceptMap)
- `frontend/src/components/features/ConceptMap.tsx` (NEW)
- `frontend/src/components/features/ConceptMapModal.tsx` (NEW)
- `frontend/src/components/features/FileUpload.tsx` (add button + modal)

### Sub-task 3 — Flashcards
- `backend/routers/flashcards.py` (NEW)
- `backend/models/schemas.py` (add schemas)
- `backend/models/db_models.py` (add FlashcardSession + Flashcard tables)
- `backend/main.py` (register router)
- `frontend/src/lib/api.ts` (add flashcard helpers)
- `frontend/src/types/index.ts` (add FlashcardItem, extend AppTab)
- `frontend/src/components/features/Flashcards.tsx` (NEW)
- `frontend/src/app/page.tsx` (add tab + render)

### Sub-task 4 — Progress Enhancement
- `backend/routers/progress.py` (extend endpoint)
- `backend/models/db_models.py` (already updated in 1 + 3)
- `frontend/src/lib/api.ts` (update ProgressSummary interface)
- `frontend/src/components/features/ProgressDashboard.tsx` (add heatmap, flashcard stats, feynman sparkline)

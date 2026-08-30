"""
StudyBuddy — Streamlit App (self-contained, no Render needed)
=============================================================
This file does two things:
  1. Launches the FastAPI backend (uvicorn) as a subprocess on localhost:8000
     the first time a Streamlit worker starts. All subsequent reruns reuse it.
  2. Renders the full 9-tab study UI, talking to the backend over loopback.

Deploy to Streamlit Cloud:
  - Repo root entry point : streamlit_app/app.py
  - Secrets (App Settings → Secrets):
        GROQ_API_KEY = "gsk_..."
  - That's it. No Render, no CORS, no environment variables to wire up.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
import random
import logging
from pathlib import Path

import requests
import streamlit as st

logger = logging.getLogger(__name__)

# ── Paths ─────────────────────────────────────────────────────────────────────
# Repo root is two levels up from streamlit_app/app.py
_HERE       = Path(__file__).parent          # …/streamlit_app/
_REPO_ROOT  = _HERE.parent                   # …/Studdy_Buddy/
_BACKEND    = _REPO_ROOT / "backend"         # …/backend/
_DATA       = _REPO_ROOT / "data"            # …/data/  (created at runtime)

BACKEND_URL = "http://localhost:8000"

# ── Timeouts ──────────────────────────────────────────────────────────────────
TIMEOUT_SHORT = 60
TIMEOUT_LONG  = 180


# ─────────────────────────────────────────────────────────────────────────────
# Sub-process launcher — starts uvicorn once per Streamlit worker lifecycle
# ─────────────────────────────────────────────────────────────────────────────
def _start_backend() -> None:
    """
    Launch the FastAPI backend as a background subprocess (non-blocking).
    Guarded by st.session_state so it only happens once per worker, not on
    every Streamlit rerun.
    """
    if st.session_state.get("_backend_started"):
        return  # already running

    # Create data directories (SQLite, ChromaDB, uploads all live here)
    _DATA.mkdir(parents=True, exist_ok=True)
    (_DATA / "chroma_db").mkdir(exist_ok=True)
    (_DATA / "uploads").mkdir(exist_ok=True)
    (_DATA / "faiss_indexes").mkdir(exist_ok=True)

    # Pull GROQ_API_KEY from Streamlit secrets (set in App Settings → Secrets)
    groq_key = ""
    try:
        groq_key = st.secrets.get("GROQ_API_KEY", "")
    except Exception:
        pass
    # Also honour a plain env var (useful for local dev)
    groq_key = groq_key or os.environ.get("GROQ_API_KEY", "")

    env = {
        **os.environ,
        # LLM
        "GROQ_API_KEY":        groq_key,
        "GROQ_MODEL":          os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b"),
        # Override any OpenAI key from secrets too
        "OPENAI_API_KEY":      os.environ.get("OPENAI_API_KEY",
                                    st.secrets.get("OPENAI_API_KEY", "") if hasattr(st, "secrets") else ""),
        # Storage — all paths relative to backend/ cwd, pointing to ../data/
        "DATABASE_URL":        f"sqlite+aiosqlite:///{_DATA}/studybuddy.db",
        "CHROMA_PERSIST_DIR":  str(_DATA / "chroma_db"),
        "UPLOAD_DIR":          str(_DATA / "uploads"),
        "FAISS_INDEX_DIR":     str(_DATA / "faiss_indexes"),
        # Upload limit
        "MAX_FILE_SIZE_MB":    "200",
        # CORS — allow everything (loopback calls, no browser security boundary)
        "CORS_ORIGINS":        "*",
        # Rate limiting — more generous inside the single-process bundle
        "RATE_LIMIT_PER_MINUTE": "60",
        # Python path so backend imports resolve correctly
        "PYTHONPATH":          str(_BACKEND),
    }

    proc = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn",
            "main:app",
            "--host", "127.0.0.1",
            "--port", "8000",
            "--workers", "1",
            "--log-level", "warning",
        ],
        cwd=str(_BACKEND),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    st.session_state["_backend_proc"]    = proc
    st.session_state["_backend_started"] = True


def _wait_for_backend(timeout: int = 60) -> bool:
    """Poll /health until backend is ready. Returns True on success."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(f"{BACKEND_URL}/health", timeout=3)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def _ensure_backend() -> bool:
    """
    Start backend if not yet running, then wait for it to be healthy.
    Shows a spinner while waiting. Returns True if backend is ready.
    """
    _start_backend()

    # If it was already running, do a quick health check
    if st.session_state.get("_backend_healthy"):
        try:
            r = requests.get(f"{BACKEND_URL}/health", timeout=3)
            if r.status_code == 200:
                return True
        except Exception:
            # Backend died — allow restart on next rerun
            st.session_state.pop("_backend_healthy", None)
            st.session_state.pop("_backend_started", None)
            st.session_state.pop("_backend_proc", None)
            return False

    with st.spinner("⏳ Starting backend… (first load takes ~20 s to warm up the embedding model)"):
        ready = _wait_for_backend(timeout=90)

    if ready:
        st.session_state["_backend_healthy"] = True
    else:
        st.error(
            "❌ Backend failed to start within 90 seconds. "
            "Check that all dependencies are installed and GROQ_API_KEY is set."
        )
    return ready


# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="StudyBuddy AI",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
  .block-container { max-width: 960px; padding-top: 1.5rem; }
  .streamlit-expanderHeader { font-weight: 600; }
  .source-chip {
      display: inline-block; background: #1e293b; border: 1px solid #334155;
      border-radius: 6px; padding: 2px 8px; font-size: 12px; color: #94a3b8; margin: 2px;
  }
</style>
""", unsafe_allow_html=True)


# ── API helpers ───────────────────────────────────────────────────────────────
def _api(method: str, path: str, timeout: int = TIMEOUT_LONG, **kwargs):
    url = f"{BACKEND_URL}{path}"
    try:
        resp = requests.request(method, url, timeout=timeout, **kwargs)
        if resp.status_code == 200:
            return resp.json(), None
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        return None, f"HTTP {resp.status_code}: {detail}"
    except requests.exceptions.ConnectionError:
        return None, "Backend not reachable. Try refreshing the page."
    except requests.exceptions.Timeout:
        return None, "Request timed out — the LLM is taking too long. Try again."
    except Exception as exc:
        return None, str(exc)


def _get(path: str, timeout: int = TIMEOUT_SHORT, **kwargs):
    return _api("GET",  path, timeout=timeout, **kwargs)


def _post(path: str, timeout: int = TIMEOUT_LONG, **kwargs):
    return _api("POST", path, timeout=timeout, **kwargs)


# ── Session-state helper ──────────────────────────────────────────────────────
def _ss(key, default):
    if key not in st.session_state:
        st.session_state[key] = default
    return st.session_state[key]


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────
def _load_documents():
    if "documents_loaded" not in st.session_state:
        data, err = _get("/api/documents", timeout=15)
        if err:
            st.session_state["documents"] = []
        else:
            st.session_state["documents"] = data or []
        st.session_state["documents_loaded"] = True


def _active_doc_id() -> str | None:
    doc = st.session_state.get("active_doc")
    return doc["doc_id"] if doc else None


def _invalidate_docs():
    for k in ("documents_loaded", "documents", "active_doc"):
        st.session_state.pop(k, None)


def sidebar():
    with st.sidebar:
        st.markdown("## 🎓 StudyBuddy AI")
        st.caption("All-in-one AI study assistant")
        st.divider()

        # Backend health check widget
        with st.expander("🔌 Backend Status", expanded=False):
            if st.button("Check health", key="health_btn"):
                data, err = _get("/health", timeout=10)
                if err:
                    st.error(err)
                else:
                    icon = "✅" if data.get("status") == "ok" else "⚠️"
                    st.write(f"{icon} **{data.get('status','?').upper()}**")
                    st.write(f"Provider : `{data.get('provider','?')}`")
                    st.write(f"Model    : `{data.get('model','?')}`")
                    st.write(f"Docs     : `{data.get('indexed_documents',0)}`")
                    st.write(f"Vectors  : `{data.get('faiss_vectors',0)}`")

        st.divider()
        st.markdown("### 📄 Active Document")
        _load_documents()

        docs: list[dict] = st.session_state.get("documents", [])
        if not docs:
            st.caption("No documents yet — upload one in the Upload tab.")
        else:
            names = [d["filename"] for d in docs]
            idx   = st.selectbox(
                "Select document",
                range(len(names)),
                format_func=lambda i: names[i],
                key="active_doc_idx",
            )
            st.session_state["active_doc"] = docs[idx]
            active = docs[idx]
            st.caption(
                f"Chunks: {active.get('chunks','?')} · "
                f"Pages: {active.get('pages','?')} · "
                f"Parser: {active.get('parser_used','?')}"
            )

        st.divider()
        st.caption("Running on **Streamlit Cloud** · Backend on **localhost:8000**")


# ─────────────────────────────────────────────────────────────────────────────
# TAB: Upload
# ─────────────────────────────────────────────────────────────────────────────
def tab_upload():
    st.subheader("📤 Upload Documents")
    st.caption("Upload your syllabus, notes, or any study material. Up to **200 MB** per file.")

    uploaded = st.file_uploader(
        "Choose file(s)",
        type=["pdf","txt","md","doc","docx","ppt","pptx","xls","xlsx",
              "png","jpg","jpeg","webp","bin"],
        accept_multiple_files=True,
        help="PDF · TXT · MD · DOCX · PPT · PPTX · XLSX · PNG · JPG · WEBP — max 200 MB",
    )

    if uploaded and st.button("⬆️ Upload & Index", type="primary"):
        for f in uploaded:
            with st.spinner(f"Uploading **{f.name}** …"):
                data, err = _api(
                    "POST", "/api/upload", timeout=300,
                    files={"file": (f.name, f.getvalue(), f.type or "application/octet-stream")},
                )
            if err:
                st.error(f"❌ {f.name}: {err}")
            else:
                st.success(
                    f"✅ **{data['filename']}** — "
                    f"{data['chunks']} chunks · {data['pages']} pages · "
                    f"`{data['parser_used']}`"
                )
                if data.get("description"):
                    st.info(f"📝 {data['description']}")
        _invalidate_docs()
        st.rerun()

    st.divider()
    st.markdown("### 📚 Indexed Documents")
    _load_documents()
    docs: list[dict] = st.session_state.get("documents", [])

    if not docs:
        st.info("No documents yet. Upload one above ↑")
        return

    for doc in docs:
        col1, col2 = st.columns([5, 1])
        with col1:
            with st.expander(f"📄 {doc['filename']}", expanded=False):
                if doc.get("description"):
                    st.write(doc["description"])
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Chunks",  doc.get("chunks", "?"))
                c2.metric("Pages",   doc.get("pages",  "?"))
                c3.metric("Tokens",  doc.get("total_tokens", "?"))
                c4.metric("Parser",  doc.get("parser_used", "?"))
        with col2:
            if st.button("🗑️", key=f"del_{doc['doc_id']}", help="Delete document"):
                _, err = _api("DELETE", f"/api/documents/{doc['doc_id']}", timeout=15)
                if err:
                    st.error(err)
                else:
                    st.success(f"Deleted {doc['filename']}")
                    _invalidate_docs()
                    st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# TAB: ELI10 Explain
# ─────────────────────────────────────────────────────────────────────────────
def tab_explain():
    st.subheader("💡 ELI10 — Explain Like I'm 10")
    st.caption("Simplified, analogy-driven explanations of any concept.")

    topic = st.text_input("Topic / concept",
                          placeholder="e.g. Photosynthesis, Newton's Laws, Supply & Demand")
    level = st.selectbox("Depth", ["eli5", "beginner", "intermediate"],
                         index=1,
                         format_func=lambda x: {
                             "eli5": "🧒 Very Simple (ELI5)",
                             "beginner": "📖 Beginner",
                             "intermediate": "🎓 Intermediate",
                         }[x])

    if st.button("✨ Explain", type="primary") and topic.strip():
        with st.spinner("Generating explanation …"):
            data, err = _post("/api/explain", json={
                "topic":  topic.strip(),
                "doc_id": _active_doc_id(),
                "level":  level,
            })
        if err:
            st.error(err)
        else:
            st.markdown("#### 📖 Explanation")
            st.write(data["explanation"])
            if data.get("analogy"):
                st.info(f"🎭 **Analogy:** {data['analogy']}")
            if data.get("key_points"):
                st.markdown("#### 🔑 Key Points")
                for pt in data["key_points"]:
                    st.markdown(f"- {pt}")


# ─────────────────────────────────────────────────────────────────────────────
# TAB: Ask AI (RAG Q&A)
# ─────────────────────────────────────────────────────────────────────────────
def tab_ask():
    st.subheader("🤖 Ask AI — RAG Q&A")
    st.caption("Ask anything about your uploaded document. Answers include source citations.")

    _ss("ask_history", [])

    mode = st.radio("Answer mode", ["standard", "eli5"], horizontal=True,
                    format_func=lambda x: "📚 Standard" if x == "standard" else "🧒 ELI5")

    for msg in st.session_state["ask_history"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("sources"):
                with st.expander("📎 Sources", expanded=False):
                    for src in msg["sources"]:
                        st.markdown(
                            f'<span class="source-chip">📄 {src["filename"]} p.{src["page"]}</span>'
                            f' {src.get("snippet","")[:120]}…',
                            unsafe_allow_html=True,
                        )
            if msg.get("follow_ups"):
                st.caption("💬 Suggested follow-ups:")
                for fq in msg["follow_ups"]:
                    if st.button(fq, key=f"fq_{hash(fq)}"):
                        st.session_state["_ask_prefill"] = fq
                        st.rerun()

    question = st.chat_input("Ask a question …")
    if st.session_state.get("_ask_prefill"):
        question = st.session_state.pop("_ask_prefill")

    if question:
        st.session_state["ask_history"].append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            with st.spinner("Thinking …"):
                history = [
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state["ask_history"][:-1]
                ]
                data, err = _post("/api/ask", json={
                    "question": question,
                    "doc_id":   _active_doc_id(),
                    "mode":     mode,
                    "k":        5,
                    "conversation_history": history[-6:],
                })
            if err:
                st.error(err)
                st.session_state["ask_history"].pop()
            else:
                answer     = data["answer"]
                sources    = data.get("sources", [])
                follow_ups = data.get("follow_up_questions", [])
                st.markdown(answer)
                if sources:
                    with st.expander("📎 Sources", expanded=False):
                        for src in sources:
                            st.markdown(
                                f'<span class="source-chip">📄 {src["filename"]} p.{src["page"]}</span>'
                                f' {src.get("snippet","")[:120]}…',
                                unsafe_allow_html=True,
                            )
                if follow_ups:
                    st.caption("💬 Suggested follow-ups:")
                    cols = st.columns(min(len(follow_ups), 3))
                    for i, fq in enumerate(follow_ups[:3]):
                        with cols[i]:
                            if st.button(fq, key=f"afq_{i}_{hash(fq)}"):
                                st.session_state["_ask_prefill"] = fq
                                st.rerun()
                st.session_state["ask_history"].append({
                    "role":       "assistant",
                    "content":    answer,
                    "sources":    sources,
                    "follow_ups": follow_ups,
                })

    if st.session_state["ask_history"] and st.button("🗑️ Clear conversation"):
        st.session_state["ask_history"] = []
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# TAB: Quiz
# ─────────────────────────────────────────────────────────────────────────────
def tab_quiz():
    st.subheader("⚡ Quiz Game")
    st.caption("Generate a timed quiz from your document.")

    _ss("quiz_data",     None)
    _ss("quiz_answers",  {})
    _ss("quiz_result",   None)
    _ss("quiz_start_ts", None)

    # Generate form
    if st.session_state["quiz_data"] is None and st.session_state["quiz_result"] is None:
        with st.form("quiz_form"):
            topic      = st.text_input("Topic (optional)", placeholder="Leave blank to use document")
            num_q      = st.slider("Questions", 3, 15, 5)
            difficulty = st.selectbox("Difficulty", ["easy", "medium", "hard", "mixed"])
            submitted  = st.form_submit_button("🎯 Generate Quiz", type="primary")

        if submitted:
            with st.spinner("Generating questions …"):
                data, err = _post("/api/generate-quiz", json={
                    "doc_id":        _active_doc_id(),
                    "topic":         topic.strip() or None,
                    "num_questions": num_q,
                    "difficulty":    difficulty,
                })
            if err:
                st.error(err)
            else:
                st.session_state.update({
                    "quiz_data":     data,
                    "quiz_answers":  {},
                    "quiz_result":   None,
                    "quiz_start_ts": time.time(),
                })
                st.rerun()
        return

    # Show result
    if st.session_state["quiz_result"] is not None:
        res   = st.session_state["quiz_result"]
        grade = res.get("grade", "?")
        pct   = res.get("percentage", 0)
        icon  = {"S": "🏆", "A": "🥇", "B": "🥈", "C": "🥉", "D": "😬"}.get(grade, "📊")

        st.markdown(f"## {icon} Grade: **{grade}** — {pct:.0f}%")
        c1, c2, c3 = st.columns(3)
        c1.metric("Score",  f"{res['score']} / {res['total']}")
        c2.metric("Time",   f"{res.get('time_taken',0):.0f}s")
        c3.metric("Grade",  grade)

        if res.get("weak_topics"):
            st.warning("📉 Weak topics: " + ", ".join(res["weak_topics"]))
        if res.get("strong_topics"):
            st.success("📈 Strong topics: " + ", ".join(res["strong_topics"]))
        if res.get("recommendations"):
            st.info("💡 " + " · ".join(res["recommendations"]))

        with st.expander("📋 Detailed Review", expanded=True):
            for d in res.get("details", []):
                icon2 = "✅" if d["is_correct"] else "❌"
                st.markdown(f"**{icon2} {d['question']}**")
                st.caption(f"Your answer: {d['user_index']} · Correct: {d['correct_index']}")
                st.info(f"💬 {d.get('explanation','')}")
                st.divider()

        if st.button("🔄 New Quiz"):
            st.session_state.update({"quiz_data": None, "quiz_answers": {}, "quiz_result": None})
            st.rerun()
        return

    # Active quiz
    quiz      = st.session_state["quiz_data"]
    questions = quiz.get("questions", [])
    answers   = st.session_state["quiz_answers"]

    st.markdown(f"**Topic:** {quiz.get('topic','Mixed')} · **Difficulty:** {quiz.get('difficulty','?')}")
    st.progress(len(answers) / len(questions) if questions else 0,
                text=f"{len(answers)} / {len(questions)} answered")

    for i, q in enumerate(questions):
        with st.container(border=True):
            st.markdown(f"**Q{i+1}. {q['question']}**")
            st.caption(f"🏷️ {q.get('topic_tag','')} · {q.get('difficulty','')}")
            opts   = q.get("options", [])
            chosen = st.radio("Choose:", range(len(opts)),
                              format_func=lambda j, opts=opts: opts[j],
                              key=f"q_{q['id']}", index=None)
            if chosen is not None:
                answers[q["id"]] = chosen
                st.session_state["quiz_answers"] = answers

    all_answered = len(answers) == len(questions)
    if st.button("✅ Submit Quiz", type="primary", disabled=not all_answered):
        elapsed = time.time() - (st.session_state["quiz_start_ts"] or time.time())
        with st.spinner("Grading …"):
            data, err = _post("/quiz/submit", json={
                "quiz_id":    quiz["quiz_id"],
                "answers":    answers,
                "time_taken": int(elapsed),
            })
        if err:
            st.error(err)
        else:
            st.session_state["quiz_result"] = data
            st.rerun()

    if st.button("🗑️ Discard Quiz"):
        st.session_state.update({"quiz_data": None, "quiz_answers": {}})
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# TAB: Revision Planner
# ─────────────────────────────────────────────────────────────────────────────
def tab_planner():
    st.subheader("📅 Revision Planner")
    st.caption("Personalised day-by-day revision schedule up to your exam date.")

    _ss("plan_data", None)

    if st.session_state["plan_data"] is None:
        with st.form("planner_form"):
            exam_date   = st.date_input("Exam date")
            daily_hours = st.slider("Daily study hours", 0.5, 8.0, 2.0, step=0.5)
            syllabus    = st.text_area("Syllabus / topics (optional)", height=100,
                                       placeholder="Chapter 1: Kinematics\nChapter 2: Dynamics…")
            submitted   = st.form_submit_button("📅 Generate Plan", type="primary")

        if submitted:
            with st.spinner("Building revision plan …"):
                data, err = _post("/api/generate-plan", json={
                    "exam_date":     exam_date.isoformat(),
                    "daily_hours":   daily_hours,
                    "syllabus_text": syllabus.strip() or None,
                    "doc_id":        _active_doc_id(),
                })
            if err:
                st.error(err)
            else:
                st.session_state["plan_data"] = data
                st.rerun()
        return

    resp  = st.session_state["plan_data"]
    stats = resp.get("stats", {})

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Days to exam",  stats.get("days_to_exam", "?"))
    c2.metric("Study days",    stats.get("study_days",   "?"))
    c3.metric("Total hours",   f"{stats.get('total_study_mins',0)//60}h")
    c4.metric("Topics",        stats.get("topics_covered","?"))

    if resp.get("summary"):
        st.info(resp["summary"])
    if resp.get("tips"):
        with st.expander("💡 Study Tips", expanded=False):
            for tip in resp["tips"]:
                st.markdown(f"- {tip}")

    st.divider()
    st.markdown("### 🗓️ Schedule")
    SESS = {"concept": "📖", "quiz": "⚡", "buffer": "🔁", "rest": "😴"}
    PRIO = {"high": "🔴", "medium": "🟡", "low": "🟢"}

    for task in resp.get("plan", []):
        icon     = SESS.get(task.get("session_type", ""), "📅")
        priority = PRIO.get(task.get("priority",     ""), "⚪")
        label    = f"{icon} **{task.get('day_label', task.get('date',''))}** {priority} — {task.get('topic','')}"
        with st.expander(label, expanded=False):
            if task.get("subtopics"):
                st.markdown("**Subtopics:** " + ", ".join(task["subtopics"]))
            cols = st.columns(3)
            cols[0].write(f"⏱️ {task.get('duration_mins',0)} mins")
            cols[1].write(f"🛠️ {task.get('technique','—')}")
            cols[2].write(f"📌 {task.get('priority','—')}")
            if task.get("notes"):
                st.caption(task["notes"])

    if st.button("🔄 New Plan"):
        st.session_state["plan_data"] = None
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# TAB: Flashcards
# ─────────────────────────────────────────────────────────────────────────────
def tab_flashcards():
    st.subheader("🃏 Flashcards")
    st.caption("AI-generated flip cards for spaced-repetition practice.")

    _ss("fc_cards",   None)
    _ss("fc_index",   0)
    _ss("fc_flipped", False)

    if st.session_state["fc_cards"] is None:
        with st.form("fc_form"):
            topic  = st.text_input("Topic (optional)")
            num    = st.slider("Number of cards", 3, 20, 8)
            submit = st.form_submit_button("🃏 Generate Cards", type="primary")

        if submit:
            with st.spinner("Generating flashcards …"):
                data, err = _post("/api/flashcards/generate", json={
                    "doc_id": _active_doc_id(),
                    "topic":  topic.strip() or None,
                    "count":  num,
                })
            if err:
                st.error(err)
            else:
                cards = data.get("cards", data.get("flashcards", []))
                if cards:
                    st.session_state.update({"fc_cards": cards, "fc_index": 0, "fc_flipped": False})
                    st.rerun()
                else:
                    st.warning("No cards returned.")
        return

    cards   = st.session_state["fc_cards"]
    idx     = st.session_state["fc_index"]
    flipped = st.session_state["fc_flipped"]
    card    = cards[idx]
    front   = card.get("front", card.get("question", ""))
    back    = card.get("back",  card.get("answer",   ""))

    st.progress((idx + 1) / len(cards), text=f"Card {idx+1} / {len(cards)}")
    with st.container(border=True):
        if not flipped:
            st.markdown(f"### ❓ {front}")
            st.caption("Click **Flip** to reveal the answer")
        else:
            st.markdown(f"### ❓ {front}")
            st.success(f"✅ {back}")

    c1, c2, c3, c4 = st.columns(4)
    if c1.button("⬅️ Prev",    disabled=idx == 0):
        st.session_state.update({"fc_index": idx-1, "fc_flipped": False}); st.rerun()
    if c2.button("🔄 Flip"):
        st.session_state["fc_flipped"] = not flipped; st.rerun()
    if c3.button("➡️ Next",    disabled=idx >= len(cards)-1):
        st.session_state.update({"fc_index": idx+1, "fc_flipped": False}); st.rerun()
    if c4.button("🔀 Shuffle"):
        random.shuffle(cards)
        st.session_state.update({"fc_cards": cards, "fc_index": 0, "fc_flipped": False}); st.rerun()

    if st.button("🗑️ New Deck"):
        st.session_state.update({"fc_cards": None, "fc_index": 0, "fc_flipped": False})
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# TAB: Feynman Mode
# ─────────────────────────────────────────────────────────────────────────────
def tab_feynman():
    st.subheader("🧠 Feynman Technique")
    st.caption("Explain a concept in your own words — get scored on understanding, gaps, and strengths.")

    with st.form("feynman_form"):
        concept     = st.text_input("Concept to explain", placeholder="e.g. Photosynthesis")
        explanation = st.text_area("Your explanation", height=200,
                                   placeholder="Explain the concept as if teaching a 10-year-old …")
        submitted   = st.form_submit_button("🔬 Evaluate", type="primary")

    if submitted and concept.strip() and explanation.strip():
        with st.spinner("Evaluating your explanation …"):
            data, err = _post("/api/feynman/evaluate", json={
                "concept":     concept.strip(),
                "explanation": explanation.strip(),
                "doc_id":      _active_doc_id(),
            })
        if err:
            st.error(err)
            return

        score = data.get("score", 0)
        grade = data.get("grade", "?")
        icon  = {"S": "🏆", "A": "🥇", "B": "🥈", "C": "🥉", "D": "😬"}.get(grade, "📊")

        st.markdown(f"## {icon} Grade: **{grade}** — {score}/100")
        st.progress(score / 100)

        col1, col2 = st.columns(2)
        with col1:
            if data.get("strengths"):
                st.success("✅ **Strengths**")
                for s in data["strengths"]:
                    st.markdown(f"- {s}")
        with col2:
            if data.get("gaps"):
                st.error("⚠️ **Gaps to fill**")
                for g in data["gaps"]:
                    st.markdown(f"- {g}")

        if data.get("coaching_tip"):
            st.info(f"💡 **Coaching tip:** {data['coaching_tip']}")

        if data.get("qa_pairs"):
            with st.expander("📝 Q&A Pairs to study", expanded=False):
                for pair in data["qa_pairs"]:
                    st.markdown(f"**Q:** {pair['question']}")
                    st.markdown(f"**A:** {pair['answer']}")
                    st.divider()


# ─────────────────────────────────────────────────────────────────────────────
# TAB: Cheat Sheet
# ─────────────────────────────────────────────────────────────────────────────
def tab_cheatsheet():
    st.subheader("📋 Cheat Sheet Generator")
    st.caption("One-page summary of your document, formatted as Markdown.")

    doc_id = _active_doc_id()
    if not doc_id:
        st.warning("⚠️ Upload and select a document first.")
        return

    topic = st.text_input("Focus topic (optional)", placeholder="e.g. Formulas, Key Definitions")

    if st.button("📋 Generate Cheat Sheet", type="primary"):
        with st.spinner("Generating cheat sheet …"):
            data, err = _post("/api/cheatsheet", json={
                "doc_id": doc_id,
                "topic":  topic.strip() or None,
            })
        if err:
            st.error(err)
        else:
            content = data.get("content", data.get("cheatsheet", str(data)))
            st.markdown("---")
            st.markdown(content)
            st.download_button(
                "⬇️ Download (.md)",
                data=content,
                file_name="cheatsheet.md",
                mime="text/markdown",
            )


# ─────────────────────────────────────────────────────────────────────────────
# TAB: Progress Dashboard
# ─────────────────────────────────────────────────────────────────────────────
def tab_progress():
    st.subheader("📊 Progress Dashboard")

    with st.spinner("Loading progress …"):
        data, err = _get("/api/progress/summary", timeout=30)

    if err:
        st.error(err)
        return

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Quizzes",       data.get("total_quizzes", 0))
    c2.metric("Avg Score",           f"{data.get('avg_score_pct', 0):.0f}%")
    c3.metric("Best Score",          f"{data.get('best_score_pct', 0):.0f}%")
    c4.metric("Streak (days)",       data.get("current_streak_days", 0))
    st.metric("Questions Answered",  data.get("total_questions_answered", 0))

    if data.get("score_history"):
        st.divider()
        st.markdown("### 📈 Score History")
        rows = [
            {"Date": h["date"], "Topic": h["topic"],
             "Score": f"{h['score']}/{h['total']}", "Grade": h["grade"]}
            for h in data["score_history"][-20:]
        ]
        st.dataframe(rows, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        if data.get("weak_topics"):
            st.markdown("### 📉 Weak Topics")
            for t in data["weak_topics"]:
                st.progress(t["avg_pct"] / 100, text=f"{t['topic']} ({t['avg_pct']:.0f}%)")
    with col2:
        if data.get("strong_topics"):
            st.markdown("### 📈 Strong Topics")
            for t in data["strong_topics"]:
                st.progress(t["avg_pct"] / 100, text=f"{t['topic']} ({t['avg_pct']:.0f}%)")

    if data.get("feynman_history"):
        st.divider()
        st.markdown("### 🧠 Feynman History")
        rows = [
            {"Date": h["date"], "Concept": h["concept"],
             "Score": h["score"], "Grade": h["grade"]}
            for h in data["feynman_history"][-10:]
        ]
        st.dataframe(rows, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# Main entrypoint
# ─────────────────────────────────────────────────────────────────────────────
def main():
    # ── Step 1: ensure backend is running (blocks until healthy or 90s) ───────
    if not _ensure_backend():
        st.stop()

    # ── Step 2: sidebar ───────────────────────────────────────────────────────
    sidebar()

    # ── Step 3: tabs ──────────────────────────────────────────────────────────
    tabs = st.tabs([
        "📤 Upload",
        "💡 ELI10",
        "🤖 Ask AI",
        "⚡ Quiz",
        "📅 Planner",
        "🃏 Flashcards",
        "🧠 Feynman",
        "📋 Cheat Sheet",
        "📊 Progress",
    ])

    with tabs[0]: tab_upload()
    with tabs[1]: tab_explain()
    with tabs[2]: tab_ask()
    with tabs[3]: tab_quiz()
    with tabs[4]: tab_planner()
    with tabs[5]: tab_flashcards()
    with tabs[6]: tab_feynman()
    with tabs[7]: tab_cheatsheet()
    with tabs[8]: tab_progress()


if __name__ == "__main__":
    main()

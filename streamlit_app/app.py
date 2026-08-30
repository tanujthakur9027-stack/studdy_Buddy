"""
StudyBuddy — Streamlit Frontend
Talks to the FastAPI backend at BACKEND_URL (set in .streamlit/secrets.toml or env).
"""
from __future__ import annotations

import os
import time
import random
import json
import requests
import streamlit as st

# ── Config ────────────────────────────────────────────────────────────────────
def _get_backend_url() -> str:
    # 1. Environment variable (e.g. set by docker / local shell)
    if os.environ.get("BACKEND_URL"):
        return os.environ["BACKEND_URL"]
    # 2. Streamlit secrets (Streamlit Cloud or local secrets.toml)
    try:
        return st.secrets["BACKEND_URL"]
    except (KeyError, Exception):
        pass
    return "http://localhost:8000"

BACKEND_URL = _get_backend_url()

# Strip trailing slash
BACKEND_URL = BACKEND_URL.rstrip("/")

TIMEOUT_SHORT  = 60    # seconds — quick endpoints
TIMEOUT_LONG   = 180   # seconds — LLM-heavy endpoints

ACCEPTED_TYPES = [
    "application/pdf",
    "text/plain",
    "text/markdown",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "image/png",
    "image/jpeg",
    "image/webp",
    "application/octet-stream",
]

# ── Page setup ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="StudyBuddy AI",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS (minimal dark theme tweaks) ────────────────────────────────────
st.markdown("""
<style>
  /* Slightly widen the main content area */
  .block-container { max-width: 960px; padding-top: 1.5rem; }
  /* Make expander headers bolder */
  .streamlit-expanderHeader { font-weight: 600; }
  /* Subtle card-like containers */
  [data-testid="stVerticalBlock"] > div:has([data-testid="stExpander"]) {
      border-radius: 8px;
  }
  /* Source citation chips */
  .source-chip {
      display: inline-block; background: #1e293b; border: 1px solid #334155;
      border-radius: 6px; padding: 2px 8px; font-size: 12px; color: #94a3b8; margin: 2px;
  }
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────
def _api(method: str, path: str, timeout=TIMEOUT_LONG, **kwargs):
    """Thin wrapper around requests; returns (data_or_None, error_or_None)."""
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
        return None, f"Cannot reach backend at {BACKEND_URL}. Is it running?"
    except requests.exceptions.Timeout:
        return None, "Request timed out. The backend is taking too long — try again."
    except Exception as exc:
        return None, str(exc)


def _get(path: str, timeout=TIMEOUT_SHORT, **kwargs):
    return _api("GET", path, timeout=timeout, **kwargs)


def _post(path: str, timeout=TIMEOUT_LONG, **kwargs):
    return _api("POST", path, timeout=timeout, **kwargs)


# ── Session-state helpers ─────────────────────────────────────────────────────
def _ss(key, default):
    if key not in st.session_state:
        st.session_state[key] = default
    return st.session_state[key]


# ── Sidebar ───────────────────────────────────────────────────────────────────
def sidebar():
    with st.sidebar:
        st.markdown("## 🎓 StudyBuddy AI")
        st.caption("Powered by RAG + LLM")
        st.divider()

        # Backend health
        with st.expander("🔌 Backend Status", expanded=False):
            if st.button("Check health", key="health_btn"):
                data, err = _get("/health", timeout=15)
                if err:
                    st.error(err)
                else:
                    status_icon = "✅" if data.get("status") == "ok" else "⚠️"
                    st.write(f"{status_icon} **{data.get('status', '?').upper()}**")
                    st.write(f"Provider: `{data.get('provider', '?')}`")
                    st.write(f"Model: `{data.get('model', '?')}`")
                    st.write(f"Docs indexed: `{data.get('indexed_documents', 0)}`")
                    st.write(f"FAISS vectors: `{data.get('faiss_vectors', 0)}`")

        st.divider()

        # Document picker
        st.markdown("### 📄 Documents")
        _load_documents()

        docs: list[dict] = st.session_state.get("documents", [])
        if not docs:
            st.caption("Upload a document first ↑")
        else:
            names = [d["filename"] for d in docs]
            idx   = st.selectbox(
                "Active document",
                range(len(names)),
                format_func=lambda i: names[i],
                key="active_doc_idx",
            )
            st.session_state["active_doc"] = docs[idx]
            st.caption(
                f"Chunks: {docs[idx].get('chunks', '?')} · "
                f"Pages: {docs[idx].get('pages', '?')} · "
                f"Parser: {docs[idx].get('parser_used', '?')}"
            )

        st.divider()
        st.caption(f"Backend: `{BACKEND_URL}`")


def _load_documents():
    """Fetch documents from backend and cache in session state."""
    if "documents_loaded" not in st.session_state:
        data, err = _get("/api/documents", timeout=20)
        if err:
            st.warning(f"Could not load documents: {err}")
            st.session_state["documents"] = []
        else:
            st.session_state["documents"] = data or []
        st.session_state["documents_loaded"] = True


def _active_doc_id() -> str | None:
    doc = st.session_state.get("active_doc")
    return doc["doc_id"] if doc else None


def _invalidate_docs():
    """Force a document list reload next time sidebar renders."""
    if "documents_loaded" in st.session_state:
        del st.session_state["documents_loaded"]
    if "documents" in st.session_state:
        del st.session_state["documents"]
    if "active_doc" in st.session_state:
        del st.session_state["active_doc"]


# ─────────────────────────────────────────────────────────────────────────────
# TAB: Upload
# ─────────────────────────────────────────────────────────────────────────────
def tab_upload():
    st.subheader("📤 Upload Documents")
    st.caption(
        "Upload your syllabus, PDF notes, DOCX, PPT, XLSX, or images. "
        "Up to **200 MB** per file."
    )

    uploaded = st.file_uploader(
        "Choose a file",
        type=["pdf", "txt", "md", "doc", "docx", "ppt", "pptx", "xls", "xlsx",
              "png", "jpg", "jpeg", "webp", "bin"],
        accept_multiple_files=True,
        help="Supported: PDF, TXT, MD, DOC, DOCX, PPT, PPTX, XLS, XLSX, PNG, JPG, WEBP — max 200 MB each",
    )

    if uploaded:
        if st.button("⬆️ Upload & Index", type="primary"):
            for f in uploaded:
                with st.spinner(f"Uploading **{f.name}** …"):
                    data, err = _api(
                        "POST", "/api/upload",
                        timeout=300,
                        files={"file": (f.name, f.getvalue(), f.type or "application/octet-stream")},
                    )
                if err:
                    st.error(f"❌ {f.name}: {err}")
                else:
                    st.success(
                        f"✅ **{data['filename']}** indexed — "
                        f"{data['chunks']} chunks · {data['pages']} pages · "
                        f"parser: `{data['parser_used']}`"
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
                c1.metric("Chunks", doc.get("chunks", "?"))
                c2.metric("Pages",  doc.get("pages",  "?"))
                c3.metric("Tokens", doc.get("total_tokens", "?"))
                c4.metric("Parser", doc.get("parser_used", "?"))
        with col2:
            if st.button("🗑️", key=f"del_{doc['doc_id']}", help="Delete this document"):
                _, err = _api("DELETE", f"/api/documents/{doc['doc_id']}", timeout=20)
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
    st.caption("Get a simplified, analogy-driven explanation of any concept from your documents.")

    topic = st.text_input("Topic / concept", placeholder="e.g. Photosynthesis, Newton's Laws, Supply & Demand")
    level = st.selectbox("Depth", ["eli5", "beginner", "intermediate"], index=1,
                         format_func=lambda x: {"eli5": "🧒 Very Simple (ELI5)",
                                                 "beginner": "📖 Beginner",
                                                 "intermediate": "🎓 Intermediate"}[x])

    if st.button("✨ Explain", type="primary") and topic.strip():
        with st.spinner("Generating explanation …"):
            data, err = _post("/api/explain", json={
                "topic": topic.strip(),
                "doc_id": _active_doc_id(),
                "level": level,
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
                for point in data["key_points"]:
                    st.markdown(f"- {point}")


# ─────────────────────────────────────────────────────────────────────────────
# TAB: Ask AI (RAG Q&A)
# ─────────────────────────────────────────────────────────────────────────────
def tab_ask():
    st.subheader("🤖 Ask AI — RAG Q&A")
    st.caption("Ask any question about your uploaded document. Answers include source citations.")

    _ss("ask_history", [])

    mode = st.radio("Answer mode", ["standard", "eli5"], horizontal=True,
                    format_func=lambda x: "📚 Standard" if x == "standard" else "🧒 ELI5")

    # Display conversation history
    for msg in st.session_state["ask_history"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("sources"):
                with st.expander("📎 Sources", expanded=False):
                    for src in msg["sources"]:
                        st.markdown(
                            f'<span class="source-chip">📄 {src["filename"]} p.{src["page"]}</span>'
                            f' {src.get("snippet", "")[:120]}…',
                            unsafe_allow_html=True,
                        )
            if msg.get("follow_ups"):
                st.caption("💬 Follow-up questions:")
                for fq in msg["follow_ups"]:
                    if st.button(fq, key=f"fq_{hash(fq)}"):
                        st.session_state["_ask_prefill"] = fq
                        st.rerun()

    question = st.chat_input("Ask a question about your document …")
    # Support follow-up pre-fill
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
                    "doc_id": _active_doc_id(),
                    "mode": mode,
                    "k": 5,
                    "conversation_history": history[-6:],  # last 3 turns
                })
            if err:
                st.error(err)
                st.session_state["ask_history"].pop()
            else:
                answer = data["answer"]
                st.markdown(answer)
                sources = data.get("sources", [])
                follow_ups = data.get("follow_up_questions", [])
                if sources:
                    with st.expander("📎 Sources", expanded=False):
                        for src in sources:
                            st.markdown(
                                f'<span class="source-chip">📄 {src["filename"]} p.{src["page"]}</span>'
                                f' {src.get("snippet", "")[:120]}…',
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
                    "role": "assistant",
                    "content": answer,
                    "sources": sources,
                    "follow_ups": follow_ups,
                })

    if st.session_state["ask_history"]:
        if st.button("🗑️ Clear conversation"):
            st.session_state["ask_history"] = []
            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# TAB: Quiz
# ─────────────────────────────────────────────────────────────────────────────
def tab_quiz():
    st.subheader("⚡ Quiz Game")
    st.caption("Generate a timed quiz from your document.")

    _ss("quiz_data",    None)
    _ss("quiz_answers", {})
    _ss("quiz_result",  None)
    _ss("quiz_start_ts", None)

    # ── Generate form ─────────────────────────────────────────────────────────
    if st.session_state["quiz_data"] is None and st.session_state["quiz_result"] is None:
        with st.form("quiz_form"):
            topic       = st.text_input("Topic (optional)", placeholder="Leave blank to use document content")
            num_q       = st.slider("Number of questions", 3, 15, 5)
            difficulty  = st.selectbox("Difficulty", ["easy", "medium", "hard", "mixed"])
            submitted   = st.form_submit_button("🎯 Generate Quiz", type="primary")

        if submitted:
            with st.spinner("Generating questions …"):
                data, err = _post("/api/generate-quiz", json={
                    "doc_id":       _active_doc_id(),
                    "topic":        topic.strip() or None,
                    "num_questions": num_q,
                    "difficulty":   difficulty,
                })
            if err:
                st.error(err)
            else:
                st.session_state["quiz_data"]    = data
                st.session_state["quiz_answers"]  = {}
                st.session_state["quiz_result"]   = None
                st.session_state["quiz_start_ts"] = time.time()
                st.rerun()
        return

    # ── Show result ───────────────────────────────────────────────────────────
    if st.session_state["quiz_result"] is not None:
        res = st.session_state["quiz_result"]
        grade = res.get("grade", "?")
        pct   = res.get("percentage", 0)
        grade_color = {"S": "🏆", "A": "🥇", "B": "🥈", "C": "🥉", "D": "😬"}.get(grade, "📊")

        st.markdown(f"## {grade_color} Grade: **{grade}** — {pct:.0f}%")
        c1, c2, c3 = st.columns(3)
        c1.metric("Score",   f"{res['score']} / {res['total']}")
        c2.metric("Time",    f"{res.get('time_taken', 0):.0f}s")
        c3.metric("Correct", f"{res['score']}")

        if res.get("weak_topics"):
            st.warning("📉 Weak topics: " + ", ".join(res["weak_topics"]))
        if res.get("strong_topics"):
            st.success("📈 Strong topics: " + ", ".join(res["strong_topics"]))
        if res.get("recommendations"):
            st.info("💡 " + " · ".join(res["recommendations"]))

        with st.expander("📋 Detailed Review", expanded=True):
            for detail in res.get("details", []):
                icon = "✅" if detail["is_correct"] else "❌"
                st.markdown(f"**{icon} {detail['question']}**")
                st.caption(f"Your answer index: {detail['user_index']} · Correct: {detail['correct_index']}")
                st.info(f"💬 {detail.get('explanation', '')}")
                st.divider()

        if st.button("🔄 New Quiz"):
            st.session_state["quiz_data"]    = None
            st.session_state["quiz_answers"] = {}
            st.session_state["quiz_result"]  = None
            st.rerun()
        return

    # ── Active quiz ───────────────────────────────────────────────────────────
    quiz  = st.session_state["quiz_data"]
    questions = quiz.get("questions", [])
    answers   = st.session_state["quiz_answers"]

    st.markdown(f"**Topic:** {quiz.get('topic', 'Mixed')} · **Difficulty:** {quiz.get('difficulty', '?')}")
    st.progress(len(answers) / len(questions) if questions else 0,
                text=f"{len(answers)} / {len(questions)} answered")

    for i, q in enumerate(questions):
        with st.container(border=True):
            st.markdown(f"**Q{i+1}. {q['question']}**")
            st.caption(f"🏷️ {q.get('topic_tag', '')} · {q.get('difficulty', '')}")
            opts = q.get("options", [])
            chosen = st.radio(
                "Choose:",
                range(len(opts)),
                format_func=lambda j, opts=opts: opts[j],
                key=f"q_{q['id']}",
                index=None,
            )
            if chosen is not None:
                answers[q["id"]] = chosen
                st.session_state["quiz_answers"] = answers

    all_answered = len(answers) == len(questions)
    if st.button("✅ Submit Quiz", type="primary", disabled=not all_answered):
        time_taken = time.time() - (st.session_state["quiz_start_ts"] or time.time())
        with st.spinner("Grading …"):
            data, err = _post("/quiz/submit", json={
                "quiz_id":    quiz["quiz_id"],
                "answers":    answers,
                "time_taken": int(time_taken),
            })
        if err:
            st.error(err)
        else:
            st.session_state["quiz_result"] = data
            st.rerun()

    if st.button("🗑️ Discard Quiz"):
        st.session_state["quiz_data"]    = None
        st.session_state["quiz_answers"] = {}
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# TAB: Revision Planner
# ─────────────────────────────────────────────────────────────────────────────
def tab_planner():
    st.subheader("📅 Revision Planner")
    st.caption("Generate a personalised day-by-day revision schedule up to your exam date.")

    _ss("plan_data", None)

    if st.session_state["plan_data"] is None:
        with st.form("planner_form"):
            exam_date    = st.date_input("Exam date")
            daily_hours  = st.slider("Daily study hours", 0.5, 8.0, 2.0, step=0.5)
            syllabus_txt = st.text_area("Syllabus / topics (optional)", height=100,
                                        placeholder="Chapter 1: Kinematics\nChapter 2: Dynamics…")
            submitted    = st.form_submit_button("📅 Generate Plan", type="primary")

        if submitted:
            with st.spinner("Building your revision plan …"):
                data, err = _post("/api/generate-plan", json={
                    "exam_date":      exam_date.isoformat(),
                    "daily_hours":    daily_hours,
                    "syllabus_text":  syllabus_txt.strip() or None,
                    "doc_id":         _active_doc_id(),
                })
            if err:
                st.error(err)
            else:
                st.session_state["plan_data"] = data
                st.rerun()
        return

    plan_resp = st.session_state["plan_data"]
    stats     = plan_resp.get("stats", {})

    # Summary metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Days to exam",    stats.get("days_to_exam", "?"))
    c2.metric("Study days",      stats.get("study_days", "?"))
    c3.metric("Total hours",     f"{stats.get('total_study_mins', 0) // 60}h")
    c4.metric("Topics",          stats.get("topics_covered", "?"))

    if plan_resp.get("summary"):
        st.info(plan_resp["summary"])

    if plan_resp.get("tips"):
        with st.expander("💡 Study Tips", expanded=False):
            for tip in plan_resp["tips"]:
                st.markdown(f"- {tip}")

    st.divider()
    st.markdown("### 🗓️ Day-by-Day Schedule")

    SESSION_ICONS = {"concept": "📖", "quiz": "⚡", "buffer": "🔁", "rest": "😴"}
    PRIORITY_COLORS = {"high": "🔴", "medium": "🟡", "low": "🟢"}

    for task in plan_resp.get("plan", []):
        icon     = SESSION_ICONS.get(task.get("session_type", ""), "📅")
        priority = PRIORITY_COLORS.get(task.get("priority", ""), "⚪")
        label    = f"{icon} **{task.get('day_label', task.get('date', ''))}** {priority} — {task.get('topic', '')}"
        with st.expander(label, expanded=False):
            if task.get("subtopics"):
                st.markdown("**Subtopics:** " + ", ".join(task["subtopics"]))
            cols = st.columns(3)
            cols[0].write(f"⏱️ {task.get('duration_mins', 0)} mins")
            cols[1].write(f"🛠️ {task.get('technique', '—')}")
            cols[2].write(f"📌 {task.get('priority', '—')}")
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

    _ss("fc_cards", None)
    _ss("fc_index", 0)
    _ss("fc_flipped", False)

    if st.session_state["fc_cards"] is None:
        with st.form("fc_form"):
            topic  = st.text_input("Topic (optional)", placeholder="Leave blank for automatic")
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
                    st.session_state["fc_cards"]   = cards
                    st.session_state["fc_index"]   = 0
                    st.session_state["fc_flipped"] = False
                    st.rerun()
                else:
                    st.warning("No cards returned.")
        return

    cards   = st.session_state["fc_cards"]
    idx     = st.session_state["fc_index"]
    flipped = st.session_state["fc_flipped"]
    card    = cards[idx]

    st.progress((idx + 1) / len(cards), text=f"Card {idx + 1} / {len(cards)}")

    front = card.get("front", card.get("question", ""))
    back  = card.get("back",  card.get("answer",   ""))

    with st.container(border=True):
        if not flipped:
            st.markdown(f"### ❓ {front}")
            st.caption("Click **Flip** to reveal the answer")
        else:
            st.markdown(f"### ❓ {front}")
            st.success(f"✅ {back}")

    c1, c2, c3, c4 = st.columns(4)
    if c1.button("⬅️ Prev", disabled=idx == 0):
        st.session_state["fc_index"]   = idx - 1
        st.session_state["fc_flipped"] = False
        st.rerun()
    if c2.button("🔄 Flip"):
        st.session_state["fc_flipped"] = not flipped
        st.rerun()
    if c3.button("➡️ Next", disabled=idx >= len(cards) - 1):
        st.session_state["fc_index"]   = idx + 1
        st.session_state["fc_flipped"] = False
        st.rerun()
    if c4.button("🔀 Shuffle"):
        random.shuffle(cards)
        st.session_state["fc_cards"]   = cards
        st.session_state["fc_index"]   = 0
        st.session_state["fc_flipped"] = False
        st.rerun()

    if st.button("🗑️ New Deck"):
        st.session_state["fc_cards"]   = None
        st.session_state["fc_index"]   = 0
        st.session_state["fc_flipped"] = False
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# TAB: Feynman Mode
# ─────────────────────────────────────────────────────────────────────────────
def tab_feynman():
    st.subheader("🧠 Feynman Technique")
    st.caption("Explain a concept in your own words — the AI grades your understanding and finds gaps.")

    with st.form("feynman_form"):
        concept     = st.text_input("Concept to explain", placeholder="e.g. Photosynthesis")
        explanation = st.text_area("Your explanation", height=200,
                                   placeholder="Explain the concept as if you're teaching it to a 10-year-old …")
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
        grade_icon = {"S": "🏆", "A": "🥇", "B": "🥈", "C": "🥉", "D": "😬"}.get(grade, "📊")

        st.markdown(f"## {grade_icon} Grade: **{grade}** — {score}/100")
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
    st.caption("Generate a concise summary / cheat sheet from your document.")

    doc_id = _active_doc_id()
    if not doc_id:
        st.warning("⚠️ Upload and select a document first.")
        return

    topic = st.text_input("Topic / focus (optional)", placeholder="e.g. Formulas, Key Definitions")

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
# TAB: Progress
# ─────────────────────────────────────────────────────────────────────────────
def tab_progress():
    st.subheader("📊 Progress Dashboard")

    with st.spinner("Loading your progress …"):
        data, err = _get("/api/progress/summary", timeout=30)

    if err:
        st.error(err)
        return

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Quizzes",     data.get("total_quizzes", 0))
    c2.metric("Avg Score",         f"{data.get('avg_score_pct', 0):.0f}%")
    c3.metric("Best Score",        f"{data.get('best_score_pct', 0):.0f}%")
    c4.metric("Streak (days)",     data.get("current_streak_days", 0))

    st.metric("Questions Answered", data.get("total_questions_answered", 0))

    # Score history as a table
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
# Main
# ─────────────────────────────────────────────────────────────────────────────
def main():
    sidebar()

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

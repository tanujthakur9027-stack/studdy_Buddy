"""
pages/learning.py — AI Study Tools (private, per-user)

Tabs: Upload/Paste Text · Ask AI · ELI10 Explain · Quiz · Planner · Flashcards · Feynman · Cheat Sheet · Progress

A sidebar "Active document" selector shared across all tabs.
All AI endpoints are called with the user's JWT so data is private.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import random
import time

import requests
import streamlit as st

from core.styles import inject_global_css, badge
from core.animations import page_enter, confetti
from core.auth_state import require_login, _p
from core.api_client import api_get, api_post, api_request, stream_sse, BACKEND_URL


inject_global_css()
require_login()
page_enter()

def _tab_head(t, s=""):
    st.markdown(
        f'<p style="font-size:1rem;font-weight:700;color:#fafafa;margin:0 0 .2rem">{t}</p>'
        + (f'<p style="font-size:.8rem;color:#71717a;margin:0 0 1rem">{s}</p>' if s else ""),
        unsafe_allow_html=True,
    )


# ── Helpers ───────────────────────────────────────────────────────────────────
def _ss(key, default):
    if key not in st.session_state:
        st.session_state[key] = default
    return st.session_state[key]


def _active_doc_id():
    doc = st.session_state.get("active_doc")
    return doc["doc_id"] if doc else None


def _load_documents(force=False):
    if force or not st.session_state.get("documents_loaded"):
        data, _ = api_get("/api/documents", timeout=15)
        st.session_state["documents"] = data or []
        st.session_state["documents_loaded"] = True


def _invalidate_docs():
    for k in ("documents_loaded", "documents", "active_doc"):
        st.session_state.pop(k, None)


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
<div style="display:flex;align-items:center;gap:10px;padding:.5rem 0 1.25rem">
  <div style="width:36px;height:36px;border-radius:9px;
       background:linear-gradient(135deg,#6366f1,#8b5cf6);
       display:flex;align-items:center;justify-content:center">
    <svg width="20" height="20" viewBox="0 0 44 44" fill="none">
      <path d="M22 4L4 15l18 11 18-11L22 4z" stroke="rgba(255,255,255,0.95)" stroke-width="2.5" stroke-linejoin="round"/>
      <path d="M4 29l18 11 18-11" stroke="rgba(255,255,255,0.95)" stroke-width="2.5" stroke-linejoin="round"/>
    </svg>
  </div>
  <span style="font-size:15px;font-weight:700;color:#fafafa">Study Buddy AI</span>
</div>""", unsafe_allow_html=True)

    st.markdown('<div class="sb-nav-label">Active Document</div>', unsafe_allow_html=True)
    _load_documents()
    docs = st.session_state.get("documents", [])
    if not docs:
        st.caption("No documents yet. Upload in the Study Material tab.")
    else:
        names = [d["filename"] for d in docs]
        idx = st.selectbox("Doc", range(len(names)),
                            format_func=lambda i: names[i],
                            key="active_doc_idx", label_visibility="collapsed")
        st.session_state["active_doc"] = docs[idx]

    if st.button("🔄 Refresh Documents"):
        _invalidate_docs()
        st.rerun()

    st.divider()
    st.markdown('<div class="sb-nav-label">Navigate</div>', unsafe_allow_html=True)
    if st.button("🏠 Dashboard"):
        st.switch_page(_p("dashboard.py"))
    if st.button("📋 Classes & Assignments"):
        st.switch_page(_p("classes.py"))
    if st.button("👤 Profile"):
        st.switch_page(_p("profile.py"))


# ── Page header ───────────────────────────────────────────────────────────────
st.markdown("""
<div style="margin-bottom:1.25rem;animation:fadeUp .4s both">
  <h1 style="font-size:1.6rem;font-weight:800;color:#fafafa;margin:0 0 .25rem;letter-spacing:-.03em">
    🧠 AI Study Tools
  </h1>
  <p style="font-size:.875rem;color:#71717a;margin:0">Upload your material or paste text, then use any tool below.</p>
</div>""", unsafe_allow_html=True)

(tab_upload, tab_ask, tab_explain, tab_quiz, tab_planner,
 tab_fc, tab_feynman, tab_cheat, tab_progress) = st.tabs([
    "📤 Study Material", "🤖 Ask AI", "💡 ELI10",
    "🎯 Quiz", "📆 Planner", "🃏 Flashcards",
    "🧠 Feynman", "📝 Cheat Sheet", "📈 Progress",
])


# ─────────────────────────────────────────────────────────────────────────────
# TAB: Study Material (Upload + Paste Text)
# ─────────────────────────────────────────────────────────────────────────────
with tab_upload:
    _ss("upload_mode", "upload")

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("📁 Upload Document", use_container_width=True,
                     type="primary" if st.session_state["upload_mode"] == "upload" else "secondary"):
            st.session_state["upload_mode"] = "upload"
            st.rerun()
    with col_b:
        if st.button("✏️ Paste / Type Text", use_container_width=True,
                     type="primary" if st.session_state["upload_mode"] == "text" else "secondary"):
            st.session_state["upload_mode"] = "text"
            st.rerun()

    st.markdown("---")

    if st.session_state["upload_mode"] == "upload":
        st.markdown("**Upload your study material** — PDF, DOCX, TXT, PPTX, XLSX, PNG, JPG, GIF, WEBP, and more.")
        uploaded = st.file_uploader(
            "Choose file(s)",
            type=["pdf","txt","md","doc","docx","ppt","pptx","xls","xlsx",
                  "png","jpg","jpeg","webp","jfif","gif","bin"],
            accept_multiple_files=True,
            key="learning_upload",
        )
        if uploaded and st.button("⚡ Upload & Index", type="primary"):
            for f in uploaded:
                with st.spinner(f"Indexing {f.name} …"):
                    data, err = api_request("POST", "/api/upload", timeout=300,
                                            files={"file": (f.name, f.getvalue(), f.type or "application/octet-stream")})
                if err:
                    st.error(f"{f.name}: {err}")
                else:
                    st.success(f"✅ **{data['filename']}** — {data['chunks']} chunks · {data['pages']} pages")
                    if data.get("description"):
                        st.caption(data["description"])
            _invalidate_docs()
            st.rerun()
    else:
        st.markdown("**Paste your topic, notes, or any text** — then switch to any AI tool tab.")
        _ss("pasted_text", "")
        pasted = st.text_area(
            "Topic or notes",
            value=st.session_state["pasted_text"],
            height=240,
            placeholder="e.g. Newton's Laws of Motion, or paste your lecture notes here…",
            key="pasted_text_input",
        )
        st.session_state["pasted_text"] = pasted
        if pasted.strip():
            wc = len(pasted.strip().split())
            st.caption(f"📝 {wc} words — switch to any tab above to generate study materials.")

    st.divider()
    st.markdown('<p style="font-size:12px;font-weight:600;color:#a1a1aa;text-transform:uppercase;letter-spacing:.06em">Indexed Documents</p>', unsafe_allow_html=True)
    _load_documents()
    docs = st.session_state.get("documents", [])
    if not docs:
        st.markdown('<div style="background:#18181b;border:1px dashed #27272a;border-radius:10px;padding:1.5rem;text-align:center;color:#52525b;font-size:13px">No documents yet.</div>', unsafe_allow_html=True)
    else:
        for doc in docs:
            col1, col2 = st.columns([6, 1])
            with col1:
                with st.expander(f"📄 {doc['filename']}", expanded=False):
                    if doc.get("description"):
                        st.caption(doc["description"])
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Chunks", doc.get("chunks", "?"))
                    c2.metric("Pages",  doc.get("pages", "?"))
                    c3.metric("Tokens", doc.get("total_tokens", "?"))
                    c4.metric("Parser", doc.get("parser_used", "?"))
            with col2:
                if st.button("Delete", key=f"del_{doc['doc_id']}"):
                    _, err = api_request("DELETE", f"/api/documents/{doc['doc_id']}", timeout=15)
                    if err:
                        st.error(err)
                    else:
                        st.success("Deleted")
                        _invalidate_docs()
                        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# TAB: Ask AI
# ─────────────────────────────────────────────────────────────────────────────
with tab_ask:
    _tab_head("Ask AI — RAG Q&A", "Ask anything about your document or topic.")
    _ss("ask_history", [])
    mode = st.radio("Mode", ["standard", "eli5"], horizontal=True,
                    format_func=lambda x: "📚 Standard" if x == "standard" else "🧒 ELI5")
    for msg in st.session_state["ask_history"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("sources"):
                with st.expander("Sources"):
                    for src in msg["sources"]:
                        st.markdown(f'<span class="src-chip">{src["filename"]} p.{src["page"]}</span>',
                                    unsafe_allow_html=True)

    question = st.chat_input("Ask a question…")
    if question:
        pasted_ctx = st.session_state.get("pasted_text", "").strip()
        st.session_state["ask_history"].append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)
        with st.chat_message("assistant"):
            with st.spinner("Thinking…"):
                body = {
                    "question": question,
                    "doc_id": _active_doc_id(),
                    "mode": mode,
                    "k": 5,
                    "conversation_history": [
                        {"role": m["role"], "content": m["content"]}
                        for m in st.session_state["ask_history"][:-1]
                    ][-6:],
                }
                if not body["doc_id"] and pasted_ctx:
                    body["context_override"] = pasted_ctx
                data, err = api_post("/api/ask", json=body)
            if err:
                st.error(err)
                st.session_state["ask_history"].pop()
            else:
                st.markdown(data["answer"])
                if data.get("sources"):
                    with st.expander("Sources"):
                        for src in data["sources"]:
                            st.markdown(f'<span class="src-chip">{src["filename"]} p.{src["page"]}</span>',
                                        unsafe_allow_html=True)
                st.session_state["ask_history"].append({
                    "role": "assistant",
                    "content": data["answer"],
                    "sources": data.get("sources", []),
                })

    if st.session_state["ask_history"] and st.button("🗑️ Clear chat"):
        st.session_state["ask_history"] = []
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# TAB: ELI10 Explain
# ─────────────────────────────────────────────────────────────────────────────
with tab_explain:
    _tab_head("ELI10 — Explain Like I'm 10", "Get simple, clear explanations with analogies.")
    default_topic = st.session_state.get("pasted_text", "")[:100] if not _active_doc_id() else ""
    topic = st.text_input("Topic or concept", value=default_topic,
                           placeholder="e.g. Photosynthesis, Newton's Laws")
    level = st.selectbox("Depth", ["eli5", "beginner", "intermediate"],
                          format_func=lambda x: {"eli5": "Very Simple (ELI5)",
                                                  "beginner": "Beginner",
                                                  "intermediate": "Intermediate"}[x])
    if st.button("Generate Explanation ✨", type="primary") and topic.strip():
        with st.spinner("Generating…"):
            data, err = api_post("/api/explain",
                                  json={"topic": topic.strip(),
                                        "doc_id": _active_doc_id(), "level": level})
        if err:
            st.error(err)
        else:
            st.markdown(f"""
<div style="background:#18181b;border:1px solid #27272a;border-radius:12px;padding:1.5rem;animation:fadeUp 0.4s both">
  <p style="font-size:15px;color:#d4d4d8;line-height:1.7">{data['explanation']}</p>
</div>""", unsafe_allow_html=True)
            if data.get("analogy"):
                st.info(f"💡 **Analogy:** {data['analogy']}")
            if data.get("key_points"):
                st.markdown("**Key Points:**")
                for pt in data["key_points"]:
                    st.markdown(f"- {pt}")


# ─────────────────────────────────────────────────────────────────────────────
# TAB: Quiz  (Kahoot-style — one question at a time, big tiles, live timer)
# ─────────────────────────────────────────────────────────────────────────────

# Kahoot tile colours — cycles through 4 per question
_KAHOOT_COLORS = [
    ("#e21b3c", "#ff3355"),   # red
    ("#1368ce", "#2196f3"),   # blue
    ("#26890c", "#2ecc71"),   # green
    ("#d89e00", "#f9a825"),   # yellow
]
_KAHOOT_SHAPES = ["▲", "◆", "●", "■"]

_KAHOOT_CSS = """
<style>
.kh-header{background:linear-gradient(135deg,#6366f1 0%,#8b5cf6 100%);
  border-radius:16px;padding:1.5rem 2rem;margin-bottom:1.5rem;text-align:center}
.kh-header h2{color:#fff;font-size:1.5rem;font-weight:800;margin:0 0 .25rem}
.kh-header p{color:rgba(255,255,255,.75);font-size:.9rem;margin:0}
.kh-timer{font-size:3.5rem;font-weight:900;text-align:center;
  color:#fafafa;line-height:1;margin:.5rem 0}
.kh-timer-warn{color:#f59e0b !important}
.kh-timer-danger{color:#ef4444 !important;animation:pulse 0.6s infinite}
.kh-question{background:#18181b;border:2px solid #3f3f46;border-radius:16px;
  padding:1.5rem 2rem;margin:1rem 0 1.5rem;text-align:center}
.kh-question p{font-size:1.25rem;font-weight:700;color:#fafafa;margin:0;line-height:1.5}
.kh-tile{border-radius:14px;padding:1.1rem 1rem;cursor:pointer;
  display:flex;align-items:center;gap:.75rem;transition:transform .15s,filter .15s;
  border:none;width:100%;text-align:left;margin-bottom:.5rem}
.kh-tile:hover{transform:scale(1.03);filter:brightness(1.12)}
.kh-tile span.shape{font-size:1.4rem;flex-shrink:0}
.kh-tile span.label{font-size:1rem;font-weight:700;color:#fff;line-height:1.3}
.kh-tile-correct{outline:4px solid #22c55e !important;filter:brightness(1.15)}
.kh-tile-wrong{filter:brightness(0.45) !important}
.kh-feedback-correct{background:#052e16;border:2px solid #22c55e;border-radius:12px;
  padding:1rem 1.5rem;text-align:center;color:#22c55e;font-size:1.1rem;font-weight:700}
.kh-feedback-wrong{background:#2d0a0a;border:2px solid #ef4444;border-radius:12px;
  padding:1rem 1.5rem;text-align:center;color:#ef4444;font-size:1.1rem;font-weight:700}
.kh-progress-track{background:#27272a;border-radius:99px;height:8px;margin:.75rem 0}
.kh-progress-fill{background:linear-gradient(90deg,#6366f1,#8b5cf6);
  border-radius:99px;height:8px;transition:width .4s ease}
.kh-result-card{background:#18181b;border:2px solid #3f3f46;border-radius:20px;
  padding:2.5rem 2rem;text-align:center;margin:1rem 0}
.kh-grade{display:inline-block;width:80px;height:80px;border-radius:50%;
  font-size:2rem;font-weight:900;line-height:80px;margin-bottom:1rem}
.kh-grade-s{background:#ffd700;color:#09090b}
.kh-grade-a{background:#22c55e;color:#fff}
.kh-grade-b{background:#6366f1;color:#fff}
.kh-grade-c{background:#f59e0b;color:#fff}
.kh-grade-d{background:#ef4444;color:#fff}
.kh-streak{background:#1e1b4b;border-radius:10px;padding:.5rem 1rem;
  display:inline-block;font-size:.85rem;color:#a5b4fc;font-weight:600;margin-top:.5rem}
.kh-review-item{border-radius:12px;padding:.875rem 1.25rem;margin:.4rem 0;
  display:flex;align-items:flex-start;gap:.75rem}
.kh-review-correct{background:#052e16;border:1px solid #22c55e}
.kh-review-wrong{background:#2d0a0a;border:1px solid #ef4444}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
@keyframes bounceIn{0%{transform:scale(0.5);opacity:0}70%{transform:scale(1.1)}100%{transform:scale(1);opacity:1}}
.bounce-in{animation:bounceIn 0.5s both}
</style>
"""

with tab_quiz:
    st.markdown(_KAHOOT_CSS, unsafe_allow_html=True)

    # ── State init ────────────────────────────────────────────────────────────
    _ss("quiz_data",        None)
    _ss("quiz_answers",     {})
    _ss("quiz_result",      None)
    _ss("quiz_start_ts",    None)
    _ss("kh_q_index",       0)          # current question index
    _ss("kh_q_start_ts",    None)       # per-question timer start
    _ss("kh_chosen",        None)       # chosen option index for current Q
    _ss("kh_revealed",      False)      # whether answer is revealed
    _ss("kh_streak",        0)          # consecutive correct answers
    _ss("kh_q_time_limit",  20)         # seconds per question

    # ── SCREEN 1: Setup form ──────────────────────────────────────────────────
    if st.session_state["quiz_data"] is None and st.session_state["quiz_result"] is None:
        st.markdown("""
<div class="kh-header">
  <h2>🎯 Kahoot-Style Quiz</h2>
  <p>One question at a time · Timed · Instant feedback</p>
</div>""", unsafe_allow_html=True)

        default_topic_q = st.session_state.get("pasted_text", "")[:80] if not _active_doc_id() else ""
        with st.form("quiz_form"):
            topic_q    = st.text_input("Topic (optional — leave blank to use active document)", value=default_topic_q)
            c1, c2, c3 = st.columns(3)
            num_q      = c1.slider("Questions", 3, 10, 5)   # max=10 matches schema cap
            difficulty = c2.selectbox("Difficulty", ["easy", "medium", "hard", "mixed"])
            time_limit = c3.selectbox("Seconds/Question", [10, 15, 20, 30, 45], index=2)
            go = st.form_submit_button("🚀 Start Quiz!", type="primary", use_container_width=True)
        if go:
            with st.spinner("Generating quiz…"):
                data, err = api_post("/api/generate-quiz",
                                      json={"doc_id": _active_doc_id(),
                                            "topic": topic_q.strip() or "",
                                            "num_questions": num_q,
                                            "difficulty": difficulty})
            if err:
                st.error(err)
            else:
                st.session_state.update({
                    "quiz_data": data, "quiz_answers": {},
                    "quiz_result": None, "quiz_start_ts": time.time(),
                    "kh_q_index": 0, "kh_q_start_ts": time.time(),
                    "kh_chosen": None, "kh_revealed": False,
                    "kh_streak": 0, "kh_q_time_limit": time_limit,
                })
                st.rerun()

    # ── SCREEN 3: Results ─────────────────────────────────────────────────────
    elif st.session_state["quiz_result"] is not None:
        res   = st.session_state["quiz_result"]
        pct   = res.get("percentage", 0)
        grade = res.get("grade", "?")
        gcls  = {"S":"kh-grade-s","A":"kh-grade-a","B":"kh-grade-b",
                 "C":"kh-grade-c","D":"kh-grade-d"}.get(grade, "kh-grade-b")
        confetti(pct >= 70)

        # Score card
        if pct >= 90:
            verdict, verdict_color = "Outstanding! 🔥", "#ffd700"
        elif pct >= 70:
            verdict, verdict_color = "Great job! 🎉", "#22c55e"
        elif pct >= 50:
            verdict, verdict_color = "Good effort! 💪", "#6366f1"
        else:
            verdict, verdict_color = "Keep practising! 📚", "#f59e0b"

        st.markdown(f"""
<div class="kh-result-card bounce-in">
  <div class="kh-grade {gcls}">{grade}</div>
  <p style="font-size:2rem;font-weight:900;color:#fafafa;margin:.25rem 0">{pct:.0f}%</p>
  <p style="font-size:1rem;color:{verdict_color};font-weight:700;margin:0">{verdict}</p>
  <p style="font-size:.875rem;color:#71717a;margin:.5rem 0 0">
    {res['score']} / {res['total']} correct &nbsp;·&nbsp; {res.get('time_taken',0):.0f}s total
  </p>
  <div class="kh-streak">🔥 Best streak this quiz: {st.session_state['kh_streak']} in a row</div>
</div>""", unsafe_allow_html=True)

        # Per-question review
        st.markdown("### 📋 Answer Review")
        for d in res.get("details", []):
            icon   = "✅" if d["is_correct"] else "❌"
            cls    = "kh-review-correct" if d["is_correct"] else "kh-review-wrong"
            colour = "#22c55e" if d["is_correct"] else "#ef4444"
            st.markdown(f"""
<div class="kh-review-item {cls}">
  <span style="font-size:1.25rem">{icon}</span>
  <div>
    <p style="margin:0;font-size:.9rem;font-weight:700;color:{colour}">{d['question']}</p>
    {f'<p style="margin:.25rem 0 0;font-size:.8rem;color:#a1a1aa">{d["explanation"]}</p>' if d.get("explanation") else ""}
  </div>
</div>""", unsafe_allow_html=True)

        st.markdown("")
        if st.button("🔄 Play Again", type="primary", use_container_width=True):
            st.session_state.update({
                "quiz_data": None, "quiz_answers": {}, "quiz_result": None,
                "kh_q_index": 0, "kh_chosen": None, "kh_revealed": False, "kh_streak": 0,
            })
            st.rerun()

    # ── SCREEN 2: Active quiz — one question at a time ────────────────────────
    else:
        quiz      = st.session_state["quiz_data"]
        questions = quiz.get("questions", [])
        qi        = st.session_state["kh_q_index"]
        answers   = st.session_state["quiz_answers"]
        time_limit = st.session_state["kh_q_time_limit"]

        if qi >= len(questions):
            # All answered — auto-submit
            elapsed = time.time() - (st.session_state["quiz_start_ts"] or time.time())
            with st.spinner("Grading…"):
                data, err = api_post("/api/quiz/submit",
                                      json={"quiz_id": quiz["quiz_id"],
                                            "answers": answers, "time_taken": int(elapsed)})
            if err:
                st.error(err)
            else:
                st.session_state["quiz_result"] = data
                st.rerun()
        else:
            q       = questions[qi]
            options = q.get("options", [])
            chosen  = st.session_state["kh_chosen"]
            revealed = st.session_state["kh_revealed"]
            correct_idx = q.get("correct_index", 0)   # field is correct_index not correct_answer

            # ── Top bar: progress + question counter ──────────────────────────
            progress_pct = qi / len(questions) * 100
            st.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.25rem">
  <span style="font-size:.8rem;color:#71717a;font-weight:600">
    Question {qi+1} of {len(questions)}
  </span>
  <span style="font-size:.8rem;color:#71717a">
    🔥 Streak: {st.session_state['kh_streak']}
  </span>
</div>
<div class="kh-progress-track">
  <div class="kh-progress-fill" style="width:{progress_pct}%"></div>
</div>""", unsafe_allow_html=True)

            # ── Timer ─────────────────────────────────────────────────────────
            if st.session_state["kh_q_start_ts"] is None:
                st.session_state["kh_q_start_ts"] = time.time()
            elapsed_q = time.time() - st.session_state["kh_q_start_ts"]
            remaining = max(0, time_limit - int(elapsed_q))
            timer_cls = "kh-timer-danger" if remaining <= 5 else ("kh-timer-warn" if remaining <= 10 else "")
            st.markdown(f'<div class="kh-timer {timer_cls}">{remaining}s</div>', unsafe_allow_html=True)

            # ── Question box ──────────────────────────────────────────────────
            st.markdown(f"""
<div class="kh-question">
  <p>{q['question']}</p>
</div>""", unsafe_allow_html=True)

            # ── Auto-reveal if timer hits 0 ───────────────────────────────────
            if remaining == 0 and not revealed:
                st.session_state["kh_revealed"] = True
                if chosen is None:
                    st.session_state["kh_chosen"] = -1   # timed out — no pick
                st.rerun()

            # ── Answer tiles (2×2 grid) ───────────────────────────────────────
            tile_rows = [options[i:i+2] for i in range(0, len(options), 2)]
            for row_idx, row in enumerate(tile_rows):
                cols = st.columns(len(row))
                for col_idx, (col, opt) in enumerate(zip(cols, row)):
                    opt_idx = row_idx * 2 + col_idx
                    bg, bg2 = _KAHOOT_COLORS[opt_idx % 4]
                    shape   = _KAHOOT_SHAPES[opt_idx % 4]

                    # After reveal: dim wrong tiles, highlight correct
                    if revealed:
                        if opt_idx == correct_idx:
                            extra_style = f"outline:4px solid #22c55e;"
                        elif opt_idx == chosen:
                            extra_style = "filter:brightness(0.4);"
                        else:
                            extra_style = "filter:brightness(0.35);"
                    else:
                        extra_style = ""

                    with col:
                        st.markdown(f"""
<div style="background:linear-gradient(135deg,{bg},{bg2});border-radius:14px;
     padding:1.1rem 1rem;display:flex;align-items:center;gap:.75rem;
     margin-bottom:.5rem;{extra_style}">
  <span style="font-size:1.4rem">{shape}</span>
  <span style="font-size:1rem;font-weight:700;color:#fff;line-height:1.3">{opt}</span>
</div>""", unsafe_allow_html=True)
                        if not revealed:
                            if col.button(f"Choose", key=f"kh_{qi}_{opt_idx}",
                                          use_container_width=True):
                                st.session_state["kh_chosen"]   = opt_idx
                                st.session_state["kh_revealed"]  = True
                                if opt_idx == correct_idx:
                                    st.session_state["kh_streak"] += 1
                                else:
                                    st.session_state["kh_streak"]  = 0
                                # Record the 0-based index the user chose (or -1 for timeout)
                                answers[q["id"]] = opt_idx
                                st.session_state["quiz_answers"] = answers
                                st.rerun()

            # ── Instant feedback after answer ─────────────────────────────────
            if revealed:
                if chosen == -1:
                    st.markdown('<div class="kh-feedback-wrong">⏰ Time\'s up! Moving on…</div>',
                                unsafe_allow_html=True)
                elif chosen == correct_idx:
                    st.markdown('<div class="kh-feedback-correct">✅ Correct! Nice one! 🔥</div>',
                                unsafe_allow_html=True)
                else:
                    correct_text = options[correct_idx] if correct_idx < len(options) else "?"
                    st.markdown(f'<div class="kh-feedback-wrong">❌ Wrong! Correct answer: <strong>{correct_text}</strong></div>',
                                unsafe_allow_html=True)
                if q.get("explanation"):
                    st.info(f"💡 {q['explanation']}")

                st.markdown("")
                col_next, col_quit = st.columns([3, 1])
                with col_next:
                    next_label = "Next Question ▶" if qi + 1 < len(questions) else "🏁 See Results"
                    if st.button(next_label, type="primary", use_container_width=True,
                                 key=f"next_{qi}"):
                        # Ensure unanswered (timed-out) questions have a placeholder
                        if q["id"] not in answers:
                            answers[q["id"]] = -1
                            st.session_state["quiz_answers"] = answers
                        st.session_state.update({
                            "kh_q_index":    qi + 1,
                            "kh_q_start_ts": time.time(),
                            "kh_chosen":     None,
                            "kh_revealed":   False,
                        })
                        st.rerun()
                with col_quit:
                    if st.button("Quit", key=f"quit_{qi}"):
                        st.session_state.update({
                            "quiz_data": None, "quiz_answers": {}, "quiz_result": None,
                            "kh_q_index": 0, "kh_chosen": None, "kh_revealed": False,
                        })
                        st.rerun()

            # ── Auto-refresh while timer is running (no answer yet) ───────────
            if not revealed and remaining > 0:
                time.sleep(1)
                st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# TAB: Revision Planner
# ─────────────────────────────────────────────────────────────────────────────
with tab_planner:
    _tab_head("Revision Planner", "Personalised study schedule from your exam date.")
    _ss("plan_data", None)
    if st.session_state["plan_data"] is None:
        default_syllabus = st.session_state.get("pasted_text", "") if not _active_doc_id() else ""
        with st.form("planner_form"):
            exam_date   = st.date_input("Exam date")
            daily_hours = st.slider("Daily study hours", 0.5, 8.0, 2.0, step=0.5)
            syllabus    = st.text_area("Syllabus / topics (optional)",
                                        value=default_syllabus, height=100)
            if st.form_submit_button("Generate Plan 📅", type="primary"):
                with st.spinner("Building personalised plan…"):
                    data, err = api_post("/api/generate-plan",
                                          json={"exam_date": exam_date.isoformat(),
                                                "daily_hours": daily_hours,
                                                "syllabus_text": syllabus.strip() or None,
                                                "doc_id": _active_doc_id()})
                if err:
                    st.error(err)
                else:
                    st.session_state["plan_data"] = data
                    st.rerun()
    else:
        resp  = st.session_state["plan_data"]
        stats = resp.get("stats", {})
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Days to Exam",  stats.get("days_to_exam", "?"))
        c2.metric("Study Days",    stats.get("study_days", "?"))
        c3.metric("Total Hours",   f"{stats.get('total_study_mins', 0) // 60}h")
        c4.metric("Topics",        stats.get("topics_covered", "?"))
        if resp.get("summary"):
            st.info(resp["summary"])
        for task in resp.get("plan", []):
            with st.expander(f"{task.get('session_type','').title()} · {task.get('day_label', task.get('date',''))} · {task.get('topic','')}"):
                ca, cb, cc = st.columns(3)
                ca.metric("Duration",  f"{task.get('duration_mins', 0)} min")
                cb.metric("Technique", task.get("technique", "—"))
                cc.metric("Priority",  task.get("priority", "—"))
                if task.get("notes"):
                    st.caption(task["notes"])
        if st.button("🔄 New Plan"):
            st.session_state["plan_data"] = None
            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# TAB: Flashcards
# ─────────────────────────────────────────────────────────────────────────────
with tab_fc:
    _tab_head("Flashcards", "AI-generated flip cards for spaced-repetition practice.")
    _ss("fc_cards", None); _ss("fc_index", 0); _ss("fc_flipped", False)

    if st.session_state["fc_cards"] is None:
        if not _active_doc_id():
            st.warning("⚠️ Please upload a document and select it from the sidebar before generating flashcards.")
        default_topic_fc = st.session_state.get("pasted_text", "")[:80] if not _active_doc_id() else ""
        with st.form("fc_form"):
            topic_fc = st.text_input("Topic (optional)", value=default_topic_fc)
            num_fc   = st.slider("Number of cards", 3, 20, 8)
            if st.form_submit_button("Generate Cards 🃏", type="primary"):
                if not _active_doc_id():
                    st.error("⚠️ No document selected. Upload one in the Study Material tab first.")
                    st.stop()
                with st.spinner("Generating flashcards…"):
                    data, err = api_post("/api/flashcards/generate",
                                          json={"doc_id": _active_doc_id(),
                                                "topic": topic_fc.strip() or "",
                                                "num_cards": num_fc})
                if err:
                    st.error(err)
                else:
                    cards = data.get("cards", data.get("flashcards", []))
                    if cards:
                        st.session_state.update({"fc_cards": cards, "fc_index": 0, "fc_flipped": False})
                        st.rerun()
                    else:
                        st.warning("No cards returned.")
    else:
        cards   = st.session_state["fc_cards"]
        idx     = st.session_state["fc_index"]
        flipped = st.session_state["fc_flipped"]
        card    = cards[idx]
        st.progress((idx + 1) / len(cards), text=f"Card {idx + 1}/{len(cards)}")
        front_text = card.get("front", card.get("question", ""))
        answer_html = (
            f'<p class="flip-a">{card.get("back", card.get("answer", ""))}</p>'
            if flipped else '<p class="flip-hint">Click Flip to reveal answer</p>'
        )
        st.markdown(f'<div class="flip-card"><p class="flip-q">{front_text}</p>{answer_html}</div>',
                    unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        if c1.button("◀ Prev", disabled=idx == 0):
            st.session_state.update({"fc_index": idx - 1, "fc_flipped": False})
            st.rerun()
        if c2.button("🔄 Flip"):
            st.session_state["fc_flipped"] = not flipped
            st.rerun()
        if c3.button("Next ▶", disabled=idx >= len(cards) - 1):
            st.session_state.update({"fc_index": idx + 1, "fc_flipped": False})
            st.rerun()
        if c4.button("🔀 Shuffle"):
            random.shuffle(cards)
            st.session_state.update({"fc_cards": cards, "fc_index": 0, "fc_flipped": False})
            st.rerun()
        if st.button("New Deck"):
            st.session_state.update({"fc_cards": None, "fc_index": 0, "fc_flipped": False})
            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# TAB: Feynman
# ─────────────────────────────────────────────────────────────────────────────
with tab_feynman:
    _tab_head("Feynman Technique", "Explain a concept in plain words — AI scores your understanding.")
    default_concept = st.session_state.get("pasted_text", "")[:80] if not _active_doc_id() else ""
    with st.form("feynman_form"):
        concept     = st.text_input("Concept", value=default_concept,
                                     placeholder="e.g. Photosynthesis")
        explanation = st.text_area("Your explanation (in your own words)", height=200)
        submitted_f = st.form_submit_button("Evaluate My Understanding ✅", type="primary")
    if submitted_f and concept.strip() and explanation.strip():
        with st.spinner("Evaluating…"):
            data, err = api_post("/api/feynman/evaluate",
                                  json={"concept": concept.strip(),
                                        "explanation": explanation.strip(),
                                        "doc_id": _active_doc_id()})
        if err:
            st.error(err)
        else:
            score = data.get("score", 0)
            grade = data.get("grade", "?")
            gcls  = {"S": "grade-s", "A": "grade-a", "B": "grade-b",
                     "C": "grade-c", "D": "grade-d"}.get(grade, "grade-b")
            st.markdown(f"""
<div style="display:flex;align-items:center;gap:1.5rem;margin-bottom:1rem;animation:scaleIn 0.5s both">
  <span class="{gcls}">{grade}</span>
  <div>
    <p style="font-size:26px;font-weight:800;color:#fafafa;margin:0">{score}/100</p>
    <p style="font-size:13px;color:#71717a;margin:0">Feynman Score</p>
  </div>
</div>""", unsafe_allow_html=True)
            st.progress(score / 100)
            col_s, col_g = st.columns(2)
            with col_s:
                if data.get("strengths"):
                    st.success("**Strengths**\n" + "\n".join(f"- {s}" for s in data["strengths"]))
            with col_g:
                if data.get("gaps"):
                    st.error("**Gaps to Fill**\n" + "\n".join(f"- {g}" for g in data["gaps"]))
            if data.get("coaching_tip"):
                st.info(f"💡 {data['coaching_tip']}")


# ─────────────────────────────────────────────────────────────────────────────
# TAB: Cheat Sheet
# ─────────────────────────────────────────────────────────────────────────────
with tab_cheat:
    _tab_head("Cheat Sheet", "One-page key-concept summary for your document.")
    doc_id = _active_doc_id()
    if not doc_id:
        st.warning("⚠️ Upload and select a document first (Study Material tab).")
    else:
        topic_cs = st.text_input("Focus topic (optional)", key="cs_topic")
        if st.button("Generate Cheat Sheet 📝", type="primary"):
            with st.spinner("Generating…"):
                try:
                    content = stream_sse("/api/cheatsheet",
                                         {"doc_id": doc_id, "topic": topic_cs.strip()})
                    st.markdown(content)
                    st.download_button("⬇️ Download (.md)", data=content,
                                        file_name="cheatsheet.md", mime="text/markdown")
                except Exception as e:
                    st.error(str(e))


# ─────────────────────────────────────────────────────────────────────────────
# TAB: Progress
# ─────────────────────────────────────────────────────────────────────────────
with tab_progress:
    _tab_head("Progress Dashboard", "Your study analytics — quizzes, Feynman, streaks.")

    # Allow user to force-refresh without reloading the whole page
    if st.button("🔄 Refresh Progress", key="refresh_progress"):
        st.session_state.pop("_progress_cache", None)

    if "_progress_cache" not in st.session_state:
        with st.spinner("Loading…"):
            _pdata, _perr = api_get("/api/progress/summary", timeout=30)
        st.session_state["_progress_cache"] = (_pdata, _perr)

    data, err = st.session_state["_progress_cache"]

    if err:
        st.error(err)
        st.session_state.pop("_progress_cache", None)  # don't cache errors
    elif data:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Quizzes",   data.get("total_quizzes", 0))
        c2.metric("Avg Score",       f"{data.get('avg_score_pct', 0):.0f}%")
        c3.metric("Best Score",      f"{data.get('best_score_pct', 0):.0f}%")
        c4.metric("Streak 🔥",       f"{data.get('current_streak_days', 0)}d")

        history = data.get("score_history", [])
        if history:
            st.divider()
            st.markdown('<p style="font-size:12px;font-weight:600;color:#a1a1aa;text-transform:uppercase;letter-spacing:.06em">Quiz History (newest first)</p>',
                        unsafe_allow_html=True)
            st.dataframe(
                # score_history is already newest-first from backend; show last 20
                [{"Date": h["date"][:10], "Topic": h["topic"],
                  "Score": f"{h['score']}/{h['total']}",
                  "%": f"{h['percentage']:.0f}%",
                  "Grade": h["grade"]}
                 for h in history[:20]],
                use_container_width=True,
                hide_index=True,
            )

        col_w, col_s = st.columns(2)
        with col_w:
            if data.get("weak_topics"):
                st.markdown('<p style="font-size:12px;font-weight:600;color:#ef4444;text-transform:uppercase">Weak Topics</p>',
                            unsafe_allow_html=True)
                for t in data["weak_topics"]:
                    st.progress(t["avg_pct"] / 100, text=f"{t['topic']} ({t['avg_pct']:.0f}%)")
        with col_s:
            if data.get("strong_topics"):
                st.markdown('<p style="font-size:12px;font-weight:600;color:#22c55e;text-transform:uppercase">Strong Topics</p>',
                            unsafe_allow_html=True)
                for t in data["strong_topics"]:
                    st.progress(t["avg_pct"] / 100, text=f"{t['topic']} ({t['avg_pct']:.0f}%)")

        # Flashcard & Feynman stats
        fc = data.get("flashcard_stats", {})
        feynman = data.get("feynman_history", [])
        if fc.get("total_sessions") or feynman:
            st.divider()
            cf1, cf2 = st.columns(2)
            if fc.get("total_sessions"):
                with cf1:
                    st.metric("Flashcard Sessions", fc.get("total_sessions", 0))
                    st.metric("Flashcards Studied", fc.get("total_cards", 0))
            if feynman:
                with cf2:
                    st.markdown('<p style="font-size:12px;font-weight:600;color:#a1a1aa;text-transform:uppercase;letter-spacing:.06em">Feynman History</p>',
                                unsafe_allow_html=True)
                    st.dataframe(
                        [{"Date": f["date"][:10], "Concept": f["concept"],
                          "Score": f["score"], "Grade": f["grade"]}
                         for f in feynman[:10]],
                        use_container_width=True,
                        hide_index=True,
                    )
    else:
        st.info("No quiz data yet — complete a quiz to see your progress here!")

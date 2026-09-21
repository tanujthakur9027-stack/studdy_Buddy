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

from core.styles import inject_global_css, heading, badge
from core.animations import page_enter, confetti
from core.auth_state import require_login
from core.api_client import api_get, api_post, api_request, stream_sse, BACKEND_URL


inject_global_css()
require_login()
page_enter()


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
        st.switch_page("pages/dashboard.py")
    if st.button("📋 Classes & Assignments"):
        st.switch_page("pages/classes.py")
    if st.button("👤 Profile"):
        st.switch_page("pages/profile.py")


# ── Page header ───────────────────────────────────────────────────────────────
heading("AI Study Tools", "Upload your material or paste text, then use any tool below.")

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
    heading("Ask AI — RAG Q&A", "Ask anything about your document or topic.")
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
    heading("ELI10 — Explain Like I'm 10", "Get simple, clear explanations with analogies.")
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
# TAB: Quiz
# ─────────────────────────────────────────────────────────────────────────────
with tab_quiz:
    heading("Quiz", "Timed multiple-choice quiz from your document or topic.")
    _ss("quiz_data", None); _ss("quiz_answers", {}); _ss("quiz_result", None); _ss("quiz_start_ts", None)

    if st.session_state["quiz_data"] is None and st.session_state["quiz_result"] is None:
        default_topic_q = st.session_state.get("pasted_text", "")[:80] if not _active_doc_id() else ""
        with st.form("quiz_form"):
            topic_q    = st.text_input("Topic (optional)", value=default_topic_q)
            num_q      = st.slider("Questions", 3, 15, 5)
            difficulty = st.selectbox("Difficulty", ["easy", "medium", "hard", "mixed"])
            if st.form_submit_button("🎯 Generate Quiz", type="primary"):
                with st.spinner("Generating quiz…"):
                    data, err = api_post("/api/generate-quiz",
                                          json={"doc_id": _active_doc_id(),
                                                "topic": topic_q.strip() or None,
                                                "num_questions": num_q,
                                                "difficulty": difficulty})
                if err:
                    st.error(err)
                else:
                    st.session_state.update({
                        "quiz_data": data, "quiz_answers": {},
                        "quiz_result": None, "quiz_start_ts": time.time()
                    })
                    st.rerun()

    elif st.session_state["quiz_result"] is not None:
        res = st.session_state["quiz_result"]
        pct = res.get("percentage", 0)
        grade = res.get("grade", "?")
        gcls = {"S": "grade-s", "A": "grade-a", "B": "grade-b", "C": "grade-c", "D": "grade-d"}.get(grade, "grade-b")
        confetti(pct >= 70)

        st.markdown(f"""
<div style="display:flex;align-items:center;gap:1.5rem;margin-bottom:1rem;animation:scaleIn 0.5s both">
  <span class="{gcls}">{grade}</span>
  <div>
    <p style="font-size:28px;font-weight:800;color:#fafafa;margin:0">{pct:.0f}%</p>
    <p style="font-size:13px;color:#71717a;margin:0">{res['score']}/{res['total']} correct · {res.get('time_taken',0):.0f}s</p>
  </div>
</div>""", unsafe_allow_html=True)

        with st.expander("📋 Review Answers", expanded=True):
            for d in res.get("details", []):
                colour = "#22c55e" if d["is_correct"] else "#ef4444"
                st.markdown(f'<p style="color:{colour};font-size:14px;font-weight:600">{"✓" if d["is_correct"] else "✗"} {d["question"]}</p>',
                            unsafe_allow_html=True)
                if d.get("explanation"):
                    st.caption(d["explanation"])
                st.divider()
        if st.button("🔄 New Quiz"):
            st.session_state.update({"quiz_data": None, "quiz_answers": {}, "quiz_result": None})
            st.rerun()

    else:
        quiz = st.session_state["quiz_data"]
        questions = quiz.get("questions", [])
        answers   = st.session_state["quiz_answers"]
        st.progress(len(answers) / len(questions) if questions else 0,
                    text=f"{len(answers)}/{len(questions)} answered")
        for i, q in enumerate(questions):
            with st.container(border=True):
                st.markdown(f"**Q{i+1}. {q['question']}**")
                chosen = st.radio("", range(len(q.get("options", []))),
                                  format_func=lambda j, opts=q.get("options", []): opts[j],
                                  key=f"q_{q['id']}", index=None)
                if chosen is not None:
                    answers[q["id"]] = chosen
                    st.session_state["quiz_answers"] = answers
        col_sub, col_dis = st.columns(2)
        with col_sub:
            if st.button("✅ Submit Quiz", type="primary",
                         disabled=len(answers) != len(questions)):
                elapsed = time.time() - (st.session_state["quiz_start_ts"] or time.time())
                with st.spinner("Grading…"):
                    data, err = api_post("/quiz/submit",
                                          json={"quiz_id": quiz["quiz_id"],
                                                "answers": answers, "time_taken": int(elapsed)})
                if err:
                    st.error(err)
                else:
                    st.session_state["quiz_result"] = data
                    st.rerun()
        with col_dis:
            if st.button("Discard"):
                st.session_state.update({"quiz_data": None, "quiz_answers": {}})
                st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# TAB: Revision Planner
# ─────────────────────────────────────────────────────────────────────────────
with tab_planner:
    heading("Revision Planner", "Personalised study schedule from your exam date.")
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
    heading("Flashcards", "AI-generated flip cards for spaced-repetition practice.")
    _ss("fc_cards", None); _ss("fc_index", 0); _ss("fc_flipped", False)

    if st.session_state["fc_cards"] is None:
        default_topic_fc = st.session_state.get("pasted_text", "")[:80] if not _active_doc_id() else ""
        with st.form("fc_form"):
            topic_fc = st.text_input("Topic (optional)", value=default_topic_fc)
            num_fc   = st.slider("Number of cards", 3, 20, 8)
            if st.form_submit_button("Generate Cards 🃏", type="primary"):
                with st.spinner("Generating flashcards…"):
                    data, err = api_post("/api/flashcards/generate",
                                          json={"doc_id": _active_doc_id(),
                                                "topic": topic_fc.strip() or None,
                                                "count": num_fc})
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
    heading("Feynman Technique", "Explain a concept in plain words — AI scores your understanding.")
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
    heading("Cheat Sheet", "One-page key-concept summary for your document.")
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
    heading("Progress Dashboard", "Your study analytics — quizzes, Feynman, streaks.")
    with st.spinner("Loading…"):
        data, err = api_get("/api/progress/summary", timeout=30)
    if err:
        st.error(err)
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Quizzes",   data.get("total_quizzes", 0))
        c2.metric("Avg Score",       f"{data.get('avg_score_pct', 0):.0f}%")
        c3.metric("Best Score",      f"{data.get('best_score_pct', 0):.0f}%")
        c4.metric("Streak 🔥",       f"{data.get('current_streak_days', 0)}d")

        if data.get("score_history"):
            st.divider()
            st.dataframe(
                [{"Date": h["date"][:10], "Topic": h["topic"],
                  "Score": f"{h['score']}/{h['total']}", "Grade": h["grade"]}
                 for h in data["score_history"][-20:]],
                use_container_width=True,
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

"""
pages/admin.py — Admin Panel (restricted to role=admin)

Tabs: Students · Classes · Assignments · Submissions · Marks · Timetable · Announcements
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

from core.styles import inject_global_css, badge, card
from core.animations import page_enter
from core.auth_state import require_login, current_user, is_admin
from core.api_client import api_get, api_post, api_patch, api_delete, api_request, BACKEND_URL


inject_global_css()
require_login()
page_enter()

if not is_admin():
    st.error("🔒 Admin access required.")
    st.stop()

# helpers
def _h(t): st.markdown(f'<p style="font-size:1rem;font-weight:700;color:#fafafa;margin:.75rem 0 .5rem">{t}</p>', unsafe_allow_html=True)

st.markdown("""
<div style="margin-bottom:1.5rem;animation:fadeUp .4s both">
  <h1 style="font-size:1.6rem;font-weight:800;color:#fafafa;margin:0 0 .25rem;letter-spacing:-.03em">
    ⚙️ Admin Panel
  </h1>
  <p style="font-size:.875rem;color:#71717a;margin:0">Manage students, classes, assignments, marks and timetable.</p>
</div>""", unsafe_allow_html=True)

(students_tab, classes_tab, assignments_tab,
 submissions_tab, marks_tab, timetable_tab, announcements_tab) = st.tabs([
    "👨‍🎓 Students", "🏛️ Classes", "📋 Assignments",
    "✅ Submissions", "📊 Marks", "📅 Timetable", "📢 Announcements",
])


# ── Students ──────────────────────────────────────────────────────────────────
with students_tab:
    _h("👨‍🎓 Registered Students")
    search = st.text_input("Search by name, email or student ID", key="admin_student_search")
    data, err = api_get(f"/api/admin/students?search={search}" if search else "/api/admin/students", timeout=15)
    if err:
        st.error(err)
    else:
        students = data or []
        st.caption(f"{len(students)} student(s)")
        for s in students:
            with st.expander(f"{'🟢' if s.get('is_active') else '🔴'} {s.get('full_name','?')} — {s.get('student_id','?')}", expanded=False):
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Email",    s.get("email", "?"))
                c2.metric("Course",   s.get("course", "—") or "—")
                c3.metric("Semester", s.get("semester", "—") or "—")
                c4.metric("Section",  s.get("section", "—") or "—")
                col_a, col_b = st.columns([3, 1])
                with col_b:
                    btn_label = "Deactivate" if s.get("is_active") else "Activate"
                    if st.button(btn_label, key=f"toggle_{s['id']}"):
                        api_patch(f"/api/admin/students/{s['id']}/status",
                                  json={"is_active": not s.get("is_active")})
                        st.rerun()


# ── Classes ───────────────────────────────────────────────────────────────────
with classes_tab:
    _h("🏛️ Classes, Sections &amp; Subjects")
    classes_data,  _ = api_get("/api/admin/classes",  timeout=10)
    sections_data, _ = api_get("/api/admin/sections", timeout=10)
    subjects_data, _ = api_get("/api/admin/subjects", timeout=10)
    classes   = classes_data  or []
    sections  = sections_data or []
    subjects  = subjects_data or []

    col1, col2, col3 = st.columns(3)
    with col1:
        with st.form("new_class"):
            st.markdown("**New Class**")
            cls_name   = st.text_input("Class Name", placeholder="B.Tech CSE Year 2")
            cls_course = st.text_input("Course",     placeholder="B.Tech")
            if st.form_submit_button("Create Class", type="primary"):
                if cls_name:
                    _, err = api_post("/api/admin/classes", json={"name": cls_name, "course": cls_course})
                    if err: st.error(err)
                    else: st.success("Created!"); st.rerun()
    with col2:
        with st.form("new_section"):
            st.markdown("**New Section**")
            sec_cls  = st.selectbox("Class", [c["id"] for c in classes],
                                    format_func=lambda i: next((c["name"] for c in classes if c["id"]==i),i), key="sec_cls")
            sec_name = st.text_input("Section Name", placeholder="A")
            if st.form_submit_button("Create Section", type="primary"):
                if sec_name and sec_cls:
                    _, err = api_post("/api/admin/sections", json={"name": sec_name, "class_id": sec_cls})
                    if err: st.error(err)
                    else: st.success("Created!"); st.rerun()
    with col3:
        with st.form("new_subject"):
            st.markdown("**New Subject**")
            sub_cls  = st.selectbox("Class", [c["id"] for c in classes],
                                    format_func=lambda i: next((c["name"] for c in classes if c["id"]==i),i), key="sub_cls")
            sub_name = st.text_input("Subject Name", placeholder="Data Structures")
            sub_code = st.text_input("Code", placeholder="CS301")
            if st.form_submit_button("Create Subject", type="primary"):
                if sub_name and sub_cls:
                    _, err = api_post("/api/admin/subjects", json={"name": sub_name, "code": sub_code, "class_id": sub_cls})
                    if err: st.error(err)
                    else: st.success("Created!"); st.rerun()

    st.divider()
    for cls in classes:
        cls_sections = [s for s in sections if s["class_id"] == cls["id"]]
        cls_subjects  = [s for s in subjects  if s["class_id"] == cls["id"]]
        with st.expander(f"📁 {cls['name']} · {len(cls_sections)} sections · {len(cls_subjects)} subjects"):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Sections**")
                for sec in cls_sections:
                    ca, cb = st.columns([3,1])
                    ca.markdown(f"<span style='color:#d4d4d8'>{sec['name']}</span>", unsafe_allow_html=True)
                    if cb.button("Del", key=f"delsec_{sec['id']}"):
                        api_delete(f"/api/admin/sections/{sec['id']}"); st.rerun()
            with c2:
                st.markdown("**Subjects**")
                for sub in cls_subjects:
                    ca, cb = st.columns([3,1])
                    ca.markdown(f"<span style='color:#d4d4d8'>{sub['name']}</span><span style='color:#52525b;font-size:11px'> {sub.get('code','')}</span>",
                                unsafe_allow_html=True)
                    if cb.button("Del", key=f"delsub_{sub['id']}"):
                        api_delete(f"/api/admin/subjects/{sub['id']}"); st.rerun()


# ── Assignments ───────────────────────────────────────────────────────────────
with assignments_tab:
    _h("📋 Manage Assignments")
    classes_data, _ = api_get("/api/admin/classes",  timeout=10)
    subjects_data, _ = api_get("/api/admin/subjects", timeout=10)
    classes  = classes_data  or []
    subjects = subjects_data or []
    with st.expander("➕ Create New Assignment", expanded=False):
        with st.form("create_assignment"):
            title   = st.text_input("Title *")
            c1, c2 = st.columns(2)
            cls_id  = c1.selectbox("Class *", [c["id"] for c in classes],
                                   format_func=lambda i: next((c["name"] for c in classes if c["id"]==i),i))
            sub_id  = c2.selectbox("Subject *", [s["id"] for s in subjects],
                                   format_func=lambda i: next((s["name"] for s in subjects if s["id"]==i),i))
            desc    = st.text_area("Description", height=80)
            instr   = st.text_area("Instructions", height=80)
            c3, c4, c5 = st.columns(3)
            due_date   = c3.date_input("Due Date")
            due_time   = c4.text_input("Due Time", value="23:59")
            max_marks  = c5.number_input("Max Marks", value=100, min_value=1)
            file       = st.file_uploader("Attach file", type=["pdf","docx","pptx","zip"])
            submit_a   = st.form_submit_button("Create Assignment", type="primary")
        if submit_a and title and cls_id and sub_id:
            files_data = {"file": (file.name, file.getvalue(), file.type)} if file else None
            form_data  = {"title": title, "class_id": cls_id, "subject_id": sub_id,
                           "description": desc, "instructions": instr,
                           "due_date": str(due_date), "due_time": due_time, "max_marks": str(max_marks)}
            _, err = api_request("POST", "/api/admin/assignments", timeout=30, data=form_data, files=files_data)
            if err: st.error(err)
            else: st.success("Assignment created!"); st.rerun()

    data, err = api_get("/api/admin/assignments", timeout=15)
    if err: st.error(err)
    else:
        for a in (data or []):
            b = badge("Published", "green") if a.get("is_published") else badge("Draft", "yellow")
            col_a, col_pub, col_del = st.columns([5, 1, 1])
            with col_a:
                card(f"""
<p style="margin:0;font-size:14px;font-weight:600;color:#fafafa">{a['title']} {b}</p>
<p style="margin:3px 0 0;font-size:12px;color:#71717a">Due: {a.get('due_date','?')} · Max: {a.get('max_marks','?')}</p>""")
            with col_pub:
                if not a.get("is_published"):
                    if st.button("Publish", key=f"pub_{a['id']}"):
                        api_post(f"/api/admin/assignments/{a['id']}/publish")
                        st.rerun()
            with col_del:
                if st.button("Delete", key=f"del_a_{a['id']}"):
                    api_delete(f"/api/admin/assignments/{a['id']}"); st.rerun()


# ── Submissions ───────────────────────────────────────────────────────────────
with submissions_tab:
    _h("✅ Assignment Submissions")
    assignments_data, _ = api_get("/api/admin/assignments", timeout=10)
    assignment_list = assignments_data or []
    sel_asgn = st.selectbox("Select Assignment",
                             ["All"] + [a["id"] for a in assignment_list],
                             format_func=lambda i: "All Assignments" if i == "All" else
                             next((a["title"] for a in assignment_list if a["id"]==i), i))
    params = f"?assignment_id={sel_asgn}" if sel_asgn != "All" else ""
    data, err = api_get(f"/api/admin/submissions{params}", timeout=15)
    if err: st.error(err)
    else:
        subs = data or []
        st.caption(f"{len(subs)} submission(s)")
        for sub in subs:
            with st.expander(f"{'✅' if sub.get('is_evaluated') else '📤'} {sub.get('student_name','?')} — {sub.get('status','?').title()}", expanded=False):
                c1, c2, c3 = st.columns(3)
                c1.metric("Student",   sub.get("student_name","?"))
                c2.metric("Submitted", sub.get("submitted_at","?")[:10])
                c3.metric("Marks",     f"{sub.get('marks_obtained','—')}" if sub.get('is_evaluated') else "Not graded")
                if sub.get("notes"):  st.caption(f"Notes: {sub['notes']}")
                if sub.get("file_url"):
                    st.markdown(f'[📎 Download Submission]({BACKEND_URL}{sub["file_url"]})')
                max_m = next((a["max_marks"] for a in assignment_list if a["id"]==sub.get("assignment_id")), 100)
                with st.form(f"grade_{sub['id']}"):
                    g_marks    = st.number_input("Marks", min_value=0.0, max_value=float(max_m),
                                                  value=float(sub.get("marks_obtained") or 0), step=0.5)
                    g_feedback = st.text_area("Feedback", value=sub.get("feedback",""), height=60)
                    if st.form_submit_button("Save Grade", type="primary"):
                        _, err = api_patch(f"/api/admin/submissions/{sub['id']}/grade",
                                           json={"marks_obtained": g_marks, "feedback": g_feedback})
                        if err: st.error(err)
                        else: st.success("Graded!"); st.rerun()


# ── Marks ─────────────────────────────────────────────────────────────────────
with marks_tab:
    _h("📊 Marks Management")
    subjects_data, _ = api_get("/api/admin/subjects", timeout=10)
    subjects = subjects_data or []
    sel_sub = st.selectbox("Select Subject", [s["id"] for s in subjects],
                            format_func=lambda i: next((s["name"] for s in subjects if s["id"]==i),i),
                            key="marks_sub_sel")
    if sel_sub:
        cats_data, _ = api_get(f"/api/admin/assessment-categories?subject_id={sel_sub}", timeout=10)
        cats = cats_data or []
        with st.expander("➕ Add Assessment Category"):
            with st.form("new_cat"):
                c1, c2, c3 = st.columns(3)
                cat_name   = c1.text_input("Name", placeholder="Mid-Term")
                cat_max    = c2.number_input("Max Marks", value=50, min_value=1)
                cat_weight = c3.number_input("Weightage %", value=20, min_value=1, max_value=100)
                if st.form_submit_button("Create", type="primary"):
                    _, err = api_post("/api/admin/assessment-categories",
                                      json={"name": cat_name, "subject_id": sel_sub,
                                            "max_marks": cat_max, "weightage": cat_weight})
                    if err: st.error(err)
                    else: st.success("Created!"); st.rerun()

        if cats:
            sel_cat = st.selectbox("Select Category",
                                    [c["id"] for c in cats],
                                    format_func=lambda i: next((f"{c['name']} (max:{c['max_marks']})" for c in cats if c["id"]==i),i))
            cat_obj = next((c for c in cats if c["id"] == sel_cat), None)
            students_data, _ = api_get("/api/admin/students", timeout=10)
            students = students_data or []
            if students and cat_obj:
                report_data, _ = api_get(f"/api/admin/marks/report?subject_id={sel_sub}", timeout=10)
                report = report_data or []
                with st.form("enter_marks_form"):
                    entries = []
                    for s in students:
                        existing = next((r for r in report if r.get("student_id")==s["id"] and r.get("category")==cat_obj["name"]), None)
                        col1, col2, col3 = st.columns([3, 2, 2])
                        col1.markdown(f'<p style="margin-top:.85rem;font-size:13px;color:#d4d4d8">{s["full_name"]}</p>', unsafe_allow_html=True)
                        marks_val = col2.number_input("", min_value=0.0, max_value=float(cat_obj["max_marks"]),
                                                       value=float(existing["obtained"]) if existing else 0.0,
                                                       step=0.5, key=f"m_{s['id']}")
                        remarks   = col3.text_input("", placeholder="Remarks", key=f"r_{s['id']}")
                        entries.append((s["id"], marks_val, remarks))
                    c1, c2 = st.columns(2)
                    save_btn    = c1.form_submit_button("💾 Save Marks", type="primary")
                    publish_btn = c2.form_submit_button("📢 Save & Publish")
                if save_btn or publish_btn:
                    payload = [{"student_id": sid, "category_id": sel_cat, "obtained_marks": m, "remarks": r}
                                for sid, m, r in entries]
                    _, err = api_post("/api/admin/marks", json=payload)
                    if err:
                        st.error(err)
                    else:
                        if publish_btn:
                            api_post("/api/admin/marks/publish", json={"category_id": sel_cat})
                        st.success("Marks saved!")
                        st.rerun()


# ── Timetable ─────────────────────────────────────────────────────────────────
with timetable_tab:
    _h("📅 Timetable Management")
    classes_data, _ = api_get("/api/admin/classes", timeout=10)
    classes = classes_data or []
    with st.expander("➕ Create New Timetable"):
        with st.form("new_tt"):
            c1, c2 = st.columns(2)
            tt_cls  = c1.selectbox("Class *", [c["id"] for c in classes],
                                    format_func=lambda i: next((c["name"] for c in classes if c["id"]==i),i))
            tt_name = c2.text_input("Name", value="Timetable")
            c3, c4, c5 = st.columns(3)
            tt_start = c3.text_input("Start Time", value="09:00")
            tt_prd   = c4.number_input("Periods/Day", value=8, min_value=1, max_value=12)
            tt_lunch = c5.number_input("Lunch After Period", value=4, min_value=1)
            if st.form_submit_button("Create Timetable", type="primary"):
                _, err = api_post("/api/admin/timetables",
                                  json={"class_id": tt_cls, "name": tt_name, "start_time": tt_start,
                                        "periods_per_day": int(tt_prd), "lunch_after_period": int(tt_lunch)})
                if err: st.error(err)
                else: st.success("Created!"); st.rerun()

    tt_data, err = api_get("/api/admin/timetables", timeout=15)
    if err: st.error(err)
    else:
        subjects_data, _ = api_get("/api/admin/subjects", timeout=10)
        subjects = subjects_data or []
        DAYS = ["Mon","Tue","Wed","Thu","Fri","Sat"]
        for tt in (tt_data or []):
            b = badge("Published","green") if tt.get("is_published") else badge("Draft","yellow")
            with st.expander(f"📅 {tt['name']} {b}"):
                slots_data, _ = api_get(f"/api/admin/timetables/{tt['id']}/slots", timeout=10)
                slots = slots_data or []
                with st.form(f"add_slot_{tt['id']}"):
                    st.markdown("**Add/Update Slot**")
                    sc1,sc2,sc3,sc4 = st.columns(4)
                    s_day  = sc1.selectbox("Day",    range(6), format_func=lambda i:DAYS[i], key=f"sd_{tt['id']}")
                    s_prd  = sc2.number_input("Period", min_value=1, max_value=tt["periods_per_day"], key=f"sp_{tt['id']}")
                    s_sub  = sc3.selectbox("Subject", [""]+[s["id"] for s in subjects],
                                           format_func=lambda i:"Free" if not i else next((s["name"] for s in subjects if s["id"]==i),i),
                                           key=f"ss_{tt['id']}")
                    s_room = sc4.text_input("Room", key=f"sr_{tt['id']}")
                    if st.form_submit_button("Save Slot"):
                        existing_slot = next((s for s in slots if s["day_of_week"]==s_day and s["period_number"]==s_prd), None)
                        payload = {"day_of_week":int(s_day),"period_number":int(s_prd),"subject_id":s_sub or None,"teacher_id":None,"room":s_room}
                        if existing_slot:
                            api_patch(f"/api/admin/timetables/{tt['id']}/slots/{existing_slot['id']}", json=payload)
                        else:
                            api_post(f"/api/admin/timetables/{tt['id']}/slots", json=payload)
                        st.rerun()
                if not tt.get("is_published"):
                    if st.button("📢 Publish Timetable", key=f"pub_tt_{tt['id']}"):
                        api_post(f"/api/admin/timetables/{tt['id']}/publish"); st.rerun()


# ── Announcements ─────────────────────────────────────────────────────────────
with announcements_tab:
    _h("📢 Announcements")
    classes_data, _ = api_get("/api/admin/classes", timeout=10)
    classes = classes_data or []
    with st.form("new_ann"):
        ann_title   = st.text_input("Title *")
        ann_content = st.text_area("Content *", height=120)
        ann_cls     = st.selectbox("Target",
                                    [""]+[c["id"] for c in classes],
                                    format_func=lambda i:"All Students (Broadcast)" if not i else
                                    next((c["name"] for c in classes if c["id"]==i),i))
        if st.form_submit_button("📢 Post Announcement", type="primary"):
            if ann_title and ann_content:
                _, err = api_post("/api/admin/announcements",
                                  json={"title":ann_title,"content":ann_content,
                                        "class_id":ann_cls or None,"section_id":None})
                if err: st.error(err)
                else: st.success("Posted!"); st.rerun()

    data, err = api_get("/api/admin/announcements", timeout=15)
    if err: st.error(err)
    else:
        for ann in (data or []):
            target = next((c["name"] for c in classes if c["id"]==ann.get("class_id")), "All Students")
            col_ann, col_del = st.columns([5, 1])
            with col_ann:
                card(f"""
<div style="display:flex;justify-content:space-between">
  <p style="margin:0;font-size:14px;font-weight:600;color:#fafafa">{ann['title']}</p>
  <span style="font-size:11px;color:#52525b">{ann.get('created_at','')[:10]}</span>
</div>
<p style="margin:4px 0 0;font-size:13px;color:#a1a1aa">{ann['content'][:150]}{'…' if len(ann['content'])>150 else ''}</p>
<p style="margin:4px 0 0;font-size:11px;color:#52525b">→ {target}</p>""")
            with col_del:
                if st.button("🗑️", key=f"del_ann_{ann['id']}"):
                    api_delete(f"/api/admin/announcements/{ann['id']}"); st.rerun()

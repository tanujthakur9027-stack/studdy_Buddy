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
from core.api_client import api_get, api_post, api_patch, api_delete, api_request, api_download, BACKEND_URL


inject_global_css()
require_login()
page_enter()

from core.header import render_identity_header
render_identity_header()

if not is_admin():
    st.error("🔒 Admin access required.")
    st.stop()

# System Diagnostics
health_data, _ = api_get("/health", timeout=5)
health = health_data or {}
api_status = health.get("status", "ok").upper()
db_name = health.get("database", "sqlite")
provider = health.get("provider", "groq")
model = health.get("model", "qwen3")
smtp_status = "Active" if health.get("smtp") == "configured" else "Simulation Mode"

st.markdown(f"""
<div style="background:rgba(17,24,39,0.9);border:1px solid rgba(31,41,55,0.9);border-radius:14px;
     padding:0.75rem 1.25rem;margin-bottom:1.5rem;display:flex;align-items:center;justify-content:space-between;
     flex-wrap:wrap;gap:12px;font-size:12px;color:#9ca3af">
  <div style="display:flex;align-items:center;gap:8px">
    <span style="display:inline-block;width:8px;height:8px;border-radius:99px;background:#10b981;box-shadow:0 0 10px #10b981"></span>
    <span>API: <strong style="color:#ffffff">{api_status}</strong></span>
  </div>
  <div>💾 DB: <strong style="color:#ffffff">{db_name}</strong></div>
  <div>✨ AI: <strong style="color:#60a5fa">{provider} ({model})</strong></div>
  <div>✉️ SMTP: <strong style="color:#fbbf24">{smtp_status}</strong></div>
  <div>⚡ Rate Limit: <strong style="color:#ffffff">{health.get('rate_limit', '60/min')}</strong></div>
</div>""", unsafe_allow_html=True)

# helpers
def _h(t): st.markdown(f'<p style="font-size:1rem;font-weight:700;color:#ffffff;margin:.75rem 0 .5rem">{t}</p>', unsafe_allow_html=True)

st.markdown("""
<div style="margin-bottom:1.5rem">
  <h1 style="font-size:1.6rem;font-weight:800;color:#ffffff;margin:0 0 .25rem;letter-spacing:-.03em">
    🛡️ Admin Command Center
  </h1>
  <p style="font-size:.875rem;color:#9ca3af;margin:0">Manage student records, batches, assignments, evaluations, schedules, broadcasts, and inquiries.</p>
</div>""", unsafe_allow_html=True)

(students_tab, attrition_tab, classes_tab, assignments_tab,
 submissions_tab, marks_tab, timetable_tab, announcements_tab,
 broadcast_tab, inquiries_tab) = st.tabs([
    "👨‍🎓 Students", "🎯 EduGuard AI", "🏛️ Classes", "📋 Assignments",
    "✅ Submissions", "📊 Marks", "📅 Timetable", "📢 Announcements",
    "✉️ Broadcast & Email", "📬 Inquiries",
])


# ── Students ──────────────────────────────────────────────────────────────────
with students_tab:
    _h("👨‍🎓 Registered Students & Roster Management")
    c_s1, c_s2, c_s3 = st.columns([2, 1, 1])
    with c_s1:
        search = st.text_input("Search by name, email or student ID", key="admin_student_search")
    with c_s2:
        st.markdown("<div style='height: 28px'></div>", unsafe_allow_html=True)
        excel_bytes, _ = api_download(f"/api/admin/students/export/excel?search={search}" if search else "/api/admin/students/export/excel")
        if excel_bytes:
            st.download_button(
                "📥 Export Excel (.xlsx)",
                data=excel_bytes,
                file_name="studybuddy_students.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key="btn_export_excel",
            )
    with c_s3:
        st.markdown("<div style='height: 28px'></div>", unsafe_allow_html=True)
        csv_bytes, _ = api_download(f"/api/admin/students/export/csv?search={search}" if search else "/api/admin/students/export/csv")
        if csv_bytes:
            st.download_button(
                "📄 Export CSV (.csv)",
                data=csv_bytes,
                file_name="studybuddy_students.csv",
                mime="text/csv",
                use_container_width=True,
                key="btn_export_csv",
            )
    data, err = api_get(f"/api/admin/students?search={search}" if search else "/api/admin/students", timeout=15)
    if err:
        st.error(err)
    else:
        students = data or []
        st.caption(f"{len(students)} student(s) registered in system")
        for s in students:
            status_icon = "🟢" if s.get("is_active") else "🔴"
            with st.expander(f"{status_icon} {s.get('full_name','?')} — {s.get('student_id','?')} ({s.get('email','?')})", expanded=False):
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Email",       s.get("email", "—"))
                c2.metric("Course",      s.get("course", "—") or "—")
                c3.metric("Semester",    s.get("semester", "—") or "—")
                c4.metric("Section",     s.get("section", "—") or "—")

                st.markdown("---")
                st.markdown("**✏️ Edit Student Profile Details**")
                with st.form(f"edit_student_{s['id']}"):
                    ec1, ec2, ec3 = st.columns(3)
                    e_name = ec1.text_input("Full Name", value=s.get("full_name", ""))
                    e_email = ec2.text_input("Email", value=s.get("email", ""))
                    e_sid = ec3.text_input("Student ID", value=s.get("student_id", ""))

                    ec4, ec5, ec6 = st.columns(3)
                    e_course = ec4.text_input("Course", value=s.get("course", ""))
                    e_sem = ec5.text_input("Semester", value=s.get("semester", ""))
                    e_sec = ec6.text_input("Section", value=s.get("section", ""))

                    if st.form_submit_button("💾 Save Profile Changes", type="primary"):
                        up_payload = {
                            "full_name": e_name.strip(),
                            "email": e_email.strip(),
                            "student_id": e_sid.strip(),
                            "course": e_course.strip(),
                            "semester": e_sem.strip(),
                            "section": e_sec.strip(),
                        }
                        _, u_err = api_patch(f"/api/admin/students/{s['id']}", json=up_payload)
                        if u_err:
                            st.error(u_err)
                        else:
                            st.success("Student details updated successfully!")
                            st.rerun()

                st.markdown("---")
                col_act, col_del = st.columns([1, 1])
                with col_act:
                    btn_label = "🔴 Deactivate Student Account" if s.get("is_active") else "🟢 Activate Student Account"
                    if st.button(btn_label, key=f"toggle_{s['id']}"):
                        api_patch(f"/api/admin/students/{s['id']}/status",
                                  json={"is_active": not s.get("is_active")})
                        st.rerun()

                with col_del:
                    del_conf = st.checkbox("Confirm permanent deletion", key=f"del_chk_{s['id']}")
                    if st.button("🗑️ Permanently Delete Student", key=f"del_btn_{s['id']}", disabled=not del_conf):
                        _, d_err = api_delete(f"/api/admin/students/{s['id']}?permanent=true")
                        if d_err:
                            st.error(d_err)
                        else:
                            st.success("Student record permanently deleted.")
                            st.rerun()


# ── EduGuard AI Attrition Hub ─────────────────────────────────────────────────
with attrition_tab:
    _h("🎯 EduGuard AI: Student Attrition Early Warning & Retention Center")
    st.markdown("""
    Powered by the **EduGuard AI Machine Learning Engine** — analyzing holistic retention telemetry 
    (1st semester grades, class attendance rate, fee/debtor status, scholarship aid, and enrollment age) 
    with **Explainable AI (XAI)** factor attribution.
    """)

    sub_roster, sub_sim = st.tabs(["📊 Live Student Roster Monitor", "🧪 What-If Attrition Simulator"])

    with sub_roster:
        st.markdown("#### Real-Time Cohort Attrition Analytics")
        if st.button("🔄 Refresh Attrition Telemetry"):
            st.rerun()

        att_data, att_err = api_get("/api/admin/attrition/students", timeout=20)
        if att_err:
            st.error(f"Failed to load attrition telemetry: {att_err}")
        else:
            records = att_data or []
            crit_count = sum(1 for r in records if r.get("risk_level") == "CRITICAL")
            mon_count = sum(1 for r in records if r.get("risk_level") == "MONITOR")
            low_count = sum(1 for r in records if r.get("risk_level") == "LOW")

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Students Evaluated", len(records))
            m2.metric("Critical Risk (>=70%)", crit_count, delta=f"{crit_count} Alert(s)" if crit_count else None, delta_color="inverse")
            m3.metric("Moderate Monitor", mon_count)
            m4.metric("Low Retention Risk", low_count)

            if not records:
                st.info("No registered students found to analyze.")
            else:
                for r in records:
                    badge_color = r.get("alert_color", "#10B981")
                    with st.expander(f"{r.get('status_text')} — {r.get('full_name')} ({r.get('student_id')})", expanded=(r.get("risk_level") == "CRITICAL")):
                        rc1, rc2, rc3 = st.columns(3)
                        rc1.metric("Calculated 1st Sem Grade", f"{r.get('calculated_grade_scale_20', 0)} / 20")
                        rc2.metric("Calculated Attendance", f"{r.get('calculated_attendance', 0)}%")
                        rc3.metric("Retention Risk Score", f"{r.get('risk_probability', 0)}%")

                        st.markdown("**🔬 Explainable AI (XAI) Contributing Factors:**")
                        impacts = r.get("factor_impacts", {})
                        for factor, pct in impacts.items():
                            st.write(f"• **{factor}**: {pct}% impact")
                            st.progress(min(1.0, max(0.0, float(pct) / 100.0)))

                        if r.get("recommendations"):
                            st.markdown("**📋 Counselor Recommended Action Items:**")
                            for rec in r.get("recommendations", []):
                                st.markdown(f"- {rec}")

                        st.markdown("---")
                        st.markdown("**🚨 Counselor Proactive Intervention Dispatch**")
                        c_col1, c_col2 = st.columns([3, 1])
                        custom_c_msg = c_col1.text_input("Custom counseling note (optional)", key=f"cmsg_{r['id']}", placeholder="e.g. Please meet Prof. Sharma for tutoring support...")
                        if c_col2.button("Dispatch Alert", key=f"disp_{r['id']}", type="primary"):
                            dispatch_payload = {
                                "student_id": r["id"],
                                "custom_message": custom_c_msg.strip() if custom_c_msg else None,
                            }
                            res, d_err = api_post("/api/admin/attrition/dispatch-alert", json=dispatch_payload)
                            if d_err:
                                st.error(d_err)
                            else:
                                st.success(f"Support check-in notification dispatched to {r.get('full_name')}!")

    with sub_sim:
        st.markdown("#### Test Custom Student Attrition Scenario")
        sim_col1, sim_col2 = st.columns([1, 1], gap="large")

        with sim_col1:
            st.markdown("**Student Metrics & Telemetry Matrix**")
            s_age = st.slider("Enrollment Age Metric", 15, 60, 20, key="sim_age")
            s_att = st.slider("Class Attendance Rate (%)", 0, 100, 85, key="sim_att")
            s_grd = st.slider("1st Semester Term Grades (0-20 scale)", 0.0, 20.0, 14.0, step=0.5, key="sim_grd")

            sc1, sc2, sc3 = st.columns(3)
            with sc1:
                s_debt_choice = st.radio("Institutional Debtor", ["No", "Yes"], index=0, key="sim_debt")
                s_debt = 1 if s_debt_choice == "Yes" else 0
            with sc2:
                s_sch_choice = st.radio("Scholarship Holder", ["No", "Yes"], index=0, key="sim_sch")
                s_sch = 1 if s_sch_choice == "Yes" else 0
            with sc3:
                s_gen_choice = st.radio("Gender Profile", ["Female", "Male"], index=0, key="sim_gen")
                s_gen = 1 if s_gen_choice == "Male" else 0

        with sim_col2:
            st.markdown("**Calculated Machine Learning Intelligence**")
            eval_req = {
                "debtor": s_debt,
                "scholarship_holder": s_sch,
                "age_at_enrollment": float(s_age),
                "gender": s_gen,
                "first_sem_grade": float(s_grd),
                "attendance_rate": float(s_att),
            }
            eval_res, eval_err = api_post("/api/admin/attrition/evaluate", json=eval_req)
            if eval_err:
                st.error(eval_err)
            else:
                sim_res = eval_res or {}
                alert_c = sim_res.get("alert_color", "#10B981")
                st.markdown(f"""
                <div style="background:#111827;border:2px solid {alert_c};border-radius:14px;padding:20px;margin-bottom:15px">
                    <p style="color:#9ca3af;font-size:12px;margin:0 0 4px;text-transform:uppercase;letter-spacing:.05em">Predictive Retention Risk Classification</p>
                    <p style="font-size:24px;font-weight:800;color:{alert_c};margin:0">{sim_res.get('status_text')}</p>
                    <p style="color:#d1d5db;font-size:13px;margin:8px 0 0">{sim_res.get('description')}</p>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("**🔬 Feature Impact Attribution (XAI):**")
                for f_name, f_pct in sim_res.get("factor_impacts", {}).items():
                    st.write(f"• **{f_name}**: {f_pct}%")
                    st.progress(min(1.0, max(0.0, float(f_pct) / 100.0)))

                if sim_res.get("recommendations"):
                    st.markdown("**Recommended Counselor Interventions:**")
                    for rec in sim_res.get("recommendations", []):
                        st.markdown(f"- {rec}")


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


# ── Broadcast & Email ─────────────────────────────────────────────────────────
with broadcast_tab:
    _h("✉️ Broadcast Notification & Email")
    st.markdown("Dispatch high-priority in-app announcements and optional SMTP emails to students.")
    classes_data, _ = api_get("/api/admin/classes", timeout=10)
    classes = classes_data or []

    with st.form("broadcast_form"):
        b_target = st.selectbox("Target Audience", ["All Students", "Specific Class", "Single Student"])
        b_class_id = None
        b_student_id = None
        if b_target == "Specific Class":
            b_class_id = st.selectbox(
                "Select Class",
                [c["id"] for c in classes],
                format_func=lambda i: next((c["name"] for c in classes if c["id"] == i), i),
            )
        elif b_target == "Single Student":
            b_student_id = st.text_input("Student User ID (UUID)")

        b_title = st.text_input("Title / Subject *", placeholder="Important Announcement")
        b_message = st.text_area("Message Body *", height=120, placeholder="Write your announcement or notice here...")
        b_email = st.checkbox("Also dispatch via SMTP Email to student inboxes", value=False)

        if st.form_submit_button("🚀 Send Broadcast", type="primary"):
            if not b_title or not b_message:
                st.error("Please provide both a title and message.")
            else:
                target_type = "all"
                target_id = None
                if b_target == "Specific Class":
                    target_type = "class"
                    target_id = b_class_id
                elif b_target == "Single Student":
                    target_type = "student"
                    target_id = b_student_id.strip() if b_student_id else None

                payload = {
                    "title": b_title.strip(),
                    "message": b_message.strip(),
                    "target": target_type,
                    "target_id": target_id,
                    "send_email": b_email,
                }
                res, err = api_post("/api/notifications/broadcast", json=payload)
                if err:
                    st.error(err)
                else:
                    st.success(
                        f"Broadcast dispatched! {res.get('in_app_count', 0)} in-app alert(s) generated. "
                        f"{res.get('emails_sent', 0)} email(s) sent via SMTP."
                    )


# ── Student Inquiries ─────────────────────────────────────────────────────────
with inquiries_tab:
    _h("📬 Student Contact & Support Inquiries")
    st.markdown("Review inquiries and questions submitted by students through the Contact Staff channel.")

    inquiries_data, inq_err = api_get("/api/notifications/admin/contacts", timeout=15)
    if inq_err:
        st.error(inq_err)
    else:
        inquiries = inquiries_data or []
        st.caption(f"{len(inquiries)} total inquiry(ies)")
        if not inquiries:
            st.info("No student inquiries at this time.")
        else:
            for inq in inquiries:
                is_read = inq.get("is_read", False)
                status_icon = "🟢 Read" if is_read else "🔴 New"
                sender_name = inq.get("sender_name") or "Student"
                student_id = inq.get("student_id") or ""
                with st.expander(
                    f"{status_icon} | {sender_name} ({student_id}) — {inq.get('title', 'No Title')}",
                    expanded=not is_read,
                ):
                    st.markdown(f"**From:** {sender_name} &lt;{inq.get('sender_email')}&gt;")
                    st.markdown(f"**Date:** {inq.get('created_at', '')[:19].replace('T', ' ')}")
                    st.text_area("Message", value=inq.get("message", ""), height=100, disabled=True, key=f"msg_{inq['id']}")
                    if not is_read:
                        if st.button("Mark as Reviewed", key=f"read_inq_{inq['id']}"):
                            api_patch(f"/api/notifications/{inq['id']}/read")
                            st.rerun()

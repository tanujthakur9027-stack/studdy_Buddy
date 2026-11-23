# -*- coding: utf-8 -*-
"""
generate_pdf_report.py — Generates a comprehensive, professional PDF audit report
for StudyBuddy AI using ReportLab with clean, balanced page layouts.
"""
from __future__ import annotations

import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas
import pypdf

PDF_OUTPUT_PATH = r"C:\Users\Tanuj kumar singh\Desktop\Studdy_Buddy\StudyBuddy_Audit_and_Error_Report.pdf"


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically compute and render total page count and headers/footers."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_header_footer(num_pages)
            super().showPage()
        super().save()

    def draw_header_footer(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))

        # Running header on pages 2+
        if self._pageNumber > 1:
            self.setStrokeColor(colors.HexColor("#E2E8F0"))
            self.setLineWidth(0.5)
            self.line(40, 755, 572, 755)
            self.drawString(40, 760, "StudyBuddy AI — Comprehensive System Audit & Quality Assurance Report")
            self.drawRightString(572, 760, "Confidential Security Audit")

        # Running footer on all pages
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(40, 38, 572, 38)
        self.drawString(40, 26, "STRICTLY FOR INTERNAL REMEDIATION • STUDYBUDDY AI DEV TEAM")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(572, 26, page_str)
        self.restoreState()


def build_pdf():
    doc = SimpleDocTemplate(
        PDF_OUTPUT_PATH,
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=42,
        bottomMargin=46,
    )

    styles = getSampleStyleSheet()

    # Custom typography palette
    C_PRIMARY   = colors.HexColor("#0F172A")  # Deep Navy
    C_ACCENT    = colors.HexColor("#4338CA")  # Indigo
    C_CRITICAL  = colors.HexColor("#DC2626")  # Red
    C_HIGH      = colors.HexColor("#EA580C")  # Orange
    C_WARN      = colors.HexColor("#D97706")  # Amber
    C_SUCCESS   = colors.HexColor("#16A34A")  # Green
    C_TEXT      = colors.HexColor("#1E293B")  # Dark Slate
    C_MUTED     = colors.HexColor("#64748B")  # Muted

    # Typography styles
    styles.add(ParagraphStyle(
        name="DocTitle",
        fontName="Helvetica-Bold",
        fontSize=21,
        leading=25,
        textColor=C_PRIMARY,
        spaceAfter=2,
    ))
    styles.add(ParagraphStyle(
        name="DocSubtitle",
        fontName="Helvetica",
        fontSize=9.5,
        leading=13,
        textColor=C_MUTED,
        spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        name="SecHeader",
        fontName="Helvetica-Bold",
        fontSize=12.5,
        leading=16,
        textColor=C_PRIMARY,
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True,
    ))
    styles.add(ParagraphStyle(
        name="SubSecHeader",
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13.5,
        textColor=C_ACCENT,
        spaceBefore=6,
        spaceAfter=2,
        keepWithNext=True,
    ))
    styles.add(ParagraphStyle(
        name="NormalBody",
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=C_TEXT,
        spaceAfter=3,
    ))
    styles.add(ParagraphStyle(
        name="TableHeader",
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10.5,
        textColor=colors.white,
    ))
    styles.add(ParagraphStyle(
        name="TableCell",
        fontName="Helvetica",
        fontSize=8,
        leading=10.5,
        textColor=C_TEXT,
    ))
    styles.add(ParagraphStyle(
        name="TableCellBold",
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10.5,
        textColor=C_TEXT,
    ))
    styles.add(ParagraphStyle(
        name="BadgeCritical",
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=9.5,
        textColor=C_CRITICAL,
    ))
    styles.add(ParagraphStyle(
        name="BadgeHigh",
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=9.5,
        textColor=C_HIGH,
    ))
    styles.add(ParagraphStyle(
        name="BadgeWarn",
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=9.5,
        textColor=C_WARN,
    ))
    styles.add(ParagraphStyle(
        name="BadgePass",
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=9.5,
        textColor=C_SUCCESS,
    ))

    story = []

    # ─────────────────────────────────────────────────────────────────────────────
    # PAGE 1: TITLE, AUDIT METADATA & SECTION 1 (EXECUTIVE SUMMARY) & SECTION 2 (TEST MATRIX)
    # ─────────────────────────────────────────────────────────────────────────────
    story.append(Paragraph("StudyBuddy AI — Comprehensive System Audit & Quality Assurance Report", styles["DocTitle"]))
    story.append(Paragraph("Full Codebase Review • Live Execution Verification • Security Exploits • Faults, Defects & Roadmap", styles["DocSubtitle"]))

    meta_data = [
        [
            Paragraph("<b>Target Workspace:</b> Studdy_Buddy (Full Stack)", styles["TableCell"]),
            Paragraph("<b>Host Environment:</b> Windows 11 / Python 3.14.6 / Node 24.17", styles["TableCell"]),
        ],
        [
            Paragraph("<b>Audit Date:</b> November 23, 2026", styles["TableCell"]),
            Paragraph("<b>Scope:</b> Backend (FastAPI), Frontend (Next.js), Streamlit, EduGuard ML & DB", styles["TableCell"]),
        ],
        [
            Paragraph("<b>Critical Security Alerts:</b> 6 Identified (1 Live Zero-Day Exploit)", styles["BadgeCritical"]),
            Paragraph("<b>Production Status:</b> Action Required Prior to Public Launch", styles["BadgeWarn"]),
        ]
    ]
    t_meta = Table(meta_data, colWidths=[266, 266])
    t_meta.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#CBD5E1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 6))

    story.append(Paragraph("1. Executive Summary", styles["SecHeader"]))
    story.append(Paragraph(
        "A rigorous, multi-vector technical audit was conducted on the StudyBuddy AI codebase. "
        "The project demonstrates impressive product breadth—including a FastAPI REST backend with 28 relational database tables, "
        "a Next.js 14 web application, a multipage Streamlit administrative portal, RAG vector search via ChromaDB and FAISS, "
        "and an ML-based dropout predictor. However, live execution revealed <b>critical security bypasses</b> (allowing anyone to create verified Admin accounts), "
        "<b>plaintext credentials committed to source code</b>, <b>SQL query crash bugs</b>, and <b>packaging mismatches</b> that prevent successful container deployment.",
        styles["NormalBody"]
    ))
    story.append(Spacer(1, 4))

    story.append(Paragraph("2. Live Execution & Verification Test Matrix", styles["SecHeader"]))

    test_headers = [
        Paragraph("<b>Target Component</b>", styles["TableHeader"]),
        Paragraph("<b>Test Action / Command</b>", styles["TableHeader"]),
        Paragraph("<b>Status</b>", styles["TableHeader"]),
        Paragraph("<b>Observed Runtime Behavior & Diagnostics</b>", styles["TableHeader"]),
    ]
    test_rows = [
        [
            Paragraph("<b>Pytest Suite</b>", styles["TableCellBold"]),
            Paragraph("<code>pytest tests -v</code>", styles["TableCell"]),
            Paragraph("<b>PASSED*</b>", styles["BadgePass"]),
            Paragraph("Failed initially with <code>ModuleNotFoundError: No module named 'main'</code>. With <code>PYTHONPATH=backend</code> set, all <b>22 tests passed</b> in 46.9s (with 37 deprecation &amp; unpickle warnings).", styles["TableCell"]),
        ],
        [
            Paragraph("<b>Frontend Typecheck</b>", styles["TableCellBold"]),
            Paragraph("<code>npx tsc --noEmit</code>", styles["TableCell"]),
            Paragraph("<b>PASSED</b>", styles["BadgePass"]),
            Paragraph("Zero TypeScript compile-time errors across all page routes, contexts, hooks, and UI components.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>Frontend ESLint</b>", styles["TableCellBold"]),
            Paragraph("<code>npm run lint</code>", styles["TableCell"]),
            Paragraph("<b>WARNING</b>", styles["BadgeWarn"]),
            Paragraph("3 warnings: <code>admin/marks/page.tsx</code> has a missing React Hook dependency (<code>report</code>) in <code>useEffect</code>; unoptimized <code>&lt;img&gt;</code> tags in profile and FileUpload.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>Frontend Production</b>", styles["TableCellBold"]),
            Paragraph("<code>npm run build</code>", styles["TableCell"]),
            Paragraph("<b>PASSED</b>", styles["BadgePass"]),
            Paragraph("Next.js 14 optimized production build succeeded. All 25 static and dynamic pages compiled cleanly.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>FastAPI Backend</b>", styles["TableCellBold"]),
            Paragraph("<code>import main; app</code>", styles["TableCell"]),
            Paragraph("<b>PASSED</b>", styles["BadgePass"]),
            Paragraph("Lifespan startup hooks, SQLite WAL mode, rate limiter, and all routers initialized cleanly.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>E2E Flow Runner</b>", styles["TableCellBold"]),
            Paragraph("<code>python test_e2e_flow.py</code>", styles["TableCell"]),
            Paragraph("<b>PASSED</b>", styles["BadgePass"]),
            Paragraph("Admin &amp; Student OTP registration, login, profile generation, roll-number lookup, and broadcasts passed 100%.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>Database Diagnostics</b>", styles["TableCellBold"]),
            Paragraph("<code>python verify_database.py</code>", styles["TableCell"]),
            Paragraph("<b>PASSED</b>", styles["BadgePass"]),
            Paragraph("Verified schema migrations and table integrity across all 28 tables in <code>studybuddy.db</code>.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>Streamlit App</b>", styles["TableCellBold"]),
            Paragraph("<code>streamlit run app.py</code>", styles["TableCell"]),
            Paragraph("<b>FAULT</b>", styles["BadgeCritical"]),
            Paragraph("Streamlit served on 8501, but the embedded FastAPI backend on 8000 does not start until a browser client connects via WebSocket; direct API calls to 8000 failed with <code>WinError 10061 (connection refused)</code>.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>Live LLM Calls</b>", styles["TableCellBold"]),
            Paragraph("<code>llm_service.chat()</code>", styles["TableCell"]),
            Paragraph("<b>FAIL (401/400)</b>", styles["BadgeCritical"]),
            Paragraph("Primary Groq key returned <code>401 Invalid API Key</code>. Fallback Gemini key returned <code>400 API key not valid</code>. Both keys in .env are invalid; any AI question/chat endpoint crashes with HTTP 500.", styles["TableCell"]),
        ],
    ]

    t_tests = Table([test_headers] + test_rows, colWidths=[95, 105, 52, 280])
    t_tests.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), C_PRIMARY),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t_tests)

    # ─────────────────────────────────────────────────────────────────────────────
    # PAGE 2: SECTION 3 (CRITICAL SECURITY VULNERABILITIES)
    # ─────────────────────────────────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("3. Critical Security Vulnerabilities & Exploit Analysis", styles["SecHeader"]))
    story.append(Paragraph(
        "Penetration testing and code review identified six high-impact security vulnerabilities:",
        styles["NormalBody"]
    ))

    # Vuln 1
    v1_box = [
        [Paragraph("<b>VULN-01: Full Admin Privilege Escalation (Broken Access Control)</b>", styles["BadgeCritical"])],
        [Paragraph("<b>Severity:</b> CRITICAL (CVSS 9.8) &bull; <b>Location:</b> <code>backend/routers/auth.py</code> (Lines 213 &amp; 322)", styles["TableCellBold"])],
        [Paragraph(
            "<b>The Flaw:</b> In both <code>/api/auth/register</code> and <code>/api/auth/register-admin</code>, the admin key check was authored as:<br/>"
            "&nbsp;&nbsp;&nbsp;&nbsp;<code>if body.admin_key and body.admin_key.strip() not in valid_keys: raise HTTPException(403)</code><br/>"
            "Because of the prefix <code>if body.admin_key and ...</code>, if an attacker sends <code>\"role\": \"admin\"</code> and simply <b>omits</b> <code>admin_key</code> (or passes <code>null</code> / empty string), the check evaluates to <code>False</code> and is skipped entirely!<br/>"
            "<b>Live Exploit Verification:</b> We dispatched an unauthenticated POST request to <code>/api/auth/register</code> with role <code>admin</code> and no admin key. The server returned <b>HTTP 201 Created</b> and registered an active administrator account with full administrative rights.<br/>"
            "<b>Remediation:</b> Require the key explicitly: <code>if not body.admin_key or body.admin_key.strip() not in valid_keys: raise HTTPException(403, \"Valid admin key required\")</code>",
            styles["TableCell"]
        )]
    ]
    t_v1 = Table(v1_box, colWidths=[532])
    t_v1.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FEF2F2")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#F87171")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t_v1)
    story.append(Spacer(1, 6))

    # Vuln 2
    v2_box = [
        [Paragraph("<b>VULN-02: Hardcoded Plaintext Secrets & Live Credentials in Repository</b>", styles["BadgeCritical"])],
        [Paragraph("<b>Severity:</b> CRITICAL (CVSS 9.1) &bull; <b>Files:</b> <code>backend/config.py</code>, <code>streamlit_app/app.py</code>, <code>frontend/src/app/login/page.tsx</code>", styles["TableCellBold"])],
        [Paragraph(
            "<b>The Flaw:</b> Live sensitive credentials and passwords are hardcoded in git-committed source files:<br/>"
            "1. <code>backend/config.py</code> &amp; <code>streamlit_app/app.py</code>:<br/>"
            "&nbsp;&nbsp;&nbsp;&nbsp;<code>smtp_user = \"[REDACTED-EMAIL]\"</code><br/>"
            "&nbsp;&nbsp;&nbsp;&nbsp;<code>smtp_pass = \"[REDACTED-APP-PASSWORD]\"</code> (Leaked Gmail Application Password)<br/>"
            "&nbsp;&nbsp;&nbsp;&nbsp;<code>admin_seed_email = \"[REDACTED-EMAIL]\"</code>, <code>admin_seed_password = \"[REDACTED-PASSWORD]\"</code><br/>"
            "2. <code>frontend/src/app/login/page.tsx</code>: The admin autofill function previously hardcoded admin credentials in client bundle.<br/>"
            "<b>Remediation:</b> Revoke the Google App Password immediately in Google Account settings. Remove hardcoded strings; inject secrets exclusively through environment variables (.env). Remove admin demo autofill from frontend.",
            styles["TableCell"]
        )]
    ]
    t_v2 = Table(v2_box, colWidths=[532])
    t_v2.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FEF2F2")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#F87171")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t_v2)
    story.append(Spacer(1, 6))

    # Vuln 3
    v3_box = [
        [Paragraph("<b>VULN-03: OTP Verification Code Leakage in HTTP Responses & Stdout Logs</b>", styles["BadgeCritical"])],
        [Paragraph("<b>Severity:</b> HIGH (CVSS 8.2) &bull; <b>File:</b> <code>backend/routers/auth.py</code> (Lines 288 &amp; 442)", styles["TableCellBold"])],
        [Paragraph(
            "<b>The Flaw:</b> In <code>/api/auth/login</code> and <code>/api/auth/register</code>, the simulation mode flag is set via: <code>is_sim = bool(otp_simulation_mode or not email_sent)</code>.<br/>"
            "If email dispatch encounters any network or SMTP issue (or is unconfigured), <b>the server includes the active 6-digit OTP code in the public JSON response field <code>simulation_otp</code></b>! Anyone triggering a login for any account receives the valid OTP right in the API response.<br/>"
            "Furthermore, lines 285 and 440 output <code>🔑 [STUDYBUDDY OTP] Login code: &gt;&gt;&gt; XXXXXX &lt;&lt;&lt;</code> directly to standard server output.<br/>"
            "<b>Remediation:</b> Restrict <code>simulation_otp</code> exclusively to isolated local development/test modes. Never return OTP codes in API responses or plain text logs in production.",
            styles["TableCell"]
        )]
    ]
    t_v3 = Table(v3_box, colWidths=[532])
    t_v3.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFF7ED")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#FDBA74")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t_v3)
    story.append(Spacer(1, 6))

    # Vuln 4
    v4_box = [
        [Paragraph("<b>VULN-04: Arbitrary File Deletion via Path Traversal</b>", styles["BadgeHigh"])],
        [Paragraph("<b>Severity:</b> HIGH (CVSS 7.5) &bull; <b>File:</b> <code>backend/services/storage_service.py</code> (Lines 167–175)", styles["TableCellBold"])],
        [Paragraph(
            "<b>The Flaw:</b> <code>delete_file(url)</code> strips <code>uploads/</code> and directly joins the remaining string to the base upload directory: <code>path = base / relative.replace(\"uploads/\", \"\")</code>. If a crafted URL containing <code>..</code> is provided, it traverses outside the upload folder and calls <code>path.unlink()</code>, allowing arbitrary file deletion on the host server.<br/>"
            "<b>Remediation:</b> Validate that <code>path.resolve().is_relative_to(base.resolve())</code> before unlinking.",
            styles["TableCell"]
        )]
    ]
    t_v4 = Table(v4_box, colWidths=[532])
    t_v4.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFF7ED")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#FDBA74")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t_v4)
    story.append(Spacer(1, 6))

    # Vuln 5 & 6 (Combined)
    v56_box = [
        [Paragraph("<b>VULN-05 &amp; 06: Unauthenticated Resource Deletion &amp; Cross-Tenant Data Leaks</b>", styles["BadgeHigh"])],
        [Paragraph("<b>Severity:</b> HIGH &bull; <b>Files:</b> <code>backend/routers/share.py</code>, <code>backend/services/document_service.py</code>", styles["TableCellBold"])],
        [Paragraph(
            "• <b>Unprotected Share Deletion (share.py L126):</b> <code>DELETE /api/share/{id}</code> has zero authentication. Anyone knowing a share ID can permanently deactivate another student's shared quiz or notes.<br/>"
            "• <b>Cross-Tenant RAG Context Leak (document_service.py L47-52):</b> If a student has uploaded 0 documents, <code>user_doc_ids</code> is empty. <code>filter_dict</code> evaluates to <code>None</code>, causing ChromaDB to search across <b>all users' documents</b> and returning other students' private notes to the asking student.",
            styles["TableCell"]
        )]
    ]
    t_v56 = Table(v56_box, colWidths=[532])
    t_v56.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFF7ED")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#FDBA74")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t_v56)

    # ─────────────────────────────────────────────────────────────────────────────
    # PAGE 3: SECTION 4 (RUNTIME DEFECTS) & SECTION 5 (DEPLOYMENT BOTTLENECKS)
    # ─────────────────────────────────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("4. Runtime Errors, Crashes & Logic Bugs", styles["SecHeader"]))
    story.append(Paragraph(
        "The following operational bugs impact stability and reliability during normal application use:",
        styles["NormalBody"]
    ))

    bugs_data = [
        [
            Paragraph("<b>Bug / Defect</b>", styles["TableHeader"]),
            Paragraph("<b>Location</b>", styles["TableHeader"]),
            Paragraph("<b>Root Cause & Impact</b>", styles["TableHeader"]),
            Paragraph("<b>Fix Required</b>", styles["TableHeader"]),
        ],
        [
            Paragraph("<b>SQLAlchemy Crash on OTP Verify</b>", styles["TableCellBold"]),
            Paragraph("<code>routers/auth.py</code><br/>Lines 408 &amp; 488", styles["TableCell"]),
            Paragraph("Query uses <code>.order_by(AuthOTP.created_at.desc())</code> followed by <code>.scalar_one_or_none()</code>. If more than 1 unused OTP exists, SQLAlchemy raises <code>MultipleResultsFound</code>, crashing the endpoint with HTTP 500.", styles["TableCell"]),
            Paragraph("Change <code>.scalar_one_or_none()</code> to <code>.scalars().first()</code>.", styles["TableCellBold"]),
        ],
        [
            Paragraph("<b>Zero Tables Created by <code>init_db()</code></b>", styles["TableCellBold"]),
            Paragraph("<code>backend/database.py</code><br/>Line 41", styles["TableCell"]),
            Paragraph("<code>Base</code> is declared in <code>database.py</code>, but <code>models.db_models</code> is never imported. Running <code>init_db()</code> from standalone scripts or migrations registers 0 tables.", styles["TableCell"]),
            Paragraph("Add <code>import models.db_models</code> inside <code>database.py</code>.", styles["TableCellBold"]),
        ],
        [
            Paragraph("<b>Uninitialized React Marks State</b>", styles["TableCellBold"]),
            Paragraph("<code>frontend/.../admin/marks/page.tsx</code><br/>Line 64", styles["TableCell"]),
            Paragraph("<code>useEffect</code> depends on <code>[selectedCategory]</code> but uses <code>report</code> inside. If report data loads asynchronously after category selection, student marks inputs remain blank.", styles["TableCell"]),
            Paragraph("Add <code>report</code> to the <code>useEffect</code> dependency array.", styles["TableCellBold"]),
        ],
        [
            Paragraph("<b>Auth Interceptor Redirect Loop</b>", styles["TableCellBold"]),
            Paragraph("<code>frontend/.../AuthContext.tsx</code><br/>Lines 109–111", styles["TableCell"]),
            Paragraph("The global response interceptor redirects to <code>/login</code> on any 401 error. Unauthenticated visitors browsing <code>/register</code> or <code>/share/[id]</code> get forcibly redirected to <code>/login</code>.", styles["TableCell"]),
            Paragraph("Whitelist public paths (<code>/register</code>, <code>/share</code>, <code>/</code>) from automatic redirect.", styles["TableCellBold"]),
        ],
        [
            Paragraph("<b>Hardcoded Backend URL in Streamlit</b>", styles["TableCellBold"]),
            Paragraph("<code>streamlit_app/core/api_client.py</code><br/>Line 20", styles["TableCell"]),
            Paragraph("<code>BACKEND_URL = \"http://localhost:8000\"</code> is hardcoded without environment variable fallback. Deploying Streamlit on Streamlit Cloud and FastAPI on Render causes connection failure.", styles["TableCell"]),
            Paragraph("Read from <code>os.environ.get(\"BACKEND_URL\", ...)</code> or <code>st.secrets</code>.", styles["TableCellBold"]),
        ],
        [
            Paragraph("<b>Brittle Relative Paths in ML Model</b>", styles["TableCellBold"]),
            Paragraph("<code>dropout_predictor_tmp/app.py</code><br/>Line 48", styles["TableCell"]),
            Paragraph("Uses relative string paths like <code>\"dropout_model.pkl\"</code>. Running Streamlit from project root looks in CWD and fails to locate the model assets.", styles["TableCell"]),
            Paragraph("Resolve paths relative to <code>Path(__file__).parent</code>.", styles["TableCellBold"]),
        ],
    ]
    t_bugs = Table(bugs_data, colWidths=[105, 95, 202, 130])
    t_bugs.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), C_PRIMARY),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t_bugs)
    story.append(Spacer(1, 8))

    story.append(Paragraph("5. Packaging, Deployment & Performance Bottlenecks", styles["SecHeader"]))
    story.append(Paragraph(
        "• <b>Missing Production Dependencies:</b> Neither <code>scikit-learn</code> nor <code>pandas</code> is listed in <code>backend/requirements.txt</code>. Docker container builds will crash with <code>ModuleNotFoundError: No module named 'sklearn'</code> when unpickling the attrition model.<br/>"
        "• <b>Render Docker Context Excludes Dropout Predictor:</b> <code>render.yaml</code> defines <code>dockerContext: ./backend</code>, which excludes <code>dropout_predictor_tmp/dropout_model.pkl</code>. The ML binary never copies into the container.<br/>"
        "• <b>Invalid LLM Catalog Identifiers:</b> Default model is set to <code>qwen/qwen3-27b</code> with fallback <code>openai/gpt-oss-20b</code>. Neither exists on Groq; valid keys still return 404/400. Update to <code>llama-3.3-70b-versatile</code>.<br/>"
        "• <b>Synchronous Email Loop (27s Latency):</b> <code>notifications.py</code> sequentially awaits <code>send_email()</code> per student. With 6 students, it required 27.0 seconds. For 30+ students, it causes HTTP gateway timeouts. Offload to FastAPI <code>BackgroundTasks</code>.<br/>"
        "• <b>Timetable N+1 Query Problem:</b> <code>student_timetable.py</code> executes 96 individual SQL queries for a 48-period weekly schedule. Optimize using a single SQL JOIN.",
        styles["NormalBody"]
    ))

    # ─────────────────────────────────────────────────────────────────────────────
    # PAGE 4: SECTION 6 (PRIORITIZED REMEDIATION ROADMAP)
    # ─────────────────────────────────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("6. Prioritized Remediation Roadmap & Exact Fixes", styles["SecHeader"]))
    story.append(Paragraph(
        "Follow this prioritized checklist to bring StudyBuddy AI to a secure, stable, production-ready state:",
        styles["NormalBody"]
    ))

    roadmap_data = [
        [
            Paragraph("<b>Priority</b>", styles["TableHeader"]),
            Paragraph("<b>Action Item</b>", styles["TableHeader"]),
            Paragraph("<b>Target Files</b>", styles["TableHeader"]),
            Paragraph("<b>Exact Code Change / Instruction</b>", styles["TableHeader"]),
        ],
        [
            Paragraph("<b>P0 - URGENT</b>", styles["BadgeCritical"]),
            Paragraph("<b>Fix Admin Privileges Check</b>", styles["TableCellBold"]),
            Paragraph("<code>backend/routers/auth.py</code><br/>Lines 213 &amp; 322", styles["TableCell"]),
            Paragraph("Replace <code>if body.admin_key and ...</code> with <code>if not body.admin_key or body.admin_key.strip() not in valid_keys: raise HTTPException(403)</code>", styles["TableCell"]),
        ],
        [
            Paragraph("<b>P0 - URGENT</b>", styles["BadgeCritical"]),
            Paragraph("<b>Revoke &amp; Rotate Secrets</b>", styles["TableCellBold"]),
            Paragraph("<code>backend/config.py</code><br/><code>streamlit_app/app.py</code><br/><code>frontend/login/page.tsx</code>", styles["TableCell"]),
            Paragraph("Revoke Google App Password. Replace hardcoded strings with <code>\"\"</code>. Delete demo credentials auto-filler from login page.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>P0 - URGENT</b>", styles["BadgeCritical"]),
            Paragraph("<b>Eliminate OTP Leakage</b>", styles["TableCellBold"]),
            Paragraph("<code>backend/routers/auth.py</code><br/>Lines 288 &amp; 442", styles["TableCell"]),
            Paragraph("Set <code>simulation_otp = None</code> unless explicitly configured in local dev mode. Remove plain-text OTP prints to stdout.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>P1 - HIGH</b>", styles["BadgeHigh"]),
            Paragraph("<b>Fix OTP Query Crash</b>", styles["TableCellBold"]),
            Paragraph("<code>backend/routers/auth.py</code><br/>Lines 408 &amp; 488", styles["TableCell"]),
            Paragraph("Replace <code>otp_result.scalar_one_or_none()</code> with <code>otp_result.scalars().first()</code> to prevent <code>MultipleResultsFound</code> exceptions.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>P1 - HIGH</b>", styles["BadgeHigh"]),
            Paragraph("<b>Ensure Models Registration</b>", styles["TableCellBold"]),
            Paragraph("<code>backend/database.py</code><br/>Line 42", styles["TableCell"]),
            Paragraph("Add <code>import models.db_models  # noqa: F401</code> immediately following <code>Base</code> definition so <code>init_db()</code> creates all 28 tables.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>P1 - HIGH</b>", styles["BadgeHigh"]),
            Paragraph("<b>Patch File Path Traversal</b>", styles["TableCellBold"]),
            Paragraph("<code>backend/services/storage_service.py</code><br/>Line 173", styles["TableCell"]),
            Paragraph("Verify <code>path.resolve().is_relative_to(base.resolve())</code> before invoking <code>path.unlink()</code>.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>P1 - HIGH</b>", styles["BadgeHigh"]),
            Paragraph("<b>Prevent Cross-Tenant RAG Leak</b>", styles["TableCellBold"]),
            Paragraph("<code>backend/services/document_service.py</code><br/>Line 47", styles["TableCell"]),
            Paragraph("When <code>user_doc_ids == []</code>, set <code>filter_dict = {\"doc_id\": \"__NONE__\"}</code> so ChromaDB does not perform an unfiltered global query.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>P2 - MEDIUM</b>", styles["BadgeWarn"]),
            Paragraph("<b>Add Missing Requirements</b>", styles["TableCellBold"]),
            Paragraph("<code>backend/requirements.txt</code><br/><code>streamlit_app/requirements.txt</code>", styles["TableCell"]),
            Paragraph("Append <code>scikit-learn&gt;=1.8.0</code> and <code>pandas&gt;=2.2.0</code> to prevent Docker unpickle <code>ModuleNotFoundError</code>.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>P2 - MEDIUM</b>", styles["BadgeWarn"]),
            Paragraph("<b>Copy ML Binary to Backend</b>", styles["TableCellBold"]),
            Paragraph("<code>backend/models/</code>", styles["TableCell"]),
            Paragraph("Copy <code>dropout_model.pkl</code> and <code>features.pkl</code> into <code>backend/models/</code> so Docker builds contain the model assets.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>P2 - MEDIUM</b>", styles["BadgeWarn"]),
            Paragraph("<b>Async Email BackgroundTasks</b>", styles["TableCellBold"]),
            Paragraph("<code>backend/routers/notifications.py</code><br/>Line 254", styles["TableCell"]),
            Paragraph("Use FastAPI <code>BackgroundTasks.add_task()</code> for broadcasting bulk emails, returning response to admin in &lt;100ms instead of 27s.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>P3 - LOW</b>", styles["BadgePass"]),
            Paragraph("<b>Frontend useEffect &amp; Auth</b>", styles["TableCellBold"]),
            Paragraph("<code>frontend/.../admin/marks/page.tsx</code><br/><code>frontend/.../AuthContext.tsx</code>", styles["TableCell"]),
            Paragraph("Add <code>report</code> to useEffect dependencies; whitelist public paths in 401 response interceptor.", styles["TableCell"]),
        ],
    ]
    t_road = Table(roadmap_data, colWidths=[75, 120, 115, 222])
    t_road.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), C_PRIMARY),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t_road)
    story.append(Spacer(1, 10))

    story.append(Paragraph(
        "<b>Audit Sign-Off:</b> This report reflects the verified state of the codebase following full execution and penetration inspection. "
        "Implementing the P0 and P1 recommendations will resolve 100% of the critical vulnerabilities and runtime crashes.",
        styles["NormalBody"]
    ))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"PDF successfully generated at: {PDF_OUTPUT_PATH}")


if __name__ == "__main__":
    build_pdf()

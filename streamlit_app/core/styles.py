"""
core/styles.py — Global CSS injected once per session.

Design tokens, keyframes, component overrides. All animations respect
@media (prefers-reduced-motion: reduce).
"""
from __future__ import annotations
import streamlit as st

# ── Colour tokens ─────────────────────────────────────────────────────────────
COLORS = {
    "bg":         "#09090b",
    "surface":    "#18181b",
    "surface2":   "#27272a",
    "border":     "#3f3f46",
    "text":       "#fafafa",
    "muted":      "#71717a",
    "dimmed":     "#52525b",
    "accent":     "#6366f1",
    "accent_hover":"#4f46e5",
    "success":    "#22c55e",
    "warning":    "#f59e0b",
    "error":      "#ef4444",
}

_CSS = """
<style>
/* ── Fonts ─────────────────────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Inter', -apple-system, sans-serif !important; }

/* ── Base ──────────────────────────────────────────────────────────────────── */
.stApp { background: #09090b; }
.block-container { max-width: 980px !important; padding: 1.5rem 2rem 4rem !important; }

/* ── Sidebar ───────────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] { background: #09090b !important; border-right: 1px solid #27272a !important; }
[data-testid="stSidebar"] > div { padding: 1.5rem 1rem !important; }

/* ── Tabs ───────────────────────────────────────────────────────────────────── */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
  background: transparent !important; border-bottom: 1px solid #27272a !important;
  gap: 0 !important; padding: 0 !important;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
  background: transparent !important; border: none !important;
  border-bottom: 2px solid transparent !important; border-radius: 0 !important;
  color: #71717a !important; font-size: 13px !important; font-weight: 500 !important;
  padding: 10px 14px !important; margin-bottom: -1px !important; white-space: nowrap !important;
}
[data-testid="stTabs"] [aria-selected="true"] {
  color: #fafafa !important; border-bottom-color: #6366f1 !important;
}

/* ── Form, Expander, Inputs ──────────────────────────────────────────────── */
div[data-testid="stForm"] {
  background: #18181b; border: 1px solid #27272a; border-radius: 12px; padding: 1.5rem !important;
}
[data-testid="stExpander"] {
  background: #18181b !important; border: 1px solid #27272a !important; border-radius: 10px !important;
}
[data-testid="baseButton-primary"] {
  background: #6366f1 !important; border: none !important; border-radius: 8px !important;
  color: #fff !important; font-size: 13px !important; font-weight: 600 !important;
  transition: background 0.15s, transform 0.1s !important;
}
[data-testid="baseButton-primary"]:hover { background: #4f46e5 !important; transform: translateY(-1px) !important; }
[data-testid="baseButton-secondary"] {
  background: #27272a !important; border: 1px solid #3f3f46 !important;
  border-radius: 8px !important; color: #d4d4d8 !important;
}
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea,
[data-testid="stNumberInput"] input {
  background: #18181b !important; border: 1px solid #3f3f46 !important;
  border-radius: 8px !important; color: #fafafa !important;
  transition: border-color 0.2s, box-shadow 0.2s !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
  border-color: #6366f1 !important; box-shadow: 0 0 0 2px rgba(99,102,241,.2) !important;
}
[data-testid="stChatMessage"] {
  background: #18181b !important; border: 1px solid #27272a !important;
  border-radius: 12px !important; padding: 1rem 1.25rem !important; margin-bottom: .75rem !important;
}
[data-testid="stMetric"] { background: #18181b; border: 1px solid #27272a; border-radius: 10px; padding: .75rem 1rem; }
[data-testid="stMetricLabel"] { color: #71717a !important; font-size: 12px !important; }
[data-testid="stMetricValue"] { color: #fafafa !important; font-size: 22px !important; font-weight: 700 !important; }
[data-testid="stFileUploader"] {
  background: #18181b !important; border: 1.5px dashed #3f3f46 !important; border-radius: 12px !important;
}
[data-baseweb="select"] > div { background: #18181b !important; border: 1px solid #3f3f46 !important; border-radius: 8px !important; }
hr { border-color: #27272a !important; margin: 1.5rem 0 !important; }

/* ── Utility classes ────────────────────────────────────────────────────────── */
.sb-heading { font-size: 22px !important; font-weight: 700 !important; color: #fafafa !important; margin-bottom: .25rem !important; letter-spacing: -.3px; }
.sb-sub { font-size: 13px !important; color: #71717a !important; margin-bottom: 1.5rem !important; }
.src-chip { display:inline-flex;align-items:center;gap:4px;background:#27272a;border:1px solid #3f3f46;border-radius:6px;padding:3px 10px;font-size:11px;color:#a1a1aa;margin:2px; }
.grade-s{color:#a78bfa;font-size:48px;font-weight:800}.grade-a{color:#22c55e;font-size:48px;font-weight:800}.grade-b{color:#3b82f6;font-size:48px;font-weight:800}.grade-c{color:#f59e0b;font-size:48px;font-weight:800}.grade-d{color:#ef4444;font-size:48px;font-weight:800}
.flip-card{background:#18181b;border:1px solid #27272a;border-radius:14px;padding:2rem 1.5rem;min-height:160px;text-align:center}
.flip-q{font-size:18px;font-weight:600;color:#d4d4d8;margin-bottom:1rem}.flip-a{font-size:16px;color:#a1a1aa}.flip-hint{font-size:12px;color:#52525b;margin-top:.75rem}
.sb-nav-label{font-size:10px;font-weight:600;letter-spacing:.08em;color:#52525b;text-transform:uppercase;padding:.5rem .25rem .25rem}
.card{background:#18181b;border:1px solid #27272a;border-radius:10px;padding:1rem 1.25rem;margin-bottom:.5rem}
.badge-green{background:#14532d;color:#4ade80;font-size:11px;font-weight:600;padding:2px 8px;border-radius:12px;display:inline}
.badge-yellow{background:#422006;color:#fbbf24;font-size:11px;font-weight:600;padding:2px 8px;border-radius:12px;display:inline}
.badge-blue{background:#1e3a5f;color:#60a5fa;font-size:11px;font-weight:600;padding:2px 8px;border-radius:12px;display:inline}
.badge-red{background:#450a0a;color:#f87171;font-size:11px;font-weight:600;padding:2px 8px;border-radius:12px;display:inline}
.badge-purple{background:#2e1065;color:#c4b5fd;font-size:11px;font-weight:600;padding:2px 8px;border-radius:12px;display:inline}

/* ── Animations ─────────────────────────────────────────────────────────────── */
@keyframes fadeUp   { from { opacity:0; transform: translateY(18px); } to { opacity:1; transform: translateY(0); } }
@keyframes fadeIn   { from { opacity:0; } to { opacity:1; } }
@keyframes scaleIn  { from { opacity:0; transform: scale(0.92); } to { opacity:1; transform: scale(1); } }
@keyframes slideInL { from { opacity:0; transform: translateX(-20px); } to { opacity:1; transform: translateX(0); } }
@keyframes shake    { 0%,100%{transform:translateX(0)} 20%,60%{transform:translateX(-8px)} 40%,80%{transform:translateX(8px)} }
@keyframes countUp  { from { opacity:0; transform: translateY(8px); } to { opacity:1; transform: translateY(0); } }
@keyframes pulse    { 0%,100%{opacity:1} 50%{opacity:.45} }
@keyframes ripple   { to { transform: scale(2.5); opacity: 0; } }
@keyframes float    { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-14px)} }
@keyframes gradientShift { 0%{background-position:0% 50%} 50%{background-position:100% 50%} 100%{background-position:0% 50%} }

/* ── Page fade-in ────────────────────────────────────────────────────────────── */
.page-fade { animation: fadeUp 0.45s cubic-bezier(0.16,1,0.3,1) both; }
.card-fade-1 { animation: fadeUp 0.4s 0.05s both; }
.card-fade-2 { animation: fadeUp 0.4s 0.12s both; }
.card-fade-3 { animation: fadeUp 0.4s 0.19s both; }
.card-fade-4 { animation: fadeUp 0.4s 0.26s both; }

/* ── Reduced motion ──────────────────────────────────────────────────────────── */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
</style>
"""


def inject_global_css() -> None:
    """Inject once per session (guarded by session_state)."""
    if st.session_state.get("_css_injected"):
        return
    st.markdown(_CSS, unsafe_allow_html=True)
    st.session_state["_css_injected"] = True


def heading(title: str, sub: str = "") -> None:
    st.markdown(f'<p class="sb-heading">{title}</p>', unsafe_allow_html=True)
    if sub:
        st.markdown(f'<p class="sb-sub">{sub}</p>', unsafe_allow_html=True)


def badge(text: str, color: str = "blue") -> str:
    return f'<span class="badge-{color}">{text}</span>'


def card(content: str) -> None:
    st.markdown(f'<div class="card">{content}</div>', unsafe_allow_html=True)


def page_fade(content_fn) -> None:
    """Wrap callable in a page-fade div."""
    st.markdown('<div class="page-fade">', unsafe_allow_html=True)
    content_fn()
    st.markdown('</div>', unsafe_allow_html=True)

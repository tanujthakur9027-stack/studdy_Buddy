"""
core/styles.py — Global CSS injected once per session.

Design tokens, keyframes, component overrides matching the Next.js dark-glass UI:
  - Base background: #030712
  - Dark glass surface: rgba(17, 24, 39, 0.95)
  - Glow borders: rgba(59, 130, 246, 0.25)
  - Gradient buttons: linear-gradient(to right, #2563eb, #6366f1, #9333ea)
"""
from __future__ import annotations
import streamlit as st

COLORS = {
    "bg":          "#030712",
    "surface":     "#111827",
    "surface2":    "#1f2937",
    "border":      "rgba(31, 41, 55, 0.8)",
    "text":        "#f9fafb",
    "muted":       "#9ca3af",
    "dimmed":      "#6b7280",
    "accent":      "#3b82f6",
    "accent_hover":"#2563eb",
    "success":     "#10b981",
    "warning":     "#f59e0b",
    "error":       "#ef4444",
}

_CSS = """
<style>
/* ── Fonts ───────────────────────────────────────────────────────────────────── */
html, body, [class*="css"] {
  font-family: -apple-system, 'Segoe UI', system-ui, BlinkMacSystemFont, sans-serif !important;
}

/* ── Base App Container ──────────────────────────────────────────────────────── */
.stApp {
  background: #030712 !important;
  color: #f9fafb !important;
}
.block-container {
  max-width: 1160px !important;
  padding: 1.5rem 2rem 4rem !important;
}

/* ── Sidebar ─────────────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #0b0f19 0%, #030712 100%) !important;
  border-right: 1px solid rgba(31, 41, 55, 0.9) !important;
}
[data-testid="stSidebar"] > div {
  padding: 1.25rem 1rem !important;
}
[data-testid="stSidebarNavLink"] {
  border-radius: 12px !important;
  margin-bottom: 2px !important;
  color: #9ca3af !important;
  font-weight: 500 !important;
  font-size: 13.5px !important;
  transition: all .15s ease !important;
}
[data-testid="stSidebarNavLink"]:hover {
  background: rgba(31, 41, 55, 0.6) !important;
  color: #ffffff !important;
}
[data-testid="stSidebarNavLink"][aria-current="page"] {
  background: rgba(37, 99, 235, 0.15) !important;
  border: 1px solid rgba(59, 130, 246, 0.3) !important;
  color: #ffffff !important;
  font-weight: 600 !important;
}

/* ── Tabs ────────────────────────────────────────────────────────────────────── */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
  background: transparent !important;
  border-bottom: 1px solid rgba(31, 41, 55, 0.9) !important;
  gap: 4px !important;
  padding: 0 !important;
  margin-bottom: 1.25rem !important;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
  background: transparent !important;
  border: none !important;
  border-bottom: 2px solid transparent !important;
  border-radius: 8px 8px 0 0 !important;
  color: #9ca3af !important;
  font-size: 13px !important;
  font-weight: 600 !important;
  padding: 10px 16px !important;
  margin-bottom: -1px !important;
  white-space: nowrap !important;
  transition: all .2s ease !important;
}
[data-testid="stTabs"] [data-baseweb="tab"]:hover {
  color: #e5e7eb !important;
  background: rgba(31, 41, 55, 0.4) !important;
}
[data-testid="stTabs"] [aria-selected="true"] {
  color: #ffffff !important;
  border-bottom: 2px solid #3b82f6 !important;
  background: rgba(37, 99, 235, 0.08) !important;
}

/* ── Buttons ─────────────────────────────────────────────────────────────────── */
[data-testid="baseButton-primary"] {
  background: linear-gradient(135deg, #2563eb 0%, #4f46e5 50%, #7c3aed 100%) !important;
  border: none !important;
  border-radius: 12px !important;
  color: #ffffff !important;
  font-size: 13px !important;
  font-weight: 600 !important;
  padding: 0.5rem 1.1rem !important;
  box-shadow: 0 4px 15px rgba(37, 99, 235, 0.35) !important;
  transition: transform .15s, box-shadow .15s !important;
}
[data-testid="baseButton-primary"]:hover {
  transform: translateY(-2px) !important;
  box-shadow: 0 8px 25px rgba(37, 99, 235, 0.5) !important;
}
[data-testid="baseButton-primary"]:active { transform: translateY(0) !important; }

[data-testid="baseButton-secondary"] {
  background: rgba(17, 24, 39, 0.9) !important;
  border: 1px solid rgba(55, 65, 81, 0.8) !important;
  border-radius: 12px !important;
  color: #d1d5db !important;
  font-size: 13px !important;
  font-weight: 500 !important;
  transition: border-color .2s, background .2s, color .2s !important;
}
[data-testid="baseButton-secondary"]:hover {
  border-color: #3b82f6 !important;
  background: rgba(31, 41, 55, 0.8) !important;
  color: #ffffff !important;
}

/* ── Inputs & Textareas ──────────────────────────────────────────────────────── */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea,
[data-testid="stNumberInput"] input {
  background: rgba(17, 24, 39, 0.95) !important;
  border: 1px solid rgba(55, 65, 81, 0.9) !important;
  border-radius: 12px !important;
  color: #ffffff !important;
  font-size: 13px !important;
  transition: border-color .2s, box-shadow .2s !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
  border-color: #3b82f6 !important;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.25) !important;
}

/* ── Selectboxes ─────────────────────────────────────────────────────────────── */
[data-baseweb="select"] > div {
  background: rgba(17, 24, 39, 0.95) !important;
  border: 1px solid rgba(55, 65, 81, 0.9) !important;
  border-radius: 12px !important;
  color: #ffffff !important;
}

/* ── Forms & Expanders ───────────────────────────────────────────────────────── */
div[data-testid="stForm"] {
  background: rgba(17, 24, 39, 0.9);
  border: 1px solid rgba(31, 41, 55, 0.9);
  border-radius: 18px;
  padding: 1.5rem !important;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.5);
}
[data-testid="stExpander"] {
  background: rgba(17, 24, 39, 0.85) !important;
  border: 1px solid rgba(31, 41, 55, 0.9) !important;
  border-radius: 14px !important;
  margin-bottom: 0.6rem !important;
  transition: border-color .2s, box-shadow .2s !important;
}
[data-testid="stExpander"]:hover {
  border-color: rgba(59, 130, 246, 0.4) !important;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3) !important;
}

/* ── Metrics Cards ───────────────────────────────────────────────────────────── */
[data-testid="stMetric"] {
  background: linear-gradient(135deg, rgba(17, 24, 39, 0.95), rgba(31, 41, 55, 0.6));
  border: 1px solid rgba(55, 65, 81, 0.7);
  border-radius: 16px;
  padding: 1rem 1.25rem;
  transition: all .2s ease;
}
[data-testid="stMetric"]:hover {
  border-color: rgba(59, 130, 246, 0.5);
  box-shadow: 0 6px 20px rgba(37, 99, 235, 0.15);
  transform: translateY(-2px);
}
[data-testid="stMetricLabel"] {
  color: #9ca3af !important;
  font-size: 12px !important;
  font-weight: 500 !important;
}
[data-testid="stMetricValue"] {
  color: #ffffff !important;
  font-size: 24px !important;
  font-weight: 800 !important;
}

/* ── File Uploader ───────────────────────────────────────────────────────────── */
[data-testid="stFileUploader"] {
  background: rgba(17, 24, 39, 0.8) !important;
  border: 1.5px dashed rgba(75, 85, 99, 0.7) !important;
  border-radius: 16px !important;
  transition: border-color .2s !important;
}
[data-testid="stFileUploader"]:hover {
  border-color: #3b82f6 !important;
}

/* ── Chat Messages ───────────────────────────────────────────────────────────── */
[data-testid="stChatMessage"] {
  background: rgba(17, 24, 39, 0.85) !important;
  border: 1px solid rgba(31, 41, 55, 0.9) !important;
  border-radius: 16px !important;
  padding: 1rem 1.25rem !important;
  margin-bottom: 0.75rem !important;
}

/* ── Card & Next.js Reusable Classes ─────────────────────────────────────────── */
.card, .sb-card {
  background: rgba(17, 24, 39, 0.85);
  border: 1px solid rgba(31, 41, 55, 0.9);
  border-radius: 16px;
  padding: 1.2rem 1.4rem;
  margin-bottom: 0.75rem;
  transition: border-color .2s, transform .18s, box-shadow .2s;
}
.card:hover, .sb-card:hover {
  border-color: rgba(59, 130, 246, 0.4);
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.4);
}

.sb-hero {
  border-radius: 22px;
  padding: 2.2rem 2.5rem;
  margin-bottom: 1.75rem;
  background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #1e293b 100%);
  border: 1px solid rgba(59, 130, 246, 0.25);
  box-shadow: 0 12px 35px -10px rgba(0, 0, 0, 0.6);
  position: relative;
  overflow: hidden;
}
.sb-hero-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: rgba(59, 130, 246, 0.15);
  border: 1px solid rgba(59, 130, 246, 0.35);
  border-radius: 99px;
  padding: 4px 14px;
  font-size: 11px;
  font-weight: 700;
  color: #93c5fd;
  margin-bottom: 0.9rem;
}

/* ── Badges ──────────────────────────────────────────────────────────────────── */
.badge-green  { background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 99px; }
.badge-yellow { background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 99px; }
.badge-blue   { background: rgba(59, 130, 246, 0.15); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.3); font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 99px; }
.badge-red    { background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 99px; }
.badge-purple { background: rgba(147, 51, 234, 0.15); color: #c084fc; border: 1px solid rgba(147, 51, 234, 0.3); font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 99px; }

/* ── Animations ──────────────────────────────────────────────────────────────── */
@keyframes fadeUp {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}
.page-fade { animation: fadeUp 0.4s ease both; }
</style>
"""


def inject_global_css() -> None:
    """Inject on every render — Streamlit wipes the DOM on each rerun."""
    st.markdown(_CSS, unsafe_allow_html=True)


def heading(title: str, sub: str = "") -> None:
    st.markdown(
        f'<p style="font-size:22px;font-weight:700;color:#fafafa;margin:0 0 .2rem;letter-spacing:-.3px">{title}</p>',
        unsafe_allow_html=True,
    )
    if sub:
        st.markdown(
            f'<p style="font-size:13px;color:#9ca3af;margin:0 0 1.25rem">{sub}</p>',
            unsafe_allow_html=True,
        )


def page_heading(title: str, sub: str = "", icon: str = "") -> None:
    """Full-width page header with optional icon and subtitle."""
    icon_html = f'<span style="font-size:1.5rem;margin-right:.5rem">{icon}</span>' if icon else ""
    st.markdown(f"""
<div style="margin-bottom:1.5rem;animation:fadeUp .4s both">
  <h1 style="font-size:1.6rem;font-weight:800;color:#ffffff;margin:0 0 .3rem;letter-spacing:-.03em">
    {icon_html}{title}
  </h1>
  {f'<p style="font-size:.9rem;color:#9ca3af;margin:0">{sub}</p>' if sub else ""}
</div>""", unsafe_allow_html=True)


def section_header(title: str) -> None:
    """Muted uppercase section label."""
    st.markdown(
        f'<p style="font-size:11px;font-weight:700;color:#9ca3af;text-transform:uppercase;'
        f'letter-spacing:.08em;margin:.5rem 0 .75rem">{title}</p>',
        unsafe_allow_html=True,
    )


def badge(text: str, color: str = "blue") -> str:
    return f'<span class="badge-{color}">{text}</span>'


def card(content: str) -> None:
    st.markdown(f'<div class="card">{content}</div>', unsafe_allow_html=True)


def page_fade(content_fn) -> None:
    """Wrap callable in a page-fade div."""
    st.markdown('<div class="page-fade">', unsafe_allow_html=True)
    content_fn()
    st.markdown('</div>', unsafe_allow_html=True)

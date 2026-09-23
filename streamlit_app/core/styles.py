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
/* ── Fonts ───────────────────────────────────────────────────────────────────── */
html, body, [class*="css"] { font-family: -apple-system, 'Segoe UI', system-ui, BlinkMacSystemFont, sans-serif !important; }

/* ── Base ────────────────────────────────────────────────────────────────────── */
.stApp { background: #09090b; }
.block-container { max-width: 1000px !important; padding: 1.5rem 2rem 4rem !important; }

/* ── Sidebar ─────────────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
  background: linear-gradient(180deg,#0d0d1a 0%,#09090b 100%) !important;
  border-right: 1px solid #1e1e30 !important;
}
[data-testid="stSidebar"] > div { padding: 1.5rem 1rem !important; }

/* ── Tabs ────────────────────────────────────────────────────────────────────── */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
  background: transparent !important; border-bottom: 1px solid #27272a !important;
  gap: 0 !important; padding: 0 !important;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
  background: transparent !important; border: none !important;
  border-bottom: 2px solid transparent !important; border-radius: 0 !important;
  color: #71717a !important; font-size: 13px !important; font-weight: 500 !important;
  padding: 10px 14px !important; margin-bottom: -1px !important; white-space: nowrap !important;
  transition: color .2s !important;
}
[data-testid="stTabs"] [aria-selected="true"] {
  color: #fafafa !important; border-bottom-color: #6366f1 !important;
}

/* ── Buttons ─────────────────────────────────────────────────────────────────── */
[data-testid="baseButton-primary"] {
  background: linear-gradient(135deg,#6366f1,#8b5cf6) !important;
  border: none !important; border-radius: 10px !important;
  color: #fff !important; font-size: 13px !important; font-weight: 600 !important;
  box-shadow: 0 4px 15px rgba(99,102,241,.35) !important;
  transition: transform .15s, box-shadow .15s !important;
}
[data-testid="baseButton-primary"]:hover {
  transform: translateY(-2px) !important;
  box-shadow: 0 6px 25px rgba(99,102,241,.55) !important;
}
[data-testid="baseButton-primary"]:active { transform: translateY(0) !important; }
[data-testid="baseButton-secondary"] {
  background: #18181b !important; border: 1px solid #3f3f46 !important;
  border-radius: 10px !important; color: #d4d4d8 !important;
  transition: border-color .2s, background .2s !important;
}
[data-testid="baseButton-secondary"]:hover {
  border-color: #6366f1 !important; background: #1e1e2e !important;
}

/* ── Inputs ──────────────────────────────────────────────────────────────────── */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea,
[data-testid="stNumberInput"] input {
  background: #18181b !important; border: 1px solid #3f3f46 !important;
  border-radius: 10px !important; color: #fafafa !important;
  transition: border-color .2s, box-shadow .2s !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
  border-color: #6366f1 !important;
  box-shadow: 0 0 0 3px rgba(99,102,241,.2), 0 0 20px rgba(99,102,241,.08) !important;
}

/* ── Forms & Expanders ───────────────────────────────────────────────────────── */
div[data-testid="stForm"] {
  background: #18181b; border: 1px solid #27272a; border-radius: 14px;
  padding: 1.5rem !important;
  box-shadow: 0 4px 24px rgba(0,0,0,.4);
}
[data-testid="stExpander"] {
  background: #18181b !important; border: 1px solid #27272a !important;
  border-radius: 12px !important;
  transition: border-color .2s !important;
}
[data-testid="stExpander"]:hover { border-color: #3f3f7a !important; }

/* ── Chat ────────────────────────────────────────────────────────────────────── */
[data-testid="stChatMessage"] {
  background: #18181b !important; border: 1px solid #27272a !important;
  border-radius: 14px !important; padding: 1rem 1.25rem !important;
  margin-bottom: .75rem !important;
  box-shadow: 0 2px 12px rgba(0,0,0,.3) !important;
}

/* ── Metrics ─────────────────────────────────────────────────────────────────── */
[data-testid="stMetric"] {
  background: linear-gradient(135deg,#18181b,#1c1c2e);
  border: 1px solid #27272a; border-radius: 12px; padding: .875rem 1rem;
  transition: border-color .2s, transform .2s, box-shadow .2s;
}
[data-testid="stMetric"]:hover {
  border-color: #6366f1;
  box-shadow: 0 0 18px rgba(99,102,241,.2);
  transform: translateY(-2px);
}
[data-testid="stMetricLabel"] { color: #71717a !important; font-size: 12px !important; }
[data-testid="stMetricValue"] { color: #fafafa !important; font-size: 22px !important; font-weight: 700 !important; }

/* ── File uploader ───────────────────────────────────────────────────────────── */
[data-testid="stFileUploader"] {
  background: #18181b !important; border: 1.5px dashed #3f3f46 !important;
  border-radius: 14px !important; transition: border-color .2s !important;
}
[data-testid="stFileUploader"]:hover { border-color: #6366f1 !important; }

/* ── Select ──────────────────────────────────────────────────────────────────── */
[data-baseweb="select"] > div {
  background: #18181b !important; border: 1px solid #3f3f46 !important;
  border-radius: 10px !important;
}
hr { border-color: #27272a !important; margin: 1.5rem 0 !important; }

/* ── Utility classes ─────────────────────────────────────────────────────────── */
.sb-heading {
  font-size: 22px !important; font-weight: 700 !important; color: #fafafa !important;
  margin-bottom: .25rem !important; letter-spacing: -.3px;
}
.sb-sub { font-size: 13px !important; color: #71717a !important; margin-bottom: 1.5rem !important; }
.src-chip {
  display:inline-flex;align-items:center;gap:4px;background:#27272a;
  border:1px solid #3f3f46;border-radius:6px;padding:3px 10px;
  font-size:11px;color:#a1a1aa;margin:2px;
}

/* ── Grade badges ────────────────────────────────────────────────────────────── */
.grade-s{color:#a78bfa;font-size:48px;font-weight:800}
.grade-a{color:#22c55e;font-size:48px;font-weight:800}
.grade-b{color:#3b82f6;font-size:48px;font-weight:800}
.grade-c{color:#f59e0b;font-size:48px;font-weight:800}
.grade-d{color:#ef4444;font-size:48px;font-weight:800}

/* ── Flashcard ───────────────────────────────────────────────────────────────── */
.flip-card {
  background: linear-gradient(135deg,#18181b,#1c1c2e);
  border: 1px solid #27272a; border-radius: 16px;
  padding: 2rem 1.5rem; min-height: 160px; text-align: center;
  box-shadow: 0 4px 24px rgba(0,0,0,.4);
}
.flip-q{font-size:18px;font-weight:600;color:#d4d4d8;margin-bottom:1rem}
.flip-a{font-size:16px;color:#a78bfa;font-weight:500}
.flip-hint{font-size:12px;color:#52525b;margin-top:.75rem}

/* ── Nav labels ──────────────────────────────────────────────────────────────── */
.sb-nav-label {
  font-size:10px;font-weight:600;letter-spacing:.08em;
  color:#52525b;text-transform:uppercase;padding:.5rem .25rem .25rem;
}

/* ── Card ────────────────────────────────────────────────────────────────────── */
.card {
  background: linear-gradient(135deg,#18181b,#1a1a2e);
  border: 1px solid #27272a; border-radius: 12px;
  padding: 1rem 1.25rem; margin-bottom: .5rem;
  transition: border-color .2s, transform .18s, box-shadow .2s;
}
.card:hover {
  border-color: #3f3f7a;
  transform: translateY(-2px);
  box-shadow: 0 4px 18px rgba(99,102,241,.15);
}

/* ── Feature cards (dashboard) ───────────────────────────────────────────────── */
.feat-card {
  border-radius: 16px; padding: 1.25rem 1.5rem; cursor: pointer;
  border: 1px solid transparent; position: relative; overflow: hidden;
  transition: transform .2s, box-shadow .2s, border-color .2s;
}
.feat-card::before {
  content:''; position:absolute; inset:0; border-radius:16px; opacity:0;
  background: radial-gradient(circle at 50% 0%, rgba(255,255,255,.06), transparent 70%);
  transition: opacity .2s;
}
.feat-card:hover { transform: translateY(-4px); }
.feat-card:hover::before { opacity:1; }

.feat-card-indigo  { background:linear-gradient(135deg,#1e1b4b,#312e81); border-color:#4338ca; }
.feat-card-indigo:hover  { box-shadow:0 8px 30px rgba(99,102,241,.4); border-color:#6366f1; }

.feat-card-amber   { background:linear-gradient(135deg,#451a03,#78350f); border-color:#b45309; }
.feat-card-amber:hover   { box-shadow:0 8px 30px rgba(245,158,11,.35); border-color:#f59e0b; }

.feat-card-violet  { background:linear-gradient(135deg,#2e1065,#4c1d95); border-color:#7c3aed; }
.feat-card-violet:hover  { box-shadow:0 8px 30px rgba(139,92,246,.4); border-color:#a78bfa; }

.feat-card-emerald { background:linear-gradient(135deg,#052e16,#14532d); border-color:#166534; }
.feat-card-emerald:hover { box-shadow:0 8px 30px rgba(34,197,94,.3); border-color:#22c55e; }

.feat-card-rose    { background:linear-gradient(135deg,#4c0519,#881337); border-color:#be123c; }
.feat-card-rose:hover    { box-shadow:0 8px 30px rgba(244,63,94,.35); border-color:#f43f5e; }

.feat-card-cyan    { background:linear-gradient(135deg,#083344,#164e63); border-color:#0e7490; }
.feat-card-cyan:hover    { box-shadow:0 8px 30px rgba(6,182,212,.3); border-color:#06b6d4; }

.feat-icon {
  width:40px;height:40px;border-radius:10px;
  display:flex;align-items:center;justify-content:center;
  font-size:1.25rem;margin-bottom:.875rem;
  background:rgba(255,255,255,.1);
}
.feat-title { font-size:.95rem;font-weight:700;color:#fafafa;margin:0 0 .25rem; }
.feat-desc  { font-size:.8rem;color:rgba(255,255,255,.55);margin:0;line-height:1.4; }

/* ── Hero banner ─────────────────────────────────────────────────────────────── */
.hero-banner {
  border-radius: 20px; padding: 2rem 2.5rem; margin-bottom: 1.75rem; position: relative;
  background: linear-gradient(135deg,#1e1b4b 0%,#312e81 40%,#2e1065 70%,#1e1b4b 100%);
  background-size: 300% 300%;
  animation: gradientShift 8s ease infinite;
  border: 1px solid rgba(99,102,241,.3);
  overflow: hidden;
}
.hero-banner::after {
  content:''; position:absolute; inset:0; border-radius:20px;
  background: radial-gradient(ellipse at 80% 50%, rgba(139,92,246,.18), transparent 60%);
  pointer-events:none;
}
.hero-label {
  display:inline-flex;align-items:center;gap:6px;
  background:rgba(99,102,241,.2);border:1px solid rgba(99,102,241,.4);
  border-radius:99px;padding:4px 12px;font-size:11px;font-weight:600;
  color:#a5b4fc;letter-spacing:.04em;margin-bottom:.875rem;
}
.hero-title {
  font-size:1.8rem;font-weight:800;color:#fafafa;margin:0 0 .5rem;letter-spacing:-.03em;
  line-height:1.2;
}
.hero-title span { color:#a78bfa; }
.hero-sub { font-size:.9rem;color:rgba(255,255,255,.6);margin:0 0 1.25rem;line-height:1.5; }

/* ── Stat cards ──────────────────────────────────────────────────────────────── */
.stat-card {
  background: linear-gradient(135deg,#18181b,#1c1c2e);
  border: 1px solid #27272a; border-radius: 14px; padding: 1.1rem 1.25rem;
  position: relative; overflow: hidden;
  transition: transform .2s, border-color .2s, box-shadow .2s;
}
.stat-card::before {
  content:''; position:absolute; top:0; left:0; right:0; height:2px;
  background: var(--accent-color, #6366f1);
  border-radius:14px 14px 0 0;
}
.stat-card:hover {
  transform: translateY(-3px);
  border-color: rgba(99,102,241,.4);
  box-shadow: 0 8px 28px rgba(0,0,0,.35);
}
.stat-label { font-size:11px;font-weight:600;color:#71717a;text-transform:uppercase;letter-spacing:.06em;margin-bottom:.5rem; }
.stat-value { font-size:2rem;font-weight:800;color:#fafafa;line-height:1; }
.stat-sub   { font-size:11px;color:#52525b;margin-top:.3rem; }

/* ── Badges ──────────────────────────────────────────────────────────────────── */
.badge-green  {background:#14532d;color:#4ade80;font-size:11px;font-weight:600;padding:2px 8px;border-radius:12px;display:inline}
.badge-yellow {background:#422006;color:#fbbf24;font-size:11px;font-weight:600;padding:2px 8px;border-radius:12px;display:inline}
.badge-blue   {background:#1e3a5f;color:#60a5fa;font-size:11px;font-weight:600;padding:2px 8px;border-radius:12px;display:inline}
.badge-red    {background:#450a0a;color:#f87171;font-size:11px;font-weight:600;padding:2px 8px;border-radius:12px;display:inline}
.badge-purple {background:#2e1065;color:#c4b5fd;font-size:11px;font-weight:600;padding:2px 8px;border-radius:12px;display:inline}

/* ── Animations ──────────────────────────────────────────────────────────────── */
@keyframes fadeUp      { from{opacity:0;transform:translateY(20px)} to{opacity:1;transform:translateY(0)} }
@keyframes fadeIn      { from{opacity:0} to{opacity:1} }
@keyframes scaleIn     { from{opacity:0;transform:scale(.92)} to{opacity:1;transform:scale(1)} }
@keyframes slideInL    { from{opacity:0;transform:translateX(-20px)} to{opacity:1;transform:translateX(0)} }
@keyframes shake       { 0%,100%{transform:translateX(0)} 20%,60%{transform:translateX(-8px)} 40%,80%{transform:translateX(8px)} }
@keyframes countUp     { from{opacity:0;transform:translateY(8px)} to{opacity:1;transform:translateY(0)} }
@keyframes pulse       { 0%,100%{opacity:1} 50%{opacity:.45} }
@keyframes ripple      { to{transform:scale(2.5);opacity:0} }
@keyframes float       { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-14px)} }
@keyframes gradientShift { 0%{background-position:0% 50%} 50%{background-position:100% 50%} 100%{background-position:0% 50%} }
@keyframes shimmer     { 0%{background-position:-200% 0} 100%{background-position:200% 0} }
@keyframes glowPulse   { 0%,100%{box-shadow:0 0 12px rgba(99,102,241,.3)} 50%{box-shadow:0 0 28px rgba(99,102,241,.6)} }
@keyframes bounceIn    { 0%{transform:scale(.5);opacity:0} 70%{transform:scale(1.08)} 100%{transform:scale(1);opacity:1} }
@keyframes slideUp     { from{opacity:0;transform:translateY(30px)} to{opacity:1;transform:translateY(0)} }

/* Staggered entrance */
.page-fade   { animation: fadeUp 0.45s cubic-bezier(.16,1,.3,1) both; }
.card-fade-1 { animation: fadeUp 0.45s 0.05s both; }
.card-fade-2 { animation: fadeUp 0.45s 0.12s both; }
.card-fade-3 { animation: fadeUp 0.45s 0.19s both; }
.card-fade-4 { animation: fadeUp 0.45s 0.26s both; }
.feat-fade-1 { animation: slideUp 0.5s 0.10s both; }
.feat-fade-2 { animation: slideUp 0.5s 0.18s both; }
.feat-fade-3 { animation: slideUp 0.5s 0.26s both; }
.feat-fade-4 { animation: slideUp 0.5s 0.34s both; }
.feat-fade-5 { animation: slideUp 0.5s 0.42s both; }
.feat-fade-6 { animation: slideUp 0.5s 0.50s both; }

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

"""
core/animations.py — Reusable animation helpers for Streamlit pages.

All HTML rendered with unsafe_allow_html uses only hardcoded strings;
any user-supplied text is HTML-escaped before insertion.
"""
from __future__ import annotations
import html
import time
import streamlit as st


# ── Escape helper ─────────────────────────────────────────────────────────────

def _e(text: str) -> str:
    """HTML-escape user-supplied strings before embedding in markup."""
    return html.escape(str(text), quote=True)


# ── Splash screen ─────────────────────────────────────────────────────────────

def show_splash(backend_check_fn, min_ms: int = 2500, timeout_s: int = 30) -> bool:
    """
    Full-screen splash: shown while the backend starts.
    - min_ms    : minimum display time in milliseconds (avoids flash on fast starts)
    - timeout_s : max seconds to wait before showing an error
    Returns True if backend came up, False if timed out.
    """
    if st.session_state.get("_splash_done"):
        return True

    placeholder = st.empty()
    placeholder.markdown("""
<style>
.splash-overlay {
  position: fixed; inset: 0; z-index: 9999;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  background: linear-gradient(135deg, #09090b 0%, #0f0f14 50%, #09090b 100%);
  animation: gradientShift 6s ease infinite;
  background-size: 200% 200%;
}
.splash-logo {
  width: 80px; height: 80px; border-radius: 24px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  display: flex; align-items: center; justify-content: center;
  animation: scaleIn 0.6s cubic-bezier(0.16,1,0.3,1) both;
  margin-bottom: 1.5rem;
  box-shadow: 0 0 48px rgba(99,102,241,0.4);
}
.splash-title {
  font-size: 36px; font-weight: 800; color: #fafafa; letter-spacing: -0.5px;
  animation: fadeUp 0.6s 0.25s both;
}
.splash-title span { color: #a78bfa; }
.splash-sub { font-size: 14px; color: #71717a; margin-top: .5rem; animation: fadeUp 0.5s 0.45s both; }
.splash-bar-bg {
  width: 220px; height: 3px; background: #27272a; border-radius: 99px;
  margin-top: 2.5rem; overflow: hidden; animation: fadeIn 0.4s 0.6s both;
}
.splash-bar {
  height: 100%; border-radius: 99px;
  background: linear-gradient(90deg, #6366f1, #a78bfa);
  animation: pulse 1.4s ease-in-out infinite;
  width: 40%;
}
</style>
<div class="splash-overlay">
  <div class="splash-logo">
    <svg width="44" height="44" viewBox="0 0 44 44" fill="none">
      <path d="M22 4L4 15l18 11 18-11L22 4z" stroke="rgba(255,255,255,0.95)" stroke-width="2.5" stroke-linejoin="round"/>
      <path d="M4 29l18 11 18-11" stroke="rgba(255,255,255,0.95)" stroke-width="2.5" stroke-linejoin="round"/>
      <path d="M4 22l18 11 18-11" stroke="rgba(255,255,255,0.7)" stroke-width="2.5" stroke-linejoin="round"/>
    </svg>
  </div>
  <p class="splash-title">Study Buddy <span>AI</span></p>
  <p class="splash-sub">Your personalised AI learning companion</p>
  <div class="splash-bar-bg"><div class="splash-bar"></div></div>
</div>
""", unsafe_allow_html=True)

    start = time.time()
    ready = False
    while time.time() - start < timeout_s:
        if backend_check_fn():
            ready = True
            break
        time.sleep(0.8)

    # Enforce minimum display time
    elapsed_ms = (time.time() - start) * 1000
    if elapsed_ms < min_ms:
        time.sleep((min_ms - elapsed_ms) / 1000)

    placeholder.empty()

    if not ready:
        st.error(
            "❌ Backend failed to start after 30 s. "
            "Check that all dependencies are installed, then click **Retry**."
        )
        if st.button("🔄 Retry"):
            for k in ("_backend_started", "_backend_healthy"):
                st.session_state.pop(k, None)
            st.rerun()
        st.stop()

    st.session_state["_splash_done"] = True
    return True


# ── Page transition ───────────────────────────────────────────────────────────

def page_enter() -> None:
    """Inject a lightweight fade-up on every page load."""
    st.markdown("""
<style>
[data-testid="stAppViewContainer"] > .main > .block-container {
  animation: fadeUp 0.4s cubic-bezier(0.16,1,0.3,1) both;
}
</style>""", unsafe_allow_html=True)


# ── Login animations ──────────────────────────────────────────────────────────

def login_card_css() -> None:
    st.markdown("""
<style>
.login-bg {
  position: fixed; inset: 0; z-index: -1; overflow: hidden;
  background: linear-gradient(135deg, #09090b 0%, #0d0d18 60%, #09090b 100%);
}
.orb { position:absolute; border-radius:50%; filter:blur(80px); opacity:.18; animation:float 8s ease-in-out infinite; }
.orb-1 { width:340px;height:340px;background:#6366f1;top:-60px;left:-80px; animation-delay:0s; }
.orb-2 { width:280px;height:280px;background:#8b5cf6;bottom:-40px;right:-60px; animation-delay:2.5s; }
.orb-3 { width:200px;height:200px;background:#3b82f6;top:40%;left:60%; animation-delay:5s; }
.login-card-anim { animation: scaleIn 0.5s cubic-bezier(0.16,1,0.3,1) both; }
</style>
<div class="login-bg">
  <div class="orb orb-1"></div>
  <div class="orb orb-2"></div>
  <div class="orb orb-3"></div>
</div>
""", unsafe_allow_html=True)


def shake_anim() -> None:
    """Inject shake CSS + trigger it once (wrong password feedback)."""
    st.markdown("""
<style>
[data-testid="stForm"] { animation: shake 0.4s ease; }
</style>""", unsafe_allow_html=True)


def success_checkmark(message: str = "Success!") -> None:
    msg = _e(message)
    st.markdown(f"""
<div style="text-align:center;padding:2rem">
  <svg width="60" height="60" viewBox="0 0 60 60" style="animation:scaleIn 0.5s cubic-bezier(0.16,1,0.3,1) both">
    <circle cx="30" cy="30" r="28" fill="none" stroke="#22c55e" stroke-width="3"
            stroke-dasharray="176" stroke-dashoffset="176"
            style="animation: dash 0.6s 0.1s ease forwards" />
    <path d="M18 30l9 9 15-15" fill="none" stroke="#22c55e" stroke-width="3"
          stroke-linecap="round" stroke-linejoin="round"
          stroke-dasharray="30" stroke-dashoffset="30"
          style="animation: dash 0.4s 0.5s ease forwards" />
  </svg>
  <style>@keyframes dash {{ to {{ stroke-dashoffset: 0; }} }}</style>
  <p style="color:#22c55e;font-size:18px;font-weight:700;margin-top:.75rem">{msg}</p>
</div>
""", unsafe_allow_html=True)


# ── Confetti (quiz celebration) ───────────────────────────────────────────────

def confetti(trigger: bool = True) -> None:
    """Show confetti burst if trigger is True (e.g. quiz score >= 70%)."""
    if not trigger:
        return
    st.markdown("""
<canvas id="confetti-canvas"
  style="position:fixed;inset:0;z-index:9998;pointer-events:none;width:100%;height:100%"></canvas>
<script>
(function(){
  var canvas=document.getElementById('confetti-canvas');
  if(!canvas)return;
  var ctx=canvas.getContext('2d');
  canvas.width=window.innerWidth; canvas.height=window.innerHeight;
  var particles=[];
  var colours=['#6366f1','#8b5cf6','#22c55e','#f59e0b','#3b82f6','#ec4899'];
  for(var i=0;i<140;i++){
    particles.push({
      x:Math.random()*canvas.width, y:-20,
      vx:(Math.random()-0.5)*5, vy:Math.random()*4+2,
      size:Math.random()*7+4, color:colours[Math.floor(Math.random()*colours.length)],
      rot:Math.random()*360, rotV:(Math.random()-0.5)*4
    });
  }
  function draw(){
    ctx.clearRect(0,0,canvas.width,canvas.height);
    var alive=false;
    for(var i=0;i<particles.length;i++){
      var p=particles[i];
      p.x+=p.vx; p.y+=p.vy; p.rot+=p.rotV; p.vy+=0.05;
      if(p.y<canvas.height+20){alive=true;}
      ctx.save(); ctx.translate(p.x,p.y); ctx.rotate(p.rot*Math.PI/180);
      ctx.fillStyle=p.color; ctx.globalAlpha=Math.max(0,1-p.y/canvas.height);
      ctx.fillRect(-p.size/2,-p.size/4,p.size,p.size/2);
      ctx.restore();
    }
    if(alive) requestAnimationFrame(draw);
    else canvas.style.display='none';
  }
  draw();
  setTimeout(function(){canvas.style.display='none';},4000);
})();
</script>
""", unsafe_allow_html=True)


# ── Count-up numbers ──────────────────────────────────────────────────────────

def count_up_metric(label: str, value: int | float, suffix: str = "", color: str = "#fafafa") -> None:
    val_str = _e(str(value))
    lbl_str = _e(label)
    suf_str = _e(suffix)
    col_str = _e(color)
    st.markdown(f"""
<div style="background:#18181b;border:1px solid #27272a;border-radius:10px;padding:.875rem 1rem;animation:countUp 0.5s ease both">
  <p style="margin:0;font-size:12px;color:#71717a">{lbl_str}</p>
  <p style="margin:4px 0 0;font-size:26px;font-weight:800;color:{col_str}">{val_str}<span style="font-size:14px;color:#71717a">{suf_str}</span></p>
</div>""", unsafe_allow_html=True)

"""
core/media_uploader.py — Reusable GIF-capable file uploader component.

render_media_uploader(label, key, allowed, max_mb)

Features:
- Accept GIF, PNG, JPG, JPEG, WEBP
- Animated GIF preview via base64 <img> (st.image shows only first frame)
- Shows filename, size, dimensions and frame count
- Enforces the same max_mb limit as the backend before uploading
- Styled dashed dropzone with CSS pulse animation on hover
- Returns the uploaded file bytes + metadata dict, or (None, None) if nothing uploaded
"""
from __future__ import annotations

import base64
import html
import io
from typing import Optional

import streamlit as st

try:
    from PIL import Image as PILImage  # type: ignore
    _PILLOW = True
except ImportError:
    _PILLOW = False


def _e(text: str) -> str:
    return html.escape(str(text), quote=True)


_UPLOADER_CSS = """
<style>
[data-testid="stFileUploader"] {
  background: #18181b !important;
  border: 1.5px dashed #3f3f46 !important;
  border-radius: 12px !important;
  transition: border-color 0.2s !important;
}
[data-testid="stFileUploader"]:hover {
  border-color: #6366f1 !important;
}
.gif-preview { border-radius: 10px; border: 1px solid #27272a; display: block; max-width: 100%; }
.media-meta { font-size: 12px; color: #71717a; margin-top: .5rem; }
.media-meta b { color: #a1a1aa; }
</style>
"""


def render_media_uploader(
    label: str = "Upload image or GIF",
    key: str = "media_upload",
    allowed: tuple[str, ...] = ("gif", "png", "jpg", "jpeg", "webp"),
    max_mb: int = 5,
) -> tuple[Optional[bytes], Optional[dict]]:
    """
    Render a styled file uploader that handles animated GIFs properly.

    Returns:
        (file_bytes, metadata_dict) where metadata contains:
          - original_name: str
          - mime: str
          - size_kb: float
          - width: int | None
          - height: int | None
          - frame_count: int (>1 for animated GIFs)
        or (None, None) if no file was selected.
    """
    st.markdown(_UPLOADER_CSS, unsafe_allow_html=True)

    uploaded = st.file_uploader(
        label,
        type=list(allowed),
        key=key,
        help=f"Max {max_mb} MB · Supported: {', '.join(f.upper() for f in allowed)}",
    )

    if uploaded is None:
        return None, None

    file_bytes = uploaded.getvalue()
    size_mb = len(file_bytes) / (1024 * 1024)

    if size_mb > max_mb:
        st.error(f"⚠️ File is {size_mb:.1f} MB — maximum allowed is {max_mb} MB.")
        return None, None

    ext = uploaded.name.rsplit(".", 1)[-1].lower() if "." in uploaded.name else ""
    mime = uploaded.type or f"image/{ext}"

    width: Optional[int] = None
    height: Optional[int] = None
    frame_count = 1

    if _PILLOW:
        try:
            img = PILImage.open(io.BytesIO(file_bytes))
            width, height = img.size
            frame_count = getattr(img, "n_frames", 1)
        except Exception:
            pass

    # ── Preview ───────────────────────────────────────────────────────────────
    is_gif = ext == "gif" or mime == "image/gif"

    if is_gif:
        # Embed as base64 so the browser renders all frames (animated)
        b64 = base64.b64encode(file_bytes).decode()
        safe_name = _e(uploaded.name)
        st.markdown(
            f'<img class="gif-preview" src="data:image/gif;base64,{b64}" alt="{safe_name}" />',
            unsafe_allow_html=True,
        )
    else:
        st.image(file_bytes, use_container_width=False, width=280)

    # ── Metadata ─────────────────────────────────────────────────────────────
    parts = [
        f"<b>File:</b> {_e(uploaded.name)}",
        f"<b>Size:</b> {size_mb:.2f} MB",
    ]
    if width and height:
        parts.append(f"<b>Dimensions:</b> {width}×{height} px")
    if frame_count > 1:
        parts.append(f"<b>Frames:</b> {frame_count} (animated GIF)")

    st.markdown(
        f'<p class="media-meta">{" &nbsp;·&nbsp; ".join(parts)}</p>',
        unsafe_allow_html=True,
    )

    metadata = {
        "original_name": uploaded.name,
        "mime": mime,
        "size_kb": round(len(file_bytes) / 1024, 1),
        "width": width,
        "height": height,
        "frame_count": frame_count,
    }
    return file_bytes, metadata

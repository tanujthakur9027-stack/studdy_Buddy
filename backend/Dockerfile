# ── Base image ────────────────────────────────────────────────────────────────
FROM python:3.11-slim

# Install system deps needed by pdfplumber / chromadb
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Python deps ───────────────────────────────────────────────────────────────
# Copy requirements first for Docker layer caching
COPY requirements.txt .

# Install numpy BEFORE faiss-cpu to prevent numpy 2.x ABI mismatch
RUN pip install --no-cache-dir "numpy<2.0.0"

# Install all remaining dependencies
RUN pip install --no-cache-dir -r requirements.txt

# ── Pre-download HuggingFace embedding model at BUILD time ────────────────────
# This ensures the model is cached in the image — no cold-start download delay.
# Model: sentence-transformers/all-MiniLM-L6-v2 (~22 MB)
RUN python -c "\
from sentence_transformers import SentenceTransformer; \
SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2'); \
print('✅ Embedding model cached')"

# ── Application code ──────────────────────────────────────────────────────────
COPY . .

# ── Runtime ───────────────────────────────────────────────────────────────────
# PORT is injected by Render at runtime.
# --workers 1 is REQUIRED — FAISS indexes are in-memory per-process;
# multiple workers would split the registry across processes.
ENV PORT=8000
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT} --workers 1"]

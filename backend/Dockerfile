FROM python:3.11-slim

# System deps needed by pdfplumber / chromadb / faiss
# libgomp1 is required by faiss-cpu on Linux
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for Docker layer caching
COPY requirements.txt .

# Install numpy first (avoids build-time ABI conflicts with faiss-cpu)
RUN pip install --no-cache-dir "numpy>=2.0.0"

# Install all remaining dependencies
# fastembed uses ONNX Runtime — no PyTorch, image stays ~200 MB
RUN pip install --no-cache-dir -r requirements.txt

# Pre-warm fastembed model at BUILD time so cold starts are instant
# bge-small-en-v1.5 is ~24 MB and caches under /root/.cache/fastembed
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('BAAI/bge-small-en-v1.5'); print('fastembed model cached')"

# Copy application code
COPY . .

# PORT is injected by Render at runtime
# --workers 1 is REQUIRED — FAISS indexes are in-memory per-process
ENV PORT=8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen(f'http://localhost:{__import__(\"os\").getenv(\"PORT\",\"8000\")}/health')" || exit 1
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT} --workers 1"]

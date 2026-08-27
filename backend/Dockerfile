FROM python:3.11-slim

# System deps needed by pdfplumber / chromadb / faiss
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for Docker layer caching
COPY requirements.txt .

# Install numpy first with a known-good wheel for python 3.11
RUN pip install --no-cache-dir "numpy>=1.26.0,<2.0.0"

# Install all remaining dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download HuggingFace embedding model at BUILD time (~22 MB)
# This avoids cold-start download delay on first request
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2'); print('Embedding model cached')"

# Copy application code
COPY . .

# PORT is injected by Render at runtime
# --workers 1 is REQUIRED — FAISS indexes are in-memory per-process
ENV PORT=8000
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT} --workers 1"]

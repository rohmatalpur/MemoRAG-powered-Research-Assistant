FROM python:3.11-slim-bookworm

WORKDIR /app

# Minimal build deps only — PyMuPDF and lxml ship pre-compiled wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
# Install CPU-only torch first to avoid downloading 2GB+ of CUDA libraries
RUN pip install --no-cache-dir torch==2.4.1+cpu --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend package so `import backend.xxx` resolves correctly
COPY backend/ ./backend/

RUN mkdir -p /app/data/papers /app/data

EXPOSE 8000

CMD ["uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

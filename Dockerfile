# ==============================================================================
# Stage 1: Build the React 19 / Vite 8 PWA bundle
# ==============================================================================
FROM node:22-slim AS frontend

WORKDIR /web

COPY web/package*.json ./
RUN npm ci

COPY web/ ./
RUN npm run build

# ==============================================================================
# Stage 2: Production Python 3.11 runtime (FastAPI + PWA + Daemon image)
# ==============================================================================
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

WORKDIR /app

# Install runtime utilities (curl for healthchecks, tzdata for America/New_York market clock, TLS certs)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    tzdata \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Create non-root application user (UID 1000 matches default Linux workstation user)
RUN useradd --create-home --shell /bin/bash --uid 1000 appuser

# Copy application source and prebuilt frontend assets owned by appuser
COPY --chown=appuser:appuser . /app
COPY --from=frontend --chown=appuser:appuser /web/dist /app/web/dist

# Ensure persistent runtime directories exist and are writable by appuser
RUN mkdir -p /app/data/backups /app/intel_bus /app/signals \
    && chown -R appuser:appuser /app/data /app/intel_bus /app/signals

USER appuser

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8080/api/health || exit 1

CMD ["sh", "-c", "python -m uvicorn api_server:app --host 0.0.0.0 --port ${PORT:-8080}"]

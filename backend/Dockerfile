# Production Dockerfile for Gridbricks Wind Intelligence FastAPI Backend
FROM python:3.11-slim

# Set environment variables for clean container execution
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8000

WORKDIR /app

# Install Python dependencies first for optimal Docker layer caching
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy backend application source and pre-seeded January 2026 SQLite database
COPY backend/app /app/backend/app
COPY backend/data /app/backend/data

# Ensure database directory exists
RUN mkdir -p /app/backend/data

EXPOSE 8000

# Self-contained health check querying the /api/health endpoint using dynamic PORT
HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
    CMD python3 -c "import os, urllib.request; port = os.environ.get('PORT', '8000'); urllib.request.urlopen(f'http://127.0.0.1:{port}/api/health')" || exit 1

# Start production Uvicorn server with 2 worker processes binding to dynamic PORT (defaults to 8000)
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2"]

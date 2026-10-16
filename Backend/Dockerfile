# ==============================================================================
# UnClone Gate Backend - Persistent Container Deployment
# Track 3: UNCLONE Agents (Zero-Trust BFSI Voice Security Gateway)
# ==============================================================================

FROM python:3.11-slim

# Set environment defaults
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000 \
    HOST=0.0.0.0

# Install curl for health checking and system utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency definition first for optimal layer caching
COPY requirements.txt .

# Install Python production dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application backend package and server runner
COPY backend/ ./backend/
COPY run_server.py .
COPY .env.example .

# Create persistent storage directory for SQLite audit logs
RUN mkdir -p /app/data

# Declare volume for persistent data mounts (e.g. Render Disk, Docker Volume)
VOLUME ["/app/data"]

# Expose default HTTP service port
EXPOSE 8000

# Container healthcheck querying the /api/health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/api/health || exit 1

# Start server using run_server.py (renders diagnostics and runs Uvicorn)
CMD ["python", "run_server.py"]

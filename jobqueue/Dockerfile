# Use Python 3.12 slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy dependency files
COPY pyproject.toml .
COPY README.md .

# Copy uv.lock if it exists, otherwise continue without it
COPY uv.lock* ./

# Install dependencies - use --frozen if uv.lock exists, otherwise generate new lockfile
RUN if [ -f uv.lock ]; then \
        echo "Found uv.lock, using --frozen install" && \
        uv sync --frozen --no-dev; \
    else \
        echo "No uv.lock found, generating new lockfile" && \
        uv sync --no-dev; \
    fi

# Copy application code
COPY app/ ./app/

# Create data directory for SQLite
RUN mkdir -p /app/data

# Set environment variables
ENV PYTHONPATH=/app
ENV JOBQUEUE_DB_URL=sqlite+aiosqlite:///./data/jobqueue.db

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
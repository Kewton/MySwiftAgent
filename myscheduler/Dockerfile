FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy dependency files
COPY pyproject.toml ./
COPY README.md ./

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

# Set timezone
ENV TZ=Asia/Tokyo
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Expose port
EXPOSE 8000

# Run the application
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
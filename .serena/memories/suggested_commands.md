# Essential Development Commands

## Environment Setup
```bash
# Install uv (one-time setup)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync dependencies
uv sync

# Navigate to jobqueue directory
cd jobqueue
```

## Development Server
```bash
# Start development server with auto-reload
uv run uvicorn app.main:app --reload

# Start server on specific host/port
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Testing
```bash
# Run all tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=app --cov-report=term-missing

# Run specific test file
uv run pytest tests/unit/test_schemas.py

# Run specific test method
uv run pytest tests/integration/test_api.py::TestHealthAPI::test_health_check -v
```

## Code Quality (Must run before PR)
```bash
# Check code with linter
uv run ruff check .

# Auto-fix linting issues
uv run ruff check . --fix

# Format code
uv run ruff format .

# Check formatting without changes
uv run ruff format . --check

# Type checking
uv run mypy .
```

## Git Operations (Darwin/macOS)
```bash
# Basic git commands work as expected
git status
git add .
git commit -m "message"
git push

# List files
ls -la

# Find files
find . -name "*.py" -type f

# Search in files (use ripgrep if available)
rg "pattern" --type py
```

## Complete Quality Check (Run before PR)
```bash
# Full quality check sequence
uv run pytest --cov=app --cov-report=term-missing && \
uv run ruff check . && \
uv run mypy . && \
uv run ruff format . --check && \
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 &
sleep 5 && curl http://localhost:8000/health && pkill -f uvicorn
```
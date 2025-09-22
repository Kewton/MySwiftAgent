# Task Completion Checklist

## Before Submitting Any Code Changes

### 1. Code Quality Checks (Mandatory)
```bash
# Run in jobqueue directory
cd jobqueue

# Fix linting issues automatically
uv run ruff check . --fix

# Ensure code is properly formatted
uv run ruff format .

# Verify type checking passes
uv run mypy .

# Verify formatting is correct (should pass without changes)
uv run ruff format . --check
```

### 2. Testing (Mandatory)
```bash
# Run all tests with coverage
uv run pytest --cov=app --cov-report=term-missing

# Ensure coverage targets are met:
# - Unit tests: 80%+
# - Integration tests: 90%+

# Run specific test suites if needed
uv run pytest tests/unit/
uv run pytest tests/integration/
```

### 3. Application Verification
```bash
# Verify application starts correctly
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000

# Test health endpoints
curl http://localhost:8000/
curl http://localhost:8000/health
```

### 4. Git Operations
```bash
# Check what will be committed
git status
git diff

# Add files (be selective, don't add unnecessary files)
git add specific_files

# Create meaningful commit message
git commit -m "descriptive message

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

### 5. Branch and PR Guidelines
- **Never push directly** to `main`, `staging`, or `release/*` branches
- **Always use PRs** for merging between branches
- **Follow branch naming**: `feature/*`, `fix/*`, `refactor/*`, etc.
- **Review CI/CD status** in GitHub Actions before merging

## Quality Thresholds (Must Pass)
- ✅ All tests passing
- ✅ No linting errors (`ruff check`)
- ✅ No type errors (`mypy`)
- ✅ Code properly formatted (`ruff format --check`)
- ✅ Application starts successfully
- ✅ Coverage targets met (80%+ unit, 90%+ integration)

## CI/CD Verification
After pushing, verify these GitHub Actions pass:
- ✅ Test Suite
- ✅ Documentation Check
- ✅ Dependency Security Check
- ✅ Security Scan (may have permissions issues, not code-related)
- ✅ Build Check (requires Dockerfile)

## Common Issues to Avoid
- **Missing type hints** → Run `mypy .`
- **Import sorting** → Run `ruff check . --fix`
- **Line length violations** → Run `ruff format .`
- **Missing newlines at EOF** → Auto-fixed by Ruff
- **Unused imports** → Auto-detected by Ruff
- **Schema mismatches** → Ensure API schemas match database models
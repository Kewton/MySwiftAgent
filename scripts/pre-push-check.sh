#!/bin/bash
# Pre-push quality check script
# Run this before pushing to ensure all CI checks will pass

set -e  # Exit on error

echo "🔍 Running pre-push quality checks..."
echo ""

cd expertAgent

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track overall success
FAILED=0

# Function to run check
run_check() {
    local name=$1
    local command=$2
    
    echo -e "${YELLOW}▶${NC} Running $name..."
    if eval "$command"; then
        echo -e "${GREEN}✓${NC} $name passed"
        echo ""
        return 0
    else
        echo -e "${RED}✗${NC} $name failed"
        echo ""
        FAILED=1
        return 1
    fi
}

# 1. Linting
run_check "Ruff linting" "uv run ruff check ."

# 2. Formatting check
run_check "Ruff formatting" "uv run ruff format . --check"

# 3. Type checking
run_check "MyPy type checking" "uv run mypy app/ core/"

# 4. Unit tests
run_check "Unit tests" "uv run pytest tests/unit/ -x --tb=short -q"

# 5. Coverage check
run_check "Test coverage" "uv run pytest tests/ --cov=app --cov=core --cov-fail-under=90 -q"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed!${NC} 🎉"
    echo "You can safely push your changes."
    exit 0
else
    echo -e "${RED}✗ Some checks failed.${NC} ⚠️"
    echo "Please fix the errors before pushing."
    exit 1
fi

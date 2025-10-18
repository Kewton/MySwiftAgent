


#!/bin/bash
# Multi-project pre-push quality check script
# Run this before pushing to ensure all CI checks will pass

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Track overall success
FAILED=0
PROJECT_ROOT=$(cd "$(dirname "$0")/.." && pwd)

# Python projects to check
PYTHON_PROJECTS=("expertAgent" "jobqueue" "myscheduler" "myVault" "commonUI")

echo "🔍 Running pre-push quality checks for all projects..."
echo ""

# Function to run check
run_check() {
    local project=$1
    local name=$2
    local command=$3

    echo -e "${YELLOW}▶${NC} [$project] Running $name..."
    if eval "$command"; then
        echo -e "${GREEN}✓${NC} [$project] $name passed"
        echo ""
        return 0
    else
        echo -e "${RED}✗${NC} [$project] $name failed"
        echo ""
        FAILED=1
        return 1
    fi
}

# Check each Python project
for project in "${PYTHON_PROJECTS[@]}"; do
    if [ ! -d "$PROJECT_ROOT/$project" ]; then
        echo -e "${YELLOW}⚠${NC} Skipping $project (directory not found)"
        continue
    fi

    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}Checking: $project${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    cd "$PROJECT_ROOT/$project"

    # 1. Linting
    run_check "$project" "Ruff linting" "uv run ruff check ."

    # 2. Formatting check
    run_check "$project" "Ruff formatting" "uv run ruff format . --check"

    # 3. Type checking (if pyproject.toml has mypy config)
    if grep -q "\[tool.mypy\]" pyproject.toml 2>/dev/null; then
        run_check "$project" "MyPy type checking" "uv run mypy app/ core/ 2>/dev/null || uv run mypy app/ 2>/dev/null || uv run mypy . 2>/dev/null"
    fi

    # 4. Unit tests
    if [ -d "tests/unit" ]; then
        run_check "$project" "Unit tests" "uv run pytest tests/unit/ -x --tb=short -q"
    fi

    # 5. Coverage check
    if [ -d "tests" ]; then
        # Get coverage threshold from pyproject.toml or skip if not set
        COVERAGE_THRESHOLD=$(grep "cov-fail-under" pyproject.toml 2>/dev/null | head -1 | sed 's/.*cov-fail-under=\([0-9]*\).*/\1/')
        if [ -n "$COVERAGE_THRESHOLD" ]; then
            # Different coverage targets for different projects
            if [ "$project" == "commonUI" ]; then
                run_check "$project" "Test coverage (≥${COVERAGE_THRESHOLD}%)" "uv run pytest tests/ --cov=components --cov=core --cov-fail-under=$COVERAGE_THRESHOLD -q"
            else
                run_check "$project" "Test coverage (≥${COVERAGE_THRESHOLD}%)" "uv run pytest tests/ --cov=app --cov=core --cov-fail-under=$COVERAGE_THRESHOLD -q 2>/dev/null || uv run pytest tests/ --cov=app --cov-fail-under=$COVERAGE_THRESHOLD -q"
            fi
        else
            echo -e "${YELLOW}⚠${NC} [$project] Coverage threshold not set, skipping coverage check"
        fi
    fi

    echo ""
done

# Check TypeScript/Node.js projects
if [ -d "$PROJECT_ROOT/graphAiServer" ]; then
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}Checking: graphAiServer${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    cd "$PROJECT_ROOT/graphAiServer"

    # Check if node_modules exists
    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}⚠${NC} [graphAiServer] node_modules not found, skipping checks"
    else
        # TypeScript checks
        if [ -f "package.json" ] && grep -q "\"lint\"" package.json; then
            run_check "graphAiServer" "ESLint" "npm run lint"
        fi

        if [ -f "tsconfig.json" ]; then
            run_check "graphAiServer" "TypeScript compilation" "npm run type-check 2>/dev/null || npx tsc --noEmit"
        fi

        if grep -q "\"build\"" package.json 2>/dev/null; then
            run_check "graphAiServer" "Build" "npm run build"
        fi
    fi

    echo ""
fi

# Final summary
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

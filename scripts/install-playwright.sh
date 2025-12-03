#!/bin/bash
#
# install-playwright.sh - Install Playwright for TypeScript acceptance tests
#
# Usage:
#   ./scripts/install-playwright.sh [--all-browsers]
#
# Options:
#   --all-browsers    Install all browsers (chromium, firefox, webkit)
#                     Default: chromium only
#
# This script:
#   1. Checks Node.js version
#   2. Installs npm dependencies
#   3. Installs Playwright browsers
#

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TYPESCRIPT_DIR="$PROJECT_ROOT/tests/acceptance/typescript"
MIN_NODE_VERSION=18

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
ALL_BROWSERS=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --all-browsers)
            ALL_BROWSERS=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [--all-browsers]"
            echo ""
            echo "Options:"
            echo "  --all-browsers    Install all browsers (chromium, firefox, webkit)"
            echo "                    Default: chromium only"
            exit 0
            ;;
        *)
            echo -e "${RED}Error: Unknown option $1${NC}"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}  Playwright Installation Script${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# Check Node.js
echo -e "${YELLOW}[1/4] Checking Node.js version...${NC}"

if ! command -v node &> /dev/null; then
    echo -e "${RED}Error: Node.js is not installed${NC}"
    echo "Please install Node.js 18+ from https://nodejs.org/"
    exit 1
fi

NODE_VERSION=$(node -v | sed 's/v//' | cut -d. -f1)
if [ "$NODE_VERSION" -lt "$MIN_NODE_VERSION" ]; then
    echo -e "${RED}Error: Node.js version $NODE_VERSION is too old${NC}"
    echo "Please install Node.js $MIN_NODE_VERSION+ from https://nodejs.org/"
    exit 1
fi

echo -e "${GREEN}  Node.js version: $(node -v)${NC}"
echo -e "${GREEN}  npm version: $(npm -v)${NC}"

# Check npm
echo ""
echo -e "${YELLOW}[2/4] Checking npm...${NC}"

if ! command -v npm &> /dev/null; then
    echo -e "${RED}Error: npm is not installed${NC}"
    exit 1
fi

echo -e "${GREEN}  npm is available${NC}"

# Install npm dependencies
echo ""
echo -e "${YELLOW}[3/4] Installing npm dependencies...${NC}"

cd "$TYPESCRIPT_DIR"

if [ -f "package-lock.json" ]; then
    echo "  Using npm ci for reproducible install..."
    npm ci
else
    echo "  Running npm install..."
    npm install
fi

echo -e "${GREEN}  Dependencies installed successfully${NC}"

# Install Playwright browsers
echo ""
echo -e "${YELLOW}[4/4] Installing Playwright browsers...${NC}"

if [ "$ALL_BROWSERS" = true ]; then
    echo "  Installing all browsers (chromium, firefox, webkit)..."
    npx playwright install chromium firefox webkit
else
    echo "  Installing chromium only (use --all-browsers for all)..."
    npx playwright install chromium
fi

echo -e "${GREEN}  Playwright browsers installed successfully${NC}"

# Summary
echo ""
echo -e "${BLUE}============================================${NC}"
echo -e "${GREEN}  Installation Complete!${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""
echo "Next steps:"
echo ""
echo "  1. Start myAgentDesk:"
echo "     cd myAgentDesk && npm run dev"
echo ""
echo "  2. Run acceptance tests:"
echo "     cd tests/acceptance/typescript"
echo "     npx playwright test"
echo ""
echo "  3. Or use Makefile:"
echo "     make acceptance-test-frontend"
echo ""
echo "For more options, see: tests/acceptance/typescript/README.md"

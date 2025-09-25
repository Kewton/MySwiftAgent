#!/bin/bash

# MySwiftAgent Quick Start Script
# Simple one-command startup for immediate development

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}🚀 MySwiftAgent Quick Start${NC}"
echo -e "${BLUE}═══════════════════════════${NC}"
echo ""

# Check if dev-start.sh exists
if [[ ! -f "$SCRIPT_DIR/dev-start.sh" ]]; then
    echo -e "${RED}❌ dev-start.sh not found${NC}"
    exit 1
fi

# Make sure it's executable
chmod +x "$SCRIPT_DIR/dev-start.sh"

echo -e "${YELLOW}⚡ Starting all services...${NC}"
echo ""

# Run the full development startup
"$SCRIPT_DIR/dev-start.sh" start

echo ""
echo -e "${GREEN}🎉 Quick start complete!${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "• Open your browser to http://localhost:8501 for the web interface"
echo "• Use './scripts/dev-start.sh status' to check service health"
echo "• Use './scripts/dev-start.sh logs' to view logs"
echo "• Use './scripts/dev-start.sh stop' to stop all services"
echo ""
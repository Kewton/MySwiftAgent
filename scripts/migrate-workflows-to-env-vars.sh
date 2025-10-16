#!/bin/bash

# Workflow Migration Script
# Converts hardcoded URLs to environment variable placeholders in GraphAI workflow YAML files

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}🔧 GraphAI Workflow Migration Script${NC}"
echo -e "${BLUE}=====================================${NC}"
echo ""

# URL mapping for replacement
declare -A URL_MAP=(
  # ExpertAgent
  ["http://127.0.0.1:8104"]="\${EXPERTAGENT_BASE_URL}"
  ["http://localhost:8104"]="\${EXPERTAGENT_BASE_URL}"
  ["http://expertagent:8000"]="\${EXPERTAGENT_BASE_URL}"

  # GraphAI Server
  ["http://127.0.0.1:8105"]="\${GRAPHAISERVER_BASE_URL}"
  ["http://localhost:8105"]="\${GRAPHAISERVER_BASE_URL}"
  ["http://graphaiserver:8000"]="\${GRAPHAISERVER_BASE_URL}"

  # MyVault
  ["http://127.0.0.1:8103"]="\${MYVAULT_BASE_URL}"
  ["http://localhost:8103"]="\${MYVAULT_BASE_URL}"
  ["http://myvault:8000"]="\${MYVAULT_BASE_URL}"

  # JobQueue
  ["http://127.0.0.1:8101"]="\${JOBQUEUE_BASE_URL}"
  ["http://localhost:8101"]="\${JOBQUEUE_BASE_URL}"
  ["http://jobqueue:8000"]="\${JOBQUEUE_BASE_URL}"

  # MyScheduler
  ["http://127.0.0.1:8102"]="\${MYSCHEDULER_BASE_URL}"
  ["http://localhost:8102"]="\${MYSCHEDULER_BASE_URL}"
  ["http://myscheduler:8000"]="\${MYSCHEDULER_BASE_URL}"
)

# Find all workflow YAML files
WORKFLOW_DIRS=(
  "$PROJECT_ROOT/docker-compose-data/graphaiserver/config/graphai"
  "$PROJECT_ROOT/graphAiServer/config/graphai"
)

TOTAL_FILES=0
MODIFIED_FILES=0
TOTAL_REPLACEMENTS=0

for WORKFLOW_DIR in "${WORKFLOW_DIRS[@]}"; do
  if [[ ! -d "$WORKFLOW_DIR" ]]; then
    echo -e "${YELLOW}⚠️  Directory not found: $WORKFLOW_DIR (skipping)${NC}"
    continue
  fi

  echo -e "${BLUE}📂 Processing directory: $WORKFLOW_DIR${NC}"

  # Find all .yml and .yaml files
  while IFS= read -r -d '' file; do
    ((TOTAL_FILES++))

    # Check if file contains any hardcoded URLs
    NEEDS_UPDATE=false
    for hardcoded_url in "${!URL_MAP[@]}"; do
      if grep -q "$hardcoded_url" "$file"; then
        NEEDS_UPDATE=true
        break
      fi
    done

    if [[ "$NEEDS_UPDATE" == "false" ]]; then
      echo -e "  ✓ No changes needed: $(basename "$file")"
      continue
    fi

    # Create backup
    BACKUP_FILE="${file}.backup_$(date +%Y%m%d_%H%M%S)"
    cp "$file" "$BACKUP_FILE"

    # Perform replacements
    FILE_REPLACEMENTS=0
    for hardcoded_url in "${!URL_MAP[@]}"; do
      env_var="${URL_MAP[$hardcoded_url]}"

      # Count occurrences before replacement
      COUNT=$(grep -o "$hardcoded_url" "$file" | wc -l | tr -d ' ')

      if [[ "$COUNT" -gt 0 ]]; then
        # Escape special characters for sed
        ESCAPED_URL=$(echo "$hardcoded_url" | sed 's/[.[\*^$]/\\&/g')
        ESCAPED_VAR=$(echo "$env_var" | sed 's/[.[\*^$]/\\&/g')

        # Replace in file
        sed -i.tmp "s|$ESCAPED_URL|$ESCAPED_VAR|g" "$file"
        rm -f "${file}.tmp"

        ((FILE_REPLACEMENTS += COUNT))
        ((TOTAL_REPLACEMENTS += COUNT))

        echo -e "    ${GREEN}✓${NC} Replaced $COUNT occurrence(s) of '$hardcoded_url' → '$env_var'"
      fi
    done

    if [[ "$FILE_REPLACEMENTS" -gt 0 ]]; then
      ((MODIFIED_FILES++))
      echo -e "  ${GREEN}✓ Modified: $(basename "$file") ($FILE_REPLACEMENTS replacements)${NC}"
      echo -e "    Backup saved: $BACKUP_FILE"
    else
      # Remove backup if no changes were made
      rm -f "$BACKUP_FILE"
    fi

  done < <(find "$WORKFLOW_DIR" -type f \( -name "*.yml" -o -name "*.yaml" \) -print0)
done

echo ""
echo -e "${BLUE}=====================================${NC}"
echo -e "${GREEN}✅ Migration complete!${NC}"
echo ""
echo -e "Summary:"
echo -e "  Total files scanned: ${TOTAL_FILES}"
echo -e "  Files modified: ${MODIFIED_FILES}"
echo -e "  Total URL replacements: ${TOTAL_REPLACEMENTS}"
echo ""

if [[ "$MODIFIED_FILES" -gt 0 ]]; then
  echo -e "${YELLOW}⚠️  Backup files created with .backup_* suffix${NC}"
  echo -e "${YELLOW}⚠️  Please test the migrated workflows before deleting backups${NC}"
  echo ""
  echo -e "To remove all backup files after testing:"
  echo -e "  find $PROJECT_ROOT -name '*.backup_*' -delete"
  echo ""
fi

echo -e "${BLUE}Next steps:${NC}"
echo "1. Test workflows in quick-start.sh environment"
echo "2. Test workflows in Docker environment"
echo "3. Verify all URLs resolve correctly"
echo "4. Remove backup files after successful verification"
echo ""

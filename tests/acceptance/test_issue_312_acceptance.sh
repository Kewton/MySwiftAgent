#!/bin/bash
# =============================================================================
# Issue #312 Acceptance Test
#
# Tests: interface_validator.py pattern property name fix
# Target: jobqueue API /api/v1/interface-masters
# =============================================================================

set -e

# Configuration
JOBQUEUE_URL="${JOBQUEUE_URL:-http://localhost:8001}"
EXPERTAGENT_URL="${EXPERTAGENT_URL:-http://localhost:8004}"
TIMESTAMP=$(date +%s)
EVIDENCE_DIR="/tmp/issue312_evidence_${TIMESTAMP}"
CREATED_IDS=()

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}🧹 Cleaning up test resources...${NC}"
    for id in "${CREATED_IDS[@]}"; do
        curl -s -X DELETE "${JOBQUEUE_URL}/api/v1/interface-masters/${id}" > /dev/null 2>&1 || true
        echo "  Deleted: ${id}"
    done
    echo "  Evidence saved to: ${EVIDENCE_DIR}"
}
trap cleanup EXIT

# Helper function: Make API request and validate
test_api() {
    local test_name="$1"
    local expected_status="$2"
    local data="$3"
    local should_have_id="$4"

    echo -e "\n[Test] ${test_name}"

    RESPONSE=$(curl -s -X POST "${JOBQUEUE_URL}/api/v1/interface-masters" \
        -H "Content-Type: application/json" \
        -d "${data}" \
        -w "\n%{http_code}")

    HTTP_CODE=$(echo "$RESPONSE" | tail -1)
    BODY=$(echo "$RESPONSE" | sed '$d')

    # Save evidence
    echo "${BODY}" > "${EVIDENCE_DIR}/${test_name// /_}.json"

    if [ "$HTTP_CODE" = "$expected_status" ]; then
        echo -e "${GREEN}✅ PASSED: HTTP ${HTTP_CODE}${NC}"

        # If we expect an ID, extract and save for cleanup
        if [ "$should_have_id" = "true" ] && command -v jq &> /dev/null; then
            ID=$(echo "$BODY" | jq -r '.interface_id // .id // empty')
            if [ -n "$ID" ] && [ "$ID" != "null" ]; then
                CREATED_IDS+=("$ID")
                echo "  Created ID: ${ID}"
            fi
        fi
        return 0
    else
        echo -e "${RED}❌ FAILED: Expected ${expected_status}, got ${HTTP_CODE}${NC}"
        echo "  Response: ${BODY}"
        return 1
    fi
}

# =============================================================================
# Main Test Execution
# =============================================================================

echo "=============================================="
echo "Issue #312 Acceptance Test"
echo "=============================================="
echo "Timestamp: $(date)"
echo "JobQueue URL: ${JOBQUEUE_URL}"
echo "Evidence Dir: ${EVIDENCE_DIR}"
echo "=============================================="

# Create evidence directory
mkdir -p "${EVIDENCE_DIR}"

# -----------------------------------------------------------------------------
# Step 1: Health Check
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}[Step 1] Health Check${NC}"

if curl -sf "${JOBQUEUE_URL}/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ jobqueue: healthy${NC}"
else
    echo -e "${RED}❌ jobqueue: not responding at ${JOBQUEUE_URL}${NC}"
    echo "Please start jobqueue service first: make dev-platform"
    exit 1
fi

# -----------------------------------------------------------------------------
# Step 2: Main Bug Fix Test - Pattern as Property Name
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}[Step 2] Main Bug Fix: Pattern as Property Name${NC}"
echo "This is the primary test for Issue #312"

test_api "pattern_as_property_name" "201" "{
    \"name\": \"test_pattern_prop_${TIMESTAMP}\",
    \"description\": \"Issue #312 - pattern as property name\",
    \"input_schema\": {
        \"type\": \"object\",
        \"properties\": {
            \"pattern\": {
                \"type\": \"string\",
                \"description\": \"URL pattern for matching\"
            }
        }
    },
    \"output_schema\": {}
}" "true" || exit 1

# -----------------------------------------------------------------------------
# Step 3: Nested Pattern Property
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}[Step 3] Nested Pattern Property${NC}"

test_api "nested_pattern_property" "201" "{
    \"name\": \"test_nested_pattern_${TIMESTAMP}\",
    \"description\": \"Nested pattern property test\",
    \"input_schema\": {
        \"type\": \"object\",
        \"properties\": {
            \"config\": {
                \"type\": \"object\",
                \"properties\": {
                    \"pattern\": {
                        \"type\": \"string\",
                        \"description\": \"Matching pattern\"
                    }
                }
            }
        }
    },
    \"output_schema\": {}
}" "true" || exit 1

# -----------------------------------------------------------------------------
# Step 4: Valid Regex Pattern (Regression Test)
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}[Step 4] Valid Regex Pattern (Regression Test)${NC}"

test_api "valid_regex_pattern" "201" "{
    \"name\": \"test_regex_${TIMESTAMP}\",
    \"description\": \"Valid regex pattern test\",
    \"input_schema\": {
        \"type\": \"object\",
        \"properties\": {
            \"url\": {
                \"type\": \"string\",
                \"pattern\": \"^https?://.+\"
            }
        }
    },
    \"output_schema\": {}
}" "true" || exit 1

# -----------------------------------------------------------------------------
# Step 5: Pattern Property WITH Regex Pattern (Complex Case)
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}[Step 5] Pattern Property with Regex Pattern${NC}"

test_api "pattern_property_with_regex" "201" "{
    \"name\": \"test_complex_${TIMESTAMP}\",
    \"description\": \"Pattern property with regex pattern\",
    \"input_schema\": {
        \"type\": \"object\",
        \"properties\": {
            \"pattern\": {
                \"type\": \"string\",
                \"pattern\": \"^[a-z]+$\",
                \"description\": \"Pattern must be lowercase letters\"
            }
        }
    },
    \"output_schema\": {}
}" "true" || exit 1

# -----------------------------------------------------------------------------
# Step 6: Invalid Regex Pattern (Should Fail with 400)
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}[Step 6] Invalid Regex Pattern (Expect 400)${NC}"

test_api "invalid_regex_pattern" "400" "{
    \"name\": \"test_invalid_${TIMESTAMP}\",
    \"description\": \"Invalid regex pattern test\",
    \"input_schema\": {
        \"type\": \"object\",
        \"properties\": {
            \"field\": {
                \"type\": \"string\",
                \"pattern\": \"[unclosed\"
            }
        }
    },
    \"output_schema\": {}
}" "false" || exit 1

# -----------------------------------------------------------------------------
# Step 7: (Optional) End-to-End via expertAgent
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}[Step 7] End-to-End Check (Optional)${NC}"

if curl -sf "${EXPERTAGENT_URL}/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ expertAgent: available${NC}"
    echo "  Note: Full E2E test via /v1/job-generator requires LLM API key"
    echo "  Skipping LLM-dependent test in automated mode"
else
    echo -e "${YELLOW}⚠️ expertAgent: not available (skipping E2E test)${NC}"
fi

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------
echo -e "\n=============================================="
echo -e "${GREEN}All Tests PASSED ✅${NC}"
echo "=============================================="
echo "Evidence saved to: ${EVIDENCE_DIR}"
echo ""
echo "Created resources (will be cleaned up):"
for id in "${CREATED_IDS[@]}"; do
    echo "  - ${id}"
done
echo "=============================================="

exit 0

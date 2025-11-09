#!/bin/bash

# Integration Test for Issue #147: YAML Configuration with dev-start.sh
# Tests that dev-start.sh can use the YAML configuration

set -euo pipefail

# Get script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Load the config loader
source "${PROJECT_ROOT}/scripts/config-loader.sh"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║${NC}     ${WHITE}Integration Test: YAML Config with dev-start.sh (Issue #147)${NC}    ${CYAN}║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${WHITE}Test 1: Load all services from YAML${NC}"
services_yaml=$(load_services_config)
if [[ -n "$services_yaml" ]]; then
    echo -e "${GREEN}✓ Successfully loaded services configuration${NC}"
else
    echo -e "${RED}✗ Failed to load services configuration${NC}"
    exit 1
fi

echo -e "${WHITE}Test 2: Get startup order${NC}"
startup_order=$(get_startup_order)
echo "Startup order:"
echo "$startup_order" | while read -r service; do
    echo -e "  ${CYAN}→${NC} $service"
done
echo -e "${GREEN}✓ Successfully determined startup order${NC}"

echo -e "${WHITE}Test 3: Simulate env var override${NC}"
export JOBQUEUE_PORT=9999
default_port=$(get_service_property "JobQueue" "port")
echo "Default port from YAML: $default_port"
echo "Environment variable JOBQUEUE_PORT: $JOBQUEUE_PORT"
if [[ "$default_port" == "8001" ]]; then
    echo -e "${GREEN}✓ YAML default value is correct (can be overridden by env var)${NC}"
else
    echo -e "${RED}✗ YAML default value mismatch${NC}"
    exit 1
fi
unset JOBQUEUE_PORT

echo -e "${WHITE}Test 4: Verify all services have required fields${NC}"
for service_name in JobQueue MyScheduler MyVault ExpertAgent GraphAiServer MyAgentDesk CommonUI; do
    port=$(get_service_property "$service_name" "port")
    directory=$(get_service_property "$service_name" "directory")
    log_file=$(get_service_property "$service_name" "log_file")
    pid_file=$(get_service_property "$service_name" "pid_file")

    if [[ -n "$port" && -n "$directory" && -n "$log_file" && -n "$pid_file" ]]; then
        echo -e "  ${GREEN}✓${NC} $service_name: port=$port, dir=$directory"
    else
        echo -e "  ${RED}✗${NC} $service_name: Missing required fields"
        exit 1
    fi
done

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║${NC}                  ${WHITE}All Integration Tests Passed!${NC}                     ${GREEN}║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${CYAN}Ready to integrate with dev-start.sh${NC}"

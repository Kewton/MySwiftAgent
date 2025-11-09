#!/bin/bash

# Environment Variable Loader for MySwiftAgent
# Provides hierarchical environment variable management with validation
#
# Usage:
#   source scripts/lib/env-loader.sh
#   load_env_files [--env-file PATH] [--dry-run]
#
# Features:
#   - Hierarchical loading: .env → .env.local → custom file
#   - Environment variable validation (required vars check)
#   - Service URL auto-configuration
#   - Dry-run mode for configuration preview

# Strict error handling
set -euo pipefail

# Get script directory and project root
if [[ -z "${PROJECT_ROOT:-}" ]]; then
    ENV_LOADER_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
    PROJECT_ROOT="$(dirname "$(dirname "$ENV_LOADER_DIR")")"
fi

# Environment file paths (not readonly to allow testing)
DEFAULT_ENV_FILE="${PROJECT_ROOT}/.env"
LOCAL_ENV_FILE="${PROJECT_ROOT}/.env.local"

# Global variables for options
CUSTOM_ENV_FILE=""
DRY_RUN_MODE=false
ENV_VARS_LOADED=()

# Color definitions (if not already defined)
if [[ -z "${RED:-}" ]]; then
    readonly RED='\033[0;31m'
    readonly GREEN='\033[0;32m'
    readonly YELLOW='\033[1;33m'
    readonly BLUE='\033[0;34m'
    readonly CYAN='\033[0;36m'
    readonly WHITE='\033[1;37m'
    readonly NC='\033[0m'
fi

# Print functions (lightweight versions if not already defined)
env_print_info() {
    echo -e "${BLUE}[ENV-LOADER] INFO: $1${NC}"
}

env_print_success() {
    echo -e "${GREEN}[ENV-LOADER] SUCCESS: $1${NC}"
}

env_print_warning() {
    echo -e "${YELLOW}[ENV-LOADER] WARNING: $1${NC}"
}

env_print_error() {
    echo -e "${RED}[ENV-LOADER] ERROR: $1${NC}" >&2
}

env_print_step() {
    echo -e "${WHITE}[ENV-LOADER] STEP: $1${NC}"
}

# Load a single environment file
# Args:
#   $1: file path
#   $2: priority level (for logging)
load_single_env_file() {
    local file_path="$1"
    local priority_level="${2:-unknown}"

    if [[ ! -f "$file_path" ]]; then
        env_print_warning "File not found: $file_path (skipping)"
        return 0
    fi

    env_print_info "Loading environment file: $file_path (priority: $priority_level)"

    # Read file line by line
    local line_count=0
    while IFS= read -r line || [[ -n "$line" ]]; do
        # Skip empty lines and comments
        if [[ -z "$line" ]] || [[ "$line" =~ ^[[:space:]]*# ]]; then
            continue
        fi

        # Parse KEY=VALUE
        if [[ "$line" =~ ^([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
            local key="${BASH_REMATCH[1]}"
            local value="${BASH_REMATCH[2]}"

            # Remove quotes if present
            value="${value#\"}"
            value="${value%\"}"
            value="${value#\'}"
            value="${value%\'}"

            # Export variable (even in dry-run mode for validation)
            export "$key=$value"

            # Track loaded variables
            ENV_VARS_LOADED+=("$key=$value (from: $file_path)")
            ((line_count++))
        fi
    done < "$file_path"

    env_print_success "Loaded $line_count variables from $file_path"
}

# Merge environment variables from multiple sources
# Priority: custom file > .env.local > .env
merge_env_files() {
    env_print_step "Merging environment files (priority: custom > .env.local > .env)"

    # Clear tracking array
    ENV_VARS_LOADED=()

    # Load in priority order (lowest to highest)
    # Priority 1: .env (base configuration)
    load_single_env_file "$DEFAULT_ENV_FILE" "1-base"

    # Priority 2: .env.local (worktree-specific overrides)
    load_single_env_file "$LOCAL_ENV_FILE" "2-local"

    # Priority 3: custom file (highest priority)
    if [[ -n "$CUSTOM_ENV_FILE" ]]; then
        if [[ ! -f "$CUSTOM_ENV_FILE" ]]; then
            env_print_error "Custom environment file not found: $CUSTOM_ENV_FILE"
            return 1
        fi
        load_single_env_file "$CUSTOM_ENV_FILE" "3-custom"
    fi

    env_print_success "Environment merge complete (${#ENV_VARS_LOADED[@]} variables loaded)"
}

# Validate required environment variables
# Returns: 0 if all required vars are set, 1 otherwise
validate_required_vars() {
    env_print_step "Validating required environment variables..."

    local missing_vars=()

    # Core required variables
    local required_vars=(
        "MSA_MASTER_KEY"
    )

    # Conditional requirements based on service enablement
    # If MYVAULT_ENABLED=true, require MYVAULT_SERVICE_TOKEN
    if [[ "${MYVAULT_ENABLED:-false}" == "true" ]]; then
        required_vars+=("MYVAULT_SERVICE_TOKEN")
    fi

    # Check each required variable
    for var_name in "${required_vars[@]}"; do
        if [[ -z "${!var_name:-}" ]]; then
            missing_vars+=("$var_name")
            env_print_error "Missing required variable: $var_name"
        else
            env_print_info "✓ $var_name is set"
        fi
    done

    # Report results
    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        env_print_error "Validation failed: ${#missing_vars[@]} required variable(s) missing"
        env_print_error "Missing variables: ${missing_vars[*]}"
        return 1
    fi

    env_print_success "All required environment variables are set"
    return 0
}

# Configure service URLs automatically
# Based on running mode (local development vs docker)
configure_service_urls() {
    env_print_step "Configuring service URLs..."

    # Determine base host (localhost for local dev, service name for docker)
    local base_host="${BASE_HOST:-localhost}"

    # Get ports from environment or use defaults
    local myvault_port="${MYVAULT_PORT:-8003}"
    local jobqueue_port="${JOBQUEUE_PORT:-8001}"
    local myscheduler_port="${MYSCHEDULER_PORT:-8002}"
    local expertagent_port="${EXPERTAGENT_PORT:-8004}"
    local graphai_port="${GRAPHAI_PORT:-8005}"
    local myagentdesk_port="${VITE_PORT:-5173}"
    local commonui_port="${COMMONUI_PORT:-8501}"

    # Configure URLs (only if not already set)
    if [[ -z "${MYVAULT_BASE_URL:-}" ]]; then
        export MYVAULT_BASE_URL="http://${base_host}:${myvault_port}"
        env_print_info "Set MYVAULT_BASE_URL=$MYVAULT_BASE_URL"
    fi

    if [[ -z "${JOBQUEUE_API_URL:-}" ]]; then
        export JOBQUEUE_API_URL="http://${base_host}:${jobqueue_port}"
        env_print_info "Set JOBQUEUE_API_URL=$JOBQUEUE_API_URL"
    fi

    if [[ -z "${MYSCHEDULER_BASE_URL:-}" ]]; then
        export MYSCHEDULER_BASE_URL="http://${base_host}:${myscheduler_port}"
        env_print_info "Set MYSCHEDULER_BASE_URL=$MYSCHEDULER_BASE_URL"
    fi

    if [[ -z "${EXPERTAGENT_BASE_URL:-}" ]]; then
        export EXPERTAGENT_BASE_URL="http://${base_host}:${expertagent_port}"
        env_print_info "Set EXPERTAGENT_BASE_URL=$EXPERTAGENT_BASE_URL"
    fi

    if [[ -z "${GRAPHAISERVER_BASE_URL:-}" ]]; then
        export GRAPHAISERVER_BASE_URL="http://${base_host}:${graphai_port}"
        env_print_info "Set GRAPHAISERVER_BASE_URL=$GRAPHAISERVER_BASE_URL"
    fi

    if [[ -z "${MYAGENTDESK_BASE_URL:-}" ]]; then
        export MYAGENTDESK_BASE_URL="http://${base_host}:${myagentdesk_port}"
        env_print_info "Set MYAGENTDESK_BASE_URL=$MYAGENTDESK_BASE_URL"
    fi

    if [[ -z "${COMMONUI_BASE_URL:-}" ]]; then
        export COMMONUI_BASE_URL="http://${base_host}:${commonui_port}"
        env_print_info "Set COMMONUI_BASE_URL=$COMMONUI_BASE_URL"
    fi

    env_print_success "Service URLs configured"
}

# Show current environment configuration (dry-run mode)
show_env_config() {
    echo ""
    echo -e "${CYAN}=====================================================================${NC}"
    echo -e "${CYAN}         Environment Configuration (Dry-Run Mode)                    ${NC}"
    echo -e "${CYAN}=====================================================================${NC}"
    echo ""

    echo -e "${WHITE}Loaded Variables (${#ENV_VARS_LOADED[@]} total):${NC}"
    for var_entry in "${ENV_VARS_LOADED[@]}"; do
        echo -e "  ${BLUE}→${NC} $var_entry"
    done

    echo ""
    echo -e "${WHITE}Service URLs:${NC}"
    echo -e "  ${BLUE}→${NC} MYVAULT_BASE_URL      = ${MYVAULT_BASE_URL:-<not set>}"
    echo -e "  ${BLUE}→${NC} JOBQUEUE_API_URL      = ${JOBQUEUE_API_URL:-<not set>}"
    echo -e "  ${BLUE}→${NC} MYSCHEDULER_BASE_URL  = ${MYSCHEDULER_BASE_URL:-<not set>}"
    echo -e "  ${BLUE}→${NC} EXPERTAGENT_BASE_URL  = ${EXPERTAGENT_BASE_URL:-<not set>}"
    echo -e "  ${BLUE}→${NC} GRAPHAISERVER_BASE_URL= ${GRAPHAISERVER_BASE_URL:-<not set>}"
    echo -e "  ${BLUE}→${NC} MYAGENTDESK_BASE_URL  = ${MYAGENTDESK_BASE_URL:-<not set>}"
    echo -e "  ${BLUE}→${NC} COMMONUI_BASE_URL     = ${COMMONUI_BASE_URL:-<not set>}"

    echo ""
    echo -e "${WHITE}Port Configuration:${NC}"
    echo -e "  ${BLUE}→${NC} MYVAULT_PORT          = ${MYVAULT_PORT:-8003}"
    echo -e "  ${BLUE}→${NC} JOBQUEUE_PORT         = ${JOBQUEUE_PORT:-8001}"
    echo -e "  ${BLUE}→${NC} MYSCHEDULER_PORT      = ${MYSCHEDULER_PORT:-8002}"
    echo -e "  ${BLUE}→${NC} EXPERTAGENT_PORT      = ${EXPERTAGENT_PORT:-8004}"
    echo -e "  ${BLUE}→${NC} GRAPHAI_PORT          = ${GRAPHAI_PORT:-8005}"
    echo -e "  ${BLUE}→${NC} VITE_PORT             = ${VITE_PORT:-5173}"
    echo -e "  ${BLUE}→${NC} COMMONUI_PORT         = ${COMMONUI_PORT:-8501}"

    echo ""
    echo -e "${CYAN}=====================================================================${NC}"
    echo ""
}

# Parse command-line arguments
parse_env_loader_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --env-file)
                if [[ -z "${2:-}" ]]; then
                    env_print_error "--env-file requires a file path argument"
                    return 1
                fi
                CUSTOM_ENV_FILE="$2"
                shift 2
                ;;
            --dry-run)
                DRY_RUN_MODE=true
                shift
                ;;
            *)
                env_print_warning "Unknown option: $1 (ignoring)"
                shift
                ;;
        esac
    done
}

# Main entry point: Load environment files
# Args: [--env-file PATH] [--dry-run]
load_env_files() {
    env_print_step "Starting environment variable loader..."

    # Parse arguments
    if ! parse_env_loader_args "$@"; then
        return 1
    fi

    # Show dry-run notice
    if [[ "$DRY_RUN_MODE" == true ]]; then
        env_print_info "Dry-run mode enabled (services will not start)"
    fi

    # Step 1: Merge environment files
    if ! merge_env_files; then
        env_print_error "Failed to merge environment files"
        return 1
    fi

    # Step 2: Configure service URLs
    configure_service_urls

    # Step 3: Validate required variables
    if ! validate_required_vars; then
        env_print_error "Environment validation failed"
        return 1
    fi

    # Step 4: Show configuration (if dry-run)
    if [[ "$DRY_RUN_MODE" == true ]]; then
        show_env_config
    fi

    env_print_success "Environment loader completed successfully"
    return 0
}

# Export functions for use in other scripts
export -f load_env_files
export -f merge_env_files
export -f validate_required_vars
export -f configure_service_urls
export -f show_env_config
export -f load_single_env_file
export -f parse_env_loader_args

# Export variables
export PROJECT_ROOT
export DEFAULT_ENV_FILE
export LOCAL_ENV_FILE

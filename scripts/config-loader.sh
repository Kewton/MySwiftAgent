#!/bin/bash

# ============================================================================
# YAML Configuration Loader for MySwiftAgent (Issue #147)
# ============================================================================
#
# This module provides functions to load and parse YAML configuration files
# for service definitions and dependencies.
#
# Features:
#   - Automatic parser detection (yq or Python fallback)
#   - Service configuration loading
#   - Dependency resolution and startup ordering
#   - YAML validation
#   - Support for custom configuration files
#
# Usage:
#   source scripts/config-loader.sh
#   config=$(load_services_config)
#   startup_order=$(get_startup_order)
#
# ============================================================================

set -eo pipefail

# Script directory
if [[ -n "${BASH_SOURCE[0]:-}" ]]; then
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
else
    SCRIPT_DIR="$(pwd)/scripts"
fi
CONFIG_DIR="${SCRIPT_DIR}/config"

# Default configuration files
DEFAULT_SERVICES_CONFIG="${CONFIG_DIR}/services.yaml"
DEFAULT_DEPENDENCIES_CONFIG="${CONFIG_DIR}/dependencies.yaml"

# Parser mode detection
YAML_PARSER_MODE=""

# Check if yq is available
check_yq_available() {
    if command -v yq &> /dev/null; then
        YAML_PARSER_MODE="yq"
        return 0
    else
        YAML_PARSER_MODE="python"
        return 1
    fi
}

# Parse YAML using yq
parse_yaml_with_yq() {
    local yaml_file="$1"
    local query="$2"

    if [[ ! -f "$yaml_file" ]]; then
        echo "Error: YAML file not found: $yaml_file" >&2
        return 1
    fi

    yq eval "$query" "$yaml_file"
}

# Parse YAML using Python
parse_yaml_with_python() {
    local yaml_file="$1"
    local query="$2"

    if [[ ! -f "$yaml_file" ]]; then
        echo "Error: YAML file not found: $yaml_file" >&2
        return 1
    fi

    python3 -c "
import yaml
import sys

try:
    with open('$yaml_file', 'r') as f:
        data = yaml.safe_load(f)

    # Simple query parser for basic queries like '.services[0].name'
    query = '$query'

    # Remove leading dot if present
    if query.startswith('.'):
        query = query[1:]

    # Navigate the data structure
    result = data
    for part in query.replace('[', '.').replace(']', '').split('.'):
        if part:
            if part.isdigit():
                result = result[int(part)]
            else:
                result = result[part]

    if isinstance(result, (dict, list)):
        print(yaml.dump(result, default_flow_style=False))
    else:
        print(result)

except Exception as e:
    print(f'Error parsing YAML: {e}', file=sys.stderr)
    sys.exit(1)
"
}

# Generic YAML query function
query_yaml() {
    local yaml_file="$1"
    local query="$2"

    # Auto-detect parser if not set
    if [[ -z "$YAML_PARSER_MODE" ]]; then
        check_yq_available
    fi

    case "$YAML_PARSER_MODE" in
        yq)
            parse_yaml_with_yq "$yaml_file" "$query"
            ;;
        python)
            parse_yaml_with_python "$yaml_file" "$query"
            ;;
        *)
            echo "Error: Unknown YAML parser mode: $YAML_PARSER_MODE" >&2
            return 1
            ;;
    esac
}

# Validate YAML syntax
validate_yaml() {
    local yaml_file="$1"

    if [[ ! -f "$yaml_file" ]]; then
        echo "Error: YAML file not found: $yaml_file" >&2
        return 1
    fi

    # Try to parse the file
    if [[ "$YAML_PARSER_MODE" == "yq" ]]; then
        if ! yq eval '.' "$yaml_file" >/dev/null 2>&1; then
            echo "Error: Invalid YAML syntax in $yaml_file" >&2
            return 1
        fi
    else
        if ! python3 -c "import yaml; yaml.safe_load(open('$yaml_file'))" 2>/dev/null; then
            echo "Error: Invalid YAML syntax in $yaml_file" >&2
            return 1
        fi
    fi

    return 0
}

# Load services configuration
load_services_config() {
    local config_file="${1:-$DEFAULT_SERVICES_CONFIG}"

    if [[ ! -f "$config_file" ]]; then
        echo "Error: Services configuration file not found: $config_file" >&2
        return 1
    fi

    # Validate first
    if ! validate_yaml "$config_file"; then
        return 1
    fi

    # Return the full services list
    query_yaml "$config_file" ".services"
}

# Load dependencies configuration
load_dependencies_config() {
    local config_file="${1:-$DEFAULT_DEPENDENCIES_CONFIG}"

    if [[ ! -f "$config_file" ]]; then
        echo "Error: Dependencies configuration file not found: $config_file" >&2
        return 1
    fi

    # Validate first
    if ! validate_yaml "$config_file"; then
        return 1
    fi

    # Return the full dependencies
    query_yaml "$config_file" ".dependencies"
}

# Get service count
get_service_count() {
    local config_file="${1:-$DEFAULT_SERVICES_CONFIG}"

    if [[ "$YAML_PARSER_MODE" == "yq" ]]; then
        query_yaml "$config_file" ".services | length"
    else
        python3 -c "
import yaml
with open('$config_file', 'r') as f:
    data = yaml.safe_load(f)
print(len(data['services']))
"
    fi
}

# Get service by name
get_service_by_name() {
    local service_name="$1"
    local config_file="${2:-$DEFAULT_SERVICES_CONFIG}"

    if [[ "$YAML_PARSER_MODE" == "yq" ]]; then
        query_yaml "$config_file" ".services[] | select(.name == \"$service_name\")"
    else
        python3 -c "
import yaml
with open('$config_file', 'r') as f:
    data = yaml.safe_load(f)

for service in data['services']:
    if service['name'] == '$service_name':
        print(yaml.dump(service, default_flow_style=False))
        break
"
    fi
}

# Get service property
get_service_property() {
    local service_name="$1"
    local property="$2"
    local config_file="${3:-$DEFAULT_SERVICES_CONFIG}"

    if [[ "$YAML_PARSER_MODE" == "yq" ]]; then
        query_yaml "$config_file" ".services[] | select(.name == \"$service_name\") | .$property"
    else
        python3 -c "
import yaml
with open('$config_file', 'r') as f:
    data = yaml.safe_load(f)

for service in data['services']:
    if service['name'] == '$service_name':
        value = service.get('$property')
        if value is not None:
            print(value)
        break
"
    fi
}

# Get startup order based on dependencies
get_startup_order() {
    local deps_file="${1:-$DEFAULT_DEPENDENCIES_CONFIG}"

    python3 -c "
import yaml

with open('$deps_file', 'r') as f:
    data = yaml.safe_load(f)

dependencies = data['dependencies']

# Topological sort
startup_order = []
visited = set()

def visit(service):
    if service in visited:
        return
    visited.add(service)

    if service in dependencies:
        for dep in dependencies[service].get('depends_on', []):
            visit(dep)

    startup_order.append(service)

# Visit all services
for service in dependencies:
    visit(service)

# Print in order
for service in startup_order:
    print(service)
"
}

# Check if parser is available
check_yaml_parser() {
    check_yq_available || true  # Don't fail if yq not available
    echo "YAML Parser Mode: $YAML_PARSER_MODE"

    if [[ "$YAML_PARSER_MODE" == "python" ]]; then
        if ! python3 -c "import yaml" 2>/dev/null; then
            echo "Error: Python yaml module not available. Install with: pip install pyyaml" >&2
            return 1
        fi
    fi

    return 0
}

# Initialize: detect parser mode
check_yq_available || true

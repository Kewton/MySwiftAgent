#!/bin/bash
# Build Docker images with proper version tagging
# This script builds all service images with version tags from pyproject.toml/package.json

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Get project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                                                                               ║${NC}"
echo -e "${CYAN}║   🐳 MySwiftAgent Docker Image Builder                                        ║${NC}"
echo -e "${CYAN}║   ═══════════════════════════════════                                        ║${NC}"
echo -e "${CYAN}║                                                                               ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Registry settings (can be overridden with environment variables)
REGISTRY="${DOCKER_REGISTRY:-ghcr.io/kewton}"
PUSH_IMAGES="${PUSH_IMAGES:-false}"

# Function to extract version from pyproject.toml
get_python_version() {
    local project_dir=$1
    if [[ -f "$project_dir/pyproject.toml" ]]; then
        grep '^version = ' "$project_dir/pyproject.toml" | sed 's/version = "\(.*\)"/\1/'
    else
        echo "unknown"
    fi
}

# Function to extract version from package.json
get_node_version() {
    local project_dir=$1
    if [[ -f "$project_dir/package.json" ]]; then
        grep '"version":' "$project_dir/package.json" | head -1 | sed 's/.*"version": "\(.*\)".*/\1/'
    else
        echo "unknown"
    fi
}

# Function to build and tag image
build_image() {
    local service_name=$1
    local service_dir=$2
    local version=$3

    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}🔨 Building ${service_name}...${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    local image_name="myswiftagent-${service_name}"

    # Build tags
    local tags=(
        "${image_name}:${version}"
        "${image_name}:latest"
    )

    # Add registry tags if pushing
    if [[ "$PUSH_IMAGES" == "true" ]]; then
        tags+=(
            "${REGISTRY}/${image_name}:${version}"
            "${REGISTRY}/${image_name}:latest"
        )
    fi

    # Build tag arguments
    local tag_args=""
    for tag in "${tags[@]}"; do
        tag_args="$tag_args -t $tag"
    done

    echo -e "${YELLOW}📦 Service:${NC} $service_name"
    echo -e "${YELLOW}📁 Directory:${NC} $service_dir"
    echo -e "${YELLOW}🏷️  Version:${NC} $version"
    echo -e "${YELLOW}🏷️  Tags:${NC}"
    for tag in "${tags[@]}"; do
        echo -e "   ${GREEN}✓${NC} $tag"
    done
    echo ""

    # Build image
    if docker build $tag_args "$service_dir"; then
        echo -e "${GREEN}✅ Successfully built ${service_name}${NC}"

        # Push images if requested
        if [[ "$PUSH_IMAGES" == "true" ]]; then
            echo -e "${CYAN}📤 Pushing images to registry...${NC}"
            docker push "${REGISTRY}/${image_name}:${version}"
            docker push "${REGISTRY}/${image_name}:latest"
            echo -e "${GREEN}✅ Successfully pushed ${service_name}${NC}"
        fi
    else
        echo -e "${RED}❌ Failed to build ${service_name}${NC}"
        return 1
    fi

    echo ""
}

# Parse command line arguments
SERVICES=()
while [[ $# -gt 0 ]]; do
    case $1 in
        --push)
            PUSH_IMAGES=true
            shift
            ;;
        --registry)
            REGISTRY="$2"
            shift 2
            ;;
        --service)
            SERVICES+=("$2")
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --push              Push images to registry after building"
            echo "  --registry REGISTRY Set Docker registry (default: ghcr.io/kewton)"
            echo "  --service SERVICE   Build specific service (can be used multiple times)"
            echo "  --help              Show this help message"
            echo ""
            echo "Services: jobqueue, myscheduler, expertagent, graphaiserver, commonui"
            echo ""
            echo "Examples:"
            echo "  $0                                  # Build all services locally"
            echo "  $0 --service jobqueue               # Build only jobqueue"
            echo "  $0 --push --registry ghcr.io/myorg # Build and push to custom registry"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# If no specific services specified, build all
if [[ ${#SERVICES[@]} -eq 0 ]]; then
    SERVICES=(jobqueue myscheduler expertagent graphaiserver commonui)
fi

echo -e "${CYAN}🔧 Configuration:${NC}"
echo -e "   ${YELLOW}Registry:${NC} $REGISTRY"
echo -e "   ${YELLOW}Push images:${NC} $PUSH_IMAGES"
echo -e "   ${YELLOW}Services:${NC} ${SERVICES[*]}"
echo ""

# Build each service
SUCCESS_COUNT=0
FAIL_COUNT=0

for service in "${SERVICES[@]}"; do
    case $service in
        jobqueue)
            VERSION=$(get_python_version "jobqueue")
            build_image "jobqueue" "jobqueue" "$VERSION" && ((SUCCESS_COUNT++)) || ((FAIL_COUNT++))
            ;;
        myscheduler)
            VERSION=$(get_python_version "myscheduler")
            build_image "myscheduler" "myscheduler" "$VERSION" && ((SUCCESS_COUNT++)) || ((FAIL_COUNT++))
            ;;
        expertagent)
            VERSION=$(get_python_version "expertAgent")
            build_image "expertagent" "expertAgent" "$VERSION" && ((SUCCESS_COUNT++)) || ((FAIL_COUNT++))
            ;;
        graphaiserver)
            VERSION=$(get_node_version "graphAiServer")
            build_image "graphaiserver" "graphAiServer" "$VERSION" && ((SUCCESS_COUNT++)) || ((FAIL_COUNT++))
            ;;
        commonui)
            VERSION=$(get_python_version "commonUI")
            build_image "commonui" "commonUI" "$VERSION" && ((SUCCESS_COUNT++)) || ((FAIL_COUNT++))
            ;;
        *)
            echo -e "${RED}❌ Unknown service: $service${NC}"
            ((FAIL_COUNT++))
            ;;
    esac
done

# Summary
echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                                                                               ║${NC}"
echo -e "${CYAN}║   📊 Build Summary                                                            ║${NC}"
echo -e "${CYAN}║   ═══════════════                                                            ║${NC}"
echo -e "${CYAN}║                                                                               ║${NC}"
echo -e "${CYAN}║   ${GREEN}✅ Successful: $SUCCESS_COUNT${NC}                                                           ${CYAN}║${NC}"
echo -e "${CYAN}║   ${RED}❌ Failed:     $FAIL_COUNT${NC}                                                           ${CYAN}║${NC}"
echo -e "${CYAN}║                                                                               ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════════════════════╝${NC}"

# Exit with appropriate code
if [[ $FAIL_COUNT -gt 0 ]]; then
    exit 1
else
    exit 0
fi

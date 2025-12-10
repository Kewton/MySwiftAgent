# =============================================================================
# MySwiftAgent Root Makefile - Layer-based Development Commands
# =============================================================================
#
# This Makefile provides layer-based Docker Compose orchestration for the
# MySwiftAgent microservices architecture.
#
# Architecture Layers:
#   Platform  - Core infrastructure (valkey, jobqueue, myscheduler, myvault, langfuse)
#   Agent     - AI services (expertagent, graphaiserver)
#   Frontend  - UI applications (commonui, myagentdesk)
#
# Usage:
#   make help           # Show available commands
#   make dev-all        # Start all services
#   make down           # Stop all services
#
# =============================================================================

# Shell and Make settings
SHELL := /bin/bash
.DEFAULT_GOAL := help

# =============================================================================
# Configuration Variables
# =============================================================================

# Docker Compose files
COMPOSE_PLATFORM := docker-compose.platform.yml
COMPOSE_AGENT := docker-compose.agent.yml
COMPOSE_FRONTEND := docker-compose.frontend.yml

# Network configuration
NETWORK_NAME := myswiftagent-network

# Port configuration for health checks
MYVAULT_PORT := 8003
JOBQUEUE_PORT := 8001
EXPERTAGENT_PORT := 8004

# Health check timeouts (seconds)
HEALTH_CHECK_TIMEOUT := 60
HEALTH_CHECK_INTERVAL := 5

# Docker Compose command (v2 syntax)
DOCKER_COMPOSE := docker compose

# =============================================================================
# PHONY Targets Declaration
# =============================================================================

.PHONY: help
.PHONY: dev-platform dev-agent dev-frontend dev-all init-myvault
.PHONY: down down-platform down-agent down-frontend
.PHONY: stop stop-platform stop-agent stop-frontend
.PHONY: logs logs-platform logs-agent logs-frontend
.PHONY: status rebuild clean clean-safe network
.PHONY: _check-platform _check-agent _wait-platform _wait-agent
.PHONY: _check-not-worktree
.PHONY: acceptance-test-platform acceptance-test-agent acceptance-test-e2e
.PHONY: acceptance-test-python acceptance-test-frontend acceptance-test-all

# =============================================================================
# Worktree Guard (Prevent Docker Compose execution in worktree)
# =============================================================================

_check-not-worktree: ## [Internal] Block execution in worktree environment
	@if [ -f .git ] && grep -q "gitdir:" .git 2>/dev/null; then \
		MAIN_REPO=$$(cat .git | sed 's/gitdir: //' | sed 's|/\.git/worktrees/.*||'); \
		echo ""; \
		echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
		echo "❌ ERROR: make コマンドはworktree環境では使用できません"; \
		echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
		echo ""; \
		echo "現在のディレクトリ: $$(pwd)"; \
		echo "メインリポジトリ:   $$MAIN_REPO"; \
		echo ""; \
		echo "📌 worktree環境での開発には以下を使用してください:"; \
		echo "   ./scripts/dev-start.sh start"; \
		echo ""; \
		echo "📌 Docker環境（make）を使用するには、メインリポジトリで実行:"; \
		echo "   cd $$MAIN_REPO && make dev-all"; \
		echo ""; \
		echo "📖 詳細: docs/claude/05-worktree-guide.md"; \
		echo ""; \
		exit 1; \
	fi

# =============================================================================
# Help Target (Default)
# =============================================================================

help: ## Show this help message
	@echo ""
	@echo "MySwiftAgent Development Commands"
	@echo "================================="
	@echo ""
	@echo "Startup Commands:"
	@grep -E '^dev-[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Shutdown Commands:"
	@grep -E '^down[a-zA-Z_-]*:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Safe Stop Commands (Data Preserved):"
	@grep -E '^stop[a-zA-Z_-]*:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Log Commands:"
	@grep -E '^logs[a-zA-Z_-]*:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Utility Commands:"
	@grep -E '^(status|rebuild|clean|clean-safe|network|init-myvault):.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Acceptance Test Commands:"
	@grep -E '^acceptance-test[a-zA-Z_-]*:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Layer Dependencies:"
	@echo "  Platform -> Agent -> Frontend"
	@echo ""

# =============================================================================
# Network Target
# =============================================================================

network: ## Create Docker network if not exists
	@if ! docker network inspect $(NETWORK_NAME) >/dev/null 2>&1; then \
		echo "Creating network: $(NETWORK_NAME)"; \
		docker network create $(NETWORK_NAME); \
	else \
		echo "Network $(NETWORK_NAME) already exists"; \
	fi

# =============================================================================
# Startup Targets
# =============================================================================

dev-platform: _check-not-worktree network ## Start Platform layer (valkey, jobqueue, myscheduler, myvault, langfuse)
	@echo "Starting Platform layer..."
	$(DOCKER_COMPOSE) -f $(COMPOSE_PLATFORM) up -d
	@echo "Platform layer started successfully"

dev-agent: _check-not-worktree _check-platform ## Start Agent layer (expertagent, graphaiserver) - requires Platform
	@echo "Starting Agent layer..."
	$(DOCKER_COMPOSE) -f $(COMPOSE_AGENT) up -d
	@echo "Agent layer started successfully"

dev-frontend: _check-not-worktree _check-agent ## Start Frontend layer (commonui, myagentdesk) - requires Agent
	@echo "Starting Frontend layer..."
	$(DOCKER_COMPOSE) -f $(COMPOSE_FRONTEND) up -d
	@echo "Frontend layer started successfully"

dev-all: _check-not-worktree network ## Start all layers in order (Platform -> Agent -> Frontend)
	@echo "Starting all services..."
	@echo ""
	@echo "[1/6] Starting Platform layer..."
	$(DOCKER_COMPOSE) -f $(COMPOSE_PLATFORM) up -d
	@echo ""
	@echo "[2/6] Waiting for Platform services to be healthy..."
	@$(MAKE) _wait-platform
	@echo ""
	@echo "[3/6] Initializing MyVault default project..."
	@./scripts/init-myvault-default-project.sh || echo "⚠️  MyVault initialization skipped (may need manual setup)"
	@echo ""
	@echo "[4/6] Starting Agent layer..."
	$(DOCKER_COMPOSE) -f $(COMPOSE_AGENT) up -d
	@echo ""
	@echo "[5/6] Waiting for Agent services to be healthy..."
	@$(MAKE) _wait-agent
	@echo ""
	@echo "[6/6] Starting Frontend layer..."
	$(DOCKER_COMPOSE) -f $(COMPOSE_FRONTEND) up -d
	@echo ""
	@echo "All services started successfully!"

init-myvault: ## Initialize MyVault default project (run after dev-platform)
	@echo "Initializing MyVault default project..."
	@./scripts/init-myvault-default-project.sh

# =============================================================================
# Shutdown Targets
# =============================================================================

down: ## Stop all services (all layers)
	@echo "Stopping all services..."
	-$(DOCKER_COMPOSE) -f $(COMPOSE_FRONTEND) down
	-$(DOCKER_COMPOSE) -f $(COMPOSE_AGENT) down
	-$(DOCKER_COMPOSE) -f $(COMPOSE_PLATFORM) down
	@echo "All services stopped"

down-platform: ## Stop Platform layer
	@echo "Stopping Platform layer..."
	$(DOCKER_COMPOSE) -f $(COMPOSE_PLATFORM) down
	@echo "Platform layer stopped"

down-agent: ## Stop Agent layer
	@echo "Stopping Agent layer..."
	$(DOCKER_COMPOSE) -f $(COMPOSE_AGENT) down
	@echo "Agent layer stopped"

down-frontend: ## Stop Frontend layer
	@echo "Stopping Frontend layer..."
	$(DOCKER_COMPOSE) -f $(COMPOSE_FRONTEND) down
	@echo "Frontend layer stopped"

# =============================================================================
# Safe Stop Targets (Containers preserved, data retained)
# =============================================================================

stop: ## Stop all containers without removing (data preserved)
	@echo "Stopping all containers (preserving data)..."
	-$(DOCKER_COMPOSE) -f $(COMPOSE_FRONTEND) stop
	-$(DOCKER_COMPOSE) -f $(COMPOSE_AGENT) stop
	-$(DOCKER_COMPOSE) -f $(COMPOSE_PLATFORM) stop
	@echo "All containers stopped (use 'make dev-all' to restart)"

stop-platform: ## Stop Platform containers without removing
	@echo "Stopping Platform containers..."
	$(DOCKER_COMPOSE) -f $(COMPOSE_PLATFORM) stop
	@echo "Platform containers stopped"

stop-agent: ## Stop Agent containers without removing
	@echo "Stopping Agent containers..."
	$(DOCKER_COMPOSE) -f $(COMPOSE_AGENT) stop
	@echo "Agent containers stopped"

stop-frontend: ## Stop Frontend containers without removing
	@echo "Stopping Frontend containers..."
	$(DOCKER_COMPOSE) -f $(COMPOSE_FRONTEND) stop
	@echo "Frontend containers stopped"

# =============================================================================
# Log Targets
# =============================================================================

logs: ## Show logs for all services (follow mode)
	@echo "Showing logs for all services (Ctrl+C to exit)..."
	$(DOCKER_COMPOSE) -f $(COMPOSE_PLATFORM) -f $(COMPOSE_AGENT) -f $(COMPOSE_FRONTEND) logs -f

logs-platform: ## Show logs for Platform layer (follow mode)
	$(DOCKER_COMPOSE) -f $(COMPOSE_PLATFORM) logs -f

logs-agent: ## Show logs for Agent layer (follow mode)
	$(DOCKER_COMPOSE) -f $(COMPOSE_AGENT) logs -f

logs-frontend: ## Show logs for Frontend layer (follow mode)
	$(DOCKER_COMPOSE) -f $(COMPOSE_FRONTEND) logs -f

# =============================================================================
# Utility Targets
# =============================================================================

status: ## Show status of all services
	@echo ""
	@echo "MySwiftAgent Service Status"
	@echo "==========================="
	@echo ""
	@echo "Platform Layer:"
	@$(DOCKER_COMPOSE) -f $(COMPOSE_PLATFORM) ps 2>/dev/null || echo "  (not running)"
	@echo ""
	@echo "Agent Layer:"
	@$(DOCKER_COMPOSE) -f $(COMPOSE_AGENT) ps 2>/dev/null || echo "  (not running)"
	@echo ""
	@echo "Frontend Layer:"
	@$(DOCKER_COMPOSE) -f $(COMPOSE_FRONTEND) ps 2>/dev/null || echo "  (not running)"
	@echo ""

rebuild: ## Rebuild all Docker images (no cache)
	@echo "Rebuilding all Docker images..."
	$(DOCKER_COMPOSE) -f $(COMPOSE_PLATFORM) build --no-cache
	$(DOCKER_COMPOSE) -f $(COMPOSE_AGENT) build --no-cache
	$(DOCKER_COMPOSE) -f $(COMPOSE_FRONTEND) build --no-cache
	@echo "All images rebuilt successfully"

clean-safe: down ## Stop all services and remove orphans (preserve volumes)
	@echo "Cleaning up (preserving volumes)..."
	-$(DOCKER_COMPOSE) -f $(COMPOSE_FRONTEND) down --remove-orphans
	-$(DOCKER_COMPOSE) -f $(COMPOSE_AGENT) down --remove-orphans
	-$(DOCKER_COMPOSE) -f $(COMPOSE_PLATFORM) down --remove-orphans
	@echo "Cleanup complete (volumes preserved)"

clean: ## Stop all services and remove volumes/orphans (WARNING: data loss)
	@echo ""
	@echo "⚠️  WARNING: This will remove all containers AND volumes!"
	@echo "   Data in docker-compose-data/ will be preserved (host mounts)."
	@echo "   Named volumes (if any) will be DELETED."
	@echo ""
	@read -p "Are you sure you want to continue? [y/N] " confirm && [ "$$confirm" = "y" ] || (echo "Aborted." && exit 1)
	@echo "Cleaning up..."
	-$(DOCKER_COMPOSE) -f $(COMPOSE_FRONTEND) down -v --remove-orphans
	-$(DOCKER_COMPOSE) -f $(COMPOSE_AGENT) down -v --remove-orphans
	-$(DOCKER_COMPOSE) -f $(COMPOSE_PLATFORM) down -v --remove-orphans
	@echo "Cleanup complete"

# =============================================================================
# Internal Targets (Dependency Checks)
# =============================================================================

_check-platform: ## [Internal] Check if Platform layer is running
	@echo "🔍 Checking Platform layer dependencies..."
	@myvault_ok=0; jobqueue_ok=0; \
	if curl -sf http://localhost:$(MYVAULT_PORT)/health >/dev/null 2>&1; then myvault_ok=1; fi; \
	if curl -sf http://localhost:$(JOBQUEUE_PORT)/health >/dev/null 2>&1; then jobqueue_ok=1; fi; \
	if [ $$myvault_ok -eq 0 ]; then \
		echo ""; \
		echo "❌ ERROR: Platform layer is not running!"; \
		echo ""; \
		echo "MyVault health check failed (port $(MYVAULT_PORT))"; \
		echo "Please start Platform layer first:"; \
		echo "  make dev-platform"; \
		echo ""; \
		exit 1; \
	fi; \
	if [ $$jobqueue_ok -eq 0 ]; then \
		echo ""; \
		echo "❌ ERROR: Platform layer is not fully running!"; \
		echo ""; \
		echo "JobQueue health check failed (port $(JOBQUEUE_PORT))"; \
		echo "Please wait for Platform services to be healthy or restart:"; \
		echo "  make dev-platform"; \
		echo ""; \
		exit 1; \
	fi; \
	echo "✅ Platform layer is running (MyVault=OK, JobQueue=OK)"

_check-agent: _check-platform ## [Internal] Check if Agent layer is running (implies Platform check)
	@echo "🔍 Checking Agent layer dependencies..."
	@if ! curl -sf http://localhost:$(EXPERTAGENT_PORT)/health >/dev/null 2>&1; then \
		echo ""; \
		echo "❌ ERROR: Agent layer is not running!"; \
		echo ""; \
		echo "ExpertAgent health check failed (port $(EXPERTAGENT_PORT))"; \
		echo "Please start Agent layer first:"; \
		echo "  make dev-agent"; \
		echo ""; \
		exit 1; \
	fi
	@echo "✅ Agent layer is running (ExpertAgent=OK)"

_wait-platform: ## [Internal] Wait for Platform services to be healthy
	@echo "⏳ Waiting for Platform services..."
	@attempt=1; \
	max_attempts=$$(($(HEALTH_CHECK_TIMEOUT) / $(HEALTH_CHECK_INTERVAL))); \
	while [ $$attempt -le $$max_attempts ]; do \
		myvault_ok=0; jobqueue_ok=0; \
		if curl -sf http://localhost:$(MYVAULT_PORT)/health >/dev/null 2>&1; then myvault_ok=1; fi; \
		if curl -sf http://localhost:$(JOBQUEUE_PORT)/health >/dev/null 2>&1; then jobqueue_ok=1; fi; \
		if [ $$myvault_ok -eq 1 ] && [ $$jobqueue_ok -eq 1 ]; then \
			echo "✅ Platform services are healthy after $$((attempt * $(HEALTH_CHECK_INTERVAL))) seconds"; \
			exit 0; \
		fi; \
		echo "⏳ Attempt $$attempt/$$max_attempts: MyVault=$$([ $$myvault_ok -eq 1 ] && echo 'OK' || echo 'waiting') JobQueue=$$([ $$jobqueue_ok -eq 1 ] && echo 'OK' || echo 'waiting')"; \
		sleep $(HEALTH_CHECK_INTERVAL); \
		attempt=$$((attempt + 1)); \
	done; \
	echo "❌ Timeout waiting for Platform services after $(HEALTH_CHECK_TIMEOUT) seconds"; \
	echo "Checking container logs for debugging..."; \
	$(DOCKER_COMPOSE) -f $(COMPOSE_PLATFORM) logs --tail=20 myvault jobqueue 2>/dev/null || true; \
	exit 1

_wait-agent: ## [Internal] Wait for Agent services to be healthy
	@echo "⏳ Waiting for Agent services..."
	@attempt=1; \
	max_attempts=$$(($(HEALTH_CHECK_TIMEOUT) / $(HEALTH_CHECK_INTERVAL))); \
	while [ $$attempt -le $$max_attempts ]; do \
		if curl -sf http://localhost:$(EXPERTAGENT_PORT)/health >/dev/null 2>&1; then \
			echo "✅ Agent services are healthy after $$((attempt * $(HEALTH_CHECK_INTERVAL))) seconds"; \
			exit 0; \
		fi; \
		echo "⏳ Attempt $$attempt/$$max_attempts: ExpertAgent=waiting"; \
		sleep $(HEALTH_CHECK_INTERVAL); \
		attempt=$$((attempt + 1)); \
	done; \
	echo "❌ Timeout waiting for Agent services after $(HEALTH_CHECK_TIMEOUT) seconds"; \
	echo "Checking container logs for debugging..."; \
	$(DOCKER_COMPOSE) -f $(COMPOSE_AGENT) logs --tail=20 expertagent 2>/dev/null || true; \
	exit 1

# =============================================================================
# Acceptance Test Targets
# =============================================================================

# TypeScript/Playwright acceptance test directory
ACCEPTANCE_TS_DIR := tests/acceptance/typescript

acceptance-test-platform: ## Run Platform layer acceptance tests
	@echo "Running Platform layer acceptance tests..."
	@./scripts/run-acceptance-tests.sh --layer platform

acceptance-test-agent: ## Run Agent layer acceptance tests
	@echo "Running Agent layer acceptance tests..."
	@./scripts/run-acceptance-tests.sh --layer agent

acceptance-test-e2e: ## Run E2E acceptance tests
	@echo "Running E2E acceptance tests..."
	@./scripts/run-acceptance-tests.sh --layer e2e

acceptance-test-python: ## Run all Python acceptance tests (platform + agent + e2e)
	@echo "Running all Python acceptance tests..."
	@./scripts/run-acceptance-tests.sh --all

acceptance-test-frontend: ## Run Frontend acceptance tests (Playwright)
	@echo "Running Frontend acceptance tests..."
	@echo ""
	@if [ ! -d "$(ACCEPTANCE_TS_DIR)/node_modules" ]; then \
		echo "Installing npm dependencies..."; \
		cd $(ACCEPTANCE_TS_DIR) && npm install; \
	fi
	@cd $(ACCEPTANCE_TS_DIR) && npx playwright test
	@echo ""
	@echo "Frontend acceptance tests completed!"

acceptance-test-all: ## Run all acceptance tests (Python + TypeScript)
	@echo "Running all acceptance tests..."
	@echo ""
	@echo "[1/2] Running Python acceptance tests..."
	@./scripts/run-acceptance-tests.sh --all || true
	@echo ""
	@echo "[2/2] Running Frontend acceptance tests..."
	@$(MAKE) acceptance-test-frontend
	@echo ""
	@echo "All acceptance tests completed!"

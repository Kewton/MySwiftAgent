.PHONY: help install dev test run lint format clean

help: ## Show this help message
	@echo "MyScheduler Development Commands"
	@echo "==============================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	uv sync

dev: ## Install dependencies including dev dependencies
	uv sync --extra dev

test: ## Run tests
	uv run pytest tests/ -v

run: ## Start the development server
	uv run uvicorn app.main:app --reload

lint: ## Run linting
	uv run ruff check .

format: ## Format code
	uv run ruff format .

type-check: ## Run type checking
	uv run mypy app/

check-all: lint type-check test ## Run all checks (lint, type-check, test)

clean: ## Clean cache files
	find . -type d -name "__pycache__" -delete
	find . -type f -name "*.pyc" -delete
	rm -f data/jobs.db

example: ## Run usage example
	uv run python example_usage.py

docker-build: ## Build Docker image
	docker build -t myscheduler .

docker-run: ## Run Docker container
	docker run -d --name myscheduler -p 8000:8000 myscheduler

docker-test: docker-build ## Build and test Docker image with health checks
	@echo "🐳 Building and testing Docker image..."
	@docker rm -f myscheduler-test 2>/dev/null || true
	docker run --rm -d --name myscheduler-test -p 8000:8000 myscheduler
	@echo "⏳ Waiting for container to start..."
	@for i in 1 2 3 4 5 6; do \
		sleep 5; \
		if curl -sf http://localhost:8000/health > /dev/null 2>&1; then \
			echo "✅ Container is ready after $$((i * 5)) seconds"; \
			break; \
		fi; \
		echo "⏳ Attempt $$i/6: Container not ready yet, waiting..."; \
		if [ $$i -eq 6 ]; then \
			echo "❌ Container failed to start after 30 seconds"; \
			docker logs myscheduler-test || true; \
			docker stop myscheduler-test 2>/dev/null || true; \
			exit 1; \
		fi; \
	done
	@echo "🔍 Testing health endpoint..."
	curl -f http://localhost:8000/health || (docker stop myscheduler-test && exit 1)
	@echo ""
	@echo "🔍 Testing API endpoints..."
	curl -f http://localhost:8000/api/v1/jobs/ || (docker stop myscheduler-test && exit 1)
	@echo ""
	@echo "✅ All Docker tests passed!"
	@docker stop myscheduler-test

docker-stop: ## Stop Docker container
	docker stop myscheduler 2>/dev/null || true
	docker rm myscheduler 2>/dev/null || true
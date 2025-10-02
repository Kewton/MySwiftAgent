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
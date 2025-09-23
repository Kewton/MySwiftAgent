# MySwiftAgent Project Overview

## Purpose
MySwiftAgent is a lightweight personal AI agent/LLM workflow system designed for quick and flexible responses with modular extensibility. The project currently contains two main components:

1. **MyScheduler** - A scheduling system
2. **JobQueue** - A FastAPI-based HTTP API job queue with async execution and persistence

## Key Features
- ⚡ Swift: Lightweight operation with flexible responses
- 🧩 Extensible: Modular functionality addition
- 🎯 Personalized: User-customizable for specific purposes
- 🔄 Workflow-oriented: LLM-centric flexible workflow design

## Current Focus
The project is currently working on the JobQueue component, which allows arbitrary HTTP API calls to be executed as jobs with async execution, persistence, and monitoring capabilities.

## Tech Stack
- **Language**: Python 3.12+
- **Framework**: FastAPI for web API
- **Database**: SQLite with aiosqlite for async operations
- **Package Management**: uv (modern Python package manager)
- **Testing**: pytest with asyncio support
- **Code Quality**: Ruff (linting + formatting), MyPy (type checking)
- **Deployment**: Docker containerization
- **CI/CD**: GitHub Actions

## Repository Structure
```
├── myscheduler/          # Scheduler component
├── jobqueue/             # Job queue component (current focus)
│   ├── app/             # Application code
│   │   ├── main.py      # FastAPI entry point
│   │   ├── core/        # Core functionality (config, DB, worker)
│   │   ├── models/      # Database models
│   │   ├── schemas/     # Pydantic schemas
│   │   └── api/         # API endpoints
│   ├── tests/           # Test code
│   │   ├── unit/        # Unit tests
│   │   ├── integration/ # Integration tests
│   │   └── conftest.py  # Test configuration
│   └── pyproject.toml   # Project configuration
├── .github/workflows/   # CI/CD workflows
└── CLAUDE.md           # Development guidelines
```
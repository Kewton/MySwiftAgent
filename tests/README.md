# MySwiftAgent Tests

This directory contains integration tests and acceptance tests for MySwiftAgent.

## Quick Reference - Test Locations

| Test Type | Location | Run Environment | Command |
|-----------|----------|-----------------|---------|
| Unit Tests | `{project}/tests/unit/` | CI + Local | Run within project directory |
| Integration Tests | `tests/integration/` | CI + Local | `make test-integration` |
| Acceptance Tests | `tests/acceptance/` | **Local Only** | `make acceptance-test-{layer}` |

## Quick Start

### Unit Tests (within each project)

```bash
# expertAgent unit tests
cd expertAgent && uv run pytest tests/unit/ -v

# myVault unit tests
cd myVault && uv run pytest tests/unit/ -v

# TypeScript projects
cd myAgentDesk && npm test
```

### Integration Tests (CI target)

```bash
# All integration tests
make test-integration

# Python integration tests only
cd tests/integration/python && uv run pytest . -v

# TypeScript integration tests only
cd tests/integration/typescript && npm test
```

### Acceptance Tests (Local only)

```bash
# Platform layer (myVault, jobqueue, myscheduler)
make acceptance-test-platform

# Agent layer (expertAgent, graphAiServer)
make acceptance-test-agent

# Frontend layer (Playwright UI tests)
make acceptance-test-frontend

# All acceptance tests
make acceptance-test-all
```

## Directory Structure

```
tests/
|-- README.md                    # This file
|-- .env.example                 # Environment variable template
|-- conftest.py                  # L0: Root pytest configuration
|
|-- integration/                 # Integration tests (CI target)
|   |-- python/
|   |   |-- conftest.py          # L1: Python integration fixtures
|   |   |-- platform/            # Platform layer tests
|   |   |-- agent/               # Agent layer tests
|   |   +-- cross_layer/         # Cross-layer tests
|   |
|   +-- typescript/
|       +-- api/                 # API integration tests
|
|-- acceptance/                  # Acceptance tests (Local only)
|   |-- python/
|   |   |-- conftest.py          # L1: Python acceptance fixtures
|   |   |-- pytest.ini           # Acceptance test config
|   |   |-- requirements.txt     # Test dependencies
|   |   |-- platform/            # Platform acceptance tests
|   |   |   +-- conftest.py      # L2: Platform fixtures
|   |   |-- agent/               # Agent acceptance tests
|   |   |   +-- conftest.py      # L2: Agent fixtures
|   |   +-- e2e/                 # E2E scenarios
|   |       |-- conftest.py      # L2: E2E fixtures
|   |       +-- scenarios/       # Scenario scripts
|   |
|   +-- typescript/              # Playwright tests
|       |-- playwright.config.ts # Playwright config
|       |-- package.json         # npm dependencies
|       |-- tsconfig.json        # TypeScript config
|       |-- ui/                  # UI tests
|       +-- e2e/                 # E2E tests
|
+-- fixtures/                    # Shared test fixtures
    |-- __init__.py
    |-- api_responses/           # Mock API responses
    |   |-- myvault/
    |   +-- expertagent/
    |-- test_data/               # Test input data
    |   |-- job_requests/
    |   +-- workflows/
    +-- factories/               # Test data factories
        +-- __init__.py
```

## conftest.py Hierarchy

The pytest configuration follows a hierarchical structure:

| Level | File | Scope | Provides |
|-------|------|-------|----------|
| L0 | `tests/conftest.py` | All tests | `project_root`, markers |
| L1 | `tests/{type}/python/conftest.py` | Test type | `service_urls`, `async_client` |
| L2 | `tests/{type}/python/{layer}/conftest.py` | Layer | Layer-specific clients |

Fixtures are inherited automatically from parent levels.

## Important Notes

### Acceptance Tests are NOT run in CI

Tests in `tests/acceptance/` are **excluded from CI** because they:
- Require external API keys (LLM providers)
- Need running services (Docker containers)
- May incur costs (API calls)

**Before merging PRs**, run acceptance tests locally:

```bash
make acceptance-test-{changed-layer}
```

### Setting up API Keys

1. Copy the environment template:
   ```bash
   cp tests/.env.example tests/.env
   ```

2. Edit `tests/.env` with your API keys

3. Never commit `.env` files to version control

### Starting Services

Before running acceptance tests, start the required services:

```bash
# Platform layer services
make dev-platform

# Agent layer services (includes platform)
make dev-agent

# All services
make dev-all
```

## Markers

Available pytest markers:

| Marker | Description |
|--------|-------------|
| `@pytest.mark.integration` | Integration test |
| `@pytest.mark.e2e` | End-to-end test |
| `@pytest.mark.platform` | Platform layer test |
| `@pytest.mark.agent` | Agent layer test |
| `@pytest.mark.frontend` | Frontend layer test |
| `@pytest.mark.requires_api_key` | Test requires external API key |
| `@pytest.mark.acceptance` | Acceptance test (local-only) |
| `@pytest.mark.slow` | Slow-running test |

## Related Documentation

- [Quality Standards](../docs/claude/04-quality-standards.md)
- [Development Workflow](../docs/claude/01-development-workflow.md)
- [Make Commands](../README.md#make-commands)

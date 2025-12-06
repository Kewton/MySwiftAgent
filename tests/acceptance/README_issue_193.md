# Issue #193 Acceptance Tests

Server Restart and Page Reload Verification for Job State Persistence

## Overview

This document describes the acceptance tests for Issue #193 and #242, which verify that:

1. Job creation state is persisted to Valkey (L2 cache)
2. After server restart, job state can be recovered from Valkey
3. Multiple server instances can access the same job state via Valkey
4. Graceful degradation when Valkey is unavailable

## Prerequisites

### Required Services

- **Valkey**: Running on `localhost:6379` (or configured via environment)
- **ExpertAgent**: Running on `localhost:8001` (optional for script tests)

### Starting Services

```bash
# Start all services (recommended)
make dev-all

# Or start Valkey only for unit/integration tests
docker-compose up -d valkey
```

## Test Scenarios

### Scenario 1: Job Persistence and Restore

**Purpose**: Verify job state is persisted to Valkey and can be restored after in-memory cache is cleared (simulating server restart).

**Steps**:
1. Create a job via `JobCreationStateManager.create_job_async()`
2. Update progress and mark as completed
3. Clear L1 (in-memory) cache
4. Retrieve job via `get_status_async()`
5. Verify job was restored from Valkey with correct data

**Expected Result**: Job state is fully restored from Valkey including status, progress, job_master_id, and result.

### Scenario 2: Multi-Instance Access

**Purpose**: Verify multiple server instances (horizontal scaling) can access the same job state via shared Valkey.

**Steps**:
1. Instance A creates and completes a job
2. Instance B (separate `JobCreationStateManager` instance) retrieves the job
3. Verify Instance B gets the correct job data

**Expected Result**: Instance B retrieves the job from Valkey and populates its L1 cache.

### Scenario 3: Valkey Fallback Behavior

**Purpose**: Verify graceful degradation when Valkey is unavailable.

**Steps**:
1. Create `JobCreationStateManager` without Valkey client
2. Create and retrieve jobs (L1 only mode)
3. Test connection failure handling

**Expected Result**: System continues to function using L1 cache only, without errors.

## Running Tests

### Integration Tests (pytest)

```bash
# Run integration tests (requires Valkey)
cd expertAgent
uv run pytest tests/integration/test_marp_report_persistence.py -v -m integration

# Run with coverage
uv run pytest tests/integration/test_marp_report_persistence.py \
  --cov=app/services/job_creation_state \
  --cov-report=term-missing
```

### Acceptance Test Script

```bash
# From repository root
./tests/acceptance/test_issue_193_acceptance.sh
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VALKEY_HOST` | `localhost` | Valkey server host |
| `VALKEY_PORT` | `6379` | Valkey server port |
| `VALKEY_TEST_DB` | `15` | Valkey database for tests |
| `EXPERTAGENT_URL` | `http://localhost:8001` | ExpertAgent API URL |

## Test Coverage

### Integration Tests Cover

- `JobCreationStateManager.create_job_async()`
- `JobCreationStateManager.update_progress_async()`
- `JobCreationStateManager.mark_completed_async()`
- `JobCreationStateManager.mark_failed_async()`
- `JobCreationStateManager.get_status_async()`
- `JobCreationStateManager.connect_valkey()`
- `JobCreationStateManager.disconnect_valkey()`
- L1/L2 cache interaction
- Graceful degradation on Valkey failure

### Coverage Target

- Integration test coverage: **50%+**

## Related Issues

- **Issue #193**: Original server restart/page reload issue
- **Issue #239**: JobCreationStateManager Valkey integration
- **Issue #242**: Integration and acceptance test creation
- **Issue #244**: Valkey initialization in main.py lifespan

## Troubleshooting

### Valkey Connection Issues

```bash
# Check if Valkey is running
docker-compose ps valkey

# Test connection
redis-cli -h localhost -p 6379 ping
# Expected: PONG

# Or with Python
python3 -c "import valkey; c = valkey.Valkey(); print(c.ping())"
```

### Test Skipping

If tests are skipped with "Valkey not available", ensure:

1. Valkey container is running
2. Port 6379 is accessible
3. No firewall blocking the connection

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `ValkeyConnectionError: Connection refused` | Valkey not running | Start Valkey with `docker-compose up -d valkey` |
| `ValkeyConnectionError: invalid-host-12345` | Invalid host configuration | Check `VALKEY_HOST` environment variable |
| `Module not found: app.services.valkey_client` | Not in correct directory | Run from `expertAgent/` directory |

## Definition of Done

- [x] Integration tests pass
- [x] Acceptance test script runs successfully
- [x] Coverage >= 50% for integration tests
- [x] Ruff/MyPy errors: 0
- [x] CI/CD green

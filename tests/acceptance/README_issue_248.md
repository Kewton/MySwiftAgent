# Issue #248 Acceptance Tests

myVault Connection Configuration Verification

## Overview

This document describes the acceptance tests for Issue #248, which verify that:

1. myVault connection configuration settings are correctly retrieved
2. Environment variable fallback works when myVault is unavailable
3. Type conversion (string to int/bool) works correctly
4. Valkey and Langfuse connection configurations are properly handled

## Prerequisites

### Required Services

| Service | Default URL | Description |
|---------|-------------|-------------|
| **myVault** | `http://localhost:8103` | Secret management service |
| **expertAgent** | `http://localhost:8104` | AI agent service |
| **Valkey** | `localhost:6379` | Redis-compatible key-value store |
| **Langfuse** | `http://localhost:3001` | LLM observability (optional) |

### Starting Services

```bash
# Start all services (recommended)
make dev-all

# Or start individual services
docker-compose up -d myvault valkey

# Start expertAgent
cd expertAgent && uv run uvicorn app.main:app --port 8104
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MYVAULT_URL` | `http://localhost:8103` | myVault service URL |
| `EXPERTAGENT_URL` | `http://localhost:8104` | expertAgent API URL |
| `VALKEY_HOST` | `localhost` | Valkey server host |
| `VALKEY_PORT` | `6379` | Valkey server port |
| `LANGFUSE_URL` | `http://localhost:3001` | Langfuse service URL |

## Test Scenarios

### Scenario 1: Service Startup Verification

**Purpose**: Verify all required services are running and healthy.

**Steps**:
1. Check myVault health endpoint (`/health`)
2. Check expertAgent health endpoint (`/health`)
3. Verify Valkey connection via ping
4. Check Langfuse health endpoint (optional)

**Expected Result**: All services respond with healthy status.

### Scenario 2: myVault Settings Verification

**Purpose**: Verify myVault contains the expected connection configuration settings.

**Steps**:
1. Query myVault for VALKEY_HOST
2. Query myVault for VALKEY_PORT
3. Query myVault for LANGFUSE_HOST

**Expected Result**: myVault settings are accessible (may require authentication).

### Scenario 3: myVault Priority Test

**Purpose**: Verify myVault has priority over environment variables.

**Steps**:
1. Mock myVault client to return a specific value
2. Set environment variable with different value
3. Call `get_connection_config()`
4. Verify myVault value is returned

**Expected Result**: myVault value takes priority over environment variable.

### Scenario 4: Environment Variable Fallback Test

**Purpose**: Verify fallback to environment variables when myVault is disabled.

**Steps**:
1. Disable myVault integration
2. Set environment variable
3. Call `get_connection_config()`
4. Verify environment variable value is returned

**Expected Result**: Environment variable value is used when myVault is disabled.

### Scenario 5: myVault Error Fallback Test

**Purpose**: Verify graceful fallback when myVault returns an error.

**Steps**:
1. Mock myVault client to raise MyVaultError
2. Set environment variable as fallback
3. Call `get_connection_config()`
4. Verify fallback to environment variable

**Expected Result**: System falls back to environment variable on myVault error.

### Scenario 6: Type Conversion Test

**Purpose**: Verify type conversion for connection configuration values.

**Steps**:
1. Test integer conversion (string "6380" -> int 6380)
2. Test boolean conversion (string "true" -> bool True)
3. Test boolean conversion (string "false" -> bool False)
4. Test string passthrough

**Expected Result**: All type conversions work correctly.

## Running Tests

### Integration Tests (pytest)

```bash
# Run integration tests
cd expertAgent
uv run pytest tests/integration/test_myvault_connection_config.py -v -m integration

# Run with coverage
uv run pytest tests/integration/test_myvault_connection_config.py \
  --cov=core \
  --cov-report=term-missing \
  -v -m integration
```

### Acceptance Test Script

```bash
# From repository root
./tests/acceptance/test_issue_248_acceptance.sh

# With custom URLs
MYVAULT_URL=http://myvault.local:8103 \
EXPERTAGENT_URL=http://expertagent.local:8104 \
./tests/acceptance/test_issue_248_acceptance.sh
```

## Test Coverage

### Integration Tests Cover

- `SecretsManager.get_connection_config()` - myVault priority
- `SecretsManager.get_connection_config()` - environment fallback
- `SecretsManager.get_connection_config()` - type conversion (int, bool, str)
- `SecretsManager.get_connection_config()` - port validation
- `SecretsManager.get_connection_config()` - error handling
- Valkey connection configuration retrieval
- Langfuse connection configuration retrieval

### Coverage Target

- Integration test coverage: **50%+**

## Evidence Collection

The acceptance test script collects evidence in:

```
./dev-reports/acceptance-test-evidence/issue-248/
├── myvault_health.json
├── expertagent_health.json
├── valkey_health.json
├── langfuse_health.json (optional)
└── test_summary.md
```

## Related Issues

- **Issue #248**: myVault connection configuration
- **Issue #250**: `get_connection_config()` implementation
- **Issue #251**: Runtime value resolution
- **Issue #252**: Valkey initialization myVault support
- **Issue #253**: Langfuse HOST myVault support
- **Issue #254**: Integration and acceptance test creation

## Troubleshooting

### myVault Connection Issues

```bash
# Check if myVault is running
curl http://localhost:8103/health

# Expected: {"status": "healthy"}
```

### expertAgent Connection Issues

```bash
# Check if expertAgent is running
curl http://localhost:8104/health

# Expected: {"status": "healthy", "service": "expertAgent", ...}
```

### Valkey Connection Issues

```bash
# Check if Valkey is running
redis-cli -h localhost -p 6379 ping
# Expected: PONG

# Or with Python
python3 -c "import valkey; c = valkey.Valkey(); print(c.ping())"
```

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `Connection refused` | Service not running | Start the service with `make dev-all` |
| `MyVaultError` | myVault authentication failed | Check MYVAULT_SERVICE_TOKEN |
| `ValueError: not found` | Configuration missing | Set in myVault or environment variable |
| `Port validation error` | Invalid port number | Use port between 1-65535 |

## Definition of Done

- [x] Integration tests created
- [x] Acceptance test script created
- [x] Integration tests pass
- [x] Acceptance test script runs successfully
- [x] Coverage >= 50% for integration tests
- [x] Ruff/MyPy errors: 0
- [x] Evidence collected

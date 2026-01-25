# Health Check Specification

## Overview

The health check module provides comprehensive health monitoring and service readiness verification for all MySwiftAgent microservices. It enables automated startup verification, continuous health monitoring, and service dependency validation.

## Module Location

- **Library**: `scripts/unified-lib/health-check.sh`
- **Integration**: `scripts/unified-start.sh`
- **Tests**: `tests/scripts/test_health_check.sh`

## Features

### Core Capabilities

1. **HTTP Health Endpoint Verification**
   - Checks `/health` endpoints on all services
   - Configurable timeout and retry intervals
   - Response time measurement
   - Status code validation

2. **Service Readiness Verification**
   - Wait for services to become healthy after startup
   - Configurable maximum wait time
   - Progress reporting during wait
   - Batch health verification

3. **Detailed Health Reporting**
   - Process status (PID verification)
   - Port listening status
   - HTTP endpoint availability
   - Response time metrics
   - Service-specific health information

4. **Color-Coded Output**
   - ✅ Green: Healthy/Success
   - ⚠️  Yellow: Warning
   - ❌ Red: Error/Unhealthy
   - ℹ️  Blue: Information

## Configuration

### Default Constants

```bash
DEFAULT_HEALTH_CHECK_TIMEOUT=30    # Maximum wait time in seconds
DEFAULT_HEALTH_CHECK_INTERVAL=1    # Check interval in seconds
```

### Service Endpoints

By default, health checks use the `/health` endpoint on each service's port:

| Service        | Port | Health Endpoint        |
|----------------|------|------------------------|
| myVault        | 8003 | http://localhost:8003/health |
| jobqueue       | 8001 | http://localhost:8001/health |
| myscheduler    | 8002 | http://localhost:8002/health |
| graphAiServer  | 8005 | http://localhost:8005/health |
| expertAgent    | 8004 | http://localhost:8004/health |

**Note**: `commonUI` and `myAgentDesk` do not have `/health` endpoints and are excluded from HTTP health checks.

## API Reference

### Functions

#### `check_service_health(service_name, port, [timeout], [endpoint])`

Check if a service's health endpoint is responding.

**Parameters:**
- `service_name`: Name of the service
- `port`: Port number
- `timeout`: (Optional) Request timeout in seconds (default: 5)
- `endpoint`: (Optional) Health endpoint path (default: `/health`)

**Returns:**
- `0`: Service is healthy (HTTP 200)
- `1`: Service is unhealthy or unreachable

**Example:**
```bash
if check_service_health "myvault" 8003 5 "/health"; then
    echo "myVault is healthy"
fi
```

#### `wait_for_healthy(service_name, port, [max_wait], [endpoint])`

Wait for a service to become healthy with timeout.

**Parameters:**
- `service_name`: Name of the service
- `port`: Port number
- `max_wait`: (Optional) Maximum wait time in seconds (default: 30)
- `endpoint`: (Optional) Health endpoint path (default: `/health`)

**Returns:**
- `0`: Service became healthy within timeout
- `1`: Timeout reached

**Example:**
```bash
if wait_for_healthy "jobqueue" 8001 30; then
    echo "jobqueue is ready"
else
    echo "jobqueue failed to start"
fi
```

#### `check_health_detailed(service_name, port, [timeout], [endpoint])`

Perform comprehensive health check with detailed output.

**Parameters:**
- `service_name`: Name of the service
- `port`: Port number
- `timeout`: (Optional) Request timeout in seconds (default: 5)
- `endpoint`: (Optional) Health endpoint path (default: `/health`)

**Returns:**
- `0`: All checks passed
- `1`: One or more checks failed

**Output includes:**
- Process status
- Port listening status
- HTTP endpoint status
- Response time
- Service health information (if available)

#### `check_all_services_health(service_specs...)`

Check health of multiple services and display summary.

**Parameters:**
- `service_specs`: Array of service specifications in format `"service_name:port[:endpoint]"`

**Returns:**
- Number of failed health checks

**Example:**
```bash
check_all_services_health \
    "myvault:8003" \
    "jobqueue:8001" \
    "myscheduler:8002"
```

#### `wait_for_all_services_healthy(timeout, service_specs...)`

Wait for all services to become healthy.

**Parameters:**
- `timeout`: Maximum wait time per service
- `service_specs`: Array of service specifications

**Returns:**
- Number of services that failed to become healthy

**Example:**
```bash
wait_for_all_services_healthy 30 \
    "myvault:8003" \
    "jobqueue:8001"
```

#### `get_response_time(service_name, port, [timeout], [endpoint])`

Get HTTP response time from service.

**Returns:**
- Response time in seconds, or "timeout" if request times out

#### `get_health_info(service_name, port, [timeout], [endpoint])`

Get health status information from service (JSON response).

**Returns:**
- JSON response from health endpoint, or `{}` if unavailable

#### `quick_health_check(service_name, port, [endpoint])`

Quick health check with minimal output (one-line status).

**Returns:**
- `0`: Healthy
- `1`: Unhealthy

## Usage

### From unified-start.sh

#### Basic Usage

```bash
# Start all services with automatic health checks
./scripts/unified-start.sh start

# Start services without health checks
./scripts/unified-start.sh start --skip-health-check

# Start with custom timeout
./scripts/unified-start.sh start --timeout 60

# Check health of running services
./scripts/unified-start.sh health

# Check health only (without starting)
./scripts/unified-start.sh --health-check-only
```

#### With Timeout Configuration

```bash
# Use 60 second timeout for health checks
./scripts/unified-start.sh start --timeout 60

# Quick health check with default timeout
./scripts/unified-start.sh --health-check-only
```

### From Custom Scripts

```bash
#!/bin/bash

# Load the health check library
source "scripts/unified-lib/common.sh"
source "scripts/unified-lib/health-check.sh"

# Check a single service
if check_service_health "myvault" 8003; then
    echo "myVault is healthy"
fi

# Wait for service to become ready
wait_for_healthy "jobqueue" 8001 30

# Check multiple services
check_all_services_health \
    "myvault:8003" \
    "jobqueue:8001" \
    "myscheduler:8002"
```

## Custom Health Endpoints

### Standard Health Endpoint Response

Services should implement `/health` endpoints that return:

**Success Response (HTTP 200):**
```json
{
  "status": "healthy",
  "service": "myvault",
  "version": "1.0.0",
  "timestamp": "2025-11-09T00:00:00Z"
}
```

**Error Response (HTTP 503):**
```json
{
  "status": "unhealthy",
  "service": "myvault",
  "error": "Database connection failed"
}
```

### Custom Endpoint Configuration

To use a custom health endpoint:

```bash
# Check custom endpoint
check_service_health "myservice" 8080 5 "/api/v1/health"

# Wait for custom endpoint
wait_for_healthy "myservice" 8080 30 "/api/v1/status"
```

## Integration with Unified Start

The health check module is automatically integrated into `unified-start.sh`:

1. **Automatic Health Checks**: After starting services, health checks run automatically
2. **Startup Verification**: Services must become healthy within the configured timeout
3. **Progress Reporting**: Real-time progress updates during health checks
4. **Failure Reporting**: Clear error messages when health checks fail

### Startup Flow

```
Start Services
    ↓
Wait for Process Startup (2-3 seconds per layer)
    ↓
Run Health Checks (configurable timeout)
    ↓
Report Overall Status
```

## Error Handling

### Common Error Scenarios

1. **Service Not Running**
   - Error: "Process not running"
   - Resolution: Check service logs, verify dependencies

2. **Port Not Listening**
   - Error: "Port X not listening"
   - Resolution: Check port conflicts, verify service startup

3. **Health Endpoint Not Responding**
   - Error: "Health endpoint not responding (HTTP XXX)"
   - Resolution: Check service implementation, network connectivity

4. **Timeout Exceeded**
   - Error: "Timeout waiting for service to become healthy"
   - Resolution: Increase timeout, check service performance

### Exit Codes

- `0`: All health checks passed
- `1+`: Number of failed health checks

## Best Practices

### Development

1. **Always implement `/health` endpoints** on new services
2. **Return appropriate HTTP status codes** (200 for healthy, 503 for unhealthy)
3. **Include service metadata** in health responses
4. **Test health checks** before deploying services

### Operations

1. **Use health checks** before running acceptance tests
2. **Set appropriate timeouts** based on service startup times
3. **Monitor health check failures** in CI/CD pipelines
4. **Use `--skip-health-check`** only when necessary

### Testing

1. **Run unit tests** for health check functions
2. **Test with real services** when possible
3. **Verify timeout behavior** works correctly
4. **Test error scenarios** (service down, port conflicts)

## Troubleshooting

### Health Check Fails but Service is Running

1. Check if the service has a `/health` endpoint
2. Verify the port number is correct
3. Check service logs for startup errors
4. Increase timeout if service is slow to start

### Timeout Too Short

**Symptoms:**
- Services fail health checks during startup
- Works when checking manually after startup

**Solution:**
```bash
# Increase timeout
./scripts/unified-start.sh start --timeout 60
```

### Service Excluded from Health Checks

Some services (like `commonUI` and `myAgentDesk`) don't have `/health` endpoints and are automatically excluded from HTTP health checks. They are still verified via process and port checks in the status command.

## Future Enhancements

Potential improvements for future versions:

1. **Custom Health Check Scripts**: Per-service custom health verification
2. **Health Check Metrics**: Collect and report health check statistics
3. **Dependency-Aware Checks**: Check services in dependency order
4. **Health Check Retry Strategies**: Exponential backoff, jitter
5. **Integration with Monitoring**: Export health metrics to monitoring systems

## Related Documentation

- [Unified Start Script Usage](../../scripts/unified-start.sh) - Main startup script
- [Development Workflow](../claude/01-development-workflow.md) - Overall development process
- [Branch Strategy](../claude/03-branch-strategy.md) - Git workflow and branching

## Version History

- **v1.0.0** (2025-11-09): Initial implementation
  - Basic health check functions
  - Integration with unified-start.sh
  - Support for custom endpoints and timeouts
  - Comprehensive test suite

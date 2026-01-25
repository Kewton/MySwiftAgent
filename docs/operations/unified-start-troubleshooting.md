# Unified Start Script - Troubleshooting Guide

This guide helps you diagnose and resolve common issues with the MySwiftAgent unified start script.

## Table of Contents

1. [Error Codes Reference](#error-codes-reference)
2. [Common Errors and Solutions](#common-errors-and-solutions)
3. [Port Conflict Resolution](#port-conflict-resolution)
4. [Service Startup Failures](#service-startup-failures)
5. [Rollback Scenarios](#rollback-scenarios)
6. [Debug Mode](#debug-mode)

---

## Error Codes Reference

The unified start script uses standardized exit codes to indicate specific error conditions:

| Exit Code | Error Type | Description |
|-----------|------------|-------------|
| `0` | SUCCESS | Operation completed successfully |
| `1` | DEPENDENCY_ERROR | Required dependencies are missing (uv, npm, curl) |
| `2` | PORT_CONFLICT | One or more ports are already in use |
| `3` | SERVICE_START_FAILED | A service failed to start |
| `4` | DIRECTORY_NOT_FOUND | Service directory not found |
| `5` | PARTIAL_STARTUP_FAILED | Some services started but others failed (rollback executed) |
| `130` | USER_INTERRUPTED | User interrupted the operation (Ctrl+C) |

---

## Common Errors and Solutions

### Error 1: Missing Dependencies

**Symptoms:**
```
ERROR: uv package manager not found
Error Code: 1
Message: Required dependencies are missing
```

**Solution:**
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install npm (macOS)
brew install node

# Install npm (Ubuntu/Debian)
sudo apt-get install nodejs npm

# Verify installations
uv --version
npm --version
```

---

### Error 2: Port Conflict

**Symptoms:**
```
WARNING: myvault: Port 8003 is in use
Conflicting process:
  PID:     12345
  Command: python
  User:    youruser
ERROR: myvault: Port 8003 is in use. Use --force to kill conflicting processes
```

**Solutions:**

#### Option 1: Use --force flag
```bash
./scripts/unified-start.sh start --force
```
This will automatically kill processes on conflicting ports.

#### Option 2: Manual port cleanup
```bash
# Find process using the port
lsof -ti:8003

# Kill the process
kill -9 $(lsof -ti:8003)

# Then retry
./scripts/unified-start.sh start
```

#### Option 3: Stop all services first
```bash
# Stop all managed services
./scripts/unified-start.sh stop

# Then start fresh
./scripts/unified-start.sh start
```

---

### Error 3: Service Startup Failed

**Symptoms:**
```
ERROR: expertagent: Failed to start (process died immediately)
Last 10 lines of expertagent log:
  ModuleNotFoundError: No module named 'fastapi'
```

**Solutions:**

#### Step 1: Check service logs
```bash
tail -50 logs/expertagent.log
```

#### Step 2: Verify service dependencies
```bash
cd expertAgent
uv sync

# Or for Node.js services
cd myAgentDesk
npm install
```

#### Step 3: Try manual startup
```bash
# Navigate to service directory
cd expertAgent

# Start service manually to see detailed errors
uv run uvicorn app.main:app --host 0.0.0.0 --port 8004
```

#### Step 4: Check configuration
- Verify `.env` files exist in service directories
- Check required environment variables are set
- Verify database connections if applicable

---

### Error 4: Directory Not Found

**Symptoms:**
```
ERROR: myvault: Directory not found: /path/to/myVault
Error Code: 4
```

**Solutions:**

#### Verify you're in the correct worktree
```bash
# Check current branch and worktree
git status
pwd

# If in wrong worktree, switch to correct one
cd /path/to/correct/worktree
```

#### Check project structure
```bash
# Verify all service directories exist
ls -la | grep -E "(myVault|jobqueue|myscheduler|graphAiServer|expertAgent|myAgentDesk|commonUI)"
```

---

## Port Conflict Resolution

### Quick Port Reference

| Service | Default Port | Check Command |
|---------|--------------|---------------|
| myVault | 8003 | `lsof -ti:8003` |
| jobqueue | 8001 | `lsof -ti:8001` |
| myscheduler | 8002 | `lsof -ti:8002` |
| graphAiServer | 8005 | `lsof -ti:8005` |
| expertAgent | 8004 | `lsof -ti:8004` |
| myAgentDesk | 5173 | `lsof -ti:5173` |
| commonUI | 8501 | `lsof -ti:8501` |

### Bulk Port Cleanup

```bash
# Kill all processes on MySwiftAgent ports
for port in 8001 8002 8003 8004 8005 5173 8501; do
    echo "Checking port $port..."
    lsof -ti:$port && kill -9 $(lsof -ti:$port) || echo "Port $port is free"
done
```

---

## Service Startup Failures

### Common Causes

1. **Missing Python packages**
   ```bash
   cd <service-directory>
   uv sync
   ```

2. **Missing Node.js packages**
   ```bash
   cd <service-directory>
   npm install
   ```

3. **Database connection issues**
   - Check database is running
   - Verify connection strings in `.env`
   - Check database credentials

4. **Permission issues**
   ```bash
   # Check log directory permissions
   ls -la logs/

   # Fix if needed
   chmod 755 logs/
   chmod 644 logs/*.log
   ```

5. **Configuration file missing**
   - Check for required `.env` files
   - Verify configuration templates exist

---

## Rollback Scenarios

The unified start script automatically rolls back started services when an error occurs.

### When Rollback Triggers

1. **Service startup failure**: If any service fails to start, all previously started services are stopped
2. **User interruption** (Ctrl+C): All started services are stopped cleanly
3. **Dependency check failure**: No services are started (no rollback needed)

### Rollback Process

```
1. Error detected
2. ROLLBACK initiated
3. Services stopped in reverse order (newest first)
4. PID files cleaned up
5. Error report displayed
6. Exit with appropriate error code
```

### Example Rollback Output

```
═══════════════════════════════════════════════════════════
  ERROR DETECTED - Initiating rollback
═══════════════════════════════════════════════════════════

═══════════════════════════════════════════════════════════
  ROLLBACK: Stopping 3 started service(s)
═══════════════════════════════════════════════════════════

[myscheduler] Rolling back...
[myscheduler]: Stopped
[jobqueue] Rolling back...
[jobqueue]: Stopped
[myvault] Rolling back...
[myvault]: Stopped

Rollback completed - all started services stopped
```

---

## Debug Mode

### Enable Verbose Output

For detailed troubleshooting, you can enable bash debug mode:

```bash
# Run with debug output
bash -x ./scripts/unified-start.sh start

# Or for even more detail
set -x
./scripts/unified-start.sh start
```

### Check Service Status

```bash
#View status of all services
./scripts/unified-start.sh status
```

Expected output:
```
Checking service status...

  myvault: Running (PID: 12345, Port: 8003)
  jobqueue: Not running
  myscheduler: Running but port 8002 not responding (PID: 12346)

Summary: 1 running, 1 stopped, 1 degraded
```

### Manual PID File Inspection

```bash
# List all PID files
ls -la /tmp/myswiftagent/*.pid

# Check specific PID file
cat /tmp/myswiftagent/myvault.pid

# Verify process is running
kill -0 $(cat /tmp/myswiftagent/myvault.pid) && echo "Running" || echo "Not running"
```

### Clean Up Stale State

If you encounter persistent issues:

```bash
# Stop all services
./scripts/unified-start.sh stop

# Remove all PID files
rm -f /tmp/myswiftagent/*.pid

# Clear logs (optional)
rm -f logs/*.log

# Restart
./scripts/unified-start.sh start
```

---

## Advanced Troubleshooting

### Service Won't Stop

```bash
# Find service PID
ps aux | grep <service-name>

# Force kill
kill -9 <PID>

# Clean up PID file
rm /tmp/myswiftagent/<service-name>.pid
```

### Port Still Showing as In Use

```bash
# Detailed port investigation
lsof -i :<port>

# Find all processes using port
lsof -ti:<port>

# Force kill all processes on port
kill -9 $(lsof -ti:<port>)

# Verify port is free
lsof -i :<port> || echo "Port is free"
```

### Check System Resources

```bash
# Check available memory
free -h  # Linux
vm_stat  # macOS

# Check disk space
df -h

# Check CPU load
top -bn1 | head -20
```

---

## Getting Help

If you continue to experience issues:

1. **Check logs**: All service logs are in `logs/` directory
2. **Run status check**: `./scripts/unified-start.sh status`
3. **Review error messages**: Pay attention to error codes and context
4. **Try manual startup**: Start services individually to isolate issues
5. **Check GitHub Issues**: https://github.com/kewton/MySwiftAgent/issues

---

## Quick Reference Commands

```bash
# Start all services
./scripts/unified-start.sh start

# Start with force (kill conflicting ports)
./scripts/unified-start.sh start --force

# Stop all services
./scripts/unified-start.sh stop

# Restart all services
./scripts/unified-start.sh restart

# Check status
./scripts/unified-start.sh status

# View help
./scripts/unified-start.sh --help

# Debug mode
bash -x ./scripts/unified-start.sh start
```

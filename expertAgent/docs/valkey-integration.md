# Valkey Integration Guide

## Overview

This document describes the Valkey persistence integration for expertAgent, providing scalable and reliable conversation data storage.

## Architecture

### Components

1. **ValkeyClient** (`app/services/valkey_client.py`)
   - Async Redis-compatible client
   - Connection pooling
   - JSON serialization/deserialization
   - TTL management

2. **ConversationStoreValkey** (`app/stores/conversation_store_valkey.py`)
   - Implements ConversationStore interface
   - Manages conversation persistence
   - Handles metadata (trace_id, prompt_version)
   - 24-hour TTL by default (configurable)

## Configuration

### Environment Variables

Add the following to your `.env` file:

```bash
# Valkey Configuration
VALKEY_HOST=localhost
VALKEY_PORT=6379
VALKEY_PASSWORD=
VALKEY_DB=0
VALKEY_ENABLED=true
CONVERSATION_STORE_TYPE=valkey  # or "memory" for in-memory storage
VALKEY_TTL_HOURS=24
```

### Docker Compose

Valkey service is defined in `docker-compose.yml`:

```yaml
valkey:
  image: valkey/valkey:latest
  container_name: myswiftagent-valkey
  ports:
    - "6379:6379"
  volumes:
    - ./valkey/data:/data
    - ./valkey/config/valkey.conf:/usr/local/etc/valkey/valkey.conf:ro
  healthcheck:
    test: ["CMD", "valkey-cli", "PING"]
    interval: 30s
    timeout: 10s
    retries: 3
  networks:
    - myswiftagent
  restart: unless-stopped
```

## Usage

### Starting Valkey

#### Using Docker Compose
```bash
docker-compose up -d valkey
```

#### Using dev-start.sh
```bash
./scripts/dev-start.sh start
```

#### For Worktree Environments
```bash
./scripts/setup-valkey-worktree.sh
```

### Python Integration

```python
from app.services.valkey_client import ValkeyClient
from app.stores.conversation_store_valkey import ConversationStoreValkey

# Initialize client
async with ValkeyClient(host="localhost", port=6379) as client:
    # Create store
    store = ConversationStoreValkey(client)

    # Save conversation
    await store.save_conversation(
        conversation_id="123",
        message_history=[{"role": "user", "content": "Hello"}],
        trace_id="trace-456",
        prompt_version="v1.0"
    )

    # Retrieve conversation
    data = await store.get_conversation("123")
```

## Data Persistence

### Storage Format

Conversations are stored as JSON with the following structure:

```json
{
  "conversation_id": "string",
  "message_history": [
    {
      "role": "user|assistant|system",
      "content": "string"
    }
  ],
  "metadata": {
    "trace_id": "string",
    "prompt_version": "string",
    "created_at": "ISO8601 timestamp",
    "updated_at": "ISO8601 timestamp"
  }
}
```

### TTL Management

- Default TTL: 24 hours
- Configurable via `VALKEY_TTL_HOURS` environment variable
- Can be overridden per conversation:

```python
await store.save_conversation(
    conversation_id="123",
    message_history=messages,
    ttl=3600  # 1 hour in seconds
)
```

## Monitoring

### Health Check

```bash
# Using Docker
docker exec myswiftagent-valkey valkey-cli PING

# Using CLI
valkey-cli PING
```

### Memory Usage

```bash
valkey-cli INFO memory
```

### Key Statistics

```bash
valkey-cli INFO stats
```

## Troubleshooting

### Connection Issues

1. **Check Valkey is running:**
   ```bash
   docker ps | grep valkey
   ```

2. **Check port availability:**
   ```bash
   lsof -i :6379
   ```

3. **Test connection:**
   ```bash
   valkey-cli -h localhost -p 6379 PING
   ```

### Data Not Persisting

1. **Check volume mounts:**
   ```bash
   docker inspect myswiftagent-valkey | grep -A 5 Mounts
   ```

2. **Check RDB/AOF settings:**
   ```bash
   valkey-cli CONFIG GET save
   valkey-cli CONFIG GET appendonly
   ```

### Performance Issues

1. **Check memory usage:**
   ```bash
   valkey-cli INFO memory | grep used_memory_human
   ```

2. **Check slow log:**
   ```bash
   valkey-cli SLOWLOG GET 10
   ```

## Testing

### Unit Tests

```bash
pytest expertAgent/tests/unit/test_valkey_client.py
pytest expertAgent/tests/unit/test_conversation_store_valkey.py
```

### Integration Tests

```bash
# Start Valkey first
docker-compose up -d valkey

# Run tests
pytest expertAgent/tests/integration/test_valkey_integration.py
```

### Performance Tests

```bash
pytest expertAgent/tests/performance/test_valkey_performance.py
```

## Security Considerations

1. **Password Protection:** Set `VALKEY_PASSWORD` in production
2. **Network Isolation:** Use Docker networks for service communication
3. **Data Encryption:** Consider TLS for production deployments
4. **Access Control:** Limit network access to Valkey port

## Migration Guide

### From In-Memory to Valkey

1. Set environment variable:
   ```bash
   CONVERSATION_STORE_TYPE=valkey
   ```

2. Restart expertAgent service

3. Existing in-memory data will be lost (plan accordingly)

### Rollback to In-Memory

1. Set environment variable:
   ```bash
   CONVERSATION_STORE_TYPE=memory
   ```

2. Restart expertAgent service

## API Reference

See the source code documentation:
- [ValkeyClient](../app/services/valkey_client.py)
- [ConversationStoreValkey](../app/stores/conversation_store_valkey.py)
- [ConversationStore Interface](../app/stores/interfaces.py)

## Support

For issues or questions, please refer to the main project documentation or create an issue in the GitHub repository.
# Valkey Data Directory

This directory contains Valkey (Redis-compatible) configuration and data files for local development.

## Structure

```
valkey/
├── config/
│   └── valkey.conf    # Valkey server configuration
└── data/
    ├── .gitkeep       # Preserves directory structure in git
    └── *.rdb          # Database dumps (gitignored)
```

## Purpose

Valkey is used for:
- Conversation data persistence in expertAgent
- Session storage
- Caching layer

## Local Development

Valkey is started automatically by:
- `./scripts/dev-start.sh` - Development environment startup
- Docker Compose (docker-compose.yml)

## CI/CD

### GitHub Actions Integration

Valkey service container is automatically started in GitHub Actions CI:
- Uses `valkey/valkey:latest` image
- Accessible at `localhost:6379`
- Health checks via `valkey-cli ping`
- Enables full integration test coverage in CI

### Git Configuration

The `data/` directory structure is preserved in git via `.gitkeep` file,
while actual data files are excluded by `.gitignore` patterns.

## Related Tests

- `expertAgent/tests/integration/test_issue_169_acceptance.py`
- `expertAgent/tests/integration/test_valkey_integration.py`
- `expertAgent/tests/performance/test_valkey_performance.py`

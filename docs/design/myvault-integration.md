# MyVault Integration Policy

**Version:** 1.0.0
**Last Updated:** 2025-10-10
**Status:** Active

---

## 📋 Overview

This document defines the standard integration policy for MyVault across all MySwiftAgent services. MyVault is the centralized secrets management service that provides:

- 🔒 **Encrypted Storage**: AES-256-GCM encryption for all secrets
- 🛂 **Role-Based Access Control (RBAC)**: Fine-grained permissions per service
- 📡 **HTTP API**: RESTful interface for CRUD operations
- 🧾 **Audit Trail**: Version history and modification tracking
- 🔑 **Token-Based Authentication**: Service identity verification

---

## 🏗️ Architecture

### Service Communication Pattern

```
┌──────────────────┐
│  Consumer Service │
│  (ExpertAgent,   │
│   CommonUI, etc.)│
└─────────┬────────┘
          │ HTTP Request
          │ Headers:
          │ - X-Service: <service-name>
          │ - X-Token: <service-token>
          ▼
┌──────────────────┐
│    MyVault API   │
│   (Port 8000)    │
└─────────┬────────┘
          │
          ▼
┌──────────────────┐
│ Encrypted SQLite │
│  (data/myvault.db)│
└──────────────────┘
```

### Key Components

| Component | Description | Location |
|-----------|-------------|----------|
| **MyVault Service** | FastAPI-based secrets management API | `myVault/` |
| **Config File** | Non-sensitive configuration (policies, services) | `myVault/config.yaml` |
| **Environment File** | Sensitive credentials (master key, tokens) | `myVault/.env` |
| **Database** | Encrypted SQLite database | `myVault/data/myvault.db` |
| **Client Libraries** | Service-specific integration code | `<service>/core/myvault_client.py` |

---

## 🔑 Required Parameters

### Environment Variables (All Consumer Services)

Every service integrating with MyVault MUST define these environment variables:

| Variable Name | Type | Required | Description | Example |
|---------------|------|----------|-------------|---------|
| `MYVAULT_BASE_URL` | String | ✅ Yes | MyVault API endpoint URL | `http://localhost:8000` (dev)<br>`http://myvault:8000` (docker) |
| `MYVAULT_SERVICE_NAME` | String | ✅ Yes | Service identifier for authentication | `expertagent`, `commonui`, `graphaiserver` |
| `MYVAULT_SERVICE_TOKEN` | String | ✅ Yes | Authentication token for service | Generated securely (see below) |
| `MYVAULT_ENABLED` | Boolean | ⚠️ Optional | Enable/disable MyVault integration | `true` (default: `false`) |
| `MYVAULT_DEFAULT_PROJECT` | String | ⚠️ Optional | Default project name for secrets | `myproject`, `default` |
| `SECRETS_CACHE_TTL` | Integer | ⚠️ Optional | Cache TTL in seconds | `300` (5 minutes) |

### MyVault Server Configuration

MyVault server requires these environment variables:

| Variable Name | Type | Required | Description | Example |
|---------------|------|----------|-------------|---------|
| `MSA_MASTER_KEY` | String | ✅ Yes | Base64-encoded 32-byte encryption key | `base64:jFi1bkzTyKQ5BLtw...` |
| `MYVAULT_TOKEN_<SERVICE>` | String | ✅ Yes | Token for each service (e.g., `MYVAULT_TOKEN_EXPERTAGENT`) | Generated securely |

---

## 🛡️ Authentication & Authorization

### Authentication Flow

1. **Consumer Service** sends HTTP request with headers:
   ```
   X-Service: expertagent
   X-Token: <service-token>
   ```

2. **MyVault** validates:
   - Service name exists in `config.yaml` (services section)
   - Token matches environment variable `MYVAULT_TOKEN_<SERVICE>`
   - Service is enabled (`enabled: true`)

3. **Authorization Check**:
   - Load service's assigned roles from `config.yaml`
   - Evaluate permissions against requested resource
   - Allow/deny based on RBAC policy

### RBAC Actions

| Action | Description | Use Case |
|--------|-------------|----------|
| `read` | Retrieve secret values | Applications reading credentials |
| `write` | Create or update secrets | Admin services managing configurations |
| `delete` | Remove secrets | Secret rotation and cleanup |
| `list` | Enumerate secrets (values redacted) | Discovery and inventory |

### Example RBAC Policy

```yaml
# config.yaml
policies:
  - name: expertagent-reader
    description: "Read-only access to all secrets for AI agent"
    permissions:
      - effect: "allow"
        actions: ["read", "list"]
        resources: ["secret:*:*"]

  - name: expertagent-google-editor
    description: "Write access to Google OAuth secrets"
    permissions:
      - effect: "allow"
        actions: ["read", "write", "list"]
        resources: ["secret:*:GOOGLE_*"]

services:
  - name: expertagent
    description: "ExpertAgent AI service"
    enabled: true
    roles:
      - expertagent-reader
      - expertagent-google-editor
```

---

## 🔧 Integration Implementation

### Step 1: Generate Service Token

```bash
# Generate secure token for new service
python -c "import secrets; print(secrets.token_urlsafe(32))"
# Output: AbC123XyZ456...
```

### Step 2: Configure MyVault Server

Add service definition to `myVault/config.yaml`:

```yaml
services:
  - name: mynewservice
    description: "My new service with MyVault integration"
    enabled: true
    roles:
      - common-reader  # Reuse existing policy or create new one
```

Add token to `myVault/.env`:

```env
MYVAULT_TOKEN_MYNEWSERVICE=AbC123XyZ456...
```

### Step 3: Configure Consumer Service

Add environment variables to service configuration:

**Docker Compose (`docker-compose.yml`):**
```yaml
services:
  mynewservice:
    environment:
      - MYVAULT_BASE_URL=http://myvault:8000
      - MYVAULT_SERVICE_NAME=mynewservice
      - MYVAULT_SERVICE_TOKEN=${MYVAULT_TOKEN_MYNEWSERVICE}
```

**Local Development (`.env` or `dev-start.sh`):**
```env
MYVAULT_BASE_URL=http://localhost:8003  # or 8103 for quick-start.sh
MYVAULT_SERVICE_NAME=mynewservice
MYVAULT_SERVICE_TOKEN=AbC123XyZ456...
```

### Step 4: Implement Client Code

#### Python Example (FastAPI/Pydantic)

```python
# core/config.py
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    # MyVault Configuration
    MYVAULT_ENABLED: bool = Field(default=False)
    MYVAULT_BASE_URL: str = Field(default="http://localhost:8000")
    MYVAULT_SERVICE_NAME: str = Field(default="mynewservice")
    MYVAULT_SERVICE_TOKEN: str = Field(default="")
    MYVAULT_DEFAULT_PROJECT: str = Field(default="")
    SECRETS_CACHE_TTL: int = Field(default=300)

settings = Settings()
```

```python
# core/myvault_client.py
import httpx
from typing import Optional

class MyVaultClient:
    def __init__(self, base_url: str, service_name: str, service_token: str):
        self.base_url = base_url.rstrip("/")
        self.service_name = service_name
        self.service_token = service_token
        self.client = httpx.Client(
            base_url=self.base_url,
            headers={
                "X-Service": self.service_name,
                "X-Token": self.service_token,
            },
            timeout=30.0,
        )

    def get_secret(self, project: str, path: str) -> str:
        """Retrieve a secret value."""
        response = self.client.get(f"/api/secrets/{project}/{path}")
        response.raise_for_status()
        return str(response.json()["value"])

    def set_secret(self, project: str, path: str, value: str) -> None:
        """Create or update a secret."""
        response = self.client.post(
            "/api/secrets",
            json={"project": project, "path": path, "value": value},
        )
        response.raise_for_status()
```

```python
# core/secrets.py (Unified secrets manager)
from typing import Optional
import os
import time
from core.config import settings
from core.myvault_client import MyVaultClient

class SecretsManager:
    def __init__(self):
        self.myvault_client: Optional[MyVaultClient] = None
        self._cache: dict[str, tuple[str, float]] = {}
        self.cache_ttl = settings.SECRETS_CACHE_TTL

        if settings.MYVAULT_ENABLED:
            self.myvault_client = MyVaultClient(
                base_url=settings.MYVAULT_BASE_URL,
                service_name=settings.MYVAULT_SERVICE_NAME,
                service_token=settings.MYVAULT_SERVICE_TOKEN,
            )

    def get_secret(self, key: str, project: Optional[str] = None) -> str:
        """
        Get secret with MyVault priority, fallback to environment variables.

        Args:
            key: Secret key (e.g., "OPENAI_API_KEY")
            project: MyVault project name (optional)

        Returns:
            Secret value
        """
        # Check cache first
        cache_key = f"{project or 'default'}:{key}"
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key][0]

        # Try MyVault
        if self.myvault_client:
            try:
                proj = project or settings.MYVAULT_DEFAULT_PROJECT or "default"
                value = self.myvault_client.get_secret(proj, key)
                self._cache[cache_key] = (value, time.time())
                return value
            except Exception as e:
                # Log warning and fallback
                print(f"MyVault lookup failed for {key}: {e}, falling back to env")

        # Fallback to environment variable
        value = os.getenv(key, "")
        if not value:
            raise ValueError(f"Secret '{key}' not found in MyVault or environment")

        self._cache[cache_key] = (value, time.time())
        return value

    def _is_cache_valid(self, key: str) -> bool:
        """Check if cached value is within TTL."""
        if key not in self._cache:
            return False
        _, timestamp = self._cache[key]
        return (time.time() - timestamp) < self.cache_ttl

# Global instance
secrets_manager = SecretsManager()
```

#### TypeScript Example (Express/Node.js)

```typescript
// src/config/settings.ts
export interface MyVaultConfig {
  MYVAULT_BASE_URL: string;
  MYVAULT_SERVICE_NAME: string;
  MYVAULT_SERVICE_TOKEN: string;
}

export const settings: MyVaultConfig = {
  MYVAULT_BASE_URL: process.env.MYVAULT_BASE_URL || 'http://localhost:8000',
  MYVAULT_SERVICE_NAME: process.env.MYVAULT_SERVICE_NAME || 'mynewservice',
  MYVAULT_SERVICE_TOKEN: process.env.MYVAULT_SERVICE_TOKEN || '',
};
```

```typescript
// src/services/myvaultClient.ts
import axios, { AxiosInstance } from 'axios';

export class MyVaultClient {
  private client: AxiosInstance;

  constructor(baseUrl: string, serviceName: string, serviceToken: string) {
    this.client = axios.create({
      baseURL: baseUrl,
      headers: {
        'X-Service': serviceName,
        'X-Token': serviceToken,
      },
      timeout: 30000,
    });
  }

  async getSecret(project: string, path: string): Promise<string> {
    const response = await this.client.get(`/api/secrets/${project}/${path}`);
    return response.data.value;
  }

  async setSecret(project: string, path: string, value: string): Promise<void> {
    await this.client.post('/api/secrets', { project, path, value });
  }
}
```

---

## 📡 API Endpoints

### Authentication Headers (All Requests)

```http
X-Service: <service-name>
X-Token: <service-token>
```

### Available Endpoints

| Method | Path | Description | Request Body | Response |
|--------|------|-------------|--------------|----------|
| **GET** | `/health` | Health check | - | `{"status":"healthy","service":"myVault"}` |
| **POST** | `/api/secrets/test` | Test authentication | - | `{"status":"ok","message":"..."}` |
| **GET** | `/api/projects` | List all projects | - | `[{"id":1,"name":"myproject",...}]` |
| **POST** | `/api/projects` | Create project | `{"name":"myproject","description":"..."}` | `{"id":1,"name":"myproject",...}` |
| **GET** | `/api/secrets` | List secrets (values redacted) | - | `[{"id":1,"project":"test","path":"api-key",...}]` |
| **GET** | `/api/secrets/{project}/{path}` | Get secret value | - | `{"id":1,"project":"test","path":"api-key","value":"secret123",...}` |
| **POST** | `/api/secrets` | Create secret | `{"project":"test","path":"api-key","value":"secret123"}` | `{"id":1,"project":"test",...}` |
| **PATCH** | `/api/secrets/{project}/{path}` | Update secret (rotation) | `{"value":"new-secret456"}` | `{"id":1,"version":2,...}` |
| **DELETE** | `/api/secrets/{project}/{path}` | Delete secret | - | HTTP 204 No Content |

### Example API Calls

**Create Secret:**
```bash
curl -X POST http://localhost:8000/api/secrets \
  -H "Content-Type: application/json" \
  -H "X-Service: expertagent" \
  -H "X-Token: <service-token>" \
  -d '{
    "project": "myproject",
    "path": "OPENAI_API_KEY",
    "value": "sk-openai-secret-key-123"
  }'
```

**Retrieve Secret:**
```bash
curl http://localhost:8000/api/secrets/myproject/OPENAI_API_KEY \
  -H "X-Service: expertagent" \
  -H "X-Token: <service-token>"
```

**Update Secret (Rotation):**
```bash
curl -X PATCH http://localhost:8000/api/secrets/myproject/OPENAI_API_KEY \
  -H "Content-Type: application/json" \
  -H "X-Service: expertagent" \
  -H "X-Token: <service-token>" \
  -d '{
    "value": "sk-openai-rotated-key-456"
  }'
```

---

## 🌐 Port Configuration

### Standard Ports (Docker Compose / dev-start.sh)

| Environment | MyVault Port | Usage |
|-------------|--------------|-------|
| **Docker Compose** | `8003` | Internal container network: `http://myvault:8000`<br>External host: `http://localhost:8003` |
| **dev-start.sh** | `8003` | Local development: `http://localhost:8003` |

### Alternative Ports (quick-start.sh)

| Environment | MyVault Port | Usage |
|-------------|--------------|-------|
| **quick-start.sh** | `8103` | Local development (parallel): `http://localhost:8103` |

### Service-Specific Configuration

| Service | Docker Compose | dev-start.sh | quick-start.sh |
|---------|----------------|--------------|----------------|
| **ExpertAgent** | `MYVAULT_BASE_URL=http://myvault:8000` | `MYVAULT_BASE_URL=http://localhost:8003` | `MYVAULT_BASE_URL=http://localhost:8103` |
| **CommonUI** | `MYVAULT_BASE_URL=http://myvault:8000` | `MYVAULT_BASE_URL=http://localhost:8003` | `MYVAULT_BASE_URL=http://localhost:8103` |
| **GraphAiServer** | `MYVAULT_BASE_URL=http://myvault:8000` | `MYVAULT_BASE_URL=http://localhost:8003` | `MYVAULT_BASE_URL=http://localhost:8103` |

---

## 🔒 Security Best Practices

### 1. Token Management

- ✅ **Generate Cryptographically Secure Tokens**:
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(32))"
  ```

- ✅ **Never Commit Tokens to Git**:
  - Store in `.env` files (gitignored)
  - Use environment variable injection in CI/CD

- ✅ **Rotate Tokens Regularly**:
  - Recommended: Every 90 days
  - Update both MyVault `.env` and consumer service `.env`

### 2. Master Key Management

- ✅ **Generate Strong Master Key**:
  ```bash
  python -c "import secrets, base64; print('base64:' + base64.b64encode(secrets.token_bytes(32)).decode())"
  ```

- ❌ **Never Share Master Key Between Environments**:
  - Development, staging, and production MUST use different keys

- ✅ **Backup Master Key Securely**:
  - Use password managers or hardware security modules (HSM)
  - Encrypt backups with separate encryption key

### 3. Access Control

- ✅ **Principle of Least Privilege**:
  - Grant only the minimum required permissions
  - Use specific resource patterns instead of wildcards where possible

- ✅ **Separate Policies by Environment**:
  - Development services should NOT access production secrets
  - Use project namespacing (e.g., `myproject:dev/*`, `myproject:prod/*`)

### 4. Network Security

- ✅ **Use HTTPS in Production**:
  - Configure reverse proxy (nginx, Traefik) with TLS
  - Enforce `https://` scheme in `MYVAULT_BASE_URL`

- ✅ **Restrict Network Access**:
  - Docker networks should isolate services
  - Firewall rules should block external access to MyVault port

### 5. Audit & Monitoring

- ✅ **Enable Audit Logging**:
  ```yaml
  # config.yaml
  audit:
    enabled: true
    log_access: true
    log_modifications: true
    retention_days: 90
  ```

- ✅ **Monitor for Anomalies**:
  - Failed authentication attempts
  - Unusual access patterns
  - Secrets accessed by unauthorized services

---

## 🧪 Testing & Validation

### Health Check

```bash
curl http://localhost:8000/health
# Expected: {"status":"healthy","service":"myVault"}
```

### Authentication Test

```bash
curl -X POST http://localhost:8000/api/secrets/test \
  -H "X-Service: expertagent" \
  -H "X-Token: <service-token>"
# Expected: {"status":"ok","message":"Authentication successful for service 'expertagent'"}
```

### Integration Test (Python)

```python
import pytest
from core.secrets import secrets_manager

def test_myvault_integration():
    # Test secret retrieval
    api_key = secrets_manager.get_secret("OPENAI_API_KEY", project="test")
    assert api_key is not None
    assert len(api_key) > 0

    # Test caching (second call should be faster)
    import time
    start = time.time()
    api_key_cached = secrets_manager.get_secret("OPENAI_API_KEY", project="test")
    elapsed = time.time() - start

    assert api_key == api_key_cached
    assert elapsed < 0.01  # Cached retrieval should be < 10ms
```

---

## 📚 Common Integration Patterns

### Pattern 1: Direct Retrieval (Simple)

```python
# Use for: One-time secret lookup during initialization
from core.myvault_client import MyVaultClient

client = MyVaultClient(
    base_url=settings.MYVAULT_BASE_URL,
    service_name=settings.MYVAULT_SERVICE_NAME,
    service_token=settings.MYVAULT_SERVICE_TOKEN,
)
api_key = client.get_secret("myproject", "OPENAI_API_KEY")
```

### Pattern 2: Unified Secrets Manager (Recommended)

```python
# Use for: Fallback to environment variables, caching support
from core.secrets import secrets_manager

api_key = secrets_manager.get_secret("OPENAI_API_KEY", project="myproject")
# Automatically tries MyVault first, falls back to os.getenv()
```

### Pattern 3: Lazy Loading with Settings

```python
# Use for: Pydantic settings with MyVault integration
from pydantic_settings import BaseSettings
from pydantic import Field
from core.secrets import secrets_manager

class Settings(BaseSettings):
    OPENAI_API_KEY: str = Field(default="")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Override with MyVault if available
        if not self.OPENAI_API_KEY:
            try:
                self.OPENAI_API_KEY = secrets_manager.get_secret("OPENAI_API_KEY")
            except ValueError:
                pass  # Use default from environment

settings = Settings()
```

---

## 🔄 Secret Rotation Workflow

### Manual Rotation

```bash
# 1. Generate new secret (e.g., new API key from external service)
NEW_API_KEY="sk-new-openai-key-789"

# 2. Update in MyVault
curl -X PATCH http://localhost:8000/api/secrets/myproject/OPENAI_API_KEY \
  -H "Content-Type: application/json" \
  -H "X-Service: commonui" \
  -H "X-Token: <admin-token>" \
  -d "{\"value\":\"$NEW_API_KEY\"}"

# 3. Restart dependent services (or wait for cache TTL expiration)
docker-compose restart expertagent
```

### Automated Rotation (Python Example)

```python
import schedule
import time
from core.myvault_client import MyVaultClient
from external_api import generate_new_api_key

def rotate_api_key():
    """Rotate API key every 90 days."""
    client = MyVaultClient(...)

    # 1. Generate new key from external service
    new_key = generate_new_api_key()

    # 2. Update in MyVault
    client.update_secret("myproject", "OPENAI_API_KEY", new_key)

    # 3. Notify monitoring
    print(f"✅ API key rotated at {time.ctime()}")

# Schedule rotation every 90 days
schedule.every(90).days.do(rotate_api_key)

while True:
    schedule.run_pending()
    time.sleep(86400)  # Check daily
```

---

## 🚨 Troubleshooting

### Error: "[Errno 61] Connection refused"

**Cause**: MyVault service is not running or wrong port configured.

**Solution**:
```bash
# 1. Check MyVault is running
curl http://localhost:8003/health  # dev-start.sh
curl http://localhost:8103/health  # quick-start.sh

# 2. Check environment variable
echo $MYVAULT_BASE_URL

# 3. Restart MyVault
docker-compose restart myvault  # Docker
./scripts/restart-myvault.sh    # dev-start.sh
```

### Error: "403 Forbidden - Service does not have access"

**Cause**: Service lacks RBAC permissions for requested resource.

**Solution**:
```bash
# 1. Check service roles in config.yaml
cat myVault/config.yaml | grep -A 5 "name: expertagent"

# 2. Add required policy
# Edit myVault/config.yaml and add/modify roles

# 3. Restart MyVault to reload config
./scripts/restart-myvault.sh
```

### Error: "401 Unauthorized - Invalid service token"

**Cause**: Token mismatch between consumer and MyVault.

**Solution**:
```bash
# 1. Verify token in consumer service
cat expertAgent/.env | grep MYVAULT_SERVICE_TOKEN

# 2. Verify token in MyVault server
cat myVault/.env | grep MYVAULT_TOKEN_EXPERTAGENT

# 3. Ensure tokens match (update if necessary)
# 4. Restart both services
```

---

## 📖 Related Documentation

- **MyVault README**: [`myVault/README.md`](../../myVault/README.md)
- **Architecture Overview**: [`docs/design/architecture-overview.md`](./architecture-overview.md)
- **Environment Variables**: [`docs/design/environment-variables.md`](./environment-variables.md)
- **Docker Guide**: [`docs/guide/DOCKER_GUIDE.md`](../guide/DOCKER_GUIDE.md)
- **Development Guide**: [`docs/guide/DEVELOPMENT_GUIDE.md`](../guide/DEVELOPMENT_GUIDE.md)

---

## ✅ Compliance Checklist

Before deploying a new service with MyVault integration:

- [ ] Service name added to `myVault/config.yaml` (services section)
- [ ] RBAC policy defined with appropriate permissions
- [ ] Service token generated securely and added to `myVault/.env`
- [ ] Consumer service configured with required environment variables
- [ ] Client code implemented (MyVaultClient or SecretsManager)
- [ ] Unit tests written for MyVault integration
- [ ] Integration tests verified in local development
- [ ] Health check endpoint tested (`/health`)
- [ ] Authentication tested (`/api/secrets/test`)
- [ ] Secret retrieval tested for all required secrets
- [ ] Error handling implemented for MyVault unavailability
- [ ] Fallback to environment variables verified
- [ ] Cache TTL configured appropriately
- [ ] Documentation updated (README, .env.example)
- [ ] Security review completed (token management, permissions)
- [ ] Deployment tested in Docker Compose environment

---

**Maintained by**: MySwiftAgent Core Team
**Questions**: Open an issue in the main repository

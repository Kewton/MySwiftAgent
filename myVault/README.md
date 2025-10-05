# myVault

> Secure secrets management for the **MySwiftAgent** ecosystem. Currently in pre-alpha and evolving toward a production-ready vault service.

---

## 🧭 Project Status

- **Stage:** Pre-alpha (design and groundwork in progress)
- **Goal:** Deliver a lightweight, local-first secrets manager that can be upgraded to enterprise-grade tooling without breaking changes
- **Focus areas:** API design, security model, configuration ergonomics, and integration with other MySwiftAgent services

---

## 🔍 Vision & Scope

myVault will offer a safe and auditable way to store, rotate, and distribute sensitive configuration across the MySwiftAgent stack.

Planned highlights:

- 🔒 **Local-first security** powered by SQLite and AES-256-GCM
- 🛂 **Fine-grained access rules** driven by declarative `.env` configuration
- 📡 **HTTP API** for cross-service reads and writes
- 🧾 **Audit trail** that records `updated_by`, version history, and timestamps
- 🧰 **CommonUI bridge** for a friendly management console
- 🚀 **Future-proofing** via optional HashiCorp Vault integration

---

## 🏗️ Architecture at a Glance

| Layer | Responsibilities |
| --- | --- |
| API Layer | FastAPI-based endpoints for CRUD, discovery, and health checks |
| Access Control | Validates `X-Service` / `X-Token` headers against `.env`-defined policies |
| Storage | Local encrypted store (AES-256-GCM + SQLite) with provider abstraction for remote backends |
| Observability | Structured logs, audit trail metadata, and integration hooks for CommonUI |

The implementation is designed so that switching from the bundled local provider to HashiCorp Vault (via `hvac`) can happen transparently when required.

---

## ⚙️ Getting Ready

### Prerequisites

- Python **3.12** or newer
- [`uv`](https://docs.astral.sh/uv/) package and environment manager
- Optional: Docker (for container experiments once the image definition lands)

### Bootstrapping the Environment

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync dependencies for myVault
cd myVault
uv sync
```

> ℹ️ The executable modules are still under active development. Startup recipes (e.g. `uv run ...`) will be published once the service entrypoint is finalized.

---

## 🧩 Configuration

myVault uses a **structured configuration approach** that separates sensitive credentials from non-sensitive policies:

- **`config.yaml`**: Non-sensitive configuration (service definitions, access policies, audit settings)
- **`.env`**: Sensitive credentials only (master key, service tokens)

### Configuration Structure

**config.yaml** (committed to repository):

```yaml
# Application configuration
application:
  title: "myVault"
  version: "0.1.0"
  port: 8000

# RBAC Policies - Define reusable access control roles
policies:
  - name: my-project-editor
    description: "Full read/write access to myproject production"
    permissions:
      - effect: "allow"
        actions: ["read", "write", "list"]
        resources: ["secret:myproject*:prod/*"]

  - name: my-project-worker-reader
    description: "Read-only access to worker secrets"
    permissions:
      - effect: "allow"
        actions: ["read"]
        resources: ["secret:myproject:prod/worker/*"]

# Service definitions - Assign roles to services
services:
  - name: my-api-service
    description: "API service with full access"
    enabled: true
    roles:
      - my-project-editor

  - name: my-worker-service
    description: "Worker service with read-only access"
    enabled: true
    roles:
      - my-project-worker-reader

# Audit configuration
audit:
  enabled: true
  log_access: true
  retention_days: 90
```

**.env** (NOT committed, contains secrets):

```env
# Master encryption key (Base64-encoded 32 bytes)
MSA_MASTER_KEY=base64:jFi1bkzTyKQ5BLtw2dBDo1RItDXlKo8A5z2JbC6TExE=

# Service authentication tokens
TOKEN_my-api-service=secure-token-here
TOKEN_my-worker-service=another-secure-token
```

### Key Design Notes

- **Service identity** is asserted through `X-Service` and `X-Token` headers
- **RBAC (Role-Based Access Control)**:
  - Policies define permissions with **actions** (read/write/delete/list), **resources** (secret paths), and **effect** (allow/deny)
  - Services are assigned **roles** (policies) that grant specific permissions
  - Supports wildcard patterns for flexible resource matching (e.g., `secret:myproject*:prod/*`)
  - Enforces **principle of least privilege** with action-level control
- **Tokens and master key** are loaded from environment variables (`.env` file or container secrets)
- **Separation of concerns**: Configuration policies are version-controlled, secrets are not

### RBAC Actions

| Action | Description | Example Use Case |
|--------|-------------|------------------|
| `read` | Retrieve secret values | Workers reading database credentials |
| `write` | Create or update secrets | API services managing configurations |
| `delete` | Remove secrets | Admin services cleaning up old secrets |
| `list` | Enumerate secrets (values redacted) | Discovery and inventory operations |

### Generating Secure Credentials

Generate a master key:

```bash
python -c "import secrets, base64; print('base64:' + base64.b64encode(secrets.token_bytes(32)).decode())"
```

Generate service tokens:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## 🌐 API Blueprint (Draft)

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Service heartbeat |
| GET | `/api/projects` | List registered projects |
| POST | `/api/projects` | Register a new project scope |
| GET | `/api/secrets` | Enumerate secrets for a project/prefix (values redacted) |
| GET | `/api/secrets/{project}/{scope}/{env}/{name}` | Retrieve a secret value |
| POST | `/api/secrets` | Create a secret |
| PATCH | `/api/secrets/{project}/{scope}/{env}/{name}` | Rotate/update a secret |
| DELETE | `/api/secrets/{project}/{scope}/{env}/{name}` | Remove a secret |
| POST | `/api/secrets/test` | Validate connectivity or credentials |

All requests must include:

```
X-Service: <service-name>
X-Token: <shared-token>
```

---

## 🔐 Security Model

- **Transport:** HTTPS is recommended for all deployments; in internal environments, use service mesh or reverse proxies to enforce TLS.
- **Encryption at Rest:** AES-256-GCM (with 12-byte IV and 16-byte auth tag) protects stored payloads.
- **Audit Columns:** Each record tracks `version`, `updated_at`, and `updated_by` for traceability.
- **Uniqueness:** `project` + `path` is unique, preventing collisions while enabling scoped namespaces.

---

## 🗺️ Roadmap

| Milestone | Description |
| --- | --- |
| ✅ Foundations | Define configuration schema, security guarantees, and provider abstraction |
| 🔜 API Surface | Solidify request/response contracts and scaffolding for CRUD endpoints |
| 🔜 Local Provider | Implement encrypted SQLite backend with auditing |
| 🔜 CommonUI Bridge | Deliver UX flows for browsing and editing secrets |
| 🚀 Enterprise Mode | Add HashiCorp Vault provider, capability tokens, and mTLS |

---

## 🧪 Quick Start & Testing

### Step 1: Generate Master Key

```bash
# Generate a cryptographically secure 32-byte key
python -c "import secrets, base64; print('base64:' + base64.b64encode(secrets.token_bytes(32)).decode())"
```

Copy the output (e.g., `base64:jFi1bkzTyKQ5BLtw2dBDo1RItDXlKo8A5z2JbC6TExE=`) for the next step.

### Step 2: Configure Environment

```bash
# Copy example configuration files
cp config.yaml.example config.yaml
cp .env.example .env

# Edit config.yaml to define your services and access policies
# Edit .env with your master key and service tokens
# MSA_MASTER_KEY=base64:YOUR_GENERATED_KEY_HERE
# TOKEN_my-api-service=YOUR_SECURE_TOKEN_HERE
```

**config.yaml** contains non-sensitive configuration (service definitions, access policies).
**.env** contains only sensitive credentials (master key, service tokens).

### Step 3: Install Dependencies

```bash
# Sync project dependencies
uv sync
```

### Step 4: Start the Service

```bash
# Run development server
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The service will be available at `http://localhost:8000`

---

## 📚 Tutorial: Building a Secure Configuration System

This tutorial walks you through building a complete secure configuration system for a multi-service application using myVault.

### Scenario: News Bot Application

You're building a news aggregation bot that consists of three services:
- **newsbot-api** - Main API service
- **newsbot-worker** - Background job processor
- **newsbot-scheduler** - Job scheduling service

Each service needs access to different secrets with proper isolation.

---

### Tutorial Step 1: Environment Setup

First, set up your development environment with proper credentials:

```bash
# Navigate to myVault directory
cd myVault

# Generate a secure master key
python -c "import secrets, base64; print('base64:' + base64.b64encode(secrets.token_bytes(32)).decode())"
# Output: base64:jFi1bkzTyKQ5BLtw2dBDo1RItDXlKo8A5z2JbC6TExE=

# Create .env from example
cp .env.example .env
```

Edit `.env` with the following configuration:

```env
##############################################
# MyVault Configuration for News Bot
##############################################

# Allowed services
ALLOWED_SERVICES=newsbot-api,newsbot-worker,newsbot-scheduler

# Service tokens (keep these secret!)
TOKEN_newsbot-api=api-secure-token-a1b2c3d4
TOKEN_newsbot-worker=worker-secure-token-e5f6g7h8
TOKEN_newsbot-scheduler=scheduler-secure-token-i9j0k1l2

# Access control rules
# newsbot-api: Full access to newsbot production + common secrets
ALLOW_newsbot-api=newsbot:prod/,common:

# newsbot-worker: Production data processing secrets only
ALLOW_newsbot-worker=newsbot:prod/worker/,newsbot:prod/database/

# newsbot-scheduler: Only scheduling-related secrets
ALLOW_newsbot-scheduler=newsbot:prod/scheduler/,common:

# Master encryption key (generated above)
MSA_MASTER_KEY=base64:jFi1bkzTyKQ5BLtw2dBDo1RItDXlKo8A5z2JbC6TExE=
```

**Key Design Principles:**
- Each service has its own unique token
- Access is scoped by prefix patterns
- Common secrets are shared across services
- Worker has limited access to only its required secrets

---

### Tutorial Step 2: Start the Vault Service

```bash
# Install dependencies
uv sync

# Start myVault in development mode
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

In another terminal, verify the service is running:

```bash
curl http://localhost:8000/health
# {"status":"healthy","service":"myVault"}
```

---

### Tutorial Step 3: Initialize Project Structure

Create the newsbot project in myVault:

```bash
curl -X POST http://localhost:8000/api/projects \
  -H "Content-Type: application/json" \
  -H "X-Service: newsbot-api" \
  -H "X-Token: api-secure-token-a1b2c3d4" \
  -d '{
    "name": "newsbot",
    "description": "News aggregation bot production secrets"
  }'
```

**Expected Response:**
```json
{
  "id": 1,
  "name": "newsbot",
  "description": "News aggregation bot production secrets",
  "created_at": "2025-10-06T12:00:00",
  "created_by": "newsbot-api"
}
```

---

### Tutorial Step 4: Store Service Secrets

Now, populate secrets for each service component:

#### 4a. API Service Secrets

```bash
# Twitter API credentials
curl -X POST http://localhost:8000/api/secrets \
  -H "Content-Type: application/json" \
  -H "X-Service: newsbot-api" \
  -H "X-Token: api-secure-token-a1b2c3d4" \
  -d '{
    "project": "newsbot",
    "path": "prod/twitter-api-key",
    "value": "twitter-key-abc123xyz"
  }'

# OpenAI API key
curl -X POST http://localhost:8000/api/secrets \
  -H "Content-Type: application/json" \
  -H "X-Service: newsbot-api" \
  -H "X-Token: api-secure-token-a1b2c3d4" \
  -d '{
    "project": "newsbot",
    "path": "prod/openai-api-key",
    "value": "sk-openai-secret-key-456"
  }'
```

#### 4b. Worker Service Secrets

```bash
# Database password
curl -X POST http://localhost:8000/api/secrets \
  -H "Content-Type: application/json" \
  -H "X-Service: newsbot-worker" \
  -H "X-Token: worker-secure-token-e5f6g7h8" \
  -d '{
    "project": "newsbot",
    "path": "prod/database/password",
    "value": "postgres-secure-password-789"
  }'

# Redis connection string
curl -X POST http://localhost:8000/api/secrets \
  -H "Content-Type: application/json" \
  -H "X-Service: newsbot-worker" \
  -H "X-Token: worker-secure-token-e5f6g7h8" \
  -d '{
    "project": "newsbot",
    "path": "prod/worker/redis-url",
    "value": "redis://user:pass@localhost:6379/0"
  }'
```

#### 4c. Scheduler Service Secrets

```bash
# Cron job webhook URL
curl -X POST http://localhost:8000/api/secrets \
  -H "Content-Type: application/json" \
  -H "X-Service: newsbot-scheduler" \
  -H "X-Token: scheduler-secure-token-i9j0k1l2" \
  -d '{
    "project": "newsbot",
    "path": "prod/scheduler/webhook-url",
    "value": "https://api.newsbot.com/jobs/trigger"
  }'
```

#### 4d. Common Secrets (shared across services)

```bash
# Shared encryption key
curl -X POST http://localhost:8000/api/secrets \
  -H "Content-Type: application/json" \
  -H "X-Service: newsbot-api" \
  -H "X-Token: api-secure-token-a1b2c3d4" \
  -d '{
    "project": "common",
    "path": "encryption-key",
    "value": "shared-aes-key-xyz789"
  }'
```

---

### Tutorial Step 5: Retrieve Secrets from Application Code

Here's how each service would retrieve its secrets at runtime:

#### Python Example (newsbot-api)

```python
import httpx
import os

class VaultClient:
    def __init__(self):
        self.base_url = os.getenv("VAULT_URL", "http://localhost:8000")
        self.service = os.getenv("SERVICE_NAME", "newsbot-api")
        self.token = os.getenv("VAULT_TOKEN", "api-secure-token-a1b2c3d4")

    def get_secret(self, project: str, path: str) -> str:
        """Retrieve a secret from myVault."""
        response = httpx.get(
            f"{self.base_url}/api/secrets/{project}/{path}",
            headers={
                "X-Service": self.service,
                "X-Token": self.token
            }
        )
        response.raise_for_status()
        return response.json()["value"]

# Usage in your application
vault = VaultClient()
twitter_key = vault.get_secret("newsbot", "prod/twitter-api-key")
openai_key = vault.get_secret("newsbot", "prod/openai-api-key")
shared_key = vault.get_secret("common", "encryption-key")
```

---

### Tutorial Step 6: Test Access Control

Verify that access control is working correctly:

#### ✅ Valid Access (should succeed)

```bash
# newsbot-api can access its own secrets
curl http://localhost:8000/api/secrets/newsbot/prod/twitter-api-key \
  -H "X-Service: newsbot-api" \
  -H "X-Token: api-secure-token-a1b2c3d4"
# Status: 200 OK
```

#### ❌ Invalid Access (should fail)

```bash
# newsbot-worker trying to access API secrets (not allowed)
curl http://localhost:8000/api/secrets/newsbot/prod/twitter-api-key \
  -H "X-Service: newsbot-worker" \
  -H "X-Token: worker-secure-token-e5f6g7h8"
# Status: 403 Forbidden
# {"detail":"Service 'newsbot-worker' does not have access to 'newsbot:prod/twitter-api-key'"}
```

---

### Tutorial Step 7: Secret Rotation

Regularly rotate credentials for security. Here's how to update the Twitter API key:

```bash
# Step 1: Update the secret with new value
curl -X PATCH http://localhost:8000/api/secrets/newsbot/prod/twitter-api-key \
  -H "Content-Type: application/json" \
  -H "X-Service: newsbot-api" \
  -H "X-Token: api-secure-token-a1b2c3d4" \
  -d '{
    "value": "twitter-key-NEW-rotated-abc789"
  }'

# Step 2: Verify version increment
curl http://localhost:8000/api/secrets/newsbot/prod/twitter-api-key \
  -H "X-Service: newsbot-api" \
  -H "X-Token: api-secure-token-a1b2c3d4"
# Response shows "version": 2, "updated_at": "2025-10-06T13:00:00"

# Step 3: Restart dependent services to pick up new credentials
# (Application code should cache secrets with TTL and refresh periodically)
```

**Best Practice: Automated Rotation**
```python
import schedule
import time

def rotate_twitter_key():
    # 1. Generate new key from Twitter API
    new_key = generate_new_twitter_key()

    # 2. Update in vault
    vault.update_secret("newsbot", "prod/twitter-api-key", new_key)

    # 3. Notify monitoring system
    send_notification("Twitter API key rotated successfully")

# Schedule rotation every 90 days
schedule.every(90).days.do(rotate_twitter_key)

while True:
    schedule.run_pending()
    time.sleep(3600)  # Check every hour
```

---

### Tutorial Step 8: Monitoring and Auditing

List all secrets to audit who updated what and when:

```bash
curl http://localhost:8000/api/secrets \
  -H "X-Service: newsbot-api" \
  -H "X-Token: api-secure-token-a1b2c3d4"
```

**Response (values are redacted for security):**
```json
[
  {
    "id": 1,
    "project": "newsbot",
    "path": "prod/twitter-api-key",
    "version": 2,
    "updated_at": "2025-10-06T13:00:00",
    "updated_by": "newsbot-api"
  },
  {
    "id": 2,
    "project": "newsbot",
    "path": "prod/openai-api-key",
    "version": 1,
    "updated_at": "2025-10-06T12:05:00",
    "updated_by": "newsbot-api"
  }
]
```

---

### Tutorial Step 9: Production Deployment Checklist

Before deploying to production:

- [ ] Generate a unique `MSA_MASTER_KEY` for production (never reuse dev keys)
- [ ] Use strong, randomly generated tokens for each service
- [ ] Restrict `ALLOW_*` prefixes to minimum required access
- [ ] Enable HTTPS/TLS for all vault communication
- [ ] Set up secret rotation schedules (90-day maximum)
- [ ] Configure database backups (encrypt `myvault.db` at rest)
- [ ] Implement secret caching with TTL in client applications
- [ ] Set up monitoring/alerting for failed authentication attempts
- [ ] Document which services have access to which prefixes
- [ ] Test disaster recovery (restore from backup)

---

### Tutorial Complete! 🎉

You now have a fully functional secrets management system with:
- ✅ Encrypted storage (AES-256-GCM)
- ✅ Fine-grained access control
- ✅ Audit trail (version history)
- ✅ Secret rotation capability
- ✅ Multi-service isolation

**Next Steps:**
- Integrate with your CI/CD pipeline
- Set up automated secret rotation
- Configure monitoring and alerting
- Plan migration to HashiCorp Vault (if needed for enterprise features)

---

## 📡 API Usage Examples

### Health Check

```bash
curl http://localhost:8000/health
# Response: {"status":"healthy","service":"myVault"}
```

### Test Connectivity (with authentication)

```bash
curl -X POST http://localhost:8000/api/secrets/test \
  -H "X-Service: testService" \
  -H "X-Token: test-secret-token-123"
# Response: {"status":"ok","message":"Authentication successful for service 'testService'"}
```

### Create a Project

```bash
curl -X POST http://localhost:8000/api/projects \
  -H "Content-Type: application/json" \
  -H "X-Service: testService" \
  -H "X-Token: test-secret-token-123" \
  -d '{
    "name": "newsbot",
    "description": "News aggregation bot secrets"
  }'
# Response: {"id":1,"name":"newsbot","description":"News aggregation bot secrets","created_at":"...","created_by":"testService"}
```

### Create a Secret

```bash
curl -X POST http://localhost:8000/api/secrets \
  -H "Content-Type: application/json" \
  -H "X-Service: testService" \
  -H "X-Token: test-secret-token-123" \
  -d '{
    "project": "test",
    "path": "prod/api-key",
    "value": "super-secret-api-key-12345"
  }'
# Response: {"id":1,"project":"test","path":"prod/api-key","value":"super-secret-api-key-12345","version":1,"updated_at":"...","updated_by":"testService"}
```

### Retrieve a Secret

```bash
curl http://localhost:8000/api/secrets/test/prod/api-key \
  -H "X-Service: testService" \
  -H "X-Token: test-secret-token-123"
# Response: {"id":1,"project":"test","path":"prod/api-key","value":"super-secret-api-key-12345","version":1,"updated_at":"...","updated_by":"testService"}
```

### List Secrets (values redacted)

```bash
curl http://localhost:8000/api/secrets \
  -H "X-Service: testService" \
  -H "X-Token: test-secret-token-123"
# Response: [{"id":1,"project":"test","path":"prod/api-key","version":1,"updated_at":"...","updated_by":"testService"}]
```

### Update a Secret (rotation)

```bash
curl -X PATCH http://localhost:8000/api/secrets/test/prod/api-key \
  -H "Content-Type: application/json" \
  -H "X-Service: testService" \
  -H "X-Token: test-secret-token-123" \
  -d '{
    "value": "new-rotated-api-key-67890"
  }'
# Response: {"id":1,"project":"test","path":"prod/api-key","value":"new-rotated-api-key-67890","version":2,"updated_at":"...","updated_by":"testService"}
```

### Delete a Secret

```bash
curl -X DELETE http://localhost:8000/api/secrets/test/prod/api-key \
  -H "X-Service: testService" \
  -H "X-Token: test-secret-token-123"
# Response: HTTP 204 No Content
```

---

## 🔬 Verification Workflow

Complete end-to-end test to verify all functionality:

```bash
# 1. Start the service
uv run uvicorn app.main:app --reload &
sleep 2

# 2. Health check
curl http://localhost:8000/health

# 3. Test authentication
curl -X POST http://localhost:8000/api/secrets/test \
  -H "X-Service: testService" \
  -H "X-Token: test-secret-token-123"

# 4. Create a project
curl -X POST http://localhost:8000/api/projects \
  -H "Content-Type: application/json" \
  -H "X-Service: testService" \
  -H "X-Token: test-secret-token-123" \
  -d '{"name": "demo", "description": "Demo project"}'

# 5. Create a secret
curl -X POST http://localhost:8000/api/secrets \
  -H "Content-Type: application/json" \
  -H "X-Service: testService" \
  -H "X-Token: test-secret-token-123" \
  -d '{"project": "test", "path": "demo/password", "value": "mySecretPass123"}'

# 6. Retrieve the secret
curl http://localhost:8000/api/secrets/test/demo/password \
  -H "X-Service: testService" \
  -H "X-Token: test-secret-token-123"

# 7. Update the secret
curl -X PATCH http://localhost:8000/api/secrets/test/demo/password \
  -H "Content-Type: application/json" \
  -H "X-Service: testService" \
  -H "X-Token: test-secret-token-123" \
  -d '{"value": "newSecretPass456"}'

# 8. Delete the secret
curl -X DELETE http://localhost:8000/api/secrets/test/demo/password \
  -H "X-Service: testService" \
  -H "X-Token: test-secret-token-123"

# 9. Stop the service
pkill -f "uvicorn app.main:app"
```

---

## 🤝 Collaboration

- Track issues and proposals in the main MySwiftAgent repository.
- When ready to contribute code, branch from the active feature branch, keep changes scoped, and document decisions in PR descriptions.
- Security reviews are mandatory before exposing the service beyond local development.

---

## 📄 License

myVault is part of the **MySwiftAgent** project and inherits its licensing terms.



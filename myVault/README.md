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

## 🧩 Configuration (.env)

myVault relies on environment variables to express who can talk to the service and what each caller may access.

```env
##############################################
# MyVault configuration (example)
##############################################

# Comma-separated list of client services allowed to connect
ALLOWED_SERVICES=myscheduler,jobqueue,graphAiServer,commonUI

# Shared tokens (sent via X-Service / X-Token headers)
TOKEN_myscheduler=msched-xxxx
TOKEN_jobqueue=jq-xxxx
TOKEN_graphAiServer=gas-xxxx
TOKEN_commonUI=ui-xxxx

# Allowed secret prefixes per service (supports wildcards)
ALLOW_myscheduler=project:newsbot/prod/,common/prod/
ALLOW_jobqueue=project:newsbot/prod/
ALLOW_graphAiServer=project:rag/dev/
ALLOW_commonUI=project:*/prod/,common/*/

# Master key for AES-256-GCM (Base64-encoded 32 bytes)
MSA_MASTER_KEY=base64:jFi1bkzTyKQ5BLtw2dBDo1RItDXlKo8A5z2JbC6TExE=
```

Key design notes:

- Service identity is asserted through the pair of headers `X-Service` and `X-Token`.
- Prefix rules (e.g. `project:*/prod/`) scope which secrets a caller may access.
- The master key should be generated with a cryptographically secure RNG. Example:

  ```bash
  python -c "import secrets, base64; print('base64:' + base64.b64encode(secrets.token_bytes(32)).decode())"
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
# Copy the example config
cp .env.example .env

# Edit .env with your master key and service credentials
# MSA_MASTER_KEY=base64:YOUR_GENERATED_KEY_HERE
# ALLOWED_SERVICES=testService,anotherService
# TOKEN_testService=test-secret-token-123
# ALLOW_testService=project:test/,common/
```

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



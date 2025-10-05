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

## 🤝 Collaboration

- Track issues and proposals in the main MySwiftAgent repository.
- When ready to contribute code, branch from the active feature branch, keep changes scoped, and document decisions in PR descriptions.
- Security reviews are mandatory before exposing the service beyond local development.

---

## 📄 License

myVault is part of the **MySwiftAgent** project and inherits its licensing terms.



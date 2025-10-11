# GraphAI Server API Documentation

## Overview

GraphAI Server provides REST API endpoints for executing GraphAI workflows defined in YAML configuration files.

## Base URL

```
http://localhost:8000
```

## Endpoints

### Health Check

**GET** `/health`

Returns the health status of the service.

**Response:**
```json
{
  "status": "healthy",
  "service": "graphAiServer"
}
```

---

### Root Endpoint

**GET** `/`

Returns a welcome message.

**Response:**
```json
{
  "message": "Welcome to Graph AI Server"
}
```

---

### API Version

**GET** `/api/v1/`

Returns API version information.

**Response:**
```json
{
  "version": "1.0",
  "service": "graphAiServer"
}
```

---

## GraphAI Agent Endpoints

### New Format (Recommended)

**POST** `/api/v1/myagent/:category/:model`

Executes a GraphAI workflow from `config/graphai/{category}/{model}.yml`.

**Path Parameters:**
- `category` (string, required): The category/subdirectory name (e.g., `default`, `expert`, `experimental`)
- `model` (string, required): The model/workflow name (without `.yml` extension)

**Request Body:**
```json
{
  "user_input": "Your input text",
  "project": "optional_project_name"
}
```

**Examples:**

1. **Default category:**
   ```bash
   curl -X POST http://localhost:8000/api/v1/myagent/default/test \
     -H "Content-Type: application/json" \
     -d '{"user_input": "Hello, world!"}'
   ```
   → Loads `config/graphai/default/test.yml`

2. **Expert category:**
   ```bash
   curl -X POST http://localhost:8000/api/v1/myagent/expert/ollama \
     -H "Content-Type: application/json" \
     -d '{"user_input": "Explain quantum computing"}'
   ```
   → Loads `config/graphai/expert/ollama.yml`

3. **Experimental category:**
   ```bash
   curl -X POST http://localhost:8000/api/v1/myagent/experimental/httpAgentFilter \
     -H "Content-Type: application/json" \
     -d '{"user_input": "Test HTTP filtering"}'
   ```
   → Loads `config/graphai/experimental/httpAgentFilter.yml`

**Success Response (200 OK):**
```json
{
  // GraphAI execution result
}
```

**Error Responses:**

- **400 Bad Request** - Invalid parameters:
  ```json
  {
    "error": "user_input is required"
  }
  ```

  ```json
  {
    "error": "Invalid category parameter"
  }
  ```

  ```json
  {
    "error": "Invalid model parameter"
  }
  ```

- **500 Internal Server Error** - Execution error:
  ```json
  {
    "error": "An error occurred while executing the GraphAI sample."
  }
  ```

---

### Legacy Format (Backward Compatibility)

**POST** `/api/v1/myagent`

Executes a GraphAI workflow using the old format.

**Request Body:**
```json
{
  "user_input": "Your input text",
  "model_name": "test",
  "project": "optional_project_name"
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/myagent \
  -H "Content-Type: application/json" \
  -d '{
    "user_input": "Hello, world!",
    "model_name": "test"
  }'
```

**Note:** This format is maintained for backward compatibility. New integrations should use the path parameter format.

---

## Directory Structure

GraphAI workflows are organized in subdirectories:

```
config/graphai/
├── default/           # Default/standard workflows
│   └── test.yml
├── expert/            # Expert/advanced workflows
│   ├── hello.yml
│   └── ollama.yml
└── experimental/      # Experimental workflows
    └── httpAgentFilter.yml
```

---

## Security

### Path Traversal Protection

All category and model parameters are validated to prevent path traversal attacks:

- ❌ Blocked characters: `..`, `/`, `\`
- ✅ Allowed characters: alphanumeric, `-`, `_`

**Invalid requests will return 400 Bad Request.**

---

## Admin Endpoints

### Admin Health Check

**GET** `/api/v1/admin/health`

Returns the health status of admin services.

**Response:**
```json
{
  "status": "healthy",
  "service": "graphaiserver-admin"
}
```

---

### Reload Secrets Cache

**POST** `/api/v1/admin/reload-secrets`

Clears the secrets cache for a specific project or all projects.

**Headers:**
- `X-Admin-Token` (string, required): Admin authentication token

**Request Body:**
```json
{
  "project": "project_name"  // Optional: omit to clear all caches
}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "message": "Cache cleared for project: project_name"
}
```

**Error Response (403 Forbidden):**
```json
{
  "error": "Invalid admin token"
}
```

---

## Environment Variables

Required environment variables:

```env
# Server Configuration
PORT=8000
NODE_ENV=development
MODEL_BASE_PATH=./config/graphai/

# MyVault Configuration
MYVAULT_ENABLED=true
MYVAULT_BASE_URL=http://localhost:8003
MYVAULT_SERVICE_NAME=graphaiserver-service
MYVAULT_SERVICE_TOKEN=your_token_here
MYVAULT_DEFAULT_PROJECT=default_project

# Admin API
ADMIN_TOKEN=your_admin_token_here
```

---

## Testing

Run integration tests:

```bash
npm test
```

Run specific test suite:

```bash
npm test -- app.test.ts
```

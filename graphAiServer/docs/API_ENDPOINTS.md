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
  "results": {
    "source": "User input text",
    "node1": { "output": "..." },
    "node2": { "output": "..." }
  },
  "errors": {},
  "logs": [
    {
      "nodeId": "node1",
      "state": "completed",
      "startTime": 1760175441540,
      "endTime": 1760175441553,
      "retryCount": 0
    },
    {
      "nodeId": "node2",
      "state": "completed",
      "startTime": 1760175441553,
      "endTime": 1760175441560,
      "retryCount": 0
    }
  ]
}
```

**Response Fields:**
- `results` (object): All node execution results (includes intermediate nodes)
- `errors` (object): Map of node IDs to error details (empty if no errors)
- `logs` (array): Execution logs for each node
  - `nodeId` (string): Node identifier
  - `state` (string): Node state (`injected`, `completed`, `failed`, `timed-out`, etc.)
  - `errorMessage` (string, optional): Error message if node failed
  - `startTime` (number, optional): Execution start timestamp (milliseconds)
  - `endTime` (number, optional): Execution end timestamp (milliseconds)
  - `retryCount` (number, optional): Number of retry attempts

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

- **500 Internal Server Error** - Execution error with detailed diagnostics:

  **Node-level errors (timeout, agent failure, etc.):**
  ```json
  {
    "results": {
      "source": "User input",
      "node1": { "output": "..." }
    },
    "errors": {
      "node2": {
        "message": "Timeout",
        "stack": "Error: Timeout\n    at ComputedNode.executeTimeout..."
      }
    },
    "logs": [
      {
        "nodeId": "node1",
        "state": "completed",
        "startTime": 1760175441540,
        "endTime": 1760175441553,
        "retryCount": 0
      },
      {
        "nodeId": "node2",
        "state": "timed-out",
        "errorMessage": "Timeout",
        "startTime": 1760175441560,
        "endTime": 1760175471560,
        "retryCount": 1
      }
    ]
  }
  ```

  **Initialization errors (YAML parsing, file not found, etc.):**
  ```json
  {
    "error": "An error occurred while executing the GraphAI sample.",
    "details": {
      "message": "Cannot find module './config/graphai/default/test.yml'",
      "type": "initialization_error",
      "timestamp": "2025-10-11T09:00:42.000Z"
    },
    "stack": "Error: Cannot find module...\n    at ..."
  }
  ```

  Note: `stack` field is only included when `NODE_ENV !== 'production'`

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

## Error Handling and Debugging

### Understanding Response Structure

All GraphAI execution responses include three main fields:

1. **`results`** - Contains execution results for all nodes (including intermediate nodes when `run(true)` is used)
2. **`errors`** - Map of node IDs to error details (empty object if no errors occurred)
3. **`logs`** - Array of execution logs showing the state and timing of each node

### Node States

The `state` field in logs can have the following values:

- `injected` - Node value was injected (e.g., source input)
- `waiting` - Node is waiting for dependencies
- `queued` - Node is queued for execution
- `executing` - Node is currently executing
- `completed` - Node execution completed successfully
- `failed` - Node execution failed with an error
- `timed-out` - Node execution exceeded timeout limit

### Debugging Timeouts

When a timeout occurs, you can identify:

1. **Which node timed out** - Check `logs` for nodes with `state: "timed-out"`
2. **Execution duration** - Calculate `endTime - startTime` to see how long it ran
3. **Retry attempts** - Check `retryCount` to see if retries were attempted
4. **Error details** - Check `errors` object for the specific error message and stack trace

**Example timeout scenario:**

```json
{
  "results": {
    "source": "User input",
    "llm": null
  },
  "errors": {
    "llm": {
      "message": "Timeout",
      "stack": "Error: Timeout\n    at ComputedNode.executeTimeout..."
    }
  },
  "logs": [
    {
      "nodeId": "source",
      "state": "injected",
      "endTime": 1760175441540
    },
    {
      "nodeId": "llm",
      "state": "timed-out",
      "errorMessage": "Timeout",
      "startTime": 1760175441540,
      "endTime": 1760175641540,
      "retryCount": 0
    }
  ]
}
```

In this example:
- The `llm` node timed out after 200 seconds (200000 milliseconds)
- No retries were attempted (`retryCount: 0`)
- The timeout error is captured in both `errors` and `logs`

### Debugging Node Failures

For non-timeout failures (agent errors, invalid inputs, etc.):

1. Check `errors` for detailed error messages and stack traces
2. Review `logs` to see which nodes completed successfully before the failure
3. Examine `results` to see partial outputs from completed nodes

### Development vs Production

- **Development mode** (`NODE_ENV !== 'production'`):
  - Full error stack traces included in responses
  - Detailed error messages for initialization errors

- **Production mode** (`NODE_ENV === 'production'`):
  - Stack traces omitted from responses
  - Generic error messages for security

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

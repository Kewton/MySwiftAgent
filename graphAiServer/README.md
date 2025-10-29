# Graph AI Server

🚀 Graph AI Server is a TypeScript/Node.js microservice for MySwiftAgent that provides graph-based AI functionality using GraphAI framework.

## Features

- ⚡ Fast and lightweight Express server
- 🧠 GraphAI framework integration for complex AI workflows
- 🔐 **MyVault integration** for centralized secret management with cache
- 🔒 Security-first with Helmet middleware
- 🌐 CORS-enabled for cross-origin requests
- 🧪 Comprehensive testing with Jest and Supertest (29 MyVault tests included)
- 🐳 Docker-ready with multi-stage build
- 📊 Health check endpoint for monitoring
- 📝 YAML-based workflow configuration

## Getting Started

### Prerequisites

- Node.js 20+
- npm

### Installation

```bash
# Install dependencies
npm ci

# Run in development mode
npm run dev

# Build for production
npm run build

# Start production server
npm start
```

### Running Tests

```bash
# Run all tests
npm test

# Run tests with coverage
npm test -- --coverage

# Run linting
npm run lint

# Run type checking
npm run type-check
```

### Docker

```bash
# Build Docker image
docker build -t graph-ai-server:latest .

# Run container
docker run -p 8000:8000 graph-ai-server:latest
```

## API Endpoints

### Health Check

```bash
GET /health
```

Returns service health status (used by CI/CD).

**Example:**
```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "graphAiServer"
}
```

### Root

```bash
GET /
```

Welcome message and basic service info.

**Example:**
```bash
curl http://localhost:8000/
```

### API v1 Root

```bash
GET /api/v1/
```

API version information.

**Example:**
```bash
curl http://localhost:8000/api/v1/
```

### GraphAI Test Endpoint

```bash
GET /api/v1/test
```

Executes a test GraphAI workflow (uses `test.yml`).

**Example:**
```bash
curl http://localhost:8000/api/v1/test
```

**Response:**
```json
{
  "results": {
    "source": "Input text",
    "node1": { "output": "..." }
  },
  "errors": {},
  "logs": [
    {
      "nodeId": "node1",
      "state": "completed",
      "startTime": 1760175441540,
      "endTime": 1760175441553,
      "retryCount": 0
    }
  ]
}
```

**Response includes:**
- `results`: All node execution results (including intermediate nodes)
- `errors`: Map of failed nodes with error details
- `logs`: Execution logs showing node states, timing, and retry information

### GraphAI Agent Endpoint

```bash
POST /api/v1/myagent
```

Executes a custom GraphAI workflow with user input.

**Request Body:**
```json
{
  "user_input": "Your input text here",
  "model_name": "podcast_map_test"
}
```

**Example:**
```bash
# Basic example
curl -X POST http://localhost:8104/api/v1/myagent \
  -H "Content-Type: application/json" \
  -d '{
    "user_input": "GraphAIについて教えて",
    "model_name": "test"
  }'
```

**Response:**
```json
{
  "results": {
    "source": "GraphAIについて教えて",
    "output": { "text": "GraphAI response..." }
  },
  "errors": {},
  "logs": [
    {
      "nodeId": "source",
      "state": "injected",
      "endTime": 1760175441540
    },
    {
      "nodeId": "output",
      "state": "completed",
      "startTime": 1760175441540,
      "endTime": 1760175441553,
      "retryCount": 0
    }
  ]
}
```

**Error Response (if timeout or node failure):**
```json
{
  "results": {
    "source": "Input text",
    "node1": { "output": "..." }
  },
  "errors": {
    "node2": {
      "message": "Timeout",
      "stack": "Error: Timeout\n    at ..."
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

### Workflow Registration Endpoint

```bash
POST /api/v1/workflows/register
```

Registers a new GraphAI workflow by saving the YAML content to the config directory. Supports organizing workflows into subdirectories.

**Request Body:**
```json
{
  "workflow_name": "my_workflow",
  "yaml_content": "version: 0.5\nnodes:\n  ...",
  "directory": "category/subcategory",  // Optional
  "overwrite": false                     // Optional
}
```

**Examples:**

```bash
# Register to root directory
curl -X POST http://localhost:8000/api/v1/workflows/register \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_name": "test_workflow",
    "yaml_content": "version: 0.5\nnodes: ..."
  }'

# Register to subdirectory
curl -X POST http://localhost:8000/api/v1/workflows/register \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_name": "podcast_generator",
    "yaml_content": "version: 0.5\nnodes: ...",
    "directory": "llmwork"
  }'

# Register to nested subdirectory
curl -X POST http://localhost:8000/api/v1/workflows/register \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_name": "advanced_agent",
    "yaml_content": "version: 0.5\nnodes: ...",
    "directory": "expert/v2"
  }'
```

**Directory parameter examples:**
- `directory: "test0001"` → `config/graphai/test0001/my_workflow.yml`
- `directory: "test/0001"` → `config/graphai/test/0001/my_workflow.yml`
- `directory` not specified → `config/graphai/my_workflow.yml`

For detailed API documentation including all response formats, see [docs/API_ENDPOINTS.md](docs/API_ENDPOINTS.md).

## MyVault Integration

🔐 **SecretsManager** provides centralized secret management with MyVault priority and environment variable fallback.

### Environment Variables

Create a `.env` file in the project root:

```env
# Server Configuration
PORT=8100
NODE_ENV=development

# MyVault Configuration (recommended for secret management)
MYVAULT_ENABLED=true
MYVAULT_BASE_URL=http://localhost:8105
MYVAULT_SERVICE_NAME=graphAiServer
MYVAULT_SERVICE_TOKEN=your-service-token
MYVAULT_DEFAULT_PROJECT=your-project-name
SECRETS_CACHE_TTL=300  # Cache TTL in seconds (default: 300)

# API Keys (fallback if MyVault is unavailable)
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
GOOGLE_API_KEY=your-google-key
GROQ_API_KEY=your-groq-key
```

### Features

- 🔒 Priority-based secret retrieval: MyVault → Environment Variables → Error
- ⚡ TTL-based caching (default 300s) for performance
- 🔄 Manual cache reload capabilities
- 📁 Project-level secret grouping
- 🛡️ Comprehensive error handling

### Usage Example

```typescript
import { secretsManager } from './src/services/secretsManager';

// Get secret (tries MyVault first, falls back to env var)
const apiKey = await secretsManager.getSecret('OPENAI_API_KEY');

// Get secret from specific project
const apiKey = await secretsManager.getSecret('OPENAI_API_KEY', 'my-project');

// Get all secrets for a project
const secrets = await secretsManager.getSecretsForProject('my-project');

// Clear cache (manual reload)
secretsManager.clearCache();  // Clear all cache
secretsManager.clearCache('my-project');  // Clear specific project
```

### Secret Retrieval Priority

1. **MyVault** (if `MYVAULT_ENABLED=true`)
   - Checks cache first (if within TTL)
   - Fetches from MyVault API if cache miss
   - Uses specified project or default project
2. **Environment Variable** (fallback)
   - Falls back to `.env` or system environment
3. **Error** (if not found anywhere)
   - Throws error with descriptive message

### Test Coverage

The MyVault integration includes comprehensive tests:
- `tests/myvaultClient.test.ts` - 13 tests for MyVault HTTP client
- `tests/secretsManager.test.ts` - 16 tests for SecretsManager logic
- `tests/integration/app.test.ts` - Integration tests

Run tests: `npm test`

## Development

### Project Structure

```
graphAiServer/
├── src/                    # Source code
│   ├── app.ts             # Express application
│   ├── index.ts           # Entry point
│   └── services/          # Service layer
│       └── graphai.ts     # GraphAI service
├── config/                # Configuration files
│   └── graphai/          # GraphAI workflow YAML files
│       └── test.yml
├── tests/                 # Test files
│   ├── unit/             # Unit tests
│   └── integration/      # Integration tests
├── dist/                  # Build output
├── Dockerfile            # Docker configuration
├── package.json          # Dependencies and scripts
└── tsconfig.json         # TypeScript configuration
```

### Environment Variables

Create a `.env` file in the project root (or copy from `.env.example`):

```env
PORT=8000
NODE_ENV=development

# GraphAI Configuration
MODEL_BASE_PATH=./config/graphai/

OPENAI_API_KEY=your_openai_api_key_here
```

### GraphAI Workflows

GraphAI workflows are defined in YAML files under `config/graphai/`. You can create custom workflows by:

1. Creating a new `.yml` file in `config/graphai/`
2. Defining nodes, agents, and connections
3. Referencing the workflow name in the API request

**Example workflow structure:**
```yaml
version: 0.5
nodes:
  source: {}
  expertAgent:
    agent: fetchAgent
    inputs:
      url: http://example.com/api
      method: POST
      body:
        user_input: :source
  output:
    agent: copyAgent
    inputs:
      text: :expertAgent.text
    isResult: true
```

## CI/CD Integration

This project is integrated with MySwiftAgent's multi-release workflow:

- **Feature branches** → `develop` (with `feature` label for minor version bump)
- **Release branches** → `release/graphAiServer/vX.Y.Z`
- **Releases** → `main` (automatic tagging and GitHub Release)

See [CLAUDE.md](../CLAUDE.md) for detailed workflow information.

## Version

Current version: 0.1.0

## License

MIT

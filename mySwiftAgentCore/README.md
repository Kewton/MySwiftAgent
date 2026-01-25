# mySwiftAgentCore

🚀 **mySwiftAgentCore** はMySwiftAgentの**メインワークフロー実行エンジン**です。
TaskFlow形式のワークフロー生成・実行を担当します。

| 項目 | 値 |
|------|-----|
| **レイヤー** | Agent層 |
| **役割** | TaskFlowワークフロー実行（推奨） |
| **技術スタック** | TypeScript + Express |
| **ポート** | 8006 |

> **Note**: ワークフロー実行は基本的にmySwiftAgentCoreを使用してください。
> GraphAI OSS形式を使用する場合のみgraphAiServerを使用します。

## 概要

This module provides:

- **Context Management**: ExecutionContext, VariableResolver, SecretManager, and ValidationCoordinator
- **Shared Types**: Workflow, Capability, and Error type definitions
- **Security**: Authentication middleware and security configuration
- **Service Stubs**: TaskFlow Engine, TaskFlow Generator Agent, and Capability Management

## Requirements

- Node.js 20+
- npm or Bun

## Installation

```bash
cd mySwiftAgentCore
npm install
```

## Development

### Start Development Server

```bash
npm run dev
```

The server will start on port 8006.

### Build

```bash
npm run build
```

### Run Tests

```bash
# Run tests
npm test

# Run tests with coverage
npm run test:coverage
```

### Linting

```bash
npm run lint
```

## API Endpoints

### Health Check

- `GET /health` - Basic health check
- `GET /health/detailed` - Detailed health with dependencies
- `GET /health/ready` - Readiness check
- `GET /health/live` - Liveness check

### API v1

- `GET /api/v1` - API version info
- `GET /api/v1/taskflow` - TaskFlow Engine stub
- `GET /api/v1/generator` - TaskFlow Generator stub
- `GET /api/v1/capabilities` - Capability Management stub

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PORT` | No | `8006` | Server port |
| `API_TOKEN` | Yes | - | API authentication token |
| `ADMIN_TOKEN` | Yes | - | Admin authentication token |
| `MYVAULT_SERVICE_TOKEN` | Yes | - | MyVault service token |
| `MYVAULT_ENABLED` | No | `false` | Enable MyVault integration |
| `MYVAULT_BASE_URL` | No | `http://localhost:8003` | MyVault base URL |
| `LANGFUSE_SECRET_KEY` | No | - | Langfuse secret key |
| `LANGFUSE_PUBLIC_KEY` | No | - | Langfuse public key |
| `LANGFUSE_BASE_URL` | No | - | Langfuse base URL |

## Architecture

### Documentation

For detailed specifications, see:

- **[API Reference](./docs/API_REFERENCE.md)** - 全APIエンドポイント仕様
- **[TaskFlow実行エンジン](./docs/features/taskflow-execution.md)** - 実行エンジンの詳細仕様
- **[ノード実行コンテキスト](./docs/internals/node-execution-context.md)** - ノード開発者向けコンテキスト仕様
- **[TaskFlow形式仕様](../docs/reference/taskflow-format.md)** - ワークフロー定義形式

### Context Management

The Context Manager follows the Facade + Dependency Injection pattern:

```typescript
import {
  createExecutionContext,
  createVariableResolver,
  createSecretManager,
  createValidationCoordinator,
} from './shared/context';

// Create execution context for a workflow
const context = createExecutionContext(workflow, {
  requestId: 'req_123',
  timeout: 60000,
});

// Resolve variables in templates
const resolver = createVariableResolver();
const resolved = await resolver.resolveString('${context.variables.input}', context);

// Manage secrets
const secretManager = createSecretManager({
  myVault: { baseUrl: 'http://localhost:8003', serviceToken: 'token' },
  fallbackToEnv: true,
});
const secret = await secretManager.get('MY_SECRET');

// Validate workflows
const validator = createValidationCoordinator();
const result = validator.validateWorkflow(workflow);
```

### Partial Success Model

Results use a three-state status:

```typescript
type ExecutionStatus = 'success' | 'partial_success' | 'failed';

interface WorkflowExecutionResult {
  status: ExecutionStatus;
  stepResults: StepResult[];
  errors: StepError[];
  recoveryActions: RecoveryAction[];
}
```

## Docker

### Build

```bash
docker build -t myswiftagentcore .
```

### Run

```bash
docker run -d \
  -p 8006:8006 \
  -e API_TOKEN=your-api-token \
  -e ADMIN_TOKEN=your-admin-token \
  -e MYVAULT_SERVICE_TOKEN=your-myvault-token \
  myswiftagentcore
```

## Integration

### With Docker Compose

```bash
# Start mySwiftAgentCore with dependencies
docker compose -f docker-compose.core.yml up -d

# Or use make
make dev-core
```

### With dev-hybrid.sh

```bash
# Start in development mode
./scripts/dev-hybrid.sh
```

## Testing

### Unit Tests

```bash
npm run test
```

### Coverage

```bash
npm run test:coverage
```

Coverage target: 90%+

## License

MIT

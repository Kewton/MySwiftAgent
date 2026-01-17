# Issue #364 設計方針書

**Issue**: #364 - feat(mySwiftAgentCore): taskflowGeneratorAgent - ワークフロー生成エージェントの実装
**作成日**: 2026-01-16
**ステータス**: 設計中

---

## 1. 概要

### 1.1 背景

Issue #359で設計された3フェーズ統一ID方式において、Phase 3: WORKFLOW_GENがexpertAgent（Python）からmySwiftAgentCore（TypeScript）に分離されることが決定された（Issue #366方針変更）。

本Issueは、TaskFlow JSON生成機能をTypeScriptで新規実装し、以下を実現する：

1. expertAgentからHTTP API経由での呼び出し
2. capabilitiesを活用したワークフロー生成
3. Langfuseトレース連携（expertAgentから引き継ぎ）
4. 並列実行によるパフォーマンス向上

### 1.2 目的

- expertAgent（Python）とmySwiftAgentCore（TypeScript）の責務分離
- HTTP API境界での疎結合アーキテクチャ
- Capabilityベースの動的ワークフロー生成
- 完全な観測可能性（Langfuseトレース統合）

### 1.3 スコープ

**含む**:
- TaskFlow Generator API実装
- LLMクライアント統合（Anthropic/OpenAI/Gemini）
- バッチ生成API（並列実行）
- Langfuseトレース統合
- TaskFlowバリデーション
- taskflowEngine連携

**含まない**:
- Job Analysis（Phase 1）- expertAgentに残る
- Registration（Phase 2）- expertAgentに残る
- ワークフロー実行 - taskflowEngineが担当

---

## 2. 受入条件 (Acceptance Criteria)

### AC-1: ワークフロー生成
- タスク定義、capabilities、interfacesを入力としてTaskFlow JSONを生成
- graphAiServer互換のTaskFlow形式を出力
- LLMプロンプトにcapabilitiesを含める

### AC-2: バッチ生成API
- 複数タスクの並列生成（max_concurrency制御）
- `POST /api/v1/generator/workflow/batch`エンドポイント
- タスクごとの成功/失敗状態管理

### AC-3: リカバリー戦略
- RETRY_CURRENT: 最大3回リトライ
- ROLLBACK_TO_ANALYSIS: recovery_suggestionをレスポンス
- FAIL_FAST: 即座に失敗レスポンス

### AC-4: Langfuseトレース
- expertAgentからtrace_contextを引き継ぎ
- WORKFLOW_GENスパンの作成
- LLM GenerationとしてAPIコール記録
- token使用量とレイテンシの記録

### AC-5: バリデーション
- 生成されたTaskFlow JSONのスキーマ検証
- ステップ間依存関係の妥当性チェック
- 無効な変数参照の検出

### AC-6: taskflowEngine統合
- 生成したワークフローをtaskflowEngineに登録
- WorkflowRegistryへの保存
- 登録成功/失敗の記録

### AC-7: TypeScript SDK
- TaskFlowGeneratorClientクラスの提供
- expertAgentからの呼び出しインターフェース

---

## 3. 設計方針 (Design Policy)

> **重要**: 型定義のSingle Source of Truthは `docs/spec/api/taskflow-generator-api.yaml` です。
> expertAgent（Python）とmySwiftAgentCore（TypeScript）の両方がこのOpenAPI仕様に準拠する必要があります。

### DP-1: サービス境界の明確化

**方針**: expertAgentとmySwiftAgentCore間をHTTP APIで完全分離

**詳細**:
```typescript
// API境界定義
interface TaskGenerationRequest {
  task_id: string;
  task_master_id: string;
  name: string;
  description: string;
  dependencies: string[];
  interface: InterfaceDefinition;
}

interface BatchGenerationRequest {
  tasks: TaskGenerationRequest[];
  capabilities: Capability[];
  project_id: string;
  options: GenerationOptions;
  trace_context?: TraceContext;
}
```

**理由**:
- 言語間依存を排除（Python ⇔ TypeScript）
- デプロイメント独立性の確保
- API versioning による後方互換性

### DP-2: LLMクライアント抽象化

**方針**: プロバイダー非依存のLLMクライアントインターフェース

**詳細**:
```typescript
// LLMクライアント抽象化
interface LLMClient {
  generateStructured<T>(
    prompt: LLMPrompt,
    responseSchema: z.ZodSchema<T>,
    options?: LLMOptions
  ): Promise<StructuredResponse<T>>;
}

// プロバイダー実装
class AnthropicClient implements LLMClient { }
class OpenAIClient implements LLMClient { }
class GeminiClient implements LLMClient { }

// ファクトリーパターン（MyVault統合必須）
class LLMClientFactory {
  constructor(private myVaultClient: MyVaultClient) {}

  async create(modelName: string): Promise<LLMClient> {
    // APIキーは必ずMyVault経由で取得（環境変数フォールバック禁止）
    if (modelName.startsWith('claude')) {
      const apiKey = await this.myVaultClient.getSecret('anthropic_api_key');
      return new AnthropicClient(apiKey);
    }
    if (modelName.startsWith('gpt')) {
      const apiKey = await this.myVaultClient.getSecret('openai_api_key');
      return new OpenAIClient(apiKey);
    }
    if (modelName.startsWith('gemini')) {
      const apiKey = await this.myVaultClient.getSecret('gemini_api_key');
      return new GeminiClient(apiKey);
    }
    throw new Error(`Unknown model: ${modelName}`);
  }
}
```

**理由**:
- 新しいLLMプロバイダーの追加が容易
- テスト時のモック化が簡単
- プロバイダー固有の実装詳細を隠蔽

### DP-3: Capabilityコンテキスト統合

**方針**: Capabilityをプロンプトに構造化して注入

**詳細**:
```typescript
class PromptBuilder {
  buildSystemPrompt(capabilities: Capability[]): string {
    const capabilitySection = this.formatCapabilities(capabilities);
    return `
${TASKFLOW_RULES}

## Available Capabilities

${capabilitySection}

You can use these capabilities in api_rest steps by referencing their IDs.
`;
  }

  private formatCapabilities(capabilities: Capability[]): string {
    return capabilities
      .filter(c => c.status === 'available')
      .map(c => `
### ${c.name} (${c.id})
- Category: ${c.category}
- Description: ${c.description}
- Parameters: ${this.formatParameters(c.parameters || [])}
`)
      .join('\n');
  }
}
```

**理由**:
- LLMが利用可能なAPIを認識
- 適切なapi_restステップの生成
- カテゴリ別の整理で理解しやすい

### DP-4: 並列実行アーキテクチャ

**方針**: Promise.allSettledによる並列処理とp-limit統合

**詳細**:
```typescript
import pLimit from 'p-limit';

class WorkflowGenerator {
  private parallelLimit: ReturnType<typeof pLimit>;

  constructor(private config: GeneratorConfig) {
    this.parallelLimit = pLimit(config.maxConcurrency || 5);
  }

  async generateBatch(
    request: BatchGenerationRequest
  ): Promise<BatchGenerationResponse> {
    const tasks = request.tasks.map(task =>
      this.parallelLimit(() => this.generateSingle(task, request))
    );

    const results = await Promise.allSettled(tasks);

    return {
      success: results.filter(r => r.status === 'fulfilled').length > 0,
      workflows: this.aggregateResults(results),
      failed_tasks: this.extractFailures(results),
      trace_url: this.tracer.getTraceUrl(),
    };
  }
}
```

**理由**:
- LLM APIのレート制限対策
- 一部失敗してもバッチ全体が停止しない
- リソース消費の制御

### DP-5: Langfuseトレース統合設計

**方針**: expertAgentからのトレースコンテキスト継続

**詳細**:
```typescript
class LangfuseIntegration {
  async continueTrace(context: TraceContext): Promise<Trace> {
    // expertAgentから引き継いだトレースを継続
    const trace = this.langfuse.trace({
      id: context.trace_id,
      name: 'job_generation',
      userId: context.user_id,
      sessionId: context.session_id,
      metadata: context.metadata,
    });

    // WORKFLOW_GENスパンを作成
    const span = trace.span({
      name: 'WORKFLOW_GEN',
      parentObservationId: context.parent_span_id,
      metadata: {
        source: 'taskflowGeneratorAgent',
        phase: 3,
      },
    });

    return { trace, span };
  }

  async recordGeneration(
    span: Span,
    task: TaskGenerationRequest,
    llmResponse: LLMResponse
  ): Promise<void> {
    // LLM呼び出しをGenerationとして記録
    span.generation({
      name: `workflow_generator_${task.task_id}`,
      model: llmResponse.model,
      modelParameters: {
        temperature: llmResponse.temperature,
        maxTokens: llmResponse.maxTokens,
      },
      input: {
        system: llmResponse.systemPrompt,
        user: llmResponse.userPrompt,
      },
      output: llmResponse.content,
      usage: {
        promptTokens: llmResponse.usage.promptTokens,
        completionTokens: llmResponse.usage.completionTokens,
      },
      metadata: {
        latencyMs: llmResponse.latencyMs,
        task_id: task.task_id,
        task_master_id: task.task_master_id,
      },
    });
  }
}
```

**理由**:
- 完全なエンドツーエンドの可観測性
- LLMコストとパフォーマンスの追跡
- デバッグとトラブルシューティングの容易さ

### DP-6: エラーハンドリングとリカバリー

**方針**: 構造化されたエラーレスポンスとリカバリー提案

**詳細**:
```typescript
enum ErrorType {
  VALIDATION_ERROR = 'VALIDATION_ERROR',
  LLM_ERROR = 'LLM_ERROR',
  TIMEOUT_ERROR = 'TIMEOUT_ERROR',
  REGISTRATION_ERROR = 'REGISTRATION_ERROR',
  CAPABILITY_NOT_FOUND = 'CAPABILITY_NOT_FOUND',
}

interface TaskError {
  task_id: string;
  error_type: ErrorType;
  message: string;
  recoverable: boolean;
  recovery_suggestion?: RecoveryStrategy;  // Defined in OpenAPI spec
}

// RecoveryStrategy is defined in OpenAPI spec (Single Source of Truth)
// See: docs/spec/api/taskflow-generator-api.yaml#/components/schemas/RecoveryStrategy
enum RecoveryStrategy {
  RETRY_CURRENT = 'RETRY_CURRENT',
  RETRY_WITH_FEEDBACK = 'RETRY_WITH_FEEDBACK',
  ROLLBACK_TO_ANALYSIS = 'ROLLBACK_TO_ANALYSIS',
  UPDATE_CAPABILITIES = 'UPDATE_CAPABILITIES',
  MANUAL_INTERVENTION = 'MANUAL_INTERVENTION',
}

class ErrorHandler {
  async handle(error: Error, context: ErrorContext): Promise<TaskError> {
    if (error instanceof ValidationError) {
      return {
        task_id: context.task_id,
        error_type: ErrorType.VALIDATION_ERROR,
        message: error.message,
        recoverable: true,
        recovery_suggestion: RecoveryStrategy.RETRY_CURRENT,
      };
    }

    if (error instanceof LLMError && error.code === 'RATE_LIMIT') {
      return {
        task_id: context.task_id,
        error_type: ErrorType.LLM_ERROR,
        message: 'Rate limit exceeded',
        recoverable: true,
        recovery_suggestion: RecoveryStrategy.RETRY_CURRENT,
      };
    }

    // 構造的な問題の場合はPhase 1からやり直しを提案
    if (error instanceof CapabilityNotFoundError) {
      return {
        task_id: context.task_id,
        error_type: ErrorType.CAPABILITY_NOT_FOUND,
        message: `Required capability not found: ${error.capabilityId}`,
        recoverable: true,
        recovery_suggestion: RecoveryStrategy.ROLLBACK_TO_ANALYSIS,
      };
    }

    // デフォルトは手動介入を提案
    return {
      task_id: context.task_id,
      error_type: ErrorType.LLM_ERROR,
      message: error.message,
      recoverable: false,
      recovery_suggestion: RecoveryStrategy.MANUAL_INTERVENTION,
    };
  }
}
```

**理由**:
- expertAgentが適切なリカバリーアクションを判断可能
- 自動リトライ可能なエラーの識別
- 構造的問題の早期発見

### DP-7: TaskFlow検証パイプライン

**方針**: 多段階検証によるワークフロー品質保証

**詳細**:
```typescript
interface ValidationPipeline {
  validators: Validator[];

  async validate(
    workflow: TaskFlowDefinition,
    context: ValidationContext
  ): Promise<ValidationResult>;
}

class TaskFlowValidator implements ValidationPipeline {
  validators = [
    new SchemaValidator(),      // Zodスキーマ検証
    new DependencyValidator(),  // 依存関係の整合性
    new VariableValidator(),    // 変数参照の妥当性
    new CapabilityValidator(),  // capability存在確認
    new SecurityValidator(),    // セキュリティチェック
  ];

  async validate(
    workflow: TaskFlowDefinition,
    context: ValidationContext
  ): Promise<ValidationResult> {
    const errors: ValidationError[] = [];
    const warnings: ValidationWarning[] = [];

    for (const validator of this.validators) {
      const result = await validator.validate(workflow, context);
      errors.push(...result.errors);
      warnings.push(...result.warnings);
    }

    return {
      isValid: errors.length === 0,
      errors,
      warnings,
      metadata: {
        validatorCount: this.validators.length,
        workflowName: workflow.workflow_name,
        stepCount: workflow.steps.length,
      },
    };
  }
}
```

**理由**:
- 無効なワークフローの早期検出
- 段階的な検証でデバッグが容易
- カスタムバリデータの追加が可能

### DP-8: TaskFlow形式の互換性維持

**方針**: graphAiServer形式への準拠とIssue #363との整合性

**詳細**:
```typescript
// graphAiServer互換形式の維持
interface TaskFlowDefinition {
  workflow_name: string;
  description?: string;
  input_schema: IOSchemaType;
  output_schema: IOSchemaType;
  steps: TaskFlowStep[];
  output: Record<string, string>;
}

// TaskFlowDefinitionAdapter（Issue #363）との連携
class WorkflowRegistrar {
  constructor(
    private taskflowClient: TaskFlowClient,
    private adapter: TaskFlowDefinitionAdapter
  ) {}

  async register(
    workflow: TaskFlowDefinition,
    projectId: string
  ): Promise<RegistrationResult> {
    // 内部形式への変換（Issue #363のアダプタを使用）
    const internalWorkflow = this.adapter.toInternal(workflow);

    // taskflowEngineに登録
    const result = await this.taskflowClient.registerWorkflow({
      project: projectId,
      workflow: internalWorkflow,
    });

    return {
      success: result.success,
      workflowId: result.workflowId,
      filePath: result.filePath,
    };
  }
}
```

**理由**:
- 既存のgraphAiServerワークフローとの互換性
- Issue #363で実装済みの機能を再利用
- 将来的な統合の容易さ

---

## 4. 技術選定

### 4.1 コア技術スタック

| 技術 | 選定理由 |
|------|---------|
| **TypeScript 5.3+** | mySwiftAgentCore標準、型安全性 |
| **Hono 3.x** | 既存のmySwiftAgentCore API framework |
| **Zod** | スキーマ検証、既存コードとの一貫性 |
| **Langfuse SDK** | トレーシング、既に#363で統合済み |
| **p-limit** | 並列実行制御、#363で採用済み |
| **axios** | HTTP client、LLM API呼び出し |

### 4.2 LLMプロバイダーSDK

| SDK | バージョン | 用途 |
|-----|-----------|------|
| **@anthropic-ai/sdk** | ^0.20.x | Claude API |
| **openai** | ^4.x | OpenAI/GPT API |
| **@google/generative-ai** | ^0.5.x | Gemini API |

---

## 5. API設計

### 5.1 REST API

#### バッチワークフロー生成
```http
POST /api/v1/generator/workflow/batch
Authorization: Bearer {token}
Content-Type: application/json

{
  "tasks": [
    {
      "task_id": "task_001",
      "task_master_id": "tm_001",
      "name": "ユーザー分析レポート生成",
      "description": "指定されたユーザーの行動分析レポートを生成",
      "dependencies": [],
      "interface": {
        "input": { "user_id": "string" },
        "output": { "report": "string", "score": "number" }
      }
    }
  ],
  "capabilities": [
    {
      "id": "user_api",
      "name": "User API",
      "description": "ユーザー情報取得API",
      "category": "api",
      "status": "available",
      "parameters": [...]
    }
  ],
  "project_id": "default_project",
  "options": {
    "max_concurrency": 5,
    "timeout_per_task_ms": 30000,
    "validate_before_register": true
  },
  "trace_context": {
    "trace_id": "job_gen_abc123",
    "parent_span_id": "registration_xyz",
    "user_id": "user_001",
    "session_id": "session_xyz"
  }
}

Response 200 OK:
{
  "success": true,
  "workflows": {
    "task_001": {
      "workflow_name": "user_analysis_workflow_task_001",
      "registered": true,
      "validation_result": {
        "isValid": true,
        "warnings": []
      }
    }
  },
  "failed_tasks": [],
  "trace_url": "https://langfuse.example.com/trace/job_gen_abc123"
}

Response 207 Multi-Status (部分成功):
{
  "success": false,
  "workflows": {
    "task_001": { ... }
  },
  "failed_tasks": [
    {
      "task_id": "task_002",
      "error_type": "VALIDATION_ERROR",
      "message": "Invalid step dependency: step_3 references non-existent step_4",
      "recoverable": true,
      "recovery_suggestion": "RETRY_CURRENT"
    }
  ],
  "trace_url": "https://langfuse.example.com/trace/job_gen_abc123"
}
```

#### ワークフロー生成状態確認
```http
GET /api/v1/generator/status/{trace_id}
Authorization: Bearer {token}

Response:
{
  "trace_id": "job_gen_abc123",
  "status": "completed",
  "total_tasks": 5,
  "completed_tasks": 4,
  "failed_tasks": 1,
  "duration_ms": 12500
}
```

### 5.2 TypeScript Client SDK

```typescript
// 使用例
import { TaskFlowGeneratorClient } from '@myswiftagent/core';

// API token must be retrieved from MyVault (no environment variable fallback)
const apiToken = await myVaultClient.getSecret('taskflow_generator_api_token');

const client = new TaskFlowGeneratorClient({
  baseUrl: 'http://localhost:8006',
  apiToken,
});

// バッチ生成
const result = await client.generateBatch({
  tasks: [...],
  capabilities: [...],
  project_id: 'my_project',
  options: {
    max_concurrency: 5,
    timeout_per_task_ms: 30000,
  },
  trace_context: {
    trace_id: 'job_gen_123',
    parent_span_id: 'registration_456',
  },
});

// 結果の処理
if (result.success) {
  console.log('All workflows generated successfully');
} else {
  // 部分的な失敗の処理
  for (const failure of result.failed_tasks) {
    if (failure.recovery_suggestion === 'ROLLBACK_TO_ANALYSIS') {
      // Phase 1からやり直し
    }
  }
}
```

---

## 6. ディレクトリ構造

```
mySwiftAgentCore/
└── src/
    └── taskflowGeneratorAgent/
        ├── index.ts                    # エントリーポイント
        ├── generator/
        │   ├── WorkflowGenerator.ts    # メイン生成ロジック
        │   ├── BatchProcessor.ts       # 並列実行管理
        │   └── WorkflowRegistrar.ts    # taskflowEngine連携
        ├── llm/
        │   ├── LLMClient.ts           # 抽象インターフェース
        │   ├── clients/
        │   │   ├── AnthropicClient.ts
        │   │   ├── OpenAIClient.ts
        │   │   └── GeminiClient.ts
        │   ├── LLMClientFactory.ts    # ファクトリー
        │   └── MarkdownParser.ts      # Gemini fallback
        ├── prompts/
        │   ├── PromptBuilder.ts       # プロンプト構築
        │   ├── templates/
        │   │   ├── system.ts          # システムプロンプト
        │   │   └── taskflow-rules.ts # TaskFlowルール
        │   └── examples/              # Few-shot examples
        │       ├── api-workflow.ts
        │       └── transform-workflow.ts
        ├── validator/
        │   ├── ValidationPipeline.ts  # パイプライン
        │   ├── validators/
        │   │   ├── SchemaValidator.ts
        │   │   ├── DependencyValidator.ts
        │   │   ├── VariableValidator.ts
        │   │   ├── CapabilityValidator.ts
        │   │   └── SecurityValidator.ts
        │   └── ValidationResult.ts
        ├── recovery/
        │   ├── ErrorHandler.ts        # エラーハンドリング
        │   ├── RetryStrategy.ts       # リトライロジック
        │   └── RecoveryAdvisor.ts     # リカバリー提案
        ├── tracing/
        │   ├── LangfuseIntegration.ts # トレース統合
        │   ├── SpanManager.ts         # スパン管理
        │   └── MetricsCollector.ts    # メトリクス収集
        ├── api/
        │   ├── routes.ts              # Honoルート定義
        │   ├── handlers.ts            # リクエストハンドラ
        │   └── middleware.ts          # 認証・ロギング
        ├── client/
        │   ├── TaskFlowGeneratorClient.ts
        │   └── types.ts
        └── types/
            ├── generator.ts           # 生成関連の型
            ├── llm.ts                 # LLM関連の型
            └── api.ts                 # API関連の型
```

---

## 7. セキュリティ設計

### 7.1 API認証
- Bearer Token認証（mySwiftAgentCore標準）
- サービス間通信用の内部トークン

### 7.2 シークレット管理
- **MyVault統合による一元管理**（環境変数フォールバックは禁止）
- すべてのAPIキー（LLMプロバイダー、外部サービス）はMyVault経由で取得
- キー暗号化at rest
- シークレット未設定時は明示的なエラーで早期失敗

### 7.3 入力検証
- Zodによる厳密な型検証
- SQLインジェクション対策（変数名のサニタイズ）
- 最大ペイロードサイズ制限

### 7.4 レート制限
- API呼び出しレート制限
- 同時実行数の制御
- タイムアウト設定

---

## 8. エラーハンドリング

### 8.1 エラー分類

| エラータイプ | リカバリー可能 | 推奨アクション |
|-------------|---------------|--------------|
| VALIDATION_ERROR | Yes | RETRY_CURRENT |
| LLM_RATE_LIMIT | Yes | RETRY_CURRENT (backoff) |
| LLM_TIMEOUT | Yes | RETRY_CURRENT |
| CAPABILITY_NOT_FOUND | Yes | ROLLBACK_TO_ANALYSIS |
| INVALID_INTERFACE | Yes | ROLLBACK_TO_ANALYSIS |
| REGISTRATION_FAILED | Yes | RETRY_CURRENT |
| INTERNAL_ERROR | No | MANUAL_INTERVENTION |

### 8.2 リトライ戦略

```typescript
const retryConfig = {
  maxAttempts: 3,
  initialDelay: 1000,
  maxDelay: 10000,
  backoffFactor: 2,
  retryableErrors: [
    'RATE_LIMIT_ERROR',
    'TIMEOUT_ERROR',
    'TEMPORARY_FAILURE',
  ],
};
```

---

## 9. 性能要件

### 9.1 レスポンスタイム
- 単一タスク生成: < 5秒（LLM呼び出し含む）
- バッチ生成（10タスク）: < 15秒（並列実行）
- バリデーション: < 100ms/workflow

### 9.2 スケーラビリティ
- 同時リクエスト: 50+
- バッチサイズ: 最大100タスク
- メモリ使用量: < 512MB

### 9.3 可用性
- APIアップタイム: 99.9%
- グレースフルシャットダウン
- ヘルスチェックエンドポイント

---

## 10. 移行計画

### 10.1 フェーズ1: 基本実装
- LLMクライアント実装
- 基本的な生成ロジック
- シンプルなバリデーション

### 10.2 フェーズ2: 統合
- expertAgentとの連携テスト
- Langfuseトレース統合
- taskflowEngine連携

### 10.3 フェーズ3: 最適化
- 並列実行の調整
- キャッシュ実装
- パフォーマンスチューニング

---

## 11. テスト戦略

### 11.1 単体テスト（90%カバレッジ）
- LLMクライアントのモック
- バリデーターの個別テスト
- エラーハンドリングのテスト

### 11.2 統合テスト
- expertAgentとのE2Eテスト
- taskflowEngineへの登録テスト
- Langfuseトレース検証

### 11.3 負荷テスト
- 並列実行のストレステスト
- メモリリークの検証
- レート制限の動作確認

---

## 12. 参考資料

### 12.1 関連Issue
- [Issue #359](https://github.com/Kewton/mySwiftAgent/issues/359): 3フェーズ統一ID方式設計
- [Issue #363](https://github.com/Kewton/mySwiftAgent/issues/363): TaskFlow Engine実装
- [Issue #365](https://github.com/Kewton/mySwiftAgent/issues/365): Capability Management実装
- [Issue #366](https://github.com/Kewton/mySwiftAgent/issues/366): コアアーキテクチャ再設計

### 12.2 参照ドキュメント
- [service-dependencies.md](../../../../docs/arch/service-dependencies.md)
- [CLAUDE.md](../../../../CLAUDE.md) - 開発ガイドライン
- **[taskflow-generator-api.yaml](../../../../docs/spec/api/taskflow-generator-api.yaml)** - OpenAPI仕様（Single Source of Truth）

### 12.3 既存実装
- expertAgent: `aiagent/langgraph/jobGeneratorV2/workflows/workflow_gen/`
- mySwiftAgentCore: `src/taskflowEngine/`, `src/capabilityManagement/`

---

## 13. 設計上の決定事項とトレードオフ

### 13.1 TypeScriptでの再実装

**決定**: expertAgent（Python）からmySwiftAgentCore（TypeScript）への移植

**トレードオフ**:
- ✅ 利点: サービス境界の明確化、独立デプロイ
- ❌ 欠点: コードの重複、メンテナンスコスト増

**代替案**:
- Python実装をそのまま使用 → サービス分離ができない
- gRPCでの連携 → 複雑性が増す

### 13.2 LLM直接呼び出し vs expertAgent経由

**決定**: mySwiftAgentCoreから直接LLM APIを呼び出し

**トレードオフ**:
- ✅ 利点: レイテンシ削減、制御の柔軟性
- ❌ 欠点: APIキー管理の重複、LLMクライアントの再実装

**代替案**:
- expertAgent経由でLLM呼び出し → ネットワークホップ増加

### 13.3 同期API vs 非同期ジョブ

**決定**: 同期的なREST APIとして実装

**トレードオフ**:
- ✅ 利点: シンプルな実装、即座の結果取得
- ❌ 欠点: 長時間実行時のタイムアウト問題

**代替案**:
- ジョブキューベース → 複雑性増加、結果ポーリング必要

---

**承認者**: _________________
**承認日**: _________________
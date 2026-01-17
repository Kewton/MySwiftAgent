# Issue #363 設計方針書

**Issue**: #363 - feat(mySwiftAgentCore): TaskFlow実行エンジンの実装
**作成日**: 2026-01-16
**ステータス**: 設計中

---

## 1. 概要

### 1.1 背景
graphAiServer（Issue #348）で実装されたTaskFlow実行エンジンが本番稼働しているが、以下の課題がある：

1. **言語分離**: graphAiServer（TypeScript）とexpertAgent（Python）間でHTTP通信が必要
2. **レイテンシ**: ネットワーク経由での呼び出しによる遅延
3. **可用性**: graphAiServerがダウンするとworkflow実行が不可
4. **統一性**: mySwiftAgentCoreに中核機能が集約されていない

### 1.2 目的
mySwiftAgentCoreにTaskFlow実行エンジンをTypeScriptで実装し、以下を実現する：

- expertAgentからの高速なworkflow実行（HTTP通信不要）
- Langfuseトレーシングの統合
- プロジェクトベースの管理（Issue #365と連携）
- graphAiServerとの互換性維持

### 1.3 スコープ
- **含む**: TaskFlow Engine実装、Langfuseトレーシング、プロジェクト管理
- **含まない**: TaskFlow Generator（Issue #364で実装）、既存graphAiServerの置き換え

---

## 2. 受入条件 (Acceptance Criteria)

### AC-1: プロジェクト単位でTaskFlowワークフローを管理
- `config/taskflow/projects/{project_name}/workflows/`にJSON定義を配置
- プロジェクトごとに独立したワークフロー管理

### AC-2: graphAiServerと互換性のあるTaskFlow形式をサポート
- Issue #348で定義されたワークフロースキーマをサポート
- `api_rest`, `code_js`, `transform`, `parallel`, `llm`ノードタイプ

### AC-3: Langfuseトレーシング統合
- ワークフロー実行の開始/終了
- 各ステップの実行時間とステータス
- エラー発生時の詳細情報

### AC-4: REST API経由での実行
- `POST /api/v1/taskflow/execute` エンドポイント
- プロジェクト指定、ワークフロー名、入力パラメータを受付

### AC-5: TypeScript SDKの提供
- `TaskFlowClient` クラスでプログラマティックな実行
- expertAgentからHTTP経由で利用可能

### AC-6: エラーハンドリングと部分成功モデル
- 各ステップの成功/失敗を個別に追跡
- 部分的な成功でも利用可能な結果を返却

### AC-7: テストカバレッジ90%以上
- 単体テスト、結合テスト、受入テスト

---

## 3. 設計方針 (Design Policy)

### DP-1: graphAiServerとの設計統一性

**方針**: graphAiServerの実装パターンを踏襲し、将来的な統合を容易にする

**詳細**:
```typescript
// graphAiServerと同じインターフェース構造
interface WorkflowDefinition {
  workflow_name: string;
  input_schema: IOSchemaType;
  output_schema: IOSchemaType;
  steps: Step[];
  output: Record<string, string>;
}

// 同じノードタイプをサポート
type NodeType = 'api_rest' | 'code_js' | 'transform' | 'parallel' | 'llm';
```

**理由**:
- 既存ワークフローの移行を容易にする
- 学習コストを最小化
- graphAiServerとの相互運用性確保

### DP-2: プロジェクトベース管理との統合

**方針**: Issue #365のCapabilityManagementパターンを踏襲

**詳細**:
```typescript
// WorkflowRegistry（CapabilityRegistryと同じパターン）
class WorkflowRegistry {
  registerForProject(projectId: string, workflow: WorkflowDefinition): void;
  getByProject(projectId: string): WorkflowDefinition[];
  executeWorkflow(projectId: string, workflowName: string, inputs: any): Promise<WorkflowResult>;
}
```

**理由**:
- 統一されたプロジェクト管理
- コードの再利用性向上
- 一貫したAPI設計

### DP-3: Langfuseトレーシングのネイティブ統合

**方針**: Langfuseをコア機能として統合（オプショナルではない）

**詳細**:
```typescript
interface TracingConfig {
  enabled: boolean;
  langfuseSecretKey?: string;
  langfusePublicKey?: string;
  langfuseBaseUrl?: string;
}

// 各ステップ実行時に自動トレース
class WorkflowExecutor {
  private tracer: LangfuseTracer;

  async executeStep(step: Step): Promise<StepResult> {
    const trace = this.tracer.startTrace(step.id);
    try {
      const result = await this.runStep(step);
      trace.success(result);
      return result;
    } catch (error) {
      trace.error(error);
      throw error;
    }
  }
}
```

**理由**:
- パフォーマンス分析の標準化
- デバッグの容易性向上
- 本番環境での問題追跡

### DP-4: モジュラーなノード実装

**方針**: 各ノードタイプを独立したクラスとして実装（Strategy Pattern）

**詳細**:
```typescript
// ノード実行インターフェース
interface NodeExecutor {
  execute(config: NodeConfig, params: any, context: ExecutionContext): Promise<NodeResult>;
  validate(config: NodeConfig): ValidationResult;
}

// 各ノードタイプの実装
class ApiRestNodeExecutor implements NodeExecutor { ... }
class CodeJsNodeExecutor implements NodeExecutor { ... }
class TransformNodeExecutor implements NodeExecutor { ... }
class ParallelNodeExecutor implements NodeExecutor { ... }
class LlmNodeExecutor implements NodeExecutor { ... }
```

**理由**:
- 新しいノードタイプの追加が容易
- 単体テストの独立性
- 保守性の向上

### DP-5: 型定義の整合性確保（アダプターパターン）

**方針**: 既存の`workflow.types.ts`とgraphAiServer形式の両方をサポートするアダプター層を実装

**背景**:
- 既存の`WorkflowDefinition`（mySwiftAgentCore）: `id`, `name`, `version`, `steps[]`
- graphAiServer形式: `workflow_name`, `input_schema`, `output_schema`, `steps[]`, `output`
- 両形式の共存と相互変換が必要

**詳細**:
```typescript
// === 型定義 ===

// graphAiServer互換形式（外部入力）
interface TaskFlowDefinition {
  workflow_name: string;
  description?: string;
  input_schema: IOSchemaType;
  output_schema: IOSchemaType;
  steps: TaskFlowStep[];
  output: Record<string, string>;
}

// 内部統一形式
interface InternalWorkflowDefinition extends WorkflowDefinition {
  inputSchema: IOSchemaType;
  outputSchema: IOSchemaType;
  outputMapping: Record<string, string>;
}

// === アダプター実装 ===

/**
 * TaskFlowDefinitionAdapter - 型変換を担当
 *
 * 責務: graphAiServer形式 <-> 内部形式の双方向変換
 */
class TaskFlowDefinitionAdapter {
  /**
   * graphAiServer形式から内部形式へ変換
   */
  static toInternal(external: TaskFlowDefinition): InternalWorkflowDefinition {
    return {
      id: this.generateId(external.workflow_name),
      name: external.workflow_name,
      version: '1.0.0',
      steps: external.steps.map(step => this.convertStep(step)),
      inputSchema: external.input_schema,
      outputSchema: external.output_schema,
      outputMapping: external.output,
      timeout: 300000, // デフォルト5分
    };
  }

  /**
   * 内部形式からgraphAiServer形式へ変換（API応答用）
   */
  static toExternal(internal: InternalWorkflowDefinition): TaskFlowDefinition {
    return {
      workflow_name: internal.name,
      input_schema: internal.inputSchema,
      output_schema: internal.outputSchema,
      steps: internal.steps as TaskFlowStep[],
      output: internal.outputMapping,
    };
  }

  /**
   * ステップ形式の変換
   */
  private static convertStep(step: TaskFlowStep): WorkflowStep {
    return {
      id: step.id,
      name: step.description || step.id,
      type: step.type,
      config: step.config as Record<string, unknown>,
      dependsOn: this.extractDependencies(step),
    };
  }

  /**
   * params内の変数参照から依存関係を抽出
   */
  private static extractDependencies(step: TaskFlowStep): string[] {
    const deps: string[] = [];
    const paramStr = JSON.stringify(step.params || {});
    const regex = /\$\{(\w+)\.output/g;
    let match;
    while ((match = regex.exec(paramStr)) !== null) {
      if (match[1] && !deps.includes(match[1])) {
        deps.push(match[1]);
      }
    }
    return deps;
  }

  private static generateId(name: string): string {
    return `wf_${name.toLowerCase().replace(/\s+/g, '_')}_${Date.now()}`;
  }
}
```

**使用パターン**:
```typescript
// ワークフロー登録時
class WorkflowRegistry {
  registerFromTaskFlow(projectId: string, taskflow: TaskFlowDefinition): void {
    const internal = TaskFlowDefinitionAdapter.toInternal(taskflow);
    this.register(projectId, internal);
  }
}

// API応答時
class WorkflowHandler {
  getWorkflow(projectId: string, name: string): TaskFlowDefinition {
    const internal = this.registry.get(projectId, name);
    return TaskFlowDefinitionAdapter.toExternal(internal);
  }
}
```

**理由**:
- 既存コードへの影響を最小化
- graphAiServerとの完全な互換性維持
- 内部処理は統一形式で一貫性確保
- 将来的な形式変更にも柔軟に対応

### DP-6: code_jsノードのセキュリティ強化（サンドボックス実装）

**方針**: `isolated-vm`を使用した安全なJavaScript実行環境を提供

**背景**:
- `code_js`ノードは任意のJavaScriptを実行可能
- 悪意あるコードによるシステム侵害リスク
- ファイルシステムアクセス、ネットワーク通信、プロセス操作を制限必須

**詳細**:
```typescript
// === 依存関係追加 ===
// package.json
{
  "dependencies": {
    "isolated-vm": "^4.x"
  }
}

// === サンドボックス実装 ===

import ivm from 'isolated-vm';

/**
 * スクリプトホワイトリスト管理
 */
interface ScriptWhitelist {
  /** 許可されたスクリプトパス（config/taskflow/scripts/配下の相対パス） */
  allowedPaths: string[];
  /** スクリプトハッシュによる整合性検証 */
  scriptHashes: Map<string, string>;
}

/**
 * サンドボックス設定
 */
interface SandboxConfig {
  /** メモリ上限（MB） */
  memoryLimitMb: number;
  /** 実行タイムアウト（ms） */
  timeoutMs: number;
  /** 許可するグローバルオブジェクト */
  allowedGlobals: string[];
}

const DEFAULT_SANDBOX_CONFIG: SandboxConfig = {
  memoryLimitMb: 128,
  timeoutMs: 30000,
  allowedGlobals: ['console', 'JSON', 'Math', 'Date', 'Array', 'Object', 'String', 'Number', 'Boolean'],
};

/**
 * CodeJsSandbox - 安全なJavaScript実行環境
 */
class CodeJsSandbox {
  private isolate: ivm.Isolate;
  private whitelist: ScriptWhitelist;
  private config: SandboxConfig;

  constructor(whitelist: ScriptWhitelist, config: SandboxConfig = DEFAULT_SANDBOX_CONFIG) {
    this.whitelist = whitelist;
    this.config = config;
    this.isolate = new ivm.Isolate({ memoryLimit: config.memoryLimitMb });
  }

  /**
   * スクリプトの検証と実行
   */
  async execute(
    scriptPath: string,
    functionName: string,
    params: Record<string, unknown>
  ): Promise<unknown> {
    // 1. ホワイトリスト検証
    if (!this.isWhitelisted(scriptPath)) {
      throw new SecurityError(
        `Script not in whitelist: ${scriptPath}`,
        'SCRIPT_NOT_WHITELISTED'
      );
    }

    // 2. スクリプト読み込みと整合性検証
    const script = await this.loadAndVerifyScript(scriptPath);

    // 3. 隔離されたコンテキストの作成
    const context = await this.isolate.createContext();

    // 4. 安全なグローバルの注入
    await this.injectSafeGlobals(context);

    // 5. パラメータの注入（deep copy）
    const jail = context.global;
    await jail.set('__params__', new ivm.ExternalCopy(params).copyInto());

    // 6. スクリプトのコンパイルと実行
    const compiled = await this.isolate.compileScript(script);
    await compiled.run(context);

    // 7. 関数の実行
    const fn = await jail.get(functionName);
    if (!fn) {
      throw new SecurityError(
        `Function not found: ${functionName}`,
        'FUNCTION_NOT_FOUND'
      );
    }

    const result = await fn.apply(
      undefined,
      [new ivm.ExternalCopy(params).copyInto()],
      { timeout: this.config.timeoutMs }
    );

    // 8. 結果の安全なコピー
    return result.copy();
  }

  /**
   * ホワイトリスト検証
   */
  private isWhitelisted(scriptPath: string): boolean {
    const normalizedPath = path.normalize(scriptPath);

    // パストラバーサル攻撃の防止
    if (normalizedPath.includes('..')) {
      return false;
    }

    return this.whitelist.allowedPaths.includes(normalizedPath);
  }

  /**
   * スクリプトの読み込みと整合性検証
   */
  private async loadAndVerifyScript(scriptPath: string): Promise<string> {
    const fullPath = path.join(SCRIPTS_BASE_DIR, scriptPath);
    const content = await fs.readFile(fullPath, 'utf-8');

    // ハッシュによる整合性検証
    const hash = crypto.createHash('sha256').update(content).digest('hex');
    const expectedHash = this.whitelist.scriptHashes.get(scriptPath);

    if (expectedHash && hash !== expectedHash) {
      throw new SecurityError(
        `Script integrity check failed: ${scriptPath}`,
        'SCRIPT_INTEGRITY_FAILED'
      );
    }

    return content;
  }

  /**
   * 安全なグローバルオブジェクトの注入
   */
  private async injectSafeGlobals(context: ivm.Context): Promise<void> {
    const jail = context.global;

    // 安全なconsole（ログは収集するが外部出力なし）
    await jail.set('console', {
      log: (...args: unknown[]) => this.captureLog('log', args),
      warn: (...args: unknown[]) => this.captureLog('warn', args),
      error: (...args: unknown[]) => this.captureLog('error', args),
    });

    // 読み取り専用のJSON
    await jail.set('JSON', {
      parse: JSON.parse,
      stringify: JSON.stringify,
    });

    // Mathは安全なのでそのまま
    await jail.set('Math', Math);
  }

  /**
   * リソースの解放
   */
  dispose(): void {
    this.isolate.dispose();
  }
}

/**
 * セキュリティエラー
 */
class SecurityError extends Error {
  constructor(message: string, public code: string) {
    super(message);
    this.name = 'SecurityError';
  }
}
```

**ホワイトリスト管理**:
```yaml
# config/taskflow/scripts/whitelist.yaml
version: "1.0"
scripts:
  - path: "calculators/risk_model.js"
    hash: "sha256:abc123..."
    description: "リスクスコア計算"
  - path: "transformers/data_mapper.js"
    hash: "sha256:def456..."
    description: "データ変換ユーティリティ"
```

**禁止される操作**:
| 操作 | 制限方法 | 理由 |
|------|---------|------|
| ファイルシステムアクセス | `fs`モジュール未提供 | データ漏洩防止 |
| ネットワーク通信 | `http/https`未提供 | 外部通信禁止 |
| プロセス操作 | `process`未提供 | システム操作禁止 |
| 環境変数アクセス | `process.env`未提供 | シークレット保護 |
| require/import | 無効化 | 任意モジュール読込禁止 |

**理由**:
- 任意コード実行による攻撃を防止
- メモリ・CPU使用量を制限しDoS攻撃を防止
- ホワイトリストによる実行可能スクリプトの制限
- 整合性検証による改ざん検知

### DP-7: 並列実行制御の具体化（p-limitパターン）

**方針**: `p-limit`ライブラリを使用した明確なリソース管理

**背景**:
- 無制限のPromise.allはリソース枯渇のリスク
- 外部APIのレート制限対応が必要
- メモリ使用量の制御が必要

**詳細**:
```typescript
// === 依存関係追加 ===
// package.json
{
  "dependencies": {
    "p-limit": "^5.x"
  }
}

// === 並列実行設定 ===

/**
 * 並列実行設定
 */
interface ParallelExecutionConfig {
  /** グローバル最大並列数（全ワークフロー合計） */
  globalMaxConcurrency: number;
  /** ワークフローあたりの最大並列数 */
  workflowMaxConcurrency: number;
  /** ノードタイプ別の並列数制限 */
  nodeTypeLimits: {
    api_rest: number;
    code_js: number;
    llm: number;
    transform: number;
  };
  /** キュー待機タイムアウト（ms） */
  queueTimeoutMs: number;
}

const DEFAULT_PARALLEL_CONFIG: ParallelExecutionConfig = {
  globalMaxConcurrency: 50,      // システム全体で50並列まで
  workflowMaxConcurrency: 10,    // 1ワークフローで10並列まで
  nodeTypeLimits: {
    api_rest: 20,  // 外部API呼び出しは控えめに
    code_js: 10,   // CPU集約的なので制限
    llm: 5,        // LLM APIは特に制限（コスト・レート制限）
    transform: 30, // 軽量なので多めに許可
  },
  queueTimeoutMs: 60000,         // 1分でタイムアウト
};

// === 並列実行マネージャー ===

import pLimit from 'p-limit';

/**
 * ParallelExecutionManager - 並列実行のリソース管理
 *
 * 3層の並列数制限を実装：
 * 1. グローバル制限: システム全体の並列数
 * 2. ワークフロー制限: 個別ワークフローの並列数
 * 3. ノードタイプ制限: ノードタイプごとの並列数
 */
class ParallelExecutionManager {
  private globalLimiter: ReturnType<typeof pLimit>;
  private nodeTypeLimiters: Map<string, ReturnType<typeof pLimit>>;
  private workflowLimiters: Map<string, ReturnType<typeof pLimit>>;
  private config: ParallelExecutionConfig;

  // メトリクス
  private metrics = {
    activeGlobal: 0,
    activeByWorkflow: new Map<string, number>(),
    activeByNodeType: new Map<string, number>(),
    queuedTasks: 0,
    completedTasks: 0,
    failedTasks: 0,
  };

  constructor(config: ParallelExecutionConfig = DEFAULT_PARALLEL_CONFIG) {
    this.config = config;
    this.globalLimiter = pLimit(config.globalMaxConcurrency);
    this.nodeTypeLimiters = new Map();
    this.workflowLimiters = new Map();

    // ノードタイプ別リミッターの初期化
    for (const [type, limit] of Object.entries(config.nodeTypeLimits)) {
      this.nodeTypeLimiters.set(type, pLimit(limit));
    }
  }

  /**
   * タスクの実行（3層の制限を適用）
   */
  async execute<T>(
    workflowId: string,
    nodeType: string,
    task: () => Promise<T>
  ): Promise<T> {
    // ワークフロー別リミッターの取得/作成
    if (!this.workflowLimiters.has(workflowId)) {
      this.workflowLimiters.set(
        workflowId,
        pLimit(this.config.workflowMaxConcurrency)
      );
    }
    const workflowLimiter = this.workflowLimiters.get(workflowId)!;
    const nodeTypeLimiter = this.nodeTypeLimiters.get(nodeType) || this.globalLimiter;

    // メトリクス更新
    this.metrics.queuedTasks++;

    try {
      // 3層のリミッターを通過
      return await this.globalLimiter(async () => {
        return await workflowLimiter(async () => {
          return await nodeTypeLimiter(async () => {
            this.metrics.queuedTasks--;
            this.metrics.activeGlobal++;
            this.updateActiveMetrics(workflowId, nodeType, 1);

            try {
              const result = await this.executeWithTimeout(task);
              this.metrics.completedTasks++;
              return result;
            } catch (error) {
              this.metrics.failedTasks++;
              throw error;
            } finally {
              this.metrics.activeGlobal--;
              this.updateActiveMetrics(workflowId, nodeType, -1);
            }
          });
        });
      });
    } catch (error) {
      this.metrics.queuedTasks--;
      throw error;
    }
  }

  /**
   * 並列ブロックの実行
   */
  async executeParallelBlock<T>(
    workflowId: string,
    tasks: Array<{ nodeType: string; task: () => Promise<T> }>
  ): Promise<Array<{ status: 'fulfilled' | 'rejected'; value?: T; reason?: Error }>> {
    const promises = tasks.map(({ nodeType, task }) =>
      this.execute(workflowId, nodeType, task)
        .then(value => ({ status: 'fulfilled' as const, value }))
        .catch(reason => ({ status: 'rejected' as const, reason }))
    );

    return Promise.all(promises);
  }

  /**
   * タイムアウト付き実行
   */
  private async executeWithTimeout<T>(task: () => Promise<T>): Promise<T> {
    const timeoutPromise = new Promise<never>((_, reject) => {
      setTimeout(
        () => reject(new Error('Task execution timeout')),
        this.config.queueTimeoutMs
      );
    });

    return Promise.race([task(), timeoutPromise]);
  }

  /**
   * メトリクス更新
   */
  private updateActiveMetrics(workflowId: string, nodeType: string, delta: number): void {
    // ワークフロー別
    const currentWorkflow = this.metrics.activeByWorkflow.get(workflowId) || 0;
    this.metrics.activeByWorkflow.set(workflowId, currentWorkflow + delta);

    // ノードタイプ別
    const currentNodeType = this.metrics.activeByNodeType.get(nodeType) || 0;
    this.metrics.activeByNodeType.set(nodeType, currentNodeType + delta);
  }

  /**
   * 現在のメトリクスを取得
   */
  getMetrics(): typeof this.metrics {
    return { ...this.metrics };
  }

  /**
   * リソースの解放
   */
  cleanup(workflowId: string): void {
    this.workflowLimiters.delete(workflowId);
    this.metrics.activeByWorkflow.delete(workflowId);
  }
}
```

**使用例**:
```typescript
// WorkflowExecutor での使用
class WorkflowExecutor {
  private parallelManager: ParallelExecutionManager;

  async executeParallelSteps(
    workflowId: string,
    steps: Step[]
  ): Promise<StepResult[]> {
    const tasks = steps.map(step => ({
      nodeType: step.type,
      task: () => this.executeStep(step),
    }));

    const results = await this.parallelManager.executeParallelBlock(
      workflowId,
      tasks
    );

    return results.map((result, index) => {
      if (result.status === 'fulfilled') {
        return result.value!;
      } else {
        return this.createFailedResult(steps[index]!, result.reason!);
      }
    });
  }
}
```

**リソース管理方針**:

| リソース | 制限値 | 監視方法 | 超過時の動作 |
|---------|-------|---------|------------|
| グローバル並列数 | 50 | メトリクス | キュー待機 |
| ワークフロー並列数 | 10 | メトリクス | キュー待機 |
| LLM API並列数 | 5 | メトリクス | キュー待機 |
| キュー待機時間 | 60秒 | タイムアウト | エラー返却 |

**メトリクス収集**:
```typescript
// Prometheus形式でエクスポート
const metrics = parallelManager.getMetrics();
// {
//   activeGlobal: 15,
//   activeByWorkflow: Map { 'wf_1' => 5, 'wf_2' => 10 },
//   activeByNodeType: Map { 'api_rest' => 8, 'llm' => 3, 'transform' => 4 },
//   queuedTasks: 5,
//   completedTasks: 1000,
//   failedTasks: 10
// }
```

**理由**:
- 3層の制限で柔軟かつ安全なリソース管理
- ノードタイプ別制限で外部APIのレート制限対応
- メトリクス収集で運用監視が可能
- p-limitの採用で実績あるパターンを活用

---

## 4. 技術選定

### 4.1 コア技術スタック

| 技術 | 選定理由 |
|------|---------|
| **TypeScript 5.3+** | 型安全性、mySwiftAgentCore標準 |
| **Hono 3.x** | 軽量、高性能なWebフレームワーク |
| **Zod** | ランタイム型検証、スキーマ定義 |
| **Langfuse SDK** | トレーシング統合 |
| **Vitest** | 高速なテスト実行 |
| **isolated-vm** | code_jsノードのサンドボックス実行（DP-6） |
| **p-limit** | 並列実行数の制御（DP-7） |

### 4.2 依存関係

```json
{
  "dependencies": {
    "@langfuse/langfuse": "^3.x",
    "hono": "^3.x",
    "zod": "^3.x",
    "axios": "^1.x",
    "handlebars": "^4.x",
    "isolated-vm": "^4.x",
    "p-limit": "^5.x",
    "js-yaml": "^4.x"
  }
}
```

---

## 5. API設計

### 5.1 REST API

#### ワークフロー実行
```http
POST /api/v1/taskflow/execute
Authorization: Bearer {token}
Content-Type: application/json

{
  "project": "default_project",
  "workflow": "user_analysis_workflow",
  "inputs": {
    "user_id": "12345",
    "include_history": true
  }
}

Response:
{
  "workflowId": "wf_123",
  "status": "success",
  "results": { ... },
  "errors": [],
  "trace_id": "langfuse_trace_123"
}
```

#### ワークフロー一覧取得
```http
GET /api/v1/taskflow/workflows?project=default_project
Authorization: Bearer {token}

Response:
{
  "workflows": [
    {
      "name": "user_analysis_workflow",
      "description": "...",
      "input_schema": { ... },
      "output_schema": { ... }
    }
  ]
}
```

### 5.2 TypeScript SDK

```typescript
// クライアント使用例
import { TaskFlowClient } from '@myswiftagent/core';

const client = new TaskFlowClient({
  baseUrl: 'http://localhost:8006',
  apiToken: process.env.API_TOKEN
});

// ワークフロー実行
const result = await client.execute({
  project: 'default_project',
  workflow: 'user_analysis_workflow',
  inputs: { user_id: '12345' }
});

// ワークフロー一覧
const workflows = await client.listWorkflows('default_project');
```

---

## 6. ディレクトリ構造

```
mySwiftAgentCore/
├── src/
│   └── taskflowEngine/
│       ├── index.ts              # エントリポイント
│       ├── types/                # 型定義
│       │   ├── TaskFlowDefinition.ts   # graphAiServer互換型
│       │   ├── InternalWorkflowDefinition.ts
│       │   └── index.ts
│       ├── adapter/              # 型変換（DP-5）
│       │   ├── TaskFlowDefinitionAdapter.ts
│       │   └── index.ts
│       ├── registry/             # ワークフロー管理
│       │   ├── WorkflowRegistry.ts
│       │   ├── ProjectManager.ts
│       │   └── index.ts
│       ├── executor/             # 実行エンジン
│       │   ├── WorkflowExecutor.ts
│       │   ├── SequentialExecutor.ts
│       │   ├── ParallelExecutor.ts
│       │   ├── ParallelExecutionManager.ts   # (DP-7)
│       │   └── index.ts
│       ├── nodes/                # ノード実装
│       │   ├── ApiRestNode.ts
│       │   ├── CodeJsNode.ts
│       │   ├── TransformNode.ts
│       │   ├── LlmNode.ts
│       │   └── index.ts
│       ├── sandbox/              # セキュリティ（DP-6）
│       │   ├── CodeJsSandbox.ts
│       │   ├── ScriptWhitelist.ts
│       │   ├── SecurityError.ts
│       │   └── index.ts
│       ├── loader/               # ワークフローローダー
│       │   ├── WorkflowLoader.ts
│       │   └── index.ts
│       ├── validator/            # スキーマ検証
│       │   ├── SchemaValidator.ts
│       │   └── index.ts
│       ├── tracer/              # Langfuse統合
│       │   ├── LangfuseTracer.ts
│       │   └── index.ts
│       ├── api/                  # REST API
│       │   ├── handlers.ts
│       │   ├── routes.ts
│       │   └── index.ts
│       └── client/               # SDK
│           ├── TaskFlowClient.ts
│           └── index.ts
├── config/
│   └── taskflow/
│       ├── scripts/              # code_jsスクリプト
│       │   ├── whitelist.yaml    # ホワイトリスト定義（DP-6）
│       │   └── calculators/
│       │       └── risk_model.js
│       └── projects/
│           └── default_project/
│               └── workflows/
│                   ├── user_analysis.json
│                   └── order_processing.json
└── tests/
    ├── unit/taskflowEngine/
    │   ├── adapter/
    │   │   └── TaskFlowDefinitionAdapter.test.ts
    │   ├── sandbox/
    │   │   └── CodeJsSandbox.test.ts
    │   └── executor/
    │       └── ParallelExecutionManager.test.ts
    ├── integration/taskflowEngine/
    └── acceptance/
```

---

## 7. セキュリティ設計

### 7.1 API認証
- Bearer Token認証（既存のmySwiftAgentCoreパターン踏襲）
- Admin専用エンドポイントの分離

### 7.2 入力検証
- Zodによる厳密な入力スキーマ検証
- SQLインジェクション、XSS対策

### 7.3 シークレット管理
- MyVault統合によるシークレット管理
- 環境変数へのフォールバック

### 7.4 実行制限
- タイムアウト設定（デフォルト5分）
- 最大並列実行数制限（DP-7: 3層制限）
- レート制限

### 7.5 code_jsノードのサンドボックス（DP-6）

| セキュリティ対策 | 実装方法 | 効果 |
|----------------|---------|------|
| **メモリ隔離** | `isolated-vm`による完全分離 | メモリ侵害防止 |
| **ホワイトリスト** | `whitelist.yaml`による許可制 | 任意スクリプト実行防止 |
| **整合性検証** | SHA-256ハッシュ照合 | 改ざん検知 |
| **パストラバーサル防止** | `..`を含むパスの拒否 | ディレクトリ探索防止 |
| **モジュール制限** | require/import無効化 | 外部モジュール読込禁止 |
| **システムアクセス制限** | fs/http/process未提供 | システム操作禁止 |
| **リソース制限** | メモリ128MB、タイムアウト30秒 | DoS攻撃防止 |

### 7.6 並列実行のリソース保護（DP-7）

| 保護対象 | 制限方式 | 制限値 |
|---------|---------|-------|
| システム全体 | グローバルリミッター | 50並列 |
| 個別ワークフロー | ワークフローリミッター | 10並列 |
| LLM API呼び出し | ノードタイプリミッター | 5並列 |
| 外部API呼び出し | ノードタイプリミッター | 20並列 |
| キュー待機 | タイムアウト | 60秒 |

---

## 8. エラーハンドリング

### 8.1 エラータイプ

```typescript
enum TaskFlowErrorCode {
  VALIDATION_ERROR = 'VALIDATION_ERROR',
  TIMEOUT = 'TIMEOUT',
  NODE_EXECUTION_ERROR = 'NODE_EXECUTION_ERROR',
  NETWORK_ERROR = 'NETWORK_ERROR',
  AUTHENTICATION_ERROR = 'AUTHENTICATION_ERROR'
}

interface TaskFlowError {
  code: TaskFlowErrorCode;
  message: string;
  stepId?: string;
  context?: Record<string, unknown>;
}
```

### 8.2 部分成功モデル
```typescript
interface WorkflowResult {
  status: 'success' | 'partial_success' | 'failed';
  completedSteps: string[];
  failedSteps: string[];
  results: Record<string, unknown>;
  errors: TaskFlowError[];
}
```

---

## 9. 性能要件

### 9.1 レスポンスタイム
- ワークフロー開始: < 100ms
- 単一ステップ実行: < 1s（外部API呼び出しを除く）
- 並列実行: Promise.allによる同時実行

### 9.2 スケーラビリティ
- 同時実行ワークフロー数: 100+
- ワークフローあたりのステップ数: 50+

---

## 10. 移行計画

### 10.1 フェーズ1: コア実装（このIssue）
- TaskFlow Engine実装
- Langfuseトレーシング統合
- 基本的なノードタイプサポート

### 10.2 フェーズ2: 統合（Issue #364後）
- TaskFlow Generatorとの統合
- expertAgentからの利用開始

### 10.3 フェーズ3: 拡張
- 追加ノードタイプのサポート
- 高度なフロー制御（条件分岐、ループ）

---

## 11. テスト戦略

### 11.1 単体テスト（90%カバレッジ）
- 各ノードExecutorの独立テスト
- WorkflowRegistryのCRUD操作
- スキーマ検証ロジック

### 11.2 結合テスト
- エンドツーエンドのワークフロー実行
- 並列実行の正確性
- エラー伝播の確認

### 11.3 受入テスト
- 実際のAPIエンドポイント呼び出し
- Langfuseトレースの確認
- パフォーマンステスト

---

## 12. 参考資料

- [Issue #348: graphAiServer TaskFlow実装](https://github.com/Kewton/mySwiftAgent/issues/348)
- [Issue #365: Capability Management実装](https://github.com/Kewton/mySwiftAgent/issues/365)
- [service-dependencies.md](../../../../docs/arch/service-dependencies.md)
- [graphAiServer TaskFlow仕様](../../../../graphAiServer/docs/GRAPHAI_WORKFLOW_GENERATION_RULES.md)

---

**承認者**: _________________
**承認日**: _________________
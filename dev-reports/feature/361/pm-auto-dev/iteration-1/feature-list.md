# Issue #361 実装機能一覧

## 概要

expertAgentとmySwiftAgentCore間の連携を実現するWorkflowGeneratorClientの実装と、orchestratorへの統合。

## 実装済み機能

### 1. HTTPクライアント抽象化層 (T1.1)

| コンポーネント | ファイル | 説明 |
|---------------|---------|------|
| IHttpClient | `clients/interfaces/http_client.py` | HTTPクライアントのProtocol定義 |
| HttpxClientAdapter | `clients/interfaces/http_client.py` | httpxベースの実装 |
| HttpResponse | `clients/interfaces/http_client.py` | レスポンスデータクラス |
| CircuitBreaker | `clients/interfaces/circuit_breaker.py` | サーキットブレーカー (CLOSED/OPEN/HALF_OPEN) |
| IMetricsCollector | `clients/interfaces/metrics.py` | メトリクス収集Protocol |
| NoOpMetricsCollector | `clients/interfaces/metrics.py` | ダミー実装 |
| LoggingMetricsCollector | `clients/interfaces/metrics.py` | ログ出力実装 |

### 2. 型定義とデータモデル (T1.2)

| 型 | ファイル | 説明 |
|----|---------|------|
| BatchStatus | `clients/types/workflow_generator.py` | 'success' \| 'partial_success' \| 'failed' |
| WorkflowStatus | `clients/types/workflow_generator.py` | 個別ワークフロー状態 |
| RecoverySuggestion | `clients/types/workflow_generator.py` | リカバリー提案 |
| TaskRequest | `clients/types/workflow_generator.py` | タスクリクエスト |
| TaskInterface | `clients/types/workflow_generator.py` | タスクインターフェース |
| TraceContext | `clients/types/workflow_generator.py` | Langfuseトレースコンテキスト |
| GenerationOptions | `clients/types/workflow_generator.py` | 生成オプション |
| BatchWorkflowGenerationResponse | `clients/types/workflow_generator.py` | バッチ生成レスポンス |
| FailedTask | `clients/types/workflow_generator.py` | 失敗タスク情報 |
| WorkflowResult | `clients/types/workflow_generator.py` | ワークフロー結果 |

### 3. WorkflowGeneratorClient本体 (T1.3)

| メソッド | ファイル | 説明 |
|---------|---------|------|
| generate_workflows | `clients/workflow_generator_client.py` | バッチワークフロー生成API呼び出し |
| _build_request_body | `clients/workflow_generator_client.py` | リクエストボディ構築 |
| _make_request | `clients/workflow_generator_client.py` | HTTP POSTリクエスト実行 |
| _parse_response | `clients/workflow_generator_client.py` | レスポンスパース |
| __aenter__ / __aexit__ | `clients/workflow_generator_client.py` | async context manager |

**特徴**:
- Protocol-based DI for testability
- Circuit Breaker for fault tolerance
- tenacity retry with exponential backoff
- Metrics collection via pluggable interface
- X-Trace-Id, X-Parent-Span-Id header propagation

### 4. Orchestrator統合 (T1.4)

| メソッド | ファイル | 変更内容 |
|---------|---------|---------|
| __init__ | `orchestrator.py` | workflow_generator_client, myswiftagent_core_url パラメータ追加 |
| _execute_workflow_gen | `orchestrator.py` | WorkflowGeneratorClientを使用してmySwiftAgentCore APIを呼び出し |
| _convert_to_parallel_result | `orchestrator.py` | BatchWorkflowGenerationResponseをParallelExecutionResultに変換 |
| _NoOpContextManager | `orchestrator.py` | 注入されたクライアント用のno-op context manager |

### 5. 単体テスト (T1.6)

| テストクラス | ファイル | テスト数 |
|------------|---------|---------|
| TestIHttpClient | `test_workflow_generator_client.py` | 3 |
| TestHttpxClientAdapter | `test_workflow_generator_client.py` | 4 |
| TestCircuitBreaker | `test_workflow_generator_client.py` | 10 |
| TestBatchStatus | `test_workflow_generator_client.py` | 5 |
| TestWorkflowStatus | `test_workflow_generator_client.py` | 3 |
| TestBatchWorkflowGenerationResponse | `test_workflow_generator_client.py` | 5 |
| TestWorkflowGeneratorClient | `test_workflow_generator_client.py` | 15 |
| TestWorkflowGeneratorClientBuildRequest | `test_workflow_generator_client.py` | 7 |

**合計**: 52テスト

## 未実装/保留タスク

| タスクID | 説明 | 理由 |
|---------|------|------|
| T1.5 | Langfuseトレース伝播 | E2Eテストで検証 |
| T2.1 | types_old.py依存解消 | 受入テスト後に実施 |
| T2.2 | workflow_gen削除 | 受入テスト後に実施 |
| T2.3 | 旧ファイル削除 | 受入テスト後に実施 |
| T2.4 | v3エイリアス削除 | 受入テスト後に実施 |
| T2.5 | テストコード整理 | 旧コード削除後に実施 |

## APIエンドポイント

**呼び出し先**: `POST /api/v1/generator/workflow/batch`

**リクエスト例**:
```json
{
  "tasks": [
    {
      "task_id": "task_001",
      "name": "Task task_001",
      "description": "Workflow for task task_001",
      "interface": {
        "input": { "type": "object" },
        "output": { "type": "object" }
      }
    }
  ],
  "capabilities": [],
  "project_id": "default_project"
}
```

**レスポンス例**:
```json
{
  "batch_id": "batch_xxx",
  "status": "success",
  "workflows": {
    "task_001": {
      "workflow_name": "workflow_task_001",
      "status": "success"
    }
  },
  "failed_tasks": [],
  "recovery_suggestion": null
}
```

## ヘッダー伝播

| ヘッダー | 用途 |
|---------|------|
| X-Trace-Id | Langfuseトレース追跡 |
| X-Parent-Span-Id | 親スパンID |

## 次のステップ

1. 受入テスト実行 (mySwiftAgentCore起動状態で)
2. Langfuseトレース伝播のE2E検証
3. types_old.py依存解消
4. 旧コード削除

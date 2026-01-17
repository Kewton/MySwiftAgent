# 受入テスト計画書

**Issue**: #364 - feat(mySwiftAgentCore): taskflowGeneratorAgent - ワークフロー生成エージェントの実装
**作成日**: 2026-01-16
**作成者**: acceptance-plan-agent
**ステータス**: 初版

---

## 1. 概要

### 対象Issue
- **番号**: #364
- **タイトル**: feat(mySwiftAgentCore): taskflowGeneratorAgent - ワークフロー生成エージェントの実装
- **プロジェクト**: mySwiftAgentCore
- **サイズ**: L（大規模）

### 参照ドキュメント
- Issue: [#364](https://github.com/Kewton/mySwiftAgent/issues/364)
- 設計方針書: `dev-reports/feature/issue/364/design-policy.md`
- 作業計画書: `dev-reports/feature/issue/364/work-plan.md`
- OpenAPI仕様: `docs/spec/api/taskflow-generator-api.yaml`

### 関連Issue
- Issue #363: TaskFlow Engine実装（依存 - 完了済み）
- Issue #365: Capability Management実装（依存 - 未着手）
- Issue #359: 3フェーズ統一ID方式（設計参照元）

---

## 2. 単体テスト結果レビュー

> **Note**: TDD実装前のため、以下は計画段階の目標値です。

### カバレッジ目標
- 目標: 90%以上
- 判定基準: `npm run test:coverage` 実行結果

### テスト品質評価（計画）

| 指標 | 目標 | 備考 |
|------|------|------|
| 総テスト数 | 100+ | 各コンポーネントに10-15テスト |
| モック使用テスト数 | 適切な範囲 | 外部APIのみモック |
| 実API呼び出しテスト数 | 0（単体テストでは） | 受入テストで検証 |

### モック使用の妥当性基準
- ✅ 許可: LLM API呼び出し（Anthropic/OpenAI/Gemini）
- ✅ 許可: taskflowEngine API呼び出し
- ✅ 許可: MyVault API呼び出し
- ✅ 許可: Langfuse API呼び出し
- ❌ 禁止: 内部ロジック（バリデーション、プロンプト構築等）

### 単体テストでカバーすべき項目
1. LLMClient - 各プロバイダーの応答処理
2. PromptBuilder - プロンプト構築ロジック
3. WorkflowGenerator - 生成ロジック
4. BatchProcessor - 並列実行制御
5. ValidationPipeline - 各Validator
6. ErrorHandler - リカバリー戦略判定
7. LangfuseIntegration - トレース記録
8. WorkflowRegistrar - 登録ロジック

---

## 3. 受入条件分析

### AC-1: ワークフロー生成
- **原文**: タスク定義、capabilities、interfacesを入力としてTaskFlow JSONを生成できる
- **分類**: 機能要件
- **テスト方法**: curl / pytest
- **モック使用**: 不可（実LLM呼び出し）
- **検証ポイント**:
  1. 入力として task_id, task_master_id, name, description, dependencies, interface を受け取れる
  2. capabilities を入力として受け取り、プロンプトに反映される
  3. graphAiServer互換のTaskFlow JSON形式で出力される
  4. workflow_name, steps, input_schema, output_schema が含まれる

### AC-2: バッチ生成API
- **原文**: 複数タスクの並列生成（max_concurrency制御）、`POST /api/v1/generator/workflow/batch` エンドポイント
- **分類**: 機能要件
- **テスト方法**: curl / pytest
- **モック使用**: 不可
- **検証ポイント**:
  1. `POST /api/v1/generator/workflow/batch` が存在する
  2. 複数タスク（3+）を同時に送信できる
  3. max_concurrency で並列度を制御できる
  4. タスクごとの成功/失敗が workflows と failed_tasks に分けて返される

### AC-3: リカバリー戦略
- **原文**: RETRY_CURRENT, ROLLBACK_TO_ANALYSIS, FAIL_FAST の3種類のリカバリー戦略
- **分類**: 機能要件
- **テスト方法**: pytest（エラー注入）
- **モック使用**: 一部可（エラー発生のため）
- **検証ポイント**:
  1. RETRY_CURRENT: 一時的エラー時に最大3回リトライ
  2. ROLLBACK_TO_ANALYSIS: capability不足時に recovery_suggestion を返却
  3. FAIL_FAST: 致命的エラー時に即座に失敗レスポンス
  4. recovery_suggestion がOpenAPI仕様のRecoveryStrategy enumに準拠

### AC-4: Langfuseトレース
- **原文**: expertAgentからtrace_contextを引き継ぎ、WORKFLOW_GENスパン作成、LLM Generation記録
- **分類**: 非機能要件（観測可能性）
- **テスト方法**: curl + Langfuseダッシュボード確認
- **モック使用**: 不可（実Langfuse接続）
- **検証ポイント**:
  1. trace_context を含むリクエストで既存トレースを継続できる
  2. WORKFLOW_GEN スパンが作成される
  3. 各タスクのスパン（task_{task_id}）が作成される
  4. LLM呼び出しがGenerationとして記録される
  5. token使用量（input_tokens, output_tokens）が記録される
  6. latency_ms が記録される
  7. レスポンスに trace_url が含まれる

### AC-5: バリデーション
- **原文**: 生成されたTaskFlow JSONのスキーマ検証、依存関係チェック、変数参照検出
- **分類**: 機能要件
- **テスト方法**: pytest（不正入力テスト）
- **モック使用**: 可（LLMを経由せず直接検証）
- **検証ポイント**:
  1. SchemaValidator: Zodスキーマ違反を検出
  2. DependencyValidator: 存在しないステップへの依存を検出
  3. VariableValidator: 無効な変数参照（$steps.xxx.yyy）を検出
  4. CapabilityValidator: 存在しないcapabilityの参照を検出
  5. SecurityValidator: セキュリティ上問題のあるパターンを検出
  6. validation_result に errors と warnings が含まれる

### AC-6: taskflowEngine統合
- **原文**: 生成したワークフローをtaskflowEngineに登録、WorkflowRegistryへの保存
- **分類**: 機能要件
- **テスト方法**: curl + ファイル確認
- **モック使用**: 不可（実taskflowEngine呼び出し）
- **検証ポイント**:
  1. 生成されたワークフローが WorkflowRegistry に登録される
  2. registered: true がレスポンスに含まれる
  3. workflow_id がレスポンスに含まれる
  4. 登録されたワークフローが実行可能である

### AC-7: TypeScript SDK
- **原文**: TaskFlowGeneratorClient クラスの提供、expertAgentからの呼び出しインターフェース
- **分類**: 機能要件
- **テスト方法**: TypeScript単体テスト + 結合テスト
- **モック使用**: 可（APIサーバーモック）
- **検証ポイント**:
  1. TaskFlowGeneratorClient クラスが存在する
  2. generateBatch メソッドが存在する
  3. 型定義がOpenAPI仕様に準拠している
  4. エラーハンドリングが適切に実装されている

---

## 4. 設計方針検証

### DP-1: サービス境界の明確化
- **設計方針**: expertAgentとmySwiftAgentCore間をHTTP APIで完全分離
- **検証方法**: curl / pytest
- **テスト項目**:
  1. APIエンドポイントがOpenAPI仕様に準拠している
  2. リクエスト/レスポンス形式が仕様通りである
  3. Authorization ヘッダーでの認証が動作する

### DP-2: LLMクライアント抽象化
- **設計方針**: プロバイダー非依存のLLMClientインターフェース
- **検証方法**: 単体テスト + 手動確認
- **テスト項目**:
  1. AnthropicClient でワークフロー生成ができる
  2. OpenAIClient でワークフロー生成ができる
  3. GeminiClient でワークフロー生成ができる
  4. LLMClientFactory がMyVault経由でAPIキーを取得する

### DP-3: Capabilityコンテキスト統合
- **設計方針**: Capabilityをプロンプトに構造化して注入
- **検証方法**: LLMプロンプト確認 + 生成結果確認
- **テスト項目**:
  1. capabilities がシステムプロンプトに含まれる
  2. category 別に整理されている
  3. 生成されたワークフローが capabilities を適切に参照する

### DP-4: 並列実行アーキテクチャ
- **設計方針**: Promise.allSettledによる並列処理とp-limit統合
- **検証方法**: パフォーマンステスト
- **テスト項目**:
  1. max_concurrency=3 で3タスクが同時実行される
  2. 一部失敗しても他タスクは継続される
  3. timeout_per_task_ms でタイムアウトが動作する

### DP-5: Langfuseトレース統合設計
- **設計方針**: expertAgentからのトレースコンテキスト継続
- **検証方法**: Langfuseダッシュボード確認
- **テスト項目**:
  1. trace_id を指定するとトレースが継続される
  2. parent_span_id を指定するとスパン階層が正しい
  3. user_id, session_id がトレースに記録される

### DP-6: エラーハンドリングとリカバリー
- **設計方針**: 構造化されたエラーレスポンスとリカバリー提案
- **検証方法**: エラー注入テスト
- **テスト項目**:
  1. error_type がErrorType enumに準拠している
  2. recovery_suggestion がRecoveryStrategy enumに準拠している
  3. recoverable フラグが適切に設定されている

### DP-7: TaskFlow検証パイプライン
- **設計方針**: 多段階検証によるワークフロー品質保証
- **検証方法**: 不正入力テスト
- **テスト項目**:
  1. 5種類のValidatorが順次実行される
  2. 全Validatorの結果が集約される
  3. isValid が errors.length === 0 と一致する

### DP-8: TaskFlow形式の互換性維持
- **設計方針**: graphAiServer形式への準拠とIssue #363との整合性
- **検証方法**: 生成結果の実行テスト
- **テスト項目**:
  1. 生成されたTaskFlowがgraphAiServerで実行可能
  2. TaskFlowDefinitionAdapterを使用して変換される
  3. WorkflowRegistry に正しく登録される

---

## 5. デッドコード検証計画

> **Note**: TDD実装後に具体的なファイルパスを更新します。

### F-1: WorkflowGenerator
- **ファイル**: `src/taskflowGeneratorAgent/generator/WorkflowGenerator.ts`
- **種別**: class
- **期待される呼び出し元**: handlers.ts, index.ts
- **検証方法**:
  ```bash
  grep -rn "WorkflowGenerator" --include="*.ts" src/taskflowGeneratorAgent/
  ```
- **E2E確認**: POST /api/v1/generator/workflow/batch が WorkflowGenerator を使用

### F-2: LLMClient implementations
- **ファイル**: `src/taskflowGeneratorAgent/llm/clients/*.ts`
- **種別**: class (AnthropicClient, OpenAIClient, GeminiClient)
- **期待される呼び出し元**: LLMClientFactory
- **検証方法**:
  ```bash
  grep -rn "AnthropicClient\|OpenAIClient\|GeminiClient" --include="*.ts" src/
  ```
- **E2E確認**: 各プロバイダーでワークフロー生成APIを呼び出し

### F-3: ValidationPipeline
- **ファイル**: `src/taskflowGeneratorAgent/validator/ValidationPipeline.ts`
- **種別**: class
- **期待される呼び出し元**: WorkflowGenerator
- **検証方法**:
  ```bash
  grep -rn "ValidationPipeline\|TaskFlowValidator" --include="*.ts" src/
  ```
- **E2E確認**: 不正なワークフローを生成させてバリデーションエラーを確認

### F-4: LangfuseIntegration
- **ファイル**: `src/taskflowGeneratorAgent/tracing/LangfuseIntegration.ts`
- **種別**: class
- **期待される呼び出し元**: WorkflowGenerator, handlers.ts
- **検証方法**:
  ```bash
  grep -rn "LangfuseIntegration" --include="*.ts" src/
  ```
- **E2E確認**: trace_context付きリクエストでトレースが記録される

### F-5: TaskFlowGeneratorClient (SDK)
- **ファイル**: `src/taskflowGeneratorAgent/client/TaskFlowGeneratorClient.ts`
- **種別**: class
- **期待される呼び出し元**: expertAgent（外部）
- **検証方法**:
  ```bash
  # TypeScriptからimportできることを確認
  grep -rn "TaskFlowGeneratorClient" --include="*.ts"
  ```
- **E2E確認**: SDKを使用してAPIを呼び出し

---

## 6. コンポーネント間整合性検証

### CI-1: RecoveryStrategy整合性
- **検証対象**: OpenAPI仕様とTypeScript実装の整合性
- **検証方法**:
  ```bash
  # OpenAPI定義
  grep -A 10 "RecoveryStrategy:" docs/spec/api/taskflow-generator-api.yaml

  # TypeScript実装
  grep -A 10 "enum RecoveryStrategy" src/taskflowGeneratorAgent/**/*.ts
  ```
- **確認項目**:
  - [ ] enum値が完全に一致している
  - [ ] RETRY_CURRENT, RETRY_WITH_FEEDBACK, ROLLBACK_TO_ANALYSIS, UPDATE_CAPABILITIES, MANUAL_INTERVENTION

### CI-2: ErrorType整合性
- **検証対象**: OpenAPI仕様とTypeScript実装の整合性
- **検証方法**:
  ```bash
  grep -A 10 "ErrorType:" docs/spec/api/taskflow-generator-api.yaml
  grep -A 10 "enum ErrorType" src/taskflowGeneratorAgent/**/*.ts
  ```
- **確認項目**:
  - [ ] enum値が完全に一致している

### CI-3: TaskFlowDefinition形式整合性
- **検証対象**: taskflowEngine (#363) と taskflowGeneratorAgent (#364)
- **検証方法**:
  ```bash
  # taskflowEngine の型定義
  cat src/taskflowEngine/types/TaskFlowDefinition.ts

  # taskflowGeneratorAgent の型定義
  cat src/taskflowGeneratorAgent/types/generator.ts
  ```
- **確認項目**:
  - [ ] workflow_name, steps, input_schema, output_schema が一致
  - [ ] TaskFlowDefinitionAdapter で相互変換可能

---

## 7. テスト環境

### 必須サービス

| サービス | URL | ヘルスチェック | 必須 |
|---------|-----|--------------|------|
| mySwiftAgentCore | http://localhost:8006 | GET /api/v1/generator/health | ✅ |
| taskflowEngine | http://localhost:8006 | GET /api/v1/taskflow/health | ✅ |
| MyVault | http://localhost:8103 | GET /health | ✅ |
| Langfuse | http://localhost:3001 | GET /api/public/health | ✅ |

### 起動コマンド

```bash
# 開発環境起動
cd mySwiftAgentCore && npm run dev

# またはDocker環境
make dev-all
```

### 環境変数

| 変数名 | 説明 | 取得元 | 必須 |
|--------|------|--------|------|
| ANTHROPIC_API_KEY | Anthropic APIキー | MyVault | ✅ |
| OPENAI_API_KEY | OpenAI APIキー | MyVault | ✅ |
| GEMINI_API_KEY | Gemini APIキー | MyVault | ✅ |
| LANGFUSE_PUBLIC_KEY | Langfuse公開キー | MyVault | ✅ |
| LANGFUSE_SECRET_KEY | Langfuse秘密キー | MyVault | ✅ |
| MYVAULT_API_TOKEN | MyVault APIトークン | 環境変数 | ✅ |

### テストデータ

**サンプルタスク定義**:
```json
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
```

**サンプルCapability**:
```json
{
  "id": "user_api",
  "name": "User API",
  "description": "ユーザー情報取得API",
  "category": "api",
  "status": "available",
  "parameters": [
    { "name": "user_id", "type": "string", "required": true }
  ]
}
```

---

## 8. テスト項目

### TC-001: ヘルスチェック
- **テスト観点**: APIサーバーが正常に起動している
- **関連する受入条件**: -
- **関連する設計方針**: DP-1
- **テスト種別**: E2E
- **テスト方法**: curl
- **前提条件**:
  1. mySwiftAgentCoreが起動済み
- **テスト手順**:
  1. GET /api/v1/generator/health を呼び出す
- **期待結果**:
  - HTTPステータス: 200
  - レスポンス: `{"status": "healthy"}`
- **curlコマンド**:
  ```bash
  curl -sf http://localhost:8006/api/v1/generator/health && echo "✅ Generator healthy"
  ```
- **pytestメソッド**: `test_tc_001_health_check`

### TC-002: 単一ワークフロー生成
- **テスト観点**: 単一タスクからTaskFlow JSONを生成できる
- **関連する受入条件**: AC-1, AC-2
- **関連する設計方針**: DP-1, DP-2, DP-3
- **テスト種別**: E2E
- **テスト方法**: curl
- **前提条件**:
  1. 全サービス起動済み
  2. MyVaultにAPIキーが設定済み
- **テスト手順**:
  1. POST /api/v1/generator/workflow/batch を1タスクで呼び出す
  2. レスポンスを確認
- **期待結果**:
  - HTTPステータス: 200
  - success: true
  - workflows.task_001 が存在する
  - workflows.task_001.workflow_name が存在する
  - workflows.task_001.registered: true
- **curlコマンド**:
  ```bash
  curl -s -X POST http://localhost:8006/api/v1/generator/workflow/batch \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${API_TOKEN}" \
    -d '{
      "tasks": [{
        "task_id": "task_001",
        "task_master_id": "tm_001",
        "name": "ユーザー分析レポート生成",
        "description": "指定されたユーザーの行動分析レポートを生成",
        "dependencies": [],
        "interface": {
          "input": { "user_id": "string" },
          "output": { "report": "string", "score": "number" }
        }
      }],
      "capabilities": [{
        "id": "user_api",
        "name": "User API",
        "category": "api",
        "status": "available"
      }],
      "project_id": "test_project",
      "options": {
        "max_concurrency": 1,
        "validate_before_register": true
      }
    }' | jq '.'
  ```
- **pytestメソッド**: `test_tc_002_single_workflow_generation`

### TC-003: バッチワークフロー生成（並列実行）
- **テスト観点**: 複数タスクを並列で生成できる
- **関連する受入条件**: AC-2
- **関連する設計方針**: DP-4
- **テスト種別**: E2E
- **テスト方法**: curl
- **前提条件**:
  1. 全サービス起動済み
- **テスト手順**:
  1. POST /api/v1/generator/workflow/batch を5タスクで呼び出す
  2. max_concurrency: 3 を設定
  3. レスポンスを確認
- **期待結果**:
  - HTTPステータス: 200 または 207
  - workflows に5つのエントリ（部分失敗の場合は成功分）
  - 処理時間が順次実行より短い
- **curlコマンド**:
  ```bash
  curl -s -X POST http://localhost:8006/api/v1/generator/workflow/batch \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${API_TOKEN}" \
    -d '{
      "tasks": [
        {"task_id": "task_001", "task_master_id": "tm_001", "name": "Task 1", "description": "Task 1 desc", "dependencies": [], "interface": {"input": {}, "output": {}}},
        {"task_id": "task_002", "task_master_id": "tm_002", "name": "Task 2", "description": "Task 2 desc", "dependencies": [], "interface": {"input": {}, "output": {}}},
        {"task_id": "task_003", "task_master_id": "tm_003", "name": "Task 3", "description": "Task 3 desc", "dependencies": [], "interface": {"input": {}, "output": {}}},
        {"task_id": "task_004", "task_master_id": "tm_004", "name": "Task 4", "description": "Task 4 desc", "dependencies": [], "interface": {"input": {}, "output": {}}},
        {"task_id": "task_005", "task_master_id": "tm_005", "name": "Task 5", "description": "Task 5 desc", "dependencies": [], "interface": {"input": {}, "output": {}}}
      ],
      "capabilities": [],
      "project_id": "test_project",
      "options": {
        "max_concurrency": 3,
        "timeout_per_task_ms": 30000
      }
    }' | jq '.workflows | length'
  ```
- **pytestメソッド**: `test_tc_003_batch_workflow_generation`

### TC-004: Langfuseトレース引き継ぎ
- **テスト観点**: expertAgentからのtrace_contextを引き継げる
- **関連する受入条件**: AC-4
- **関連する設計方針**: DP-5
- **テスト種別**: E2E
- **テスト方法**: curl + Langfuseダッシュボード
- **前提条件**:
  1. 全サービス起動済み
  2. Langfuseが起動済み
- **テスト手順**:
  1. trace_context付きでAPIを呼び出す
  2. レスポンスのtrace_urlを確認
  3. Langfuseダッシュボードでトレースを確認
- **期待結果**:
  - trace_url がレスポンスに含まれる
  - WORKFLOW_GEN スパンが記録される
  - Generation（LLM呼び出し）が記録される
- **curlコマンド**:
  ```bash
  curl -s -X POST http://localhost:8006/api/v1/generator/workflow/batch \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${API_TOKEN}" \
    -d '{
      "tasks": [{"task_id": "task_001", "task_master_id": "tm_001", "name": "Test Task", "description": "Test", "dependencies": [], "interface": {"input": {}, "output": {}}}],
      "capabilities": [],
      "project_id": "test_project",
      "trace_context": {
        "trace_id": "test_trace_001",
        "parent_span_id": "parent_span_001",
        "user_id": "test_user",
        "session_id": "test_session"
      }
    }' | jq '.trace_url'
  ```
- **pytestメソッド**: `test_tc_004_langfuse_trace_continuation`

### TC-005: バリデーションエラー検出
- **テスト観点**: 不正なタスク定義でバリデーションエラーが返る
- **関連する受入条件**: AC-5
- **関連する設計方針**: DP-7
- **テスト種別**: E2E
- **テスト方法**: curl
- **前提条件**:
  1. 全サービス起動済み
- **テスト手順**:
  1. 空のname、存在しないdependenciesを持つタスクを送信
  2. エラーレスポンスを確認
- **期待結果**:
  - HTTPステータス: 400
  - error_type が含まれる
  - message にエラー詳細が含まれる
- **curlコマンド**:
  ```bash
  curl -s -X POST http://localhost:8006/api/v1/generator/workflow/batch \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${API_TOKEN}" \
    -d '{
      "tasks": [{
        "task_id": "invalid_task",
        "task_master_id": "",
        "name": "",
        "description": "",
        "dependencies": ["non_existent_task"],
        "interface": {}
      }],
      "capabilities": [],
      "project_id": "test_project"
    }' -w '\nHTTP_STATUS:%{http_code}'
  ```
- **pytestメソッド**: `test_tc_005_validation_error`

### TC-006: リカバリー戦略（RETRY_CURRENT）
- **テスト観点**: 一時的エラー時にRETRY_CURRENTが返る
- **関連する受入条件**: AC-3
- **関連する設計方針**: DP-6
- **テスト種別**: E2E（エラー注入）
- **テスト方法**: pytest（モックでレート制限をシミュレート）
- **前提条件**:
  1. 全サービス起動済み
- **テスト手順**:
  1. レート制限エラーを発生させる
  2. recovery_suggestionを確認
- **期待結果**:
  - failed_tasks にエラーが含まれる
  - recovery_suggestion: "RETRY_CURRENT"
  - recoverable: true
- **pytestメソッド**: `test_tc_006_recovery_retry_current`

### TC-007: リカバリー戦略（ROLLBACK_TO_ANALYSIS）
- **テスト観点**: capability不足時にROLLBACK_TO_ANALYSISが返る
- **関連する受入条件**: AC-3
- **関連する設計方針**: DP-6
- **テスト種別**: E2E
- **テスト方法**: pytest
- **前提条件**:
  1. 全サービス起動済み
- **テスト手順**:
  1. 存在しないcapabilityを参照するタスクを送信
  2. recovery_suggestionを確認
- **期待結果**:
  - error_type: "CAPABILITY_NOT_FOUND"
  - recovery_suggestion: "ROLLBACK_TO_ANALYSIS"
- **pytestメソッド**: `test_tc_007_recovery_rollback_to_analysis`

### TC-008: taskflowEngine登録確認
- **テスト観点**: 生成されたワークフローがtaskflowEngineに登録される
- **関連する受入条件**: AC-6
- **関連する設計方針**: DP-8
- **テスト種別**: E2E
- **テスト方法**: curl
- **前提条件**:
  1. 全サービス起動済み
- **テスト手順**:
  1. ワークフローを生成
  2. workflow_idを取得
  3. taskflowEngine APIで登録を確認
- **期待結果**:
  - registered: true
  - workflow_id が返される
  - taskflowEngineにワークフローが存在する
- **curlコマンド**:
  ```bash
  # ワークフロー生成
  RESPONSE=$(curl -s -X POST http://localhost:8006/api/v1/generator/workflow/batch \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${API_TOKEN}" \
    -d '{
      "tasks": [{"task_id": "task_reg_001", "task_master_id": "tm_reg_001", "name": "Registration Test", "description": "Test registration", "dependencies": [], "interface": {"input": {}, "output": {}}}],
      "capabilities": [],
      "project_id": "test_project",
      "options": {"validate_before_register": true}
    }')

  WORKFLOW_ID=$(echo $RESPONSE | jq -r '.workflows.task_reg_001.workflow_id')

  # 登録確認
  curl -sf http://localhost:8006/api/v1/taskflow/workflows/${WORKFLOW_ID}
  ```
- **pytestメソッド**: `test_tc_008_taskflow_engine_registration`

### TC-009: LLMプロバイダー切り替え（Anthropic）
- **テスト観点**: AnthropicClientでワークフロー生成ができる
- **関連する受入条件**: AC-1
- **関連する設計方針**: DP-2
- **テスト種別**: E2E
- **テスト方法**: curl
- **前提条件**:
  1. MyVaultにAnthropic APIキーが設定済み
- **テスト手順**:
  1. model指定でAPIを呼び出す（claude-*）
  2. 生成結果を確認
- **期待結果**:
  - 正常にワークフローが生成される
  - Langfuseでモデル名が記録される
- **pytestメソッド**: `test_tc_009_anthropic_provider`

### TC-010: LLMプロバイダー切り替え（OpenAI）
- **テスト観点**: OpenAIClientでワークフロー生成ができる
- **関連する受入条件**: AC-1
- **関連する設計方針**: DP-2
- **テスト種別**: E2E
- **テスト方法**: curl
- **前提条件**:
  1. MyVaultにOpenAI APIキーが設定済み
- **テスト手順**:
  1. model指定でAPIを呼び出す（gpt-*）
  2. 生成結果を確認
- **期待結果**:
  - 正常にワークフローが生成される
- **pytestメソッド**: `test_tc_010_openai_provider`

### TC-011: ステータス確認API
- **テスト観点**: 生成状態を確認できる
- **関連する受入条件**: AC-2
- **関連する設計方針**: DP-1
- **テスト種別**: E2E
- **テスト方法**: curl
- **前提条件**:
  1. 全サービス起動済み
- **テスト手順**:
  1. ワークフロー生成を実行
  2. GET /api/v1/generator/status/{trace_id} を呼び出す
- **期待結果**:
  - status が返される（pending/in_progress/completed/failed）
  - total_tasks, completed_tasks, failed_tasks が含まれる
- **curlコマンド**:
  ```bash
  curl -sf http://localhost:8006/api/v1/generator/status/test_trace_001
  ```
- **pytestメソッド**: `test_tc_011_status_api`

### TC-012: TypeScript SDK動作確認
- **テスト観点**: TaskFlowGeneratorClientが動作する
- **関連する受入条件**: AC-7
- **関連する設計方針**: DP-1
- **テスト種別**: 結合テスト
- **テスト方法**: TypeScript テスト
- **前提条件**:
  1. 全サービス起動済み
- **テスト手順**:
  1. TaskFlowGeneratorClientをインスタンス化
  2. generateBatch を呼び出す
  3. 結果を確認
- **期待結果**:
  - 型安全にAPIを呼び出せる
  - エラーハンドリングが動作する
- **pytestメソッド**: `test_tc_012_typescript_sdk` (TypeScript jest)

---

## 9. E2E統合テスト計画

### E2E-1: フルフロー統合テスト
- **テストファイル**: `mySwiftAgentCore/tests/acceptance/test_issue_364_acceptance.py`
- **実行コマンド**:
  ```bash
  cd mySwiftAgentCore && npm run test:acceptance
  ```
- **検証項目**:
  - [ ] ヘルスチェックが成功する
  - [ ] 単一ワークフロー生成が成功する
  - [ ] バッチワークフロー生成が成功する
  - [ ] Langfuseトレースが記録される
  - [ ] taskflowEngineへの登録が成功する
  - [ ] バリデーションエラーが適切に返される
  - [ ] リカバリー戦略が正しく設定される

### E2E-2: expertAgent連携テスト
- **テストファイル**: `expertAgent/tests/integration/test_taskflow_generator_integration.py`
- **実行コマンド**:
  ```bash
  cd expertAgent && uv run pytest tests/integration/test_taskflow_generator_integration.py -v
  ```
- **検証項目**:
  - [ ] expertAgentからmySwiftAgentCoreへのAPI呼び出しが成功する
  - [ ] trace_contextが正しく引き継がれる
  - [ ] レスポンスの型がPython側で正しくパースされる

---

## 10. テスト実行計画

### 実行順序
1. サービス起動確認（ヘルスチェック）
2. 単体テスト実行（`npm run test`）
3. TypeScript受入テスト実行（`npm run test:acceptance`）
4. Python結合テスト実行（expertAgent連携）
5. 追加curlテスト実行

### 成功基準
- [ ] すべての単体テストがパス（カバレッジ90%以上）
- [ ] すべてのTC-001〜TC-012がパス
- [ ] E2E-1, E2E-2がパス
- [ ] すべての受入条件（AC-1〜AC-7）が検証済み
- [ ] すべての設計方針（DP-1〜DP-8）が検証済み
- [ ] デッドコードが検出されないこと
- [ ] コンポーネント間整合性が確認されること

---

## 11. 補足事項

### 注意事項
1. LLM APIの呼び出しはコストが発生するため、テスト実行回数に注意
2. Langfuseトレースの確認は手動で行う必要がある場合がある
3. Issue #365（Capability Management）が未実装の場合、capabilitiesのテストは限定的になる可能性がある

### 今後の拡張
1. パフォーマンステスト（負荷テスト）の追加
2. セキュリティテスト（認証バイパス、インジェクション）の追加
3. 障害注入テスト（カオスエンジニアリング）の追加

---

**作成者**: acceptance-plan-agent
**作成日**: 2026-01-16

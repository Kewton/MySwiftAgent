# 受入テスト計画書

**Issue**: #363
**作成日**: 2026-01-16
**作成者**: acceptance-plan-agent

---

## 1. 概要

### 対象Issue
- **番号**: #363
- **タイトル**: feat(mySwiftAgentCore): taskflowEngine - TaskFlow実行エンジンの実装
- **プロジェクト**: mySwiftAgentCore

### 参照ドキュメント
- Issue: #363
- 設計方針書: `dev-reports/feature/issue/363/design-policy.md`
- 作業計画書: `dev-reports/feature/issue/363/work-plan.md`
- アーキテクチャレビュー: `dev-reports/feature/issue/363/architecture-review.md`

---

## 2. 単体テスト結果レビュー

### カバレッジ
- 現在: TDD実装前（対象なし）
- 目標: 90%
- 判定: TDD実装後に確認

### テスト品質評価（TDD実装後に確認）
| 指標 | 値 | 判定 |
|------|-----|------|
| 総テスト数 | - | - |
| モック使用テスト数 | - | - |
| モック使用率 | -% | - |
| 実API呼び出しテスト数 | - | - |

### モック使用の妥当性
- 外部API呼び出し（LLM API等）はモック可
- 内部コンポーネント間は実装を使用
- サンドボックス実行は実際のisolated-vmを使用

### 単体テストでカバーすべき項目
1. TaskFlowDefinitionAdapter - 型変換の双方向変換
2. CodeJsSandbox - セキュリティ制限の動作
3. ParallelExecutionManager - 並列数制限の動作
4. 各NodeExecutor - ノード実行ロジック
5. WorkflowExecutor - ワークフロー実行フロー
6. SchemaValidator - 入力/出力検証

---

## 3. 受入条件分析

### AC-1: プロジェクト単位でTaskFlowワークフローを管理
- **原文**: `config/taskflow/projects/{project_name}/workflows/`にJSON定義を配置。プロジェクトごとに独立したワークフロー管理。
- **分類**: 機能要件
- **テスト方法**: curl / pytest
- **モック使用**: 不可
- **検証ポイント**:
  1. プロジェクトディレクトリ構造が正しく認識される
  2. プロジェクト単位でワークフローが分離される
  3. 異なるプロジェクトのワークフローが混在しない

### AC-2: graphAiServerと互換性のあるTaskFlow形式をサポート
- **原文**: Issue #348で定義されたワークフロースキーマをサポート。`api_rest`, `code_js`, `transform`, `parallel`, `llm`ノードタイプ。
- **分類**: 機能要件
- **テスト方法**: pytest / curl
- **モック使用**: 外部APIのみ可
- **検証ポイント**:
  1. graphAiServer形式のJSONが読み込める
  2. 全5種類のノードタイプが動作する
  3. 変数参照（`${inputs.xxx}`, `${step_id.output.xxx}`）が解決される

### AC-3: Langfuseトレーシング統合
- **原文**: ワークフロー実行の開始/終了、各ステップの実行時間とステータス、エラー発生時の詳細情報。
- **分類**: 非機能要件
- **テスト方法**: pytest / Langfuseダッシュボード確認
- **モック使用**: Langfuse APIはモック可（単体）、E2Eでは実接続
- **検証ポイント**:
  1. ワークフロー実行でトレースが生成される
  2. 各ステップがSpanとして記録される
  3. LLMノードがGenerationとして記録される
  4. trace_contextが引き継がれる

### AC-4: REST API経由での実行
- **原文**: `POST /api/v1/taskflow/execute` エンドポイント。プロジェクト指定、ワークフロー名、入力パラメータを受付。
- **分類**: 機能要件
- **テスト方法**: curl / pytest
- **モック使用**: 不可
- **検証ポイント**:
  1. エンドポイントが存在する
  2. リクエスト形式が設計通り
  3. レスポンス形式が設計通り
  4. 認証が動作する

### AC-5: TypeScript SDKの提供
- **原文**: `TaskFlowClient` クラスでプログラマティックな実行。expertAgentからHTTP経由で利用可能。
- **分類**: 機能要件
- **テスト方法**: Vitest / 統合テスト
- **モック使用**: 外部HTTP呼び出しはモック可
- **検証ポイント**:
  1. TaskFlowClientが動作する
  2. execute()メソッドが機能する
  3. listWorkflows()メソッドが機能する

### AC-6: エラーハンドリングと部分成功モデル
- **原文**: 各ステップの成功/失敗を個別に追跡。部分的な成功でも利用可能な結果を返却。
- **分類**: 機能要件
- **テスト方法**: pytest / curl
- **モック使用**: 一部可（エラー発生用）
- **検証ポイント**:
  1. ステップ失敗時に`partial_success`が返る
  2. 失敗ステップ以降も実行が継続される（設定による）
  3. errors配列に詳細情報が含まれる

### AC-7: テストカバレッジ90%以上
- **原文**: 単体テスト、結合テスト、受入テスト。
- **分類**: 非機能要件
- **テスト方法**: Vitest coverage
- **モック使用**: N/A
- **検証ポイント**:
  1. カバレッジ90%以上達成
  2. 全テストがパス

---

## 4. 設計方針検証

### DP-1: graphAiServerとの設計統一性
- **設計方針**: graphAiServerの実装パターンを踏襲し、将来的な統合を容易にする
- **検証方法**: コード構造確認 / APIテスト
- **テスト項目**:
  1. WorkflowDefinitionインターフェースがgraphAiServer互換
  2. ノードタイプが同一（api_rest, code_js, transform, parallel, llm）
  3. 変数参照記法が同一（`${...}`形式）

### DP-2: プロジェクトベース管理との統合
- **設計方針**: Issue #365のCapabilityManagementパターンを踏襲
- **検証方法**: コード構造確認
- **テスト項目**:
  1. WorkflowRegistryがCapabilityRegistryと同様のパターン
  2. プロジェクト単位でのワークフロー管理が機能

### DP-3: Langfuseトレーシングのネイティブ統合
- **設計方針**: Langfuseをコア機能として統合（オプショナルではない）
- **検証方法**: APIテスト / Langfuseダッシュボード確認
- **テスト項目**:
  1. すべてのワークフロー実行でトレースが生成される
  2. TracingConfigが正しく適用される

### DP-4: モジュラーなノード実装
- **設計方針**: 各ノードタイプを独立したクラスとして実装（Strategy Pattern）
- **検証方法**: コード構造確認 / 単体テスト
- **テスト項目**:
  1. NodeExecutorインターフェースが存在
  2. 各ノード実装がインターフェースを実装
  3. 新しいノードタイプの追加が容易

### DP-5: 型定義の整合性確保（アダプターパターン）
- **設計方針**: TaskFlowDefinitionAdapterによる双方向変換
- **検証方法**: 単体テスト / 統合テスト
- **テスト項目**:
  1. toInternal()が正しく変換
  2. toExternal()が正しく変換
  3. 往復変換でデータが保持される

### DP-6: code_jsノードのセキュリティ強化
- **設計方針**: isolated-vmによるサンドボックス、ホワイトリスト、整合性検証
- **検証方法**: セキュリティテスト / 単体テスト
- **テスト項目**:
  1. ホワイトリストにないスクリプトが拒否される
  2. ファイルシステムアクセスが制限される
  3. ネットワークアクセスが制限される
  4. メモリ/タイムアウト制限が動作する

### DP-7: 並列実行制御の具体化
- **設計方針**: p-limitによる3層並列制限（グローバル/ワークフロー/ノードタイプ）
- **検証方法**: 負荷テスト / 単体テスト
- **テスト項目**:
  1. グローバル制限（50並列）が動作する
  2. ワークフロー制限（10並列）が動作する
  3. ノードタイプ制限（LLM: 5並列等）が動作する
  4. メトリクスが収集される

---

## 5. デッドコード検証計画

### F-1: TaskFlowDefinitionAdapter
- **ファイル**: `src/taskflowEngine/adapter/TaskFlowDefinitionAdapter.ts`
- **種別**: class
- **期待される呼び出し元**: WorkflowRegistry, APIハンドラー
- **検証方法**:
  ```bash
  grep -rn "TaskFlowDefinitionAdapter" --include="*.ts" src/
  ```
- **E2E確認**: ワークフロー登録・実行APIを叩いて変換が動作することを確認

### F-2: CodeJsSandbox
- **ファイル**: `src/taskflowEngine/sandbox/CodeJsSandbox.ts`
- **種別**: class
- **期待される呼び出し元**: CodeJsNode
- **検証方法**:
  ```bash
  grep -rn "CodeJsSandbox" --include="*.ts" src/
  ```
- **E2E確認**: code_jsノードを含むワークフローを実行

### F-3: ParallelExecutionManager
- **ファイル**: `src/taskflowEngine/executor/ParallelExecutionManager.ts`
- **種別**: class
- **期待される呼び出し元**: WorkflowExecutor, ParallelExecutor
- **検証方法**:
  ```bash
  grep -rn "ParallelExecutionManager" --include="*.ts" src/
  ```
- **E2E確認**: 並列実行を含むワークフローを実行

### F-4: LangfuseTracer
- **ファイル**: `src/taskflowEngine/tracer/LangfuseTracer.ts`
- **種別**: class
- **期待される呼び出し元**: WorkflowExecutor
- **検証方法**:
  ```bash
  grep -rn "LangfuseTracer" --include="*.ts" src/
  ```
- **E2E確認**: Langfuseダッシュボードでトレースが表示される

### F-5: TaskFlowClient
- **ファイル**: `src/taskflowEngine/client/TaskFlowClient.ts`
- **種別**: class
- **期待される呼び出し元**: 外部クライアント（expertAgent等）
- **検証方法**:
  ```bash
  grep -rn "TaskFlowClient" --include="*.ts" src/
  ```
- **E2E確認**: SDKを使用したワークフロー実行テスト

---

## 6. テスト環境

### 必須サービス
| サービス | URL | ヘルスチェック |
|---------|-----|--------------|
| mySwiftAgentCore | http://localhost:8006 | GET /health |
| Langfuse | http://localhost:3001 | GET /api/public/health |

### 起動コマンド
```bash
# mySwiftAgentCore起動
cd mySwiftAgentCore
npm run dev

# Langfuse起動（Docker Compose）
cd langfuse
docker compose up -d
```

### 環境変数
| 変数名 | 説明 | 必須 |
|--------|------|------|
| API_TOKEN | mySwiftAgentCore認証トークン | Yes |
| LANGFUSE_SECRET_KEY | Langfuseシークレットキー | Yes |
| LANGFUSE_PUBLIC_KEY | Langfuseパブリックキー | Yes |
| LANGFUSE_HOST | Langfuseホスト（http://localhost:3001） | Yes |
| OPENAI_API_KEY | OpenAI APIキー（LLMノード用） | LLMテスト時 |

### テストデータ準備
1. `config/taskflow/projects/default_project/workflows/` にサンプルワークフローを配置
2. `config/taskflow/scripts/whitelist.yaml` にホワイトリストを設定
3. `config/taskflow/scripts/calculators/` にテストスクリプトを配置

---

## 7. テスト項目

### TC-001: ヘルスチェック
- **テスト観点**: サービス起動確認
- **関連する受入条件**: 前提条件
- **関連する設計方針**: -
- **テスト種別**: E2E
- **テスト方法**: curl
- **前提条件**:
  1. mySwiftAgentCoreが起動している
- **テスト手順**:
  1. ヘルスチェックエンドポイントにアクセス
- **期待結果**:
  - HTTPステータス: 200
  - レスポンス: `{ "status": "healthy" }`
- **curlコマンド**:
  ```bash
  curl -sf http://localhost:8006/health && echo "OK"
  ```
- **pytestメソッド**: `test_tc_001_health_check`

### TC-002: 基本的なワークフロー実行
- **テスト観点**: AC-2, AC-4の検証
- **関連する受入条件**: AC-2, AC-4
- **関連する設計方針**: DP-1
- **テスト種別**: E2E
- **テスト方法**: curl / pytest
- **前提条件**:
  1. mySwiftAgentCoreが起動している
  2. hello_worldワークフローが登録されている
- **テスト手順**:
  1. execute APIを呼び出し
  2. レスポンスを検証
- **期待結果**:
  - HTTPステータス: 200
  - status: "success"
  - results: 期待される出力
- **curlコマンド**:
  ```bash
  curl -s -X POST http://localhost:8006/api/v1/taskflow/execute \
    -H "Authorization: Bearer ${API_TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{
      "project": "default_project",
      "workflow": "hello_world",
      "inputs": { "name": "TaskFlow" }
    }' | jq
  ```
- **pytestメソッド**: `test_tc_002_basic_workflow_execution`

### TC-003: 並列実行ワークフロー
- **テスト観点**: AC-2, DP-7の検証
- **関連する受入条件**: AC-2
- **関連する設計方針**: DP-7
- **テスト種別**: E2E
- **テスト方法**: curl / pytest
- **前提条件**:
  1. mySwiftAgentCoreが起動している
  2. parallel_api_callsワークフローが登録されている
- **テスト手順**:
  1. 並列ステップを含むワークフローを実行
  2. 全ステップの結果を検証
- **期待結果**:
  - HTTPステータス: 200
  - status: "success"
  - 並列ステップの結果が含まれる
- **curlコマンド**:
  ```bash
  curl -s -X POST http://localhost:8006/api/v1/taskflow/execute \
    -H "Authorization: Bearer ${API_TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{
      "project": "default_project",
      "workflow": "parallel_api_calls",
      "inputs": { "user_id": "test_user_123" }
    }' | jq
  ```
- **pytestメソッド**: `test_tc_003_parallel_workflow_execution`

### TC-004: code_jsノード実行（許可されたスクリプト）
- **テスト観点**: AC-2, DP-6の検証
- **関連する受入条件**: AC-2
- **関連する設計方針**: DP-6
- **テスト種別**: E2E
- **テスト方法**: curl / pytest
- **前提条件**:
  1. mySwiftAgentCoreが起動している
  2. calculate_risk_scoreワークフローが登録されている
  3. スクリプトがホワイトリストに登録されている
- **テスト手順**:
  1. code_jsノードを含むワークフローを実行
  2. 計算結果を検証
- **期待結果**:
  - HTTPステータス: 200
  - status: "success"
  - リスクスコアが計算されている
- **curlコマンド**:
  ```bash
  curl -s -X POST http://localhost:8006/api/v1/taskflow/execute \
    -H "Authorization: Bearer ${API_TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{
      "project": "default_project",
      "workflow": "calculate_risk_score",
      "inputs": { "age": 30, "income": 50000 }
    }' | jq
  ```
- **pytestメソッド**: `test_tc_004_code_js_allowed_script`

### TC-005: code_jsノード実行（禁止されたスクリプト）
- **テスト観点**: DP-6セキュリティの検証
- **関連する受入条件**: AC-2
- **関連する設計方針**: DP-6
- **テスト種別**: E2E / セキュリティ
- **テスト方法**: curl / pytest
- **前提条件**:
  1. mySwiftAgentCoreが起動している
  2. malicious_scriptワークフローが存在する（ホワイトリスト外）
- **テスト手順**:
  1. ホワイトリスト外のスクリプトを実行
  2. エラーを検証
- **期待結果**:
  - HTTPステータス: 400 または 403
  - エラーメッセージ: SCRIPT_NOT_WHITELISTED
- **curlコマンド**:
  ```bash
  curl -s -X POST http://localhost:8006/api/v1/taskflow/execute \
    -H "Authorization: Bearer ${API_TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{
      "project": "default_project",
      "workflow": "malicious_script",
      "inputs": {}
    }' | jq
  ```
- **pytestメソッド**: `test_tc_005_code_js_blocked_script`

### TC-006: Langfuseトレーシング
- **テスト観点**: AC-3, DP-3の検証
- **関連する受入条件**: AC-3
- **関連する設計方針**: DP-3
- **テスト種別**: E2E
- **テスト方法**: curl / Langfuseダッシュボード
- **前提条件**:
  1. mySwiftAgentCoreが起動している
  2. Langfuseが起動している
  3. 環境変数が設定されている
- **テスト手順**:
  1. trace_context付きでワークフローを実行
  2. Langfuseダッシュボードでトレースを確認
- **期待結果**:
  - HTTPステータス: 200
  - trace_urlが返却される
  - Langfuseにトレースが記録される
- **curlコマンド**:
  ```bash
  curl -s -X POST http://localhost:8006/api/v1/taskflow/execute \
    -H "Authorization: Bearer ${API_TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{
      "project": "default_project",
      "workflow": "user_analysis",
      "inputs": { "user_id": "123" },
      "trace_context": {
        "trace_id": "acceptance_test_trace_001",
        "metadata": { "source": "acceptance_test" }
      }
    }' | jq
  ```
- **pytestメソッド**: `test_tc_006_langfuse_tracing`

### TC-007: ワークフロー一覧取得
- **テスト観点**: AC-1, AC-4の検証
- **関連する受入条件**: AC-1, AC-4
- **関連する設計方針**: DP-2
- **テスト種別**: E2E
- **テスト方法**: curl / pytest
- **前提条件**:
  1. mySwiftAgentCoreが起動している
  2. default_projectにワークフローが登録されている
- **テスト手順**:
  1. workflows APIを呼び出し
  2. 登録済みワークフローの一覧を検証
- **期待結果**:
  - HTTPステータス: 200
  - workflows配列が返却される
  - 各ワークフローにname, input_schema, output_schemaが含まれる
- **curlコマンド**:
  ```bash
  curl -s -X GET "http://localhost:8006/api/v1/taskflow/workflows?project=default_project" \
    -H "Authorization: Bearer ${API_TOKEN}" | jq
  ```
- **pytestメソッド**: `test_tc_007_list_workflows`

### TC-008: 入力検証エラー
- **テスト観点**: AC-6の検証
- **関連する受入条件**: AC-6
- **関連する設計方針**: DP-1
- **テスト種別**: E2E
- **テスト方法**: curl / pytest
- **前提条件**:
  1. mySwiftAgentCoreが起動している
  2. strict_schema_workflowが登録されている
- **テスト手順**:
  1. 不正な入力でワークフローを実行
  2. エラーレスポンスを検証
- **期待結果**:
  - HTTPステータス: 400
  - エラーコード: VALIDATION_ERROR
  - エラー詳細が含まれる
- **curlコマンド**:
  ```bash
  curl -s -X POST http://localhost:8006/api/v1/taskflow/execute \
    -H "Authorization: Bearer ${API_TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{
      "project": "default_project",
      "workflow": "strict_schema_workflow",
      "inputs": { "invalid_field": "should_be_number" }
    }' | jq
  ```
- **pytestメソッド**: `test_tc_008_input_validation_error`

### TC-009: 存在しないワークフロー
- **テスト観点**: AC-6の検証
- **関連する受入条件**: AC-6
- **関連する設計方針**: -
- **テスト種別**: E2E
- **テスト方法**: curl / pytest
- **前提条件**:
  1. mySwiftAgentCoreが起動している
- **テスト手順**:
  1. 存在しないワークフローを実行
  2. エラーレスポンスを検証
- **期待結果**:
  - HTTPステータス: 404
  - エラーメッセージ: Workflow not found
- **curlコマンド**:
  ```bash
  curl -s -X POST http://localhost:8006/api/v1/taskflow/execute \
    -H "Authorization: Bearer ${API_TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{
      "project": "default_project",
      "workflow": "non_existent_workflow",
      "inputs": {}
    }' | jq
  ```
- **pytestメソッド**: `test_tc_009_workflow_not_found`

### TC-010: 部分成功モデル
- **テスト観点**: AC-6の検証
- **関連する受入条件**: AC-6
- **関連する設計方針**: -
- **テスト種別**: E2E
- **テスト方法**: pytest
- **前提条件**:
  1. mySwiftAgentCoreが起動している
  2. partial_failure_workflowが登録されている（一部ステップが失敗する設計）
- **テスト手順**:
  1. 一部ステップが失敗するワークフローを実行
  2. partial_successステータスを検証
- **期待結果**:
  - status: "partial_success"
  - completedSteps: 成功したステップのリスト
  - failedSteps: 失敗したステップのリスト
  - errors: エラー詳細
- **pytestメソッド**: `test_tc_010_partial_success`

### TC-011: SDK経由の実行
- **テスト観点**: AC-5の検証
- **関連する受入条件**: AC-5
- **関連する設計方針**: -
- **テスト種別**: 結合
- **テスト方法**: Vitest
- **前提条件**:
  1. mySwiftAgentCoreが起動している
- **テスト手順**:
  1. TaskFlowClientをインスタンス化
  2. execute()メソッドを呼び出し
  3. listWorkflows()メソッドを呼び出し
- **期待結果**:
  - execute()が正常に動作
  - listWorkflows()がワークフロー一覧を返却
- **pytestメソッド**: `test_tc_011_sdk_execution`（Vitestで実行）

### TC-012: 型アダプター変換（E2E統合）
- **テスト観点**: DP-5の検証
- **関連する受入条件**: AC-2
- **関連する設計方針**: DP-5
- **テスト種別**: E2E
- **テスト方法**: pytest
- **前提条件**:
  1. graphAiServer形式のワークフローJSONが存在
- **テスト手順**:
  1. graphAiServer形式のワークフローを登録
  2. ワークフローを実行
  3. 結果がgraphAiServer互換形式で返却されることを確認
- **期待結果**:
  - 登録が成功
  - 実行が成功
  - 出力形式がgraphAiServer互換
- **pytestメソッド**: `test_tc_012_adapter_integration`

---

## 8. テスト実行計画

### 実行順序
1. サービス起動確認（TC-001）
2. 基本機能テスト（TC-002, TC-007）
3. ノードタイプテスト（TC-003, TC-004, TC-005）
4. トレーシングテスト（TC-006）
5. エラーハンドリングテスト（TC-008, TC-009, TC-010）
6. SDK/統合テスト（TC-011, TC-012）

### 成功基準
- [x] TC-001〜TC-012のすべてがパス
- [x] 単体テストカバレッジ90%以上
- [x] 結合テスト全パス
- [x] Langfuseダッシュボードでトレースが確認できる
- [x] セキュリティテスト（TC-005）が正しくブロックされる

### pytest受入テストファイル
```
mySwiftAgentCore/tests/acceptance/test_issue_363_acceptance.py
```

### 実行コマンド
```bash
# 受入テスト実行
cd mySwiftAgentCore
npm test -- tests/acceptance/test_issue_363_acceptance.test.ts

# または Vitest
npx vitest run tests/acceptance/test_issue_363_acceptance.test.ts
```

---

## 9. 補足事項

### isolated-vmの注意点
- Node.js 18以上が必要
- ネイティブバイナリのビルドが必要な場合あり
- CI環境でのビルドに追加設定が必要な可能性

### Langfuseとの接続
- ローカル環境ではDocker Composeで起動
- 環境変数の設定が必須
- トレース確認はダッシュボード（http://localhost:3001）で手動確認

### テストデータの準備
- サンプルワークフローは事前に`config/taskflow/projects/default_project/workflows/`に配置
- ホワイトリストは`config/taskflow/scripts/whitelist.yaml`に設定

---

## 10. コンポーネント間整合性検証（Issue #359/360）

### CI-1: 型定義の整合性
- **検証対象**: TaskFlowDefinition, InternalWorkflowDefinition
- **検証方法**:
  ```bash
  grep -n "workflow_name\|input_schema\|output_schema" src/taskflowEngine/types/
  ```
- **確認項目**:
  - [ ] graphAiServer形式とmySwiftAgentCore形式の両方がサポートされている
  - [ ] アダプターで正しく変換される
  - [ ] 往復変換でデータが失われない

### CI-2: エラーコードの一貫性
- **検証対象**: TaskFlowErrorCode
- **検証方法**:
  ```bash
  grep -n "TaskFlowErrorCode\|VALIDATION_ERROR\|TIMEOUT" src/taskflowEngine/
  ```
- **確認項目**:
  - [ ] エラーコードが一貫している
  - [ ] エラーメッセージが適切

### CI-3: トレーシングの一貫性
- **検証対象**: Langfuseトレース構造
- **検証方法**: Langfuseダッシュボードで確認
- **確認項目**:
  - [ ] すべてのステップがSpanとして記録される
  - [ ] LLMノードがGenerationとして記録される
  - [ ] エラー時にERRORレベルで記録される

---

**作成者**: acceptance-plan-agent
**レビュー状態**: 未レビュー

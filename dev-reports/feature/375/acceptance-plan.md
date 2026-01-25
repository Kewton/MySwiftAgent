# 受入テスト計画書

**Issue**: #375
**作成日**: 2026-01-18
**作成者**: acceptance-plan-agent

---

## 1. 概要

### 対象Issue
- **番号**: #375
- **タイトル**: mySwiftAgentCore: ワークフロー生成・実行のバリデーション強化
- **プロジェクト**: mySwiftAgentCore

### 参照ドキュメント
- Issue: #375
- 設計方針書: `dev-reports/feature/issue/375/design-policy.md`
- 作業計画書: `dev-reports/feature/issue/375/work-plan.md`

### 背景
E2Eテスト（task_001, task_002, task_003）実行時に発見された複数の問題を解決し、ワークフロー生成・実行の信頼性を向上させる。

| # | 問題 | 現象 | 真因 |
|---|------|------|------|
| 1 | task_001のresultsが空 | ワークフロー実行成功だが`results: {}` | WorkflowRegistryにホットリロード機能がない |
| 2 | capability名不一致 | `Capability 'myllm' not found` | capability_id存在チェックがない |
| 3 | TransformNode設定エラー | `No template or mapping provided` | ノードタイプ仕様がLLMに提供されていない |
| 4 | 出力マッピング不一致 | `messageId` vs `message_id` | responseSchemaフィールド名の強制がない |

---

## 2. 単体テスト結果レビュー

### カバレッジ
- 現在: TDD結果未取得（単体テスト実装前）
- 目標: 90%
- 判定: 実装後に確認

### テスト品質評価（計画）
| 指標 | 期待値 | 判定基準 |
|------|--------|----------|
| 総テスト数 | 30+ | 各バリデータに10テスト以上 |
| モック使用テスト数 | 適切 | 外部API/LLM呼び出しのみ |
| モック使用率 | 30%以下 | バリデーションロジック自体はモック不要 |
| 実API呼び出しテスト数 | 5+ | E2E結合テスト |

### モック使用の妥当性（計画）
- 外部API呼び出し（Google Search API）: モック可
- LLM呼び出し（ワークフロー生成）: モック可
- CapabilityRegistry参照: 実オブジェクト使用必須
- ファイルシステム操作: 実操作推奨

### 単体テストでカバーすべき項目
1. CapabilityValidator: capability_id存在確認、エラーメッセージ生成
2. OutputMappingValidator: camelCase/snake_case検出、型不一致検出
3. NodeConfigValidator: TransformNode設定、api_rest設定
4. FileSystemWatcher: ファイル変更検知、デバウンス処理
5. WorkflowReloader: リロード処理、履歴管理

---

## 3. 受入条件分析

### AC-1: capability_id存在バリデーション
- **原文**:
  - ワークフロー生成後、全ステップのcapability_idがCapabilityRegistryに存在することを検証する
  - 存在しないcapability_idがある場合、フィードバックループで再生成する
  - エラーメッセージに利用可能なcapability一覧を含める
- **分類**: 機能要件
- **テスト方法**: pytest / curl
- **モック使用**: 不可（CapabilityRegistryは実オブジェクト必須）
- **検証ポイント**:
  1. 存在しないcapability_idでワークフロー生成を試行し、エラーが返る
  2. エラーメッセージに`UNKNOWN_CAPABILITY`エラーコードが含まれる
  3. エラーメッセージに利用可能なcapability一覧が含まれる
  4. フィードバックループで正しいcapability_idに修正される

### AC-2: 出力マッピングとresponseSchemaの整合性チェック
- **原文**:
  - ワークフロー生成後、output mappingのフィールド参照がresponseSchemaと一致することを検証する
  - 不一致がある場合（camelCase vs snake_case等）、フィードバックループで修正する
  - capability YAMLのresponseSchemaを出力マッピング生成時に強制的に参照させる
- **分類**: 機能要件
- **テスト方法**: pytest / curl
- **モック使用**: 不可
- **検証ポイント**:
  1. camelCase/snake_case不一致の検出
  2. 警告メッセージに`CASE_MISMATCH`が含まれる
  3. フィールド参照先がresponseSchemaに存在することの確認
  4. 不一致時のフィードバックループでの自動修正

### AC-3: ノードタイプ仕様のプロンプト追加
- **原文**:
  - TransformNodeの仕様（`template`または`mapping`が必須、`expression`は未対応）をプロンプトに含める
  - 各ノードタイプ（api_rest, transform, llm等）の設定仕様を明確化する
  - 生成後にノード設定のバリデーションを追加する
- **分類**: 機能要件
- **テスト方法**: pytest / curl
- **モック使用**: 一部可（LLMプロンプト確認はモック可）
- **検証ポイント**:
  1. TransformNodeで`expression`使用時にエラーが返る
  2. TransformNodeで`template`または`mapping`のどちらかがあれば成功
  3. エラーメッセージに`INVALID_NODE_CONFIG`が含まれる
  4. プロンプトにノードタイプ仕様が含まれている

### AC-4: ワークフローリロード機能
- **原文**:
  - APIエンドポイント `POST /api/v1/taskflow/reload` を追加する
  - 指定プロジェクトのワークフローファイルを再読み込みする
  - 開発モード時はファイル変更監視による自動リロードを検討する（オプション）
- **分類**: 機能要件
- **テスト方法**: curl / pytest
- **モック使用**: 不可（実ファイル操作必須）
- **検証ポイント**:
  1. `/api/v1/taskflow/reload/{projectId}/{workflowName}`エンドポイントが存在する
  2. リロード成功時に`status: "success"`が返る
  3. リロード後のワークフロー実行で新しい内容が反映される
  4. 存在しないワークフロー指定時に404エラーが返る

### AC-5: E2Eテスト成功
- **原文**:
  - `./mySwiftAgentCore/e2etest/e2e-test-script.sh` が成功すること
  - task_001, task_002, task_003 が全て成功すること
  - 各タスクのresultsが正しく返却されること
- **分類**: 機能要件
- **テスト方法**: Bash script / curl
- **モック使用**: 不可（完全E2E）
- **検証ポイント**:
  1. E2Eテストスクリプトが exit code 0 で終了
  2. Test 1 (Health Check): PASS
  3. Test 2 (Generator Health): PASS
  4. Test 3 (Batch Generation): PASS
  5. Test 4 (Workflow Execution): task_001が成功（または許容されるtimeout）
  6. task_001: results.resultsに検索結果が含まれる
  7. task_002: results.summaryに要約テキストが含まれる
  8. task_003: results.message_idにメールIDが含まれる

---

## 4. 設計方針検証

### DP-1: アーキテクチャ整合性（検証レイヤー構成）
- **設計方針**: ValidationPipelineに新規バリデータ（OutputMappingValidator, NodeConfigValidator）を統合
- **検証方法**: コード構造確認、API呼び出し
- **テスト項目**:
  1. ValidationPipelineがOutputMappingValidatorを呼び出している
  2. ValidationPipelineがCapabilityValidatorを呼び出している
  3. 検証エラーが適切にAPI レスポンスに反映される

### DP-2: 技術選定整合性（chokidar使用）
- **設計方針**: ファイル監視にchokidarを使用
- **検証方法**: コード確認、動作テスト
- **テスト項目**:
  1. chokidarがpackage.jsonに含まれている
  2. FileSystemWatcherがchokidarを使用している
  3. ファイル変更時にイベントが発行される

### DP-3: API設計整合性（リロードエンドポイント）
- **設計方針**:
  - `POST /api/v1/taskflow/reload/{projectId}/{workflowName}`
  - `POST /api/v1/taskflow/validate`
- **検証方法**: curl / pytest
- **テスト項目**:
  1. リロードエンドポイントが存在する
  2. リクエスト形式が設計通りである
  3. レスポンス形式が設計通りである（status, workflowId, validationResult, reloadedAt）
  4. エラーレスポンス形式が設計通りである

### DP-4: セキュリティ設計整合性
- **設計方針**:
  - 指定ディレクトリのみ監視可能
  - パス検証によるディレクトリトラバーサル防止
  - デバウンスによるDoS攻撃防止
- **検証方法**: pytest
- **テスト項目**:
  1. 許可されていないディレクトリの監視が拒否される
  2. 相対パス（`../`）を含むリクエストが拒否される
  3. 連続リロードリクエストがデバウンスされる

### DP-5: パフォーマンス設計整合性
- **設計方針**:
  - デバウンス: 500ms
  - 検証結果キャッシュ: 5分TTL
- **検証方法**: pytest / 手動計測
- **テスト項目**:
  1. 連続ファイル変更が500ms以内にグループ化される
  2. 同一ワークフローの再検証がキャッシュから返る

---

## 5. デッドコード検証計画

### F-1: OutputMappingValidator
- **ファイル**: `src/taskflowGeneratorAgent/validator/validators/OutputMappingValidator.ts`
- **種別**: class
- **期待される呼び出し元**: ValidationPipeline, BatchProcessor
- **検証方法**:
  ```bash
  grep -rn "OutputMappingValidator" --include="*.ts" mySwiftAgentCore/src/
  ```
- **E2E確認**: ワークフロー生成APIを呼び出し、出力マッピング検証が実行されることを確認

### F-2: NodeConfigValidator
- **ファイル**: `src/taskflowGeneratorAgent/validator/validators/NodeConfigValidator.ts`
- **種別**: class
- **期待される呼び出し元**: ValidationPipeline
- **検証方法**:
  ```bash
  grep -rn "NodeConfigValidator" --include="*.ts" mySwiftAgentCore/src/
  ```
- **E2E確認**: 不正なTransformNode設定でエラーが返ることを確認

### F-3: FileSystemWatcher
- **ファイル**: `src/taskflowEngine/watcher/FileSystemWatcher.ts`
- **種別**: class
- **期待される呼び出し元**: WorkflowReloader, index.ts
- **検証方法**:
  ```bash
  grep -rn "FileSystemWatcher" --include="*.ts" mySwiftAgentCore/src/
  ```
- **E2E確認**: ファイル変更時に自動リロードが実行されることを確認（開発モード時）

### F-4: WorkflowReloader
- **ファイル**: `src/taskflowEngine/loader/WorkflowReloader.ts`
- **種別**: class
- **期待される呼び出し元**: リロードAPIハンドラ, FileSystemWatcher
- **検証方法**:
  ```bash
  grep -rn "WorkflowReloader" --include="*.ts" mySwiftAgentCore/src/
  ```
- **E2E確認**: リロードAPIを呼び出し、ワークフローが再読み込みされることを確認

### F-5: CapabilityErrorType拡張
- **ファイル**: エラータイプ定義ファイル
- **種別**: type
- **期待される定義**:
  - `UNKNOWN_CAPABILITY`
  - `OUTPUT_MAPPING_MISMATCH`
  - `INVALID_NODE_CONFIG`
- **検証方法**:
  ```bash
  grep -rn "UNKNOWN_CAPABILITY\|OUTPUT_MAPPING_MISMATCH\|INVALID_NODE_CONFIG" --include="*.ts" mySwiftAgentCore/src/
  ```
- **E2E確認**: 各エラータイプがAPIレスポンスに含まれることを確認

---

## 6. テスト環境

### 必須サービス
| サービス | URL | ヘルスチェック |
|---------|-----|--------------|
| mySwiftAgentCore | http://localhost:8006 | GET /health |
| myVault | http://localhost:8103 | GET /health |
| expertAgent | http://localhost:8104 | GET /health |
| graphAiServer | http://localhost:8105 | GET /health |
| Valkey | localhost:6379 | PING |
| PostgreSQL | localhost:5432 | - |
| Langfuse | http://localhost:3001 | GET /api/public/health |

### 起動コマンド
```bash
# Platform層: Dockerで起動
cd /Users/maenokota/share/work/github_kewton/MySwiftAgent
docker compose up -d valkey postgres langfuse myvault jobqueue myscheduler

# Agent層: ローカルで起動（推奨: dev-hybrid.sh）
./scripts/dev-hybrid.sh stop --local-only
./scripts/dev-hybrid.sh start --local-only

# 起動確認
curl -sf http://localhost:8006/health && echo "mySwiftAgentCore healthy"
curl -sf http://localhost:8103/health && echo "myVault healthy"
curl -sf http://localhost:8104/health && echo "expertAgent healthy"
curl -sf http://localhost:8105/health && echo "graphAiServer healthy"
```

### 環境変数
| 変数名 | 説明 | 必須 |
|--------|------|------|
| ANTHROPIC_API_KEY | Anthropic APIキー（LLM呼び出し用） | YES |
| OPENAI_API_KEY | OpenAI APIキー（代替LLM） | NO |
| GOOGLE_API_KEY | Google Search API（google_search capability） | YES |
| GOOGLE_CSE_ID | Google Custom Search Engine ID | YES |
| GMAIL_CREDENTIALS | Gmail API認証情報（gmail_send capability） | YES |

### テストデータ
- **default_project**: myVaultに設定済みのテストプロジェクト
- **capability定義**: `mySwiftAgentCore/config/capabilities/` に定義済み
  - `google_search.yaml`
  - `myllm.yaml`
  - `gmail_send.yaml`

---

## 7. テスト項目

### TC-001: capability_id存在確認 - 存在するcapability
- **テスト観点**: 正常系 - 存在するcapability_idでワークフロー生成が成功する
- **関連する受入条件**: AC-1
- **関連する設計方針**: DP-1
- **テスト種別**: E2E
- **テスト方法**: curl
- **前提条件**:
  1. mySwiftAgentCoreが起動している
  2. default_projectにgoogle_search capabilityが登録されている
- **テスト手順**:
  1. バッチ生成APIを呼び出す（google_search使用）
  2. レスポンスを確認する
- **期待結果**:
  - success: true
  - validationErrorsが空
- **curlコマンド**:
  ```bash
  curl -s -X POST http://localhost:8006/api/v1/generator/workflow/batch \
    -H "Content-Type: application/json" \
    -d '{
      "tasks": [{
        "task_id": "test_001",
        "name": "Test Search",
        "description": "Search using google_search capability",
        "interface": {"input": {"query": "string"}, "output": {"results": "array"}}
      }],
      "capabilities": [{"id": "google_search", "name": "Google Search", "category": "api", "status": "available"}],
      "project_id": "default_project"
    }' | jq '.success, .validationErrors'
  ```
- **pytestメソッド**: `test_tc_001_valid_capability_id`

### TC-002: capability_id存在確認 - 存在しないcapability
- **テスト観点**: 異常系 - 存在しないcapability_idでエラーが返る
- **関連する受入条件**: AC-1
- **関連する設計方針**: DP-1
- **テスト種別**: E2E
- **テスト方法**: curl
- **前提条件**:
  1. mySwiftAgentCoreが起動している
- **テスト手順**:
  1. 存在しないcapability_id（`invalid_capability`）でバッチ生成APIを呼び出す
  2. エラーレスポンスを確認する
- **期待結果**:
  - validationErrorsに`UNKNOWN_CAPABILITY`エラーが含まれる
  - 利用可能なcapability一覧がエラーメッセージに含まれる
- **curlコマンド**:
  ```bash
  curl -s -X POST http://localhost:8006/api/v1/generator/workflow/batch \
    -H "Content-Type: application/json" \
    -d '{
      "tasks": [{
        "task_id": "test_002",
        "name": "Invalid Test",
        "description": "Test with invalid capability",
        "interface": {"input": {"data": "string"}, "output": {"result": "string"}}
      }],
      "capabilities": [{"id": "invalid_capability", "name": "Invalid", "category": "api", "status": "available"}],
      "project_id": "default_project"
    }' | jq '.validationErrors, .failed_tasks'
  ```
- **pytestメソッド**: `test_tc_002_invalid_capability_id`

### TC-003: 出力マッピング検証 - camelCase/snake_case不一致
- **テスト観点**: 出力マッピングのケース不一致が検出される
- **関連する受入条件**: AC-2
- **関連する設計方針**: DP-1
- **テスト種別**: E2E
- **テスト方法**: curl
- **前提条件**:
  1. mySwiftAgentCoreが起動している
  2. capability YAMLにresponseSchemaが定義されている
- **テスト手順**:
  1. バリデーションAPIを呼び出す（camelCase/snake_case不一致のワークフロー）
  2. 警告レスポンスを確認する
- **期待結果**:
  - warnings配列にCASE_MISMATCH警告が含まれる
  - "messageId vs message_id"のような具体的な指摘が含まれる
- **curlコマンド**:
  ```bash
  curl -s -X POST http://localhost:8006/api/v1/taskflow/validate \
    -H "Content-Type: application/json" \
    -d '{
      "projectId": "default_project",
      "workflow": {
        "workflow_name": "test_mapping",
        "steps": [{
          "id": "step1",
          "type": "api_rest",
          "config": {"capability_id": "gmail_send"}
        }],
        "output": {
          "messageId": "$steps.step1.message_id"
        }
      }
    }' | jq '.warnings'
  ```
- **pytestメソッド**: `test_tc_003_output_mapping_case_mismatch`

### TC-004: ノード設定バリデーション - TransformNode expression使用
- **テスト観点**: TransformNodeでexpression使用時にエラーが返る
- **関連する受入条件**: AC-3
- **関連する設計方針**: DP-1
- **テスト種別**: E2E
- **テスト方法**: curl
- **前提条件**:
  1. mySwiftAgentCoreが起動している
- **テスト手順**:
  1. expressionを使用したTransformNodeでワークフロー実行を試行
  2. エラーレスポンスを確認する
- **期待結果**:
  - status: "failed"
  - errors配列に"No template or mapping provided"または"INVALID_NODE_CONFIG"が含まれる
- **curlコマンド**:
  ```bash
  curl -s -X POST http://localhost:8006/api/v1/taskflow/execute \
    -H "Content-Type: application/json" \
    -d '{
      "project": "default_project",
      "workflow": "inline_test",
      "inputs": {"data": "test"},
      "_workflow": {
        "workflow_name": "inline_test",
        "steps": [{
          "id": "transform1",
          "type": "transform",
          "config": {"expression": "data.toUpperCase()"}
        }],
        "output": {"result": "$steps.transform1.output"}
      }
    }' | jq '.status, .errors'
  ```
- **pytestメソッド**: `test_tc_004_transform_node_expression_error`

### TC-005: ノード設定バリデーション - TransformNode template使用（正常）
- **テスト観点**: TransformNodeでtemplate使用時に正常動作する
- **関連する受入条件**: AC-3
- **関連する設計方針**: DP-1
- **テスト種別**: E2E
- **テスト方法**: curl
- **前提条件**:
  1. mySwiftAgentCoreが起動している
- **テスト手順**:
  1. templateを使用したTransformNodeでワークフロー実行
  2. 成功レスポンスを確認する
- **期待結果**:
  - status: "success"
  - results.outputにテンプレート適用結果が含まれる
- **curlコマンド**:
  ```bash
  curl -s -X POST http://localhost:8006/api/v1/taskflow/execute \
    -H "Content-Type: application/json" \
    -d '{
      "project": "default_project",
      "workflow": "inline_template_test",
      "inputs": {"name": "World"},
      "_workflow": {
        "workflow_name": "inline_template_test",
        "steps": [{
          "id": "transform1",
          "type": "transform",
          "config": {"template": "Hello, {{name}}!"}
        }],
        "output": {"result": "$steps.transform1.output"}
      }
    }' | jq '.status, .results'
  ```
- **pytestメソッド**: `test_tc_005_transform_node_template_success`

### TC-006: ワークフローリロード - 正常系
- **テスト観点**: リロードAPIが正常に動作する
- **関連する受入条件**: AC-4
- **関連する設計方針**: DP-3
- **テスト種別**: E2E
- **テスト方法**: curl
- **前提条件**:
  1. mySwiftAgentCoreが起動している
  2. 対象ワークフローファイルが存在する
- **テスト手順**:
  1. リロードAPIを呼び出す
  2. 成功レスポンスを確認する
- **期待結果**:
  - status: "success"
  - reloadedAtにタイムスタンプが含まれる
- **curlコマンド**:
  ```bash
  curl -s -X POST http://localhost:8006/api/v1/taskflow/reload/default_project/execute_google_search_task_001 \
    | jq '.status, .reloadedAt'
  ```
- **pytestメソッド**: `test_tc_006_workflow_reload_success`

### TC-007: ワークフローリロード - 存在しないワークフロー
- **テスト観点**: 存在しないワークフローのリロードで404エラーが返る
- **関連する受入条件**: AC-4
- **関連する設計方針**: DP-3
- **テスト種別**: E2E
- **テスト方法**: curl
- **前提条件**:
  1. mySwiftAgentCoreが起動している
- **テスト手順**:
  1. 存在しないワークフロー名でリロードAPIを呼び出す
  2. エラーレスポンスを確認する
- **期待結果**:
  - HTTPステータス: 404
  - status: "error"
  - message: "Workflow not found"
- **curlコマンド**:
  ```bash
  curl -s -w "\nHTTP Status: %{http_code}" -X POST http://localhost:8006/api/v1/taskflow/reload/default_project/nonexistent_workflow \
    | jq '.status, .message'
  ```
- **pytestメソッド**: `test_tc_007_workflow_reload_not_found`

### TC-008: E2Eテストスクリプト実行
- **テスト観点**: E2Eテストスクリプトが成功する
- **関連する受入条件**: AC-5
- **関連する設計方針**: DP-1, DP-3
- **テスト種別**: E2E
- **テスト方法**: Bash script
- **前提条件**:
  1. 全サービスが起動している
  2. 環境変数（APIキー等）が設定されている
- **テスト手順**:
  1. E2Eテストスクリプトを実行
  2. 終了コードを確認
- **期待結果**:
  - Test 1 (Health Check): PASS
  - Test 2 (Generator Health): PASS
  - Test 3 (Batch Generation): PASS
  - Test 4 (Workflow Execution): PASS または許容されるTIMEOUT
  - Exit code: 0
- **実行コマンド**:
  ```bash
  cd /Users/maenokota/share/work/github_kewton/MySwiftAgent/mySwiftAgentCore
  ./e2etest/e2e-test-script.sh
  echo "Exit code: $?"
  ```
- **pytestメソッド**: `test_tc_008_e2e_script_execution`

### TC-009: task_001 Google Search 実行
- **テスト観点**: task_001（Google Search）が正常に実行される
- **関連する受入条件**: AC-5
- **関連する設計方針**: DP-1
- **テスト種別**: E2E
- **テスト方法**: curl
- **前提条件**:
  1. 全サービスが起動している
  2. GOOGLE_API_KEY, GOOGLE_CSE_IDが設定されている
  3. execute_google_search_task_001ワークフローが生成済み
- **テスト手順**:
  1. task_001ワークフローを実行（query: 大谷翔平の妻）
  2. 結果を確認
- **期待結果**:
  - status: "success"
  - results.resultsに検索結果配列が含まれる（空でない）
- **curlコマンド**:
  ```bash
  curl -s -X POST http://localhost:8006/api/v1/taskflow/execute \
    -H "Content-Type: application/json" \
    -d '{
      "project": "default_project",
      "workflow": "execute_google_search_task_001",
      "inputs": {"query": "大谷翔平の妻"}
    }' \
    --max-time 240 | jq '.status, .results.results | length'
  ```
- **pytestメソッド**: `test_tc_009_task_001_google_search`

### TC-010: task_002 Summarize 実行
- **テスト観点**: task_002（Summarize）が正常に実行される
- **関連する受入条件**: AC-5
- **関連する設計方針**: DP-1
- **テスト種別**: E2E
- **テスト方法**: curl
- **前提条件**:
  1. 全サービスが起動している
  2. ANTHROPIC_API_KEYが設定されている
  3. task_001の結果が取得済み
- **テスト手順**:
  1. task_001の結果を使用してtask_002を実行
  2. 結果を確認
- **期待結果**:
  - status: "success"
  - results.summaryに要約テキストが含まれる
- **curlコマンド**:
  ```bash
  # task_001の結果を取得
  TASK001_RESULT=$(curl -s -X POST http://localhost:8006/api/v1/taskflow/execute \
    -H "Content-Type: application/json" \
    -d '{"project": "default_project", "workflow": "execute_google_search_task_001", "inputs": {"query": "大谷翔平の妻"}}' \
    --max-time 240)

  SEARCH_RESULTS=$(echo "$TASK001_RESULT" | jq '.results.results')

  # task_002実行
  curl -s -X POST http://localhost:8006/api/v1/taskflow/execute \
    -H "Content-Type: application/json" \
    -d "{\"project\": \"default_project\", \"workflow\": \"summarize_search_results_task_002\", \"inputs\": {\"results\": $SEARCH_RESULTS}}" \
    --max-time 120 | jq '.status, .results.summary'
  ```
- **pytestメソッド**: `test_tc_010_task_002_summarize`

### TC-011: task_003 Send Email 実行
- **テスト観点**: task_003（Send Email）が正常に実行される
- **関連する受入条件**: AC-5
- **関連する設計方針**: DP-1
- **テスト種別**: E2E
- **テスト方法**: curl
- **前提条件**:
  1. 全サービスが起動している
  2. GMAIL_CREDENTIALSが設定されている
  3. task_002の結果が取得済み
- **テスト手順**:
  1. task_002の結果を使用してtask_003を実行
  2. 結果を確認
- **期待結果**:
  - status: "success"
  - results.message_idにGmailメッセージIDが含まれる
- **curlコマンド**:
  ```bash
  # task_002の結果からsummaryを取得（事前に実行済みとする）
  SUMMARY="大谷翔平の妻についての要約テキスト"

  curl -s -X POST http://localhost:8006/api/v1/taskflow/execute \
    -H "Content-Type: application/json" \
    -d "{
      \"project\": \"default_project\",
      \"workflow\": \"send_email_via_gmail_task_003\",
      \"inputs\": {
        \"summary\": \"$SUMMARY\",
        \"to_email\": \"test@example.com\",
        \"subject\": \"大谷翔平の妻についての検索結果サマリー\"
      }
    }" \
    --max-time 60 | jq '.status, .results.message_id'
  ```
- **pytestメソッド**: `test_tc_011_task_003_send_email`

### TC-012: コンポーネント間整合性 - バリデータ整合性
- **テスト観点**: 複数バリデータが一貫したルールを適用している
- **関連する受入条件**: AC-1, AC-2, AC-3
- **関連する設計方針**: DP-1
- **テスト種別**: 結合
- **テスト方法**: pytest
- **前提条件**:
  1. 各バリデータが実装されている
- **テスト手順**:
  1. 同一ワークフローを複数バリデータで検証
  2. 結果の一貫性を確認
- **期待結果**:
  - 各バリデータが矛盾しないエラー/警告を返す
  - エラーメッセージの形式が統一されている
- **pytestメソッド**: `test_tc_012_validator_consistency`

### TC-013: フィードバックループ動作確認
- **テスト観点**: バリデーションエラー時にフィードバックループで修正される
- **関連する受入条件**: AC-1, AC-2
- **関連する設計方針**: DP-1
- **テスト種別**: E2E
- **テスト方法**: curl
- **前提条件**:
  1. mySwiftAgentCoreが起動している
  2. LLM APIキーが設定されている
- **テスト手順**:
  1. 意図的にエラーを含むワークフロー生成リクエストを送信
  2. フィードバックループ後の修正結果を確認
- **期待結果**:
  - 最終的に有効なワークフローが生成される
  - ログにフィードバックループの実行が記録される
- **pytestメソッド**: `test_tc_013_feedback_loop`

---

## 8. テスト実行計画

### 実行順序
1. サービス起動確認（ヘルスチェック）
2. pytest単体テスト実行（実装確認）
3. バリデータ個別テスト（TC-001 - TC-005）
4. リロードAPI テスト（TC-006 - TC-007）
5. E2Eスクリプトテスト（TC-008）
6. タスク連鎖テスト（TC-009 - TC-011）
7. 整合性テスト（TC-012 - TC-013）

### 成功基準
- [ ] すべてのpytestテストがパス
- [ ] TC-001 - TC-013 すべてパス
- [ ] E2Eテストスクリプトが exit code 0 で終了
- [ ] task_001, task_002, task_003 が全て成功（または許容されるtimeout）
- [ ] デッドコードが検出されないこと（F-1 - F-5 確認済み）

### 実行コマンドまとめ

```bash
# 1. サービス起動
./scripts/dev-hybrid.sh start --local-only

# 2. ヘルスチェック
curl -sf http://localhost:8006/health && echo "OK"

# 3. pytest実行（単体・結合テスト）
cd /Users/maenokota/share/work/github_kewton/MySwiftAgent/mySwiftAgentCore
npm test

# 4. E2Eテストスクリプト実行
./e2etest/e2e-test-script.sh

# 5. 個別タスクテスト（手動）
# TC-009, TC-010, TC-011 のcurlコマンドを順次実行
```

---

## 9. 補足事項

### タイムアウト考慮
- Google Search APIは1-3分かかる場合がある
- LLM呼び出しは30-60秒かかる場合がある
- curlコマンドには`--max-time`を設定している

### 外部サービス依存
- Google Search API: GOOGLE_API_KEY, GOOGLE_CSE_ID必須
- Anthropic API: ANTHROPIC_API_KEY必須
- Gmail API: GMAIL_CREDENTIALS必須

### 回復手順（テスト失敗時）
1. サービスログ確認: `docker compose logs -f myswiftagentcore`
2. 環境変数確認: myVaultのsecrets一覧
3. ワークフローファイル確認: `generated/workflows/default_project/`

### 注意事項
- task_003（Send Email）は実際にメールを送信するため、テスト用アドレスを使用すること
- E2Eテストは時間がかかる（全体で5-10分程度）
- LLMエラー（API key未設定等）は許容されるエラーとして扱う

---

## 承認欄

- [ ] テスト計画レビュー完了
- [ ] テスト環境準備完了
- [ ] 受入テスト実行完了

作成日: 2026-01-18
作成者: acceptance-plan-agent

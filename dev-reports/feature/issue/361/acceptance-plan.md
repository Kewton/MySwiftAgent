# 受入テスト計画書

**Issue**: #361
**作成日**: 2026-01-20
**作成者**: Claude Code

---

## 1. 概要

### 対象Issue
- **番号**: #361
- **タイトル**: feat(expertAgent): mySwiftAgentCore連携実装と旧WORKFLOW_GENコード削除
- **プロジェクト**: expertAgent

### 参照ドキュメント
- Issue: #361
- 設計方針書: `dev-reports/feature/issue/361/design-policy.md`
- 作業計画書: `dev-reports/feature/issue/361/work-plan.md`

### 概要
expertAgentのjobGeneratorV2（Python）からmySwiftAgentCore（TypeScript）のワークフロー生成APIを呼び出すための連携実装を行い、旧WORKFLOW_GEN実装（約12,690行）を削除する。

---

## 2. 単体テスト結果レビュー

### カバレッジ目標
- 目標: 90%以上
- 判定基準: 新規実装コードのカバレッジ90%以上

### テスト品質評価計画

| 指標 | 目標値 | 判定基準 |
|------|--------|---------|
| 新規テスト数 | 50件以上 | WorkflowGeneratorClient + インターフェース層 |
| モック使用テスト数 | 必要最小限 | 外部APIモックのみ |
| モック使用率 | 30%未満 | 過剰モック禁止 |
| 実API呼び出しテスト数 | 10件以上 | E2Eテストで検証 |

### 単体テストでカバーすべき項目
1. WorkflowGeneratorClient正常系（成功レスポンス）
2. WorkflowGeneratorClient部分成功（partial_success）
3. WorkflowGeneratorClientタイムアウト処理
4. WorkflowGeneratorClientリトライ機構
5. サーキットブレーカー状態遷移（CLOSED→OPEN→HALF_OPEN）
6. メトリクス記録
7. HTTPクライアント抽象化
8. 認証ヘッダー拡張性

---

## 3. 受入条件分析

### AC-1: WorkflowGeneratorClientが実装されている
- **原文**: WorkflowGeneratorClientが実装されている
- **分類**: 機能要件
- **テスト方法**: pytest + curl
- **モック使用**: E2Eでは不可
- **検証ポイント**:
  1. WorkflowGeneratorClientクラスが存在する
  2. generate_workflows()メソッドが正常に動作する
  3. 非同期コンテキストマネージャーが動作する

### AC-2: WorkflowGeneratorClientの単体テストが実装されている
- **原文**: WorkflowGeneratorClientの単体テストが実装されている（カバレッジ90%以上）
- **分類**: 品質要件
- **テスト方法**: pytest coverage
- **検証ポイント**:
  1. tests/unit/test_clients/ にテストファイルが存在
  2. カバレッジが90%以上
  3. 異常系テストが含まれる

### AC-3: mySwiftAgentCore API呼び出しでワークフロー生成
- **原文**: jobGeneratorV2がmySwiftAgentCore APIを呼び出してワークフローを生成する
- **分類**: 機能要件
- **テスト方法**: E2E実行
- **モック使用**: 不可
- **検証ポイント**:
  1. orchestrator.pyからWorkflowGeneratorClientが呼び出される
  2. POST /api/v1/generator/workflow/batch が呼び出される
  3. ワークフローが正常に生成される

### AC-4: Langfuseトレース伝播
- **原文**: trace_idがmySwiftAgentCoreに正しく伝播される
- **分類**: 機能要件
- **テスト方法**: Langfuse UI + ログ確認
- **検証ポイント**:
  1. X-Trace-Id ヘッダーが送信される
  2. Langfuseで親子Span関係が確認できる

### AC-5: recovery_suggestion処理
- **原文**: エラー時のrecovery_suggestion処理が実装されている
- **分類**: 機能要件
- **テスト方法**: pytest + 異常系E2E
- **検証ポイント**:
  1. ROLLBACK_TO_ANALYSISが適切に処理される
  2. 部分失敗時の処理が適切

### AC-6: 旧コード削除
- **原文**: workflows/workflow_gen/、types_old.py等が削除されている
- **分類**: 品質要件
- **テスト方法**: ファイル存在確認 + import検証
- **検証ポイント**:
  1. workflow_gen/ ディレクトリが存在しない
  2. types_old.py が存在しない
  3. orchestrator_old.py が存在しない
  4. adapter_old.py が存在しない
  5. v3エイリアスファイルが存在しない

### AC-7: types_old.py依存解消
- **原文**: types_old.pyへの依存が全て解消されている
- **分類**: 品質要件
- **テスト方法**: grep + mypy
- **検証ポイント**:
  1. `from .types_old import` が存在しない
  2. mypy通過
  3. 全テスト通過

### AC-8: 品質基準
- **原文**: pre-push-check-all.sh に合格する
- **分類**: 品質要件
- **テスト方法**: スクリプト実行
- **検証ポイント**:
  1. TypeScript/Pythonコンパイルエラーゼロ
  2. Ruff/MyPyエラーゼロ
  3. 全テスト通過

---

## 4. 設計方針検証

### DP-1: アーキテクチャ整合性
- **設計方針**: 3フェーズアーキテクチャ（JOB_ANALYSIS → REGISTRATION → WORKFLOW_GEN）
- **検証方法**: コード構造確認 + E2Eテスト
- **テスト項目**:
  1. Phase 3でWorkflowGeneratorClientが呼び出される
  2. parallel_workflow_generation呼び出しが削除されている

### DP-2: API設計整合性
- **設計方針**: POST /api/v1/generator/workflow/batch エンドポイント使用
- **検証方法**: curl + pytest
- **テスト項目**:
  1. エンドポイントが正しく呼び出される
  2. リクエスト形式が設計通り（tasks, capabilities, project_id, trace_context）
  3. レスポンス形式が設計通り（status, success, workflows）

### DP-3: 部分成功モデル整合性
- **設計方針**: BatchStatus enum（success/partial_success/failed）
- **検証方法**: pytest
- **テスト項目**:
  1. BatchStatus.SUCCESS が正しく判定される
  2. BatchStatus.PARTIAL_SUCCESS が正しく判定される
  3. BatchStatus.FAILED が正しく判定される
  4. from_results() ファクトリメソッドが正しく動作

### DP-4: HTTPクライアント抽象化
- **設計方針**: IHttpClient Protocol による抽象化
- **検証方法**: コード確認 + pytest
- **テスト項目**:
  1. IHttpClient Protocol が定義されている
  2. HttpxClientAdapter が実装されている
  3. テスト時にモックHTTPクライアントを注入できる

### DP-5: サーキットブレーカー
- **設計方針**: CircuitState（CLOSED/OPEN/HALF_OPEN）
- **検証方法**: pytest
- **テスト項目**:
  1. 正常時はCLOSED状態
  2. 連続失敗でOPEN状態に遷移
  3. タイムアウト後HALF_OPEN状態に遷移
  4. HALF_OPENで成功するとCLOSED状態に復帰

---

## 5. デッドコード検証計画

### F-1: WorkflowGeneratorClient
- **ファイル**: `expertAgent/aiagent/clients/workflow_generator_client.py`
- **種別**: class
- **期待される呼び出し元**: orchestrator.py
- **検証方法**:
  ```bash
  grep -rn "WorkflowGeneratorClient" --include="*.py" | grep -v "def \|class "
  ```
- **E2E確認**: Job Generate実行でワークフロー生成が成功する

### F-2: IHttpClient
- **ファイル**: `expertAgent/aiagent/clients/interfaces/http_client.py`
- **種別**: Protocol
- **期待される呼び出し元**: WorkflowGeneratorClient
- **検証方法**:
  ```bash
  grep -rn "IHttpClient" --include="*.py"
  ```
- **E2E確認**: HTTP通信が成功する

### F-3: CircuitBreaker
- **ファイル**: `expertAgent/aiagent/clients/interfaces/circuit_breaker.py`
- **種別**: class
- **期待される呼び出し元**: WorkflowGeneratorClient
- **検証方法**:
  ```bash
  grep -rn "CircuitBreaker" --include="*.py" | grep -v "def \|class "
  ```
- **E2E確認**: 連続失敗時にサーキットブレーカーが動作する（ログ確認）

### F-4: BatchStatus
- **ファイル**: `expertAgent/aiagent/clients/types/workflow_generator.py`
- **種別**: Enum
- **期待される呼び出し元**: WorkflowGeneratorClient, orchestrator.py
- **検証方法**:
  ```bash
  grep -rn "BatchStatus" --include="*.py"
  ```
- **E2E確認**: レスポンスにstatusフィールドが含まれる

---

## 6. テスト環境

### 必須サービス
| サービス | URL | ヘルスチェック |
|---------|-----|--------------|
| expertAgent | http://localhost:8104 | GET /health |
| mySwiftAgentCore | http://localhost:8006 | GET /api/health |
| myVault | http://localhost:8003 | GET /health |
| Langfuse | http://localhost:3001 | Web UI確認 |

### 起動コマンド（E2Eテスト用 - 必須）

```bash
# 1. 既存サービスを停止
./scripts/dev-hybrid.sh stop --local-only

# 2. ローカルモードでサービスを起動
./scripts/dev-hybrid.sh start --local-only

# 3. ヘルスチェック
curl -sf http://localhost:8104/health && echo "expertAgent healthy"
curl -sf http://localhost:8006/api/health && echo "mySwiftAgentCore healthy"
curl -sf http://localhost:8003/health && echo "myVault healthy"
```

### 環境変数
| 変数名 | 説明 | 必須 |
|--------|------|------|
| MYVAULT_ENABLED | MyVault有効化フラグ | true |
| MYVAULT_BASE_URL | MyVault URL | http://localhost:8003 |
| MYSWIFTAGENT_CORE_URL | mySwiftAgentCore URL | http://localhost:8006 |
| USE_MYSWIFTAGENT_CORE_WORKFLOW_GEN | 新実装使用フラグ | true |

### シークレット・設定情報
- myVault (default_project) からシークレットを取得
- OPENAI_API_KEY, ANTHROPIC_API_KEY が設定済みであること

---

## 7. テスト項目

### TC-001: mySwiftAgentCore API直接呼び出し
- **テスト観点**: WorkflowGeneratorClientがmySwiftAgentCore APIを正しく呼び出せるか
- **関連する受入条件**: AC-1, AC-3
- **関連する設計方針**: DP-2
- **テスト種別**: E2E
- **テスト方法**: curl
- **前提条件**:
  1. mySwiftAgentCoreが起動している
  2. myVaultにシークレットが登録されている
- **テスト手順**:
  1. POST /api/v1/generator/workflow/batch を呼び出す
  2. レスポンスを確認する
- **期待結果**:
  - HTTPステータス: 200
  - レスポンス: status, success, workflows が含まれる
- **curlコマンド**:
  ```bash
  curl -s -X POST http://localhost:8006/api/v1/generator/workflow/batch \
    -H "Content-Type: application/json" \
    -H "X-Trace-Id: test-trace-$(date +%s)" \
    -d '{
      "tasks": [{
        "task_id": "test_task_001",
        "name": "Test Task",
        "description": "Integration test task for searching",
        "interface": {
          "input": {"keyword": "string"},
          "output": {"result": "string"}
        }
      }],
      "capabilities": [],
      "project_id": "default_project"
    }' | jq '.status, .success'
  ```
- **pytestメソッド**: `test_tc_001_myswiftagentcore_api_direct_call`

### TC-002: expertAgent経由のワークフロー生成
- **テスト観点**: orchestrator.pyがWorkflowGeneratorClientを使用してワークフロー生成するか
- **関連する受入条件**: AC-3
- **関連する設計方針**: DP-1
- **テスト種別**: E2E
- **テスト方法**: myAgentDesk UI / API
- **前提条件**:
  1. expertAgent, mySwiftAgentCoreが起動している
  2. myVaultにシークレットが登録されている
- **テスト手順**:
  1. Job Generate APIを呼び出す
  2. Phase 3（WORKFLOW_GEN）が成功することを確認
- **期待結果**:
  - Job Generateが成功する
  - ワークフローが生成される
- **手動テストURL**:
  ```
  http://localhost:8000/projects/proj_mjbjua2z7y65wy/workbenches/wb_1766969315404_udrhx79/generate
  ```
- **pytestメソッド**: `test_tc_002_workflow_generation_via_expertAgent`

### TC-003: 部分成功シナリオ
- **テスト観点**: 複数タスクで一部失敗した場合、partial_successが返されるか
- **関連する受入条件**: AC-5
- **関連する設計方針**: DP-3
- **テスト種別**: E2E
- **テスト方法**: curl
- **前提条件**:
  1. mySwiftAgentCoreが起動している
- **テスト手順**:
  1. 有効なタスクと無効なタスクを含むリクエストを送信
  2. ステータスを確認
- **期待結果**:
  - status: "partial_success"
  - succeeded_tasks > 0
  - failed_task_count > 0
- **curlコマンド**:
  ```bash
  curl -s -X POST http://localhost:8006/api/v1/generator/workflow/batch \
    -H "Content-Type: application/json" \
    -d '{
      "tasks": [
        {
          "task_id": "valid_task",
          "name": "Valid Task",
          "description": "This should succeed",
          "interface": {"input": {"query": "string"}, "output": {"result": "string"}}
        },
        {
          "task_id": "invalid_task",
          "name": "",
          "description": "This should fail validation",
          "interface": {}
        }
      ],
      "capabilities": [],
      "project_id": "default_project"
    }' | jq '.status, .success, .succeeded_tasks, .failed_task_count'
  ```
- **pytestメソッド**: `test_tc_003_partial_success_scenario`

### TC-004: Langfuseトレース伝播確認
- **テスト観点**: trace_idがexpertAgent→mySwiftAgentCoreに伝播されるか
- **関連する受入条件**: AC-4
- **関連する設計方針**: DP-2
- **テスト種別**: E2E
- **テスト方法**: ログ確認 + Langfuse UI
- **前提条件**:
  1. Langfuseが起動している
  2. expertAgent, mySwiftAgentCoreが起動している
- **テスト手順**:
  1. 特定のtrace_idでJob Generateを実行
  2. Langfuse UIでトレースを確認
- **期待結果**:
  - expertAgentからmySwiftAgentCoreへのトレースが連続している
  - X-Trace-Idヘッダーがログに記録されている
- **検証コマンド**:
  ```bash
  # expertAgentログでtrace_id確認
  grep "X-Trace-Id" expertAgent/logs/*.log

  # Langfuse UI確認
  open http://localhost:3001
  ```
- **pytestメソッド**: `test_tc_004_langfuse_trace_propagation`

### TC-005: 旧コード削除確認
- **テスト観点**: 旧WORKFLOW_GEN関連コードが削除されているか
- **関連する受入条件**: AC-6, AC-7
- **関連する設計方針**: -
- **テスト種別**: 静的検証
- **テスト方法**: ファイル存在確認 + grep
- **テスト手順**:
  1. 削除対象ファイル/ディレクトリの存在を確認
  2. types_old.pyへのimportが存在しないことを確認
- **期待結果**:
  - workflow_gen/ が存在しない
  - types_old.py が存在しない
  - orchestrator_old.py が存在しない
  - adapter_old.py が存在しない
  - v3エイリアスファイルが存在しない
  - `from .types_old import` が存在しない
- **検証コマンド**:
  ```bash
  # ディレクトリ存在確認
  ls expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/workflow_gen/ 2>/dev/null && echo "FAIL: workflow_gen exists" || echo "PASS: workflow_gen deleted"

  # ファイル存在確認
  ls expertAgent/aiagent/langgraph/jobGeneratorV2/types_old.py 2>/dev/null && echo "FAIL: types_old.py exists" || echo "PASS: types_old.py deleted"
  ls expertAgent/aiagent/langgraph/jobGeneratorV2/orchestrator_old.py 2>/dev/null && echo "FAIL: orchestrator_old.py exists" || echo "PASS: orchestrator_old.py deleted"
  ls expertAgent/aiagent/langgraph/jobGeneratorV2/adapter_old.py 2>/dev/null && echo "FAIL: adapter_old.py exists" || echo "PASS: adapter_old.py deleted"

  # v3エイリアス確認
  ls expertAgent/aiagent/langgraph/jobGeneratorV2/*_v3.py 2>/dev/null && echo "FAIL: v3 files exist" || echo "PASS: v3 files deleted"

  # import確認
  grep -rn "from .types_old import" expertAgent/ && echo "FAIL: types_old import exists" || echo "PASS: no types_old import"
  ```
- **pytestメソッド**: `test_tc_005_old_code_deletion`

### TC-006: pre-push-check-all.sh実行
- **テスト観点**: 品質基準を満たしているか
- **関連する受入条件**: AC-8
- **関連する設計方針**: -
- **テスト種別**: 品質検証
- **テスト方法**: スクリプト実行
- **テスト手順**:
  1. pre-push-check-all.sh を実行
  2. 全チェックがパスすることを確認
- **期待結果**:
  - 終了コード: 0
  - TypeScript/Pythonエラー: 0
  - Ruff/MyPyエラー: 0
  - テスト: 全パス
- **実行コマンド**:
  ```bash
  ./scripts/pre-push-check-all.sh
  ```
- **pytestメソッド**: `test_tc_006_pre_push_check`

### TC-007: E2Eワークフロー実行
- **テスト観点**: 生成されたワークフローが実際に実行できるか
- **関連する受入条件**: AC-3
- **関連する設計方針**: DP-1, DP-2
- **テスト種別**: E2E
- **テスト方法**: myAgentDesk UI
- **前提条件**:
  1. 全サービスが起動している
  2. ワークフローが生成済み
- **テスト手順**:
  1. Job Generate実行
  2. Run実行（パラメータ: キーワード「大谷翔平の妻」）
  3. 実行結果を確認
- **期待結果**:
  - ジョブが正常に完了
  - 検索結果が取得できる
- **手動テストURL**:
  ```
  http://localhost:8000/projects/proj_mjbjua2z7y65wy/workbenches/wb_1766969315404_udrhx79/runs
  パラメータ:
  - キーワード: 大谷翔平の妻
  ```
- **pytestメソッド**: `test_tc_007_e2e_workflow_execution`

### TC-008: サーキットブレーカー動作確認
- **テスト観点**: サーキットブレーカーが正しく動作するか
- **関連する受入条件**: AC-1
- **関連する設計方針**: DP-5
- **テスト種別**: 単体テスト
- **テスト方法**: pytest
- **テスト手順**:
  1. 連続失敗を発生させる
  2. OPEN状態に遷移することを確認
  3. タイムアウト後HALF_OPENに遷移することを確認
- **期待結果**:
  - 5回連続失敗でOPEN状態
  - 30秒後にHALF_OPEN状態
  - 成功でCLOSED状態に復帰
- **pytestメソッド**: `test_tc_008_circuit_breaker_state_transitions`

---

## 8. テスト実行計画

### 実行順序

1. **環境準備**
   ```bash
   ./scripts/dev-hybrid.sh stop --local-only
   ./scripts/dev-hybrid.sh start --local-only
   ```

2. **ヘルスチェック**
   ```bash
   curl -sf http://localhost:8104/health && echo "expertAgent OK"
   curl -sf http://localhost:8006/api/health && echo "mySwiftAgentCore OK"
   curl -sf http://localhost:8003/health && echo "myVault OK"
   ```

3. **静的検証（TC-005）**
   - 旧コード削除確認
   - import文確認

4. **単体テスト実行**
   ```bash
   cd expertAgent
   uv run pytest tests/unit/test_clients/ -v --cov=aiagent.clients --cov-report=term-missing
   ```

5. **結合テスト実行**
   ```bash
   cd expertAgent
   uv run pytest tests/integration/test_workflow_generator_integration.py -v
   ```

6. **受入テスト実行**
   ```bash
   cd expertAgent
   uv run pytest tests/acceptance/test_issue_361_acceptance.py -v -s
   ```

7. **E2Eテスト（手動）**
   - TC-002: Job Generate実行
   - TC-007: ワークフロー実行

8. **品質チェック**
   ```bash
   ./scripts/pre-push-check-all.sh
   ```

### 成功基準

- [ ] すべてのpytestテストがパス
- [ ] すべての受入条件（AC-1〜AC-8）が検証済み
- [ ] すべての設計方針（DP-1〜DP-5）が検証済み
- [ ] デッドコードが検出されないこと
- [ ] 旧コードが完全に削除されていること
- [ ] pre-push-check-all.shがパス
- [ ] Langfuseでトレース連続性が確認できること

---

## 9. コンポーネント間整合性検証

### CI-1: BatchStatus整合性
- **検証対象**: expertAgent と mySwiftAgentCore のステータス値
- **検証方法**:
  ```bash
  # expertAgent側
  grep -n "BatchStatus\|status.*success\|partial_success\|failed" expertAgent/aiagent/clients/

  # mySwiftAgentCore側
  grep -n "status.*success\|partial_success\|failed" mySwiftAgentCore/src/
  ```
- **確認項目**:
  - [ ] 両サービスで同じステータス値を使用している
  - [ ] from_results()のロジックが正しい

### CI-2: HTTPヘッダー整合性
- **検証対象**: トレース用ヘッダー
- **検証方法**:
  ```bash
  grep -n "X-Trace-Id\|X-Parent-Span-Id" expertAgent/ mySwiftAgentCore/
  ```
- **確認項目**:
  - [ ] ヘッダー名が一致している
  - [ ] ヘッダーが正しく伝播している

---

## 10. 補足事項

### リスク対策
1. **mySwiftAgentCore API障害時**: リトライ機構が動作することを確認（TC-008）
2. **types_old.py移行漏れ**: mypy実行で検出（TC-006）
3. **カバレッジ低下**: 単体テスト実行時にカバレッジレポートを確認

### 移行期間の考慮
- 環境変数 `USE_MYSWIFTAGENT_CORE_WORKFLOW_GEN` で新旧切り替え可能
- 切り替え動作の確認もテスト項目に含む

### 参照Issue
- #359: 3フェーズ統一ID方式
- #360: 成功条件・エラー伝播修正
- #383: Epic - TaskFlow安定化（受入テスト完了）

---

*作成日: 2026-01-20*
*作成者: Claude Code*

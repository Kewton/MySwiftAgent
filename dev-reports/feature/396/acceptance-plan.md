# 受入テスト計画書

**Issue**: #396
**作成日**: 2026-01-23
**作成者**: acceptance-plan-agent
**フェーズ**: PRE-TDD（TDD実装前の計画立案）

---

## 1. 概要

### 対象Issue
- **番号**: #396
- **タイトル**: Bug: orchestrator.py - Phase 3完了後のTaskMaster workflow更新が未実装（Issue #390 問題#4）
- **プロジェクト**: expertAgent
- **サイズ**: S
- **優先度**: High（本番環境でのワークフロー実行不可を解消）

### 問題概要
Job Generator V2のPhase 3（WORKFLOW_GEN）完了後、TaskMasterの`body_template.workflow`フィールドが`__PENDING__`から実際のワークフロー名に更新されない。これにより、ジョブ実行時に`HTTP 404: Workflow '__PENDING__' not found`エラーが発生する。

### 参照ドキュメント
- Issue: #396
- 設計方針書: `dev-reports/feature/issue/396/design-policy.md`
- 作業計画書: `dev-reports/feature/issue/396/work-plan.md`
- 関連Issue: #390（問題#4として特定）、#360（All-or-Nothing更新要件）

---

## 2. 単体テスト結果レビュー

### PRE-TDD状態
このセクションはTDD実装後に更新されます。

**現在の状態**:
- **単体テスト**: `test_orchestrator_issue390.py` - 全テストにskipマーク（実装待ち）
- **結合テスト**: `test_issue390_integration.py` - 全テストにskipマーク（実装待ち）

### 準備済みテスト一覧

| テストファイル | テスト数 | 状態 |
|--------------|---------|------|
| `expertAgent/tests/unit/test_job_generator_v2/test_orchestrator_issue390.py` | 9件 | skipマーク |
| `expertAgent/tests/integration/test_issue390_integration.py` | 7件 | skipマーク |

### TDD実装後に確認する項目
- [ ] カバレッジ90%以上
- [ ] 全skipマークが解除されている
- [ ] 静的解析エラーが0件

---

## 3. 受入条件分析

### AC-1: TaskMaster workflow更新
- **原文**: Job Generate後、TaskMasterのbody_template.workflowが実際のワークフロー名で更新される
- **分類**: 機能要件
- **テスト方法**: pytest E2E / curl
- **モック使用**: 不可（実サービス連携必須）
- **検証ポイント**:
  1. Phase 3完了後にTaskMasterのbody_template.workflowが`__PENDING__`でないこと
  2. body_template.workflowに実際のワークフロー名（例: `task_001_google_search`）が設定されること
  3. 既存のinputs, project, job_paramsフィールドが保持されること

### AC-2: Job Run正常実行
- **原文**: Job Runが正常に実行される（__PENDING__エラーが発生しない）
- **分類**: 機能要件
- **テスト方法**: pytest E2E / curl
- **モック使用**: 不可（実サービス連携必須）
- **検証ポイント**:
  1. Job実行時に`HTTP 404: Workflow '__PENDING__' not found`エラーが発生しないこと
  2. ワークフローが正常に開始されること

### AC-3: 単体テストパス
- **原文**: test_orchestrator_issue390.pyの全テストがパス
- **分類**: 品質要件
- **テスト方法**: pytest
- **モック使用**: 可（単体テストは対象外、CI実行で確認）
- **検証ポイント**:
  1. skipマークが解除されていること
  2. 全9件のテストがパスすること

### AC-4: 結合テストパス
- **原文**: test_issue390_integration.pyの全テストがパス
- **分類**: 品質要件
- **テスト方法**: pytest
- **モック使用**: 可（結合テストは対象外、CI実行で確認）
- **検証ポイント**:
  1. skipマークが解除されていること
  2. 全7件のテストがパスすること

### AC-5: E2Eテスト成功
- **原文**: E2Eテスト成功（実際のジョブ生成→実行フロー）
- **分類**: 機能要件
- **テスト方法**: pytest受入テスト / curl
- **モック使用**: 不可（E2Eは実サービス必須）
- **検証ポイント**:
  1. Job Generate APIが成功すること
  2. TaskMasterが更新されること
  3. Job Run APIが成功すること（404エラーなし）

---

## 4. 設計方針検証

### DP-1: All-or-Nothing Pattern（Issue #360）
- **設計方針**: 部分的成功は許可しない。一つでもTaskMaster更新に失敗したら全体が失敗
- **検証方法**: 障害注入テスト（モック環境）
- **テスト項目**:
  1. 全TaskMaster更新成功時に正常完了すること
  2. 1件でも更新失敗時にOrchestratorErrorが発生すること
  3. 複数件失敗時にエラーメッセージに全失敗task_idが含まれること

### DP-2: Local Import Pattern（循環参照回避）
- **設計方針**: `_update_task_masters_workflow`メソッド内でローカルインポートを使用
- **検証方法**: コード構造確認 / 起動テスト
- **テスト項目**:
  1. orchestrator.pyのインポート時に循環参照エラーが発生しないこと
  2. update_task_master_body_template_taskflowが正しくインポートされること

### DP-3: Fail-Fast Pattern
- **設計方針**: エラーは即座に上位に伝播
- **検証方法**: 異常系テスト
- **テスト項目**:
  1. JobQueue API障害時に即座にOrchestratorErrorが発生すること
  2. エラーメッセージにphase情報が含まれること

### DP-4: 既存フィールド保持
- **設計方針**: body_template更新時にinputs, project, job_paramsフィールドを保持
- **検証方法**: API呼び出し結果確認
- **テスト項目**:
  1. タスクチェイニング用inputs（`{{tasks[0].output_data}}`など）が保持されること
  2. projectフィールドが保持されること
  3. job_paramsフィールドが保持されること

---

## 5. デッドコード検証計画

### F-1: _update_task_masters_workflow メソッド
- **ファイル**: `expertAgent/aiagent/langgraph/jobGeneratorV2/orchestrator.py`
- **種別**: method
- **期待される呼び出し元**: `_execute_workflow_gen` メソッド（Phase 3完了後）
- **検証方法**:
  ```bash
  # 呼び出し箇所を確認
  grep -rn "_update_task_masters_workflow" expertAgent/ --include="*.py"
  ```
- **E2Eでの確認方法**: Job Generate API呼び出し後、TaskMasterのbody_template.workflowを確認

### F-2: update_task_master_body_template_taskflow 関数
- **ファイル**: `expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/registration/task_master_utils.py`
- **種別**: function
- **期待される呼び出し元**: `_update_task_masters_workflow` メソッド
- **検証方法**:
  ```bash
  # 呼び出し箇所を確認
  grep -rn "update_task_master_body_template_taskflow" expertAgent/ --include="*.py" | grep -v "def update_task_master"
  ```
- **E2Eでの確認方法**: TaskMaster更新ログの確認

---

## 6. コンポーネント間整合性検証

### CI-1: orchestrator.py と task_master_utils.py の整合性
- **検証対象**: TaskMaster更新処理の一貫性
- **検証方法**:
  ```bash
  # 同じtask_master_id, workflow_name形式を使用していることを確認
  grep -n "task_master_id\|workflow_name" expertAgent/aiagent/langgraph/jobGeneratorV2/orchestrator.py
  grep -n "task_master_id\|workflow_name" expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/registration/task_master_utils.py
  ```
- **確認項目**:
  - [ ] task_master_idの型がstrで一貫している
  - [ ] workflow_nameの型がstrで一貫している

### CI-2: ParallelExecutionResult構造との整合性
- **検証対象**: _update_task_masters_workflowが受け取る結果構造
- **確認項目**:
  - [ ] successful_tasks内にworkflow辞書が存在する
  - [ ] workflow辞書にtask_master_id, workflow_nameが含まれる

---

## 7. サービス間データフロー検証

### DF-1: データフロー完全性
外部サービスに渡すデータの取得元が明確であることを確認：

| 送信元 | データ項目 | 送信先 | 取得方法 | 検証状態 |
|--------|-----------|--------|---------|---------|
| orchestrator | task_master_id | JobQueue API | ParallelExecutionResult.successful_tasks[].workflow.task_master_id | ??? |
| orchestrator | workflow_name | JobQueue API | ParallelExecutionResult.successful_tasks[].workflow.workflow_name | ??? |
| task_master_utils | body_template | JobQueue API | 既存TaskMaster + workflow更新 | ??? |

### DF-2: 空配列/null検証
テストデータが「空」「null」を正常ケースとして扱っていないか確認：

| 検出パターン | テストファイル | 問題 |
|------------|--------------|------|
| successful_tasks=[] | test_orchestrator_issue390.py | ✅ 適切（空の場合のテスト） |
| workflow=None | test_orchestrator_issue390.py | ✅ 適切（ワークフローなしのテスト） |

---

## 8. テスト環境

### 必須サービス
| サービス | URL | ヘルスチェック |
|---------|-----|--------------|
| expertAgent | http://localhost:8004 | GET /health |
| JobQueue | http://localhost:8001 | GET /api/v1/health |
| myVault | http://localhost:8003 | GET /health |
| mySwiftAgentCore | http://localhost:8006 | GET /health |

### 起動コマンド（E2Eテスト用 - 必須）

**重要**: E2Eテストは以下の環境で実行すること。

```bash
# 1. 既存サービスを停止
./scripts/dev-hybrid.sh stop --local-only

# 2. ローカルモードでサービスを起動
./scripts/dev-hybrid.sh start --local-only
```

これにより:
- mySwiftAgentCore, expertAgent: ローカル直接起動（localhost:8006, localhost:8004）
- myVault: Dockerコンテナで起動（localhost:8003）
- JobQueue: Dockerコンテナで起動（localhost:8001）

### シークレット・設定情報

**E2Eテストで使用するシークレットは、コンテナ起動のmyVaultのdefault_projectから取得**します。

| 項目 | 取得元 |
|------|--------|
| OPENAI_API_KEY | myVault (default_project) |
| LLM_API_KEY | myVault (default_project) |
| ANTHROPIC_API_KEY | myVault (default_project) |

### 環境変数
| 変数名 | 説明 | 必須 |
|--------|------|------|
| MYVAULT_ENABLED | MyVault有効化フラグ | true |
| MYVAULT_BASE_URL | MyVault URL | http://localhost:8003 |
| JOBQUEUE_API_URL | JobQueue URL | http://localhost:8001 |
| MYSWIFTAGENT_CORE_URL | mySwiftAgentCore URL | http://localhost:8006 |

---

## 9. テスト項目

### TC-001: TaskMaster workflow更新（正常系）
- **テスト観点**: Job Generate後にTaskMasterのworkflowフィールドが更新されること
- **関連する受入条件**: AC-1, AC-5
- **関連する設計方針**: DP-4
- **テスト種別**: E2E
- **テスト方法**: curl / pytest
- **前提条件**:
  1. 全サービスが起動していること
  2. myVaultにAPIキーが登録されていること
- **テスト手順**:
  1. Job Generate APIを呼び出す
  2. 生成されたjob_master_idを取得
  3. TaskMaster一覧を取得
  4. 各TaskMasterのbody_template.workflowを確認
- **期待結果**:
  - HTTPステータス: 200
  - body_template.workflowが`__PENDING__`でないこと
  - body_template.workflowに実際のワークフロー名が設定されていること
- **curlコマンド**:
  ```bash
  # 1. Job Generate
  RESPONSE=$(curl -s -X POST http://localhost:8004/v1/job-generator/generate \
    -H "Content-Type: application/json" \
    -d '{
      "user_requirement": "Google検索を実行する簡単なジョブ",
      "project_id": "default_project"
    }')
  echo "$RESPONSE" | jq .

  # 2. job_master_idを取得
  JOB_MASTER_ID=$(echo "$RESPONSE" | jq -r '.job_master_id')
  echo "Job Master ID: $JOB_MASTER_ID"

  # 3. TaskMaster確認
  curl -s "http://localhost:8001/api/v1/task-masters?job_master_id=$JOB_MASTER_ID" | jq '.[] | {id, body_template}'
  ```
- **pytestメソッド**: `test_tc_001_taskmaster_workflow_updated`

### TC-002: Job Run正常実行（__PENDING__エラーなし）
- **テスト観点**: 更新されたTaskMasterでJob Runが成功すること
- **関連する受入条件**: AC-2, AC-5
- **関連する設計方針**: -
- **テスト種別**: E2E
- **テスト方法**: curl / pytest
- **前提条件**:
  1. TC-001が成功していること
  2. TaskMasterのworkflowが更新されていること
- **テスト手順**:
  1. Job Master IDを使用してJobを作成
  2. Job実行ステータスを確認
- **期待結果**:
  - HTTPステータス: 200（Job作成成功）
  - `HTTP 404: Workflow '__PENDING__' not found`エラーが発生しないこと
- **curlコマンド**:
  ```bash
  # Job作成（TC-001で取得したJOB_MASTER_IDを使用）
  curl -s -X POST http://localhost:8001/api/v1/jobs \
    -H "Content-Type: application/json" \
    -d "{
      \"job_master_id\": \"$JOB_MASTER_ID\",
      \"body\": {
        \"keyword\": \"テストキーワード\"
      }
    }" | jq .
  ```
- **pytestメソッド**: `test_tc_002_job_run_no_pending_error`

### TC-003: 既存フィールド保持（タスクチェイニング）
- **テスト観点**: workflow更新時にinputs, project, job_paramsが保持されること
- **関連する受入条件**: AC-1
- **関連する設計方針**: DP-4
- **テスト種別**: E2E
- **テスト方法**: curl / pytest
- **前提条件**:
  1. TC-001が成功していること
- **テスト手順**:
  1. TaskMasterのbody_templateを取得
  2. inputs, project, job_paramsフィールドを確認
- **期待結果**:
  - inputsフィールドが存在すること（`{{job.body}}`または`{{tasks[n].output_data}}`）
  - projectフィールドが存在すること
  - job_paramsフィールドが存在すること
- **curlコマンド**:
  ```bash
  # TaskMasterの全フィールド確認
  curl -s "http://localhost:8001/api/v1/task-masters?job_master_id=$JOB_MASTER_ID" | \
    jq '.[] | {id, body_template: {workflow, inputs, project, job_params}}'
  ```
- **pytestメソッド**: `test_tc_003_existing_fields_preserved`

### TC-004: All-or-Nothing動作確認（障害注入）
- **テスト観点**: 一部更新失敗時に全体が失敗すること
- **関連する受入条件**: -
- **関連する設計方針**: DP-1
- **テスト種別**: 結合（モック使用）
- **テスト方法**: pytest
- **前提条件**:
  1. モック環境でのテスト
- **テスト手順**:
  1. 2件のTaskMaster更新をシミュレート
  2. 1件目は成功、2件目は失敗を設定
  3. OrchestratorErrorが発生することを確認
- **期待結果**:
  - OrchestratorErrorが発生すること
  - エラーメッセージに失敗したtask_idが含まれること
- **pytestメソッド**: `test_tc_004_all_or_nothing_failure`
  (Note: この項目は既存の`test_update_task_masters_partial_failure_raises_error`でカバー)

### TC-005: 循環参照なしでの起動確認
- **テスト観点**: ローカルインポートパターンで循環参照が発生しないこと
- **関連する受入条件**: -
- **関連する設計方針**: DP-2
- **テスト種別**: 単体
- **テスト方法**: python import
- **前提条件**:
  1. 実装完了後
- **テスト手順**:
  1. orchestrator.pyをインポート
  2. エラーなくインポートできることを確認
- **期待結果**:
  - ImportError/CircularImportErrorが発生しないこと
- **コマンド**:
  ```bash
  cd expertAgent
  uv run python -c "from aiagent.langgraph.jobGeneratorV2.orchestrator import JobGenerationOrchestrator; print('Import OK')"
  ```
- **pytestメソッド**: N/A（起動確認のみ）

### TC-006: 単体テスト全パス確認
- **テスト観点**: test_orchestrator_issue390.pyの全テストがパスすること
- **関連する受入条件**: AC-3
- **関連する設計方針**: -
- **テスト種別**: CI確認
- **テスト方法**: pytest
- **前提条件**:
  1. skipマークが解除されていること
- **テスト手順**:
  1. 単体テストを実行
- **期待結果**:
  - 全9件のテストがパス
  - skippedが0件
- **コマンド**:
  ```bash
  cd expertAgent
  uv run pytest tests/unit/test_job_generator_v2/test_orchestrator_issue390.py -v
  ```
- **pytestメソッド**: N/A（CI実行）

### TC-007: 結合テスト全パス確認
- **テスト観点**: test_issue390_integration.pyの全テストがパスすること
- **関連する受入条件**: AC-4
- **関連する設計方針**: -
- **テスト種別**: CI確認
- **テスト方法**: pytest
- **前提条件**:
  1. skipマークが解除されていること
- **テスト手順**:
  1. 結合テストを実行
- **期待結果**:
  - 全7件のテストがパス
  - skippedが0件
- **コマンド**:
  ```bash
  cd expertAgent
  uv run pytest tests/integration/test_issue390_integration.py -v
  ```
- **pytestメソッド**: N/A（CI実行）

---

## 10. テスト実行計画

### 実行順序
1. **サービス起動確認（ヘルスチェック）**
   ```bash
   curl -sf http://localhost:8004/health && echo "expertAgent OK"
   curl -sf http://localhost:8001/api/v1/health && echo "JobQueue OK"
   curl -sf http://localhost:8003/health && echo "myVault OK"
   curl -sf http://localhost:8006/health && echo "mySwiftAgentCore OK"
   ```

2. **TC-005: 循環参照なしでの起動確認**（インポートテスト）

3. **TC-006: 単体テスト全パス確認**（CI実行）

4. **TC-007: 結合テスト全パス確認**（CI実行）

5. **TC-001: TaskMaster workflow更新**（E2E）

6. **TC-003: 既存フィールド保持**（E2E、TC-001の結果を使用）

7. **TC-002: Job Run正常実行**（E2E、TC-001の結果を使用）

### 成功基準
- [ ] TC-001がパス（TaskMaster workflowが更新される）
- [ ] TC-002がパス（Job Runで404エラーが発生しない）
- [ ] TC-003がパス（既存フィールドが保持される）
- [ ] TC-005がパス（循環参照エラーなし）
- [ ] TC-006がパス（単体テスト全件パス、skipped=0）
- [ ] TC-007がパス（結合テスト全件パス、skipped=0）
- [ ] デッドコードが検出されないこと（F-1, F-2の呼び出し確認）

---

## 11. 受入テストファイル計画

### ファイル配置
```
expertAgent/tests/acceptance/test_issue_396_acceptance.py
```

### テストメソッド構成
```python
"""Acceptance tests for Issue #396: TaskMaster workflow update after Phase 3.

Run with:
    cd expertAgent
    uv run pytest tests/acceptance/test_issue_396_acceptance.py -v -s
"""

import pytest

@pytest.mark.acceptance
class TestIssue396Acceptance:
    """E2E acceptance tests for Issue #396."""

    async def test_tc_001_taskmaster_workflow_updated(self):
        """TC-001: TaskMaster workflow is updated after Job Generate."""
        pass

    async def test_tc_002_job_run_no_pending_error(self):
        """TC-002: Job Run succeeds without __PENDING__ error."""
        pass

    async def test_tc_003_existing_fields_preserved(self):
        """TC-003: Existing body_template fields are preserved."""
        pass
```

---

## 12. 補足事項

### Issue #390 との関係
本Issueは、Issue #390で特定された4つの問題のうち、問題#4（TaskMaster workflow更新の欠落）のみを修正します。問題1-3はIssue #390で既に修正済みです。

### 準備済みリソース
Issue #390で以下が既に準備されています：
- 単体テスト（skipマーク付き）: `test_orchestrator_issue390.py`
- 結合テスト（skipマーク付き）: `test_issue390_integration.py`
- 更新関数: `update_task_master_body_template_taskflow`

これらのリソースを活用し、skipマークを解除してテストを実行します。

### 既知の制限事項
- TC-004（All-or-Nothing障害注入）はモック環境でのみ実行可能
- E2Eテストには実際のLLM呼び出しが含まれるため、APIキーが必要

---

**作成日**: 2026-01-23
**作成者**: acceptance-plan-agent (Claude Opus 4.5)
**対象Issue**: #396
**関連Issue**: #390（問題#4）、#360（All-or-Nothing要件）

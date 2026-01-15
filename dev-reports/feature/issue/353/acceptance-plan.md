# 受入テスト計画書

**Issue**: #353
**作成日**: 2026-01-12
**作成者**: acceptance-plan-agent

---

## 1. 概要

### 対象Issue
- **番号**: #353
- **タイトル**: Job Generator V2: WORKFLOW_GEN フェーズ未完了時に __PENDING__ プレースホルダーが残存しジョブ実行失敗
- **プロジェクト**: expertAgent
- **関連プロジェクト**: jobqueue, myAgentDesk

### 参照ドキュメント
- Issue: #353
- 設計方針書: `dev-reports/feature/issue/353/design-policy.md`
- 作業計画書: `dev-reports/feature/issue/353/work-plan.md`

### 問題概要
Job Generator V2でジョブを生成した際、WORKFLOW_GENフェーズが正常に完了しない場合、TaskMasterの`workflow_name`にプレースホルダー`__PENDING__`が残存し、ジョブ実行時に`Workflow '__PENDING__' not found`エラーが発生する。

---

## 2. 単体テスト結果レビュー

### ステータス
- **フェーズ**: PRE-TDD（TDD実装前）
- **単体テストレビュー**: TDD実装後に実施予定

### TDD実装後の確認項目
| 項目 | 確認内容 | 判定基準 |
|------|---------|---------|
| カバレッジ | 単体テストカバレッジ | 90%以上 |
| テスト数 | 実装した機能に対するテスト数 | 各機能に最低1テスト |
| 静的解析 | Ruff/MyPyエラー | 0件 |
| モック使用率 | モック使用の割合 | 過剰でないこと |

### 予定される単体テストファイル
- `expertAgent/tests/unit/test_pending_workflow_validator.py`
- `expertAgent/tests/unit/test_workflow_gen_retry.py`
- `expertAgent/tests/unit/test_error_notification.py`

---

## 3. 受入条件分析

### AC-1: WORKFLOW_GEN フェーズ失敗時のエラーハンドリング
- **原文**: WORKFLOW_GEN フェーズ失敗時に適切なエラーハンドリング
- **分類**: 機能要件
- **テスト方法**: curl / pytest
- **モック使用**: 一部可（GraphAiServerを停止して異常系テスト）
- **検証ポイント**:
  1. WORKFLOW_GENフェーズ失敗時にエラーが適切にキャッチされる
  2. リトライが設定回数（最大3回）まで実行される
  3. Exponential backoffでリトライ間隔が増加する
  4. 最終的な失敗時に適切なエラーメッセージが返却される

### AC-2: __PENDING__ バリデーション
- **原文**: `__PENDING__` が残った状態で FINALIZATION に進まないバリデーション追加
- **分類**: 機能要件
- **テスト方法**: curl / pytest
- **モック使用**: 不可（実サービス連携で検証）
- **検証ポイント**:
  1. `PendingWorkflowValidator`がFINALIZATION前に実行される
  2. `__PENDING__`が検出された場合、ジョブ生成が失敗ステータスになる
  3. 検出されたTaskMaster IDが`pending_workflows`フィールドに含まれる
  4. `ErrorType.INCOMPLETE_WORKFLOW`エラーが発生する

### AC-3: UI表示
- **原文**: ジョブ生成 UI で WORKFLOW_GEN 失敗を明示的に表示
- **分類**: UI要件（expertAgent API拡張が対象）
- **テスト方法**: curl / pytest
- **モック使用**: 不可（APIレスポンス確認）
- **検証ポイント**:
  1. `/api/v1/jobs/{job_id}/status`に`notification`フィールドが含まれる
  2. `notification.level`が`error`または`critical`に設定される
  3. `notification.message`にわかりやすいエラー説明が含まれる
  4. `notification.suggested_actions`に推奨アクションが含まれる
  5. `pending_workflows`フィールドに未完了タスク情報が含まれる

### AC-4: 既存データ修復手段
- **原文**: 既存の `__PENDING__` ジョブの検出・修復手段の提供
- **分類**: 機能要件
- **テスト方法**: curl / pytest
- **モック使用**: 不可（実データ検出を確認）
- **検証ポイント**:
  1. `__PENDING__`が残存しているTaskMasterを検出できる
  2. 検出結果がAPI経由で取得できる
  3. 再試行機能が提供される（Phase 3: オプション機能）

---

## 4. 設計方針検証

### DP-1: PendingWorkflowValidator実装
- **設計方針**: Chain of Responsibilityパターンを継続し、ValidationPipelineに新規バリデーターを追加
- **検証方法**: コード構造確認 / APIテスト
- **テスト項目**:
  1. `PendingWorkflowValidator`クラスが`ValidationProtocol`を実装している
  2. バリデーターがFINALIZATION前のタイミングで実行される
  3. 全TaskMasterの`workflow_name`を検証する

### DP-2: ErrorType拡張
- **設計方針**: 既存の6種類に`INCOMPLETE_WORKFLOW`を追加
- **検証方法**: コード確認 / APIレスポンス検証
- **テスト項目**:
  1. `ErrorType.INCOMPLETE_WORKFLOW`が`protocols.py`に定義されている
  2. エラー発生時に適切なErrorTypeが設定される
  3. 既存のErrorTypeとの互換性が保たれている

### DP-3: WorkflowGenRetryConfig
- **設計方針**: WORKFLOW_GEN専用のリトライ設定（exponential backoff）
- **検証方法**: ログ確認 / 時間測定
- **テスト項目**:
  1. `max_retries`が設定値（デフォルト3）に従う
  2. `base_delay_seconds`（1.0秒）からexponential backoffで増加
  3. `max_delay_seconds`（30.0秒）を超えない
  4. タイムアウト設定が適用される（LLM: 120秒、登録: 30秒）

### DP-4: ErrorNotificationモデル
- **設計方針**: エラー通知用データモデルの定義
- **検証方法**: APIレスポンス確認
- **テスト項目**:
  1. `notification`フィールドがAPIレスポンスに含まれる
  2. `level`, `title`, `message`, `details`フィールドが含まれる
  3. `suggested_actions`, `can_retry`, `requires_user_action`が含まれる
  4. `langfuse_trace_id`が含まれる（トレーシング有効時）

### DP-5: API拡張
- **設計方針**: `/api/v1/jobs/{job_id}/status`のレスポンス拡張
- **検証方法**: curl / pytest
- **テスト項目**:
  1. 既存フィールド（status, progress, phase）が保持される
  2. `notification`フィールドが追加される
  3. `pending_workflows`フィールドが追加される
  4. 正常系では`notification`と`pending_workflows`が`null`

---

## 5. デッドコード検証計画

### F-1: PendingWorkflowValidator
- **ファイル**: `expertAgent/aiagent/langgraph/jobGeneratorV2/validators/pending_workflow.py`
- **種別**: class
- **期待される呼び出し元**:
  - `JobGenerationOrchestrator._can_proceed_to_finalization()`
  - `ValidationPipeline`
- **検証方法**:
  ```bash
  grep -rn "PendingWorkflowValidator" --include="*.py" expertAgent/
  ```
- **E2E確認**: WORKFLOW_GEN失敗時のジョブ生成でエラーが発生することを確認

### F-2: ErrorType.INCOMPLETE_WORKFLOW
- **ファイル**: `expertAgent/aiagent/langgraph/jobGeneratorV2/protocols.py`
- **種別**: constant (Enum value)
- **期待される呼び出し元**:
  - `PendingWorkflowValidator.validate()`
  - `ErrorRecoveryManager`
- **検証方法**:
  ```bash
  grep -rn "INCOMPLETE_WORKFLOW" --include="*.py" expertAgent/
  ```
- **E2E確認**: エラーレスポンスに`INCOMPLETE_WORKFLOW`タイプが含まれることを確認

### F-3: WorkflowGenRetryConfig
- **ファイル**: `expertAgent/aiagent/langgraph/jobGeneratorV2/retry/workflow_gen_retry.py`
- **種別**: dataclass
- **期待される呼び出し元**:
  - `WorkflowGenWorkflow`
  - `calculate_retry_delay()`
- **検証方法**:
  ```bash
  grep -rn "WorkflowGenRetryConfig" --include="*.py" expertAgent/
  ```
- **E2E確認**: リトライ発生時にexponential backoffが適用されることを確認

### F-4: ErrorNotification
- **ファイル**: `expertAgent/aiagent/langgraph/jobGeneratorV2/protocols.py` または `expertAgent/app/models/`
- **種別**: dataclass
- **期待される呼び出し元**:
  - Job Status APIエンドポイント
  - `NotificationService`
- **検証方法**:
  ```bash
  grep -rn "ErrorNotification" --include="*.py" expertAgent/
  ```
- **E2E確認**: APIレスポンスの`notification`フィールドにデータが含まれることを確認

### F-5: calculate_retry_delay関数
- **ファイル**: `expertAgent/aiagent/langgraph/jobGeneratorV2/retry/workflow_gen_retry.py`
- **種別**: function
- **期待される呼び出し元**:
  - `WorkflowGenWorkflow.execute()`
  - リトライロジック
- **検証方法**:
  ```bash
  grep -rn "calculate_retry_delay" --include="*.py" expertAgent/
  ```
- **E2E確認**: リトライログで遅延時間が増加していることを確認

### F-6: execute_with_timeout関数
- **ファイル**: `expertAgent/aiagent/langgraph/jobGeneratorV2/retry/workflow_gen_retry.py`
- **種別**: function
- **期待される呼び出し元**:
  - `WorkflowGenWorkflow.execute()`
  - LLM/GraphAiServer呼び出し
- **検証方法**:
  ```bash
  grep -rn "execute_with_timeout" --include="*.py" expertAgent/
  ```
- **E2E確認**: タイムアウト発生時に適切なエラーが返却されることを確認

---

## 6. テスト環境

### 必須サービス
| サービス | URL | ヘルスチェック |
|---------|-----|--------------|
| expertAgent | http://localhost:8004 | GET /health |
| jobqueue | http://localhost:8001 | GET /health |
| graphAiServer | http://localhost:8005 | GET /health |
| myVault | http://localhost:8003 | GET /health |
| Langfuse | http://localhost:3001 | GET / |

### 起動コマンド
```bash
# 推奨: ハイブリッドモード（Platform=Docker, Agent=ローカル）
./scripts/dev-hybrid.sh

# または: Docker全環境
make dev-all
```

### ヘルスチェック確認
```bash
curl -sf http://localhost:8001/health && echo "JobQueue healthy"
curl -sf http://localhost:8003/health && echo "MyVault healthy"
curl -sf http://localhost:8004/health && echo "ExpertAgent healthy"
curl -sf http://localhost:8005/health && echo "GraphAiServer healthy"
```

### 環境変数
| 変数名 | 説明 | 必須 |
|--------|------|------|
| OPENAI_API_KEY | OpenAI APIキー | 必須 |
| ANTHROPIC_API_KEY | Anthropic APIキー | 任意（LLM選択による） |
| LANGFUSE_SECRET_KEY | Langfuseシークレットキー | 任意（トレーシング時） |
| LANGFUSE_PUBLIC_KEY | Langfuse公開キー | 任意（トレーシング時） |

### テストデータ準備
- 正常系テスト: 簡単なジョブ要件（例: "CSVファイルを読み込んでExcelに出力する"）
- 異常系テスト: GraphAiServerを停止してWORKFLOW_GEN失敗を誘発

---

## 7. テスト項目

### TC-001: 正常系 - ジョブ生成成功
- **テスト観点**: 正常なジョブ生成で`__PENDING__`が正しく更新される
- **関連する受入条件**: AC-2
- **関連する設計方針**: DP-1
- **テスト種別**: E2E
- **テスト方法**: curl / pytest
- **前提条件**:
  1. 全サービスが起動している
  2. 環境変数が設定されている
- **テスト手順**:
  1. `/api/v1/job-generator`にジョブ生成リクエストを送信
  2. レスポンスから`job_id`を取得
  3. ジョブ完了まで`/api/v1/jobs/{job_id}/status`をポーリング
  4. 完了後、JobQueueからTaskMaster情報を取得
  5. `workflow_name`が`__PENDING__`でないことを確認
- **期待結果**:
  - HTTPステータス: 200
  - `status`: "completed"
  - TaskMasterの`workflow_name`が実際のワークフロー名
  - `notification`: null（正常系）
  - `pending_workflows`: null（正常系）
- **curlコマンド**:
  ```bash
  # Step 1: ジョブ生成
  JOB_RESPONSE=$(curl -s -X POST http://localhost:8004/api/v1/job-generator \
    -H "Content-Type: application/json" \
    -d '{
      "user_requirement": "CSVファイルを読み込んでExcelに出力する"
    }')
  echo $JOB_RESPONSE | jq .

  # Step 2: ジョブIDを取得
  JOB_ID=$(echo $JOB_RESPONSE | jq -r '.job_id')

  # Step 3: ステータス確認（ポーリング）
  curl -s http://localhost:8004/api/v1/jobs/$JOB_ID/status | jq .

  # Step 4: TaskMaster確認（JobMasterIDが取得できたら）
  JOB_MASTER_ID=$(echo $JOB_RESPONSE | jq -r '.job_master_id')
  curl -s http://localhost:8001/api/v1/job-masters/$JOB_MASTER_ID | jq '.tasks[].body_template.workflow_name'
  ```
- **pytestメソッド**: `test_tc_001_normal_job_generation`

### TC-002: 異常系 - GraphAiServerダウン時のエラーハンドリング
- **テスト観点**: GraphAiServerが利用不可の場合の適切なエラーハンドリング
- **関連する受入条件**: AC-1, AC-3
- **関連する設計方針**: DP-3, DP-4
- **テスト種別**: E2E
- **テスト方法**: curl / pytest
- **前提条件**:
  1. expertAgent, jobqueue, myVaultが起動している
  2. GraphAiServerが停止している
- **テスト手順**:
  1. GraphAiServerを停止
  2. `/api/v1/job-generator`にジョブ生成リクエストを送信
  3. `/api/v1/jobs/{job_id}/status`でステータス確認
  4. リトライが実行されていることをログで確認
  5. 最終的にエラーレスポンスが返却されることを確認
- **期待結果**:
  - HTTPステータス: 200（ステータスAPIは成功）
  - `status`: "failed" または "incomplete_workflow"
  - `notification.level`: "error" または "critical"
  - `notification.message`: エラー説明が含まれる
  - `pending_workflows`: 未完了タスク情報が含まれる
- **curlコマンド**:
  ```bash
  # Step 1: GraphAiServerを停止
  docker stop graphaiserver

  # Step 2: ジョブ生成
  JOB_RESPONSE=$(curl -s -X POST http://localhost:8004/api/v1/job-generator \
    -H "Content-Type: application/json" \
    -d '{
      "user_requirement": "PDFファイルを生成する"
    }')
  JOB_ID=$(echo $JOB_RESPONSE | jq -r '.job_id')

  # Step 3: ステータス確認
  curl -s http://localhost:8004/api/v1/jobs/$JOB_ID/status | jq .

  # Step 4: notification確認
  curl -s http://localhost:8004/api/v1/jobs/$JOB_ID/status | jq '.notification'

  # Step 5: pending_workflows確認
  curl -s http://localhost:8004/api/v1/jobs/$JOB_ID/status | jq '.pending_workflows'

  # Cleanup: GraphAiServerを再起動
  docker start graphaiserver
  ```
- **pytestメソッド**: `test_tc_002_graphai_server_down`

### TC-003: 異常系 - __PENDING__残存検出
- **テスト観点**: `__PENDING__`が残存している場合にFINALIZATIONに進まない
- **関連する受入条件**: AC-2
- **関連する設計方針**: DP-1, DP-2
- **テスト種別**: E2E
- **テスト方法**: curl / pytest
- **前提条件**:
  1. 全サービスが起動している
  2. テスト用のTaskMasterを作成済み
- **テスト手順**:
  1. TaskMasterを手動で作成（`workflow_name = "__PENDING__"`）
  2. PendingWorkflowValidatorを直接呼び出し（または該当APIを呼び出し）
  3. `__PENDING__`が検出されることを確認
  4. エラータイプが`INCOMPLETE_WORKFLOW`であることを確認
- **期待結果**:
  - バリデーションエラーが発生
  - `error_type`: "incomplete_workflow"
  - `pending_task_master_ids`に該当IDが含まれる
- **curlコマンド**:
  ```bash
  # テストデータ作成（TaskMasterに__PENDING__を設定）
  # 注: 実際のAPIパスは実装に依存
  curl -X POST http://localhost:8001/api/v1/task-masters \
    -H "Content-Type: application/json" \
    -d '{
      "name": "テスト用タスク",
      "body_template": {
        "workflow_name": "__PENDING__",
        "inputs": "{{job.body}}",
        "project": "{{job.project}}"
      }
    }'
  ```
- **pytestメソッド**: `test_tc_003_pending_detection`

### TC-004: リトライ動作確認 - Exponential Backoff
- **テスト観点**: リトライがexponential backoffで実行される
- **関連する受入条件**: AC-1
- **関連する設計方針**: DP-3
- **テスト種別**: E2E
- **テスト方法**: ログ確認 / 時間測定
- **前提条件**:
  1. GraphAiServerが断続的にエラーを返す状態（または停止状態）
  2. expertAgentのログが確認可能
- **テスト手順**:
  1. GraphAiServerを一時的に停止
  2. ジョブ生成リクエストを送信
  3. expertAgentのログでリトライ間隔を確認
  4. 間隔が1秒 -> 2秒 -> 4秒と増加していることを確認
- **期待結果**:
  - リトライが最大3回まで実行される
  - リトライ間隔がexponential backoffに従う（1s, 2s, 4s程度）
  - ログにリトライ情報が出力される
- **curlコマンド**:
  ```bash
  # Step 1: GraphAiServerを停止
  docker stop graphaiserver

  # Step 2: ジョブ生成（バックグラウンド実行）
  curl -s -X POST http://localhost:8004/api/v1/job-generator \
    -H "Content-Type: application/json" \
    -d '{"user_requirement": "テスト"}' &

  # Step 3: ログ確認
  docker logs -f expertagent 2>&1 | grep -E "retry|backoff|delay"

  # Cleanup
  docker start graphaiserver
  ```
- **pytestメソッド**: `test_tc_004_exponential_backoff`

### TC-005: API拡張確認 - notificationフィールド
- **テスト観点**: ステータスAPIのレスポンスに`notification`フィールドが含まれる
- **関連する受入条件**: AC-3
- **関連する設計方針**: DP-4, DP-5
- **テスト種別**: E2E
- **テスト方法**: curl / pytest
- **前提条件**:
  1. ジョブが作成されている（成功/失敗どちらでも）
- **テスト手順**:
  1. ジョブ生成を実行
  2. `/api/v1/jobs/{job_id}/status`を呼び出し
  3. レスポンス構造を確認
- **期待結果**:
  - 正常系: `notification`が`null`
  - 異常系: `notification`オブジェクトに以下が含まれる
    - `level`: "info" | "warning" | "error" | "critical"
    - `title`: 文字列
    - `message`: 文字列
    - `details`: オブジェクト
    - `suggested_actions`: 配列
    - `can_retry`: boolean
    - `requires_user_action`: boolean
    - `langfuse_trace_id`: 文字列またはnull
- **curlコマンド**:
  ```bash
  # ステータスAPIのレスポンス構造確認
  curl -s http://localhost:8004/api/v1/jobs/$JOB_ID/status | jq '{
    status: .status,
    progress: .progress,
    phase: .phase,
    notification: .notification,
    pending_workflows: .pending_workflows
  }'
  ```
- **pytestメソッド**: `test_tc_005_notification_field`

### TC-006: API拡張確認 - pending_workflowsフィールド
- **テスト観点**: `__PENDING__`検出時に`pending_workflows`フィールドに情報が含まれる
- **関連する受入条件**: AC-2, AC-4
- **関連する設計方針**: DP-5
- **テスト種別**: E2E
- **テスト方法**: curl / pytest
- **前提条件**:
  1. WORKFLOW_GENフェーズが失敗したジョブが存在する
- **テスト手順**:
  1. WORKFLOW_GEN失敗を誘発（TC-002と同様）
  2. `/api/v1/jobs/{job_id}/status`を呼び出し
  3. `pending_workflows`フィールドを確認
- **期待結果**:
  - `pending_workflows`に配列が含まれる
  - 各要素に以下が含まれる:
    - `task_master_id`: 文字列
    - `task_name`: 文字列
    - `body_template`: オブジェクト（`workflow_name: "__PENDING__"`を含む）
- **curlコマンド**:
  ```bash
  # pending_workflowsフィールド確認
  curl -s http://localhost:8004/api/v1/jobs/$JOB_ID/status | jq '.pending_workflows[] | {
    task_master_id,
    task_name,
    workflow_name: .body_template.workflow_name
  }'
  ```
- **pytestメソッド**: `test_tc_006_pending_workflows_field`

### TC-007: ErrorType確認 - INCOMPLETE_WORKFLOW
- **テスト観点**: `ErrorType.INCOMPLETE_WORKFLOW`が正しく使用される
- **関連する受入条件**: AC-1, AC-2
- **関連する設計方針**: DP-2
- **テスト種別**: 結合
- **テスト方法**: pytest
- **前提条件**:
  1. 新しいErrorTypeが実装されている
- **テスト手順**:
  1. `__PENDING__`を含むデータでバリデーションを実行
  2. 発生するエラーのタイプを確認
- **期待結果**:
  - `WorkflowError.error_type`が`ErrorType.INCOMPLETE_WORKFLOW`
  - エラーメッセージに`__PENDING__`に関する説明が含まれる
- **pytestメソッド**: `test_tc_007_incomplete_workflow_error_type`

### TC-008: Langfuseトレース確認
- **テスト観点**: エラー発生時にLangfuseトレースIDが含まれる
- **関連する受入条件**: AC-3
- **関連する設計方針**: DP-4
- **テスト種別**: E2E
- **テスト方法**: curl + Langfuse UI
- **前提条件**:
  1. Langfuseが起動している
  2. 環境変数が設定されている
- **テスト手順**:
  1. ジョブ生成を実行（エラーが発生するシナリオ）
  2. `/api/v1/jobs/{job_id}/status`を呼び出し
  3. `notification.langfuse_trace_id`を取得
  4. Langfuse UIでトレースを確認
- **期待結果**:
  - `langfuse_trace_id`が文字列で含まれる
  - Langfuse UIでトレースが確認できる
  - トレースにエラー情報が記録されている
- **curlコマンド**:
  ```bash
  # トレースID取得
  TRACE_ID=$(curl -s http://localhost:8004/api/v1/jobs/$JOB_ID/status | jq -r '.notification.langfuse_trace_id')
  echo "Langfuse Trace: http://localhost:3001/trace/$TRACE_ID"
  ```
- **pytestメソッド**: `test_tc_008_langfuse_trace`

---

## 8. テスト実行計画

### 実行順序
1. **環境準備**
   - サービス起動確認（ヘルスチェック）
   - 環境変数確認
2. **正常系テスト**
   - TC-001: 正常系ジョブ生成
3. **API構造確認**
   - TC-005: notificationフィールド
   - TC-006: pending_workflowsフィールド
4. **異常系テスト**
   - TC-002: GraphAiServerダウン
   - TC-003: __PENDING__残存検出
   - TC-007: ErrorType確認
5. **リトライ・タイムアウト確認**
   - TC-004: Exponential Backoff
6. **Observability確認**
   - TC-008: Langfuseトレース

### pytest実行コマンド
```bash
# 受入テスト全体実行
cd expertAgent
uv run pytest tests/acceptance/test_issue_353_acceptance.py -v

# 特定テストケース実行
uv run pytest tests/acceptance/test_issue_353_acceptance.py::test_tc_001_normal_job_generation -v
uv run pytest tests/acceptance/test_issue_353_acceptance.py::test_tc_002_graphai_server_down -v
```

### 成功基準
- [ ] TC-001: 正常系ジョブ生成がパス
- [ ] TC-002: GraphAiServerダウン時のエラーハンドリングがパス
- [ ] TC-003: __PENDING__残存検出がパス
- [ ] TC-004: Exponential Backoffが確認できる
- [ ] TC-005: notificationフィールドが存在する
- [ ] TC-006: pending_workflowsフィールドが存在する
- [ ] TC-007: INCOMPLETE_WORKFLOW ErrorTypeが使用される
- [ ] TC-008: Langfuseトレースが記録される
- [ ] すべての受入条件（AC-1〜AC-4）が検証済み
- [ ] デッドコードが検出されないこと（F-1〜F-6が実際に使用されている）

---

## 9. 補足事項

### 注意点
1. **GraphAiServer停止テスト**: TC-002, TC-004はGraphAiServerを停止するため、他のテストに影響しないよう順序に注意
2. **タイムアウト考慮**: リトライテスト（TC-004）は数分かかる可能性があるため、十分なタイムアウトを設定
3. **テストデータクリーンアップ**: TC-003で作成したテストデータは終了後にクリーンアップ

### 今後の検討事項
- myAgentDesk UIでの通知表示テスト（Playwright）は別Issue（Phase 3オプション）
- 自動修復機能のテストは実装後に追加

### 関連Issue
- Issue #342: Job Generator V2 基盤実装
- Issue #353: 本Issue（WORKFLOW_GEN フェーズ未完了時のエラーハンドリング改善）

# 受入テスト計画書

**Issue**: #386
**作成日**: 2025-01-21
**作成者**: acceptance-plan skill

---

## 1. 概要

### 対象Issue
- **番号**: #386
- **タイトル**: 【P1】Phase 2統合: master_manager + BodyTemplateValidator + trace_id伝播
- **プロジェクト**: expertAgent

### 参照ドキュメント
- Issue: #386
- 設計方針書: `dev-reports/feature/issue/386/design-policy.md`
- 作業計画書: `dev-reports/feature/issue/386/work-plan.md`

### 実装概要
- Phase 2（REGISTRATION）の完全実装
- 現在のプレースホルダー実装を、実際のjobqueue API呼び出しに置き換え
- MasterManagerSubWorkflowを活用
- BodyTemplateValidatorによる検証統合
- trace_idの伝播実装

---

## 2. 単体テスト結果レビュー

### カバレッジ
- 現在: TDD未実施（PM Auto-Dev Phase 1で実装予定）
- 目標: 90%
- 判定: ⏳ 未評価

### テスト品質評価
| 指標 | 値 | 判定 |
|------|-----|------|
| 総テスト数 | TBD | - |
| モック使用テスト数 | TBD | - |
| モック使用率 | TBD | ⏳ |
| 実API呼び出しテスト数 | TBD | - |

### モック使用の妥当性
- 単体テストでは外部APIのモックは許容
- MasterManagerSubWorkflow呼び出しはモックで検証
- 実際のDB登録は受入テストで検証

### 単体テストでカバーされるべき項目
1. orchestrator._execute_registration のMasterManagerSubWorkflow呼び出し
2. run_workflowのtrace_id/parent_span_idパラメータ受け渡し
3. task_id → task_master_id マッピングの正確性
4. エラーケース（jobqueue接続失敗、バリデーションエラー）

---

## 3. 受入条件分析

### AC-1: master_manager統合 - 実際のDB登録
- **原文**: jobqueue APIで実際にJobMaster/TaskMasterが作成される
- **分類**: 機能要件
- **テスト方法**: curl + pytest
- **モック使用**: 不可（実サービス必須）
- **検証ポイント**:
  1. JobMasterがjobqueue DBに登録される
  2. TaskMasterが各タスク分登録される
  3. InterfaceMasterが入出力分登録される
  4. task_master_idが実際のDBレコードIDになる

### AC-2: master_manager統合 - エラー処理
- **原文**: 登録失敗時は適切なエラー処理
- **分類**: 機能要件
- **テスト方法**: pytest（モック+実サービス停止）
- **モック使用**: 一部可（サービス停止シミュレーション）
- **検証ポイント**:
  1. jobqueue接続エラー時にOrchestratorErrorが発生
  2. エラーメッセージにjobqueue接続失敗が含まれる
  3. エラー時はPhase 3に進まない（Fail-Fast）

### AC-3: BodyTemplateValidator統合
- **原文**: インターフェース定義がvalidator経由で検証される
- **分類**: 機能要件
- **テスト方法**: pytest
- **モック使用**: 一部可（LLMレスポンスのモック）
- **検証ポイント**:
  1. MasterManagerSubWorkflow内でBodyTemplateValidatorが呼び出される
  2. 無効なインターフェースで適切なエラーが発生

### AC-4: trace_id伝播
- **原文**: run_workflow()がtrace_id, parent_span_idを受け取り、Phase 3に渡される
- **分類**: 機能要件
- **テスト方法**: pytest + curl + ログ確認
- **モック使用**: 不可（Langfuse連携確認必須）
- **検証ポイント**:
  1. run_workflow()がtrace_id, parent_span_idパラメータを受け取る
  2. Phase 3のgenerate_workflows()にtrace_idが渡される
  3. Langfuseでトレースが連続して表示される
  4. Phase 1, 2, 3すべてのログにtrace_idが出力される

---

## 4. 設計方針検証

### DP-1: アーキテクチャ整合性
- **設計方針**: MasterManagerSubWorkflowの再利用
- **検証方法**: コード構造確認 + APIテスト
- **テスト項目**:
  1. orchestrator._execute_registration内でMasterManagerSubWorkflow.create_mastersが呼び出される
  2. ExecutionContextがMasterManagerSubWorkflowに渡される

### DP-2: Unified ID Pattern遵守
- **設計方針**: task_idを全フェーズで一貫使用、インデックスベースの参照を禁止
- **検証方法**: コードレビュー + APIテスト
- **テスト項目**:
  1. Phase 2の登録でtask_idがそのまま使用される
  2. Phase 3への引き継ぎでtask_idベースのマッピングが使用される

### DP-3: Fail-Fast Pattern
- **設計方針**: エラー時は即座に例外をraise、サイレントフォールバックなし
- **検証方法**: エラーケーステスト
- **テスト項目**:
  1. jobqueue接続エラー時にOrchestratorErrorが即座にraise
  2. BodyTemplateValidator検証エラー時にOrchestratorErrorが即座にraise

### DP-4: Dependency Injection Pattern
- **設計方針**: ExecutionContext経由で依存性注入
- **検証方法**: コード構造確認
- **テスト項目**:
  1. JobqueueClientがExecutionContext.storageから取得される
  2. MasterManagerSubWorkflowにcontextが渡される

---

## 5. デッドコード検証計画

### F-1: _execute_registration実装
- **ファイル**: `expertAgent/aiagent/langgraph/jobGeneratorV2/orchestrator.py`
- **種別**: method
- **期待される呼び出し元**: `JobGenerationOrchestrator.run_workflow`
- **検証方法**:
  ```bash
  grep -rn "_execute_registration" expertAgent/ --include="*.py" | grep -v "def _execute_registration"
  ```
- **E2Eでの確認方法**: Job Generator API呼び出しでPhase 2が実行されることを確認

### F-2: trace_idパラメータ
- **ファイル**: `expertAgent/aiagent/langgraph/jobGeneratorV2/orchestrator.py`
- **種別**: parameter
- **期待される呼び出し元**: adapter.py または FastAPIエンドポイント
- **検証方法**:
  ```bash
  grep -rn "trace_id" expertAgent/ --include="*.py" | head -50
  ```
- **E2Eでの確認方法**: X-Trace-Idヘッダー付きリクエストでログにtrace_idが出力されることを確認

### F-3: MasterManagerSubWorkflow呼び出し
- **ファイル**: `expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/registration/master_manager.py`
- **種別**: class/method
- **期待される呼び出し元**: orchestrator._execute_registration
- **検証方法**:
  ```bash
  grep -rn "MasterManagerSubWorkflow" expertAgent/ --include="*.py" | grep -v "class MasterManagerSubWorkflow"
  ```
- **E2Eでの確認方法**: Job生成後にjobqueue DBにマスターレコードが作成されることを確認

---

## 6. コンポーネント間整合性検証

### CI-1: orchestrator ↔ MasterManagerSubWorkflow整合性
- **検証対象**: _execute_registrationとMasterManagerSubWorkflow.create_mastersの引数/戻り値
- **確認項目**:
  - [ ] 引数の型が一致している（tasks, interfaces, project_id）
  - [ ] 戻り値のマッピングが正しい（task_id → task_master_id）
  - [ ] ExecutionContextが正しく渡される

### CI-2: MasterManagerSubWorkflow ↔ BodyTemplateValidator整合性
- **検証対象**: body_template検証の呼び出し
- **確認項目**:
  - [ ] MasterManagerSubWorkflow内でBodyTemplateValidator.validateが呼び出される
  - [ ] 検証エラー時の例外伝播が正しい

### CI-3: orchestrator ↔ adapter整合性
- **検証対象**: trace_idパラメータの伝播
- **確認項目**:
  - [ ] adapter.pyがrun_workflowにtrace_idを渡す
  - [ ] FastAPIエンドポイントがX-Trace-Idヘッダーを取得してadapterに渡す

---

## 7. サービス間データフロー検証

### DF-1: データフロー完全性

| 送信元 | データ項目 | 送信先 | 取得方法 | 検証状態 |
|--------|-----------|--------|---------|---------|
| orchestrator | tasks, interfaces | MasterManagerSubWorkflow | メソッド引数 | ??? |
| MasterManagerSubWorkflow | JobMaster/TaskMaster | jobqueue API | HTTP POST | ??? |
| orchestrator | trace_id | mySwiftAgentCore | HTTPヘッダー | ??? |

**検証方法**:
```bash
# パラメータの取得・設定箇所を確認
grep -rn "trace_id\s*=" expertAgent/ --include="*.py"
grep -rn "X-Trace-Id" expertAgent/ --include="*.py"
```

### DF-2: 空配列/null検証【禁止パターン検出】

テストデータが「空」「null」を正常ケースとして扱っていないか確認：

| 検出パターン | 検証 |
|------------|------|
| tasks=[] | ❌ 本番では空でない |
| interfaces={} | ❌ 本番では空でない |
| trace_id=None | ⚠️ オプショナルだが検証必要 |

### DF-3: サービス連携の全データ項目テスト

| サービス連携 | 必須データ項目 | テスト有無 |
|-------------|--------------|----------|
| orchestrator→MasterManager | tasks | ✅必須 |
| orchestrator→MasterManager | interfaces | ✅必須 |
| orchestrator→MasterManager | project_id | ✅必須 |
| MasterManager→jobqueue | JobMaster | ✅必須 |
| MasterManager→jobqueue | TaskMaster | ✅必須 |
| MasterManager→jobqueue | InterfaceMaster | ✅必須 |

---

## 8. テスト環境

### 必須サービス
| サービス | URL | ヘルスチェック |
|---------|-----|--------------|
| jobqueue | http://localhost:8101 | GET /health |
| expertAgent | http://localhost:8104 | GET /health |
| myVault | http://localhost:8003 | GET /health |
| mySwiftAgentCore | http://localhost:8006 | GET /health |

### 起動コマンド

**E2Eテスト用**:
```bash
# 1. 既存サービスを停止
./scripts/dev-hybrid.sh stop --local-only

# 2. Platform層をDocker、Agent層をローカルで起動
./scripts/dev-hybrid.sh start
```

### 環境変数
| 変数名 | 説明 | 必須 |
|--------|------|------|
| JOBQUEUE_API_TOKEN | jobqueue API認証トークン | ✅ |
| MYVAULT_ENABLED | MyVault有効化フラグ | ✅ (true) |
| MYVAULT_BASE_URL | MyVault URL | ✅ (http://localhost:8003) |
| OPENAI_API_KEY | OpenAI APIキー（LLM呼び出し用） | ✅ |

### テストデータ
- project_id: `test_project_386`
- trace_id: `test-trace-386-xxx`
- user_requirement: 「毎日朝9時にGmailをチェックしてSlackに通知」

---

## 9. テスト項目

### TC-001: 正常系 - Phase 2でマスター登録が成功
- **テスト観点**: MasterManagerSubWorkflow経由で実際にjobqueue APIが呼び出され、DB登録される
- **関連する受入条件**: AC-1
- **関連する設計方針**: DP-1, DP-2
- **テスト種別**: E2E
- **テスト方法**: curl + DB確認
- **前提条件**:
  1. jobqueueサービスが起動している
  2. expertAgentサービスが起動している
  3. LLM APIキーが設定されている
- **テスト手順**:
  1. Job Generator APIを呼び出す
  2. レスポンスでjob_master_idを取得
  3. jobqueue APIでJobMaster/TaskMasterの存在を確認
- **期待結果**:
  - HTTPステータス: 200
  - レスポンスに`job_master_id`が含まれる（`jm_`プレフィックスではなく実際のUUID）
  - jobqueueにJobMaster/TaskMaster/InterfaceMasterが登録される
- **curlコマンド**:
  ```bash
  # Job生成
  curl -s -X POST http://localhost:8104/v1/job-generator \
    -H "Content-Type: application/json" \
    -H "X-Trace-Id: test-trace-386-001" \
    -d '{
      "user_requirement": "毎日朝9時にGmailをチェックしてSlackに通知",
      "project_id": "test_project_386",
      "max_tasks": 3
    }'

  # JobMaster確認
  curl -s http://localhost:8101/api/v1/job-masters?project_id=test_project_386 \
    -H "X-API-Token: $JOBQUEUE_API_TOKEN" | jq '.items[0]'

  # TaskMaster確認
  curl -s http://localhost:8101/api/v1/task-masters?limit=10 \
    -H "X-API-Token: $JOBQUEUE_API_TOKEN" | jq '.items[] | {master_id, name}'
  ```
- **pytestメソッド**: `test_tc_001_phase2_master_registration_success`

### TC-002: 正常系 - trace_id伝播確認
- **テスト観点**: trace_idがHTTPヘッダー経由で全フェーズに伝播する
- **関連する受入条件**: AC-4
- **関連する設計方針**: DP-1
- **テスト種別**: E2E
- **テスト方法**: curl + ログ確認
- **前提条件**:
  1. 全サービスが起動している
  2. Langfuseが有効化されている
- **テスト手順**:
  1. X-Trace-Idヘッダー付きでJob Generator APIを呼び出す
  2. expertAgentログでtrace_idの出力を確認
  3. （可能であれば）Langfuseでトレースの連続性を確認
- **期待結果**:
  - Phase 1, 2, 3のログにtrace_idが出力される
  - Langfuseで連続したトレースとして確認できる
- **curlコマンド**:
  ```bash
  TRACE_ID="test-trace-$(date +%s)"
  curl -s -X POST http://localhost:8104/v1/job-generator \
    -H "Content-Type: application/json" \
    -H "X-Trace-Id: $TRACE_ID" \
    -d '{
      "user_requirement": "trace_idテスト",
      "project_id": "test_project_386"
    }'

  # ログ確認
  docker logs expertagent 2>&1 | grep "$TRACE_ID"
  ```
- **pytestメソッド**: `test_tc_002_trace_id_propagation`

### TC-003: 異常系 - jobqueueサービス停止時
- **テスト観点**: jobqueue接続エラー時にFail-Fastでエラー返却
- **関連する受入条件**: AC-2
- **関連する設計方針**: DP-3
- **テスト種別**: E2E（サービス停止）
- **テスト方法**: curl（サービス停止状態）
- **前提条件**:
  1. expertAgentサービスが起動している
  2. jobqueueサービスが停止している
- **テスト手順**:
  1. jobqueueサービスを停止
  2. Job Generator APIを呼び出す
  3. エラーレスポンスを確認
- **期待結果**:
  - HTTPステータス: 500または503
  - エラーメッセージにjobqueue接続失敗が含まれる
- **curlコマンド**:
  ```bash
  # jobqueue停止
  docker stop jobqueue

  # テスト実行
  curl -s -X POST http://localhost:8104/v1/job-generator \
    -H "Content-Type: application/json" \
    -d '{
      "user_requirement": "エラーテスト",
      "project_id": "test_project_386"
    }'

  # jobqueue再起動
  docker start jobqueue
  ```
- **pytestメソッド**: `test_tc_003_jobqueue_connection_error`

### TC-004: 異常系 - BodyTemplateValidator検証エラー
- **テスト観点**: 不正なbody_template時にバリデーションエラー
- **関連する受入条件**: AC-3
- **関連する設計方針**: DP-3
- **テスト種別**: 結合テスト（モック使用）
- **テスト方法**: pytest（LLMレスポンスをモック）
- **前提条件**:
  1. テスト用の不正なbody_templateを準備
- **テスト手順**:
  1. LLMレスポンスをモックで不正なbody_templateを返すよう設定
  2. orchestrator.run_workflowを呼び出す
  3. BodyTemplateValidatorでエラーが発生することを確認
- **期待結果**:
  - OrchestratorErrorが発生
  - エラーメッセージにバリデーションエラー内容が含まれる
- **pytestメソッド**: `test_tc_004_body_template_validation_error`

### TC-005: デッドコード検証 - MasterManagerSubWorkflow統合確認
- **テスト観点**: MasterManagerSubWorkflowが実際にorchestrator経由で呼び出される
- **関連する受入条件**: AC-1
- **関連する設計方針**: DP-1
- **テスト種別**: E2E
- **テスト方法**: grep + API呼び出し
- **前提条件**:
  1. 全サービスが起動している
- **テスト手順**:
  1. MasterManagerSubWorkflowの呼び出し箇所を確認
  2. Job Generator APIを呼び出す
  3. jobqueue DBにレコードが作成されることで統合を確認
- **期待結果**:
  - orchestrator._execute_registration内でMasterManagerSubWorkflowが呼び出される
  - 実際のDB登録が行われる
- **検証コマンド**:
  ```bash
  # 呼び出し箇所確認
  grep -rn "MasterManagerSubWorkflow" expertAgent/ --include="*.py" | grep -v "class MasterManagerSubWorkflow"

  # DB登録確認（TC-001と同様）
  ```
- **pytestメソッド**: `test_tc_005_master_manager_integration`

### TC-006: Phase間連携確認 - Phase 1 → Phase 2 → Phase 3
- **テスト観点**: 3フェーズが正しく連携し、task_idマッピングが引き継がれる
- **関連する受入条件**: AC-1, AC-4
- **関連する設計方針**: DP-2
- **テスト種別**: E2E
- **テスト方法**: curl + レスポンス検証
- **前提条件**:
  1. 全サービスが起動している
- **テスト手順**:
  1. Job Generator APIを呼び出す
  2. レスポンスでtask_breakdownとworkflow生成結果を確認
  3. task_idが一貫していることを確認
- **期待結果**:
  - Phase 1でtask_idが生成される
  - Phase 2でtask_idベースのmaster_idマッピングが作成される
  - Phase 3でtask_idベースのworkflowが生成される
- **pytestメソッド**: `test_tc_006_phase_flow_integration`

---

## 10. テスト実行計画

### 実行順序
1. サービス起動確認（ヘルスチェック）
2. TC-001: 正常系 - Phase 2でマスター登録が成功
3. TC-002: 正常系 - trace_id伝播確認
4. TC-005: デッドコード検証 - MasterManagerSubWorkflow統合確認
5. TC-006: Phase間連携確認
6. TC-003: 異常系 - jobqueueサービス停止時
7. TC-004: 異常系 - BodyTemplateValidator検証エラー

### 成功基準
- [ ] すべてのpytestテストがパス
- [ ] TC-001: JobMaster/TaskMasterがDBに登録される
- [ ] TC-002: trace_idがログに出力される
- [ ] TC-003: jobqueue停止時に適切なエラーが返される
- [ ] TC-004: バリデーションエラー時に適切なエラーが返される
- [ ] TC-005: MasterManagerSubWorkflowが実際に呼び出される
- [ ] TC-006: Phase間でtask_idが一貫している
- [ ] すべての受入条件（AC-1〜AC-4）が検証済み
- [ ] デッドコードが検出されないこと

---

## 11. 補足事項

### 注意点
1. **LLM呼び出し**: TC-001, TC-002, TC-006は実際のLLM呼び出しが発生するため、APIキーが必要
2. **テスト実行時間**: LLM呼び出しを含むテストは時間がかかる（1テスト30秒〜1分程度）
3. **テストデータクリーンアップ**: テスト後にjobqueueのテストデータを削除する必要がある

### 前提条件チェックリスト
- [ ] OPENAI_API_KEY が設定されている
- [ ] JOBQUEUE_API_TOKEN が設定されている
- [ ] dev-hybrid.sh でサービスが起動している
- [ ] jobqueue DBが初期化されている

### 参照ドキュメント
- Issue #359 3フェーズアーキテクチャ設計
- Issue #361 mySwiftAgentCore連携実装
- expertAgent API Reference: `/expertAgent/docs/API_REFERENCE.md`
- サービス依存関係: `/docs/arch/service-dependencies.md`

---

**作成日**: 2025-01-21
**作成者**: acceptance-plan skill
**対象Issue**: #386

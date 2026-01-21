# 受入テスト計画書

**Issue**: #385
**作成日**: 2026-01-21
**作成者**: acceptance-plan-agent
**フェーズ**: PRE-TDD (単体テスト実装前)

---

## 1. 概要

### 対象Issue
- **番号**: #385
- **タイトル**: 【P0】Capability取得・渡し + 空タスク検証の実装
- **プロジェクト**: expertAgent
- **優先度**: P0 (Critical)
- **ラベル**: `bug`, `cross-layer`

### 問題概要
1. **Capability取得・渡しが未実装**: `orchestrator.py L302`で常に`capabilities=[]`が渡されている
2. **空タスク検証が未実装**: 0タスク生成でも「成功」として処理が継続

### 参照ドキュメント
- Issue: #385
- 設計方針書: `dev-reports/feature/issue/385/design-policy.md`
- 作業計画書: `dev-reports/feature/issue/385/work-plan.md`

---

## 2. 単体テスト結果レビュー

### 現在の状況
- **フェーズ**: PRE-TDD (単体テスト未実装)
- 単体テスト結果レビューはTDD実装完了後に実施予定

### TDD実装後に確認すべき項目

| 指標 | 目標 | 確認方法 |
|------|------|---------|
| 総テスト数 | 各機能に最低1テスト | `pytest --co -q` |
| カバレッジ | 90%以上 | `pytest --cov` |
| モック使用率 | 適切（外部APIのみ） | `grep -c "@patch" tests/` |
| 静的解析 | エラー0件 | `ruff check && mypy` |

### 期待される単体テストファイル
- `expertAgent/tests/unit/test_clients/test_workflow_generator_client.py` - fetch_capabilities()テスト
- `expertAgent/tests/unit/test_langgraph/test_jobGeneratorV2/test_orchestrator.py` - 空タスク検証テスト
- `expertAgent/tests/unit/test_clients/test_log_sanitizer.py` - ログサニタイザーテスト

---

## 3. 受入条件分析

### AC-1: capabilities に実際のcapabilityリストが渡される
- **原文**: capabilities に実際のcapabilityリストが渡される
- **分類**: 機能要件
- **テスト方法**: E2E API呼び出し + ログ確認
- **モック使用**: 不可（実際のmySwiftAgentCore API呼び出し必須）
- **検証ポイント**:
  1. `WorkflowGeneratorClient.fetch_capabilities()`が実行される
  2. mySwiftAgentCore `/api/v1/capabilities` APIが呼び出される
  3. 取得したcapabilityが空でないことを確認
  4. capabilityが`generate_workflows()`に渡される

### AC-2: capability取得失敗時は明示的エラー
- **原文**: capability取得失敗時は明示的エラー
- **分類**: 機能要件（エラーハンドリング）
- **テスト方法**: E2E API呼び出し（異常系）
- **モック使用**: 一部可（mySwiftAgentCore停止状態のシミュレーション）
- **検証ポイント**:
  1. 存在しないproject_idで呼び出した場合のエラー
  2. mySwiftAgentCore接続エラー時の明示的エラー
  3. エラーメッセージに「capability」が含まれる

### AC-3: 0タスク時は OrchestratorError が発生
- **原文**: 0タスク時は OrchestratorError が発生
- **分類**: 機能要件（バリデーション）
- **テスト方法**: E2E API呼び出し（空要求）
- **モック使用**: 不可
- **検証ポイント**:
  1. 空の`user_requirement`で呼び出し
  2. 曖昧な要求で0タスクが生成される場合
  3. エラーレスポンスに「0 tasks」が含まれる

### AC-4: 単体テストカバレッジ90%以上
- **原文**: 単体テストカバレッジ90%以上
- **分類**: 非機能要件（品質）
- **テスト方法**: CIレポート確認
- **検証ポイント**:
  1. `pytest --cov`でカバレッジ計測
  2. 新規コードのカバレッジが90%以上

### AC-5: 結合テストで実際のcapabilityが渡されることを検証
- **原文**: 結合テストで実際のcapabilityが渡されることを検証
- **分類**: 機能要件（検証）
- **テスト方法**: 結合テスト + E2Eテスト
- **モック使用**: 不可
- **検証ポイント**:
  1. 実際のmySwiftAgentCore APIを呼び出し
  2. レスポンスにcapability情報が含まれる
  3. ワークフロー生成結果がcapabilityを反映

---

## 4. 設計方針検証

### DP-1: mySwiftAgentCore Capability API使用
- **設計方針**: `GET /api/v1/capabilities?project={project_id}` を使用
- **検証方法**: API呼び出し確認
- **テスト項目**:
  1. エンドポイント `/api/v1/capabilities` が呼び出される
  2. `project` パラメータが正しく渡される
  3. レスポンス形式が `{ "capabilities": [...], "count": N }` である

### DP-2: WorkflowGeneratorClient.fetch_capabilities()メソッド
- **設計方針**: WorkflowGeneratorClientに新規メソッドを追加
- **検証方法**: コード確認 + 単体テスト
- **テスト項目**:
  1. `fetch_capabilities(project_id)`メソッドが存在する
  2. 戻り値が `list[dict[str, Any]]` 形式である
  3. エラーハンドリングが実装されている

### DP-3: orchestrator.pyの_execute_workflow_gen()でcapability取得
- **設計方針**: ワークフロー生成時にcapabilityを取得して渡す
- **検証方法**: E2Eテスト + ログ確認
- **テスト項目**:
  1. `_execute_workflow_gen()`内でcapabilityが取得される
  2. `generate_workflows()`に空でないcapabilityが渡される
  3. ログに「capabilities=」が出力される（サニタイズ済み）

### DP-4: Guard Clause Patternで空タスク検証
- **設計方針**: `_validate_task_count()`メソッドで早期検証
- **検証方法**: 単体テスト + E2Eテスト
- **テスト項目**:
  1. `_validate_task_count()`メソッドが存在する
  2. タスク数0の場合に`OrchestratorError`が発生
  3. エラーメッセージに「0 tasks」が含まれる

### DP-5: log_sanitizer.pyでセンシティブ情報除外
- **設計方針**: ログ出力時に`_internal`, `secret_key`等を除外
- **検証方法**: ログ確認 + 単体テスト
- **テスト項目**:
  1. `sanitize_capability_for_log()`関数が存在する
  2. `_internal`キーが除外される
  3. `create_capability_log_summary()`でサマリ出力が可能

---

## 5. デッドコード検証計画

### F-1: WorkflowGeneratorClient.fetch_capabilities()
- **ファイル**: `expertAgent/aiagent/clients/workflow_generator_client.py`
- **種別**: function (新規追加予定)
- **期待される呼び出し元**: `orchestrator.py._execute_workflow_gen()`
- **検証方法**:
  ```bash
  grep -rn "fetch_capabilities" --include="*.py" expertAgent/
  ```
- **E2E確認**: Job Generator APIを呼び出し、capability取得が実行されることを確認

### F-2: orchestrator._validate_task_count()
- **ファイル**: `expertAgent/aiagent/langgraph/jobGeneratorV2/orchestrator.py`
- **種別**: function (新規追加予定)
- **期待される呼び出し元**: `_execute_job_analysis()`
- **検証方法**:
  ```bash
  grep -rn "_validate_task_count" --include="*.py" expertAgent/
  ```
- **E2E確認**: 空要求でエラーが発生することを確認

### F-3: log_sanitizer関数群
- **ファイル**: `expertAgent/aiagent/clients/utils/log_sanitizer.py`
- **種別**: module (新規追加予定)
- **期待される呼び出し元**: orchestrator.py, workflow_generator_client.py
- **検証方法**:
  ```bash
  grep -rn "sanitize_capability\|create_capability_log_summary" --include="*.py" expertAgent/
  ```
- **E2E確認**: ログ出力に`_internal`が含まれないことを確認

### F-4: CapabilityFetchError例外クラス
- **ファイル**: `expertAgent/aiagent/clients/workflow_generator_client.py`
- **種別**: class (新規追加予定)
- **期待される呼び出し元**: `fetch_capabilities()`のエラーハンドリング
- **検証方法**:
  ```bash
  grep -rn "CapabilityFetchError" --include="*.py" expertAgent/
  ```
- **E2E確認**: capability取得失敗時に適切な例外が発生

---

## 6. テスト環境

### 必須サービス

| サービス | URL | ヘルスチェック | 役割 |
|---------|-----|--------------|------|
| expertAgent | http://localhost:8004 | GET /health | Job Generator API |
| mySwiftAgentCore | http://localhost:8006 | GET /health | Capability API, Workflow Generator |
| myVault | http://localhost:8003 | GET /health | シークレット管理 |

### 起動コマンド（E2Eテスト用 - 必須）

**重要**: E2Eテストは以下の環境で実行すること。

```bash
# 1. 既存サービスを停止
./scripts/dev-hybrid.sh stop --local-only

# 2. ローカルモードでサービスを起動
./scripts/dev-hybrid.sh start --local-only
```

これにより:
- mySwiftAgentCore, expertAgent: ローカル直接起動
- myVault: Dockerコンテナで起動（default_projectを使用）

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
| MYSWIFTAGENT_CORE_URL | mySwiftAgentCore URL | (default: http://localhost:8006) |
| MYVAULT_ENABLED | MyVault有効化フラグ | true |
| MYVAULT_BASE_URL | MyVault URL | http://localhost:8003 |

---

## 7. コンポーネント間整合性検証

### CI-1: データフロー完全性

外部サービスに渡すデータの取得元が明確であることを確認:

| 送信元 | データ項目 | 送信先 | 取得方法 | 検証状態 |
|--------|-----------|--------|---------|---------|
| expertAgent | capabilities | mySwiftAgentCore | Capability API | 要検証 |
| expertAgent | trace_id | mySwiftAgentCore | Langfuse context | 既存実装 |
| expertAgent | project_id | mySwiftAgentCore | リクエストパラメータ | 既存実装 |

**検証方法**:
```bash
# パラメータの取得・設定箇所を確認
grep -rn "capabilities\s*=" --include="*.py" expertAgent/aiagent/
grep -rn "fetch_capabilities" --include="*.py" expertAgent/
```

### CI-2: 空配列/null検証【禁止パターン検出】

テストデータが「空」「null」を正常ケースとして扱っていないか確認:

| 検出パターン | 問題 | 対処 |
|------------|------|------|
| capabilities=[] | 本番では空でない | 実際のcapabilityを使用 |
| capabilities=None | 本番では必須 | エラーテストのみで使用可 |

**チェック方法**:
```bash
# テストファイルでの空配列/null使用を検出
grep -rn "capabilities.*=.*\[\]" expertAgent/tests/
grep -rn '"capabilities".*:.*\[\]' expertAgent/tests/
```

**禁止**: テストで空配列を正常ケースとして使用することは禁止。
本番で値が必須の場合、テストでも実際の値を使用すること。

### CI-3: サービス連携の全データ項目テスト

| サービス連携 | 必須データ項目 | テスト有無 |
|-------------|--------------|----------|
| expertAgent->mySwiftAgentCore | capabilities | TC-001で検証 |
| expertAgent->mySwiftAgentCore | trace_id | 既存テストで検証済み |
| expertAgent->mySwiftAgentCore | project_id | 既存テストで検証済み |

---

## 8. テスト項目

### TC-001: Capability取得正常系テスト
- **テスト観点**: mySwiftAgentCoreからcapabilityが正しく取得されるか
- **関連する受入条件**: AC-1
- **関連する設計方針**: DP-1, DP-2, DP-3
- **テスト種別**: E2E
- **テスト方法**: curl + pytest
- **前提条件**:
  1. mySwiftAgentCoreが起動している (localhost:8006)
  2. default_projectにcapabilityが登録されている
- **テスト手順**:
  1. mySwiftAgentCore Capability APIを直接呼び出し、capabilityが存在することを確認
  2. expertAgent Job Generator APIを呼び出し
  3. ログを確認し、capabilityが取得・渡されていることを検証
- **期待結果**:
  - Capability APIからcapabilityリストが返される（count > 0）
  - Job Generator処理が正常完了
  - ログに「capabilities=」が出力される（空でないこと）
- **curlコマンド**:
  ```bash
  # 1. Capability取得確認（mySwiftAgentCore直接）
  curl -s http://localhost:8006/api/v1/capabilities?project=default_project | jq '.capabilities | length'

  # 2. Job Generator呼び出し
  curl -s -X POST http://localhost:8004/v1/job-generator/generate \
    -H "Content-Type: application/json" \
    -d '{
      "user_requirement": "Gmailで未読メールをチェックして",
      "project_id": "default_project"
    }'
  ```
- **pytestメソッド**: `test_tc_001_capability_fetch_success`

### TC-002: Capability取得がワークフロー生成に渡される検証
- **テスト観点**: 取得したcapabilityがgenerate_workflows()に渡されるか
- **関連する受入条件**: AC-1, AC-5
- **関連する設計方針**: DP-3
- **テスト種別**: E2E
- **テスト方法**: pytest + ログ確認
- **前提条件**:
  1. 全サービスが起動している
  2. default_projectにcapabilityが登録されている
- **テスト手順**:
  1. Job Generator APIを呼び出し
  2. expertAgentのログを確認
  3. mySwiftAgentCoreへのリクエストボディを確認
- **期待結果**:
  - generate_workflows()に渡されるcapabilitiesが空でない
  - mySwiftAgentCoreへのリクエストにcapabilitiesが含まれる
- **curlコマンド**:
  ```bash
  curl -s -X POST http://localhost:8004/v1/job-generator/generate \
    -H "Content-Type: application/json" \
    -d '{
      "user_requirement": "Googleカレンダーの今日の予定を確認して",
      "project_id": "default_project"
    }' | jq '.workflows'
  ```
- **pytestメソッド**: `test_tc_002_capability_passed_to_workflow_gen`

### TC-003: Capability取得失敗時のエラーハンドリング
- **テスト観点**: capability取得失敗時に明示的エラーが返されるか
- **関連する受入条件**: AC-2
- **関連する設計方針**: DP-2
- **テスト種別**: E2E
- **テスト方法**: curl
- **前提条件**:
  1. expertAgentが起動している
  2. 存在しないproject_idを使用
- **テスト手順**:
  1. 存在しないproject_idでJob Generator APIを呼び出し
  2. エラーレスポンスを確認
- **期待結果**:
  - HTTPステータス: 4xx または 5xx
  - レスポンスにエラー情報が含まれる
  - エラーメッセージに「capability」が含まれる（大文字小文字不問）
- **curlコマンド**:
  ```bash
  curl -s -X POST http://localhost:8004/v1/job-generator/generate \
    -H "Content-Type: application/json" \
    -d '{
      "user_requirement": "テストタスク",
      "project_id": "non_existent_project_12345"
    }' | jq '.error'
  ```
- **pytestメソッド**: `test_tc_003_capability_fetch_error_handling`

### TC-004: 空タスク検証（空の要求）
- **テスト観点**: 空のuser_requirementで0タスク検証が機能するか
- **関連する受入条件**: AC-3
- **関連する設計方針**: DP-4
- **テスト種別**: E2E
- **テスト方法**: curl
- **前提条件**:
  1. expertAgentが起動している
- **テスト手順**:
  1. 空のuser_requirementでJob Generator APIを呼び出し
  2. エラーレスポンスを確認
- **期待結果**:
  - エラーレスポンスが返される
  - エラーメッセージに「0 tasks」または「empty」が含まれる
- **curlコマンド**:
  ```bash
  curl -s -X POST http://localhost:8004/v1/job-generator/generate \
    -H "Content-Type: application/json" \
    -d '{
      "user_requirement": "",
      "project_id": "default_project"
    }' | jq '.error'
  ```
- **pytestメソッド**: `test_tc_004_empty_task_validation_empty_requirement`

### TC-005: 空タスク検証（曖昧な要求）
- **テスト観点**: 曖昧な要求で0タスクが生成される場合の検証
- **関連する受入条件**: AC-3
- **関連する設計方針**: DP-4
- **テスト種別**: E2E
- **テスト方法**: curl
- **前提条件**:
  1. expertAgentが起動している
- **テスト手順**:
  1. 意味のない/曖昧なuser_requirementでJob Generator APIを呼び出し
  2. エラーまたは0タスク検証が発動することを確認
- **期待結果**:
  - エラーレスポンスが返される、または
  - タスク分析結果が空の場合にOrchestratorErrorが発生
- **curlコマンド**:
  ```bash
  curl -s -X POST http://localhost:8004/v1/job-generator/generate \
    -H "Content-Type: application/json" \
    -d '{
      "user_requirement": "あいうえお",
      "project_id": "default_project"
    }' | jq '.'
  ```
- **pytestメソッド**: `test_tc_005_empty_task_validation_ambiguous_requirement`

### TC-006: ログサニタイザー動作確認
- **テスト観点**: ログ出力にセンシティブ情報が含まれていないか
- **関連する受入条件**: AC-1（セキュリティ）
- **関連する設計方針**: DP-5
- **テスト種別**: E2E + ログ確認
- **テスト方法**: ログ解析
- **前提条件**:
  1. 全サービスが起動している
  2. Job Generator APIが呼び出し済み
- **テスト手順**:
  1. Job Generator APIを呼び出し
  2. expertAgentのログを確認
  3. `_internal`や`secret_key`が含まれていないことを検証
- **期待結果**:
  - ログに「capabilities=」が出力される
  - ログに`_internal`が含まれない
  - ログに`secret_key`が含まれない
- **ログ確認コマンド**:
  ```bash
  # ログ確認（Dockerコンテナの場合）
  docker logs expertAgent 2>&1 | grep "capabilities=" | head -5

  # センシティブ情報が含まれていないことを確認
  docker logs expertAgent 2>&1 | grep -i "_internal" | wc -l  # 0であること
  ```
- **pytestメソッド**: `test_tc_006_log_sanitizer_no_sensitive_data`

### TC-007: E2E統合テスト（正常フロー全体）
- **テスト観点**: Capability取得からワークフロー生成までの全フローが動作するか
- **関連する受入条件**: AC-1, AC-5
- **関連する設計方針**: DP-1, DP-2, DP-3
- **テスト種別**: E2E
- **テスト方法**: pytest
- **前提条件**:
  1. 全サービスが起動している
  2. myVaultにAPIキーが登録されている
- **テスト手順**:
  1. Job Generator APIを呼び出し
  2. ステータスポーリングで完了を待機
  3. 結果を検証
- **期待結果**:
  - Job生成が成功する
  - ワークフローが生成される
  - capabilityが反映されたワークフローである
- **pytestメソッド**: `test_tc_007_e2e_full_flow_with_capabilities`

---

## 9. テスト実行計画

### 実行順序

1. **環境準備**
   ```bash
   # サービス起動
   ./scripts/dev-hybrid.sh start --local-only

   # ヘルスチェック
   curl -sf http://localhost:8004/health && echo "expertAgent OK"
   curl -sf http://localhost:8006/health && echo "mySwiftAgentCore OK"
   curl -sf http://localhost:8003/health && echo "myVault OK"
   ```

2. **Capability API確認**（TC-001の前提確認）
   ```bash
   curl -s http://localhost:8006/api/v1/capabilities?project=default_project | jq '.count'
   ```

3. **pytest受入テスト実行**
   ```bash
   cd /Users/maenokota/share/work/github_kewton/MySwiftAgent
   uv run pytest expertAgent/tests/acceptance/test_issue_385_acceptance.py -v -s
   ```

4. **追加curlテスト実行**（上記TC-001〜TC-006のcurlコマンド）

5. **ログ確認**
   ```bash
   docker logs expertAgent 2>&1 | tail -100
   ```

### 成功基準

- [ ] TC-001: Capability取得正常系 - PASS
- [ ] TC-002: Capabilityがワークフロー生成に渡される - PASS
- [ ] TC-003: Capability取得失敗時エラー - PASS
- [ ] TC-004: 空タスク検証（空要求） - PASS
- [ ] TC-005: 空タスク検証（曖昧要求） - PASS
- [ ] TC-006: ログサニタイザー動作 - PASS
- [ ] TC-007: E2E統合テスト - PASS
- [ ] すべての受入条件が検証済み
- [ ] デッドコードが検出されないこと（F-1〜F-4が呼び出されている）
- [ ] 単体テストカバレッジ90%以上（TDD完了後）

---

## 10. サービス間データフロー検証

### DF-1: Capability取得フロー

```
[expertAgent] --> [mySwiftAgentCore]
     |                    |
     |  GET /api/v1/capabilities?project=default_project
     |                    |
     |  <-- { capabilities: [...], count: N }
     |
     v
[orchestrator._execute_workflow_gen()]
     |
     |  capabilities = await client.fetch_capabilities(project_id)
     |
     v
[WorkflowGeneratorClient.generate_workflows()]
     |
     |  POST /api/v1/generator/workflow/batch
     |  Body: { tasks: [...], capabilities: [...], project_id: "..." }
     |
     v
[mySwiftAgentCore Workflow Generator]
```

### DF-2: 検証必須項目

| チェック項目 | 検証方法 | テストケース |
|------------|---------|-------------|
| capabilities取得 | API呼び出し確認 | TC-001 |
| capabilities渡し | リクエストボディ確認 | TC-002 |
| capabilities空でない | count > 0 確認 | TC-001, TC-002 |
| エラー時明示的処理 | エラーレスポンス確認 | TC-003 |

### DF-3: テスト項目必須化チェックリスト

- [ ] **DF-TC-1**: 実際のcapabilityデータがAPIに渡されることを検証 (TC-001, TC-002)
- [ ] **DF-TC-2**: capability取得失敗時のエラー処理を検証 (TC-003)
- [ ] **DF-TC-3**: 空タスク時のエラー処理を検証 (TC-004, TC-005)

---

## 11. 補足事項

### 既存コードの問題箇所

現在の`orchestrator.py` L302では以下のように常に空配列が渡されている:

```python
response = await c.generate_workflows(
    tasks=task_requests,
    capabilities=[],  # <-- 常に空配列（問題）
    project_id=project_id,
    ...
)
```

この問題を修正し、実際のcapabilityを取得して渡す必要がある。

### テストデータ要件

- mySwiftAgentCoreの`default_project`にcapabilityが登録されていること
- 最低1つ以上のcapabilityが利用可能であること

### 将来の拡張

- Capabilityキャッシング（v2で検討）
- Capability同期（WebHook通知）

---

**作成日**: 2026-01-21
**作成者**: acceptance-plan-agent
**レビュー**: 未実施
**フェーズ**: PRE-TDD

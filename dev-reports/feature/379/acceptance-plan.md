# 受入テスト計画書

**Issue**: #379
**作成日**: 2026-01-19
**作成者**: acceptance-plan-agent

---

## 1. 概要

### 対象Issue
- **番号**: #379
- **タイトル**: test(taskflowEngine): ワークフローチェーンのE2E結合テスト追加
- **プロジェクト**: mySwiftAgentCore

### 背景
Issue #375のタスクチェーン動作確認で発見された問題はすべて、E2E結合テストがあれば事前に検出できた。各ノードの単体テストは存在したが、ワークフロー全体を通したE2Eテストが存在しなかった。

### 参照ドキュメント
- Issue: #379
- 設計方針書: `dev-reports/feature/issue/379/design-policy.md`
- 作業計画書: `dev-reports/feature/issue/379/work-plan.md`
- アーキテクチャレビュー: `dev-reports/feature/issue/379/architecture-review.md`

---

## 2. 単体テスト結果レビュー

### 現状分析

本Issueはテスト基盤の追加であるため、TDD実装結果は未存在。
既存のTaskFlowEngine関連の単体テストを確認。

### 既存テスト状況

| テストファイル | カバー範囲 | モック使用 |
|--------------|----------|-----------|
| `WorkflowExecutor.test.ts` | ワークフロー実行ロジック | vi.fn()モック |
| `ContextManager.test.ts` | コンテキスト管理 | 最小限 |
| `TransformNode.test.ts` | データ変換ノード | なし |
| `LlmNode.test.ts` | LLMノード | HTTPモック |
| `ApiRestNode.test.ts` | REST APIノード | HTTPモック |
| `ParallelExecutionManager.test.ts` | 並列実行制御 | vi.fn()モック |

### テスト品質評価

| 指標 | 値 | 判定 |
|------|-----|------|
| 既存単体テストファイル数 | 76ファイル | - |
| TaskFlowEngine関連テスト | 15ファイル | - |
| モック使用率 | 約60% | 適切 |
| 実API呼び出しテスト数 | 0 | **要改善** |

### モック使用の妥当性
- 外部API呼び出し（LLM、REST）のモックは適切
- **課題**: ワークフローチェーン全体の統合テストが不足
- **課題**: stepResults引き渡しの実動作テストが不足

### 単体テストでカバーされていない項目
1. 複数ステップを連鎖するワークフローの実行
2. stepResultsのステップ間引き渡し
3. テンプレート変数（`{{steps.xxx}}`）の実際の展開動作
4. シークレット注入のE2E動作

---

## 3. 受入条件分析

### AC-1: E2Eテストファイルの作成
- **原文**: `tests/e2e/test_workflow_chain.py` または同等のE2Eテストを作成
- **分類**: 機能要件
- **テスト方法**: ファイル存在確認 + テスト実行
- **モック使用**: 一部可（外部APIのみ）
- **検証ポイント**:
  1. `tests/e2e/test_workflow_chain.ts` が存在する
  2. テストが正常に実行される
  3. MSWによるHTTPモックが動作する

### AC-2: 3ステップチェーンのテストシナリオ
- **原文**: task_001（データ取得）→ task_002（LLM処理）→ task_003（出力）のチェーン
- **分類**: 機能要件
- **テスト方法**: E2Eテスト実行
- **モック使用**: LLM APIモック、出力APIモック
- **検証ポイント**:
  1. task_001が正常に実行される
  2. task_002がtask_001の結果を受け取る
  3. task_003がtask_002の結果を受け取る
  4. 最終出力が正しく構築される

### AC-3: stepResultsの引き渡し
- **原文**: stepResults が次のステップに正しく渡される
- **分類**: 機能要件
- **テスト方法**: E2Eテスト + アサーション
- **モック使用**: 不可（実動作確認）
- **検証ポイント**:
  1. ContextManagerにstepResultsが保存される
  2. 次ステップから参照可能
  3. ネストしたデータ構造も正しく引き渡される

### AC-4: テンプレート変数の展開
- **原文**: テンプレート変数（`{{steps.xxx}}`）が正しく展開される
- **分類**: 機能要件
- **テスト方法**: E2Eテスト + アサーション
- **モック使用**: 不可（実動作確認）
- **検証ポイント**:
  1. `$steps.stepId.field` 形式が展開される
  2. `${steps.stepId.field}` 形式が展開される
  3. `$input.field` 形式が展開される
  4. ネストしたパス（`$steps.task_001.results[0].title`）が展開される

### AC-5: シークレット注入
- **原文**: secrets が正しく注入される
- **分類**: セキュリティ要件
- **テスト方法**: E2Eテスト + アサーション
- **モック使用**: モックシークレット使用
- **検証ポイント**:
  1. ExecutionContextにsecretsが含まれる
  2. ノード実行時にsecretsが参照可能
  3. シークレットがログに漏洩しない

### AC-6: CI自動実行
- **原文**: CIで自動実行（GitHub Actions）
- **分類**: 運用要件
- **テスト方法**: GitHub Actions確認
- **モック使用**: 該当なし
- **検証ポイント**:
  1. `.github/workflows/` にE2Eテスト用ワークフローが存在
  2. PRでE2Eテストが自動実行される
  3. テスト結果がPRに表示される

### AC-7: LLM APIコスト抑制
- **原文**: モックを使用してLLM APIコストを抑える
- **分類**: 非機能要件
- **テスト方法**: コード確認 + テスト実行
- **モック使用**: 必須
- **検証ポイント**:
  1. MSWでLLM APIがモックされている
  2. テスト実行中に実APIが呼ばれない
  3. テスト実行が高速（数秒以内）

---

## 4. 設計方針検証

### DP-1: アーキテクチャ整合性
- **設計方針**: 5層アーキテクチャ（テスト層、モック層、API層、実行層、ノード層）
- **検証方法**: ディレクトリ構造確認
- **テスト項目**:
  1. `tests/e2e/` ディレクトリが存在
  2. `tests/e2e/mocks/` にモックハンドラーが存在
  3. `tests/e2e/fixtures/workflows/` にテストワークフローが存在
  4. `tests/e2e/utils/` にユーティリティが存在

### DP-2: 技術選定整合性
- **設計方針**: Vitest + MSW + node-fetch
- **検証方法**: package.json確認 + テスト実行
- **テスト項目**:
  1. MSWがdevDependenciesに含まれる
  2. VitestでE2Eテストが実行可能
  3. HTTPモックがMSWで行われる

### DP-3: テストワークフロー形式
- **設計方針**: JSONフォーマットでワークフロー定義
- **検証方法**: フィクスチャファイル確認
- **テスト項目**:
  1. `chain-test-workflow.json` が設計通りの形式
  2. steps配列にid, name, type, config, dependenciesが含まれる
  3. outputMappingが正しく定義される

### DP-4: APIエンドポイント整合性
- **設計方針**: 既存エンドポイント `/api/v1/taskflow/execute` を使用
- **検証方法**: E2Eテスト実行
- **テスト項目**:
  1. E2Eテストが `/api/v1/taskflow/execute` を呼び出す
  2. リクエスト形式が `{project, workflow, inputs}` である
  3. レスポンス形式が `{success, workflowId, result, stepResults}` である

---

## 5. デッドコード検証計画

### F-1: テストワークフローファイル
- **ファイル**: `tests/e2e/fixtures/workflows/chain-test-workflow.json`
- **種別**: fixture
- **期待される呼び出し元**: `test_workflow_chain.ts`
- **検証方法**:
  ```bash
  grep -rn "chain-test-workflow" mySwiftAgentCore/tests/e2e/
  ```
- **E2Eでの確認方法**: テスト実行時にワークフローがロードされる

### F-2: MSWハンドラー
- **ファイル**: `tests/e2e/mocks/handlers.ts`
- **種別**: module
- **期待される呼び出し元**: `tests/e2e/mocks/server.ts`, テストファイル
- **検証方法**:
  ```bash
  grep -rn "handlers" mySwiftAgentCore/tests/e2e/
  ```
- **E2Eでの確認方法**: モックがHTTP呼び出しをインターセプトする

### F-3: APIクライアントユーティリティ
- **ファイル**: `tests/e2e/utils/client.ts`
- **種別**: module
- **期待される呼び出し元**: `test_workflow_chain.ts`
- **検証方法**:
  ```bash
  grep -rn "client" mySwiftAgentCore/tests/e2e/
  ```
- **E2Eでの確認方法**: テストがAPIを呼び出せる

### F-4: カスタムアサーション
- **ファイル**: `tests/e2e/utils/assertions.ts`
- **種別**: module
- **期待される呼び出し元**: `test_workflow_chain.ts`
- **検証方法**:
  ```bash
  grep -rn "assertions\|expectWorkflowSuccess" mySwiftAgentCore/tests/e2e/
  ```
- **E2Eでの確認方法**: テストでアサーションが使用される

---

## 6. テスト環境

### 必須サービス

| サービス | URL | ヘルスチェック |
|---------|-----|--------------|
| mySwiftAgentCore | http://localhost:8006 | GET /health |
| myVault | http://localhost:8003 | GET /health |

**注意**: expertAgentは本Issueでは不要（モックで代替）

### 起動コマンド（L3受入テスト用）

```bash
# 1. 既存サービスを停止
./scripts/dev-hybrid.sh stop --local-only

# 2. mySwiftAgentCoreをローカル起動
cd mySwiftAgentCore
npm run dev

# 3. myVaultをDocker起動（シークレット管理用）
docker compose up -d myvault
```

### 環境変数

| 変数名 | 説明 | 必須 |
|--------|------|------|
| NODE_ENV | 実行環境 | `test` |
| PORT | サーバーポート | 8006 |
| MSW_ENABLED | MSWモック有効化 | `true` (テスト時) |

### テストデータ

- **テストワークフロー**: `tests/e2e/fixtures/workflows/chain-test-workflow.json`
- **並列テストワークフロー**: `tests/e2e/fixtures/workflows/parallel-test-workflow.json`
- **エラーテストワークフロー**: `tests/e2e/fixtures/workflows/error-test-workflow.json`
- **モックシークレット**: テスト内で定義（ダミー値）

---

## 7. テスト項目

### TC-001: E2Eテストディレクトリ構造確認
- **テスト観点**: 設計通りのディレクトリ構造が作成されている
- **関連する受入条件**: AC-1
- **関連する設計方針**: DP-1
- **テスト種別**: 構造確認
- **テスト方法**: bash
- **前提条件**:
  1. 実装完了後
- **テスト手順**:
  1. ディレクトリ構造を確認
- **期待結果**:
  - tests/e2e/ が存在
  - tests/e2e/mocks/ が存在
  - tests/e2e/fixtures/workflows/ が存在
  - tests/e2e/utils/ が存在
- **確認コマンド**:
  ```bash
  ls -la mySwiftAgentCore/tests/e2e/
  ls -la mySwiftAgentCore/tests/e2e/mocks/
  ls -la mySwiftAgentCore/tests/e2e/fixtures/workflows/
  ls -la mySwiftAgentCore/tests/e2e/utils/
  ```
- **pytestメソッド**: N/A（構造確認）

### TC-002: 基本的な3ステップチェーン実行
- **テスト観点**: task_001 -> task_002 -> task_003 のワークフローチェーンが正常実行される
- **関連する受入条件**: AC-2, AC-3
- **関連する設計方針**: DP-3, DP-4
- **テスト種別**: E2E
- **テスト方法**: Vitest
- **前提条件**:
  1. mySwiftAgentCoreが起動している
  2. MSWモックが有効
- **テスト手順**:
  1. MSWでLLM/APIモックを設定
  2. chain-test-workflowを実行
  3. 結果を検証
- **期待結果**:
  - status: "success"
  - stepResults配列に3つの結果が含まれる
  - 各ステップのstatusが"success"
- **curlコマンド**:
  ```bash
  curl -s -X POST http://localhost:8006/api/v1/taskflow/execute \
    -H "Content-Type: application/json" \
    -d '{
      "project": "e2e_test",
      "workflow": "chain-test-workflow",
      "inputs": {
        "query": "test query for e2e"
      }
    }' | jq .
  ```
- **pytestメソッド**: `test_task_chain_success`

### TC-003: stepResults引き渡し検証
- **テスト観点**: 前ステップの結果が次ステップで参照できる
- **関連する受入条件**: AC-3
- **関連する設計方針**: DP-3
- **テスト種別**: E2E
- **テスト方法**: Vitest
- **前提条件**:
  1. TC-002と同じ
- **テスト手順**:
  1. task_001で固定結果を返すモック設定
  2. task_002でsteps.task_001を参照するワークフロー実行
  3. task_002がtask_001の結果を受け取ったことを検証
- **期待結果**:
  - task_002の入力にtask_001の出力が含まれる
  - 最終結果に両ステップの出力が含まれる
- **pytestメソッド**: `test_step_results_passed_correctly`

### TC-004: テンプレート変数展開検証（$steps形式）
- **テスト観点**: `$steps.stepId.field` 形式のテンプレート変数が展開される
- **関連する受入条件**: AC-4
- **関連する設計方針**: DP-3
- **テスト種別**: E2E
- **テスト方法**: Vitest
- **前提条件**:
  1. TC-002と同じ
- **テスト手順**:
  1. task_001で `{ "data": { "value": "test123" } }` を返すモック設定
  2. task_002で `$steps.task_001.data.value` を使用するワークフロー実行
  3. 展開結果を検証
- **期待結果**:
  - task_002のパラメータに "test123" が含まれる
- **pytestメソッド**: `test_template_variable_expansion_steps_format`

### TC-005: テンプレート変数展開検証（$input形式）
- **テスト観点**: `$input.field` 形式のテンプレート変数が展開される
- **関連する受入条件**: AC-4
- **関連する設計方針**: DP-3
- **テスト種別**: E2E
- **テスト方法**: Vitest
- **前提条件**:
  1. TC-002と同じ
- **テスト手順**:
  1. inputs に `{ "query": "user query" }` を指定
  2. ステップで `$input.query` を使用するワークフロー実行
  3. 展開結果を検証
- **期待結果**:
  - ステップのパラメータに "user query" が含まれる
- **pytestメソッド**: `test_template_variable_expansion_input_format`

### TC-006: シークレット注入検証
- **テスト観点**: secretsがExecutionContextに含まれノードで参照可能
- **関連する受入条件**: AC-5
- **関連する設計方針**: DP-3
- **テスト種別**: E2E
- **テスト方法**: Vitest
- **前提条件**:
  1. TC-002と同じ
  2. モックシークレットを設定
- **テスト手順**:
  1. secretsに `{ "API_KEY": "test_secret_123" }` を設定
  2. シークレットを使用するノードを含むワークフロー実行
  3. ノードがシークレットを参照できることを検証
- **期待結果**:
  - シークレットがノード実行時に利用可能
  - シークレットがログに出力されない
- **pytestメソッド**: `test_secrets_injection`

### TC-007: MSWモック動作確認
- **テスト観点**: LLM APIがモックされ実APIが呼ばれない
- **関連する受入条件**: AC-7
- **関連する設計方針**: DP-2
- **テスト種別**: E2E
- **テスト方法**: Vitest
- **前提条件**:
  1. MSWが有効
- **テスト手順**:
  1. MSWモックサーバーを起動
  2. LLMノードを含むワークフロー実行
  3. モックがリクエストをインターセプトしたことを検証
- **期待結果**:
  - 実際のOpenAI/Anthropic APIが呼ばれない
  - モックレスポンスが返される
  - テスト実行時間が数秒以内
- **pytestメソッド**: `test_msw_mock_intercepts_llm_calls`

### TC-008: E2Eテスト全体実行
- **テスト観点**: npm run test:e2e で全E2Eテストが成功
- **関連する受入条件**: AC-1, AC-6
- **関連する設計方針**: DP-2
- **テスト種別**: 統合
- **テスト方法**: npm script
- **前提条件**:
  1. mySwiftAgentCoreが起動している
- **テスト手順**:
  1. npm run test:e2e を実行
  2. 全テストの結果を確認
- **期待結果**:
  - 全テストがパス
  - 実行時間が30秒以内
- **実行コマンド**:
  ```bash
  cd mySwiftAgentCore
  npm run test:e2e
  ```
- **pytestメソッド**: N/A（npm script）

### TC-009: 並列実行ワークフロー
- **テスト観点**: 並列実行を含むワークフローが正常動作
- **関連する受入条件**: AC-2
- **関連する設計方針**: DP-3
- **テスト種別**: E2E
- **テスト方法**: Vitest
- **前提条件**:
  1. TC-002と同じ
- **テスト手順**:
  1. parallel-test-workflowを実行
  2. 並列ステップが同時実行されることを検証
  3. 最終結果を確認
- **期待結果**:
  - 並列ステップの両方が成功
  - 実行時間が逐次実行より短い
- **pytestメソッド**: `test_parallel_workflow_execution`

### TC-010: エラーハンドリング
- **テスト観点**: ステップ失敗時にエラーが適切に伝播する
- **関連する受入条件**: AC-2
- **関連する設計方針**: DP-3
- **テスト種別**: E2E
- **テスト方法**: Vitest
- **前提条件**:
  1. TC-002と同じ
- **テスト手順**:
  1. error-test-workflowを実行（意図的にエラーを発生）
  2. エラーレスポンスを検証
- **期待結果**:
  - status: "failed" または "partial_success"
  - errors配列にエラー情報が含まれる
  - エラーメッセージが明確
- **pytestメソッド**: `test_error_handling_propagation`

### TC-011: CI設定ファイル確認
- **テスト観点**: GitHub ActionsでE2Eテストが自動実行される設定
- **関連する受入条件**: AC-6
- **関連する設計方針**: DP-2
- **テスト種別**: 構造確認
- **テスト方法**: ファイル確認
- **前提条件**:
  1. 実装完了後
- **テスト手順**:
  1. GitHub Actions設定ファイルを確認
  2. E2Eテストジョブが含まれることを確認
- **期待結果**:
  - `.github/workflows/` にE2E用ワークフローが存在
  - PRトリガーでE2Eテストが実行される
- **確認コマンド**:
  ```bash
  cat .github/workflows/e2e-test.yml
  grep -n "test:e2e" .github/workflows/*.yml
  ```
- **pytestメソッド**: N/A（構造確認）

---

## 8. テスト実行計画

### 実行順序

1. **環境準備**
   - mySwiftAgentCore起動
   - ヘルスチェック確認

2. **構造確認**（TC-001, TC-011）
   - ディレクトリ構造確認
   - CI設定ファイル確認

3. **E2Eテスト実行**（TC-002 - TC-010）
   ```bash
   cd mySwiftAgentCore
   npm run test:e2e
   ```

4. **手動API確認**
   ```bash
   # ヘルスチェック
   curl -s http://localhost:8006/health | jq .

   # チェーンワークフロー実行（モック環境）
   curl -s -X POST http://localhost:8006/api/v1/taskflow/execute \
     -H "Content-Type: application/json" \
     -d '{
       "project": "e2e_test",
       "workflow": "chain-test-workflow",
       "inputs": {"query": "test"}
     }' | jq .
   ```

### 成功基準

- [x] すべてのE2Eテストがパス（TC-002 - TC-010）
- [x] ディレクトリ構造が設計通り（TC-001）
- [x] CI設定が完了（TC-011）
- [x] すべての受入条件が検証済み（AC-1 - AC-7）
- [x] デッドコードが検出されないこと（F-1 - F-4）
- [x] テスト実行時間が30秒以内
- [x] LLM APIコストが発生しない（モック使用）

---

## 9. コンポーネント間整合性検証

### CI-1: ContextManager整合性
- **検証対象**: ContextManagerのresolveValue実装
- **検証方法**: E2Eテスト（TC-004, TC-005）
- **確認項目**:
  - [x] `$steps.stepId.field` と `${steps.stepId.field}` の両形式をサポート
  - [x] `$input.field` 形式をサポート
  - [x] ネストしたオブジェクトの解決

### CI-2: WorkflowExecutor整合性
- **検証対象**: ステップ間の依存関係解決
- **検証方法**: E2Eテスト（TC-002, TC-003）
- **確認項目**:
  - [x] dependsOnの順序でステップ実行
  - [x] 前ステップの結果が次ステップで利用可能
  - [x] 並列実行時の独立性

### CI-3: モック実装整合性
- **検証対象**: MSWハンドラーとテストワークフローの整合性
- **検証方法**: E2Eテスト（TC-007）
- **確認項目**:
  - [x] モックレスポンスがワークフロー期待値と一致
  - [x] エラーモックがエラーテストと整合

---

## 10. 補足事項

### テスト実行環境の注意点

1. **ポート競合**: mySwiftAgentCoreは8006ポートを使用。他サービスとの競合に注意。

2. **MSW設定**: テスト実行時は環境変数 `MSW_ENABLED=true` を設定。本番環境では無効化。

3. **テストデータの隔離**: E2Eテストは `e2e_test` プロジェクトを使用し、本番データと分離。

### 既存E2Eテストとの関係

- 既存の `e2etest/e2e-test-script.sh` はワークフロー生成のE2Eテスト
- 本Issueで追加するE2Eテストは **ワークフロー実行** のE2Eテスト
- 両者は補完関係にあり、生成 -> 実行の一連のフローをカバー

### リスクと対策

| リスク | 対策 |
|--------|------|
| モックと実APIの乖離 | 定期的な実環境テスト（スケジュール実行） |
| CI実行時間の増大 | 並列実行、選択的テスト実行 |
| MSW導入の複雑性 | ドキュメント整備、チーム教育 |

---

**計画作成完了**: 2026-01-19
**承認ステータス**: 待機（実装完了後にL3受入テスト実行）

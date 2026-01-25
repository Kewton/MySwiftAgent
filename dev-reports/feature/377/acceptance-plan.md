# 受入テスト計画書

**Issue**: #377
**作成日**: 2026-01-19
**作成者**: acceptance-plan-agent

---

## 1. 概要

### 対象Issue
- **番号**: #377
- **タイトル**: refactor(taskflowEngine): Secrets注入パターンの統一
- **プロジェクト**: mySwiftAgentCore

### 参照ドキュメント
- Issue: #377
- 設計方針書: `dev-reports/feature/issue/377/design-policy.md`
- 作業計画書: `dev-reports/feature/issue/377/work-plan.md`

### Issue背景
Issue #375のタスクチェーン動作確認中に、LlmNodeがAPIキーを取得できない問題が発生した。真因はノードタイプによってSecrets取得方法が異なっていたこと。本Issueでは全ノードタイプで統一されたSecrets取得パターンを実装する。

---

## 2. 単体テスト結果レビュー

**注記**: 本計画はPRE-TDD段階で作成されたため、単体テスト結果は未実装。
TDD実装後に以下の項目を更新すること。

### カバレッジ（TDD実装後に更新）
- 現在: TBD%
- 目標: 90%
- 判定: TBD

### テスト品質評価（TDD実装後に更新）
| 指標 | 値 | 判定 |
|------|-----|------|
| 総テスト数 | TBD | - |
| モック使用テスト数 | TBD | - |
| モック使用率 | TBD% | TBD |
| 実API呼び出しテスト数 | TBD | - |

### 単体テストでカバーすべき項目
1. SecretAnalyzer.analyzeWorkflow() - 静的Secrets宣言の解析
2. SecretAnalyzer.analyzeWorkflow() - 動的Secrets（getRequiredSecrets）の解析
3. LlmNode.requiredSecrets - プロパティの存在と値
4. ApiRestNode.getRequiredSecrets() - config.authベースの動的取得
5. Handler改善 - 必要なSecretsのみ取得するロジック
6. SecretNotFoundError - エラーメッセージとコンテキスト

---

## 3. 受入条件分析

### AC-1: NodeExecutorインターフェース拡張
- **原文**: NodeExecutorインターフェースにrequiredSecretsプロパティ追加
- **分類**: 機能要件
- **テスト方法**: コード構造確認、TypeScript型検証
- **モック使用**: 不可
- **検証ポイント**:
  1. NodeExecutorインターフェースにrequiredSecrets?: readonly string[]が追加されている
  2. getRequiredSecrets?(config: NodeConfig): Promise<string[]>メソッドが型定義に含まれる
  3. 既存のNodeExecutor実装（型検査）に破壊的変更がない

### AC-2: SecretAnalyzerクラス実装
- **原文**: SecretAnalyzerクラスの実装
- **分類**: 機能要件
- **テスト方法**: pytest、結合テスト
- **モック使用**: 一部可（外部APIのみ）
- **検証ポイント**:
  1. SecretAnalyzerクラスが存在する
  2. analyzeWorkflow()メソッドがWorkflowSecretRequirementsを返す
  3. 静的Secrets（requiredSecrets配列）を正しく収集する
  4. 動的Secrets（getRequiredSecretsメソッド）を正しく収集する
  5. ワークフロー内の全ステップを解析する

### AC-3: Handler改善実装
- **原文**: 改善されたHandler実装（必要なSecretsのみ取得）
- **分類**: 機能要件
- **テスト方法**: E2E API呼び出し
- **モック使用**: 不可
- **検証ポイント**:
  1. Handlerがワークフロー実行前にSecretAnalyzerを呼び出す
  2. SecretAnalyzerの結果に基づいて必要なSecretsのみ取得する
  3. 不要なSecrets（使用しないキー）を取得しない
  4. Secrets不足時にSecretNotFoundErrorを返す

### AC-4: ノード移行完了
- **原文**: LlmNode、ApiRestNodeの移行完了
- **分類**: 機能要件
- **テスト方法**: E2E ワークフロー実行
- **モック使用**: 不可
- **検証ポイント**:
  1. LlmNodeにrequiredSecretsプロパティが追加されている
  2. LlmNode.requiredSecretsが['OPENAI_API_KEY', 'LLM_API_KEY']を含む
  3. ApiRestNodeにgetRequiredSecretsメソッドが追加されている
  4. ApiRestNode.getRequiredSecrets()がconfig.auth.secret_keyを返す

### AC-5: 単体テストカバレッジ
- **原文**: 単体テスト実装（カバレッジ90%以上）
- **分類**: 品質要件
- **テスト方法**: npm test -- --coverage
- **モック使用**: 単体テスト内で適切に使用
- **検証ポイント**:
  1. 全体カバレッジが90%以上
  2. SecretAnalyzer.tsのカバレッジが90%以上
  3. 新規追加ファイルのカバレッジが90%以上

### AC-6: 結合テスト実装
- **原文**: 結合テスト実装
- **分類**: 品質要件
- **テスト方法**: npm test
- **モック使用**: 外部APIのみ
- **検証ポイント**:
  1. 複数ノードを含むワークフローでSecrets注入が正しく動作する
  2. LlmNode + ApiRestNodeの連携テストがパスする
  3. エラーケース（Secrets不足）のテストがパスする

### AC-7: E2E受入テスト
- **原文**: E2E受入テスト実装と成功
- **分類**: 品質要件
- **テスト方法**: pytest（実サービス起動）
- **モック使用**: 不可
- **検証ポイント**:
  1. 実際のワークフローAPI呼び出しで機能が動作する
  2. LLM APIキーが正しく注入されてLlmNodeが動作する
  3. ApiRestNodeが動的Secretsを正しく取得する

### AC-8: ドキュメント更新
- **原文**: ドキュメント更新
- **分類**: ドキュメント要件
- **テスト方法**: ファイル存在確認、内容レビュー
- **モック使用**: N/A
- **検証ポイント**:
  1. NodeExecutor開発ガイドが更新されている
  2. Secrets注入パターンの移行ガイドが作成されている
  3. SecretAnalyzer使用方法が文書化されている

---

## 4. 設計方針検証

### DP-1: アーキテクチャ整合性
- **設計方針**: 4層構造（API層、実行層、ノード層、インフラ層）でSecretAnalyzerはAPI層に配置
- **検証方法**: コード構造確認
- **テスト項目**:
  1. SecretAnalyzerがAPI層（handlers付近）に配置されている
  2. NodeExecutorがノード層にとどまっている
  3. SecretManagerがインフラ層として使用されている

### DP-2: 宣言的Secrets定義パターン
- **設計方針**: NodeExecutorにrequiredSecrets?: readonly string[]を追加
- **検証方法**: TypeScript型検査、コード確認
- **テスト項目**:
  1. NodeExecutorインターフェースにrequiredSecretsが追加されている
  2. readonly修飾子で不変性が保証されている
  3. オプショナル（?）で後方互換性が維持されている

### DP-3: ハイブリッドアプローチ
- **設計方針**: 静的（宣言的）と動的（getRequiredSecrets）の両方をサポート
- **検証方法**: E2Eテスト
- **テスト項目**:
  1. LlmNodeが静的パターン（requiredSecrets配列）を使用している
  2. ApiRestNodeが動的パターン（getRequiredSecrets）を使用している
  3. SecretAnalyzerが両パターンを正しく処理する

### DP-4: 最小権限原則
- **設計方針**: ワークフローで使用するSecretsのみ取得
- **検証方法**: ログ確認、パフォーマンステスト
- **テスト項目**:
  1. LlmNodeのみのワークフローでOPENAI_API_KEY/LLM_API_KEYのみ取得
  2. ApiRestNode（auth未設定）のワークフローでSecrets取得なし
  3. 複合ワークフローで必要なSecretsのみ取得

### DP-5: 統一エラーハンドリング
- **設計方針**: SecretNotFoundErrorによる一貫したエラー報告
- **検証方法**: 異常系E2Eテスト
- **テスト項目**:
  1. Secrets不足時にSecretNotFoundErrorがスローされる
  2. エラーメッセージに不足しているキー名が含まれる
  3. エラーにworkflow IDとstep IDが含まれる

### DP-6: 後方互換性
- **設計方針**: 既存NodeExecutorの破壊的変更なし、段階的移行可能
- **検証方法**: 既存テストスイート実行
- **テスト項目**:
  1. requiredSecrets未定義のノードでも正常動作する
  2. 既存のワークフロー定義が変更なしで動作する
  3. CI/CDの既存テストが全てパスする

---

## 5. デッドコード検証計画

### F-1: SecretAnalyzerクラス
- **ファイル**: `mySwiftAgentCore/src/taskflowEngine/analyzer/SecretAnalyzer.ts`
- **種別**: class
- **期待される呼び出し元**: handlers.ts
- **検証方法**:
  ```bash
  grep -rn "SecretAnalyzer" --include="*.ts" mySwiftAgentCore/src/
  ```
- **E2E確認**: ワークフローAPI実行時にSecretAnalyzerが呼ばれることをログで確認

### F-2: WorkflowSecretRequirements型
- **ファイル**: `mySwiftAgentCore/src/taskflowEngine/analyzer/SecretAnalyzer.ts`（またはtypes）
- **種別**: type/interface
- **期待される呼び出し元**: SecretAnalyzer, handlers.ts
- **検証方法**:
  ```bash
  grep -rn "WorkflowSecretRequirements" --include="*.ts" mySwiftAgentCore/src/
  ```
- **E2E確認**: TypeScript型チェックでエラーなし

### F-3: LlmNode.requiredSecrets
- **ファイル**: `mySwiftAgentCore/src/taskflowEngine/nodes/LlmNode.ts`
- **種別**: property
- **期待される呼び出し元**: SecretAnalyzer.analyzeWorkflow()
- **検証方法**:
  ```bash
  grep -rn "requiredSecrets" --include="*.ts" mySwiftAgentCore/src/
  ```
- **E2E確認**: LlmNodeを含むワークフロー実行で正しいSecretsが注入される

### F-4: ApiRestNode.getRequiredSecrets
- **ファイル**: `mySwiftAgentCore/src/taskflowEngine/nodes/ApiRestNode.ts`
- **種別**: method
- **期待される呼び出し元**: SecretAnalyzer.analyzeWorkflow()
- **検証方法**:
  ```bash
  grep -rn "getRequiredSecrets" --include="*.ts" mySwiftAgentCore/src/
  ```
- **E2E確認**: ApiRestNode（auth設定あり）を含むワークフロー実行で正しいSecretsが注入される

### F-5: SecretNotFoundError
- **ファイル**: `mySwiftAgentCore/src/taskflowEngine/errors/SecretNotFoundError.ts`
- **種別**: class
- **期待される呼び出し元**: handlers.ts
- **検証方法**:
  ```bash
  grep -rn "SecretNotFoundError" --include="*.ts" mySwiftAgentCore/src/
  ```
- **E2E確認**: Secrets不足時のワークフロー実行でエラーが返される

---

## 6. テスト環境

### 必須サービス
| サービス | URL | ヘルスチェック |
|---------|-----|--------------|
| mySwiftAgentCore | http://localhost:8006 | GET /health |
| MyVault（オプション） | http://localhost:8003 | GET /health |

### 起動コマンド
```bash
# mySwiftAgentCore起動
cd mySwiftAgentCore
npm run dev

# ヘルスチェック
curl -sf http://localhost:8006/health && echo "mySwiftAgentCore healthy"
```

### 環境変数
| 変数名 | 説明 | 必須 |
|--------|------|------|
| OPENAI_API_KEY | OpenAI APIキー（LlmNodeテスト用） | LlmNodeテスト時 |
| LLM_API_KEY | 代替LLM APIキー | オプション |
| ANTHROPIC_API_KEY | Anthropic APIキー | オプション |
| MYVAULT_ENABLED | MyVault有効化フラグ | オプション |
| MYVAULT_BASE_URL | MyVault URL | MYVAULT_ENABLED=true時 |
| MYVAULT_SERVICE_NAME | サービス名 | MYVAULT_ENABLED=true時 |
| MYVAULT_SERVICE_TOKEN | サービストークン | MYVAULT_ENABLED=true時 |

### テストデータ
1. **test_llm_workflow.yaml**: LlmNodeのみを含むワークフロー
2. **test_api_workflow.yaml**: ApiRestNode（auth設定なし）のワークフロー
3. **test_api_workflow_with_auth.yaml**: ApiRestNode（auth設定あり）のワークフロー
4. **test_complex_workflow.yaml**: LlmNode + ApiRestNodeの複合ワークフロー

---

## 7. テスト項目

### TC-001: SecretAnalyzer静的Secrets解析
- **テスト観点**: SecretAnalyzerがrequiredSecrets配列を正しく解析する
- **関連する受入条件**: AC-2
- **関連する設計方針**: DP-3
- **テスト種別**: 結合
- **テスト方法**: pytest
- **前提条件**:
  1. mySwiftAgentCoreが起動している
  2. テストワークフロー（LlmNode含む）が登録されている
- **テスト手順**:
  1. LlmNodeを含むワークフローを実行
  2. レスポンスからSecretsが正しく注入されたことを確認
- **期待結果**:
  - ワークフロー実行成功（status: completed）
  - LlmNodeがAPIキーを使用してLLM呼び出しを実行
- **curlコマンド**:
  ```bash
  curl -s -X POST http://localhost:8006/api/v1/workflows/execute \
    -H "Content-Type: application/json" \
    -d '{
      "project": "default_project",
      "workflow": "test_llm_workflow",
      "inputs": {"prompt": "Hello"}
    }' | jq '.status'
  ```
- **pytestメソッド**: `test_tc_001_secret_analyzer_static_secrets`

### TC-002: SecretAnalyzer動的Secrets解析
- **テスト観点**: SecretAnalyzerがgetRequiredSecretsメソッドを正しく呼び出す
- **関連する受入条件**: AC-2, AC-4
- **関連する設計方針**: DP-3
- **テスト種別**: 結合
- **テスト方法**: pytest
- **前提条件**:
  1. mySwiftAgentCoreが起動している
  2. ApiRestNode（auth設定あり）のワークフローが登録されている
  3. 対応するSecretが環境変数に設定されている
- **テスト手順**:
  1. ApiRestNode（auth: {secret_key: "CUSTOM_API_KEY"}）を含むワークフローを実行
  2. レスポンスから動的Secretsが正しく注入されたことを確認
- **期待結果**:
  - ワークフロー実行成功
  - ApiRestNodeがCUSTOM_API_KEYを使用してAPI呼び出しを実行
- **curlコマンド**:
  ```bash
  curl -s -X POST http://localhost:8006/api/v1/workflows/execute \
    -H "Content-Type: application/json" \
    -d '{
      "project": "default_project",
      "workflow": "test_api_workflow_with_auth",
      "inputs": {}
    }' | jq '.status'
  ```
- **pytestメソッド**: `test_tc_002_secret_analyzer_dynamic_secrets`

### TC-003: 最小権限Secrets取得
- **テスト観点**: 必要なSecretsのみが取得されることを確認
- **関連する受入条件**: AC-3
- **関連する設計方針**: DP-4
- **テスト種別**: E2E
- **テスト方法**: pytest + ログ確認
- **前提条件**:
  1. mySwiftAgentCoreが起動している
  2. Secretsなしワークフローが登録されている
- **テスト手順**:
  1. transform/code_jsノードのみのワークフローを実行
  2. Secrets取得ログを確認（取得なしであること）
- **期待結果**:
  - ワークフロー実行成功
  - Secrets取得呼び出しが0回
- **pytestメソッド**: `test_tc_003_minimal_secrets_retrieval`

### TC-004: SecretNotFoundErrorエラーハンドリング
- **テスト観点**: 必要なSecretsが不足している場合の適切なエラー処理
- **関連する受入条件**: AC-3
- **関連する設計方針**: DP-5
- **テスト種別**: E2E
- **テスト方法**: pytest
- **前提条件**:
  1. mySwiftAgentCoreが起動している
  2. LlmNodeワークフローが登録されている
  3. OPENAI_API_KEYとLLM_API_KEYが**未設定**
- **テスト手順**:
  1. 環境変数からOPENAI_API_KEY、LLM_API_KEYを削除
  2. LlmNodeを含むワークフローを実行
  3. エラーレスポンスを確認
- **期待結果**:
  - HTTPステータス: 400
  - エラータイプ: SecretNotFoundError
  - エラーメッセージに不足キー名が含まれる
- **curlコマンド**:
  ```bash
  # 環境変数を一時的にunset後に実行
  unset OPENAI_API_KEY
  unset LLM_API_KEY
  curl -s -X POST http://localhost:8006/api/v1/workflows/execute \
    -H "Content-Type: application/json" \
    -d '{
      "project": "default_project",
      "workflow": "test_llm_workflow",
      "inputs": {"prompt": "Test"}
    }' | jq '.error'
  ```
- **pytestメソッド**: `test_tc_004_secret_not_found_error`

### TC-005: LlmNode requiredSecrets移行
- **テスト観点**: LlmNodeがrequiredSecretsプロパティを持ち、正しく動作する
- **関連する受入条件**: AC-4
- **関連する設計方針**: DP-2
- **テスト種別**: E2E
- **テスト方法**: pytest
- **前提条件**:
  1. mySwiftAgentCoreが起動している
  2. OPENAI_API_KEYが設定されている
- **テスト手順**:
  1. LlmNodeを含むワークフローを実行
  2. LLM応答を確認
- **期待結果**:
  - ワークフロー実行成功
  - LLM応答が取得できる
- **curlコマンド**:
  ```bash
  curl -s -X POST http://localhost:8006/api/v1/workflows/execute \
    -H "Content-Type: application/json" \
    -d '{
      "project": "default_project",
      "workflow": "test_llm_workflow",
      "inputs": {"prompt": "Say hello"}
    }' | jq '.results'
  ```
- **pytestメソッド**: `test_tc_005_llm_node_required_secrets`

### TC-006: ApiRestNode getRequiredSecrets移行
- **テスト観点**: ApiRestNodeがgetRequiredSecretsメソッドを持ち、動的にSecretsを要求する
- **関連する受入条件**: AC-4
- **関連する設計方針**: DP-3
- **テスト種別**: E2E
- **テスト方法**: pytest
- **前提条件**:
  1. mySwiftAgentCoreが起動している
  2. 対象APIのSecretsが設定されている
- **テスト手順**:
  1. ApiRestNode（auth設定あり）を含むワークフローを実行
  2. API応答を確認
- **期待結果**:
  - ワークフロー実行成功
  - 認証付きAPI呼び出しが成功
- **pytestメソッド**: `test_tc_006_api_rest_node_get_required_secrets`

### TC-007: 後方互換性確認
- **テスト観点**: requiredSecrets未定義のノードでも正常動作する
- **関連する受入条件**: AC-4
- **関連する設計方針**: DP-6
- **テスト種別**: E2E
- **テスト方法**: pytest
- **前提条件**:
  1. mySwiftAgentCoreが起動している
- **テスト手順**:
  1. CodeJsNode/TransformNodeのみのワークフローを実行
  2. 正常終了を確認
- **期待結果**:
  - ワークフロー実行成功
  - requiredSecrets未定義でもエラーにならない
- **pytestメソッド**: `test_tc_007_backward_compatibility`

### TC-008: 複合ワークフローSecrets注入
- **テスト観点**: 複数ノードタイプを含むワークフローで正しくSecrets注入される
- **関連する受入条件**: AC-6, AC-7
- **関連する設計方針**: DP-3, DP-4
- **テスト種別**: E2E
- **テスト方法**: pytest
- **前提条件**:
  1. mySwiftAgentCoreが起動している
  2. 必要な全Secretsが設定されている
- **テスト手順**:
  1. LlmNode + ApiRestNodeを含む複合ワークフローを実行
  2. 全ステップの成功を確認
- **期待結果**:
  - 全ステップ実行成功
  - 各ノードタイプに正しいSecretsが注入される
- **curlコマンド**:
  ```bash
  curl -s -X POST http://localhost:8006/api/v1/workflows/execute \
    -H "Content-Type: application/json" \
    -d '{
      "project": "default_project",
      "workflow": "test_complex_workflow",
      "inputs": {"prompt": "Analyze this data"}
    }' | jq '{status: .status, errors: .errors}'
  ```
- **pytestメソッド**: `test_tc_008_complex_workflow_secrets_injection`

### TC-009: パフォーマンス確認
- **テスト観点**: Secrets取得が効率的に行われる（必要なもののみ取得）
- **関連する受入条件**: AC-3
- **関連する設計方針**: DP-4
- **テスト種別**: E2E
- **テスト方法**: pytest + 時間計測
- **前提条件**:
  1. mySwiftAgentCoreが起動している
  2. 全Secretsが設定されている
- **テスト手順**:
  1. 同一ワークフローを5回実行
  2. 平均実行時間を計測
- **期待結果**:
  - 平均実行時間が既存実装と同等以下（100ms増加以内）
- **pytestメソッド**: `test_tc_009_performance`

### TC-010: デッドコード検証
- **テスト観点**: 新規実装コードが実際に使用されている
- **関連する受入条件**: AC-2, AC-4
- **関連する設計方針**: DP-2, DP-3
- **テスト種別**: 静的解析 + E2E
- **テスト方法**: grep + pytest
- **前提条件**:
  1. 実装完了後
- **テスト手順**:
  1. SecretAnalyzerの呼び出し箇所をgrepで確認
  2. requiredSecretsの参照箇所をgrepで確認
  3. getRequiredSecretsの呼び出し箇所をgrepで確認
  4. E2Eテストで実際の動作を確認
- **期待結果**:
  - 各新規コードが1箇所以上から参照されている
  - E2Eテストで機能が動作する
- **pytestメソッド**: `test_tc_010_dead_code_verification`

---

## 8. テスト実行計画

### 実行順序
1. サービス起動確認（ヘルスチェック）
2. テスト環境変数の設定確認
3. テストワークフローの登録確認
4. 単体テスト実行（npm test）
5. pytest受入テスト実行
6. パフォーマンステスト実行
7. デッドコード検証

### 実行コマンド

```bash
# 1. サービス起動
cd mySwiftAgentCore
npm run dev &

# 2. ヘルスチェック
curl -sf http://localhost:8006/health && echo "Service healthy"

# 3. 単体テスト実行
npm test -- --coverage

# 4. pytest受入テスト実行
cd mySwiftAgentCore
uv run pytest tests/acceptance/test_issue_377_acceptance.py -v -s
```

### 成功基準
- [ ] すべての単体テストがパス（カバレッジ90%以上）
- [ ] すべての結合テストがパス
- [ ] すべてのpytest受入テストがパス（TC-001〜TC-010）
- [ ] すべての受入条件が検証済み（AC-1〜AC-8）
- [ ] すべての設計方針が検証済み（DP-1〜DP-6）
- [ ] デッドコードが検出されないこと（F-1〜F-5）
- [ ] パフォーマンス劣化なし（既存実装と同等以下）

---

## 9. 補足事項

### コンポーネント間整合性検証

#### CI-1: NodeExecutor実装整合性
- **検証対象**: LlmNode, ApiRestNode, 他のNodeExecutor実装
- **確認項目**:
  - [ ] 全てのNodeExecutorがNodeExecutorインターフェースに準拠
  - [ ] requiredSecrets/getRequiredSecretsの実装が一貫している
  - [ ] 型定義が正しい

#### CI-2: SecretManager連携整合性
- **検証対象**: SecretAnalyzer, handlers.ts, SecretManager
- **確認項目**:
  - [ ] SecretAnalyzerがSecretManagerを正しく使用
  - [ ] キャッシュ戦略が維持されている（5分TTL）
  - [ ] MyVault/環境変数フォールバックが正しく動作

### テストデータ準備
```bash
# テストワークフロー配置先
mySwiftAgentCore/config/workflows/default_project/

# 必要なファイル
- test_llm_workflow.yaml
- test_api_workflow.yaml
- test_api_workflow_with_auth.yaml
- test_complex_workflow.yaml
- test_no_secrets_workflow.yaml
```

### 受入テストファイル
```python
# tests/acceptance/test_issue_377_acceptance.py
# 上記TC-001〜TC-010を実装
```

---

*作成日: 2026-01-19*
*作成者: acceptance-plan-agent*
*Issue: #377*

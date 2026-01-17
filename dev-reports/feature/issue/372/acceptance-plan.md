# 受入テスト計画書

**Issue**: #372
**作成日**: 2026-01-17
**作成者**: acceptance-plan スキル

---

## 1. 概要

### 対象Issue
- **番号**: #372
- **タイトル**: feat(mySwiftAgentCore): ケイパビリティAPIエンドポイントのベースURL解決機能
- **プロジェクト**: mySwiftAgentCore

### 参照ドキュメント
- Issue: #372
- 設計方針書: `dev-reports/feature/issue/372/design-policy.md`
- 関連Issue: #363 (TaskFlow実行エンジン), #364 (taskflowGeneratorAgent), #365 (ケイパビリティ管理)

### 問題の背景
- capability の `_internal.endpoint` は相対パス（例: `/v1/utility/gmail/search`）
- `ApiRestNode` は完全なURL（例: `http://localhost:8004/v1/utility/gmail/search`）を期待
- ベースURL解決機能を追加して、環境ごと（local/Docker/production）でURL切り替えを可能にする

---

## 2. 単体テスト結果レビュー

### TDD実装前の状態
- **状態**: TDD実装前（受入テスト計画立案フェーズ）
- **カバレッジ**: N/A（実装後に測定）
- **目標**: 90%以上

### 既存の関連テストファイル
| ファイル | 説明 |
|---------|------|
| `YamlLoader.test.ts` | YAML読み込みテスト |
| `CapabilityRegistry.test.ts` | レジストリテスト |
| `ApiRestNode.test.ts` | REST API実行テスト |
| `PromptBuilder.test.ts` | プロンプト生成テスト |

### TDD実装後に確認すべき項目
- [ ] EndpointConfigManager の単体テストカバレッジ
- [ ] URLResolver の単体テストカバレッジ
- [ ] CapabilityExecutor の単体テストカバレッジ
- [ ] モック使用率が適切か（外部APIのみモック）

---

## 3. 受入条件分析

### AC-1: api_endpoints読み込み
- **原文**: CapabilityLoader が index.yaml の api_endpoints を読み込める
- **分類**: 機能要件
- **テスト方法**: pytest（単体テスト）
- **モック使用**: 不可
- **検証ポイント**:
  1. index.yaml が正常にパースされる
  2. api_endpoints セクションが取得できる
  3. expert_agent, google_apis, graphai_server の設定が読み込まれる

### AC-2: 環境変数解決
- **原文**: CapabilityLoader が環境変数 `${VAR:-default}` 形式を解決できる
- **分類**: 機能要件
- **テスト方法**: pytest（単体テスト + 結合テスト）
- **モック使用**: 不可
- **検証ポイント**:
  1. `${VAR:-default}` 形式が正しく解決される
  2. 環境変数が設定されている場合、その値が使用される
  3. 環境変数が設定されていない場合、デフォルト値が使用される
  4. ネストした環境変数のパース（例: `${A:-${B:-default}}`）

### AC-3: api_sourceによるベースURL特定
- **原文**: 各ケイパビリティの `_internal.api_source` からベースURLを特定できる
- **分類**: 機能要件
- **テスト方法**: pytest（単体テスト + 結合テスト）
- **モック使用**: 不可
- **検証ポイント**:
  1. capability に api_source がある場合、対応するベースURLが使用される
  2. 無効な api_source の場合、適切なエラーが返される

### AC-4: endpoint_prefixフォールバック
- **原文**: `api_source` がない場合、`endpoint_prefix` でフォールバック解決できる
- **分類**: 機能要件
- **テスト方法**: pytest（単体テスト + 結合テスト）
- **モック使用**: 不可
- **検証ポイント**:
  1. api_source がない場合、endpoint でプレフィックスマッチング
  2. `/v1/` で始まるエンドポイントは expert_agent にマッチ
  3. 複数マッチする場合の優先順位が正しい
  4. マッチしない場合の処理（エラーまたは相対パスのまま）

### AC-5: 完全URLを含むワークフロー生成
- **原文**: taskflowGeneratorAgent が完全URLを含むワークフローを生成できる
- **分類**: 機能要件（E2E）
- **テスト方法**: pytest + 実LLM呼び出し
- **モック使用**: 一部可（LLMをモックしない場合）
- **検証ポイント**:
  1. 生成されたワークフローの api_rest ステップに完全URLが含まれる
  2. または capability_id が含まれる（ApiRestNode拡張方式）
  3. URLが正しい形式（http://... または https://...）

### AC-6: taskflowEngineでの実行
- **原文**: 生成されたワークフローが taskflowEngine で正常に実行できる
- **分類**: 機能要件（E2E）
- **テスト方法**: pytest + 実サービス呼び出し
- **モック使用**: 不可
- **検証ポイント**:
  1. taskflowEngine でワークフロー実行が成功
  2. 実際のAPI呼び出しが正常に完了
  3. 期待するレスポンスが返される

### AC-7: 環境変数オーバーライド
- **原文**: 環境変数 `EXPERT_AGENT_BASE_URL` でベースURLをオーバーライドできる
- **分類**: 機能要件
- **テスト方法**: pytest + 環境変数操作
- **モック使用**: 不可
- **検証ポイント**:
  1. 環境変数を設定するとデフォルト値が上書きされる
  2. オーバーライドしたURLでAPIが呼び出される
  3. 環境変数削除後、デフォルト値に戻る

### AC-8: 単体テストカバレッジ
- **原文**: 単体テストカバレッジ90%以上
- **分類**: 非機能要件
- **テスト方法**: vitest --coverage
- **モック使用**: N/A
- **検証ポイント**:
  1. 新規実装コードのカバレッジ90%以上
  2. 主要なブランチがカバーされている

---

## 4. 設計方針検証

### DP-1: コンポーネント構成
- **設計方針**: EndpointConfigManager、URLResolver、CapabilityExecutor の3コンポーネント構成
- **検証方法**: コード構造確認
- **テスト項目**:
  1. `mySwiftAgentCore/src/capabilityManagement/endpoint/` ディレクトリが存在
  2. EndpointConfigManager.ts が存在し、設計仕様通りのAPI
  3. URLResolver.ts が存在し、設計仕様通りのAPI
  4. CapabilityExecutor.ts が存在し、設計仕様通りのAPI

### DP-2: ApiRestNode拡張
- **設計方針**: ApiRestNodeに capability_id パラメータを追加
- **検証方法**: コード確認 + APIテスト
- **テスト項目**:
  1. ApiRestNodeConfig に capability_id が追加されている
  2. capability_id 指定時に CapabilityExecutor 経由で実行
  3. url 指定時は従来通りの動作（後方互換性）

### DP-3: 環境変数形式
- **設計方針**: `${VAR:-default}` 形式の環境変数解決
- **検証方法**: 単体テスト + 結合テスト
- **テスト項目**:
  1. 正規表現 `/\$\{([^}]+)\}/g` によるパターンマッチング
  2. `split(':-')` によるデフォルト値分離
  3. `process.env` からの値取得

### DP-4: index.yaml設定形式
- **設計方針**: api_endpoints セクションをindex.yamlに追加
- **検証方法**: 設定ファイル読み込みテスト
- **テスト項目**:
  1. api_endpoints.expert_agent.base_url が読み込める
  2. api_endpoints.expert_agent.endpoint_prefix が読み込める
  3. YAML形式が正しくパースされる

---

## 5. デッドコード検証計画

### F-1: EndpointConfigManager
- **ファイル**: `mySwiftAgentCore/src/capabilityManagement/endpoint/EndpointConfigManager.ts`
- **種別**: class
- **期待される呼び出し元**: URLResolver, CapabilityLoader
- **検証方法**:
  ```bash
  grep -rn "EndpointConfigManager" mySwiftAgentCore/src --include="*.ts" | grep -v "\.test\.ts"
  ```
- **E2E確認**: API実行時にベースURLが解決されることを確認

### F-2: URLResolver
- **ファイル**: `mySwiftAgentCore/src/capabilityManagement/endpoint/URLResolver.ts`
- **種別**: class
- **期待される呼び出し元**: CapabilityExecutor
- **検証方法**:
  ```bash
  grep -rn "URLResolver" mySwiftAgentCore/src --include="*.ts" | grep -v "\.test\.ts"
  ```
- **E2E確認**: capability_id 指定時にURLが正しく解決されることを確認

### F-3: CapabilityExecutor
- **ファイル**: `mySwiftAgentCore/src/taskflowEngine/nodes/CapabilityExecutor.ts`
- **種別**: class
- **期待される呼び出し元**: ApiRestNodeExecutor
- **検証方法**:
  ```bash
  grep -rn "CapabilityExecutor\|capabilityExecutor" mySwiftAgentCore/src --include="*.ts" | grep -v "\.test\.ts"
  ```
- **E2E確認**: TaskFlow実行時にcapabilityが実行されることを確認

### F-4: resolveEnvVars関数
- **ファイル**: `mySwiftAgentCore/src/capabilityManagement/endpoint/EndpointConfigManager.ts`
- **種別**: function
- **期待される呼び出し元**: EndpointConfigManager内部
- **検証方法**:
  ```bash
  grep -rn "resolveEnvVars" mySwiftAgentCore/src --include="*.ts"
  ```
- **E2E確認**: 環境変数が解決されたURLでAPIが呼び出されることを確認

---

## 6. テスト環境

### 必須サービス
| サービス | URL | ヘルスチェック |
|---------|-----|--------------|
| mySwiftAgentCore | http://localhost:3000 | GET /health |
| expertAgent | http://localhost:8004 | GET /health |
| myVault | http://localhost:8003 | GET /health |

### 起動コマンド
```bash
# 推奨: ハイブリッドモード（Platform=Docker, Agent=ローカル）
./scripts/dev-hybrid.sh

# または: Docker全環境
make dev-all
```

### 環境変数
| 変数名 | 説明 | 必須 | デフォルト |
|--------|------|------|----------|
| EXPERT_AGENT_BASE_URL | expertAgent API | No | http://localhost:8004 |
| GRAPHAI_SERVER_BASE_URL | graphAiServer API | No | http://localhost:8005 |
| MYVAULT_BASE_URL | MyVault API | No | http://localhost:8003 |
| API_TOKEN | API認証トークン | Yes | - |

### テストデータ
- google_search capability の定義（YAML）
- gmail_send capability の定義（YAML）
- サンプルワークフロー定義（JSON）

---

## 7. テスト項目

### TC-001: api_endpoints読み込みテスト
- **テスト観点**: index.yaml の api_endpoints が正しく読み込めるか
- **関連する受入条件**: AC-1
- **関連する設計方針**: DP-4
- **テスト種別**: 単体テスト
- **テスト方法**: vitest
- **前提条件**:
  1. index.yaml に api_endpoints セクションが存在
  2. expert_agent, google_apis 等の設定が定義済み
- **テスト手順**:
  1. EndpointConfigManager を初期化
  2. loadProjectEndpoints('default_project') を呼び出し
  3. 結果を検証
- **期待結果**:
  - expert_agent.base_url が取得できる
  - endpoint_prefix が取得できる
- **pytestメソッド**: `test_tc_001_load_api_endpoints`

### TC-002: 環境変数解決テスト（設定あり）
- **テスト観点**: 環境変数が設定されている場合の値解決
- **関連する受入条件**: AC-2, AC-7
- **関連する設計方針**: DP-3
- **テスト種別**: 単体テスト
- **テスト方法**: vitest
- **前提条件**:
  1. EXPERT_AGENT_BASE_URL=http://custom-host:9000 を設定
- **テスト手順**:
  1. 環境変数を設定
  2. resolveEnvVars('${EXPERT_AGENT_BASE_URL:-http://localhost:8004}') を呼び出し
  3. 結果を検証
  4. 環境変数をクリア
- **期待結果**:
  - 結果: `http://custom-host:9000`
- **pytestメソッド**: `test_tc_002_resolve_env_var_with_value`

### TC-003: 環境変数解決テスト（デフォルト値）
- **テスト観点**: 環境変数が未設定の場合のデフォルト値使用
- **関連する受入条件**: AC-2
- **関連する設計方針**: DP-3
- **テスト種別**: 単体テスト
- **テスト方法**: vitest
- **前提条件**:
  1. EXPERT_AGENT_BASE_URL が未設定
- **テスト手順**:
  1. 環境変数が未設定であることを確認
  2. resolveEnvVars('${EXPERT_AGENT_BASE_URL:-http://localhost:8004}') を呼び出し
  3. 結果を検証
- **期待結果**:
  - 結果: `http://localhost:8004`
- **pytestメソッド**: `test_tc_003_resolve_env_var_default`

### TC-004: api_sourceによるURL解決テスト
- **テスト観点**: api_source 指定によるベースURL特定
- **関連する受入条件**: AC-3
- **関連する設計方針**: DP-1
- **テスト種別**: 単体テスト
- **テスト方法**: vitest
- **前提条件**:
  1. capability に api_source: 'expert_agent' が設定
  2. api_endpoints に expert_agent が定義済み
- **テスト手順**:
  1. URLResolver を初期化
  2. capability の URL を解決
  3. 結果を検証
- **期待結果**:
  - URL: `http://localhost:8004/v1/utility/google_search`
- **pytestメソッド**: `test_tc_004_resolve_url_by_api_source`

### TC-005: endpoint_prefixフォールバックテスト
- **テスト観点**: api_source 未設定時のプレフィックスマッチング
- **関連する受入条件**: AC-4
- **関連する設計方針**: DP-1
- **テスト種別**: 単体テスト
- **テスト方法**: vitest
- **前提条件**:
  1. capability に api_source が未設定
  2. endpoint: '/v1/utility/gmail/search'
  3. expert_agent の endpoint_prefix: '/v1/'
- **テスト手順**:
  1. URLResolver を初期化
  2. api_source なしの capability の URL を解決
  3. 結果を検証
- **期待結果**:
  - URL: `http://localhost:8004/v1/utility/gmail/search`
- **pytestメソッド**: `test_tc_005_resolve_url_by_prefix_fallback`

### TC-006: ApiRestNode capability_id 実行テスト
- **テスト観点**: capability_id 指定時の実行
- **関連する受入条件**: AC-6
- **関連する設計方針**: DP-2
- **テスト種別**: 結合テスト
- **テスト方法**: vitest + API呼び出し
- **前提条件**:
  1. expertAgent が起動している
  2. capability_id: 'google_search' が定義済み
- **テスト手順**:
  1. ApiRestNodeExecutor を初期化
  2. capability_id 指定で execute を呼び出し
  3. 結果を検証
- **期待結果**:
  - 実際のAPIが呼び出される
  - レスポンスが返される
- **pytestメソッド**: `test_tc_006_api_rest_node_with_capability_id`

### TC-007: 後方互換性テスト（直接URL指定）
- **テスト観点**: 従来の直接URL指定が引き続き動作する
- **関連する受入条件**: AC-6
- **関連する設計方針**: DP-2
- **テスト種別**: 結合テスト
- **テスト方法**: vitest
- **前提条件**:
  1. expertAgent が起動している
- **テスト手順**:
  1. ApiRestNodeExecutor を初期化
  2. url 直接指定で execute を呼び出し
  3. 結果を検証
- **期待結果**:
  - 従来通りの動作
  - capability_id なしでも動作
- **pytestメソッド**: `test_tc_007_api_rest_node_with_direct_url`

### TC-008: E2E ワークフロー実行テスト
- **テスト観点**: 生成されたワークフローがTaskFlowEngineで実行できる
- **関連する受入条件**: AC-5, AC-6
- **関連する設計方針**: DP-1, DP-2
- **テスト種別**: E2E
- **テスト方法**: pytest + 実サービス
- **前提条件**:
  1. mySwiftAgentCore が起動している
  2. expertAgent が起動している
  3. API_TOKEN が設定されている
- **テスト手順**:
  1. サービスヘルスチェック
  2. POST /api/v1/taskflow/execute でワークフロー実行
  3. 結果を検証
- **期待結果**:
  - HTTPステータス: 200
  - ワークフロー実行成功
  - capability のAPI呼び出し成功
- **curlコマンド**:
  ```bash
  curl -s -X POST http://localhost:3000/api/v1/taskflow/execute \
    -H "Content-Type: application/json" \
    -H "X-API-Token: ${API_TOKEN}" \
    -d '{
      "project": "default_project",
      "workflow": "test_workflow",
      "inputs": {}
    }'
  ```
- **pytestメソッド**: `test_tc_008_e2e_workflow_execution`

### TC-009: 環境変数オーバーライドE2Eテスト
- **テスト観点**: 環境変数変更が実行時に反映される
- **関連する受入条件**: AC-7
- **関連する設計方針**: DP-3
- **テスト種別**: E2E
- **テスト方法**: pytest + 環境変数操作
- **前提条件**:
  1. 各サービスが起動している
- **テスト手順**:
  1. EXPERT_AGENT_BASE_URL を別のURLに設定
  2. ワークフロー実行
  3. 呼び出し先URLを確認（ログまたはモック）
  4. 環境変数をリセット
- **期待結果**:
  - オーバーライドしたURLにリクエストが送信される
- **pytestメソッド**: `test_tc_009_env_override_e2e`

### TC-010: エラーハンドリングテスト（無効な api_source）
- **テスト観点**: 無効な api_source 指定時のエラー処理
- **関連する受入条件**: AC-3
- **関連する設計方針**: DP-1
- **テスト種別**: 単体テスト
- **テスト方法**: vitest
- **前提条件**:
  1. capability に api_source: 'invalid_source' が設定
- **テスト手順**:
  1. URLResolver を初期化
  2. 無効な api_source の capability を渡す
  3. エラーを検証
- **期待結果**:
  - EndpointResolutionError がスローされる
  - エラーメッセージに api_source が含まれる
- **pytestメソッド**: `test_tc_010_invalid_api_source_error`

### TC-011: エラーハンドリングテスト（マッチするプレフィックスなし）
- **テスト観点**: プレフィックスマッチングで一致しない場合
- **関連する受入条件**: AC-4
- **関連する設計方針**: DP-1
- **テスト種別**: 単体テスト
- **テスト方法**: vitest
- **前提条件**:
  1. capability に api_source 未設定
  2. endpoint: '/unknown/endpoint'（どのプレフィックスにもマッチしない）
- **テスト手順**:
  1. URLResolver を初期化
  2. マッチしないエンドポイントを渡す
  3. エラーを検証
- **期待結果**:
  - EndpointResolutionError がスローされる
  - エラーメッセージにエンドポイントが含まれる
- **pytestメソッド**: `test_tc_011_no_matching_prefix_error`

---

## 8. テスト実行計画

### 実行順序
1. サービス起動確認（ヘルスチェック）
   ```bash
   curl -s http://localhost:3000/health
   curl -s http://localhost:8004/health
   ```
2. 単体テスト実行
   ```bash
   cd mySwiftAgentCore && npm test -- --coverage
   ```
3. 結合テスト実行
   ```bash
   cd mySwiftAgentCore && npm test -- tests/integration/
   ```
4. 受入テスト実行
   ```bash
   cd mySwiftAgentCore && npm test -- tests/acceptance/test_issue_372_acceptance.ts
   ```

### 成功基準
- [ ] すべての単体テストがパス
- [ ] 単体テストカバレッジ90%以上
- [ ] すべての結合テストがパス
- [ ] すべての受入テストがパス
- [ ] すべての受入条件（AC-1〜AC-8）が検証済み
- [ ] デッドコードが検出されない（F-1〜F-4が実際に使用されている）
- [ ] 設計方針（DP-1〜DP-4）が実装に反映されている

---

## 9. 補足事項

### コンポーネント間整合性検証

#### CI-1: URLバリデータ整合性
- **検証対象**: URLResolver と ApiRestNode のURL検証
- **確認項目**:
  - [ ] URLの形式検証が一貫している
  - [ ] http/https の取り扱いが一貫している

#### CI-2: 環境変数パターン整合性
- **検証対象**: resolveEnvVars と既存の環境変数処理
- **確認項目**:
  - [ ] `${VAR:-default}` 形式が全箇所で統一
  - [ ] security.ts との環境変数処理が整合

### 実行時の注意事項

1. **環境変数の設定**
   - テスト実行前に `API_TOKEN` が設定されていることを確認
   - 環境変数オーバーライドテストでは、テスト後に必ず元の値に戻す

2. **サービス依存**
   - expertAgent はAPIモック不可（実際の呼び出しをテスト）
   - myVault はシークレット取得に必要

3. **並行実行**
   - 環境変数を操作するテストは直列実行を推奨
   - 他のテストとの競合を避けるため

### 推奨改善項目（アーキテクチャレビューより）

1. **URL検証の追加**: 構築されたURLの妥当性検証
2. **起動時の設定検証**: 全capabilityのURL解決可能性検証
3. **エンドポイントマッチングの明確化**: アルゴリズムのドキュメント化

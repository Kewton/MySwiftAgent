# 受入テスト計画書

**Issue**: #365
**作成日**: 2026-01-16
**作成者**: acceptance-plan (slash command)

---

## 1. 概要

### 対象Issue
- **番号**: #365
- **タイトル**: feat(mySwiftAgentCore): capabilityManagement - Capability一元管理システムの実装
- **プロジェクト**: mySwiftAgentCore

### 参照ドキュメント
- Issue: #365
- 設計方針書: `dev-reports/feature/issue/365/design-policy.md`
- 作業計画書: `dev-reports/feature/issue/365/work-plan.md`

---

## 2. 単体テスト結果レビュー

### カバレッジ
- 現在: N/A（TDD未実施）
- 目標: 90%
- 判定: ⏳ TDD実装待ち

### 実装状況（事前確認）

| コンポーネント | 状態 | ファイル |
|--------------|------|---------|
| 型定義拡張 | ✅ 完了 | `src/shared/types/capability.types.ts` |
| YamlLoader | ✅ 完了 | `src/capabilityManagement/loader/YamlLoader.ts` |
| CapabilitySanitizer | ✅ 完了 | `src/capabilityManagement/loader/YamlLoader.ts` |
| CapabilityRegistry（プロジェクト対応） | ⬜ 未実装 | `src/capabilityManagement/registry/CapabilityRegistry.ts` |
| ProjectManager | ⬜ 未実装 | `src/capabilityManagement/registry/ProjectManager.ts` |
| API routes | ⬜ 未実装 | `src/capabilityManagement/api/routes.ts` |
| API handlers | ⬜ 未実装 | `src/capabilityManagement/api/handlers.ts` |
| CapabilityClient | ⬜ 未実装 | `src/capabilityManagement/client/CapabilityClient.ts` |
| 単体テスト | ⬜ 未実装 | `tests/unit/capabilityManagement/*.test.ts` |

### 単体テストでカバーすべき項目
1. YamlLoader: YAMLファイル読込、スキーマ検証、部分的失敗処理
2. CapabilitySanitizer: `_internal`セクション除外
3. CapabilityRegistry: プロジェクト単位の登録・取得
4. ProjectManager: プロジェクト管理、共有capability参照
5. API handlers: リクエスト処理、エラーハンドリング
6. CapabilityClient: HTTP通信、エラーハンドリング

---

## 3. 受入条件分析

### AC-1: プロジェクト単位でcapabilitiesを管理できる
- **原文**: プロジェクト単位でcapabilitiesを管理できる
- **分類**: 機能要件
- **テスト方法**: pytest / curl
- **モック使用**: 不可
- **検証ポイント**:
  1. `config/capabilities/default_project/`ディレクトリに複数のYAMLファイルを配置できる
  2. プロジェクトID指定でcapabilitiesを取得できる
  3. 異なるプロジェクト間でcapabilitiesが分離されている

### AC-2: 既存YAMLファイルがdefault_projectに移行されている
- **原文**: 既存YAMLファイルがdefault_projectに移行されている
- **分類**: 機能要件
- **テスト方法**: ファイル確認 + API呼び出し
- **モック使用**: 不可
- **検証ポイント**:
  1. `expertAgent/aiagent/.../api_info/`から移行されたYAMLが存在する
  2. 移行後のYAMLが正しいスキーマに従っている
  3. APIから移行されたcapabilitiesを取得できる

### AC-3: REST API経由でcapabilitiesを取得できる
- **原文**: REST API経由でcapabilitiesを取得できる
- **分類**: 機能要件
- **テスト方法**: curl / pytest
- **モック使用**: 不可
- **検証ポイント**:
  1. `GET /api/v1/capabilities?project=default_project` が成功する
  2. `GET /api/v1/capabilities/{id}?project=default_project` が成功する
  3. 認証なしアクセスが401で拒否される
  4. 認証ありアクセスが200で成功する

### AC-4: クライアント向けレスポンスから内部詳細（`_internal`）が除外される
- **原文**: クライアント向けレスポンスから内部詳細（`_internal`）が除外される
- **分類**: セキュリティ要件
- **テスト方法**: curl + JSON検証
- **モック使用**: 不可
- **検証ポイント**:
  1. APIレスポンスに`_internal`フィールドが含まれない
  2. `endpoint`、`secret_key`などの内部情報が露出しない
  3. 複数capability取得時も全てから`_internal`が除外される

### AC-5: YAML形式でcapabilitiesを返却できる
- **原文**: YAML形式でcapabilitiesを返却できる
- **分類**: 機能要件
- **テスト方法**: curl
- **モック使用**: 不可
- **検証ポイント**:
  1. `GET /api/v1/capabilities/yaml?project=default_project` が成功する
  2. レスポンスがYAML形式である（Content-Type: text/yaml）
  3. YAML内に`_internal`が含まれない

### AC-6: expertAgent（Python）からHTTP経由で利用できる
- **原文**: expertAgent（Python）からHTTP経由で利用できる
- **分類**: 機能要件（統合）
- **テスト方法**: Python httpx
- **モック使用**: 不可
- **検証ポイント**:
  1. PythonからHTTP GETリクエストが成功する
  2. JSON形式でcapabilitiesを取得できる
  3. YAML形式でcapabilitiesを取得できる

### AC-7: 単体テストカバレッジ90%以上
- **原文**: 単体テストカバレッジ90%以上
- **分類**: 品質要件
- **テスト方法**: カバレッジレポート確認
- **モック使用**: 単体テスト内では可
- **検証ポイント**:
  1. `npm run test:coverage` でカバレッジ90%以上
  2. 主要パスがテストされている
  3. エッジケースがテストされている

---

## 4. 設計方針検証

### DP-1: アーキテクチャ整合性
- **設計方針**: Registry/Loader/Sanitizer/APIの分離構造
- **検証方法**: コード構造確認
- **テスト項目**:
  1. `src/capabilityManagement/registry/` にRegistry関連コードが存在する
  2. `src/capabilityManagement/loader/` にLoader関連コードが存在する
  3. `src/capabilityManagement/api/` にAPI関連コードが存在する
  4. 各モジュールが独立してテスト可能である

### DP-2: API設計整合性
- **設計方針**: RESTful API（設計方針書Section 5）
- **検証方法**: curl / pytest
- **テスト項目**:
  1. `GET /api/v1/capabilities` エンドポイントが存在する
  2. `GET /api/v1/capabilities/{id}` エンドポイントが存在する
  3. `GET /api/v1/capabilities/yaml` エンドポイントが存在する
  4. `POST /api/v1/capabilities` エンドポイントが存在する（Admin権限必要）
  5. クエリパラメータ `project` が機能する
  6. 認証ヘッダー `Authorization: Bearer {token}` が機能する

### DP-3: セキュリティ設計整合性
- **設計方針**: JSON_SCHEMAによる安全なYAML読込、_internal除外
- **検証方法**: コード確認 + APIテスト
- **テスト項目**:
  1. YamlLoaderが`yaml.JSON_SCHEMA`を使用している
  2. 悪意のあるYAMLタグ（`!!python/object`等）が拒否される
  3. APIレスポンスに`_internal`が含まれない
  4. 認証なしアクセスが拒否される

### DP-4: データモデル整合性
- **設計方針**: CapabilityExtended型、CapabilityInternal型
- **検証方法**: コード確認 + API応答検証
- **テスト項目**:
  1. `capability.types.ts`にCapabilityExtended型が定義されている
  2. `capability.types.ts`にCapabilityInternal型が定義されている
  3. YAMLファイルが`_internal`セクションを含む形式で読み込める
  4. APIレスポンスがPublicCapability型に準拠している

---

## 5. デッドコード検証計画

### F-1: YamlLoader
- **ファイル**: `src/capabilityManagement/loader/YamlLoader.ts`
- **種別**: class
- **期待される呼び出し元**: CapabilityRegistry, API handlers
- **検証方法**:
  ```bash
  grep -rn "YamlLoader\|createYamlLoader" --include="*.ts" | grep -v "YamlLoader.ts" | grep -v "\.test\.ts"
  ```
- **E2E確認**: APIを呼び出してYAMLファイルが正しく読み込まれることを確認

### F-2: CapabilitySanitizer
- **ファイル**: `src/capabilityManagement/loader/YamlLoader.ts`
- **種別**: class
- **期待される呼び出し元**: API handlers
- **検証方法**:
  ```bash
  grep -rn "CapabilitySanitizer\|createSanitizer" --include="*.ts" | grep -v "YamlLoader.ts" | grep -v "\.test\.ts"
  ```
- **E2E確認**: APIレスポンスに`_internal`が含まれないことを確認

### F-3: CapabilityExtendedSchema（Zodスキーマ）
- **ファイル**: `src/shared/types/capability.types.ts`
- **種別**: constant
- **期待される呼び出し元**: YamlLoader.validate()
- **検証方法**:
  ```bash
  grep -rn "CapabilityExtendedSchema" --include="*.ts" | grep -v "capability.types.ts" | grep -v "\.test\.ts"
  ```
- **E2E確認**: 不正なYAMLがバリデーションエラーで拒否されることを確認

### F-4: CapabilityRegistry（プロジェクト対応版）- TDD実装後に追加
- **ファイル**: `src/capabilityManagement/registry/CapabilityRegistry.ts`（予定）
- **種別**: class
- **期待される呼び出し元**: API handlers
- **検証方法**: grep + E2Eテスト
- **E2E確認**: プロジェクト指定でcapabilitiesが正しく取得できること

### F-5: API Routes - TDD実装後に追加
- **ファイル**: `src/capabilityManagement/api/routes.ts`（予定）
- **種別**: function
- **期待される呼び出し元**: app.ts（メインアプリケーション）
- **検証方法**: grep + APIテスト
- **E2E確認**: APIエンドポイントが正常に応答すること

---

## 6. テスト環境

### 必須サービス
| サービス | URL | ヘルスチェック |
|---------|-----|--------------|
| mySwiftAgentCore | http://localhost:8006 | GET /health |

### 起動コマンド
```bash
# mySwiftAgentCore開発サーバー起動
cd mySwiftAgentCore
npm run dev
```

### 環境変数
| 変数名 | 説明 | 必須 |
|--------|------|------|
| API_TOKEN | API認証トークン | ✅ |
| ADMIN_TOKEN | Admin権限トークン（登録時） | ✅ |

### テストデータ
- `config/capabilities/default_project/` にテスト用YAMLファイルを配置
- テスト用capability定義（`google_search.yaml`など）

---

## 7. テスト項目

### TC-001: Capability一覧取得（プロジェクト指定）
- **テスト観点**: プロジェクト単位でcapabilitiesを取得できる
- **関連する受入条件**: AC-1, AC-3
- **関連する設計方針**: DP-2
- **テスト種別**: E2E
- **テスト方法**: curl / pytest
- **前提条件**:
  1. mySwiftAgentCoreが起動している
  2. `config/capabilities/default_project/`にYAMLファイルが存在する
  3. API_TOKENが設定されている
- **テスト手順**:
  1. `GET /api/v1/capabilities?project=default_project`を呼び出す
  2. レスポンスを検証する
- **期待結果**:
  - HTTPステータス: 200
  - レスポンス: `{ "capabilities": [...], "total": N, "project": "default_project" }`
- **curlコマンド**:
  ```bash
  curl -s http://localhost:8006/api/v1/capabilities?project=default_project \
    -H "Authorization: Bearer ${API_TOKEN}" | jq
  ```
- **pytestメソッド**: `test_tc_001_capability_list_by_project`

### TC-002: 特定Capability取得
- **テスト観点**: IDを指定してcapabilityを取得できる
- **関連する受入条件**: AC-3
- **関連する設計方針**: DP-2
- **テスト種別**: E2E
- **テスト方法**: curl / pytest
- **前提条件**:
  1. mySwiftAgentCoreが起動している
  2. `google_search` capabilityが登録されている
- **テスト手順**:
  1. `GET /api/v1/capabilities/google_search?project=default_project`を呼び出す
  2. レスポンスを検証する
- **期待結果**:
  - HTTPステータス: 200
  - レスポンス: `{ "capability_id": "google_search", "name": "...", ... }`
- **curlコマンド**:
  ```bash
  curl -s http://localhost:8006/api/v1/capabilities/google_search?project=default_project \
    -H "Authorization: Bearer ${API_TOKEN}" | jq
  ```
- **pytestメソッド**: `test_tc_002_capability_get_by_id`

### TC-003: _internal除外確認
- **テスト観点**: APIレスポンスから`_internal`が除外される
- **関連する受入条件**: AC-4
- **関連する設計方針**: DP-3
- **テスト種別**: E2E / セキュリティ
- **テスト方法**: curl + JSON検証
- **前提条件**:
  1. mySwiftAgentCoreが起動している
  2. `_internal`セクションを持つcapabilityが登録されている
- **テスト手順**:
  1. capability一覧を取得する
  2. レスポンスに`_internal`が含まれないことを確認する
  3. 特定capability取得でも同様に確認する
- **期待結果**:
  - レスポンスに`_internal`キーが存在しない
  - `endpoint`、`secret_key`等の内部情報が露出しない
- **curlコマンド**:
  ```bash
  # 一覧取得で_internal除外確認
  curl -s http://localhost:8006/api/v1/capabilities?project=default_project \
    -H "Authorization: Bearer ${API_TOKEN}" | jq 'any(.capabilities[]; has("_internal"))'
  # 期待: false
  ```
- **pytestメソッド**: `test_tc_003_internal_excluded`

### TC-004: YAML形式取得
- **テスト観点**: YAML形式でcapabilitiesを取得できる
- **関連する受入条件**: AC-5
- **関連する設計方針**: DP-2
- **テスト種別**: E2E
- **テスト方法**: curl
- **前提条件**:
  1. mySwiftAgentCoreが起動している
  2. capabilitiesが登録されている
- **テスト手順**:
  1. `GET /api/v1/capabilities/yaml?project=default_project`を呼び出す
  2. Content-Typeを確認する
  3. YAML形式であることを確認する
- **期待結果**:
  - HTTPステータス: 200
  - Content-Type: text/yaml
  - レスポンスがYAML形式
- **curlコマンド**:
  ```bash
  curl -s http://localhost:8006/api/v1/capabilities/yaml?project=default_project \
    -H "Authorization: Bearer ${API_TOKEN}" \
    -w "\n\nContent-Type: %{content_type}\n"
  ```
- **pytestメソッド**: `test_tc_004_yaml_format`

### TC-005: 認証なしアクセス拒否
- **テスト観点**: 認証なしアクセスが401で拒否される
- **関連する受入条件**: AC-3
- **関連する設計方針**: DP-3
- **テスト種別**: セキュリティ
- **テスト方法**: curl
- **前提条件**:
  1. mySwiftAgentCoreが起動している
- **テスト手順**:
  1. 認証ヘッダーなしでAPIを呼び出す
  2. 401レスポンスを確認する
- **期待結果**:
  - HTTPステータス: 401 Unauthorized
- **curlコマンド**:
  ```bash
  curl -s http://localhost:8006/api/v1/capabilities?project=default_project \
    -w "\nHTTP Status: %{http_code}\n"
  # 期待: HTTP Status: 401
  ```
- **pytestメソッド**: `test_tc_005_unauthorized_access`

### TC-006: Capability登録（Admin権限）
- **テスト観点**: Admin権限でcapabilityを登録できる
- **関連する受入条件**: AC-1
- **関連する設計方針**: DP-2
- **テスト種別**: E2E
- **テスト方法**: curl / pytest
- **前提条件**:
  1. mySwiftAgentCoreが起動している
  2. ADMIN_TOKENが設定されている
- **テスト手順**:
  1. `POST /api/v1/capabilities`で新規capabilityを登録する
  2. 登録されたcapabilityを取得して確認する
- **期待結果**:
  - 登録: HTTPステータス 201
  - 取得: 登録したcapabilityが返される
- **curlコマンド**:
  ```bash
  curl -s -X POST http://localhost:8006/api/v1/capabilities \
    -H "Authorization: Bearer ${ADMIN_TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{
      "project": "default_project",
      "capability": {
        "id": "test_capability",
        "name": "テストCapability",
        "description": "テスト用",
        "version": "1.0",
        "status": "available",
        "category": "test",
        "parameters": [],
        "returnType": "string"
      }
    }' | jq
  ```
- **pytestメソッド**: `test_tc_006_capability_registration`

### TC-007: 権限不足での登録拒否
- **テスト観点**: 一般トークンでの登録が403で拒否される
- **関連する受入条件**: AC-3
- **関連する設計方針**: DP-3
- **テスト種別**: セキュリティ
- **テスト方法**: curl
- **前提条件**:
  1. mySwiftAgentCoreが起動している
  2. API_TOKEN（非Admin）が設定されている
- **テスト手順**:
  1. 一般トークンでPOSTを試みる
  2. 403レスポンスを確認する
- **期待結果**:
  - HTTPステータス: 403 Forbidden
- **curlコマンド**:
  ```bash
  curl -s -X POST http://localhost:8006/api/v1/capabilities \
    -H "Authorization: Bearer ${API_TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{"project": "test", "capability": {}}' \
    -w "\nHTTP Status: %{http_code}\n"
  # 期待: HTTP Status: 403
  ```
- **pytestメソッド**: `test_tc_007_forbidden_registration`

### TC-008: Python（expertAgent）からの利用
- **テスト観点**: PythonからHTTP経由でcapabilitiesを取得できる
- **関連する受入条件**: AC-6
- **関連する設計方針**: DP-2
- **テスト種別**: 統合
- **テスト方法**: Python httpx
- **前提条件**:
  1. mySwiftAgentCoreが起動している
  2. Pythonからアクセス可能
- **テスト手順**:
  1. Pythonでhttpxを使用してAPIを呼び出す
  2. JSON/YAMLレスポンスを検証する
- **期待結果**:
  - HTTPステータス: 200
  - JSONデコードが成功する
- **Pythonコード**:
  ```python
  import httpx
  import os

  client = httpx.Client(base_url='http://localhost:8006')
  response = client.get(
      '/api/v1/capabilities',
      params={'project': 'default_project'},
      headers={'Authorization': f'Bearer {os.environ["API_TOKEN"]}'}
  )
  assert response.status_code == 200
  data = response.json()
  assert 'capabilities' in data
  ```
- **pytestメソッド**: `test_tc_008_python_integration`

### TC-009: YAML形式でのPython利用（LLMプロンプト用）
- **テスト観点**: PythonからYAML形式でcapabilitiesを取得できる
- **関連する受入条件**: AC-5, AC-6
- **関連する設計方針**: DP-2
- **テスト種別**: 統合
- **テスト方法**: Python httpx
- **前提条件**:
  1. mySwiftAgentCoreが起動している
- **テスト手順**:
  1. YAML形式でcapabilitiesを取得する
  2. YAMLとしてパース可能であることを確認する
- **期待結果**:
  - レスポンスがYAMLとしてパース可能
  - LLMプロンプトに埋め込み可能な形式
- **Pythonコード**:
  ```python
  import httpx
  import yaml
  import os

  client = httpx.Client(base_url='http://localhost:8006')
  response = client.get(
      '/api/v1/capabilities/yaml',
      params={'project': 'default_project'},
      headers={'Authorization': f'Bearer {os.environ["API_TOKEN"]}'}
  )
  assert response.status_code == 200
  # YAMLとしてパース可能であることを確認
  capabilities = yaml.safe_load(response.text)
  assert 'capabilities' in capabilities
  ```
- **pytestメソッド**: `test_tc_009_python_yaml_integration`

### TC-010: セキュアYAML読込（悪意のあるYAML拒否）
- **テスト観点**: 悪意のあるYAMLタグが拒否される
- **関連する受入条件**: N/A（セキュリティ要件）
- **関連する設計方針**: DP-3
- **テスト種別**: セキュリティ
- **テスト方法**: 単体テスト
- **前提条件**:
  1. YamlLoaderが実装されている
- **テスト手順**:
  1. `!!python/object`などの危険なタグを含むYAMLを読み込む
  2. エラーまたは安全な解釈になることを確認する
- **期待結果**:
  - 危険なタグが実行されない
  - エラーまたは文字列として解釈される
- **pytestメソッド**: `test_tc_010_secure_yaml_parsing`

---

## 8. テスト実行計画

### 実行順序
1. サービス起動確認（ヘルスチェック）
   ```bash
   curl -sf http://localhost:8006/health && echo "mySwiftAgentCore healthy"
   ```
2. 単体テスト実行
   ```bash
   cd mySwiftAgentCore && npm run test
   ```
3. pytest受入テスト実行
   ```bash
   cd mySwiftAgentCore && npm run test:acceptance
   # または
   uv run pytest tests/acceptance/test_issue_365_acceptance.py -v
   ```
4. 追加curlテスト実行（手動確認）

### 成功基準
- [ ] すべての単体テストがパス
- [ ] カバレッジ90%以上
- [ ] すべてのpytest受入テストがパス
- [ ] TC-001〜TC-010の全テストケースがパス
- [ ] すべての受入条件（AC-1〜AC-7）が検証済み
- [ ] デッドコードが検出されないこと

---

## 9. コンポーネント間整合性検証

### CI-1: 型定義とZodスキーマの整合性
- **検証対象**: `capability.types.ts`のTypeScript型とZodスキーマ
- **確認項目**:
  - [ ] CapabilityExtended型とCapabilityExtendedSchemaが一致
  - [ ] CapabilityInternal型とCapabilityInternalSchemaが一致
  - [ ] PublicCapability型がCapabilityExtendedから`_internal`を除外

### CI-2: YamlLoaderとCapabilitySanitizerの連携
- **検証対象**: ローダーからサニタイザーへのデータフロー
- **確認項目**:
  - [ ] YamlLoaderが`_internal`を含むデータを正しく読み込む
  - [ ] CapabilitySanitizerが`_internal`を除外する
  - [ ] API層でサニタイズが適用される

### CI-3: APIとレジストリの整合性
- **検証対象**: APIハンドラとCapabilityRegistryの連携
- **確認項目**:
  - [ ] APIがRegistryからデータを取得する
  - [ ] プロジェクトフィルタが正しく適用される
  - [ ] エラーハンドリングが一貫している

---

## 10. 補足事項

### 既存実装の活用
- 既存の`CapabilityManagement`クラスを拡張してプロジェクト対応を追加
- 既存のZod型定義を活用してバリデーションを実装

### 移行対象YAMLファイル
移行元: `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/prompts/api_info/`
- google_search.yaml
- gmail_send.yaml
- その他

### フォールバック機能
- expertAgent側でmySwiftAgentCore接続失敗時に既存YAMLをフォールバックとして使用する機能が必要

### 今後の拡張
- Phase 2で動的capability登録、capability合成、実行履歴分析を追加予定
- Issue #363（TaskFlow Engine）、#364（TaskFlow Generator）との統合

---

**作成日**: 2026-01-16
**作成者**: acceptance-plan (slash command)
**Issue**: #365

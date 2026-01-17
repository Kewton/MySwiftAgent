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
- 設計方針書: **未作成** - Issue本文の設計を参照
- 関連Issue: #364 (taskflowGeneratorAgent), #359 (3フェーズ統一ID方式)

---

## 2. 単体テスト結果レビュー

### テスト結果サマリ
- **総テスト数**: 905 (全プロジェクト)
- **結果**: 全テストPASS
- **capabilityManagement関連テスト**:

| テストファイル | テスト数 | 結果 |
|---------------|---------|------|
| YamlLoader.test.ts | 23 | PASS |
| handlers.test.ts | 15 | PASS |
| CapabilityClient.test.ts | 10 | PASS |
| ProjectManager.test.ts | 17 | PASS |
| index.test.ts | 34 | PASS |
| middleware.test.ts | 11 | PASS |
| routes.test.ts | 3 | PASS |
| CapabilityRegistry.test.ts | 複数 | PASS |
| **合計** | **113+** | **PASS** |

### カバレッジ
- 現在: 92.13% (全体)
- 目標: 90%
- 判定: ✅ PASS

### モック使用の妥当性
- 単体テストでは適切にモックを使用
- E2Eでの実API検証が必要

---

## 3. 受入条件分析

### AC-1: プロジェクト単位でcapabilitiesを管理できる
- **原文**: プロジェクト単位でcapabilitiesを管理できる
- **分類**: 機能要件
- **テスト方法**: pytest / curl
- **検証ポイント**:
  1. プロジェクトごとに異なるcapabilitiesが登録できる
  2. プロジェクト間でcapabilitiesが分離されている
  3. _shared capabilitiesが複数プロジェクトで共有できる

### AC-2: 既存YAMLファイルがdefault_projectに移行されている
- **原文**: 既存YAMLファイルがdefault_projectに移行されている
- **分類**: 機能要件
- **テスト方法**: ファイル存在確認 + API検証
- **検証ポイント**:
  1. config/capabilities/default_project/ にYAMLファイルが存在
  2. index.yamlにcapabilityリストが定義されている
  3. API経由で取得できる

### AC-3: REST API経由でcapabilitiesを取得できる
- **原文**: REST API経由でcapabilitiesを取得できる
- **分類**: 機能要件
- **テスト方法**: curl / pytest
- **検証ポイント**:
  1. GET /api/v1/capabilities?project={project_id} が動作
  2. GET /api/v1/capabilities/{capability_id}?project={project_id} が動作
  3. POST /api/v1/capabilities で登録できる

### AC-4: クライアント向けレスポンスから内部詳細（_internal）が除外される
- **原文**: クライアント向けレスポンスから内部詳細（`_internal`）が除外される
- **分類**: セキュリティ要件
- **テスト方法**: curl / pytest
- **検証ポイント**:
  1. レスポンスに`_internal`フィールドが含まれない
  2. endpoint, auth_type, secret_keyが露出しない

### AC-5: YAML形式でcapabilitiesを返却できる
- **原文**: YAML形式でcapabilitiesを返却できる
- **分類**: 機能要件
- **テスト方法**: curl / pytest
- **検証ポイント**:
  1. Accept: application/yaml でYAML形式が返る
  2. LLMプロンプト用のフォーマットになっている

### AC-6: expertAgent（Python）からHTTP経由で利用できる
- **原文**: expertAgent（Python）からHTTP経由で利用できる
- **分類**: 結合要件
- **テスト方法**: Python pytest
- **検証ポイント**:
  1. Pythonクライアントからアクセス可能
  2. job_analyzerプロンプトにcapabilitiesを含められる

### AC-7: 単体テストカバレッジ90%以上
- **原文**: 単体テストカバレッジ90%以上
- **分類**: 品質要件
- **テスト方法**: vitest --coverage
- **検証ポイント**:
  1. カバレッジ92.13% (✅ 達成済み)

---

## 4. 設計方針検証

※ design-policy.mdが存在しないため、Issue本文の設計を基に検証

### DP-1: ディレクトリ構成
- **設計方針**: src/capabilityManagement/ 配下に機能を配置
- **検証方法**: ファイル構造確認
- **テスト項目**:
  1. registry/, loader/, api/, client/ サブディレクトリが存在
  2. 各モジュールがindex.tsからエクスポートされている

### DP-2: Capability定義スキーマ
- **設計方針**: YAML形式でcapability_id, name, inputs, outputs, _internalを定義
- **検証方法**: YAMLファイル検証
- **テスト項目**:
  1. 必須フィールドが定義されている
  2. inputs/outputsが正しく定義されている

### DP-3: API設計
- **設計方針**: REST API（GET /api/v1/capabilities, POST /api/v1/capabilities）
- **検証方法**: curl / pytest
- **テスト項目**:
  1. エンドポイントが設計通り
  2. リクエスト/レスポンス形式が設計通り

### DP-4: セキュリティ設計
- **設計方針**: _internalフィールドをクライアントに非公開
- **検証方法**: レスポンス検証
- **テスト項目**:
  1. Sanitizerが_internalを除外
  2. secret_keyが露出しない

---

## 5. デッドコード検証計画

### F-1: CapabilityManagement class
- **ファイル**: src/capabilityManagement/index.ts
- **種別**: class
- **検証方法**: Grep / API呼び出し
- **E2E確認**: APIからcapabilitiesを取得

### F-2: CapabilityRegistry class
- **ファイル**: src/capabilityManagement/registry/CapabilityRegistry.ts
- **種別**: class
- **検証方法**: handlers.tsでの使用確認
- **E2E確認**: POST /api/v1/capabilitiesでcapability登録

### F-3: ProjectManager class
- **ファイル**: src/capabilityManagement/registry/ProjectManager.ts
- **種別**: class
- **検証方法**: handlers.tsでの使用確認
- **E2E確認**: プロジェクトパラメータでのAPI呼び出し

### F-4: YamlLoader class
- **ファイル**: src/capabilityManagement/loader/YamlLoader.ts
- **種別**: class
- **検証方法**: 初期化時のYAML読み込み確認
- **E2E確認**: YAMLファイルからのcapability取得

### F-5: CapabilitySanitizer class
- **ファイル**: src/capabilityManagement/loader/YamlLoader.ts
- **種別**: class
- **検証方法**: _internal除外確認
- **E2E確認**: レスポンスに_internalがないこと

### F-6: CapabilityClient class
- **ファイル**: src/capabilityManagement/client/CapabilityClient.ts
- **種別**: class
- **検証方法**: 外部からの利用確認
- **E2E確認**: Python clientからの呼び出し

### F-7: API routes
- **ファイル**: src/capabilityManagement/api/routes.ts
- **種別**: function
- **検証方法**: main routerへのマウント確認
- **E2E確認**: /api/v1/capabilitiesへのアクセス

---

## 6. テスト環境

### 必須サービス
| サービス | URL | ヘルスチェック |
|---------|-----|--------------|
| mySwiftAgentCore | http://localhost:8006 | GET /health |
| expertAgent | http://localhost:8004 | GET /health |
| myVault | http://localhost:8003 | GET /health |

### 起動コマンド
```bash
# 推奨: ハイブリッドモード
./scripts/dev-hybrid.sh

# mySwiftAgentCoreのみ（dev-reportsディレクトリ内）
cd mySwiftAgentCore && npm run dev
```

### 環境変数
| 変数名 | 説明 | 必須 |
|--------|------|------|
| MYVAULT_SERVICE_TOKEN | MyVaultアクセストークン | 推奨 |

### テストデータ
- config/capabilities/default_project/ にYAMLファイルが必要
- テスト用capabilityデータ（google_search.yaml, gmail_send.yaml等）

---

## 7. テスト項目

### TC-001: Capability一覧取得API
- **テスト観点**: プロジェクト単位でcapabilitiesを取得できる
- **関連する受入条件**: AC-1, AC-3
- **関連する設計方針**: DP-3
- **テスト種別**: E2E
- **テスト方法**: curl
- **前提条件**:
  1. mySwiftAgentCoreが起動している
  2. default_projectにcapabilitiesが登録されている
- **テスト手順**:
  1. GET /api/v1/capabilities?project=default_project を実行
  2. レスポンスを検証
- **期待結果**:
  - HTTPステータス: 200
  - レスポンス: capabilities配列を含むJSON
- **curlコマンド**:
  ```bash
  curl -s "http://localhost:8006/api/v1/capabilities?project=default_project" | jq .
  ```
- **pytestメソッド**: `test_tc_001_capability_list`

### TC-002: Capability詳細取得API
- **テスト観点**: 特定のcapability詳細を取得できる
- **関連する受入条件**: AC-3
- **関連する設計方針**: DP-3
- **テスト種別**: E2E
- **テスト方法**: curl
- **前提条件**:
  1. mySwiftAgentCoreが起動している
  2. google_search capabilityが登録されている
- **テスト手順**:
  1. GET /api/v1/capabilities/google_search?project=default_project を実行
  2. レスポンスを検証
- **期待結果**:
  - HTTPステータス: 200
  - レスポンス: capability詳細JSON
- **curlコマンド**:
  ```bash
  curl -s "http://localhost:8006/api/v1/capabilities/google_search?project=default_project" | jq .
  ```
- **pytestメソッド**: `test_tc_002_capability_detail`

### TC-003: _internal除外検証
- **テスト観点**: クライアント向けレスポンスから_internalが除外される
- **関連する受入条件**: AC-4
- **関連する設計方針**: DP-4
- **テスト種別**: E2E / セキュリティ
- **テスト方法**: curl + jq
- **前提条件**:
  1. mySwiftAgentCoreが起動している
  2. _internalセクションを持つcapabilityが存在
- **テスト手順**:
  1. GET /api/v1/capabilities/google_search?project=default_project を実行
  2. レスポンスに_internalが含まれないことを確認
- **期待結果**:
  - HTTPステータス: 200
  - レスポンス: _internal, endpoint, secret_keyが含まれない
- **curlコマンド**:
  ```bash
  curl -s "http://localhost:8006/api/v1/capabilities/google_search?project=default_project" | jq 'has("_internal")'
  # 期待結果: false
  ```
- **pytestメソッド**: `test_tc_003_internal_excluded`

### TC-004: Capability登録API
- **テスト観点**: 新しいcapabilityを登録できる
- **関連する受入条件**: AC-3
- **関連する設計方針**: DP-3
- **テスト種別**: E2E
- **テスト方法**: curl
- **前提条件**:
  1. mySwiftAgentCoreが起動している
  2. 管理者権限がある（該当する場合）
- **テスト手順**:
  1. POST /api/v1/capabilities を実行
  2. レスポンスを検証
  3. 登録されたcapabilityをGETで確認
- **期待結果**:
  - HTTPステータス: 201 (Created)
  - レスポンス: 登録されたcapability
- **curlコマンド**:
  ```bash
  curl -s -X POST "http://localhost:8006/api/v1/capabilities" \
    -H "Content-Type: application/json" \
    -d '{
      "project": "default_project",
      "capability": {
        "capability_id": "test_capability",
        "name": "Test Capability",
        "description": "テスト用capability",
        "inputs": {"param1": {"type": "string", "required": true}},
        "outputs": {"result": {"type": "string"}}
      }
    }' | jq .
  ```
- **pytestメソッド**: `test_tc_004_capability_register`

### TC-005: YAML形式レスポンス
- **テスト観点**: YAML形式でcapabilitiesを取得できる
- **関連する受入条件**: AC-5
- **関連する設計方針**: DP-3
- **テスト種別**: E2E
- **テスト方法**: curl
- **前提条件**:
  1. mySwiftAgentCoreが起動している
- **テスト手順**:
  1. Accept: application/yaml ヘッダー付きでGETを実行
  2. レスポンスがYAML形式であることを確認
- **期待結果**:
  - HTTPステータス: 200
  - Content-Type: application/yaml
  - レスポンス: 有効なYAML
- **curlコマンド**:
  ```bash
  curl -s "http://localhost:8006/api/v1/capabilities?project=default_project" \
    -H "Accept: application/yaml"
  ```
- **pytestメソッド**: `test_tc_005_yaml_response`

### TC-006: プロジェクト分離検証
- **テスト観点**: プロジェクト間でcapabilitiesが分離されている
- **関連する受入条件**: AC-1
- **関連する設計方針**: DP-1
- **テスト種別**: E2E
- **テスト方法**: curl
- **前提条件**:
  1. mySwiftAgentCoreが起動している
  2. 複数プロジェクトにcapabilitiesが登録されている
- **テスト手順**:
  1. project_aのcapabilitiesを取得
  2. project_bのcapabilitiesを取得
  3. 内容が異なることを確認
- **期待結果**:
  - 各プロジェクトで異なるcapabilities
  - 他プロジェクトのcapabilitiesが混入しない
- **pytestメソッド**: `test_tc_006_project_isolation`

### TC-007: CapabilityClient統合テスト
- **テスト観点**: TypeScript CapabilityClientが動作する
- **関連する受入条件**: AC-3
- **関連する設計方針**: DP-3
- **テスト種別**: 結合
- **テスト方法**: TypeScript単体テスト経由
- **前提条件**:
  1. mySwiftAgentCoreが起動している
- **テスト手順**:
  1. CapabilityClientをインスタンス化
  2. getCapabilities()を呼び出し
  3. 結果を検証
- **pytestメソッド**: `test_tc_007_capability_client`

### TC-008: expertAgentからの利用
- **テスト観点**: PythonからHTTP経由で利用できる
- **関連する受入条件**: AC-6
- **関連する設計方針**: -
- **テスト種別**: E2E / 結合
- **テスト方法**: Python pytest
- **前提条件**:
  1. mySwiftAgentCoreが起動している
  2. expertAgentのテスト環境が準備されている
- **テスト手順**:
  1. PythonでHTTPリクエストを送信
  2. レスポンスを検証
  3. job_analyzerプロンプト生成で使用
- **期待結果**:
  - 正常にcapabilitiesを取得
  - YAMLフォーマットでプロンプトに組み込み可能
- **pytestメソッド**: `test_tc_008_expert_agent_integration`

### TC-009: HealthCheck API
- **テスト観点**: capabilityManagementのヘルスチェック
- **関連する受入条件**: -
- **関連する設計方針**: -
- **テスト種別**: E2E
- **テスト方法**: curl
- **前提条件**:
  1. mySwiftAgentCoreが起動している
- **テスト手順**:
  1. GET /api/v1/capabilities/health を実行
  2. レスポンスを検証
- **期待結果**:
  - HTTPステータス: 200
  - status: healthy
- **curlコマンド**:
  ```bash
  curl -s "http://localhost:8006/api/v1/capabilities/health" | jq .
  ```
- **pytestメソッド**: `test_tc_009_health_check`

### TC-010: 既存YAML移行検証
- **テスト観点**: 既存YAMLファイルがdefault_projectに存在する
- **関連する受入条件**: AC-2
- **関連する設計方針**: -
- **テスト種別**: ファイル検証 + E2E
- **テスト方法**: ls + curl
- **前提条件**:
  1. config/capabilities/default_project/ が存在
- **テスト手順**:
  1. ディレクトリ構造を確認
  2. API経由で取得できることを確認
- **期待結果**:
  - google_search.yaml, gmail_send.yaml等が存在
  - index.yamlにcapabilityリストが定義
  - API経由で取得可能
- **curlコマンド**:
  ```bash
  ls -la mySwiftAgentCore/config/capabilities/default_project/
  ```
- **pytestメソッド**: `test_tc_010_yaml_migration`

---

## 8. テスト実行計画

### 実行順序
1. サービス起動確認（ヘルスチェック）- TC-009
2. 既存YAML移行検証 - TC-010
3. Capability一覧取得 - TC-001
4. Capability詳細取得 - TC-002
5. _internal除外検証 - TC-003
6. YAML形式レスポンス - TC-005
7. Capability登録 - TC-004
8. プロジェクト分離検証 - TC-006
9. CapabilityClient統合 - TC-007
10. expertAgent統合 - TC-008

### 成功基準
- [ ] すべてのpytestテストがパス
- [ ] すべての受入条件が検証済み
- [ ] デッドコードが検出されないこと
- [ ] セキュリティ検証（_internal除外）がパス

### 実行コマンド

```bash
# pytest受入テスト
uv run pytest mySwiftAgentCore/tests/acceptance/test_issue_365_acceptance.py -v -s

# curl手動テスト
./scripts/run-acceptance-tests.sh 365
```

---

## 9. 補足事項

### 🚨 重大な発見: モジュール未統合 (2026-01-16 更新)

**発見事項**:
`src/capabilityManagement/` モジュールは実装されテストも合格（132テスト）しているが、**メインAPIルーターに統合されていない**。

**証拠**: `src/api/routes.ts:142-149` で `/api/v1/capabilities` がスタブのまま

```typescript
// 現状: Capabilities routes (stub)
app.get('/api/v1/capabilities', (c) => {
  return c.json({
    service: 'Capability Management',
    status: 'stub',
    message: 'Capability Management API is not yet implemented',
  });
});
```

**影響**:
- TC-001〜TC-006: 現状はすべて失敗（スタブ応答）
- デッドコード: `createCapabilityRoutes`関数が未使用

**推奨する修正作業**:
```typescript
// src/api/routes.ts に追加すべきコード
import { createCapabilityRoutes } from '../capabilityManagement/api/index.js';
import { CapabilityRegistry, CapabilitySanitizer, YamlLoader } from '../capabilityManagement/index.js';

// createApiRoutes関数内で、スタブを置き換え
const registry = new CapabilityRegistry();
const sanitizer = new CapabilitySanitizer();
const loader = new YamlLoader('./config/capabilities');
// YAMLファイルを読み込んでレジストリに登録
const capabilityRoutes = createCapabilityRoutes({ registry, sanitizer });
app.route('/', capabilityRoutes);
```

### その他の補足

- design-policy.mdが存在しないため、Issue本文の設計を基に計画を作成
- expertAgent統合テスト（AC-6）はmySwiftAgentCore側の統合完了後にテスト可能
- config/capabilities/default_project/ に3ファイル存在確認済み:
  - index.yaml
  - google_search.yaml
  - weather_api.yaml

### 受入テスト実行前の必須作業

1. **統合作業**: `createCapabilityRoutes`を`src/api/routes.ts`に統合
2. **YAMLファイル読み込み**: 起動時にYAMLをCapabilityRegistryに登録
3. **サービス再起動**: 変更を反映

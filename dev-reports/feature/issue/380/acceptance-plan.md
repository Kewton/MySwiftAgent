# 受入テスト計画書

**Issue**: #380
**作成日**: 2024-01-20
**作成者**: acceptance-plan-agent
**フェーズ**: PRE-TDD（TDD実装前計画）

---

## 1. 概要

### 対象Issue
- **番号**: #380
- **タイトル**: feat(taskflowGenerator): Capability出力スキーマの正確な定義とカタログ整備
- **プロジェクト**: mySwiftAgentCore (TypeScript)

### 参照ドキュメント
- Issue: #380
- 設計方針書: `dev-reports/feature/issue/380/design-policy.md`
- 作業計画書: `dev-reports/feature/issue/380/work-plan.md`

### 背景
TaskFlowGeneratorAgentは、Capabilityの入出力スキーマを理解してワークフローを生成するが、`responseSchema`が不完全または未定義のCapabilityがあり、AIがフィールド名を誤るケースが発生していた。

---

## 2. 単体テスト結果レビュー

### PRE-TDD フェーズ

本計画書はTDD実装前に作成されています。単体テスト結果は、TDD実装完了後に以下の形式でレビューされます：

| 指標 | 期待値 | 実測値 |
|------|--------|--------|
| カバレッジ | 90%以上 | TDD実装後に記入 |
| 総テスト数 | - | TDD実装後に記入 |
| 静的解析エラー | 0件 | TDD実装後に記入 |

### TDD実装後の確認項目

- [ ] `tests/unit/capabilities/catalog/CapabilityCatalogGenerator.test.ts` が作成されている
- [ ] `tests/unit/capabilities/catalog/SchemaValidator.test.ts` が作成されている
- [ ] `tests/unit/taskflowGeneratorAgent/validator/validators/ResponseSchemaValidator.test.ts` が作成されている
- [ ] 単体テストカバレッジが90%以上

---

## 3. 受入条件分析

### AC-1: 全CapabilityにresponseSchemaを追加

- **原文**: 全Capabilityに`output_schema`を追加（設計方針で`responseSchema`に統一）
- **分類**: 機能要件
- **テスト方法**: CLI実行 + カタログ検証
- **モック使用**: 不可
- **検証ポイント**:
  1. `config/capabilities/default_project/` 配下の全YAMLファイルに`responseSchema`が定義されている
  2. 生成されたカタログで全Capabilityに`responseSchema`が含まれている
  3. `responseSchema`がJSON Schema Draft-07形式に準拠している

### AC-2: 出力フィールド名を正確に定義

- **原文**: 出力フィールド名を正確に定義
- **分類**: 機能要件
- **テスト方法**: API実行 + スキーマ検証
- **モック使用**: 不可（実サービスでの検証必須）
- **検証ポイント**:
  1. `google_search`の出力に`search_results`フィールドが存在する
  2. `direct_llm`の出力に`result`フィールドが存在する
  3. `gmail_send`の出力に`result`, `message_id`フィールドが存在する
  4. 定義されたフィールド名と実際のAPI応答が一致する

### AC-3: Capabilityカタログを生成するスクリプトを作成

- **原文**: Capabilityカタログを生成するスクリプトを作成
- **分類**: 機能要件
- **テスト方法**: npm コマンド実行
- **モック使用**: 不可
- **検証ポイント**:
  1. `npm run generate:catalog` コマンドが存在する
  2. コマンド実行が正常終了する（exit code 0）
  3. カタログファイルが生成される

### AC-4: カタログをJSON/YAML形式でエクスポート可能にする

- **原文**: カタログをJSON/YAML形式でエクスポート可能にする
- **分類**: 機能要件
- **テスト方法**: ファイル検証 + 形式検証
- **モック使用**: 不可
- **検証ポイント**:
  1. `config/capabilities/catalog/capabilities-catalog.json` が生成される
  2. `config/capabilities/catalog/capabilities-catalog.yaml` が生成される
  3. `config/capabilities/catalog/capabilities-catalog.md` が生成される（Markdown形式）
  4. JSON形式が妥当（パース可能）
  5. YAML形式が妥当（パース可能）

### AC-5: AIプロンプトに注入できる形式で出力

- **原文**: AIプロンプトに注入できる形式で出力
- **分類**: 機能要件
- **テスト方法**: PromptBuilder統合検証
- **モック使用**: 不可
- **検証ポイント**:
  1. カタログのJSON形式がPromptBuilderで読み込み可能
  2. `formatCapabilitiesEnhanced()` で`responseSchema`が含まれる
  3. 生成されたプロンプトに各Capabilityの出力スキーマが含まれる

---

## 4. 設計方針検証

### DP-1: 用語統一（responseSchema）

- **設計方針**: 出力スキーマは`responseSchema`で統一（`output_schema`は不採用）
- **検証方法**: Grep検索 + コード確認
- **テスト項目**:
  1. 新規実装で`output_schema`が使用されていないこと
  2. YAMLファイルで`responseSchema`キーが使用されていること
  3. TypeScript型定義で`responseSchema`プロパティが定義されていること

```bash
# 検証コマンド
grep -rn "output_schema" mySwiftAgentCore/src/ --include="*.ts" | wc -l
# Expected: 0（新規コード内で使用されていない）

grep -rn "responseSchema" mySwiftAgentCore/config/capabilities/default_project/*.yaml | wc -l
# Expected: Capability数と同等
```

### DP-2: JSON Schema Draft-07準拠

- **設計方針**: JSON Schema Draft-07に準拠、ajvライブラリ使用
- **検証方法**: ajvバリデーション実行
- **テスト項目**:
  1. ajvパッケージがインストールされている
  2. ResponseSchemaValidatorがajvを使用している
  3. 生成されたスキーマがJSON Schema Draft-07に準拠

```bash
# 検証コマンド
cat mySwiftAgentCore/package.json | jq '.dependencies.ajv // .devDependencies.ajv'
# Expected: バージョン番号が出力される
```

### DP-3: ディレクトリ構造

- **設計方針**: `src/capabilities/catalog/` 配下にGenerator、Validator等を配置
- **検証方法**: ファイル存在確認
- **テスト項目**:
  1. `src/capabilities/catalog/CapabilityCatalogGenerator.ts` が存在
  2. `src/capabilities/catalog/SchemaValidator.ts` が存在
  3. `src/capabilities/types/catalog.ts` が存在

```bash
# 検証コマンド
ls -la mySwiftAgentCore/src/capabilities/catalog/
ls -la mySwiftAgentCore/src/capabilities/types/
```

### DP-4: カタログ生成アーキテクチャ

- **設計方針**: `config/capabilities/catalog/` に生成物を出力
- **検証方法**: カタログ生成実行後のディレクトリ確認
- **テスト項目**:
  1. カタログディレクトリが自動作成される
  2. 3形式（JSON/YAML/Markdown）のファイルが生成される
  3. 生成物にバージョンとタイムスタンプが含まれる

---

## 5. デッドコード検証計画

### F-1: CapabilityCatalogGenerator

- **ファイル**: `src/capabilities/catalog/CapabilityCatalogGenerator.ts`
- **種別**: class
- **期待される呼び出し元**: `scripts/generate-catalog.ts`、API endpoint（将来）
- **検証方法**:
  ```bash
  grep -rn "CapabilityCatalogGenerator" mySwiftAgentCore/src/ mySwiftAgentCore/scripts/ --include="*.ts" | grep -v "import\|export\|class "
  ```
- **E2Eでの確認方法**: `npm run generate:catalog` 実行でカタログが生成されること

### F-2: ResponseSchemaValidator

- **ファイル**: `src/taskflowGeneratorAgent/validator/validators/ResponseSchemaValidator.ts`
- **種別**: class
- **期待される呼び出し元**: ValidationPipeline、CapabilityCatalogGenerator
- **検証方法**:
  ```bash
  grep -rn "ResponseSchemaValidator" mySwiftAgentCore/src/ --include="*.ts" | grep -v "import\|export\|class "
  ```
- **E2Eでの確認方法**: カタログ生成時にスキーマバリデーションが実行されること

### F-3: SchemaValidator

- **ファイル**: `src/capabilities/catalog/SchemaValidator.ts`
- **種別**: class/function
- **期待される呼び出し元**: CapabilityCatalogGenerator
- **検証方法**:
  ```bash
  grep -rn "SchemaValidator" mySwiftAgentCore/src/ --include="*.ts" | grep -v "import\|export\|class "
  ```
- **E2Eでの確認方法**: 不正なスキーマでエラーが発生すること

### F-4: カタログ型定義

- **ファイル**: `src/capabilities/types/catalog.ts`
- **種別**: type/interface
- **期待される呼び出し元**: CapabilityCatalogGenerator、PromptBuilder
- **検証方法**:
  ```bash
  grep -rn "CapabilityCatalog\|CatalogOptions" mySwiftAgentCore/src/ --include="*.ts" | grep -v "import\|type "
  ```
- **E2Eでの確認方法**: 型を使用したコードがコンパイルエラーなく動作すること

### F-5: CLIスクリプト

- **ファイル**: `scripts/generate-catalog.ts`
- **種別**: script
- **期待される呼び出し元**: `npm run generate:catalog`
- **検証方法**:
  ```bash
  cat mySwiftAgentCore/package.json | jq '.scripts["generate:catalog"]'
  ```
- **E2Eでの確認方法**: npmコマンドで実行可能であること

---

## 6. テスト環境

### 必須サービス

| サービス | URL | ヘルスチェック | 必須度 |
|---------|-----|--------------|--------|
| mySwiftAgentCore | http://localhost:8006 | GET /health | 必須（API検証） |
| expertAgent | http://localhost:8004 | GET /health | 必須（Capability実行） |
| myVault | http://localhost:8003 | GET /health | 必須（シークレット取得） |

### 起動コマンド（E2Eテスト用 - 必須）

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

**E2Eテストで使用するシークレットは、コンテナ起動のmyVaultのdefault_projectから取得します。**

| 項目 | 取得元 |
|------|--------|
| SERPER_API_KEY | myVault (default_project) |
| OPENAI_API_KEY | myVault (default_project) |

myVaultへのシークレット登録（事前設定が必要な場合）:
```bash
curl -X POST http://localhost:8003/api/v1/secrets \
  -H "Content-Type: application/json" \
  -d '{"project": "default_project", "key": "SERPER_API_KEY", "value": "xxx"}'
```

### 環境変数

| 変数名 | 説明 | 必須 |
|--------|------|------|
| NODE_ENV | 実行環境 | development |

### ビルド・準備コマンド

```bash
cd mySwiftAgentCore
npm install
npm run build
```

---

## 7. テスト項目

### TC-001: カタログ生成コマンド実行

- **テスト観点**: CLIコマンドが正常に動作し、カタログが生成されること
- **関連する受入条件**: AC-3
- **関連する設計方針**: DP-4
- **テスト種別**: E2E
- **テスト方法**: npm コマンド実行
- **前提条件**:
  1. mySwiftAgentCoreのビルドが完了している
  2. 依存パッケージがインストールされている
- **テスト手順**:
  1. `npm run generate:catalog` を実行
  2. exit code を確認
  3. 生成されたファイルを確認
- **期待結果**:
  - exit code: 0
  - `config/capabilities/catalog/` ディレクトリが存在
  - 3つのファイル（JSON/YAML/MD）が生成される
- **コマンド**:
  ```bash
  cd mySwiftAgentCore
  npm run generate:catalog
  echo "Exit code: $?"
  ls -la config/capabilities/catalog/
  ```
- **pytestメソッド**: `test_tc_001_catalog_generation_command`

### TC-002: JSON形式カタログの妥当性検証

- **テスト観点**: 生成されたJSONカタログが正しい形式であること
- **関連する受入条件**: AC-4, AC-1
- **関連する設計方針**: DP-2
- **テスト種別**: E2E
- **テスト方法**: jq/node による検証
- **前提条件**:
  1. TC-001が完了している
- **テスト手順**:
  1. JSONファイルをパース
  2. Capability数を確認
  3. 各CapabilityにresponseSchemaが含まれるか確認
- **期待結果**:
  - JSONパースが成功
  - Capability数 >= 4（google_search, direct_llm, gmail_send, json_output_agent）
  - すべてのCapabilityにresponseSchemaが定義されている
- **コマンド**:
  ```bash
  # JSON形式の検証
  cat mySwiftAgentCore/config/capabilities/catalog/capabilities-catalog.json | jq '.'

  # Capability数確認
  cat mySwiftAgentCore/config/capabilities/catalog/capabilities-catalog.json | jq '.capabilities | length'

  # responseSchema定義済み確認
  cat mySwiftAgentCore/config/capabilities/catalog/capabilities-catalog.json | \
    jq '[.capabilities[] | select(.responseSchema != null)] | length'
  ```
- **pytestメソッド**: `test_tc_002_json_catalog_validity`

### TC-003: YAML形式カタログの妥当性検証

- **テスト観点**: 生成されたYAMLカタログが正しい形式であること
- **関連する受入条件**: AC-4
- **関連する設計方針**: -
- **テスト種別**: E2E
- **テスト方法**: yq/python による検証
- **前提条件**:
  1. TC-001が完了している
- **テスト手順**:
  1. YAMLファイルをパース
  2. 構造を確認
- **期待結果**:
  - YAMLパースが成功
  - JSONカタログと同等の内容
- **コマンド**:
  ```bash
  # YAML形式の検証（yqがインストールされている場合）
  yq '.' mySwiftAgentCore/config/capabilities/catalog/capabilities-catalog.yaml

  # または Python で検証
  python3 -c "
import yaml
with open('mySwiftAgentCore/config/capabilities/catalog/capabilities-catalog.yaml') as f:
    data = yaml.safe_load(f)
    print(f'Capabilities count: {len(data.get(\"capabilities\", []))}')
  "
  ```
- **pytestメソッド**: `test_tc_003_yaml_catalog_validity`

### TC-004: ResponseSchemaValidator動作確認

- **テスト観点**: ResponseSchemaValidatorがajvを使用してスキーマ検証を行うこと
- **関連する受入条件**: AC-1, AC-2
- **関連する設計方針**: DP-2
- **テスト種別**: 結合
- **テスト方法**: テストスクリプト実行
- **前提条件**:
  1. ResponseSchemaValidatorが実装されている
  2. ajvがインストールされている
- **テスト手順**:
  1. テスト用スクリプトを実行
  2. 正常なデータでバリデーション成功を確認
  3. 異常なデータでバリデーション失敗を確認
- **期待結果**:
  - 正常データ: valid = true
  - 異常データ: valid = false, errors配列にエラー詳細
- **コマンド**:
  ```bash
  # テストスクリプトが存在する場合
  cd mySwiftAgentCore
  npx ts-node scripts/test-schema-validator.ts

  # または npm test で単体テストを実行
  npm test -- --grep "ResponseSchemaValidator"
  ```
- **pytestメソッド**: `test_tc_004_response_schema_validator`

### TC-005: google_search Capabilityの出力スキーマ検証

- **テスト観点**: google_searchの実際の出力がresponseSchemaと一致すること
- **関連する受入条件**: AC-2
- **関連する設計方針**: DP-1
- **テスト種別**: E2E
- **テスト方法**: API実行 + スキーマ検証
- **前提条件**:
  1. mySwiftAgentCore、expertAgentが起動している
  2. SERPER_API_KEYがmyVaultに登録されている
- **テスト手順**:
  1. google_search APIを呼び出す
  2. 応答に`search_results`フィールドが存在することを確認
  3. 応答に`search_results_count`フィールドが存在することを確認
- **期待結果**:
  - HTTPステータス: 200
  - 応答に`search_results`配列が含まれる
  - 各結果に`title`, `link`, `knowledge`フィールドが含まれる
- **curlコマンド**:
  ```bash
  curl -s -X POST http://localhost:8004/v1/utility/google_search \
    -H "Content-Type: application/json" \
    -d '{"queries": ["TypeScript testing"], "num": 1}' | jq '{
      has_search_results: (.search_results != null),
      search_results_count: .search_results_count,
      first_result_keys: (.search_results[0] | keys)
    }'
  ```
- **pytestメソッド**: `test_tc_005_google_search_schema_validation`

### TC-006: direct_llm Capabilityの出力スキーマ検証

- **テスト観点**: direct_llmの実際の出力がresponseSchemaと一致すること
- **関連する受入条件**: AC-2
- **関連する設計方針**: DP-1
- **テスト種別**: E2E
- **テスト方法**: API実行 + スキーマ検証
- **前提条件**:
  1. mySwiftAgentCore、expertAgentが起動している
  2. OPENAI_API_KEYがmyVaultに登録されている
- **テスト手順**:
  1. direct_llm APIを呼び出す
  2. 応答に`result`フィールドが存在することを確認
- **期待結果**:
  - HTTPステータス: 200
  - 応答に`result`文字列が含まれる
- **curlコマンド**:
  ```bash
  curl -s -X POST http://localhost:8004/v1/mylllm \
    -H "Content-Type: application/json" \
    -d '{"user_input": "Hello", "model": "gpt-4o-mini"}' | jq '{
      has_result: (.result != null),
      result_type: (if .result then type else "null" end)
    }'
  ```
- **pytestメソッド**: `test_tc_006_direct_llm_schema_validation`

### TC-007: AIプロンプト注入形式の検証

- **テスト観点**: カタログがPromptBuilderで正しく読み込まれ、プロンプトに注入されること
- **関連する受入条件**: AC-5
- **関連する設計方針**: DP-1, DP-3
- **テスト種別**: 結合
- **テスト方法**: テストスクリプト/単体テスト
- **前提条件**:
  1. CapabilityCatalogGeneratorが実装されている
  2. PromptBuilderが更新されている
- **テスト手順**:
  1. CapabilityCatalogGeneratorでカタログを生成
  2. カタログからCapability情報を取得
  3. PromptBuilder.formatCapabilitiesEnhanced()を呼び出す
  4. 出力にresponseSchemaが含まれることを確認
- **期待結果**:
  - プロンプト出力に`Response Schema`セクションが含まれる
  - 各CapabilityのresponseSchemaがJSON形式で出力される
- **pytestメソッド**: `test_tc_007_prompt_injection_format`

### TC-008: カタログバージョンとタイムスタンプ

- **テスト観点**: 生成されたカタログにメタデータが含まれること
- **関連する受入条件**: AC-4
- **関連する設計方針**: DP-4
- **テスト種別**: E2E
- **テスト方法**: JSONファイル検証
- **前提条件**:
  1. TC-001が完了している
- **テスト手順**:
  1. カタログJSONを読み込む
  2. versionフィールドを確認
  3. generatedフィールドを確認
- **期待結果**:
  - `version`フィールドが存在（例: "1.0.0"）
  - `generated`フィールドがISO 8601形式のタイムスタンプ
- **コマンド**:
  ```bash
  cat mySwiftAgentCore/config/capabilities/catalog/capabilities-catalog.json | jq '{
    version: .version,
    generated: .generated
  }'
  ```
- **pytestメソッド**: `test_tc_008_catalog_metadata`

### TC-009: Markdown形式カタログの可読性

- **テスト観点**: 生成されたMarkdownが人間可読であること
- **関連する受入条件**: AC-4
- **関連する設計方針**: -
- **テスト種別**: E2E
- **テスト方法**: ファイル内容確認
- **前提条件**:
  1. TC-001が完了している
- **テスト手順**:
  1. Markdownファイルを読み込む
  2. 主要セクションが含まれることを確認
- **期待結果**:
  - タイトルヘッダーが存在
  - 各Capabilityがセクションとして記載
  - 入力/出力スキーマが記載
- **コマンド**:
  ```bash
  # Markdownの構造確認
  grep -E "^#" mySwiftAgentCore/config/capabilities/catalog/capabilities-catalog.md | head -20

  # google_searchセクションの確認
  grep -A 20 "google_search" mySwiftAgentCore/config/capabilities/catalog/capabilities-catalog.md
  ```
- **pytestメソッド**: `test_tc_009_markdown_catalog_readability`

### TC-010: 不正スキーマ検出テスト

- **テスト観点**: ResponseSchemaValidatorが不正なスキーマを検出できること
- **関連する受入条件**: AC-1
- **関連する設計方針**: DP-2
- **テスト種別**: 結合
- **テスト方法**: テストケース実行
- **前提条件**:
  1. ResponseSchemaValidatorが実装されている
- **テスト手順**:
  1. 不正な型のデータでバリデーション実行
  2. 必須フィールド欠落でバリデーション実行
  3. エラーメッセージを確認
- **期待結果**:
  - バリデーション失敗
  - 適切なエラーメッセージが返される
- **pytestメソッド**: `test_tc_010_invalid_schema_detection`

---

## 8. コンポーネント間整合性検証

### CI-1: 用語統一の一貫性

- **検証対象**: responseSchema vs output_schema の使用
- **検証方法**:
  ```bash
  # 新規コードでoutput_schemaが使用されていないか確認
  grep -rn "output_schema" mySwiftAgentCore/src/capabilities/ --include="*.ts"

  # responseSchemaが一貫して使用されているか確認
  grep -rn "responseSchema" mySwiftAgentCore/config/capabilities/default_project/*.yaml | wc -l
  ```
- **確認項目**:
  - [ ] 新規実装コードで`output_schema`が使用されていない
  - [ ] YAML定義で`responseSchema`キーが統一されている
  - [ ] TypeScript型定義で`responseSchema`プロパティ名が統一されている

### CI-2: ajvバージョン互換性

- **検証対象**: ajvパッケージの設定
- **検証方法**:
  ```bash
  cat mySwiftAgentCore/package.json | jq '.dependencies.ajv'
  ```
- **確認項目**:
  - [ ] ajvが依存関係に含まれている
  - [ ] ajv-formatsも必要に応じて含まれている

---

## 9. E2E統合テスト計画

### E2E-1: カタログ生成からプロンプト注入までの一連フロー

- **テストファイル**: `tests/acceptance/test_issue_380_acceptance.py`
- **実行コマンド**:
  ```bash
  cd mySwiftAgentCore
  # ビルドとカタログ生成
  npm run build
  npm run generate:catalog

  # 受入テスト実行
  cd ..
  uv run pytest tests/acceptance/test_issue_380_acceptance.py -v -s
  ```
- **検証項目**:
  - [ ] カタログ生成が成功する
  - [ ] 生成されたカタログが正しい形式である
  - [ ] カタログのCapability情報がPromptBuilderで利用可能

### E2E-2: TaskFlowGeneratorAgentとの統合確認

- **目的**: 生成されたカタログがTaskFlowGeneratorAgentで使用されること
- **検証項目**:
  - [ ] TaskFlowGeneratorがカタログからCapability情報を取得できる
  - [ ] 生成されるワークフローで正しいフィールド名が使用される

---

## 10. テスト実行計画

### 実行順序

1. **ビルド・準備**（5分）
   - npm install
   - npm run build

2. **カタログ生成テスト**（10分）
   - TC-001: カタログ生成コマンド
   - TC-002: JSON検証
   - TC-003: YAML検証
   - TC-008: メタデータ検証
   - TC-009: Markdown検証

3. **バリデータテスト**（10分）
   - TC-004: ResponseSchemaValidator
   - TC-010: 不正スキーマ検出

4. **API統合テスト**（15分）
   - サービス起動
   - TC-005: google_search検証
   - TC-006: direct_llm検証
   - TC-007: プロンプト注入検証

5. **整合性検証**（5分）
   - CI-1: 用語統一
   - CI-2: ajv互換性

### 成功基準

- [ ] すべてのTC-xxxテストがパス
- [ ] すべてのCI-xxx検証がパス
- [ ] すべての受入条件（AC-1からAC-5）が検証済み
- [ ] デッドコードが検出されないこと（F-1からF-5の機能が使用されている）
- [ ] カタログ生成が再現可能（複数回実行で同一結果）

---

## 11. 補足事項

### TDD実装後の更新

本計画書はPRE-TDDフェーズで作成されています。TDD実装完了後、以下のセクションを更新してください：

1. Section 2「単体テスト結果レビュー」にカバレッジ情報を追加
2. 必要に応じてテスト項目を追加・修正
3. 実装で判明した新たなテスト観点を追加

### 既存のresponseSchema状況

現在確認できているCapabilityのresponseSchema定義状況：

| Capability | responseSchema定義 |
|-----------|-------------------|
| google_search | あり（search_results, search_results_count, status） |
| direct_llm | あり（result） |
| gmail_send | あり（result, message_id） |
| json_output_agent | あり（result） |

### 参考コマンド集

```bash
# サービス起動
./scripts/dev-hybrid.sh start --local-only

# サービス停止
./scripts/dev-hybrid.sh stop --local-only

# ヘルスチェック
curl -s http://localhost:8006/health
curl -s http://localhost:8004/health
curl -s http://localhost:8003/health

# カタログ生成
cd mySwiftAgentCore && npm run generate:catalog

# 単体テスト実行
cd mySwiftAgentCore && npm test

# 受入テスト実行
uv run pytest tests/acceptance/test_issue_380_acceptance.py -v -s
```

---

**作成完了**: 2024-01-20
**次のステップ**: TDD実装 -> 受入テスト実装・実行 -> 本計画書の更新

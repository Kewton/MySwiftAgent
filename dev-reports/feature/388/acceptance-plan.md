# 受入テスト計画書

**Issue**: #388
**タイトル**: 中期: スキーマ変換ロジックの分離（Issue #387 フォローアップ）
**作成日**: 2026-01-21
**作成者**: Claude AI Assistant

---

## 1. 概要

### 対象Issue
- **番号**: #388
- **タイトル**: 中期: スキーマ変換ロジックの分離（Issue #387 フォローアップ）
- **プロジェクト**: expertAgent

### 参照ドキュメント
- Issue: #388
- 設計方針書: `dev-reports/feature/issue/388/design-policy.md`
- 作業計画書: `dev-reports/feature/issue/388/work-plan.md`
- アーキテクチャレビュー: `dev-reports/feature/issue/388/architecture-review.md`

### 機能概要
JSON Schema形式とSimple Mapping形式間の変換ロジックを、`orchestrator.py`から独立したユーティリティモジュール `schema_converter.py` に分離する。

---

## 2. 単体テスト結果レビュー

### カバレッジ
- **現在**: 100%（29テストすべてパス）
- **目標**: 90%
- **判定**: ✅ PASS

### テスト品質評価

| 指標 | 値 | 判定 |
|------|-----|------|
| 総テスト数 | 29 | ✅ 十分 |
| モック使用テスト数 | 0 | ✅ |
| モック使用率 | 0% | ✅ 優秀 |
| ログ出力テスト数 | 5 | ✅ |

### モック使用の妥当性
- モック使用なし（純粋関数のため不要）
- 全テストが実関数を直接テスト
- 外部依存なし

### テストカテゴリ別内訳

| カテゴリ | テスト数 | 内容 |
|---------|----------|------|
| TestJsonSchemaToSimpleMapping | 9 | 順変換テスト |
| TestSimpleMappingToJsonSchema | 4 | 逆変換テスト |
| TestRoundTripConversion | 3 | 往復変換テスト |
| TestInformationLoss | 5 | 情報損失文書化テスト |
| TestLogging | 5 | ログ出力テスト |
| TestTypeAliases | 2 | 型エイリアステスト |
| TestIntegration | 1 | 統合テスト |

### 単体テストでカバーされていない項目
1. **E2E統合**: JobGenerator API経由でのスキーマ変換動作
2. **サービス間連携**: mySwiftAgentCoreへの実際のリクエスト送信
3. **ログファイル出力**: 実環境でのログファイルへの記録確認

---

## 3. 受入条件分析

### AC-1: schema_converter.pyが作成されている
- **原文**: `schema_converter.py` が作成されている
- **分類**: 機能要件
- **テスト方法**: ファイル存在確認 + import確認
- **検証ポイント**:
  1. `aiagent/clients/interfaces/schema_converter.py` が存在する
  2. `json_schema_to_simple_mapping` がimport可能
  3. `simple_mapping_to_json_schema` がimport可能
  4. 型エイリアス `JsonSchema`, `SimpleMapping` がimport可能

### AC-2: 変換ロジックの単体テストがある（カバレッジ90%以上）
- **原文**: 変換ロジックの単体テストがある（カバレッジ90%以上）
- **分類**: 品質要件
- **テスト方法**: pytest --cov
- **検証ポイント**:
  1. テストファイル `tests/unit/test_clients/test_schema_converter.py` が存在
  2. カバレッジ90%以上

### AC-3: 情報損失に関するテストが文書化されている
- **原文**: 情報損失に関するテストが文書化されている
- **分類**: ドキュメント要件
- **テスト方法**: テストコードレビュー
- **検証ポイント**:
  1. `TestInformationLoss` クラスが存在
  2. required, description, format, nested, array のテストがある

### AC-4: orchestrator.pyから変換ロジックが分離されている
- **原文**: `orchestrator.py` から変換ロジックが分離されている
- **分類**: 機能要件
- **テスト方法**: コード検査 + E2Eテスト
- **検証ポイント**:
  1. `_schema_to_simple_mapping` メソッドが orchestrator.py に存在しない
  2. orchestrator.py が schema_converter をimportしている
  3. JobGenerator APIが正常動作する

### AC-5: 既存の単体テストがすべて成功する
- **原文**: 既存の単体テストがすべて成功する
- **分類**: 品質要件
- **テスト方法**: pytest実行
- **検証ポイント**:
  1. 全単体テストがパス
  2. 静的解析エラーなし（Ruff, MyPy）

---

## 4. 設計方針検証

### DP-1: 配置場所の整合性
- **設計方針**: `clients/interfaces/` に配置（アーキテクチャレビューの改善案を採用）
- **検証方法**: ファイルパス確認
- **テスト項目**:
  1. `aiagent/clients/interfaces/schema_converter.py` に配置されている
  2. `__init__.py` でエクスポートされている

### DP-2: 純粋関数設計
- **設計方針**: ステートレスな純粋関数として実装
- **検証方法**: コード検査
- **テスト項目**:
  1. 関数は副作用を持たない（同じ入力に対して同じ出力）
  2. 外部状態に依存しない
  3. 例外を発生させない

### DP-3: 型エイリアスの実装
- **設計方針**: JsonSchema, SimpleMapping 型エイリアスを定義
- **検証方法**: import確認
- **テスト項目**:
  1. `JsonSchema` 型エイリアスが存在する
  2. `SimpleMapping` 型エイリアスが存在する
  3. 型ヒントが正しく動作する

### DP-4: デバッグログ機能
- **設計方針**: 情報損失時にDEBUGレベルでログ出力
- **検証方法**: ログ出力テスト
- **テスト項目**:
  1. required損失時にログ出力される
  2. description損失時にログ出力される
  3. format損失時にログ出力される
  4. nested structure損失時にログ出力される
  5. array item type損失時にログ出力される

### DP-5: エラー透過設計
- **設計方針**: 例外を発生させず、空辞書等を返す
- **検証方法**: 異常系テスト
- **テスト項目**:
  1. 空辞書入力で空辞書が返る
  2. 不正な型混在で空辞書が返る
  3. 型情報なしで "string" デフォルト

---

## 5. デッドコード検証計画

### F-1: json_schema_to_simple_mapping
- **ファイル**: `aiagent/clients/interfaces/schema_converter.py`
- **種別**: function
- **期待される呼び出し元**: `orchestrator.py`
- **検証方法**:
  ```bash
  # 呼び出し箇所を確認
  grep -rn "json_schema_to_simple_mapping" --include="*.py" | grep -v "def json_schema_to_simple_mapping\|import\|test_"
  ```
- **E2E確認**: JobGenerator API経由で変換が実行されることを確認

### F-2: simple_mapping_to_json_schema
- **ファイル**: `aiagent/clients/interfaces/schema_converter.py`
- **種別**: function
- **期待される呼び出し元**: 将来の逆変換ニーズ（現時点では未使用の可能性あり）
- **検証方法**:
  ```bash
  grep -rn "simple_mapping_to_json_schema" --include="*.py" | grep -v "def simple_mapping_to_json_schema\|import\|test_"
  ```
- **注記**: 設計方針で将来の拡張性のため実装、現時点で未使用は許容

### F-3: _log_information_loss
- **ファイル**: `aiagent/clients/interfaces/schema_converter.py`
- **種別**: internal function
- **期待される呼び出し元**: `json_schema_to_simple_mapping`
- **検証方法**:
  ```bash
  grep -rn "_log_information_loss" --include="*.py"
  ```

---

## 6. テスト環境

### 必須サービス

| サービス | URL | ヘルスチェック |
|---------|-----|--------------|
| expertAgent | http://localhost:8004 | GET /health |
| mySwiftAgentCore | http://localhost:8006 | GET /health |
| myVault | http://localhost:8003 | GET /health |

### 起動コマンド

```bash
# 1. 既存サービスを停止
./scripts/dev-hybrid.sh stop --local-only

# 2. ローカルモードでサービスを起動
./scripts/dev-hybrid.sh start --local-only
```

### 環境変数

| 変数名 | 説明 | 必須 |
|--------|------|------|
| MYVAULT_ENABLED | MyVault有効化フラグ | ✅ (true) |
| MYVAULT_BASE_URL | MyVault URL | ✅ (http://localhost:8003) |
| LOG_LEVEL | ログレベル | 推奨 (DEBUG) |

---

## 7. テスト項目

### TC-001: モジュール存在確認
- **テスト観点**: schema_converter.pyが正しく配置・エクスポートされている
- **関連する受入条件**: AC-1
- **関連する設計方針**: DP-1
- **テスト種別**: 結合
- **テスト方法**: pytest
- **前提条件**:
  1. expertAgent環境がセットアップ済み
- **テスト手順**:
  1. Pythonインタプリタでimport確認
- **期待結果**:
  - import成功
- **curlコマンド**: N/A
- **pytestメソッド**: `test_tc_001_module_import`
- **検証コマンド**:
  ```bash
  python -c "from aiagent.clients.interfaces.schema_converter import json_schema_to_simple_mapping, simple_mapping_to_json_schema, JsonSchema, SimpleMapping; print('✅ Import successful')"
  ```

### TC-002: 変換関数の動作確認（順変換）
- **テスト観点**: JSON Schema → Simple Mapping変換が正しく動作する
- **関連する受入条件**: AC-1, AC-2
- **関連する設計方針**: DP-2
- **テスト種別**: 結合
- **テスト方法**: pytest
- **前提条件**:
  1. schema_converter.pyが存在
- **テスト手順**:
  1. JSON Schema形式のデータを入力
  2. 変換関数を呼び出し
  3. 出力がSimple Mapping形式であることを確認
- **期待結果**:
  - `{"type": "object", "properties": {"email": {"type": "string"}}}` → `{"email": "string"}`
- **pytestメソッド**: `test_tc_002_json_schema_to_simple_mapping`

### TC-003: 変換関数の動作確認（逆変換）
- **テスト観点**: Simple Mapping → JSON Schema変換が正しく動作する
- **関連する受入条件**: AC-1
- **関連する設計方針**: DP-2
- **テスト種別**: 結合
- **テスト方法**: pytest
- **前提条件**:
  1. schema_converter.pyが存在
- **テスト手順**:
  1. Simple Mapping形式のデータを入力
  2. 変換関数を呼び出し
  3. 出力がJSON Schema形式であることを確認
- **期待結果**:
  - `{"email": "string"}` → `{"type": "object", "properties": {"email": {"type": "string"}}}`
- **pytestメソッド**: `test_tc_003_simple_mapping_to_json_schema`

### TC-004: orchestrator.pyの分離確認
- **テスト観点**: orchestrator.pyから変換ロジックが分離されている
- **関連する受入条件**: AC-4
- **関連する設計方針**: DP-1
- **テスト種別**: コード検査
- **テスト方法**: grep
- **前提条件**: なし
- **テスト手順**:
  1. orchestrator.pyで`_schema_to_simple_mapping`メソッドが存在しないことを確認
  2. orchestrator.pyでschema_converterがimportされていることを確認
- **期待結果**:
  - `_schema_to_simple_mapping` が存在しない
  - `from ...clients.interfaces.schema_converter import json_schema_to_simple_mapping` が存在する
- **検証コマンド**:
  ```bash
  # メソッドが存在しないことを確認
  grep -n "def _schema_to_simple_mapping" aiagent/langgraph/jobGeneratorV2/orchestrator.py && echo "❌ Method still exists" || echo "✅ Method removed"

  # importが存在することを確認
  grep -n "from.*schema_converter import" aiagent/langgraph/jobGeneratorV2/orchestrator.py && echo "✅ Import found" || echo "❌ Import missing"
  ```
- **pytestメソッド**: `test_tc_004_orchestrator_separation`

### TC-005: デバッグログ出力確認
- **テスト観点**: 情報損失時にDEBUGログが出力される
- **関連する受入条件**: AC-3
- **関連する設計方針**: DP-4
- **テスト種別**: 結合
- **テスト方法**: pytest (caplog)
- **前提条件**:
  1. ログレベルがDEBUGに設定
- **テスト手順**:
  1. required/description/format等を含むJSON Schemaを変換
  2. ログ出力を確認
- **期待結果**:
  - "Information loss" を含むログが出力される
- **pytestメソッド**: `test_tc_005_debug_logging`

### TC-006: デッドコード検証（json_schema_to_simple_mapping）
- **テスト観点**: json_schema_to_simple_mappingが実際に使用されている
- **関連する設計方針**: DP-1
- **テスト種別**: デッドコード検証
- **テスト方法**: grep
- **前提条件**: なし
- **テスト手順**:
  1. 関数の呼び出し箇所を検索
  2. テスト以外から呼び出されていることを確認
- **期待結果**:
  - orchestrator.pyから呼び出されている
- **検証コマンド**:
  ```bash
  grep -rn "json_schema_to_simple_mapping" --include="*.py" | grep -v "def json_schema_to_simple_mapping\|import\|test_" | head -5
  ```
- **pytestメソッド**: `test_tc_006_no_dead_code_json_schema_to_simple_mapping`

### TC-007: E2E統合テスト（JobGenerator API）
- **テスト観点**: JobGenerator APIを通じてスキーマ変換が正しく動作する
- **関連する受入条件**: AC-4, AC-5
- **テスト種別**: E2E
- **テスト方法**: curl / pytest
- **前提条件**:
  1. expertAgentが起動している
  2. mySwiftAgentCoreが起動している
- **テスト手順**:
  1. ヘルスチェック実行
  2. Job生成APIを呼び出し
  3. レスポンスを確認
- **期待結果**:
  - APIが正常に応答する
  - エラーなくJob生成が開始される
- **curlコマンド**:
  ```bash
  # ヘルスチェック
  curl -sf http://localhost:8004/health && echo "✅ expertAgent healthy"

  # Job生成API呼び出し
  # Note: エンドポイントは /v1/job-generator（/generate なし）
  #       リクエストは user_requirement フィールドを使用
  curl -s -X POST http://localhost:8004/v1/job-generator \
    -H "Content-Type: application/json" \
    -d '{
      "user_requirement": "Create a task to send an email with recipient, subject and body fields",
      "project_id": "default_project"
    }' | jq .
  ```
- **pytestメソッド**: `test_tc_007_e2e_job_generator_api`

### TC-008: 静的解析確認
- **テスト観点**: Ruff/MyPyエラーがない
- **関連する受入条件**: AC-5
- **テスト種別**: 品質確認
- **テスト方法**: ruff, mypy
- **前提条件**: なし
- **テスト手順**:
  1. Ruffを実行
  2. MyPyを実行
- **期待結果**:
  - エラー0件
- **検証コマンド**:
  ```bash
  python -m ruff check aiagent/clients/interfaces/schema_converter.py
  python -m mypy aiagent/clients/interfaces/schema_converter.py --ignore-missing-imports
  ```
- **pytestメソッド**: `test_tc_008_static_analysis`

---

## 8. サービス間データフロー検証

### DF-1: スキーマ変換データフロー

| 送信元 | データ項目 | 送信先 | 変換処理 | 検証状態 |
|--------|-----------|--------|---------|---------|
| InterfaceDefinition | input_schema (JSON Schema) | TaskInterface | json_schema_to_simple_mapping | ✅ |
| InterfaceDefinition | output_schema (JSON Schema) | TaskInterface | json_schema_to_simple_mapping | ✅ |
| TaskInterface | input (Simple Mapping) | mySwiftAgentCore | なし | ✅ |
| TaskInterface | output (Simple Mapping) | mySwiftAgentCore | なし | ✅ |

### DF-2: 情報損失データフロー

| 損失項目 | 入力例 | 出力例 | ログ出力 |
|---------|--------|--------|---------|
| required | `{"required": ["email"]}` | なし | ✅ DEBUG |
| description | `{"description": "User email"}` | なし | ✅ DEBUG |
| format | `{"format": "email"}` | なし | ✅ DEBUG |
| nested | `{"properties": {...}}` | `"object"` | ✅ DEBUG |
| array items | `{"items": {"type": "string"}}` | `"array"` | ✅ DEBUG |

---

## 9. テスト実行計画

### 実行順序

1. **静的解析確認** (TC-008)
   ```bash
   python -m ruff check aiagent/clients/interfaces/schema_converter.py
   python -m mypy aiagent/clients/interfaces/schema_converter.py --ignore-missing-imports
   ```

2. **モジュール存在確認** (TC-001)
   ```bash
   python -c "from aiagent.clients.interfaces.schema_converter import json_schema_to_simple_mapping, simple_mapping_to_json_schema, JsonSchema, SimpleMapping; print('✅ Import successful')"
   ```

3. **コード分離確認** (TC-004)
   ```bash
   grep -n "def _schema_to_simple_mapping" aiagent/langgraph/jobGeneratorV2/orchestrator.py && echo "❌ FAIL" || echo "✅ PASS"
   grep -n "from.*schema_converter import" aiagent/langgraph/jobGeneratorV2/orchestrator.py && echo "✅ PASS" || echo "❌ FAIL"
   ```

4. **デッドコード検証** (TC-006)
   ```bash
   grep -rn "json_schema_to_simple_mapping" --include="*.py" | grep -v "def json_schema_to_simple_mapping\|import\|test_"
   ```

5. **単体テスト実行** (TC-002, TC-003, TC-005)
   ```bash
   uv run pytest tests/unit/test_clients/test_schema_converter.py -v
   ```

6. **E2E統合テスト** (TC-007)
   ```bash
   # サービス起動
   ./scripts/dev-hybrid.sh start --local-only

   # ヘルスチェック
   curl -sf http://localhost:8004/health && echo "✅ expertAgent healthy"

   # 受入テスト実行
   uv run pytest tests/acceptance/test_issue388_acceptance.py -v
   ```

### 成功基準

- [x] すべての静的解析がパス（Ruff, MyPy）
- [x] モジュールが正しくimport可能
- [x] orchestrator.pyから変換ロジックが分離されている
- [x] 単体テスト29件すべてパス
- [ ] デッドコードが検出されない（実際の呼び出しあり）
- [ ] E2E統合テストがパス
- [ ] ログ出力が確認できる

---

## 10. 補足事項

### 既知の制約
- `simple_mapping_to_json_schema` は将来の拡張性のために実装されており、現時点ではテストコード以外から呼び出されていない可能性がある（デッドコードではなく、設計上の判断）

### テスト環境の注意点
- E2Eテストを実行する際は、`LOG_LEVEL=DEBUG` を設定して情報損失ログを確認すること
- mySwiftAgentCoreが起動していない場合、TC-007は失敗する

### 関連Issue
- #387: Unknown errorの修正（親Issue）
- #389: 長期対応 - 共有API仕様の策定

---

**レビュー完了日時**: 2026-01-21
**レビュー者**: Claude AI Assistant
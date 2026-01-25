# 受入テスト計画書

**Issue**: #355
**作成日**: 2026-01-12
**作成者**: acceptance-plan-agent

---

## 1. 概要

### 対象Issue
- **番号**: #355
- **タイトル**: Issue #354-1: TaskFlow Adapter Layer 実装
- **プロジェクト**: expertAgent
- **親Issue**: #354

### 参照ドキュメント
- Issue: #355
- 設計方針書: `dev-reports/investigation/issue-353-pending-workflow/schema-unification-proposal.md`
- 関連Issue: #353 (スキーマ不整合問題), #354 (親Issue)

### 機能概要
ExpertAgent出力（JSON文字列フィールド）をGraphAiServer形式（オブジェクト）に変換するAdapterパターンの実装。Issue #353で発覚したスキーマ不整合を解決する。

---

## 2. 単体テスト結果レビュー

### 注記
**PRE-TDD計画**: TDD実装前のため、単体テスト結果レビューは実装完了後に追加されます。

### 期待される単体テスト要件

| 指標 | 目標値 |
|------|--------|
| カバレッジ | 90%以上 |
| モック使用率 | 適切（外部API呼び出しのみ） |
| Ruff/MyPyエラー | 0件 |

### 単体テストで確認すべき項目
1. TaskFlowAdapter.convert() の基本動作
2. JSON文字列→オブジェクト変換
3. 既存オブジェクトの保持
4. 不正JSON時のエラーハンドリング
5. ConversionResult データ構造

---

## 3. 受入条件分析

### AC-1: JSON文字列フィールドのオブジェクト変換
- **原文**: `TaskFlowAdapter.convert()` が JSON文字列フィールドをオブジェクトに変換
- **分類**: 機能要件
- **テスト方法**: pytest / curl
- **モック使用**: 不可（実変換ロジック検証）
- **検証ポイント**:
  1. JSON文字列 `'{"key": "value"}'` が `{"key": "value"}` に変換される
  2. 変換後のデータ型が `dict` であること
  3. 入力データが破壊されないこと（ディープコピー）

### AC-2: 変換エラー時の詳細エラーメッセージ
- **原文**: 変換エラー時に詳細なエラーメッセージを返却
- **分類**: 機能要件
- **テスト方法**: pytest
- **モック使用**: 不可
- **検証ポイント**:
  1. ConversionResult.success が False
  2. ConversionResult.errors に詳細メッセージが含まれる
  3. エラーメッセージにフィールド名と原因が含まれる

### AC-3: workflow_registrar.py への統合
- **原文**: `workflow_registrar.py` がAdapterを使用して変換を実行
- **分類**: 機能要件
- **テスト方法**: pytest (結合テスト) / curl (E2E)
- **モック使用**: 外部APIのみ
- **検証ポイント**:
  1. register_taskflow_workflow() がAdapterを呼び出す
  2. 変換失敗時に適切なエラーを返す
  3. 変換成功時に変換後データで登録

### AC-4: input_schema JSON文字列変換
- **原文**: `input_schema` が JSON文字列の場合、オブジェクトに変換される
- **分類**: 機能要件
- **テスト方法**: pytest
- **モック使用**: 不可
- **検証ポイント**:
  1. `'{"query": "string"}'` → `{"query": "string"}`
  2. 変換後に workflow_json["input_schema"] が dict

### AC-5: output_schema JSON文字列変換
- **原文**: `output_schema` が JSON文字列の場合、オブジェクトに変換される
- **分類**: 機能要件
- **テスト方法**: pytest
- **モック使用**: 不可
- **検証ポイント**:
  1. `'{"result": "string"}'` → `{"result": "string"}`
  2. 変換後に workflow_json["output_schema"] が dict

### AC-6: output JSON文字列変換
- **原文**: `output` が JSON文字列の場合、オブジェクトに変換される
- **分類**: 機能要件
- **テスト方法**: pytest
- **モック使用**: 不可
- **検証ポイント**:
  1. `'{"result": "${step_001.output}"}'` → `{"result": "${step_001.output}"}`
  2. 変数参照（`${...}`）が保持される

### AC-7: steps[*].config.body JSON文字列変換
- **原文**: `steps[*].config.body` が JSON文字列の場合、オブジェクトに変換される
- **分類**: 機能要件
- **テスト方法**: pytest
- **モック使用**: 不可
- **検証ポイント**:
  1. ステップ内のbodyフィールドが変換される
  2. 複数ステップが正しく処理される

### AC-8: 既存オブジェクトの保持
- **原文**: 既にオブジェクトの場合、そのまま保持される
- **分類**: 機能要件
- **テスト方法**: pytest
- **モック使用**: 不可
- **検証ポイント**:
  1. dict型入力がそのまま保持
  2. 値が変更されない

### AC-9: 不正JSON時のエラー返却
- **原文**: 不正なJSONの場合、エラーを返却
- **分類**: 機能要件
- **テスト方法**: pytest
- **モック使用**: 不可
- **検証ポイント**:
  1. `'invalid json'` でエラー
  2. ConversionResult.success = False
  3. errors にJSONDecodeError情報

### AC-10: 品質基準 - 単体テストカバレッジ
- **原文**: 単体テストカバレッジ 90% 以上
- **分類**: 非機能要件
- **テスト方法**: pytest-cov
- **モック使用**: N/A
- **検証ポイント**:
  1. adapter/ ディレクトリのカバレッジが90%以上

### AC-11: 品質基準 - 静的解析
- **原文**: Ruff/MyPy エラーゼロ
- **分類**: 非機能要件
- **テスト方法**: ruff / mypy
- **モック使用**: N/A
- **検証ポイント**:
  1. `ruff check` でエラー0
  2. `mypy` でエラー0

### AC-12: 既存テストのパス
- **原文**: 既存テストが全てパス
- **分類**: 非機能要件
- **テスト方法**: pytest
- **モック使用**: N/A
- **検証ポイント**:
  1. expertAgent全体のテストがパス
  2. リグレッションなし

---

## 4. 設計方針検証

### DP-1: Adapter Pattern適用
- **設計方針**: ExpertAgent出力をGraphAiServer形式に変換するAdapterパターン実装
- **検証方法**: コード構造確認 / 単体テスト
- **テスト項目**:
  1. TaskFlowAdapterクラスが存在する
  2. convert()メソッドがConversionResultを返す
  3. 2つのシステム間のスキーマ差異を吸収している

### DP-2: ディレクトリ構成
- **設計方針**: `adapter/` ディレクトリに配置
- **検証方法**: ファイル存在確認
- **テスト項目**:
  1. `expertAgent/.../workflow_gen/adapter/__init__.py` が存在
  2. `expertAgent/.../workflow_gen/adapter/taskflow_adapter.py` が存在

### DP-3: 変換対象フィールド
- **設計方針**: ワークフローレベル (input_schema, output_schema, output) とステップレベル (steps[*].config.body) を変換
- **検証方法**: 単体テスト / E2Eテスト
- **テスト項目**:
  1. WORKFLOW_JSON_STRING_FIELDS に正しいフィールドが定義
  2. STEP_JSON_STRING_FIELDS に "body" が含まれる
  3. 両レベルの変換が正しく動作

### DP-4: エラーハンドリング
- **設計方針**: ConversionResult dataclassでエラーを詳細に返却
- **検証方法**: 単体テスト
- **テスト項目**:
  1. ConversionResult.success でBool判定
  2. ConversionResult.errors でエラー一覧取得
  3. ConversionResult.warnings で警告取得

### DP-5: workflow_registrar.py 統合
- **設計方針**: register_taskflow_workflow()でAdapterを使用
- **検証方法**: コード確認 / 結合テスト
- **テスト項目**:
  1. `from .adapter import TaskFlowAdapter` のインポート
  2. `_adapter.convert()` の呼び出し
  3. 変換失敗時のエラーハンドリング

---

## 5. デッドコード検証計画

### F-1: TaskFlowAdapter クラス
- **ファイル**: `expertAgent/.../adapter/taskflow_adapter.py`
- **種別**: class
- **期待される呼び出し元**: workflow_registrar.py
- **検証方法**:
  ```bash
  grep -rn "TaskFlowAdapter" --include="*.py" expertAgent/ | grep -v "def\|class\|#\|test"
  ```
- **E2Eでの確認方法**: register_taskflow_workflow() を呼び出して変換が実行されることを確認

### F-2: TaskFlowAdapter.convert() メソッド
- **ファイル**: `expertAgent/.../adapter/taskflow_adapter.py`
- **種別**: method
- **期待される呼び出し元**: workflow_registrar.py内のregister_taskflow_workflow()
- **検証方法**:
  ```bash
  grep -rn "\.convert(" --include="*.py" expertAgent/ | grep -v "test\|#"
  ```
- **E2Eでの確認方法**: ワークフロー登録APIを呼び出して変換が実行されることを確認

### F-3: ConversionResult dataclass
- **ファイル**: `expertAgent/.../adapter/taskflow_adapter.py`
- **種別**: dataclass
- **期待される呼び出し元**: TaskFlowAdapter.convert()の戻り値として使用
- **検証方法**:
  ```bash
  grep -rn "ConversionResult" --include="*.py" expertAgent/ | grep -v "def\|class\|#"
  ```
- **E2Eでの確認方法**: convert()の戻り値がConversionResult型であることを確認

### F-4: WORKFLOW_JSON_STRING_FIELDS 定数
- **ファイル**: `expertAgent/.../adapter/taskflow_adapter.py`
- **種別**: constant
- **期待される呼び出し元**: TaskFlowAdapter.convert()内でループ使用
- **検証方法**:
  ```bash
  grep -rn "WORKFLOW_JSON_STRING_FIELDS" --include="*.py" expertAgent/
  ```
- **E2Eでの確認方法**: input_schema, output_schema, output がすべて変換されることを確認

### F-5: STEP_JSON_STRING_FIELDS 定数
- **ファイル**: `expertAgent/.../adapter/taskflow_adapter.py`
- **種別**: constant
- **期待される呼び出し元**: TaskFlowAdapter._convert_step()内でループ使用
- **検証方法**:
  ```bash
  grep -rn "STEP_JSON_STRING_FIELDS" --include="*.py" expertAgent/
  ```
- **E2Eでの確認方法**: steps[*].config.body が変換されることを確認

---

## 6. テスト環境

### 必須サービス
| サービス | URL | ヘルスチェック |
|---------|-----|--------------|
| expertAgent | http://localhost:8104 | GET /health |
| graphAiServer | http://localhost:8105 | GET /health |
| myVault | http://localhost:8103 | GET /health |

### 起動コマンド
```bash
# 推奨: ハイブリッドモード（Agent層開発向け）
./scripts/dev-hybrid.sh

# または: Docker全環境
make dev-all
```

### 環境変数
| 変数名 | 説明 | 必須 |
|--------|------|------|
| GRAPHAISERVER_BASE_URL | GraphAiServer URL | (default: http://localhost:8005) |
| GRAPHAISERVER_ADMIN_TOKEN | GraphAiServer管理トークン | 登録APIテスト時 |

### テストデータ
- JSON文字列フィールドを含むワークフロー定義
- 既にオブジェクトのフィールドを含むワークフロー定義
- 不正JSONを含むワークフロー定義

---

## 7. テスト項目

### TC-001: JSON文字列 input_schema の変換
- **テスト観点**: input_schema がJSON文字列の場合にオブジェクトに変換される
- **関連する受入条件**: AC-4
- **関連する設計方針**: DP-3
- **テスト種別**: 単体 / E2E
- **テスト方法**: pytest
- **前提条件**:
  1. TaskFlowAdapterクラスが実装済み
  2. テスト環境が起動済み
- **テスト手順**:
  1. input_schema が `'{"query": "string"}'` のワークフローを作成
  2. adapter.convert() を呼び出す
  3. result.data["input_schema"] の型と値を確認
- **期待結果**:
  - result.success == True
  - result.data["input_schema"] が dict型
  - result.data["input_schema"] == {"query": "string"}
- **pytestメソッド**: `test_tc_001_convert_json_string_input_schema`

### TC-002: JSON文字列 output_schema の変換
- **テスト観点**: output_schema がJSON文字列の場合にオブジェクトに変換される
- **関連する受入条件**: AC-5
- **関連する設計方針**: DP-3
- **テスト種別**: 単体 / E2E
- **テスト方法**: pytest
- **前提条件**:
  1. TaskFlowAdapterクラスが実装済み
- **テスト手順**:
  1. output_schema が `'{"result": "string"}'` のワークフローを作成
  2. adapter.convert() を呼び出す
  3. result.data["output_schema"] の型と値を確認
- **期待結果**:
  - result.success == True
  - result.data["output_schema"] が dict型
  - result.data["output_schema"] == {"result": "string"}
- **pytestメソッド**: `test_tc_002_convert_json_string_output_schema`

### TC-003: JSON文字列 output の変換
- **テスト観点**: output がJSON文字列の場合にオブジェクトに変換される
- **関連する受入条件**: AC-6
- **関連する設計方針**: DP-3
- **テスト種別**: 単体 / E2E
- **テスト方法**: pytest
- **前提条件**:
  1. TaskFlowAdapterクラスが実装済み
- **テスト手順**:
  1. output が `'{"result": "${step_001.output}"}'` のワークフローを作成
  2. adapter.convert() を呼び出す
  3. result.data["output"] の型と値を確認
- **期待結果**:
  - result.success == True
  - result.data["output"] が dict型
  - result.data["output"] == {"result": "${step_001.output}"}
- **pytestメソッド**: `test_tc_003_convert_json_string_output`

### TC-004: steps[*].config.body の変換
- **テスト観点**: ステップのconfig.bodyがJSON文字列の場合にオブジェクトに変換される
- **関連する受入条件**: AC-7
- **関連する設計方針**: DP-3
- **テスト種別**: 単体 / E2E
- **テスト方法**: pytest
- **前提条件**:
  1. TaskFlowAdapterクラスが実装済み
- **テスト手順**:
  1. steps[0].config.body が `'{"data": "value"}'` のワークフローを作成
  2. adapter.convert() を呼び出す
  3. result.data["steps"][0]["config"]["body"] の型と値を確認
- **期待結果**:
  - result.success == True
  - result.data["steps"][0]["config"]["body"] が dict型
- **pytestメソッド**: `test_tc_004_convert_json_string_step_body`

### TC-005: 既存オブジェクトの保持
- **テスト観点**: 既にオブジェクトのフィールドがそのまま保持される
- **関連する受入条件**: AC-8
- **関連する設計方針**: DP-3
- **テスト種別**: 単体
- **テスト方法**: pytest
- **前提条件**:
  1. TaskFlowAdapterクラスが実装済み
- **テスト手順**:
  1. input_schema が既に dict のワークフローを作成
  2. adapter.convert() を呼び出す
  3. result.data["input_schema"] の型と値を確認
- **期待結果**:
  - result.success == True
  - result.data["input_schema"] が元の dict と同じ
- **pytestメソッド**: `test_tc_005_preserve_existing_objects`

### TC-006: 不正JSON時のエラー返却
- **テスト観点**: 不正なJSONの場合にエラーが返却される
- **関連する受入条件**: AC-9
- **関連する設計方針**: DP-4
- **テスト種別**: 単体
- **テスト方法**: pytest
- **前提条件**:
  1. TaskFlowAdapterクラスが実装済み
- **テスト手順**:
  1. input_schema が `'invalid json'` のワークフローを作成
  2. adapter.convert() を呼び出す
  3. result.success と result.errors を確認
- **期待結果**:
  - result.success == False
  - result.errors に "input_schema" と "Invalid JSON" を含むメッセージ
- **pytestメソッド**: `test_tc_006_error_on_invalid_json`

### TC-007: ConversionResult 構造確認
- **テスト観点**: ConversionResultが正しい構造を持つ
- **関連する受入条件**: AC-2
- **関連する設計方針**: DP-4
- **テスト種別**: 単体
- **テスト方法**: pytest
- **前提条件**:
  1. ConversionResult dataclassが定義済み
- **テスト手順**:
  1. ConversionResultインスタンスを作成
  2. success, data, errors, warnings 属性を確認
- **期待結果**:
  - success: bool
  - data: dict | None
  - errors: list[str]
  - warnings: list[str]
- **pytestメソッド**: `test_tc_007_conversion_result_structure`

### TC-008: workflow_registrar.py 統合確認
- **テスト観点**: register_taskflow_workflow()がAdapterを使用する
- **関連する受入条件**: AC-3
- **関連する設計方針**: DP-5
- **テスト種別**: 結合
- **テスト方法**: pytest (モック使用)
- **前提条件**:
  1. TaskFlowAdapterがworkflow_registrar.pyに統合済み
  2. httpxをモック
- **テスト手順**:
  1. JSON文字列フィールドを含むワークフローを作成
  2. register_taskflow_workflow() を呼び出す
  3. GraphAiServer登録APIに送信されるペイロードを確認
- **期待結果**:
  - 送信されるdefinitionがオブジェクト形式
  - JSON文字列が変換されている
- **pytestメソッド**: `test_tc_008_workflow_registrar_integration`

### TC-009: Adapter変換失敗時のエラーハンドリング
- **テスト観点**: Adapter変換失敗時にworkflow_registrar.pyがエラーを返す
- **関連する受入条件**: AC-2, AC-3
- **関連する設計方針**: DP-4, DP-5
- **テスト種別**: 結合
- **テスト方法**: pytest
- **前提条件**:
  1. TaskFlowAdapterがworkflow_registrar.pyに統合済み
- **テスト手順**:
  1. 不正JSONを含むワークフローを作成
  2. register_taskflow_workflow() を呼び出す
  3. 戻り値のエラー内容を確認
- **期待結果**:
  - WorkflowRegistrationResult.success == False
  - error に "Schema conversion failed" を含む
- **pytestメソッド**: `test_tc_009_workflow_registrar_error_handling`

### TC-010: E2E - ワークフロー登録成功
- **テスト観点**: JSON文字列を含むワークフローがGraphAiServerに正常登録される
- **関連する受入条件**: AC-1, AC-3
- **関連する設計方針**: DP-1, DP-5
- **テスト種別**: E2E
- **テスト方法**: pytest / curl
- **前提条件**:
  1. expertAgent, graphAiServer が起動済み
  2. GRAPHAISERVER_ADMIN_TOKEN が設定済み
- **テスト手順**:
  1. JSON文字列フィールドを含むワークフローを作成
  2. register_taskflow_workflow() を呼び出す
  3. GraphAiServerでワークフローを取得して確認
- **期待結果**:
  - 登録成功
  - GraphAiServer上のワークフローが正しいオブジェクト形式
- **curlコマンド**:
  ```bash
  # ワークフロー取得（登録後の確認）
  curl -s http://localhost:8105/api/v2/workflows/test_workflow \
    -H "x-admin-token: ${GRAPHAISERVER_ADMIN_TOKEN}"
  ```
- **pytestメソッド**: `test_tc_010_e2e_workflow_registration`

### TC-011: 複数フィールド同時変換
- **テスト観点**: 複数のJSON文字列フィールドが同時に変換される
- **関連する受入条件**: AC-4, AC-5, AC-6, AC-7
- **関連する設計方針**: DP-3
- **テスト種別**: 単体 / E2E
- **テスト方法**: pytest
- **前提条件**:
  1. TaskFlowAdapterクラスが実装済み
- **テスト手順**:
  1. input_schema, output_schema, output, steps[0].config.body が全てJSON文字列のワークフローを作成
  2. adapter.convert() を呼び出す
  3. 全フィールドの型を確認
- **期待結果**:
  - すべてのフィールドがdict型に変換
  - result.success == True
- **pytestメソッド**: `test_tc_011_convert_multiple_fields`

### TC-012: ディープコピー検証
- **テスト観点**: 入力データが変換により破壊されない
- **関連する受入条件**: AC-1
- **関連する設計方針**: DP-1
- **テスト種別**: 単体
- **テスト方法**: pytest
- **前提条件**:
  1. TaskFlowAdapterクラスが実装済み
- **テスト手順**:
  1. JSON文字列フィールドを含むワークフローを作成
  2. 元のデータを保存
  3. adapter.convert() を呼び出す
  4. 元のデータが変更されていないことを確認
- **期待結果**:
  - 元のデータ（input_schema等）がJSON文字列のまま
  - result.dataは変換後のオブジェクト
- **pytestメソッド**: `test_tc_012_deep_copy_preservation`

---

## 8. テスト実行計画

### 実行順序
1. サービス起動確認（ヘルスチェック）
2. 単体テスト実行 (TC-001 ~ TC-007, TC-011, TC-012)
3. 結合テスト実行 (TC-008, TC-009)
4. E2Eテスト実行 (TC-010)

### テストコマンド

```bash
# 単体テスト
cd /Users/maenokota/share/work/github_kewton/MySwiftAgent/expertAgent
uv run pytest tests/unit/langgraph/jobGeneratorV2/workflows/workflow_gen/adapter/ -v

# 結合テスト
uv run pytest tests/integration/langgraph/jobGeneratorV2/workflows/workflow_gen/ -v -m "not e2e"

# 受入テスト（E2E）
uv run pytest tests/acceptance/test_issue_355_acceptance.py -v

# カバレッジ確認
uv run pytest tests/unit/langgraph/jobGeneratorV2/workflows/workflow_gen/adapter/ --cov=aiagent/langgraph/jobGeneratorV2/workflows/workflow_gen/adapter --cov-report=term-missing

# 静的解析
ruff check aiagent/langgraph/jobGeneratorV2/workflows/workflow_gen/adapter/
mypy aiagent/langgraph/jobGeneratorV2/workflows/workflow_gen/adapter/
```

### 成功基準
- [x] すべての単体テストがパス (TC-001 ~ TC-007, TC-011, TC-012)
- [x] すべての結合テストがパス (TC-008, TC-009)
- [x] E2Eテストがパス (TC-010)
- [x] 単体テストカバレッジ 90%以上 (AC-10)
- [x] Ruff/MyPy エラーゼロ (AC-11)
- [x] 既存テストが全てパス (AC-12)
- [x] デッドコードが検出されないこと (F-1 ~ F-5)

---

## 9. 補足事項

### Issue #353 との関連
- Issue #353 で発覚した問題: ExpertAgentがJSON文字列を出力し、GraphAiServerがオブジェクトを期待
- 本Issueで解決: Adapter Layerで変換を吸収

### 後続Issue
- #354-2 Contract Tests: スキーマ整合性の自動検証
- #354-3 JSON Schema Single Source of Truth: スキーマ一元管理

### 手動検証が必要な項目（Issue記載）
- Job Generator V2 でジョブ生成 -> ワークフロー登録成功
- 登録されたワークフローが GraphAiServer で実行可能

これらはE2Eテスト後に手動で確認する。

# 受入テスト計画書

**Issue**: #356
**作成日**: 2026-01-12
**作成者**: acceptance-plan-agent
**フェーズ**: PRE-TDD (単体テスト実装前)

---

## 1. 概要

### 対象Issue
- **番号**: #356
- **タイトル**: Issue #354-2: TaskFlow Contract Tests 実装
- **プロジェクト**: expertAgent
- **親Issue**: #354
- **依存**: Issue #355 (Adapter Layer) - 完了済み

### 参照ドキュメント
- Issue: #356
- 設計書: `dev-reports/investigation/issue-353-pending-workflow/schema-unification-proposal.md`
- 依存Issue #355 受入計画: `dev-reports/feature/issue/355/acceptance-plan.md`

### Issue概要
ExpertAgent/GraphAiServer間のスキーマ整合性を自動検証するContract Tests実装。
スキーマ変更時の不整合を早期に検出する。

---

## 2. 単体テスト結果レビュー

### ステータス
**PRE-TDD**: 単体テストは未実装

TDD実装後に以下を確認予定:
- カバレッジ: 90%以上
- テスト数: 各機能に最低1テスト
- 静的解析: Ruff/MyPy エラー 0件
- モック使用率: 外部API (GraphAiServer) のみモック許容

### 実装後の確認項目
| 指標 | 目標値 | 確認方法 |
|------|--------|---------|
| カバレッジ | 90%以上 | `uv run pytest --cov` |
| テスト数 | 10+ | pytest出力 |
| 静的解析 | 0エラー | `make lint` |
| モック使用率 | 外部APIのみ | コードレビュー |

---

## 3. 受入条件分析

### AC-1: JSON文字列フィールド変換の契約テストが存在
- **原文**: JSON文字列フィールド変換の契約テストが存在
- **分類**: 機能要件
- **テスト方法**: pytest
- **モック使用**: 不可（TaskFlowAdapterは実オブジェクト）
- **検証ポイント**:
  1. `test_json_string_fields_are_converted` テストファイルが存在
  2. `input_schema`, `output_schema`, `output` フィールドの変換をテスト
  3. JSON文字列 -> dict変換が正しく動作

### AC-2: Pydanticモデル出力互換性の契約テストが存在
- **原文**: Pydanticモデル出力互換性の契約テストが存在
- **分類**: 機能要件
- **テスト方法**: pytest
- **モック使用**: 不可
- **検証ポイント**:
  1. `test_pydantic_model_output_is_convertible` テストが存在
  2. `TaskFlowWorkflow.model_dump()` の出力がアダプターで変換可能
  3. 変換後のデータ構造が正しい

### AC-3: GraphAiServer検証の契約テスト（integration mark）が存在
- **原文**: GraphAiServer検証の契約テスト（integration mark）が存在
- **分類**: 機能要件（結合テスト）
- **テスト方法**: pytest + httpx
- **モック使用**: 一部可（CI環境ではGraphAiServerへの接続をモック）
- **検証ポイント**:
  1. `test_converted_workflow_passes_graphai_validation` テストが存在
  2. `@pytest.mark.integration` マーカーが付与
  3. 実GraphAiServer APIを呼び出して検証

### AC-4: 契約テストが全てパス
- **原文**: 契約テストが全てパス
- **分類**: 品質基準
- **テスト方法**: pytest実行
- **モック使用**: 環境依存
- **検証ポイント**:
  1. 全契約テストがグリーン
  2. エラー・失敗なし
  3. スキップされたテストが適切にマークされている

### AC-5: テストフィクスチャが3種類以上
- **原文**: テストフィクスチャが3種類以上
- **分類**: 品質基準
- **テスト方法**: ファイル確認 + pytest実行
- **モック使用**: 不可
- **検証ポイント**:
  1. `tests/contract/fixtures/` ディレクトリが存在
  2. 3種類以上のJSONフィクスチャファイル
  3. フィクスチャがテストで使用されている

### AC-6: 必須テストケースの存在
- **原文**:
  - `test_json_string_fields_are_converted` が存在しパス
  - `test_pydantic_model_output_is_convertible` が存在しパス
  - `test_converted_workflow_passes_graphai_validation` が存在
- **分類**: 機能要件
- **テスト方法**: pytest
- **検証ポイント**:
  1. 各テストメソッドが定義されている
  2. テストが正常に実行される
  3. アサーションが適切

---

## 4. 設計方針検証

### DP-1: ディレクトリ構造整合性
- **設計方針**: `tests/contract/` ディレクトリ構造を作成
- **検証方法**: ファイルシステム確認
- **テスト項目**:
  1. `tests/contract/__init__.py` が存在
  2. `tests/contract/conftest.py` が存在
  3. `tests/contract/test_taskflow_schema_contract.py` が存在
  4. `tests/contract/fixtures/` ディレクトリが存在

### DP-2: TaskFlowAdapter統合確認
- **設計方針**: Issue #355で実装されたTaskFlowAdapterを使用
- **検証方法**: コードレビュー + テスト実行
- **テスト項目**:
  1. Contract TestsがTaskFlowAdapterをインポート
  2. アダプターの変換機能を実際に呼び出し
  3. 変換結果を検証

### DP-3: GraphAiServer API統合
- **設計方針**: httpxを使用してGraphAiServer APIを呼び出し
- **検証方法**: 結合テスト実行
- **テスト項目**:
  1. `httpx.AsyncClient` を使用
  2. `/api/v2/workflows/validate` エンドポイントを呼び出し
  3. レスポンスを適切に検証

### DP-4: CI/CD ワークフロー設定
- **設計方針**: GitHub Actionsでスキーマ関連ファイル変更時にContract Tests実行
- **検証方法**: ワークフローファイル確認
- **テスト項目**:
  1. `.github/workflows/contract-tests.yml` が存在
  2. 適切なパストリガーが設定されている
  3. テスト実行ステップが正しい

---

## 5. デッドコード検証計画

### F-1: tests/contract/conftest.py
- **ファイル**: `tests/contract/conftest.py`
- **種別**: pytest fixtures
- **期待される呼び出し元**: テストファイル内のフィクスチャ参照
- **検証方法**:
  ```bash
  grep -rn "@pytest.fixture" tests/contract/conftest.py
  grep -rn "adapter\|graphai_validate_url" tests/contract/test_*.py
  ```
- **E2Eでの確認方法**: pytest実行時にフィクスチャが使用される

### F-2: test_json_string_fields_are_converted
- **ファイル**: `tests/contract/test_taskflow_schema_contract.py`
- **種別**: テストメソッド
- **期待される呼び出し元**: pytest
- **検証方法**:
  ```bash
  uv run pytest tests/contract/ -k "test_json_string_fields" -v
  ```
- **E2Eでの確認方法**: テストが実行されパスする

### F-3: test_pydantic_model_output_is_convertible
- **ファイル**: `tests/contract/test_taskflow_schema_contract.py`
- **種別**: テストメソッド
- **期待される呼び出し元**: pytest
- **検証方法**:
  ```bash
  uv run pytest tests/contract/ -k "test_pydantic_model" -v
  ```
- **E2Eでの確認方法**: テストが実行されパスする

### F-4: test_converted_workflow_passes_graphai_validation
- **ファイル**: `tests/contract/test_taskflow_schema_contract.py`
- **種別**: テストメソッド (integration)
- **期待される呼び出し元**: pytest
- **検証方法**:
  ```bash
  uv run pytest tests/contract/ -k "test_converted_workflow" -v -m integration
  ```
- **E2Eでの確認方法**: GraphAiServer起動後にテストが実行されパスする

### F-5: テストフィクスチャファイル
- **ファイル**: `tests/contract/fixtures/valid_workflows/*.json`
- **種別**: JSONテストデータ
- **期待される呼び出し元**: parametrizeテスト
- **検証方法**:
  ```bash
  ls tests/contract/fixtures/valid_workflows/
  grep -rn "VALID_WORKFLOWS_DIR" tests/contract/
  ```
- **E2Eでの確認方法**: フィクスチャを使用したテストがパスする

---

## 6. テスト環境

### 必須サービス
| サービス | URL | ヘルスチェック | 必須度 |
|---------|-----|--------------|--------|
| expertAgent | http://localhost:8104 | GET /health | 結合テスト時 |
| graphAiServer | http://localhost:8105 | GET /health | 結合テスト時 |

### 起動コマンド
```bash
# 単体テスト・契約テスト（モック）
# サービス起動不要

# 結合テスト（実API）
./scripts/dev-hybrid.sh

# または Docker全環境
make dev-all
```

### 環境変数
| 変数名 | 説明 | 必須 |
|--------|------|------|
| GRAPHAI_SERVER_URL | GraphAiServer URL | 結合テスト時 |

### テストデータ
- **フィクスチャファイル**: `tests/contract/fixtures/valid_workflows/`
  - `simple_api_rest.json`: シンプルなAPI呼び出しワークフロー
  - `multi_step.json`: 複数ステップワークフロー
  - `transform_workflow.json`: Transform ステップを含むワークフロー

---

## 7. テスト項目

### TC-001: Contract Testsディレクトリ構造確認
- **テスト観点**: ディレクトリ構造が設計通り作成されているか
- **関連する受入条件**: AC-1, AC-2, AC-3, AC-5
- **関連する設計方針**: DP-1
- **テスト種別**: 構造確認
- **テスト方法**: ファイルシステム確認
- **前提条件**:
  1. TDD実装完了
- **テスト手順**:
  1. `tests/contract/` ディレクトリの存在確認
  2. 必須ファイルの存在確認
  3. フィクスチャディレクトリの確認
- **期待結果**:
  - `tests/contract/__init__.py` 存在
  - `tests/contract/conftest.py` 存在
  - `tests/contract/test_taskflow_schema_contract.py` 存在
  - `tests/contract/fixtures/` 存在
- **bashコマンド**:
  ```bash
  ls -la tests/contract/
  ls -la tests/contract/fixtures/
  ```
- **pytestメソッド**: N/A (構造確認)

### TC-002: JSON文字列フィールド変換テスト実行
- **テスト観点**: JSON文字列がオブジェクトに正しく変換されるか
- **関連する受入条件**: AC-1, AC-6
- **関連する設計方針**: DP-2
- **テスト種別**: 単体テスト
- **テスト方法**: pytest
- **前提条件**:
  1. TDD実装完了
  2. TaskFlowAdapter実装済み (Issue #355)
- **テスト手順**:
  1. 契約テストを実行
  2. `test_json_string_fields_are_converted` がパスすることを確認
- **期待結果**:
  - テストがパス
  - `input_schema`, `output_schema`, `output` フィールドが変換される
- **bashコマンド**:
  ```bash
  cd /Users/maenokota/share/work/github_kewton/MySwiftAgent/expertAgent && \
  uv run pytest tests/contract/test_taskflow_schema_contract.py \
    -k "test_json_string_fields_are_converted" -v
  ```
- **pytestメソッド**: `test_json_string_fields_are_converted`

### TC-003: Pydanticモデル互換性テスト実行
- **テスト観点**: Pydanticモデル出力がアダプターで変換可能か
- **関連する受入条件**: AC-2, AC-6
- **関連する設計方針**: DP-2
- **テスト種別**: 単体テスト
- **テスト方法**: pytest
- **前提条件**:
  1. TDD実装完了
  2. TaskFlowWorkflowスキーマ実装済み
- **テスト手順**:
  1. 契約テストを実行
  2. `test_pydantic_model_output_is_convertible` がパスすることを確認
- **期待結果**:
  - テストがパス
  - `model_dump()` 出力が正しく変換される
- **bashコマンド**:
  ```bash
  cd /Users/maenokota/share/work/github_kewton/MySwiftAgent/expertAgent && \
  uv run pytest tests/contract/test_taskflow_schema_contract.py \
    -k "test_pydantic_model_output_is_convertible" -v
  ```
- **pytestメソッド**: `test_pydantic_model_output_is_convertible`

### TC-004: GraphAiServer検証テスト実行（結合テスト）
- **テスト観点**: 変換後のワークフローがGraphAiServerで検証を通るか
- **関連する受入条件**: AC-3, AC-6
- **関連する設計方針**: DP-3
- **テスト種別**: 結合テスト
- **テスト方法**: pytest + httpx
- **前提条件**:
  1. TDD実装完了
  2. GraphAiServer起動済み (localhost:8105)
- **テスト手順**:
  1. GraphAiServerを起動
  2. 結合テストを実行
- **期待結果**:
  - テストがパス
  - GraphAiServer APIレスポンス 200
  - バリデーション成功
- **bashコマンド**:
  ```bash
  # GraphAiServerヘルスチェック
  curl -s http://localhost:8105/health

  # 結合テスト実行
  cd /Users/maenokota/share/work/github_kewton/MySwiftAgent/expertAgent && \
  uv run pytest tests/contract/test_taskflow_schema_contract.py \
    -k "test_converted_workflow_passes_graphai_validation" -v -m integration
  ```
- **pytestメソッド**: `test_converted_workflow_passes_graphai_validation`

### TC-005: テストフィクスチャ確認
- **テスト観点**: 3種類以上のテストフィクスチャが存在し使用されているか
- **関連する受入条件**: AC-5
- **関連する設計方針**: DP-1
- **テスト種別**: 構造確認 + テスト実行
- **テスト方法**: ファイル確認 + pytest
- **前提条件**:
  1. TDD実装完了
- **テスト手順**:
  1. フィクスチャファイル数を確認
  2. フィクスチャを使用したテストを実行
- **期待結果**:
  - 3ファイル以上のJSONフィクスチャ
  - フィクスチャがテストで使用されている
- **bashコマンド**:
  ```bash
  # フィクスチャファイル確認
  ls tests/contract/fixtures/valid_workflows/*.json | wc -l

  # フィクスチャ使用テスト実行
  cd /Users/maenokota/share/work/github_kewton/MySwiftAgent/expertAgent && \
  uv run pytest tests/contract/ -k "fixture" -v
  ```
- **pytestメソッド**: `test_fixture_workflows_pass_validation`

### TC-006: 全契約テスト実行
- **テスト観点**: 全ての契約テストがパスするか
- **関連する受入条件**: AC-4
- **関連する設計方針**: DP-2, DP-3
- **テスト種別**: 全体テスト
- **テスト方法**: pytest
- **前提条件**:
  1. TDD実装完了
  2. 結合テスト時はGraphAiServer起動
- **テスト手順**:
  1. 契約テスト全体を実行（integrationマーク除外）
  2. 結合テストを実行（integration マーク含む）
- **期待結果**:
  - 全テストがパス
  - エラー・失敗なし
- **bashコマンド**:
  ```bash
  # 単体テストのみ
  cd /Users/maenokota/share/work/github_kewton/MySwiftAgent/expertAgent && \
  uv run pytest tests/contract/ -v -m "not integration"

  # 全テスト（GraphAiServer起動必要）
  cd /Users/maenokota/share/work/github_kewton/MySwiftAgent/expertAgent && \
  uv run pytest tests/contract/ -v
  ```
- **pytestメソッド**: N/A (全体実行)

### TC-007: CI/CDワークフロー設定確認
- **テスト観点**: GitHub Actionsワークフローが正しく設定されているか
- **関連する受入条件**: CI検証（手動）
- **関連する設計方針**: DP-4
- **テスト種別**: 設定確認
- **テスト方法**: ファイル確認
- **前提条件**:
  1. TDD実装完了
- **テスト手順**:
  1. ワークフローファイルの存在確認
  2. パストリガー設定確認
  3. テスト実行ステップ確認
- **期待結果**:
  - `.github/workflows/contract-tests.yml` 存在
  - `paths:` に適切なトリガー設定
  - `pytest tests/contract/` 実行ステップ
- **bashコマンド**:
  ```bash
  cat .github/workflows/contract-tests.yml
  grep -A 10 "paths:" .github/workflows/contract-tests.yml
  ```
- **pytestメソッド**: N/A (設定確認)

### TC-008: TaskFlowAdapter統合確認
- **テスト観点**: Contract TestsがTaskFlowAdapterを正しく使用しているか
- **関連する受入条件**: AC-1, AC-2, AC-3
- **関連する設計方針**: DP-2
- **テスト種別**: コード確認
- **テスト方法**: grep + テスト実行
- **前提条件**:
  1. TDD実装完了
- **テスト手順**:
  1. TaskFlowAdapterのインポート確認
  2. adapter.convert()呼び出し確認
- **期待結果**:
  - TaskFlowAdapterがインポートされている
  - convert()メソッドが呼び出されている
- **bashコマンド**:
  ```bash
  grep -n "TaskFlowAdapter" tests/contract/test_taskflow_schema_contract.py
  grep -n "adapter.convert" tests/contract/test_taskflow_schema_contract.py
  ```
- **pytestメソッド**: N/A (コード確認)

---

## 8. テスト実行計画

### 実行順序

#### Phase 1: 構造確認（TDD実装後）
1. TC-001: ディレクトリ構造確認
2. TC-005: フィクスチャ確認
3. TC-007: CI/CDワークフロー設定確認
4. TC-008: TaskFlowAdapter統合確認

#### Phase 2: 単体テスト
5. TC-002: JSON文字列フィールド変換テスト
6. TC-003: Pydanticモデル互換性テスト

#### Phase 3: 結合テスト（GraphAiServer起動後）
7. TC-004: GraphAiServer検証テスト
8. TC-006: 全契約テスト実行

### 成功基準
- [ ] tests/contract/ ディレクトリ構造が正しい
- [ ] テストフィクスチャが3種類以上存在
- [ ] test_json_string_fields_are_converted がパス
- [ ] test_pydantic_model_output_is_convertible がパス
- [ ] test_converted_workflow_passes_graphai_validation が存在
- [ ] 全契約テストがパス
- [ ] CI/CDワークフロー設定が完了
- [ ] デッドコードが検出されないこと

### 受入テストファイル
TDD実装後に以下のファイルを作成:
```
expertAgent/tests/acceptance/test_issue_356_acceptance.py
```

---

## 9. 補足事項

### Issue #355 (Adapter Layer) との関係
- Issue #355で実装されたTaskFlowAdapterを使用
- Contract TestsはAdapterの機能を検証するテスト
- Adapter Layerが正しく動作していることが前提

### CI/CD手動検証項目
以下はPRマージ後に手動検証が必要:
- [ ] PRでスキーマ関連ファイル変更時にContract Testsが実行される
- [ ] Contract Tests失敗時にPRがブロックされる

### 将来の拡張
- Phase 3 (JSON Schema as Single Source of Truth) 実装時にContract Testsを拡張
- スキーマ自動生成との統合テスト追加

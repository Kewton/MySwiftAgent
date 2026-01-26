# 受入テスト計画書

**Issue**: #407
**作成日**: 2024-01-26
**作成者**: acceptance-plan (slash command)

---

## 1. 概要

### 対象Issue
- **番号**: #407
- **タイトル**: fix(expertAgent): SYSTEM_INJECTED_FIELDSの前方一致チェック対応
- **プロジェクト**: expertAgent
- **ラベル**: bug, fix
- **優先度**: 高（クロスサービスE2Eテストがブロックされている）

### 参照ドキュメント
- Issue: #407
- 設計方針書: `dev-reports/feature/issue/407/design-policy.md`
- アーキテクチャレビュー: `dev-reports/feature/issue/407/architecture-review.md`

### 問題の概要
`BodyTemplateValidator`の`SYSTEM_INJECTED_FIELDS`チェックが完全一致のみを行っているため、`user_input.{field}`形式の参照がバリデーションエラーとなる。

---

## 2. 単体テスト結果レビュー

### 現状の単体テスト状況
**注**: 本Issueは実装前のため、TDD実装結果は存在しない。既存テストの状況を記載。

### 既存テストクラス
`expertAgent/tests/unit/langgraph/jobGeneratorV2/validators/test_body_template_validator.py`:

| テストクラス | テスト数 | 内容 |
|-------------|---------|------|
| TestBodyTemplateValidator | 8 | 基本的なバリデーション機能 |
| TestBodyTemplateValidationResult | 3 | 結果データクラスのテスト |
| TestValidationStrategy | 2 | TaskFlow/GraphAI Strategy |
| TestValidationErrorTypes | 2 | エラータイプの分類 |
| **TestSystemInjectedFields** | **7** | **Issue #395 システムフィールド除外** |
| TestGraphAIValidationStrategy | 5 | GraphAI固有のバリデーション |

### 現在のTestSystemInjectedFieldsのカバレッジ
| テストメソッド | カバー範囲 | Issue #407対応 |
|---------------|-----------|---------------|
| test_system_injected_fields_constant_exists | 定数存在確認 | - |
| test_system_injected_fields_is_immutable | 不変性確認 | - |
| test_project_field_validation_skipped | `project`完全一致スキップ | 維持 |
| test_user_field_validation_continues_when_missing | ユーザーフィールド検証 | - |
| test_user_field_validation_passes_when_exists | ユーザーフィールド存在時 | - |
| test_mixed_system_and_user_fields | 混合フィールド | - |
| test_graphai_strategy_also_skips_system_fields | GraphAI対応 | 維持 |

### 単体テストでカバーされていない項目（追加必要）
1. `user_input.{field}`形式の前方一致スキップ
2. `project.{field}`形式の前方一致スキップ
3. `user_input.nested.deep.field`のような深いネスト
4. `user_input_extra`のような類似名の正しい検証（エラーになること）
5. `user_inputquery`のようなドットなし連結の正しい検証（エラーになること）
6. ヘルパー関数`_is_system_injected_field()`の直接テスト

---

## 3. 受入条件分析

### AC-1: user_input.{field}形式のスキップ
- **原文**: `user_input.{field}`形式の参照がバリデーションエラーにならない
- **分類**: 機能要件
- **テスト方法**: pytest単体テスト + E2Eテスト
- **モック使用**: 不可（実際のバリデーション実行）
- **検証ポイント**:
  1. `user_input.query`がスキップされる
  2. `user_input.max_results`がスキップされる
  3. バリデーション結果の`is_valid`がTrueになる

### AC-2: project.{field}形式のスキップ
- **原文**: `project.{field}`形式の参照がバリデーションエラーにならない
- **分類**: 機能要件
- **テスト方法**: pytest単体テスト
- **モック使用**: 不可
- **検証ポイント**:
  1. `project.name`がスキップされる
  2. `project.secrets.api_key`のようなネストもスキップされる

### AC-3: user_input完全一致の動作維持
- **原文**: 既存の`user_input`完全一致のスキップ動作が維持される
- **分類**: 機能要件（リグレッション防止）
- **テスト方法**: 既存テスト実行
- **モック使用**: 不可
- **検証ポイント**:
  1. 既存の`test_system_injected_fields_constant_exists`がパス
  2. 既存の`test_mixed_system_and_user_fields`がパス

### AC-4: project完全一致の動作維持
- **原文**: 既存の`project`完全一致のスキップ動作が維持される
- **分類**: 機能要件（リグレッション防止）
- **テスト方法**: 既存テスト実行
- **モック使用**: 不可
- **検証ポイント**:
  1. 既存の`test_project_field_validation_skipped`がパス

### AC-5: 無関係フィールドのバリデーション継続
- **原文**: 無関係なフィールド（例: `query`）のバリデーションが引き続き実行される
- **分類**: 機能要件（セキュリティ）
- **テスト方法**: pytest単体テスト
- **モック使用**: 不可
- **検証ポイント**:
  1. `query`（input_schemaに存在しない）がエラーになる
  2. `user_input_extra`（類似名だがドットなし）がエラーになる
  3. `user_inputquery`（ドットなし連結）がエラーになる

### AC-6: クロスサービスE2Eテスト成功
- **原文**: クロスサービスE2Eテストが成功する
- **分類**: 機能要件（E2E）
- **テスト方法**: クロスサービスE2Eテスト実行
- **モック使用**: 不可
- **検証ポイント**:
  1. Job生成APIが正常に動作
  2. Issue #403のフォールバックケースでエラーが発生しない
  3. TaskFlow/GraphAI両エンジンで動作

### AC-7: GraphAIエンジン対応
- **原文**: GraphAIエンジン使用時も`user_input.{field}`形式がエラーにならない
- **分類**: 機能要件
- **テスト方法**: pytest単体テスト
- **モック使用**: 不可
- **検証ポイント**:
  1. `GraphAIValidationStrategy.validate_job_body_reference`でスキップされる

### AC-8: ヘルパー関数の実装
- **原文**: モジュールレベルのプライベートヘルパー関数`_is_system_injected_field`が追加
- **分類**: 実装要件
- **テスト方法**: コード検査 + pytest
- **検証ポイント**:
  1. 関数が`body_template_validator.py`に存在
  2. `SYSTEM_INJECTED_FIELDS`定義の直後に配置
  3. 両Strategyで使用されている

### AC-9: user_input.{field}の単体テスト
- **原文**: 単体テストで `user_input.max_results`, `user_input.query` 等のドット区切りパスがスキップされることを検証
- **分類**: テスト要件
- **検証ポイント**:
  1. パラメータライズドテストが追加されている
  2. 複数のfield_pathパターンがテストされている

### AC-10: project.{field}の単体テスト
- **原文**: 単体テストで `project.name` 形式もスキップされることを検証
- **分類**: テスト要件
- **検証ポイント**:
  1. `project.name`のテストケースが存在
  2. テストがパス

### AC-11: リグレッションなし
- **原文**: 既存の単体テスト・結合テストが全てパスする
- **分類**: テスト要件
- **テスト方法**: 全テスト実行
- **検証ポイント**:
  1. `pytest expertAgent/tests/unit/`が全パス
  2. `pytest expertAgent/tests/integration/`が全パス

---

## 4. 設計方針検証

### DP-1: ヘルパー関数パターン
- **設計方針**: 共通ロジックはモジュールレベルのプライベートヘルパー関数として実装
- **検証方法**: コード検査
- **テスト項目**:
  1. `_is_system_injected_field()`関数が存在
  2. 関数がprivate（アンダースコア始まり）である
  3. モジュールレベルに配置されている

### DP-2: Strategy パターン維持
- **設計方針**: TaskFlowとGraphAIの両方で同じヘルパー関数を利用
- **検証方法**: コード検査 + テスト
- **テスト項目**:
  1. `TaskFlowValidationStrategy`が`_is_system_injected_field`を使用
  2. `GraphAIValidationStrategy`が`_is_system_injected_field`を使用
  3. 両Strategyで同一の動作をする

### DP-3: セキュリティファースト
- **設計方針**: ドット付き前方一致により誤マッチを防止
- **検証方法**: 境界値テスト
- **テスト項目**:
  1. `user_input_extra`がスキップされない（エラーになる）
  2. `user_inputquery`がスキップされない（エラーになる）
  3. `project_extra`がスキップされない（エラーになる）

### DP-4: 既存パターンとの整合性
- **設計方針**: 他のバリデータと同様のヘルパー関数パターンを採用
- **検証方法**: コード比較
- **テスト項目**:
  1. `field_in_schema()`と同様のシグネチャ
  2. 単一の責任（前方一致チェックのみ）

---

## 5. デッドコード検証計画

### F-1: _is_system_injected_field関数
- **ファイル**: `expertAgent/aiagent/langgraph/jobGeneratorV2/validators/body_template_validator.py`
- **種別**: function
- **期待される呼び出し元**:
  - `TaskFlowValidationStrategy.validate_job_body_reference`
  - `GraphAIValidationStrategy.validate_job_body_reference`
- **検証方法**:
  ```bash
  grep -rn "_is_system_injected_field" expertAgent/ --include="*.py" | grep -v "def _is_system_injected_field"
  ```
- **E2E確認**: Job生成APIを呼び出し、`user_input.{field}`形式がエラーにならないことを確認

### F-2: SYSTEM_INJECTED_FIELDS定数の継続使用
- **ファイル**: `body_template_validator.py`
- **種別**: constant
- **検証方法**:
  ```bash
  grep -rn "SYSTEM_INJECTED_FIELDS" expertAgent/ --include="*.py"
  ```
- **期待**: ヘルパー関数内で使用されている

---

## 6. テスト環境

### 必須サービス
| サービス | URL | ヘルスチェック | 必要性 |
|---------|-----|--------------|--------|
| expertAgent | http://localhost:8004 | GET /aiagent-api/health | E2Eテスト時のみ |
| myVault | http://localhost:8003 | GET /api/v1/health | E2Eテスト時のみ |

### 起動コマンド（E2Eテスト用）

```bash
# 1. 既存サービスを停止
./scripts/dev-hybrid.sh stop --local-only

# 2. ローカルモードでサービスを起動
./scripts/dev-hybrid.sh start --local-only
```

### 単体テスト実行（サービス起動不要）

```bash
# 単体テストのみ実行
cd expertAgent
uv run pytest tests/unit/langgraph/jobGeneratorV2/validators/test_body_template_validator.py -v

# 関連テストも実行
uv run pytest tests/unit/test_job_generator_v2/test_registration/test_master_manager.py -v -k "fallback"
```

### 環境変数
| 変数名 | 説明 | 必須 | 単体テスト | E2E |
|--------|------|------|----------|-----|
| PYTHONPATH | Pythonパス | ✅ | 自動設定 | 自動設定 |
| MYVAULT_ENABLED | MyVault有効化 | - | 不要 | true |

---

## 7. テスト項目

### TC-001: ヘルパー関数の存在確認
- **テスト観点**: ヘルパー関数が正しく実装されている
- **関連する受入条件**: AC-8
- **関連する設計方針**: DP-1
- **テスト種別**: 単体テスト
- **テスト方法**: pytest
- **前提条件**:
  1. 実装完了後
- **テスト手順**:
  1. `_is_system_injected_field`をインポート
  2. 関数が存在することを確認
- **期待結果**:
  - インポートが成功
  - callable である
- **pytestメソッド**: `test_is_system_injected_field_exists`

### TC-002: user_input完全一致のスキップ
- **テスト観点**: 既存動作の維持（リグレッション防止）
- **関連する受入条件**: AC-3
- **テスト種別**: 単体テスト
- **テスト方法**: pytest
- **テスト手順**:
  1. `_is_system_injected_field("user_input")`を呼び出し
- **期待結果**:
  - True を返す
- **pytestメソッド**: `test_system_injected_field_exact_match_user_input`

### TC-003: user_input.{field}のスキップ
- **テスト観点**: 前方一致スキップの動作確認
- **関連する受入条件**: AC-1, AC-9
- **関連する設計方針**: DP-3
- **テスト種別**: 単体テスト
- **テスト方法**: pytest (パラメータライズド)
- **テスト手順**:
  1. 各field_pathに対して`_is_system_injected_field`を呼び出し
- **テストデータ**:
  ```python
  @pytest.mark.parametrize("field_path,expected", [
      ("user_input.query", True),
      ("user_input.max_results", True),
      ("user_input.nested.deep.field", True),
  ])
  ```
- **期待結果**:
  - すべてTrue を返す
- **pytestメソッド**: `test_system_injected_field_prefix_matching_user_input`

### TC-004: project.{field}のスキップ
- **テスト観点**: project系フィールドの前方一致スキップ
- **関連する受入条件**: AC-2, AC-10
- **テスト種別**: 単体テスト
- **テスト方法**: pytest (パラメータライズド)
- **テストデータ**:
  ```python
  @pytest.mark.parametrize("field_path,expected", [
      ("project", True),
      ("project.name", True),
      ("project.secrets.api_key", True),
  ])
  ```
- **期待結果**:
  - すべてTrue を返す
- **pytestメソッド**: `test_system_injected_field_prefix_matching_project`

### TC-005: 無関係フィールドのバリデーション継続
- **テスト観点**: セキュリティ - 誤スキップ防止
- **関連する受入条件**: AC-5
- **関連する設計方針**: DP-3
- **テスト種別**: 単体テスト
- **テスト方法**: pytest (パラメータライズド)
- **テストデータ**:
  ```python
  @pytest.mark.parametrize("field_path,expected", [
      ("query", False),
      ("user_input_extra", False),
      ("user_inputquery", False),
      ("project_extra", False),
      ("projectname", False),
  ])
  ```
- **期待結果**:
  - すべてFalse を返す（スキップされない）
- **pytestメソッド**: `test_system_injected_field_non_matching`

### TC-006: TaskFlowStrategy統合テスト
- **テスト観点**: TaskFlowValidationStrategyでの動作確認
- **関連する受入条件**: AC-1, AC-8
- **関連する設計方針**: DP-2
- **テスト種別**: 単体テスト
- **テスト方法**: pytest
- **テスト手順**:
  1. TaskFlowValidationStrategyインスタンス作成
  2. `validate_job_body_reference("job.body.user_input.query", {})`呼び出し
- **期待結果**:
  - 空のエラーリストを返す
- **pytestメソッド**: `test_taskflow_strategy_skips_user_input_nested_field`

### TC-007: GraphAIStrategy統合テスト
- **テスト観点**: GraphAIValidationStrategyでの動作確認
- **関連する受入条件**: AC-7, AC-8
- **関連する設計方針**: DP-2
- **テスト種別**: 単体テスト
- **テスト方法**: pytest
- **テスト手順**:
  1. GraphAIValidationStrategyインスタンス作成
  2. `validate_job_body_reference("job.body.user_input.query", {})`呼び出し
- **期待結果**:
  - 空のエラーリストを返す
- **pytestメソッド**: `test_graphai_strategy_skips_user_input_nested_field`

### TC-008: BodyTemplateValidator統合テスト
- **テスト観点**: バリデーター全体での動作確認
- **関連する受入条件**: AC-1, AC-2
- **テスト種別**: 単体テスト
- **テスト方法**: pytest
- **テスト手順**:
  1. BodyTemplateValidatorインスタンス作成
  2. `user_input.query`を含むbody_templateでvalidate呼び出し
- **期待結果**:
  - `result.is_valid`がTrue
- **pytestメソッド**: `test_body_template_validator_with_nested_system_field`

### TC-009: 既存テストリグレッション確認
- **テスト観点**: 既存機能の維持
- **関連する受入条件**: AC-3, AC-4, AC-11
- **テスト種別**: 単体テスト + 結合テスト
- **テスト方法**: pytest
- **テスト手順**:
  1. 全単体テスト実行
  2. 全結合テスト実行
- **期待結果**:
  - 全テストパス
- **実行コマンド**:
  ```bash
  cd expertAgent
  uv run pytest tests/unit/ -v
  uv run pytest tests/integration/ -v
  ```

### TC-010: Issue #403関連テスト確認
- **テスト観点**: フォールバック機能との統合
- **関連する受入条件**: AC-6
- **テスト種別**: 受入テスト + 単体テスト
- **テスト方法**: pytest
- **テスト手順**:
  1. Issue #403受入テスト実行
  2. MasterManagerのフォールバックテスト実行
  3. 結合テストのフォールバックテスト実行
- **期待結果**:
  - `test_tc_004_fallback_to_user_input`がパス
  - `test_build_multi_dependency_template_fallback`がパス
  - `test_fallback_to_user_input_for_missing_field`がパス
- **実行コマンド**:
  ```bash
  cd expertAgent
  # Issue #403受入テスト
  uv run pytest tests/acceptance/test_issue_403_acceptance.py::test_tc_004_fallback_to_user_input -v
  # MasterManagerのフォールバック単体テスト
  uv run pytest tests/unit/test_job_generator_v2/test_registration/test_master_manager.py::test_build_multi_dependency_template_fallback -v
  # 結合テストのフォールバックテスト
  uv run pytest tests/integration/test_registration_validation.py::test_fallback_to_user_input_for_missing_field -v
  ```

### TC-011: デッドコード検証
- **テスト観点**: 実装した関数が実際に使用されている
- **関連する受入条件**: AC-8
- **テスト種別**: コード検査
- **テスト手順**:
  1. grep で呼び出し箇所を確認
- **期待結果**:
  - TaskFlowValidationStrategyで使用
  - GraphAIValidationStrategyで使用
- **検証コマンド**:
  ```bash
  grep -rn "_is_system_injected_field" expertAgent/aiagent/ --include="*.py"
  ```

### TC-012: エッジケーステスト
- **テスト観点**: 境界値テスト
- **関連する設計方針**: DP-3
- **テスト種別**: 単体テスト
- **テスト方法**: pytest (パラメータライズド)
- **テストデータ**:
  ```python
  @pytest.mark.parametrize("field_path,expected", [
      ("", False),           # 空文字列
      (".", False),          # ドットのみ
      ("user_input.", False), # 末尾ドット（不正な形式）
      (".user_input", False), # 先頭ドット
  ])
  ```
- **期待結果**:
  - すべてFalse を返す
- **pytestメソッド**: `test_system_injected_field_edge_cases`

---

## 8. テスト実行計画

### 実行順序
1. **Phase 1: 単体テスト実行**（所要時間目安: 約1分）
   - TC-001〜TC-008, TC-012を実行
   - カバレッジ90%以上を確認

2. **Phase 2: リグレッションテスト**（所要時間目安: 約5分）
   - TC-009: 全既存テストの実行
   - TC-010: Issue #403関連テストの確認

3. **Phase 3: デッドコード検証**（所要時間目安: 約30秒）
   - TC-011: grepによるコード検査

4. **Phase 4: E2Eテスト（オプション）**（所要時間目安: 約3分、サービス起動時間除く）
   - クロスサービスE2Eテストの実行
   - サービス起動が必要

### 成功基準
- [ ] すべてのpytestテストがパス
- [ ] カバレッジ90%以上を維持
- [ ] 静的解析エラーゼロ（Ruff/MyPy）
- [ ] すべての受入条件（AC-1〜AC-11）が検証済み
- [ ] デッドコードが検出されないこと
- [ ] Issue #403関連テストがパス

### テストファイル

**新規作成**:
- `expertAgent/tests/acceptance/test_issue_407_acceptance.py`

**修正対象**:
- `expertAgent/tests/unit/langgraph/jobGeneratorV2/validators/test_body_template_validator.py`
  - `TestSystemInjectedFields`クラスにテストケース追加

---

## 9. 補足事項

### 関連Issue
- Issue #403: body_template生成で複数タスクからのデータ集約をサポート（原因）
- Issue #395, #396: BodyTemplateValidator追加
- Issue #404: E2Eテスト時に発見

### エラーメッセージ（修正前）
```
Job creation failed (V2): Registration failed: Body template validation failed for task 'Google検索実行': MISSING_REFERENCE: Field 'user_input.max_results' not found in input_schema
```

### 修正後の期待動作
- `user_input.max_results`はSYSTEM_INJECTED_FIELDSの子フィールドとして認識
- バリデーションがスキップされ、エラーが発生しない
- Job生成が正常に完了する

---

**計画完了**: 2024-01-26
**次のステップ**: TDD実装フェーズへ移行
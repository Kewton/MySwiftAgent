# 受入テスト計画書

**Issue**: #408
**作成日**: 2026-01-26
**作成者**: acceptance-plan-agent

---

## 1. 概要

### 対象Issue
- **番号**: #408
- **タイトル**: feat(expertAgent): ユーザー入力フィールド名の整合性検証機能
- **プロジェクト**: expertAgent

### 背景
E2Eテストにおいて、LLM生成のInterface Definitionがユーザー入力フィールド名を変更（例：`email` → `recipient_email`）することで、実行時にフィールド参照が失敗しメール送信が失敗する問題が発生した。

### 参照ドキュメント
- Issue: #408
- 設計方針書: `dev-reports/feature/issue/408/design-policy.md`

---

## 2. 単体テスト結果レビュー

### TDD実装状況
- **状態**: TDD実装未実施
- **判定**: ⚠️ 単体テスト実装が必要

> **📝 注意**: TDD実装完了後、以下の項目を実際の値で更新すること
> - カバレッジ（目標: 90%以上）
> - 総テスト数
> - モック使用率

### 想定テストケース（設計方針書より）

| テストケース | 説明 | 期待結果 |
|------------|------|---------|
| test_user_input_field_mismatch_detection | 存在しないフィールドへの参照を検出 | USER_INPUT_FIELD_MISMATCH警告 |
| test_valid_user_input_field_no_warning | 存在するフィールドへの参照は警告なし | 警告なし |
| test_no_validation_when_user_input_schema_none | user_input_schema未指定時は検証スキップ | 警告なし（後方互換性） |
| test_multiple_field_mismatches | 複数の不整合フィールドを検出 | 複数警告 |
| test_fallback_warning_for_missing_field | フォールバック時の警告 | ログ出力 |

### 単体テストで検証すべき重要項目
1. `_validate_user_input_fields()`の正常動作
2. `USER_INPUT_FIELD_MISMATCH`警告の生成
3. 後方互換性（user_input_schema=None時のスキップ）
4. `_build_multi_dependency_template`のフォールバック検証

---

## 3. 受入条件分析

### AC-1: Interface Definitionプロンプト強化
- **原文**: Interface Definitionプロンプトにユーザー入力フィールド名保持ルールが追加されている
- **分類**: 機能要件
- **テスト方法**: ファイル内容確認 + LLM生成テスト
- **モック使用**: 不可（実LLM呼び出し必要）
- **検証ポイント**:
  1. `expertAgent/prompts/interface_schema/default.yaml`にフィールド名保持ルールが存在
  2. 禁止例・正しい例が記載されている
  3. 理由説明が含まれている

### AC-2: フィールド名不整合の検出機能
- **原文**: フィールド名不整合の検出機能が正しく動作することを確認
- **分類**: 機能要件
- **テスト方法**: pytest
- **モック使用**: 一部可（LLM呼び出しはモック可、検証ロジックは実行）
- **検証ポイント**:
  1. 存在しないフィールド名への参照で`USER_INPUT_FIELD_MISMATCH`警告が生成される
  2. 複数の不整合を全て検出できる
  3. 決定的なテストケースで100%検出

### AC-3: Body Template検証機能
- **原文**: Body Template検証時に`user_input.*`への参照を実際のユーザー入力スキーマと照合する機能が実装されている
- **分類**: 機能要件
- **テスト方法**: pytest（結合テスト）
- **モック使用**: 一部可
- **検証ポイント**:
  1. `BodyTemplateValidator.validate()`が`user_input_schema`を受け取る
  2. `user_input.X`参照時に`user_input_schema`と照合される
  3. 照合結果がWarningとして返される

### AC-4: _build_multi_dependency_templateのフォールバック検証
- **原文**: `_build_multi_dependency_template`のフォールバック時に、`user_input_schema`にフィールドが存在するか検証が行われる
- **分類**: 機能要件
- **テスト方法**: pytest + ログ確認
- **モック使用**: 一部可
- **検証ポイント**:
  1. フォールバック前に`field_name`が`user_input_schema`に存在するか確認
  2. 存在しない場合はWARNINGログが出力される
  3. ログに`Issue #408`と`Available fields`が含まれる

### AC-5: 警告出力機能
- **原文**: 存在しないフィールドへの参照を検出した場合、WARNINGログが出力され、生成結果のmetadataに警告情報が含まれる
- **分類**: 機能要件
- **テスト方法**: pytest + ログ確認
- **モック使用**: 一部可
- **検証ポイント**:
  1. WARNINGレベルでログ出力
  2. ValidationResult.warningsに警告情報が含まれる
  3. 警告メッセージに利用可能フィールドリストが含まれる

### AC-6: E2Eテストでメール送信成功
- **原文**: E2Eテストでメール送信が正常に動作することを確認
- **分類**: E2E要件
- **テスト方法**: シェルスクリプト + pytest
- **モック使用**: 不可（実サービス連携必須）
- **検証ポイント**:
  1. `./scripts/e2e/cross-service/test_full_workflow_e2e.sh`を3回実行
  2. 各実行でメール送信タスクが成功
  3. 3回中3回成功

---

## 4. 設計方針検証

### DP-1: ValidationStrategy維持
- **設計方針**: ValidationStrategyのインターフェースは変更しない。user_input専用の検証はBodyTemplateValidator.validate()内で一括実施
- **検証方法**: コード確認 + 後方互換性テスト
- **テスト項目**:
  1. `ValidationStrategy.validate_job_body_reference()`のシグネチャが変更されていない
  2. 既存テストが変更なしで通過する
  3. `user_input_schema=None`で呼び出しても正常動作

### DP-2: 新規メソッド追加
- **設計方針**: `_validate_user_input_fields()`メソッドを新規追加
- **検証方法**: コード確認 + 単体テスト
- **テスト項目**:
  1. メソッドが存在する
  2. `BodyTemplateValidationWarning`を返す
  3. `warning_type="USER_INPUT_FIELD_MISMATCH"`を使用

### DP-3: 後方互換性
- **設計方針**: デフォルト値Noneにより既存呼び出しは変更不要
- **検証方法**: 既存テスト実行
- **テスト項目**:
  1. `user_input_schema`なしで`validate()`を呼び出せる
  2. 既存の`BodyTemplateValidator`テストがすべて通過

### DP-4: 環境変数による制御
- **設計方針**: `BODY_TEMPLATE_STRICT_VALIDATION`で厳格モード切替
- **検証方法**: 環境変数設定 + テスト
- **テスト項目**:
  1. `BODY_TEMPLATE_STRICT_VALIDATION=false`で警告のみ
  2. `BODY_TEMPLATE_STRICT_VALIDATION=true`でエラー扱い

---

## 5. デッドコード検証計画

### F-1: _validate_user_input_fields()
- **ファイル**: `expertAgent/aiagent/langgraph/jobGeneratorV2/validators/body_template_validator.py`
- **種別**: method
- **期待される呼び出し元**: `BodyTemplateValidator.validate()`
- **検証方法**:
  ```bash
  grep -rn "_validate_user_input_fields" expertAgent/ --include="*.py" | grep -v "def _validate_user_input_fields"
  ```
- **E2E確認**: Job Generation APIを呼び出し、不整合フィールドで警告が出力されることを確認

### F-2: USER_INPUT_FIELD_MISMATCH定数
- **ファイル**: `body_template_validator.py`
- **種別**: constant/string
- **期待される呼び出し元**: `_validate_user_input_fields()`
- **検証方法**:
  ```bash
  grep -rn "USER_INPUT_FIELD_MISMATCH" expertAgent/ --include="*.py"
  ```
- **E2E確認**: 警告メッセージに`USER_INPUT_FIELD_MISMATCH`が含まれることを確認

### F-3: _get_user_input_schema()（実装される場合）
- **ファイル**: `expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/registration/master_manager.py`
- **種別**: method
- **期待される呼び出し元**: `create_masters()`, `_build_multi_dependency_template()`
- **検証方法**:
  ```bash
  grep -rn "_get_user_input_schema\|user_input_schema" expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/registration/ --include="*.py"
  ```
- **E2E確認**: MasterManager経由でJobが生成され、検証が実行されることを確認

### F-4: プロンプト強化ルール
- **ファイル**: `expertAgent/prompts/interface_schema/default.yaml`
- **種別**: yaml content
- **期待される使用箇所**: LLM呼び出し時のプロンプト
- **検証方法**:
  ```bash
  grep -rn "interface_schema" expertAgent/ --include="*.py" | head -20
  ```
- **E2E確認**: 実際のLLM生成でフィールド名が保持されることを確認（複数回テスト）

---

## 6. コンポーネント間整合性検証

### CI-1: バリデータ整合性
- **検証対象**: `_validate_user_input_fields()`と`_is_system_injected_field()`の連携
- **確認項目**:
  - [ ] `user_input`自体はスキップされる（Issue #407維持）
  - [ ] `user_input.X`のサブフィールドのみ検証される
  - [ ] 両方の関数が矛盾なく動作する

### CI-2: 警告生成の一貫性
- **検証対象**: `_build_multi_dependency_template`と`_validate_user_input_fields`の警告
- **検証方法**:
  ```bash
  # 両箇所からの警告メッセージフォーマットを比較
  grep -rn "Issue #408" expertAgent/ --include="*.py"
  grep -rn "USER_INPUT_FIELD_MISMATCH" expertAgent/ --include="*.py"

  # ログレベルの確認
  grep -rn "logger.warning\|logging.WARNING" expertAgent/aiagent/langgraph/jobGeneratorV2/ --include="*.py"
  ```
- **確認項目**:
  - [ ] 両箇所で同じフィールド名の問題を検出した場合の挙動
  - [ ] 警告メッセージのフォーマットが一貫している（フィールド名、利用可能フィールドリストの形式）
  - [ ] ログレベルが統一されている（WARNING）
  - [ ] 重複警告が発生した場合の許容（デバッグ目的として問題なし）

---

## 7. サービス間データフロー検証

### DF-1: user_input_schema伝播
| 送信元 | データ項目 | 送信先 | 取得方法 | 検証状態 |
|--------|-----------|--------|---------|---------|
| InterfaceSchema | input_schema | MasterManager | interfaces[first_task_id] | ❓ 要検証 |
| MasterManager | user_input_schema | BodyTemplateValidator | validate()引数 | ❓ 要検証 |
| MasterManager | user_input_schema | _build_multi_dependency_template | メソッド引数 | ❓ 要検証 |

### DF-2: 警告情報伝播
| 送信元 | データ項目 | 送信先 | 検証状態 |
|--------|-----------|--------|---------|
| _validate_user_input_fields | BodyTemplateValidationWarning | ValidationResult | ❓ 要検証 |
| ValidationResult | warnings | 呼び出し元 | ❓ 要検証 |
| MasterManager | log warning | Logger | ❓ 要検証 |

---

## 8. テスト環境

### 必須サービス
| サービス | URL | ヘルスチェック |
|---------|-----|--------------|
| expertAgent | http://localhost:8004 | GET /health |
| mySwiftAgentCore | http://localhost:8006 | GET /health |
| myVault | http://localhost:8003 | GET /health |

### 起動コマンド（E2Eテスト用 - 必須）

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
| BODY_TEMPLATE_STRICT_VALIDATION | 厳格モード | ❌ (テストで両方確認) |

### テストデータ
- ユーザー入力例: `{"email": "test@example.com", "keyword": "テスト"}`
- 不整合パターン: LLMが`recipient_email`を生成
- 正常パターン: LLMが`email`をそのまま使用

---

## 9. テスト項目

### TC-001: プロンプトにフィールド名保持ルールが存在する
- **テスト観点**: AC-1の検証（プロンプト強化）
- **関連する受入条件**: AC-1
- **関連する設計方針**: DP-1
- **テスト種別**: ファイル確認
- **テスト方法**: grep/cat
- **前提条件**:
  1. 実装完了後
- **テスト手順**:
  1. `expertAgent/prompts/interface_schema/default.yaml`を確認
  2. 「フィールド名保持ルール」または類似のセクションが存在するか確認
  3. 禁止例・正しい例が含まれるか確認
- **期待結果**:
  - フィールド名保持ルールが記載されている
  - 5つ以上の禁止例と正しい例が存在
- **確認コマンド**:
  ```bash
  grep -A 20 "フィールド名" expertAgent/prompts/interface_schema/default.yaml
  ```
- **pytestメソッド**: `test_tc_001_prompt_contains_field_name_rules`

### TC-002: 存在しないフィールド名への参照で警告が生成される
- **テスト観点**: AC-2の検証（不整合検出）
- **関連する受入条件**: AC-2, AC-3
- **関連する設計方針**: DP-2
- **テスト種別**: 単体テスト
- **テスト方法**: pytest
- **前提条件**:
  1. `_validate_user_input_fields()`が実装済み
- **テスト手順**:
  1. `user_input_schema = {"properties": {"email": {"type": "string"}}}`を用意
  2. `body_template = {"recipient": "{{job.body.user_input.recipient_email}}"}`を用意
  3. `validator.validate(..., user_input_schema=user_input_schema)`を実行
  4. `result.warnings`を確認
- **期待結果**:
  - `len(result.warnings) == 1`
  - `result.warnings[0].warning_type == "USER_INPUT_FIELD_MISMATCH"`
  - `"recipient_email"` in `result.warnings[0].message`
  - `"email"` in `result.warnings[0].message`（使用可能フィールド）
- **pytestメソッド**: `test_tc_002_detects_mismatched_field_name`

### TC-003: 正しいフィールド名への参照では警告が出ない
- **テスト観点**: AC-2の検証（正常ケース）
- **関連する受入条件**: AC-2, AC-3
- **関連する設計方針**: DP-2
- **テスト種別**: 単体テスト
- **テスト方法**: pytest
- **前提条件**:
  1. `_validate_user_input_fields()`が実装済み
- **テスト手順**:
  1. `user_input_schema = {"properties": {"email": {"type": "string"}}}`を用意
  2. `body_template = {"recipient": "{{job.body.user_input.email}}"}`を用意
  3. `validator.validate(..., user_input_schema=user_input_schema)`を実行
  4. `result.warnings`を確認
- **期待結果**:
  - `len(result.warnings) == 0`
- **pytestメソッド**: `test_tc_003_no_warning_for_valid_field_name`

### TC-004: user_input_schema=Noneで後方互換性を維持
- **テスト観点**: AC-3の後方互換性検証
- **関連する受入条件**: AC-3
- **関連する設計方針**: DP-3
- **テスト種別**: 単体テスト
- **テスト方法**: pytest
- **前提条件**:
  1. `validate()`シグネチャ変更済み
- **テスト手順**:
  1. `body_template = {"recipient": "{{job.body.user_input.any_field}}"}`を用意
  2. `validator.validate(..., user_input_schema=None)`を実行（または引数省略）
  3. `result.warnings`を確認
- **期待結果**:
  - エラーなく実行完了
  - user_input関連の警告なし（スキップされる）
- **pytestメソッド**: `test_tc_004_backward_compatibility_with_none_schema`

### TC-005: 複数の不整合フィールドを全て検出
- **テスト観点**: AC-2の網羅性検証
- **関連する受入条件**: AC-2
- **関連する設計方針**: DP-2
- **テスト種別**: 単体テスト
- **テスト方法**: pytest
- **前提条件**:
  1. `_validate_user_input_fields()`が実装済み
- **テスト手順**:
  1. `user_input_schema = {"properties": {"email": {}, "keyword": {}}}`を用意
  2. 複数の不整合参照を含むbody_templateを用意:
     ```python
     body_template = {
         "to": "{{job.body.user_input.recipient_email}}",
         "query": "{{job.body.user_input.search_keyword}}"
     }
     ```
  3. `validator.validate(...)`を実行
  4. 警告数を確認
- **期待結果**:
  - `len(result.warnings) == 2`（recipient_email, search_keyword）
  - 各警告の`location`が異なる（`job.body.user_input.recipient_email`, `job.body.user_input.search_keyword`）
  - 各警告の`warning_type == "USER_INPUT_FIELD_MISMATCH"`
- **pytestメソッド**: `test_tc_005_detects_multiple_mismatched_fields`

### TC-006: _build_multi_dependency_templateでフォールバック時に警告ログ
- **テスト観点**: AC-4の検証
- **関連する受入条件**: AC-4
- **関連する設計方針**: DP-2
- **テスト種別**: 単体テスト
- **テスト方法**: pytest + caplog
- **前提条件**:
  1. `_build_multi_dependency_template`の変更完了
- **テスト手順**:
  1. 存在しないフィールドへのフォールバックが発生する条件を設定
  2. `caplog.at_level(logging.WARNING)`でログをキャプチャ
  3. メソッドを実行
  4. ログ内容を確認
- **期待結果**:
  - `"Issue #408"` in `caplog.text`
  - `"not found in user_input_schema"` in `caplog.text`
  - `"Available fields"` in `caplog.text`
- **pytestメソッド**: `test_tc_006_fallback_warning_for_missing_field`

### TC-007: 警告がValidationResultに含まれる
- **テスト観点**: AC-5の検証
- **関連する受入条件**: AC-5
- **関連する設計方針**: DP-2
- **テスト種別**: 単体テスト
- **テスト方法**: pytest
- **前提条件**:
  1. 警告生成機能が実装済み
- **テスト手順**:
  1. 不整合を含むbody_templateで`validate()`を実行
  2. `result.warnings`の内容を確認
- **期待結果**:
  - `result.warnings`が空でない
  - 各警告が`BodyTemplateValidationWarning`インスタンス
  - `warning_type`, `message`, `location`が設定されている
- **pytestメソッド**: `test_tc_007_warnings_in_validation_result`

### TC-008: MasterManagerがuser_input_schemaをValidatorに渡す
- **テスト観点**: 結合テスト - データフロー検証
- **関連する受入条件**: AC-3
- **関連する設計方針**: DP-1
- **テスト種別**: 結合テスト
- **テスト方法**: pytest
- **前提条件**:
  1. MasterManagerの変更完了
  2. BodyTemplateValidatorの変更完了
- **テスト手順**:
  1. 複数タスクのinterfacesを用意（task_001にuser_inputフィールド定義）
  2. task_002以降でuser_inputの別名参照を含むbody_templateを設定
  3. `manager.create_masters()`を実行
  4. 警告が収集されることを確認
- **期待結果**:
  - 不整合フィールドに対する警告が生成される
- **pytestメソッド**: `test_tc_008_master_manager_passes_user_input_schema`

### TC-009: 環境変数BODY_TEMPLATE_STRICT_VALIDATIONの動作
- **テスト観点**: DP-4の検証
- **関連する受入条件**: AC-5
- **関連する設計方針**: DP-4
- **テスト種別**: 単体テスト
- **テスト方法**: pytest + monkeypatch
- **前提条件**:
  1. 環境変数による制御が実装済み
- **テスト手順**:
  1. `BODY_TEMPLATE_STRICT_VALIDATION=false`で警告のみを確認
  2. `BODY_TEMPLATE_STRICT_VALIDATION=true`でエラー化を確認
- **期待結果**:
  - **false時**:
    - `result.warnings`に警告が含まれる
    - `result.is_valid == True`（または処理続行可能）
    - 例外が発生しない
  - **true時**:
    - `ValidationError`が発生する、または`result.is_valid == False`
    - エラーメッセージに`USER_INPUT_FIELD_MISMATCH`が含まれる
    - WARNINGログも同時に出力される
- **追加検証ポイント**:
  - 環境変数未設定時はデフォルト（false）として動作する
  - 環境変数の大文字小文字（`true`/`True`/`TRUE`）を正しく処理する
- **pytestメソッド**: `test_tc_009_strict_validation_env_var`

### TC-010: E2Eテストでメール送信成功
- **テスト観点**: AC-6の検証
- **関連する受入条件**: AC-6
- **テスト種別**: E2E
- **テスト方法**: シェルスクリプト
- **前提条件**:
  1. AC-1〜AC-5の実装完了
  2. サービス起動済み（`./scripts/dev-hybrid.sh start --local-only`）
  3. 環境変数設定済み
- **テスト手順**:
  1. `./scripts/e2e/cross-service/test_full_workflow_e2e.sh`を3回実行
  2. 各実行結果を記録
  3. メール送信タスクの成功を確認
- **期待結果**:
  - 3回中3回成功
  - メール送信タスクが正常完了
- **実行コマンド**:
  ```bash
  for i in 1 2 3; do
      echo "=== Run $i ==="
      ./scripts/e2e/cross-service/test_full_workflow_e2e.sh \
          --keyword "テストキーワード" \
          --email "test@example.com"
      echo "Result: $?"
  done
  ```
- **pytestメソッド**: N/A（手動/シェル実行）

### TC-011: デッドコード検証 - _validate_user_input_fields
- **テスト観点**: F-1のデッドコード検証
- **テスト種別**: コード確認 + E2E
- **テスト方法**: grep + API呼び出し
- **テスト手順**:
  1. grepで呼び出し箇所を確認
  2. E2Eで警告が出力されることを確認
- **期待結果**:
  - validate()から呼び出されている
  - E2Eで警告ログが出力される
- **確認コマンド**:
  ```bash
  grep -rn "_validate_user_input_fields" expertAgent/ --include="*.py" | grep -v "def _validate_user_input_fields"
  ```
- **pytestメソッド**: `test_tc_011_validate_user_input_fields_not_dead_code`

---

## 10. テスト実行計画

### 実行前チェックリスト

テスト実行前に以下を確認すること：

```bash
# 1. 実装ファイルの存在確認
ls expertAgent/aiagent/langgraph/jobGeneratorV2/validators/body_template_validator.py

# 2. 新規メソッドの実装確認
grep -n "_validate_user_input_fields" expertAgent/aiagent/langgraph/jobGeneratorV2/validators/body_template_validator.py

# 3. プロンプトファイルの更新確認
grep -A 5 "フィールド名" expertAgent/prompts/interface_schema/default.yaml

# 4. テストファイルの存在確認
ls expertAgent/tests/unit/langgraph/jobGeneratorV2/validators/test_issue_408_user_input_validation.py
ls expertAgent/tests/acceptance/test_issue_408_acceptance.py

# 5. 環境変数設定確認（E2Eテスト用）
echo "MYVAULT_ENABLED: ${MYVAULT_ENABLED:-not set}"
echo "MYVAULT_BASE_URL: ${MYVAULT_BASE_URL:-not set}"
```

**チェック結果**:
- [ ] 実装ファイルが存在する
- [ ] `_validate_user_input_fields`メソッドが実装されている
- [ ] プロンプトにフィールド名保持ルールが追加されている
- [ ] テストファイルが存在する
- [ ] 環境変数が設定されている（E2Eテスト時）

### 実行順序

1. **単体テスト実行**
   ```bash
   uv run pytest expertAgent/tests/unit/langgraph/jobGeneratorV2/validators/test_issue_408_user_input_validation.py -v
   ```

2. **結合テスト実行**
   ```bash
   uv run pytest expertAgent/tests/integration/langgraph/jobGeneratorV2/test_issue_408_integration.py -v
   ```

3. **サービス起動確認**
   ```bash
   ./scripts/dev-hybrid.sh start --local-only
   curl http://localhost:8004/health
   curl http://localhost:8006/health
   ```

4. **受入テスト実行**
   ```bash
   uv run pytest expertAgent/tests/acceptance/test_issue_408_acceptance.py -v -s
   ```

5. **E2Eテスト実行（3回）**
   ```bash
   for i in 1 2 3; do
       ./scripts/e2e/cross-service/test_full_workflow_e2e.sh \
           --keyword "テスト" --email "test@example.com"
   done
   ```

### 成功基準

- [ ] TC-001〜TC-009: すべてのpytestテストがパス
- [ ] TC-010: E2Eテスト3回中3回成功
- [ ] TC-011: デッドコードが検出されない
- [ ] すべての受入条件（AC-1〜AC-6）が検証済み
- [ ] 設計方針との整合性が確認済み（DP-1〜DP-4）

---

## 11. 補足事項

### 注意事項
- E2Eテストは実際のLLMを呼び出すため、LLMの非決定性により結果が変動する可能性がある
- プロンプト強化の効果は複数回の実行で確認が必要
- 警告が出た場合でも、機能は動作を継続する設計のため、E2Eテストは最終的に成功すべき

### 関連Issue
- Issue #407: SYSTEM_INJECTED_FIELDSの前方一致チェック対応（前提条件）
- Issue #403: 複数タスクからのデータ集約サポート

### レビュー結果
本計画は2026-01-26のアーキテクチャレビューで承認された設計方針に基づいて作成。
設計評価: ⭐⭐⭐⭐⭐（5/5） - 承認済み

### 更新履歴
| 日付 | 更新内容 |
|------|---------|
| 2026-01-26 | 初版作成 |
| 2026-01-26 | レビュー改善提案を反映（Section 2, TC-005, TC-009, CI-2, Section 10）|

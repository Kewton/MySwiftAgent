# 受入テスト計画書

**Issue**: #358
**作成日**: 2026-01-13
**作成者**: acceptance-plan-agent
**フェーズ**: PRE-TDD（単体テスト結果は実装後に追加予定）

---

## 1. 概要

### 対象Issue
- **番号**: #358
- **タイトル**: feat(jobGeneratorV2): ジョブ生成時のbody_template整合性バリデーション追加
- **プロジェクト**: expertAgent

### 目的
Job Generator V2のREGISTRATIONフェーズにおいて、TaskMasterの`body_template`に含まれるテンプレート変数（`{{job.body}}`、`{{tasks[N].output_data}}`など）の整合性を事前検証する機能を追加し、実行時エラーを防止する。

### 参照ドキュメント
- Issue: #358
- 設計方針書: `dev-reports/feature/issue/358/design-policy.md`
- 作業計画書: `dev-reports/feature/issue/358/work-plan.md`

---

## 2. 単体テスト結果レビュー

**ステータス**: TDD実装前のため、実装後に更新予定

### カバレッジ（実装後に記入）
- 現在: --%
- 目標: 90%
- 判定: 未実施

### テスト品質評価（実装後に記入）
| 指標 | 値 | 判定 |
|------|-----|------|
| 総テスト数 | - | - |
| モック使用テスト数 | - | - |
| モック使用率 | --% | - |
| 実API呼び出しテスト数 | - | - |

### 期待される単体テストファイル
以下のテストファイルが実装されることを期待：

1. `expertAgent/tests/unit/validators/test_body_template_validator.py`
   - BodyTemplateValidatorクラスの正常系・異常系テスト
   - 各種エラーパターンのテスト

2. `expertAgent/tests/unit/validators/test_template_variable_extractor.py`
   - テンプレート変数抽出のテスト
   - 複雑なネスト構造のテスト

3. `expertAgent/tests/unit/validators/test_schema_comparator.py`
   - スキーマ比較ロジックのテスト

---

## 3. 受入条件分析

### AC-1: BodyTemplateValidatorクラスの実装
- **原文**: BodyTemplateValidatorクラスの実装
- **分類**: 機能要件
- **テスト方法**: pytest E2E
- **モック使用**: 不可（実際のバリデーション動作を確認）
- **検証ポイント**:
  1. BodyTemplateValidatorクラスが存在し、インスタンス化可能
  2. validate()メソッドが正しく動作
  3. ValidationResult型を返却

### AC-2: テンプレート変数の抽出機能
- **原文**: テンプレート変数の抽出機能（`{{...}}`パターン）
- **分類**: 機能要件
- **テスト方法**: pytest / curl
- **モック使用**: 不可
- **検証ポイント**:
  1. `{{job.body}}`パターンの正確な抽出
  2. `{{tasks[N].output_data}}`パターンの正確な抽出
  3. `{{job.project}}`パターンの正確な抽出
  4. ネストした構造からの再帰的抽出

### AC-3: job.body参照の検証
- **原文**: job.body参照の検証（input_schemaとの照合）
- **分類**: 機能要件
- **テスト方法**: pytest E2E
- **モック使用**: 不可
- **検証ポイント**:
  1. `{{job.body.user_input}}`がinput_schemaに存在する場合は検証パス
  2. 存在しないフィールド参照時にエラーを返す
  3. 類似フィールドのサジェスション機能

### AC-4: tasks[N].output_data参照の検証
- **原文**: tasks[N].output_data参照の検証（タスク順序・output_schemaとの照合）
- **分類**: 機能要件
- **テスト方法**: pytest E2E
- **モック使用**: 不可
- **検証ポイント**:
  1. 存在するタスクインデックス参照は検証パス
  2. 未来のタスク参照（現在task[1]から`{{tasks[2].output_data}}`参照）でエラー
  3. 存在しないタスクインデックス参照でエラー
  4. 出力スキーマとの整合性確認

### AC-5: 検証結果のレポート生成
- **原文**: 検証結果のレポート生成（エラー/警告/必須パラメータ）
- **分類**: 機能要件
- **テスト方法**: pytest / curl
- **モック使用**: 不可
- **検証ポイント**:
  1. ValidationResultにerrors配列が含まれる
  2. ValidationResultにwarnings配列が含まれる
  3. ValidationResultにrequired_job_body_fields配列が含まれる
  4. 各エラー/警告にfield_path, message, suggestionが含まれる

### AC-6: REGISTRATIONフェーズへの統合
- **原文**: REGISTRATIONフェーズへの統合（TaskMaster作成前にバリデーション実行）
- **分類**: 機能要件
- **テスト方法**: pytest E2E / curl
- **モック使用**: 不可（実際のワークフロー実行で確認）
- **検証ポイント**:
  1. ジョブ生成APIを呼び出すとバリデーションが実行される
  2. バリデーションエラー時はTaskMasterが作成されない
  3. 既存のジョブ生成フローが正常に動作する

### AC-7: エラー時の明確なメッセージで生成中止
- **原文**: エラー時は明確なメッセージで生成中止
- **分類**: 機能要件
- **テスト方法**: curl / pytest E2E
- **モック使用**: 不可
- **検証ポイント**:
  1. エラー時にHTTP 400/422ステータスを返却
  2. エラーレスポンスに具体的な問題箇所が記載される
  3. エラーレスポンスに修正サジェスションが含まれる

### AC-8: 警告時はログ出力して続行
- **原文**: 警告時はログ出力して続行
- **分類**: 機能要件
- **テスト方法**: pytest E2E（ログ確認）
- **モック使用**: 一部可（ログ出力の確認にのみ）
- **検証ポイント**:
  1. 警告レベルの問題でもジョブ生成は成功する
  2. 警告メッセージがログに出力される
  3. レスポンスにwarnings情報が含まれる（オプション）

### AC-9: JobMasterへの必須パラメータ情報付与
- **原文**: JobMasterへの必須パラメータ情報付与
- **分類**: 機能要件
- **テスト方法**: curl / pytest E2E
- **モック使用**: 不可
- **検証ポイント**:
  1. 生成されたジョブのメタデータに必須フィールド情報が含まれる
  2. `{{job.body.xxx}}`から抽出された必須フィールドが正しい

### AC-10: JobQueue APIで必須パラメータ情報を返却
- **原文**: JobQueue APIで必須パラメータ情報を返却
- **分類**: 機能要件
- **テスト方法**: curl / pytest E2E
- **モック使用**: 不可（実際のJobQueue APIを使用）
- **検証ポイント**:
  1. JobQueue APIのジョブ詳細取得で必須フィールド情報が返却される
  2. 必須フィールドのJSON Schema情報が含まれる

---

## 4. 設計方針検証

### DP-1: Strategy Patternによるエンジン別検証
- **設計方針**: Strategy Patternによるエンジン別検証ルール分離（design-policy.md 4.1.2）
- **検証方法**: コード構造確認 + E2Eテスト
- **テスト項目**:
  1. TaskFlowValidationStrategyが存在し動作する
  2. GraphAIValidationStrategyが存在し動作する
  3. engine="taskflow"指定時にTaskFlowStrategyが使用される
  4. engine="graphai"指定時にGraphAIStrategyが使用される

### DP-2: Result型パターンによるエラー情報伝達
- **設計方針**: Result型パターンによる詳細エラー情報伝達（design-policy.md 技術選定）
- **検証方法**: APIレスポンス確認
- **テスト項目**:
  1. ValidationResultにis_valid, errors, warnings, required_job_body_fieldsが含まれる
  2. 複数エラーが同時に検出可能
  3. エラー情報にerror_type, field_path, message, suggestionが含まれる

### DP-3: 既存フローへの影響最小化
- **設計方針**: 既存のジョブ生成フローへの影響最小化（design-policy.md 8.1）
- **検証方法**: 既存テストの実行 + 手動確認
- **テスト項目**:
  1. バリデーション機能追加後も既存のジョブ生成が正常に動作する
  2. パフォーマンス劣化が5%以内
  3. 既存のエラーハンドリングが維持される

### DP-4: テンプレートインジェクション対策
- **設計方針**: テンプレート変数の評価は行わず、構文解析のみ実施（design-policy.md 6.1）
- **検証方法**: セキュリティテスト
- **テスト項目**:
  1. 悪意のあるテンプレート（コード実行試行）が安全に処理される
  2. 再帰的なテンプレート参照が検出される
  3. 最大再帰深度の制限が機能する

---

## 5. デッドコード検証計画

実装後に以下の機能が実際に使用されているか確認する。

### F-1: BodyTemplateValidator.validate()
- **ファイル**: `validators/body_template_validator.py`
- **種別**: class method
- **期待される呼び出し元**: MasterManagerSubWorkflow.create_masters()
- **検証方法**:
  ```bash
  grep -rn "BodyTemplateValidator" --include="*.py" expertAgent/
  grep -rn "\.validate(" --include="*.py" expertAgent/aiagent/langgraph/jobGeneratorV2/
  ```
- **E2E確認**: ジョブ生成APIを叩いてバリデーションが実行されることを確認

### F-2: extract_template_variables()
- **ファイル**: `validators/template_variable_extractor.py`
- **種別**: function
- **期待される呼び出し元**: BodyTemplateValidator
- **検証方法**:
  ```bash
  grep -rn "extract_template_variables" --include="*.py" expertAgent/
  ```
- **E2E確認**: 抽出された変数がバリデーション結果に反映される

### F-3: ValidationStrategy implementations
- **ファイル**: `validators/body_template_validator.py`
- **種別**: class
- **期待される呼び出し元**: BodyTemplateValidator
- **検証方法**:
  ```bash
  grep -rn "TaskFlowValidationStrategy\|GraphAIValidationStrategy" --include="*.py" expertAgent/
  ```
- **E2E確認**: engine指定に応じた適切なStrategyが使用される

### F-4: ValidationError / ValidationWarning / RequiredField
- **ファイル**: `validators/body_template_validator.py`
- **種別**: dataclass
- **期待される呼び出し元**: ValidationResult作成時
- **検証方法**:
  ```bash
  grep -rn "ValidationError\|ValidationWarning\|RequiredField" --include="*.py" expertAgent/
  ```
- **E2E確認**: エラー/警告レスポンスに正しい構造が含まれる

### F-5: compare_schemas()
- **ファイル**: `validators/schema_comparator.py`
- **種別**: function
- **期待される呼び出し元**: validate_task_references()
- **検証方法**:
  ```bash
  grep -rn "compare_schemas" --include="*.py" expertAgent/
  ```
- **E2E確認**: スキーマ不一致時に適切な警告/エラーが生成される

---

## 6. テスト環境

### 必須サービス
| サービス | URL | ヘルスチェック |
|---------|-----|--------------|
| expertAgent | http://localhost:8104 | GET /health |
| JobQueue | http://localhost:8001 | GET /health |
| myVault | http://localhost:8103 | GET /health |

### 起動コマンド
```bash
# 推奨: ハイブリッドモード（Agent層開発用）
./scripts/dev-hybrid.sh

# または: Docker全環境
make dev-all
```

### 環境変数
| 変数名 | 説明 | 必須 |
|--------|------|------|
| OPENAI_API_KEY | OpenAI APIキー（LLM呼び出し用） | 任意（Job Generator使用時） |
| ANTHROPIC_API_KEY | Anthropic APIキー | 任意 |

### テストデータ
- 有効なbody_templateサンプル（正常系確認用）
- 無効なtask参照を含むテンプレート（異常系確認用）
- スキーマ不一致を含むワークフロー定義（警告確認用）

---

## 7. テスト項目

### TC-001: 有効なbody_templateでのジョブ生成成功
- **テスト観点**: 正常系 - バリデーションを通過するbody_templateでジョブが生成される
- **関連する受入条件**: AC-1, AC-6
- **関連する設計方針**: DP-3
- **テスト種別**: E2E
- **テスト方法**: curl / pytest
- **前提条件**:
  1. expertAgentサービスが起動している
  2. JobQueueサービスが起動している
- **テスト手順**:
  1. ジョブ生成APIにリクエストを送信
  2. レスポンスを確認
  3. JobQueueにジョブが登録されていることを確認
- **期待結果**:
  - HTTPステータス: 200
  - レスポンス: `job_id`が含まれる
  - ジョブが正常に生成される
- **curlコマンド**:
  ```bash
  curl -s -X POST http://localhost:8104/aiagent-api/v1/job/generate \
    -H "Content-Type: application/json" \
    -d '{
      "requirement": "ファイルの内容を読み取ってサマリーを生成",
      "engine": "taskflow",
      "project_id": "test-project"
    }'
  ```
- **pytestメソッド**: `test_tc_001_valid_template_job_generation`

### TC-002: テンプレート変数の正確な抽出
- **テスト観点**: `{{job.body}}`、`{{tasks[N].output_data}}`、`{{job.project}}`パターンの抽出
- **関連する受入条件**: AC-2
- **関連する設計方針**: DP-2
- **テスト種別**: E2E / 結合
- **テスト方法**: pytest
- **前提条件**:
  1. テスト対象のbody_templateが準備されている
- **テスト手順**:
  1. 複数パターンを含むbody_templateを作成
  2. バリデーションを実行
  3. 抽出された変数一覧を確認
- **期待結果**:
  - すべてのテンプレート変数が正確に抽出される
  - 抽出結果にfield_path情報が含まれる
- **pytestメソッド**: `test_tc_002_template_variable_extraction`

### TC-003: job.body参照の検証（正常系）
- **テスト観点**: input_schemaに存在するフィールドへの参照がパスする
- **関連する受入条件**: AC-3
- **関連する設計方針**: DP-2
- **テスト種別**: E2E
- **テスト方法**: pytest
- **前提条件**:
  1. 有効なinput_schemaが定義されている
- **テスト手順**:
  1. `{{job.body.user_input}}`を含むテンプレートを検証
  2. input_schemaに"user_input"フィールドが存在
- **期待結果**:
  - is_valid: true
  - errors: []
- **pytestメソッド**: `test_tc_003_job_body_reference_valid`

### TC-004: job.body参照の検証（異常系）
- **テスト観点**: 存在しないフィールド参照時にエラーを返す
- **関連する受入条件**: AC-3, AC-7
- **関連する設計方針**: DP-2
- **テスト種別**: E2E
- **テスト方法**: pytest
- **前提条件**:
  1. input_schemaに該当フィールドが存在しない
- **テスト手順**:
  1. `{{job.body.nonexistent_field}}`を含むテンプレートを検証
  2. 検証結果を確認
- **期待結果**:
  - is_valid: false
  - errors: SCHEMA_MISMATCHエラーを含む
  - suggestion: 類似フィールド候補
- **pytestメソッド**: `test_tc_004_job_body_reference_invalid`

### TC-005: tasks[N]参照の検証（正常系）
- **テスト観点**: 有効なタスクインデックス参照がパスする
- **関連する受入条件**: AC-4
- **関連する設計方針**: DP-2
- **テスト種別**: E2E
- **テスト方法**: pytest
- **前提条件**:
  1. 2タスク以上のワークフローが定義されている
- **テスト手順**:
  1. task[1]のbody_templateに`{{tasks[0].output_data}}`を設定
  2. バリデーションを実行
- **期待結果**:
  - is_valid: true
  - errors: []
- **pytestメソッド**: `test_tc_005_task_reference_valid`

### TC-006: tasks[N]参照の検証（未来タスク参照エラー）
- **テスト観点**: 未来のタスクを参照した場合にエラーを返す
- **関連する受入条件**: AC-4, AC-7
- **関連する設計方針**: DP-2
- **テスト種別**: E2E
- **テスト方法**: pytest
- **前提条件**:
  1. 複数タスクのワークフローが定義されている
- **テスト手順**:
  1. task[0]のbody_templateに`{{tasks[1].output_data}}`を設定
  2. バリデーションを実行
- **期待結果**:
  - is_valid: false
  - errors: INVALID_INDEXエラー（"Cannot reference future task"）
- **pytestメソッド**: `test_tc_006_task_reference_future_task_error`

### TC-007: tasks[N]参照の検証（存在しないインデックスエラー）
- **テスト観点**: 存在しないタスクインデックスを参照した場合にエラー
- **関連する受入条件**: AC-4, AC-7
- **関連する設計方針**: DP-2
- **テスト種別**: E2E
- **テスト方法**: pytest
- **前提条件**:
  1. 2タスクのワークフローが定義されている
- **テスト手順**:
  1. `{{tasks[5].output_data}}`を含むテンプレートを検証（タスク数は2）
  2. 検証結果を確認
- **期待結果**:
  - is_valid: false
  - errors: INVALID_INDEXエラー（"out of range"）
- **pytestメソッド**: `test_tc_007_task_reference_out_of_range`

### TC-008: 検証結果レポートの構造確認
- **テスト観点**: ValidationResultの構造が設計通りである
- **関連する受入条件**: AC-5
- **関連する設計方針**: DP-2
- **テスト種別**: E2E
- **テスト方法**: pytest
- **前提条件**:
  1. 複数エラー・警告を含むテンプレートが準備されている
- **テスト手順**:
  1. 複合的な問題を含むテンプレートを検証
  2. ValidationResultの構造を確認
- **期待結果**:
  - is_valid: bool
  - errors: list[ValidationError]
  - warnings: list[ValidationWarning]
  - required_job_body_fields: list[RequiredField]
- **pytestメソッド**: `test_tc_008_validation_result_structure`

### TC-009: バリデーションエラー時のジョブ生成中止
- **テスト観点**: エラー検出時にジョブ生成が中止される
- **関連する受入条件**: AC-6, AC-7
- **関連する設計方針**: DP-3
- **テスト種別**: E2E
- **テスト方法**: curl / pytest
- **前提条件**:
  1. 不正なbody_templateを生成するリクエストが可能
- **テスト手順**:
  1. 不正なテンプレート参照を含むリクエストを送信
  2. レスポンスを確認
  3. JobQueueにジョブが登録されていないことを確認
- **期待結果**:
  - HTTPステータス: 400 or 422
  - エラーメッセージに具体的な問題箇所が記載
  - JobQueueにジョブが存在しない
- **curlコマンド**:
  ```bash
  # 不正なリクエスト例（実装により調整）
  curl -s -X POST http://localhost:8104/aiagent-api/v1/job/generate \
    -H "Content-Type: application/json" \
    -d '{
      "requirement": "invalid workflow with bad references",
      "engine": "taskflow",
      "test_mode": "force_invalid_reference"
    }'
  ```
- **pytestメソッド**: `test_tc_009_validation_error_stops_generation`

### TC-010: 警告時のジョブ生成続行
- **テスト観点**: 警告レベルの問題ではジョブ生成が続行される
- **関連する受入条件**: AC-8
- **関連する設計方針**: DP-3
- **テスト種別**: E2E
- **テスト方法**: pytest（ログ確認含む）
- **前提条件**:
  1. 警告レベルの問題を含むワークフローが定義可能
- **テスト手順**:
  1. スキーマ不一致（警告レベル）を含むリクエストを送信
  2. レスポンスを確認
  3. ログに警告メッセージが出力されていることを確認
- **期待結果**:
  - HTTPステータス: 200
  - job_idが返却される
  - ログに警告メッセージが出力される
- **pytestメソッド**: `test_tc_010_warning_allows_continuation`

### TC-011: 必須パラメータ情報の抽出
- **テスト観点**: job.body参照から必須フィールドが正しく抽出される
- **関連する受入条件**: AC-9
- **関連する設計方針**: DP-2
- **テスト種別**: E2E
- **テスト方法**: pytest
- **前提条件**:
  1. `{{job.body.xxx}}`参照を含むテンプレートが定義されている
- **テスト手順**:
  1. バリデーションを実行
  2. required_job_body_fieldsを確認
- **期待結果**:
  - required_job_body_fieldsに正しいフィールドパスが含まれる
  - 各フィールドにjson_schema情報が含まれる
- **pytestメソッド**: `test_tc_011_required_field_extraction`

### TC-012: JobQueue APIでの必須パラメータ返却
- **テスト観点**: 生成されたジョブの必須パラメータ情報がJobQueue APIで取得可能
- **関連する受入条件**: AC-10
- **関連する設計方針**: DP-2
- **テスト種別**: E2E
- **テスト方法**: curl / pytest
- **前提条件**:
  1. ジョブが正常に生成されている
  2. JobQueueサービスが起動している
- **テスト手順**:
  1. ジョブを生成
  2. JobQueue APIでジョブ詳細を取得
  3. 必須パラメータ情報を確認
- **期待結果**:
  - ジョブ詳細にrequired_body_fieldsが含まれる
- **curlコマンド**:
  ```bash
  # ジョブ生成
  JOB_ID=$(curl -s -X POST http://localhost:8104/aiagent-api/v1/job/generate \
    -H "Content-Type: application/json" \
    -d '{"requirement": "test", "engine": "taskflow"}' | jq -r '.job_id')

  # ジョブ詳細取得
  curl -s http://localhost:8001/jobs/${JOB_ID} | jq '.required_body_fields'
  ```
- **pytestメソッド**: `test_tc_012_jobqueue_api_required_fields`

### TC-013: TaskFlowエンジンでの検証動作
- **テスト観点**: engine="taskflow"指定時に適切なStrategyが使用される
- **関連する受入条件**: AC-1
- **関連する設計方針**: DP-1
- **テスト種別**: E2E
- **テスト方法**: pytest
- **前提条件**:
  1. TaskFlowValidationStrategyが実装されている
- **テスト手順**:
  1. engine="taskflow"でバリデーションを実行
  2. TaskFlow固有の検証ルールが適用されることを確認
- **期待結果**:
  - TaskFlowValidationStrategyが使用される
  - TaskFlow固有のbody_template構造が検証される
- **pytestメソッド**: `test_tc_013_taskflow_engine_validation`

### TC-014: GraphAIエンジンでの検証動作
- **テスト観点**: engine="graphai"指定時に適切なStrategyが使用される
- **関連する受入条件**: AC-1
- **関連する設計方針**: DP-1
- **テスト種別**: E2E
- **テスト方法**: pytest
- **前提条件**:
  1. GraphAIValidationStrategyが実装されている
- **テスト手順**:
  1. engine="graphai"でバリデーションを実行
  2. GraphAI固有の検証ルールが適用されることを確認
- **期待結果**:
  - GraphAIValidationStrategyが使用される
  - GraphAI固有のbody_template構造が検証される
- **pytestメソッド**: `test_tc_014_graphai_engine_validation`

### TC-015: 既存ジョブ生成フローの互換性確認
- **テスト観点**: バリデーション機能追加後も既存のジョブ生成が正常動作
- **関連する受入条件**: 技術要件（既存フローへの影響最小化）
- **関連する設計方針**: DP-3
- **テスト種別**: E2E
- **テスト方法**: 既存テスト実行 + 手動確認
- **前提条件**:
  1. 既存のジョブ生成テストが存在する
- **テスト手順**:
  1. 既存のジョブ生成テストを実行
  2. すべてパスすることを確認
- **期待結果**:
  - 既存テストがすべてパス
  - パフォーマンス劣化5%以内
- **pytestメソッド**: `test_tc_015_backward_compatibility`

### TC-016: テンプレートインジェクション対策
- **テスト観点**: 悪意のあるテンプレートが安全に処理される
- **関連する受入条件**: 技術要件（セキュリティ）
- **関連する設計方針**: DP-4
- **テスト種別**: セキュリティ
- **テスト方法**: pytest
- **前提条件**:
  1. 悪意のあるテンプレートサンプルが準備されている
- **テスト手順**:
  1. コード実行を試みるテンプレートを検証
  2. 再帰的なテンプレート参照を検証
- **期待結果**:
  - コード実行されない
  - 再帰参照が検出される
  - 適切なエラーメッセージが返却される
- **pytestメソッド**: `test_tc_016_template_injection_prevention`

---

## 8. テスト実行計画

### 実行順序
1. **サービス起動確認（ヘルスチェック）**
   ```bash
   curl -sf http://localhost:8104/health && echo "expertAgent OK"
   curl -sf http://localhost:8001/health && echo "JobQueue OK"
   curl -sf http://localhost:8103/health && echo "myVault OK"
   ```

2. **pytest受入テスト実行**
   ```bash
   cd /Users/maenokota/share/work/github_kewton/MySwiftAgent/expertAgent
   uv run pytest tests/acceptance/test_issue_358_acceptance.py -v
   ```

3. **curlによる手動確認**（pytest失敗時のデバッグ用）

### 成功基準
- [ ] すべてのpytestテストがパス（TC-001〜TC-016）
- [ ] すべての受入条件が検証済み（AC-1〜AC-10）
- [ ] すべての設計方針が検証済み（DP-1〜DP-4）
- [ ] デッドコードが検出されないこと（F-1〜F-5）
- [ ] 既存テストへの影響なし
- [ ] パフォーマンス劣化5%以内

---

## 9. 補足事項

### TDD実装後の更新事項

TDD実装完了後、以下のセクションを更新する：

1. **セクション2: 単体テスト結果レビュー**
   - カバレッジ値の記入
   - テスト品質評価の記入
   - モック使用率の確認

2. **デッドコード検証結果**
   - 実際のコード検索結果を追記
   - 統合確認結果を記録

### 受入テストファイル

実装する受入テストファイル:
- `expertAgent/tests/acceptance/test_issue_358_acceptance.py`

### 注意事項

- 本計画はPRE-TDDフェーズで作成されており、実装詳細は変更される可能性がある
- テストケースの一部は実装方針により調整が必要
- テスト用の強制エラー発生機構（`test_mode`パラメータ等）は実装時に確定

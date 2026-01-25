# 受入テスト計画書

**Issue**: #403
**作成日**: 2026-01-25
**作成者**: acceptance-plan-agent

---

## 1. 概要

### 対象Issue
- **番号**: #403
- **タイトル**: feat(expertAgent): body_template生成でinterfaceDefinitionsを考慮した複数タスクからのデータ集約
- **プロジェクト**: expertAgent

### 参照ドキュメント
- Issue: #403
- 設計方針書: `dev-reports/feature/issue/403/design-policy.md`
- 関連Issue: #401, #402, #342, #358

### 機能概要
`master_manager.py`の`_build_body_template`メソッドを拡張し、interfaceDefinitionsで定義された入力要件を解析して、複数の依存タスクからデータを集約するbody_templateを生成する。

---

## 2. 単体テスト結果レビュー

### 現状確認
- **実装状態**: 未実装（`_find_field_source`メソッドが存在しない）
- **既存テスト**: master_manager関連24件パス
- **失敗テスト**: 12件（別Issue関連の可能性）

### 予定カバレッジ目標
- 現在: N/A（未実装）
- 目標: 90%以上

### 単体テストでカバーすべき項目
1. `_find_field_source`の正常系テスト
2. `_find_field_source`の異常系テスト（フィールド未発見）
3. `_build_body_template`の複数依存タスクテスト
4. 後方互換性テスト（オプション引数省略時）
5. フォールバックテスト（user_inputへの切り替え）
6. ログ出力テスト（WARNING, DEBUG, INFO）
7. 検証ロジックテスト（`validate_multi_field_references`）

---

## 3. 受入条件分析

### AC-1: interfaceDefinitionsの入力要件を解析して必要なフィールドを特定する
- **原文**: interfaceDefinitionsの入力要件を解析して必要なフィールドを特定する
- **分類**: 機能要件
- **テスト方法**: pytest
- **モック使用**: 一部可（外部APIのみ）
- **検証ポイント**:
  1. `InterfaceSchema.input_schema`の`properties`キーからフィールドリストを抽出できる
  2. 空のproperties / 存在しないschemaを適切にハンドリングする

### AC-2: 各フィールドの取得元タスクをdependenciesから決定する
- **原文**: 各フィールドの取得元タスクを`dependencies`から決定する
- **分類**: 機能要件
- **テスト方法**: pytest
- **モック使用**: 不可（ロジックテスト）
- **検証ポイント**:
  1. 依存タスクリストの順序で探索し、最初にフィールドを出力するタスクを選択
  2. 複数タスクが同じフィールドを出力する場合、依存順序で最初のタスクを優先

### AC-3: 複数タスクからのデータを集約するbody_templateを生成する
- **原文**: 複数タスクからのデータを集約するbody_templateを生成する
- **分類**: 機能要件
- **テスト方法**: pytest + E2E curl
- **モック使用**: 不可（実際のテンプレート生成）
- **検証ポイント**:
  1. `inputs`が辞書形式で複数の`{{tasks[N].output_data.field}}`参照を含む
  2. 各フィールドが正しい依存タスクのorderを参照する

### AC-4: task_006のbody_templateが{keyword, summary, recipient_email}を正しく参照する
- **原文**: task_006のbody_templateが`{keyword, summary, recipient_email}`を正しく参照する
- **分類**: 機能要件（E2Eシナリオ）
- **テスト方法**: E2E pytest
- **モック使用**: 不可
- **検証ポイント**:
  1. `keyword`: task_001（order=0）から取得
  2. `summary`: task_005（order=4）から取得
  3. `recipient_email`: task_005（order=4）から取得

### AC-5: 既存の単一依存タスクでも正しく動作する（後方互換性）
- **原文**: 既存の単一依存タスクでも正しく動作する（後方互換性）
- **分類**: 非機能要件（後方互換性）
- **テスト方法**: pytest
- **モック使用**: 不可
- **検証ポイント**:
  1. オプション引数（task, interfaces, task_order_map）をNoneで呼び出した場合、従来動作
  2. 単一依存タスクでは`{{tasks[order-1].output_data}}`形式を維持

### AC-6: 依存タスクの出力にフィールドが存在しない場合、user_inputからフォールバック取得する
- **原文**: 依存タスクの出力にフィールドが存在しない場合、user_inputからフォールバック取得する
- **分類**: エラーハンドリング
- **テスト方法**: pytest
- **モック使用**: 不可
- **検証ポイント**:
  1. フィールドが依存タスクに存在しない場合、`{{job.body.user_input.field}}`を生成
  2. WARNINGログが出力される

### AC-7: interfacesが存在しないタスクの場合、従来の動作にフォールバックする
- **原文**: interfacesが存在しないタスクの場合、従来の動作にフォールバックする
- **分類**: エラーハンドリング
- **テスト方法**: pytest
- **モック使用**: 不可
- **検証ポイント**:
  1. `interfaces`にタスクIDが存在しない場合、`{{tasks[order-1].output_data}}`形式を維持

### AC-8: 単体テスト - `_find_field_source`の正常系・異常系テスト
- **原文**: 単体テスト - `_find_field_source`の正常系・異常系テスト
- **分類**: テスト要件
- **テスト方法**: pytest
- **検証ポイント**:
  1. 単一依存でフィールド発見
  2. 複数依存で最初に見つかったタスクを選択
  3. フィールドが存在しない場合Noneを返却

### AC-9: 単体テスト - `_build_body_template`の複数依存タスクテスト
- **原文**: 単体テスト - `_build_body_template`の複数依存タスクテスト
- **分類**: テスト要件
- **テスト方法**: pytest
- **検証ポイント**:
  1. 複数依存タスクからのフィールド集約
  2. 生成されたテンプレートの形式検証

### AC-10: 結合テスト - 複数依存を持つワークフローのE2E登録テスト
- **原文**: 結合テスト - 複数依存を持つワークフローのE2E登録テスト
- **分類**: テスト要件（E2E）
- **テスト方法**: pytest + 実API呼び出し
- **検証ポイント**:
  1. Job Generator V2 APIで複数依存ワークフローを生成
  2. 生成されたTaskMasterのbody_templateが正しい形式

---

## 4. 設計方針検証

### DP-1: フィールド解決戦略（依存順序優先）
- **設計方針**: 依存タスクリストの順序で探索し、最初に見つかったタスクを使用
- **検証方法**: 単体テスト + ログ確認
- **テスト項目**:
  1. task_001(keyword)とtask_005(summary)から各フィールドを取得できる
  2. DEBUGログでフィールド解決の過程を確認可能

### DP-2: 後方互換性（オプション引数）
- **設計方針**: task, interfaces, task_order_mapはオプション引数として追加
- **検証方法**: 単体テスト
- **テスト項目**:
  1. オプション引数省略時は従来動作
  2. 既存テストが変更なしでパス

### DP-3: フォールバック+ログ出力
- **設計方針**: フォールバック時はWARNINGログを出力
- **検証方法**: 単体テスト + ログ検証
- **テスト項目**:
  1. フィールド未発見時にuser_inputへフォールバック
  2. WARNINGログが出力される

### DP-4: 検証ロジック（validate_multi_field_references）
- **設計方針**: BodyTemplateValidatorに複数フィールド参照の検証を追加
- **検証方法**: 単体テスト
- **テスト項目**:
  1. 参照先タスクの存在確認
  2. 参照先フィールドの存在確認
  3. DAG整合性（循環参照チェック）

---

## 5. デッドコード検証計画

### F-1: _find_field_source
- **ファイル**: `expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/registration/master_manager.py`
- **種別**: method
- **期待される呼び出し元**: `_build_body_template`メソッド
- **検証方法**:
  ```bash
  grep -rn "_find_field_source" expertAgent/ --include="*.py" | grep -v "def _find_field_source"
  ```
- **E2E確認**: Job Generator V2 APIで複数依存ワークフローを生成し、body_templateを検証

### F-2: validate_multi_field_references（実装予定）
- **ファイル**: `expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/registration/validators/body_template_validator.py`
- **種別**: method
- **期待される呼び出し元**: `TaskFlowValidationStrategy.validate`メソッド
- **検証方法**:
  ```bash
  grep -rn "validate_multi_field_references" expertAgent/ --include="*.py" | grep -v "def validate_multi_field_references"
  ```
- **E2E確認**: 不正なbody_templateで検証エラーが発生することを確認

### F-3: FieldResolutionError（実装予定）
- **ファイル**: `expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/registration/errors.py`（または適切な場所）
- **種別**: class
- **期待される呼び出し元**: `_find_field_source`メソッドまたはバリデータ
- **検証方法**:
  ```bash
  grep -rn "FieldResolutionError" expertAgent/ --include="*.py" | grep -v "class FieldResolutionError"
  ```
- **E2E確認**: エラーケースでFieldResolutionErrorが適切に発生することを確認

---

## 6. コンポーネント間整合性検証

### CI-1: InterfaceSchema整合性
- **検証対象**: `InterfaceSchema`の入力・出力スキーマ形式
- **検証方法**:
  ```bash
  grep -rn "InterfaceSchema\|input_schema\|output_schema" expertAgent/aiagent/langgraph/jobGeneratorV2/ --include="*.py"
  ```
- **確認項目**:
  - [ ] JobAnalyzerが生成するInterfaceSchemaと_find_field_sourceが期待する形式が一致
  - [ ] `properties`キーの存在と構造が一致

### CI-2: task_order_map整合性
- **検証対象**: `task_order_map`の構築と使用
- **検証方法**:
  - create_masters内での構築ロジック確認
  - _build_body_templateでの使用パターン確認
- **確認項目**:
  - [ ] トポロジカルソート後の順序がtask_order_mapに正しく反映
  - [ ] 参照時にキーが存在することを保証

### CI-3: body_templateフォーマット整合性
- **検証対象**: 新旧body_template形式の互換性
- **検証方法**:
  - 旧形式: `"inputs": "{{tasks[N].output_data}}"`（文字列）
  - 新形式: `"inputs": {"field": "{{tasks[N].output_data.field}}"}`（辞書）
- **確認項目**:
  - [ ] mySwiftAgentCoreが両形式を処理可能
  - [ ] BodyTemplateValidatorが両形式を検証可能

---

## 7. サービス間データフロー検証

### DF-1: データフロー完全性
| 送信元 | データ項目 | 送信先 | 取得方法 | 検証状態 |
|--------|-----------|--------|---------|---------|
| expertAgent | body_template.inputs | mySwiftAgentCore | TaskMaster API | ??? |
| expertAgent | interfaceDefinitions | create_masters | JobAnalyzer出力 | ??? |
| JobAnalyzer | output_schema | _find_field_source | InterfaceSchema | ??? |

### DF-2: 空配列/null検証
**チェック方法**:
```bash
# テストファイルでの空配列/null使用を検出
grep -rn "interfaces.*=.*{}" expertAgent/tests/
grep -rn "task_order_map.*=.*{}" expertAgent/tests/
grep -rn "dependencies.*=.*\[\]" expertAgent/tests/
```

**禁止パターン**:
- テストで`dependencies=[]`を正常ケースとして使用しない（フィールド解決が発生しないため）
- テストで`interfaces={}`を正常ケースとして使用しない（フォールバックパスのみテストになる）

### DF-3: テスト項目必須化
- [ ] **DF-TC-1**: 実際のinterfaceDefinitionsでフィールド解決が動作することを検証
- [ ] **DF-TC-2**: 複数の依存タスクから異なるフィールドを取得できることを検証
- [ ] **DF-TC-3**: フィールドが見つからない場合のフォールバック動作を検証

---

## 8. E2E統合テスト計画

### E2E-1: 複数依存ワークフロー登録E2Eテスト
- **テストファイル**: `expertAgent/tests/acceptance/test_issue_403_acceptance.py`
- **実行コマンド**:
  ```bash
  cd expertAgent && uv run pytest tests/acceptance/test_issue_403_acceptance.py -v -s
  ```
- **検証項目**:
  - [ ] Job Generator V2 APIで複数依存ワークフローを生成
  - [ ] task_006のbody_templateが`{keyword, summary, recipient_email}`を正しく参照
  - [ ] 生成されたTaskMasterがJobQueue APIに登録される

### E2E-2: フィールド解決の詳細検証
- **目的**: 設計方針（依存順序優先）が正しく動作することを検証
- **シナリオ**:
  ```
  task_001 (order=0): output={keyword: "AI"}
  task_004 (order=3): output={processed: true}
  task_005 (order=4): output={summary: "要約", recipient_email: "test@example.com"}
  task_006 (order=5): dependencies=[task_001, task_004, task_005], input={keyword, summary, recipient_email}
  ```
- **期待結果**:
  ```json
  {
    "workflow": "__PENDING__",
    "inputs": {
      "keyword": "{{tasks[0].output_data.keyword}}",
      "summary": "{{tasks[4].output_data.summary}}",
      "recipient_email": "{{tasks[4].output_data.recipient_email}}"
    },
    "project": "{{job.body.project}}"
  }
  ```

---

## 9. テスト環境

### 必須サービス
| サービス | URL | ヘルスチェック |
|---------|-----|--------------|
| expertAgent | http://localhost:8004 | GET /health |
| jobqueue | http://localhost:8001 | GET /health |
| myVault | http://localhost:8003 | GET /health |

### 起動コマンド（E2Eテスト用 - 必須）
```bash
# 1. 既存サービスを停止
./scripts/dev-hybrid.sh stop --local-only

# 2. ローカルモードでサービスを起動
./scripts/dev-hybrid.sh start --local-only
```

### シークレット・設定情報
E2Eテストで使用するシークレットは、コンテナ起動のmyVaultのdefault_projectから取得。

| 項目 | 取得元 |
|------|--------|
| OPENAI_API_KEY | myVault (default_project) |
| LLM_API_KEY | myVault (default_project) |

### 環境変数
| 変数名 | 説明 | 必須 |
|--------|------|------|
| MYVAULT_ENABLED | MyVault有効化フラグ | ✅ (true) |
| MYVAULT_BASE_URL | MyVault URL | ✅ (http://localhost:8003) |
| JOBQUEUE_BASE_URL | JobQueue URL | ✅ (http://localhost:8001) |

---

## 10. テスト項目

### TC-001: _find_field_source単一依存テスト
- **テスト観点**: 単一依存タスクからフィールドを正しく解決できる
- **関連する受入条件**: AC-2
- **関連する設計方針**: DP-1
- **テスト種別**: 単体テスト
- **テスト方法**: pytest
- **前提条件**:
  1. MasterManagerSubWorkflowインスタンス生成
  2. テスト用InterfaceSchema準備
- **テスト手順**:
  1. 単一依存タスクとインターフェースを準備
  2. `_find_field_source`を呼び出し
  3. 戻り値を検証
- **期待結果**:
  - 正しい依存タスクIDが返却される
- **pytestメソッド**: `test_find_field_source_single_dependency`

### TC-002: _find_field_source複数依存テスト（依存順序優先）
- **テスト観点**: 複数の依存タスクが同じフィールドを出力する場合、依存順序で最初のタスクを優先
- **関連する受入条件**: AC-2
- **関連する設計方針**: DP-1
- **テスト種別**: 単体テスト
- **テスト方法**: pytest
- **前提条件**:
  1. 複数タスクが同じフィールドを出力するシナリオ
- **テスト手順**:
  1. task_001, task_003 両方が`keyword`を出力するインターフェース準備
  2. dependencies=[task_001, task_003]で`_find_field_source`呼び出し
  3. 戻り値を検証
- **期待結果**:
  - dependencies順序で最初のtask_001が返却される
- **pytestメソッド**: `test_find_field_source_multiple_deps_first_match`

### TC-003: _find_field_sourceフィールド未発見テスト
- **テスト観点**: フィールドが依存タスクに存在しない場合Noneを返却
- **関連する受入条件**: AC-6
- **関連する設計方針**: DP-3
- **テスト種別**: 単体テスト
- **テスト方法**: pytest
- **前提条件**:
  1. 依存タスクの出力に対象フィールドがない
- **テスト手順**:
  1. 対象フィールドを出力しないインターフェース準備
  2. `_find_field_source`呼び出し
  3. 戻り値を検証
- **期待結果**:
  - Noneが返却される
- **pytestメソッド**: `test_find_field_source_field_not_found`

### TC-004: _build_body_template複数依存集約テスト
- **テスト観点**: 複数タスクからデータを集約するbody_templateを生成
- **関連する受入条件**: AC-3, AC-4
- **関連する設計方針**: DP-1
- **テスト種別**: 単体テスト
- **テスト方法**: pytest
- **前提条件**:
  1. Issue本文のシナリオ準備（task_001, task_004, task_005, task_006）
- **テスト手順**:
  1. 複数依存のTaskDefinitionとInterfaceSchema準備
  2. `_build_body_template`呼び出し
  3. 生成されたテンプレートを検証
- **期待結果**:
  - `inputs`が辞書形式
  - `keyword`: `{{tasks[0].output_data.keyword}}`
  - `summary`: `{{tasks[4].output_data.summary}}`
  - `recipient_email`: `{{tasks[4].output_data.recipient_email}}`
- **pytestメソッド**: `test_build_body_template_multi_dependency_aggregation`

### TC-005: 後方互換性テスト
- **テスト観点**: オプション引数省略時に従来動作を維持
- **関連する受入条件**: AC-5, AC-7
- **関連する設計方針**: DP-2
- **テスト種別**: 単体テスト
- **テスト方法**: pytest
- **前提条件**:
  1. 既存の呼び出しパターン（引数orderのみ）
- **テスト手順**:
  1. `_build_body_template(order=1)`を呼び出し
  2. 生成されたテンプレートを検証
- **期待結果**:
  - `inputs`: `{{tasks[0].output_data}}`（文字列形式）
- **pytestメソッド**: `test_build_body_template_backward_compatibility`

### TC-006: フォールバック+警告ログテスト
- **テスト観点**: フィールド未発見時のuser_inputフォールバックと警告ログ出力
- **関連する受入条件**: AC-6
- **関連する設計方針**: DP-3
- **テスト種別**: 単体テスト
- **テスト方法**: pytest + caplog
- **前提条件**:
  1. 依存タスクに存在しないフィールドを要求
- **テスト手順**:
  1. 必須フィールドが依存タスクに存在しないシナリオ準備
  2. `_build_body_template`呼び出し
  3. テンプレートとログを検証
- **期待結果**:
  - `inputs.missing_field`: `{{job.body.user_input.missing_field}}`
  - WARNINGログが出力される
- **pytestメソッド**: `test_build_body_template_fallback_with_warning_log`

### TC-007: validate_multi_field_referencesテスト
- **テスト観点**: 複数フィールド参照の妥当性検証
- **関連する受入条件**: 設計方針検証
- **関連する設計方針**: DP-4
- **テスト種別**: 単体テスト
- **テスト方法**: pytest
- **前提条件**:
  1. 不正な参照を含むbody_template
- **テスト手順**:
  1. 存在しないタスクorderを参照するテンプレート準備
  2. `validate_multi_field_references`呼び出し
  3. 検証エラーを確認
- **期待結果**:
  - エラーリストに検出された問題が含まれる
- **pytestメソッド**: `test_validate_multi_field_references_invalid_order`

### TC-008: E2E複数依存ワークフロー登録テスト
- **テスト観点**: 実際のJob Generator V2 APIで複数依存ワークフローを生成
- **関連する受入条件**: AC-10
- **テスト種別**: E2E
- **テスト方法**: pytest + 実API呼び出し
- **前提条件**:
  1. サービス起動済み（expertAgent, jobqueue）
  2. 環境変数設定済み
- **テスト手順**:
  1. Job Generator V2 APIにリクエスト送信
  2. ステータスポーリングで完了待機
  3. 生成されたTaskMasterを取得
  4. body_templateを検証
- **期待結果**:
  - ジョブ生成成功
  - task_006のbody_templateが正しい形式
- **curlコマンド**:
  ```bash
  # Step 1: Job生成開始
  curl -s -X POST http://localhost:8004/v2/jobs/generate \
    -H "Content-Type: application/json" \
    -d '{
      "input": "キーワード検索してメール詳細を取得し、要約を作成してメールを送信する",
      "engine": "taskflow",
      "project": "default_project"
    }'

  # Step 2: ステータス確認
  curl -s "http://localhost:8004/v2/jobs/{job_id}/status"

  # Step 3: 結果取得（生成完了後）
  curl -s "http://localhost:8004/v2/jobs/{job_id}/result"
  ```
- **pytestメソッド**: `test_e2e_multi_dependency_workflow_registration`

---

## 11. テスト実行計画

### 実行順序
1. **単体テスト実行**
   ```bash
   cd expertAgent && uv run pytest tests/unit/test_job_generator_v2/test_registration/test_master_manager.py -v
   ```

2. **結合テスト実行**
   ```bash
   cd expertAgent && uv run pytest tests/integration/test_registration_validation.py -v
   ```

3. **サービス起動確認**
   ```bash
   curl http://localhost:8004/health
   curl http://localhost:8001/health
   ```

4. **E2E受入テスト実行**
   ```bash
   cd expertAgent && uv run pytest tests/acceptance/test_issue_403_acceptance.py -v -s
   ```

5. **デッドコード検証**
   ```bash
   grep -rn "_find_field_source" expertAgent/ --include="*.py" | grep -v "def _find_field_source"
   grep -rn "validate_multi_field_references" expertAgent/ --include="*.py" | grep -v "def validate_multi_field_references"
   ```

### 成功基準
- [ ] すべての単体テストがパス（TC-001〜TC-007）
- [ ] 結合テストがパス
- [ ] E2Eテストがパス（TC-008）
- [ ] すべての受入条件（AC-1〜AC-10）が検証済み
- [ ] デッドコードが検出されないこと（_find_field_source, validate_multi_field_referencesが実際に使用されている）
- [ ] カバレッジ90%以上

---

## 12. 補足事項

### リスク
| リスク | 影響度 | 対策 |
|-------|-------|------|
| mySwiftAgentCoreが新形式body_templateを処理できない | 高 | 事前にmySwiftAgentCoreのテンプレート展開ロジックを確認 |
| 既存テストが新シグネチャで壊れる | 中 | オプション引数により後方互換性維持 |
| フィールド解決の優先順位が複雑なケースで意図しない動作 | 中 | 詳細なログ出力で追跡可能に |

### 追加確認事項
1. **mySwiftAgentCore側の確認**: 新形式（辞書形式の`inputs`）を処理できるか確認
2. **BodyTemplateValidator拡張**: `validate_multi_field_references`の追加実装
3. **ログ出力の検証**: DEBUG/WARNING/INFOログが適切に出力されることを確認

### 関連Issue
- Issue #401: Run status同期問題
- Issue #402: トポロジカルソート問題
- Issue #342: Job Generator V2アーキテクチャ
- Issue #358: BodyTemplateValidator設計

# 受入テスト計画書

**Issue**: #409
**タイトル**: bug(expertAgent): 複数独立タスク存在時のデータフロー設計不備
**作成日**: 2026-01-26
**作成者**: acceptance-plan (スラッシュコマンド)

---

## 1. 概要

### 対象Issue
- **番号**: #409
- **タイトル**: 複数独立タスク存在時のデータフロー設計不備
- **プロジェクト**: expertAgent
- **ラベル**: bug

### 問題の要約

複数の独立タスク（`dependencies=[]`）が存在する場合、2番目以降の独立タスクがユーザー入力（`{{job.body.user_input}}`）ではなく、前のタスクの出力（`{{tasks[order-1].output_data}}`）を参照してしまい、データが失われる問題。

### 参照ドキュメント
- Issue: #409
- 設計方針書: `dev-reports/issue/409/design-policy.md`
- 関連Issue: #408（ユーザー入力フィールド名の整合性検証機能）、#403

---

## 2. 単体テスト結果レビュー

### 現状（実装前）

本Issueは**未実装**のため、単体テスト結果は存在しません。

### 実装完了時の目標値

| 指標 | 目標値 | 根拠 |
|------|--------|------|
| 単体テストカバレッジ | 90%以上 | CLAUDE.md準拠 |
| 結合テストカバレッジ | 50%以上 | CLAUDE.md準拠 |
| 新規追加コードカバレッジ | 100% | design-policy.md セクション11.4 |
| 静的解析エラー | 0件 | CLAUDE.md準拠 |

### 単体テストでカバーすべき項目

1. `_build_body_template`の独立タスク判定ロジック
2. `_get_user_input_schema`のスキーママージロジック
3. 同名フィールド衝突時の型チェック
4. レガシー呼び出し（`task=None`）の後方互換性

---

## 3. 受入条件分析

### AC-1: 独立タスクがuser_inputを使用する
- **原文**: `dependencies=[]`のタスク（TaskFlow）は`{{job.body.user_input}}`を使用する
- **分類**: 機能要件
- **テスト方法**: pytest / 実API呼び出し
- **モック使用**: 一部可（LLM呼び出しのみ）
- **検証ポイント**:
  1. `order > 0`かつ`dependencies=[]`のタスクが`{{job.body.user_input}}`を参照すること
  2. `order == 0`のタスクは従来通り動作すること

### AC-2: スキーママージ機能
- **原文**: `_get_user_input_schema`が全独立タスクのフィールドを含む
- **分類**: 機能要件
- **テスト方法**: pytest
- **モック使用**: 不可
- **検証ポイント**:
  1. 複数の独立タスクの`input_schema`がマージされること
  2. `properties`と`required`両方がマージされること

### AC-3: Issue #408検証機能との統合
- **原文**: Issue #408の検証が正しく機能する（全ユーザー入力フィールドが検証対象）
- **分類**: 機能要件（結合）
- **テスト方法**: pytest / 結合テスト
- **モック使用**: 一部可
- **検証ポイント**:
  1. 複数独立タスク存在時に全フィールドが検証対象となること

### AC-4: 複数独立タスクのテストケース追加
- **原文**: 複数独立タスクのテストケースが追加される
- **分類**: 品質要件
- **テスト方法**: テストファイル確認
- **モック使用**: N/A
- **検証ポイント**:
  1. `test_issue_409_acceptance.py`が作成されること
  2. TC-007〜TC-012が実装されること

### AC-5: レガシーテストの維持
- **原文**: 既存テストTC-005は「task=Noneでのレガシー動作テスト」として残し、テストのdocstringにレガシー互換性テストであることを明記する
- **分類**: 品質要件
- **テスト方法**: コード確認
- **モック使用**: N/A
- **検証ポイント**:
  1. TC-005のdocstringにレガシー互換性テストであることが明記されること
  2. TC-005が従来通り動作すること

### AC-6: 同名フィールド衝突時の警告ログ（型一致）
- **原文**: 同名フィールド衝突時に**両方の型情報を含む**警告ログを出力する
- **分類**: 機能要件
- **テスト方法**: pytest / ログ確認
- **モック使用**: 不可
- **検証ポイント**:
  1. 同名・同型フィールドが存在する場合に警告ログが出力されること
  2. ログに`Existing type: X, New type: Y`形式で両方の型情報が含まれること

### AC-7: 同名フィールド衝突時のエラー（型不一致）
- **原文**: 同名フィールドで**型が異なる場合はValueErrorを発生**させる
- **分類**: 機能要件
- **テスト方法**: pytest / 例外確認
- **モック使用**: 不可
- **検証ポイント**:
  1. 同名・異型フィールドが存在する場合に`ValueError`が発生すること
  2. エラーメッセージに両方の型情報が含まれること

### AC-8: ドキュメント作成
- **原文**: 独立タスクのデータフロー仕様を`expertAgent/docs/`に文書化する
- **分類**: ドキュメント要件
- **テスト方法**: ファイル存在確認
- **モック使用**: N/A
- **検証ポイント**:
  1. `expertAgent/docs/features/independent-task-dataflow.md`が作成されること
  2. 独立タスクの定義、データフロー仕様、同名フィールドの扱いが記載されていること

---

## 4. 設計方針検証

### DP-1: 後方互換性の維持
- **設計方針**: `task=None`の場合はレガシー動作を維持（design-policy.md セクション10.1）
- **検証方法**: pytest
- **テスト項目**:
  1. `_build_body_template(order=1, task=None)`が`{{tasks[0].output_data}}`を返すこと
  2. 既存テストTC-005が変更なくパスすること

### DP-2: 独立タスク判定ロジック
- **設計方針**: `order == 0 or (task is not None and not task.dependencies)`（design-policy.md セクション6.1）
- **検証方法**: pytest
- **テスト項目**:
  1. `order=0`のタスクは`{{job.body.user_input}}`を返すこと
  2. `order > 0`かつ`dependencies=[]`のタスクは`{{job.body.user_input}}`を返すこと
  3. `order > 0`かつ`dependencies`があるタスクは前タスク出力を参照すること

### DP-3: 同名フィールド衝突の処理分岐
- **設計方針**: 型一致→警告+後勝ち、型不一致→ValueError（design-policy.md セクション9.1）
- **検証方法**: pytest
- **テスト項目**:
  1. 型一致時に警告ログが出力されること
  2. 型不一致時に`ValueError`が発生すること
  3. ログ/エラーメッセージに両方の型情報が含まれること

### DP-4: スキーママージのパフォーマンス
- **設計方針**: O(n×m)で影響軽微（design-policy.md セクション8.1）
- **検証方法**: 目視確認（パフォーマンステストは不要）
- **テスト項目**:
  1. 独立タスク10個程度でも処理が完了すること（タイムアウトなし）

---

## 5. デッドコード検証計画

### F-1: `_build_body_template`の独立タスク分岐
- **ファイル**: `expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/registration/master_manager.py`
- **種別**: 条件分岐（追加）
- **検証方法**:
  ```bash
  # 独立タスク判定が実行されることを確認
  grep -rn "task is not None and not task.dependencies" expertAgent/
  ```
- **E2E確認**: 複数独立タスクを持つJobを生成し、両タスクのbody_templateを確認

### F-2: `_get_user_input_schema`のスキーママージ
- **ファイル**: `expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/registration/master_manager.py`
- **種別**: メソッド（修正）
- **検証方法**:
  ```bash
  # マージロジックが使用されることを確認
  grep -rn "_get_user_input_schema" expertAgent/ --include="*.py" | grep -v "def _get_user_input_schema"
  ```
- **E2E確認**: 複数独立タスク存在時にマージされたスキーマが返されることを確認

### F-3: 同名フィールド衝突の型チェック
- **ファイル**: `expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/registration/master_manager.py`
- **種別**: 条件分岐（追加）
- **検証方法**:
  ```bash
  # 型チェックロジックが存在することを確認
  grep -rn "existing_type.*new_type" expertAgent/
  ```
- **E2E確認**: 同名・異型フィールドを持つタスクでValueErrorが発生することを確認

---

## 6. テスト環境

### 必須サービス
| サービス | URL | ヘルスチェック |
|---------|-----|--------------|
| expertAgent | http://localhost:8004 | GET /health |
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

### テストデータ

**複数独立タスクシナリオ（正常系）**:
```json
{
  "tasks": [
    {"id": "task_001", "name": "Get Keyword", "dependencies": []},
    {"id": "task_002", "name": "Get Email", "dependencies": []},
    {"id": "task_003", "name": "Search", "dependencies": ["task_001"]},
    {"id": "task_004", "name": "Send Email", "dependencies": ["task_002", "task_003"]}
  ],
  "interfaces": {
    "task_001": {
      "input_schema": {
        "type": "object",
        "properties": {"keyword": {"type": "string"}},
        "required": ["keyword"]
      }
    },
    "task_002": {
      "input_schema": {
        "type": "object",
        "properties": {"email": {"type": "string"}},
        "required": ["email"]
      }
    }
  }
}
```

**同名フィールド衝突シナリオ（型一致・警告ログ確認用）**:
```json
{
  "tasks": [
    {"id": "task_001", "name": "Task A", "dependencies": []},
    {"id": "task_002", "name": "Task B", "dependencies": []}
  ],
  "interfaces": {
    "task_001": {
      "input_schema": {
        "type": "object",
        "properties": {"shared_field": {"type": "string"}},
        "required": ["shared_field"]
      }
    },
    "task_002": {
      "input_schema": {
        "type": "object",
        "properties": {"shared_field": {"type": "string"}, "unique_field": {"type": "string"}},
        "required": ["shared_field"]
      }
    }
  }
}
```

**同名フィールド衝突シナリオ（型不一致・ValueError確認用）**:
```json
{
  "tasks": [
    {"id": "task_001", "name": "Task A", "dependencies": []},
    {"id": "task_002", "name": "Task B", "dependencies": []}
  ],
  "interfaces": {
    "task_001": {
      "input_schema": {
        "type": "object",
        "properties": {"count": {"type": "string"}},
        "required": ["count"]
      }
    },
    "task_002": {
      "input_schema": {
        "type": "object",
        "properties": {"count": {"type": "integer"}},
        "required": ["count"]
      }
    }
  }
}
```

---

## 7. テスト項目

### テストケース番号マッピング

本計画のテストケース番号とIssue #409で定義されたテストケース番号の対応関係：

| 本計画 | Issue #409 | 概要 |
|--------|-----------|------|
| TC-001 | TC-007 | 独立タスク（task指定あり、dependencies=[]）がuser_inputを使用 |
| TC-002 | - | レガシー呼び出し（task=None）の後方互換性 |
| TC-003 | TC-009 | スキーママージ - 複数独立タスクのフィールドをマージ |
| TC-004 | TC-011 | 同名フィールド衝突 - 型一致時の警告ログ |
| TC-005 | TC-012 | 同名フィールド衝突 - 型不一致時のValueError |
| TC-006 | TC-010 | Issue #408検証との統合 |
| TC-007 | TC-008 | E2E - 複数独立タスクのJob生成フロー |
| TC-008 | - | ドキュメント存在確認 |

> **注**: Issue #409のTC-007〜TC-012は「本Issueで追加するテスト」として定義されており、本計画ではより詳細な実行手順を含めて再整理しています。

---

### TC-001: 独立タスク（order > 0, dependencies=[]）がuser_inputを使用する
- **テスト観点**: AC-1の主要検証
- **関連する受入条件**: AC-1
- **関連する設計方針**: DP-2
- **テスト種別**: 単体テスト
- **テスト方法**: pytest
- **前提条件**:
  1. MasterManagerSubWorkflowインスタンスが作成済み
  2. TaskDefinitionオブジェクト（dependencies=[]）が準備済み
- **テスト手順**:
  1. `_build_body_template(order=1, task=task_with_empty_deps, ...)`を呼び出す
  2. 戻り値の`inputs`フィールドを確認する
- **期待結果**:
  - `inputs`が`"{{job.body.user_input}}"`であること
- **pytestメソッド**: `test_tc001_independent_task_uses_user_input`

### TC-002: レガシー呼び出し（task=None）の後方互換性
- **テスト観点**: 後方互換性の維持
- **関連する受入条件**: AC-5
- **関連する設計方針**: DP-1
- **テスト種別**: 単体テスト
- **テスト方法**: pytest
- **前提条件**:
  1. MasterManagerSubWorkflowインスタンスが作成済み
- **テスト手順**:
  1. `_build_body_template(order=1, task=None)`を呼び出す
  2. 戻り値の`inputs`フィールドを確認する
- **期待結果**:
  - `inputs`が`"{{tasks[0].output_data}}"`であること（レガシー動作）
- **pytestメソッド**: `test_tc002_legacy_call_backward_compatibility`

### TC-003: スキーママージ - 複数独立タスクのフィールドをマージ
- **テスト観点**: AC-2の主要検証
- **関連する受入条件**: AC-2
- **関連する設計方針**: DP-2
- **テスト種別**: 単体テスト
- **テスト方法**: pytest
- **前提条件**:
  1. MasterManagerSubWorkflowインスタンスが作成済み
  2. 2つの独立タスク（異なるフィールドを持つ）が準備済み
- **テスト手順**:
  1. `_get_user_input_schema(sorted_tasks, interfaces)`を呼び出す
  2. 戻り値の`properties`フィールドを確認する
- **期待結果**:
  - 両タスクのフィールド（keyword, email）がマージされていること
  - `required`フィールドもマージされていること
- **pytestメソッド**: `test_tc003_schema_merge_multiple_independent_tasks`

### TC-004: 同名フィールド衝突 - 型一致時の警告ログ
- **テスト観点**: AC-6の検証
- **関連する受入条件**: AC-6
- **関連する設計方針**: DP-3
- **テスト種別**: 単体テスト
- **テスト方法**: pytest + ログキャプチャ
- **前提条件**:
  1. 2つの独立タスク（同名・同型フィールドを持つ）が準備済み
- **テスト手順**:
  1. `_get_user_input_schema`を呼び出す
  2. 警告ログをキャプチャして確認する
- **期待結果**:
  - 警告ログが出力されること
  - ログに`Existing type: string, New type: string`が含まれること
- **pytestメソッド**: `test_tc004_same_field_same_type_warning_log`

### TC-005: 同名フィールド衝突 - 型不一致時のValueError
- **テスト観点**: AC-7の検証
- **関連する受入条件**: AC-7
- **関連する設計方針**: DP-3
- **テスト種別**: 単体テスト
- **テスト方法**: pytest + pytest.raises
- **前提条件**:
  1. 2つの独立タスク（同名・異型フィールドを持つ）が準備済み
- **テスト手順**:
  1. `_get_user_input_schema`を呼び出す
  2. ValueErrorが発生することを確認する
- **期待結果**:
  - `ValueError`が発生すること
  - エラーメッセージに`'string' vs 'integer'`が含まれること
- **pytestメソッド**: `test_tc005_same_field_different_type_value_error`

### TC-006: Issue #408検証との統合
- **テスト観点**: AC-3の検証（結合テスト）
- **関連する受入条件**: AC-3
- **関連する設計方針**: DP-2
- **テスト種別**: 結合テスト
- **テスト方法**: pytest
- **前提条件**:
  1. 複数独立タスクを持つワークフロー構成が準備済み
- **テスト手順**:
  1. MasterManagerSubWorkflowの`create_masters`を呼び出す
  2. Issue #408の検証が全フィールドを対象としていることを確認する
- **期待結果**:
  - 両独立タスクのフィールドが検証対象となること
- **pytestメソッド**: `test_tc006_integration_with_issue_408_validation`

### TC-007: E2E - 複数独立タスクのJob生成フロー
- **テスト観点**: E2E-001（実際のJob生成フロー）
- **関連する受入条件**: AC-1, AC-2
- **関連する設計方針**: DP-2
- **テスト種別**: E2E / 受入テスト
- **テスト方法**: pytest + 実サービス呼び出し
- **前提条件**:
  1. expertAgentサービスが起動済み
  2. myVaultサービスが起動済み（APIキー設定済み）
  3. **LLMが確実に独立タスクを生成するよう、プロンプトを具体的に設計**
     - 例: 「Task1でキーワード入力を受け取り、Task2で別途メールアドレス入力を受け取る」
     - プロンプトに「2つの独立したタスクとして」と明示
- **代替検証方法**: LLM出力が不安定な場合、登録フェーズ（`MasterManagerSubWorkflow`）を直接テスト
- **テスト手順**:
  1. 複数独立タスクを生成するプロンプトでJob生成APIを呼び出す
  2. 生成されたTaskMasterのbody_templateを確認する
- **期待結果**:
  - 両独立タスクのbody_templateが`{{job.body.user_input}}`を参照すること
- **curlコマンド**:
  ```bash
  curl -s -X POST http://localhost:8004/v1/api/job/generate \
    -H "Content-Type: application/json" \
    -d '{
      "prompt": "キーワードについてGoogle検索してメール送信する\n- キーワード: 大谷翔平\n- メール送信先: test@example.com",
      "project": "default_project",
      "engine": "taskflow"
    }'
  ```
- **pytestメソッド**: `test_tc007_e2e_multiple_independent_tasks_job_generation`

### TC-008: ドキュメント存在確認
- **テスト観点**: AC-8の検証
- **関連する受入条件**: AC-8
- **関連する設計方針**: N/A
- **テスト種別**: ドキュメント確認
- **テスト方法**: ファイル存在確認
- **前提条件**: なし
- **テスト手順**:
  1. `expertAgent/docs/features/independent-task-dataflow.md`の存在を確認する
  2. 必要な内容が記載されているか確認する
- **期待結果**:
  - ファイルが存在すること
  - 独立タスクの定義、データフロー仕様、同名フィールドの扱いが記載されていること
- **bashコマンド**:
  ```bash
  ls -la expertAgent/docs/features/independent-task-dataflow.md
  grep -c "dependencies=\[\]" expertAgent/docs/features/independent-task-dataflow.md
  ```
- **pytestメソッド**: `test_tc008_documentation_exists`

---

## 8. コンポーネント間整合性検証

### CI-1: バリデータ整合性
- **検証対象**: `_build_body_template`と`_get_user_input_schema`の独立タスク判定
- **検証方法**:
  ```bash
  # 両メソッドの独立タスク判定が一貫していることを確認
  grep -n "not task.dependencies\|dependencies=\[\]" expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/registration/master_manager.py
  ```
- **確認項目**:
  - [ ] 両メソッドで同じ条件（`not task.dependencies`）を使用していること

### CI-2: エラーメッセージ整合性
- **検証対象**: ValueError発生時のメッセージフォーマット
- **検証方法**: TC-005のエラーメッセージ確認
- **確認項目**:
  - [ ] エラーメッセージに型情報が一貫した形式で含まれること

---

## 9. サービス間データフロー検証

### DF-1: ユーザー入力の伝播
| 送信元 | データ項目 | 送信先 | 取得方法 | 検証状態 |
|--------|-----------|--------|---------|---------|
| User | keyword, email | expertAgent | API POST body | 📋 未検証 |
| expertAgent | body_template | TaskMaster | Job登録時 | 📋 未検証 |
| TaskMaster | user_input | Workflow実行 | テンプレート展開 | 📋 未検証 |

### DF-2: テストデータ妥当性
- **禁止**: テストで空の`dependencies`を「依存あり」として扱うことは禁止
- **確認**: `dependencies=[]`は「独立タスク」として正しく扱われること

---

## 10. テスト実行計画

### 実行順序
1. サービス起動確認（ヘルスチェック）
2. 単体テスト実行（TC-001〜TC-005）
3. 結合テスト実行（TC-006）
4. E2Eテスト実行（TC-007）
5. ドキュメント確認（TC-008）
6. デッドコード検証（F-1〜F-3）

### 実行コマンド

```bash
# 1. サービス起動
./scripts/dev-hybrid.sh start --local-only

# 2. ヘルスチェック
curl -s http://localhost:8004/health | jq .
curl -s http://localhost:8003/health | jq .

# 3. 単体・結合テスト実行（絶対パス使用推奨）
uv run pytest expertAgent/tests/acceptance/test_issue_409_acceptance.py -v -s

# 4. カバレッジ確認
uv run pytest expertAgent/tests/ \
  --cov=expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/registration/master_manager.py \
  --cov-report=term-missing

# 5. 静的解析
./scripts/pre-push-check-all.sh

# 6. 既存テスト（Issue #403 TC-005）の動作確認
uv run pytest expertAgent/tests/acceptance/test_issue_403_acceptance.py::TestBodyTemplateValidation::test_tc005_build_body_template_backward_compatibility -v
```

### 成功基準
- [ ] すべての単体テスト（TC-001〜TC-005）がパス
- [ ] 結合テスト（TC-006）がパス
- [ ] E2Eテスト（TC-007）がパス
- [ ] ドキュメント確認（TC-008）がパス
- [ ] 単体テストカバレッジ90%以上
- [ ] 静的解析エラー0件
- [ ] デッドコードが検出されないこと
- [ ] 既存テスト（Issue #403 TC-005: `test_tc005_build_body_template_backward_compatibility`）が変更なくパス
- [ ] Issue #403 TC-005のdocstringにレガシー互換性テストであることが明記済み

---

## 11. 補足事項

### 既存テストへの影響

以下の既存テストが影響を受ける可能性があります：

| テストファイル | 該当テストケース | 行番号 | 影響 | 対応 |
|--------------|----------------|--------|------|------|
| `expertAgent/tests/acceptance/test_issue_403_acceptance.py` | `test_tc005_build_body_template_backward_compatibility` | L254-273 | docstring更新が必要 | レガシー互換性テストであることを明記 |
| `expertAgent/tests/acceptance/test_issue_408_acceptance.py` | - | - | 統合動作の検証が必要 | TC-006で検証 |

**確認コマンド**:
```bash
# Issue #403 TC-005の内容確認
sed -n '254,273p' expertAgent/tests/acceptance/test_issue_403_acceptance.py
```

### 注意事項

1. **LLM呼び出しのモック**: E2Eテスト以外ではLLM呼び出しをモック可能
2. **myVault依存**: シークレット取得が必要なテストはmyVaultサービス起動が必須
3. **GraphAI未対応**: 本Issueではgraphaiエンジンのテストは対象外

### 今後の課題

- GraphAIエンジンへの同様の修正（将来Issue）
- 互換性チェックの強化（将来Issue）
- モニタリング追加（将来Issue）

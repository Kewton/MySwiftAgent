# 受入テスト計画書

**Issue**: #392
**作成日**: 2026-01-22
**作成者**: acceptance-plan-agent

---

## 1. 概要

### 対象Issue
- **番号**: #392
- **タイトル**: Bug: workflow_name が重複形式 (task_task_001_task_001) になる
- **タイプ**: Bug Fix
- **プロジェクト**: mySwiftAgentCore / expertAgent

### 問題の要約
Job Generator V2 で生成されるワークフロー名が `task_task_001_task_001` のような重複形式になり、ワークフローの検索・実行に失敗する。

### 修正内容
1. `mySwiftAgentCore/src/taskflowGeneratorAgent/prompts/PromptBuilder.ts` の `generateWorkflowName` メソッドに重複回避ロジックを追加
2. `expertAgent/prompts/task_breakdown/default.yaml` にタスク命名規則を追加

### 参照ドキュメント
- Issue: #392
- 作業計画書: `expertAgent/dev-reports/feature/issue/392/work-plan.md`

---

## 2. 単体テスト結果レビュー

### カバレッジ
- 現在: 全テストパス (1689/1689)
- 目標: 90%
- 判定: PASS

### テスト品質評価
| 指標 | 値 | 判定 |
|------|-----|------|
| 追加テスト数 | 6 | - |
| テスト対象 | generateWorkflowName メソッド | - |
| エッジケースカバレッジ | 完全 | PASS |

### 追加されたテストケース
1. `task_id` と同じ名前の場合 - 重複回避確認
2. `task_id` を含む名前の場合 - 重複回避確認
3. 意味のある名前の場合 - 正常生成確認
4. 空の名前の場合 - フォールバック確認
5. 汎用名"task"の場合 - フォールバック確認
6. 日本語名の場合 - 文字列処理確認

### 単体テストでカバーされていない項目
1. LLMが実際に適切なタスク名を生成するか（プロンプト改善の効果）
2. 実際のJob Generator V2 APIを通じた動作確認
3. mySwiftAgentCore との統合動作確認

---

## 3. 受入条件分析

### AC-1: ワークフロー名の重複が発生しない
- **原文**: ワークフロー名が意味のある一意の名前になる（例: `gmail_search_task_001`）
- **分類**: 機能要件
- **テスト方法**: E2Eテスト（実API呼び出し）
- **検証ポイント**:
  1. `task_001` という名前のタスクでも `task_001_task_001` にならない
  2. `task_001` を含む名前でも重複しない
  3. 意味のある名前では正しく `{name}_{task_id}` 形式になる

### AC-2: LLMが適切なタスク名を生成する
- **原文**: タスク名として意味のある名前を生成するようプロンプトを修正
- **分類**: 機能要件
- **テスト方法**: E2Eテスト（実LLM呼び出し）
- **検証ポイント**:
  1. LLMがID形式（`task_001`）の名前を生成しない
  2. タスクの内容を表す意味のある名前が生成される

### AC-3: 既存ワークフローへの影響がない
- **原文**: 既存ワークフローへの影響がない
- **分類**: 非機能要件（後方互換性）
- **テスト方法**: 回帰テスト
- **検証ポイント**:
  1. 意味のある名前を持つタスクが正常に処理される
  2. 既存のワークフロー生成パターンが動作する

---

## 4. 設計方針検証

### DP-1: 重複回避ロジックの設計
- **設計方針**: `generateWorkflowName` メソッドで重複を検出し、task_idのみを返す
- **検証方法**: コードレビュー + テスト
- **テスト項目**:
  1. `baseName === task.task_id` の場合に `task_id` のみを返す
  2. `baseName.includes(task.task_id)` の場合に `task_id` のみを返す
  3. 空文字列や "task" の場合に `task_id` のみを返す

### DP-2: プロンプト改善の設計
- **設計方針**: `default.yaml` にタスク命名規則を追加し、ID形式の名前を禁止
- **検証方法**: プロンプト内容確認 + 実LLM呼び出し
- **テスト項目**:
  1. プロンプトにタスク命名規則が含まれている
  2. 禁止例（`task_001`）が明記されている
  3. 正しい例（`Gmail検索`）が明記されている

---

## 5. デッドコード検証計画

### F-1: generateWorkflowName メソッドの重複回避ロジック
- **ファイル**: `mySwiftAgentCore/src/taskflowGeneratorAgent/prompts/PromptBuilder.ts`
- **種別**: メソッド内ロジック
- **検証方法**:
  ```bash
  # 呼び出し箇所を確認
  grep -rn "generateWorkflowName" mySwiftAgentCore/src/ --include="*.ts"
  ```
- **E2E確認**: buildUserPrompt 経由で呼び出されることを確認

### F-2: タスク命名規則（プロンプト）
- **ファイル**: `expertAgent/prompts/task_breakdown/default.yaml`
- **種別**: プロンプトテンプレート
- **検証方法**:
  ```bash
  # プロンプトが使用されているか確認
  grep -rn "task_breakdown/default.yaml" expertAgent/ --include="*.py"
  ```
- **E2E確認**: Job Generator V2 API呼び出しでプロンプトが使用されることを確認

---

## 6. テスト環境

### 必須サービス
| サービス | URL | ヘルスチェック |
|---------|-----|--------------|
| mySwiftAgentCore | http://localhost:8006 | GET /health |
| expertAgent | http://localhost:8004 | GET /health |
| myVault | http://localhost:8003 | GET /health |

### 起動コマンド（E2Eテスト用）

```bash
# 1. 既存サービスを停止
./scripts/dev-hybrid.sh stop --local-only

# 2. ローカルモードでサービスを起動
./scripts/dev-hybrid.sh start --local-only
```

### シークレット・設定情報

E2Eテストで使用するシークレットは、コンテナ起動のmyVaultのdefault_projectから取得します。

| 項目 | 取得元 |
|------|--------|
| OPENAI_API_KEY | myVault (default_project) |
| LLM_API_KEY | myVault (default_project) |

### 環境変数
| 変数名 | 説明 | 必須 |
|--------|------|------|
| MYVAULT_ENABLED | MyVault有効化フラグ | true |
| MYVAULT_BASE_URL | MyVault URL | http://localhost:8003 |

---

## 7. テスト項目

### TC-001: ID形式のタスク名で重複しないこと
- **テスト観点**: `task.name = "task_001"` の場合、ワークフロー名が `task_001` になる（`task_001_task_001` ではない）
- **関連する受入条件**: AC-1
- **関連する設計方針**: DP-1
- **テスト種別**: E2E
- **テスト方法**: curl + pytest
- **前提条件**:
  1. mySwiftAgentCore が起動している
  2. expertAgent が起動している
- **テスト手順**:
  1. PromptBuilder.buildUserPrompt を task.name = "task_001" で呼び出す
  2. 生成されたプロンプト内の workflow_name を確認
- **期待結果**:
  - プロンプトに `workflow_name: "task_001"` が含まれる
  - `task_001_task_001` が含まれない
- **pytestメソッド**: `test_tc_001_id_format_task_name_no_duplication`

### TC-002: task_idを含むタスク名で重複しないこと
- **テスト観点**: `task.name = "Task_001 Search"` の場合、ワークフロー名が `task_001` になる
- **関連する受入条件**: AC-1
- **関連する設計方針**: DP-1
- **テスト種別**: E2E
- **テスト方法**: pytest
- **前提条件**:
  1. mySwiftAgentCore が起動している
- **テスト手順**:
  1. PromptBuilder.buildUserPrompt を task.name = "Task_001 Search" で呼び出す
  2. 生成されたプロンプト内の workflow_name を確認
- **期待結果**:
  - プロンプトに `workflow_name: "task_001"` が含まれる
  - `task_001_search_task_001` が含まれない
- **pytestメソッド**: `test_tc_002_task_name_contains_task_id_no_duplication`

### TC-003: 意味のあるタスク名で正しく生成されること
- **テスト観点**: `task.name = "Gmail Search"` の場合、ワークフロー名が `gmail_search_task_001` になる
- **関連する受入条件**: AC-1
- **関連する設計方針**: DP-1
- **テスト種別**: E2E
- **テスト方法**: pytest
- **前提条件**:
  1. mySwiftAgentCore が起動している
- **テスト手順**:
  1. PromptBuilder.buildUserPrompt を task.name = "Gmail Search" で呼び出す
  2. 生成されたプロンプト内の workflow_name を確認
- **期待結果**:
  - プロンプトに `workflow_name: "gmail_search_task_001"` が含まれる
- **pytestメソッド**: `test_tc_003_meaningful_task_name_correct_generation`

### TC-004: 空のタスク名でフォールバックすること
- **テスト観点**: `task.name = ""` の場合、ワークフロー名が `task_001` になる
- **関連する受入条件**: AC-1
- **関連する設計方針**: DP-1
- **テスト種別**: E2E
- **テスト方法**: pytest
- **前提条件**:
  1. mySwiftAgentCore が起動している
- **テスト手順**:
  1. PromptBuilder.buildUserPrompt を task.name = "" で呼び出す
  2. 生成されたプロンプト内の workflow_name を確認
- **期待結果**:
  - プロンプトに `workflow_name: "task_001"` が含まれる
- **pytestメソッド**: `test_tc_004_empty_task_name_fallback`

### TC-005: 汎用名"task"でフォールバックすること
- **テスト観点**: `task.name = "Task"` の場合、ワークフロー名が `task_001` になる（`task_task_001` ではない）
- **関連する受入条件**: AC-1
- **関連する設計方針**: DP-1
- **テスト種別**: E2E
- **テスト方法**: pytest
- **前提条件**:
  1. mySwiftAgentCore が起動している
- **テスト手順**:
  1. PromptBuilder.buildUserPrompt を task.name = "Task" で呼び出す
  2. 生成されたプロンプト内の workflow_name を確認
- **期待結果**:
  - プロンプトに `workflow_name: "task_001"` が含まれる
  - `task_task_001` が含まれない
- **pytestメソッド**: `test_tc_005_generic_task_name_fallback`

### TC-006: LLMが適切なタスク名を生成すること（E2E）
- **テスト観点**: 実際のLLM呼び出しで、ID形式のタスク名が生成されないこと
- **関連する受入条件**: AC-2
- **関連する設計方針**: DP-2
- **テスト種別**: E2E（実LLM呼び出し）
- **テスト方法**: curl
- **前提条件**:
  1. expertAgent が起動している
  2. myVault に OPENAI_API_KEY が設定されている
- **テスト手順**:
  1. Job Generator V2 API を呼び出す
  2. 生成されたタスクの name を確認
- **期待結果**:
  - タスク名が `task_001` 形式ではない
  - タスク名がタスクの内容を表す意味のある名前である
- **curlコマンド**:
  ```bash
  curl -s -X POST http://localhost:8004/v1/job-generator/generate \
    -H "Content-Type: application/json" \
    -d '{
      "user_requirement": "Gmailでメールを検索して内容を要約する",
      "project": "default_project"
    }' | jq '.tasks[0] | {name, task_id}'
  ```
- **pytestメソッド**: `test_tc_006_llm_generates_meaningful_task_names`

### TC-007: プロンプトにタスク命名規則が含まれていること
- **テスト観点**: `default.yaml` にタスク命名規則が正しく追加されていること
- **関連する受入条件**: AC-2
- **関連する設計方針**: DP-2
- **テスト種別**: 静的検証
- **テスト方法**: grep
- **前提条件**: なし
- **テスト手順**:
  1. `default.yaml` の内容を確認
  2. タスク命名規則セクションの存在を確認
- **期待結果**:
  - "タスク命名規則" または "Issue #392" が含まれる
  - "task_001" が禁止例として記載されている
  - "Gmail検索" などが正しい例として記載されている
- **検証コマンド**:
  ```bash
  grep -n "タスク命名規則\|Issue #392" expertAgent/prompts/task_breakdown/default.yaml
  grep -n "task_001.*禁止\|NG.*task_001" expertAgent/prompts/task_breakdown/default.yaml
  ```
- **pytestメソッド**: `test_tc_007_prompt_includes_naming_rules`

---

## 8. テスト実行計画

### 実行順序
1. サービス起動確認（ヘルスチェック）
2. 単体テスト再実行（既存6テストケース）
3. 静的検証（TC-007）
4. E2Eテスト実行（TC-001〜TC-006）

### テストコマンド

```bash
# 1. サービスヘルスチェック
curl -sf http://localhost:8006/health && echo "mySwiftAgentCore: OK"
curl -sf http://localhost:8004/health && echo "expertAgent: OK"
curl -sf http://localhost:8003/health && echo "myVault: OK"

# 2. 単体テスト実行（mySwiftAgentCore）
cd mySwiftAgentCore && npm test -- --run tests/unit/taskflowGeneratorAgent/prompts/PromptBuilder.test.ts

# 3. 静的検証
grep -n "タスク命名規則\|Issue #392" expertAgent/prompts/task_breakdown/default.yaml

# 4. E2Eテスト実行
# TC-006: 実LLM呼び出しテスト
curl -s -X POST http://localhost:8004/v1/job-generator/generate \
  -H "Content-Type: application/json" \
  -d '{
    "user_requirement": "Gmailでメールを検索して内容を要約する",
    "project": "default_project"
  }' | jq '.tasks[] | {task_id, name}'
```

### 成功基準
- [x] すべての単体テストがパス（6/6）
- [ ] すべてのE2Eテストがパス（TC-001〜TC-007）
- [ ] すべての受入条件が検証済み
- [ ] デッドコードが検出されないこと
- [ ] 既存ワークフローへの影響がないこと

---

## 9. 補足事項

### 注意点
- TC-006（実LLM呼び出し）はAPIキーが必要なため、ローカル環境でのみ実行可能
- LLMの出力は非決定的なため、複数回のテスト実行が推奨される
- 日本語タスク名のテストでは、日本語文字が除去されて英数字のみが残る点に注意

### 関連Issue
- Issue #390: E2Eテストで本問題が発見された
- Issue #361: mySwiftAgentCore 統合

### 修正されたファイル
1. `mySwiftAgentCore/src/taskflowGeneratorAgent/prompts/PromptBuilder.ts` (L279-301)
2. `expertAgent/prompts/task_breakdown/default.yaml` (L95-102)
3. `mySwiftAgentCore/tests/unit/taskflowGeneratorAgent/prompts/PromptBuilder.test.ts` (L1111-1205)

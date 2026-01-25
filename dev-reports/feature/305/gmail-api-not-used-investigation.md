# Gmail API 未使用問題 調査レポート

**Issue**: #305 (関連調査)
**対象**: v1.35 「分析レポートのメール送信」タスク
**調査日**: 2025-12-25
**ステータス**: ✅ 修正完了

---

## 1. 問題概要

v1.35 において、「分析レポートのメール送信」タスクに対して Gmail API (`/v1/utility/gmail/send`) が使用されず、代わりに `jsonoutput` API を使用したモック実装が生成された。

task_api_mapping の修正後にも関わらず、この問題が発生した根本原因を4つのフェーズで調査した。

---

## 2. 調査結果サマリ

| フェーズ | 根本原因 | 重要度 |
|---------|----------|-------|
| Task Breakdown | task_api_mappingはプロンプトに含まれているが、LLMが採用しなかった可能性 | 中 |
| Task Breakdown Evaluation | キーワードベースの評価が緩すぎ（「メール送信」キーワードで問題なし判定） | 高 |
| **Workflow Generation** | **「Mock Approach for Non-LLM Tasks」ルールがGmail API使用を禁止** | **最重要** |
| Workflow Evaluation | fast_modeが有効でLLM Evaluationがスキップされた | 高 |

---

## 3. 詳細調査結果

### 3.1 Phase 1: Task Breakdown

**調査対象**: `task_breakdown.py` の `_build_expert_agent_capabilities()`

**発見**:
- task_api_mappingはプロンプトに正しく含まれている（lines 156-173）
- fallbackプロンプト (lines 387-398) にも明記:
  ```
  | メール送信 | Gmail送信 | `/v1/utility/gmail/send` |
  ```

**問題点**:
- LLMがこの推奨を採用するかは確率的
- `task_breakdown` がデータベースに保存されていない（`null`）ため、実際にどのAPIが推奨されたか確認不可

**影響度**: 中

---

### 3.2 Phase 2: Task Breakdown Evaluation

**調査対象**: `evaluation.py` の `_build_api_specificity_check_prompt()`

**発見** (lines 629-656):
```python
api_keywords = [
    "gmail",
    "メール送信",
    "メール検索",
    "メール",
    # ...
]
```

**評価ロジック** (lines 773-774):
```
- `recommended_apis: fetchAgent` + `name: メール送信処理`
  → タスク名から「メール送信」が明確なので **問題なし**
```

**問題点**:
- タスク名に「メール」キーワードが含まれていれば、`recommended_apis` に具体的なGmail APIが指定されていなくても「問題なし」と判定
- **実際のAPI選択を検証していない**

**影響度**: 高

---

### 3.3 Phase 3: Workflow Generation ★根本原因

**調査対象**: `workflow_generation.py` の `create_workflow_generation_prompt()`

**発見** (lines 503-560):
```
**CRITICAL RULE - Mock Approach for Non-LLM Tasks** (MANDATORY):
- ❌ DO NOT attempt TTS audio generation via LLM
- ❌ DO NOT attempt file upload/download via LLM
- ❌ DO NOT attempt email sending via LLM  ← ★これが原因！
- ❌ DO NOT attempt cloud storage operations via LLM
- ✅ Use LLM to generate MOCK RESULTS for these tasks
- ✅ Include implementation notes for future API integration
```

**実際に生成されたワークフロー** (v1.35):
```yaml
# Step 1: Build mock prompt for email sending simulation
# As per mandatory rule for non-LLM tasks (email sending), we use a mock approach.
build_mock_prompt:
  agent: stringTemplateAgent
  inputs:
    recipient: :source.recipient_email
    subject: :source.subject
    body: :source.body_markdown
  params:
    template: |-
      あなたはメール送信システムを模擬するエージェントです。
      以下の情報を基に、分析レポートのメール送信処理の結果を模擬的に生成してください。
```

**問題点**:
- **このルールがtask_api_mappingの推奨を完全にオーバーライドしている**
- LLMは「メール送信はモック化すべき」と判断してGmail APIを使用しない
- ワークフロー生成プロンプトがtask_api_mappingを参照していない

**影響度**: 最重要

---

### 3.4 Phase 4: Workflow Evaluation

**調査対象**: `agent.py` の `validator_router()`

**発見** (lines 63-71):
```python
# Issue #305: Skip LLM evaluation in fast_mode when:
# 1. Rule-based validation passed
# 2. Workflow execution succeeded (HTTP 200)
if fast_mode and is_valid and test_http_status == 200:
    logger.info(
        "Validator router: fast_mode enabled and validation passed, "
        "skipping LLM evaluation -> result_summary_generator"
    )
    return "result_summary_generator"
```

**v1.35 の状態**:
```json
{
  "test_result": {"http_status": 200, "is_valid": true},
  "evaluation": null  // LLM Evaluationがスキップされた
}
```

**問題点**:
- `fast_mode=True` (デフォルト) でルールベースバリデーションが成功すると、LLM Evaluationがスキップされる
- LLM Evaluationには「Uses recommended APIs appropriately」のチェックがあるが、スキップされたため実行されなかった

**影響度**: 高

---

## 4. 根本原因の相関図

```
[Task Breakdown]
     ↓
task_api_mapping: "メール送信 → Gmail API" を推奨
     ↓
[Task Breakdown Evaluation]
     ↓
「メール」キーワード検出 → 問題なし判定（実際のAPI選択を検証せず）
     ↓
[Workflow Generation] ★根本原因
     ↓
「Mock Approach for Non-LLM Tasks」ルール適用
 → "email sending" はモック化すべき → Gmail API 使用禁止
     ↓
モックワークフロー生成（jsonoutput API 使用）
     ↓
[Workflow Evaluation]
     ↓
fast_mode + HTTP 200 → LLM Evaluation スキップ
     ↓
「recommended APIs appropriately」チェックなし
     ↓
モックワークフローが最終結果として採用
```

---

## 5. 実施した修正

### ✅ 修正1: Mock Approach for Non-LLM Tasks ルールの削除

**方針**: 品質重視のため、Mock Approachルール全体を削除

**修正ファイル**: `workflowGeneratorAgents/prompts/workflow_generation.py`

**削除した内容** (旧 lines 503-560):
```
**CRITICAL RULE - Mock Approach for Non-LLM Tasks** (MANDATORY):
- ❌ DO NOT attempt TTS audio generation via LLM
- ❌ DO NOT attempt file upload/download via LLM
- ❌ DO NOT attempt email sending via LLM
- ❌ DO NOT attempt cloud storage operations via LLM
- ✅ Use LLM to generate MOCK RESULTS for these tasks
- ✅ Include implementation notes for future API integration

**Non-LLM Task Pattern Examples**:
（モック実装のYAMLサンプル2件も削除）
```

**期待される効果**:
- メール送信タスクでGmail API (`/v1/utility/gmail/send`) が使用される
- TTS音声合成タスクでText-to-Speech API が使用される
- ファイルアップロードタスクでGoogle Drive API が使用される

---

### ✅ 修正2: fast_mode のデフォルト値を False に変更

**方針**: 品質重視のため、LLM Evaluationをデフォルトで実行

**修正ファイル**:
- `workflowGeneratorAgents/state.py` (line 140)
- `workflowGeneratorAgents/agent.py` (line 257)
- `tests/unit/test_workflow_generator_agent.py` (line 208-218)

**変更内容**:
```python
# Before
fast_mode: bool = True

# After
fast_mode: bool = False
```

**期待される効果**:
- 全ワークフローに対してLLM Evaluationが実行される
- 「Uses recommended APIs appropriately」チェックが有効になる
- API選択の不適切さが検出・修正される

**トレードオフ**:
- 処理時間が増加（1タスクあたり +10-30秒）
- APIコストが増加（LLM Evaluation呼び出し分）

---

## 6. 残課題（今後の検討事項）

### Task Breakdown Evaluation の厳格化

キーワードベースの評価に加え、task_api_mappingとの照合を追加:

```python
# タスク種別に対応するAPIが recommended_apis に含まれているか検証
if task_type == "メール送信" and not any("gmail" in api.lower() for api in recommended_apis):
    issues.append({
        "task_id": task_id,
        "problem": "メール送信タスクにGmail APIが推奨されていない",
        "recommended_api": "/v1/utility/gmail/send"
    })
```

---

## 7. 関連ファイル

| ファイルパス | 状態 |
|-------------|------|
| `workflowGeneratorAgents/prompts/workflow_generation.py` | ✅ 修正済み: Mock Approach Rule 削除 |
| `workflowGeneratorAgents/state.py` | ✅ 修正済み: fast_mode デフォルト False |
| `workflowGeneratorAgents/agent.py` | ✅ 修正済み: fast_mode デフォルト False |
| `tests/unit/test_workflow_generator_agent.py` | ✅ 修正済み: テスト更新 |
| `jobTaskGeneratorAgents/prompts/evaluation.py` | 残課題: Keyword-based Check (lines 629-656) |

---

## 8. 結論

Gmail API が使用されなかった**根本原因**は、Workflow Generation プロンプト内の「Mock Approach for Non-LLM Tasks」ルールであった。

### ✅ 実施した修正

品質重視の方針に基づき、以下の2点を修正した：

1. **Mock Approachルールの削除**
   - メール送信・TTS音声合成・ファイルアップロード等で実際のDirect APIが使用される

2. **fast_modeのデフォルト値をFalseに変更**
   - 全ワークフローでLLM Evaluationが実行される
   - 「Uses recommended APIs appropriately」チェックが有効になる

### 残課題

- Task Breakdown Evaluation のキーワードベース評価の厳格化

これは今後の改善として検討する。

---

**作成者**: Claude Code
**修正日**: 2025-12-25

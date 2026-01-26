# 作業計画: メール未送信問題の修正

## 不具合概要

- **問題**: E2Eテストで7/7タスク成功と表示されるが、メールが実際には送信されない
- **根本原因**: LLMがユーザー入力フィールドを正しく設計せず（`email` → `recipient_email`）、検証機能もそれを止めなかった
- **影響範囲**: ワークフロー生成全体

## 選択された対策案

| 対策案 | 概要 | 優先度 |
|-------|------|--------|
| 対策案1 | LLMプロンプトの改善 | High |
| 対策案2 | 検証の厳格化（WARNING→ERROR） | High |
| 対策案4 | user_input_schemaの明示的定義 | Medium |

---

## 対策案1: LLMプロンプトの改善

### 変更ファイル
- `expertAgent/aiagent/langgraph/jobGeneratorV2/nodes/job_analyzer.py`

### 変更内容
`JOB_ANALYSIS_SYSTEM_PROMPT` に以下のルールを追加:

1. **ユーザー入力フィールドの一貫性ルール**
   - 独立タスク（dependencies=[]）のinput_schemaは、ユーザーが実際に入力するフィールド名を正確に反映すること
   - 要件に「キーワード」と書かれていれば `keyword`、「メールアドレス」と書かれていれば `email` を使用

2. **フィールド名変更禁止ルール**
   - `email` を `recipient_email` や `user_email` に変更しない
   - `keyword` を `search_keyword` や `query` に変更しない

### テスト
- 単体テスト: プロンプトに新ルールが含まれることを確認
- 結合テスト: LLMが一貫したフィールド名を生成することを確認

---

## 対策案2: 検証の厳格化

### 変更ファイル
- `expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/registration/master_manager.py`

### 変更内容
`_build_multi_dependency_template` メソッドで、フィールド不一致を検出した場合:

**現状（WARNING）**:
```python
if field_name not in valid_user_input_fields:
    logger.warning("Issue #408: Fallback field '%s' not found in user_input_schema...")
```

**改善後（ERROR）**:
```python
if field_name not in valid_user_input_fields:
    raise UserInputFieldMismatchError(
        f"Field '{field_name}' not found in user_input_schema. "
        f"Available fields: {sorted(valid_user_input_fields)}. "
        f"The LLM may have generated inconsistent field names."
    )
```

### 新規例外クラス
- `UserInputFieldMismatchError` を `errors.py` に追加

### テスト
- 単体テスト: フィールド不一致時にエラーが発生することを確認
- 結合テスト: 問題のあるワークフローが作成されないことを確認

---

## 対策案4: user_input_schemaの明示的定義

### 変更ファイル
- `expertAgent/aiagent/langgraph/jobGeneratorV2/nodes/job_analyzer.py`

### 変更内容

1. **JobAnalysisResponseに新フィールド追加**:
```python
class JobAnalysisResponse(BaseModel):
    tasks: list[AnalyzedTask]
    interfaces: dict[str, InterfaceDefinition]
    job_body_parameters: list[JobParameter]
    overall_summary: str
    # 新規追加
    user_input_schema: dict[str, Any] = Field(
        default_factory=dict,
        description="Schema defining fields that users will provide as input"
    )
```

2. **プロンプトに新セクション追加**:
```
4. **User Input Schema**: Define the exact fields the user will provide.
   - Extract field names directly from the requirements (e.g., "キーワード" → "keyword")
   - These fields MUST be referenced consistently in all tasks
   - Example: {"keyword": {"type": "string"}, "email": {"type": "string", "format": "email"}}
```

3. **MasterManagerでの使用**:
   - `_get_user_input_schema()` でLLM生成のスキーマを優先的に使用
   - フォールバックとして従来の独立タスクからのマージを使用

### テスト
- 単体テスト: user_input_schemaが正しく生成されることを確認
- 結合テスト: スキーマがワークフロー全体で一貫して使用されることを確認

---

## 実装順序

1. **対策案4** (user_input_schema明示化) - 基盤となる変更
2. **対策案1** (プロンプト改善) - LLM生成品質の向上
3. **対策案2** (検証厳格化) - 最終的な安全網

## Definition of Done

- [ ] 全対策案が実装されている
- [ ] 単体テストカバレッジ 90%以上
- [ ] 静的解析エラー 0件
- [ ] E2Eテストでメールが正常に送信される

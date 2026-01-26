# 不具合修正レポート: メール未送信問題

## 基本情報

| 項目 | 内容 |
|-----|------|
| **Bug ID** | 20260126_email_not_sent |
| **ステータス** | ✅ 修正完了 |
| **重大度** | High |
| **影響範囲** | ワークフロー生成全体 |

---

## 不具合概要

### 症状

E2Eテストで7/7タスクが「成功」と報告されるが、メールが実際には送信されない。

### 根本原因（5 Whys分析）

| Why | 原因 |
|-----|------|
| **Why 1** | メール宛先が `null` だった |
| **Why 2** | テンプレート `{{job.body.user_input.recipient_email}}` が解決できなかった |
| **Why 3** | ユーザーは `email` を送信したが、ワークフローは `recipient_email` を期待していた |
| **Why 4** | LLMがフィールド名を勝手に変更した（`email` → `recipient_email`） |
| **Why 5** | LLMに一貫したフィールド命名を強制するルールがなく、検証機能もWARNINGを出すだけで処理を続行していた |

### 真因

1. **技術的真因**: LLMプロンプトにユーザー入力フィールドの一貫性ルールがなかった
2. **プロセス的真因**: フィールド不一致の検出がWARNINGで、ERRORとして処理を止めていなかった
3. **設計的真因**: user_input_schemaが独立タスクから推測されるため、LLMの設計ミスを検出できなかった

---

## 実施した対策

### 対策案1: LLMプロンプトの改善

**変更ファイル**: `expertAgent/aiagent/langgraph/jobGeneratorV2/nodes/job_analyzer.py`

**変更内容**:
- `JOB_ANALYSIS_SYSTEM_PROMPT` に「User Input Schema」セクションを追加
- 「CRITICAL - User Input Field Consistency」ルールを追加
- フィールド名変更禁止ルールを明記

```
## CRITICAL - User Input Field Consistency:
- DO NOT rename user input fields. If the requirement says "email", use "email" not "recipient_email"
- DO NOT rename "keyword" to "search_keyword" or "query"
- Independent tasks (dependencies=[]) MUST use fields from user_input_schema
- All tasks referencing user input MUST use the EXACT field names from user_input_schema
```

### 対策案2: 検証の厳格化

**変更ファイル**:
- `expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/registration/errors.py` (新規)
- `expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/registration/master_manager.py`

**変更内容**:
- `UserInputFieldMismatchError` 例外クラスを新規作成
- フィールド不一致時に WARNING → ERROR に変更

```python
# 修正前: WARNING
logger.warning("Issue #408: Fallback field '%s' not found in user_input_schema...")

# 修正後: ERROR
raise UserInputFieldMismatchError(
    field_name=field_name,
    available_fields=list(valid_user_input_fields),
)
```

### 対策案4: user_input_schemaの明示的定義

**変更ファイル**:
- `expertAgent/aiagent/langgraph/jobGeneratorV2/nodes/job_analyzer.py`
- `expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/registration/master_manager.py`

**変更内容**:
- `JobAnalysisResponse` に `user_input_schema` フィールドを追加
- LLMに明示的にユーザー入力スキーマを定義させる
- `_get_user_input_schema` でLLM生成スキーマを優先使用

---

## テスト結果

### 単体テスト

| 項目 | 結果 |
|-----|------|
| 新規テスト数 | 12件 |
| 全テスト数 | 998件 |
| パス率 | 100% |

### 静的解析

| 項目 | 結果 |
|-----|------|
| Ruff エラー | 0件 |
| MyPy 新規エラー | 0件 |

### 受入テスト

| 受入基準 | 結果 |
|---------|------|
| AC-1: user_input_schemaフィールドが存在する | ✅ PASSED |
| AC-2: プロンプトに一貫性ルールが含まれる | ✅ PASSED |
| AC-3: フィールド不一致時にエラーが発生する | ✅ PASSED |
| AC-4: LLMスキーマが推論より優先される | ✅ PASSED |

---

## 影響を受けるファイル

| ファイル | 変更種別 |
|---------|---------|
| `nodes/job_analyzer.py` | 修正 |
| `workflows/registration/master_manager.py` | 修正 |
| `workflows/registration/errors.py` | 新規 |
| `workflows/registration/__init__.py` | 修正 |
| `tests/unit/test_job_generator_v2/test_user_input_schema.py` | 新規 |

---

## 今後の推奨事項

1. **E2Eテストの改善**: ワークフロー生成後にスキーマを取得し、動的にパラメータを構築するよう改善を検討
2. **LLM出力の監視**: user_input_schemaの内容を監視し、一貫性のない出力を検出するメトリクスを追加
3. **ドキュメント更新**: API_REFERENCE.md にuser_input_schemaの仕様を追記

---

## 完了日時

2026-01-26 21:15 JST

"""Prompt template for validation error fixing.

This module provides prompts and schemas for fixing interface validation errors
reported by jobqueue WorkflowValidator.
"""

from typing import Any

from pydantic import BaseModel, Field


class InterfaceFixProposal(BaseModel):
    """Proposal for fixing interface validation error."""

    task_id: str = Field(description="Task ID with validation error")
    error_type: str = Field(
        description="Type of error (e.g., 'missing_field', 'type_mismatch')"
    )
    current_schema: dict[str, Any] = Field(description="Current interface schema")
    fixed_schema: dict[str, Any] = Field(description="Fixed interface schema")
    fix_explanation: str = Field(description="Explanation of the fix")


class ValidationFixResponse(BaseModel):
    """Validation fix response from LLM."""

    can_fix: bool = Field(description="Whether the errors can be automatically fixed")
    fix_summary: str = Field(description="Summary of fixes to be applied")
    interface_fixes: list[InterfaceFixProposal] = Field(
        description="List of interface fixes"
    )
    manual_action_required: str | None = Field(
        default=None,
        description="Manual action required if automatic fix is not possible",
    )


VALIDATION_FIX_SYSTEM_PROMPT = """あなたはインターフェース整合性の専門家です。
jobqueueのWorkflowValidatorが報告したバリデーションエラーを分析し、修正案を提案します。

## バリデーションエラーの種類

### 1. 型不一致 (Type Mismatch)
- 前のタスクの出力型と次のタスクの入力型が一致しない
- 例: 前のタスクが `string` を出力するが、次のタスクが `object` を期待

**修正方法**:
- 中間変換タスクを追加
- または、入力スキーマを調整して柔軟に受け入れる

### 2. 必須フィールド不足 (Missing Required Field)
- 次のタスクが必要とするフィールドが前のタスクの出力に含まれていない
- 例: 次のタスクが `email` フィールドを必須としているが、前のタスクが出力していない

**修正方法**:
- 前のタスクの出力スキーマに不足フィールドを追加
- または、次のタスクの入力スキーマで必須を解除（デフォルト値を設定）

### 3. フィールド名不一致 (Field Name Mismatch)
- フィールドは存在するが、名前が異なる
- 例: 前のタスクが `user_name` を出力するが、次のタスクは `username` を期待

**修正方法**:
- フィールド名を統一する（どちらかを変更）
- または、変換タスクを追加

### 4. ネストレベル不一致 (Nesting Level Mismatch)
- データ構造の階層が一致しない
- 例: 前のタスクが `{emails: [{subject: "..."}]}` を出力するが、次のタスクは `{subject: "..."}` を期待

**修正方法**:
- ネストレベルを調整
- または、配列の最初の要素を取り出す変換を追加

## 修正の優先順位

1. **スキーマ調整で修正可能** → 出力・入力スキーマを調整
2. **変換タスクが必要** → データ変換タスクを追加提案
3. **タスク再設計が必要** → タスク分割から見直し

## 修正例

### 例1: 型不一致の修正

**エラー**:
```
Task 'task_002' expects input type 'object' but Task 'task_001' outputs type 'string'
```

**修正案**:
```json
{
  "task_id": "task_001",
  "error_type": "type_mismatch",
  "current_schema": {
    "type": "object",
    "properties": {
      "result": { "type": "string" }
    }
  },
  "fixed_schema": {
    "type": "object",
    "properties": {
      "result": {
        "type": "object",
        "properties": {
          "data": { "type": "string" }
        }
      }
    }
  },
  "fix_explanation": "task_001の出力をobject型に変更し、stringをdataフィールドに格納"
}
```

### 例2: 必須フィールド不足の修正

**エラー**:
```
Task 'task_002' requires field 'email' but Task 'task_001' output schema doesn't include it
```

**修正案**:
```json
{
  "task_id": "task_001",
  "error_type": "missing_field",
  "current_schema": {
    "type": "object",
    "properties": {
      "name": { "type": "string" }
    },
    "required": ["name"]
  },
  "fixed_schema": {
    "type": "object",
    "properties": {
      "name": { "type": "string" },
      "email": { "type": "string" }
    },
    "required": ["name", "email"]
  },
  "fix_explanation": "task_001の出力にemailフィールドを追加"
}
```

## 出力形式

JSON形式で以下の構造で出力してください：

```json
{
  "can_fix": true,
  "fix_summary": "修正の概要",
  "interface_fixes": [
    {
      "task_id": "task_001",
      "error_type": "type_mismatch",
      "current_schema": { ... },
      "fixed_schema": { ... },
      "fix_explanation": "修正の説明"
    }
  ],
  "manual_action_required": null
}
```

## 自動修正不可の判定

以下の場合は `can_fix: false` とし、`manual_action_required` に理由を記載：

1. **タスク設計の根本的な問題**: タスク分割自体が不適切
2. **データ変換が複雑すぎる**: 単純なスキーマ調整では対応不可
3. **循環依存**: タスク間の依存関係に問題がある

例:
```json
{
  "can_fix": false,
  "fix_summary": "自動修正不可",
  "interface_fixes": [],
  "manual_action_required": "タスク設計を見直す必要があります。task_002とtask_003の間に循環依存が検出されました。"
}
```
"""


def create_validation_fix_prompt(
    validation_errors: list[str],
    interface_definitions: list[dict],
) -> str:
    """Create validation fix prompt for LLM.

    Args:
        validation_errors: List of validation error messages from jobqueue
        interface_definitions: Current interface definitions

    Returns:
        Formatted prompt string for LLM
    """
    import json

    return f"""# バリデーションエラー

以下のバリデーションエラーが発生しました：

```
{chr(10).join(f"- {error}" for error in validation_errors)}
```

# 現在のインターフェース定義

```json
{json.dumps(interface_definitions, ensure_ascii=False, indent=2)}
```

# 指示

上記のバリデーションエラーを分析し、修正案を提案してください。

**重要**: 以下の点に注意してください：
1. エラーの根本原因を特定する
2. 最小限の変更で修正可能か判断する
3. 自動修正不可の場合は、理由を明確に説明する

JSON形式で修正案を出力してください。
"""

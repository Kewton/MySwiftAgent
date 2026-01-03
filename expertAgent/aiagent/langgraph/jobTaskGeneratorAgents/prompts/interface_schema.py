"""Prompt template for interface schema definition.

This module provides prompts and schemas for defining input/output interfaces
for each task in JSON Schema format, compatible with jobqueue InterfaceMaster.
"""

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.services.prompt_loader import PromptLoader


class DerivedFieldDefinition(BaseModel):
    """Derived field definition for downstream tasks.

    Derived fields are pre-processed data outputs that downstream tasks can use
    directly without additional string manipulation. This supports the
    "Ready-to-Use Output" principle (Issue #337).

    Example:
        email_subject:
            template: "Search results: {query}"
            type: string
            description: "Email subject line"
            source_mapping:
                query: "source.user_input.query"
    """

    model_config = ConfigDict(extra="forbid")

    template: str = Field(
        description="Template string. Use {field_name} to reference source data"
    )
    type: str = Field(default="string", description="Type of the generated value")
    description: str | None = Field(
        default=None, description="Description of the derived field"
    )
    source_mapping: dict[str, str] | None = Field(
        default=None,
        description="Explicit mapping of variable names to source paths (optional)",
    )


class InterfaceSchemaDefinition(BaseModel):
    """Interface schema for a single task."""

    # Forbid extra fields to ensure OpenAI API compatibility
    # OpenAI's structured output requires additionalProperties: false
    model_config = ConfigDict(extra="forbid")

    task_id: str = Field(description="Task ID to define interface for")
    interface_name: str = Field(
        description="Interface name (e.g., 'gmail_search_interface')"
    )
    description: str = Field(description="Description of the interface")
    input_schema: dict[str, Any] = Field(
        description="JSON Schema for input (must be valid JSON Schema)"
    )
    output_schema: dict[str, Any] = Field(
        description="JSON Schema for output (must be valid JSON Schema)"
    )
    derived_fields: dict[str, DerivedFieldDefinition] = Field(
        default_factory=dict,
        description="Derived field definitions for downstream tasks (ready-to-use data)",
    )

    @field_validator("input_schema", "output_schema", mode="before")
    @classmethod
    def parse_json_schema(cls, value: Any) -> dict[str, Any]:
        """Parse JSON string to dict if needed.

        Gemini's structured output may return nested dicts as JSON strings.
        This validator handles both dict and str inputs.

        Args:
            value: Input value (dict or JSON string)

        Returns:
            Parsed dictionary

        Raises:
            ValueError: If value is invalid JSON string or wrong type
        """
        if isinstance(value, str):
            try:
                parsed: dict[str, Any] = json.loads(value)
                return parsed
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON schema string: {e}") from e
        elif isinstance(value, dict):
            return value
        else:
            raise ValueError(
                f"Expected dict or JSON string, got {type(value).__name__}"
            )


class InterfaceSchemaResponse(BaseModel):
    """Interface schema response from LLM."""

    interfaces: list[InterfaceSchemaDefinition] = Field(
        default_factory=list,
        description="List of interface schemas for all tasks",
    )


# Load prompt from YAML
_loader = PromptLoader.create_default()
_prompt_data = _loader.load_prompt("interface_schema")
INTERFACE_SCHEMA_SYSTEM_PROMPT = _prompt_data.get("system_prompt", "")

# Fallback to hardcoded prompt if YAML not found
if not INTERFACE_SCHEMA_SYSTEM_PROMPT:
    INTERFACE_SCHEMA_SYSTEM_PROMPT = """あなたはAPI設計の専門家です。
各タスクのインターフェーススキーマ（入力・出力）をJSON Schema形式で定義します。

## JSON Schema の原則

1. **明確な型定義**: すべてのフィールドに型を指定
2. **必須フィールド**: required で必須フィールドを明示
3. **詳細な説明**: description で各フィールドの目的を説明
4. **適切な制約**: pattern, minLength, maxLength, enum等で制約を設定

## インターフェース設計の原則

### 1. 入力スキーマ (input_schema)
- タスク実行に必要なすべてのパラメータを含む
- 前のタスクの出力を受け取る場合、そのフォーマットに合わせる
- デフォルト値が必要な場合は default で指定

### 2. 出力スキーマ (output_schema)
- タスク実行結果のフォーマットを明確に定義
- 次のタスクが使用しやすい構造にする
- エラー情報も含める（成功/失敗の判定が可能）

## JSON Schema の例

### 例1: Gmail検索タスク

**入力スキーマ**:
```json
{
  "type": "object",
  "properties": {
    "query": {
      "type": "string",
      "description": "検索キーワード",
      "minLength": 1
    },
    "max_results": {
      "type": "integer",
      "description": "最大取得件数",
      "default": 10,
      "minimum": 1,
      "maximum": 100
    },
    "date_from": {
      "type": "string",
      "description": "検索開始日 (YYYY-MM-DD形式)",
      "pattern": "^\\d{4}-\\d{2}-\\d{2}$"
    }
  },
  "required": ["query"],
  "additionalProperties": false
}
```

**出力スキーマ**:
```json
{
  "type": "object",
  "properties": {
    "success": {
      "type": "boolean",
      "description": "検索成功フラグ"
    },
    "emails": {
      "type": "array",
      "description": "検索結果のメール一覧",
      "items": {
        "type": "object",
        "properties": {
          "id": { "type": "string" },
          "subject": { "type": "string" },
          "from": { "type": "string" },
          "date": { "type": "string" },
          "snippet": { "type": "string" }
        },
        "required": ["id", "subject", "from", "date"]
      }
    },
    "count": {
      "type": "integer",
      "description": "取得件数"
    },
    "error_message": {
      "type": "string",
      "description": "エラーメッセージ（失敗時）"
    }
  },
  "required": ["success", "emails", "count"],
  "additionalProperties": false
}
```

### 例2: PDF生成タスク

**入力スキーマ**:
```json
{
  "type": "object",
  "properties": {
    "emails": {
      "type": "array",
      "description": "メール一覧（前のタスクの出力）",
      "items": {
        "type": "object",
        "properties": {
          "subject": { "type": "string" },
          "from": { "type": "string" },
          "date": { "type": "string" },
          "snippet": { "type": "string" }
        }
      }
    },
    "title": {
      "type": "string",
      "description": "PDFのタイトル",
      "minLength": 1
    }
  },
  "required": ["emails", "title"],
  "additionalProperties": false
}
```

**出力スキーマ**:
```json
{
  "type": "object",
  "properties": {
    "success": {
      "type": "boolean",
      "description": "PDF生成成功フラグ"
    },
    "pdf_path": {
      "type": "string",
      "description": "生成されたPDFファイルのパス"
    },
    "pdf_base64": {
      "type": "string",
      "description": "PDFファイルのBase64エンコード文字列"
    },
    "error_message": {
      "type": "string",
      "description": "エラーメッセージ（失敗時）"
    }
  },
  "required": ["success"],
  "additionalProperties": false
}
```

### 例3: 音声合成（TTS）タスク - **重要: OpenAI TTS API仕様**

**入力スキーマ**:
```json
{
  "type": "object",
  "properties": {
    "text": {
      "type": "string",
      "description": "音声合成するテキスト（最大4096文字）",
      "minLength": 1,
      "maxLength": 4096
    },
    "voice": {
      "type": "string",
      "description": "音声タイプ（OpenAI TTS APIで使用可能な値のみ）",
      "enum": ["alloy", "echo", "fable", "onyx", "nova", "shimmer"],
      "default": "alloy"
    },
    "file_name": {
      "type": "string",
      "description": "保存ファイル名（拡張子.mp3を含む）",
      "example": "podcast_episode_001.mp3"
    }
  },
  "required": ["text"],
  "additionalProperties": false
}
```

**重要**: `voice`パラメータは必ず`enum`で指定された値のみを使用してください。
- ✅ 正しい: "alloy", "echo", "fable", "onyx", "nova", "shimmer"
- ❌ 間違い: "ja-JP-Standard-A", "en-US-Wavenet-D"（これらはGoogle Cloud TTS形式で、本システムでは使用不可）

**出力スキーマ**:
```json
{
  "type": "object",
  "properties": {
    "success": {
      "type": "boolean",
      "description": "音声合成成功フラグ"
    },
    "audio_url": {
      "type": "string",
      "description": "音声ファイルのURL（Google Drive公開リンク）"
    },
    "file_id": {
      "type": "string",
      "description": "Google DriveファイルID"
    },
    "error_message": {
      "type": "string",
      "description": "エラーメッセージ（失敗時）"
    }
  },
  "required": ["success"],
  "additionalProperties": false
}
```

### 例4: Web検索タスク - **重要: Google検索API仕様**

**入力スキーマ**:
```json
{
  "type": "object",
  "properties": {
    "queries": {
      "type": "array",
      "description": "検索クエリのリスト（複数クエリ一括検索可能）",
      "items": {
        "type": "string"
      },
      "minItems": 1
    },
    "num": {
      "type": "integer",
      "description": "各クエリの検索結果件数",
      "default": 10,
      "minimum": 1,
      "maximum": 100
    }
  },
  "required": ["queries"],
  "additionalProperties": false
}
```

**重要**: `queries`パラメータは配列形式です。
- ✅ 正しい: `"queries": ["検索クエリ1", "検索クエリ2"]`
- ❌ 間違い: `"query": "検索クエリ"`（単数形は不可）

## インターフェース命名規則

- スネークケースを使用: `gmail_search_interface`
- タスクの目的を明確に表現: `{service}_{action}_interface`
- 例: `gmail_search_interface`, `pdf_generate_interface`, `drive_upload_interface`

## 出力形式

JSON形式で以下の構造で出力してください：

```json
{
  "interfaces": [
    {
      "task_id": "task_001",
      "interface_name": "gmail_search_interface",
      "description": "Gmail検索タスクのインターフェース",
      "input_schema": { ... },
      "output_schema": { ... }
    }
  ]
}
```

## 重要な注意事項

1. **JSON Schemaの妥当性**: 必ず正しいJSON Schema形式で出力
2. **タスク間の整合性**: 前のタスクのoutput_schemaと次のタスクのinput_schemaが一致
3. **エラーハンドリング**: すべての出力スキーマに `success` と `error_message` を含める
4. **additionalProperties**: 予期しないフィールドを防ぐため `false` に設定
5. **Regex pattern記述の注意**:
   - JSON文字列内では1回エスケープ: `"pattern": "^\\d{4}-\\d{2}-\\d{2}$"`
   - ❌ 間違い: `"pattern": "^\\\\d{4}..."` (4重エスケープ)
   - ✅ 正しい: `"pattern": "^\\d{4}..."` (2重エスケープ)
   - ✅ 正しい: `"pattern": "^[a-zA-Z0-9_]+$"` (通常の文字クラス)
   - ✅ 正しい: `"pattern": "^[\\p{L}\\p{N}\\s\\-\\.\\(\\)&]+$"` (Unicode property escapes)

## default値の生成ルール - Issue #340 CRITICAL

**重要**: default値は実際のデータ値であり、スキーマ定義ではありません。

❌ 禁止パターン（オブジェクト配列をdefaultに含める）:
```json
{
  "focus_points": {
    "type": "array",
    "items": {"type": "string"},
    "default": [{"type": "string", "description": "最新ニュース"}]
  }
}
```

✅ 正しいパターン（プリミティブ値の配列をdefaultに含める）:
```json
{
  "focus_points": {
    "type": "array",
    "items": {"type": "string"},
    "default": ["最新ニュース", "主要なトピック"]
  }
}
```

**ルール**:
- default値は items.type と一致する型の値のみ使用
- items.type="string" なら default は文字列配列 (例: `["a", "b"]`)
- items.type="number" なら default は数値配列 (例: `[1, 2, 3]`)
- items.type="boolean" なら default は真偽値配列 (例: `[true, false]`)
- オブジェクト（{...}）を配列の default に含めることは禁止
"""


def create_interface_schema_prompt(
    task_breakdown: list[dict],
) -> str:
    """Create interface schema definition prompt for LLM.

    Args:
        task_breakdown: Task breakdown result

    Returns:
        Formatted prompt string for LLM
    """
    import json

    return f"""# タスク分割結果

```json
{json.dumps(task_breakdown, ensure_ascii=False, indent=2)}
```

# 指示

上記の各タスクについて、インターフェーススキーマ（入力・出力）をJSON Schema形式で定義してください。

**重要**: 以下の点に注意してください：
1. タスク間の依存関係を考慮し、前のタスクの出力が次のタスクの入力に適切に渡される設計にする
2. すべての出力スキーマに `success` フィールドを含め、エラーハンドリングを可能にする
3. JSON Schemaの仕様に完全準拠する（type, properties, required, additionalPropertiesを適切に設定）

JSON形式で出力してください。
"""

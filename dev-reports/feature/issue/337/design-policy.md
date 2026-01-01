# Issue #337: タスクチェーン Ready-to-Use Output 原則の導入 - 設計方針書

## 1. 現状調査サマリ

### 1.1 現行アーキテクチャ

```
┌─────────────────────────────────────────────────────────────────┐
│                    Job Generation Flow                          │
├─────────────────────────────────────────────────────────────────┤
│  expertAgent (LangGraph)                                        │
│  ├── requirement_analysis_node                                  │
│  ├── task_breakdown_node                                        │
│  ├── interface_definition_node ◀── JSON Schema生成              │
│  ├── master_creation_node      ◀── TaskMaster/InterfaceMaster登録│
│  └── workflow_generation_node  ◀── GraphAI YAML生成             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    jobqueue (Data Model)                         │
├─────────────────────────────────────────────────────────────────┤
│  TaskMaster                    InterfaceMaster                  │
│  ├── id                        ├── id                           │
│  ├── name                      ├── name                         │
│  ├── description               ├── description                  │
│  ├── method, url               ├── input_schema (JSON Schema)   │
│  ├── headers, body_template    └── output_schema (JSON Schema)  │
│  ├── input_interface_id ───────────┘                            │
│  └── output_interface_id ──────────┘                            │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 問題の本質

GraphAI の `fetchAgent` body フィールド内では、文字列リテラル内に `:source.field` 参照を埋め込んでも補間されない:

```yaml
# ❌ 動作しない: subject は "検索結果サマリ: :source.user_input.query" という文字列になる
send_email:
  agent: fetchAgent
  inputs:
    body:
      subject: "検索結果サマリ: :source.user_input.query"
```

### 1.3 現行の回避策

`stringTemplateAgent` を使用して事前に文字列を構築:

```yaml
build_subject:
  agent: stringTemplateAgent
  inputs:
    query: :source.user_input.query
  params:
    template: "検索結果サマリ: ${query}"

send_email:
  agent: fetchAgent
  inputs:
    body:
      subject: :build_subject  # ← 構築済み文字列を参照
```

**問題点**: ワークフロー生成LLMがこのルールを常に守るとは限らない

### 1.4 インターフェース定義の現行フロー

```python
# interface_definition_node で InterfaceSchemaResponse を生成
class InterfaceSchemaDefinition(BaseModel):
    task_id: str
    interface_name: str
    description: str
    input_schema: dict[str, Any]   # JSON Schema V7
    output_schema: dict[str, Any]  # JSON Schema V7

# InterfaceMaster として jobqueue に登録
class InterfaceMaster(Base):
    id: str
    name: str
    description: str
    input_schema: dict[str, Any] | None  # JSON Schema V7
    output_schema: dict[str, Any] | None # JSON Schema V7
```

## 2. アーキテクチャ設計

### 2.1 proposed: derived_fields 拡張

**設計原則**: 上流タスクが「下流タスクが即座に使える形」でデータを出力する

```
┌─────────────────────────────────────────────────────────────────┐
│              InterfaceMaster (Extended)                         │
├─────────────────────────────────────────────────────────────────┤
│  id: str                                                        │
│  name: str                                                      │
│  description: str                                               │
│  input_schema: JSON Schema V7                                   │
│  output_schema: JSON Schema V7                                  │
│  └── x-derived-fields: DerivedFieldsSchema ◀── NEW              │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 データフロー

```
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│   Task A         │    │   Task B         │    │   Task C         │
│   (検索)          │    │   (要約)          │    │   (メール送信)    │
├──────────────────┤    ├──────────────────┤    ├──────────────────┤
│ output_schema:   │    │ output_schema:   │    │ input_schema:    │
│   query          │───▶│   summary_text   │───▶│   subject        │
│   results        │    │   key_points     │    │   body           │
│                  │    │ x-derived-fields:│    │   to             │
│                  │    │   email_subject  │    │                  │
│                  │    │   email_body     │    │                  │
└──────────────────┘    └──────────────────┘    └──────────────────┘
                              │
                              ▼
                    stringTemplateAgent で
                    derived_fields を構築
```

### 2.3 ワークフロー生成時の自動展開

```yaml
# derived_fields がある場合のワークフロー自動生成
nodes:
  source: {}

  # 元のタスク出力
  summarize:
    agent: fetchAgent
    inputs:
      url: http://localhost:8004/v1/chat
      body:
        text: :source.user_input.search_results

  # derived_fields 用ノード（自動生成）
  build_email_subject:
    agent: stringTemplateAgent
    inputs:
      query: :source.user_input.query           # source から取得
    params:
      template: "検索結果サマリ: ${query}"

  build_email_body:
    agent: stringTemplateAgent
    inputs:
      summary_text: :summarize.summary_text     # 同一タスクの出力から取得
      key_points: :summarize.key_points         # 同一タスクの出力から取得
    params:
      template: |
        ${summary_text}

        重要なポイント:
        ${key_points}

  # メール送信タスク
  send_email:
    agent: fetchAgent
    inputs:
      url: http://localhost:8004/v1/utility/gmail/send
      body:
        to: :source.user_input.to
        subject: :build_email_subject           # derived_field を参照
        body: :build_email_body                 # derived_field を参照
```

## 3. テンプレート変数のソース解決ルール

### 3.1 変数ソースの優先順位

テンプレート内の `{variable}` は以下の優先順位で解決される:

| 優先順位 | ソース | 説明 | 例 |
|----------|--------|------|-----|
| 1 | 同一タスクの `output_schema.properties` | タスク自身の出力フィールド | `{summary_text}` → `:summarize.summary_text` |
| 2 | `source.user_input` | ユーザー入力パラメータ | `{query}` → `:source.user_input.query` |
| 3 | 前タスクの出力（明示的指定） | 特定タスクの出力を参照 | `{@prev_task.field}` → `:prev_task.field` |

### 3.2 解決ルールの詳細

```yaml
# 要約タスクの output_schema
output_schema:
  properties:
    summary_text: { type: string }    # ← タスク自身の出力
    key_points: { type: string }      # ← タスク自身の出力
  x-derived-fields:
    email_subject:
      template: "検索結果サマリ: {query}"
      # {query} は properties に存在しない
      # → source.user_input.query から取得
    email_body:
      template: "{summary_text}\n\n重要ポイント:\n{key_points}"
      # {summary_text}, {key_points} は properties に存在
      # → 同一タスクの出力から取得
```

### 3.3 ワークフロー生成時の変数マッピング

```yaml
# LLM（ワークフロー生成ノード）が行う変数マッピング

# Step 1: テンプレート変数を抽出
#   template: "検索結果サマリ: {query}" → 変数: [query]

# Step 2: 変数ソースを決定
#   query ∈ output_schema.properties? → No
#   query ∈ source.user_input? → Yes → :source.user_input.query

# Step 3: stringTemplateAgent ノードを生成
build_email_subject:
  agent: stringTemplateAgent
  inputs:
    query: :source.user_input.query    # 解決されたソース
  params:
    template: "検索結果サマリ: ${query}"
```

### 3.4 GraphAI 参照形式の統一

本設計では以下の参照形式を使用する:

| 形式 | 用途 | 例 |
|------|------|-----|
| `:node_name.field` | ノードの出力フィールドを直接参照 | `:summarize.summary_text` |
| `:source.user_input.field` | ユーザー入力を参照 | `:source.user_input.query` |

**注意**: fetchAgent の result オブジェクト構造に依存する場合は `:node_name.result.field` 形式も使用可能だが、本設計では簡潔な `:node_name.field` 形式を推奨する。

## 4. 技術選定

### 4.1 実装方針

| 要素 | 選択 | 理由 |
|------|------|------|
| データモデル | InterfaceMaster 拡張 | 既存モデルへの後方互換性のある追加 |
| テンプレートエンジン | stringTemplateAgent | GraphAI 既存機能を活用 |
| スキーマ拡張 | JSON Schema 内 metadata | JSON Schema V7 の拡張ポイントを活用 |
| 自動展開 | プロンプトベース | ワークフロー生成LLMに処理を委任 |

### 4.2 代替案の検討

| 代替案 | 評価 | 採否 |
|--------|------|------|
| GraphAI 自体に文字列補間機能追加 | GraphAI コア変更が必要、影響範囲大 | ❌ |
| fetchAgent body の前処理 | 実行時オーバーヘッド、複雑性増加 | ❌ |
| derived_fields メタデータ方式 | LLMが認識可能、後方互換性あり | ✅ |

## 5. 設計パターン

### 5.1 derived_fields スキーマ

```python
from typing import Any
from pydantic import BaseModel, Field, ConfigDict

class DerivedFieldDefinition(BaseModel):
    """派生フィールドの定義"""
    model_config = ConfigDict(extra="forbid")

    template: str = Field(
        description="テンプレート文字列。{field_name} で元データを参照"
    )
    type: str = Field(
        default="string",
        description="生成される値の型"
    )
    description: str | None = Field(
        default=None,
        description="フィールドの説明"
    )
    source_mapping: dict[str, str] | None = Field(
        default=None,
        description="変数名 → ソースパスの明示的マッピング（オプション）"
    )
```

### 5.2 JSON Schema 内での表現

```json
{
  "type": "object",
  "properties": {
    "summary_text": { "type": "string", "description": "要約本文" },
    "key_points": { "type": "string", "description": "重要ポイント" }
  },
  "x-derived-fields": {
    "email_subject": {
      "template": "検索結果サマリ: {query}",
      "type": "string",
      "description": "メール件名として使用",
      "source_mapping": {
        "query": "source.user_input.query"
      }
    },
    "email_body": {
      "template": "{summary_text}\n\n重要なポイント:\n{key_points}",
      "type": "string",
      "description": "メール本文として使用"
    }
  }
}
```

**注意**: `source_mapping` はオプション。省略時は「3. テンプレート変数のソース解決ルール」に従って自動解決される。

### 5.3 プロンプト拡張パターン

interface_schema.py の INTERFACE_SCHEMA_SYSTEM_PROMPT に追加:

```markdown
## 派生フィールド (x-derived-fields) の設計

### 目的
下流タスクが文字列加工なしでデータを使用できるよう、上流タスクで「すぐ使える形」のデータを生成する。

### 使用ケース
| 下流タスク | 必要な derived_fields |
|-----------|----------------------|
| メール送信 | email_subject, email_body |
| Slack通知 | slack_title, slack_message |
| ファイル保存 | filename, file_description |

### テンプレート変数のソース解決
1. `{var}` が同一タスクの properties に存在 → 同一タスクの出力から取得
2. `{var}` が properties に存在しない → source.user_input から取得
3. 明示的に指定する場合 → source_mapping を使用

### 定義例
```json
{
  "output_schema": {
    "properties": {
      "summary_text": { "type": "string" }
    },
    "x-derived-fields": {
      "email_subject": {
        "template": "検索結果: {query}",
        "type": "string"
      }
    }
  }
}
```

### ワークフロー生成時の処理
1. x-derived-fields の各フィールドに対応する stringTemplateAgent ノードを生成
2. テンプレート変数のソースを解決し、inputs に設定
3. 下流タスクは `:build_{field_name}` で直接参照可能
```

## 6. エラーハンドリング設計

### 6.1 エラーケースと対処

| エラーケース | 検出タイミング | 対処方法 |
|-------------|---------------|----------|
| テンプレート変数が解決不能 | ワークフロー生成時 | エラーを返し、評価ノードで再試行 |
| 循環参照 | インターフェース定義時 | 参照深度チェックで拒否 |
| 無効なテンプレート構文 | インターフェース定義時 | バリデーションエラー |
| source_mapping のパスが不正 | ワークフロー生成時 | エラーログ出力、フォールバック |

### 6.2 テンプレート検証

```python
import re
from typing import Any

class TemplateValidationError(Exception):
    """テンプレート検証エラー"""
    pass

def validate_template(
    template: str,
    properties: dict[str, Any],
    source_mapping: dict[str, str] | None = None
) -> list[str]:
    """
    テンプレートを検証し、解決不能な変数を返す。

    Args:
        template: テンプレート文字列
        properties: output_schema.properties
        source_mapping: 明示的な変数マッピング

    Returns:
        解決不能な変数のリスト（空なら検証OK）
    """
    # テンプレート内の {variable} を抽出
    variables = re.findall(r'\{([^}]+)\}', template)

    unresolved = []
    for var in variables:
        # source_mapping で明示的に指定されている
        if source_mapping and var in source_mapping:
            continue
        # properties に存在する
        if var in properties:
            continue
        # source.user_input から取得可能と仮定（実行時検証）
        # ここでは警告のみ
        unresolved.append(var)

    return unresolved

def validate_derived_fields(output_schema: dict[str, Any]) -> list[dict[str, Any]]:
    """
    x-derived-fields 全体を検証。

    Returns:
        検証エラーのリスト
    """
    errors = []
    derived_fields = output_schema.get("x-derived-fields", {})
    properties = output_schema.get("properties", {})

    for field_name, field_def in derived_fields.items():
        template = field_def.get("template", "")
        source_mapping = field_def.get("source_mapping")

        unresolved = validate_template(template, properties, source_mapping)

        if unresolved:
            errors.append({
                "field": field_name,
                "unresolved_variables": unresolved,
                "message": f"変数 {unresolved} は properties に存在せず、source.user_input から取得されます"
            })

    return errors
```

### 6.3 評価ノードでのチェック

```python
def check_derived_fields_in_evaluator(state: dict) -> dict:
    """
    評価ノードで derived_fields の妥当性をチェック。

    下流タスクがメール送信等の場合、上流タスクに
    適切な derived_fields が定義されているか確認。
    """
    tasks = state.get("task_breakdown", [])
    interface_definitions = state.get("interface_definitions", {})

    issues = []

    for i, task in enumerate(tasks):
        task_type = task.get("task_type", "")

        # メール送信タスクの場合
        if "email" in task_type.lower() or "mail" in task_type.lower():
            # 前タスクの output_schema を確認
            if i > 0:
                prev_task_id = tasks[i - 1].get("task_id")
                prev_interface = interface_definitions.get(prev_task_id, {})
                output_schema = prev_interface.get("output_schema", {})
                derived = output_schema.get("x-derived-fields", {})

                if "email_subject" not in derived:
                    issues.append(f"タスク {prev_task_id} に email_subject が未定義")
                if "email_body" not in derived:
                    issues.append(f"タスク {prev_task_id} に email_body が未定義")

    if issues:
        return {
            "is_valid": False,
            "feedback": "derived_fields の定義が不足しています: " + ", ".join(issues)
        }

    return {"is_valid": True}
```

## 7. データモデル設計

### 7.1 InterfaceMaster 拡張（jobqueue）

```python
# jobqueue/app/models/interface_master.py

class InterfaceMaster(Base):
    """Interface master model for input/output type definitions."""

    __tablename__ = "interface_masters"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_schema: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, comment="JSON Schema V7 for input validation"
    )
    output_schema: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, comment="JSON Schema V7 for output validation"
    )
    # NOTE: derived_fields は output_schema 内の x-derived-fields として表現
    # DBスキーマ変更不要（JSON Schema の拡張属性を活用）
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
```

**設計判断**: `derived_fields` を独立カラムにせず、`output_schema` 内の `x-derived-fields` として表現
- **理由**: DBスキーマ変更不要、後方互換性維持、JSON Schema V7 の拡張ポイント活用

### 7.2 InterfaceSchemaDefinition 拡張（expertAgent）

```python
# expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/prompts/interface_schema.py

class DerivedFieldDefinition(BaseModel):
    """派生フィールド定義"""
    model_config = ConfigDict(extra="forbid")

    template: str = Field(description="テンプレート文字列。{field} で元データ参照")
    type: str = Field(default="string", description="生成値の型")
    description: str | None = Field(default=None)
    source_mapping: dict[str, str] | None = Field(
        default=None,
        description="変数名 → ソースパスの明示的マッピング"
    )

class InterfaceSchemaDefinition(BaseModel):
    """Interface schema for a single task."""
    model_config = ConfigDict(extra="forbid")

    task_id: str
    interface_name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    derived_fields: dict[str, DerivedFieldDefinition] = Field(
        default_factory=dict,
        description="派生フィールド定義（下流タスク用の加工済みデータ）"
    )
```

## 8. API設計

### 8.1 既存API互換性

InterfaceMaster API は変更不要（`x-derived-fields` は output_schema の一部）

```http
POST /api/v1/interface-masters
Content-Type: application/json

{
  "name": "summarize_interface",
  "description": "要約タスクのインターフェース",
  "input_schema": {
    "type": "object",
    "properties": {
      "text": { "type": "string" }
    }
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "summary_text": { "type": "string" },
      "key_points": { "type": "string" }
    },
    "x-derived-fields": {
      "email_subject": {
        "template": "サマリ: {summary_text}",
        "type": "string"
      }
    }
  }
}
```

### 8.2 derived_fields 抽出ユーティリティ

```python
def extract_derived_fields(output_schema: dict[str, Any]) -> dict[str, Any]:
    """output_schema から x-derived-fields を抽出"""
    return output_schema.get("x-derived-fields", {})

def has_derived_fields(output_schema: dict[str, Any]) -> bool:
    """derived_fields が存在するか確認"""
    derived = output_schema.get("x-derived-fields", {})
    return bool(derived)

def get_template_variables(template: str) -> list[str]:
    """テンプレートから変数を抽出"""
    import re
    return re.findall(r'\{([^}]+)\}', template)
```

## 9. セキュリティ設計

### 9.1 テンプレートインジェクション対策

```python
def validate_template_security(template: str) -> bool:
    """テンプレートのセキュリティ検証"""
    import re

    # 危険なパターンを検出
    dangerous_patterns = [
        r'\$\{.*\}',      # JavaScript テンプレートリテラル
        r'\{\{.*\}\}',    # Jinja2/Mustache テンプレート
        r'<%.*%>',        # ERB/ASP テンプレート
        r'<script',       # XSS
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, template, re.IGNORECASE):
            return False

    return True
```

### 9.2 スキーマ検証

- `x-derived-fields` 内のテンプレートは許可されたソースのみ参照可能
- 循環参照の検出と拒否
- テンプレート長の制限（最大1000文字）

## 10. パフォーマンス設計

### 10.1 ワークフロー生成オーバーヘッド

| 処理 | 追加コスト | 対策 |
|------|-----------|------|
| derived_fields 解析 | 無視できる（JSON パース） | - |
| stringTemplateAgent ノード追加 | ノード数増加 | 必要最小限の derived_fields |
| LLM プロンプト拡張 | トークン増加（~500） | プロンプト最適化 |

### 10.2 実行時オーバーヘッド

stringTemplateAgent は軽量（文字列置換のみ）のため、実行時影響は最小限

## 11. 設計判断とトレードオフ

### 11.1 主要な設計判断

| 判断 | 選択 | 代替案 | 理由 |
|------|------|--------|------|
| derived_fields の格納場所 | output_schema 内 x-derived-fields | 独立カラム | DBスキーマ変更不要、後方互換性 |
| テンプレート処理 | stringTemplateAgent | カスタムAgent | 既存機能活用、保守性 |
| 自動展開方式 | プロンプトベース | コード生成 | LLM の柔軟性活用 |
| 変数ソース解決 | 優先順位ルール + 明示的指定 | 完全明示的 | 使いやすさと柔軟性のバランス |

### 11.2 トレードオフ

| 利点 | 欠点 |
|------|------|
| 後方互換性完全維持 | JSON Schema 拡張属性は標準外 |
| DBスキーマ変更不要 | output_schema の複雑化 |
| LLMによる柔軟な処理 | LLMの動作不確実性 |
| 変数ソース自動解決 | 暗黙的な挙動による混乱の可能性 |

### 11.3 リスクと軽減策

| リスク | 軽減策 |
|--------|--------|
| LLMが derived_fields を無視 | 評価ノードでチェック、再試行 |
| テンプレート参照エラー | スキーマ検証で事前チェック |
| 複雑すぎるテンプレート | テンプレート長・複雑性の制限 |
| 変数ソースの曖昧さ | source_mapping で明示的指定を推奨 |

## 12. 実装フェーズ

### Phase 1: 基盤実装（推定工数: 1日）

1. InterfaceSchemaDefinition に derived_fields 追加
2. interface_schema.py プロンプト拡張
3. ワークフロー生成プロンプトに derived_fields 処理ルール追加
4. テンプレート検証ユーティリティ実装
5. 単体テスト作成

### Phase 2: 検証・改善（推定工数: 2日）

1. メール送信シナリオで E2E テスト
2. 評価ノードに derived_fields チェック追加
3. エッジケース対応（ネスト参照、複数ソース）
4. エラーハンドリング強化

### Phase 3: ドキュメント・リファクタリング（推定工数: 1日）

1. capabilities.yaml への反映
2. API ドキュメント更新
3. 使用ガイド作成
4. 変数ソース解決ルールのドキュメント化

## 13. 受入条件マッピング

| Issue受入条件 | 設計対応 |
|---------------|----------|
| derived_fields を含む output_interface が定義可能 | 7.2 InterfaceSchemaDefinition 拡張 |
| ワークフロー生成LLMが derived_fields を正しく出力に含める | 5.3 プロンプト拡張パターン |
| 下流タスクが文字列加工なしでデータを使用可能 | 2.3 ワークフロー自動展開 |
| テンプレート変数のソースが明確に解決される | 3. テンプレート変数のソース解決ルール |
| 不正なテンプレートが検出される | 6. エラーハンドリング設計 |

---

**作成日**: 2026-01-01
**更新日**: 2026-01-01
**関連Issue**: #337, #325
**レビュアー**: -

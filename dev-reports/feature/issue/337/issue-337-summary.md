# Issue #337: タスクチェーン Ready-to-Use Output 原則の導入

## 1. 背景

### 1.1 システム構成

```
┌─────────────────────────────────────────────────────────────────┐
│                    Job Generator (expertAgent)                   │
├─────────────────────────────────────────────────────────────────┤
│  LangGraph ノード:                                               │
│  ├── タスク分割ノード        → タスクを分解                       │
│  ├── インターフェース定義ノード → 各タスクの入出力スキーマを生成    │
│  ├── マスター作成ノード      → TaskMaster/InterfaceMaster を登録  │
│  └── ワークフロー生成ノード  → GraphAI YAML を生成                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    graphAiServer                                 │
│                    (ワークフロー実行エンジン)                      │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 ワークフロー生成の流れ

ユーザーが「Googleで検索して結果をメールで送信」とリクエストすると:

1. **タスク分割**: 検索 → 要約 → メール送信 の3タスクに分解
2. **インターフェース定義**: 各タスクの入出力スキーマを生成
3. **ワークフロー生成**: GraphAI YAML を生成
4. **実行**: graphAiServer がワークフローを実行

---

## 2. 課題

### 2.1 GraphAI fetchAgent の文字列補間制限

GraphAI の `fetchAgent` では、body フィールド内で文字列リテラルに参照を埋め込んでも補間されない。

```yaml
# ❌ これは動作しない
send_email:
  agent: fetchAgent
  inputs:
    body:
      to: :source.user_input.to
      subject: "検索結果サマリ: :source.user_input.query"  # 補間されない
      body: :summarize.summary_text
```

**実行結果**:
```
subject = "検索結果サマリ: :source.user_input.query"  ← 文字列がそのまま送信される
→ HTTP 422 エラー または 意図しないメール件名
```

### 2.2 現状の回避策の問題

現状、`stringTemplateAgent` を使用して事前に文字列を構築する必要がある:

```yaml
# 現状の回避策
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
      subject: :build_subject  # 構築済み文字列を参照
```

**問題点**:
- ワークフロー生成LLMがこのルールを常に守るとは限らない
- LLMへの指示が複雑化する
- ルール違反時に実行時エラーが発生

---

## 3. あるべき姿

### 3.1 Ready-to-Use Output 原則

**原則**: 上流タスクが「下流タスクがそのまま使える形」でデータを出力する

```
┌────────────────┐      ┌────────────────┐      ┌────────────────┐
│  検索タスク     │──▶│  要約タスク     │──▶│  メール送信     │
│                │      │                │      │                │
│ output:        │      │ output:        │      │ input:         │
│   query        │      │   summary_text │      │   subject ◀────│── そのまま使える
│   results      │      │   email_subject│      │   body   ◀────│── そのまま使える
│                │      │   email_body   │      │                │
└────────────────┘      └────────────────┘      └────────────────┘
                              ↑
                        derived_fields で
                        加工済みデータを提供
```

### 3.2 x-derived-fields の導入

インターフェース定義時に `x-derived-fields` を宣言し、ワークフロー生成時に自動的に `stringTemplateAgent` ノードを追加する。

```yaml
# インターフェース定義（LLMが生成）
output_schema:
  properties:
    summary_text: { type: string }
    key_points: { type: string }
  x-derived-fields:                    # ← 新規追加
    email_subject:
      template: "検索結果サマリ: {query}"
      type: string
    email_body:
      template: "{summary_text}\n\n重要ポイント:\n{key_points}"
      type: string
```

### 3.3 メカニズム

```
┌─────────────────────────────────────────────────────────────────┐
│  Step 1: インターフェース定義（LLMが設計）                        │
├─────────────────────────────────────────────────────────────────┤
│  要約タスクの output_schema:                                     │
│    x-derived-fields:           ◀── ① 「何が必要か」を宣言        │
│      email_subject:                                             │
│        template: "検索結果: {query}"                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 2: ワークフロー生成（自動展開）                             │
├─────────────────────────────────────────────────────────────────┤
│  build_email_subject:          ◀── ② 自動的にノードを生成        │
│    agent: stringTemplateAgent                                   │
│    inputs:                                                      │
│      query: :source.user_input.query                            │
│    params:                                                      │
│      template: "検索結果: ${query}"                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 3: 後続タスク（メール送信）                                 │
├─────────────────────────────────────────────────────────────────┤
│  send_email:                                                    │
│    inputs:                                                      │
│      body:                                                      │
│        subject: :build_email_subject  ◀── ③ そのまま使える       │
└─────────────────────────────────────────────────────────────────┘
```

### 3.4 テンプレート変数のソース解決ルール

テンプレート内の `{variable}` は以下の優先順位で解決される:

| 優先順位 | ソース | 説明 | 例 |
|----------|--------|------|-----|
| 1 | 同一タスクの `properties` | タスク自身の出力フィールド | `{summary_text}` → `:summarize.summary_text` |
| 2 | `source.user_input` | ユーザー入力パラメータ | `{query}` → `:source.user_input.query` |
| 3 | 明示的指定（source_mapping） | 特定ソースを指定 | `source_mapping: { "var": "path" }` |

**解決ルールの具体例**:

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

### 3.5 GraphAI 参照形式の統一

本設計では以下の参照形式を使用する:

| 形式 | 用途 | 例 |
|------|------|-----|
| `:node_name.field` | ノードの出力フィールドを直接参照 | `:summarize.summary_text` |
| `:source.user_input.field` | ユーザー入力を参照 | `:source.user_input.query` |

---

## 4. あるべき姿の具体例（机上シミュレーション結果）

### 4.1 タスク1: 検索→要約→メール送信（基本パターン）

**シナリオ**: Google検索結果を要約してメールで送信

**インターフェース定義**:
```yaml
# 要約タスクの output_schema
properties:
  summary_text: { type: string }
  key_points: { type: string }
x-derived-fields:
  email_subject:
    template: "検索結果サマリ: {query}"
    # {query} は properties にないため source.user_input.query から取得
  email_body:
    template: "{summary_text}\n\n重要ポイント:\n{key_points}"
    # {summary_text}, {key_points} は properties から取得
```

**自動生成されるワークフロー**:
```yaml
nodes:
  source: {}

  google_search:
    agent: fetchAgent
    inputs:
      url: http://localhost:8004/v1/utility/google_search
      body:
        queries: [:source.user_input.query]

  summarize:
    agent: fetchAgent
    inputs:
      url: http://localhost:8004/v1/chat
      body:
        messages:
          - role: user
            content: :google_search.results

  # ===== 自動生成ノード =====
  build_email_subject:
    agent: stringTemplateAgent
    inputs:
      query: :source.user_input.query       # source から取得（優先順位2）
    params:
      template: "検索結果サマリ: ${query}"

  build_email_body:
    agent: stringTemplateAgent
    inputs:
      summary_text: :summarize.summary_text  # 同一タスクから取得（優先順位1）
      key_points: :summarize.key_points      # 同一タスクから取得（優先順位1）
    params:
      template: "${summary_text}\n\n重要ポイント:\n${key_points}"
  # ===== ここまで自動生成 =====

  send_email:
    agent: fetchAgent
    inputs:
      url: http://localhost:8004/v1/utility/gmail/send
      body:
        to: :source.user_input.to
        subject: :build_email_subject   # ✅ 構築済み
        body: :build_email_body         # ✅ 構築済み

  output:
    agent: copyAgent
    inputs:
      result:
        success: :send_email.success
    isResult: true
```

**実行フロー**:
```
1. source: { query: "AI最新動向", to: "user@example.com" }
2. google_search: [検索結果...]
3. summarize: { summary_text: "AIの最新動向...", key_points: "1. LLM進化..." }
4. build_email_subject: "検索結果サマリ: AI最新動向"
5. build_email_body: "AIの最新動向...\n\n重要ポイント:\n1. LLM進化..."
6. send_email: { success: true }
```

| 判定 | 結果 |
|------|------|
| ✅ 成功 | メール件名・本文が正しく構築される |

---

### 4.2 タスク2: 検索→要約→複数送信先（メール + Slack + PDF）

**シナリオ**: 要約結果を3つの異なるサービスに送信

**インターフェース定義**:
```yaml
# 要約タスクの output_schema
properties:
  summary_text: { type: string }
x-derived-fields:
  email_subject:
    template: "検索結果サマリ: {query}"
  email_body:
    template: "{summary_text}"
  slack_title:
    template: ":mag: {query} の検索結果"
  slack_message:
    template: "{summary_text}"
  pdf_filename:
    template: "search_{query}.pdf"
  pdf_title:
    template: "検索結果レポート: {query}"
```

**自動生成されるノード**:
```yaml
build_email_subject: { agent: stringTemplateAgent, ... }
build_email_body: { agent: stringTemplateAgent, ... }
build_slack_title: { agent: stringTemplateAgent, ... }
build_slack_message: { agent: stringTemplateAgent, ... }
build_pdf_filename: { agent: stringTemplateAgent, ... }
build_pdf_title: { agent: stringTemplateAgent, ... }
```

| 判定 | 結果 |
|------|------|
| ✅ 成功 | 1つのタスクから複数の derived_fields を定義可能 |

---

### 4.3 タスク3: Gmail→本文抽出→TTS→Drive保存

**シナリオ**: メール本文をポッドキャスト化してDriveに保存

**インターフェース定義**:
```yaml
# 音声合成タスクの output_schema
properties:
  audio_base64: { type: string }
  duration_sec: { type: number }
x-derived-fields:
  drive_filename:
    template: "podcast_{date}_{email_subject}.mp3"
    source_mapping:
      date: "source.user_input.date"
      email_subject: "extract_body.subject"
  drive_description:
    template: "メール「{email_subject}」から生成（{duration_sec}秒）"
    source_mapping:
      email_subject: "extract_body.subject"
    # {duration_sec} は properties から自動取得
```

**自動生成されるワークフロー**:
```yaml
build_drive_filename:
  agent: stringTemplateAgent
  inputs:
    date: :source.user_input.date        # source_mapping で指定
    email_subject: :extract_body.subject  # source_mapping で指定
  params:
    template: "podcast_${date}_${email_subject}.mp3"

upload_to_drive:
  inputs:
    body:
      filename: :build_drive_filename
      content: :tts.audio_base64
```

| 判定 | 結果 |
|------|------|
| ✅ 成功 | チェーン途中のタスクでも derived_fields 定義可能、source_mapping で明示的指定も可能 |

---

### 4.4 タスク4: 検索→条件分岐→通知

**シナリオ**: 検索結果の有無で処理を分岐

```
検索 → 結果判定 → (結果あり) → 要約 → メール送信
                → (結果なし) → エラー通知
```

**インターフェース定義**:
```yaml
# 要約タスク（結果ありブランチ）
x-derived-fields:
  email_subject:
    template: "検索結果: {query}"
  email_body:
    template: "{summary_text}"

# エラー通知タスク（結果なしブランチ）
x-derived-fields:
  email_subject:
    template: "検索結果なし: {query}"
  email_body:
    template: "「{query}」の検索結果は見つかりませんでした。"
```

| 判定 | 結果 |
|------|------|
| ✅ 成功 | 各ブランチで独立して derived_fields を定義 |

---

### 4.5 タスク5: 既存タスクとの混在（後方互換性）

**シナリオ**: 既存ワークフローに新規タスクを追加

```yaml
# 既存タスクA（derived_fields なし）→ そのまま動作
output_schema:
  properties:
    data: { type: string }

# 新規タスクB（derived_fields あり）
output_schema:
  properties:
    result: { type: string }
  x-derived-fields:
    formatted_result:
      template: "結果: {result}"
```

| 判定 | 結果 |
|------|------|
| ✅ 成功 | 既存タスクは影響なし、後方互換性維持 |

---

### 4.6 注意が必要なケース

| ケース | 状況 | 対策 |
|--------|------|------|
| ネスト参照 `{result.data.title}` | Phase 1 では未対応 | フラット化した output を推奨 |
| LLMが derived_fields を無視 | 下流で補間問題発生 | 評価ノードでチェック追加 |
| 変数ソースが不明確 | 意図しないソースから取得 | source_mapping で明示的に指定 |
| 無効なテンプレート構文 | ワークフロー生成エラー | バリデーションで事前検出 |

---

### 4.7 シミュレーション結果サマリ

| # | パターン | 判定 | 備考 |
|---|----------|------|------|
| 1 | 基本メール送信 | ✅ | 主要ユースケース |
| 2 | 複数送信先 | ✅ | 1タスクから複数 derived_fields |
| 3 | チェーン途中 | ✅ | 任意の位置で定義可能 |
| 4 | 条件分岐 | ✅ | 各ブランチで独立定義 |
| 5 | 既存タスク混在 | ✅ | 後方互換性あり |

---

## 5. 実現方法（修正箇所）

### 5.1 修正ファイル一覧

| Phase | # | ファイル | 変更内容 |
|-------|---|----------|----------|
| 1 | 1 | `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/prompts/interface_schema.py` | `DerivedFieldDefinition` クラス追加 |
| 1 | 2 | `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/prompts/interface_schema.yaml` | プロンプトに x-derived-fields 説明追加 |
| 1 | 3 | `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/prompts/workflow_generation.yaml` | 自動展開ルール追加 |
| 1 | 4 | `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/utils/template_validator.py` | テンプレート検証ユーティリティ（新規） |
| 2 | 5 | `expertAgent/tests/unit/test_derived_fields.py` | 単体テスト新規作成 |
| 2 | 6 | `expertAgent/tests/integration/test_derived_fields_workflow.py` | 結合テスト新規作成 |
| 2 | 7 | `expertAgent/tests/acceptance/test_issue_337_acceptance.py` | 受入テスト新規作成 |
| 3 | 8 | `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/utils/config/expert_agent_capabilities.yaml` | 説明追加 |

### 5.2 修正不要ファイル

| コンポーネント | 理由 |
|---------------|------|
| `jobqueue/` | `x-derived-fields` は JSON 内に格納（DBスキーマ変更不要） |
| `graphAiServer/` | `stringTemplateAgent` は既存機能 |
| `myAgentDesk/` | オプショナル（表示のみ） |

---

### 5.3 修正詳細

#### 修正1: interface_schema.py

**ファイル**: `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/prompts/interface_schema.py`

```python
# 追加: DerivedFieldDefinition クラス
class DerivedFieldDefinition(BaseModel):
    """派生フィールド定義"""
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

# 変更: InterfaceSchemaDefinition に derived_fields 追加
class InterfaceSchemaDefinition(BaseModel):
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

#### 修正2: interface_schema.yaml

**ファイル**: `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/prompts/interface_schema.yaml`

```yaml
# 追加セクション
## 派生フィールド (x-derived-fields)

### 目的
下流タスクが文字列加工なしでデータを使用できるよう設計する。

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

### 定義方法
output_schema に x-derived-fields を追加:

{
  "output_schema": {
    "properties": { ... },
    "x-derived-fields": {
      "email_subject": {
        "template": "検索結果: {query}",
        "type": "string"
      }
    }
  }
}
```

#### 修正3: workflow_generation.yaml

**ファイル**: `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/prompts/workflow_generation.yaml`

```yaml
# 追加ルール
## x-derived-fields 処理ルール

タスクの output_schema に x-derived-fields がある場合:

1. 各 derived_field に対応する stringTemplateAgent ノードを生成
   - ノード名: build_{field_name}
   - inputs: テンプレート変数のソースを解決して設定
   - params.template: {var} を ${var} 形式に変換

2. 変数ソースの解決
   - {var} が properties に存在 → :task_name.var
   - {var} が properties に存在しない → :source.user_input.var
   - source_mapping で指定されている → 指定されたパス

3. 下流タスクでは生成されたノードを参照
   - 例: subject: :build_email_subject

### 変換例

x-derived-fields:
  email_subject:
    template: "結果: {query}"

↓ 自動変換

build_email_subject:
  agent: stringTemplateAgent
  inputs:
    query: :source.user_input.query
  params:
    template: "結果: ${query}"
```

#### 修正4: template_validator.py（新規）

**ファイル**: `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/utils/template_validator.py`

```python
import re
from typing import Any

def validate_template(
    template: str,
    properties: dict[str, Any],
    source_mapping: dict[str, str] | None = None
) -> list[str]:
    """
    テンプレートを検証し、解決不能な変数を返す。

    Returns:
        解決不能な変数のリスト（空なら検証OK）
    """
    variables = re.findall(r'\{([^}]+)\}', template)

    unresolved = []
    for var in variables:
        if source_mapping and var in source_mapping:
            continue
        if var in properties:
            continue
        # source.user_input から取得可能と仮定（警告のみ）
        unresolved.append(var)

    return unresolved

def validate_derived_fields(output_schema: dict[str, Any]) -> list[dict[str, Any]]:
    """x-derived-fields 全体を検証。"""
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

---

## 6. エラーハンドリング

### 6.1 エラーケースと対処

| エラーケース | 検出タイミング | 対処方法 |
|-------------|---------------|----------|
| テンプレート変数が解決不能 | ワークフロー生成時 | エラーを返し、評価ノードで再試行 |
| 循環参照 | インターフェース定義時 | 参照深度チェックで拒否 |
| 無効なテンプレート構文 | インターフェース定義時 | バリデーションエラー |
| source_mapping のパスが不正 | ワークフロー生成時 | エラーログ出力、フォールバック |

### 6.2 評価ノードでのチェック

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

        if "email" in task_type.lower() or "mail" in task_type.lower():
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
            "feedback": "derived_fields の定義が不足: " + ", ".join(issues)
        }

    return {"is_valid": True}
```

---

## 7. 期待効果

| 効果 | 説明 |
|------|------|
| **実行時エラー削減** | fetchAgent body 内の文字列補間問題を構造的に回避 |
| **LLM負担軽減** | 「stringTemplateAgent を使え」というルールをLLMが覚える必要がない |
| **タスク設計の明確化** | 各タスクが「何を出力すべきか」がスキーマで明示される |
| **再利用性向上** | 同じ要約タスクを別のJob（Slack通知、PDF生成等）でも使い回せる |
| **後方互換性** | 既存ワークフローは影響なし |
| **変数ソースの明確化** | 優先順位ルール + source_mapping で曖昧さを排除 |

---

## 8. 関連情報

| 項目 | 内容 |
|------|------|
| Issue | #337 |
| 親Issue | #325 (Job Generator 実行信頼性向上) |
| 関連Issue | #335 (capabilities.yaml Gmail送信APIスキーマ修正) |
| 設計方針書 | `dev-reports/feature/issue/337/design-policy.md` |
| アーキテクチャレビュー | `dev-reports/feature/issue/337/architecture-review.md` |
| 作業計画書 | `dev-reports/feature/issue/337/work-plan.md` |

---

**作成日**: 2026-01-01
**更新日**: 2026-01-01
**作成者**: Claude Code

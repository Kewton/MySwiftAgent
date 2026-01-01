# Issue #338 実装サマリ

**Issue**: #338 - タスクチェーン インターフェース契約強制メカニズムの導入
**作成日**: 2026-01-02
**関連Issue**: #337, #333

---

## 1. 背景

### 発生した障害

v1.28 のタスクチェーン実行（Google検索→要約生成）で、以下の3つの障害が連鎖的に発生:

| 問題 | 現象 | 影響 |
|------|------|------|
| **問題1** | ワークフローYAMLで `:execute_search.results` を参照したが存在せず `null` | Task 0 失敗 |
| **問題2** | GraphAI出力がネスト構造で、output_interface定義と不一致 | データ構造破損 |
| **問題3** | Task 1 が `:source.user_input.search_results` を参照したがパスが存在しない | Task 1 失敗 |

### 障害発生時のデータフロー

```
GraphAI実行結果:
{
  "results": {
    "source": {...},
    "execute_search": {
      "search_results": [...]    ← 正しいパス
    },
    "format_results": {...}
  }
}

ワークフローYAML（誤り）:
  inputs:
    results: :execute_search.results   ← 存在しない！
```

---

## 2. 課題

### 根本原因（5 Whys分析結果）

```
表層問題
├── 問題1: ワークフローYAMLノード参照エラー
├── 問題2: ワークフロー出力 ↔ output_interface不一致
└── 問題3: タスク間データパス不一致

        ↓ 5 Whys 分析

真因（Root Cause）
└── インターフェース契約の強制メカニズムが存在しない
    - input_interface / output_interface は「宣言」のみ
    - 実際のデータフローは契約を無視して動作
    - 違反を検出するバリデーションがない
```

### 現状の問題点

| 観点 | 現状 | 問題 |
|------|------|------|
| **出力ノード命名** | 自由（format_results等） | `_extract_graphai_output` が `output` を期待 |
| **output_interface** | 宣言のみ | 実際の出力は全ノード結果が返される |
| **タスク間データ連携** | テンプレート変数で参照 | 変換されていないデータを参照してパス不一致 |
| **API応答スキーマ** | LLMに提供されない | LLMが誤ったフィールド名を生成 |

---

## 3. あるべき姿

### 理想のデータフロー

```
[インターフェース定義]          [実際のデータフロー]

output_interface: {             GraphAI結果
  success: bool                      ↓
  search_results: [...]         ┌─────────────────────┐
  error_message: string         │ Interface Transformer│ ← 新規追加
}                               └─────────────────────┘
       ↓                              ↓
    強制される                   {
       ↓                          success: true,
input_interface: {                search_results: [...],
  search_results: [...]           error_message: ""
  summary_format: string        }
}                                    ↓
                               user_input: (変換後データ)
                                    ↓
                               :source.user_input.search_results
                                    ↓
                                 正常動作!
```

### あるべき姿の要件

| 要件 | 説明 |
|------|------|
| **出力ノード命名規約** | ワークフロー生成時に `output` ノード名を強制 |
| **output_interface変換** | GraphAI結果をoutput_interface定義に基づいて変換 |
| **API応答スキーマ提供** | ワークフロー生成時にLLMへAPI応答スキーマを提供 |
| **インターフェース整合性検証** | ジョブ生成時にタスク間の整合性をチェック |

---

## 4. あるべき姿の具体例（机上シミュレーション）

### シナリオ: Google検索 → 要約生成

#### Step 1: ワークフロー生成（改善後）

**入力**: TaskMaster定義
```yaml
task_name: "Google検索実行"
recommended_apis:
  - /v1/utility/google_search
output_interface:
  type: object
  properties:
    success: { type: boolean }
    search_results: { type: array }
    error_message: { type: string }
  required: [success, search_results]
```

**LLMへ提供されるコンテキスト**（改善点: API応答スキーマ含む）:
```yaml
# API Response Schema (自動注入)
/v1/utility/google_search:
  response:
    search_results: [{ title: str, link: str, knowledge: str }]
    search_results_count: int
    status: str
  note: "Use 'link' not 'url', 'knowledge' not 'snippet'"
```

**生成されるワークフローYAML**（改善点: `output` ノード強制）:
```yaml
nodes:
  source:
    value:
      user_input: :agentInputData.user_input

  execute_search:
    agent: fetchAgent
    inputs:
      url: "http://myvault:8003/v1/utility/google_search"
      body:
        query: :source.user_input.search_query

  output:                          # ← 改善: "format_results" ではなく "output"
    agent: copyAgent
    inputs:
      success: true
      search_results: :execute_search.search_results   # ← 改善: 正しいパス
      error_message: ""
    isResult: true
```

#### Step 2: GraphAI実行結果

```json
{
  "results": {
    "source": { "user_input": { "search_query": "AI最新動向" } },
    "execute_search": {
      "search_results": [
        { "title": "AI News", "link": "https://...", "knowledge": "..." }
      ],
      "search_results_count": 1,
      "status": "ok"
    },
    "output": {
      "success": true,
      "search_results": [...],
      "error_message": ""
    }
  }
}
```

#### Step 3: output_interface変換（新規処理）

**変換前**（`_extract_graphai_output` 結果）:
```json
{
  "success": true,
  "search_results": [...],
  "error_message": ""
}
```

**変換処理**:
```python
# _transform_to_interface の実行
output_interface = {
  "properties": {
    "success": {"type": "boolean"},
    "search_results": {"type": "array"},
    "error_message": {"type": "string"}
  },
  "required": ["success", "search_results"]
}

# フィールド探索（recursive戦略）
result = {
  "success": _find_field_value(raw_output, "success"),        # → true
  "search_results": _find_field_value(raw_output, "search_results"),  # → [...]
  "error_message": _find_field_value(raw_output, "error_message")     # → ""
}

# 必須フィールド検証
required = ["success", "search_results"]
missing = [f for f in required if result.get(f) is None]  # → []
# 検証OK
```

**変換後**（task.output_data に格納）:
```json
{
  "success": true,
  "search_results": [
    { "title": "AI News", "link": "https://...", "knowledge": "..." }
  ],
  "error_message": ""
}
```

#### Step 4: Task 1（要約生成）でのデータ参照

**Task 1 ワークフロー**:
```yaml
nodes:
  source:
    value:
      user_input: :agentInputData.user_input

  summarize:
    agent: openAIAgent
    inputs:
      prompt: |
        以下の検索結果を要約してください:
        {{:source.user_input.search_results}}
```

**テンプレート解決**:
```python
# template_resolver.py
# user_input = Task 0 の output_data（変換済み）
user_input = {
  "success": true,
  "search_results": [...],  # ← 正しくフラットな構造
  "error_message": ""
}

# :source.user_input.search_results → 正常に解決!
resolved = user_input["search_results"]
```

### シミュレーション結果比較

| 項目 | 改善前 | 改善後 |
|------|--------|--------|
| ワークフロー出力ノード | `format_results` | `output`（強制） |
| API参照パス | `:execute_search.results`（誤り） | `:execute_search.search_results`（正確） |
| Task 0 output_data | 全ノード結果（ネスト） | output_interface準拠（フラット） |
| Task 1 データ参照 | 失敗 | 成功 |
| タスクチェーン全体 | **失敗** | **成功** |

---

## 5. 実現方法（修正箇所）

### 修正ファイル一覧

| Phase | ファイル | 修正内容 |
|-------|---------|---------|
| **1** | `expertAgent/.../prompts/workflow_generation.yaml` | `output`ノード強制ルール追加 |
| **1** | `expertAgent/.../workflow_generation.py` | 生成後検証ロジック追加 |
| **2** | `jobqueue/app/core/worker.py` | `_transform_to_interface`, `_find_field_value` 追加 |
| **2** | `jobqueue/app/repositories/task_master.py` | output_interface取得 |
| **3** | `expertAgent/.../utils/workflow_helper.py` | API応答スキーマ取得関数 |
| **3** | `expertAgent/.../prompts/workflow_generation.yaml` | スキーマ注入プレースホルダー |
| **4** | `expertAgent/.../nodes/evaluator.py` | `check_interface_compatibility` 追加 |

### Phase 1: 出力ノード命名規約の強制

**ファイル**: `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/prompts/workflow_generation.yaml`

```yaml
# 追加ルール
system_prompt: |
  ...
  CRITICAL REQUIREMENT - OUTPUT NODE:
  - 出力ノードは必ず "output" という名前にする
  - isResult: true と組み合わせる
  - 他の名前（format_results, final_output等）は禁止

  正しい例:
  output:
    agent: copyAgent
    inputs:
      success: true
      search_results: :execute_search.search_results
    isResult: true
```

### Phase 2: output_interface変換レイヤー

**ファイル**: `jobqueue/app/core/worker.py`

```python
async def _execute_tasks(self, job: Job, tasks: list[Task]) -> None:
    for task in tasks:
        # 既存: タスク実行
        raw_output = await self._execute_single_task(task)

        # 新規: output_interface変換
        output_interface = await self._get_output_interface(task.master_id)
        task.output_data = _transform_to_interface(raw_output, output_interface)

        # 既存: 次タスクへのデータ連携
        ...


def _transform_to_interface(
    raw_output: dict,
    output_interface: dict | None
) -> dict:
    """output_interface定義に基づいてデータを変換"""
    if output_interface is None:
        return raw_output

    result = {}
    properties = output_interface.get("properties", {})

    for field_name, field_def in properties.items():
        strategy = _determine_search_strategy(field_name, field_def)
        value = _find_field_value(raw_output, field_name, strategy)
        result[field_name] = value

    # 必須フィールド検証
    required_fields = output_interface.get("required", [])
    missing = [f for f in required_fields if result.get(f) is None]
    if missing:
        logger.warning(f"[TRANSFORM] Missing required fields: {missing}")

    return result


def _find_field_value(
    data: dict,
    field_name: str,
    search_strategy: Literal["direct", "recursive", "path"] = "recursive"
) -> Any:
    """フィールド探索（3戦略サポート）"""
    if search_strategy == "direct":
        return data.get(field_name)

    if search_strategy == "recursive":
        return _recursive_search(data, field_name)

    if search_strategy == "path":
        return _path_based_search(data, field_name)

    return None
```

### Phase 3: API応答スキーマ提供

**ファイル**: `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/utils/workflow_helper.py`

```python
async def get_api_response_schemas(recommended_apis: list[str]) -> dict:
    """capabilities.yaml からAPI応答スキーマを取得"""
    schemas = {}
    for api_path in recommended_apis:
        schema = await _fetch_api_schema_from_capabilities(api_path)
        if schema:
            schemas[api_path] = schema
    return schemas


# ワークフロー生成コンテキストに注入
context = {
    "task_master": task_master,
    "api_response_schemas": await get_api_response_schemas(
        task_master.get("recommended_apis", [])
    )
}
```

### Phase 4: インターフェース整合性検証

**ファイル**: `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/nodes/evaluator.py`

```python
def check_interface_compatibility(tasks: list[dict]) -> list[str]:
    """タスク間インターフェース整合性検証"""
    warnings = []

    for i in range(len(tasks) - 1):
        current_output = tasks[i].get("output_interface", {})
        next_input = tasks[i + 1].get("input_interface", {})

        required_fields = next_input.get("required", [])
        available_fields = current_output.get("properties", {}).keys()

        for field in required_fields:
            if field not in available_fields:
                warnings.append(
                    f"Task {i+1} output missing '{field}' required by Task {i+2}"
                )

    return warnings


# evaluator_node で呼び出し
def evaluator_node(state: AgentState) -> AgentState:
    tasks = state.get("generated_tasks", [])

    # 既存: 3層検証
    ...

    # 新規: インターフェース整合性検証（4層目）
    interface_warnings = check_interface_compatibility(tasks)
    if interface_warnings:
        logger.warning(f"Interface compatibility issues: {interface_warnings}")
        state["warnings"].extend(interface_warnings)

    return state
```

---

## 実装スケジュール

> **重要**: Phase 1-2 は同一リリースで実装すること（アーキテクチャレビュー推奨）

| Phase | 内容 | 優先度 |
|-------|------|--------|
| **Phase 1-2** | 出力ノード命名規約 + 変換レイヤー | **同時実装必須** |
| Phase 3 | API応答スキーマ提供 | 高 |
| Phase 4 | インターフェース整合性検証 | 中 |

---

## 期待効果

| 効果 | 説明 |
|------|------|
| **タスクチェーン障害防止** | v1.28相当の障害が再発しない |
| **デバッグ容易化** | 変換処理のログで問題箇所を特定可能 |
| **LLM生成精度向上** | API応答スキーマ提供により正確なパス参照 |
| **早期問題検出** | ジョブ生成時に整合性問題を警告 |

---

**参照ドキュメント**:
- [根本原因分析レポート](./task-chain-failure-analysis.md)
- [設計方針書](./design-policy.md)
- [アーキテクチャレビュー](./architecture-review.md)

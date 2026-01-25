# Issue #340 根本原因分析レポート

## 概要

- **Issue番号**: #340
- **報告日時**: 2026-01-03
- **分析対象**: stringTemplateAgent が `[object Object]` に変換する問題
- **発見契機**: v1.38 ワークフロー実行時の HTTP 500 エラー

---

## 問題の再現

### エラー発生箇所
- **URL**: `http://localhost:8000/projects/proj_mjbjua2z7y65wy/workbenches/wb_1766969315404_udrhx79/runs/run_1767448760140_quihjja`
- **失敗タスク**: task_002 (検索結果の分析とサマリ生成)
- **エラーノード**: `generate_summary`

### エラー内容
```
HTTP 500 Error in generate_summary node
```

---

## 根本原因

### Interface Schema の default 値の問題

task_002 の `focus_points` フィールドの定義:

```json
{
  "focus_points": {
    "type": "array",
    "description": "分析時に重点を置くポイント",
    "items": {
      "type": "string"
    },
    "default": [
      {"type": "string", "description": "最新ニュース"},
      {"type": "string", "description": "主要なトピック"}
    ]
  }
}
```

**問題点**: `default` 値にスキーマオブジェクトが含まれている

**期待される正しい値**:
```json
{
  "default": ["最新ニュース", "主要なトピック"]
}
```

### 原因の流れ

```
[1] Interface Schema生成 (LLM)
     ↓ プロンプトにdefault値ルールがない
     ↓ LLMがスキーマオブジェクトをdefaultに設定
[2] sample_input生成 (_enum_or_default)
     ↓ default値を型チェックなしでそのまま返却
     ↓ オブジェクト配列がテストデータに混入
[3] workflow_tester (_detect_object_object_pattern)
     ↓ 検出はするが、直接エッジでフロー継続
[4] GraphAI実行 (stringTemplateAgent)
     ↓ オブジェクト配列を文字列化
     ↓ [object Object] に変換
[5] HTTP 500 エラー発生
```

---

## 識別された問題一覧

### P0 (Critical) - 即時対応必須

| # | 問題 | ファイル | 行番号 | 詳細 |
|---|------|---------|--------|------|
| 1 | Interface Schemaプロンプトにdefault値ルールがない | `jobTaskGeneratorAgents/prompts/interface_schema.py` | - | LLMがスキーマオブジェクトをdefault値として生成 |
| 2 | `_enum_or_default`がdefault値の型検証をしない | `workflowGeneratorAgents/nodes/sample_input_generator.py` | 181-196 | default値をそのまま返却、型チェックなし |
| 3 | sample_input_generator後に条件分岐がない | `workflowGeneratorAgents/agent.py` | 250 | 検出しても直接エッジでフロー継続 |

### P1 (High) - 優先対応

| # | 問題 | ファイル | 行番号 | 詳細 |
|---|------|---------|--------|------|
| 4 | test_data_regeneration.pyに配列制約ルールがない | `workflowGeneratorAgents/prompts/test_data_regeneration.py` | - | 再生成時も配列制約が適用されない |
| 5 | object_array_issuesがtest_data_regeneratorに渡されない | `workflowGeneratorAgents/nodes/test_data_regenerator.py` | 83 | test_data_issuesのみ参照 |
| 6 | LLM Evaluationプロンプトに配列制約ルールがない | `workflowGeneratorAgents/prompts/llm_evaluation.py` | - | 評価基準に配列要素型が含まれない |
| 7 | self_repair_nodeにobject_array_issuesフィードバックがない | `workflowGeneratorAgents/nodes/self_repair.py` | - | schema_validation_issuesのみ処理 |

### P2 (Medium) - 計画的対応

| # | 問題 | ファイル | 行番号 | 詳細 |
|---|------|---------|--------|------|
| 8 | workflow_validatorが配列要素型を検証しない | `workflowGeneratorAgents/nodes/workflow_validator.py` | - | array→listマッピングのみ |
| 9 | interface_definition.pyがdefault値の型を検証しない | `jobTaskGeneratorAgents/nodes/interface_definition.py` | - | normalize_json_schema_propertiesで未検証 |

---

## 問題詳細

### 問題1: Interface Schemaプロンプトにdefault値ルールがない

**ファイル**: `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/prompts/interface_schema.py`

**現状**: プロンプトにdefault値の生成ルールが含まれていない

**影響**: LLMがスキーマ定義オブジェクトをdefault値として生成してしまう

**推奨修正**:
```python
# プロンプトに追加すべきルール
"""
## default値の生成ルール
- default値は、そのフィールドの型に適合する実際のデータ値を設定すること
- 配列(array)型のdefaultには、items定義に適合する要素の配列を設定すること
- NG例: {"default": [{"type": "string", "description": "説明"}]}
- OK例: {"default": ["実際の値1", "実際の値2"]}
"""
```

---

### 問題2: `_enum_or_default`がdefault値の型検証をしない

**ファイル**: `expertAgent/aiagent/langgraph/workflowGeneratorAgents/nodes/sample_input_generator.py`
**行番号**: 181-196

**現在のコード**:
```python
def _enum_or_default(schema: dict[str, Any]) -> SchemaValue:
    ...
    default = schema.get("default")
    if default is not None:
        return default  # ← 型チェックなしで返却
```

**問題点**: default値がスキーマの型定義と一致するか検証していない

**推奨修正**:
```python
def _enum_or_default(schema: dict[str, Any]) -> SchemaValue:
    ...
    default = schema.get("default")
    if default is not None:
        # 配列の場合、要素がオブジェクトでないか検証
        if isinstance(default, list):
            items_type = schema.get("items", {}).get("type")
            if items_type == "string":
                # 全要素が文字列であることを検証
                if all(isinstance(item, str) for item in default):
                    return default
                # オブジェクトが含まれる場合は使用しない
                return None
        return default
```

---

### 問題3: sample_input_generator後に条件分岐がない

**ファイル**: `expertAgent/aiagent/langgraph/workflowGeneratorAgents/agent.py`
**行番号**: 250

**現在のコード**:
```python
# sample_input_generator -> workflow_tester (直接エッジ)
workflow.add_edge("sample_input_generator", "workflow_tester")
```

**問題点**: `has_object_array_errors=True`でも処理が継続する

**推奨修正**:
```python
# 条件分岐を追加
workflow.add_conditional_edges(
    "sample_input_generator",
    route_after_sample_input,
    {
        "continue": "workflow_tester",
        "error": "test_data_regenerator",  # エラー時は再生成へ
    }
)
```

---

### 問題4: test_data_regeneration.pyに配列制約ルールがない

**ファイル**: `expertAgent/aiagent/langgraph/workflowGeneratorAgents/prompts/test_data_regeneration.py`

**現状**: `TEST_DATA_REGENERATION_SYSTEM_PROMPT`に配列型制約が含まれていない

**推奨修正**:
```python
TEST_DATA_REGENERATION_SYSTEM_PROMPT = """
...
## 配列型の制約
- 配列(array)型フィールドの要素は、items定義で指定された型と一致させること
- items.type="string"の配列には、文字列のみを含めること
- オブジェクト配列（[{...}, {...}]）は禁止
...
"""
```

---

### 問題5: object_array_issuesがtest_data_regeneratorに渡されない

**ファイル**: `expertAgent/aiagent/langgraph/workflowGeneratorAgents/nodes/test_data_regenerator.py`
**行番号**: 83

**現在のコード**:
```python
test_data_issues=state.get("test_data_issues", [])  # object_array_issues未参照
```

**推奨修正**:
```python
test_data_issues=state.get("test_data_issues", []) + state.get("object_array_issues", [])
```

---

### 問題6: LLM Evaluationプロンプトに配列制約ルールがない

**ファイル**: `expertAgent/aiagent/langgraph/workflowGeneratorAgents/prompts/llm_evaluation.py`

**現状**: 評価基準に配列要素型の検証が含まれていない

**推奨修正**: 評価基準に配列要素型チェックを追加

---

### 問題7: self_repair_nodeにobject_array_issuesフィードバックがない

**ファイル**: `expertAgent/aiagent/langgraph/workflowGeneratorAgents/nodes/self_repair.py`

**現状**: `schema_validation_issues`のみ処理、`object_array_issues`は無視

**推奨修正**: object_array_issuesも修復対象として含める

---

### 問題8: workflow_validatorが配列要素型を検証しない

**ファイル**: `expertAgent/aiagent/langgraph/workflowGeneratorAgents/nodes/workflow_validator.py`

**現状**: `_json_schema_type_to_python`で`array`を`list`にマッピングするのみ

**推奨修正**: 配列要素の型検証を追加

---

### 問題9: interface_definition.pyがdefault値の型を検証しない

**ファイル**: `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/nodes/interface_definition.py`

**現状**: `normalize_json_schema_properties`でdefault値の型検証なし

**推奨修正**: default値がスキーマ型と一致することを検証

---

## 修正優先順位

```
[P0] 即時対応 (v1.39)
├── 問題1: Interface Schemaプロンプト修正
├── 問題2: _enum_or_default型検証追加
└── 問題3: 条件分岐追加

[P1] 次期対応 (v1.40)
├── 問題4: test_data_regenerationプロンプト修正
├── 問題5: object_array_issues引き渡し
├── 問題6: LLM Evaluationプロンプト修正
└── 問題7: self_repair_node修正

[P2] 計画的対応 (v1.41+)
├── 問題8: workflow_validator配列検証
└── 問題9: interface_definition検証
```

---

## 次のアクション

1. **Issue作成**: 各問題グループに対してIssueを作成
2. **P0対応**: v1.39で問題1-3を修正
3. **テスト追加**: 各修正に対する単体・結合・受入テストを追加
4. **回帰テスト**: 既存テスト全体の確認

---

## 関連ファイル

### 修正対象ファイル
- `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/prompts/interface_schema.py`
- `expertAgent/aiagent/langgraph/workflowGeneratorAgents/nodes/sample_input_generator.py`
- `expertAgent/aiagent/langgraph/workflowGeneratorAgents/agent.py`
- `expertAgent/aiagent/langgraph/workflowGeneratorAgents/prompts/test_data_regeneration.py`
- `expertAgent/aiagent/langgraph/workflowGeneratorAgents/nodes/test_data_regenerator.py`
- `expertAgent/aiagent/langgraph/workflowGeneratorAgents/prompts/llm_evaluation.py`
- `expertAgent/aiagent/langgraph/workflowGeneratorAgents/nodes/self_repair.py`
- `expertAgent/aiagent/langgraph/workflowGeneratorAgents/nodes/workflow_validator.py`
- `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/nodes/interface_definition.py`

### 参考ドキュメント
- `dev-reports/feature/issue/340/pm-auto-dev/progress-report.md`
- `dev-reports/feature/issue/340/work-plan.md`

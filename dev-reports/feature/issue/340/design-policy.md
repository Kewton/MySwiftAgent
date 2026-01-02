# 設計方針書: Issue #340 - stringTemplateAgent オブジェクト変換問題

## 現状調査サマリ

### 対象プロジェクト
- **プロジェクト名**: expertAgent, graphAiServer
- **主要モジュール**:
  - `expertAgent/aiagent/langgraph/workflowGeneratorAgents/` - ワークフロー生成
  - `graphAiServer/` - GraphAI実行環境

### 問題の概要

`stringTemplateAgent` がオブジェクト型の入力を `[object Object]` 文字列に変換してしまい、後続の LLM 呼び出しが失敗して HTTP 500 エラーが発生する。

```javascript
// 入力
{ search_results: [{title: "Sample", ...}], focus_points: ["ニュース", "トピック"] }

// 期待される出力
"検索結果: [{\"title\": \"Sample\", ...}] / ポイント: [\"ニュース\", \"トピック\"]"

// 実際の出力
"検索結果: [object Object] / ポイント: [object Object],[object Object]"
```

### 既存アーキテクチャパターン

| パターン | 使用箇所 | 目的 |
|---------|---------|------|
| **Multi-Stage Validation** | validator_node → llm_evaluator_node | 軽量検証 → 重量検証の段階的実行 |
| **Self-Repair Loop** | self_repair_node → generator_node | エラー時の自動修復 |
| **Schema Validation** | workflow_schema_validator_node | API型・フィールド名の事前検証 (Issue #333) |
| **Test Data Regeneration** | test_data_regenerator_node | テストデータ品質の改善 (Issue #305) |

### モジュール間依存関係

```
generator_node (YAML生成)
    ↓
schema_validator_node (API型・フィールド名検証) ← Issue #333
    ├→ [エラー時] self_repair_node
    └→ [成功時] sample_input_generator_node
        ↓
    workflow_tester_node (GraphAIServer実行)  ← ★ここで問題発生
        ↓
    validator_node → llm_evaluator_node
```

### 参照したドキュメント

| ドキュメント | 関連内容 |
|-------------|---------|
| `graphAiServer/docs/GRAPHAI_WORKFLOW_GENERATION_RULES.md` | stringTemplateAgent の使用ルール |
| `expertAgent/aiagent/langgraph/workflowGeneratorAgents/prompts/workflow_generation.py` | TYPE_VALIDATION_RULES |
| `expertAgent/aiagent/langgraph/workflowGeneratorAgents/nodes/workflow_schema_validator.py` | 既存バリデーションパターン |

### 設計上の制約

1. **stringTemplateAgent はJavaScript関数を評価しない** - `${JSON.stringify(data)}` は動作しない
2. **配列/オブジェクトは toString() で `[object Object]` になる** - JavaScript仕様
3. **:reference は inputs 内でのみ機能** - 文字列リテラル内では動作しない

---

## アーキテクチャ設計

### システム構成図

```mermaid
graph TD
    subgraph "ワークフロー生成フロー"
        G[generator_node] --> SV[schema_validator_node]
        SV --> SI[sample_input_generator_node]
        SI --> WT[workflow_tester_node]
        WT --> V[validator_node]
        V --> LE[llm_evaluator_node]
    end

    subgraph "Issue #340 対策レイヤー"
        SI -.-> TV[type_validator]
        TV -.-> |オブジェクト配列検出| TDR[test_data_regenerator_node]

        WT -.-> OV[output_validator]
        OV -.-> |[object Object]検出| ERR[error_feedback]
    end

    subgraph "既存バリデーション (Issue #333)"
        SV --> |型ミスマッチ| SR[self_repair_node]
        SR --> G
    end
```

### 対策レイヤー構成

| 層 | 名称 | 責務 | 実装場所 | フォールバック |
|----|------|------|---------|---------------|
| **Layer 1** | テストデータ型検証 | stringTemplateAgent入力フィールドのオブジェクト配列検出 | `sample_input_generator.py` | Layer 3 へ |
| **Layer 2** | プロンプト型制約 | LLMへの明示的な型制約指示 | `workflow_generation.py` | - |
| **Layer 3** | 実行時検出 | `[object Object]` パターン検出 | `workflow_tester.py` | エラー終了 |

### Layer間連携の明確化

```python
# state.py への追加
class ObjectArrayValidationResult(TypedDict):
    """オブジェクト配列検証結果（Layer間連携用）"""
    detected_at: Literal["layer1_type_validation", "layer3_runtime_detection"]
    detection_timestamp: str  # ISO 8601形式
    fallback_triggered: bool  # Layer 1で検出漏れ → Layer 3で検出
    issues: list[dict]  # 検出された問題リスト
```

---

## 技術選定

| カテゴリ | 選定技術 | 選定理由 | 既存との整合性 |
|---------|---------|---------|---------------|
| バリデーション | Pydantic + regex | 型検証と文字列パターン検出 | workflow_schema_validator と同様 |
| エラー報告 | 標準 issue dict 形式 | 既存の validation_errors との統合 | Issue #333 パターン踏襲 |
| 修復戦略 | test_data_regenerator 拡張 | 既存の再生成ループ活用 | Issue #305 パターン踏襲 |

---

## 設計パターン

### 採用パターン

#### 1. Early Detection Pattern（早期検出）

テストデータ生成時点で **stringTemplateAgent の入力として使用されるフィールド** のオブジェクト配列を検出し、プリミティブ型への変換を促す。

```python
# sample_input_generator.py への追加
def _get_string_template_input_fields(yaml_content: str) -> set[str]:
    """YAMLからstringTemplateAgentのinputフィールド名を抽出

    検出対象を絞り込み、誤検出を防止する。
    """
    workflow = yaml.safe_load(yaml_content)
    fields = set()
    for node_id, node_def in workflow.get("nodes", {}).items():
        if node_def.get("agent") == "stringTemplateAgent":
            inputs = node_def.get("inputs", {})
            for field_name, field_ref in inputs.items():
                # :source.user_input.xxx 形式から xxx を抽出
                if isinstance(field_ref, str) and field_ref.startswith(":source.user_input."):
                    fields.add(field_ref.split(".")[-1])
    return fields

def _validate_primitive_arrays(
    sample_input: dict,
    target_fields: set[str],  # stringTemplateAgent入力フィールドのみ
) -> list[dict]:
    """配列要素がプリミティブ型であることを検証

    Args:
        sample_input: テストデータ
        target_fields: stringTemplateAgentの入力として使用されるフィールド名
    """
    issues = []
    for field, value in sample_input.items():
        # stringTemplateAgent入力フィールドのみを検証
        if field not in target_fields:
            continue
        if isinstance(value, list):
            for i, item in enumerate(value):
                if isinstance(item, dict):
                    issues.append(_object_array_issue(field, i, type(item).__name__))
    return issues
```

#### 2. Output Sentinel Pattern（出力監視）

stringTemplateAgent の出力に `[object Object]` が含まれていないことを検証。

```python
# workflow_tester.py への追加
def _detect_object_object_pattern(execution_result: dict) -> list[dict]:
    """[object Object] パターンを再帰的に検出

    Returns:
        検出された問題のリスト
    """
    issues = []

    def _scan(obj: Any, path: str = "") -> None:
        if isinstance(obj, str) and "[object Object]" in obj:
            issues.append({
                "node_id": "workflow_execution",
                "issue_type": "object_object_detected",
                "message": f"[object Object] pattern detected at '{path}'",
                "severity": "error",
                "field_name": path,
                "actual_value": obj[:100] + "..." if len(obj) > 100 else obj,
                "suggestion": "Ensure all objects are serialized before passing to stringTemplateAgent",
            })
        elif isinstance(obj, dict):
            for key, value in obj.items():
                _scan(value, f"{path}.{key}" if path else key)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                _scan(item, f"{path}[{i}]")

    _scan(execution_result)
    return issues
```

#### 3. Schema Enrichment Pattern（スキーマ強化）

テストデータスキーマに `primitiveArray` 制約を追加。

```yaml
# input_interface.schema の拡張
focus_points:
  type: array
  items:
    type: string  # ← オブジェクトではなくプリミティブ
  x-primitive-only: true  # カスタム制約
```

---

## データモデル設計

### 検証Issue構造（既存パターン踏襲）

```python
# workflow_schema_validator.py の _issue() と同様
def _object_array_issue(
    field_name: str,
    index: int,
    actual_type: str,
) -> dict[str, Any]:
    return {
        "node_id": "sample_input",
        "issue_type": "object_in_array",
        "message": f"Array field '{field_name}' contains object at index {index}. "
                   f"stringTemplateAgent will convert this to '[object Object]'.",
        "severity": "error",
        "field_name": field_name,
        "expected_value": "primitive type (string, number, boolean)",
        "actual_value": actual_type,
        "suggestion": "Use primitive types in arrays, or serialize objects before passing to stringTemplateAgent",
    }
```

### State拡張

```python
# WorkflowGeneratorState への追加フィールド
class WorkflowGeneratorState(TypedDict):
    # 既存フィールド...

    # Issue #340: オブジェクト配列検証
    object_array_issues: list[dict]  # 検出されたオブジェクト配列問題
    has_object_array_errors: bool    # オブジェクト配列エラーの有無
    object_array_validation_result: ObjectArrayValidationResult | None  # Layer間連携情報
```

---

## API設計

### 既存APIへの影響

**影響なし** - 内部バリデーションの追加のみで、外部APIの変更は不要。

### 内部インターフェース

```python
# 新規追加関数
async def validate_sample_input_types(
    sample_input: dict,
    yaml_content: str,
) -> tuple[bool, list[dict], ObjectArrayValidationResult]:
    """
    テストデータの型検証

    Args:
        sample_input: テストデータ
        yaml_content: ワークフローYAML（stringTemplateAgent入力フィールド抽出用）

    Returns:
        (is_valid, issues, validation_result): バリデーション結果
    """
```

---

## ログ設計

### ログレベル定義

| 検出レイヤー | ログレベル | 理由 |
|-------------|-----------|------|
| **Layer 1** (テストデータ型検証) | `WARNING` | 再生成で回復可能、実行コスト発生前 |
| **Layer 3** (実行時検出) | `ERROR` | 実行コスト発生後、フォールバック検出 |
| **再生成成功時** | `INFO` | 正常回復の記録 |
| **再生成失敗時** | `ERROR` | 最終的な失敗 |

### ログフォーマット

```python
# Layer 1 検出時
logger.warning(
    "[OBJECT_ARRAY_VALIDATION] Detected object in array field '%s[%d]'. "
    "Triggering test data regeneration. "
    "(task_master_id=%s, field_type=%s)",
    field_name, index, task_master_id, actual_type
)

# Layer 3 検出時（フォールバック）
logger.error(
    "[OBJECT_OBJECT_DETECTION] Runtime detection of '[object Object]' pattern. "
    "Layer 1 validation missed this case. "
    "(task_master_id=%s, path=%s, fallback_triggered=True)",
    task_master_id, path
)

# 再生成成功時
logger.info(
    "[OBJECT_ARRAY_VALIDATION] Test data regeneration succeeded. "
    "(task_master_id=%s, regeneration_count=%d)",
    task_master_id, regeneration_count
)
```

---

## メトリクス設計

### 収集メトリクス

| メトリクス名 | 種別 | 説明 |
|-------------|------|------|
| `object_array_detection_total` | Counter | オブジェクト配列検出の総数 |
| `object_array_detection_layer` | Counter (labeled) | 検出レイヤー別カウント (`layer1`, `layer3`) |
| `test_data_regeneration_total` | Counter | テストデータ再生成の総数 |
| `test_data_regeneration_success` | Counter | テストデータ再生成成功数 |
| `object_object_fallback_detection` | Counter | Layer 3 フォールバック検出数（Layer 1 漏れ） |

### メトリクス実装

```python
# metrics.py への追加（既存のメトリクス基盤を活用）
from prometheus_client import Counter

OBJECT_ARRAY_DETECTION = Counter(
    "workflow_generator_object_array_detection_total",
    "Total number of object array detections",
    ["layer", "task_master_id"]
)

TEST_DATA_REGENERATION = Counter(
    "workflow_generator_test_data_regeneration_total",
    "Total number of test data regeneration attempts",
    ["success", "task_master_id"]
)

# 使用例
OBJECT_ARRAY_DETECTION.labels(layer="layer1", task_master_id=task_master_id).inc()
TEST_DATA_REGENERATION.labels(success="true", task_master_id=task_master_id).inc()
```

---

## セキュリティ設計

**影響なし** - 入力検証の強化は既存のセキュリティ境界内で実施。

---

## パフォーマンス設計

### 検証コスト

| 検証 | コスト | タイミング |
|------|-------|-----------|
| stringTemplateAgent入力フィールド抽出 | O(nodes) | sample_input生成前 |
| オブジェクト配列検出 | O(target_fields × array_size) | sample_input生成後 |
| `[object Object]`検出 | O(result_size) | workflow実行後 |

**影響**: 軽微（既存のスキーマ検証と同等）

---

## 設計判断とトレードオフ

### 判断1: 検出タイミング

| 選択肢 | メリット | デメリット |
|-------|---------|-----------|
| **A. テストデータ生成時（採用）** | 早期検出、再生成コスト削減 | 全ケースをカバーできない |
| B. YAML生成時 | ワークフロー構造も検証可能 | 複雑、誤検出リスク |
| C. 実行時のみ | 確実な検出 | 実行コストが無駄 |

**決定**: A を採用し、C をフォールバックとして併用

### 判断2: エラー時の対応

| 選択肢 | メリット | デメリット |
|-------|---------|-----------|
| **A. 自動再生成（採用）** | 人手不要 | 再生成でも解決しない場合あり |
| B. エラー終了 | 明確なフィードバック | 成功率低下 |

**決定**: A を採用（既存の test_data_regenerator パターン踏襲）

### 判断3: stringTemplateAgent の修正

| 選択肢 | メリット | デメリット |
|-------|---------|-----------|
| A. stringTemplateAgent 改修 | 根本解決 | 外部ライブラリ依存、影響範囲大 |
| **B. 入力検証強化（採用）** | 影響範囲限定、後方互換 | 完全な防止ではない |

**決定**: B を採用（stringTemplateAgent は @graphai/agents の外部ライブラリ）

### 判断4: 検出対象の絞り込み

| 選択肢 | メリット | デメリット |
|-------|---------|-----------|
| A. 全配列フィールド検証 | 漏れなし | 誤検出リスク高 |
| **B. stringTemplateAgent入力のみ（採用）** | 誤検出防止、パフォーマンス向上 | YAML解析が必要 |

**決定**: B を採用（誤検出による不要な再生成を防止）

---

## 実装計画

### Phase 1: テストデータ型検証（Layer 1）

| タスク | ファイル | 内容 |
|-------|---------|------|
| 1.1 | `sample_input_generator.py` | `_get_string_template_input_fields()` 追加 |
| 1.2 | `sample_input_generator.py` | `_validate_primitive_arrays()` 追加（対象絞り込み対応） |
| 1.3 | `test_data_regenerator.py` | 型エラー時の再生成ロジック強化 |
| 1.4 | テスト | 単体テスト追加 |

### Phase 2: プロンプト型制約（Layer 2）

| タスク | ファイル | 内容 |
|-------|---------|------|
| 2.1 | `workflow_generation.py` | TYPE_VALIDATION_RULES に配列型制約追加 |
| 2.2 | テスト | プロンプト統合テスト |

### Phase 3: 実行時検出（Layer 3）

| タスク | ファイル | 内容 |
|-------|---------|------|
| 3.1 | `workflow_tester.py` | `_detect_object_object_pattern()` 追加 |
| 3.2 | `validator.py` | 新規エラータイプの統合 |
| 3.3 | テスト | 結合テスト |

### Phase 4: 可観測性

| タスク | ファイル | 内容 |
|-------|---------|------|
| 4.1 | 各ノード | ログ出力追加（レベル定義に従う） |
| 4.2 | `metrics.py` | メトリクス定義追加 |
| 4.3 | テスト | ログ/メトリクス検証 |

### Phase 5: 受入テスト

| タスク | ファイル | 内容 |
|-------|---------|------|
| 5.1 | `tests/acceptance/test_issue_340_acceptance.py` | E2E検証 |

---

## 受入条件（Issue #340より）

- [ ] stringTemplateAgent にオブジェクトを渡した場合、`[object Object]` ではなく適切な文字列表現を生成
- [ ] テストデータ生成時にオブジェクト配列が不適切に使用されないようバリデーション
- [ ] workflow_tester で `[object Object]` パターンを検出した場合にエラーまたは警告を出力
- [ ] v1.36 で失敗した「検索結果の分析」タスクが成功することを確認

---

## 参照ドキュメント

| ドキュメント | 用途 |
|-------------|------|
| `docs/claude/04-quality-standards.md` | 品質基準 |
| `graphAiServer/docs/GRAPHAI_WORKFLOW_GENERATION_RULES.md` | GraphAI仕様 |
| `dev-reports/feature/issue/333/design-policy.md` | Issue #333 設計（参考） |
| `expertAgent/docs/API_REFERENCE.md` | API仕様 |

---

## 改訂履歴

| 日付 | 版 | 内容 |
|------|-----|------|
| 2025-01-03 | 1.0 | 初版作成 |
| 2025-01-03 | 1.1 | アーキテクチャレビュー反映（MF-1, MF-2, SF-1, SF-2） |

# V2 タスクチェーン 対策案

**作成日**: 2026-01-09
**関連Issue**: #342
**前提ドキュメント**: `v2-taskchain-root-cause-analysis.md`

---

## 1. 対策案サマリー

| 根本原因 | 対策案 | 実装コスト | 影響範囲 | 推奨 |
|---------|-------|----------|---------|-----|
| body_template二重ネスト | A1: コード修正 / A2: ドキュメント整合 | 低 / 中 | 全Task 0 | A1 |
| 出力ノード命名不整合 | B1: isResult検出 / B2: 命名統一 | 中 / 低 | 全タスク | B1+B2 |
| sourceパス参照不整合 | C1: LLMプロンプト修正 / C2: パス変換層 | 低 / 高 | 全ワークフロー | C1 |
| recipientフィールド欠落 | D1: 静的パラメータ機構 / D2: Job body拡張 | 中 / 低 | メール送信タスク | D1 |
| Interface変換の不完全性 | E1: 変換ロジック強化 / E2: isResult活用 | 中 / 中 | 全タスク | E1+E2 |

---

## 2. 根本原因1: body_template二重ネスト問題

### 現状の問題

```python
# master_manager.py:_build_body_template()
if order == 0:
    return {
        "user_input": "{{job.body}}",  # ← job.body全体を代入
    }
```

Job bodyが `{"user_input": {"query": "..."}, "model_name": "..."}` の場合、
graphAiServerへのリクエストが二重ネストになる。

### 対策案A1: コード修正（推奨）

**修正箇所**: `expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/registration/master_manager.py`

```python
def _build_body_template(self, order: int) -> dict[str, Any]:
    if order == 0:
        # 修正: user_input部分のみを取り出す
        return {
            "user_input": "{{job.body.user_input}}",
            "job_params": "{{job.body}}",  # job_paramsは全体を保持
        }
    else:
        return {
            "user_input": f"{{{{tasks[{order - 1}].output_data}}}}",
            "job_params": "{{job.body}}",
        }
```

**利点**:
- 既存のJob Master/ワークフローとの互換性維持
- 単一箇所の修正で全体に適用

**欠点**:
- 既存のジョブで`job.body.user_input`が存在しない場合にエラー

**影響範囲**: 新規作成されるTask Master

### 対策案A2: ドキュメント整合＋検証追加

Job body形式を`{"user_input": {...}}`に標準化し、検証を追加。

```python
def _build_body_template(self, order: int) -> dict[str, Any]:
    if order == 0:
        return {
            "user_input": "{{job.body.user_input}}",
            "job_params": "{{job.body}}",
        }
```

**追加**: Job作成時のバリデーション
```python
# jobs.py または job_masters.py
def validate_job_body(body: dict) -> None:
    if "user_input" not in body:
        raise ValueError("job.body must contain 'user_input' field")
```

---

## 3. 根本原因2: 出力ノード命名不整合

### 現状の問題

```python
# worker.py:_extract_graphai_output()
output_node = results.get("output")  # "output"固定
if output_node is None:
    return results  # 全結果を返す
```

ワークフローの出力ノード名が`format_output`の場合、抽出されない。

### 対策案B1: isResultノード動的検出（推奨）

**修正箇所**: `jobqueue/app/core/worker.py`

```python
def _extract_graphai_output(response_data: Any) -> Any:
    """Extract isResult node from GraphAI response."""
    if not isinstance(response_data, dict) or "results" not in response_data:
        return response_data

    results = response_data.get("results", {})
    logs = response_data.get("logs", [])

    # 1. logsからisResult:trueのノードを特定
    result_node_id = None
    for log in logs:
        if log.get("state") == "completed" and log.get("nodeId") not in ["source", "__loopIndex"]:
            # 最後に完了したノードを結果ノードとみなす
            result_node_id = log.get("nodeId")

    # 2. "output"ノードを優先的に探す（後方互換性）
    if "output" in results:
        return _extract_nested_result(results["output"])

    # 3. 特定されたノードから抽出
    if result_node_id and result_node_id in results:
        logger.info(f"[GRAPHAI_EXTRACT] Using result node: {result_node_id}")
        return _extract_nested_result(results[result_node_id])

    # 4. フォールバック: 全結果を返す
    logger.debug("[GRAPHAI_EXTRACT] No result node found, returning full results")
    return results

def _extract_nested_result(node_data: Any) -> Any:
    """Extract nested result if present."""
    if isinstance(node_data, dict) and "result" in node_data:
        return node_data["result"]
    return node_data
```

**利点**:
- 任意の出力ノード名に対応
- 後方互換性を維持

### 対策案B2: 出力ノード命名の統一

**修正箇所**: `expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/workflow_gen/yaml_generator.py`

LLM生成プロンプトに出力ノード命名規則を追加:

```
## 出力ノード命名規則
最終出力ノードは必ず `output` という名前を使用してください。

```yaml
output:
  agent: copyAgent
  inputs:
    result: :previous_node.result
  isResult: true
```
```

**利点**:
- シンプルな解決策
- 抽出ロジックの複雑化を回避

**欠点**:
- 既存ワークフローの修正が必要

---

## 4. 根本原因3: sourceパス参照不整合

### 現状の問題

graphAiServerのsource構造:
```javascript
source = {
  user_input: {...},  // 動的データ
  job_params: {...}   // 静的パラメータ
}
```

ワークフローでの参照:
- `:source.query` ❌ (旧形式)
- `:source.user_input.query` ✅ (正しい形式)

### 対策案C1: LLMプロンプト修正（推奨）

**修正箇所**: GRAPHAI_WORKFLOW_GENERATION_RULES.md + LLM生成プロンプト

```markdown
## sourceノード構造（重要）

`source`ノードは以下の構造を持ちます：

```yaml
source:
  user_input:   # 動的入力データ（前タスクの出力または初期入力）
    query: "検索キーワード"
    url: "https://example.com"
  job_params:   # 静的パラメータ（Job bodyから継承）
    recipient: "user@example.com"
```

### 参照方法

- ✅ `:source.user_input.query` - 動的データへのアクセス
- ✅ `:source.job_params.recipient` - 静的パラメータへのアクセス
- ❌ `:source.query` - 非推奨（直接アクセス不可）

### Issue #331 による改善

`job_params`は`user_input`にマージされるため、以下も有効：
- `:source.user_input.recipient` - job_paramsのデータも取得可能
```

**追加**: プロンプトビルダーへの組み込み

```python
# prompt_builder.py
SOURCE_STRUCTURE_GUIDE = """
## sourceノード参照ルール
1. 入力データは `:source.user_input.*` で参照
2. 静的パラメータは `:source.job_params.*` で参照
3. `:source.直接フィールド名` は使用禁止
"""
```

### 対策案C2: パス変換層の追加

graphAiServerにパス変換レイヤーを追加:

```javascript
// graphai.ts - resolveSourcePaths()
function resolveSourcePaths(graph_data: GraphData): void {
  for (const [nodeId, nodeConfig] of Object.entries(graph_data.nodes)) {
    if (nodeConfig.inputs) {
      for (const [key, value] of Object.entries(nodeConfig.inputs)) {
        if (typeof value === 'string' && value.startsWith(':source.')) {
          // :source.X を :source.user_input.X に変換
          if (!value.startsWith(':source.user_input.') &&
              !value.startsWith(':source.job_params.')) {
            const field = value.replace(':source.', '');
            nodeConfig.inputs[key] = `:source.user_input.${field}`;
            console.log(`✓ Path converted: ${value} → ${nodeConfig.inputs[key]}`);
          }
        }
      }
    }
  }
}
```

**利点**:
- 既存ワークフローとの完全互換性

**欠点**:
- 実行時オーバーヘッド
- 意図しない変換のリスク

---

## 5. 根本原因4: recipientフィールド欠落

### 現状の問題

メール送信に必要な`recipient`がデータフローに存在しない。

### 対策案D1: 静的パラメータ機構（推奨）

**修正箇所**: タスク分解・登録フロー

1. **タスク分解時にパラメータを抽出**

```python
# task_breakdown/decomposer.py
def _extract_static_params(task: dict, job_description: str) -> dict:
    """タスク説明からメールアドレス等の静的パラメータを抽出"""
    params = {}

    # メールアドレスの抽出
    email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
    emails = re.findall(email_pattern, job_description)
    if emails and task.get("type") == "email_send":
        params["recipient"] = emails[0]

    return params
```

2. **Job Masterのbodyにパラメータを含める**

```python
# master_manager.py
async def _create_job_master(self, ..., static_params: dict) -> str:
    body = {
        "user_input": {},  # 実行時に上書き
        **static_params,   # recipient等の静的パラメータ
    }
```

3. **ワークフローでの参照**

```yaml
send_email:
  body:
    to: :source.job_params.recipient  # 静的パラメータから取得
    subject: :source.user_input.email_subject
    body: :source.user_input.email_body
```

### 対策案D2: Job body拡張（即時対応）

**手動修正**: 既存Job Masterのbodyを更新

```bash
curl -X PUT "http://localhost:8001/api/v1/job-masters/jm_01KEH9NMY2WHPPSBFV9W5D2R3V" \
  -H "Content-Type: application/json" \
  -d '{
    "body": {
      "user_input": {},
      "recipient": "newtons.boiled.clock@gmail.com"
    }
  }'
```

---

## 6. 根本原因5: Interface変換の不完全性

### 現状の問題

`_transform_to_interface()`が正しく動作しない:
1. `_extract_graphai_output()`が全結果を返す
2. output_schemaのフィールドがトップレベルに存在しない

### 対策案E1: 変換ロジック強化（推奨）

**修正箇所**: `jobqueue/app/core/worker.py:_transform_to_interface()`

```python
def _transform_to_interface(
    raw_output: Any,
    output_interface: dict[str, Any] | None,
) -> dict[str, Any]:
    """Transform raw output to match output_interface definition."""
    if output_interface is None:
        return raw_output if isinstance(raw_output, dict) else {"value": raw_output}

    if not isinstance(raw_output, dict):
        return raw_output

    properties = output_interface.get("properties", {})
    result: dict[str, Any] = {}

    for field_name in properties:
        # 改善: より深い再帰検索
        value = _deep_search_field(raw_output, field_name, max_depth=10)
        result[field_name] = value

        if value is None:
            logger.warning(f"[TRANSFORM] Field not found: {field_name}")

    return result

def _deep_search_field(data: dict, field_name: str, max_depth: int = 10) -> Any:
    """深い再帰検索でフィールドを探す"""
    if max_depth <= 0:
        return None

    # 直接アクセス
    if field_name in data:
        return data[field_name]

    # ネストされた辞書を検索
    for key, value in data.items():
        if isinstance(value, dict):
            result = _deep_search_field(value, field_name, max_depth - 1)
            if result is not None:
                return result

    return None
```

### 対策案E2: isResultノードとの連携

**修正箇所**: 抽出と変換の統合

```python
async def _process_task_output(
    self,
    response_data: Any,
    output_interface: dict[str, Any] | None,
    logs: list[dict],
) -> dict[str, Any]:
    """タスク出力を処理（抽出→変換の統合）"""

    # 1. isResultノードを特定
    result_node_id = self._find_result_node(logs)

    # 2. 結果データを抽出
    results = response_data.get("results", {})
    if result_node_id and result_node_id in results:
        extracted = results[result_node_id]
    elif "output" in results:
        extracted = results["output"]
    else:
        extracted = results

    # 3. インターフェースに基づき変換
    return _transform_to_interface(extracted, output_interface)
```

---

## 7. 実装優先順位

### Phase 1: 緊急修正（1-2日）

| # | 対策 | ファイル | 作業内容 |
|---|-----|---------|---------|
| 1 | A1 | master_manager.py | body_template修正 |
| 2 | B2 | yaml_generator.py | 出力ノード名をoutputに統一 |
| 3 | D2 | jobqueue API | 既存Job Masterのbody更新 |
| 4 | **NEW** | taskchain-data-contract.md | データ契約ドキュメント作成 ✅ 完了 |

**Phase 1 完了条件**:
- [ ] 単体テスト全PASS
- [ ] 結合テスト全PASS
- [ ] 受入テスト AT-01, AT-02, AT-03 PASS
- [ ] 回帰テストで既存機能の動作確認

### Phase 2: 安定化（3-5日）

| # | 対策 | ファイル | 作業内容 |
|---|-----|---------|---------|
| 5 | B1 | worker.py | isResultノード動的検出 |
| 6 | C1 | RULES.md + プロンプト | source構造ドキュメント整備 |
| 7 | E1 | worker.py | 変換ロジック強化 |

**Phase 2 完了条件**:
- [ ] isResult検出の単体テストPASS
- [ ] format_output対応の結合テストPASS

### Phase 3: 設計改善（1-2週間）

| # | 対策 | ファイル | 作業内容 |
|---|-----|---------|---------|
| 8 | D1 | decomposer.py | 静的パラメータ抽出機構 |
| 9 | - | INPUT_SCHEMA.md | ドキュメント更新 |
| 10 | - | E2Eテスト | タスクチェーンテスト追加 |

**Phase 3 完了条件**:
- [ ] 全テストPASS
- [ ] E2Eテストで3タスクチェーン成功

---

## 8. リスクと緩和策

| リスク | 影響 | 緩和策 |
|-------|-----|-------|
| 既存ワークフローの破壊 | 高 | Phase 1でB2を慎重に適用、段階的移行 |
| body_template変更の副作用 | 中 | 既存Job Masterの互換性テスト |
| isResult検出の誤動作 | 中 | "output"ノードの優先探索で後方互換性確保 |

---

## 9. 検証計画

### 単体テスト追加

```python
# test_worker.py
def test_extract_graphai_output_with_format_output():
    """format_outputノードからの抽出テスト"""
    response = {
        "results": {
            "source": {},
            "google_search": {},
            "format_output": {"search_results": [...]}
        },
        "logs": [
            {"nodeId": "format_output", "state": "completed"}
        ]
    }
    result = _extract_graphai_output(response)
    assert "search_results" in result

def test_build_body_template_extracts_user_input():
    """body_templateがuser_inputのみを抽出するテスト"""
    manager = MasterManager(...)
    template = manager._build_body_template(0)
    assert template["user_input"] == "{{job.body.user_input}}"
```

### E2Eテスト追加

```python
# test_taskchain_e2e.py
async def test_three_task_chain_completes():
    """3タスクチェーンの完全実行テスト"""
    job_id = await create_job_from_master(...)
    await wait_for_job_completion(job_id, timeout=300)

    tasks = await get_job_tasks(job_id)
    assert all(t["status"] == "SUCCEEDED" for t in tasks)
```

---

## 10. 関連ドキュメント

### 分析・対策ドキュメント
- `v2-taskchain-root-cause-analysis.md` - 根本原因分析
- `task3-email-http422-analysis.md` - Task 3詳細分析
- `http-422-error-investigation-report.md` - 初期調査レポート

### 仕様・テストドキュメント
- `docs/spec/taskchain-data-contract.md` - **データ契約仕様書** ✅ 新規作成
- `v2-taskchain-regression-test-plan.md` - **回帰テスト計画** ✅ 新規作成

### 参照ドキュメント
- `graphAiServer/docs/GRAPHAI_WORKFLOW_GENERATION_RULES.md` - ワークフロー生成ルール
- `docs/arch/service-dependencies.md` - サービス依存関係

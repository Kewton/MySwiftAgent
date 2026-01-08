# 設計方針書: Issue #338 Bug2 - derived_fields バリデーションエラー

**作成日**: 2026-01-06
**Issue**: [#338 Task Chain Interface Contract Enforcement](https://github.com/Kewton/MySwiftAgent/issues/338)
**関連Issue**: #337 (derived_fields 機能追加)

---

## 概要

### 問題概要

`interface_definition` ノードで `derived_fields` の Pydantic バリデーションエラーが発生し、ワークフローが18回リトライして最終的に失敗する。

### エラー詳細

**Langfuse トレース**: `http://localhost:3001/project/cmi4ow4sq0006pw07ywz6lpmm/traces/6e408fc26542402bb6b4bc1e08b30cfc`

```
PydanticToolsParser ERROR:
3 validation errors for InterfaceSchemaResponse
interfaces.0.derived_fields Input should be a valid dictionary
  [type=dict_type, input_value='results -> task_002.input.search_results', input_type=str]
interfaces.1.derived_fields Input should be a valid dictionary
  [type=dict_type, input_value='email_subject -> task_00... -> task_003.input.body', input_type=str]
interfaces.2.derived_fields Input should be a valid dictionary
  [type=dict_type, input_value='message_id -> (logging/tracking)', input_type=str]
```

### ワークフロー影響

```
requirement_analysis → evaluator → interface_definition
                                          ↓
                                   [PydanticToolsParser ERROR]
                                          ↓
                                   schema_enrichment → evaluator
                                          ↓
                                   interface_definition (リトライ)
                                          ↓
                               ... 18回繰り返し ...
                                          ↓
                                   max_retries_exceeded → END
```

---

## 真因分析

### 作り込んだ真因

| ID | 真因 | 詳細 | 影響 |
|----|------|------|------|
| **1-A** | プロンプトに `derived_fields` のガイダンスがない | `INTERFACE_SCHEMA_SYSTEM_PROMPT` に `derived_fields` の説明・例が含まれていない | LLMが正しい形式を理解できず、推測で文字列形式を出力 |
| **1-B** | `derived_fields` に field_validator がない | `input_schema`, `output_schema` には `parse_json_schema` validator があるが、`derived_fields` にはない | 文字列入力が即座にバリデーションエラーになる |
| **1-C** | Issue #337 の実装が不完全 | スキーマ定義と検証関数は作成されたが、プロンプト更新が漏れた | 機能追加とLLMガイダンスが分離 |

### チェック機構で是正できなかった真因

| ID | 真因 | 詳細 | 影響 |
|----|------|------|------|
| **2-A** | Pydantic解析が evaluator より先に失敗 | `invoke_structured_llm` 内で Pydantic 解析が失敗 | evaluator の検証ロジックに到達しない |
| **2-B** | リトライにエラーフィードバックがない | `interface_definition_node` は最大3回リトライするが、同じプロンプトを使用 | LLMが「何が間違っていたか」を知らず同じ間違いを繰り返す |
| **2-C** | `check_derived_fields_for_downstream_tasks` が未使用 | 関数は `evaluator.py` に定義されているが、`evaluator_node` 内で呼び出されていない | 仮に呼び出されても、Pydantic 解析エラー後なので到達しない |

---

## 設計方針

### 改善案サマリー

| 優先度 | 改善案 | 効果 | 対象ファイル |
|--------|--------|------|-------------|
| 🔴 高 | プロンプトに derived_fields ガイダンス追加 | LLMが正しい形式を理解 | `prompts/interface_schema.py` |
| 🔴 高 | field_validator 追加 | 不正入力の graceful degradation | `prompts/interface_schema.py` |
| 🟡 中 | リトライ時エラーフィードバック | 自己修正の促進 | `nodes/interface_definition.py` |

---

### Phase 8-1: プロンプト改善（優先度: 高）

**対象ファイル**: `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/prompts/interface_schema.py`

**変更内容**: `INTERFACE_SCHEMA_SYSTEM_PROMPT` に以下のガイダンスを追加

```markdown
## derived_fields（派生フィールド）の定義

downstream タスクが直接使用できる事前フォーマット済みデータを定義します。
このフィールドは **オプション** です。必要な場合のみ定義してください。

### 形式（重要: 文字列ではなくオブジェクト形式で指定）

✅ **正しい形式**:
```json
{
  "derived_fields": {
    "email_subject": {
      "template": "検索結果: {query}",
      "type": "string",
      "description": "メール件名"
    },
    "summary_text": {
      "template": "{count}件のメールが見つかりました",
      "type": "string"
    }
  }
}
```

❌ **禁止形式（バリデーションエラーになります）**:
```json
{
  "derived_fields": "email_subject -> task_002.input.subject"
}
```

### derived_fields が不要な場合

derived_fields を使用しない場合は、空オブジェクトを指定するか、フィールド自体を省略してください：
```json
{
  "derived_fields": {}
}
```
```

**期待効果**: LLMが正しい形式を理解し、文字列形式での出力を防止

---

### Phase 8-2: field_validator 追加（優先度: 高）

**対象ファイル**: `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/prompts/interface_schema.py`

**変更内容**: `InterfaceSchemaDefinition` クラスに `derived_fields` 用の field_validator を追加

```python
@field_validator("derived_fields", mode="before")
@classmethod
def parse_derived_fields(cls, value: Any) -> dict[str, Any]:
    """Parse derived_fields with graceful degradation.

    If the LLM outputs a string instead of dict (common error),
    return empty dict to allow the workflow to continue.
    """
    if value is None:
        return {}
    if isinstance(value, str):
        logger.warning(
            "derived_fields received as string (%s...), using empty dict. "
            "LLM should output dict format: {'field_name': {'template': '...', 'type': '...'}}",
            value[:50] if len(value) > 50 else value,
        )
        return {}
    if isinstance(value, dict):
        return value
    logger.warning(
        "derived_fields has unexpected type %s, using empty dict",
        type(value).__name__,
    )
    return {}
```

**期待効果**: 不正な入力を graceful degradation で処理し、ワークフローが継続可能に

---

### Phase 8-3: リトライ時エラーフィードバック（優先度: 中）

**対象ファイル**: `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/nodes/interface_definition.py`

**変更内容**: リトライ時にエラー内容をプロンプトに追加

```python
for attempt in range(max_internal_retries):
    try:
        call_result = await invoke_structured_llm(
            messages=messages,
            response_model=InterfaceSchemaResponse,
            ...
        )
        break
    except StructuredLLMError as exc:
        last_error = exc
        logger.warning(
            "Interface schema generation attempt %d/%d failed: %s",
            attempt + 1,
            max_internal_retries,
            exc,
        )
        if attempt < max_internal_retries - 1:
            # 新規: エラーフィードバックをプロンプトに追加
            error_feedback = (
                f"\n\n## 前回の出力でエラーが発生しました\n"
                f"エラー内容: {exc}\n\n"
                f"**重要**: derived_fields は文字列ではなく、"
                f"オブジェクト形式で指定してください。\n"
                f"正しい形式: {{'field_name': {{'template': '...', 'type': 'string'}}}}"
            )
            messages = [
                messages[0],  # system prompt
                {"role": "user", "content": messages[1]["content"] + error_feedback},
            ]
            logger.info("Retrying with error feedback...")
            continue
```

**期待効果**: LLMが前回のエラーを理解し、自己修正できる

---

## 実装タスク

| タスク | 対象ファイル | 内容 | 優先度 | 状態 |
|--------|------------|------|--------|------|
| 8-1 | `prompts/interface_schema.py` | `derived_fields` ガイダンスをプロンプトに追加 | 🔴 高 | ✅ 完了 |
| 8-2 | `prompts/interface_schema.py` | `parse_derived_fields` field_validator 追加 | 🔴 高 | ✅ 完了 |
| 8-3 | `nodes/interface_definition.py` | リトライ時エラーフィードバック追加 | 🟡 中 | 未着手 |
| 8-4 | `tests/unit/test_interface_schema.py` | derived_fields バリデーションテスト追加 | 🔴 高 | ✅ 完了 |
| 8-5 | `tests/integration/test_issue_338_derived_fields.py` | E2E統合テスト追加 | 🟡 中 | ✅ 完了 |

---

## テスト計画

### 単体テスト

```python
# tests/unit/test_interface_schema.py

class TestDerivedFieldsValidator:
    """Issue #338 Phase 8: derived_fields validation tests."""

    def test_derived_fields_dict_passthrough(self):
        """Valid dict format should pass through unchanged."""
        data = {
            "task_id": "task_001",
            "interface_name": "test_interface",
            "description": "Test",
            "input_schema": {"type": "object"},
            "output_schema": {"type": "object"},
            "derived_fields": {
                "email_subject": {"template": "{query}", "type": "string"}
            },
        }
        result = InterfaceSchemaDefinition.model_validate(data)
        assert result.derived_fields == data["derived_fields"]

    def test_derived_fields_string_graceful_degradation(self):
        """String format should degrade to empty dict with warning."""
        data = {
            "task_id": "task_001",
            "interface_name": "test_interface",
            "description": "Test",
            "input_schema": {"type": "object"},
            "output_schema": {"type": "object"},
            "derived_fields": "results -> task_002.input.search_results",
        }
        result = InterfaceSchemaDefinition.model_validate(data)
        assert result.derived_fields == {}

    def test_derived_fields_none_to_empty_dict(self):
        """None should become empty dict."""
        data = {
            "task_id": "task_001",
            "interface_name": "test_interface",
            "description": "Test",
            "input_schema": {"type": "object"},
            "output_schema": {"type": "object"},
            "derived_fields": None,
        }
        result = InterfaceSchemaDefinition.model_validate(data)
        assert result.derived_fields == {}

    def test_derived_fields_empty_dict_passthrough(self):
        """Empty dict should pass through unchanged."""
        data = {
            "task_id": "task_001",
            "interface_name": "test_interface",
            "description": "Test",
            "input_schema": {"type": "object"},
            "output_schema": {"type": "object"},
            "derived_fields": {},
        }
        result = InterfaceSchemaDefinition.model_validate(data)
        assert result.derived_fields == {}

    def test_derived_fields_invalid_type_graceful_degradation(self):
        """Invalid types should degrade to empty dict."""
        data = {
            "task_id": "task_001",
            "interface_name": "test_interface",
            "description": "Test",
            "input_schema": {"type": "object"},
            "output_schema": {"type": "object"},
            "derived_fields": ["invalid", "list"],
        }
        result = InterfaceSchemaDefinition.model_validate(data)
        assert result.derived_fields == {}
```

### 結合テスト

```python
# tests/integration/test_issue_338_derived_fields.py

class TestIssue338DerivedFieldsIntegration:
    """Integration tests for derived_fields validation."""

    async def test_interface_definition_with_invalid_derived_fields(self):
        """Workflow should continue even if LLM outputs invalid derived_fields."""
        # Mock LLM to return string derived_fields
        # Verify workflow continues without crash
        ...

    async def test_retry_with_error_feedback(self):
        """Error feedback should help LLM correct its output."""
        # First call returns invalid format
        # Second call should receive error feedback and correct the format
        ...
```

---

## 設計判断

### 判断1: derived_fields の graceful degradation 戦略

| 選択肢 | メリット | デメリット | 採用 |
|--------|---------|-----------|------|
| **A. バリデーションエラーでワークフロー停止** | 厳密な検証 | ユーザー体験悪化、18回リトライの無駄 | - |
| **B. 空dictで続行 + 警告ログ** | 継続可能、ユーザー体験維持 | derived_fields 機能が使えない | ✅ 採用 |
| **C. 文字列をパースして変換** | 機能維持 | 実装複雑、エラーリスク高 | - |

**採用理由**:
- 選択肢Bは最も安全で、`derived_fields` はオプション機能のため空でも基本機能に影響なし
- 警告ログにより問題を可視化し、プロンプト改善の効果測定が可能

### 判断2: プロンプト改善 vs field_validator の優先順位

| アプローチ | 単独での効果 | 組み合わせ効果 |
|-----------|------------|--------------|
| プロンプト改善のみ | LLMの出力品質向上、根本解決 | - |
| field_validator のみ | エラー回避、但し機能未使用 | - |
| **両方実装** | **根本解決 + フォールバック** | ✅ 採用 |

**採用理由**:
- プロンプト改善で根本解決を目指しつつ、field_validator でフォールバックを提供
- 多層防御により、LLMの出力が不安定でもワークフローが継続可能

---

## 責任分析

| 層 | 責任 | 今後の対策 |
|----|------|----------|
| **設計層** | Issue #337 の設計時に「LLMへのガイダンス」が考慮されていなかった | 設計レビューでプロンプト影響を確認する手順を追加 |
| **実装層** | スキーマ追加時に対応するプロンプト更新が漏れた | チェックリストに「プロンプト更新」を必須項目として追加 |
| **テスト層** | 単体テストは成功したがE2E統合テストでプロンプト問題を検出できなかった | 実際のLLM呼び出しを含む統合テストを追加 |
| **レビュー層** | PRレビューでプロンプト未更新を検出できなかった | 「スキーマ変更=プロンプト更新必須」のレビュー観点を追加 |

---

## 参照ドキュメント

- [Issue #338](https://github.com/Kewton/MySwiftAgent/issues/338)
- [Issue #337](https://github.com/Kewton/MySwiftAgent/issues/337) - derived_fields 機能追加
- [root-cause-analysis.md](../root-cause-analysis.md)
- [design-policy.md](../design-policy.md) - 全体設計方針

---

## 実装詳細

### Phase 8-1 & 8-2 実装（2026-01-06）

**変更ファイル:**
- `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/prompts/interface_schema.py`
  - `derived_fields` ガイダンスを `INTERFACE_SCHEMA_SYSTEM_PROMPT` に追加
  - `parse_derived_fields` field_validator を `InterfaceSchemaDefinition` に追加
  - メトリクス収集用関数 `get_derived_fields_degradation_count()`, `reset_derived_fields_degradation_count()` を追加

**メトリクス収集:**
- グローバルカウンター `_derived_fields_degradation_count` で graceful degradation 発生回数を追跡
- 警告ログに `[degradation_count=N]` を含めて Langfuse で検索可能に

### Phase 8-4 & 8-5 実装（2026-01-06）

**追加テストファイル:**
- `expertAgent/tests/unit/test_interface_schema.py` (18テスト)
  - `TestDerivedFieldDefinition`: 3テスト
  - `TestInterfaceSchemaDefinitionDerivedFields`: 8テスト
  - `TestInterfaceSchemaDefinitionJsonSchema`: 3テスト
  - `TestInterfaceSchemaResponse`: 2テスト
  - `TestDegradationCounterFunctions`: 2テスト

- `expertAgent/tests/integration/test_issue_338_derived_fields.py` (7テスト)
  - `TestIssue338DerivedFieldsIntegration`: 4テスト
  - `TestDerivedFieldsEdgeCases`: 3テスト

**テスト結果:** 25テスト全てパス

---

## 変更履歴

| 日付 | バージョン | 変更内容 |
|------|-----------|---------|
| 2026-01-06 | 1.0 | 初版作成 |
| 2026-01-06 | 1.1 | Phase 8-1, 8-2, 8-4, 8-5 実装完了

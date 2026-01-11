# V2 バリデーター設計レビュー

## 概要

| 項目 | 値 |
|------|-----|
| Issue | #342 |
| 作成日 | 2026-01-09 |
| ステータス | 設計見直し必要 |
| 深刻度 | Critical |
| 影響範囲 | V2ワークフロー生成全体 |

---

## 1. 問題の発見経緯

### 1.1 発生した事象

V2で生成されたワークフロー（v1.86, v1.87）の実行が失敗：

```
HTTP 500: {"errors":{"01KEGF108SBW0AK4JGMTXRSQ69":{"message":"Invalid URL"}}}
```

### 1.2 調査結果

| バージョン | 生成方式 | 実行結果 |
|-----------|---------|---------|
| v1.85 | V1 (LLM via `/v1/aiagent/workflow/llm`) | **成功** |
| v1.86 | V2 (テンプレートフォールバック) | **失敗** |
| v1.87 | V2 (テンプレートフォールバック) | **失敗** |

### 1.3 V1 vs V2 YAML比較

**V1 (v1.85) - 動作する:**
```yaml
nodes:
  source: {}
  google_search:
    agent: fetchAgent
    inputs:
      url: ${EXPERTAGENT_BASE_URL}/aiagent-api/v1/utility/google_search
      method: POST
      body:
        query: :source.query
```

**V2 (v1.87) - 動作しない:**
```yaml
nodes:
  source: {}
  01KEGFTD772V8T8QVZTYB0SWWN:
    agent: fetchAgent
    inputs:
      data: :source.user_input  # URL, method, body がない
```

---

## 2. 根本原因分析

### 2.1 問題の構造

```
┌─────────────────────────────────────────────────────────────┐
│ V2 LLM生成                                                  │
│ ・${EXPERTAGENT_BASE_URL}/... を含むYAMLを生成              │
│ ・:source.query のようなパスを使用                          │
└────────────────────────┬────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ ValidationPipeline                                          │
│ ├─ AgentConstraintValidator                                 │
│ │   → ${EXPERTAGENT_BASE_URL} を環境変数として検出          │
│ │   → CRITICAL ERROR                                        │
│ └─ SourcePathRuleEngine                                     │
│     → :source.query を無効なパスとして検出                  │
│     → CRITICAL ERROR                                        │
└────────────────────────┬────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ 3回リトライ後、テンプレート生成にフォールバック             │
└────────────────────────┬────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ テンプレート生成 (_build_nodes, _generate_yaml)             │
│ ・URL, method, body を含まない壊れたYAMLを生成              │
└────────────────────────┬────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ 実行時: "Invalid URL" エラー                                │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 バリデーターの自己矛盾

| コンポーネント | 動作 | 場所 |
|--------------|------|------|
| LLMGeneratorSubWorkflow | `${EXPERTAGENT_BASE_URL}/...` を生成 | `llm_generator.py:310` |
| ParameterMapper | `${EXPERTAGENT_BASE_URL}/...` を生成 | `parameter_mapper.py:71` |
| Few-shot patterns | `${EXPERTAGENT_BASE_URL}/...` を使用 | `search_pattern.yaml:45` |
| **AgentConstraintValidator** | **上記をエラーとして検出** | `agent_constraint_validator.py:62` |

**V2は自分自身が生成するパターンを拒否している。**

---

## 3. 設計思想の誤り

### 3.1 誤った前提

**AgentConstraintValidator の設計時の前提:**
```python
# agent_constraint_validator.py:7-8
# - fetchAgent: Timeout in milliseconds, no environment variables in URLs
```

> 「GraphAI does not resolve environment variables at runtime」
> （GraphAIは実行時に環境変数を展開しない）

### 3.2 実際の動作

**graphAiServerは環境変数を展開する:**

```typescript
// graphAiServer/src/services/graphai.ts:86-109
const replacements: Record<string, string> = {
  '${EXPERTAGENT_BASE_URL}': process.env.EXPERTAGENT_BASE_URL || `http://localhost:${EXPERTAGENT_PORT}`,
};

for (const [placeholder, value] of Object.entries(replacements)) {
  url = url.replace(...);
}
console.log(`✓ Resolved environment variable in node '${nodeId}': ${url}`);
```

### 3.3 誤りの分類

| 分類 | 該当 | 説明 |
|------|------|------|
| アーキテクチャバグ | × | システム全体の設計問題ではない |
| **設計思想の誤り** | **○** | V1の動作メカニズムの誤解 |
| コンポーネント間理解不足 | ○ | graphAiServerの機能がexpertAgent側に伝わっていない |
| V1互換性テスト不足 | ○ | V1パターンでの動作確認をしていない |

---

## 4. 設計思想の見直し

### 4.1 現行の設計思想（誤り）

```
┌─────────────────────────────────────────────────────────────┐
│ 現行の設計思想                                               │
│                                                             │
│ 1. GraphAIは環境変数を展開しない                             │
│    → URLに ${VAR} を含めてはいけない                        │
│                                                             │
│ 2. :source.* は user_input または job_params が必須          │
│    → :source.query は無効                                   │
│                                                             │
│ 3. バリデーションは厳格であるべき                            │
│    → 少しでも疑わしいパターンはエラー                        │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 見直し後の設計思想

```
┌─────────────────────────────────────────────────────────────┐
│ 見直し後の設計思想                                           │
│                                                             │
│ 1. graphAiServerが環境変数を展開する                         │
│    → ${EXPERTAGENT_BASE_URL} は許可する                     │
│    → 許可リストで管理                                        │
│                                                             │
│ 2. V1互換のパスパターンを許可                                │
│    → :source.query, :source.results なども有効               │
│    → ただし :source のみ（フィールドなし）は無効             │
│                                                             │
│ 3. バリデーションはV1互換性を考慮                            │
│    → V1で動作するパターンは許可                              │
│    → 明らかに無効なパターンのみエラー                        │
└─────────────────────────────────────────────────────────────┘
```

### 4.3 設計原則の追加

```
┌─────────────────────────────────────────────────────────────┐
│ 追加する設計原則                                             │
│                                                             │
│ 原則1: 既存システムとの互換性を最優先                        │
│   - V1で動作するパターンはV2でも動作すべき                   │
│   - 新しいバリデーションルールは既存パターンを壊さない       │
│                                                             │
│ 原則2: コンポーネント間の動作を理解してから設計              │
│   - graphAiServer, expertAgent, jobqueue の連携を理解       │
│   - 環境変数展開、パス解決の仕組みを把握                     │
│                                                             │
│ 原則3: 自己生成パターンの検証                                │
│   - LLM/テンプレートが生成するパターンをバリデータがテスト   │
│   - 自己矛盾がないことを確認                                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. 設計変更案

### 5.1 変更一覧

| 変更ID | 対象ファイル | 変更内容 | 優先度 |
|--------|------------|---------|--------|
| DC-1 | `agent_constraint_validator.py` | 環境変数許可リスト追加 | P0 |
| DC-2 | `source_path_rule_engine.py` | V1互換パスパターン許可 | P0 |
| DC-3 | `yaml_generator.py` | テンプレートフォールバック修正 | P1 |
| DC-4 | `validation_pipeline.py` | バリデーション厳格度設定 | P2 |

### 5.2 DC-1: 環境変数許可リスト追加

**対象:** `expertAgent/aiagent/langgraph/jobGeneratorV2/validators/agent_constraint_validator.py`

**現行:**
```python
# Environment variable patterns in URLs
ENV_VAR_PATTERNS = [
    re.compile(r"\$\{[A-Z_][A-Z0-9_]*\}"),  # ${ENV_VAR}
    re.compile(r"\{\{[A-Z_][A-Z0-9_]*\}\}"),  # {{ENV_VAR}}
    re.compile(r"%[A-Z_][A-Z0-9_]*%"),  # %ENV_VAR%
]
```

**変更後:**
```python
# Environment variable patterns in URLs
ENV_VAR_PATTERNS = [
    re.compile(r"\$\{[A-Z_][A-Z0-9_]*\}"),  # ${ENV_VAR}
    re.compile(r"\{\{[A-Z_][A-Z0-9_]*\}\}"),  # {{ENV_VAR}}
    re.compile(r"%[A-Z_][A-Z0-9_]*%"),  # %ENV_VAR%
]

# Allowed environment variables (resolved by graphAiServer at runtime)
# See: graphAiServer/src/services/graphai.ts:86-109
ALLOWED_ENV_VARS = {
    "${EXPERTAGENT_BASE_URL}",  # Resolved to http://localhost:8004 or configured URL
}
```

**validate_fetch_agent メソッド変更:**
```python
def validate_fetch_agent(self, config: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    # ... timeout validation ...

    # Validate URL for environment variables
    inputs = config.get("inputs", {})
    url = inputs.get("url", "")

    if isinstance(url, str) and url:
        for pattern in ENV_VAR_PATTERNS:
            match = pattern.search(url)
            if match:
                env_var = match.group(0)
                # Check if it's an allowed environment variable
                if env_var not in ALLOWED_ENV_VARS:
                    errors.append(
                        f"URL contains unknown environment variable: '{env_var}'. "
                        f"Allowed: {', '.join(ALLOWED_ENV_VARS)}. "
                        "graphAiServer resolves these at runtime."
                    )
                break

    return errors
```

### 5.3 DC-2: V1互換パスパターン許可

**対象:** `expertAgent/aiagent/langgraph/jobGeneratorV2/validators/source_path_rule_engine.py`

**現行:**
```python
VALID_SOURCE_PREFIXES = [
    ":source.user_input.",
    ":source.job_params.",
]
```

**変更後:**
```python
# V1 compatible: :source.fieldName (e.g., :source.query, :source.results)
# V2 extended: :source.user_input.fieldName, :source.job_params.fieldName
VALID_SOURCE_PATTERNS = [
    # V2 explicit patterns (preferred)
    re.compile(r"^:source\.user_input\.[\w\.]+$"),
    re.compile(r"^:source\.job_params\.[\w\.]+$"),
    # V1 compatible patterns (legacy support)
    re.compile(r"^:source\.[\w]+$"),  # :source.query, :source.results
    re.compile(r"^:source\.[\w]+\.[\w\.]+$"),  # :source.query.field
]

# Invalid patterns (must have at least one field after :source)
INVALID_SOURCE_PATTERNS = [
    re.compile(r"^:source$"),  # :source alone is invalid
    re.compile(r"^:source\.$"),  # :source. with trailing dot
]
```

**validate_path メソッド変更:**
```python
def validate_path(self, path: str | None) -> tuple[bool, str]:
    # ... existing validation ...

    # Check source references
    if path.startswith(":source"):
        # Check for invalid patterns first
        for pattern in INVALID_SOURCE_PATTERNS:
            if pattern.match(path):
                return False, (
                    f"Invalid source path '{path}'. "
                    ":source must be followed by a field name "
                    "(e.g., :source.query, :source.user_input.data)"
                )

        # Check for valid patterns
        for pattern in VALID_SOURCE_PATTERNS:
            if pattern.match(path):
                return True, ""

        # If no pattern matched, it's invalid
        return False, (
            f"Invalid source path '{path}'. "
            "Valid formats: :source.fieldName, :source.user_input.field, :source.job_params.field"
        )

    return True, ""
```

### 5.4 DC-3: テンプレートフォールバック修正

**対象:** `expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/workflow_gen/yaml_generator.py`

**現行 (_build_nodes):**
```python
def _build_nodes(self, task_master_ids: list[str], interfaces: dict) -> list[WorkflowNodeDefinition]:
    nodes = []
    for idx, tm_id in enumerate(task_master_ids):
        task_id = tm_id.replace("tm_", "") if tm_id.startswith("tm_") else tm_id

        if idx == 0:
            inputs = {"data": ":source.user_input"}  # 不完全
        else:
            inputs = {"data": f":source.{prev_task_id}"}

        node = WorkflowNodeDefinition(
            node_id=task_id,
            agent="fetchAgent",  # URLなし
            inputs=inputs,
            params={"task_master_id": tm_id},
            is_result=idx == len(task_master_ids) - 1,
        )
        nodes.append(node)
    return nodes
```

**変更後:**
```python
def _build_nodes(
    self,
    task_master_ids: list[str],
    interfaces: dict[str, InterfaceSchema],
    task_id_mapping: TaskIdMapping | None = None,
) -> list[WorkflowNodeDefinition]:
    """Build V1-compatible node definitions with proper fetchAgent configuration."""
    nodes = []

    for idx, tm_id in enumerate(task_master_ids):
        task_id = tm_id.replace("tm_", "") if tm_id.startswith("tm_") else tm_id
        normalized_task_id = _normalize_task_id(tm_id, task_id_mapping)
        interface = interfaces.get(normalized_task_id)

        # Get API endpoint from interface
        api_endpoint = self._get_api_endpoint(interface)

        # Build V1-compatible inputs
        if idx == 0:
            body_inputs = self._build_initial_body(interface)
        else:
            prev_task_id = task_master_ids[idx - 1].replace("tm_", "")
            body_inputs = self._build_chained_body(interface, prev_task_id)

        inputs = {
            "url": f"${{EXPERTAGENT_BASE_URL}}{api_endpoint}",
            "method": "POST",
            "body": body_inputs,
        }

        node = WorkflowNodeDefinition(
            node_id=task_id,
            agent="fetchAgent",
            inputs=inputs,
            params={"task_master_id": tm_id},
            is_result=idx == len(task_master_ids) - 1,
            timeout=30000,  # 30 seconds default
        )
        nodes.append(node)

    return nodes

def _get_api_endpoint(self, interface: InterfaceSchema | None) -> str:
    """Get API endpoint path from interface or return default."""
    if interface and interface.recommended_api:
        # Extract path from recommended_api (e.g., "/v1/utility/google_search")
        return interface.recommended_api
    return "/aiagent-api/v1/utility/echo"  # Safe default

def _build_initial_body(self, interface: InterfaceSchema | None) -> dict:
    """Build request body for first task using source references."""
    if interface and interface.input_schema:
        body = {}
        for field in interface.input_schema.get("required", []):
            body[field] = f":source.{field}"
        return body
    return {"data": ":source.user_input"}

def _build_chained_body(self, interface: InterfaceSchema | None, prev_task_id: str) -> dict:
    """Build request body for chained task using previous task output."""
    return {"data": f":{prev_task_id}.result"}
```

### 5.5 DC-4: バリデーション厳格度設定

**対象:** `expertAgent/aiagent/langgraph/jobGeneratorV2/pipeline/validation_pipeline.py`

**追加:**
```python
from enum import Enum

class ValidationStrictness(Enum):
    """Validation strictness levels."""
    STRICT = "strict"       # All rules enforced (for new development)
    V1_COMPATIBLE = "v1"    # Allow V1 patterns (default for production)
    PERMISSIVE = "permissive"  # Minimal validation (for debugging)

class ValidationPipeline:
    def __init__(
        self,
        validators: list[WorkflowValidator] | None = None,
        observer: "ValidationObserver | None" = None,
        strictness: ValidationStrictness = ValidationStrictness.V1_COMPATIBLE,
    ):
        self.strictness = strictness

        if validators is None:
            self.validators = self._create_default_validators()
        else:
            self.validators = validators

        self.observer = observer

    def _create_default_validators(self) -> list[WorkflowValidator]:
        """Create validators based on strictness level."""
        if self.strictness == ValidationStrictness.PERMISSIVE:
            return []  # No validation

        validators = [
            SourcePathRuleEngine(v1_compatible=self.strictness == ValidationStrictness.V1_COMPATIBLE),
            AgentConstraintValidator(allow_known_env_vars=self.strictness == ValidationStrictness.V1_COMPATIBLE),
        ]

        return validators
```

---

## 6. テスト計画

### 6.1 ユニットテスト追加

```python
# tests/unit/test_job_generator_v2/test_validators/test_v1_compatibility.py

class TestV1CompatiblePatterns:
    """Test that V1 patterns are accepted by V2 validators."""

    def test_expertagent_base_url_allowed(self):
        """${EXPERTAGENT_BASE_URL} should be allowed."""
        validator = AgentConstraintValidator(allow_known_env_vars=True)
        config = {
            "agent": "fetchAgent",
            "inputs": {
                "url": "${EXPERTAGENT_BASE_URL}/aiagent-api/v1/utility/google_search"
            }
        }
        errors = validator.validate_fetch_agent(config)
        assert len(errors) == 0

    def test_source_query_allowed(self):
        """:source.query should be allowed for V1 compatibility."""
        validator = SourcePathRuleEngine(v1_compatible=True)
        is_valid, error = validator.validate_path(":source.query")
        assert is_valid is True

    def test_v1_workflow_yaml_valid(self):
        """V1-style workflow should pass validation."""
        pipeline = ValidationPipeline(strictness=ValidationStrictness.V1_COMPATIBLE)
        v1_workflow = {
            "version": "0.5",
            "nodes": {
                "source": {},
                "google_search": {
                    "agent": "fetchAgent",
                    "inputs": {
                        "url": "${EXPERTAGENT_BASE_URL}/aiagent-api/v1/utility/google_search",
                        "method": "POST",
                        "body": {"query": ":source.query"}
                    }
                }
            }
        }
        result = pipeline.validate(v1_workflow)
        assert result.is_valid
```

### 6.2 E2Eテスト

```bash
# V2でジョブ生成し、実行が成功することを確認
USE_JOB_GENERATOR_V2=true ./scripts/dev-start.sh

# UIからジョブ生成・実行
# v1.88+ が成功することを確認
```

---

## 7. 影響範囲

### 7.1 影響を受けるファイル

| ファイル | 変更種別 | 影響 |
|---------|---------|------|
| `agent_constraint_validator.py` | 修正 | 環境変数許可ロジック追加 |
| `source_path_rule_engine.py` | 修正 | V1互換パターン追加 |
| `yaml_generator.py` | 修正 | テンプレート生成修正 |
| `validation_pipeline.py` | 修正 | 厳格度設定追加 |
| テストファイル群 | 追加 | V1互換テスト追加 |

### 7.2 後方互換性

| 項目 | 状態 |
|------|------|
| V1ワークフロー | 影響なし（V1は別パス） |
| V2既存テスト | 修正必要（厳格度変更による） |
| API | 変更なし |
| DB | 変更なし |

---

## 8. 実装計画

### 8.1 フェーズ

| フェーズ | 内容 | 所要時間 |
|---------|------|---------|
| Phase 1 | DC-1, DC-2 実装（バリデーター修正） | 2時間 |
| Phase 2 | DC-3 実装（テンプレート修正） | 2時間 |
| Phase 3 | DC-4 実装（厳格度設定） | 1時間 |
| Phase 4 | テスト追加・E2E検証 | 2時間 |

### 8.2 優先順位

**P0 (即座に対応):**
- DC-1: 環境変数許可リスト（LLM生成を成功させる）
- DC-2: V1互換パスパターン（LLM生成を成功させる）

**P1 (次に対応):**
- DC-3: テンプレートフォールバック修正（フォールバック時も動作）

**P2 (その後対応):**
- DC-4: 厳格度設定（運用柔軟性向上）

---

## 9. 教訓と再発防止

### 9.1 今回の教訓

1. **既存システムの動作を理解してから新機能を設計する**
   - graphAiServerの環境変数展開機能を知らなかった

2. **自己矛盾テストを実施する**
   - LLMが生成するパターンをバリデーターでテストすべきだった

3. **V1互換性テストを必須化する**
   - V1で動作するワークフローがV2でも動作することを確認

### 9.2 再発防止策

1. **コンポーネント間ドキュメントの整備**
   - graphAiServerの機能一覧をexpertAgentのドキュメントに記載

2. **設計レビューチェックリストに追加**
   - [ ] 既存システムとの互換性を確認したか
   - [ ] 自己矛盾がないか確認したか
   - [ ] E2Eテストで動作確認したか

3. **CI/CDにV1互換テストを追加**
   - V1パターンを含むワークフローの検証テスト

---

## 10. 承認

| 役割 | 承認者 | 日付 |
|------|--------|------|
| 設計レビュー | - | - |
| 実装承認 | - | - |

---

*このドキュメントはIssue #342 V2バリデーター問題の根本原因分析と設計見直しをまとめたものです。*

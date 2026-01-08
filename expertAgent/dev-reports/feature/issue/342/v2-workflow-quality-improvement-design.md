# V2 ワークフロー生成品質改善 - 設計方針書

**作成日**: 2026-01-07
**Issue**: #342 (追加対応)
**ステータス**: ✅ Approved (レビュー指摘反映済み)
**レビュー日**: 2026-01-07

---

## 1. 背景と問題

### 1.1 現状の問題

V2 Job Generatorで生成されるワークフローが低品質:

```yaml
# 現在の出力（問題あり）
nodes:
  task_001:
    agent: fetchAgent           # 全ノードがfetchAgent
    inputs:
      data: :source.user_input  # 単純な入力参照のみ
    params:
      task_master_id: tm_task_001
```

### 1.2 根本原因

| 原因 | 詳細 | 影響 |
|------|------|------|
| テンプレート生成使用 | `use_llm_generation=False`でLLM未使用 | 品質低下 |
| Agent固定 | 全ノードが`fetchAgent`にハードコード | 機能不全 |
| API無視 | `recommended_api`が反映されない | 意図不一致 |
| スキーマ未活用 | interface定義のI/Oスキーマ未使用 | データフロー不適切 |

---

## 2. 改善方針

### 2.1 全体アーキテクチャ

```
┌─────────────────────────────────────────────────────────────┐
│                  WorkflowGenWorkflow                         │
├─────────────────────────────────────────────────────────────┤
│  1. Agent Selection Logic (NEW)                              │
│     - recommended_api → Agent mapping                        │
│     - タスク種別に基づく選択                                   │
├─────────────────────────────────────────────────────────────┤
│  2. Parameter Mapper (NEW)                                   │
│     - interface.input_schema → node.params                   │
│     - interface.output_schema → node.inputs reference        │
├─────────────────────────────────────────────────────────────┤
│  3. LLM Generator (既存・有効化)                              │
│     - PromptBuilder + Few-shot examples                      │
│     - Structured output (GraphAIWorkflowSchema)              │
├─────────────────────────────────────────────────────────────┤
│  4. YAML Validator (既存)                                    │
│     - Syntax validation                                      │
│     - Agent validation                                       │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. 詳細設計

### 3.1 LLM生成の有効化

#### 3.1.1 変更箇所

**`workflows/workflow_gen/workflow.py`**:

```python
# Before
yaml_generator = YamlGeneratorSubWorkflow(
    graphai_version="0.6",
    # use_llm_generation=False (デフォルト)
)
yaml_result = await yaml_generator.generate(...)

# After
yaml_generator = YamlGeneratorSubWorkflow(
    graphai_version="0.6",
    use_llm_generation=True,  # LLM有効化
)
yaml_result = await yaml_generator.generate_with_llm(
    task_master_ids=input.task_master_ids,
    job_master_id=input.job_master_id,
    interfaces=interfaces_dict,
    context=context,
    max_retries=2,
)
```

#### 3.1.2 フォールバック戦略

```python
try:
    # LLM生成を試行
    yaml_result = await yaml_generator.generate_with_llm(...)
except WorkflowError as e:
    if e.error_type == ErrorType.LLM:
        # LLM失敗時はテンプレートにフォールバック
        logger.warning("LLM generation failed, falling back to template")
        yaml_result = await yaml_generator.generate(...)
    else:
        raise
```

---

### 3.2 Agent選択ロジック

#### 3.2.1 API → Agent マッピング

**新規ファイル: `workflows/workflow_gen/agent_selector.py`**

```python
from dataclasses import dataclass
from typing import Literal

AgentType = Literal[
    "fetchAgent",           # HTTP API呼び出し
    "anthropicAgent",       # Claude LLM
    "geminiAgent",          # Gemini LLM
    "stringTemplateAgent",  # テキスト整形
    "mapAgent",             # 配列処理
    "copyAgent",            # データコピー
]

@dataclass
class AgentMapping:
    """APIエンドポイントからAgentへのマッピング定義"""
    api_pattern: str        # APIパターン（正規表現）
    agent: AgentType        # 使用するAgent
    default_params: dict    # デフォルトパラメータ


# APIエンドポイント → Agent マッピングテーブル
# 注意: GraphAI仕様では fetchAgent は inputs ブロック内に url, method, body を配置
API_AGENT_MAPPINGS: list[AgentMapping] = [
    # expertAgent utility APIs
    AgentMapping(
        api_pattern=r"/v1/utility/google_search",
        agent="fetchAgent",
        default_params={
            "method": "POST",
            "timeout": 180,  # LLMナレッジ抽出のため長め
        }
    ),
    AgentMapping(
        api_pattern=r"/v1/utility/gmail/send",
        agent="fetchAgent",
        default_params={
            "method": "POST",
        }
    ),
    AgentMapping(
        api_pattern=r"/v1/utility/slack",
        agent="fetchAgent",
        default_params={
            "method": "POST",
        }
    ),
    # expertAgent AI Agent APIs (fetchAgentでexpertAgentを呼び出す)
    AgentMapping(
        api_pattern=r"/v1/aiagent/.*",
        agent="fetchAgent",  # expertAgent API呼び出しはfetchAgent
        default_params={
            "method": "POST",
        }
    ),
    # テキスト処理（GraphAI内で完結）
    AgentMapping(
        api_pattern=r"text_format|template",
        agent="stringTemplateAgent",
        default_params={}
    ),
]


class AgentSelector:
    """タスクに適切なAgentを選択するクラス"""

    def select_agent(
        self,
        recommended_api: str | None,
        task_type: str | None = None,
        task_description: str | None = None,
    ) -> tuple[AgentType, dict]:
        """
        Args:
            recommended_api: 推奨API（例: "/v1/utility/gmail/send"）
            task_type: タスク種別（例: "email_send", "search"）
            task_description: タスク説明

        Returns:
            (agent_type, default_params)
        """
        # 1. recommended_apiからマッチング
        if recommended_api:
            for mapping in API_AGENT_MAPPINGS:
                if re.search(mapping.api_pattern, recommended_api):
                    return mapping.agent, mapping.default_params.copy()

        # 2. task_typeからの推論
        if task_type:
            type_mapping = {
                "email_send": ("fetchAgent", {"method": "POST"}),
                "search": ("fetchAgent", {"method": "POST"}),
                "llm_process": ("anthropicAgent", {}),
                "data_transform": ("copyAgent", {}),
            }
            if task_type in type_mapping:
                return type_mapping[task_type]

        # 3. デフォルト: fetchAgent
        return "fetchAgent", {}
```

#### 3.2.2 使用例

```python
selector = AgentSelector()

# Gmail送信タスク
agent, params = selector.select_agent(
    recommended_api="/v1/utility/gmail/send",
    task_type="email_send"
)
# → ("fetchAgent", {"baseUrl": "${EXPERT_AGENT_URL}", "method": "POST"})

# LLM要約タスク
agent, params = selector.select_agent(
    recommended_api="/v1/aiagent/summarize",
    task_type="llm_process"
)
# → ("anthropicAgent", {"model": "claude-sonnet-4-20250514"})
```

---

### 3.3 パラメータマッピング

#### 3.3.1 Interface Schema → Node Params 変換

**新規ファイル: `workflows/workflow_gen/parameter_mapper.py`**

```python
from dataclasses import dataclass
from typing import Any

@dataclass
class NodeParameter:
    """ノードパラメータ定義"""
    name: str
    value: Any
    source: str  # "static", "input_ref", "previous_node"


class ParameterMapper:
    """InterfaceスキーマからNodeパラメータへのマッピング"""

    def map_input_params(
        self,
        interface: InterfaceSchema,
        task_index: int,
        previous_task_id: str | None,
    ) -> dict[str, Any]:
        """
        入力スキーマからノードのinputsを生成

        Args:
            interface: InterfaceSchema
            task_index: タスクのインデックス（0=最初）
            previous_task_id: 前のタスクID（依存関係）

        Returns:
            inputs定義（dict）
        """
        inputs: dict[str, Any] = {}
        input_schema = interface.input_schema or {}
        properties = input_schema.get("properties", {})

        for prop_name, prop_def in properties.items():
            if task_index == 0:
                # 最初のタスク: user_inputから取得
                inputs[prop_name] = f":source.user_input.{prop_name}"
            else:
                # 後続タスク: 前のタスクの出力から取得
                inputs[prop_name] = f":source.{previous_task_id}.{prop_name}"

        return inputs

    def map_api_params(
        self,
        recommended_api: str,
        interface: InterfaceSchema,
    ) -> dict[str, Any]:
        """
        推奨APIからfetchAgentのパラメータを生成

        Args:
            recommended_api: API エンドポイント
            interface: InterfaceSchema

        Returns:
            params定義（dict）
        """
        # GraphAI仕様: fetchAgentは inputs ブロックに url, method, body を配置
        # URL は baseUrl + path ではなく、完全なURLを構築
        full_url = f"${{EXPERTAGENT_BASE_URL}}{recommended_api}"
        params: dict[str, Any] = {
            "url": full_url,
            "method": "POST",
        }

        # output_schemaからheadersを推論
        output_schema = interface.output_schema or {}
        if output_schema.get("type") == "object":
            params["headers"] = {
                "Content-Type": "application/json",
                "Accept": "application/json",
            }

        return params
```

#### 3.3.2 生成例

```python
mapper = ParameterMapper()

# Gmail送信タスクの入力マッピング
interface = InterfaceSchema(
    task_id="task_002",
    input_schema={
        "properties": {
            "to": {"type": "string"},
            "subject": {"type": "string"},
            "body": {"type": "string"},
        }
    }
)

inputs = mapper.map_input_params(
    interface=interface,
    task_index=1,
    previous_task_id="task_001",
)
# → {
#     "to": ":source.user_input.to",
#     "subject": ":source.task_001.subject",
#     "body": ":source.task_001.body"
# }

params = mapper.map_api_params(
    recommended_api="/v1/utility/gmail/send",
    interface=interface,
)
# → {
#     "baseUrl": "${EXPERT_AGENT_BASE_URL}",
#     "path": "/v1/utility/gmail/send",
#     "method": "POST",
#     "headers": {"Content-Type": "application/json", ...}
# }
```

---

### 3.4 Few-shot Examples活用

#### 3.4.1 高品質なExample追加

**`workflows/workflow_gen/prompt_builder/few_shot/examples/`**:

```yaml
# gmail_send_example.yaml
name: "Gmail送信ワークフロー"
description: "検索結果をメールで送信"
tags: ["email", "gmail", "notification"]
workflow_yaml: |
  version: "0.5"
  nodes:
    source: {}

    send_email:
      agent: fetchAgent
      inputs:
        url: ${EXPERTAGENT_BASE_URL}/v1/utility/gmail/send
        method: POST
        body:
          to: :source.user_input.recipient_email
          subject: :source.user_input.subject
          body: :source.user_input.content
      isResult: true
```

```yaml
# google_search_example.yaml
name: "Google検索ワークフロー"
description: "キーワードでGoogle検索を実行"
tags: ["search", "google", "web"]
workflow_yaml: |
  version: "0.5"
  nodes:
    source: {}

    search:
      agent: fetchAgent
      inputs:
        url: ${EXPERTAGENT_BASE_URL}/v1/utility/google_search
        method: POST
        body:
          query: :source.user_input.keyword
          max_results: 5
      timeout: 180  # LLMナレッジ抽出のため長め
      isResult: true
```

```yaml
# search_and_notify_example.yaml
name: "検索＆通知ワークフロー"
description: "検索結果を整形してメール送信"
tags: ["search", "email", "chain"]
workflow_yaml: |
  version: "0.5"
  nodes:
    source: {}

    search:
      agent: fetchAgent
      inputs:
        url: ${EXPERTAGENT_BASE_URL}/v1/utility/google_search
        method: POST
        body:
          query: :source.user_input.keyword
          max_results: 5
      timeout: 180

    format_results:
      agent: stringTemplateAgent
      inputs:
        keyword: :source.user_input.keyword
        results: :search.results
      params:
        template: |
          検索結果: ${keyword}

          {{#each results}}
          - {{title}}: {{snippet}}
          {{/each}}

    send_notification:
      agent: fetchAgent
      inputs:
        url: ${EXPERTAGENT_BASE_URL}/v1/utility/gmail/send
        method: POST
        body:
          to: :source.user_input.email
          subject: "検索結果サマリ"
          body: :format_results
      isResult: true
```

#### 3.4.2 Example選択ロジック強化

```python
def select_few_shot_examples(
    recommended_apis: list[str] | None,
    task_chain_length: int,
    input_schema: dict,
    output_schema: dict,
) -> list[FewShotExample]:
    """
    タスクに最適なFew-shot examplesを選択

    選択基準:
    1. recommended_apisとのマッチング（最優先）
    2. タスクチェーン長の類似性
    3. スキーマ構造の類似性
    """
    examples = load_all_examples()
    scored_examples = []

    for example in examples:
        score = 0

        # API マッチング（+10点/API）
        if recommended_apis:
            for api in recommended_apis:
                if any(api in tag for tag in example.tags):
                    score += 10

        # チェーン長の類似性（+5点）
        example_node_count = count_nodes(example.workflow_yaml)
        if abs(example_node_count - task_chain_length) <= 1:
            score += 5

        scored_examples.append((score, example))

    # スコア順でトップ3を返す
    scored_examples.sort(key=lambda x: x[0], reverse=True)
    return [ex for score, ex in scored_examples[:3] if score > 0]
```

---

## 4. 実装計画

### 4.1 タスク分解

| Phase | タスク | 見積 | 依存 | デッドコード対策 |
|-------|-------|------|------|-----------------|
| **Phase 1** | AgentSelector実装 | 2h | - | 統合確認必須 |
| **Phase 2** | ParameterMapper実装 | 2h | - | 統合確認必須 |
| **Phase 3** | Few-shot examples追加 | 1h | - | loader統合確認 |
| **Phase 4** | LLM生成有効化 + 不要コード削除 | 2h | Phase 1-3 | `create_yaml_generation_prompt`削除 |
| **Phase 5** | 統合テスト + デッドコード検証 | 2h | Phase 4 | verify_no_dead_code.sh実行 |

### 4.2 Phase 4 詳細: LLM有効化 + デッドコード整理

#### 4.2.1 workflow.py の変更

```python
# Before (yaml_generator.generate() を直接呼び出し)
yaml_result = await yaml_generator.generate(...)

# After (generate_with_llm() を優先、フォールバック内蔵)
try:
    yaml_result = await yaml_generator.generate_with_llm(
        task_master_ids=task_master_ids,
        job_master_id=job_master_id,
        interfaces=interfaces,
        context=context,
    )
except WorkflowError as e:
    if e.error_type == ErrorType.LLM:
        # LLM失敗時のみテンプレートにフォールバック（ログ出力）
        logger.warning("LLM generation failed, using template fallback: %s", e)
        yaml_result = await yaml_generator.generate(...)
    else:
        raise
```

#### 4.2.2 削除対象コード

| 削除対象 | 理由 | 代替 |
|---------|------|------|
| `create_yaml_generation_prompt()` | 新PromptBuilderで置換 | `prompt_builder/assembler.py` |
| `YAML_GENERATION_SYSTEM_PROMPT`（旧版） | GraphAI仕様非準拠 | `prompt_builder/system/workflow_generator.py` |

#### 4.2.3 維持するコード（フォールバック用）

| 維持対象 | 理由 | 対応 |
|---------|------|------|
| `generate()` | LLM失敗時のフォールバック | deprecatedマーカー追加 |
| `_build_workflow_nodes()` | generate()から使用 | docstring更新 |
| `_generate_yaml()` | generate()から使用 | docstring更新 |

### 4.3 変更ファイル

| ファイル | 変更種別 | 内容 |
|---------|---------|------|
| `agent_selector.py` | 新規 | Agent選択ロジック |
| `parameter_mapper.py` | 新規 | パラメータマッピング |
| `yaml_generator.py` | 修正 | 新コンポーネント統合 |
| `workflow.py` | 修正 | LLM生成有効化 |
| `few_shot/examples/*.yaml` | 新規 | 高品質Example |
| `few_shot/loader.py` | 修正 | Example選択強化 |

---

## 5. 期待される出力

### 5.1 Before（現状）

```yaml
nodes:
  task_001:
    agent: fetchAgent
    inputs:
      data: :source.user_input
    params:
      task_master_id: tm_task_001
```

### 5.2 After（改善後）

```yaml
version: "0.5"
nodes:
  source: {}

  google_search:
    agent: fetchAgent
    inputs:
      url: ${EXPERTAGENT_BASE_URL}/v1/utility/google_search
      method: POST
      body:
        query: :source.user_input.keyword
        max_results: 5
    timeout: 180
    console:
      after: true

  format_result:
    agent: stringTemplateAgent
    inputs:
      keyword: :source.user_input.keyword
      results: :google_search.results
    params:
      template: |
        検索結果: ${keyword}
        {{#each results}}
        - {{title}}: {{snippet}}
        {{/each}}

  send_email:
    agent: fetchAgent
    inputs:
      url: ${EXPERTAGENT_BASE_URL}/v1/utility/gmail/send
      method: POST
      body:
        to: :source.user_input.email
        subject: "検索結果サマリ"
        body: :format_result
    isResult: true
```

---

## 6. リスクと対策

| リスク | 影響 | 対策 |
|-------|------|------|
| LLM生成の失敗 | ワークフロー生成不可 | テンプレートへのフォールバック |
| Agent選択の誤り | 実行時エラー | バリデーション強化 |
| パラメータ不足 | API呼び出し失敗 | 必須パラメータチェック |
| Few-shot不足 | 品質低下 | 継続的なExample追加 |

---

## 6.1 拡張性・保守性の改善（Should Fix）

### 6.1.1 Agent Mappingの外部設定化

**目的**: 新しいAPIエンドポイント追加時にコード変更なしで対応可能にする

**設計案**:
```python
# workflows/workflow_gen/config/agent_mappings.yaml
mappings:
  - api_pattern: "/v1/utility/google_search"
    agent: "fetchAgent"
    default_params:
      method: "POST"
      timeout: 180
  - api_pattern: "/v1/utility/gmail/send"
    agent: "fetchAgent"
    default_params:
      method: "POST"
  # 新規APIは設定追加のみで対応

# agent_selector.py
class AgentSelector:
    def __init__(self, config_path: str | None = None):
        self.mappings = self._load_config(config_path or "config/agent_mappings.yaml")

    def _load_config(self, path: str) -> list[AgentMapping]:
        with open(path) as f:
            config = yaml.safe_load(f)
        return [AgentMapping(**m) for m in config["mappings"]]
```

### 6.1.2 Protocol/Interface導入

**目的**: テスト容易性とLSP準拠の向上

```python
from abc import ABC, abstractmethod
from typing import Protocol

class AgentSelectorProtocol(Protocol):
    """Agent選択のインターフェース"""
    def select_agent(
        self,
        recommended_api: str | None,
        task_type: str | None = None,
        task_description: str | None = None,
    ) -> tuple[str, dict]: ...

class ParameterMapperProtocol(Protocol):
    """パラメータマッピングのインターフェース"""
    def map_input_params(
        self,
        interface: InterfaceSchema,
        task_index: int,
        previous_task_id: str | None,
    ) -> dict[str, Any]: ...

# 依存性注入による利用
class YamlGeneratorSubWorkflow:
    def __init__(
        self,
        agent_selector: AgentSelectorProtocol | None = None,
        parameter_mapper: ParameterMapperProtocol | None = None,
    ):
        self.agent_selector = agent_selector or AgentSelector()
        self.parameter_mapper = parameter_mapper or ParameterMapper()
```

### 6.1.3 エラーハンドリングの詳細化

**目的**: LLM生成失敗時の適切なリトライとフォールバック

```python
@dataclass
class LLMRetryConfig:
    """LLMリトライ設定"""
    max_retries: int = 2
    retry_delay_seconds: float = 1.0
    exponential_backoff: bool = True

async def generate_with_llm(
    self,
    task_master_ids: list[str],
    job_master_id: str,
    interfaces: dict[str, InterfaceSchema],
    context: ExecutionContext,
    retry_config: LLMRetryConfig | None = None,
) -> YamlGenerationResult:
    """LLMを使用したワークフロー生成（リトライ対応）"""
    config = retry_config or LLMRetryConfig()
    last_error: Exception | None = None

    for attempt in range(config.max_retries + 1):
        try:
            return await self._generate_with_llm_impl(...)
        except WorkflowError as e:
            last_error = e
            if e.error_type != ErrorType.LLM:
                raise
            if attempt < config.max_retries:
                delay = config.retry_delay_seconds
                if config.exponential_backoff:
                    delay *= (2 ** attempt)
                await asyncio.sleep(delay)
                logger.warning(
                    "LLM generation retry %d/%d after %.1fs",
                    attempt + 1, config.max_retries, delay
                )

    # リトライ上限到達: テンプレートフォールバック
    logger.warning("LLM generation failed, falling back to template")
    return await self.generate(task_master_ids, job_master_id, interfaces)
```

---

## 7. 受入条件

- [ ] LLM生成が有効化され、高品質なYAMLが生成される
- [ ] recommended_apiに基づいて適切なAgentが選択される
- [ ] interface定義のスキーマがパラメータに反映される
- [ ] Few-shot examplesが適切に選択・活用される
- [ ] 単体テストカバレッジ90%以上
- [ ] E2E検証で期待通りのワークフローが生成される

---

**作成者**: Claude Code
**レビュー完了**: 2026-01-07

---

## Appendix: レビュー指摘事項と対応

### A.1 Must Fix（修正済み）

| 指摘事項 | 対応内容 |
|---------|---------|
| GraphAI仕様との不整合 | fetchAgentのパラメータを`inputs`ブロックに統一 |
| 非存在Agentの参照 | `anthropicAgent`を`fetchAgent`に修正（expertAgent API呼び出し用） |
| 環境変数名の不整合 | `${EXPERTAGENT_BASE_URL}`に統一 |

### A.2 Should Fix（設計書に追加）

| 指摘事項 | 対応内容 |
|---------|---------|
| Agent選択ロジックの拡張性 | 6.1.1 Agent Mappingの外部設定化として設計追加 |
| Protocol/Interface導入 | 6.1.2 Protocol/Interface導入として設計追加 |
| エラーハンドリングの具体性 | 6.1.3 エラーハンドリングの詳細化として設計追加 |

### A.3 GraphAI仕様準拠のポイント

1. **fetchAgent**: `url`, `method`, `body`は**必ず`inputs`ブロック内**に配置
2. **環境変数**: `${EXPERTAGENT_BASE_URL}`を使用
3. **バージョン**: `version: "0.5"`（現在の標準）
4. **timeout**: 処理時間の長いAPI（Google検索等）は`timeout: 180`を設定

---

## Appendix B: デッドコード対策（Issue #338教訓）

### B.1 現状の分析

**現在のファイル構成** (`workflows/workflow_gen/`):
```
yaml_generator.py       # テンプレート生成（現在使用中）
llm_generator.py        # LLM生成（存在するが未使用）
workflow.py             # メインワークフロー
test_runner.py          # テスト実行
yaml_validator.py       # YAML検証
prompt_builder/         # プロンプト構築（部分的に使用）
validators/             # バリデーター群
```

### B.2 不要になる処理の特定

| コード | ファイル | 行数 | 判定 | 対応 |
|--------|---------|------|------|------|
| `YAML_GENERATION_SYSTEM_PROMPT` | yaml_generator.py:43-70 | 27行 | ⚠️ 置換対象 | GraphAI仕様準拠版に更新 |
| `_build_workflow_nodes()` | yaml_generator.py:190-242 | 52行 | ⚠️ 条件付き維持 | フォールバック用に維持 |
| `_generate_yaml()` | yaml_generator.py:244-285 | 41行 | ⚠️ 条件付き維持 | フォールバック用に維持 |
| `create_yaml_generation_prompt()` | yaml_generator.py:476-506 | 30行 | ❌ 削除対象 | 新プロンプトビルダーで置換 |

### B.3 デッドコード防止戦略

#### 方針: フォールバック機構として維持

テンプレート生成（`generate()`メソッド）は**LLM失敗時のフォールバック**として維持する。
ただし、以下の対策を実施:

1. **明確なコード分離**
```python
class YamlGeneratorSubWorkflow:
    """
    生成モード:
    1. LLM生成（デフォルト）: generate_with_llm()
    2. テンプレート生成（フォールバック）: generate()

    フォールバック条件:
    - LLM APIエラー
    - バリデーション失敗（max_retries超過）
    - interface情報不足
    """
```

2. **使用状況の追跡**
```python
# 生成方法の統計をログ出力
logger.info(
    "YAML generated: method=%s, job_id=%s",
    result.generation_method,  # "llm" or "template"
    context.job_id,
)
```

3. **非推奨マーカーの明示**
```python
def generate(...) -> YamlGenerationResult:
    """Generate using template (FALLBACK ONLY).

    .. deprecated::
        Use generate_with_llm() for production.
        This method is maintained only as fallback.
    """
```

### B.4 削除対象コード

以下のコードは今回の実装で**完全削除**:

| コード | 理由 |
|--------|------|
| `create_yaml_generation_prompt()` | 新しいPromptBuilderで置換 |
| `YAML_GENERATION_SYSTEM_PROMPT`（旧版） | GraphAI仕様非準拠のため |

### B.5 新規追加コードの統合確認

新規ファイルは**必ずワークフローに統合**して使用されることを確認:

| 新規ファイル | 統合先 | 確認方法 |
|-------------|-------|---------|
| `agent_selector.py` | `llm_generator.py` または `yaml_generator.py` | import確認 + 呼び出し確認 |
| `parameter_mapper.py` | `llm_generator.py` または `yaml_generator.py` | import確認 + 呼び出し確認 |
| `config/agent_mappings.yaml` | `agent_selector.py` | ファイル読み込み確認 |
| `few_shot/examples/*.yaml` | `prompt_builder/few_shot/loader.py` | loader使用確認 |

### B.6 実装時チェックリスト

#### Phase 1-3 完了時（新規コード追加後）
- [ ] `agent_selector.py` が `yaml_generator.py` または `llm_generator.py` でimportされている
- [ ] `parameter_mapper.py` が `yaml_generator.py` または `llm_generator.py` でimportされている
- [ ] 新規Few-shotファイルが `loader.py` で読み込まれている
- [ ] 単体テストで新規クラスが呼び出されている

#### Phase 4 完了時（LLM有効化後）
- [ ] `workflow.py` が `generate_with_llm()` を呼び出している
- [ ] テンプレート生成がフォールバックとしてのみ使用される
- [ ] 削除対象コード（`create_yaml_generation_prompt`等）が削除されている

#### Phase 5 完了時（統合テスト後）
- [ ] E2Eテストで `generation_method: "llm"` が確認できる
- [ ] フォールバック時に `generation_method: "template"` がログ出力される
- [ ] 未使用コードがないことを静的解析で確認

### B.7 デッドコード検証スクリプト

```bash
#!/bin/bash
# scripts/verify_no_dead_code.sh

echo "=== V2 Workflow Gen デッドコード検証 ==="

# 1. 削除対象が存在しないことを確認
echo "Checking removed code..."
if grep -r "create_yaml_generation_prompt" expertAgent/aiagent/langgraph/jobGeneratorV2/; then
    echo "❌ ERROR: create_yaml_generation_prompt should be removed"
    exit 1
fi
echo "✅ Removed code verified"

# 2. 新規クラスが使用されていることを確認
echo "Checking new classes usage..."
if ! grep -r "AgentSelector" expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/workflow_gen/*.py | grep -v "agent_selector.py"; then
    echo "❌ ERROR: AgentSelector is not used"
    exit 1
fi
if ! grep -r "ParameterMapper" expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/workflow_gen/*.py | grep -v "parameter_mapper.py"; then
    echo "❌ ERROR: ParameterMapper is not used"
    exit 1
fi
echo "✅ New classes are integrated"

# 3. LLM生成がデフォルトで使用されていることを確認
echo "Checking LLM generation is default..."
if ! grep -r "generate_with_llm" expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/workflow_gen/workflow.py; then
    echo "❌ ERROR: generate_with_llm is not called in workflow.py"
    exit 1
fi
echo "✅ LLM generation is enabled"

echo ""
echo "=== All checks passed ==="
```

### B.8 修正後のファイル構成

```
workflows/workflow_gen/
├── __init__.py
├── workflow.py              # メインワークフロー（LLM優先に変更）
├── yaml_generator.py        # 生成器（LLM+テンプレートフォールバック）
├── llm_generator.py         # LLM生成サブワークフロー（強化）
├── agent_selector.py        # NEW: Agent選択ロジック
├── parameter_mapper.py      # NEW: パラメータマッピング
├── yaml_validator.py        # YAML検証
├── test_runner.py           # テスト実行
├── schemas.py               # スキーマ定義
├── errors.py                # エラー定義
├── config/
│   └── agent_mappings.yaml  # NEW: Agent設定ファイル
├── prompt_builder/
│   ├── __init__.py
│   ├── assembler.py         # プロンプト組み立て
│   ├── few_shot/
│   │   ├── __init__.py
│   │   ├── loader.py        # Example読み込み（強化）
│   │   └── examples/        # NEW: 高品質Example追加
│   │       ├── gmail_send.yaml
│   │       ├── google_search.yaml
│   │       └── search_and_notify.yaml
│   └── ...
└── validators/
    └── ...
```

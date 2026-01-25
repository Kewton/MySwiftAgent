# 設計方針書: Issue #342 V2 タスク分割 API情報注入メカニズム

**作成日**: 2026-01-07
**更新日**: 2026-01-07（レビュー指摘対応）
**Issue**: [#342 V2 Workflow Quality Improvement](https://github.com/Kewton/MySwiftAgent/issues/342)
**関連ドキュメント**: `v2-task-breakdown-api-fix.md`, `v2-workflow-quality-improvement-design.md`
**承認状態**: ✅ 条件付き承認 → 修正済み

---

## 1. 現状調査サマリ

### 1.1 対象プロジェクト

- **プロジェクト名**: expertAgent
- **主要モジュール**:
  - `aiagent/langgraph/jobGeneratorV2/` - V2 Job Generator (新アーキテクチャ)
  - `aiagent/langgraph/jobTaskGeneratorAgents/` - V1 Job Generator (参照用)
- **関連サービス**: jobqueue, graphAiServer, myAgentDesk

### 1.2 V1 vs V2 アーキテクチャ比較

| 項目 | V1 (jobTaskGeneratorAgents) | V2 (jobGeneratorV2) |
|------|----------------------------|---------------------|
| **ワークフロー形式** | 完全なYAML（URL, body直記載） | 委譲型（task_master_id参照） |
| **API情報の流れ** | プロンプトに `{expert_agent_capabilities}` 注入 | ❌ 欠落 |
| **LangGraph構造** | 単一StateGraph | Orchestrator + SubWorkflow |
| **recommended_apis** | 全タスクに設定される | ❌ 空になる |

### 1.3 既存設計パターン

| パターン | V1での使用箇所 | V2での状態 |
|---------|---------------|-----------|
| **Capability Injection** | `_build_expert_agent_capabilities()` → prompt | ❌ 未実装 |
| **API Mapping** | `task_api_mapping` in YAML | ❌ 未使用 |
| **SubWorkflow Pattern** | - | ✅ 実装済（ただしcap未注入）|
| **Protocol Pattern** | - | ✅ 実装済 |

### 1.4 問題の発生フロー

```
TaskBreakdownWorkflow.execute()
    │
    ├── Step 1: decomposer.decompose()  ← capabilities なし
    │       └── LLM: API情報を知らない
    │           └── recommended_apis = []
    │
    ├── Step 2: feasibility.check()     ← capabilities あり（ロード済）
    │       └── 正常動作（ただし入力データが不完全）
    │
    └── Step 3: alternative.generate()  ← capabilities あり
            └── 代替案生成（ただし元タスクのAPI情報が空）
```

### 1.5 モジュール間依存関係（修正前）

```
jobGeneratorV2/
├── orchestrator.py           # メインオーケストレータ
├── context.py                # 実行コンテキスト
├── llm_utils.py              # LLMユーティリティ ← 修正対象
├── types.py                  # 型定義 ← 修正対象（Capability型拡張）
│
└── workflows/
    ├── task_breakdown/
    │   ├── workflow.py       # メインワークフロー ← 修正対象
    │   ├── decomposer.py     # タスク分解 ← 修正対象
    │   ├── feasibility.py    # 実現可能性チェック (capabilities使用)
    │   └── alternative.py    # 代替案生成 (capabilities使用)
    │
    ├── interface_design/
    │   └── ...
    │
    ├── workflow_gen/
    │   ├── yaml_generator.py # YAML生成 ← 修正対象（P1）
    │   ├── llm_generator.py
    │   └── prompt_builder/   # プロンプトビルダー ← 修正対象（P1）
    │
    └── registration/
        └── master_manager.py # マスター登録 ← 修正対象（P1）
```

### 1.6 修正後のディレクトリ構造

```
aiagent/langgraph/
├── shared/                              # 【新規作成】V1/V2共通モジュール
│   ├── __init__.py
│   └── capability_utils.py              # capabilities読み込み・フォーマット
│
├── jobGeneratorV2/
│   ├── types.py                         # Capability型拡張（use_cases, method追加）
│   ├── llm_utils.py                     # プロンプトビルダー更新
│   └── workflows/
│       └── task_breakdown/
│           ├── workflow.py              # capabilities渡し
│           └── decomposer.py            # コンストラクタ追加
│
└── jobTaskGeneratorAgents/              # V1（変更なし、将来的にshared参照へ移行可能）
    └── utils/config/
        └── expert_agent_capabilities.yaml  # 既存（変更なし）
```

**設計判断**:
- `shared/` モジュールを新設し、V1/V2間でコード共通化（DRY原則）
- V1コードは変更せず、将来的に`shared`を参照するよう移行可能
- YAMLファイルは既存の場所を維持（移動によるリスク回避）

---

## 2. 設計原則

### 2.1 基本原則

| 原則 | 説明 | 適用 |
|------|------|------|
| **情報の一貫性** | API情報は全フェーズで一貫して利用可能 | capabilities を最初にロード |
| **依存性注入** | SubWorkflowは外部から依存を受け取る | コンストラクタ注入 |
| **単一責任** | 各SubWorkflowは単一の責任を持つ | capabilities フォーマットは別関数 |
| **後方互換性** | V1ジョブ生成に影響を与えない | V2コードのみ修正 |
| **フェイルセーフ** | capabilities未設定時はYAMLからロード | フォールバック機構 |
| **DRY原則** | V1/V2間でコード重複を排除 | `shared/capability_utils.py` で共通化 |

### 2.2 データフロー設計

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           shared/capability_utils.py                     │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ load_capabilities_from_yaml()    format_capabilities_for_prompt()│    │
│  └─────────────────────────────────────────────────────────────────┘    │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        TaskBreakdownWorkflow                             │
│                                                                          │
│  ┌─────────────────┐                                                    │
│  │ capabilities    │ ← load_capabilities_from_yaml() [shared]           │
│  │ (list[dict])    │                                                    │
│  └────────┬────────┘                                                    │
│           │                                                              │
│           ├──────────────────────────────────────┐                       │
│           │                                      │                       │
│           ▼                                      ▼                       │
│  ┌─────────────────┐                   ┌─────────────────┐              │
│  │ TaskDecomposer  │                   │ FeasibilityCheck│              │
│  │ SubWorkflow     │                   │ SubWorkflow     │              │
│  │                 │                   │                 │              │
│  │ capabilities ───┼─► system_prompt   │ capabilities ───┼─►            │
│  │                 │   (via shared)    │                 │              │
│  └────────┬────────┘                   └─────────────────┘              │
│           │                                                              │
│           ▼                                                              │
│  ┌─────────────────┐                                                    │
│  │ LLM Response    │                                                    │
│  │ recommended_apis│ ← 全タスクにAPI情報が含まれる                       │
│  └─────────────────┘                                                    │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.3 インターフェース契約

#### 2.3.1 shared/capability_utils.py（新規）

```python
"""V1/V2共通のcapabilityユーティリティ

このモジュールはV1とV2の両方から使用される共通関数を提供します。
YAMLファイルの読み込みとプロンプト用フォーマットを担当します。
"""

def load_capabilities_from_yaml() -> list[dict[str, Any]]:
    """expert_agent_capabilities.yaml からcapabilitiesをロード

    契約:
    - YAMLファイルが存在しない場合は空リストを返す
    - utility_apis と ai_agent_apis の両方を統合して返す
    - 返却される各dictには name, endpoint, description, use_cases, method を含む

    Returns:
        List of capability dictionaries with all fields from YAML.
    """
    ...

def format_capabilities_for_prompt(capabilities: list[dict[str, Any]]) -> str:
    """capabilitiesをLLMプロンプト用にフォーマット

    契約:
    - 空リストの場合は空文字列を返す
    - Utility API と AI Agent API をグループ化して出力
    - 各APIは「**{name}** (`{endpoint}`): {description} - {use_cases}」形式

    Args:
        capabilities: List of capability dictionaries

    Returns:
        Formatted string for prompt injection (Markdown format)
    """
    ...
```

#### 2.3.2 TaskDecomposerSubWorkflow

```python
class TaskDecomposerSubWorkflow:
    """タスク分解サブワークフロー

    契約:
    - capabilities が渡された場合、LLMプロンプトにAPI情報を含める
    - capabilities が空/Noneの場合、YAMLから自動ロードする
    - 返却される TaskDefinition には recommended_api が設定される（可能な限り）

    入力:
    - capabilities: list[dict[str, Any]] - 利用可能なAPI一覧（YAML形式）
    - input_data: TaskBreakdownInput - ユーザー要件

    出力:
    - list[TaskDefinition] - recommended_api が設定されたタスク一覧
    """

    def __init__(self, capabilities: list[dict[str, Any]] | None = None) -> None:
        """
        Args:
            capabilities: 利用可能なAPI一覧。Noneの場合はYAMLから自動ロード。
        """
        ...
```

#### 2.3.3 システムプロンプト関数

```python
def _build_task_breakdown_system_prompt(
    capabilities: list[dict[str, Any]] | None = None
) -> str:
    """タスク分割用システムプロンプトを構築

    契約:
    - capabilities が渡された場合、shared.format_capabilities_for_prompt() を使用
    - capabilities が空/Noneの場合、API一覧セクションは空になる
    - 返却されるプロンプトは常に有効な文字列
    - recommended_apis の記述ルールと Few-shot 例を含む
    """
    ...
```

#### 2.3.4 Capability 型定義（types.py 拡張）

```python
@dataclass
class Capability:
    """API機能定義

    必須フィールド:
    - name: str - API名（日本語可）
    - endpoint: str - APIエンドポイント（例: "/v1/utility/gmail/send"）
    - description: str - API説明

    オプショナルフィールド（YAMLスキーマと整合）:
    - use_cases: list[str] - 利用シナリオ一覧
    - method: str - HTTPメソッド（デフォルト: "POST"）
    - input_schema: dict - リクエストスキーマ（旧名: request_schema）
    - output_schema: dict - レスポンススキーマ（旧名: response_schema）
    """
    name: str
    description: str
    endpoint: str
    use_cases: list[str] = field(default_factory=list)      # 追加
    method: str = "POST"                                     # 追加
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)
```

**Note**: 内部的には `list[dict]` を使用し、`Capability` dataclass への変換は必要に応じて行う。
これによりYAMLからの読み込みがシンプルになり、フィールド追加時の影響を最小化。

---

## 3. 詳細設計

### 3.1 Phase 1: タスク分割 API 情報注入

#### 3.1.1 修正ファイル一覧

| ファイル | 修正内容 | 変更規模 |
|---------|---------|---------|
| `shared/capability_utils.py` | 【新規】共通ユーティリティ作成 | **New** |
| `shared/__init__.py` | 【新規】パッケージ初期化 | **New** |
| `jobGeneratorV2/types.py` | Capability型に `use_cases`, `method` 追加 | Small |
| `jobGeneratorV2/llm_utils.py` | `_build_task_breakdown_system_prompt()` 拡張 | Medium |
| `task_breakdown/workflow.py` | capabilities を decomposer に渡す | Small |
| `task_breakdown/decomposer.py` | コンストラクタ追加 | Medium |

#### 3.1.2 shared/capability_utils.py 詳細（新規）

```python
"""Shared utilities for capability handling across V1 and V2.

This module provides common functions for loading and formatting
capabilities from YAML configuration.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

# YAML config path (shared between V1 and V2)
_CONFIG_PATH = Path(__file__).parent.parent / "jobTaskGeneratorAgents/utils/config"


def load_capabilities_from_yaml() -> list[dict[str, Any]]:
    """Load capabilities from expert_agent_capabilities.yaml.

    Returns:
        List of capability dictionaries with all fields from YAML.
    """
    yaml_path = _CONFIG_PATH / "expert_agent_capabilities.yaml"
    if not yaml_path.exists():
        return []

    with open(yaml_path, encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

    capabilities = []

    # Utility APIs
    for api in config.get("utility_apis", []):
        capabilities.append({
            "name": api.get("name", ""),
            "endpoint": api.get("endpoint", ""),
            "description": api.get("description", ""),
            "use_cases": api.get("use_cases", []),
            "method": api.get("method", "POST"),
            "request_schema": api.get("request_schema", {}),
            "response_schema": api.get("response_schema", {}),
        })

    # AI Agent APIs
    for api in config.get("ai_agent_apis", []):
        capabilities.append({
            "name": api.get("name", ""),
            "endpoint": api.get("endpoint", ""),
            "description": api.get("description", ""),
            "use_cases": api.get("use_cases", []),
            "method": api.get("method", "POST"),
            "request_schema": api.get("request_schema", {}),
            "response_schema": api.get("response_schema", {}),
        })

    return capabilities


def format_capabilities_for_prompt(capabilities: list[dict[str, Any]]) -> str:
    """Format capabilities for LLM prompt injection.

    Args:
        capabilities: List of capability dictionaries

    Returns:
        Formatted string for prompt injection
    """
    if not capabilities:
        return ""

    lines = ["## 利用可能なAPI", ""]

    # Group by type
    utility_apis = [c for c in capabilities if c["endpoint"].startswith("/v1/utility/")]
    ai_apis = [c for c in capabilities if not c["endpoint"].startswith("/v1/utility/")]

    if utility_apis:
        lines.append("### Utility API (Direct API)")
        for api in utility_apis:
            use_cases = "、".join(api.get("use_cases", []))
            lines.append(
                f"- **{api['name']}** (`{api['endpoint']}`): "
                f"{api['description']} - {use_cases}"
            )
        lines.append("")

    if ai_apis:
        lines.append("### AI Agent API")
        for api in ai_apis:
            use_cases = "、".join(api.get("use_cases", []))
            lines.append(
                f"- **{api['name']}** (`{api['endpoint']}`): "
                f"{api['description']} - {use_cases}"
            )
        lines.append("")

    return "\n".join(lines)
```

**設計判断**:
- V1の `_build_expert_agent_capabilities()` のロジックを参考に共通化
- 型は `list[dict]` を使用し、dataclass変換のオーバーヘッドを回避
- パス解決は相対パスで、V1のYAML配置場所を参照

#### 3.1.3 workflow.py 修正詳細

**修正前**:
```python
async def execute(self, input_data, context):
    # Step 1: Decompose
    decomposer = TaskDecomposerSubWorkflow()
    tasks = await decomposer.decompose(input_data, context)

    # Step 2: Check feasibility (capabilities loaded here)
    capabilities = input_data.available_capabilities
    if not capabilities:
        capabilities = load_capabilities_from_yaml()
```

**修正後**:
```python
from ...shared.capability_utils import load_capabilities_from_yaml

async def execute(self, input_data, context):
    # Load capabilities FIRST using shared utility
    capabilities = load_capabilities_from_yaml()
    logger.info("Loaded %d capabilities for task breakdown", len(capabilities))

    # Step 1: Decompose WITH capabilities
    decomposer = TaskDecomposerSubWorkflow(capabilities=capabilities)
    tasks = await decomposer.decompose(input_data, context)

    # Step 2: Check feasibility (reuse same capabilities)
    feasibility = FeasibilitySubWorkflow(capabilities=capabilities)
```

**設計判断**:
- `shared.capability_utils` から読み込み関数をインポート
- capabilities のロードを最初に移動
- 同じ capabilities インスタンスを全 SubWorkflow で共有
- メモリ効率とデータ一貫性を両立

#### 3.1.4 decomposer.py 修正詳細

**新規追加: コンストラクタ**
```python
from ...shared.capability_utils import load_capabilities_from_yaml

class TaskDecomposerSubWorkflow:
    def __init__(self, capabilities: list[dict[str, Any]] | None = None) -> None:
        """Initialize with available capabilities.

        Args:
            capabilities: List of capability dicts from YAML.
                         If None, will load from YAML automatically.
        """
        self._capabilities = capabilities

    async def decompose(self, input_data, context) -> list[TaskDefinition]:
        # Auto-load if not provided
        capabilities = self._capabilities
        if capabilities is None:
            capabilities = load_capabilities_from_yaml()
            logger.info("Auto-loaded %d capabilities", len(capabilities))

        # Build prompts WITH capabilities
        system_prompt = _build_task_breakdown_system_prompt(capabilities)
        # ... rest unchanged
```

**設計判断**:
- コンストラクタ注入により、テスト時のモック容易性を確保
- `None` の場合は自動ロード（フォールバック機構）
- フォーマット処理は `shared.format_capabilities_for_prompt()` に委譲

#### 3.1.5 llm_utils.py 修正詳細

**実装コード**:
```python
from ..shared.capability_utils import format_capabilities_for_prompt


def _build_task_breakdown_system_prompt(
    capabilities: list[dict[str, Any]] | None = None
) -> str:
    """Build system prompt for task breakdown with API info."""
    # Use shared formatting function
    capabilities_section = format_capabilities_for_prompt(capabilities or [])

    # Build recommended_apis instruction
    api_instruction = ""
    if capabilities:
        api_instruction = """
## recommended_apis の記述ルール

**重要**: 各タスクには必ず `recommended_apis` を指定してください。

1. タスク実行に必要なAPIを上記リストから選択
2. 各APIには `api_name`, `endpoint`, `reason` を含める
3. 1タスク1API を原則とする

### 例
```json
{
  "task_id": "task_001",
  "name": "Google検索",
  "recommended_apis": [
    {
      "api_name": "Google検索",
      "endpoint": "/v1/utility/google_search",
      "reason": "キーワードでWeb検索を実行"
    }
  ]
}
```
"""

    return f\"\"\"You are an expert task decomposition assistant.
Your task is to decompose user requirements into executable workflow tasks.

## Principles
1. Hierarchical decomposition - Break complex tasks into smaller units
2. Clear dependencies - Define which tasks depend on others
3. Specificity and executability - Each task should be specific and actionable
4. Modularity and reusability - Design tasks that can be reused
5. **API Selection** - Each task MUST specify recommended_apis from available APIs

{capabilities_section}
{api_instruction}
## Output Format
Return a structured response with:
- tasks: List of TaskBreakdownItem with task_id, name, description, dependencies, recommended_apis
- overall_summary: Summary of the entire workflow
- job_body_parameters: Parameters extracted from the requirements
\"\"\"
```

**システムプロンプト構造**:

```
┌─────────────────────────────────────────────────────────────────┐
│ You are an expert task decomposition assistant.                 │
│ ...                                                             │
│ 5. **API Selection** ← 新規追加                                 │
│                                                                 │
│ ## 利用可能なAPI ← shared.format_capabilities_for_prompt()      │
│ ### Utility API (Direct API)                                    │
│ - **Gmail検索** (`/v1/utility/gmail/search`): ...              │
│ - **Google検索** (`/v1/utility/google_search`): ...            │
│ ...                                                             │
│ ### AI Agent API                                                │
│ - **MyLLM** (`/v1/myllm`): ...                                 │
│                                                                 │
│ ## recommended_apis の記述ルール ← 新規追加セクション            │
│ 1. タスク実行に必要なAPIを上記リストから選択                      │
│ 2. 各APIには api_name, endpoint, reason を含める                │
│ 3. 1タスク1API を原則とする                                      │
│                                                                 │
│ ### 例 ← Few-shot例（Google検索の例）                           │
│ ```json                                                         │
│ { "task_id": "task_001", "recommended_apis": [...] }           │
│ ```                                                             │
│                                                                 │
│ ## Output Format                                                │
│ ...                                                             │
└─────────────────────────────────────────────────────────────────┘
```

**設計判断**:
- `shared.format_capabilities_for_prompt()` を使用してDRY原則を遵守
- V1の成功パターン（`{expert_agent_capabilities}`）を参考
- Few-shot例を含めてLLMの出力品質を向上
- 日本語と英語のバイリンガルプロンプト（APIは日本語名、構造は英語）

### 3.2 Phase 2: TaskMaster URL API固有化

#### 3.2.1 URL解決ロジック

```python
class MasterManagerSubWorkflow:
    # 環境変数から取得（デフォルト値付き）
    _EXPERTAGENT_URL = os.environ.get("EXPERTAGENT_BASE_URL", "http://localhost:8004")
    _GRAPHAI_URL = os.environ.get("GRAPHAI_SERVER_URL", "http://localhost:8005")

    def _resolve_task_url(self, task: TaskDefinition) -> str:
        """Resolve API URL based on recommended_api.

        解決ロジック:
        1. recommended_api が /v1/utility/* → expertAgent URL
        2. recommended_api が /v1/aiagent/* → expertAgent URL
        3. recommended_api が /api/v1/* → graphAiServer URL
        4. それ以外 → graphAiServer fallback

        Args:
            task: Task definition with recommended_api

        Returns:
            Full URL for the task
        """
        endpoint = task.recommended_api or ""

        if endpoint.startswith("/v1/utility/") or endpoint.startswith("/v1/aiagent/"):
            return f"{self._EXPERTAGENT_URL}{endpoint}"

        # Fallback to graphAiServer
        return f"{self._GRAPHAI_URL}/api/v1/myagent"
```

**設計判断**:
- 環境変数による設定可能性
- 明示的なフォールバック（graphAiServer）
- エンドポイントパターンによるルーティング

#### 3.2.2 body_template 生成ロジック

```python
# API別テンプレートマッピング
API_BODY_TEMPLATES = {
    "/v1/utility/google_search": {
        "queries": ["{{job.body.query}}"],
        "num": 3,
    },
    "/v1/utility/gmail/send": {
        "to": "{{job.body.to}}",
        "subject": "{{job.body.subject}}",
        "body": "{{job.body.body}}",
    },
    "/v1/utility/gmail/search": {
        "query": "{{job.body.query}}",
        "max_results": "{{job.body.max_results|default:10}}",
    },
    "/v1/aiagent/utility/jsonoutput": {
        "prompt": "{{job.body.prompt}}",
        "schema": "{{job.body.schema}}",
    },
    "/v1/myllm": {
        "prompt": "{{job.body.prompt}}",
        "model": "{{job.body.model|default:'gemini-2.5-flash'}}",
    },
}

def _build_api_specific_body_template(
    self,
    task: TaskDefinition,
    order: int,
) -> dict[str, Any]:
    """Build API-specific body template.

    Args:
        task: Task definition
        order: Task execution order (0-indexed)

    Returns:
        Body template dict with Jinja2-style placeholders
    """
    endpoint = task.recommended_api or ""

    # Get base template
    base_template = API_BODY_TEMPLATES.get(endpoint, {})

    if not base_template:
        # Default template
        return self._build_default_body_template(order)

    # Adjust for chained tasks
    if order > 0:
        return self._adjust_template_for_chain(base_template, order)

    return base_template.copy()
```

**設計判断**:
- APIごとのテンプレートをマッピングで管理
- タスクチェーン（order > 0）での参照調整
- 拡張可能な設計（新APIはマッピングに追加）

---

## 4. エラーハンドリング設計

### 4.1 エラーシナリオと対応

| シナリオ | 検出方法 | 対応 |
|---------|---------|------|
| capabilities ロード失敗 | `load_capabilities_from_yaml()` が空を返す | 警告ログ出力、空リストで続行 |
| LLMが recommended_apis を無視 | 返却値の検証 | 警告ログ、フォールバック値なし |
| 不正な endpoint 形式 | パターンマッチ失敗 | デフォルトURL使用 |
| body_template マッピング不在 | `API_BODY_TEMPLATES.get()` が None | デフォルトテンプレート使用 |

### 4.2 ログ出力設計

```python
# 情報レベル
logger.info("Loading capabilities: %d APIs found", len(capabilities))
logger.info("Building system prompt with %d capabilities", len(caps))

# 警告レベル
logger.warning("No capabilities provided to decomposer, API info will be missing")
logger.warning("Task %s has no recommended_api, using fallback URL", task.id)

# デバッグレベル
logger.debug("Formatted capabilities: %s", formatted_caps)
logger.debug("Resolved URL for task %s: %s", task.id, url)
```

---

## 5. テスト設計

### 5.1 単体テスト

#### 5.1.1 shared/capability_utils.py テスト（新規）

| テストケース | 検証内容 | ファイル |
|-------------|---------|---------|
| `test_load_capabilities_from_yaml` | YAMLから正しくロード | `test_capability_utils.py` |
| `test_load_capabilities_includes_use_cases` | use_casesフィールドが含まれる | `test_capability_utils.py` |
| `test_load_capabilities_yaml_not_found` | ファイル不在時に空リスト | `test_capability_utils.py` |
| `test_format_capabilities_empty` | 空リストで空文字列 | `test_capability_utils.py` |
| `test_format_capabilities_includes_api_info` | API情報がプロンプトに含まれる | `test_capability_utils.py` |
| `test_format_capabilities_groups_by_type` | Utility/AI APIでグループ化 | `test_capability_utils.py` |

```python
# tests/unit/test_job_generator_v2/test_capability_utils.py
"""Tests for shared capability utilities."""

import pytest
from aiagent.langgraph.shared.capability_utils import (
    format_capabilities_for_prompt,
    load_capabilities_from_yaml,
)


class TestLoadCapabilitiesFromYaml:
    """Tests for load_capabilities_from_yaml."""

    def test_loads_capabilities(self):
        """Test that capabilities are loaded from YAML."""
        caps = load_capabilities_from_yaml()
        assert len(caps) > 0

    def test_includes_use_cases(self):
        """Test that use_cases field is included."""
        caps = load_capabilities_from_yaml()
        gmail_search = next((c for c in caps if "Gmail検索" in c["name"]), None)
        assert gmail_search is not None
        assert "use_cases" in gmail_search
        assert len(gmail_search["use_cases"]) > 0

    def test_includes_method(self):
        """Test that method field is included."""
        caps = load_capabilities_from_yaml()
        assert all("method" in c for c in caps)


class TestFormatCapabilitiesForPrompt:
    """Tests for format_capabilities_for_prompt."""

    def test_empty_returns_empty_string(self):
        """Test with empty capabilities."""
        result = format_capabilities_for_prompt([])
        assert result == ""

    def test_includes_api_info(self):
        """Test that API info is included."""
        caps = [{"name": "Gmail検索", "endpoint": "/v1/utility/gmail/search",
                 "description": "Gmail検索", "use_cases": ["検索"]}]
        result = format_capabilities_for_prompt(caps)
        assert "Gmail検索" in result
        assert "/v1/utility/gmail/search" in result

    def test_integration_with_actual_yaml(self):
        """Integration: format loaded capabilities."""
        caps = load_capabilities_from_yaml()
        result = format_capabilities_for_prompt(caps)
        assert "## 利用可能なAPI" in result
        assert "Utility API" in result
```

#### 5.1.2 既存テストの更新

| テストケース | 検証内容 | ファイル |
|-------------|---------|---------|
| `test_decomposer_init_with_capabilities` | コンストラクタ注入 | `test_decomposer.py` |
| `test_decomposer_auto_loads_when_none` | None時に自動ロード | `test_decomposer.py` |
| `test_system_prompt_includes_apis` | APIがプロンプトに含まれる | `test_llm_utils.py` |
| `test_system_prompt_uses_shared_format` | shared関数を使用 | `test_llm_utils.py` |
| `test_resolve_task_url_utility` | utility API URL | `test_master_manager.py` |
| `test_resolve_task_url_fallback` | フォールバックURL | `test_master_manager.py` |
| `test_body_template_google_search` | Google検索テンプレート | `test_master_manager.py` |
| `test_body_template_gmail_send` | Gmail送信テンプレート | `test_master_manager.py` |

### 5.2 結合テスト（統合確認）

| テストケース | 検証内容 | 重要度 |
|-------------|---------|--------|
| `test_task_breakdown_e2e_with_api_assignment` | 全フローで recommended_api が設定される | **Critical** |
| `test_system_prompt_actually_used_in_llm_call` | プロンプトが実際にLLM呼び出しで使用される | **Critical** |
| `test_recommended_api_propagates_to_workflow` | recommended_apiがワークフロー生成まで伝播 | **Critical** |
| `test_workflow_gen_uses_recommended_api` | ワークフロー生成がAPI情報を使用 | High |
| `test_registration_creates_correct_url` | TaskMasterが正しいURLで作成される | High |

```python
# tests/integration/test_v2_task_breakdown_integration.py
"""Integration tests for V2 task breakdown with API assignment."""

import pytest
from unittest.mock import patch, AsyncMock


class TestTaskBreakdownIntegration:
    """Integration tests for task breakdown flow."""

    @pytest.mark.asyncio
    async def test_recommended_api_in_all_tasks(self):
        """Test that all tasks have recommended_api after decomposition."""
        # Setup
        workflow = TaskBreakdownWorkflow()
        input_data = TaskBreakdownInput(
            user_requirement="Google検索してメール送信"
        )

        # Execute
        with patch("...invoke_structured_llm") as mock_llm:
            mock_llm.return_value = MockLLMResponse(...)
            output = await workflow.execute(input_data, context)

        # Verify: ALL tasks must have recommended_api
        for task in output.tasks:
            assert task.recommended_api, f"Task {task.id} missing recommended_api"

    @pytest.mark.asyncio
    async def test_system_prompt_contains_api_list(self):
        """Test that system prompt sent to LLM contains API list."""
        captured_messages = []

        async def capture_llm_call(messages, **kwargs):
            captured_messages.extend(messages)
            return MockResponse(...)

        with patch("...invoke_structured_llm", side_effect=capture_llm_call):
            await workflow.execute(input_data, context)

        # Verify system prompt contains API info
        system_prompt = captured_messages[0]["content"]
        assert "## 利用可能なAPI" in system_prompt
        assert "/v1/utility/google_search" in system_prompt
```

### 5.3 受入テスト基準

```
✅ タスク分割で recommended_apis が全タスクに設定される（100%）
✅ システムプロンプトにAPI一覧が含まれる
✅ TaskMaster の URL が API 固有エンドポイントを指す
✅ body_template が API 固有パラメータを含む
✅ ワークフロー生成が LLM ベースで成功する（80%以上）
✅ 生成されたジョブが実行可能
```

### 5.4 テストカバレッジ目標

| モジュール | カバレッジ目標 |
|-----------|--------------|
| `shared/capability_utils.py` | 95% |
| `jobGeneratorV2/llm_utils.py` | 90% |
| `task_breakdown/decomposer.py` | 90% |
| `task_breakdown/workflow.py` | 85% |

---

## 6. 移行・互換性

### 6.1 後方互換性

| 項目 | 影響 | 対応 |
|------|------|------|
| V1 Job Generator | 影響なし | 別モジュール |
| 既存V2ジョブ | 影響なし | 新規生成のみ対象 |
| API定義 | 影響なし | 読み取りのみ |
| 外部インターフェース | 影響なし | 内部実装のみ変更 |

### 6.2 デプロイ考慮事項

- **フィーチャーフラグ不要**: 内部実装の修正のみ
- **ロールバック**: コード戻しで即時復旧可能
- **監視**: Langfuseでジョブ生成品質を監視

---

## 7. 成功基準

### 7.1 定量基準

| 指標 | 現状 | 目標 |
|------|------|------|
| recommended_apis 設定率 | 33% (1/3タスク) | 100% |
| LLMベース生成成功率 | 0% | 80%以上 |
| テンプレートフォールバック率 | 100% | 20%以下 |

### 7.2 定性基準

- 生成されたワークフローが実行可能
- API固有のパラメータが正しく設定される
- タスクチェーンのデータフローが正しい

---

## 8. 実装順序（更新版）

| 順序 | タスク | 見積 | 備考 |
|------|--------|------|------|
| 1 | `shared/__init__.py` 作成 | 0.1h | パッケージ初期化 |
| 2 | `shared/capability_utils.py` 作成 | 1h | 共通ユーティリティ |
| 3 | `jobGeneratorV2/types.py` 修正 | 0.5h | Capability型拡張 |
| 4 | `jobGeneratorV2/llm_utils.py` 修正 | 1h | プロンプトビルダー更新 |
| 5 | `task_breakdown/decomposer.py` 修正 | 0.5h | コンストラクタ追加 |
| 6 | `task_breakdown/workflow.py` 修正 | 0.5h | capabilities渡し |
| 7 | 単体テスト作成・実行 | 1h | shared + 既存テスト更新 |
| 8 | 結合テスト作成・実行 | 1h | 統合確認テスト |

**合計見積**: 5.6時間（Phase 1のみ）

---

## 9. レビュー履歴

| 日付 | レビュアー | 結果 | 指摘事項 |
|------|-----------|------|---------|
| 2026-01-07 | シニアアーキテクト | 条件付き承認 | Capability型不整合、V1共通化未検討 |
| 2026-01-07 | - | 修正完了 | shared/capability_utils.py追加、型定義修正 |

---

**作成日**: 2026-01-07
**更新日**: 2026-01-07
**Issue**: #342
**承認**: ✅ 承認（レビュー指摘対応済み）

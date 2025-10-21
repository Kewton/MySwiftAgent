# 設計方針: GraphAI Workflow Generator API

**作成日**: 2025-10-21
**更新日**: 2025-10-21 (JobMaster/TaskMaster ID対応、複数ワークフロー生成)
**ブランチ**: feature/issue/108
**担当**: Claude Code
**Issue**: https://github.com/Kewton/MySwiftAgent/issues/108

---

## 📋 要求・要件

### ビジネス要求

expertAgentの `/api/v1/job-generator` エンドポイントが生成したJobMaster/TaskMasterをもとに、GraphAiServer上で**実行可能な**LLMワークフロー（YAML形式）を自動生成し、動作確認までを完了するAIエージェントを実装する。

### 機能要件

#### 1. expertAgent: `/api/v1/workflow-generator` (NEW)
- **入力（XOR制約）**:
  - `job_master_id`: ジョブマスタID → ジョブに紐づく**全タスク**のワークフローを生成
  - `task_master_id`: タスクマスタID → **指定タスクのみ**のワークフローを生成

- **出力**: GraphAI YML形式のワークフロー定義（複数可） + 動作確認結果

- **処理フロー**:
  1. データベースからJobMaster/TaskMaster情報を取得
  2. 各TaskMasterごとに個別のワークフローYMLを生成（LLMベース）
  3. graphAiServerへYML登録
  4. テスト実行（サンプル入力で動作確認）
  5. 実行結果検証（非LLM）
  6. 失敗時の自己修復ループ（最大3回/タスク）

#### 2. graphAiServer: `/api/v1/workflows/register` (NEW)
- **入力**: `{ "workflow_name": "...", "workflow_yaml": "..." }`
- **処理**: YMLファイルを `config/graphai/` ディレクトリに保存
- **出力**: `{ "status": "success", "file_path": "/app/config/graphai/workflow_name.yml" }`

#### 3. Capability-based Workflow Generation
- `graphai_capabilities.yaml` で定義されたGraphAI標準エージェント（geminiAgent, anthropicAgent, fetchAgent等）のみ使用
- `expert_agent_capabilities.yaml` で定義されたexpertAgent APIエンドポイント（Gmail検索、Google検索、File Reader等）を活用
- 利用不可能な機能は使用しない（実現可能性を重視）

#### 4. TaskMaster→ワークフロー変換ロジック
- TaskMasterの説明文（`description`）から意図を理解
- TaskMasterの入力インタフェース（`input_interface_id`）と出力インタフェース（`output_interface_id`）をGraphAIのノード接続に変換
- 1タスク = 1ワークフローYML（タスク間の依存関係は考慮しない）

#### 5. 動作確認と自己修復
- **サンプル入力生成**: InterfaceMasterのinput_schemaから自動生成
- **テスト実行**: graphAiServerでワークフロー実行
- **検証（非LLM）**:
  - 正常終了チェック（HTTPステータスコード200）
  - 出力スキーマ検証（output_schemaと実際の出力を比較）
  - エラーログ解析（キーワードベース: "error", "exception", "failed"等）
- **自己修復ループ**:
  - 検証失敗時、エラー情報をLLMにフィードバックして再生成
  - 最大3回のリトライ（タスクごと）

#### 6. GraphAI Workflow Generation Rules準拠
- `GRAPHAI_WORKFLOW_GENERATION_RULES.md` に記載されたベストプラクティスに従う
- `sourceノード`、`outputノード`の必須要素を含む
- `fetchAgent`を使用する際は`inputs`ブロック内に`url`, `method`, `body`を正しく配置
- エラー回避パターンを適用

### 非機能要件

- **パフォーマンス**:
  - 単一タスク: 60秒以内に完了（リトライ含む）
  - 複数タスク（job_master_id指定時）: タスク数 × 60秒 + 30秒（並列処理余裕）
- **信頼性**:
  - LLM生成結果のYAML構文検証を実施
  - 実行結果の自動検証により、動作保証されたワークフローのみ返却
- **拡張性**: 新しいエージェントの追加に対応可能な設計
- **可用性**: myVaultによるAPI Key管理でセキュアな実行

---

## 🏗️ アーキテクチャ設計

### システム構成

```
┌─────────────────────────────────────────────────────────────────┐
│                         expertAgent                             │
│                                                                 │
│  ┌───────────────────┐           ┌────────────────────────────┐ │
│  │ /api/v1/          │           │ /api/v1/                   │ │
│  │ job-generator     │           │ workflow-generator (NEW)   │ │
│  │                   │           │                            │ │
│  │ 入力: 自然言語要求  │           │ 入力: job_master_id        │ │
│  │ 出力:              │           │      OR task_master_id     │ │
│  │  - job_master_id  │──────────▶│                            │ │
│  │  - task_master_ids│           │ 処理:                       │ │
│  └───────────────────┘           │  1. DB照会 (JobMaster/     │ │
│                                  │     TaskMaster取得)         │ │
│                                  │  2. 各タスクのYML生成       │ │
│                                  │  3. YML登録                │ │
│                                  │  4. テスト実行              │ │
│                                  │  5. 検証 (非LLM)           │ │
│                                  │  6. 自己修復ループ          │ │
│                                  │                            │ │
│                                  │ 出力:                       │ │
│                                  │  - workflows (複数可)       │ │
│                                  └────────────────────────────┘ │
│                                           │                     │
│                                           │ API呼び出し          │
│                                           ▼                     │
│  ┌─────────────────────────────────────────────────────────────┤
│  │ JobqueueClient (DB照会)                                     │
│  │  - GET /api/v1/job-masters/{job_master_id}                  │
│  │  - GET /api/v1/task-masters/{task_master_id}                │
│  │  - GET /api/v1/interface-masters/{interface_master_id}      │
│  └─────────────────────────────────────────────────────────────┘
└─────────────────────────────────────────────────────────────────┘
                                            │
                                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      GraphAiServer                              │
│                                                                 │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ /api/v1/workflows/register (NEW)                           │ │
│  │                                                            │ │
│  │ 入力: { workflow_name, workflow_yaml }                     │ │
│  │ 処理: config/graphai/ にYMLファイル保存                     │ │
│  │ 出力: { status, file_path }                                │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ /api/v1/workflows/{workflow_name} (既存または拡張)          │ │
│  │                                                            │ │
│  │ 入力: { user_input }                                       │ │
│  │ 処理: 登録済みワークフロー実行                               │ │
│  │ 出力: { status, result, logs }                             │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### データフロー（拡張版）

#### ケースA: job_master_id 指定時（複数ワークフロー生成）

```
1. ユーザー
   │
   │ POST /api/v1/workflow-generator
   │ { "job_master_id": 123 }
   ▼
2. workflow-generator (NEW)
   │
   │ === Phase 1: JobMaster情報取得 ===
   │ a. GET /api/v1/job-masters/123 (via JobqueueClient)
   │    → JobMaster詳細取得
   │
   │ b. JobMasterに紐づくTaskMasterリストを取得
   │    → JobMasterTask経由でtask_master_idsを取得
   │    → 各TaskMasterの詳細を取得
   │    例: [TaskMaster(id=1, name="企業名入力"), TaskMaster(id=2, name="分析")]
   │
   │ === Phase 2: 各TaskMasterのInterfaceMaster取得 ===
   │ c. GET /api/v1/interface-masters/{input_interface_id}
   │ d. GET /api/v1/interface-masters/{output_interface_id}
   │    → input_schema, output_schemaを取得
   │
   │ === Phase 3-8: 各TaskMasterごとにワークフロー生成ループ ===
   │ for each TaskMaster in task_masters:
   │
   │   === Phase 3: YML生成（LLM） ===
   │   e. LLMプロンプト生成
   │      - TaskMaster情報（name, description, url）
   │      - InterfaceMaster情報（input_schema, output_schema）
   │      - Capabilities情報
   │   f. Gemini 2.5 Flash or Claude Haiku 4.5 実行
   │   g. YAML構文検証
   │
   │   === Phase 4: YML登録 ===
   │   h. POST http://graphaiserver:8000/api/v1/workflows/register
   │      { "workflow_name": "task_1_workflow", "workflow_yaml": "..." }
   │
   │   === Phase 5: サンプル入力生成 ===
   │   i. input_schema から自動生成
   │      例: { "company_name": "sample_company_name" }
   │
   │   === Phase 6: テスト実行 ===
   │   j. POST http://graphaiserver:8000/api/v1/workflows/task_1_workflow
   │      { "user_input": { "company_name": "sample_company_name" } }
   │
   │   === Phase 7: 実行結果検証（非LLM） ===
   │   k. 検証ロジック実行:
   │      - 正常終了チェック（status_code == 200）
   │      - 出力スキーマ検証（output_schema vs 実際の出力）
   │      - エラーログ解析
   │
   │   === Phase 8: 失敗時の自己修復 ===
   │   l. 検証失敗の場合:
   │      - エラー情報をLLMにフィードバック
   │      - YML再生成（Phase 3に戻る、最大3回）
   │
   │   m. 成功の場合:
   │      - 次のTaskMasterへ
   │
   │ end for
   ▼
3. workflow-generator Response（複数ワークフロー）
   {
     "status": "success",
     "workflows": [
       {
         "task_master_id": 1,
         "task_name": "企業名入力",
         "workflow_yaml": "version: 0.5\nnodes:\n  source: {}\n  ...",
         "workflow_name": "task_1_workflow",
         "workflow_file_path": "/app/config/graphai/task_1_workflow.yml",
         "validation_result": {
           "is_valid": true,
           "syntax_check": "passed",
           "test_execution": "passed",
           "output_schema_validation": "passed"
         },
         "test_execution_result": {
           "status": "success",
           "output": { "company_name": "sample_company_name" },
           "execution_time_ms": 1200
         },
         "retry_count": 0
       },
       {
         "task_master_id": 2,
         "task_name": "売上データ分析",
         "workflow_yaml": "version: 0.5\nnodes:\n  source: {}\n  ...",
         "workflow_name": "task_2_workflow",
         "workflow_file_path": "/app/config/graphai/task_2_workflow.yml",
         "validation_result": {
           "is_valid": true,
           "syntax_check": "passed",
           "test_execution": "passed",
           "output_schema_validation": "passed"
         },
         "test_execution_result": {
           "status": "success",
           "output": { "report": "sample report text" },
           "execution_time_ms": 2300
         },
         "retry_count": 1
       }
     ],
     "summary": {
       "total_tasks": 2,
       "successful_tasks": 2,
       "failed_tasks": 0,
       "total_execution_time_ms": 5800
     }
   }
```

#### ケースB: task_master_id 指定時（単一ワークフロー生成）

```
1. ユーザー
   │
   │ POST /api/v1/workflow-generator
   │ { "task_master_id": 1 }
   ▼
2. workflow-generator (NEW)
   │
   │ === Phase 1: TaskMaster情報取得 ===
   │ a. GET /api/v1/task-masters/1 (via JobqueueClient)
   │    → TaskMaster詳細取得
   │
   │ === Phase 2: InterfaceMaster取得 ===
   │ b. GET /api/v1/interface-masters/{input_interface_id}
   │ c. GET /api/v1/interface-masters/{output_interface_id}
   │
   │ === Phase 3-8: ワークフロー生成（ケースAと同様） ===
   │ （1つのTaskMasterのみ処理）
   ▼
3. workflow-generator Response（単一ワークフロー）
   {
     "status": "success",
     "workflows": [
       {
         "task_master_id": 1,
         "task_name": "企業名入力",
         "workflow_yaml": "...",
         "workflow_name": "task_1_workflow",
         "workflow_file_path": "/app/config/graphai/task_1_workflow.yml",
         "validation_result": { ... },
         "test_execution_result": { ... },
         "retry_count": 0
       }
     ],
     "summary": {
       "total_tasks": 1,
       "successful_tasks": 1,
       "failed_tasks": 0,
       "total_execution_time_ms": 2800
     }
   }
```

### 技術選定

| 技術要素 | 選定技術 | 選定理由 |
|---------|---------|---------|
| **expertAgent Framework** | FastAPI + Python | expertAgentの既存スタックと統一 |
| **graphAiServer Framework** | Express + TypeScript | graphAiServerの既存スタックと統一 |
| **LLM Provider** | Gemini 2.5 Flash（第一優先）<br>Claude Haiku 4.5（フォールバック） | - Gemini: コスト効率が高い、JSON Schemaモード対応<br>- Claude: 高品質な構造化出力 |
| **YAML Parser** | PyYAML | Python標準的なYAMLライブラリ |
| **Prompt Engineering** | Jinja2 Template | 複雑なプロンプトの構造化管理 |
| **Validation** | Pydantic + JSON Schema | 型安全性とスキーマ検証 |
| **Capabilities管理** | YAML Files | 既存のgraphai_capabilities.yaml, expert_agent_capabilities.yaml を活用 |
| **DB Access** | JobqueueClient (httpx) | 既存のJobqueue API統合 |

### ディレクトリ構成

```
expertAgent/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── job_generator_endpoints.py       # 既存
│   │       └── workflow_generator_endpoints.py  # NEW
│   ├── schemas/
│   │   ├── job_generator.py                     # 既存
│   │   └── workflow_generator.py                # NEW
│   ├── core/
│   │   └── workflow_generation/                 # NEW
│   │       ├── __init__.py
│   │       ├── capabilities_loader.py           # Capabilitiesファイル読み込み
│   │       ├── prompt_builder.py                # LLMプロンプト生成
│   │       ├── llm_client.py                    # LLM API呼び出し
│   │       ├── yaml_validator.py                # YAML構文検証
│   │       ├── sample_input_generator.py        # サンプル入力データ生成
│   │       ├── execution_validator.py           # 実行結果検証（非LLM）
│   │       ├── workflow_tester.py               # テスト実行ロジック
│   │       ├── task_data_fetcher.py             # NEW: TaskMaster/InterfaceMaster取得
│   │       └── workflow_generator.py            # メインロジック（複数タスク対応）
│   └── templates/
│       └── workflow_generation/                 # NEW
│           ├── workflow_prompt.j2               # Jinja2プロンプトテンプレート
│           └── workflow_fix_prompt.j2           # 修正用プロンプト
└── tests/
    ├── unit/
    │   ├── test_workflow_generator_endpoints.py  # NEW
    │   ├── test_capabilities_loader.py           # NEW
    │   ├── test_prompt_builder.py                # NEW
    │   ├── test_yaml_validator.py                # NEW
    │   ├── test_sample_input_generator.py        # NEW
    │   ├── test_execution_validator.py           # NEW
    │   ├── test_workflow_tester.py               # NEW
    │   └── test_task_data_fetcher.py             # NEW
    └── integration/
        └── test_workflow_generator_api.py        # NEW

graphAiServer/
├── src/
│   ├── routes/
│   │   └── workflows.ts                         # NEW
│   ├── controllers/
│   │   └── workflowController.ts                # NEW
│   └── services/
│       └── workflowRegistrationService.ts       # NEW
├── config/
│   └── graphai/                                 # YML保存先
│       └── (動的に生成されたワークフロー)
└── tests/
    ├── unit/
    │   └── test_workflow_registration.test.ts   # NEW
    └── integration/
        └── test_workflow_register_api.test.ts   # NEW
```

---

## 🎯 設計上の決定事項

### 1. LLM選定: Gemini 2.5 Flash を第一優先とする

**判断理由**:
- graphai_capabilities.yamlでgeminiAgentが「推奨デフォルト」に指定されている
- コスト効率が高い（Claude Haikuよりも安価）
- JSON SchemaモードによるStructured Outputが利用可能
- expertAgentの既存実装でGemini APIが既に統合済み

**実装方針**:
```python
# 優先順位: Gemini → Claude
try:
    result = await generate_workflow_with_gemini(...)
except Exception as e:
    logger.warning(f"Gemini generation failed: {e}. Falling back to Claude.")
    result = await generate_workflow_with_claude(...)
```

### 2. 入力形式: XOR制約（job_master_id OR task_master_id）

**判断理由**:
- ユーザーの柔軟性を確保（ジョブ全体 or 個別タスク）
- 明確なバリデーションで誤使用を防止
- job_master_id指定時は複数ワークフロー生成、task_master_id指定時は単一ワークフロー生成

**実装方針**:
```python
class WorkflowGeneratorRequest(BaseModel):
    job_master_id: int | None = Field(default=None, description="Generate workflows for all tasks in this job")
    task_master_id: int | None = Field(default=None, description="Generate workflow for a single task")

    @model_validator(mode="after")
    def validate_xor(self):
        if (self.job_master_id is None) == (self.task_master_id is None):
            raise ValueError("Exactly one of 'job_master_id' or 'task_master_id' must be provided")
        return self
```

### 3. TaskMasterデータ取得戦略

**判断理由**:
- JobqueueClientを使用してRESTful APIで取得
- データベース直接アクセスではなく、既存APIを活用
- キャッシュ不要（都度最新情報を取得）

**実装方針**:
```python
# app/core/workflow_generation/task_data_fetcher.py
class TaskDataFetcher:
    def __init__(self):
        self.client = JobqueueClient()

    async def fetch_task_masters_by_job_master_id(
        self, job_master_id: int
    ) -> list[dict]:
        """
        JobMasterに紐づく全TaskMasterを取得

        Args:
            job_master_id: JobMaster ID

        Returns:
            TaskMaster情報のリスト（InterfaceMaster情報含む）
        """
        # 1. JobMaster取得
        job_master = await self.client.get_job_master(str(job_master_id))

        # 2. JobMasterTaskを介してTaskMaster IDリストを取得
        # （実際のAPIは job_master["tasks"] などに含まれると仮定）
        task_master_ids = job_master.get("task_master_ids", [])

        # 3. 各TaskMasterとInterfaceMasterを取得
        task_masters = []
        for task_master_id in task_master_ids:
            task_master = await self._fetch_task_master_with_interfaces(task_master_id)
            task_masters.append(task_master)

        return task_masters

    async def fetch_task_master_by_id(
        self, task_master_id: int
    ) -> dict:
        """
        TaskMaster IDから単一TaskMasterを取得

        Args:
            task_master_id: TaskMaster ID

        Returns:
            TaskMaster情報（InterfaceMaster情報含む）
        """
        return await self._fetch_task_master_with_interfaces(task_master_id)

    async def _fetch_task_master_with_interfaces(
        self, task_master_id: int
    ) -> dict:
        """
        TaskMasterとそのInterfaceMasterを取得

        Returns:
            {
                "task_master_id": int,
                "name": str,
                "description": str,
                "url": str,
                "input_interface": { "input_schema": {...} },
                "output_interface": { "output_schema": {...} }
            }
        """
        # TaskMaster取得
        task_master = await self.client.get_task_master(str(task_master_id))

        # InterfaceMaster取得
        input_interface = await self.client.get_interface_master(
            task_master["input_interface_id"]
        )
        output_interface = await self.client.get_interface_master(
            task_master["output_interface_id"]
        )

        return {
            "task_master_id": task_master["id"],
            "name": task_master["name"],
            "description": task_master["description"],
            "url": task_master["url"],
            "method": task_master["method"],
            "input_interface": input_interface,
            "output_interface": output_interface,
        }
```

### 4. プロンプト設計: 単一タスク志向アプローチ

**判断理由**:
- 1 TaskMaster = 1 ワークフローYML
- タスク間のデータフローは考慮しない（各タスクは独立）
- シンプルで理解しやすい設計

**実装方針**:
```jinja2
# app/templates/workflow_generation/workflow_prompt.j2
あなたはGraphAI YMLワークフロー生成の専門家です。

# タスク情報
タスク名: {{ task_master.name }}
タスク説明: {{ task_master.description }}
実行URL: {{ task_master.url }}

# 入力スキーマ
{{ task_master.input_interface.input_schema | tojson(indent=2) }}

# 出力スキーマ
{{ task_master.output_interface.output_schema | tojson(indent=2) }}

# 利用可能なエージェント
{{ capabilities | tojson(indent=2) }}

# ワークフロー生成ルール
{{ generation_rules }}

# あなたのタスク
上記のタスク情報をもとに、GraphAI YML形式のワークフローを生成してください。

## 要件
1. sourceノードはuser_inputを受け取る（input_schemaに準拠）
2. outputノードはtask_master.urlを呼び出して結果を返す（output_schemaに準拠）
3. 利用可能なエージェントのみ使用（graphai_capabilities, expert_agent_capabilitiesに記載のもの）
4. GRAPHAI_WORKFLOW_GENERATION_RULESに準拠

## 出力形式
YAML形式で出力してください。説明文は不要です。
```

### 5. YAML検証戦略

**判断理由**:
- LLM生成結果は構文エラーを含む可能性がある
- 必須要素の欠落を防ぐため、検証ロジックを実装

**実装方針**:
```python
# app/core/workflow_generation/yaml_validator.py
class WorkflowYAMLValidator:
    @staticmethod
    def validate(yaml_content: str) -> tuple[bool, list[str]]:
        errors = []

        # 1. YAML構文チェック
        try:
            data = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            errors.append(f"YAML syntax error: {e}")
            return False, errors

        # 2. 必須要素チェック
        if "version" not in data:
            errors.append("Missing required field: version")
        if "nodes" not in data:
            errors.append("Missing required field: nodes")
        if "source" not in data.get("nodes", {}):
            errors.append("Missing required node: source")

        # 3. isResult: true を持つノードが存在するか
        has_result = any(
            node.get("isResult") for node in data.get("nodes", {}).values()
        )
        if not has_result:
            errors.append("At least one node must have 'isResult: true'")

        return len(errors) == 0, errors
```

### 6. サンプル入力データ生成戦略

**判断理由**:
- テスト実行には実際の入力データが必要
- InterfaceMasterのinput_schemaから自動生成することで、手動設定を不要にする

**実装方針**:
```python
# app/core/workflow_generation/sample_input_generator.py
class SampleInputGenerator:
    @staticmethod
    def generate_from_schema(input_schema: dict) -> dict:
        """
        JSON Schemaから適切なサンプルデータを生成

        Args:
            input_schema: InterfaceMasterのinput_schema

        Returns:
            サンプル入力データ（dict）
        """
        if input_schema.get("type") != "object":
            return {}

        properties = input_schema.get("properties", {})
        sample_data = {}

        for prop_name, prop_schema in properties.items():
            prop_type = prop_schema.get("type", "string")

            if prop_type == "string":
                sample_data[prop_name] = f"sample_{prop_name}"
            elif prop_type == "integer":
                sample_data[prop_name] = 123
            elif prop_type == "number":
                sample_data[prop_name] = 123.45
            elif prop_type == "boolean":
                sample_data[prop_name] = True
            elif prop_type == "array":
                sample_data[prop_name] = ["sample_item"]
            elif prop_type == "object":
                sample_data[prop_name] = {}

        return sample_data
```

### 7. 実行結果検証戦略（非LLM）

**判断理由**:
- LLMベースの検証は不確実性が高く、コストも高い
- ルールベース検証で十分に実行結果を評価可能

**実装方針**:
```python
# app/core/workflow_generation/execution_validator.py
class ExecutionValidator:
    @staticmethod
    def validate_execution_result(
        response: dict,
        expected_output_schema: dict
    ) -> tuple[bool, list[str]]:
        """
        実行結果を検証（非LLM）

        Args:
            response: GraphAiServerからのレスポンス
            expected_output_schema: 期待される出力スキーマ

        Returns:
            (is_valid, errors)
        """
        errors = []

        # 1. HTTPステータスチェック
        if response.get("status") != "success":
            errors.append(f"Execution failed with status: {response.get('status')}")
            return False, errors

        # 2. エラーログチェック
        logs = response.get("logs", "")
        error_keywords = ["error", "exception", "failed", "traceback"]
        if any(keyword in logs.lower() for keyword in error_keywords):
            errors.append(f"Error found in logs: {logs[:200]}")

        # 3. 出力スキーマ検証（JSON Schema validation）
        result = response.get("result", {})
        try:
            jsonschema.validate(instance=result, schema=expected_output_schema)
        except jsonschema.ValidationError as e:
            errors.append(f"Output schema validation failed: {e.message}")

        return len(errors) == 0, errors
```

### 8. 複数ワークフロー生成戦略

**判断理由**:
- job_master_id指定時は複数TaskMasterを処理
- 各TaskMasterは独立してワークフロー生成・検証
- 1つのタスクが失敗しても他のタスクは継続

**実装方針**:
```python
MAX_RETRY = 3

async def generate_workflows_for_job_master(
    job_master_id: int
) -> dict:
    """
    JobMasterに紐づく全TaskMasterのワークフローを生成

    Returns:
        {
            "status": "success" | "partial_success" | "failed",
            "workflows": [WorkflowResult, ...],
            "summary": {...}
        }
    """
    # 1. TaskMaster取得
    fetcher = TaskDataFetcher()
    task_masters = await fetcher.fetch_task_masters_by_job_master_id(job_master_id)

    # 2. 各TaskMasterごとにワークフロー生成
    workflows = []
    successful_count = 0
    failed_count = 0

    for task_master in task_masters:
        try:
            workflow_result = await generate_workflow_for_task_master(
                task_master, max_retry=MAX_RETRY
            )
            workflows.append(workflow_result)
            successful_count += 1
        except WorkflowGenerationError as e:
            logger.error(f"Failed to generate workflow for task {task_master['task_master_id']}: {e}")
            workflows.append({
                "task_master_id": task_master["task_master_id"],
                "task_name": task_master["name"],
                "status": "failed",
                "error_message": str(e)
            })
            failed_count += 1

    # 3. 全体ステータス判定
    if failed_count == 0:
        status = "success"
    elif successful_count > 0:
        status = "partial_success"
    else:
        status = "failed"

    return {
        "status": status,
        "workflows": workflows,
        "summary": {
            "total_tasks": len(task_masters),
            "successful_tasks": successful_count,
            "failed_tasks": failed_count
        }
    }
```

### 9. 自己修復ループ戦略

**判断理由**:
- LLM生成は確率的であり、1回目で完璧なワークフローが生成されるとは限らない
- エラー情報をフィードバックすることで、LLMが自己修復可能

**実装方針**:
```python
async def generate_workflow_for_task_master(
    task_master: dict,
    max_retry: int = 3
) -> dict:
    """
    単一TaskMasterのワークフローを生成（自己修復ループ含む）

    Returns:
        WorkflowResult
    """
    previous_errors = []

    for attempt in range(max_retry):
        logger.info(f"Workflow generation attempt {attempt + 1}/{max_retry} for task {task_master['task_master_id']}")

        # Phase 1: YML生成
        if attempt == 0:
            yaml_content = await llm_client.generate_workflow(task_master, capabilities, generation_rules)
        else:
            yaml_content = await llm_client.fix_workflow(
                task_master, capabilities, generation_rules,
                previous_yaml=yaml_content,
                errors=previous_errors
            )

        # Phase 2: YAML構文検証
        is_valid, syntax_errors = yaml_validator.validate(yaml_content)
        if not is_valid:
            previous_errors = syntax_errors
            continue

        # Phase 3: YML登録
        workflow_name = f"task_{task_master['task_master_id']}_workflow"
        registration_result = await register_workflow_to_graphai(workflow_name, yaml_content)
        if not registration_result["success"]:
            previous_errors = [f"Registration failed: {registration_result['error']}"]
            continue

        # Phase 4: テスト実行
        sample_input = sample_input_generator.generate_from_schema(
            task_master["input_interface"]["input_schema"]
        )
        execution_result = await execute_workflow_on_graphai(workflow_name, sample_input)

        # Phase 5: 実行結果検証
        is_valid, execution_errors = execution_validator.validate_execution_result(
            execution_result,
            task_master["output_interface"]["output_schema"]
        )

        if is_valid:
            logger.info(f"Workflow validation succeeded on attempt {attempt + 1}")
            return {
                "task_master_id": task_master["task_master_id"],
                "task_name": task_master["name"],
                "status": "success",
                "workflow_yaml": yaml_content,
                "workflow_name": workflow_name,
                "workflow_file_path": registration_result["file_path"],
                "validation_result": {
                    "is_valid": True,
                    "syntax_check": "passed",
                    "test_execution": "passed",
                    "output_schema_validation": "passed"
                },
                "test_execution_result": execution_result,
                "retry_count": attempt
            }
        else:
            previous_errors = execution_errors

    # 最大リトライ回数到達
    raise WorkflowGenerationError(
        f"Failed to generate valid workflow after {max_retry} attempts. "
        f"Last errors: {previous_errors}"
    )
```

### 10. graphAiServer YML登録API設計

**判断理由**:
- expertAgentから動的にワークフローYMLを登録できるようにする
- ファイルシステムへの直接書き込みではなく、APIを介することでセキュリティを確保

**実装方針（TypeScript）**:
```typescript
// graphAiServer/src/routes/workflows.ts
import express from 'express';
import { registerWorkflow } from '../controllers/workflowController';

const router = express.Router();

router.post('/workflows/register', registerWorkflow);

export default router;
```

```typescript
// graphAiServer/src/controllers/workflowController.ts
import fs from 'fs/promises';
import path from 'path';

export const registerWorkflow = async (req, res) => {
  const { workflow_name, workflow_yaml } = req.body;

  // バリデーション
  if (!workflow_name || !workflow_yaml) {
    return res.status(400).json({
      status: 'error',
      message: 'workflow_name and workflow_yaml are required'
    });
  }

  // ファイル名のサニタイズ（セキュリティ）
  const sanitizedName = workflow_name.replace(/[^a-zA-Z0-9_-]/g, '_');
  const filePath = path.join(__dirname, '../../config/graphai', `${sanitizedName}.yml`);

  try:
    // YMLファイル保存
    await fs.writeFile(filePath, workflow_yaml, 'utf8');

    return res.status(200).json({
      status: 'success',
      file_path: filePath,
      workflow_name: sanitizedName
    });
  } catch (error) {
    return res.status(500).json({
      status: 'error',
      message: `Failed to save workflow: ${error.message}`
    });
  }
};
```

---

## ✅ 制約条件チェック結果

### コード品質原則
- [x] **SOLID原則**: 遵守
  - Single Responsibility: 各モジュールは明確な責務（TaskMaster取得、Capabilities読み込み、プロンプト生成、LLM実行、YAML検証、実行検証）
  - Open-Closed: 新しいLLM Providerや検証ロジックの追加が容易
  - Liskov Substitution: LLMクライアントの抽象化により、GeminiとClaudeを透過的に切り替え可能
  - Interface Segregation: 各モジュールは必要最小限のインタフェースのみ公開
  - Dependency Inversion: myVault経由でのAPI Key管理、JobqueueClient経由でのDB照会
- [x] **KISS原則**: 遵守
  - シンプルなデータフロー（取得 → 生成 → 登録 → テスト → 検証 → 修復）
  - 複雑なロジックは避け、LLMに任せる
- [x] **YAGNI原則**: 遵守
  - 現時点で必要な機能のみ実装（タスク間の依存関係解決などは将来対応）
- [x] **DRY原則**: 遵守
  - Capabilitiesファイルは1箇所で管理（job-generatorと共有）
  - プロンプトテンプレートはJinja2で再利用可能
  - ワークフロー生成ロジックは単一関数で共通化

### アーキテクチャガイドライン
- [x] **architecture-overview.md**: 準拠
  - expertAgentの既存スタック（FastAPI + Python + myVault連携）を活用
  - graphAiServerの既存スタック（Express + TypeScript）を活用
  - GraphAiServerとの連携フロー（expertAgentがYML生成→登録、GraphAiServerが実行）を維持
  - JobqueueClientによるRESTful API統合
- [x] **レイヤー分離**: 遵守
  - API層（`endpoints.py`, `routes.ts`）、ビジネスロジック層（`core/workflow_generation/`, `controllers/`）、データ層（`schemas.py`、JobqueueClient）を分離

### 設定管理ルール
- [x] **環境変数**: 遵守
  - `MYVAULT_ENABLED`, `MYVAULT_BASE_URL`, `MYVAULT_SERVICE_TOKEN` を使用
  - API KeysはmyVaultから動的取得
  - graphAiServerのURLは環境変数で管理（`GRAPHAISERVER_BASE_URL`）
  - JobqueueのURLは環境変数で管理（`JOBQUEUE_API_URL`）
- [x] **myVault統合**: 遵守
  - `GOOGLE_API_KEY`, `ANTHROPIC_API_KEY` をmyVaultで管理

### 品質担保方針
- [x] **単体テストカバレッジ**: 目標90%以上
  - expertAgent:
    - `capabilities_loader.py`: 100%（ファイル読み込み、キャッシュロジック）
    - `prompt_builder.py`: 95%（Jinja2テンプレート生成）
    - `yaml_validator.py`: 100%（各種検証ケース）
    - `llm_client.py`: 90%（正常ケース、エラーケース、リトライロジック）
    - `sample_input_generator.py`: 100%（各種データ型のサンプル生成）
    - `execution_validator.py`: 100%（正常ケース、エラーケース、スキーマ検証）
    - `workflow_tester.py`: 90%（テスト実行ロジック）
    - `task_data_fetcher.py`: 95%（JobqueueClient統合、データ取得）
  - graphAiServer:
    - `workflowController.ts`: 90%（正常ケース、エラーケース、ファイル保存）
- [x] **結合テストカバレッジ**: 目標50%以上
  - expertAgent:
    - `/api/v1/workflow-generator` エンドポイントの正常ケース（job_master_id, task_master_id）
    - XORバリデーションエラーケース
    - YAML構文エラーケース
    - 自己修復ループの動作確認
    - 複数ワークフロー生成の動作確認
  - graphAiServer:
    - `/api/v1/workflows/register` エンドポイントの正常ケース
    - バリデーションエラーケース

### CI/CD準拠
- [x] **PRラベル**: `feature` ラベルを付与予定（minor版数アップ）
- [x] **コミットメッセージ**: Conventional Commits規約に準拠
  - expertAgent: `feat(expertAgent): add workflow generator API with JobMaster/TaskMaster support`
  - graphAiServer: `feat(graphAiServer): add workflow registration API`
- [x] **pre-push-check-all.sh**: 実行予定

### 参照ドキュメント遵守
- [x] **GRAPHAI_WORKFLOW_GENERATION_RULES.md**: 準拠
  - sourceノード、outputノード、isResult: true の必須要素を含む
  - fetchAgentの正しい構造（inputs内にurl, method, body）
  - エラー回避パターン適用
- [ ] **NEW_PROJECT_SETUP.md**: 非該当（新プロジェクト追加ではない）

### 違反・要検討項目
なし

---

## 📚 参考ドキュメント

**必須参照**:
- [GraphAI Workflow Generation Rules](../../../graphAiServer/docs/GRAPHAI_WORKFLOW_GENERATION_RULES.md)
- [GraphAI Capabilities](../../../expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/utils/config/graphai_capabilities.yaml)
- [ExpertAgent Capabilities](../../../expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/utils/config/expert_agent_capabilities.yaml)

**推奨参照**:
- [Architecture Overview](../../../docs/design/architecture-overview.md)
- [Environment Variables](../../../docs/design/environment-variables.md)
- [MyVault Integration](../../../docs/design/myvault-integration.md)

---

## 🚀 次のステップ

1. **設計方針レビュー**: ユーザーからのフィードバックを受ける
2. **作業計画作成**: Phase分解、スケジュール策定（`work-plan.md`）
3. **実装開始**: Phase 1（expertAgent基盤実装）から着手

---

最終更新: 2025-10-21 (JobMaster/TaskMaster ID対応、複数ワークフロー生成)

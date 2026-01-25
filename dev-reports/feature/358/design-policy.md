# Issue #358: body_template整合性バリデーション - 設計方針書

## 1. 概要

### 1.1 背景

Job Generator V2において、TaskMasterの`body_template`に含まれるテンプレート変数（`{{job.body}}`、`{{tasks[N].output_data}}`など）の整合性検証が実行時まで行われない問題があります。これにより、不整合なジョブが生成され、実行時にGraphAiServerから「inputs is required」エラーが発生し、エラー原因の特定が困難になっています。

### 1.2 目的

REGISTRATIONフェーズにおいて、TaskMaster作成前に`body_template`の整合性を検証する機能を追加し、以下を実現します：

- 不整合なジョブ生成の防止
- エラー発見の早期化
- 明確なエラーメッセージの提供
- ジョブ実行時の必須パラメータの特定

### 1.3 参照ドキュメント

- `expertAgent/docs/API_REFERENCE.md` - Expert Agent API仕様
- `docs/spec/job-generation-workflow.md` - Job Generator仕様とLangGraphエージェント設計
- `CLAUDE.md` - 開発ガイドラインとコード品質原則

## 2. システムアーキテクチャ設計

### 2.1 システム構成図

```mermaid
graph TD
    subgraph "REGISTRATION Phase"
        A[RegistrationWorkflow] --> B[MasterManagerSubWorkflow]
        B --> C[InterfaceMaster作成]
        B --> D[body_template構築]
        D --> E[BodyTemplateValidator<br/>（新規追加）]
        E --> F{検証結果}
        F -->|OK| G[TaskMaster作成]
        F -->|NG| H[エラーで生成中止]
        G --> I[JobMaster作成]
        I --> J[JobMasterTask作成]
    end

    subgraph "Validation Layer"
        E --> K[テンプレート変数抽出]
        K --> L[job.body参照検証]
        K --> M[tasks[N]参照検証]
        K --> N[必須パラメータ抽出]
        L --> O[input_schemaとの照合]
        M --> P[タスク順序の妥当性確認]
        M --> Q[output_schemaとの照合]
    end
```

### 2.2 レイヤー構成

| レイヤー | 責務 | 主要コンポーネント |
|---------|------|-------------------|
| **Workflow層** | 処理フロー制御 | RegistrationWorkflow, MasterManagerSubWorkflow |
| **Validation層** | body_template検証 | BodyTemplateValidator（新規） |
| **Domain層** | ビジネスロジック | TaskMaster作成、テンプレート構築 |
| **Integration層** | 外部サービス連携 | JobqueueClient |

## 3. 技術選定

| カテゴリ | 選定技術 | 選定理由 | 既存との整合性 |
|---------|---------|---------|---------------|
| バリデーションパターン | Strategy Pattern | エンジン（GraphAI/TaskFlow）ごとの検証ルール分離 | 既存のengine_strategyパターンに準拠 |
| エラーハンドリング | Result型パターン | 詳細なエラー情報の伝達 | PendingWorkflowValidationResultと同様 |
| テンプレート解析 | 正規表現 + AST | `{{...}}`パターンの確実な抽出 | variable_patterns.pyの既存実装を活用 |
| スキーマ照合 | Pydantic検証 | 型安全性の確保 | InterfaceSchemaの既存実装と整合 |

## 4. 設計パターンと詳細設計

### 4.1 採用する設計パターン

#### 4.1.1 Validator Patternの拡張

既存の`validators/`ディレクトリに新規バリデータを追加し、責任を分離：

```python
# validators/body_template_validator.py
class BodyTemplateValidator:
    """body_templateの整合性を検証する"""

    def validate(
        self,
        body_template: dict[str, Any],
        task_order: int,
        interfaces: dict[str, InterfaceSchema],
        sorted_tasks: list[TaskDefinition],
        engine: str = "taskflow"
    ) -> BodyTemplateValidationResult:
        """body_templateを検証し、結果を返す"""
```

#### 4.1.2 Strategy Patternによるエンジン別検証

```python
# validators/body_template_validator.py
class ValidationStrategy(Protocol):
    """エンジン別の検証戦略インターフェース"""
    def validate(self, template: dict, context: ValidationContext) -> ValidationResult:
        ...

class TaskFlowValidationStrategy:
    """TaskFlowエンジン用の検証戦略"""

class GraphAIValidationStrategy:
    """GraphAIエンジン用の検証戦略"""
```

### 4.2 データモデル設計

#### 4.2.1 検証結果のデータ構造

```python
@dataclass
class BodyTemplateValidationResult:
    """body_template検証結果"""
    is_valid: bool
    errors: list[ValidationError]
    warnings: list[ValidationWarning]
    required_job_body_fields: list[RequiredField]
    metadata: dict[str, Any]

@dataclass
class ValidationError:
    """検証エラー"""
    error_type: ErrorType  # MISSING_REFERENCE, INVALID_INDEX, SCHEMA_MISMATCH
    field_path: str
    message: str
    suggestion: str | None

@dataclass
class RequiredField:
    """ジョブ実行時の必須フィールド"""
    field_path: str  # e.g., "user_input", "config.api_key"
    json_schema: dict[str, Any]
    source_template: str  # e.g., "{{job.body.user_input}}"
```

### 4.3 検証フローの詳細

#### 4.3.1 テンプレート変数の抽出

```python
def extract_template_variables(template: dict[str, Any]) -> list[TemplateVariable]:
    """{{...}}パターンを再帰的に抽出"""
    variables = []

    def extract_from_value(value: Any, path: str = ""):
        if isinstance(value, str):
            # 正規表現で{{...}}を抽出
            pattern = r'\{\{([^}]+)\}\}'
            matches = re.finditer(pattern, value)
            for match in matches:
                variables.append(TemplateVariable(
                    expression=match.group(1).strip(),
                    field_path=path,
                    raw_template=match.group(0)
                ))
        elif isinstance(value, dict):
            for k, v in value.items():
                extract_from_value(v, f"{path}.{k}" if path else k)
        elif isinstance(value, list):
            for i, item in enumerate(value):
                extract_from_value(item, f"{path}[{i}]")

    extract_from_value(template)
    return variables
```

#### 4.3.2 job.body参照の検証

```python
def validate_job_body_references(
    variables: list[TemplateVariable],
    input_schema: dict[str, Any]
) -> list[ValidationError]:
    """job.body.*参照をinput_schemaと照合"""
    errors = []

    for var in variables:
        if var.expression.startswith("job.body"):
            # job.body.user_input → ["user_input"]
            path_parts = var.expression.split(".")[2:]  # "job", "body"を除く

            # JSON Schemaと照合
            if not is_valid_schema_path(input_schema, path_parts):
                errors.append(ValidationError(
                    error_type=ErrorType.SCHEMA_MISMATCH,
                    field_path=var.field_path,
                    message=f"'{var.expression}' not found in input_schema",
                    suggestion=suggest_similar_field(input_schema, path_parts)
                ))

    return errors
```

#### 4.3.3 tasks[N]参照の検証

```python
def validate_task_references(
    variables: list[TemplateVariable],
    task_order: int,
    sorted_tasks: list[TaskDefinition],
    interfaces: dict[str, InterfaceSchema]
) -> list[ValidationError]:
    """tasks[N].output_data参照を検証"""
    errors = []

    for var in variables:
        match = re.match(r'tasks\[(\d+)\]\.output_data', var.expression)
        if match:
            ref_index = int(match.group(1))

            # タスク順序の妥当性確認
            if ref_index >= task_order:
                errors.append(ValidationError(
                    error_type=ErrorType.INVALID_INDEX,
                    field_path=var.field_path,
                    message=f"Cannot reference future task[{ref_index}] from task[{task_order}]"
                ))
            elif ref_index >= len(sorted_tasks):
                errors.append(ValidationError(
                    error_type=ErrorType.INVALID_INDEX,
                    field_path=var.field_path,
                    message=f"Task index {ref_index} out of range (total: {len(sorted_tasks)})"
                ))
            else:
                # output_schemaとの整合性確認
                ref_task = sorted_tasks[ref_index]
                interface = interfaces.get(ref_task.id)
                if interface and interface.output_schema:
                    # 次タスクのinput_schemaと前タスクのoutput_schemaを比較
                    current_interface = interfaces.get(sorted_tasks[task_order].id)
                    if current_interface and current_interface.input_schema:
                        schema_errors = compare_schemas(
                            interface.output_schema,
                            current_interface.input_schema
                        )
                        errors.extend(schema_errors)

    return errors
```

## 5. API設計

### 5.1 BodyTemplateValidatorの統合

```python
# workflows/registration/master_manager.py の修正
class MasterManagerSubWorkflow:
    def __init__(self, ...):
        self._validator = BodyTemplateValidator()

    async def create_masters(self, ...):
        # ... 既存のコード ...

        # TaskMaster作成のループ内
        for order, task in enumerate(sorted_tasks):
            # ... mapping取得など ...

            body_template = self._build_body_template(order)

            # 新規: バリデーション実行
            validation_result = self._validator.validate(
                body_template=body_template,
                task_order=order,
                interfaces=interfaces,
                sorted_tasks=sorted_tasks,
                engine=self._engine
            )

            if not validation_result.is_valid:
                # エラーメッセージ生成
                error_details = self._format_validation_errors(
                    task.id, validation_result.errors
                )
                raise WorkflowError(
                    f"body_template validation failed for task {task.id}: {error_details}",
                    error_type=ErrorType.PERMANENT
                )

            # 警告のログ出力
            if validation_result.warnings:
                for warning in validation_result.warnings:
                    logger.warning(
                        f"body_template warning for task {task.id}: {warning.message}"
                    )

            # TaskMaster作成（既存処理）
            task_master_id = await self._create_task_master(...)

            # 必須パラメータ情報の保存（将来拡張用）
            if validation_result.required_job_body_fields:
                await self._store_required_fields(
                    task_master_id,
                    validation_result.required_job_body_fields
                )
```

## 6. セキュリティ設計

### 6.1 テンプレートインジェクション対策

- テンプレート変数の評価は行わず、構文解析のみ実施
- 任意コード実行の防止
- 再帰的なテンプレート参照の検出と防止

### 6.2 データ検証

- 入力データのサニタイゼーション
- JSON Schemaによる厳密な型検証
- 最大再帰深度の制限

## 7. パフォーマンス設計

### 7.1 効率的な検証

- テンプレート変数の抽出結果をキャッシュ
- 大規模なスキーマに対する最適化されたパス探索
- 非同期処理による並列検証（必要に応じて）

### 7.2 スケーラビリティ

- タスク数に対してO(n)の計算量
- メモリ使用量の最小化
- 大規模ワークフローへの対応

## 8. 設計上の決定事項とトレードオフ

### 8.1 採用した設計の理由

| 決定事項 | 理由 | トレードオフ |
|---------|------|-------------|
| REGISTRATIONフェーズでの検証 | 早期エラー検出、明確なエラーメッセージ | 処理時間の若干の増加 |
| Strategy Patternの採用 | エンジン別ロジックの分離、拡張性 | クラス数の増加 |
| 必須フィールド情報の抽出 | 実行時エラーの事前防止 | 追加の解析処理 |

### 8.2 代替案との比較

| 代替案 | メリット | デメリット | 不採用理由 |
|--------|--------|-----------|-----------|
| 実行時検証のみ | 実装が簡単 | エラー発見が遅い | 現状の問題を解決できない |
| LLMによる検証 | 柔軟な検証 | 処理時間、コスト | 決定的な検証には不適 |
| 静的型システム | コンパイル時検証 | 動的な構造に対応困難 | テンプレートの動的性質 |

### 8.3 想定されるリスクと対策

| リスク | 影響 | 対策 |
|--------|------|------|
| 過度に厳格な検証 | 正当なテンプレートの拒否 | 警告レベルの導入、段階的な検証強化 |
| パフォーマンス劣化 | ジョブ生成時間の増加 | キャッシング、最適化、非同期化 |
| 新エンジンへの対応 | 拡張性の問題 | Strategy Patternによる疎結合設計 |

## 9. 実装計画

### 9.1 実装順序

1. **Phase 1**: 基本的なバリデータの実装
   - BodyTemplateValidatorクラスの作成
   - テンプレート変数抽出機能
   - 基本的なエラー型定義

2. **Phase 2**: 検証ロジックの実装
   - job.body参照の検証
   - tasks[N]参照の検証
   - スキーマ照合機能

3. **Phase 3**: 統合とテスト
   - MasterManagerSubWorkflowへの統合
   - 単体テストの作成（90%カバレッジ）
   - 結合テストの作成

4. **Phase 4**: 拡張機能
   - 必須フィールド情報の保存
   - JobQueue APIへの情報追加
   - ドキュメント更新

### 9.2 ファイル構成

```
expertAgent/aiagent/langgraph/jobGeneratorV2/
├── validators/
│   ├── body_template_validator.py      # 新規: メインバリデータ
│   ├── template_variable_extractor.py  # 新規: 変数抽出
│   └── schema_comparator.py           # 新規: スキーマ比較
├── workflows/registration/
│   └── master_manager.py               # 修正: バリデータ統合
└── tests/
    ├── unit/validators/
    │   └── test_body_template_validator.py
    └── integration/
        └── test_registration_validation.py
```

## 10. まとめ

本設計により、Job Generator V2のbody_template整合性検証機能を追加し、以下の効果が期待できます：

- **エラー発見の早期化**: REGISTRATIONフェーズでの検証により、不整合なジョブ生成を防止
- **明確なエラーメッセージ**: 具体的な問題箇所と修正提案の提供
- **保守性の向上**: 既存アーキテクチャとの整合性を保ちつつ、拡張可能な設計
- **開発効率の向上**: 実行時エラーのデバッグ時間削減

本設計は、CLAUDE.mdに定義されたSOLID原則、KISS原則に従い、既存のJob Generator V2アーキテクチャと整合性を保ちながら、必要最小限の変更で最大の効果を実現します。
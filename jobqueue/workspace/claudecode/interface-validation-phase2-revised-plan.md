# Interface Validation Phase 2+ 修正版実装計画

## 📋 文書情報

- **作成日**: 2025-10-17
- **対象**: JobQueue Interface検証機能 Phase 2.2以降
- **前提**: Phase 2.1完了（Job内のTask連鎖の検証機能実装済み）

---

## 🎯 Phase 2.1 完了状況まとめ

### ✅ 実装済み機能

1. **JobInterfaceValidator サービス**
   - パス: `app/services/job_interface_validator.py`
   - 機能: 既存JobのTask連鎖に対してInterface互換性を検証
   - 対応: 考慮①（包含関係チェック）、考慮②（Masterless実行対応）

2. **検証APIエンドポイント**
   - エンドポイント: `POST /api/v1/jobs/{job_id}/validate-interfaces`
   - 機能: 指定したJob IDの全Task間のInterface互換性をチェック
   - レスポンス形式:
     ```json
     {
       "is_valid": true/false,
       "errors": ["エラーメッセージ1", "エラーメッセージ2"],
       "warnings": ["警告メッセージ1"],
       "task_interfaces": [
         {
           "task_order": 0,
           "task_master_name": "search_query",
           "input_interface": null,
           "output_interface": "SearchResultInterface"
         }
       ],
       "compatibility_checks": [
         {
           "task_a_order": 0,
           "task_a_name": "search_query",
           "task_b_order": 1,
           "task_b_name": "info_analyzer",
           "is_compatible": true,
           "missing_properties": []
         }
       ]
     }
     ```

3. **包含関係チェックロジック**
   - `InterfaceValidator.check_output_contains_input_properties()`
   - Task A の output_schema に Task B の input_schema が要求する全プロパティが含まれているか検証
   - 型の互換性もチェック（string, number, array, object等）

4. **統合テスト**
   - パス: `tests/integration/test_job_interface_validation.py`
   - 6テストケース実装、全て合格

---

## 📐 実際のシステムアーキテクチャ

### データモデル構造

```
Job (1:N) Task (N:1) TaskMaster (N:1) InterfaceMaster
├── id (j_XXXXX)
├── name
├── master_id (nullable) ← 考慮②: JobMaster無しで実行可能
├── status (QUEUED/RUNNING/SUCCEEDED/FAILED/CANCELED)
├── tags (JSON array) ← Phase 2.2で検証結果を保存
├── created_at
├── started_at
├── finished_at
└── tasks (relationship)
    ├── Task (order=0)
    │   ├── id (t_XXXXX)
    │   ├── job_id
    │   ├── master_id → TaskMaster
    │   │   ├── id (tm_XXXXX)
    │   │   ├── name
    │   │   ├── method, url, timeout_sec
    │   │   ├── input_interface_id → InterfaceMaster
    │   │   └── output_interface_id → InterfaceMaster
    │   ├── order
    │   └── status
    ├── Task (order=1)
    └── Task (order=2)
```

### 重要な制約

1. **JobMasterは存在するが、task_configsフィールドは存在しない**
   - JobMasterは単なるJobの雛形定義
   - Jobを作成する際に個別にTaskを追加する（`POST /api/v1/jobs` のtasksパラメータ）

2. **Job.metadataフィールドは存在しない**
   - 検証結果などのメタデータを保存する場合は `Job.tags` (JSON配列) を使用

3. **考慮②対応: master_id=NULLのJobも実行可能**
   - JobMaster無しで直接Jobを作成・実行できる
   - この場合もTasksは必須なので、Interface検証は実行可能

---

## 🚀 Phase 2.2: Job作成時のInterface検証（修正版）

### ユーザー要件

1. **検証タイミング**: Job作成時に自動検証（オプショナル）
2. **検証結果の保存**: `Job.tags` に追加
3. **検証失敗時の動作**:
   - ⚠️ 警告のみ（Job作成は継続）
   - 🚫 **ただし、検証失敗したJobのIDを指定してのジョブ実行は不可**

### 実装アプローチ

#### 1. Job作成APIの拡張

**ファイル**: `app/api/v1/jobs.py`

**変更箇所**: `create_job()` および `create_job_from_master()`

**追加パラメータ**:
```python
class JobCreate(BaseModel):
    # ... 既存フィールド ...
    validate_interfaces: bool = True  # デフォルトでInterface検証を実行
```

**実装フロー**:
```python
@router.post("/jobs", response_model=JobResponse, status_code=201)
async def create_job(
    job_data: JobCreate,
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    # ... 既存のJob・Task作成ロジック ...

    await db.commit()
    await db.refresh(job)

    # Interface検証実行（オプショナル）
    if job_data.validate_interfaces and job_data.tasks:
        validation_result = await JobInterfaceValidator.validate_job_interfaces(
            db, job.id
        )

        # 検証結果をJob.tagsに追加
        validation_tag = _format_validation_tag(validation_result)
        if job.tags is None:
            job.tags = []
        job.tags.append(validation_tag)

        # 検証失敗した場合でもJob作成は継続（警告のみ）
        if not validation_result.is_valid:
            logger.warning(
                f"Job {job.id} created with interface validation warnings: "
                f"{validation_result.errors}"
            )

        await db.commit()
        await db.refresh(job)

    return JobResponse(job_id=job.id, status=job.status)
```

#### 2. 検証結果タグのフォーマット

**ヘルパー関数**:
```python
def _format_validation_tag(validation_result: JobInterfaceValidationResult) -> dict:
    """Format validation result as a tag for Job.tags field."""
    return {
        "type": "interface_validation",
        "validated_at": datetime.now(UTC).isoformat(),
        "is_valid": validation_result.is_valid,
        "error_count": len(validation_result.errors),
        "warning_count": len(validation_result.warnings),
        "errors": validation_result.errors[:5],  # 最初の5件のみ保存
        "warnings": validation_result.warnings[:5],
    }
```

**Job.tagsの例**:
```json
[
  {
    "type": "interface_validation",
    "validated_at": "2025-10-17T10:30:00Z",
    "is_valid": false,
    "error_count": 2,
    "warning_count": 0,
    "errors": [
      "Incompatible interfaces: Task 0 (search_query) → Task 1 (info_analyzer)",
      "  - Missing property: search_results (type: array)"
    ],
    "warnings": []
  }
]
```

#### 3. Job実行時の検証チェック

**ファイル**: `app/core/worker.py` (推測)

**追加ロジック**: Jobの実行を開始する前に `Job.tags` をチェック

```python
async def execute_job(job_id: str):
    """Execute a job and its tasks."""
    job = await db.get(Job, job_id)

    # Interface検証失敗チェック
    if job.tags:
        validation_tag = next(
            (tag for tag in job.tags if tag.get("type") == "interface_validation"),
            None
        )
        if validation_tag and not validation_tag.get("is_valid"):
            # 検証失敗したJobの実行は拒否
            job.status = JobStatus.FAILED
            await db.commit()
            raise ValueError(
                f"Job {job_id} cannot be executed: Interface validation failed. "
                f"Errors: {validation_tag.get('errors', [])}"
            )

    # ... 既存の実行ロジック ...
```

**考慮事項**:
- `validate_interfaces=False` で作成したJobは検証タグが無いため、実行時のチェックはスキップされる
- 既存のJob（Phase 2.2以前に作成）もタグが無いため影響なし

---

## 🧪 Phase 2.2: テスト計画

### 統合テストケース

**ファイル**: `tests/integration/test_job_creation_validation.py`

1. **test_create_job_with_validation_enabled**
   - `validate_interfaces=True` でJobを作成
   - 互換性のあるTaskを含む
   - Job作成成功、`Job.tags`に`is_valid=true`のタグが追加されることを確認

2. **test_create_job_with_validation_warnings**
   - `validate_interfaces=True` でJobを作成
   - 互換性の無いTaskを含む
   - Job作成は成功するが、`Job.tags`に`is_valid=false`のタグが追加されることを確認

3. **test_create_job_with_validation_disabled**
   - `validate_interfaces=False` でJobを作成
   - `Job.tags`に検証タグが追加されないことを確認

4. **test_execute_job_with_failed_validation**
   - 検証失敗したJobの実行を試みる
   - 実行が拒否され、エラーメッセージが返されることを確認

5. **test_execute_job_without_validation_tag**
   - 検証タグの無いJob（既存Job相当）の実行
   - 正常に実行されることを確認

---

## 🔄 Phase 2.3: Worker I/O検証（修正版）

### 目的

Task実行時に、実際の入出力データがInterface定義に準拠しているか検証

### 実装アプローチ

#### 1. Task入力データの検証

**ファイル**: `app/core/worker.py` (推測)

**検証タイミング**: Task実行直前

```python
async def execute_task(task: Task, input_data: dict):
    """Execute a single task with input validation."""
    task_master = await db.get(TaskMaster, task.master_id)

    # 入力Interface検証
    if task_master.input_interface_id:
        input_interface = await db.get(InterfaceMaster, task_master.input_interface_id)
        if input_interface and input_interface.input_schema:
            try:
                InterfaceValidator.validate_input(
                    input_data,
                    input_interface.input_schema
                )
            except InterfaceValidationError as e:
                # 検証失敗 → Task失敗
                task.status = TaskStatus.FAILED
                task.error_message = f"Input validation failed: {'; '.join(e.errors)}"
                await db.commit()
                raise

    # ... 既存のHTTPリクエスト実行ロジック ...
    response = await execute_http_request(task_master, input_data)

    # 出力Interface検証
    if task_master.output_interface_id:
        output_interface = await db.get(InterfaceMaster, task_master.output_interface_id)
        if output_interface and output_interface.output_schema:
            try:
                InterfaceValidator.validate_output(
                    response,
                    output_interface.output_schema
                )
            except InterfaceValidationError as e:
                # 検証失敗 → Task失敗
                task.status = TaskStatus.FAILED
                task.error_message = f"Output validation failed: {'; '.join(e.errors)}"
                await db.commit()
                raise

    return response
```

#### 2. Task結果の保存

**ファイル**: `app/models/task.py`

**追加フィールド候補**:
```python
class Task(Base):
    # ... 既存フィールド ...
    input_validation_result: Optional[str] = None  # JSON string
    output_validation_result: Optional[str] = None  # JSON string
```

**考慮事項**:
- 既存のDBスキーマ変更が必要（ALTER TABLE）
- または `Task.tags` (JSON) を追加してメタデータ保存用にする

---

## 📊 Phase 3: テストインフラ拡充（修正版）

### 目的

Interface検証機能の包括的なテストケース追加

### 実装内容

#### 1. モックデータジェネレータ

**ファイル**: `tests/utils/interface_mock.py`

```python
"""Mock data generator for interface testing."""
from typing import Any
import json

class InterfaceMockGenerator:
    """Generate mock data conforming to JSON Schema."""

    @staticmethod
    def generate_mock_data(schema: dict) -> dict:
        """Generate mock data that validates against the given schema."""
        if schema.get("type") == "object":
            return InterfaceMockGenerator._generate_object(schema)
        elif schema.get("type") == "array":
            return InterfaceMockGenerator._generate_array(schema)
        else:
            return InterfaceMockGenerator._generate_primitive(schema)

    @staticmethod
    def _generate_object(schema: dict) -> dict:
        """Generate mock object with required and optional properties."""
        result = {}
        properties = schema.get("properties", {})
        required = schema.get("required", [])

        for prop_name in required:
            prop_schema = properties.get(prop_name, {})
            result[prop_name] = InterfaceMockGenerator.generate_mock_data(prop_schema)

        return result

    @staticmethod
    def _generate_array(schema: dict) -> list:
        """Generate mock array."""
        items_schema = schema.get("items", {})
        return [InterfaceMockGenerator.generate_mock_data(items_schema)]

    @staticmethod
    def _generate_primitive(schema: dict) -> Any:
        """Generate mock primitive value."""
        schema_type = schema.get("type", "string")

        if schema_type == "string":
            return "mock_string"
        elif schema_type == "number":
            return 123.45
        elif schema_type == "integer":
            return 42
        elif schema_type == "boolean":
            return True
        elif schema_type == "null":
            return None
        else:
            return "unknown_type"
```

#### 2. エンドツーエンドテスト

**ファイル**: `tests/integration/test_interface_e2e.py`

```python
"""End-to-end tests for interface validation."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

class TestInterfaceE2E:
    """E2E test suite for interface validation."""

    @pytest.mark.asyncio
    async def test_job_creation_to_execution_with_validation(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test complete flow: Job creation → validation → execution."""
        # 1. Create compatible TaskMasters with Interfaces
        # 2. Create Job with validate_interfaces=True
        # 3. Verify validation tag in Job.tags
        # 4. Execute Job (should succeed)
        # 5. Verify all Tasks succeeded
        pass

    @pytest.mark.asyncio
    async def test_job_with_incompatible_interfaces_blocked(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test that Jobs with incompatible interfaces cannot be executed."""
        # 1. Create incompatible TaskMasters
        # 2. Create Job with validate_interfaces=True
        # 3. Verify validation tag shows is_valid=false
        # 4. Attempt to execute Job (should fail with error)
        pass
```

---

## 🎯 Phase 2.2 実装の優先度と順序

### 優先度: High

1. ✅ **Job作成時の検証ロジック追加**
   - `app/api/v1/jobs.py` の `create_job()` および `create_job_from_master()` の拡張
   - `validate_interfaces` パラメータの追加
   - 検証結果を `Job.tags` に保存

2. ✅ **Job実行時の検証チェック**
   - `app/core/worker.py` に検証失敗チェックロジック追加
   - 検証失敗Jobの実行を拒否

3. ✅ **統合テスト**
   - `tests/integration/test_job_creation_validation.py` の作成
   - 5つのテストケース実装

### 優先度: Medium

4. ⏳ **Pydanticスキーマの更新**
   - `app/schemas/job.py` に `validate_interfaces` フィールド追加
   - ドキュメント更新

5. ⏳ **エラーメッセージの改善**
   - 検証失敗時のユーザーフレンドリーなメッセージ
   - 修正方法の提案を含める

---

## 📝 実装時の注意事項

### 1. 後方互換性の維持

- **既存Job**（Phase 2.2以前に作成）は `tags` に検証タグが無い
- Workerは検証タグの有無を確認し、無い場合はスキップ
- `validate_interfaces` のデフォルト値は `True` だが、既存APIクライアントは影響を受けない

### 2. パフォーマンス考慮

- Job作成時の検証はオプショナル（`validate_interfaces=False` で無効化可能）
- 大量のTask（10件以上）を含むJobは検証に時間がかかる可能性
- 非同期処理なので他のリクエストへの影響は最小限

### 3. データベースマイグレーション

- Phase 2.2では新規フィールド追加は不要（`Job.tags` を使用）
- Phase 2.3で `Task.input_validation_result`, `Task.output_validation_result` を追加する場合はALTER TABLE必要

### 4. ログとモニタリング

- 検証失敗時は必ずログ出力（`logger.warning` レベル）
- Job実行拒否時は `logger.error` レベルでログ出力
- メトリクス収集: 検証失敗率、実行拒否回数

---

## 🚀 次のアクション

### 即座に開始可能なタスク

1. **Phase 2.2 実装**: Job作成時の検証ロジック追加
   - ファイル: `app/api/v1/jobs.py`, `app/schemas/job.py`
   - 所要時間: 2-3時間

2. **Worker側の実行チェック追加**
   - ファイル: `app/core/worker.py`
   - 所要時間: 1-2時間

3. **統合テスト作成**
   - ファイル: `tests/integration/test_job_creation_validation.py`
   - 所要時間: 2-3時間

### 承認が必要な設計判断

1. **検証タグのフォーマット**: 上記の提案で良いか？
2. **Job実行拒否のエラーハンドリング**: Exceptionを投げるか、Job.statusをFAILEDにするか？
3. **Phase 2.3のスコープ**: Worker I/O検証を含めるか、後回しにするか？

---

## 📚 参考資料

- **Phase 2.1 実装**: `app/services/job_interface_validator.py`
- **既存のJob作成API**: `app/api/v1/jobs.py` (Lines 40-131, 274-391)
- **Job・Taskモデル**: `app/models/job.py`, `app/models/task.py`
- **InterfaceValidator**: `app/services/interface_validator.py`

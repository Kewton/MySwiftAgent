# Issue #310 設計方針書

## 概要

| 項目 | 内容 |
|------|------|
| Issue | #310: [Bug] Job生成でtask_breakdown/interface_definitionsがDBに保存されない |
| 種別 | バグ修正 |
| 優先度 | P1（機能不全） |
| 影響範囲 | expertAgent, myAgentDesk |
| 作成日 | 2025-12-25 |
| 最終更新 | 2025-12-25（アーキテクチャレビュー反映） |

---

## 1. 問題の概要

Job Generator機能で生成された `task_breakdown` と `interface_definitions` がDBに保存されず、UIに表示されない問題。

### 現象
- Phase 1（Task Breakdown）で生成されたデータがUIに表示されない
- Phase 2（Workflow Generation）完了後もデータが空のまま
- `job_version.taskBreakdown` と `job_version.interfaceDefinitions` がnull

---

## 2. 根本原因分析

### データフロー図（現状）

```
[LangGraph Agent]
    ↓ task_breakdown生成
    ↓ interface_definitions生成
[AgentState] ←── 両方正しくデータ存在

[_build_response_from_state()]
    ↓ task_breakdown ← state.get("task_breakdown") ✅ 正しく抽出
    ↓ interface_definitions ← ❌ 抽出していない（フィールドなし）

[JobGeneratorResponse]
    ↓ task_breakdown ✅ 含まれる（list[dict[str, Any]] | None型）
    ↓ interface_definitions ❌ フィールドが存在しない

[job_state_manager.mark_completed_async()]
    ↓ result = response.model_dump() で保存

[HTTP GET /jobs/{job_id}/status]
    ↓ result.task_breakdown ✅ 取得可能
    ↓ result.interface_definitions ❌ 存在しない

[myAgentDesk /api/jobs/[id]/status]
    ↓ taskBreakdownFromApi = apiResult.value.task_breakdown ✅ 取得
    ↓ ❌ updateGenerationResult()でtaskBreakdownを保存していない
    ↓ ❌ updateGenerationResult()でinterfaceDefinitionsを保存していない

[DB job_version table]
    ↓ taskBreakdown = null ❌
    ↓ interfaceDefinitions = null ❌
```

### 問題箇所（3箇所）

#### 問題1: JobGeneratorResponse スキーマに interface_definitions フィールドがない

**ファイル**: `expertAgent/app/schemas/job_generator.py:45-127`

**現状のコード**:
```python
class JobGeneratorResponse(BaseModel):
    status: str
    job_id: str | None = None
    job_master_id: str | None = None
    task_breakdown: list[dict[str, Any]] | None = None  # ✅ 存在する
    evaluation_result: dict[str, Any] | None = None
    infeasible_tasks: list[dict[str, Any]] = []
    alternative_proposals: list[dict[str, Any]] = []
    api_extension_proposals: list[dict[str, Any]] = []
    requirement_relaxation_suggestions: list[dict[str, Any]] = []
    validation_errors: list[str] = []
    error_message: str | None = None
    langfuse_trace_id: str | None = None
    # ❌ interface_definitions フィールドがない
```

#### 問題2: _build_response_from_state() が interface_definitions を抽出しない

**ファイル**: `expertAgent/app/api/v1/job_generator_endpoints.py:297-446`

**現状のコード**（抜粋）:
```python
def _build_response_from_state(
    state: dict[str, Any],
    langfuse_trace_id: str | None = None,
) -> JobGeneratorResponse:
    # ...
    task_breakdown = state.get("task_breakdown")  # ✅ 抽出している
    # ...
    return JobGeneratorResponse(
        status=status,
        job_id=job_id,
        job_master_id=job_master_id,
        task_breakdown=task_breakdown,  # ✅ 含めている
        evaluation_result=evaluation_result,
        # ...
        # ❌ interface_definitions を抽出・含めていない
    )
```

> **注**: `task_breakdown`は正しく抽出されています。問題は`interface_definitions`のみです。

#### 問題3: myAgentDesk status API が taskBreakdown/interfaceDefinitions を DB に保存しない

**ファイル**: `myAgentDesk/src/routes/api/jobs/[jobId]/status/+server.ts:81-93`

**現状のコード**:
```typescript
// Job完了時の処理
if (resultStatus !== 'failed' && resultStatus !== 'error') {
    const updated = await jobVersionRepository.updateGenerationResult(jobId, {
        status: 'success',
        externalJobMasterId: result?.job_master_id ?? apiResult.value.job_master_id ?? undefined,
        externalTraceId: langfuseTraceId ?? undefined,
        workflows: workflowStatuses ? JSON.stringify(workflowStatuses) : undefined
        // ❌ taskBreakdown を保存していない
        // ❌ interfaceDefinitions を保存していない
    });
}
```

> **注**: `taskBreakdownFromApi`（line 59）でAPIから取得しているが、DBに保存していません。

---

## 3. 修正方針

### 方針A: データフロー全体の修正（推奨）

全ての問題箇所を修正し、エンドツーエンドでデータが正しく流れるようにする。

#### 修正1: JobGeneratorResponse に interface_definitions を追加

```python
class JobGeneratorResponse(BaseModel):
    status: str
    job_id: str | None = None
    job_master_id: str | None = None
    task_breakdown: list[dict[str, Any]] | None = None
    interface_definitions: dict[str, Any] | None = None  # 追加
    evaluation_result: dict[str, Any] | None = None
    # ... 既存フィールド
```

#### 修正2: _build_response_from_state() で interface_definitions を抽出

```python
def _build_response_from_state(
    state: dict[str, Any],
    langfuse_trace_id: str | None = None,
) -> JobGeneratorResponse:
    # ...
    task_breakdown = state.get("task_breakdown")
    interface_definitions = state.get("interface_definitions")  # 追加
    # ...
    return JobGeneratorResponse(
        status=status,
        job_id=job_id,
        job_master_id=job_master_id,
        task_breakdown=task_breakdown,
        interface_definitions=interface_definitions,  # 追加
        evaluation_result=evaluation_result,
        # ...
    )
```

#### 修正3: myAgentDesk status API でDBに保存

```typescript
// Job完了時の処理
if (resultStatus !== 'failed' && resultStatus !== 'error') {
    const updated = await jobVersionRepository.updateGenerationResult(jobId, {
        status: 'success',
        externalJobMasterId: result?.job_master_id ?? apiResult.value.job_master_id ?? undefined,
        externalTraceId: langfuseTraceId ?? undefined,
        // 追加: task_breakdown と interface_definitions を保存
        taskBreakdown: apiResult.value.task_breakdown
            ? JSON.stringify(apiResult.value.task_breakdown) : undefined,
        interfaceDefinitions: apiResult.value.interface_definitions
            ? JSON.stringify(apiResult.value.interface_definitions) : undefined,
        workflows: workflowStatuses ? JSON.stringify(workflowStatuses) : undefined
    });
}
```

> **注**: 失敗時（lines 71-77）も同様に保存処理を追加する必要があります。

### 方針B: myAgentDesk側のみ修正（非推奨）

DBへの保存のみ修正する方法。ただし、expertAgent側の`interface_definitions`がAPIレスポンスに含まれないため、myAgentDesk側だけでは解決できません。

### 選択: 方針A

根本原因を全て解消するため、方針Aを採用。

---

## 4. 修正ファイル一覧

| # | ファイル | 修正内容 | 優先度 |
|---|----------|----------|--------|
| 1 | `expertAgent/app/schemas/job_generator.py` | `interface_definitions` フィールド追加 | P1 |
| 2 | `expertAgent/app/api/v1/job_generator_endpoints.py` | `_build_response_from_state()` で `interface_definitions` 抽出 | P1 |
| 3 | `myAgentDesk/src/routes/api/jobs/[jobId]/status/+server.ts` | `taskBreakdown`/`interfaceDefinitions` のDB保存処理追加 | P1 |
| 4 | `myAgentDesk/src/lib/api/clients/expert-agent.ts` | 型定義に `interface_definitions` 追加（必要に応じて） | P2 |

---

## 5. テスト計画

### 単体テスト

#### expertAgent

```python
# expertAgent/tests/unit/test_job_generator_endpoints.py

def test_build_response_from_state_includes_interface_definitions():
    """interface_definitionsが正しく抽出されることを確認"""
    state = {
        "task_breakdown": [{"task_id": "t1", "name": "Task 1"}],
        "interface_definitions": {
            "t1": {
                "interface_master_id": "im_001",
                "input_schema": {"type": "object"},
                "output_schema": {"type": "object"}
            }
        },
        "job_id": "job_123",
        "job_master_id": "jm_001",
    }
    response = _build_response_from_state(state)

    assert response.task_breakdown is not None
    assert response.interface_definitions is not None
    assert "t1" in response.interface_definitions


def test_job_generator_response_schema_has_interface_definitions():
    """JobGeneratorResponseにinterface_definitionsフィールドが存在することを確認"""
    response = JobGeneratorResponse(
        status="success",
        interface_definitions={"t1": {"interface_master_id": "im_001"}}
    )
    assert response.interface_definitions == {"t1": {"interface_master_id": "im_001"}}
```

#### myAgentDesk

```typescript
// myAgentDesk/src/routes/api/jobs/[jobId]/status/+server.test.ts

test('status API saves taskBreakdown to DB on success', async () => {
    // Setup: Create job version with generating status
    const jobVersion = await createTestJobVersion({ status: 'generating' });

    // Mock: ExpertAgent API returns success with task_breakdown
    mockExpertAgentApi.getJobStatus.mockResolvedValue({
        ok: true,
        value: {
            status: 'completed',
            task_breakdown: [{ task_id: 't1', name: 'Task 1' }],
            interface_definitions: { t1: { interface_master_id: 'im_001' } }
        }
    });

    // Action: Call status API
    const response = await GET({ params: { jobId: jobVersion.id } });

    // Assert: DB contains taskBreakdown and interfaceDefinitions
    const updated = await jobVersionRepository.findById(jobVersion.id);
    expect(updated.taskBreakdown).not.toBeNull();
    expect(updated.interfaceDefinitions).not.toBeNull();
});
```

### 結合テスト

1. Job Generator API を呼び出し、レスポンスに `interface_definitions` が含まれることを確認
2. ポーリング完了後、DBに `task_breakdown` と `interface_definitions` が保存されていることを確認

### 受入テスト（L3）

```bash
#!/bin/bash
# tests/acceptance/test_issue_310_acceptance.sh

# 1. Job生成を実行（expertAgentが起動している前提）
JOB_RESPONSE=$(curl -s -X POST http://localhost:8004/aiagent-api/v1/job-generator \
  -H "Content-Type: application/json" \
  -d '{"user_requirement": "テスト用のジョブ生成"}')

JOB_ID=$(echo $JOB_RESPONSE | jq -r '.job_id')

# 2. ポーリングして完了を待つ
for i in {1..30}; do
    STATUS=$(curl -s "http://localhost:8004/aiagent-api/v1/jobs/${JOB_ID}/status" | jq -r '.status')
    if [ "$STATUS" = "completed" ]; then
        break
    fi
    sleep 2
done

# 3. DBを確認
cd myAgentDesk
RESULT=$(sqlite3 data/local.db "SELECT taskBreakdown, interfaceDefinitions FROM job_version WHERE externalJobId = '${JOB_ID}';")

if [ -n "$RESULT" ] && [ "$RESULT" != "|" ]; then
    echo "✅ PASS: taskBreakdown/interfaceDefinitions がDBに保存されている"
else
    echo "❌ FAIL: データがnullのまま"
fi
```

---

## 6. リスク評価

| リスク | 影響度 | 対策 |
|--------|--------|------|
| API互換性破壊 | 低 | フィールド追加のみで後方互換性あり |
| マイグレーション不要 | なし | DBスキーマ変更なし（カラムは既存） |
| テスト不足 | 中 | 単体・結合テストを追加（上記テスト計画参照） |
| 型定義の不整合 | 中 | expertAgent/myAgentDesk間でAPI契約を明示化 |

---

## 7. 実装順序

1. **expertAgent側の修正**（先に完了）
   - `JobGeneratorResponse`にフィールド追加
   - `_build_response_from_state()`で抽出処理追加
   - 単体テスト追加

2. **myAgentDesk側の修正**
   - status APIで`updateGenerationResult()`にフィールド追加
   - 型定義更新（必要に応じて）

3. **結合テスト・受入テスト実行**

---

## 8. 承認

| 項目 | ステータス |
|------|-----------|
| 設計レビュー | :white_check_mark: 完了（2025-12-25） |
| 実装承認 | 承認待ち |

### アーキテクチャレビュー結果

- **評価**: :star::star::star::star: 4/5
- **判定**: 条件付き承認（Conditionally Approved）
- **詳細**: `dev-reports/feature/issue/310/architecture-review.md` 参照

---

## 参考資料

- Issue #305: Job Generator Workflow Generation & UI Enhancement
- `myAgentDesk/src/lib/server/db/schema.ts` - JobVersionスキーマ定義
- `expertAgent/docs/API_REFERENCE.md` - API仕様書
- `dev-reports/feature/issue/310/architecture-review.md` - アーキテクチャレビュー

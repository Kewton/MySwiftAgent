# Issue #393 設計方針書

## 概要

| 項目 | 内容 |
|------|------|
| Issue番号 | #393 |
| タイトル | Tech Debt: Issue #361 Phase 2 未完了 - workflow_gen ディレクトリの削除 |
| タイプ | 技術的負債解消（リファクタリング） |
| 優先度 | Low |
| 作成日 | 2026-01-22 |

---

## 1. 現状調査結果

### 1.1 Issue説明との差異

**Issue #393 の記載**:
> `workflow_registrar.py` の `update_task_master_body_template_taskflow` 関数のみが `orchestrator.py` から使用されている

**実際の状況**:
`workflow_gen` ディレクトリは複数の場所から参照されており、単純な削除は困難です。

### 1.2 workflow_gen ディレクトリ構造

```
expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/workflow_gen/
├── __init__.py
├── workflow.py              # WorkflowGenWorkflow クラス
├── workflow_registrar.py    # update_task_master_body_template_taskflow 関数
├── llm_generator.py
├── yaml_generator.py
├── yaml_validator.py
├── test_runner.py
├── engine_strategy.py
├── errors.py
├── schemas.py
├── taskflow_generator.py
├── agent_selector.py
├── adapter/
│   ├── __init__.py
│   └── taskflow_adapter.py
├── schemas/
│   ├── __init__.py
│   ├── graphai_schema.py
│   ├── taskflow_schema.py
│   └── variable_patterns.py
├── prompt_builder/
│   ├── __init__.py
│   ├── assembler.py
│   ├── constraints/
│   ├── few_shot/
│   ├── rules/
│   └── system/
└── validators/
    ├── __init__.py
    ├── agent_validator.py
    ├── reference_validator.py
    ├── structure_validator.py
    └── syntax_validator.py
```

### 1.3 外部依存関係

| ファイル | インポート内容 |
|---------|---------------|
| `adapter_old.py` | `WorkflowGenWorkflow` |
| `workflows/__init__.py` | `WorkflowGenWorkflow`, `TestRunnerSubWorkflow`, `YamlGeneratorSubWorkflow` |
| `retry/__init__.py` | `workflow_gen_retry` |

### 1.4 update_task_master_body_template_taskflow 参照箇所（網羅的調査）

**アーキテクチャレビュー指摘（Must Fix #2）に基づく網羅的調査結果:**

```bash
# 調査コマンド
grep -rn "update_task_master_body_template_taskflow" --include="*.py" expertAgent/
```

| ファイル | 行番号 | 内容 |
|---------|--------|------|
| `workflow_gen/workflow_registrar.py` | 219 | 関数定義 |
| `workflow_gen/workflow.py` | 44 | import 文 |
| `workflow_gen/workflow.py` | 487 | 関数呼び出し |
| `tests/unit/test_job_generator_v2/test_orchestrator_issue390.py` | 複数 | モック/テスト |
| `tests/integration/test_issue390_integration.py` | 複数 | 結合テスト |

**重要**: 設計書初版では `workflow_gen/workflow.py` が漏れていました。Phase 2 でこのファイルのインポートパスも更新が必要です。

### 1.5 JOBQUEUE_API_URL の import 元（Must Fix #3 対応）

**アーキテクチャレビュー指摘に基づく調査結果:**

現在の `workflow_registrar.py` での定義:
```python
from aiagent.langgraph.jobGeneratorV2.workflows.common import settings
JOBQUEUE_API_URL = settings.JOBQUEUE_API_URL or "http://localhost:8001"
```

移動先 `task_master_utils.py` でも同様に `settings` モジュールから取得する:
```python
from aiagent.langgraph.jobGeneratorV2.workflows.common import settings
JOBQUEUE_API_URL = settings.JOBQUEUE_API_URL or "http://localhost:8001"
```

### 1.6 エクスポートされているクラス（__all__）

```python
# workflows/__init__.py
__all__ = [
    # Phase D: Workflow Generation
    "WorkflowGenWorkflow",
    "YamlGeneratorSubWorkflow",
    "TestRunnerSubWorkflow",
]
```

---

## 2. 設計上の課題

### 2.1 Issue説明とのスコープ差異

| Issue記載 | 実際の状況 |
|----------|----------|
| `update_task_master_body_template_taskflow` のみ使用 | 多数のクラス・関数が使用中 |
| 簡単な移動で完了 | 大規模リファクタリングが必要 |
| 影響範囲：コード整理のみ | 影響範囲：Phase D 全体 |

### 2.2 mySwiftAgentCore 統合状況

Issue #361 で導入された新アーキテクチャ:

```
現在のフロー:
  orchestrator.py
    → RegistrationWorkflow (registration/)     ... mySwiftAgentCore 統合済み
    → WorkflowGenWorkflow (workflow_gen/)      ... 旧アーキテクチャ（GraphAI用）
```

**重要な発見**: `workflow_gen/` は GraphAI ワークフロー生成用であり、mySwiftAgentCore（TaskFlow）とは別系統です。

---

## 3. 設計方針

### 3.1 段階的アプローチ（推奨）

完全削除ではなく、段階的なリファクタリングを推奨します。

#### Phase 1: 関数移動（Issue #393 本来のスコープ）

**対象**: `update_task_master_body_template_taskflow` 関数

**移動先**: `workflows/registration/task_master_utils.py`（新規作成）

```python
# 移動先: registration/task_master_utils.py
async def update_task_master_body_template_taskflow(
    task_master_id: str,
    workflow_name: str,
) -> bool:
    """Update TaskMaster body_template for TaskFlow V2 workflow execution."""
    # 既存実装をそのまま移動
```

**理由**:
- TaskFlow V2 関連のため `registration/` が適切
- `master_manager.py` に追加すると肥大化するため別ファイル
- 関数の責務（TaskMaster更新）と一致

#### Phase 2: インポートパス更新（Must Fix #2 反映）

| ファイル | 変更前 | 変更後 |
|---------|--------|--------|
| `workflow_gen/workflow.py` (L44) | `from .workflow_registrar import update_task_master_body_template_taskflow` | `from ..registration.task_master_utils import update_task_master_body_template_taskflow` |
| `tests/unit/.../test_orchestrator_issue390.py` | `.workflow_gen.workflow_registrar` | `.registration.task_master_utils` |
| `tests/integration/test_issue390_integration.py` | `.workflow_gen.workflow_registrar` | `.registration.task_master_utils` |

**注意**: `workflow_gen/workflow.py` は当初の設計書で漏れていた重要な参照箇所です。

#### Phase 3: workflow_gen 整理（将来タスク）

Issue #393 のスコープ外。別 Issue として起票を推奨。

- `workflow_gen/` の役割を明確化（GraphAI専用）
- 不要なコードの特定と削除
- ディレクトリ名変更の検討（`graphai_workflow_gen/` など）

### 3.2 代替案: 完全削除（非推奨）

**リスク**:
- 大規模な変更による回帰リスク
- GraphAI ワークフロー生成機能への影響
- テスト修正工数の増大

**評価**: 現時点では非推奨。Issue #393 のスコープを Phase 1 に限定すべき。

---

## 4. 実装設計

### 4.1 新規ファイル: task_master_utils.py

```python
# expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/registration/task_master_utils.py
"""TaskMaster utility functions for Job Generator V2.

Issue #393: Moved from workflow_gen/workflow_registrar.py
"""

import logging
from typing import TYPE_CHECKING

from aiagent.langgraph.jobGeneratorV2.workflows.common import settings

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Environment variable (from settings module - Must Fix #3)
JOBQUEUE_API_URL = settings.JOBQUEUE_API_URL or "http://localhost:8001"


async def update_task_master_body_template_taskflow(
    task_master_id: str,
    workflow_name: str,
) -> bool:
    """Update TaskMaster body_template for TaskFlow V2 workflow execution.

    Issue #350: TaskFlow V2 uses different body_template structure.
    Issue #393: Moved from workflow_gen/workflow_registrar.py
    """
    # 実装は既存コードをそのまま移動
```

### 4.2 registration/__init__.py の更新

```python
# 追加するエクスポート
from aiagent.langgraph.jobGeneratorV2.workflows.registration.task_master_utils import (
    update_task_master_body_template_taskflow,
)

__all__ = [
    # 既存エクスポート
    "RegistrationWorkflow",
    "MasterManagerSubWorkflow",
    "JobRegistrarSubWorkflow",
    # 追加
    "update_task_master_body_template_taskflow",
]
```

### 4.3 後方互換性の確保

`workflow_gen/workflow_registrar.py` に re-export を残す（非推奨警告付き）:

```python
# workflow_gen/workflow_registrar.py
import warnings

# Re-export for backward compatibility (deprecated)
from aiagent.langgraph.jobGeneratorV2.workflows.registration.task_master_utils import (
    update_task_master_body_template_taskflow as _update_taskflow,
)


def update_task_master_body_template_taskflow(*args, **kwargs):
    """Deprecated: Use registration.task_master_utils instead."""
    warnings.warn(
        "update_task_master_body_template_taskflow is deprecated. "
        "Import from registration.task_master_utils instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return _update_taskflow(*args, **kwargs)
```

---

## 5. テスト戦略

### 5.1 影響を受けるテストファイル

| テストファイル | 影響 |
|--------------|------|
| `tests/unit/test_job_generator_v2/test_orchestrator_issue390.py` | インポートパス更新 |
| `tests/integration/test_issue390_integration.py` | インポートパス更新 |

### 5.2 テスト更新方針

1. 新しいインポートパスでテストを更新
2. 後方互換性の re-export が動作することを確認
3. 既存テストの回帰がないことを確認

---

## 6. リスク評価

| リスク | 確率 | 影響 | 対策 |
|-------|------|------|------|
| インポートパスの変更漏れ | 中 | 中 | grep で全ての参照箇所を確認 |
| テスト失敗 | 低 | 低 | CI で検出可能 |
| GraphAI 機能への影響 | 低 | 高 | workflow_gen 本体は変更しない |

---

## 7. 作業工数見積

| フェーズ | 作業内容 | 見積 |
|---------|---------|------|
| Phase 1 | 関数移動・新ファイル作成 | 30分 |
| Phase 2 | インポートパス更新 | 30分 |
| Phase 3 | テスト更新・実行 | 30分 |
| Phase 4 | 後方互換性対応 | 15分 |
| 合計 | | 1時間45分 |

---

## 8. Definition of Done

- [x] `update_task_master_body_template_taskflow` が `registration/task_master_utils.py` に移動
- [ ] 全てのインポートパスが更新されている
- [ ] 後方互換性の re-export が実装されている
- [ ] 全テストがパスする
- [ ] 静的解析エラーがない
- [ ] コードレビュー完了

---

## 9. 推奨事項

### 9.1 Issue #393 のスコープ修正（Must Fix #1 対応）

**アーキテクチャレビューで指摘された Issue 記載と実際のスコープの乖離に対応:**

Issue #393 の説明を以下のように修正することを推奨:

**現在のIssue記載**:
> `workflow_gen/` ディレクトリを削除

**実際の状況**:
- `workflow_gen/` は GraphAI ワークフロー生成用として広く使用中
- `WorkflowGenWorkflow` 等、複数のクラスが他モジュールから参照
- 単純削除は困難、段階的リファクタリングが必要

**修正後の推奨タイトル**:
> Tech Debt: update_task_master_body_template_taskflow 関数の移動

**修正後の推奨本文**:
> `workflow_gen/workflow_registrar.py` の `update_task_master_body_template_taskflow` 関数を
> `registration/` ディレクトリに移動し、依存関係を整理する。
>
> 注: `workflow_gen/` の完全削除は別 Issue で対応。

### 9.2 後続 Issue の起票

`workflow_gen/` ディレクトリの完全整理は別 Issue として起票:

- **Issue タイトル**: Tech Debt: workflow_gen ディレクトリの役割明確化と整理
- **内容**: GraphAI 専用コードとして整理、不要コードの削除

---

## 10. 参照ドキュメント

- Issue #361: mySwiftAgentCore 統合
- Issue #350: TaskFlow V2 body_template 形式
- Issue #390: E2E テストでの発見
- `expertAgent/docs/API_REFERENCE.md`
- `docs/arch/service-dependencies.md`

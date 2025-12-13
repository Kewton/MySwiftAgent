# Issue #277 追加要件: Workflow Tasksセクションでのインターフェース詳細表示

## 概要

| 項目 | 内容 |
|------|------|
| **Issue** | #277 - commonUIのJob Configurationでのtaskのインタフェース確認効率化 |
| **追加要件** | Workflow Tasksセクションでタスク選択時にインターフェース詳細を表示 |
| **報告日時** | 2025-12-14 |
| **ステータス** | 調査完了・対応方針策定済 |

---

## 現状分析

### 現在の実装状況

`commonUI/pages/7_🔧_Job_Configuration.py` の構成：

| セクション | 機能 | インターフェース表示 |
|-----------|------|---------------------|
| **📂 Select JobMaster** | JobMaster選択 | なし |
| **📋 Workflow Tasks** | ワークフロータスク一覧・管理 | 列としてInput/Output名のみ表示 |
| **➕ Add Task to Workflow** | 新規タスク追加 | **タスク選択時に詳細表示あり** |
| **🔍 Workflow Validation** | バリデーション結果 | なし |

### 現在の「📋 Workflow Tasks」セクション

```
┌─────────────────────────────────────────────────────────────────┐
│ 📋 Workflow Tasks                                                │
├─────────────────────────────────────────────────────────────────┤
│ [DataFrame: Order | Task Name | Input Interface | Output Interface | ... ] │
├─────────────────────────────────────────────────────────────────┤
│ Task Management                                                  │
│ [Move Up Selector] [Move Down Selector] [Remove Selector]       │
│ [⬆️ Move Up]       [⬇️ Move Down]       [🗑️ Remove]              │
└─────────────────────────────────────────────────────────────────┘
```

**問題点:**
- DataFrameにはインターフェース名（`get_interface_name()`の結果）のみ表示
- タスクを選択してもインターフェースのJSON Schema詳細は確認不可
- 「➕ Add Task」パネルでは詳細表示があるが、既存ワークフロータスクでは不可

### 「➕ Add Task」パネルの現在の動作（参考）

タスク選択時に `render_task_interface_info()` を呼び出し：
- Input/Output インターフェース名を表示
- JSON Schemaをエキスパンダーで展開表示可能
- プロパティ一覧（フィールド名、型、required/optional）を表示

---

## 要件定義

### ユーザーストーリー

> 「📋 Workflow Tasks」セクションでワークフロー内のタスクを選択した際、そのタスクの入出力インターフェース詳細（JSON Schema含む）を確認したい。

### 受入条件

1. **タスク選択UI追加**: Workflow Tasksセクションにタスク選択用のセレクトボックスを追加
2. **インターフェース詳細表示**: 選択したタスクの`render_task_interface_info()`を呼び出し、Input/Output Schema詳細を表示
3. **既存機能維持**: 既存のMove Up/Move Down/Remove機能は変更なし
4. **UX向上**: タスク管理操作と詳細閲覧を分離し、誤操作を防止

---

## 対応方針

### 方針A: タスク詳細表示専用セクション追加（推奨）

**概要**: Task Managementの上に「Task Details」セクションを追加

```
┌─────────────────────────────────────────────────────────────────┐
│ 📋 Workflow Tasks                                                │
├─────────────────────────────────────────────────────────────────┤
│ [DataFrame: Order | Task Name | Input Interface | Output Interface | ... ] │
├─────────────────────────────────────────────────────────────────┤
│ 🔍 Task Details                                 [NEW SECTION]   │
│ [Task Selector: Select task to view details...]                 │
│ ┌─────────────────────────────────────────────┐                 │
│ │ **Interface Information**                    │                 │
│ │ Input: [name]   Output: [name]              │                 │
│ │ [Input Schema Expander] [Output Schema Expander]              │
│ └─────────────────────────────────────────────┘                 │
├─────────────────────────────────────────────────────────────────┤
│ Task Management                                                  │
│ [Move Up] [Move Down] [Remove]                                  │
└─────────────────────────────────────────────────────────────────┘
```

**メリット:**
- 詳細閲覧と管理操作の明確な分離
- 既存コンポーネント（`render_task_interface_info()`）を再利用可能
- UXが直感的

**デメリット:**
- セクションが増え、画面が長くなる可能性

### 方針B: DataFrame行クリックで詳細表示

**概要**: DataFrameの行選択機能を使用し、選択行のタスク詳細を表示

**メリット:**
- 画面レイアウトの変更が少ない

**デメリット:**
- Streamlit DataFrameの選択機能に制限あり
- 実装がやや複雑

### 方針C: Task Management統合

**概要**: 既存のTask Managementセレクターを共通化し、選択したタスクの詳細を表示

**メリット:**
- UIの追加が最小限

**デメリット:**
- Move Up/Down/Removeの誤操作リスク
- セレクターの役割が不明確になる

---

## 推奨: 方針A

### 実装計画

#### 1. セッション状態の拡張

```python
# 追加する session_state
if "selected_workflow_task_id" not in st.session_state:
    st.session_state.selected_workflow_task_id = None
```

#### 2. `render_workflow_tasks()` 関数の修正

```python
def render_workflow_tasks() -> None:
    # ... 既存のDataFrame表示 ...

    # NEW: Task Details セクション
    st.divider()
    st.caption("🔍 Task Details")

    tasks = st.session_state.workflow_tasks
    task_options = {
        f"{t['order']}: {t['task_name']}": t for t in tasks
    }

    selected = st.selectbox(
        "Select task to view interface details",
        options=["Select a task...", *task_options.keys()],
        key="workflow_task_detail_selector",
    )

    if selected and selected != "Select a task...":
        task = task_options[selected]
        # TaskMasterの詳細を取得してrender_task_interface_infoを呼び出す
        task_master = get_task_master_detail(task["task_master_id"])
        if task_master:
            render_task_interface_info(task_master)

    # ... 既存のTask Management ...
```

#### 3. TaskMaster詳細取得関数の追加（必要に応じて）

```python
def get_task_master_detail(task_master_id: str) -> dict[str, Any] | None:
    """Get TaskMaster detail from cache or API."""
    # available_task_masters から取得、またはAPIコール
```

### タスク一覧

| タスクID | 説明 | 見積もり |
|----------|------|---------|
| 1.1 | session_state に `selected_workflow_task_id` 追加 | 小 |
| 1.2 | `render_workflow_tasks()` にTask Detailsセクション追加 | 中 |
| 1.3 | タスク選択時のインターフェース詳細表示ロジック実装 | 中 |
| 2.1 | 単体テスト追加 | 中 |
| 3.1 | 動作確認・UIテスト | 小 |

---

## 影響範囲

### 変更ファイル

| ファイル | 変更内容 |
|----------|---------|
| `commonUI/pages/7_🔧_Job_Configuration.py` | Task Detailsセクション追加 |
| `commonUI/tests/unit/test_job_configuration.py` | テストケース追加 |

### 既存機能への影響

- **影響なし**: 既存のMove Up/Move Down/Remove機能
- **影響なし**: Add Task to Workflowパネル
- **影響なし**: interface_service.pyの既存関数

---

## 備考

- 現在のIssue #277のPR #282 はdevelopブランチへのマージ待ち
- 本追加要件は新たなPRとして対応するか、PR #282に含めるか要検討
- `render_task_interface_info()` は既に `task_master` オブジェクトの `input_interface_id` / `output_interface_id` を使用するため、再利用可能

# Interface Validation Phase 1 - commonUI実装進捗

## 作業開始日時

2025-10-17

## タスク概要

commonUI の JobQueue画面に Interface Validation Phase 1 機能を統合

## 完了した作業

### Task 1: API仕様理解 ✅ (完了)

**実施内容**:
1. ✅ jobqueue API スキーマ確認
2. ✅ TaskMaster API 仕様理解
3. ✅ InterfaceMaster API 仕様理解
4. ✅ Job作成API 仕様理解
5. ✅ JobQueue画面の現状確認

**確認したAPI仕様**:

#### TaskMaster API (`GET /api/v1/task-masters`)
```python
# レスポンススキーマ: TaskMasterDetail
{
  "id": "tm_01ABC...",
  "name": "Task Name",
  "description": "Task description",
  "method": "POST",
  "url": "https://api.example.com",
  "headers": {...},
  "body_template": {...},
  "timeout_sec": 30,
  "input_interface_id": "if_01XYZ..." | null,   # 重要: 入力Interface ID
  "output_interface_id": "if_01XYZ..." | null,  # 重要: 出力Interface ID
  "current_version": 1,
  "is_active": true,
  "created_at": "2025-10-17T00:00:00Z",
  "updated_at": "2025-10-17T00:00:00Z",
  "created_by": "user",
  "updated_by": "user"
}

# クエリパラメータ
- is_active: bool | None (フィルタ)
- page: int (default: 1)
- size: int (default: 20, max: 100)
```

####Interface Master API (`GET /api/v1/interface-masters`)
```python
# レスポンススキーマ: InterfaceMasterDetail
{
  "id": "if_01XYZ...",
  "name": "Interface Name",
  "description": "Interface description",
  "input_schema": {                    # JSON Schema V7
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {...},
    "required": [...]
  } | null,
  "output_schema": {                   # JSON Schema V7
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {...},
    "required": [...]
  } | null,
  "is_active": true,
  "created_at": "2025-10-17T00:00:00Z",
  "updated_at": "2025-10-17T00:00:00Z"
}

# クエリパラメータ
- is_active: bool | None
- page: int
- size: int
```

#### Job作成API (`POST /api/v1/jobs`)
```python
# リクエストスキーマ: JobCreate
{
  "name": "My Job",
  "method": "POST",
  "url": "https://api.example.com",
  "headers": {"Content-Type": "application/json"} | null,
  "params": {"key": "value"} | null,
  "body": {"data": "value"} | null,
  "timeout_sec": 30,
  "priority": 5,
  "max_attempts": 1,
  "backoff_strategy": "exponential",
  "backoff_seconds": 5.0,
  "scheduled_at": "2025-10-17T00:00:00Z" | null,
  "ttl_seconds": 604800,
  "tags": ["tag1", "tag2"] | null,
  "input_data": {...} | null,
  "tasks": [                           # 重要: タスク配列
    {
      "master_id": "tm_01ABC...",      # TaskMaster ID
      "sequence": 0,                   # 実行順序 (0-based)
      "input_data": {...} | null       # タスク個別の入力データ
    },
    {
      "master_id": "tm_01DEF...",
      "sequence": 1,
      "input_data": {...} | null
    }
  ] | null,
  "validate_interfaces": true          # Interface検証フラグ
}

# レスポンススキーマ: JobResponse
{
  "job_id": "j_01JKL...",
  "status": "queued"
}
```

**重要な発見**:
1. **自動Task作成**: `tasks` 配列を送信すると、API側でTaskが自動作成される
2. **Interface検証**: `validate_interfaces: true` で互換性検証が自動実行される
3. **検証結果の格納**: 検証結果は Job の `tags` フィールドに格納される
4. **非ブロッキング検証**: 検証に失敗してもJobは作成される（警告のみ）

**JobQueue画面の現状**:
- **ファイル**: `commonUI/pages/1_📋_JobQueue.py` (1082行)
- **構造**:
  - API Configuration セクション (Line 113-240) ← フォーム外
  - Job作成フォーム (Line 243-456) ← フォーム内
  - Job一覧 (Line 572-690)
  - Job詳細 (Line 729-977)

**統合方針**:
- **Task選択UIの配置**: フォーム外（Line 241の`st.divider()`の後）
- **理由**: リアルタイム互換性チェックを実現するため、session_state を活用
- **参考**: API Configuration セクションと同じパターンを採用

### Task 2: components/task_selector.py コンポーネント作成 ✅ (完了)

**実装したクラス**: `TaskSelector`

**実装内容**:
```python
class TaskSelector:
    """TaskMaster選択と順序変更UI コンポーネント"""

    @staticmethod
    def render_task_selector(
        available_tasks: list[dict[str, Any]],
        key_prefix: str = "task_selector",
    ) -> list[dict[str, Any]]:
        """
        Task選択UIをレンダリング

        Args:
            available_tasks: TaskMasterリスト (API GET /task-masters レスポンス)
            key_prefix: session state キープレフィックス

        Returns:
            選択済みTaskリスト: [{
                "master_id": "tm_01ABC...",
                "sequence": 0,
                "name": "Task Name",
                "input_interface_id": "if_01XYZ..." | None,
                "output_interface_id": "if_01XYZ..." | None,
            }]
        """
```

**実装した機能**:
1. ✅ TaskMasterのドロップダウン選択
2. ✅ 選択したTaskのリスト表示
3. ✅ 順序変更 (上へ/下へボタン)
4. ✅ Task削除ボタン
5. ✅ 各TaskのInterface情報表示（input/output Interface ID）
6. ✅ Clear All Tasksボタン
7. ✅ Session state管理（key_prefix対応）
8. ✅ 重複Task選択の防止

**設計上のポイント**:
- **Session state管理**: `{key_prefix}_selected_tasks` キーで状態を保持
- **リアルタイム更新**: ボタンクリック時に `st.rerun()` で即座にUI更新
- **拡張性**: `key_prefix` パラメータにより複数箇所での使用が可能

### Task 3: components/interface_compatibility_checker.py コンポーネント作成 ✅ (完了)

**実装したクラス**: `InterfaceCompatibilityChecker`

**実装内容**:
```python
class InterfaceCompatibilityChecker:
    """Interface互換性検証コンポーネント"""

    @staticmethod
    def check_compatibility(
        selected_tasks: list[dict[str, Any]],
        interfaces: dict[str, dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """
        連続するTask間のInterface互換性をチェック

        Returns:
            {
                "is_compatible": bool,
                "issues": [
                    {
                        "type": "error" | "warning",
                        "task_index": int,
                        "task_name": str,
                        "message": str,
                    }
                ],
                "summary": str
            }
        """
```

**実装した機能**:
1. ✅ 連続Task間のInterface互換性チェック
2. ✅ エラーと警告の分類
3. ✅ 詳細レポート表示 (`render_compatibility_result()`)
4. ✅ インライン表示（コンパクト版）(`render_inline_compatibility_check()`)
5. ✅ Interface名の表示（IDのみでなく名前も表示）
6. ✅ 推奨対策の表示

**検証ロジック**:
- **Case 1**: 両方のInterfaceが未定義 → 警告
- **Case 2**: 現在TaskのOutputが未定義 → 警告
- **Case 3**: 次TaskのInputが未定義 → 警告
- **Case 4**: Output Interface ID ≠ Input Interface ID → エラー

**設計上のポイント**:
- **非破壊的検証**: 検証に失敗してもJob作成は可能（警告のみ）
- **段階的な詳細度**: インライン表示と詳細表示の2モード
- **ユーザーフレンドリー**: エラーごとに具体的な推奨対策を表示

### Task 4: JobQueue画面統合 ✅ (完了)

**実装内容**:

#### 4.1 API データロード機能の追加

**ファイル**: `commonUI/pages/1_📋_JobQueue.py` (Lines 1067-1095)

```python
def load_task_masters() -> None:
    """TaskMasterをAPIから読み込み"""
    # GET /api/v1/task-masters?is_active=true
    # → st.session_state.jobqueue_task_masters に保存

def load_interface_masters() -> None:
    """InterfaceMasterをAPIから読み込み"""
    # GET /api/v1/interface-masters?is_active=true
    # → dict[interface_id, interface] 形式で保存（O(1)ルックアップ用）
```

**呼び出しタイミング**: `main()` 関数の最初で1回のみ実行（Lines 1098-1103）

#### 4.2 Task選択UI セクションの追加

**配置場所**: API Configuration セクションと Job作成フォームの間（Lines 249-267）

```python
# Task Selection Section (Interface Validation Phase 1)
st.subheader("📋 Task Selection (Optional)")

# TaskSelector コンポーネント
selected_tasks = TaskSelector.render_task_selector(
    available_tasks=st.session_state.jobqueue_task_masters,
    key_prefix="jobqueue",
)

# インライン互換性チェック（2タスク以上の場合）
if selected_tasks and len(selected_tasks) >= 2:
    InterfaceCompatibilityChecker.render_inline_compatibility_check(
        selected_tasks=selected_tasks,
        interfaces=st.session_state.jobqueue_interface_masters,
    )
```

**配置理由**: リアルタイム互換性チェックを実現するため、フォーム外に配置

#### 4.3 Job作成ロジックの拡張

**ファイル**: `commonUI/pages/1_📋_JobQueue.py` (Lines 478-493)

```python
# Add selected tasks if any (Interface Validation Phase 1)
selected_tasks = TaskSelector.get_selected_tasks("jobqueue")
if selected_tasks:
    # Transform selected tasks to tasks array format for API
    job_data["tasks"] = [
        {
            "master_id": task["master_id"],
            "sequence": task["sequence"],
        }
        for task in selected_tasks
    ]
    # Enable interface validation
    job_data["validate_interfaces"] = True
    st.info(f"📋 {len(selected_tasks)} task(s) will be executed in sequence")
```

**実装した機能**:
- ✅ 選択されたTaskの取得
- ✅ API形式への変換（必要なフィールドのみ送信）
- ✅ `validate_interfaces: true` フラグの自動付与
- ✅ ユーザーへのフィードバック表示

#### 4.4 Session State の初期化

**ファイル**: `commonUI/pages/1_📋_JobQueue.py` (Lines 35-38)

```python
if "jobqueue_task_masters" not in st.session_state:
    st.session_state.jobqueue_task_masters = []
if "jobqueue_interface_masters" not in st.session_state:
    st.session_state.jobqueue_interface_masters = {}
```

#### 4.5 コンポーネントのインポート追加

**ファイル**: `commonUI/pages/1_📋_JobQueue.py` (Lines 14-18)

```python
from components.interface_compatibility_checker import InterfaceCompatibilityChecker
from components.task_selector import TaskSelector
```

**統合結果**:
- ✅ Task選択UIの表示
- ✅ リアルタイム互換性チェック
- ✅ tasks配列を含むJob作成リクエスト送信
- ✅ 既存のJob作成フローとの共存（Task選択はオプション）
- ✅ パフォーマンス最適化（InterfaceMasterをdict化してO(1)ルックアップ）

---

## 次の作業

### Task 5: 単体テスト作成 (次回)

**対象コンポーネント**:
1. `components/task_selector.py`
2. `components/interface_compatibility_checker.py`

**テスト項目**:
- Task選択・削除・順序変更の動作確認
- Interface互換性チェックロジックの検証
- 各種エッジケース（空リスト、None、重複等）

### Task 6: 統合テスト作成 (次回)

**テストシナリオ**:
1. JobQueue画面でTask選択からJob作成までの一連のフロー
2. 互換性エラーがある場合の警告表示
3. tasks配列を含むJob作成APIリクエストの検証

---

**作成者**: Claude Code
**最終更新日時**: 2025-10-18

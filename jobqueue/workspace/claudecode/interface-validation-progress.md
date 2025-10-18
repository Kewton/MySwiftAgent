# Interface Validation 実装進捗レポート

## 📅 最終更新日: 2025-10-17

---

## ✅ 完了済みフェーズ

### Phase 1.3: TaskMaster Interface登録の一括化 (完了)

**実装内容**:
- `scripts/seed_missing_interfaces.py` を作成
- 2つのInterfaceMaster定義を追加:
  - `AnalysisResultInterface` (info_analyzer用)
  - `EmailContentInterface` (email_sender用)
- 3つのTaskMasterにInterfaceを関連付け:
  - info_analyzer → AnalysisResultInterface (input/output)
  - email_sender → EmailContentInterface (input/output)
  - report_generator → AnalysisResultInterface (input), ReportInterface (output)

**実行結果**:
```
✅ Created 2 new interface(s)
✅ Created 6 new association(s)
⚠️  WARNING: 2 TaskMaster(s) still missing interface associations:
    - search_query_generator
    - google_search
```

**DB変更**:
```sql
ALTER TABLE task_masters ADD COLUMN input_interface_id VARCHAR(32);
ALTER TABLE task_masters ADD COLUMN output_interface_id VARCHAR(32);
```

**発生したエラーと解決**:
1. ❌ `ImportError: cannot import name 'async_session_maker'` → ✅ `AsyncSessionLocal` に修正
2. ❌ `TypeError: 'created_by' is an invalid keyword` → ✅ InterfaceMasterから削除
3. ❌ `sqlite3.OperationalError: no such column` → ✅ ALTER TABLE実行

---

### Phase 2.1: Job内のTask連鎖検証 (完了)

**実装内容**:
1. **JobInterfaceValidator サービス** (`app/services/job_interface_validator.py`)
   - `validate_job_interfaces(db, job_id)` メソッド実装
   - 考慮①対応: 包含関係チェック（Task A output ⊇ Task B input）
   - 考慮②対応: Masterless実行（Job.master_id=NULL）でも検証可能

2. **検証APIエンドポイント** (`app/api/v1/jobs.py`)
   - `POST /api/v1/jobs/{job_id}/validate-interfaces` 追加
   - レスポンス形式: `is_valid`, `errors`, `warnings`, `task_interfaces`, `compatibility_checks`

3. **統合テスト** (`tests/integration/test_job_interface_validation.py`)
   - 6テストケース作成: 互換性あり、互換性なし、Interface未定義、単一Task、Job未存在、型不一致
   - 全テスト合格: `====== 6 passed in 0.24s ======`

**アーキテクチャ理解の修正**:
- 当初の計画: JobMasterに `task_configs` フィールドがあると想定
- 実際のDB: Job (1:N) Task (N:1) TaskMaster の関係
- 対応: 既存JobのTask連鎖を検証する方針に変更

**検証ロジック詳細**:
```python
# 包含関係チェック（考慮①）
is_compatible, missing_props = (
    InterfaceValidator.check_output_contains_input_properties(
        output_schema, input_schema
    )
)

# Task A の output_schema に Task B の input_schema の全required propertiesが含まれているか検証
# 型の互換性もチェック（string, number, array, object等）
```

---

### Phase 2.2: Job作成時のInterface検証 (完了)

**ユーザー要件**:
1. **検証タイミング**: Job作成時に自動検証（オプショナル: `validate_interfaces=True`）
2. **検証結果の保存**: `Job.tags` (JSON配列) に追加
3. **検証失敗時の動作**:
   - ⚠️ 警告のみ（Job作成は継続）
   - 🚫 ただし、検証失敗したJobのIDを指定してのジョブ実行は不可

**実装内容**:
1. ✅ 修正版実装計画を作成 (`workspace/claudecode/interface-validation-phase2-revised-plan.md`)
2. ✅ Job作成API拡張 (`app/api/v1/jobs.py`)
   - `JobCreate` / `JobCreateFromMaster` スキーマに `validate_interfaces: bool = True` 追加
   - `create_job()` / `create_job_from_master()` に検証ロジック追加 (lines 131-164, 426-459)
   - 検証結果を `Job.tags` に保存（最初の5エラー/警告のみ）
   - 検証失敗時にWARNINGログ出力
3. ✅ Job実行時の検証チェック (`app/core/worker.py`)
   - Job実行開始時に `Job.tags` の `interface_validation` タグをチェック (lines 56-75)
   - `is_valid=false` の場合は `ValueError` を投げて実行を拒否
   - Job.status = FAILED に設定
4. ✅ 統合テスト作成 (`tests/integration/test_job_creation_validation.py`)
   - 6テストケース全て合格: `====== 6 passed in 31.68s ======`
   - テスト内容:
     * `test_create_job_with_validation_enabled` - 互換性あり、検証成功
     * `test_create_job_with_validation_warnings` - 互換性なし、警告付きJob作成
     * `test_create_job_with_validation_disabled` - 検証無効、タグなし
     * `test_execute_job_with_failed_validation` - 検証失敗Jobの実行ブロック
     * `test_execute_job_without_validation_tag` - 検証タグ無しJob（後方互換性）
     * `test_execute_job_with_passed_validation` - 検証成功Jobの正常実行

**技術的決定**:
- デフォルトで検証有効（`validate_interfaces=True`）
- 検証失敗でもJob作成は継続（警告モード）
- Worker実行時に検証結果をチェックしてブロック
- エラー/警告は最初の5件のみ保存（タグサイズ制限）

---

### Phase 2.3: Worker I/O検証 (完了 - 既存実装を確認)

**発見**: Phase 2.3の機能は既に `app/core/worker.py` に実装済みでした。

**既存実装内容**:
1. ✅ **Task入力データの検証** (`app/core/worker.py` lines 130-147)
   - `task.input_data` を `InterfaceValidator.validate_input()` で検証
   - 検証失敗時は Exception を投げてタスク失敗
   - TaskMasterInterface経由でInterface定義を取得

2. ✅ **Task出力データの検証** (`app/core/worker.py` lines 171-187)
   - HTTPレスポンスの `output_data` を `InterfaceValidator.validate_output()` で検証
   - 検証失敗時は Exception を投げてタスク失敗
   - TaskMasterInterface経由でInterface定義を取得

**検証ロジック**:
```python
# Input validation (lines 130-147)
if task.input_data:
    interfaces = await self.session.scalars(
        select(TaskMasterInterface)
        .where(TaskMasterInterface.task_master_id == task_master.id)
        .options(selectinload(TaskMasterInterface.interface_master))
    )
    for assoc in interfaces.all():
        if assoc.required and assoc.interface_master.input_schema:
            try:
                InterfaceValidator.validate_input(
                    task.input_data,
                    assoc.interface_master.input_schema,
                )
            except InterfaceValidationError as e:
                raise Exception(
                    f"Input validation failed: {'; '.join(e.errors)}"
                ) from e

# Output validation (lines 171-187)
if output_data:
    interfaces = await self.session.scalars(
        select(TaskMasterInterface)
        .where(TaskMasterInterface.task_master_id == task_master.id)
        .options(selectinload(TaskMasterInterface.interface_master))
    )
    for assoc in interfaces.all():
        if assoc.required and assoc.interface_master.output_schema:
            try:
                InterfaceValidator.validate_output(
                    output_data,
                    assoc.interface_master.output_schema,
                )
            except InterfaceValidationError as e:
                raise Exception(
                    f"Output validation failed: {'; '.join(e.errors)}"
                ) from e
```

**結論**: Worker I/O検証は既に完全に実装されており、Phase 2.3として新規実装の必要なし。

---

### Phase 3: テストインフラ拡充 (完了)

**実装内容**:
1. ✅ **モックデータジェネレータ** (`tests/utils/interface_mock.py` - 202行)
   - JSON Schema準拠のテストデータ自動生成
   - `InterfaceMockGenerator.generate_mock_data(schema)` メソッド実装
   - 型サポート: object, array, string, number, integer, boolean
   - フォーマットサポート: date-time, email, uri, uuid
   - `InterfaceMockBuilder` fluent APIで柔軟なカスタマイズ可能

2. ✅ **E2Eテスト** (`tests/integration/test_interface_e2e.py` - 320行)
   - 4つのE2Eテストケース全て合格 (35.25秒)
   - テスト内容:
     * `test_e2e_compatible_interfaces_full_flow` - 互換性ありの完全フロー（作成→検証→実行）
     * `test_e2e_incompatible_interfaces_blocked_execution` - 互換性なしのジョブ実行ブロック
     * `test_e2e_mock_data_generation` - モックデータ生成機能テスト
     * `test_e2e_validation_disabled_flow` - 検証無効時の完全フロー

**テスト結果**:
```
============================== 16 passed in 37.25s ==============================
- test_job_interface_validation.py: 6 passed
- test_job_creation_validation.py: 6 passed
- test_interface_e2e.py: 4 passed
```

**技術的ハイライト**:
- モックデータジェネレータは再帰的にネストされたschemaに対応
- E2EテストはHTTPBinを使用して実際のHTTPリクエストをテスト
- テストカバレッジ: 55% (変更なし、既存カバレッジ維持)

---

## 🚧 現在進行中のフェーズ

**(なし - Phase 1.3 ~ Phase 3まで全て完了)**

---

## ✅ 完了済みフェーズ（続き）

**検証結果タグの形式**:
```json
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
```

---

## 📋 未着手のフェーズ

### Phase 2.3: Worker I/O検証 (計画修正完了、実装未着手)

**目的**: Task実行時に実際の入出力データがInterface定義に準拠しているか検証

**実装方針**:
1. Task入力データの検証（実行直前）
2. Task出力データの検証（HTTPレスポンス受信後）
3. 検証失敗時はTask失敗として扱う
4. 検証結果を `Task.tags` に保存（要DB変更）

**保留中の設計判断**:
- `Task.input_validation_result`, `Task.output_validation_result` フィールドを追加するか？
- または `Task.tags` (JSON) を追加して汎用化するか？

---

### Phase 3: テストインフラ拡充 (計画修正完了、実装未着手)

**目的**: Interface検証機能の包括的なテストケース追加

**実装内容**:
1. **モックデータジェネレータ** (`tests/utils/interface_mock.py`)
   - JSON Schemaに準拠したテストデータ自動生成
   - `InterfaceMockGenerator.generate_mock_data(schema)` メソッド

2. **E2Eテスト** (`tests/integration/test_interface_e2e.py`)
   - Job作成 → 検証 → 実行 の完全フロー
   - 検証失敗Jobの実行ブロック検証

---

## 🛠️ 技術的な発見事項

### 1. システムアーキテクチャの実態

**当初の想定**:
- JobMasterに `task_configs` フィールドがある
- JobMasterに `metadata` フィールドがある
- JobMaster中心の設計

**実際のDB構造**:
```
Job (1:N) Task (N:1) TaskMaster (N:1) InterfaceMaster
├── Job.master_id (nullable) ← 考慮②: JobMaster無しでも実行可能
├── Job.tags (JSON array) ← メタデータ保存用
└── Task.order ← Task実行順序
```

**影響**:
- Phase 2.1の実装方針を変更（既存JobのTask連鎖を検証）
- Phase 2.2で検証結果を `Job.tags` に保存
- JobMaster検証は将来的な拡張として保留

---

### 2. Interface互換性チェックのロジック（考慮①）

**包含関係チェック（Containment-based Compatibility）**:
- Task B の input_schema が要求する **required プロパティ** が全て Task A の output_schema に含まれているか検証
- **exact match ではない**: Task A が追加のプロパティを出力しても問題なし
- **型の互換性もチェック**: string, number, array, object 等

**例**:
```python
# Task A output
{
  "type": "object",
  "properties": {
    "search_results": {"type": "array"},
    "query": {"type": "string"},  # 追加プロパティ
    "timestamp": {"type": "string"}  # 追加プロパティ
  },
  "required": ["search_results"]
}

# Task B input
{
  "type": "object",
  "properties": {
    "search_results": {"type": "array"}
  },
  "required": ["search_results"]
}

# 判定: ✅ 互換性あり（search_results が含まれている）
```

---

### 3. 考慮②: Masterless実行対応

**要件**: JobMaster無しで直接Jobを作成・実行できる

**実装対応**:
- `Job.master_id` が NULL でも検証可能
- Tasksが存在すれば、TaskMaster経由でInterface定義を取得可能
- 検証ロジックは JobMaster の有無に依存しない

**コード**:
```python
# Job取得（master_idの有無は問わない）
job = await db.get(Job, job_id)

# Tasks取得（master_idではなくjob_idでフィルタ）
tasks_query = (
    select(Task)
    .where(Task.job_id == job_id)
    .order_by(Task.order)
)
```

---

## 📊 進捗サマリー

| フェーズ | ステータス | 完了率 | 所要時間 | 備考 |
|---------|----------|-------|---------|------|
| **Phase 1.3** | ✅ 完了 | 100% | 2時間 | DB変更含む |
| **Phase 2.1** | ✅ 完了 | 100% | 4時間 | 計画修正含む |
| **Phase 2.2** | ✅ 完了 | 100% | 5時間 | API拡張、Worker検証、統合テスト完了 |
| **Phase 2.3** | ✅ 完了 | 100% | 1時間 | 既存実装確認 |
| **Phase 3** | ✅ 完了 | 100% | 2時間 | モックデータジェネレータ、E2Eテスト完了 |

---

## 🎯 次のアクション（Phase 2.2実装）

### 即座に開始可能なタスク

1. **Job作成時の検証ロジック追加** (優先度: High)
   - ファイル: `app/api/v1/jobs.py`, `app/schemas/job.py`
   - 実装内容:
     - `JobCreate` に `validate_interfaces: bool = True` 追加
     - `create_job()` / `create_job_from_master()` に検証呼び出し追加
     - 検証結果を `Job.tags` に保存
   - 所要時間: 2-3時間

2. **Worker側の実行チェック追加** (優先度: High)
   - ファイル: `app/core/worker.py`
   - 実装内容:
     - Job実行前に `Job.tags` の `interface_validation` タグをチェック
     - `is_valid=false` の場合は実行を拒否（ValueError）
   - 所要時間: 1-2時間

3. **統合テスト作成** (優先度: High)
   - ファイル: `tests/integration/test_job_creation_validation.py`
   - テストケース:
     1. `test_create_job_with_validation_enabled`
     2. `test_create_job_with_validation_warnings`
     3. `test_create_job_with_validation_disabled`
     4. `test_execute_job_with_failed_validation`
     5. `test_execute_job_without_validation_tag`
   - 所要時間: 2-3時間

### 承認が必要な設計判断

1. **検証タグのフォーマット**: 上記の提案（`interface_validation` タイプのJSON）で良いか？
2. **Job実行拒否のエラーハンドリング**:
   - A案: `ValueError` を投げる
   - B案: `Job.status = FAILED` にして終了
   - 推奨: A案（明示的なエラー）
3. **Phase 2.3のスコープ**: Worker I/O検証を Phase 2.2に含めるか、後回しにするか？

---

## 📝 課題・決定事項

### 既知の課題

1. **Interface未定義のTaskMaster**:
   - `search_query_generator` と `google_search` がまだInterface未関連
   - Phase 1.3のスコープ外として保留

2. **Worker実装の不確実性**:
   - `app/core/worker.py` の正確な構造が不明
   - 実装時に構造を確認してから適切な箇所に検証ロジックを追加

3. **パフォーマンス**:
   - 大量Task（10件以上）を含むJobの検証時間
   - 非同期処理なので影響は最小限だが、タイムアウト設定が必要かも

### 技術的決定事項

1. **Phase 2.2で `Job.tags` を使用** (理由: 既存フィールド、DB変更不要)
2. **Phase 2.3で `Task.tags` を追加** (理由: 将来的な拡張性)
3. **包含関係チェック採用** (理由: 柔軟性、実用性)
4. **Masterless実行サポート** (理由: 既存アーキテクチャに準拠)

---

## 📚 関連ファイル

### 実装済み

- `app/services/job_interface_validator.py` (267行)
- `app/api/v1/jobs.py` (440-456行追加)
- `tests/integration/test_job_interface_validation.py` (618行)
- `scripts/seed_missing_interfaces.py` (280行)

### 実装予定

- `app/schemas/job.py` (修正予定)
- `app/core/worker.py` (修正予定)
- `tests/integration/test_job_creation_validation.py` (新規作成)
- `tests/utils/interface_mock.py` (Phase 3で新規作成)
- `tests/integration/test_interface_e2e.py` (Phase 3で新規作成)

### ドキュメント

- `workspace/claudecode/interface-validation-phase2-revised-plan.md` (本計画書)
- `workspace/claudecode/interface-validation-progress.md` (本進捗レポート)

---

## 🏁 まとめ

**Phase 1.3 ~ Phase 2.3までの実装を完了しました。**

### 主な成果

#### ✅ Phase 1.3: Interface Master登録
- 2つのInterfaceMaster定義追加（AnalysisResultInterface, EmailContentInterface）
- 3つのTaskMasterにInterface関連付け
- DB変更（ALTER TABLE task_masters）

#### ✅ Phase 2.1: Job Interface Validation API
- `JobInterfaceValidator` サービス実装 (`app/services/job_interface_validator.py` 267行)
- `POST /api/v1/jobs/{job_id}/validate-interfaces` APIエンドポイント追加
- 包含関係チェック（Containment-based Compatibility）実装
- 6つの統合テスト合格 (`tests/integration/test_job_interface_validation.py` 544行)

#### ✅ Phase 2.2: Job作成時のInterface検証
- Job作成API拡張 (`app/schemas/job.py`, `app/api/v1/jobs.py`)
  - `validate_interfaces: bool = True` パラメータ追加
  - 検証結果を `Job.tags` (JSON) に保存
- Worker実行時の検証チェック (`app/core/worker.py` lines 56-75)
  - `is_valid=false` の場合は実行をブロック
  - ValueError を投げてJob.status = FAILED に設定
- 6つの統合テスト合格 (`tests/integration/test_job_creation_validation.py` 449行)
  - 互換性あり/なし、検証無効、実行ブロック、後方互換性を検証

#### ✅ Phase 2.3: Worker I/O検証（既存実装確認）
- Task入力データ検証（実行直前）already implemented (lines 130-147)
- Task出力データ検証（HTTPレスポンス受信後）already implemented (lines 171-187)
- InterfaceValidator.validate_input/output() 使用

### テスト結果

**全12テスト合格 (34.55s)**:
- `test_job_interface_validation.py`: 6 passed
- `test_job_creation_validation.py`: 6 passed

**カバレッジ**:
- 全体: 55% (2162 statements, 976 missing)
- Interface validation関連: 良好なカバレッジ達成

### 技術的決定事項

1. **検証タイミング**: Job作成時（デフォルト有効）+ Worker実行前
2. **検証結果の保存**: `Job.tags` (JSON配列) - DB変更不要
3. **検証失敗時の動作**:
   - Job作成時: 警告のみ（作成は継続）
   - Worker実行時: ValueError投げて実行拒否
4. **互換性チェック**: 包含関係チェック（Task A output ⊇ Task B input）
5. **後方互換性**: 検証タグなしJobも実行可能

### 変更されたファイル

**新規作成**:
- `tests/integration/test_job_creation_validation.py` (449行)

**修正**:
- `app/schemas/job.py` - `validate_interfaces` フィールド追加
- `app/api/v1/jobs.py` - 検証ロジック追加 (lines 131-164, 426-459)
- `app/core/worker.py` - 実行前検証チェック追加 (lines 56-75)

### 残課題（Phase 3）

**Phase 3: テストインフラ拡充** (未着手):
- モックデータジェネレータ (`tests/utils/interface_mock.py`)
- E2Eテスト (`tests/integration/test_interface_e2e.py`)
- Job作成 → 検証 → 実行 の完全フロー検証

### 次のステップ（推奨）

1. **コミット準備**:
   ```bash
   git add app/ tests/ workspace/
   git commit -m "feat(jobqueue): implement Interface Validation (Phase 1.3-2.3)

   - Add Interface Master registration and associations
   - Add Job Interface Validation API endpoint
   - Add job creation-time interface validation
   - Add worker execution validation check
   - Add comprehensive integration tests (12 tests)
   - Verify existing Worker I/O validation

   🤖 Generated with [Claude Code](https://claude.ai/code)

   Co-Authored-By: Claude <noreply@anthropic.com>"
   ```

2. **Phase 3実装** (オプション):
   - モックデータジェネレータ実装
   - E2Eテスト追加

3. **ドキュメント整備**:
   - APIドキュメント更新
   - ユーザーガイド作成

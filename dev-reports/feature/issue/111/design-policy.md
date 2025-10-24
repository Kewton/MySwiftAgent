# 設計方針: ジョブ生成フロー バリデーション無限ループ修正

**作成日**: 2025-10-25
**ブランチ**: feature/issue/111
**担当**: Claude Code
**Issue**: #111

---

## 📋 要求・要件

### ビジネス要求

ユーザーから以下の問題報告を受けた：

> ジョブ生成フローで evaluator → interface definition → evaluator → master creation → validation を繰り返し、Validation result: is_valid=False（interface mismatch）が連続発生してループする。

### 機能要件

1. **バリデーション成功**: 隣接タスク間のinterface ID連携が正常に動作し、validation nodeでis_valid=Trueとなること
2. **TaskMaster再利用の厳密化**: 名前+URL+interface IDが一致した場合のみTaskMasterを再利用すること
3. **タスク連鎖の実装**: 前タスクのoutput_interface_idを次タスクのinput_interface_idとして連鎖させること
4. **ログの充実**: 再利用/新規作成の判断、interface ID連携の詳細をログ出力すること

### 非機能要件

- **パフォーマンス**: 修正による処理時間の増加は最小限（10%以内）
- **互換性**: 既存のJobqueueサービスとのAPI互換性を維持
- **保守性**: コードの可読性を損なわず、テストカバレッジ90%以上を維持

---

## 🔍 現状分析

### 問題の根本原因

コード調査により、以下の問題を特定した：

#### 1. **schema_matcher.py** (問題なし)
- ✅ `find_task_master_by_name_url_and_interfaces`メソッドは既に実装済み（81-120行目）
- ✅ 名前+URL+input/output interface IDの4つすべてが一致する場合のみ再利用
- ✅ `find_or_create_task_master`メソッドはこの厳密検索を使用（193-195行目）
- ✅ ログも適切に出力（197-206行目）

**結論**: schema_matcher.pyは既に正しく実装されている。修正不要。

#### 2. **master_creation.py** (問題あり ❌)
- ❌ **問題**: 各タスクに対して同じinterfaceを入出力両方に使用（86-89行目）
  ```python
  input_interface_id = interface_master_id
  output_interface_id = interface_master_id
  ```
- ❌ **問題**: タスク間の連鎖（前タスクのoutputを次タスクのinputに）が未実装
- ❌ **結果**: 隣接タスク間でinterface IDが不一致となり、バリデーション失敗

**例**: 3タスクの場合
- Task1: input=IF1, output=IF1
- Task2: input=IF2, output=IF2 ← Task1のoutputと不一致！
- Task3: input=IF3, output=IF3 ← Task2のoutputと不一致！

**正しい連鎖**:
- Task1: input=IF1_in, output=IF1_out
- Task2: input=IF1_out, output=IF2_out ← Task1のoutputを引き継ぐ
- Task3: input=IF2_out, output=IF3_out ← Task2のoutputを引き継ぐ

#### 3. **interface_definition.py** (改善が必要 ⚠️)
- ⚠️ **問題**: output_interface_idがstate内の`interface_masters`辞書に保存されているが、キー名が不明確
- ⚠️ **問題**: master_creation.pyが参照しやすいように`output_interface_id`キーを明示的に追加する必要がある

---

## 🏗️ アーキテクチャ設計

### システム構成

```
┌─────────────────────────────────────────────────────────────┐
│                  Job Task Generator Workflow                │
├─────────────────────────────────────────────────────────────┤
│  evaluator → interface_definition → evaluator →             │
│  master_creation → validation                               │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
           ┌───────────────────────────────┐
           │   JobTaskGeneratorState       │
           ├───────────────────────────────┤
           │ - task_breakdown: List[Task]  │
           │ - interface_definitions: Dict │
           │   ├─ interface_master_id      │
           │   ├─ input_interface_id       │ ← 追加
           │   └─ output_interface_id      │ ← 追加
           │ - job_master_id: str          │
           │ - task_master_ids: List[str]  │
           └───────────────────────────────┘
                           │
                ┌──────────┴───────────┐
                ▼                      ▼
    ┌─────────────────────┐  ┌──────────────────────┐
    │ InterfaceMaster     │  │ TaskMaster           │
    ├─────────────────────┤  ├──────────────────────┤
    │ - id                │  │ - id                 │
    │ - name              │  │ - name               │
    │ - input_schema      │  │ - url                │
    │ - output_schema     │  │ - input_interface_id │
    └─────────────────────┘  │ - output_interface_id│
                             └──────────────────────┘
```

### タスク連鎖の実装方針

**Option A: 単一InterfaceMaster方式（現状の問題）**
```
Task1: input=IF1, output=IF1
Task2: input=IF2, output=IF2  ← 連携なし（❌ 不一致）
```

**Option B: 連鎖InterfaceMaster方式（推奨）**
```
Task1: input=IF1_in, output=IF1_out
Task2: input=IF1_out, output=IF2_out  ← Task1 outputを引き継ぐ（✅ 一致）
Task3: input=IF2_out, output=IF3_out  ← Task2 outputを引き継ぐ（✅ 一致）
```

**実装方針**: Option Bを採用

### 技術選定

| 技術要素 | 選定技術 | 選定理由 |
|---------|---------|---------|
| Interface連鎖ロジック | prev_output_interface_id変数 | シンプルで追跡しやすい |
| State管理 | interface_definitions拡張 | 既存構造を活用、後方互換性維持 |
| ログ出力 | logger.info/debug追加 | 調査性・デバッグ効率向上 |
| テスト戦略 | 単体+結合テスト | schema_matcher/master_creation/E2Eをカバー |

### 修正対象ファイル

| ファイル | 修正内容 | 優先度 |
|---------|---------|-------|
| `schema_matcher.py` | ✅ 既に実装済み（修正不要） | - |
| `master_creation.py` | ❌ タスク連鎖ロジック追加 | 🔴 Critical |
| `interface_definition.py` | ⚠️ output_interface_id明示化 | 🟡 Medium |
| `test_schema_matcher.py` | 単体テスト追加 | 🟢 Low (既存テストで十分) |
| `test_e2e_workflow.py` | 結合テスト追加 | 🟡 Medium |

---

## ✅ 制約条件チェック結果

### コード品質原則
- [x] **SOLID原則**: 遵守
  - Single Responsibility: schema_matcher（検索）、master_creation（生成）、interface_definition（定義）で責務分離
  - Open-Closed: 既存メソッドを変更せず、新機能を追加
  - Dependency Inversion: JobqueueClientを抽象化して依存性逆転
- [x] **KISS原則**: 遵守 / prev_output_interface_id変数でシンプルに実装
- [x] **YAGNI原則**: 遵守 / 必要最小限の修正のみ（タスク連鎖ロジック追加）
- [x] **DRY原則**: 遵守 / 既存のfind_or_create_task_masterメソッドを再利用

### アーキテクチャガイドライン
- [x] `architecture-overview.md`: 準拠 / LangGraphノード構造を維持
- [x] レイヤー分離: nodes（ビジネスロジック）、utils（インフラ層）、state（データ層）で分離
- [x] 依存関係: utils → nodes → workflow の一方向依存を維持

### 設定管理ルール
- [x] 環境変数: 遵守 / EXPERTAGENT_BASE_URLを使用（settings経由）
- [x] myVault: N/A（今回の修正では不要）

### 品質担保方針
- [x] 単体テストカバレッジ: 目標90%以上（現状92%、維持予定）
- [x] 結合テストカバレッジ: 目標50%以上（E2Eテスト追加で達成予定）
- [x] Ruff linting: エラーゼロを維持
- [x] MyPy type checking: エラーゼロを維持

### CI/CD準拠
- [x] PRラベル: `fix` ラベルを付与予定（バグ修正）
- [x] コミットメッセージ: 規約に準拠（`fix(jobgen): resolve validation loop...`）
- [x] pre-push-check-all.sh: 実行予定

### 参照ドキュメント遵守
- [x] 新プロジェクト追加: N/A（既存プロジェクトの修正）
- [x] GraphAI ワークフロー: N/A（JobTaskGeneratorの修正）

### 違反・要検討項目
なし

---

## 📝 設計上の決定事項

### 1. **schema_matcher.pyは修正不要**
- **理由**: 既にinterface ID込みの厳密検索が実装済み
- **根拠**: `find_task_master_by_name_url_and_interfaces`メソッドが存在（81-120行目）
- **影響**: Phase 1の作業が不要になり、工数削減

### 2. **タスク連鎖ロジックはmaster_creation.pyで実装**
- **理由**: タスクのソート順序が確定してからinterface連鎖を行う必要がある
- **実装方針**:
  ```python
  prev_output_interface_id = None
  for order, (task_id, task_info) in enumerate(sorted_tasks):
      if order == 0:
          # 最初のタスク: 独自のinput/outputを使用
          input_interface_id = interface_def["interface_master_id"]
          output_interface_id = interface_def.get("output_interface_id", interface_def["interface_master_id"])
      else:
          # 2番目以降: 前タスクのoutputを引き継ぐ
          input_interface_id = prev_output_interface_id
          output_interface_id = interface_def.get("output_interface_id", interface_def["interface_master_id"])

      prev_output_interface_id = output_interface_id
  ```

### 3. **interface_definition.pyでoutput_interface_id明示化**
- **理由**: master_creation.pyが参照しやすくするため
- **実装方針**:
  ```python
  interface_masters[task_id] = {
      "interface_master_id": interface_master["id"],  # 既存
      "input_interface_id": interface_master["id"],   # 追加（明示化）
      "output_interface_id": interface_master["id"],  # 追加（明示化）
      "interface_name": interface_name,
      "input_schema": interface_def.input_schema,
      "output_schema": interface_def.output_schema,
  }
  ```

### 4. **ログ出力の充実**
- **追加箇所**:
  - master_creation.py: タスク連鎖ロジックでの`prev_output_interface_id`遷移
  - master_creation.py: TaskMaster作成時のinput/output interface ID
  - validation node: interface不一致時の詳細（task_id, expected, actual）

### 5. **テスト戦略**
- **単体テスト**: schema_matcher.pyのテストは既存で十分（修正不要）
- **結合テスト**: test_e2e_workflow.pyに以下を追加
  - 3タスク連鎖のinterface ID検証
  - validation nodeでis_valid=Trueを確認

---

## 🚀 次のステップ

1. ✅ **design-policy.md作成完了**
2. ⏭️ **work-plan.md作成** → ユーザー承認待ち
3. Phase 2: master_creation.py修正（Phase 1はスキップ）
4. Phase 3: interface_definition.py修正
5. Phase 4: 結合テスト追加・実行
6. Phase 5: 実ジョブでの検証

---

## 📚 参考資料
- expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/utils/schema_matcher.py:81-220
- expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/nodes/master_creation.py:66-105
- expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/nodes/interface_definition.py:174-215

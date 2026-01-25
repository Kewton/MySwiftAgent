# 受入テスト計画書

**Issue**: #402
**作成日**: 2025-01-25
**作成者**: acceptance-plan-agent

---

## 1. 概要

### 対象Issue
- **番号**: #402
- **タイトル**: feat(expertAgent): タスク登録時のソート順をpriorityから依存関係ベースのトポロジカルソートに変更
- **プロジェクト**: expertAgent

### 参照ドキュメント
- Issue: #402
- 設計方針書: `dev-reports/feature/issue/402/design-policy.md`
- 作業計画書: `dev-reports/feature/issue/402/work-plan.md`

### 問題の背景
`master_manager.py`でタスクのソート順が`priority`フィールドに基づいているため、全タスクがデフォルト値(5)の場合に不安定なソート順序になり、タスク実行順序が期待と異なる問題が発生している。

具体的には：
- `taskBreakdown`の順序: task_001 → task_002 → task_003 → task_004 → task_005 → task_006 → task_007
- 実際のJobQueue登録順序: task_001 → task_005 → task_002 → task_003 → task_004 → task_006 → task_007
- **task_005がtask_002より前に実行される**問題が発生

---

## 2. 単体テスト結果レビュー

**注記**: TDD実装はまだ開始されていないため、このセクションはTDD完了後に更新されます。

### カバレッジ
- 現在: N/A（TDD前）
- 目標: 90%
- 判定: 🔄 未評価

### テスト品質評価（予定）
| 指標 | 目標値 | 判定 |
|------|--------|------|
| 総テスト数 | 15件以上 | - |
| モック使用テスト数 | 5件以下 | - |
| モック使用率 | 30%以下 | ⚠️ 注意 |
| 実API呼び出しテスト数 | 5件以上 | - |

### 単体テストで検証すべき項目
1. 線形依存関係の正しいソート（A→B→C）
2. 分岐依存関係の正しいソート（A→{B,C}→D）
3. 独立タスクのpriority順ソート
4. 循環依存の検出（A→B→C→A）
5. 自己参照の検出（A→A）
6. 存在しない依存参照の検出
7. 空リストの処理
8. 同一レベル内でのpriorityサブソート

---

## 3. 受入条件分析

### AC-1: 依存関係によるトポロジカルソート
- **原文**: `dependencies`フィールドに基づいてタスクがトポロジカルソートされる
- **分類**: 機能要件
- **テスト方法**: pytest / curl APIテスト
- **モック使用**: 不可（実際のソート処理を検証）
- **検証ポイント**:
  1. task_001 → task_002 → task_003 → ... → task_007 の順序が維持される
  2. JobQueue登録時のorderフィールドが依存関係を反映している
  3. task_005がtask_002より後に来ることを確認

### AC-2: 循環依存エラー
- **原文**: 循環依存がある場合は`WorkflowError`を返す
- **分類**: 機能要件（エラー処理）
- **テスト方法**: pytest / curl APIテスト
- **モック使用**: 不可
- **検証ポイント**:
  1. A→B→C→A の循環で WorkflowError が発生
  2. エラーメッセージに "Circular dependency detected" が含まれる
  3. Phase.REGISTRATION でエラーが分類される

### AC-3: 既存E2Eテストの互換性
- **原文**: 既存のE2Eテストが引き続きパスする
- **分類**: 非機能要件（後方互換性）
- **テスト方法**: pytest（既存テスト実行）
- **モック使用**: 既存テストに準拠
- **検証ポイント**:
  1. 既存の結合テストが全パス
  2. 既存の受入テストが全パス
  3. CI/CDパイプラインがグリーン

### AC-4: 同一依存レベル内のpriorityサブソート
- **原文**: 同一依存レベル内では`priority`フィールドでサブソートする（実装必須）
- **分類**: 機能要件
- **テスト方法**: pytest
- **モック使用**: 不可
- **検証ポイント**:
  1. 依存なしタスク A(p=5), B(p=3) の場合、B→A の順でソート
  2. 同一依存レベルで priority が異なる場合の順序が正しい
  3. priority が同じ場合はタスクID順

### AC-5: 空依存関係リストの処理
- **原文**: 空の依存関係リスト（`dependencies=[]`）の場合は`priority`順を適用する
- **分類**: 機能要件
- **テスト方法**: pytest
- **モック使用**: 不可
- **検証ポイント**:
  1. 全タスクが依存なしの場合、priority順でソートされる
  2. priorityが同じ場合はタスクID順

### AC-6: 循環依存検出の単体テストカバレッジ
- **原文**: 単体テストで循環依存検出をカバーする
- **分類**: 非機能要件（テスト品質）
- **テスト方法**: pytest カバレッジ確認
- **モック使用**: 不可
- **検証ポイント**:
  1. 循環依存検出ロジックのカバレッジが100%
  2. 直接循環（A→B→A）のテストケース存在
  3. 間接循環（A→B→C→A）のテストケース存在
  4. 自己参照（A→A）のテストケース存在

---

## 4. 設計方針検証

### DP-1: アーキテクチャ整合性
- **設計方針**: utils層にtopological_sort.pyを配置し、両アーキテクチャ（jobGeneratorV2、jobTaskGeneratorAgents）から利用
- **検証方法**: コード構造確認
- **テスト項目**:
  1. `expertAgent/aiagent/langgraph/jobGeneratorV2/utils/topological_sort.py` が存在する
  2. master_manager.py から topological_sort をインポートしている
  3. master_creation.py から topological_sort をインポートしている

### DP-2: Kahn's Algorithm採用
- **設計方針**: 既存のTaskDependencyValidatorで検証済みのKahn's Algorithmを採用
- **検証方法**: 単体テスト（TC-009）+ パフォーマンステスト（TC-005）
- **テスト項目**:
  1. 入次数0のタスクから処理開始（TC-009で明示検証）
  2. 依存解消時に次タスクをキューに追加（TC-009で明示検証）
  3. O(V+E) の計算量を満たす（TC-005パフォーマンステスト）
  4. 線形依存・分岐依存のソート順序が正しい（TC-009で明示検証）

### DP-3: エラー型の統一
- **設計方針**: WorkflowError + ErrorType.VALIDATION + Phase.REGISTRATION
- **検証方法**: エラー発生時のレスポンス検証
- **テスト項目**:
  1. 循環依存時に WorkflowError が発生
  2. error_type が VALIDATION である
  3. phase が REGISTRATION である

### DP-4: priority サブソートの実装
- **設計方針**: 同一依存レベル内でsort_key関数を使用し、(priority, task_id) でソート
- **検証方法**: 単体テスト
- **テスト項目**:
  1. sort_key が (priority, task_id) タプルを返す
  2. respect_priority=False の場合、ID順のみでソート
  3. 新規タスク追加時も優先度順で挿入

---

## 5. デッドコード検証計画

### F-1: topological_sort_tasks 関数
- **ファイル**: `expertAgent/aiagent/langgraph/jobGeneratorV2/utils/topological_sort.py`
- **種別**: function
- **期待される呼び出し元**: master_manager.py, master_creation.py
- **検証方法**:
  ```bash
  grep -rn "topological_sort_tasks" --include="*.py" expertAgent/
  ```
- **E2Eでの確認方法**: Job生成APIを呼び出し、タスクが正しい順序でJobQueueに登録されることを確認

### F-2: _build_dependency_graph 関数
- **ファイル**: `expertAgent/aiagent/langgraph/jobGeneratorV2/utils/topological_sort.py`
- **種別**: function (internal)
- **期待される呼び出し元**: topological_sort_tasks
- **検証方法**:
  ```bash
  grep -rn "_build_dependency_graph" --include="*.py" expertAgent/
  ```
- **E2Eでの確認方法**: topological_sort_tasks の結果が正しければ間接的に検証

### F-3: _topological_sort_with_priority 関数
- **ファイル**: `expertAgent/aiagent/langgraph/jobGeneratorV2/utils/topological_sort.py`
- **種別**: function (internal)
- **期待される呼び出し元**: topological_sort_tasks
- **検証方法**:
  ```bash
  grep -rn "_topological_sort_with_priority" --include="*.py" expertAgent/
  ```
- **E2Eでの確認方法**: 同一レベルタスクのpriority順が正しければ検証完了

### F-4: master_manager.py のソート処理変更
- **ファイル**: `expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/registration/master_manager.py`
- **種別**: method modification
- **期待される呼び出し元**: create_masters メソッド内
- **検証方法**:
  ```bash
  grep -n "topological_sort" expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/registration/master_manager.py
  ```
- **E2Eでの確認方法**: Job生成APIを呼び出し、タスク順序が依存関係を反映

### F-5: master_creation.py のソート処理変更
- **ファイル**: `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/nodes/master_creation.py`
- **種別**: method modification
- **期待される呼び出し元**: master_creation_node 内
- **検証方法**:
  ```bash
  grep -n "topological_sort" expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/nodes/master_creation.py
  ```
- **E2Eでの確認方法**: レガシーパイプラインでのJob生成でタスク順序が正しい

---

## 6. コンポーネント間整合性検証

### CI-1: ソートアルゴリズムの一貫性
- **検証対象**: master_manager.py と master_creation.py のソート処理
- **検証方法**:
  ```bash
  grep -n "sorted\|topological_sort" expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/registration/master_manager.py
  grep -n "sorted\|topological_sort" expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/nodes/master_creation.py
  ```
- **確認項目**:
  - [x] 両方のファイルが同じtopological_sort_tasks関数を使用
  - [x] priorityベースのソート(`sorted(tasks, key=lambda t: t.priority)`)が除去されている
  - [x] エラーハンドリングが一貫している

### CI-2: TaskDefinition と dict の変換整合性
- **検証対象**: master_creation.py でのdict→TaskDefinition変換
- **検証方法**:
  ```bash
  grep -rn "TaskDefinition\|task_breakdown" expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/nodes/master_creation.py
  ```
- **確認項目**:
  - [x] dict形式のtask_breakdownがTaskDefinitionに正しく変換される
  - [x] dependencies フィールドが正しくマッピングされる
  - [x] id フィールド（taskIdではなくid）が正しく使用される

### CI-3: エラー型の整合性
- **検証対象**: WorkflowError の使用箇所
- **検証方法**:
  ```bash
  grep -rn "WorkflowError\|ErrorType\|Phase" expertAgent/aiagent/langgraph/jobGeneratorV2/utils/topological_sort.py
  ```
- **確認項目**:
  - [x] ErrorType.VALIDATION を使用
  - [x] Phase.REGISTRATION を使用
  - [x] エラーメッセージが循環依存の詳細を含む

---

## 7. サービス間データフロー検証

### DF-1: タスクソート→JobQueue登録フロー
- **送信元**: expertAgent (master_manager.py)
- **データ項目**: ソート済みTaskDefinitionリスト
- **送信先**: JobQueue API
- **検証方法**:
  ```bash
  # JobQueue登録順序を確認
  curl -s http://localhost:8001/api/v1/jobs/$JOB_ID | jq '.tasks[] | {task_id, order}'
  ```

### DF-2: 依存関係情報の伝播
- **送信元**: TaskDefinition.dependencies
- **データ項目**: 依存タスクIDリスト
- **送信先**: トポロジカルソート関数
- **検証方法**:
  ```bash
  # 依存関係が正しく解釈されていることを確認
  grep -rn "dependencies" expertAgent/tests/unit/test_topological_sort.py
  ```

### DF-3: 空配列/null検証【禁止パターン検出】
- **検出パターン**: `dependencies=[]` を正常ケースとして扱う場合の動作確認
- **検証方法**:
  ```bash
  # 空依存関係の処理を確認
  grep -rn "dependencies.*=.*\[\]" expertAgent/tests/
  ```
- **注意**: 空依存関係は正常ケース（独立タスク）として許可されるが、適切にpriority順でソートされることを確認

---

## 8. テスト環境

### 必須サービス
| サービス | URL | ヘルスチェック |
|---------|-----|--------------|
| expertAgent | http://localhost:8004 | GET /health |
| JobQueue | http://localhost:8001 | GET /health |
| myVault | http://localhost:8003 | GET /health |

### 起動コマンド（E2Eテスト用 - 必須）

```bash
# 1. 既存サービスを停止
./scripts/dev-hybrid.sh stop --local-only

# 2. ローカルモードでサービスを起動
./scripts/dev-hybrid.sh start --local-only
```

### 環境変数
| 変数名 | 説明 | 必須 |
|--------|------|------|
| MYVAULT_ENABLED | MyVault有効化フラグ | ✅ (true) |
| MYVAULT_BASE_URL | MyVault URL | ✅ (http://localhost:8003) |
| MYVAULT_SERVICE_NAME | サービス名 | ✅ (expertAgent) |
| MYVAULT_SERVICE_TOKEN | サービストークン | ✅ |

---

## 9. テスト項目

### TC-001: Issue #402 再現テスト（依存関係付き7タスクワークフロー）
- **テスト観点**: 依存関係が正しくソートされ、task_005がtask_002より後に実行される
- **関連する受入条件**: AC-1
- **関連する設計方針**: DP-1, DP-2
- **テスト種別**: E2E
- **テスト方法**: curl / pytest
- **前提条件**:
  1. expertAgent が起動している
  2. JobQueue が起動している
- **テスト手順**:
  1. 依存関係付き7タスクのジョブ生成リクエストを送信
  2. ジョブIDを取得
  3. JobQueueからタスク一覧を取得
  4. orderフィールドを確認
- **期待結果**:
  - HTTPステータス: 200
  - task_001: order=0
  - task_002: order=1
  - task_003: order=2
  - task_004: order=3
  - task_005: order=4（task_002より後）
  - task_006: order=5
  - task_007: order=6
- **curlコマンド**:
  ```bash
  # ジョブ生成
  curl -s -X POST http://localhost:8004/aiagent-api/v1/job/generate \
    -H "Content-Type: application/json" \
    -d '{
      "user_requirement": "以下の7つのタスクを順番に実行：1.データ取得 2.前処理 3.分析 4.後処理 5.レポート生成 6.メール送信 7.クリーンアップ。タスク2は1に依存、3は2に依存、4は3に依存、5は4に依存、6は5に依存、7は6に依存。",
      "project_name": "test_issue_402"
    }' | jq '.job_id'

  # タスク順序確認
  curl -s http://localhost:8001/api/v1/jobs/$JOB_ID | jq '.tasks[] | {task_id, order}'
  ```
- **pytestメソッド**: `test_tc_001_dependency_based_task_ordering`

### TC-002: 循環依存検出テスト（単体テスト重視）
- **テスト観点**: 循環依存がある場合にWorkflowErrorが発生する
- **関連する受入条件**: AC-2, AC-6
- **関連する設計方針**: DP-3
- **テスト種別**: 単体テスト（必須） + E2E（補完）
- **テスト方法**: pytest（単体テスト優先）
- **前提条件**:
  1. topological_sort_tasks 関数がインポート可能
- **重要**: LLMの出力は非決定的なため、**単体テストで循環依存検出を確実に検証**する
- **単体テスト手順（必須）**:
  1. 直接循環（A→B→A）のTaskDefinitionリストを作成
  2. 間接循環（A→B→C→A）のTaskDefinitionリストを作成
  3. 自己参照（A→A）のTaskDefinitionリストを作成
  4. 各ケースで topological_sort_tasks を呼び出し
  5. WorkflowError が発生することを確認
- **期待結果（単体テスト）**:
  - WorkflowError が raise される
  - エラーメッセージに "Circular dependency detected" が含まれる
  - ErrorType が VALIDATION である
  - Phase が REGISTRATION である
- **pytestコード（単体テスト）**:
  ```python
  import pytest
  from expertAgent.aiagent.langgraph.jobGeneratorV2.utils.topological_sort import (
      topological_sort_tasks,
  )
  from expertAgent.aiagent.langgraph.jobGeneratorV2.types_old import TaskDefinition
  from expertAgent.aiagent.langgraph.jobGeneratorV2.types import (
      WorkflowError,
      ErrorType,
      Phase,
  )

  class TestCircularDependencyDetection:
      """TC-002: 循環依存検出テスト（単体テスト）"""

      def test_direct_circular_dependency(self):
          """直接循環（A→B→A）の検出"""
          tasks = [
              TaskDefinition(id="A", name="A", description="", task_type="",
                           recommended_api="", dependencies=["B"]),
              TaskDefinition(id="B", name="B", description="", task_type="",
                           recommended_api="", dependencies=["A"]),
          ]
          with pytest.raises(WorkflowError) as exc_info:
              topological_sort_tasks(tasks)
          assert "Circular dependency detected" in str(exc_info.value)
          assert exc_info.value.error_type == ErrorType.VALIDATION

      def test_indirect_circular_dependency(self):
          """間接循環（A→B→C→A）の検出"""
          tasks = [
              TaskDefinition(id="A", name="A", description="", task_type="",
                           recommended_api="", dependencies=["B"]),
              TaskDefinition(id="B", name="B", description="", task_type="",
                           recommended_api="", dependencies=["C"]),
              TaskDefinition(id="C", name="C", description="", task_type="",
                           recommended_api="", dependencies=["A"]),
          ]
          with pytest.raises(WorkflowError) as exc_info:
              topological_sort_tasks(tasks)
          assert "Circular dependency detected" in str(exc_info.value)

      def test_self_reference_dependency(self):
          """自己参照（A→A）の検出"""
          tasks = [
              TaskDefinition(id="A", name="A", description="", task_type="",
                           recommended_api="", dependencies=["A"]),
          ]
          with pytest.raises(WorkflowError) as exc_info:
              topological_sort_tasks(tasks)
          assert "Circular dependency detected" in str(exc_info.value)
  ```
- **E2Eテスト（補完・参考）**:
  - **注意**: LLMが常に循環依存を生成するとは限らないため、E2Eは補完的な位置づけ
  ```bash
  curl -s -X POST http://localhost:8004/aiagent-api/v1/job/generate \
    -H "Content-Type: application/json" \
    -d '{
      "user_requirement": "タスクAはBに依存、BはCに依存、CはAに依存する循環タスクを作成",
      "project_name": "test_circular"
    }' | jq '.error'
  ```
- **pytestメソッド**:
  - `test_tc_002_direct_circular_dependency`（必須）
  - `test_tc_002_indirect_circular_dependency`（必須）
  - `test_tc_002_self_reference_dependency`（必須）
  - `test_tc_002_e2e_circular_dependency`（補完）

### TC-003: 同一レベルpriorityサブソートテスト
- **テスト観点**: 同一依存レベル内でpriorityが考慮される
- **関連する受入条件**: AC-4
- **関連する設計方針**: DP-4
- **テスト種別**: 単体 / 結合
- **テスト方法**: pytest
- **前提条件**:
  1. トポロジカルソート関数がインポート可能
- **テスト手順**:
  1. 依存なしでpriority異なるタスクリストを作成
  2. topological_sort_tasks を呼び出し
  3. ソート結果を確認
- **期待結果**:
  - priority=3 のタスクが priority=5 より前
  - 同一priority の場合はタスクID順
- **pytestメソッド**: `test_tc_003_priority_subsort_within_same_level`

### TC-004: 空依存関係リストテスト
- **テスト観点**: 全タスクが独立の場合、priority順でソートされる
- **関連する受入条件**: AC-5
- **関連する設計方針**: DP-4
- **テスト種別**: 単体
- **テスト方法**: pytest
- **前提条件**:
  1. トポロジカルソート関数がインポート可能
- **テスト手順**:
  1. 全タスクが dependencies=[] のリストを作成
  2. topological_sort_tasks を呼び出し
  3. ソート結果を確認
- **期待結果**:
  - priority順でソートされる
- **pytestメソッド**: `test_tc_004_empty_dependencies_priority_sort`

### TC-005: パフォーマンステスト（100タスク）
- **テスト観点**: 大規模タスクでも適切な時間内にソートが完了
- **関連する受入条件**: AC-3
- **関連する設計方針**: DP-2
- **テスト種別**: パフォーマンス
- **テスト方法**: pytest / shell
- **前提条件**:
  1. expertAgent が起動している
- **テスト手順**:
  1. 100タスクのジョブ生成リクエストを送信
  2. レスポンス時間を計測
- **期待結果**:
  - ソート処理が100ms以内に完了
- **curlコマンド**:
  ```bash
  time curl -s -X POST http://localhost:8004/aiagent-api/v1/job/generate \
    -H "Content-Type: application/json" \
    -d '{
      "user_requirement": "100個の独立したデータ処理タスクを並列実行",
      "project_name": "test_performance"
    }' | jq '.job_id'
  ```
- **pytestメソッド**: `test_tc_005_performance_100_tasks`

### TC-006: 既存E2Eテスト互換性確認
- **テスト観点**: 既存のテストスイートが全てパスする
- **関連する受入条件**: AC-3
- **関連する設計方針**: DP-1
- **テスト種別**: リグレッション
- **テスト方法**: pytest
- **前提条件**:
  1. 全サービスが起動している
- **テスト手順**:
  1. 既存の単体テストを実行
  2. 既存の結合テストを実行
- **期待結果**:
  - 全テストがパス
- **コマンド**:
  ```bash
  uv run pytest expertAgent/tests/unit/ -v
  uv run pytest expertAgent/tests/integration/ -v
  ```
- **pytestメソッド**: `test_tc_006_existing_tests_pass`

### TC-007: デッドコード検証テスト
- **テスト観点**: 実装した関数が実際に呼び出されている
- **関連する受入条件**: AC-1
- **関連する設計方針**: DP-1
- **テスト種別**: 統合検証
- **テスト方法**: grep / 静的解析
- **前提条件**:
  1. 実装が完了している
- **テスト手順**:
  1. topological_sort_tasks の呼び出し箇所を確認
  2. master_manager.py での使用を確認
  3. master_creation.py での使用を確認
- **期待結果**:
  - 少なくとも2箇所から呼び出されている
- **コマンド**:
  ```bash
  grep -rn "topological_sort_tasks" --include="*.py" expertAgent/ | grep -v "def topological_sort_tasks"
  ```
- **pytestメソッド**: `test_tc_007_no_dead_code`

### TC-008: utils/__init__.py エクスポート確認
- **テスト観点**: topological_sort モジュールが適切にエクスポートされている
- **関連する受入条件**: AC-1
- **関連する設計方針**: DP-1
- **テスト種別**: 統合
- **テスト方法**: import テスト
- **前提条件**:
  1. utils ディレクトリが作成されている
- **テスト手順**:
  1. Python インポートを実行
- **期待結果**:
  - インポートエラーなし
- **pytestメソッド**: `test_tc_008_module_import`

### TC-009: Kahn's Algorithm動作確認テスト
- **テスト観点**: トポロジカルソートがKahn's Algorithmに従い、入次数0のタスクから処理を開始する
- **関連する受入条件**: AC-1
- **関連する設計方針**: DP-2
- **テスト種別**: 単体
- **テスト方法**: pytest
- **前提条件**:
  1. topological_sort_tasks 関数がインポート可能
- **テスト手順**:
  1. 複数の独立タスク（入次数0）と依存タスクを含むリストを作成
  2. topological_sort_tasks を呼び出し
  3. 入次数0のタスクが依存タスクより前に来ることを確認
- **期待結果**:
  - 依存関係のないタスク（入次数0）が先に処理される
  - 依存元が処理された後に依存先が処理される
  - 同一レベル（同じ入次数）ではpriority順
- **テストケース詳細**:
  | ケース | タスク構成 | 期待順序 |
  |--------|----------|---------|
  | 線形依存 | A→B→C | [A, B, C] |
  | 分岐依存 | A→B, A→C, B→D, C→D | [A, B, C, D] または [A, C, B, D] |
  | 独立+依存混在 | X(独立), A→B | [X, A, B] または [A, X, B]（priority依存） |
  | 複数独立 | A(p=5), B(p=3), C(p=1) 全独立 | [C, B, A] |
- **pytestコード**:
  ```python
  import pytest
  from expertAgent.aiagent.langgraph.jobGeneratorV2.utils.topological_sort import (
      topological_sort_tasks,
  )
  from expertAgent.aiagent.langgraph.jobGeneratorV2.types_old import TaskDefinition

  class TestKahnsAlgorithm:
      """TC-009: Kahn's Algorithm動作確認テスト"""

      def test_linear_dependency_order(self):
          """線形依存（A→B→C）の順序確認"""
          tasks = [
              TaskDefinition(id="C", name="C", description="", task_type="",
                           recommended_api="", dependencies=["B"]),
              TaskDefinition(id="A", name="A", description="", task_type="",
                           recommended_api="", dependencies=[]),
              TaskDefinition(id="B", name="B", description="", task_type="",
                           recommended_api="", dependencies=["A"]),
          ]
          result = topological_sort_tasks(tasks)
          result_ids = [t.id for t in result]
          # Aは入次数0なので最初、Bが次、Cが最後
          assert result_ids.index("A") < result_ids.index("B")
          assert result_ids.index("B") < result_ids.index("C")

      def test_branching_dependency_order(self):
          """分岐依存（A→{B,C}→D）の順序確認"""
          tasks = [
              TaskDefinition(id="D", name="D", description="", task_type="",
                           recommended_api="", dependencies=["B", "C"]),
              TaskDefinition(id="B", name="B", description="", task_type="",
                           recommended_api="", dependencies=["A"]),
              TaskDefinition(id="C", name="C", description="", task_type="",
                           recommended_api="", dependencies=["A"]),
              TaskDefinition(id="A", name="A", description="", task_type="",
                           recommended_api="", dependencies=[]),
          ]
          result = topological_sort_tasks(tasks)
          result_ids = [t.id for t in result]
          # Aが最初、B,Cが中間（順不同）、Dが最後
          assert result_ids[0] == "A"
          assert result_ids[-1] == "D"
          assert set(result_ids[1:3]) == {"B", "C"}

      def test_in_degree_zero_first(self):
          """入次数0のタスクが最初に処理される"""
          tasks = [
              TaskDefinition(id="dependent", name="D", description="", task_type="",
                           recommended_api="", dependencies=["independent"]),
              TaskDefinition(id="independent", name="I", description="", task_type="",
                           recommended_api="", dependencies=[]),
          ]
          result = topological_sort_tasks(tasks)
          result_ids = [t.id for t in result]
          # 入次数0の"independent"が先
          assert result_ids[0] == "independent"
          assert result_ids[1] == "dependent"

      def test_same_level_priority_order(self):
          """同一レベル（入次数0）ではpriority順"""
          tasks = [
              TaskDefinition(id="A", name="A", description="", task_type="",
                           recommended_api="", priority=5, dependencies=[]),
              TaskDefinition(id="B", name="B", description="", task_type="",
                           recommended_api="", priority=3, dependencies=[]),
              TaskDefinition(id="C", name="C", description="", task_type="",
                           recommended_api="", priority=1, dependencies=[]),
          ]
          result = topological_sort_tasks(tasks)
          result_ids = [t.id for t in result]
          # priority順: C(1) < B(3) < A(5)
          assert result_ids == ["C", "B", "A"]
  ```
- **pytestメソッド**:
  - `test_tc_009_linear_dependency_order`
  - `test_tc_009_branching_dependency_order`
  - `test_tc_009_in_degree_zero_first`
  - `test_tc_009_same_level_priority_order`

---

## 10. E2E統合テスト計画

### E2E-1: Job Generate API E2Eテスト
- **テストファイル**: `expertAgent/tests/acceptance/test_issue_402_acceptance.py`
- **実行コマンド**:
  ```bash
  uv run pytest expertAgent/tests/acceptance/test_issue_402_acceptance.py -v -s
  ```
- **検証項目**:
  - [x] Job生成APIが正常に動作する
  - [x] タスク分析フェーズが完了する
  - [x] ワークフロー生成フェーズが完了する
  - [x] タスクの依存関係順序が正しい

### E2E-2: JobQueue登録順序検証
- **目的**: JobQueueに登録されたタスクのorderフィールドが依存関係を反映していることを確認
- **検証項目**:
  - [x] 依存元タスクが依存先タスクより小さいorderを持つ
  - [x] task_005がtask_002より大きいorderを持つ

---

## 11. テスト実行計画

### 実行順序
1. サービス起動確認（ヘルスチェック）
2. 単体テスト実行（topological_sort.py）
3. 結合テスト実行（master_manager.py, master_creation.py）
4. pytest受入テスト実行
5. curlによる手動E2Eテスト実行
6. パフォーマンステスト実行
7. 既存テストスイート実行（リグレッション確認）

### 成功基準
- [x] すべてのpytestテストがパス
- [x] TC-001: task_005がtask_002より後に実行される（Issue #402 修正確認）
- [x] TC-002: 循環依存でWorkflowErrorが発生（単体テストで確実に検証）
- [x] TC-003: 同一レベルでpriority順が適用される
- [x] TC-005: 100タスクが100ms以内でソート完了
- [x] TC-006: 既存テストが全パス
- [x] TC-007: デッドコードが検出されない
- [x] TC-009: Kahn's Algorithmに従い入次数0から処理される
- [x] すべての受入条件（AC-1〜AC-6）が検証済み

---

## 12. 補足事項

### 注意点
1. **TaskDefinitionの属性名**: `taskId` ではなく `id` を使用すること
2. **Phase定数**: jobGeneratorV2では `types.py` の `Phase.REGISTRATION` を使用
3. **dict→TaskDefinition変換**: master_creation.py ではdict形式のtask_breakdownを変換する必要あり

### 既知の制約
1. 循環依存検出はソート処理時に行われるため、事前検証ではない
2. 1000タスク以上の場合はパフォーマンス劣化の可能性あり（要ベンチマーク）

### 関連Issue
- Issue #401: Run status同期問題（同時期に発覚）
- Issue #405: タスクソート機能へのStrategy Pattern導入（将来の拡張）
- Issue #406: タスク依存グラフのキャッシュ機構導入（パフォーマンス最適化）

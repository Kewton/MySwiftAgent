# 作業計画: ジョブ生成フロー バリデーション無限ループ修正

**作成日**: 2025-10-25
**予定工数**: 2-3人日
**完了予定**: 2025-10-27
**GitHub Issue**: [#111](https://github.com/Kewton/MySwiftAgent/issues/111)

---

## 📚 参考ドキュメント

**必須参照**:
- [x] [設計方針書](./design-policy.md) - 今回の修正の設計判断
- [x] [アーキテクチャ概要](../../../docs/design/architecture-overview.md)
- [x] [環境変数管理](../../../docs/design/environment-variables.md)

**推奨参照**:
- [x] [開発ガイド](../../../DEVELOPMENT_GUIDE.md) - 品質基準

---

## 📊 Phase分解

### Phase 1: interface_definition.py修正（output_interface_id明示化） (0.5日)
**目的**: state内のinterface_definitions辞書に`input_interface_id`と`output_interface_id`を明示的に追加

**タスク**:
- [ ] 既存の`interface_definition.py`を読み取り（206-211行目を確認）
- [ ] `interface_masters[task_id]`辞書に以下のキーを追加:
  ```python
  interface_masters[task_id] = {
      "interface_master_id": interface_master["id"],  # 既存
      "input_interface_id": interface_master["id"],   # 追加（明示化）
      "output_interface_id": interface_master["id"],  # 追加（明示化）
      "interface_name": interface_name,               # 既存
      "input_schema": interface_def.input_schema,     # 既存
      "output_schema": interface_def.output_schema,   # 既存
  }
  ```
- [ ] ログ出力を追加:
  ```python
  logger.debug(
      f"Interface definition for task {task_id}:\n"
      f"  input_interface_id: {interface_master['id']}\n"
      f"  output_interface_id: {interface_master['id']}"
  )
  ```
- [ ] Ruff linting + MyPy type checking 実行
- [ ] 単体テストの実行（既存テストが影響を受けないか確認）

**成果物**:
- `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/nodes/interface_definition.py` (修正版)

**完了条件**:
- `interface_masters`辞書に`input_interface_id`と`output_interface_id`が追加される
- ログに詳細情報が出力される
- Ruff・MyPyエラーなし
- 既存単体テストが合格

---

### Phase 2: master_creation.py修正（タスク連鎖ロジック追加） (1.0日)
**目的**: 前タスクのoutput_interface_idを次タスクのinput_interface_idとして連鎖させる

**タスク**:
- [ ] 既存の`master_creation.py`を読み取り（66-114行目を確認）
- [ ] タスク連鎖ロジックを実装:
  ```python
  # Step 1: TaskMasters作成前にソート（priority順）
  sorted_task_ids = sorted(task_breakdown, key=lambda t: t.get("priority", 5))
  
  # Step 2: prev_output_interface_id変数を初期化
  prev_output_interface_id = None
  
  # Step 3: ソート済みタスクをループ
  for order, task in enumerate(sorted_task_ids):
      task_id = task["task_id"]
      interface_def = interface_definitions[task_id]
      
      if order == 0:
          # 最初のタスク: 独自のinput/outputを使用
          input_interface_id = interface_def["input_interface_id"]
          output_interface_id = interface_def["output_interface_id"]
      else:
          # 2番目以降: 前タスクのoutputを引き継ぐ
          input_interface_id = prev_output_interface_id
          output_interface_id = interface_def["output_interface_id"]
      
      # TaskMaster作成
      task_master = await matcher.find_or_create_task_master(
          name=task["name"],
          description=task["description"],
          method="POST",
          url=task_url,
          input_interface_id=input_interface_id,
          output_interface_id=output_interface_id,
          timeout_sec=60,
      )
      
      # 次のタスクのために保存
      prev_output_interface_id = output_interface_id
      
      logger.info(
          f"TaskMaster created for task {task_id} (order={order}):\n"
          f"  input_interface_id: {input_interface_id}\n"
          f"  output_interface_id: {output_interface_id}\n"
          f"  prev_output_interface_id → next_input_interface_id"
      )
  ```
- [ ] 既存のTaskMaster作成ロジック（86-114行目）を上記ロジックに置き換え
- [ ] ログ出力の充実（タスク連鎖の詳細を記録）
- [ ] Ruff linting + MyPy type checking 実行

**成果物**:
- `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/nodes/master_creation.py` (修正版)

**完了条件**:
- タスク連鎖ロジックが実装される
- 隣接タスク間でinterface IDが一致する
- ログにタスク連鎖の詳細が出力される
- Ruff・MyPyエラーなし

---

### Phase 3: 結合テスト追加・実行 (0.5日)
**目的**: タスク連鎖が正常に動作し、validation nodeでis_valid=Trueとなることを確認

**タスク**:
- [ ] `tests/integration/test_e2e_workflow.py`（または類似のE2Eテストファイル）を確認
- [ ] 3タスク連鎖のテストケースを追加:
  ```python
  @pytest.mark.asyncio
  async def test_job_generator_three_task_chain_validation():
      """Test that 3-task chain passes validation with interface chaining."""
      request_data = {
          "user_requirement": "Task1: データ取得 → Task2: データ処理 → Task3: レポート生成",
          "available_capabilities": [...],
      }
      
      # Job Generator実行
      response = await client.post("/v1/job-generator", json=request_data)
      
      # アサーション
      assert response.status_code == 200
      result = response.json()
      assert result["status"] == "success"
      assert "job_master_id" in result
      
      # interface連鎖の確認（ログから検証）
      # または、Jobqueueから取得したTaskMasterのinterface IDを検証
  ```
- [ ] テスト実行:
  ```bash
  cd expertAgent
  uv run pytest tests/integration/test_e2e_workflow.py::test_job_generator_three_task_chain_validation -v
  ```
- [ ] カバレッジ測定:
  ```bash
  uv run pytest tests/integration/ --cov=aiagent/langgraph/jobTaskGeneratorAgents/nodes --cov-report=term-missing
  ```

**成果物**:
- `expertAgent/tests/integration/test_e2e_workflow.py` (テスト追加版)

**完了条件**:
- 3タスク連鎖のテストケースが合格
- validation nodeでis_valid=Trueが確認される
- カバレッジ50%以上を維持

---

### Phase 4: 実ジョブでの検証 (0.5日)
**目的**: 実際のJob Generatorエンドポイントで修正が正常に動作することを確認

**タスク**:
- [ ] expertAgentサービスを起動:
  ```bash
  cd expertAgent
  uv run uvicorn app.main:app --host 0.0.0.0 --port 8104
  ```
- [ ] 実際のリクエストを送信（3タスク以上の複雑なワークフロー）:
  ```bash
  curl -s -X POST http://localhost:8104/aiagent-api/v1/job-generator \
    -H "Content-Type: application/json" \
    -d @./tests/fixtures/scenario_complex_workflow.json
  ```
- [ ] ログ出力を確認（`logs/expertagent.log`）:
  - `Validation result: is_valid=True` が出力されるか
  - interface_mismatch エラーが出なくなったか
  - タスク連鎖ロジックのログが正常か
  - リトライ回数が0または1回で収束するか
- [ ] 結果JSONを確認:
  - `status: "success"`
  - `job_master_id` と `job_id` が取得できるか
- [ ] ログからパフォーマンス情報を取得:
  - Job Generator全体の実行時間
  - master_creation nodeの実行時間
  - validation nodeの実行時間

**成果物**:
- テスト結果レポート（`phase-4-progress.md`に記載）

**完了条件**:
- `Validation result: is_valid=True` が確認される
- interface_mismatch エラーが発生しない
- リトライループが解消される

---

### Phase 5: 品質チェックとPR作成 (0.5日)
**目的**: 品質基準を満たし、PRを作成してレビューに提出

**タスク**:
- [ ] Pre-push チェックスクリプトを実行:
  ```bash
  cd expertAgent
  ./scripts/pre-push-check.sh
  ```
- [ ] 全チェック項目が合格することを確認:
  - Ruff linting エラーゼロ
  - Ruff formatting 適用済み
  - MyPy type checking エラーゼロ
  - 単体テストカバレッジ90%以上
  - 結合テストカバレッジ50%以上
- [ ] コミットメッセージをConventional Commits規約に準拠して作成:
  ```
  fix(jobgen): resolve validation loop with interface chaining
  
  - Add input_interface_id/output_interface_id to interface_definitions
  - Implement task chaining logic in master_creation node
  - Link adjacent tasks by connecting prev_output → next_input
  - Add comprehensive logging for interface ID transitions
  - Add E2E test for 3-task chain validation
  
  Fixes #111
  
  🤖 Generated with Claude Code
  Co-Authored-By: Claude <noreply@anthropic.com>
  ```
- [ ] PRを作成:
  ```bash
  gh pr create --base develop \
    --title "fix(jobgen): resolve validation loop with interface chaining (#111)" \
    --body "$(cat dev-reports/feature/issue/111/final-report.md)" \
    --label "fix,bug"
  ```
- [ ] CI/CDパイプラインが合格することを確認

**成果物**:
- Pull Request (#111)

**完了条件**:
- pre-push-check.sh 合格
- CI/CD パイプライン合格
- PRが作成され、レビュー待ち状態

---

### Phase 6: 最終報告書作成 (0.5日)
**目的**: 作業ドキュメントを完成させ、最終報告書を作成

**タスク**:
- [ ] `phase-1-progress.md` を作成（interface_definition.py修正の詳細）
- [ ] `phase-2-progress.md` を作成（master_creation.py修正の詳細）
- [ ] `phase-3-progress.md` を作成（結合テスト結果）
- [ ] `phase-4-progress.md` を作成（実ジョブ検証結果）
- [ ] `final-report.md` を作成:
  - 納品物一覧
  - 品質指標（カバレッジ、Linting結果）
  - 修正前後の比較（リトライ回数、実行時間）
  - 制約条件チェック結果（最終版）
  - 参考資料

**成果物**:
- `dev-reports/feature/issue/111/phase-*-progress.md` (全Phase分)
- `dev-reports/feature/issue/111/final-report.md`

**完了条件**:
- すべてのドキュメントが完備
- 制約条件チェックに合格

---

## ✅ 制約条件チェック結果

### コード品質原則
- [x] **SOLID原則**: 遵守予定
  - Single Responsibility: interface_definition（定義）、master_creation（生成・連鎖）で責務分離
  - Open-Closed: 既存のfind_or_create_task_masterメソッドを変更せず利用
  - Dependency Inversion: JobqueueClientを抽象化して依存性逆転
- [x] **KISS原則**: 遵守予定 / prev_output_interface_id変数でシンプルに実装
- [x] **YAGNI原則**: 遵守予定 / 必要最小限の修正のみ
- [x] **DRY原則**: 遵守予定 / 既存メソッドを再利用

### アーキテクチャガイドライン
- [x] `architecture-overview.md`: 準拠 / LangGraphノード構造を維持
- [x] レイヤー分離: nodes（ビジネスロジック）、utils（インフラ層）で分離

### 設定管理ルール
- [x] 環境変数: 遵守 / EXPERTAGENT_BASE_URLを使用
- [x] myVault: N/A（今回の修正では不要）

### 品質担保方針
- [ ] 単体テストカバレッジ: 90%以上を維持予定
- [ ] 結合テストカバレッジ: 50%以上を維持予定（Phase 3で確認）
- [ ] Ruff linting: エラーゼロ（各Phase完了時に確認）
- [ ] MyPy type checking: エラーゼロ（各Phase完了時に確認）

### CI/CD準拠
- [x] PRラベル: `fix`, `bug` を付与予定
- [x] コミットメッセージ: Conventional Commits規約に準拠予定
- [ ] pre-push-check.sh: Phase 5で実行予定

### 参照ドキュメント遵守
- [x] 設計方針書: 遵守（design-policy.md）
- [x] アーキテクチャ概要: 準拠
- [x] 環境変数管理: 準拠

### 違反・要検討項目
なし

---

## 📅 スケジュール

| Phase | 内容 | 開始予定 | 完了予定 | 工数 | 状態 |
|-------|------|---------|---------|------|------|
| Phase 1 | interface_definition.py修正 | 10/25 AM | 10/25 PM | 0.5日 | 予定 |
| Phase 2 | master_creation.py修正 | 10/25 PM | 10/26 AM | 1.0日 | 予定 |
| Phase 3 | 結合テスト追加・実行 | 10/26 AM | 10/26 PM | 0.5日 | 予定 |
| Phase 4 | 実ジョブでの検証 | 10/26 PM | 10/27 AM | 0.5日 | 予定 |
| Phase 5 | 品質チェックとPR作成 | 10/27 AM | 10/27 PM | 0.5日 | 予定 |
| Phase 6 | 最終報告書作成 | 10/27 PM | 10/27 PM | 0.5日 | 予定 |

**合計工数**: 3.5日
**完了予定**: 2025-10-27

---

## 🎯 リスク管理

### リスク1: タスク連鎖ロジックの実装ミス
**影響度**: 高
**対策**: 
- Phase 2で詳細なログ出力を追加
- Phase 3で結合テストを実施
- Phase 4で実ジョブでの検証を実施

### リスク2: 既存のJobqueueサービスとの互換性
**影響度**: 中
**対策**: 
- JobqueueのAPIは変更せず、expertAgent側のみ修正
- schema_matcherの厳密検索が既に実装済みなので、API互換性は維持される

### リスク3: パフォーマンス劣化
**影響度**: 低
**対策**: 
- タスク連鎖ロジックはO(n)の計算量（nはタスク数）
- 実ジョブ検証でパフォーマンスを測定（Phase 4）

### リスク4: ログ出力量の増加
**影響度**: 低
**対策**: 
- INFOレベルでサマリーのみ記録
- 詳細はDEBUGレベル

---

## 📝 メモ

### 技術的検討事項
- **schema_matcher.pyは修正不要**: 既に`find_task_master_by_name_url_and_interfaces`メソッドが実装済み
- **タスク連鎖の方向**: Task1 output → Task2 input → Task2 output → Task3 input
- **最初のタスクのinput**: 独自のinput_interface_idを使用（外部からの入力を想定）
- **最後のタスクのoutput**: 独自のoutput_interface_idを使用（外部への出力を想定）

### 今後の拡張可能性
- **並列タスク対応**: 現在は直列タスクのみ対応、将来的に並列タスクも対応予定
- **条件分岐対応**: 条件によってタスクフローが変わる場合の対応（Phase 10以降）
- **インターフェース互換性チェック**: 前タスクのoutput schemaと次タスクのinput schemaの整合性チェック（将来的に検討）

---

**次ステップ**: Phase 1の実装開始（ユーザー承認後）

# 作業計画: TaskMaster 再利用ロジックの厳密化

**作成日**: 2025-10-24
**予定工数**: 0.5人日
**完了予定**: 2025-10-24

---

## 📚 参考ドキュメント

**必須参照**:
- [x] [設計方針: TaskMaster 再利用ロジックの厳密化](./taskmaster-reuse-fix-design-policy.md)

**推奨参照**:
- [x] [アーキテクチャ概要](../../../docs/design/architecture-overview.md)
- [x] [CLAUDE.md](../../../CLAUDE.md)

---

## 📊 Phase分解

### Phase 1: コード修正と影響範囲確認 (1時間)

#### タスク 1.1: 既存コードの影響範囲確認
- [ ] `find_task_master_by_name_and_url` の使用箇所を Grep で検索
- [ ] 後方互換性のリスクを評価

#### タスク 1.2: schema_matcher.py の修正
- [ ] 新規メソッド `find_task_master_by_name_url_and_interfaces` を追加
- [ ] 既存メソッド `find_or_create_task_master` を修正
- [ ] ログ出力を追加（再利用時/新規作成時）

#### タスク 1.3: 静的解析チェック
- [ ] `uv run ruff check` でエラーゼロを確認
- [ ] `uv run ruff format` でフォーマット適用
- [ ] `uv run mypy` で型エラーゼロを確認

---

### Phase 2: 単体テスト追加 (1時間)

#### タスク 2.1: テストファイル作成
- [ ] `tests/unit/test_schema_matcher_strict.py` を作成
- [ ] 既存の `test_schema_matcher.py` があれば確認して統合

#### タスク 2.2: テストケース実装
- [ ] **ケース1**: 完全一致する TaskMaster の再利用
  - name, URL, input_interface_id, output_interface_id がすべて一致
  - 期待: 既存 TaskMaster を返す
- [ ] **ケース2**: interface_id が異なる場合の新規作成
  - name と URL は一致するが、interface_id が異なる
  - 期待: 新規 TaskMaster を作成
- [ ] **ケース3**: 検索エラー時のフォールバック
  - API エラー時に None を返すことを確認

#### タスク 2.3: カバレッジ確認
- [ ] `uv run pytest tests/unit/test_schema_matcher*.py --cov=aiagent/langgraph/jobTaskGeneratorAgents/utils/schema_matcher.py --cov-report=term-missing`
- [ ] 90%以上のカバレッジを確認

---

### Phase 3: E2E テストと検証 (30分)

#### タスク 3.1: E2E ワークフローテスト実行
- [ ] `uv run pytest tests/integration/test_e2e_workflow.py -v -k test_complete_workflow_success`
- [ ] ログから interface_mismatch ループが発生しないことを確認

#### タスク 3.2: ログ分析
- [ ] `logs/expertagent.log` から以下を確認:
  - [ ] Validation が通過して master_creation 以降に進む
  - [ ] "Reusing existing TaskMaster" または "Creating new TaskMaster" のログ出力
  - [ ] interface_mismatch エラーが発生しない

#### タスク 3.3: 修正前後の比較
- [ ] 修正前: Validation → interface_definition の無限ループ
- [ ] 修正後: Validation → master_creation → job_registration の正常フロー

---

### Phase 4: ドキュメント作成とコミット (30分)

#### タスク 4.1: 最終報告書作成
- [ ] `taskmaster-reuse-fix-final-report.md` を作成
- [ ] テスト結果、カバレッジ、ログ分析結果をまとめる

#### タスク 4.2: 品質チェック
- [ ] `./scripts/pre-push-check-all.sh` を実行
- [ ] すべてのチェックが合格することを確認

#### タスク 4.3: コミット・プッシュ
- [ ] 変更ファイルを git add
- [ ] コミットメッセージ: `fix(schema_matcher): add interface ID validation to prevent reuse loops`
- [ ] プッシュして CI/CD が通過することを確認

---

## ✅ 制約条件チェック結果

### コード品質原則
- [x] SOLID原則: 遵守予定 / 新規メソッド追加で Open-Closed を維持
- [x] KISS原則: 遵守予定 / シンプルな完全一致検索
- [x] YAGNI原則: 遵守予定 / 必要最小限の修正
- [x] DRY原則: 遵守予定 / 検索ロジックをメソッドに抽出

### アーキテクチャガイドライン
- [x] architecture-overview.md: 準拠 / utils レイヤーの責務を維持

### 設定管理ルール
- [x] 環境変数: 変更なし
- [x] myVault: 変更なし

### 品質担保方針
- [x] 単体テストカバレッジ: 90%以上を維持予定
- [x] 結合テストカバレッジ: 既存テストで検証予定
- [x] Ruff linting: エラーゼロ予定
- [x] MyPy type checking: エラーゼロ予定

### CI/CD準拠
- [x] PRラベル: `fix` ラベルを付与予定
- [x] コミットメッセージ: 規約に準拠予定
- [x] pre-push-check-all.sh: 実行予定

### 違反・要検討項目
なし

---

## 📅 スケジュール

| Phase | 開始予定 | 完了予定 | 所要時間 | 状態 |
|-------|---------|---------|---------|------|
| Phase 1: コード修正と影響範囲確認 | 即時 | +1時間 | 1時間 | 予定 |
| Phase 2: 単体テスト追加 | +1時間 | +2時間 | 1時間 | 予定 |
| Phase 3: E2E テストと検証 | +2時間 | +2.5時間 | 30分 | 予定 |
| Phase 4: ドキュメント作成とコミット | +2.5時間 | +3時間 | 30分 | 予定 |

---

## 🎯 完了条件

### 必須条件
- [x] schema_matcher.py に interface_id 検証ロジックを追加
- [x] 単体テストで 90%以上のカバレッジを維持
- [x] E2E テストで interface_mismatch ループが発生しない
- [x] Ruff linting、MyPy エラーゼロ
- [x] pre-push-check-all.sh 合格

### 推奨条件
- [x] ログから再利用/新規作成の判断を追跡可能
- [x] 最終報告書で修正前後の挙動を比較

---

## 📝 備考

- 既存の `find_task_master_by_name_and_url` メソッドは削除せず、後方互換性を維持
- 新規メソッド `find_task_master_by_name_url_and_interfaces` を追加して、明示的に interface_id を検証
- ログ出力を追加して、デバッグ性を向上

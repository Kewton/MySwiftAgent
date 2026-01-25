# 作業計画: docs/design ディレクトリ最新化

**作成日**: 2025-10-19
**予定工数**: 2.5時間
**完了予定**: 2025-10-19

---

## 📚 参考ドキュメント

**必須参照** (該当する場合):
- [ ] [新プロジェクトセットアップ手順書](../../docs/procedures/NEW_PROJECT_SETUP.md) - 該当なし
- [ ] [GraphAI ワークフロー生成ルール](../../graphAiServer/docs/GRAPHAI_WORKFLOW_GENERATION_RULES.md) - 該当なし

**推奨参照**:
- [x] [アーキテクチャ概要](../../docs/design/architecture-overview.md) - 更新対象
- [x] [環境変数管理](../../docs/design/environment-variables.md) - 更新対象
- [x] [myVault連携](../../docs/design/myvault-integration.md) - 更新対象
- [x] [開発ガイドライン](../../CLAUDE.md) - 制約条件チェック用
- [x] [README.md](../../README.md) - 整合性確認用

---

## 📊 Phase分解

### Phase 1: architecture-overview.md の検証・更新 (30分)

**作業内容**:
- [ ] README.md, docker-compose.yml とのクロスチェック
- [ ] プロジェクト一覧の確認
  - 現在: JobQueue, MyScheduler, MyVault, ExpertAgent, GraphAiServer, CommonUI
  - 追加確認: Docs プロジェクトの記載有無
- [ ] ポート設定の検証
  - Docker Compose: 8001-8005, 8501
  - quick-start.sh: 8101-8105, 8601
- [ ] サービス依存関係の確認
- [ ] 環境変数設定の検証
- [ ] 起動モード説明の確認
- [ ] 最終更新日を 2025-10-19 に変更
- [ ] phase-1-progress.md 作成

**検証方法**:
```bash
# docker-compose.ymlのサービス一覧確認
cat docker-compose.yml | grep -E "^  [a-z]" | sed 's/:$//' | sort

# ポート設定確認
grep -E "ports:" docker-compose.yml -A 1

# quick-start.shのポート確認
grep -E "PORT=" scripts/quick-start.sh
```

**完了条件**:
- ✅ 全検証項目をクリア
- ✅ README.mdとの整合性確認完了
- ✅ 最終更新日の変更完了
- ✅ phase-1-progress.md 作成完了

---

### Phase 2: environment-variables.md の検証・更新 (30分)

**作業内容**:
- [ ] 各プロジェクトの .env 設定例の検証
  - jobqueue/.env
  - myscheduler/.env
  - myVault/.env
  - expertAgent/.env
  - graphAiServer/.env
  - commonUI/.env
- [ ] MyVault統合の環境変数確認
- [ ] ポート設定の検証（Docker / dev-start / quick-start）
- [ ] トークン生成方法の確認
- [ ] 起動スクリプトとの整合性確認
- [ ] 最終更新日を 2025-10-19 に変更
- [ ] phase-2-progress.md 作成

**検証方法**:
```bash
# 各プロジェクトの .env.example 確認
for project in jobqueue myscheduler myVault expertAgent graphAiServer commonUI; do
  echo "=== $project ==="
  [ -f "$project/.env.example" ] && cat "$project/.env.example" || echo "No .env.example"
  echo
done

# MyVault環境変数確認
grep -E "MYVAULT_" expertAgent/.env.example
```

**完了条件**:
- ✅ 全プロジェクトの .env 設定例を検証
- ✅ 実際の設定ファイルとの整合性確認完了
- ✅ 最終更新日の変更完了
- ✅ phase-2-progress.md 作成完了

---

### Phase 3: myvault-integration.md の検証・更新 (30分)

**作業内容**:
- [ ] 必須パラメータ（環境変数）の検証
- [ ] RBACポリシー例の確認
- [ ] ポート構成の検証
  - Docker Compose: 8003
  - quick-start.sh: 8103
- [ ] 統合実装手順の確認
- [ ] 統合サービス一覧の最新化
  - 現在: ExpertAgent, GraphAiServer, CommonUI
  - 追加確認: 他のサービスの統合状況
- [ ] 最終更新日を 2025-10-19 に変更
- [ ] phase-3-progress.md 作成

**検証方法**:
```bash
# MyVault設定ファイル確認
cat myVault/config.yaml

# サービストークン確認
grep -E "TOKEN_" myVault/.env.example

# ポート設定確認
grep -E "MYVAULT.*PORT" scripts/quick-start.sh
```

**完了条件**:
- ✅ 全検証項目をクリア
- ✅ myVault/config.yaml との整合性確認完了
- ✅ 最終更新日の変更完了
- ✅ phase-3-progress.md 作成完了

---

### 最終報告: final-report.md 作成 (15分)

**作業内容**:
- [ ] 全Phase の作業内容まとめ
- [ ] 品質指標の確認
- [ ] 納品物一覧の作成
- [ ] 制約条件チェック（最終）
- [ ] final-report.md 作成

**完了条件**:
- ✅ final-report.md 作成完了
- ✅ 全制約条件チェックをクリア

---

## ✅ 制約条件チェック結果

### コード品質原則
- [x] **SOLID原則**: 該当なし（ドキュメント更新のみ）
- [x] **KISS原則**: 遵守 / 最小限の更新で目的達成
- [x] **YAGNI原則**: 遵守 / 不要な新規ドキュメント作成を回避
- [x] **DRY原則**: 遵守 / CLAUDE.mdとの重複を最小化

### アーキテクチャガイドライン
- [x] **architecture-overview.md**: 準拠 / ドキュメント自体を更新
- [x] **レイヤー分離**: 該当なし（ドキュメント更新のみ）

### 設定管理ルール
- [x] **環境変数**: 遵守 / environment-variables.mdの内容を検証・更新
- [x] **myVault**: 遵守 / myvault-integration.mdの内容を検証・更新

### 品質担保方針
- [x] **単体テストカバレッジ**: 該当なし（ドキュメント更新のみ）
- [x] **結合テストカバレッジ**: 該当なし（ドキュメント更新のみ）
- [x] **Ruff linting**: 該当なし（Markdownファイルのみ）
- [x] **MyPy type checking**: 該当なし（Markdownファイルのみ）

### CI/CD準拠
- [x] **PRラベル**: `docs` ラベルを付与予定（patch bump判定）
- [x] **コミットメッセージ**: 規約に準拠
  - `docs(design): update architecture-overview to latest project structure`
  - `docs(design): update environment-variables to latest configuration`
  - `docs(design): update myvault-integration to latest integration status`
- [ ] **pre-push-check-all.sh**: ドキュメント更新のみのため実行不要

### 参照ドキュメント遵守
- [x] **新プロジェクト追加時**: 該当なし（既存ドキュメント更新のみ）
- [x] **GraphAI ワークフロー開発時**: 該当なし

### 違反・要検討項目
なし

---

## 📅 スケジュール

| Phase | 開始予定 | 完了予定 | 状態 |
|-------|---------|---------|------|
| 準備 | 10/19 10:00 | 10/19 10:30 | ✅ 完了 |
| 計画 | 10/19 10:30 | 10/19 10:45 | 🔄 進行中 |
| Phase 1 | 10/19 10:45 | 10/19 11:15 | ⏳ 予定 |
| Phase 2 | 10/19 11:15 | 10/19 11:45 | ⏳ 予定 |
| Phase 3 | 10/19 11:45 | 10/19 12:15 | ⏳ 予定 |
| 報告 | 10/19 12:15 | 10/19 12:30 | ⏳ 予定 |

**総所要時間**: 約2.5時間
**完了予定**: 2025-10-19 12:30

---

## 🎯 作業の進め方

### 各Phaseでの作業フロー

1. **検証ツールを使用した自動確認**
   ```bash
   # 設定ファイルの確認
   cat docker-compose.yml
   cat scripts/quick-start.sh
   ls -la */。env.example
   ```

2. **ドキュメントの更新**
   - Edit ツールを使用して該当箇所を修正
   - 最終更新日を変更

3. **整合性確認**
   - README.md との比較
   - 実際の設定ファイルとの比較

4. **phase-{N}-progress.md の作成**
   - 作業内容の記録
   - 発生した課題の記録
   - 決定事項の記録

5. **制約条件チェック**
   - 各Phase完了時に実施

---

## 🚀 納品物

### 更新ドキュメント
- ✅ `./docs/design/architecture-overview.md`
- ✅ `./docs/design/environment-variables.md`
- ✅ `./docs/design/myvault-integration.md`

### 作業ドキュメント
- ✅ `./dev-reports/feature/issue/104/design-policy.md`
- ✅ `./dev-reports/feature/issue/104/work-plan.md`
- ⏳ `./dev-reports/feature/issue/104/phase-1-progress.md`
- ⏳ `./dev-reports/feature/issue/104/phase-2-progress.md`
- ⏳ `./dev-reports/feature/issue/104/phase-3-progress.md`
- ⏳ `./dev-reports/feature/issue/104/final-report.md`

---

## 📝 備考

### 作業中の注意事項

1. **最終更新日の統一**: 全ドキュメントで 2025-10-19 に統一する
2. **README.mdとの整合性**: ポート番号・サービス一覧は必ずREADME.mdと一致させる
3. **実ファイルとの確認**: 環境変数設定は実際の .env.example と比較する
4. **制約条件チェック**: 各Phase完了時に必ず実施する

### 今後の展開

本作業完了後、必要に応じて以下を別issueで対応：
- **ci-cd-pipeline.md**: GitHub Actionsワークフロー詳細
- **development-workflow.md**: 作業ドキュメント管理・ブランチ戦略詳細
- **branch-strategy.md**: ブランチ構成・マージフロー

---

**作業計画作成完了。Phase 1 の作業を開始します。**

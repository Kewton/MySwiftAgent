# 作業計画: 開発ルール改善とClaude Code Skill導入

**作成日**: 2025-11-05
**予定工数**: 2人日
**完了予定**: 2025-11-06

---

## 📚 参考ドキュメント

**必須参照**:
- [x] 現行CLAUDE.md（更新対象）
- [x] 新アジャイル開発ルール（要求仕様）

**推奨参照**:
- [x] [アーキテクチャ概要](../../docs/design/architecture-overview.md)
- [ ] Claude Code公式ドキュメント（スキル実装）

---

## 📊 Phase分解

### Phase 1: 開発ルール統合 (0.5日)
**目的**: CLAUDE.mdへの新開発ルール反映

- [ ] 現行CLAUDE.mdのバックアップ作成
- [ ] アジャイル開発セクション追加
  - [ ] Feature管理ルール
  - [ ] Issue分割戦略
  - [ ] ブランチ・PR戦略
  - [ ] フィーチャーフラグ管理
  - [ ] Wiki運用ルール
- [ ] 既存セクションとの整合性確認
- [ ] ドキュメントフォーマット統一

### Phase 2: Claude Code Skill実装 (1日)
**目的**: 6種類のスキル定義と実装

#### スキル作成タスク
- [ ] ディレクトリ構造作成 (.claude/skills/)
- [ ] 要件定義スキル (requirements.md)
  - [ ] プロンプトテンプレート作成
  - [ ] Opus モデル指定
  - [ ] ユーザーストーリー生成ロジック
- [ ] 設計方針作成スキル (design-policy.md)
  - [ ] 技術選定支援プロンプト
  - [ ] アーキテクチャ図生成指示
- [ ] 作業計画立案スキル (work-plan.md)
  - [ ] Phase分割ロジック
  - [ ] 工数見積もりテンプレート
- [ ] アーキテクチャレビュースキル (architecture-review.md)
  - [ ] レビューチェックリスト
  - [ ] 既存設計との整合性確認
- [ ] 進捗報告スキル (progress-report.md)
  - [ ] Sonnet モデル指定
  - [ ] 定型報告フォーマット
- [ ] リファクタリングスキル (refactoring.md)
  - [ ] Codex CLI統合設定
  - [ ] コード品質チェック項目

### Phase 3: ドキュメント整備・検証 (0.5日)
**目的**: 完成度確認と品質保証

- [ ] CLAUDE.md最終確認
  - [ ] スキル使用方法セクション追加
  - [ ] サンプルコマンド記載
  - [ ] トラブルシューティング追加
- [ ] スキル動作検証
  - [ ] 各スキルの単体テスト
  - [ ] エンドツーエンドシナリオテスト
- [ ] Wiki基本構造セットアップ
  - [ ] _Sidebar.md作成
  - [ ] 初期ページ構成
- [ ] 品質チェック実行
  - [ ] Markdownフォーマット確認
  - [ ] リンク整合性チェック

---

## ✅ 制約条件チェック結果

### コード品質原則
- [x] SOLID原則: 遵守 / モジュール設計
- [x] KISS原則: 遵守 / 必要最小限の実装
- [x] YAGNI原則: 遵守 / 段階的機能追加
- [x] DRY原則: 遵守 / テンプレート再利用

### アーキテクチャガイドライン
- [x] architecture-overview.md: 準拠
- [x] Claude Code標準機能活用

### 設定管理ルール
- [x] 環境変数: N/A（スキル定義は静的）
- [x] myVault: N/A（機密情報なし）

### 品質担保方針
- [x] ドキュメント品質: レビュー実施予定
- [x] 動作確認: 各スキルテスト実施

### CI/CD準拠
- [x] PRラベル: feature ラベル付与予定
- [x] コミットメッセージ: 規約準拠

### 参照ドキュメント遵守
- [x] 設計方針書作成済み
- [x] 作業計画書作成中

### 違反・要検討項目
なし

---

## 📅 スケジュール

| Phase | 開始予定 | 完了予定 | 状態 | 備考 |
|-------|---------|---------|------|------|
| Phase 1: 開発ルール統合 | 11/05 14:00 | 11/05 18:00 | 予定 | CLAUDE.md更新 |
| Phase 2: Skill実装 | 11/05 18:00 | 11/06 12:00 | 予定 | 6スキル作成 |
| Phase 3: 検証・整備 | 11/06 12:00 | 11/06 16:00 | 予定 | 品質確認 |

---

## 🎯 成果物

### 更新ファイル
1. **CLAUDE.md** - アジャイル開発ルール追加、スキル使用方法追加
2. **docs/procedures/AGILE_WORKFLOW.md** - 詳細ワークフロー

### 新規作成ファイル
1. **.claude/skills/** ディレクトリ
   - requirements.md
   - design-policy.md
   - work-plan.md
   - architecture-review.md
   - progress-report.md
   - refactoring.md

2. **.claude/commands/**
   - skill-help.md（スキルヘルプコマンド）

3. **GitHub Wiki初期構成**
   - _Sidebar.md
   - Home.md
   - Development-Process.md

---

## 📝 実装詳細仕様

### スキル実装仕様

#### 1. 要件定義スキル
```yaml
name: requirements
model: opus
trigger: "/requirements" または "要件定義を作成"
input:
  - feature_description: Feature概要
  - user_context: ユーザー背景
output:
  - user_story: As a... I want... So that...形式
  - acceptance_criteria: 受け入れ条件
  - technical_requirements: 技術要件
```

#### 2. 設計方針作成スキル
```yaml
name: design-policy
model: opus
trigger: "/design" または "設計方針を作成"
input:
  - requirements: 要件定義
  - constraints: 制約条件
output:
  - architecture: アーキテクチャ図
  - technology_stack: 技術選定
  - design_decisions: 設計判断
```

#### 3. 作業計画立案スキル
```yaml
name: work-plan
model: opus
trigger: "/plan" または "作業計画を立案"
input:
  - feature: Feature内容
  - design: 設計方針
output:
  - issue_list: Issue分割案
  - dependencies: 依存関係
  - schedule: スケジュール
```

#### 4. アーキテクチャレビュースキル
```yaml
name: architecture-review
model: opus
trigger: "/review-arch" または "アーキテクチャをレビュー"
input:
  - design_document: 設計書
  - existing_architecture: 既存構成
output:
  - review_comments: レビューコメント
  - risks: リスク評価
  - recommendations: 推奨事項
```

#### 5. 進捗報告スキル
```yaml
name: progress-report
model: sonnet
trigger: "/progress" または "進捗を報告"
input:
  - completed_tasks: 完了タスク
  - pending_tasks: 残タスク
output:
  - summary: 進捗サマリ
  - blockers: ブロッカー
  - next_steps: 次のステップ
```

#### 6. リファクタリングスキル
```yaml
name: refactoring
model: sonnet
trigger: "/refactor" または "リファクタリングを実施"
tools:
  - codex_cli: MCP経由でCodex CLI使用
input:
  - target_code: 対象コード
  - quality_issues: 品質課題
output:
  - refactored_code: リファクタ済みコード
  - improvements: 改善点
  - test_coverage: テストカバレッジ
```

---

## 🚨 リスクと対策

| リスク | 影響度 | 発生確率 | 対策 |
|-------|-------|---------|------|
| 既存ルールとの競合 | 高 | 低 | 段階的統合、互換性維持 |
| スキル動作不良 | 中 | 中 | 十分なテスト、フォールバック |
| チーム習熟度 | 中 | 高 | ドキュメント充実、サンプル提供 |

---

## 📌 特記事項

1. **優先順位**: 開発ルール統合 > スキル基本実装 > 細部調整
2. **互換性**: 既存プロジェクトへの影響最小化を最優先
3. **拡張性**: 将来的なスキル追加を考慮した設計
4. **段階リリース**: まず基本機能、その後高度な機能を追加
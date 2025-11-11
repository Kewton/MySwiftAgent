# Claude Code Skills ヘルプ

## 利用可能なスキル一覧（13種類）

### 開発プロセススキル

#### 1. 要件定義 (`/requirements`)
**用途**: ユーザーストーリー、受入条件、技術要件を生成
**モデル**: Opus
**フェーズ**: 1. Feature定義（メインセッション）
**使用例**:
```
/requirements プロフィール画像アップロード機能
```

#### 2. 設計方針 (`/design-policy`)
**用途**: アーキテクチャ設計、技術選定、設計判断を支援
**モデル**: Opus
**フェーズ**: 2. 仕様ドラフト（メインセッション）
**使用例**:
```
/design-policy 認証システムの設計
```

#### 3. アーキテクチャレビュー (`/architecture-review`)
**用途**: 設計レビュー、リスク評価、改善提案
**モデル**: Opus
**フェーズ**: 3. レビュー・承認（メインセッション） / 12. コードレビュー（worktreeセッション）
**使用例**:
```
/architecture-review [設計書を添付]
```

#### 4. Issue分割 (`/issue-split`)
**用途**: FeatureをIssueに分割、依存関係整理
**モデル**: Opus
**フェーズ**: 4. Issue分割（メインセッション）
**使用例**:
```
/issue-split ユーザー管理機能
```

#### 5. 作業計画 (`/work-plan`)
**用途**: Issue単位の具体的な作業計画立案
**モデル**: Opus
**フェーズ**: 5. 作業計画（メインセッション）
**使用例**:
```
/work-plan Issue #123
```

### 実装支援スキル

#### 6. 受入テスト (`/acceptance-test`)
**用途**: BDD形式の受入テストシナリオ作成
**モデル**: Sonnet
**フェーズ**: 6. テスト作成（worktreeセッション）
**使用例**:
```
/acceptance-test ユーザーログイン機能
```

#### 7. TDD実装 (`/tdd-impl`)
**用途**: テスト駆動開発でコード実装
**モデル**: Sonnet
**フェーズ**: 7. TDD実装（worktreeセッション）
**使用例**:
```
/tdd-impl UserService.authenticate
```

#### 8. リファクタリング (`/refactoring`)
**用途**: コード品質改善、設計パターン適用、技術的負債解消
**モデル**: Sonnet + Codex CLI
**フェーズ**: 9. リファクタリング（worktreeセッション、必要時）
**使用例**:
```
/refactoring [対象コード]
```

### 環境設定スキル

#### 9. Worktreeセットアップ (`/worktree-setup`)
**用途**: git worktreeの作成と環境設定
**モデル**: Haiku
**フェーズ**: worktree作成時
**使用例**:
```
/worktree-setup issue/123-user-auth
```

### 進捗管理スキル

#### 10. 進捗報告 (`/progress-report`)
**用途**: 進捗サマリ作成、ブロッカー報告、次ステップ明確化
**モデル**: Sonnet
**フェーズ**: 10. 進捗管理（worktreeセッション）
**使用例**:
```
/progress-report
```

### 自動化スキル

#### 11. PM自動開発 (`/pm-auto-dev`)
**用途**: プロダクトマネージャーとして自動開発を実行
**モデル**: Opus + Sonnet
**フェーズ**: 自動化フロー
**使用例**:
```
/pm-auto-dev Issue #123
```

#### 12. PR作成 (`/pm-create-pr`)
**用途**: プルリクエストの自動作成とドラフト生成
**モデル**: Sonnet
**フェーズ**: 11. PR作成（worktreeセッション）
**使用例**:
```
/pm-create-pr feat: ユーザー認証機能
```

### UIデザインスキル

#### 13. UIモックアップ (`/ui-mockup`)
**用途**: HTMLモックアップを生成
**モデル**: Sonnet
**フェーズ**: UIデザイン段階
**使用例**:
```
/ui-mockup ログイン画面
```

## スキルの実行方法

### 方法1: スラッシュコマンド
```
/[スキル名] [パラメータ]
```

### 方法2: 自然言語
```
「[機能名]の要件定義を作成してください」
「この設計をレビューしてください」
「リファクタリングを実施してください」
```

## スキルの組み合わせ例

### 新機能開発フロー（セッション切り替えあり）

#### メインセッション（developブランチ）
1. `/requirements` - 要件定義作成
2. `/design` - 設計方針策定
3. `/review-arch` - 設計レビュー
4. `/issue-split` - Issueに分割
5. `/plan` - Issue単位の作業計画立案

#### 🔄 セッション切替（git worktree作成）

#### worktreeセッション（issueブランチ）
6. 開発実装（手動）
7. テスト作成（手動）
8. `/refactor` - コード改善（必要時）
9. `/progress` - 進捗報告（定期）
10. PR作成（手動）
11. `/review-arch` - コードレビュー（必要時）

#### 🔄 セッション戻し（メインに戻る）

#### メインセッション（developブランチ）
12. フィーチャーフラグ設定（手動）
13. Wiki文書化（手動）

## カスタマイズ

スラッシュコマンド定義ファイルは `.claude/commands/` ディレクトリに配置されています：
- `requirements.md` - 要件定義コマンド
- `design-policy.md` - 設計方針コマンド
- `issue-split.md` - Issue分割コマンド
- `work-plan.md` - 作業計画コマンド
- `architecture-review.md` - レビューコマンド
- `progress-report.md` - 進捗報告コマンド
- `refactoring.md` - リファクタリングコマンド
- `acceptance-test.md` - 受入テストコマンド
- `tdd-impl.md` - TDD実装コマンド
- `worktree-setup.md` - Worktreeセットアップコマンド
- `pm-auto-dev.md` - PM自動開発コマンド
- `pm-create-pr.md` - PR作成コマンド
- `ui-mockup.md` - UIモックアップコマンド

各ファイルを編集することで、スラッシュコマンドの動作をカスタマイズできます。

## トラブルシューティング

### Q: スキルが実行されない
A: Claude Codeが最新バージョンか確認してください。

### Q: Opus/Sonnetモデルの切り替えは？
A: 各スキルで自動的に最適なモデルが選択されます。

### Q: Codex CLIが動作しない
A: MCP設定でCodex CLIが有効になっているか確認してください。

## 関連ドキュメント
- [CLAUDE.md](../../CLAUDE.md) - プロジェクト全体のガイドライン
- [AGILE_WORKFLOW.md](../../docs/procedures/AGILE_WORKFLOW.md) - アジャイル開発ワークフロー
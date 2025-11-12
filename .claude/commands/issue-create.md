---
title: "Issue一括作成"
description: "Issue分割計画書からGitHub Issueを一括作成し、親子関係を設定"
tags: ["issue", "github", "automation", "project-management"]
model: sonnet
---

# Issue一括作成スキル

## 概要
Issue分割計画書（`issue-split.md`）を解析し、GitHubにIssueを一括作成します。
親Issue（Feature）と子Issue（実装単位）の関連付けを自動で行い、進捗を可視化します。

## 使用方法
```bash
/issue-create <親Issue番号> [issue-split.mdのパス]
```

**例**:
```bash
/issue-create 152
/issue-create 152 dev-reports/feature/issue/152/issue-split.md
```

**引数**:
- `<親Issue番号>`: Feature Issue番号（必須）
- `[issue-split.mdのパス]`: Issue分割計画書のパス（省略時は自動検索）

## 実行内容

あなたはプロジェクトマネージャーです。Issue分割計画書から子Issueを一括作成し、親Issueと関連付けてください：

### 1. 事前確認

#### 親Issueの検証
```bash
gh issue view <親Issue番号>
```
- 親Issueが存在するか確認
- Feature Issueであることを確認（ラベルに "feature" が含まれる）
- 既に子Issueが作成済みでないか確認

#### issue-split.mdの検索
引数で指定されない場合、以下の優先順位で検索：
1. `dev-reports/feature/issue/<親Issue番号>/issue-split.md`
2. カレントディレクトリの `issue-split.md`
3. `dev-reports/**/issue-split.md`（最新のもの）

### 2. issue-split.mdの解析

#### 抽出する情報
- **Issue一覧セクション**:
  - Issue番号（例: #152-1）
  - タイトル
  - 概要
  - サイズ（S/M/L）
  - 優先度（High/Medium/Low）
  - 作業見積（時間）
  - 担当候補
  - スコープ
  - 技術スタック
  - 受入基準（2層構造）

- **Phase情報**:
  - Phase番号
  - Phase名
  - 各Issueの所属Phase
  - Phase完了条件

- **依存関係**:
  - 依存先Issue（ブロックされる側）
  - ブロック対象Issue（ブロックする側）
  - 並列実行可能性

### 3. 子Issueの一括作成

#### Issue作成ループ
各Issueについて以下を実行：

```bash
gh issue create \
  --title "Issue #<親Issue番号>-<連番>: <タイトル>" \
  --body "$(cat /tmp/issue-body-<連番>.md)" \
  --label "<サイズ>,<優先度>,feature,<Phase>" \
  --assignee "@me" \
  --project "MySwiftAgent" \
  --milestone "<Phase名>"
```

#### Issue本文のテンプレート
```markdown
**親Issue**: #<親Issue番号>
**Phase**: <Phase名>
**サイズ**: <サイズ> (<作業見積>)
**優先度**: <優先度>

## 概要
<概要>

## 依存関係
<依存先Issueのリスト>

## ブロック対象
<ブロックするIssueのリスト>

## スコープ
<スコープのチェックリスト>

## 技術スタック
<技術スタック>

## 受入基準 (Acceptance Criteria)

### 🤖 自動検証可能な基準（pm-auto-devが実施）

**機能要件**:
<機能要件のチェックリスト>

**品質基準**:
<品質基準のチェックリスト>

**テストケース**:
<テストケースのチェックリスト>

### 👤 手動検証が必要な基準（ユーザーが実施）

**UX/UI検証**:
<UX/UI検証のチェックリスト>

**ビジネスロジック検証**:
<ビジネスロジック検証のチェックリスト>

**運用検証**:
<運用検証のチェックリスト>

---

📄 **詳細**: [Issue分割計画書](<issue-split.mdへのリンク>)
```

### 4. 親Issueの更新

#### タスクリストの追加
親Issueの本文を更新し、子Issueのタスクリストを追加：

```bash
gh issue edit <親Issue番号> --body "$(cat /tmp/parent-issue-body.md)"
```

#### 親Issue本文のテンプレート
```markdown
<既存の本文>

---

## 子Issue進捗

### Phase 1: <Phase名>
- [ ] #<子Issue番号> Issue #<親Issue番号>-<連番>: <タイトル>（<見積>）
- [ ] #<子Issue番号> Issue #<親Issue番号>-<連番>: <タイトル>（<見積>）

### Phase 2: <Phase名>
- [ ] #<子Issue番号> Issue #<親Issue番号>-<連番>: <タイトル>（<見積>）
...

## 全体進捗
- **完了**: 0/<総Issue数> (0%)
- **作業中**: 0/<総Issue数>
- **未着手**: <総Issue数>/<総Issue数>

## マイルストーン
- Phase 1完了予定: <期限>
- Phase 2完了予定: <期限>
- 全体完了予定: <期限>

---

📄 **Issue分割計画書**: [issue-split.md](<リンク>)
```

### 5. 依存関係の設定

#### コメントによる依存関係の記録
各子Issueにコメントを追加：

```bash
# 依存先がある場合
gh issue comment <子Issue番号> --body "⚠️ **Blocked by**: #<依存先Issue番号>"

# ブロック対象がある場合
gh issue comment <依存先Issue番号> --body "🚧 **Blocks**: #<子Issue番号>"
```

### 6. issue-split.mdへのリンク追記

#### リンクセクションの追加
issue-split.mdの末尾に以下を追記：

```markdown
---

## 🔗 作成されたGitHub Issue

### 親Issue
- #<親Issue番号>: <Feature名>
  - URL: https://github.com/Kewton/MySwiftAgent/issues/<親Issue番号>

### 子Issue

#### Phase 1: <Phase名>
- #<子Issue番号>: Issue #<親Issue番号>-<連番>: <タイトル>
  - URL: https://github.com/Kewton/MySwiftAgent/issues/<子Issue番号>
  - サイズ: <サイズ>、優先度: <優先度>
...

### 作成日時
<作成日時>

### 作成者
@<GitHubユーザー名>
```

### 7. 結果サマリーの出力

#### コンソール出力
```
✅ 子Issueを一括作成しました

親Issue: #152 要件定義エージェントへのMLOps導入
  https://github.com/Kewton/MySwiftAgent/issues/152

作成された子Issue: 10個

Phase 1: 基盤構築（並列可）
  #201: Issue #152-1: Valkey永続化基盤の実装（3日）
    https://github.com/Kewton/MySwiftAgent/issues/201
    📌 並列実行可能: #202

  #202: Issue #152-8: プロンプトYAML化実装（2日）
    https://github.com/Kewton/MySwiftAgent/issues/202
    📌 並列実行可能: #201

Phase 2: コアAPI実装
  #203: Issue #152-2: 診断情報取得API実装（2日）
    https://github.com/Kewton/MySwiftAgent/issues/203
    ⚠️  Blocked by: #201

  #204: Issue #152-3: フィードバックAPI実装（1日）
    https://github.com/Kewton/MySwiftAgent/issues/204
    ⚠️  Blocked by: #201
    📌 並列実行可能: #203

  #205: Issue #152-4: 複数候補提示機能（3日）
    https://github.com/Kewton/MySwiftAgent/issues/205
    ⚠️  Blocked by: #202

Phase 3: AI機能拡張
  #206: Issue #152-5: AI推奨システム実装（2日）
    https://github.com/Kewton/MySwiftAgent/issues/206
    ⚠️  Blocked by: #205

Phase 4: 可視化・分析
  #207: Issue #152-6: 品質可視化API実装（2日）
    https://github.com/Kewton/MySwiftAgent/issues/207
    ⚠️  Blocked by: #203, #204

  #208: Issue #152-7: リアルタイムダッシュボード実装（2日）
    https://github.com/Kewton/MySwiftAgent/issues/208
    ⚠️  Blocked by: #207

Phase 5: ABテスト
  #209: Issue #152-9: ABテスト基盤実装（4日）
    https://github.com/Kewton/MySwiftAgent/issues/209
    ⚠️  Blocked by: #202, #207

Phase 6: UI統合
  #210: Issue #152-10: UI実装（5日）
    https://github.com/Kewton/MySwiftAgent/issues/210
    ⚠️  Blocked by: #203, #204, #205, #206, #207, #208

📊 統計情報
- 総Issue数: 10個
- 総見積工数: 216時間（約5週間）
- 並列実行可能: 3組（Phase 1: #201/#202、Phase 2: #203/#204）

📄 Issue分割計画書を更新しました
  dev-reports/feature/issue/152/issue-split.md

🎯 次のステップ
1. 親Issue（#152）で全体進捗を確認
2. Phase 1の並列実行可能Issue（#201, #202）から着手
3. 各Issueで /work-plan を実行して詳細作業計画を立案
```

## エラーハンドリング

### エラーケース

| エラー | 条件 | 対処 |
|--------|------|------|
| **親Issue不在** | 指定された親Issue番号が存在しない | エラーメッセージを表示し終了 |
| **非Feature Issue** | 親Issueに "feature" ラベルがない | 警告を表示し、続行するか確認 |
| **issue-split.md不在** | Issue分割計画書が見つからない | エラーメッセージを表示し終了 |
| **GitHub CLI未認証** | `gh auth status` が失敗 | 認証手順を案内 |
| **Issue作成失敗** | `gh issue create` がエラー | エラー詳細を表示し、ロールバック手順を案内 |
| **重複Issue検出** | 同じタイトルのIssueが既存 | 警告を表示し、続行するか確認 |

### ロールバック手順

Issue作成途中でエラーが発生した場合：

1. 作成済みの子Issueを列挙
2. 各Issueを削除するか確認
3. ユーザーが承認した場合のみ削除実行

```bash
# 作成済みIssueの削除（ユーザー確認後）
gh issue close <Issue番号> --comment "作成エラーのためクローズ"
```

## 注意事項

### 前提条件
- [x] GitHub CLIがインストール済み（`gh --version`）
- [x] GitHub認証が完了済み（`gh auth status`）
- [x] リポジトリへの書き込み権限がある
- [x] issue-split.mdが正しい形式である

### 制限事項
- 親Issueは事前に手動で作成しておく必要がある
- GitHub Projects連携は手動設定が必要（自動化は将来対応）
- マイルストーンは事前に作成しておく必要がある

### ベストプラクティス
- `/issue-split` 実行直後に `/issue-create` を実行
- 親Issueのテンプレートは事前に整備しておく
- Issue作成後は親Issueで全体進捗を確認
- 並列実行可能なIssueを優先的に着手

## 関連スキル

- `/issue-split`: Issue分割計画書の作成（本スキルの前提）
- `/work-plan`: 各Issue単位の詳細作業計画立案
- `/progress`: Issue進捗の報告

## 参照ドキュメント

- [開発ワークフロー](../../docs/claude/01-development-workflow.md)
- [Issue分割ガイド](../../docs/claude/08-issue-split.md)
- [GitHub CLI Documentation](https://cli.github.com/manual/)

---

**実行確認**: このスキルはGitHub APIに変更を加えます。実行前に内容を確認してください。

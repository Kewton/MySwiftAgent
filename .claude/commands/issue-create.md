---
title: "Issue一括作成"
description: "Issue分割計画書からGitHub Issueを一括作成し、親子関係を設定"
tags: ["issue", "github", "automation", "project-management"]
model: opus
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
  - Phaseの実行順序（Week情報）
  - 並列実行マーク（⚡）の有無

- **依存関係**:
  - 依存先Issue（ブロックされる側）
  - ブロック対象Issue（ブロックする側）
  - 並列実行可能性
  - 依存関係マトリクスからの情報

- **スケジュール情報**:
  - 総見積工数
  - 並列化による短縮効果
  - Phase別の週次スケジュール

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

## 📅 実装Phase計画と実行順序

本Featureは **<Phase数>つのPhase** に分割され、各Phaseに子Issueが割り当てられています。
Phase内で並列実行可能なIssueは同時着手できますが、Phase間には依存関係があります。

### Phase 1: <Phase名>（Week <週番号>） ⚡並列実行可能

**開始条件**: なし（即座に着手可能）

**実行順序**:
1. 📌 **並列着手**: <並列実行可能なIssue番号> を同時に開始可能

| Issue | タイトル | 見積 | 担当 | 依存 |
|-------|----------|------|------|------|
| #<子Issue番号> | Issue #<親Issue番号>-<連番>: <タイトル> | <見積> | <担当> | なし |
| #<子Issue番号> | Issue #<親Issue番号>-<連番>: <タイトル> | <見積> | <担当> | なし |

**Phase完了条件**:
- [ ] <完了条件1>
- [ ] <完了条件2>

**ブロック解除**: Phase 1完了で **Phase 2** の <Issue番号リスト> が着手可能

---

### Phase 2: <Phase名>（Week <週番号>） ⚡一部並列可

**開始条件**: <依存Issue番号> が完了

**実行順序**:
1. 📌 **並列着手**: <並列実行可能なIssue番号> を同時に開始可能
2. ⏩ **独立着手**: <Issue番号> は <依存Issue番号> 完了後に開始

| Issue | タイトル | 見積 | 担当 | 依存 |
|-------|----------|------|------|------|
| #<子Issue番号> | Issue #<親Issue番号>-<連番>: <タイトル> | <見積> | <担当> | #<依存Issue> ✅ |

**Phase完了条件**:
- [ ] `/pm-auto-dev <Issue番号リスト>` 完了（自動検証済み）
- [ ] <完了条件>

**ブロック解除**: <次Phase情報>

---

（各Phaseごとに同様の構造を繰り返す）

---

## 🔀 依存関係可視化

```mermaid
graph TD
    subgraph "Phase 1: <Phase名>（Week <週番号>）"
        I<子Issue番号>[#<子Issue番号> <タイトル短縮><br/><見積>]
        I<子Issue番号>[#<子Issue番号> <タイトル短縮><br/><見積>]
    end

    subgraph "Phase 2: <Phase名>（Week <週番号>）"
        I<子Issue番号>[#<子Issue番号> <タイトル短縮><br/><見積>]
    end

    %% 依存関係
    I<子Issue番号> --> I<子Issue番号>
    I<子Issue番号> --> I<子Issue番号>

    %% 並列実行可能なIssueのスタイル
    style I<子Issue番号> fill:#e3f2fd,stroke:#1976d2,stroke-width:3px
    style I<子Issue番号> fill:#e3f2fd,stroke:#1976d2,stroke-width:3px
```

**凡例**:
- 🟦 青枠太線: Phase 1 並列実行可能
- 🟧 橙枠太線: Phase 2 並列実行可能
- 矢印: 依存関係（元Issue完了後に先Issue着手可能）

---

## 📊 実行シミュレーション（最短スケジュール）

| Week | 並列作業 | 実行Issue | 作業日数 |
|------|---------|-----------|---------|
| Week 1 Day 1-<日数> | <並列数>名並列 | <Issue番号リスト> | <日数>日 |
| Week <週番号> Day <日数> | <並列数>名並列 | <Issue番号リスト> | <日数>日 |

**合計**: 約<営業日数>営業日（並列化により<元日数>日→<短縮日数>日に短縮）

---

## 🎯 推奨着手順序

### 🚀 今すぐ着手可能（Phase 1）
```bash
# 並列で<人数>名がそれぞれ着手
/work-plan <子Issue番号>  # <タイトル>（<見積>）
/work-plan <子Issue番号>  # <タイトル>（<見積>）
```

### ⏳ Phase 1完了待ち（Phase 2）
```bash
# <依存Issue番号>完了後、並列で着手可能
/work-plan <子Issue番号>  # <タイトル>（<見積>）
/work-plan <子Issue番号>  # <タイトル>（<見積>）

# <依存Issue番号>完了後、着手可能
/work-plan <子Issue番号>  # <タイトル>（<見積>）
```

### ⏳ Phase 2完了待ち（Phase 3以降）
```bash
# 順次実行
/work-plan <子Issue番号>  # <タイトル>（<依存条件>）
/work-plan <子Issue番号>  # <タイトル>（<依存条件>）
```

---

## 子Issue進捗

### Phase 1: <Phase名>
- [ ] #<子Issue番号> Issue #<親Issue番号>-<連番>: <タイトル>（<見積>）
- [ ] #<子Issue番号> Issue #<親Issue番号>-<連番>: <タイトル>（<見積>）

### Phase 2: <Phase名>
- [ ] #<子Issue番号> Issue #<親Issue番号>-<連番>: <タイトル>（<見積>）
...

---

## 全体進捗
- **完了**: 0/<総Issue数> (0%)
- **作業中**: 0/<総Issue数>
- **未着手**: <総Issue数>/<総Issue数>

**予定**: Week <開始週> 開始 → Week <完了週> 完了（約<週数>週間）

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
================================================================================
✅ 子Issueを一括作成しました
================================================================================

親Issue: #<親Issue番号> <Feature名>
  https://github.com/Kewton/MySwiftAgent/issues/<親Issue番号>

作成された子Issue: <総Issue数>個

--------------------------------------------------------------------------------
Phase 1: <Phase名>（並列可）
--------------------------------------------------------------------------------
  #<子Issue番号>: Issue #<親Issue番号>-<連番>: <タイトル>（<見積>）
    https://github.com/Kewton/MySwiftAgent/issues/<子Issue番号>
    📌 並列実行可能: #<子Issue番号>
    🚧 Blocks: #<子Issue番号>, #<子Issue番号>

  #<子Issue番号>: Issue #<親Issue番号>-<連番>: <タイトル>（<見積>）
    https://github.com/Kewton/MySwiftAgent/issues/<子Issue番号>
    📌 並列実行可能: #<子Issue番号>

--------------------------------------------------------------------------------
Phase 2: <Phase名>
--------------------------------------------------------------------------------
  #<子Issue番号>: Issue #<親Issue番号>-<連番>: <タイトル>（<見積>）
    https://github.com/Kewton/MySwiftAgent/issues/<子Issue番号>
    ⚠️  Blocked by: #<子Issue番号>
    📌 並列実行可能: #<子Issue番号>
    🚧 Blocks: #<子Issue番号>

  （各Phaseごとに同様の形式で出力）

================================================================================
📊 統計情報
================================================================================
- 総Issue数: <総Issue数>個
- 総見積工数: <総日数>日（約<週数>週間）
- 並列実行可能: <並列グループ数>組
  - Phase 1: #<子Issue番号> ⇄ #<子Issue番号>
  - Phase 2: #<子Issue番号> ⇄ #<子Issue番号>
- ブロック関係:
  - #<子Issue番号> → #<子Issue番号>, #<子Issue番号> (Phase 1完了でPhase 2開始可能)
  - #<子Issue番号> → #<子Issue番号> (<説明>)
  - #<子Issue番号> → #<子Issue番号> (<説明>)

================================================================================
📄 更新されたファイル
================================================================================
- 親Issue #<親Issue番号>: 実行順序・依存関係グラフ・子Issueタスクリスト追加
  https://github.com/Kewton/MySwiftAgent/issues/<親Issue番号>

- issue-split.md: GitHub Issueリンクセクション追加
  dev-reports/feature/issue/<親Issue番号>/issue-split.md

================================================================================
🎯 次のステップ
================================================================================
1. 親Issue（#<親Issue番号>）で全体進捗を確認
   https://github.com/Kewton/MySwiftAgent/issues/<親Issue番号>

2. Phase 1の並列実行可能Issueから着手
   - #<子Issue番号>: <タイトル>
   - #<子Issue番号>: <タイトル>

3. 各Issueで /work-plan を実行して詳細作業計画を立案
   例: /work-plan <子Issue番号>

4. /pm-auto-dev で自動開発・テスト実行
   例: /pm-auto-dev <子Issue番号>

================================================================================
✅ Issue一括作成が完了しました
================================================================================
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

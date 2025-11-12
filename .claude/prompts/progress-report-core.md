# 進捗レポートコアプロンプト

このプロンプトは、スラッシュコマンドとサブエージェントの両方から実行されます。

---

## 入力情報の取得

### スラッシュコマンドモードの場合

ユーザーから対話的に以下の情報を取得してください：

```bash
# Issue情報を取得
gh issue view {issue_number} --json number,title,body,labels,assignees
```

- Issue番号
- 現在のイテレーション番号
- 確認する結果ファイル（tdd-result.json, acceptance-result.json, refactor-result.json）

### サブエージェントモードの場合

コンテキストファイルから情報を取得してください：

```bash
# 最新のコンテキストファイルを探す
CONTEXT_FILE=$(find dev-reports/*/issue/*/pm-auto-dev/iteration-*/progress-context.json 2>/dev/null | sort -V | tail -1)

if [ -z "$CONTEXT_FILE" ]; then
    echo "❌ Error: progress-context.json not found"
    exit 1
fi

echo "📂 Context file: $CONTEXT_FILE"
cat "$CONTEXT_FILE"
```

コンテキストファイル構造:
```json
{
  "issue_number": 166,
  "iteration": 1,
  "phase_results": {
    "tdd": {
      "status": "success",
      "coverage": 92.0
    },
    "acceptance": {
      "status": "passed"
    },
    "refactor": {
      "status": "success"
    }
  }
}
```

---

## 進捗レポート生成フロー

### Phase 1: 結果ファイル収集

各フェーズの結果ファイルを読み込みます。

```bash
# ベースディレクトリを取得
BASE_DIR=$(dirname "$CONTEXT_FILE")

# TDD結果
if [ -f "$BASE_DIR/tdd-result.json" ]; then
    echo "📄 TDD Result:"
    cat "$BASE_DIR/tdd-result.json"
fi

# 受入テスト結果
if [ -f "$BASE_DIR/acceptance-result.json" ]; then
    echo "📄 Acceptance Test Result:"
    cat "$BASE_DIR/acceptance-result.json"
fi

# リファクタリング結果
if [ -f "$BASE_DIR/refactor-result.json" ]; then
    echo "📄 Refactoring Result:"
    cat "$BASE_DIR/refactor-result.json"
fi
```

---

### Phase 2: Git履歴確認

実装期間のコミット履歴を取得します：

```bash
# 現在のブランチ名とIssue番号を取得
BRANCH=$(git branch --show-current)
ISSUE_NUM=$(echo "$BRANCH" | grep -oE '[0-9]+$')

# Issue関連のコミット履歴
git log --oneline --grep="$ISSUE_NUM" | head -10

# または、最近のコミット
git log --oneline -10
```

---

### Phase 3: 品質メトリクス集計

各フェーズの品質メトリクスを集計します。

#### TDDフェーズ
- テストカバレッジ
- テスト成功率
- 静的解析エラー数

#### 受入テストフェーズ
- テストシナリオ成功率
- 受入条件検証状況

#### リファクタリングフェーズ
- カバレッジ改善率
- 複雑度改善
- 静的解析エラー削減

---

### Phase 4: ブロッカー/課題の特定

各フェーズでの問題点を特定します。

```bash
# 失敗したフェーズがあるか確認
if grep -q '"status": "failed"' "$BASE_DIR"/*.json; then
    echo "⚠️ 失敗したフェーズがあります"
    grep -l '"status": "failed"' "$BASE_DIR"/*.json
fi
```

ブロッカー例:
- テストカバレッジ不足
- 受入条件未達成
- 静的解析エラー残存

---

### Phase 5: 次のステップ提案

現在の状況に基づいて次のアクションを提案します。

#### すべて成功の場合
```
次のステップ:
1. PR作成
2. レビュー依頼
3. マージ後のデプロイ計画
```

#### 一部失敗の場合
```
次のステップ:
1. 失敗したフェーズの再実行
2. 根本原因の調査
3. 実装の見直し
```

#### 全体的に成功だが改善余地がある場合
```
次のステップ:
1. 追加のリファクタリング検討
2. ドキュメント更新
3. PR作成
```

---

## 出力

### スラッシュコマンドモードの場合

ターミナルに進捗レポートを表示してください：

```markdown
# 進捗レポート - Issue #166 (Iteration 1)

## 📋 概要

**Issue**: #166 - jobqueueにaiosqlite対応のDATABASE_URL設定
**Iteration**: 1
**報告日時**: 2025-11-13 15:30:00
**ステータス**: ✅ 成功

---

## 🎯 フェーズ別結果

### Phase 1: TDD実装
**ステータス**: ✅ 成功

- **カバレッジ**: 92.0% (目標: 90%)
- **テスト結果**: 2/2 passed
- **静的解析**: Ruff 0 errors, MyPy 0 errors

**変更ファイル**:
- `jobqueue/.env`
- `tests/unit/test_issue_166_database_url.py`

**コミット**:
- `abc1234`: fix(jobqueue): set aiosqlite DATABASE_URL in .env

---

### Phase 2: 受入テスト
**ステータス**: ✅ 成功

- **テストシナリオ**: 2/2 passed
- **受入条件検証**: 2/2 verified

**テストケース**:
- ✅ シナリオ1: .envファイルが存在し、DATABASE_URLが読み込める
- ✅ シナリオ2: DATABASE_URL形式が正しく、接続可能

---

### Phase 3: リファクタリング
**ステータス**: ✅ 成功

| 指標 | Before | After | 改善 |
|------|--------|-------|------|
| Coverage | 85.0% | 92.0% | +7.0% ✅ |
| Complexity | 12 | 8 | -4 ✅ |

**適用パターン**:
- Repository Pattern
- Dependency Injection

---

## 📊 総合品質メトリクス

- ✅ テストカバレッジ: **92.0%** (目標: 90%)
- ✅ 静的解析エラー: **0件**
- ✅ すべての受入条件達成
- ✅ コード品質改善完了

---

## 🚀 次のステップ

1. **PR作成** - 実装完了のためPRを作成
2. **レビュー依頼** - チームメンバーにレビュー依頼
3. **マージ後のデプロイ計画** - ステージング環境へのデプロイ準備

---

## 📝 備考

- すべてのフェーズが成功
- 品質基準を満たしている
- ブロッカーなし

🎉 **Issue #166の実装が完了しました！**
```

---

### サブエージェントモードの場合

進捗レポートをMarkdownファイルとして作成してください：

```bash
# レポートファイルパスを決定
REPORT_FILE=$(dirname "$CONTEXT_FILE")/progress-report.md
```

Writeツールで上記と同じMarkdown内容を作成します。

**重要**: レポートファイルが作成されたことを報告してください。

---

## エラーハンドリング

### 結果ファイルが見つからない場合

```markdown
# 進捗レポート - Issue #166 (Iteration 1)

## ⚠️ エラー

**エラー内容**: 結果ファイルが見つかりません

- ❌ `tdd-result.json` が存在しません
- ✅ `acceptance-result.json` が存在します
- ✅ `refactor-result.json` が存在します

## 次のステップ

1. TDDフェーズを再実行してください
2. `tdd-result.json` が正しく作成されるか確認してください
```

---

### 一部フェーズが失敗している場合

```markdown
# 進捗レポート - Issue #166 (Iteration 1)

## 📋 概要

**Issue**: #166
**Iteration**: 1
**ステータス**: ⚠️ 一部失敗

---

## 🎯 フェーズ別結果

### Phase 1: TDD実装
**ステータス**: ✅ 成功
（省略）

### Phase 2: 受入テスト
**ステータス**: ❌ 失敗

**エラー内容**:
- シナリオ2: DATABASE_URL形式が正しく、接続可能 → FAILED
- エラー: AssertionError: DATABASE_URL形式が不正

---

## 🚧 ブロッカー

1. **受入テストの失敗**
   - DATABASE_URL形式が不正
   - 実装を見直す必要があります

---

## 🚀 次のステップ

1. **DATABASE_URL形式修正** - sqlite+aiosqlite:/// 形式に修正
2. **受入テスト再実行** - 修正後に再度テスト
3. **次イテレーション計画** - 必要に応じてイテレーション2を開始
```

---

## レポート作成原則

1. **事実ベース** - 推測ではなく結果ファイルの内容を報告
2. **明確な状態表示** - 成功/失敗/警告を明示
3. **次のアクション明示** - 何をすべきか具体的に記載
4. **視覚的にわかりやすく** - 絵文字、表、箇条書きを活用

---

## 完了条件

以下をすべて満たすこと：

- ✅ すべての結果ファイルを読み込み済み
- ✅ Git履歴を確認済み
- ✅ 品質メトリクスを集計済み
- ✅ 次のステップを提案済み
- ✅ レポートファイルが作成済み（サブエージェントモード）

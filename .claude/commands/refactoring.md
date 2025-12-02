---
model: opus
description: "コード品質改善、設計パターン適用、技術的負債解消"
phase: "10. リファクタリング"
session: "worktree"
---

# リファクタリングスキル

## 概要
コード品質を改善し、SOLID原則に基づく設計パターンを適用して、技術的負債を解消するスキルです。

このスキルは**スラッシュコマンドモード**で動作します（ユーザーが直接実行）。

## 使用方法
- `/refactoring [対象ファイル/クラス]`
- 「[ファイル名]をリファクタリングしてください」
- 「Repository Patternを適用してください」

---

## 実行内容

**共通プロンプトを読み込んで実行します**:

```bash
cat .claude/prompts/refactoring-core.md
```

↑ **このプロンプトの内容に従って、リファクタリングを実行してください。**

---

## 動作モード

**スラッシュコマンドモード**:
- ユーザーから対話的に情報を取得
- リファクタリング対象、改善目標、適用パターンなどを確認
- コード品質分析を実行
- リファクタリングを段階的に適用
- 結果をターミナルに表示

---

## リファクタリング原則

- **SOLID**: Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, Dependency Inversion
- **KISS**: Keep It Simple, Stupid
- **DRY**: Don't Repeat Yourself
- **YAGNI**: You Aren't Gonna Need It

---

## 完了条件

以下をすべて満たすこと：
- ✅ すべてのテストが引き続き成功
- ✅ 品質メトリクスが改善（カバレッジ、複雑度）
- ✅ 静的解析エラーがゼロ
- ✅ コミットが完了

---

## 📝 Note

サブエージェントとして呼び出す場合は、PM Auto-Devが以下のように実行します：

```
Use refactoring-agent to improve code quality for Issue #166.
```

この場合、`.claude/agents/refactoring-agent.md` が使用されます（本ファイルは使用されません）。

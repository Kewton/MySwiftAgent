---
model: opus
description: "Issue要件に基づく自動受入テスト実行"
phase: "9. テスト（受入テスト）"
session: "worktree"
---

# 受入テストスキル

## 概要
Issue要件に基づいて受入テスト（Acceptance Test）を自動実行し、すべての受入条件が満たされていることを検証するスキルです。

このスキルは**スラッシュコマンドモード**で動作します（ユーザーが直接実行）。

## 使用方法
- `/acceptance-test [Issue番号]`
- 「Issue #[番号]の受入テストを実行してください」
- 「[機能名]の受入条件を検証してください」

---

## 実行内容

**共通プロンプトを読み込んで実行します**:

```bash
cat .claude/prompts/acceptance-test-core.md
```

↑ **このプロンプトの内容に従って、受入テストを実行してください。**

---

## 動作モード

**スラッシュコマンドモード**:
- ユーザーから対話的に情報を取得
- Issue番号、受入条件、テストシナリオなどを確認
- E2Eテストを実行
- 結果をターミナルに表示

---

## 完了条件

以下をすべて満たすこと：
- ✅ すべてのテストシナリオが成功
- ✅ すべての受入条件が検証済み
- ✅ エビデンスが収集済み（ログ、スクリーンショットなど）

---

## 📝 Note

サブエージェントとして呼び出す場合は、PM Auto-Devが以下のように実行します：

```
Use acceptance-test-agent to verify Issue #166 acceptance criteria.
```

この場合、`.claude/agents/acceptance-test-agent.md` が使用されます（本ファイルは使用されません）。

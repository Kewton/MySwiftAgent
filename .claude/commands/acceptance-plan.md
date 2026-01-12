---
model: opus
description: "受入テスト計画を立案・レビュー"
phase: "8. 受入テスト準備"
session: "worktree"
---

# 受入テスト計画スキル

## 概要

Issue要件と設計方針に基づいて、意味のある受入テスト計画を立案するスキルです。

### 品質基準

| 基準 | 説明 |
|------|------|
| **ユーザー視点** | 実際のユーザー操作を想定したテスト |
| **E2E重視** | モックを最小限にし、実サービス連携を検証 |
| **デッドコード検出** | 実装された機能が実際に使用されていることを検証 |
| **設計方針準拠** | design-policy.md の設計判断が実装に反映されていることを検証 |

## 使用方法

- `/acceptance-plan [Issue番号]`
- 「Issue #350の受入テスト計画を作成してください」

---

## 実行内容

**共通プロンプトを読み込んで実行します**:

```bash
cat .claude/prompts/acceptance-plan-core.md
```

↑ **このプロンプトの内容に従って、受入テスト計画を立案してください。**

---

## 前提条件

以下のファイルが存在すること：

| ファイル | パス | 必須 |
|---------|------|------|
| 設計方針書 | `dev-reports/feature/issue/{issue_number}/design-policy.md` | ✅ 必須 |
| 作業計画書 | `dev-reports/feature/issue/{issue_number}/work-plan.md` | 推奨 |
| TDD結果 | `dev-reports/.../tdd-result.json` | 推奨 |

---

## 出力

### 受入テスト計画書

**ファイルパス**:
```
dev-reports/feature/issue/{issue_number}/acceptance-plan.md
```

**含まれる内容**:
1. 概要
2. 単体テスト結果レビュー
3. 受入条件分析
4. 設計方針検証項目
5. デッドコード検証計画
6. テスト環境・方法
7. テスト項目
8. テスト実行計画

---

## 動作モード

**スラッシュコマンドモード**:
- ユーザーから対話的に情報を取得
- Issue番号を指定して計画を立案
- 結果を `acceptance-plan.md` に出力

---

## 完了条件

以下をすべて満たすこと：

- ✅ Issue情報を読み込み済み
- ✅ design-policy.md を読み込み済み
- ✅ 単体テスト結果をレビュー済み
- ✅ 受入条件を分析済み
- ✅ 設計方針との整合性確認項目を作成済み
- ✅ デッドコード検証計画を作成済み
- ✅ テスト環境・方法を定義済み
- ✅ テスト項目を作成済み
- ✅ acceptance-plan.md を出力済み

---

## 📝 Note

サブエージェントとして呼び出す場合は、PM Auto-Devが以下のように実行します：

```
Use acceptance-plan-agent to create acceptance test plan for Issue #350.
```

この場合、`.claude/agents/acceptance-plan-agent.md` が使用されます。

---

## 関連スキル

- `/design-policy` - 設計方針作成（前提条件）
- `/work-plan` - 作業計画立案
- `/acceptance-test` - 受入テスト実行

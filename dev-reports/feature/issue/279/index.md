# Issue #279: myAgentDesk MVP再構築

## 概要

myAgentDesk MVP（SvelteKit）の設計ドキュメントおよびワイヤーフレーム集です。

**技術スタック**: Svelte 5.45.6 + SvelteKit 2.49.1 + TailwindCSS 4.1.18

---

## ドキュメント一覧

### 設計ドキュメント

| ファイル | 説明 | 主な内容 |
|---------|------|---------|
| [requirements.md](./requirements.md) | 要件定義書 | 機能要件、ユーザーストーリー、API連携仕様、バージョン管理体系 |
| [screen-transition.md](./screen-transition.md) | 画面遷移図 | URL設計、ナビゲーションフロー、状態遷移、アクセス制御 |
| [er-diagram.md](./er-diagram.md) | E-R図 | データモデル、エンティティ定義、外部サービス連携境界 |
| [design-system.md](./design-system.md) | デザインシステム | カラーパレット、タイポグラフィ、スペーシング、コンポーネント |
| [design-policy.md](./design-policy.md) | 設計方針書 | 技術選定理由、設計パターン、ADR、エラーハンドリング方針 |

### レビュードキュメント

| ファイル | 説明 | ステータス |
|---------|------|-----------|
| [architecture-review.md](./architecture-review.md) | アーキテクチャレビュー | ✅ 承認済 (4.4/5) |

### 実装計画

| ファイル | 説明 | 主な内容 |
|---------|------|---------|
| [issue-split.md](./issue-split.md) | Issue分割計画書 | 13 Issues、7 Phases、依存関係グラフ、マイルストーン |

---

## ワイヤーフレーム

| ファイル | テーマ | 説明 |
|---------|-------|------|
| [wireframe-pattern-a-professional-blue.html](./wireframe-pattern-a-professional-blue.html) | ライトモード | ビジネス向けの信頼感と清潔感のある青基調デザイン |
| [wireframe-pattern-b-dark-mode.html](./wireframe-pattern-b-dark-mode.html) | ダークモード | 開発者向けの目の疲労軽減を考慮したダークテーマ |

---

## 主要機能

### Workbench改善ループ

```
Requirements → Generate → Review → Run → Analyze → Improve → Requirements...
```

1. **Requirements**: 要件定義（Markdown形式）のバージョン管理
2. **Generate**: AI（ExpertAgent）によるJob自動生成
3. **Review**: 生成されたタスク分解の確認・編集
4. **Run**: Job実行と進捗モニタリング
5. **Analyze**: 実行結果の分析（Langfuse連携）
6. **Improve**: 分析結果に基づく改善提案

### バージョン管理体系

```
JobVersion: vN.M
  N = RequirementVersion（要件定義のバージョン）
  M = Job生成回数（同一要件からの生成回数）
```

例: `v5.2` = 要件定義v5から2回目のJob生成

---

## 関連サービス

| サービス | ポート | 役割 |
|---------|-------|------|
| ExpertAgent | 8104 | AIエージェント・Job/Workflow生成 |
| JobQueue | 8101 | ジョブキュー・非同期実行管理 |
| MyScheduler | 8102 | CRONスケジューリング |
| MyVault | 8103 | シークレット・プロジェクト設定管理 |
| GraphAiServer | 8105 | ワークフロー実行エンジン |
| Langfuse | 3001 | LLMトレーシング・分析 |

---

## モックアップ

インタラクティブなモックアップは以下で確認できます:

```bash
# 開発サーバー起動
cd myAgentDesk
npm run dev

# ブラウザでアクセス
open http://localhost:8000/mockups/feature-279/pattern-a
```

---

## 参照ドキュメント

- [expertAgent/docs/API_REFERENCE.md](../../../expertAgent/docs/API_REFERENCE.md) - API仕様
- [docs/arch/service-dependencies.md](../../../docs/arch/service-dependencies.md) - サービス間依存関係
- [myAgentDesk/README.md](../../../myAgentDesk/README.md) - SvelteKitセットアップ

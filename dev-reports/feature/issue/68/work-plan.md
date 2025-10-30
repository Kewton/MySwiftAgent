# 作業計画: myAgentDesk プロジェクト新規追加

**作成日**: 2025-10-30
**予定工数**: 2人日（約16時間）
**完了予定**: 2025-10-30

---

## 📚 参考ドキュメント

**必須参照**:
- [x] [新プロジェクトセットアップ手順書](../../docs/procedures/NEW_PROJECT_SETUP.md) - TypeScriptプロジェクト追加手順

**推奨参照**:
- [x] [アーキテクチャ概要](../../docs/design/architecture-overview.md)
- [x] [CLAUDE.md](../../CLAUDE.md) - ブランチ戦略・品質基準

**外部ドキュメント**:
- [ ] [SvelteKit Documentation](https://kit.svelte.dev/docs)
- [ ] [Vite Documentation](https://vitejs.dev/)

---

## 📊 Phase分解

### Phase 1: プロジェクト基盤作成（4時間）

**目的**: SvelteKitプロジェクトの基本構造を作成

**タスク**:
- [ ] プロジェクトディレクトリ作成（`myAgentDesk/`）
- [ ] `package.json` の作成と初期依存関係インストール
  - SvelteKit
  - TypeScript
  - Vite
  - Tailwind CSS
  - ESLint + Prettier
- [ ] `tsconfig.json` の作成（strict mode有効化）
- [ ] `svelte.config.js` の作成（adapter-node設定）
- [ ] `vite.config.ts` の作成（Cloudflare API proxy準備）
- [ ] Tailwind CSS設定（`tailwind.config.js`, `postcss.config.js`）
- [ ] `.gitignore` の作成（`node_modules/`, `.svelte-kit/`, `build/`）
- [ ] `README.md` の作成

**成果物**:
- ✅ myAgentDesk/package.json（バージョン: 0.1.0）
- ✅ TypeScript + SvelteKit設定ファイル一式
- ✅ Tailwind CSS設定

**検証**:
```bash
cd myAgentDesk
npm install
npm run dev  # 開発サーバー起動確認
```

---

### Phase 2: 基本UIコンポーネント実装（4時間）

**目的**: 3ページのワイヤーフレームを実装

**タスク**:
- [ ] 共通レイアウト作成（`src/routes/+layout.svelte`）
  - ヘッダー（ナビゲーション）
  - フッター
  - Tailwind CSSスタイリング
- [ ] トップページ作成（`src/routes/+page.svelte`）
  - ヒーローセクション
  - 機能紹介カード
  - CTA（Call To Action）
- [ ] エージェント一覧ページ作成（`src/routes/agents/+page.svelte`）
  - エージェントカードコンポーネント
  - グリッドレイアウト
  - ダミーデータ表示
- [ ] 設定ページ作成（`src/routes/settings/+page.svelte`）
  - 設定フォーム（基本構造）
  - 保存ボタン（イベントハンドラーのみ）
- [ ] 共通コンポーネント作成（`src/lib/components/`）
  - Button.svelte
  - Card.svelte
  - Header.svelte

**成果物**:
- ✅ 3ページのワイヤーフレーム実装
- ✅ 再利用可能な共通コンポーネント

**検証**:
```bash
npm run dev
# ブラウザで http://localhost:5173 を確認
# /agents, /settings ページの遷移確認
```

---

### Phase 3: Dockerファイル・CI/CD統合（3時間）

**目的**: コンテナ化とCI/CD統合

**タスク**:
- [ ] `Dockerfile` の作成（Multi-stage build）
  - Stage 1: ビルド（npm run build）
  - Stage 2: 本番実行（node build/index.js）
- [ ] `.dockerignore` の作成
- [ ] Health check エンドポイント実装（`src/routes/health/+server.ts`）
- [ ] Docker イメージビルド検証
- [ ] `.github/workflows/multi-release.yml` の更新
  - プロジェクト検出リスト（行395付近）に `myAgentDesk` 追加
- [ ] ポート設定統一（`PORT=8000`）

**成果物**:
- ✅ Dockerfile（multi-stage build）
- ✅ Health check API実装
- ✅ CI/CD統合設定

**検証**:
```bash
# Dockerビルド
docker build -t myagentdesk:0.1.0 ./myAgentDesk

# コンテナ起動
docker run -p 8000:8000 myagentdesk:0.1.0

# Health check
curl -f http://localhost:8000/health
```

---

### Phase 4: テスト実装・品質チェック（3時間）

**目的**: 単体テスト・E2Eテストの実装と品質担保

**タスク**:
- [ ] Vitest設定（`vitest.config.ts`）
- [ ] 単体テスト作成（`src/lib/components/*.test.ts`）
  - Button.svelteのテスト
  - Card.svelteのテスト
- [ ] Playwright設定（`playwright.config.ts`）
- [ ] E2Eテスト作成（`tests/integration/app.test.ts`）
  - トップページの表示確認
  - エージェント一覧ページの遷移確認
  - 設定ページの表示確認
- [ ] ESLint実行・修正
- [ ] TypeScript型チェック実行・修正
- [ ] カバレッジ測定（目標: 80%以上）

**成果物**:
- ✅ 単体テスト（Vitest）
- ✅ E2Eテスト（Playwright）
- ✅ ESLint・TypeScript品質クリア

**検証**:
```bash
# 単体テスト
npm test

# E2Eテスト
npm run test:e2e

# Linting
npm run lint

# 型チェック
npm run type-check

# カバレッジ
npm run test -- --coverage
```

---

### Phase 5: ドキュメント作成・PR提出（2時間）

**目的**: 最終ドキュメント作成とPR提出

**タスク**:
- [ ] `myAgentDesk/README.md` の充実
  - プロジェクト概要
  - セットアップ手順
  - 開発コマンド一覧
  - デプロイ手順
- [ ] Phase毎の進捗ドキュメント作成
  - phase-1-progress.md
  - phase-2-progress.md
  - phase-3-progress.md
  - phase-4-progress.md
- [ ] final-report.md の作成
- [ ] 全ファイルをコミット
- [ ] PR作成（feature/issue/68 → develop）
  - タイトル: "🎉 Add new TypeScript project: myAgentDesk (SvelteKit)"
  - ラベル: `feature`

**成果物**:
- ✅ 完全なドキュメント一式
- ✅ PR提出

**コミットメッセージ例**:
```
feat(myAgentDesk): add initial SvelteKit project structure

- Add SvelteKit + TypeScript project with Tailwind CSS
- Implement 3-page wireframe (/, /agents, /settings)
- Add Docker configuration (multi-stage build)
- Add Health check endpoint (/health)
- Add unit tests (Vitest) and E2E tests (Playwright)
- Add CI/CD integration (multi-release.yml)

Issue: #68

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

## ✅ 制約条件チェック結果

### コード品質原則
- [x] SOLID原則: 遵守予定 / コンポーネント単一責任
- [x] KISS原則: 遵守予定 / シンプルな構成
- [x] YAGNI原則: 遵守予定 / Cloudflareは段階的実装
- [x] DRY原則: 遵守予定 / 共通コンポーネント化

### アーキテクチャガイドライン
- [x] architecture-overview.md: 準拠予定
- [x] NEW_PROJECT_SETUP.md: 完全遵守

### 設定管理ルール
- [x] 環境変数: .env でCloudflare API URL管理予定
- [x] myVault: N/A（フロントエンドプロジェクト）

### 品質担保方針
- [x] 単体テスト: Vitest（目標80%以上）
- [x] E2Eテスト: Playwright
- [x] ESLint: TypeScript + Svelte用設定
- [x] TypeScript: strict mode有効化

### CI/CD準拠
- [x] PRラベル: `feature` ラベル付与予定
- [x] コミットメッセージ: Conventional Commits準拠
- [x] multi-release.yml: プロジェクトリスト追加予定

### 参照ドキュメント遵守
- [x] NEW_PROJECT_SETUP.md: TypeScript手順完全遵守
- [x] CLAUDE.md: ブランチ戦略・品質基準準拠

### 違反・要検討項目
なし

---

## 📅 スケジュール

| Phase | 開始予定 | 完了予定 | 所要時間 | 状態 |
|-------|---------|---------|---------|------|
| Phase 1 | 10/30 09:00 | 10/30 13:00 | 4時間 | 予定 |
| Phase 2 | 10/30 13:00 | 10/30 17:00 | 4時間 | 予定 |
| Phase 3 | 10/30 17:00 | 10/30 20:00 | 3時間 | 予定 |
| Phase 4 | 10/30 20:00 | 10/30 23:00 | 3時間 | 予定 |
| Phase 5 | 10/30 23:00 | 10/31 01:00 | 2時間 | 予定 |

**総所要時間**: 16時間（2人日）

---

## 📋 成功基準

| 基準 | 目標 | 検証方法 |
|------|------|---------|
| **プロジェクト構成** | NEW_PROJECT_SETUP.md準拠 | ディレクトリ構成確認 |
| **ビルド成功** | エラーなしでビルド完了 | `npm run build` |
| **開発サーバー起動** | 正常起動 | `npm run dev` |
| **Dockerビルド** | イメージ作成成功 | `docker build -t myagentdesk:0.1.0 .` |
| **Health check** | 200 OK | `curl http://localhost:8000/health` |
| **単体テスト** | 80%以上カバレッジ | `npm test -- --coverage` |
| **E2Eテスト** | 全テストパス | `npm run test:e2e` |
| **ESLint** | エラーゼロ | `npm run lint` |
| **TypeScript** | 型エラーゼロ | `npm run type-check` |
| **CI/CD統合** | multi-release.yml更新完了 | 目視確認 |
| **ワイヤーフレーム** | 3ページ実装完了 | ブラウザ確認 |

---

## 🎯 リスク管理

### リスク1: SvelteKit特有の設定

**リスク**: NEW_PROJECT_SETUP.mdの例（Express）と構成が異なる

**対策**:
- 公式ドキュメント参照
- adapter-node使用でDocker対応

**影響**: 低（SvelteKitは十分に成熟したフレームワーク）

### リスク2: Cloudflare連携の複雑性

**リスク**: Issue #68の要求（Cloudflare連携）が複雑

**対策**:
- Phase 1では基盤のみ準備
- 実装は将来のPhaseで対応

**影響**: 低（段階的実装で対応可能）

### リスク3: Tailwind CSS設定

**リスク**: SvelteKitとTailwindの統合に注意が必要

**対策**:
- 公式ガイド参照
- PostCSS設定確認

**影響**: 低（公式サポートあり）

---

## 🚀 次のステップ

ユーザー承認後、以下の順で実施：

1. **Phase 1実施**: プロジェクト基盤作成
2. **Phase 2実施**: ワイヤーフレーム実装
3. **Phase 3実施**: Docker・CI/CD統合
4. **Phase 4実施**: テスト・品質チェック
5. **Phase 5実施**: ドキュメント・PR提出

---

## 📝 備考

### SvelteKit vs Express の違い

| 項目 | SvelteKit | Express（手順書例） |
|------|-----------|-------------------|
| 用途 | フロントエンド（UI） | バックエンド（API） |
| エントリーポイント | `src/routes/+page.svelte` | `src/index.ts` |
| ルーティング | ファイルベース | コードベース |
| ビルド出力 | `.svelte-kit/` → `build/` | `dist/` |
| 開発ポート | 5173 | 8000 |
| 本番ポート | 8000（統一） | 8000 |

### パッケージ依存関係（概算）

**必須**:
- @sveltejs/kit
- @sveltejs/adapter-node
- svelte
- vite
- typescript

**開発**:
- vitest
- @playwright/test
- eslint
- prettier
- tailwindcss
- postcss
- autoprefixer

**総パッケージ数**: 約30-40パッケージ（開発依存含む）

---

**承認後、Phase 1から実施開始します。**

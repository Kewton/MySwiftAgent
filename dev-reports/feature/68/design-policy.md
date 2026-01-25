# 設計方針: myAgentDesk プロジェクト新規追加

**作成日**: 2025-10-30
**ブランチ**: feature/issue/68
**担当**: Claude Code
**Issue**: #68 "Sveltekitのプロジェクトを追加しワイヤーフレームを作成する"

---

## 📋 要求・要件

### ビジネス要求
- Issue #68: SvelteKitプロジェクトを追加し、ワイヤーフレームを作成
- プロジェクト名: **myAgentDesk**
- バックエンド連携: Cloudflareを利用した安全な連携

### 機能要件
1. **新TypeScriptプロジェクトの追加**: SvelteKitベースのフロントエンドプロジェクト
2. **ワイヤーフレーム作成**: 基本的なUI構造の実装
3. **バックエンド連携基盤**: Cloudflare経由での安全な通信設定
4. **CI/CD統合**: 既存のマルチプロジェクトリリースフローへの統合

### 非機能要件
- **パフォーマンス**: SvelteKitの高速レンダリングを活用
- **セキュリティ**: Cloudflare経由での通信暗号化
- **保守性**: TypeScriptによる型安全性確保
- **拡張性**: 将来的な機能追加に対応可能な構造

---

## 🏗️ アーキテクチャ設計

### システム構成

```
myAgentDesk/
├── src/
│   ├── routes/              # SvelteKitルーティング
│   │   ├── +page.svelte    # トップページ
│   │   ├── +layout.svelte  # 共通レイアウト
│   │   └── api/            # APIルート（オプション）
│   ├── lib/                 # 共通ライブラリ・コンポーネント
│   │   ├── components/     # Svelteコンポーネント
│   │   └── utils/          # ユーティリティ関数
│   └── app.html            # HTMLテンプレート
├── static/                  # 静的アセット
├── tests/                   # テストコード
│   ├── unit/               # 単体テスト
│   └── integration/        # 結合テスト
├── package.json            # プロジェクト設定・依存関係
├── tsconfig.json           # TypeScript設定
├── svelte.config.js        # SvelteKit設定
├── vite.config.ts          # Vite設定
├── Dockerfile              # コンテナイメージ定義
└── README.md               # プロジェクトドキュメント
```

### 技術選定

| 技術要素 | 選定技術 | 選定理由 |
|---------|---------|---------|
| **フレームワーク** | SvelteKit | Issue #68の要求、高速レンダリング、SSR/CSR対応 |
| **言語** | TypeScript | 型安全性、保守性向上 |
| **スタイリング** | Tailwind CSS | 迅速なUI開発、ユーティリティファースト |
| **ビルドツール** | Vite | 高速ビルド、HMR対応 |
| **テストフレームワーク** | Vitest + Playwright | SvelteKit推奨、E2Eテスト対応 |
| **バックエンド連携** | Cloudflare Workers（準備） | Issue #68の要求、エッジでの処理 |
| **デプロイ** | Docker + Node.js | CI/CD統合、既存フローとの整合性 |

### 技術スタック詳細

#### SvelteKit設定
```javascript
// svelte.config.js
import adapter from '@sveltejs/adapter-node';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

export default {
  preprocess: vitePreprocess(),
  kit: {
    adapter: adapter({
      out: 'build',
      precompress: true
    })
  }
};
```

#### Vite設定（Cloudflare準備）
```typescript
// vite.config.ts
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  plugins: [sveltekit()],
  test: {
    include: ['src/**/*.{test,spec}.{js,ts}']
  },
  server: {
    proxy: {
      '/api': {
        target: process.env.CLOUDFLARE_API_URL || 'http://localhost:8787',
        changeOrigin: true
      }
    }
  }
});
```

---

## 💡 技術的決定事項

### 決定1: SvelteKitのAdapter選定

**判断**: `@sveltejs/adapter-node` を使用

**理由**:
1. **Docker対応**: Node.jsランタイムでコンテナ化可能
2. **既存CI/CD統合**: multi-release.ymlのTypeScript検出に対応
3. **柔軟性**: SSR/CSRの柔軟な切替が可能

**代替案**:
- `@sveltejs/adapter-static`: 静的サイト生成（SSRなし）
- `@sveltejs/adapter-cloudflare`: Cloudflare Pages専用（Docker不要）

### 決定2: Tailwind CSS採用

**判断**: Tailwind CSS + DaisyUI（オプション）

**理由**:
1. **迅速な開発**: ユーティリティクラスで高速プロトタイピング
2. **一貫性**: デザインシステムの一元管理
3. **軽量化**: PurgeCSSで未使用スタイル除去

### 決定3: Cloudflare連携は段階的実装

**判断**: Phase 1では基盤のみ準備、Phase 2以降で実装

**理由**:
1. **複雑性管理**: まずプロジェクト基盤を安定化
2. **YAGNI原則**: 必要になってから実装
3. **段階的リリース**: 初回リリースは基本機能のみ

### 決定4: ワイヤーフレームのスコープ

**判断**: 基本的な3ページ構成

**実装内容**:
1. **トップページ** (`/`): サービス紹介、ダッシュボード
2. **エージェント一覧** (`/agents`): エージェントカード表示
3. **設定ページ** (`/settings`): 基本設定UI

**理由**:
- 初回リリースで最小限の機能を確認
- ワイヤーフレームとして十分な構造
- 将来的な拡張が容易

---

## ✅ 制約条件チェック結果

### コード品質原則
- [x] **SOLID原則**: 遵守 / コンポーネント単一責任、Svelte Storeで状態管理分離
- [x] **KISS原則**: 遵守 / シンプルなディレクトリ構成、最小限の依存関係
- [x] **YAGNI原則**: 遵守 / Cloudflare連携は段階的実装（Phase 2以降）
- [x] **DRY原則**: 遵守 / 共通コンポーネント・ユーティリティの共有

### アーキテクチャガイドライン
- [x] **architecture-overview.md**: 準拠 / マイクロサービス構成に適合
- [x] **NEW_PROJECT_SETUP.md**: 遵守 / TypeScriptプロジェクト手順に従う

### 設定管理ルール
- [x] **環境変数**: 準拠 / `.env` でCloudflare API URL等を管理
- [x] **myVault**: 該当なし / フロントエンドプロジェクトのため

### 品質担保方針
- [x] **単体テスト**: Vitest（目標: 80%以上）
- [x] **結合テスト**: Playwright（E2Eテスト）
- [x] **ESLint**: TypeScript + Svelte用設定
- [x] **TypeScript strict mode**: 有効化

### CI/CD準拠
- [x] **PRラベル**: `feature` ラベル予定
- [x] **コミットメッセージ**: Conventional Commits準拠
- [x] **multi-release.yml**: プロジェクトリスト追加必要

### 参照ドキュメント遵守
- [x] **NEW_PROJECT_SETUP.md**: TypeScriptプロジェクト手順を完全遵守
- [x] **CLAUDE.md**: ブランチ戦略・品質基準準拠

### 違反・要検討項目
なし

---

## 📚 参考資料

### 公式ドキュメント
- [SvelteKit Documentation](https://kit.svelte.dev/docs)
- [Svelte Documentation](https://svelte.dev/docs)
- [Vite Documentation](https://vitejs.dev/)
- [Cloudflare Workers Documentation](https://developers.cloudflare.com/workers/)

### プロジェクト内部ドキュメント
- [NEW_PROJECT_SETUP.md](../../docs/procedures/NEW_PROJECT_SETUP.md)
- [architecture-overview.md](../../docs/design/architecture-overview.md)
- [CLAUDE.md](../../CLAUDE.md)

---

## 📝 設計上の決定事項まとめ

1. **SvelteKit + TypeScript**: フロントエンドフレームワークとして採用
2. **@sveltejs/adapter-node**: Docker対応のため選定
3. **Tailwind CSS**: 迅速なUI開発のため採用
4. **Cloudflare連携**: Phase 2以降で段階的実装
5. **3ページ構成**: 初回リリースのワイヤーフレームスコープ
6. **Vitest + Playwright**: テストフレームワーク
7. **初回バージョン**: 0.1.0

---

## ⚠️ 注意事項

### SvelteKitとバックエンドの違い

**重要**: SvelteKitはフロントエンドフレームワークですが、NEW_PROJECT_SETUP.mdのTypeScript例（Express）はバックエンドです。以下の違いに注意：

| 項目 | SvelteKit（本プロジェクト） | Express（手順書例） |
|------|-------------------------|-------------------|
| **用途** | フロントエンド（UI） | バックエンド（API） |
| **レンダリング** | SSR/CSR対応 | なし |
| **ルーティング** | ファイルベース | コードベース |
| **ビルド出力** | 静的アセット + SSRサーバー | JSバンドル |
| **デプロイ** | Node.js adapter使用 | 標準的なNode.jsアプリ |

### ポート設定

- **開発**: `PORT=5173` (Vite default)
- **本番**: `PORT=8000` (Docker統一ポート)

### Cloudflare連携の注意

Phase 2以降でCloudflare Workers連携を実装する際は、以下を考慮：
- CORS設定
- 認証・認可
- エラーハンドリング

---

**次のステップ**: work-plan.md で作業計画を策定

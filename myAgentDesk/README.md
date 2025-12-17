# myAgentDesk

AI Agent Desktop - MySwiftAgentのWebインターフェース

## 技術スタック

- **Framework**: SvelteKit 2.49 + Svelte 5 (runes API)
- **Database**: SQLite + Drizzle ORM
- **Styling**: TailwindCSS 4
- **Testing**: Vitest + Playwright
- **Language**: TypeScript 5.9

## クイックスタート

### 1. 依存関係のインストール

```bash
npm install
```

### 2. データベースの初期化（オプション）

データベーステーブルは開発サーバー初回起動時に**自動作成**されます。

テスト用データを投入したい場合のみ実行：

```bash
npm run db:seed
```

### 3. 開発サーバーの起動

```bash
npm run dev
```

ブラウザで http://localhost:8000 にアクセス

## npm スクリプト

| コマンド | 説明 |
|---------|------|
| `npm run dev` | 開発サーバー起動 |
| `npm run build` | プロダクションビルド |
| `npm run preview` | ビルド結果のプレビュー |
| `npm run check` | TypeScript型チェック |
| `npm run lint` | Lint実行 |
| `npm run format` | コードフォーマット |
| `npm run test` | ユニットテスト（watch mode） |
| `npm run test:unit` | ユニットテスト（single run） |
| `npm run test:e2e` | E2Eテスト（Playwright） |
| `npm run db:push` | DBスキーマをプッシュ |
| `npm run db:seed` | シードデータ投入 |
| `npm run db:studio` | Drizzle Studio起動 |

## ディレクトリ構成

```
myAgentDesk/
├── src/
│   ├── lib/
│   │   ├── components/     # 再利用可能なコンポーネント
│   │   ├── server/         # サーバーサイドコード
│   │   │   ├── db/         # Drizzle ORM設定・スキーマ
│   │   │   └── repositories/ # データアクセス層
│   │   └── types/          # TypeScript型定義
│   └── routes/             # SvelteKitルート
│       ├── projects/       # プロジェクト画面
│       └── settings/       # 設定画面
├── data/                   # SQLiteデータベース
├── scripts/                # ユーティリティスクリプト
└── tests/                  # テストファイル
```

## 環境変数

`.env.example` を `.env` にコピーして設定：

```bash
cp .env.example .env
```

| 変数 | 説明 | デフォルト |
|-----|------|----------|
| `DATABASE_URL` | SQLiteデータベースパス | `./data/local.db` |
| `PORT` | サーバーポート | `8000` |

## トラブルシューティング

### "no such table" エラー

データベーステーブルが作成されていません：

```bash
npm run db:push
```

### プロジェクト一覧が空

シードデータを投入：

```bash
npm run db:seed
```

### ポートが使用中

別のポートで起動：

```bash
PORT=3000 npm run dev
```

## 関連ドキュメント

- [MySwiftAgent メインREADME](../README.md)
- [アーキテクチャ概要](../docs/design/architecture-overview.md)

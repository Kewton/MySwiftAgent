# myAgentDesk Getting Started

myAgentDeskの開発環境セットアップと基本的な使い方です。

## 前提条件

- Node.js 20+
- npm または pnpm

## セットアップ

### 1. 依存関係のインストール

```bash
cd myAgentDesk
npm install
```

### 2. 環境変数の設定

```bash
cp .env.example .env
```

```bash
# .env
PUBLIC_API_BASE_URL=http://localhost:8004
PUBLIC_WORKFLOW_API_URL=http://localhost:8006
```

### 3. 開発サーバーの起動

```bash
npm run dev
```

ブラウザで http://localhost:5173 を開きます。

## 基本的な使い方

### ジョブの作成

1. 「新規ジョブ」ボタンをクリック
2. ジョブ名を入力
3. プロンプトを入力
4. 「作成」をクリック

### ジョブの実行

1. ジョブ一覧から対象のジョブを選択
2. 「実行」ボタンをクリック
3. 実行結果を確認

### ワークフローの確認

1. 「ワークフロー」タブをクリック
2. 生成されたワークフロー一覧を確認
3. 詳細を表示して構造を確認

## 開発

### ディレクトリ構成

```
myAgentDesk/
├── src/
│   ├── lib/
│   │   ├── components/    # UIコンポーネント
│   │   ├── stores/        # Svelteストア
│   │   └── utils/         # ユーティリティ
│   └── routes/            # ページルート
├── static/                # 静的ファイル
├── tests/                 # テスト
│   ├── unit/              # 単体テスト
│   └── e2e/               # E2Eテスト
└── package.json
```

### テストの実行

```bash
# 単体テスト
npm test

# E2Eテスト
npm run test:e2e
```

### ビルド

```bash
npm run build
```

## トラブルシューティング

### API接続エラー

バックエンドサービスが起動していることを確認してください。

```bash
# サービス状態確認
curl http://localhost:8004/health
curl http://localhost:8006/health
```

### ビルドエラー

node_modulesを再インストールしてください。

```bash
rm -rf node_modules
npm install
```

## 関連ドキュメント

- [API Reference](../API_REFERENCE.md)
- [コンポーネント一覧](../components.md)
- [expertAgent API](../../../expertAgent/docs/API_REFERENCE.md)

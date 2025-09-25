# CommonUI

🎨 **CommonUI** は、MySwiftAgentの共通UIコンポーネントとStreamlitアプリケーションを提供するプロジェクトです。
JobQueueとMyScheduler向けの統一されたWeb UIを通じて、直感的なジョブ管理・スケジューリング操作を実現します。

## ✨ 特徴

- 🚀 **Streamlit**: 高速なプロトタイピングと直感的なUI
- 🔄 **Multi-Service**: JobQueueとMyScheduler両方に対応
- 🛡️ **堅牢性**: エラーハンドリング、リトライ処理、通知システム
- 🔧 **設定管理**: 環境変数とStreamlit Secretsによる柔軟な設定
- 📱 **レスポンシブ**: サイドバーベースの使いやすいレイアウト

## 📦 プロジェクト構成

```
commonUI/
├── Home.py                # Streamlitメインアプリ（ホーム画面）
├── pages/                 # マルチページアプリのページ群
│   ├── 1_📋_JobQueue.py   # JobQueue管理画面
│   └── 2_⏰_MyScheduler.py # MyScheduler管理画面
├── components/            # 共通UIコンポーネント
│   ├── sidebar.py         # サイドバー設定
│   ├── http_client.py     # HTTPクライアントとリトライ処理
│   └── notifications.py   # 通知・トースト管理
├── core/                  # コア機能
│   ├── config.py          # 設定管理
│   └── exceptions.py      # カスタム例外
├── tests/                 # テストコード
├── .streamlit/           # Streamlit設定
│   └── config.toml       # UI設定
├── .env.example          # 環境変数テンプレート
├── pyproject.toml        # プロジェクト設定
├── Dockerfile           # Docker設定
└── README.md           # このファイル
```

## 🚀 セットアップ

### 前提条件

- Python 3.12以上
- [uv](https://docs.astral.sh/uv/) パッケージマネージャ

### インストール

```bash
# 1. リポジトリクローン
git clone https://github.com/Kewton/MySwiftAgent.git
cd MySwiftAgent/commonUI

# 2. 依存関係インストール
uv sync --extra dev

# 3. 環境変数設定
cp .env.example .env
# .env ファイルを編集してAPI設定を行う
```

### 環境変数設定

`.env` ファイルまたはStreamlit Secretsで以下を設定：

```bash
# JobQueue API設定
JOBQUEUE_BASE_URL=http://localhost:8001
JOBQUEUE_API_TOKEN=your-jobqueue-token

# MyScheduler API設定
MYSCHEDULER_BASE_URL=http://localhost:8002
MYSCHEDULER_API_TOKEN=your-myscheduler-token

# UI設定
POLLING_INTERVAL=5
DEFAULT_SERVICE=JobQueue
OPERATION_MODE=full  # full | readonly
```

## 🏃 起動方法

### Streamlitアプリケーション

```bash
# メインUIの起動
uv run streamlit run Home.py

# ブラウザで http://localhost:8501 にアクセス
```

## 🎛️ 画面構成

### サイドバー設定

- **サービス切替**: JobQueue ↔ MyScheduler
- **API設定**: Base URL, Token, ポーリング間隔
- **操作モード**: 閲覧のみ / フル操作切替

### JobQueue管理画面

#### 作成タブ
- ジョブ定義フォーム送信
- 実行結果ダイアログ表示
- 成功時は詳細画面へ自動遷移

#### 一覧タブ
- フィルタ・検索機能
- ページング対応のジョブリスト
- 行クリックで詳細表示

#### 詳細画面
- ジョブ定義・実行結果表示
- キャンセル・再実行操作
- Live更新（ポーリング）

### MyScheduler管理画面

#### 作成タブ
- スケジュール種別切替（cron / interval / date）
- 動的入力フォーム
- バリデーション付き設定

#### 一覧タブ
- ジョブID / トリガー / 次回実行時刻 / 状態表示
- フィルタ・ソート機能

#### 詳細画面
- 人間可読なスケジュール説明
- ジョブ操作（停止/再開/削除）

## 🔧 開発・テスト

### コード品質チェック

```bash
# 静的解析・フォーマット
uv run ruff check .
uv run ruff format .
uv run mypy .
```

### テスト実行

```bash
# 全テスト実行
uv run pytest

# カバレッジ付きテスト
uv run pytest --cov=components --cov=core --cov-report=term-missing

# 統合テスト
uv run pytest tests/integration/ -v
```

### 起動確認

```bash
# アプリケーション起動テスト
timeout 5 uv run streamlit run Home.py --server.headless=true
```

## 🛡️ エラーハンドリング

### HTTPクライアント

- **リトライ処理**: 5xx系エラーのみ自動再試行（最大3回）
- **タイムアウト**: APIリクエストは30秒でタイムアウト
- **例外変換**: HTTP例外をUI表示用例外に変換

### 通知システム

- **成功通知**: `st.success()` + `st.toast()`
- **エラー通知**: `st.error()` + ログ出力
- **情報通知**: `st.info()` + 進行状況表示

### セキュリティ

- **秘密情報**: API Token等はログ出力から除外
- **入力検証**: Pydanticによる厳密なバリデーション
- **HTTPS**: 本番環境では必ずHTTPS通信

## 🐳 Docker

```bash
# イメージビルド
docker build -t commonui:latest .

# コンテナ起動
docker run -p 8501:8501 --env-file .env commonui:latest
```

## 📋 タスクリスト（Issue #13）

- [x] Streamlitプロジェクト初期化
- [x] プロジェクト構造設計（Home.py / pages/ / components/）
- [ ] サイドバー実装（サービス切替・API設定）
- [ ] 共通HTTPクライアント（httpx + リトライ）
- [ ] 例外ハンドリング（API→UI）
- [ ] 成功/失敗通知システム
- [ ] 環境変数・Secrets対応
- [ ] JobQueue UI実装
- [ ] MyScheduler UI実装
- [ ] 統合テスト・E2Eテスト

## 🤝 コントリビューション

1. このリポジトリをフォーク
2. フィーチャーブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. Pull Requestを作成

詳細は[CLAUDE.md](../CLAUDE.md)の開発ルールを参照してください。

## 📄 ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 🔗 関連リンク

- [MySwiftAgent メインリポジトリ](https://github.com/Kewton/MySwiftAgent)
- [Issue #13 - UIプロジェクトの雛形作成](https://github.com/Kewton/MySwiftAgent/issues/13)
- [JobQueue プロジェクト](../jobqueue/README.md)
- [MyScheduler プロジェクト](../myscheduler/README.md)
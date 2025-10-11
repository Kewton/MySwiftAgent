# CommonUI

🎨 **CommonUI** は、MySwiftAgentの共通UIコンポーネントとStreamlitアプリケーションを提供するプロジェクトです。
JobQueueとMyScheduler向けの統一されたWeb UIを通じて、直感的なジョブ管理・スケジューリング操作を実現します。

## ✨ 特徴

- 🚀 **Streamlit**: 高速なプロトタイピングと直感的なUI
- 🔄 **Multi-Service**: JobQueue、MyScheduler、MyVault全てに対応
- 🔐 **MyVault統合**: シークレット管理・キャッシュリロード・認証設定
- 🛡️ **堅牢性**: エラーハンドリング、リトライ処理、通知システム
- 🔧 **設定管理**: 環境変数とStreamlit Secretsによる柔軟な設定
- 📱 **レスポンシブ**: サイドバーベースの使いやすいレイアウト
- 📊 **リアルタイム**: 実行履歴の自動更新とライブモニタリング
- 🎯 **実行制御**: Trigger Now機能による即座のジョブ実行
- 🧪 **テストカバレッジ**: MyVault認証含む包括的なテスト (7 tests)

## 📦 プロジェクト構成

```
commonUI/
├── Home.py                # Streamlitメインアプリ（ホーム画面）
├── pages/                 # マルチページアプリのページ群
│   ├── 1_📋_JobQueue.py   # JobQueue管理画面
│   ├── 2_⏰_MyScheduler.py # MyScheduler管理画面
│   └── 3_🔐_MyVault.py    # 🆕 MyVault管理画面（シークレット管理）
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
MYSCHEDULER_BASE_URL=http://localhost:8003
MYSCHEDULER_API_TOKEN=your-myscheduler-token

# MyVault API設定（シークレット管理）
MYVAULT_BASE_URL=http://localhost:8105
MYVAULT_SERVICE_NAME=commonUI
MYVAULT_SERVICE_TOKEN=your-service-token

# ExpertAgent API設定（シークレットキャッシュリロード）
EXPERTAGENT_BASE_URL=http://localhost:8103
EXPERTAGENT_ADMIN_TOKEN=your-admin-token

# GraphAiServer API設定（シークレットキャッシュリロード）
GRAPHAISERVER_BASE_URL=http://localhost:8100
GRAPHAISERVER_ADMIN_TOKEN=your-admin-token

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

### MyVault管理画面 🆕

#### シークレット管理タブ
- **プロジェクト選択**: ドロップダウンでプロジェクトを切り替え
- **シークレット一覧**: プロジェクトごとのシークレットkey/value表示
- **シークレット追加・更新**: key/valueペアの登録・上書き
- **シークレット削除**: 不要なシークレットの削除
- **マスク表示**: デフォルトで値をマスク、クリックで表示切替

#### キャッシュリロードタブ
- **ExpertAgent**:
  - 全体キャッシュクリア（全プロジェクト）
  - プロジェクト別キャッシュクリア
  - リロード結果の即時フィードバック
- **GraphAiServer**:
  - 全体キャッシュクリア（全プロジェクト）
  - プロジェクト別キャッシュクリア
  - リロード結果の即時フィードバック

#### 認証設定タブ
- **シークレット定義管理**:
  - `myvault_secrets.yaml`の編集
  - プロジェクトごとのシークレットキー定義
  - YAMLバリデーション
  - 設定保存とリロード

**主な機能:**
- 🔐 複数プロジェクトのシークレット一元管理
- 🔄 ExpertAgent/GraphAiServerのキャッシュリロード
- 🛡️ X-Service/X-Token認証対応
- 📝 シークレット定義のYAML管理
- ⚡ リアルタイム更新と即時反映

### MyScheduler管理画面

#### 作成タブ
- **ジョブ名設定**: 識別しやすいジョブ名の設定
- **スケジュール種別切替**: cron / interval / date
- **動的入力フォーム**: スケジュール設定に応じた入力項目
- **HTTP設定**: URL, Method, Headers, Body設定
- **バリデーション**: 入力値の検証と詳細なエラー表示

#### Scheduled Jobs一覧タブ
- **包括的ジョブ情報表示**:
  - **Name**: 設定されたジョブ名（Job IDではなく）
  - **Next Run**: 次回実行予定時刻
  - **Trigger**: スケジュール設定の概要
  - **Status**: 実行状態（running/paused）
  - **Target URL**: 実行対象のAPI URL
  - **Method**: HTTP メソッド
  - **Executions**: 実行回数（リアルタイム更新）
- **ジョブ制御機能**:
  - **Trigger Now**: 選択されたジョブの即座実行
  - **Pause/Resume**: ジョブの一時停止・再開
  - **Delete**: ジョブの削除
- **フィルタ・ソート機能**: 条件による絞り込み

#### 詳細画面
- **ジョブ詳細情報**:
  - **ジョブ名**: 設定されたジョブ名
  - **スケジュール詳細**: 人間可読なスケジュール説明
  - **HTTP設定**: URL, Method, Headers, Body の詳細
  - **実行統計**: 総実行回数、成功/失敗率
- **実行履歴**:
  - **詳細な実行ログ**: 開始/終了時刻、ステータス、レスポンス詳細
  - **エラー情報**: 失敗時のエラーメッセージ
  - **パフォーマンス**: 実行時間、レスポンスサイズ
- **ジョブ操作**: 停止/再開/削除/即座実行

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
- **接続エラー対応**: サービス接続不可時の適切なエラー表示

### 通知システム

- **成功通知**: `st.success()` + `st.toast()`
- **エラー通知**: `st.error()` + ログ出力
- **情報通知**: `st.info()` + 進行状況表示
- **サービス状態**: 接続可否の視覚的フィードバック

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

## 🎯 主要機能の詳細

### MyScheduler統合機能

#### ジョブ名管理
- ジョブ作成時にユーザーフレンドリーなジョブ名を設定可能
- 一覧表示でJob IDではなくジョブ名を表示
- ジョブ名が未設定の場合はJob IDをフォールバック表示

#### 実行履歴トラッキング
- **リアルタイム実行カウント**: データベースベースの正確な実行回数表示
- **詳細実行履歴**: 各実行の開始/終了時刻、ステータス、実行時間
- **エラー追跡**: 失敗した実行のエラー詳細とリトライ情報
- **パフォーマンス監視**: HTTPステータス、レスポンスサイズ、実行時間

#### 即座実行機能（Trigger Now）
- スケジュールとは独立した手動実行機能
- 実行後も元のスケジュール設定を維持
- 即座実行も実行履歴に記録
- Next Runの適切な更新

### API連携機能

#### MyScheduler API統合
- `/api/v1/jobs` - ジョブ一覧取得・作成
- `/api/v1/jobs/{job_id}` - ジョブ詳細取得・削除
- `/api/v1/jobs/{job_id}/pause` - ジョブ一時停止
- `/api/v1/jobs/{job_id}/resume` - ジョブ再開
- `/api/v1/jobs/{job_id}/trigger` - ジョブ即座実行
- `/api/v1/jobs/{job_id}/executions` - ジョブ実行履歴取得

## 📋 完了済み機能（Issue #13対応）

- [x] Streamlitプロジェクト初期化
- [x] プロジェクト構造設計（Home.py / pages/ / components/）
- [x] サイドバー実装（サービス切替・API設定）
- [x] 共通HTTPクライアント（httpx + リトライ）
- [x] 例外ハンドリング（API→UI）
- [x] 成功/失敗通知システム
- [x] 環境変数・Secrets対応
- [x] JobQueue UI実装
- [x] MyScheduler UI実装（作成・一覧・詳細）
- [x] MyScheduler実行履歴機能
- [x] ジョブ名管理機能
- [x] Trigger Now（即座実行）機能
- [x] 実行回数カウント機能
- [x] 統合テスト・E2Eテスト

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
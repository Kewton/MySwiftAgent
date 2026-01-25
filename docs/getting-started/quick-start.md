# クイックスタート

5分でMySwiftAgentを起動し、最初のワークフローを実行するガイドです。

## 前提条件

- Docker Desktop がインストールされていること
- Git がインストールされていること
- Node.js 20+ がインストールされていること（オプション）
- Python 3.11+ がインストールされていること（オプション）

## 1. リポジトリのクローン

```bash
git clone https://github.com/your-org/MySwiftAgent.git
cd MySwiftAgent
```

## 2. 環境変数の設定

```bash
cp .env.example .env
```

最低限必要な環境変数を設定：

```bash
# .env
OPENAI_API_KEY=your-openai-api-key
# または
ANTHROPIC_API_KEY=your-anthropic-api-key
```

## 3. サービスの起動

```bash
make dev-all
```

すべてのサービスがDocker環境で起動します。

## 4. 動作確認

ヘルスチェックを実行：

```bash
./scripts/health-check.sh
```

期待される出力：

```
✅ JobQueue: healthy (http://localhost:8001)
✅ MyScheduler: healthy (http://localhost:8002)
✅ MyVault: healthy (http://localhost:8003)
✅ ExpertAgent: healthy (http://localhost:8004)
✅ GraphAiServer: healthy (http://localhost:8005)
```

## 5. Web UIにアクセス

ブラウザで以下のURLにアクセス：

- **myAgentDesk**: http://localhost:5173
- **Langfuse (Observability)**: http://localhost:3001

## 次のステップ

- [インストール詳細](./installation.md) - 各サービスの詳細設定
- [初めてのワークフロー](./first-workflow.md) - ワークフローの作成と実行
- [ローカル開発環境](../operations/local-development.md) - 開発環境の構築

---

**関連ドキュメント**:
- [環境変数一覧](../reference/environment-variables.md)
- [トラブルシューティング](../operations/troubleshooting.md)

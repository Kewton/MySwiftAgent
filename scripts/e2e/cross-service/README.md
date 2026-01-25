# Cross-Service E2E Tests

サービス間を横断する実践的なE2Eテストを格納するディレクトリです。

## 概要

このディレクトリには、複数のマイクロサービスを連携させた実践的なEnd-to-Endテストを配置します。
単一サービスのテストではなく、実際のユーザーシナリオに基づいたフルスタックテストです。

## テスト一覧

| テスト | 説明 | 所要時間 |
|--------|------|---------|
| `test_full_workflow_e2e.sh` | Job生成→実行→メール送信の完全E2E | 約3-5分 |

## 前提条件

### サービス起動

```bash
# Platform層（Docker）+ Agent層（ローカル）で起動
./scripts/dev-hybrid.sh stop --local-only
./scripts/dev-hybrid.sh start --local-only
```

### 必須サービス

| サービス | URL | 役割 |
|---------|-----|------|
| myAgentDesk | http://localhost:8000 | Web UI |
| expertAgent | http://localhost:8004 | Job Generator API |
| mySwiftAgentCore | http://localhost:8006 | Workflow実行 |
| myVault | http://localhost:8003 | シークレット管理 |

### 必須環境設定

- myVaultに `default_project` のシークレットが設定済み
  - `ANTHROPIC_API_KEY`: Claude API キー
  - `GOOGLE_CREDENTIALS`: Google API認証情報
  - `GMAIL_CREDENTIALS`: Gmail API認証情報

## テスト実行

### フルワークフローE2E

```bash
# 基本実行（インタラクティブモード）
./scripts/e2e/cross-service/test_full_workflow_e2e.sh

# パラメータ指定（非インタラクティブ）
./scripts/e2e/cross-service/test_full_workflow_e2e.sh \
  --keyword "大谷翔平の妻" \
  --email "your-email@example.com" \
  --project-id "proj_xxxx" \
  --workbench-id "wb_xxxx"

# ヘルプ表示
./scripts/e2e/cross-service/test_full_workflow_e2e.sh --help
```

### 全テスト実行

```bash
./scripts/e2e/cross-service/run_all_tests.sh
```

## テストフロー

### test_full_workflow_e2e.sh

```
1. サービスヘルスチェック
   ↓
2. myAgentDesk経由でJob Generate実行
   ↓
3. 生成されたJobVersionを確認
   ↓
4. Runを作成・実行（keyword + email パラメータ）
   ↓
5. Run完了を待機（ポーリング）
   ↓
6. 結果検証（status = success）
   ↓
7. レポート出力
```

## テスト結果

テスト結果は以下に出力されます：

```
scripts/e2e/cross-service/results/
├── test_full_workflow_YYYYMMDD_HHMMSS.log
└── test_full_workflow_YYYYMMDD_HHMMSS.json
```

## トラブルシューティング

### サービスが起動していない

```bash
# サービス状態確認
curl -s http://localhost:8000/api/health | jq
curl -s http://localhost:8004/health | jq
curl -s http://localhost:8006/health | jq

# 再起動
./scripts/dev-hybrid.sh stop --local-only
./scripts/dev-hybrid.sh start --local-only
```

### myVaultシークレットが設定されていない

```bash
# シークレット確認
curl -s http://localhost:8003/api/v1/projects/default_project/secrets \
  -H "X-Service-Name: test" \
  -H "X-Service-Token: test-token"
```

### Workbenchが見つからない

myAgentDesk (http://localhost:8000) でProjectとWorkbenchを事前に作成してください。

## 関連ドキュメント

- [mySwiftAgentCore E2Eテスト](../myswiftagentcore/README.md)
- [受入テストガイド](../../../docs/development/testing-guide.md)
- [ローカル開発環境](../../../docs/operations/local-development.md)

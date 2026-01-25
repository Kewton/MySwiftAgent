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

### デフォルトProject/Workbench

スクリプトには以下のデフォルト値が設定されています：

| 項目 | デフォルト値 |
|------|-------------|
| Project ID | `proj_mjbjua2z7y65wy` |
| Workbench ID | `wb_1766969315404_udrhx79` |

これらはmyAgentDeskで事前に作成されたProject/Workbenchを想定しています。
別のProject/Workbenchを使用する場合は`--project-id`と`--workbench-id`オプションで指定してください。

## テスト実行

### フルワークフローE2E

```bash
# 基本実行（デフォルトProject/Workbench使用）
./scripts/e2e/cross-service/test_full_workflow_e2e.sh \
  --keyword "大谷翔平の妻" \
  --email "your-email@example.com" \
  --no-confirm

# インタラクティブモード
./scripts/e2e/cross-service/test_full_workflow_e2e.sh

# カスタムProject/Workbench指定
./scripts/e2e/cross-service/test_full_workflow_e2e.sh \
  --keyword "検索キーワード" \
  --email "your-email@example.com" \
  --project-id "proj_xxxx" \
  --workbench-id "wb_xxxx" \
  --no-confirm

# 既存のJobVersionを使用（Job生成をスキップ）
./scripts/e2e/cross-service/test_full_workflow_e2e.sh \
  --skip-generate \
  --job-version-id "jv_xxxx" \
  --keyword "検索キーワード" \
  --email "your-email@example.com" \
  --no-confirm

# ヘルプ表示
./scripts/e2e/cross-service/test_full_workflow_e2e.sh --help
```

### オプション一覧

| オプション | 説明 | 必須 |
|-----------|------|------|
| `--keyword <keyword>` | 検索キーワード | No (デフォルト: AI技術の最新動向) |
| `--email <email>` | メール送信先 | Yes |
| `--project-id <id>` | Project ID | No (デフォルトあり) |
| `--workbench-id <id>` | Workbench ID | No (デフォルトあり) |
| `--skip-generate` | Job生成をスキップ | No |
| `--job-version-id <id>` | 使用するJobVersion ID | `--skip-generate`時に必須 |
| `--no-confirm` | 確認プロンプトをスキップ | No |

### 全テスト実行

```bash
./scripts/e2e/cross-service/run_all_tests.sh
```

## テストフロー

### test_full_workflow_e2e.sh

```
1. サービスヘルスチェック
   - myAgentDesk, expertAgent, mySwiftAgentCore, myVault
   ↓
2. Project/Workbench検証
   - デフォルトまたは指定されたIDの存在確認
   ↓
3. パラメータ確認
   - keyword, email の設定
   ↓
4. Job Generate実行
   - SvelteKit Form Actions経由でexpertAgentを呼び出し
   - 生成完了までポーリング（phase, progress表示）
   ↓
5. Run作成・実行
   - /api/runs APIでRun作成
   - JobQueueにジョブ登録
   ↓
6. Run完了待機
   - タスクステータスをポーリング
   - 全タスク完了で成功判定
   ↓
7. 結果検証・レポート出力
```

## テスト結果

テスト結果は以下に出力されます：

```
scripts/e2e/cross-service/results/
├── test_full_workflow_YYYYMMDD_HHMMSS.log   # 詳細ログ
└── test_full_workflow_YYYYMMDD_HHMMSS.json  # 結果JSON
```

### 結果JSONの例

```json
{
    "timestamp": "20260125_170428",
    "test": "full_workflow_e2e",
    "parameters": {
        "keyword": "大谷翔平の妻",
        "email": "test@example.com",
        "project_id": "proj_mjbjua2z7y65wy",
        "workbench_id": "wb_1766969315404_udrhx79",
        "job_version_id": "jv_xxx",
        "run_id": "run_xxx",
        "external_job_id": "j_xxx"
    },
    "result": {
        "status": "success",
        "duration_seconds": 120,
        "success": true
    }
}
```

## トラブルシューティング

### サービスが起動していない

```bash
# サービス状態確認
curl -s http://localhost:8000/ | head -1  # myAgentDesk
curl -s http://localhost:8004/health | jq
curl -s http://localhost:8006/health | jq
curl -s http://localhost:8003/health | jq

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

```bash
# Workbench存在確認
curl -s -o /dev/null -w "%{http_code}" \
  "http://localhost:8000/projects/proj_mjbjua2z7y65wy/workbenches/wb_1766969315404_udrhx79"
```

### 既に生成中のJobがある場合

スクリプトは自動的に生成中のJobの完了を待機します。
または、`--skip-generate --job-version-id "jv_xxx"`で既存のJobVersionを使用できます。

### Runステータスが更新されない

スクリプトはタスクレベルでステータスを確認します。
全タスクが成功（SUCCEEDED）になれば、Runステータスに関わらず成功と判定されます。

## 関連ドキュメント

- [mySwiftAgentCore E2Eテスト](../myswiftagentcore/README.md)
- [受入テストガイド](../../../docs/development/testing-guide.md)
- [ローカル開発環境](../../../docs/operations/local-development.md)

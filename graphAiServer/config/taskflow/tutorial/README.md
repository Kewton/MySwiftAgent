# TaskFlow v2 チュートリアル

TaskFlow v2 ワークフローエンジンの学習用チュートリアル集です。

## チュートリアル一覧

### 基礎編（Tutorial 1-7）

| # | ファイル | 内容 | 学習ポイント |
|---|---------|------|-------------|
| 1 | `1_hello.json` | Hello World | GETリクエスト、基本構造 |
| 2 | `2_post_with_body.json` | POST送信 | POSTリクエスト、動的ボディ |
| 3 | `3_sequential_chain.json` | 順次実行 | ステップ間のデータフロー |
| 4 | `4_parallel_fetch.json` | 並列実行 | parallel ブロック |
| 5 | `5_local_api.json` | ローカルAPI | 開発モード設定 |
| 6 | `6_expert_agent.json` | ExpertAgent連携 | 外部エージェント呼び出し |
| 7 | `7_expert_agent_chat.json` | チャット対話 | ユーザー入力処理 |

### Transform モード編（Tutorial 8-11）

| # | ファイル | 内容 | 学習ポイント |
|---|---------|------|-------------|
| 8 | `8_transform_template.json` | テンプレート変換 | Handlebars記法、ヘルパー関数 |
| 9 | `9_transform_map.json` | 配列変換 | mapモード、@index/@first/@last |
| 10 | `10_transform_concat.json` | 連結 | concatモード、separator |
| 11 | `11_transform_merge.json` | オブジェクト統合 | mergeモード、shallow/deep |

### V2 新機能編（Tutorial 12-15）

| # | ファイル | 内容 | 学習ポイント |
|---|---------|------|-------------|
| 12 | `12_conditional_basic.json` | 条件分岐（基本） | if/then/else、比較演算子 |
| 13 | `13_conditional_nested.json` | ネスト条件分岐 | 複雑な分岐ロジック |
| 14 | `14_validation_demo.json` | バリデーション | 3層検証、agentSummary |
| 15 | `15_vault_usage.json` | シークレット | ${secrets.KEY}、MyVault連携 |

### 実践編（Tutorial 16-18）

| # | ファイル | 内容 | 学習ポイント |
|---|---------|------|-------------|
| 16 | `16_data_pipeline.json` | データパイプライン | ETLパターン、複数ステップ連携 |
| 17 | `17_error_handling.json` | エラーハンドリング | フォールバック、グレースフル |
| 18 | `18_report_generator.json` | レポート生成 | 全技術の統合 |

## 実行方法

### 1. バリデーション（実行前確認）

```bash
curl -X POST http://localhost:8005/api/v2/workflows/validate \
  -H "Content-Type: application/json" \
  -d '{
    "definition": '"$(cat config/taskflow/tutorial/8_transform_template.json)"',
    "options": {"level": 2, "includeAgentFeedback": true}
  }'
```

### 2. ワークフロー実行

```bash
# Tutorial 8: テンプレート変換
curl -X POST http://localhost:8005/api/v2/workflows \
  -H "Content-Type: application/json" \
  -d '{
    "definition": '"$(cat config/taskflow/tutorial/8_transform_template.json)"',
    "inputs": {
      "name": "田中",
      "items": ["りんご", "みかん", "バナナ"],
      "show_count": true
    }
  }'
```

### 3. 登録して実行

```bash
# 登録
curl -X POST http://localhost:8005/api/v2/workflows/register \
  -H "Content-Type: application/json" \
  -H "x-admin-token: YOUR_TOKEN" \
  -d '{
    "workflow_name": "tutorial_8_transform_template",
    "definition": '"$(cat config/taskflow/tutorial/8_transform_template.json)"'
  }'

# 登録済みワークフロー実行
curl -X POST http://localhost:8005/api/v2/workflows \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_name": "tutorial_8_transform_template",
    "inputs": {"name": "田中", "items": ["りんご"], "show_count": true}
  }'
```

## 学習順序の推奨

```
基礎（1-4） → Transform（8-11） → 条件分岐（12-13） → 実践（16-18）
     ↓
ExpertAgent連携（5-7） → バリデーション（14） → シークレット（15）
```

## 注意事項

- **Tutorial 5-7**: `TASKFLOW_ALLOW_HTTP=true TASKFLOW_ALLOW_LOCAL=true` が必要
- **Tutorial 15**: MyVault サービスの起動が必要
- **Tutorial 14**: `/api/v2/workflows/validate` エンドポイントを使用

## Transform モード早見表

| モード | 用途 | 主なパラメータ |
|--------|------|---------------|
| `template` | テンプレート展開 | `template` |
| `map` | 配列変換 | `source_field`, `template` |
| `concat` | 連結 | `separator`, `fields` |
| `merge` | オブジェクト統合 | `strategy` (shallow/deep) |

## 条件式演算子

| 演算子 | 意味 | 例 |
|--------|------|-----|
| `==` | 等しい | `inputs.value == 10` |
| `!=` | 等しくない | `inputs.status != 'error'` |
| `>` | より大きい | `inputs.score > 80` |
| `<` | より小さい | `inputs.age < 18` |
| `>=` | 以上 | `inputs.count >= 5` |
| `<=` | 以下 | `inputs.price <= 1000` |

## 変数参照構文

| 構文 | 説明 | 例 |
|------|------|-----|
| `${inputs.field}` | 入力値参照 | `${inputs.user_id}` |
| `${node_id.output.field}` | ノード出力参照 | `${fetch.output.data}` |
| `${secrets.KEY}` | シークレット参照 | `${secrets.API_TOKEN}` |

# TaskFlowEngine E2E Tests

mySwiftAgentCore TaskFlowEngineのcapability E2Eテストスクリプト集です。

## 前提条件

- mySwiftAgentCore が起動していること（port 8006）
- expertAgent が起動していること（port 8004）
- 必要なAPIキーが設定されていること（OPENAI_API_KEY, SERPER_API_KEY等）

```bash
# サービス起動（開発モード）
cd mySwiftAgentCore && npm run dev

# または全サービス起動
./scripts/dev-hybrid.sh
```

## テストスクリプト

| スクリプト | Capability | 所要時間 | 備考 |
|-----------|------------|----------|------|
| `test_direct_llm.sh` | direct_llm | ~2秒 | GPT-4o-mini |
| `test_json_output_agent.sh` | json_output_agent | ~3秒 | Gemini |
| `test_google_search.sh` | google_search | 1-3分 | LLMナレッジ抽出あり |
| `test_gmail_send.sh` | gmail_send | ~1秒 | 実際にメール送信 |

## 使用方法

### 個別テスト

```bash
# direct_llm テスト
./test_direct_llm.sh

# json_output_agent テスト
./test_json_output_agent.sh

# google_search テスト（引数でクエリ指定可）
./test_google_search.sh "検索キーワード" 3

# gmail_send テスト（宛先必須）
./test_gmail_send.sh test@example.com "件名" "本文"
```

### 一括テスト

```bash
# 基本テストのみ（メール送信なし、google_search含む）
./run_all_tests.sh

# google_searchをスキップ（高速）
./run_all_tests.sh --skip-google

# メール送信テストを含む
./run_all_tests.sh --with-email test@example.com

# 全テスト実行
./run_all_tests.sh --with-email test@example.com
```

## 環境変数

| 変数 | デフォルト | 説明 |
|------|------------|------|
| `TASKFLOW_API` | http://localhost:8006 | TaskFlowEngine API URL |
| `EXPERT_AGENT_API` | http://localhost:8004 | ExpertAgent API URL |
| `PROJECT` | default_project | プロジェクトID |
| `TIMEOUT` | 180 | google_searchタイムアウト（秒） |

## テスト対象ワークフロー

テストで使用するワークフローは以下に格納されています：

```
mySwiftAgentCore/generated/workflows/default_project/capability_examples/
├── direct_llm_example.json
├── gmail_send_example.json
├── google_search_example.json
└── json_output_agent_example.json
```

## 注意事項

- `test_gmail_send.sh` は実際にメールを送信します
- `test_google_search.sh` はSerper API + LLM呼び出しのため1-3分かかります
- APIキーが設定されていない場合、テストは失敗します

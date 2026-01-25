# Langfuse 統合規約

**バージョン:** 1.0.0
**最終更新日:** 2025-12-11
**ステータス:** 有効

---

## 概要

本ドキュメントは、MySwiftAgentにおけるLangfuse統合の設定・運用ガイドを定義します。Langfuseは以下の機能を提供するLLM Observabilityプラットフォームです:

- **トレーシング**: LLM呼び出しの詳細ログ記録
- **コスト追跡**: トークン使用量とコストの可視化
- **品質評価**: プロンプトと応答の品質分析
- **デバッグ**: LLMワークフローの問題診断
- **Self-hosted**: オンプレミス環境でのデプロイ対応

---

## アーキテクチャ

### サービス間通信パターン

```
+------------------+
|  expertAgent     |
|  (LangGraph)     |
+--------+---------+
         |
         | Langfuse CallbackHandler
         | (トレース送信)
         v
+------------------+
|  Langfuse API    |
|  (ポート 3001)   |
+--------+---------+
         |
         v
+------------------+
|  PostgreSQL      |
| (トレースDB)     |
+------------------+
```

### 主要コンポーネント

| コンポーネント | 説明 | 場所 |
|---------------|------|------|
| **LangfuseService** | Langfuse連携サービス | `expertAgent/app/services/langfuse_service.py` |
| **CallbackHandler** | LangChain/LangGraphコールバック | `langfuse.callback.CallbackHandler` |
| **trace_id** | トレース識別子 | SSEイベントで伝播 |
| **Langfuse Self-hosted** | オンプレミス Langfuse | `docker-compose.yml` |

---

## 必須パラメータ

### 環境変数 (expertAgent)

| 変数名 | 型 | 必須 | 説明 | 例 |
|--------|------|------|------|-----|
| `LANGFUSE_ENABLED` | Boolean | 任意 | Langfuse統合の有効/無効 | `true` (デフォルト: `false`) |
| `LANGFUSE_SECRET_KEY` | String | はい* | Langfuse Secret Key | `sk-lf-xxxxxxxx` |
| `LANGFUSE_PUBLIC_KEY` | String | はい* | Langfuse Public Key | `pk-lf-xxxxxxxx` |
| `LANGFUSE_HOST` | String | 任意 | Langfuse APIエンドポイント | `http://localhost:3001` |

*`LANGFUSE_ENABLED=true`の場合は必須

### MyVault経由での設定 (推奨)

MyVaultを使用してLangfuse APIキーを安全に管理できます:

```yaml
# myVault経由でシークレットを取得
project: default
secrets:
  - LANGFUSE_SECRET_KEY
  - LANGFUSE_PUBLIC_KEY
```

---

## セットアップ手順

### ステップ1: Langfuse Self-hostedの起動

Docker Composeを使用してLangfuseをローカルで起動:

```bash
# 標準のdev-start.shで起動
./scripts/dev-start.sh

# または make コマンド
make dev-all
```

Langfuseは `http://localhost:3001` でアクセス可能です。

### ステップ2: Langfuseの初期設定

1. ブラウザで `http://localhost:3001` にアクセス
2. 管理者アカウントを作成
3. プロジェクトを作成
4. Settings > API Keys から以下を取得:
   - **Secret Key** (`sk-lf-xxxxxxxx`)
   - **Public Key** (`pk-lf-xxxxxxxx`)

### ステップ3: 環境変数の設定

**開発環境 (`.env`):**

```env
# Langfuse設定
LANGFUSE_ENABLED=true
LANGFUSE_SECRET_KEY=sk-lf-xxxxxxxx
LANGFUSE_PUBLIC_KEY=pk-lf-xxxxxxxx
LANGFUSE_HOST=http://localhost:3001
```

**MyVaultを使用する場合:**

```bash
# MyVaultにシークレットを登録
curl -X POST http://localhost:8003/api/secrets \
  -H "Content-Type: application/json" \
  -H "X-Service: expertAgent" \
  -H "X-Token: <service-token>" \
  -d '{
    "project": "default",
    "path": "LANGFUSE_SECRET_KEY",
    "value": "sk-lf-xxxxxxxx"
  }'

curl -X POST http://localhost:8003/api/secrets \
  -H "Content-Type: application/json" \
  -H "X-Service: expertAgent" \
  -H "X-Token: <service-token>" \
  -d '{
    "project": "default",
    "path": "LANGFUSE_PUBLIC_KEY",
    "value": "pk-lf-xxxxxxxx"
  }'
```

---

## LangfuseService の使用方法

### 基本的な初期化

```python
from app.services.langfuse_service import LangfuseService

# MyVault経由で初期化（推奨）
langfuse_service = await LangfuseService.create_from_myvault()

# または環境変数から直接初期化
langfuse_service = LangfuseService.create_from_env()
```

### CallbackHandlerの取得

```python
# LangChain/LangGraph用のコールバックハンドラーを取得
handler = langfuse_service.get_callback_handler()

# LLM呼び出し時にコールバックを設定
response = await llm.ainvoke(
    messages,
    config={"callbacks": [handler]}
)
```

### trace_idの抽出

```python
from app.services.langfuse_service import LangfuseService

# LLM呼び出し後にtrace_idを取得
trace_id = LangfuseService.extract_trace_id(handler)

if trace_id:
    # trace_idを会話メタデータに保存
    await conversation_service.save_with_metadata(
        conversation_id=conversation_id,
        messages=messages,
        metadata={"trace_id": trace_id}
    )
```

---

## trace_id の伝播フロー

### SSEストリーム経由での伝播

```
1. チャットリクエスト受信
   ↓
2. LangfuseService.get_callback_handler()
   ↓
3. LLM呼び出し (handler付き)
   ↓
4. LangfuseService.extract_trace_id(handler)
   ↓
5. SSEイベントとしてtrace_idを送信
   └─ data: {"type": "trace_id", "trace_id": "abc123"}
   ↓
6. ConversationService.save_with_metadata()
   └─ metadata: {"trace_id": "abc123"}
```

### Diagnostics APIでの取得

```bash
# 会話データと共にtrace_urlを取得
curl http://localhost:8004/aiagent-api/v1/chat/diagnostics?limit=10
```

レスポンス例:
```json
{
  "items": [
    {
      "conversation_id": "conv-123",
      "langfuse_link": {
        "trace_url": "http://localhost:3001/trace/abc123",
        "trace_id": "abc123"
      }
    }
  ]
}
```

---

## フロントエンド連携

### View in Langfuse リンク

MLOps Diagnosticsページでは、有効なtrace_urlがある場合のみ「View in Langfuse」リンクが表示されます:

```svelte
{#if selectedDiagnostic.langfuse_trace_url && isValidLangfuseUrl(selectedDiagnostic.langfuse_trace_url)}
  <a href={selectedDiagnostic.langfuse_trace_url} target="_blank">
    View in Langfuse
  </a>
{/if}
```

### デモデータの検出

APIがエラーまたは空リストを返した場合、デモデータにフォールバックします。
デモデータ使用時は以下の表示が行われます:

1. 「デモデータを表示中」警告バナーが表示
2. 「View in Langfuse」リンクは非表示（`/trace/demo`はフェイクURL）

---

## ポート構成

### 標準ポート

| サービス | ポート | URL |
|---------|--------|-----|
| Langfuse (Web UI) | 3001 | http://localhost:3001 |
| Langfuse (API) | 3001 | http://localhost:3001/api |

### Docker Compose設定

```yaml
# docker-compose.yml
services:
  langfuse:
    image: langfuse/langfuse:latest
    ports:
      - "3001:3000"
    environment:
      - DATABASE_URL=postgresql://langfuse:langfuse@langfuse-postgres:5432/langfuse
      - NEXTAUTH_SECRET=your-nextauth-secret
      - SALT=your-salt
      - NEXTAUTH_URL=http://localhost:3001
```

---

## トラブルシューティング

### エラー: "Trace not found"

**原因**: Langfuseでトレースが見つからない、または処理中

**解決策**:

1. **トレースが生成されているか確認**:
   ```bash
   # Langfuse ヘルスチェック
   curl http://localhost:3001/api/public/health
   ```

2. **APIキーが正しく設定されているか確認**:
   ```bash
   # expertAgentの環境変数を確認
   echo $LANGFUSE_ENABLED
   echo $LANGFUSE_SECRET_KEY
   ```

3. **CallbackHandlerが正しく設定されているか確認**:
   - LLM呼び出し時に`callbacks=[handler]`が渡されているか
   - `handler.last_trace_id`が取得できるか

4. **Langfuseの処理遅延**:
   - トレースは非同期で送信されるため、数秒の遅延が発生する場合がある
   - 「Retry」ボタンをクリックして再確認

### エラー: "View in Langfuse" リンクが表示されない

**原因**:

1. デモデータを使用中（`/trace/demo` URL）
2. `langfuse_trace_url`が`null`または空

**解決策**:

1. **Diagnostics APIが正しいデータを返しているか確認**:
   ```bash
   curl http://localhost:8004/aiagent-api/v1/chat/diagnostics?limit=10
   ```

2. **会話データがValkeyに保存されているか確認**:
   ```bash
   docker exec myswiftagent-valkey redis-cli KEYS "conversation:*"
   ```

3. **trace_idがメタデータに含まれているか確認**:
   - `save_with_metadata()`が呼び出されているか
   - `metadata`に`trace_id`が設定されているか

### エラー: Langfuseに接続できない

**原因**: Langfuseサービスが起動していない

**解決策**:

```bash
# Dockerコンテナの状態を確認
docker ps | grep langfuse

# Langfuseを再起動
docker-compose restart langfuse

# ログを確認
docker-compose logs -f langfuse
```

---

## テスト

### ヘルスチェック

```bash
# Langfuseヘルスチェック
curl -sf http://localhost:3001/api/public/health && echo "Langfuse: healthy"
```

### 統合テスト (Python)

```python
import pytest
from app.services.langfuse_service import LangfuseService

class TestLangfuseIntegration:
    def test_extract_trace_id_with_valid_handler(self):
        """有効なハンドラーからtrace_idを抽出できる"""
        class MockHandler:
            last_trace_id = "test-trace-123"

        trace_id = LangfuseService.extract_trace_id(MockHandler())
        assert trace_id == "test-trace-123"

    def test_extract_trace_id_with_none_handler(self):
        """Noneハンドラーの場合はNoneを返す"""
        trace_id = LangfuseService.extract_trace_id(None)
        assert trace_id is None

    def test_extract_trace_id_without_attribute(self):
        """last_trace_id属性がない場合はNoneを返す"""
        class MockHandler:
            pass

        trace_id = LangfuseService.extract_trace_id(MockHandler())
        assert trace_id is None
```

### 受入テスト (L3)

```bash
# L3受入テストを実行
uv run pytest tests/acceptance/test_issue_194_acceptance.py -v
```

---

## セキュリティベストプラクティス

### 1. APIキー管理

- **MyVaultを使用してAPIキーを管理** (推奨)
- **環境変数に直接APIキーを設定しない** (開発環境を除く)
- **APIキーをGitにコミットしない**

### 2. ネットワークセキュリティ

- **本番環境ではHTTPSを使用**
- **Langfuseへのアクセスを内部ネットワークに制限**

### 3. データプライバシー

- **機密データをプロンプトに含めない**
- **PIIデータのマスキングを検討**

---

## 関連ドキュメント

- **MyVault統合規約**: [`docs/design/myvault-integration.md`](./myvault-integration.md)
- **アーキテクチャ概要**: [`docs/design/architecture-overview.md`](./architecture-overview.md)
- **環境変数一覧**: [`docs/design/environment-variables.md`](./environment-variables.md)
- **expertAgent API Reference**: [`expertAgent/docs/API_REFERENCE.md`](../../expertAgent/docs/API_REFERENCE.md)
- **Langfuse公式ドキュメント**: https://langfuse.com/docs

---

## コンプライアンスチェックリスト

Langfuse統合をデプロイする前に:

- [ ] Langfuse Self-hostedが起動している
- [ ] Langfuse APIキーを取得している
- [ ] 環境変数またはMyVaultでAPIキーを設定している
- [ ] `LANGFUSE_ENABLED=true`が設定されている
- [ ] LLM呼び出し時にCallbackHandlerが渡されている
- [ ] `extract_trace_id()`でtrace_idを取得している
- [ ] `save_with_metadata()`でtrace_idを保存している
- [ ] Diagnostics APIでtrace_urlが返却されている
- [ ] フロントエンドで「View in Langfuse」リンクが動作している
- [ ] 単体テストが通過している
- [ ] L3受入テストが通過している

---

**管理者**: MySwiftAgentコアチーム
**質問**: メインリポジトリでissueを開く

---

最終更新: 2025-12-11

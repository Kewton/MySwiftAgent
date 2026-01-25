# 要件定義書: Issue #263

## Langfuse CallbackHandler の myVault APIキー対応

**Issue**: [#263](https://github.com/Kewton/MySwiftAgent/issues/263)
**作成日**: 2025-12-09
**ステータス**: Draft

---

## 1. ユーザーストーリー

```
As a システム管理者
I want to myVault に保存した Langfuse APIキーで LLM トレースを送信したい
So that 環境変数を設定せずにセキュアにシークレット管理ができる
```

---

## 2. 受入条件（Acceptance Criteria）

### AC-1: myVault APIキーでトレース送信

| 項目 | 内容 |
|------|------|
| **Given** | myVault に `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST` が設定されている |
| **When** | 要件定義チャット (`/chat/requirement-definition`) を実行する |
| **Then** | Langfuse UI にトレースが表示される |

### AC-2: 環境変数未設定でも動作

| 項目 | 内容 |
|------|------|
| **Given** | 環境変数 `LANGFUSE_*` が設定されていない |
| **And** | myVault に APIキーが設定されている |
| **When** | LLM 呼び出しが行われる |
| **Then** | myVault の APIキーでトレースが送信される |

### AC-3: 既存機能との互換性

| 項目 | 内容 |
|------|------|
| **Given** | `ai_agent_service.py` のサンプルエージェントが動作している |
| **When** | Langfuse統合修正後にエージェントを実行する |
| **Then** | 同様にトレースが送信される（既存動作を壊さない） |

### AC-4: Langfuse無効時の動作

| 項目 | 内容 |
|------|------|
| **Given** | myVault にも環境変数にも APIキーが設定されていない |
| **When** | LLM 呼び出しが行われる |
| **Then** | エラーなく動作し、トレースはスキップされる |

---

## 3. 機能要件

### 必須機能（Must Have）

| ID | 要件 | 優先度 |
|----|------|--------|
| FR-1 | `get_callback_handler()` が myVault APIキーを使用する | P0 |
| FR-2 | Langfuse v3 API 仕様に準拠した実装 | P0 |
| FR-3 | 既存の `Langfuse` クライアント初期化を活用 | P0 |
| FR-4 | `flush()` が正しくトレースを送信する | P0 |

### あると良い機能（Nice to Have）

| ID | 要件 | 優先度 |
|----|------|--------|
| FR-5 | `trace_name`, `user_id`, `session_id` パラメータの活用 | P1 |
| FR-6 | トレース送信成功/失敗のログ出力 | P1 |

### 将来的な拡張（Future Enhancement）

| ID | 要件 |
|----|------|
| FR-7 | マルチプロジェクト対応（複数 Langfuse インスタンス） |
| FR-8 | トレースサンプリング設定 |

---

## 4. 非機能要件

### パフォーマンス要件

| 項目 | 基準 |
|------|------|
| トレース送信遅延 | LLM レスポンスに影響しない（非同期送信） |
| メモリ使用量 | シングルトンパターンで1クライアントのみ |

### セキュリティ要件

| 項目 | 基準 |
|------|------|
| APIキー管理 | myVault 経由で取得（環境変数にハードコードしない） |
| ログ出力 | APIキーをログに出力しない |

### ユーザビリティ要件

| 項目 | 基準 |
|------|------|
| 設定変更 | myVault 更新後は expertAgent 再起動で反映 |
| エラーメッセージ | 設定ミス時に明確なエラーログを出力 |

### 互換性要件

| 項目 | 基準 |
|------|------|
| Langfuse SDK | v3.x（現在インストール済み） |
| Python | 3.12+ |

---

## 5. 技術的制約

### 使用する技術スタック

| 技術 | バージョン | 用途 |
|------|-----------|------|
| Langfuse SDK | v3.x | LLM Observability |
| LangChain | 0.3.x | LLM フレームワーク |
| myVault API | v1 | シークレット管理 |

### 既存システムとの連携

```
myVault (port 8103)
    ↓ secrets_manager.get_secret()
expertAgent/langfuse_service.py
    ↓ Langfuse(public_key, secret_key, host)
    ↓ CallbackHandler()
Langfuse Self-hosted (port 3001)
```

### Langfuse v3 API 仕様

**重要**: Langfuse LangChain統合ドキュメントによると、v3 では以下のパターンが推奨されています：

```python
from langfuse import Langfuse, get_client
from langfuse.langchain import CallbackHandler

# 1. Langfuse クライアントを初期化（APIキー設定）
Langfuse(
    public_key="...",
    secret_key="...",
    host="..."
)

# 2. CallbackHandler は引数なしで作成
# → 内部で get_client() を呼び出し、上記で設定されたクライアントを使用
handler = CallbackHandler()
```

---

## 6. 実装方針

### 対応案

現在の `_initialize_client()` で `Langfuse()` を呼び出していますが、これがグローバルシングルトンとして機能しているか確認が必要です。

**Option A: 既存実装の確認・修正**
- `Langfuse()` コンストラクタ呼び出し時にグローバルクライアントが設定される仕様であれば、`CallbackHandler()` が自動的にそのクライアントを使用する
- 現在の実装が正しく動作しない原因を特定し修正

**Option B: CallbackHandler に public_key を明示的に渡す**
```python
handler = CallbackHandler(public_key=public_key)
```

### 修正対象ファイル

| ファイル | 変更内容 |
|----------|----------|
| `expertAgent/app/services/langfuse_service.py` | `get_callback_handler()` の修正 |
| `expertAgent/tests/unit/test_langfuse_service.py` | 単体テスト追加/修正 |

---

## 7. リスクと対策

| リスク | 影響度 | 対策 |
|--------|--------|------|
| Langfuse v3 API 変更 | 中 | SDK バージョン固定、ドキュメント参照 |
| myVault 接続障害時の動作 | 低 | 既存の graceful degradation 維持 |
| 既存トレース機能への影響 | 中 | 既存テストの実行、回帰テスト |

---

## 8. テスト計画

### 単体テスト

| テストケース | 検証内容 |
|--------------|----------|
| `test_callback_handler_uses_myvault_keys` | myVault APIキーで CallbackHandler が作成される |
| `test_callback_handler_disabled_gracefully` | APIキー未設定時に None を返す |
| `test_flush_sends_traces` | flush() がトレースを送信する |

### 結合テスト（ローカル受入テスト）

| テストケース | 検証内容 |
|--------------|----------|
| 要件定義チャット実行 → Langfuse UI でトレース確認 | E2E トレース送信 |
| サンプルエージェント実行 → Langfuse UI でトレース確認 | 既存機能の回帰確認 |

---

## 参照資料

- [Langfuse LangChain Integration](https://langfuse.com/docs/langchain/python)
- [Langfuse Python SDK Advanced Usage](https://langfuse.com/docs/observability/sdk/python/advanced-usage)
- [GitHub Discussion: CallbackHandler init params](https://github.com/orgs/langfuse/discussions/7651)
- [GitHub Issue: Multi-project setting](https://github.com/langfuse/langfuse/issues/7322)

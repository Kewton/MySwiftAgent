# Issue #194: Langfuse Trace not found エラーの長期対応 - 要件定義書

> 作成日: 2025-12-08
> Issue: [#194](https://github.com/kewton/MySwiftAgent/issues/194)
> ステータス: 要件定義完了

---

## 調査結果サマリー

### 発見した根本原因（Issue #194の元の分析を補完）

| 原因 | 詳細 | 該当コード |
|------|------|-----------|
| **ストレージ不整合** ⭐ | チャットAPI：インメモリ / Diagnostics API：Valkey | `chat_endpoints.py:35`, `diagnostic_endpoints.py:21` |
| デモデータのフェイクURL | Issue記載通り | `+page.svelte:111` |
| Langfuse APIキー未設定時 | Issue記載通り | `langfuse_service.py:52-59` |

### コード調査結果

| ファイル | 使用ストレージ | 永続化 |
|---------|--------------|--------|
| `expertAgent/app/api/v1/chat_endpoints.py:35` | `conversation_store`（インメモリ） | ❌ サーバー再起動で消失 |
| `expertAgent/app/api/v1/diagnostic_endpoints.py:21` | `ConversationStoreValkey` | ✅ Valkey永続化 |

### Phase優先度の提案

| Phase | 内容 | 優先度 | 理由 |
|-------|------|--------|------|
| **Phase 2** | バックエンドのストレージ統一 | 🔴 最高 | 根本原因の解決 |
| Phase 1 | フロントエンドの改善 | 🟡 中 | UX改善（即効性あり） |
| Phase 3 | Langfuse連携強化 | 🟢 低 | Phase 2完了後に実施 |

---

## 1. ユーザーストーリー

### 主要ストーリー
```
As a 開発者/運用担当者
I want to MLOps Diagnosticsページで会話の詳細とLangfuseトレースを確認したい
So that AIエージェントの応答品質を分析・改善できる
```

### サブストーリー
```
As a 開発者
I want to チャットセッションの会話履歴が永続化される
So that サーバー再起動後も会話データにアクセスできる

As a 開発者
I want to デモデータと実データを明確に区別できる
So that 誤ったリンクをクリックすることがない

As a 開発者
I want to Langfuse連携の状態を確認できる
So that トレーシングが正しく動作しているか把握できる
```

---

## 2. 受入条件（Acceptance Criteria）

### Phase 1: フロントエンドの改善

#### AC1.1: デモデータ表示の明確化
- **Given**: APIがエラーまたは空リストを返した場合
- **When**: Diagnosticsページがデモデータにフォールバックする
- **Then**:
  - 「デモデータを表示中」のバナーが表示される
  - 「View in Langfuse」リンクが非表示になる
  - デモデータであることがユーザーに明確に伝わる

#### AC1.2: 有効なtrace_urlの検証
- **Given**: 会話データにlangfuse_trace_urlが含まれる場合
- **When**: URLが有効な形式（`http(s)://host/trace/{valid-uuid}`）の場合
- **Then**: 「View in Langfuse」リンクが表示される
- **When**: URLがデモ用（`/trace/demo`）または無効な場合
- **Then**: リンクは非表示

---

### Phase 2: バックエンドの改善 ⭐ **最重要**

#### AC2.1: ストレージ統一
- **Given**: ユーザーがチャットAPIで会話を行う
- **When**: メッセージが保存される
- **Then**:
  - 会話データがValkeyに永続化される（`ConversationStoreValkey`使用）
  - Diagnostics APIで同じデータが取得可能になる
  - サーバー再起動後もデータが保持される

#### AC2.2: trace_idの生成と保存
- **Given**: チャットセッションが開始される
- **When**: 最初のメッセージが送信される
- **Then**:
  - ユニークな`trace_id`がUUID形式で生成される
  - `trace_id`がValkeyのメタデータに保存される
  - Diagnostics APIのレスポンスに`langfuse_trace_url`が含まれる

#### AC2.3: インデックス更新
- **Given**: 会話がValkeyに保存される
- **When**: `job_id`, `user_id`, `project_id`等のメタデータが指定される
- **Then**: `IndexManager`によりインデックスが更新され、フィルタ検索が可能になる

---

### Phase 3: Langfuse連携の強化

#### AC3.1: トレース生成の確認
- **Given**: Langfuse APIキーがmyVaultに設定されている
- **When**: チャットセッションでLLMを呼び出す
- **Then**:
  - Langfuseにトレースが送信される
  - `handler.last_trace_id`で取得した`trace_id`がValkeyに保存される

#### AC3.2: ヘルスチェックAPI
- **Given**: `/api/v1/observability/langfuse/health` エンドポイント
- **When**: GETリクエストを送信
- **Then**:
  - Langfuse連携の状態（enabled/disabled）
  - 最後のトレース送信時刻
  - 設定されているホストURL
  が返却される

#### AC3.3: 設定ガイドの整備
- **Given**: ユーザーがLangfuse Self-hostedを設定したい
- **When**: ドキュメントを参照
- **Then**:
  - myVaultへのAPIキー登録手順
  - 環境変数設定方法
  - 動作確認手順
  が記載されている

---

## 3. 機能要件

### Must Have（必須）

| ID | 機能 | 対象コンポーネント |
|----|------|-----------------|
| F1 | チャットAPIのValkeyストア移行 | `chat_endpoints.py`, `conversation_store.py` |
| F2 | trace_id生成・保存 | `chat_endpoints.py`, `langfuse_service.py` |
| F3 | デモデータ時のLangfuseリンク非表示 | `+page.svelte` |
| F4 | デモデータ使用中表示 | `+page.svelte` |

### Nice to Have（推奨）

| ID | 機能 | 対象コンポーネント |
|----|------|-----------------|
| F5 | Langfuseヘルスチェック API | `observability_endpoints.py` |
| F6 | Langfuse接続テストツール | CLI/API |
| F7 | 会話データの手動Valkey同期ツール | 管理スクリプト |

### Future Enhancement（将来拡張）

| ID | 機能 |
|----|------|
| F8 | Langfuse UI埋め込み（iframe） |
| F9 | トレース履歴のバッチ取得 |
| F10 | 自動アラート（トレース生成失敗時） |

---

## 4. 非機能要件

### パフォーマンス要件
- Valkey書き込みレイテンシ: < 50ms
- Diagnostics API応答時間: < 200ms（100件取得時）
- Langfuseへのトレース送信: 非同期（ユーザー応答をブロックしない）

### セキュリティ要件
- Langfuse APIキーはmyVaultで管理（平文保存禁止）
- Valkey接続情報はmyVaultから取得
- trace_urlはサニタイズしてXSS対策

### 可用性要件
- Valkey接続失敗時: 503 Service Unavailable を返却
- Langfuse無効時: トレーシングをスキップし、通常動作継続
- フェイルオープン設計（監視系の障害がメイン機能に影響しない）

### 互換性要件
- 既存の`ConversationStoreValkey`インターフェースを維持
- Diagnostics APIのレスポンス形式は変更なし
- 後方互換性のため、インメモリストアも一定期間サポート

---

## 5. 技術的制約

### 使用する技術スタック

| 領域 | 技術 |
|------|------|
| バックエンド | FastAPI, Python 3.11+ |
| 永続化 | Valkey (Redis互換) |
| Observability | Langfuse Self-hosted |
| フロントエンド | SvelteKit |
| シークレット管理 | myVault |

### 既存システムとの連携

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  myAgentDesk    │────▶│  expertAgent    │────▶│     Valkey      │
│  (フロントエンド) │     │  (API Server)   │     │   (永続化)      │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │    Langfuse     │
                        │  (Observability)│
                        └─────────────────┘
```

### データ形式

**Valkey保存形式:**
```json
{
  "conversation_id": "conv-xxx",
  "messages": [
    {"role": "user", "content": "...", "timestamp": "..."}
  ],
  "metadata": {
    "trace_id": "uuid-xxx",
    "user_id": "user-xxx",
    "job_id": "job-xxx",
    "created_at": "2025-12-08T00:00:00Z",
    "updated_at": "2025-12-08T00:00:00Z"
  }
}
```

---

## 6. リスクと対策

### 技術的リスク

| リスク | 影響 | 発生確率 | 対策 |
|--------|------|---------|------|
| Valkey移行時のデータロス | 高 | 低 | インメモリストアとの並行運用期間を設ける |
| Langfuse SDK互換性問題 | 中 | 中 | バージョン固定、E2Eテスト追加 |
| 既存チャット機能への影響 | 高 | 中 | 単体テスト・結合テストの徹底 |

### ビジネスリスク

| リスク | 影響 | 対策 |
|--------|------|------|
| 開発期間の超過 | 中 | Phase分割による段階的リリース |
| ユーザー混乱（デモデータと実データ） | 低 | UI/UXの明確化 |

### 対策案

1. **段階的マイグレーション**
   - Phase 1（FE改善）を先行リリース
   - Phase 2（BE統一）は十分なテスト後にリリース

2. **フィーチャーフラグ**
   - `USE_VALKEY_FOR_CHAT=true` で切り替え可能
   - 問題発生時に即座にロールバック

3. **監視強化**
   - Valkey書き込み成功率の監視
   - Langfuseトレース送信成功率の監視

---

## 7. 影響範囲

### 変更対象ファイル

| Phase | ファイル | 変更内容 |
|-------|---------|---------|
| 1 | `myAgentDesk/src/routes/mlops/diagnostics/+page.svelte` | デモデータ判定、リンク非表示 |
| 2 | `expertAgent/app/api/v1/chat_endpoints.py` | Valkeyストア使用に変更 |
| 2 | `expertAgent/app/services/conversation/conversation_store.py` | 非推奨化またはValkey委譲 |
| 2 | `expertAgent/app/services/langfuse_service.py` | trace_id取得ヘルパー追加 |
| 3 | `expertAgent/app/api/v1/observability_endpoints.py` | ヘルスチェックAPI追加 |
| 3 | `docs/design/langfuse-integration.md` | 設定ガイド新規作成 |

### テスト追加

| テスト種別 | 対象 | 件数（目安） |
|-----------|------|------------|
| 単体テスト | Valkeyストア移行 | 10件 |
| 結合テスト | Chat→Diagnosticsフロー | 5件 |
| 受入テスト | E2E（FE→BE→Valkey→Langfuse） | 3件 |

---

## 8. 関連Issue/PR

- #170 (MLOps UI実装) - CLOSED
- #193 (Job ID not found - 永続化問題) - CLOSED
- #169 (Valkey infrastructure) - 参照
- #113 (Langfuse Self-hosted統合) - 参照

---

## 9. 推奨アプローチ

1. **Phase 1を先行実施**（影響範囲が小さく即効性あり）
2. **Phase 2を本格実装**（ストレージ統一が最重要）
3. **Phase 3は任意**（ヘルスチェック・ドキュメント整備）

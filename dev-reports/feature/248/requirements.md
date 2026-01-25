# Issue #248 要件定義書

## 他サービスの接続情報の管理の myVault への集約

**作成日**: 2025-12-06
**Issue**: [#248](https://github.com/Kewton/MySwiftAgent/issues/248)
**ステータス**: Draft

---

## 現状分析

### 確認した現在のソースコード状態

| サービス | 設定項目 | 現在の管理場所 | myVault対応状態 |
|---------|---------|---------------|----------------|
| **Langfuse** | `LANGFUSE_PUBLIC_KEY` | myVault | ✅ 対応済み |
| **Langfuse** | `LANGFUSE_SECRET_KEY` | myVault | ✅ 対応済み |
| **Langfuse** | `LANGFUSE_HOST` | 環境変数 (.env) | ❌ 未対応 |
| **Valkey** | `VALKEY_HOST` | 環境変数 (.env) | ❌ 未対応 |
| **Valkey** | `VALKEY_PORT` | 環境変数 (.env) | ❌ 未対応 |
| **Valkey** | `VALKEY_DB` | 環境変数 (.env) | ❌ 未対応 |
| **Valkey** | `VALKEY_ENABLED` | 環境変数 (.env) | ❌ 未対応 |
| **Valkey** | `VALKEY_TTL` | 環境変数 (.env) | ❌ 未対応 |

### 既存インフラの状況

| コンポーネント | 状態 | 備考 |
|--------------|------|------|
| **myVault** | 稼働中 | プロジェクト/シークレット管理機能実装済み |
| **secrets_manager** | 稼働中 | myVault優先、環境変数フォールバック |
| **Langfuse API Keys** | myVault管理 | `langfuse_service.py` で `secrets_manager` 使用 |

### 現在の問題点

1. **設定の分散管理**:
   - APIキー → myVault
   - 接続情報 (HOST/PORT) → 環境変数
   - 開発環境ごとに複数箇所で設定変更が必要

2. **セキュリティリスク**:
   - 接続情報が `.env` ファイルに平文保存
   - 複数箇所での管理による漏洩リスク増加

3. **運用負荷**:
   - worktree ごとに `.env` の手動設定が必要
   - 環境切り替え時の設定ミスリスク

---

## 1. ユーザーストーリー

### US-1: 開発者としての Langfuse 設定集約
```
As a 開発者
I want to Langfuse の接続情報を myVault で一元管理したい
So that 開発環境ごとに設定を管理する手間を省き、設定ミスを防げる
```

### US-2: 開発者としての Valkey 設定集約
```
As a 開発者
I want to Valkey の接続情報を myVault で一元管理したい
So that 開発環境ごとに設定を管理する手間を省き、設定ミスを防げる
```

### US-3: ユーザーとしてのセキュリティ向上
```
As a ユーザー
I want to サービス接続情報を myVault で一元管理したい
So that 複数箇所での管理による情報漏洩リスクを低減できる
```

---

## 2. 受入条件（Acceptance Criteria）

### AC-1: Langfuse 接続情報の myVault 管理
- **Given**: myVault に `LANGFUSE_HOST` が登録されている
- **When**: expertAgent が起動する
- **Then**: myVault から `LANGFUSE_HOST` を取得して Langfuse に接続する

### AC-2: Valkey 接続情報の myVault 管理
- **Given**: myVault に Valkey 接続情報が登録されている
- **When**: expertAgent が起動する
- **Then**: myVault から接続情報を取得して Valkey に接続する

### AC-3: 環境変数フォールバック
- **Given**: myVault に接続情報が未登録の場合
- **When**: expertAgent が起動する
- **Then**: 環境変数から接続情報を取得してサービスに接続する（後方互換性維持）

### AC-4: プロジェクト別設定
- **Given**: myVault に複数プロジェクトが存在する
- **When**: 特定プロジェクトを指定して接続情報を取得する
- **Then**: そのプロジェクトに紐づく接続情報が返される

### AC-5: CommonUI からの設定管理
- **Given**: CommonUI（myAgentDesk）の設定画面を開いている
- **When**: Langfuse/Valkey の接続情報を入力・保存する
- **Then**: myVault に接続情報が保存され、サービスが利用可能になる

---

## 3. 機能要件

### 3.1 必須機能（Must Have）

| ID | 要件 | 詳細 |
|----|------|------|
| M-1 | Langfuse HOST の myVault 管理 | `LANGFUSE_HOST` を myVault から取得 |
| M-2 | Valkey 接続情報の myVault 管理 | `VALKEY_HOST`, `VALKEY_PORT`, `VALKEY_DB` を myVault から取得 |
| M-3 | 環境変数フォールバック | myVault 未登録時は環境変数から取得（後方互換性） |
| M-4 | secrets_manager 拡張 | 接続情報（非シークレット）の取得サポート |

### 3.2 あると良い機能（Nice to Have）

| ID | 要件 | 詳細 |
|----|------|------|
| N-1 | CommonUI 設定画面 | myAgentDesk から接続情報を登録・編集 |
| N-2 | 接続テスト機能 | 登録した接続情報でサービスへの接続をテスト |
| N-3 | 設定のインポート/エクスポート | `.env` ファイルから myVault への一括インポート |

### 3.3 将来的な拡張（Future Enhancement）

| ID | 要件 | 詳細 |
|----|------|------|
| F-1 | JobQueue 接続情報管理 | `JOBQUEUE_API_URL` 等の myVault 管理 |
| F-2 | myScheduler 接続情報管理 | スケジューラー接続情報の myVault 管理 |
| F-3 | graphAiServer 接続情報管理 | ワークフロー実行サーバー接続情報の myVault 管理 |
| F-4 | 設定の暗号化 | 接続情報も暗号化して保存（現在シークレットのみ暗号化） |

---

## 4. 非機能要件

### 4.1 パフォーマンス要件
- myVault からの接続情報取得: **10ms 以下**
- キャッシュ TTL: **300秒**（既存の `SECRETS_CACHE_TTL` を利用）

### 4.2 セキュリティ要件
- 接続情報は myVault の暗号化ストレージに保存
- myVault API 通信は HTTPS（本番環境）
- 接続情報のログ出力時はマスキング

### 4.3 可用性要件
- myVault 接続不可時は環境変数フォールバック（Graceful Degradation）
- サービス起動時に myVault 接続失敗でもアプリケーション起動可能

### 4.4 互換性要件
- 既存の `.env` ファイルによる設定を引き続きサポート
- myVault 未使用環境でも動作可能

---

## 5. 技術的制約

### 5.1 使用する技術スタック

| カテゴリ | 技術 | 備考 |
|---------|------|------|
| **シークレット管理** | myVault | 既存インフラ活用 |
| **クライアント** | `secrets_manager` | 既存実装を拡張 |
| **キャッシュ** | インメモリ (dict) | 既存キャッシュ機構を利用 |

### 5.2 既存システムとの連携

```
┌─────────────────────────────────────────────────────────────────────────┐
│                             expertAgent                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │                      secrets_manager                                 ││
│  │  ┌─────────────────────────────────────────────────────────────────┐││
│  │  │  get_secret() / get_connection_config()                         │││
│  │  │                                                                 │││
│  │  │  1. Check myVault (priority)                                    │││
│  │  │     └── LANGFUSE_HOST, VALKEY_HOST, VALKEY_PORT, etc.          │││
│  │  │                                                                 │││
│  │  │  2. Fallback to environment variables                           │││
│  │  │     └── .env / .env.local                                       │││
│  │  └─────────────────────────────────────────────────────────────────┘││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                   │                                      │
│                                   ▼                                      │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐   │
│  │ langfuse_service │  │   ValkeyClient   │  │  Other Services      │   │
│  └──────────────────┘  └──────────────────┘  └──────────────────────┘   │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ HTTP API
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                              myVault                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │  Project: default_project                                           ││
│  │  ├── LANGFUSE_PUBLIC_KEY (既存)                                      ││
│  │  ├── LANGFUSE_SECRET_KEY (既存)                                      ││
│  │  ├── LANGFUSE_HOST (新規)                                            ││
│  │  ├── VALKEY_HOST (新規)                                              ││
│  │  ├── VALKEY_PORT (新規)                                              ││
│  │  ├── VALKEY_DB (新規)                                                ││
│  │  └── VALKEY_TTL (新規)                                               ││
│  └─────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────┘
```

### 5.3 myVault キー設計

#### 新規追加するシークレット

| キー名 | 値の例 | 説明 |
|-------|-------|------|
| `LANGFUSE_HOST` | `http://localhost:3001` | Langfuse Self-hosted URL |
| `VALKEY_HOST` | `localhost` | Valkey ホスト名 |
| `VALKEY_PORT` | `6379` | Valkey ポート番号 |
| `VALKEY_DB` | `0` | Valkey データベース番号 |
| `VALKEY_TTL` | `86400` | Valkey TTL（秒） |

#### キー命名規則

```
{SERVICE}_{CONFIG_TYPE}

例:
- LANGFUSE_HOST      → Langfuse の接続先ホスト
- VALKEY_HOST        → Valkey の接続先ホスト
- VALKEY_PORT        → Valkey のポート番号
```

---

## 6. リスクと対策

### 6.1 技術的リスク

| リスク | 影響度 | 発生確率 | 対策 |
|-------|--------|---------|------|
| myVault 接続失敗 | 中 | 低 | 環境変数フォールバックで Graceful Degradation |
| 設定値の型変換エラー | 中 | 中 | `secrets_manager` で型変換サポート（int, bool） |
| キャッシュ不整合 | 低 | 低 | 設定変更時の手動キャッシュクリア機能 |
| 既存テストの破損 | 中 | 中 | モックで myVault 依存を分離 |

### 6.2 ビジネスリスク

| リスク | 影響度 | 発生確率 | 対策 |
|-------|--------|---------|------|
| 既存環境での動作不良 | 高 | 低 | 環境変数フォールバックで後方互換性維持 |
| 設定移行時の漏れ | 中 | 中 | 移行チェックリスト・インポート機能 |

---

## 7. 解決策オプションの比較

### Option 1: secrets_manager 拡張（推奨）

| 項目 | 評価 |
|------|------|
| **実現可能性** | 高い - 既存の `secrets_manager` を拡張 |
| **メリット** | 既存パターンの再利用、最小限のコード変更 |
| **デメリット** | シークレットと接続情報が同一 API で管理される |
| **工数見積** | 小（2-3日） |

### Option 2: 専用 ConnectionConfigManager 新設

| 項目 | 評価 |
|------|------|
| **実現可能性** | 高い |
| **メリット** | 関心の分離、シークレットと接続情報を明確に区別 |
| **デメリット** | 新規実装コスト、二重管理のリスク |
| **工数見積** | 中（4-5日） |

### Option 3: myVault スキーマ拡張（接続情報専用テーブル）

| 項目 | 評価 |
|------|------|
| **実現可能性** | 中程度 - myVault のスキーマ変更が必要 |
| **メリット** | データモデルとして明確、将来の拡張性高い |
| **デメリット** | myVault 側の変更が必要、マイグレーション対応 |
| **工数見積** | 大（1週間以上） |

### 推奨: Option 1 - secrets_manager 拡張

**理由:**
1. 既存の `secrets_manager` パターンをそのまま活用可能
2. myVault 側の変更が不要
3. 最小限のコード変更で実現可能
4. 後方互換性を容易に維持

---

## 8. 実装方針

### 8.1 secrets_manager の拡張

```python
# expertAgent/core/secrets.py に追加

def get_connection_config(
    self,
    key: str,
    project: Optional[str] = None,
    *,
    default: Optional[str] = None,
    value_type: type = str,
) -> Any:
    """Get connection configuration with type conversion.

    Args:
        key: Config key name (e.g., "VALKEY_PORT")
        project: Optional project name
        default: Default value if not found
        value_type: Type to convert value to (str, int, bool)

    Returns:
        Configuration value with appropriate type
    """
    try:
        value = self.get_secret(key, project)
        return self._convert_type(value, value_type)
    except ValueError:
        if default is not None:
            return default
        raise
```

### 8.2 サービス初期化の変更

```python
# expertAgent/app/main.py の変更例

from core.secrets import secrets_manager

# Valkey 接続情報を myVault から取得
valkey_host = secrets_manager.get_connection_config(
    "VALKEY_HOST", default=settings.VALKEY_HOST
)
valkey_port = secrets_manager.get_connection_config(
    "VALKEY_PORT", default=settings.VALKEY_PORT, value_type=int
)
```

---

## 9. 影響範囲

### 変更が必要なファイル

| ファイル | 変更内容 |
|---------|---------|
| `expertAgent/core/secrets.py` | `get_connection_config()` メソッド追加 |
| `expertAgent/app/main.py` | Valkey 接続情報の取得を myVault 優先に変更 |
| `expertAgent/app/services/langfuse_service.py` | `LANGFUSE_HOST` の取得を myVault 優先に変更 |
| `expertAgent/app/api/v1/ab_test_endpoints.py` | Valkey 接続情報の取得を変更 |
| `expertAgent/app/api/v1/diagnostic_endpoints.py` | Valkey 接続情報の取得を変更 |

### テスト追加

| テストファイル | テスト内容 |
|--------------|-----------|
| `tests/unit/test_secrets_connection_config.py` | `get_connection_config()` の単体テスト |
| `tests/integration/test_myvault_connection_config.py` | myVault 連携の結合テスト |

---

## 10. 次のステップ

1. **設計レビュー**: この要件定義の承認
2. **Issue分割**: `/issue-split` でサブIssueに分割
3. **TDD開発**: `/tdd-impl` で実装開始

---

## 関連ドキュメント

- [Issue #248](https://github.com/Kewton/MySwiftAgent/issues/248)
- `expertAgent/core/secrets.py` - 既存の secrets_manager 実装
- `myVault/app/schemas/secret.py` - myVault シークレットスキーマ
- `docs/design/myvault-integration.md` - myVault 連携設計

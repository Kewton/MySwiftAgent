# 作業計画書: Issue #253 - Langfuse HOST の myVault 対応

## Issue 概要

| 項目 | 内容 |
|------|------|
| **Issue番号** | #253 |
| **タイトル** | Langfuse HOST の myVault 対応 |
| **親Issue** | #248 |
| **サイズ** | XS (1 Story Point) |
| **作業見積** | 1時間 |
| **優先度** | High |
| **依存Issue** | #250（完了済み ✅） |

## 現状分析

### 対象ファイル

| ファイル | 現状 | 変更内容 |
|----------|------|----------|
| `expertAgent/app/services/langfuse_service.py:74` | `settings.LANGFUSE_HOST` を直接使用 | `secrets_manager.get_connection_config()` に変更 |
| `expertAgent/myvault_secrets.yaml:24` | `LANGFUSE_HOST` 定義済み ✅ | 変更不要 |

### 依存コード（利用可能）

```python
# SecretsManager.get_connection_config() - 既に実装済み (PR #259)
secrets_manager.get_connection_config(
    key="LANGFUSE_HOST",
    value_type=str,
    default="http://localhost:3001"
)
```

## 詳細タスク分解

### Phase 1: 実装（30分）

| Task | 内容 | 所要時間 | 成果物 |
|------|------|----------|--------|
| **1.1** | `langfuse_service.py` の HOST 取得を `get_connection_config()` 使用に変更 | 15分 | `langfuse_service.py` |
| **1.2** | インポート文の確認・調整 | 5分 | `langfuse_service.py` |

### Phase 2: テスト（20分）

| Task | 内容 | 所要時間 | 成果物 |
|------|------|----------|--------|
| **2.1** | 既存テスト実行・パス確認 | 10分 | テスト結果 |
| **2.2** | myVault フォールバックテストケース追加（必要に応じて） | 10分 | `test_langfuse_service.py` |

### Phase 3: 品質チェック（10分）

| Task | 内容 | 所要時間 | 成果物 |
|------|------|----------|--------|
| **3.1** | Ruff/MyPy 静的解析 | 5分 | エラーゼロ確認 |
| **3.2** | pre-push-check.sh 実行 | 5分 | 全チェックパス |

## 実装内容

### 変更前 (langfuse_service.py:60-83)

```python
def _initialize_client(self) -> None:
    try:
        public_key = secrets_manager.get_secret("LANGFUSE_PUBLIC_KEY")
        secret_key = secrets_manager.get_secret("LANGFUSE_SECRET_KEY")

        self._client = Langfuse(
            secret_key=secret_key,
            public_key=public_key,
            host=settings.LANGFUSE_HOST,  # ← 環境変数直接参照
        )
```

### 変更後

```python
def _initialize_client(self) -> None:
    try:
        public_key = secrets_manager.get_secret("LANGFUSE_PUBLIC_KEY")
        secret_key = secrets_manager.get_secret("LANGFUSE_SECRET_KEY")

        # myVault 優先、環境変数フォールバック
        langfuse_host = secrets_manager.get_connection_config(
            "LANGFUSE_HOST",
            value_type=str,
            default=settings.LANGFUSE_HOST,
        )

        self._client = Langfuse(
            secret_key=secret_key,
            public_key=public_key,
            host=langfuse_host,
        )
```

## 受入基準チェックリスト

### 自動検証可能な基準

| 基準 | 検証方法 |
|------|----------|
| myVault に `LANGFUSE_HOST` がある場合、その値で Langfuse に接続 | 単体テスト |
| myVault に値がない場合、環境変数 `LANGFUSE_HOST` を使用 | 単体テスト |
| Ruff/MyPy エラーゼロ | `uv run ruff check && uv run mypy` |
| 既存テスト全パス | `uv run pytest` |

### 手動検証が必要な基準

| 基準 | 検証方法 |
|------|----------|
| Langfuse ダッシュボードでトレースが表示される | 開発環境で動作確認 |
| myVault 設定変更後、サービス再起動で新設定が反映される | 手動確認 |

## Definition of Done

- [x] 依存Issue #250 完了確認
- [ ] `langfuse_service.py` の HOST 取得を `get_connection_config()` 使用に変更
- [ ] myVault に `LANGFUSE_HOST` を登録（手動、ユーザー確認）
- [ ] 単体テストパス
- [ ] 静的解析エラーゼロ
- [ ] CI/CDグリーン
- [ ] コードレビュー承認

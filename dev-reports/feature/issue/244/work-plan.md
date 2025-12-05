# Issue #244 作業計画書
## expertAgent main.py で JobCreationStateManager の Valkey 接続初期化

---

## 1. Issue概要

```markdown
## Issue: expertAgent main.py で JobCreationStateManager の Valkey 接続初期化
**Issue番号**: #244
**サイズ**: S (2 Story Points)
**作業見積**: 2-3時間
**優先度**: High
**依存Issue**: #239（Valkey統合実装）- 完了済み
**親Issue**: #193（Marp Report永続化）
```

---

## 2. 詳細タスク分解

### Phase 1: 実装タスク

#### Task 1.1: JobCreationStateManager 公開メソッド追加
- **所要時間**: 20分
- **成果物**: `expertAgent/app/services/job_creation_state.py`
- **依存**: なし
- **内容**:
  - `configure_valkey(client, ttl_seconds)` メソッド追加
  - `is_valkey_connected` プロパティ追加

#### Task 1.2: main.py lifespan Valkey初期化
- **所要時間**: 30分
- **成果物**: `expertAgent/app/main.py`
- **依存**: Task 1.1
- **内容**:
  - インポート追加（job_state_manager, ValkeyClient, settings）
  - lifespan startup で Valkey 接続初期化
  - lifespan shutdown で Valkey 切断

#### Task 1.3: /health エンドポイント拡張
- **所要時間**: 15分
- **成果物**: `expertAgent/app/main.py`
- **依存**: Task 1.1
- **内容**:
  - 戻り値の型を `dict[str, Any]` に変更
  - `valkey.enabled`, `valkey.connected` を追加

### Phase 2: テストタスク

#### Task 2.1: 単体テスト - configure_valkey
- **所要時間**: 30分
- **成果物**: `expertAgent/tests/unit/test_job_creation_state.py`
- **依存**: Task 1.1
- **テストケース**:
  - configure_valkey でクライアントが設定されること
  - configure_valkey で TTL が設定されること
  - is_valkey_connected が正しく動作すること

#### Task 2.2: 単体テスト - health エンドポイント
- **所要時間**: 20分
- **成果物**: `expertAgent/tests/unit/test_main_health.py`（または既存ファイルに追加）
- **依存**: Task 1.3
- **テストケース**:
  - /health が valkey 状態を含むこと
  - Valkey無効時は connected=False

#### Task 2.3: 静的解析・品質チェック
- **所要時間**: 10分
- **成果物**: なし（CI準備）
- **依存**: Task 1.1, 1.2, 1.3
- **内容**:
  - `uv run ruff check .`
  - `uv run mypy .`
  - 既存テスト実行

### Phase 3: 検証・完了タスク

#### Task 3.1: E2Eテスト（ローカル検証）
- **所要時間**: 20分
- **成果物**: 検証ログ
- **依存**: Phase 1, Phase 2 完了
- **内容**:
  - Valkey起動状態でアプリ起動確認
  - `/health` エンドポイント確認
  - ログ出力確認

#### Task 3.2: PR作成
- **所要時間**: 15分
- **成果物**: GitHub Pull Request
- **依存**: Task 3.1
- **内容**:
  - コミットメッセージ作成
  - PR説明文作成
  - レビュー依頼

---

## 3. タスク依存関係

```
┌─────────────────────────────────────────────────────────────────┐
│                      Phase 1: 実装                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌──────────────┐                                              │
│   │  Task 1.1    │                                              │
│   │ 公開メソッド │                                              │
│   │   (20分)     │                                              │
│   └──────┬───────┘                                              │
│          │                                                       │
│          ├──────────────────┬───────────────────┐               │
│          ▼                  ▼                   │               │
│   ┌──────────────┐   ┌──────────────┐          │               │
│   │  Task 1.2    │   │  Task 1.3    │          │               │
│   │  lifespan    │   │   /health    │          │               │
│   │   (30分)     │   │   (15分)     │          │               │
│   └──────────────┘   └──────────────┘          │               │
│                                                 │               │
└─────────────────────────────────────────────────│───────────────┘
                                                  │
┌─────────────────────────────────────────────────│───────────────┐
│                      Phase 2: テスト            │               │
├─────────────────────────────────────────────────│───────────────┤
│          ┌──────────────────────────────────────┘               │
│          │                                                       │
│          ▼                                                       │
│   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐       │
│   │  Task 2.1    │   │  Task 2.2    │   │  Task 2.3    │       │
│   │ 単体テスト   │   │ healthテスト │   │  静的解析    │       │
│   │   (30分)     │   │   (20分)     │   │   (10分)     │       │
│   └──────┬───────┘   └──────┬───────┘   └──────┬───────┘       │
│          │                  │                  │                │
└──────────│──────────────────│──────────────────│────────────────┘
           │                  │                  │
           └──────────────────┼──────────────────┘
                              │
┌─────────────────────────────│───────────────────────────────────┐
│                      Phase 3: 検証・完了                         │
├─────────────────────────────│───────────────────────────────────┤
│                              ▼                                   │
│                       ┌──────────────┐                          │
│                       │  Task 3.1    │                          │
│                       │  E2Eテスト   │                          │
│                       │   (20分)     │                          │
│                       └──────┬───────┘                          │
│                              │                                   │
│                              ▼                                   │
│                       ┌──────────────┐                          │
│                       │  Task 3.2    │                          │
│                       │   PR作成     │                          │
│                       │   (15分)     │                          │
│                       └──────────────┘                          │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘

総作業時間: 約2時間30分
```

---

## 4. 作業スケジュール

### 単一セッション（推奨）

| 時間 | タスク | 成果物 |
|------|--------|--------|
| 0:00-0:20 | Task 1.1: 公開メソッド追加 | job_creation_state.py |
| 0:20-0:50 | Task 1.2: lifespan 修正 | main.py |
| 0:50-1:05 | Task 1.3: /health 拡張 | main.py |
| 1:05-1:35 | Task 2.1: 単体テスト（configure_valkey） | test_job_creation_state.py |
| 1:35-1:55 | Task 2.2: 単体テスト（health） | test_main_health.py |
| 1:55-2:05 | Task 2.3: 静的解析 | - |
| 2:05-2:25 | Task 3.1: E2Eテスト | 検証ログ |
| 2:25-2:40 | Task 3.2: PR作成 | GitHub PR |

**総作業時間**: 約2時間40分

---

## 5. チェックポイント

| タイミング | 確認事項 | 対応 |
|-----------|---------|------|
| Task 1.1完了時 | メソッド追加後の型チェック | `uv run mypy app/services/job_creation_state.py` |
| Task 1.2完了時 | アプリ起動確認（Valkey無効） | `VALKEY_ENABLED=false uv run uvicorn ...` |
| Task 1.3完了時 | /health レスポンス確認 | `curl http://localhost:8104/health` |
| Phase 2完了時 | 全テスト通過 | `uv run pytest tests/unit/` |
| PR作成前 | CI/CDパス確認 | `./scripts/pre-push-check.sh` |

---

## 6. リスクと対策

| リスク | 発生確率 | 影響 | 対策 |
|-------|---------|------|------|
| 既存テストの失敗 | 低 | 修正に30分追加 | 変更前にテスト実行確認 |
| MyPy型エラー | 中 | 修正に15分追加 | 型アノテーション慎重に記述 |
| Valkey接続テストの環境依存 | 中 | E2Eテスト不可 | モックテストで代替 |
| main.pyのインポート循環 | 低 | 修正に20分追加 | TYPE_CHECKING使用 |

---

## 7. 成果物チェックリスト

### コード

- [ ] `expertAgent/app/services/job_creation_state.py`
  - [ ] `configure_valkey()` メソッド
  - [ ] `is_valkey_connected` プロパティ
- [ ] `expertAgent/app/main.py`
  - [ ] インポート追加
  - [ ] lifespan Valkey初期化
  - [ ] /health エンドポイント拡張

### テスト

- [ ] `expertAgent/tests/unit/test_job_creation_state.py`
  - [ ] test_configure_valkey
  - [ ] test_is_valkey_connected
- [ ] `expertAgent/tests/unit/test_main_health.py`（または既存に追加）
  - [ ] test_health_includes_valkey_status

### ドキュメント

- [ ] PR説明文（受入条件のチェックリスト含む）

---

## 8. Definition of Done

Issue完了条件：

- [ ] `JobCreationStateManager.configure_valkey()` メソッドが実装されている
- [ ] `JobCreationStateManager.is_valkey_connected` プロパティが実装されている
- [ ] `main.py` lifespan で Valkey 接続初期化が実装されている
- [ ] `VALKEY_ENABLED=true` 時に L2 キャッシュが有効化される
- [ ] Valkey 接続失敗時もアプリケーションが起動する
- [ ] `/health` エンドポイントが Valkey 状態を返す
- [ ] Ruff/MyPy エラーゼロ
- [ ] 既存テストがパス
- [ ] 新規メソッドの単体テストがパス
- [ ] コードレビュー承認
- [ ] develop ブランチにマージ

---

## 9. コマンドリファレンス

### 開発環境

```bash
# worktree に移動（既に作成済みの場合）
cd ~/MySwiftAgent-worktrees/fix-issue-244

# 依存関係インストール
cd expertAgent && uv sync

# 開発サーバー起動（Valkey無効）
VALKEY_ENABLED=false uv run uvicorn app.main:app --reload --port 8554

# 開発サーバー起動（Valkey有効）
VALKEY_ENABLED=true VALKEY_HOST=localhost VALKEY_PORT=6379 uv run uvicorn app.main:app --reload --port 8554
```

### テスト

```bash
# 単体テスト
uv run pytest tests/unit/test_job_creation_state.py -v

# 全単体テスト
uv run pytest tests/unit/ -v

# カバレッジ
uv run pytest tests/unit/ --cov=app --cov-report=term-missing
```

### 品質チェック

```bash
# Ruff
uv run ruff check app/ tests/

# MyPy
uv run mypy app/

# フォーマット
uv run ruff format app/ tests/

# 全チェック（pre-push）
./scripts/pre-push-check.sh
```

### 検証

```bash
# /health 確認
curl -s http://localhost:8554/health | jq

# Valkey接続状態確認
curl -s http://localhost:8554/health | jq '.valkey'
```

---

## 10. 次のアクション

作業計画承認後：

1. **worktree移動**: `cd ~/MySwiftAgent-worktrees/fix-issue-244`
2. **ブランチ確認**: `git branch` → `fix/issue/240`（既に作成済み）
3. **タスク実行**: Phase 1 → Phase 2 → Phase 3 の順で実装
4. **PR作成**: `/pm-create-pr` で Pull Request 作成
5. **進捗報告**: 必要に応じて `/progress-report` で報告

---

## 11. 関連ドキュメント

| ドキュメント | パス |
|-------------|------|
| 要件定義書 | [requirements.md](./requirements.md) |
| 設計方針書 | [design-policy.md](./design-policy.md) |
| アーキテクチャレビュー | [architecture-review.md](./architecture-review.md) |
| 親Issue設計 | [../193/design-policy.md](../193/design-policy.md) |

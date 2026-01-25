# 🛡️ 品質基準と開発環境

## 🐍 Python開発環境

### 環境構築ツール

- **[uv](https://docs.astral.sh/uv/)** を標準の依存関係管理・仮想環境ツールとして採用
- 従来の `pip` + `venv` / `poetry` / `pipenv` は使用しない

### セットアップ手順

```bash
# 1. uvのインストール (初回のみ)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. プロジェクトの依存関係同期
uv sync

# 3. 開発サーバー起動
uv run uvicorn app.main:app --reload

# 4. テスト実行
uv run pytest

# 5. 静的解析・フォーマット
uv run ruff check .
uv run ruff format .
uv run mypy .
```

### プロジェクト構成

```
pyproject.toml          # プロジェクト設定・依存関係
.python-version         # Python版数指定
uv.lock                 # ロックファイル (自動生成)
app/                    # アプリケーションコード
├── main.py            # FastAPIエントリーポイント
├── core/              # コア機能 (設定、DB、ワーカー)
├── models/            # データベースモデル
├── schemas/           # Pydanticスキーマ
└── api/               # APIエンドポイント
tests/                  # テストコード
├── unit/              # 単体テスト
├── integration/       # 結合テスト
└── conftest.py        # テスト設定
```

## 🛡️ 品質担保方針

### 原理原則

下記の原理原則に従いコード品質を担保すること

- **SOLID**
  - Single Responsibility Principle (単一責任原則)
  - Open-Closed Principle (開放/閉鎖原則)
  - Liskov Substitution Principle (リスコフの置換原則)
  - Interface Segregation Principle (インターフェース分離の原則)
  - Dependency Inversion Principle (依存性逆転の原則)
- **KISS**
  - Keep It Simple, Stupid
- **YAGNI**
  - You Aren't Gonna Need It
- **DRY**
  - Don't Repeat Yourself

### 静的解析・コード品質

| ツール | 用途 | 設定ファイル | 実行コマンド |
|--------|------|-------------|--------------|
| **Ruff** | Linting + Formatting | `pyproject.toml` | `uv run ruff check .` <br> `uv run ruff format .` |
| **MyPy** | 型チェック | `pyproject.toml` | `uv run mypy .` |

### テスト方針

| テストレベル | 対象 | フレームワーク | カバレッジ目標 | 根拠 |
|-------------|------|-------------|--------------|------|
| **単体テスト (Unit Tests)** | 個別関数・クラス・内部ロジック | pytest | **90%以上** | 内部ロジックの詳細な検証が目的。全パス・全分岐を網羅する |
| **結合テスト (Integration Tests)** | API エンドポイント・統合フロー | pytest + httpx | **50%以上** | エンドポイントの動作確認が主目的。内部ロジックは単体テストでカバー済み |

#### カバレッジ要件の設計思想

**単体テスト (90%要件)**:
- **目的**: 個別関数・クラスの内部ロジックを詳細に検証
- **対象**: ビジネスロジック、ユーティリティ関数、データ処理、エラーハンドリング
- **実行**: `uv run pytest tests/unit/` で実行
- **pyproject.toml設定**: `--cov-fail-under=90` でデフォルト90%を強制

**結合テスト (50%要件)**:
- **目的**: APIエンドポイントの動作確認、統合フロー検証
- **対象**: HTTPリクエスト/レスポンス、認証、エンドポイント間の連携
- **測定範囲**: `--cov=app` でAPIレイヤー (`app/`) のみ測定（`core/` は除外）
- **実行**: `uv run pytest tests/integration/ --cov=app --cov-fail-under=50` で実行（cd-develop.yml）
- **カバレッジが低い理由**:
  - 内部ロジック (`core/`) は既に単体テストで100%近くカバー済み
  - 結合テストはエンドポイント呼び出しのみ実行するため、全コードパスを通らない
  - APIレイヤーのみ測定することで、結合テストの本質（エンドポイント動作確認）に焦点を絞る
  - 低いしきい値（50%）でも統合フロー検証の目的は十分達成できる

**CI/CDでの運用**:
- **Feature/Fix PR (ci-feature.yml)**: 単体テスト + 結合テスト両方実行（90%要件適用）
- **Develop統合 (cd-develop.yml)**:
  - 単体テスト: 90%要件（`--cov=app --cov=core` で全体測定）
  - 結合テスト: 50%要件（`--cov=app` でAPIレイヤーのみ測定、`--cov-fail-under=50`）
- **最終品質保証**: 単体テストと結合テストを組み合わせて全体で90%以上を確保

### テスト階層（Test Pyramid）

| Level | テスト種別 | 場所 | 実行環境 | カバレッジ | 特徴 |
|-------|-----------|------|---------|-----------|------|
| **L1** | 単体テスト | `{project}/tests/unit/` | CI | 90%+ | 高速、モック多用 |
| **L2** | 結合テスト | `tests/integration/` | CI | 50%+ | API間通信、DB接続 |
| **L3** | 受入テスト（開発者） | `tests/acceptance/` | ローカル | - | APIキー必要、E2E |
| **L4** | 受入テスト（PO） | - | 手動 | - | UX/UI検証 |

```
                    +-------------+
                   /|    L4 PO    |\        <- 手動確認
                  / |    受入     | \
                 /  +-------------+  \
                /   +-------------+   \
               /    |  L3 開発者  |    \    <- ローカル実行
              /     |    受入     |     \
             /      +-------------+      \
            /      +---------------+      \
           /       |   L2 結合    |       \ <- CI実行
          /        +---------------+        \
         /        +-------------------+      \
        /         |     L1 単体      |       \ <- CI実行
       /          +-------------------+        \
      ------------------------------------------------
```

### 受入テストのスキップ条件

以下のラベルが付与されたPRは、L3/L4受入テストをスキップできます：

| ラベル | 説明 | 例 |
|-------|------|-----|
| `docs-only` | ドキュメントのみの変更 | README更新、仕様書修正 |
| `internal` | 内部リファクタリング | コード整理、変数名変更 |
| `test-only` | テストコードのみの変更 | テスト追加、テスト修正 |
| `ci-only` | CI/CD設定のみの変更 | ワークフロー修正 |

> **注意**: ユーザー影響がある変更（機能追加、バグ修正、UI変更）は
> 必ずL3またはL4の受入テストを実施してください。

### PO受入テスト（L4）が必要なPR

以下の条件に該当するPRは、PO（プロダクトオーナー）による手動受入テストが必要です：

**必須条件**:
- UI/UXに影響する変更
- 新機能の追加
- ユーザーフローの変更
- エラーメッセージの変更
- 課金・認証に関わる変更

**判定フロー**:
```
PRの変更内容
    |
    v
ユーザーに見える変更か？
    |
    +-- Yes --> L4 PO受入テスト必要
    |
    +-- No  --> L3 開発者受入テストのみ
```

### 必須チェック項目

**PRマージ前の必須確認事項：**

```bash
# 1. 全テストが通過すること
uv run pytest --cov=app --cov-report=term-missing

# 2. 静的解析エラーがないこと
uv run ruff check .
uv run mypy .

# 3. コードフォーマットが適用済みであること
uv run ruff format . --check

# 4. アプリケーションが正常に起動すること
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### CI/CD との連携

GitHub Actions で以下を自動実行：

1. **品質チェック** - Linting, 型チェック, フォーマット確認
2. **テスト実行** - 単体・結合テスト + カバレッジ測定
3. **セキュリティ監査** - 脆弱性スキャン
4. **ビルド検証** - アプリケーション起動確認
5. **🔄 バージョン管理自動化** - セマンティックリリース、タグ作成、GitHub Release

#### 📋 自動化されるバージョン管理フロー

| トリガー | 自動実行内容 | 対象ワークフロー |
|---------|-------------|----------------|
| **PR → `develop`** | ラベル検証、コンベンショナルコミットチェック | `conventional-commits.yml` |
| **PR → `main` (merged)** | pyproject.toml バージョンバンプ、GitHub Release作成 | `auto-release.yml` |
| **`release/*` push** | リリース候補検証、自動デプロイトリガー | `multi-release.yml` |
| **GitHub Release published** | 本番・ステージング自動デプロイ | `deploy-on-release.yml` |

### パフォーマンス・セキュリティ

- **HTTP タイムアウト**: 適切な上限設定（デフォルト30秒）
- **レスポンスサイズ制限**: デフォルト1MB、設定可能
- **リクエスト検証**: Pydantic による厳密なスキーマ検証
- **エラーハンドリング**: 機密情報の漏洩防止

## ログ設定（マルチワーカー対応）

全Pythonプロジェクトは統一されたログ設定方針に従います。

### **基本方針**

- ✅ **`logging.basicConfig(force=True)`を使用**: マルチワーカー環境で正常動作
- ✅ **プロジェクト固有のログファイル名**: `{プロジェクト名}.log` で管理
- ✅ **3種類のハンドラー**: StreamHandler（コンソール）、RotatingFileHandler（メインログ）、TimedRotatingFileHandler（エラーログ）
- ✅ **統一フォーマット**: `[%(process)d-%(thread)d]-%(asctime)s-%(levelname)s-%(message)s`

### **ログファイル命名規則**

| プロジェクト | ログファイル名 | エラーログファイル名 |
|------------|-------------|------------------|
| expertAgent | `expertagent.log` | `expertagent_rotation.log` |
| jobqueue | `jobqueue.log` | `jobqueue_rotation.log` |
| myscheduler | `myscheduler.log` | `myscheduler_rotation.log` |
| myVault | `myvault.log` | `myvault_rotation.log` |

### **推奨ワーカー数**

| プロジェクト | ワーカー数 | 理由 |
|------------|----------|------|
| expertAgent | 4 | LLM APIコールが多く並列処理が効果的 |
| jobqueue | 4 | 非同期ジョブ実行で並列度を高める |
| myscheduler | 1 | APSchedulerはシングルプロセス推奨 |
| myVault | 1 | SQLite使用のためシングルプロセス |

### **環境変数設定**

`.env`ファイルで以下を設定:

```bash
LOG_LEVEL=DEBUG  # 開発時はDEBUG、本番時はINFO
LOG_DIR=./logs   # ログ出力ディレクトリ
```

### **詳細ドキュメント**

ログ設定の詳細は [logging-policy.md](../design/logging-policy.md) を参照してください。

## 🤖 AI開発支援・コード生成時の注意事項

### Claude Code 利用時のルール

1. **品質第一**: 生成されたコードも手動コードと同等の品質基準を適用
2. **テスト必須**: AI生成コードには特に包括的なテストを作成
3. **レビュー強化**: AI生成部分は人間による詳細レビューを実施
4. **セキュリティ重視**: 外部API呼び出し、認証まわりは特に慎重に検証
5. **ドキュメント更新**: 生成されたコードに対応する仕様書・READMEの更新
6. **🏷️ PRラベル必須**: AI生成PR も適切なセマンティックバージョニングラベルを付与

### 推奨フロー（自動化対応）

```
AI生成 → 静的解析 → テスト作成 → 🏷️ PRラベル付与 → 手動レビュー → PR作成 → 🔄 自動バージョン管理
```

### 🎯 AI開発時のバージョン管理指針

- **`vibe/*` ブランチ**: 実験的機能開発時も本番品質を維持し、適切なラベル付与
- **破壊的変更**: AIによるリファクタリングでAPI変更が生じる場合は `breaking` ラベル必須
- **機能追加**: 新機能実装時は `feature` ラベルでminor版数アップ
- **バグ修正**: AI による不具合修正は `fix` ラベルでpatch版数アップ

---

[← ブランチ戦略](./03-branch-strategy.md) | [CLAUDE.md](../../CLAUDE.md) | [次: 並列開発環境 →](./05-worktree-guide.md)
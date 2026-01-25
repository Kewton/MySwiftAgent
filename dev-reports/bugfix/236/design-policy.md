# 設計方針書: greenlet プラットフォーム非互換性の修正

> Issue #236: fix(ci): expertAgent Integration Tests fail due to greenlet platform incompatibility

## 1. 設計概要

### 1.1 変更の性質

| 項目 | 内容 |
|------|------|
| 変更種別 | 構成管理（.gitignore 修正） |
| 影響範囲 | 依存関係管理、CI/CD |
| コード変更 | なし（設定ファイルのみ） |
| リスクレベル | 低 |

### 1.2 設計目標

1. **再現性**: 全環境（ローカル、CI）で同一の依存関係を使用
2. **安定性**: プラットフォーム起因の CI 失敗を防止
3. **保守性**: 依存関係更新プロセスの明確化

## 2. 依存関係管理アーキテクチャ

### 2.1 現在の状態（問題あり）

```mermaid
graph TD
    subgraph "ローカル開発環境 (macOS)"
        L_DEV[開発者] --> L_UV[uv sync]
        L_UV --> L_LOCK[uv.lock 生成]
        L_LOCK --> L_INSTALL[依存関係インストール]
        L_INSTALL --> L_SUCCESS[✅ 成功]
    end

    subgraph "Git リポジトリ"
        GIT[.gitignore]
        GIT -->|uv.lock 除外| IGNORE[uv.lock なし]
    end

    subgraph "CI 環境 (Linux)"
        CI_CHECKOUT[checkout] --> CI_UV[uv sync]
        CI_UV -->|lock なし| CI_RESOLVE[新規依存解決]
        CI_RESOLVE --> CI_GREENLET[greenlet 3.3.0]
        CI_GREENLET -->|Linux wheel なし| CI_FAIL[❌ 失敗]
    end

    L_DEV -.->|push| GIT
    GIT -.->|checkout| CI_CHECKOUT

    style CI_FAIL fill:#f99
    style IGNORE fill:#ff9
```

### 2.2 修正後の状態（目標）

```mermaid
graph TD
    subgraph "ローカル開発環境"
        L_DEV[開発者] --> L_UV[uv sync]
        L_UV --> L_LOCK[uv.lock 使用/更新]
        L_LOCK --> L_INSTALL[依存関係インストール]
        L_INSTALL --> L_SUCCESS[✅ 成功]
        L_LOCK -->|変更時| L_COMMIT[git commit]
    end

    subgraph "Git リポジトリ"
        GIT[uv.lock コミット済み]
    end

    subgraph "CI 環境 (Linux)"
        CI_CHECKOUT[checkout] --> CI_LOCK[uv.lock 取得]
        CI_LOCK --> CI_UV[uv sync]
        CI_UV -->|lock 使用| CI_INSTALL[同一バージョン]
        CI_INSTALL --> CI_GREENLET[greenlet 3.2.4]
        CI_GREENLET -->|Linux wheel あり| CI_SUCCESS[✅ 成功]
    end

    L_COMMIT -.->|push| GIT
    GIT -.->|checkout| CI_CHECKOUT

    style CI_SUCCESS fill:#9f9
    style GIT fill:#9f9
```

### 2.3 依存関係フロー

```mermaid
sequenceDiagram
    participant Dev as 開発者
    participant Local as ローカル環境
    participant Git as GitHub
    participant CI as CI環境

    Note over Dev,CI: 【修正後のフロー】

    Dev->>Local: 依存関係を追加/更新
    Local->>Local: uv add <package> または pyproject.toml 編集
    Local->>Local: uv lock (自動または手動)
    Local->>Local: uv sync
    Local->>Git: git add pyproject.toml uv.lock
    Local->>Git: git commit && git push

    Git->>CI: ワークフロー起動
    CI->>CI: checkout (uv.lock 含む)
    CI->>CI: uv sync (lock ファイル使用)
    CI->>CI: テスト実行
    CI->>Git: 結果報告 ✅
```

## 3. 技術選定

### 3.1 採用技術

| カテゴリ | 選定技術 | 選定理由 |
|---------|---------|---------|
| パッケージマネージャー | uv | 既存採用、高速、lock ファイルサポート |
| Lock ファイル形式 | uv.lock | uv 標準形式、プラットフォーム互換性情報含む |
| バージョン管理 | Git | 既存採用 |

### 3.2 uv.lock の特徴

| 特徴 | 説明 |
|------|------|
| クロスプラットフォーム | 複数プラットフォームの wheel 情報を保持 |
| 決定論的解決 | 同一 lock から常に同一環境を再現 |
| 高速インストール | 解決済みのため再計算不要 |
| 差分表示可能 | テキスト形式で git diff 可能 |

## 4. 設計判断とトレードオフ

### 4.1 採用した設計

**方針**: `.gitignore` から `uv.lock` を削除し、lock ファイルをコミットする

### 4.2 代替案の検討

| 代替案 | 説明 | 不採用理由 |
|--------|------|-----------|
| required-environments 設定 | pyproject.toml でプラットフォーム指定 | 完全な再現性なし、設定が複雑 |
| greenlet バージョン固定 | `greenlet<3.3.0` を指定 | 一時的な回避策、他パッケージで再発リスク |
| CI で lock 再生成 | `uv lock` を CI で実行 | 毎回異なる解決になる可能性 |
| 環境別 lock ファイル | `uv.lock.linux`, `uv.lock.macos` | 複雑、uv 非対応 |

### 4.3 トレードオフ分析

| 観点 | 採用案 | トレードオフ |
|------|--------|-------------|
| **再現性** | lock コミット | 完全な再現性を保証 |
| **保守性** | lock コミット | 依存更新時に lock も更新必要 |
| **コンフリクト** | lock コミット | マージ時にコンフリクト可能性あり |
| **透明性** | lock コミット | 依存変更が履歴で追跡可能 |

### 4.4 コンフリクト発生時の対処

```bash
# uv.lock でコンフリクト発生時
git checkout --theirs uv.lock  # または --ours
uv lock                         # 再生成
git add uv.lock
git commit
```

### 4.5 CLAUDE.md 原則への準拠

| 原則 | 準拠状況 | 説明 |
|------|---------|------|
| **KISS** | 準拠 | 最もシンプルな解決策（.gitignore 修正のみ） |
| **YAGNI** | 準拠 | 必要最小限の変更（expertAgent のみ） |
| **DRY** | N/A | 設定変更のため該当せず |
| **SOLID** | N/A | コード変更なしのため該当せず |

## 5. 実装方針

### 5.1 変更対象ファイル

```
.gitignore                    # uv.lock 行を削除
expertAgent/uv.lock           # Git 追跡開始（新規追加）
```

### 5.2 変更内容（差分）

#### .gitignore

```diff
  #Pipfile.lock
  #poetry.lock
  #pdm.lock
- uv.lock
  /.emacs.desktop.lock
  *.pid.lock
  yarn.lock
  Cargo.lock
```

#### expertAgent/uv.lock

```bash
# 新規追跡開始
git add expertAgent/uv.lock
```

### 5.3 実装手順

1. `.gitignore` から `uv.lock` 行を削除
2. `expertAgent/uv.lock` の内容確認（greenlet 3.2.4 であること）
3. `git add .gitignore expertAgent/uv.lock`
4. コミット作成
5. PR 作成・CI 確認

### 5.4 uv.lock 内容の事前確認

```bash
# greenlet バージョン確認
grep -A2 'name = "greenlet"' expertAgent/uv.lock
# 期待出力: version = "3.2.4"

# Linux wheel 存在確認
grep "manylinux.*greenlet" expertAgent/uv.lock
# 期待出力: Linux wheel URL が含まれる
```

## 6. 品質保証方針

### 6.1 検証方法

| 検証項目 | 方法 | 期待結果 |
|----------|------|----------|
| uv.lock 追跡 | `git ls-files expertAgent/uv.lock` | ファイルパス出力 |
| CI 依存インストール | CI ログ確認 | エラーなし |
| Integration Tests | CI 結果確認 | 全テスト PASSED |
| Code Quality | CI 結果確認 | 静的解析成功 |

### 6.2 受入基準の検証

| AC | 検証方法 | 判定基準 |
|----|----------|----------|
| AC1 | `grep uv.lock .gitignore` | 出力なし |
| AC2 | `git ls-files expertAgent/uv.lock` | ファイルパス出力 |
| AC3 | CI ログ: "Install dependencies" | exit code 0 |
| AC4 | CI 結果: Integration Tests | 全テスト PASSED |
| AC5 | CI 結果: Code Quality | 成功 |
| AC6 | CI 全体 | 全ジョブ緑 |

### 6.3 ロールバック計画

| 状況 | 対応 |
|------|------|
| uv.lock コミット後に問題 | `git revert` で変更を戻す |
| 別の依存関係問題 | `uv lock --upgrade` で再生成 |

## 7. 影響分析

### 7.1 影響を受けるコンポーネント

| コンポーネント | 影響 |
|---------------|------|
| expertAgent | 直接影響（uv.lock 追跡開始） |
| CI ワークフロー | 間接影響（依存解決方法変更） |
| 他プロジェクト | 影響なし（今回は対象外） |

### 7.2 他プロジェクトへの展開

本修正が成功した場合、同様の問題を防ぐため、他プロジェクトの `uv.lock` も段階的にコミットすることを推奨：

| プロジェクト | 優先度 | 理由 |
|-------------|--------|------|
| myscheduler | 高 | 本番運用中 |
| jobqueue | 中 | 準備中 |
| myVault | 高 | 本番運用中 |
| graphAiServer | 中 | 開発中 |
| commonUI | 低 | TypeScript（uv 不使用） |

> **注**: 他プロジェクトの対応は別 Issue として切り出すことを推奨

## 8. 関連ドキュメント

| ドキュメント | 内容 |
|-------------|------|
| [requirements.md](./requirements.md) | 要件定義書 |
| [current-state-analysis.md](./current-state-analysis.md) | 現状整理レポート |
| [uv 公式: Lock files](https://docs.astral.sh/uv/concepts/projects/#lockfile) | uv lock ファイルの説明 |

---

**作成日**: 2024-12-04
**ステータス**: 設計完了・レビュー待ち
**レビュー**: -

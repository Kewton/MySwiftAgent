# 要件定義書: greenlet プラットフォーム非互換性の修正

> Issue #236: fix(ci): expertAgent Integration Tests fail due to greenlet platform incompatibility

## 1. ユーザーストーリー

```
As a 開発者
I want to CI環境（Linux）でexpertAgentの全テストが正常に実行されるようにする
So that コード品質を継続的に担保し、安心してマージ・デプロイができる
```

## 2. 現状分析サマリー

> 詳細: [current-state-analysis.md](./current-state-analysis.md)

### 2.1 問題の構造

| 項目 | 内容 |
|------|------|
| 直接原因 | greenlet 3.3.0 に Linux wheel がない |
| 根本原因 | `uv.lock` が `.gitignore` に含まれ、Git にコミットされていない |
| 影響範囲 | expertAgent の Integration Tests, Code Quality Analysis |

### 2.2 失敗しているジョブ

| ジョブ | 状態 | 影響 |
|--------|------|------|
| Test Suite (expertAgent) | 成功 | - |
| Code Quality Analysis (expertAgent) | **失敗** | 静的解析が実行不可 |
| Integration Tests (expertAgent) | **失敗** | 22テスト未実行 |

### 2.3 エラーメッセージ

```
error: Distribution `greenlet==3.3.0 @ registry+https://pypi.org/simple` can't be installed
because it doesn't have a source distribution or wheel for the current platform

hint: You're on Linux (`manylinux_2_39_x86_64`), but `greenlet` (v3.3.0) only has wheels
for the following platform: `macosx_11_0_universal2`
```

## 3. 受入条件（Acceptance Criteria）

### AC1: uv.lock の Git 追跡

- **Given**: プロジェクトルートの `.gitignore` に `uv.lock` が含まれている
- **When**: `.gitignore` から `uv.lock` を削除する
- **Then**: `uv.lock` ファイルが Git で追跡可能になる

### AC2: expertAgent の uv.lock コミット

- **Given**: expertAgent ディレクトリに `uv.lock` が存在する
- **When**: `uv.lock` を Git にコミットする
- **Then**: CI 環境で同一の依存関係が使用される

### AC3: CI 環境での依存関係インストール成功

- **Given**: `uv.lock` がリポジトリにコミットされている
- **When**: CI 環境で `uv sync --extra dev` が実行される
- **Then**: `greenlet` を含む全ての依存関係が正常にインストールされる

### AC4: Integration Tests の成功

- **Given**: 依存関係が正常にインストールされた状態
- **When**: Integration Tests ジョブが実行される
- **Then**: 以下のテストが全て成功する
  - `test_issue_169_acceptance.py`: Valkey 関連テスト
  - `test_valkey_integration.py`: Valkey 統合テスト
  - **合計**: 22テスト以上

### AC5: Code Quality Analysis の成功

- **Given**: 依存関係が正常にインストールされた状態
- **When**: Code Quality Analysis ジョブが実行される
- **Then**: Ruff、MyPy などの静的解析ツールが正常に実行される

### AC6: CI 全体の成功

- **Given**: 全ての修正が適用された状態
- **When**: `cd-develop.yml` ワークフローが実行される
- **Then**: 全てのジョブが成功し、CI 全体が緑色になる

## 4. 機能要件

### 4.1 必須機能（Must Have）

| ID | 要件 | 詳細 |
|----|------|------|
| FR-1 | .gitignore から uv.lock を削除 | プロジェクトルートの `.gitignore` から `uv.lock` 行を削除 |
| FR-2 | expertAgent の uv.lock をコミット | `expertAgent/uv.lock` を Git に追加してコミット |
| FR-3 | uv.lock の整合性確認 | Linux 互換の greenlet バージョンが含まれていることを確認 |

### 4.2 あると良い機能（Nice to Have）

| ID | 要件 | 詳細 |
|----|------|------|
| NR-1 | 他プロジェクトの uv.lock も追跡 | myscheduler, jobqueue, myVault の uv.lock も同様にコミット |
| NR-2 | CI での uv.lock 整合性チェック | `uv lock --check` をCIに追加してdriftを検出 |

### 4.3 将来的な拡張（Future Enhancement）

| ID | 要件 | 詳細 |
|----|------|------|
| FE-1 | Dependabot/Renovate 統合 | 依存関係の自動更新とPR作成 |
| FE-2 | マルチプラットフォームCI | Linux/macOS/Windows での並列テスト |

## 5. 非機能要件

### 5.1 パフォーマンス要件

| ID | 要件 | 基準値 |
|----|------|--------|
| NFR-P1 | CI 実行時間 | 現状と同等（悪化なし） |
| NFR-P2 | 依存関係インストール時間 | lock ファイル使用により高速化期待 |

### 5.2 信頼性要件

| ID | 要件 | 基準値 |
|----|------|--------|
| NFR-R1 | CI 成功率 | 100%（プラットフォーム起因の失敗なし） |
| NFR-R2 | 依存関係の再現性 | 全環境で同一バージョン |

### 5.3 保守性要件

| ID | 要件 | 詳細 |
|----|------|------|
| NFR-M1 | uv.lock 更新プロセス | 依存関係変更時は `uv lock` を実行してコミット |
| NFR-M2 | ドキュメント化 | README に uv.lock 管理方法を記載 |

### 5.4 互換性要件

| ID | 要件 | 詳細 |
|----|------|------|
| NFR-C1 | プラットフォーム互換性 | macOS, Linux (ubuntu-latest) 両方で動作 |
| NFR-C2 | Python バージョン互換性 | Python 3.12 で動作 |

## 6. 技術的制約

### 6.1 使用する技術スタック

| 項目 | 詳細 |
|------|------|
| パッケージマネージャー | uv |
| CI/CD プラットフォーム | GitHub Actions |
| ターゲット環境 | Linux (ubuntu-latest), macOS |
| Python バージョン | 3.12 |

### 6.2 修正対象ファイル

| ファイル | 変更内容 |
|----------|----------|
| `.gitignore` | `uv.lock` 行を削除 |
| `expertAgent/uv.lock` | Git に追加（新規追跡） |

### 6.3 影響を受けるパッケージ

| パッケージ | 現在のバージョン（ローカル） | 問題バージョン（CI） |
|-----------|---------------------------|---------------------|
| greenlet | 3.2.4 | 3.3.0 |

### 6.4 greenlet の依存関係チェーン

```
expertAgent
└── sqlalchemy (async support)
    └── greenlet
```

## 7. リスクと対策

### 7.1 技術的リスク

| リスク | 影響度 | 発生確率 | 対策 |
|--------|--------|----------|------|
| uv.lock マージコンフリクト | 中 | 中 | 自動マージ可能、手動解決も容易 |
| 他プロジェクトへの影響 | 低 | 低 | 段階的に対応（まず expertAgent のみ） |
| ローカル環境での再解決 | 低 | 低 | `uv sync` で自動解決 |

### 7.2 運用リスク

| リスク | 影響度 | 発生確率 | 対策 |
|--------|--------|----------|------|
| uv.lock 更新忘れ | 中 | 中 | CI で `uv lock --check` を追加（Nice to Have） |
| 依存関係のドリフト | 低 | 低 | 定期的な `uv lock --upgrade` |

## 8. 実装チェックリスト

### 8.1 準備作業

- [ ] 現在の uv.lock 内容確認（greenlet バージョン）
- [ ] Linux 互換性確認（greenlet 3.2.4 には Linux wheel あり）

### 8.2 実装作業

- [ ] `.gitignore` から `uv.lock` を削除
- [ ] `expertAgent/uv.lock` を `git add`
- [ ] コミット作成

### 8.3 検証作業

- [ ] PR 作成後、CI ワークフローが実行されることを確認
- [ ] 依存関係インストールが成功することを確認
- [ ] Integration Tests が成功することを確認
- [ ] Code Quality Analysis が成功することを確認
- [ ] CI 全体が緑色になることを確認

## 9. 参考情報

| 項目 | リンク/参照 |
|------|------------|
| 現状分析レポート | [current-state-analysis.md](./current-state-analysis.md) |
| 失敗した CI Run | https://github.com/Kewton/MySwiftAgent/actions/runs/19932210244 |
| uv 公式: Lock files | https://docs.astral.sh/uv/concepts/projects/#lockfile |
| greenlet PyPI | https://pypi.org/project/greenlet/ |
| Issue #182 | Valkey サービス追加（本 Issue の発見契機） |

---

**優先度**: High（CI が失敗している状態）
**見積もり工数**: 1h（調査含む）
**担当レイヤー**: DevOps / CI/CD
**作成日**: 2024-12-04
**更新日**: 2024-12-04（現状整理結果を反映）

# 要件定義書: Integration Tests ジョブへの Valkey サービスコンテナ追加

> Issue #182: fix(ci): Add Valkey service container to Integration Tests job

## 1. ユーザーストーリー

```
As a 開発者
I want to Integration Tests ジョブで Valkey サービスコンテナを利用できるようにする
So that Valkey 関連の統合テストが CI 環境で正常に実行され、品質担保ができる
```

## 2. 現状分析サマリー

> 詳細: [current-state-analysis.md](./current-state-analysis.md)

### 2.1 ワークフロー構成の不整合

| ジョブ | 行番号 | Valkey サービス | テスト結果 |
|--------|--------|----------------|-----------|
| Test Suite | 71-148 | あり (line 77-86) | 正常動作 |
| Integration Tests | 150-200 | **なし** | 22テスト失敗 |

### 2.2 失敗テストの内訳

#### test_issue_169_acceptance.py（全15テスト中）

| テスト | Valkey依存 | 状態 |
|--------|-----------|------|
| `test_ac1_valkey_directory_exists` | No | PASSED |
| `test_ac2_valkey_config_and_data_structure` | No | PASSED |
| `test_ac3_valkey_connection` | **Yes** | ERROR |
| `test_ac4_conversation_data_saved_to_valkey` | **Yes** | ERROR |
| `test_ac5_ttl_functionality` | **Yes** | ERROR |
| `test_ac6_metadata_persistence` | **Yes** | ERROR |
| `test_ac10_unit_test_coverage_90_percent` | No | PASSED |
| `test_ac12_static_analysis_clean` | No | PASSED |
| `test_scenario1_basic_save_and_retrieve` | **Yes** | ERROR |
| `test_scenario2_ttl_auto_deletion` | **Yes** | ERROR |
| `test_scenario3_metadata_persistence` | **Yes** | ERROR |
| `test_scenario4_error_fallback` | No | PASSED |
| `test_scenario5_performance_50ms` | **Yes** | ERROR |
| `test_scenario6_large_volume_processing` | **Yes** | ERROR |
| `test_scenario7_environment_variable_switching` | No | PASSED |

#### test_valkey_integration.py（全12テスト）

| テストクラス | テスト数 | Valkey依存 | 状態 |
|-------------|---------|-----------|------|
| `TestValkeyClientIntegration` | 5 | **Yes** | 全て ERROR |
| `TestConversationStoreValkeyIntegration` | 8 | **Yes** | 全て ERROR |
| `TestValkeyErrorHandling` | 3 | 部分的 | 一部 PASSED |

### 2.3 エラー詳細

```
valkey.exceptions.ConnectionError: Error Multiple exceptions:
  [Errno 111] Connect call failed ('::1', 6379, 0, 0),
  [Errno 111] Connect call failed ('127.0.0.1', 6379)
  connecting to localhost:6379.
```

### 2.4 Fixture の動作

**ファイル**: `expertAgent/tests/fixtures/valkey_fixtures.py`

```python
@pytest.fixture
async def valkey_test_client():
    client = ValkeyClient(host="localhost", port=6379, db=15)
    try:
        await client.connect()
    except ValkeyConnectionError as e:
        pytest.skip(f"Valkey not available: {e}")  # ← 接続失敗時はスキップ
```

- **接続先**: `localhost:6379` (db=15)
- **エラー処理**: `pytest.skip()` でスキップする設計
- **問題**: CI 環境では Valkey が存在しないため ERROR として報告される

## 3. 受入条件（Acceptance Criteria）

### AC1: Valkey サービスコンテナの追加

- **Given**: `cd-develop.yml` の Integration Tests ジョブ定義 (line 150-200)
- **When**: ワークフローが実行される
- **Then**: Valkey サービスコンテナが起動し、ポート 6379 でアクセス可能になる

### AC2: ヘルスチェック設定

- **Given**: Valkey サービスコンテナ
- **When**: コンテナ起動時
- **Then**: `valkey-cli ping` でヘルスチェックが実行され、正常応答を確認後にジョブが開始される

### AC3: Valkey 統合テストの成功

- **Given**: Valkey サービスコンテナが正常稼働
- **When**: Integration Tests ジョブが実行される
- **Then**: 以下のテストが全て成功する
  - `test_issue_169_acceptance.py`: 10テスト（Valkey依存テスト）
  - `test_valkey_integration.py`: 12テスト（全テスト）
  - **合計**: 22テスト

### AC4: CI 全体の成功

- **Given**: 全ての修正が適用された状態
- **When**: `cd-develop.yml` ワークフローが実行される
- **Then**: 全てのジョブが成功し、CI 全体が緑色になる

## 4. 機能要件

### 4.1 必須機能（Must Have）

| ID | 要件 | 詳細 |
|----|------|------|
| FR-1 | Valkey サービスコンテナ追加 | Integration Tests ジョブ (line 154) に `valkey/valkey:latest` イメージのサービスコンテナを追加 |
| FR-2 | ポートマッピング設定 | ホストの 6379 ポートをコンテナの 6379 ポートにマッピング |
| FR-3 | ヘルスチェック設定 | `valkey-cli ping` によるヘルスチェック（10秒間隔、5秒タイムアウト、5回リトライ） |
| FR-4 | Test Suite との設定一致 | Test Suite ジョブ (line 77-86) と同一の設定を使用 |

### 4.2 あると良い機能（Nice to Have）

| ID | 要件 | 詳細 |
|----|------|------|
| NR-1 | サービス設定の共通化 | YAML アンカー等で設定の重複を避ける（将来の保守性向上） |

### 4.3 将来的な拡張（Future Enhancement）

| ID | 要件 | 詳細 |
|----|------|------|
| FE-1 | Valkey クラスタ対応 | 本番環境を想定したクラスタ構成でのテスト実行 |

## 5. 非機能要件

### 5.1 パフォーマンス要件

| ID | 要件 | 基準値 |
|----|------|--------|
| NFR-P1 | コンテナ起動時間 | 30秒以内にヘルスチェック通過 |
| NFR-P2 | ジョブ実行時間への影響 | 現在のジョブ実行時間 + 30秒以内 |

### 5.2 信頼性要件

| ID | 要件 | 基準値 |
|----|------|--------|
| NFR-R1 | ヘルスチェックリトライ | 最大5回のリトライで安定起動を保証 |
| NFR-R2 | テスト成功率 | Valkey 関連テスト 22/22 (100%) 成功 |

### 5.3 互換性要件

| ID | 要件 | 詳細 |
|----|------|------|
| NFR-C1 | Test Suite ジョブとの整合性 | 既存の Test Suite ジョブ (line 77-86) と同一の設定を使用 |
| NFR-C2 | GitHub Actions ランナー互換性 | `ubuntu-latest` ランナーで動作すること |

## 6. 技術的制約

### 6.1 使用する技術スタック

| 項目 | 詳細 |
|------|------|
| CI/CD プラットフォーム | GitHub Actions |
| サービスコンテナ | Docker (GitHub Actions 提供) |
| Valkey イメージ | `valkey/valkey:latest` |
| テストフレームワーク | pytest |
| Valkey クライアント | valkey-py |

### 6.2 修正対象ファイル

| ファイル | 変更箇所 | 変更内容 |
|----------|----------|----------|
| `.github/workflows/cd-develop.yml` | line 154 (`strategy:` の前) | `services` セクション追加 |

### 6.3 現在の Integration Tests ジョブ構造

```yaml
# line 150-164
integration-test:
  name: Integration Tests
  runs-on: ubuntu-latest
  needs: [test, detect-changes]
  if: needs.detect-changes.outputs.myscheduler == 'true' || ...
  # ← ここに services セクションを追加
  strategy:
    matrix:
      project:
        - ${{ needs.detect-changes.outputs.myscheduler == 'true' && 'myscheduler' || '' }}
        # ...
```

### 6.4 追加する設定仕様

```yaml
  services:
    valkey:
      image: valkey/valkey:latest
      ports:
        - 6379:6379
      options: >-
        --health-cmd "valkey-cli ping"
        --health-interval 10s
        --health-timeout 5s
        --health-retries 5
```

### 6.5 参照: Test Suite ジョブの既存設定

**ファイル**: `.github/workflows/cd-develop.yml` (line 77-86)

```yaml
test:
  name: Test Suite
  runs-on: ubuntu-latest
  needs: detect-changes
  # ...
  services:
    valkey:
      image: valkey/valkey:latest
      ports:
        - 6379:6379
      options: >-
        --health-cmd "valkey-cli ping"
        --health-interval 10s
        --health-timeout 5s
        --health-retries 5
```

### 6.6 テスト環境の接続設定

| パラメータ | 値 | 設定元 |
|-----------|-----|--------|
| Host | `localhost` | `valkey_fixtures.py` |
| Port | `6379` | `valkey_fixtures.py` |
| DB | `15` | テスト用データベース（本番と分離） |

## 7. リスクと対策

### 7.1 技術的リスク

| リスク | 影響度 | 発生可能性 | 対策 |
|--------|--------|-----------|------|
| Valkey イメージの互換性問題 | 中 | 低 | Test Suite で動作実績のある `latest` を使用 |
| ヘルスチェック失敗による起動遅延 | 低 | 低 | リトライ設定により自動復旧 |
| ポート競合 | 低 | 極低 | GitHub Actions のサービスコンテナは分離環境で動作 |

### 7.2 運用リスク

| リスク | 影響度 | 発生可能性 | 対策 |
|--------|--------|-----------|------|
| CI 実行時間の増加 | 低 | 中 | コンテナ起動のオーバーヘッドは最小限（約30秒） |
| 設定の不整合（Test Suite と Integration Tests） | 中 | 低 | 同一設定のコピー、PR レビューで確認 |

## 8. 実装チェックリスト

### 8.1 実装作業

- [ ] `cd-develop.yml` の Integration Tests ジョブ (line 154) に `services` セクションを追加
- [ ] Test Suite ジョブ (line 77-86) と同一の設定であることを確認
- [ ] YAML 構文の検証（ローカルまたは YAML リンター）

### 8.2 検証作業

- [ ] PR 作成後、CI ワークフローが実行されることを確認
- [ ] Integration Tests ジョブが正常に開始されることを確認
- [ ] `test_issue_169_acceptance.py` の 10テストが成功することを確認
- [ ] `test_valkey_integration.py` の 12テストが成功することを確認
- [ ] CI 全体が緑色になることを確認

## 9. 参考情報

| 項目 | リンク/参照 |
|------|------------|
| 現状分析レポート | [current-state-analysis.md](./current-state-analysis.md) |
| 関連 Issue | Issue #169: Valkey persistence infrastructure (CLOSED) |
| 既存設定参考 | Test Suite ジョブの services セクション (line 77-86) |
| 失敗した CI Run | https://github.com/Kewton/MySwiftAgent/actions/runs/19536228720 |
| Valkey 公式ドキュメント | https://valkey.io/docs/ |
| Valkey Fixture | `expertAgent/tests/fixtures/valkey_fixtures.py` |

---

**優先度**: Medium
**見積もり工数**: 0.5h（設定変更のみ、コード変更なし）
**担当レイヤー**: DevOps / CI/CD
**作成日**: 2024-12-04
**更新日**: 2024-12-04（現状整理結果を反映）

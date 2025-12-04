# 現状整理: Issue #182 - Integration Tests ジョブへの Valkey サービスコンテナ追加

## 1. 問題の概要

GitHub Actions の "Integration Tests" ジョブに Valkey サービスコンテナが設定されていないため、Valkey 関連の統合テストが全て失敗している。

### 影響範囲

| テストファイル | テスト数 | 状態 |
|---------------|---------|------|
| `test_issue_169_acceptance.py` | 10 | ERROR |
| `test_valkey_integration.py` | 12 | ERROR |
| **合計** | **22** | **全てエラー** |

## 2. ワークフロー構成の分析

### 2.1 cd-develop.yml の構造

```
.github/workflows/cd-develop.yml
├── detect-changes (line 22-69)
├── test (Test Suite) (line 71-148)          ← Valkey サービスあり
├── integration-test (Integration Tests) (line 150-200) ← Valkey サービスなし ❌
├── build-check (line 202-277)
├── code-quality (line 279-327)
└── notify (line 329-343)
```

### 2.2 Test Suite ジョブの Valkey 設定（正常動作中）

**ファイル**: `.github/workflows/cd-develop.yml` (line 77-86)

```yaml
test:
  name: Test Suite
  runs-on: ubuntu-latest
  needs: detect-changes
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

### 2.3 Integration Tests ジョブの現状（問題あり）

**ファイル**: `.github/workflows/cd-develop.yml` (line 150-164)

```yaml
integration-test:
  name: Integration Tests
  runs-on: ubuntu-latest
  needs: [test, detect-changes]
  # services セクションが存在しない ❌
  strategy:
    matrix:
      project:
        - ${{ needs.detect-changes.outputs.myscheduler == 'true' && 'myscheduler' || '' }}
        # ...
```

## 3. エラー詳細

### 3.1 エラーメッセージ

```
valkey.exceptions.ConnectionError: Error Multiple exceptions:
  [Errno 111] Connect call failed ('::1', 6379, 0, 0),
  [Errno 111] Connect call failed ('127.0.0.1', 6379)
  connecting to localhost:6379.
```

### 3.2 失敗しているテストの詳細

#### test_issue_169_acceptance.py

| テスト名 | 分類 | 状態 |
|---------|------|------|
| `test_ac1_valkey_directory_exists` | AC1 | PASSED |
| `test_ac2_valkey_config_and_data_structure` | AC2 | PASSED |
| `test_ac3_valkey_connection` | AC3 | ERROR |
| `test_ac4_conversation_data_saved_to_valkey` | AC4 | ERROR |
| `test_ac5_ttl_functionality` | AC5 | ERROR |
| `test_ac6_metadata_persistence` | AC6 | ERROR |
| `test_ac10_unit_test_coverage_90_percent` | AC10 | PASSED |
| `test_ac12_static_analysis_clean` | AC12 | PASSED |
| `test_scenario1_basic_save_and_retrieve` | Scenario1 | ERROR |
| `test_scenario2_ttl_auto_deletion` | Scenario2 | ERROR |
| `test_scenario3_metadata_persistence` | Scenario3 | ERROR |
| `test_scenario4_error_fallback` | Scenario4 | PASSED |
| `test_scenario5_performance_50ms` | Scenario5 | ERROR |
| `test_scenario6_large_volume_processing` | Scenario6 | ERROR |
| `test_scenario7_environment_variable_switching` | Scenario7 | PASSED |

#### test_valkey_integration.py

| テストクラス | テスト数 | 状態 |
|-------------|---------|------|
| `TestValkeyClientIntegration` | 5 | ERROR |
| `TestConversationStoreValkeyIntegration` | 8 | ERROR |
| `TestValkeyErrorHandling` | 3 | 部分的にPASSED |

## 4. Valkey Fixture の分析

### 4.1 Fixture 構成

**ファイル**: `expertAgent/tests/fixtures/valkey_fixtures.py`

```python
@pytest.fixture
async def valkey_test_client() -> AsyncGenerator[ValkeyClient, None]:
    client = ValkeyClient(host="localhost", port=6379, db=15)
    try:
        await client.connect()
    except ValkeyConnectionError as e:
        pytest.skip(f"Valkey not available: {e}")  # ← 接続失敗時はスキップ
    # ...
```

### 4.2 Fixture 読み込み

**ファイル**: `expertAgent/tests/conftest.py` (line 13)

```python
pytest_plugins = ["tests.fixtures.valkey_fixtures"]
```

### 4.3 テスト環境の設定

| パラメータ | 値 | 説明 |
|-----------|-----|------|
| Host | `localhost` | Valkey サーバーホスト |
| Port | `6379` | Valkey サーバーポート |
| DB | `15` | テスト用データベース番号（本番データと分離） |

## 5. 根本原因

1. **設定の欠落**: Integration Tests ジョブに `services` セクションが追加されていない
2. **Test Suite では動作**: Test Suite ジョブには正しく Valkey サービスが設定されている
3. **一貫性の欠如**: 同じテストコードを実行するにもかかわらず、サービス設定が異なる

## 6. 関連情報

### 6.1 関連 Issue

- **Issue #169**: Valkey永続化基盤の実装（CLOSED）
  - 親Issue: #152
  - 単体テストカバレッジ: 100%
  - Valkey クライアント・ConversationStoreValkey 実装完了

### 6.2 失敗した CI Run

- **Run ID**: 19536228720
- **URL**: https://github.com/Kewton/MySwiftAgent/actions/runs/19536228720
- **日時**: 2025-11-20T12:07:09Z

## 7. 修正方針

### 7.1 必要な変更

Integration Tests ジョブに Test Suite ジョブと同一の `services` セクションを追加する。

### 7.2 修正箇所

**ファイル**: `.github/workflows/cd-develop.yml`
**位置**: line 154（`strategy:` の前）

```yaml
integration-test:
  name: Integration Tests
  runs-on: ubuntu-latest
  needs: [test, detect-changes]
  if: needs.detect-changes.outputs.myscheduler == 'true' || ...

  # 追加する services セクション
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

  strategy:
    matrix:
      # ...
```

## 8. 検証項目

- [ ] Integration Tests ジョブの YAML 構文が正しいこと
- [ ] Valkey サービスコンテナが正常に起動すること
- [ ] 22個の Valkey テストが全て成功すること
- [ ] CI 全体が成功すること

---

**作成日**: 2024-12-04
**更新日**: -
**ステータス**: 調査完了・修正待ち

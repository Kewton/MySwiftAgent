# 作業計画: ワークフローノードのテスト実装

**作成日**: 2025-10-24
**ブランチ**: `feature/issue/111`
**対象Issue**: #111 (Gemini API integration)
**目的**: Recursion limit バグを検知できなかったテストカバレッジギャップを解消

---

## 📋 要求・要件

### ビジネス要求
- ✅ Recursion limit バグのような重大なバグをテストで検知可能にする
- ✅ ワークフローノードの内部ロジックを網羅的にテストする
- ✅ CI/CDで継続的にテストを実行可能にする
- ✅ APIキーなしでテストの89%を実行可能にする

### 機能要件
- ✅ Unit Tests: 全ノード（7ノード）+ 全ルーター（2ルーター）のユニットテスト
- ✅ Integration Tests (Node): フィクスチャデータを使用したノードレベル統合テスト
- ✅ Integration Tests (E2E): 実LLM APIを使用したエンドツーエンドテスト
- ✅ カバレッジ目標: ワークフローノード 90%以上、ルーティングロジック 100%

### 非機能要件
- **セキュリティ**: APIキーをリポジトリにコミットしない、テストコードにハードコードしない
- **パフォーマンス**: Unit/Integration Testsは高速実行（LLM呼び出しなし）
- **可用性**: CI/CDで常時実行可能（APIキー不要テストが89%）
- **保守性**: pytest マーカーで実行対象を選択可能

---

## 🏗️ アーキテクチャ設計

### テスト構成

```
expertAgent/tests/
├── unit/                          # Unit Tests (APIキー不要)
│   ├── test_workflow_nodes.py    # 全ノードのユニットテスト（35件）
│   ├── test_workflow_routers.py  # 全ルーターのユニットテスト（18件）
│   └── test_schemas.py           # スキーマバリデーションテスト（15件）
├── integration/                   # Integration Tests
│   ├── test_workflow_integration.py  # ノードレベル統合テスト（30件、APIキー不要）
│   ├── test_workflow_e2e.py      # E2Eテスト（10件、APIキー必要）
│   ├── conftest.py               # フィクスチャ定義（APIキー取得含む）
│   └── fixtures/
│       └── llm_responses.py      # LLMレスポンスのフィクスチャデータ
└── utils/
    └── mock_helpers.py           # モックヘルパー関数
```

### テストマーカー設計

| マーカー | 用途 | API利用 | APIキー要否 | 実行頻度 |
|---------|------|--------|-----------|---------|
| `@pytest.mark.unit` | ノード/ルーターのユニットテスト | ❌ 完全モック | 不要 | 常時 |
| `@pytest.mark.integration` | ノードレベル統合テスト | ❌ フィクスチャモック | 不要 | 常時 |
| `@pytest.mark.e2e` | E2Eワークフローテスト | ✅ 実LLM API | 必要 | 定期 |
| `@pytest.mark.llm_required` | 実LLM必須テスト | ✅ 実LLM API | 必要 | ローカル |

### APIキー取得設計

**優先順位**:
1. **モックデータ** - Unit/Integration Testsの89%（APIキー不要）
2. **環境変数** `TEST_GOOGLE_API_KEY` - CI/CD環境（E2E Tests）
3. **MyVault** - ローカル開発環境（E2E Tests）
4. **Skip Test** - APIキー取得失敗時はテストスキップ

**実装**:
```python
# tests/integration/conftest.py
@pytest.fixture(scope="session")
async def llm_api_key():
    # 環境変数 → MyVault → Skip
    if api_key := os.getenv("TEST_GOOGLE_API_KEY"):
        return api_key
    try:
        vault_client = MyVaultClient()
        if api_key := await vault_client.get_secret("GOOGLE_API_KEY"):
            return api_key
    except Exception:
        pass
    pytest.skip("LLM API key not available")
```

---

## 📊 Phase分解

### **Phase 0: 基盤準備** (0.5日) - 2025-10-24

**目的**: テストインフラの構築

**タスク**:
- [ ] pytest マーカー設定を `pyproject.toml` に追加
- [ ] `.gitignore` に `.env.test` を追加
- [ ] `tests/integration/fixtures/llm_responses.py` 作成
- [ ] `tests/utils/mock_helpers.py` 作成
- [ ] `tests/integration/conftest.py` にAPIキー取得フィクスチャ追加

**成果物**:
- `pyproject.toml` (markers設定)
- `.gitignore` (更新)
- `tests/integration/fixtures/llm_responses.py` (フィクスチャデータ)
- `tests/utils/mock_helpers.py` (モックヘルパー)
- `tests/integration/conftest.py` (APIキーフィクスチャ)

**検証方法**:
```bash
# pytest マーカーが正しく設定されていることを確認
uv run pytest --markers | grep "unit:"

# フィクスチャが正しくインポートできることを確認
uv run python3 -c "from tests.integration.fixtures.llm_responses import VALIDATION_SUCCESS_RESPONSE"
```

---

### **Phase 1: 緊急対応テスト** (1日) - 2025-10-25

**目的**: 今回発生したRecursion limitバグを検知可能にする

**タスク**:
- [ ] validation ノードのリトライロジックテスト（`@pytest.mark.unit`）
  - `test_validation_success()` - 成功時retry_count維持
  - `test_validation_failure_increments_retry_count()` - 失敗時retry_count +1
  - `test_validation_exception_increments_retry_count()` - 例外時retry_count +1
- [ ] validation_router の条件分岐テスト（`@pytest.mark.unit`）
  - `test_validation_success_routes_to_job_registration()` - 成功パス
  - `test_validation_failure_retries_interface_definition()` - リトライパス
  - `test_validation_max_retries_routes_to_end()` - 上限パス
- [ ] Recursion limit 検証テスト（`@pytest.mark.integration`）
  - `test_workflow_completes_within_recursion_limit()` - 再帰上限未到達
  - `test_workflow_stops_after_max_retries()` - リトライ上限で停止

**成果物**:
- `tests/unit/test_workflow_nodes.py` (validation ノードテスト: 3件)
- `tests/unit/test_workflow_routers.py` (validation_router テスト: 3件)
- `tests/integration/test_workflow_integration.py` (Recursion limitテスト: 2件)

**検証方法**:
```bash
# Phase 1のテストのみ実行
uv run pytest tests/unit/test_workflow_nodes.py::TestValidationNode -v
uv run pytest tests/unit/test_workflow_routers.py::TestValidationRouter -v
uv run pytest tests/integration/test_workflow_integration.py -v -m integration

# APIキーなしで実行可能なことを確認
unset TEST_GOOGLE_API_KEY
uv run pytest -m "unit or integration" -v
```

**期待結果**:
- ✅ 全テスト合格（8件）
- ✅ APIキーなしで実行可能
- ✅ validation ノードの retry_count インクリメントバグを検知可能

---

### **Phase 2: 全ノード・全ルーターのユニットテスト** (3日) - 2025-10-26～28

**目的**: ワークフローノード・ルーターの内部ロジックを網羅的にテスト

**タスク**:

#### **2-1: 全ノードのユニットテスト** (2日)
- [ ] requirement_analysis ノード（5件）
  - 成功ケース、失敗ケース、例外ケース、retry_count更新、評価フィードバック反映
- [ ] evaluator ノード（5件）
  - 成功ケース（after_task_breakdown）、成功ケース（after_interface_definition）、失敗ケース、retry_count=0リセット、例外ケース
- [ ] interface_definition ノード（5件）
  - 成功ケース、失敗ケース、例外時retry_count +1、Gemini JSON文字列対応、空タスク対応
- [ ] master_creation ノード（5件）
  - 成功ケース、JobMaster作成、TaskMaster作成、InterfaceMaster作成、例外ケース
- [ ] validation ノード（5件）
  - 成功ケース、失敗時retry_count +1、例外時retry_count +1、修正提案生成、警告のみケース
- [ ] job_registration ノード（5件）
  - 成功ケース、Job作成、Task作成、例外ケース、部分成功ケース

**成果物**: `tests/unit/test_workflow_nodes.py` (30件 + Phase 1の3件 = 33件)

#### **2-2: 全ルーターのユニットテスト** (1日)
- [ ] evaluator_router（9件）
  - after_task_breakdown: 成功→interface_definition、失敗→requirement_analysis、上限→END
  - after_interface_definition: 成功→master_creation、失敗→interface_definition、上限→END
  - その他のステージ（after_validation等）
- [ ] validation_router（3件 + Phase 1の3件）
  - 成功→job_registration
  - 失敗→interface_definition
  - 上限→END

**成果物**: `tests/unit/test_workflow_routers.py` (12件 + Phase 1の3件 = 15件)

#### **2-3: スキーマバリデーションテスト** (0.5日)
- [ ] JobGeneratorResponse スキーマ（5件）
  - 成功レスポンス（job_master_id: str）
  - 失敗レスポンス（infeasible_tasks）
  - 部分成功レスポンス
  - job_master_id が int の場合エラー
  - バリデーションエラーレスポンス
- [ ] InterfaceSchemaDefinition スキーマ（5件）
  - 正常ケース（dict）
  - Gemini JSON文字列ケース（str → dict変換）
  - 不正JSON文字列ケース（エラー）
  - 不正型ケース（list等でエラー）
  - extra="allow" の動作確認
- [ ] その他スキーマ（5件）
  - ValidationFixResponse, TaskBreakdownResponse等

**成果物**: `tests/unit/test_schemas.py` (15件)

**検証方法**:
```bash
# Phase 2のテストのみ実行
uv run pytest tests/unit/ -v -m unit

# カバレッジ確認
uv run pytest tests/unit/ --cov=aiagent/langgraph/jobTaskGeneratorAgents/nodes --cov=aiagent/langgraph/jobTaskGeneratorAgents/agent --cov-report=html

# カバレッジ目標確認
open htmlcov/index.html  # ノード: 90%以上、ルーター: 100%
```

**期待結果**:
- ✅ 全テスト合格（63件）
- ✅ APIキーなしで実行可能
- ✅ ノードカバレッジ 90%以上
- ✅ ルーターカバレッジ 100%

---

### **Phase 3: E2Eワークフローテスト** (2日) - 2025-10-29～30

**目的**: 実際のLLM APIを使用したエンドツーエンドテスト

**タスク**:
- [ ] E2Eテスト作成（`@pytest.mark.e2e`）
  - `test_workflow_success_path()` - 成功シナリオ
  - `test_workflow_with_infeasible_tasks()` - 実現不可タスク検出
  - `test_workflow_with_validation_errors()` - バリデーションエラー検出
  - `test_workflow_with_retry_recovery()` - リトライで回復
  - `test_workflow_stops_after_max_retries()` - 最大リトライで停止
  - `test_workflow_with_gemini_fallback()` - Claude→Gemini フォールバック
  - `test_workflow_completes_within_timeout()` - タイムアウト未到達
  - `test_workflow_handles_llm_errors()` - LLMエラーハンドリング
  - `test_workflow_generates_valid_jobmaster()` - JobMaster生成検証
  - `test_workflow_generates_valid_interfaces()` - Interface生成検証

**成果物**: `tests/integration/test_workflow_e2e.py` (10件)

**検証方法**:
```bash
# APIキーを設定してE2Eテスト実行
export TEST_GOOGLE_API_KEY="your_test_api_key"
uv run pytest tests/integration/test_workflow_e2e.py -v -m e2e

# または MyVault経由で実行
uv run pytest tests/integration/test_workflow_e2e.py -v -m e2e

# APIキーなしでスキップされることを確認
unset TEST_GOOGLE_API_KEY
uv run pytest tests/integration/test_workflow_e2e.py -v -m e2e
# → "LLM API key not available" でスキップ
```

**期待結果**:
- ✅ APIキーあり: 全テスト合格（10件）
- ✅ APIキーなし: 全テストスキップ（CI/CDが失敗しない）
- ✅ 実際のLLM動作を検証
- ✅ エンドツーエンドのカバレッジ 80%以上

---

### **Phase 4: CI/CD統合・ドキュメント作成** (1日) - 2025-10-31

**目的**: CI/CD統合とドキュメント整備

**タスク**:
- [ ] CI/CD設定更新
  - `.github/workflows/ci-feature.yml` にテスト実行追加
  - GitHub Secrets設定ドキュメント作成
- [ ] README更新
  - テスト実行方法の記載
  - pytest マーカーの説明
  - カバレッジ目標の記載
- [ ] 作業報告書作成
  - `final-report.md` 作成
  - テスト結果・カバレッジ報告
  - 品質指標の達成度

**成果物**:
- `.github/workflows/ci-feature.yml` (更新)
- `expertAgent/README.md` (更新)
- `dev-reports/feature/issue/111/final-report.md` (作業報告書)

**検証方法**:
```bash
# CI/CD相当のテスト実行
uv run pytest -m "unit or integration" --cov=aiagent/langgraph --cov-report=term-missing

# 全テスト実行（E2E含む）
uv run pytest --cov=aiagent/langgraph --cov-report=html
```

**期待結果**:
- ✅ CI/CDで Unit + Integration Tests が自動実行
- ✅ ドキュメントが整備されている
- ✅ 作業報告書が完成

---

## ✅ 制約条件チェック結果

### コード品質原則
- [x] **SOLID原則**: 遵守 / テストコードも単一責任・依存性逆転を適用
- [x] **KISS原則**: 遵守 / シンプルなモック・フィクスチャ設計
- [x] **YAGNI原則**: 遵守 / 必要最小限のテストケース
- [x] **DRY原則**: 遵守 / モックヘルパー・フィクスチャで重複排除

### アーキテクチャガイドライン
- [x] `architecture-overview.md`: 準拠 / テスト構成もレイヤー分離
- [x] 依存関係の方向性: 遵守 / テストがプロダクションコードに依存

### 設定管理ルール
- [x] **環境変数**: 遵守 / `TEST_GOOGLE_API_KEY` で管理
- [x] **MyVault**: 遵守 / E2EテストでMyVaultから取得

### 品質担保方針
- [ ] **単体テストカバレッジ**: 目標 90%以上（Phase 2完了後達成予定）
- [ ] **結合テストカバレッジ**: 目標 80%以上（Phase 3完了後達成予定）
- [x] **Ruff linting**: エラーゼロ（テストコードも対象）
- [x] **MyPy type checking**: エラーゼロ（テストコードも対象）

### CI/CD準拠
- [ ] **PRラベル**: `feature` ラベル付与予定
- [x] **コミットメッセージ**: 規約準拠（`test: add workflow node/router unit tests`）
- [ ] **pre-push-check-all.sh**: Phase 4で実行予定

### 参照ドキュメント遵守
- [x] **セキュリティ方針**: `/tmp/test_security_policy_proposal.md` 遵守
- [x] **テストカバレッジギャップ分析**: `/tmp/test_coverage_gap_analysis_report.md` 反映

### 違反・要検討項目
- ⚠️ **Phase 2完了まで**: カバレッジ目標未達成（既存テストのみ）
- ⚠️ **Phase 3完了まで**: E2Eテスト未実装（E2Eカバレッジ不足）

---

## 📅 スケジュール

| Phase | 開始予定 | 完了予定 | 工数 | 状態 |
|-------|---------|---------|------|------|
| Phase 0: 基盤準備 | 10/24 | 10/24 | 0.5日 | 予定 |
| Phase 1: 緊急対応テスト | 10/25 | 10/25 | 1日 | 予定 |
| Phase 2: 全ノード・全ルーターテスト | 10/26 | 10/28 | 3日 | 予定 |
| Phase 3: E2Eワークフローテスト | 10/29 | 10/30 | 2日 | 予定 |
| Phase 4: CI/CD統合・ドキュメント | 10/31 | 10/31 | 1日 | 予定 |

**総工数**: 7.5日

---

## 🎯 カバレッジ目標

| カテゴリ | 現在 | Phase 1 | Phase 2 | Phase 3 | 最終目標 |
|---------|------|---------|---------|---------|---------|
| **ワークフローノード** | 0% | 20% | 90% | 90% | **90%以上** |
| **ルーティングロジック** | 0% | 50% | 100% | 100% | **100%** |
| **スキーマバリデーション** | 30% | 30% | 95% | 95% | **95%以上** |
| **E2Eワークフロー** | 0% | 10% | 10% | 80% | **80%以上** |

---

## 📊 テストケース数の目標

| テストレベル | Phase 1 | Phase 2 | Phase 3 | 合計 |
|------------|---------|---------|---------|------|
| **Unit Tests (Nodes)** | 3件 | +30件 | - | **33件** |
| **Unit Tests (Routers)** | 3件 | +12件 | - | **15件** |
| **Unit Tests (Schemas)** | - | 15件 | - | **15件** |
| **Integration Tests (Node)** | 2件 | +20件 | - | **22件** |
| **Integration Tests (E2E)** | - | - | 10件 | **10件** |
| **合計** | 8件 | +77件 | +10件 | **95件** |

**内訳**:
- APIキー不要: 85件（89%）
- APIキー必要: 10件（11%）

---

## 🔗 関連ドキュメント

**必須参照**:
- ✅ [テストセキュリティ方針](/tmp/test_security_policy_proposal.md)
- ✅ [テストカバレッジギャップ分析](/tmp/test_coverage_gap_analysis_report.md)
- ✅ [Recursion Limit調査報告](/tmp/recursion_limit_investigation_report.md)

**推奨参照**:
- ✅ [アーキテクチャ概要](../../docs/design/architecture-overview.md)
- ✅ [環境変数管理](../../docs/design/environment-variables.md)
- ✅ [myVault連携](../../docs/design/myvault-integration.md)

---

## 📝 備考

### リスク管理
- **リスク1**: E2EテストでのLLM APIコスト増加
  - **対策**: テスト実行頻度を定期（1日1回）に制限、APIキー制限設定
- **リスク2**: LLMレスポンスの不安定性
  - **対策**: フィクスチャデータで安定したテストを優先、E2Eはサニティチェックのみ
- **リスク3**: テスト実装に時間がかかる
  - **対策**: Phase 1を最優先、Phase 2/3は段階的に実装

### 成功基準
- ✅ Phase 1完了: Recursion limitバグを検知可能なテストが実装されている
- ✅ Phase 2完了: ノードカバレッジ90%以上、ルーターカバレッジ100%達成
- ✅ Phase 3完了: E2Eカバレッジ80%以上達成
- ✅ Phase 4完了: CI/CDで自動テスト実行、ドキュメント整備完了

---

**作成者**: Claude Code
**レビュアー**: ユーザー承認済み

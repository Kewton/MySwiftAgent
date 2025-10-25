# 作業計画: Job Generator Multi-Model Support Enhancement

**作成日**: 2025-10-22
**予定工数**: 4-6人日
**完了予定**: 2025-10-24
**GitHub Issue**: [#111](https://github.com/Kewton/MySwiftAgent/issues/111)

---

## 📚 参考ドキュメント

**必須参照** (該当する場合):
- [x] [アーキテクチャ概要](../../../docs/design/architecture-overview.md)
- [x] [環境変数管理](../../../docs/design/environment-variables.md)
- [ ] ~~[新プロジェクトセットアップ手順書](../../../docs/procedures/NEW_PROJECT_SETUP.md)~~ - 該当なし
- [ ] ~~[GraphAI ワークフロー生成ルール](../../../graphAiServer/docs/GRAPHAI_WORKFLOW_GENERATION_RULES.md)~~ - 該当なし

**推奨参照**:
- [x] [myVault連携](../../../docs/design/myvault-integration.md) - API Key管理
- [x] [開発ガイド](../../../DEVELOPMENT_GUIDE.md) - 品質基準

---

## 📊 Phase分解

### Phase 1: 環境変数設定の追加 (0.5日)
**目的**: `core/config.py`にJob Generator用の環境変数を追加

**タスク**:
- [x] `core/config.py`を読み取り
- [ ] 以下の環境変数を追加:
  - `JOB_GENERATOR_MAX_TOKENS: int = Field(default=32768)`
  - `JOB_GENERATOR_REQUIREMENT_ANALYSIS_MODEL: str = Field(default="claude-haiku-4-5")`
  - `JOB_GENERATOR_EVALUATOR_MODEL: str = Field(default="claude-haiku-4-5")`
  - `JOB_GENERATOR_INTERFACE_DEFINITION_MODEL: str = Field(default="claude-haiku-4-5")`
  - `JOB_GENERATOR_VALIDATION_MODEL: str = Field(default="claude-haiku-4-5")`
- [ ] `.env.example`に環境変数のコメント・例を追加（既存の記述を更新）
- [ ] Ruff linting + MyPy type checking 実行

**成果物**:
- `expertAgent/core/config.py` (修正版)
- `expertAgent/.env.example` (更新版)

**完了条件**:
- 環境変数が`settings`オブジェクトから参照可能
- Ruff・MyPyエラーなし

---

### Phase 2: llm_factory.py拡張機能の実装 (1.5日)
**目的**: フォールバック機能、パフォーマンス測定、コスト追跡機能を実装

**タスク**:
- [x] 既存の`llm_factory.py`を読み取り
- [ ] `ModelPerformanceTracker`クラスを実装
  - `start()`, `end()`, `get_duration_ms()`, `log_metrics()` メソッド
- [ ] `ModelCostTracker`クラスを実装
  - `COST_TABLE`（クラス変数）
  - `calculate_cost()`, `add_call()`, `log_summary()` メソッド
- [ ] `create_llm_with_fallback()`関数を実装
  - Try-Exceptチェーンでフォールバック処理
  - プライマリモデル → Claude → GPT → Gemini の順序
  - 最大リトライ回数: 3回
  - パフォーマンストラッカー・コストトラッカーの初期化
- [ ] Docstringを詳細に記述（引数、戻り値、例外、使用例）
- [ ] Ruff linting + MyPy type checking 実行

**成果物**:
- `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/utils/llm_factory.py` (拡張版)

**完了条件**:
- `create_llm_with_fallback()`が動作し、フォールバックが正常に機能
- ログに正確なメトリクス・コスト情報が出力される
- Ruff・MyPyエラーなし

---

### Phase 3: requirement_analysis.pyの更新 (0.5日)
**目的**: `create_llm()` → `create_llm_with_fallback()` に置き換え

**タスク**:
- [x] 既存の`requirement_analysis.py`を読み取り
- [ ] `create_llm()` → `create_llm_with_fallback()` に置き換え
- [ ] パフォーマンストラッカー・コストトラッカーの受け取り
- [ ] LLM呼び出し後にトラッカーを更新（`tracker.end()`）
- [ ] ログ出力（`tracker.log_metrics()`, `cost_tracker.log_summary()`）
- [ ] Ruff linting + MyPy type checking 実行

**成果物**:
- `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/nodes/requirement_analysis.py` (修正版)

**完了条件**:
- フォールバック機能が動作
- ログにメトリクス・コスト情報が出力される
- Ruff・MyPyエラーなし

---

### Phase 4: evaluator.pyの更新 (0.5日)
**目的**: `ChatAnthropic`（ハードコード） → `create_llm_with_fallback()` に置き換え

**タスク**:
- [x] 既存の`evaluator.py`を読み取り（line 68-74を確認）
- [ ] `ChatAnthropic`のインスタンス化を削除
- [ ] `os.getenv("JOB_GENERATOR_EVALUATOR_MODEL", "claude-haiku-4-5")` で環境変数読み取り
- [ ] `create_llm_with_fallback()`を呼び出し
- [ ] パフォーマンストラッカー・コストトラッカーの受け取り
- [ ] LLM呼び出し後にトラッカーを更新
- [ ] Ruff linting + MyPy type checking 実行

**成果物**:
- `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/nodes/evaluator.py` (修正版)

**完了条件**:
- ハードコードが削除され、環境変数から読み取り
- フォールバック機能が動作
- Ruff・MyPyエラーなし

---

### Phase 5: interface_definition.pyの更新 (0.5日)
**目的**: 2箇所の`ChatAnthropic` → `create_llm_with_fallback()` に置き換え

**タスク**:
- [x] 既存の`interface_definition.py`を読み取り（line 120-126, 150-154を確認）
- [ ] 1箇所目（line 120-126）: structured_model用のLLM作成
  - `create_llm_with_fallback()`を呼び出し
- [ ] 2箇所目（line 150-154）: raw_model用のLLM作成
  - `create_llm_with_fallback()`を呼び出し
- [ ] パフォーマンストラッカー・コストトラッカーの受け取り
- [ ] LLM呼び出し後にトラッカーを更新
- [ ] Ruff linting + MyPy type checking 実行

**成果物**:
- `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/nodes/interface_definition.py` (修正版)

**完了条件**:
- 2箇所のハードコードが削除され、環境変数から読み取り
- フォールバック機能が動作
- Ruff・MyPyエラーなし

---

### Phase 6: validation.pyの更新 (0.5日)
**目的**: `ChatAnthropic` → `create_llm_with_fallback()` に置き換え

**タスク**:
- [x] 既存の`validation.py`を読み取り（line 107-113を確認）
- [ ] `ChatAnthropic`のインスタンス化を削除
- [ ] `os.getenv("JOB_GENERATOR_VALIDATION_MODEL", "claude-haiku-4-5")` で環境変数読み取り
- [ ] `create_llm_with_fallback()`を呼び出し
- [ ] パフォーマンストラッカー・コストトラッカーの受け取り
- [ ] LLM呼び出し後にトラッカーを更新
- [ ] Ruff linting + MyPy type checking 実行

**成果物**:
- `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/nodes/validation.py` (修正版)

**完了条件**:
- ハードコードが削除され、環境変数から読み取り
- フォールバック機能が動作
- Ruff・MyPyエラーなし

---

### Phase 7: 単体テストの作成 (1日)
**目的**: `llm_factory.py`の新機能に対する包括的な単体テストを作成

**タスク**:
- [ ] `tests/unit/test_llm_factory_fallback.py`を作成
- [ ] テストケース:
  1. `test_create_llm_with_fallback_primary_success` - プライマリモデルが成功
  2. `test_create_llm_with_fallback_fallback_to_second` - プライマリ失敗、2番目成功
  3. `test_create_llm_with_fallback_all_failed` - すべて失敗でValueError
  4. `test_model_performance_tracker_metrics` - パフォーマンス測定
  5. `test_model_cost_tracker_calculation` - コスト計算
  6. `test_model_cost_tracker_summary` - コストサマリー
  7. `test_create_llm_with_custom_fallback_list` - カスタムフォールバックリスト
  8. `test_create_llm_with_fallback_max_retries` - 最大リトライ回数
- [ ] Mockを使用してLLM APIの呼び出しをシミュレート
- [ ] カバレッジ測定: `uv run pytest tests/unit/test_llm_factory_fallback.py --cov=aiagent/langgraph/jobTaskGeneratorAgents/utils/llm_factory --cov-report=term-missing`
- [ ] カバレッジ目標: 90%以上

**成果物**:
- `expertAgent/tests/unit/test_llm_factory_fallback.py` (新規)

**完了条件**:
- 全テストケースが合格
- カバレッジ90%以上
- Ruff・MyPyエラーなし

---

### Phase 8: 結合テストの実行 (0.5日)
**目的**: 各ノードでClaude/GPT/Geminiの切り替えを確認

**タスク**:
- [ ] `.env`ファイルを作成し、各ノードで異なるモデルを指定:
  ```
  JOB_GENERATOR_REQUIREMENT_ANALYSIS_MODEL=claude-haiku-4-5
  JOB_GENERATOR_EVALUATOR_MODEL=gpt-4o-mini
  JOB_GENERATOR_INTERFACE_DEFINITION_MODEL=gemini-2.5-flash
  JOB_GENERATOR_VALIDATION_MODEL=claude-haiku-4-5
  ```
- [ ] Job Generatorエンドポイント（`/v1/job-generator`）を起動
- [ ] 実際のリクエストを送信し、各ノードでモデルが切り替わることを確認
- [ ] ログ出力を確認:
  - モデル名が正しく記録されているか
  - パフォーマンスメトリクスが出力されているか
  - コストサマリーが正確か
- [ ] フォールバックテスト（オプション）:
  - プライマリモデルのAPI Keyを無効化し、フォールバックが動作するか確認

**成果物**:
- テスト結果レポート（`phase-8-progress.md`に記載）

**完了条件**:
- 各ノードでモデルが正しく切り替わる
- ログに正確なメトリクス・コスト情報が出力される
- フォールバック機能が動作（オプション）

---

### Phase 9: ドキュメント更新と最終報告 (0.5日)
**目的**: 作業ドキュメントを完成させ、最終報告書を作成

**タスク**:
- [ ] `phase-1-progress.md` 〜 `phase-8-progress.md` を作成
- [ ] `final-report.md` を作成:
  - 納品物一覧
  - 品質指標（カバレッジ、Linting結果）
  - 制約条件チェック結果（最終版）
  - 参考資料
- [ ] `.env.example`に使用例のコメントを追加
- [ ] `README.md`に新機能の説明を追加（オプション）

**成果物**:
- `dev-reports/feature/issue/111/phase-*-progress.md` (全Phase分)
- `dev-reports/feature/issue/111/final-report.md`
- `expertAgent/.env.example` (完成版)

**完了条件**:
- すべてのドキュメントが完備
- 制約条件チェックに合格

---

### Phase 10: 品質チェックとPR作成 (0.5日)
**目的**: 品質基準を満たし、PRを作成してレビューに提出

**タスク**:
- [ ] Pre-push チェックスクリプトを実行:
  ```bash
  cd expertAgent
  ./scripts/pre-push-check.sh
  ```
- [ ] 全チェック項目が合格することを確認:
  - Ruff linting エラーゼロ
  - Ruff formatting 適用済み
  - MyPy type checking エラーゼロ
  - 単体テストカバレッジ90%以上
  - 結合テストカバレッジ50%以上
- [ ] コミットメッセージをConventional Commits規約に準拠して作成
- [ ] PRを作成:
  ```bash
  gh pr create --base develop \
    --title "feat(expertAgent): Job Generator Multi-Model Support Enhancement (#111)" \
    --body "$(cat dev-reports/feature/issue/111/final-report.md)" \
    --label "feature,enhancement"
  ```
- [ ] CI/CDパイプラインが合格することを確認

**成果物**:
- Pull Request (#111)

**完了条件**:
- pre-push-check.sh 合格
- CI/CD パイプライン合格
- PRが作成され、レビュー待ち状態

---

## ✅ 制約条件チェック結果

### コード品質原則
- [x] SOLID原則: 遵守予定
- [x] KISS原則: 遵守予定
- [x] YAGNI原則: 遵守予定
- [x] DRY原則: 遵守予定

### アーキテクチャガイドライン
- [x] architecture-overview.md: 準拠予定
- [x] レイヤー分離: 維持予定

### 設定管理ルール
- [x] 環境変数: `core/config.py`で一元管理
- [x] myVault: API Keysは引き続きmyVaultで管理

### 品質担保方針
- [ ] 単体テストカバレッジ: 90%以上（Phase 7で達成予定）
- [ ] 結合テストカバレッジ: 50%以上（Phase 8で達成予定）
- [ ] Ruff linting: エラーゼロ（各Phase完了時に確認）
- [ ] MyPy type checking: エラーゼロ（各Phase完了時に確認）

### CI/CD準拠
- [x] PRラベル: `feature`, `enhancement` を付与予定
- [x] コミットメッセージ: Conventional Commits規約に準拠予定
- [ ] pre-push-check-all.sh: Phase 10で実行予定

### 参照ドキュメント遵守
- [x] アーキテクチャ概要: 準拠
- [x] 環境変数管理: 準拠
- [x] myVault連携: API Key管理は変更なし

### 違反・要検討項目
なし

---

## 📅 スケジュール

| Phase | 内容 | 開始予定 | 完了予定 | 工数 | 状態 |
|-------|------|---------|---------|------|------|
| Phase 1 | 環境変数設定の追加 | 10/22 AM | 10/22 PM | 0.5日 | 予定 |
| Phase 2 | llm_factory.py拡張機能の実装 | 10/22 PM | 10/23 AM | 1.5日 | 予定 |
| Phase 3 | requirement_analysis.py更新 | 10/23 AM | 10/23 PM | 0.5日 | 予定 |
| Phase 4 | evaluator.py更新 | 10/23 PM | 10/23 PM | 0.5日 | 予定 |
| Phase 5 | interface_definition.py更新 | 10/23 PM | 10/23 PM | 0.5日 | 予定 |
| Phase 6 | validation.py更新 | 10/23 PM | 10/24 AM | 0.5日 | 予定 |
| Phase 7 | 単体テストの作成 | 10/24 AM | 10/24 PM | 1.0日 | 予定 |
| Phase 8 | 結合テストの実行 | 10/24 PM | 10/24 PM | 0.5日 | 予定 |
| Phase 9 | ドキュメント更新と最終報告 | 10/24 PM | 10/24 PM | 0.5日 | 予定 |
| Phase 10 | 品質チェックとPR作成 | 10/24 PM | 10/24 PM | 0.5日 | 予定 |

**合計工数**: 6.0日
**完了予定**: 2025-10-24

---

## 🎯 リスク管理

### リスク1: APIエラーのシミュレートが困難
**影響度**: 中
**対策**: 単体テストでMockを使用し、APIエラーを強制的に発生させる

### リスク2: コスト単価の変動
**影響度**: 低
**対策**: `ModelCostTracker.COST_TABLE`を容易に更新可能な設計

### リスク3: フォールバックの無限ループ
**影響度**: 高
**対策**: `max_retries`パラメータで最大リトライ回数を制限（デフォルト3回）

### リスク4: ログ出力量の増加
**影響度**: 低
**対策**: INFOレベルでサマリーのみ記録、詳細はDEBUGレベル

---

## 📝 メモ

### 技術的検討事項
- **非同期対応**: `create_llm_with_fallback()`は同期関数のまま（LLM作成はインスタンス化のみ）
- **トークンカウント**: LangChainの`usage_metadata`から取得（OpenAI/Anthropic/Google対応）
- **コスト計算の精度**: プロバイダー公式料金表に基づく（2025年10月時点）

### 今後の拡張可能性
- **動的コスト取得**: APIから最新の料金表を取得（将来的に検討）
- **プロバイダー追加**: Azure OpenAI, AWS Bedrock等（必要に応じて）
- **メトリクスの可視化**: Prometheus/Grafanaへのエクスポート（Phase 11以降）

---

**次ステップ**: Phase 1の実装開始

# 受入テスト計画書

**Issue**: #359
**作成日**: 2026-01-14
**作成者**: acceptance-plan-agent

---

## 1. 概要

### 対象Issue
- **番号**: #359
- **タイトル**: refactor(jobGeneratorV2): 3フェーズ統一ID方式によるアーキテクチャ簡素化
- **プロジェクト**: expertAgent
- **サイズ**: L（大規模リファクタリング）

### 参照ドキュメント
- Issue: #359
- 設計方針書: `dev-reports/feature/issue/359/design-policy.md`
- 作業計画書: `dev-reports/feature/issue/359/work-plan.md`

### テスト計画の目的
本受入テスト計画は、jobGeneratorV2の3フェーズ統一ID方式リファクタリングが設計方針通りに実装され、以下を達成していることを検証する：

1. 4フェーズから3フェーズへの削減（JOB_ANALYSIS, REGISTRATION, WORKFLOW_GEN）
2. 統一ID（task_id）によるデータ管理
3. LLM呼び出し回数の削減（17-18回から6回へ）
4. コード量の削減（904行から約300行へ）
5. 並列実行メカニズムの正常動作
6. ErrorRecoveryManagerのリトライ・ロールバック動作

---

## 2. 単体テスト結果レビュー

> **注意**: 本セクションはPRE-TDDフェーズで作成されています。TDD実装完了後に更新が必要です。

### カバレッジ（TDD実装後に記入）
- 現在: TBD
- 目標: 90%
- 判定: TBD

### テスト品質評価（TDD実装後に記入）
| 指標 | 値 | 判定 |
|------|-----|------|
| 総テスト数 | TBD | - |
| モック使用テスト数 | TBD | - |
| モック使用率 | TBD% | TBD |
| 実API呼び出しテスト数 | TBD | - |

### 期待される単体テストファイル
- `tests/unit/test_unified_task_identifier.py`
- `tests/unit/test_error_recovery.py`
- `tests/unit/test_parallel_executor.py`
- `tests/unit/test_job_analyzer.py`
- `tests/unit/test_validators.py`
- `tests/integration/test_job_generation_e2e.py`
- `tests/contract/test_taskflow_contract.py`

### 単体テストでカバーされるべき項目
1. UnifiedTaskIdentifierの等価性・ハッシュ性
2. ErrorRecoveryManagerのエラー分類とリカバリー戦略決定
3. 並列実行の成功/失敗/部分成功パターン
4. job_analyzerのLLM出力パース・バリデーション
5. TaskDependencyValidatorの循環参照検出
6. ValidationPipelineのチェーン実行

---

## 3. 受入条件分析

### AC-1: Phase 0 - 不要コードの調査と削除
- **原文**: Phase 0: 不要コードの調査と削除が完了している
- **分類**: 機能要件
- **テスト方法**: コード検査、Grepによる確認
- **モック使用**: 不可
- **検証ポイント**:
  1. TaskIdMappingクラスが削除されている
  2. SkipAggregatorクラスが削除されている
  3. 旧TASK_BREAKDOWNノードが削除されている
  4. 旧INTERFACE_DESIGNノードが削除されている

### AC-2: JOB_ANALYSISフェーズの統合
- **原文**: JOB_ANALYSISフェーズが1回のLLM呼び出しでタスク分解とインターフェース設計を完了する
- **分類**: 機能要件
- **テスト方法**: pytest + Langfuseトレース確認
- **モック使用**: 一部可（LLM呼び出しは実API使用）
- **検証ポイント**:
  1. job_analyzerノードが1回のLLM呼び出しで完了する
  2. 出力がJobAnalysisResponse形式（tasks[], interfaces{}, job_body_parameters）
  3. 各タスクにtask_idが割り当てられている
  4. Pydantic検証が実行される
  5. 依存関係検証（循環参照チェック）が実行される

### AC-3: REGISTRATIONフェーズの辞書形式出力
- **原文**: REGISTRATIONフェーズがtask_id -> task_master_idの辞書形式マッピングを返す
- **分類**: 機能要件
- **テスト方法**: pytest
- **モック使用**: 不可（実DB登録を確認）
- **検証ポイント**:
  1. 出力が辞書形式（Dict[str, str]）である
  2. インデックスベースのアクセスが存在しない
  3. BodyTemplateValidatorが実行される

### AC-4: WORKFLOW_GENフェーズの並列処理
- **原文**: WORKFLOW_GENフェーズが各タスクを並列で処理できる
- **分類**: 機能要件 + 非機能要件
- **テスト方法**: pytest + 実行時間計測
- **モック使用**: 一部可（外部APIのみ）
- **検証ポイント**:
  1. asyncio.gatherによる並列実行が行われる
  2. Semaphoreによる並列度制御（max_concurrent=5）
  3. 個別タスク失敗が他タスクに影響しない
  4. ParallelExecutionResultが正しく集約される
  5. 5タスクの処理が従来比50%以下の時間で完了

### AC-5: インデックスベースルックアップの排除
- **原文**: インデックスベースのルックアップが存在しない
- **分類**: 機能要件
- **テスト方法**: コード検査、Grep
- **モック使用**: 不可
- **検証ポイント**:
  1. `task_master_ids[idx]` 形式のアクセスが存在しない
  2. `tasks[i]` 形式のインデックスアクセスが存在しない
  3. すべてのルックアップがtask_idベース

### AC-6: サイレントフォールバックの排除
- **原文**: サイレントフォールバックが存在しない（データ不在時はエラー）
- **分類**: 機能要件
- **テスト方法**: pytest（エラーケーステスト）
- **モック使用**: 可
- **検証ポイント**:
  1. データ不在時に明示的なエラーが発生する
  2. 空データで続行するパスが存在しない
  3. エラーメッセージが具体的

### AC-7: 既存機能との互換性
- **原文**: 既存のジョブ生成機能と同等の結果を出力できる
- **分類**: 機能要件
- **テスト方法**: E2Eテスト
- **モック使用**: 不可
- **検証ポイント**:
  1. `/api/v1/job-generator` エンドポイントが動作する
  2. レスポンス形式が既存と同一
  3. 生成されたワークフローがgraphAiServerで実行可能

### AC-8: 3フェーズ統一ID方式準拠
- **原文**: コードベースが提案するグラフ構造（3フェーズ統一ID方式）に準拠している
- **分類**: 機能要件
- **テスト方法**: コード検査 + E2Eテスト
- **モック使用**: 不可
- **検証ポイント**:
  1. フェーズが3つ（JOB_ANALYSIS, REGISTRATION, WORKFLOW_GEN）
  2. 旧4フェーズ構造のコードが存在しない
  3. オーケストレーターコードが300行以下

### AC-9: ErrorRecoveryManagerの動作
- **原文**: ErrorRecoveryManagerが期待通りのリトライ・ロールバック動作をする
- **分類**: 機能要件
- **テスト方法**: pytest（エラーシナリオテスト）
- **モック使用**: 可（エラー注入）
- **検証ポイント**:
  1. RETRY_CURRENT戦略が正しく動作する
  2. RETRY_WITH_FEEDBACK戦略が正しく動作する
  3. ROLLBACK_TO_ANALYSIS戦略が正しく動作する
  4. FAIL_FAST戦略が正しく動作する
  5. フェーズごとの最大リトライ回数（3回）が遵守される
  6. 全体の最大リトライ回数（5回）が遵守される

### AC-10: LLMプロンプトの内容
- **原文**: job_analyzerのプロンプトがタスク分解原則・JSON Schema生成ルールを含んでいる / workflow_generatorのプロンプトがTaskFlow V2仕様を含んでいる
- **分類**: 機能要件
- **テスト方法**: Grep + Langfuseトレース確認
- **モック使用**: 不可
- **検証ポイント**:
  1. job_analyzerプロンプトにタスク分解原則が含まれる
  2. job_analyzerプロンプトにJSON Schema生成ルールが含まれる
  3. workflow_generatorプロンプトにTaskFlow V2仕様が含まれる

### AC-11: myVaultモデル設定
- **原文**: myVaultからモデル設定が正しく読み込まれる / デフォルトモデル（gemini-3-flash-preview）が正しく設定されている
- **分類**: 機能要件
- **テスト方法**: E2Eテスト + Langfuseトレース確認
- **モック使用**: 不可
- **検証ポイント**:
  1. myVaultの `JOB_GENERATOR_ANALYSIS_MODEL` が読み込まれる
  2. myVaultの `WORKFLOW_GENERATOR_MODEL` が読み込まれる
  3. 未設定時は `gemini-3-flash-preview` が使用される

### AC-12: バリデーション実行
- **原文**: 各フェーズでバリデーションが実行される
- **分類**: 機能要件
- **テスト方法**: pytest + ログ確認
- **モック使用**: 可（エラー注入）
- **検証ポイント**:
  1. JOB_ANALYSIS: Pydantic検証が実行される
  2. JOB_ANALYSIS: 依存関係検証（循環参照・存在チェック）が実行される
  3. REGISTRATION: BodyTemplateValidatorが実行される
  4. WORKFLOW_GEN: ValidationPipelineが実行される
  5. バリデーションエラー時に適切なリトライ/ロールバックが発生する

### AC-13: デバッグログ出力
- **原文**: DEBUGレベルでLLMプロンプト・レスポンス全文が出力される / INFOレベルでフェーズ遷移・タスク処理状況が出力される
- **分類**: 機能要件
- **テスト方法**: ログ出力確認
- **モック使用**: 不可
- **検証ポイント**:
  1. DEBUG: LLMプロンプト全文が出力される
  2. DEBUG: LLMレスポンス全文が出力される
  3. INFO: フェーズ開始/終了が出力される
  4. INFO: タスク処理状況が出力される
  5. WARNING: リトライ発生時に出力される

### AC-14: Langfuseトレース
- **原文**: ジョブ生成リクエストごとにトレースが作成される
- **分類**: 機能要件
- **テスト方法**: Langfuseダッシュボード確認
- **モック使用**: 不可
- **検証ポイント**:
  1. トレース構造がJOB_ANALYSIS -> REGISTRATION -> WORKFLOW_GEN
  2. 各LLM呼び出し（Generation）にmodel, input, output, usageが記録される
  3. フェーズごとのSpanが正しく親子関係を持つ
  4. エラー発生時にlevel=ERRORが記録される

### AC-15: テストカバレッジ
- **原文**: 単体テストカバレッジ90%以上 / 結合テストカバレッジ50%以上
- **分類**: 非機能要件
- **テスト方法**: pytest --cov
- **モック使用**: 可
- **検証ポイント**:
  1. 単体テストカバレッジが90%以上
  2. 結合テストカバレッジが50%以上

### AC-16: Contract Test
- **原文**: Contract Testが導入されている
- **分類**: 機能要件
- **テスト方法**: pytest
- **モック使用**: 不可
- **検証ポイント**:
  1. expertAgent <-> graphAiServer間のContract Testが存在する
  2. スキーマ互換性が検証される
  3. テストがパスする

---

## 4. 設計方針検証

### DP-1: 3フェーズ統一ID方式
- **設計方針**: Phase 1: JOB_ANALYSIS（タスク分解+インターフェース設計統合）、Phase 2: REGISTRATION（DB登録）、Phase 3: WORKFLOW_GEN（並列実行）
- **検証方法**: コード構造確認 + E2Eテスト
- **テスト項目**:
  1. orchestrator.pyが3フェーズ構造で実装されている
  2. 旧4フェーズ（TASK_BREAKDOWN, INTERFACE_DESIGN, REGISTRATION, WORKFLOW_GEN）のコードが削除されている
  3. E2Eで3フェーズ遷移が確認できる

### DP-2: 統一IDパターン
- **設計方針**: UnifiedTaskIdentifierクラスによるtask_id管理、task_idのみで等価判定
- **検証方法**: 単体テスト + コード検査
- **テスト項目**:
  1. UnifiedTaskIdentifierクラスが存在する
  2. `__hash__`と`__eq__`がtask_idのみで判定している
  3. 辞書のキーとして使用可能

### DP-3: 並列実行パターン
- **設計方針**: asyncio.gather + Semaphoreによる並列実行、例外は個別キャッチ
- **検証方法**: 単体テスト + E2Eテスト
- **テスト項目**:
  1. `parallel_workflow_generation`関数が存在する
  2. max_concurrent=5（デフォルト）が設定されている
  3. タイムアウト処理が実装されている
  4. TaskResult/ParallelExecutionResultが正しく使用されている

### DP-4: エラーハンドリング設計
- **設計方針**: ErrorRecoveryManager + フェーズ別エラー契約
- **検証方法**: 単体テスト
- **テスト項目**:
  1. ErrorRecoveryManagerクラスが存在する
  2. フェーズ別エラー契約（JobAnalysisErrorContract等）が存在する
  3. RecoveryStrategy列挙型が正しく定義されている
  4. エスカレーション機能が実装されている

### DP-5: バリデーションパイプライン
- **設計方針**: ValidationPipelineによるチェーン検証（構造→スキーマ→依存関係→意味的）
- **検証方法**: 単体テスト
- **テスト項目**:
  1. ValidationPipelineクラスが存在する
  2. StructuralValidator, SchemaValidator, DependencyValidator, SemanticValidatorが存在する
  3. バリデーション結果がValidationResult形式で返却される

### DP-6: データフロー設計
- **設計方針**: JobGenerationRequest -> JobAnalysisResponse -> RegistrationOutput -> WorkflowGenPhaseOutput
- **検証方法**: E2Eテスト
- **テスト項目**:
  1. 各フェーズ間でtask_idベースのデータ受け渡しが行われている
  2. インデックスベースのデータアクセスが存在しない

### DP-7: モデル設定方針
- **設計方針**: myVaultでモデル設定管理、デフォルトはgemini-3-flash-preview
- **検証方法**: E2Eテスト + Langfuseトレース確認
- **テスト項目**:
  1. myVaultから`JOB_GENERATOR_ANALYSIS_MODEL`が取得される
  2. myVaultから`WORKFLOW_GENERATOR_MODEL`が取得される
  3. 未設定時はデフォルトモデルが使用される

---

## 5. デッドコード検証計画

### F-1: UnifiedTaskIdentifier
- **ファイル**: `expertAgent/aiagent/langgraph/jobGeneratorV2/types.py`
- **種別**: class
- **期待される呼び出し元**: orchestrator.py, job_analyzer.py, master_manager.py, workflow_generator.py
- **検証方法**:
  ```bash
  grep -rn "UnifiedTaskIdentifier" expertAgent/aiagent/langgraph/jobGeneratorV2/ --include="*.py"
  ```
- **E2E確認**: ジョブ生成API呼び出しで内部的に使用されることを確認

### F-2: ErrorRecoveryManager
- **ファイル**: `expertAgent/aiagent/langgraph/jobGeneratorV2/error_recovery.py`
- **種別**: class
- **期待される呼び出し元**: orchestrator.py
- **検証方法**:
  ```bash
  grep -rn "ErrorRecoveryManager" expertAgent/aiagent/langgraph/jobGeneratorV2/ --include="*.py"
  ```
- **E2E確認**: エラー発生時のリトライ動作で使用されることを確認

### F-3: parallel_workflow_generation
- **ファイル**: `expertAgent/aiagent/langgraph/jobGeneratorV2/parallel_executor.py`
- **種別**: function
- **期待される呼び出し元**: orchestrator.py
- **検証方法**:
  ```bash
  grep -rn "parallel_workflow_generation" expertAgent/aiagent/langgraph/jobGeneratorV2/ --include="*.py"
  ```
- **E2E確認**: 複数タスクのワークフロー生成時に並列実行されることを確認

### F-4: TaskDependencyValidator
- **ファイル**: `expertAgent/aiagent/langgraph/jobGeneratorV2/validators/task_dependency.py`
- **種別**: class
- **期待される呼び出し元**: job_analyzer.py, ValidationPipeline
- **検証方法**:
  ```bash
  grep -rn "TaskDependencyValidator" expertAgent/aiagent/langgraph/jobGeneratorV2/ --include="*.py"
  ```
- **E2E確認**: 循環参照を持つタスク定義時にエラーが発生することを確認

### F-5: job_analyzer
- **ファイル**: `expertAgent/aiagent/langgraph/jobGeneratorV2/nodes/job_analyzer.py`
- **種別**: module
- **期待される呼び出し元**: orchestrator.py
- **検証方法**:
  ```bash
  grep -rn "job_analyzer" expertAgent/aiagent/langgraph/jobGeneratorV2/ --include="*.py"
  ```
- **E2E確認**: ジョブ生成APIでLangfuseトレースにjob_analyzerが記録されることを確認

### F-6: 削除対象コード（存在しないことを確認）
- **対象**: TaskIdMapping, SkipAggregator, 旧TASK_BREAKDOWN, 旧INTERFACE_DESIGN
- **種別**: class/module
- **検証方法**:
  ```bash
  grep -rn "TaskIdMapping\|SkipAggregator" expertAgent/aiagent/langgraph/jobGeneratorV2/ --include="*.py"
  ```
- **期待結果**: 検索結果が0件

---

## 6. テスト環境

### 必須サービス
| サービス | URL | ヘルスチェック |
|---------|-----|--------------|
| ExpertAgent | http://localhost:8004 | GET /health |
| GraphAiServer | http://localhost:8005 | GET /health |
| MyVault | http://localhost:8003 | GET /health |
| JobQueue | http://localhost:8001 | GET /health |

### 起動コマンド
```bash
# 推奨: ハイブリッドモード（Platform=Docker, Agent=ローカル）
./scripts/dev-hybrid.sh

# または: Docker全環境
make dev-all
```

### 環境変数
| 変数名 | 説明 | 必須 |
|--------|------|------|
| OPENAI_API_KEY | OpenAI APIキー | No |
| ANTHROPIC_API_KEY | Anthropic APIキー | No |
| GOOGLE_API_KEY | Google AI APIキー（Gemini用） | Yes |
| LANGFUSE_HOST | LangfuseホストURL | Yes |
| LANGFUSE_PUBLIC_KEY | Langfuse公開キー | Yes |
| LANGFUSE_SECRET_KEY | Langfuse秘密キー | Yes |

### テストデータ
- **基本ジョブ要求**: "PDFファイルをGoogle Driveにアップロードして完了通知をSlackに送る"
- **複雑なジョブ要求**: "CSVファイルを読み込んで、データを集計し、グラフを作成してレポートを生成し、メールで送信する"
- **エラーケース**: "存在しないAPIを呼び出して結果を処理する"

---

## 7. テスト項目

### TC-001: 基本的なジョブ生成（2タスク）
- **テスト観点**: 3フェーズ統一ID方式の基本動作確認
- **関連する受入条件**: AC-2, AC-3, AC-4, AC-7
- **関連する設計方針**: DP-1, DP-2, DP-6
- **テスト種別**: E2E
- **テスト方法**: curl + pytest
- **前提条件**:
  1. ExpertAgentが起動済み
  2. GraphAiServerが起動済み
  3. GOOGLE_API_KEYが設定済み
- **テスト手順**:
  1. `/api/v1/job-generator` に2タスクのジョブ要求を送信
  2. レスポンスのステータスとタスク数を確認
  3. Langfuseでトレース構造を確認
- **期待結果**:
  - HTTPステータス: 200
  - status: "success"
  - task_breakdown数: 2
  - LLM呼び出し回数: 3（job_analyzer: 1回, workflow_generator: 2回）
- **curlコマンド**:
  ```bash
  curl -s -X POST http://localhost:8004/api/v1/job-generator \
    -H "Content-Type: application/json" \
    -d '{
      "user_requirement": "PDFファイルをGoogle Driveにアップロードして完了通知をSlackに送る",
      "max_retry": 3
    }'
  ```
- **pytestメソッド**: `test_tc_001_basic_job_generation_two_tasks`

### TC-002: 複雑なワークフロー生成（5タスク）
- **テスト観点**: 並列実行メカニズムとパフォーマンス
- **関連する受入条件**: AC-4, AC-7, AC-8
- **関連する設計方針**: DP-3, DP-1
- **テスト種別**: E2E + パフォーマンス
- **テスト方法**: curl + 時間計測
- **前提条件**:
  1. ExpertAgentが起動済み
  2. GraphAiServerが起動済み
- **テスト手順**:
  1. `/api/v1/job-generator` に5タスクのジョブ要求を送信
  2. 実行時間を計測
  3. LLM呼び出し回数を確認
- **期待結果**:
  - task_breakdown数: 5
  - LLM呼び出し回数: 6（job_analyzer: 1回, workflow_generator: 5回並列）
  - 実行時間: 従来比50%以下
- **curlコマンド**:
  ```bash
  time curl -s -X POST http://localhost:8004/api/v1/job-generator \
    -H "Content-Type: application/json" \
    -d '{
      "user_requirement": "CSVファイルを読み込んで、データを集計し、グラフを作成してレポートを生成し、メールで送信する",
      "max_retry": 3
    }'
  ```
- **pytestメソッド**: `test_tc_002_complex_workflow_five_tasks`

### TC-003: ErrorRecoveryManager - RETRY_CURRENT
- **テスト観点**: 一時的エラー時のリトライ動作
- **関連する受入条件**: AC-9, AC-12
- **関連する設計方針**: DP-4
- **テスト種別**: 結合
- **テスト方法**: pytest（エラー注入）
- **前提条件**:
  1. テスト用のエラー注入機構が実装済み
- **テスト手順**:
  1. LLM API呼び出しで一時的エラーを発生させる
  2. リトライが実行されることを確認
  3. 最終的に成功することを確認
- **期待結果**:
  - RETRY_CURRENT戦略が選択される
  - 最大3回までリトライが実行される
  - ログにリトライ発生が記録される
- **pytestメソッド**: `test_tc_003_error_recovery_retry_current`

### TC-004: ErrorRecoveryManager - ROLLBACK_TO_ANALYSIS
- **テスト観点**: 重大なエラー時のロールバック動作
- **関連する受入条件**: AC-9
- **関連する設計方針**: DP-4
- **テスト種別**: 結合
- **テスト方法**: pytest（エラー注入）
- **前提条件**:
  1. テスト用のエラー注入機構が実装済み
- **テスト手順**:
  1. WORKFLOW_GENフェーズで全タスク失敗を発生させる
  2. ROLLBACK_TO_ANALYSISが実行されることを確認
  3. JOB_ANALYSISから再実行されることを確認
- **期待結果**:
  - ROLLBACK_TO_ANALYSIS戦略が選択される
  - JOB_ANALYSISフェーズから再開される
- **pytestメソッド**: `test_tc_004_error_recovery_rollback_to_analysis`

### TC-005: 並列実行の部分成功
- **テスト観点**: 一部タスク失敗時の継続動作
- **関連する受入条件**: AC-4, AC-9
- **関連する設計方針**: DP-3, DP-4
- **テスト種別**: 結合
- **テスト方法**: pytest
- **前提条件**:
  1. 複数タスクのジョブ要求
  2. 一部タスクでエラー発生設定
- **テスト手順**:
  1. 3タスクのうち1タスクのみ失敗させる
  2. ParallelExecutionResultを確認
  3. 成功タスクが正常に登録されることを確認
- **期待結果**:
  - partial_success = True
  - successful_tasks数: 2
  - failed_tasks数: 1
  - 成功タスクのワークフローは登録される
- **pytestメソッド**: `test_tc_005_parallel_execution_partial_success`

### TC-006: インデックスベースルックアップの不在確認
- **テスト観点**: 設計方針に反するコードの不在
- **関連する受入条件**: AC-5
- **関連する設計方針**: DP-2
- **テスト種別**: コード検査
- **テスト方法**: Grep
- **前提条件**: なし
- **テスト手順**:
  1. orchestrator.pyでインデックスアクセスを検索
  2. 関連ファイルでインデックスアクセスを検索
- **期待結果**:
  - `task_master_ids[idx]` が0件
  - `tasks[i]` 形式のアクセスが0件（イテレーション除く）
- **検証コマンド**:
  ```bash
  grep -n "\[idx\]\|\[i\]" expertAgent/aiagent/langgraph/jobGeneratorV2/orchestrator.py
  ```
- **pytestメソッド**: `test_tc_006_no_index_based_lookup`

### TC-007: サイレントフォールバックの不在確認
- **テスト観点**: データ不在時のエラー発生
- **関連する受入条件**: AC-6
- **関連する設計方針**: DP-4
- **テスト種別**: 結合
- **テスト方法**: pytest
- **前提条件**: なし
- **テスト手順**:
  1. 存在しないtask_idでルックアップを試みる
  2. 明示的なエラーが発生することを確認
- **期待結果**:
  - KeyError または カスタム例外が発生
  - 空データで続行しない
- **pytestメソッド**: `test_tc_007_no_silent_fallback`

### TC-008: myVaultモデル設定読み込み
- **テスト観点**: 外部設定の正しい読み込み
- **関連する受入条件**: AC-11
- **関連する設計方針**: DP-7
- **テスト種別**: E2E
- **テスト方法**: curl + Langfuseトレース確認
- **前提条件**:
  1. myVaultにモデル設定が登録済み
  2. Langfuseが起動済み
- **テスト手順**:
  1. myVaultに `JOB_GENERATOR_ANALYSIS_MODEL` を設定
  2. ジョブ生成APIを呼び出す
  3. Langfuseで使用モデルを確認
- **期待結果**:
  - Langfuseトレースに設定したモデル名が記録される
- **pytestメソッド**: `test_tc_008_myvault_model_setting`

### TC-009: デフォルトモデルの使用
- **テスト観点**: 未設定時のデフォルト値適用
- **関連する受入条件**: AC-11
- **関連する設計方針**: DP-7
- **テスト種別**: E2E
- **テスト方法**: curl + Langfuseトレース確認
- **前提条件**:
  1. myVaultにモデル設定が未登録
  2. Langfuseが起動済み
- **テスト手順**:
  1. myVaultからモデル設定を削除
  2. ジョブ生成APIを呼び出す
  3. Langfuseで使用モデルを確認
- **期待結果**:
  - Langfuseトレースに `gemini-3-flash-preview` が記録される
- **pytestメソッド**: `test_tc_009_default_model_usage`

### TC-010: LangfuseトレースStructure
- **テスト観点**: 観測可能性の正常動作
- **関連する受入条件**: AC-14
- **関連する設計方針**: なし
- **テスト種別**: E2E
- **テスト方法**: curl + Langfuseダッシュボード確認
- **前提条件**:
  1. Langfuseが起動済み
- **テスト手順**:
  1. ジョブ生成APIを呼び出す
  2. Langfuseダッシュボードでトレースを確認
- **期待結果**:
  - トレース構造: JobGeneration -> JOB_ANALYSIS -> REGISTRATION -> WORKFLOW_GEN
  - 各LLM呼び出しにmodel, input, output, usageが記録
  - フェーズごとのSpanが正しく親子関係
- **pytestメソッド**: `test_tc_010_langfuse_trace_structure`

### TC-011: Contract Test（expertAgent <-> graphAiServer）
- **テスト観点**: サービス間インターフェース互換性
- **関連する受入条件**: AC-16
- **関連する設計方針**: なし
- **テスト種別**: Contract Test
- **テスト方法**: pytest
- **前提条件**:
  1. graphAiServerが起動済み
- **テスト手順**:
  1. Contract Testを実行
  2. 生成されたワークフローがgraphAiServerで実行可能か確認
- **期待結果**:
  - Contract Testが全パス
  - スキーマ互換性エラーなし
- **pytestメソッド**: `test_tc_011_contract_test_expert_graphai`

### TC-012: オーケストレーターコード行数
- **テスト観点**: コード削減目標の達成
- **関連する受入条件**: AC-8
- **関連する設計方針**: DP-1
- **テスト種別**: コード検査
- **テスト方法**: wc -l
- **前提条件**: なし
- **テスト手順**:
  1. orchestrator.pyの行数をカウント
- **期待結果**:
  - 行数: 300行以下
- **検証コマンド**:
  ```bash
  wc -l expertAgent/aiagent/langgraph/jobGeneratorV2/orchestrator.py
  ```
- **pytestメソッド**: `test_tc_012_orchestrator_code_lines`

### TC-013: 削除対象コードの不在確認
- **テスト観点**: Phase 0の完了確認
- **関連する受入条件**: AC-1
- **関連する設計方針**: なし
- **テスト種別**: コード検査
- **テスト方法**: Grep
- **前提条件**: なし
- **テスト手順**:
  1. TaskIdMapping, SkipAggregatorを検索
  2. 旧フェーズ関連コードを検索
- **期待結果**:
  - TaskIdMapping: 0件
  - SkipAggregator: 0件
  - 旧TASK_BREAKDOWNノード: 削除済み
  - 旧INTERFACE_DESIGNノード: 削除済み
- **検証コマンド**:
  ```bash
  grep -rn "TaskIdMapping\|SkipAggregator" expertAgent/aiagent/langgraph/jobGeneratorV2/
  ```
- **pytestメソッド**: `test_tc_013_dead_code_removed`

### TC-014: TaskDependencyValidator - 循環参照検出
- **テスト観点**: 依存関係バリデーション
- **関連する受入条件**: AC-12
- **関連する設計方針**: DP-5
- **テスト種別**: 単体
- **テスト方法**: pytest
- **前提条件**: なし
- **テスト手順**:
  1. 循環参照を含むタスク定義を作成
  2. TaskDependencyValidatorで検証
- **期待結果**:
  - ValidationResult.is_valid = False
  - エラーメッセージに循環参照の説明が含まれる
- **pytestメソッド**: `test_tc_014_task_dependency_circular_reference`

### TC-015: DEBUGログ出力確認
- **テスト観点**: デバッグ情報の出力
- **関連する受入条件**: AC-13
- **関連する設計方針**: なし
- **テスト種別**: E2E
- **テスト方法**: ログ出力確認
- **前提条件**:
  1. ログレベルをDEBUGに設定
- **テスト手順**:
  1. ジョブ生成APIを呼び出す
  2. ログ出力を確認
- **期待結果**:
  - LLMプロンプト全文が出力される
  - LLMレスポンス全文が出力される
- **pytestメソッド**: `test_tc_015_debug_log_output`

---

## 8. テスト実行計画

### 実行順序
1. **サービス起動確認**（ヘルスチェック）
   ```bash
   curl -sf http://localhost:8004/health && echo "ExpertAgent: OK"
   curl -sf http://localhost:8005/health && echo "GraphAiServer: OK"
   curl -sf http://localhost:8003/health && echo "MyVault: OK"
   ```

2. **コード検査テスト**（TC-006, TC-012, TC-013）
   - インデックスベースルックアップの不在確認
   - オーケストレーターコード行数確認
   - 削除対象コードの不在確認

3. **単体テスト実行**
   ```bash
   cd expertAgent && uv run pytest tests/unit/langgraph/jobGeneratorV2/ -v --cov
   ```

4. **結合テスト実行**（TC-003, TC-004, TC-005, TC-007, TC-014）
   ```bash
   cd expertAgent && uv run pytest tests/integration/ -v -k "job_generator"
   ```

5. **Contract Test実行**（TC-011）
   ```bash
   cd expertAgent && uv run pytest tests/contract/test_taskflow_contract.py -v
   ```

6. **E2Eテスト実行**（TC-001, TC-002, TC-008, TC-009, TC-010, TC-015）
   ```bash
   cd expertAgent && uv run pytest tests/acceptance/test_issue_359_acceptance.py -v
   ```

7. **Langfuseダッシュボード確認**
   - トレース構造の目視確認
   - コスト・レイテンシ分析

### 成功基準
- [ ] TC-001: 基本的なジョブ生成がパス
- [ ] TC-002: 複雑なワークフロー生成がパス（実行時間従来比50%以下）
- [ ] TC-003: ErrorRecoveryManager RETRY_CURRENTがパス
- [ ] TC-004: ErrorRecoveryManager ROLLBACK_TO_ANALYSISがパス
- [ ] TC-005: 並列実行の部分成功がパス
- [ ] TC-006: インデックスベースルックアップが存在しない
- [ ] TC-007: サイレントフォールバックが存在しない
- [ ] TC-008: myVaultモデル設定読み込みがパス
- [ ] TC-009: デフォルトモデル使用がパス
- [ ] TC-010: Langfuseトレース構造が正しい
- [ ] TC-011: Contract Testがパス
- [ ] TC-012: オーケストレーターコードが300行以下
- [ ] TC-013: 削除対象コードが存在しない
- [ ] TC-014: TaskDependencyValidator循環参照検出がパス
- [ ] TC-015: DEBUGログ出力がパス
- [ ] 単体テストカバレッジ90%以上
- [ ] 結合テストカバレッジ50%以上
- [ ] すべての受入条件が検証済み

---

## 9. 補足事項

### 関連Issue
- Issue #342: jobGeneratorV2のバグ修正（TaskIdMapping, SkipAggregator追加）- 本Issueで削除予定
- Issue #348: TaskFlow条件分岐対応
- Issue #357: JSON Schema Single Source of Truth導入
- Issue #358: body_templateバリデーション追加

### リスクと対策
| リスク | 影響度 | 発生確率 | 対策 |
|-------|-------|---------|------|
| 既存機能への影響 | 高 | 中 | アダプター層での互換性維持、段階的移行 |
| 性能劣化 | 中 | 低 | 並列実行の最適化、プロファイリング実施 |
| LLM出力の品質低下 | 高 | 中 | プロンプト調整、複数モデルでのテスト |
| Contract Test失敗 | 中 | 中 | graphAiServer側との事前調整 |

### テスト実施の注意点
1. **LLM APIコスト**: E2Eテストは実際のLLM APIを使用するため、テスト回数を最小限に抑える
2. **並列テスト**: 並列実行テストはAPIレート制限に注意
3. **Langfuse確認**: トレース確認は手動で行う必要がある（自動化困難）
4. **環境変数**: テスト前に必要な環境変数がすべて設定されていることを確認

---

**作成完了**: 2026-01-14
**次ステップ**: TDD実装後に単体テスト結果レビューセクションを更新

# 作業計画: GraphAI Workflow Generator API

**作成日**: 2025-10-21
**予定工数**: 9人日
**完了予定**: 2025-10-30
**ブランチ**: feature/issue/108

---

## 📋 プロジェクト概要

### ビジネス要求

Job Generator API (`/api/v1/job-generator`) で生成されたタスク情報を基に、GraphAI上で実行可能なLLMワークフローYAMLファイルを自動生成・登録・検証するAIエージェントAPIを実装する。

### 機能概要

- **エンドポイント**: `POST /api/v1/workflow-generator`
- **入力**: `job_master_id` OR `task_master_id` (XOR制約)
- **主要機能**:
  1. JobMaster/TaskMaster情報をJobqueueClientで取得
  2. LLMでGraphAI workflow YAMLを生成
  3. graphAiServerに自動登録
  4. サンプル入力で動作確認
  5. 非LLM検証で結果チェック
  6. エラー時は自己修復ループ（最大3回リトライ）

### 技術スタック

| 要素 | 技術 |
|------|------|
| Framework | FastAPI + LangGraph |
| LLM | Gemini 2.5 Flash (primary), Claude Haiku 4.5 (fallback) |
| Validation | JSON Schema + Rule-based |
| Client | JobqueueClient (REST API) |
| Output | GraphAI YAML files |

---

## 📚 参考ドキュメント

**必須参照**:
- ✅ [GraphAI Workflow Generation Rules](../../../graphAiServer/docs/GRAPHAI_WORKFLOW_GENERATION_RULES.md)
- ✅ [アーキテクチャ概要](../../../docs/design/architecture-overview.md)
- ✅ [設計方針 (design-policy.md)](./design-policy.md)

**推奨参照**:
- ✅ [環境変数管理](../../../docs/design/environment-variables.md)
- ✅ [myVault連携](../../../docs/design/myvault-integration.md)
- ✅ [開発ガイド (CLAUDE.md)](../../../CLAUDE.md)

---

## 📊 Phase分解

### Phase 1: expertAgent基盤実装 (2日)

**目的**: API基盤とデータ取得ロジックの実装

#### タスク詳細

- [ ] **1.1 スキーマ定義** (2時間)
  - `app/schemas/workflow_generator.py` 作成
  - `WorkflowGeneratorRequest` (XOR validator実装)
  - `WorkflowGeneratorResponse`
  - `WorkflowResult`
  - 単体テスト: `tests/unit/test_workflow_generator_schemas.py`

- [ ] **1.2 TaskDataFetcher実装** (3時間)
  - `aiagent/langgraph/workflowGeneratorAgents/utils/task_data_fetcher.py` 作成
  - `fetch_task_masters_by_job_master_id()` メソッド
  - `fetch_task_master_by_id()` メソッド
  - JobqueueClient統合（`get_job_master()`, `get_task_master()`, `get_interface_master()`）
  - 単体テスト: `tests/unit/test_task_data_fetcher.py` (モック使用)

- [ ] **1.3 APIエンドポイント実装** (3時間)
  - `app/api/v1/workflow_generator_endpoints.py` 作成
  - `POST /api/v1/workflow-generator` エンドポイント
  - XOR constraint validation
  - エラーハンドリング（400, 404, 422, 500）
  - `app/main.py` にルーター追加
  - 統合テスト: `tests/integration/test_workflow_generator_api.py`

- [ ] **1.4 Phase 1完了確認** (0.5時間)
  - `scripts/pre-push-check-all.sh` 実行
  - エラーゼロを確認
  - Phase 1作業記録作成: `phase-1-progress.md`

**成果物**:
- ✅ API基盤コード（3ファイル）
- ✅ 単体テスト（カバレッジ90%以上）
- ✅ 統合テスト（基本動作確認）
- ✅ 品質チェック合格

---

### Phase 2: graphAiServer API実装 (1日)

**目的**: Workflow登録エンドポイントの実装

#### タスク詳細

- [ ] **2.1 スキーマ定義** (1時間)
  - `graphAiServer/app/schemas/workflow.py` 作成
  - `WorkflowRegisterRequest` (workflow_name, yaml_content)
  - `WorkflowRegisterResponse` (status, file_path, errors)

- [ ] **2.2 登録エンドポイント実装** (2時間)
  - `graphAiServer/app/api/v1/workflow_endpoints.py` 作成
  - `POST /api/v1/workflows/register` エンドポイント
  - YAML保存先: `graphAiServer/config/graphai/{workflow_name}.yml`
  - YAML構文検証（PyYAML使用）
  - エラーハンドリング（400, 500）
  - `graphAiServer/app/main.py` にルーター追加

- [ ] **2.3 テスト実装** (2時間)
  - 単体テスト: `graphAiServer/tests/unit/test_workflow_endpoints.py`
  - 統合テスト: `graphAiServer/tests/integration/test_workflow_api.py`
  - テストケース:
    - 正常系: YAML保存成功
    - 異常系: 不正なYAML構文
    - 異常系: ファイル書き込み権限エラー

- [ ] **2.4 Phase 2完了確認** (0.5時間)
  - `scripts/pre-push-check-all.sh` 実行
  - エラーゼロを確認
  - Phase 2作業記録作成: `phase-2-progress.md`

**成果物**:
- ✅ graphAiServer登録API（2ファイル）
- ✅ YAML保存ロジック
- ✅ 単体・統合テスト
- ✅ 品質チェック合格

---

### Phase 3: LangGraph Agent実装 (3日)

**目的**: ワークフロー生成・検証・自己修復のAIエージェント実装

#### タスク詳細

- [ ] **3.1 State定義** (1時間)
  - `aiagent/langgraph/workflowGeneratorAgents/state.py` 作成
  - `WorkflowGeneratorState` TypedDict定義
  - フィールド: task_data, generated_workflows, validation_results, errors, retry_count

- [ ] **3.2 Generator Node実装** (4時間)
  - `aiagent/langgraph/workflowGeneratorAgents/nodes/generator_node.py`
  - LLM呼び出し（Gemini 2.5 Flash primary, Claude Haiku 4.5 fallback）
  - プロンプト設計:
    - タスク情報（name, description, input/output schema）
    - 利用可能capabilities（graphai_capabilities.yaml, expert_agent_capabilities.yaml）
    - GraphAI YAML生成ルール
  - YAML構文検証
  - 単体テスト: `tests/unit/test_generator_node.py`

- [ ] **3.3 Sample Input Generator Node実装** (2時間)
  - `aiagent/langgraph/workflowGeneratorAgents/nodes/sample_input_generator_node.py`
  - 入力InterfaceMaster JSON SchemaからサンプルJSON生成
  - LLM使用（簡易プロンプト）
  - 単体テスト: `tests/unit/test_sample_input_generator_node.py`

- [ ] **3.4 Workflow Tester Node実装** (3時間)
  - `aiagent/langgraph/workflowGeneratorAgents/nodes/workflow_tester_node.py`
  - graphAiServer登録API呼び出し
  - graphAiServer実行API呼び出し（`POST /api/v1/execute`）
  - レスポンス取得・エラーログ記録
  - 単体テスト: `tests/unit/test_workflow_tester_node.py` (モック使用)

- [ ] **3.5 Validator Node実装** (3時間)
  - `aiagent/langgraph/workflowGeneratorAgents/nodes/validator_node.py`
  - `ExecutionValidator` クラス実装:
    - HTTP status check (200-299 = success)
    - Error log analysis (keyword: "error", "exception", "failed")
    - JSON Schema validation (output vs expected_output_schema)
  - 検証結果: `(is_valid: bool, errors: list[str])`
  - 単体テスト: `tests/unit/test_validator_node.py`

- [ ] **3.6 Self-Repair Node実装** (2時間)
  - `aiagent/langgraph/workflowGeneratorAgents/nodes/self_repair_node.py`
  - エラーフィードバックをLLMに提供
  - 修正YAML生成
  - リトライカウント管理（最大3回）
  - 単体テスト: `tests/unit/test_self_repair_node.py`

- [ ] **3.7 LangGraph構築** (3時間)
  - `aiagent/langgraph/workflowGeneratorAgents/graph.py`
  - StateGraph定義
  - ノード追加: generator → sample_input_generator → workflow_tester → validator
  - 条件分岐: validator成功 → END, 失敗 → self_repair → generator (max 3回)
  - グラフコンパイル
  - 統合テスト: `tests/integration/test_workflow_generator_agent.py`

- [ ] **3.8 Phase 3完了確認** (0.5時間)
  - `scripts/pre-push-check-all.sh` 実行
  - エラーゼロを確認
  - Phase 3作業記録作成: `phase-3-progress.md`

**成果物**:
- ✅ LangGraph Agent（7ファイル）
- ✅ 各nodeの単体テスト
- ✅ Agent統合テスト
- ✅ 品質チェック合格

---

### Phase 4: 統合テスト・品質担保 (1.5日)

**目的**: E2Eテストとカバレッジ確認

#### タスク詳細

- [ ] **4.1 E2Eテスト作成** (3時間)
  - `tests/integration/test_e2e_workflow_generator.py`
  - テストシナリオ:
    - ケース1: job_master_id指定 → 複数workflow生成成功
    - ケース2: task_master_id指定 → 単一workflow生成成功
    - ケース3: 検証失敗 → 自己修復ループ → 成功
    - ケース4: 3回リトライ失敗 → partial_success
  - 前提条件: Jobqueue API / graphAiServer起動

- [ ] **4.2 カバレッジ確認** (2時間)
  - 単体テストカバレッジ: 90%以上
  - 結合テストカバレッジ: 50%以上
  - HTMLレポート生成: `htmlcov/index.html`
  - 未カバー箇所の補足テスト追加

- [ ] **4.3 エラーハンドリング検証** (2時間)
  - 異常系テスト:
    - JobqueueClient API エラー（404, 500）
    - graphAiServer API エラー（400, 500）
    - LLM API エラー（timeout, rate limit）
    - 不正なYAML生成
  - タイムアウト設定検証

- [ ] **4.4 実シナリオでの動作確認（タスク単位 + ジョブ単位 + 統合）** (6時間)

  **対象シナリオ**:
  - **シナリオ1**: 企業名を入力すると、その企業の過去5年の売り上げとビジネスモデルの変化をまとめてメール送信する
  - **シナリオ2**: 指定したWebサイトからPDFファイルを抽出し、Google Driveにアップロード後、メールで通知します
  - **シナリオ3**: This workflow searches for a newsletter in Gmail using a keyword, summarizes it, converts it to an MP3 podcast

  **各シナリオで以下の4ステップを実施**:

  ### Step 1: タスク単位での動作確認（task_master_id指定）

  - [ ] `/api/v1/job-generator` でジョブ・タスク生成
    - ユーザー要求を送信
    - JobMaster、TaskMaster、InterfaceMasterが作成される
    - `job_master_id` と各 `task_master_id` を記録

  - [ ] 各タスクに対して `/api/v1/workflow-generator` を実行（task_master_id指定）
    - リクエスト: `{"task_master_id": 123}`
    - レスポンスで生成されたYAMLを取得
    - YAMLファイルの内容検証:
      - ✅ capabilities準拠（graphai_capabilities.yaml, expert_agent_capabilities.yaml）
      - ✅ YAML文法正しさ（PyYAML構文チェック）
      - ✅ GraphAI構造正しさ（nodes, version, loop定義）

  - [ ] graphAiServerで各タスクのワークフローを個別実行
    - `POST /api/v1/execute` でワークフロー実行
    - サンプル入力データを使用
    - 実行結果検証:
      - ✅ HTTP 200 OK
      - ✅ エラーログなし
      - ✅ 出力がInterfaceMasterのoutput_schemaに準拠

  - [ ] 自己修復ループの動作確認
    - 意図的にエラーを発生させる（無効なcapability指定など）
    - `/api/v1/workflow-generator` 再実行
    - 自己修復ループで修正されることを確認（max 3回リトライ）

  ### Step 2: ジョブ単位での動作確認（job_master_id指定）

  - [ ] `/api/v1/workflow-generator` をジョブ単位で実行（job_master_id指定）
    - リクエスト: `{"job_master_id": 456}`
    - レスポンスで複数のYAMLが生成される（1タスク = 1 YAML）
    - 生成されたすべてのYAMLファイルを検証:
      - ✅ タスク数と一致するYAML数
      - ✅ 各YAMLがcapabilities準拠
      - ✅ 各YAMLが文法的に正しい

  - [ ] 複数ワークフローの整合性確認
    - 各タスクのワークフロー名が一意
    - 入力/出力スキーマの整合性（タスク間で出力→入力の型が一致）

  ### Step 3: 全タスクを結合して動作確認

  - [ ] タスク間の依存関係を確認
    - JobMasterTaskのorder順で実行順序を確認
    - 各タスクの入力/出力が連結可能か検証

  - [ ] 順次実行シミュレーション
    - Task 1実行 → 出力をTask 2の入力として使用 → Task 2実行 → ...
    - 各ステップで出力がJSON Schemaに準拠していることを確認
    - 最終出力が期待される結果になることを確認

  ### Step 4: ジョブID指定でジョブ実行して最終動作確認

  - [ ] jobqueue API経由でジョブを実行
    - `POST /api/v1/jobs` でJob作成（job_master_id指定）
    - Job IDを取得

  - [ ] ジョブの実行状態を監視
    - `GET /api/v1/jobs/{job_id}` でステータス確認
    - 各タスクの実行状態を監視（pending → running → completed）

  - [ ] 最終結果の検証
    - すべてのタスクが completed 状態
    - エラーログなし
    - 最終出力が期待される結果（例: メール送信成功、PDFアップロード完了、MP3ファイル生成完了）

  **成果物（シナリオごと）**:
  - ✅ タスク単位での動作確認レポート
  - ✅ ジョブ単位での動作確認レポート
  - ✅ 全タスク結合での動作確認レポート
  - ✅ ジョブ実行での最終動作確認レポート
  - ✅ 自己修復ループの動作確認レポート

- [ ] **4.5 Phase 4完了確認** (0.5時間)
  - `scripts/pre-push-check-all.sh` 実行
  - エラーゼロを確認
  - Phase 4作業記録作成: `phase-4-progress.md`

**成果物**:
- ✅ E2Eテストスイート
- ✅ カバレッジレポート（90%/50%達成）
- ✅ エラーハンドリング検証結果
- ✅ 実シナリオ動作確認レポート（3シナリオ × 4ステップ）
  - タスク単位での動作確認レポート
  - ジョブ単位での動作確認レポート
  - 全タスク結合での動作確認レポート
  - ジョブ実行での最終動作確認レポート
- ✅ 品質チェック合格

---

### Phase 5: ドキュメント作成 (0.5日)

**目的**: 最終ドキュメント整備

#### タスク詳細

- [ ] **5.1 API仕様書更新** (1時間)
  - OpenAPI schema更新（Swagger UI表示）
  - リクエスト/レスポンス例追加
  - エラーコード一覧作成

- [ ] **5.2 最終作業報告作成** (2時間)
  - `dev-reports/feature/issue/108/final-report.md`
  - 納品物一覧
  - 品質指標（カバレッジ、静的解析結果）
  - 制約条件チェック結果（最終版）

- [ ] **5.3 README更新** (1時間)
  - 使用例追加
  - セットアップ手順更新

- [ ] **5.4 Phase 5完了確認** (0.5時間)
  - `scripts/pre-push-check-all.sh` 実行
  - エラーゼロを確認
  - Phase 5作業記録作成: `phase-5-progress.md`

**成果物**:
- ✅ API仕様書
- ✅ 最終作業報告
- ✅ README
- ✅ 品質チェック合格（最終）

---

## ✅ 制約条件チェック結果

### コード品質原則

- [x] **SOLID原則**: 遵守予定
  - Single Responsibility: 各nodeは単一の責務（生成、検証、修復）
  - Open-Closed: 新規nodeの追加が容易な設計
  - Liskov Substitution: LLM providerの置き換え可能性
  - Interface Segregation: 最小限のインタフェース定義
  - Dependency Inversion: JobqueueClient抽象化

- [x] **KISS原則**: 遵守予定
  - 複雑な検証ロジックを避け、ルールベース検証採用
  - LangGraphの標準パターンに従う

- [x] **YAGNI原則**: 遵守予定
  - 必要最小限の機能のみ実装（複雑な依存関係解決は後回し）

- [x] **DRY原則**: 遵守予定
  - 共通ロジックはutils/に配置
  - バリデーション処理の共通化

### アーキテクチャガイドライン

- [x] **architecture-overview.md**: 準拠予定
  - expertAgent: API層 + LangGraph Agent層
  - graphAiServer: Workflow登録API追加
  - jobqueue: 既存APIを活用（変更なし）

- [x] **レイヤー分離**: 遵守予定
  ```
  API Layer (app/api/v1/)
    ↓
  Agent Layer (aiagent/langgraph/)
    ↓
  Utility Layer (utils/)
  ```

### 設定管理ルール

- [x] **環境変数**: 遵守予定
  - `JOBQUEUE_API_URL`: Jobqueue API URL
  - `GRAPHAI_SERVER_URL`: graphAiServer URL
  - `GEMINI_API_KEY`: Gemini API key (myVault経由)
  - `ANTHROPIC_API_KEY`: Claude API key (myVault経由)

- [x] **myVault**: 遵守予定
  - APIキーはmyVaultで管理
  - `aiagent/langgraph/workflowGeneratorAgents/utils/myvault_manager.py` で取得

### 品質担保方針

- [x] **単体テストカバレッジ**: 90%以上（目標）
  - 各node、utility、schemaに対する単体テスト
  - モック使用で外部依存を排除

- [x] **結合テストカバレッジ**: 50%以上（目標）
  - API endpoint統合テスト
  - Agent統合テスト
  - E2Eテスト

- [x] **静的解析**: エラーゼロ（目標）
  - Ruff linting
  - Ruff formatting
  - MyPy type checking

### CI/CD準拠

- [x] **PRラベル**: `feature` ラベル付与予定（minor version bump）
- [x] **コミットメッセージ**: Conventional Commits準拠
  - `feat(expertAgent): add workflow generator API`
  - `feat(graphAiServer): add workflow registration endpoint`
  - `test: add E2E tests for workflow generator`

- [x] **pre-push-check-all.sh**: Phase完了毎に実行予定

### 参照ドキュメント遵守

- [x] **GRAPHAI_WORKFLOW_GENERATION_RULES.md**: 必須参照
  - LLMプロンプトに組み込み
  - YAML生成ルールを厳守

- [x] **graphai_capabilities.yaml**: 必須参照
  - 利用可能なagentのみ使用
  - LLMに渡して生成時に制約

- [x] **expert_agent_capabilities.yaml**: 必須参照
  - 利用可能なexpertAgent APIのみ使用

### 違反・要検討項目

**なし**

---

## 📅 スケジュール

| Phase | タスク | 開始予定 | 完了予定 | 所要時間 | 状態 |
|-------|-------|---------|---------|---------|------|
| **Phase 1** | expertAgent基盤実装 | 10/21 | 10/23 | 2日 | 予定 |
| 1.1 | スキーマ定義 | 10/21 AM | 10/21 AM | 2時間 | 予定 |
| 1.2 | TaskDataFetcher実装 | 10/21 PM | 10/21 PM | 3時間 | 予定 |
| 1.3 | APIエンドポイント実装 | 10/22 AM | 10/22 PM | 3時間 | 予定 |
| 1.4 | Phase 1完了確認 | 10/22 PM | 10/22 PM | 0.5時間 | 予定 |
| **Phase 2** | graphAiServer API実装 | 10/23 | 10/23 | 1日 | 予定 |
| 2.1 | スキーマ定義 | 10/23 AM | 10/23 AM | 1時間 | 予定 |
| 2.2 | 登録エンドポイント実装 | 10/23 AM | 10/23 PM | 2時間 | 予定 |
| 2.3 | テスト実装 | 10/23 PM | 10/23 PM | 2時間 | 予定 |
| 2.4 | Phase 2完了確認 | 10/23 PM | 10/23 PM | 0.5時間 | 予定 |
| **Phase 3** | LangGraph Agent実装 | 10/24 | 10/26 | 3日 | 予定 |
| 3.1 | State定義 | 10/24 AM | 10/24 AM | 1時間 | 予定 |
| 3.2 | Generator Node実装 | 10/24 AM | 10/24 PM | 4時間 | 予定 |
| 3.3 | Sample Input Generator Node実装 | 10/25 AM | 10/25 AM | 2時間 | 予定 |
| 3.4 | Workflow Tester Node実装 | 10/25 AM | 10/25 PM | 3時間 | 予定 |
| 3.5 | Validator Node実装 | 10/25 PM | 10/25 PM | 3時間 | 予定 |
| 3.6 | Self-Repair Node実装 | 10/26 AM | 10/26 AM | 2時間 | 予定 |
| 3.7 | LangGraph構築 | 10/26 AM | 10/26 PM | 3時間 | 予定 |
| 3.8 | Phase 3完了確認 | 10/26 PM | 10/26 PM | 0.5時間 | 予定 |
| **Phase 4** | 統合テスト・品質担保 | 10/27 | 10/29 | 2日 | 予定 |
| 4.1 | E2Eテスト作成 | 10/27 AM | 10/27 AM | 3時間 | 予定 |
| 4.2 | カバレッジ確認 | 10/27 AM | 10/27 PM | 2時間 | 予定 |
| 4.3 | エラーハンドリング検証 | 10/27 PM | 10/27 PM | 2時間 | 予定 |
| 4.4 | 実シナリオ動作確認（4ステップ × 3シナリオ） | 10/28 AM | 10/29 PM | 6時間 | 予定 |
| 4.5 | Phase 4完了確認 | 10/29 PM | 10/29 PM | 0.5時間 | 予定 |
| **Phase 5** | ドキュメント作成 | 10/30 | 10/30 | 0.5日 | 予定 |
| 5.1 | API仕様書更新 | 10/30 AM | 10/30 AM | 1時間 | 予定 |
| 5.2 | 最終作業報告作成 | 10/30 AM | 10/30 PM | 2時間 | 予定 |
| 5.3 | README更新 | 10/30 PM | 10/30 PM | 1時間 | 予定 |
| 5.4 | Phase 5完了確認 | 10/30 PM | 10/30 PM | 0.5時間 | 予定 |

**総工数**: 9人日
**進捗率**: 0% (作業計画作成完了)

---

## 🚨 リスク管理

### 技術的リスク

| リスク | 影響度 | 発生確率 | 対策 |
|-------|-------|---------|------|
| **LLM生成YAML品質不安定** | 高 | 中 | ・詳細プロンプト設計<br>・Few-shot examples追加<br>・自己修復ループで品質向上 |
| **graphAiServer実行環境エラー** | 中 | 低 | ・事前に動作確認<br>・詳細エラーログ記録 |
| **JobqueueClient API変更** | 中 | 低 | ・APIバージョン固定<br>・統合テストで検出 |
| **LLM API rate limit** | 中 | 中 | ・リトライロジック実装<br>・Exponential backoff採用 |
| **カバレッジ目標未達** | 低 | 低 | ・Phase毎にカバレッジ確認<br>・早期に未カバー箇所を補足 |

### スケジュールリスク

| リスク | 影響度 | 発生確率 | 対策 |
|-------|-------|---------|------|
| **LangGraph Agent実装遅延** | 高 | 中 | ・Phase 3を優先度最高に設定<br>・早期着手 |
| **E2Eテスト環境準備遅延** | 中 | 低 | ・Phase 1-2と並行で環境構築 |
| **ドキュメント作成遅延** | 低 | 低 | ・Phase完了毎に段階的作成 |

### 品質リスク

| リスク | 影響度 | 発生確率 | 対策 |
|-------|-------|---------|------|
| **静的解析エラー多発** | 中 | 低 | ・pre-commit hooks有効化<br>・Phase毎に `pre-push-check-all.sh` 実行 |
| **テスト不足** | 高 | 低 | ・TDD採用<br>・実装前にテストケース設計 |

---

## 📝 備考

### 前提条件

- Jobqueue API (`http://localhost:8101`) が起動していること
- graphAiServer (`http://localhost:8102`) が起動していること
- myVault (`http://localhost:8103`) が起動していること
- Gemini API key / Anthropic API key がmyVaultに登録済みであること

### 制約事項

- 1 TaskMaster = 1 Workflow YML（タスク間依存関係は未対応）
- 自己修復ループは最大3回まで（無限ループ防止）
- graphAiServer登録先: `config/graphai/` ディレクトリ（固定）

### 今後の拡張可能性

- タスク間依存関係の自動解決
- Workflow実行履歴の記録・分析
- Workflow最適化エージェント（パフォーマンス改善）

---

## 📋 追加要件（ユーザーフィードバック反映）

### pre-push-check-all.sh 実行の徹底

各Phase完了時に必ず `scripts/pre-push-check-all.sh` を実行し、以下の品質基準を満たすことを確認します：

- ✅ Ruff linting: エラーゼロ
- ✅ Ruff formatting: 全ファイル適用済み
- ✅ MyPy type checking: エラーゼロ
- ✅ Unit tests: すべて合格
- ✅ Coverage: expertAgent 90%以上、graphAiServer（該当する場合）

### 実シナリオでの動作確認（4ステップ × 3シナリオ）

Phase 4にて、以下の3つの実シナリオで包括的な動作確認を実施します：

1. **シナリオ1**: 企業名を入力すると、その企業の過去5年の売り上げとビジネスモデルの変化をまとめてメール送信する
2. **シナリオ2**: 指定したWebサイトからPDFファイルを抽出し、Google Driveにアップロード後、メールで通知します
3. **シナリオ3**: This workflow searches for a newsletter in Gmail using a keyword, summarizes it, converts it to an MP3 podcast

**各シナリオで以下の4ステップを実施**:

#### Step 1: タスク単位での動作確認（task_master_id指定）
- `/api/v1/job-generator` でジョブ・タスク生成
- 各タスクに対して `/api/v1/workflow-generator` を実行（task_master_id指定）
- graphAiServerで各タスクのワークフローを個別実行
- 自己修復ループの動作確認

#### Step 2: ジョブ単位での動作確認（job_master_id指定）
- `/api/v1/workflow-generator` をジョブ単位で実行（job_master_id指定）
- 複数のYAMLが生成される（1タスク = 1 YAML）
- 複数ワークフローの整合性確認

#### Step 3: 全タスクを結合して動作確認
- タスク間の依存関係を確認
- 順次実行シミュレーション（Task 1 → Task 2 → ... → Task N）
- 最終出力が期待される結果になることを確認

#### Step 4: ジョブID指定でジョブ実行して最終動作確認
- jobqueue API経由でジョブを実行（`POST /api/v1/jobs`）
- ジョブの実行状態を監視（pending → running → completed）
- 最終結果の検証（メール送信成功、PDFアップロード完了、MP3ファイル生成完了）

---

**作業計画作成完了日**: 2025-10-21
**次のステップ**: ユーザーレビュー・承認待ち → Phase 1実装開始

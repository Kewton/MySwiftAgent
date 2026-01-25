# 作業計画: ジョブ・タスク自動生成エージェント

**作成日**: 2025-10-19
**予定工数**: 15人日
**完了予定**: 2025-11-03
**ブランチ**: feature/issue/97
**Issue**: #97

---

## 📚 参考ドキュメント

**必須参照**:
- [x] [設計方針](./design-policy.md) - 本作業の設計方針
- [ ] [GraphAI ワークフロー生成ルール](../../graphAiServer/docs/GRAPHAI_WORKFLOW_GENERATION_RULES.md) - 実現可能性評価で参照
- [ ] [GraphAI 利用可能Agent一覧](../../graphAiServer/docs/AVAILABLE_AGENTS.md) - 実現可能性評価で参照

**推奨参照**:
- [ ] [アーキテクチャ概要](../../docs/design/architecture-overview.md)
- [ ] [環境変数管理](../../docs/design/environment-variables.md)
- [ ] [myVault連携](../../docs/design/myvault-integration.md)

---

## 🔧 開発・検証環境

### 環境起動

**本プロジェクトでは `scripts/quick-start.sh` を使用して開発・検証環境を起動します。**

#### 起動方法

```bash
# 全サービスを一括起動
./scripts/quick-start.sh
```

#### ポート設定

| サービス | ポート | URL |
|---------|--------|-----|
| JobQueue | 8101 | http://localhost:8101 |
| MyScheduler | 8102 | http://localhost:8102 |
| MyVault | 8103 | http://localhost:8103 |
| ExpertAgent | 8104 | http://localhost:8104 |
| GraphAiServer | 8105 | http://localhost:8105 |
| CommonUI | 8601 | http://localhost:8601 |

#### 環境変数

`quick-start.sh` により以下の環境変数が自動設定されます：

- `JOBQUEUE_API_URL=http://localhost:8101`
- `MYSCHEDULER_BASE_URL=http://localhost:8102`
- `MYVAULT_BASE_URL=http://localhost:8103`
- `EXPERTAGENT_BASE_URL=http://localhost:8104`
- `GRAPHAISERVER_BASE_URL=http://localhost:8105/api`

#### 動作確認コマンド

```bash
# サービス状態確認
./scripts/dev-start.sh status

# ログ確認
./scripts/dev-start.sh logs

# サービス停止
./scripts/dev-start.sh stop
```

#### 検証手順

本エージェントの検証は以下の手順で実施します：

1. **環境起動**: `./scripts/quick-start.sh`
2. **API動作確認**:
   ```bash
   curl -X POST http://localhost:8104/api/v1/job-generator \
     -H "Content-Type: application/json" \
     -d '{"user_requirement": "テスト要件"}'
   ```
3. **CommonUI確認**: http://localhost:8601 でWeb UI確認
4. **ログ確認**: `./scripts/dev-start.sh logs expertAgent`

---

## 📊 Phase分解

### Phase 1: 基盤実装 (3日)

**目的**: State定義、プロンプト、ユーティリティの実装

#### タスク一覧
- [ ] **State定義実装** (`state.py`)
  - JobTaskGeneratorState TypedDict定義
  - 全フィールドの型定義（feasibility_analysis含む）
  - デフォルト値設定
  - 工数: 0.5日

- [ ] **プロンプトテンプレート実装** (`prompts/`)
  - `task_breakdown.py` - タスク分割プロンプト
  - `evaluation.py` - 4原則+実現可能性評価プロンプト
    - GraphAI/expertAgent機能リストを含める
    - 実現困難なタスク例を含める
  - `interface_schema.py` - インターフェース定義プロンプト
  - `validation_fix.py` - バリデーション修正プロンプト
  - 工数: 1日

- [ ] **ユーティリティ実装** (`utils/`)
  - `jobqueue_client.py` - jobqueue API client
    - InterfaceMaster CRUD
    - TaskMaster CRUD
    - JobMaster CRUD
    - JobMasterTask CRUD
    - Validation API
    - Job作成API
  - `schema_matcher.py` - 既存スキーマ検索ロジック（名前・URL完全一致）
  - `graphai_capabilities.py` - GraphAI/expertAgent機能リスト管理
    - GraphAI標準Agent一覧
    - expertAgent Direct API一覧
    - 実現困難なタスクと代替案マッピング
  - 工数: 1.5日

**成果物**:
- `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/state.py`
- `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/prompts/*.py`
- `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/utils/*.py`

**検証方法**:
- 単体テストで各ユーティリティ関数の動作確認
- jobqueue APIクライアントの接続テスト

---

### Phase 2: Node実装 (5日)

**目的**: 6つのNodeの実装

#### タスク一覧
- [ ] **requirement_analysis_node** (`nodes/requirement_analysis.py`)
  - LLM呼び出し（claude-haiku-4-5）
  - タスク分割ロジック
  - 4原則に基づく分割
  - 単体テスト作成
  - 工数: 0.5日

- [ ] **evaluator_node** (`nodes/evaluator.py`)
  - LLM呼び出し（claude-haiku-4-5）
  - 5原則評価ロジック
  - **実現可能性チェック**:
    - GraphAI標準Agent照合
    - expertAgent Direct API照合
    - 実現困難なタスク検出
  - **代替案検討**:
    - 既存機能での代替検索
    - 複数API組み合わせ検討
  - **API機能追加提案**:
    - 代替不可時の提案生成
    - 優先度判定ロジック
  - 評価結果のPydanticバリデーション
  - リトライロジック
  - 単体テスト作成（実現可能性評価含む）
  - 工数: 1.5日

- [ ] **interface_definition_node** (`nodes/interface_definition.py`)
  - LLM呼び出し（claude-haiku-4-5）
  - JSON Schema生成ロジック
  - jobqueue API連携（InterfaceMaster検索・登録）
  - 既存InterfaceMaster検索（schema_matcher使用）
  - 単体テスト作成
  - 工数: 1日

- [ ] **master_creation_node** (`nodes/master_creation.py`)
  - TaskMaster検索・登録
  - TaskMaster IDリスト保存
  - JobMaster登録
  - **JobMasterTask登録**（重要！）
    - order順に各TaskMasterを関連付け
    - is_required=True設定
  - jobqueue API連携
  - 単体テスト作成
  - 工数: 1日

- [ ] **validation_node** (`nodes/validation.py`)
  - jobqueue Validation API呼び出し
    - GET /api/v1/job-masters/{master_id}/validate-workflow
  - バリデーション結果解析
  - エラー修正提案生成（LLM）
  - リトライロジック
  - 単体テスト作成
  - 工数: 0.5日

- [ ] **job_registration_node** (`nodes/job_registration.py`)
  - JobMasterTask取得
  - tasksパラメータ構築
  - Job作成API呼び出し
  - Job ID取得・返却
  - 単体テスト作成
  - 工数: 0.5日

**成果物**:
- `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/nodes/*.py`
- `expertAgent/tests/unit/test_job_task_generator/test_*.py`

**検証方法**:
- 各Nodeの単体テスト（90%カバレッジ目標）
- LLM出力のPydanticバリデーション確認
- jobqueue API連携のモックテスト

---

### Phase 3: LangGraphエージェント統合 (3日)

**目的**: エッジ定義、ルーター実装、エージェント本体の統合

#### タスク一覧
- [ ] **エージェント本体実装** (`agent.py`)
  - StateGraph定義
  - 6つのNode追加
  - エントリーポイント設定
  - 工数: 0.5日

- [ ] **ルーター実装** (`agent.py`)
  - **evaluator_router**:
    - タスク分割後の評価 → interface_definition
    - インターフェース定義後の評価 → master_creation
    - 評価不合格 → リトライ or 終了
    - **実現困難なタスクあり** → 代替案適用 or API提案出力
  - **validation_router**:
    - バリデーション成功 → job_registration
    - バリデーション失敗 → interface_definition（リトライ）
    - リトライ超過 → 終了
  - 条件分岐ロジックの実装
  - 工数: 1.5日

- [ ] **エッジ定義** (`agent.py`)
  - requirement_analysis → evaluator
  - evaluator → (conditional) interface_definition / requirement_analysis / master_creation / END
  - interface_definition → evaluator
  - master_creation → validation
  - validation → (conditional) job_registration / interface_definition / END
  - job_registration → END
  - 工数: 0.5日

- [ ] **統合テスト**
  - エンドツーエンドフロー確認
  - リトライロジック確認
  - エラーハンドリング確認
  - 工数: 0.5日

**成果物**:
- `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/agent.py`
- `expertAgent/tests/integration/test_job_task_generator/test_end_to_end.py`

**検証方法**:
- モック環境でのE2Eテスト
- 各条件分岐の網羅的なテスト

---

### Phase 4: APIエンドポイント実装 (2日)

**目的**: REST APIエンドポイントの実装

#### タスク一覧
- [ ] **APIエンドポイント実装** (`app/api/v1/job_generator_endpoints.py`)
  - POST /api/v1/job-generator エンドポイント
  - リクエストスキーマ定義（Pydantic）:
    - user_requirement: str
    - max_retry: int (default: 5)
  - レスポンススキーマ定義（Pydantic）:
    - job_id: Optional[str]
    - status: str
    - error_message: Optional[str]
    - infeasible_tasks: List[Dict] (実現困難なタスクリスト)
    - alternative_proposals: List[Dict] (代替案リスト)
    - api_extension_proposals: List[Dict] (API機能追加提案リスト)
  - LangGraphエージェント呼び出し
  - エラーハンドリング
  - 工数: 1日

- [ ] **APIルーター登録** (`app/api/v1/router.py`)
  - job_generator_endpointsをルーターに追加
  - 工数: 0.5日

- [ ] **API統合テスト**
  - httpxクライアントでのAPIテスト
  - 正常系・異常系のテスト
  - 工数: 0.5日

**成果物**:
- `expertAgent/app/api/v1/job_generator_endpoints.py`
- `expertAgent/tests/integration/test_job_task_generator/test_api.py`

**検証方法**:
- curlコマンドでの動作確認
- 統合テスト実行（50%カバレッジ目標）

---

### Phase 5: テスト実装・品質担保 (2日)

**目的**: テストカバレッジ達成、品質チェック

#### タスク一覧
- [ ] **単体テストの拡充**
  - evaluator_nodeの実現可能性評価テスト
    - 実現可能なタスクのみの場合
    - Slack通知→Gmail代替ケース
    - 代替不可→API提案ケース
  - 各Nodeのエッジケーステスト
  - カバレッジ90%達成確認
  - 工数: 1日

- [ ] **結合テストの拡充**
  - E2Eテスト（複数シナリオ）:
    - 評価成功→Job登録成功
    - 評価失敗→リトライ→成功
    - 実現困難なタスク→代替案適用→成功
    - 実現困難なタスク→API提案→失敗
    - バリデーション失敗→リトライ→成功
  - jobqueue統合テスト
  - カバレッジ50%達成確認
  - 工数: 0.5日

- [ ] **品質チェック**
  - Ruff linting
  - Ruff formatting
  - MyPy type checking
  - pre-push-check-all.sh実行
  - 工数: 0.5日

**成果物**:
- 単体テスト（90%カバレッジ達成）
- 結合テスト（50%カバレッジ達成）
- 品質チェック合格

**検証方法**:
- `uv run pytest tests/ --cov=aiagent --cov-report=html`
- カバレッジレポート確認

---

## ✅ 制約条件チェック結果

### コード品質原則
- [x] **SOLID原則**: 各Nodeは単一責任、State駆動設計
- [x] **KISS原則**: 遵守予定 / 複雑性を最小限に
- [x] **YAGNI原則**: 遵守予定 / GraphAI YAML生成は別イシュー
- [x] **DRY原則**: 遵守予定 / プロンプト・ユーティリティの共通化

### アーキテクチャガイドライン
- [x] **architecture-overview.md**: 準拠 / expertAgent拡張
- [x] **environment-variables.md**: 準拠 / JOBQUEUE_BASE_URL使用
- [x] **myvault-integration.md**: 準拠 / LLM APIキーはmyVault管理

### 設定管理ルール
- [x] **環境変数**: JOBQUEUE_BASE_URL, CLAUDE_API_KEY (myVault)
- [x] **myVault**: LLM APIキー管理

### 品質担保方針
- [x] **単体テストカバレッジ**: 90%以上目標
- [x] **結合テストカバレッジ**: 50%以上目標
- [x] **Ruff linting**: 適用予定
- [x] **MyPy type checking**: 厳密な型定義予定

### CI/CD準拠
- [x] **PRラベル**: `feature` ラベル (minor bump)
- [x] **コミットメッセージ**: 規約準拠予定
- [x] **pre-push-check-all.sh**: 実行予定

### 参照ドキュメント遵守
- [x] **新プロジェクト追加**: 該当なし（既存expertAgent拡張）
- [x] **GraphAI ワークフロー開発**: 該当なし（スコープ外だが機能リスト参照）

### 設計方針遵守
- [x] **JobMasterTask登録**: master_creation_nodeで必須実装
- [x] **実現可能性評価**: evaluator_nodeで必須実装
- [x] **GraphAI機能リスト**: graphai_capabilities.pyで管理

### 違反・要検討項目
なし

---

## 📅 スケジュール

| Phase | 開始予定 | 完了予定 | 主担当 | 状態 |
|-------|---------|---------|--------|------|
| Phase 1: 基盤実装 | 10/20 | 10/22 | Claude Code | 予定 |
| Phase 2: Node実装 | 10/23 | 10/27 | Claude Code | 予定 |
| Phase 3: LangGraph統合 | 10/28 | 10/30 | Claude Code | 予定 |
| Phase 4: APIエンドポイント | 10/31 | 11/01 | Claude Code | 予定 |
| Phase 5: テスト・品質担保 | 11/02 | 11/03 | Claude Code | 予定 |

**合計予定工数**: 15人日

---

## 🔍 依存関係

### 外部依存
- **jobqueue API**: InterfaceMaster, TaskMaster, JobMaster, JobMasterTask, Validation, Job CRUD
- **LLM API**: claude-haiku-4-5 (myVault経由でAPIキー取得)

### 内部依存
- Phase 2 は Phase 1 に依存（State, プロンプト, ユーティリティ）
- Phase 3 は Phase 2 に依存（全Node実装完了）
- Phase 4 は Phase 3 に依存（エージェント統合完了）
- Phase 5 は Phase 4 に依存（API実装完了）

---

## 🚨 リスクと対策

| リスク | 発生時の対策 |
|-------|------------|
| **LLM出力の不安定性** | Pydanticバリデーション強化、リトライ回数増加 |
| **jobqueue API仕様変更** | jobqueue統合テストで早期検知、バージョン固定 |
| **実現可能性評価の精度不足** | GraphAI機能リストの更新、評価プロンプトの改善 |
| **テストカバレッジ未達** | Phase 5 の工数を1日延長、優先度の高いテストに集中 |
| **パフォーマンス問題** | 非同期処理の最適化、LLM呼び出しの並列化検討 |

---

## 📝 Phase完了条件

### Phase 1
- [ ] State定義が全フィールドを含む
- [ ] プロンプトテンプレートが4種類完成
- [ ] ユーティリティの単体テストが合格

### Phase 2
- [ ] 6つのNodeが実装完了
- [ ] 各Nodeの単体テストが合格（90%カバレッジ）
- [ ] evaluator_nodeの実現可能性評価が動作

### Phase 3
- [ ] LangGraphエージェントが統合完了
- [ ] evaluator_router, validation_routerが実装完了
- [ ] E2Eテストが合格

### Phase 4
- [ ] APIエンドポイントが実装完了
- [ ] curlコマンドでの動作確認成功
- [ ] API統合テストが合格

### Phase 5
- [ ] 単体テストカバレッジ90%以上
- [ ] 結合テストカバレッジ50%以上
- [ ] pre-push-check-all.sh合格

---

## 🎯 最終成果物チェックリスト

- [ ] ソースコード
  - [ ] State定義
  - [ ] 6つのNode実装
  - [ ] LangGraphエージェント統合
  - [ ] APIエンドポイント実装
  - [ ] プロンプトテンプレート
  - [ ] ユーティリティ実装

- [ ] テスト
  - [ ] 単体テスト（90%カバレッジ）
  - [ ] 結合テスト（50%カバレッジ）
  - [ ] E2Eテスト

- [ ] ドキュメント
  - [ ] design-policy.md（完成済み）
  - [ ] work-plan.md（本ドキュメント）
  - [ ] phase-{N}-progress.md（各Phase完了時）
  - [ ] final-report.md（全作業完了時）

- [ ] 品質チェック
  - [ ] Ruff linting合格
  - [ ] Ruff formatting適用
  - [ ] MyPy type checking合格
  - [ ] pre-push-check-all.sh合格

---

**作業計画作成完了。Phase 1: 基盤実装から着手します。**

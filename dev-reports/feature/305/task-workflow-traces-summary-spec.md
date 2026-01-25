# Task Workflow Traces サマリ表示機能仕様書

**Issue**: #305 拡張機能
**作成日**: 2025-12-24
**ステータス**: ドラフト

---

## 1. 概要

### 1.1 目的
Recent Job Versions セクションの「Task Workflow Traces」において、各タスクのワークフロー生成結果サマリを表示し、生成結果の詳細を確認可能にする。

### 1.2 現状の課題
現在の UI では以下の情報のみ表示されている：
- タスク名
- ステータス（success/failed）
- ワークフロー名
- Langfuse Trace リンク
- エラーメッセージ（ツールチップのみ）

**問題点**:
1. 成功/失敗の詳細な理由が不明
2. 生成されたワークフロー YAML のプレビューができない
3. テストデータ（sample_input）の確認ができない
4. LLM 評価スコアや改善提案が見えない
5. 実行結果の詳細が確認できない

### 1.3 ゴール
- ワークフロー生成の品質を一目で把握可能にする
- 失敗時の原因特定を容易にする
- 生成されたワークフローの内容を即座に確認できる

---

## 2. データ要件

### 2.1 バックエンド拡張

#### WorkflowStatusItem の拡張

現在の `WorkflowStatusItem`:
```typescript
interface WorkflowStatusItem {
  task_id: string;
  task_name: string | null;
  status: 'pending' | 'generating' | 'success' | 'failed';
  workflow_name: string | null;
  generation_time_ms: number | null;
  error_message: string | null;
  langfuse_trace_id: string | null;
}
```

**拡張後** `WorkflowStatusItemExtended`:
```typescript
interface WorkflowStatusItemExtended extends WorkflowStatusItem {
  // 生成結果サマリ
  summary: WorkflowGenerationSummary | null;
}

interface WorkflowGenerationSummary {
  // YAML プレビュー（先頭 500 文字）
  yaml_preview: string | null;

  // テストデータ
  sample_input: Record<string, unknown> | null;

  // テスト実行結果
  test_result: TestExecutionSummary | null;

  // 評価情報
  evaluation: EvaluationSummary | null;

  // リトライ情報
  retry_info: RetryInfo | null;

  // 失敗詳細（失敗時のみ）
  failure_details: FailureDetails | null;
}

interface TestExecutionSummary {
  http_status: number | null;
  is_valid: boolean;
  validation_errors: string[];
  execution_time_ms: number | null;
}

interface EvaluationSummary {
  score: number | null;  // 0-100
  feedback: string | null;
  suggestions: string[];
}

interface RetryInfo {
  retry_count: number;
  max_retry: number;
  generation_model: string | null;
}
```

#### 失敗詳細情報 (FailureDetails)

```typescript
interface FailureDetails {
  // 失敗ステージ
  failure_stage: FailureStage;

  // エラーサマリ
  error_summary: {
    http_status: number | null;
    error_code: string | null;
    error_message: string;
    error_detail: string | null;
  };

  // 原因分析
  cause_analysis: {
    category: string;        // "API パラメータ", "YAML構文", "スキーマ不整合" 等
    problem_location: string | null;  // ノード名、行番号など
    problem_field: string | null;     // 問題のフィールド名
    actual_value: string | null;      // 実際の値
    expected_value: string | null;    // 期待される値
  } | null;

  // 推奨対応
  recommendations: string[];

  // リトライ履歴
  retry_history: Array<{
    attempt: number;
    error_message: string;
    model_used: string | null;
    timestamp: string;
  }>;
}

type FailureStage =
  | 'yaml_generation'        // YAML生成失敗
  | 'schema_validation'      // 入力スキーマ検証失敗
  | 'workflow_registration'  // graphAiServer登録失敗
  | 'workflow_execution'     // ワークフロー実行失敗 (HTTP 4xx/5xx)
  | 'node_error'            // 個別ノードエラー
  | 'output_validation'     // 出力スキーマ検証失敗
  | 'quality_evaluation';   // 品質基準未達
```

#### 失敗ステージ分類と判定ロジック

| ステージ | 判定条件 | 主な原因 |
|---------|---------|---------|
| `yaml_generation` | `yaml_content` が空または YAML パースエラー | LLMが不正なYAMLを生成 |
| `schema_validation` | `validation_result.input_validation.is_valid == false` | テストデータがスキーマ不適合 |
| `workflow_registration` | 登録 HTTP ステータス != 200/201 | graphAiServer登録失敗 |
| `workflow_execution` | `test_http_status` == 400/422/500/504 | APIエラー、タイムアウト |
| `node_error` | `validation_errors` に `[graphai]` カテゴリあり | 個別ノード実行失敗 |
| `output_validation` | `validation_errors` に `[output]` カテゴリあり | 出力スキーマ不適合 |
| `quality_evaluation` | `evaluation_score < 70` or `is_acceptable == false` | 品質基準未達 |

**判定優先順位**: 上から順に評価し、最初に該当したステージを `failure_stage` とする。

#### 既存データからの FailureDetails 生成（LLMノード不要）

```python
# expertAgent での FailureDetails 生成ロジック（疑似コード）
def build_failure_details(state: WorkflowGeneratorState) -> FailureDetails | None:
    if state["status"] == "success":
        return None

    # 1. 失敗ステージの判定
    failure_stage = determine_failure_stage(state)

    # 2. エラーサマリの構築
    error_summary = {
        "http_status": state.get("test_http_status"),
        "error_code": extract_error_code(state.get("error_message")),
        "error_message": state.get("error_message", "Unknown error"),
        "error_detail": extract_error_detail(state.get("validation_errors", [])),
    }

    # 3. 原因分析（validation_errors から抽出）
    cause_analysis = extract_cause_from_validation_errors(
        state.get("validation_errors", [])
    )

    # 4. 推奨対応（LLM evaluator の suggestions を活用）
    recommendations = state.get("evaluation_suggestions", [])
    if not recommendations:
        recommendations = generate_default_recommendations(failure_stage)

    # 5. リトライ履歴
    retry_history = format_repair_history(state.get("repair_history", []))

    return FailureDetails(
        failure_stage=failure_stage,
        error_summary=error_summary,
        cause_analysis=cause_analysis,
        recommendations=recommendations,
        retry_history=retry_history,
    )
```

### 2.2 API 変更

#### オプション1: 既存 API 拡張（推奨）
- `/api/v1/jobs/{job_id}/status` のレスポンスに `summary` フィールドを追加
- `include_summary=true` クエリパラメータで詳細取得を制御

```python
# expertAgent/app/api/v1/job_generator_endpoints.py
@router.get("/jobs/{job_id}/status")
async def get_job_status(
    job_id: str,
    include_summary: bool = False,  # NEW
) -> JobCreationStatusResponse:
    ...
```

#### オプション2: 別エンドポイント追加
- `/api/v1/jobs/{job_id}/workflow-summaries` 新規追加
- サマリデータを別途取得

**推奨**: オプション1（既存 API 拡張）

### 2.3 設計判断: 新規LLMノードは不要

#### 判断理由

失敗詳細の構築に新規LLMエージェントノードを追加しない理由：

| 必要情報 | 既存データソース | LLM不要の理由 |
|---------|-----------------|--------------|
| failure_stage | ステータス、HTTP コード、validation_errors | ルールベースで判定可能 |
| error_summary | error_message, test_http_status | そのまま使用可能 |
| cause_analysis | validation_errors (カテゴリ付き) | validator_node が既に分類 |
| recommendations | llm_evaluator の suggestions | 既存LLM評価を活用 |
| retry_history | repair_history | そのまま使用可能 |

#### 既存ノードからのデータ活用

```
┌─────────────────────────────────────────────────────────────────┐
│                    既存ワークフローからのデータ抽出              │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│ validator_node │   │ workflow_tester│  │ llm_evaluator │
│               │   │               │   │               │
│ • validation_ │   │ • test_http_  │   │ • evaluation_ │
│   errors      │   │   status      │   │   suggestions │
│ • is_valid    │   │ • test_execu- │   │ • strengths   │
│               │   │   tion_result │   │ • weaknesses  │
└───────────────┘   └───────────────┘   └───────────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              ▼
                ┌─────────────────────────┐
                │  build_failure_details() │
                │  (純粋な変換ロジック)     │
                └─────────────────────────┘
                              │
                              ▼
                ┌─────────────────────────┐
                │     FailureDetails       │
                └─────────────────────────┘
```

#### コスト・パフォーマンス比較

| 項目 | LLMノード追加 | 既存データ活用（採用） |
|-----|-------------|---------------------|
| LLMコスト | +$0.01〜0.05/回 | $0 |
| レイテンシ | +500ms〜2s | +10ms未満 |
| 実装複雑度 | 高（新ノード+プロンプト） | 低（変換関数のみ） |
| 精度 | やや高（自然言語推論） | 十分（ルールベース） |

**結論**: 既存データで必要十分な情報が得られるため、LLMノード追加は不要。

---

## 3. UI 設計

### 3.1 表示モード

#### コンパクトモード（デフォルト）
現在の表示 + 以下を追加:
- 評価スコアバッジ（成功時）
- 生成時間
- リトライ回数（1回以上の場合）

```
┌─────────────────────────────────────────────────────────────────┐
│ Task Workflow Traces                                            │
├─────────────────────────────────────────────────────────────────┤
│ 📋 詳細音声スクリプトの生成                                      │
│   ✅ success  workflow_tm_01...  ⭐85  ⏱️1.2s  🔄1  [Trace]     │
│ ├─ [▶ 詳細を表示]                                               │
├─────────────────────────────────────────────────────────────────┤
│ 📋 音声合成とGoogle Driveアップロード                            │
│   ❌ failed   -                        ⏱️0.8s  🔄3  [Trace]     │
│   └─ Error: HTTP 400 - Invalid voice parameter                  │
│ ├─ [▶ 詳細を表示]                                               │
└─────────────────────────────────────────────────────────────────┘
```

#### 詳細モード（展開時）
クリックで展開して以下を表示:

```
┌─────────────────────────────────────────────────────────────────┐
│ 📋 詳細音声スクリプトの生成                                      │
│   ✅ success  workflow_tm_01...  ⭐85  ⏱️1.2s  🔄1  [Trace]     │
├─────────────────────────────────────────────────────────────────┤
│ ▼ 詳細                                                          │
├─────────────────────────────────────────────────────────────────┤
│ 📄 生成ワークフロー YAML                                        │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ version: 0.5                                                │ │
│ │ nodes:                                                      │ │
│ │   source: {}                                                │ │
│ │   build_prompt:                                             │ │
│ │     agent: stringTemplateAgent                              │ │
│ │     inputs: ...                                             │ │
│ │ [全文を表示]                                                │ │
│ └─────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│ 📊 テストデータ                                                  │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ {                                                           │ │
│ │   "title": "Sample Title",                                  │ │
│ │   "sections": ["section1", "section2"],                     │ │
│ │   "script_style": "monologue"                               │ │
│ │ }                                                           │ │
│ └─────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│ ✅ テスト実行: HTTP 200                                         │
│    検証: 合格 (エラーなし)                                       │
├─────────────────────────────────────────────────────────────────┤
│ ⭐ LLM評価: 85/100                                              │
│    フィードバック: タスク要件を適切に満たしています。            │
│    改善提案:                                                     │
│    - エラーハンドリングの追加を検討                             │
└─────────────────────────────────────────────────────────────────┘
```

#### 失敗時の詳細表示

```
┌─────────────────────────────────────────────────────────────────┐
│ 📋 音声合成とGoogle Driveアップロード                            │
│   ❌ failed   -              ⏱️0.8s  🔄3/3  [Trace]              │
├─────────────────────────────────────────────────────────────────┤
│ ▼ 失敗詳細                                                      │
├─────────────────────────────────────────────────────────────────┤
│ ❌ 失敗ステージ: ワークフロー実行 (workflow_execution)          │
│                                                                 │
│ 📊 エラーサマリ                                                 │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ HTTP Status: 400 Bad Request                                │ │
│ │ エラー: Invalid voice parameter                             │ │
│ │ 詳細: "ja-JP-Standard-A" is not valid. Expected one of:     │ │
│ │       alloy, echo, fable, onyx, nova, shimmer               │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│ 🔍 原因分析                                                     │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ カテゴリ: API パラメータ                                    │ │
│ │ 問題箇所: ノード "tts_drive_upload"                         │ │
│ │ 問題フィールド: body.voice                                  │ │
│ │ 受信値: "ja-JP-Standard-A" (Google Cloud TTS形式)          │ │
│ │ 期待値: OpenAI TTS形式 (alloy, echo, fable, ...)           │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│ 💡 推奨対応                                                     │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ 1. Interface定義でvoiceのenum制約を追加                     │ │
│ │ 2. ワークフロー再生成を実行                                 │ │
│ │                                                             │ │
│ │ [🔄 ワークフロー再生成] [📝 Interface修正へ]                │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│ 📄 失敗時のワークフローYAML                                     │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ version: 0.5                                                │ │
│ │ nodes:                                                      │ │
│ │   tts_drive_upload:                                         │ │
│ │     agent: fetchAgent                                       │ │
│ │     inputs:                                                 │ │
│ │       body:                                                 │ │
│ │         voice: :source.voice_id  # ← 問題箇所              │ │
│ │ [全文を表示]                                                │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│ 📊 使用されたテストデータ                                       │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ {                                                           │ │
│ │   "full_script": "これはサンプルテキストです...",          │ │
│ │   "voice_id": "ja-JP-Standard-A",  ← 問題の値              │ │
│ │   "file_name": "sample_file.txt"                           │ │
│ │ }                                                           │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│ 🔄 リトライ履歴 (3回試行)                                       │
│ ├─ 1回目: HTTP 400 - Invalid voice parameter (gemini-2.5-flash)│
│ ├─ 2回目: HTTP 400 - Invalid voice parameter (gpt-4o-mini)    │
│ └─ 3回目: HTTP 400 - Invalid voice parameter (最大試行到達)    │
└─────────────────────────────────────────────────────────────────┘
```

#### 失敗ステージ別の表示カスタマイズ

| 失敗ステージ | 強調表示項目 | アクションボタン |
|-------------|-------------|----------------|
| `yaml_generation` | YAML構文エラー詳細、エラー行番号 | [再生成] |
| `schema_validation` | 期待型 vs 実際型、スキーマパス | [テストデータ編集] [再実行] |
| `workflow_registration` | サーバーエラーメッセージ | [再試行] |
| `workflow_execution` | HTTP ステータス、APIエラー詳細 | [再生成] [API仕様確認] |
| `node_error` | 失敗ノード名、タイムアウト情報 | [再生成] [ノード設定確認] |
| `output_validation` | 出力スキーマ不一致箇所 | [再生成] |
| `quality_evaluation` | 評価スコア詳細、不合格理由 | [再生成] [品質基準確認] |

#### LLM評価詳細の表示（成功・失敗共通）

```
┌─────────────────────────────────────────────────────────────────┐
│ ⭐ LLM評価: 85/100                                              │
├─────────────────────────────────────────────────────────────────┤
│ スコア内訳                                                       │
│ ├─ 構造: 90/100      ████████████████████░░░░                   │
│ ├─ 要件: 85/100      ███████████████████░░░░░                   │
│ ├─ 出力品質: 80/100  ████████████████░░░░░░░░                   │
│ ├─ エラー処理: 75/100 ███████████████░░░░░░░░░                   │
│ └─ テストデータ: 88/100 ███████████████████░░░░                  │
├─────────────────────────────────────────────────────────────────┤
│ ✅ 良い点                                                       │
│ ├─ APIパラメータが正しく設定されている                          │
│ └─ 入力スキーマに準拠したデータフロー                           │
├─────────────────────────────────────────────────────────────────┤
│ ⚠️ 改善点                                                       │
│ └─ タイムアウト設定が短い可能性                                 │
├─────────────────────────────────────────────────────────────────┤
│ 💡 提案                                                         │
│ └─ エラー時のフォールバック処理を検討                           │
├─────────────────────────────────────────────────────────────────┤
│ 確信度: 0.92                                                    │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 UI コンポーネント

#### 新規コンポーネント
```
myAgentDesk/src/lib/components/generation/
├── WorkflowTraceSummary.svelte      # サマリ表示コンポーネント（成功/失敗共通）
├── FailureDetailsPanel.svelte       # 失敗詳細パネル（NEW）
├── CauseAnalysisCard.svelte         # 原因分析カード（NEW）
├── RetryHistoryList.svelte          # リトライ履歴リスト（NEW）
├── YamlPreview.svelte               # YAML プレビュー
├── TestDataDisplay.svelte           # テストデータ表示
├── EvaluationBadge.svelte           # 評価スコアバッジ
└── EvaluationDetailsPanel.svelte    # 評価詳細パネル（NEW）
```

#### WorkflowTraceSummary.svelte Props
```typescript
interface WorkflowTraceSummaryProps {
  workflowStatus: WorkflowStatusItemExtended;
  expanded: boolean;
  onToggle: () => void;
}
```

#### FailureDetailsPanel.svelte Props
```typescript
interface FailureDetailsPanelProps {
  failureDetails: FailureDetails;
  yamlPreview: string | null;
  sampleInput: Record<string, unknown> | null;
  onRegenerate?: () => void;
  onEditTestData?: () => void;
}
```

#### EvaluationDetailsPanel.svelte Props
```typescript
interface EvaluationDetailsPanelProps {
  evaluation: {
    overall_score: number;
    structural_score: number;
    requirement_score: number;
    output_quality_score: number;
    error_handling_score: number;
    test_data_quality_score: number;
    strengths: string[];
    weaknesses: string[];
    suggestions: string[];
    confidence: number;
  };
}
```

### 3.3 スコア表示ルール

| スコア範囲 | バッジ色 | アイコン |
|-----------|---------|---------|
| 90-100    | 緑      | ⭐⭐⭐   |
| 70-89     | 青      | ⭐⭐     |
| 50-69     | 黄      | ⭐       |
| 0-49      | 赤      | ⚠️       |
| null      | グレー  | -        |

---

## 4. 実装計画

### Phase 1: バックエンド拡張（優先度: 高）

1. **WorkflowStatusItem モデル拡張**
   - `expertAgent/app/services/job_creation_state.py`
   - `summary` フィールド追加

2. **ワークフロー生成結果の保存**
   - `workflow_generation_node.py` でサマリデータを生成
   - `JobCreationStateManager` に保存

3. **API レスポンス拡張**
   - `include_summary` パラメータ対応
   - サマリデータのシリアライズ

### Phase 2: フロントエンド実装（優先度: 高）

1. **型定義更新**
   - `myAgentDesk/src/lib/types/job-version.ts`

2. **API クライアント更新**
   - `expert-agent.ts` の型更新

3. **コンポーネント実装**
   - `WorkflowTraceSummary.svelte`
   - `YamlPreview.svelte`
   - `EvaluationBadge.svelte`

4. **ページ統合**
   - `+page.svelte` に統合

### Phase 3: 拡張機能（優先度: 中）

1. **YAML 全文表示モーダル**
2. **テストデータ編集・再実行機能**
3. **失敗ワークフローの再生成ボタン**

---

## 5. データフロー

```
┌─────────────────────────────────────────────────────────────────┐
│                    Workflow Generation Flow                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ workflow_generation_node.py                                     │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ generate_workflow_for_task() returns:                       │ │
│ │   - yaml_content                                            │ │
│ │   - sample_input                                            │ │
│ │   - test_execution_result                                   │ │
│ │   - evaluation_score, feedback, suggestions                 │ │
│ │   - retry_count, generation_model                           │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ JobCreationStateManager                                         │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ workflow_statuses: [                                        │ │
│ │   {                                                         │ │
│ │     task_id, status, workflow_name, ...,                    │ │
│ │     summary: {                                              │ │
│ │       yaml_preview, sample_input, test_result,              │ │
│ │       evaluation, retry_info                                │ │
│ │     }                                                       │ │
│ │   }                                                         │ │
│ │ ]                                                           │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ /api/v1/jobs/{job_id}/status?include_summary=true              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ myAgentDesk                                                     │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ +page.svelte                                                │ │
│ │   └─ WorkflowTraceSummary.svelte                            │ │
│ │        ├─ EvaluationBadge.svelte                            │ │
│ │        ├─ YamlPreview.svelte                                │ │
│ │        └─ TestDataDisplay.svelte                            │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6. テスト計画

### 6.1 単体テスト

| テスト対象 | テスト内容 |
|-----------|-----------|
| WorkflowStatusItem | summary フィールドのシリアライズ/デシリアライズ |
| workflow_generation_node | サマリデータの正しい生成 |
| build_failure_details | 各失敗ステージの正しい判定 |
| build_failure_details | validation_errors からの原因分析抽出 |
| WorkflowTraceSummary.svelte | コンパクト/詳細モードの切り替え |
| FailureDetailsPanel.svelte | 失敗ステージ別の表示切り替え |
| CauseAnalysisCard.svelte | 原因分析情報の正しい表示 |
| RetryHistoryList.svelte | リトライ履歴のタイムライン表示 |
| EvaluationBadge.svelte | スコア範囲に応じた色分け |
| EvaluationDetailsPanel.svelte | 5項目スコアのプログレスバー表示 |
| YamlPreview.svelte | YAML の truncate 処理 |

### 6.2 結合テスト

| テスト対象 | テスト内容 |
|-----------|-----------|
| API → UI | include_summary=true でサマリが取得できること |
| 展開/折りたたみ | UI 状態が正しく切り替わること |
| 失敗詳細表示 | 失敗時に FailureDetailsPanel が表示されること |
| 失敗ステージ判定 | 各失敗ステージに応じた表示内容が正しいこと |
| アクションボタン | 再生成ボタンクリックで適切なAPIが呼ばれること |

### 6.3 受入テスト

| テストシナリオ | 期待結果 |
|---------------|---------|
| 成功ワークフローの詳細表示 | YAML、テストデータ、評価スコアが表示される |
| YAML生成失敗の詳細表示 | 構文エラー詳細とエラー行が表示される |
| API実行失敗の詳細表示 | HTTP ステータス、原因分析、推奨対応が表示される |
| 品質評価失敗の詳細表示 | 評価スコア詳細、不合格理由が表示される |
| リトライ履歴表示 | 各試行の結果とモデル名が時系列で表示される |
| 複数タスクの一括展開 | パフォーマンス問題なく動作する |

---

## 7. 非機能要件

### 7.1 パフォーマンス
- サマリデータはオンデマンドロード（展開時に取得）
- YAML プレビューは先頭 500 文字に制限
- ページ初期ロード時はサマリ非取得

### 7.2 アクセシビリティ
- 展開/折りたたみボタンにキーボードアクセス対応
- スクリーンリーダー対応のラベル

### 7.3 エラーハンドリング
- サマリ取得失敗時は「詳細を読み込めません」表示
- 部分的なデータ欠損に対する graceful degradation

---

## 8. 影響範囲

### 変更ファイル（予定）

**バックエンド (expertAgent)**:
- `app/services/job_creation_state.py` - WorkflowStatusItem モデル拡張
- `app/services/failure_details_builder.py` - **新規** FailureDetails 生成ロジック
- `aiagent/langgraph/jobTaskGeneratorAgents/nodes/workflow_generation.py` - サマリ生成統合
- `app/api/v1/job_generator_endpoints.py` - include_summary パラメータ対応

**フロントエンド (myAgentDesk)**:
- `src/lib/types/job-version.ts` - 型定義拡張
- `src/lib/api/clients/expert-agent.ts` - API クライアント拡張
- `src/lib/components/generation/WorkflowTraceSummary.svelte` - **新規** メインコンポーネント
- `src/lib/components/generation/FailureDetailsPanel.svelte` - **新規** 失敗詳細パネル
- `src/lib/components/generation/CauseAnalysisCard.svelte` - **新規** 原因分析カード
- `src/lib/components/generation/RetryHistoryList.svelte` - **新規** リトライ履歴
- `src/lib/components/generation/YamlPreview.svelte` - **新規** YAML プレビュー
- `src/lib/components/generation/EvaluationBadge.svelte` - **新規** 評価バッジ
- `src/lib/components/generation/EvaluationDetailsPanel.svelte` - **新規** 評価詳細
- `src/lib/components/generation/TestDataDisplay.svelte` - **新規** テストデータ表示
- `src/routes/projects/[projectId]/workbenches/[workbenchId]/generate/+page.svelte` - 統合

---

## 9. 承認

| 役割 | 名前 | 日付 | 承認 |
|-----|-----|------|-----|
| 設計者 | Claude | 2025-12-24 | ✅ |
| レビュアー | - | - | ⬜ |
| 承認者 | - | - | ⬜ |

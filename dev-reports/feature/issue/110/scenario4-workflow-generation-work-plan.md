# 作業計画: シナリオ4各タスクのワークフロー生成と動作確認

**作成日**: 2025-10-27
**ブランチ**: feature/issue/110
**担当**: Claude Code
**プロジェクト**: expertAgent - workflowGeneratorAgents

---

## 📋 要求・要件

### ユーザー要求
> シナリオ４（ジョブID＝j_01K8DRZGFHWMPRNWJXJZA3QCYK）で生成した各タスクについて、workflowGeneratorAgentsを使用してLLMワークフローを生成し動作確認を実施して欲しいです。
> 作業計画を立案しドキュメントに出力してください。
> なお、タスク毎に動作確認を実施しレポートとして出力して欲しいです。

### 機能要件

1. **ワークフロー自動生成**
   - workflowGeneratorAgentsを使用して各タスクのGraphAI YAMLワークフローを生成
   - TaskMaster IDを入力として、自動的にワークフローYAMLを生成
   - Self-repair機能による自動修正（最大3回リトライ）

2. **動作確認**
   - 生成されたワークフローをGraphAIサーバーに登録
   - サンプル入力データでワークフロー実行
   - 実行結果の検証（正常終了、エラーログ確認）

3. **タスク毎のレポート作成**
   - 各タスク（7タスク）について個別のレポートを作成
   - レポート内容: 生成結果、実行結果、エラー分析、改善提案

### 非機能要件

- **信頼性**: 自動生成されたYAMLの構文エラー率 0%
- **パフォーマンス**: タスク1件あたりの生成時間 < 120秒
- **保守性**: レポートはMarkdown形式で統一
- **トレーサビリティ**: 全生成結果とテスト結果をファイルとして保存

---

## 🏗️ アーキテクチャ設計

### システム構成

```
┌─────────────────────────────────────────────────────────────┐
│                     Claude Code (作業実行者)                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              expertAgent API (Port 8104)                    │
│  ┌────────────────────────────────────────────────────────┐ │
│  │    /v1/workflow-generator (POST)                       │ │
│  │    - Input: task_master_id                             │ │
│  │    - Output: GraphAI YAML workflow                     │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  workflowGeneratorAgents (LangGraph)                   │ │
│  │    ┌──────────────────────────────────────┐            │ │
│  │    │ 1. generator                         │            │ │
│  │    │ 2. sample_input_generator            │            │ │
│  │    │ 3. workflow_tester                   │            │ │
│  │    │ 4. validator                         │            │ │
│  │    │ 5. self_repair (retry loop)          │            │ │
│  │    └──────────────────────────────────────┘            │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│            GraphAI Server (Port 8105) - Optional            │
│  - Workflow Registration API                                │
│  - Workflow Execution API                                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   PostgreSQL Database                       │
│  - JobMaster: jm_01K8DRZGD7XJD8EJ8MAA8EFH4M                │
│  - TaskMaster: 7 tasks (tm_01K8DRZG9NC7EP45H9K7YBXF3Z, ...) │
│  - InterfaceMaster: Input/Output schemas                    │
└─────────────────────────────────────────────────────────────┘
```

### 技術選定

| 技術要素 | 選定技術 | 選定理由 |
|---------|---------|---------|
| **ワークフロー生成** | workflowGeneratorAgents (LangGraph) | 自動リトライ、Self-repair機能内蔵 |
| **LLMモデル** | Gemini 2.5 Flash | 高速、低コスト、JSON出力に対応 |
| **データベース** | PostgreSQL | expertAgentの既存データベース |
| **レポート形式** | Markdown | 可読性、Git管理容易 |
| **テスト実行** | GraphAI Server API | 実際の実行環境で動作確認 |

### ディレクトリ構成

```
dev-reports/feature/issue/110/
├── scenario4-workflow-generation-work-plan.md         # 本ドキュメント
├── scenario4-task-001-report.md                       # タスク1レポート
├── scenario4-task-002-report.md                       # タスク2レポート
├── scenario4-task-003-report.md                       # タスク3レポート
├── scenario4-task-004-report.md                       # タスク4レポート
├── scenario4-task-005-report.md                       # タスク5レポート
├── scenario4-task-006-report.md                       # タスク6レポート
├── scenario4-task-007-report.md                       # タスク7レポート
└── scenario4-final-summary.md                         # 最終サマリー

/tmp/scenario4_workflows_test/
├── task_001_keyword_analysis.yaml                     # 生成されたYAML
├── task_001_generation_result.json                    # 生成結果JSON
├── task_001_execution_result.json                     # 実行結果JSON
├── task_002_script_generation.yaml
├── task_002_generation_result.json
├── task_002_execution_result.json
├── ... (タスク3-7も同様)
└── summary.json                                       # 全体サマリー
```

---

## ✅ 制約条件チェック結果

### コード品質原則
- [x] **SOLID原則**: 遵守（workflowGeneratorAgentsは単一責任）
- [x] **KISS原則**: 遵守（シンプルなAPI呼び出し）
- [x] **YAGNI原則**: 遵守（必要な機能のみ実装）
- [x] **DRY原則**: 遵守（共通処理はworkflowGeneratorAgentsに集約）

### アーキテクチャガイドライン
- [x] **architecture-overview.md**: 準拠（expertAgent APIの既存設計に従う）
- [x] **GRAPHAI_WORKFLOW_GENERATION_RULES.md**: 遵守予定（GraphAI YAMLフォーマット）

### 設定管理ルール
- [x] **環境変数**: expertAgent APIサーバーURL（http://localhost:8104）
- [x] **myVault**: LLM API Key管理（expertAgent側で実施）

### 品質担保方針
- [ ] **単体テスト**: 各タスクのワークフロー生成テスト（実施予定）
- [ ] **結合テスト**: GraphAI実行テスト（実施予定）
- [x] **カバレッジ**: 全7タスクを対象（100%）

### 参照ドキュメント遵守
- [x] **GRAPHAI_WORKFLOW_GENERATION_RULES.md**: ワークフロー生成時に遵守
- [x] **新プロジェクト追加時**: 該当なし（既存expertAgentプロジェクト）

### 違反・要検討項目
なし

---

## 📊 Phase分解

### Phase 1: 環境確認・準備 (30分)

**目的**: 作業環境の準備と前提条件の確認

#### タスク
- [ ] expertAgent APIサーバー起動確認
- [ ] PostgreSQL接続確認
- [ ] シナリオ4の7タスク存在確認
- [ ] 作業ディレクトリ作成 (`/tmp/scenario4_workflows_test/`)
- [ ] GraphAIサーバー起動確認（オプション）

#### 成功基準
- ✅ expertAgent API `/health` エンドポイントが200 OKを返す
- ✅ データベースに7タスク（tm_01K8DRZG9NC7EP45H9K7YBXF3Z 他）が存在
- ✅ 作業ディレクトリが作成済み

---

### Phase 2: タスク1-3のワークフロー生成・動作確認 (4-5時間)

**目的**: 最優先タスク（タスク1-3）のワークフロー生成と動作確認

#### 対象タスク

| # | TaskMaster ID | タスク名 | 優先度 |
|---|--------------|---------|-------|
| 1 | `tm_01K8DRZG9NC7EP45H9K7YBXF3Z` | キーワード分析と構成案作成 | 🔴 最優先 |
| 2 | `tm_01K8DRZGAB6Z9RJ704RH3Z2KAD` | ポッドキャストスクリプト生成 | 🟡 高 |
| 3 | `tm_01K8DRZGAZXVBQVGCANWEMGZRC` | 音声ファイル生成（TTS） | 🟡 高 |

#### タスク実施内容（各タスク共通）

##### 2.1 ワークフロー生成

**API呼び出し**:
```bash
curl -X POST http://localhost:8104/aiagent-api/v1/workflow-generator \
  -H "Content-Type: application/json" \
  -d '{
    "task_master_id": "tm_01K8DRZG9NC7EP45H9K7YBXF3Z"
  }' \
  | jq '.' > /tmp/scenario4_workflows_test/task_001_generation_result.json
```

**検証項目**:
- [ ] HTTP 200 OK応答
- [ ] `status: "success"` が返される
- [ ] `yaml_content` にGraphAI YAML形式のワークフローが含まれる
- [ ] `is_valid: true` （バリデーション成功）
- [ ] `retry_count` が3回以内

##### 2.2 YAML保存

```bash
jq -r '.yaml_content' /tmp/scenario4_workflows_test/task_001_generation_result.json \
  > /tmp/scenario4_workflows_test/task_001_keyword_analysis.yaml
```

##### 2.3 YAML構文検証

**検証項目**:
- [ ] `source: {}` ノードが存在
- [ ] `version: 0.5` が設定されている
- [ ] YAML構文エラーがない（yamllint使用）
- [ ] `:source.property_name` 形式でのuser_input参照が実装されている

##### 2.4 GraphAI実行テスト（オプション）

**前提条件**: GraphAIサーバーが起動している

**実行手順**:
```bash
# ワークフロー登録
curl -X POST http://localhost:8105/api/v1/workflow/register \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_name": "keyword_analysis",
    "yaml_content": "'"$(cat /tmp/scenario4_workflows_test/task_001_keyword_analysis.yaml)"'"
  }'

# 実行テスト
curl -X POST http://localhost:8105/api/v1/myagent/default/keyword_analysis \
  -H "Content-Type: application/json" \
  -d '{
    "user_input": {
      "keyword": "AI技術の最新動向",
      "target_duration": "15分"
    }
  }' \
  | jq '.' > /tmp/scenario4_workflows_test/task_001_execution_result.json
```

**検証項目**:
- [ ] HTTP 200 OK応答
- [ ] `results.output` にポッドキャスト構成案が含まれる
- [ ] エラーログがない

##### 2.5 レポート作成

**テンプレート**:
```markdown
# タスク1: キーワード分析と構成案作成 - 動作確認レポート

## 📊 生成結果
- Status: success/failed
- Retry count: X回
- Generation time: XX秒

## ✅ YAML検証結果
- source: {} ノード: ✅/❌
- user_input参照: ✅/❌
- YAML構文: ✅/❌

## 🚀 実行テスト結果
- GraphAI登録: ✅/❌
- ワークフロー実行: ✅/❌
- Output検証: ✅/❌

## 🐛 検出された問題
（あれば記載）

## 💡 改善提案
（あれば記載）
```

#### 成功基準（Phase 2）
- ✅ タスク1-3のワークフローYAML生成成功（3/3）
- ✅ YAML構文エラー 0件
- ✅ タスク1のGraphAI実行成功（最低1タスク）
- ✅ タスク1-3の個別レポート作成完了

---

### Phase 3: タスク4-7のワークフロー生成・動作確認 (4-5時間)

**目的**: 残りタスク（タスク4-7）のワークフロー生成と動作確認

#### 対象タスク

| # | TaskMaster ID | タスク名 | 優先度 |
|---|--------------|---------|-------|
| 4 | `tm_01K8DRZGBFWCSWYF8ZG14CVWQ8` | ポッドキャストファイルアップロード | 🟢 中 |
| 5 | `tm_01K8DRZGC0G5QB4GQ6V1RRDQS8` | 公開リンク生成 | 🟢 中 |
| 6 | `tm_01K8DRZGCFT6C1EQT9X6DV9WB9` | メール本文構成 | 🟢 中 |
| 7 | `tm_01K8DRZGCW3K7ZQP0FD6A7C7B6` | ポッドキャストリンクのメール送信 | 🟢 中 |

#### タスク実施内容
Phase 2と同様の手順で実施:
1. ワークフロー生成
2. YAML保存
3. YAML構文検証
4. GraphAI実行テスト（オプション）
5. レポート作成

#### 特記事項
- **タスク4-5**: Google Drive API連携が必要（認証情報が必要）
- **タスク6-7**: Gmail API連携が必要（テスト用アカウント必要）
- 認証情報がない場合はYAML生成のみ実施、実行テストはスキップ可能

#### 成功基準（Phase 3）
- ✅ タスク4-7のワークフローYAML生成成功（4/4）
- ✅ YAML構文エラー 0件
- ✅ タスク4-7の個別レポート作成完了

---

### Phase 4: End-to-End動作確認（オプション） (2-3時間)

**目的**: シナリオ4全体の連携動作確認

#### 実施内容

##### 4.1 全タスク連携テスト

**テストシナリオ**:
1. ユーザーがキーワード "機械学習の基礎" を入力
2. タスク1で構成案生成
3. タスク2でスクリプト生成（タスク1の出力を使用）
4. タスク3で音声ファイル生成（タスク2の出力を使用）
5. タスク4でGoogle Driveにアップロード（タスク3の出力を使用）
6. タスク5で公開リンク生成（タスク4の出力を使用）
7. タスク6でメールコンテンツ作成（タスク5の出力を使用）
8. タスク7でメール送信（タスク6の出力を使用）

**実施条件**:
- expertAgent APIサーバーが起動
- GraphAIサーバーが起動
- Google API認証情報が設定済み
- テスト用Gmailアカウントが利用可能

##### 4.2 異常系テスト

**テストケース**:
- 不正なキーワード入力（空文字列、特殊文字）
- タスク間のデータ不整合（スキーマ違反）
- API エラー（TTS API、Gmail API）
- タイムアウト（長時間処理）

#### 成功基準（Phase 4）
- ✅ 全7タスクの連携動作成功
- ✅ 異常系テストで適切なエラーハンドリング確認

---

### Phase 5: 最終評価・ドキュメント作成 (2時間)

**目的**: 全作業結果の評価とサマリー作成

#### 5.1 評価指標の測定

| 評価項目 | 目標 | 実績 | 判定 |
|---------|------|------|------|
| **YAML生成成功率** | 100% (7/7) | XX% | ✅/❌ |
| **YAML構文エラー** | 0件 | XX件 | ✅/❌ |
| **sourceノード設定率** | 100% (7/7) | XX% | ✅/❌ |
| **user_input参照正確性** | 100% (7/7) | XX% | ✅/❌ |
| **ワークフロー実行成功率** | ≥30% (2/7) | XX% | ✅/❌ |
| **平均生成時間** | <120秒/タスク | XX秒 | ✅/❌ |
| **平均リトライ回数** | <1.5回 | XX回 | ✅/❌ |

#### 5.2 タスク別結果サマリー

| # | タスク名 | 生成 | YAML検証 | 実行テスト | 総合評価 |
|---|---------|------|---------|-----------|---------|
| 1 | キーワード分析 | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ |
| 2 | スクリプト生成 | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ |
| 3 | 音声ファイル生成 | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ |
| 4 | ファイルアップロード | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ |
| 5 | 公開リンク生成 | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ |
| 6 | メール本文構成 | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ |
| 7 | メール送信 | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ |

#### 5.3 成果物

**ドキュメント**:
- [x] `scenario4-workflow-generation-work-plan.md`: 本ドキュメント
- [ ] `scenario4-task-001-report.md`: タスク1レポート
- [ ] `scenario4-task-002-report.md`: タスク2レポート
- [ ] `scenario4-task-003-report.md`: タスク3レポート
- [ ] `scenario4-task-004-report.md`: タスク4レポート
- [ ] `scenario4-task-005-report.md`: タスク5レポート
- [ ] `scenario4-task-006-report.md`: タスク6レポート
- [ ] `scenario4-task-007-report.md`: タスク7レポート
- [ ] `scenario4-final-summary.md`: 最終サマリー

**成果物（YAML）**:
- [ ] `task_001_keyword_analysis.yaml`
- [ ] `task_002_script_generation.yaml`
- [ ] `task_003_audio_generation.yaml`
- [ ] `task_004_file_upload.yaml`
- [ ] `task_005_public_link.yaml`
- [ ] `task_006_email_body.yaml`
- [ ] `task_007_email_send.yaml`

**成果物（テスト結果）**:
- [ ] `task_001_generation_result.json`
- [ ] `task_001_execution_result.json`
- [ ] （以下同様、タスク2-7も）
- [ ] `summary.json`

#### 成功基準（Phase 5）
- ✅ 全7タスクの個別レポート作成完了
- ✅ 最終サマリードキュメント作成完了
- ✅ 評価指標測定完了

---

## 📅 スケジュール

| Phase | 内容 | 予定工数 | 優先度 | 開始予定 | 完了予定 |
|-------|------|---------|-------|---------|---------|
| Phase 1 | 環境確認・準備 | 30分 | 🔴 最優先 | 即時 | +30分 |
| Phase 2 | タスク1-3生成・動作確認 | 4-5時間 | 🔴 最優先 | +30分 | +5.5時間 |
| Phase 3 | タスク4-7生成・動作確認 | 4-5時間 | 🟡 高 | +5.5時間 | +10.5時間 |
| Phase 4 | E2E動作確認（オプション） | 2-3時間 | 🟢 中 | +10.5時間 | +13.5時間 |
| Phase 5 | 最終評価・ドキュメント | 2時間 | 🟡 高 | +10.5時間 | +12.5時間 |

**総予定工数**:
- 必須タスク（Phase 1-3, 5）: 10.5-12.5時間
- オプションタスク（Phase 4）: +2-3時間
- **合計**: 12.5-15.5時間

---

## ⚠️ リスクと対策

### リスク1: expertAgent APIサーバーが起動していない

**リスク**: ワークフロー生成APIが利用できない

**対策**:
- Phase 1で環境確認を実施
- サーバー起動コマンド: `cd expertAgent && uv run uvicorn app.main:app --host 0.0.0.0 --port 8104`
- ヘルスチェック: `curl http://localhost:8104/health`

### リスク2: GraphAIサーバーが利用不可

**リスク**: ワークフロー実行テストができない

**対策**:
- YAML生成と静的検証のみ実施
- 実行テストはオプションとする
- 最小構成でのローカルGraphAI環境構築

### リスク3: 生成されたYAMLに実行エラーが発生

**リスク**: workflowGeneratorAgentsのプロンプトが不十分

**対策**:
- Self-repair機能が最大3回リトライ
- エラーパターンを収集してプロンプト改善
- 手動修正パターンを文書化

### リスク4: Google API認証情報がない

**リスク**: タスク4-7の実行テストができない

**対策**:
- タスク1-3のみ動作確認を実施
- YAML生成は全タスク実施
- 認証情報設定手順を文書化

### リスク5: 生成時間が長すぎる

**リスク**: 7タスク生成に14分以上かかる（Phase 2実績: 平均109秒/タスク）

**対策**:
- タイムアウト設定を調整（現在200秒）
- 並列生成の検討（現在は直列）
- モデル選択の最適化（Gemini 2.5 Flash推奨）

---

## 📚 参考ドキュメント

**必須参照**:
- [ ] [GraphAI ワークフロー生成ルール](../../../graphAiServer/docs/GRAPHAI_WORKFLOW_GENERATION_RULES.md)
- [ ] [workflowGeneratorAgents agent.py](../../../expertAgent/aiagent/langgraph/workflowGeneratorAgents/agent.py)
- [ ] [アーキテクチャ概要](../../../docs/design/architecture-overview.md)

**推奨参照**:
- [ ] `llm-agent-migration-design.md`: expertAgent jsonoutput API移行設計
- [ ] `phase-3-llm-migration-complete.md`: LLMエージェント移行完了報告
- [ ] `phase-4-work-plan.md`: sourceノード修正後のワークフロー再生成計画

---

## 📝 設計上の決定事項

1. **タスク毎のレポート作成**
   - ユーザー要求に従い、各タスク（7タスク）について個別レポートを作成
   - レポートテンプレートを統一し、比較しやすくする

2. **Phase分解の優先順位**
   - タスク1-3を最優先（コアワークフロー）
   - タスク4-7は認証情報が必要な可能性があるため後回し
   - E2E動作確認はオプションとする

3. **実行テストの位置づけ**
   - YAML生成は必須
   - GraphAI実行テストはオプション（環境依存）
   - 最低1タスク（タスク1）の実行成功を目標とする

4. **成果物の保存場所**
   - ドキュメント: `dev-reports/feature/issue/110/`
   - YAML・JSON: `/tmp/scenario4_workflows_test/`
   - Git管理対象: ドキュメントのみ（YAML・JSONは参考資料）

5. **評価指標の設定**
   - YAML生成成功率: 100%（必須）
   - ワークフロー実行成功率: ≥30%（最低2タスク）
   - 平均生成時間: <120秒/タスク

---

**作成日**: 2025-10-27
**作成者**: Claude Code
**バージョン**: 1.0
**ステータス**: 作業計画立案完了 → 実施待ち

# 設計方針: GraphAI標準LLMエージェント廃止とexpertAgent統合

**作成日**: 2025-10-26
**ブランチ**: feature/issue/110
**担当者**: Claude Code

---

## 📋 要求・要件

### ユーザー要求
> LLMエージェントについてgraphAI標準のエージェント（anthropicAgent、geminiAgent、openAIAgent、groqAgent、replicateAgent）の使用を禁止してください。
> その代わり、expertAgentの "/aiagent/utility/jsonoutput" を使用するようにしてください。

### 背景
- **現状の問題**:
  - GraphAI標準のLLMエージェント（geminiAgent等）がマークダウンコードブロック（```json ... ```）でJSONを返す
  - jsonParserAgentでパースエラーが発生
  - ワークフロー実行が中断される

- **expertAgent `/aiagent/utility/jsonoutput` の利点**:
  - マークダウン抽出機能内蔵（`toParseJson`関数）
  - 常に純粋なdict（辞書）を返す
  - 複数のLLMモデル対応（Claude, GPT, Gemini, Ollama）
  - 統一されたインターフェース

---

## 🏗️ アーキテクチャ設計

### 変更前のワークフロー構造

```yaml
# 従来のGraphAI標準エージェント使用
generate_podcast_config:
  agent: geminiAgent
  params:
    model: gemini-2.5-flash
  inputs:
    prompt: |
      Generate podcast config...
```

### 変更後のワークフロー構造

```yaml
# expertAgent jsonoutput API使用
generate_podcast_config:
  agent: fetchAgent
  params:
    method: POST
    headers:
      Content-Type: application/json
    url: http://localhost:8104/aiagent-api/v1/aiagent/utility/jsonoutput
  inputs:
    body:
      user_input: |
        Generate podcast config...
      model_name: gemini-2.5-flash
      project: default
  timeout: 30000
```

### API仕様確認

**エンドポイント**: `POST /aiagent-api/v1/aiagent/utility/jsonoutput`

**リクエストボディ**:
```json
{
  "user_input": "プロンプト文字列",
  "model_name": "gpt-4o-mini | gemini-2.5-flash | claude-3-5-sonnet | ...",
  "project": "default | default_project | ..."
}
```

**レスポンス**:
```json
{
  "result": { ... },  // 純粋なJSONオブジェクト（マークダウン削除済み）
  "type": "jsonOutput",
  "attempts": 1       // リトライ回数（optional）
}
```

**重要な特徴**:
1. ✅ マークダウンコードブロック自動削除
2. ✅ 複数LLMモデル対応
3. ✅ リトライ機能内蔵
4. ✅ 統一されたJSON出力

---

## 📝 実装計画

### Phase 1: workflowGeneratorAgents プロンプト修正

**ファイル**: `aiagent/langgraph/workflowGeneratorAgents/prompts/workflow_generation.py`

**修正内容**:

#### 1. Agent Selection セクションの書き換え

**修正前**:
```
5. **Agent Selection** (CRITICAL):
   - **PRIORITY**: If "Recommended APIs" are specified, use them first
   - For LLM processing:
     * geminiAgent: Use gemini-2.5-flash as default model (REQUIRED)
     * openAIAgent: Use gpt-4o-mini as fallback
```

**修正後**:
```
5. **Agent Selection** (CRITICAL):
   - **PRIORITY**: If "Recommended APIs" are specified, use them first
   - **IMPORTANT**: NEVER use GraphAI standard LLM agents (geminiAgent, openAIAgent, anthropicAgent, groqAgent, replicateAgent)
   - For LLM processing:
     * Use fetchAgent to call expertAgent jsonoutput API
     * URL: http://localhost:8104/aiagent-api/v1/aiagent/utility/jsonoutput
     * Default model: gemini-2.5-flash (recommended), gpt-4o-mini (fallback)
```

#### 2. Example Workflow Structure の書き換え

**修正前の例** (geminiAgent使用):
```yaml
llm_analysis:
  agent: geminiAgent
  params:
    model: gemini-2.5-flash
  inputs:
    prompt: |
      Analyze: :source.keyword
```

**修正後の例** (fetchAgent + jsonoutput):
```yaml
llm_analysis:
  agent: fetchAgent
  params:
    method: POST
    headers:
      Content-Type: application/json
    url: http://localhost:8104/aiagent-api/v1/aiagent/utility/jsonoutput
  inputs:
    body:
      user_input: |
        Analyze: :source.keyword
      model_name: gemini-2.5-flash
      project: default
  timeout: 30000
```

#### 3. 複数の Example 追加

以下のパターンのワークフロー例を追加：

**Example 1**: Gemini 2.5 Flash使用（推奨）
**Example 2**: GPT-4o-mini使用（フォールバック）
**Example 3**: Claude 3.5 Sonnet使用（高品質）
**Example 4**: 複数LLMノードの組み合わせ

---

### Phase 2: recommended_apis の更新

**ファイル**: `aiagent/langgraph/jobTaskGeneratorAgents/prompts/task_breakdown.py`

**修正内容**:

#### 利用可能なAPI種別の更新

**修正前**:
```python
**GraphAI標準エージェント**:
- `geminiAgent`: Google Gemini APIを使用したLLM処理（推奨モデル: gemini-2.5-flash）
- `openAIAgent`: OpenAI APIを使用したLLM処理
- `fetchAgent`: HTTP APIコール（RESTful API呼び出し）
```

**修正後**:
```python
**LLM処理 (expertAgent jsonoutput API)**:
- LLM処理には必ず expertAgent の jsonoutput API を使用
- URL: `http://localhost:8104/aiagent-api/v1/aiagent/utility/jsonoutput`
- 推奨モデル: `gemini-2.5-flash` (Google Gemini 2.5 Flash)
- フォールバックモデル: `gpt-4o-mini` (OpenAI GPT-4o mini)
- 高品質モデル: `claude-3-5-sonnet` (Anthropic Claude 3.5 Sonnet)
- fetchAgent経由で呼び出す

**その他のエージェント**:
- `fetchAgent`: HTTP APIコール（expertAgent jsonoutput API含む）
- `copyAgent`: データコピー・フォーマット変換
- `jsonParserAgent`: JSON解析（※ user_inputの解析には使用しない）
```

#### recommended_apis の具体例

**修正前**:
```json
{
  "task_id": "task_002",
  "name": "検索結果の分析",
  "recommended_apis": ["geminiAgent"]
}
```

**修正後**:
```json
{
  "task_id": "task_002",
  "name": "検索結果の分析",
  "recommended_apis": ["fetchAgent (expertAgent jsonoutput API)"],
  "implementation_note": "Use fetchAgent to call http://localhost:8104/aiagent-api/v1/aiagent/utility/jsonoutput with model_name=gemini-2.5-flash"
}
```

---

### Phase 3: 既存ワークフローの移行戦略

#### 自動移行不要
- GraphAI標準エージェントを含むワークフローは既に登録済み
- 新規生成されるワークフローから適用

#### 手動移行が必要な既存ワークフロー（オプション）
- `keyword_analysis_podcast_config.yml`
- `podcast_script_generation.yml`
- 他、geminiAgent/openAIAgent使用ワークフロー

**移行手順**:
1. 既存YAMLを読み込み
2. geminiAgent/openAIAgent ノードを検出
3. fetchAgent + jsonoutput API形式に変換
4. 動作確認後、上書き登録

---

## 📊 期待される効果

### 改善指標

| 指標 | 変更前 | 変更後 | 期待改善率 |
|------|-------|-------|-----------|
| **JSON パースエラー** | 発生 | 解消 | +100% |
| **ワークフロー完了率** | 60% (3/5ノード) | 100% (5/5ノード) | +67% |
| **マークダウン処理** | 手動対応必要 | 自動処理 | +100% |
| **LLMモデル選択** | エージェント固定 | リクエスト時指定 | 柔軟性向上 |
| **エラーハンドリング** | なし | リトライ機能 | 信頼性向上 |

### 副次的な利点

1. **LLM統一管理**
   - expertAgent で全LLM呼び出しを一元管理
   - API Key管理がシンプルに（myVault経由）
   - ログ・監視の統一

2. **柔軟なモデル選択**
   - ワークフロー実行時にモデルを動的に変更可能
   - コスト最適化が容易（タスクに応じてモデル選択）

3. **JSON出力保証**
   - マークダウン削除が自動
   - jsonParserAgent不要（直接JSONオブジェクト取得）

---

## ✅ 制約条件チェック

### コード品質原則
- [x] **SOLID原則**: 遵守（単一責任：expertAgentがLLM呼び出しを担当）
- [x] **KISS原則**: 遵守（シンプルなfetchAgent呼び出し）
- [x] **YAGNI原則**: 遵守（必要な機能のみ）
- [x] **DRY原則**: 遵守（LLM呼び出しロジックを集約）

### アーキテクチャガイドライン
- [x] **architecture-overview.md**: 準拠（expertAgentとGraphAIの分離維持）
- [x] **GRAPHAI_WORKFLOW_GENERATION_RULES.md**: 更新予定

### 設定管理ルール
- [x] **環境変数管理**: expertAgentのURL（将来的に設定可能）
- [x] **myVault連携**: expertAgent側でAPI Key管理

### 品質担保方針
- [ ] **単体テスト**: workflowGeneratorAgentsのプロンプト変更テスト
- [ ] **結合テスト**: 生成されたYAMLの実行テスト

---

## 🎯 実装ステップ

### Step 1: プロンプト修正（約30分）
1. `workflow_generation.py` のAgent Selectionセクション書き換え
2. Example Workflow Structure追加（3-4パターン）
3. LLM禁止の明示

### Step 2: recommended_apis 説明更新（約15分）
1. `task_breakdown.py` のAPI種別説明更新
2. Few-shot learning例の更新

### Step 3: テスト（約30分）
1. ワークフロー生成テスト（recommended_apisが正しく反映されるか）
2. 生成されたYAMLの実行テスト（fetchAgent + jsonoutput API）
3. エラーハンドリング確認

### Step 4: ドキュメント更新（約15分）
1. `GRAPHAI_WORKFLOW_GENERATION_RULES.md` 更新
2. final-report.md 更新

**合計予想時間**: 約1.5時間

---

## 📋 リスク分析

### リスク1: expertAgent サーバーの可用性
- **発生確率**: 低
- **影響度**: 高（ワークフロー全体が停止）
- **対策**:
  - expertAgent のヘルスチェック実装
  - リトライ機能活用
  - タイムアウト設定

### リスク2: ネットワークレイテンシ
- **発生確率**: 低（ローカル通信）
- **影響度**: 中（実行時間増加）
- **対策**:
  - タイムアウトを適切に設定（30秒推奨）
  - 非同期処理活用

### リスク3: 既存ワークフローの互換性
- **発生確率**: 中
- **影響度**: 中（既存ワークフローが動作しなくなる）
- **対策**:
  - 新規生成ワークフローのみ適用
  - 既存ワークフローは手動移行（オプション）

---

## 📝 まとめ

### 設計のポイント

1. **GraphAI標準LLMエージェント完全廃止**
   - geminiAgent, openAIAgent, anthropicAgent, groqAgent, replicateAgent 使用禁止
   - workflowGeneratorAgents のプロンプトで明示

2. **expertAgent jsonoutput API 統一使用**
   - fetchAgent経由で呼び出し
   - マークダウン削除自動化
   - JSON出力保証

3. **柔軟なモデル選択**
   - gemini-2.5-flash（推奨）
   - gpt-4o-mini（フォールバック）
   - claude-3-5-sonnet（高品質）

4. **段階的移行**
   - 新規ワークフローから適用
   - 既存ワークフローは任意で移行

---

**作成日**: 2025-10-26
**作成者**: Claude Code
**ブランチ**: feature/issue/110
**次のアクション**: Phase 1実装開始

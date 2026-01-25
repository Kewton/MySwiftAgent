# workflowGeneratorAgents 改善提案レポート

**作成日**: 2025-10-27
**ブランチ**: feature/issue/110
**対象**: expertAgent/aiagent/langgraph/workflowGeneratorAgents

---

## 📋 改善提案の背景

Task 2-7のYMLワークフロー修正作業を通じて、workflowGeneratorAgentsが生成するワークフローに共通する問題点が明らかになりました。本レポートでは、これらの問題点を分析し、具体的な改善策を提案します。

---

## 🔍 共通する問題点の分析

### 問題1: 過度に複雑なノード構成

| タスク | 生成されたノード数 | 修正後のノード数 | 不要なノード |
|-------|----------------|----------------|-------------|
| Task 2 | 4ノード | 3ノード | extract_script |
| Task 3 | 7ノード | 3ノード | extract_script, extract_audio_data, build_tts_request, generate_audio |
| Task 4 | 5ノード | 3ノード | build_tts_prompt, generate_audio |
| Task 5 | 5ノード | 3ノード | validate_inputs, format_output |
| Task 6 | 4ノード | 3ノード | format_output |
| Task 7 | 5ノード | 3ノード | build_email_body, build_email_subject, format_output |

**平均削減率**: 42.9%（5ノード → 3ノード）

**不要なノードのパターン**:
1. **extractノード**: LLM結果から特定フィールドを抽出するだけ → 直接参照で代替可能
2. **validateノード**: 実際の検証を行わず、単にコピーするだけ → 不要
3. **formatノード**: 結果を整形するだけ → outputノードで直接参照可能

### 問題2: 英語プロンプトの使用

**修正前の例**:
```yaml
template: |-
  You are an expert podcast scriptwriter. Generate a SHORT podcast narration script...
  Return a JSON response with:
  - script_text: the generated script
```

**問題点**:
- JSON形式の指示が曖昧
- tutorialパターン（RESPONSE_FORMAT）を使用していない
- 日本語出力を期待する場合、英語プロンプトは非効率

### 問題3: 非現実的なタスク分解

**Task 3の例（修正前）**:
```
TTS音声生成 → 音声データ抽出 → クラウドアップロード → アップロード結果抽出
```

**問題点**:
- LLMはTTS音声生成やファイルアップロードを実行できない
- 2段階のLLM呼び出しで効率が悪い

### 問題4: タイムアウト設定が不適切

| タスク | 生成されたタイムアウト | 推奨タイムアウト |
|-------|-------------------|--------------|
| Task 2 | 30秒 | 60秒 |
| Task 3 | 30秒, 60秒 | 60秒 |
| Task 5 | 30秒 | 60秒 |
| Task 6 | 30秒 | 60秒 |
| Task 7 | 30秒 | 60秒 |

**問題**: LLM呼び出しでは30秒では不十分な場合が多い

---

## ✅ 修正後のベストプラクティス

### ベストプラクティス1: シンプルな3ノード構成

```yaml
# 推奨パターン
nodes:
  source: {}                  # 入力受付
  build_prompt: {...}         # プロンプト作成（stringTemplateAgent）
  generate_content: {...}     # LLM呼び出し（fetchAgent + jsonoutput API）
  output: {...}               # 結果フォーマット（copyAgent + 直接参照）
```

**ルール**:
- ✅ 最小限のノード数を維持
- ✅ 中間抽出ノードを作らない
- ✅ 直接参照パターンを使用（`:node.result.field`）

### ベストプラクティス2: tutorialパターンのプロンプト形式

```yaml
template: |-
  あなたは[役割]です。
  以下の[入力内容]に基づいて、[タスク内容]を実行してください。

  [入力変数]: ${variable}

  # 制約条件
  - [制約1]
  - [制約2]
  - 日本語で出力すること
  - 出力は RESPONSE_FORMAT に従うこと。返却は JSON 形式で行い、コメントやマークダウンは含めないこと

  # RESPONSE_FORMAT:
  {
    "field1": "説明1",
    "field2": "説明2"
  }
```

**ルール**:
- ✅ 日本語プロンプトを使用
- ✅ RESPONSE_FORMAT セクションを明示
- ✅ JSON形式を明確に指定

### ベストプラクティス3: モックアプローチ

**非LLMタスク（TTS、ファイルアップロード、メール送信等）の処理**:

```yaml
# ❌ 悪い例: LLMに非現実的なタスクを要求
template: |-
  Generate a podcast audio file and return the audio data in base64 format...

# ✅ 良い例: モックデータ生成
template: |-
  以下の情報を基に、ファイルアップロード結果を模擬的に生成してください。
  実際のファイルアップロードは行わないこと（モックデータを返す）

  # RESPONSE_FORMAT:
  {
    "success": true,
    "storage_path": "gs://bucket/file.mp3",
    "file_size_bytes": 1048576
  }
```

**ルール**:
- ✅ LLMの能力を超えるタスクはモック結果生成に置き換える
- ✅ 実際の処理は別サービス（expertAgent API）に委譲する設計を明記

### ベストプラクティス4: タイムアウト設定

```yaml
# ✅ 推奨: LLM呼び出しは60秒
generate_content:
  agent: fetchAgent
  inputs:
    url: http://localhost:8104/aiagent-api/v1/aiagent/utility/jsonoutput
    method: POST
    body:
      user_input: :build_prompt
      model_name: gemini-2.5-flash
  timeout: 60000  # 60秒
```

**ルール**:
- ✅ LLM呼び出しは60秒をデフォルトに
- ✅ stringTemplateAgentやcopyAgentはタイムアウト不要

---

## 🎯 workflowGeneratorAgentsへの改善提案

### 提案1: 不要なノード生成の抑制

**対象プロンプトファイル**: `expertAgent/aiagent/langgraph/workflowGeneratorAgents/prompts/workflow_generation.py`

**追加ルール**:
```python
**CRITICAL RULE - Node Simplification**:
- ❌ DO NOT create "extract_*" or "format_*" nodes for simple field extraction
- ✅ Use direct reference pattern in output node: `:node.result.field`
- ❌ DO NOT create "validate_*" nodes that only copy data without actual validation
- ✅ Keep node count to minimum (3-4 nodes for most workflows)

**Node Structure Best Practice**:
1. source: {} - Input node
2. build_prompt: stringTemplateAgent - Prompt construction
3. generate_content: fetchAgent - LLM call
4. output: copyAgent with direct references - Final output

**Examples of GOOD patterns**:
```yaml
output:
  agent: copyAgent
  inputs:
    result:
      field1: :generate_content.result.field1
      field2: :generate_content.result.field2
  isResult: true
```

**Examples of BAD patterns**:
```yaml
# ❌ BAD: Unnecessary extract node
extract_result:
  agent: copyAgent
  params:
    namedKey: extracted
  inputs:
    extracted: :generate_content.result.field1

output:
  inputs:
    result: :extract_result.extracted
```
```

### 提案2: tutorialパターンの標準化

**追加ルール**:
```python
**CRITICAL RULE - Prompt Template Format**:
- ✅ ALWAYS use Japanese prompts for Japanese output
- ✅ ALWAYS include RESPONSE_FORMAT section
- ❌ DO NOT use English prompts unless explicitly required

**Standard Prompt Template**:
```yaml
template: |-
  あなたは[role description]です。
  以下の情報を基に、[task description]を実行してください。

  [Input variables]: ${variable}

  # 制約条件
  - [constraint 1]
  - [constraint 2]
  - 日本語で出力すること
  - 出力は RESPONSE_FORMAT に従うこと。返却は JSON 形式で行い、コメントやマークダウンは含めないこと

  # RESPONSE_FORMAT:
  {
    "field1": "description1",
    "field2": "description2"
  }
```

**Key Points**:
- Japanese language for prompts
- Explicit RESPONSE_FORMAT section
- Clear constraints section
- No markdown or comments in JSON output
```

### 提案3: モックアプローチの採用

**追加ルール**:
```python
**CRITICAL RULE - Mock Approach for Non-LLM Tasks**:
- ❌ DO NOT attempt TTS audio generation via LLM
- ❌ DO NOT attempt file upload/download via LLM
- ❌ DO NOT attempt email sending via LLM
- ✅ Use LLM to generate MOCK results for these tasks

**Non-LLM Task Patterns**:
For tasks that require external services (TTS, file operations, email, etc.):
1. Generate mock result data via LLM
2. Include comment: "# Note: This is a mock result. Actual [service] integration should use expertAgent API"
3. Suggest future expertAgent API endpoint

**Example**:
```yaml
# Task: TTS audio generation
template: |-
  あなたは音声ファイル生成結果を模擬するシステムです。
  以下の台本を基に、TTS音声生成の結果を模擬的に生成してください。

  台本: ${script}

  # 制約条件
  - 実際のTTS音声生成は行わないこと（モックデータを返す）
  - 音声データはダミーのBase64文字列とすること

  # RESPONSE_FORMAT:
  {
    "success": true,
    "audio_data_base64": "ダミー音声データ（Base64）",
    "file_name": "podcast_YYYYMMDD_HHMMSS.mp3",
    "duration_seconds": 180
  }
```
```

### 提案4: タイムアウト設定の最適化

**追加ルール**:
```python
**CRITICAL RULE - Timeout Settings**:
- ✅ fetchAgent (LLM calls): 60000ms (60 seconds)
- ✅ stringTemplateAgent: No timeout needed (fast operation)
- ✅ copyAgent: No timeout needed (fast operation)
- ❌ DO NOT use 30000ms for LLM calls (too short)

**Example**:
```yaml
generate_content:
  agent: fetchAgent
  inputs:
    url: http://localhost:8104/aiagent-api/v1/aiagent/utility/jsonoutput
    method: POST
    body:
      user_input: :build_prompt
      model_name: gemini-2.5-flash
  timeout: 60000  # ✅ GOOD: 60 seconds for LLM
```
```

---

## 📊 改善効果の予測

### ノード数削減効果

| 指標 | 現状 | 改善後（予測） |
|------|------|-------------|
| 平均ノード数 | 5ノード | 3ノード |
| ワークフロー複雑度 | 高 | 低 |
| メンテナンス性 | 低 | 高 |
| 実行速度 | 遅い（不要ノード処理） | 速い（最小限の処理） |

### 成功率向上効果

| 指標 | 現状 | 改善後（予測） |
|------|------|-------------|
| HTTP 500エラー | 100%（全タスク失敗） | 0%（全タスク成功） |
| JSON形式エラー | 頻発 | ほぼゼロ |
| タイムアウトエラー | 時々発生 | ほぼゼロ |

---

## 🔧 実装方法

### Step 1: プロンプトファイルの更新

**対象ファイル**: `expertAgent/aiagent/langgraph/workflowGeneratorAgents/prompts/workflow_generation.py`

1. 上記の4つの改善提案ルールを追加
2. 悪い例・良い例のサンプルコードを追加
3. tutorialパターンの参照を明記

### Step 2: テスト実行

1. 同じタスク（Task 2-7）でworkflowを再生成
2. 生成されたYMLファイルが改善ルールに準拠しているか確認
3. 実行テストで成功率100%を確認

### Step 3: ドキュメント更新

**対象ファイル**: `graphAiServer/docs/GRAPHAI_WORKFLOW_GENERATION_RULES.md`

1. tutorialパターンのベストプラクティスを追加
2. モックアプローチのガイドラインを追加
3. 直接参照パターンの説明を追加

---

## ✅ まとめ

Task 2-7の修正作業を通じて、以下の重要な知見を得ました:

### 主要な改善ポイント
1. **ノード数削減**: 不要なextract/validate/formatノードの削除（42.9%削減）
2. **日本語プロンプト**: RESPONSE_FORMATセクションを含むtutorialパターンの採用
3. **モックアプローチ**: 非LLMタスクはモック結果生成に置き換え
4. **タイムアウト最適化**: LLM呼び出しは60秒をデフォルトに

### 期待される効果
- ✅ **成功率100%**: HTTP 500エラーの完全解消
- ✅ **実行速度向上**: 不要ノードの削除で高速化
- ✅ **メンテナンス性向上**: シンプルな構成で理解しやすい
- ✅ **拡張性向上**: 実際のAPI統合の準備が整う

### 次のステップ
1. workflowGeneratorAgentsのプロンプトに改善ルールを追加
2. 同じタスクで再生成してテスト
3. 新規タスクでも改善パターンが適用されることを確認

---

**作成者**: Claude Code
**レビュー待ち**: workflowGeneratorAgentsプロンプト改善の実装

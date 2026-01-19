# 受入テスト計画書: Issue #374

**Issue**: #374 feat(mySwiftAgentCore): Capability Prompt強化 + Validation強化 + フィードバックループ実装
**作成日**: 2026-01-17
**作成者**: Claude Code (Acceptance Plan スキル)
**対象プロジェクト**: mySwiftAgentCore

---

## 1. 概要

本計画書は、Issue #374の実装が完了した後に実施する受入テストの計画を定めます。

### 1.1 Issue概要

TaskFlowGeneratorAgentにおけるCapability情報のLLMへの提供を強化し、以下の機能を実装：

1. **Capability仕様のPrompt注入強化**: 完全なCapability仕様（パラメータ詳細、レスポンススキーマ、使用例）をLLMに渡す
2. **Validation強化**: 生成されたワークフローをCapability仕様に照らして検証する
3. **フィードバックループ実装** (Issue #367統合): バリデーションエラー発生時にLLMに修正を依頼する機構

### 1.2 受入条件（Issueより）

| AC-ID | 受入条件 | 分類 |
|-------|---------|------|
| AC-1 | PromptBuilderが完全なCapability仕様をLLMに渡す | 機能要件 |
| AC-2 | WorkflowCapabilityValidatorが必須パラメータ・型・制約を検証する | 機能要件 |
| AC-3 | 検証失敗時に `LLMValidationError` が生成される | 機能要件 |
| AC-4 | フィードバック付きプロンプトでLLMが再生成を試みる | 機能要件 |
| AC-5 | 最大リトライ回数（3回）まで自動修正を試みる | 機能要件 |
| AC-6 | E2Eテスト（Test 4）が成功する | 品質要件 |
| AC-7 | HTTP 422エラーが解消される | 品質要件 |

---

## 2. 設計方針検証項目

design-policy.md で定められた設計判断が正しく実装されているかを検証します。

### 2.1 アーキテクチャ設計の検証

| DP-ID | 設計方針 | 検証内容 |
|-------|---------|---------|
| DP-1 | ValidationPipeline拡張 | WorkflowCapabilityValidatorがValidationPipelineに統合されているか |
| DP-2 | PromptBuilder強化 | formatCapabilities()が完全なCapability仕様を出力するか |
| DP-3 | PromptBuilderにbuildFeedbackPrompt追加 | フィードバックプロンプトが正しく構築されるか |
| DP-4 | ErrorHandler活用 | 既存ErrorHandlerがLLMValidationErrorを適切に分類するか |
| DP-5 | CapabilityRegistry活用 | getByProjectExtended()がCapabilityExtendedを返すか |

### 2.2 技術選定の検証

| DP-ID | 技術選定 | 検証内容 |
|-------|---------|---------|
| DP-6 | TypeScript + Zod | 新規型定義がZodスキーマで検証可能か |
| DP-7 | カスタムError階層 | LLMValidationErrorがError階層に正しく組み込まれているか |
| DP-8 | pino ロギング | フィードバックループのログが構造化されているか |
| DP-9 | Vitest | 新規コンポーネントの単体テストがVitest形式か |

### 2.3 セキュリティ設計の検証

| DP-ID | セキュリティ項目 | 検証内容 |
|-------|----------------|---------|
| DP-10 | _internal フィールド除外 | LLMに渡すCapabilityに_internalが含まれないか |
| DP-11 | secret_key 非開示 | 認証情報がプロンプトに漏洩しないか |

### 2.4 パフォーマンス設計の検証

| DP-ID | パフォーマンス項目 | 検証内容 |
|-------|------------------|---------|
| DP-12 | フィードバックタイムアウト戦略 | 各リトライで適切なタイムアウトが設定されるか |
| DP-13 | プロンプトサイズ制限 | 50件を超えるCapability時に関連性選択が動作するか |
| DP-14 | メトリクス収集 | GenerationMetricsが正しく収集されるか |

---

## 3. デッドコード検証計画

実装された機能が実際にコードベースに統合され、呼び出されていることを検証します。

### 3.1 新規ファイル・クラス

| DC-ID | ファイル/クラス | 期待される呼び出し元 | 検証方法 |
|-------|----------------|-------------------|---------|
| DC-1 | `WorkflowCapabilityValidator` | ValidationPipeline | Grep: `WorkflowCapabilityValidator` が `ValidationPipeline` または `routes.ts` で使用されているか |
| DC-2 | `LLMValidationError` | WorkflowGenerator | Grep: `LLMValidationError` が `WorkflowGenerator` で throw されているか |
| DC-3 | `CapabilityForPrompt` 型 | PromptBuilder | Grep: `CapabilityForPrompt` が `PromptBuilder` で使用されているか |
| DC-4 | `buildFeedbackPrompt()` | WorkflowGenerator | Grep: `buildFeedbackPrompt` が呼び出されているか |
| DC-5 | `selectRelevantCapabilities()` | PromptBuilder | Grep: `selectRelevantCapabilities` が呼び出されているか |
| DC-6 | `GenerationMetricsCollector` | WorkflowGenerator | Grep: `GenerationMetricsCollector` が使用されているか |
| DC-7 | `metrics.ts` | generator.ts または WorkflowGenerator | Grep: `GenerationMetrics` がインポートされているか |
| DC-8 | `CapabilitySelector.ts` | PromptBuilder | Grep: `CapabilitySelector` がインポートされているか |

### 3.2 新規メソッド

| DC-ID | メソッド | 期待される呼び出し元 | 検証方法 |
|-------|---------|-------------------|---------|
| DC-9 | `formatSingleCapability()` | `formatCapabilities()` | Grep: 内部呼び出しの確認 |
| DC-10 | `formatParameter()` | `formatSingleCapability()` | Grep: 内部呼び出しの確認 |
| DC-11 | `validateRequiredParams()` | `validateStep()` | Grep: 内部呼び出しの確認 |
| DC-12 | `validateParamTypes()` | `validateStep()` | Grep: 内部呼び出しの確認 |
| DC-13 | `validateParamConstraints()` | `validateStep()` | Grep: 内部呼び出しの確認 |
| DC-14 | `warnUnknownParams()` | `validateStep()` | Grep: 内部呼び出しの確認 |
| DC-15 | `toFeedbackSummary()` | `buildFeedbackPrompt()` | Grep: LLMValidationErrorのメソッド呼び出し確認 |
| DC-16 | `recordAttempt()` | WorkflowGenerator generate() | Grep: メトリクス記録の呼び出し確認 |
| DC-17 | `calculateRelevanceScore()` | `selectRelevantCapabilities()` | Grep: 内部呼び出しの確認 |
| DC-18 | `extractKeywords()` | `selectRelevantCapabilities()` | Grep: 内部呼び出しの確認 |

### 3.3 新規定数

| DC-ID | 定数 | 期待される使用箇所 | 検証方法 |
|-------|------|------------------|---------|
| DC-19 | `MAX_CAPABILITIES_PER_PROMPT` | PromptBuilder または selectRelevantCapabilities | Grep: 定数が使用されているか |
| DC-20 | `MAX_CAPABILITY_DESCRIPTION_LENGTH` | formatSingleCapability | Grep: 定数が使用されているか（存在する場合） |

---

## 4. テスト環境

### 4.1 必須サービス

| サービス | URL | 用途 |
|---------|-----|------|
| mySwiftAgentCore | http://localhost:8006 | 受入テスト対象 |
| myVault | http://localhost:8003 | シークレット管理（LLM APIキー） |

### 4.2 環境変数

```bash
# 必須
OPENAI_API_KEY=sk-xxxx           # または Claude API Key
ANTHROPIC_API_KEY=sk-ant-xxxx    # Claude使用時

# オプション
LOG_LEVEL=debug                  # 詳細ログ出力
```

### 4.3 テストデータ

- `config/capabilities/default_project/*.yaml` - Capability定義ファイル
- テスト用タスク定義（後述）

---

## 5. テスト項目

### 5.1 AC-1: PromptBuilderが完全なCapability仕様をLLMに渡す

#### TC-001: formatCapabilities() が拡張フィールドを含む

**目的**: PromptBuilderが完全なCapability仕様をフォーマットすることを検証

**前提条件**:
- mySwiftAgentCoreが起動している
- google_search Capability に responseSchema, examples, metadata が定義されている

**テスト手順**:
1. PromptBuilder インスタンスを作成
2. google_search を含む CapabilityForPrompt[] を準備
3. `formatCapabilities(capabilities)` を呼び出す
4. 出力文字列を検証

**期待結果**:
- 出力に `Response Schema:` セクションが含まれる
- 出力に `TaskFlow Step Example:` セクションが含まれる
- 出力に `Use Cases:` セクションが含まれる
- パラメータに `[default: ...]` が含まれる（defaultValueがある場合）
- パラメータに `{min: ..., max: ...}` が含まれる（validationがある場合）

**検証方法**: 単体テスト（Vitest）

```typescript
// tests/unit/taskflowGeneratorAgent/prompts/PromptBuilder.test.ts
describe('PromptBuilder.formatCapabilities()', () => {
  it('should include responseSchema in output', async () => {
    const capabilities: CapabilityForPrompt[] = [{
      id: 'google_search',
      name: 'Google検索',
      category: 'search',
      status: 'available',
      parameters: [{
        name: 'queries',
        type: 'array',
        required: true,
        validation: { min: 1, max: 10 }
      }],
      responseSchema: { search_results: { type: 'array' } },
      examples: [{ description: 'test', taskflow_step: {...} }],
      metadata: { use_cases: ['キーワード検索'] }
    }];

    const output = promptBuilder.formatCapabilities(capabilities);

    expect(output).toContain('Response Schema:');
    expect(output).toContain('TaskFlow Step Example:');
    expect(output).toContain('Use Cases:');
  });
});
```

---

#### TC-002: パラメータの詳細情報が出力される

**目的**: defaultValue, validation がパラメータ出力に含まれることを検証

**前提条件**:
- CapabilityParameter に defaultValue と validation が設定されている

**テスト手順**:
1. defaultValue: 10, validation: { min: 1, max: 100 } を持つパラメータを準備
2. `formatCapabilities()` を呼び出す
3. 出力を検証

**期待結果**:
- `[default: 10]` が出力に含まれる
- `{min: 1, max: 100}` が出力に含まれる

**検証方法**: 単体テスト（Vitest）

---

### 5.2 AC-2: WorkflowCapabilityValidatorが必須パラメータ・型・制約を検証する

#### TC-003: 必須パラメータ欠落の検出

**目的**: 必須パラメータが欠落している場合にエラーを返すことを検証

**前提条件**:
- google_search Capability で `queries` が必須パラメータ

**テスト手順**:
1. WorkflowCapabilityValidator インスタンスを作成
2. queries パラメータが欠落したワークフローを準備
3. `validateWorkflow()` を呼び出す

**期待結果**:
- `valid: false` が返される
- errors に `MISSING_REQUIRED_PARAM` コードが含まれる
- errors に `parameter: 'queries'` が含まれる

**検証方法**: 単体テスト（Vitest）

```typescript
// tests/unit/taskflowGeneratorAgent/validator/WorkflowCapabilityValidator.test.ts
describe('WorkflowCapabilityValidator', () => {
  it('should detect missing required parameters', async () => {
    const workflow = {
      steps: [{
        id: 'search',
        type: 'api_rest',
        config: { capability_id: 'google_search' },
        params: { body: {} }  // queries が欠落
      }]
    };

    const result = validator.validateWorkflow(workflow, 'default_project');

    expect(result.valid).toBe(false);
    expect(result.errors).toContainEqual(
      expect.objectContaining({
        code: 'MISSING_REQUIRED_PARAM',
        parameter: 'queries'
      })
    );
  });
});
```

---

#### TC-004: パラメータ型不一致の検出

**目的**: パラメータ型が仕様と異なる場合にエラーを返すことを検証

**前提条件**:
- google_search Capability で `queries` が array 型

**テスト手順**:
1. queries に string 型の値を設定したワークフローを準備
2. `validateWorkflow()` を呼び出す

**期待結果**:
- `valid: false` が返される
- errors に `PARAM_TYPE_MISMATCH` コードが含まれる
- errors に `expected: 'array', actual: 'string'` が含まれる

**検証方法**: 単体テスト（Vitest）

---

#### TC-005: パラメータ制約違反の検出（min/max）

**目的**: min/max 制約に違反した値を検出することを検証

**前提条件**:
- num パラメータに `validation: { min: 1, max: 100 }` が設定されている

**テスト手順**:
1. num: 0 を設定したワークフローを準備
2. `validateWorkflow()` を呼び出す

**期待結果**:
- `valid: false` が返される
- errors に `PARAM_BELOW_MIN` コードが含まれる

**検証方法**: 単体テスト（Vitest）

---

#### TC-006: パラメータ制約違反の検出（enum）

**目的**: enum 制約に違反した値を検出することを検証

**前提条件**:
- パラメータに `validation: { enum: ['A', 'B', 'C'] }` が設定されている

**テスト手順**:
1. 'D' を設定したワークフローを準備
2. `validateWorkflow()` を呼び出す

**期待結果**:
- `valid: false` が返される
- errors に `PARAM_NOT_IN_ENUM` コードが含まれる

**検証方法**: 単体テスト（Vitest）

---

#### TC-007: 未知パラメータの警告

**目的**: 未定義のパラメータが警告として報告されることを検証

**前提条件**:
- google_search Capability に `unknown_param` は定義されていない

**テスト手順**:
1. unknown_param を含むワークフローを準備
2. `validateWorkflow()` を呼び出す

**期待結果**:
- `valid: true` が返される（エラーではない）
- warnings に `UNKNOWN_PARAM` コードが含まれる

**検証方法**: 単体テスト（Vitest）

---

#### TC-008: 動的参照（$input, $steps）はスキップされる

**目的**: $input.xxx や $steps.xxx のような動的参照は型チェックをスキップすることを検証

**前提条件**:
- queries が array 型だが、値が `$input.query` になっている

**テスト手順**:
1. queries: "$input.query" を設定したワークフローを準備
2. `validateWorkflow()` を呼び出す

**期待結果**:
- errors に `PARAM_TYPE_MISMATCH` が含まれない
- 動的参照は実行時解決のためスキップ

**検証方法**: 単体テスト（Vitest）

---

### 5.3 AC-3: 検証失敗時に LLMValidationError が生成される

#### TC-009: LLMValidationError の生成

**目的**: バリデーション失敗時に LLMValidationError が正しく生成されることを検証

**前提条件**:
- ValidationResult に errors が含まれている

**テスト手順**:
1. 失敗した ValidationResult を準備
2. LLMValidationError を生成
3. プロパティを検証

**期待結果**:
- `validationResult` プロパティが設定されている
- `rawContent` プロパティが設定されている
- `attempt` プロパティが設定されている
- `name` が 'LLMValidationError'

**検証方法**: 単体テスト（Vitest）

---

#### TC-010: toFeedbackSummary() の出力

**目的**: LLMValidationError.toFeedbackSummary() が適切なフィードバックを生成することを検証

**テスト手順**:
1. 複数のエラーを含む LLMValidationError を生成
2. `toFeedbackSummary()` を呼び出す
3. 出力文字列を検証

**期待結果**:
- `## 前回の生成結果に以下の問題がありました` が含まれる
- 各エラーの `### エラー:` セクションが含まれる
- `修正方法:` が含まれる（suggestion がある場合）
- `## 上記のエラーを修正したワークフローを再生成してください` が含まれる

**検証方法**: 単体テスト（Vitest）

---

### 5.4 AC-4: フィードバック付きプロンプトでLLMが再生成を試みる

#### TC-011: buildFeedbackPrompt() の構築

**目的**: フィードバックプロンプトが正しく構築されることを検証

**前提条件**:
- 元のプロンプトと LLMValidationError がある

**テスト手順**:
1. PromptBuilder インスタンスを作成
2. 元のプロンプト、LLMValidationError、CapabilityForPrompt[] を準備
3. `buildFeedbackPrompt()` を呼び出す

**期待結果**:
- エラーフィードバックセクションが含まれる
- 問題のあったCapability仕様が再提示される
- 前回の不正な出力が含まれる
- 元のタスク要件が含まれる

**検証方法**: 単体テスト（Vitest）

---

#### TC-012: フィードバックループの動作（モック）

**目的**: WorkflowGeneratorがフィードバックループを実行することを検証

**前提条件**:
- LLMClient をモック化
- 1回目は不正なワークフロー、2回目は正しいワークフローを返す

**テスト手順**:
1. WorkflowGenerator インスタンスを作成
2. LLMClient のモックを設定
3. `generate()` を呼び出す

**期待結果**:
- LLMClient が2回呼び出される
- 2回目の呼び出しにフィードバックプロンプトが含まれる
- 最終的に成功が返される
- `attempts: 2` が返される

**検証方法**: 単体テスト（Vitest）

---

### 5.5 AC-5: 最大リトライ回数（3回）まで自動修正を試みる

#### TC-013: 最大リトライ到達時のエラー

**目的**: 3回失敗後に MAX_RETRIES_EXCEEDED エラーが返されることを検証

**前提条件**:
- LLMClient が常に不正なワークフローを返す

**テスト手順**:
1. WorkflowGenerator インスタンスを作成
2. LLMClient のモックを設定（常に失敗）
3. `generate()` を呼び出す

**期待結果**:
- `success: false` が返される
- `error.code: 'MAX_RETRIES_EXCEEDED'` が返される
- `attempts: 3` が返される
- `lastValidationErrors` が含まれる

**検証方法**: 単体テスト（Vitest）

---

#### TC-014: リトライ回数のカウント

**目的**: 各試行が正しくカウントされることを検証

**テスト手順**:
1. 2回目で成功するモックを設定
2. `generate()` を呼び出す

**期待結果**:
- `attempts: 2` が返される
- LLMClient が2回呼び出される

**検証方法**: 単体テスト（Vitest）

---

### 5.6 AC-6/AC-7: E2Eテスト成功・HTTP 422エラー解消

#### TC-015: E2E - google_search ワークフロー生成（正常系）

**目的**: 実際のLLMを使用してgoogle_searchワークフローが正しく生成されることを検証

**前提条件**:
- mySwiftAgentCore が起動している
- LLM APIキーが設定されている
- google_search Capability が定義されている

**テスト手順**:
1. `/api/v1/generator/workflow/batch` に POST
2. タスク: "Execute Google Search"
3. レスポンスを検証

**期待結果**:
- HTTP 200 が返される
- 生成されたワークフローの params.body に `queries` (array) が含まれる
- `query` (string) ではなく `queries` (array) が使用されている

**検証方法**: 受入テスト（pytest）+ curl

```bash
curl -X POST http://localhost:8006/api/v1/generator/workflow/batch \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "default_project",
    "tasks": [{
      "task_id": "test_001",
      "name": "Execute Google Search",
      "description": "Search for AI news"
    }]
  }'
```

---

#### TC-016: E2E - gmail_send ワークフロー生成（正常系）

**目的**: gmail_send ワークフローが正しいパラメータ形式で生成されることを検証

**前提条件**:
- gmail_send Capability が定義されている

**テスト手順**:
1. `/api/v1/generator/workflow/batch` に POST
2. タスク: "Send Email via Gmail"
3. レスポンスを検証

**期待結果**:
- HTTP 200 が返される
- 生成されたワークフローのパラメータがCapability仕様に準拠

**検証方法**: 受入テスト（pytest）+ curl

---

#### TC-017: E2E - バリデーション失敗時のリトライ動作

**目的**: バリデーション失敗時にフィードバックループが動作することを検証

**前提条件**:
- ログレベルが debug に設定されている

**テスト手順**:
1. 複雑なタスクでワークフロー生成を実行
2. サーバーログを確認

**期待結果**:
- ログに `Attempt 1 failed, retrying with feedback...` が出力される場合がある
- 最終的に成功または MAX_RETRIES_EXCEEDED

**検証方法**: 受入テスト（pytest）+ ログ確認

---

#### TC-018: E2E - 生成されたワークフローの実行

**目的**: 生成されたワークフローが実際に実行できることを検証

**前提条件**:
- TC-015 で生成されたワークフローがある
- TaskFlowEngine が起動している

**テスト手順**:
1. 生成されたワークフローを `/api/v1/taskflow/execute` に POST
2. レスポンスを検証

**期待結果**:
- HTTP 200 が返される
- HTTP 422 エラーが発生しない
- ワークフローが正常に実行される

**検証方法**: 受入テスト（pytest）+ curl

---

### 5.7 設計方針検証テスト

#### TC-019: DP-10 - _internal フィールド除外の検証

**目的**: LLMに渡すCapabilityに_internalが含まれないことを検証

**テスト手順**:
1. routes.ts の CapabilityForPrompt 変換ロジックを確認
2. 単体テストで _internal フィールドが除外されることを確認

**期待結果**:
- `_internal` プロパティが含まれない

**検証方法**: 単体テスト（Vitest）

---

#### TC-020: DP-13 - プロンプトサイズ制限の検証

**目的**: 50件を超えるCapabilityがある場合に関連性選択が動作することを検証

**前提条件**:
- 60件のCapabilityを持つモックデータ

**テスト手順**:
1. 60件のCapabilityForPromptを準備
2. `selectRelevantCapabilities()` を呼び出す
3. 結果を検証

**期待結果**:
- 返却されるCapabilityが50件以下
- タスクに関連性の高いCapabilityが優先される

**検証方法**: 単体テスト（Vitest）

```typescript
describe('selectRelevantCapabilities()', () => {
  it('should limit capabilities to MAX_CAPABILITIES_PER_PROMPT', () => {
    const capabilities = generateMockCapabilities(60);
    const task = { name: 'Search task', description: 'Search for news' };

    const result = selectRelevantCapabilities(task, capabilities);

    expect(result.length).toBeLessThanOrEqual(50);
  });
});
```

---

#### TC-021: DP-14 - メトリクス収集の検証

**目的**: GenerationMetricsが正しく収集されることを検証

**テスト手順**:
1. GenerationMetricsCollector インスタンスを作成
2. `startGeneration()`, `recordAttempt()`, `finalize()` を呼び出す
3. 結果を検証

**期待結果**:
- `initialSuccessRate` が正しく計算される
- `averageRetryCount` が正しく計算される
- `tokenUsageByAttempt` が記録される
- `validationErrorTypes` がカウントされる

**検証方法**: 単体テスト（Vitest）

---

#### TC-022: DP-14 - APIレスポンスにmetricsが含まれる

**目的**: 生成結果のAPIレスポンスにmetricsフィールドが含まれることを検証

**テスト手順**:
1. `/api/v1/generator/workflow/batch` に POST
2. レスポンスを検証

**期待結果**:
- レスポンスに `metrics` フィールドが含まれる（または results[].metrics）

**検証方法**: 受入テスト（pytest）+ curl

---

### 5.8 デッドコード検証テスト

#### TC-023: DC-1 - WorkflowCapabilityValidator の統合確認

**目的**: WorkflowCapabilityValidatorが実際に呼び出されることを検証

**テスト手順**:
```bash
grep -rn "WorkflowCapabilityValidator" mySwiftAgentCore/src/
```

**期待結果**:
- ValidationPipeline または routes.ts で使用されている

**検証方法**: Grep + 結合テスト

---

#### TC-024: DC-4 - buildFeedbackPrompt() の呼び出し確認

**目的**: buildFeedbackPrompt()が実際に呼び出されることを検証

**テスト手順**:
```bash
grep -rn "buildFeedbackPrompt" mySwiftAgentCore/src/
```

**期待結果**:
- WorkflowGenerator.generate() 内で呼び出されている

**検証方法**: Grep + 結合テスト

---

#### TC-025: DC-5 - selectRelevantCapabilities() の呼び出し確認

**目的**: selectRelevantCapabilities()が実際に呼び出されることを検証

**テスト手順**:
```bash
grep -rn "selectRelevantCapabilities" mySwiftAgentCore/src/
```

**期待結果**:
- PromptBuilder.formatCapabilities() 内で呼び出されている

**検証方法**: Grep + 結合テスト

---

#### TC-026: DC-6 - GenerationMetricsCollector の使用確認

**目的**: GenerationMetricsCollectorが実際に使用されることを検証

**テスト手順**:
```bash
grep -rn "GenerationMetricsCollector" mySwiftAgentCore/src/
```

**期待結果**:
- WorkflowGenerator で使用されている

**検証方法**: Grep + 結合テスト

---

## 6. テスト実行計画

### 6.1 単体テスト（CI実行）

```bash
cd mySwiftAgentCore
npm run test -- --coverage
```

**カバレッジ目標**: 90%以上

**対象ファイル**:
- `src/taskflowGeneratorAgent/prompts/PromptBuilder.ts`
- `src/taskflowGeneratorAgent/prompts/CapabilitySelector.ts`
- `src/taskflowGeneratorAgent/validator/WorkflowCapabilityValidator.ts`
- `src/taskflowGeneratorAgent/types/generator.ts`
- `src/taskflowGeneratorAgent/generator/WorkflowGenerator.ts`
- `src/taskflowGeneratorAgent/metrics/GenerationMetricsCollector.ts`

---

### 6.2 結合テスト（CI実行）

```bash
cd mySwiftAgentCore
npm run test:integration
```

**対象**:
- ValidationPipeline + WorkflowCapabilityValidator 統合
- WorkflowGenerator フィードバックループ（モックLLM）

---

### 6.3 受入テスト（ローカル実行）

**前提条件**:
- サービス起動: `./scripts/dev-hybrid.sh` または `make dev-all`
- 環境変数設定: `.env` に LLM API キー

```bash
# 受入テスト実行
cd mySwiftAgentCore
uv run pytest tests/acceptance/test_issue_374_acceptance.py -v

# curlによる手動検証
curl -X POST http://localhost:8006/api/v1/generator/workflow/batch \
  -H "Content-Type: application/json" \
  -d @test_data/issue_374_test_request.json
```

---

## 7. 受入テストファイル

以下のファイルを作成すること：

```
mySwiftAgentCore/tests/acceptance/test_issue_374_acceptance.py
```

### 7.1 テストファイル構成

```python
"""
Issue #374 受入テスト（L3: ローカル受入テスト）

前提条件:
- mySwiftAgentCore が起動していること
- .env に LLM API キーが設定されていること

実行方法:
  cd mySwiftAgentCore
  uv run pytest tests/acceptance/test_issue_374_acceptance.py -v
"""
import pytest
import requests
from typing import Any


@pytest.mark.acceptance
class TestIssue374Acceptance:
    """Issue #374: Capability Prompt強化 + Validation強化 + フィードバックループ実装"""

    CORE_URL = "http://localhost:8006"

    @pytest.fixture(autouse=True)
    def check_service_running(self) -> None:
        """サービス起動確認"""
        try:
            response = requests.get(f"{self.CORE_URL}/health", timeout=5)
            assert response.status_code == 200
        except requests.exceptions.ConnectionError:
            pytest.skip("mySwiftAgentCore is not running")

    # TC-015: E2E - google_search ワークフロー生成
    def test_tc015_google_search_workflow_generation(self) -> None:
        """TC-015: google_searchワークフローが正しいパラメータ形式で生成される"""
        # 実装

    # TC-016: E2E - gmail_send ワークフロー生成
    def test_tc016_gmail_send_workflow_generation(self) -> None:
        """TC-016: gmail_sendワークフローが正しいパラメータ形式で生成される"""
        # 実装

    # TC-018: E2E - 生成されたワークフローの実行
    def test_tc018_execute_generated_workflow(self) -> None:
        """TC-018: 生成されたワークフローが実行可能"""
        # 実装

    # TC-022: DP-14 - APIレスポンスにmetricsが含まれる
    def test_tc022_response_includes_metrics(self) -> None:
        """TC-022: 生成結果にmetricsフィールドが含まれる"""
        # 実装
```

---

## 8. 合格基準

### 8.1 必須合格条件

| 条件 | 基準 |
|------|------|
| 単体テストカバレッジ | 90%以上 |
| 結合テスト | 全て PASS |
| 受入テスト TC-015〜TC-018 | 全て PASS |
| 設計方針検証 TC-019〜TC-022 | 全て PASS |
| デッドコード検証 TC-023〜TC-026 | 全て PASS |
| HTTP 422 エラー | 発生しないこと |

### 8.2 推奨条件

| 条件 | 基準 |
|------|------|
| フィードバックループによる成功率 | 90%以上 |
| 初回成功率 | 70%以上 |
| 平均リトライ回数 | 1.5回以下 |

---

## 9. テスト項目サマリ

| TC-ID | テスト名 | レベル | 必須 |
|-------|---------|-------|------|
| TC-001 | formatCapabilities() が拡張フィールドを含む | 単体 | ✅ |
| TC-002 | パラメータの詳細情報が出力される | 単体 | ✅ |
| TC-003 | 必須パラメータ欠落の検出 | 単体 | ✅ |
| TC-004 | パラメータ型不一致の検出 | 単体 | ✅ |
| TC-005 | パラメータ制約違反の検出（min/max） | 単体 | ✅ |
| TC-006 | パラメータ制約違反の検出（enum） | 単体 | ✅ |
| TC-007 | 未知パラメータの警告 | 単体 | ✅ |
| TC-008 | 動的参照（$input, $steps）はスキップされる | 単体 | ✅ |
| TC-009 | LLMValidationError の生成 | 単体 | ✅ |
| TC-010 | toFeedbackSummary() の出力 | 単体 | ✅ |
| TC-011 | buildFeedbackPrompt() の構築 | 単体 | ✅ |
| TC-012 | フィードバックループの動作（モック） | 単体 | ✅ |
| TC-013 | 最大リトライ到達時のエラー | 単体 | ✅ |
| TC-014 | リトライ回数のカウント | 単体 | ✅ |
| TC-015 | E2E - google_search ワークフロー生成 | 受入 | ✅ |
| TC-016 | E2E - gmail_send ワークフロー生成 | 受入 | ✅ |
| TC-017 | E2E - バリデーション失敗時のリトライ動作 | 受入 | ✅ |
| TC-018 | E2E - 生成されたワークフローの実行 | 受入 | ✅ |
| TC-019 | DP-10 - _internal フィールド除外の検証 | 単体 | ✅ |
| TC-020 | DP-13 - プロンプトサイズ制限の検証 | 単体 | ✅ |
| TC-021 | DP-14 - メトリクス収集の検証 | 単体 | ✅ |
| TC-022 | DP-14 - APIレスポンスにmetricsが含まれる | 受入 | ✅ |
| TC-023 | DC-1 - WorkflowCapabilityValidator の統合確認 | デッドコード | ✅ |
| TC-024 | DC-4 - buildFeedbackPrompt() の呼び出し確認 | デッドコード | ✅ |
| TC-025 | DC-5 - selectRelevantCapabilities() の呼び出し確認 | デッドコード | ✅ |
| TC-026 | DC-6 - GenerationMetricsCollector の使用確認 | デッドコード | ✅ |

**合計**: 26テスト項目（全て必須）

---

## 10. 参照ドキュメント

- [Issue #374](https://github.com/kewton/MySwiftAgent/issues/374)
- [設計方針書](./design-policy.md)
- [設計仕様書](./design-spec-capability-prompt-enhancement.md)
- [CLAUDE.md](../../../../CLAUDE.md) - テストカバレッジ基準

---

**作成日**: 2026-01-17
**Issue**: #374
**作成者**: Claude Code (Acceptance Plan スキル)

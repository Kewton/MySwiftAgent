# NodeExecutionContext 設計仕様書

## 概要

本ドキュメントは、mySwiftAgentCoreの`taskflowEngine`におけるNodeExecutionContextインターフェースの設計仕様を定義します。ノード開発者がこのドキュメントを参照することで、ワークフロー実行時のコンテキストを正しく利用できるようになることを目的としています。

## 背景

Issue #375のタスクチェーン動作確認中に、以下の問題が発生しました：

- TransformNodeがcontextを使用せず、input/stepsにアクセスできなかった
- LlmNodeがstepResultsをテンプレート展開に含めていなかった
- オブジェクト/配列のString変換が適切に行われていなかった

**真因**: NodeExecutionContextの各フィールドの責務と使用パターンが明文化されておらず、ノード開発時に見落とされた。

---

## NodeExecutionContextインターフェース

### インターフェース定義

```typescript
export interface NodeExecutionContext {
  workflowId: string;                      // ワークフローの一意識別子
  stepResults: Record<string, unknown>;    // 前ステップの実行結果
  variables: Record<string, unknown>;      // ランタイム変数（inputを含む）
  secrets: Record<string, string>;         // シークレット情報
  timeout?: number;                        // タイムアウト（ミリ秒）
  capabilityExecutor?: ICapabilityExecutor; // Capability実行用インターフェース
}
```

**ソースコード**: [BaseNode.ts:48](../../mySwiftAgentCore/src/taskflowEngine/nodes/BaseNode.ts)

---

## フィールド詳細

### 1. workflowId

| 項目 | 値 |
|------|-----|
| **型** | `string` |
| **必須** | Yes |
| **責務** | 実行中のワークフローインスタンスの一意識別 |
| **生成タイミング** | WorkflowExecutor初期化時 |

**使用例**:
```typescript
// ログ出力でワークフローを特定
console.log(`Executing workflow: ${context.workflowId}`);
```

---

### 2. stepResults

| 項目 | 値 |
|------|-----|
| **型** | `Record<string, unknown>` |
| **必須** | Yes（初期値は空オブジェクト） |
| **責務** | 実行済みステップの出力結果を保持 |
| **更新タイミング** | 各ステップ実行完了時 |

**データ構造**:
```typescript
{
  "step1": { "data": "result1", "status": "success" },
  "step2": { "value": 123, "items": ["a", "b", "c"] }
}
```

**アクセス方法**:

| 方法 | パターン | 例 |
|------|---------|-----|
| テンプレート | `{{steps.stepId.field}}` | `{{steps.step1.data}}` |
| コード | `context.stepResults['stepId']` | `context.stepResults['step1']` |

**使用例**:
```typescript
// 前のステップの結果を取得
const previousResult = context.stepResults['fetchData'];
if (previousResult) {
  const data = previousResult as { items: string[] };
  console.log(`Received ${data.items.length} items`);
}
```

---

### 3. variables

| 項目 | 値 |
|------|-----|
| **型** | `Record<string, unknown>` |
| **必須** | Yes |
| **責務** | ワークフロー実行時の変数保持 |
| **初期化** | ExecutionOptions.variablesから設定 |

**必須フィールド**:
```typescript
{
  "input": unknown  // ワークフロー入力データ（必須）
  // その他のカスタム変数
}
```

**アクセス方法**:

| 方法 | パターン | 例 |
|------|---------|-----|
| テンプレート | `{{input.field}}` | `{{input.name}}` |
| JSONPath形式 | `$.input.field` | `$.input.name` |
| コード | `context.variables['input']` | `context.variables['input']` |

**使用例**:
```typescript
// ワークフロー入力を取得
const input = context.variables['input'] as { query: string };
console.log(`Processing query: ${input.query}`);
```

---

### 4. secrets

| 項目 | 値 |
|------|-----|
| **型** | `Record<string, string>` |
| **必須** | Yes（初期値は空オブジェクト） |
| **責務** | APIキー、認証トークン等の機密情報保持 |

**命名規則**:
- OpenAI API: `OPENAI_API_KEY`
- 汎用LLM: `LLM_API_KEY`
- カスタム: `{SERVICE}_API_KEY`

**セキュリティ要件**:
- ログ出力禁止
- メモリ内保持のみ（永続化禁止）
- ノード実行時のみ参照可能

**使用例**:
```typescript
// APIキーの取得と検証
const apiKey = context.secrets['OPENAI_API_KEY'];
if (!apiKey) {
  throw new Error('Required secret OPENAI_API_KEY not found');
}

// リクエストヘッダーに設定
const headers = {
  'Authorization': `Bearer ${apiKey}`,
  'Content-Type': 'application/json'
};
```

---

### 5. timeout

| 項目 | 値 |
|------|-----|
| **型** | `number \| undefined` |
| **必須** | No |
| **責務** | ステップ実行のタイムアウト制御（ミリ秒） |
| **適用対象** | API呼び出し、コード実行等 |

**優先順位**:
1. ステップ定義のtimeout
2. Capability定義の`_internal.timeout_ms`
3. デフォルト値（30000ms）

**使用例**:
```typescript
// タイムアウト値の決定
const timeout =
  config.timeout ??                    // 1. ステップ定義
  capability?._internal?.timeout_ms ?? // 2. Capability定義
  30000;                               // 3. デフォルト

// fetchで使用
const controller = new AbortController();
setTimeout(() => controller.abort(), timeout);
```

---

### 6. capabilityExecutor

| 項目 | 値 |
|------|-----|
| **型** | `ICapabilityExecutor \| undefined` |
| **必須** | No（Issue #372で追加） |
| **責務** | capability_idベースのAPI実行 |

**インターフェース定義**:
```typescript
interface ICapabilityExecutor {
  resolveCapability(capabilityId: string): Promise<ICapability | null>;
  executeCapability(
    capability: ICapability,
    params: Record<string, unknown>,
    context: NodeExecutionContext
  ): Promise<unknown>;
}
```

**使用例**:
```typescript
// Capability経由でAPI実行
if (context.capabilityExecutor && config.config.capability_id) {
  const capability = await context.capabilityExecutor.resolveCapability(
    config.config.capability_id
  );
  if (capability) {
    const result = await context.capabilityExecutor.executeCapability(
      capability,
      params,
      context
    );
    return { success: true, output: result };
  }
}
```

---

## テンプレート構文

### サポートする参照形式

| パターン | 例 | 説明 | 使用場所 |
|---------|-----|------|---------|
| `{{input.field}}` | `{{input.name}}` | 入力フィールド参照 | テンプレート |
| `{{steps.stepId.field}}` | `{{steps.step1.data}}` | ステップ結果参照 | テンプレート |
| `$.input.field` | `$.input.name` | JSONPath形式入力参照 | 設定ファイル |
| `${stepId.field}` | `${step1.data}` | ContextManager参照 | 内部処理 |
| `${steps.stepId.field}` | `${steps.step1.data}` | GraphAI互換形式 | ワークフロー定義 |

### Handlebars形式（推奨）

テンプレート展開には`{{path}}`形式を使用します。

```typescript
// テンプレート: "Hello {{input.name}}, {{steps.step1.result}}"
template.replace(/\{\{([^}]+)\}\}/g, (_, path) => {
  const value = getNestedValue(templateContext, path.trim());
  if (value === undefined) return '';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
});
```

### Dollar形式（URL専用）

URL補間には`${key}`形式を使用します。

```typescript
// URL: "https://api.example.com/search?q=${query}"
url.replace(/\$\{(\w+)\}/g, (match, key) => {
  const value = params[key];
  return value !== undefined ? String(value) : match;
});
```

### 参照解決の優先順位

1. ステップ結果（stepResults）
2. 入力データ（variables.input）
3. カスタム変数（variables）
4. デフォルト値またはエラー

---

## ノード実装パターン

### 基本実装パターン

```typescript
import {
  NodeConfig,
  NodeExecutionContext,
  NodeExecutionResult,
  NodeExecutor,
  NodeValidationResult
} from './BaseNode';

export class MyNode implements NodeExecutor {
  async execute(
    config: NodeConfig,
    params: Record<string, unknown>,
    context: NodeExecutionContext
  ): Promise<NodeExecutionResult> {
    try {
      // 1. コンテキストからの情報取得
      const input = context.variables['input'] ?? {};
      const previousResults = context.stepResults;

      // 2. テンプレート展開用コンテキスト構築【重要】
      const templateContext = {
        ...params,
        input,               // ← 必須: 入力データを含める
        steps: previousResults, // ← 必須: ステップ結果を含める
      };

      // 3. ビジネスロジック実行
      const result = await this.processLogic(templateContext);

      // 4. 結果返却
      return { success: true, output: result };
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      return {
        success: false,
        output: null,
        error: { code: 'EXECUTION_ERROR', message }
      };
    }
  }

  validate(config: NodeConfig): NodeValidationResult {
    // バリデーションロジック
    return { valid: true, errors: [] };
  }

  private async processLogic(context: Record<string, unknown>): Promise<unknown> {
    // 実際の処理ロジック
    return context;
  }
}
```

### 各ノードタイプの実装要件

| ノードタイプ | 必須コンテキスト利用 | テンプレート形式 | 特記事項 |
|------------|-------------------|----------------|---------|
| TransformNode | stepResults, variables | `{{path}}` | input/stepsを展開 |
| LlmNode | secrets, stepResults, variables | `{{path}}` | APIキー必須 |
| ApiRestNode | secrets, capabilityExecutor | `${key}` (URL) | capability優先 |
| CodeJsNode | 全フィールド | - | サンドボックス隔離 |
| ParallelNode | stepResults | - | 並列実行管理 |

---

## セキュリティ要件

### シークレット管理

| 要件 | 説明 |
|------|------|
| 保存場所 | メモリ内のみ（永続化禁止） |
| アクセス制御 | ノード実行時のみ参照可能 |
| ログ出力 | シークレット値のログ出力禁止 |
| 命名規則 | 大文字スネークケース必須 |

### コード実行セキュリティ

| 要件 | 説明 |
|------|------|
| サンドボックス | CodeJsNodeは隔離環境で実行 |
| タイムアウト | 必ず設定（デフォルト30秒） |
| リソース制限 | メモリ/CPU使用量の上限設定 |

---

## エラーハンドリング

### 必須エラーチェック

```typescript
// シークレット存在確認
if (!context.secrets['REQUIRED_KEY']) {
  throw new Error('Required secret REQUIRED_KEY not found');
}

// 必須ステップ結果確認
if (!context.stepResults['requiredStep']) {
  throw new Error('Required step "requiredStep" not executed');
}

// 入力データ確認
if (!context.variables['input']) {
  throw new Error('Input data is required');
}
```

### エラー伝播

- ノードエラーは`NodeExecutionResult`のerrorフィールドで返却
- WorkflowExecutorがエラーハンドリングとリトライを制御

---

## 実装チェックリスト

### ノード開発時の必須確認事項

- [ ] contextから`input`を取得しているか
- [ ] `stepResults`を参照する必要があるか確認
- [ ] 必要な`secrets`を取得しているか
- [ ] テンプレート展開で`input`/`steps`を含めているか
- [ ] タイムアウトを適切に設定しているか
- [ ] エラーハンドリングを実装しているか

### レビュー時の確認事項

- [ ] NodeExecutionContextの全必須フィールドを考慮しているか
- [ ] テンプレート展開パターンが正しいか
- [ ] セキュリティ要件を満たしているか
- [ ] 既存ノードとの一貫性があるか

---

## よくある間違いと対策

### 1. テンプレートコンテキストにinput/stepsを含めない

**問題**: テンプレート展開時に`{{input.xxx}}`や`{{steps.xxx}}`が解決されない

**対策**:
```typescript
// NG: paramsのみを使用
const result = this.expandTemplate(template, params);

// OK: input/stepsを含める
const templateContext = {
  ...params,
  input: context.variables['input'] ?? {},
  steps: context.stepResults,
};
const result = this.expandTemplate(template, templateContext);
```

### 2. オブジェクト/配列を文字列に変換しない

**問題**: テンプレート展開時にオブジェクトが`[object Object]`になる

**対策**:
```typescript
// テンプレート展開時にJSON.stringify()を使用
if (typeof value === 'object') {
  return JSON.stringify(value);
}
return String(value);
```

### 3. シークレットをログに出力する

**問題**: APIキーがログに出力され、セキュリティリスクになる

**対策**:
```typescript
// NG: シークレット値をログに出力
console.log(`Using API key: ${context.secrets['API_KEY']}`);

// OK: シークレットの存在確認のみログ出力
console.log(`API key present: ${!!context.secrets['API_KEY']}`);
```

### 4. ステップ結果の参照パスに.outputを含める（Issue #396）

**問題**: `${stepId.output.field}`のようにoutputを含めると、ステップ結果が解決されない

**原因**: WorkflowExecutorは`result.output`を直接stepResultsに保存するため、stepResults[stepId]は既にoutputオブジェクトそのものです。

```typescript
// WorkflowExecutor.tsでの保存方法
contextManager.setStepResult(step.id, result.output);

// stepResults['step1']の内容
{ "content": "...", "status": "success" }  // ✓ outputオブジェクトそのもの
```

**対策**:
```json
// NG: .outputを含める（解決されない）
"user_input": "${generate_email_content.output.content}"

// OK: 直接フィールドを参照
"user_input": "${generate_email_content.content}"

// OK: stepsプレフィックスを使用
"user_input": "${steps.generate_email_content.content}"
```

**正しいパス構文一覧**:

| パス | 解決先 | 用途 |
|-----|-------|------|
| `${stepId.field}` | `stepResults[stepId].field` | 短縮形式 |
| `${steps.stepId.field}` | `stepResults[stepId].field` | 明示的形式 |
| `${inputs.field}` | `variables['input'].field` | 入力参照 |

---

## 関連ドキュメント

- [BaseNode.ts](../../mySwiftAgentCore/src/taskflowEngine/nodes/BaseNode.ts) - インターフェース定義
- [ContextManager.ts](../../mySwiftAgentCore/src/taskflowEngine/executor/ContextManager.ts) - コンテキスト管理
- [WorkflowExecutor.ts](../../mySwiftAgentCore/src/taskflowEngine/executor/WorkflowExecutor.ts) - ワークフロー実行
- Issue #372: Capability実行機能追加
- Issue #375: コンテキスト利用の問題報告

---

*最終更新日: 2026-01-19*
*Issue: #376*

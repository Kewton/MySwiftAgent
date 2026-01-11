# 設計書: Conditional Step (if/else分岐) の実装

## 概要

V2 TaskFlow Engineに条件分岐機能 (`type: "conditional"`) を追加し、ワークフロー内でif/else分岐を実現する。

## 現状分析

### 現在のStep Types
```typescript
// workflow-schema.ts
export const NodeTypeSchema = z.enum(['api_rest', 'code_js', 'transform']);

export const StepSchema = z.union([SingleStepSchema, ParallelBlockSchema]);
// SingleStep: api_rest | code_js | transform
// ParallelBlock: { type: 'parallel', steps: [...] }
```

### 現在のExecutor構造（関数ベース）
```typescript
// workflow-executor.ts - 既存パターン
for (const step of workflow.executionPlan) {
  if (step.type === 'single') {
    await executeSequential(step.nodeIds, workflow.nodes, context);
  } else if (step.type === 'parallel') {
    await executeParallel(step.nodeIds, workflow.nodes, context);
  }
}
```

### 不足している機能
- 条件に基づく分岐実行
- 複数条件の評価（if/else if/else）
- 条件式の評価

## 設計案

### Option A: シンプルな2分岐 (推奨)

```json
{
  "type": "conditional",
  "condition": "${fetch_user.output.status} == 'active'",
  "then": [
    { "id": "process_active", "type": "api_rest", "config": {...} }
  ],
  "else": [
    { "id": "process_inactive", "type": "transform", "config": {...} }
  ]
}
```

### 推奨: Option A（シンプルな2分岐）

**理由:**
1. LLMが生成しやすいシンプルな構造
2. ネストで複数条件も表現可能
3. 実装が比較的容易

## 詳細設計

### 1. スキーマ定義 (workflow-schema.ts)

```typescript
/**
 * Condition expression - simple comparison syntax
 * セキュリティ: プリミティブ値のみ許可する厳格なパターン
 */
const ConditionExpressionSchema = z.string().refine(
  (expr) => {
    // 厳格なパターン: ${var.path} OPERATOR VALUE のみ許可
    // VALUE は: 文字列リテラル、数値、boolean、null のみ
    const pattern = /^\$\{[a-zA-Z_][a-zA-Z0-9_.]*\}\s*(==|!=|>|<|>=|<=)\s*('[^']*'|"[^"]*"|-?\d+(\.\d+)?|true|false|null)$/;
    return pattern.test(expr.trim());
  },
  { message: 'Invalid condition expression format. Use: ${var} == \'value\' or ${var} > 10' }
);

/** Conditional Block Schema */
export const ConditionalBlockSchema = z.object({
  type: z.literal('conditional'),
  condition: ConditionExpressionSchema,
  then: z.array(z.lazy(() => StepSchema)).min(1),
  else: z.array(z.lazy(() => StepSchema)).optional(),
});

/** Updated Step Schema */
export const StepSchema = z.union([
  SingleStepSchema,
  ParallelBlockSchema,
  ConditionalBlockSchema,  // 追加
]);
```

### 2. 条件式評価器 (condition-evaluator.ts) - セキュリティ強化版

```typescript
// src/engine/executor/condition-evaluator.ts

import type { ContextManager } from '../context/context-manager.js';

/**
 * 許可する比較演算子
 */
type ComparisonOperator = '==' | '!=' | '>' | '<' | '>=' | '<=';

/**
 * 許可するプリミティブ値の型
 */
type AllowedPrimitive = string | number | boolean | null;

/**
 * 条件式評価結果
 */
export interface ConditionEvaluationResult {
  result: boolean;
  evaluatedCondition: string;  // デバッグ用: 変数解決後の式
  error?: string;
}

/**
 * 条件式を安全に評価する
 *
 * セキュリティ対策:
 * 1. ホワイトリスト方式でプリミティブ値のみ許可
 * 2. eval/Function等の動的コード実行を使用しない
 * 3. JSON.parseを使用しない（任意オブジェクト生成防止）
 *
 * @param condition - 条件式 (e.g., "${user.output.status} == 'active'")
 * @param context - 実行コンテキスト
 * @returns 評価結果
 */
export function evaluateCondition(
  condition: string,
  context: ContextManager
): ConditionEvaluationResult {
  try {
    // 1. 条件式をパース
    const parsed = parseConditionExpression(condition);
    if (!parsed) {
      return {
        result: false,
        evaluatedCondition: condition,
        error: 'Invalid condition expression format',
      };
    }

    // 2. 変数を解決（プリミティブ値のみ取得）
    const leftValue = resolveVariableAsPrimitive(parsed.variable, context);
    const rightValue = parsed.value;

    // 3. 比較演算を実行
    const result = compareValues(leftValue, parsed.operator, rightValue);

    return {
      result,
      evaluatedCondition: `${JSON.stringify(leftValue)} ${parsed.operator} ${JSON.stringify(rightValue)}`,
    };
  } catch (error) {
    return {
      result: false,
      evaluatedCondition: condition,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

/**
 * 条件式をパースする
 */
interface ParsedCondition {
  variable: string;      // e.g., "user.output.status"
  operator: ComparisonOperator;
  value: AllowedPrimitive;
}

function parseConditionExpression(expr: string): ParsedCondition | null {
  const pattern = /^\$\{([a-zA-Z_][a-zA-Z0-9_.]*)\}\s*(==|!=|>|<|>=|<=)\s*(.+)$/;
  const match = expr.trim().match(pattern);

  if (!match) return null;

  const [, variable, operator, rawValue] = match;
  const value = parseAllowedValue(rawValue.trim());

  if (value === undefined) return null;

  return {
    variable,
    operator: operator as ComparisonOperator,
    value,
  };
}

/**
 * 許可された値のみをパースする（ホワイトリスト方式）
 *
 * 許可する値:
 * - 文字列リテラル: 'value' または "value"
 * - 数値: 123, -45.67
 * - boolean: true, false
 * - null
 */
function parseAllowedValue(rawValue: string): AllowedPrimitive | undefined {
  // 文字列リテラル (シングルクォート)
  if (rawValue.startsWith("'") && rawValue.endsWith("'")) {
    return rawValue.slice(1, -1);
  }

  // 文字列リテラル (ダブルクォート)
  if (rawValue.startsWith('"') && rawValue.endsWith('"')) {
    return rawValue.slice(1, -1);
  }

  // boolean
  if (rawValue === 'true') return true;
  if (rawValue === 'false') return false;

  // null
  if (rawValue === 'null') return null;

  // 数値 (整数または小数、負の値も許可)
  if (/^-?\d+(\.\d+)?$/.test(rawValue)) {
    return Number(rawValue);
  }

  // 許可されない値
  return undefined;
}

/**
 * 変数をプリミティブ値として解決する
 */
function resolveVariableAsPrimitive(
  variablePath: string,
  context: ContextManager
): AllowedPrimitive {
  const value = context.resolveVariable(`\${${variablePath}}`);

  // プリミティブ値のみ許可
  if (typeof value === 'string') return value;
  if (typeof value === 'number') return value;
  if (typeof value === 'boolean') return value;
  if (value === null) return null;

  // オブジェクト/配列は文字列化
  if (typeof value === 'object') {
    return JSON.stringify(value);
  }

  return String(value);
}

/**
 * 比較演算を実行する
 */
function compareValues(
  left: AllowedPrimitive,
  operator: ComparisonOperator,
  right: AllowedPrimitive
): boolean {
  switch (operator) {
    case '==':
      return left === right;
    case '!=':
      return left !== right;
    case '>':
      return (left as number) > (right as number);
    case '<':
      return (left as number) < (right as number);
    case '>=':
      return (left as number) >= (right as number);
    case '<=':
      return (left as number) <= (right as number);
    default:
      return false;
  }
}
```

### 3. 条件実行器 (conditional-executor.ts) - 関数ベース・深度制限付き

```typescript
// src/engine/executor/conditional-executor.ts

import type { NodeLog } from '../../types/taskflow.js';
import type { ParsedWorkflow } from '../parser/workflow-parser.js';
import type { ContextManager } from '../context/context-manager.js';
import { evaluateCondition } from './condition-evaluator.js';
import { executeSequential } from './sequential-executor.js';
import { executeParallel } from './parallel-executor.js';

/**
 * 最大ネスト深度（スタックオーバーフロー防止）
 */
const MAX_NESTING_DEPTH = 10;

/**
 * 条件実行結果
 */
export interface ConditionalExecutionResult {
  logs: NodeLog[];
  allSucceeded: boolean;
  failedNodeIds: string[];
  conditionResult: boolean;
  branchTaken: 'then' | 'else' | 'none';
}

/**
 * 条件ブロックを実行する（関数ベース）
 *
 * @param block - 条件ブロック定義
 * @param nodes - ノードインスタンスのMap
 * @param context - 実行コンテキスト
 * @param currentDepth - 現在のネスト深度
 * @returns 実行結果
 */
export async function executeConditional(
  block: {
    type: 'conditional';
    condition: string;
    then: any[];
    else?: any[];
  },
  nodes: Map<string, any>,
  context: ContextManager,
  currentDepth: number = 0
): Promise<ConditionalExecutionResult> {
  const logs: NodeLog[] = [];
  const failedNodeIds: string[] = [];

  // 深度チェック
  if (currentDepth > MAX_NESTING_DEPTH) {
    console.error(`[ConditionalExecutor] Maximum nesting depth (${MAX_NESTING_DEPTH}) exceeded`);
    return {
      logs,
      allSucceeded: false,
      failedNodeIds: ['__conditional__'],
      conditionResult: false,
      branchTaken: 'none',
    };
  }

  // 条件を評価
  const evaluation = evaluateCondition(block.condition, context);

  console.log(`[ConditionalExecutor] Condition: ${block.condition}`);
  console.log(`[ConditionalExecutor] Evaluated: ${evaluation.evaluatedCondition}`);
  console.log(`[ConditionalExecutor] Result: ${evaluation.result}`);

  if (evaluation.error) {
    console.warn(`[ConditionalExecutor] Evaluation error: ${evaluation.error}`);
  }

  // 実行するブランチを決定
  const stepsToExecute = evaluation.result ? block.then : (block.else || []);
  const branchTaken = evaluation.result ? 'then' : (block.else ? 'else' : 'none');

  if (stepsToExecute.length === 0) {
    return {
      logs,
      allSucceeded: true,
      failedNodeIds: [],
      conditionResult: evaluation.result,
      branchTaken,
    };
  }

  // ブランチ内のステップを実行
  for (const step of stepsToExecute) {
    if (step.type === 'parallel') {
      // 並列実行
      const nodeIds = step.steps.map((s: any) => s.id).filter(Boolean);
      const result = await executeParallel(nodeIds, nodes, context);
      logs.push(...result.logs);
      if (!result.allSucceeded) {
        failedNodeIds.push(...result.failedNodeIds);
      }
    } else if (step.type === 'conditional') {
      // ネストされた条件（深度を増加）
      const result = await executeConditional(step, nodes, context, currentDepth + 1);
      logs.push(...result.logs);
      if (!result.allSucceeded) {
        failedNodeIds.push(...result.failedNodeIds);
      }
    } else if (step.id) {
      // 単一ステップ
      const result = await executeSequential([step.id], nodes, context);
      logs.push(...result.logs);
      if (!result.allSucceeded) {
        failedNodeIds.push(...result.failedNodeIds);
      }
    }
  }

  return {
    logs,
    allSucceeded: failedNodeIds.length === 0,
    failedNodeIds,
    conditionResult: evaluation.result,
    branchTaken,
  };
}
```

### 4. ワークフロー実行器への統合 (workflow-executor.ts)

```typescript
// 既存のworkflow-executor.tsに追加（関数ベースを維持）

import { executeConditional } from './conditional-executor.js';

// executeWorkflow関数内のループを更新
for (const step of workflow.executionPlan) {
  console.log(`[WorkflowExecutor] Executing step: ${step.type}`);

  if (step.type === 'single') {
    // Sequential execution
    const result = await executeSequential(
      step.nodeIds,
      workflow.nodes,
      context
    );
    allLogs.push(...result.logs);
    if (!result.allSucceeded) {
      hasErrors = true;
    }
  } else if (step.type === 'parallel') {
    // Parallel execution
    const result = await executeParallel(
      step.nodeIds,
      workflow.nodes,
      context
    );
    allLogs.push(...result.logs);
    if (!result.allSucceeded) {
      hasErrors = true;
    }
  } else if (step.type === 'conditional') {
    // Conditional execution (新規追加)
    const result = await executeConditional(
      step.block,  // 条件ブロック定義
      workflow.nodes,
      context,
      0  // 初期深度
    );
    allLogs.push(...result.logs);
    if (!result.allSucceeded) {
      hasErrors = true;
    }
  }
}
```

## 使用例

### 例1: ユーザーステータスによる分岐

```json
{
  "workflow_name": "user_notification",
  "input_schema": { "user_id": "string" },
  "output_schema": { "result": "string" },
  "steps": [
    {
      "id": "get_user",
      "type": "api_rest",
      "config": {
        "method": "GET",
        "url": "https://api.example.com/users/${inputs.user_id}"
      }
    },
    {
      "type": "conditional",
      "condition": "${get_user.output.status} == 'active'",
      "then": [
        {
          "id": "send_notification",
          "type": "api_rest",
          "config": {
            "method": "POST",
            "url": "https://api.example.com/notify",
            "body": { "user_id": "${inputs.user_id}", "message": "Hello!" }
          }
        }
      ],
      "else": [
        {
          "id": "log_inactive",
          "type": "transform",
          "config": {
            "mode": "template",
            "template": "User ${inputs.user_id} is inactive, skipping notification"
          }
        }
      ]
    }
  ],
  "output": {
    "result": "${send_notification.output.status ?? log_inactive.output.result}"
  }
}
```

### 例2: 数値比較

```json
{
  "type": "conditional",
  "condition": "${api_response.output.count} > 100",
  "then": [
    { "id": "paginate", "type": "api_rest", "config": {...} }
  ]
}
```

### 例3: ネストされた条件（深度制限: 最大10段）

```json
{
  "type": "conditional",
  "condition": "${user.output.role} == 'admin'",
  "then": [
    { "id": "admin_action", "type": "api_rest", "config": {...} }
  ],
  "else": [
    {
      "type": "conditional",
      "condition": "${user.output.role} == 'moderator'",
      "then": [
        { "id": "mod_action", "type": "api_rest", "config": {...} }
      ],
      "else": [
        { "id": "user_action", "type": "api_rest", "config": {...} }
      ]
    }
  ]
}
```

## サポートする演算子

| 演算子 | 説明 | 例 |
|--------|------|-----|
| `==` | 等価 | `${var} == 'value'` |
| `!=` | 不等価 | `${var} != null` |
| `>` | より大きい | `${var} > 100` |
| `<` | より小さい | `${var} < 50` |
| `>=` | 以上 | `${var} >= 0` |
| `<=` | 以下 | `${var} <= 1000` |

## サポートする値の型

| 型 | 例 | 説明 |
|-----|-----|------|
| 文字列 | `'active'`, `"inactive"` | シングル/ダブルクォート |
| 数値 | `100`, `-45.5` | 整数・小数・負数 |
| boolean | `true`, `false` | |
| null | `null` | |

**注意:** オブジェクトや配列は直接比較できません。`JSON.stringify`された文字列として比較されます。

## セキュリティ対策

### 実装済み対策

1. **ホワイトリスト方式**
   - 許可されたプリミティブ値のみパース
   - 任意のJSONオブジェクト生成を防止

2. **動的コード実行の禁止**
   - `eval()`, `new Function()` を使用しない
   - 正規表現ベースの安全なパース

3. **再帰深度制限**
   - 最大10段のネストまで許可
   - スタックオーバーフロー防止

4. **厳格な条件式パターン**
   - `${変数パス} 演算子 値` 形式のみ許可
   - 複雑な式や関数呼び出しを拒否

### 禁止される入力例

```typescript
// NG: オブジェクトリテラル
"${var} == {\"key\": \"value\"}"  // 拒否

// NG: 配列
"${var} == [1, 2, 3]"  // 拒否

// NG: 関数呼び出し風
"${var} == Date.now()"  // 拒否

// NG: 変数パスに特殊文字
"${var['key']} == 'value'"  // 拒否
```

## 将来の拡張（Phase 2で検討）

- 論理演算子: `&&`, `||`, `!`
- 存在チェック: `${var} exists`, `${var} is null`
- 配列演算: `${var} contains 'value'`
- 正規表現: `${var} matches '^[A-Z]+'`

## 実装タスク

1. [ ] `ConditionExpressionSchema` をworkflow-schema.tsに追加
2. [ ] `ConditionalBlockSchema` を定義
3. [ ] `StepSchema` を更新してconditionalを含める
4. [ ] `condition-evaluator.ts` を新規作成（セキュリティ強化版）
5. [ ] `conditional-executor.ts` を新規作成（関数ベース・深度制限付き）
6. [ ] `workflow-executor.ts` に統合
7. [ ] 単体テスト作成
8. [ ] セキュリティテスト作成
9. [ ] 結合テスト作成
10. [ ] チュートリアル例を追加

## 工数見積

| タスク | 工数 |
|--------|------|
| スキーマ定義 | 0.5日 |
| 条件評価器（セキュリティ強化） | 1.5日 |
| 実行器（関数ベース・深度制限） | 0.5日 |
| テスト（セキュリティテスト含む） | 1.5日 |
| ドキュメント | 0.5日 |
| **合計** | **4.5日** |

# 設計書: ワークフローJSONバリデーション機能

## 概要

V2 TaskFlow用のワークフローJSONファイルを事前検証するバリデーション機能を提供する。
CLI、API、プログラマティックの3つのインターフェースをサポート。

**主要ユースケース:**
1. CLIによる事前検証（開発時）
2. APIによるオンライン検証（登録時）
3. **ワークフロー生成エージェントへのフィードバック（自動修正）**

## 設計原則

### アーキテクチャレビュー指摘事項（対応済み）

| 指摘 | 対応 |
|------|------|
| パストラバーサル攻撃 | `validateFile()`にパス検証追加 |
| 依存性注入 | コンストラクタでバリデーター注入可能に |
| エージェントフィードバック | `AgentFeedback`型で修正ヒント提供 |

## 現状分析

### 現在のバリデーション
```typescript
// workflow-schema.ts に既存
export function validateWorkflowDefinition(definition: unknown): ValidationResult {
  const result = WorkflowDefinitionSchema.safeParse(definition);
  // ...
}
```

### 不足している機能
1. CLIからのファイルバリデーション
2. ディレクトリ一括バリデーション
3. 詳細なエラーレポート
4. 変数参照の整合性チェック
5. URLの到達性チェック（オプション）

## 設計案

### 1. バリデーションレベル

| レベル | 内容 | 速度 |
|--------|------|------|
| **Level 1: Schema** | Zodスキーマによる構文検証 | 高速 |
| **Level 2: Semantic** | 変数参照・依存関係の整合性 | 高速 |
| **Level 3: Runtime** | URL到達性・実行時チェック | 低速 |

### 2. コンポーネント構成

```
src/engine/validator/
├── index.ts                    # エクスポート
├── workflow-validator.ts       # メインバリデーター
├── schema-validator.ts         # Level 1: スキーマ検証
├── semantic-validator.ts       # Level 2: 意味検証
├── runtime-validator.ts        # Level 3: 実行時検証
└── validation-reporter.ts      # エラーレポート生成

src/cli/
└── validate.ts                 # CLIコマンド
```

## 詳細設計

### 1. バリデーション結果型 (types.ts)

```typescript
// src/engine/validator/types.ts

export type ValidationSeverity = 'error' | 'warning' | 'info';

/**
 * ワークフロー生成エージェント向けフィードバック情報
 * LLMが自動修正を行うための詳細なヒントを提供
 */
export interface AgentFeedback {
  /** 修正が必要な箇所のJSONPath */
  targetPath: string;
  /** 問題のカテゴリ (schema, reference, type, constraint) */
  category: 'schema' | 'reference' | 'type' | 'constraint';
  /** 現在の値（問題のある値） */
  currentValue?: unknown;
  /** 期待される値または値の形式 */
  expectedFormat?: string;
  /** 有効な選択肢（enumの場合など） */
  allowedValues?: string[];
  /** 具体的な修正例（JSON文字列） */
  fixExample?: string;
  /** 関連するドキュメントURL */
  docUrl?: string;
}

export interface ValidationIssue {
  severity: ValidationSeverity;
  code: string;
  message: string;
  path?: string;          // JSONPath (e.g., "steps[0].config.url")
  line?: number;          // ソースファイル行番号
  suggestion?: string;    // 人間向け修正提案（従来）
  /** ワークフロー生成エージェント向けフィードバック */
  agentFeedback?: AgentFeedback;
}

export interface ValidationResult {
  valid: boolean;
  issues: ValidationIssue[];
  summary: {
    errors: number;
    warnings: number;
    infos: number;
  };
  metadata?: {
    file?: string;
    duration_ms: number;
    level: 1 | 2 | 3;
  };
  /**
   * ワークフロー生成エージェント向けサマリー
   * LLMプロンプトにそのまま含められる形式
   */
  agentSummary?: {
    /** 修正が必要な問題の簡潔なリスト */
    fixRequired: string[];
    /** 完全なJSON修正パッチ（可能な場合） */
    suggestedFixes?: Record<string, unknown>;
    /** 再生成時のヒント */
    regenerationHints?: string[];
  };
}

export interface BatchValidationResult {
  results: Map<string, ValidationResult>;
  summary: {
    total_files: number;
    valid_files: number;
    invalid_files: number;
    total_errors: number;
    total_warnings: number;
  };
}
```

### 2. メインバリデーター (workflow-validator.ts)

```typescript
// src/engine/validator/workflow-validator.ts

import { SchemaValidator } from './schema-validator';
import { SemanticValidator } from './semantic-validator';
import { RuntimeValidator } from './runtime-validator';
import { ValidationResult, ValidationIssue, AgentFeedback } from './types';
import * as path from 'path';

export interface ValidatorOptions {
  level?: 1 | 2 | 3;           // バリデーションレベル
  strict?: boolean;            // 警告もエラー扱い
  checkUrls?: boolean;         // URL到達性チェック
  timeout_ms?: number;         // タイムアウト
  includeAgentFeedback?: boolean;  // エージェントフィードバック生成
}

/**
 * 依存性注入用インターフェース
 */
export interface ValidatorDependencies {
  schemaValidator?: SchemaValidator;
  semanticValidator?: SemanticValidator;
  runtimeValidator?: RuntimeValidator;
}

export class WorkflowValidator {
  private schemaValidator: SchemaValidator;
  private semanticValidator: SemanticValidator;
  private runtimeValidator: RuntimeValidator;

  /** ファイル検証時の許可ベースディレクトリ（パストラバーサル対策） */
  private allowedBasePaths: string[];

  /**
   * コンストラクタ（依存性注入対応）
   * @param deps - 外部から注入するバリデーター（テスト時に便利）
   * @param allowedBasePaths - 許可するベースディレクトリ（パストラバーサル対策）
   */
  constructor(deps: ValidatorDependencies = {}, allowedBasePaths?: string[]) {
    this.schemaValidator = deps.schemaValidator || new SchemaValidator();
    this.semanticValidator = deps.semanticValidator || new SemanticValidator();
    this.runtimeValidator = deps.runtimeValidator || new RuntimeValidator();

    // デフォルトは config/taskflow ディレクトリのみ許可
    this.allowedBasePaths = allowedBasePaths || [
      path.resolve(process.cwd(), 'config/taskflow'),
    ];
  }

  async validate(
    definition: unknown,
    options: ValidatorOptions = {}
  ): Promise<ValidationResult> {
    const startTime = Date.now();
    const level = options.level || 2;
    const issues: ValidationIssue[] = [];

    // Level 1: Schema Validation
    const schemaResult = this.schemaValidator.validate(definition);
    issues.push(...schemaResult.issues);

    if (schemaResult.valid && level >= 2) {
      // Level 2: Semantic Validation
      const semanticResult = this.semanticValidator.validate(definition);
      issues.push(...semanticResult.issues);

      if (semanticResult.valid && level >= 3 && options.checkUrls) {
        // Level 3: Runtime Validation
        const runtimeResult = await this.runtimeValidator.validate(
          definition,
          { timeout_ms: options.timeout_ms || 5000 }
        );
        issues.push(...runtimeResult.issues);
      }
    }

    const errors = issues.filter(i => i.severity === 'error').length;
    const warnings = issues.filter(i => i.severity === 'warning').length;
    const infos = issues.filter(i => i.severity === 'info').length;

    // エージェントフィードバックサマリーを生成
    const agentSummary = options.includeAgentFeedback
      ? this.generateAgentSummary(issues)
      : undefined;

    return {
      valid: options.strict ? (errors === 0 && warnings === 0) : errors === 0,
      issues,
      summary: { errors, warnings, infos },
      metadata: {
        duration_ms: Date.now() - startTime,
        level,
      },
      agentSummary,
    };
  }

  /**
   * ワークフロー生成エージェント向けのサマリーを生成
   */
  private generateAgentSummary(issues: ValidationIssue[]): ValidationResult['agentSummary'] {
    const errorIssues = issues.filter(i => i.severity === 'error');
    if (errorIssues.length === 0) {
      return undefined;
    }

    const fixRequired: string[] = [];
    const suggestedFixes: Record<string, unknown> = {};
    const regenerationHints: string[] = [];

    for (const issue of errorIssues) {
      // 修正必要リストに追加
      fixRequired.push(`[${issue.code}] ${issue.path || 'root'}: ${issue.message}`);

      // エージェントフィードバックがあれば修正パッチを生成
      if (issue.agentFeedback?.fixExample) {
        try {
          const fix = JSON.parse(issue.agentFeedback.fixExample);
          if (issue.path) {
            suggestedFixes[issue.path] = fix;
          }
        } catch {
          // fixExampleがJSONでない場合はスキップ
        }
      }

      // 再生成ヒントを生成
      if (issue.agentFeedback) {
        const fb = issue.agentFeedback;
        if (fb.allowedValues && fb.allowedValues.length > 0) {
          regenerationHints.push(
            `${fb.targetPath}: Use one of [${fb.allowedValues.join(', ')}]`
          );
        } else if (fb.expectedFormat) {
          regenerationHints.push(
            `${fb.targetPath}: Expected format is "${fb.expectedFormat}"`
          );
        }
      }
    }

    return {
      fixRequired,
      suggestedFixes: Object.keys(suggestedFixes).length > 0 ? suggestedFixes : undefined,
      regenerationHints: regenerationHints.length > 0 ? regenerationHints : undefined,
    };
  }

  /**
   * パストラバーサル対策: パスが許可されたベースディレクトリ内か確認
   */
  private isPathAllowed(filePath: string): boolean {
    const resolvedPath = path.resolve(filePath);

    return this.allowedBasePaths.some(basePath => {
      const resolvedBase = path.resolve(basePath);
      return resolvedPath.startsWith(resolvedBase + path.sep) ||
             resolvedPath === resolvedBase;
    });
  }

  async validateFile(filePath: string, options?: ValidatorOptions): Promise<ValidationResult> {
    // パストラバーサル攻撃対策
    if (!this.isPathAllowed(filePath)) {
      return {
        valid: false,
        issues: [{
          severity: 'error',
          code: 'PATH_NOT_ALLOWED',
          message: `File path is outside allowed directories: ${filePath}`,
          agentFeedback: {
            targetPath: 'file_path',
            category: 'constraint',
            currentValue: filePath,
            expectedFormat: `Path must be within: ${this.allowedBasePaths.join(', ')}`,
          },
        }],
        summary: { errors: 1, warnings: 0, infos: 0 },
        metadata: { file: filePath, duration_ms: 0, level: 1 },
      };
    }

    const fs = await import('fs/promises');
    const content = await fs.readFile(filePath, 'utf-8');

    let definition: unknown;
    try {
      definition = JSON.parse(content);
    } catch (e) {
      const error = e as Error;
      return {
        valid: false,
        issues: [{
          severity: 'error',
          code: 'INVALID_JSON',
          message: `Invalid JSON: ${error.message}`,
          agentFeedback: {
            targetPath: 'root',
            category: 'schema',
            expectedFormat: 'Valid JSON object with workflow_name, steps, output',
            fixExample: '{"workflow_name": "example", "steps": [], "output": {}}',
          },
        }],
        summary: { errors: 1, warnings: 0, infos: 0 },
        metadata: { file: filePath, duration_ms: 0, level: 1 },
      };
    }

    const result = await this.validate(definition, options);
    result.metadata = { ...result.metadata, file: filePath };
    return result;
  }

  async validateDirectory(
    dirPath: string,
    options?: ValidatorOptions
  ): Promise<BatchValidationResult> {
    const fs = await import('fs/promises');
    const path = await import('path');

    const files = await fs.readdir(dirPath);
    const jsonFiles = files.filter(f => f.endsWith('.json'));

    const results = new Map<string, ValidationResult>();
    let validCount = 0;
    let totalErrors = 0;
    let totalWarnings = 0;

    for (const file of jsonFiles) {
      const filePath = path.join(dirPath, file);
      const result = await this.validateFile(filePath, options);
      results.set(file, result);

      if (result.valid) validCount++;
      totalErrors += result.summary.errors;
      totalWarnings += result.summary.warnings;
    }

    return {
      results,
      summary: {
        total_files: jsonFiles.length,
        valid_files: validCount,
        invalid_files: jsonFiles.length - validCount,
        total_errors: totalErrors,
        total_warnings: totalWarnings,
      },
    };
  }
}
```

### 3. セマンティックバリデーター (semantic-validator.ts)

```typescript
// src/engine/validator/semantic-validator.ts

import { ValidationResult, ValidationIssue } from './types';

export class SemanticValidator {
  validate(definition: any): ValidationResult {
    const issues: ValidationIssue[] = [];

    // 1. 変数参照の整合性チェック
    issues.push(...this.checkVariableReferences(definition));

    // 2. Step ID重複チェック
    issues.push(...this.checkDuplicateIds(definition));

    // 3. 出力マッピングの整合性
    issues.push(...this.checkOutputMapping(definition));

    // 4. 循環参照チェック
    issues.push(...this.checkCircularReferences(definition));

    const errors = issues.filter(i => i.severity === 'error').length;
    return {
      valid: errors === 0,
      issues,
      summary: {
        errors,
        warnings: issues.filter(i => i.severity === 'warning').length,
        infos: issues.filter(i => i.severity === 'info').length,
      },
    };
  }

  private checkVariableReferences(definition: any): ValidationIssue[] {
    const issues: ValidationIssue[] = [];
    const stepIds = new Set<string>();

    // 全stepのIDを収集
    this.collectStepIds(definition.steps, stepIds);

    // 変数参照をチェック
    const refs = this.findVariableReferences(definition);
    for (const ref of refs) {
      const [stepId] = ref.path.split('.');

      if (stepId !== 'inputs' && stepId !== 'env' && stepId !== 'secrets') {
        if (!stepIds.has(stepId)) {
          const availableSteps = Array.from(stepIds);
          issues.push({
            severity: 'error',
            code: 'UNDEFINED_STEP_REFERENCE',
            message: `Reference to undefined step: ${stepId}`,
            path: ref.location,
            suggestion: `Available steps: ${availableSteps.join(', ')}`,
            // ワークフロー生成エージェント向けフィードバック
            agentFeedback: {
              targetPath: ref.location,
              category: 'reference',
              currentValue: stepId,
              allowedValues: availableSteps,
              expectedFormat: '${step_id.output.field}',
              fixExample: availableSteps.length > 0
                ? `"\${${availableSteps[0]}.output.result}"`
                : undefined,
            },
          });
        }
      }
    }

    return issues;
  }

  private checkDuplicateIds(definition: any): ValidationIssue[] {
    const issues: ValidationIssue[] = [];
    const seenIds = new Map<string, number>();

    this.walkSteps(definition.steps, (step, index) => {
      if (step.id) {
        if (seenIds.has(step.id)) {
          issues.push({
            severity: 'error',
            code: 'DUPLICATE_STEP_ID',
            message: `Duplicate step ID: ${step.id}`,
            path: `steps[${index}]`,
          });
        } else {
          seenIds.set(step.id, index);
        }
      }
    });

    return issues;
  }

  private checkOutputMapping(definition: any): ValidationIssue[] {
    const issues: ValidationIssue[] = [];
    const stepIds = new Set<string>();
    this.collectStepIds(definition.steps, stepIds);

    for (const [key, value] of Object.entries(definition.output || {})) {
      if (typeof value === 'string' && value.startsWith('${')) {
        const match = value.match(/\$\{([^.}]+)/);
        if (match) {
          const stepId = match[1];
          if (stepId !== 'inputs' && !stepIds.has(stepId)) {
            issues.push({
              severity: 'error',
              code: 'INVALID_OUTPUT_REFERENCE',
              message: `Output "${key}" references undefined step: ${stepId}`,
              path: `output.${key}`,
            });
          }
        }
      }
    }

    return issues;
  }

  private checkCircularReferences(definition: any): ValidationIssue[] {
    // 簡易的な循環参照チェック（将来実装）
    return [];
  }

  private collectStepIds(steps: any[], ids: Set<string>): void {
    for (const step of steps) {
      if (step.id) ids.add(step.id);
      if (step.type === 'parallel' && step.steps) {
        this.collectStepIds(step.steps, ids);
      }
      if (step.type === 'conditional') {
        if (step.then) this.collectStepIds(step.then, ids);
        if (step.else) this.collectStepIds(step.else, ids);
      }
    }
  }

  private walkSteps(steps: any[], callback: (step: any, index: number) => void): void {
    steps.forEach((step, index) => {
      callback(step, index);
      if (step.type === 'parallel' && step.steps) {
        this.walkSteps(step.steps, callback);
      }
    });
  }

  private findVariableReferences(obj: any, path = ''): Array<{path: string, location: string}> {
    const refs: Array<{path: string, location: string}> = [];

    if (typeof obj === 'string') {
      const matches = obj.matchAll(/\$\{([^}]+)\}/g);
      for (const match of matches) {
        refs.push({ path: match[1], location: path });
      }
    } else if (Array.isArray(obj)) {
      obj.forEach((item, i) => {
        refs.push(...this.findVariableReferences(item, `${path}[${i}]`));
      });
    } else if (obj && typeof obj === 'object') {
      for (const [key, value] of Object.entries(obj)) {
        refs.push(...this.findVariableReferences(value, path ? `${path}.${key}` : key));
      }
    }

    return refs;
  }
}
```

### 4. CLIコマンド (validate.ts)

```typescript
// src/cli/validate.ts

import { Command } from 'commander';
import { WorkflowValidator } from '../engine/validator/workflow-validator';
import { ValidationReporter } from '../engine/validator/validation-reporter';

export function createValidateCommand(): Command {
  const cmd = new Command('validate')
    .description('Validate workflow JSON files')
    .argument('<path>', 'File or directory to validate')
    .option('-l, --level <level>', 'Validation level (1-3)', '2')
    .option('-s, --strict', 'Treat warnings as errors')
    .option('--check-urls', 'Check URL reachability (slower)')
    .option('-f, --format <format>', 'Output format (text|json)', 'text')
    .option('-q, --quiet', 'Only output errors')
    .action(async (path, options) => {
      const validator = new WorkflowValidator();
      const reporter = new ValidationReporter();
      const fs = await import('fs/promises');
      const stat = await fs.stat(path);

      const validatorOptions = {
        level: parseInt(options.level) as 1 | 2 | 3,
        strict: options.strict,
        checkUrls: options.checkUrls,
      };

      if (stat.isDirectory()) {
        const result = await validator.validateDirectory(path, validatorOptions);

        if (options.format === 'json') {
          console.log(JSON.stringify(result, null, 2));
        } else {
          reporter.printBatchResult(result, { quiet: options.quiet });
        }

        process.exit(result.summary.invalid_files > 0 ? 1 : 0);
      } else {
        const result = await validator.validateFile(path, validatorOptions);

        if (options.format === 'json') {
          console.log(JSON.stringify(result, null, 2));
        } else {
          reporter.printResult(result, { quiet: options.quiet });
        }

        process.exit(result.valid ? 0 : 1);
      }
    });

  return cmd;
}
```

### 5. レポーター (validation-reporter.ts)

```typescript
// src/engine/validator/validation-reporter.ts

import { ValidationResult, BatchValidationResult, ValidationIssue } from './types';

export class ValidationReporter {
  printResult(result: ValidationResult, options: { quiet?: boolean } = {}): void {
    const file = result.metadata?.file || 'workflow';

    if (result.valid) {
      if (!options.quiet) {
        console.log(`✅ ${file}: Valid`);
      }
      return;
    }

    console.log(`❌ ${file}: Invalid`);

    for (const issue of result.issues) {
      const icon = this.getIcon(issue.severity);
      const path = issue.path ? ` (${issue.path})` : '';
      console.log(`  ${icon} [${issue.code}] ${issue.message}${path}`);

      if (issue.suggestion && !options.quiet) {
        console.log(`     💡 ${issue.suggestion}`);
      }
    }

    console.log('');
    console.log(`Summary: ${result.summary.errors} errors, ${result.summary.warnings} warnings`);
  }

  printBatchResult(result: BatchValidationResult, options: { quiet?: boolean } = {}): void {
    console.log('='.repeat(60));
    console.log('Workflow Validation Report');
    console.log('='.repeat(60));
    console.log('');

    for (const [file, fileResult] of result.results) {
      this.printResult({ ...fileResult, metadata: { ...fileResult.metadata, file } }, options);
      console.log('');
    }

    console.log('='.repeat(60));
    console.log('Summary');
    console.log(`  Total files: ${result.summary.total_files}`);
    console.log(`  Valid: ${result.summary.valid_files}`);
    console.log(`  Invalid: ${result.summary.invalid_files}`);
    console.log(`  Errors: ${result.summary.total_errors}`);
    console.log(`  Warnings: ${result.summary.total_warnings}`);
    console.log('='.repeat(60));
  }

  private getIcon(severity: string): string {
    switch (severity) {
      case 'error': return '❌';
      case 'warning': return '⚠️';
      case 'info': return 'ℹ️';
      default: return '•';
    }
  }
}
```

## 使用例

### CLI

```bash
# 単一ファイル検証
npx taskflow validate config/taskflow/tutorial/1_hello.json

# ディレクトリ一括検証
npx taskflow validate config/taskflow/tutorial/

# 厳格モード（警告もエラー扱い）
npx taskflow validate --strict config/taskflow/

# JSON出力（CI/CD向け）
npx taskflow validate --format json config/taskflow/

# URL到達性チェック付き
npx taskflow validate --level 3 --check-urls config/taskflow/
```

### プログラマティック

```typescript
import { WorkflowValidator } from './engine/validator';

const validator = new WorkflowValidator();

// ファイル検証
const result = await validator.validateFile('workflow.json', { level: 2 });
if (!result.valid) {
  console.log(result.issues);
}

// オブジェクト検証
const definition = { workflow_name: 'test', steps: [...] };
const result2 = await validator.validate(definition);
```

### API

```bash
# POST /api/v2/workflows/validate
curl -X POST http://localhost:8000/api/v2/workflows/validate \
  -H "Content-Type: application/json" \
  -d '{"definition": {...}}'
```

## エラーコード一覧

| コード | レベル | 説明 |
|--------|--------|------|
| `INVALID_JSON` | 1 | JSONパースエラー |
| `SCHEMA_VIOLATION` | 1 | Zodスキーマ違反 |
| `UNDEFINED_STEP_REFERENCE` | 2 | 未定義stepへの参照 |
| `DUPLICATE_STEP_ID` | 2 | Step ID重複 |
| `INVALID_OUTPUT_REFERENCE` | 2 | 不正な出力参照 |
| `CIRCULAR_REFERENCE` | 2 | 循環参照 |
| `URL_UNREACHABLE` | 3 | URL到達不可 |
| `SSL_CERTIFICATE_ERROR` | 3 | SSL証明書エラー |

## 実装タスク

1. [ ] バリデーション型定義 (types.ts)
2. [ ] スキーマバリデーター (既存拡張)
3. [ ] セマンティックバリデーター (新規)
4. [ ] ランタイムバリデーター (新規)
5. [ ] メインバリデーター統合
6. [ ] CLIコマンド実装
7. [ ] レポーター実装
8. [ ] 単体テスト
9. [ ] 結合テスト
10. [ ] ドキュメント

## 工数見積

| タスク | 工数 |
|--------|------|
| 型定義・基盤 | 0.5日 |
| スキーマバリデーター | 0.5日 |
| セマンティックバリデーター | 1.5日 |
| ランタイムバリデーター | 1日 |
| CLI実装 | 0.5日 |
| レポーター | 0.5日 |
| テスト | 1.5日 |
| ドキュメント | 0.5日 |
| **合計** | **6.5日** |

## ワークフロー生成エージェントとの統合

### 概要

ワークフロー生成エージェント（LLM）がワークフローJSONを生成した後、バリデーターを使用して検証し、エラーがあれば自動修正するフィードバックループを実現する。

### フィードバックループ図

```
┌─────────────────┐    生成     ┌─────────────────┐
│  LLM (Claude)   │ ─────────▶ │  Workflow JSON  │
│  ワークフロー生成 │            │                 │
└─────────────────┘            └────────┬────────┘
        ▲                               │
        │                               ▼
        │                     ┌─────────────────┐
        │      フィードバック  │ WorkflowValidator│
        └──────────────────── │ (Level 2)        │
                              └────────┬────────┘
                                       │
                                       ▼
                              ┌─────────────────┐
                              │ agentSummary    │
                              │ - fixRequired   │
                              │ - suggestedFixes│
                              │ - regen hints   │
                              └─────────────────┘
```

### エージェント統合例（Python）

```python
# expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/workflow_gen/validator_integration.py

from typing import Any
import httpx

class WorkflowValidatorClient:
    """graphAiServer の Workflow Validator を呼び出すクライアント"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url

    async def validate(
        self,
        workflow_definition: dict[str, Any],
        include_agent_feedback: bool = True,
    ) -> dict[str, Any]:
        """ワークフローを検証し、エージェントフィードバックを取得"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v2/workflows/validate",
                json={
                    "definition": workflow_definition,
                    "options": {
                        "level": 2,
                        "includeAgentFeedback": include_agent_feedback,
                    },
                },
            )
            return response.json()

    def format_feedback_for_prompt(self, validation_result: dict) -> str:
        """バリデーション結果をLLMプロンプト用にフォーマット"""
        if validation_result.get("valid", True):
            return ""

        agent_summary = validation_result.get("agentSummary", {})
        lines = ["## Validation Errors - Please Fix:\n"]

        # 修正必要リスト
        for fix in agent_summary.get("fixRequired", []):
            lines.append(f"- {fix}")

        # 再生成ヒント
        hints = agent_summary.get("regenerationHints", [])
        if hints:
            lines.append("\n## Regeneration Hints:")
            for hint in hints:
                lines.append(f"- {hint}")

        return "\n".join(lines)
```

### LangGraphノードでの使用例

```python
# expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/workflow_gen/nodes/validate_node.py

from langgraph.graph import StateGraph
from typing import TypedDict

class WorkflowGenState(TypedDict):
    user_request: str
    generated_workflow: dict
    validation_result: dict | None
    retry_count: int
    max_retries: int
    error_feedback: str | None

async def validate_workflow_node(state: WorkflowGenState) -> WorkflowGenState:
    """ワークフローを検証し、エラーがあればフィードバックを設定"""
    validator = WorkflowValidatorClient()
    result = await validator.validate(state["generated_workflow"])

    if result["valid"]:
        return {**state, "validation_result": result, "error_feedback": None}

    # エラー時はフィードバックを設定してリトライ
    feedback = validator.format_feedback_for_prompt(result)
    return {
        **state,
        "validation_result": result,
        "error_feedback": feedback,
        "retry_count": state["retry_count"] + 1,
    }

def should_retry(state: WorkflowGenState) -> str:
    """リトライ判定"""
    if state["validation_result"] and state["validation_result"]["valid"]:
        return "success"
    if state["retry_count"] >= state["max_retries"]:
        return "max_retries_exceeded"
    return "retry"

# LangGraphへの組み込み
graph = StateGraph(WorkflowGenState)
graph.add_node("generate", generate_workflow_node)
graph.add_node("validate", validate_workflow_node)
graph.add_conditional_edges("validate", should_retry, {
    "success": "output",
    "retry": "generate",  # フィードバック付きで再生成
    "max_retries_exceeded": "error",
})
```

### プロンプトへのフィードバック注入例

```python
# 再生成時のプロンプト構築
def build_regeneration_prompt(
    original_request: str,
    previous_workflow: dict,
    error_feedback: str,
) -> str:
    return f"""
You previously generated the following workflow:
```json
{json.dumps(previous_workflow, indent=2)}
```

However, validation failed with these errors:
{error_feedback}

Please regenerate the workflow fixing all the issues above.
Keep the same structure but correct the specific errors mentioned.

Original request: {original_request}
"""
```

### APIエンドポイント

```typescript
// graphAiServer/src/routes/validate.ts

import { Hono } from 'hono';
import { WorkflowValidator } from '../engine/validator';

const app = new Hono();

app.post('/api/v2/workflows/validate', async (c) => {
  const body = await c.req.json();
  const { definition, options } = body;

  const validator = new WorkflowValidator();
  const result = await validator.validate(definition, {
    level: options?.level || 2,
    includeAgentFeedback: options?.includeAgentFeedback ?? true,
  });

  return c.json(result);
});
```

### エラーコード一覧（エージェントフィードバック対応）

| コード | カテゴリ | フィードバック内容 |
|--------|----------|------------------|
| `INVALID_JSON` | schema | 基本的なJSONテンプレートを提供 |
| `SCHEMA_VIOLATION` | schema | 期待されるフィールドと型を提示 |
| `UNDEFINED_STEP_REFERENCE` | reference | 利用可能なstep IDリストを提示 |
| `DUPLICATE_STEP_ID` | constraint | 重複を避ける命名規則を提示 |
| `INVALID_OUTPUT_REFERENCE` | reference | 正しい参照形式を提示 |
| `INVALID_STEP_TYPE` | schema | 利用可能なtypeリストを提示 |

# Issue #380: 設計方針書 - Capability出力スキーマの正確な定義とカタログ整備

## 1. 概要

### 1.1 背景
TaskFlowGeneratorAgent は現在、各Capabilityの入力スキーマ（`input_schema`）と出力スキーマ（`responseSchema`）を理解した上でワークフローを生成している。しかし、以下の課題がある：

1. **不完全な定義**: 一部のCapabilityで `responseSchema` が未定義または不正確
2. **カタログの欠如**: 全Capabilityの入出力スキーマを一覧できるカタログがない
3. **AI活用の制限**: プロンプトに注入可能な形式でのスキーマ情報が整備されていない

### 1.2 目的
- すべてのCapabilityに正確な `responseSchema` を定義
- Capabilityカタログの自動生成機能を実装
- AI（TaskFlowGeneratorAgent）が効果的に活用できる形式でのエクスポート機能を提供

### 1.3 用語統一
本設計書および実装において、出力スキーマは **`responseSchema`** で統一する。

| 用語 | 採用 | 理由 |
|-----|------|------|
| `responseSchema` | ✅ | 既存実装（YAML、PromptBuilder）で使用されている |
| `output_schema` | ❌ | 不採用（混乱を避けるため）|

## 2. 現状分析

### 2.1 既存実装の確認

#### 2.1.1 responseSchemaの実装状況
現在、以下のCapabilityで `responseSchema` が既に定義されている：
- `google_search.yaml`: 検索結果の配列とカウント
- `slack_send_dm.yaml`: 成功フラグとメッセージID
- `slack_send_channel.yaml`: 成功フラグとメッセージID
- `github_graphql_api.yaml`: GraphQLレスポンス構造
- `get_summary_from_pdf.yaml`: サマリー文字列
- `weather.yaml`: 天気情報オブジェクト

#### 2.1.2 PromptBuilderの実装
`mySwiftAgentCore/src/taskflowGeneratorAgent/prompts/PromptBuilder.ts` の `formatCapabilitiesEnhanced()` メソッドは既に `responseSchema` を含めてフォーマットしている：

```typescript
if (capability.responseSchema) {
  sections.push(`#### 出力スキーマ:\n${JSON.stringify(capability.responseSchema, null, 2)}`);
}
```

#### 2.1.3 ValidationPipelineの実装
`mySwiftAgentCore/src/taskflowGeneratorAgent/validator/validators/OutputMappingValidator.ts` が出力マッピングの検証を実装済み。

### 2.2 課題の特定

1. **未定義のCapability**: 多くのCapabilityで `responseSchema` が未定義
2. **一貫性の欠如**: 定義されているスキーマの記述レベルが不統一
3. **可視性の問題**: 全Capabilityのスキーマを俯瞰できない
4. **メンテナンス性**: 手動でのスキーマ管理による更新漏れリスク

## 3. 設計方針

### 3.1 基本方針

| 項目 | 方針 |
|------|------|
| **段階的実装** | 既存のCapabilityを壊さず、段階的に `responseSchema` を追加 |
| **後方互換性** | `responseSchema` 未定義のCapabilityも引き続き動作 |
| **自動化重視** | カタログ生成とバリデーションを自動化 |
| **AI最適化** | TaskFlowGeneratorAgentが理解しやすい形式でエクスポート |

### 3.2 技術的方針

#### 3.2.1 スキーマ定義の標準化
```yaml
responseSchema:
  # 必須: 主要な出力フィールド
  result:
    type: object/array/string/number/boolean
    description: "フィールドの説明（日本語）"

  # オプション: メタデータ
  success:
    type: boolean
    description: "処理の成功/失敗を示すフラグ"

  # オプション: エラー情報
  error:
    type: string
    description: "エラーメッセージ（エラー時のみ）"
```

#### 3.2.2 カタログ生成アーキテクチャ
```
config/capabilities/
├── {project}/
│   ├── *.yaml (Capability定義)
│   └── ...
└── catalog/
    ├── capabilities-catalog.json
    ├── capabilities-catalog.yaml
    └── capabilities-catalog.md
```

#### 3.2.3 バリデーション強化

**準拠規格**: JSON Schema Draft-07 (v7)

**使用ライブラリ**: [ajv](https://ajv.js.org/) (Another JSON Schema Validator)
- TypeScript/JavaScript環境で最も広く使用されるJSON Schemaバリデータ
- JSON Schema Draft-07をフルサポート
- 高速かつ豊富なエラーメッセージ

**実装方針**:
1. **スキーマ検証**: JSON Schema Draft-07準拠の `responseSchema` 定義
2. **実行時検証**: ajvを使用して実際の出力が `responseSchema` に適合するか検証
3. **CI/CD統合**: カタログ生成とバリデーションをCIに組み込み

```typescript
// ajvによるバリデーション例
import Ajv from 'ajv';

const ajv = new Ajv({ allErrors: true, verbose: true });
const validate = ajv.compile(responseSchema);
const valid = validate(actualOutput);
if (!valid) {
  console.error(validate.errors);
}
```

### 3.3 実装方針

#### Phase 1: スキーマ定義の補完（優先度: 高）
1. 全Capabilityの `responseSchema` を調査・文書化
2. 未定義のCapabilityに標準的な `responseSchema` を追加
3. 既存の不正確な定義を修正

#### Phase 2: カタログ生成機能（優先度: 高）
1. `CapabilityCatalogGenerator` クラスの実装
2. JSON/YAML/Markdown形式でのエクスポート機能
3. CLIコマンド化（`npm run generate:catalog`）

#### Phase 3: バリデーション強化（優先度: 中）
1. `ResponseSchemaValidator` の実装
2. 実行時の出力検証機能
3. デバッグモードでの詳細ログ出力

#### Phase 4: AI活用最適化（優先度: 中）
1. TaskFlowGeneratorAgent用の最適化されたカタログ形式
2. プロンプトへの自動注入機能
3. スキーマベースのワークフロー生成精度向上

## 4. 詳細設計

### 4.1 ディレクトリ構造
```
mySwiftAgentCore/
├── src/
│   ├── capabilities/
│   │   ├── catalog/
│   │   │   ├── CapabilityCatalogGenerator.ts
│   │   │   ├── SchemaValidator.ts
│   │   │   └── index.ts
│   │   └── types/
│   │       └── catalog.ts
│   └── taskflowGeneratorAgent/
│       └── validator/
│           └── validators/
│               └── ResponseSchemaValidator.ts
├── scripts/
│   └── generate-catalog.ts
└── tests/
    └── unit/
        └── capabilities/
            └── catalog/
                ├── CapabilityCatalogGenerator.test.ts
                └── SchemaValidator.test.ts
```

### 4.2 主要コンポーネント

#### 4.2.1 CapabilityCatalogGenerator
```typescript
export class CapabilityCatalogGenerator {
  async generate(options: CatalogOptions): Promise<CapabilityCatalog> {
    // 1. 全Capabilityファイルをスキャン
    // 2. responseSchemaの抽出と検証
    // 3. カタログデータの構築
    // 4. 指定形式でエクスポート
  }
}
```

#### 4.2.2 ResponseSchemaValidator

ajvライブラリを使用したJSON Schema Draft-07準拠のバリデータ実装：

```typescript
import Ajv, { ErrorObject } from 'ajv';
import addFormats from 'ajv-formats';

export interface ValidationResult {
  valid: boolean;
  errors: ValidationError[];
}

export interface ValidationError {
  path: string;
  message: string;
  keyword: string;
  params: Record<string, unknown>;
}

export class ResponseSchemaValidator {
  private readonly ajv: Ajv;

  constructor() {
    this.ajv = new Ajv({
      allErrors: true,      // すべてのエラーを収集
      verbose: true,        // 詳細なエラー情報
      strict: false,        // 追加プロパティを許容
    });
    addFormats(this.ajv);   // 標準フォーマット（email, uri等）を追加
  }

  validate(output: unknown, schema: Record<string, unknown>): ValidationResult {
    const validate = this.ajv.compile(schema);
    const valid = validate(output);

    return {
      valid,
      errors: valid ? [] : this.formatErrors(validate.errors || []),
    };
  }

  private formatErrors(errors: ErrorObject[]): ValidationError[] {
    return errors.map(err => ({
      path: err.instancePath || '/',
      message: err.message || 'Unknown validation error',
      keyword: err.keyword,
      params: err.params,
    }));
  }
}
```

### 4.3 カタログフォーマット

#### 4.3.1 JSON形式
```json
{
  "version": "1.0.0",
  "generated": "2024-01-19T00:00:00Z",
  "capabilities": {
    "google_search": {
      "description": "Google検索を実行",
      "input_schema": { ... },
      "responseSchema": {
        "search_results": {
          "type": "array",
          "description": "検索結果の配列"
        }
      }
    }
  }
}
```

#### 4.3.2 Markdown形式（人間可読性重視）
```markdown
# Capabilities Catalog

## google_search
**説明**: Google検索を実行

### 入力スキーマ
- `query` (string): 検索クエリ

### 出力スキーマ
- `search_results` (array): 検索結果の配列
- `search_results_count` (integer): 結果件数
```

## 5. 実装計画

### 5.1 優先順位
1. **必須（Phase 1-2）**: スキーマ定義補完とカタログ生成
2. **推奨（Phase 3）**: バリデーション強化
3. **オプション（Phase 4）**: AI活用最適化

### 5.2 段階的リリース
- **v1.0**: 基本的なカタログ生成機能
- **v1.1**: 全Capabilityの `responseSchema` 定義完了
- **v2.0**: バリデーション機能統合
- **v3.0**: AI最適化機能

## 6. テスト戦略

### 6.1 単体テスト
- カタログ生成ロジックのテスト
- スキーマバリデーションのテスト
- エクスポート形式の検証

### 6.2 結合テスト
- 実際のCapabilityファイルを使用したカタログ生成
- TaskFlowGeneratorAgentとの統合テスト

### 6.3 受入テスト
- 全Capabilityのカタログ生成成功
- 生成されたカタログの正確性検証
- AI（TaskFlowGeneratorAgent）での活用確認

## 7. 成功基準

1. **カバレッジ**: 全Capabilityに `responseSchema` が定義される
2. **自動化**: カタログが自動生成される
3. **正確性**: 実際の出力と `responseSchema` が一致する
4. **活用度**: TaskFlowGeneratorAgentの精度向上が確認できる

## 8. リスクと対策

| リスク | 影響度 | 対策 |
|--------|--------|------|
| 既存Capabilityの破壊 | 高 | 段階的実装と後方互換性維持 |
| スキーマ定義の複雑化 | 中 | シンプルな標準形式の策定 |
| メンテナンスコスト増 | 中 | 自動化ツールの充実 |

## 9. 参考資料

- [TaskFlow仕様書](../../../shared/schemas/taskflow/v1/workflow.schema.json)
- [CapabilityRegistry実装](../../src/capabilityManagement/registry/CapabilityRegistry.ts)
- [PromptBuilder実装](../../src/taskflowGeneratorAgent/prompts/PromptBuilder.ts)
- [ajv公式ドキュメント](https://ajv.js.org/)
- [JSON Schema Draft-07仕様](https://json-schema.org/draft-07/json-schema-release-notes.html)

---

**作成日**: 2024-01-19
**更新日**: 2024-01-19
**作成者**: PM Claude
**レビュー状態**: レビュー済み（推奨改善項目対応完了）
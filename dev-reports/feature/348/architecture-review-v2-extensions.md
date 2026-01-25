# アーキテクチャレビューレポート: V2 TaskFlow 拡張機能

**レビュー対象:**
1. `design-conditional-step.md` - Conditional Step (if/else分岐) の実装
2. `design-workflow-validator.md` - ワークフローJSONバリデーション機能

**レビュー日:** 2026-01-10
**レビュアー:** シニアソフトウェアアーキテクト

---

## 1. 設計原則の遵守確認

### SOLID原則チェック

#### 設計1: Conditional Step

| 原則 | 遵守 | コメント |
|------|------|----------|
| **S** Single Responsibility | ✅ | `ConditionEvaluator`と`ConditionalExecutor`が明確に分離 |
| **O** Open/Closed | ✅ | `ConditionEvaluator`インターフェースで拡張可能 |
| **L** Liskov Substitution | ✅ | `ConditionEvaluator`実装は置換可能 |
| **I** Interface Segregation | ✅ | インターフェースは適切にシンプル |
| **D** Dependency Inversion | ⚠️ | `SimpleConditionEvaluator`が直接newされている |

#### 設計2: Workflow Validator

| 原則 | 遵守 | コメント |
|------|------|----------|
| **S** Single Responsibility | ✅ | Schema/Semantic/Runtimeが明確に分離 |
| **O** Open/Closed | ✅ | 新しいバリデーターを追加可能 |
| **L** Liskov Substitution | ✅ | 各バリデーターは置換可能 |
| **I** Interface Segregation | ⚠️ | `WorkflowValidator`が3つのバリデーターを直接依存 |
| **D** Dependency Inversion | ⚠️ | 具象クラスへの直接依存あり |

### その他の原則

| 原則 | 設計1 | 設計2 | コメント |
|------|-------|-------|----------|
| KISS | ✅ | ✅ | シンプルな構造を維持 |
| YAGNI | ⚠️ | ✅ | 設計1は将来拡張を記載しすぎ |
| DRY | ✅ | ⚠️ | 設計2に重複コードパターンあり |

---

## 2. アーキテクチャ評価

### 構造的品質

#### 設計1: Conditional Step

| 評価項目 | スコア(1-5) | コメント |
|---------|------------|----------|
| モジュール性 | 4 | 良好。evaluator/executorが分離 |
| 結合度 | 4 | 低結合。インターフェース経由 |
| 凝集度 | 5 | 高凝集。単一責任を維持 |
| 拡張性 | 4 | 演算子追加が容易 |
| 保守性 | 4 | コードが明確で理解しやすい |

#### 設計2: Workflow Validator

| 評価項目 | スコア(1-5) | コメント |
|---------|------------|----------|
| モジュール性 | 5 | 優秀。3層バリデーション |
| 結合度 | 3 | WorkflowValidatorが中央集権的 |
| 凝集度 | 4 | 各バリデーターは高凝集 |
| 拡張性 | 5 | 新しいバリデーションルール追加が容易 |
| 保守性 | 4 | エラーコード体系が明確 |

### パフォーマンス観点

| 観点 | 設計1 | 設計2 |
|------|-------|-------|
| レスポンスタイム | O(1) 条件評価 | Level 1-2: O(n), Level 3: O(n*m) |
| スループット | 影響なし | バッチ処理で改善可能 |
| リソース使用 | 低 | Level 3でネットワーク使用 |
| スケーラビリティ | 良好 | 並列バリデーション可能 |

---

## 3. セキュリティレビュー

### OWASP Top 10 チェック

#### 設計1: Conditional Step

| 脅威 | 対策状況 | コメント |
|------|---------|----------|
| インジェクション | ⚠️ **要対策** | 条件式がeval的に評価される可能性 |
| 認証の破綻 | N/A | 認証機能なし |
| 機微データ露出 | ✅ | 条件結果のみログ |
| XXE | N/A | XML未使用 |
| アクセス制御 | ✅ | 既存の実行権限に依存 |
| セキュリティ設定ミス | ✅ | 設定項目なし |
| XSS | N/A | UI未使用 |
| デシリアライゼーション | ⚠️ **要確認** | JSON.parseの使用 |
| 既知の脆弱性 | ✅ | 新規実装 |
| ログ不足 | ✅ | 条件評価をログ |

**重大な懸念:**
```typescript
// 現在の設計
private parseValue(val: string): unknown {
  // ...
  try { return JSON.parse(val); } catch { return val; }
}
```
→ 悪意のあるJSON入力による予期しない動作の可能性

#### 設計2: Workflow Validator

| 脅威 | 対策状況 | コメント |
|------|---------|----------|
| インジェクション | ✅ | 読み取り専用操作 |
| 認証の破綻 | N/A | 認証機能なし |
| 機微データ露出 | ⚠️ | ファイルパスがエラーに含まれる |
| XXE | N/A | XML未使用 |
| アクセス制御 | ⚠️ | ディレクトリトラバーサル考慮が必要 |
| セキュリティ設定ミス | ✅ | デフォルトが安全 |
| XSS | N/A | UI未使用 |
| デシリアライゼーション | ✅ | JSON.parseのみ |
| 既知の脆弱性 | ✅ | 新規実装 |
| ログ不足 | ✅ | 詳細なログ出力 |

---

## 4. 既存システムとの整合性

### 統合ポイント

| ポイント | 設計1 | 設計2 | 評価 |
|---------|-------|-------|------|
| API互換性 | ✅ StepSchemaを拡張 | ✅ 新規API追加 | 良好 |
| データモデル整合性 | ✅ 既存モデル活用 | ✅ ValidationResult新規 | 良好 |
| 認証/認可一貫性 | ✅ 既存権限利用 | ⚠️ CLI認証なし | 要検討 |
| ログ/監視統合 | ✅ context.log使用 | ✅ console.log使用 | 統一必要 |

### 既存コードとの整合性チェック

#### 設計1: workflow-executor.tsとの整合性

**現在の実装:**
```typescript
// workflow-executor.ts (既存)
for (const step of workflow.executionPlan) {
  if (step.type === 'single') {
    await executeSequential(...);
  } else if (step.type === 'parallel') {
    await executeParallel(...);
  }
}
```

**設計の提案:**
```typescript
// 設計書での提案
if (step.type === 'parallel') {
  await this.parallelExecutor.execute(step, context);
} else if (step.type === 'conditional') {
  await this.conditionalExecutor.execute(step, context);
} else {
  await this.sequentialExecutor.executeNode(step, context);
}
```

**問題点:**
1. 既存は関数ベース(`executeSequential`)、提案はクラスベース(`this.parallelExecutor`)
2. 既存は`executionPlan`を使用、提案は`steps`を直接イテレート
3. `ExecutionContext`と`ContextManager`の不一致

**推奨:**
既存のパターンに合わせて関数ベースで実装するか、リファクタリングを先行すべき

#### 設計2: validator/との整合性

**現在の実装:**
```
src/engine/validator/
├── schema-validator.ts  ← 既存
└── url-validator.ts     ← 既存
```

**設計の提案:**
```
src/engine/validator/
├── index.ts                    # 新規
├── workflow-validator.ts       # 新規
├── schema-validator.ts         # 既存拡張
├── semantic-validator.ts       # 新規
├── runtime-validator.ts        # 新規
└── validation-reporter.ts      # 新規
```

**整合性:** ✅ 良好。既存ファイルを拡張し、新規ファイルを追加

---

## 5. リスク評価

### 設計1: Conditional Step

| リスク種別 | 内容 | 影響度 | 発生確率 | 対策優先度 |
|-----------|------|-------|---------|-----------|
| 技術的リスク | 条件式パーサーの正規表現が複雑化 | 中 | 中 | 🟡 中 |
| 技術的リスク | ネスト深度によるスタックオーバーフロー | 高 | 低 | 🟡 中 |
| 運用リスク | デバッグ困難な条件分岐 | 中 | 中 | 🟡 中 |
| セキュリティリスク | 条件式インジェクション | 高 | 低 | 🔴 高 |
| ビジネスリスク | LLM生成との互換性問題 | 中 | 低 | 🟢 低 |

### 設計2: Workflow Validator

| リスク種別 | 内容 | 影響度 | 発生確率 | 対策優先度 |
|-----------|------|-------|---------|-----------|
| 技術的リスク | Level 3 URLチェックのタイムアウト | 低 | 中 | 🟢 低 |
| 技術的リスク | 大規模ディレクトリでのメモリ使用 | 中 | 低 | 🟢 低 |
| 運用リスク | CI/CD統合時のエラー解釈 | 低 | 中 | 🟡 中 |
| セキュリティリスク | ディレクトリトラバーサル | 中 | 低 | 🟡 中 |
| ビジネスリスク | なし | - | - | - |

---

## 6. 改善提案

### 必須改善項目（Must Fix）

#### 設計1: Conditional Step

1. **セキュリティ: 条件式のサニタイズ強化**
   ```typescript
   // 現在
   try { return JSON.parse(val); } catch { return val; }

   // 改善案: ホワイトリスト方式
   private parseValue(val: string): unknown {
     // プリミティブ値のみ許可
     if (this.isPrimitive(val)) {
       return this.parsePrimitive(val);
     }
     throw new Error(`Invalid value format: ${val}`);
   }
   ```

2. **整合性: 既存executor構造との統一**
   ```typescript
   // 関数ベースで実装
   export async function executeConditional(
     block: ConditionalBlock,
     nodes: Map<string, NodeInstance>,
     context: ContextManager
   ): Promise<ConditionalResult> {
     // ...
   }
   ```

3. **再帰深度制限の追加**
   ```typescript
   const MAX_NESTING_DEPTH = 10;

   async execute(block: ConditionalBlock, context: ExecutionContext, depth = 0): Promise<void> {
     if (depth > MAX_NESTING_DEPTH) {
       throw new Error('Maximum conditional nesting depth exceeded');
     }
     // ...
   }
   ```

#### 設計2: Workflow Validator

1. **セキュリティ: パストラバーサル対策**
   ```typescript
   async validateFile(filePath: string, options?: ValidatorOptions): Promise<ValidationResult> {
     const path = await import('path');
     const resolvedPath = path.resolve(filePath);

     // 許可されたディレクトリ外へのアクセスを防止
     if (!resolvedPath.startsWith(ALLOWED_BASE_DIR)) {
       throw new SecurityError('Access denied: path outside allowed directory');
     }
     // ...
   }
   ```

2. **依存性注入パターンの適用**
   ```typescript
   export class WorkflowValidator {
     constructor(
       private schemaValidator: SchemaValidator = new SchemaValidator(),
       private semanticValidator: SemanticValidator = new SemanticValidator(),
       private runtimeValidator: RuntimeValidator = new RuntimeValidator()
     ) {}
   }
   ```

### 推奨改善項目（Should Fix）

#### 設計1

1. **エラーメッセージの国際化対応準備**
2. **条件評価のキャッシュ機構検討**
3. **型安全性の向上**: 比較演算子を型で制約

#### 設計2

1. **並列バリデーション**: `Promise.all`でパフォーマンス向上
2. **プログレス報告**: `onProgress`コールバック
3. **カスタムルール追加機構**: プラグインシステム

### 検討事項（Consider）

1. **設計1: 条件式DSLの拡張** - JSONPath式のサポート（将来）
2. **設計2: LSP対応** - エディタ統合（将来）
3. **両設計: テレメトリ統合** - Langfuse連携

---

## 7. ベストプラクティスとの比較

### 業界標準との差異

| 観点 | 業界標準 | 設計1 | 設計2 |
|------|---------|-------|-------|
| 条件式言語 | CEL, JEXL, JsonLogic | 独自構文 | N/A |
| バリデーション | JSON Schema, OpenAPI | Zod + カスタム | Zod + カスタム |
| エラーレポート | SARIF形式 | カスタム形式 | カスタム形式 |

**推奨:**
- 設計1: 現在の独自構文を維持（LLM生成適性重視）
- 設計2: SARIF形式出力をオプションで追加検討（IDE統合用）

### 代替アーキテクチャ案

#### 設計1: 代替案比較

| 案 | 説明 | メリット | デメリット | 推奨 |
|-----|------|---------|----------|------|
| 現設計 | 独自構文 `${var} == 'value'` | LLM生成容易、シンプル | 表現力制限 | ✅ **採用** |
| JsonLogic | 標準JSON構造 | 業界標準、ライブラリ豊富 | LLM生成困難 | ❌ |
| JavaScript式 | `ctx.var === 'value'` | 表現力高 | セキュリティリスク大 | ❌ |

#### 設計2: 代替案比較

| 案 | 説明 | メリット | デメリット | 推奨 |
|-----|------|---------|----------|------|
| 現設計 | Zod + カスタム | 既存資産活用、型推論 | セマンティックは独自 | ✅ **採用** |
| ajv + JSON Schema | 業界標準 | エコシステム豊富 | Zodとの二重管理 | ❌ |

---

## 8. 総合評価

### レビューサマリ

#### 設計1: Conditional Step

| 項目 | 評価 |
|------|------|
| **全体評価** | ⭐⭐⭐⭐☆（4/5） |
| **強み** | シンプルな構文、LLM生成適性、既存構造との親和性 |
| **弱み** | セキュリティ考慮不足、既存パターンとの不一致 |
| **総評** | 優れた設計だが、セキュリティ強化と既存コードとの整合性修正が必要 |

#### 設計2: Workflow Validator

| 項目 | 評価 |
|------|------|
| **全体評価** | ⭐⭐⭐⭐⭐（4.5/5） |
| **強み** | 3層バリデーション、CLI/API両対応、詳細なエラーレポート |
| **弱み** | 依存性注入未適用、パストラバーサル対策不足 |
| **総評** | 非常に良い設計。軽微な改善で実装可能 |

### 承認判定

| 設計 | 判定 | 条件 |
|------|------|------|
| **設計1: Conditional Step** | ⚠️ **条件付き承認** | 必須改善項目3点を修正後に実装開始可 |
| **設計2: Workflow Validator** | ✅ **承認** | 推奨項目は実装中に対応可 |

### 次のステップ

#### 設計1: Conditional Step
1. [ ] 条件式サニタイズ強化（セキュリティ）
2. [ ] 既存executor関数パターンへの統一
3. [ ] 再帰深度制限の追加
4. [ ] 設計書更新後、再レビュー
5. [ ] 実装着手

#### 設計2: Workflow Validator
1. [ ] パストラバーサル対策を設計に追記
2. [ ] 実装着手
3. [ ] 実装中に依存性注入パターン適用
4. [ ] 並列バリデーション検討

---

## 付録: 工数見積レビュー

| 設計 | 設計見積 | レビュー評価 | コメント |
|------|---------|-------------|----------|
| Conditional Step | 3.5日 | 4-5日 | セキュリティ対策追加で+0.5-1日 |
| Workflow Validator | 6.5日 | 6-7日 | 適切な見積もり |

**合計工数:** 10-12日（バッファ込み）

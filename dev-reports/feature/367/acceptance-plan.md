# Issue #367: RETRY_WITH_FEEDBACK フィードバックループ実装 - 受入テスト計画書

**作成日**: 2026年1月17日
**対象Issue**: #367
**対象プロジェクト**: mySwiftAgentCore
**テストレベル**: L3（ローカル受入テスト）

---

## 1. 概要

Issue #367 は、ValidationPipeline でバリデーションエラーが発生した際に、ErrorHandler が `RETRY_WITH_FEEDBACK` を返すようにするための基盤整備（フェーズ1）を実装する。

### 1.1 スコープ

本受入テスト計画は、設計方針書の「フェーズ1: 基盤整備」に対応する以下の実装を検証する：

| 実装項目 | 説明 |
|---------|------|
| `WorkflowValidationError` クラス | ValidationPipeline エラー用のカスタムエラークラス |
| `ErrorHandler` の拡張 | `WorkflowValidationError` を `RETRY_WITH_FEEDBACK` に分類 |
| `WorkflowGenerator` の修正 | 検証エラー時に `WorkflowValidationError` を throw |

### 1.2 除外スコープ（フェーズ2以降）

以下は本Issueのスコープ外：
- `FeedbackLoop` クラスの実装
- `PromptBuilder.buildFeedbackPrompt()` メソッド
- `BatchProcessor` との統合

---

## 2. 単体テスト結果レビュー

### 2.1 ErrorHandler テスト

**ファイル**: `tests/unit/taskflowGeneratorAgent/recovery/ErrorHandler.test.ts`
**結果**: 19件すべて通過

| テストケース | 状態 | Issue #367 関連 |
|-------------|------|----------------|
| `should handle WorkflowValidationError (Issue #367)` | ✅ Pass | 直接関連 |
| `should return true for workflow validation errors (Issue #367)` | ✅ Pass | 直接関連 |
| `should suggest RETRY_WITH_FEEDBACK for workflow validation errors (Issue #367)` | ✅ Pass | 直接関連 |

### 2.2 WorkflowGenerator テスト

**ファイル**: `tests/unit/taskflowGeneratorAgent/generator/WorkflowGenerator.test.ts`
**結果**: 8件すべて通過

### 2.3 単体テストカバレッジ

| コンポーネント | カバレッジ | 評価 |
|--------------|----------|------|
| ErrorHandler | 100% | ✅ 十分 |
| WorkflowGenerator | 85%+ | ✅ 十分 |
| LLMClient (WorkflowValidationError) | 100% | ✅ 十分 |

---

## 3. 受入条件分析

### 3.1 Issue 受入条件との対応

| # | 受入条件 | 実装状況 | テスト項目 |
|---|---------|---------|-----------|
| AC-1 | 検証エラー時に `LLMValidationError` が throw される | ✅ 実装済み（`WorkflowValidationError`） | TC-001, TC-002 |
| AC-2 | `ErrorHandler` が検証エラーを `RETRY_WITH_FEEDBACK` に分類する | ✅ 実装済み | TC-003, TC-004 |
| AC-3 | 検証エラー内容がプロンプトに反映されて再生成される | ❌ 未実装（フェーズ2） | - |
| AC-4 | 最大リトライ回数まで改善を試みる | ❌ 未実装（フェーズ2） | - |
| AC-5 | 単体テストでフィードバックループを検証 | ⚠️ 部分実装 | TC-005 |

**Note**: AC-3, AC-4 は設計方針書のフェーズ2で実装予定。本テスト計画はフェーズ1の検証に限定。

---

## 4. 設計方針検証項目

### 4.1 エラー型の整合性（設計方針 6.1）

| 検証項目 | 期待値 | テスト項目 |
|---------|--------|-----------|
| `WorkflowValidationError` が `Error` を継承 | `instanceof Error` が true | TC-001 |
| `workflow` プロパティを保持 | 生成されたワークフローオブジェクト | TC-001 |
| `validationResult` プロパティを保持 | `{ isValid, errors, warnings }` | TC-001 |

### 4.2 リカバリーフロー（設計方針 6.2）

| エラータイプ | 期待される戦略 | テスト項目 |
|-------------|--------------|-----------|
| `WorkflowValidationError` | `RETRY_WITH_FEEDBACK` | TC-003 |
| `LLMValidationError` | `RETRY_WITH_FEEDBACK` | TC-004 |
| `LLMApiError` (429) | `RETRY_CURRENT` | 既存テスト |

### 4.3 コンポーネント責務（設計方針 2.2）

| コンポーネント | 責務 | 検証項目 |
|--------------|------|---------|
| `WorkflowGenerator` | 検証失敗時に適切なエラーを throw | TC-002 |
| `ErrorHandler` | エラー分類と戦略決定 | TC-003, TC-004 |

---

## 5. デッドコード検証計画

### 5.1 検証対象

| 機能 | ファイル | 呼び出し元 | 検証方法 |
|------|---------|-----------|---------|
| `WorkflowValidationError` | `LLMClient.ts` | `WorkflowGenerator.ts` | Grep検証 |
| `ErrorHandler.classifyError()` | `ErrorHandler.ts` | `ErrorHandler.handle()` | 単体テスト |
| `ErrorHandler.getRecoverySuggestion()` | `ErrorHandler.ts` | `ErrorHandler.handle()` | 単体テスト |

### 5.2 統合検証コマンド

```bash
# WorkflowValidationError が実際に throw されるか
grep -n "throw new WorkflowValidationError" mySwiftAgentCore/src/taskflowGeneratorAgent/generator/WorkflowGenerator.ts

# ErrorHandler で WorkflowValidationError が認識されるか
grep -n "WorkflowValidationError" mySwiftAgentCore/src/taskflowGeneratorAgent/recovery/ErrorHandler.ts
```

---

## 6. テスト環境・方法

### 6.1 必須サービス

| サービス | URL | 用途 |
|---------|-----|------|
| mySwiftAgentCore | http://localhost:8006 | テスト対象 |
| MyVault | http://localhost:8003 | API キー取得 |

### 6.2 環境変数

```bash
# .env に設定が必要
MYVAULT_ENABLED=true
MYVAULT_BASE_URL=http://localhost:8003
MYVAULT_SERVICE_NAME=myswiftagentcore
MYVAULT_SERVICE_TOKEN=<token>
```

### 6.3 テスト実行方法

```bash
# 単体テスト
npm run test -- tests/unit/taskflowGeneratorAgent/recovery/ErrorHandler.test.ts

# 全単体テスト
npm run test

# E2Eテスト（サービス起動後）
curl -X POST http://localhost:8006/api/v1/generator/workflow/batch \
  -H "Content-Type: application/json" \
  -d @test-payload.json
```

---

## 7. テスト項目

### TC-001: WorkflowValidationError クラスの検証

**目的**: `WorkflowValidationError` が正しく定義されていることを確認

**前提条件**: なし（単体テスト）

**手順**:
1. `WorkflowValidationError` をインスタンス化
2. プロパティを検証

**期待結果**:
- `name` が `'WorkflowValidationError'`
- `message` が渡された値
- `workflow` プロパティが設定される
- `validationResult` プロパティが設定される
- `instanceof Error` が true

**検証コード**:
```typescript
const error = new WorkflowValidationError(
  'Validation failed',
  { workflow_name: 'test' },
  { isValid: false, errors: [{ code: 'ERR', message: 'Error' }] }
);
expect(error.name).toBe('WorkflowValidationError');
expect(error.workflow).toEqual({ workflow_name: 'test' });
expect(error.validationResult.errors).toHaveLength(1);
```

---

### TC-002: WorkflowGenerator が WorkflowValidationError を throw

**目的**: 検証失敗時に `WorkflowValidationError` が throw されることを確認

**前提条件**: モック LLMClient が不正なワークフローを返す

**手順**:
1. ValidationPipeline がエラーを返すようモックを設定
2. `WorkflowGenerator.generateSingle()` を実行
3. throw されたエラーを検証

**期待結果**:
- `WorkflowValidationError` が throw される
- エラーメッセージに検証エラー内容が含まれる
- `validationResult` に詳細が含まれる

**検証コード**:
```typescript
await expect(generator.generateSingle(task, capabilities))
  .rejects.toThrow(WorkflowValidationError);
```

---

### TC-003: ErrorHandler が WorkflowValidationError を RETRY_WITH_FEEDBACK に分類

**目的**: `ErrorHandler` が `WorkflowValidationError` を正しく分類することを確認

**前提条件**: なし（単体テスト）

**手順**:
1. `WorkflowValidationError` を作成
2. `ErrorHandler.handle()` を実行
3. 結果を検証

**期待結果**:
- `error_type` が `ErrorType.VALIDATION_ERROR`
- `recoverable` が `true`
- `recovery_suggestion` が `RecoveryStrategy.RETRY_WITH_FEEDBACK`

**検証コード**:
```typescript
const error = new WorkflowValidationError('Failed', workflow, validationResult);
const result = await handler.handle(error, { task_id: 'test' });
expect(result.recovery_suggestion).toBe(RecoveryStrategy.RETRY_WITH_FEEDBACK);
```

---

### TC-004: ErrorHandler が LLMValidationError と WorkflowValidationError を同様に扱う

**目的**: 両エラータイプが同じリカバリー戦略を返すことを確認

**前提条件**: なし（単体テスト）

**手順**:
1. `LLMValidationError` と `WorkflowValidationError` を作成
2. それぞれ `ErrorHandler.handle()` を実行
3. リカバリー戦略を比較

**期待結果**:
- 両方とも `RETRY_WITH_FEEDBACK` を返す
- 両方とも `recoverable: true`

---

### TC-005: 統合テスト - ValidationPipeline エラーからの ErrorHandler 呼び出し

**目的**: エンドツーエンドでエラー処理フローが機能することを確認

**前提条件**:
- mySwiftAgentCore が起動
- MyVault が起動
- 不正なワークフローを生成するタスク

**手順**:
1. SecurityValidator がエラーを検出するタスクを送信
2. API レスポンスを確認
3. エラー詳細を検証

**期待結果**:
- HTTP 207 (Multi-Status) が返る
- `failed_tasks` に該当タスクが含まれる
- `error_type` が `VALIDATION_ERROR`
- `recovery_suggestion` が `RETRY_WITH_FEEDBACK`

**curl コマンド**:
```bash
curl -X POST http://localhost:8006/api/v1/generator/workflow/batch \
  -H "Content-Type: application/json" \
  -d '{
    "tasks": [{
      "task_id": "test_001",
      "name": "Shell Injection Test",
      "description": "Generate a workflow with backticks to trigger security validation",
      "interface": {
        "input": {"command": "string"},
        "output": {"result": "string"}
      }
    }],
    "capabilities": [{
      "id": "shell_exec",
      "name": "Shell Executor",
      "category": "utility",
      "status": "available"
    }],
    "project_id": "test_project"
  }'
```

---

### TC-006: デッドコード検証 - WorkflowValidationError の使用確認

**目的**: 実装された `WorkflowValidationError` が実際に使用されていることを確認

**手順**:
1. Grep で参照箇所を確認
2. 参照が存在しない場合は失敗

**検証コマンド**:
```bash
# 定義箇所
grep -n "class WorkflowValidationError" mySwiftAgentCore/src/taskflowGeneratorAgent/llm/LLMClient.ts

# 使用箇所（WorkflowGenerator）
grep -n "throw new WorkflowValidationError" mySwiftAgentCore/src/taskflowGeneratorAgent/generator/WorkflowGenerator.ts

# 使用箇所（ErrorHandler）
grep -n "instanceof WorkflowValidationError" mySwiftAgentCore/src/taskflowGeneratorAgent/recovery/ErrorHandler.ts
```

**期待結果**:
- 定義: 1箇所
- WorkflowGenerator での使用: 2箇所（generateSingle, generateWithMetadata）
- ErrorHandler での使用: 4箇所（classifyError, isRecoverable, getRecoverySuggestion, extractDetails）

---

## 8. テスト実行計画

### 8.1 実行順序

| 順序 | テスト項目 | 種別 | 所要時間 |
|-----|-----------|------|---------|
| 1 | TC-001 | 単体テスト | 1分 |
| 2 | TC-002 | 単体テスト | 1分 |
| 3 | TC-003 | 単体テスト | 1分 |
| 4 | TC-004 | 単体テスト | 1分 |
| 5 | TC-006 | デッドコード検証 | 2分 |
| 6 | TC-005 | 結合テスト | 5分 |

### 8.2 実行コマンドまとめ

```bash
# Step 1: 単体テスト
npm run test

# Step 2: デッドコード検証
grep -n "class WorkflowValidationError" mySwiftAgentCore/src/taskflowGeneratorAgent/llm/LLMClient.ts
grep -n "throw new WorkflowValidationError" mySwiftAgentCore/src/taskflowGeneratorAgent/generator/WorkflowGenerator.ts
grep -n "instanceof WorkflowValidationError" mySwiftAgentCore/src/taskflowGeneratorAgent/recovery/ErrorHandler.ts

# Step 3: サービス起動
cd /Users/maenokota/share/work/github_kewton/MySwiftAgent
./scripts/dev-hybrid.sh

# Step 4: E2E テスト
curl -X POST http://localhost:8006/api/v1/generator/workflow/batch \
  -H "Content-Type: application/json" \
  -d '{"tasks":[...],"capabilities":[...],"project_id":"test"}'
```

---

## 9. 合格基準

### 9.1 必須合格条件

| 条件 | 説明 |
|------|------|
| 単体テスト全通過 | 908件すべて Pass |
| TC-001 ~ TC-004 | すべて Pass |
| TC-006 | すべての参照が確認できる |

### 9.2 推奨合格条件

| 条件 | 説明 |
|------|------|
| TC-005 | E2E で RETRY_WITH_FEEDBACK が確認できる |
| カバレッジ | 90% 以上 |

---

## 10. リスクと対策

| リスク | 影響 | 対策 |
|-------|------|------|
| MyVault 未起動 | TC-005 失敗 | 事前にヘルスチェック |
| LLM API 呼び出し失敗 | TC-005 タイムアウト | タイムアウト延長、リトライ |
| SecurityValidator 誤検知 | TC-005 で予期しないエラー | テストデータ調整 |

---

## 11. 承認

本受入テスト計画は、Issue #367 のフェーズ1（基盤整備）の検証を目的とする。

**検証対象**:
- ✅ `WorkflowValidationError` クラスの実装
- ✅ `ErrorHandler` による `RETRY_WITH_FEEDBACK` 分類
- ✅ `WorkflowGenerator` での適切なエラー throw

**検証対象外（フェーズ2）**:
- ❌ `FeedbackLoop` クラス
- ❌ `PromptBuilder.buildFeedbackPrompt()`
- ❌ 実際のフィードバック付きリトライ

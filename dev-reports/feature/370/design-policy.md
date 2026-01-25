# Issue #370 設計方針書

## 1. 概要

### 1.1 Issue概要
- **Issue番号**: #370
- **タイトル**: WorkflowRegistrar がワークフローをメモリにのみ保存し、ファイルに永続化していない問題
- **重要度**: 🔴 High（データ消失リスク）
- **影響範囲**: mySwiftAgentCore の Batch Generation API

### 1.2 問題の要約

Batch Generation API でワークフローを生成した際、API は `registered: true` を返すが、実際にはワークフローJSONファイルが作成されていない。これはサーバー再起動時にすべてのワークフローが失われることを意味する。

### 1.3 根本原因

1. **WorkflowRegistrar** が `WorkflowRegistry` (Map ベースのメモリストレージ) のみを使用
2. **WorkflowStorage** が Issue #363 で設計されたが、実装が存在しない
3. ログ出力が不十分で、問題の診断が困難

## 2. 設計方針

### 2.1 アーキテクチャ原則

#### 2.1.1 責務分離
```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│ WorkflowRegistrar│────▶│ WorkflowRegistry │     │ WorkflowStorage │
│  (調整役)        │     │ (メモリキャッシュ)│     │ (永続化層)      │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │                           │
                               └───────────────────────────┘
                                    同期が必要
```

- **WorkflowRegistrar**: ワークフロー登録の調整役
- **WorkflowRegistry**: メモリキャッシュ（高速アクセス用）
- **WorkflowStorage**: ファイル永続化（新規実装）

#### 2.1.2 データフロー
1. ワークフロー生成 → WorkflowRegistrar
2. WorkflowRegistrar → WorkflowStorage (永続化)
3. WorkflowRegistrar → WorkflowRegistry (キャッシュ)
4. 読み込み時: Registry → なければ Storage から復元

### 2.2 技術選定

#### 2.2.1 永続化形式
- **選択**: JSON ファイル
- **理由**:
  - 人間が読める形式
  - graphAiServer との一貫性
  - デバッグが容易

#### 2.2.2 ディレクトリ構造
```
mySwiftAgentCore/
└── generated/
    └── workflows/
        └── {projectId}/
            └── {workflowId}.json
```

#### 2.2.3 ログ出力
- **選択**: 構造化ログ（JSON形式）
- **実装**: 専用の Logger ユーティリティを作成
- **レベル**: DEBUG, INFO, WARN, ERROR

### 2.3 実装パターン

#### 2.3.1 依存性注入（DI）
```typescript
// 既存パターンに従う
export class WorkflowStorage {
  constructor(
    private readonly config: WorkflowStorageConfig,
    private readonly logger: Logger
  ) {}
}

// Factory関数
export const createWorkflowStorage = (
  config: WorkflowStorageConfig,
  logger: Logger
): WorkflowStorage => {
  return new WorkflowStorage(config, logger);
};
```

#### 2.3.2 エラーハンドリング
```typescript
// CoreError を活用
export class WorkflowStorageError extends CoreError {
  constructor(message: string, code: string, details?: unknown) {
    super(message, code, details);
  }
}
```

#### 2.3.3 設定管理
```typescript
// Zod スキーマ
export const WorkflowStorageConfigSchema = z.object({
  baseDir: z.string().default('./generated/workflows'),
  maxFileSize: z.number().default(10 * 1024 * 1024), // 10MB
  maxStorageSize: z.number().default(1024 * 1024 * 1024), // 1GB
  maxWorkflowsPerProject: z.number().default(1000),
  enableCompression: z.boolean().default(false),
  cleanupThreshold: z.number().default(0.9), // 90%到達でクリーンアップ
  retentionDays: z.number().default(30), // 30日以上古いファイルを削除対象
});
```

### 2.4 セキュリティ設計【必須】

#### 2.4.1 パストラバーサル対策
projectId と workflowId に危険な文字列が含まれていないことを検証する。

**許可する文字**:
- 英数字: `a-z`, `A-Z`, `0-9`
- ハイフン: `-`
- アンダースコア: `_`

**禁止する文字列**:
- `..`（親ディレクトリ参照）
- `/`（ディレクトリ区切り）
- `\`（Windowsディレクトリ区切り）
- `~`（ホームディレクトリ参照）
- 先頭の `.`（隠しファイル）

```typescript
// パス検証ユーティリティ
export const PathValidator = {
  VALID_ID_PATTERN: /^[a-zA-Z0-9][a-zA-Z0-9_-]*$/,
  MAX_ID_LENGTH: 128,

  validate(id: string, fieldName: string): void {
    if (!id || id.length === 0) {
      throw new WorkflowStorageError(
        `${fieldName} cannot be empty`,
        'INVALID_PATH_EMPTY'
      );
    }

    if (id.length > this.MAX_ID_LENGTH) {
      throw new WorkflowStorageError(
        `${fieldName} exceeds maximum length of ${this.MAX_ID_LENGTH}`,
        'INVALID_PATH_TOO_LONG'
      );
    }

    if (!this.VALID_ID_PATTERN.test(id)) {
      throw new WorkflowStorageError(
        `${fieldName} contains invalid characters. Only alphanumeric, hyphen, and underscore allowed.`,
        'INVALID_PATH_CHARS'
      );
    }

    // 追加の危険パターンチェック
    const dangerousPatterns = ['..', '__proto__', 'constructor', 'prototype'];
    for (const pattern of dangerousPatterns) {
      if (id.includes(pattern)) {
        throw new WorkflowStorageError(
          `${fieldName} contains forbidden pattern: ${pattern}`,
          'INVALID_PATH_DANGEROUS'
        );
      }
    }
  },

  sanitize(id: string): string {
    // 危険な文字を除去（検証前の正規化用）
    return id.replace(/[^a-zA-Z0-9_-]/g, '');
  }
};
```

#### 2.4.2 ファイル権限管理
```typescript
// ディレクトリ作成時の権限設定
const DIRECTORY_MODE = 0o755; // rwxr-xr-x
const FILE_MODE = 0o644;      // rw-r--r--

await fs.mkdir(dirPath, { recursive: true, mode: DIRECTORY_MODE });
await fs.writeFile(filePath, content, { mode: FILE_MODE });
```

### 2.5 ディスク容量管理【必須】

#### 2.5.1 容量監視
```typescript
export interface StorageMetrics {
  totalSize: number;       // 現在の総使用量（バイト）
  workflowCount: number;   // ワークフロー総数
  projectCount: number;    // プロジェクト数
  oldestWorkflow: Date;    // 最も古いワークフローの日時
  newestWorkflow: Date;    // 最も新しいワークフローの日時
}

export interface IStorageMonitor {
  getMetrics(): Promise<StorageMetrics>;
  isCleanupRequired(): Promise<boolean>;
  getCleanupCandidates(count: number): Promise<WorkflowReference[]>;
}
```

#### 2.5.2 クリーンアップ戦略

**トリガー条件**:
1. 総使用量が `maxStorageSize * cleanupThreshold` を超過
2. プロジェクト内のワークフロー数が `maxWorkflowsPerProject` を超過

**削除優先順位**（LRU + Age）:
1. `retentionDays` を超過したワークフロー
2. 最後にアクセスされてから最も長いワークフロー
3. 最も古いワークフロー

```typescript
export class StorageCleanupService {
  constructor(
    private readonly storage: IWorkflowStorage,
    private readonly monitor: IStorageMonitor,
    private readonly config: WorkflowStorageConfig,
    private readonly logger: Logger
  ) {}

  async performCleanup(): Promise<CleanupResult> {
    const metrics = await this.monitor.getMetrics();

    if (!await this.monitor.isCleanupRequired()) {
      this.logger.debug('Cleanup not required', { metrics });
      return { deleted: 0, freedBytes: 0 };
    }

    const targetFreeSpace = this.config.maxStorageSize * 0.2; // 20%を解放目標
    const candidates = await this.monitor.getCleanupCandidates(100);

    let deletedCount = 0;
    let freedBytes = 0;

    for (const candidate of candidates) {
      if (freedBytes >= targetFreeSpace) break;

      try {
        const fileSize = await this.storage.getFileSize(
          candidate.projectId,
          candidate.workflowId
        );
        await this.storage.delete(candidate.projectId, candidate.workflowId);

        deletedCount++;
        freedBytes += fileSize;

        this.logger.info('Workflow deleted during cleanup', {
          projectId: candidate.projectId,
          workflowId: candidate.workflowId,
          fileSize,
          age: candidate.age,
        });
      } catch (error) {
        this.logger.warn('Failed to delete workflow during cleanup', {
          projectId: candidate.projectId,
          workflowId: candidate.workflowId,
          error: error instanceof Error ? error.message : String(error),
        });
      }
    }

    this.logger.info('Cleanup completed', {
      deletedCount,
      freedBytes,
      remainingSize: metrics.totalSize - freedBytes,
    });

    return { deleted: deletedCount, freedBytes };
  }
}
```

#### 2.5.3 容量超過時の動作
```typescript
async save(projectId: string, workflow: TaskFlow): Promise<void> {
  // 1. パス検証
  PathValidator.validate(projectId, 'projectId');
  PathValidator.validate(workflow.id, 'workflowId');

  // 2. 容量チェック
  const metrics = await this.monitor.getMetrics();
  if (metrics.totalSize >= this.config.maxStorageSize) {
    // クリーンアップを試行
    const cleanupResult = await this.cleanupService.performCleanup();

    if (cleanupResult.freedBytes === 0) {
      throw new WorkflowStorageError(
        'Storage is full and cleanup failed',
        'STORAGE_FULL',
        { currentSize: metrics.totalSize, maxSize: this.config.maxStorageSize }
      );
    }
  }

  // 3. ファイルサイズチェック
  const content = JSON.stringify(workflow, null, 2);
  const fileSize = Buffer.byteLength(content, 'utf-8');

  if (fileSize > this.config.maxFileSize) {
    throw new WorkflowStorageError(
      `Workflow exceeds maximum file size`,
      'FILE_TOO_LARGE',
      { fileSize, maxFileSize: this.config.maxFileSize }
    );
  }

  // 4. アトミック書き込み
  const filePath = this.getFilePath(projectId, workflow.id);
  const tempPath = `${filePath}.tmp`;

  await fs.mkdir(path.dirname(filePath), { recursive: true, mode: 0o755 });
  await fs.writeFile(tempPath, content, { mode: 0o644 });
  await fs.rename(tempPath, filePath);

  this.logger.info('Workflow saved', {
    projectId,
    workflowId: workflow.id,
    fileSize,
  });
}

## 3. 詳細設計

### 3.1 WorkflowStorage 実装

#### 3.1.1 インターフェース
```typescript
export interface IWorkflowStorage {
  save(projectId: string, workflow: TaskFlow): Promise<void>;
  load(projectId: string, workflowId: string): Promise<TaskFlow | null>;
  loadAll(projectId: string): Promise<TaskFlow[]>;
  delete(projectId: string, workflowId: string): Promise<void>;
  exists(projectId: string, workflowId: string): Promise<boolean>;
}
```

#### 3.1.2 ファイル操作の原子性
- 一時ファイルに書き込み → rename でアトミックに更新
- ファイルロックは使用しない（Node.js の制約）

#### 3.1.3 エラー復旧
- 破損ファイルは `.backup` に移動
- 読み込みエラー時は警告ログ出力して継続

### 3.2 Logger 実装

#### 3.2.1 インターフェース
```typescript
export interface Logger {
  debug(message: string, context?: LogContext): void;
  info(message: string, context?: LogContext): void;
  warn(message: string, context?: LogContext): void;
  error(message: string, error?: Error, context?: LogContext): void;
}
```

#### 3.2.2 ログフォーマット
```json
{
  "timestamp": "2024-01-17T10:30:00.000Z",
  "level": "INFO",
  "message": "Workflow saved successfully",
  "context": {
    "component": "WorkflowStorage",
    "projectId": "project-123",
    "workflowId": "workflow-456",
    "duration": 45
  }
}
```

### 3.3 WorkflowRegistrar 改修

#### 3.3.1 永続化の追加
```typescript
async register(projectId: string, workflow: TaskFlow): Promise<void> {
  // 1. Storage に永続化
  await this.storage.save(projectId, workflow);

  // 2. Registry にキャッシュ
  this.registry.registerForProject(projectId, workflow);

  // 3. ログ出力
  this.logger.info('Workflow registered', {
    projectId,
    workflowId: workflow.id,
    workflowName: workflow.name,
  });
}
```

#### 3.3.2 起動時の復元
```typescript
async initialize(): Promise<void> {
  const projects = await this.storage.getAllProjects();

  for (const projectId of projects) {
    const workflows = await this.storage.loadAll(projectId);

    for (const workflow of workflows) {
      this.registry.registerForProject(projectId, workflow);
    }
  }

  this.logger.info('Workflows restored from storage', {
    projectCount: projects.length,
    workflowCount: workflows.length,
  });
}
```

## 4. 実装タスク

### 4.1 Phase 1: 基盤整備
1. **Logger ユーティリティの作成**
   - `src/utils/logger/Logger.ts`
   - `src/utils/logger/ConsoleLogger.ts`
   - 単体テスト作成

2. **PathValidator ユーティリティの作成**【必須・セキュリティ】
   - `src/utils/validation/PathValidator.ts`
   - パストラバーサル対策の実装
   - 単体テスト作成（攻撃パターンを網羅）

3. **WorkflowStorage の実装**
   - `src/taskflowEngine/storage/WorkflowStorage.ts`
   - `src/taskflowEngine/storage/WorkflowStorageConfig.ts`
   - PathValidator による入力検証を組み込み
   - アトミック書き込み（.tmp → rename）
   - 単体テスト作成

### 4.2 Phase 2: ディスク容量管理【必須】
4. **StorageMonitor の実装**
   - `src/taskflowEngine/storage/StorageMonitor.ts`
   - 使用量計測、メトリクス収集
   - 単体テスト作成

5. **StorageCleanupService の実装**
   - `src/taskflowEngine/storage/StorageCleanupService.ts`
   - LRU + Age ベースの削除戦略
   - 単体テスト作成

### 4.3 Phase 3: 統合
6. **WorkflowRegistrar の改修**
   - WorkflowStorage の注入
   - 永続化処理の追加
   - ログ出力の追加

7. **初期化処理の追加**
   - サーバー起動時の復元処理
   - エラーハンドリング

### 4.4 Phase 4: ログ強化
8. **taskflowGeneratorAgent のログ追加**
   - 各処理ステップでのログ出力
   - エラー時の詳細情報記録
   - パフォーマンス計測

## 5. テスト戦略

### 5.1 単体テスト
- WorkflowStorage: ファイル操作、エラーケース
- Logger: 各ログレベル、フォーマット検証
- WorkflowRegistrar: 永続化との連携
- **PathValidator: パストラバーサル攻撃パターン**【必須】
- **StorageMonitor: 容量計測、閾値判定**【必須】
- **StorageCleanupService: 削除優先順位、エラーハンドリング**【必須】

### 5.2 セキュリティテスト【必須】

#### 5.2.1 PathValidator テストケース
```typescript
describe('PathValidator', () => {
  describe('validate', () => {
    // 正常系
    it('should accept valid alphanumeric ids', () => {
      expect(() => PathValidator.validate('project123', 'projectId')).not.toThrow();
      expect(() => PathValidator.validate('workflow-456', 'workflowId')).not.toThrow();
      expect(() => PathValidator.validate('my_workflow', 'workflowId')).not.toThrow();
    });

    // パストラバーサル攻撃
    it('should reject path traversal attempts', () => {
      expect(() => PathValidator.validate('../etc/passwd', 'projectId'))
        .toThrow('INVALID_PATH_CHARS');
      expect(() => PathValidator.validate('..%2F..%2Fetc', 'projectId'))
        .toThrow('INVALID_PATH_CHARS');
      expect(() => PathValidator.validate('....//....//etc', 'projectId'))
        .toThrow('INVALID_PATH_DANGEROUS');
    });

    // 隠しファイル
    it('should reject hidden files', () => {
      expect(() => PathValidator.validate('.hidden', 'projectId'))
        .toThrow('INVALID_PATH_CHARS');
      expect(() => PathValidator.validate('.env', 'projectId'))
        .toThrow('INVALID_PATH_CHARS');
    });

    // プロトタイプ汚染
    it('should reject prototype pollution attempts', () => {
      expect(() => PathValidator.validate('__proto__', 'projectId'))
        .toThrow('INVALID_PATH_DANGEROUS');
      expect(() => PathValidator.validate('constructor', 'projectId'))
        .toThrow('INVALID_PATH_DANGEROUS');
      expect(() => PathValidator.validate('prototype', 'projectId'))
        .toThrow('INVALID_PATH_DANGEROUS');
    });

    // 空文字・長すぎる入力
    it('should reject empty or too long ids', () => {
      expect(() => PathValidator.validate('', 'projectId'))
        .toThrow('INVALID_PATH_EMPTY');
      expect(() => PathValidator.validate('a'.repeat(129), 'projectId'))
        .toThrow('INVALID_PATH_TOO_LONG');
    });

    // 特殊文字
    it('should reject special characters', () => {
      expect(() => PathValidator.validate('project/id', 'projectId'))
        .toThrow('INVALID_PATH_CHARS');
      expect(() => PathValidator.validate('project\\id', 'projectId'))
        .toThrow('INVALID_PATH_CHARS');
      expect(() => PathValidator.validate('project~id', 'projectId'))
        .toThrow('INVALID_PATH_CHARS');
      expect(() => PathValidator.validate('project:id', 'projectId'))
        .toThrow('INVALID_PATH_CHARS');
    });
  });
});
```

### 5.3 結合テスト
- E2E: ワークフロー生成 → 永続化 → サーバー再起動 → 復元
- 異常系: ディスクフル、権限エラー、破損ファイル
- **容量管理: 閾値超過 → クリーンアップ → 正常保存**【必須】

### 5.3 受入テスト
```python
def test_workflow_persistence_after_restart():
    # 1. ワークフローを生成
    response = generate_workflow()
    workflow_id = response['workflow_id']

    # 2. ファイルが作成されたことを確認
    assert os.path.exists(f'generated/workflows/{project_id}/{workflow_id}.json')

    # 3. サーバーを再起動
    restart_server()

    # 4. ワークフローが復元されたことを確認
    workflows = get_workflows(project_id)
    assert workflow_id in [w['id'] for w in workflows]
```

## 6. 移行計画

### 6.1 後方互換性
- 既存の Registry ベースのコードは動作継続
- Storage は追加レイヤーとして実装

### 6.2 段階的リリース
1. **v1**: Logger 実装（他の改善にも活用可能）
2. **v2**: WorkflowStorage 実装（Registry と並行動作）
3. **v3**: 完全統合（起動時復元を含む）

## 7. リスクと対策

### 7.1 リスク
1. **ディスク容量**: 大量のワークフローでディスクフル
2. **パフォーマンス**: ファイルI/Oによる遅延
3. **データ整合性**: Registry と Storage の不整合

### 7.2 対策
1. **容量管理**:
   - 古いワークフローの自動削除
   - 圧縮オプション

2. **パフォーマンス**:
   - 非同期I/O
   - バッチ処理

3. **整合性**:
   - トランザクション的な更新
   - 定期的な整合性チェック

## 8. 成功基準

### 8.1 機能要件
1. ✅ ワークフローがファイルに永続化される
2. ✅ サーバー再起動後も使用可能
3. ✅ 既存機能への影響なし
4. ✅ ログから問題を診断可能
5. ✅ 単体テストカバレッジ 90%以上

### 8.2 セキュリティ要件【必須】
6. ✅ パストラバーサル攻撃を防御できる
7. ✅ プロトタイプ汚染攻撃を防御できる
8. ✅ 不正な文字を含むIDを拒否できる
9. ✅ ファイル権限が適切に設定される

### 8.3 容量管理要件【必須】
10. ✅ 総使用量が設定上限を超えない
11. ✅ 閾値超過時に自動クリーンアップが動作する
12. ✅ クリーンアップ後も重要なワークフローが保持される
13. ✅ 容量メトリクスがログ出力される

## 9. 参考資料

- Issue #363: taskflowEngine 基本設計
- graphAiServer の永続化実装: `graphAiServer/src/api/v2/workflows.ts`
- 既存の Registry 実装: `mySwiftAgentCore/src/taskflowEngine/registry/`

---

作成日: 2024-01-17
作成者: PM (Claude Code)
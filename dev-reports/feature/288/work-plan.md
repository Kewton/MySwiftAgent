# 作業計画書: Issue #288 - Project一覧・詳細画面

## 1. 概要

| 項目 | 内容 |
|------|------|
| Issue番号 | #288 |
| タイトル | [myAgentDesk] #279-4: Project一覧・詳細画面 |
| 親Issue | #279 myAgentDesk MVP再構築 |
| Phase | Phase 2 - Project・Workbench管理 |
| 見積もり工数 | 12時間（1.5日） |
| 優先度 | P1 (High) |

### 1.1 依存関係

```
Phase 1 (Foundation) - 完了済み
├── #285: SvelteKit Routing Foundation ✅
├── #286: Drizzle ORM + SQLite ✅
└── #287: APIクライアント境界 ✅

Phase 2 (本Issue)
└── #288: Project一覧・詳細画面 ← 今回の作業
    └── ブロック対象: #289 (Workbench一覧・詳細画面)
```

### 1.2 現状分析

Phase 1で実装済みの基盤:

| 領域 | 実装状況 | ファイル |
|------|---------|---------|
| ルーティング | ✅ スケルトン実装 | `src/routes/projects/**/*.svelte` |
| DBスキーマ | ✅ 完了 | `src/lib/server/db/schema.ts` |
| APIクライアント | ✅ 完了 | `src/lib/api/clients/*.ts` |
| Project Guard | ✅ 基本実装 | `src/lib/guards/project-guard.ts` |

**Issue #288で必要な作業**:
- ハードコードからDB/API取得への移行
- Project詳細ダッシュボードの機能実装
- Vault設定画面のmyVault API統合
- Project Guardの実際のDB検証組み込み

---

## 2. スコープ定義

### 2.1 実装対象画面

| 画面 | URL | 機能 |
|------|-----|------|
| Project一覧 | `/projects` | カード表示、Workbench数、新規作成モーダル |
| Project詳細 | `/projects/:projectId` | 概要、All Runs、All Schedules |
| Vault設定 | `/projects/:projectId/vault` | シークレット一覧、疎通確認 |

### 2.2 対象外（Out of Scope）

- Workbench画面（Issue #289で実装）
- Project新規作成のバックエンド処理（モーダルUIのみ）
- 認証・認可機能
- レスポンシブデザイン最適化（Issue #296で実装）

---

## 3. 技術設計

### 3.1 データフロー

```
Browser Request
      │
      ▼
+page.server.ts (SSR)
├── DB Query (Project)
├── API Call (JobQueue - Runs)
├── API Call (MyScheduler - Schedules)
└── API Call (MyVault - Secrets)
      │
      ▼
+page.svelte (CSR)
├── $state for local UI state
├── $derived for computed values
└── Components rendering
```

### 3.2 ファイル構成

```
src/
├── routes/projects/
│   ├── +page.svelte              # Project一覧（更新）
│   ├── +page.server.ts           # 新規: サーバーサイドデータ取得
│   ├── [projectId]/
│   │   ├── +layout.svelte        # Project共通レイアウト（更新）
│   │   ├── +layout.server.ts     # 新規: Project Guard適用
│   │   ├── +page.svelte          # Project詳細（更新）
│   │   ├── +page.server.ts       # 新規: ダッシュボードデータ
│   │   └── vault/
│   │       ├── +page.svelte      # Vault設定（更新）
│   │       └── +page.server.ts   # 新規: シークレットデータ
├── lib/
│   ├── components/
│   │   └── projects/             # 新規ディレクトリ
│   │       ├── ProjectCard.svelte
│   │       ├── CreateProjectModal.svelte
│   │       ├── ProjectStats.svelte
│   │       ├── RecentRunsList.svelte
│   │       ├── RecentSchedulesList.svelte
│   │       └── SecretsList.svelte
│   └── server/
│       └── repositories/         # 新規ディレクトリ
│           └── project.ts        # Project DB操作
└── tests/
    └── unit/
        └── projects/             # 新規テストディレクトリ
```

### 3.3 型定義

```typescript
// src/lib/types/project.ts

/** Project一覧画面用のデータ */
export interface ProjectListItem {
  id: string;
  name: string;
  description: string | null;
  workbenchCount: number;
  lastSyncedAt: Date | null;
  createdAt: Date;
}

/** Project詳細ダッシュボード用のデータ */
export interface ProjectDashboard {
  project: Project;
  workbenchCount: number;
  recentRuns: RunSummary[];
  activeSchedules: ScheduleSummary[];
  stats: ProjectStats;
}

/** 実行サマリー */
export interface RunSummary {
  id: string;
  workbenchName: string;
  jobVersionLabel: string;
  status: RunStatus;
  startedAt: Date | null;
  completedAt: Date | null;
}

/** スケジュールサマリー */
export interface ScheduleSummary {
  id: string;
  workbenchName: string;
  name: string;
  cronExpression: string;
  isEnabled: boolean;
  nextRunAt: Date | null;
}

/** プロジェクト統計 */
export interface ProjectStats {
  totalRuns: number;
  successRate: number;
  runsLast7Days: number;
  activeSchedules: number;
}
```

### 3.4 DB操作（Repository層）

```typescript
// src/lib/server/repositories/project.ts

import { db } from '$lib/server/db';
import { project, workbench, run, schedule, jobVersion } from '$lib/server/db/schema';
import { eq, desc, and, gte, count, sql } from 'drizzle-orm';

export class ProjectRepository {
  /** 全プロジェクト一覧取得（Workbench数付き） */
  async findAllWithStats(): Promise<ProjectListItem[]> {
    const results = await db
      .select({
        id: project.id,
        name: project.name,
        description: project.description,
        lastSyncedAt: project.lastSyncedAt,
        createdAt: project.createdAt,
        workbenchCount: count(workbench.id)
      })
      .from(project)
      .leftJoin(workbench, eq(workbench.projectId, project.id))
      .groupBy(project.id)
      .orderBy(desc(project.updatedAt));

    return results;
  }

  /** Project詳細（存在確認） */
  async findById(projectId: string): Promise<Project | null> {
    const [result] = await db
      .select()
      .from(project)
      .where(eq(project.id, projectId))
      .limit(1);

    return result ?? null;
  }

  /** 最近のRun一覧（プロジェクト内） */
  async findRecentRuns(projectId: string, limit: number = 10): Promise<RunSummary[]> {
    const results = await db
      .select({
        id: run.id,
        workbenchName: workbench.name,
        jobVersionLabel: jobVersion.versionLabel,
        status: run.status,
        startedAt: run.startedAt,
        completedAt: run.completedAt
      })
      .from(run)
      .innerJoin(workbench, eq(run.workbenchId, workbench.id))
      .innerJoin(jobVersion, eq(run.jobVersionId, jobVersion.id))
      .where(eq(workbench.projectId, projectId))
      .orderBy(desc(run.createdAt))
      .limit(limit);

    return results;
  }

  /** アクティブスケジュール一覧 */
  async findActiveSchedules(projectId: string): Promise<ScheduleSummary[]> {
    const results = await db
      .select({
        id: schedule.id,
        workbenchName: workbench.name,
        name: schedule.name,
        cronExpression: schedule.cronExpression,
        isEnabled: schedule.isEnabled,
        nextRunAt: schedule.nextRunAt
      })
      .from(schedule)
      .innerJoin(workbench, eq(schedule.workbenchId, workbench.id))
      .where(
        and(
          eq(workbench.projectId, projectId),
          eq(schedule.isEnabled, true)
        )
      )
      .orderBy(schedule.nextRunAt);

    return results;
  }
}
```

### 3.5 API統合（Vault）

```typescript
// src/routes/projects/[projectId]/vault/+page.server.ts

import type { PageServerLoad } from './$types';
import { getMyVaultClient } from '$lib/api';

export const load: PageServerLoad = async ({ params, locals }) => {
  const { projectId } = params;

  const vaultClient = getMyVaultClient();

  // プロジェクトのシークレット一覧取得
  const secretsResult = await vaultClient.listSecrets();

  if (!secretsResult.ok) {
    // API接続エラー時は空の状態を返す
    return {
      secrets: [],
      connectionStatus: 'disconnected' as const,
      error: secretsResult.error.message
    };
  }

  // プロジェクトでフィルタリング
  const projectSecrets = secretsResult.value.filter(
    s => s.project === projectId
  );

  // 必須シークレットの設定状況チェック
  const requiredKeys = ['GOOGLE_API_KEY', 'OPENAI_API_KEY'];
  const missingKeys = requiredKeys.filter(
    key => !projectSecrets.some(s => s.key === key)
  );

  return {
    secrets: projectSecrets.map(s => ({
      key: s.key,
      description: s.description,
      createdAt: s.created_at,
      // 値は表示しない（セキュリティ）
      hasValue: Boolean(s.value)
    })),
    connectionStatus: 'connected' as const,
    missingKeys
  };
};
```

---

## 4. 実装フェーズ

### Phase 1: Repository層実装（3時間）

**作業内容**:
1. `src/lib/types/project.ts` - 型定義作成
2. `src/lib/server/repositories/project.ts` - Repository実装
3. 単体テスト作成

**成果物**:
- ProjectRepository クラス
- 型定義ファイル
- テスト（90%以上カバレッジ）

### Phase 2: Project一覧画面（2時間）

**作業内容**:
1. `src/routes/projects/+page.server.ts` - サーバーサイドデータ取得
2. `src/routes/projects/+page.svelte` - 更新（DBデータ表示）
3. `src/lib/components/projects/ProjectCard.svelte` - カードコンポーネント
4. `src/lib/components/projects/CreateProjectModal.svelte` - 新規作成モーダル（UI only）

**成果物**:
- 機能するProject一覧画面
- Workbench数表示
- 新規作成モーダル（UIのみ）

### Phase 3: Project詳細画面（3時間）

**作業内容**:
1. `src/routes/projects/[projectId]/+layout.server.ts` - Project Guard適用
2. `src/routes/projects/[projectId]/+page.server.ts` - ダッシュボードデータ
3. `src/routes/projects/[projectId]/+page.svelte` - 更新
4. コンポーネント作成:
   - `ProjectStats.svelte`
   - `RecentRunsList.svelte`
   - `RecentSchedulesList.svelte`

**成果物**:
- Project詳細ダッシュボード
- All Runs表示
- All Schedules表示
- 統計情報表示

### Phase 4: Vault設定画面（2時間）

**作業内容**:
1. `src/routes/projects/[projectId]/vault/+page.server.ts` - myVault API統合
2. `src/routes/projects/[projectId]/vault/+page.svelte` - 更新
3. `src/lib/components/projects/SecretsList.svelte` - シークレット一覧
4. 疎通確認機能（UIトリガー）

**成果物**:
- シークレット一覧表示
- 疎通確認ボタン（モック実装）
- 設定不足警告表示

### Phase 5: テスト・品質検証（2時間）

**作業内容**:
1. 単体テスト追加・カバレッジ確認
2. ESLint/TypeScriptエラー修正
3. E2Eテストシナリオ作成（Playwright）
4. 手動検証

**品質基準**:
- 単体テストカバレッジ 90%以上
- ESLint/TypeScript エラーゼロ
- ruff/mypy（該当なし - フロントエンドのみ）

---

## 5. テスト計画

### 5.1 単体テスト

| テスト対象 | テストケース数 | カバレッジ目標 |
|-----------|--------------|---------------|
| ProjectRepository | 12 | 95% |
| Project Guard | 6 | 100% |
| コンポーネント | 18 | 85% |

**主要テストケース**:

```typescript
// src/tests/unit/projects/repository.test.ts

describe('ProjectRepository', () => {
  describe('findAllWithStats', () => {
    it('should return all projects with workbench counts', async () => {});
    it('should return empty array when no projects', async () => {});
    it('should order by updatedAt descending', async () => {});
  });

  describe('findById', () => {
    it('should return project when exists', async () => {});
    it('should return null when not found', async () => {});
  });

  describe('findRecentRuns', () => {
    it('should return runs within project', async () => {});
    it('should limit to specified count', async () => {});
    it('should order by createdAt descending', async () => {});
    it('should include workbench and jobVersion info', async () => {});
  });

  describe('findActiveSchedules', () => {
    it('should return only enabled schedules', async () => {});
    it('should filter by projectId', async () => {});
    it('should order by nextRunAt', async () => {});
  });
});
```

### 5.2 統合テスト

```typescript
// src/tests/integration/projects/list.test.ts

describe('GET /projects', () => {
  it('should return project list page', async () => {});
  it('should display workbench counts', async () => {});
});

describe('GET /projects/:projectId', () => {
  it('should return project dashboard', async () => {});
  it('should return 404 for invalid projectId', async () => {});
});

describe('GET /projects/:projectId/vault', () => {
  it('should display secrets list', async () => {});
  it('should show connection status', async () => {});
  it('should warn about missing required keys', async () => {});
});
```

### 5.3 E2Eテスト（Playwright）

```typescript
// tests/e2e/projects.spec.ts

test.describe('Project Management', () => {
  test('should navigate to project list', async ({ page }) => {
    await page.goto('/projects');
    await expect(page.getByRole('heading', { name: 'Projects' })).toBeVisible();
  });

  test('should display project cards', async ({ page }) => {
    await page.goto('/projects');
    const cards = page.locator('.project-card');
    await expect(cards).toHaveCount.greaterThan(0);
  });

  test('should navigate to project detail', async ({ page }) => {
    await page.goto('/projects');
    await page.locator('.project-card').first().click();
    await expect(page).toHaveURL(/\/projects\/[^/]+$/);
  });

  test('should show 404 for invalid project', async ({ page }) => {
    await page.goto('/projects/invalid_id');
    await expect(page.getByText('Project not found')).toBeVisible();
  });

  test('should display vault settings', async ({ page }) => {
    await page.goto('/projects/proj_001/vault');
    await expect(page.getByRole('heading', { name: 'Vault Settings' })).toBeVisible();
  });
});
```

---

## 6. 受入基準

### 6.1 自動検証可能な基準

| 基準 | 検証方法 | 期待結果 |
|------|---------|---------|
| Project一覧表示 | E2Eテスト | 3件以上のプロジェクト表示 |
| Project詳細表示 | E2Eテスト | プロジェクト名、統計表示 |
| Vault設定表示 | E2Eテスト | シークレット一覧表示 |
| 404エラー | E2Eテスト | 無効IDで404画面 |
| 単体テストカバレッジ | vitest --coverage | 90%以上 |
| ESLint | npm run lint | エラー0件 |
| TypeScript | npm run type-check | エラー0件 |

### 6.2 手動検証が必要な基準

| 基準 | 確認項目 |
|------|---------|
| UX/UIデザイン | カードホバーエフェクト |
| UX/UIデザイン | モーダルアニメーション |
| Vault機能 | 疎通確認ボタン動作 |
| 警告表示 | 設定不足時のバッジ表示 |

---

## 7. リスクと対策

| リスク | 影響度 | 対策 |
|--------|--------|------|
| Phase 1未完了 | 高 | 現状確認 → 完了済み確認 |
| API接続エラー | 中 | Mock実装でフォールバック |
| DB接続エラー | 中 | エラーハンドリング実装 |
| パフォーマンス | 低 | クエリ最適化、インデックス確認 |

---

## 8. L3受入テスト計画【必須】

### Step 1: サービス起動確認

```bash
# サービス起動
./scripts/dev-start.sh

# ヘルスチェック
curl -sf http://localhost:8000/api/health && echo "✅ myAgentDesk: healthy"
curl -sf http://localhost:8103/health && echo "✅ myVault: healthy"
```

### Step 2: Project一覧画面の確認

```bash
# Project一覧ページ取得
curl -s http://localhost:8000/projects \
  -w "\nHTTP Status: %{http_code}\n" \
  | head -50

# 期待: HTTP Status: 200, HTML containing "Projects"
```

### Step 3: Project詳細画面の確認

```bash
# Project詳細ページ取得（有効なprojectId）
curl -s http://localhost:8000/projects/proj_001 \
  -w "\nHTTP Status: %{http_code}\n" \
  | head -50

# 期待: HTTP Status: 200, HTML containing project name

# 無効なprojectIdで404確認
curl -s http://localhost:8000/projects/invalid_project_id \
  -w "\nHTTP Status: %{http_code}\n"

# 期待: HTTP Status: 404
```

### Step 4: Vault設定画面の確認

```bash
# Vault設定ページ取得
curl -s http://localhost:8000/projects/proj_001/vault \
  -w "\nHTTP Status: %{http_code}\n" \
  | head -50

# 期待: HTTP Status: 200, HTML containing "Vault Settings"
```

### Step 5: myVault API連携確認

```bash
# myVault API経由でシークレット一覧取得
curl -s http://localhost:8103/api/secrets \
  -H "X-Service: myAgentDesk" \
  -H "X-Token: ${MYVAULT_SERVICE_TOKEN}" \
  | head -30

# 期待: JSON array of secrets
```

### Step 6: エビデンス収集

```bash
# レスポンスをファイルに保存
curl -s http://localhost:8000/projects > /tmp/projects_list.html
curl -s http://localhost:8000/projects/proj_001 > /tmp/project_detail.html
curl -s http://localhost:8000/projects/proj_001/vault > /tmp/vault_settings.html

echo "✅ Evidence saved to /tmp/"
```

---

## 9. 参照ドキュメント

| ドキュメント | 用途 |
|-------------|------|
| [design-policy.md](../279/design-policy.md) | アーキテクチャ設計方針 |
| [issue-split.md](../279/issue-split.md) | Issue分割詳細 |
| [API_REFERENCE.md](../../expertAgent/docs/API_REFERENCE.md) | ExpertAgent API仕様 |
| [service-dependencies.md](../../docs/arch/service-dependencies.md) | サービス間依存関係 |
| [screen-transition.md](../../docs/design/screen-transition.md) | 画面遷移設計 |

---

## 10. 完了定義

以下がすべて満たされた時点で完了:

- [ ] Project一覧画面がDBデータを表示
- [ ] Project詳細ダッシュボードが統計情報を表示
- [ ] Vault設定画面がmyVault APIと連携
- [ ] Project Guardが無効IDで404を返す
- [ ] 単体テストカバレッジ90%以上
- [ ] ESLint/TypeScriptエラー0件
- [ ] E2Eテストがすべてパス
- [ ] コードレビュー完了
- [ ] developブランチにマージ

---

## 11. 作業ログ

| 日時 | 作業内容 | 担当 |
|------|---------|------|
| - | 作業計画書作成 | Claude |

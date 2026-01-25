# 作業計画書: Issue #289 - Workbench一覧・詳細画面

## 1. 概要

| 項目 | 内容 |
|------|------|
| Issue番号 | #289 |
| タイトル | [myAgentDesk] #279-5: Workbench一覧・詳細画面 |
| 親Issue | #279 myAgentDesk MVP再構築 |
| Phase | Phase 2 - Project・Workbench管理 |
| 見積もり工数 | 12時間（1.5日） |
| 優先度 | P1 (High) |

### 1.1 依存関係

```
Phase 1 (Foundation) - 完了済み
├── #285: SvelteKit Routing Foundation ✅
├── #286: Drizzle ORM + SQLite ✅
└── #287: APIクライアント境界 ✅ (間接依存: #288経由)

Phase 2 (本Issue)
├── #288: Project一覧・詳細画面 ← 直接依存先
└── #289: Workbench一覧・詳細画面 ← 今回の作業
    └── ブロック対象: #290 (Requirements編集)
```

**依存関係の詳細**:
- **直接依存**: #285 (Routing), #286 (DB), #288 (Project画面)
- **間接依存**: #287 (APIクライアント) - #288経由で利用
- **issue-split.md準拠**: #279-5の依存先は #279-1, #279-2, #279-4

### 1.2 現状分析

Phase 1で実装済みの基盤:

| 領域 | 実装状況 | ファイル |
|------|---------|---------|
| Workbench一覧 | ✅ スケルトン実装 | `workbenches/+page.svelte` |
| Workbench詳細 | ✅ リダイレクトのみ | `workbenches/[workbenchId]/+page.svelte` |
| タブナビゲーション | ✅ 完了 | `WorkbenchTabs.svelte` |
| NextActionBar | ✅ 完了 | `NextActionBar.svelte` |
| Workbench Guard | ✅ モック実装 | `workbench-guard.ts` |
| DBスキーマ | ✅ 完了 | `schema.ts` |

**Issue #289で必要な作業**:
- Workbench一覧: ハードコード→DB取得、ステータス/フィルタリング追加
- Workbench詳細: 概要パネル実装（リダイレクトではなく）
- Workbench Guard: 実際のDB検証への移行
- 新規作成モーダル（UIのみ）

---

## 2. スコープ定義

### 2.1 実装対象画面

| 画面 | URL | 機能 |
|------|-----|------|
| Workbench一覧 | `/projects/:projectId/workbenches` | カード表示、ステータス、フィルタリング、新規作成 |
| Workbench詳細 | `/projects/:projectId/workbenches/:workbenchId` | 概要パネル、タブナビゲーション、NextActionBar |

### 2.2 対象外（Out of Scope）

- Requirements編集画面（Issue #290で実装）
- Job生成・レビュー（Issue #291で実装）
- スケジュール管理（Issue #297で実装）
- Workbench新規作成のバックエンド処理（UIのみ）

---

## 3. 技術設計

### 3.1 URL駆動状態管理

```typescript
// Workbench一覧のフィルタリング
// URL: /projects/proj_001/workbenches?status=active

import { page } from '$app/stores';
import { goto } from '$app/navigation';

// フィルター状態の読み取り
const statusFilter = $derived($page.url.searchParams.get('status') || 'all');

// フィルター変更
function setFilter(status: string) {
  const url = new URL($page.url);
  if (status === 'all') {
    url.searchParams.delete('status');
  } else {
    url.searchParams.set('status', status);
  }
  goto(url.toString(), { replaceState: true });
}
```

### 3.2 データフロー

```
Browser Request: /projects/:projectId/workbenches
      │
      ▼
+page.server.ts (SSR)
├── DB Query (Workbench list with stats)
├── URL params (status filter)
└── Computed stats (runs, schedules count)
      │
      ▼
+page.svelte (CSR)
├── $state for local UI state (modal open)
├── $derived for filtered list
├── $derived for status counts
└── Components rendering
```

### 3.3 ファイル構成

```
src/
├── routes/projects/[projectId]/workbenches/
│   ├── +page.svelte              # 更新: フィルタリング、DB連携
│   ├── +page.server.ts           # 新規: サーバーサイドデータ取得
│   └── [workbenchId]/
│       ├── +layout.svelte        # 更新: 概要パネル追加
│       ├── +layout.server.ts     # 更新: DB検証
│       └── +page.svelte          # 更新: 概要ダッシュボード
├── lib/
│   ├── components/
│   │   └── workbenches/          # 新規ディレクトリ
│   │       ├── WorkbenchCard.svelte
│   │       ├── WorkbenchStatusFilter.svelte
│   │       ├── CreateWorkbenchModal.svelte
│   │       ├── WorkbenchOverview.svelte
│   │       └── WorkbenchStats.svelte
│   ├── guards/
│   │   └── workbench-guard.ts    # 更新: DB検証統合
│   └── server/
│       └── repositories/
│           └── workbench.ts      # 新規: Workbench DB操作
└── tests/
    └── unit/
        └── workbenches/          # 新規テストディレクトリ
```

### 3.4 型定義

```typescript
// src/lib/types/workbench.ts

/** Workbench一覧画面用のデータ */
export interface WorkbenchListItem {
  id: string;
  name: string;
  description: string | null;
  status: WorkbenchStatus;
  activeRequirementVersionId: string | null;
  runCount: number;
  lastRunAt: Date | null;
  lastRunStatus: RunStatus | null;
  scheduleCount: number;
  createdAt: Date;
  updatedAt: Date;
}

/** Workbench詳細用のデータ */
export interface WorkbenchDetail {
  id: string;
  name: string;
  description: string | null;
  status: WorkbenchStatus;
  projectId: string;
  activeRequirementVersion: RequirementVersionSummary | null;
  currentJobVersion: JobVersionSummary | null;
  stats: WorkbenchStats;
}

/** Workbench統計 */
export interface WorkbenchStats {
  totalRuns: number;
  successfulRuns: number;
  failedRuns: number;
  successRate: number;
  lastRunAt: Date | null;
  activeSchedules: number;
  pendingRuns: number;
}

/** ステータス別カウント */
export interface WorkbenchStatusCounts {
  all: number;
  active: number;
  draft: number;
  archived: number;
}

/** フィルター状態 */
export type WorkbenchStatusFilter = 'all' | WorkbenchStatus;
```

### 3.5 DB操作（Repository層）

```typescript
// src/lib/server/repositories/workbench.ts

import { db } from '$lib/server/db';
import { workbench, run, schedule, requirementVersion, jobVersion } from '$lib/server/db/schema';
import { eq, desc, and, count, sql } from 'drizzle-orm';

export class WorkbenchRepository {
  /** プロジェクト内のWorkbench一覧取得（統計付き）
   *
   * N+1問題対策: ウィンドウ関数とサブクエリを使用して1回のクエリで取得
   */
  async findByProjectWithStats(projectId: string): Promise<WorkbenchListItem[]> {
    // サブクエリで実行数とスケジュール数を集計
    const runCountSubquery = db
      .select({
        workbenchId: run.workbenchId,
        runCount: count(run.id).as('run_count')
      })
      .from(run)
      .groupBy(run.workbenchId)
      .as('run_stats');

    const scheduleCountSubquery = db
      .select({
        workbenchId: schedule.workbenchId,
        scheduleCount: count(schedule.id).as('schedule_count')
      })
      .from(schedule)
      .where(eq(schedule.isEnabled, true))
      .groupBy(schedule.workbenchId)
      .as('schedule_stats');

    // N+1対策: 最新Run情報をウィンドウ関数で取得するサブクエリ
    // ROW_NUMBER() OVER (PARTITION BY workbench_id ORDER BY created_at DESC)
    const latestRunSubquery = db
      .select({
        workbenchId: run.workbenchId,
        status: run.status,
        completedAt: run.completedAt,
        rowNum: sql<number>`ROW_NUMBER() OVER (PARTITION BY ${run.workbenchId} ORDER BY ${run.createdAt} DESC)`.as('row_num')
      })
      .from(run)
      .as('latest_run_ranked');

    // 最新Run（row_num = 1）のみをフィルタ
    const latestRunFiltered = db
      .select({
        workbenchId: latestRunSubquery.workbenchId,
        lastRunStatus: latestRunSubquery.status,
        lastRunAt: latestRunSubquery.completedAt
      })
      .from(latestRunSubquery)
      .where(eq(latestRunSubquery.rowNum, 1))
      .as('latest_run');

    // 1回のクエリで全データを取得（N+1問題回避）
    const results = await db
      .select({
        id: workbench.id,
        name: workbench.name,
        description: workbench.description,
        status: workbench.status,
        activeRequirementVersionId: workbench.activeRequirementVersionId,
        createdAt: workbench.createdAt,
        updatedAt: workbench.updatedAt,
        runCount: sql<number>`COALESCE(${runCountSubquery.runCount}, 0)`,
        scheduleCount: sql<number>`COALESCE(${scheduleCountSubquery.scheduleCount}, 0)`,
        lastRunAt: latestRunFiltered.lastRunAt,
        lastRunStatus: latestRunFiltered.lastRunStatus
      })
      .from(workbench)
      .leftJoin(runCountSubquery, eq(workbench.id, runCountSubquery.workbenchId))
      .leftJoin(scheduleCountSubquery, eq(workbench.id, scheduleCountSubquery.workbenchId))
      .leftJoin(latestRunFiltered, eq(workbench.id, latestRunFiltered.workbenchId))
      .where(eq(workbench.projectId, projectId))
      .orderBy(desc(workbench.updatedAt));

    return results;
  }

  /** Workbench詳細取得 */
  async findByIdWithDetail(workbenchId: string): Promise<WorkbenchDetail | null> {
    const [wb] = await db
      .select()
      .from(workbench)
      .where(eq(workbench.id, workbenchId))
      .limit(1);

    if (!wb) return null;

    // 関連データ取得
    const [activeReq] = wb.activeRequirementVersionId
      ? await db
          .select()
          .from(requirementVersion)
          .where(eq(requirementVersion.id, wb.activeRequirementVersionId))
          .limit(1)
      : [null];

    // 統計情報
    const stats = await this.getWorkbenchStats(workbenchId);

    // 現在のJobVersion
    const [currentJob] = await db
      .select()
      .from(jobVersion)
      .where(and(
        eq(jobVersion.workbenchId, workbenchId),
        eq(jobVersion.status, 'active')
      ))
      .orderBy(desc(jobVersion.createdAt))
      .limit(1);

    return {
      ...wb,
      activeRequirementVersion: activeReq
        ? { id: activeReq.id, version: activeReq.version, status: activeReq.status }
        : null,
      currentJobVersion: currentJob
        ? { id: currentJob.id, versionLabel: currentJob.versionLabel, status: currentJob.status }
        : null,
      stats
    };
  }

  /** Workbench統計取得 */
  private async getWorkbenchStats(workbenchId: string): Promise<WorkbenchStats> {
    const [runStats] = await db
      .select({
        total: count(run.id),
        successful: sql<number>`SUM(CASE WHEN ${run.status} = 'success' THEN 1 ELSE 0 END)`,
        failed: sql<number>`SUM(CASE WHEN ${run.status} = 'failed' THEN 1 ELSE 0 END)`,
        pending: sql<number>`SUM(CASE WHEN ${run.status} IN ('queued', 'running') THEN 1 ELSE 0 END)`
      })
      .from(run)
      .where(eq(run.workbenchId, workbenchId));

    const [scheduleStats] = await db
      .select({
        active: count(schedule.id)
      })
      .from(schedule)
      .where(and(
        eq(schedule.workbenchId, workbenchId),
        eq(schedule.isEnabled, true)
      ));

    const [lastRun] = await db
      .select({ completedAt: run.completedAt })
      .from(run)
      .where(eq(run.workbenchId, workbenchId))
      .orderBy(desc(run.completedAt))
      .limit(1);

    const total = runStats?.total ?? 0;
    const successful = runStats?.successful ?? 0;

    return {
      totalRuns: total,
      successfulRuns: successful,
      failedRuns: runStats?.failed ?? 0,
      successRate: total > 0 ? Math.round((successful / total) * 100) : 0,
      lastRunAt: lastRun?.completedAt ?? null,
      activeSchedules: scheduleStats?.active ?? 0,
      pendingRuns: runStats?.pending ?? 0
    };
  }

  /** ステータス別カウント取得 */
  async getStatusCounts(projectId: string): Promise<WorkbenchStatusCounts> {
    const results = await db
      .select({
        status: workbench.status,
        count: count(workbench.id)
      })
      .from(workbench)
      .where(eq(workbench.projectId, projectId))
      .groupBy(workbench.status);

    const counts: WorkbenchStatusCounts = { all: 0, active: 0, draft: 0, archived: 0 };
    for (const r of results) {
      counts[r.status as keyof Omit<WorkbenchStatusCounts, 'all'>] = r.count;
      counts.all += r.count;
    }

    return counts;
  }
}
```

### 3.6 Workbench概要パネル

```svelte
<!-- src/lib/components/workbenches/WorkbenchOverview.svelte -->

<script lang="ts">
  import type { WorkbenchDetail } from '$lib/types/workbench';

  interface Props {
    workbench: WorkbenchDetail;
  }

  let { workbench }: Props = $props();

  const statusBadgeClass = $derived({
    draft: 'badge-draft',
    active: 'badge-active',
    archived: 'badge-archived'
  }[workbench.status]);

  const successRateColor = $derived(
    workbench.stats.successRate >= 80 ? 'text-green-600' :
    workbench.stats.successRate >= 50 ? 'text-yellow-600' : 'text-red-600'
  );
</script>

<div class="overview-panel">
  <div class="overview-header">
    <h2>{workbench.name}</h2>
    <span class="status-badge {statusBadgeClass}">{workbench.status}</span>
  </div>

  {#if workbench.description}
    <p class="description">{workbench.description}</p>
  {/if}

  <div class="stats-grid">
    <div class="stat-card">
      <span class="stat-label">Total Runs</span>
      <span class="stat-value">{workbench.stats.totalRuns}</span>
    </div>
    <div class="stat-card">
      <span class="stat-label">Success Rate</span>
      <span class="stat-value {successRateColor}">{workbench.stats.successRate}%</span>
    </div>
    <div class="stat-card">
      <span class="stat-label">Active Schedules</span>
      <span class="stat-value">{workbench.stats.activeSchedules}</span>
    </div>
    <div class="stat-card">
      <span class="stat-label">Pending Runs</span>
      <span class="stat-value">{workbench.stats.pendingRuns}</span>
    </div>
  </div>

  {#if workbench.activeRequirementVersion}
    <div class="version-info">
      <span class="version-label">Active Requirements:</span>
      <span class="version-value">v{workbench.activeRequirementVersion.version}</span>
    </div>
  {/if}

  {#if workbench.currentJobVersion}
    <div class="version-info">
      <span class="version-label">Current Job:</span>
      <span class="version-value">{workbench.currentJobVersion.versionLabel}</span>
    </div>
  {/if}
</div>
```

---

## 4. 実装フェーズ

### Phase 1: Repository層実装（2.5時間）

**作業内容**:
1. `src/lib/types/workbench.ts` - 型定義作成
2. `src/lib/server/repositories/workbench.ts` - Repository実装
3. 単体テスト作成

**成果物**:
- WorkbenchRepository クラス
- 型定義ファイル
- テスト（90%以上カバレッジ）

### Phase 2: Workbench一覧画面（3時間）

**作業内容**:
1. `src/routes/.../workbenches/+page.server.ts` - サーバーサイドデータ取得
2. `src/routes/.../workbenches/+page.svelte` - 更新（DB連携、フィルタリング）
3. コンポーネント作成:
   - `WorkbenchCard.svelte` - ステータス、統計表示付きカード
   - `WorkbenchStatusFilter.svelte` - フィルターUI
   - `CreateWorkbenchModal.svelte` - 新規作成モーダル（UI）

**成果物**:
- 機能するWorkbench一覧画面
- ステータスフィルタリング
- ステータス別カウント表示

### Phase 3: Workbench詳細・概要パネル（3時間）

**作業内容**:
1. `src/routes/.../[workbenchId]/+layout.server.ts` - 更新（DB検証）
2. `src/routes/.../[workbenchId]/+page.svelte` - 概要ダッシュボード
3. コンポーネント作成:
   - `WorkbenchOverview.svelte` - 概要パネル
   - `WorkbenchStats.svelte` - 統計表示

**成果物**:
- Workbench詳細概要パネル
- 統計情報表示
- バージョン情報表示

### Phase 4: Workbench Guard強化（1.5時間）

**作業内容**:
1. `src/lib/guards/workbench-guard.ts` - DB検証統合
2. Project所属確認の強化
3. エラーハンドリング改善

**成果物**:
- DB検証によるWorkbench Guard
- セキュリティ強化（Project不一致で404）

### Phase 5: テスト・品質検証（2時間）

**作業内容**:
1. 単体テスト追加・カバレッジ確認
2. ESLint/TypeScriptエラー修正
3. E2Eテストシナリオ作成（Playwright）
4. 手動検証

**品質基準**:
- 単体テストカバレッジ 90%以上
- ESLint/TypeScript エラーゼロ

---

## 5. テスト計画

### 5.1 単体テスト

| テスト対象 | テストケース数 | カバレッジ目標 |
|-----------|--------------|---------------|
| WorkbenchRepository | 15 | 95% |
| Workbench Guard | 8 | 100% |
| コンポーネント | 20 | 85% |

**主要テストケース**:

```typescript
// src/tests/unit/workbenches/repository.test.ts

describe('WorkbenchRepository', () => {
  describe('findByProjectWithStats', () => {
    it('should return workbenches for specified project', async () => {});
    it('should include run count', async () => {});
    it('should include schedule count', async () => {});
    it('should include last run info', async () => {});
    it('should order by updatedAt descending', async () => {});
    it('should return empty array when no workbenches', async () => {});
  });

  describe('findByIdWithDetail', () => {
    it('should return workbench with stats', async () => {});
    it('should include active requirement version', async () => {});
    it('should include current job version', async () => {});
    it('should return null when not found', async () => {});
  });

  describe('getStatusCounts', () => {
    it('should return counts per status', async () => {});
    it('should include total (all) count', async () => {});
  });
});

// src/tests/unit/guards/workbench-guard.test.ts

describe('validateWorkbenchAccess', () => {
  it('should return valid for existing workbench', () => {});
  it('should return error for null workbench', () => {});
  it('should return error for ID mismatch', () => {});
  it('should return error for project mismatch (security)', () => {});
  it('should return 404 for all error cases', () => {});
});
```

### 5.2 E2Eテスト（Playwright）

```typescript
// tests/e2e/workbenches.spec.ts

test.describe('Workbench Management', () => {
  test('should display workbench list', async ({ page }) => {
    await page.goto('/projects/proj_001/workbenches');
    await expect(page.getByRole('heading', { name: 'Workbenches' })).toBeVisible();
    const cards = page.locator('.workbench-card');
    await expect(cards).toHaveCount.greaterThan(0);
  });

  test('should filter by status', async ({ page }) => {
    await page.goto('/projects/proj_001/workbenches');
    await page.getByRole('button', { name: 'Active' }).click();
    await expect(page).toHaveURL(/status=active/);
  });

  test('should navigate to workbench detail', async ({ page }) => {
    await page.goto('/projects/proj_001/workbenches');
    await page.locator('.workbench-card').first().click();
    await expect(page).toHaveURL(/\/workbenches\/[^/]+/);
  });

  test('should show tabs on workbench detail', async ({ page }) => {
    await page.goto('/projects/proj_001/workbenches/wb_001');
    await expect(page.getByRole('link', { name: 'Requirements' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Generate' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Runs' })).toBeVisible();
  });

  test('should update URL when clicking tabs', async ({ page }) => {
    await page.goto('/projects/proj_001/workbenches/wb_001/requirements');
    await page.getByRole('link', { name: 'Review' }).click();
    await expect(page).toHaveURL(/\/review$/);
  });

  test('should show 404 for invalid workbench', async ({ page }) => {
    await page.goto('/projects/proj_001/workbenches/invalid_id');
    await expect(page.getByText('Workbench not found')).toBeVisible();
  });

  test('should show 404 for project mismatch', async ({ page }) => {
    // proj_002のWorkbenchにproj_001のURLでアクセス
    await page.goto('/projects/proj_001/workbenches/wb_from_proj_002');
    await expect(page.getByText('Workbench not found')).toBeVisible();
  });
});
```

---

## 6. 受入基準

### 6.1 自動検証可能な基準

| 基準 | 検証方法 | 期待結果 |
|------|---------|---------|
| Workbench一覧表示 | E2Eテスト | 5件以上のWorkbench表示 |
| フィルタリング | E2Eテスト | URL変化、表示更新 |
| タブナビゲーション | E2Eテスト | URL変化、タブアクティブ |
| 404エラー（無効ID） | E2Eテスト | 404画面表示 |
| 404エラー（Project不一致） | E2Eテスト | 404画面表示 |
| 単体テストカバレッジ | vitest --coverage | 90%以上 |
| ESLint | npm run lint | エラー0件 |
| TypeScript | npm run type-check | エラー0件 |

### 6.2 手動検証が必要な基準

| 基準 | 確認項目 |
|------|---------|
| UX/UIデザイン | タブ切り替えアニメーション |
| UX/UIデザイン | カードホバーエフェクト |
| NextActionBar | 現在の状態に応じた変化 |
| ブックマーク | 同じタブが開く |
| フィルター | ブラウザバックで状態復元 |

---

## 7. L3受入テスト計画

### Step 1: サービス起動確認

```bash
# サービス起動
./scripts/dev-start.sh

# ヘルスチェック
curl -sf http://localhost:8000/api/health && echo "✅ myAgentDesk: healthy"
```

### Step 2: 画面アクセス確認

```bash
# Workbench一覧
curl -s http://localhost:8000/projects/proj_001/workbenches \
  -w "\nHTTP Status: %{http_code}\n" \
  | head -50

# 期待: HTTP Status: 200, HTML containing "Workbenches"

# Workbench詳細
curl -s http://localhost:8000/projects/proj_001/workbenches/wb_001 \
  -w "\nHTTP Status: %{http_code}\n" \
  | head -50

# 期待: HTTP Status: 200 または 302 (redirect to requirements)
```

### Step 3: フィルタリング確認

```bash
# ステータスフィルター
curl -s "http://localhost:8000/projects/proj_001/workbenches?status=active" \
  -w "\nHTTP Status: %{http_code}\n" \
  | head -30

# 期待: HTTP Status: 200, フィルタリングされたリスト
```

### Step 4: セキュリティ確認

```bash
# 無効なWorkbench ID
curl -s http://localhost:8000/projects/proj_001/workbenches/invalid_id \
  -w "\nHTTP Status: %{http_code}\n"

# 期待: HTTP Status: 404

# Project不一致
curl -s http://localhost:8000/projects/proj_002/workbenches/wb_001 \
  -w "\nHTTP Status: %{http_code}\n"

# 期待: HTTP Status: 404 (セキュリティ：情報漏洩防止)
```

---

## 8. リスクと対策

| リスク | 影響度 | 対策 |
|--------|--------|------|
| Issue #288未完了 | 高 | Project Guard依存確認 |
| DB接続エラー | 中 | エラーハンドリング実装 |
| パフォーマンス | 中 | クエリ最適化、N+1回避 |
| タブ遷移遅延 | 低 | prefetch活用 |

---

## 9. 参照ドキュメント

| ドキュメント | 用途 |
|-------------|------|
| [design-policy.md](../279/design-policy.md) | URL駆動状態管理 |
| [issue-split.md](../279/issue-split.md) | Issue分割詳細 |
| [screen-transition.md](../../docs/design/screen-transition.md) | 画面遷移設計 |
| [schema.ts](../../myAgentDesk/src/lib/server/db/schema.ts) | DBスキーマ |

---

## 10. 完了定義

以下がすべて満たされた時点で完了:

- [ ] Workbench一覧がDBデータを表示
- [ ] ステータスフィルタリングがURL駆動で動作
- [ ] Workbench詳細が概要パネルを表示
- [ ] タブナビゲーションがURL更新
- [ ] Workbench Guardが無効ID/Project不一致で404を返す
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

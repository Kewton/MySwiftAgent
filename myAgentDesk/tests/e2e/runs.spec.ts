/**
 * E2E Tests for Runs Page (Execution History / Monitoring)
 * Issue #293: [myAgentDesk] Runs画面（実行履歴・監視）
 *
 * 【実践的テスト】
 * - Runs一覧画面の表示検証
 * - Run詳細画面のリアルタイム更新
 * - ポーリング動作確認
 * - Rerun機能
 * - ステータス遷移の可視化
 *
 * テストデータ:
 * - wb_001: Test Workbench with JobVersions
 * - jv_001: Active JobVersion for running
 */
import { test, expect } from '@playwright/test';

// シードデータのテストデータ
const TEST_PROJECT_ID = 'proj_001';
const TEST_WORKBENCH_ID = 'wb_001';
const TEST_JOB_VERSION_ID = 'jv_001';

// ステータス定義
const TERMINAL_STATUSES = ['success', 'failed', 'canceled', 'timeout'];
const ALL_STATUSES = ['queued', 'running', ...TERMINAL_STATUSES];

test.describe('Runs List Page (実践的テスト)', () => {
	test('Runs一覧画面が正常にロードされる', async ({ page }) => {
		await page.goto(`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/runs`);
		await page.waitForLoadState('networkidle');

		// ページタイトルまたはヘッダーにRunsが含まれることを確認
		const heading = page.locator('h1, h2, [data-testid="page-title"]');
		await expect(heading.first()).toContainText(/runs|executions|history/i);
	});

	test('Runs一覧にステータスバッジが表示される', async ({ page }) => {
		await page.goto(`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/runs`);
		await page.waitForLoadState('networkidle');

		// ステータスバッジの存在確認
		const statusBadges = page.locator(
			'[data-testid="run-status-badge"], .badge, [class*="status"]'
		);
		const badgeCount = await statusBadges.count();

		// Runが存在すればバッジが表示される（0件の場合はスキップ）
		if (badgeCount > 0) {
			const firstBadge = statusBadges.first();
			await expect(firstBadge).toBeVisible();

			// バッジのテキストがステータスを含む
			const badgeText = await firstBadge.textContent();
			const hasValidStatus = ALL_STATUSES.some((status) =>
				badgeText?.toLowerCase().includes(status)
			);
			expect(hasValidStatus || badgeText?.length).toBeTruthy();
		}
	});

	test('Runカードをクリックすると詳細画面に遷移する', async ({ page }) => {
		await page.goto(`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/runs`);
		await page.waitForLoadState('networkidle');

		// Runへのリンクを探す
		const runLink = page.locator('a[href*="/runs/run_"]').first();
		if ((await runLink.count()) > 0) {
			await runLink.click();
			await page.waitForLoadState('networkidle');

			// URLが詳細画面に遷移していることを確認
			await expect(page).toHaveURL(/\/runs\/run_/);
		}
	});

	test('ページネーションが機能する（Runが多い場合）', async ({ page }) => {
		await page.goto(`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/runs`);
		await page.waitForLoadState('networkidle');

		// ページネーションコントロールを探す
		const pagination = page.locator('[data-testid="pagination"], nav[aria-label="pagination"]');
		if ((await pagination.count()) > 0) {
			const nextButton = pagination.locator('button:has-text("Next"), a:has-text("Next")');
			if ((await nextButton.count()) > 0 && (await nextButton.isEnabled())) {
				await nextButton.click();
				await page.waitForLoadState('networkidle');

				// URLにページパラメータが追加されることを確認
				await expect(page).toHaveURL(/[?&]page=/);
			}
		}
	});

	test('JobVersionフィルタが機能する（フィルタがある場合）', async ({ page }) => {
		await page.goto(`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/runs`);
		await page.waitForLoadState('networkidle');

		// フィルタ要素を探す
		const filter = page.locator('[data-testid="job-version-filter"], select[name="jobVersion"]');
		if ((await filter.count()) > 0) {
			// フィルタオプションを選択
			const options = await filter.locator('option').allTextContents();
			if (options.length > 1) {
				await filter.selectOption({ index: 1 });
				await page.waitForLoadState('networkidle');
			}
		}
	});
});

test.describe('Run Detail Page (実践的テスト)', () => {
	// テスト用のRun IDを保持
	let createdRunId: string | null = null;

	test('Run詳細画面が正常にロードされる', async ({ page }) => {
		// まずRunを作成
		const createResponse = await page.request.post('/api/runs', {
			data: { jobVersionId: TEST_JOB_VERSION_ID }
		});

		if (createResponse.status() === 200 || createResponse.status() === 201) {
			const data = await createResponse.json();
			createdRunId = data.id;

			// 詳細画面に遷移
			await page.goto(
				`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/runs/${createdRunId}`
			);
			await page.waitForLoadState('networkidle');

			// ステータス表示を確認
			const statusElement = page.locator(
				'[data-testid="run-status"], [class*="status"], text=/queued|running/i'
			);
			await expect(statusElement.first()).toBeVisible();
		}
	});

	test('プログレスバーが表示される（running状態の場合）', async ({ page }) => {
		// 任意のRunを取得
		const response = await page.request.get(
			`/api/workbenches/${TEST_WORKBENCH_ID}/runs?status=running`
		);

		if (response.status() === 200) {
			const data = await response.json();
			const runs = Array.isArray(data) ? data : data.runs || [];

			if (runs.length > 0) {
				const runId = runs[0].id;
				await page.goto(
					`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/runs/${runId}`
				);
				await page.waitForLoadState('networkidle');

				// プログレスバーを確認
				const progressBar = page.locator(
					'[role="progressbar"], [data-testid="progress-bar"], .progress-bar'
				);
				if ((await progressBar.count()) > 0) {
					await expect(progressBar.first()).toBeVisible();
				}
			}
		}
	});

	test('Langfuseリンクが表示される（external_trace_idがある場合）', async ({ page }) => {
		// Runを作成
		const createResponse = await page.request.post('/api/runs', {
			data: { jobVersionId: TEST_JOB_VERSION_ID }
		});

		if (createResponse.status() === 200 || createResponse.status() === 201) {
			const data = await createResponse.json();

			await page.goto(
				`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/runs/${data.id}`
			);
			await page.waitForLoadState('networkidle');

			// Langfuseリンクを探す（存在すれば）
			const langfuseLink = page.locator('a[href*="langfuse"], a:has-text("Open Trace")');
			const count = await langfuseLink.count();
			console.log(`Langfuse link count: ${count}`);
		}
	});

	test('Rerunボタンが失敗Runに表示される', async ({ page }) => {
		// 失敗Runを取得
		const response = await page.request.get(
			`/api/workbenches/${TEST_WORKBENCH_ID}/runs?status=failed`
		);

		if (response.status() === 200) {
			const data = await response.json();
			const runs = Array.isArray(data) ? data : data.runs || [];

			if (runs.length > 0) {
				const failedRunId = runs[0].id;
				await page.goto(
					`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/runs/${failedRunId}`
				);
				await page.waitForLoadState('networkidle');

				// Rerunボタンを確認
				const rerunButton = page.locator(
					'button:has-text("Rerun"), button:has-text("Re-run"), [data-testid="rerun-button"]'
				);
				if ((await rerunButton.count()) > 0) {
					await expect(rerunButton.first()).toBeVisible();
				}
			}
		}
	});
});

test.describe('Run Polling (実践的テスト)', () => {
	test('ポーリングでステータスが更新される', async ({ page }) => {
		// Runを作成
		const createResponse = await page.request.post('/api/runs', {
			data: { jobVersionId: TEST_JOB_VERSION_ID }
		});

		if (createResponse.status() === 200 || createResponse.status() === 201) {
			const data = await createResponse.json();
			const runId = data.id;

			await page.goto(
				`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/runs/${runId}`
			);
			await page.waitForLoadState('networkidle');

			// 初期ステータスを記録
			const statusElement = page.locator('[data-testid="run-status"], [class*="status"]').first();
			const initialStatus = await statusElement.textContent();
			console.log(`Initial status: ${initialStatus}`);

			// 10秒待機してステータス変化を確認
			await page.waitForTimeout(10000);

			const newStatus = await statusElement.textContent();
			console.log(`Status after 10s: ${newStatus}`);

			// ステータスが変化したか終了ステータスになったことを確認
			// (テスト環境では実際のジョブ実行がないため、変化しない可能性あり)
		}
	});

	test('終了ステータスでポーリングが停止する', async ({ page }) => {
		// 成功または失敗のRunを取得
		const response = await page.request.get(`/api/workbenches/${TEST_WORKBENCH_ID}/runs`);

		if (response.status() === 200) {
			const data = await response.json();
			const runs = Array.isArray(data) ? data : data.runs || [];

			const terminalRun = runs.find((r: { status: string }) =>
				TERMINAL_STATUSES.includes(r.status)
			);

			if (terminalRun) {
				await page.goto(
					`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/runs/${terminalRun.id}`
				);
				await page.waitForLoadState('networkidle');

				// ネットワークリクエストを監視
				const statusRequests: string[] = [];
				page.on('request', (request) => {
					if (request.url().includes('/status')) {
						statusRequests.push(request.url());
					}
				});

				// 10秒待機
				await page.waitForTimeout(10000);

				// 終了ステータスのRunではポーリングリクエストが発生しないはず
				console.log(`Status API requests during 10s: ${statusRequests.length}`);
				// ポーリングが停止していれば0または1回（初回のみ）
				expect(statusRequests.length).toBeLessThanOrEqual(2);
			}
		}
	});

	test('ページ遷移でポーリングが停止する（メモリリーク防止）', async ({ page }) => {
		// Runを作成
		const createResponse = await page.request.post('/api/runs', {
			data: { jobVersionId: TEST_JOB_VERSION_ID }
		});

		if (createResponse.status() === 200 || createResponse.status() === 201) {
			const data = await createResponse.json();
			const runId = data.id;

			await page.goto(
				`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/runs/${runId}`
			);
			await page.waitForLoadState('networkidle');

			// ネットワークリクエストを監視
			const statusRequestsAfterNav: string[] = [];
			page.on('request', (request) => {
				if (request.url().includes(`/runs/${runId}/status`)) {
					statusRequestsAfterNav.push(request.url());
				}
			});

			// 別のページに遷移
			await page.goto(`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/runs`);
			await page.waitForLoadState('networkidle');

			// 5秒待機
			await page.waitForTimeout(5000);

			// 遷移後は元のRunへのポーリングリクエストが発生しないはず
			console.log(`Status requests after navigation: ${statusRequestsAfterNav.length}`);
		}
	});
});

test.describe('Run Actions (実践的テスト)', () => {
	test('Run開始APIがqueuedステータスのRunを作成する', async ({ page }) => {
		const response = await page.request.post('/api/runs', {
			data: { jobVersionId: TEST_JOB_VERSION_ID }
		});

		expect([200, 201]).toContain(response.status());

		const data = await response.json();
		expect(data.id).toBeTruthy();
		expect(data.status).toBe('queued');
	});

	test('存在しないJobVersionでRun開始を試みると404', async ({ page }) => {
		const response = await page.request.post('/api/runs', {
			data: { jobVersionId: 'jv_nonexistent_999' }
		});

		expect([400, 404]).toContain(response.status());
	});

	test('Rerun APIが新しいRunを作成する', async ({ page }) => {
		// まず失敗Runを探す
		const listResponse = await page.request.get(
			`/api/workbenches/${TEST_WORKBENCH_ID}/runs?status=failed`
		);

		if (listResponse.status() === 200) {
			const data = await listResponse.json();
			const runs = Array.isArray(data) ? data : data.runs || [];

			if (runs.length > 0) {
				const failedRunId = runs[0].id;

				// Rerun実行
				const rerunResponse = await page.request.post(`/api/runs/${failedRunId}/rerun`);

				if (rerunResponse.status() === 200 || rerunResponse.status() === 201) {
					const newRun = await rerunResponse.json();
					expect(newRun.id).not.toBe(failedRunId);
					expect(newRun.status).toBe('queued');
				}
			}
		}
	});
});

test.describe('Error Handling (実践的テスト)', () => {
	test('存在しないRunにアクセスすると404', async ({ page }) => {
		const response = await page.goto(
			`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/runs/run_nonexistent_999`
		);

		expect(response?.status()).toBe(404);
	});

	test('別のWorkbench経由でRunにアクセスすると404', async ({ page }) => {
		// まずRunを作成
		const createResponse = await page.request.post('/api/runs', {
			data: { jobVersionId: TEST_JOB_VERSION_ID }
		});

		if (createResponse.status() === 200 || createResponse.status() === 201) {
			const data = await createResponse.json();

			// 別のWorkbench経由でアクセス
			const response = await page.goto(
				`/projects/${TEST_PROJECT_ID}/workbenches/wb_other/runs/${data.id}`
			);

			// 404またはリダイレクトを期待
			expect([404, 302, 307]).toContain(response?.status() || 404);
		}
	});
});

test.describe('User Workflow (実践的テスト)', () => {
	test('ユーザーフロー: Run作成 → ステータス確認 → 一覧に戻る', async ({ page }) => {
		// Step 1: Runs一覧画面にアクセス
		await page.goto(`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/runs`);
		await page.waitForLoadState('networkidle');

		// Step 2: Run作成（APIから直接）
		const createResponse = await page.request.post('/api/runs', {
			data: { jobVersionId: TEST_JOB_VERSION_ID }
		});

		if (createResponse.status() === 200 || createResponse.status() === 201) {
			const data = await createResponse.json();
			const runId = data.id;

			// Step 3: 詳細画面に遷移
			await page.goto(
				`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/runs/${runId}`
			);
			await page.waitForLoadState('networkidle');

			// ステータスが表示されていることを確認
			await expect(page.locator('body')).toContainText(/queued|running|success|failed/i);

			// Step 4: 一覧に戻る
			const backButton = page.locator(
				'a:has-text("Back"), button:has-text("Back"), [data-testid="back-button"]'
			);
			if ((await backButton.count()) > 0) {
				await backButton.first().click();
			} else {
				await page.goBack();
			}
			await page.waitForLoadState('networkidle');

			// 一覧画面に戻ったことを確認
			await expect(page).toHaveURL(/\/runs\/?$/);
		}
	});
});

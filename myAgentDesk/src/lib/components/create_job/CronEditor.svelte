<script lang="ts">
	import { onMount } from 'svelte';

	export let cronExpression = '0 9 * * *';
	export let timezone = 'Asia/Tokyo';
	export let onCronChange: (cron: string) => void;

	let nextExecution = '';
	let isValid = true;
	let validationError = '';

	// Cron式のバリデーション
	function validateCron(cron: string): boolean {
		// 簡易バリデーション（5フィールド: 分 時 日 月 曜日）
		const parts = cron.trim().split(/\s+/);
		if (parts.length !== 5) {
			validationError = 'Cron式は5つのフィールドが必要です（分 時 日 月 曜日）';
			return false;
		}
		validationError = '';
		return true;
	}

	// 次回実行日時の計算（簡易版）
	function calculateNextExecution(cron: string, tz: string): string {
		if (!validateCron(cron)) return '無効なCron式';

		// 実際の実装ではcronstrue等のライブラリを使用
		// ここでは簡易的な説明文を返す
		const parts = cron.split(/\s+/);
		const minute = parts[0];
		const hour = parts[1];
		const day = parts[2];
		const month = parts[3];
		const weekday = parts[4];

		if (day === '*' && month === '*' && weekday === '*') {
			return `毎日 ${hour}:${minute.padStart(2, '0')} (${tz})`;
		}
		if (weekday !== '*') {
			const weekdays = ['日', '月', '火', '水', '木', '金', '土'];
			return `毎週${weekdays[parseInt(weekday)]}曜日 ${hour}:${minute.padStart(2, '0')} (${tz})`;
		}
		if (day !== '*') {
			return `毎月${day}日 ${hour}:${minute.padStart(2, '0')} (${tz})`;
		}

		return 'カスタムスケジュール';
	}

	function handleCronChange() {
		isValid = validateCron(cronExpression);
		if (isValid) {
			nextExecution = calculateNextExecution(cronExpression, timezone);
			onCronChange(cronExpression);
		}
	}

	function setPreset(preset: string) {
		cronExpression = preset;
		handleCronChange();
	}

	onMount(() => {
		handleCronChange();
	});

	$: {
		cronExpression;
		timezone;
		handleCronChange();
	}
</script>

<div class="cron-editor bg-white dark:bg-dark-card p-6 rounded-lg shadow-sm">
	<h3 class="text-lg font-semibold mb-4 text-gray-900 dark:text-white">スケジュール設定</h3>

	<!-- Cron式入力 -->
	<div class="mb-4">
		<label for="cron-input" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
			Cron式
		</label>
		<input
			id="cron-input"
			type="text"
			bind:value={cronExpression}
			on:input={handleCronChange}
			class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-indigo-500 dark:bg-dark-input dark:text-white"
			class:border-red-500={!isValid}
			placeholder="0 9 * * *"
		/>
		<p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
			形式: 分 時 日 月 曜日（例: 0 9 * * * = 毎日9時）
		</p>
		{#if !isValid}
			<p class="mt-1 text-xs text-red-500">{validationError}</p>
		{/if}
	</div>

	<!-- プリセット選択 -->
	<div class="mb-4">
		<p class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
			よく使うスケジュール
		</p>
		<div class="grid grid-cols-2 gap-2">
			<button
				type="button"
				on:click={() => setPreset('0 9 * * *')}
				class="px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-dark-hover transition"
			>
				毎日9時
			</button>
			<button
				type="button"
				on:click={() => setPreset('0 */6 * * *')}
				class="px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-dark-hover transition"
			>
				6時間ごと
			</button>
			<button
				type="button"
				on:click={() => setPreset('0 9 * * 1')}
				class="px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-dark-hover transition"
			>
				毎週月曜9時
			</button>
			<button
				type="button"
				on:click={() => setPreset('0 9 1 * *')}
				class="px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-dark-hover transition"
			>
				毎月1日9時
			</button>
		</div>
	</div>

	<!-- プレビュー -->
	{#if isValid}
		<div
			class="mb-4 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg"
		>
			<p class="text-sm font-medium text-blue-900 dark:text-blue-300">
				📅 スケジュール: {nextExecution}
			</p>
		</div>
	{/if}

	<!-- タイムゾーン選択 -->
	<div>
		<label
			for="timezone-select"
			class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
		>
			タイムゾーン
		</label>
		<select
			id="timezone-select"
			bind:value={timezone}
			class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-indigo-500 dark:bg-dark-input dark:text-white"
		>
			<option value="Asia/Tokyo">Asia/Tokyo (JST)</option>
			<option value="UTC">UTC</option>
			<option value="America/New_York">America/New_York (EST)</option>
			<option value="Europe/London">Europe/London (GMT)</option>
		</select>
	</div>
</div>

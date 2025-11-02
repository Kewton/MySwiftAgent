<script lang="ts">
	export let executionMode: 'api_only' | 'schedule' | 'both' = 'api_only';
	export let onChange: (mode: 'api_only' | 'schedule' | 'both') => void;

	function handleChange() {
		onChange(executionMode);
	}
</script>

<div class="schedule-selector bg-white dark:bg-dark-card p-6 rounded-lg shadow-sm">
	<h3 class="text-lg font-semibold mb-4 text-gray-900 dark:text-white">実行方法の選択</h3>

	<div class="space-y-3">
		<!-- API公開のみ -->
		<label
			class="flex items-start space-x-3 cursor-pointer hover:bg-gray-50 dark:hover:bg-dark-hover p-3 rounded-lg transition"
		>
			<input
				type="radio"
				value="api_only"
				bind:group={executionMode}
				on:change={handleChange}
				class="mt-1"
			/>
			<div>
				<div class="font-medium text-gray-900 dark:text-white">API公開のみ</div>
				<div class="text-sm text-gray-500 dark:text-gray-400">
					手動実行のみ。ジョブをAPIとして公開し、必要なときに呼び出します。
				</div>
			</div>
		</label>

		<!-- スケジュール実行 -->
		<label
			class="flex items-start space-x-3 cursor-pointer hover:bg-gray-50 dark:hover:bg-dark-hover p-3 rounded-lg transition"
		>
			<input
				type="radio"
				value="schedule"
				bind:group={executionMode}
				on:change={handleChange}
				class="mt-1"
			/>
			<div>
				<div class="font-medium text-gray-900 dark:text-white">スケジュール実行</div>
				<div class="text-sm text-gray-500 dark:text-gray-400">
					定期実行のみ。指定したスケジュールで自動的にジョブを実行します。
				</div>
			</div>
		</label>

		<!-- 両方 -->
		<label
			class="flex items-start space-x-3 cursor-pointer hover:bg-gray-50 dark:hover:bg-dark-hover p-3 rounded-lg transition"
		>
			<input
				type="radio"
				value="both"
				bind:group={executionMode}
				on:change={handleChange}
				class="mt-1"
			/>
			<div>
				<div class="font-medium text-gray-900 dark:text-white">両方</div>
				<div class="text-sm text-gray-500 dark:text-gray-400">
					手動実行とスケジュール実行の両方を有効にします。
				</div>
			</div>
		</label>
	</div>
</div>

<style>
	/* カスタムラジオボタンスタイル */
	input[type='radio'] {
		accent-color: #6366f1; /* Indigo */
	}
</style>

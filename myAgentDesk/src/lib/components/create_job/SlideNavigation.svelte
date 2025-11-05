<script lang="ts">
	export let currentSlide = 1;
	export let totalSlides = 1;
	export let onPrev: () => void;
	export let onNext: () => void;
	export let onFullscreen: () => void;
	export let onExportPdf: () => void;
	export let onExportPng: () => void;

	$: canGoPrev = currentSlide > 1;
	$: canGoNext = currentSlide < totalSlides;
</script>

<div
	class="slide-navigation flex items-center justify-between p-4 bg-white dark:bg-dark-card border-t border-gray-200 dark:border-gray-700"
>
	<!-- 前後移動 -->
	<div class="flex items-center space-x-3">
		<button
			on:click={onPrev}
			disabled={!canGoPrev}
			class="px-3 py-2 text-sm font-medium rounded-lg border transition {canGoPrev
				? 'border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-dark-hover text-gray-700 dark:text-gray-300'
				: 'border-gray-200 dark:border-gray-700 text-gray-400 dark:text-gray-600 cursor-not-allowed'}"
			aria-label="前のスライド"
		>
			← 前へ
		</button>
		<span class="text-sm font-medium text-gray-700 dark:text-gray-300 min-w-[80px] text-center">
			{currentSlide} / {totalSlides}
		</span>
		<button
			on:click={onNext}
			disabled={!canGoNext}
			class="px-3 py-2 text-sm font-medium rounded-lg border transition {canGoNext
				? 'border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-dark-hover text-gray-700 dark:text-gray-300'
				: 'border-gray-200 dark:border-gray-700 text-gray-400 dark:text-gray-600 cursor-not-allowed'}"
			aria-label="次のスライド"
		>
			次へ →
		</button>
	</div>

	<!-- 全画面・エクスポート -->
	<div class="flex items-center space-x-2">
		<button
			on:click={onFullscreen}
			class="px-3 py-2 text-sm font-medium rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-dark-hover text-gray-700 dark:text-gray-300 transition"
			aria-label="全画面表示"
		>
			🖥️ 全画面
		</button>
		<button
			on:click={onExportPdf}
			class="px-3 py-2 text-sm font-medium rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-dark-hover text-gray-700 dark:text-gray-300 transition"
			aria-label="PDFでエクスポート"
		>
			📄 PDF
		</button>
		<button
			on:click={onExportPng}
			class="px-3 py-2 text-sm font-medium rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-dark-hover text-gray-700 dark:text-gray-300 transition"
			aria-label="PNGでエクスポート"
		>
			🖼️ PNG
		</button>
	</div>
</div>

<style>
	button:disabled {
		opacity: 0.5;
	}
</style>

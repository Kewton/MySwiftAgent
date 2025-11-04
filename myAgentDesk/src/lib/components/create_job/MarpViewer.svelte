<svelte:options accessors={true} />

<script lang="ts">
	import { onMount } from 'svelte';
	import { getMarpReport } from '$lib/services/marp-api';
	import type { MarpReportResponse } from '$lib/services/marp-api';
	import { Marp } from '@marp-team/marp-core';

	export let jobId: string;
	export let format: 'html' | 'pdf' | 'png' = 'html';

	let html = '';
	let isLoading = true;
	let error: string | null = null;
	let report: MarpReportResponse | null = null;

	// 外部から現在のスライドとスライド総数を参照できるようにexport
	export let currentSlide = 1;
	export let totalSlides = 0;

	onMount(async () => {
		await loadReport();
	});

	async function loadReport() {
		isLoading = true;
		error = null;

		try {
			report = await getMarpReport(jobId, format);

			// htmlが空の場合、Markdownをクライアント側でHTMLに変換
			if (!report.html && report.markdown) {
				const marp = new Marp();
				const { html: renderedHtml } = marp.render(report.markdown);
				html = renderedHtml;
			} else {
				html = report.html;
			}

			totalSlides = report.slide_count;
			currentSlide = 1;
			isLoading = false;
		} catch (err) {
			error = err instanceof Error ? err.message : 'スライドの読み込みに失敗しました';
			isLoading = false;
		}
	}

	// iframe内のスライド変更イベントをリッスン
	function handleMessage(event: MessageEvent) {
		if (event.data?.type === 'slide-change') {
			currentSlide = event.data.slideIndex + 1;
		}
	}

	// スライド操作メソッド（親コンポーネントから呼び出し可能）
	export function nextSlide() {
		if (currentSlide < totalSlides) {
			currentSlide++;
			postMessageToIframe({ type: 'navigate', slideIndex: currentSlide - 1 });
		}
	}

	export function prevSlide() {
		if (currentSlide > 1) {
			currentSlide--;
			postMessageToIframe({ type: 'navigate', slideIndex: currentSlide - 1 });
		}
	}

	export function goToSlide(index: number) {
		if (index >= 1 && index <= totalSlides) {
			currentSlide = index;
			postMessageToIframe({ type: 'navigate', slideIndex: index - 1 });
		}
	}

	function postMessageToIframe(message: { type: string; slideIndex?: number }) {
		const iframe = document.querySelector('.marp-viewer iframe') as HTMLIFrameElement;
		if (iframe && iframe.contentWindow) {
			iframe.contentWindow.postMessage(message, '*');
		}
	}
</script>

<svelte:window on:message={handleMessage} />

<div class="marp-viewer-container w-full h-full">
	{#if isLoading}
		<div
			class="loading flex flex-col items-center justify-center h-full bg-gray-50 dark:bg-gray-900"
		>
			<div
				class="spinner border-4 border-gray-300 dark:border-gray-700 border-t-indigo-600 rounded-full w-12 h-12 animate-spin mb-4"
			></div>
			<p class="text-gray-700 dark:text-gray-300 font-medium">スライドを読み込み中...</p>
		</div>
	{:else if error}
		<div
			class="error flex flex-col items-center justify-center h-full bg-red-50 dark:bg-red-900/20 p-6"
		>
			<div class="text-red-600 dark:text-red-400 text-6xl mb-4">⚠️</div>
			<p class="text-red-800 dark:text-red-300 font-semibold text-lg mb-2">
				スライドの読み込みに失敗しました
			</p>
			<p class="text-red-600 dark:text-red-400 text-sm">{error}</p>
			<button
				on:click={loadReport}
				class="mt-4 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition"
			>
				再試行
			</button>
		</div>
	{:else}
		<div class="marp-viewer w-full h-full bg-white dark:bg-gray-900 rounded-lg overflow-hidden">
			<iframe
				title="Marp Slides"
				srcdoc={html}
				class="w-full h-full border-0"
				sandbox="allow-scripts allow-same-origin"
			/>
		</div>
	{/if}
</div>

<style>
	.marp-viewer-container {
		min-height: 500px;
	}

	.spinner {
		animation: spin 1s linear infinite;
	}

	@keyframes spin {
		0% {
			transform: rotate(0deg);
		}
		100% {
			transform: rotate(360deg);
		}
	}

	/* iframeのスタイル調整 */
	.marp-viewer iframe {
		background: white;
	}

	/* ダークモード時もMarpスライドは白背景を維持（Marpのデフォルトスタイルは明るい背景用のため） */
	:global(.dark) .marp-viewer iframe {
		background: white;
	}
</style>

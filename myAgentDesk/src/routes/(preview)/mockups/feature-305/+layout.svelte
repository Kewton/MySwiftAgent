<script lang="ts">
	import { page } from '$app/stores';
	import type { Snippet } from 'svelte';

	let { children }: { children: Snippet } = $props();

	const patterns = [
		{ id: 'pattern-a', name: 'A: シンプル', label: 'Minimal' },
		{ id: 'pattern-b', name: 'B: 標準', label: 'Standard' },
		{ id: 'pattern-c', name: 'C: リッチ', label: 'Rich' },
		{ id: 'pattern-d', name: 'D: 革新的', label: 'Innovative' },
		{ id: 'comparison', name: '比較', label: 'Compare' }
	];

	const currentPattern = $derived($page.url.pathname.split('/').pop() ?? '');
</script>

<div class="preview-shell">
	<!-- Preview Control Bar -->
	<header class="preview-bar">
		<div class="preview-left">
			<span class="preview-badge">PREVIEW</span>
			<span class="preview-title">Issue #305 - ワークフロー自動生成UI</span>
		</div>
		<nav class="pattern-nav">
			{#each patterns as pattern}
				<a
					href="/mockups/feature-305/{pattern.id}"
					class="pattern-link"
					class:active={currentPattern === pattern.id}
				>
					{pattern.name}
				</a>
			{/each}
		</nav>
	</header>

	<!-- Pattern Content -->
	<main class="preview-content">
		{@render children()}
	</main>

	<!-- Preview Status Bar -->
	<footer class="preview-status">
		<span>
			Current: <strong>{patterns.find((p) => p.id === currentPattern)?.name ?? 'Overview'}</strong>
		</span>
		<span class="sep">|</span>
		<span>Issue #305: Job生成時ワークフロー自動生成</span>
		<span class="sep">|</span>
		<span>URL: {$page.url.pathname}</span>
	</footer>
</div>

<style>
	:global(*) {
		box-sizing: border-box;
	}

	:global(body) {
		margin: 0;
		font-family:
			-apple-system,
			BlinkMacSystemFont,
			'Segoe UI',
			Roboto,
			'Helvetica Neue',
			sans-serif;
	}

	.preview-shell {
		min-height: 100vh;
		display: flex;
		flex-direction: column;
		background: #f8fafc;
	}

	.preview-bar {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 6px 12px;
		background: #0f172a;
		color: white;
		position: sticky;
		top: 0;
		z-index: 9999;
	}

	.preview-left {
		display: flex;
		align-items: center;
		gap: 10px;
	}

	.preview-badge {
		padding: 2px 6px;
		background: #10b981;
		border-radius: 3px;
		font-size: 10px;
		font-weight: 700;
		letter-spacing: 0.5px;
	}

	.preview-title {
		font-size: 12px;
		font-weight: 500;
		color: #e2e8f0;
	}

	.pattern-nav {
		display: flex;
		gap: 4px;
	}

	.pattern-link {
		padding: 4px 10px;
		border-radius: 4px;
		text-decoration: none;
		font-size: 11px;
		font-weight: 500;
		color: #94a3b8;
		background: transparent;
		border: 1px solid transparent;
		transition: all 0.15s;
	}

	.pattern-link:hover {
		color: white;
		background: rgba(255, 255, 255, 0.1);
	}

	.pattern-link.active {
		color: white;
		background: #10b981;
		border-color: #10b981;
	}

	.preview-content {
		flex: 1;
		display: flex;
		flex-direction: column;
	}

	.preview-status {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 4px 12px;
		background: #0f172a;
		color: #94a3b8;
		font-size: 11px;
		position: sticky;
		bottom: 0;
		z-index: 9999;
	}

	.preview-status strong {
		font-weight: 600;
		color: #10b981;
	}

	.sep {
		color: #334155;
	}
</style>

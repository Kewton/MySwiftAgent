<script lang="ts">
	import { page } from '$app/stores';

	// eslint-disable-next-line @typescript-eslint/no-unused-vars
	export const data = undefined;

	$: currentPattern = $page.url.pathname.split('/').pop();
	$: patterns = ['pattern-a', 'pattern-b', 'pattern-c', 'pattern-d'];

	const patternLabels: Record<string, string> = {
		'pattern-a': 'パターンA: シンプル',
		'pattern-b': 'パターンB: 標準',
		'pattern-c': 'パターンC: リッチ',
		'pattern-d': 'パターンD: 革新的'
	};

	const patternFeatures: Record<string, string[]> = {
		'pattern-a': ['複数候補提示機能', 'フィードバック機能', 'モバイルファースト', 'シンプルなUI'],
		'pattern-b': [
			'複数候補提示機能',
			'フィードバック機能',
			'基本的なメトリクス表示',
			'バランスの良いUI'
		],
		'pattern-c': [
			'複数候補提示機能',
			'フィードバック機能',
			'詳細ダッシュボード',
			'診断情報表示',
			'プロンプト管理'
		],
		'pattern-d': [
			'全機能実装',
			'AIアシスト推奨',
			'ABテスト機能',
			'インタラクティブダッシュボード',
			'リアルタイム更新'
		]
	};
</script>

<div class="mockup-container">
	<!-- ナビゲーションバー -->
	<nav class="mockup-nav">
		<h1>Feature #152 - 要件定義エージェントMLOps導入</h1>
		<div class="pattern-switcher">
			{#each patterns as pattern}
				<a
					href="/mockups/feature-152/{pattern}"
					class:active={currentPattern === pattern}
					aria-label={patternLabels[pattern]}
				>
					{patternLabels[pattern]}
				</a>
			{/each}
			<a
				href="/mockups/feature-152/comparison"
				class:active={currentPattern === 'comparison'}
				aria-label="比較ビュー"
			>
				比較
			</a>
		</div>
	</nav>

	<!-- メタ情報パネル -->
	<aside class="mockup-info">
		<h3>現在のパターン</h3>
		<p class="pattern-name">{patternLabels[currentPattern || 'pattern-a'] || '比較ビュー'}</p>

		{#if currentPattern && currentPattern !== 'comparison'}
			<h3>実装機能</h3>
			<ul>
				{#each patternFeatures[currentPattern] || [] as feature}
					<li>{feature}</li>
				{/each}
			</ul>
		{/if}

		<h3>Issue情報</h3>
		<dl>
			<dt>Issue番号</dt>
			<dd>#152</dd>
			<dt>優先度</dt>
			<dd>Medium (feature)</dd>
			<dt>対象プロジェクト</dt>
			<dd>expertAgent</dd>
			<dt>対象API</dt>
			<dd>/v1/chat/requirement-definition</dd>
		</dl>
	</aside>

	<!-- コンテンツエリア -->
	<main class="mockup-content">
		<slot />
	</main>
</div>

<style>
	.mockup-container {
		display: grid;
		grid-template-areas:
			'nav nav'
			'info content';
		grid-template-columns: 280px 1fr;
		grid-template-rows: auto 1fr;
		min-height: 100vh;
		background: #f8f9fa;
	}

	.mockup-nav {
		grid-area: nav;
		padding: 1.5rem;
		background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
		color: white;
		box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
	}

	.mockup-nav h1 {
		margin: 0 0 1rem 0;
		font-size: 1.25rem;
		font-weight: 600;
	}

	.pattern-switcher {
		display: flex;
		gap: 0.5rem;
		flex-wrap: wrap;
	}

	.pattern-switcher a {
		padding: 0.5rem 1rem;
		border-radius: 0.375rem;
		text-decoration: none;
		color: white;
		background: rgba(255, 255, 255, 0.1);
		border: 1px solid rgba(255, 255, 255, 0.2);
		transition: all 0.2s;
		font-size: 0.875rem;
		font-weight: 500;
		backdrop-filter: blur(10px);
	}

	.pattern-switcher a:hover {
		background: rgba(255, 255, 255, 0.2);
		transform: translateY(-1px);
	}

	.pattern-switcher a.active {
		background: white;
		color: #667eea;
		border-color: white;
		box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
	}

	.mockup-info {
		grid-area: info;
		padding: 1.5rem;
		background: white;
		border-right: 1px solid #dee2e6;
		overflow-y: auto;
	}

	.mockup-info h3 {
		margin: 1.5rem 0 0.75rem 0;
		font-size: 0.875rem;
		font-weight: 600;
		text-transform: uppercase;
		color: #6c757d;
	}

	.mockup-info h3:first-child {
		margin-top: 0;
	}

	.pattern-name {
		font-size: 1.125rem;
		font-weight: 600;
		color: #667eea;
		margin: 0;
	}

	.mockup-info ul {
		margin: 0;
		padding-left: 1.25rem;
		list-style: none;
	}

	.mockup-info li {
		position: relative;
		padding: 0.25rem 0;
		font-size: 0.875rem;
		color: #495057;
	}

	.mockup-info li::before {
		content: '✓';
		position: absolute;
		left: -1.25rem;
		color: #28a745;
		font-weight: bold;
	}

	.mockup-info dl {
		margin: 0;
		display: grid;
		grid-template-columns: auto 1fr;
		gap: 0.5rem;
		font-size: 0.875rem;
	}

	.mockup-info dt {
		font-weight: 600;
		color: #6c757d;
	}

	.mockup-info dd {
		margin: 0;
		color: #495057;
	}

	.mockup-content {
		grid-area: content;
		padding: 2rem;
		overflow-y: auto;
		background: #f8f9fa;
	}

	@media (max-width: 1024px) {
		.mockup-container {
			grid-template-areas:
				'nav'
				'content'
				'info';
			grid-template-columns: 1fr;
			grid-template-rows: auto 1fr auto;
		}

		.mockup-info {
			border-right: none;
			border-top: 1px solid #dee2e6;
		}

		.pattern-switcher {
			flex-direction: column;
		}
	}
</style>

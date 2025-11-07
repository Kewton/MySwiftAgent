<script lang="ts">
	// 利用可能なモックアップのリスト（実際は動的に取得）
	let mockups = [
		{ id: 'feature-001', name: 'ユーザー管理機能', status: 'review', date: '2024-11-07' },
		{ id: 'feature-002', name: 'ダッシュボード改善', status: 'selected', date: '2024-11-06' },
		{ id: 'feature-003', name: '通知システム', status: 'draft', date: '2024-11-05' }
	];

	let filter = 'all';

	$: filteredMockups = filter === 'all' ? mockups : mockups.filter((m) => m.status === filter);
</script>

<div class="mockups-index">
	<h1>UIモックアップ一覧</h1>

	<div class="controls">
		<div class="filter-buttons">
			<button class:active={filter === 'all'} on:click={() => (filter = 'all')}> すべて </button>
			<button class:active={filter === 'draft'} on:click={() => (filter = 'draft')}>
				ドラフト
			</button>
			<button class:active={filter === 'review'} on:click={() => (filter = 'review')}>
				レビュー中
			</button>
			<button class:active={filter === 'selected'} on:click={() => (filter = 'selected')}>
				選定済み
			</button>
		</div>
	</div>

	<div class="mockup-grid">
		{#each filteredMockups as mockup}
			<div class="mockup-card">
				<div class="mockup-header">
					<h3>{mockup.name}</h3>
					<span class="status status-{mockup.status}">
						{mockup.status === 'draft'
							? 'ドラフト'
							: mockup.status === 'review'
								? 'レビュー中'
								: '選定済み'}
					</span>
				</div>

				<div class="mockup-info">
					<p>Feature: {mockup.id}</p>
					<p>作成日: {mockup.date}</p>
				</div>

				<div class="mockup-patterns">
					<h4>利用可能なパターン:</h4>
					<div class="pattern-links">
						<a href="/mockups/{mockup.id}/pattern-a">A: シンプル</a>
						<a href="/mockups/{mockup.id}/pattern-b">B: 標準</a>
						<a href="/mockups/{mockup.id}/pattern-c">C: リッチ</a>
						<a href="/mockups/{mockup.id}/pattern-d">D: 革新的</a>
					</div>
				</div>

				<div class="mockup-actions">
					<a href="/mockups/{mockup.id}/comparison" class="btn-primary"> パターンを比較 </a>
				</div>
			</div>
		{/each}
	</div>

	{#if filteredMockups.length === 0}
		<div class="empty-state">
			<p>該当するモックアップがありません</p>
		</div>
	{/if}
</div>

<style>
	.mockups-index {
		max-width: 1200px;
		margin: 0 auto;
		padding: 2rem;
	}

	h1 {
		margin-bottom: 2rem;
	}

	.controls {
		margin-bottom: 2rem;
	}

	.filter-buttons {
		display: flex;
		gap: 0.5rem;
	}

	.filter-buttons button {
		padding: 0.5rem 1rem;
		border: 1px solid #dee2e6;
		background: white;
		border-radius: 0.25rem;
		cursor: pointer;
		transition: all 0.2s;
	}

	.filter-buttons button:hover {
		background: #f8f9fa;
	}

	.filter-buttons button.active {
		background: #007bff;
		color: white;
		border-color: #007bff;
	}

	.mockup-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
		gap: 1.5rem;
	}

	.mockup-card {
		background: white;
		border: 1px solid #dee2e6;
		border-radius: 0.5rem;
		padding: 1.5rem;
		transition:
			transform 0.2s,
			box-shadow 0.2s;
	}

	.mockup-card:hover {
		transform: translateY(-2px);
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
	}

	.mockup-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		margin-bottom: 1rem;
	}

	.mockup-header h3 {
		margin: 0;
		font-size: 1.25rem;
	}

	.status {
		padding: 0.25rem 0.75rem;
		border-radius: 1rem;
		font-size: 0.875rem;
		font-weight: 500;
	}

	.status-draft {
		background: #e9ecef;
		color: #495057;
	}

	.status-review {
		background: #fff3cd;
		color: #856404;
	}

	.status-selected {
		background: #d4edda;
		color: #155724;
	}

	.mockup-info {
		margin-bottom: 1rem;
		color: #6c757d;
		font-size: 0.9rem;
	}

	.mockup-info p {
		margin: 0.25rem 0;
	}

	.mockup-patterns {
		margin-bottom: 1rem;
	}

	.mockup-patterns h4 {
		margin: 0.5rem 0;
		font-size: 0.9rem;
		color: #6c757d;
	}

	.pattern-links {
		display: grid;
		grid-template-columns: repeat(2, 1fr);
		gap: 0.5rem;
	}

	.pattern-links a {
		padding: 0.25rem 0.5rem;
		background: #f8f9fa;
		border-radius: 0.25rem;
		text-decoration: none;
		color: #495057;
		font-size: 0.875rem;
		text-align: center;
		transition: background 0.2s;
	}

	.pattern-links a:hover {
		background: #e9ecef;
	}

	.mockup-actions {
		padding-top: 1rem;
		border-top: 1px solid #dee2e6;
	}

	.btn-primary {
		display: block;
		padding: 0.5rem 1rem;
		background: #007bff;
		color: white;
		text-align: center;
		text-decoration: none;
		border-radius: 0.25rem;
		transition: background 0.2s;
	}

	.btn-primary:hover {
		background: #0056b3;
	}

	.empty-state {
		text-align: center;
		padding: 3rem;
		color: #6c757d;
	}
</style>

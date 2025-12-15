<!--
  Breadcrumb Component
  Issue #285: SvelteKit Routing Foundation

  Displays breadcrumb navigation based on current URL path.
  Pattern: Home > Projects > proj_001 > Workbenches > wb_abc123 > ...
-->
<script lang="ts">
	import { page } from '$app/stores';

	interface BreadcrumbItem {
		label: string;
		href: string;
	}

	const items = $derived.by(() => {
		const pathname = $page.url.pathname;
		const params = $page.params;
		const breadcrumbs: BreadcrumbItem[] = [{ label: 'Home', href: '/' }];

		const segments = pathname.split('/').filter(Boolean);

		let currentPath = '';

		for (let i = 0; i < segments.length; i++) {
			const segment = segments[i];
			currentPath += `/${segment}`;

			// Map URL segments to readable labels
			let label = segment;

			// Handle dynamic segments
			if (segment === params.projectId) {
				label = params.projectId;
			} else if (segment === params.workbenchId) {
				label = params.workbenchId;
			} else if (segment === params.reqVersionId) {
				label = params.reqVersionId;
			} else if (segment === params.jobVersionId) {
				label = params.jobVersionId;
			} else if (segment === params.runId) {
				label = params.runId;
			} else if (segment === params.scheduleId) {
				label = params.scheduleId;
			} else {
				// Capitalize first letter for static segments
				label = segment.charAt(0).toUpperCase() + segment.slice(1);
				// Handle kebab-case
				label = label.replace(/-/g, ' ');
			}

			breadcrumbs.push({ label, href: currentPath });
		}

		return breadcrumbs;
	});
</script>

<nav class="breadcrumb" aria-label="Breadcrumb">
	<ol class="breadcrumb-list">
		{#each items as item, index}
			<li class="breadcrumb-item">
				{#if index < items.length - 1}
					<a href={item.href} class="breadcrumb-link">{item.label}</a>
					<span class="separator" aria-hidden="true">/</span>
				{:else}
					<span class="breadcrumb-current" aria-current="page">{item.label}</span>
				{/if}
			</li>
		{/each}
	</ol>
</nav>

<style>
	.breadcrumb {
		padding: 0.5rem 1rem;
		background: #f8fafc;
		border-bottom: 1px solid #e2e8f0;
	}

	.breadcrumb-list {
		display: flex;
		align-items: center;
		gap: 0.25rem;
		margin: 0;
		padding: 0;
		list-style: none;
		font-size: 0.875rem;
	}

	.breadcrumb-item {
		display: flex;
		align-items: center;
		gap: 0.25rem;
	}

	.breadcrumb-link {
		color: #64748b;
		text-decoration: none;
	}

	.breadcrumb-link:hover {
		color: #3b82f6;
		text-decoration: underline;
	}

	.breadcrumb-current {
		color: #1e293b;
		font-weight: 500;
	}

	.separator {
		color: #cbd5e1;
		margin: 0 0.25rem;
	}
</style>

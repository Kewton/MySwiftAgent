<!--
  ProjectSidebar Component
  Issue #285: SvelteKit Routing Foundation

  Sidebar navigation for project-level pages.
  Contains: Overview, Workbenches, Vault Settings
-->
<script lang="ts">
	import { page } from '$app/stores';

	interface Project {
		id: string;
		name: string;
	}

	interface Props {
		project: Project;
	}

	let { project }: Props = $props();

	const currentPath = $derived($page.url.pathname);
	const basePath = $derived(`/projects/${project.id}`);

	function isActive(path: string): boolean {
		if (path === basePath) {
			return currentPath === basePath;
		}
		return currentPath.startsWith(path);
	}
</script>

<nav class="project-sidebar" aria-label="Project navigation">
	<div class="sidebar-header">
		<h2 class="project-name">{project.name}</h2>
	</div>

	<ul class="sidebar-nav">
		<li>
			<a
				href={basePath}
				class="sidebar-link"
				class:active={isActive(basePath) &&
					!currentPath.includes('/workbenches') &&
					!currentPath.includes('/vault')}
				aria-label="Overview"
			>
				Overview
			</a>
		</li>
		<li>
			<a
				href="{basePath}/workbenches"
				class="sidebar-link"
				class:active={isActive(`${basePath}/workbenches`)}
				aria-label="Workbenches"
			>
				Workbenches
			</a>
		</li>
		<li>
			<a
				href="{basePath}/vault"
				class="sidebar-link"
				class:active={isActive(`${basePath}/vault`)}
				aria-label="Vault"
			>
				Vault
			</a>
		</li>
	</ul>
</nav>

<style>
	.project-sidebar {
		width: 240px;
		min-height: 100%;
		background: #f8fafc;
		border-right: 1px solid #e2e8f0;
		padding: 1rem 0;
	}

	.sidebar-header {
		padding: 0 1rem 1rem;
		border-bottom: 1px solid #e2e8f0;
		margin-bottom: 1rem;
	}

	.project-name {
		margin: 0;
		font-size: 1rem;
		font-weight: 600;
		color: #1e293b;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.sidebar-nav {
		list-style: none;
		margin: 0;
		padding: 0;
	}

	.sidebar-link {
		display: block;
		padding: 0.625rem 1rem;
		color: #64748b;
		text-decoration: none;
		font-size: 0.875rem;
		font-weight: 500;
		transition:
			color 0.15s,
			background 0.15s;
	}

	.sidebar-link:hover {
		color: #1e293b;
		background: #e2e8f0;
	}

	.sidebar-link.active {
		color: #3b82f6;
		background: #eff6ff;
		border-right: 2px solid #3b82f6;
	}
</style>

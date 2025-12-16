<!--
  GlobalNav Component
  Issue #285: SvelteKit Routing Foundation

  Global navigation bar displayed at the top of all pages.
  Contains: Logo/Home, Projects link, Settings
-->
<script lang="ts">
	import { page } from '$app/stores';

	const currentPath = $derived($page.url.pathname);

	function isActive(path: string): boolean {
		if (path === '/') {
			return currentPath === '/';
		}
		return currentPath.startsWith(path);
	}
</script>

<nav class="global-nav" aria-label="Global navigation">
	<div class="nav-left">
		<a href="/" class="logo" aria-label="MyAgentDesk Home">MyAgentDesk</a>
	</div>

	<div class="nav-center">
		<a href="/projects" class="nav-link" class:active={isActive('/projects')} aria-label="Projects">
			Projects
		</a>
	</div>

	<div class="nav-right">
		<a href="/settings" class="nav-link" aria-label="Settings">Settings</a>
	</div>
</nav>

<style>
	.global-nav {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0 1rem;
		height: 56px;
		background: #1e293b;
		color: white;
		border-bottom: 1px solid #334155;
	}

	.nav-left {
		display: flex;
		align-items: center;
	}

	.logo {
		font-size: 1.25rem;
		font-weight: 700;
		color: white;
		text-decoration: none;
		letter-spacing: -0.5px;
	}

	.logo:hover {
		color: #60a5fa;
	}

	.nav-center {
		display: flex;
		gap: 1rem;
	}

	.nav-right {
		display: flex;
		align-items: center;
		gap: 1rem;
	}

	.nav-link {
		color: #94a3b8;
		text-decoration: none;
		font-size: 0.875rem;
		font-weight: 500;
		padding: 0.5rem 0.75rem;
		border-radius: 0.375rem;
		transition:
			color 0.15s,
			background 0.15s;
	}

	.nav-link:hover {
		color: white;
		background: rgba(255, 255, 255, 0.1);
	}

	.nav-link.active {
		color: white;
		background: #3b82f6;
	}
</style>

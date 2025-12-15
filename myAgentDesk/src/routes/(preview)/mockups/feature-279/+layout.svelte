<script lang="ts">
  import { page } from '$app/stores';
  import type { Snippet } from 'svelte';

  let { children }: { children: Snippet } = $props();

  const currentPath = $derived($page.url.pathname);
</script>

<div class="preview-shell">
  <!-- Preview Control Bar -->
  <header class="preview-bar">
    <div class="preview-left">
      <span class="preview-badge">PREVIEW</span>
      <span class="preview-title">Issue #279 - myAgentDesk MVP Mockup</span>
    </div>
    <nav class="pattern-nav">
      <a
        href="/mockups/feature-279/pattern-a"
        class="pattern-link active"
      >
        Pattern A: Professional
      </a>
    </nav>
  </header>

  <!-- Pattern Content -->
  <main class="preview-content">
    {@render children()}
  </main>

  <!-- Preview Status Bar -->
  <footer class="preview-status">
    <span>
      Current: <strong>Pattern A: Professional</strong>
    </span>
    <span class="sep">|</span>
    <span>screen-transition.md compliant</span>
    <span class="sep">|</span>
    <span>URL: {$page.url.pathname}{$page.url.search}</span>
  </footer>
</div>

<style>
  :global(*) {
    box-sizing: border-box;
  }

  :global(body) {
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
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
    background: #3b82f6;
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
    background: #2563eb;
    border-color: #2563eb;
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
    color: #2563eb;
  }

  .sep {
    color: #334155;
  }
</style>

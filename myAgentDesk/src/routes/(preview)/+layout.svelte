<script lang="ts">
  import { dev } from '$app/environment';
</script>

{#if dev}
  <div class="preview-banner">
    ⚠️ プレビューモード - このページは開発環境でのみ表示されます
  </div>
{/if}

<div class="preview-layout">
  <slot />
</div>

<style>
  .preview-banner {
    background: #ffc107;
    color: #000;
    padding: 0.5rem;
    text-align: center;
    font-weight: bold;
    position: sticky;
    top: 0;
    z-index: 1000;
  }

  .preview-layout {
    min-height: 100vh;
    background: #f5f5f5;
  }
</style>
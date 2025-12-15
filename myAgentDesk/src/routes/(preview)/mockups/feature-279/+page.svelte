<script lang="ts">
  import { goto } from '$app/navigation';
  import { onMount } from 'svelte';

  // Redirect to pattern-a on mount
  onMount(() => {
    goto('/mockups/feature-279/pattern-a');
  });
</script>

<div class="loading">
  <p>Loading comparison view...</p>
</div>

<style>
  .loading {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 400px;
    color: var(--color-text-secondary);
  }
</style>

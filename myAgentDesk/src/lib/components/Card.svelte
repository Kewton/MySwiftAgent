<script lang="ts">
	export let variant: 'default' | 'chat' | 'node' = 'default';
	export let hoverable = false;

	const variantClasses = {
		default: 'bg-white dark:bg-dark-card rounded-lg shadow-sm',
		chat: 'chat-bubble',
		node: 'node-card'
	};

	const hoverClass = hoverable ? 'hover:shadow-md cursor-pointer' : '';
</script>

<div
	class="{variantClasses[variant]} {hoverClass} transition-shadow"
	on:click
	on:keydown={(e) => e.key === 'Enter' && e.currentTarget.click()}
	role="button"
	tabindex="0"
>
	<slot />
</div>

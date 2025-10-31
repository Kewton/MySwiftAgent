<script lang="ts">
	export let variant: 'primary' | 'secondary' | 'danger' | 'ghost' = 'primary';
	export let size: 'sm' | 'md' | 'lg' = 'md';
	export let disabled = false;
	export let type: 'button' | 'submit' | 'reset' = 'button';

	// カスタムクラスを受け入れる
	let className = '';
	export { className as class };

	const variantClasses = {
		primary: 'bg-primary-500 hover:bg-primary-600 text-white',
		secondary:
			'bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-900 dark:text-white',
		danger: 'bg-red-500 hover:bg-red-600 text-white',
		ghost:
			'bg-transparent hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-300'
	};

	const sizeClasses = {
		sm: 'px-3 py-1.5 text-sm',
		md: 'px-4 py-2 text-base',
		lg: 'px-6 py-3 text-lg'
	};
</script>

<button
	{type}
	{disabled}
	class="rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed {variantClasses[
		variant
	]} {sizeClasses[size]} {className}"
	on:click
>
	<slot />
</button>

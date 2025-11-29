<script lang="ts">
	/**
	 * ConversationTimeline - Displays conversation messages in a timeline format
	 *
	 * Features:
	 * - Alternating layout for user/assistant messages
	 * - Timestamp display
	 * - Message content with markdown support potential
	 * - Responsive design
	 */

	import type { DiagnosticMessage } from '../types';

	export let messages: DiagnosticMessage[] = [];
	export let loading = false;

	function formatTime(timestamp: string): string {
		try {
			const date = new Date(timestamp);
			return date.toLocaleTimeString('ja-JP', {
				hour: '2-digit',
				minute: '2-digit',
				second: '2-digit'
			});
		} catch {
			return timestamp;
		}
	}

	function formatDate(timestamp: string): string {
		try {
			const date = new Date(timestamp);
			return date.toLocaleDateString('ja-JP', {
				year: 'numeric',
				month: 'short',
				day: 'numeric'
			});
		} catch {
			return '';
		}
	}

	// Group messages by date
	$: groupedMessages = messages.reduce(
		(groups, message) => {
			const date = formatDate(message.timestamp);
			if (!groups[date]) {
				groups[date] = [];
			}
			groups[date].push(message);
			return groups;
		},
		{} as Record<string, DiagnosticMessage[]>
	);
</script>

<div class="conversation-timeline" data-testid="conversation-timeline">
	{#if loading}
		<div class="space-y-4 animate-pulse">
			{#each [0, 1, 2, 3] as i (i)}
				<div class="flex gap-3">
					<div class="w-8 h-8 rounded-full bg-gray-300 dark:bg-gray-600"></div>
					<div class="flex-1">
						<div class="h-4 bg-gray-300 dark:bg-gray-600 rounded w-1/4 mb-2"></div>
						<div class="h-16 bg-gray-300 dark:bg-gray-600 rounded"></div>
					</div>
				</div>
			{/each}
		</div>
	{:else if messages.length === 0}
		<div class="text-center py-8 text-gray-500 dark:text-gray-400" data-testid="no-messages">
			No messages in this conversation
		</div>
	{:else}
		<div class="space-y-6">
			{#each Object.entries(groupedMessages) as [date, dateMessages]}
				<!-- Date Separator -->
				<div class="flex items-center gap-3">
					<div class="flex-1 h-px bg-gray-200 dark:bg-gray-700"></div>
					<span class="text-xs text-gray-500 dark:text-gray-400 font-medium">
						{date}
					</span>
					<div class="flex-1 h-px bg-gray-200 dark:bg-gray-700"></div>
				</div>

				<!-- Messages for this date -->
				{#each dateMessages as message}
					<div
						class="flex gap-3 {message.role === 'user' ? 'flex-row-reverse' : ''}"
						data-testid="message-{message.role}"
					>
						<!-- Avatar -->
						<div
							class="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center
								{message.role === 'user'
								? 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400'
								: 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400'}"
						>
							{#if message.role === 'user'}
								<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
									<path
										fill-rule="evenodd"
										d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z"
										clip-rule="evenodd"
									/>
								</svg>
							{:else}
								<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
									<path d="M2 10a8 8 0 018-8v8h8a8 8 0 11-16 0z" />
									<path d="M12 2.252A8.014 8.014 0 0117.748 8H12V2.252z" />
								</svg>
							{/if}
						</div>

						<!-- Message Content -->
						<div class="flex-1 max-w-[80%] {message.role === 'user' ? 'text-right' : ''}">
							<!-- Header -->
							<div
								class="flex items-center gap-2 mb-1 {message.role === 'user' ? 'justify-end' : ''}"
							>
								<span class="text-sm font-medium text-gray-900 dark:text-gray-100">
									{message.role === 'user' ? 'User' : 'Assistant'}
								</span>
								<span class="text-xs text-gray-500 dark:text-gray-400">
									{formatTime(message.timestamp)}
								</span>
							</div>

							<!-- Content -->
							<div
								class="p-3 rounded-lg {message.role === 'user'
									? 'bg-blue-100 dark:bg-blue-900/30 text-blue-900 dark:text-blue-100'
									: 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100'}"
							>
								<p class="text-sm whitespace-pre-wrap break-words">
									{message.content}
								</p>
							</div>
						</div>
					</div>
				{/each}
			{/each}
		</div>
	{/if}
</div>

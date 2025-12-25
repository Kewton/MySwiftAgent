/**
 * Formatting Utilities
 * Issue #292: Review Page (JobVersion Detail)
 *
 * Common formatting functions used across the application.
 * Extracted to eliminate code duplication (DRY principle).
 */

/**
 * Format a date string to Japanese locale format.
 *
 * @param dateString - ISO date string or null
 * @returns Formatted date string or '-' if null
 *
 * @example
 * formatDate('2024-01-15T10:30:00.000Z') // '2024/01/15 19:30'
 * formatDate(null) // '-'
 */
export function formatDate(dateString: string | null): string {
	if (!dateString) return '-';
	const date = new Date(dateString);
	return date.toLocaleDateString('ja-JP', {
		year: 'numeric',
		month: '2-digit',
		day: '2-digit',
		hour: '2-digit',
		minute: '2-digit'
	});
}

/**
 * Format JSON object to pretty-printed string.
 *
 * @param obj - Object to format
 * @param fallback - Fallback value if obj is null/undefined
 * @returns Formatted JSON string
 *
 * @example
 * formatJson({ name: 'test' }) // '{\n  "name": "test"\n}'
 * formatJson(null, '{}') // '{}'
 */
export function formatJson(obj: unknown, fallback = ''): string {
	if (!obj) return fallback;
	try {
		return JSON.stringify(obj, null, 2);
	} catch {
		return String(obj);
	}
}

/**
 * Generate Langfuse trace URL.
 *
 * @param traceId - Langfuse trace ID
 * @param baseUrl - Langfuse base URL (defaults to localhost:3001)
 * @returns Trace URL or null if traceId is null
 *
 * @example
 * getLangfuseUrl('abc123') // 'http://localhost:3001/trace/abc123'
 * getLangfuseUrl(null) // null
 */
export function getLangfuseUrl(
	traceId: string | null,
	baseUrl = 'http://localhost:3001'
): string | null {
	if (!traceId) return null;
	return `${baseUrl}/trace/${traceId}`;
}

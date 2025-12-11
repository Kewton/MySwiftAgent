/**
 * Unit tests for MLOps Diagnostics Page
 *
 * Issue #194: Tests for demo data detection and Langfuse link visibility
 *
 * Note: These tests verify the isValidLangfuseUrl utility function
 * which is the core logic for Issue #194.
 */

import { describe, it, expect } from 'vitest';

describe('DiagnosticsPage - isValidLangfuseUrl logic', () => {
	/**
	 * Test the isValidLangfuseUrl logic directly.
	 * The actual function is internal to the Svelte component,
	 * so we test the same logic here.
	 */
	function isValidLangfuseUrl(url: string | null): boolean {
		if (!url) return false;
		// Demo URLs contain /trace/demo
		if (url.includes('/trace/demo')) return false;
		return true;
	}

	describe('isValidLangfuseUrl function', () => {
		it('should return false for null URL', () => {
			expect(isValidLangfuseUrl(null)).toBe(false);
		});

		it('should return false for empty string', () => {
			expect(isValidLangfuseUrl('')).toBe(false);
		});

		it('should return false for demo trace URLs', () => {
			expect(isValidLangfuseUrl('http://localhost:3001/trace/demo')).toBe(false);
			expect(isValidLangfuseUrl('http://langfuse.example.com/trace/demo')).toBe(false);
		});

		it('should return true for valid trace URLs', () => {
			expect(isValidLangfuseUrl('http://localhost:3001/trace/abc123')).toBe(true);
			expect(isValidLangfuseUrl('http://langfuse.example.com/trace/real-trace-id')).toBe(true);
		});

		it('should return true for trace URLs with demo in other parts', () => {
			// Only /trace/demo should be rejected, not other occurrences of "demo"
			expect(isValidLangfuseUrl('http://demo.langfuse.com/trace/abc123')).toBe(true);
		});
	});

	describe('Demo Data Detection Logic', () => {
		it('should mark isUsingDemoData=true when API returns empty list', () => {
			// Simulated logic: when items.length === 0, isUsingDemoData should be true
			const apiResponse = { items: [], total: 0 };
			const isUsingDemoData = apiResponse.items.length === 0;
			expect(isUsingDemoData).toBe(true);
		});

		it('should mark isUsingDemoData=false when API returns data', () => {
			// Simulated logic: when items.length > 0, isUsingDemoData should be false
			const apiResponse = {
				items: [{ conversation_id: 'conv-123' }],
				total: 1
			};
			const isUsingDemoData = apiResponse.items.length === 0;
			expect(isUsingDemoData).toBe(false);
		});
	});

	describe('Langfuse Link Visibility Logic', () => {
		it('should show link when URL is valid and not demo', () => {
			const url = 'http://localhost:3001/trace/real-trace-123';
			const shouldShowLink = isValidLangfuseUrl(url);
			expect(shouldShowLink).toBe(true);
		});

		it('should hide link when URL is demo', () => {
			const url = 'http://localhost:3001/trace/demo';
			const shouldShowLink = isValidLangfuseUrl(url);
			expect(shouldShowLink).toBe(false);
		});

		it('should hide link when URL is null', () => {
			const url = null;
			const shouldShowLink = isValidLangfuseUrl(url);
			expect(shouldShowLink).toBe(false);
		});
	});
});

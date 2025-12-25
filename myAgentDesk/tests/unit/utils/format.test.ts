/**
 * Format Utilities Tests
 * Issue #292: Review Page (JobVersion Detail)
 */

import { describe, it, expect } from 'vitest';
import { formatDate, formatJson, getLangfuseUrl } from '$lib/utils/format';

describe('formatDate', () => {
	it('should return "-" for null input', () => {
		expect(formatDate(null)).toBe('-');
	});

	it('should format a valid date string', () => {
		// Create a date in JST timezone
		const dateString = '2024-01-15T10:30:00.000Z';
		const result = formatDate(dateString);

		// The result should contain date components
		expect(result).toMatch(/\d{4}\/\d{2}\/\d{2}/);
		expect(result).toMatch(/\d{2}:\d{2}/);
	});

	it('should handle various date formats', () => {
		const dateString = '2023-12-25T00:00:00.000Z';
		const result = formatDate(dateString);
		expect(result).toBeTruthy();
		expect(result).not.toBe('-');
	});
});

describe('formatJson', () => {
	it('should return empty string for null with default fallback', () => {
		expect(formatJson(null)).toBe('');
	});

	it('should return custom fallback for null', () => {
		expect(formatJson(null, '{}')).toBe('{}');
	});

	it('should return empty string for undefined with default fallback', () => {
		expect(formatJson(undefined)).toBe('');
	});

	it('should format a simple object', () => {
		const obj = { name: 'test' };
		const result = formatJson(obj);
		expect(result).toBe('{\n  "name": "test"\n}');
	});

	it('should format nested objects', () => {
		const obj = { level1: { level2: { value: 42 } } };
		const result = formatJson(obj);
		expect(result).toContain('"level1"');
		expect(result).toContain('"level2"');
		expect(result).toContain('42');
	});

	it('should format arrays', () => {
		const arr = [1, 2, 3];
		const result = formatJson(arr);
		expect(result).toContain('1');
		expect(result).toContain('2');
		expect(result).toContain('3');
	});

	it('should handle objects with circular references gracefully', () => {
		const obj: Record<string, unknown> = { name: 'test' };
		obj.self = obj; // Create circular reference
		const result = formatJson(obj);
		// Should return string representation instead of throwing
		expect(result).toBe('[object Object]');
	});

	it('should handle primitive values', () => {
		expect(formatJson('hello')).toBe('"hello"');
		expect(formatJson(42)).toBe('42');
		expect(formatJson(true)).toBe('true');
	});
});

describe('getLangfuseUrl', () => {
	it('should return null for null input', () => {
		expect(getLangfuseUrl(null)).toBeNull();
	});

	it('should return default localhost URL', () => {
		const result = getLangfuseUrl('abc123');
		expect(result).toBe('http://localhost:3001/trace/abc123');
	});

	it('should use custom base URL', () => {
		const result = getLangfuseUrl('xyz789', 'https://langfuse.example.com');
		expect(result).toBe('https://langfuse.example.com/trace/xyz789');
	});

	it('should handle trace IDs with special characters', () => {
		const result = getLangfuseUrl('trace-id-with-dashes');
		expect(result).toBe('http://localhost:3001/trace/trace-id-with-dashes');
	});

	it('should handle empty string trace ID', () => {
		// Empty string is falsy, so should return null
		const result = getLangfuseUrl('');
		expect(result).toBeNull();
	});
});

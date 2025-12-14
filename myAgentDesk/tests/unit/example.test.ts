import { describe, it, expect } from 'vitest';

describe('Example Test Suite', () => {
	it('should pass a basic test', () => {
		expect(1 + 1).toBe(2);
	});

	it('should handle string operations', () => {
		const greeting = 'Hello, SvelteKit!';
		expect(greeting).toContain('SvelteKit');
	});
});

/**
 * @file Result<T, E> type tests
 * @description TDD Phase 1: RED - Tests for unified Result type pattern
 */

import { describe, it, expect } from 'vitest';
import {
	ok,
	err,
	isOk,
	isErr,
	unwrap,
	unwrapOr,
	map,
	mapErr,
	andThen,
	type Result
} from '../result';

describe('Result<T, E>', () => {
	describe('ok()', () => {
		it('should create a success result', () => {
			const result = ok('hello');
			expect(result.ok).toBe(true);
			expect(result.value).toBe('hello');
		});

		it('should handle complex types', () => {
			const data = { id: 1, name: 'test' };
			const result = ok(data);
			expect(result.ok).toBe(true);
			expect(result.value).toEqual(data);
		});
	});

	describe('err()', () => {
		it('should create an error result', () => {
			const error = new Error('test error');
			const result = err(error);
			expect(result.ok).toBe(false);
			expect(result.error).toBe(error);
		});

		it('should handle string errors', () => {
			const result = err('string error');
			expect(result.ok).toBe(false);
			expect(result.error).toBe('string error');
		});
	});

	describe('isOk()', () => {
		it('should return true for success results', () => {
			const result = ok('value');
			expect(isOk(result)).toBe(true);
		});

		it('should return false for error results', () => {
			const result = err('error');
			expect(isOk(result)).toBe(false);
		});
	});

	describe('isErr()', () => {
		it('should return false for success results', () => {
			const result = ok('value');
			expect(isErr(result)).toBe(false);
		});

		it('should return true for error results', () => {
			const result = err('error');
			expect(isErr(result)).toBe(true);
		});
	});

	describe('unwrap()', () => {
		it('should return value for success results', () => {
			const result = ok('hello');
			expect(unwrap(result)).toBe('hello');
		});

		it('should throw for error results', () => {
			const result = err('error');
			expect(() => unwrap(result)).toThrow('Tried to unwrap an Err value: error');
		});
	});

	describe('unwrapOr()', () => {
		it('should return value for success results', () => {
			const result = ok('hello');
			expect(unwrapOr(result, 'default')).toBe('hello');
		});

		it('should return default for error results', () => {
			const result = err('error');
			expect(unwrapOr(result, 'default')).toBe('default');
		});
	});

	describe('map()', () => {
		it('should transform success values', () => {
			const result = ok(5);
			const mapped = map(result, (x) => x * 2);
			expect(isOk(mapped)).toBe(true);
			if (isOk(mapped)) {
				expect(mapped.value).toBe(10);
			}
		});

		it('should pass through error values', () => {
			const result = err<number, string>('error');
			const mapped = map(result, (x) => x * 2);
			expect(isErr(mapped)).toBe(true);
			if (isErr(mapped)) {
				expect(mapped.error).toBe('error');
			}
		});
	});

	describe('mapErr()', () => {
		it('should pass through success values', () => {
			const result: Result<number, string> = ok(5);
			const mapped = mapErr(result, (e) => `Wrapped: ${e}`);
			expect(isOk(mapped)).toBe(true);
			if (isOk(mapped)) {
				expect(mapped.value).toBe(5);
			}
		});

		it('should transform error values', () => {
			const result = err<number, string>('error');
			const mapped = mapErr(result, (e) => `Wrapped: ${e}`);
			expect(isErr(mapped)).toBe(true);
			if (isErr(mapped)) {
				expect(mapped.error).toBe('Wrapped: error');
			}
		});
	});

	describe('andThen()', () => {
		it('should chain success operations', () => {
			const result = ok(5);
			const chained = andThen(result, (x) => ok(x * 2));
			expect(isOk(chained)).toBe(true);
			if (isOk(chained)) {
				expect(chained.value).toBe(10);
			}
		});

		it('should short-circuit on error', () => {
			const result = err<number, string>('error');
			const chained = andThen(result, (x) => ok(x * 2));
			expect(isErr(chained)).toBe(true);
			if (isErr(chained)) {
				expect(chained.error).toBe('error');
			}
		});

		it('should propagate errors from chained operations', () => {
			const result = ok(5);
			const chained = andThen(result, () => err<number, string>('chained error'));
			expect(isErr(chained)).toBe(true);
			if (isErr(chained)) {
				expect(chained.error).toBe('chained error');
			}
		});
	});
});

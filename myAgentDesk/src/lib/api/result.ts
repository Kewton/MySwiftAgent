/**
 * @file Result<T, E> type implementation
 * @description Unified Result type pattern for type-safe error handling
 */

/**
 * Success result type
 */
export interface Ok<T> {
	ok: true;
	value: T;
}

/**
 * Error result type
 */
export interface Err<E> {
	ok: false;
	error: E;
}

/**
 * Result type - Either a success value or an error
 */
export type Result<T, E> = Ok<T> | Err<E>;

/**
 * Create a success result
 */
export function ok<T>(value: T): Ok<T> {
	return { ok: true, value };
}

/**
 * Create an error result
 */
export function err<E>(error: E): Err<E>;
export function err<T, E>(error: E): Result<T, E>;
export function err<T, E>(error: E): Err<E> | Result<T, E> {
	return { ok: false, error };
}

/**
 * Type guard for success results
 */
export function isOk<T, E>(result: Result<T, E>): result is Ok<T> {
	return result.ok === true;
}

/**
 * Type guard for error results
 */
export function isErr<T, E>(result: Result<T, E>): result is Err<E> {
	return result.ok === false;
}

/**
 * Extract value from success result, throws on error
 */
export function unwrap<T, E>(result: Result<T, E>): T {
	if (isOk(result)) {
		return result.value;
	}
	throw new Error(`Tried to unwrap an Err value: ${result.error}`);
}

/**
 * Extract value or return default
 */
export function unwrapOr<T, E>(result: Result<T, E>, defaultValue: T): T {
	if (isOk(result)) {
		return result.value;
	}
	return defaultValue;
}

/**
 * Transform success value
 */
export function map<T, U, E>(result: Result<T, E>, fn: (value: T) => U): Result<U, E> {
	if (isOk(result)) {
		return ok(fn(result.value));
	}
	return result;
}

/**
 * Transform error value
 */
export function mapErr<T, E, F>(result: Result<T, E>, fn: (error: E) => F): Result<T, F> {
	if (isErr(result)) {
		return err(fn(result.error));
	}
	return result;
}

/**
 * Chain Result operations (flatMap)
 */
export function andThen<T, U, E>(
	result: Result<T, E>,
	fn: (value: T) => Result<U, E>
): Result<U, E> {
	if (isOk(result)) {
		return fn(result.value);
	}
	return result;
}

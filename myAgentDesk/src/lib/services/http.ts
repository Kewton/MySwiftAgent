import { ServiceError } from './types';
import { getApiBase } from './config';

interface RequestOptions extends RequestInit {
	path: string;
}

const JSON_HEADERS = {
	'Content-Type': 'application/json'
};

export interface FetchJsonOptions extends Omit<RequestOptions, 'body'> {
	body?: unknown;
	skipDefaultHeaders?: boolean;
}

export async function fetchJson<T>({
	path,
	body,
	skipDefaultHeaders,
	headers,
	method = 'GET',
	...rest
}: FetchJsonOptions): Promise<T> {
	const url = `${getApiBase()}${path}`;
	const requestHeaders = new Headers(headers);

	if (!skipDefaultHeaders) {
		Object.entries(JSON_HEADERS).forEach(([key, value]) => {
			if (!requestHeaders.has(key)) {
				requestHeaders.set(key, value);
			}
		});
	}

	let response: Response;

	try {
		response = await fetch(url, {
			method,
			headers: requestHeaders,
			body: body === undefined ? undefined : JSON.stringify(body),
			...rest
		});
	} catch (error) {
		throw new ServiceError(`Failed to fetch ${path}`, undefined, error);
	}

	let parsed: unknown = null;
	const rawText = await response.text();

	if (rawText) {
		try {
			parsed = JSON.parse(rawText);
		} catch (error) {
			throw new ServiceError('Failed to parse JSON response', response.status, error);
		}
	}

	if (!response.ok) {
		const detail = (parsed as { detail?: string })?.detail;
		throw new ServiceError(
			detail || `HTTP ${response.status}: ${response.statusText}`,
			response.status,
			parsed
		);
	}

	return parsed as T;
}

export interface StreamSseOptions<TEvent> extends Omit<RequestOptions, 'body'> {
	body?: unknown;
	signal?: AbortSignal;
	onEvent: (event: TEvent) => void;
}

const LINE_BREAK = /\r?\n/;

export async function streamSse<TEvent>(options: StreamSseOptions<TEvent>): Promise<void> {
	const { path, body, headers, signal, onEvent, method = 'POST', ...rest } = options;
	const url = `${getApiBase()}${path}`;
	const requestHeaders = new Headers(headers ?? JSON_HEADERS);

	let response: Response;

	try {
		response = await fetch(url, {
			method,
			headers: requestHeaders,
			body: body === undefined ? undefined : JSON.stringify(body),
			signal,
			...rest
		});
	} catch (error) {
		throw new ServiceError(`Failed to connect to ${path}`, undefined, error);
	}

	if (!response.ok) {
		throw new ServiceError(`HTTP ${response.status}: ${response.statusText}`, response.status);
	}

	const reader = response.body?.getReader();

	if (!reader) {
		throw new ServiceError('Response body is not readable');
	}

	const decoder = new TextDecoder();
	let buffer = '';

	try {
		// eslint-disable-next-line no-constant-condition
		while (true) {
			const { done, value } = await reader.read();
			if (done) {
				processBuffer(buffer, onEvent);
				break;
			}

			buffer += decoder.decode(value, { stream: true });
			const lines = buffer.split(LINE_BREAK);

			buffer = lines.pop() || '';

			for (const line of lines) {
				processLine(line, onEvent);
			}
		}
	} catch (error) {
		if (signal?.aborted) return;
		throw new ServiceError('Error processing stream data', undefined, error);
	}
}

function processBuffer<TEvent>(buffer: string, onEvent: (event: TEvent) => void) {
	if (!buffer.trim()) return;
	processLine(buffer, onEvent);
}

function processLine<TEvent>(line: string, onEvent: (event: TEvent) => void) {
	const trimmed = line.trim();
	if (!trimmed.startsWith('data:')) return;
	const payload = trimmed.substring(5).trimStart();
	if (!payload) return;
	onEvent(JSON.parse(payload));
}

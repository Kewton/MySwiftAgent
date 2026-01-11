/**
 * REST API Node Implementation
 *
 * This node executes HTTP requests to external APIs.
 * Includes comprehensive security features:
 * - SSRF protection (blocks private IPs, metadata endpoints)
 * - HTTPS enforcement
 * - SSL certificate verification
 * - Domain whitelisting support
 *
 * @module nodes/api-rest-node
 * @see Issue #348 - Must Fix: SSRF Protection, HTTPS Enforcement
 */

import type { ApiRestConfig, ApiRestStep, HttpMethod } from '../types/taskflow.js';
import { BaseNode, ApiError, TimeoutError, NodeExecutionError } from './base-node.js';
import { ContextManager } from '../engine/context/context-manager.js';
import {
  validateUrl,
  validateResolvedUrl,
  hasVariableReferences,
  SecurityError,
} from '../engine/validator/url-validator.js';
import https from 'https';
import http from 'http';

// ============================================================
// Types
// ============================================================

interface HttpRequestOptions {
  method: HttpMethod;
  headers: Record<string, string>;
  body?: string;
  timeout: number;
  rejectUnauthorized: boolean;
}

interface HttpResponse {
  statusCode: number;
  headers: Record<string, string | string[] | undefined>;
  body: unknown;
}

// ============================================================
// HTTP Client
// ============================================================

/**
 * Execute an HTTP request with timeout support
 * @param url - Request URL
 * @param options - Request options
 * @returns HTTP response
 */
async function executeHttpRequest(
  url: string,
  options: HttpRequestOptions
): Promise<HttpResponse> {
  return new Promise((resolve, reject) => {
    const parsedUrl = new URL(url);
    const isHttps = parsedUrl.protocol === 'https:';

    const requestOptions = {
      hostname: parsedUrl.hostname,
      port: parsedUrl.port || (isHttps ? 443 : 80),
      path: parsedUrl.pathname + parsedUrl.search,
      method: options.method,
      headers: options.headers,
      timeout: options.timeout,
      rejectUnauthorized: options.rejectUnauthorized,
    };

    const httpModule = isHttps ? https : http;

    const req = httpModule.request(requestOptions, (res) => {
      const chunks: Buffer[] = [];

      res.on('data', (chunk) => {
        chunks.push(chunk);
      });

      res.on('end', () => {
        const bodyStr = Buffer.concat(chunks).toString('utf8');
        let body: unknown;

        // Try to parse as JSON
        const contentType = res.headers['content-type'] || '';
        if (contentType.includes('application/json')) {
          try {
            body = JSON.parse(bodyStr);
          } catch {
            body = bodyStr;
          }
        } else {
          body = bodyStr;
        }

        resolve({
          statusCode: res.statusCode || 500,
          headers: res.headers as Record<string, string | string[] | undefined>,
          body,
        });
      });
    });

    req.on('error', (error) => {
      reject(new Error(`HTTP request failed: ${error.message}`));
    });

    req.on('timeout', () => {
      req.destroy();
      reject(new TimeoutError(`Request timed out after ${options.timeout}ms`, options.timeout));
    });

    if (options.body) {
      req.write(options.body);
    }

    req.end();
  });
}

// ============================================================
// API REST Node Class
// ============================================================

/**
 * REST API Node for executing HTTP requests
 *
 * Security Features:
 * - SSRF protection via URL validation
 * - HTTPS enforcement (HTTP disabled by default)
 * - SSL certificate verification (enabled by default)
 * - Domain whitelist support via environment variable
 */
export class ApiRestNode extends BaseNode<ApiRestConfig> {
  constructor(step: ApiRestStep) {
    super(step);
  }

  /**
   * Execute the API request
   * @param params - Resolved parameters
   * @param context - Execution context
   * @returns API response
   */
  protected async executeInternal(
    params: Record<string, unknown>,
    context: ContextManager
  ): Promise<unknown> {
    // 1. Resolve URL (may contain variable references)
    const resolvedUrl = await this.resolveUrl(context);

    // 2. Validate resolved URL for security
    this.validateSecureUrl(resolvedUrl);

    // 3. Build request headers
    const headers = await this.buildHeaders(context);

    // 4. Build request body
    const body = await this.buildBody(context, headers);

    // 5. Execute HTTP request
    const response = await this.executeRequest(resolvedUrl, headers, body);

    // 6. Handle response
    return this.handleResponse(response);
  }

  /**
   * Resolve URL with variable references
   * @param context - Execution context
   * @returns Fully resolved URL
   */
  private async resolveUrl(context: ContextManager): Promise<string> {
    const url = this.config.url;

    // If URL contains variable references, resolve them
    if (hasVariableReferences(url)) {
      const resolved = await context.resolve(url);
      if (typeof resolved !== 'string') {
        throw new NodeExecutionError(
          'URL must resolve to a string',
          'INVALID_URL'
        );
      }
      return resolved;
    }

    return url;
  }

  /**
   * Validate URL for security (SSRF protection)
   * @param url - URL to validate
   * @throws SecurityError if URL is blocked
   */
  private validateSecureUrl(url: string): void {
    // First check: validate URL structure
    const initialValidation = validateUrl(url);
    if (!initialValidation.valid) {
      throw new SecurityError(
        `URL validation failed: ${initialValidation.error}`,
        initialValidation.securityIssue
      );
    }

    // Second check: validate resolved URL
    const resolvedValidation = validateResolvedUrl(url);
    if (!resolvedValidation.valid) {
      throw new SecurityError(
        `URL security check failed: ${resolvedValidation.error}`,
        resolvedValidation.securityIssue
      );
    }
  }

  /**
   * Build request headers with variable resolution
   * @param context - Execution context
   * @returns Resolved headers
   */
  private async buildHeaders(context: ContextManager): Promise<Record<string, string>> {
    const headers: Record<string, string> = {};

    if (this.config.headers) {
      for (const [key, value] of Object.entries(this.config.headers)) {
        const resolved = await context.resolve(value);
        headers[key] = String(resolved);
      }
    }

    return headers;
  }

  /**
   * Build request body with variable resolution
   * @param context - Execution context
   * @param headers - Request headers (for Content-Type)
   * @returns Serialized body or undefined
   */
  private async buildBody(
    context: ContextManager,
    headers: Record<string, string>
  ): Promise<string | undefined> {
    if (!this.config.body) {
      return undefined;
    }

    const resolved = await context.resolve(this.config.body);

    if (resolved === undefined || resolved === null) {
      return undefined;
    }

    // Serialize based on Content-Type
    const contentType = headers['Content-Type'] || headers['content-type'] || '';

    if (contentType.includes('application/json')) {
      return JSON.stringify(resolved);
    }

    if (typeof resolved === 'string') {
      return resolved;
    }

    // Default to JSON serialization
    if (!contentType) {
      headers['Content-Type'] = 'application/json';
    }
    return JSON.stringify(resolved);
  }

  /**
   * Execute the HTTP request
   * @param url - Request URL
   * @param headers - Request headers
   * @param body - Request body
   * @returns HTTP response
   */
  private async executeRequest(
    url: string,
    headers: Record<string, string>,
    body?: string
  ): Promise<HttpResponse> {
    const timeout = this.config.timeout_ms || 30000;
    const verifySsl = this.config.verify_ssl !== false;

    console.log(`[ApiRestNode:${this.id}] ${this.config.method} ${url}`);

    const response = await executeHttpRequest(url, {
      method: this.config.method,
      headers,
      body,
      timeout,
      rejectUnauthorized: verifySsl,
    });

    console.log(`[ApiRestNode:${this.id}] Response: ${response.statusCode}`);

    return response;
  }

  /**
   * Handle HTTP response
   * @param response - HTTP response
   * @returns Response body for success, throws for errors
   */
  private handleResponse(response: HttpResponse): unknown {
    // Success: 2xx status codes
    if (response.statusCode >= 200 && response.statusCode < 300) {
      return response.body;
    }

    // Client error: 4xx status codes
    if (response.statusCode >= 400 && response.statusCode < 500) {
      throw new ApiError(
        `API returned ${response.statusCode}: ${this.extractErrorMessage(response.body)}`,
        response.statusCode,
        response.body
      );
    }

    // Server error: 5xx status codes
    throw new ApiError(
      `API returned ${response.statusCode}: ${this.extractErrorMessage(response.body)}`,
      response.statusCode,
      response.body
    );
  }

  /**
   * Extract error message from response body
   * @param body - Response body
   * @returns Error message string
   */
  private extractErrorMessage(body: unknown): string {
    if (typeof body === 'string') {
      return body.slice(0, 200);
    }

    if (body && typeof body === 'object') {
      const bodyObj = body as Record<string, unknown>;

      // Common error message fields
      if (bodyObj.error && typeof bodyObj.error === 'string') {
        return bodyObj.error;
      }
      if (bodyObj.message && typeof bodyObj.message === 'string') {
        return bodyObj.message;
      }
      if (bodyObj.error_description && typeof bodyObj.error_description === 'string') {
        return bodyObj.error_description;
      }

      return JSON.stringify(body).slice(0, 200);
    }

    return 'Unknown error';
  }
}

// ============================================================
// Factory Function
// ============================================================

/**
 * Create an API REST node from a step definition
 * @param step - Step definition
 * @returns ApiRestNode instance
 */
export function createApiRestNode(step: ApiRestStep): ApiRestNode {
  return new ApiRestNode(step);
}

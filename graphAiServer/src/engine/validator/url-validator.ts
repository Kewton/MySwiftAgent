/**
 * URL Validator with SSRF Protection
 *
 * This module provides URL validation with comprehensive SSRF (Server-Side Request Forgery) protection.
 * It blocks access to private IP addresses, metadata endpoints, and enforces HTTPS.
 *
 * Security Features:
 * - Private IP range blocking (RFC 1918, RFC 6598, loopback, link-local)
 * - Cloud metadata endpoint blocking (AWS, GCP, Azure)
 * - HTTPS enforcement (HTTP disabled by default)
 * - Domain whitelist support
 * - IPv6 private address blocking
 *
 * @module engine/validator/url-validator
 * @see Issue #348 - SSRF Protection (Must Fix)
 */

import type { UrlValidationResult } from '../../types/taskflow.js';

// ============================================================
// Configuration
// ============================================================

/**
 * Get allowed domains from environment variable
 * Format: comma-separated list of domains
 * Supports wildcards: *.example.com
 */
function getAllowedDomains(): string[] {
  const domainsEnv = process.env.TASKFLOW_ALLOWED_DOMAINS || '';
  return domainsEnv
    .split(',')
    .map((d) => d.trim())
    .filter(Boolean);
}

/**
 * Check if HTTP is allowed (development only, disabled by default)
 */
function isHttpAllowed(): boolean {
  return process.env.TASKFLOW_ALLOW_HTTP === 'true';
}

/**
 * Check if local/private IPs are allowed (development only, disabled by default)
 * When enabled, allows localhost, 127.0.0.1, 192.168.x.x, etc.
 */
function isLocalAllowed(): boolean {
  return process.env.TASKFLOW_ALLOW_LOCAL === 'true';
}

// ============================================================
// Private IP Range Patterns
// ============================================================

/**
 * Regular expressions for private and reserved IP ranges
 * Based on RFC 1918, RFC 6598, and other reserved address spaces
 */
const PRIVATE_IP_PATTERNS: RegExp[] = [
  // IPv4 Loopback (127.0.0.0/8)
  /^127\./,

  // IPv4 Class A Private (10.0.0.0/8)
  /^10\./,

  // IPv4 Class B Private (172.16.0.0/12)
  /^172\.(1[6-9]|2[0-9]|3[01])\./,

  // IPv4 Class C Private (192.168.0.0/16)
  /^192\.168\./,

  // IPv4 Link-Local (169.254.0.0/16)
  /^169\.254\./,

  // IPv4 Current Network (0.0.0.0/8)
  /^0\./,

  // IPv4 Shared Address Space (100.64.0.0/10) - RFC 6598
  /^100\.(6[4-9]|[7-9][0-9]|1[01][0-9]|12[0-7])\./,

  // IPv4 Broadcast
  /^255\.255\.255\.255$/,

  // IPv6 Loopback (::1)
  /^::1$/,

  // IPv6 Unique Local Address (fc00::/7)
  /^fc00:/i,
  /^fd[0-9a-f]{2}:/i,

  // IPv6 Link-Local (fe80::/10)
  /^fe80:/i,

  // IPv6 Private (deprecated site-local fec0::/10)
  /^fec0:/i,

  // IPv4-mapped IPv6 addresses for private ranges
  /^::ffff:127\./i,
  /^::ffff:10\./i,
  /^::ffff:172\.(1[6-9]|2[0-9]|3[01])\./i,
  /^::ffff:192\.168\./i,
  /^::ffff:169\.254\./i,
];

// ============================================================
// Blocked Hostnames
// ============================================================

/**
 * List of blocked hostnames including:
 * - localhost and its aliases
 * - Cloud provider metadata endpoints
 */
const BLOCKED_HOSTNAMES: string[] = [
  // Localhost variants
  'localhost',
  'localhost.localdomain',

  // Cloud metadata endpoints
  '169.254.169.254', // AWS, GCP, Azure metadata
  'metadata.google.internal', // GCP metadata
  'metadata.goog', // GCP alternative
  'metadata.azure.com', // Azure metadata
  'metadata.azure.com.', // Azure with trailing dot
  'instance-data.ec2.internal', // AWS EC2 internal

  // Kubernetes internal
  'kubernetes.default',
  'kubernetes.default.svc',
  'kubernetes.default.svc.cluster.local',

  // Docker internal
  'host.docker.internal',
  'gateway.docker.internal',
];

/**
 * Blocked hostname patterns (for dynamic matching)
 */
const BLOCKED_HOSTNAME_PATTERNS: RegExp[] = [
  // Any subdomain of metadata.google.internal
  /^.*\.metadata\.google\.internal$/i,
  // EC2 metadata patterns
  /^.*\.ec2\.internal$/i,
  // AWS internal
  /^.*\.amazonaws\.com\.internal$/i,
];

// ============================================================
// Validation Functions
// ============================================================

/**
 * Check if an IP address is in a private or reserved range
 * @param ip - IP address to check
 * @returns true if the IP is private/reserved
 */
function isPrivateIP(ip: string): boolean {
  return PRIVATE_IP_PATTERNS.some((pattern) => pattern.test(ip));
}

/**
 * Check if a hostname is blocked
 * @param hostname - Hostname to check
 * @returns true if the hostname is blocked
 */
function isBlockedHostname(hostname: string): boolean {
  const lowerHostname = hostname.toLowerCase();

  // Check exact matches
  if (BLOCKED_HOSTNAMES.includes(lowerHostname)) {
    return true;
  }

  // Check patterns
  if (BLOCKED_HOSTNAME_PATTERNS.some((pattern) => pattern.test(lowerHostname))) {
    return true;
  }

  return false;
}

/**
 * Check if a hostname is in the allowed domains whitelist
 * @param hostname - Hostname to check
 * @param allowedDomains - List of allowed domains
 * @returns true if the hostname matches the whitelist
 */
function matchesWhitelist(hostname: string, allowedDomains: string[]): boolean {
  if (allowedDomains.length === 0) {
    return true; // No whitelist = all domains allowed
  }

  const lowerHostname = hostname.toLowerCase();

  return allowedDomains.some((domain) => {
    const lowerDomain = domain.toLowerCase();

    if (lowerDomain.startsWith('*.')) {
      // Wildcard match: *.example.com matches sub.example.com
      const suffix = lowerDomain.slice(1); // .example.com
      const baseDomain = lowerDomain.slice(2); // example.com
      return lowerHostname.endsWith(suffix) || lowerHostname === baseDomain;
    }

    // Exact match
    return lowerHostname === lowerDomain;
  });
}

/**
 * Check if a string looks like an IP address (IPv4 or IPv6)
 * @param str - String to check
 * @returns true if the string appears to be an IP address
 */
function looksLikeIP(str: string): boolean {
  // IPv4 pattern
  const ipv4Pattern = /^(\d{1,3}\.){3}\d{1,3}$/;
  if (ipv4Pattern.test(str)) {
    return true;
  }

  // IPv6 pattern (simplified check)
  if (str.includes(':')) {
    return true;
  }

  return false;
}

// ============================================================
// Main Validation Function
// ============================================================

/**
 * Validate a URL for SSRF protection
 *
 * This function performs comprehensive security checks:
 * 1. HTTPS protocol enforcement
 * 2. Private IP address blocking
 * 3. Blocked hostname detection
 * 4. Domain whitelist validation
 *
 * @param urlString - URL to validate
 * @returns Validation result with detailed error information
 *
 * @example
 * ```typescript
 * const result = validateUrl('https://api.example.com/data');
 * if (!result.valid) {
 *   console.error(`URL blocked: ${result.error}`);
 * }
 * ```
 */
export function validateUrl(urlString: string): UrlValidationResult {
  // Handle variable references - these will be resolved later
  if (urlString.startsWith('${env.') || urlString.startsWith('${secrets.')) {
    // Variable references are validated at resolution time
    return { valid: true };
  }

  // Parse URL
  let url: URL;
  try {
    url = new URL(urlString);
  } catch {
    return {
      valid: false,
      error: 'Invalid URL format',
    };
  }

  // 1. Protocol check - HTTPS required
  const httpAllowed = isHttpAllowed();
  if (url.protocol === 'http:' && !httpAllowed) {
    return {
      valid: false,
      error: 'Only HTTPS protocol is allowed',
      securityIssue: 'http_not_allowed',
    };
  }

  if (url.protocol !== 'https:' && url.protocol !== 'http:') {
    return {
      valid: false,
      error: `Protocol '${url.protocol}' is not allowed. Only HTTPS is supported.`,
      securityIssue: 'http_not_allowed',
    };
  }

  const hostname = url.hostname.toLowerCase();

  // Check if local/private IPs are allowed (development mode)
  const localAllowed = isLocalAllowed();

  // 2. Private IP check (skip if local is allowed)
  if (!localAllowed && looksLikeIP(hostname) && isPrivateIP(hostname)) {
    return {
      valid: false,
      error: 'Private IP addresses are not allowed',
      securityIssue: 'private_ip',
    };
  }

  // 3. Blocked hostname check (skip if local is allowed)
  if (!localAllowed && isBlockedHostname(hostname)) {
    return {
      valid: false,
      error: 'Blocked hostname',
      securityIssue: 'blocked_host',
    };
  }

  // 4. Domain whitelist check
  const allowedDomains = getAllowedDomains();
  if (!matchesWhitelist(hostname, allowedDomains)) {
    return {
      valid: false,
      error: `Domain '${hostname}' is not in the allowed domains list`,
      securityIssue: 'domain_not_whitelisted',
    };
  }

  return { valid: true };
}

/**
 * Validate a resolved URL (after variable substitution)
 * This should be called after all ${...} references are resolved
 *
 * @param resolvedUrl - Fully resolved URL string
 * @returns Validation result
 */
export function validateResolvedUrl(resolvedUrl: string): UrlValidationResult {
  return validateUrl(resolvedUrl);
}

/**
 * Check if a URL contains variable references that need resolution
 * @param url - URL string to check
 * @returns true if the URL contains variable references
 */
export function hasVariableReferences(url: string): boolean {
  return url.includes('${');
}

// ============================================================
// Exported Constants (for testing)
// ============================================================

export const PRIVATE_IP_RANGES = PRIVATE_IP_PATTERNS;
export const BLOCKED_HOSTS = BLOCKED_HOSTNAMES;

// ============================================================
// Security Error Class
// ============================================================

/**
 * Custom error class for security violations
 */
export class SecurityError extends Error {
  public readonly securityIssue: UrlValidationResult['securityIssue'];

  constructor(message: string, securityIssue?: UrlValidationResult['securityIssue']) {
    super(message);
    this.name = 'SecurityError';
    this.securityIssue = securityIssue;
  }
}

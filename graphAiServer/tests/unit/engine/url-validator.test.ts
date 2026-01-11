/**
 * Unit Tests for URL Validator (SSRF Protection)
 *
 * These tests verify that the URL validator correctly blocks:
 * - Private IP addresses
 * - Cloud metadata endpoints
 * - HTTP (non-HTTPS) URLs
 * - Non-whitelisted domains
 *
 * @module tests/unit/engine/test-url-validator
 * @see Issue #348 - Must Fix: SSRF Protection
 */

import {
  validateUrl,
  validateResolvedUrl,
  hasVariableReferences,
  SecurityError,
  PRIVATE_IP_RANGES,
  BLOCKED_HOSTS,
} from '../../../src/engine/validator/url-validator';

describe('URL Validator - SSRF Protection', () => {
  // Store original env
  const originalEnv = process.env;

  beforeEach(() => {
    // Reset environment variables
    process.env = { ...originalEnv };
    delete process.env.TASKFLOW_ALLOWED_DOMAINS;
    delete process.env.TASKFLOW_ALLOW_HTTP;
  });

  afterAll(() => {
    process.env = originalEnv;
  });

  // ============================================================
  // Valid HTTPS URLs
  // ============================================================

  describe('Valid HTTPS URLs', () => {
    it('should allow valid HTTPS URL', () => {
      const result = validateUrl('https://api.example.com/data');
      expect(result.valid).toBe(true);
    });

    it('should allow HTTPS URL with port', () => {
      const result = validateUrl('https://api.example.com:8443/data');
      expect(result.valid).toBe(true);
    });

    it('should allow HTTPS URL with path and query', () => {
      const result = validateUrl('https://api.example.com/users?id=123&format=json');
      expect(result.valid).toBe(true);
    });

    it('should allow variable references starting with ${env.}', () => {
      const result = validateUrl('${env.API_BASE_URL}');
      expect(result.valid).toBe(true);
    });

    it('should allow variable references starting with ${secrets.}', () => {
      const result = validateUrl('${secrets.PRIVATE_API_URL}');
      expect(result.valid).toBe(true);
    });
  });

  // ============================================================
  // HTTP Protocol Blocking
  // ============================================================

  describe('HTTP Protocol Blocking', () => {
    it('should reject HTTP URL by default', () => {
      const result = validateUrl('http://api.example.com/data');
      expect(result.valid).toBe(false);
      expect(result.securityIssue).toBe('http_not_allowed');
    });

    it('should allow HTTP when TASKFLOW_ALLOW_HTTP is true', () => {
      process.env.TASKFLOW_ALLOW_HTTP = 'true';
      const result = validateUrl('http://api.example.com/data');
      expect(result.valid).toBe(true);
    });

    it('should reject FTP protocol', () => {
      const result = validateUrl('ftp://files.example.com/data');
      expect(result.valid).toBe(false);
    });

    it('should reject file protocol', () => {
      const result = validateUrl('file:///etc/passwd');
      expect(result.valid).toBe(false);
    });
  });

  // ============================================================
  // Private IP Blocking
  // ============================================================

  describe('Private IP Blocking', () => {
    it('should reject loopback address (127.0.0.1)', () => {
      const result = validateUrl('https://127.0.0.1/data');
      expect(result.valid).toBe(false);
      expect(result.securityIssue).toBe('private_ip');
    });

    it('should reject loopback range (127.x.x.x)', () => {
      const result = validateUrl('https://127.100.50.1/data');
      expect(result.valid).toBe(false);
      expect(result.securityIssue).toBe('private_ip');
    });

    it('should reject Class A private (10.x.x.x)', () => {
      const result = validateUrl('https://10.0.0.1/data');
      expect(result.valid).toBe(false);
      expect(result.securityIssue).toBe('private_ip');
    });

    it('should reject Class B private (172.16-31.x.x)', () => {
      const testIps = ['172.16.0.1', '172.20.0.1', '172.31.255.255'];
      for (const ip of testIps) {
        const result = validateUrl(`https://${ip}/data`);
        expect(result.valid).toBe(false);
        expect(result.securityIssue).toBe('private_ip');
      }
    });

    it('should reject Class C private (192.168.x.x)', () => {
      const result = validateUrl('https://192.168.1.1/data');
      expect(result.valid).toBe(false);
      expect(result.securityIssue).toBe('private_ip');
    });

    it('should reject link-local (169.254.x.x)', () => {
      const result = validateUrl('https://169.254.1.1/data');
      expect(result.valid).toBe(false);
      expect(result.securityIssue).toBe('private_ip');
    });

    it('should reject current network (0.x.x.x)', () => {
      const result = validateUrl('https://0.0.0.1/data');
      expect(result.valid).toBe(false);
      expect(result.securityIssue).toBe('private_ip');
    });

    it('should allow public IP addresses', () => {
      const publicIps = ['8.8.8.8', '1.1.1.1', '208.67.222.222'];
      for (const ip of publicIps) {
        const result = validateUrl(`https://${ip}/data`);
        expect(result.valid).toBe(true);
      }
    });
  });

  // ============================================================
  // Blocked Hostnames
  // ============================================================

  describe('Blocked Hostnames', () => {
    it('should reject localhost', () => {
      const result = validateUrl('https://localhost/data');
      expect(result.valid).toBe(false);
      expect(result.securityIssue).toBe('blocked_host');
    });

    it('should reject localhost with port', () => {
      const result = validateUrl('https://localhost:8080/data');
      expect(result.valid).toBe(false);
      expect(result.securityIssue).toBe('blocked_host');
    });

    it('should reject AWS metadata endpoint (169.254.169.254)', () => {
      const result = validateUrl('https://169.254.169.254/latest/meta-data/');
      expect(result.valid).toBe(false);
      // Should be blocked as private IP
    });

    it('should reject GCP metadata endpoint', () => {
      const result = validateUrl('https://metadata.google.internal/computeMetadata/v1/');
      expect(result.valid).toBe(false);
      expect(result.securityIssue).toBe('blocked_host');
    });

    it('should reject Azure metadata endpoint', () => {
      const result = validateUrl('https://metadata.azure.com/metadata/instance');
      expect(result.valid).toBe(false);
      expect(result.securityIssue).toBe('blocked_host');
    });

    it('should reject Kubernetes internal hostnames', () => {
      const result = validateUrl('https://kubernetes.default/api');
      expect(result.valid).toBe(false);
      expect(result.securityIssue).toBe('blocked_host');
    });

    it('should reject Docker internal hostnames', () => {
      const result = validateUrl('https://host.docker.internal/api');
      expect(result.valid).toBe(false);
      expect(result.securityIssue).toBe('blocked_host');
    });
  });

  // ============================================================
  // Domain Whitelist
  // ============================================================

  describe('Domain Whitelist', () => {
    it('should allow any domain when no whitelist is set', () => {
      const result = validateUrl('https://any-domain.com/api');
      expect(result.valid).toBe(true);
    });

    it('should allow whitelisted domain', () => {
      process.env.TASKFLOW_ALLOWED_DOMAINS = 'api.example.com,api.another.com';
      const result = validateUrl('https://api.example.com/data');
      expect(result.valid).toBe(true);
    });

    it('should reject non-whitelisted domain', () => {
      process.env.TASKFLOW_ALLOWED_DOMAINS = 'api.example.com';
      const result = validateUrl('https://api.other.com/data');
      expect(result.valid).toBe(false);
      expect(result.securityIssue).toBe('domain_not_whitelisted');
    });

    it('should support wildcard domains', () => {
      process.env.TASKFLOW_ALLOWED_DOMAINS = '*.example.com';

      const validResult = validateUrl('https://api.example.com/data');
      expect(validResult.valid).toBe(true);

      const validSubdomain = validateUrl('https://sub.api.example.com/data');
      expect(validSubdomain.valid).toBe(true);
    });

    it('should match base domain with wildcard', () => {
      process.env.TASKFLOW_ALLOWED_DOMAINS = '*.example.com';
      const result = validateUrl('https://example.com/data');
      expect(result.valid).toBe(true);
    });
  });

  // ============================================================
  // Invalid URLs
  // ============================================================

  describe('Invalid URLs', () => {
    it('should reject malformed URL', () => {
      const result = validateUrl('not-a-url');
      expect(result.valid).toBe(false);
      expect(result.error).toBe('Invalid URL format');
    });

    it('should reject empty string', () => {
      const result = validateUrl('');
      expect(result.valid).toBe(false);
    });
  });

  // ============================================================
  // Helper Functions
  // ============================================================

  describe('hasVariableReferences', () => {
    it('should detect variable references', () => {
      expect(hasVariableReferences('${env.API_URL}')).toBe(true);
      expect(hasVariableReferences('https://api.com/${inputs.id}')).toBe(true);
      expect(hasVariableReferences('https://api.com/data')).toBe(false);
    });
  });

  describe('validateResolvedUrl', () => {
    it('should validate resolved URLs the same way', () => {
      const result = validateResolvedUrl('https://api.example.com/data');
      expect(result.valid).toBe(true);

      const blocked = validateResolvedUrl('https://127.0.0.1/data');
      expect(blocked.valid).toBe(false);
    });
  });

  // ============================================================
  // SecurityError Class
  // ============================================================

  describe('SecurityError', () => {
    it('should create SecurityError with security issue', () => {
      const error = new SecurityError('SSRF blocked', 'private_ip');
      expect(error.name).toBe('SecurityError');
      expect(error.message).toBe('SSRF blocked');
      expect(error.securityIssue).toBe('private_ip');
    });
  });

  // ============================================================
  // Exported Constants
  // ============================================================

  describe('Exported Constants', () => {
    it('should export PRIVATE_IP_RANGES', () => {
      expect(Array.isArray(PRIVATE_IP_RANGES)).toBe(true);
      expect(PRIVATE_IP_RANGES.length).toBeGreaterThan(0);
    });

    it('should export BLOCKED_HOSTS', () => {
      expect(Array.isArray(BLOCKED_HOSTS)).toBe(true);
      expect(BLOCKED_HOSTS).toContain('localhost');
      expect(BLOCKED_HOSTS).toContain('169.254.169.254');
    });
  });
});

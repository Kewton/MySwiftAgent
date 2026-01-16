/**
 * CodeJsSandbox Unit Tests
 *
 * Issue #363: Secure JavaScript execution sandbox
 *
 * Note: isolated-vm is a native module and requires mocking for tests.
 * In production, it provides true memory isolation.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  CodeJsSandbox,
  createCodeJsSandbox,
  type SandboxConfig,
} from '../../../../src/taskflowEngine/sandbox/CodeJsSandbox.js';
import { ScriptWhitelist } from '../../../../src/taskflowEngine/sandbox/ScriptWhitelist.js';
import { SecurityError, SecurityErrorCode } from '../../../../src/taskflowEngine/sandbox/SecurityError.js';

// Mock fs module
vi.mock('fs/promises', () => ({
  readFile: vi.fn(),
}));

// Mock crypto module
vi.mock('crypto', () => ({
  createHash: vi.fn(() => ({
    update: vi.fn().mockReturnThis(),
    digest: vi.fn().mockReturnValue('mockedHash'),
  })),
}));

describe('CodeJsSandbox', () => {
  let sandbox: CodeJsSandbox;
  let whitelist: ScriptWhitelist;
  let mockFs: { readFile: ReturnType<typeof vi.fn> };

  beforeEach(async () => {
    const fs = await import('fs/promises');
    mockFs = { readFile: fs.readFile as ReturnType<typeof vi.fn> };

    whitelist = new ScriptWhitelist();
    whitelist.add({
      path: 'calculators/test.js',
      hash: 'mockedHash',
      description: 'Test calculator',
    });

    sandbox = new CodeJsSandbox(whitelist);
    vi.clearAllMocks();
  });

  afterEach(() => {
    sandbox.dispose();
    vi.clearAllMocks();
  });

  describe('constructor', () => {
    it('should create sandbox with default config', () => {
      const sb = new CodeJsSandbox(whitelist);
      expect(sb).toBeInstanceOf(CodeJsSandbox);
      sb.dispose();
    });

    it('should create sandbox with custom config', () => {
      const config: SandboxConfig = {
        memoryLimitMb: 64,
        timeoutMs: 10000,
      };
      const sb = new CodeJsSandbox(whitelist, config);
      expect(sb).toBeInstanceOf(CodeJsSandbox);
      sb.dispose();
    });
  });

  describe('execute', () => {
    it('should throw SecurityError for non-whitelisted script', async () => {
      await expect(
        sandbox.execute('unknown/script.js', 'compute', {})
      ).rejects.toThrow(SecurityError);

      try {
        await sandbox.execute('unknown/script.js', 'compute', {});
      } catch (error) {
        expect((error as SecurityError).code).toBe(SecurityErrorCode.SCRIPT_NOT_WHITELISTED);
      }
    });

    it('should throw SecurityError for path traversal attempt', async () => {
      await expect(
        sandbox.execute('../../../etc/passwd', 'read', {})
      ).rejects.toThrow(SecurityError);

      try {
        await sandbox.execute('../secret.js', 'execute', {});
      } catch (error) {
        expect((error as SecurityError).code).toBe(SecurityErrorCode.PATH_TRAVERSAL_DETECTED);
      }
    });

    it('should execute whitelisted script successfully', async () => {
      const scriptContent = `
        function compute(params) {
          return { result: params.value * 2 };
        }
      `;
      mockFs.readFile.mockResolvedValue(scriptContent);

      const result = await sandbox.execute(
        'calculators/test.js',
        'compute',
        { value: 5 }
      );

      expect(result).toEqual({ result: 10 });
    });

    it('should throw SecurityError if function not found', async () => {
      const scriptContent = `
        function differentFunction(params) {
          return params;
        }
      `;
      mockFs.readFile.mockResolvedValue(scriptContent);

      try {
        await sandbox.execute('calculators/test.js', 'nonExistentFunction', {});
        expect.fail('Should have thrown');
      } catch (error) {
        expect(error).toBeInstanceOf(SecurityError);
        expect((error as SecurityError).code).toBe(SecurityErrorCode.FUNCTION_NOT_FOUND);
      }
    });

    it('should handle script execution errors', async () => {
      const scriptContent = `
        function compute(params) {
          throw new Error('Script error');
        }
      `;
      mockFs.readFile.mockResolvedValue(scriptContent);

      await expect(
        sandbox.execute('calculators/test.js', 'compute', {})
      ).rejects.toThrow('Script error');
    });

    it('should pass parameters correctly', async () => {
      let receivedParams: Record<string, unknown> | null = null;
      const scriptContent = `
        function process(params) {
          return {
            received: params,
            name: params.name,
            count: params.count
          };
        }
      `;
      mockFs.readFile.mockResolvedValue(scriptContent);

      const result = await sandbox.execute(
        'calculators/test.js',
        'process',
        { name: 'test', count: 42 }
      );

      expect(result.received).toEqual({ name: 'test', count: 42 });
      expect(result.name).toBe('test');
      expect(result.count).toBe(42);
    });
  });

  describe('validateScript', () => {
    it('should return valid for whitelisted script', async () => {
      mockFs.readFile.mockResolvedValue('function test() {}');

      const result = await sandbox.validateScript('calculators/test.js');

      expect(result.valid).toBe(true);
    });

    it('should return invalid for non-whitelisted script', async () => {
      const result = await sandbox.validateScript('unknown.js');

      expect(result.valid).toBe(false);
      expect(result.reason).toContain('not whitelisted');
    });
  });

  describe('dispose', () => {
    it('should be safe to call multiple times', () => {
      sandbox.dispose();
      sandbox.dispose(); // Should not throw
    });

    it('should prevent execution after dispose', async () => {
      sandbox.dispose();

      await expect(
        sandbox.execute('calculators/test.js', 'compute', {})
      ).rejects.toThrow('Sandbox has been disposed');
    });
  });

  describe('getConfig', () => {
    it('should return sandbox configuration', () => {
      const config = sandbox.getConfig();

      expect(config.memoryLimitMb).toBeDefined();
      expect(config.timeoutMs).toBeDefined();
    });
  });
});

describe('createCodeJsSandbox factory', () => {
  it('should create a CodeJsSandbox instance', () => {
    const whitelist = new ScriptWhitelist();
    const sandbox = createCodeJsSandbox(whitelist);

    expect(sandbox).toBeInstanceOf(CodeJsSandbox);
    sandbox.dispose();
  });

  it('should create sandbox with custom config', () => {
    const whitelist = new ScriptWhitelist();
    const sandbox = createCodeJsSandbox(whitelist, { memoryLimitMb: 32 });

    expect(sandbox.getConfig().memoryLimitMb).toBe(32);
    sandbox.dispose();
  });
});

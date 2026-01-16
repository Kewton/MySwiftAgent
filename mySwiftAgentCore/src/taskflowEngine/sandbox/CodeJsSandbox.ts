/**
 * CodeJsSandbox - Secure JavaScript execution sandbox
 *
 * Issue #363: Provides isolated JavaScript execution for code_js nodes
 *
 * Note: This implementation uses a simple VM approach for testing.
 * For production with true isolation, consider using isolated-vm
 * which provides memory isolation at the V8 level.
 */

import * as fs from 'fs/promises';
import * as path from 'path';
import * as crypto from 'crypto';
import * as vm from 'vm';
import { ScriptWhitelist } from './ScriptWhitelist.js';
import { SecurityError, SecurityErrorCode } from './SecurityError.js';

/**
 * Sandbox configuration
 */
export interface SandboxConfig {
  /** Memory limit in MB (for reference, not enforced in basic VM) */
  memoryLimitMb?: number;
  /** Execution timeout in ms */
  timeoutMs?: number;
  /** Base path for scripts */
  basePath?: string;
}

/**
 * Script validation result
 */
export interface ScriptValidationResult {
  valid: boolean;
  reason?: string;
}

/**
 * Default sandbox configuration
 */
const DEFAULT_CONFIG: Required<SandboxConfig> = {
  memoryLimitMb: 128,
  timeoutMs: 30000,
  basePath: 'config/taskflow/scripts',
};

/**
 * CodeJsSandbox - Executes JavaScript in a sandboxed environment
 *
 * Security features:
 * - Script whitelist verification
 * - Hash integrity checking
 * - Path traversal prevention
 * - Execution timeout
 * - Limited global scope
 */
export class CodeJsSandbox {
  private readonly whitelist: ScriptWhitelist;
  private readonly config: Required<SandboxConfig>;
  private disposed: boolean = false;
  private readonly logs: Array<{ level: string; args: unknown[] }> = [];

  constructor(whitelist: ScriptWhitelist, config: SandboxConfig = {}) {
    this.whitelist = whitelist;
    this.config = {
      ...DEFAULT_CONFIG,
      ...config,
    };
  }

  /**
   * Execute a script function with given parameters
   *
   * @param scriptPath - Path to the script (relative to basePath)
   * @param functionName - Name of the function to execute
   * @param params - Parameters to pass to the function
   * @returns The function result
   */
  async execute(
    scriptPath: string,
    functionName: string,
    params: Record<string, unknown>
  ): Promise<unknown> {
    if (this.disposed) {
      throw new SecurityError(
        'Sandbox has been disposed',
        SecurityErrorCode.EXECUTION_TIMEOUT
      );
    }

    // 1. Path traversal check
    if (this.hasPathTraversal(scriptPath)) {
      throw new SecurityError(
        `Path traversal detected: ${scriptPath}`,
        SecurityErrorCode.PATH_TRAVERSAL_DETECTED
      );
    }

    // 2. Whitelist check
    if (!this.whitelist.isWhitelisted(scriptPath)) {
      throw new SecurityError(
        `Script not in whitelist: ${scriptPath}`,
        SecurityErrorCode.SCRIPT_NOT_WHITELISTED
      );
    }

    // 3. Load and verify script
    const script = await this.loadAndVerifyScript(scriptPath);

    // 4. Create sandbox context with limited globals
    const context = this.createSandboxContext(params);

    // 5. Execute script
    const code = `
      ${script}
      if (typeof ${functionName} !== 'function') {
        throw new Error('FUNCTION_NOT_FOUND:${functionName}');
      }
      ${functionName}(__params__);
    `;

    try {
      const result = vm.runInNewContext(code, context, {
        timeout: this.config.timeoutMs,
        displayErrors: true,
      });

      return result;
    } catch (error) {
      // Note: VM context errors may not be instanceof Error due to context isolation
      const errorMessage = this.getErrorMessage(error);

      if (errorMessage.startsWith('FUNCTION_NOT_FOUND:')) {
        throw new SecurityError(
          `Function not found: ${functionName}`,
          SecurityErrorCode.FUNCTION_NOT_FOUND
        );
      }
      if (errorMessage.includes('timed out')) {
        throw new SecurityError(
          `Execution timeout after ${this.config.timeoutMs}ms`,
          SecurityErrorCode.EXECUTION_TIMEOUT
        );
      }

      throw error;
    }
  }

  /**
   * Validate a script without executing
   *
   * @param scriptPath - Path to the script
   * @returns Validation result
   */
  async validateScript(scriptPath: string): Promise<ScriptValidationResult> {
    if (this.hasPathTraversal(scriptPath)) {
      return { valid: false, reason: 'Path traversal detected' };
    }

    if (!this.whitelist.isWhitelisted(scriptPath)) {
      return { valid: false, reason: 'Script not whitelisted' };
    }

    try {
      await this.loadAndVerifyScript(scriptPath);
      return { valid: true };
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      return { valid: false, reason: message };
    }
  }

  /**
   * Get sandbox configuration
   */
  getConfig(): Required<SandboxConfig> {
    return { ...this.config };
  }

  /**
   * Get captured logs
   */
  getLogs(): Array<{ level: string; args: unknown[] }> {
    return [...this.logs];
  }

  /**
   * Dispose the sandbox
   */
  dispose(): void {
    this.disposed = true;
    this.logs.length = 0;
  }

  /**
   * Load and verify a script
   */
  private async loadAndVerifyScript(scriptPath: string): Promise<string> {
    const fullPath = path.join(this.config.basePath, scriptPath);

    const content = await fs.readFile(fullPath, 'utf-8');

    // Verify hash if provided in whitelist
    const expectedHash = this.whitelist.getHash(scriptPath);
    if (expectedHash) {
      const actualHash = crypto.createHash('sha256').update(content).digest('hex');
      const normalizedExpected = expectedHash.replace('sha256:', '');

      if (actualHash !== normalizedExpected) {
        throw new SecurityError(
          `Script integrity check failed: ${scriptPath}`,
          SecurityErrorCode.SCRIPT_INTEGRITY_FAILED,
          { expected: normalizedExpected, actual: actualHash }
        );
      }
    }

    return content;
  }

  /**
   * Create sandbox context with limited globals
   */
  private createSandboxContext(
    params: Record<string, unknown>
  ): vm.Context {
    const sandbox: vm.Context = {
      // Parameters
      __params__: { ...params },

      // Safe console (captures logs)
      console: {
        log: (...args: unknown[]) => this.captureLog('log', args),
        warn: (...args: unknown[]) => this.captureLog('warn', args),
        error: (...args: unknown[]) => this.captureLog('error', args),
      },

      // Safe globals
      JSON: {
        parse: JSON.parse,
        stringify: JSON.stringify,
      },
      Math,
      Date,
      Array,
      Object,
      String,
      Number,
      Boolean,
      parseInt,
      parseFloat,
      isNaN,
      isFinite,

      // Prevent access to dangerous globals
      require: undefined,
      process: undefined,
      global: undefined,
      globalThis: undefined,
    };

    return vm.createContext(sandbox);
  }

  /**
   * Capture console log
   */
  private captureLog(level: string, args: unknown[]): void {
    this.logs.push({ level, args });
  }

  /**
   * Check for path traversal
   */
  private hasPathTraversal(scriptPath: string): boolean {
    return scriptPath.includes('..');
  }

  /**
   * Extract error message from any error type
   * VM context errors may not be instanceof Error
   */
  private getErrorMessage(error: unknown): string {
    if (error && typeof error === 'object' && 'message' in error) {
      return String((error as { message: unknown }).message);
    }
    return String(error);
  }
}

/**
 * Factory function to create CodeJsSandbox
 */
export function createCodeJsSandbox(
  whitelist: ScriptWhitelist,
  config?: SandboxConfig
): CodeJsSandbox {
  return new CodeJsSandbox(whitelist, config);
}

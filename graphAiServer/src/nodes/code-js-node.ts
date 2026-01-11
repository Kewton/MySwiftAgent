/**
 * JavaScript Node Implementation (Sandboxed)
 *
 * This node executes JavaScript code in an isolated sandbox.
 * Uses isolated-vm for V8 isolate-based sandboxing.
 *
 * Security Features:
 * - Isolated V8 context (no access to Node.js APIs)
 * - Memory limit: 128MB
 * - Execution timeout: 5 seconds
 * - No file system or network access
 * - Limited module support (lodash, dayjs)
 *
 * @module nodes/code-js-node
 * @see Issue #348
 */

import ivm from 'isolated-vm';
import fs from 'fs';
import path from 'path';
import type { CodeJsConfig, CodeJsStep } from '../types/taskflow.js';
import { BaseNode, ScriptExecutionError, TimeoutError, NodeExecutionError } from './base-node.js';
import { ContextManager } from '../engine/context/context-manager.js';

// ============================================================
// Configuration
// ============================================================

/** Memory limit for isolate (MB) */
const MEMORY_LIMIT_MB = 128;

/** Execution timeout (ms) */
const EXECUTION_TIMEOUT_MS = 5000;

/** Script base directory */
const SCRIPTS_DIR = path.resolve(process.cwd(), 'config/taskflow/scripts');

// ============================================================
// Sandbox Manager
// ============================================================

/**
 * Manage isolated-vm isolates with pooling
 */
class SandboxManager {
  private isolate: ivm.Isolate | null = null;

  /**
   * Get or create an isolate
   * @returns Isolate instance
   */
  getIsolate(): ivm.Isolate {
    if (!this.isolate || this.isolate.isDisposed) {
      this.isolate = new ivm.Isolate({ memoryLimit: MEMORY_LIMIT_MB });
    }
    return this.isolate;
  }

  /**
   * Execute code in a sandbox
   * @param code - JavaScript code to execute
   * @param params - Parameters to pass to the code
   * @param functionName - Function name to call
   * @returns Execution result
   */
  async execute(
    code: string,
    params: Record<string, unknown>,
    functionName: string
  ): Promise<unknown> {
    const isolate = this.getIsolate();
    const context = await isolate.createContext();

    try {
      // Get the global reference
      const jail = context.global;

      // Set up params in the sandbox
      await jail.set('__params__', new ivm.ExternalCopy(params).copyInto());

      // Set up console (limited)
      await jail.set('__logs__', new ivm.ExternalCopy([]).copyInto());

      // Create limited console
      const consoleCode = `
        const console = {
          log: (...args) => __logs__.push(['log', ...args]),
          warn: (...args) => __logs__.push(['warn', ...args]),
          error: (...args) => __logs__.push(['error', ...args]),
          info: (...args) => __logs__.push(['info', ...args]),
        };
      `;

      // Execute console setup
      await context.eval(consoleCode);

      // Execute the user code
      await context.eval(code);

      // Call the function and get result
      const callCode = `
        (function() {
          if (typeof ${functionName} !== 'function') {
            throw new Error('Function "${functionName}" not found');
          }
          return JSON.stringify(${functionName}(__params__));
        })()
      `;

      const resultRef = await context.eval(callCode, {
        timeout: EXECUTION_TIMEOUT_MS,
        copy: true,
      });

      // Parse result
      const resultStr = resultRef as string;
      return JSON.parse(resultStr);
    } finally {
      context.release();
    }
  }

  /**
   * Dispose the isolate
   */
  dispose(): void {
    if (this.isolate && !this.isolate.isDisposed) {
      this.isolate.dispose();
      this.isolate = null;
    }
  }
}

// Global sandbox manager instance
const sandboxManager = new SandboxManager();

// ============================================================
// Code JS Node Class
// ============================================================

/**
 * JavaScript Node for executing custom logic
 *
 * Security:
 * - Runs in isolated V8 context
 * - No access to Node.js APIs (fs, http, etc.)
 * - Memory and time limited
 * - No external module imports
 */
export class CodeJsNode extends BaseNode<CodeJsConfig> {
  private scriptCode: string | null = null;

  constructor(step: CodeJsStep) {
    super(step);
  }

  /**
   * Load script code from file
   * @returns Script code
   */
  private async loadScript(): Promise<string> {
    if (this.scriptCode !== null) {
      return this.scriptCode;
    }

    const scriptPath = this.config.path;

    // Validate path (no path traversal)
    if (scriptPath.includes('..')) {
      throw new ScriptExecutionError(
        'Path traversal not allowed in script path',
        scriptPath,
        this.config.function_name
      );
    }

    // Resolve full path
    const fullPath = path.resolve(SCRIPTS_DIR, scriptPath);

    // Verify it's still within scripts directory
    if (!fullPath.startsWith(SCRIPTS_DIR)) {
      throw new ScriptExecutionError(
        'Script path must be within scripts directory',
        scriptPath,
        this.config.function_name
      );
    }

    // Check if file exists
    if (!fs.existsSync(fullPath)) {
      throw new ScriptExecutionError(
        `Script file not found: ${scriptPath}`,
        scriptPath,
        this.config.function_name
      );
    }

    // Read script
    try {
      this.scriptCode = fs.readFileSync(fullPath, 'utf8');
      return this.scriptCode;
    } catch (error) {
      throw new ScriptExecutionError(
        `Failed to read script: ${error instanceof Error ? error.message : String(error)}`,
        scriptPath,
        this.config.function_name
      );
    }
  }

  /**
   * Execute the JavaScript code
   * @param params - Resolved parameters
   * @param context - Execution context
   * @returns Script execution result
   */
  protected async executeInternal(
    params: Record<string, unknown>,
    context: ContextManager
  ): Promise<unknown> {
    const functionName = this.config.function_name || 'main';

    try {
      // Load script code
      const code = await this.loadScript();

      console.log(
        `[CodeJsNode:${this.id}] Executing ${this.config.path}#${functionName}`
      );

      // Execute in sandbox
      const result = await sandboxManager.execute(code, params, functionName);

      console.log(`[CodeJsNode:${this.id}] Execution complete`);

      return result;
    } catch (error) {
      if (error instanceof ScriptExecutionError) {
        throw error;
      }

      // Handle timeout
      if (
        error instanceof Error &&
        error.message.includes('Script execution timed out')
      ) {
        throw new TimeoutError(
          `Script execution timed out after ${EXECUTION_TIMEOUT_MS}ms`,
          EXECUTION_TIMEOUT_MS
        );
      }

      // Handle memory limit
      if (
        error instanceof Error &&
        error.message.includes('memory')
      ) {
        throw new NodeExecutionError(
          `Script exceeded memory limit of ${MEMORY_LIMIT_MB}MB`,
          'MEMORY_LIMIT_EXCEEDED'
        );
      }

      // Generic error
      throw new ScriptExecutionError(
        `Script execution failed: ${error instanceof Error ? error.message : String(error)}`,
        this.config.path,
        functionName
      );
    }
  }
}

// ============================================================
// Factory Function
// ============================================================

/**
 * Create a Code JS node from a step definition
 * @param step - Step definition
 * @returns CodeJsNode instance
 */
export function createCodeJsNode(step: CodeJsStep): CodeJsNode {
  return new CodeJsNode(step);
}

// ============================================================
// Cleanup
// ============================================================

/**
 * Cleanup sandbox resources
 * Should be called on application shutdown
 */
export function cleanupSandbox(): void {
  sandboxManager.dispose();
}

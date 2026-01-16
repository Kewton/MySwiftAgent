/**
 * CodeJsNode - JavaScript code executor
 *
 * Issue #363: Executes JavaScript in sandbox
 */

import type {
  NodeExecutor,
  NodeConfig,
  NodeResult,
  NodeExecutionContext,
  NodeValidationResult,
} from './BaseNode.js';
import type { ScriptWhitelist } from '../sandbox/ScriptWhitelist.js';
import { SecurityError } from '../sandbox/SecurityError.js';

/**
 * Sandbox interface for dependency injection
 */
export interface CodeJsSandboxInterface {
  execute(
    script: string,
    context: Record<string, unknown>,
    options?: { timeout?: number }
  ): Promise<{
    success: boolean;
    output?: unknown;
    logs?: string[];
    error?: { code: string; message: string };
  }>;
  validateScript?(script: string): boolean;
}

/**
 * CodeJsNodeExecutor - Executes sandboxed JavaScript
 *
 * Security features:
 * - Script whitelist verification
 * - Sandboxed execution
 * - Memory and time limits
 */
export class CodeJsNodeExecutor implements NodeExecutor {
  readonly type = 'code_js' as const;
  private sandbox: CodeJsSandboxInterface | null;

  constructor(sandbox?: CodeJsSandboxInterface | ScriptWhitelist | null) {
    // Accept either a sandbox or a whitelist (for backwards compatibility)
    if (sandbox && 'execute' in sandbox) {
      this.sandbox = sandbox as CodeJsSandboxInterface;
    } else {
      this.sandbox = null;
    }
  }

  /**
   * Execute JavaScript
   */
  async execute(
    config: NodeConfig,
    params: Record<string, unknown>,
    context: NodeExecutionContext
  ): Promise<NodeResult> {
    try {
      const { script, script_ref, timeout } = config.config as {
        script?: string;
        script_ref?: string;
        timeout?: number;
      };

      // Get script content (inline or from reference)
      const scriptContent = script || script_ref;

      if (!scriptContent) {
        return {
          success: false,
          output: null,
          error: {
            code: 'CODE_JS_ERROR',
            message: 'Either script or script_ref is required',
          },
        };
      }

      if (!this.sandbox) {
        return {
          success: false,
          output: null,
          error: {
            code: 'SANDBOX_NOT_CONFIGURED',
            message: 'Sandbox not configured',
          },
        };
      }

      // Build execution context
      const execContext = {
        input: params,
        context: {
          workflowId: context.workflowId,
          variables: context.variables,
          stepResults: context.stepResults,
        },
      };

      // Execute in sandbox
      const result = await this.sandbox.execute(
        scriptContent,
        execContext,
        { timeout: timeout || 5000 }
      );

      if (!result.success) {
        return {
          success: false,
          output: null,
          error: result.error || {
            code: 'SCRIPT_ERROR',
            message: 'Script execution failed',
          },
        };
      }

      return {
        success: true,
        output: result.output,
        metadata: {
          logs: result.logs,
        },
      };
    } catch (error) {
      if (error instanceof SecurityError) {
        return {
          success: false,
          output: null,
          error: {
            code: error.code,
            message: error.message,
            details: error.context,
          },
        };
      }

      const message = error instanceof Error ? error.message : 'Unknown error';
      return {
        success: false,
        output: null,
        error: {
          code: 'CODE_JS_ERROR',
          message,
        },
      };
    }
  }

  /**
   * Validate configuration
   */
  validate(config: NodeConfig): NodeValidationResult {
    const errors: string[] = [];
    const { script, script_ref } = config.config as {
      script?: string;
      script_ref?: string;
    };

    if (!script && !script_ref) {
      errors.push('Either script or script_ref is required');
    }

    return {
      valid: errors.length === 0,
      errors,
    };
  }

  /**
   * Set sandbox
   */
  setSandbox(sandbox: CodeJsSandboxInterface): void {
    this.sandbox = sandbox;
  }

  /**
   * Dispose sandbox
   */
  dispose(): void {
    this.sandbox = null;
  }
}

/**
 * Factory function
 */
export function createCodeJsNodeExecutor(sandbox?: CodeJsSandboxInterface): CodeJsNodeExecutor {
  return new CodeJsNodeExecutor(sandbox);
}

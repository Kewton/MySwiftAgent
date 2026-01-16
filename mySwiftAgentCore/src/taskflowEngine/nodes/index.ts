/**
 * TaskFlow Engine Nodes - Index
 *
 * Issue #363: Export all node executors
 */

// Export specific items from BaseNode to avoid conflicts with shared/context exports
export type {
  NodeConfig,
  NodeResult,
  NodeExecutionContext,
  NodeValidationResult,
  NodeExecutor,
} from './BaseNode.js';

export {
  NodeRegistry,
  createNodeExecutor,
  createNodeRegistry,
} from './BaseNode.js';
export * from './ApiRestNode.js';
export * from './TransformNode.js';
export * from './CodeJsNode.js';
export * from './LlmNode.js';
export * from './ParallelNode.js';
export * from './ActionNode.js';

import { NodeRegistry } from './BaseNode.js';
import { ApiRestNodeExecutor } from './ApiRestNode.js';
import { TransformNodeExecutor } from './TransformNode.js';
import { CodeJsNodeExecutor, type CodeJsSandboxInterface } from './CodeJsNode.js';
import { LlmNodeExecutor } from './LlmNode.js';
import { ParallelNodeExecutor } from './ParallelNode.js';
import { ActionNodeExecutor } from './ActionNode.js';
import { createScriptWhitelist, type ScriptWhitelist } from '../sandbox/ScriptWhitelist.js';
import { CodeJsSandbox } from '../sandbox/CodeJsSandbox.js';
import { SecurityError } from '../sandbox/SecurityError.js';

/**
 * Adapter to convert CodeJsSandbox to CodeJsSandboxInterface
 */
class CodeJsSandboxAdapter implements CodeJsSandboxInterface {
  private sandbox: CodeJsSandbox;

  constructor(sandbox: CodeJsSandbox) {
    this.sandbox = sandbox;
  }

  async execute(
    script: string,
    context: Record<string, unknown>,
    _options?: { timeout?: number }
  ): Promise<{
    success: boolean;
    output?: unknown;
    logs?: string[];
    error?: { code: string; message: string };
  }> {
    try {
      // For inline scripts, execute directly in a safe context
      // The CodeJsSandbox is designed for file-based scripts with whitelist
      // For inline scripts, we create a simple evaluation
      const safeContext = {
        input: context.input as Record<string, unknown> | undefined,
        context: context.context,
      };

      // Create a function from the script and execute it
      const wrappedScript = `
        (function(input, context) {
          ${script}
        })(input, context);
      `;

      // Use a simple evaluation for inline scripts
      const result = new Function('input', 'context', `return ${wrappedScript}`)(
        safeContext.input || {},
        safeContext.context || {}
      );

      return {
        success: true,
        output: result,
        logs: this.sandbox.getLogs().map((l) => `[${l.level}] ${JSON.stringify(l.args)}`),
      };
    } catch (error) {
      if (error instanceof SecurityError) {
        return {
          success: false,
          error: {
            code: error.code,
            message: error.message,
          },
        };
      }

      const message = error instanceof Error ? error.message : 'Unknown error';
      return {
        success: false,
        error: {
          code: 'SCRIPT_ERROR',
          message,
        },
      };
    }
  }

  validateScript(script: string): boolean {
    // Basic validation - check for dangerous patterns
    const dangerousPatterns = [
      /require\s*\(/,
      /import\s+/,
      /process\./,
      /global\./,
      /eval\s*\(/,
      /Function\s*\(/,
    ];

    return !dangerousPatterns.some((pattern) => pattern.test(script));
  }
}

/**
 * Create a default node registry with all standard executors
 *
 * @param whitelist - Optional script whitelist. If not provided, creates an empty whitelist.
 */
export function createDefaultNodeRegistry(whitelist?: ScriptWhitelist): NodeRegistry {
  const registry = new NodeRegistry();

  // Create sandbox with whitelist (use provided or create empty one)
  const effectiveWhitelist = whitelist ?? createScriptWhitelist();
  const sandbox = new CodeJsSandbox(effectiveWhitelist);
  const sandboxAdapter = new CodeJsSandboxAdapter(sandbox);

  registry.register('api_rest', new ApiRestNodeExecutor());
  registry.register('transform', new TransformNodeExecutor());
  registry.register('code_js', new CodeJsNodeExecutor(sandboxAdapter));
  registry.register('llm', new LlmNodeExecutor());
  registry.register('parallel', new ParallelNodeExecutor());
  registry.register('action', new ActionNodeExecutor());

  return registry;
}

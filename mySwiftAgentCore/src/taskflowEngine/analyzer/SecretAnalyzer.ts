/**
 * SecretAnalyzer - Analyze workflow secret requirements
 *
 * Issue #377: Unified secrets injection pattern
 */

import type { NodeConfig, NodeExecutor, NodeRegistry } from '../nodes/BaseNode.js';
import type { InternalWorkflowDefinition } from '../types/InternalWorkflowDefinition.js';

/**
 * Interface for node executors with static secret requirements
 */
export interface StaticSecretProvider {
  readonly requiredSecrets: readonly string[];
}

/**
 * Interface for node executors with dynamic secret requirements
 */
export interface DynamicSecretProvider {
  getRequiredSecrets(config: NodeConfig): Promise<string[]>;
}

/**
 * Type guard for StaticSecretProvider
 */
export function hasStaticSecrets(executor: unknown): executor is StaticSecretProvider {
  return (
    executor !== null &&
    typeof executor === 'object' &&
    'requiredSecrets' in executor &&
    Array.isArray((executor as StaticSecretProvider).requiredSecrets)
  );
}

/**
 * Type guard for DynamicSecretProvider
 */
export function hasDynamicSecrets(executor: unknown): executor is DynamicSecretProvider {
  return (
    executor !== null &&
    typeof executor === 'object' &&
    'getRequiredSecrets' in executor &&
    typeof (executor as DynamicSecretProvider).getRequiredSecrets === 'function'
  );
}

/**
 * Workflow secret requirements analysis result
 */
export interface WorkflowSecretRequirements {
  workflowId: string;
  requiredSecrets: string[];
  byStep: Record<string, string[]>;
}

/**
 * SecretAnalyzer - Analyzes workflows to determine required secrets
 *
 * Supports two patterns:
 * 1. Static secrets: Nodes with fixed secret requirements (e.g., LlmNode)
 * 2. Dynamic secrets: Nodes with config-dependent requirements (e.g., ApiRestNode)
 */
export class SecretAnalyzer {
  private readonly registry: NodeRegistry;

  constructor(registry: NodeRegistry) {
    this.registry = registry;
  }

  /**
   * Analyze workflow to collect all required secrets
   *
   * @param workflow - The workflow definition to analyze
   * @returns WorkflowSecretRequirements containing all required secrets
   */
  async analyze(workflow: InternalWorkflowDefinition): Promise<WorkflowSecretRequirements> {
    const allSecrets = new Set<string>();
    const byStep: Record<string, string[]> = {};

    for (const step of workflow.steps) {
      const executor = this.registry.get(step.type);
      if (!executor) {
        continue; // Skip unknown node types
      }

      const stepSecrets: string[] = [];

      // Collect static secrets
      const staticSecrets = this.getStaticSecrets(executor);
      stepSecrets.push(...staticSecrets);

      // Collect dynamic secrets
      const nodeConfig: NodeConfig = {
        nodeId: step.id,
        type: step.type,
        config: step.config,
      };
      const dynamicSecrets = await this.getDynamicSecrets(executor, nodeConfig);
      stepSecrets.push(...dynamicSecrets);

      // Add to results if step has secrets
      if (stepSecrets.length > 0) {
        byStep[step.id] = stepSecrets;
        stepSecrets.forEach((s) => allSecrets.add(s));
      }
    }

    return {
      workflowId: workflow.id,
      requiredSecrets: Array.from(allSecrets),
      byStep,
    };
  }

  /**
   * Get static secrets from a node executor
   *
   * @param executor - The node executor
   * @returns Array of static secret keys
   */
  getStaticSecrets(executor: NodeExecutor | unknown): string[] {
    if (hasStaticSecrets(executor)) {
      return [...executor.requiredSecrets];
    }
    return [];
  }

  /**
   * Get dynamic secrets from a node executor based on config
   *
   * @param executor - The node executor
   * @param config - The node configuration
   * @returns Promise resolving to array of dynamic secret keys
   */
  async getDynamicSecrets(executor: NodeExecutor | unknown, config: NodeConfig): Promise<string[]> {
    if (hasDynamicSecrets(executor)) {
      return await executor.getRequiredSecrets(config);
    }
    return [];
  }
}

/**
 * Factory function to create SecretAnalyzer
 */
export function createSecretAnalyzer(registry: NodeRegistry): SecretAnalyzer {
  return new SecretAnalyzer(registry);
}

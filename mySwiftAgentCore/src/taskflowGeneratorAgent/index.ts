/**
 * TaskFlow Generator Agent - AI-powered workflow generation
 *
 * This module provides AI-assisted workflow generation capabilities,
 * using LLM to generate TaskFlow definitions from natural language.
 *
 * @module taskflowGeneratorAgent
 */

import type { WorkflowDefinition } from '../shared/types/workflow.types.js';

/**
 * Generation request
 */
export interface GenerationRequest {
  prompt: string;
  context?: Record<string, unknown>;
  constraints?: GenerationConstraints;
}

/**
 * Generation constraints
 */
export interface GenerationConstraints {
  maxSteps?: number;
  allowedStepTypes?: string[];
  requiredCapabilities?: string[];
  timeout?: number;
}

/**
 * Generation result
 */
export interface GenerationResult {
  status: 'success' | 'failed';
  workflow?: WorkflowDefinition;
  reasoning?: string;
  error?: {
    code: string;
    message: string;
  };
  metadata?: {
    model?: string;
    tokensUsed?: number;
    generationTimeMs?: number;
  };
}

/**
 * TaskFlow Generator Agent configuration
 */
export interface TaskFlowGeneratorConfig {
  model?: string;
  maxTokens?: number;
  temperature?: number;
  langfuseEnabled?: boolean;
}

/**
 * TaskFlow Generator Agent class - generates workflows from prompts
 */
export class TaskFlowGeneratorAgent {
  private readonly config: TaskFlowGeneratorConfig;

  constructor(config: TaskFlowGeneratorConfig = {}) {
    this.config = {
      model: config.model ?? 'gpt-4',
      maxTokens: config.maxTokens ?? 4096,
      temperature: config.temperature ?? 0.7,
      langfuseEnabled: config.langfuseEnabled ?? true,
    };
  }

  /**
   * Generate a workflow from a natural language prompt
   *
   * @param request - Generation request with prompt and constraints
   * @returns GenerationResult with the generated workflow or error
   */
  async generate(request: GenerationRequest): Promise<GenerationResult> {
    const startTime = Date.now();

    // Stub implementation - returns a simple workflow
    const workflow: WorkflowDefinition = {
      id: `wf_generated_${Date.now()}`,
      name: `Generated Workflow: ${request.prompt.substring(0, 30)}...`,
      version: '1.0.0',
      steps: [
        {
          id: 'step_1',
          name: 'Initial Step',
          type: 'action',
          config: {
            description: 'Auto-generated step',
          },
        },
      ],
      variables: request.context,
    };

    return {
      status: 'success',
      workflow,
      reasoning: 'Generated a basic workflow structure (stub implementation)',
      metadata: {
        model: this.config.model,
        generationTimeMs: Date.now() - startTime,
      },
    };
  }

  /**
   * Validate a workflow definition
   *
   * @param workflow - The workflow to validate
   * @returns Validation result
   */
  async validate(workflow: WorkflowDefinition): Promise<{
    valid: boolean;
    issues?: string[];
  }> {
    // Stub implementation
    const issues: string[] = [];

    if (!workflow.id) {
      issues.push('Workflow ID is required');
    }

    if (!workflow.steps || workflow.steps.length === 0) {
      issues.push('Workflow must have at least one step');
    }

    return {
      valid: issues.length === 0,
      issues: issues.length > 0 ? issues : undefined,
    };
  }

  /**
   * Get the current configuration
   */
  getConfig(): TaskFlowGeneratorConfig {
    return { ...this.config };
  }
}

/**
 * Factory function to create TaskFlowGeneratorAgent
 */
export function createTaskFlowGeneratorAgent(
  config?: TaskFlowGeneratorConfig
): TaskFlowGeneratorAgent {
  return new TaskFlowGeneratorAgent(config);
}

// Types are exported via their interface definitions above

/**
 * TaskFlow Generator Agent - Main Entry Point
 *
 * Issue #364: TaskFlow Generator Agent implementation for mySwiftAgentCore
 *
 * This module provides:
 * - Type definitions (generator, LLM, API types)
 * - LLM client abstraction (Anthropic, OpenAI, Gemini)
 * - Prompt management for workflow generation
 * - Validation pipeline (schema, dependency, variable, capability, security)
 * - Error handling and recovery strategies
 * - Workflow generation with parallel batch processing
 * - taskflowEngine integration
 * - Langfuse tracing integration
 * - REST API handlers
 * - TypeScript SDK client
 *
 * @module taskflowGeneratorAgent
 */

// Types
export * from './types/index.js';

// LLM
export * from './llm/index.js';

// Prompts
export * from './prompts/index.js';

// Validator
export * from './validator/index.js';

// Recovery
export * from './recovery/index.js';

// Services (Issue #399)
export * from './services/index.js';

// Generator
export * from './generator/index.js';

// Storage (Issue #370)
export * from './storage/index.js';

// Tracing
export * from './tracing/index.js';

// API
export * from './api/index.js';

// Client
export * from './client/index.js';

// Legacy exports for backward compatibility
import type { WorkflowDefinition } from '../shared/types/workflow.types.js';

/**
 * @deprecated Use TaskGenerationRequest from ./types/generator.js
 */
export interface GenerationRequest {
  prompt: string;
  context?: Record<string, unknown>;
  constraints?: GenerationConstraints;
}

/**
 * @deprecated Use GenerationOptions from ./types/generator.js
 */
export interface GenerationConstraints {
  maxSteps?: number;
  allowedStepTypes?: string[];
  requiredCapabilities?: string[];
  timeout?: number;
}

/**
 * @deprecated Use BatchGenerationResponse from ./types/generator.js
 */
export interface LegacyGenerationResult {
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
 * @deprecated Use WorkflowGeneratorConfig from ./generator/WorkflowGenerator.js
 */
export interface TaskFlowGeneratorConfig {
  model?: string;
  maxTokens?: number;
  temperature?: number;
  langfuseEnabled?: boolean;
}

/**
 * Validation result interface
 */
export interface ValidationResult {
  valid: boolean;
  issues?: {
    type: 'error' | 'warning';
    message: string;
    path?: string;
  }[];
}

/**
 * TaskFlowGeneratorAgent - Legacy class for backward compatibility
 *
 * @deprecated Use WorkflowGenerator from ./generator/WorkflowGenerator.js
 */
export class TaskFlowGeneratorAgent {
  private readonly config: Required<TaskFlowGeneratorConfig>;

  constructor(config: TaskFlowGeneratorConfig = {}) {
    this.config = {
      model: config.model ?? 'claude-sonnet-4-20250514',
      maxTokens: config.maxTokens ?? 4096,
      temperature: config.temperature ?? 0.7,
      langfuseEnabled: config.langfuseEnabled ?? false,
    };
  }

  /**
   * Get configuration
   */
  getConfig(): Required<TaskFlowGeneratorConfig> {
    return { ...this.config };
  }

  /**
   * Generate workflow from prompt (mock implementation)
   *
   * @deprecated Use WorkflowGenerator.generate for real LLM-based generation
   */
  async generate(request: GenerationRequest): Promise<LegacyGenerationResult> {
    const startTime = Date.now();
    const workflowId = `wf_generated_${Date.now()}`;

    // Create a mock workflow based on the request
    const workflow: WorkflowDefinition = {
      id: workflowId,
      name: `Generated Workflow`,
      version: '1.0.0',
      steps: [
        {
          id: 'step_1',
          name: 'Process Input',
          type: 'action',
          config: {},
        },
        {
          id: 'step_2',
          name: 'Transform Data',
          type: 'action',
          config: {},
          dependsOn: ['step_1'],
        },
        {
          id: 'step_3',
          name: 'Output Result',
          type: 'action',
          config: {},
          dependsOn: ['step_2'],
        },
      ],
      variables: request.context,
    };

    return {
      status: 'success',
      workflow,
      reasoning: `Generated workflow for: ${request.prompt}`,
      metadata: {
        model: this.config.model,
        tokensUsed: 500,
        generationTimeMs: Date.now() - startTime,
      },
    };
  }

  /**
   * Validate workflow
   */
  async validate(workflow: WorkflowDefinition): Promise<ValidationResult> {
    const issues: ValidationResult['issues'] = [];

    // Basic validation
    if (!workflow.id || workflow.id.trim() === '') {
      issues.push({
        type: 'error',
        message: 'Workflow ID is required',
        path: 'id',
      });
    }

    if (!workflow.name || workflow.name.trim() === '') {
      issues.push({
        type: 'error',
        message: 'Workflow name is required',
        path: 'name',
      });
    }

    if (!workflow.steps || workflow.steps.length === 0) {
      issues.push({
        type: 'error',
        message: 'Workflow must have at least one step',
        path: 'steps',
      });
    }

    // Validate step dependencies
    if (workflow.steps) {
      const stepIds = new Set(workflow.steps.map((s) => s.id));
      for (const step of workflow.steps) {
        if (step.dependsOn) {
          for (const dep of step.dependsOn) {
            if (!stepIds.has(dep)) {
              issues.push({
                type: 'error',
                message: `Step "${step.id}" depends on non-existent step "${dep}"`,
                path: `steps.${step.id}.dependsOn`,
              });
            }
          }
        }
      }
    }

    return {
      valid: issues.length === 0,
      issues: issues.length > 0 ? issues : undefined,
    };
  }
}

/**
 * Factory function to create TaskFlowGeneratorAgent
 *
 * @deprecated Use createWorkflowGenerator from ./generator/WorkflowGenerator.js
 */
export function createTaskFlowGeneratorAgent(
  config?: TaskFlowGeneratorConfig
): TaskFlowGeneratorAgent {
  return new TaskFlowGeneratorAgent(config);
}

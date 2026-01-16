/**
 * WorkflowGenerator - Core workflow generation logic
 *
 * Issue #364: Main workflow generation with LLM integration
 */

import type { LLMClient } from '../llm/LLMClient.js';
import { WorkflowValidationError } from '../llm/LLMClient.js';
import { PromptBuilder } from '../prompts/PromptBuilder.js';
import { RetryStrategy } from '../recovery/RetryStrategy.js';
import { ValidationPipeline, type ValidationContext } from '../validator/ValidationPipeline.js';
import type {
  TaskGenerationRequest,
  Capability,
  ValidationResult,
} from '../types/generator.js';
import {
  TaskFlowDefinitionSchema,
  type TaskFlowDefinition,
} from '../../taskflowEngine/types/TaskFlowDefinition.js';

/**
 * Workflow Generator Configuration
 */
export interface WorkflowGeneratorConfig {
  llmClient: LLMClient;
  maxRetries?: number;
  retryDelayMs?: number;
  validateBeforeReturn?: boolean;
  promptBuilder?: PromptBuilder;
  validationPipeline?: ValidationPipeline;
}

/**
 * Generation Result with metadata
 */
export interface GenerationResult {
  workflow: TaskFlowDefinition;
  validationResult?: ValidationResult;
  llmMetadata: {
    model: string;
    promptTokens: number;
    completionTokens: number;
    latencyMs: number;
  };
}

/**
 * WorkflowGenerator - Generates TaskFlow workflows using LLM
 *
 * Features:
 * - LLM-based workflow generation
 * - Capability context injection
 * - Automatic validation
 * - Retry with exponential backoff
 */
export class WorkflowGenerator {
  private readonly llmClient: LLMClient;
  private readonly promptBuilder: PromptBuilder;
  private readonly retryStrategy: RetryStrategy;
  private readonly validationPipeline: ValidationPipeline;
  private readonly validateBeforeReturn: boolean;

  constructor(config: WorkflowGeneratorConfig) {
    this.llmClient = config.llmClient;
    this.promptBuilder = config.promptBuilder ?? new PromptBuilder();
    this.retryStrategy = new RetryStrategy({
      maxAttempts: config.maxRetries ?? 3,
      initialDelayMs: config.retryDelayMs ?? 1000,
      maxDelayMs: 10000,
      backoffFactor: 2,
    });
    this.validationPipeline = config.validationPipeline ?? new ValidationPipeline();
    this.validateBeforeReturn = config.validateBeforeReturn ?? true;
  }

  /**
   * Generate workflow for a single task
   *
   * @param task - Task generation request
   * @param capabilities - Available capabilities
   * @param projectId - Project identifier
   * @returns Generated TaskFlow definition
   */
  async generateSingle(
    task: TaskGenerationRequest,
    capabilities: Capability[],
    projectId?: string
  ): Promise<TaskFlowDefinition> {
    return this.retryStrategy.execute(async (_attempt) => {
      // Build prompt
      const prompt = this.promptBuilder.buildPrompt(task, capabilities);

      // Generate with LLM
      const response = await this.llmClient.generateStructured(
        prompt,
        TaskFlowDefinitionSchema
      );

      const workflow = response.data;

      // Validate if enabled
      if (this.validateBeforeReturn) {
        const context: ValidationContext = {
          capabilities,
          projectId: projectId ?? 'default',
        };

        const validationResult = await this.validationPipeline.validate(
          workflow,
          context
        );

        if (!validationResult.isValid) {
          const errorMessages = validationResult.errors
            ?.map((e) => e.message)
            .join('; ');
          throw new WorkflowValidationError(
            `Validation failed: ${errorMessages}`,
            workflow,
            validationResult
          );
        }
      }

      return workflow;
    });
  }

  /**
   * Generate workflow with full result metadata
   *
   * @param task - Task generation request
   * @param capabilities - Available capabilities
   * @param projectId - Project identifier
   * @returns Generation result with metadata
   */
  async generateWithMetadata(
    task: TaskGenerationRequest,
    capabilities: Capability[],
    projectId?: string
  ): Promise<GenerationResult> {
    return this.retryStrategy.execute(async () => {
      // Build prompt
      const prompt = this.promptBuilder.buildPrompt(task, capabilities);

      // Generate with LLM
      const response = await this.llmClient.generateStructured(
        prompt,
        TaskFlowDefinitionSchema
      );

      const workflow = response.data;

      // Validate
      const context: ValidationContext = {
        capabilities,
        projectId: projectId ?? 'default',
      };

      const validationResult = await this.validationPipeline.validate(
        workflow,
        context
      );

      if (this.validateBeforeReturn && !validationResult.isValid) {
        const errorMessages = validationResult.errors
          ?.map((e) => e.message)
          .join('; ');
        throw new WorkflowValidationError(
          `Validation failed: ${errorMessages}`,
          workflow,
          validationResult
        );
      }

      return {
        workflow,
        validationResult,
        llmMetadata: {
          model: response.raw.model,
          promptTokens: response.raw.usage.promptTokens,
          completionTokens: response.raw.usage.completionTokens,
          latencyMs: response.raw.latencyMs,
        },
      };
    });
  }
}

/**
 * Factory function
 */
export function createWorkflowGenerator(
  config: WorkflowGeneratorConfig
): WorkflowGenerator {
  return new WorkflowGenerator(config);
}

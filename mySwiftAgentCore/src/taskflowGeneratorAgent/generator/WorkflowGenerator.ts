/**
 * WorkflowGenerator - Core workflow generation logic
 *
 * Issue #364: Main workflow generation with LLM integration
 * Issue #374: Feedback loop support with metrics collection
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
  CapabilityForPrompt,
} from '../types/generator.js';
import {
  TaskFlowDefinitionSchema,
  type TaskFlowDefinition,
} from '../../taskflowEngine/types/TaskFlowDefinition.js';
// Issue #374: Import constants for feedback loop
import { MAX_RETRY_COUNT } from '../constants.js';
// Issue #374: Import WorkflowCapabilityError for feedback loop
import { WorkflowCapabilityError } from '../types/errors.js';
// Issue #374: Import metrics collector for generation tracking
import {
  createMetricsCollector,
  type AttemptData,
} from './MetricsCollector.js';

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
 *
 * Issue #374: Extended with generationMetrics for feedback loop tracking
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
  // Issue #374: Generation metrics from feedback loop
  generationMetrics?: {
    initialSuccessRate: number;
    averageRetryCount: number;
    tokenUsageByAttempt: number[];
    validationErrorTypes: Record<string, number>;
    totalDurationMs: number;
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
   * Issue #374: Implements feedback loop for validation failures
   * - Catches WorkflowCapabilityError and WorkflowValidationError
   * - Builds feedback prompt with error details
   * - Retries up to MAX_RETRY_COUNT times
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
    let attempt = 0;
    let lastError: Error | null = null;
    let lastRawContent = '';

    // Issue #374: Use MAX_RETRY_COUNT for feedback loop
    const maxRetries = Math.min(this.retryStrategy.getMaxAttempts(), MAX_RETRY_COUNT);

    while (attempt < maxRetries) {
      attempt++;

      try {
        // Build prompt (with feedback on retry)
        let prompt = this.promptBuilder.buildPrompt(task, capabilities);

        // Issue #374: Add feedback to prompt on retry
        if (lastError && lastRawContent) {
          const feedbackPrompt = this.buildFeedbackForRetry(
            prompt.user,
            lastError,
            lastRawContent,
            attempt - 1,
            capabilities as CapabilityForPrompt[]
          );
          prompt = {
            system: prompt.system,
            user: feedbackPrompt,
          };
        }

        // Generate with LLM
        const response = await this.llmClient.generateStructured(
          prompt,
          TaskFlowDefinitionSchema
        );

        const workflow = response.data;
        lastRawContent = response.raw.content;

        // Validate if enabled
        if (this.validateBeforeReturn) {
          const context: ValidationContext = {
            capabilities,
            projectId: projectId ?? 'default_project',
          };

          const validationResult = await this.validationPipeline.validate(
            workflow,
            context
          );

          if (!validationResult.isValid) {
            const errorMessages = validationResult.errors
              ?.map((e) => e.message)
              .join('; ');
            // Issue #374: Throw WorkflowCapabilityError for feedback loop
            throw new WorkflowCapabilityError(
              `Validation failed: ${errorMessages}`,
              validationResult,
              response.raw.content,
              attempt
            );
          }
        }

        return workflow;
      } catch (error) {
        lastError = error as Error;

        // Issue #374: Handle capability validation errors for feedback loop
        if (error instanceof WorkflowCapabilityError) {
          // Can retry with feedback
          if (attempt < maxRetries) {
            continue;
          }
        } else if (error instanceof WorkflowValidationError) {
          // Convert to WorkflowCapabilityError for consistent handling
          lastRawContent = JSON.stringify(error.workflow);
          if (attempt < maxRetries) {
            continue;
          }
        } else {
          // Other errors (LLM API errors, network errors, etc.) - retry without feedback
          if (attempt < maxRetries) {
            continue;
          }
        }

        // Max retries reached
        throw error;
      }
    }

    // Should not reach here, but just in case
    throw lastError ?? new Error('Generation failed after all retries');
  }

  /**
   * Build feedback prompt for retry attempt
   *
   * Issue #374: Creates feedback prompt using PromptBuilder
   *
   * @param originalPrompt - Original user prompt
   * @param error - Error from previous attempt
   * @param rawContent - Raw LLM output from previous attempt
   * @param attempt - Attempt number
   * @param capabilities - Available capabilities
   * @returns Feedback prompt string
   */
  private buildFeedbackForRetry(
    originalPrompt: string,
    error: Error,
    rawContent: string,
    attempt: number,
    capabilities: CapabilityForPrompt[]
  ): string {
    // Issue #374: Use buildFeedbackPrompt for WorkflowCapabilityError
    if (error instanceof WorkflowCapabilityError) {
      return this.promptBuilder.buildFeedbackPrompt(
        originalPrompt,
        error,
        capabilities
      );
    }

    // Fallback for other errors
    const sections: string[] = [];
    sections.push(`## Previous generation failed (attempt ${attempt}):`);
    sections.push(`Error: ${error.message}`);
    sections.push('');
    sections.push('## Previous Attempt (Failed)');
    sections.push('```json');
    sections.push(rawContent);
    sections.push('```');
    sections.push('');
    sections.push('## Original Requirements');
    sections.push(originalPrompt);
    sections.push('');
    sections.push('## Instructions');
    sections.push('Please fix the errors and regenerate the workflow.');
    sections.push('Output ONLY the corrected JSON workflow definition.');

    return sections.join('\n');
  }

  /**
   * Generate workflow with full result metadata
   *
   * Issue #374: Uses GenerationMetricsCollector to track generation metrics
   * - Tracks success rate, retry count, token usage
   * - Records validation error types for analysis
   *
   * @param task - Task generation request
   * @param capabilities - Available capabilities
   * @param projectId - Project identifier
   * @returns Generation result with metadata and metrics
   */
  async generateWithMetadata(
    task: TaskGenerationRequest,
    capabilities: Capability[],
    projectId?: string
  ): Promise<GenerationResult> {
    // Issue #374: Initialize metrics collector
    const metricsCollector = createMetricsCollector();
    metricsCollector.startGeneration();

    let attempt = 0;
    let lastError: Error | null = null;
    let lastRawContent = '';
    let lastResponse: {
      data: TaskFlowDefinition;
      raw: { content: string; model: string; usage: { promptTokens: number; completionTokens: number }; latencyMs: number };
    } | null = null;

    const maxRetries = Math.min(this.retryStrategy.getMaxAttempts(), MAX_RETRY_COUNT);

    while (attempt < maxRetries) {
      attempt++;
      const attemptStartTime = Date.now();

      try {
        // Build prompt (with feedback on retry)
        let prompt = this.promptBuilder.buildPrompt(task, capabilities);

        if (lastError && lastRawContent) {
          const feedbackPrompt = this.buildFeedbackForRetry(
            prompt.user,
            lastError,
            lastRawContent,
            attempt - 1,
            capabilities as CapabilityForPrompt[]
          );
          prompt = {
            system: prompt.system,
            user: feedbackPrompt,
          };
        }

        // Generate with LLM
        const response = await this.llmClient.generateStructured(
          prompt,
          TaskFlowDefinitionSchema
        );

        const workflow = response.data;
        lastResponse = response;
        lastRawContent = response.raw.content;

        // Validate
        const context: ValidationContext = {
          capabilities,
          projectId: projectId ?? 'default_project',
        };

        const validationResult = await this.validationPipeline.validate(
          workflow,
          context
        );

        const attemptEndTime = Date.now();

        // Issue #374: Record attempt metrics
        const attemptData: AttemptData = {
          startTime: attemptStartTime,
          endTime: attemptEndTime,
          durationMs: attemptEndTime - attemptStartTime,
          tokenUsage: {
            prompt: response.raw.usage.promptTokens,
            completion: response.raw.usage.completionTokens,
            total: response.raw.usage.promptTokens + response.raw.usage.completionTokens,
          },
          validationErrors: validationResult.errors ?? [],
          success: validationResult.isValid,
        };
        metricsCollector.recordAttempt(attemptData);

        if (this.validateBeforeReturn && !validationResult.isValid) {
          const errorMessages = validationResult.errors
            ?.map((e) => e.message)
            .join('; ');
          throw new WorkflowCapabilityError(
            `Validation failed: ${errorMessages}`,
            validationResult,
            response.raw.content,
            attempt
          );
        }

        // Issue #374: Finalize metrics and return with result
        const generationMetrics = metricsCollector.finalize();

        return {
          workflow,
          validationResult,
          llmMetadata: {
            model: response.raw.model,
            promptTokens: response.raw.usage.promptTokens,
            completionTokens: response.raw.usage.completionTokens,
            latencyMs: response.raw.latencyMs,
          },
          generationMetrics,
        };
      } catch (error) {
        lastError = error as Error;

        // Record failed attempt
        const attemptEndTime = Date.now();
        const attemptData: AttemptData = {
          startTime: attemptStartTime,
          endTime: attemptEndTime,
          durationMs: attemptEndTime - attemptStartTime,
          tokenUsage: {
            prompt: lastResponse?.raw.usage.promptTokens ?? 0,
            completion: lastResponse?.raw.usage.completionTokens ?? 0,
            total: (lastResponse?.raw.usage.promptTokens ?? 0) + (lastResponse?.raw.usage.completionTokens ?? 0),
          },
          validationErrors: error instanceof WorkflowCapabilityError
            ? (error.validationResult.errors ?? [])
            : [],
          success: false,
        };
        metricsCollector.recordAttempt(attemptData);

        // Handle capability validation errors for feedback loop
        if (error instanceof WorkflowCapabilityError) {
          if (attempt < maxRetries) {
            continue;
          }
        } else if (error instanceof WorkflowValidationError) {
          lastRawContent = JSON.stringify(error.workflow);
          if (attempt < maxRetries) {
            continue;
          }
        } else {
          // Other errors (LLM API errors, network errors, etc.) - retry without feedback
          if (attempt < maxRetries) {
            continue;
          }
        }

        throw error;
      }
    }

    throw lastError ?? new Error('Generation failed after all retries');
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

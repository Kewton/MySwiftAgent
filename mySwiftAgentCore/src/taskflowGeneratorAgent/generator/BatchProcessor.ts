/**
 * BatchProcessor - Parallel batch workflow generation
 *
 * Issue #364: Parallel execution with concurrency control
 */

import type { WorkflowGenerator } from './WorkflowGenerator.js';
import { ErrorHandler } from '../recovery/ErrorHandler.js';
import {
  type BatchGenerationRequest,
  type WorkflowGenerationResult,
  type TaskError,
  type TaskGenerationRequest,
  type Capability,
} from '../types/generator.js';
import type { TaskFlowDefinition } from '../../taskflowEngine/types/TaskFlowDefinition.js';

/**
 * Issue #368: Internal batch result type with workflow definitions
 *
 * This type extends the public BatchGenerationResponse with actual workflow definitions
 * for use by the Handler to register workflows with WorkflowRegistrar.
 */
export interface InternalBatchResult {
  success: boolean;
  workflows: Record<string, WorkflowGenerationResult>;
  workflowDefinitions: Record<string, TaskFlowDefinition>;
  failed_tasks: TaskError[];
}

/**
 * Batch Processor Configuration
 */
export interface BatchProcessorConfig {
  generator: WorkflowGenerator;
  maxConcurrency?: number;
  timeoutPerTaskMs?: number;
}

/**
 * Semaphore for concurrency control
 */
class Semaphore {
  private permits: number;
  private queue: Array<() => void> = [];

  constructor(permits: number) {
    this.permits = permits;
  }

  async acquire(): Promise<void> {
    if (this.permits > 0) {
      this.permits--;
      return;
    }

    await new Promise<void>((resolve) => {
      this.queue.push(resolve);
    });
    this.permits--;
  }

  release(): void {
    this.permits++;
    const next = this.queue.shift();
    if (next) {
      next();
    }
  }
}

/**
 * BatchProcessor - Processes multiple tasks in parallel
 *
 * Features:
 * - Concurrent execution with limit
 * - Partial success handling
 * - Error aggregation
 * - Timeout per task
 */
export class BatchProcessor {
  private readonly generator: WorkflowGenerator;
  private readonly maxConcurrency: number;
  private readonly timeoutPerTaskMs: number;
  private readonly errorHandler: ErrorHandler;

  constructor(config: BatchProcessorConfig) {
    this.generator = config.generator;
    this.maxConcurrency = config.maxConcurrency ?? 5;
    this.timeoutPerTaskMs = config.timeoutPerTaskMs ?? 30000;
    this.errorHandler = new ErrorHandler();
  }

  /**
   * Process batch of tasks
   *
   * Issue #368: Returns InternalBatchResult with workflowDefinitions for registration
   *
   * @param request - Batch generation request
   * @returns Internal batch result with workflow definitions and metadata
   */
  async processBatch(request: BatchGenerationRequest): Promise<InternalBatchResult> {
    const { tasks, capabilities, project_id, options } = request;

    // Use options from request if provided
    const concurrency = options?.max_concurrency ?? this.maxConcurrency;
    const timeout = options?.timeout_per_task_ms ?? this.timeoutPerTaskMs;

    // Handle empty task list
    if (tasks.length === 0) {
      return {
        success: true,
        workflows: {},
        workflowDefinitions: {},
        failed_tasks: [],
      };
    }

    // Create semaphore for concurrency control
    const semaphore = new Semaphore(concurrency);

    // Process all tasks in parallel (with concurrency limit)
    const results = await Promise.allSettled(
      tasks.map((task) =>
        this.processTask(task, capabilities, project_id, semaphore, timeout)
      )
    );

    // Aggregate results
    const workflows: Record<string, WorkflowGenerationResult> = {};
    const workflowDefinitions: Record<string, TaskFlowDefinition> = {};
    const failedTasks: TaskError[] = [];

    for (let i = 0; i < results.length; i++) {
      const result = results[i];
      const task = tasks[i];

      if (!task) continue;

      if (result?.status === 'fulfilled' && result.value) {
        // Store workflow metadata
        workflows[task.task_id] = {
          workflow_name: result.value.workflow_name,
          registered: false, // Will be set by WorkflowRegistrar
        };
        // Issue #368: Store actual workflow definition for registration
        workflowDefinitions[task.task_id] = result.value;
      } else if (result?.status === 'rejected') {
        const error = result.reason instanceof Error
          ? result.reason
          : new Error(String(result.reason));

        const taskError = await this.errorHandler.handle(error, {
          task_id: task.task_id,
        });

        failedTasks.push(taskError);
      }
    }

    return {
      success: failedTasks.length === 0,
      workflows,
      workflowDefinitions,
      failed_tasks: failedTasks,
    };
  }

  /**
   * Process a single task with semaphore and timeout
   */
  private async processTask(
    task: TaskGenerationRequest,
    capabilities: Capability[],
    projectId: string,
    semaphore: Semaphore,
    timeout: number
  ): Promise<TaskFlowDefinition> {
    // Acquire semaphore permit
    await semaphore.acquire();

    try {
      // Create timeout promise
      const timeoutPromise = new Promise<never>((_, reject) => {
        setTimeout(() => {
          const error = new Error(`Task ${task.task_id} timed out after ${timeout}ms`);
          error.name = 'TimeoutError';
          reject(error);
        }, timeout);
      });

      // Generate workflow with timeout
      const generationPromise = this.generator.generateSingle(
        task,
        capabilities,
        projectId
      );

      return await Promise.race([generationPromise, timeoutPromise]);
    } finally {
      // Release semaphore permit
      semaphore.release();
    }
  }
}

/**
 * Factory function
 */
export function createBatchProcessor(config: BatchProcessorConfig): BatchProcessor {
  return new BatchProcessor(config);
}

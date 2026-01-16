/**
 * ParallelExecutionManager - Resource management for parallel execution
 *
 * Issue #363: Implements 3-layer concurrency control
 * 1. Global limit: System-wide parallel execution limit
 * 2. Workflow limit: Per-workflow parallel execution limit
 * 3. Node type limit: Per-node-type parallel execution limit
 */

import type { NodeType } from '../types/TaskFlowDefinition.js';

/**
 * Parallel execution configuration
 */
export interface ParallelExecutionConfig {
  /** Global maximum concurrency (all workflows combined) */
  globalMaxConcurrency: number;
  /** Maximum concurrency per workflow */
  workflowMaxConcurrency: number;
  /** Node type specific limits */
  nodeTypeLimits: Record<NodeType, number>;
  /** Queue waiting timeout in ms */
  queueTimeoutMs: number;
}

/**
 * Execution metrics
 */
export interface ExecutionMetrics {
  activeGlobal: number;
  activeByWorkflow: Map<string, number>;
  activeByNodeType: Map<string, number>;
  queuedTasks: number;
  completedTasks: number;
  failedTasks: number;
}

/**
 * Parallel block result
 */
export interface ParallelBlockResult<T> {
  status: 'fulfilled' | 'rejected';
  value?: T;
  reason?: Error;
}

/**
 * Default configuration
 */
const DEFAULT_CONFIG: ParallelExecutionConfig = {
  globalMaxConcurrency: 50,
  workflowMaxConcurrency: 10,
  nodeTypeLimits: {
    api_rest: 20,
    code_js: 10,
    llm: 5,
    transform: 30,
    parallel: 10,
    action: 50,
  },
  queueTimeoutMs: 60000,
};

/**
 * Simple semaphore for concurrency limiting
 */
class Semaphore {
  private permits: number;
  private readonly maxPermits: number;
  private readonly waitQueue: Array<() => void> = [];

  constructor(permits: number) {
    this.permits = permits;
    this.maxPermits = permits;
  }

  async acquire(): Promise<void> {
    if (this.permits > 0) {
      this.permits--;
      return;
    }

    return new Promise<void>((resolve) => {
      this.waitQueue.push(resolve);
    });
  }

  release(): void {
    const next = this.waitQueue.shift();
    if (next) {
      next();
    } else if (this.permits < this.maxPermits) {
      this.permits++;
    }
  }
}

/**
 * ParallelExecutionManager - Manages parallel execution with 3-layer limits
 *
 * Features:
 * - Global concurrency limit
 * - Per-workflow concurrency limit
 * - Per-node-type concurrency limit
 * - Execution metrics tracking
 * - Timeout support
 */
export class ParallelExecutionManager {
  private readonly config: ParallelExecutionConfig;
  private readonly globalSemaphore: Semaphore;
  private readonly nodeTypeSemaphores: Map<string, Semaphore>;
  private readonly workflowSemaphores: Map<string, Semaphore>;
  private readonly metrics: ExecutionMetrics;

  constructor(config: Partial<ParallelExecutionConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
    this.globalSemaphore = new Semaphore(this.config.globalMaxConcurrency);
    this.nodeTypeSemaphores = new Map();
    this.workflowSemaphores = new Map();

    // Initialize node type semaphores
    for (const [type, limit] of Object.entries(this.config.nodeTypeLimits)) {
      this.nodeTypeSemaphores.set(type, new Semaphore(limit));
    }

    this.metrics = {
      activeGlobal: 0,
      activeByWorkflow: new Map(),
      activeByNodeType: new Map(),
      queuedTasks: 0,
      completedTasks: 0,
      failedTasks: 0,
    };
  }

  /**
   * Execute a task with 3-layer concurrency control
   *
   * @param workflowId - The workflow identifier
   * @param nodeType - The node type
   * @param task - The task to execute
   * @returns Task result
   */
  async execute<T>(
    workflowId: string,
    nodeType: string,
    task: () => Promise<T>
  ): Promise<T> {
    // Get or create workflow semaphore
    if (!this.workflowSemaphores.has(workflowId)) {
      this.workflowSemaphores.set(
        workflowId,
        new Semaphore(this.config.workflowMaxConcurrency)
      );
    }
    const workflowSemaphore = this.workflowSemaphores.get(workflowId)!;

    // Get node type semaphore (fallback to global if type not configured)
    const nodeTypeSemaphore =
      this.nodeTypeSemaphores.get(nodeType) || this.globalSemaphore;

    this.metrics.queuedTasks++;

    try {
      // Acquire all semaphores (3-layer control)
      await this.globalSemaphore.acquire();
      await workflowSemaphore.acquire();
      await nodeTypeSemaphore.acquire();

      this.metrics.queuedTasks--;
      this.updateActiveMetrics(workflowId, nodeType, 1);

      // Execute with timeout
      const result = await this.executeWithTimeout(task);
      this.metrics.completedTasks++;
      return result;
    } catch (error) {
      this.metrics.failedTasks++;
      throw error;
    } finally {
      this.updateActiveMetrics(workflowId, nodeType, -1);
      nodeTypeSemaphore.release();
      workflowSemaphore.release();
      this.globalSemaphore.release();
    }
  }

  /**
   * Execute multiple tasks in parallel
   *
   * @param workflowId - The workflow identifier
   * @param tasks - Array of tasks with their node types
   * @returns Array of results (fulfilled or rejected)
   */
  async executeParallelBlock<T>(
    workflowId: string,
    tasks: Array<{ nodeType: NodeType; task: () => Promise<T> }>
  ): Promise<Array<ParallelBlockResult<T>>> {
    const promises = tasks.map(async ({ nodeType, task }) => {
      try {
        const value = await this.execute(workflowId, nodeType, task);
        return { status: 'fulfilled' as const, value };
      } catch (error) {
        return {
          status: 'rejected' as const,
          reason: error instanceof Error ? error : new Error(String(error)),
        };
      }
    });

    return Promise.all(promises);
  }

  /**
   * Get current execution metrics
   */
  getMetrics(): ExecutionMetrics {
    return {
      activeGlobal: this.metrics.activeGlobal,
      activeByWorkflow: new Map(this.metrics.activeByWorkflow),
      activeByNodeType: new Map(this.metrics.activeByNodeType),
      queuedTasks: this.metrics.queuedTasks,
      completedTasks: this.metrics.completedTasks,
      failedTasks: this.metrics.failedTasks,
    };
  }

  /**
   * Cleanup resources for a workflow
   *
   * @param workflowId - The workflow identifier
   */
  cleanup(workflowId: string): void {
    this.workflowSemaphores.delete(workflowId);
    this.metrics.activeByWorkflow.delete(workflowId);
  }

  /**
   * Execute with timeout
   */
  private async executeWithTimeout<T>(task: () => Promise<T>): Promise<T> {
    const timeoutPromise = new Promise<never>((_, reject) => {
      setTimeout(() => {
        reject(new Error('Task execution timeout'));
      }, this.config.queueTimeoutMs);
    });

    return Promise.race([task(), timeoutPromise]);
  }

  /**
   * Update active metrics
   */
  private updateActiveMetrics(
    workflowId: string,
    nodeType: string,
    delta: number
  ): void {
    this.metrics.activeGlobal += delta;

    const currentWorkflow = this.metrics.activeByWorkflow.get(workflowId) || 0;
    this.metrics.activeByWorkflow.set(workflowId, currentWorkflow + delta);

    const currentNodeType = this.metrics.activeByNodeType.get(nodeType) || 0;
    this.metrics.activeByNodeType.set(nodeType, currentNodeType + delta);
  }
}

/**
 * Factory function to create ParallelExecutionManager
 */
export function createParallelExecutionManager(
  config?: Partial<ParallelExecutionConfig>
): ParallelExecutionManager {
  return new ParallelExecutionManager(config);
}

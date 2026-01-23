/**
 * WorkflowRegistrar - taskflowEngine integration with persistence
 *
 * Issue #364: Register generated workflows in taskflowEngine
 * Issue #370: Add persistence and logging
 * Issue #373: Add taskId support for nested directory structure
 * Issue #378: Add registerDetailed() and config directory loading
 */

import * as fs from 'fs/promises';
import * as path from 'path';
import type { TaskFlowDefinition } from '../../taskflowEngine/types/TaskFlowDefinition.js';
import type { WorkflowRegistry } from '../../taskflowEngine/registry/WorkflowRegistry.js';
import type { InternalWorkflowDefinition } from '../../taskflowEngine/types/InternalWorkflowDefinition.js';
import type { WorkflowStorage } from '../storage/WorkflowStorage.js';
import { Logger, createLogger } from '../../utils/logger/Logger.js';
import type {
  DetailedRegistrationResult,
  BatchRegistrationSummary,
  RegistrationStatus,
} from '../types/registration.js';
import { determineStatus } from '../types/registration.js';

/**
 * Registration Result
 */
export interface RegistrationResult {
  success: boolean;
  workflowId?: string;
  filePath?: string;
  error?: string;
}

/**
 * Registrar Configuration
 *
 * Issue #378: Added configDir for loading workflows from config directory
 */
export interface WorkflowRegistrarConfig {
  registry: WorkflowRegistry;
  storage?: WorkflowStorage;
  logger?: Logger;
  defaultProject?: string;
  /** Config directory path (default: config/taskflow/projects) */
  configDir?: string;
}

/**
 * Default config directory path
 */
const DEFAULT_CONFIG_DIR = 'config/taskflow/projects';

/**
 * WorkflowRegistrar - Registers workflows in taskflowEngine with persistence
 *
 * Features:
 * - Register workflow in WorkflowRegistry
 * - Persist workflow to filesystem via WorkflowStorage
 * - Project-based organization
 * - Structured logging
 * - Initialize from persisted storage
 * - Issue #378: Load from config directory with priority
 */
export class WorkflowRegistrar {
  private readonly registry: WorkflowRegistry;
  private readonly storage?: WorkflowStorage;
  private readonly logger: Logger;
  private readonly defaultProject: string;
  private readonly configDir: string;
  /** Track workflows loaded from config (to avoid overwriting with generated) */
  private readonly loadedFromConfig: Set<string> = new Set();

  constructor(config: WorkflowRegistrarConfig) {
    this.registry = config.registry;
    this.storage = config.storage;
    this.logger = config.logger ?? createLogger({ name: 'WorkflowRegistrar' });
    this.defaultProject = config.defaultProject ?? 'default_project';
    this.configDir = config.configDir ?? DEFAULT_CONFIG_DIR;
  }

  /**
   * Initialize registrar by loading workflows from storage
   *
   * Issue #370: Restore workflows from filesystem on startup
   * Issue #378: Load from config directory first (priority), then generated storage
   *
   * Loading order:
   * 1. config/taskflow/projects/{projectId}/workflows/ (priority, tracked in loadedFromConfig)
   * 2. generated/workflows/{projectId}/ (only if not already loaded from config)
   */
  async initialize(): Promise<void> {
    this.logger.info('Initializing WorkflowRegistrar');

    // Step 1: Load from config directory (priority)
    await this.loadFromConfigDirectory();

    // Step 2: Load from generated storage (don't overwrite config)
    if (this.storage) {
      await this.loadFromGeneratedStorage();
    }

    this.logger.info('WorkflowRegistrar initialization complete');
  }

  /**
   * Load workflows from config directory
   *
   * Issue #378: Config directory has priority over generated storage
   */
  private async loadFromConfigDirectory(): Promise<void> {
    this.logger.info('Loading workflows from config directory', {
      configDir: this.configDir,
    });

    try {
      // Check if config directory exists
      try {
        await fs.access(this.configDir);
      } catch {
        this.logger.debug('Config directory does not exist, skipping', {
          configDir: this.configDir,
        });
        return;
      }

      // List projects in config directory
      const projectEntries = await fs.readdir(this.configDir);
      let totalLoaded = 0;

      for (const projectId of projectEntries) {
        if (typeof projectId !== 'string') continue;

        const projectPath = path.join(this.configDir, projectId);

        // Check if it's a directory
        try {
          const stat = await fs.stat(projectPath);
          if (!stat.isDirectory()) continue;
        } catch {
          continue;
        }

        // Load workflows from project's workflows subdirectory
        const workflowsPath = path.join(projectPath, 'workflows');
        const loadedCount = await this.loadWorkflowsFromDirectory(projectId, workflowsPath, true);
        totalLoaded += loadedCount;

        if (loadedCount > 0) {
          this.logger.info('Loaded workflows from config', {
            projectId,
            count: loadedCount,
          });
        }
      }

      this.logger.info('Finished loading from config directory', {
        totalWorkflows: totalLoaded,
      });
    } catch (e) {
      this.logger.error('Failed to load from config directory', {
        error: e instanceof Error ? e.message : String(e),
      });
    }
  }

  /**
   * Load workflows from generated storage
   *
   * Issue #378: Don't overwrite workflows already loaded from config
   */
  private async loadFromGeneratedStorage(): Promise<void> {
    this.logger.info('Loading workflows from generated storage');

    try {
      const projects = await this.storage!.getAllProjects();
      let totalRestored = 0;

      for (const projectId of projects) {
        const workflows = await this.storage!.loadAll(projectId);

        for (const [workflowId, workflow] of Object.entries(workflows)) {
          const key = `${projectId}:${workflow.workflow_name}`;

          // Skip if already loaded from config
          if (this.loadedFromConfig.has(key)) {
            this.logger.debug('Skipping workflow (already loaded from config)', {
              projectId,
              workflowId,
            });
            continue;
          }

          try {
            const internalWorkflow = this.toInternalWorkflow(workflow);
            this.registry.registerForProject(projectId, internalWorkflow);
            totalRestored++;

            this.logger.debug('Restored workflow from generated storage', {
              projectId,
              workflowId,
            });
          } catch (e) {
            this.logger.warn('Failed to restore workflow', {
              projectId,
              workflowId,
              error: e instanceof Error ? e.message : String(e),
            });
          }
        }
      }

      this.logger.info('Finished loading from generated storage', {
        totalWorkflows: totalRestored,
      });
    } catch (e) {
      this.logger.error('Failed to initialize from storage', {
        error: e instanceof Error ? e.message : String(e),
      });
    }
  }

  /**
   * Load workflows from a directory
   *
   * @param projectId - Project identifier
   * @param dirPath - Directory path
   * @param markAsConfig - Whether to track as config-loaded (won't be overwritten)
   * @returns Number of workflows loaded
   */
  private async loadWorkflowsFromDirectory(
    projectId: string,
    dirPath: string,
    markAsConfig: boolean
  ): Promise<number> {
    let loaded = 0;

    try {
      // Check if directory exists
      try {
        await fs.access(dirPath);
      } catch {
        return 0;
      }

      const files = await fs.readdir(dirPath);

      for (const file of files) {
        if (typeof file !== 'string' || !file.endsWith('.json') || file.endsWith('.tmp')) {
          continue;
        }

        const filePath = path.join(dirPath, file);

        try {
          const content = await fs.readFile(filePath, 'utf-8');
          const workflow = JSON.parse(content) as TaskFlowDefinition;
          const internalWorkflow = this.toInternalWorkflow(workflow);

          this.registry.registerForProject(projectId, internalWorkflow);
          loaded++;

          if (markAsConfig) {
            const key = `${projectId}:${workflow.workflow_name}`;
            this.loadedFromConfig.add(key);
          }

          this.logger.debug('Loaded workflow', {
            projectId,
            workflowName: workflow.workflow_name,
            source: markAsConfig ? 'config' : 'generated',
          });
        } catch (e) {
          this.logger.warn('Failed to load workflow file', {
            filePath,
            error: e instanceof Error ? e.message : String(e),
          });
        }
      }
    } catch (e) {
      this.logger.debug('Failed to read directory', {
        dirPath,
        error: e instanceof Error ? e.message : String(e),
      });
    }

    return loaded;
  }

  /**
   * Register a workflow
   *
   * Issue #370: Also persist to filesystem
   * Issue #373: Add taskId support for nested directory structure
   *
   * @param workflow - TaskFlow definition to register
   * @param projectId - Project identifier (optional)
   * @param taskId - Task identifier for nested directory (optional)
   * @returns Registration result
   */
  async register(
    workflow: TaskFlowDefinition,
    projectId?: string,
    taskId?: string
  ): Promise<RegistrationResult> {
    const project = projectId ?? this.defaultProject;
    const workflowName = workflow.workflow_name;

    this.logger.info('Registering workflow', {
      projectId: project,
      workflowName,
      taskId,
    });

    try {
      // Convert TaskFlowDefinition to InternalWorkflowDefinition
      const internalWorkflow = this.toInternalWorkflow(workflow);

      // Register with taskflowEngine registry (memory)
      this.registry.registerForProject(project, internalWorkflow);

      this.logger.debug('Registered workflow to memory', {
        projectId: project,
        workflowId: internalWorkflow.id,
      });

      // Persist to storage if available
      let filePath: string | undefined;
      let storageError: string | undefined;

      if (this.storage) {
        const saveResult = await this.storage.save(project, workflowName, workflow, taskId);

        if (saveResult.success) {
          filePath = saveResult.filePath;
          this.logger.info('Persisted workflow to storage', {
            projectId: project,
            workflowName,
            filePath,
          });
        } else {
          storageError = saveResult.error;
          this.logger.warn('Failed to persist workflow to storage', {
            projectId: project,
            workflowName,
            error: storageError,
          });
        }
      }

      // If storage failed, return with error but still registered to memory
      if (storageError) {
        return {
          success: false,
          workflowId: workflowName,
          error: storageError,
        };
      }

      return {
        success: true,
        workflowId: workflowName,
        filePath,
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);

      this.logger.error('Failed to register workflow', {
        projectId: project,
        workflowName,
        error: errorMessage,
      });

      return {
        success: false,
        error: errorMessage,
      };
    }
  }

  /**
   * Register a workflow with detailed result
   *
   * Issue #378: Returns DetailedRegistrationResult with status field
   *
   * @param workflow - TaskFlow definition to register
   * @param projectId - Project identifier (optional)
   * @param taskId - Task identifier for nested directory (optional)
   * @returns Detailed registration result with status
   */
  async registerDetailed(
    workflow: TaskFlowDefinition,
    projectId?: string,
    taskId?: string
  ): Promise<DetailedRegistrationResult> {
    const project = projectId ?? this.defaultProject;
    const workflowName = workflow.workflow_name;

    this.logger.info('Registering workflow (detailed)', {
      projectId: project,
      workflowName,
      taskId,
    });

    let memoryRegistered = false;
    let storagePersisted = false;
    let filePath: string | undefined;
    let storageError: string | undefined;

    try {
      // Step 1: Register with taskflowEngine registry (memory)
      const internalWorkflow = this.toInternalWorkflow(workflow);
      this.registry.registerForProject(project, internalWorkflow);
      memoryRegistered = true;

      this.logger.debug('Registered workflow to memory', {
        projectId: project,
        workflowId: internalWorkflow.id,
      });

      // Step 2: Persist to storage if available
      if (this.storage) {
        const saveResult = await this.storage.save(project, workflowName, workflow, taskId);

        if (saveResult.success) {
          storagePersisted = true;
          filePath = saveResult.filePath;
          this.logger.info('Persisted workflow to storage', {
            projectId: project,
            workflowName,
            filePath,
          });
        } else {
          storageError = saveResult.error;
          this.logger.warn('Failed to persist workflow to storage', {
            projectId: project,
            workflowName,
            error: storageError,
          });
        }
      } else {
        // No storage configured, memory-only is considered full success
        storagePersisted = true;
      }

      // Determine status
      let status: RegistrationStatus;
      if (memoryRegistered && storagePersisted) {
        status = 'success';
      } else if (memoryRegistered) {
        status = 'partial_success';
      } else {
        status = 'failed';
      }

      return {
        status,
        success: status !== 'failed',
        workflowId: workflowName,
        filePath,
        memoryRegistered,
        storagePersisted,
        storageError,
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);

      this.logger.error('Failed to register workflow', {
        projectId: project,
        workflowName,
        error: errorMessage,
      });

      return {
        status: 'failed',
        success: false,
        memoryRegistered,
        storagePersisted,
        error: errorMessage,
      };
    }
  }

  /**
   * Register multiple workflows with detailed results
   *
   * Issue #378: Returns BatchRegistrationSummary with aggregated status
   *
   * @param workflows - Map of task_id to workflow
   * @param projectId - Project identifier (optional)
   * @returns Batch registration summary with detailed results
   */
  async registerBatchDetailed(
    workflows: Record<string, TaskFlowDefinition>,
    projectId?: string
  ): Promise<BatchRegistrationSummary> {
    const results: Record<string, DetailedRegistrationResult> = {};
    let succeeded = 0;
    let partialSuccess = 0;
    let failed = 0;

    this.logger.info('Registering batch of workflows (detailed)', {
      projectId: projectId ?? this.defaultProject,
      count: Object.keys(workflows).length,
    });

    for (const [taskId, workflow] of Object.entries(workflows)) {
      const result = await this.registerDetailed(workflow, projectId, taskId);
      results[taskId] = result;

      if (result.status === 'success') {
        succeeded++;
      } else if (result.status === 'partial_success') {
        partialSuccess++;
      } else {
        failed++;
      }
    }

    const total = Object.keys(workflows).length;
    const status = determineStatus(succeeded + partialSuccess, failed, total);

    this.logger.info('Batch registration complete (detailed)', {
      total,
      succeeded,
      partialSuccess,
      failed,
      status,
    });

    return {
      status,
      success: status !== 'failed',
      total,
      succeeded,
      partialSuccess,
      failed,
      results,
    };
  }

  /**
   * Register multiple workflows
   *
   * Issue #373: Pass task_id as taskId for directory structure
   *
   * @param workflows - Map of task_id to workflow
   * @param projectId - Project identifier (optional)
   * @returns Map of task_id to registration result
   */
  async registerBatch(
    workflows: Record<string, TaskFlowDefinition>,
    projectId?: string
  ): Promise<Record<string, RegistrationResult>> {
    const results: Record<string, RegistrationResult> = {};

    this.logger.info('Registering batch of workflows', {
      projectId: projectId ?? this.defaultProject,
      count: Object.keys(workflows).length,
    });

    for (const [taskId, workflow] of Object.entries(workflows)) {
      // Pass taskId for nested directory structure
      results[taskId] = await this.register(workflow, projectId, taskId);
    }

    const successCount = Object.values(results).filter((r) => r.success).length;
    this.logger.info('Batch registration complete', {
      total: Object.keys(workflows).length,
      success: successCount,
      failed: Object.keys(workflows).length - successCount,
    });

    return results;
  }

  /**
   * Check if workflow exists
   *
   * @param workflowName - Workflow name
   * @param projectId - Project identifier (optional)
   * @returns True if workflow exists
   */
  exists(workflowName: string, projectId?: string): boolean {
    const project = projectId ?? this.defaultProject;

    try {
      const workflow = this.registry.getWorkflow(project, workflowName);
      return !!workflow;
    } catch {
      return false;
    }
  }

  /**
   * Unregister a workflow
   *
   * @param workflowName - Workflow name
   * @param projectId - Project identifier (optional)
   * @returns True if unregistered successfully
   */
  unregister(workflowName: string, projectId?: string): boolean {
    const project = projectId ?? this.defaultProject;

    this.logger.info('Unregistering workflow', {
      projectId: project,
      workflowName,
    });

    try {
      return this.registry.unregisterFromProject(project, workflowName);
    } catch {
      return false;
    }
  }

  /**
   * Convert TaskFlowDefinition to InternalWorkflowDefinition
   */
  private toInternalWorkflow(workflow: TaskFlowDefinition): InternalWorkflowDefinition {
    return {
      id: `wf_${Date.now()}_${workflow.workflow_name}`,
      name: workflow.workflow_name,
      version: '1.0.0',
      steps: workflow.steps.map((step) => ({
        id: step.id,
        name: step.id,
        type: step.type,
        config: step.config as Record<string, unknown>,
        params: step.params as Record<string, unknown>,
      })),
      inputSchema: workflow.input_schema,
      outputSchema: workflow.output_schema,
      outputMapping: workflow.output,
    };
  }
}

/**
 * Factory function
 */
export function createWorkflowRegistrar(
  config: WorkflowRegistrarConfig
): WorkflowRegistrar {
  return new WorkflowRegistrar(config);
}

/**
 * TaskFlow v2 API - Workflow Endpoints
 *
 * Provides REST API endpoints for:
 * - Workflow execution
 * - Workflow validation
 * - Workflow registration (admin)
 * - Workflow management (admin)
 *
 * @module api/v2/workflows
 * @see Issue #348
 */

import { Router } from 'express';
import type { Request, Response, NextFunction } from 'express';
import fs from 'fs';
import path from 'path';
import { parseWorkflow } from '../../engine/parser/workflow-parser.js';
import { executeWorkflow, hasWorkflowErrors } from '../../engine/executor/workflow-executor.js';
import { workflowValidator, ValidationReporter } from '../../engine/validator/index.js';
import type { ValidatorOptions } from '../../engine/validator/workflow-validator.js';
import { ValidationError, NotFoundError, ForbiddenError, asyncHandler } from './error-handler.js';
import { settings } from '../../config/settings.js';
import type { WorkflowResult } from '../../types/taskflow.js';

// ============================================================
// Configuration
// ============================================================

/** Workflow storage directory */
const WORKFLOW_DIR = path.resolve(process.cwd(), 'config/taskflow/workflows');

// Ensure directory exists
if (!fs.existsSync(WORKFLOW_DIR)) {
  fs.mkdirSync(WORKFLOW_DIR, { recursive: true });
}

// ============================================================
// Router
// ============================================================

const router = Router();

// ============================================================
// Middleware
// ============================================================

/**
 * Admin token authentication middleware
 */
function requireAdminToken(req: Request, res: Response, next: NextFunction): void {
  const token = req.headers['x-admin-token'];

  if (!settings.ADMIN_TOKEN || token !== settings.ADMIN_TOKEN) {
    throw new ForbiddenError('Invalid admin token');
  }

  next();
}

// ============================================================
// Public Endpoints
// ============================================================

/**
 * POST /api/v2/workflows
 * Execute a workflow
 *
 * Request body:
 * - workflow_name: string (optional) - Name of registered workflow
 * - definition: object (optional) - Inline workflow definition
 * - inputs: object - Workflow inputs
 * - project: string (optional) - Project for secrets
 *
 * Response: WorkflowResult
 */
router.post(
  '/',
  asyncHandler(async (req: Request, res: Response) => {
    const { workflow_name, definition, inputs, project } = req.body;

    // Validate request
    if (!inputs || typeof inputs !== 'object') {
      throw new ValidationError('inputs is required and must be an object');
    }

    if (!workflow_name && !definition) {
      throw new ValidationError('Either workflow_name or definition is required');
    }

    let workflowDef = definition;

    // Load registered workflow if name provided
    if (workflow_name && !definition) {
      workflowDef = loadRegisteredWorkflow(workflow_name);
    }

    // Parse workflow
    const parseResult = parseWorkflow(workflowDef);

    if (!parseResult.success) {
      throw new ValidationError('Invalid workflow definition', {
        errors: parseResult.errors,
      });
    }

    // Execute workflow
    console.log(`[v2/workflows] Executing workflow: ${workflow_name || workflowDef.workflow_name}`);

    const result = await executeWorkflow(parseResult.workflow!, inputs, {
      project,
    });

    // Return with appropriate status code
    if (hasWorkflowErrors(result)) {
      res.status(500).json(result);
    } else {
      res.json(result);
    }
  })
);

/**
 * POST /api/v2/workflows/validate
 * Validate a workflow definition without executing
 *
 * Request body:
 * - definition: object - Workflow definition to validate
 * - options?: { level?: 1|2|3, strict?: boolean, checkUrls?: boolean, includeAgentFeedback?: boolean }
 *
 * Response:
 * - valid: boolean
 * - errors: array (for backward compatibility)
 * - issues: array (new format with severity)
 * - summary: { errors, warnings, infos }
 * - agentSummary?: object (for LLM auto-fix)
 */
router.post(
  '/validate',
  asyncHandler(async (req: Request, res: Response) => {
    const { definition, options } = req.body;

    if (!definition) {
      throw new ValidationError('definition is required');
    }

    // Build validator options
    const validatorOptions: ValidatorOptions = {
      level: options?.level || 2,
      strict: options?.strict || false,
      checkUrls: options?.checkUrls || false,
      includeAgentFeedback: options?.includeAgentFeedback ?? true,
    };

    // Use new 3-level validator
    const result = await workflowValidator.validate(definition, validatorOptions);

    // Convert to backward-compatible format
    const errors = result.issues
      .filter((i) => i.severity === 'error')
      .map((i) => ({
        path: i.path || '',
        message: i.message,
        code: i.code,
      }));

    res.json({
      valid: result.valid,
      errors, // backward compatibility
      issues: result.issues,
      summary: result.summary,
      agentSummary: result.agentSummary,
    });
  })
);

/**
 * GET /api/v2/workflows
 * List all registered workflows
 *
 * Response:
 * - workflows: array of workflow names
 */
router.get(
  '/',
  asyncHandler(async (req: Request, res: Response) => {
    const workflows = listRegisteredWorkflows();

    res.json({
      workflows,
      count: workflows.length,
    });
  })
);

/**
 * GET /api/v2/workflows/:name
 * Get a registered workflow definition
 *
 * Response: WorkflowDefinition
 */
router.get(
  '/:name',
  asyncHandler(async (req: Request, res: Response) => {
    const { name } = req.params;

    const workflow = loadRegisteredWorkflow(name);

    res.json(workflow);
  })
);

// ============================================================
// Admin Endpoints
// ============================================================

/**
 * POST /api/v2/workflows/register
 * Register a new workflow
 *
 * Request body:
 * - workflow_name: string
 * - definition: object
 * - overwrite: boolean (optional)
 *
 * Response:
 * - status: string
 * - workflow_name: string
 * - file_path: string
 */
router.post(
  '/register',
  requireAdminToken,
  asyncHandler(async (req: Request, res: Response) => {
    const { workflow_name, definition, overwrite = false } = req.body;

    if (!workflow_name) {
      throw new ValidationError('workflow_name is required');
    }

    if (!definition) {
      throw new ValidationError('definition is required');
    }

    // Validate workflow name
    const nameRegex = /^[a-zA-Z_][a-zA-Z0-9_-]*$/;
    if (!nameRegex.test(workflow_name)) {
      throw new ValidationError(
        'workflow_name must start with a letter or underscore and contain only alphanumeric characters, underscores, and hyphens'
      );
    }

    // Validate definition using 3-level validator
    const validationResult = await workflowValidator.validate(definition, {
      level: 2,
      includeAgentFeedback: true,
    });
    if (!validationResult.valid) {
      throw new ValidationError('Invalid workflow definition', {
        errors: validationResult.issues.filter((i) => i.severity === 'error'),
        agentSummary: validationResult.agentSummary,
      });
    }

    // Check if exists
    const filePath = path.join(WORKFLOW_DIR, `${workflow_name}.json`);
    if (fs.existsSync(filePath) && !overwrite) {
      throw new ValidationError(
        `Workflow '${workflow_name}' already exists. Set overwrite=true to replace.`
      );
    }

    // Ensure workflow_name in definition matches
    const finalDefinition = {
      ...definition,
      workflow_name,
    };

    // Save workflow
    fs.writeFileSync(filePath, JSON.stringify(finalDefinition, null, 2));

    console.log(`[v2/workflows] Registered workflow: ${workflow_name}`);

    res.json({
      status: 'success',
      workflow_name,
      file_path: filePath,
    });
  })
);

/**
 * DELETE /api/v2/workflows/:name
 * Delete a registered workflow
 *
 * Response:
 * - status: string
 * - workflow_name: string
 */
router.delete(
  '/:name',
  requireAdminToken,
  asyncHandler(async (req: Request, res: Response) => {
    const { name } = req.params;

    // Validate name
    const nameRegex = /^[a-zA-Z_][a-zA-Z0-9_-]*$/;
    if (!nameRegex.test(name)) {
      throw new ValidationError('Invalid workflow name');
    }

    const filePath = path.join(WORKFLOW_DIR, `${name}.json`);

    if (!fs.existsSync(filePath)) {
      throw new NotFoundError(`Workflow '${name}' not found`);
    }

    fs.unlinkSync(filePath);

    console.log(`[v2/workflows] Deleted workflow: ${name}`);

    res.json({
      status: 'success',
      workflow_name: name,
    });
  })
);

// ============================================================
// Helper Functions
// ============================================================

/**
 * Load a registered workflow from disk
 * @param name - Workflow name
 * @returns Workflow definition
 */
function loadRegisteredWorkflow(name: string): unknown {
  // Validate name (security)
  const nameRegex = /^[a-zA-Z_][a-zA-Z0-9_-]*$/;
  if (!nameRegex.test(name)) {
    throw new ValidationError('Invalid workflow name');
  }

  const filePath = path.join(WORKFLOW_DIR, `${name}.json`);

  if (!fs.existsSync(filePath)) {
    throw new NotFoundError(`Workflow '${name}' not found`);
  }

  try {
    const content = fs.readFileSync(filePath, 'utf8');
    return JSON.parse(content);
  } catch (error) {
    throw new ValidationError(
      `Failed to load workflow: ${error instanceof Error ? error.message : String(error)}`
    );
  }
}

/**
 * List all registered workflows
 * @returns Array of workflow names
 */
function listRegisteredWorkflows(): string[] {
  if (!fs.existsSync(WORKFLOW_DIR)) {
    return [];
  }

  const files = fs.readdirSync(WORKFLOW_DIR);

  return files
    .filter((f) => f.endsWith('.json'))
    .map((f) => f.replace('.json', ''))
    .sort();
}

// ============================================================
// Export
// ============================================================

export default router;

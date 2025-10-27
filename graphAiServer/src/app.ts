import express, { Request, Response } from 'express';
import cors from 'cors';
import helmet from 'helmet';
import fs from 'fs';
import path from 'path';
import yaml from 'js-yaml';
import { runGraphAI, testGraphAI, GraphAIResponse } from './services/graphai.js';
import { secretsManager } from './services/secretsManager.js';
import { settings } from './config/settings.js';
import type {
  WorkflowRegisterRequest,
  WorkflowRegisterResponse,
  WorkflowValidationError,
} from './types/workflow.js';

const app = express();

// Configuration: Workflow directory path (resolve from process.cwd())
const WORKFLOW_DIR = path.resolve(process.cwd(), 'config/graphai');

// Middleware
app.use(helmet());
app.use(cors());
app.use(express.json());

// Health check endpoint (required for CI/CD)
app.get('/health', (_req: Request, res: Response) => {
  res.json({ status: 'healthy', service: 'graphAiServer' });
});

// Root endpoint
app.get('/', (_req: Request, res: Response) => {
  res.json({ message: 'Welcome to Graph AI Server' });
});

// API v1 root
app.get('/api/v1/', (_req: Request, res: Response) => {
  res.json({ version: '1.0', service: 'graphAiServer' });
});

// GraphAI test endpoint
app.get('/api/v1/test', async (_req: Request, res: Response) => {
  try {
    console.log("Executing GraphAI sample...");
    const result: GraphAIResponse = await testGraphAI();
    console.log("GraphAI sample finished.");

    // Check if there are any errors in the execution
    const hasErrors = Object.keys(result.errors).length > 0;
    const hasTimedOutNodes = result.logs.some(log => log.state === 'timed-out');

    if (hasErrors || hasTimedOutNodes) {
      // Return 500 if there are errors or timeouts, but include full details
      res.status(500).json(result);
    } else {
      // Return 200 for successful execution
      res.json(result);
    }
  } catch (error) {
    console.error("Error executing GraphAI sample:", error);

    const errorMessage = error instanceof Error ? error.message : String(error);
    const errorStack = error instanceof Error ? error.stack : undefined;

    res.status(500).json({
      error: 'An error occurred while executing the GraphAI sample.',
      details: {
        message: errorMessage,
        type: errorMessage.includes('Timeout') ? 'timeout' : 'initialization_error',
        timestamp: new Date().toISOString(),
      },
      ...(process.env.NODE_ENV !== 'production' && { stack: errorStack })
    });
  }
});

// GraphAI agent endpoint with path parameters (new format)
app.post('/api/v1/myagent/:category/:model', async (req: Request, res: Response) => {
  const { user_input, project } = req.body;
  const { category, model } = req.params;

  if (!user_input) {
    return res.status(400).json({ error: 'user_input is required' });
  }

  // Path traversal security validation
  if (category.includes('..') || category.includes('/') || category.includes('\\')) {
    return res.status(400).json({ error: 'Invalid category parameter' });
  }

  if (model.includes('..') || model.includes('/') || model.includes('\\')) {
    return res.status(400).json({ error: 'Invalid model parameter' });
  }

  try {
    // Construct model_name from category and model
    const model_name = `${category}/${model}`;

    const result: GraphAIResponse = await runGraphAI(user_input, model_name, project);

    // Check if there are any errors in the execution
    const hasErrors = Object.keys(result.errors).length > 0;
    const hasTimedOutNodes = result.logs.some(log => log.state === 'timed-out');

    if (hasErrors || hasTimedOutNodes) {
      // Return 500 if there are errors or timeouts, but include full details
      res.status(500).json(result);
    } else {
      // Return 200 for successful execution
      res.json(result);
    }
  } catch (error) {
    console.error("Error executing GraphAI sample:", error);

    const errorMessage = error instanceof Error ? error.message : String(error);
    const errorStack = error instanceof Error ? error.stack : undefined;

    res.status(500).json({
      error: 'An error occurred while executing the GraphAI sample.',
      details: {
        message: errorMessage,
        type: errorMessage.includes('Timeout') ? 'timeout' : 'initialization_error',
        timestamp: new Date().toISOString(),
      },
      ...(process.env.NODE_ENV !== 'production' && { stack: errorStack })
    });
  }
});

// GraphAI agent endpoint (legacy format for backward compatibility)
app.post('/api/v1/myagent', async (req: Request, res: Response) => {
  const { user_input, model_name, project } = req.body;

  if (!user_input) {
    return res.status(400).json({ error: 'user_input is required' });
  }

  if (!model_name) {
    return res.status(400).json({ error: 'model_name is required' });
  }

  try {
    const result: GraphAIResponse = await runGraphAI(user_input, model_name, project);

    // Check if there are any errors in the execution
    const hasErrors = Object.keys(result.errors).length > 0;
    const hasTimedOutNodes = result.logs.some(log => log.state === 'timed-out');

    if (hasErrors || hasTimedOutNodes) {
      // Return 500 if there are errors or timeouts, but include full details
      res.status(500).json(result);
    } else {
      // Return 200 for successful execution
      res.json(result);
    }
  } catch (error) {
    console.error("Error executing GraphAI sample:", error);

    const errorMessage = error instanceof Error ? error.message : String(error);
    const errorStack = error instanceof Error ? error.stack : undefined;

    res.status(500).json({
      error: 'An error occurred while executing the GraphAI sample.',
      details: {
        message: errorMessage,
        type: errorMessage.includes('Timeout') ? 'timeout' : 'initialization_error',
        timestamp: new Date().toISOString(),
      },
      ...(process.env.NODE_ENV !== 'production' && { stack: errorStack })
    });
  }
});

// Workflow registration endpoint
app.post('/api/v1/workflows/register', async (req: Request, res: Response) => {
  const { workflow_name, yaml_content, overwrite = false, directory } = req.body as WorkflowRegisterRequest;

  // Validate request body
  if (!workflow_name || !yaml_content) {
    const response: WorkflowRegisterResponse = {
      status: 'error',
      error_message: 'Both workflow_name and yaml_content are required',
    };
    return res.status(400).json(response);
  }

  // Validate directory parameter (path traversal protection)
  if (directory && directory.includes('..')) {
    const response: WorkflowRegisterResponse = {
      status: 'error',
      error_message: 'Invalid directory parameter: ".." is not allowed for security reasons',
    };
    return res.status(400).json(response);
  }

  // Validate workflow_name (must be a valid filename)
  const filenameRegex = /^[a-zA-Z0-9_-]+$/;
  if (!filenameRegex.test(workflow_name)) {
    const response: WorkflowRegisterResponse = {
      status: 'error',
      error_message: 'workflow_name must contain only alphanumeric characters, underscores, and hyphens',
    };
    return res.status(400).json(response);
  }

  // Path traversal security validation
  if (workflow_name.includes('..') || workflow_name.includes('/') || workflow_name.includes('\\')) {
    const response: WorkflowRegisterResponse = {
      status: 'error',
      error_message: 'Invalid workflow_name parameter',
    };
    return res.status(400).json(response);
  }

  const validation_errors: WorkflowValidationError[] = [];

  try {
    // Step 1: Validate YAML syntax
    try {
      yaml.load(yaml_content);
    } catch (error) {
      const yamlError = error as Error & { mark?: { line: number; column: number } };
      validation_errors.push({
        type: 'yaml_syntax',
        message: yamlError.message,
        line: yamlError.mark?.line,
        column: yamlError.mark?.column,
      });

      const response: WorkflowRegisterResponse = {
        status: 'error',
        error_message: 'YAML syntax validation failed',
        validation_errors,
      };
      return res.status(400).json(response);
    }

    // Step 2: Construct target directory path
    const target_dir = directory
      ? path.join(WORKFLOW_DIR, directory)
      : WORKFLOW_DIR;

    // Step 3: Check if target directory exists (create if needed)
    if (!fs.existsSync(target_dir)) {
      try {
        fs.mkdirSync(target_dir, { recursive: true });
        console.log(`Created workflow directory: ${target_dir}`);
      } catch (error) {
        validation_errors.push({
          type: 'file_system',
          message: `Failed to create workflow directory: ${error}`,
        });

        const response: WorkflowRegisterResponse = {
          status: 'error',
          error_message: 'Failed to create workflow directory',
          validation_errors,
        };
        return res.status(500).json(response);
      }
    }

    // Step 4: Check if file already exists (if overwrite is false)
    const file_path = path.join(target_dir, `${workflow_name}.yml`);
    if (fs.existsSync(file_path) && !overwrite) {
      const response: WorkflowRegisterResponse = {
        status: 'error',
        error_message: `Workflow '${workflow_name}' already exists. Set overwrite=true to replace it.`,
      };
      return res.status(409).json(response);
    }

    // Step 5: Write YAML content to file
    try {
      fs.writeFileSync(file_path, yaml_content, 'utf8');
      console.log(`✓ Workflow registered: ${file_path}`);

      const response: WorkflowRegisterResponse = {
        status: 'success',
        file_path,
        workflow_name,
      };
      return res.status(200).json(response);
    } catch (error) {
      validation_errors.push({
        type: 'file_system',
        message: `Failed to write workflow file: ${error}`,
      });

      const response: WorkflowRegisterResponse = {
        status: 'error',
        error_message: 'Failed to write workflow file',
        validation_errors,
      };
      return res.status(500).json(response);
    }
  } catch (error) {
    console.error('Unexpected error during workflow registration:', error);

    const errorMessage = error instanceof Error ? error.message : String(error);
    const response: WorkflowRegisterResponse = {
      status: 'error',
      error_message: `Internal server error: ${errorMessage}`,
    };
    return res.status(500).json(response);
  }
});

// Admin token middleware
const requireAdminToken = (req: Request, res: Response, next: Function) => {
  const token = req.headers['x-admin-token'];
  if (!settings.ADMIN_TOKEN || token !== settings.ADMIN_TOKEN) {
    return res.status(403).json({ error: 'Invalid admin token' });
  }
  next();
};

// Admin health check
app.get('/api/v1/admin/health', (_req: Request, res: Response) => {
  res.json({ status: 'healthy', service: 'graphaiserver-admin' });
});

// Cache reload endpoint
app.post('/api/v1/admin/reload-secrets', requireAdminToken, (req: Request, res: Response) => {
  try {
    const { project } = req.body;
    secretsManager.clearCache(project);
    res.json({
      success: true,
      message: project ? `Cache cleared for project: ${project}` : 'All cache cleared',
    });
  } catch (error) {
    res.status(500).json({ error: String(error) });
  }
});

export default app;
